"""Source-bound detail regressions; facts come from dated scoped HTML captures."""
import hashlib
import json
import sys
import unittest
from copy import deepcopy
from html import escape
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from happings_detail_layout import parse_detail, detail_url, MAX_BYTES

FIXTURES = Path(__file__).parent / "fixtures" / "happings_detail"
PISA = "https://www.happings.com/it/happing/mercato-coperto-campagna-amica-di-pisa/"
URL = "https://www.happings.com/it/happing/mercato-esempio/"


def fixture(name):
    manifest = json.loads((FIXTURES / "manifest.json").read_text())
    meta = next(x for x in manifest["samples"] if x["name"] == name)
    raw = (FIXTURES / meta["fixture_path"]).read_bytes()
    return raw, meta


def sample(*, schema=None, performances=None, description="", hours="07:30 - 12:30",
           address="Via Esempio 2, Pisa", date_label="24 Ottobre 2026", extra="",
           title="Mercato esempio", canonical=URL, summary="", sidebar_extra=""):
    if schema is None:
        schema = {"@type": "Event", "name": "Mercato esempio", "url": URL,
                  "startDate": "2026-10-24T07:30:00+02:00", "endDate": "2026-10-24T12:30:00+02:00",
                  "eventStatus": "https://schema.org/EventScheduled",
                  "location": {"@type": "Place", "name": "Piazza del mercato",
                               "address": {"@type": "PostalAddress", "streetAddress": "Via Esempio 2",
                                           "addressLocality": "Pisa", "addressRegion": "Toscana", "addressCountry": "IT"}}}
    if performances is None:
        performances = ["24 Ottobre 2026 · 07:30", "31 Ottobre 2026 · 07:30"]
    return (f'<link rel="canonical" href="{escape(canonical)}">'
            '<script type="application/ld+json" id="happings-event-schema">'
            + (schema if isinstance(schema, str) else json.dumps(schema, ensure_ascii=False)) + '</script>'
            '<div class="happings-event-hero"><div class="happings-event-category">Mercati</div>'
            f'<h1>{escape(title)}</h1></div><main class="happings-event-content">'
            f'<div class="happings-event-description-card"><p>{escape(description)}</p></div>'
            '<section class="happings-event-performances"><ul>'
            + ''.join('<li>' + escape(x) + '</li>' for x in performances) + '</ul></section>'
            '<section class="happings-event-auto-summary">' + summary + '</section>'
            + extra + '</main><aside class="happings-event-sidebar">'
            '<div class="happings-social-box" data-event-id="999"></div>'
            f'<div class="happings-event-info-item"><strong>Data</strong><p>{escape(date_label)}</p></div>'
            f'<div class="happings-event-info-item"><strong>Orario</strong><p>{escape(hours)}</p></div>'
            '<div class="happings-event-info-item"><strong>Dove si svolge</strong>'
            f'<p>Piazza del mercato</p><p>{escape(address)}</p></div>'
            + sidebar_extra + '</aside>')


def parsed(**kw):
    return parse_detail(sample(**kw), requested_url=URL)


class CapturedDetailTests(unittest.TestCase):
    def test_lucca_weekends_keep_boundaries_without_daily_or_overnight_hours(self):
        raw, meta = fixture("lucca_antiquario")
        result = parse_detail(raw, requested_url=meta["capture"]["requested_url"])
        event = result["event"]
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(result["warnings"], [])
        self.assertTrue(event["calendar_complete"])
        self.assertEqual([x["date"] for x in event["occurrences"]],
                         ["2026-10-17", "2026-10-18", "2026-11-14", "2026-11-15", "2026-12-19", "2026-12-20"])
        self.assertEqual(len(event["date_intervals"]), 3)
        self.assertTrue(all(x["continuous_opening_confirmed"] is False for x in event["date_intervals"]))
        self.assertEqual(event["hours_scope"], "interval_boundaries")
        self.assertEqual(event["hours_intervals"], [])
        self.assertIn("non attesta l’apertura notturna continuativa", event["hours_text"])
        self.assertEqual(len(event["source_links"]), 3)
        self.assertTrue(all(url.startswith("https://eventi.turismo.lucca.it/") for url in event["source_links"]))
        self.assertEqual(event["admission_text"], "L’ingresso è gratuito")
        for saturday, sunday in zip(event["occurrences"][::2], event["occurrences"][1::2]):
            self.assertEqual((saturday["start_time"], saturday["end_time"]), ("08:00", None))
            self.assertEqual((sunday["start_time"], sunday["end_time"]), (None, "20:00"))
            self.assertEqual(saturday["interval_end"], sunday["date"])

    def test_piemontese_schema_interval_crosses_month_without_daily_hours_claim(self):
        raw, meta = fixture("piemontese")
        result = parse_detail(raw, requested_url=meta["capture"]["requested_url"])
        event = result["event"]
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(result["warnings"], [])
        self.assertTrue(event["calendar_complete"])
        self.assertEqual(event["category"], "Shopping")
        self.assertEqual([x["date"] for x in event["occurrences"]], ["2026-10-31", "2026-11-01"])
        self.assertEqual(event["sidebar_hours_text"], "9:30 - 19:30")
        self.assertIn("31/10/2026 ore 09:30", event["hours_text"])
        self.assertIn("01/11/2026 ore 19:30", event["hours_text"])
        self.assertIn("non attestano gli orari giornalieri", event["hours_text"])
        self.assertEqual(event["hours_scope"], "interval_boundaries")

    def test_castelrotto_conditional_weather_clause_does_not_cancel_dates(self):
        raw, meta = fixture("castelrotto")
        result = parse_detail(raw, requested_url=meta["capture"]["requested_url"])
        event = result["event"]
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(event["category"], "Enogastronomia")
        self.assertTrue(event["calendar_complete"])
        self.assertEqual(len(event["occurrences"]), 4)
        self.assertTrue(all(x["status"] == "source_listed" for x in event["occurrences"]))
        self.assertIn("in caso di maltempo", event["conditions"][0])

    def test_parcines_conflicting_source_hours_and_workshop_are_kept_distinct(self):
        raw, meta = fixture("natale_parcines")
        result = parse_detail(raw, requested_url=meta["capture"]["requested_url"])
        event = result["event"]
        self.assertEqual(result["status"], "conflict")
        self.assertFalse(event["calendar_complete"])
        self.assertEqual(len(event["occurrences"]), 1)
        self.assertEqual((event["occurrences"][0]["start_time"], event["occurrences"][0]["end_time"]), ("10:00", "18:00"))
        self.assertEqual(event["hours_text"], "10:00 - 16:00")
        self.assertEqual(len(event["subevents"]), 1)
        self.assertEqual((event["subevents"][0]["start_time"], event["subevents"][0]["end_time"]), ("13:00", "16:00"))
        self.assertIn("laboratorio", event["subevents"][0]["text"])

    def test_concert_detail_title_and_category_do_not_certify_a_market(self):
        raw, meta = fixture("natale_concerto")
        result = parse_detail(raw, requested_url=meta["capture"]["requested_url"])
        event = result["event"]
        self.assertEqual(event["category"], "Natale")
        self.assertIn("Jingle Bells Rock", event["name"])
        self.assertIn("coro giovanile", event["description"])
        self.assertTrue(any(x["code"] == "description_schema_address_mismatch" for x in result["conflicts"]))
        self.assertIn({"kind": "telephone", "value": "+39 0473 561770"}, event["contacts"])
        self.assertIn({"kind": "website", "value": "http://www.lanaregion.it"}, event["contacts"])
        self.assertFalse(any(x["kind"] == "email" for x in event["contacts"]))
        self.assertIn("source_contact_email_obscured", result["warnings"])

    def test_fumetti_talk_keeps_its_program_category_and_context(self):
        raw, meta = fixture("notizia_fumetti")
        result = parse_detail(raw, requested_url=meta["capture"]["requested_url"])
        self.assertEqual(result["event"]["category"], "Arte e cultura")
        self.assertIn("Tipologia: Incontri", result["event"]["description"])
        self.assertEqual(len(result["event"]["occurrences"]), 1)

    def test_pisa_actual_layout_recovers_scoped_facts_and_ten_dates(self):
        raw, meta = fixture("pisa")
        self.assertEqual(hashlib.sha256(raw).hexdigest(), meta["fixture_sha256"])
        self.assertEqual(meta["capture"]["sha256"], "d07bc45c56cde4ee939aab5bb927496d1e18f0f17aa4cab01fe587cac2faafa0")
        result = parse_detail(raw, requested_url=PISA)
        event = result["event"]
        self.assertEqual(result["source"]["published_at"], "2026-09-30T19:14:55+00:00")
        self.assertEqual(result["status"], "parsed")
        self.assertEqual(event["source_id"], "14873")
        self.assertEqual(event["location"]["street_address"], "VIA del Chiassatello, 64/65")
        self.assertEqual(event["location"]["city"], "Pisa")
        self.assertEqual(event["location"]["region"], "Toscana")
        self.assertIsNone(event["location"]["province"])
        self.assertEqual(event["hours_text"], "7:30 - 12:30")
        self.assertEqual(len(event["occurrences"]), 10)
        self.assertEqual(event["occurrences"][0]["date"], "2026-10-24")
        self.assertEqual(event["occurrences"][-1]["date"], "2026-12-26")
        self.assertEqual(event["occurrences"][0]["end_time"], "12:30")
        self.assertTrue(all(x["end_time"] is None for x in event["occurrences"][1:]))
        self.assertTrue(event["calendar_complete"])
        self.assertEqual(event["calendar_scope"], "explicit_visible_list")
        self.assertEqual(event["contacts"], [])
        self.assertIsNone(event["organizer"])
        self.assertEqual(event["geo"]["precision"], "publisher_point_unverified")

    def test_lana_actual_prose_exception_keeps_december_24_thursday_and_1300(self):
        raw, meta = fixture("lana")
        event = parse_detail(raw, requested_url=meta["capture"]["requested_url"])["event"]
        self.assertEqual(len(event["occurrences"]), 10)
        last = event["occurrences"][-1]
        self.assertEqual((last["date"], last["start_time"], last["end_time"]), ("2026-12-24", "07:30", "13:00"))
        self.assertIn("fino al 18 dicembre", event["hours_text"])
        self.assertIn("24 dicembre termina alle 13:00", event["hours_text"])
        self.assertEqual(event["edition_interval"], {"start": "2026-10-02", "end": "2026-12-24"})
        self.assertEqual(event["organizer"]["name"], "Comune di Lana")
        self.assertEqual(event["organizer"]["url"], "https://www.happings.com/it/organizer/comune-di-lana/")
        self.assertTrue(event["calendar_complete"])

    def test_pescia_same_parser_nine_dates_with_correct_source_identity(self):
        raw, meta = fixture("pescia")
        result = parse_detail(raw, requested_url=meta["capture"]["requested_url"])
        event = result["event"]
        self.assertEqual(result["conflicts"], [])
        self.assertEqual(event["source_id"], "15328")
        self.assertEqual(event["location"]["city"], "Pescia")
        self.assertEqual(event["location"]["street_address"], "VIALE Giovanni XXIII, snc")
        self.assertEqual(len(event["occurrences"]), 9)
        self.assertEqual(event["occurrences"][-1]["date"], "2026-12-22")
        self.assertEqual(event["recurrence_text"], "martedì 08:30–12:30.")

    def test_fixture_captures_keep_hash_and_acquisition_separate(self):
        manifest = json.loads((FIXTURES / "manifest.json").read_text())
        for entry in manifest["samples"]:
            raw = (FIXTURES / entry["fixture_path"]).read_bytes()
            self.assertEqual(hashlib.sha256(raw).hexdigest(), entry["fixture_sha256"])
            self.assertRegex(entry["capture"]["captured_at"], r"^2026-10-20T")
            self.assertNotIn(b"nonce", raw)
            self.assertNotIn(b"<form", raw)
            result = parse_detail(raw, requested_url=entry["capture"]["requested_url"])
            metadata = entry.get("retained_editorial_metadata", [{}])[0]
            self.assertEqual(result["source"]["modified_at"], metadata.get("dateModified"))
            self.assertEqual(result["source"]["published_at"], metadata.get("datePublished"))
            self.assertNotEqual(result["source"]["html_sha256"], entry["capture"]["sha256"])


class DetailIdentityTests(unittest.TestCase):
    def test_reject_unreviewed_url_and_never_construct_slug(self):
        for url in (URL + "?q=1", URL + "#item", URL.replace("https", "http"),
                    URL.replace("www.happings.com", "www.happings.com.evil.test"),
                    URL.replace("www.happings.com", "user@www.happings.com"),
                    "https://www.happings.com/it/mercati-settimanali-a-pisa.html"):
            self.assertIsNone(detail_url(url))
            with self.assertRaises(ValueError):
                parse_detail(sample(), requested_url=url)

    def test_canonical_conflict_is_not_used_as_an_observed_redirect(self):
        result = parsed(canonical=PISA)
        self.assertEqual(result["source"]["final_url"], URL)
        self.assertEqual(result["source"]["canonical_url"], PISA)
        self.assertEqual(result["status"], "conflict")
        self.assertFalse(result["event"]["calendar_complete"])

    def test_schema_from_other_event_cannot_supply_location(self):
        text = sample().replace('"url": "' + URL + '"', '"url": "' + PISA + '"')
        result = parse_detail(text, requested_url=URL)
        self.assertEqual(result["status"], "conflict")
        self.assertIsNone(result["event"]["location"]["city"])
        self.assertTrue(any(x["code"] == "schema_url_mismatch" for x in result["conflicts"]))

    def test_html_codes_in_the_schema_title_are_not_a_contradiction(self):
        # Real pages: JSON-LD "Mercato &#8211; Natale" while the visible title shows "–".
        schema = {"@type": "Event", "name": "Mercato esempio &#8211; Natale &amp; dintorni", "url": URL,
                  "startDate": "2026-10-24T07:30:00+02:00", "endDate": "2026-10-24T12:30:00+02:00",
                  "eventStatus": "https://schema.org/EventScheduled",
                  "location": {"@type": "Place", "name": "Piazza del mercato",
                               "address": {"@type": "PostalAddress", "streetAddress": "Via Esempio 2",
                                           "addressLocality": "Pisa", "addressRegion": "Toscana",
                                           "addressCountry": "IT"}}}
        result = parsed(schema=schema, title="Mercato esempio – Natale & dintorni")
        self.assertFalse(any(x["code"] == "schema_title_mismatch" for x in result["conflicts"]))

    def test_title_contradiction_and_multiple_event_schemas_are_explicit(self):
        result = parsed(title="Mercato diverso")
        self.assertTrue(any(x["code"] == "schema_title_mismatch" for x in result["conflicts"]))
        html = sample()
        schema = html[html.index('<script'):html.index('</script>') + len('</script>')]
        result = parse_detail(html + schema, requested_url=URL)
        self.assertTrue(any(x["code"] == "multiple_event_schemas" for x in result["conflicts"]))

    def test_two_heroes_or_missing_content_is_layout_change(self):
        html = sample() + '<div class="happings-event-hero"><h1>Altro evento</h1></div>'
        self.assertEqual(parse_detail(html, requested_url=URL)["status"], "layout_changed")
        self.assertEqual(parse_detail('<h1>Mercato esempio</h1>', requested_url=URL)["status"], "layout_changed")

    def test_footer_navigation_related_cards_never_supply_event_fields(self):
        poison = '<div class="happings-related-events"><div class="happings-event-performances"><li>1 Gennaio 2099 · 23:00</li></div><div class="happings-event-description-card">Sabato dalle 22:00 alle 23:00</div></div>'
        html = sample(extra=poison) + '<footer><div class="happings-event-info-item"><strong>Telefono</strong><p><a href="tel:+390123456">0123456</a></p></div>Via Compagni 25</footer>'
        result = parse_detail(html, requested_url=URL)
        self.assertEqual(len(result["event"]["occurrences"]), 2)
        self.assertEqual(result["event"]["contacts"], [])
        self.assertIsNone(result["event"]["recurrence_text"])
        self.assertEqual(result["event"]["location"]["street_address"], "Via Esempio 2")

    def test_scoped_contacts_are_read_without_publisher_footer(self):
        sidebar = '<div class="happings-event-info-item"><strong>Contatti</strong><p><a href="mailto:organizzatore@example.org">Email</a><a href="tel:+3905012345">Telefono</a></p></div>'
        event = parsed(sidebar_extra=sidebar)["event"]
        self.assertEqual(event["contacts"], [{"kind": "email", "value": "organizzatore@example.org"}, {"kind": "telephone", "value": "+3905012345"}])

    def test_visible_address_and_summary_conflicts_are_not_erased(self):
        result = parsed(address="Via Altra 9, Pisa", summary='<p>L’indirizzo indicato è Via Terza 3.</p>')
        self.assertEqual(result["status"], "conflict")
        self.assertEqual({x["code"] for x in result["conflicts"]}, {"visible_schema_address_mismatch", "summary_schema_address_mismatch"})

    def test_invalid_json_does_not_borrow_organization_contacts(self):
        result = parsed(schema='{"@type":"Event",notvalid}')
        self.assertIn("invalid_json_ld", result["warnings"])
        self.assertIsNone(result["event"]["location"]["city"])
        self.assertEqual(result["event"]["contacts"], [])


class DetailCalendarTests(unittest.TestCase):
    def test_old_edition_year_stays_old(self):
        text = sample(summary='<p>Il periodo indicato va dal 1 Ottobre 2026 al 31 Ottobre 2026.</p>').replace("2026", "2025")
        event = parse_detail(text, requested_url=URL)["event"]
        self.assertEqual([x["date"] for x in event["occurrences"]], ["2025-10-24", "2025-10-31"])
        self.assertEqual(event["edition_interval"]["end"], "2025-10-31")

    def test_missing_year_or_invalid_date_is_not_filled_from_current_year(self):
        for line in ("31 Ottobre · 07:30", "31 Novembre 2026 · 07:30"):
            result = parsed(performances=["24 Ottobre 2026 · 07:30", line])
            self.assertFalse(result["event"]["calendar_complete"])
            self.assertEqual(len(result["event"]["occurrences"]), 1)
            self.assertIn(line, result["event"]["calendar_notes"])

    def test_date_range_is_not_expanded_into_daily_openings(self):
        result = parsed(performances=["24 Ottobre 2026 · 07:30", "Dal 1 Novembre 2026 al 3 Novembre 2026"])
        self.assertEqual(len(result["event"]["occurrences"]), 1)
        self.assertFalse(result["event"]["calendar_complete"])

    def test_different_sessions_on_same_date_remain_distinct(self):
        result = parsed(performances=["24 Ottobre 2026 · 07:30 - 12:30", "24 Ottobre 2026 · 15:30 - 18:30"])
        self.assertEqual(result["status"], "parsed")
        self.assertEqual([(x["start_time"], x["end_time"]) for x in result["event"]["occurrences"]], [("07:30", "12:30"), ("15:30", "18:30")])

    def test_schema_and_visible_times_disagreement_is_held(self):
        for line, code in (("24 Ottobre 2026 · 08:00", "schema_performance_start_mismatch"),
                           ("24 Ottobre 2026 · 07:30 - 13:00", "schema_performance_end_mismatch")):
            result = parsed(performances=[line])
            self.assertTrue(any(x["code"] == code for x in result["conflicts"]))
            self.assertFalse(result["event"]["calendar_complete"])

    def test_weekday_disagreement_and_edition_overflow_are_held(self):
        result = parsed(performances=["lunedì 24 Ottobre 2026 · 07:30"], summary='<p>Il periodo indicato va dal 1 Ottobre 2026 al 20 Ottobre 2026.</p>')
        self.assertEqual({x["code"] for x in result["conflicts"]}, {"weekday_date_mismatch", "occurrence_outside_edition"})

    def test_schema_next_date_must_match_visible_list_and_sidebar(self):
        result = parsed(performances=["31 Ottobre 2026 · 07:30"], date_label="31 Ottobre 2026")
        self.assertEqual({x["code"] for x in result["conflicts"]}, {"schema_date_absent_from_performances", "sidebar_schema_date_mismatch"})

    def test_midnight_placeholders_do_not_invent_exact_opening_hours(self):
        html = sample(performances=["24 Ottobre 2026"], hours="Giornata intera")
        html = html.replace("T07:30:00", "T00:00:00").replace("T12:30:00", "T23:59:00")
        event = parse_detail(html, requested_url=URL)["event"]
        self.assertTrue(event["all_day"])
        self.assertIsNone(event["occurrences"][0]["start_time"])
        self.assertIsNone(event["occurrences"][0]["end_time"])

    def test_explicit_midnight_is_not_discarded(self):
        html = sample(performances=["24 Ottobre 2026 · 00:00 - 02:00"], hours="00:00 - 02:00")
        html = html.replace("T07:30:00", "T00:00:00").replace("T12:30:00", "T02:00:00")
        event = parse_detail(html, requested_url=URL)["event"]
        self.assertEqual(event["occurrences"][0]["start_time"], "00:00")

    def test_performance_cancellation_is_retained(self):
        event = parsed(performances=["24 Ottobre 2026 · 07:30", "31 Ottobre 2026 · 07:30 annullato"])["event"]
        self.assertEqual(event["occurrences"][1]["status"], "cancelled")
        self.assertEqual(event["occurrences"][0]["status"], "source_listed")

    def test_unscoped_cancellation_description_blocks_calendar_application(self):
        event = parsed(description="Il mercato è sospeso fino a nuova comunicazione.")["event"]
        self.assertFalse(event["calendar_complete"])
        self.assertIn("sospeso", event["calendar_notes"][0])

    def test_prose_day_month_joins_only_unique_explicit_date(self):
        result = parsed(performances=["24 Ottobre 2026 · 07:30", "31 Ottobre 2026 · 07:30", "31 Ottobre 2027 · 07:30"],
                        description="L’appuntamento del 31 ottobre termina alle 13:00.")
        event = result["event"]
        self.assertFalse(event["calendar_complete"])
        self.assertTrue(all(x["end_time"] is None for x in event["occurrences"][1:]))
        self.assertIn("date_specific_hours_without_unique_explicit_date", result["warnings"])

    def test_prose_exception_conflicting_with_list_is_held(self):
        result = parsed(performances=["24 Ottobre 2026 · 07:30", "31 Ottobre 2026 · 07:30 - 12:30"],
                        description="Il 31 ottobre termina alle 13:00.")
        self.assertTrue(any(x["code"] == "prose_performance_end_mismatch" for x in result["conflicts"]))

    def test_multi_weekday_hours_keep_all_conditions(self):
        event = parsed(description="Le aperture settimanali riportate dalla fonte sono: martedì 07:30–12:30, sabato 15:00–18:00.")["event"]
        self.assertIn("martedì 07:30–12:30, sabato 15:00–18:00", event["hours_text"])
        self.assertIn({"start": "15:00", "end": "18:00"}, event["hours_intervals"])

    def test_editorial_timestamp_stays_separate_from_event_date(self):
        html = '<meta property="article:modified_time" content="2026-10-20T12:00:00+02:00">' + sample()
        result = parse_detail(html, requested_url=URL)
        self.assertEqual(result["source"]["modified_at"], "2026-10-20T12:00:00+02:00")
        self.assertEqual(result["event"]["occurrences"][0]["date"], "2026-10-24")

    def test_multi_day_schema_cancellation_applies_to_its_whole_interval(self):
        html = sample(performances=[], date_label="24 Ottobre 2026 - 25 Ottobre 2026")
        html = html.replace('2026-10-24T12:30:00', '2026-10-25T12:30:00').replace('EventScheduled', 'EventCancelled')
        event = parse_detail(html, requested_url=URL)["event"]
        self.assertEqual(len(event["occurrences"]), 2)
        self.assertTrue(all(x["status"] == "cancelled" for x in event["occurrences"]))

    def test_explicit_weekend_range_requires_a_source_year(self):
        result = parsed(description="Le edizioni sono 14–15 novembre e 19–20 dicembre.")
        self.assertEqual(result["event"]["date_intervals"], [])
        self.assertIn("unyearred_edition_range", result["warnings"])
        self.assertFalse(result["event"]["calendar_complete"])

    def test_long_multi_day_interval_is_not_expanded_as_months_of_openings(self):
        html = sample(performances=[], date_label="24 Ottobre 2026 - 31 Dicembre 2026")
        html = html.replace('2026-10-24T12:30:00', '2026-12-31T12:30:00')
        result = parse_detail(html, requested_url=URL)
        self.assertFalse(result["event"]["calendar_complete"])
        self.assertIn("long_schema_interval_not_enumerated", result["warnings"])
        self.assertEqual(result["event"]["occurrences"], [])

    def test_sidebar_multi_day_interval_disagreement_is_not_ignored(self):
        html = sample(performances=[], date_label="24 Ottobre 2026 - 26 Ottobre 2026")
        html = html.replace('2026-10-24T12:30:00', '2026-10-25T12:30:00')
        result = parse_detail(html, requested_url=URL)
        self.assertTrue(any(x["code"] == "sidebar_schema_interval_mismatch" for x in result["conflicts"]))

    def test_response_size_bound(self):
        with self.assertRaises(ValueError):
            parse_detail(b"x" * (MAX_BYTES + 1), requested_url=URL)


if __name__ == "__main__":
    unittest.main()
