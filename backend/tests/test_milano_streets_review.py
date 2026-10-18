import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from milano_2026_street_overlay import EVIDENCE_FILE,EXPECTED_BLOB,git_blob_sha

class MilanoStreetReviewTests(unittest.TestCase):
    def test_pinned_certificate(self):
        self.assertEqual(git_blob_sha(EVIDENCE_FILE),EXPECTED_BLOB)

if __name__=='__main__':
    unittest.main()
