"""Exact-identity and calendar regressions for observed Happings detail pages."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import happings_detail_enrichment as enrich
from happings_detail_layout import parse_detail
from source_calendar import (clean_source_calendar, clean_source_detail,
                             refresh_source_calendar, source_calendar_dates)

TODAY = date(2026, 10, 20)
PISA = "https://www.happings.com/it/happing/mercato-coperto-campagna-amica-di-pisa/"
FIXTURES = Path(__file__).parent / "fixtures/happings_detail"


def page(name="pisa", url=PISA, day=TODAY):
    return {"requested_url": url, "final_url": url,
            "html": (FIXTURES / (name + ".html")).read_bytes(),
            "fetched_at": day.isoformat() + "T12:00:00+00:00"}


def observed_page(name, day=TODAY):
    manifest = json.loads((FIXTURES / "manifest.json").read_text("utf-8"))
    capture = next(item["capture"] for item in manifest["samples"] if item["name"] == name)
    result = page(name, capture["requested_url"], day)
    result["final_url"] = capture["final_url"]
    return result


def document():
    source = page()
    return parse_detail(source["html"], requested_url=PISA, final_url=PISA)


def existing(**changes):
    result = {"slug": "existing-campagna-amica-pisa", "nome": "Mercato coperto Campagna Amica di Pisa",
              "citta": "Pisa", "provincia": "PI", "regione": "Toscana",
              "indirizzo": "VIA del Chiassatello, 64/65", "fonte": "happings.com",
              "url_fonte": "https://www.happings.com/it/mercati-settimanali-a-pisa.html",
              "ricorrenza_testo": "settimanale - sabato", "orario_testo": "",
              "date": ["2027-01-02"], "date_quality": "prevista", "verificato_il": "",
              "aggiornato_il": "2025-01-01", "status": "non_confermato",
              "position_quality": "sconosciuta", "lat": None, "lng": None,
              "categoria": "alimentare", "fonti": []}
    result.update(changes)
    return result


class HappingsDetailEnrichmentTests(unittest.TestCase):
    def run_source(self, rows=None, *, source=None, today=TODAY, **kwargs):
        return enrich.preview(rows or [], [source or page()], today=today,
                              apply=True, admit_new=True, **kwargs)

    def admit(self):
        rows, report = self.run_source()
        self.assertEqual(len(rows), 1)
        return rows[0], report

    def test_real_pisa_source_preserves_all_explicit_dates_and_global_hours(self):
        row, report = self.admit()
        self.assertEqual(row["indirizzo"], "VIA del Chiassatello, 64/65")
        self.assertEqual(row["orario_testo"], "7:30 - 12:30")
        self.assertEqual((row["citta"], row["provincia"], row["regione"]), ("Pisa", "PI", "Toscana"))
        self.assertEqual(len(row["date"]), 10)
        self.assertEqual(row["date"][0], "2026-10-24")
        self.assertEqual(row["date"][-1], "2026-12-26")
        self.assertEqual(row["date_quality"], "riportata")
        self.assertEqual(row["status"], "non_confermato")
        self.assertEqual(row["verificato_il"], "")
        self.assertEqual(report["coordinates_assigned"], 0)
        self.assertIsNone(row["lat"])
        self.assertEqual(row["dettaglio_fonte"]["evento"]["geo"]["precision"], "publisher_point_unverified")
        self.assertEqual(row["calendario_fonte"]["occorrenze"][0]["end_time"], "12:30")
        self.assertIsNone(row["calendario_fonte"]["occorrenze"][1]["end_time"])

    def test_preview_and_new_admission_are_opt_in(self):
        rows, report = enrich.preview([], [page()], today=TODAY)
        self.assertEqual(rows, [])
        self.assertEqual(len(report["candidates"]), 1)
        self.assertEqual(report["new_market_ids"], [])
        rows, report = enrich.preview([], [page()], today=TODAY, apply=True)
        self.assertEqual(rows, [])
        self.assertEqual(report["outcomes"][0]["reason"], "new_venue_admission_disabled")

    def test_pisa_never_replaces_other_weekly_market_in_same_city(self):
        weekly = existing(slug="mercato-settimanale-di-pisa-pisa-sabato",
                          nome="Mercato settimanale di Pisa", indirizzo="Piazza Vettovaglie")
        original = copy.deepcopy(weekly)
        rows, report = self.run_source([weekly])
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0], original)
        self.assertEqual(weekly, original)
        self.assertEqual(report["changed_existing_ids"], [])

    def test_same_page_reread_is_idempotent_and_does_not_create_another_venue(self):
        row, _ = self.admit()
        rows, report = self.run_source([row])
        self.assertEqual(rows, [row])
        self.assertEqual(report["new_market_ids"], [])
        self.assertEqual(report["changed_existing_ids"], [])

    def test_named_exact_venue_recovers_hours_and_replaces_forecast_with_reported_dates(self):
        before = existing()
        rows, report = self.run_source([before])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["slug"], before["slug"])
        self.assertEqual(rows[0]["url_fonte"], before["url_fonte"])
        self.assertEqual(rows[0]["orario_testo"], "7:30 - 12:30")
        self.assertNotIn("2027-01-02", rows[0]["date"])
        self.assertEqual(rows[0]["date_quality"], "riportata")
        self.assertEqual(report["changed_existing_ids"], [before["slug"]])
        self.assertEqual(rows[0]["aggiornato_il"], before["aggiornato_il"])
        self.assertEqual(rows[0]["ricorrenza_testo"], before["ricorrenza_testo"])

    def test_distinctive_name_and_exact_weekday_can_fill_blank_address(self):
        before = existing(indirizzo="")
        rows, _ = self.run_source([before])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["indirizzo"], "VIA del Chiassatello, 64/65")

    def test_wrong_weekday_blocks_join_and_duplicate_admission(self):
        before = existing(ricorrenza_testo="settimanale - venerdì")
        rows, report = self.run_source([before])
        self.assertEqual(rows, [before])
        self.assertEqual(report["outcomes"][0]["reason"], "ambiguous_existing_identity")

    def test_ambiguous_duplicate_saved_venues_are_not_merged(self):
        first, second = existing(), existing(slug="duplicate-source-market")
        rows, report = self.run_source([first, second])
        self.assertEqual(rows, [first, second])
        self.assertEqual(report["new_market_ids"], [])
        self.assertEqual(report["outcomes"][0]["reason"], "ambiguous_existing_identity")

    def test_same_street_and_day_other_name_is_held_instead_of_duplicated(self):
        before = existing(nome="Mercato settimanale di Pisa")
        rows, report = self.run_source([before])
        self.assertEqual(rows, [before])
        self.assertEqual(report["outcomes"][0]["reason"], "ambiguous_existing_identity")

    def test_existing_canonical_link_with_wrong_city_is_not_admitted_again(self):
        before = existing(citta="Lucca", provincia="LU", url_fonte=PISA)
        rows, report = self.run_source([before])
        self.assertEqual(rows, [before])
        self.assertEqual(report["outcomes"][0]["reason"], "ambiguous_existing_identity")

    def test_canonical_link_in_other_source_list_also_prevents_duplicate(self):
        before = existing(citta="Lucca", provincia="LU", fonti=[{"nome": "Happings", "url": PISA}])
        rows, report = self.run_source([before])
        self.assertEqual(rows, [before])
        self.assertEqual(report["new_market_ids"], [])

    def test_conflicting_unowned_address_holds_other_fields_and_calendar(self):
        before = existing(url_fonte=PISA, indirizzo="Via Garibaldi 10")
        rows, report = self.run_source([before])
        self.assertEqual(rows, [before])
        self.assertIn("source_address_conflicts_with_unowned_or_verified_venue",
                      report["outcomes"][0]["field_holds"])

    def test_house_number_separator_is_not_erased_for_matching(self):
        before = existing(url_fonte=PISA, indirizzo="VIA del Chiassatello, 64-65")
        rows, _ = self.run_source([before])
        self.assertEqual(rows, [before])

    def test_other_primary_source_never_receives_owned_field_or_calendar_assignment(self):
        before = existing(fonte="other.example", url_fonte="https://other.example/pisa")
        rows, report = self.run_source([before])
        self.assertEqual(rows[0]["orario_testo"], "")
        self.assertEqual(rows[0]["date"], before["date"])
        self.assertNotIn("calendario_fonte", rows[0])
        self.assertNotIn("campi_gestiti", rows[0]["riscontri_campi"][0])
        self.assertIn("secondary_source_cannot_assign_orario_testo", report["outcomes"][0]["field_holds"])

    def test_human_confirmation_and_unowned_reported_calendar_are_preserved(self):
        for changes in ({"verificato_il": "2026-10-19"}, {"date_quality": "confermata"},
                        {"date_quality": "riportata"}):
            with self.subTest(changes=changes):
                before = existing(**changes)
                rows, report = self.run_source([before])
                self.assertEqual(rows[0]["date"], before["date"])
                self.assertEqual(rows[0]["date_quality"], before["date_quality"])
                self.assertNotIn("calendario_fonte", rows[0])
                self.assertIn("existing_unowned_or_confirmed_calendar", report["outcomes"][0]["field_holds"])

    def test_newer_source_can_update_only_owned_hours_and_keeps_provenance(self):
        row, _ = self.admit()
        doc = document()
        doc["event"]["hours_text"] = "07:30 - 13:30"
        doc["source"]["html_sha256"] = "b" * 64
        tomorrow = TODAY + timedelta(days=1)
        with patch("happings_detail_layout.parse_detail", return_value=doc):
            rows, _ = self.run_source([row], source=page(day=tomorrow), today=tomorrow)
        self.assertEqual(rows[0]["orario_testo"], "07:30 - 13:30")
        receipt = rows[0]["riscontri_campi"][0]
        self.assertIn("orario_testo", receipt["campi_gestiti"])
        self.assertEqual(receipt["valori"]["ricorrenza_testo"], row["ricorrenza_testo"])
        self.assertTrue(receipt["versioni_precedenti"])

    def test_same_day_changed_page_has_no_proven_version_order(self):
        row, _ = self.admit()
        doc = document()
        doc["source"]["html_sha256"] = "c" * 64
        doc["event"]["hours_text"] = "07:30 - 14:30"
        with patch("happings_detail_layout.parse_detail", return_value=doc):
            rows, report = self.run_source([row])
        self.assertEqual(rows, [row])
        self.assertIn("source_version_ordering_not_proven", report["outcomes"][0]["field_holds"])

    def test_manual_hour_change_is_not_overwritten(self):
        row, _ = self.admit()
        row["orario_testo"] = "08:00 - 10:00"
        rows, report = self.run_source([row])
        self.assertEqual(rows[0]["orario_testo"], "08:00 - 10:00")
        self.assertIn("existing_unowned_or_verified_orario_testo", report["outcomes"][0]["field_holds"])

    def test_partial_calendar_cannot_admit_new_venue_or_replace_existing_dates(self):
        doc = document()
        doc["event"]["calendar_complete"] = False
        with patch("happings_detail_layout.parse_detail", return_value=doc):
            rows, report = self.run_source()
            self.assertEqual(rows, [])
            self.assertEqual(report["outcomes"][0]["reason"], "new_venue_requires_explicit_source_dates")
            before = existing()
            rows, report = self.run_source([before])
            self.assertEqual(rows[0]["date"], before["date"])
            self.assertNotIn("calendario_fonte", rows[0])
            self.assertEqual(rows[0]["orario_testo"], "7:30 - 12:30")

    def test_schema_next_occurrence_does_not_replace_a_complete_saved_list(self):
        row, _ = self.admit()
        doc = document()
        doc["event"]["calendar_scope"] = "schema_occurrence_only"
        doc["event"]["occurrences"] = doc["event"]["occurrences"][:1]
        doc["source"]["html_sha256"] = "e" * 64
        tomorrow = TODAY + timedelta(days=1)
        with patch("happings_detail_layout.parse_detail", return_value=doc):
            rows, report = self.run_source([row], source=page(day=tomorrow), today=tomorrow)
        self.assertEqual(rows[0]["calendario_fonte"], row["calendario_fonte"])
        self.assertIn("calendar_source_scope_became_partial", report["outcomes"][0]["field_holds"])

    def test_past_edition_is_never_rolled_into_next_year(self):
        doc = document()
        for item in doc["event"]["occurrences"]:
            item["date"] = item["date"].replace("2026-", "2025-")
        doc["event"]["edition_interval"] = {"start": "2025-10-03", "end": "2025-12-26"}
        with patch("happings_detail_layout.parse_detail", return_value=doc):
            rows, report = self.run_source()
        self.assertEqual(rows, [])
        self.assertEqual(report["outcomes"][0]["reason"], "new_venue_has_no_upcoming_source_date")

    def test_source_conflict_prevents_any_assignment_or_admission(self):
        doc = document()
        doc["status"] = "conflict"
        doc["conflicts"] = [{"field": "location", "code": "address_disagrees", "values": []}]
        before = existing()
        with patch("happings_detail_layout.parse_detail", return_value=doc):
            rows, report = self.run_source([before])
        self.assertEqual(rows, [before])
        self.assertEqual(report["outcomes"][0]["reason"], "source_layout_or_content_conflict")

    def test_unknown_or_disagreeing_istat_geography_is_held(self):
        for key, value in (("province", "LU"), ("region", "Lazio"), ("city", "Not a Comune")):
            doc = document()
            doc["event"]["location"][key] = value
            with patch("happings_detail_layout.parse_detail", return_value=doc):
                rows, report = self.run_source()
            self.assertEqual(rows, [])
            self.assertEqual(report["outcomes"][0]["reason"], "source_geography_not_exact_istat_identity")

    def test_publication_date_is_preserved_without_becoming_update_date(self):
        doc = document()
        doc["source"]["published_at"] = "2026-09-30T19:14:55+00:00"
        with patch("happings_detail_layout.parse_detail", return_value=doc):
            rows, _ = self.run_source()
        self.assertEqual(rows[0]["dettaglio_fonte"]["fonte_pubblicata_il"], "2026-09-30")
        self.assertEqual(rows[0]["fonte_aggiornata_il"], "")

    def test_repeated_canonical_page_is_rejected_before_duplicate_assignments(self):
        with self.assertRaisesRegex(ValueError, "Repeated canonical"):
            enrich.preview([], [page(), page()], today=TODAY, apply=True, admit_new=True)

    def test_read_date_is_required_current_and_timezone_explicit(self):
        for timestamp in (None, "2026-10-20T12:00:00", "2026-10-21T12:00:00+00:00",
                          "2026-01-01T12:00:00+00:00"):
            source = page()
            source["fetched_at"] = timestamp
            with self.subTest(timestamp=timestamp), self.assertRaises(ValueError):
                self.run_source(source=source)

    def test_candidate_changes_fail_verification(self):
        rows, report = self.run_source()
        changed = copy.deepcopy(rows)
        changed[0]["date"].append("2027-01-02")
        with self.assertRaises(ValueError):
            enrich.verify_changes([], changed, report, today=TODAY)
        report["output_sha256"] = enrich.digest(changed)
        with self.assertRaises(ValueError):
            enrich.verify_changes([], changed, report, today=TODAY)

    def test_page_receipt_and_calendar_proof_are_bound_even_after_hash_recomputed(self):
        for kind in ("page", "receipt", "calendar", "detail", "outcome"):
            rows, report = self.run_source()
            with self.subTest(kind=kind):
                if kind == "page":
                    report["source_pages"][0]["html_sha256"] = "d" * 64
                elif kind == "receipt":
                    rows[0]["riscontri_campi"][0]["sha256"] = "d" * 64
                elif kind == "calendar":
                    rows[0]["calendario_fonte"]["sha256"] = "d" * 64
                elif kind == "detail":
                    rows[0]["dettaglio_fonte"]["sha256"] = "d" * 64
                else:
                    report["outcomes"][0]["url"] = "https://www.happings.com/it/happing/other/"
                report["output_sha256"] = enrich.digest(rows)
                with self.assertRaises(ValueError):
                    enrich.verify_changes([], rows, report, today=TODAY)

    def test_existing_calendar_values_are_rebuilt_from_parsed_source_facts(self):
        before = existing()
        rows, report = self.run_source([before])
        rows[0]["date"].append("2027-01-02")
        report["output_sha256"] = enrich.digest(rows)
        report["changes"][0]["after_sha256"] = enrich.digest(rows[0])
        with self.assertRaisesRegex(ValueError, "reconstructed"):
            enrich.verify_changes([before], rows, report, today=TODAY)

    def test_unrepresentable_page_does_not_abort_later_valid_page(self):
        first = observed_page("pescia")
        bad = parse_detail(first["html"], requested_url=first["requested_url"], final_url=first["final_url"])
        bad["event"]["occurrences"][0]["start_time"] = "29:00"
        good = document()
        with patch("happings_detail_layout.parse_detail", side_effect=[bad, good]):
            rows, report = enrich.preview([], [first, page()], today=TODAY, apply=True, admit_new=True)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["citta"], "Pisa")
        self.assertEqual(report["outcomes"][0]["reason"], "source_detail_not_representable")
        self.assertEqual(report["outcomes"][1]["status"], "new_venue_admitted")

    def test_parser_layout_failure_does_not_abort_later_valid_page(self):
        first = observed_page("pescia")
        with patch("happings_detail_layout.parse_detail", side_effect=[ValueError("layout"), document()]):
            rows, report = enrich.preview([], [first, page()], today=TODAY, apply=True, admit_new=True)
        self.assertEqual(len(rows), 1)
        self.assertEqual(report["outcomes"][0]["reason"], "source_layout_or_content_conflict")

    def test_admission_limit_holds_remaining_candidates_without_losing_first(self):
        rows, report = enrich.preview([], [page(), observed_page("pescia")], today=TODAY,
                                      apply=True, admit_new=True, max_new=1)
        self.assertEqual(len(rows), 1)
        self.assertEqual(report["outcomes"][1]["reason"], "new_venue_batch_limit")

    def test_saved_agricultural_market_taxonomy_keeps_explicit_local_names(self):
        cases = [
            ("Agrimercato di Erba", "Mercati", "alimentare"),
            ("Agrimercato Campagna Amica di Novi", "Mercati", "alimentare"),
            ("Bauernmarkt in Kastelruth", "Mercati", "alimentare"),
            ("Campagna amica a Favaro veneto", "Mercati", "alimentare"),
            ("Inser Markt’l a Tirolo", "Mercati", "misto"),
            ("Mercato coperto Campagna Amica", "Mercati", "alimentare"),
        ]
        for title, category, expected in cases:
            with self.subTest(title=title):
                event = {"name": title, "category": category}
                self.assertEqual(enrich._category(event), expected)

    def test_market_name_tokens_cannot_override_unrelated_taxonomy(self):
        cases = [
            ("Agrimercato Campagna Amica di Novi", "Arte e cultura"),
            ("Bauernmarkt in Kastelruth", "Fiere"),
            ("Campagna Amica Day", "Fiere"),
            ("Campagna amica a Favaro veneto", "Sagre e folklore"),
            ("Inser Markt’l a Tirolo", "Concerti"),
            ("Concerto al mercato contadino", "Mercati"),
            ("Talk sul mercato finanziario", "Mercati"),
            ("11ª Via della Lana", "Mercati"),
            ("Biofest(a)", "Mercati"),
            ("Oasi Prodotti Tipici di Torino", "Mercati"),
        ]
        for title, category in cases:
            with self.subTest(title=title, category=category):
                self.assertIsNone(enrich._category({"name": title, "category": category}))

    def test_false_friend_market_talk_is_not_admitted(self):
        rows, report = self.run_source(source=observed_page("notizia_fumetti"))
        self.assertEqual(rows, [])
        self.assertEqual(report["outcomes"][0]["reason"], "source_category_or_event_is_not_a_market")

    def test_concert_inside_christmas_market_is_not_a_market_even_without_address_conflict(self):
        source = observed_page("natale_concerto")
        doc = parse_detail(source["html"], requested_url=source["requested_url"], final_url=source["final_url"])
        doc["status"], doc["conflicts"] = "parsed", []
        with patch("happings_detail_layout.parse_detail", return_value=doc):
            rows, report = self.run_source(source=source)
        self.assertEqual(rows, [])
        self.assertEqual(report["outcomes"][0]["reason"], "source_category_or_event_is_not_a_market")

    def test_source_category_is_required_even_when_name_contains_market(self):
        doc = document()
        for category in (None, "Arte e cultura", "Musica"):
            doc["event"]["category"] = category
            with patch("happings_detail_layout.parse_detail", return_value=doc):
                rows, report = self.run_source()
            self.assertEqual(rows, [])
            self.assertEqual(report["outcomes"][0]["reason"], "source_category_or_event_is_not_a_market")

    def test_generic_weekly_title_variant_needs_exact_venue_and_nominal_day(self):
        doc = document()
        doc["event"]["name"] = "Mercato del sabato mattina a Pisa"
        before = existing(nome="Mercato settimanale di Pisa")
        with patch("happings_detail_layout.parse_detail", return_value=doc):
            rows, report = self.run_source([before])
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["slug"], before["slug"])
        self.assertEqual(rows[0]["orario_testo"], "7:30 - 12:30")
        self.assertEqual(report["new_market_ids"], [])

    def test_lana_documented_extra_thursday_does_not_break_friday_market_identity(self):
        source = observed_page("lana")
        doc = parse_detail(source["html"], requested_url=source["requested_url"], final_url=source["final_url"])
        before = existing(nome="Mercato settimanale di Lana", citta="Lana", provincia="BZ",
                          regione="Trentino-Alto Adige", indirizzo=doc["event"]["location"]["street_address"],
                          ricorrenza_testo="settimanale - venerdì")
        rows, report = self.run_source([before], source=source)
        self.assertEqual(len(rows), 1, report["outcomes"])
        self.assertEqual(rows[0]["slug"], before["slug"])
        self.assertIn("2026-12-24", rows[0]["date"])

    def test_generic_same_weekday_different_venue_wording_blocks_duplicate_only(self):
        source = observed_page("lana")
        before = existing(nome="Mercato settimanale di Lana", citta="Lana", provincia="BZ",
                          regione="Trentino-Alto Adige", indirizzo='parco della Casa di Riposo "Lorenzerhof"',
                          ricorrenza_testo="settimanale - venerdì")
        rows, report = self.run_source([before], source=source)
        self.assertEqual(rows, [before])
        self.assertEqual(report["outcomes"][0]["reason"], "ambiguous_existing_identity")

    def test_source_venue_inside_existing_compound_address_blocks_duplicate_only(self):
        source = observed_page("lucca_antiquario")
        before = existing(nome="Mercato Antiquario Lucchese", citta="Lucca", provincia="LU",
                          categoria="antiquariato", fonte="cosedicasa.com",
                          url_fonte="https://www.cosedicasa.com/mercatini/lucca-piazza-antelminelli",
                          indirizzo='Piazza Antelminelli, via del Battistero, piazza San Martino, piazza San Giusto',
                          ricorrenza_testo="mensile - terza domenica del mese")
        rows, report = self.run_source([before], source=source)
        self.assertEqual(rows, [before])
        self.assertEqual(report["outcomes"][0]["reason"], "ambiguous_existing_identity")


class SourceCalendarTests(unittest.TestCase):
    def setUp(self):
        rows, _ = enrich.preview([], [page()], today=TODAY, apply=True, admit_new=True)
        self.row = rows[0]

    def test_expired_list_stays_empty_and_never_forecasts_january(self):
        result = refresh_source_calendar(self.row, today=date(2027, 1, 1))
        self.assertEqual(result["date"], [])
        self.assertEqual(result["date_quality"], "sconosciuta")
        self.assertIsNone(result["proiezione_regola"])

    def test_calendar_and_detail_are_bound_to_all_identity_fields(self):
        for key in ("slug", "citta", "provincia", "regione"):
            row = {**self.row, key: "another identity"}
            self.assertIsNone(clean_source_calendar(self.row["calendario_fonte"], row, today=TODAY))
            self.assertIsNone(clean_source_detail(self.row["dettaglio_fonte"], row, today=TODAY))

    def test_one_cancelled_or_postponed_occurrence_does_not_cancel_the_other_dates(self):
        calendar = copy.deepcopy(self.row["calendario_fonte"])
        calendar["occorrenze"][0]["status"] = "cancelled"
        calendar["occorrenze"][1]["status"] = "postponed"
        dates = source_calendar_dates(calendar, self.row, today=TODAY)
        self.assertEqual(len(dates), 8)
        self.assertNotIn("2026-10-24", dates)
        self.assertNotIn("2026-10-31", dates)
        self.assertIn("2026-11-07", dates)

    def test_existing_documented_cancellation_is_not_resurrected_by_reported_list(self):
        row = copy.deepcopy(self.row)
        row["eccezioni_calendario"] = [{
            "mercato": row["calendario_fonte"]["mercato"], "data": "2026-10-24",
            "letto_il": "2026-10-20", "url": "https://example.org/market-cancellation",
            "sha256": "c" * 64, "motivo": "Edizione annullata dall'organizzatore",
            "fonte_id": "organizer-notice"}]
        result = refresh_source_calendar(row, today=TODAY)
        self.assertNotIn("2026-10-24", result["date"])
        self.assertEqual(len(result["date"]), 9)

    def test_invalid_calendar_entry_invalidates_whole_calendar_instead_of_partial_truncation(self):
        for change in ({"date": "2026-02-30"}, {"start_time": "29:00"},
                       {"status": "confirmed"}, {"evidence": []}, {"unknown": "field"}):
            calendar = copy.deepcopy(self.row["calendario_fonte"])
            calendar["occorrenze"][0].update(change)
            self.assertIsNone(clean_source_calendar(calendar, self.row, today=TODAY))

    def test_human_confirmed_calendar_survives_source_refresh(self):
        row = {**self.row, "verificato_il": "2026-10-19", "date_quality": "confermata", "date": ["2026-11-01"]}
        result = refresh_source_calendar(row, today=TODAY)
        self.assertEqual(result["date"], ["2026-11-01"])
        self.assertEqual(result["date_quality"], "confermata")

    def test_lana_exception_survives_calendar_and_detail_serialization(self):
        rows, report = enrich.preview([], [observed_page("lana")], today=TODAY, apply=True, admit_new=True)
        self.assertEqual(len(rows), 1, report["outcomes"])
        christmas = [item for item in rows[0]["calendario_fonte"]["occorrenze"] if item["date"] == "2026-12-24"]
        self.assertEqual(christmas[0]["end_time"], "13:00")
        self.assertIn("13:00", rows[0]["orario_testo"])

    def test_lucca_weekend_keeps_boundary_hours_and_only_explicit_days(self):
        rows, report = enrich.preview([], [observed_page("lucca_antiquario")], today=TODAY,
                                      apply=True, admit_new=True)
        self.assertEqual(len(rows), 1, report["outcomes"])
        row = rows[0]
        self.assertEqual(row["date"], ["2026-11-14", "2026-11-15", "2026-12-19", "2026-12-20"])
        calendar = row["calendario_fonte"]
        self.assertEqual(len(calendar["intervalli"]), 3)
        saturday = next(item for item in calendar["occorrenze"] if item["date"] == "2026-11-14")
        sunday = next(item for item in calendar["occorrenze"] if item["date"] == "2026-11-15")
        self.assertEqual(saturday["start_time"], "08:00")
        self.assertIsNone(saturday["end_time"])
        self.assertIsNone(sunday["start_time"])
        self.assertEqual(sunday["end_time"], "20:00")
        self.assertFalse(calendar["intervalli"][0]["continuous_opening_confirmed"])

    def test_shopping_market_multiday_schema_keeps_interval_and_no_daily_hour_inference(self):
        rows, report = enrich.preview([], [observed_page("piemontese")], today=TODAY,
                                      apply=True, admit_new=True)
        self.assertEqual(len(rows), 1, report["outcomes"])
        row = rows[0]
        self.assertEqual(row["date"], ["2026-10-31", "2026-11-01"])
        self.assertEqual(len(row["calendario_fonte"]["intervalli"]), 1)
        self.assertIsNone(row["calendario_fonte"]["occorrenze"][0]["end_time"])
        self.assertIsNone(row["calendario_fonte"]["occorrenze"][1]["start_time"])

    def test_conditional_bad_weather_stays_a_condition_not_an_actual_cancellation(self):
        rows, report = enrich.preview([], [observed_page("castelrotto")], today=TODAY,
                                      apply=True, admit_new=True)
        self.assertEqual(len(rows), 1, report["outcomes"])
        row = rows[0]
        self.assertTrue(row["date"])
        self.assertTrue(row["dettaglio_fonte"]["evento"]["conditions"])
        self.assertTrue(all(item["status"] == "source_listed" for item in row["calendario_fonte"]["occorrenze"]))


class SourceAdmissionCertificateTests(unittest.TestCase):
    def test_over_sixty_four_unique_source_pages_keep_bounded_admission_and_certificate(self):
        from export_static import normalize
        template = observed_page("notizia_fumetti")
        source_url = template["requested_url"]
        pages = []
        for index in range(65):
            url = source_url.rstrip("/") + "-campione-" + str(index) + "/"
            pages.append({**template, "requested_url": url, "final_url": url,
                          "html": template["html"].replace(source_url.encode(), url.encode())})
        pages.append(page())
        rows, evidence = enrich.preview([], pages, today=TODAY, apply=True, admit_new=True)
        self.assertEqual(len(evidence["source_pages"]), 66)
        self.assertEqual(len({item["final_url"] for item in evidence["source_pages"]}), 66)
        self.assertEqual(evidence["counts"]["source_category_or_event_is_not_a_market"], 65)
        self.assertEqual(evidence["max_new"], 32)
        self.assertEqual(len(rows), 1)
        certificate = enrich.cert_from_detail_evidence(evidence, today=TODAY)
        exported = [normalize(row, TODAY)[0] for row in rows]
        self.assertEqual(enrich.verify_source_admission_certificate([], exported, certificate, TODAY),
                         ([], 1))
        with self.assertRaisesRegex(ValueError, "Invalid Happings detail batch"):
            enrich.preview([], pages + pages[:63], today=TODAY, apply=True, admit_new=True)

    def fixture(self):
        from export_static import normalize
        base = [existing(slug="unrelated-weekly", nome="Mercato settimanale di Pisa",
                         indirizzo="Piazza Vettovaglie")]
        rows, evidence = enrich.preview(base, [page(), observed_page("pescia")],
            today=TODAY, apply=True, admit_new=True)
        exported = [normalize(row, TODAY)[0] for row in rows]
        return base, exported, enrich.cert_from_detail_evidence(evidence, today=TODAY)

    def test_two_independent_admissions_reconstruct_without_self_collision(self):
        base, exported, certificate = self.fixture()
        comparable, count = enrich.verify_source_admission_certificate(base, exported, certificate, TODAY)
        self.assertEqual(count, 2)
        self.assertEqual([row["slug"] for row in comparable], [base[0]["slug"]])
        self.assertNotIn("candidate", certificate["admissions"][0])

    def test_missing_extra_or_removed_identity_is_not_hidden_by_certificate(self):
        base, exported, certificate = self.fixture()
        for bad in (exported[:-1], exported[1:], exported + [{"slug": "unproved-extra"}]):
            with self.subTest(bad_ids=[row["slug"] for row in bad]), self.assertRaises(ValueError):
                enrich.verify_source_admission_certificate(base, bad, certificate, TODAY)

    def test_detached_source_hash_and_calendar_fact_are_rejected(self):
        base, exported, certificate = self.fixture()
        bad = copy.deepcopy(certificate)
        bad["admissions"][0]["source_page"]["html_sha256"] = "0" * 64
        with self.assertRaises(ValueError):
            enrich.verify_source_admission_certificate(base, exported, bad, TODAY)
        bad = copy.deepcopy(certificate)
        bad["admissions"][0]["document"]["parsed"]["event"]["occurrences"][0]["date"] = "2026-10-25"
        with self.assertRaises(ValueError):
            enrich.verify_source_admission_certificate(base, exported, bad, TODAY)
        bad_rows = copy.deepcopy(exported)
        bad_rows[1]["orario_testo"] = "00:00 - 23:59"
        with self.assertRaises(ValueError):
            enrich.verify_source_admission_certificate(base, bad_rows, certificate, TODAY)

    def test_stale_duplicated_and_preexisting_admissions_fail(self):
        base, exported, certificate = self.fixture()
        with self.assertRaises(ValueError):
            enrich.verify_source_admission_certificate(base, exported, certificate, TODAY + timedelta(days=1))
        bad = copy.deepcopy(certificate)
        bad["admissions"].append(copy.deepcopy(bad["admissions"][0]))
        with self.assertRaises(ValueError):
            enrich.verify_source_admission_certificate(base, exported, bad, TODAY)
        with self.assertRaises(ValueError):
            enrich.verify_source_admission_certificate(base + [exported[1]], exported, certificate, TODAY)

    def test_source_validity_does_not_authorize_duplicate_venue(self):
        base, exported, certificate = self.fixture()
        duplicate = existing(slug="another-already-known-pisa-campagna-amica")
        with self.assertRaisesRegex(ValueError, "overlaps"):
            enrich.verify_source_admission_certificate(base + [duplicate], exported + [duplicate], certificate, TODAY)

    def test_no_certificate_preserves_historical_guard_input(self):
        self.assertEqual(enrich.verify_source_admission_certificate([], [{"slug": "x"}], None, TODAY),
                         ([{"slug": "x"}], 0))
        _, evidence = enrich.preview([], [], today=TODAY, apply=True, admit_new=True)
        self.assertIsNone(enrich.cert_from_detail_evidence(evidence, today=TODAY))


if __name__ == "__main__":
    unittest.main()
