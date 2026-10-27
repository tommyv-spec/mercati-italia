"""A complete Happings province page that lists a town only on other weekdays."""
from __future__ import annotations

import copy
import sys
import unittest
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))
from test_happings_source_enrichment import SAMPLE, TODAY, feed, row
from export_static import concluded_reason
from field_conflicts import delisted_weekday
from happings_source_enrichment import preview, safe_report
from recurrence_refresh import refresh_record


def read(rows, html=SAMPLE, today=TODAY):
    pages = [{**feed()[0], "html": html}]
    after, report = preview(rows, pages, today=today, apply=True, rights_verified=True)
    safe_report(report, rows, source_pages=pages)
    return after, report


class WeekdayConflictTests(unittest.TestCase):
    def test_a_dropped_weekday_withdraws_forecasts_and_hides_the_card(self):
        # The Venice page lists Spinea on Wednesday and Saturday only.
        (card,), report = read([row("spinea-lunedi", day="lunedì")])
        self.assertEqual(report["weekday_conflict_ids"], ["spinea-lunedi"])
        self.assertEqual(card["conflitti_campi"][0]["valore_fonte"], "settimanale - mercoledì, sabato")
        self.assertEqual(concluded_reason(card, TODAY), "")  # dates still upcoming until the refresh
        projected, reason = refresh_record(card, TODAY, 120, 540)
        self.assertEqual(reason, "source_lists_town_on_other_weekdays")
        self.assertEqual((projected["date"], projected["date_quality"]), ([], "sconosciuta"))
        self.assertEqual(concluded_reason(projected, TODAY), "non_piu_elencato")

    def test_a_later_read_that_lists_the_weekday_again_ends_the_warning(self):
        (card,), _ = read([row("spinea-lunedi", day="lunedì")])
        later = TODAY + timedelta(days=7)
        relisted = SAMPLE.replace(b"Mercati del sabato", b"Mercati del luned&#236;")
        (again,), report = read([card], relisted, later)
        self.assertEqual(report["weekday_conflicts"], [])
        self.assertIsNone(delisted_weekday(again, today=later))
        self.assertNotEqual(refresh_record(again, later, 120, 540)[1], "source_lists_town_on_other_weekdays")

    def test_a_town_listed_on_the_card_weekday_is_never_warned(self):
        # Several markets on the card's own weekday (the Ravenna case): listed.
        busy = SAMPLE.replace(b"<li>a Dolo", b"<li>a Spinea, in Via Roma (la mattina)</li><li>a Dolo")
        _, report = read([row("spinea-mercoledi")], busy)
        self.assertEqual(report["weekday_conflicts"], [])

    def test_qualified_rows_or_a_town_missing_from_the_page_prove_nothing(self):
        seasonal = SAMPLE.replace(b"Piazza Fermi (la mattina)", b"Piazza Fermi (estivo) (la mattina)")
        for html, card in ((seasonal, row("spinea-lunedi", day="lunedì")),
                           (SAMPLE, row("mirano-lunedi", city="Mirano", day="lunedì"))):
            with self.subTest(city=card["citta"]):
                _, report = read([card], html)
                self.assertEqual(report["weekday_conflicts"], [])

    def test_the_release_guard_rebuilds_every_warning_from_the_captured_page(self):
        rows = [row("spinea-lunedi", day="lunedì")]
        _, report = preview(rows, feed(), today=TODAY, apply=True, rights_verified=True)
        with self.assertRaises(ValueError):
            safe_report(report, rows, source_pages=None)
        forged = copy.deepcopy(report)
        forged["weekday_conflicts"][0]["conflict"]["prova"]["giorni_elencati"] = [2]
        with self.assertRaises(ValueError):
            safe_report(forged, rows, source_pages=feed())

    def test_a_human_verification_keeps_its_dates(self):
        (card,), _ = read([row("spinea-lunedi", day="lunedì")])
        verified = {**card, "verificato_il": "2026-10-01"}
        self.assertNotEqual(refresh_record(verified, TODAY, 120, 540)[1], "source_lists_town_on_other_weekdays")
        self.assertNotEqual(concluded_reason({**verified, "date": []}, TODAY), "non_piu_elencato")


if __name__ == "__main__":
    unittest.main()
