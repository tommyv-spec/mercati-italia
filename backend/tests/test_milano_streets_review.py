import unittest
import json
import copy
from datetime import date
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from milano_2026_street_overlay import EVIDENCE_FILE,EXPECTED_BLOB,git_blob_sha,source_rows,integrate,verify_diff
from milano_2026_overlay import OLD_DATASET

class MilanoStreetReviewTests(unittest.TestCase):
    def test_pinned_certificate(self):
        self.assertEqual(git_blob_sha(EVIDENCE_FILE),EXPECTED_BLOB)
        root=EVIDENCE_FILE.parent
        self.assertEqual(len(source_rows(json.loads(EVIDENCE_FILE.read_text('utf-8')),
            json.loads((root/'milano-mss-oct2026-observations.json').read_text('utf-8')),
            json.loads((root/'milano-mss-gis-reviewed.json').read_text('utf-8')))),25)

    def test_certificate_first_official_street(self):
        rows=json.loads(EVIDENCE_FILE.read_text('utf-8'))['entries']
        row=next(x for x in rows if x['gis_id']==44)
        self.assertEqual(row['street_display'],'Via Ferrieri E.')
        self.assertEqual(row['pdf_pages'],[1])

if __name__=='__main__':
    unittest.main()
