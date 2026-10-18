"""Validate the Happings weekly-index structure using source-like, offline fixtures."""
from __future__ import annotations
import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from happings_weekly_layout import (
    VENICE_NEW, VENICE_OLD, MAX_HTML_BYTES, parse, compare_saved_markets, verify
)

TODAY=date(2026,10,19)
HTML=b"""
<html><body>
<div class="happings-seo-content">
  <h2>Mercati settimanali nei comuni in provincia di Venezia</h2>
  <h3>Mercati del mercoled&#236; nei comuni di Venezia</h3>
  <ul>
    <li>a Spinea, in Villaggio dei Fiori (la mattina)</li>
    <li>a Dolo, in Piazza San Valentino (la mattina)</li>
    <li>a Venezia, in Via Fapanni, Mestre (la mattina)</li>
  </ul>
  <h3>Mercati del sabato nei comuni di Venezia</h3>
  <ul><li>a Spinea, in Piazza Fermi (la mattina)</li></ul>
  <h3>Mercati della domenica nei comuni di Venezia</h3>
  <ul><li>a Mira, in centro (la mattina)</li></ul>
</div>
<div class="footer">
  <h3>Mercati del gioved&#236; nei comuni di Venezia</h3>
  <ul><li>a Spinea, in Via Inventata (la mattina)</li></ul>
</div>
</body></html>
"""

def market(sid,street="",*,city="Spinea",day="mercoledì",url=VENICE_OLD):
    return {
        "slug":sid,"fonte":"happings.com","url_fonte":url,
        "regione":"Veneto","provincia":"VE","citta":city,
        "nome":"Mercato settimanale di "+city,
        "indirizzo":street,"orario_testo":"",
        "ricorrenza_testo":"settimanale - "+day,
        "date_quality":"prevista","date":["2026-10-21"],
        "verificato_il":"",
    }

class HappingsOfflineLayoutTests(unittest.TestCase):
    def test_source_weekdays_real_venice_layout_not_footer(self):
        p=parse(HTML,source_url=VENICE_NEW)
        self.assertEqual(len(p.rows),5)
        self.assertEqual(p.weekday_headings,[2,5,6])
        rows=[x for x in p.rows if x["city_key"]=="spinea"]
        self.assertEqual(len(rows),2)
        wed=next(x for x in rows if x["weekday"]==2)
        self.assertEqual(wed["place"],"Villaggio dei Fiori")
        self.assertEqual(wed["daypart"],"morning_not_clock_hours")
        sat=next(x for x in rows if x["weekday"]==5)
        self.assertEqual(sat["place"],"Piazza Fermi")
        self.assertTrue(wed["has_specific_location"])
        vague=next(x for x in p.rows if x["city_key"]=="mira")
        self.assertFalse(vague["has_specific_location"])

    def test_canonical_and_legacy_page_urls_match_only_source_scoped_records(self):
        rows=[
            market("spinea-1"),
            market("spinea-2","Villaggio dei Fiori"),
            market("spinea-saturday","Piazza Fermi",day="sabato"),
            market("spinea-monday","",day="lunedì"),
            market("dolo-other","",city="Dolo"),
        ]
        before=copy.deepcopy(rows)
        result=compare_saved_markets(rows,HTML,source_url=VENICE_NEW,today=TODAY)
        self.assertTrue(verify(result,len(rows)))
        self.assertEqual(rows,before)
        self.assertEqual(result["matching_legacy_market_records"],5)
        self.assertEqual(result["publisher_items_detected"],5)
        counts=result["counts"]
        self.assertEqual(counts["unique_city_day_source_item"],4)
        self.assertEqual(counts["saved_market_missing_source_location"],2)
        self.assertEqual(counts["source_and_saved_market_street_agree"],2)
        self.assertEqual(counts["no_matching_city_day_on_page"],1)
        self.assertGreaterEqual(counts["publisher_dayparts_not_exact_hours"],4)
        self.assertEqual(result["catalog_fields_modified"],0)
        safe=json.dumps(result)
        for original in ("Villaggio dei Fiori","Piazza Fermi","Via Fapanni","Via Inventata"):
            self.assertNotIn(original,safe)
        self.assertFalse(result["source_scraping_permitted_by_this_audit"])

    def test_multiple_venues_same_city_day_cannot_assign_address(self):
        extra=HTML.replace(
            b'<li>a Dolo, in Piazza San Valentino (la mattina)</li>',
            b'<li>a Spinea, in Piazza dei Fiori (la mattina)</li>',
        )
        result=compare_saved_markets([market("spinea-no-street")],extra,
                                    source_url=VENICE_NEW,today=TODAY)
        self.assertEqual(result["counts"]["more_than_one_source_venue_on_city_day"],1)
        self.assertEqual(result["counts"].get("saved_market_missing_source_location",0),0)

    def test_wrong_city_weekday_and_foreign_source_cannot_join(self):
        rows=[
            market("wrong-city",city="Mirano"),
            market("wrong-day",day="venerdì"),
            market("different-publisher",url="https://www.happings.com/it/mercati-settimanali-a-padova.html"),
        ]
        result=compare_saved_markets(rows,HTML,source_url=VENICE_NEW,today=TODAY)
        self.assertEqual(result["matching_legacy_market_records"],2)
        self.assertEqual(result["counts"]["no_matching_city_day_on_page"],2)
        self.assertEqual(result["catalog_records_added"],0)

    def test_source_scope_bad_url_unknown_template_or_garbage_is_denied(self):
        for url in (
            "http://www.happings.com/it/mercati-settimanali-a-venezia.html",
            "https://evil.example/it/mercati-settimanali-a-venezia.html",
            "https://www.happings.com/it/happing/private/",
            "https://www.happings.com/it/mercati-settimanali-a-venezia.html?foo=bar",
            "https://user:pass@www.happings.com/it/mercati-settimanali-a-venezia.html",
        ):
            with self.subTest(url=url),self.assertRaises(ValueError):
                parse(HTML,source_url=url)
        with self.assertRaisesRegex(ValueError,"Missing or unbounded"):
            parse(b"A"*(MAX_HTML_BYTES+1),source_url=VENICE_NEW)
        with self.assertRaisesRegex(ValueError,"no longer matches"):
            parse(b"<p>no market indexes</p>"*40,source_url=VENICE_NEW)
        no_verification=compare_saved_markets([market("m")],HTML,source_url=VENICE_NEW)
        no_verification["confirmed_market_editions_added"]=1
        with self.assertRaises(ValueError):
            verify(no_verification,1)

    def test_ambiguous_weekday_slug_override_is_rejected(self):
        wrong=market("mercato-settimanale-a-spinea-sabato",day="mercoledì")
        outcome=compare_saved_markets([wrong],HTML,source_url=VENICE_NEW,today=TODAY)
        self.assertEqual(outcome["counts"]["cannot_prove_catalog_weekday"],1)
        self.assertEqual(outcome["counts"].get("saved_market_missing_source_location",0),0)

if __name__=="__main__":
    unittest.main()
