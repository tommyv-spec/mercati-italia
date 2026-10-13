import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_contract_activation import activate,validate_admissions,validate_release,verify_static
from source_lifecycle import digest
from test_source_corciano import DATA

ROOT=Path(__file__).resolve().parents[1]/"data"
CONTRACT=json.loads((ROOT/"market-source-contracts.json").read_text("utf-8"))
ACTIVE_REGISTRY=json.loads((ROOT/"approved-source-admissions.json").read_text("utf-8"))
EMPTY=copy.deepcopy(ACTIVE_REGISTRY)
EMPTY["approvals"]=[]
NO_ACTIVE_CONTRACT=copy.deepcopy(CONTRACT)
NO_ACTIVE_CONTRACT["raw_profiles"][0].update({
    "publication_mode":"shadow_only",
    "legal_reuse_reviewed":False,
    "max_new_ids_per_run":0,
})
RAW=CONTRACT["raw_profiles"][0]
TODAY=date(2026,10,13)
BLOB=DATA.encode("utf-8")


def enabled_fixture():
    cfg=copy.deepcopy(CONTRACT)
    p=cfg["raw_profiles"][0]
    p["publication_mode"]="approved_dev_only"
    p["legal_reuse_reviewed"]=True
    p["max_new_ids_per_run"]=4
    proof={
       "schema":1,"mode":"approved_dev_only","source_id":p["id"],
       "reviewed_profile_sha256":digest(p),
       "publisher_license_evidence_url":p["attribution_url"],
       "identity_granularity":"market_venue",
       "reviewed_on":"2026-10-13",
       "max_new_ids":4,"source_record_kind":"market_venue",
       "source_specific_geo_approval":False,
    }
    reg=copy.deepcopy(EMPTY);reg["approvals"]=[proof]
    return cfg,reg


def far_baseline():
    return [{"slug":"unrelated-market-firenze","nome":"Mercato centrale",
             "citta":"Firenze","regione":"Toscana","provincia":"FI",
             "indirizzo":"Piazza del Mercato","status":"non_confermato"}]


class GenericActivationTests(unittest.TestCase):
    def test_defaults_to_no_approved_sources_and_no_network_requests(self):
        called=[]
        old=far_baseline()
        res,report=activate(NO_ACTIVE_CONTRACT,EMPTY,old,today=TODAY,
                            fetch=lambda url:called.append(url))
        self.assertEqual(res,old)
        self.assertEqual(called,[])
        self.assertEqual(report["source_contracts_active"],0)
        self.assertEqual(report["new_market_ids"],[])
        self.assertTrue(validate_release(old,res,report,NO_ACTIVE_CONTRACT,EMPTY)["release_safe"])

    def test_real_publisher_admission_reconciles_existing_catalog_without_duplicate_additions(self):
        # Municipal bytes are a fixed offline fixture, not fetched by CI.
        # Approval is source-level; a duplicate under another source stays held.
        from merge_catalog import load_existing
        base=load_existing(Path(__file__).resolve().parents[2]/'public/data/v1/manifest.json')
        self.assertEqual(len(base),13784)
        self.assertEqual(ACTIVE_REGISTRY['approvals'][0]['max_new_ids'],2)
        before=copy.deepcopy(base)
        result,report=activate(CONTRACT,ACTIVE_REGISTRY,base,today=TODAY,
                               fetch=lambda url:(BLOB,False))
        self.assertEqual(result,before)
        self.assertEqual(report['source_contracts_active'],1)
        self.assertEqual(report['new_market_ids'],[])
        self.assertEqual(report['status_counts']['approved_sources_reconciled'],1)
        self.assertEqual(report['per_source'][RAW['id']]['source_eligible_candidates'],0)
        self.assertTrue(validate_release(base,result,report,CONTRACT,ACTIVE_REGISTRY)['release_safe'])
        replay,again=activate(CONTRACT,ACTIVE_REGISTRY,result,today=TODAY,
                              fetch=lambda url:(BLOB,False))
        self.assertEqual(result,replay)
        self.assertEqual(again['new_market_ids'],[])

    def test_source_level_approval_can_admit_four_distinct_ids_as_one_contract(self):
        cfg,reg=enabled_fixture()
        fetches=[]
        old=far_baseline()
        frozen=copy.deepcopy(old)
        def fetch(url):
            fetches.append(url)
            return BLOB,False
        output,report=activate(cfg,reg,old,today=TODAY,fetch=fetch)
        self.assertEqual(len(fetches),1)
        self.assertEqual(len(output),len(old)+4)
        self.assertEqual(old,frozen)
        self.assertEqual(report["source_contracts_active"],1)
        self.assertEqual(len(report["new_market_ids"]),4)
        self.assertEqual(report["status_counts"]["new_source_venues_staged_for_DEV"],4)
        cert=validate_release(old,output,report,cfg,reg)
        self.assertTrue(cert["release_safe"])
        self.assertEqual(cert["source_approved_added_venue_id_count"],4)
        self.assertTrue(all(not item["verificato_il"] and item["lat"] is None
                            and item["date_quality"]=="sconosciuta" for item in output[1:]))
        replay,second=activate(cfg,reg,output,today=TODAY,fetch=fetch)
        self.assertEqual(replay,output)
        self.assertEqual(second["new_market_ids"],[])
        self.assertTrue(validate_release(output,replay,second,cfg,reg)["release_safe"])

    def test_approved_source_replays_remaining_venues_across_scheduled_cycles(self):
        cfg,reg=enabled_fixture()
        reg["approvals"][0]["max_new_ids"]=2
        old=far_baseline()
        source_fetch=lambda url:(BLOB,False)
        first,one=activate(cfg,reg,old,today=TODAY,fetch=source_fetch)
        self.assertEqual(len(first)-len(old),2)
        self.assertEqual(one["per_source"][RAW["id"]]["deferred_candidate_count"],2)
        self.assertEqual(one["status_counts"]["eligible_venues_deferred_to_next_run"],2)
        self.assertTrue(validate_release(old,first,one,cfg,reg)["release_safe"])
        second,two=activate(cfg,reg,first,today=TODAY,fetch=source_fetch)
        self.assertEqual(len(second)-len(first),2)
        self.assertEqual(two["per_source"][RAW["id"]]["deferred_candidate_count"],0)
        self.assertTrue(validate_release(first,second,two,cfg,reg)["release_safe"])
        third,three=activate(cfg,reg,second,today=TODAY,fetch=source_fetch)
        self.assertEqual(third,second)
        self.assertEqual(three["new_market_ids"],[])
        self.assertTrue(validate_release(second,third,three,cfg,reg)["release_safe"])
        bogus=copy.deepcopy(one)
        bogus["per_source"][RAW["id"]]["deferred_candidate_count"]=10
        with self.assertRaisesRegex(ValueError,"quota or lost deferred"):
            validate_release(old,first,bogus,cfg,reg)
        bogus=copy.deepcopy(one)
        bogus["per_source"][RAW["id"]]["status"]="offline_no_source_inference"
        with self.assertRaisesRegex(ValueError,"Unavailable/offline"):
            validate_release(old,first,bogus,cfg,reg)

    def test_offline_or_source_outage_never_closes_historical_market(self):
        cfg,reg=enabled_fixture()
        old=far_baseline()
        off,off_report=activate(cfg,reg,old,today=TODAY,offline=True,
                                fetch=lambda url:(_ for _ in ()).throw(AssertionError("NO FETCH")))
        self.assertEqual(off,old)
        self.assertEqual(off_report["status_counts"]["offline_skipped"],1)
        bad,report=activate(cfg,reg,old,today=TODAY,
                            fetch=lambda url:(_ for _ in ()).throw(OSError("unavailable")))
        self.assertEqual(bad,old)
        self.assertEqual(report["status_counts"]["publisher_sources_held"],1)
        self.assertEqual(report["per_source"][RAW["id"]]["status"],"publisher_source_held_for_review")

    def test_malformed_csv_held_and_safe_prior_ids_preserved(self):
        cfg,reg=enabled_fixture()
        old=far_baseline()
        damaged=BLOB.replace(b";long;lat;geopoint",b";long;latitude;geopoint")
        created,report=activate(cfg,reg,old,today=TODAY,
                                fetch=lambda url:(damaged,False))
        self.assertEqual(created,old)
        self.assertEqual(report["status_counts"]["publisher_sources_held"],1)
        self.assertEqual(report["new_market_ids"],[])
        self.assertTrue(validate_release(old,created,report,cfg,reg)["release_safe"])

    def test_publisher_overlap_blocks_generic_duplicate_without_deleting_original(self):
        cfg,reg=enabled_fixture()
        old=far_baseline()+[{
            "slug":"older-public-listing","nome":"Mercato settimanale di Corciano",
            "citta":"Corciano","regione":"Umbria",
            "indirizzo":"Piazza Caduti","ricorrenza_testo":"settimanale - mercoledì"
        }]
        result,report=activate(cfg,reg,old,today=TODAY,
                               fetch=lambda url:(BLOB,False))
        self.assertEqual(len(result),len(old)+3)
        self.assertNotIn("pg-corciano-mercato-di-corciano",report["new_market_ids"])
        self.assertTrue(validate_release(old,result,report,cfg,reg)["release_safe"])

    def test_publisher_approved_full_static_export_enforces_day_labels_and_no_navigation(self):
        from tempfile import TemporaryDirectory
        from export_static import export
        from recurrence_refresh import refresh_records
        cfg,reg=enabled_fixture()
        old=far_baseline()
        new,report=activate(cfg,reg,old,today=TODAY,fetch=lambda url:(BLOB,False))
        updated,_=refresh_records(new,TODAY,120,540)
        with TemporaryDirectory() as td:
            path=Path(td)/"public/data/v1"
            export(updated,path,today=TODAY,min_count=1)
            certificate=verify_static(path/"manifest.json",report,cfg,reg,TODAY)
            self.assertTrue(certificate["release_safe"])
            self.assertEqual(certificate["new_source_venue_ids_verified"],4)
            self.assertEqual(certificate["source_weekly_forecasts_only"],4)
            self.assertEqual(certificate["navigation_holds_in_index"],4)
            self.assertEqual(certificate["new_precise_coordinates"],0)

    def test_source_admission_registry_strict_and_license_required(self):
        cfg,reg=enabled_fixture()
        invalid=copy.deepcopy(reg)
        invalid["approvals"][0]["source_id"]="not-allowed"
        with self.assertRaisesRegex(ValueError,"source import identity"):
            validate_admissions(cfg,invalid)
        invalid=copy.deepcopy(reg)
        invalid["approvals"].append(invalid["approvals"][0])
        with self.assertRaisesRegex(ValueError,"source import identity"):
            validate_admissions(cfg,invalid)
        invalid=copy.deepcopy(reg)
        invalid["approvals"][0]["max_new_ids"]="100"
        with self.assertRaisesRegex(ValueError,"growth allowance"):
            validate_admissions(cfg,invalid)
        invalid=copy.deepcopy(cfg)
        invalid["raw_profiles"][0]["legal_reuse_reviewed"]=False
        with self.assertRaisesRegex(ValueError,"Raw source"):
            validate_admissions(invalid,reg)
        with self.assertRaisesRegex(ValueError,"approval must match"):
            validate_admissions(cfg,EMPTY)

    def test_independent_guard_rejects_added_id_and_original_record_mutation(self):
        cfg,reg=enabled_fixture();old=far_baseline()
        output,summary=activate(cfg,reg,old,today=TODAY,fetch=lambda url:(BLOB,False))
        damaged=copy.deepcopy(output)
        damaged[0]["indirizzo"]="Via Nuova"
        with self.assertRaisesRegex(ValueError,"Independent generic"):
            validate_release(old,damaged,summary,cfg,reg)
        damaged=copy.deepcopy(output)
        damaged.append(copy.deepcopy(damaged[-1]))
        with self.assertRaisesRegex(ValueError,"Independent generic"):
            validate_release(old,damaged,summary,cfg,reg)
        damaged=copy.deepcopy(summary);damaged["new_market_openings_confirmed"]=1
        with self.assertRaisesRegex(ValueError,"Independent generic"):
            validate_release(old,output,damaged,cfg,reg)
        # A source-level admission cannot silently change the URL or add GPS
        # to any new venue after the source was accepted.
        tampered=copy.deepcopy(output)
        tampered[1]["url_fonte"]="https://unreviewed.example/"
        with self.assertRaisesRegex(ValueError,"Unsafe field"):
            validate_release(old,tampered,summary,cfg,reg)
        tampered=copy.deepcopy(output)
        tampered[1]["lat"]=43.12
        with self.assertRaisesRegex(ValueError,"Unsafe field"):
            validate_release(old,tampered,summary,cfg,reg)


if __name__=="__main__":
    unittest.main()
