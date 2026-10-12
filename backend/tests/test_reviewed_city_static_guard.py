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

    def test_bad_report_fails_closed(self):
        d = json.loads(self.report_path.read_text())
        d['individual_events_confirmed'] = 1
        self.report_path.write_text(json.dumps(d))
        with self.assertRaisesRegex(ValueError,'release report'):
            self.check()


if __name__ == '__main__':
    unittest.main()
