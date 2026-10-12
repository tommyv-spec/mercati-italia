import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_yield_audit import (
    audit, compare_bologna, BOLOGNA_URL, BOLOGNA_ID, ROMA_ID, PIEMONTE_ID,
)

TODAY=date(2026,10,12)

def market(sid,title,address,city="Bologna",day="settimanale - sabato",hours=""):
    return {
        "slug":sid,"nome":title,"regione":"Emilia-Romagna","citta":city,
        "indirizzo":address,"ricorrenza_testo":day,"orario_testo":hours,
        "url_fonte":"https://example.org/market",
        "date":[],"date_quality":"sconosciuta","verificato_il":"",
    }

def official(sid,title,address,day="settimanale - sabato"):
    return {
        **market(sid,title,address,day=day,hours="08:00-13:00 (fonte da verificare)"),
        "url_fonte":BOLOGNA_URL,
        "aggiornato_il":"2025-04-02",
    }

def fixture():
    base=[
        market("bo-open-legacy","Mercato Piazza Mercanti","Piazza Mercanti",hours=""),
        market("legacy-exact","Mercato Via Fiori","Via Fiori"),
        market("legacy-ambiguous","Mercato di Piazza Rosse","Piazza Rosse"),
        market("legacy-second","Mercato in Piazza Nuova","Piazza Nuova"),
    ]
    samples=[
        official("bo-open-001","Mercato Via Fiori","Via Fiori"),
        official("bo-open-002","Mercato diverso","Piazza Rosse"),
        official("bo-open-003","Mercato Via Sole","Via Sole"),
        official("bo-open-legacy","Mercato Piazza Mercanti","Piazza Mercanti"),
    ]
    return base,samples

def registry():
    def src(ident,title,bucket):
        return {"id":ident,"title":title,"organization":"Official publisher",
                "triage_class":bucket,"triage_reasons":[]}
    return {"schema":1,"record_imports":0,"sources":[
        src(BOLOGNA_ID,"Mercati e fiere","mixed_events_candidate"),
        src(ROMA_ID,"Dati sui Mercati Rionali","market_location_candidate"),
        src(PIEMONTE_ID,"Anagrafica mercati","general_market_candidate"),
        src("statistics","Mercati 2017 - vendite aggregate","aggregated_statistics"),
        src("stall-list","Posteggi mercati e fiere","mixed_events_candidate"),
    ]}

def municipalities(n):
    return {"review_only":True,"catalog_market_ids_preserved":n,
            "municipalities_without_catalog_listings":2988}

class YieldTests(unittest.TestCase):
    def test_verified_adapter_yield_is_strictly_review_only(self):
        base,source=fixture()
        frozen=copy.deepcopy(base)
        report=compare_bologna(base,source,TODAY)
        count=report["counts"]
        self.assertEqual(count["observed_source_rows"],4)
        self.assertEqual(count["new_ids_not_new_market_proof"],3)
        self.assertEqual(count["strong_exact_place_day_overlaps"],1)
        self.assertEqual(count["possible_duplicate_places_or_names"],1)
        self.assertEqual(count["possible_new_venues_unconfirmed"],1)
        self.assertEqual(count["same_id_already_published"],1)
        self.assertEqual(count["missing_hours_on_strong_match"],1)
        self.assertEqual(report["source_age_days"],558)
        self.assertEqual(report["records_imported"],0)
        self.assertEqual(report["events_confirmed"],0)
        self.assertEqual(base,frozen)

    def test_unknown_source_observations_are_not_zero(self):
        base,_=fixture()
        result=audit(base,registry(),municipalities(len(base)),
                     {"schema":1,"probe_history":{}},TODAY)
        self.assertEqual(result["sources_checked"],5)
        self.assertEqual(result["actual_source_samples_checked"],0)
        self.assertIsNone(result["priority_queue"][0]["actual_rows_examined"])
        self.assertIsNone(result["priority_queue"][0]["possible_distinct_venues"])
        self.assertEqual(result["sources_imported"],0)
        self.assertEqual(result["market_rows_edited"],0)

    def test_next_source_actions_bounded_and_unlicensed(self):
        base,source=fixture()
        result=audit(base,registry(),municipalities(len(base)),
                     {"schema":1,"probe_history":{}},TODAY,source)
        q=result["priority_queue"]
        self.assertEqual([x["source_id"] for x in q[:3]],
                         [BOLOGNA_ID,ROMA_ID,PIEMONTE_ID])
        self.assertTrue(all(x["market_entries_added"]==0 for x in q))
        self.assertTrue(all(x["license_needs_review"] for x in result["all_sources"]))
        excluded={x["source_id"]:x["stage"] for x in result["all_sources"]}
        self.assertEqual(excluded["statistics"],"statistics_not_events")
        self.assertEqual(excluded["stall-list"],"stalls_not_market_visits")
        self.assertEqual(result["markets_added"],0)

    def test_conflict_must_not_be_silently_promoted(self):
        base,source=fixture()
        bad=copy.deepcopy(source)
        bad[2]["date_quality"]="confermata"
        with self.assertRaisesRegex(ValueError,"Unapproved"):
            compare_bologna(base,bad,TODAY)
        bad=copy.deepcopy(source)
        bad[0]["aggiornato_il"]="2026-10-12"
        with self.assertRaisesRegex(ValueError,"Unapproved"):
            compare_bologna(base,bad,TODAY)
        bad=copy.deepcopy(source)
        bad[0]["url_fonte"]="https://example.invalid"
        with self.assertRaisesRegex(ValueError,"Unapproved"):
            compare_bologna(base,bad,TODAY)

    def test_duplicate_source_or_catalog_refused(self):
        base,source=fixture()
        with self.assertRaisesRegex(ValueError,"Invalid Bologna identity"):
            compare_bologna(base,source+[source[0]],TODAY)
        with self.assertRaisesRegex(ValueError,"Catalog ID collision"):
            compare_bologna(base+[base[0]],source,TODAY)

    def test_registry_count_and_integrity_gates(self):
        base,source=fixture()
        bad=registry()
        bad["record_imports"]=1
        with self.assertRaises(ValueError):
            audit(base,bad,municipalities(len(base)),{"schema":1},TODAY,source)
        bad=registry()
        bad["sources"].append(bad["sources"][0])
        with self.assertRaisesRegex(ValueError,"Repeated source"):
            audit(base,bad,municipalities(len(base)),{"schema":1},TODAY,source)
        bad=registry()
        with self.assertRaises(ValueError):
            audit(base,bad,municipalities(0),{"schema":1},TODAY,source)

if __name__=="__main__":
    unittest.main()
