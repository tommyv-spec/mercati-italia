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

    def test_dataset_scoped_freshness_count_is_not_record_verification(self):
        freshness = {"metrics": {
            "source_date_within_30d": 1300,
            "recent_dataset_only_update": 1127,
            "dataset_updated_not_specific_market": 1127,
        }}
        row = summary(decision(), None, None, "test-scope",
                      None, freshness)
        self.assertEqual(row["source_dataset_level_records"], 1127)
        self.assertEqual(row["source_recent_dataset_only"], 1127)
        self.assertEqual(row["documented_verification_count"], 0)

    def test_lombardia_screening_stats_remain_review_only(self):
        screened = {
            "schema": 1, "source_total": 1360, "accepted": 1127,
            "quarantined": 233, "market_confirmations": 0,
            "deleted_existing_records": 0,
        }
        result = summary(decision(), None, None, "extra", None, None, None, screened)
        self.assertEqual(result["lombardia_source_total"], 1360)
        self.assertEqual(result["lombardia_source_accepted"], 1127)
        self.assertEqual(result["lombardia_source_quarantined"], 233)

    def test_bologna_quarantine_history_is_explicit_and_not_verification(self):
        bologna = {"schema": 1,"source_total":48,"accepted":47,
                   "quarantined":1,"market_confirmations":0,
                   "deleted_existing_records":0}
        result = summary(decision(),None,None,"bologna",None,None,None,None,bologna)
        self.assertEqual(result["bologna_source_total"],48)
        self.assertEqual(result["bologna_source_accepted"],47)
        self.assertEqual(result["bologna_source_quarantined"],1)
        self.assertEqual(result["documented_verification_count"],0)

    def test_bologna_report_cannot_claim_unreviewed_import(self):
        bad = {"schema":1,"source_total":48,"accepted":47,
               "quarantined":1,"market_confirmations":1}
        with self.assertRaisesRegex(ValueError,"Untrusted official overlap"):
            summary(decision(),None,None,"bad",None,None,None,None,bad)

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
