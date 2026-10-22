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

if __name__=="__main__":
    unittest.main()
