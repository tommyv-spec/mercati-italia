"""Live source QA report: independent every publisher and preserves outages."""
from __future__ import annotations
import sys
import unittest
import copy
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from official_source_output_audit import run,validate,ALL_SOURCES,markdown
from official_source_output_gate import profile

TODAY=date(2026,10,18)


def row(source,n):
    p=profile(source)
    urls=p.get("source_pages") or ["https://opendata.comune.fi.it/page_dataset_show?id=mercati"]
    province={"lombardia":"MI","milano":"MI","bologna":"BO","corciano":"PG","firenze":"FI"}[source]
    city={"lombardia":"Pogliano Milanese","milano":"Milano","bologna":"Bologna",
          "corciano":"Corciano","firenze":"Firenze"}[source]
    x=[]
    for i in range(n):
        x.append({
            "slug":p["identity_prefix"]+str(i+1)+("-venerdi" if source=="lombardia" else ""),
            "regione":p["region"],"citta":city,"provincia":province,
            "nome":"Mercato "+str(i),"indirizzo":"Via Test "+str(i),
            "orario_testo":"08:00–12:30","lat":None,"lng":None,
            "position_quality":"sconosciuta","status":"non_confermato",
            "date":[],"date_quality":"sconosciuta","ricorrenza_testo":"Ogni venerdì",
            "verificato_il":"","aggiornato_il":"2026-10-13","url_fonte":urls[0],
        })
    return x


class OfficialSourceBatchAuditTests(unittest.TestCase):
    def test_five_sources_have_counted_passes_and_no_import_claims(self):
        seen=[]
        def fetch(sid,today):
            seen.append(sid)
            return row(sid,int(profile(sid)["min_records"]))
        result=run(fetch=fetch,today=TODAY)
        self.assertEqual(seen,list(ALL_SOURCES))
        self.assertEqual(result["source_batches_passed"],5)
        self.assertTrue(validate(result))
        self.assertEqual(result["catalog_updates"],0)
        self.assertEqual(result["market_openings_confirmed"],0)
        self.assertNotIn("Via Test ",str(result))
        self.assertIn("lombardia",markdown(result))

    def test_publisher_outage_retains_only_old_proof_labeled_not_current(self):
        def fetch(sid,today):
            return row(sid,int(profile(sid)["min_records"]))
        prior=run(fetch=fetch,today=TODAY)
        broken=run(fetch=lambda sid,today: (
            (_ for _ in ()).throw(OSError("offline")) if sid=="lombardia"
            else fetch(sid,today)),today=TODAY,previous=prior)
        self.assertEqual(broken["source_batches_passed"],4)
        state=next(s for s in broken["sources"] if s["source_id"]=="lombardia")
        self.assertEqual(state["status"],"publisher_unavailable_or_mapping_contract_changed")
        self.assertNotIn("current_publisher_gate",state)
        self.assertIn("last_good_publisher_gate",state)
        self.assertTrue(validate(broken))
        self.assertEqual(broken["catalog_updates"],0)

    def test_layout_change_quarantines_individual_source(self):
        def fetch(sid,today):
            data=row(sid,int(profile(sid)["min_records"]))
            if sid=="firenze":
                data[0]["url_fonte"]="https://invalid.example/market"
            return data
        result=run(fetch=fetch,today=TODAY)
        self.assertEqual(result["source_batches_passed"],4)
        f=next(s for s in result["sources"] if s["source_id"]=="firenze")
        self.assertEqual(f["failure_class"],"ValueError")
        self.assertFalse(f.get("current_publisher_gate"))
        self.assertTrue(validate(result))

    def test_offline_mode_and_previous_evidence_are_safe(self):
        prior=run(fetch=lambda sid,today: row(sid,int(profile(sid)["min_records"])),today=TODAY)
        result=run(today=TODAY,previous=prior,offline=True)
        self.assertEqual(result["source_batches_passed"],0)
        self.assertTrue(all(x["status"]=="offline_skipped" for x in result["sources"]))
        self.assertTrue(all(x.get("last_good_publisher_gate") is not None for x in result["sources"]))
        self.assertTrue(validate(result))

    def test_report_cannot_claim_a_new_market_or_fake_source_success(self):
        current=run(offline=True,today=TODAY)
        bad=copy.deepcopy(current)
        bad["market_openings_confirmed"]=1
        with self.assertRaises(ValueError):
            validate(bad)
        bad=copy.deepcopy(current)
        bad["sources"][0]["new_market_openings_confirmed"]=1
        with self.assertRaises(ValueError):
            validate(bad)
        with self.assertRaises(ValueError):
            run(previous={"schema":1,"research_only":False},offline=True,today=TODAY)

if __name__=="__main__":
    unittest.main()
