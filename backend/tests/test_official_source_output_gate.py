"""Regression suite: a wrong publisher column, date or identity cannot enter DEV."""
from __future__ import annotations

import copy
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from official_source_output_gate import inspect,verify_gate,profile
from autopilot import retrieve_sources,source_feed

TODAY=date(2026,10,18)
COUNTS={"milano":85,"firenze":3,"lombardia":1100,"bologna":48,"corciano":4}
URLS={
 "milano":"https://dati.comune.milano.it/dataset/ds291-economia-mercati-settimanali-scoperti",
 "firenze":"https://www.feelflorence.it/it/mercati/mercato-central",
 "lombardia":"https://www.dati.lombardia.it/d/68zx-njaw",
 "bologna":"https://opendata.comune.bologna.it/explore/dataset/mercati-e-fiere/",
 "corciano":"https://comune.corciano.pg.it/area_letturaDocumento/29645/pagsistema.html",
}
REGIONS={"milano":("Lombardia","MI","Milano"),
         "firenze":("Toscana","FI","Firenze"),
         "lombardia":("Lombardia","PV","Pavia"),
         "bologna":("Emilia-Romagna","BO","Bologna"),
         "corciano":("Umbria","PG","Corciano")}
PREFIX={"milano":"mi-mss-","firenze":"fi-feelflorence-",
        "lombardia":"lo-mercap-","bologna":"bo-open-",
        "corciano":"pg-corciano-"}


def source_rows(sid,n=None):
    n=n or COUNTS[sid]
    region,province,city=REGIONS[sid]
    out=[]
    for i in range(n):
        row={
            "slug":PREFIX[sid]+str(i+1)+("-venerdi" if sid=="lombardia" else ""),
            "regione":region,"provincia":province,"citta":city,
            "nome":"Mercato comunale prova "+str(i+1),
            "indirizzo":"Via Roma "+str(i) if sid!="milano" else "",
            "orario_testo":"08:00–13:00 (da verificare)",
            "lat":None,"lng":None,"position_quality":"sconosciuta",
            "ricorrenza_testo":"Ogni venerdì",
            "date":[],
            "date_quality":"sconosciuta",
            "status":"non_confermato","verificato_il":"",
            "fonte":"Test fonte comunale",
            "url_fonte":URLS[sid],
            "aggiornato_il":"2026-10-13",
        }
        out.append(row)
    return out


class CrossPublisherOfficialOutputTests(unittest.TestCase):
    def test_all_five_existing_adapters_have_frozen_independent_gate(self):
        for sid,n in COUNTS.items():
            with self.subTest(publisher=sid):
                rows=source_rows(sid)
                unchanged=copy.deepcopy(rows)
                report=inspect(sid,rows,today=TODAY)
                self.assertTrue(verify_gate(report))
                self.assertEqual(rows,unchanged)
                self.assertEqual(report["rows"],n)
                self.assertEqual(report["market_confirmations"],0)
                self.assertEqual(report["catalog_updates"],0)
                self.assertEqual(report["source_prefix"],PREFIX[sid])
                self.assertEqual(len(report["identity_sha256"]),64)
                self.assertNotIn("Mercato comunale prova",str(report))
                self.assertNotIn("Via Roma",str(report))

    def test_milan_missing_address_is_not_silently_fabricated(self):
        rows=source_rows("milano")
        report=inspect("milano",rows,today=TODAY)
        self.assertEqual(report["field_coverage"]["nonempty_address"],0)
        self.assertEqual(report["market_confirmations"],0)
        self.assertTrue(all(x["indirizzo"]=="" for x in rows))
        # The official DS291 JSON really has no street column. Refusing an
        # address guessed from "MERCATO" is the correct behavior.

    def test_malformed_publisher_identity_street_city_or_host_is_rejected(self):
        original=source_rows("milano")
        changes=[
            ("slug","lo-mercap-1-venerdi"),
            ("url_fonte","https://evil.example/markets"),
            ("url_fonte","https://dati.comune.milano.it@evil.example/mercati"),
            ("regione","Piemonte"),
            ("provincia","TO"),
            ("citta"," "),
            ("indirizzo",["via","X"]),
            ("orario_testo",{"start":"08:00"}),
        ]
        for field,value in changes:
            with self.subTest(field=field,value=value):
                rows=copy.deepcopy(original)
                rows[0][field]=value
                with self.assertRaises(ValueError):
                    inspect("milano",rows,today=TODAY)

    def test_no_human_confirmation_or_precise_unreviewed_gps(self):
        for field,value in [
            ("status","attivo"),("verificato_il","2026-10-18"),
            ("date_quality","confermata"),
            ("position_quality","precisa"),
            ("lat",0),("lng",0),
        ]:
            rows=source_rows("lombardia")
            rows[0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                inspect("lombardia",rows,today=TODAY)
        rows=source_rows("firenze")
        rows[0].update({"lat":43.78,"lng":11.25,"position_quality":"precisa"})
        self.assertEqual(inspect("firenze",rows,today=TODAY)
                         ["field_coverage"]["source_coordinates_present"],1)

    def test_day_slugs_and_forecast_dates_must_agree_with_declared_weekdays(self):
        rows=source_rows("lombardia")
        rows[0]["ricorrenza_testo"]="Ogni martedì"
        with self.assertRaisesRegex(ValueError,"weekday"):
            inspect("lombardia",rows,today=TODAY)
        rows=source_rows("lombardia")
        rows[0]["date"]=["2026-10-19"]  # Monday, not Friday.
        rows[0]["date_quality"]="prevista"
        with self.assertRaisesRegex(ValueError,"weekday"):
            inspect("lombardia",rows,today=TODAY)
        rows[0]["date"]=["2026-10-23"]
        self.assertEqual(inspect("lombardia",rows,today=TODAY)
                         ["field_coverage"]["forecasted_records"],1)

    def test_inconsistent_dataset_date_or_duplicate_id_rejects_all(self):
        rows=source_rows("firenze")
        rows[1]["aggiornato_il"]="2026-10-12"
        with self.assertRaisesRegex(ValueError,"mixes"):
            inspect("firenze",rows,today=TODAY)
        rows=source_rows("firenze")
        rows[1]["slug"]=rows[0]["slug"]
        with self.assertRaisesRegex(ValueError,"duplicated"):
            inspect("firenze",rows,today=TODAY)
        rows=source_rows("lombardia")
        rows[0]["aggiornato_il"]="2027-10-13"
        with self.assertRaisesRegex(ValueError,"future"):
            inspect("lombardia",rows,today=TODAY)
        rows=source_rows("corciano")
        rows[0]["date"]=["2026-10-23"]
        with self.assertRaisesRegex(ValueError,"quality"):
            inspect("corciano",rows,today=TODAY)

    def test_field_coverage_and_source_id_drift_requires_review(self):
        base=source_rows("milano")
        # Official existing Milan batch really has zero addresses. The
        # previous report must not invent any claim to the contrary.
        first=inspect("milano",base,today=TODAY)
        again=inspect("milano",base,today=TODAY,previous=first)
        self.assertEqual(first,again)
        changed=copy.deepcopy(base)
        changed[0]["slug"]="mi-mss-new"
        with self.assertRaisesRegex(ValueError,"identities changed"):
            inspect("milano",changed,today=TODAY,previous=first)
        changed=copy.deepcopy(base)
        changed[0]["aggiornato_il"]="2026-10-17"
        with self.assertRaisesRegex(ValueError,"mixes"):
            inspect("milano",changed,today=TODAY,previous=first)
        # Altering a header mapping and silently blanking previously
        # populated values is a major publisher field regression.
        original=source_rows("lombardia")
        old=inspect("lombardia",original,today=TODAY)
        changed=copy.deepcopy(original)
        for row in changed[:550]:
            row["orario_testo"]=""
        with self.assertRaisesRegex(ValueError,"column completeness regressed"):
            inspect("lombardia",changed,today=TODAY,previous=old)

    def test_only_approved_source_profiles_allowed(self):
        with self.assertRaisesRegex(ValueError,"Unreviewed"):
            profile("happings")
        with self.assertRaisesRegex(ValueError,"Unreviewed"):
            inspect("eventiesagre",[],today=TODAY)

    def test_enabled_autopilot_checks_both_live_results_and_resume_cache(self):
        rows=source_rows("milano")
        config={"sources":[{
            "id":"milano","enabled":True,"official":True,
            "min_records":85,"max_records":1800,"license":"CC BY 4.0",
        }]}
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)
            with patch("autopilot.source_feed", return_value=rows):
                batch,status=retrieve_sources(config,out,TODAY,False,False)
            self.assertEqual(len(batch),85)
            self.assertTrue(verify_gate(status["milano"]["normalized_publisher_output_gate"]))
            self.assertEqual(status["milano"]["status"],"retrieved")
            with patch("autopilot.source_feed",side_effect=AssertionError("must use cache")):
                batch,status=retrieve_sources(config,out,TODAY,False,True)
            self.assertEqual(len(batch),85)
            self.assertEqual(status["milano"]["status"],"resumed_checkpoint")
            self.assertTrue(verify_gate(status["milano"]["normalized_publisher_output_gate"]))
            # Deliberately corrupt checkpoint: the resumed run MUST reject.
            cache=out/"sources"/"milano.json"
            entries=json.loads(cache.read_text("utf-8"))
            entries[0]["url_fonte"]="https://evil.example"
            cache.write_text(json.dumps(entries),"utf-8")
            with self.assertRaisesRegex(ValueError,"provenance"):
                retrieve_sources(config,out,TODAY,False,True)

if __name__=="__main__":
    unittest.main()
