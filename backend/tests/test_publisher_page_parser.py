import copy
import hashlib
import html
import json
from pathlib import Path
import re
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from publisher_page_parser import parse_page


BACKEND = Path(__file__).resolve().parents[1]
FIXTURES = Path(__file__).parent / "fixtures" / "primary-market-evidence-2026-10-19"
URL = "https://publisher.example/mercati/"


def contract(**changes):
    base = {
        "source_id": "test-publisher", "category": "misto", "market_kind": "ordinary",
        "cadence": "weekly", "content_scope": {"tag": "div", "class": "entry-content"},
        "municipalities": [
            {"citta": "Comune Alfa", "provincia": "AA", "regione": "Regione Uno"},
            {"citta": "Comune Beta", "provincia": "BB", "regione": "Regione Due"},
        ],
    }
    base.update(changes)
    return base


def page(body, *, updated="2026-03-23", before="", after="", metadata=""):
    stamp = f"<p>Ultimo aggiornamento: {updated}</p>" if updated else ""
    return (f"<html><head>{metadata}</head><body>{before}"
            f'<div class="entry-content">{body}{stamp}</div>{after}</body></html>')


def block(city="Comune Alfa", when="ogni lunedì", where="Piazza Uno", hours=None):
    timing = f"<br><strong>Orario:</strong> {html.escape(hours)}" if hours is not None else ""
    return (f"<p><strong>{html.escape(city)}</strong><br>"
            f"<strong>Quando:</strong> {html.escape(when)}<br>"
            f"<strong>Dove:</strong> {html.escape(where)}{timing}</p>")


def parse(body, **kwargs):
    return parse_page(page(body), source_url=URL, contract=contract(**kwargs))


def source_contract(kind):
    gazetteer = json.loads((BACKEND / "data" / "istat-comuni-2026.json").read_text())
    municipalities = [
        {"citta": city, "provincia": province, "regione": region}
        for region, places in gazetteer["provinces_by_region"].items()
        for city, province in places.items() if province == "RA"
    ]
    value = contract(source_id="bassa-romagna-" + kind, municipalities=municipalities)
    if kind == "weekly":
        value.update(start_heading="MERCATI SETTIMANALI", end_heading="FIERE DOMENICALI",
                     min_rows=20, max_rows=60, min_city_blocks=9, max_city_blocks=15)
    else:
        value.update(market_kind="farmers", category="contadino", min_rows=6, max_rows=30,
                     min_city_blocks=6, max_city_blocks=15)
    return value


def fixture(kind):
    return (FIXTURES / ("bassa-romagna-" + kind + ".html")).read_bytes()


def projection(rows):
    return sorted((row["source_row_id"], row["citta"], row["localita"], row["weekday"],
                   row["indirizzo"], row["orario_testo"], row["cadenza"],
                   tuple(row["issues"])) for row in rows)


class PublisherPageParserTests(unittest.TestCase):
    def test_weekly_entire_page_preserves_every_city_day_and_fraction(self):
        result = parse_page(fixture("weekly"), source_url=URL, contract=source_contract("weekly"))
        self.assertTrue(result["complete"], result["issues"])
        self.assertEqual(result["metrics"]["city_blocks"], 9)
        self.assertEqual(result["metrics"]["fraction_rows"], 7)
        expected = [
            ("Alfonsine", "", 0, "Piazza della Resistenza"),
            ("Alfonsine", "", 3, "Piazza Monti"),
            ("Alfonsine", "Filo", 2, "Piazza Margotti"),
            ("Bagnacavallo", "", 5, "Piazza della Libertà e nelle vie adiacenti"),
            ("Bagnacavallo", "", 3, "Largo De Gasperi"),
            ("Bagnacavallo", "Villanova di Bagnacavallo", 4, "Piazza Matteucci e largo Tre Giunchi"),
            ("Bagnara di Romagna", "", 0, "Piazza Marconi"),
            ("Conselice", "", 5, "Piazza F. Foresti e in Via Garibaldi"),
            ("Conselice", "Lavezzola", 5, "Piazza Caduti"),
            ("Conselice", "San Patrizio", 1, "Via Mameli"),
            ("Cotignola", "", 4, "Piazza Vittorio Emanuele II e/o Piazza Mazzini"),
            ("Cotignola", "Barbiano", 1, "Piazza Alberico"),
            ("Fusignano", "", 4, "Corso Emaldi"),
            ("Fusignano", "", 1, "Piazza Corelli"),
            ("Lugo", "", 2, "Pavaglione e centro storico"),
            ("Lugo", "San Bernardino", 0, "Piazza della Pace"),
            ("Lugo", "Voltana", 1, "Piazza dell’Unità"),
            ("Massa Lombarda", "", 1, "Piazza Mazzini e vie del centro"),
            ("Massa Lombarda", "", 4, "Piazza Mazzini e vie del centro"),
            ("Sant'Agata sul Santerno", "", 1, "Largo Margherita di Savoia"),
        ]
        actual = [(r["citta"], r["localita"], r["weekday"], r["indirizzo"]) for r in result["rows"]]
        self.assertEqual(sorted(actual), sorted(expected))
        self.assertTrue(all(r["orario_testo"] == "" and r["orari"] == [] for r in result["rows"]))
        self.assertEqual(result["fonte_aggiornata_il"], "2026-03-23")
        self.assertEqual(result["source_sha256"], hashlib.sha256(fixture("weekly")).hexdigest())

    def test_farmers_entire_page_preserves_all_hours_and_cadence(self):
        result = parse_page(fixture("farmers"), source_url=URL, contract=source_contract("farmers"))
        self.assertTrue(result["complete"], result["issues"])
        self.assertEqual(len(result["rows"]), 6)
        rows = {r["citta"]: r for r in result["rows"]}
        self.assertEqual({name: r["orario_testo"] for name, r in rows.items()}, {
            "Alfonsine": "07:00–13:00",
            "Bagnara di Romagna": "Estate: 16:00–19:00; Inverno: 14:00–17:00",
            "Conselice": "Inverno: 09:30–12:30; Estate: 08:30–11:30",
            "Lugo": "07:00–14:00",
            "Massa Lombarda": "Maggio: 15:30–19:00; giugno–settembre: 15:00–19:00; ottobre–dicembre: 14:30–18:00",
            "Sant'Agata sul Santerno": "09:30–12:00",
        })
        self.assertEqual(rows["Massa Lombarda"]["indirizzo"], "Via Dini e Salvalai 34 (zona stadio – Parco Piave)")
        self.assertEqual(rows["Sant'Agata sul Santerno"]["cadenza"], "fortnightly")
        self.assertEqual({r["market_kind"] for r in rows.values()}, {"farmers"})
        self.assertEqual({r["fonte_aggiornata_il"] for r in rows.values()}, {"2026-01-27"})
        for row in rows.values():
            self.assertFalse(set(row) & {"date", "status", "lat", "lng", "verificato_il", "stagione_inizio", "stagione_fine"})

    def test_changed_source_hours_and_address_retain_semantic_identity(self):
        first = parse(block(hours="08:00–13:00"))
        second = parse(block(where="Piazza Due", hours="08:30–14:00"))
        self.assertEqual(first["rows"][0]["source_row_id"], second["rows"][0]["source_row_id"])
        self.assertNotEqual(first["source_sha256"], second["source_sha256"])
        self.assertEqual(second["rows"][0]["indirizzo"], "Piazza Due")
        self.assertEqual(second["rows"][0]["orario_testo"], "08:30–14:00")
        self.assertEqual(first["fonte_aggiornata_il"], second["fonte_aggiornata_il"])

    def test_reordering_city_blocks_does_not_change_identity(self):
        a, b = block(), block("Comune Beta", "ogni martedì", "Via Tre")
        self.assertEqual(projection(parse(a + b)["rows"]), projection(parse(b + a)["rows"]))

    def test_markup_wrappers_entities_and_break_variants_preserve_all_rows(self):
        for kind in ("weekly", "farmers"):
            with self.subTest(kind=kind):
                raw = fixture(kind).decode()
                variant = raw.replace("<strong>", "<b><span>").replace("</strong>", "</span></b>")
                variant = variant.replace("<br />", "<br>\n").replace("<p>", "<section>").replace("</p>", "</section>")
                variant = variant.replace("Quando:", "QUANDO&#58;").replace("Dove:", "DOVE :")
                original = parse_page(raw, source_url=URL, contract=source_contract(kind))
                changed = parse_page(variant, source_url=URL, contract=source_contract(kind))
                self.assertTrue(changed["complete"], changed["issues"])
                self.assertEqual(projection(original["rows"]), projection(changed["rows"]))

    def test_definition_lists_and_reordered_labels(self):
        body = ("<h2>Comune Alfa</h2><dl><dt>Dove</dt><dd>Piazza Uno</dd>"
                "<dt>Orario</dt><dd>8–13</dd><dt>Quando</dt><dd>ogni lunedì</dd></dl>")
        result = parse(body)
        self.assertTrue(result["complete"], result["issues"])
        self.assertEqual(result["rows"][0]["orario_testo"], "08:00–13:00")
        self.assertEqual(result["rows"][0]["indirizzo"], "Piazza Uno")

    def test_same_city_day_two_venues_are_not_a_unique_identity(self):
        body = block().replace("</p>", "<br><strong>Dove:</strong> Piazza Due</p>")
        result = parse(body)
        self.assertTrue(result["complete"])
        self.assertEqual(len(result["rows"]), 2)
        self.assertEqual(len({r["source_row_id"] for r in result["rows"]}), 1)
        self.assertTrue(all(not r["identity_unique"] and not r["comune_giorno_univoco"] for r in result["rows"]))
        self.assertEqual(result["metrics"]["ambiguous_source_identities"], 1)

    def test_fraction_same_day_vetoes_municipality_only_join(self):
        body = block(hours="8–13").replace(
            "</p>", "<br><strong>Frazioni:</strong> Borgo Nuovo il lunedì (Via Quattro)</p>")
        rows = parse(body)["rows"]
        self.assertEqual(len(rows), 2)
        self.assertTrue(all(r["identity_unique"] and not r["comune_giorno_univoco"] for r in rows))
        fraction = next(r for r in rows if r["localita"])
        self.assertEqual(fraction["citta"], "Comune Alfa")
        self.assertEqual(fraction["orario_testo"], "")
        self.assertEqual(fraction["orari"], [])

    def test_alternative_venues_are_preserved_without_creating_two_markets(self):
        rows = parse(block(where="Piazza Uno e/o Piazza Due"))["rows"]
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["sedi_alternative"], ["Piazza Uno", "Piazza Due"])
        self.assertFalse(rows[0]["comune_giorno_univoco"])
        self.assertIn("alternative_venues", rows[0]["issues"])

    def test_day_labels_in_venues_override_display_order(self):
        result = parse(block(when="giovedì e sabato", where="Piazza Due (sabato), Via Tre (giovedì)"))
        self.assertEqual({r["giorno"]: r["indirizzo"] for r in result["rows"]},
                         {"sabato": "Piazza Due", "giovedì": "Via Tre"})
        bad = parse(block(when="giovedì e sabato", where="Piazza Due (sabato)"))
        self.assertFalse(bad["complete"])
        self.assertEqual(bad["rows"], [])

    def test_morning_and_contact_numbers_never_become_clock_hours(self):
        body = block(when="ogni lunedì mattina", hours="mattina").replace(
            "</p>", "<br><strong>Info:</strong> 08-13</p>")
        row = parse(body)["rows"][0]
        self.assertEqual(row["fascia_giorno"], "mattina")
        self.assertEqual(row["orario_testo"], "")
        self.assertEqual(row["orari"], [])

    def test_qualifier_of_one_weekday_does_not_spread_to_other_weekdays(self):
        rows = parse(block(when="sabato; giovedì mattina", where="Piazza Uno"))["rows"]
        self.assertTrue(all(r["fascia_giorno"] == "" and r["orario_testo"] == "" for r in rows))
        self.assertTrue(all(r["quando_testo"] == "sabato; giovedì mattina" for r in rows))

    def test_invalid_or_office_hours_are_held_while_raw_venue_survives(self):
        for timing in ("25:00–26:00", "13:00–08:00", "ufficio dalle 8 alle 13", "8–13 su appuntamento"):
            with self.subTest(timing=timing):
                row = parse(block(hours=timing))["rows"][0]
                self.assertEqual(row["orario_testo"], "")
                self.assertIn("unparsed_or_invalid_hours", row["issues"])

    def test_header_navigation_scripts_and_other_sections_are_ignored(self):
        noise = block(where="Via Sbagliata", hours="1–2")
        raw = page(block(), before="<header>" + noise + "</header><nav>" + noise + "</nav>",
                   after=noise)
        raw = raw.replace('<div class="entry-content">', '<div class="entry-content"><nav>' + noise +
                          "</nav><script>" + noise + "</script>")
        result = parse_page(raw, source_url=URL, contract=contract())
        self.assertTrue(result["complete"], result["issues"])
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["rows"][0]["indirizzo"], "Piazza Uno")

    def test_unknown_municipality_never_inherits_previous_city(self):
        result = parse(block() + block("Comune Sconosciuto", "ogni martedì", "Via Estranea"))
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["rows"][0]["citta"], "Comune Alfa")
        self.assertIn("unknown_municipality_heading", {i["code"] for i in result["issues"]})

    def test_table_added_to_valid_blocks_cannot_silently_pass_cardinality(self):
        table = ("<table><thead><tr><th>Comune</th><th>Giorno</th><th>Sede</th>"
                 "<th>Orario di apertura</th></tr></thead><tbody><tr>"
                 "<td>Comune Beta</td><td>martedì</td><td>Piazza Due</td>"
                 "<td>08:00–13:00</td></tr></tbody></table>")
        result = parse(block() + table, min_rows=1, max_rows=10)
        self.assertFalse(result["complete"])
        self.assertEqual(len(result["rows"]), 1)
        self.assertIn("unsupported_table_layout", {i["code"] for i in result["issues"]})

    def test_nested_blocks_in_table_cells_do_not_hide_unsupported_table(self):
        table = ("<table><tr><td><section><p>Comune Beta</p>"
                 "<p>martedì — Piazza Due — 08:00–13:00</p>"
                 "</section></td></tr></table>")
        result = parse(block() + "<h2>Altri mercati</h2>" + table)
        self.assertFalse(result["complete"])
        self.assertIn("unsupported_table_layout", {i["code"] for i in result["issues"]})

    def test_tables_outside_selected_section_or_in_navigation_are_ignored(self):
        table = "<table><tr><td>Comune Beta</td><td>martedì — Piazza Due</td></tr></table>"
        body = (table + "<h2>Mercati settimanali</h2><nav>" + table + "</nav>"
                + block() + "<h2>Fiere</h2>" + table)
        raw = page(body, before=table, after=table)
        result = parse_page(raw, source_url=URL, contract=contract(
            start_heading="Mercati settimanali", end_heading="Fiere"))
        self.assertTrue(result["complete"], result["issues"])
        self.assertEqual(len(result["rows"]), 1)
        self.assertEqual(result["rows"][0]["indirizzo"], "Piazza Uno")

    def test_missing_value_does_not_consume_next_municipality_heading(self):
        result = parse(block(where="") + block("Comune Sconosciuto", "ogni martedì", "Via Estranea"))
        self.assertFalse(result["complete"])
        self.assertEqual(result["rows"], [])

    def test_homonymous_municipalities_require_an_unambiguous_heading(self):
        municipalities = [
            {"citta": "Comune Alfa", "provincia": "AA", "regione": "Regione Uno"},
            {"citta": "Comune Alfa", "provincia": "BB", "regione": "Regione Due"},
        ]
        result = parse(block(), municipalities=municipalities)
        self.assertFalse(result["complete"])
        self.assertEqual(result["rows"], [])
        resolved = parse(block("Comune Alfa (BB)"), municipalities=municipalities)
        self.assertTrue(resolved["complete"])
        self.assertEqual(resolved["rows"][0]["provincia"], "BB")

    def test_optional_numeric_istat_does_not_change_existing_identity(self):
        original = parse(block())["rows"][0]
        municipalities = copy.deepcopy(contract()["municipalities"])
        municipalities[0]["istat"] = "999001"
        with_code = parse(block(), municipalities=municipalities)["rows"][0]
        self.assertEqual(original["istat"], "")
        self.assertEqual(with_code["istat"], "999001")
        self.assertEqual(original["source_row_id"], with_code["source_row_id"])

    def test_kind_is_part_of_identity_and_is_never_guessed_from_food(self):
        ordinary = parse(block())["rows"][0]
        farmers = parse(block(), market_kind="farmers", category="contadino")["rows"][0]
        self.assertNotEqual(ordinary["source_row_id"], farmers["source_row_id"])
        self.assertEqual(farmers["market_kind"], "farmers")

    def test_qualified_recurrences_do_not_become_ordinary_weekly_rules(self):
        for when, cadence in (("sabato a settimane alterne", "fortnightly"),
                              ("ultimo lunedì del mese", "monthly_or_qualified"),
                              ("lunedì solo in estate", "seasonal_or_qualified"),
                              ("lunedì 19 ottobre 2026", "dated_or_qualified")):
            with self.subTest(when=when):
                self.assertEqual(parse(block(when=when))["rows"][0]["cadenza"], cadence)
        self.assertFalse(parse(block(when="dal lunedì al sabato"))["complete"])

    def test_source_date_is_explicit_and_never_replaced_by_reading_time(self):
        raw = page(block(), updated=None)
        result = parse_page(raw, source_url=URL, contract=contract())
        self.assertIsNone(result["fonte_aggiornata_il"])
        self.assertIsNone(result["rows"][0]["fonte_aggiornata_il"])
        conflicting = page(block(), metadata='<meta property="article:modified_time" content="2026-10-19">')
        result = parse_page(conflicting, source_url=URL, contract=contract())
        self.assertFalse(result["complete"])
        self.assertIsNone(result["fonte_aggiornata_il"])

    def test_missing_scope_delimiter_and_lost_blocks_fail_closed(self):
        result = parse_page(page(block()).replace('class="entry-content"', 'class="renamed"'),
                            source_url=URL, contract=contract())
        self.assertFalse(result["complete"])
        self.assertEqual(result["rows"], [])
        result = parse(block(), min_city_blocks=2)
        self.assertFalse(result["complete"])
        raw = fixture("weekly").decode().replace("FIERE DOMENICALI</strong>", "FIERE CAMBIATE</strong>")
        result = parse_page(raw, source_url=URL, contract=source_contract("weekly"))
        self.assertFalse(result["complete"])
        self.assertEqual(result["rows"], [])

    def test_unparsed_fraction_is_reported_not_silently_lost(self):
        result = parse(block().replace("</p>", "<br><strong>Frazioni:</strong> Borgo Nuovo ogni mese</p>"))
        self.assertFalse(result["complete"])
        self.assertIn("unparsed_fraction", {i["code"] for i in result["issues"]})

    def test_fraction_continuations_after_visual_breaks_are_not_lost(self):
        body = block().replace("</p>", "<br><strong>Frazioni:</strong> Borgo Uno il martedì (Via Due)"
                              "<br><strong>Borgo Due</strong> il mercoledì (Via Tre)</p>")
        result = parse(body)
        self.assertTrue(result["complete"], result["issues"])
        self.assertEqual({r["localita"] for r in result["rows"]}, {"", "Borgo Uno", "Borgo Due"})

    def test_new_unrecognized_hours_label_signals_layout_change(self):
        body = block(hours="8–13").replace("Orario:", "Apertura:")
        result = parse(body)
        self.assertFalse(result["complete"])
        self.assertIn("unparsed_market_line", {i["code"] for i in result["issues"]})


if __name__ == "__main__":
    unittest.main()
