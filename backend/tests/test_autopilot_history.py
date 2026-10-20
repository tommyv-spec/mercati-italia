import tempfile
import unittest
import copy
import json
from contextlib import contextmanager
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from autopilot_history import summary, save_history, HISTORY_LIMIT


def managed_generic_cycle():
    """Approved fixture source changed on a later day, through real export QA."""
    from datetime import timedelta
    from test_source_contract_activation import enabled_fixture,fixture_activate,far_baseline,BLOB,TODAY
    from source_contract_activation import verify_static
    from export_static import export
    cfg,registry=enabled_fixture()
    first,_=fixture_activate(cfg,registry,far_baseline(),today=TODAY,fetch=lambda url:(BLOB,False))
    later=TODAY+timedelta(days=1)
    changed=BLOB.replace(b";CADUTI;",b";NUOVA SEDE;")
    updated,report=fixture_activate(cfg,registry,first,today=later,fetch=lambda url:(changed,False))
    report["enabled"]=True
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/"public/data/v1"
        export(updated,path,today=later,min_count=1,
               preserve_ids=set(report["evidence_updated_market_ids"]))
        final=verify_static(path/"manifest.json",report,cfg,registry,later)
        approved=decision()
        approved["candidate"]["records"]=len(updated)
        approved["new_signature"]=json.loads((path/"manifest.json").read_text())["content_signature"]
    return approved,report,final

def decision():
    return {
        "approved":True, "has_changes":True,
        "candidate":{
            "records":12650,"future_60":11056,"future_90":11048,
            "indexed_gzip_bytes":356587,"verified":0,"precise":89,
            "missing_hours":10627
        },
        "gates":{"records_ok":True},
    }


@contextmanager
def later_happings_cycle():
    """Real source builders, mixed admission phases, and immutable export."""
    from datetime import date
    from test_source_contract_activation import enabled_fixture,fixture_activate,far_baseline,BLOB
    from roma_xiii_2026_venues import integrate,EVIDENCE_FILE,EXPECTED_EXISTING,CATALOG_SOURCE
    from roma_xiii_2026_release_guard import check_static
    from source_contract_activation import verify_static
    from happings_detail_enrichment import preview,cert_from_detail_evidence
    from export_static import export
    from recurrence_refresh import refresh_records
    today=date(2026,10,20)
    original=far_baseline()+[{
        "slug":sid,"nome":"Mercato comunale "+sid,"citta":"Roma","provincia":"RM",
        "regione":"Lazio","indirizzo":street,"url_fonte":CATALOG_SOURCE,
        "status":"non_confermato"} for sid,street in EXPECTED_EXISTING.items()]
    source=json.loads(EVIDENCE_FILE.read_text("utf-8"))
    roman,rome=integrate(original,source,apply=True,today=today)
    cfg,registry=enabled_fixture()
    generic,report=fixture_activate(cfg,registry,roman,today=today,fetch=lambda url:(BLOB,False))
    report["enabled"]=True
    projected,_=refresh_records(generic,today,120,540)
    url="https://www.happings.com/it/happing/mercato-coperto-campagna-amica-di-pisa/"
    html=(Path(__file__).parent/"fixtures/happings_detail/pisa.html").read_bytes()
    final,evidence=preview(projected,[{"requested_url":url,"final_url":url,"html":html,
        "fetched_at":today.isoformat()+"T12:00:00+00:00"}],today=today,apply=True,admit_new=True)
    report["happings_detail_admission_certificate"]=cert_from_detail_evidence(evidence,today=today)
    with tempfile.TemporaryDirectory() as td:
        path=Path(td)/"public/data/v1"
        export(final,path,today=today,min_count=1,preserve_ids={row["slug"] for row in final})
        guard=verify_static(path/"manifest.json",report,cfg,registry,today)
        approved=decision()
        approved.update(today=today.isoformat(),new_signature=json.loads(
            (path/"manifest.json").read_text())["content_signature"])
        approved["candidate"]["records"]=len(final)
        city={"schema":1,"reviewed_at":"2026-10-12",
              "reviewed_evidence_digest":"4ee7fe7ac44ee2111dde0d50926f9547827256a6c11361eb1d7eeb0fe6de802a",
              "records_total":len(original),"individual_events_confirmed":0,
              "publisher_links_replaced":0,"opening_dates_added":0,"market_records_deleted":0,
              "counts":{"city_fixed":0,"coordinates_quarantined":0,"navigation_hold_added":0}}
        yield approved,{
            "reviewed_cities":city,"roma_xiii_2026_report":rome,
            "roma_xiii_2026_final_guard":check_static(path/"manifest.json",source,today),
            "generic_admission_report":report,"generic_admission_static_guard":guard,
            "final_manifest":path/"manifest.json"}


class AutopilotHistoryTests(unittest.TestCase):
    def test_later_source_additions_reconcile_all_earlier_cohorts_from_actual_export(self):
        with later_happings_cycle() as (approved,kwargs):
            result=summary(approved,None,None,"mixed-source-growth",**kwargs)
            self.assertEqual(result["record_count"],13)
            self.assertEqual(result["roma_xiii_2026_new_venues_this_run"],5)
            self.assertEqual(result["generic_approved_publisher_venues_added"],4)
            self.assertEqual(result["happings_source_venues_added"],1)
            self.assertEqual(result["documented_verification_count"],0)

    def test_later_source_count_requires_certificate_actual_assets_and_matching_signature(self):
        with later_happings_cycle() as (approved,kwargs):
            for change in ("manifest_missing","certificate_missing","count","signature","report_hash"):
                decision_copy=copy.deepcopy(approved); bad=copy.deepcopy(kwargs)
                if change=="manifest_missing":bad.pop("final_manifest")
                elif change=="certificate_missing":bad["generic_admission_report"].pop("happings_detail_admission_certificate")
                elif change=="count":bad["generic_admission_static_guard"]["separately_proved_happings_admissions"]=2
                elif change=="signature":decision_copy["new_signature"]="0"*64
                else:bad["generic_admission_static_guard"]["source_admission_report_sha256"]="0"*64
                with self.subTest(change=change),self.assertRaises(ValueError):
                    summary(decision_copy,None,None,"unproved-count",**bad)

    def test_recomputed_export_hash_cannot_authorize_changed_source_hours(self):
        from datetime import date
        from export_static import export
        from merge_catalog import load_existing
        with later_happings_cycle() as (approved,kwargs):
            path=kwargs["final_manifest"]
            rows=load_existing(path)
            added=kwargs["generic_admission_report"]["happings_detail_admission_certificate"]["admissions"][0]["market_id"]
            next(row for row in rows if row["slug"]==added)["orario_testo"]="00:00–23:59"
            export(rows,path.parent,today=date.fromisoformat(approved["today"]),min_count=1,
                   preserve_ids={row["slug"] for row in rows})
            signature=json.loads(path.read_text())["content_signature"]
            approved["new_signature"]=signature
            kwargs["generic_admission_static_guard"]["catalog_content_signature"]=signature
            with self.assertRaisesRegex(ValueError,"differs from parsed source"):
                summary(approved,None,None,"tampered-candidate",**kwargs)

    def test_later_source_proof_does_not_hide_a_changed_prior_cohort_count(self):
        with later_happings_cycle() as (approved,kwargs):
            for key,field in (("reviewed_cities","records_total"),
                              ("roma_xiii_2026_report","existing_catalog_records"),
                              ("generic_admission_report","original_market_ids")):
                bad=copy.deepcopy(kwargs);bad[key][field]+=1
                with self.subTest(cohort=key),self.assertRaises(ValueError):
                    summary(approved,None,None,"unproved-cohort",**bad)

    def test_existing_workflow_cli_validates_default_published_manifest(self):
        import subprocess
        with later_happings_cycle() as (approved,kwargs):
            root=kwargs["final_manifest"].parents[3]
            decision_path=root/"release-decision.json"
            decision_path.write_text(json.dumps(approved),"utf-8")
            args=[sys.executable,str(Path(__file__).resolve().parents[1]/"autopilot_history.py"),
                  "--decision",str(decision_path),"--run-id","unchanged-workflow",
                  "--out",str(root/"history")]
            for key,flag in (("reviewed_cities","--reviewed-cities-report"),
                             ("roma_xiii_2026_report","--roma-xiii-2026-report"),
                             ("roma_xiii_2026_final_guard","--roma-xiii-2026-final-guard"),
                             ("generic_admission_report","--generic-admission-report"),
                             ("generic_admission_static_guard","--generic-admission-static-guard")):
                path=root/(key+".json");path.write_text(json.dumps(kwargs[key]),"utf-8")
                args.extend([flag,str(path)])
            # No new flag is needed by the trusted MAIN workflow: it has
            # already copied the approved candidate to public/data/v1.
            result=subprocess.run(args,cwd=root,text=True,capture_output=True,check=True)
            self.assertTrue(json.loads(result.stdout)["quality_approved"])

    def test_managed_source_updates_persist_only_with_exact_final_catalog_proof(self):
        approved,generic,final=managed_generic_cycle()
        result=summary(approved,None,None,"source-updated",generic_admission_report=generic,
                       generic_admission_static_guard=final)
        self.assertEqual(result["generic_approved_publisher_fields_updated"],1)
        self.assertEqual(result["generic_approved_publisher_evidence_refreshed"],4)
        self.assertEqual(result["generic_approved_publisher_venues_added"],0)
        self.assertEqual(result["documented_verification_count"],0)

    def test_managed_field_count_without_matching_report_or_catalog_signature_is_rejected(self):
        approved,generic,final=managed_generic_cycle()
        for field,value in (("source_admission_report_sha256","0"*64),
                            ("catalog_content_signature","0"*64),
                            ("existing_source_fields_updated",2),
                            ("existing_source_evidence_ids_checked",3),
                            ("existing_source_evidence_ids_sha256","0"*64)):
            broken=copy.deepcopy(final);broken[field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,"exact final static"):
                summary(approved,None,None,"forged",generic_admission_report=generic,
                        generic_admission_static_guard=broken)
        generic=copy.deepcopy(generic)
        generic["per_source"][next(iter(generic["per_source"]))]["source_read_on"]="2026-10-01"
        with self.assertRaisesRegex(ValueError,"exact final static"):
            summary(approved,None,None,"changed-report",generic_admission_report=generic,
                    generic_admission_static_guard=final)

    def test_source_bound_istat_municipality_repairs_preserve_caution(self):
        manual = {
            "schema":1, "enabled":True, "reviewed_at":"2026-10-12",
            "reviewed_evidence_digest":
                "4ee7fe7ac44ee2111dde0d50926f9547827256a6c11361eb1d7eeb0fe6de802a",
            "records_total":12650,
            "individual_events_confirmed":0,"publisher_links_replaced":0,
            "opening_dates_added":0,"market_records_deleted":0,
            "counts":{"city_fixed":16,"coordinates_quarantined":7,
                      "navigation_hold_added":16}
        }
        out=summary(decision(),None,None,"city-publish",reviewed_cities=manual)
        self.assertEqual(out["reviewed_city_source_corrected"],16)
        self.assertEqual(out["reviewed_city_source_coordinates_quarantined"],7)
        self.assertEqual(out["reviewed_city_source_navigation_blocked"],16)
        self.assertEqual(out["documented_verification_count"],0)
        self.assertIn("indicazioni stradali disabilitate",
                      __import__("autopilot_history").markdown(out))
        manual["individual_events_confirmed"]=1
        with self.assertRaisesRegex(ValueError,"Untrusted manually reviewed"):
            summary(decision(),None,None,"bad",reviewed_cities=manual)

    def test_persistent_city_holds_are_distinct_from_new_edits(self):
        proof = {
            "schema": 1,
            "evidence_sha256": "4ee7fe7ac44ee2111dde0d50926f9547827256a6c11361eb1d7eeb0fe6de802a",
            "manifest_records": 12650, "release_safe": True,
            "reviewed_cities_in_final_details": 16,
            "reviewed_cities_in_search_index": 16,
            "source_urls_preserved": 16,
            "navigation_routes_still_blocked": 16,
            "unsafe_coordinates_still_quarantined": 7,
            "individual_market_confirmations": 0,
        }
        item = summary(decision(), None, None, "safety-still-active",
                       reviewed_city_static_guard=proof)
        self.assertEqual(item["reviewed_city_source_navigation_blocked"], 0)
        self.assertEqual(item["reviewed_city_source_navigation_held_total"], 16)
        self.assertEqual(item["reviewed_city_source_coordinates_held_total"], 7)
        self.assertEqual(item["reviewed_city_source_final_details_checked"], 16)
        self.assertIn("Protezioni ancora attive", __import__("autopilot_history").markdown(item))
        proof["navigation_routes_still_blocked"] = 12
        with self.assertRaisesRegex(ValueError, "Untrusted persistent"):
            summary(decision(), None, None, "unsafe", reviewed_city_static_guard=proof)

    def test_roma_xiii_active_holds_are_counted_on_repeated_daily_runs(self):
        city = {
            "schema":1, "evidence_sha256":
                "4ee7fe7ac44ee2111dde0d50926f9547827256a6c11361eb1d7eeb0fe6de802a",
            "manifest_records":12650, "release_safe":True,
            "reviewed_cities_in_final_details":16,
            "reviewed_cities_in_search_index":16,
            "source_urls_preserved":16,
            "navigation_routes_still_blocked":16,
            "unsafe_coordinates_still_quarantined":7,
            "individual_market_confirmations":0,
        }
        rome = {
            "schema":1, "market_ids_in_catalog":12650,
            "rome_sources_guarded":2,"current_coordinate_holds":2,
            "current_navigation_holds":2,
            "original_source_links_preserved":2,"new_geocodes_added":0,
            "market_openings_verified":0,"release_safe":True,
        }
        result=summary(decision(),None,None,"roma-after-replay",
                       reviewed_city_static_guard=city,
                       roma_xiii_static_guard=rome)
        self.assertEqual(result["roma_xiii_coordinate_holds_active"],2)
        self.assertEqual(result["roma_xiii_navigation_holds_active"],2)
        self.assertEqual(result["all_reviewed_coordinate_holds_active"],9)
        self.assertEqual(result["all_reviewed_navigation_holds_active"],18)
        self.assertEqual(result["documented_verification_count"],0)
        display=__import__("autopilot_history").markdown(result)
        self.assertIn("Roma Municipio XIII",display)
        self.assertIn("**18** navigazioni",display)
        rome["current_coordinate_holds"]=1
        with self.assertRaisesRegex(ValueError,"Untrusted persistent Rome"):
            summary(decision(),None,None,"unsafe-rome",
                    roma_xiii_static_guard=rome)

    def test_five_roma_market_additions_correctly_bridge_prior_city_review_total(self):
        import json
        from roma_xiii_2026_venues import EXPECTED,EVIDENCE_FILE,checksum
        evidence=json.loads(EVIDENCE_FILE.read_text("utf-8"))
        old=12645
        venue={
            "schema":1,"enabled":True,
            "source_manifest_sha256":checksum(evidence),
            "source_market_identities":8,
            "official_preexisting_plateatici":2,
            "candidate_venue_records":5,
            "existing_catalog_records":old,
            "new_market_ids":sorted(EXPECTED),
            "already_published_curated_ids":[],
            "new_market_count":5,"records_added":5,
            "records_removed":0,"existing_records_changed":0,
            "new_coordinates_added":0,"new_opening_confirmations":0,
            "new_human_verifications":0,
            "held_2026_fogaccia_tuesday_single_stall":True,
            "held_urbano_ii_relocation":True,
        }
        proof={
            "schema":1,"release_safe":True,
            "reviewed_source_digest":checksum(evidence),
            "market_count_in_final_manifest":12650,
            "reviewed_2026_venue_identifiers":5,
            "forecast_only_markets":4,
            "route_holds_in_details":5,
            "route_holds_in_search_index":5,
            "original_publisher_source_links_retained":5,
            "geocoordinates_invented":0,
            "verified_future_markets_created":0,
            "excluded_fogaccia_tuesday_one_vendor":True,
            "excluded_pending_pineta_sacchetti_relocation":True,
        }
        city={
            "schema":1,"reviewed_at":"2026-10-12",
            "reviewed_evidence_digest":
                "4ee7fe7ac44ee2111dde0d50926f9547827256a6c11361eb1d7eeb0fe6de802a",
            "records_total":old,
            "individual_events_confirmed":0,"publisher_links_replaced":0,
            "opening_dates_added":0,"market_records_deleted":0,
            "counts":{"city_fixed":0,"coordinates_quarantined":0,"navigation_hold_added":0},
        }
        report=summary(decision(),None,None,"source-growth",
                       reviewed_cities=city,
                       roma_xiii_2026_report=venue,
                       roma_xiii_2026_final_guard=proof)
        self.assertEqual(report["record_count"],12650)
        self.assertEqual(report["roma_xiii_2026_new_venues_this_run"],5)
        self.assertEqual(report["roma_xiii_2026_reviewed_venues_active"],5)
        self.assertEqual(report["roma_xiii_2026_forecast_only_venues"],4)
        self.assertIn("Roma XIII nuove fonti comunali",
                      __import__("autopilot_history").markdown(report))
        stale=venue.copy()
        stale["new_market_ids"]=[]
        with self.assertRaisesRegex(ValueError,"Untrusted source-bound"):
            summary(decision(),None,None,"incorrect-source-growth",
                    reviewed_cities=city,roma_xiii_2026_report=stale,
                    roma_xiii_2026_final_guard=proof)
        replay=venue.copy()
        replay["existing_catalog_records"]=12650
        replay["records_added"]=0
        replay["new_market_count"]=0
        replay["new_market_ids"]=[]
        replay["already_published_curated_ids"]=sorted(EXPECTED)
        city["records_total"]=12650
        second=summary(decision(),None,None,"replay",reviewed_cities=city,
                       roma_xiii_2026_report=replay,
                       roma_xiii_2026_final_guard=proof)
        self.assertEqual(second["roma_xiii_2026_new_venues_this_run"],0)
        self.assertEqual(second["roma_xiii_2026_reviewed_venues_active"],5)

    def test_generic_source_level_approved_additions_reconcile_city_history(self):
        generic={
            "schema":1,"enabled":True,"publication_channel":"dev-only",
            "source_contracts_active":1,
            "original_market_ids":12648,
            "candidate_market_ids":12650,
            "new_market_ids":["approved-test-a","approved-test-b"],
            "record_ids_deleted":0,"old_market_fields_changed":0,
            "new_market_openings_confirmed":0,
            "new_market_coordinates_created":0,
            "new_market_directions_enabled":0,
        }
        final={
            "schema":1,"release_safe":True,
            "market_records_checked":12650,
            "source_contracts_active":1,
            "new_source_venue_ids_verified":2,
            "navigation_holds_in_index":2,
            "source_weekly_forecasts_only":2,
            "new_precise_coordinates":0,"original_markets_deleted":0,
            "no_individual_market_openings_confirmed":True,
        }
        city={
            "schema":1,"reviewed_at":"2026-10-12",
            "reviewed_evidence_digest":
                "4ee7fe7ac44ee2111dde0d50926f9547827256a6c11361eb1d7eeb0fe6de802a",
            "records_total":12648,
            "individual_events_confirmed":0,"publisher_links_replaced":0,
            "opening_dates_added":0,"market_records_deleted":0,
            "counts":{"city_fixed":0,"coordinates_quarantined":0,
                      "navigation_hold_added":0},
        }
        result=summary(decision(),None,None,"approved-contract",
                       reviewed_cities=city,
                       generic_admission_report=generic,
                       generic_admission_static_guard=final)
        self.assertEqual(result["generic_approved_publisher_contracts"],1)
        self.assertEqual(result["generic_approved_publisher_venues_added"],2)
        self.assertEqual(result["generic_approved_publisher_forecasts_only"],2)
        self.assertIn("contratti di interi dataset",
                      __import__("autopilot_history").markdown(result))
        unsafe=final.copy()
        unsafe["navigation_holds_in_index"]=1
        with self.assertRaisesRegex(ValueError,"final generic"):
            summary(decision(),None,None,"unsafe-generic",
                    generic_admission_report=generic,
                    generic_admission_static_guard=unsafe)
        invalid=generic.copy()
        invalid["new_market_openings_confirmed"]=1
        with self.assertRaisesRegex(ValueError,"Untrusted source-level"):
            summary(decision(),None,None,"invented",
                    generic_admission_report=invalid,
                    generic_admission_static_guard=final)

    def test_metrics_without_pii_and_priority_order(self):
        result=summary(
            decision(),
            {"queue":[{"code":"verified_source_evidence"},{"code":"location_precision"}]},
            {"candidates":[{},{}],"query_failures":{}},
            "101"
        )
        self.assertEqual(result["record_count"],12650)
        self.assertEqual(result["top_improvement_priorities"][0],"verified_source_evidence")
        self.assertEqual(result["source_candidates_scored"],2)
        self.assertNotIn("user",result)
        self.assertTrue(result["dev_only"])

    def test_source_intelligence_metrics_are_reported_without_auto_importing(self):
        registry = {
            "scan": {"total_known": 42, "delta": {"new": 2, "changed": 3}},
            "sources": [
                {"triage_class": "market_location_candidate"},
                {"triage_class": "aggregated_statistics"},
                {"triage_class": "market_location_candidate"},
            ],
        }
        report = summary(decision(), None, None, "200", registry)
        self.assertEqual(report["source_registry_known"], 42)
        self.assertEqual(report["source_registry_new"], 2)
        self.assertEqual(report["source_registry_changed"], 3)
        self.assertEqual(report["source_location_candidates"], 2)
        self.assertEqual(report["source_historical_statistics"], 1)

    def test_monitor_data_is_persisted_without_claiming_events_are_verified(self):
        monitor = {
            "metrics": {
                "source_date_within_30d": 5,
                "source_date_outside_limit": 100,
                "source_date_unknown": 8,
                "forecast_from_stale_or_unknown_source": 7,
            },
            "warnings": ["source_data_older_than_allowed_forecast_window"],
            "errors": [],
        }
        rights = {"source_evidence": [
            {"status": "metadata_checked"},
            {"status": "needs_review"},
            {"status": "metadata_checked"},
        ]}
        value = summary(decision(), None, None, "fresh-1", None, monitor, rights)
        self.assertEqual(value["source_age_over_limit"], 100)
        self.assertEqual(value["forecast_from_stale_sources"], 7)
        self.assertEqual(value["publisher_metadata_readable"], 2)
        self.assertEqual(value["publisher_metadata_checked"], 3)
        self.assertIn("oltre soglia", __import__("autopilot_history").markdown(value))
        self.assertNotIn("verified_event_count", value)

    def test_dataset_scoped_freshness_count_is_not_record_verification(self):
        freshness = {"metrics": {
            "source_date_within_30d": 1300,
            "recent_dataset_only_update": 1127,
            "dataset_updated_not_specific_market": 1127,
        }}
        row = summary(decision(), None, None, "test-scope",
                      None, freshness)
        self.assertEqual(row["source_dataset_level_records"], 1127)
        self.assertEqual(row["source_recent_dataset_only"], 1127)
        self.assertEqual(row["documented_verification_count"], 0)

    def test_lombardia_screening_stats_remain_review_only(self):
        screened = {
            "schema": 1, "source_total": 1360, "accepted": 1127,
            "quarantined": 233, "market_confirmations": 0,
            "deleted_existing_records": 0,
        }
        result = summary(decision(), None, None, "extra", None, None, None, screened)
        self.assertEqual(result["lombardia_source_total"], 1360)
        self.assertEqual(result["lombardia_source_accepted"], 1127)
        self.assertEqual(result["lombardia_source_quarantined"], 233)

    def test_bologna_quarantine_history_is_explicit_and_not_verification(self):
        bologna = {"schema": 1,"source_total":48,"accepted":47,
                   "quarantined":1,"market_confirmations":0,
                   "deleted_existing_records":0}
        result = summary(decision(),None,None,"bologna",None,None,None,None,bologna)
        self.assertEqual(result["bologna_source_total"],48)
        self.assertEqual(result["bologna_source_accepted"],47)
        self.assertEqual(result["bologna_source_quarantined"],1)
        self.assertEqual(result["documented_verification_count"],0)

    def test_bologna_report_cannot_claim_unreviewed_import(self):
        bad = {"schema":1,"source_total":48,"accepted":47,
               "quarantined":1,"market_confirmations":1}
        with self.assertRaisesRegex(ValueError,"Untrusted official overlap"):
            summary(decision(),None,None,"bad",None,None,None,None,bad)

    def test_real_municipal_hash_and_quarantine_are_persisted(self):
        detail = {"schema": 1, "source_total": 4, "accepted": 2,
                  "quarantined": 2, "source_csv_sha256": "a"*64,
                  "market_confirmations": 0, "deleted_existing_records": 0}
        report = summary(decision(),None,None,"corciano",None,None,None,None,None,detail)
        self.assertEqual(report["corciano_source_total"],4)
        self.assertEqual(report["corciano_source_accepted"],2)
        self.assertEqual(report["corciano_source_quarantined"],2)
        self.assertEqual(report["corciano_source_sha256"],"a"*64)
        self.assertEqual(report["documented_verification_count"],0)
        self.assertIn("Corciano:", __import__("autopilot_history").markdown(report))

    def test_corrupted_municipal_report_is_not_treated_as_success(self):
        detail = {"schema": 1, "source_total": 4, "accepted": 1,
                  "quarantined": 2, "market_confirmations": 0}
        with self.assertRaisesRegex(ValueError,"Untrusted official overlap"):
            summary(decision(),None,None,"corciano",None,None,None,None,None,detail)

    def test_source_hour_enrichment_is_measured_without_fabricating_verification(self):
        official = {
            "schema":1,"source_id":"lombardia-mercap",
            "enabled":True,"source_rows_screened":233,
            "exact_matches":132,"legacy_records_changed":132,
            "existing_market_hours_added":129,
            "official_source_attributions_added":132,
            "record_identity_changes":0,"confirmed_date_changes":0,
            "individual_market_verifications":0,"coordinates_overwritten":0,
            "primary_sources_overwritten":0,"old_dataset_dates_overwritten":0,
        }
        r=summary(decision(),None,None,"enrich-run",
                  None,None,None,None,None,None,official)
        self.assertTrue(r["official_enrichment_enabled"])
        self.assertEqual(r["official_enrichment_hours_added"],129)
        self.assertEqual(r["official_enrichment_attributions_added"],132)
        self.assertEqual(r["official_enrichment_held_rows"],233)
        self.assertEqual(r["documented_verification_count"],0)

    def test_untrusted_hour_enrichment_mutating_verification_must_fail(self):
        official={"schema":1,"source_id":"lombardia-mercap",
                  "individual_market_verifications":1}
        with self.assertRaisesRegex(ValueError,"Untrusted official enrichment"):
            summary(decision(),None,None,"bad",None,None,None,None,None,None,official)

    def test_review_only_quality_metrics_persist_without_erasing_markets(self):
        q={"schema":1, "review_only":True,
           "market_updates_applied":0,
           "market_confirmations_created":0,
           "market_identities_deleted":0,
           "quality_release_safe":True,
           "metrics":{
               "total":13779,
               "future_date_quality_mismatch":0,
               "suspicious_city":52,
               "review_only_duplicate_groups":755,
               "review_only_potential_extra_rows":812,
               "future_dates_missing":1984,
           }}
        r=summary(decision(),None,None,"quality",None,None,None,None,None,None,None,q)
        self.assertEqual(r["quality_audit_record_total"],13779)
        self.assertEqual(r["quality_unscheduled_false_labels"],0)
        self.assertEqual(r["quality_suspicious_cities"],52)
        self.assertEqual(r["quality_potential_weekly_duplicate_groups"],755)
        self.assertIn("Audit nazionale", __import__("autopilot_history").markdown(r))
        self.assertEqual(r["documented_verification_count"],0)

    def test_bad_catalog_quality_claim_cannot_be_reported_as_approved(self):
        q={"schema":1,"review_only":True,"market_updates_applied":1,
           "market_confirmations_created":0,
           "market_identities_deleted":0,"quality_release_safe":True}
        with self.assertRaisesRegex(ValueError,"Untrusted national catalog"):
            summary(decision(),None,None,"quality",None,None,None,None,None,None,None,q)

    def test_reversible_ui_quality_metrics_are_versioned_not_database_deletion(self):
        display = {
            "schema":1,"review_only":True,"display_grouping_only":True,
            "market_data_modified":False,
            "metrics":{
                "original_records":12650,"ids_retained":12650,
                "highly_supported_same_source_visit_groups":382,
                "suppressed_repeat_buttons_only":382,
                "original_records_in_reversible_groups":764,
                "malformed_source_city_labels_guarded_in_ui":52,
                "market_identities_deleted":0,"event_confirmations_created":0,
                "verification_claims_created":0,
            },
        }
        row=summary(decision(),None,None,"daily-ui",
                    None,None,None,None,None,None,None,None,display)
        self.assertEqual(row["visitor_duplicate_visit_groups"],382)
        self.assertEqual(row["visitor_duplicate_buttons_avoided"],382)
        self.assertEqual(row["visitor_bad_city_labels_guarded"],52)
        self.assertEqual(row["visitor_original_market_ids_retained"],12650)
        self.assertIn("Miglioramento UX reversibile",__import__("autopilot_history").markdown(row))

    def test_bad_display_report_cannot_claim_lost_original_market_ids(self):
        bad={"schema":1,"review_only":True,"display_grouping_only":True,
             "market_data_modified":False,
             "metrics":{
                "original_records":12650,"ids_retained":12649,
                "suppressed_repeat_buttons_only":1,
                "original_records_in_reversible_groups":2,
                "market_identities_deleted":0,"event_confirmations_created":0,
                "verification_claims_created":0,
             }}
        with self.assertRaisesRegex(ValueError,"Untrusted reversible"):
            summary(decision(),None,None,"unsafe-ui",
                    None,None,None,None,None,None,None,None,bad)

    def test_ISTAT_reconciliation_is_persisted_without_false_openings(self):
        report={
            "schema":1,"istat_reference":"2026-02-21",
            "source_file_sha256":"83842076860450f7e482daecea6b7a769f5f93d0bf5b0d48802b44896d7a26d5",
            "enabled":True,"ids_preserved":True,
            "market_confirmations_created":0,"verified_dates_created":0,
            "coordinates_changed":0,"publisher_sources_replaced":0,
            "counts":{
                "city_fixed":32,"contaminated_market_titles_fixed":18,
                "records_calendar_quarantined":19,
                "forecast_days_quarantined":331,
                "needs_manual_municipality_review":20,
            },
        }
        item=summary(decision(),None,None,"istat-sample",
                     municipality_report=report)
        self.assertTrue(item["municipality_istat_enabled"])
        self.assertEqual(item["municipality_city_fixed"],32)
        self.assertEqual(item["municipality_calendars_quarantined"],19)
        self.assertEqual(item["municipality_forecast_dates_removed"],331)
        self.assertEqual(item["municipality_needs_manual_review"],20)
        self.assertEqual(item["documented_verification_count"],0)
        self.assertIn("Riconciliazione ISTAT",__import__("autopilot_history").markdown(item))

    def test_bad_ISTAT_claim_does_not_pass_daily_history_gate(self):
        bad={
            "schema":1,"istat_reference":"2026-02-21",
            "source_file_sha256":"83842076860450f7e482daecea6b7a769f5f93d0bf5b0d48802b44896d7a26d5",
            "enabled":True,"ids_preserved":True,
            "market_confirmations_created":1,"verified_dates_created":0,
            "coordinates_changed":0,"publisher_sources_replaced":0,
            "counts":{"city_fixed":32},
        }
        with self.assertRaisesRegex(ValueError,"Untrusted official ISTAT"):
            summary(decision(),None,None,"bad",municipality_report=bad)

    def test_history_is_idempotent_and_bounded(self):
        with tempfile.TemporaryDirectory() as temp:
            folder=Path(temp)
            for i in range(HISTORY_LIMIT+5):
                record=summary(decision(),None,None,str(i))
                save_history(folder,record)
            history=(folder/"history.jsonl").read_text("utf-8").splitlines()
            self.assertEqual(len(history),HISTORY_LIMIT)
            self.assertNotIn('"run_id": "0"',history[0])
            item=summary(decision(),None,None,str(HISTORY_LIMIT+4))
            save_history(folder,item)
            self.assertEqual(len((folder/"history.jsonl").read_text("utf-8").splitlines()),HISTORY_LIMIT)
            self.assertIn("Mercati Autopilot",(folder/"LATEST.md").read_text("utf-8"))

    def test_failed_candidate_cannot_be_recorded_as_success(self):
        bad=decision()
        bad["approved"]=False
        with self.assertRaisesRegex(ValueError,"failed candidate"):
            summary(bad,None,None,"1")

if __name__=="__main__":
    unittest.main()
