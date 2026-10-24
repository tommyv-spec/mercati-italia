"""Resumable Happings full-source inventory, with no speculative market facts.

Run from the repository root:
    python backend/happings_bulk_snapshot.py --out PATH

Discovery: actual /it/ homepage, Italian weekly-index article sitemaps,
Yoast Happings event sitemaps, and paginated public 'mercati' archive.
Extraction: existing publisher parsers; write *every* source unit with its
observed page URL/hash. Zero automatic publication or fabricated opening claims.
No external service, browser, Docker or paid API.
"""
from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import os
import re
import sys
import tempfile
import time
from contextlib import contextmanager
from collections import Counter
from datetime import date, datetime, timezone
from http.client import HTTPException
from urllib.parse import urlsplit
from pathlib import Path

import happings_detail_discovery as detail_discovery
import happings_detail_layout
import happings_detail_enrichment
import happings_province_directory as province
import happings_source_enrichment as weekly
import happings_weekly_layout

SCHEMA = 1
MAX_QUEUE = 50_000
MAX_RESPONSE = 2_600_000
WEEKLY_PAGES_FILE = Path(__file__).resolve().parent / "data" / "happings-weekly-pages.json"


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".part")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True,
                              default=str) + "\n", encoding="utf-8")
    tmp.replace(path)


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def fingerprint(url):
    return hashlib.sha256(url.encode("utf-8")).hexdigest()


def valid_queue(urls):
    if (not isinstance(urls, list) or len(urls) > MAX_QUEUE
            or len(set(urls)) != len(urls)
            or any(detail_discovery.url_kind(url) != "detail"
                   and not weekly._valid_page_url(url) for url in urls)):
        raise ValueError("Happings bulk inventory contained foreign, duplicate or unreviewed URLs")
    return True


def collect_links(robots, *, sleep, weekly_only=False, provinces=None):
    """Discover all observed roots before touching individual market pages."""
    today = date.today()
    urls, provincial = province.discover(
        today=today, robots=robots,
        policy={"enabled": True, "max_requests": 4, "max_seconds": 90},
        sleep=sleep)
    if provincial["status"] not in {"retrieved", "partial"}:
        raise ValueError("Happings home/WordPress post index was unavailable")
    if weekly_only:
        # Weekly indexes alone feed the field fills (minutes, not hours). The
        # ~1 MB post sitemaps often time out, so the observed page list is
        # the base and discovery only adds pages. One URL per province key.
        known = json.loads(WEEKLY_PAGES_FILE.read_text("utf-8"))["urls"]
        by_key = {}
        for url in sorted(set(urls) | set(known), key=lambda u: (not u.endswith("-e-provincia/"), u)):
            by_key.setdefault(happings_weekly_layout.province_page_key(url), url)
        if provinces:
            # Pilot runs: a named subset of pages, never a silent empty one.
            unknown = set(provinces) - set(by_key)
            if unknown:
                raise ValueError("Unknown Happings province pages: " + ", ".join(sorted(unknown)))
            by_key = {key: by_key[key] for key in provinces}
        queue = sorted(by_key.values())
        valid_queue(queue)
        return queue, {"observed_at": utc_now(), "home_url": province.HOMEPAGE,
                       "province_discovery": provincial, "weekly_only": True,
                       "italian_province_pages": len(queue), "event_detail_pages": 0}
    sitemap_url = province.INDEX
    if not robots.can_fetch(weekly.USER_AGENT, sitemap_url):
        raise ValueError("Happings sitemap no longer allowed by robots")
    sleep(weekly._request_pause(robots))
    xml, _ = detail_discovery.fetch_one(sitemap_url, robots=robots)
    _, all_sitemaps = detail_discovery._observed_links(xml, sitemap_url)
    event_sitemaps = sorted({
        url for url in all_sitemaps
        if detail_discovery.url_kind(url) == "sitemap"
        and re.fullmatch(r"/happings_event-sitemap[0-9]*\.xml",
                         urlsplit(url).path)
    })
    if not event_sitemaps:
        raise ValueError("Publisher's event sitemap family is absent")
    details = set()
    captures = []
    for url in event_sitemaps:
        if not robots.can_fetch(weekly.USER_AGENT, url):
            captures.append({"url": url, "status": "robots_denied"})
            continue
        sleep(weekly._request_pause(robots))
        try:
            xml, _ = detail_discovery.fetch_one(url, robots=robots)
            _, links = detail_discovery._observed_links(xml, url)
            new = {link for link in links if detail_discovery.url_kind(link) == "detail"}
            details.update(new)
            captures.append({"url": url, "sha256": hashlib.sha256(xml).hexdigest(),
                             "detail_urls": len(new), "status": "read"})
        except (OSError, HTTPException, ValueError) as error:
            captures.append({"url": url, "status": "unavailable",
                             "error": type(error).__name__})
    if len(details) < 100:
        raise ValueError("Too few observed Happings event pages: source discovery may be truncated")
    # The category is a second, independent HTML path. It may list a
    # detail absent from the sitemap, so link traversal must not stop early.
    archives_seen = set()
    categories = provincial.get("homepage", {}).get("market_category_urls", [])
    queue = [u for u in categories if detail_discovery.url_kind(u) == "archive"]
    archive_report = []
    while queue and len(archives_seen) < 120:
        url = queue.pop(0)
        if url in archives_seen:
            continue
        archives_seen.add(url)
        if not robots.can_fetch(weekly.USER_AGENT, url):
            archive_report.append({"url": url, "status": "robots_denied"})
            continue
        sleep(weekly._request_pause(robots))
        try:
            raw, _ = detail_discovery.fetch_one(url, robots=robots)
            _, links = detail_discovery._observed_links(raw, url)
            new_details = {link for link in links if detail_discovery.url_kind(link) == "detail"}
            details.update(new_details)
            for link in links:
                if detail_discovery.url_kind(link) == "archive" and link not in archives_seen:
                    if link not in queue:
                        queue.append(link)
            archive_report.append({"url": url, "status": "read",
                                   "sha256": hashlib.sha256(raw).hexdigest(),
                                   "detail_urls": len(new_details)})
        except (OSError, HTTPException, ValueError) as error:
            archive_report.append({"url": url, "status": "unavailable",
                                   "error": type(error).__name__})

    if not urls or not details:
        raise ValueError("Publisher produced no reviewed weekly or detail inventory")
    all_urls = sorted(set(urls)) + sorted(details)
    valid_queue(all_urls)
    return all_urls, {"observed_at": utc_now(), "home_url": province.HOMEPAGE,
                      "province_discovery": provincial,
                      "event_sitemaps": captures, "market_archives": archive_report,
                      "italian_province_pages": len(urls),
                      "event_detail_pages": len(details)}


def page_fact(url, robots):
    if not robots.can_fetch(weekly.USER_AGENT, url):
        return {"url": url, "status": "robots_denied", "read_at": utc_now()}
    try:
        kind = detail_discovery.url_kind(url)
        if kind == "detail":
            raw, final = detail_discovery.fetch_one(url, robots=robots)
        elif weekly._valid_page_url(url):
            raw, final = weekly._fetch_one(url, robots=robots)
            if not weekly.allowed_url(url, url, final):
                raise ValueError("Provincial redirect changed geographic scope")
        else:
            raise ValueError("URL outside reviewed source layouts")
        evidence = {"url": url, "final_url": final, "read_at": utc_now(),
                    "status": "read", "html_sha256": hashlib.sha256(raw).hexdigest(),
                    "bytes": len(raw), "kind": "detail" if kind == "detail" else "weekly"}
        try:
            if kind == "detail":
                parsed = happings_detail_layout.parse_detail(raw,
                             requested_url=url, final_url=final)
                event = parsed["event"]
                is_market = happings_detail_enrichment._category(event) is not None
                evidence["status"] = "parsed"
                evidence["market_classified"] = is_market
                evidence["event"] = event if is_market else {
                    "name": event.get("name"), "category": event.get("category")}
                evidence["source"] = parsed.get("source")
                evidence["conflicts"] = parsed.get("conflicts")
                evidence["warnings"] = parsed.get("warnings")
                evidence["field_evidence"] = parsed.get("field_evidence")
            else:
                parsed = happings_weekly_layout.parse(raw, source_url=final,
                                                       observed_on=date.today())
                evidence["status"] = "parsed"
                evidence["source_rows"] = len(parsed.rows)
                evidence["markets"] = [{
                    "city": r["city"], "weekday": r["weekday"],
                    "place": r["place"], "daypart": r.get("daypart"),
                    "calendar_scope": r.get("calendar_scope"),
                    "editorial_scope": r.get("editorial_scope"),
                    "has_specific_location": r.get("has_specific_location"),
                } for r in parsed.rows]
        except (ValueError, KeyError, TypeError) as error:
            evidence["status"] = "unassessed"
            evidence["parse_error"] = type(error).__name__
        return evidence
    except (OSError, HTTPException, ValueError) as error:
        return {"url": url, "status": "unavailable", "read_at": utc_now(),
                "error": type(error).__name__}


@contextmanager
def snapshot_lock(out):
    """Exclusive crash-persistent lock shared by full and incremental crawls.

    A stale lock requires inspection. Never silently steal it or allow two
    crawlers to race on the same atomic checkpoint and fact files.
    """
    root=Path(out)
    root.mkdir(parents=True,exist_ok=True)
    path=root/".happings-crawl.lock"
    try:
        fd=os.open(str(path),os.O_CREAT|os.O_EXCL|os.O_WRONLY,0o600)
    except FileExistsError:
        raise RuntimeError("Another Happings crawler holds this snapshot lock") from None
    try:
        with os.fdopen(fd,"w",encoding="utf-8") as handle:
            handle.write(json.dumps({"pid":os.getpid(),"started_at":utc_now()})+"\n")
        yield
    finally:
        path.unlink(missing_ok=True)


def _run_unlocked(out, *, max_pages=0, weekly_only=False, provinces=None):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    auth = json.loads(weekly.RIGHTS_REVIEW_FILE.read_text(encoding="utf-8"))
    permit = weekly.authorization_status(auth, today=date.today())
    if not permit["authorized"]:
        raise ValueError("Happings automatic extraction authorization is not active")
    robots = weekly.robots_allowed()
    delay = weekly._request_pause(robots)
    checkpoint = out / "checkpoint.json"
    if checkpoint.exists():
        status = json.loads(checkpoint.read_text(encoding="utf-8"))
        if (status.get("schema") != SCHEMA or not isinstance(status.get("queue"), list)
                or not isinstance(status.get("done"), dict)):
            raise ValueError("Existing crawl checkpoint is not safe to resume")
        valid_queue(status["queue"])
        if not set(status["done"]).issubset(status["queue"]):
            raise ValueError("Saved source outcomes are outside the observed URL inventory")
        print("Resumed checkpoint", len(status["done"]), "/", len(status["queue"]), flush=True)
    else:
        queue, discovery = collect_links(robots, sleep=time.sleep, weekly_only=weekly_only,
                                         provinces=provinces)
        status = {"schema": SCHEMA, "started_at": utc_now(),
                  "queue": queue, "done": {}, "discovery": discovery}
        write_json(checkpoint, status)
        print("Discovered", len(queue), "unique source pages:", discovery["italian_province_pages"],
              "weekly indexes,", discovery["event_detail_pages"], "event details.", flush=True)

    served = 0
    for url in status["queue"]:
        if url in status["done"]:
            continue
        if max_pages and served >= max_pages:
            break
        time.sleep(delay)
        result = page_fact(url, robots)
        path = out / "pages" / (fingerprint(url) + ".json.gz")
        path.parent.mkdir(parents=True, exist_ok=True)
        target = path.with_name(path.name + ".part")
        target.write_bytes(gzip.compress((json.dumps(result, ensure_ascii=False,
                              sort_keys=True, default=str)+"\n").encode("utf-8")))
        target.replace(path)
        status["done"][url] = {"status": result["status"],
                               "kind": result.get("kind", "unknown"),
                               "facts_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                               "read_at": result["read_at"],
                               "source_rows": result.get("source_rows", 0),
                               "market_classified": result.get("market_classified", False)}
        write_json(checkpoint, status)
        served += 1
        if served == 1 or served % 15 == 0:
            counts = Counter(item["status"] for item in status["done"].values())
            print("Pages", len(status["done"]), "/", len(status["queue"]),
                  "status", dict(counts), "latest", url, flush=True)

    counts = Counter(item["status"] for item in status["done"].values())
    summary = {"schema": SCHEMA, "as_of": utc_now(),
               "pages_discovered": len(status["queue"]),
               "pages_processed": len(status["done"]),
               "pages_pending": len(status["queue"])-len(status["done"]),
               "source_rows_extracted": sum(item.get("source_rows",0)
                                            for item in status["done"].values()),
               "market_event_details_classified": sum(
                    item.get("market_classified") is True for item in status["done"].values()),
               "status_counts": dict(counts),
               "catalog_applied": False, "openings_verified": 0,
               "note": "Raw publisher facts only; all catalogue IDs and fields require a separate verified reconciliation."}
    write_json(out / "summary.json", summary)
    print("SNAPSHOT", json.dumps(summary, ensure_ascii=False), flush=True)
    return summary


def run(out, *, max_pages=0, weekly_only=False, provinces=None):
    with snapshot_lock(out):
        return _run_unlocked(out,max_pages=max_pages,weekly_only=weekly_only,provinces=provinces)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path,
                        default=Path(os.getenv("LOCALAPPDATA") or tempfile.gettempdir()) / "mercati-italia" / "happings-full-crawl")
    parser.add_argument("--max-pages", type=int, default=0,
                        help="Stop after N new pages this invocation; zero means all pending.")
    parser.add_argument("--weekly-only", action="store_true",
                        help="Read only the Italian weekly province indexes, then retry failures once.")
    parser.add_argument("--provinces", type=lambda v: [p for p in v.split(",") if p],
                        help="With --weekly-only: pilot on these page keys, e.g. pistoia,roma")
    opts = parser.parse_args()
    if opts.max_pages < 0:
        parser.error("--max-pages must not be negative")
    if opts.provinces and not opts.weekly_only:
        parser.error("--provinces requires --weekly-only")
    summary = run(opts.out, max_pages=opts.max_pages, weekly_only=opts.weekly_only,
                  provinces=opts.provinces)
    if opts.weekly_only and summary["status_counts"].keys() - {"parsed"}:
        from happings_retry_failures import retry
        print("RETRY", json.dumps(retry(opts.out, max_attempts=2), ensure_ascii=False, default=str), flush=True)


if __name__ == "__main__":
    main()
