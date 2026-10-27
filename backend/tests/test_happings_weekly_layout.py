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
    VENICE_NEW, VENICE_OLD, MAX_HTML_BYTES, parse, compare_saved_markets, verify,
    province_page_key, _origins_equivalent,
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

    def test_all_province_redirects_resolve_old_source_urls_not_just_venice(self):
        modena_old="https://www.happings.com/it/mercati-settimanali-a-modena.html"
        modena_new="https://www.happings.com/it/mercati-settimanali-a-modena-e-provincia/"
        padova_new="https://www.happings.com/it/mercati-settimanali-a-padova-e-provincia/"
        self.assertTrue(_origins_equivalent(modena_old,modena_new))
        self.assertTrue(_origins_equivalent(modena_new,modena_old))
        self.assertTrue(_origins_equivalent(VENICE_OLD,VENICE_NEW))
        self.assertFalse(_origins_equivalent(modena_old,padova_new))
        self.assertFalse(_origins_equivalent(
            "https://www.happings.com/it/mercato-settimanale-a-carpi.html",
            modena_new))
        self.assertFalse(_origins_equivalent(
            "https://evil.example/it/mercati-settimanali-a-modena.html",
            modena_new))
        # A prior version of the audit reported zero matches outside Veneto.
        modena_html=HTML.replace(b"Spinea",b"Carpi").replace(b"Venezia",b"Modena")
        old=[market("carpi-monday",city="Carpi",url=modena_old)]
        record=compare_saved_markets(old,modena_html,source_url=modena_new,today=TODAY)
        self.assertEqual(record["counts"]["same_publisher_page_catalog_rows"],1)
        self.assertEqual(record["counts"]["saved_market_missing_source_location"],1)
        self.assertEqual(record["catalog_fields_modified"],0)

    def test_old_ad_province_family_has_a_syntactic_key_without_inventing_redirects(self):
        # These ten old ad- URLs are present in the stored catalog. Pairing
        # synthetic URLs here proves normalization, never a live redirect.
        for province in ("agrigento","ancona","aosta","arezzo","asti",
                         "avellino","enna","imperia","isernia","oristano"):
            old=f"https://www.happings.com/it/mercati-settimanali-ad-{province}.html"
            canonical=f"https://www.happings.com/it/mercati-settimanali-a-{province}-e-provincia/"
            with self.subTest(province=province):
                self.assertEqual(province_page_key(old),province)
                self.assertEqual(province_page_key(canonical),province)
                self.assertTrue(_origins_equivalent(old,canonical))
                self.assertFalse(_origins_equivalent(old,VENICE_NEW))
        old="https://www.happings.com/it/mercati-settimanali-ad-ancona.html"
        fixture=HTML.replace(b"Venezia",b"Ancona").replace(b"Spinea",b"Agugliano")
        original=[market("agugliano-mercoledi",city="Agugliano",url=old)]
        report=compare_saved_markets(original,fixture,source_url=old,today=TODAY)
        self.assertEqual(report["matching_legacy_market_records"],1)
        self.assertEqual(report["counts"]["saved_market_missing_source_location"],1)

    def test_scope_key_rejects_unreviewed_paths_and_foreign_origins(self):
        for url in (
            "https://www.happings.com/it/mercati-settimanali-ad-ancona/",
            "https://www.happings.com/it/mercato-settimanale-a-ancona.html",
            "https://www.happings.com/it/mercati-settimanali-a-.html",
            "https://www.happings.com/it/mercati-settimanali-a--ancona.html",
            "https://www.happings.com/it/mercati-settimanali-ad-ancona.html?x=1",
            "https://www.happings.com/it/mercati-settimanali-ad-ancona.html#section",
            "https://www.happings.com:444/it/mercati-settimanali-ad-ancona.html",
            "http://www.happings.com/it/mercati-settimanali-ad-ancona.html",
            "https://evil.example/it/mercati-settimanali-ad-ancona.html",
        ):
            with self.subTest(url=url):
                self.assertIsNone(province_page_key(url))
                self.assertFalse(_origins_equivalent(url,url))

    def test_changed_block_or_heading_never_inherits_previous_weekday(self):
        first=(b'<div class="happings-seo-content">'
               b'<h3>Mercati del mercoledi nei comuni di Venezia</h3>'
               b'<ul><li>a Dolo, in Piazza San Valentino (la mattina)</li></ul>')
        for boundary in (
            b'</div><div class="happings-seo-content">',
            b'<h2>Mercati straordinari</h2>',
            b'<h3>Altre informazioni per visitatori</h3>',
        ):
            with self.subTest(boundary=boundary):
                fixture=(b'<html><body>'+first+boundary+
                         b'<ul><li>a Spinea, in Via Roma (la mattina)</li></ul>'
                         b'</div></body></html>')
                fixture=fixture.ljust(300,b' ')
                parsed=parse(fixture,source_url=VENICE_NEW)
                self.assertEqual([(r["city"],r["weekday"]) for r in parsed.rows],[("Dolo",2)])
                report=compare_saved_markets([market("spinea-mercoledi")],fixture,
                                            source_url=VENICE_NEW,today=TODAY)
                self.assertEqual(report["counts"]["no_matching_city_day_on_page"],1)

    def test_changed_ordered_list_cannot_be_skipped_or_joined_to_weekday(self):
        fixture=HTML.replace(
            b'<li>a Dolo, in Piazza San Valentino (la mattina)</li>',
            b'</ul><ol><li>a Dolo, in Piazza San Valentino (la mattina)</li></ol><ul>',
        )
        with self.assertRaisesRegex(ValueError,"unparsed listing items"):
            parse(fixture,source_url=VENICE_NEW)

    def test_ad_town_item_keeps_a_second_venue_ambiguous(self):
        fixture=HTML.replace(
            b'<li>a Dolo, in Piazza San Valentino (la mattina)</li>',
            b'<li>ad Agugliano, in Via Roma (il mattino)</li>',
        ).replace(b'Spinea',b'Agugliano')
        parsed=parse(fixture,source_url=VENICE_NEW)
        venues=[r for r in parsed.rows if r["city"]=="Agugliano" and r["weekday"]==2]
        self.assertEqual(len(venues),2)
        self.assertTrue(all(r["daypart"]=="morning_not_clock_hours" for r in venues))
        report=compare_saved_markets([market("agugliano-mercoledi",city="Agugliano")],
                                    fixture,source_url=VENICE_NEW,today=TODAY)
        self.assertEqual(report["counts"]["more_than_one_source_venue_on_city_day"],1)
        self.assertEqual(report["counts"].get("saved_market_missing_source_location",0),0)

    def test_unparsed_second_venue_cannot_make_first_venue_falsely_unique(self):
        for changed_item in (
            b'<li>a Spinea, Piazza Roma (la mattina)</li>',
            b'<li>a Spinea, in Piazza Roma<ul><li>Seconda sede</li></ul></li>',
        ):
            with self.subTest(item=changed_item):
                fixture=HTML.replace(
                    b'<li>a Dolo, in Piazza San Valentino (la mattina)</li>',changed_item)
                with self.assertRaisesRegex(ValueError,"unparsed listing items"):
                    compare_saved_markets([market("spinea-mercoledi")],fixture,
                                          source_url=VENICE_NEW,today=TODAY)

    def test_ambiguous_heading_or_incomplete_listing_is_quarantined(self):
        changed=HTML.replace(b'Mercati del sabato',b'Mercati del sabato e della domenica')
        with self.assertRaisesRegex(ValueError,"unparsed listing items or headings"):
            parse(changed,source_url=VENICE_NEW)
        incomplete=HTML[:HTML.index(b'  <h3>Mercati del sabato')]
        with self.assertRaisesRegex(ValueError,"incomplete"):
            parse(incomplete,source_url=VENICE_NEW)

    def test_explicit_heading_province_must_match_observed_source_url(self):
        with self.assertRaisesRegex(ValueError,"heading crossed province"):
            parse(HTML,source_url="https://www.happings.com/it/mercati-settimanali-a-modena-e-provincia/")
        # Apostrophes and hyphens normalize without guessing a different town.
        aquila=HTML.replace(b'Venezia',b"L'Aquila")
        self.assertEqual(len(parse(aquila,source_url=
            "https://www.happings.com/it/mercati-settimanali-a-l-aquila.html").rows),5)

    def test_non_content_inline_text_never_becomes_a_street(self):
        for tag in ("script","style","template","noscript"):
            with self.subTest(tag=tag):
                hidden=(f'<{tag}>Via Errata</{tag}>').encode()
                fixture=HTML.replace(b'Villaggio dei Fiori',hidden+b'Villaggio dei Fiori')
                parsed=parse(fixture,source_url=VENICE_NEW)
                wed=next(row for row in parsed.rows
                         if row["city_key"]=="spinea" and row["weekday"]==2)
                self.assertEqual(wed["place"],"Villaggio dei Fiori")
                self.assertTrue(wed["has_specific_location"])

    def test_non_content_duplicate_listing_is_never_counted(self):
        ghost=(b'<div class="happings-seo-content">'
               b'<h3>Mercati del venerdi nei comuni di Padova</h3>'
               b'<ul><li>a Spinea, in Via Errata (la mattina)</li></ul></div>')
        for tag in (b'template',b'noscript'):
            with self.subTest(tag=tag):
                fixture=HTML.replace(b'<html><body>',
                    b'<html><body><'+tag+b'>'+ghost+b'</'+tag+b'>')
                parsed=parse(fixture,source_url=VENICE_NEW)
                self.assertEqual(len(parsed.rows),5)
                self.assertEqual(parsed.seo_blocks,1)

    def test_non_content_nested_heading_does_not_change_listing_weekday(self):
        fixture=HTML.replace(
            b'<ul>\n    <li>a Spinea',
            b'<template><h3>Mercati del venerdi nei comuni di Padova</h3></template>'
            b'<ul>\n    <li>a Spinea',
        )
        parsed=parse(fixture,source_url=VENICE_NEW)
        self.assertEqual(parsed.weekday_headings,[2,5,6])
        self.assertEqual(parsed.rows[0]["weekday"],2)

    def test_qualified_weekday_heading_is_not_an_ordinary_weekly_section(self):
        for heading in (
            b'Mercati del mercoledi sospesi',
            b'Mercati del mercoledi straordinari',
            b'Mercati del mercoledi solo in estate',
        ):
            with self.subTest(heading=heading):
                fixture=HTML.replace(
                    b'Mercati del mercoled&#236; nei comuni di Venezia',heading)
                with self.assertRaisesRegex(ValueError,"unparsed listing items or headings"):
                    parse(fixture,source_url=VENICE_NEW)

    def test_explicit_listing_title_cannot_cross_province(self):
        fixture=HTML.replace(
            b'Mercati settimanali nei comuni in provincia di Venezia',
            b'Mercati settimanali nei comuni in provincia di Padova',
        )
        with self.assertRaisesRegex(ValueError,"heading crossed province"):
            parse(fixture,source_url=VENICE_NEW)
        generic_weekdays=fixture.replace(b' nei comuni di Venezia',b'')
        with self.assertRaisesRegex(ValueError,"heading crossed province"):
            parse(generic_weekdays,source_url=VENICE_NEW)

    def test_clock_hours_must_not_be_imported_as_part_of_an_address(self):
        for label in (
            b'Via Roma (dalle 08:00 alle 13:00)',
            b'Via Roma (ore 8-13)',
            b'Via Roma dalle 8 alle 13',
            b'Via Roma (08.00-13.00)',
        ):
            with self.subTest(label=label):
                fixture=HTML.replace(b'Villaggio dei Fiori (la mattina)',label)
                parsed=parse(fixture,source_url=VENICE_NEW)
                wed=next(row for row in parsed.rows
                         if row["city_key"]=="spinea" and row["weekday"]==2)
                self.assertFalse(wed["has_specific_location"])
                report=compare_saved_markets([market("spinea-mercoledi")],fixture,
                                            source_url=VENICE_NEW,today=TODAY)
                self.assertEqual(report["counts"].get("saved_market_missing_source_location",0),0)
                self.assertEqual(report["catalog_fields_modified"],0)

    def test_numeric_street_names_and_building_numbers_remain_specific(self):
        for label in (b'Piazza 8 Marzo',b'Via XX Settembre 13'):
            with self.subTest(label=label):
                fixture=HTML.replace(b'Villaggio dei Fiori',label)
                parsed=parse(fixture,source_url=VENICE_NEW)
                self.assertTrue(parsed.rows[0]["has_specific_location"])

    def test_conditional_or_retired_locations_are_not_ordinary_addresses(self):
        for label in (
            b'Via Roma (mercato sospeso)',
            b'Via Roma (dal 2025 trasferito in Piazza Italia)',
            b'Via Roma (solo in estate)',
            b'Via Roma, mercato annullato',
            b'Via Roma, esclusi i festivi',
            b'Via Roma, temporaneamente spostato in Via Milano',
        ):
            with self.subTest(label=label):
                fixture=HTML.replace(b'Villaggio dei Fiori (la mattina)',label)
                parsed=parse(fixture,source_url=VENICE_NEW)
                self.assertFalse(parsed.rows[0]["has_specific_location"])
                report=compare_saved_markets([market("spinea-mercoledi")],fixture,
                                            source_url=VENICE_NEW,today=TODAY)
                self.assertEqual(report["counts"].get("saved_market_missing_source_location",0),0)

    def test_conditional_second_venue_still_prevents_a_unique_match(self):
        fixture=HTML.replace(
            b'a Dolo, in Piazza San Valentino (la mattina)',
            b'a Spinea, in Via Roma (solo in estate)',
        )
        report=compare_saved_markets([market("spinea-mercoledi")],fixture,
                                    source_url=VENICE_NEW,today=TODAY)
        self.assertEqual(report["counts"].get("saved_market_missing_source_location",0),0)
        self.assertEqual(report["counts"]["more_than_one_source_venue_on_city_day"],1)

    def test_multiple_venues_same_city_day_cannot_assign_address(self):
        extra=HTML.replace(
            b'<li>a Dolo, in Piazza San Valentino (la mattina)</li>',
            b'<li>a Spinea, in Piazza dei Fiori (la mattina)</li>',
        )
        result=compare_saved_markets([market("spinea-no-street")],extra,
                                    source_url=VENICE_NEW,today=TODAY)
        self.assertEqual(result["counts"]["more_than_one_source_venue_on_city_day"],1)
        self.assertEqual(result["counts"].get("saved_market_missing_source_location",0),0)

    def test_numbered_markets_of_one_town_are_that_town_and_stay_separate(self):
        numbered=HTML.replace(
            b'<li>a Dolo, in Piazza San Valentino (la mattina)</li>',
            b'<li>a Spinea 1, in centro (la mattina)</li><li>a Spinea 2, in centro (la mattina)</li>',
        )
        rows=[r for r in parse(numbered,source_url=VENICE_NEW).rows if r["weekday"]==2]
        self.assertEqual([(r["city"],r["city_label"]) for r in rows if r["city_label"].startswith("Spinea ")],
                         [("Spinea","Spinea 1"),("Spinea","Spinea 2")])
        result=compare_saved_markets([market("spinea-no-street")],numbered,
                                    source_url=VENICE_NEW,today=TODAY)
        self.assertEqual(result["counts"]["more_than_one_source_venue_on_city_day"],1)

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
