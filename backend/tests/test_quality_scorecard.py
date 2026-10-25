import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import quality_scorecard as q

TODAY = date(2026, 10, 25)


def row(slug, **fields):
    return {"slug": slug, "fonte": "happings.com", "orario_testo": "", "indirizzo": "",
            "date": [], "lat": None, "riscontri_campi": [], **fields}


class ScorecardTests(unittest.TestCase):
    def test_counts_only_visible_markets_and_classifies_fields(self):
        rows = [row("a", orario_testo="08:00–13:00", indirizzo="Via Roma", date=["2026-11-01"], lat=45.0,
                    riscontri_campi=[{"letto_il": "2026-10-24"}]),
                row("b", orario_testo="La mattina", indirizzo="centro"),
                row("copy", orario_testo="La mattina", duplicato_di="b")]
        m = q.measure(rows, TODAY)
        self.assertEqual((m["schede"], m["visibili"], m["copie_unite"]), (3, 2, 1))
        self.assertEqual(m["percentuali"]["orari_esatti"], 50.0)
        self.assertEqual(m["percentuali"]["solo_fascia"], 50.0)
        self.assertEqual(m["percentuali"]["solo_centro"], 50.0)
        self.assertEqual(m["fonti"]["happings.com"]["letta_il"], "2026-10-24")

    def test_only_reads_of_the_markets_own_source_count(self):
        page = "https://www.eventiesagre.it/Eventi/1_Fiera.html"
        other = row("other", fonte="eventiesagre.it", url_fonte="https://www.eventiesagre.it/Eventi/2.html",
                    riscontri_campi=[{"url": "https://www.happings.com/it/x/", "letto_il": "2026-10-25"}])
        reread = row("reread", fonte="eventiesagre.it", url_fonte=page)
        m = q.measure([other, reread], TODAY, {page: "2026-10-21"})
        self.assertEqual(m["fonti"]["eventiesagre.it"]["letta_il"], "2026-10-21")
        self.assertEqual(m["fonti"]["eventiesagre.it"]["riletti_30_giorni"], 50.0)

    def test_red_flags_for_drops_stale_sources_and_failed_jobs(self):
        now = q.measure([row("a", orario_testo="La mattina", riscontri_campi=[{"letto_il": "2026-10-01"}])], TODAY)
        before = {"date": "2026-10-18", "visibili": 1, "percentuali": {**now["percentuali"], "orari_esatti": 40.0}}
        flags = q.red_flags(now, before, {"settimanale": {"status": "failed", "at": "2026-10-20"}}, TODAY)
        self.assertEqual(len(flags), 3)
        self.assertEqual(q.red_flags(now, None, {"giornaliero": {"status": "ok"}},
                                     date(2026, 10, 5)), [])

    def test_history_keeps_one_entry_per_day_and_compares_with_the_previous_day(self):
        import json, tempfile
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            history, report = Path(tmp) / "h.json", Path(tmp) / "r.md"
            with patch.object(q, "load_existing", return_value=[row("a")]):
                q.run(Path("m"), history, report, today=date(2026, 10, 18))
                q.run(Path("m"), history, report, today=TODAY)
                q.run(Path("m"), history, report, today=TODAY)
            self.assertEqual([h["date"] for h in json.loads(history.read_text("utf-8"))],
                             ["2026-10-18", "2026-10-25"])
            self.assertIn("(2026-10-18)", report.read_text("utf-8"))


if __name__ == "__main__":
    unittest.main()
