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

    def test_real_veneto_soave_concession_file_is_not_market_schedule(self):
        # Observed original CSV 2026-10-12:
        # NOME;FIERA/MERCATO;ATTIVITA';DATA VALIDITA CONCESSIONE;DATA SCADENZA CONCESSIONE
        from source_probe import schema_viability
        fields = ["NOME","FIERA/MERCATO","ATTIVITA'",
                  "DATA VALIDITA CONCESSIONE","DATA SCADENZA CONCESSIONE"]
        hints = infer_columns(fields)
        self.assertEqual(
            schema_viability(fields,hints),
            "concession_registry_without_visit_schedule"
        )
        self.assertNotIn("weekday",hints)
        self.assertNotIn("address",hints)

    def test_real_lazio_2007_yearly_census_is_not_visit_calendar(self):
        from source_probe import schema_viability
        fields = ["comune","provincia","anno","mercati","totale",
                  "attivazioni","cessazioni","posteggi",
                  "alimentare_totale","produttori_totale"]
        self.assertEqual(schema_viability(fields,infer_columns(fields)),
                         "historical_aggregate_not_venues")

    def test_allowed_new_hosts_have_strict_official_paths(self):
        soave = ("https://dati.veneto.it/SpodCkanApi/api/2/rest/dataset/"
                 "4afb27b6-e3a4-4f25-9dae-5c1fa925e4d9.csv")
        lazio = ("https://dati.lazio.it/dataset/"
                 "74600cc1-0adb-4ae3-8255-30556e03e932/resource/"
                 "2d48b4df-5df7-48c5-81d8-a8f8758d7756/download/oscomercatimensili.csv")
        self.assertTrue(safe_url(soave))
        self.assertTrue(safe_url(lazio))
        self.assertFalse(safe_url("https://dati.veneto.it/admin/users"))
        self.assertFalse(safe_url("https://dati.lazio.it/private/review.csv"))
        self.assertFalse(safe_url(soave + "?url=http://localhost"))
        self.assertFalse(safe_url(lazio.replace(".csv",".exe")))
        self.assertEqual(sample_target(source("v",soave))[1],"CSV")

    def test_source_history_rotates_new_unreviewed_sources_instead_of_same_top_three(self):
        from datetime import date
        older = "https://dati.veneto.it/SpodCkanApi/api/2/rest/dataset/"
        dataset_ids = [
            "c97582dd-d37d-4f1d-a1c5-b0b90188c651",
            "4afb27b6-e3a4-4f25-9dae-5c1fa925e4d9",
            "04bc0bfa-d895-49a9-a603-150234cc4ee9",
            "d305152b-ec6a-466e-b417-02316d603d0c",
            "5e0e619c-eb69-4a82-b2a4-532a01118c4c"
        ]
        sources = [source(f"veneto-{i}",older+d+".csv") for i,d in enumerate(dataset_ids)]
        registry = {"schema":1,"record_imports":0,"sources":sources}
        sample = (b"NOME;FIERA/MERCATO;DATA VALIDITA CONCESSIONE;"
                  b"DATA SCADENZA CONCESSIONE\n"
                  b"Mercato settimanale;MERCATO;01/01/2015;31/12/2030\n")
        seen=[]
        def fixture(url):
            seen.append(url)
            return sample,False
        first=survey(registry,fetch=fixture,reference_date=date(2026,10,12))
        self.assertEqual([x["id"] for x in first["reports"]],
                         ["veneto-0","veneto-1","veneto-2"])
        self.assertEqual(first["unreviewed_sources_remaining"],2)
        self.assertEqual(first["reports"][0]["schema_viability"],
                         "concession_registry_without_visit_schedule")
        self.assertEqual(first["imports"],0)
        second=survey(registry,fetch=fixture,previous=first,
                      reference_date=date(2026,10,13))
        self.assertEqual([x["id"] for x in second["reports"]][:2],
                         ["veneto-3","veneto-4"])
        self.assertEqual(second["unreviewed_sources_remaining"],0)
        self.assertEqual(len(second["reports"]),3)
        self.assertEqual(len(seen),6)
        self.assertEqual(second["probe_history"]["veneto-1"]["checked_date"],"2026-10-12")
        self.assertEqual(second["probe_history"]["veneto-3"]["checked_date"],"2026-10-13")
        self.assertTrue(all(r["adapter_enabled"] is False for r in second["reports"]))

    def test_offline_skip_preserves_bounded_prior_history(self):
        from datetime import date
        u="https://dati.veneto.it/SpodCkanApi/api/2/rest/dataset/4afb27b6-e3a4-4f25-9dae-5c1fa925e4d9.csv"
        source_entry=source("test",u)
        rg={"schema":1,"record_imports":0,"sources":[source_entry]}
        first=survey(rg,offline=True,reference_date=date(2026,10,12))
        self.assertEqual(first["reports"][0]["status"],"offline_skipped")
        second=survey(rg,offline=True,previous=first,
                      reference_date=date(2026,10,13))
        self.assertEqual(second["imports"],0)
        self.assertEqual(second["verified_event_count"],0)
        self.assertEqual(second["probe_history"]["test"]["checked_date"],"2026-10-13")

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
