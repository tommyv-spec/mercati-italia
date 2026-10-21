"""Incremental, bounded Happings source refresh without duplicate crawlers.

Rebuild the observed page inventory from the same authorized homepage/sitemaps
and refresh older source facts in a durable checkpoint. Never publish, delete
market identities, invent hours or elevate a market to confirmed.
"""
from __future__ import annotations

import argparse
import gzip
import io
import hashlib
import json
import os
import tempfile
import time
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import happings_bulk_snapshot as bulk
import happings_source_enrichment as weekly

MAX_PAGES_PER_RUN = 150
MAX_DAYS_BETWEEN_DISCOVERY = 14
DEFAULT_DISCOVERY_DAYS = 1
REFRESH_DAYS = {"weekly": 7, "market_detail": 14, "other_detail": 90,
                "unavailable": 1, "unassessed": 2, "robots_denied": 3}


def _when(iso):
    if not isinstance(iso, str):
        raise ValueError("Missing prior source timestamp")
    try:
        value = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("Invalid source observation timestamp") from exc
    if value.tzinfo is None:
        raise ValueError("Timezone missing from source timestamp")
    return value.astimezone(timezone.utc)


def _due(url, entry, now):
    if entry is None:
        # A newly discovered event must not starve behind old reviews.
        return (-float("inf"), url)
    if not isinstance(entry, dict) or entry.get("status") not in {
            "parsed", "unavailable", "unassessed", "robots_denied"}:
        raise ValueError("Untrusted prior source observation")
    kind=entry.get("kind")
    if kind not in {"weekly", "detail", "unknown"}:
        raise ValueError("Unknown prior source layout")
    state=entry["status"]
    cadence=(REFRESH_DAYS[state] if state!="parsed" else
             REFRESH_DAYS["weekly"] if kind=="weekly" else
             REFRESH_DAYS["market_detail"] if entry.get("market_classified") is True
             else REFRESH_DAYS["other_detail"])
    observed=_when(entry.get("read_at"))
    latest=_when(entry["last_attempt"]) if entry.get("last_attempt") else observed
    if observed > now + timedelta(minutes=5) or latest > now + timedelta(minutes=5):
        raise ValueError("Source timestamp is in the future")
    if (now-latest).total_seconds() < 24*3600 and entry.get("last_attempt"):
        return None
    if (now-observed).total_seconds() < cadence*86400:
        return None
    age=(now-observed).total_seconds()/(cadence*86400)
    # More overdue sources first, with stable URL order as tie-breaker.
    return (-age, url)


def _verify_old(snapshot, url, entry):
    """Reject tampered or missing compressed source facts before replacing them."""
    if not isinstance(entry, dict) or not isinstance(entry.get("facts_sha256"),str):
        raise ValueError("Original source facts lack their recorded checksum")
    path=snapshot/"pages"/(bulk.fingerprint(url)+".json.gz")
    if not path.is_file() or not 5<=path.stat().st_size<=3_000_000:
        raise ValueError("Original source fact file missing or too large")
    raw=path.read_bytes()
    if hashlib.sha256(raw).hexdigest()!=entry["facts_sha256"]:
        raise ValueError("Refusing refresh over altered Happings source facts")
    with gzip.GzipFile(fileobj=io.BytesIO(raw)) as compressed:
        content=compressed.read(5_000_001)
    if len(content)>5_000_000:
        raise ValueError("Previous Happings source fact is unbounded")
    fact=json.loads(content)
    if fact.get("url")!=url or fact.get("status")!=entry.get("status"):
        raise ValueError("Original source facts do not match checkpoint")
    return path


def _store(snapshot, url, result, prior):
    if (not isinstance(result,dict) or result.get("url")!=url
            or result.get("status") not in {
                "parsed", "unassessed", "unavailable", "robots_denied"}
            or not isinstance(result.get("read_at"),str)):
        raise ValueError("Untrusted refreshed Happings source observation")
    path=snapshot/"pages"/(bulk.fingerprint(url)+".json.gz")
    if prior is not None:
        _verify_old(snapshot,url,prior)
    if prior is not None and prior["status"]=="parsed" and result["status"]!="parsed":
        return {**prior, "last_attempt":result["read_at"],
                "last_refresh_error":result["status"]}
    packed=gzip.compress((json.dumps(result,ensure_ascii=False,
        sort_keys=True,default=str)+"\n").encode("utf-8"))
    path.parent.mkdir(parents=True,exist_ok=True)
    temp=path.with_name(path.name+".part")
    temp.write_bytes(packed)
    temp.replace(path)
    return {
        "status":result["status"],"kind":result.get("kind",prior.get("kind","unknown") if prior else "unknown"),
        "facts_sha256":hashlib.sha256(packed).hexdigest(),
        "read_at":result["read_at"],
        "source_rows":result.get("source_rows",0),
        "market_classified":result.get("market_classified",False),
        "last_attempt":result["read_at"],
        "last_refresh_error":"" if result["status"]=="parsed" else result["status"],
    }


def refresh(snapshot, *, max_pages=70, discovery_days=DEFAULT_DISCOVERY_DAYS,
            now=None, robots=None, discovery=None, reader=None, sleep=time.sleep):
    snapshot=Path(snapshot)
    if (type(max_pages) is not int or not 1<=max_pages<=MAX_PAGES_PER_RUN
            or type(discovery_days) is not int or not 1<=discovery_days<=MAX_DAYS_BETWEEN_DISCOVERY):
        raise ValueError("Refresh exceeds bounded publisher source budget")
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Refresh requires timezone-aware datetime")
    now=now.astimezone(timezone.utc)
    authorized=weekly.authorization_status(
        json.loads(weekly.RIGHTS_REVIEW_FILE.read_text("utf-8")), today=now.date())
    if not authorized["authorized"]:
        raise ValueError("No active publisher authorization for automated refresh")
    with bulk.snapshot_lock(snapshot):
        path=snapshot/"checkpoint.json"
        if not path.is_file():
            raise ValueError("No verified Happings snapshot; initial full crawl required")
        state=json.loads(path.read_text("utf-8"))
        queue,done=state.get("queue"),state.get("done")
        if (state.get("schema")!=1 or not isinstance(queue,list) or not isinstance(done,dict)
                or not queue or len(queue)>bulk.MAX_QUEUE or len(set(queue))!=len(queue)
                or not set(done).issubset(queue)):
            raise ValueError("Invalid prior source crawl checkpoint")
        bulk.valid_queue(queue)
        robots=robots or weekly.robots_allowed()
        delay=weekly._request_pause(robots)
        source_discovery=state.get("discovery") or {}
        last=source_discovery.get("observed_at")
        needs_discovery=(not last or now-_when(last)>=timedelta(days=discovery_days))
        discovered=0
        discovery_error=None
        if needs_discovery:
            try:
                links,observed=(discovery or bulk.collect_links)(robots,sleep=sleep)
                bulk.valid_queue(links)
                known=set(queue)
                extra=[u for u in links if u not in known]
                if len(queue)+len(extra)>bulk.MAX_QUEUE:
                    raise ValueError("Publisher inventory grew beyond safe bound")
                # Append all newly observed URLs; never discard existing source
                # pages solely because a sitemap temporarily omits them.
                queue.extend(extra)
                state["discovery"]=observed
                bulk.write_json(path,state)
                discovered=len(extra)
            except (OSError,ValueError) as exc:
                discovery_error=type(exc).__name__
        ranked=[]
        for url in queue:
            due=_due(url,done.get(url),now)
            if due is not None:
                ranked.append((due,url))
        ranked.sort(key=lambda x:x[0])
        chosen=[url for _,url in ranked[:max_pages]]
        fetched=Counter()
        reader=reader or bulk.page_fact
        for url in chosen:
            if not robots.can_fetch(weekly.USER_AGENT,url):
                result={"url":url,"status":"robots_denied","read_at":bulk.utc_now()}
            else:
                sleep(delay)
                result=reader(url,robots)
            before=done.get(url)
            after=_store(snapshot,url,result,before)
            done[url]=after
            fetched[result["status"]]+=1
            if before is not None and before.get("status")=="parsed" and result["status"]!="parsed":
                fetched["last_good_observation_retained"]+=1
            bulk.write_json(path,state)
        summary={"schema":1,"refreshed_at":bulk.utc_now(),"pages_known":len(queue),
                "pages_seen":len(done),"pages_pending":len(queue)-len(done),
                "new_urls_discovered":discovered,
                "discovery_attempted":needs_discovery,"discovery_error":discovery_error,
                "pages_due":len(ranked),"pages_attempted":len(chosen),
                "pages_due_after_batch":len(ranked)-len(chosen),
                "source_statuses":dict(sorted(Counter(x["status"] for x in done.values()).items())),
                "refresh_outcomes":dict(sorted(fetched.items())),
                "catalog_mutations":0,
                "catalog_publication":False}
        bulk.write_json(snapshot/"refresh-status.json",summary)
        return summary


def main():
    parser=argparse.ArgumentParser()
    local=Path(os.getenv("LOCALAPPDATA") or tempfile.gettempdir())/"mercati-italia"
    parser.add_argument("--snapshot",type=Path,default=local/"happings-full-crawl")
    parser.add_argument("--max-pages",type=int,default=70)
    parser.add_argument("--discovery-days",type=int,default=1)
    args=parser.parse_args()
    print(json.dumps(refresh(args.snapshot,max_pages=args.max_pages,
                             discovery_days=args.discovery_days),
                     ensure_ascii=False,sort_keys=True),flush=True)


if __name__=="__main__":
    main()
