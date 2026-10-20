"""New province local-guide body; explicit scope must survive extraction."""
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
import tempfile
import unittest

from happings_weekly_layout import parse
from happings_source_enrichment import preview, safe_report
from happings_field_coverage import weekly_page_coverage
from test_happings_source_enrichment import row
from happings_weekly_conflicts import verify_source_pages

TODAY = date(2026, 10, 20)
OLD = "https://www.happings.com/it/mercati-settimanali-a-lucca.html"
URL = "https://www.happings.com/it/mercati-settimanali-a-lucca-e-provincia/"
FIXTURE = Path(__file__).parent / "fixtures/happings_editorial_weekly_lucca_excerpt.html"
HTML = FIXTURE.read_bytes()


def market(slug="lucca-wednesday", *, city="Lucca", day="mercoledì", street=""):
    return row(slug, city=city, day=day, street=street, url=OLD, province="LU", region="Toscana")


def feed(raw=HTML):
    return [{"requested_url": OLD, "final_url": URL, "html": raw}]


def change(old, new, raw=HTML):
    assert old in raw.decode()
    return raw.decode().replace(old, new).encode()


class EditorialWeeklyTests(unittest.TestCase):
    def test_real_excerpt_separates_three_current_day_places_and_53_historical_rows(self):
        parsed = parse(HTML, source_url=URL, observed_on=TODAY)
        self.assertEqual(len(parsed.rows), 56)
        current = [r for r in parsed.rows if r["editorial_scope"]["status"] == "current"]
        self.assertEqual([(r["city"], r["weekday"], r["place"]) for r in current], [
            ("Lucca", 2, "Piazzale Don Baroni"), ("Lucca", 5, "Piazzale Don Baroni"),
            ("Ponte a Moriano", 1, "Piazza del Popolo")])
        self.assertTrue(all(r["clock_hours"] == {"start_time": "08:00", "end_time": "13:00"} for r in current))
        historical = [r for r in parsed.rows if r["editorial_scope"]["status"] == "historical_unverified"]
        self.assertEqual(len(historical), 53)
        self.assertTrue(all(r["calendar_scope"]["assignment_allowed"] is False and
                            r["calendar_scope"]["forecast_allowed"] is False for r in historical))
        self.assertTrue(all(r["clock_hours"] is None for r in historical))
        self.assertTrue(all(r["has_specific_location"] is False for r in historical))
        # Replacement prose is retained as evidence, not two active venues.
        self.assertNotIn("Piazza del Carmine", [r["place"] for r in current])

    def test_historical_agreement_never_refreshes_fields_receipts_or_calendar(self):
        base = [market("pietrasanta-monday", city="Pietrasanta", day="lunedì", street="Piazza Oberdan")]
        before = deepcopy(base)
        after, report = preview(base, feed(), today=TODAY, apply=True, rights_verified=True)
        self.assertEqual(after, before)
        self.assertEqual(report["observations"], [])
        self.assertEqual(report["parser_counts"]["publisher_historical_section_held"], 1)
        self.assertEqual(report["parser_counts"]["publisher_editorial_historical_rows"], 53)
        self.assertTrue(safe_report(report, base, source_pages=feed()))

    def test_only_explicit_current_scope_can_fill_missing_address_and_never_hours(self):
        base = [market()]
        after, report = preview(base, feed(), today=TODAY, apply=True, rights_verified=True)
        self.assertEqual(after[0]["indirizzo"], "Piazzale Don Baroni")
        for key in ("orario_testo", "date", "date_quality", "aggiornato_il", "verificato_il", "lat", "lng"):
            self.assertEqual(after[0][key], base[0][key])
        self.assertEqual(report["field_changes"], 1)
        self.assertTrue(safe_report(report, base, source_pages=feed()))

    def test_unmarked_or_unconfirmed_sections_cannot_authorize_current_assignments(self):
        for heading in ("Lucca città: sedi e giorni", "Lucca città: sedi e giorni non aggiornati",
                        "Lucca città: sedi e giorni da verificare", "Lucca città: elenco storico"):
            with self.subTest(heading=heading):
                raw = change("Lucca città: sedi e giorni aggiornati", heading)
                after, report = preview([market()], feed(raw), today=TODAY, apply=True, rights_verified=True)
                self.assertEqual(after, [market()])
                self.assertEqual(report["observations"], [])

    def test_later_disclaimer_qualifies_the_whole_same_section(self):
        raw = change("<p><a", "<p>Le indicazioni non sono state tutte riconfermate.</p><p><a")
        parsed = parse(raw, source_url=URL)
        self.assertTrue(all(r["calendar_scope"] for r in parsed.rows))
        after, report = preview([market()], feed(raw), today=TODAY, apply=True, rights_verified=True)
        self.assertEqual(after, [market()])
        self.assertEqual(report["observations"], [])

    def test_unknown_current_second_market_cannot_make_first_falsely_unique(self):
        for content in ("<p>Un altro mercato il mercoledì presso un luogo da definire.</p>",
                        "<ul><li>Un altro mercato a Lucca si tiene ogni mercoledì in Via Roma.</li></ul>",
                        "<ol><li>Un altro mercato a Lucca si tiene ogni mercoledì in Via Roma.</li></ol>"):
            with self.subTest(content=content):
                raw = change("<p><a", content+"<p><a")
                parsed = parse(raw, source_url=URL)
                self.assertEqual(parsed.editorial_sections[0]["reason"], "current_editorial_section_incomplete")
                after, report = preview([market()], feed(raw), today=TODAY, apply=True, rights_verified=True)
                self.assertEqual(after, [market()])
                self.assertEqual(report["observations"], [])

    def test_explicit_second_current_venue_remains_ambiguous(self):
        raw = change("<p><a", "<p>Il mercato settimanale di Lucca si svolge in Via Roma il mercoledì, dalle 8:00 alle 13:00.</p><p><a")
        after, report = preview([market()], feed(raw), today=TODAY, apply=True, rights_verified=True)
        self.assertEqual(after, [market()])
        self.assertEqual(report["parser_counts"]["no_unique_source_market_city_weekday"], 1)

    def test_current_narrative_with_foreign_heading_city_or_ambiguous_place_is_held(self):
        for old, new in (("Il mercato settimanale di Lucca", "Il mercato settimanale di Camaiore"),
                         ("Piazzale Don Baroni il", "Via Roma a Pisa il"),
                         ("Piazzale Don Baroni il", "Via Roma, Pisa il"),
                         ("Piazzale Don Baroni il", "Via Roma oppure Via Milano il")):
            with self.subTest(new=new):
                raw = change(old, new)
                after, report = preview([market()], feed(raw), today=TODAY, apply=True, rights_verified=True)
                self.assertEqual(after, [market()])
                self.assertEqual(report["observations"], [])

    def test_invalid_equal_reversed_or_partial_clocks_do_not_promote_current_prose(self):
        for text in ("dalle 13:00 alle 8:00", "dalle 8:00 alle 8:00", "dalle 25:00 alle 26:00", "dalle 8:00"):
            with self.subTest(text=text):
                raw = change("dalle 8:00 alle 13:00", text)
                after, report = preview([market()], feed(raw), today=TODAY, apply=True, rights_verified=True)
                self.assertEqual(after, [market()])
                self.assertEqual(report["observations"], [])

    def test_unreviewed_weekday_or_changed_nested_list_quarantines_page(self):
        for old, new in (("Mercati del mercoledì nei comuni", "Mercati del mercoledì sospesi nei comuni"),
                         ("<ul>", "<ol>"),
                         ("a Pietrasanta, in Piazza Oberdan (la mattina)", "<ul><li>a Pietrasanta, in Piazza Oberdan</li></ul>")):
            with self.subTest(new=new):
                with self.assertRaises(ValueError):
                    parse(change(old, new), source_url=URL)

    def test_foreign_province_repeated_body_and_unclosed_body_are_rejected(self):
        for old, new in (("Mercati settimanali a Lucca e provincia", "Mercati settimanali a Pisa e provincia"),
                         ("Mercati del lunedì nei comuni di Lucca", "Mercati del lunedì nei comuni di Pisa"),
                         ('<div class="hpe-editorial-body">', '<div class="hpe-editorial-body"></div><div class="hpe-editorial-body">')):
            with self.subTest(new=new):
                with self.assertRaises(ValueError):
                    parse(change(old, new), source_url=URL)
        with self.assertRaises(ValueError):
            parse(HTML[:HTML.index(b"</ul>")], source_url=URL)

    def test_footer_sidebar_and_unrelated_guide_links_never_supply_market_rows(self):
        false = '<h2>Sedi e giorni aggiornati</h2><p>Il mercato settimanale di Lucca si svolge in Via Inventata il mercoledì, dalle 8:00 alle 13:00.</p>'
        raw = change('<div class="hpe-editorial-grid">', '<div class="hpe-editorial-grid"><aside>'+false+'</aside>')
        raw = raw.replace(b"</body>", ("<footer>"+false+"</footer></body>").encode())
        parsed = parse(raw, source_url=URL)
        self.assertEqual(len(parsed.rows), 56)
        self.assertNotIn("Via Inventata", [r["place"] for r in parsed.rows])
        self.assertEqual(sum(s["source_rows"] for s in parsed.editorial_sections), 56)
        outside = change('<main id="main" class="hpe-editorial-main">', '<footer id="main" class="hpe-editorial-main">')
        with self.assertRaises(ValueError):
            parse(outside, source_url=URL)

    def test_raw_coverage_does_not_claim_absence_when_parser_drops_rows(self):
        parsed = parse(HTML, source_url=URL)
        parsed.rows = []
        report = weekly_page_coverage(HTML, parsed, requested_url=OLD, final_url=URL)
        self.assertEqual(report["source_units"], 56)
        hours = report["fields"]["orario_testo"]
        self.assertEqual(hours["source_presence"]["precise"], 3)
        self.assertEqual(hours["source_presence"]["qualitative"], 53)
        self.assertEqual(hours["disposition"]["source_present_parser_missing"], 3)


class ExplicitAddressConflictTests(unittest.TestCase):
    def base(self):
        return [market(street="Piazza del Carmine"),
                market("lucca-saturday", day="sabato", street="Via dei Bacchettoni")]

    def run_preview(self, base=None, raw=HTML, **kwargs):
        return preview(self.base() if base is None else base, feed(raw), today=kwargs.pop("today", TODAY),
                       apply=kwargs.pop("apply", True), rights_verified=True, **kwargs)

    def test_two_uniquely_bound_explicit_replacements_only_add_negative_evidence(self):
        base = self.base()
        after, report = self.run_preview(base)
        self.assertEqual(report["address_conflict_ids"], sorted(r["slug"] for r in base))
        self.assertEqual(report["field_changes"], 0)
        self.assertEqual(report["record_changes"], 2)
        for old, new in zip(base, after):
            self.assertEqual({k: v for k, v in new.items() if k != "conflitti_campi"}, old)
            self.assertEqual(len(new["conflitti_campi"]), 1)
            proof = new["conflitti_campi"][0]
            self.assertEqual(proof["valore_catalogo"], old["indirizzo"])
            self.assertEqual(proof["valore_fonte"], "Piazzale Don Baroni")
            self.assertEqual(proof["letto_il"], TODAY.isoformat())
            self.assertIn("Queste indicazioni sostituiscono", proof["prova"]["frammento"])
        self.assertEqual(report["observations"], [])
        self.assertTrue(safe_report(report, base, source_pages=feed()))
        self.assertTrue(verify_source_pages(report["editorial_documents"], feed(), today=TODAY))

    def test_a_disagreement_without_an_exact_explicit_old_address_is_only_held(self):
        for old, new in (("Queste indicazioni sostituiscono i vecchi riferimenti", "Altre informazioni citano"),
                         ("in Piazza del Carmine e in Via dei Bacchettoni", "in Piazza del Carmine Nuova e in Via dei Bacchettoni Nuova")):
            with self.subTest(new=new):
                after, report = self.run_preview(raw=change(old, new))
                self.assertEqual(after, self.base())
                self.assertEqual(report["address_conflicts"], [])

    def test_duplicate_from_any_publisher_or_disagreeing_weekday_prevents_association(self):
        for competitor in (
            market("other-wednesday", street="Via Dante"),
            {**market("other-wednesday", street="Via Dante"), "fonte": "example.it", "url_fonte": "https://example.it/market"},
            {**market("other-mercoledi", day="giovedì", street="Via Dante"), "nome": "Un altro mercato"},
        ):
            with self.subTest(competitor=competitor["slug"]):
                base = [self.base()[0], competitor]
                after, report = self.run_preview(base)
                self.assertEqual(after, base)
                self.assertEqual(report["address_conflicts"], [])

    def test_repeated_or_historical_source_venue_never_gets_an_arbitrary_target(self):
        repeat = "<p>Il mercato settimanale di Lucca si svolge in Via Roma il mercoledì, dalle 8:00 alle 13:00.</p><p><a"
        for raw in (change("<p><a", repeat),
                    change("Lucca città: sedi e giorni aggiornati", "Lucca città: elenco storico da verificare")):
            with self.subTest(raw=raw[:20]):
                after, report = self.run_preview([self.base()[0]], raw=raw)
                self.assertEqual(after, [self.base()[0]])
                self.assertEqual(report["address_conflicts"], [])

    def test_foreign_province_or_unproved_catalog_day_cannot_receive_a_warning(self):
        for change_to_record in ({"provincia": "PI"}, {"ricorrenza_testo": "settimanale"},
                                 {"nome": "Mercatino dell'antiquariato di Lucca"}):
            base = [{**self.base()[0], **change_to_record}]
            after, report = self.run_preview(base)
            self.assertEqual(after, base)
            self.assertEqual(report["address_conflicts"], [])

    def test_verified_address_and_gps_are_never_replaced_by_the_warning(self):
        base = [{**self.base()[0], "verificato_il": "2026-10-10", "position_quality": "precisa"}]
        after, report = self.run_preview(base)
        self.assertEqual(len(report["address_conflicts"]), 1)
        self.assertEqual({k: v for k, v in after[0].items() if k != "conflitti_campi"}, base[0])

    def test_dry_run_does_not_persist_warnings(self):
        after, report = self.run_preview(apply=False)
        self.assertEqual(after, self.base())
        self.assertEqual(len(report["address_conflicts"]), 2)
        self.assertEqual(report["address_conflict_ids"], [])
        self.assertTrue(safe_report(report, self.base(), source_pages=feed()))

    def test_report_or_document_tamper_cannot_authorize_a_warning(self):
        base = self.base()
        _, original = self.run_preview(base)
        for field, value in (("valore_fonte", "Via Inventata"), ("letto_il", "2026-10-19"),
                             ("sha256", "0" * 64), ("url_finale", "https://example.it/")):
            report = deepcopy(original)
            report["address_conflicts"][0]["conflict"][field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                safe_report(report, base, source_pages=feed())
        documents = deepcopy(original["editorial_documents"])
        documents[0]["rows"][0]["source_evidence"]["paragraph_text"] += " Altered."
        with self.assertRaisesRegex(ValueError, "captured HTML"):
            verify_source_pages(documents, feed(), today=TODAY)
        changed_page = feed(change("Piazzale Don Baroni", "Via Roma"))
        with self.assertRaisesRegex(ValueError, "captured HTML"):
            verify_source_pages(original["editorial_documents"], changed_page, today=TODAY)

    def test_regenerated_envelope_from_tampered_document_still_requires_original_bytes(self):
        from happings_weekly_conflicts import propose
        _, report = self.run_preview()
        # Both self-declared document and warning are forged consistently;
        # the unchanged acquisition receipt must still reject the substitute.
        import json
        report["editorial_documents"] = json.loads(json.dumps(
            report["editorial_documents"], ensure_ascii=False).replace("Piazzale Don Baroni", "Via Prova Contrasto"))
        report["address_conflicts"] = propose(self.base(), report["editorial_documents"], today=TODAY,
            apply_authorized=True, rights_gate_passed=True)
        with self.assertRaisesRegex(ValueError, "captured HTML"):
            safe_report(report, self.base(), source_pages=feed())
        with self.assertRaisesRegex(ValueError, "captured source pages"):
            safe_report(report, self.base())

    def test_reread_is_idempotent_and_new_read_day_upserts_only_same_proof(self):
        first, _ = self.run_preview()
        second, repeat = self.run_preview(first)
        self.assertEqual(second, first)
        self.assertEqual(repeat["record_changes"], 0)
        for offset in range(1, 5):
            second, report = self.run_preview(second, today=TODAY + timedelta(days=offset))
            self.assertTrue(safe_report(report, first, source_pages=feed()))
            self.assertTrue(all(len(row["conflitti_campi"]) == 1 for row in second))
        self.assertTrue(all(row["conflitti_campi"][0]["letto_il"] == "2026-10-24" for row in second))

    def test_same_day_changed_source_version_is_held_without_erasing_existing_warning(self):
        first, _ = self.run_preview()
        second, report = self.run_preview(first, raw=HTML + b" ")
        self.assertEqual(second, first)
        self.assertEqual(report["address_conflicts"], [])

    def test_shared_phase_diff_and_static_export_guard_keep_the_warning_bound(self):
        from export_static import prepare
        import happings_autopilot as phase
        base = self.base()
        with tempfile.TemporaryDirectory() as folder:
            after, report, protected = phase.run(
                base, policy={"enabled": True, "details": {"enabled": False}},
                out=Path(folder), today=TODAY, baseline_signature="synthetic-fixture",
                pipeline_policy_digest="synthetic-policy",
                fetcher=lambda urls, **_: feed())
            exported, _ = prepare(after, TODAY, preserve_ids=protected)
            self.assertTrue(phase.verify_exported(base, after, exported, report, today=TODAY, source_checkpoint_dir=Path(folder))["release_safe"])
            with self.assertRaisesRegex(ValueError, "original checkpoint"):
                phase.verify_exported(base, after, exported, report, today=TODAY)
            for field, value in (("indirizzo", "Piazzale Don Baroni"), ("lat", 43.0),
                                 ("verificato_il", TODAY.isoformat()), ("date", [])):
                tampered = deepcopy(after)
                tampered[0][field] = value
                with self.subTest(field=field), self.assertRaises(ValueError):
                    phase.verify_changes(base, tampered, report, source_pages=feed())


if __name__ == "__main__":
    unittest.main()
