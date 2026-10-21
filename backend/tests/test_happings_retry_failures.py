"""Bounded retry repairs only failed Happings URLs, never rewrites good pages."""
from __future__ import annotations
import gzip
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from happings_retry_failures import retry
import happings_bulk_snapshot as bulk

SOURCE="https://www.happings.com/it/mercati-settimanali-a-gorizia-e-provincia/"
SUCCESS="https://www.happings.com/it/happing/mercato-coperto-campagna-amica-di-pisa/"

class FakeRobots:
    def can_fetch(self,*_args):
        return True
    def crawl_delay(self,*_args):
        return None
    def request_rate(self,*_args):
        return None


def setup(root):
    known={}
    for url,status,kind in ((SOURCE,"unavailable","unknown"),
                            (SUCCESS,"parsed","detail")):
        fact={"url":url,"status":status,"kind":kind,
              "read_at":datetime.now(timezone.utc).isoformat(),
              "html_sha256":"a"*64 if status=="parsed" else None,
              "bytes":500 if status=="parsed" else None}
        raw=gzip.compress((json.dumps(fact,sort_keys=True)+"\n").encode("utf-8"))
        path=root/"pages"/(hashlib.sha256(url.encode()).hexdigest()+".json.gz")
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(raw)
        known[url]={"status":status,"kind":kind,
                    "read_at":fact["read_at"],"facts_sha256":hashlib.sha256(raw).hexdigest()}
    (root/"checkpoint.json").write_text(json.dumps({"schema":1,"queue":[SOURCE,SUCCESS],
                                   "done":known}),"utf-8")


class HappingsRetryTests(unittest.TestCase):
    def test_retries_failure_once_and_leaves_success_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            setup(root)
            goodfile=next((root/"pages").glob(hashlib.sha256(SUCCESS.encode()).hexdigest()+"*"))
            before=goodfile.read_bytes()
            called=[]
            def reader(url,robots):
                called.append(url)
                return {"url":url,"status":"parsed","kind":"weekly",
                        "read_at":datetime.now(timezone.utc).isoformat(),
                        "html_sha256":"b"*64,"bytes":680,
                        "source_rows":1,"markets":[{"city":"Gorizia","place":"Piazza Vittoria",
                                                  "weekday":2}]}
            result=retry(root,robots=FakeRobots(),reader=reader,sleep=lambda _:None)
            self.assertEqual(called,[SOURCE])
            self.assertTrue(result["source_content_complete"])
            self.assertEqual(result["recovered_in_this_run"],1)
            self.assertEqual(goodfile.read_bytes(),before)
            state=json.loads((root/"checkpoint.json").read_text("utf-8"))
            self.assertEqual(state["done"][SOURCE]["attempts"],2)
            self.assertEqual(state["done"][SOURCE]["status"],"parsed")
            self.assertEqual(retry(root,robots=FakeRobots(),reader=reader,
                                   sleep=lambda _:None)["new_requests"],0)

    def test_persistent_failure_is_retained_then_exhausted(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);setup(root)
            def failed(url,robots):
                return {"url":url,"status":"unavailable",
                        "kind":"unknown","read_at":datetime.now(timezone.utc).isoformat(),
                        "error":"HTTPError"}
            first=retry(root,robots=FakeRobots(),reader=failed,sleep=lambda _:None)
            second=retry(root,robots=FakeRobots(),reader=failed,sleep=lambda _:None)
            third=retry(root,robots=FakeRobots(),reader=failed,sleep=lambda _:None)
            self.assertFalse(first["source_content_complete"])
            self.assertEqual(second["new_requests"],1)
            self.assertEqual(third["new_requests"],0)
            self.assertEqual(third["source_pages_unresolved"],1)

    def test_existing_crawler_lock_prevents_competing_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            setup(root)
            original=(root/"checkpoint.json").read_bytes()
            with bulk.snapshot_lock(root):
                with self.assertRaisesRegex(RuntimeError,"Another Happings crawler"):
                    retry(root,robots=FakeRobots(),sleep=lambda _:None)
                self.assertEqual(original,(root/"checkpoint.json").read_bytes())
            self.assertFalse((root/".happings-crawl.lock").exists())

    def test_incomplete_first_pass_cannot_concurrently_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);setup(root)
            state=json.loads((root/"checkpoint.json").read_text("utf-8"))
            state["done"].pop(SUCCESS)
            (root/"checkpoint.json").write_text(json.dumps(state),"utf-8")
            with self.assertRaises(ValueError):
                retry(root,robots=FakeRobots(),sleep=lambda _:None)

if __name__=="__main__":
    unittest.main()
