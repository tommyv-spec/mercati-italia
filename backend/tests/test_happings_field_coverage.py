"""Source/parser/catalog denominators for real scoped Happings formats."""
from __future__ import annotations

import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from happings_field_coverage import (FIELDS, aggregate_coverage, detail_page_coverage,
                                     weekly_page_coverage)
from happings_source_enrichment import preview as weekly_preview, summarize
from happings_detail_enrichment import preview as detail_preview
from happings_detail_layout import parse_detail
from happings_weekly_layout import parse, compare_saved_markets, VENICE_OLD, VENICE_NEW
from source_format_audit import inventory

TODAY = date(2026, 10, 20)
FIXTURES = Path(__file__).parent / "fixtures"
PISA = "https://www.happings.com/it/happing/mercato-coperto-campagna-amica-di-pisa/"


def listing(*places, suffix=" (la mattina)"):
    text = ('<!doctype html><html><head><title>Mercati settimanali a Venezia</title>'
            '<meta name="fixture" content="scoped provincial source example"></head><body>'
            '<div class="happings-seo-content"><h2>Mercati settimanali nei comuni in provincia di Venezia</h2>'
            '<h3>Mercati del mercoledì nei comuni di Venezia</h3><ul>'
            + ''.join('<li>a Spinea, in ' + place + suffix + '</li>' for place in places)
            + '</ul></div></body></html>')
    return text.encode()


def weekly_row(slug="saved", address="", **changes):
    return {"slug": slug, "nome": "Mercato settimanale di Spinea", "citta": "Spinea",
            "provincia": "VE", "regione": "Veneto", "indirizzo": address,
            "fonte": "happings.com", "url_fonte": VENICE_OLD,
            "ricorrenza_testo": "settimanale - mercoledì", "orario_testo": "",
            "date": ["2026-10-21"], "date_quality": "prevista", "verificato_il": "",
            "aggiornato_il": "2026-06-05", "status": "non_confermato",
            "position_quality": "non_verificata", "lat": 45.49, "lng": 12.15,
            "fonti": [], **changes}


def detail_row(**changes):
    return {**weekly_row("saved-pisa", "VIA del Chiassatello, 64/65"),
            "nome": "Mercato coperto Campagna Amica di Pisa", "citta": "Pisa", "provincia": "PI",
            "regione": "Toscana", "url_fonte": PISA, "ricorrenza_testo": "settimanale - sabato",
            "date": ["2027-01-02"], "lat": None, "lng": None,
            "position_quality": "sconosciuta", **changes}


def detail_page(name="pisa"):
    manifest = json.loads((FIXTURES / "happings_detail/manifest.json").read_text())
    source = next(item["capture"] for item in manifest["samples"] if item["name"] == name)
    return {"requested_url": source["requested_url"], "final_url": source["final_url"],
            "html": (FIXTURES / "happings_detail" / (name + ".html")).read_bytes(),
            "fetched_at": TODAY.isoformat() + "T12:00:00+00:00"}


class HappingsFieldCoverageTests(unittest.TestCase):
    def weekly(self, html=None, rows=None, apply=True):
        before = rows or [weekly_row()]
        page = {"requested_url": VENICE_OLD, "final_url": VENICE_NEW,
                "html": html or listing("Via Roma")}
        after, report = weekly_preview(before, [page], today=TODAY, apply=apply, rights_verified=apply)
        return before, after, report

    def field(self, report, field):
        return report["field_coverage"]["fields"][field]

    def assert_partitions(self, coverage):
        for field in coverage["fields"].values():
            self.assertEqual(field["source_units_denominator"], coverage["source_units"])
            for key in ("source_presence", "reader", "disposition"):
                self.assertEqual(sum(field[key].values()), coverage["source_units"])

    def test_centro_is_vague_source_and_zero_recoverable_precise_addresses(self):
        before, after, report = self.weekly(listing("centro"))
        field = self.field(report, "indirizzo")
        self.assertEqual(after, before)
        self.assertEqual(field["source_presence"]["qualitative"], 1)
        self.assertEqual(field["source_presence"]["precise"], 0)
        self.assertEqual(field["disposition"]["source_qualitative"], 1)
        self.assertEqual(field["linked_precise_source_units"], 0)
        self.assertEqual(field["catalog_values_applied"], 0)

    def test_la_mattina_is_retained_daypart_never_a_clock_gap_or_new_hours(self):
        _, after, report = self.weekly()
        field = self.field(report, "orario_testo")
        self.assertEqual(after[0]["orario_testo"], "")
        self.assertEqual(field["source_presence"]["qualitative"], 1)
        self.assertEqual(field["reader"]["parsed"], 1)
        self.assertEqual(field["disposition"]["source_present_parser_missing"], 0)
        self.assertEqual(field["catalog_values_applied"], 0)

    def test_absence_comes_from_the_source_block_not_nonempty_catalog(self):
        _, after, report = self.weekly(listing("Via Roma", suffix=""),
                                     [weekly_row(orario_testo="09:00–12:00")])
        self.assertEqual(after[0]["orario_testo"], "09:00–12:00")
        self.assertEqual(self.field(report, "orario_testo")["disposition"]["source_absent"], 1)
        comparison = compare_saved_markets(after, listing("Via Roma", suffix=""), source_url=VENICE_NEW, today=TODAY)
        self.assertEqual(comparison["publisher_time_granularity"], "not_indicated")

    def test_precise_weekly_hours_not_read_are_a_parser_gap_not_source_absence(self):
        html = listing("Via Roma (08:00–13:00)", suffix="")
        before, after, report = self.weekly(html)
        field = self.field(report, "orario_testo")
        self.assertEqual(after, before)
        self.assertEqual(field["source_presence"]["precise"], 1)
        self.assertEqual(field["disposition"]["source_present_parser_missing"], 1)
        self.assertEqual(field["disposition"]["source_absent"], 0)
        offline = compare_saved_markets(before, html, source_url=VENICE_NEW, today=TODAY)
        self.assertEqual(offline["publisher_time_granularity"], "clock_information_present_reader_gap")

    def test_seasonal_precise_street_is_held_not_called_vague_or_parser_loss(self):
        _, after, report = self.weekly(listing("Via Roma (estivo)"))
        field = self.field(report, "indirizzo")
        self.assertEqual(field["source_presence"]["precise"], 1)
        self.assertEqual(field["reader"]["parsed"], 1)
        self.assertEqual(field["disposition"]["source_present_parsed_held"], 1)
        self.assertEqual(after[0]["indirizzo"], "")

    def test_source_row_and_duplicate_catalog_assignments_have_separate_denominators(self):
        _, _, report = self.weekly(rows=[weekly_row("one"), weekly_row("two")])
        coverage = report["field_coverage"]
        field = self.field(report, "indirizzo")
        self.assertEqual((coverage["source_units"], coverage["catalog_page_pairs_considered"],
                          coverage["catalog_page_pairs_linked"]), (1, 2, 2))
        self.assertEqual(field["disposition"]["source_present_parsed_applied"], 1)
        self.assertEqual(field["catalog_values_applied"], 2)
        self.assert_partitions(coverage)

    def test_one_protected_duplicate_does_not_hide_another_actual_assignment(self):
        _, _, report = self.weekly(rows=[weekly_row("one"), weekly_row("protected", verificato_il="2026-10-19")])
        field = self.field(report, "indirizzo")
        self.assertEqual(field["catalog_values_applied"], 1)
        self.assertEqual(field["disposition"]["source_present_parsed_applied"], 1)
        self.assertEqual(report["field_coverage"]["catalog_page_pairs_linked"], 1)

    def test_preview_and_identical_reread_do_not_count_as_new_applied_values(self):
        before, after, report = self.weekly(apply=False)
        self.assertEqual(before, after)
        self.assertEqual(self.field(report, "indirizzo")["disposition"]["source_present_parsed_available"], 1)
        _, after, _ = self.weekly()
        _, again, repeated = self.weekly(rows=after)
        self.assertEqual(again, after)
        field = self.field(repeated, "indirizzo")
        self.assertEqual(field["catalog_values_applied"], 0)
        self.assertEqual(field["catalog_values_supported"], 1)
        self.assertEqual(summarize(repeated)["field_coverage"], repeated["field_coverage"])

    def test_two_source_venues_remain_parsed_but_identity_unresolved(self):
        _, _, report = self.weekly(listing("Via Roma", "Piazza Fermi"))
        field = self.field(report, "indirizzo")
        self.assertEqual(field["source_presence"]["precise"], 2)
        self.assertEqual(field["disposition"]["source_present_parsed_identity_unresolved"], 2)
        self.assertEqual(report["field_coverage"]["catalog_page_pairs_considered"], 1)
        self.assertEqual(report["field_coverage"]["catalog_page_pairs_linked"], 0)

    def test_one_venue_observation_cannot_support_another_row_on_the_same_day(self):
        before, after, report = self.weekly()
        html = listing("Via Roma", "Piazza Fermi")
        parser = parse(html, source_url=VENICE_NEW, observed_on=TODAY)
        observations = copy.deepcopy(report["observations"])
        import hashlib
        for item in observations:
            item["source_html_sha256"] = hashlib.sha256(html).hexdigest()
        coverage = weekly_page_coverage(html, parser, requested_url=VENICE_OLD,
            final_url=VENICE_NEW, observations=observations, considered_ids=["saved"],
            before={row["slug"]: row for row in before}, after={row["slug"]: row for row in after})
        for field in ("indirizzo", "ricorrenza_testo"):
            self.assertEqual(coverage["fields"][field]["linked_precise_source_units"], 1)
            self.assertEqual(coverage["fields"][field]["disposition"]["source_present_parsed_identity_unresolved"], 1)
        self.assertEqual(coverage["fields"]["indirizzo"]["catalog_values_applied"], 1)

    def test_conflicting_saved_street_is_reported_as_held_not_missing(self):
        before, after, report = self.weekly(rows=[weekly_row(address="Piazza Fermi")])
        self.assertEqual(before, after)
        self.assertEqual(self.field(report, "indirizzo")["disposition"]["source_present_parsed_held"], 1)

    def test_changed_layout_is_unassessed_never_source_absence(self):
        html = listing("Via Roma").replace(b"happings-seo-content", b"new-unknown-layout")
        _, _, report = self.weekly(html)
        coverage = report["field_coverage"]
        self.assertEqual((coverage["pages_unassessed"], coverage["source_units"]), (1, 0))
        self.assertEqual(self.field(report, "indirizzo")["disposition"]["source_absent"], 0)

    def test_known_source_unit_omitted_by_parser_remains_visible_in_diagnostics(self):
        html = listing("Via Roma", "Piazza Fermi")
        parser = parse(html, source_url=VENICE_NEW, observed_on=TODAY)
        parser.rows.pop()
        coverage = weekly_page_coverage(html, parser, requested_url=VENICE_OLD, final_url=VENICE_NEW)
        self.assertEqual(coverage["source_units"], 2)
        self.assertEqual(coverage["fields"]["indirizzo"]["source_presence"]["precise"], 2)
        self.assertEqual(coverage["fields"]["indirizzo"]["disposition"]["source_present_parser_missing"], 1)

    def test_real_pisa_detail_hours_are_parsed_and_applied_not_an_unsupported_layout(self):
        before = [detail_row()]
        after, report = detail_preview(before, [detail_page()], today=TODAY, apply=True)
        field = self.field(report, "orario_testo")
        self.assertEqual(after[0]["orario_testo"], "7:30 - 12:30")
        self.assertEqual(field["source_presence"]["precise"], 1)
        self.assertEqual(field["reader"]["parsed"], 1)
        self.assertEqual(field["disposition"]["source_present_parsed_applied"], 1)
        self.assertEqual(field["catalog_values_applied"], 1)
        self.assert_partitions(report["field_coverage"])

    def test_new_venue_candidate_is_not_counted_as_an_existing_catalog_record(self):
        after, report = detail_preview([], [detail_page()], today=TODAY)
        coverage = report["field_coverage"]
        self.assertEqual(after, [])
        self.assertEqual(coverage["catalog_page_pairs_considered"], 0)
        self.assertEqual(coverage["catalog_page_pairs_linked"], 0)
        self.assertEqual(coverage["new_venue_candidates_not_catalog_records"], 1)

    def test_real_detail_hours_lost_by_a_reader_are_present_but_missing_not_absent(self):
        page = detail_page()
        document = parse_detail(page["html"], requested_url=PISA, final_url=PISA)
        document["event"].update(hours_text=None, hours_intervals=[])
        coverage = detail_page_coverage(page["html"], document, {"status": "held", "reason": "no_match"})
        field = coverage["fields"]["orario_testo"]
        self.assertEqual(field["source_presence"]["precise"], 1)
        self.assertEqual(field["disposition"]["source_present_parser_missing"], 1)
        self.assertEqual(field["disposition"]["source_absent"], 0)

    def test_unrelated_date_conflict_does_not_hide_a_missing_hours_reader(self):
        page = detail_page()
        document = parse_detail(page["html"], requested_url=PISA, final_url=PISA)
        document["event"].update(hours_text=None, hours_intervals=[])
        document["conflicts"] = [{"field": "edition_interval", "code": "test_date_conflict"}]
        coverage = detail_page_coverage(page["html"], document, {"status": "held"})
        self.assertEqual(coverage["fields"]["orario_testo"]["disposition"]["source_present_parser_missing"], 1)
        self.assertEqual(coverage["fields"]["orario_testo"]["disposition"]["source_present_parser_held_conflict"], 0)

    def test_real_detail_explicit_date_loss_is_partial_not_source_absence(self):
        page = detail_page()
        document = parse_detail(page["html"], requested_url=PISA, final_url=PISA)
        del document["event"]["occurrences"][4]
        coverage = detail_page_coverage(page["html"], document, {"status": "held"})
        field = coverage["fields"]["date"]
        self.assertEqual(field["source_presence"]["precise"], 1)
        self.assertEqual(field["disposition"]["source_present_parser_partial"], 1)

    def test_real_lucca_interval_boundary_hours_are_present_and_keep_scope(self):
        _, report = detail_preview([], [detail_page("lucca_antiquario")], today=TODAY)
        field = self.field(report, "orario_testo")
        self.assertEqual(field["source_presence"]["precise"], 1)
        self.assertEqual(field["reader"]["parsed"], 1)
        self.assertEqual(report["field_coverage"]["pages"][0]["parsed_hours_scope"], "interval_boundaries")

    def test_real_parcines_contradictory_hours_are_held_not_an_unreported_parser_loss(self):
        _, report = detail_preview([], [detail_page("natale_parcines")], today=TODAY)
        field = self.field(report, "orario_testo")
        self.assertEqual(field["source_presence"]["precise"], 1)
        self.assertEqual(field["disposition"]["source_present_parsed_held"], 1)
        self.assertEqual(field["catalog_values_applied"], 0)

    def test_date_specific_clock_information_is_not_absent_or_a_missing_general_hour(self):
        html = ('<!doctype html><html><head></head><body><div class="happings-event-hero">'
                '<h1>Mercato di Pisa</h1></div><main class="happings-event-content">'
                '<section class="happings-event-performances"><ul>'
                '<li>24 Ottobre 2026 · 07:30 - 12:30</li></ul></section>'
                '</main><aside class="happings-event-sidebar"></aside></body></html>').encode()
        document = parse_detail(html, requested_url=PISA, final_url=PISA)
        self.assertIsNone(document["event"]["hours_text"])
        coverage = detail_page_coverage(html, document, {"status": "held"})
        field = coverage["fields"]["orario_testo"]
        self.assertEqual(field["source_presence"]["precise"], 1)
        self.assertEqual(field["reader"]["parsed"], 1)
        self.assertEqual(field["disposition"]["source_present_parser_missing"], 0)

    def test_parsed_detail_with_competing_saved_identities_remains_unlinked(self):
        before = [detail_row(slug="one"), detail_row(slug="two")]
        after, report = detail_preview(before, [detail_page()], today=TODAY, apply=True)
        self.assertEqual(before, after)
        self.assertEqual(self.field(report, "orario_testo")["disposition"]["source_present_parsed_identity_unresolved"], 1)

    def test_retained_detail_fact_does_not_claim_overwrite_of_unowned_hours(self):
        before = [detail_row(orario_testo="09:00–13:00")]
        after, report = detail_preview(before, [detail_page()], today=TODAY, apply=True)
        self.assertEqual(after[0]["orario_testo"], "09:00–13:00")
        field = self.field(report, "orario_testo")
        self.assertEqual(field["catalog_values_applied"], 0)
        self.assertEqual(field["disposition"]["source_present_parsed_retained_as_detail"], 1)

    def test_publication_date_footer_and_related_cards_do_not_supply_market_fields(self):
        html = ('<!doctype html><html><head><script type="application/ld+json">'
                '{"@type":"WebPage","url":"' + PISA + '","datePublished":"2026-10-01"}'
                '</script></head><body><div class="happings-event-hero"><h1>Mercato di Pisa</h1></div>'
                '<main class="happings-event-content"><div class="happings-related-events">'
                '<div class="happings-event-info-item"><strong>Orario</strong><p>08:00–14:00</p></div>'
                '<section class="happings-event-performances"><li>24 Ottobre 2026</li></section></div></main>'
                '<aside class="happings-event-sidebar"></aside><footer>'
                '<div class="happings-event-info-item"><strong>Orario</strong><p>07:00–19:00</p></div>'
                '<script type="application/ld+json">{"@type":"Event","name":"Mercato di Pisa",'
                '"url":"' + PISA + '","startDate":"2026-10-24"}</script></footer></body></html>').encode()
        document = parse_detail(html, requested_url=PISA, final_url=PISA)
        coverage = detail_page_coverage(html, document, {"status": "held"})
        for field in ("orario_testo", "date"):
            self.assertEqual(coverage["fields"][field]["disposition"]["source_absent"], 1)

    def test_decimal_price_is_not_an_exact_opening_time(self):
        html = ('<!doctype html><html><body><div class="happings-event-hero"><h1>Mercato di Pisa</h1></div>'
                '<main class="happings-event-content"><div class="happings-event-description-card">'
                '<p>Ingresso 12.30 euro. Orari non indicati.</p></div></main>'
                '<aside class="happings-event-sidebar"></aside></body></html>').encode()
        document = parse_detail(html, requested_url=PISA, final_url=PISA)
        coverage = detail_page_coverage(html, document, {"status": "held"})
        self.assertEqual(coverage["fields"]["orario_testo"]["disposition"]["source_absent"], 1)

    def test_real_trieste_keeps_52_physical_rows_not_seven_day_markets(self):
        html = (FIXTURES / "happings_weekly/trieste_52_rows.html").read_bytes()
        url = "https://www.happings.com/it/mercati-settimanali-a-trieste-e-provincia/"
        parser = parse(html, source_url=url, observed_on=TODAY)
        coverage = aggregate_coverage([weekly_page_coverage(html, parser, requested_url=url, final_url=url)])
        self.assertEqual(coverage["source_units"], 52)
        self.assertEqual(coverage["fields"]["indirizzo"]["source_presence"]["precise"], 52)
        self.assertEqual(coverage["fields"]["orario_testo"]["source_presence"]["qualitative"], 52)
        self.assert_partitions(coverage)

    def test_report_has_no_field_values_and_never_modifies_inputs(self):
        page, row = detail_page(), detail_row()
        original = copy.deepcopy((page, row))
        _, report = detail_preview([row], [page], today=TODAY)
        self.assertEqual((page, row), original)
        encoded = json.dumps(report["field_coverage"], ensure_ascii=False)
        self.assertNotIn("Chiassatello", encoded)
        self.assertNotIn("12:30", encoded)
        self.assertNotIn("<", encoded)
        self.assertEqual(report["field_coverage"]["market_openings_verified"], 0)

    def test_catalog_inventory_emptiness_has_no_source_absence_claim(self):
        report = inventory([weekly_row()])
        self.assertEqual(report["formats"][0]["empty_fields_basis"], "catalog_storage_only_not_source_absence")
        self.assertEqual(report["formats"][0]["empty_fields"]["orario_testo"], 1)

    def test_empty_batch_has_explicit_zero_denominators(self):
        coverage = aggregate_coverage([])
        self.assertEqual((coverage["pages_supplied"], coverage["source_units"]), (0, 0))
        self.assert_partitions(coverage)


if __name__ == "__main__":
    unittest.main()
