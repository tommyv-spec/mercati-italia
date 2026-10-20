"""Exact field-level source transfer from Happings: no guessed hours/GPS/dates."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
import tempfile
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from happings_source_enrichment import (
    preview,fetch_pages,safe_report,summarize,allowed_url,select_pages,offline_pages,MAX_REQUESTS_PER_RUN,
    authorization_status, catalog_page_routes, secondary_catalog_page_routes, RIGHTS_REVIEW_FILE,
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

def row(slug,*,city="Spinea",day="mercoledì",street="",url=VENICE_OLD,
        province="VE",region="Veneto"):
    return {
        "slug":slug,"nome":"Mercato settimanale di "+city,
        "citta":city,"provincia":province,"regione":region,
        "indirizzo":street,"fonte":"happings.com","url_fonte":url,
        "ricorrenza_testo":"settimanale - "+day,"orario_testo":"",
        "date":["2026-10-21"],"date_quality":"prevista",
        "aggiornato_il":"2026-06-05","verificato_il":"",
        "lat":45.49,"lng":12.15,"position_quality":"non_verificata",
        "status":"non_confermato","fonti":[],
    }

def feed():
    return [{"requested_url":VENICE_OLD,"final_url":VENICE_NEW,"html":SAMPLE}]


def secondary(slug="other-origin", *, street="Villaggio dei Fiori", **changes):
    return {**row(slug,street=street),"fonte":"eventiesagre.it",
            "url_fonte":"https://www.eventiesagre.it/Mercatini_Filiera+Corta/12345_Mercato.html",
            **changes}


class HappingsSourceEnrichmentTests(unittest.TestCase):
    def test_replay_offline_html_with_real_old_to_canonical_redirect(self):
        with tempfile.TemporaryDirectory() as folder:
            source=Path(folder)/"reviewed-venezia.html"
            source.write_bytes(SAMPLE)
            pages=offline_pages([VENICE_OLD],[source],[VENICE_NEW])
            self.assertEqual(pages[0]["requested_url"],VENICE_OLD)
            self.assertEqual(pages[0]["final_url"],VENICE_NEW)
            before=[row("mercato-settimanale-a-spinea-spinea-mercoledi")]
            after,result=preview(before,pages,today=TODAY)
            self.assertEqual(before,after)
            self.assertEqual(result["field_candidates"],1)
            self.assertEqual(result["field_changes"],0)
            self.assertTrue(safe_report(result,before))
            with self.assertRaisesRegex(ValueError,"crossed province"):
                offline_pages([VENICE_OLD],[source],[
                    "https://www.happings.com/it/mercati-settimanali-a-modena-e-provincia/"
                ])
            with self.assertRaisesRegex(ValueError,"align"):
                offline_pages([VENICE_OLD],[source],[])
            with self.assertRaisesRegex(ValueError,"align"):
                offline_pages([VENICE_OLD],[source,source],[VENICE_NEW])

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
        self.assertEqual(summarize(report)["record_changes"],0)
        self.assertEqual(summarize(report)["calendar_content_dates_inferred"],0)

    def test_absent_or_malformed_permission_forbids_any_address_write(self):
        with self.assertRaisesRegex(ValueError,"reviewed rights"):
            preview([row("x")],feed(),today=TODAY,apply=True)
        with self.assertRaisesRegex(ValueError,"active project authorization"):
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

    def test_conflicting_town_detail_is_not_hidden_by_province_url_filter(self):
        base=[row("missing"),row("town-source",street="Via Roma",
              url="https://www.happings.com/it/mercato-settimanale-a-spinea.html")]
        after,report=preview(base,feed(),today=TODAY,apply=True,rights_verified=True)
        self.assertEqual(after,base)
        self.assertEqual(report["field_candidates"],0)
        self.assertEqual(report["parser_counts"]["conflicting_previously_saved_location"],2)

    def test_province_and_region_must_agree_with_source_and_official_municipality(self):
        for wrong in (row("x",province="MO"),row("x",region="Lombardia"),
                      row("x",province=""),row("x",region="")):
            with self.subTest(wrong=wrong):
                after,report=preview([wrong],feed(),today=TODAY,apply=True,rights_verified=True)
                self.assertEqual(after,[wrong])
                self.assertEqual(report["parser_counts"]["identity_geography_unproven"],1)
        url="https://www.happings.com/it/mercati-settimanali-a-vibo-valentia.html"
        sample=SAMPLE.replace(b"Spinea",b"Tropea").replace(b"Venezia",b"Vibo Valentia")
        pages=[{"requested_url":url,"final_url":url,"html":sample}]
        base=[row("tropea-vv",city="Tropea",province="VV",region="Calabria",url=url),
              row("tropea-vb",city="Tropea",province="VB",region="Calabria",url=url)]
        after,report=preview(base,pages,today=TODAY,apply=True,rights_verified=True)
        self.assertEqual(report["changed_ids"],["tropea-vv"])
        self.assertEqual(after[1],base[1])

    def test_changed_template_is_quarantined_without_discarding_valid_other_page(self):
        bad=SAMPLE.replace(b"<li>a Dolo",b"<li>unknown layout Dolo")
        modena="https://www.happings.com/it/mercati-settimanali-a-modena.html"
        pages=feed()+[{"requested_url":modena,"final_url":modena,
                       "html":bad.replace(b"Spinea",b"Modena").replace(b"Venezia",b"Modena")}]
        base=[row("spinea"),row("modena",city="Modena",province="MO",
                               region="Emilia-Romagna",url=modena)]
        after,report=preview(base,pages,today=TODAY,apply=True,rights_verified=True)
        self.assertEqual(report["changed_ids"],["spinea"])
        self.assertEqual(after[1],base[1])
        self.assertEqual([p["status"] for p in report["source_pages"]],["parsed","layout_changed"])
        self.assertTrue(safe_report(report,base))

    def test_proposal_receipt_is_bound_to_html_geography_and_original_blank(self):
        base=[row("spinea")]
        after,report=preview(base,feed(),today=TODAY,apply=True,rights_verified=True)
        self.assertEqual(report["proposals"][0]["source_html_sha256"],hashlib.sha256(SAMPLE).hexdigest())
        for field,value in (("source_html_sha256","0"*64),("source_province","MO"),
                            ("source_day",5),("apply_authorized",False)):
            forged=copy.deepcopy(report)
            forged["proposals"][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                safe_report(forged,base)
        with self.assertRaises(ValueError):
            safe_report(report,after)

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

    def test_monthly_or_duplicate_dates_do_not_prove_a_weekly_market(self):
        for recurrence,dates in (("mensile - primo mercoledì del mese",["2026-10-21"]),
                                 ("",["2026-10-21","2026-10-21"])):
            base=[{**row("spinea-mercoledi"),"ricorrenza_testo":recurrence,"date":dates}]
            after,report=preview(base,feed(),today=TODAY,apply=True,rights_verified=True)
            self.assertEqual(after,base)
            self.assertEqual(report["field_candidates"],0)
            self.assertEqual(select_pages(base,today=TODAY),[])

    def test_vague_venue_and_preexisting_nonempty_address_are_never_overwritten(self):
        old=[row("a",street="centro"),row("b",street="Villaggio dei Fiori")]
        candidate,report=preview(old,feed(),today=TODAY,apply=True,rights_verified=True)
        self.assertEqual(candidate[0],old[0])
        self.assertEqual(candidate[1]["indirizzo"],old[1]["indirizzo"])
        receipt=candidate[1]["riscontri_campi"][0]
        self.assertNotIn("campi_gestiti",receipt)
        self.assertEqual(receipt["fonte_aggiornata_il"],"")
        self.assertEqual(report["field_candidates"],0)

    def test_redirects_must_stay_at_same_approved_publisher_and_province(self):
        self.assertTrue(allowed_url(VENICE_OLD,VENICE_OLD,VENICE_NEW))
        self.assertFalse(allowed_url(VENICE_OLD,VENICE_OLD,
                                     "https://www.happings.com/it/mercati-settimanali-a-roma-e-provincia/"))
        self.assertFalse(allowed_url(VENICE_OLD,VENICE_OLD,
                                     "https://evil.example/it/mercati-settimanali-a-venezia.html"))

    def test_ad_alias_matches_offline_without_guessing_live_redirect(self):
        old="https://www.happings.com/it/mercati-settimanali-ad-agrigento.html"
        new="https://www.happings.com/it/mercati-settimanali-a-agrigento-e-provincia/"
        self.assertTrue(allowed_url(old,old,new))
        base=[row("agrigento",city="Agrigento",province="AG",region="Sicilia",url=old)]
        pages=[{"requested_url":old,"final_url":new,
                "html":SAMPLE.replace(b"Spinea",b"Agrigento").replace(b"Venezia",b"Agrigento")}]
        after,report=preview(base,pages,today=TODAY)
        self.assertEqual(after,base)
        self.assertEqual(report["field_candidates"],1)
        self.assertEqual(report["field_changes"],0)
        self.assertEqual(select_pages(base,today=TODAY),[old])

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

    def test_redirect_robots_denial_is_checked_before_redirect_request(self):
        from happings_source_enrichment import GuardedRedirects,USER_AGENT
        from urllib.request import Request
        from urllib.robotparser import RobotFileParser
        robots=RobotFileParser()
        robots.parse(["User-agent: *","Disallow: /it/mercati-settimanali-a-venezia-e-provincia/"])
        self.assertTrue(robots.can_fetch(USER_AGENT,VENICE_OLD))
        with self.assertRaisesRegex(ValueError,"robots policy denied redirected"):
            GuardedRedirects(VENICE_OLD,robots).redirect_request(
                Request(VENICE_OLD),None,301,"Moved",{},VENICE_NEW)

    def test_observed_legacy_two_hop_transport_retains_exact_province_and_final_scope(self):
        from happings_source_enrichment import GuardedRedirects
        from happings_weekly_layout import _valid_page_url
        from urllib.request import Request
        from urllib.robotparser import RobotFileParser
        robots=RobotFileParser();robots.parse(["User-agent: *","Allow: /"])
        for old,canonical in (
            ("https://www.happings.com/it/mercati-settimanali-a-crotone.html",
             "https://www.happings.com/it/mercati-settimanali-a-crotone-e-provincia/"),
            ("https://www.happings.com/it/mercati-settimanali-a-cuneo.html",
             "https://www.happings.com/it/mercati-settimanali-a-cuneo-e-provincia/"),
            ("https://www.happings.com/it/mercati-settimanali-ad-enna.html",
             "https://www.happings.com/it/mercati-settimanali-a-enna-e-provincia/"),
        ):
            with self.subTest(old=old):
                transport=old[:-5]+"/";pauses=[]
                guard=GuardedRedirects(old,robots,sleep=pauses.append)
                first=guard.redirect_request(Request(old),None,301,"Moved",{},transport)
                final=guard.redirect_request(first,None,301,"Moved",{},canonical)
                self.assertEqual(final.full_url,canonical)
                self.assertEqual(pauses,[3,3])
                self.assertFalse(_valid_page_url(transport))
                self.assertFalse(allowed_url(old,old,transport))
                self.assertTrue(allowed_url(old,old,canonical))
                with self.assertRaisesRegex(ValueError,"hop count"):
                    guard.redirect_request(final,None,301,"Moved",{},old)

    def test_legacy_intermediate_cannot_escape_original_slug_or_bypass_robots(self):
        from happings_source_enrichment import GuardedRedirects
        from urllib.request import Request
        from urllib.robotparser import RobotFileParser
        transport=VENICE_OLD[:-5]+"/"
        for target in (transport.replace("venezia","modena"),
                       transport.replace("https:","http:"),
                       transport.replace("www.happings.com","evil.example"),
                       transport+"?alternate=1",transport+"#section"):
            with self.subTest(target=target),self.assertRaisesRegex(ValueError,"left reviewed"):
                GuardedRedirects(VENICE_OLD,sleep=lambda _:self.fail("No request before URL proof")).redirect_request(
                    Request(VENICE_OLD),None,301,"Moved",{},target)
        robot=RobotFileParser();robot.parse(["User-agent: *","Disallow: "+transport.split(".com",1)[1]])
        with self.assertRaisesRegex(ValueError,"robots policy denied"):
            GuardedRedirects(VENICE_OLD,robot,sleep=lambda _:self.fail("No denied request")).redirect_request(
                Request(VENICE_OLD),None,301,"Moved",{},transport)
        guard=GuardedRedirects(VENICE_OLD,sleep=lambda _:None)
        first=guard.redirect_request(Request(VENICE_OLD),None,301,"Moved",{},transport)
        with self.assertRaisesRegex(ValueError,"crossed province"):
            guard.redirect_request(first,None,301,"Moved",{},VENICE_NEW.replace("venezia","modena"))

    def test_intermediate_200_body_is_not_accepted_as_a_reviewed_final_page(self):
        import happings_source_enrichment as source
        class Response:
            url=VENICE_OLD[:-5]+"/"
            headers={"Content-Type":"text/html; charset=utf-8"}
            def __enter__(self):return self
            def __exit__(self,*args):return None
            def read(self,limit):return SAMPLE
        class Opener:
            def open(self,*args,**kwargs):return Response()
        with patch.object(source,"_public_dns"),self.assertRaisesRegex(ValueError,"unreviewed target"):
            source._fetch_one(VENICE_OLD,opener=Opener())

    def test_fetch_error_codes_are_bounded_and_do_not_copy_exception_payloads(self):
        from happings_source_enrichment import failure_code,valid_failure_code
        from urllib.error import HTTPError
        examples=[
            (ValueError("Source redirect left reviewed Happings province layout"),"redirect_unreviewed"),
            (ValueError("Publisher redirect crossed province"),"redirect_crossed_province"),
            (HTTPError(VENICE_OLD,429,"remote body is not a diagnostic",{},None),"http_429"),
            (OSError("private upstream text"),"connection_error"),
            (ValueError("arbitrary untrusted details"),"validation_failed"),
        ]
        for error,expected in examples:
            self.assertEqual(failure_code(error),expected)
            self.assertTrue(valid_failure_code(expected))
        for bad in (None,[],"http_200","http_600","http_429?secret=1","unknown",False):
            self.assertFalse(valid_failure_code(bad))
        failures=[]
        def fail(url,**kwargs):raise examples[0][0]
        self.assertEqual(fetch_pages([VENICE_OLD],permission_confirmed=True,failures=failures,
            robots_fetch=lambda url,**kwargs:(b"User-agent: *\nAllow: /\n",url),
            page_fetch=fail,sleep=lambda _:None),[])
        self.assertEqual(failures,[{"requested_url":VENICE_OLD,"error_type":"ValueError",
                                    "error_code":"redirect_unreviewed"}])

    def test_robot_delay_and_aliases_cannot_bypass_request_budget(self):
        sleeps=[]
        def robots(url,**kwargs):
            return b"User-agent: *\nAllow: /\nCrawl-delay: 8\n",url
        fetch_pages([VENICE_OLD],permission_confirmed=True,robots_fetch=robots,
                    page_fetch=lambda url,**kwargs:(SAMPLE,VENICE_NEW),sleep=sleeps.append)
        self.assertEqual(sleeps,[8])
        from happings_source_enrichment import GuardedRedirects
        from urllib.request import Request
        from urllib.robotparser import RobotFileParser
        policy=RobotFileParser()
        policy.parse(["User-agent: *","Allow: /","Crawl-delay: 8"])
        redirects=[]
        follow=GuardedRedirects(VENICE_OLD,policy,sleep=redirects.append).redirect_request(
            Request(VENICE_OLD),None,301,"Moved",{},VENICE_NEW)
        self.assertEqual(follow.full_url,VENICE_NEW)
        self.assertEqual(redirects,[8])
        with self.assertRaisesRegex(ValueError,"URL not from"):
            fetch_pages([VENICE_OLD,VENICE_NEW],permission_confirmed=True,
                        robots_fetch=lambda *a,**k:self.fail("No robots request for duplicate aliases"))

    def test_default_publisher_rights_record_is_not_authentication(self):
        from happings_source_enrichment import RIGHTS_REVIEW_FILE
        rights=json.loads(RIGHTS_REVIEW_FILE.read_text("utf-8"))
        self.assertFalse(rights["republication_rights_authenticated"])
        self.assertTrue(rights["recurring_extraction_enabled"])
        status=authorization_status(rights,today=TODAY)
        self.assertTrue(status["authorized"])
        self.assertFalse(status["rights_authenticated"])
        self.assertEqual(status["basis"],"explicit_project_owner_instruction")
        self.assertEqual(rights["technical_limits"]["max_index_pages_per_run"],MAX_REQUESTS_PER_RUN)
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
        places=[("Spinea","VE","Veneto"),("Modena","MO","Emilia-Romagna"),
                ("Padova","PD","Veneto"),("Bologna","BO","Emilia-Romagna"),
                ("Rimini","RN","Emilia-Romagna")]
        old=[row("market-"+str(i),url=urls[i%len(urls)],
                 city=places[i%5][0],province=places[i%5][1],region=places[i%5][2])
             for i in range(22)]
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

    def test_rotation_coalesces_aliases_and_rejects_wrong_province(self):
        base=[row("old"),row("canonical",url=VENICE_NEW),row("wrong",province="MO")]
        selected=select_pages(base,today=TODAY)
        self.assertEqual(len(selected),1)
        self.assertIn(selected[0],(VENICE_OLD,VENICE_NEW))
        with self.assertRaisesRegex(ValueError,"repeated source page"):
            preview(base,feed()+[{"requested_url":VENICE_NEW,"final_url":VENICE_NEW,"html":SAMPLE}])

    def test_no_original_market_is_ever_deleted_or_verified(self):
        old=[row("spinea-1"),row("dolo-1",city="Dolo")]
        updated,report=preview(old,feed(),today=TODAY,apply=True,rights_verified=True)
        self.assertEqual({m["slug"] for m in old},{m["slug"] for m in updated})
        self.assertEqual(report["market_rows_deleted"],0)
        self.assertEqual(report["market_rows_inserted"],0)
        self.assertEqual(report["market_openings_verified"],0)
        self.assertEqual(report["new_geographic_points"],0)
        self.assertTrue(safe_report(report,old))

    def test_malformed_or_future_project_authorization_does_not_enable_requests(self):
        baseline=json.loads(RIGHTS_REVIEW_FILE.read_text())
        for change in ({"scope":["automated_extraction",{}]}, {"scope":["automated_extraction"]},
                       {"revoked":True},{"authorized":"true"},{"publication_channel":"production"},
                       {"recorded_on":"2026-10-20"},{"recorded_on":"20261019"}):
            with self.subTest(change=change):
                altered=copy.deepcopy(baseline)
                altered["project_authorization"].update(change)
                self.assertFalse(authorization_status(altered,today=TODAY)["authorized"])

    def test_town_routes_keep_source_identity_and_join_only_matching_town(self):
        town=row("town",url="https://www.happings.com/it/mercato-settimanale-a-spinea.html")
        wrong={**town,"slug":"wrong","url_fonte":"https://www.happings.com/it/mercato-settimanale-a-dolo.html"}
        base=[row("province"),town,wrong]
        routes=catalog_page_routes(base)
        self.assertEqual(routes,{"province":VENICE_OLD,"town":VENICE_OLD})
        revised,report=preview(base,feed(),today=TODAY,apply=True,rights_verified=True)
        self.assertEqual(revised[1]["url_fonte"],town["url_fonte"])
        self.assertEqual(revised[1]["indirizzo"],"Villaggio dei Fiori")
        self.assertEqual(revised[2],wrong)
        town_proof=next(p for p in report["proposals"] if p["market_id"]=="town")
        self.assertEqual(town_proof["evidence_method"],"town_link_same_province_city_weekday")
        self.assertTrue(safe_report(report,base))

    def test_complete_addresses_stay_in_rotation(self):
        base=[row("a"),row("b",city="Dolo")]
        before=select_pages(base,today=TODAY)
        filled=[{**r,"indirizzo":"Via Roma"} for r in base]
        self.assertEqual(select_pages(filled,today=TODAY),before)
        self.assertEqual(catalog_page_routes(filled),catalog_page_routes(base))

    def test_town_punctuation_can_normalize_but_missing_letters_and_suffixes_cannot(self):
        from happings_source_enrichment import _town_url_matches
        self.assertTrue(_town_url_matches(row("prezza",city="Prezza",url="https://www.happings.com/it/mercato-settimanale-a-prezza--.html")))
        self.assertTrue(_town_url_matches(row("santagata",city="Sant'Agata de' Goti",url="https://www.happings.com/it/mercato-settimanale-a-sant-agata-de--goti.html")))
        self.assertFalse(_town_url_matches(row("suffix",url="https://www.happings.com/it/mercato-settimanale-a-spinea-2.html")))
        self.assertFalse(_town_url_matches(row("missing",city="Città Sant'Angelo",url="https://www.happings.com/it/mercato-settimanale-a-citt---sant-angelo.html")))

    def test_confirmed_or_precisely_positioned_markets_are_not_assigned_a_street(self):
        for change in ({"verificato_il":"2026-10-18"},{"position_quality":"precisa"}):
            base=[{**row("protected"),**change}]
            after,report=preview(base,feed(),today=TODAY,apply=True,rights_verified=True)
            self.assertEqual(after,base)
            self.assertEqual(report["field_changes"],0)

    def test_new_read_adds_source_observation_without_renewing_calendar_dates(self):
        before=[row("a",street="Villaggio dei Fiori")]
        first,proof=preview(before,feed(),today=TODAY,apply=True,rights_verified=True)
        later=TODAY+timedelta(days=7)
        after,proof2=preview(first,feed(),today=later,apply=True,rights_verified=True)
        self.assertEqual(after[0]["riscontri_campi"][0]["letto_il"],later.isoformat())
        self.assertEqual(after[0]["riscontri_campi"][0]["fonte_aggiornata_il"],"")
        self.assertNotIn("campi_gestiti",after[0]["riscontri_campi"][0])
        for field in ("date","aggiornato_il","date_quality","verificato_il","lat","lng","orario_testo"):
            self.assertEqual(after[0].get(field),before[0].get(field))
        self.assertEqual(proof2["field_changes"],0)
        self.assertTrue(safe_report(proof2,first))

    def test_same_day_changed_body_does_not_override_the_previous_observation(self):
        base=[row("a")]
        first,_=preview(base,feed(),today=TODAY,apply=True,rights_verified=True)
        changed=[{**feed()[0],"html":SAMPLE.replace(b"Villaggio dei Fiori",b"Via Nuova")}]
        second,report=preview(first,changed,today=TODAY,apply=True,rights_verified=True)
        self.assertEqual(second,first)
        self.assertEqual(report["field_changes"],0)

    def test_unowned_conflicting_cohort_prevents_managed_address_replacement(self):
        first,_=preview([row("owned")],feed(),today=TODAY,apply=True,rights_verified=True)
        mixed=[*first,row("unowned",street="Villaggio dei Fiori")]
        changed=[{**feed()[0],"html":SAMPLE.replace(b"Villaggio dei Fiori",b"Via Nuova")}]
        after,report=preview(mixed,changed,today=TODAY+timedelta(days=7),apply=True,rights_verified=True)
        self.assertEqual(after[0]["indirizzo"],mixed[0]["indirizzo"])
        self.assertEqual(after[1],mixed[1])
        self.assertTrue(all("indirizzo" not in proof["valori"] for proof in after[0]["riscontri_campi"]))
        self.assertEqual(report["retired_ids"],["owned"])
        self.assertEqual(report["field_changes"],0)

    def test_secondary_source_only_observes_identical_existing_values(self):
        base=[row("primary",street="Villaggio dei Fiori"),secondary()]
        original=copy.deepcopy(base)
        after,report=preview(base,feed(),today=TODAY,apply=True,rights_verified=True)
        self.assertEqual(base,original)
        self.assertEqual(report["field_changes"],0)
        self.assertEqual(report["secondary_observed_ids"],["other-origin"])
        self.assertEqual(set(after[1])-set(base[1]),{"riscontri_campi"})
        self.assertEqual({key for key in base[1] if after[1][key]!=base[1][key]},{"fonti"})
        receipt=after[1]["riscontri_campi"][0]
        self.assertEqual(receipt["metodo"],"sede_giorno_provincia")
        self.assertEqual(receipt["valori"],{"indirizzo":"Villaggio dei Fiori",
                                          "ricorrenza_testo":base[1]["ricorrenza_testo"]})
        self.assertEqual(receipt["fonte_aggiornata_il"],"")
        self.assertNotIn("campi_gestiti",receipt)
        self.assertNotIn("gestore_campi",receipt)
        self.assertTrue(safe_report(report,base))

    def test_secondary_capacity_never_introduces_a_source_request(self):
        external=secondary()
        self.assertEqual(secondary_catalog_page_routes([external]),{})
        self.assertEqual(select_pages([external],today=TODAY),[])
        base=[row("primary",street="Villaggio dei Fiori"),external]
        self.assertEqual(secondary_catalog_page_routes(base),{external["slug"]:VENICE_OLD})
        self.assertEqual(select_pages(base,today=TODAY),select_pages(base[:1],today=TODAY))
        without_street=[base[0],{**external,"indirizzo":""}]
        self.assertEqual(secondary_catalog_page_routes(without_street),{})
        self.assertEqual(select_pages(without_street,today=TODAY),select_pages(base,today=TODAY))

    def test_secondary_unknown_identity_or_street_cannot_gain_an_observation(self):
        cases=(
            {"indirizzo":""},{"indirizzo":"centro"},{"indirizzo":"Piazza Altrove"},
            {"ricorrenza_testo":"settimanale - lunedì"},{"provincia":"MO"},
            {"regione":"Lombardia"},{"nome":"Mercato contadino di Spinea"},
            {"categoria":"antiquariato"},{"url_fonte":VENICE_OLD},
            {"url_fonte":"https://name:secret@example.org/market"},
            {"nome_originale":"Mercato estivo di Spinea"},
        )
        for change in cases:
            with self.subTest(change=change):
                base=[row("primary",street="Villaggio dei Fiori"),secondary(**change)]
                after,report=preview(base,feed(),today=TODAY,apply=True,rights_verified=True)
                self.assertEqual(after[1],base[1])
                self.assertEqual(report["secondary_observed_ids"],[])
                self.assertFalse(any(p["market_id"]=="other-origin" for p in report["proposals"]))
                self.assertTrue(safe_report(report,base))

    def test_secondary_address_spelling_is_preserved(self):
        base=[row("primary",street="Villaggio dei Fiori"),secondary(street="villaggio dei fiori")]
        after,report=preview(base,feed(),today=TODAY,apply=True,rights_verified=True)
        self.assertEqual(after[1]["indirizzo"],"villaggio dei fiori")
        self.assertEqual(after[1]["riscontri_campi"][0]["valori"]["indirizzo"],"villaggio dei fiori")
        self.assertEqual(report["field_changes"],0)

    def test_secondary_source_ambiguity_is_not_resolved_by_matching_one_saved_street(self):
        ambiguous=SAMPLE.replace(b"<li>a Dolo",b"<li>a Spinea, in Via Alternativa (la mattina)</li><li>a Dolo")
        base=[row("primary",street="Villaggio dei Fiori"),secondary()]
        after,report=preview(base,[{**feed()[0],"html":ambiguous}],today=TODAY,apply=True,rights_verified=True)
        self.assertEqual(after,base)
        self.assertEqual(report["secondary_observed_ids"],[])

    def test_qualified_other_origin_is_retained_in_the_location_conflict_cohort(self):
        for qualifier in ({"ricorrenza_testo":"settimanale - mercoledì da giugno a settembre"},
                          {"nome_originale":"Mercato estivo settimanale di Spinea"}):
            with self.subTest(qualifier=qualifier):
                base=[row("primary"),secondary("conflict",street="Via Alternativa",**qualifier)]
                after,report=preview(base,feed(),today=TODAY,apply=True,rights_verified=True)
                self.assertEqual(after,base)
                self.assertEqual(report["field_changes"],0)
                self.assertEqual(report["parser_counts"]["conflicting_previously_saved_location"],1)

    def test_secondary_reread_does_not_acquire_field_ownership(self):
        base=[row("primary",street="Villaggio dei Fiori"),secondary()]
        first,_=preview(base,feed(),today=TODAY,apply=True,rights_verified=True)
        later=TODAY+timedelta(days=7)
        second,report=preview(first,feed(),today=later,apply=True,rights_verified=True)
        proof=second[1]["riscontri_campi"][0]
        self.assertEqual(proof["letto_il"],later.isoformat())
        self.assertNotIn("campi_gestiti",proof)
        self.assertNotIn("gestore_campi",proof)
        self.assertEqual(report["field_changes"],0)
        self.assertEqual(second[1]["url_fonte"],base[1]["url_fonte"])

    def test_secondary_receipt_tampering_cannot_assign_values_or_ownership(self):
        base=[row("primary",street="Villaggio dei Fiori"),secondary()]
        _,report=preview(base,feed(),today=TODAY,apply=True,rights_verified=True)
        for mutation in ("values","ownership","relation"):
            forged=copy.deepcopy(report)
            observation=next(x for x in forged["observations"] if x["source_relation"]=="secondary")
            if mutation=="values":
                observation["values"]["indirizzo"]="Via Nuova"
            elif mutation=="ownership":
                observation["source_proof"].update({"campi_gestiti":["indirizzo"],"gestore_campi":"happings-weekly-index"})
            else:
                observation["source_relation"]="primary"
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):
                safe_report(forged,base)

    def test_new_unique_source_address_retires_only_its_old_address_support(self):
        from field_evidence import make_receipt
        base=[row("primary",street="Villaggio dei Fiori"),secondary()]
        first,_=preview(base,feed(),today=TODAY,apply=True,rights_verified=True)
        official=make_receipt(first[1],values={"indirizzo":first[1]["indirizzo"]},
            source_url="https://comune.example/mercati",source_name="Comune",source_id="official-fixture",
            source_row="market-1",read_on=TODAY.isoformat(),source_updated_on=TODAY.isoformat(),source_sha256="a"*64)
        first[1]["riscontri_campi"].append(official)
        changed=[{**feed()[0],"html":SAMPLE.replace(b"Villaggio dei Fiori",b"Via Nuova")}]
        after,report=preview(first,changed,today=TODAY+timedelta(days=7),apply=True,rights_verified=True)
        self.assertEqual(report["field_changes"],0)
        self.assertEqual(report["retired_ids"],["other-origin","primary"])
        self.assertEqual(report["observed_ids"],[])
        self.assertEqual(after[1]["indirizzo"],first[1]["indirizzo"])
        self.assertEqual(after[1]["fonti"],first[1]["fonti"])
        self.assertIn(official,after[1]["riscontri_campi"])
        hproof=next(p for p in after[1]["riscontri_campi"] if p["fonte_id"].startswith("happings-weekly"))
        self.assertEqual(hproof["valori"],{"ricorrenza_testo":first[1]["ricorrenza_testo"]})
        self.assertEqual(hproof["letto_il"],TODAY.isoformat())
        self.assertTrue(all(r["retired_fields"]==["indirizzo"] for r in report["retirements"]))
        self.assertTrue(safe_report(report,first))

    def test_missing_ambiguous_vague_or_failed_new_page_does_not_retire_support(self):
        first,_=preview([row("primary",street="Villaggio dei Fiori"),secondary()],feed(),
                        today=TODAY,apply=True,rights_verified=True)
        variants=(
            [],
            [{**feed()[0],"html":SAMPLE.replace(b"a Spinea, in Villaggio dei Fiori",b"a Mirano, in Via Nuova")}],
            [{**feed()[0],"html":SAMPLE.replace(b"Villaggio dei Fiori",b"centro")}],
            [{**feed()[0],"html":SAMPLE.replace(b"Villaggio dei Fiori",b"Via Nuova").replace(
                b"<li>a Dolo",b"<li>a Spinea, in Via Alternativa (la mattina)</li><li>a Dolo")}],
            [{**feed()[0],"html":b"<html>"+b"changed layout "*30+b"</html>"}],
        )
        for pages in variants:
            with self.subTest(pages=len(pages)):
                after,report=preview(first,pages,today=TODAY+timedelta(days=7),apply=True,rights_verified=True)
                self.assertEqual(after,first)
                self.assertEqual(report["retirements"],[])

    def test_same_day_or_older_contradiction_does_not_retire_source_support(self):
        first,_=preview([row("primary",street="Villaggio dei Fiori"),secondary()],feed(),
                        today=TODAY,apply=True,rights_verified=True)
        changed=[{**feed()[0],"html":SAMPLE.replace(b"Villaggio dei Fiori",b"Via Nuova")}]
        for today in (TODAY,TODAY-timedelta(days=1)):
            after,report=preview(first,changed,today=today,apply=True,rights_verified=True)
            self.assertEqual(after,first)
            self.assertEqual(report["retirements"],[])

    def test_retirement_evidence_cannot_be_forged_or_apply_when_preview_only(self):
        first,_=preview([row("primary",street="Villaggio dei Fiori"),secondary()],feed(),
                        today=TODAY,apply=True,rights_verified=True)
        changed=[{**feed()[0],"html":SAMPLE.replace(b"Villaggio dei Fiori",b"Via Nuova")}]
        later=TODAY+timedelta(days=7)
        after,preview_report=preview(first,changed,today=later)
        self.assertEqual(after,first)
        self.assertEqual(len(preview_report["retirements"]),2)
        self.assertEqual(preview_report["retired_ids"],[])
        self.assertTrue(safe_report(preview_report,first))
        _,report=preview(first,changed,today=later,apply=True,rights_verified=True)
        for key,value in (("retired_receipts",[]),("source_day",1),("source_value","Via Inventata"),
                          ("source_html_sha256","f"*64),("source_relation","unknown")):
            forged=copy.deepcopy(report)
            forged["retirements"][0][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):safe_report(forged,first)

    def test_observation_tampering_cannot_change_source_dates_or_weekdays(self):
        before=[row("a")]
        _,report=preview(before,feed(),today=TODAY,apply=True,rights_verified=True)
        for key,value in (("fonte_aggiornata_il",TODAY.isoformat()),("letto_il","2026-10-18")):
            altered=copy.deepcopy(report)
            altered["observations"][0]["source_proof"][key]=value
            with self.assertRaises(ValueError):safe_report(altered,before)
        altered=copy.deepcopy(report)
        altered["observations"][0]["values"]["ricorrenza_testo"]="settimanale - venerdì"
        with self.assertRaises(ValueError):safe_report(altered,before)

    def test_unproved_season_hours_or_cancellations_in_recurrence_are_not_observed(self):
        for text in ("settimanale - mercoledì da giugno a settembre",
                     "settimanale - mercoledì dalle 8 alle 13",
                     "settimanale - mercoledì esclusi festivi",
                     "settimanale - mercoledì sospeso"):
            with self.subTest(text=text):
                base=[{**row("a"),"ricorrenza_testo":text}]
                self.assertEqual(select_pages(base,today=TODAY),[])
                after,report=preview(base,feed(),today=TODAY,apply=True,rights_verified=True)
                self.assertEqual(after,base)
                self.assertEqual(report["observations"],[])

    def test_qualified_weekly_records_remain_in_the_conflicting_venue_cohort(self):
        for url in (VENICE_OLD,"https://www.happings.com/it/mercato-settimanale-a-spinea.html"):
            for suffix in ("da giugno a settembre","dalle 8 alle 13","esclusi festivi","sospeso"):
                with self.subTest(url=url,suffix=suffix):
                    other=row("qualified",street="Via Contraddizione 10",url=url)
                    other["ricorrenza_testo"]="settimanale - mercoledì "+suffix
                    base=[row("target"),other]
                    after,report=preview(base,feed(),today=TODAY,apply=True,rights_verified=True)
                    self.assertEqual(after,base)
                    self.assertEqual(report["field_changes"],0)
                    self.assertEqual(report["observations"],[])
                    self.assertGreater(report["parser_counts"]["conflicting_previously_saved_location"],0)
                    self.assertTrue(safe_report(report,base))

    def test_qualified_market_on_another_weekday_does_not_block_this_cohort(self):
        other=row("qualified",day="venerdì",street="Via Contraddizione 10")
        other["ricorrenza_testo"]="settimanale - venerdì da giugno a settembre"
        base=[row("target"),other]
        after,report=preview(base,feed(),today=TODAY,apply=True,rights_verified=True)
        self.assertEqual(report["changed_ids"],["target"])
        self.assertEqual(after[1],other)
        self.assertTrue(safe_report(report,base))

    def test_parser_location_rejection_prevents_assignment_and_observation(self):
        for place in ("Via Nuova 1 (sospeso)","Via Nuova 1 ore 10.00","Via Nuova 1 (solo estate)"):
            for existing in ("",place):
                with self.subTest(place=place,existing=existing):
                    blob=SAMPLE.replace(b"Villaggio dei Fiori (la mattina)",place.encode("utf-8"))
                    pages=[{"requested_url":VENICE_OLD,"final_url":VENICE_NEW,"html":blob}]
                    base=[row("target",street=existing)]
                    after,report=preview(base,pages,today=TODAY,apply=True,rights_verified=True)
                    self.assertEqual(after,base)
                    self.assertEqual(report["observations"],[])
                    self.assertEqual(report["field_candidates"],0)
                    self.assertEqual(report["source_pages"][0]["source_rows"],4)
                    reason=("publisher_calendar_scope_unrepresented" if "estate" in place
                            else "publisher_only_vague_or_area_location")
                    self.assertEqual(report["parser_counts"][reason],1)
                    self.assertTrue(safe_report(report,base))

    def test_rejected_second_location_still_makes_source_identity_ambiguous(self):
        for place in ("Via Nuova 1 (sospeso)","Via Nuova 1 ore 10.00","Via Nuova 1 (solo estate)"):
            with self.subTest(place=place):
                extra=("<li>a Spinea, in "+place+"</li>\n<li>a Dolo").encode("utf-8")
                blob=SAMPLE.replace(b"<li>a Dolo",extra)
                pages=[{"requested_url":VENICE_OLD,"final_url":VENICE_NEW,"html":blob}]
                base=[row("target")]
                after,report=preview(base,pages,today=TODAY,apply=True,rights_verified=True)
                self.assertEqual(after,base)
                self.assertEqual(report["observations"],[])
                self.assertEqual(report["source_pages"][0]["source_rows"],5)
                self.assertEqual(report["parser_counts"]["no_unique_source_market_city_weekday"],1)
                self.assertTrue(safe_report(report,base))

    def test_failed_first_page_does_not_prevent_next_permitted_page(self):
        modena="https://www.happings.com/it/mercati-settimanali-a-modena.html"
        attempts=[]
        def get(url,**kwargs):
            attempts.append(url)
            if url==modena:raise OSError("source unavailable")
            return SAMPLE,VENICE_NEW
        failures=[]
        pages=fetch_pages([modena,VENICE_OLD],permission_confirmed=True,failures=failures,
            robots_fetch=lambda url,**kwargs:(b"User-agent: *\nAllow: /\n",url),
            page_fetch=get,sleep=lambda _:None)
        self.assertEqual(attempts,[modena,VENICE_OLD])
        self.assertEqual([p["requested_url"] for p in pages],[VENICE_OLD])
        self.assertEqual(failures,[{"requested_url":modena,"error_type":"OSError",
                                    "error_code":"connection_error"}])

if __name__=="__main__":
    unittest.main()
