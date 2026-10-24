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
from field_evidence import identity, make_receipt, mark_managed_fields, valid_receipt


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

    def evidence(self, row, kind):
        if kind == "riscontri_campi":
            receipt = make_receipt(
                row, values={"orario_testo": row["orario_testo"]},
                source_url=row["url_fonte"], source_name=row["fonte"],
                source_id="fixture", source_row="row-1", read_on=self.today,
                source_updated_on="2026-10-01", source_sha256="a" * 64)
            return [mark_managed_fields(receipt, ["orario_testo"], manager="fixture_ingest")]
        return [{"mercato": identity(row), "data": "2026-10-13", "letto_il": str(self.today),
                 "url": row["url_fonte"], "sha256": "b" * 64,
                 "fonte_id": "fixture", "motivo": "Edizione annullata dal Comune"}]

    def test_field_and_cancellation_evidence_automatically_protect_ids_from_dedup(self):
        first = market(slug="first-id", indirizzo="Via Roma 1", orario_testo="08:00-13:00")
        second = {**first, "slug": "second-id"}
        for kind in ("riscontri_campi", "eccezioni_calendario"):
            for observed in (first, second):
                evidence = self.evidence(observed, kind)
                inputs = [{**row, **({kind: evidence} if row is observed else {})}
                          for row in (first, second)]
                for ordered in (inputs, list(reversed(inputs))):
                    with self.subTest(kind=kind, observed=observed["slug"], first=ordered[0]["slug"]):
                        rows, report = prepare(ordered, self.today)
                        self.assertEqual({r["slug"] for r in rows}, {first["slug"], second["slug"]})
                        self.assertEqual(report["same_source_duplicates_merged"], 0)
                        kept = next(r for r in rows if r["slug"] == observed["slug"])
                        self.assertEqual(kept[kind], evidence)
                        if kind == "riscontri_campi":
                            self.assertTrue(valid_receipt(kept[kind][0], kept, today=self.today))
                            self.assertEqual(kept[kind][0]["campi_gestiti"], ["orario_testo"])
                        else:
                            self.assertEqual(kept["date"], [])
                            other = next(r for r in rows if r["slug"] != observed["slug"])
                            self.assertEqual(other["date"], ["2026-10-13"])

    def test_valid_evidence_blocks_collision_renaming_and_invalid_slug_replacement(self):
        first = market(slug="same-id", indirizzo="Via Roma 1", orario_testo="08:00-13:00")
        second = {**first, "indirizzo": "Piazza Dante 2"}
        for kind in ("riscontri_campi", "eccezioni_calendario"):
            for observed in (first, second):
                inputs = [{**row, **({kind: self.evidence(row, kind)} if row is observed else {})}
                          for row in (first, second)]
                for ordered in (inputs, list(reversed(inputs))):
                    with self.subTest(kind=kind, observed=observed["indirizzo"]):
                        with self.assertRaisesRegex(ValueError, "protected"):
                            prepare(ordered, self.today)
            bad_id = {**first, "slug": "Bad ID"}
            bad_id[kind] = self.evidence(bad_id, kind)
            with self.subTest(kind=kind), self.assertRaisesRegex(ValueError, "protected"):
                prepare([bad_id], self.today)

    def test_invalid_evidence_does_not_acquire_identity_protection(self):
        first = market(slug="first-id", indirizzo="Via Roma 1", orario_testo="08:00-13:00")
        second = {**first, "slug": "second-id"}
        for kind in ("riscontri_campi", "eccezioni_calendario"):
            evidence = self.evidence(second, kind)
            evidence[0]["sha256"] = "invalid"
            rows, report = prepare([first, {**second, kind: evidence}], self.today)
            with self.subTest(kind=kind):
                self.assertEqual(len(rows), 1)
                self.assertEqual(report["same_source_duplicates_merged"], 1)
                self.assertFalse(rows[0].get(kind))

    def test_dataset_timestamp_scope_survives_only_as_detail_provenance(self):
        converted, err = normalize(market(
            slug="lo-mercap-100551-venerdi",
            aggiornato_il="2026-10-06",
            aggiornamento_ambito="dataset",
            id_fonte="100551",
            verificato_il="",
        ), self.today)
        self.assertIsNone(err)
        self.assertEqual(converted["aggiornamento_ambito"], "dataset")
        self.assertEqual(converted["id_fonte"], "100551")
        self.assertEqual(converted["verificato_il"], "")
        self.assertNotIn("aggiornamento_ambito", INDEX_FIELDS)
        self.assertNotIn("id_fonte", INDEX_FIELDS)

    def test_keeps_only_future_valid_dates(self):
        result, error = normalize(market(), self.today)
        self.assertIsNone(error)
        self.assertEqual(result["date"], ["2026-10-13"])

    def test_empty_future_dates_never_claim_a_forecast(self):
        item, reason = normalize(market(
            date=[], date_quality="prevista",
            ricorrenza_testo="mensile - da verificare",
        ), self.today)
        self.assertIsNone(reason)
        self.assertEqual(item["date"], [])
        self.assertEqual(item["date_quality"], "sconosciuta")
        self.assertEqual(item["status"], "non_confermato")

    def test_past_only_date_is_not_a_confirmed_future_edition(self):
        item, reason = normalize(market(
            date=["2026-09-04"], date_quality="confermata",
            verificato_il="2026-09-04",
        ), self.today)
        self.assertIsNone(reason)
        self.assertEqual(item["date"], [])
        self.assertEqual(item["date_quality"], "sconosciuta")
        # Preserve the actual provenance: we demote only the forward-looking
        # display label, not a previously documented historical check.
        self.assertEqual(item["verificato_il"], "2026-09-04")

    def test_future_dates_keep_their_original_conservative_quality(self):
        item, reason = normalize(market(
            date=["2026-10-13"], date_quality="prevista"
        ), self.today)
        self.assertIsNone(reason)
        self.assertEqual(item["date"], ["2026-10-13"])
        self.assertEqual(item["date_quality"], "prevista")

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

    def test_soft_merged_copy_must_point_to_a_kept_record_in_its_town(self):
        from compact_index import project_index
        kept = market("kept", indirizzo="Via Roma 1")
        copy = market("copy", indirizzo="Via Roma 1", url_fonte="https://example.org/markets/2",
                      duplicato_di="kept")
        rows, _ = prepare([kept, copy], self.today)
        index = {r[0]: r[-1] for r in project_index(rows, schema=7, today=self.today)}
        self.assertEqual(index, {"kept": "", "copy": "kept"})
        for bad in (market("lost", duplicato_di="missing"),
                    market("chain", url_fonte="https://example.org/markets/3", duplicato_di="copy"),
                    market("far", citta="Milano", regione="Lombardia", duplicato_di="kept")):
            with self.subTest(bad["slug"]), self.assertRaises(ValueError):
                prepare([kept, copy, bad], self.today)

    def test_corciano_derived_stable_id_does_not_merge_with_scraped_source(self):
        from export_static import prepare
        old = market(slug="scraped",regione="Umbria",citta="Corciano",
                     nome="Mercato Di Corciano",indirizzo="Piazza Caduti",
                     url_fonte="https://example.org/markets/corciano")
        municipal = market(slug="pg-corciano-mercato-di-corciano",
                           regione="Umbria",citta="Corciano",
                           nome=old["nome"], indirizzo=old["indirizzo"],
                           url_fonte=old["url_fonte"])
        cleaned, stats = prepare([old,municipal], self.today)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(stats["same_source_duplicates_merged"], 0)

    def test_address_enrichment_preserves_both_bookmarks_through_static_export(self):
        from merge_catalog import load_existing
        source = "https://www.happings.com/it/mercati-settimanali-a-venezia.html"
        first = market(
            slug="mercato-settimanale-a-spinea-spinea-mercoledi",
            nome="Mercato settimanale a Spinea", citta="Spinea",
            regione="Veneto", provincia="VE", fonte="happings.com",
            indirizzo="Villaggio dei Fiori", url_fonte=source,
            ricorrenza_testo="settimanale - mercoledì", date=["2026-10-14"],
        )
        second = {**first, "slug":"mercato-settimanale-di-spinea-spinea-mercoledi",
                  "nome":"Mercato settimanale di Spinea"}
        # A filled address makes the two legacy names mergeable. Either ID
        # can be the protected enrichment target, in either input order.
        self.assertEqual(len(prepare([first, second], self.today)[0]), 1)
        for protected in ({first["slug"]}, {second["slug"]}):
            for records in ([first, second], [second, first]):
                with self.subTest(protected=protected, first=records[0]["slug"]):
                    with tempfile.TemporaryDirectory() as folder:
                        out = Path(folder)/"public/data/v1"
                        result = export(records, out, self.today, preserve_ids=protected)
                        saved = load_existing(out/"manifest.json")
                    self.assertEqual({row["slug"] for row in saved},
                                     {first["slug"], second["slug"]})
                    self.assertEqual(result["stats"]["same_source_duplicates_merged"], 0)
                    self.assertTrue(all(row["indirizzo"] == "Villaggio dei Fiori" for row in saved))

    def test_protected_ids_cannot_be_filtered_renamed_or_repeated(self):
        for records, protected in (
            ([market(status="annullato")], {"mercato-centro-roma"}),
            ([market(slug="Bad ID")], {"Bad ID"}),
            ([market(), market()], {"mercato-centro-roma"}),
            ([market()], {"missing-id"}),
        ):
            with self.subTest(protected=protected), self.assertRaisesRegex(ValueError, "protected"):
                prepare(records, self.today, preserve_ids=protected)
        with self.assertRaisesRegex(ValueError, "set of nonempty"):
            prepare([market()], self.today, preserve_ids="mercato-centro-roma")

    def test_distinct_lombardia_publisher_ids_same_street_day_never_merge(self):
        first = market(
            slug="lo-mercap-100551-venerdi",
            nome="Mercato di Pogliano Milanese – Via Europa",
            regione="Lombardia", citta="Pogliano Milanese",
            indirizzo="VIA EUROPA", date=["2026-10-16"],
            url_fonte="https://www.dati.lombardia.it/d/68zx-njaw",
        )
        second = market(
            slug="lo-mercap-100552-venerdi",
            nome=first["nome"], regione=first["regione"],
            citta=first["citta"], indirizzo=first["indirizzo"],
            date=first["date"], url_fonte=first["url_fonte"],
        )
        cleaned, report = prepare([first, second], self.today)
        self.assertEqual(len(cleaned), 2)
        self.assertEqual(report["same_source_duplicates_merged"], 0)
        self.assertEqual({r["slug"] for r in cleaned},
                         {"lo-mercap-100551-venerdi", "lo-mercap-100552-venerdi"})

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
            self.assertEqual(manifest["index_schema"], 7)
            self.assertEqual(manifest["index_as_of"], self.today.isoformat())
            self.assertTrue((Path(temp) / "public" / manifest["index"]).is_file())
            index = json.loads((Path(temp) / "public" / manifest["index"]).read_text("utf-8"))
            self.assertIsInstance(index["markets"][0], list)
            self.assertEqual(index["markets"][0][0], "mercato-centro-roma")
            self.assertEqual(index["markets"][0][11], ["2026-10-13"])
            self.assertEqual(index["markets"][0][12], "")
            self.assertEqual(index["markets"][0][13], "")
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
        self.assertEqual(out[0]["date_quality"], "sconosciuta")
        self.assertEqual(out[0]["date"], [])
        self.assertEqual(out[0]["status"], "non_confermato")
        self.assertEqual(out[0]["aggiornato_il"], "2024-05-27")
        self.assertIsNone(out[0]["lat"])
        self.assertIn("calendario, sede e orari da verificare", out[0]["descrizione"])
        # The same source may be used as a *forecast* only near its source date.
        fresh = convert([record], today=date(2025, 1, 10))[0]
        self.assertTrue(fresh["date"])
        self.assertEqual(fresh["date_quality"], "prevista")
        self.assertTrue(all(date.fromisoformat(d).weekday() in {1, 5} for d in fresh["date"]))

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
