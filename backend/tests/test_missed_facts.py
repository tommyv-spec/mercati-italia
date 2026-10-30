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



if __name__ == "__main__":
    unittest.main()
