import unittest
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_freshness import as_day, source_date_evidence


class SourceDateEvidenceTests(unittest.TestCase):
    def dataset(self, **changes):
        row = {"slug": "lo-mercap-10", "url_fonte": "https://www.dati.lombardia.it/d/68zx-njaw",
               "aggiornamento_ambito": "dataset", "aggiornato_il": "2026-10-06"}
        row.update(changes)
        return row

    def test_unqualified_import_and_verification_dates_are_not_publisher_dates(self):
        row = {"slug": "legacy", "url_fonte": "https://example.org/markets",
               "aggiornato_il": "2026-10-12T10:00:00", "importato_il": "2026-10-12",
               "fonte_letta_il": "2026-10-12", "verificato_il": "2026-10-12"}
        self.assertEqual(source_date_evidence(row)["basis"], "unknown")

    def test_explicit_publisher_date_takes_precedence_over_import(self):
        row = self.dataset(fonte_aggiornata_il="2020-01-01", aggiornato_il="2026-10-12")
        evidence = source_date_evidence(row)
        self.assertEqual(evidence["value"], "2020-01-01")
        self.assertEqual(evidence["basis"], "declared_source_content")
        self.assertEqual(evidence["scope"], "dataset")

    def test_invalid_declared_date_does_not_fall_back_to_a_good_legacy_value(self):
        evidence = source_date_evidence(self.dataset(fonte_aggiornata_il="2026-10-12Tnot-a-time"))
        self.assertEqual(evidence["basis"], "unknown")
        self.assertEqual(evidence["reason"], "invalid_declared_source_date")

    def test_legacy_dataset_requires_reviewed_identity_url_and_date_shape(self):
        self.assertEqual(source_date_evidence(self.dataset())["basis"], "reviewed_legacy_dataset")
        for changes in ({"slug": "other-adapter"}, {"url_fonte": "https://example.org"},
                        {"aggiornamento_ambito": "pagina"},
                        {"aggiornato_il": "2026-10-06T10:00:00"}):
            with self.subTest(changes=changes):
                self.assertEqual(source_date_evidence(self.dataset(**changes))["basis"], "unknown")

    def test_fixed_dated_document_cannot_acquire_new_date_from_an_import(self):
        row = {"slug": "pg-corciano-1", "aggiornamento_ambito": "dataset",
               "url_fonte": "https://comune.corciano.pg.it/area_letturaDocumento/29645/pagsistema.html",
               "aggiornato_il": "2026-01-07"}
        self.assertEqual(source_date_evidence(row)["basis"], "reviewed_legacy_dataset")
        row["aggiornato_il"] = "2026-10-12"
        self.assertEqual(source_date_evidence(row)["basis"], "unknown")

    def test_content_date_requires_attributable_source_url(self):
        for url in (None, "", "javascript:foo", "https://[invalid", "https://example.org:bad",
                    "https://username:password@example.org/"):
            with self.subTest(url=url):
                row = self.dataset(url_fonte=url, fonte_aggiornata_il="2026-10-12")
                self.assertEqual(source_date_evidence(row)["basis"], "unknown")

    def test_date_parser_rejects_date_prefix_followed_by_invalid_timestamp(self):
        for value in (None, "2026-02-30", "2026-10-12Tbad", "2026-10-12 copy", "2026-10-12extra"):
            with self.subTest(value=value):
                self.assertIsNone(as_day(value))
        self.assertEqual(as_day("2026-10-12T09:00:00+00:00"), date(2026, 10, 12))
        self.assertEqual(as_day("2026-10-12"), date(2026, 10, 12))


if __name__ == "__main__":
    unittest.main()
