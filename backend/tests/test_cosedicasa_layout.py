import hashlib
import json
import re
import unittest
from datetime import date
from pathlib import Path

from cosedicasa_layout import MAX_BYTES, parse_detail, source_url


FIXTURES = Path(__file__).parent / "fixtures" / "cosedicasa_detail"
MANIFEST = json.loads((FIXTURES / "manifest.json").read_text())
SAMPLES = {item["sample"]: item for item in MANIFEST["samples"]}


def html(name):
    return (FIXTURES / SAMPLES[name]["fixture_file"]).read_text()


def parse(name, markup=None, **kwargs):
    sample = SAMPLES[name]
    return parse_detail(markup if markup is not None else html(name),
                        requested_url=sample["requested_url"],
                        final_url=kwargs.get("final_url", sample["final_url"]))


def alter_schema(markup, change):
    match = re.search(r'(<script type="application/ld\+json">)(.*?)(</script>)', markup, re.S)
    value = json.loads(match[2])
    change(value)
    return markup[:match.start(2)] + json.dumps(value, ensure_ascii=False) + markup[match.end(2):]


def remove_row(markup, suffix):
    return re.sub(r'<div class="mercatini-mostre-row mercatini-mostre-' + suffix + r'">.*?</div>',
                  "", markup, flags=re.S)


class CoseDiCasaLayoutTests(unittest.TestCase):
    def test_five_semantic_fixtures_preserve_facts_verified_on_complete_captures(self):
        for name, sample in SAMPLES.items():
            with self.subTest(name=name):
                content = html(name)
                self.assertEqual(hashlib.sha256(content.encode()).hexdigest(), sample["fixture_sha256"])
                parsed = parse(name, content)
                expected, event = sample["expected"], parsed["event"]
                self.assertEqual(parsed["status"], expected["status"])
                for key in ("location", "hours_text", "hours_intervals", "edition_intervals",
                            "calendar_scope", "calendar_complete", "calendar_rules", "suspensions"):
                    self.assertEqual(event[key], expected[key], key)
                self.assertEqual([v["date"] for v in event["occurrences"]], expected["occurrences"])
                self.assertEqual(sorted({v["code"] for v in parsed["conflicts"]}), expected["conflict_codes"])
                self.assertEqual(parsed["source"]["modified_at"], expected["modified_at"])
                self.assertEqual(parsed["source"]["html_sha256"], hashlib.sha256(content.encode()).hexdigest())
                self.assertNotIn("read_on", parsed["source"])
                self.assertNotIn("fetched_at", parsed["source"])
                self.assertTrue(parsed["field_evidence"]["location.address"])
                self.assertTrue(parsed["field_evidence"]["hours_text"])

    def test_bologna_keeps_sunday_anchor_preceding_saturday_and_summer_exclusion(self):
        parsed = parse("bologna")
        rule = parsed["event"]["calendar_rules"][0]
        self.assertEqual((rule["ordinal"], rule["weekday"], rule["relative_day_offsets"]), (2, 6, [-1, 0]))
        self.assertEqual(rule["excluded_months"], [7, 8])
        self.assertEqual(parsed["event"]["edition_intervals"], [{"start": "2026-11-07", "end": "2026-11-08"}])
        self.assertIn("ordinal_saturday_differs_preceding_saturday", {c["code"] for c in parsed["conflicts"]})
        self.assertFalse(parsed["event"]["calendar_complete"])
        self.assertEqual(parsed["event"]["occurrences"], [])

    def test_schema_date_stamped_with_the_read_day_is_not_a_calendar_conflict(self):
        sample = SAMPLES["todi"]
        read = lambda day: parse_detail(html("todi"), requested_url=sample["requested_url"],
                                        final_url=sample["final_url"], read_on=day)
        for day in (date(2026, 10, 20), date(2026, 10, 21), date(2026, 10, 22)):  # a cached copy too
            parsed = read(day)
            self.assertEqual(parsed["status"], "parsed")
            self.assertEqual(parsed["conflicts"], [])
            self.assertIn("schema_date_is_read_day", parsed["warnings"])
            self.assertEqual([o["date"] for o in parsed["event"]["occurrences"]], ["2027-03-21"])
        codes = {c["code"] for c in read(date(2026, 11, 5))["conflicts"]}
        self.assertIn("schema_dates_not_visible_calendar", codes)
        bologna = parse_detail(html("bologna"), requested_url=SAMPLES["bologna"]["requested_url"],
                               read_on=date(2026, 10, 20))
        self.assertEqual({c["code"] for c in bologna["conflicts"]}, {"ordinal_saturday_differs_preceding_saturday"})

    def test_next_date_row_is_not_a_suspension_despite_shared_css_class(self):
        event = parse("bologna")["event"]
        self.assertEqual(len(event["suspensions"]), 1)
        self.assertEqual(event["suspensions"][0]["start"]["month"], 7)
        self.assertEqual(event["suspensions"][0]["end"]["month"], 8)
        self.assertTrue(any(row["field"] == "next_dates" for row in event["source_rows"]))
        self.assertEqual(event["date_intervals"][0]["start"], "2026-11-07")

    def test_venezia_retains_five_edition_ranges_and_holds_suspension_conflict(self):
        parsed = parse("venezia")
        self.assertEqual(len(parsed["event"]["date_intervals"]), 5)
        self.assertEqual(parsed["event"]["date_intervals"][0]["end"], "2026-05-10")
        self.assertEqual(parsed["event"]["date_intervals"][-1]["start"], "2026-12-04")
        self.assertEqual(parsed["event"]["occurrences"], [])
        self.assertFalse(parsed["event"]["calendar_complete"])
        self.assertTrue(all(v["continuous_opening_confirmed"] is False for v in parsed["event"]["date_intervals"]))
        self.assertIn("listed_date_during_suspension", {v["code"] for v in parsed["conflicts"]})

    def test_todi_preserves_sunset_and_does_not_invent_extra_edition_year(self):
        parsed = parse("todi")
        event = parsed["event"]
        self.assertEqual(event["hours_text"], "09:00–tramonto")
        self.assertEqual(event["hours_intervals"], [{"start": "09:00", "end": None}])
        self.assertEqual(event["calendar_rules"][0]["included_months"], list(range(3, 11)))
        self.assertEqual([v["date"] for v in event["occurrences"]], ["2027-03-21"])
        self.assertIn("extra_edition_year_unknown", parsed["warnings"])
        self.assertTrue(any(v["kind"] == "extra_edition_claim" for v in event["scope_statements"]))
        self.assertNotIn("2026-11-11", json.dumps(event))
        self.assertNotIn("2027-11-11", json.dumps(event))

    def test_selected_fridays_are_not_expanded_or_replaced_by_auxiliary_hours(self):
        parsed = parse("cernobbio")
        dates = [v["date"] for v in parsed["event"]["occurrences"]]
        self.assertEqual(len(dates), 14)
        self.assertNotIn("2026-06-19", dates)
        self.assertNotIn("2026-09-04", dates)
        self.assertEqual(parsed["event"]["hours_text"], "08:00–19:00")
        self.assertIn("auxiliary_activity_hours_not_market_hours", parsed["warnings"])
        self.assertEqual(parsed["event"]["calendar_rules"][0]["kind"], "selected_dates_only")
        self.assertTrue(parsed["event"]["calendar_complete"])

    def test_fiumicino_keeps_midnight_conflicting_bounds_and_conditional_weather(self):
        parsed = parse("fiumicino")
        event = parsed["event"]
        self.assertEqual(event["hours_text"], "18:00–24:00")
        self.assertEqual(event["hours_intervals"][0]["end"], "24:00")
        self.assertEqual(event["edition_intervals"], [{"start": "2026-06-02", "end": "2026-08-10"}])
        self.assertEqual(event["occurrences"], [])
        self.assertFalse(event["calendar_complete"])
        self.assertEqual(event["conditions"][0]["kind"], "weather_condition")
        self.assertEqual(event["date_intervals"][0]["status"], "source_listed")
        self.assertIn("description_visible_edition_bounds_disagree", {c["code"] for c in parsed["conflicts"]})

    def test_canonical_is_not_transport_proof_and_requested_url_is_preserved(self):
        unknown = parse("cernobbio", final_url=None)
        observed = parse("cernobbio")
        self.assertIsNone(unknown["source"]["final_url"])
        self.assertEqual(unknown["source"]["canonical_url"], SAMPLES["cernobbio"]["final_url"])
        self.assertIn("canonical_change_without_transport_evidence", unknown["warnings"])
        self.assertEqual(observed["source"]["requested_url"], SAMPLES["cernobbio"]["requested_url"])
        self.assertEqual(observed["source"]["final_url"], SAMPLES["cernobbio"]["final_url"])
        self.assertNotEqual(observed["source"]["requested_url"], observed["source"]["final_url"])

    def test_wrong_canonical_and_primary_event_name_are_identity_holds(self):
        markup = html("bologna").replace('<link rel="canonical" href="', '<link rel="canonical" href="https://wrong.example/?u=')
        parsed = parse("bologna", markup)
        self.assertEqual(parsed["status"], "held")
        self.assertTrue(any(c["field"] == "identity" for c in parsed["conflicts"]))
        changed = alter_schema(html("bologna"), lambda s: s.update(name="Evento diverso"))
        parsed = parse("bologna", changed)
        self.assertIn("schema_event_name_differs_primary", {c["code"] for c in parsed["conflicts"]})

    def test_description_related_events_and_footer_cannot_supply_missing_address(self):
        markup = remove_row(html("bologna"), "address")
        markup = alter_schema(markup, lambda s: s["location"]["address"].pop("streetAddress"))
        markup = markup.replace("Il mercato si tiene", "Iscrizioni presso Via Inventata 42. Il mercato si tiene")
        markup = markup.replace('</div></div><footer>', '</div><aside><h1>Altro evento</h1><div class="mercatini-mostre-address">Luogo: Via Sbagliata 10</div></aside></div><footer>')
        parsed = parse("bologna", markup)
        self.assertIsNone(parsed["event"]["location"]["address"])
        self.assertEqual(parsed["event"]["location"]["city"], "Bologna")
        self.assertEqual(parsed["event"]["hours_text"], "08:30–18:00")
        self.assertNotIn("Via Inventata", json.dumps(parsed["event"]["source_rows"]))

    def test_foreign_event_jsonld_cannot_fill_missing_address(self):
        markup = remove_row(html("bologna"), "address")
        markup = alter_schema(markup, lambda s: s.update(url="https://www.cosedicasa.com/mercatini/altro-evento"))
        parsed = parse("bologna", markup)
        self.assertIsNone(parsed["event"]["location"]["address"])
        self.assertIn("matching_event_schema_absent", parsed["warnings"])

    def test_structured_address_disagreement_holds_address_and_keeps_independent_hours(self):
        markup = alter_schema(html("bologna"), lambda s: s["location"]["address"].update(streetAddress="Via Diversa 1"))
        parsed = parse("bologna", markup)
        self.assertIsNone(parsed["event"]["location"]["address"])
        self.assertTrue(any(c["field"] == "address" and c["path"] == "location.address" for c in parsed["conflicts"]))
        self.assertEqual(parsed["event"]["hours_text"], "08:30–18:00")

    def test_city_disagreement_is_identity_conflict(self):
        markup = alter_schema(html("bologna"), lambda s: s["location"]["address"].update(addressLocality="Modena (Modena)"))
        parsed = parse("bologna", markup)
        self.assertIsNone(parsed["event"]["location"]["city"])
        self.assertTrue(any(c["field"] == "identity" and c.get("path") == "location.city" for c in parsed["conflicts"]))

    def test_visible_datetime_disagreement_is_not_silently_selected(self):
        markup = html("cernobbio").replace('datetime="2026-06-05"', 'datetime="2026-06-06"', 1)
        parsed = parse("cernobbio", markup)
        self.assertFalse(parsed["event"]["calendar_complete"])
        self.assertIn("visible_date_datetime_disagree_or_invalid", {c["code"] for c in parsed["conflicts"]})
        self.assertNotIn("2026-06-06", [v["date"] for v in parsed["event"]["occurrences"]])
        self.assertEqual(parsed["event"]["hours_text"], "08:00–19:00")

    def test_editorial_modified_timestamp_never_becomes_occurrence_or_read_date(self):
        parsed = parse("cernobbio")
        self.assertEqual(parsed["source"]["modified_at"], "2026-07-03T14:02:51+00:00")
        markup = re.sub(r'<meta property="article:modified_time"[^>]+>', '', html("cernobbio"))
        unknown = parse("cernobbio", markup)
        self.assertIsNone(unknown["source"]["modified_at"])
        self.assertIsNone(unknown["source"]["published_at"])
        self.assertEqual(unknown["event"]["occurrences"], parsed["event"]["occurrences"])

    def test_schema_today_date_does_not_create_a_current_opening(self):
        original = parse("bologna")
        changed = parse("bologna", alter_schema(html("bologna"), lambda s: s.update(startDate="2027-01-05", endDate="2027-01-05")))
        self.assertEqual(changed["event"]["edition_intervals"], original["event"]["edition_intervals"])
        self.assertEqual(changed["event"]["occurrences"], [])
        self.assertFalse(changed["event"]["calendar_complete"])
        self.assertEqual(changed["source"]["modified_at"], original["source"]["modified_at"])

    def test_cancellation_is_limited_to_matching_schema_occurrence(self):
        markup = alter_schema(html("cernobbio"), lambda s: s.update(eventStatus="https://schema.org/EventCancelled"))
        parsed = parse("cernobbio", markup)
        statuses = {v["date"]: v["status"] for v in parsed["event"]["occurrences"]}
        self.assertEqual(statuses["2026-09-25"], "cancelled")
        self.assertEqual(sum(value == "cancelled" for value in statuses.values()), 1)
        self.assertEqual(sum(value == "source_listed" for value in statuses.values()), 13)
        self.assertTrue(parsed["event"]["calendar_complete"])

    def test_even_agreed_daily_edition_bounds_are_not_enumerated_as_openings(self):
        markup = html("fiumicino").replace("dal 10 giugno al 2 agosto", "dal 2 giugno al 10 agosto")
        parsed = parse("fiumicino", markup)
        self.assertTrue(parsed["event"]["calendar_complete"])
        self.assertEqual(parsed["event"]["calendar_scope"], "edition_bounds")
        self.assertEqual(parsed["event"]["occurrences"], [])
        self.assertEqual(len(parsed["event"]["date_intervals"]), 1)

    def test_unqualified_extra_date_keeps_calendar_incomplete_even_if_schema_agrees(self):
        markup = alter_schema(html("todi"), lambda s: s.update(startDate="2027-03-21", endDate="2027-03-21"))
        parsed = parse("todi", markup)
        self.assertEqual(parsed["conflicts"], [])
        self.assertFalse(parsed["event"]["calendar_complete"])
        self.assertIn("extra_edition_year_unknown", parsed["warnings"])

    def test_broken_jsonld_is_held_for_calendar_without_losing_visible_hours(self):
        markup = html("cernobbio").replace('"@context":', 'invalid-token "@context":', 1)
        parsed = parse("cernobbio", markup)
        self.assertIn("invalid_json_ld", parsed["warnings"])
        self.assertFalse(parsed["event"]["calendar_complete"])
        self.assertEqual(parsed["event"]["hours_text"], "08:00–19:00")

    def test_jsonld_type_array_is_accepted_for_the_same_event(self):
        markup = alter_schema(html("cernobbio"), lambda s: s.update({"@type": ["Event", "Festival"]}))
        parsed = parse("cernobbio", markup)
        self.assertNotIn("matching_event_schema_absent", parsed["warnings"])
        self.assertTrue(parsed["event"]["calendar_complete"])

    def test_invalid_minutes_are_not_reinterpreted_as_an_integer_hour(self):
        markup = html("bologna").replace("8,30", "8,99")
        parsed = parse("bologna", markup)
        self.assertIsNone(parsed["event"]["hours_text"])
        self.assertIn("invalid_market_clock_interval", parsed["warnings"])

    def test_multiple_hour_claims_are_held_without_picking_the_first(self):
        markup = html("bologna").replace("Dalle ore 8,30 alle 18.", "Dalle ore 8,30 alle 18. Dalle ore 10 alle 15.")
        parsed = parse("bologna", markup)
        self.assertIsNone(parsed["event"]["hours_text"])
        self.assertIn("multiple_market_hour_claims_require_scope", {c["code"] for c in parsed["conflicts"]})

    def test_hour_qualification_survives_the_public_hours_value(self):
        markup = html("bologna").replace("Dalle ore 8,30 alle 18.", "Dalle ore 8,30 alle 18 solo il sabato.")
        parsed = parse("bologna", markup)
        self.assertIn("08:30–18:00", parsed["event"]["hours_text"])
        self.assertIn("solo il sabato", parsed["event"]["hours_text"])
        self.assertTrue(any(v["kind"] == "hours_qualification" for v in parsed["event"]["scope_statements"]))

    def test_next_dates_written_as_two_complete_dates_are_one_range(self):
        from cosedicasa_layout import _explicit_text_dates as read
        self.assertEqual(read("31 ottobre 2026 - 1 novembre 2026"), [("2026-10-31", "2026-11-01")])
        self.assertEqual(read("5-6 ottobre 2026"), [("2026-10-05", "2026-10-06")])
        self.assertEqual(read("1 novembre 2026 - 31 ottobre 2026"), [])
        self.assertEqual(read("31 ottobre - 1 novembre"), [])  # no year: never guessed

    def test_missing_or_duplicate_primary_wrapper_is_unsupported(self):
        for markup in (html("bologna").replace('id="post-content"', 'id="other-content"'),
                       html("bologna") + '<div id="post-content" class="mercatini-mostre-wrapper"></div>'):
            parsed = parse("bologna", markup)
            self.assertEqual(parsed["status"], "unsupported")
            self.assertIsNone(parsed["event"]["name"])
            self.assertFalse(parsed["event"]["calendar_complete"])

    def test_urls_byte_limits_and_invalid_utf8_fail_closed(self):
        for bad in ("http://www.cosedicasa.com/mercatini/bologna", "https://evil.example/mercatini/bologna",
                    SAMPLES["bologna"]["requested_url"] + "?preview=1", "https://www.cosedicasa.com/news/bologna"):
            self.assertIsNone(source_url(bad))
            with self.assertRaises(ValueError):
                parse_detail(html("bologna"), requested_url=bad)
        for bad in (b"", b"x" * (MAX_BYTES + 1), b"\xff\xfe"):
            with self.assertRaises(ValueError):
                parse_detail(bad, requested_url=SAMPLES["bologna"]["requested_url"])

    def test_output_uses_only_json_facts_and_does_not_retain_full_description(self):
        for name in SAMPLES:
            parsed = parse(name)
            self.assertEqual(json.loads(json.dumps(parsed)), parsed)
            self.assertNotIn("description", parsed["event"])
            self.assertNotIn("html", parsed)
            self.assertNotIn("source_body", parsed)
            self.assertNotIn("Via non pertinente", json.dumps(parsed))


if __name__ == "__main__":
    unittest.main()
