import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from export_static import EVENTS_FIELDS, events_rows, is_weekly_market, short_description  # noqa: E402


class EventsFileTests(unittest.TestCase):
    def test_weekly_by_rule_or_tag(self):
        self.assertTrue(is_weekly_market({"proiezione_regola": {"kind": "weekly", "weekdays": [2]}}))
        self.assertTrue(is_weekly_market({"tags": ["mercato comunale"]}))
        self.assertTrue(is_weekly_market({"tags": ["MERCAP"]}))
        self.assertFalse(is_weekly_market({"proiezione_regola": {"kind": "monthly_nth_weekday"}, "tags": ["antiquariato"]}))
        self.assertFalse(is_weekly_market({"categoria": "misto"}))

    def test_short_description_cuts_on_sentence_then_word(self):
        self.assertEqual(short_description("Breve."), "Breve.")
        long_text = "Prima frase lunga. " * 10 + "Seconda frase che non entra."
        cut = short_description(long_text, limit=60)
        self.assertTrue(cut.endswith("…"))
        self.assertLessEqual(len(cut), 61)
        self.assertEqual(short_description("a" * 300, limit=240), "a" * 240 + "…")
        self.assertEqual(short_description(None), "")

    def test_events_rows_skip_weekly_concluded_and_merged(self):
        markets = [
            {"slug": "fiera", "indirizzo": "Piazza Grande", "ricorrenza_testo": "primo weekend",
             "descrizione": "Testo.", "ingresso": "Ingresso gratuito", "consigli": "Arriva presto",
             "tags": ["antiquariato"], "proiezione_regola": None},
            {"slug": "weekly", "tags": ["settimanale"]},
            {"slug": "gone", "concluso": "fonte_non_riletta"},
            {"slug": "copy", "duplicato_di": "fiera"},
        ]
        rows = events_rows(markets)
        self.assertEqual(rows, [["fiera", "Piazza Grande", "primo weekend", "Testo.", "Ingresso gratuito", "Arriva presto"]])
        self.assertEqual(EVENTS_FIELDS, ("slug", "indirizzo", "ricorrenza_testo", "descrizione", "ingresso", "consigli"))


if __name__ == "__main__":
    unittest.main()
