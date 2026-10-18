"""Exact field-level source transfer from Happings: no guessed hours/GPS/dates."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from happings_source_enrichment import (
    preview,fetch_pages,safe_report,summarize,allowed_url,select_pages,MAX_REQUESTS_PER_RUN,
)
from happings_weekly_layout import VENICE_OLD, VENICE_NEW

TODAY=date(2026,10,19)
SAMPLE=b"""
<!doctype html><html lang="it"><body>
<h1>Mercati settimanali a Venezia</h1>
<div class="happings-seo-content">
<h3>Mercati del mercoled&#236; nei comuni di Venezia</h3>
<ul><li>a Spinea, in Villaggio dei Fiori (la mattina)</li>
    <li>a Dolo, in Piazza San Valentino (la mattina)</li>
    <li>a Scorz&#232;, in Piazza San Marco (la mattina)</li>
</ul>
<h3>Mercati del sabato nei comuni di Venezia</h3>
<ul><li>a Spinea, in Piazza Fermi (la mattina)</li></ul>
</div></body></html>"""

def row(slug,*,city="Spinea",day="mercoledì",street="",url=VENICE_OLD):
    return {
        "slug":slug,"nome":"Mercato settimanale di "+city,
        "citta":city,"provincia":"VE","regione":"Veneto",
        "indirizzo":street,"fonte":"happings.com","url_fonte":url,
        "ricorrenza_testo":"settimanale - "+day,"orario_testo":"",
        "date":["2026-10-21"],"date_quality":"prevista",
        "aggiornato_il":"2026-06-05","verificato_il":"",
        "lat":45.49,"lng":12.15,"position_quality":"non_verificata",
        "status":"non_confermato","fonti":[],
    }

def feed():
    return [{"requested_url":VENICE_OLD,"final_url":VENICE_NEW,"html":SAMPLE}]


class HappingsSourceEnrichmentTests(unittest.TestCase):
    def test_one_unique_city_day_fills_blanks_when_explicitly_permitted(self):
        base=[
            row("mercato-settimanale-a-spinea-spinea-mercoledi"),
            row("mercato-settimanale-di-spinea-spinea"),
            row("mercato-settimanale-di-spinea-spinea-mercoledi",street="Villaggio dei Fiori"),
            row("mercato-settimanale-di-spinea-spinea-sabato",street="Piazza Fermi",day="sabato"),
        ]
        snapshot=copy.deepcopy(base)
        candidate,report=preview(base,feed(),today=TODAY,apply=True,rights_verified=True)
        self.assertEqual(len(candidate),4)
        self.assertEqual(report["field_candidates"],2)
        self.assertEqual(report["field_changes"],2)
        self.assertTrue(safe_report(report,base))
        self.assertEqual(base,snapshot)
        for r in candidate[:2]:
            self.assertEqual(r["indirizzo"],"Villaggio dei Fiori")
            self.assertEqual(r["orario_testo"],"")
            self.assertEqual(r["date_quality"],"prevista")
            self.assertEqual(r["date"],["2026-10-21"])
            self.assertEqual(r["lat"],45.49)
            self.assertEqual(r["verificato_il"],"")
            self.assertEqual(r["url_fonte"],VENICE_OLD)
            self.assertTrue(any(x["url"]==VENICE_NEW for x in r["fonti"]))
        again,repeat=preview(candidate,feed(),today=TODAY,apply=True,rights_verified=True)
        self.assertEqual(again,candidate)
        self.assertEqual(repeat["field_changes"],0)
        self.assertEqual(repeat["field_candidates"],0)

    def test_dry_run_cannot_update_even_when_source_is_available(self):
        original=[row("spinea-1")]
        before=copy.deepcopy(original)
        candidate,report=preview(original,feed(),today=TODAY)
        self.assertEqual(candidate,before)
        self.assertEqual(original,before)
        self.assertEqual(report["field_candidates"],1)
        self.assertEqual(report["field_changes"],0)
        self.assertFalse(report["proposals"][0]["apply_authorized"])
        self.assertFalse(report["proposals"][0]["individually_confirmed"])
        self.assertFalse(summarize(report)["bulk_crawling_enabled"])

    def test_absent_or_malformed_permission_forbids_any_address_write(self):
        with self.assertRaisesRegex(ValueError,"reviewed rights"):
            preview([row("x")],feed(),today=TODAY,apply=True)
        with self.assertRaisesRegex(ValueError,"explicit publisher-rights approval"):
            fetch_pages([VENICE_OLD])
        with self.assertRaises(ValueError):
            fetch_pages([VENICE_OLD]*3,permission_confirmed=True)

    def test_two_distinct_venues_on_same_city_weekday_get_no_updates(self):
        changed=SAMPLE.replace(
            b'<li>a Dolo, in Piazza San Valentino (la mattina)</li>',
            b'<li>a Spinea, in Via Roma (la mattina)</li>',
        )
        page=[{"requested_url":VENICE_OLD,"final_url":VENICE_NEW,"html":changed}]
        candidate,report=preview([row("spinea-1")],page,today=TODAY,apply=True,
                                 rights_verified=True)
        self.assertEqual(candidate[0]["indirizzo"],"")
        self.assertEqual(report["field_candidates"],0)
        self.assertEqual(report["parser_counts"]["no_unique_source_market_city_weekday"],1)

    def test_saved_street_conflict_quarantines_entire_city_weekday_group(self):
        old=[row("a"),row("b",street="Piazza Inventata")]
        candidate,report=preview(old,feed(),today=TODAY,apply=True,rights_verified=True)
        self.assertEqual(candidate,old)
        self.assertEqual(report["parser_counts"]["conflicting_previously_saved_location"],2)
        self.assertEqual(report["field_candidates"],0)

    def test_distinct_city_or_day_cannot_copy_other_market_location(self):
        for market in (
            row("x",city="Mirano"),
            row("x",day="lunedì"),
            row("mercato-settimanale-di-spinea-spinea-sabato",
                day="mercoledì"),
        ):
            with self.subTest(market=market):
                candidate,report=preview([market],feed(),today=TODAY,apply=True,rights_verified=True)
                self.assertEqual(report["field_candidates"],0)
                self.assertEqual(candidate,[market])

    def test_vague_venue_and_preexisting_nonempty_address_are_never_overwritten(self):
        old=[row("a",street="centro"),row("b",street="Villaggio dei Fiori")]
        candidate,report=preview(old,feed(),today=TODAY,apply=True,rights_verified=True)
        self.assertEqual(candidate,old)
        self.assertEqual(report["field_candidates"],0)

    def test_redirects_must_stay_at_same_approved_publisher_and_province(self):
        self.assertTrue(allowed_url(VENICE_OLD,VENICE_OLD,VENICE_NEW))
        self.assertFalse(allowed_url(VENICE_OLD,VENICE_OLD,
                                     "https://www.happings.com/it/mercati-settimanali-a-roma-e-provincia/"))
        self.assertFalse(allowed_url(VENICE_OLD,VENICE_OLD,
                                     "https://evil.example/it/mercati-settimanali-a-venezia.html"))

    def test_robots_denial_and_request_budget_prevent_any_unauthorized_crawl(self):
        calls=[]
        def get_robots(url,**kwargs):
            calls.append(url)
            return b"User-agent: *\nDisallow: /it/mercati-settimanali-a-\n",url
        def page_get(url,**kwargs):
            raise AssertionError("Unreviewed publisher robot-disallowed page fetched")
        with self.assertRaisesRegex(ValueError,"robots policy denied"):
            fetch_pages([VENICE_OLD],permission_confirmed=True,
                        robots_fetch=get_robots,page_fetch=page_get,sleep=lambda _:None)
        self.assertEqual(calls,["https://www.happings.com/robots.txt"])
        def allow(url,**kwargs):
            return b"User-agent: *\nAllow: /\n",url
        fetched=[]
        def page(url,**kwargs):
            fetched.append(url)
            return SAMPLE,VENICE_NEW
        result=fetch_pages([VENICE_OLD],permission_confirmed=True,
                           robots_fetch=allow,page_fetch=page,sleep=lambda _:None)
        self.assertEqual(len(result),1)
        self.assertEqual(fetched,[VENICE_OLD])

    def test_default_publisher_rights_record_is_not_authentication(self):
        from happings_source_enrichment import RIGHTS_REVIEW_FILE
        rights=json.loads(RIGHTS_REVIEW_FILE.read_text("utf-8"))
        self.assertFalse(rights["republication_rights_authenticated"])
        self.assertFalse(rights["mass_crawling_enabled"])
        self.assertEqual(rights["technical_limits"]["max_index_pages_per_run"],2)
        self.assertTrue(all(x["digital_signature_verified"] is False
                            for x in rights["user_supplied_documents"]))

    def test_stable_rotation_selects_pages_with_missing_market_streets(self):
        urls=[
            "https://www.happings.com/it/mercati-settimanali-a-venezia.html",
            "https://www.happings.com/it/mercati-settimanali-a-modena.html",
            "https://www.happings.com/it/mercati-settimanali-a-padova.html",
            "https://www.happings.com/it/mercati-settimanali-a-bologna.html",
            "https://www.happings.com/it/mercati-settimanali-a-rimini.html",
        ]
        old=[row("market-"+str(i),url=urls[i%len(urls)]) for i in range(22)]
        old[0]["indirizzo"]="Piazza Fermi"
        original=copy.deepcopy(old)
        visited=set()
        for i in range(5):
            day=date.fromordinal(TODAY.toordinal()+i)
            selected=select_pages(old,today=day)
            self.assertLessEqual(len(selected),MAX_REQUESTS_PER_RUN)
            self.assertTrue(all(x in urls for x in selected))
            visited.update(selected)
            self.assertEqual(select_pages(old,today=day),selected)
        self.assertEqual(visited,set(urls))
        self.assertEqual(old,original)

    def test_never_schedule_publisher_event_details_or_non_empty_streets(self):
        catalog=[
            row("source-missing",url=VENICE_OLD),
            row("detail-link",url="https://www.happings.com/it/mercato-settimanale-a-spinea.html"),
            row("source-complete",street="Villaggio dei Fiori",url=
                "https://www.happings.com/it/mercati-settimanali-a-modena.html"),
        ]
        self.assertEqual(select_pages(catalog,today=TODAY),[VENICE_OLD])
        catalog.append(copy.deepcopy(catalog[0]))
        with self.assertRaisesRegex(ValueError,"Repeated legacy market ID"):
            select_pages(catalog,today=TODAY)

    def test_no_original_market_is_ever_deleted_or_verified(self):
        old=[row("spinea-1"),row("dolo-1",city="Dolo")]
        updated,report=preview(old,feed(),today=TODAY,apply=True,rights_verified=True)
        self.assertEqual({m["slug"] for m in old},{m["slug"] for m in updated})
        self.assertEqual(report["market_rows_deleted"],0)
        self.assertEqual(report["market_rows_inserted"],0)
        self.assertEqual(report["market_openings_verified"],0)
        self.assertEqual(report["new_geographic_points"],0)
        self.assertTrue(safe_report(report,old))

if __name__=="__main__":
    unittest.main()
