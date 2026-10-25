"""Revisit unresolved Happings URLs after the first full-source crawl.

Retries only completed failed checkpoints, sequentially with publisher delays.
Keeps every successful observation intact. On repeated failure retains an
explicit unresolved source error; never claims complete content from a 404.
"""
from __future__ import annotations

import gzip
import hashlib
import json
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import happings_bulk_snapshot as bulk
import happings_source_enrichment as weekly
import atomic_write

MAX_ATTEMPTS = 3
FAILED = {"unavailable", "unassessed"}
HARD_FAILURE = {"robots_denied"}


def retry(snapshot, *, max_attempts=MAX_ATTEMPTS, robots=None,
          reader=None, sleep=time.sleep):
    # Share the crawler's exclusive checkpoint lock with the refresher.
    # A retry must never overwrite a page while another worker is fetching it.
    with bulk.snapshot_lock(snapshot):
        return _retry_unlocked(snapshot,max_attempts=max_attempts,robots=robots,
                               reader=reader,sleep=sleep)


def _retry_unlocked(snapshot, *, max_attempts=MAX_ATTEMPTS, robots=None,
                    reader=None, sleep=time.sleep):
    snapshot=Path(snapshot)
    if type(max_attempts) is not int or not 2 <= max_attempts <= MAX_ATTEMPTS:
        raise ValueError("Invalid bounded Happings retry count")
    checkpoint=snapshot/"checkpoint.json"
    status=json.loads(checkpoint.read_text("utf-8"))
    queue,done=status.get("queue"),status.get("done")
    if (status.get("schema") != 1 or not isinstance(queue,list)
            or not isinstance(done,dict) or not set(done).issubset(queue)
            or len(done)!=len(queue) or len(queue)>bulk.MAX_QUEUE):
        raise ValueError("Retry requires a finished valid first-pass snapshot")
    bulk.valid_queue(queue)
    for url,item in done.items():
        if not isinstance(item,dict) or item.get("status") not in {
                "parsed","unavailable","unassessed","robots_denied"}:
            raise ValueError("Untrusted Happings retry checkpoint item")
    reader=reader or bulk.page_fact
    pending=[url for url in queue if done[url]["status"] in FAILED
             and int(done[url].get("attempts",1)) < max_attempts]
    if pending:
        robots=robots or weekly.robots_allowed()
        delay=weekly._request_pause(robots)
    else:
        delay=0
    attempts=[]
    for url in pending:
        sleep(delay)
        fact=reader(url,robots)
        if (not isinstance(fact,dict) or fact.get("url")!=url
                or fact.get("status") not in {"parsed","unassessed","unavailable","robots_denied"}
                or not isinstance(fact.get("read_at"),str)):
            raise ValueError("Happings retry source result changed URL or schema")
        path=snapshot/"pages"/(bulk.fingerprint(url)+".json.gz")
        packed=gzip.compress((json.dumps(fact,ensure_ascii=False,
                 sort_keys=True,default=str)+"\n").encode("utf-8"))
        target=path.with_name(path.name+".part")
        target.write_bytes(packed)
        atomic_write.replace(target, path)
        earlier=done[url]
        done[url]={"status":fact["status"],"kind":fact.get("kind",earlier.get("kind","unknown")),
                   "facts_sha256":hashlib.sha256(packed).hexdigest(),
                   "read_at":fact["read_at"],
                   "source_rows":fact.get("source_rows",0),
                   "market_classified":fact.get("market_classified",False),
                   "attempts":int(earlier.get("attempts",1))+1}
        bulk.write_json(checkpoint,status)
        attempts.append({"url":url,"status":fact["status"],"attempts":done[url]["attempts"]})
    unresolved=[url for url in queue if done[url]["status"] in FAILED|HARD_FAILURE]
    results={"schema":1,"as_of":datetime.now(timezone.utc).isoformat(),
             "pages_total":len(queue),"pages_parsed":sum(
                 r["status"]=="parsed" for r in done.values()),
             "source_pages_unresolved":len(unresolved),
             "unresolved_urls":unresolved[:100],
             "new_requests":len(attempts),"retries":attempts,
             "recovered_in_this_run":sum(x["status"]=="parsed" for x in attempts),
             "source_content_complete":not unresolved,
             "source_errors_not_silently_excluded":True}
    bulk.write_json(snapshot/"retry-status.json",results)
    return results
