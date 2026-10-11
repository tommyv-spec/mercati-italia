import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from source_scout import candidate, discover
from autopilot_feedback import opportunities, as_markdown


class SourceScoutTests(unittest.TestCase):
    def test_structured_municipal_csv_with_open_license_is_candidate_not_auto_imported(self):
        source={
            "id":"dataset-mercati-xx","title":"Mercati settimanali scoperti di Milano",
            "license_title":"Creative Commons Attribution CC BY 4.0",
            "organization":{"title":"Comune di Milano"},
            "metadata_modified":"2026-09-25T12:00:00",
            "resources":[{"format":"CSV","url":"https://dati.comune.milano.it/some.csv",
                          "name":"Mercati e giornate"}],
        }
        result=candidate(source)
        self.assertTrue(result)
        self.assertFalse(result["automatic_import_allowed"])
        self.assertEqual(result["resources"][0]["format"],"CSV")
        self.assertEqual(result["license_status"],"claimed_open_license_review_required")
        self.assertGreater(result["score"],10)

    def test_harvest_timestamp_is_not_dataset_freshness(self):
        row = {
            "id": "metadata-not-data",
            "title": "Mercati settimanali Firenze",
            "license_title": "CC BY 4.0",
            "metadata_modified": "2026-10-12T12:00:00",
            "resources": [{"format": "CSV", "url": "https://dati.comune.fi.it/mercati.csv"}],
        }
        candidate_only_metadata = candidate(row)
        candidate_with_data_date = candidate({**row, "modified": "2026-09-10"})
        self.assertEqual(candidate_only_metadata["data_modified"], "")
        self.assertEqual(candidate_only_metadata["metadata_modified"], "2026-10-12T12:00:00")
        self.assertEqual(candidate_with_data_date["score"] - candidate_only_metadata["score"], 3)

    def test_financial_markets_are_rejected(self):
        self.assertIsNone(candidate({
            "id":"finance","title":"Mercati finanziari e prezzi azioni",
            "resources":[{"format":"CSV","url":"https://dati.gov.it/data.csv"}],
        }))

    def test_unstructured_and_insecure_downloads_are_rejected(self):
        base={"id":"mercati","title":"Mercati rionali", "resources":[]}
        self.assertIsNone(candidate(base))
        self.assertIsNone(candidate({**base,"resources":[
            {"format":"CSV","url":"http://example.com/markets.csv"}
        ]}))
        self.assertIsNone(candidate({**base,"resources":[
            {"format":"PDF","url":"https://example.com/markets.pdf"}
        ]}))

    def test_fixture_discovery_deduplicates_catalog_results(self):
        row={
            "id":"fi-market", "title":"Mercati settimanali Firenze",
            "resources":[{"format":"GEOJSON","url":"https://www.dati.gov.it/mock.geojson"}],
        }
        data={"mercati settimanali":[row], "mercati rionali":[row]}
        result=discover(fixtures=data)
        self.assertEqual(len(result["candidates"]),1)
        self.assertFalse(result["candidates"][0]["automatic_import_allowed"])
        self.assertTrue(result["no_unapproved_source_imports"])
        self.assertFalse(result["offline_mode"])
        self.assertFalse(result["truncated"])


class ContinuousImprovementTests(unittest.TestCase):
    def test_priority_roadmap_is_measured_and_does_not_mutate_data(self):
        metrics={
            "snapshot_total":12650,
            "fields_missing":{"hours":10627,"verified_at":12650,
                               "source_url":0},
            "sources":[{"name":"happings.com","count":9647}],
            "position_quality":{"precisa":89},
            "compact_index_future_coverage":{"60":11056},
            "cities_with_variant_spellings":200,
        }
        output=opportunities(metrics)
        codes={issue["code"] for issue in output["queue"]}
        self.assertIn("verified_source_evidence",codes)
        self.assertEqual(output["queue"][0]["code"], "verified_source_evidence",
                         "Never optimize easy date forecasts ahead of missing verification")
        self.assertIn("opening_hours_coverage",codes)
        self.assertIn("location_precision",codes)
        self.assertTrue(output["metrics_are_observed_not_verified_events"])
        self.assertGreaterEqual(len(output["queue"]),6)
        self.assertIn("Criterio di accettazione",as_markdown(output))
        self.assertEqual(metrics["snapshot_total"],12650)

    def test_falling_future_coverage_has_explicit_regression_incident(self):
        current={
            "snapshot_total":100,
            "fields_missing":{"hours":70,"verified_at":100},
            "position_quality":{"precisa":10},
            "compact_index_future_coverage":{"60":3},
        }
        old={"compact_index_future_coverage":{"60":200}}
        result=opportunities(current,old)
        self.assertIn("date_coverage_regression",{x["code"] for x in result["queue"]})


if __name__ == "__main__":
    unittest.main()
