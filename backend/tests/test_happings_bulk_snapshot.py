"""Resumable full-source inventory, without HTTP in the unit tests."""
from __future__ import annotations
import gzip
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import happings_bulk_snapshot as bulk

PISA="https://www.happings.com/it/happing/mercato-coperto-campagna-amica-di-pisa/"
GORIZIA="https://www.happings.com/it/mercati-settimanali-a-gorizia-e-provincia/"
FOREIGN="https://www.happings.com/it/mercati-settimanali-a-barcelona-e-provincia/"


class FakeRobots:
    def can_fetch(self, *_args):
        return True
    def crawl_delay(self, *_args):
        return None
    def request_rate(self, *_args):
        return None


class FullSourceInventoryTests(unittest.TestCase):
    def test_queue_only_accepts_actual_supported_happings_source_urls(self):
        self.assertTrue(bulk.valid_queue([GORIZIA, PISA]))
        with self.assertRaises(ValueError):
            bulk.valid_queue([PISA,PISA])
        with self.assertRaises(ValueError):
            bulk.valid_queue([PISA,"https://evil.invalid/mercato/"])
        with self.assertRaises(ValueError):
            bulk.valid_queue([PISA,"https://www.happings.com/it/happing/"])

    def test_resume_preserves_progress_and_does_not_redownload_same_market(self):
        calls=[]
        def fake_fact(url, robots):
            calls.append(url)
            return {"url":url,"status":"parsed","read_at":"2026-10-21T08:00:00+00:00",
                    "kind":"weekly" if url==GORIZIA else "detail",
                    "source_rows":2 if url==GORIZIA else 0,
                    "market_classified":url==PISA}
        data={"italian_province_pages":1,"event_detail_pages":1}
        with tempfile.TemporaryDirectory() as tmp:
            mocks=(patch.object(bulk.weekly,"robots_allowed",return_value=FakeRobots()),
                   patch.object(bulk.weekly,"_request_pause",return_value=0),
                   patch.object(bulk.weekly,"authorization_status",return_value={"authorized":True}),
                   patch.object(bulk,"collect_links",return_value=([GORIZIA,PISA],data)),
                   patch.object(bulk,"page_fact",side_effect=fake_fact),
                   patch.object(bulk.time,"sleep",return_value=None))
            for m in mocks:m.start()
            self.addCleanup(lambda: [m.stop() for m in mocks])
            stage1=bulk.run(Path(tmp),max_pages=1)
            self.assertEqual(stage1["pages_pending"],1)
            stage2=bulk.run(Path(tmp),max_pages=1)
            self.assertEqual(stage2["pages_pending"],0)
            self.assertEqual(stage2["source_rows_extracted"],2)
            self.assertEqual(stage2["market_event_details_classified"],1)
            self.assertEqual(calls,[GORIZIA,PISA])
            self.assertFalse(stage2["catalog_applied"])
            manifest=json.loads((Path(tmp)/"checkpoint.json").read_text("utf-8"))
            self.assertEqual(len(manifest["done"]),2)
            for url in calls:
                stored=Path(tmp)/"pages"/(bulk.fingerprint(url)+".json.gz")
                self.assertEqual(json.loads(gzip.decompress(stored.read_bytes()))["url"],url)

    def test_unsafe_existing_checkpoint_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            (Path(tmp)/"checkpoint.json").write_text(
                json.dumps({"schema":1,"queue":[PISA,PISA],"done":{}}),"utf-8")
            with (patch.object(bulk.weekly,"robots_allowed",return_value=FakeRobots()),
                  patch.object(bulk.weekly,"authorization_status",return_value={"authorized":True})):
                with self.assertRaises(ValueError):
                    bulk.run(tmp,max_pages=1)


if __name__=="__main__":
    unittest.main()
