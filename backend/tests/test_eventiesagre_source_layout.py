"""Synthetic versions of the observed Eventi e Sagre page structures.

No publisher HTML, network access, BeautifulSoup or HTTP client is required.
"""
import json
from pathlib import Path
import sys
import unittest
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eventiesagre_source_layout import MAX_BYTES, parse_eventiesagre_html


URL = "https://www.eventiesagre.it/Mercatini_Filiera+Corta/12345_Mercato+Di+Esempio.html"
TODAY = date(2026, 10, 20)


def html(*, body="", address="Via della Fonte, 4", hours="dalle ore 08:00 alle ore 13:00",
         start="02/11/2026", end="02/11/2026", archived=False,
         modified="2026-10-10 12:30:00", heading=True, jsonld=None,
         extra_card="", after="", event_id="12345", card_name="Mercato Di Esempio",
         heading_city="Esempio (BO)"):
    ld = '<script type="application/ld+json">' + jsonld + '</script>' if jsonld else ""
    source_dates = f'<div><span>Dal:</span> <span>{start}</span></div><div>Al: {end}</div>' if start or end else ""
    venue = f'<div class="recapito">{address}</div>' if address else ""
    marker = '<div id="eventopassato">Evento Passato!</div>' if archived else ""
    title = f'<h1>Mercato Di Esempio</h1><h3>Edizione - {hours}<br>{heading_city}</h3>' if heading else ""
    return f'''<!doctype html><html><head>{ld}</head><body>
      <aside><h1>Mercato Estraneo</h1><a>Altrove (RM)</a></aside>
      <div id="schedaEvento"><div class="SX">
       <div>Numero Evento: {event_id}</div>
       <div class="recapito grassetto titolo allignsx">{card_name}</div>
       {source_dates}<div class="recapito grassetto">Dove:</div>{venue}
       <div class="recapito titolo"><a href="https://www.eventiesagre.it/cerca/cat/sez/mesi/Emilia+Romagna/BO/Esempio/rilib">Esempio</a></div>
       <div>Emilia Romagna - Italia</div>{extra_card}
      </div><div class="DX"><div id="condividi">{marker}</div></div></div>
      <div id="contenuto">{title}<div>{body}</div>
       <hr><div id="correlati"><h3>Evento vicino</h3><a>Altrove (RM)</a>
       <p>Orario: dalle 14 alle 22. Dal: 25/12/2026</p><p>Via Falsa, 99</p></div>
       <div>Data ultimo aggiornamento pagina {modified}</div>{after}
      </div><footer><p><address>Via del Publisher, 8</address></p>
       <p>31/12/2030</p><a>Altrove (RM)</a></footer>
      </body></html>'''.encode()


def parse(**kwargs):
    return parse_eventiesagre_html(html(**kwargs), URL, today=TODAY)


class EventiESagreLayoutTests(unittest.TestCase):
    def test_primary_fields_are_scoped_and_date_kinds_stay_distinct(self):
        result = parse()
        self.assertEqual(result["legacy_fields"], {
            "nome": "Mercato Di Esempio", "citta": "Esempio", "provincia": "BO",
            "regione": "Emilia Romagna", "indirizzo": "Via della Fonte, 4",
            "orario_raw": "08:00–13:00", "ricorrenza_raw": "", "date_raw": ["2026-11-02"],
        })
        self.assertEqual(result["source_modified_on"], "2026-10-10")
        self.assertEqual(result["edition_intervals"], [{"start": "2026-11-02", "end": "2026-11-02"}])
        self.assertFalse(result["market_openings_verified"])
        self.assertEqual(result["network_requests"], 0)

    def test_footer_and_related_fields_never_fill_a_missing_venue(self):
        result = parse(address="", body="<p>Programma disponibile presso il Comune.</p>")
        self.assertEqual(result["legacy_fields"]["indirizzo"], "")
        self.assertEqual(result["legacy_fields"]["citta"], "Esempio")
        self.assertNotIn("Publisher", result["description_text"])
        self.assertNotIn("Altrove", result["description_text"])

    def test_body_is_not_limited_to_first_ten_paragraphs(self):
        result = parse(address="", hours="", body="<p>Nota</p>" * 12 +
                       "<p>Dove fanno il mercato settimanale: Via della Fonte, 4</p>"
                       "<p>Orari del Mercato: Dalle 08:00 alle 13:00</p>")
        self.assertEqual(result["legacy_fields"]["indirizzo"], "Via della Fonte, 4")
        self.assertEqual(result["legacy_fields"]["orario_raw"], "08:00–13:00")

    def test_split_inline_words_keep_labels_readable(self):
        result = parse(hours="", body="<p><strong>Orari del Mercat</strong>o: Dalle 08:00 alle 13:00</p>")
        self.assertEqual(result["legacy_fields"]["orario_raw"], "08:00–13:00")

    def test_market_information_heading_is_not_a_contacts_section(self):
        facts = ("<p><strong>Quando si svolge</strong>: Mercoledì tutto l'anno</p>"
                 "<p><strong>Orari del Mercat</strong>o: Dalle 08:00 alle 13:00</p>")
        result = parse(hours="", body="<p><strong>Informazioni sul Mercato:</strong></p>" + facts)
        self.assertEqual(result["legacy_fields"]["orario_raw"], "08:00–13:00")
        # A contacts heading still ends the facts.
        result = parse(hours="", body="<p><strong>Informazioni:</strong></p>" + facts)
        self.assertEqual(result["legacy_fields"]["orario_raw"], "")

    def test_labelled_numeric_hour_range_without_dalle_is_read(self):
        result = parse(hours="", body="<p>Orario: 08:00 - 13:00</p>")
        self.assertEqual(result["legacy_fields"]["orario_raw"], "08:00–13:00")

    def test_short_hours_and_decimal_variants_are_explicit(self):
        for value, expected in [("Dalle ore 8 alle 19", "08:00–19:00"),
                                ("dalle 8.30 alle ore 18.30", "08:30–18:30"),
                                ("dalle 8,30 alle 24", "08:30–24:00")]:
            with self.subTest(value=value):
                self.assertEqual(parse(hours=value)["legacy_fields"]["orario_raw"], expected)

    def test_start_only_does_not_invent_closing_time(self):
        self.assertEqual(parse(hours="dalle ore 10:00")["legacy_fields"]["orario_raw"], "Dalle 10:00")
        self.assertEqual(parse(hours="la mattina")["legacy_fields"]["orario_raw"], "")

    def test_activity_times_do_not_override_the_market_header(self):
        result = parse(body="<p>Laboratorio bambini 14.30-15.30; concerto dalle 18 alle 20.</p>")
        self.assertEqual(result["legacy_fields"]["orario_raw"], "08:00–13:00")

    def test_conflicting_explicit_hours_are_held(self):
        result = parse(body="<p>Orari del mercato: dalle 9 alle 19</p>")
        self.assertEqual(result["legacy_fields"]["orario_raw"], "")
        self.assertIn("visible_hours_conflict", result["issues"])

    def test_address_conflict_is_reported_without_choosing_a_version(self):
        result = parse(body="<p>Luogo: Viale Nuovo, 9</p>")
        self.assertEqual(result["legacy_fields"]["indirizzo"], "")
        self.assertIn("visible_address_conflict", result["issues"])

    def test_lowercase_location_prose_requires_the_card_municipality(self):
        result = parse(address="", body="<p>In via Mazzini ad Esempio una volta al mese.</p>")
        self.assertEqual(result["legacy_fields"]["indirizzo"], "via Mazzini")
        result = parse(address="", body="<p>In via Mazzini ad Altrove una volta al mese.</p>")
        self.assertEqual(result["legacy_fields"]["indirizzo"], "")

    def test_market_venue_prose_is_bounded_at_punctuation(self):
        result = parse(address="", body="<p>Arrivano i mercatini serali, allestiti in Piazza Nuova; un appuntamento estivo.</p>")
        self.assertEqual(result["legacy_fields"]["indirizzo"], "Piazza Nuova")

    def test_repeated_place_day_blocks_are_separate_and_duplicate_rows_collapse(self):
        one = "<p>Luogo: Via Prima</p><p>Giorni di svolgimento: Lunedì</p><p>Orario: Dalle ore 8.00 alle ore 14.00</p>"
        two = "<p>Luogo: Via Seconda</p><p>Giorni di svolgimento: Venerdì</p><p>Orario: Dalle ore 9 alle 13</p>"
        result = parse(address="", body=one + two + one)
        self.assertEqual(len(result["source_rows"]), 2)
        self.assertEqual(result["source_rows"][0], {"address": "Via Prima", "recurrence": "Lunedì", "hours": "08:00–14:00"})
        self.assertEqual(result["legacy_fields"]["indirizzo"], "")
        self.assertEqual(result["legacy_fields"]["ricorrenza_raw"], "")
        self.assertEqual(result["legacy_fields"]["orario_raw"], "")
        self.assertIn("multiple_market_rows_require_separate_identity", result["issues"])

    def test_monthly_exception_is_retained_whole_in_source_evidence(self):
        result = parse(body="<p>Ogni terza domenica del mese tranne agosto. Altre informazioni.</p>")
        self.assertEqual(result["recurrence_text"], "Ogni terza domenica del mese tranne agosto")
        self.assertTrue(result["scope_statements"])
        self.assertEqual(result["legacy_fields"]["ricorrenza_raw"], "")

    def test_labelled_weekday_is_kept_without_making_up_a_rule(self):
        result = parse(body="<p>Quando si svolge: Lunedì tutto l'anno</p>")
        self.assertEqual(result["recurrence_text"], "Lunedì tutto l'anno")
        self.assertEqual(result["legacy_fields"]["ricorrenza_raw"], "")

    def test_old_numeric_monthly_statement_survives_without_forecast(self):
        result = parse(heading=False, body="<p>2^ Domenica di ogni mese</p>",
                       start="01/02/2016", end="31/12/2016", archived=True)
        self.assertEqual(result["recurrence_text"], "2^ Domenica di ogni mese")
        self.assertEqual(result["legacy_fields"]["ricorrenza_raw"], "")

    def test_archived_record_keeps_identity_and_source_date_without_new_forecasts(self):
        result = parse(start="02/01/2023", end="02/01/2023", archived=True,
                       body="<p>Ogni lunedì</p>")
        self.assertTrue(result["archive_marker"])
        self.assertTrue(result["edition_is_past"])
        self.assertEqual(result["legacy_fields"]["nome"], "Mercato Di Esempio")
        self.assertEqual(result["legacy_fields"]["date_raw"], ["2023-01-02"])
        self.assertEqual(result["legacy_fields"]["ricorrenza_raw"], "")

    def test_interval_is_not_expanded_into_daily_openings_or_recurrence(self):
        result = parse(start="01/11/2026", end="30/11/2026", body="<p>Ogni lunedì</p>")
        self.assertEqual(result["edition_intervals"], [{"start": "2026-11-01", "end": "2026-11-30"}])
        self.assertEqual(result["legacy_fields"]["date_raw"], [])
        self.assertEqual(result["legacy_fields"]["ricorrenza_raw"], "")

    def test_invalid_and_reversed_dates_stay_unknown(self):
        for start, end in [("30/02/2026", "30/02/2026"), ("03/11/2026", "02/11/2026")]:
            result = parse(start=start, end=end)
            self.assertEqual(result["edition_intervals"], [])
            self.assertEqual(result["legacy_fields"]["date_raw"], [])
            self.assertIn("edition_dates_missing_or_invalid", result["issues"])

    def test_body_and_related_dates_do_not_become_edition_dates(self):
        result = parse(start="", end="", body="<p>Laboratorio del 25/12/2026.</p>")
        self.assertEqual(result["legacy_fields"]["date_raw"], [])

    def test_future_or_conflicting_editorial_timestamp_is_not_a_calendar_value(self):
        for modified, after in [("2030-01-01 00:00:00", ""),
                                ("2026-10-10 12:30:00", "<div>Data ultimo aggiornamento pagina 2026-10-11</div>")]:
            result = parse(modified=modified, after=after)
            self.assertEqual(result["source_modified_on"], "")
            self.assertEqual(result["legacy_fields"]["date_raw"], ["2026-11-02"])
            self.assertIn("publisher_date_conflict_or_future", result["issues"])

    def test_jsonld_midnight_times_never_supply_opening_hours(self):
        event = {"@type": "Event", "url": URL, "startDate": "2026-11-02T00:00:00+0100", "endDate": "2026-11-02T23:59:59+0100"}
        result = parse(hours="", jsonld=json.dumps(event))
        self.assertEqual(result["legacy_fields"]["orario_raw"], "")
        self.assertEqual(result["jsonld_events_matched"], 1)

    def test_invalid_jsonld_does_not_break_valid_visible_fields(self):
        result = parse(jsonld='{"@type":"Event","description":"invalid\nnewline"}')
        self.assertEqual(result["invalid_jsonld_blocks"], 1)
        self.assertEqual(result["legacy_fields"]["date_raw"], ["2026-11-02"])

    def test_jsonld_conflict_blocks_dates_and_foreign_event_is_ignored(self):
        event = {"@type": "Event", "url": URL, "startDate": "2027-11-02", "endDate": "2027-11-02"}
        result = parse(jsonld=json.dumps(event))
        self.assertEqual(result["legacy_fields"]["date_raw"], [])
        self.assertIn("jsonld_visible_edition_conflict", result["issues"])
        event["url"] = URL.replace("12345_", "99999_")
        result = parse(jsonld=json.dumps(event))
        self.assertEqual(result["jsonld_events_matched"], 0)
        self.assertEqual(result["legacy_fields"]["date_raw"], ["2026-11-02"])

    def test_past_marker_conflicts_with_future_edition(self):
        result = parse(archived=True)
        self.assertIn("archive_marker_date_conflict", result["issues"])
        self.assertEqual(result["legacy_fields"]["date_raw"], [])

    def test_card_only_older_layout_uses_its_own_title(self):
        result = parse(heading=False, hours="", body="<p>Programma del mercato.</p>")
        self.assertEqual(result["layout"], "eventiesagre_card_only_v1")
        self.assertEqual(result["legacy_fields"]["nome"], "Mercato Di Esempio")
        self.assertEqual(result["legacy_fields"]["orario_raw"], "")

    def test_card_and_article_identity_disagreement_is_rejected(self):
        for args in ({"event_id": "99999"}, {"card_name": "Un altro evento"}):
            with self.subTest(args=args), self.assertRaises(ValueError):
                parse(**args)

    def test_duplicate_or_missing_scopes_are_rejected(self):
        for blob in (html().replace(b'id="schedaEvento"', b'id="other"'),
                     html() + b'<div id="contenuto"><h1>Other</h1></div>'):
            with self.assertRaises(ValueError):
                parse_eventiesagre_html(blob, URL, today=TODAY)

    def test_scoped_municipality_conflicts_do_not_leak_into_fields(self):
        result = parse(heading_city="Altrove (RM)")
        self.assertEqual(result["legacy_fields"]["citta"], "")
        self.assertIn("card_heading_locality_conflict", result["issues"])
        extra = '<a href="https://www.eventiesagre.it/cerca/cat/sez/mesi/Lazio/RM/Altrove/rilib">Altrove</a>'
        result = parse(extra_card=extra)
        self.assertEqual(result["legacy_fields"]["citta"], "")
        self.assertIn("locality_missing_or_ambiguous", result["issues"])

    def test_all_observed_category_prefixes_share_the_bounded_detail_contract(self):
        categories = ["Mercatini_Filiera+Corta", "Mercatini_Vari", "Mercatini_Antiquariato",
                      "Mercatini_Artigianato", "Mercatini_Usato", "Mercatini_Enogastronomici",
                      "Mercatini_hobbisti+creativi", "Mercatini_Collezionismo", "Mercatini_Natale",
                      "Eventi_Enogastronomici", "Eventi_Feste", "Eventi_Mostra+Mercato",
                      "Eventi_Festival", "Eventi_Sagre", "Eventi_Folklore", "Eventi_Fiere"]
        for category in categories:
            url = URL.replace("Mercatini_Filiera+Corta", category)
            with self.subTest(category=category):
                self.assertEqual(parse_eventiesagre_html(html(), url, today=TODAY)["source_id"], "12345")

    def test_unreviewed_or_unbounded_inputs_are_rejected(self):
        for url in (URL.replace("https:", "http:"), URL + "?other=1", URL.replace("www.eventiesagre.it", "example.com")):
            with self.assertRaises(ValueError):
                parse_eventiesagre_html(html(), url, today=TODAY)
        with self.assertRaises(ValueError):
            parse_eventiesagre_html(b"x" * (MAX_BYTES + 1), URL, today=TODAY)


if __name__ == "__main__":
    unittest.main()
