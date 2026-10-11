import unittest
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from freshness_monitor import analyze, markdown


TODAY = date(2026, 10, 12)


def row(slug="a", **overrides):
    value = {
        "slug": slug, "fonte": "Comune", "url_fonte": "https://example.org/m",
        "aggiornato_il": "2026-10-11", "date_quality": "prevista",
        "date": ["2026-10-17"], "verificato_il": "",
    }
    value.update(overrides)
    return value


class FreshnessTests(unittest.TestCase):
    def test_fresh_automatic_refresh_is_not_false_human_verification(self):
        result = analyze([row()], TODAY)
        m = result["metrics"]
        self.assertEqual(m["source_date_within_30d"], 1)
        self.assertEqual(m["with_forecast_dates"], 1)
        self.assertEqual(m["without_documented_verification"], 1)
        self.assertIn("no_record_has_documented_verification", result["warnings"])
        self.assertTrue(result["safe_for_automatic_quality_promotion"])
        self.assertFalse(result["catalog_was_modified"])

    def test_stale_or_unknown_source_predictions_are_reported(self):
        result = analyze([
            row("old", aggiornato_il="2023-03-03"),
            row("unknown", aggiornato_il=""),
            row("fresh", aggiornato_il="2026-10-11"),
        ], TODAY)
        self.assertEqual(result["metrics"]["forecast_from_stale_or_unknown_source"], 2)
        self.assertEqual(result["metrics"]["source_date_outside_limit"], 1)
        self.assertIn("future_predictions_have_stale_or_missing_source_dates", result["warnings"])

    def test_suspect_confirmation_blocks_automatic_promotion(self):
        out = analyze([row(date_quality="confermata")], TODAY)
        self.assertFalse(out["safe_for_automatic_quality_promotion"])
        self.assertIn("confirmed_events_without_documented_evidence", out["errors"])

    def test_future_dated_source_blocks_automatic_promotion(self):
        out = analyze([row(aggiornato_il="2027-10-12")], TODAY)
        self.assertFalse(out["safe_for_automatic_quality_promotion"])
        self.assertEqual(out["metrics"]["future_dated_source"], 1)

    def test_publisher_metadata_is_never_event_confirmation(self):
        evidence = {
            "schema": 1, "market_imports": 0,
            "source_evidence": [
                {"publisher": "Roma Capitale", "status": "metadata_checked",
                 "publisher_data_updated_at": "2022-06-10",
                 "license_comparison": "publisher_and_catalog_agree_review_required"},
            ],
        }
        out = analyze([row()], TODAY, evidence)
        self.assertEqual(out["publisher_evidence"][0]["market_records_verified_by_metadata"], 0)
        self.assertIn("Roma Capitale", markdown(out))

    def test_invalid_untrusted_publisher_report_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "Untrusted"):
            analyze([row()], TODAY, {"schema": 1, "market_imports": 1})

    def test_repeatable_for_same_date(self):
        inputs = [row("x"), row("y", aggiornato_il="2020-01-01")]
        one = analyze(inputs, TODAY)
        two = analyze(inputs, TODAY)
        self.assertEqual(one, two)
        self.assertEqual(inputs[0]["verificato_il"], "")

    def test_duplicate_record_ids_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            analyze([row("dup"), row("dup")], TODAY)


if __name__ == "__main__":
    unittest.main()
