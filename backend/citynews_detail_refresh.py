"""Small, persistent queue for reviewed existing Citynews event-detail URLs.

Robots and unsuccessful requests consume the same eight-request allowance.
No redirect is followed: a different edition URL is not the same catalog
identity. Resume replays bounded captured bytes without making new requests.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import re
import time
import zlib
from collections import Counter
from copy import deepcopy
from datetime import date, datetime, timezone
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser

from citynews_detail_enrichment import (
    MAX_BYTES, catalog_urls, parse_document, preview, verify_source_pages,
)
from citynews_urls import source_identity
from citynews_transport import fetch as _http, valid_url as _valid_transport_url
from field_evidence import as_day, fingerprint
import atomic_write

PUBLISHER = "citynews"
STATE_FILENAME = "citynews-detail-state.json"
REPORT_FILENAME = "citynews-detail-refresh.json"
USER_AGENT = "MercatiItaliaEditorialRefresh/1.0"
MAX_RESOURCES = 1000
MAX_STATE_BYTES = 800_000
MAX_REQUESTS = 8
ROBOTS_BYTES = 55_000
DEFAULT_POLICY = {"enabled": True, "max_requests": 8, "max_details": 8,
    "max_seconds": 60, "min_delay_seconds": 2, "overdue_after_days": 45,
    "new_market_ids_allowed": False, "overwrite_unowned_fields": False}
STATUSES = {"unread", "inflight", "retrieved", "layout_held", "unavailable", "robots_denied"}


class _BudgetExhausted(RuntimeError):
    """The next HTTP call has not started and must not count as a failure."""


def validate_policy(policy=None):
    policy = deepcopy(DEFAULT_POLICY if policy is None else policy)
    if (not isinstance(policy, dict) or set(policy) != set(DEFAULT_POLICY)
            or type(policy["enabled"]) is not bool
            or type(policy["max_requests"]) is not int or not 2 <= policy["max_requests"] <= MAX_REQUESTS
            or type(policy["max_details"]) is not int or not 1 <= policy["max_details"] <= MAX_REQUESTS
            or type(policy["max_seconds"]) is not int or not 1 <= policy["max_seconds"] <= 60
            or type(policy["min_delay_seconds"]) is not int or not 2 <= policy["min_delay_seconds"] <= 30
            or type(policy["overdue_after_days"]) is not int or not 1 <= policy["overdue_after_days"] <= 45
            or policy["new_market_ids_allowed"] is not False or policy["overwrite_unowned_fields"] is not False):
        raise ValueError("Unreviewed Citynews request or update policy")
    return policy


def _write(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, sort_keys=True, ensure_ascii=False) + "\n", "utf-8")
    atomic_write.replace(temporary, path)


def _resource(today):
    return {"first_seen": today.isoformat(), "last_attempt": None, "last_read": None,
        "last_parsed": None, "sha256": None, "status": "unread", "attempts": 0,
        "attempt_cycle": 0, "read_cycle": 0, "last_error": None}


def validate_state(state, *, today):
    keys = {"schema", "publisher", "as_of", "cycle", "last_completed_cycle", "last_completed_on", "resources"}
    if (not isinstance(state, dict) or set(state) != keys or state.get("schema") != 1
            or state.get("publisher") != PUBLISHER or not as_day(state.get("as_of"))
            or as_day(state["as_of"]) > today or type(state.get("cycle")) is not int or not 1 <= state["cycle"] <= 100000
            or type(state.get("last_completed_cycle")) is not int
            or not 0 <= state["last_completed_cycle"] <= state["cycle"]
            or (state.get("last_completed_on") is not None and (not as_day(state["last_completed_on"])
                or as_day(state["last_completed_on"]) > today))
            or not isinstance(state.get("resources"), dict) or len(state["resources"]) > MAX_RESOURCES):
        raise ValueError("Invalid bounded Citynews queue")
    for url, item in state["resources"].items():
        if source_identity(url) is None or not isinstance(item, dict) or set(item) != set(_resource(today)):
            raise ValueError("Citynews queue contains an unreviewed resource")
        for field in ("first_seen", "last_attempt", "last_read", "last_parsed"):
            value = item[field]
            if value is not None and (not as_day(value) or as_day(value) > today):
                raise ValueError("Citynews queue observation date is invalid")
        if (item["first_seen"] is None or item["status"] not in STATUSES
                or any(type(item[k]) is not int or not 0 <= item[k] <= 1000000
                       for k in ("attempts", "attempt_cycle", "read_cycle"))
                or item["read_cycle"] > item["attempt_cycle"] or item["attempt_cycle"] > state["cycle"]
                or item["sha256"] is not None and not re.fullmatch(r"[0-9a-f]{64}", str(item["sha256"]))
                or bool(item["last_read"]) != bool(item["sha256"])
                or item["last_read"] and (not item["last_attempt"] or item["last_read"] > item["last_attempt"])
                or item["last_parsed"] and (not item["last_read"] or item["last_parsed"] > item["last_read"])
                or item["last_error"] is not None and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,99}", str(item["last_error"]))):
            raise ValueError("Citynews queue history is inconsistent")
    if len(json.dumps(state, ensure_ascii=False).encode()) > MAX_STATE_BYTES:
        raise ValueError("Citynews queue exceeds its byte bound")
    return deepcopy(state)


def seed_state(rows, previous=None, *, today):
    urls = catalog_urls(rows)
    if len(urls) > MAX_RESOURCES:
        raise ValueError("Citynews existing-source inventory exceeds its bound")
    state = validate_state(previous, today=today) if previous is not None else {
        "schema": 1, "publisher": PUBLISHER, "as_of": today.isoformat(), "cycle": 1,
        "last_completed_cycle": 0, "last_completed_on": None, "resources": {}}
    if state["last_completed_cycle"] == state["cycle"]:
        state["cycle"] += 1
    state["as_of"] = today.isoformat()
    state["resources"] = {url: state["resources"].get(url, _resource(today)) for url in urls}
    return validate_state(state, today=today)


def progress(state, *, today, overdue_after_days=45):
    entries = validate_state(state, today=today)["resources"]
    return {"resources": len(entries), "cycle": state["cycle"],
        "attempted_in_cycle": sum(v["attempt_cycle"] == state["cycle"] for v in entries.values()),
        "read_in_cycle": sum(v["read_cycle"] == state["cycle"] for v in entries.values()),
        "never_read": sum(v["last_read"] is None for v in entries.values()),
        "overdue": sum(v["last_read"] is None or (today - as_day(v["last_read"])).days > overdue_after_days
                       for v in entries.values()),
        "statuses": dict(sorted(Counter(v["status"] for v in entries.values()).items())),
        "market_freshness_guaranteed": False}


def _robots_url(url):
    return "https://" + urlsplit(url).netloc + "/robots.txt"


def _robot_policy(raw, url, minimum):
    text = raw.decode("utf-8-sig", errors="strict")
    if not re.search(r"(?im)^\s*user-agent\s*:", text) or "<html" in text.lower():
        raise ValueError("Citynews robots contains no readable policy")
    robot = RobotFileParser(url); robot.parse(text.splitlines())
    pause = max(minimum, robot.crawl_delay(USER_AGENT) or robot.crawl_delay("*") or 0)
    rate = robot.request_rate(USER_AGENT) or robot.request_rate("*")
    if rate and rate.requests > 0:
        pause = max(pause, rate.seconds / rate.requests)
    if pause > 30:
        raise ValueError("Citynews publisher pacing exceeds the bounded run")
    return robot, pause


def _pack(body, url, read_on):
    return {"url": url, "read_on": read_on, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
            "body_gzip_base64": base64.b64encode(gzip.compress(body, mtime=0)).decode("ascii")}


def _unpack(value, *, today, kind):
    limit = ROBOTS_BYTES if kind == "robots" else MAX_BYTES
    if (not isinstance(value, dict) or set(value) != {"url", "read_on", "bytes", "sha256", "body_gzip_base64"}
            or not _valid_transport_url(value.get("url"), kind) or as_day(value.get("read_on")) != today
            or type(value.get("bytes")) is not int or not (1 if kind == "robots" else 100) <= value["bytes"] <= limit
            or not re.fullmatch(r"[0-9a-f]{64}", str(value.get("sha256") or ""))
            or not isinstance(value.get("body_gzip_base64"), str) or len(value["body_gzip_base64"]) > 2 * limit):
        raise ValueError("Invalid bounded Citynews response checkpoint")
    try:
        packed = base64.b64decode(value["body_gzip_base64"], validate=True)
        with gzip.GzipFile(fileobj=io.BytesIO(packed)) as stream:
            body = stream.read(limit + 1)
    except (OSError, ValueError, TypeError, EOFError, zlib.error):
        raise ValueError("Invalid compressed Citynews response checkpoint") from None
    if len(body) != value["bytes"] or hashlib.sha256(body).hexdigest() != value["sha256"]:
        raise ValueError("Citynews response bytes differ from their saved proof")
    return body


def _state_after(before, attempts, pages, *, today):
    result = deepcopy(before)
    by_url = {p["url"]: p for p in pages}
    for attempt in attempts:
        item = result["resources"][attempt["url"]]
        item.update(last_attempt=today.isoformat(), attempts=item["attempts"] + 1,
                    status=attempt["status"], last_error=attempt.get("error_type"))
        if attempt["status"] != "inflight":
            item["attempt_cycle"] = before["cycle"]
        if attempt["status"] in {"retrieved", "layout_held"}:
            page = by_url[attempt["url"]]
            item.update(last_read=page["read_on"], read_cycle=before["cycle"], sha256=page["sha256"])
            if attempt["status"] == "retrieved":
                item["last_parsed"] = page["read_on"]
    if result["resources"] and all(v["attempt_cycle"] == before["cycle"] for v in result["resources"].values()):
        result.update(last_completed_cycle=before["cycle"], last_completed_on=today.isoformat())
    return validate_state(result, today=today)


def _replay_saved(saved, context, before, policy, *, today):
    if (not isinstance(saved, dict) or set(saved) != {"schema", "context", "state", "requests", "attempts", "robots", "pages"}
            or saved["schema"] != 1 or saved["context"] != context):
        raise ValueError("Citynews resume belongs to another baseline, policy, day or queue")
    requests, attempts, robots, pages = (saved[k] for k in ("requests", "attempts", "robots", "pages"))
    if (any(not isinstance(v, list) for v in (requests, attempts, robots, pages))
            or len(requests) > policy["max_requests"] or len(attempts) > policy["max_details"]
            or any(not isinstance(v, dict) for group in (requests, attempts, robots, pages) for v in group)
            or len({a.get("url") for a in attempts}) != len(attempts)
            or len({p.get("url") for p in pages}) != len(pages)
            or len({p.get("url") for p in robots}) != len(robots)):
        raise ValueError("Citynews checkpoint exceeds bounds or repeats source URLs")
    for request in requests:
        if (not isinstance(request, dict) or set(request) - {"url", "kind", "status", "error_type", "http_status"}
                or not {"url", "kind", "status"} <= set(request)
                or request["status"] not in {"started", "succeeded", "failed"}
                or not _valid_transport_url(request["url"], request["kind"])
                or request.get("error_type") is not None and not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,99}", str(request["error_type"]))
                or request.get("http_status") is not None and (type(request["http_status"]) is not int or not 100 <= request["http_status"] <= 599)):
            raise ValueError("Invalid Citynews checkpoint request")
        if (request["status"] in {"started", "succeeded"} and set(request) != {"url", "kind", "status"}
                or request["status"] == "failed" and not request.get("error_type")):
            raise ValueError("Citynews request lifecycle is inconsistent")
    if len({(r["kind"], r["url"]) for r in requests}) != len(requests):
        raise ValueError("Citynews checkpoint repeats a transport request")
    robot_bodies = {p["url"]: _unpack(p, today=today, kind="robots") for p in robots}
    page_bodies = {p["url"]: _unpack(p, today=today, kind="detail") for p in pages}
    if (set(robot_bodies) != {r["url"] for r in requests if r["kind"] == "robots" and r["status"] == "succeeded"}
            or set(page_bodies) != {r["url"] for r in requests if r["kind"] == "detail" and r["status"] == "succeeded"}):
        raise ValueError("Citynews successful request lost its captured response")
    used, successful_pages = set(), set()
    for attempt in attempts:
        if (not isinstance(attempt, dict) or set(attempt) - {"url", "status", "network_attempted", "robots_request", "page_request", "error_type"}
                or not {"url", "status", "network_attempted", "robots_request", "page_request"} <= set(attempt)
                or attempt["url"] not in before["resources"] or attempt["status"] not in STATUSES - {"unread"}
                or type(attempt["network_attempted"]) is not bool):
            raise ValueError("Invalid Citynews checkpoint attempt")
        url = attempt["url"]
        for key, kind, target in (("robots_request", "robots", _robots_url(url)), ("page_request", "detail", url)):
            index = attempt[key]
            if index is not None:
                if type(index) is not int or not 0 <= index < len(requests) or requests[index]["url"] != target or requests[index]["kind"] != kind:
                    raise ValueError("Citynews attempt lost its exact transport request")
                used.add(index)
        if attempt["network_attempted"] != (attempt["page_request"] is not None):
            raise ValueError("Citynews page-attempt count is inconsistent")
        robot_index = attempt["robots_request"]
        if robot_index is None:
            if attempt["status"] != "inflight" or attempt["page_request"] is not None:
                raise ValueError("Citynews attempted source lacks its robots request")
            continue
        robot_request = requests[robot_index]
        robot = None
        robot_error = None
        if robot_request["status"] == "succeeded":
            raw = robot_bodies.get(_robots_url(url))
            if raw is None:
                raise ValueError("Citynews robots read lost its saved body")
            try:
                robot, _ = _robot_policy(raw, _robots_url(url), policy["min_delay_seconds"])
            except (ValueError, UnicodeError) as error:
                robot_error = type(error).__name__
                if attempt["status"] != "unavailable":
                    raise ValueError("Unreadable Citynews robots was not held") from None
        if attempt["page_request"] is not None and (robot_index >= attempt["page_request"]
                or robot is None or not robot.can_fetch(USER_AGENT, url)):
            raise ValueError("Citynews page request preceded or violated its robots policy")
        if attempt["status"] in {"retrieved", "layout_held"}:
            index = attempt["page_request"]
            if robot is None or not robot.can_fetch(USER_AGENT, url) or index is None or requests[index]["status"] != "succeeded" or url not in page_bodies:
                raise ValueError("Citynews read lacks permitted captured HTTP bytes")
            successful_pages.add(url)
            try:
                parsed = parse_document(page_bodies[url], requested_url=url, today=today)
                recognized = parsed["status"] != "unsupported"
            except (ValueError, KeyError, TypeError):
                recognized = False
            if (attempt["status"] == "retrieved") != recognized:
                raise ValueError("Citynews source layout status differs from its captured body")
            expected_error = None if recognized else "SourceLayoutChanged"
            if attempt.get("error_type") != expected_error:
                raise ValueError("Citynews source layout reason differs from its body")
        elif attempt["status"] == "robots_denied":
            if (robot is None or robot.can_fetch(USER_AGENT, url) or attempt["page_request"] is not None
                    or attempt.get("error_type") != "RobotsDenied"):
                raise ValueError("Citynews robots denial was not proven")
        elif attempt["status"] == "unavailable":
            if not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,99}", str(attempt.get("error_type") or "")):
                raise ValueError("Citynews failed attempt lost its reason")
            failed = requests[attempt["page_request"]] if attempt["page_request"] is not None else robot_request
            if not (failed["status"] == "failed" and failed.get("error_type") == attempt["error_type"]
                    or attempt["page_request"] is None and robot_error == attempt["error_type"]):
                raise ValueError("Citynews terminal failure lacks an actual failed request or unreadable robots")
        elif attempt.get("error_type") is not None:
            raise ValueError("Citynews interrupted request cannot claim a terminal failure")
    if used != set(range(len(requests))) or successful_pages != set(page_bodies):
        raise ValueError("Citynews checkpoint contains unattached transport evidence")
    expected = _state_after(before, attempts, pages, today=today)
    if expected != validate_state(saved["state"], today=today):
        raise ValueError("Citynews queue claims an unobserved read or cycle")
    return expected, requests, attempts, robots, pages


def run(rows, *, out, today, baseline_signature, policy_digest, policy=None,
        previous_state=None, offline=False, resume=False, fetcher=None,
        deadline=None, monotonic=time.monotonic, sleep=time.sleep, now=None):
    """Return (candidate, report, preserve_ids); persisted state is in report.

Every HTTP attempt, including robots and failures, counts toward max_requests.
The caller may impose its existing shared deadline; this reader never raises it.
"""
    policy = validate_policy(policy)
    if not isinstance(today, date) or not baseline_signature or not policy_digest:
        raise ValueError("Missing Citynews source candidate context")
    before = seed_state(rows, previous_state, today=today)
    state = deepcopy(before)
    context = {"date": today.isoformat(), "baseline": baseline_signature, "pipeline_policy": policy_digest,
               "policy": policy, "catalog": fingerprint(rows), "state_before": fingerprint(before)}
    out = Path(out); checkpoint = out / "sources/citynews-detail-pages.json"
    started = monotonic(); end = started + policy["max_seconds"]
    if deadline is not None: end = min(end, deadline)
    requests, attempts, robots, pages = [], [], [], []
    http = fetcher or _http; now = now or (lambda: datetime.now(timezone.utc))
    status, stop_reason = "disabled", "disabled"

    def save():
        nonlocal state
        state = _state_after(before, attempts, pages, today=today)
        _write(checkpoint, {"schema": 1, "context": context, "state": state, "requests": requests,
                            "attempts": attempts, "robots": robots, "pages": pages})

    def read(url, kind, attempt, key):
        if len(requests) >= policy["max_requests"] or end - monotonic() <= .1:
            raise _BudgetExhausted("Citynews request or time allowance exhausted")
        stamp = now()
        if stamp.tzinfo is None or stamp.date() != today:
            raise ValueError("Citynews acquisition day differs from candidate day")
        attempt[key] = len(requests)
        if kind == "detail": attempt["network_attempted"] = True
        item = {"url": url, "kind": kind, "status": "started"}; requests.append(item); save()
        remaining = end - monotonic()
        if remaining <= .1:
            # Saving progress may consume the last available time. Nothing
            # was sent, so remove the intent instead of claiming an HTTP try.
            requests.pop(); attempt[key] = None
            if kind == "detail": attempt["network_attempted"] = False
            save()
            raise _BudgetExhausted("Citynews deadline reached before HTTP started")
        try:
            limit = ROBOTS_BYTES if kind == "robots" else MAX_BYTES
            body, final = http(url, timeout=min(12, remaining), max_bytes=limit,
                               accept="text/plain" if kind == "robots" else "text/html")
            if final != url or not isinstance(body, bytes) or not (1 if kind == "robots" else 100) <= len(body) <= limit:
                raise ValueError("Citynews response changed exact URL or byte bound")
            stamp = now()
            if stamp.tzinfo is None or stamp.date() != today:
                raise ValueError("Citynews acquisition crossed candidate day")
            item["status"] = "succeeded"
            packed = _pack(body, url, stamp.date().isoformat())
            (robots if kind == "robots" else pages).append(packed)
            return body, len(requests) - 1
        except (OSError, HTTPException, ValueError, TypeError) as error:
            item.update(status="failed", error_type=type(error).__name__)
            if isinstance(error, HTTPError): item["http_status"] = error.code
            raise

    if policy["enabled"] and resume:
        status, stop_reason = "resume_missing_evidence", "resume_missing_evidence"
        if checkpoint.is_file():
            if checkpoint.stat().st_size > MAX_REQUESTS * MAX_BYTES * 2 + MAX_STATE_BYTES:
                raise ValueError("Citynews response checkpoint exceeds its bound")
            saved = json.loads(checkpoint.read_text("utf-8"))
            state, requests, attempts, robots, pages = _replay_saved(saved, context, before, policy, today=today)
            status, stop_reason = "resumed", "saved_checkpoint_only"
    elif policy["enabled"] and offline:
        status, stop_reason = "offline_skipped", "offline"
    elif policy["enabled"]:
        status, stop_reason = "completed", "queue_exhausted"
        cache, failures, last_contact = {}, set(), {}
        pending = sorted((url for url, value in before["resources"].items() if value["attempt_cycle"] < before["cycle"]),
                         key=lambda url: (before["resources"][url]["last_attempt"] or "", url))
        if not pending: stop_reason = "no_catalog_rows"
        for url in pending:
            robot_url = _robots_url(url)
            if robot_url in failures: continue
            needed = 1 if robot_url in cache else 2
            if len(requests) + needed > policy["max_requests"]:
                stop_reason = "request_limit"; break
            if len(attempts) >= policy["max_details"]:
                stop_reason = "detail_limit"; break
            if end - monotonic() <= 1:
                stop_reason = "time_budget"; break
            attempt = {"url": url, "status": "inflight", "network_attempted": False,
                       "robots_request": None, "page_request": None}
            attempts.append(attempt)
            try:
                if robot_url not in cache:
                    body, index = read(robot_url, "robots", attempt, "robots_request")
                    last_contact[robot_url] = monotonic()
                    robot, pause = _robot_policy(body, robot_url, policy["min_delay_seconds"])
                    cache[robot_url] = (robot, pause, index)
                robot, pause, index = cache[robot_url]
                attempt["robots_request"] = index
                if not robot.can_fetch(USER_AGENT, url):
                    attempt.update(status="robots_denied", error_type="RobotsDenied"); save(); continue
                wait = max(0, last_contact.get(robot_url, started) + pause - monotonic())
                if end - monotonic() <= wait + .1:
                    stop_reason = "time_budget"; save(); break
                if wait: sleep(wait)
                try:
                    body, _ = read(url, "detail", attempt, "page_request")
                finally:
                    # Failed requests consume the publisher's pacing too.
                    last_contact[robot_url] = monotonic()
                try:
                    parsed = parse_document(body, requested_url=url, today=today)
                    recognized = parsed["status"] != "unsupported"
                except (ValueError, KeyError, TypeError):
                    recognized = False
                attempt["status"] = "retrieved" if recognized else "layout_held"
                if not recognized: attempt["error_type"] = "SourceLayoutChanged"
            except _BudgetExhausted:
                stop_reason = "time_budget"; save(); break
            except (OSError, HTTPException, ValueError, TypeError, UnicodeError) as error:
                attempt.update(status="unavailable", error_type=type(error).__name__)
                if robot_url not in cache: failures.add(robot_url)
            save()
        save()
        _replay_saved(json.loads(checkpoint.read_text("utf-8")), context, before, policy, today=today)
    documents, parsed_pages, parse_holds = [], [], []
    for packed in pages:
        body = _unpack(packed, today=today, kind="detail")
        try:
            doc = parse_document(body, requested_url=packed["url"], today=today)
            documents.append({"read_on": packed["read_on"], "parsed": doc})
            parsed_pages.append({"requested_url": packed["url"], "final_url": packed["url"],
                                 "read_on": packed["read_on"], "html": body})
            if doc["status"] == "unsupported": parse_holds.append({"url": packed["url"], "reason": "SourceLayoutChanged"})
        except (ValueError, KeyError, TypeError) as error:
            parse_holds.append({"url": packed["url"], "reason": type(error).__name__})
    verify_source_pages(parsed_pages, documents, today=today)
    result, evidence = preview(rows, documents, today=today)
    report = {"schema": 1, "publisher": PUBLISHER, "date": today.isoformat(), "enabled": policy["enabled"],
        "status": status, "stop_reason": stop_reason, "policy": policy,
        "network_requests": 0 if resume else len(requests), "captured_network_requests": len(requests),
        "details_attempted": len(attempts), "source_pages_read": len(pages),
        "documents_parsed": sum(v["parsed"]["status"] != "unsupported" for v in documents),
        "requests": requests, "attempts": attempts, "parse_holds": parse_holds,
        "robots": [{k: v for k, v in p.items() if k != "body_gzip_base64"} for p in robots],
        "source_pages": [{"requested_url": p["url"], "final_url": p["url"], "read_on": p["read_on"],
                          "bytes": p["bytes"], "sha256": p["sha256"]} for p in pages],
        "elapsed_seconds": round(max(0, monotonic() - started), 3), "state": state,
        "progress": progress(state, today=today, overdue_after_days=policy["overdue_after_days"]),
        "evidence": evidence}
    _write(out / STATE_FILENAME, state); _write(out / REPORT_FILENAME, report)
    preserve = {v["slug"] for v in evidence["outcomes"] if v["status"] != "held"}
    return result, report, preserve
