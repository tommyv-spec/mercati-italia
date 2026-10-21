"""Bad compressed snapshots never exhaust memory or bypass provenance."""
from __future__ import annotations
import gzip
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from happings_full_reconciliation import _saved_page
from happings_bulk_refresh import _verify_old

URL="https://www.happings.com/it/happing/mercato-coperto-campagna-amica-di-pisa/"


class StorageLimitsTests(unittest.TestCase):
    def test_small_gzip_with_excessive_expansion_is_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            path=root/"pages"/(hashlib.sha256(URL.encode()).hexdigest()+".json.gz")
            path.parent.mkdir()
            content=gzip.compress(b"x"*5_000_100,compresslevel=9)
            path.write_bytes(content)
            evidence={"status":"parsed","kind":"detail",
                      "facts_sha256":hashlib.sha256(content).hexdigest(),
                      "read_at":"2026-10-21T09:00:00+00:00"}
            with self.assertRaisesRegex(ValueError,"Corrupt or oversized"):
                _saved_page(root,URL,evidence)
            with self.assertRaisesRegex(ValueError,"unbounded"):
                _verify_old(root,URL,evidence)

if __name__=="__main__":
    unittest.main()
