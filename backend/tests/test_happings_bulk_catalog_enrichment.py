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

    def test_one_listed_market_is_one_card_across_sources_showing_the_most_detail(self):
        happ=base_row(street="centro"); happ["orario_testo"]="La mattina"
        ees=base_row("mercato-settimanale-di-albenga-ees")
        ees.update(fonte="eventiesagre.it", nome="Mercato Settimanale Di Albenga",
                   ricorrenza_testo="Ogni mercoledì", indirizzo="Via Dalmazia", orario_testo="08:00–13:00",
                   url_fonte="https://www.eventiesagre.it/Mercatini_Filiera+Corta/1_Mercato+Settimanale+Di+Albenga.html")
        key=bulk.catalog_key(happ)
        self.assertEqual(bulk.catalog_key(ees),key)
        with patch.object(bulk,"read_weekly_source",
                          return_value=({key:[fact(place="centro")]},Counter())):
            candidate,report=bulk.enrich([happ,ees],".",today=DAY)
        by={r["slug"]:r for r in candidate}
        self.assertEqual(by[happ["slug"]].get("duplicato_di"),ees["slug"])  # real street + clock hours stay visible
        self.assertNotIn("duplicato_di",by[ees["slug"]])
        self.assertTrue(any(p["valori"].get("ricorrenza_testo")=="Ogni mercoledì"
                            for p in by[ees["slug"]]["riscontri_campi"]))
        self.assertEqual({k:by[ees["slug"]][k] for k in bulk.FIELDS},{k:ees[k] for k in bulk.FIELDS})

    def test_any_source_card_at_the_listed_street_joins_and_the_most_detailed_shows(self):
        happ=base_row(street="Via Dalmazia"); happ["orario_testo"]="La mattina"
        official=base_row("lo-mercap-1-mercoledi")
        official.update(fonte="Regione Liguria", nome="Mercato di Albenga – Via Dalmazia",
                        indirizzo="VIA DALMAZIA, 1", orario_testo="07:00–13:00",
                        ricorrenza_testo="Ogni mercoledì", date=[(DAY.replace(day=28)).isoformat()],
                        url_fonte="https://example.org/mercati.json")
        key=bulk.catalog_key(happ)
        with patch.object(bulk,"read_weekly_source",return_value=({key:[fact()]},Counter())):
            candidate,report=bulk.enrich([happ,official],".",today=DAY)
            undated,_=bulk.enrich([happ,{**official,"date":[]}],".",today=DAY)
        by={r["slug"]:r for r in candidate}
        self.assertEqual(by[happ["slug"]].get("duplicato_di"),official["slug"])
        self.assertEqual(report["counts"]["other_source_same_venue_joined"],1)
        # Never a field change or a Happings proof on the other source's card.
        self.assertEqual(by[official["slug"]],official)
        # A card without upcoming dates stays out: the visible card keeps its dates.
        self.assertFalse(any(r.get("duplicato_di") for r in undated))
        # Never through one member: a held copy at the official street does not pull the
        # official card behind a card the page lists at another street.
        held=base_row("mercato-settimanale-di-albenga-albenga-old",street="VIA DALMAZIA, 1")
        held.update(orario_testo="07:00–13:00",duplicato_di=happ["slug"])
        moved={**happ,"indirizzo":"Via Roma"}
        with patch.object(bulk,"read_weekly_source",return_value=({key:[fact(place="Via Roma")]},Counter())):
            candidate,_=bulk.enrich([moved,held,official],".",today=DAY)
        self.assertNotIn("duplicato_di",{r["slug"]:r for r in candidate}[official["slug"]])

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
        # Another source's generic weekly market on a town/day the page lists once:
        # never a field change, only the page's still-listed proof of its weekday.
        self.assertEqual({k:candidate[0].get(k) for k in bulk.FIELDS},{k:other.get(k) for k in bulk.FIELDS})
        self.assertEqual(report["counts"].get("updated_records",0),0)
        self.assertEqual([c["values"] for c in report["confirmations"]],[{"ricorrenza_testo":other["ricorrenza_testo"]}])
        self.assertEqual(candidate[0]["riscontri_campi"][0]["metodo"],"sede_giorno_provincia")
        # Two markets listed that day: no proof, nothing assumed.
        with patch.object(bulk,"read_weekly_source",
                          return_value=({key:[fact(),fact(place="Piazza del Popolo")]},Counter())):
            candidate,report=bulk.enrich([other],".",today=DAY)
        self.assertEqual(candidate,[other])

    def test_several_listed_markets_prove_the_other_card_whose_street_one_row_names(self):
        other=base_row("mercato-settimanale-di-albenga-ees",street="VIA DALMAZIA, 1")
        other.update(fonte="eventiesagre.it",orario_testo="08:00–13:00",
                     url_fonte="https://www.eventiesagre.it/x/1_Mercato+Settimanale+Di+Albenga.html")
        key=bulk.catalog_key(other)
        two={key:[fact(),fact(place="Piazza del Popolo")]}
        with patch.object(bulk,"read_weekly_source",return_value=(two,Counter())):
            candidate,report=bulk.enrich([other],".",today=DAY)
            elsewhere,_=bulk.enrich([{**other,"indirizzo":"Via Roma"}],".",today=DAY)
            afternoon,_=bulk.enrich([{**other,"orario_testo":"14:00–19:00"}],".",today=DAY)
        self.assertEqual([c["values"] for c in report["confirmations"]],[{"ricorrenza_testo":other["ricorrenza_testo"]}])
        self.assertEqual({k:candidate[0].get(k) for k in bulk.FIELDS},{k:other.get(k) for k in bulk.FIELDS})
        self.assertEqual(elsewhere,[{**other,"indirizzo":"Via Roma"}])
        self.assertEqual(afternoon,[{**other,"orario_testo":"14:00–19:00"}])

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


class CutStreetTests(unittest.TestCase):
    def test_a_cut_street_takes_the_one_listed_place_it_begins(self):
        from happings_bulk_catalog_enrichment import cut_place
        card = lambda street: {"indirizzo": street}
        self.assertEqual(cut_place(card("cen"), ["centro"]), "centro")
        self.assertEqual(cut_place(card("Pi"), ["Piazza Vittorio Emanuele", "Via Mazzini"]), "Piazza Vittorio Emanuele")
        for street, places in (("Via Roma", ["Via Roma 12"]),          # a real street is never "cut"
                               ("centro", ["centro storico"]),          # nor the town centre
                               ("Pi", ["Piazza Italia", "Piazza Duomo"]),  # two places fit
                               ("P", ["Piazza Italia", "Via Mazzini"]),    # one letter among several
                               ("Via", ["Mercato Nord"])):              # nothing fits
            with self.subTest(street=street):
                self.assertIsNone(cut_place(card(street), places))
