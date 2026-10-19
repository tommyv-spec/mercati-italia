import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from freshness_monitor import analyze, markdown, add_refresh_evidence


TODAY = date(2026, 10, 12)


def row(slug="a", **overrides):
    value = {
        "slug": slug, "fonte": "Comune", "url_fonte": "https://example.org/m",
        "aggiornato_il": "2026-10-11", "fonte_aggiornata_il": "2026-10-11",
        "date_quality": "prevista",
        "date": ["2026-10-17"], "verificato_il": "",
    }
    value.update(overrides)
    return value


class FreshnessTests(unittest.TestCase):
    def test_daily_refresh_report_binds_same_catalog_and_date(self):
        result = analyze([row()], TODAY)
        decision = {"new_signature": "same-catalog", "today": TODAY.isoformat(),
            "publisher_refresh": {"release_safe": True, "conflicts": 1,
                "source_url_coverage": {"markets": 1, "unique_primary_urls": 1},
                "selected_pages": [{"source_id": "municipal-list", "status": "layout_changed"}]}}
        add_refresh_evidence(result, decision, "same-catalog")
        self.assertIn("publisher_refresh_incomplete", result["warnings"])
        self.assertIn("publisher_refresh_conflicting_fields", result["warnings"])
        self.assertIn("municipal-list", markdown(result))
        with self.assertRaises(ValueError):
            add_refresh_evidence(result, decision, "different-catalog")
        with self.assertRaises(ValueError):
            add_refresh_evidence(result, {**decision, "today": "2025-01-01"}, "same-catalog")

    def test_fresh_automatic_refresh_is_not_false_human_verification(self):
        result = analyze([row()], TODAY)
        m = result["metrics"]
        self.assertEqual(m["source_date_within_30d"], 1)
        self.assertEqual(m["with_forecast_dates"], 1)
        self.assertEqual(m["without_documented_verification"], 1)
        self.assertIn("no_record_has_documented_verification", result["warnings"])
        self.assertTrue(result["safe_for_automatic_quality_promotion"])
        self.assertFalse(result["catalog_was_modified"])

    def test_recent_dataset_timestamp_is_not_an_individual_market_verification(self):
        result = analyze([row(fonte_aggiornata_il="2026-10-06",
                              aggiornamento_ambito="dataset")], TODAY)
        self.assertEqual(result["metrics"]["source_date_within_30d"], 1)
        self.assertEqual(result["metrics"]["recent_dataset_only_update"], 1)
        self.assertEqual(result["metrics"]["dataset_updated_not_specific_market"], 1)
        self.assertEqual(result["metrics"]["without_documented_verification"], 1)

    def test_stale_or_unknown_source_predictions_are_reported(self):
        result = analyze([
            row("old", fonte_aggiornata_il="2023-03-03"),
            row("unknown", fonte_aggiornata_il=""),
            row("fresh", fonte_aggiornata_il="2026-10-11"),
        ], TODAY)
        self.assertEqual(result["metrics"]["forecast_from_stale_or_unknown_source"], 2)
        self.assertEqual(result["metrics"]["source_date_outside_limit"], 1)
        self.assertIn("future_predictions_have_stale_or_missing_source_dates", result["warnings"])

    def test_suspect_confirmation_blocks_automatic_promotion(self):
        out = analyze([row(date_quality="confermata")], TODAY)
        self.assertFalse(out["safe_for_automatic_quality_promotion"])
        self.assertIn("confirmed_events_without_documented_evidence", out["errors"])

    def test_future_dated_source_blocks_automatic_promotion(self):
        out = analyze([row(fonte_aggiornata_il="2027-10-12")], TODAY)
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
        inputs = [row("x"), row("y", fonte_aggiornata_il="2020-01-01")]
        one = analyze(inputs, TODAY)
        two = analyze(inputs, TODAY)
        self.assertEqual(one, two)
        self.assertEqual(inputs[0]["verificato_il"], "")

    def test_duplicate_record_ids_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            analyze([row("dup"), row("dup")], TODAY)

    def test_recent_import_and_read_do_not_refresh_publisher_content_age(self):
        records = [
            row("old", fonte_aggiornata_il="2020-01-01",
                importato_il="2026-10-12T09:00:00+00:00", fonte_letta_il="2026-10-12"),
            row("unknown", fonte_aggiornata_il="", aggiornato_il="2026-10-12T09:00:00",
                importato_il="2026-10-12T09:00:00+00:00", fonte_letta_il="2026-10-12"),
        ]
        before = deepcopy(records)
        out = analyze(records, TODAY)
        m = out["metrics"]
        self.assertEqual(m["import_within_30d"], 2)
        self.assertEqual(m["source_read_within_30d"], 2)
        self.assertEqual(m["source_date_outside_limit"], 1)
        self.assertEqual(m["source_date_unknown"], 1)
        self.assertEqual(m.get("source_date_within_30d", 0), 0)
        self.assertEqual(m["forecast_from_stale_or_unknown_source"], 2)
        self.assertEqual(m["without_documented_verification"], 2)
        self.assertEqual(records, before)

    def test_legacy_dates_and_generic_dataset_markers_are_unknown(self):
        records = [
            row("plain", fonte_aggiornata_il=""),
            row("timestamp", fonte_aggiornata_il="", aggiornato_il="2026-10-12T01:00:00"),
            row("dataset", fonte_aggiornata_il="", aggiornamento_ambito="dataset"),
            row("future_import", fonte_aggiornata_il="", aggiornato_il="2030-01-01T01:00:00"),
        ]
        out = analyze(records, TODAY)
        self.assertEqual(out["metrics"]["source_date_unknown"], 4)
        self.assertEqual(out["metrics"]["legacy_update_timestamp_without_source_date"], 4)
        self.assertEqual(out["metrics"].get("recent_dataset_only_update", 0), 0)
        self.assertEqual(out["metrics"].get("future_dated_source", 0), 0)
        self.assertTrue(out["safe_for_automatic_quality_promotion"])

    def test_reviewed_legacy_dataset_remains_dataset_evidence_only(self):
        out = analyze([row(
            "lo-mercap-123", fonte_aggiornata_il="", aggiornato_il="2026-10-06",
            aggiornamento_ambito="dataset", url_fonte="https://www.dati.lombardia.it/d/68zx-njaw",
        )], TODAY)
        m = out["metrics"]
        self.assertEqual(m["source_date_from_reviewed_legacy_dataset"], 1)
        self.assertEqual(m["recent_dataset_only_update"], 1)
        self.assertEqual(m["without_documented_verification"], 1)
        self.assertEqual(out["field_evidence"]["metrics"].get("markets_with_recent_field_evidence", 0), 0)

    def test_recent_global_metadata_does_not_date_unknown_market_sources(self):
        out = analyze([row(fonte_aggiornata_il="")], TODAY, {
            "schema": 1, "market_imports": 0,
            "source_evidence": [{"publisher": "Comune", "status": "metadata_checked",
                                 "publisher_data_updated_at": "2026-10-12"}],
        })
        self.assertEqual(out["metrics"]["source_date_unknown"], 1)
        self.assertEqual(out["metrics"].get("source_date_within_30d", 0), 0)
        self.assertEqual(out["publisher_evidence"][0]["market_records_verified_by_metadata"], 0)

    def test_all_sources_and_fields_share_the_full_catalog_denominator(self):
        records = [row(str(n), fonte=f"Fonte {n:02}", url_fonte=f"https://source{n}.example/m",
                       fonte_aggiornata_il="" if n % 2 else "2026-10-11") for n in range(20)]
        records.extend([row("missing", url_fonte=""), row("invalid", url_fonte="https://[invalid")])
        before = deepcopy(records)
        out = analyze(records, TODAY)
        self.assertEqual(out["metrics"]["total"], 22)
        self.assertEqual(len(out["source_domains_top"]), 12)
        self.assertEqual(sum(x["metrics"]["total"] for x in out["source_summaries"]), 22)
        self.assertEqual(sum(out["source_content_age_states"].values()), 22)
        self.assertEqual(out["field_evidence"]["metrics"]["markets"], 22)
        self.assertEqual(sum(x["markets"] for x in out["field_evidence"]["publishers"]), 22)
        self.assertNotIn("markets", out["field_evidence"])
        self.assertIn("Fonte 19", markdown(out))
        self.assertEqual(records, before)

    def test_unknown_source_age_is_reported_even_without_forecast_dates(self):
        out = analyze([row(fonte_aggiornata_il="", date=[], date_quality="sconosciuta")], TODAY)
        self.assertIn("source_content_dates_are_unproven", out["warnings"])
        self.assertEqual(out["metrics"]["source_date_unknown"], 1)
        self.assertEqual(out["metrics"].get("forecast_from_stale_or_unknown_source", 0), 0)

    def test_custom_source_age_limit_still_flags_a_known_recent_bucket(self):
        out = analyze([row(fonte_aggiornata_il="2026-08-12")], TODAY, max_source_age_days=30)
        self.assertEqual(out["metrics"]["source_date_31_to_90d"], 1)
        self.assertEqual(out["metrics"]["source_date_outside_limit"], 1)
        self.assertEqual(out["metrics"]["forecast_from_stale_or_unknown_source"], 1)


if __name__ == "__main__":
    unittest.main()
