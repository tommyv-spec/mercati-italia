import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from roma_xiii_2026_venues import (
    EXPECTED,EXPECTED_EXISTING,EVIDENCE_FILE,validate_manifest,
    integrate,validate_added,make_market,checksum,venue_clash,
    DOC_2026,DOC_MOVE,
)
from recurrence_refresh import refresh_records
from export_static import export
from merge_catalog import load_existing

EVIDENCE=json.loads(EVIDENCE_FILE.read_text("utf-8"))
TODAY=date(2026,10,13)


def plateatico(sid,street):
    return {
        "slug":sid,
        "nome":sid.replace("-roma","").title(),
        "citta":"Roma","provincia":"RM","regione":"Lazio",
        "indirizzo":street,"url_fonte":"https://dati.comune.roma.it/catalog/dataset/d881",
        "date":[],"date_quality":"sconosciuta","verificato_il":"",
        "categoria":"misto","status":"non_confermato",
        "lat":None,"lng":None,"position_quality":"sconosciuta",
    }


def baseline():
    return [plateatico(sid,street) for sid,street in EXPECTED_EXISTING.items()]


class Rome2026MarketsTests(unittest.TestCase):
    def test_municipality_documented_eight_distinct_entities_five_candidates(self):
        approved=validate_manifest(EVIDENCE)
        self.assertEqual(len(approved),5)
        self.assertEqual(len(EVIDENCE["entities"]),8)
        self.assertEqual(len({v["canonical_id"] for v in EVIDENCE["entities"]}),8)
        self.assertEqual(approved["rm13-salt-fogaccia-sabato"]["source_day_numbers"],[5])
        self.assertNotIn("rm13-salt-fogaccia-martedi",approved)
        self.assertEqual(
            next(x for x in EVIDENCE["entities"] if x["canonical_id"]=="pineta-sacchetti-urbano-ii")["record_status"],
            "quarantine_only")
        self.assertEqual(EVIDENCE["direct_pdf_2026"],DOC_2026)

    def test_true_additions_are_cautious_and_preserve_old_source_ids(self):
        old=baseline()
        frozen=copy.deepcopy(old)
        out,report=integrate(old,EVIDENCE,apply=True,today=TODAY)
        self.assertEqual(len(out),7)
        self.assertEqual(len(report["new_market_ids"]),5)
        self.assertEqual(report["new_market_count"],5)
        self.assertEqual(report["existing_records_changed"],0)
        self.assertEqual(out[:2],old)
        self.assertEqual(old,frozen)
        cert=validate_added(old,out,report,EVIDENCE)
        self.assertEqual(cert["approved_official_market_additions"],5)
        self.assertEqual(cert["verified_events_created"],0)
        self.assertEqual(cert["precise_geocodes_created"],0)
        self.assertEqual(cert["directions_activated"],0)
        self.assertTrue(all(x["lat"] is None and x["lng"] is None for x in out[2:]))
        self.assertTrue(all(x["date"]==[] and x["date_quality"]=="sconosciuta" for x in out[2:]))
        self.assertTrue(all(x["verificato_il"]=="" and x["status"]=="non_confermato" for x in out[2:]))

    def test_four_weekly_regulations_are_predictions_never_confirmations(self):
        old=baseline()
        initial,_=integrate(old,EVIDENCE,apply=True,today=TODAY)
        changed,summary=refresh_records(initial,TODAY,120,540)
        new={x["slug"]:x for x in changed if x["slug"] in EXPECTED}
        self.assertEqual(len(new),5)
        self.assertEqual(sum(x["date_quality"]=="prevista" for x in new.values()),4)
        self.assertEqual(new["rm13-plateatico-san-silverio"]["date"],[])
        for sid,v in new.items():
            self.assertFalse(v["verificato_il"])
            self.assertNotEqual(v["date_quality"],"confermata")
            self.assertIn("non conferm",v["descrizione"].casefold())
            if EXPECTED[sid]["weekdays"]:
                self.assertTrue(len(v["date"])>=12)
                self.assertEqual({date.fromisoformat(x).weekday() for x in v["date"]},
                                 set(EXPECTED[sid]["weekdays"]))

    def test_second_day_rollover_is_idempotent_and_preserves_prior_records(self):
        first,_=integrate(baseline(),EVIDENCE,apply=True,today=TODAY)
        projected,_=refresh_records(first,TODAY,120,540)
        second,report=integrate(projected,EVIDENCE,apply=True,today=TODAY)
        self.assertEqual(second,projected)
        self.assertEqual(report["already_published_curated_ids"],sorted(EXPECTED))
        self.assertEqual(report["records_added"],0)
        self.assertEqual(report["new_market_ids"],[])

    def test_dry_run_never_edits_or_adds_market(self):
        old=baseline();original=copy.deepcopy(old)
        out,report=integrate(old,EVIDENCE,apply=False,today=TODAY)
        self.assertEqual(out,old)
        self.assertEqual(old,original)
        self.assertEqual(report["records_added"],0)
        self.assertEqual(report["review_only_potential_ids"],sorted(EXPECTED))
        self.assertTrue(report["review_only"])

    def test_conflict_same_street_and_name_does_not_create_sixth_market(self):
        old=baseline()
        city=make_market(validate_manifest(EVIDENCE)["rm13-salt-valle-aurelia"])
        copy_existing={**city,"slug":"legacy-valle-aurelia"}
        with self.assertRaisesRegex(ValueError,"venue collision"):
            integrate(old+[copy_existing],EVIDENCE,apply=True,today=TODAY)
        # Piazza Ormea != the plateatico at Via Borgo Ticino, even though
        # both official documents use the word "Casalotti".
        new=make_market(validate_manifest(EVIDENCE)["rm13-salt-casalotti-ormea"])
        self.assertIsNone(venue_clash(old,new))

    def test_unreviewed_publisher_2026_source_data_fails_closed(self):
        for field,value in (
            ("direct_pdf_2026","https://other.example/markets.pdf"),
            ("approved_new_venue_candidates",6),
            ("expected_physical_market_identities",9)
        ):
            altered=copy.deepcopy(EVIDENCE);altered[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                validate_manifest(altered)
        altered=copy.deepcopy(EVIDENCE)
        for entry in altered["entities"]:
            if entry.get("slug")=="rm13-salt-fogaccia-sabato":
                entry["source_day_numbers"]=[1,5]
        with self.assertRaisesRegex(ValueError,"differs"):
            validate_manifest(altered)

    def test_tuesday_fogaccia_one_stall_is_never_published(self):
        cases=validate_manifest(EVIDENCE)
        sat=make_market(cases["rm13-salt-fogaccia-sabato"])
        self.assertEqual(sat["date"],[])
        self.assertIn("only the saturday venue",sat["descrizione"].lower())
        self.assertEqual(cases["rm13-salt-fogaccia-sabato"]["quarantined_other_day"]["evidence_url"],DOC_MOVE)

    def test_new_venues_never_override_historic_Casalotti_or_Irnerio(self):
        old=baseline()
        old[0]["indirizzo"]="Via Ovada"
        with self.assertRaisesRegex(ValueError,"Existing Rome plateatico"):
            integrate(old,EVIDENCE,apply=True,today=TODAY)
        out,_=integrate(baseline(),EVIDENCE,apply=True,today=TODAY)
        bad=copy.deepcopy(out);bad[0]["url_fonte"]="https://other.example"
        _,report=integrate(baseline(),EVIDENCE,apply=True,today=TODAY)
        with self.assertRaisesRegex(ValueError,"changed existing market"):
            validate_added(baseline(),bad,report,EVIDENCE)

    def test_full_static_export_and_reimport_preserve_all_source_fields(self):
        approved=validate_manifest(EVIDENCE)
        rows=[make_market(approved[sid]) for sid in sorted(approved)]
        with TemporaryDirectory() as tmp:
            path=Path(tmp)/"public/data/v1"
            export(rows,path,today=TODAY)
            from validate_static import validate
            validate(path/"manifest.json")
            stored=load_existing(path/"manifest.json")
            self.assertEqual(len(stored),5)
            self.assertTrue(all(x["navigazione_sospesa_motivo"] for x in stored))
            self.assertTrue(all(x["url_fonte"] and x["id_fonte"] for x in stored))
            self.assertTrue(all(not x["verificato_il"] for x in stored))

if __name__=="__main__":
    unittest.main()
