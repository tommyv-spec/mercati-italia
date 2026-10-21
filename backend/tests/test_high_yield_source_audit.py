"""Contract tests: high-yield source research must not become data admission."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from high_yield_source_audit import analyze, markdown

REGISTRY = json.loads((ROOT / "backend/data/high-yield-source-leads-2026-10-17.json").read_text("utf-8"))
COVERAGE = json.loads((ROOT / "reports/automation/data-coverage.json").read_text("utf-8"))


class HighYieldResearchTests(unittest.TestCase):
    def test_reviewed_lead_list_is_read_only_and_uses_old_gaps_as_upper_bound(self):
        result = analyze(REGISTRY, COVERAGE)
        self.assertEqual(len(result["sources"]), 8)
        self.assertEqual(result["markets_imported"], 0)
        self.assertEqual(result["markets_updated"], 0)
        self.assertEqual(result["openings_confirmed"], 0)
        veneto = next(x for x in result["sources"]
                      if x["id"] == "veneto-regional-calendar-2026")
        gaps = veneto["gap_upper_bounds_not_measured_matches"]
        # This is a dated data-coverage snapshot, not an immutable fixture.
        # Validate exact source-to-report mapping instead of stale totals.
        veneto_snapshot = next(x for x in COVERAGE["by_region"] if x["region"] == "Veneto")
        self.assertEqual(gaps["baseline_records_in_region"], veneto_snapshot["records"])
        self.assertEqual(gaps["missing_hours_in_region"], veneto_snapshot["missing_hours"])
        self.assertEqual(gaps["missing_addresses_in_region"], veneto_snapshot["missing_address"])
        self.assertLessEqual(gaps["missing_hours_in_region"], gaps["baseline_records_in_region"])
        self.assertIsNone(veneto["verified_matches"])
        lombardia = next(x for x in result["sources"]
                         if x["id"] == "lombardia-mercap")
        self.assertTrue(lombardia["already_has_connector"])
        lombardia_snapshot = next(x for x in COVERAGE["by_region"] if x["region"] == "Lombardia")
        self.assertEqual(lombardia["gap_upper_bounds_not_measured_matches"]["missing_hours_in_region"],
                         lombardia_snapshot["missing_hours"])
        coldiretti = next(x for x in result["sources"]
                          if x["id"] == "campagna-amica-markets")
        self.assertIsNone(coldiretti["gap_upper_bounds_not_measured_matches"])
        self.assertIn("rights_status", coldiretti)
        text = markdown(result)
        self.assertIn("non", text)
        self.assertIn(str(veneto_snapshot["missing_hours"]), text)

    def test_cannot_enable_import_approval_from_research_metadata(self):
        bad = copy.deepcopy(REGISTRY)
        bad["automatic_import_allowed"] = True
        with self.assertRaises(ValueError):
            analyze(bad, COVERAGE)
        bad = copy.deepcopy(REGISTRY)
        bad["sources"][0]["automatic_import_allowed"] = True
        with self.assertRaises(ValueError):
            analyze(bad, COVERAGE)
        bad = copy.deepcopy(REGISTRY)
        bad["sources"][0]["publication_mode"] = "approved_dev_only"
        with self.assertRaises(ValueError):
            analyze(bad, COVERAGE)

    def test_repeated_or_unbounded_or_unsafe_sources_are_rejected(self):
        bad = copy.deepcopy(REGISTRY)
        bad["sources"].append(copy.deepcopy(bad["sources"][0]))
        with self.assertRaises(ValueError):
            analyze(bad, COVERAGE)
        bad = copy.deepcopy(REGISTRY)
        bad["sources"][0]["url"] = "http://127.0.0.1/internal"
        with self.assertRaises(ValueError):
            analyze(bad, COVERAGE)
        bad = copy.deepcopy(REGISTRY)
        bad["sources"][0]["field_targets"].append("verified_2026_opening")
        with self.assertRaises(ValueError):
            analyze(bad, COVERAGE)

    def test_no_nationwide_source_is_assumed_to_cover_all_cities(self):
        bad = copy.deepcopy(REGISTRY)
        candidate = next(x for x in bad["sources"]
                         if x["id"] == "campagna-amica-markets")
        candidate["region"] = "Lombardia"
        with self.assertRaises(ValueError):
            analyze(bad, COVERAGE)

    def test_coverage_report_must_not_claim_a_market_import(self):
        bad = copy.deepcopy(COVERAGE)
        bad["market_updates_applied"] = 1
        with self.assertRaises(ValueError):
            analyze(REGISTRY, bad)


if __name__ == "__main__":
    unittest.main()
