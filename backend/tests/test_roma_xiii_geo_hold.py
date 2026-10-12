import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from roma_xiii_geo_hold import (
    apply_holds,verify_diff,validated_map,git_blob_sha,CASES,SOURCE_GIT_BLOB_SHA,
    ORIGINAL_POINT,ORIGINAL_URL,
)
from reviewed_city_evidence import NAVIGATION_HOLD,COORD_HOLD
from export_static import export
from roma_xiii_geo_hold import verify_static
from datetime import date

SOURCE_FILE=Path(__file__).resolve().parents[1]/"data/roma-municipio-xiii-market-map-reviewed.json"
SOURCE=json.loads(SOURCE_FILE.read_text("utf-8"))


def row(slug):
    return {
        "slug":slug,"nome":CASES[slug]["name"],"indirizzo":CASES[slug]["street"],
        "regione":"Lazio","citta":"Roma","provincia":"RM",
        "url_fonte":ORIGINAL_URL,"fonte":"Roma Capitale historic source",
        "lat":41.9,"lng":12.5,"position_quality":"non_verificata",
        "verificato_il":"","status":"non_confermato",
        "date_quality":"sconosciuta","date":[],
        "categoria":"misto","orario_testo":"","ricorrenza_testo":"",
    }


class RomeGeoSafetyTests(unittest.TestCase):
    def test_original_source_approved_2024_map_is_immutable(self):
        self.assertEqual(git_blob_sha(SOURCE_FILE),SOURCE_GIT_BLOB_SHA)
        self.assertEqual(set(validated_map(SOURCE)),set(["rm13-0"+str(i) for i in range(1,10)]))

    def test_only_two_exact_wrong_indicative_coordinates_suspended(self):
        rows=[row(k) for k in CASES]
        preserved=copy.deepcopy(rows)
        result,report=apply_holds(rows,SOURCE,apply=True)
        self.assertEqual(report["new_coordinates_quarantined"],2)
        self.assertEqual(report["new_directions_blocked"],2)
        self.assertEqual({x["slug"] for x in result},{x["slug"] for x in rows})
        self.assertEqual(rows,preserved)
        proof=verify_diff(rows,result,report,SOURCE)
        self.assertTrue(proof["release_safe"])
        for before,after in zip(rows,result):
            self.assertIsNone(after["lat"])
            self.assertIsNone(after["lng"])
            self.assertEqual(after["coordinate_originali"],ORIGINAL_POINT)
            self.assertEqual(after["coordinate_sospese_motivo"],COORD_HOLD)
            self.assertEqual(after["navigazione_sospesa_motivo"],NAVIGATION_HOLD)
            for field in ("slug","nome","citta","regione","indirizzo","url_fonte",
                          "date_quality","date","status","verificato_il"):
                self.assertEqual(before[field],after[field])

    def test_replay_does_not_duplicate_suspensions(self):
        rows=[row(k) for k in CASES]
        first,_=apply_holds(rows,SOURCE,apply=True)
        second,report=apply_holds(first,SOURCE,apply=True)
        self.assertEqual(first,second)
        self.assertEqual(report["new_coordinates_quarantined"],0)
        self.assertEqual(report["new_directions_blocked"],0)
        self.assertEqual(report["already_quarantined"],2)
        self.assertEqual(verify_diff(first,second,report,SOURCE)["new_coordinate_holds"],0)

    def test_readonly_never_applies_changes(self):
        rows=[row(k) for k in CASES]
        output,report=apply_holds(rows,SOURCE,apply=False)
        self.assertEqual(output,rows)
        self.assertTrue(report["review_only"])
        self.assertEqual(report["changed_ids"],[])

    def test_unrelated_markets_are_unchanged(self):
        other=row("irnerio-roma")
        other["slug"]="other-source"
        rows=[other]+[row(k) for k in CASES]
        fixed,report=apply_holds(rows,SOURCE,apply=True)
        self.assertEqual(fixed[0],rows[0])
        self.assertEqual(report["record_count"],3)

    def test_wrong_geo_and_previously_verified_data_are_held(self):
        for field,value in (
            ("lat",41.91),("lng",12.45),("position_quality","precisa"),
            ("url_fonte","https://example.org/other"),("verificato_il","2026-10-12"),
            ("nome","different"),("indirizzo","Via Altra"),
            ("date_quality","confermata"),("status","attivo"),
        ):
            rows=[row(k) for k in CASES]
            rows[0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                apply_holds(rows,SOURCE,apply=True)

    def test_replaced_evidence_or_wrong_source_location_refused(self):
        wrong=copy.deepcopy(SOURCE)
        wrong["observations"][0]["latitude"]=41.9
        wrong["observations"][0]["longitude"]=12.5
        with self.assertRaisesRegex(ValueError,"does not disprove"):
            apply_holds([row(k) for k in CASES],wrong,apply=True)
        wrong=copy.deepcopy(SOURCE)
        wrong["observations"][0]["source_name"]="Wrong market"
        with self.assertRaisesRegex(ValueError,"Unreviewed Rome source name"):
            apply_holds([row(k) for k in CASES],wrong,apply=True)

    def test_illicit_date_url_or_city_change_rejected_by_diff_guard(self):
        rows=[row(k) for k in CASES]
        revised,report=apply_holds(rows,SOURCE,apply=True)
        for field,value in (
            ("date",["2026-10-24"]),("url_fonte","https://bad.example"),
            ("citta","Other"),("status","attivo"),("nome","Other")
        ):
            bad=copy.deepcopy(revised)
            bad[0][field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,"unapproved source market field"):
                verify_diff(rows,bad,report,SOURCE)

    def test_export_preserves_protected_details_and_compact_index(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as directory:
            import pathlib
            path=pathlib.Path(directory)/"public/data/v1"
            rows=[row(k) for k in CASES]
            rows,_=apply_holds(rows,SOURCE,apply=True)
            export(rows,path,today=date(2026,10,12))
            proof=verify_static(path/"manifest.json",SOURCE)
            self.assertEqual(proof["current_coordinate_holds"],2)
            self.assertEqual(proof["current_navigation_holds"],2)
            self.assertEqual(proof["new_geocodes_added"],0)


if __name__=="__main__":
    unittest.main()
