import unittest
import sys
from pathlib import Path
from datetime import date
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from merge_catalog import combine
from field_evidence import make_receipt


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
    def test_location_fallback_requires_same_explicit_market_identity(self):
        old = market(slug="legacy-id", provincia="MI", categoria="misto",
                     ricorrenza_testo="Ogni lunedì")
        new = {**old, "slug": "renamed-id", "ricorrenza_testo": "settimanale - lunedi"}
        merged, stats = combine([old], [new])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["slug"], old["slug"])
        self.assertEqual(stats["merged"], 1)

    def test_location_fallback_holds_different_or_unproved_identity_fields(self):
        old = market(slug="legacy-id", provincia="MI", categoria="misto",
                     ricorrenza_testo="Ogni lunedì")
        cases = [
            {"provincia": "VA"}, {"provincia": ""},
            {"categoria": "alimentare"}, {"categoria": ""},
            {"fonte": "Altro editore"}, {"fonte": ""},
            {"url_fonte": "https://other.example/markets"}, {"url_fonte": ""},
            {"ricorrenza_testo": "Ogni mercoledì"},
            {"ricorrenza_testo": "Ogni lunedì da giugno ad agosto"},
            {"ricorrenza_testo": "quindicinale - lunedì"},
            {"ricorrenza_testo": "mensile - primo lunedì del mese"},
            {"ricorrenza_testo": "settimanale"},
            {"slug": "renamed-id-mercoledi"},
        ]
        for changes in cases:
            new = {**old, "slug": "renamed-id", **changes}
            for base, incoming in ((old, new), (new, old)):
                with self.subTest(changes=changes, base=base["slug"]):
                    rows, stats = combine([base], [incoming])
                    self.assertEqual({r["slug"] for r in rows}, {old["slug"], new["slug"]})
                    self.assertEqual(stats["merged"], 0)

    def test_matching_slug_days_and_dates_do_not_supply_missing_recurrence(self):
        old = market(slug="legacy-id-lunedi", provincia="MI", categoria="misto",
                     ricorrenza_testo="", date=["2026-10-19"])
        new = {**old, "slug": "renamed-id-lunedi"}
        rows, stats = combine([old], [new])
        self.assertEqual(len(rows), 2)
        self.assertEqual(stats["merged"], 0)

    def test_field_evidence_blocks_fallback_for_either_identity(self):
        first = market(slug="legacy-id", provincia="MI", categoria="misto",
                       ricorrenza_testo="Ogni lunedì", orario_testo="08:00-13:00")
        second = {**first, "slug": "renamed-id"}
        for observed in (first, second):
            receipt = make_receipt(
                observed, values={"orario_testo": observed["orario_testo"]},
                source_url=observed["url_fonte"], source_name=observed["fonte"],
                source_id="fixture", source_row="row-1", read_on=date(2026, 10, 19),
                source_updated_on="2026-10-13", source_sha256="a" * 64)
            rows = [{**row, **({"riscontri_campi": [receipt]} if row is observed else {})}
                    for row in (first, second)]
            for ordered in (rows, list(reversed(rows))):
                with self.subTest(observed=observed["slug"], first=ordered[0]["slug"]):
                    merged, stats = combine(ordered[:1], ordered[1:])
                    self.assertEqual(len(merged), 2)
                    self.assertEqual(stats["merged"], 0)
                    kept = next(row for row in merged if row["slug"] == observed["slug"])
                    self.assertEqual(kept["riscontri_campi"], [receipt])

    def test_stale_old_prediction_not_resurrected(self):
        old = market()
        new = market(date=[], date_quality="sconosciuta",
                     descrizione="Dati 2024 da ricontrollare", fonte_letta_il="2026-10-19")
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
