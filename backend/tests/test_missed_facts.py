import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from missed_facts import lost_in_merge, page_text, time_range


class MissedFactsTests(unittest.TestCase):
    def test_time_ranges_as_pages_write_them(self):
        # Real Cose di Casa wording (Bordighera's typo, Catania, Cecina).
        for text in ("prima domenica del mese. Dale ore 8 alle 19.", "dalle ore 7 fino alle 14",
                     "tutto l'anno, dalle ore 9 alle 19,30.", "Orario: 9:00 - 18:30"):
            with self.subTest(text=text):
                self.assertIsNotNone(time_range(text))
        for text in ("Tel: 02.63.675.307", "aggiornato 2022-08-11 00:44:41", "ore 19 alle 8", "la mattina"):
            with self.subTest(text=text):
                self.assertIsNone(time_range(text))

    def test_page_text_drops_scripts_and_the_site_footer(self):
        html = (b"<html><script>var t='ore 8 alle 9'</script><h1>Mercato</h1><p>Si svolge</p>"
                b"<footer>P.IVA 12601550150 - dalle 9 alle 18</footer></html>")
        self.assertEqual(page_text(html).strip(), "Mercato Si svolge")

    def test_a_hidden_copy_with_clock_hours_is_a_loss_but_the_template_is_not(self):
        shown = {"slug": "a", "orario_testo": "La mattina", "indirizzo": "centro"}
        rows = [shown,
                {"slug": "b", "duplicato_di": "a", "fonte": "happings.com",
                 "orario_testo": "07:15–13:00 (fonte comunale, da verificare)", "indirizzo": "Piazza Roma"},
                {"slug": "c", "duplicato_di": "a", "fonte": "eventiesagre.it", "orario_testo": "08:00–13:00"}]
        lost = lost_in_merge(rows, {r["slug"]: r for r in rows})
        self.assertEqual(sorted((x["field"], x["copy"]) for x in lost), [("indirizzo", "b"), ("orario", "b")])


    def test_the_shown_card_becomes_the_copy_that_states_clock_hours(self):
        from export_static import prefer_exact_hours
        def group(*copies):
            kept = {"slug": "k", "fonte": "happings.com", "orario_testo": "La mattina",
                    "indirizzo": "Via Roma", "date": ["2026-11-04"]}
            return [kept] + [{"slug": f"c{i}", "duplicato_di": "k", "date": ["2026-11-04"], **c}
                             for i, c in enumerate(copies)]
        official = {"fonte": "happings.com", "orario_testo": "07:15–13:00 (fonte comunale, da verificare)",
                    "indirizzo": "Piazza Paolo VI"}
        rows, merged = group(official), {}
        self.assertEqual(prefer_exact_hours(rows, merged, lambda r: ""), 1)
        self.assertEqual(merged, {"k": "c0"})
        self.assertNotIn("duplicato_di", rows[1])
        for copies in ([{**official, "indirizzo": ""}],                                  # would lose the street
                       [{"fonte": "eventiesagre.it", "orario_testo": "08:00–13:00", "indirizzo": "Via Roma"}],
                       [official, {**official, "orario_testo": "08:00–12:00"}]):           # two candidates
            with self.subTest(copies=copies):
                merged = {}
                self.assertEqual(prefer_exact_hours(group(*copies), merged, lambda r: ""), 0)
                self.assertEqual(merged, {})


if __name__ == "__main__":
    unittest.main()
