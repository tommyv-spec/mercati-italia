import tempfile
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from autopilot_history import summary, save_history, HISTORY_LIMIT

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

class AutopilotHistoryTests(unittest.TestCase):
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
