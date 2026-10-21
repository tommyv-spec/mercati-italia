"""The Happings finisher waits for the real complete checkpoint."""
from __future__ import annotations
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from happings_bulk_finisher import progress,finish

class FinisherTests(unittest.TestCase):
    def test_incomplete_state_requires_no_action(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/"checkpoint.json").write_text(
                json.dumps({"schema":1,"queue":["A","B"],"done":{"A":{}}}),"utf-8")
            self.assertEqual(progress(root),(1,2))
            with patch("happings_bulk_finisher.current_dev_catalog",
                       side_effect=AssertionError("Must not fetch a new catalog")):
                self.assertEqual(finish(root,repo=root,out=root/"audit"),
                                 {"complete":False,"pages_completed":1,"pages_total":2})
    def test_complete_state_runs_exact_reconciliation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/"checkpoint.json").write_text(
                json.dumps({"schema":1,"queue":["A"],"done":{"A":{}}}),"utf-8")
            with (patch("happings_bulk_finisher.current_dev_catalog",
                        return_value=(root/"fake-manifest.json","testsha")),
                  patch("happings_bulk_finisher.retry_failures",
                        return_value={"new_requests":0,"recovered_in_this_run":0,
                          "source_pages_unresolved":0,"source_content_complete":True}),
                  patch("happings_bulk_finisher.analyze",
                        return_value={"unique_weekly_city_day_groups":1,
                          "outcomes":{"new_venue_possible_needs_source_html_admission":1},
                          "existing_catalog_id_mutations":0}) as analyzer,
                  patch("happings_bulk_finisher.audit_detail_matches",
                        return_value={"counts":{"uniquely_matched_existing":1}})):
                result=finish(root,repo=root,out=root/"audit")
                self.assertTrue(result["complete"])
                analyzer.assert_called_once()
                doc=json.loads((root/"audit/happings-source-reconciliation.json").read_text("utf-8"))
                self.assertEqual(doc["dev_revision_analyzed"],"testsha")
    def test_tampered_queue_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)
            (p/"checkpoint.json").write_text(
                json.dumps({"schema":1,"queue":["A","A"],"done":{}}),"utf-8")
            with self.assertRaises(ValueError):
                progress(p)
if __name__=="__main__":
    unittest.main()
