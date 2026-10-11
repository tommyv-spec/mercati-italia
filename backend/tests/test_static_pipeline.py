import json
import tempfile
import unittest
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from export_static import export, normalize, prepare, parse_location, parse_dates
from source_milano import convert


def market(slug="mercato-centro-roma", **kwargs):
    row = {
        "slug": slug,
        "nome": "Mercato Centro",
        "citta": "Roma",
        "regione": "Lazio",
        "provincia": "RM",
        "categoria": "alimentare",
        "date": ["2026-10-13", "2026-10-01"],
        "fonte": "Comune",
        "url_fonte": "https://example.org/markets/1",
        "lat": 41.9, "lng": 12.5,
        "date_quality": "prevista",
    }
    row.update(kwargs)
    return row


class ExportTests(unittest.TestCase):
    def setUp(self):
        self.today = date(2026, 10, 11)

    def test_keeps_only_future_valid_dates(self):
        result, error = normalize(market(), self.today)
        self.assertIsNone(error)
        self.assertEqual(result["date"], ["2026-10-13"])

    def test_never_labels_center_coordinates_precise(self):
        result, _ = normalize(market(), self.today)
        self.assertEqual(result["position_quality"], "non_verificata")

    def test_geocoding_absent_is_not_faked(self):
        result, _ = normalize(market(lat=None, lng=None), self.today)
        self.assertIsNone(result["lat"])
        self.assertIsNone(result["lng"])

    def test_rejects_coordinates_outside_italy(self):
        result, _ = normalize(market(lat=0, lng=0), self.today)
        self.assertIsNone(result["lat"])
        self.assertEqual(result["position_quality"], "sconosciuta")

    def test_does_not_misclassify_sagre_as_markets(self):
        result, reason = normalize(market(categoria="sagra"), self.today)
        self.assertIsNone(result)
        self.assertEqual(reason, "excluded_non_market_category")

    def test_skips_cancelled(self):
        result, reason = normalize(market(status="annullato"), self.today)
        self.assertIsNone(result)
        self.assertEqual(reason, "inactive_market")

    def test_keeps_distinct_markets_with_same_name_city(self):
        a = market("same-slug", indirizzo="Via Roma 1")
        b = market("same-slug", indirizzo="Piazza Dante 2")
        rows, report = prepare([a, b], self.today)
        self.assertEqual(len(rows), 2)
        self.assertEqual(len(report["id_collisions_kept_separate"]), 1)

    def test_rejects_conflicting_duplicate_without_address(self):
        a = market("same-slug", orario_testo="08:00-12:00")
        b = market("same-slug", orario_testo="09:00-13:00")
        with self.assertRaisesRegex(ValueError, "Conflicting records"):
            prepare([a, b], self.today)

    def test_export_manifest_and_immutability(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "public" / "data" / "v1"
            result = export([market()], out, today=self.today)
            manifest = result["manifest"]
            self.assertEqual(manifest["total"], 1)
            self.assertEqual(manifest["layout"], "single")
            asset = Path(temp) / "public" / manifest["catalog"]
            self.assertTrue(asset.exists())
            snapshot = json.loads(asset.read_text("utf-8"))
            self.assertEqual(snapshot["markets"][0]["slug"], "mercato-centro-roma")
            second = export([market()], out, today=self.today)
            self.assertTrue(second["unchanged"])

    def test_rejects_accidental_mass_deletion(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "public" / "data" / "v1"
            rows = [market(slug="roma-" + str(n)) for n in range(10)]
            export(rows, out, today=self.today)
            with self.assertRaisesRegex(ValueError, "too many markets"):
                export(rows[:2], out, today=self.today)

    def test_dry_run_does_not_write_catalog(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "public" / "data" / "v1"
            result = export([market()], out, today=self.today, dry_run=True)
            self.assertEqual(result["stats"]["accepted"], 1)
            self.assertFalse(out.exists())


class MilanoTests(unittest.TestCase):
    def test_import_official_schema_without_claiming_verification(self):
        record = {
            "ID": 1, "MERCATO": "papiniano", "status mss": "attivo",
            "MARTEDI": "x", "SABATO": "x",
            "orari": "7:30-14:00", "NIL": "MAGENTA",
        }
        out = convert([record], today=date(2026, 10, 11))
        self.assertEqual(len(out), 1)
        self.assertEqual(out[0]["slug"], "mi-mss-1")
        self.assertEqual(out[0]["date_quality"], "prevista")
        self.assertEqual(out[0]["status"], "non_confermato")
        self.assertEqual(out[0]["aggiornato_il"], "2024-05-27")
        self.assertIsNone(out[0]["lat"])
        self.assertTrue(all(date.fromisoformat(d).weekday() in {1, 5} for d in out[0]["date"]))

    def test_inactive_ignored(self):
        self.assertEqual(convert([{"ID": 4, "MERCATO": "closed", "status mss": "non attivo"}]), [])


if __name__ == "__main__":
    unittest.main()
