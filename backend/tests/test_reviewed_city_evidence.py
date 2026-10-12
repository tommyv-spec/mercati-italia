import copy
import json
import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reviewed_city_evidence import (
    apply_reviewed_cities, verify_reviewed_diff, validate_evidence,
    NAVIGATION_HOLD, COORD_HOLD, point_distance_km,
)

ROOT=Path(__file__).resolve().parents[2]
ISTAT=json.loads((ROOT/"backend/data/istat-comuni-2026.json").read_text("utf-8"))
EVIDENCE=json.loads((ROOT/"backend/data/reviewed-city-evidence-2026-10-12.json").read_text("utf-8"))

def sample_data():
    rows=[]
    for c in EVIDENCE["cases"]:
        row={
            "slug":c["slug"],"nome":"Nome del mercatino valido ma non verificato",
            "regione":c["region"],"citta":c["expected_original_city"],
            "provincia":c["expected_original_province"],
            "url_fonte":c["expected_source_url"],
            "fonte":"editore della pagina",
            "lat":c.get("coordinate_reference",{}).get("observed_old_point",[45.4,9.2])[0],
            "lng":c.get("coordinate_reference",{}).get("observed_old_point",[45.4,9.2])[1],
            "position_quality":"indicativa","verificato_il":"",
            "date_quality":"prevista","date":["2026-10-18","2026-10-25"],
            "ricorrenza_testo":"mensile - terza domenica del mese",
            "indirizzo":"indirizzo riportato, da verificare",
            "aggiornato_il":"2026-06-05","completezza":31,
            "status":"non_confermato",
        }
        rows.append(row)
    return rows


class ReviewedCityEvidenceTests(unittest.TestCase):
    def test_manually_reviewed_source_pages_and_istat_province_complete(self):
        verified=validate_evidence(EVIDENCE,ISTAT)
        self.assertEqual(len(verified),13)
        self.assertEqual(sum(bool(x.get("coordinate_reference"))
                             for x in verified.values()),6)
        self.assertEqual({x["target_city"] for x in verified.values()
                          if x["region"]=="Lombardia"},{"Milano","Cernobbio"})

    def test_initial_city_review_and_coordinate_quarantine_is_exact(self):
        rows=sample_data()
        frozen=copy.deepcopy(rows)
        corrected,report=apply_reviewed_cities(rows,ISTAT,EVIDENCE,apply=True)
        self.assertEqual(len(corrected),len(rows))
        self.assertEqual(report["counts"]["city_fixed"],13)
        self.assertEqual(report["counts"]["coordinates_quarantined"],6)
        self.assertEqual(report["counts"]["navigation_hold_added"],13)
        self.assertEqual({r["slug"] for r in corrected},{r["slug"] for r in rows})
        approved=verify_reviewed_diff(rows,corrected,report,ISTAT,EVIDENCE)
        self.assertEqual(approved["cities_corrected"],13)
        self.assertEqual(approved["unsafe_points_suppressed"],6)
        for before,after in zip(rows,corrected):
            self.assertEqual(after["date"],before["date"])
            self.assertEqual(after["ricorrenza_testo"],before["ricorrenza_testo"])
            self.assertEqual(after["verificato_il"],before["verificato_il"])
            self.assertEqual(after["status"],before["status"])
            self.assertEqual(after["url_fonte"],before["url_fonte"])
            self.assertEqual(after["aggiornato_il"],before["aggiornato_il"])
            self.assertEqual(after["navigazione_sospesa_motivo"],NAVIGATION_HOLD)
            if before["slug"] in {x["slug"] for x in EVIDENCE["cases"]
                                  if x.get("coordinate_reference")}:
                self.assertIsNone(after["lat"])
                self.assertIsNone(after["lng"])
                self.assertEqual(after["coordinate_sospese_motivo"],COORD_HOLD)
                self.assertEqual(after["coordinate_originali"],
                                 {"lat":before["lat"],"lng":before["lng"]})
            else:
                self.assertEqual((after["lat"],after["lng"]),
                                 (before["lat"],before["lng"]))
        self.assertEqual(rows,frozen)

    def test_no_changes_when_replayed_with_same_sources(self):
        initial,_=apply_reviewed_cities(sample_data(),ISTAT,EVIDENCE,apply=True)
        again,report=apply_reviewed_cities(initial,ISTAT,EVIDENCE,apply=True)
        self.assertEqual(initial,again)
        self.assertEqual(report["counts"]["city_fixed"],0)
        self.assertEqual(report["counts"]["coordinates_quarantined"],0)
        self.assertEqual(report["counts"]["navigation_hold_added"],0)
        self.assertEqual(report["counts"]["unchanged_already_reviewed"],13)
        self.assertEqual(verify_reviewed_diff(initial,again,report,ISTAT,EVIDENCE)["cities_corrected"],0)

    def test_read_only_mode_never_changes_market(self):
        source=sample_data()
        copied=copy.deepcopy(source)
        result,report=apply_reviewed_cities(source,ISTAT,EVIDENCE,apply=False)
        self.assertEqual(result,copied)
        self.assertTrue(report["review_only"])
        self.assertEqual(report["counts"]["city_fixed"],0)

    def test_untested_source_or_old_city_blocks_pipeline(self):
        for field,value in (("url_fonte","https://evil.example/unknown"),
                            ("citta","Unrelated municipality"),
                            ("provincia","XX")):
            data=sample_data()
            data[0][field]=value
            with self.assertRaisesRegex(ValueError,"since manual review|Unreviewed"):
                apply_reviewed_cities(data,ISTAT,EVIDENCE,apply=True)

    def test_duplicate_or_wrong_istat_data_prevents_all_changes(self):
        with self.assertRaisesRegex(ValueError,"repeated|Repeated|missing"):
            rows=sample_data()
            apply_reviewed_cities(rows+[rows[0]],ISTAT,EVIDENCE,apply=True)
        bad=copy.deepcopy(ISTAT)
        bad["source_file_sha256"]="0"*64
        with self.assertRaises(ValueError):
            apply_reviewed_cities(sample_data(),bad,EVIDENCE,apply=True)

    def test_coordinate_reference_must_prove_bad_point_not_new_geocode(self):
        bad=copy.deepcopy(EVIDENCE)
        geo=next(x for x in bad["cases"] if x.get("coordinate_reference"))["coordinate_reference"]
        geo["latitude"],geo["longitude"]=geo["observed_old_point"]
        with self.assertRaisesRegex(ValueError,"not disproved"):
            validate_evidence(bad,ISTAT)
        data=sample_data()
        lon=next(x for x in data if x["slug"]=="cernobbio-mercatino-delle-curiosita-mercatino-delle-curiosita")
        lon["lat"]=45.84108
        lon["lng"]=9.06704
        with self.assertRaisesRegex(ValueError,"Map coordinates changed"):
            apply_reviewed_cities(data,ISTAT,EVIDENCE,apply=True)

    def test_compromised_output_is_rejected_by_independent_field_guard(self):
        old=sample_data()
        fixed,report=apply_reviewed_cities(old,ISTAT,EVIDENCE,apply=True)
        for field,bad_value in [
            ("date",["2026-12-01"]),
            ("url_fonte","https://fake.example"),
            ("verificato_il","2026-10-12"),
            ("status","attivo"),
            ("nome","Changed event title"),
        ]:
            corrupt=copy.deepcopy(fixed)
            corrupt[0][field]=bad_value
            with self.assertRaisesRegex(ValueError,"Unapproved market field modified"):
                verify_reviewed_diff(old,corrupt,report,ISTAT,EVIDENCE)

    def test_province_and_valid_municipality_are_source_bound(self):
        new=copy.deepcopy(EVIDENCE)
        new["cases"][0]["target_istat_province"]="BA"
        with self.assertRaisesRegex(ValueError,"ISTAT"):
            validate_evidence(new,ISTAT)
        new=copy.deepcopy(EVIDENCE)
        new["cases"][0]["expected_source_url"]="http://local.invalid"
        with self.assertRaisesRegex(ValueError,"Unreviewed"):
            validate_evidence(new,ISTAT)

    def test_vetted_geolocation_outliers_are_not_slight_rounding_errors(self):
        self.assertGreater(point_distance_km((45.44,12.32),(45.3539721,10.7364908)),100)
        self.assertGreater(point_distance_km((41.13,16.87),(40.14789,18.48682)),100)


if __name__=="__main__":
    unittest.main()
