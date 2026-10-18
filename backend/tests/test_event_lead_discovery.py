"""Regression/negative tests for scheduled EVENT LEADS, never confirmed markets."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
from event_lead_discovery import (
    FIRENZE_URL, EVENTI_ROBOTS, EVENTI_BASE,
    BOLOGNA_BASE, allowed_request, build_bologna_url, check_robots,
    collect, kind_for_title, parse_bologna_pages, parse_eventiesagre_links,
    parse_firenze, planned_listing_urls, validate_report, verify_registry,
)
REGISTRY = json.loads((ROOT/"backend/data/event-lead-source-contracts.json").read_text("utf-8"))
TODAY = date(2026, 10, 18)


def florence():
    return {
        "type": "FeatureCollection",
        "totalFeatures": 4,
        "features": [
            {"type": "Feature", "id": 57, "geometry": {"type": "MultiPoint"},
             "properties": {
                 "titolo": "Mercato di Natale in Piazza Santa Croce",
                 "comuni": "Firenze", "data_inizio": "14/11/2026",
                 "data_fine": "20/12/2026",
                 "feelflorence_link": "https://www.feelflorence.it/it/eventi/mercato-di-natale-piazza-santa-croce",
                 "email": "do-not-store@example.com", "descrizione": "proprietary event description"}},
            {"type": "Feature", "id": 58, "geometry": {},
             "properties": {
                 "titolo": "Italian Opera", "comuni": "Firenze",
                 "data_inizio": "01/01/2026", "data_fine": "30/12/2026",
                 "feelflorence_link": "https://www.feelflorence.it/it/eventi/italian-opera"}},
            {"type": "Feature", "id": 59, "geometry": {},
             "properties": {
                 "titolo": "Mercato dell'Antiquariato", "comuni": "Firenze",
                 "data_inizio": "21/01/2023", "data_fine": "30/12/2023",
                 "feelflorence_link": "https://www.feelflorence.it/it/eventi/mercato-antiquariato"}},
            {"type": "Feature", "id": 60, "geometry": {},
             "properties": {
                 "titolo": "Fiera delle Idee", "comuni": "Firenze",
                 "data_inizio": "20/10/2026", "data_fine": "20/10/2026",
                 "feelflorence_link": "https://www.feelflorence.it/it/eventi/fiera-delle-idee"}},
        ],
    }


def bologna():
    return {
        "total_count": 2,
        "results": [
            {"id": "543010", "title": "Mercatino dell'Antiquariato in Piazza",
             "address": "Piazza Maggiore, Bologna", "start": "2026-11-18",
             "end": None, "url": "https://culturabologna.it/events/543010",
             "coordinate": {"lon": 11.34, "lat": 44.49}},
            {"id": "576593", "title": "Fiera delle Idee | Laboratori per il benessere",
             "address": "Via di Test 1", "start": "2026-10-20",
             "end": None, "url": "https://culturabologna.it/events/576593"},
        ],
    }


def listing():
    return b"""
    <div>Eventi in Evidenza<a href="/Mercatini_Antiquariato/20001_Promoted.html">
    Sponsored placement</a></div>
    <h2>Elenco Eventi da 1 a 2 di 2</h2>
    <a href="/Mercatini_Artigianato/21165052_Mercantico+A+Cascina.html">A</a>
    <a href="/Mercatini_Antiquariato/21180696_Mercato+Dell+antiquariato.html">B</a>
    <a href="/Eventi_Sagre/21105395_Sagra.html">Not a market-link category</a>
    <h2>Elenco Eventi da 1 a 2 di 2</h2>
    <a href="/Mercatini_Usato/88888_Footer.html">footer</a>
    """


def baseline():
    return [
        {"slug": "fi-other", "citta": "Firenze", "nome": "Mercato ortofrutticolo",
         "indirizzo": "Via del Test"},
        {"slug": "bo-actual", "citta": "Bologna",
         "nome": "Mercatino Antiquariato Piazza", "indirizzo": "Piazza Maggiore"},
    ]


class EventLeadDiscoveryTests(unittest.TestCase):

    def test_source_contracts_are_three_frozen_research_layouts(self):
        self.assertEqual(set(verify_registry(REGISTRY)), {
            "firenze-feelflorence", "bologna-agenda", "eventiesagre-index"
        })
        bad = copy.deepcopy(REGISTRY)
        bad["market_import_permission"] = True
        with self.assertRaisesRegex(ValueError, "Untrusted"):
            verify_registry(bad)
        bad = copy.deepcopy(REGISTRY)
        bad["sources"][2]["fields_saved"].append("event_description")
        with self.assertRaisesRegex(ValueError, "cannot supply event facts"):
            verify_registry(bad)
        bad = copy.deepcopy(REGISTRY)
        bad["sources"][0]["url"] = "https://evil.example/markets"
        with self.assertRaises(ValueError):
            verify_registry(bad)

    def test_http_scope_disallows_third_party_detail_scraping_or_redirects(self):
        self.assertTrue(allowed_request(FIRENZE_URL))
        self.assertTrue(allowed_request(EVENTI_ROBOTS))
        self.assertTrue(allowed_request(build_bologna_url(TODAY)))
        for url in (
            "http://www.eventiesagre.it/robots.txt",
            "https://www.eventiesagre.it/Mercatini_Antiquariato/21180696_Example.html",
            "https://evil.com/cerca/Mercatini/Antiquariato/mesi/Toscana/prov/cit/rilib",
            "https://www.eventiesagre.it/cerca/Mercatini/Antiquariato/mesi/Toscana/prov/cit/rilib?all=1",
            "https://datigis.comune.fi.it/resources/open-data/eventi-a-firenze/feelflorence_eventi.geojson?redirect=1",
            "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/eventi-bologna-agenda-cultura/records?where=1%3D1&limit=1000",
        ):
            with self.subTest(url=url):
                self.assertFalse(allowed_request(url))

    def test_firenze_real_schema_filters_unrelated_and_expired_events(self):
        leads, data = parse_firenze(json.dumps(florence()).encode(), TODAY)
        self.assertEqual(data["rows_examined"], 4)
        self.assertEqual(len(leads), 1)
        self.assertEqual(leads[0]["id"], "firenze-feelflorence:57")
        self.assertFalse(leads[0]["opening_confirmed"])
        self.assertEqual(leads[0]["start"], "2026-11-14")
        self.assertNotIn("email", leads[0])
        self.assertNotIn("description", leads[0])
        self.assertNotIn("coordinates", leads[0])
        raw = florence()
        raw["features"][1]["id"] = 57
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            parse_firenze(json.dumps(raw).encode(), TODAY)
        raw = florence()
        raw["features"][0]["properties"].pop("data_fine")
        with self.assertRaisesRegex(ValueError, "reviewed fields"):
            parse_firenze(json.dumps(raw).encode(), TODAY)

    def test_bologna_bounded_paging_and_market_semantics(self):
        leads, data = parse_bologna_pages([json.dumps(bologna()).encode()], TODAY)
        self.assertEqual(len(leads), 1)
        self.assertEqual(data["not_matching_market_scope"], 1)
        self.assertEqual(leads[0]["source_url"], "https://culturabologna.it/events/543010")
        bad = bologna()
        bad["results"][1]["id"] = "543010"
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            parse_bologna_pages([json.dumps(bad).encode()], TODAY)
        bad = bologna()
        bad["total_count"] = 151
        with self.assertRaisesRegex(ValueError, "count"):
            parse_bologna_pages([json.dumps(bad).encode()], TODAY)
        bad = bologna()
        bad["results"][0]["url"] = "https://evil.example/market"
        leads, _ = parse_bologna_pages([json.dumps(bad).encode()], TODAY)
        self.assertEqual(leads, [])

    def test_proprietary_index_extracts_only_href_after_list_heading(self):
        links = parse_eventiesagre_links(listing())
        self.assertEqual([x["id"] for x in links], ["21165052", "21180696"])
        self.assertTrue(all(set(row) == {"id", "url"} for row in links))
        with self.assertRaisesRegex(ValueError, "markup changed"):
            parse_eventiesagre_links(b"<html><h1>No listings</h1></html>")
        with self.assertRaisesRegex(ValueError, "first-page quota"):
            parse_eventiesagre_links(listing(), max_links=1)

    def test_robot_policy_checked_and_denial_is_not_overridden(self):
        pages = planned_listing_urls(TODAY)
        self.assertTrue(all(allowed_request(x) for x in pages))
        ok = b"User-agent: *\nAllow: /\nDisallow: /private/\n"
        self.assertTrue(check_robots(lambda _: ok, pages))
        denied = b"User-agent: *\nDisallow: /cerca/Mercatini/\n"
        with self.assertRaisesRegex(ValueError, "denies"):
            check_robots(lambda _: denied, pages)

    @patch("event_lead_discovery.time.sleep", lambda _: None)
    def test_all_sources_collect_without_changing_the_market_catalog(self):
        old = baseline()
        frozen = copy.deepcopy(old)
        seen = []
        def fake_fetch(url):
            seen.append(url)
            if url == FIRENZE_URL:
                return json.dumps(florence()).encode()
            if url.startswith(BOLOGNA_BASE):
                return json.dumps(bologna()).encode()
            if url == EVENTI_ROBOTS:
                return b"User-agent: *\nAllow: /\n"
            return listing()
        report = collect(REGISTRY, old, today=TODAY, fetch=fake_fetch)
        self.assertEqual(old, frozen)
        self.assertTrue(validate_report(report, REGISTRY, 2))
        self.assertEqual(report["catalog_imports"], 0)
        self.assertEqual(report["individual_event_confirmations"], 0)
        self.assertEqual(report["fresh_official_leads"], 2)
        self.assertEqual(report["new_external_url_pointers"], 2)
        third_party = [x for x in report["leads"]
                       if x["source_id"] == "eventiesagre-index"]
        self.assertEqual(len(third_party), 2)
        self.assertTrue(all("title" not in x and "start" not in x
                            and x["opening_confirmed"] is False for x in third_party))
        self.assertEqual(len(seen), 5)

    @patch("event_lead_discovery.time.sleep", lambda _: None)
    def test_network_outage_does_not_remove_old_records_or_confirm_closure(self):
        original = collect(REGISTRY, baseline(), today=TODAY, offline=True)
        self.assertEqual(original["checked_sources"][0]["state"], "offline_skipped")
        one = collect(REGISTRY, baseline(), today=TODAY,
                      fetch=lambda _: (_ for _ in ()).throw(OSError("offline")))
        self.assertTrue(all(x["state"] == "source_unavailable_or_schema_review"
                            for x in one["checked_sources"]))
        self.assertEqual(one["baseline_market_ids_preserved"], 2)
        self.assertEqual(one["new_market_records_created"], 0)

    def test_explicit_false_positive_titles_are_not_markets(self):
        self.assertIsNone(kind_for_title("Fiera delle Idee | Laboratori"))
        self.assertIsNone(kind_for_title("Live al Mercato Sonato"))
        self.assertEqual(kind_for_title("Fiera dell'Antiquariato"), "fair_review")
        self.assertIsNone(kind_for_title("Concerto alla Chiesa di Santa Maria"))
        self.assertEqual(kind_for_title("Sagra delle castagne"), "related_sagra_review")


if __name__ == "__main__":
    unittest.main()
