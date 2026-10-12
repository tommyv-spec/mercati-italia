import unittest
from datetime import date, datetime, timezone
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from source_evidence import SPECS, evaluate, license_code, date_value, metadata_fetch


def reg():
    return {
        "schema": 1, "record_imports": 0,
        "sources": [
            {"id": s["id"], "license":
             "Creative Commons Attribuzione 4.0 Internazionale (CC BY 4.0)"
             if s["slug"] in ("bologna", "roma")
             else "Creative Commons CC0 1.0 Universale"}
            for s in SPECS
        ],
    }


def responder(url):
    if "bologna.it" in url:
        return {
            "dataset_id": "mercati-e-fiere",
            "metas": {"default": {
                "license": "CC BY 4.0", "modified": "2025-12-31T12:31:56Z",
                "data_processed": "2025-04-02T14:33:42Z",
                "modified_updates_on_data_change": False,
                "metadata_processed": "2026-10-10T12:00:00Z",
            }},
        }
    if "lombardia.it" in url:
        return {
            "id": "68zx-njaw", "license": {
                "name": "CC0 1.0",
                "termsLink": "https://creativecommons.org/publicdomain/zero/1.0/"
            },
            "rowsUpdatedAt": 1791244800, "viewLastModified": 1791331200,
        }
    if "roma.it" in url:
        return {
            "success": True, "result": {
                "id": "e2e30174-ba7f-4319-bf4a-c13f80278c0c",
                "license_title": "CC BY 4.0",
                "metadata_modified": "2026-10-10T09:00:00",
                "resources": [{
                    "id": "61ae5f8b-8ac5-44c0-ad82-6d342d0c45d6",
                    "name": "Mercati Rionali - Giugno 2022",
                    "url": "https://dati.comune.roma.it/data/mercati_rionali_giugno_2022.csv",
                    "last_modified": "2022-06-10T10:00:00",
                    "license_type": "CC BY 4.0",
                }],
            },
        }
    raise AssertionError("Unexpected URL")


class RightsEvidenceTests(unittest.TestCase):
    def test_publisher_metadata_does_not_grant_publication_or_legal_approval(self):
        result = evaluate(reg(), fetch=responder, today=date(2026, 10, 12))
        self.assertEqual(result["source_requests_max"], 3)
        self.assertEqual(result["market_imports"], 0)
        self.assertEqual(result["legal_license_approvals"], 0)
        for row in result["source_evidence"]:
            self.assertEqual(row["status"], "metadata_checked")
            self.assertEqual(row["market_events_confirmed"], 0)
            self.assertFalse(row["import_permission_granted"])
            self.assertFalse(row["license_legally_reviewed"])
            self.assertFalse(row["record_level_freshness_verified"])
            self.assertEqual(row["license_comparison"],
                             "publisher_and_catalog_agree_review_required")

    def test_bologna_manual_modified_does_not_disguise_old_data(self):
        result = evaluate(reg(), fetch=responder, today=date(2026, 10, 12))
        bologna = result["source_evidence"][0]
        self.assertEqual(bologna["publisher_data_updated_at"], "2025-04-02")
        self.assertEqual(bologna["publisher_declared_modified_at"], "2025-12-31")
        self.assertEqual(bologna["publisher_metadata_updated_at"], "2026-10-10")
        self.assertEqual(bologna["provider_data_timestamp_type"], "publisher_data_processed")
        self.assertIn("modified_newer_than_data_without_auto_update", bologna["review_required"])
        self.assertEqual(bologna["source_data_age_label"], "dataset_metadata_over_365d")
        self.assertFalse(bologna["record_level_freshness_verified"])

    def test_bologna_requires_processing_timestamp_when_no_auto_update_flag(self):
        def no_processed(url):
            obj = responder(url)
            if "bologna.it" in url:
                obj["metas"]["default"].pop("data_processed")
            return obj
        report = evaluate(reg(), fetch=no_processed, today=date(2026,10,12))
        row = report["source_evidence"][0]
        self.assertIsNone(row["publisher_data_updated_at"])
        self.assertIn("publisher_data_processed_unknown", row["review_required"])
        self.assertEqual(row["source_data_age_label"], "dataset_update_unknown")

    def test_roma_is_archival_even_with_new_metadata_harvest(self):
        result = evaluate(reg(), fetch=responder, today=date(2026, 10, 12))
        roman = next(r for r in result["source_evidence"] if r["publisher"] == "Roma Capitale")
        self.assertEqual(roman["edition_year"], 2022)
        self.assertIn("historical_resource_edition", roman["review_required"])
        self.assertEqual(roman["publisher_data_updated_at"], "2022-06-10")
        self.assertEqual(roman["publisher_metadata_updated_at"], "2026-10-10")
        self.assertEqual(roman["source_data_age_label"], "dataset_metadata_over_365d")

    def test_unknown_license_or_conflicting_license_cannot_be_called_verified(self):
        conflicting = reg()
        conflicting["sources"][0]["license"] = "CC0 1.0"
        result = evaluate(conflicting, fetch=responder, today=date(2026, 10, 12))
        self.assertEqual(result["source_evidence"][0]["license_comparison"],
                         "conflicting_claims_review_required")
        self.assertFalse(result["source_evidence"][0]["license_legally_reviewed"])

    def test_mismatched_dataset_is_quarantined(self):
        def wrong(url):
            if "lombardia" in url:
                return {"id": "unrelated", "license": "CC0"}
            return responder(url)
        result = evaluate(reg(), fetch=wrong, today=date(2026, 10, 12))
        row = result["source_evidence"][1]
        self.assertEqual(row["status"], "needs_review")
        self.assertNotIn("publisher_response_sha256", row)
        self.assertFalse(row["import_permission_granted"])

    def test_missing_roma_resource_is_quarantined(self):
        def changed(url):
            obj = responder(url)
            if "roma" in url:
                obj["result"]["resources"] = []
            return obj
        result = evaluate(reg(), fetch=changed, today=date(2026, 10, 12))
        self.assertEqual(result["source_evidence"][2]["status"], "needs_review")

    def test_offline_never_fetches(self):
        result = evaluate(reg(), fetch=lambda _: self.fail("network"),
                          offline=True, today=date(2026, 10, 12))
        self.assertTrue(all(x["status"] == "offline" for x in result["source_evidence"]))

    def test_license_matching_is_exact_and_never_approves_nc(self):
        self.assertEqual(license_code("CC BY 4.0"), "CC-BY-4.0")
        self.assertEqual(license_code("cc-by4"), "CC-BY-4.0")
        self.assertEqual(license_code("CC0 1.0"), "CC0-1.0")
        self.assertIsNone(license_code("CC BY-NC-SA 4.0"))
        self.assertIsNone(license_code("copyright reserved"))
        self.assertIsNone(license_code("unlicensed"))
        with self.assertRaisesRegex(ValueError, "Unapproved"):
            metadata_fetch("https://evil.example/private")

    def test_only_dataset_metadata_timestamps_are_counted(self):
        self.assertEqual(date_value("2025-12-31T11:00:00Z").isoformat(), "2025-12-31")
        self.assertIsNone(date_value("not an ISO date"))
        self.assertIsNone(date_value(0))
        epoch = datetime(2026, 10, 6, tzinfo=timezone.utc).timestamp()
        self.assertEqual(date_value(epoch).isoformat(), "2026-10-06")


if __name__ == "__main__":
    unittest.main()
