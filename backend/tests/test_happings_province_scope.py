"""Real row identity, geographic names and source-qualified provincial facts."""
from __future__ import annotations

import copy
import hashlib
import json
import sys
import unittest
from collections import Counter
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from happings_source_enrichment import preview, safe_report
from happings_weekly_layout import parse, compare_saved_markets, VENICE_OLD, VENICE_NEW
from recurrence_refresh import refresh_record, temporal_scope_hold
from stored_market_sibling_proposals import safe_stored_street

TODAY = date(2026, 10, 20)
FIXTURES = Path(__file__).parent / "fixtures/happings_weekly"


def page(items, *, province="Venezia"):
    return (f'<!doctype html><html lang="it"><head><title>Mercati settimanali: prova offline</title></head><body>'
            f'<div class="happings-seo-content"><h2>Mercati settimanali nei comuni in provincia di {province}</h2>'
            f'<h3>Mercati del mercoledì nei comuni di {province}</h3><ul>'
            + "".join(f"<li>a {city}, in {place} (la mattina)</li>" for city, place in items)
            + '</ul></div></body></html>').encode("utf-8")


def market(**updates):
    row = {"slug": "mercato-settimanale-spinea", "nome": "Mercato settimanale di Spinea",
           "citta": "Spinea", "provincia": "VE", "regione": "Veneto", "categoria": "misto",
           "indirizzo": "", "orario_testo": "", "ricorrenza_testo": "settimanale - mercoledì",
           "url_fonte": VENICE_OLD, "fonte": "happings.com", "fonti": [],
           "date": ["2026-10-21"], "date_quality": "prevista", "verificato_il": "",
           "status": "non_confermato", "position_quality": "sconosciuta",
           "lat": None, "lng": None, "aggiornato_il": "2026-06-05"}
    return {**row, **updates}


class ProvincialScopeTests(unittest.TestCase):
    def test_real_trieste_fixture_keeps_52_distinct_rows_in_seven_sections(self):
        raw = (FIXTURES / "trieste_52_rows.html").read_bytes()
        manifest = json.loads((FIXTURES / "manifest.json").read_text())
        self.assertEqual(hashlib.sha256(raw).hexdigest(), manifest["fixture_sha256"])
        self.assertNotEqual(manifest["fixture_sha256"], manifest["source_capture"]["sha256"])
        parsed = parse(raw, source_url=manifest["source_capture"]["final_url"], observed_on=TODAY)
        self.assertEqual(len(parsed.rows), 52)
        self.assertEqual(len({(r["city_key"], r["weekday"], r["place"]) for r in parsed.rows}), 52)
        self.assertEqual(Counter(r["weekday"] for r in parsed.rows), {0: 9, 1: 8, 2: 9, 3: 9, 4: 8, 5: 8, 6: 1})
        self.assertEqual(Counter(r["city"] for r in parsed.rows), {"Trieste": 51, "Muggia": 1})
        self.assertEqual(sum(r["has_specific_location"] for r in parsed.rows), 52)
        self.assertEqual(len(parsed.weekday_headings), 7)
        url = manifest["source_capture"]["final_url"]
        old = [market(slug=f"fixture-trieste-{day}", citta="Trieste", provincia="TS",
                      regione="Friuli-Venezia Giulia", url_fonte=url,
                      ricorrenza_testo="settimanale - " + day)
               for day in ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica")]
        saved = copy.deepcopy(old)
        compared = compare_saved_markets(old, raw, source_url=url, today=TODAY)
        self.assertEqual(compared["publisher_items_detected"], 52)
        self.assertEqual(compared["counts"]["more_than_one_source_venue_on_city_day"], 6)
        self.assertEqual(compared["catalog_fields_modified"], 0)
        self.assertEqual(old, saved)

    def test_season_words_in_complete_geographic_names_are_not_calendar_qualifiers(self):
        for place in ("Passeggiata d'Inverno", "Passeggiata d’Inverno", "Via Inverno", "Via dell'Estate", "Viale della Primavera"):
            with self.subTest(place=place):
                parsed = parse(page([("Spinea", place)]), source_url=VENICE_NEW, observed_on=TODAY)
                self.assertEqual(parsed.rows[0]["place"], place)
                self.assertIsNone(parsed.rows[0]["calendar_scope"])
                self.assertTrue(parsed.rows[0]["has_specific_location"])
        parsed = parse(page([("Inverno e Monteleone", "Piazza Roma")]), source_url=VENICE_NEW, observed_on=TODAY)
        self.assertEqual(parsed.rows[0]["city_key"], "inverno e monteleone")
        self.assertIsNone(parsed.rows[0]["calendar_scope"])

    def test_walkway_prefix_does_not_make_a_vague_label_or_prose_a_named_address(self):
        for place in ("Passeggiata", "Passeggiata per il centro", "passeggiata per le vie del paese",
                      "Passeggiata lungo il fiume", "Passeggiata verso Piazza Roma", "Passeggiata di 2 ore",
                      "Passeggiata su richiesta", "Passeggiata da definire", "Passeggiata mercati settimanali"):
            with self.subTest(place=place):
                self.assertFalse(safe_stored_street(place))

    def test_explicit_city_qualifiers_are_separate_without_ordinary_weekly_assignment(self):
        for qualifier, reason in (("estivo", "seasonal_scope_unrepresented"),
                                  ("invernale", "seasonal_scope_unrepresented"),
                                  ("ogni 15gg", "interval_scope_unrepresented"),
                                  ("quindicinale", "interval_scope_unrepresented")):
            with self.subTest(qualifier=qualifier):
                blob = page([("Spinea (" + qualifier + ")", "Via Roma")])
                parsed = parse(blob, source_url=VENICE_NEW, observed_on=TODAY)
                source = parsed.rows[0]
                self.assertEqual(source["city"], "Spinea")
                self.assertEqual(source["city_label"], "Spinea (" + qualifier + ")")
                self.assertEqual(source["calendar_scope"]["qualifiers"],
                                 [{"field": "city", "text": qualifier, "reason": reason}])
                self.assertFalse(source["calendar_scope"]["forecast_allowed"])
                self.assertFalse(source["has_specific_location"])
                before = [market()]
                after, report = preview(before, [{"requested_url": VENICE_OLD, "final_url": VENICE_NEW,
                                                 "html": blob}], today=TODAY, apply=True, rights_verified=True)
                self.assertEqual(after, before)
                self.assertEqual(report["observations"], [])
                self.assertEqual(report["parser_counts"]["publisher_calendar_scope_unrepresented"], 1)
                self.assertTrue(safe_report(report, before))

    def test_seasonal_second_venue_stays_in_ambiguity_even_after_city_qualifier_is_split(self):
        blob = page([("Spinea", "Via Roma"), ("Spinea (estivo)", "Piazza Italia")])
        parsed = parse(blob, source_url=VENICE_NEW, observed_on=TODAY)
        self.assertEqual(len(parsed.rows), 2)
        self.assertEqual({row["city_key"] for row in parsed.rows}, {"spinea"})
        before = [market()]
        after, report = preview(before, [{"requested_url": VENICE_OLD, "final_url": VENICE_NEW,
                                         "html": blob}], today=TODAY, apply=True, rights_verified=True)
        self.assertEqual(after, before)
        self.assertEqual(report["parser_counts"]["no_unique_source_market_city_weekday"], 1)

    def test_separate_temporal_qualifier_cannot_hide_behind_a_real_street_name(self):
        for place in ("Passeggiata d’Inverno (estivo)", "Passeggiata d’Inverno (ogni 15gg)",
                      "Via Roma in inverno", "Via Roma, solo in estate", "Via Roma quindicinale"):
            with self.subTest(place=place):
                source = parse(page([("Spinea", place)]), source_url=VENICE_NEW, observed_on=TODAY).rows[0]
                self.assertEqual(source["place_label"], place)
                self.assertTrue(source["calendar_scope"]["qualifiers"])
                self.assertFalse(source["has_specific_location"])

    def test_geonym_can_receive_exact_address_without_changing_calendar(self):
        before = [market()]
        blob = page([("Spinea", "Passeggiata d’Inverno")])
        after, report = preview(before, [{"requested_url": VENICE_OLD, "final_url": VENICE_NEW,
                                         "html": blob}], today=TODAY, apply=True, rights_verified=True)
        self.assertEqual(after[0]["indirizzo"], "Passeggiata d’Inverno")
        for field in ("date", "date_quality", "ricorrenza_testo", "verificato_il", "orario_testo"):
            self.assertEqual(after[0][field], before[0][field])
        self.assertTrue(safe_report(report, before))

    def test_existing_qualified_identity_still_retires_unsupported_predictions(self):
        for qualifier in ("estivo", "invernale", "ogni 15gg", "quindicinale"):
            with self.subTest(qualifier=qualifier):
                row = market(nome="Mercato settimanale di Spinea (" + qualifier + ")")
                self.assertIsNotNone(temporal_scope_hold(row))
                refreshed, _ = refresh_record(row, TODAY)
                self.assertEqual(refreshed["date"], [])
                self.assertEqual(refreshed["slug"], row["slug"])
                self.assertEqual(refreshed["nome"], row["nome"])

    def test_explicit_month_or_date_window_is_never_an_ordinary_street_or_calendar(self):
        for qualifier in ("da giugno a settembre", "dal 1 giugno al 30 settembre", "dal 01/06 al 30/09"):
            with self.subTest(qualifier=qualifier):
                blob = page([("Spinea", "Via Roma (" + qualifier + ")")])
                source = parse(blob, source_url=VENICE_NEW, observed_on=TODAY).rows[0]
                self.assertEqual(source["place"], "Via Roma")
                self.assertEqual(source["place_label"], "Via Roma (" + qualifier + ")")
                self.assertEqual(source["calendar_scope"]["qualifiers"],
                                 [{"field": "place", "text": qualifier, "reason": "date_range_scope_unrepresented"}])
                self.assertFalse(source["has_specific_location"])
                before = [market()]
                after, report = preview(before, [{"requested_url": VENICE_OLD, "final_url": VENICE_NEW,
                                                 "html": blob}], today=TODAY, apply=True, rights_verified=True)
                self.assertEqual(after, before)
                self.assertEqual(report["observations"], [])
                self.assertEqual(report["parser_counts"]["publisher_calendar_scope_unrepresented"], 1)

    def test_street_month_names_do_not_become_date_windows(self):
        for place in ("Via XX Settembre", "Piazza Primo Maggio", "Passeggiata d’Inverno"):
            with self.subTest(place=place):
                source = parse(page([("Inverno e Monteleone", place)]), source_url=VENICE_NEW, observed_on=TODAY).rows[0]
                self.assertEqual(source["city"], "Inverno e Monteleone")
                self.assertEqual(source["place"], place)
                self.assertIsNone(source["calendar_scope"])
                self.assertTrue(source["has_specific_location"])


if __name__ == "__main__":
    unittest.main()
