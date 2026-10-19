"""All incomplete market identities remain and every field has provenance."""
from __future__ import annotations
import copy
import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from market_evidence_worklist import analyze, validate, registry_check, fields, family, markdown
import happings_source_enrichment as happings
from merge_catalog import load_existing
from source_lombardia import SOURCE_PAGE
CONTRACTS=json.loads((ROOT/"data/market-evidence-source-families.json").read_text("utf-8"))
TODAY=date(2026,10,18)


def market(sid,*,city="Pogliano Milanese",province="MI",street="",day="venerdì",
           hours="",publisher="happings.com",date_quality="prevista",coordinate=None):
    lat,lng=coordinate or (45.539,8.996)
    return {
        "slug":sid,"regione":"Lombardia","provincia":province,"citta":city,
        "nome":"Mercato settimanale di "+city,"indirizzo":street,
        "ricorrenza_testo":"Ogni "+day,
        "orario_testo":hours,"date":[(TODAY+timedelta(days=5)).isoformat()],
        "date_quality":date_quality,"fonte":publisher,
        "url_fonte":"https://www.happings.com/it/happing/test-pogliano",
        "lat":lat,"lng":lng,"position_quality":"non_verificata",
        "verificato_il":"","aggiornato_il":"2026-10-13",
        "status":"non_confermato",
    }


def official(sid="100551",*,city="Pogliano Milanese",province="MI",
             street="VIA EUROPA",day="venerdì",hours="08:00–12:00 (fonte comunale, da verificare)",
             coords=(45.5384,8.9953)):
    return {
        "slug":"lo-mercap-"+sid+"-venerdi","regione":"Lombardia",
        "provincia":province,"citta":city,"nome":"Mercato di "+city,
        "indirizzo":street,"ricorrenza_testo":"Ogni "+day,
        "orario_testo":hours,"date_quality":"prevista",
        "verificato_il":"","lat":coords[0],"lng":coords[1],
        "aggiornato_il":"2026-10-06","url_fonte":SOURCE_PAGE,
    }


class PerMarketEvidenceTests(unittest.TestCase):
    def test_five_source_layouts_are_known_but_never_grant_scraping_rights(self):
        self.assertTrue(registry_check(CONTRACTS))
        self.assertEqual(family("happings.com",CONTRACTS)["id"],
                         "happings-weekly-or-detail")
        self.assertEqual(family("unknown-town-site",CONTRACTS)["rights"],
                         "not_resolved_by_this_worklist")
        for field in ("may_grant_source_reuse_rights","may_apply_field_changes",
                      "may_confirm_individual_market_dates","may_enable_source_crawlers"):
            bad=copy.deepcopy(CONTRACTS)
            bad[field]=True
            with self.subTest(field=field),self.assertRaises(ValueError):
                registry_check(bad)
        bad=copy.deepcopy(CONTRACTS)
        bad["families"][0]["bulk_scrape_allowed"]=True
        with self.assertRaises(ValueError):
            registry_check(bad)

    def test_unlisted_operational_source_is_unresolved_without_denying_or_granting_rights(self):
        # Bologna has an approved reader in the operational registry, although
        # this report's deliberately small source-family registry omits it.
        label="Comune di Bologna, dati aperti CC BY 4.0 (licenza dichiarata)"
        row=market("bo-piano-reviewed",publisher=label,city="Bologna",province="BO")
        before=copy.deepcopy(row)
        report=analyze([row],CONTRACTS,today=TODAY,shards=1)
        self.assertTrue(validate(report,1))
        profile=report["sources_by_volume"][0]
        task=report["daily_worklist"][0]
        self.assertEqual(profile["source_family"],"source-family-not-resolved-by-this-worklist")
        self.assertEqual(profile["reuse_status"],"not_resolved_by_this_worklist")
        self.assertEqual(task["source_rights"],"not_resolved_by_this_worklist")
        self.assertEqual(profile["next_automation"],
                         "consult_existing_operational_source_registries_then_find_primary_publisher")
        self.assertEqual(task["next_source_action"],profile["next_automation"])
        self.assertIsNone(profile["authorization"])
        self.assertFalse(report["may_enable_source_crawlers"])
        self.assertFalse(report["may_grant_source_reuse_rights"])
        self.assertEqual(report["market_fields_changed"],0)
        self.assertEqual(row,before)

    def test_all_incomplete_market_rows_and_legacy_sources_are_retained(self):
        rows=[
            market("m-one"),
            market("m-two",publisher="eventiesagre.it",street="Centro"),
            market("m-three",publisher="cosedicasa.com",street="Via Roma",
                   hours="09:00–13:00"),
            market("m-four",publisher="Comune inesistente",city="Ferrara",
                   province="FE",street="Via Nuova"),
        ]
        original=copy.deepcopy(rows)
        report=analyze(rows,CONTRACTS,today=TODAY,shards=1)
        self.assertTrue(validate(report,len(rows)))
        self.assertEqual(rows,original)
        self.assertEqual(report["market_records_scanned"],len(rows))
        self.assertEqual(report["market_identities_preserved"],len(rows))
        self.assertEqual(report["market_rows_removed"],0)
        self.assertEqual(report["market_rows_added"],0)
        self.assertEqual(report["market_fields_changed"],0)
        self.assertEqual(report["confirmed_openings_added"],0)
        self.assertEqual(report["distinct_source_labels"],4)
        self.assertEqual({x["market_id"] for x in report["daily_worklist"]},
                         {x["slug"] for x in rows})
        self.assertEqual(report["missing_by_field"]["individual_edition_confirmation"],4)
        self.assertTrue(all(x["source_incomplete_record_retained"] for x in report["daily_worklist"]))

    def test_source_unique_town_day_only_is_not_an_address_confirmation(self):
        entry=market("m-no-address")
        report=analyze([entry],CONTRACTS,official=[official()],today=TODAY,shards=1)
        self.assertTrue(validate(report,1))
        task=report["daily_worklist"][0]
        self.assertEqual(task["official_match"],"city_weekday_only_unconfirmed_venue")
        lead=task["official_evidence"][0]
        self.assertEqual(lead["field"],"indirizzo")
        self.assertEqual(lead["source_id"],"lo-mercap-100551-venerdi")
        self.assertFalse(lead["can_apply"])
        self.assertFalse(lead["opening_verified"])
        self.assertFalse(lead["exact_venue_identity_confirmed"])
        self.assertEqual(entry["indirizzo"],"")

    def test_exact_street_weekday_supports_missing_hours_but_not_verification(self):
        entry=market("legacy-pogliano-venerdi",street="Via Europa")
        report=analyze([entry],CONTRACTS,official=[official()],today=TODAY,shards=1)
        task=report["daily_worklist"][0]
        self.assertEqual(task["official_match"],"unique_city_province_street_weekday")
        proof=task["official_evidence"][0]
        self.assertEqual(proof["field"],"orario_testo")
        self.assertTrue(proof["can_apply"])
        self.assertFalse(proof["opening_verified"])
        self.assertEqual(proof["source_url"],SOURCE_PAGE)
        self.assertEqual(entry["orario_testo"],"")
        self.assertEqual(report["official_join_results"]["exact_field_evidence_candidates"],1)

    def test_different_province_date_conflict_and_coordinates_are_not_matched(self):
        cases=[
            market("m-wrongprovince",street="Via Europa",province="VA"),
            market("m-wrongday",street="Via Europa",day="martedì"),
            market("m-faraway",street="Via Europa",coordinate=(46.4,9.5)),
        ]
        for row in cases:
            with self.subTest(slug=row["slug"]):
                result=analyze([row],CONTRACTS,official=[official()],today=TODAY,shards=1)
                task=result["daily_worklist"][0]
                self.assertEqual(task["official_evidence"],[])
                self.assertEqual(row["orario_testo"],"")

    def test_two_official_venues_same_city_day_never_guess_street(self):
        official_two=official(sid="100552",street="VIA TORINO")
        report=analyze([market("unknown")],CONTRACTS,official=[official(),official_two],
                       today=TODAY,shards=1)
        row=report["daily_worklist"][0]
        self.assertEqual(row["official_match"],"no_usable_source_match")
        self.assertEqual(row["source_conflict"],"many_market_places_on_same_city_day")
        self.assertEqual(row["official_evidence"],[])

    def test_same_source_id_can_find_missing_street_without_creating_new_market(self):
        src=official()
        old=market(src["slug"],street="",publisher="Regione Lombardia – MERCap (CC0 1.0 dichiarata)")
        old["url_fonte"]=SOURCE_PAGE
        report=analyze([old],CONTRACTS,official=[src],today=TODAY,shards=1)
        matches=report["daily_worklist"][0]["official_evidence"]
        matching=next(x for x in matches if x["field"]=="indirizzo")
        self.assertTrue(matching["can_apply"])
        self.assertEqual(report["market_fields_changed"],0)

    def test_stale_official_snapshots_cannot_supply_fresh_evidence(self):
        src=official()
        src["aggiornato_il"]="2023-01-01"
        result=analyze([market("legacy",street="Via Europa")],CONTRACTS,official=[src],
                       today=TODAY,shards=1)
        self.assertEqual(result["official_source_status"],"stale_or_empty_source")
        self.assertEqual(result["daily_worklist"][0]["official_evidence"],[])

    def test_weekday_mismatch_with_slug_is_not_accepted(self):
        row=market("mercato-pogliano-venerdi",street="Via Europa",day="martedì")
        out=analyze([row],CONTRACTS,official=[official()],today=TODAY,shards=1)
        self.assertEqual(out["daily_worklist"][0]["official_evidence"],[])

    def test_31_day_rotation_is_fair_no_truncation_and_full_audit_every_day(self):
        records=[market("venue-"+str(i),street="" if i%2 else "Centro")
                 for i in range(310)]
        seen=set()
        for offset in range(31):
            d=TODAY+timedelta(days=offset)
            out=analyze(records,CONTRACTS,today=d)
            self.assertTrue(validate(out,310))
            self.assertEqual(out["market_records_scanned"],310)
            seen.update(x["market_id"] for x in out["daily_worklist"])
        self.assertEqual(seen,{x["slug"] for x in records})

    def test_real_national_catalog_every_market_is_kept_in_review(self):
        manifest=ROOT.parent/"public/data/v1/manifest.json"
        if not manifest.exists():
            self.skipTest("Catalog only becomes available after source migration")
        originals=load_existing(manifest)
        self.assertGreater(len(originals),12_000)
        before={m["slug"] for m in originals}
        report=analyze(originals,CONTRACTS,today=TODAY)
        self.assertTrue(validate(report,len(originals)))
        self.assertEqual(report["market_identities_preserved"],len(before))
        self.assertEqual(len(before),len(originals))
        self.assertGreaterEqual(report["distinct_source_labels"],40)
        self.assertGreater(len(report["daily_worklist"]),0)
        self.assertEqual(before,{m["slug"] for m in originals})
        self.assertEqual(report["market_rows_removed"],0)

    def test_invalid_source_signature_and_duplicate_market_ids_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            analyze([market("x"),market("x")],CONTRACTS,today=TODAY)
        corrupt=official()
        corrupt["url_fonte"]="https://evil.example/market"
        with self.assertRaises(ValueError):
            analyze([market("m")],CONTRACTS,official=[corrupt],today=TODAY)
        bad=official()
        bad["verificato_il"]="2026-10-18"
        with self.assertRaises(ValueError):
            analyze([market("m")],CONTRACTS,official=[bad],today=TODAY)
        result=analyze([market("m")],CONTRACTS,today=TODAY,shards=1)
        result["market_rows_removed"]=1
        with self.assertRaises(ValueError):
            validate(result,1)


class HappingsSourceAuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.today=date(2026,10,19)
        self.record=json.loads(happings.RIGHTS_REVIEW_FILE.read_text("utf-8"))
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/"happings-rights-review.json"
        self.write_record(self.record)
        self.override=patch.object(happings,"RIGHTS_REVIEW_FILE",self.path)
        self.override.start()
        self.addCleanup(self.override.stop)

    def write_record(self,record):
        self.path.write_text(json.dumps(record),"utf-8")

    def report(self,*,today=None,rows=None):
        result=analyze(rows or [market("happings-legacy")],CONTRACTS,
                       today=today or self.today,shards=1)
        self.assertTrue(validate(result,len(rows or [None])))
        return result

    def test_owner_authorization_is_reported_without_publisher_authentication_or_network(self):
        rows=[market("happings-legacy")]
        before=copy.deepcopy(rows)
        contracts_before=copy.deepcopy(CONTRACTS)
        with patch.object(happings,"fetch_pages",side_effect=AssertionError("No report network")):
            result=self.report(rows=rows)
        source=result["sources_by_volume"][0]
        self.assertEqual(source["reuse_status"],"project_owner_authorized")
        self.assertTrue(source["bulk_scrape_allowed"])
        auth=source["authorization"]
        self.assertEqual(auth["basis"],"explicit_project_owner_instruction")
        self.assertFalse(auth["rights_authenticated"])
        self.assertEqual(auth["publication_channel"],"dev-only")
        self.assertEqual(auth["adapter_scope"],"happings_weekly_province_index")
        self.assertEqual(len(auth["record_sha256"]),64)
        self.assertFalse(auth["granted_by_this_report"])
        task=result["daily_worklist"][0]
        self.assertEqual(task["source_rights"],"project_owner_authorized")
        self.assertEqual(task["source_authorization"],auth)
        self.assertFalse(result["may_enable_source_crawlers"])
        self.assertFalse(result["may_grant_source_reuse_rights"])
        self.assertEqual(result["market_fields_changed"],0)
        self.assertEqual(rows,before)
        self.assertEqual(CONTRACTS,contracts_before)
        self.assertIn("Il registro del motore autorizza",markdown(result))

    def test_revoked_instruction_changes_next_report_without_cached_permission(self):
        first=self.report()["sources_by_volume"][0]
        self.record["project_authorization"]["revoked"]=True
        self.write_record(self.record)
        second=self.report()["sources_by_volume"][0]
        self.assertTrue(first["bulk_scrape_allowed"])
        self.assertFalse(second["bulk_scrape_allowed"])
        self.assertEqual(second["reuse_status"],"blocked_rights")
        self.assertEqual(second["next_automation"],
                         "cross_match_with_independent_licensed_official_sources")
        self.assertNotEqual(first["authorization"]["record_sha256"],
                            second["authorization"]["record_sha256"])

    def test_historical_report_does_not_backdate_project_authorization(self):
        before=self.report(today=self.today-timedelta(days=1))["sources_by_volume"][0]
        after=self.report()["sources_by_volume"][0]
        self.assertFalse(before["bulk_scrape_allowed"])
        self.assertEqual(before["reuse_status"],"blocked_rights")
        self.assertTrue(after["bulk_scrape_allowed"])

    def test_missing_malformed_or_oversized_record_cannot_authorize_extraction(self):
        for raw in (None,b"not-json",b" "*65_537,b'{"schema":1}',b"\xff"):
            with self.subTest(raw=raw[:20] if raw else raw):
                if raw is None:
                    self.path.unlink()
                else:
                    self.path.write_bytes(raw)
                source=self.report()["sources_by_volume"][0]
                self.assertFalse(source["bulk_scrape_allowed"])
                self.assertEqual(source["reuse_status"],"invalid_or_missing_rights_record")

    def test_wrong_scope_or_channel_follows_existing_crawler_authorization_gate(self):
        for key,value in (("publication_channel","production"),
                          ("scope",["automated_extraction"]),
                          ("authorized",False)):
            with self.subTest(key=key):
                record=copy.deepcopy(self.record)
                record["project_authorization"][key]=value
                self.write_record(record)
                source=self.report()["sources_by_volume"][0]
                self.assertFalse(source["bulk_scrape_allowed"])
                self.assertEqual(source["reuse_status"],"blocked_rights")

    def test_authenticated_grant_remains_distinct_from_owner_instruction(self):
        self.record["republication_rights_authenticated"]=True
        self.write_record(self.record)
        source=self.report()["sources_by_volume"][0]
        self.assertEqual(source["reuse_status"],"authenticated")
        self.assertTrue(source["bulk_scrape_allowed"])
        self.assertTrue(source["authorization"]["rights_authenticated"])
        self.assertEqual(source["authorization"]["basis"],"authenticated_publisher_grant")

    def test_source_contract_cannot_replace_or_override_the_real_permission_record(self):
        for key,value in (("bulk_scrape_allowed",True),("bulk_scrape_allowed",False),
                          ("rights","project_owner_authorized"),
                          ("authorization_source","/tmp/unchecked-permission.json"),
                          ("authorization",{"authorized":True})):
            with self.subTest(key=key,value=value):
                cfg=copy.deepcopy(CONTRACTS)
                cfg["families"][0][key]=value
                with self.assertRaises(ValueError):
                    analyze([market("happings-legacy")],cfg,today=self.today,shards=1)

    def test_eventiesagre_and_cosedicasa_keep_their_no_bulk_policy(self):
        rows=[market("happings-legacy"),market("events",publisher="eventiesagre.it"),
              market("editorial",publisher="cosedicasa.com")]
        report=self.report(rows=rows)
        sources={source["publisher"]:source for source in report["sources_by_volume"]}
        self.assertTrue(sources["happings.com"]["bulk_scrape_allowed"])
        for label in ("eventiesagre.it","cosedicasa.com"):
            with self.subTest(label=label):
                self.assertFalse(sources[label]["bulk_scrape_allowed"])
                self.assertIsNone(sources[label]["authorization"])
        self.assertEqual(sources["eventiesagre.it"]["reuse_status"],
                         "link_id_only_no_bulk_content_copy")
        self.assertEqual(sources["cosedicasa.com"]["reuse_status"],
                         "no_verified_bulk_reuse_permission")

    def test_report_validation_rejects_new_authority_and_false_authentication(self):
        result=self.report()
        for field in ("may_enable_source_crawlers","may_grant_source_reuse_rights"):
            bad=copy.deepcopy(result)
            bad[field]=True
            with self.subTest(field=field),self.assertRaises(ValueError):
                validate(bad,1)
        for key,value in (("rights_authenticated",True),("granted_by_this_report",True),
                          ("publication_channel","production")):
            bad=copy.deepcopy(result)
            bad["sources_by_volume"][0]["authorization"][key]=value
            with self.subTest(key=key),self.assertRaises(ValueError):
                validate(bad,1)
        bad=copy.deepcopy(result)
        bad["daily_worklist"][0]["source_authorization"]={"authorized":True}
        with self.assertRaises(ValueError):
            validate(bad,1)
        bad=copy.deepcopy(result)
        bad["daily_worklist"][0]["source_rights"]="no_verified_bulk_reuse_permission"
        with self.assertRaises(ValueError):
            validate(bad,1)

if __name__=="__main__":
    unittest.main()
