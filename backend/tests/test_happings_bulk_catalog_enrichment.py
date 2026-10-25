"""Regression tests for nationwide source-backed Happings field recovery."""
from __future__ import annotations
import copy
import sys
import unittest
from collections import Counter
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import happings_bulk_catalog_enrichment as bulk

DAY=date(2026,10,22)
URL="https://www.happings.com/it/mercati-settimanali-a-savona-e-provincia/"

def base_row(slug="mercato-settimanale-di-albenga-albenga", *, street=""):
    return {"slug":slug,"nome":"Mercato settimanale di Albenga",
            "citta":"Albenga","regione":"Liguria","provincia":"SV",
            "indirizzo":street,"orario_testo":"",
            "ricorrenza_testo":"settimanale - mercoledì",
            "fonte":"happings.com",
            "url_fonte":"https://www.happings.com/it/mercati-settimanali-a-savona.html",
            "fonti":[],"riscontri_campi":[],"verificato_il":"",
            "position_quality":"sconosciuta"}

def fact(place="Via Dalmazia", part="morning_not_clock_hours"):
    return {"url":URL,"html_sha256":"a"*64,"read_on":DAY.isoformat(),
            "daypart":part,"place":place,"has_specific_location":True,
            "calendar_scope":None,"editorial_scope":None}

class BulkFieldTests(unittest.TestCase):
    def test_fill_blank_hours_and_street_from_exact_source(self):
        row=base_row()
        values={"indirizzo":"Via Dalmazia","orario_testo":"La mattina"}
        evidence={"source_url":URL,"source_day":2,
                  "source_html_sha256":"a"*64,"observed_at":DAY.isoformat()}
        changed, held=bulk._update(row,values,evidence,today=DAY)
        self.assertIsNone(held)
        self.assertEqual({key:changed[key] for key in values},values)
        self.assertEqual(row["indirizzo"],"")
        self.assertTrue(any(all(proof.get("valori",{}).get(k)==v
                                for k,v in values.items())
                            for proof in changed["riscontri_campi"]))
        self.assertEqual(changed["verificato_il"],"")

    def test_each_read_restates_a_still_listed_market_without_new_ownership(self):
        from datetime import timedelta
        row=base_row()
        key=bulk.catalog_key(row)
        with patch.object(bulk,"read_weekly_source",return_value=({key:[fact()]},Counter())):
            filled,report=bulk.enrich([row],".",today=DAY)
        self.assertEqual(len(report["changes"]),1)
        week=DAY+timedelta(days=7)
        later={**fact(),"read_on":week.isoformat(),"html_sha256":"b"*64}
        with patch.object(bulk,"read_weekly_source",return_value=({key:[later]},Counter())):
            again,report=bulk.enrich(filled,".",today=week)
            repeat,second=bulk.enrich(again,".",today=week)
        self.assertEqual((report["changes"],len(report["confirmations"])),([],1))
        proofs=[p for p in again[0]["riscontri_campi"] if p["sha256"]=="b"*64]
        self.assertEqual(len(again[0]["riscontri_campi"]),1)
        self.assertEqual(proofs[0]["valori"],{"indirizzo":"Via Dalmazia","orario_testo":"La mattina",
                                              "ricorrenza_testo":"settimanale - mercoledì"})
        self.assertEqual(proofs[0]["campi_gestiti"],["indirizzo","orario_testo"])
        self.assertEqual({k:again[0][k] for k in bulk.FIELDS},{k:filled[0][k] for k in bulk.FIELDS})
        self.assertEqual((repeat,second["confirmations"]),(again,[]))

    def test_conflicting_existing_street_is_never_overwritten(self):
        old=base_row(street="Piazza Don Gnocchi")
        blank=base_row("mercato-settimanale-di-albenga-albenga-mercoledi")
        key=bulk.catalog_key(old)
        self.assertIsNotNone(key)
        with patch.object(bulk,"read_weekly_source",
                          return_value=({key:[fact()]},Counter())):
            candidate, report=bulk.enrich([old,blank],".",today=DAY)
        self.assertEqual(candidate[0]["indirizzo"],old["indirizzo"])
        self.assertEqual(candidate[1]["indirizzo"],"")
        self.assertEqual(candidate[1]["orario_testo"],"La mattina")
        self.assertEqual(report["counts"].get("filled_indirizzo",0),0)

    def test_incompatible_dayparts_do_not_create_hours(self):
        row=base_row()
        key=bulk.catalog_key(row)
        pages=[fact(part="morning_not_clock_hours"),fact(place="Piazza del Popolo",
                                                         part="afternoon_not_clock_hours")]
        with patch.object(bulk,"read_weekly_source",
                          return_value=({key:pages},Counter())):
            candidate, report=bulk.enrich([row],".",today=DAY)
        self.assertEqual(candidate[0]["orario_testo"],"")
        self.assertEqual(report["counts"].get("filled_orario_testo",0),0)

    def test_non_source_market_and_verified_records_stay_protected(self):
        row=base_row()
        verified=copy.deepcopy(row)
        verified["verificato_il"]=DAY.isoformat()
        values={"orario_testo":"La mattina"}
        evidence={"source_url":URL,"source_day":2,
                  "source_html_sha256":"a"*64,"observed_at":DAY.isoformat()}
        result, reason=bulk._update(verified,values,evidence,today=DAY)
        self.assertEqual(result,verified)
        self.assertEqual(reason,"human_verified_record_held")
        other=copy.deepcopy(row)
        other["fonte"]="comune.example"
        key=bulk.catalog_key(other)
        with patch.object(bulk,"read_weekly_source",
                          return_value=({key:[fact()]},Counter())):
            candidate,report=bulk.enrich([other],".",today=DAY)
        self.assertEqual(candidate,[other])
        self.assertEqual(report["counts"].get("updated_records",0),0)

    def test_cut_weekday_is_repaired_only_when_the_page_leaves_one_day(self):
        cut=base_row()
        cut["ricorrenza_testo"]="settimanale - me"
        wednesday=("liguria","SV","albenga",2)
        with patch.object(bulk,"read_weekly_source",
                          return_value=({wednesday:[fact()]},Counter())):
            candidate,_=bulk.enrich([cut],".",today=DAY)
        self.assertEqual(candidate[0]["ricorrenza_testo"],"settimanale - mercoledì")
        self.assertTrue(any(proof["valori"].get("ricorrenza_testo")=="settimanale - mercoledì"
                            for proof in candidate[0]["riscontri_campi"]))
        # "m" fits both Tuesday and Wednesday on the page: no guess.
        cut["ricorrenza_testo"]="settimanale - m"
        pages={wednesday:[fact()],wednesday[:3]+(1,):[fact(place="Via Roma")]}
        with patch.object(bulk,"read_weekly_source",return_value=(pages,Counter())):
            candidate,_=bulk.enrich([cut],".",today=DAY)
        self.assertEqual(candidate[0]["ricorrenza_testo"],"settimanale - m")

    def test_centre_is_recorded_only_for_the_single_listed_market(self):
        row=base_row()
        key=bulk.catalog_key(row)
        centre=fact(place="centro")
        centre["has_specific_location"]=False
        with patch.object(bulk,"read_weekly_source",
                          return_value=({key:[centre]},Counter())):
            candidate,_=bulk.enrich([row],".",today=DAY)
        self.assertEqual(candidate[0]["indirizzo"],"centro")
        with patch.object(bulk,"read_weekly_source",
                          return_value=({key:[centre,fact()]},Counter())):
            candidate,_=bulk.enrich([row],".",today=DAY)
        self.assertEqual(candidate[0]["indirizzo"],"")

    def test_copies_of_one_listed_market_are_soft_merged_stably(self):
        full=base_row(street="Via Dalmazia")
        full["orario_testo"]="La mattina"
        blank=base_row("mercato-settimanale-di-albenga-albenga-mercoledi")
        key=bulk.catalog_key(full)
        one={key:[fact()]}
        with patch.object(bulk,"read_weekly_source",return_value=(one,Counter())):
            first,report=bulk.enrich([full,blank],".",today=DAY)
        self.assertNotIn("duplicato_di",first[0])
        self.assertEqual(first[1]["duplicato_di"],full["slug"])
        self.assertEqual(report["duplicate_markers"],
                         [{"id":blank["slug"],"duplicato_di":full["slug"]}])
        with patch.object(bulk,"read_weekly_source",return_value=(one,Counter())):
            again,report=bulk.enrich(first,".",today=DAY)
        self.assertEqual(again,first)
        self.assertEqual(report["duplicate_markers"],[])

    def test_stale_marker_clears_when_the_page_lists_two_markets(self):
        full=base_row(street="Via Dalmazia")
        blank=dict(base_row("mercato-settimanale-di-albenga-albenga-mercoledi"),
                   duplicato_di=full["slug"])
        two={bulk.catalog_key(full):[fact(),fact(place="Piazza del Popolo")]}
        with patch.object(bulk,"read_weekly_source",return_value=(two,Counter())):
            candidate,report=bulk.enrich([full,blank],".",today=DAY)
        self.assertNotIn("duplicato_di",candidate[1])
        self.assertEqual(report["duplicate_markers"],[{"id":blank["slug"],"duplicato_di":""}])

    def test_unread_page_keeps_markers_unless_the_kept_record_is_gone(self):
        full=base_row(street="Via Dalmazia")
        blank=dict(base_row("mercato-settimanale-di-albenga-albenga-mercoledi"),
                   duplicato_di=full["slug"])
        with patch.object(bulk,"read_weekly_source",return_value=({},Counter())):
            kept,_=bulk.enrich([full,blank],".",today=DAY)
            orphan,_=bulk.enrich([blank],".",today=DAY)
        self.assertEqual(kept[1]["duplicato_di"],full["slug"])
        self.assertNotIn("duplicato_di",orphan[0])

if __name__=="__main__":
    unittest.main()
