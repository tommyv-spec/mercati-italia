import unittest
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_probe import sample_target, safe_url, extract_columns, infer_columns, survey, MAX_PROBES


def source(ident, url, fmt="CSV", kind="market_location_candidate"):
    return {
        "id": ident, "title": ident, "triage_class": kind, "triage_reasons": [],
        "resources": [{"url": url, "format": fmt}],
    }


class SchemaProbeTests(unittest.TestCase):
    def test_known_provider_sample_urls_are_bounded_queries(self):
        bologna = source("bo", "https://opendata.comune.bologna.it/api/v2/catalog/datasets/mercati-e-fiere/exports/csv?use_labels=true")
        lombardia = source("lo", "https://www.dati.lombardia.it/api/views/68zx-njaw/rows.csv?accessType=DOWNLOAD")
        self.assertEqual(sample_target(bologna)[1], "JSON")
        self.assertIn("limit=5", sample_target(bologna)[0])
        self.assertIn("%24limit=5", sample_target(lombardia)[0])
        self.assertTrue(safe_url(sample_target(lombardia)[0]))

    def test_unapproved_or_private_urls_are_never_contacted(self):
        for url in ["http://opendata.comune.bologna.it/test.csv",
                    "https://opendata.comune.bologna.it.evil.com/test.csv",
                    "https://localhost/private.csv",
                    "https://user:password@www.dati.lombardia.it/file.csv"]:
            self.assertFalse(safe_url(url))
        self.assertEqual(sample_target(source("unsafe", "https://evil.example/dump.csv")), (None, None))

    def test_sample_is_schema_only_and_never_saves_source_values(self):
        registry = {
            "schema": 1, "record_imports": 0,
            "sources": [source("Roma", "https://dati.comune.roma.it/catalog/mercati.csv")],
        }
        sample = b"Nome_Mercato,INDIRIZZO,Apertura_Lunedi,Chiusura_Lunedi\nSecret Name,Via Test 4,8,15\n"
        output = survey(registry, fetch=lambda _: (sample, False))
        self.assertEqual(output["imports"], 0)
        self.assertEqual(output["verified_event_count"], 0)
        found = output["reports"][0]
        self.assertEqual(found["status"], "schema_preview_only")
        self.assertIn("name", found["field_hints"])
        self.assertIn("address", found["field_hints"])
        self.assertIn("hours", found["field_hints"])
        self.assertNotIn("Secret Name", str(output))
        self.assertFalse(found["source_license_verified"])

    def test_provider_json_schema_and_offline_mode(self):
        contents = b'{"results":[{"nome":"Sample","indirizzo":"Via A","giorno":"sabato"}]}'
        fields = extract_columns(contents, "JSON")
        self.assertEqual(len(fields), 3)
        self.assertIn("weekday", infer_columns(fields))
        registry = {"schema": 1, "record_imports": 0,
                    "sources": [source("b", "https://dati.comune.roma.it/file.csv")]}
        offline = survey(registry, offline=True)
        self.assertEqual(offline["reports"][0]["status"], "offline_skipped")

    def test_real_bologna_schema_distinguishes_market_name_and_district(self):
        fields = ["denominazione", "tipologia_mercato", "nome_quartiere",
                  "nome_zona", "ubicazione", "giorni_svolgimento",
                  "orario_svolgimento", "lat", "long", "geopoint"]
        hints = infer_columns(fields)
        self.assertEqual(hints["name"], ["denominazione"])
        self.assertEqual(hints["market_type"], ["tipologia_mercato"])
        self.assertEqual(hints["district"], ["nome_quartiere", "nome_zona"])
        self.assertEqual(hints["longitude"], ["long"])
        self.assertEqual(hints["latitude"], ["lat"])

    def test_real_lombardia_schema_does_not_invent_market_name_or_wgs84(self):
        fields = ["codice_id", "descom", "ubicazione", "periodicita_tipo",
                  "giorno", "dalle_ore_invernale", "anno_istituzione_mercato",
                  "geo_x", "geo_y", "location"]
        hints = infer_columns(fields)
        self.assertNotIn("name", hints)
        self.assertNotIn("latitude", hints)
        self.assertNotIn("longitude", hints)
        self.assertEqual(hints["municipality"], ["descom"])
        self.assertEqual(hints["stable_id_candidate"], ["codice_id"])
        self.assertEqual(hints["geometry_requires_crs_review"], ["geo_x", "geo_y", "location"])

    def test_real_roma_schema_distinguishes_notes_and_municipio(self):
        fields = ["Municipio", "Nome_Mercato", "Note_mercato",
                  "INDIRIZZO", "Apertura_Lunedi", "Chiusura_Lunedi"]
        hints = infer_columns(fields)
        self.assertEqual(hints["name"], ["Nome_Mercato"])
        self.assertEqual(hints["notes"], ["Note_mercato"])
        self.assertEqual(hints["district"], ["Municipio"])
        self.assertNotIn("municipality", hints)
        self.assertIn("hours", hints)

    def test_failed_link_is_recorded_not_promoted(self):
        registry = {"schema": 1, "record_imports": 0,
                    "sources": [source("b", "https://dati.comune.roma.it/file.csv")]}
        def fail(_):
            raise ConnectionError("offline")
        out = survey(registry, fetch=fail)
        self.assertEqual(out["reports"][0]["status"], "needs_review")
        self.assertEqual(out["imports"], 0)


if __name__ == "__main__":
    unittest.main()
