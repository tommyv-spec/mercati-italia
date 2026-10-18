import unittest
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from merge_catalog import combine


def market(slug="mi-mss-17", **fields):
    baseline = {
        "slug": slug,
        "nome": "Mercato Papiniano",
        "regione": "Lombardia",
        "citta": "Milano",
        "indirizzo": "Viale Papiniano",
        "fonte": "Comune Milano",
        "url_fonte": "https://dati.comune.milano.it/dataset/test",
        "aggiornato_il": "2024-05-27",
        "status": "non_confermato",
        "date_quality": "prevista",
        "date": ["2026-10-13", "2026-10-20"],
        "verificato_il": "",
    }
    baseline.update(fields)
    return baseline


class ProvenanceMergeTests(unittest.TestCase):
    def test_stale_old_prediction_not_resurrected(self):
        old = market()
        new = market(date=[], date_quality="sconosciuta",
                     descrizione="Dati 2024 da ricontrollare")
        merged, stats = combine([old], [new])
        self.assertEqual(stats["merged"], 1)
        self.assertEqual(merged[0]["date"], [])
        self.assertEqual(merged[0]["date_quality"], "sconosciuta")
        self.assertEqual(merged[0]["aggiornato_il"], "2024-05-27")
        self.assertEqual(old["date"], ["2026-10-13", "2026-10-20"])

    def test_confirmed_existing_keeps_verified_dates(self):
        old = market(date_quality="confermata",
                     verificato_il="2026-10-08",
                     aggiornato_il="2026-10-08")
        new = market(date=[], date_quality="sconosciuta",
                     aggiornato_il="2024-05-27")
        combined, stats = combine([old], [new])
        self.assertEqual(combined[0]["date"], old["date"])
        self.assertEqual(combined[0]["date_quality"], "confermata")
        self.assertEqual(combined[0]["verificato_il"], "2026-10-08")

    def test_different_street_markets_never_merge(self):
        old = market()
        newer = market(slug="different", indirizzo="Via Farini 25")
        merged, stats = combine([old], [newer])
        self.assertEqual(len(merged), 2)
        self.assertEqual(stats["merged"], 0)

    def test_corciano_market_identity_is_never_absorbed_by_scraped_duplicate(self):
        original = market(slug="mercato-settimanale-di-corciano-corciano",
                          regione="Umbria", citta="Corciano",
                          nome="Mercato Settimanale Di Corciano",
                          indirizzo="Piazza Caduti")
        municipal = market(slug="pg-corciano-mercato-di-corciano",
                           regione="Umbria", citta="Corciano",
                           nome="Mercato Settimanale Di Corciano",
                           indirizzo="Piazza Caduti")
        combined, counts = combine([original],[municipal])
        self.assertEqual(len(combined),2)
        self.assertEqual(counts["merged"],0)

    def test_official_weekday_identity_never_absorbed_by_generic_city_card(self):
        baseline = market(slug="legacy-venerdi", nome="Mercato di Pogliano Milanese – Via Europa",
                          citta="Pogliano Milanese", indirizzo="Via Europa")
        official = market(slug="lo-mercap-100551-venerdi",
                          nome="Mercato di Pogliano Milanese – Via Europa",
                          citta="Pogliano Milanese", indirizzo="Via Europa",
                          fonte="Regione Lombardia",
                          url_fonte="https://www.dati.lombardia.it/d/68zx-njaw")
        combined, stats = combine([baseline], [official])
        self.assertEqual(len(combined), 2)
        self.assertEqual(stats["merged"], 0)
        self.assertEqual({row["slug"] for row in combined},
                         {"legacy-venerdi", "lo-mercap-100551-venerdi"})

    def test_source_evidence_preserved_and_unique(self):
        original = market(fonte="Old source", url_fonte="https://example.org/old")
        incoming = market(fonte="Municipality", url_fonte="https://example.org/new",
                          aggiornato_il="2026-10-11")
        result, _ = combine([original], [incoming])
        sources = result[0]["fonti"]
        self.assertEqual(len(sources), 2)
        self.assertEqual({x["url"] for x in sources},
                         {"https://example.org/old", "https://example.org/new"})


if __name__ == "__main__":
    unittest.main()
