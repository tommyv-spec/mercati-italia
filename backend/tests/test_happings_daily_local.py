"""Local scheduled Happings refresh must be idempotent and fail visible."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from happings_daily_local import run


class DailyHappingsTests(unittest.TestCase):
    def test_success_records_both_exact_stages(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with (patch("happings_daily_local.refresh",
                        return_value={"pages_attempted":0,"new_urls_discovered":0}) as refresh,
                  patch("happings_daily_local.finish",
                        return_value={"complete":True,"source_content_complete":True,
                                      "dev_sha":"verified-head"}) as finish):
                result=run(snapshot=root/"scan",repo=root,out=root/"qa")
            self.assertEqual(result["status"],"completed")
            self.assertTrue(result["qa"]["source_content_complete"])
            refresh.assert_called_once()
            finish.assert_called_once()

    def test_qa_failure_preserves_machine_readable_error(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with (patch("happings_daily_local.refresh",
                        return_value={"pages_attempted":1}),
                  patch("happings_daily_local.finish",side_effect=ValueError("Unverified source URL"))):
                with self.assertRaisesRegex(ValueError,"Unverified"):
                    run(snapshot=root/"scan",repo=root,out=root/"qa")
            report=json.loads((root/"qa/happings-local-run.json").read_text(encoding="utf-8"))
            self.assertEqual(report["status"],"failed")
            self.assertEqual(report["error_type"],"ValueError")
            self.assertFalse(report["production_modified"])
            self.assertFalse(report["github_paid_services_used"])

    def test_discovery_batch_progress_does_not_run_premature_qa(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with (patch("happings_daily_local.refresh",
                        return_value={"pages_attempted":70,"pages_pending":21}),
                  patch("happings_daily_local.finish",
                        side_effect=AssertionError("Never finish an open queue"))):
                result=run(snapshot=root/"scan",repo=root,out=root/"qa")
            self.assertEqual(result["status"],"in_progress")
            self.assertEqual(result["qa"]["complete"],False)
            self.assertEqual(json.loads((root/"qa/happings-local-run.json").read_text("utf-8"))["status"],
                             "in_progress")

    def test_incomplete_snapshot_never_passes_as_complete(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with (patch("happings_daily_local.refresh",return_value={"pages_attempted":0}),
                  patch("happings_daily_local.finish",
                        return_value={"complete":False,"pages_completed":42})):
                with self.assertRaisesRegex(ValueError,"first-pass"):
                    run(snapshot=root/"scan",repo=root,out=root/"qa")


if __name__=="__main__":
    unittest.main()
