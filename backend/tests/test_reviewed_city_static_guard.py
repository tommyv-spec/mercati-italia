import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from reviewed_city_static_guard import (
    verify_static, evidence_digest, NAVIGATION_HOLD, COORDINATE_HOLD,
    PROVENANCE, INDEX_FIELDS,
)


class PublishedCitySafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.public = self.root / 'public'
        self.assets = self.public / 'data/v1'
        self.assets.mkdir(parents=True)
        self.evidence_path = self.root / 'evidence.json'
        self.policy_path = self.root / 'policy.json'
        self.report_path = self.root / 'daily.json'
        self.manifest_path = self.assets / 'manifest.json'
        self.cases = []
        self.details = []
        for n in range(16):
            sid = f'market-{n}'
            url = f'https://publisher.example/market-{n}'
            geo = n < 7
            case = {
                'slug': sid, 'target_city': 'Citta Comune',
                'region': 'Lombardia', 'expected_original_city': f'Bad label {n}',
                'expected_source_url': url,
            }
            if geo:
                case['coordinate_reference'] = {'observed_old_point': [46.0 + n/100, 9.0]}
            self.cases.append(case)
            row = {
                'slug': sid, 'nome': f'Mercatino {n}', 'citta': case['target_city'],
                'regione': 'Lombardia', 'citta_originale': case['expected_original_city'],
                'localita_ricostruita_da': PROVENANCE,
                'navigazione_sospesa_motivo': NAVIGATION_HOLD,
                'url_fonte': url, 'fonti': [{'url':url, 'nome':'publisher'}],
                'status':'non_confermato', 'verificato_il':'',
                'date_quality':'prevista', 'lat':None if geo else 45.0,
                'lng':None if geo else 9.0,
                'position_quality':'sconosciuta' if geo else 'non_verificata',
                'categoria':'misto','tags':[],'orario_testo':'','date':['2026-10-18'],
            }
            if geo:
                row['coordinate_originali'] = {'lat':case['coordinate_reference']['observed_old_point'][0], 'lng':9.0}
                row['coordinate_sospese_motivo'] = COORDINATE_HOLD
            self.details.append(row)
        evidence = {'schema':1,'cases':self.cases}
        self.evidence_path.write_text(json.dumps(evidence))
        digest = evidence_digest(evidence)
        self.policy_path.write_text(json.dumps({'reviewed_source_cities':{
            'enabled':True,'evidence_sha256':digest}}))
        self.report_path.write_text(json.dumps({
            'schema':1,'enabled':True,'review_only':False,'ids_preserved':True,
            'reviewed_evidence_digest':digest,'records_total':16,
            'individual_events_confirmed':0,'publisher_links_replaced':0,
            'opening_dates_added':0,'market_records_deleted':0,
        }))
        self.render()

    def render(self):
        region = self.assets / 'regions/lombardia-test.json'
        region.parent.mkdir(parents=True,exist_ok=True)
        region.write_text(json.dumps({'schema':1,'markets':self.details}))
        index = self.assets / 'index-test.json'
        rows = [[m.get(k) for k in INDEX_FIELDS] for m in self.details]
        index.write_text(json.dumps({'schema':1,'markets':rows}))
        self.manifest_path.write_text(json.dumps({
            'schema':1, 'index_schema':5, 'layout':'regional','total':16,
            'regions':[{'path':'data/v1/regions/lombardia-test.json','count':16}],
            'index':'data/v1/index-test.json',
        }))

    def check(self):
        return verify_static(self.manifest_path, self.evidence_path,
                             self.policy_path, self.report_path)

    def test_reviewed_routes_and_coordinates_are_blocked_in_exported_assets(self):
        result = self.check()
        self.assertEqual(result['navigation_routes_still_blocked'], 16)
        self.assertEqual(result['unsafe_coordinates_still_quarantined'], 7)
        self.assertEqual(result['reviewed_cities_in_search_index'], 16)
        self.assertTrue(result['release_safe'])

    def test_any_lost_navigation_hold_fails_closed(self):
        self.details[15].pop('navigazione_sospesa_motivo')
        self.render()
        with self.assertRaisesRegex(ValueError,'directions re-enabled'):
            self.check()

    def test_unsafe_coordinate_appearing_again_fails_closed(self):
        self.details[0]['lat']=46.0
        self.render()
        with self.assertRaisesRegex(ValueError,'Unsafe map point'):
            self.check()

    def test_missing_publisher_source_fails_closed(self):
        self.details[0]['fonti']=[]
        self.render()
        with self.assertRaisesRegex(ValueError,'Original publisher URL lost'):
            self.check()

    def test_fabricated_market_confirmation_fails_closed(self):
        self.details[0]['date_quality']='confermata'
        self.render()
        with self.assertRaisesRegex(ValueError,'not proof of market opening'):
            self.check()

    def test_missing_reviewed_id_fails_closed(self):
        self.details.pop()
        self.render()
        with self.assertRaisesRegex(ValueError,'Malformed full-detail regional shard'):
            self.check()

    def test_index_city_must_match_verified_details(self):
        i = self.assets / 'index-test.json'
        index = json.loads(i.read_text())
        index['markets'][0][2] = 'Wrong city'
        i.write_text(json.dumps(index))
        with self.assertRaisesRegex(ValueError,'differs between index and detail'):
            self.check()

    def test_policy_fingerprint_mismatch_fails_closed(self):
        d = json.loads(self.policy_path.read_text())
        d['reviewed_source_cities']['evidence_sha256']='0'*64
        self.policy_path.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'pinned SHA-256'):
            self.check()

    def test_explicit_policy_disable_cannot_silently_restore_routes(self):
        d = json.loads(self.policy_path.read_text())
        d['reviewed_source_cities']['enabled']=False
        self.policy_path.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'gate is disabled'):
            self.check()

    def test_empty_approved_generic_source_registry_preserves_city_evidence_digest(self):
        from source_lifecycle import digest as contract_digest
        from roma_xiii_geo_hold import git_blob_sha
        root=Path(__file__).resolve().parents[1]/"data"
        source_file=root/"market-source-contracts.json"
        approval_file=root/"approved-source-admissions.json"
        source=json.loads(source_file.read_text("utf-8"))
        admission=json.loads(approval_file.read_text("utf-8"))
        policy=json.loads(self.policy_path.read_text("utf-8"))
        policy["source_lifecycle"]={"enabled":True,
                                   "reviewed_contract_blob_sha1":git_blob_sha(source_file)}
        policy["source_contract_admissions"]={
            "enabled":True,
            "approved_registry_blob_sha1":git_blob_sha(approval_file)}
        self.policy_path.write_text(json.dumps(policy))
        proof={
            "schema":1,"enabled":True,"source_contracts_active":len(admission["approvals"]),
            "source_registry_sha256":contract_digest(admission),
            "source_contract_sha256":contract_digest(source),
            "original_market_ids":16,"candidate_market_ids":16,
            "new_market_ids":[],"record_ids_deleted":0,"old_market_fields_changed":0,
            "new_market_openings_confirmed":0,
            "new_market_coordinates_created":0,"new_market_directions_enabled":0,
        }
        source_report=self.root/"generic-publisher.json"
        source_report.write_text(json.dumps(proof))
        result=verify_static(self.manifest_path,self.evidence_path,self.policy_path,
                             self.report_path,None,source_report)
        self.assertEqual(result["manifest_records"],16)
        self.assertIsInstance(result["evidence_sha256"],str)
        self.assertEqual(result["evidence_sha256"],evidence_digest({
            "schema":1,"cases":self.cases
        }))
        self.assertTrue(result["release_safe"])
        proof["candidate_market_ids"]=17
        proof["new_market_ids"]=["unlicensed-market"]
        source_report.write_text(json.dumps(proof))
        with self.assertRaises(ValueError):
            verify_static(self.manifest_path,self.evidence_path,self.policy_path,
                          self.report_path,None,source_report)

    def test_bad_report_fails_closed(self):
        d = json.loads(self.report_path.read_text())
        d['individual_events_confirmed'] = 1
        self.report_path.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'release report'):
            self.check()

    def test_disabled_approved_publishers_preserve_city_guards_without_claiming_active_reads(self):
        import copy
        from unittest.mock import Mock, patch
        from test_source_contract_activation import CONTRACT, ACTIVE_REGISTRY, TODAY, fixture_activate
        from source_lifecycle import digest as contract_digest
        from roma_xiii_geo_hold import git_blob_sha
        source, registry = copy.deepcopy(CONTRACT), copy.deepcopy(ACTIVE_REGISTRY)
        for profile in source["raw_profiles"]:
            profile["enabled"] = False
            certificate = next(r for r in registry["approvals"] if r["source_id"] == profile["id"])
            certificate["reviewed_profile_sha256"] = contract_digest(profile)
        fetch = Mock(side_effect=AssertionError("disabled publisher must not be read"))
        result, proof = fixture_activate(source, registry, self.details, today=TODAY, fetch=fetch)
        fetch.assert_not_called()
        self.assertEqual(result, self.details)
        self.assertEqual(proof["source_contracts_active"], 0)
        proof["enabled"] = True
        data = self.root / "backend/data"
        data.mkdir(parents=True)
        source_file, approval_file = data / "market-source-contracts.json", data / "approved-source-admissions.json"
        source_file.write_text(json.dumps(source))
        approval_file.write_text(json.dumps(registry))
        policy = json.loads(self.policy_path.read_text())
        policy["source_lifecycle"] = {"enabled": True, "reviewed_contract_blob_sha1": git_blob_sha(source_file)}
        policy["source_contract_admissions"] = {"enabled": True, "approved_registry_blob_sha1": git_blob_sha(approval_file)}
        self.policy_path.write_text(json.dumps(policy))
        source_report = self.root / "generic-disabled.json"
        source_report.write_text(json.dumps(proof))
        with patch("reviewed_city_static_guard.__file__", str(self.root / "backend/reviewed_city_static_guard.py")):
            final = verify_static(self.manifest_path, self.evidence_path, self.policy_path,
                                  self.report_path, None, source_report)
            self.assertTrue(final["release_safe"])
            self.assertEqual(final["navigation_routes_still_blocked"], 16)
            self.assertEqual(final["unsafe_coordinates_still_quarantined"], 7)
            damaged = copy.deepcopy(proof)
            damaged["source_contracts_active"] = 1
            source_report.write_text(json.dumps(damaged))
            with self.assertRaisesRegex(ValueError, "pinned to a reviewed source identity"):
                verify_static(self.manifest_path, self.evidence_path, self.policy_path,
                              self.report_path, None, source_report)
            damaged = copy.deepcopy(proof)
            first = source["raw_profiles"][0]["id"]
            damaged["per_source"][first]["source_read_on"] = TODAY.isoformat()
            source_report.write_text(json.dumps(damaged))
            with self.assertRaisesRegex(ValueError, "Disabled publisher"):
                verify_static(self.manifest_path, self.evidence_path, self.policy_path,
                              self.report_path, None, source_report)

    def test_managed_generic_updates_use_final_field_proof_and_preserve_city_holds(self):
        from datetime import timedelta
        from test_source_contract_activation import CONTRACT,ACTIVE_REGISTRY,BLOB,TODAY,fixture_activate
        from roma_xiii_geo_hold import git_blob_sha
        source_file=Path(__file__).resolve().parents[1]/"data/market-source-contracts.json"
        approval_file=source_file.with_name("approved-source-admissions.json")
        def fetch(blob):
            def read(url, **_):
                if "bologna" in url:
                    raise OSError("Fixture source not included")
                return blob,False
            return read
        first,_=fixture_activate(CONTRACT,ACTIVE_REGISTRY,self.details,today=TODAY,fetch=fetch(BLOB))
        base,_=fixture_activate(CONTRACT,ACTIVE_REGISTRY,first,today=TODAY,fetch=fetch(BLOB))
        self.assertEqual(len(base),20)
        later=TODAY+timedelta(days=1)
        changed=BLOB.replace(b";CADUTI;",b";NUOVA SEDE;")
        self.details,generic=fixture_activate(CONTRACT,ACTIVE_REGISTRY,base,today=later,fetch=fetch(changed))
        generic["enabled"]=True
        self.assertEqual(generic["old_market_fields_changed"],1)
        self.render()
        manifest=json.loads(self.manifest_path.read_text())
        manifest["total"]=20;manifest["regions"][0]["count"]=20
        self.manifest_path.write_text(json.dumps(manifest))
        daily=json.loads(self.report_path.read_text());daily["records_total"]=20
        self.report_path.write_text(json.dumps(daily))
        policy=json.loads(self.policy_path.read_text())
        policy["source_lifecycle"]={"enabled":True,"reviewed_contract_blob_sha1":git_blob_sha(source_file)}
        policy["source_contract_admissions"]={"enabled":True,"approved_registry_blob_sha1":git_blob_sha(approval_file)}
        self.policy_path.write_text(json.dumps(policy))
        source_report=self.root/"generic.json"
        source_report.write_text(json.dumps(generic))
        result=verify_static(self.manifest_path,self.evidence_path,self.policy_path,
                             self.report_path,None,source_report)
        self.assertEqual(result["generic_existing_fields_checked"],1)
        self.assertEqual(result["navigation_routes_still_blocked"],16)
        self.assertEqual(result["unsafe_coordinates_still_quarantined"],7)
        region=self.assets/"regions/lombardia-test.json"
        payload=json.loads(region.read_text())
        target=next(row for row in payload["markets"] if row["slug"]=="pg-corciano-mercato-di-corciano")
        target["indirizzo"]="Sede diversa dalla prova"
        region.write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError,"Managed publisher fields"):
            verify_static(self.manifest_path,self.evidence_path,self.policy_path,
                          self.report_path,None,source_report)

    def happings_admission(self):
        """Use real page facts and semantic certificates, without mocking guards."""
        from export_static import normalize
        from happings_detail_enrichment import preview, cert_from_detail_evidence
        from test_happings_detail_enrichment import page, TODAY
        from test_source_contract_activation import CONTRACT, ACTIVE_REGISTRY, fixture_activate
        from roma_xiii_geo_hold import git_blob_sha

        def unavailable(url, **_):
            raise OSError("This fixture contains only the observed Happings page")

        baseline, generic = fixture_activate(CONTRACT, ACTIVE_REGISTRY, self.details,
                                              today=TODAY, fetch=unavailable)
        self.assertEqual(generic["old_market_fields_changed"], 0)
        self.assertEqual(generic["evidence_updated_market_ids"], [])
        self.assertEqual(generic["new_market_ids"], [])
        final, evidence = preview(baseline, [page()], today=TODAY,
                                  apply=True, admit_new=True)
        self.assertEqual(len(final), 17)
        new_id = evidence["new_market_ids"][0]
        row, error = normalize(next(row for row in final if row["slug"] == new_id), TODAY)
        self.assertIsNone(error)
        self.details = [*baseline, row]
        self.render()
        manifest = json.loads(self.manifest_path.read_text())
        manifest["total"] = manifest["regions"][0]["count"] = len(self.details)
        self.manifest_path.write_text(json.dumps(manifest))

        source_file = Path(__file__).resolve().parents[1] / "data/market-source-contracts.json"
        approval_file = source_file.with_name("approved-source-admissions.json")
        policy = json.loads(self.policy_path.read_text())
        policy["source_lifecycle"] = {"enabled": True,
                                      "reviewed_contract_blob_sha1": git_blob_sha(source_file)}
        policy["source_contract_admissions"] = {
            "enabled": True, "approved_registry_blob_sha1": git_blob_sha(approval_file)}
        self.policy_path.write_text(json.dumps(policy))
        generic["enabled"] = True
        generic["happings_detail_admission_certificate"] = cert_from_detail_evidence(evidence, today=TODAY)
        source_report = self.root / "generic-with-happings.json"
        source_report.write_text(json.dumps(generic))
        return source_report, generic, new_id

    def check_with_generic(self, source_report):
        return verify_static(self.manifest_path, self.evidence_path, self.policy_path,
                             self.report_path, None, source_report)

    def test_source_reconstructed_happings_admission_preserves_every_reviewed_hold(self):
        source_report, generic, _ = self.happings_admission()
        result = self.check_with_generic(source_report)
        self.assertTrue(result["release_safe"])
        self.assertEqual(result["manifest_records"], 17)
        self.assertEqual(result["separately_proved_happings_admissions"], 1)
        self.assertEqual(result["navigation_routes_still_blocked"], 16)
        self.assertEqual(result["unsafe_coordinates_still_quarantined"], 7)
        self.assertEqual(result["source_urls_preserved"], 16)
        # The earlier phase remains an honest historical cohort of 16 rows.
        self.assertEqual(generic["candidate_market_ids"], 16)
        self.assertEqual(json.loads(source_report.read_text()), generic)

    def test_happings_added_count_without_source_certificate_still_fails_closed(self):
        source_report, generic, _ = self.happings_admission()
        del generic["happings_detail_admission_certificate"]
        generic["separately_proved_happings_admissions"] = 1
        source_report.write_text(json.dumps(generic))
        with self.assertRaisesRegex(ValueError, "counts disagree"):
            self.check_with_generic(source_report)

    def test_happings_certificate_must_match_source_observation_and_exact_detail(self):
        import copy
        source_report, generic, new_id = self.happings_admission()
        damaged = copy.deepcopy(generic)
        damaged["happings_detail_admission_certificate"]["admissions"][0]["source_page"]["html_sha256"] = "0" * 64
        source_report.write_text(json.dumps(damaged))
        with self.assertRaisesRegex(ValueError, "detached from its observed source page"):
            self.check_with_generic(source_report)
        source_report.write_text(json.dumps(generic))
        region = self.assets / "regions/lombardia-test.json"
        payload = json.loads(region.read_text())
        next(row for row in payload["markets"] if row["slug"] == new_id)["indirizzo"] = "Via inventata 100"
        region.write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError, "differs from parsed source facts"):
            self.check_with_generic(source_report)

    def test_happings_certificate_does_not_excuse_another_unproved_market(self):
        source_report, _, _ = self.happings_admission()
        region = self.assets / "regions/lombardia-test.json"
        payload = json.loads(region.read_text())
        payload["markets"].append({**self.details[15], "slug": "unproved-extra-market"})
        region.write_text(json.dumps(payload))
        manifest = json.loads(self.manifest_path.read_text())
        manifest["total"] = manifest["regions"][0]["count"] = 18
        self.manifest_path.write_text(json.dumps(manifest))
        with self.assertRaisesRegex(ValueError, "does not match generic source admission proof"):
            self.check_with_generic(source_report)

    def test_happings_source_dates_must_survive_in_actual_compact_index(self):
        source_report, _, new_id = self.happings_admission()
        index_path = self.assets / "index-test.json"
        index = json.loads(index_path.read_text())
        next(row for row in index["markets"] if row[0] == new_id)[-1] = ["2026-10-25"]
        index_path.write_text(json.dumps(index))
        with self.assertRaisesRegex(ValueError, "source facts lost in compact search index"):
            self.check_with_generic(source_report)

    def test_proved_happings_admission_does_not_relax_existing_city_protection(self):
        source_report, _, _ = self.happings_admission()
        region = self.assets / "regions/lombardia-test.json"
        payload = json.loads(region.read_text())
        payload["markets"][15].pop("navigazione_sospesa_motivo")
        region.write_text(json.dumps(payload))
        with self.assertRaisesRegex(ValueError, "directions re-enabled"):
            self.check_with_generic(source_report)


if __name__ == '__main__':
    unittest.main()
