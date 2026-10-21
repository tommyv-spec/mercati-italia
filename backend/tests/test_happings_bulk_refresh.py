"""Recurring bulk refresh never races, guesses, or loses last-good facts."""
from __future__ import annotations
import gzip
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import happings_bulk_snapshot as bulk
from happings_bulk_refresh import refresh

NOW=datetime(2026,10,21,18,tzinfo=timezone.utc)
WEEKLY="https://www.happings.com/it/mercati-settimanali-a-gorizia-e-provincia/"
DETAIL="https://www.happings.com/it/happing/mercatino-di-prova/"
NEW="https://www.happings.com/it/happing/mercatino-nuovo/"


class Robots:
    def can_fetch(self, agent, url):
        return True
    def crawl_delay(self,agent):
        return None
    def request_rate(self,agent):
        return None


def seed(root, *, old_days=30, include_detail=False):
    queue=[WEEKLY]+([DETAIL] if include_detail else [])
    done={}
    for url in queue:
        stamp=(NOW-timedelta(days=old_days)).isoformat()
        fact={"url":url,"status":"parsed","read_at":stamp,
            "kind":"weekly" if url==WEEKLY else "detail",
            "source_rows":2 if url==WEEKLY else 0,
            "market_classified":url==DETAIL,
            "html_sha256":"d"*64,"bytes":2000}
        data=gzip.compress(json.dumps(fact,sort_keys=True).encode())
        folder=root/"pages"
        folder.mkdir(exist_ok=True,parents=True)
        (folder/(bulk.fingerprint(url)+".json.gz")).write_bytes(data)
        done[url]={"status":"parsed","read_at":stamp,
                   "kind":fact["kind"],
                   "source_rows":fact["source_rows"],
                   "market_classified":fact["market_classified"],
                   "facts_sha256":hashlib.sha256(data).hexdigest()}
    bulk.write_json(root/"checkpoint.json",
       {"schema":1,"queue":queue,"done":done,
        "discovery":{"observed_at":NOW.isoformat()}})
    return done


def observed(url, robots):
    return {"url":url,"status":"parsed","kind":"weekly" if url==WEEKLY else "detail",
            "read_at":NOW.isoformat(),"html_sha256":"e"*64,"bytes":3000,
            "source_rows":1 if url==WEEKLY else 0,
            "market_classified":url!=WEEKLY}


class BulkRefreshTests(unittest.TestCase):
    @patch("happings_bulk_refresh.weekly.authorization_status",
           return_value={"authorized":True})
    def test_revisits_due_weekly_but_not_fresh_market_detail(self, _auth):
        with tempfile.TemporaryDirectory() as p:
            root=Path(p)
            seed(root,old_days=9,include_detail=True)
            calls=[]
            def fetch(url,robots):
                calls.append(url)
                return observed(url,robots)
            result=refresh(root,now=NOW,robots=Robots(),reader=fetch,
                           sleep=lambda _:None)
            self.assertEqual(calls,[WEEKLY])
            self.assertEqual(result["pages_attempted"],1)
            self.assertEqual(result["catalog_mutations"],0)
            self.assertEqual(result["pages_due_after_batch"],0)
            self.assertFalse((root/".happings-crawl.lock").exists())
            self.assertEqual(json.loads((root/"checkpoint.json").read_text())
                             ["done"][WEEKLY]["read_at"], NOW.isoformat())

    @patch("happings_bulk_refresh.weekly.authorization_status",
           return_value={"authorized":True})
    def test_failed_update_keeps_last_good_and_backoff(self, _auth):
        with tempfile.TemporaryDirectory() as p:
            root=Path(p); old=seed(root,old_days=14)
            original=(root/"pages"/(bulk.fingerprint(WEEKLY)+".json.gz")).read_bytes()
            def failure(url,robots):
                return {"url":url,"status":"unavailable","read_at":NOW.isoformat()}
            r=refresh(root,now=NOW,robots=Robots(),reader=failure,
                      sleep=lambda _:None)
            self.assertEqual(r["refresh_outcomes"]["last_good_observation_retained"],1)
            self.assertEqual((root/"pages"/(bulk.fingerprint(WEEKLY)+".json.gz")).read_bytes(),original)
            state=json.loads((root/"checkpoint.json").read_text())
            self.assertEqual(state["done"][WEEKLY]["status"],"parsed")
            self.assertEqual(state["done"][WEEKLY]["read_at"],old[WEEKLY]["read_at"])
            calls=[]
            r=refresh(root,now=NOW+timedelta(hours=4),robots=Robots(),
                      reader=lambda *a:calls.append(1),sleep=lambda _:None)
            self.assertEqual(r["pages_attempted"],0)
            self.assertFalse(calls)

    @patch("happings_bulk_refresh.weekly.authorization_status",
           return_value={"authorized":True})
    def test_discovers_new_url_and_keeps_old_queue_and_history(self, _auth):
        with tempfile.TemporaryDirectory() as p:
            root=Path(p);seed(root,old_days=0)
            state=json.loads((root/"checkpoint.json").read_text())
            state["discovery"]["observed_at"]=(NOW-timedelta(days=2)).isoformat()
            bulk.write_json(root/"checkpoint.json",state)
            report=refresh(root,now=NOW,robots=Robots(),
                discovery=lambda robots,sleep:([WEEKLY,NEW],{"observed_at":NOW.isoformat()}),
                reader=observed,sleep=lambda _:None)
            self.assertEqual(report["new_urls_discovered"],1)
            self.assertEqual(report["pages_attempted"],1)
            saved=json.loads((root/"checkpoint.json").read_text())
            self.assertEqual(saved["queue"],[WEEKLY,NEW])
            self.assertEqual(saved["done"][NEW]["status"],"parsed")
            self.assertEqual(saved["done"][WEEKLY]["read_at"],state["done"][WEEKLY]["read_at"])

    @patch("happings_bulk_refresh.weekly.authorization_status",
           return_value={"authorized":True})
    def test_does_not_overwrite_tampered_previous_fact(self, _auth):
        with tempfile.TemporaryDirectory() as p:
            root=Path(p);seed(root,old_days=15)
            f=root/"pages"/(bulk.fingerprint(WEEKLY)+".json.gz")
            f.write_bytes(f.read_bytes()+b"modified")
            with self.assertRaisesRegex(ValueError,"altered"):
                refresh(root,now=NOW,robots=Robots(),reader=observed,sleep=lambda _:None)
            self.assertFalse((root/".happings-crawl.lock").exists())

    @patch("happings_bulk_refresh.weekly.authorization_status",
           return_value={"authorized":True})
    def test_refuses_second_concurrent_crawler(self, _auth):
        with tempfile.TemporaryDirectory() as p:
            root=Path(p);seed(root,old_days=15)
            with bulk.snapshot_lock(root):
                with self.assertRaisesRegex(RuntimeError,"crawler"):
                    refresh(root,now=NOW,robots=Robots(),reader=observed,sleep=lambda _:None)


if __name__=="__main__":
    unittest.main()
