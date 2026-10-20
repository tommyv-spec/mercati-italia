"""Publication dates survive source/export/offline without becoming verification."""
from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from export_static import export, normalize
from field_evidence import clean_receipts, field_states
from happings_page_metadata import parse_page_metadata, clean_page_metadata
from happings_source_enrichment import preview, safe_report
from happings_weekly_layout import parse, VENICE_NEW, VENICE_OLD
from merge_catalog import load_existing
from recurrence_refresh import refresh_record
from source_freshness import source_date_evidence
from test_happings_province_scope import market, page

TODAY = date(2026, 10, 20)
PUBLISHED = "2025-10-24T09:08:09+00:00"
MODIFIED = "2025-10-24T09:33:55+00:00"


def document(*, nodes=None, meta="", footer=""):
    if nodes is None:
        nodes = [{"@type": "WebPage", "url": VENICE_NEW,
                  "datePublished": PUBLISHED, "dateModified": MODIFIED}]
    markup = '<script type="application/ld+json">' + json.dumps({"@graph": nodes}) + '</script>'
    return page([("Spinea", "Via Roma")]).replace(b"</head>", (meta + markup + "</head>").encode()).replace(
        b"</body>", ("<footer>" + footer + "</footer></body>").encode())


def enriched(raw):
    before = [market()]
    after, report = preview(before, [{"requested_url": VENICE_OLD, "final_url": VENICE_NEW,
                                     "html": raw}], today=TODAY, apply=True, rights_verified=True)
    return before, after, report


class PageMetadataTests(unittest.TestCase):
    def test_webpage_dates_are_discovered_without_article_meta(self):
        parsed = parse(document(), source_url=VENICE_NEW, observed_on=TODAY)
        metadata = parsed.page_metadata
        self.assertEqual(metadata["published_at"], PUBLISHED)
        self.assertEqual(metadata["modified_at"], MODIFIED)
        self.assertEqual(metadata["conflicts"], [])
        self.assertEqual({x["property"] for x in metadata["evidence"]},
                         {"WebPage.datePublished", "WebPage.dateModified"})
        self.assertEqual(clean_page_metadata(metadata, final_url=VENICE_NEW, read_on=TODAY), metadata)

    def test_foreign_webpage_event_dates_and_footer_metadata_cannot_supply_page_dates(self):
        nodes = [{"@type": "WebPage", "url": VENICE_OLD, "datePublished": PUBLISHED},
                 {"@type": "WebPage", "url": "https://www.happings.com/it/", "datePublished": PUBLISHED},
                 {"@type": "Event", "url": VENICE_NEW, "datePublished": PUBLISHED,
                  "startDate": "2026-10-21T07:00:00+02:00"}]
        footer = ('<meta property="article:published_time" content="' + PUBLISHED + '">'
                  '<script type="application/ld+json">' + json.dumps({"@type": "WebPage", "url": VENICE_NEW,
                  "datePublished": PUBLISHED}) + '</script><head><meta property="article:modified_time" content="'
                  + MODIFIED + '"></head>')
        metadata = parse_page_metadata(document(nodes=nodes, footer=footer), final_url=VENICE_NEW, read_on=TODAY)
        self.assertIsNone(metadata)
        malformed = ('<html><body><footer><head><meta property="article:published_time" content="'
                     + PUBLISHED + '"></head></footer></body></html>').encode()
        self.assertIsNone(parse_page_metadata(malformed, final_url=VENICE_NEW, read_on=TODAY))

    def test_canonical_tag_does_not_rescope_metadata_to_an_unobserved_page(self):
        raw = document(nodes=[{"@type": "WebPage", "url": VENICE_OLD, "datePublished": PUBLISHED}],
                       meta='<link rel="canonical" href="' + VENICE_OLD + '">')
        self.assertIsNone(parse_page_metadata(raw, final_url=VENICE_NEW, read_on=TODAY))

    def test_future_invalid_and_conflicting_dates_are_explicitly_unresolved(self):
        for value, code in (("2027-01-01T01:00:00+00:00", "future_editorial_date"),
                            ("2026-02-30T01:00:00+00:00", "invalid_editorial_date"),
                            ("ieri", "invalid_editorial_date"),
                            ("2025-10-24T08:08:09+00:00", "conflicting_editorial_dates")):
            with self.subTest(value=value):
                meta = '<meta property="article:published_time" content="' + value + '">'
                result = parse_page_metadata(document(meta=meta), final_url=VENICE_NEW, read_on=TODAY)
                self.assertIsNone(result["published_at"])
                self.assertEqual(result["modified_at"], MODIFIED)
                self.assertTrue(any(x["code"] == code for x in result["conflicts"]))
                self.assertEqual(clean_page_metadata(result, final_url=VENICE_NEW, read_on=TODAY), result)

    def test_equivalent_timestamps_are_not_conflicts_but_reversed_dates_are(self):
        meta = '<meta property="article:published_time" content="2025-10-24T11:08:09+02:00">'
        result = parse_page_metadata(document(meta=meta), final_url=VENICE_NEW, read_on=TODAY)
        self.assertEqual(result["published_at"], PUBLISHED)
        self.assertEqual(result["conflicts"], [])
        nodes = [{"@type": "WebPage", "url": VENICE_NEW, "datePublished": PUBLISHED,
                  "dateModified": "2025-10-23T09:00:00+00:00"}]
        result = parse_page_metadata(document(nodes=nodes), final_url=VENICE_NEW, read_on=TODAY)
        self.assertIsNone(result["modified_at"])
        self.assertIn({"field": "modified_at", "code": "modification_precedes_publication"}, result["conflicts"])

    def test_unbounded_metadata_does_not_keep_a_convenient_partial_date(self):
        nodes = [{"@type": "WebPage", "url": VENICE_NEW, "datePublished": PUBLISHED}] * 33
        self.assertIsNone(parse_page_metadata(document(nodes=nodes), final_url=VENICE_NEW, read_on=TODAY))

    def test_same_day_complete_timestamps_keep_their_actual_order(self):
        for published, modified in (
                ("2025-10-24T12:00:00+00:00", "2025-10-24T09:00:00+00:00"),
                ("2025-10-24T11:30:00+02:00", "2025-10-24T09:00:00+00:00"),
                ("2025-10-24T09:00:00.000002+00:00", "2025-10-24T09:00:00.000001+00:00")):
            with self.subTest(published=published, modified=modified):
                nodes = [{"@type": "WebPage", "url": VENICE_NEW,
                          "datePublished": published, "dateModified": modified}]
                result = parse_page_metadata(document(nodes=nodes), final_url=VENICE_NEW, read_on=TODAY)
                self.assertIsNone(result["modified_at"])
                self.assertIn({"field": "modified_at", "code": "modification_precedes_publication"},
                              result["conflicts"])
                self.assertEqual(clean_page_metadata(result, final_url=VENICE_NEW, read_on=TODAY), result)

    def test_same_day_date_only_metadata_does_not_invent_a_time_order(self):
        for published, modified in (
                ("2025-10-24", "2025-10-24T09:00:00+00:00"),
                ("2025-10-24T12:00:00+00:00", "2025-10-24"),
                ("2025-10-24T11:00:00+02:00", "2025-10-24T09:00:00+00:00")):
            with self.subTest(published=published, modified=modified):
                nodes = [{"@type": "WebPage", "url": VENICE_NEW,
                          "datePublished": published, "dateModified": modified}]
                result = parse_page_metadata(document(nodes=nodes), final_url=VENICE_NEW, read_on=TODAY)
                self.assertIsNotNone(result["published_at"])
                self.assertIsNotNone(result["modified_at"])
                self.assertEqual(result["conflicts"], [])

    def test_page_metadata_is_bound_to_page_and_receipt_by_semantic_guard(self):
        before, after, report = enriched(document())
        source = report["source_pages"][0]["page_metadata"]
        proof = after[0]["riscontri_campi"][0]
        self.assertEqual(proof["metadati_pagina"], source)
        self.assertEqual(proof["fonte_aggiornata_il"], "")
        self.assertEqual(proof["letto_il"], TODAY.isoformat())
        self.assertTrue(safe_report(report, before))
        for mutate in ("url", "published_at", "conflicts", "promote_to_row_freshness"):
            with self.subTest(mutate=mutate):
                altered = copy.deepcopy(report)
                metadata = altered["observations"][0]["source_proof"]["metadati_pagina"]
                if mutate == "url":
                    metadata["url"] = VENICE_OLD
                elif mutate == "published_at":
                    metadata["published_at"] = "2026-10-20T09:00:00+00:00"
                elif mutate == "conflicts":
                    metadata["conflicts"] = [{"field": "published_at", "code": "invented"}]
                else:
                    altered["observations"][0]["source_proof"]["fonte_aggiornata_il"] = "2026-10-20"
                with self.assertRaises(ValueError):
                    safe_report(altered, before)

    def test_editorial_metadata_does_not_change_freshness_confirmation_or_projection(self):
        _, with_dates, report = enriched(document())
        _, without_dates, _ = enriched(document(nodes=[]))
        first, plain = with_dates[0], without_dates[0]
        self.assertEqual(field_states(first, today=TODAY), field_states(plain, today=TODAY))
        self.assertEqual(field_states(first, today=TODAY)["indirizzo"], "riscontrato_data_fonte_sconosciuta")
        self.assertEqual(source_date_evidence(first), source_date_evidence(plain))
        self.assertEqual(report["market_openings_verified"], 0)
        left, left_reason = refresh_record(first, TODAY + timedelta(days=1))
        right, right_reason = refresh_record(plain, TODAY + timedelta(days=1))
        self.assertEqual(left_reason, right_reason)
        for key in ("date", "date_quality", "verificato_il", "status", "proiezione_generata_il", "proiezione_regola"):
            self.assertEqual(left.get(key), right.get(key))

    def test_export_load_and_next_day_offline_keep_editorial_dates_and_original_read(self):
        _, rows, _ = enriched(document())
        expected = copy.deepcopy(rows[0]["riscontri_campi"][0]["metadati_pagina"])
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "public/data/v1"
            export(rows, out, today=TODAY)
            loaded = load_existing(out / "manifest.json")
            self.assertEqual(len(loaded), 1)
            refreshed, _ = refresh_record(loaded[0], TODAY + timedelta(days=1))
            normalized, reason = normalize(refreshed, TODAY + timedelta(days=1))
            self.assertIsNone(reason)
            proof = normalized["riscontri_campi"][0]
            self.assertEqual(proof["metadati_pagina"], expected)
            self.assertEqual(proof["letto_il"], TODAY.isoformat())
            self.assertEqual(proof["fonte_aggiornata_il"], "")
            self.assertEqual(normalized["verificato_il"], "")
            self.assertEqual(normalized["slug"], rows[0]["slug"])

    def test_conflict_status_cannot_be_erased_when_receipt_is_cleaned_later(self):
        raw = document(meta='<meta property="article:published_time" content="2026-10-21T12:00:00+00:00">')
        _, rows, _ = enriched(raw)
        proof = rows[0]["riscontri_campi"][0]
        self.assertIsNone(proof["metadati_pagina"]["published_at"])
        self.assertTrue(proof["metadati_pagina"]["conflicts"])
        later = clean_receipts([proof], rows[0], today=TODAY + timedelta(days=2))
        self.assertEqual(later[0]["metadati_pagina"], proof["metadati_pagina"])
        forged = copy.deepcopy(proof)
        forged["metadati_pagina"]["conflicts"] = []
        self.assertEqual(clean_receipts([forged], rows[0], today=TODAY + timedelta(days=2)), [])

    def test_same_observed_bytes_can_gain_metadata_without_a_new_read_or_lost_ownership(self):
        _, rows, _ = enriched(document())
        original = copy.deepcopy(rows[0])
        original["riscontri_campi"][0].pop("metadati_pagina")
        after, report = preview([original], [{"requested_url": VENICE_OLD, "final_url": VENICE_NEW,
                                             "html": document()}], today=TODAY, apply=True, rights_verified=True)
        proof = after[0]["riscontri_campi"][0]
        self.assertEqual(proof["metadati_pagina"], rows[0]["riscontri_campi"][0]["metadati_pagina"])
        for key in ("letto_il", "sha256", "valori", "fonte_aggiornata_il", "campi_gestiti", "gestore_campi"):
            self.assertEqual(proof.get(key), original["riscontri_campi"][0].get(key))
        self.assertEqual(report["field_changes"], 0)
        self.assertTrue(safe_report(report, [original]))


if __name__ == "__main__":
    unittest.main()
