import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from bologna_2026_leads import audit, validate_evidence, same_street_only, markdown
from merge_catalog import load_existing

EVIDENCE = json.loads((ROOT / "backend/data/bologna-municipal-leads-2026.json").read_text("utf-8"))
TODAY = date(2026, 10, 12)


def record(slug, street="Via Garibaldi", city="Bologna", region="Emilia-Romagna"):
    return {
        "slug": slug, "nome": "Mercato di prova", "regione": region,
        "citta": city, "indirizzo": street, "date_quality": "prevista",
        "date": ["2026-10-12"], "status": "non_confermato",
    }


class Bologna2026LeadTests(unittest.TestCase):
    def test_four_facts_are_pinned_to_source_without_new_confirmation(self):
        self.assertEqual(len(validate_evidence(EVIDENCE)), 4)
        result = audit([record("one")], EVIDENCE, TODAY)
        self.assertTrue(result["review_only"])
        self.assertEqual(result["pinned_municipal_leads"], 4)
        self.assertEqual(result["planned_market_starts_not_verified"], 2)
        self.assertEqual(result["historically_reported_open_in_june"], 2)
        self.assertEqual(result["without_same_street_record"], 4)
        self.assertEqual(result["market_rows_imported"], 0)
        self.assertEqual(result["calendar_dates_created"], 0)
        self.assertEqual(result["verified_openings_created"], 0)
        self.assertEqual(result["coordinate_points_invented"], 0)

    def test_same_street_is_not_proof_of_same_market(self):
        before=[record("puntoni-vintage", "Piazza Puntoni"),
                record("unrelated", "Via Garibaldi")]
        original=copy.deepcopy(before)
        result=audit(before, EVIDENCE, TODAY)
        self.assertEqual(result["without_same_street_record"], 3)
        self.assertEqual(result["observations"][2]["overlapping_street_count"],1)
        self.assertFalse(result["observations"][2]["catalog_publication_approved"])
        self.assertTrue(same_street_only("Piazza Puntoni","Piazza Puntoni 12"))
        self.assertFalse(same_street_only("Piazza Puntoni","Piazza VIII Agosto"))
        self.assertEqual(before,original)

    def test_different_city_cannot_create_false_venue_match(self):
        result=audit([record("milan-vetulonia", "Via Vetulonia", city="Milano",
                             region="Lombardia")], EVIDENCE, TODAY)
        self.assertEqual(result["bologna_catalog_entries"], 0)
        self.assertEqual(result["without_same_street_record"], 4)

    def test_wrong_rights_or_publication_claim_aborts(self):
        for field,value in [
            ("automatic_import_allowed",True),
            ("reuse_licence_review_required",False),
            ("events_confirmed",1),
            ("market_records_added",1),
            ("coordinates_created",1),
        ]:
            data=copy.deepcopy(EVIDENCE)
            data[field]=value
            with self.subTest(field=field), self.assertRaisesRegex(ValueError,"Unreviewed"):
                validate_evidence(data)

    def test_source_fields_cannot_be_mutated(self):
        for field,value in [
            ("source_edition_status","opened_and_verified"),
            ("weekday","sabato"),
            ("declared_hours","00:00–23:59"),
            ("street","Via inventata"),
            ("ready_for_catalog",True),
        ]:
            data=copy.deepcopy(EVIDENCE)
            data["leads"][2][field]=value
            with self.subTest(field=field), self.assertRaises(ValueError):
                validate_evidence(data)

    def test_catalog_identity_and_dates_are_bounded(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            audit([record("one"),record("one")], EVIDENCE, TODAY)
        with self.assertRaisesRegex(ValueError,"newer than audit"):
            audit([record("one")], EVIDENCE, date(2026, 5, 1))
        with self.assertRaisesRegex(ValueError,"Invalid full market"):
            audit([], EVIDENCE, TODAY)

    def test_real_dev_catalog_invariants(self):
        manifest=ROOT / "public/data/v1/manifest.json"
        if not manifest.is_file():
            self.skipTest("DEV static catalog not mounted")
        rows=load_existing(manifest)
        res=audit(rows,EVIDENCE,TODAY)
        self.assertEqual(res["catalog_ids_preserved"],len(rows))
        self.assertEqual(len(res["observations"]),4)
        self.assertIn("Nessuna",markdown(res) if "Nessuna" in markdown(res) else "Nessuna")


if __name__=="__main__":
    unittest.main()
