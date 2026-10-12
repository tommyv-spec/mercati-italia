import copy
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from milano_2026_overlay import (
    reconcile, verified_pairs, PDF_DATE, OLD_DATASET,
    PDF_DOCUMENT, OFFICIAL_PDF_SOURCE, HOLD_MARKETS,
)
from recurrence_refresh import refresh_records, explicit_rule

ROOT=Path(__file__).resolve().parents[1]
PDF=json.loads((ROOT/"data/milano-mss-oct2026-observations.json").read_text("utf-8"))
GIS=json.loads((ROOT/"data/milano-mss-gis-reviewed.json").read_text("utf-8"))


def existing(ident, days="Ogni martedì, sabato"):
    return {
        "slug":f"mi-mss-{ident}", "nome":"Mercato di Papiniano",
        "citta":"Milano","provincia":"MI","regione":"Lombardia",
        "url_fonte":OLD_DATASET,"fonte":"Comune di Milano - Open Data (CC BY 4.0)",
        "aggiornato_il":"2024-05-27", "ricorrenza_testo":days,
        "orario_testo":"", "date":[], "date_quality":"sconosciuta",
        "status":"non_confermato", "verificato_il":"",
        "indirizzo":"Via Papiniano", "lat":45.45,"lng":9.18,
        "position_quality":"non_verificata",
    }


class MilanoCrossPublisherTests(unittest.TestCase):
    def test_real_2026_pdf_and_gis_identifiers_reconcile_without_guessing_eight_new_markets(self):
        matched, report=verified_pairs(PDF,GIS)
        self.assertEqual(report["gis_market_ids"],84)
        self.assertEqual(report["pdf_weekday_rows"],87)
        self.assertEqual(report["pdf_distinct_name_labels"],80)
        self.assertGreaterEqual(len(matched),65)
        self.assertEqual(report["future_events_confirmed"],0)
        self.assertEqual(report["net_new_market_ids_authorized"],0)
        self.assertEqual(matched[1],[1,5])
        self.assertNotIn(2,matched,"Ciccotti construction ambiguity must remain on hold")

    def test_papiniano_dual_source_refresh_is_predicted_never_confirmed(self):
        base=[existing(1)]
        freeze=copy.deepcopy(base)
        future, report=reconcile(base,PDF,GIS,today=date(2026,10,12),apply=True)
        self.assertEqual(len(report["modified_ids"]),1)
        self.assertEqual(future[0]["slug"],base[0]["slug"])
        self.assertEqual(future[0]["aggiornato_il"],"2026-10-01")
        self.assertEqual(future[0]["aggiornamento_ambito"],"dataset")
        self.assertEqual(explicit_rule(future[0]["ricorrenza_testo"])["weekdays"],[1,5])
        self.assertIn(OFFICIAL_PDF_SOURCE,future[0]["fonti"])
        for k in ("nome","citta","lat","lng","orario_testo","verificato_il",
                  "url_fonte","status","indirizzo","date_quality"):
            self.assertEqual(future[0][k],freeze[0][k])
        projections, reason=refresh_records(future,date(2026,10,12),120,540)
        self.assertEqual(reason["all_dates_marked_forecast"],True)
        self.assertEqual(projections[0]["date_quality"],"prevista")
        self.assertGreater(len(projections[0]["date"]),12)
        self.assertEqual(base,freeze)

    def test_reported_market_is_not_new_id_and_no_fuzzy_merge(self):
        base=[existing(1),{**existing(1),"slug":"legacy-elsewhere",
                              "url_fonte":"https://other.example/market"}]
        future,report=reconcile(base,PDF,GIS,today=date(2026,10,12),apply=True)
        self.assertEqual(len(future),2)
        self.assertEqual(report["records_added"],0)
        self.assertEqual(report["records_deleted"],0)
        self.assertEqual(future[1],base[1])

    def test_replay_is_idempotent_with_documented_source(self):
        old=[existing(1)]
        first,_=reconcile(old,PDF,GIS,today=date(2026,10,12),apply=True)
        second,report=reconcile(first,PDF,GIS,today=date(2026,10,13),apply=True)
        self.assertEqual(first,second)
        self.assertEqual(report["modified_ids"],[])

    def test_conflicting_old_weekday_is_held_and_not_overwritten(self):
        old=[existing(1,"Ogni domenica")]
        later,report=reconcile(old,PDF,GIS,today=date(2026,10,12),apply=True)
        self.assertEqual(later,old)
        self.assertEqual(report["counts"]["held_existing_weekday_conflict"],1)

    def test_past_sourced_pdf_never_generates_unbounded_forecasts(self):
        late=PDF_DATE+timedelta(days=541)
        old=[existing(1)]
        later,report=reconcile(old,PDF,GIS,today=late,apply=True)
        self.assertEqual(later,old)
        self.assertEqual(report["counts"]["held_stale_oct2026_pdf"],1)

    def test_unknown_municipal_id_fails_without_touching_source(self):
        r=existing(1)
        r["citta"]="Pisa"
        with self.assertRaisesRegex(ValueError,"conflicting publisher"):
            reconcile([r],PDF,GIS,today=date(2026,10,12),apply=True)
        r=existing(9999)
        out,report=reconcile([r],PDF,GIS,today=date(2026,10,12),apply=True)
        self.assertEqual(out,[r])
        self.assertEqual(report["modified_ids"],[])

    def test_previously_confirmed_or_human_verified_is_untouched(self):
        for override in ({"date_quality":"confermata"},
                         {"verificato_il":"2026-10-11"},{"status":"annullato"}):
            old={**existing(1),**override}
            out,_=reconcile([old],PDF,GIS,today=date(2026,10,12),apply=True)
            self.assertEqual(out,[old])

    def test_bad_publisher_data_and_mismatched_days_fail_closed(self):
        bad=copy.deepcopy(PDF);bad["publisher_report_url"]="https://example.com/fake"
        with self.assertRaisesRegex(ValueError,"Unreviewed"):
            verified_pairs(bad,GIS)
        bad=copy.deepcopy(GIS);bad["records"][0]["weekdays"]=[6]
        matched,_=verified_pairs(PDF,bad)
        self.assertNotIn(1,matched)
        bad=copy.deepcopy(GIS);bad["records"].append(copy.deepcopy(bad["records"][0]))
        with self.assertRaisesRegex(ValueError,"changed official Milan GIS"):
            verified_pairs(PDF,bad)

    def test_independent_milan_release_guard_rejects_any_unapproved_field(self):
        from milano_2026_release_guard import verify
        old=[existing(1)]
        new,report=reconcile(old,PDF,GIS,today=date(2026,10,12),apply=True)
        proven=verify(old,new,report,PDF,GIS)
        self.assertEqual(proven["milan_source_changes"],1)
        self.assertTrue(proven["release_safe"])
        bad=copy.deepcopy(new)
        bad[0]["lat"]=0
        with self.assertRaisesRegex(ValueError,"Non-source market field"):
            verify(old,bad,report,PDF,GIS)
        bad=copy.deepcopy(new)
        bad[0]["fonti"]=[OFFICIAL_PDF_SOURCE]
        with self.assertRaisesRegex(ValueError,"Original source evidence"):
            verify(old,bad,report,PDF,GIS)

    def test_dry_run_proposes_but_does_not_modify_any_input(self):
        rows=[existing(1)]
        frozen=copy.deepcopy(rows)
        out,report=reconcile(rows,PDF,GIS,today=date(2026,10,12),apply=False)
        self.assertEqual(out,frozen)
        self.assertEqual(report["counts"]["candidate_existing_market_schedules"],1)
        self.assertEqual(report["modified_ids"],[])


if __name__=="__main__":
    unittest.main()
