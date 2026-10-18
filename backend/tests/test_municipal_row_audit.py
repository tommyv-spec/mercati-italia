import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from municipal_row_audit import (
    allowed, audit, make_catalog_url, profile_csv, select_catalog,
)

TODAY=date(2026,10,12)
PKG1="084aa29f-70fc-40e4-aea5-5f1f86f6a0c5"
PKG2="3a9703a1-3177-472d-8226-8440bba34b61"
RES1="13f722d5-d5d6-4a1a-966c-f6a557a33574"
RES2="b65de6bd-309e-452f-a18f-98563e5c4977"
URL1=f"https://opendata.boxxapps.com/dataset/{PKG1}/resource/{RES1}/download/7003_20261009_cm_fiere_mercati.csv"
URL2=f"https://opendata.boxxapps.com/dataset/{PKG2}/resource/{RES2}/download/7848_20261007_cm_posteggi_mercati.csv"

# Exact column types and date patterns observed in public 2026 municipal CSVs.
MINERBE = (
    "NOME_MERCATO,FIERA_MERCATO,ATTIVITA,DATA_VALIDITA_CONCESSIONE,DATA_SCADENZA_CONCESSIONE\r\n"
    "MERCATO DI MINERBE,MERCATO,MINERBE#1,26/08/2022,31/12/2032\r\n"
    "MERCATO DI MINERBE,MERCATO,MINERBE#2,30/11/2011,31/12/2024\r\n"
    "MERCATO DI MINERBE,MERCATO,MINERBE#3,30/11/2011,31/12/2024\r\n"
).encode()
CEREA = (
    "NOME_MERCATO,FIERA_MERCATO,GIORNO,INIZIO_PERIODO,FINE_PERIODO,TIPO_POSTEGGIO,TOTALE_POSTEGGI\r\n"
    "MERCATO SETTIMANALE,MERCATO,Nessun giorno,01/01/2011,31/12/2011,NON ALIMENTARE,100\r\n"
    "MERCATO SETTIMANALE,MERCATO,Nessun giorno,01/01/2018,31/12/2020,ALIMENTARE,16\r\n"
).encode()


def package(sid, url, title):
    return {
        "id":sid,"license_id":"CC-BY-4.0","private":False,
        "title":title,"modified":"2026-10-09",
        "publisher_name":"Comune di Test",
        "resources":[{
            "id":RES1 if sid==PKG1 else RES2, "format":"CSV",
            "last_modified":"2026-10-09", "url":url,
        }],
    }


class MunicipalRowAuditTests(unittest.TestCase):
    def test_real_recent_csv_has_old_vendor_concessions_not_29_markets(self):
        p=profile_csv(MINERBE,TODAY)
        self.assertEqual(p["source_rows_read"],3)
        self.assertEqual(p["distinct_market_names_not_new_markets"],1)
        self.assertEqual(p["expired_concession_rows"],2)
        self.assertEqual(p["source_kind"],"concessions_not_market_visits")
        self.assertEqual(p["markets_confirmed"],0)
        self.assertIs(p["market_import_permission"],False)

    def test_real_stall_history_cannot_create_future_market(self):
        p=profile_csv(CEREA,TODAY)
        self.assertEqual(p["historical_stall_rows"],2)
        self.assertEqual(p["explicit_valid_weekdays"],0)
        self.assertEqual(p["source_kind"],"historic_stall_capacity_not_market_visits")
        self.assertEqual(p["distinct_market_names_not_new_markets"],1)

    def test_actual_venue_calendar_schema_is_candidate_only(self):
        p=profile_csv(b"NOME_MERCATO,GIORNO,INDIRIZZO,ORARIO\nMercato Campagna,Martedi,Via Garibaldi 2,08:00-13:00\n",TODAY)
        self.assertEqual(p["source_kind"],"venue_schedule_review_candidate")
        self.assertEqual(p["rows_with_addresses"],1)
        self.assertEqual(p["rows_with_hours"],1)
        self.assertEqual(p["explicit_valid_weekdays"],1)
        self.assertFalse(p["market_import_permission"])

    def test_host_exact_path_and_query_allowlist_blocks_tricks(self):
        self.assertTrue(allowed(URL1))
        self.assertTrue(allowed(make_catalog_url(TODAY),metadata=True))
        for url in (
            "http://opendata.boxxapps.com/api/3/action/package_search?q=fiere+mercati&rows=15&start=0",
            "https://opendata.boxxapps.com.evil.net/dataset/a.csv",
            "https://opendata.boxxapps.com/other/bad.csv",
            "https://opendata.boxxapps.com/api/3/action/package_search?q=*&rows=1000&start=0",
            URL1+"?redirect=https://127.0.0.1",
            "https://opendata.boxxapps.com/dataset/../../private/test.csv",
        ):
            self.assertFalse(allowed(url,metadata=("/api/" in url)))

    def test_ckan_source_catalog_filters_untrusted_licenses_or_paths(self):
        bad=package(PKG1,URL1,"Fiere e mercati")
        bad["license_id"]="UNKNOWN"
        eligible=package(PKG2,URL2,"Posteggi mercati e fiere")
        chosen,total=select_catalog(json.dumps({"success":True,"result":{
            "count":87,"results":[bad,eligible]
        }}).encode())
        self.assertEqual(total,87)
        self.assertEqual(len(chosen),1)
        self.assertEqual(chosen[0]["id"],PKG2)

    def test_daily_network_stub_is_read_only_and_history_idempotent(self):
        dataset={
            "success":True,"result":{
                "count":87,"results":[package(PKG1,URL1,"Fiere e mercati"),
                                      package(PKG2,URL2,"Posteggi mercati e fiere")],
            }
        }
        requests=[]
        def fetch(url,*,metadata=False):
            requests.append((url,metadata))
            if metadata:return json.dumps(dataset).encode()
            return MINERBE if url==URL1 else CEREA if url==URL2 else b""
        result=audit(reference=TODAY,fetch=fetch)
        self.assertEqual(result["catalog_total"],87)
        self.assertEqual(len(result["sources"]),2)
        self.assertEqual(result["imports"],0)
        self.assertEqual(result["verified_events"],0)
        self.assertEqual(len(result["history"]),2)
        self.assertEqual(len(requests),3)
        second=audit(reference=TODAY,fetch=fetch,previous=result)
        self.assertEqual(second["imports"],0)
        self.assertEqual(len(second["history"]),2)

    def test_offline_never_calls_network(self):
        def should_not_fetch(*args,**kwargs):
            raise AssertionError("No network in offline mode")
        r=audit(reference=TODAY,offline=True,fetch=should_not_fetch)
        self.assertEqual(r["sources"],[])
        self.assertTrue(r["review_only"])
        self.assertEqual(r["imports"],0)

    def test_malformed_csv_and_source_metadata_fail_closed(self):
        for value in (b"", b"A,B\nhello,there\n", b"NOME_MERCATO,NOME_MERCATO\nx,y\n"):
            with self.assertRaises(ValueError):
                profile_csv(value,TODAY)
        with self.assertRaises(ValueError):
            select_catalog(b'{"success":false,"result":{}}')


if __name__=="__main__":
    unittest.main()
