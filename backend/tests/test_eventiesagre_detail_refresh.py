"""Existing-source identity, field ownership, edition limits and queue progress.

Synthetic HTML uses the already observed EES scopes; no publisher body is
copied into the repository and these tests never perform network requests.
"""
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_eventiesagre_source_layout import html as source_html, URL
from editorial_calendar_scope import (
    KEY, apply_editorial_scope, clean_editorial_evidence, retain_editorial_evidence,
    valid_editorial_reported_dates,
)
from eventiesagre_detail_refresh import (
    DEFAULT_POLICY, ROBOTS, STATE_FILENAME, catalog_urls, parse_document, preview,
    progress, run, seed_state, state_filename, validate_policy, validate_state,
    validate_redirects, verify_changes, verify_exported,
)
from export_static import normalize
from field_evidence import fingerprint, make_receipt
from recurrence_refresh import refresh_record

TODAY = date(2026, 10, 20)


def html(**changes):
    defaults = {"start": "01/10/2026", "end": "31/12/2026", "body": "<p>Ogni lunedì</p>"}
    defaults.update(changes)
    return source_html(**defaults).replace(b"Esempio", b"Bologna")


def row(**changes):
    result = {"slug": "preserved-market-id", "nome": "Mercato Di Bologna",
        "citta": "Bologna", "provincia": "BO", "regione": "Emilia-Romagna",
        "indirizzo": "", "orario_testo": "", "ricorrenza_testo": "settimanale - lunedì",
        "ricorrenza": "settimanale", "url_fonte": URL, "fonte": "eventiesagre.it",
        "date": ["2026-10-26", "2026-11-02", "2027-01-04"], "date_quality": "prevista",
        "proiezione_regola": {"kind": "weekly", "weekdays": [0]},
        "proiezione_generata_il": "2026-10-19", "proiezione_fonte": "ricorrenza_testo",
        "categoria": "misto", "status": "non_confermato", "fonti": [],
        "verificato_il": "", "lat": None, "lng": None, "position_quality": "sconosciuta",
        "confidence": 65, "fonte_aggiornata_il": "2026-10-10"}
    result.update(changes)
    return result


def document(blob=None, *, today=TODAY, url=URL):
    return {"read_on": today.isoformat(), "parsed": parse_document(
        blob or html(), requested_url=url, today=today)}


class EditorialBindingTests(unittest.TestCase):
    def test_existing_identity_fields_and_source_dates_survive(self):
        original = row()
        output, report = preview([original], [document()], today=TODAY)
        actual = output[0]
        self.assertEqual(actual["slug"], original["slug"])
        self.assertEqual(actual["url_fonte"], URL)
        self.assertEqual(actual["indirizzo"], "Via della Fonte, 4")
        self.assertEqual(actual["orario_testo"], "08:00–13:00")
        self.assertEqual(actual["date"], ["2026-10-26", "2026-11-02"])
        self.assertEqual(actual[KEY]["modified_on"], "2026-10-10")
        self.assertEqual(actual[KEY]["read_on"], "2026-10-20")
        self.assertEqual(actual["fonte_aggiornata_il"], original["fonte_aggiornata_il"])
        self.assertEqual(actual["riscontri_campi"][0]["campi_gestiti"], ["indirizzo", "orario_testo"])
        self.assertEqual(report["new_market_ids"], [])
        self.assertEqual(report["individual_openings_confirmed"], 0)
        self.assertTrue(verify_exported(output, report, today=TODAY)["release_safe"])

    def test_page_stating_the_same_rule_restates_the_recurrence_without_owning_it(self):
        output, _ = preview([row()], [document()], today=TODAY)
        proof = output[0]["riscontri_campi"][0]
        self.assertEqual(proof["valori"]["ricorrenza_testo"], "settimanale - lunedì")
        self.assertNotIn("ricorrenza_testo", proof["campi_gestiti"])
        other, _ = preview([row(ricorrenza_testo="settimanale - martedì")], [document()], today=TODAY)
        self.assertFalse(any("ricorrenza_testo" in p["valori"] for p in other[0].get("riscontri_campi") or []))
        self.assertEqual(other[0]["ricorrenza_testo"], "settimanale - martedì")

    def test_archived_edition_preserves_identity_and_facts_without_promoting_old_fields(self):
        original = row()
        output, report = preview([original], [document(html(
            start="01/01/2021", end="31/12/2021", archived=True,
            modified="2026-10-10 12:30:00"))], today=TODAY)
        actual = output[0]
        self.assertEqual(actual["date"], [])
        self.assertEqual(actual["date_quality"], "sconosciuta")
        self.assertEqual(actual["indirizzo"], "")
        self.assertEqual(actual["orario_testo"], "")
        self.assertEqual(actual[KEY]["facts"]["hours_text"], "08:00–13:00")
        self.assertTrue(actual[KEY]["facts"]["archive_marker"])
        self.assertEqual(actual["status"], original["status"])
        self.assertNotIn("riscontri_campi", actual)
        self.assertIsNone(actual["proiezione_regola"])
        self.assertEqual(report["outcomes"][0]["calendar_disposition"], "archived_edition_forecast_held")

    def test_unmarked_past_edition_still_removes_out_of_scope_predictions(self):
        output, _ = preview([row()], [document(html(start="01/01/2021", end="31/12/2021"))], today=TODAY)
        self.assertEqual(output[0]["date"], [])
        self.assertFalse(output[0][KEY]["facts"]["archive_marker"])

    def test_single_explicit_date_is_reported_without_making_a_weekly_series(self):
        output, _ = preview([row()], [document(html(start="02/11/2026", end="02/11/2026"))], today=TODAY)
        self.assertEqual(output[0]["date"], ["2026-11-02"])
        self.assertEqual(output[0]["date_quality"], "riportata")
        self.assertEqual(output[0][KEY]["calendar_mode"], "reported_explicit")
        self.assertTrue(valid_editorial_reported_dates(output[0], today=TODAY))
        unproved = deepcopy(output[0])
        unproved["date"].append("2026-11-09")
        self.assertFalse(valid_editorial_reported_dates(unproved, today=TODAY))
        later, _ = apply_editorial_scope(output[0], today=date(2026, 11, 3))
        self.assertEqual(later["date"], [])
        self.assertEqual(later["date_quality"], "sconosciuta")

    def test_blank_province_requires_unique_observed_geography_and_exact_venue(self):
        original = row(provincia="", indirizzo="Via della Fonte, 4")
        output, report = preview([original], [document()], today=TODAY)
        self.assertEqual(output[0]["provincia"], "")
        self.assertEqual(output[0][KEY]["facts"]["location"]["province"], "BO")
        self.assertEqual(output[0]["orario_testo"], "08:00–13:00")
        self.assertTrue(verify_exported(output, report, today=TODAY)["release_safe"])
        for changes in ({"regione": "Lombardia"}, {"regione": ""},
                        {"provincia": "FI"}, {"indirizzo": "Via Altra, 9"}):
            with self.subTest(changes=changes):
                bad = {**original, **changes}
                unchanged, _ = preview([bad], [document()], today=TODAY)
                self.assertEqual(unchanged, [bad])

    def test_blank_province_does_not_let_generic_title_fill_a_missing_venue(self):
        original = row(provincia="")
        unchanged, report = preview([original], [document()], today=TODAY)
        self.assertEqual(unchanged, [original])
        self.assertEqual(report["outcomes"][0]["reason"], "missing_province_requires_exact_venue_or_specific_title")
        observed = document()
        observed["parsed"]["event"]["name"] = "Il Mercato delle Curiosità a Bologna"
        named = row(provincia="", nome="Il Mercato delle Curiosità a Bologna")
        output, _ = preview([named], [observed], today=TODAY)
        self.assertEqual(output[0]["indirizzo"], "Via della Fonte, 4")
        self.assertEqual(output[0]["provincia"], "")

    def test_namesake_municipality_and_forged_province_cannot_bind(self):
        observed = document()
        observed["parsed"]["event"]["location"].update(city="Castro", province="LE", region="Puglia")
        original = row(citta="Castro", provincia="", regione="Lombardia", indirizzo="Via della Fonte, 4")
        unchanged, _ = preview([original], [observed], today=TODAY)
        self.assertEqual(unchanged, [original])
        observed["parsed"]["event"]["location"]["region"] = "Lombardia"
        unchanged, _ = preview([original], [observed], today=TODAY)
        self.assertEqual(unchanged, [original])

    def test_future_editorial_metadata_holds_only_its_row(self):
        original = row()
        observed = document()
        observed["parsed"]["source"]["modified_at"] = "2027-01-01"
        unchanged, report = preview([original], [observed], today=TODAY)
        self.assertEqual(unchanged, [original])
        self.assertEqual(report["outcomes"][0]["reason"], "source_evidence_not_bindable")

    def test_range_without_observed_recurrence_never_becomes_daily_or_weekly_openings(self):
        output, _ = preview([row()], [document(html(body="<p>Informazioni sul mercato.</p>"))], today=TODAY)
        self.assertEqual(output[0]["date"], [])
        self.assertEqual(output[0][KEY]["facts"]["edition_intervals"],
                         [{"start": "2026-10-01", "end": "2026-12-31"}])

    def test_incompatible_catalog_recurrence_does_not_get_a_partial_false_calendar(self):
        output, report = preview([row(ricorrenza_testo="settimanale - sabato")], [document()], today=TODAY)
        self.assertEqual(output[0]["date"], [])
        self.assertEqual(report["outcomes"][0]["calendar_disposition"], "editorial_recurrence_conflicts_with_catalog")

    def test_calendar_conflict_does_not_hide_independent_hours(self):
        ld = json.dumps({"@type": "Event", "url": URL, "startDate": "2030-01-01"})
        output, report = preview([row()], [document(html(jsonld=ld))], today=TODAY)
        self.assertEqual(output[0]["orario_testo"], "08:00–13:00")
        self.assertEqual(output[0]["date"], [])
        self.assertTrue(any(v["field"] == "calendar" for v in output[0][KEY]["conflicts"]))
        self.assertTrue(verify_exported(output, report, today=TODAY)["release_safe"])

    def test_partial_hours_never_acquire_an_invented_end(self):
        output, _ = preview([row()], [document(html(hours="dalle ore 10:00"))], today=TODAY)
        self.assertEqual(output[0]["orario_testo"], "Dalle 10:00")

    def test_unowned_nonempty_address_conflict_holds_the_source_join(self):
        original = row(indirizzo="Via già salvata 19")
        output, report = preview([original], [document()], today=TODAY)
        self.assertEqual(output, [original])
        self.assertEqual(report["outcomes"][0]["reason"], "existing_venue_conflict")

    def test_unowned_nonempty_hours_remain_and_conflict_is_visible(self):
        output, report = preview([row(orario_testo="07:00–11:00")], [document()], today=TODAY)
        self.assertEqual(output[0]["orario_testo"], "07:00–11:00")
        self.assertEqual(report["outcomes"][0]["field_holds"][0]["field"], "orario_testo")

    def test_same_value_observation_does_not_create_field_ownership(self):
        original = row(indirizzo="Via della Fonte, 4", orario_testo="08:00–13:00")
        output, _ = preview([original], [document()], today=TODAY)
        self.assertNotIn("gestore_campi", output[0]["riscontri_campi"][0])

    def test_later_source_can_update_only_its_own_assigned_fields(self):
        first, _ = preview([row()], [document()], today=TODAY)
        tomorrow = TODAY + timedelta(days=1)
        latest = document(html(address="Via Nuova, 2", hours="dalle ore 09:00 alle ore 14:00",
                               modified="2026-10-21 08:00:00"), today=tomorrow)
        second, report = preview(first, [latest], today=tomorrow)
        self.assertEqual(second[0]["indirizzo"], "Via Nuova, 2")
        self.assertEqual(second[0]["orario_testo"], "09:00–14:00")
        self.assertTrue(second[0]["riscontri_campi"][0].get("versioni_precedenti"))
        self.assertTrue(verify_changes(first, second, report, today=tomorrow)["release_safe"])

    def test_unchanged_reread_preserves_ownership_for_a_later_changed_source(self):
        assigned, _ = preview([row()], [document()], today=TODAY)
        day2, day3 = TODAY + timedelta(days=1), TODAY + timedelta(days=2)
        reread, _ = preview(assigned, [document(today=day2)], today=day2)
        receipt = reread[0]["riscontri_campi"][0]
        self.assertEqual(receipt["gestore_campi"], "eventiesagre_detail")
        self.assertEqual(receipt["campi_gestiti"], ["indirizzo", "orario_testo"])
        updated, report = preview(reread, [document(html(hours="dalle ore 09:00 alle ore 14:00",
            modified="2026-10-22 08:00:00"), today=day3)], today=day3)
        self.assertEqual(updated[0]["orario_testo"], "09:00–14:00")
        self.assertTrue(updated[0]["riscontri_campi"][0]["versioni_precedenti"])
        self.assertTrue(verify_exported(updated, report, today=day3)["release_safe"])

    def test_same_day_changed_content_cannot_establish_update_order(self):
        first, _ = preview([row()], [document()], today=TODAY)
        second, report = preview(first, [document(html(hours="dalle ore 09:00 alle ore 14:00"))], today=TODAY)
        self.assertEqual(second, first)
        self.assertEqual(report["outcomes"][0]["reason"], "source_version_ordering_not_proven")

    def test_foreign_primary_url_source_number_or_geography_never_matches(self):
        for change in ({"url_fonte": URL.replace("12345_", "67890_")},
                       {"citta": "Modena", "provincia": "MO"},
                       {"provincia": "FI"}, {"regione": "Toscana"}):
            with self.subTest(change=change):
                original = row(**change)
                if "url_fonte" in change:
                    with self.assertRaises(ValueError):
                        preview([original], [document()], today=TODAY)
                else:
                    after, _ = preview([original], [document()], today=TODAY)
                    self.assertEqual(after, [original])
        with self.assertRaises(ValueError):
            parse_document(html(event_id="67890"), requested_url=URL, today=TODAY)

    def test_four_distinct_venues_survive_and_duplicate_source_block_never_creates_id(self):
        blocks = []
        rows = []
        for i, day in enumerate(("lunedì", "martedì", "mercoledì", "giovedì")):
            blocks.append(f"<p>Luogo: Via Sede {i}</p><p>Giorni di svolgimento: {day}</p>"
                          f"<p>Orario: Dalle ore {8+i} alle ore {12+i}</p>")
            rows.append(row(slug=f"existing-venue-{i}", indirizzo=f"Via Sede {i}",
                            ricorrenza_testo="settimanale - " + day))
        blob = html(address="", hours="", body="".join(blocks + blocks[:1]))
        output, report = preview(rows, [document(blob)], today=TODAY)
        self.assertEqual([r["slug"] for r in output], [r["slug"] for r in rows])
        self.assertEqual(len(output), 4)
        self.assertEqual([r["orario_testo"] for r in output],
                         ["08:00–12:00", "09:00–13:00", "10:00–14:00", "11:00–15:00"])
        self.assertEqual(len({r[KEY]["facts"]["selected_row_id"] for r in output}), 4)
        self.assertEqual(len(output[0][KEY]["facts"]["source_rows"]), 4)
        self.assertTrue(all(not r["date"] for r in output))
        self.assertEqual(report["new_market_ids"], [])

    def test_multi_venue_missing_address_cannot_receive_the_first_block(self):
        body = ("<p>Luogo: Via Uno</p><p>Giorni di svolgimento: lunedì</p>"
                "<p>Orario: Dalle 8 alle 13</p><p>Luogo: Via Due</p>"
                "<p>Giorni di svolgimento: lunedì</p><p>Orario: Dalle 9 alle 14</p>")
        original = row()
        output, report = preview([original], [document(html(address="", body=body))], today=TODAY)
        self.assertEqual(output, [original])
        self.assertEqual(report["outcomes"][0]["reason"], "multiple_venues_need_exact_address_and_days")

    def test_human_confirmation_and_independent_recent_recurrence_survive_archival_source(self):
        original = row(verificato_il="2026-10-19", date_quality="confermata")
        archived = document(html(start="01/01/2021", end="31/12/2021", archived=True))
        output, _ = preview([original], [archived], today=TODAY)
        self.assertEqual(output[0]["date"], original["date"])
        self.assertEqual(output[0]["date_quality"], "confermata")
        original = row()
        original["riscontri_campi"] = [make_receipt(original,
            values={"ricorrenza_testo": original["ricorrenza_testo"]},
            source_url="https://www.comune.bologna.it/mercati", source_name="Comune",
            source_id="official-independent", source_row="venue", read_on="2026-10-19",
            source_updated_on="2026-10-10", source_sha256="a" * 64)]
        output, _ = preview([original], [archived], today=TODAY)
        self.assertEqual(output[0]["date"], original["date"])

    def test_offline_refresh_export_and_reload_cannot_reanimate_archived_forecasts(self):
        output, report = preview([row()], [document(html(
            start="01/01/2021", end="31/12/2021", archived=True))], today=TODAY)
        tomorrow = TODAY + timedelta(days=1)
        refreshed, _ = refresh_record(output[0], tomorrow)
        scoped, _ = apply_editorial_scope(refreshed, today=tomorrow)
        normalized, reason = normalize(scoped, tomorrow)
        self.assertIsNone(reason)
        final = retain_editorial_evidence(scoped, normalized, today=tomorrow)
        self.assertEqual(final["date"], [])
        self.assertIsNone(final["proiezione_regola"])
        self.assertEqual(final[KEY]["read_on"], "2026-10-20")
        self.assertEqual(final[KEY]["modified_on"], "2026-10-10")
        reloaded = json.loads(json.dumps(final))
        refreshed_again, _ = refresh_record(reloaded, tomorrow + timedelta(days=1))
        final_again, _ = apply_editorial_scope(refreshed_again, today=tomorrow + timedelta(days=1))
        self.assertEqual(final_again["date"], [])
        self.assertTrue(verify_exported([final_again], report, today=tomorrow + timedelta(days=1))["release_safe"])

    def test_semantic_guard_rejects_unproved_field_even_after_hashes_are_recomputed(self):
        original = row()
        output, report = preview([original], [document()], today=TODAY)
        changed = deepcopy(output)
        changed[0]["orario_testo"] = "00:00–23:59"
        changed[0]["riscontri_campi"][0]["valori"]["orario_testo"] = "00:00–23:59"
        altered = deepcopy(report)
        altered["output_sha256"] = fingerprint(changed)
        altered["outcomes"][0]["after_sha256"] = fingerprint(changed[0])
        with self.assertRaises(ValueError):
            verify_changes([original], changed, altered, today=TODAY)

    def test_export_guard_reconstructs_facts_not_only_the_saved_source_hash(self):
        output, report = preview([row()], [document()], today=TODAY)
        for change in (lambda facts: facts.update(hours_text="00:00–23:59"),
                       lambda facts: facts["edition_intervals"][0].update(end="2030-12-31"),
                       lambda facts: facts.update(conditions=["Unsupported claim"])):
            altered = deepcopy(output)
            change(altered[0][KEY]["facts"])
            with self.assertRaises(ValueError):
                verify_exported(altered, report, today=TODAY)

    def test_tampered_scope_and_identity_are_rejected(self):
        output, _ = preview([row()], [document()], today=TODAY)
        for change in (lambda e: e.update(source_id="99999"),
                       lambda e: e["market"].update(citta="Modena"),
                       lambda e: e.update(read_on="2027-01-01")):
            altered = deepcopy(output[0])
            change(altered[KEY])
            self.assertIsNone(clean_editorial_evidence(altered[KEY], altered, today=TODAY))
            with self.assertRaises(ValueError):
                apply_editorial_scope(altered, today=TODAY)
        # A stored rule is derived, never trusted: it is re-read from the saved text.
        altered = deepcopy(output[0])
        honest = altered[KEY]["facts"]["forecast_rule"]
        altered[KEY]["facts"]["forecast_rule"] = {"kind": "daily"}
        self.assertEqual(clean_editorial_evidence(altered[KEY], altered, today=TODAY)["facts"]["forecast_rule"], honest)


class EditorialQueueTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.path = Path(self.folder.name)
        self.clock = 0.0
        self.calls = []
        self.robots = b"User-agent: *\nDisallow:\nCrawl-delay: 2\n"
        self.failure_urls = set()

    def tick(self):
        return self.clock

    def sleep(self, seconds):
        self.clock += seconds

    def fetch(self, url, **kwargs):
        self.calls.append(url)
        self.clock += .2
        if url == ROBOTS:
            return self.robots, url
        if url in self.failure_urls:
            raise OSError("Observed transport failure")
        numeric = url.split("/")[-1].split("_")[0]
        return html(event_id=numeric), url

    def execute(self, rows=None, **changes):
        policy = {**DEFAULT_POLICY, "max_details": 2}
        args = {"out": self.path / "run", "today": TODAY, "baseline_signature": "baseline",
            "policy_digest": "policy", "policy": policy, "fetcher": self.fetch,
            "monotonic": self.tick, "sleep": self.sleep,
            "now": lambda: datetime(2026, 10, 20, 12, tzinfo=timezone.utc)}
        args.update(changes)
        return run(rows or [row()], **args)

    def inventory(self, count):
        return [row(slug=f"kept-{i}", url_fonte=URL.replace("12345_", f"{10000+i}_")) for i in range(count)]

    def test_distinct_ids_share_one_request_and_the_queue_has_only_existing_urls(self):
        rows = [row(), row(slug="second-existing-id"), row(slug="outside", url_fonte="https://example.org/market")]
        output, report, preserve = self.execute(rows)
        self.assertEqual(self.calls, [ROBOTS, URL])
        self.assertEqual(set(report["state"]["resources"]), {URL})
        self.assertEqual(report["progress"]["cycle_read"], 1)
        self.assertEqual(preserve, {"preserved-market-id", "second-existing-id"})
        self.assertEqual([r["slug"] for r in output], [r["slug"] for r in rows])
        self.assertTrue((self.path / "run" / STATE_FILENAME).is_file())

    def test_empty_publisher_inventory_finishes_without_any_network_request(self):
        original = row(url_fonte="https://example.org/market")
        output, report, preserve = self.execute([original])
        self.assertEqual(output, [original])
        self.assertEqual(self.calls, [])
        self.assertEqual(report["status"], "completed")
        self.assertEqual(report["stop_reason"], "no_catalog_rows")
        self.assertEqual(report["network_requests"], 0)
        self.assertEqual(report["progress"]["resources"], 0)
        self.assertFalse(report["progress"]["successful_read_cycle_complete"])
        self.assertEqual(preserve, set())

    def test_full_attempt_cycle_advances_without_starving_failed_or_unread_urls(self):
        rows = self.inventory(5)
        self.failure_urls.add(rows[0]["url_fonte"])
        _, first, _ = self.execute(rows)
        self.assertEqual(first["progress"]["cycle_attempted"], 2)
        self.assertEqual(first["progress"]["cycle_read"], 1)
        _, second, _ = self.execute(rows, out=self.path / "run2", previous_state=first["state"])
        _, third, _ = self.execute(rows, out=self.path / "run3", previous_state=second["state"])
        self.assertEqual(third["progress"]["cycle_attempted"], 5)
        self.assertEqual(third["progress"]["cycle_read"], 4)
        self.assertTrue(third["progress"]["attempt_cycle_complete"])
        self.assertFalse(third["progress"]["successful_read_cycle_complete"])
        self.assertEqual(third["progress"]["overdue_urls"], [rows[0]["url_fonte"]])
        _, fourth, _ = self.execute(rows, out=self.path / "run4", previous_state=third["state"])
        self.assertEqual(fourth["progress"]["cycle"], 2)
        self.assertEqual(fourth["progress"]["last_completed_cycle"], 1)
        self.assertFalse(fourth["progress"]["market_freshness_guaranteed"])

    def test_robots_denial_advances_attempt_coverage_without_claiming_a_read(self):
        self.robots = b"User-agent: *\nDisallow: /\n"
        output, report, _ = self.execute()
        self.assertEqual(self.calls, [ROBOTS])
        self.assertEqual(output, [row()])
        self.assertEqual(report["progress"]["cycle_attempted"], 1)
        self.assertEqual(report["progress"]["cycle_read"], 0)
        self.assertEqual(report["state"]["resources"][URL]["status"], "robots_denied")

    def test_missing_or_unreadable_robots_performs_no_detail_requests(self):
        self.robots = b"<html>Temporary error</html>"
        output, report, _ = self.execute()
        self.assertEqual(output, [row()])
        self.assertEqual(self.calls, [ROBOTS])
        self.assertEqual(report["status"], "robots_unavailable")
        self.assertEqual(report["progress"]["cycle_attempted"], 0)

    def test_shared_deadline_and_publisher_rate_are_both_respected(self):
        self.robots = b"User-agent: *\nDisallow:\nRequest-rate: 1/10\n"
        _, report, _ = self.execute(self.inventory(5), deadline=15)
        self.assertEqual(report["details_attempted"], 1)
        self.assertEqual(report["robots"]["pacing_seconds"], 10)
        self.assertEqual(report["stop_reason"], "time_budget")
        self.assertLessEqual(self.clock, 15)

    def test_elapsed_budget_stops_even_when_request_quota_is_not_reached(self):
        _, report, _ = self.execute(self.inventory(10), policy={**DEFAULT_POLICY, "max_seconds": 7})
        self.assertLess(report["details_attempted"], 64)
        self.assertEqual(report["stop_reason"], "time_budget")
        self.assertLessEqual(report["elapsed_seconds"], 7)

    def test_resume_reuses_exact_checkpoint_without_another_network_request(self):
        rows = self.inventory(3)
        first, report, _ = self.execute(rows)
        before = len(self.calls)
        again, resumed, _ = self.execute(rows, resume=True)
        self.assertEqual(again, first)
        self.assertEqual(len(self.calls), before)
        self.assertEqual(resumed["network_requests"], 0)
        self.assertEqual(resumed["state"], report["state"])
        self.assertEqual(resumed["evidence"], report["evidence"])

    def test_resume_rejects_changed_baseline_or_checkpoint_body(self):
        self.execute()
        with self.assertRaises(ValueError):
            self.execute(resume=True, baseline_signature="other-baseline")
        path = self.path / "run/sources/eventiesagre-detail-pages.json"
        saved = json.loads(path.read_text())
        saved["pages"][0]["sha256"] = "0" * 64
        path.write_text(json.dumps(saved))
        with self.assertRaises(ValueError):
            self.execute(resume=True)

    def test_resume_rejects_unattempted_url_marked_as_read_or_completed(self):
        rows = self.inventory(3)
        self.execute(rows)
        path = self.path / "run/sources/eventiesagre-detail-pages.json"
        saved = json.loads(path.read_text())
        invented = deepcopy(saved["state"]["resources"][rows[0]["url_fonte"]])
        saved["state"]["resources"][rows[2]["url_fonte"]] = invented
        path.write_text(json.dumps(saved))
        with self.assertRaisesRegex(ValueError, "unobserved queue history"):
            self.execute(rows, resume=True)

    def test_offline_runs_do_not_invent_reads_or_reset_existing_attempts(self):
        _, first, _ = self.execute(self.inventory(3))
        old_count = len(self.calls)
        unchanged, offline, _ = self.execute(self.inventory(3), offline=True,
                                            out=self.path / "offline", previous_state=first["state"])
        self.assertEqual(unchanged, self.inventory(3))
        self.assertEqual(old_count, len(self.calls))
        self.assertEqual(offline["state"], first["state"])

    def test_public_state_contains_transport_bookkeeping_and_no_publisher_body(self):
        _, report, _ = self.execute()
        saved = (self.path / "run" / STATE_FILENAME).read_text()
        self.assertNotIn("body", saved)
        self.assertNotIn("Via della Fonte", saved)
        self.assertNotIn("08:00", saved)
        self.assertEqual(json.loads(saved), report["state"])

    def test_overdue_source_reads_are_measured_not_assumed_fresh_from_cycle_completion(self):
        _, report, _ = self.execute()
        later = TODAY + timedelta(days=46)
        measured = progress(report["state"], today=later)
        self.assertEqual(measured["overdue_urls"], [URL])
        self.assertEqual(measured["never_read"], 0)
        self.assertFalse(measured["market_freshness_guaranteed"])

    def test_request_policy_cannot_enable_new_ids_or_increase_limits(self):
        self.assertEqual(validate_policy()["max_seconds"], 600)
        for key, value in (("max_details", 129), ("max_seconds", 601),
                           ("new_market_ids_allowed", True), ("overwrite_unowned_fields", True),
                           ("min_delay_seconds", 0)):
            with self.subTest(key=key), self.assertRaises(ValueError):
                validate_policy({**DEFAULT_POLICY, key: value})

    def test_tampered_queue_future_read_or_nonpublisher_url_fails_closed(self):
        state = seed_state([row()], today=TODAY)
        state["resources"][URL]["last_attempt"] = "2027-01-01"
        state["resources"][URL]["attempts"] = 1
        with self.assertRaises(ValueError):
            validate_state(state, today=TODAY)
        self.assertEqual(catalog_urls([row(url_fonte="http://www.eventiesagre.it/unsafe")]), [])


CDC = "cosedicasa.com"
CDC_FIXTURES = Path(__file__).parent / "fixtures/cosedicasa_detail"
CDC_SAMPLES = {v["sample"]: v for v in json.loads((CDC_FIXTURES / "manifest.json").read_text())["samples"]}


def cdc_document(name):
    sample = CDC_SAMPLES[name]
    return {"read_on": TODAY.isoformat(), "parsed": parse_document(
        (CDC_FIXTURES / sample["fixture_file"]).read_bytes(), requested_url=sample["requested_url"],
        final_url=sample["final_url"], today=TODAY)}


def cdc_row(name, **changes):
    sample, event = CDC_SAMPLES[name], cdc_document(name)["parsed"]["event"]
    result = row(slug="existing-cdc-" + name, nome=event["name"], citta=event["location"]["city"],
        provincia={"bologna": "BO", "venezia": "VE"}.get(name, ""),
        regione=event["location"]["region"], indirizzo=sample["expected"]["location"]["address"],
        url_fonte=sample["requested_url"], fonte=CDC, ricorrenza_testo="mensile - 2ª domenica")
    result.update(changes)
    return result


class CoseDiCasaBridgeTests(unittest.TestCase):
    def test_all_five_observed_shapes_keep_facts_and_never_flatten_editions(self):
        names = list(CDC_SAMPLES)
        before = [cdc_row(name) for name in names]
        after, report = preview(before, [cdc_document(name) for name in names], today=TODAY, publisher=CDC)
        by_name = dict(zip(names, after))
        self.assertEqual([v["slug"] for v in after], [v["slug"] for v in before])
        self.assertTrue(all(not v["date"] for v in after))
        self.assertEqual(by_name["bologna"]["orario_testo"], "08:30–18:00")
        self.assertEqual(by_name["venezia"]["orario_testo"], "09:00–19:00")
        self.assertEqual(by_name["todi"]["orario_testo"], "09:00–tramonto")
        self.assertIsNone(by_name["todi"][KEY]["facts"]["hours_intervals"][0]["end"])
        self.assertEqual(by_name["cernobbio"]["orario_testo"], "")
        self.assertEqual(by_name["fiumicino"]["orario_testo"], "")
        self.assertEqual(by_name["fiumicino"][KEY]["facts"]["hours_text"], "18:00–24:00")
        self.assertEqual(len(by_name["cernobbio"][KEY]["facts"]["occurrences"]), 14)
        self.assertEqual(len(by_name["venezia"][KEY]["facts"]["edition_intervals"]), 5)
        self.assertEqual(by_name["todi"]["provincia"], "")
        self.assertEqual(by_name["todi"][KEY]["facts"]["observed_location"]["province"], "Perugia")
        self.assertTrue(verify_exported(after, report, today=TODAY)["release_safe"])

    def test_actual_todi_address_difference_stays_held_despite_matching_title(self):
        before = cdc_row("todi", indirizzo="Giardini Oberdan (all'arrivo dell'ascensore del parcheggio)")
        after, report = preview([before], [cdc_document("todi")], today=TODAY, publisher=CDC)
        self.assertEqual(after, [before])
        self.assertEqual(report["outcomes"][0]["reason"], "existing_venue_conflict")

    def test_canonical_changed_slug_without_actual_http_redirect_never_binds(self):
        sample = CDC_SAMPLES["cernobbio"]
        document = {"read_on": TODAY.isoformat(), "parsed": parse_document(
            (CDC_FIXTURES / sample["fixture_file"]).read_bytes(), requested_url=sample["requested_url"], today=TODAY)}
        original = cdc_row("cernobbio")
        after, report = preview([original], [document], today=TODAY, publisher=CDC)
        self.assertEqual(after, [original])
        self.assertEqual(report["outcomes"][0]["status"], "held")

    def test_observed_cdc_redirect_survives_checkpoint_resume_and_missing_chain_fails(self):
        sample = CDC_SAMPLES["cernobbio"]
        original, final = sample["requested_url"], sample["final_url"]
        calls, clock = [], [0.0]
        def fetch(url, **kwargs):
            calls.append(url)
            clock[0] += .2
            if url.endswith("/robots.txt"):
                return b"User-agent: *\nDisallow:\n", url
            if url == original:
                raise HTTPError(url, 301, "Moved", {"Location": final}, None)
            return (CDC_FIXTURES / sample["fixture_file"]).read_bytes(), url
        def sleep(seconds):
            clock[0] += seconds
        with tempfile.TemporaryDirectory() as folder:
            args = dict(out=Path(folder), today=TODAY, baseline_signature="baseline", policy_digest="policy",
                publisher=CDC, fetcher=fetch, monotonic=lambda: clock[0], sleep=sleep,
                now=lambda: datetime(2026, 10, 20, 12, tzinfo=timezone.utc))
            after, report, _ = run([cdc_row("cernobbio")], **args)
            self.assertEqual(calls, ["https://www.cosedicasa.com/robots.txt", original, final])
            self.assertEqual(report["source_pages"][0]["redirects"], [{"from": original, "to": final, "status": 301}])
            self.assertTrue(after[0][KEY]["redirect_observed"])
            self.assertTrue((Path(folder) / state_filename(CDC)).is_file())
            resumed, again, _ = run([cdc_row("cernobbio")], resume=True, **args)
            self.assertEqual(resumed, after)
            self.assertEqual(again["state"], report["state"])
            self.assertEqual(len(calls), 3)
            path = Path(folder) / "sources/cosedicasa-detail-pages.json"
            saved = json.loads(path.read_text())
            saved["pages"][0]["redirects"] = []
            path.write_text(json.dumps(saved))
            with self.assertRaises(ValueError):
                run([cdc_row("cernobbio")], resume=True, **args)

    def test_redirect_chain_cannot_change_numeric_ees_identity_or_invent_a_cdc_hop(self):
        self.assertFalse(validate_redirects(URL, URL, []))
        for target, chain in (
            (URL.replace("12345_", "67890_"), [{"from": URL, "to": URL.replace("12345_", "67890_"), "status": 301}]),
            ("https://www.cosedicasa.com/mercatini/foreign", []),
            (URL, [{"from": URL, "to": URL, "status": 200}])):
            with self.subTest(target=target), self.assertRaises(ValueError):
                validate_redirects(URL, target, chain)

    def test_cdc_quota_is_independent_and_cannot_borrow_ees_time(self):
        policy = validate_policy(publisher=CDC)
        self.assertEqual((policy["max_details"], policy["max_seconds"]), (64, 300))
        for change in ({"max_details": 65}, {"max_seconds": 301}):
            with self.assertRaises(ValueError):
                validate_policy({**policy, **change}, publisher=CDC)


if __name__ == "__main__":
    unittest.main()
