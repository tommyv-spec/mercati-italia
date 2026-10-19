import copy
import json
import sys
import unittest
from datetime import date, timedelta
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
for item in NO_ACTIVE_CONTRACT["raw_profiles"]:
    item.update({
        "publication_mode":"shadow_only",
        "legal_reuse_reviewed":False,
        "max_new_ids_per_run":0,
    })
RAW=CONTRACT["raw_profiles"][0]
TODAY=date(2026,10,13)
BLOB=DATA.encode("utf-8")


def fixture_activate(*args, **kwargs):
    # These fixed municipal bytes simulate a read on the explicit fixture day.
    kwargs.setdefault("read_on", kwargs.get("today", TODAY))
    return activate(*args, **kwargs)


def enabled_fixture():
    cfg=copy.deepcopy(CONTRACT)
    cfg["raw_profiles"]=cfg["raw_profiles"][:1]
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
        res,report=fixture_activate(NO_ACTIVE_CONTRACT,EMPTY,old,today=TODAY,
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
        # Daily DEV admissions grow this catalog. Test the source identities,
        # not a one-time national record count.
        self.assertGreaterEqual(len(base),13784)
        self.assertEqual(len({row['slug'] for row in base}),len(base))
        self.assertEqual(ACTIVE_REGISTRY['approvals'][0]['max_new_ids'],2)
        before=copy.deepcopy(base)
        single=copy.deepcopy(CONTRACT)
        single["raw_profiles"]=single["raw_profiles"][:1]
        registry=copy.deepcopy(ACTIVE_REGISTRY)
        registry["approvals"]=registry["approvals"][:1]
        result,report=fixture_activate(single,registry,base,today=TODAY,
                               fetch=lambda url:(BLOB,False))
        self.assertEqual([r["slug"] for r in result],[r["slug"] for r in before])
        for prior,observed in zip(before,result):
            changed={k for k in set(prior)|set(observed) if prior.get(k)!=observed.get(k)}
            self.assertLessEqual(changed,{"riscontri_campi","fonte_letta_il","fonte_aggiornata_il"})
        self.assertEqual(report['source_contracts_active'],1)
        self.assertEqual(report['new_market_ids'],[])
        self.assertEqual(report['status_counts']['approved_sources_reconciled'],1)
        self.assertEqual(report['per_source'][RAW['id']]['source_eligible_candidates'],0)
        self.assertTrue(validate_release(base,result,report,single,registry)['release_safe'])
        replay,again=fixture_activate(single,registry,result,today=TODAY,
                              fetch=lambda url:(BLOB,False))
        self.assertEqual(result,replay)
        self.assertEqual(again['new_market_ids'],[])

    def test_two_live_fixture_cycles_change_managed_fields_through_static_export(self):
        from tempfile import TemporaryDirectory
        from export_static import export
        from merge_catalog import load_existing
        from recurrence_refresh import refresh_records
        cfg,reg=enabled_fixture()
        first,one=fixture_activate(cfg,reg,far_baseline(),today=TODAY,fetch=lambda url:(BLOB,False))
        with TemporaryDirectory() as td:
            path=Path(td)/"public/data/v1"
            projected,_=refresh_records(first,TODAY,120,540)
            export(projected,path,today=TODAY,min_count=1,preserve_ids=set(one["new_market_ids"]))
            baseline=load_existing(path/"manifest.json")
            altered=BLOB.replace(b";CADUTI;3;1;07:30;14:00;",b";NUOVA SEDE;3;1;08:00;13:00;")
            tomorrow=TODAY+timedelta(days=1)
            updated,two=fixture_activate(cfg,reg,baseline,today=tomorrow,fetch=lambda url:(altered,False))
            self.assertEqual(two["updated_market_ids"],["pg-corciano-mercato-di-corciano"])
            self.assertEqual(two["old_market_fields_changed"],2)
            self.assertTrue(validate_release(baseline,updated,two,cfg,reg)["release_safe"])
            projected,_=refresh_records(updated,tomorrow,120,540)
            export(projected,path,today=tomorrow,min_count=1,
                   preserve_ids=set(two["evidence_updated_market_ids"]))
            proof=verify_static(path/"manifest.json",two,cfg,reg,tomorrow)
            self.assertTrue(proof["release_safe"])
            self.assertEqual(proof["existing_source_fields_updated"],2)
            final=load_existing(path/"manifest.json")
            selected=next(r for r in final if r["slug"]=="pg-corciano-mercato-di-corciano")
            self.assertEqual(selected["indirizzo"],"Piazza Nuova Sede, Corciano")
            self.assertEqual(selected["riscontri_campi"][0]["gestore_campi"],"source_contract_ingest")
            self.assertTrue(selected["riscontri_campi"][0]["versioni_precedenti"])

    def test_managed_update_guard_rejects_unreported_field_receipt_or_identity_change(self):
        cfg,reg=enabled_fixture()
        first,_=fixture_activate(cfg,reg,far_baseline(),today=TODAY,fetch=lambda url:(BLOB,False))
        tomorrow=TODAY+timedelta(days=1)
        blob=BLOB.replace(b";CADUTI;",b";NUOVA SEDE;")
        updated,report=fixture_activate(cfg,reg,first,today=tomorrow,fetch=lambda url:(blob,False))
        mid="pg-corciano-mercato-di-corciano"
        for field,value in (("nome","Mercato alterato"),("indirizzo","Sede non dichiarata"),
                            ("verificato_il",tomorrow.isoformat()),("riscontri_campi",[])):
            corrupted=copy.deepcopy(updated)
            next(r for r in corrupted if r["slug"]==mid)[field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                validate_release(first,corrupted,report,cfg,reg)
        corrupted=copy.deepcopy(report)
        next(p for p in corrupted["per_source"][RAW["id"]]["updates"]
             if p["slug"]==mid)["changed_fields"]={}
        with self.assertRaises(ValueError):
            validate_release(first,updated,corrupted,cfg,reg)

    def test_resume_reuses_exact_bytes_and_original_read_date_without_fetch(self):
        from tempfile import TemporaryDirectory
        cfg,reg=enabled_fixture()
        old=far_baseline()
        calls=[]
        with TemporaryDirectory() as td:
            first,one=fixture_activate(cfg,reg,old,today=TODAY,source_cache=td,
                                      fetch=lambda url:(calls.append(url) or BLOB,False))
            resumed,two=fixture_activate(cfg,reg,old,today=TODAY,source_cache=td,resume=True,
                                        read_on=TODAY+timedelta(days=1),
                                        fetch=lambda url:(_ for _ in ()).throw(AssertionError("NO NETWORK")))
            self.assertEqual(len(calls),1)
            self.assertEqual(first,resumed)
            self.assertEqual(two["per_source"][RAW["id"]]["source_read_on"],TODAY.isoformat())
            self.assertEqual(two["per_source"][RAW["id"]]["source_read_mode"],"resumed_checkpoint")
            offline,_=fixture_activate(cfg,reg,old,today=TODAY,source_cache=td,resume=True,offline=True,
                                      fetch=lambda url:(_ for _ in ()).throw(AssertionError("NO NETWORK")))
            self.assertEqual(offline,first)
            again,_=fixture_activate(cfg,reg,old,today=TODAY,source_cache=td,
                                    fetch=lambda url:(_ for _ in ()).throw(AssertionError("NO DOUBLE FETCH")))
            self.assertEqual(again,first)

    def test_resume_missing_or_tampered_snapshot_never_refetches(self):
        from tempfile import TemporaryDirectory
        cfg,reg=enabled_fixture()
        old=far_baseline()
        no_fetch=lambda url:(_ for _ in ()).throw(AssertionError("NO NETWORK"))
        with TemporaryDirectory() as td:
            output,report=fixture_activate(cfg,reg,old,today=TODAY,source_cache=td,resume=True,fetch=no_fetch)
            self.assertEqual(output,old)
            self.assertEqual(report["per_source"][RAW["id"]]["status"],"resume_checkpoint_missing")
            fixture_activate(cfg,reg,old,today=TODAY,source_cache=td,fetch=lambda url:(BLOB,False))
            cache=Path(td)/(digest(cfg["raw_profiles"][0]["resource_url"])+".json")
            evidence=json.loads(cache.read_text())
            evidence["sha256"]="0"*64
            cache.write_text(json.dumps(evidence))
            output,report=fixture_activate(cfg,reg,old,today=TODAY,source_cache=td,resume=True,fetch=no_fetch)
            self.assertEqual(output,old)
            self.assertEqual(report["per_source"][RAW["id"]]["status"],"publisher_source_held_for_review")

    def test_resume_rejects_baseline_contract_certificate_or_reference_drift(self):
        from tempfile import TemporaryDirectory
        cfg,reg=enabled_fixture()
        old=far_baseline()
        with TemporaryDirectory() as td:
            fixture_activate(cfg,reg,old,today=TODAY,source_cache=td,fetch=lambda url:(BLOB,False))
            other=copy.deepcopy(old);other[0]["nome"]="Altro nome"
            cases=[(cfg,reg,other,TODAY),(cfg,reg,old,TODAY+timedelta(days=1))]
            new_cfg=copy.deepcopy(cfg);new_cfg["raw_profiles"][0]["notes"]+=" fixture"
            new_reg=copy.deepcopy(reg)
            new_reg["approvals"][0]["reviewed_profile_sha256"]=digest(new_cfg["raw_profiles"][0])
            cases.append((new_cfg,new_reg,old,TODAY))
            new_reg=copy.deepcopy(reg);new_reg["approvals"][0]["max_new_ids"]=2
            cases.append((cfg,new_reg,old,TODAY))
            for cfg_,reg_,base_,day_ in cases:
                with self.assertRaisesRegex(ValueError,"Cannot resume"):
                    fixture_activate(cfg_,reg_,base_,today=day_,source_cache=td,resume=True,
                                     fetch=lambda url:(_ for _ in ()).throw(AssertionError("NO NETWORK")))

    def test_unavailable_other_approved_source_does_not_block_managed_updates(self):
        from http.client import IncompleteRead
        cfg,reg=enabled_fixture()
        first,_=fixture_activate(cfg,reg,far_baseline(),today=TODAY,fetch=lambda url:(BLOB,False))
        cfg["raw_profiles"].append(copy.deepcopy(CONTRACT["raw_profiles"][1]))
        reg["approvals"].append(copy.deepcopy(ACTIVE_REGISTRY["approvals"][1]))
        changed=BLOB.replace(b";CADUTI;",b";NUOVA SEDE;")
        def fetch(url):
            if "bologna" in url:
                raise IncompleteRead(b"",100)
            return changed,False
        result,report=fixture_activate(cfg,reg,first,today=TODAY+timedelta(days=1),fetch=fetch)
        self.assertEqual(len(result),len(first))
        self.assertEqual(report["old_market_fields_changed"],1)
        self.assertEqual(report["status_counts"]["publisher_sources_held"],1)
        self.assertEqual(report["status_counts"]["approved_sources_reconciled"],1)

    def test_held_legacy_conflict_retires_only_contradicted_source_claim(self):
        from field_evidence import field_states
        from export_static import export
        from tempfile import TemporaryDirectory
        cfg,reg=enabled_fixture()
        original,_=fixture_activate(cfg,reg,far_baseline(),today=TODAY,fetch=lambda url:(BLOB,False))
        mid="pg-corciano-mercato-di-corciano"
        target=next(r for r in original if r["slug"]==mid)
        primary=target["riscontri_campi"][0]
        primary.pop("campi_gestiti");primary.pop("gestore_campi")
        before=copy.deepcopy(original)
        changed=BLOB.replace(b";CADUTI;",b";NUOVA SEDE;")
        tomorrow=TODAY+timedelta(days=1)
        result,report=fixture_activate(cfg,reg,before,today=tomorrow,fetch=lambda url:(changed,False))
        self.assertEqual(before,original)
        after=next(r for r in result if r["slug"]==mid)
        self.assertEqual(after["indirizzo"],target["indirizzo"])
        self.assertEqual(report["old_market_fields_changed"],0)
        self.assertEqual(report["updated_market_ids"],[])
        self.assertEqual(report["evidence_updated_market_ids"],[mid])
        self.assertEqual(report["status_counts"]["source_evidence_retirements"],1)
        disposition=report["per_source"][RAW["id"]]
        self.assertEqual(disposition["status"],"publisher_source_held_for_review")
        self.assertEqual(disposition["field_review_needed"]["source_address_changed"],1)
        self.assertEqual(disposition["updates"][0]["retired_observations"],[primary])
        self.assertNotIn("indirizzo",after["riscontri_campi"][0]["valori"])
        self.assertEqual(after["riscontri_campi"][0]["letto_il"],TODAY.isoformat())
        self.assertEqual(field_states(after,today=tomorrow)["indirizzo"],"senza_riscontro_documentato")
        self.assertTrue(validate_release(before,result,report,cfg,reg)["release_safe"])
        with TemporaryDirectory() as td:
            path=Path(td)/"public/data/v1"
            export(result,path,today=tomorrow,min_count=1,preserve_ids={mid})
            self.assertTrue(verify_static(path/"manifest.json",report,cfg,reg,tomorrow)["release_safe"])
        corrupted=copy.deepcopy(result)
        next(r for r in corrupted if r["slug"]==mid)["riscontri_campi"]=[primary]
        with self.assertRaises(ValueError):
            validate_release(before,corrupted,report,cfg,reg)

    def test_held_conflict_preserves_independent_source_evidence(self):
        cfg,reg=enabled_fixture()
        first,_=fixture_activate(cfg,reg,far_baseline(),today=TODAY,fetch=lambda url:(BLOB,False))
        mid="pg-corciano-mercato-di-corciano"
        target=next(r for r in first if r["slug"]==mid)
        secondary=copy.deepcopy(target["riscontri_campi"][0])
        secondary.pop("campi_gestiti");secondary.pop("gestore_campi")
        secondary.update({"fonte_id":"independent-primary-page","url":"https://example.org/municipal-market",
                          "metodo":"pagina_primaria_revisionata","ambito":"pagina"})
        target["riscontri_campi"].append(secondary)
        changed=BLOB.replace(b";CADUTI;",b";NUOVA SEDE;")
        result,report=fixture_activate(cfg,reg,first,today=TODAY+timedelta(days=1),
                                      fetch=lambda url:(changed,False))
        after=next(r for r in result if r["slug"]==mid)
        self.assertEqual(after["indirizzo"],target["indirizzo"])
        self.assertIn(secondary,after["riscontri_campi"])
        own=next(r for r in after["riscontri_campi"] if r["fonte_id"]==RAW["id"])
        self.assertNotIn("indirizzo",own["valori"])
        self.assertEqual(report["old_market_fields_changed"],0)

    def test_source_level_approval_can_admit_four_distinct_ids_as_one_contract(self):
        cfg,reg=enabled_fixture()
        fetches=[]
        old=far_baseline()
        frozen=copy.deepcopy(old)
        def fetch(url):
            fetches.append(url)
            return BLOB,False
        output,report=fixture_activate(cfg,reg,old,today=TODAY,fetch=fetch)
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
        replay,second=fixture_activate(cfg,reg,output,today=TODAY,fetch=fetch)
        self.assertEqual(replay,output)
        self.assertEqual(second["new_market_ids"],[])
        self.assertTrue(validate_release(output,replay,second,cfg,reg)["release_safe"])

    def test_approved_source_replays_remaining_venues_across_scheduled_cycles(self):
        cfg,reg=enabled_fixture()
        reg["approvals"][0]["max_new_ids"]=2
        old=far_baseline()
        source_fetch=lambda url:(BLOB,False)
        first,one=fixture_activate(cfg,reg,old,today=TODAY,fetch=source_fetch)
        self.assertEqual(len(first)-len(old),2)
        self.assertEqual(one["per_source"][RAW["id"]]["deferred_candidate_count"],2)
        self.assertEqual(one["status_counts"]["eligible_venues_deferred_to_next_run"],2)
        self.assertTrue(validate_release(old,first,one,cfg,reg)["release_safe"])
        second,two=fixture_activate(cfg,reg,first,today=TODAY,fetch=source_fetch)
        self.assertEqual(len(second)-len(first),2)
        self.assertEqual(two["per_source"][RAW["id"]]["deferred_candidate_count"],0)
        self.assertTrue(validate_release(first,second,two,cfg,reg)["release_safe"])
        third,three=fixture_activate(cfg,reg,second,today=TODAY,fetch=source_fetch)
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

    def test_changed_publisher_weekday_held_without_losing_existing_records(self):
        cfg,reg=enabled_fixture()
        reg["approvals"][0]["max_new_ids"]=2
        fetch=lambda url:(BLOB,False)
        first,initial=fixture_activate(cfg,reg,far_baseline(),today=TODAY,fetch=fetch)
        self.assertEqual(initial["per_source"][RAW["id"]]["deferred_candidate_count"],2)
        changed=copy.deepcopy(first)
        changed[1]["ricorrenza_testo"]="settimanale - domenica"
        later,report=fixture_activate(cfg,reg,changed,today=TODAY,fetch=fetch)
        self.assertEqual(later,changed)
        self.assertEqual(report["new_market_ids"],[])
        self.assertEqual(report["status_counts"]["published_source_drift_held"],1)
        self.assertEqual(report["per_source"][RAW["id"]]["hold_reason"],
                         "previously_published_identity_calendar_or_hours_changed")
        self.assertTrue(validate_release(changed,later,report,cfg,reg)["release_safe"])

    def test_offline_or_source_outage_never_closes_historical_market(self):
        cfg,reg=enabled_fixture()
        old=far_baseline()
        off,off_report=fixture_activate(cfg,reg,old,today=TODAY,offline=True,
                                fetch=lambda url:(_ for _ in ()).throw(AssertionError("NO FETCH")))
        self.assertEqual(off,old)
        self.assertEqual(off_report["status_counts"]["offline_skipped"],1)
        bad,report=fixture_activate(cfg,reg,old,today=TODAY,
                            fetch=lambda url:(_ for _ in ()).throw(OSError("unavailable")))
        self.assertEqual(bad,old)
        self.assertEqual(report["status_counts"]["publisher_sources_held"],1)
        self.assertEqual(report["per_source"][RAW["id"]]["status"],"publisher_source_held_for_review")

    def test_malformed_csv_held_and_safe_prior_ids_preserved(self):
        cfg,reg=enabled_fixture()
        old=far_baseline()
        damaged=BLOB.replace(b";long;lat;geopoint",b";long;latitude;geopoint")
        created,report=fixture_activate(cfg,reg,old,today=TODAY,
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
        result,report=fixture_activate(cfg,reg,old,today=TODAY,
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
        new,report=fixture_activate(cfg,reg,old,today=TODAY,fetch=lambda url:(BLOB,False))
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
        output,summary=fixture_activate(cfg,reg,old,today=TODAY,fetch=lambda url:(BLOB,False))
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
