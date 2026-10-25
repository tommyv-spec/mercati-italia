import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "ops"))
import runner as r


class RunnerTests(unittest.TestCase):
    def test_expressions_used_by_the_project_workflows(self):
        ctx = r.Ctx(github=r.Ctx(event_name="schedule", run_id="42"), inputs=r.Ctx(),
                    env=r.Ctx(DEV_BRANCH="dev"), needs=r.Ctx(qa=r.Ctx(result="success")),
                    always=lambda: True)
        self.assertEqual(r.expand("${{ github.event_name == 'workflow_dispatch' && inputs.offline || 'false' }}", ctx), "false")
        self.assertEqual(r.expand("x-${{ github.run_id }}-${{ env.DEV_BRANCH }}", ctx), "x-42-dev")
        self.assertTrue(r.condition("needs.qa.result == 'success'", ctx, default=False))
        self.assertTrue(r.condition("${{ always() }}", ctx, default=False))
        self.assertFalse(r.condition(None, ctx, default=False))

    def test_daily_and_weekly_due_rules_catch_up_missed_runs(self):
        with patch.object(r, "schedule_of", side_effect=lambda n: {"d": "17 04 * * *".split(),
                                                                     "w": "05 03 * * 1".split()}[n]):
            monday, tuesday = date(2026, 10, 26), date(2026, 10, 27)
            self.assertTrue(r.due("d", {}, monday)[0])
            self.assertFalse(r.due("d", {"d": {"last_success": "2026-10-26"}}, monday)[0])
            self.assertTrue(r.due("w", {"w": {"last_success": "2026-10-19"}}, monday)[0])
            self.assertFalse(r.due("w", {"w": {"last_success": "2026-10-26"}}, tuesday)[0])
            # The PC was off on Monday: the weekly job catches up on Tuesday.
            self.assertTrue(r.due("w", {"w": {"last_success": "2026-10-19"}}, tuesday)[0])

    def test_single_directory_artifact_round_trips_its_contents(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = type("R", (), {"artifacts": Path(tmp) / "art"})()
            first, second = Path(tmp) / "a", Path(tmp) / "b"
            (first / "out").mkdir(parents=True)
            (first / "out" / "report.json").write_text("{}", encoding="utf-8")
            ctx = r.Ctx(github=r.Ctx(run_id="7"))
            r.upload(run, first, {"name": "rep-${{ github.run_id }}", "path": "out/"}, ctx)
            second.mkdir()
            r.download(run, second, {"name": "rep-${{ github.run_id }}", "path": "restored"}, ctx)
            self.assertTrue((second / "restored" / "report.json").is_file())
            # Several paths under one folder: that folder is the root (no nesting).
            (first / "out" / "b.md").write_text("#", encoding="utf-8")
            r.upload(run, first, {"name": "multi", "path": "out/report.json\nout/b.md"}, ctx)
            r.download(run, second, {"name": "multi", "path": "out"}, ctx)
            self.assertTrue((second / "out" / "report.json").is_file())
            self.assertTrue((second / "out" / "b.md").is_file())
            self.assertFalse((second / "out" / "out").exists())


if __name__ == "__main__":
    unittest.main()
