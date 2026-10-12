import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_change_detector import compare, markdown


def snapshot(data_date="2026-10-06", digest="first", status="metadata_checked"):
    return {
        "schema": 1, "market_imports": 0, "reference_date": "2026-10-12",
        "source_evidence": [{
            "source_id": "lombardia", "publisher": "Regione Lombardia",
            "status": status,
            "publisher_response_sha256": digest,
            "publisher_data_updated_at": data_date,
        }],
    }


class ChangeDetectorTests(unittest.TestCase):
    def test_first_scan_has_no_proven_change(self):
        result=compare(snapshot())
        self.assertEqual(result["counts"]["first_observation"],1)
        self.assertEqual(result["imported_markets"],0)

    def test_stable_recheck_is_idempotent(self):
        result=compare(snapshot(),snapshot())
        self.assertEqual(result["counts"]["unchanged"],1)
        self.assertEqual(result,compare(snapshot(),snapshot()))

    def test_metadata_only_change_is_not_a_dataset_update(self):
        result=compare(snapshot(digest="new"),snapshot())
        self.assertEqual(result["counts"]["publisher_metadata_changed"],1)
        self.assertEqual(result["counts"]["publisher_data_date_advanced"],0)

    def test_advanced_data_date_does_not_authorize_import(self):
        result=compare(snapshot("2026-10-11","new"),snapshot())
        self.assertEqual(result["counts"]["publisher_data_date_advanced"],1)
        self.assertFalse(result["results"][0]["automatic_import_allowed"])
        self.assertEqual(result["results"][0]["events_confirmed"],0)

    def test_older_timestamp_is_flagged_not_treated_as_fresh(self):
        result=compare(snapshot("2025-10-01"),snapshot())
        self.assertEqual(result["counts"]["publisher_data_date_rolled_back"],1)

    def test_timestamp_methodology_fix_is_not_falsely_reported_as_supplier_rollback(self):
        old = snapshot("2025-12-31")
        old["source_evidence"][0]["provider_data_timestamp_type"] = "publisher_dataset_modified"
        corrected = snapshot("2025-04-02")
        corrected["source_evidence"][0]["provider_data_timestamp_type"] = "publisher_data_processed"
        result = compare(corrected, old)
        self.assertEqual(result["counts"]["timestamp_interpretation_corrected"], 1)
        self.assertEqual(result["counts"]["publisher_data_date_rolled_back"], 0)
        self.assertEqual(result["counts"]["publisher_data_date_advanced"], 0)
        self.assertFalse(result["results"][0]["automatic_import_allowed"])

    def test_network_failure_is_distinct_from_source_change(self):
        result=compare(snapshot(status="needs_review"),snapshot())
        self.assertEqual(result["counts"]["publisher_unavailable"],1)

    def test_markdown_remains_review_only(self):
        self.assertIn("Nessuna licenza",markdown(compare(snapshot())))

    def test_malformed_previous_snapshot_is_rejected(self):
        with self.assertRaises(ValueError):
            compare(snapshot(),{"schema":1,"market_imports":5})


if __name__=="__main__":
    unittest.main()
