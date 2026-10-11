import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from autopilot_history import summary, save_history, HISTORY_LIMIT

def decision():
    return {
        "approved":True, "has_changes":True,
        "candidate":{
            "records":12650,"future_60":11056,"future_90":11048,
            "indexed_gzip_bytes":356587,"verified":0,"precise":89,
            "missing_hours":10627
        },
        "gates":{"records_ok":True},
    }

class AutopilotHistoryTests(unittest.TestCase):
    def test_metrics_without_pii_and_priority_order(self):
        result=summary(
            decision(),
            {"queue":[{"code":"verified_source_evidence"},{"code":"location_precision"}]},
            {"candidates":[{},{}],"query_failures":{}},
            "101"
        )
        self.assertEqual(result["record_count"],12650)
        self.assertEqual(result["top_improvement_priorities"][0],"verified_source_evidence")
        self.assertEqual(result["source_candidates_scored"],2)
        self.assertNotIn("user",result)
        self.assertTrue(result["dev_only"])

    def test_source_intelligence_metrics_are_reported_without_auto_importing(self):
        registry = {
            "scan": {"total_known": 42, "delta": {"new": 2, "changed": 3}},
            "sources": [
                {"triage_class": "market_location_candidate"},
                {"triage_class": "aggregated_statistics"},
                {"triage_class": "market_location_candidate"},
            ],
        }
        report = summary(decision(), None, None, "200", registry)
        self.assertEqual(report["source_registry_known"], 42)
        self.assertEqual(report["source_registry_new"], 2)
        self.assertEqual(report["source_registry_changed"], 3)
        self.assertEqual(report["source_location_candidates"], 2)
        self.assertEqual(report["source_historical_statistics"], 1)

    def test_monitor_data_is_persisted_without_claiming_events_are_verified(self):
        monitor = {
            "metrics": {
                "source_date_within_30d": 5,
                "source_date_outside_limit": 100,
                "source_date_unknown": 8,
                "forecast_from_stale_or_unknown_source": 7,
            },
            "warnings": ["source_data_older_than_allowed_forecast_window"],
            "errors": [],
        }
        rights = {"source_evidence": [
            {"status": "metadata_checked"},
            {"status": "needs_review"},
            {"status": "metadata_checked"},
        ]}
        value = summary(decision(), None, None, "fresh-1", None, monitor, rights)
        self.assertEqual(value["source_age_over_limit"], 100)
        self.assertEqual(value["forecast_from_stale_sources"], 7)
        self.assertEqual(value["publisher_metadata_readable"], 2)
        self.assertEqual(value["publisher_metadata_checked"], 3)
        self.assertIn("oltre soglia", __import__("autopilot_history").markdown(value))
        self.assertNotIn("verified_event_count", value)

    def test_history_is_idempotent_and_bounded(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            for i in range(HISTORY_LIMIT+5):
                record=summary(decision(),None,None,str(i))
                save_history(folder,record)
            history=(folder/"history.jsonl").read_text("utf-8").splitlines()
            self.assertEqual(len(history),HISTORY_LIMIT)
            self.assertNotIn('"run_id": "0"',history[0])
            item=summary(decision(),None,None,str(HISTORY_LIMIT+4))
            save_history(folder,item)
            self.assertEqual(len((folder/"history.jsonl").read_text("utf-8").splitlines()),HISTORY_LIMIT)
            self.assertIn("Mercati Autopilot",(folder/"LATEST.md").read_text("utf-8"))

    def test_failed_candidate_cannot_be_recorded_as_success(self):
        bad=decision()
        bad["approved"]=False
        with self.assertRaisesRegex(ValueError,"failed candidate"):
            summary(bad,None,None,"1")

if __name__=="__main__":
    unittest.main()
