import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from source_intake import evaluate, fingerprint, normalize, markdown


def row(ident="a", metadata="2026-10-12", data_modified=""):
    return {
        "id": ident, "title": "Mercati settimanali Milano",
        "organization": "Comune di Milano",
        "metadata_modified": metadata, "data_modified": data_modified,
        "license": "CC BY 4.0",
        "license_status": "claimed_open_license_review_required",
        "score": 15,
        "resources": [{"format": "CSV", "url": "https://dati.comune.milano.it/mercati.csv",
                       "name": "Mercati"}],
    }


def scout(rows, offline=False, errors=None, stamp="2026-10-12T00:00:00Z"):
    return {
        "metadata_only": True, "generated_at_utc": stamp,
        "candidates": rows, "query_failures": errors or {},
        "offline_mode": offline, "truncated": False,
    }


class IntakeTests(unittest.TestCase):
    def test_new_sources_never_auto_approved(self):
        result = evaluate(scout([row()]))
        self.assertEqual(result["scan"]["delta"]["new"], 1)
        self.assertEqual(result["record_imports"], 0)
        self.assertEqual(result["source_licenses_verified_by_automation"], 0)
        item = result["sources"][0]
        self.assertFalse(item["automatic_import_allowed"])
        self.assertIn("license_terms", item["review_required"])
        self.assertIn("Licenza", markdown(result))

    def test_metadata_harvest_timestamp_is_not_market_update(self):
        first = evaluate(scout([row(metadata="2026-10-11")]))
        newer = evaluate(scout([row(metadata="2026-10-12")],
                               stamp="2026-10-13T00:00:00Z"), first)
        self.assertEqual(newer["scan"]["delta"]["changed"], 0)
        self.assertEqual(newer["scan"]["delta"]["unchanged"], 1)
        actual = evaluate(scout([row(data_modified="2026-09-03")],
                                stamp="2026-10-14T00:00:00Z"), newer)
        self.assertEqual(actual["scan"]["delta"]["changed"], 1)
        self.assertEqual(len(actual["events"]), 2)

    def test_partial_and_offline_scan_does_not_erase_sources(self):
        first = evaluate(scout([row("a"), row("b")]))
        offline = evaluate(scout([], offline=True, stamp="2026-10-13T00:00:00Z"), first)
        self.assertEqual(offline["scan"]["total_known"], 2)
        self.assertEqual(offline["scan"]["delta"]["not_seen_in_sample"], 0)
        self.assertFalse(offline["sample_reliable_for_missing_match"])
        broken = evaluate(scout([row("a")], errors={"q": "timeout"},
                                stamp="2026-10-14T00:00:00Z"), offline)
        self.assertFalse(broken["sample_reliable_for_missing_match"])
        self.assertFalse(next(x for x in broken["sources"] if x["id"] == "b")["not_seen_in_latest_sample"])

    def test_missing_in_bounded_sample_does_not_delete(self):
        first = evaluate(scout([row("a"), row("b")]))
        newer = evaluate(scout([row("a")], stamp="2026-10-13T00:00:00Z"), first)
        self.assertEqual(len(newer["sources"]), 2)
        self.assertTrue(next(x for x in newer["sources"] if x["id"] == "b")["not_seen_in_latest_sample"])
        self.assertEqual(newer["scan"]["delta"]["not_seen_in_sample"], 1)

    def test_bad_urls_and_duplicate_ids_fail_closed(self):
        invalid = row()
        invalid["resources"] = [{"format":"CSV","url":"https://user:pass@localhost/export.csv"}]
        with self.assertRaisesRegex(ValueError, "secure structured-data"):
            normalize(invalid)
        with self.assertRaisesRegex(ValueError, "Duplicate source ID"):
            evaluate(scout([row(), row()]))

    def test_requires_read_only_metadata_contract(self):
        with self.assertRaisesRegex(ValueError, "read-only"):
            evaluate({"candidates": [row()]})

    def test_unknown_prior_schema_must_not_overwrite(self):
        with self.assertRaisesRegex(ValueError, "Unknown source registry schema"):
            evaluate(scout([row()]), {"schema": 999, "sources": []})


if __name__ == "__main__":
    unittest.main()
