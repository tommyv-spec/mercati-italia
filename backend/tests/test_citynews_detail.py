"""Observed Citynews DOM semantics and identity-bound editorial roundtrip.

The fixture manifest distinguishes factual excerpts from raw HTTP hashes.
Future examples below are deliberately synthetic; none claims a live event.
"""
from copy import deepcopy
from datetime import date, timedelta
from html import escape
import hashlib
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from citynews_layout import MAX_BYTES, parse_detail
from citynews_urls import source_identity
from citynews_detail_enrichment import (
    catalog_urls, parse_document, preview, verify_changes, verify_exported,
    verify_source_pages,
)
from editorial_calendar_scope import (
    KEY, apply_editorial_scope, clean_editorial_evidence, retain_editorial_evidence,
    valid_editorial_reported_dates,
)
from export_static import normalize
from field_evidence import field_states, fingerprint, make_receipt
from recurrence_refresh import refresh_record

TODAY = date(2026, 10, 20)
URL = "https://www.bolognatoday.it/eventi/mercato-edizione-test-2026.html"
NAME = "Mercato delle curiosità di Bologna 2026"
FIXTURES = Path(__file__).parent / "fixtures/citynews_detail"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())


def html(*, title=NAME, city="Bologna", street="Via della Fonte, 4", hours="Dalle 9 alle 18",
         start="2026-11-01", end="2026-11-01", canonical=URL, schema_url=URL,
         schema_name=None, schema_start=None, schema_end=None, schema_status=None,
         body="", tail="", extra_head="", publication="19 ottobre 2026 15:30"):
    def italian(value):
        y, m, d = value.split("-"); return d + "/" + m + "/" + y
    schema = {"@type": "Event", "name": schema_name or title, "url": schema_url,
              "startDate": schema_start or start, "location": {"@type": "Place", "name": "Sede Test",
                  "address": (street or "") + ", " + city + ", "}}
    if schema_end is not None: schema["endDate"] = schema_end
    if schema_status is not None: schema["eventStatus"] = "https://schema.org/" + schema_status
    return ("<!doctype html><html><head><link rel=\"canonical\" href=\"" + escape(canonical, quote=True) + "\">"
        "<script type=\"application/ld+json\">" + json.dumps([schema], ensure_ascii=False) + "</script>" + extra_head +
        "</head><body><article class=\"l-entry\"><header class=\"l-entry__header\">"
        "<h1 class=\"l-entry__title\">" + escape(title) + "</h1><div class=\"l-grid l-grid--square\">"
        "<div class=\"l-grid__item\"><span class=\"u-label-03\">Dove</span>"
        "<a href=\"/eventi/location/sede-test/\">Sede Test</a><p><a href=\"#map\">" +
        escape(street or "Indirizzo non disponibile") + "</a></p></div>"
        "<div class=\"l-grid__item\"><span class=\"u-label-03\">Quando</span><span>Dal " + italian(start) +
        " al " + italian(end) + "</span><span class=\"u-label-011\">" + escape(hours) + "</span></div></div></header>"
        "<section class=\"l-entry__byline--small\"><time>" + publication + "</time></section>"
        "<section class=\"l-entry__body\">" + body + "</section></article>" + tail + "</body></html>").encode()


def row(**changes):
    result = {"slug": "preserved-citynews-id", "nome": NAME, "citta": "Bologna", "provincia": "BO",
        "regione": "Emilia-Romagna", "indirizzo": "", "orario_testo": "",
        "ricorrenza_testo": "settimanale - domenica", "ricorrenza": "settimanale",
        "url_fonte": URL, "fonte": "bolognatoday.it", "date": ["2026-10-25", "2026-11-01", "2026-11-08"],
        "date_quality": "prevista", "proiezione_regola": {"kind": "weekly", "weekdays": [6]},
        "proiezione_generata_il": "2026-10-19", "proiezione_fonte": "ricorrenza_testo",
        "categoria": "misto", "status": "non_confermato", "fonti": [], "verificato_il": "",
        "lat": None, "lng": None, "position_quality": "sconosciuta", "confidence": 65,
        "fonte_aggiornata_il": "2026-10-10"}
    result.update(changes)
    return result


def observed(blob=None, *, today=TODAY, url=URL, final_url=None):
    return {"read_on": today.isoformat(), "parsed": parse_document(
        blob or html(), requested_url=url, final_url=final_url, today=today)}


class RealLayoutTests(unittest.TestCase):
    def fixture(self, host):
        item = next(v for v in MANIFEST["results"] if v["fixture"].startswith(host + "--"))
        return parse_detail((FIXTURES / item["fixture"]).read_bytes(),
                            requested_url=item["requested_url"], final_url=item["final_url"])

    def test_all_27_captured_semantic_excerpts_retain_the_reviewed_facts(self):
        self.assertEqual(len(MANIFEST["results"]), 27)
        for item in MANIFEST["results"]:
            with self.subTest(item=item["fixture"]):
                blob = (FIXTURES / item["fixture"]).read_bytes()
                self.assertEqual(hashlib.sha256(blob).hexdigest(), item["fixture_sha256"])
                self.assertNotEqual(item["fixture_sha256"], item["raw_sha256"])
                parsed = parse_detail(blob, requested_url=item["requested_url"], final_url=item["final_url"])
                self.assertEqual(parsed["event"], item["expected_event"])
                self.assertEqual(parsed["conflicts"], item["expected_conflicts"])
                self.assertEqual(parsed["warnings"], item["expected_warnings"])
                self.assertEqual(parsed["status"], item["status"])

    def test_real_simple_partial_and_qualified_hours_keep_their_scope(self):
        catania = self.fixture("cataniatoday.it")["event"]
        self.assertEqual(catania["occurrences"][0]["start_time"], "08:30")
        self.assertIsNone(catania["occurrences"][0]["end_time"])
        cesena = self.fixture("cesenatoday.it")["event"]
        self.assertEqual(cesena["hours_intervals"][0]["start"], "09:00")
        self.assertIsNone(cesena["hours_intervals"][0]["end"])
        monza = self.fixture("monzatoday.it")["event"]
        self.assertEqual(monza["hours_intervals"], [])
        self.assertIn("Venerdì dalle 12 alle 20", monza["hours_text"])
        self.assertIn("sabato e domenica dalle 9 alle 20", monza["hours_text"])
        arezzo = self.fixture("arezzonotizie.it")["event"]
        self.assertEqual(arezzo["hours_text"], "dalle 15 del 21 febbraio")
        self.assertEqual(arezzo["hours_intervals"], [])

    def test_real_ranges_are_edition_bounds_not_daily_openings(self):
        forli = self.fixture("forlitoday.it")["event"]
        self.assertEqual(forli["edition_intervals"], [{"start": "2026-02-06", "end": "2026-02-27"}])
        self.assertEqual(forli["occurrences"], [])
        self.assertIsNone(forli["forecast_rule"])
        rimini = self.fixture("riminitoday.it")["event"]
        self.assertEqual(rimini["edition_intervals"][0]["end"], "2026-06-14")
        self.assertEqual(rimini["occurrences"], [])

    def test_real_street_commas_do_not_become_municipalities(self):
        event = self.fixture("arezzonotizie.it")["event"]
        self.assertEqual(event["location"]["address"], "Via Lazzaro Spallanzani, 23")
        self.assertEqual(event["location"]["city"], "Arezzo")
        self.assertIsNone(self.fixture("bresciatoday.it")["event"]["location"]["city"])

    def test_real_external_organizer_url_is_not_the_page_identity(self):
        bologna = self.fixture("bolognatoday.it")
        self.assertEqual(bologna["status"], "parsed")
        self.assertIn("schema_event_url_is_external_not_page_identity", bologna["warnings"])
        self.assertEqual(bologna["source"]["requested_url"], bologna["source"]["canonical_url"])

    def test_real_editorial_variant_and_changed_edition_redirect_are_held(self):
        lecco = self.fixture("leccotoday.it")
        self.assertEqual(lecco["status"], "unsupported")
        self.assertIsNone(lecco["event"]["location"]["address"])
        viterbo = self.fixture("viterbotoday.it")
        self.assertFalse(viterbo["event"]["calendar_complete"])
        self.assertIn({"field": "identity", "code": "redirect_changes_exact_event_identity"}, viterbo["conflicts"])
        self.assertEqual(viterbo["event"]["edition_intervals"][0]["start"], "2026-02-22")

    def test_year_comes_from_visible_event_not_typo_in_url(self):
        modena = self.fixture("modenatoday.it")
        self.assertIn("3026", modena["source"]["requested_url"])
        self.assertEqual(modena["event"]["occurrences"][0]["date"], "2026-02-15")


class StructuralBoundaryTests(unittest.TestCase):
    def test_footer_programme_and_related_event_do_not_fill_fields(self):
        source = html(street="", hours="Orario non disponibile", body="<p>Programma alle 23:00. Via Altra 99.</p>",
            tail='<footer><a href="#map">Via Footer 8</a><span class="u-label-011">7-24</span>'
                 '<script type="application/ld+json">{"@type":"Event","name":"Altro"}</script></footer>')
        parsed = parse_detail(source, requested_url=URL)
        self.assertEqual(parsed["status"], "parsed")
        self.assertIsNone(parsed["event"]["location"]["address"])
        self.assertIsNone(parsed["event"]["hours_text"])

    def test_very_long_programme_does_not_break_the_primary_event_card(self):
        parsed = parse_detail(html(body="<p>" + "descrizione " * 1500 + "</p>"), requested_url=URL)
        self.assertEqual(parsed["status"], "parsed")

    def test_unresolved_cancellation_prose_holds_calendar_without_guessing_scope(self):
        parsed = parse_detail(html(body="<p>Il programma è rinviato per maltempo.</p>"), requested_url=URL)
        self.assertFalse(parsed["event"]["calendar_complete"])
        self.assertEqual(parsed["event"]["occurrences"], [])
        self.assertEqual(parsed["event"]["scope_statements"], ["rinviato"])

    def test_schema_visible_disagreements_never_silently_choose_a_value(self):
        for changes, field in (({"schema_name": "Altro evento"}, "identity"),
                               ({"schema_start": "2026-11-02"}, "calendar"),
                               ({"schema_end": "2026-11-03"}, "calendar"),
                               ({"canonical": URL.replace("test", "altro")}, "identity")):
            with self.subTest(changes=changes):
                parsed = parse_detail(html(**changes), requested_url=URL)
                self.assertTrue(any(c["field"] == field for c in parsed["conflicts"]))
                self.assertFalse(parsed["event"]["calendar_complete"])

    def test_multiple_primary_events_and_malformed_schema_are_held(self):
        for script in ('<script type="application/ld+json">{"@type":"Event","name":"Altro"}</script>',
                       '<script type="application/ld+json">{BROKEN}</script>'):
            parsed = parse_detail(html(extra_head=script), requested_url=URL)
            self.assertEqual(parsed["status"], "held")
            self.assertFalse(parsed["event"]["calendar_complete"])

    def test_precise_cancelled_single_date_is_not_a_future_opening(self):
        parsed = parse_detail(html(schema_status="EventCancelled"), requested_url=URL)
        self.assertEqual(parsed["event"]["occurrences"][0]["status"], "cancelled")

    def test_same_or_reversed_clock_endpoints_do_not_claim_opening_windows(self):
        for value in ("Dalle 9 alle 9", "18-9", "9:99-18"):
            parsed = parse_detail(html(hours=value), requested_url=URL)
            self.assertEqual(parsed["event"]["hours_intervals"], [])
            self.assertTrue(any(c["field"] == "hours" for c in parsed["conflicts"]))
            self.assertEqual(parsed["event"]["hours_text"], value)

    def test_explicit_title_year_cannot_be_rebound_to_another_edition(self):
        parsed = parse_detail(html(start="2027-11-01", end="2027-11-01"), requested_url=URL)
        self.assertIn({"field": "calendar", "code": "title_edition_year_disagrees"}, parsed["conflicts"])
        self.assertFalse(parsed["event"]["calendar_complete"])
        self.assertEqual(parsed["event"]["occurrences"], [])

    def test_publication_is_not_modified_time_or_read_date(self):
        parsed = parse_detail(html(), requested_url=URL)
        self.assertEqual(parsed["source"]["published_at"], "2026-10-19")
        self.assertIsNone(parsed["source"]["modified_at"])
        self.assertNotIn("read_on", parsed["source"])

    def test_only_reviewed_exact_detail_urls_and_bounded_html_are_accepted(self):
        for bad in (URL.replace("https:", "http:"), URL + "?edition=2", URL + "#map",
                    "https://www.evil.today.it/eventi/a.html", "https://www.romatoday.it/eventi/",
                    "https://www.romatoday.it/eventi/location/a.html", "https://www.romatoday.it/news/a.html",
                    "https://www.romatoday.it:443/eventi/a.html"):
            self.assertIsNone(source_identity(bad), bad)
        with self.assertRaises(ValueError): parse_detail(b"x" * (MAX_BYTES + 1), requested_url=URL)


class BindingAndRoundtripTests(unittest.TestCase):
    def test_exact_future_edition_fills_fields_but_never_claims_source_freshness(self):
        before = row(); result, report = preview([before], [observed()], today=TODAY)
        actual = result[0]
        self.assertEqual(actual["indirizzo"], "Via della Fonte, 4")
        self.assertEqual(actual["orario_testo"], "Dalle 9 alle 18")
        self.assertEqual(actual["date"], ["2026-11-01"])
        self.assertEqual(actual["date_quality"], "riportata")
        self.assertEqual(actual["fonte_aggiornata_il"], before["fonte_aggiornata_il"])
        self.assertEqual(actual[KEY]["published_on"], "2026-10-19")
        self.assertEqual(actual[KEY]["modified_on"], "")
        self.assertEqual(actual[KEY]["read_on"], "2026-10-20")
        self.assertEqual(field_states(actual, today=TODAY)["orario_testo"], "riscontrato_data_fonte_sconosciuta")
        self.assertTrue(valid_editorial_reported_dates(actual, today=TODAY))
        self.assertEqual(report["new_market_ids"], [])
        self.assertTrue(verify_exported(result, report, today=TODAY)["release_safe"])
        self.assertEqual(before, row())

    def test_primary_url_title_and_city_must_all_match(self):
        for changes in ({"nome": NAME + " altro evento"}, {"citta": "Modena"},
                        {"provincia": "MO"}, {"regione": "Lombardia"}, {"citta": "Sede Test"}):
            before = row(**changes)
            result, report = preview([before], [observed()], today=TODAY)
            self.assertEqual(result, [before])
            self.assertEqual(report["outcomes"][0]["status"], "held")
        with self.assertRaises(ValueError):
            preview([row(url_fonte=URL + "/")], [observed()], today=TODAY)

    def test_missing_or_namesake_source_city_does_not_use_publisher_city(self):
        for city in ("", "Castro", "Sede Test"):
            result, report = preview([row()], [observed(html(city=city))], today=TODAY)
            self.assertEqual(result, [row()])
            self.assertEqual(report["outcomes"][0]["reason"], "source_identity_conflict")

    def test_explicit_foreign_country_cannot_be_normalized_into_italy(self):
        body = html().decode()
        source_address = json.dumps({"@type": "PostalAddress", "addressLocality": "Bologna",
            "addressRegion": "BO", "addressCountry": "FR", "streetAddress": "Via della Fonte, 4"})
        body = body.replace('"Via della Fonte, 4, Bologna, "', source_address).encode()
        original = row(); result, report = preview([original], [observed(body)], today=TODAY)
        self.assertEqual(result, [original])
        self.assertEqual(report["outcomes"][0]["reason"], "source_identity_conflict")

    def test_accessory_programme_hours_and_title_year_conflicts_are_not_promoted(self):
        result, _ = preview([row()], [observed(html(hours="Concerto dalle 21 alle 23"))], today=TODAY)
        self.assertEqual(result[0]["orario_testo"], "")
        self.assertEqual(result[0][KEY]["facts"]["hours_text"], "Concerto dalle 21 alle 23")
        result, _ = preview([row()], [observed(html(start="2027-11-01", end="2027-11-01"))], today=TODAY)
        self.assertEqual(result[0]["date"], [])
        self.assertEqual(result[0]["orario_testo"], "")

    def test_blank_province_can_retain_exact_specific_identity_without_filling_geography(self):
        before = row(provincia="")
        result, _ = preview([before], [observed()], today=TODAY)
        self.assertEqual(result[0]["provincia"], "")
        self.assertEqual(result[0][KEY]["facts"]["location"]["province"], "BO")

    def test_duplicate_exact_candidates_remain_held(self):
        before = [row(), row(slug="other-existing-id")]
        result, report = preview(before, [observed()], today=TODAY)
        self.assertEqual(result, before)
        self.assertEqual({v["reason"] for v in report["outcomes"]}, {"multiple_exact_catalog_candidates"})

    def test_wrong_municipality_duplicate_does_not_block_one_proven_existing_identity(self):
        before = [row(), row(slug="bad-old-city", citta="Sede Test")]
        result, report = preview(before, [observed()], today=TODAY)
        self.assertIn(KEY, result[0]); self.assertEqual(result[1], before[1])
        self.assertEqual(report["changed_existing_ids"], [before[0]["slug"]])

    def test_old_edition_keeps_facts_without_recertifying_hours_or_rolling_dates(self):
        result, report = preview([row()], [observed(html(start="2021-11-01", end="2021-11-01"))], today=TODAY)
        actual = result[0]
        self.assertEqual(actual["indirizzo"], "")
        self.assertEqual(actual["orario_testo"], "")
        self.assertEqual(actual["date"], [])
        self.assertEqual(actual["date_quality"], "sconosciuta")
        self.assertEqual(actual[KEY]["facts"]["hours_text"], "Dalle 9 alle 18")
        self.assertTrue(report["outcomes"][0]["historical_edition"])
        self.assertNotIn("riscontri_campi", actual)

    def test_multi_day_interval_has_no_automatic_daily_or_weekly_schedule(self):
        result, _ = preview([row()], [observed(html(start="2026-11-01", end="2026-11-30"))], today=TODAY)
        self.assertEqual(result[0]["date"], [])
        self.assertEqual(result[0][KEY]["facts"]["edition_intervals"], [{"start": "2026-11-01", "end": "2026-11-30"}])
        self.assertEqual(result[0]["ricorrenza_testo"], row()["ricorrenza_testo"])

    def test_cancelled_explicit_date_never_appears_as_open(self):
        result, _ = preview([row()], [observed(html(schema_status="EventCancelled"))], today=TODAY)
        self.assertEqual(result[0]["date"], [])
        self.assertEqual(result[0][KEY]["facts"]["occurrences"][0]["status"], "cancelled")

    def test_human_calendar_and_fields_are_preserved(self):
        before = row(verificato_il="2026-10-19", date_quality="confermata", orario_testo="07:00–11:00")
        result, _ = preview([before], [observed()], today=TODAY)
        self.assertEqual(result[0]["date"], before["date"])
        self.assertEqual(result[0]["date_quality"], "confermata")
        self.assertEqual(result[0]["orario_testo"], before["orario_testo"])
        self.assertEqual(result[0]["indirizzo"], "")

    def test_unowned_address_conflict_holds_join_and_unowned_hours_stay(self):
        before = row(indirizzo="Via Altra, 8")
        result, report = preview([before], [observed()], today=TODAY)
        self.assertEqual(result, [before]); self.assertEqual(report["outcomes"][0]["reason"], "existing_venue_conflict")
        result, report = preview([row(orario_testo="7–11")], [observed()], today=TODAY)
        self.assertEqual(result[0]["orario_testo"], "7–11")
        self.assertTrue(any(v["field"] == "orario_testo" for v in report["outcomes"][0]["field_holds"]))

    def test_only_later_same_edition_owned_fields_can_change(self):
        initial, _ = preview([row()], [observed()], today=TODAY)
        nextday = TODAY + timedelta(days=1)
        updated, report = preview(initial, [observed(html(hours="10-19"), today=nextday)], today=nextday)
        self.assertEqual(updated[0]["orario_testo"], "10-19")
        self.assertTrue(updated[0]["riscontri_campi"][0].get("versioni_precedenti"))
        self.assertTrue(verify_exported(updated, report, today=nextday)["release_safe"])
        same_day, _ = preview(initial, [observed(html(hours="10-19"))], today=TODAY)
        self.assertEqual(same_day, initial)
        new_edition, report = preview(initial, [observed(html(start="2026-11-08", end="2026-11-08"), today=nextday)], today=nextday)
        self.assertEqual(new_edition, initial)
        self.assertEqual(report["outcomes"][0]["reason"], "source_edition_identity_changed")

    def test_same_value_does_not_grant_ownership_and_independent_receipt_blocks_update(self):
        same, _ = preview([row(orario_testo="Dalle 9 alle 18")], [observed()], today=TODAY)
        self.assertNotIn("orario_testo", same[0]["riscontri_campi"][0].get("campi_gestiti", []))
        initial, _ = preview([row()], [observed()], today=TODAY)
        other = make_receipt(initial[0], values={"orario_testo": initial[0]["orario_testo"]},
            source_url="https://www.comune.bologna.it/mercati", source_name="Comune", source_id="official",
            source_row="one", read_on=TODAY.isoformat(), source_updated_on="2026-10-19", source_sha256="a" * 64)
        initial[0]["riscontri_campi"].append(other)
        tomorrow = TODAY + timedelta(days=1)
        result, _ = preview(initial, [observed(html(hours="10-19"), today=tomorrow)], today=tomorrow)
        self.assertEqual(result[0]["orario_testo"], "Dalle 9 alle 18")

    def test_reread_is_idempotent_and_export_replays_all_facts(self):
        result, report = preview([row()], [observed()], today=TODAY)
        repeated, _ = preview(result, [observed()], today=TODAY)
        self.assertEqual(repeated, result)
        tomorrow = TODAY + timedelta(days=1)
        refreshed, _ = refresh_record(result[0], today=tomorrow)
        normalized, reason = normalize(refreshed, tomorrow)
        self.assertIsNotNone(normalized, reason)
        final = retain_editorial_evidence(refreshed, normalized, today=tomorrow)
        self.assertEqual(final[KEY], result[0][KEY])
        self.assertEqual(final["date"], ["2026-11-01"])
        self.assertTrue(verify_exported([final], report, today=tomorrow)["release_safe"])
        expired, _ = apply_editorial_scope(final, today=date(2026, 11, 2))
        self.assertEqual(expired["date"], [])
        self.assertEqual(expired["date_quality"], "sconosciuta")

    def test_diff_and_final_guards_reject_forged_values_even_with_recomputed_digest(self):
        before = [row()]; result, report = preview(before, [observed()], today=TODAY)
        for mutation in (lambda r: r.update(date=["2026-11-08"]),
                         lambda r: r.update(nome="Another event"),
                         lambda r: r[KEY]["facts"].update(hours_text="7–24"),
                         lambda r: r.update(provincia="MO"),
                         lambda r: r.update(orario_testo="7–24")):
            altered, proof = deepcopy(result), deepcopy(report); mutation(altered[0])
            proof["output_sha256"] = fingerprint(altered)
            with self.assertRaises(ValueError): verify_changes(before, altered, proof, today=TODAY)
            with self.assertRaises(ValueError): verify_exported(altered, report, today=TODAY)

    def test_raw_bytes_replay_rejects_forged_document_or_hash(self):
        blob = html(); docs = [observed(blob)]
        pages = [{"requested_url": URL, "final_url": URL, "read_on": TODAY.isoformat(), "html": blob}]
        self.assertEqual(verify_source_pages(pages, docs, today=TODAY)["source_pages_replayed"], 1)
        for change in ("facts", "hash", "body"):
            copied, raw = deepcopy(docs), deepcopy(pages)
            if change == "facts": copied[0]["parsed"]["event"]["hours_text"] = "7–24"
            elif change == "hash": copied[0]["parsed"]["source"]["html_sha256"] = "a" * 64
            else: raw[0]["html"] = html(hours="10-19")
            with self.assertRaises(ValueError): verify_source_pages(raw, copied, today=TODAY)

    def test_invalid_batch_shape_duplicate_url_and_stale_reads_fail_closed(self):
        for documents in ([observed(), observed()], [observed(today=TODAY - timedelta(days=46))]):
            with self.assertRaises(ValueError): preview([row()], documents, today=TODAY)
        with self.assertRaises(ValueError): preview([row(), row()], [observed()], today=TODAY)
        forged = observed(); forged["parsed"]["source"]["modified_at"] = "2026-10-19"
        with self.assertRaises(ValueError): preview([row()], [forged], today=TODAY)
        future = observed(html(publication="21 ottobre 2026 12:00"))
        result, report = preview([row()], [future], today=TODAY)
        self.assertEqual(result, [row()])
        self.assertEqual(report["outcomes"][0]["reason"], "source_evidence_not_bindable")


if __name__ == "__main__":
    unittest.main()
