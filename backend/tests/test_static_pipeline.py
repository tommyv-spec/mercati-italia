import json
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from export_static import export, normalize, prepare, parse_location, parse_dates, small_index, INDEX_FIELDS
from source_milano import convert
from source_firenze import convert as convert_firenze


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

    def test_generic_festival_requires_market_evidence(self):
        row, reason = normalize(market(nome="Festa della Castagna", categoria="misto"), self.today)
        self.assertIsNone(row)
        self.assertEqual(reason, "generic_without_market_evidence")

    def test_region_name_is_normalized(self):
        result, _ = normalize(market(regione="Emilia romagna"), self.today)
        self.assertEqual(result["regione"], "Emilia-Romagna")
        result, _ = normalize(market(regione="Val D'Aosta"), self.today)
        self.assertEqual(result["regione"], "Valle d'Aosta")

    def test_excludes_non_italian_regions(self):
        result, reason = normalize(market(regione="Galicia"), self.today)
        self.assertIsNone(result)
        self.assertEqual(reason, "not_italian_region")

    def test_link_sanitization(self):
        result, _ = normalize(market(url_fonte="javascript:alert(1)"), self.today)
        self.assertEqual(result["url_fonte"], "")
        self.assertEqual(result["completezza"], 45)  # base + future date + approximate coordinates

    def test_excludes_obsolete_named_edition(self):
        result, reason = normalize(
            market(nome="Collezionare a Firenze - Giugno 2023", date=[]), self.today
        )
        self.assertIsNone(result)
        self.assertEqual(reason, "historical_edition_without_future_date")

    def test_keeps_old_year_if_new_future_date_is_documented(self):
        result, reason = normalize(
            market(nome="Mostra Mercato 2023", date=["2026-10-13"]), self.today
        )
        self.assertIsNone(reason)
        self.assertIsNotNone(result)

    def test_skips_city_with_no_letters(self):
        result, reason = normalize(market(citta="70-72"), self.today)
        self.assertIsNone(result)
        self.assertEqual(reason, "invalid_city_name")

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

    def test_merges_same_source_city_and_name_variants(self):
        source = "https://www.happings.com/it/mercati-settimanali-a-chieti.html"
        a = market(
            slug="mercato-settimanale-a-archi-archi-domenica",
            nome="Mercato settimanale a Archi", citta="Archi",
            indirizzo="", url_fonte=source, date=["2026-10-11"],
        )
        b = market(
            slug="mercato-settimanale-di-archi-archi-domenica",
            nome="Mercato settimanale di Archi", citta="Archi",
            indirizzo="ce...", url_fonte=source, date=["2026-10-18"],
        )
        rows, report = prepare([a, b], self.today)
        self.assertEqual(len(rows), 1)
        self.assertEqual(report["same_source_duplicates_merged"], 1)
        self.assertEqual(rows[0]["date"], ["2026-10-11", "2026-10-18"])
        self.assertEqual(rows[0]["date_quality"], "prevista")

    def test_preserves_different_weekdays_at_same_street(self):
        source = "https://example.org/markets/by-city"
        first = market(slug="mercato-semanale-di-roma-roma-lunedi",
                       nome="Mercato settimanale di Roma",
                       citta="Roma", indirizzo="Via Nazionale 12", url_fonte=source)
        second = market(slug="mercato-semanale-di-roma-roma-giovedi",
                        nome="Mercato settimanale di Roma",
                        citta="Roma", indirizzo="Via Nazionale 12", url_fonte=source)
        rows, report = prepare([first, second], self.today)
        self.assertEqual(len(rows), 2)
        self.assertEqual(report["same_source_duplicates_merged"], 0)

    def test_keeps_general_market_record_separate_from_weekday(self):
        source = "https://example.org/markets/by-city"
        summary = market(slug="mercato-settimanale-di-roma-roma",
                         nome="Mercato settimanale di Roma",
                         citta="Roma", indirizzo="Via Nazionale 12", url_fonte=source)
        monday = market(slug="mercato-settimanale-di-roma-roma-lunedi",
                        nome="Mercato settimanale di Roma",
                        citta="Roma", indirizzo="Via Nazionale 12", url_fonte=source)
        rows, report = prepare([summary, monday], self.today)
        self.assertEqual(len(rows), 2)
        self.assertEqual(report["same_source_duplicates_merged"], 0)

    def test_does_not_merge_same_name_at_distinct_addresses(self):
        source = "https://example.org/markets/all"
        a = market(slug="market-1", nome="Mercato artigianale",
                   indirizzo="Via Dante 1", url_fonte=source)
        b = market(slug="market-2", nome="Mercato artigianale",
                   indirizzo="Piazza Garibaldi 2", url_fonte=source)
        rows, report = prepare([a, b], self.today)
        self.assertEqual(len(rows), 2)
        self.assertEqual(report["same_source_duplicates_merged"], 0)

    def test_does_not_merge_same_name_from_different_sources(self):
        a = market(slug="market-a", nome="Mercato settimanale",
                   url_fonte="https://example.org/one")
        b = market(slug="market-b", nome="Mercato settimanale",
                   url_fonte="https://example.org/two")
        rows, report = prepare([a, b], self.today)
        self.assertEqual(len(rows), 2)
        self.assertEqual(report["same_source_duplicates_merged"], 0)

    def test_rejects_conflicting_duplicate_without_address(self):
        a = market("same-slug", orario_testo="08:00-12:00")
        b = market("same-slug", orario_testo="09:00-13:00")
        with self.assertRaisesRegex(ValueError, "Conflicting records"):
            prepare([a, b], self.today)

    def test_search_index_is_small_but_supports_7_day_filters(self):
        dates = [(self.today + timedelta(days=i)).isoformat() for i in range(16)]
        raw = market(date=dates, descrizione="Large description " * 100)
        record, _ = normalize(raw, self.today)
        indexed = small_index([record])[0]
        self.assertEqual(len(indexed[INDEX_FIELDS.index("date")]), 16)
        self.assertNotIn("descrizione", INDEX_FIELDS)
        self.assertNotIn("indirizzo", INDEX_FIELDS)
        self.assertNotIn("fonti", INDEX_FIELDS)
        self.assertIn("orario_testo", INDEX_FIELDS)
        self.assertEqual(len(indexed), len(INDEX_FIELDS))

    def test_export_manifest_and_immutability(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "public" / "data" / "v1"
            result = export([market()], out, today=self.today)
            manifest = result["manifest"]
            self.assertEqual(manifest["total"], 1)
            self.assertEqual(manifest["layout"], "single")
            self.assertEqual(manifest["index_schema"], 5)
            self.assertTrue((Path(temp) / "public" / manifest["index"]).is_file())
            index = json.loads((Path(temp) / "public" / manifest["index"]).read_text("utf-8"))
            self.assertIsInstance(index["markets"][0], list)
            self.assertEqual(index["markets"][0][0], "mercato-centro-roma")
            self.assertEqual(index["markets"][0][-1], ["2026-10-13"])
            asset = Path(temp) / "public" / manifest["catalog"]
            self.assertTrue(asset.exists())
            snapshot = json.loads(asset.read_text("utf-8"))
            self.assertEqual(snapshot["markets"][0]["slug"], "mercato-centro-roma")
            second = export([market()], out, today=self.today)
            self.assertTrue(second["unchanged"])

    def test_rejects_accidental_mass_deletion(self):
        with tempfile.TemporaryDirectory() as temp:
            out = Path(temp) / "public" / "data" / "v1"
            rows = [market(slug="roma-" + str(n), nome="Mercato Centro " + str(n)) for n in range(10)]
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

    def test_official_4326_coordinates(self):
        official = {
            "ID": 1, "MERCATO": "papiniano", "status mss": "attivo",
            "MARTEDI": "x", "SABATO": "x", "LAT_Y_4326": 45.4582755,
            "LONG_X_4326": 9.17023017,
        }
        out = convert([official], today=date(2026, 10, 11))
        self.assertEqual(out[0]["lat"], 45.4582755)
        self.assertEqual(out[0]["lng"], 9.17023017)
        self.assertEqual(out[0]["position_quality"], "precisa")

    def test_inactive_ignored(self):
        self.assertEqual(convert([{"ID": 4, "MERCATO": "closed", "status mss": "non attivo"}]), [])



class FirenzeTests(unittest.TestCase):
    def test_official_point_and_uncertain_schedule(self):
        geojson = {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature", "id": 12,
                "geometry": {"type": "Point", "coordinates": [11.25, 43.77]},
                "properties": {
                    "nome": "Mercato delle Pulci",
                    "indirizzo": "Piazza Annigoni",
                    "descrizione": "Oggetti usati e libri",
                    "feelflorence_link": "https://www.feelflorence.it/it/punti-di-interesse/test",
                    "orari": "lunedì e domenica 9-19",
                },
            }],
        }
        items = convert_firenze(geojson)
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["categoria"], "usato")
        self.assertEqual(items[0]["lat"], 43.77)
        self.assertEqual(items[0]["lng"], 11.25)
        self.assertEqual(items[0]["position_quality"], "precisa")
        self.assertEqual(items[0]["date_quality"], "sconosciuta")
        self.assertEqual(items[0]["date"], [])
        self.assertEqual(items[0]["aggiornato_il"], "2023-03-03")

    def test_geojson_refuses_invalid_coordinates(self):
        geojson = {
            "type": "FeatureCollection",
            "features": [{"type": "Feature", "id": 1,
                          "geometry": {"type": "Point", "coordinates": [0, 0]},
                          "properties": {"nome": "Mercato Test"}}],
        }
        self.assertIsNone(convert_firenze(geojson)[0]["lat"])


if __name__ == "__main__":
    unittest.main()
