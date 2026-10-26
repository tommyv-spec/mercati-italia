"""Find editorial market pages the catalog does not have yet, and admit the safe ones.

One mechanism for every reviewed publisher, configured per publisher and never
per market: the publisher's own index pages (a sitemap or listing pages) give
candidate page URLs; the existing page reader parses each candidate; general
admission rules decide. A new record carries the same editorial evidence and
field receipts that the existing re-read path builds, so later re-reads own it.

Admission is fail-closed. A page is held when it has any conflict, is an old
edition, has no ISTAT municipality, no app category, no upcoming date after the
export rules, or looks like a market the catalog (or this run) already has.
"""
from __future__ import annotations

import hashlib
import json
import re
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from html import unescape
from http.client import HTTPException
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import eventiesagre_detail_refresh as editorial
from editorial_calendar_scope import KEY, clean_editorial_evidence, source_identity, text_key
from editorial_transport import INDEX_ACCEPT, discovery_index_url, failure_code, fetch as _http
from eventiesagre_source_layout import MAX_BYTES
from field_evidence import FIELDS, as_day, clean_receipts, fingerprint
from recurrence_refresh import explicit_rule
import atomic_write

SCHEMA = 1
POLICY_PATH = editorial.POLICY_PATH
PUBLISHERS = {"eventiesagre.it": "eventiesagre", "cosedicasa.com": "cosedicasa"}
ORDER = tuple(PUBLISHERS)
REPORT_FILENAME = "editorial-discovery.json"
MAX_INDEXES = 2000
MAX_CANDIDATES = 8000
MAX_LINKS = 20_000
MAX_STATE_BYTES = 4_000_000
MAX_INDEX_REQUESTS = 12
MAX_CANDIDATE_READS = 24
MAX_NEW = 16
MAX_SECONDS = 180
UNAVAILABLE_RETRY_DAYS = 2
POLICY_KEYS = {"publisher", "enabled", "new_market_ids_allowed", "reuse_permission_verified",
               "owner_decision", "index_format", "seed_urls", "follow_pattern", "category_rules",
               "max_index_requests", "max_candidate_reads", "max_new", "max_seconds",
               "min_delay_seconds", "recheck_after_days"}
INDEX_KEYS = {"first_seen", "last_checked", "lastmod", "status", "links", "error"}
INDEX_STATUSES = {"unread", "read", "unavailable", "robots_denied"}
CANDIDATE_KEYS = {"first_seen", "last_attempt", "attempts", "lastmod", "status", "reason"}
CANDIDATE_STATUSES = {"pending", "held", "unavailable", "robots_denied"}
NO_NEW_STATE = {"disabled", "offline_skipped", "resume_missing_evidence"}
LOC = re.compile(r"<(url|sitemap)>(.*?)</\1>", re.S | re.I)
HREF = re.compile(r"""\bhref\s*=\s*["']([^"'<>]{1,700})["']""", re.I)


def state_filename(publisher):
    return PUBLISHERS[publisher] + "-discovery-state.json"


STATE_FILENAMES = frozenset(state_filename(p) for p in PUBLISHERS)


def _write(path, value, *, sort_keys=True):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=sort_keys) + "\n", "utf-8")
    atomic_write.replace(temporary, path)


def _write_state(path, state):
    # Queue order is the order pages were discovered (a listing's own order);
    # sorting keys would replace it with alphabetical URLs on the next run.
    _write(path, state, sort_keys=False)


# ---------------------------------------------------------------- policy

def validate_policy(policy=None, *, publisher):
    """One publisher's discovery contract; anything unexpected fails closed."""
    if publisher not in PUBLISHERS:
        raise ValueError("Unreviewed editorial discovery publisher")
    if policy is None:
        registry = json.loads(POLICY_PATH.read_text("utf-8"))
        if registry.get("schema") != 1 or registry.get("publication_channel") != "dev-only":
            raise ValueError("Invalid editorial source policy")
        policy = (registry.get("discovery") or {}).get(PUBLISHERS[publisher])
    def bounded(key, low, high):
        return type(policy.get(key)) is int and low <= policy[key] <= high
    if (not isinstance(policy, dict) or set(policy) != POLICY_KEYS
            or policy["publisher"] != publisher
            or type(policy["enabled"]) is not bool
            # Admission happens only when this is literally True.
            or type(policy["new_market_ids_allowed"]) is not bool
            # The owner accepted these publishers without a reuse grant; the
            # contract must keep saying so rather than imply permission.
            or policy["reuse_permission_verified"] is not False
            or not isinstance(policy["owner_decision"], str) or not 20 <= len(policy["owner_decision"]) <= 400
            or policy["index_format"] not in INDEX_ACCEPT
            or not isinstance(policy["seed_urls"], list) or not 1 <= len(policy["seed_urls"]) <= 200
            or not isinstance(policy["follow_pattern"], str) or not 10 <= len(policy["follow_pattern"]) <= 400
            or not isinstance(policy["category_rules"], list) or not 1 <= len(policy["category_rules"]) <= 30
            or not bounded("max_index_requests", 1, MAX_INDEX_REQUESTS)
            or not bounded("max_candidate_reads", 1, MAX_CANDIDATE_READS)
            or not bounded("max_new", 1, MAX_NEW)
            or not bounded("max_seconds", 10, MAX_SECONDS)
            or not bounded("min_delay_seconds", 2, 30)
            or not bounded("recheck_after_days", 1, 365)):
        raise ValueError("Unreviewed editorial discovery policy")
    try:
        re.compile(policy["follow_pattern"])
        for rule in policy["category_rules"]:
            if (not isinstance(rule, list) or len(rule) != 3 or rule[0] not in {"url", "name"}
                    or not isinstance(rule[1], str) or not 1 <= len(rule[1]) <= 300
                    or rule[2] not in _categories()):
                raise ValueError
            re.compile(rule[1])
    except (re.error, ValueError, TypeError):
        raise ValueError("Unreviewed editorial discovery pattern or category rule") from None
    discovery = {PUBLISHERS[publisher]: policy}
    if (len(set(policy["seed_urls"])) != len(policy["seed_urls"])
            or any(not discovery_index_url(url, discovery=discovery) for url in policy["seed_urls"])):
        raise ValueError("Discovery seed is outside the publisher's own index pages")
    return deepcopy(policy)


def _categories():
    from export_static import VALID_CATEGORIES
    return VALID_CATEGORIES


def configuration(*, enabled=True):
    """Validate every publisher's discovery contract before anything is read."""
    if type(enabled) is not bool:
        raise ValueError("Discovery enablement must be an explicit boolean")
    return {"schema": SCHEMA, "enabled": enabled,
            "publishers": {p: validate_policy(publisher=p) for p in ORDER}}


def _active(config, publisher):
    return config["enabled"] and config["publishers"][publisher]["enabled"]


def reserved_seconds(config):
    """Wall-clock time the daily job keeps aside for discovery."""
    return max((config["publishers"][p]["max_seconds"] for p in ORDER if _active(config, p)), default=0)


def _caps(config):
    return {p: config["publishers"][p]["max_new"]
            if _active(config, p) and config["publishers"][p]["new_market_ids_allowed"] is True else 0
            for p in ORDER}


# ---------------------------------------------------------------- state

def _index_entry(today, lastmod=""):
    return {"first_seen": today.isoformat(), "last_checked": None, "lastmod": lastmod,
            "status": "unread", "links": 0, "error": None}


def _candidate_entry(today, lastmod=""):
    return {"first_seen": today.isoformat(), "last_attempt": None, "attempts": 0,
            "lastmod": lastmod, "status": "pending", "reason": None}


def _lastmod(value):
    day = as_day(str(value or "")[:10])
    return day.isoformat() if day else ""


def validate_state(state, *, today, publisher, policy):
    if (not isinstance(state, dict) or set(state) != {"schema", "publisher", "indexes", "candidates"}
            or state["schema"] != SCHEMA or state["publisher"] != publisher
            or not isinstance(state["indexes"], dict) or len(state["indexes"]) > MAX_INDEXES
            or not isinstance(state["candidates"], dict) or len(state["candidates"]) > MAX_CANDIDATES):
        raise ValueError("Invalid editorial discovery state")
    discovery = {PUBLISHERS[publisher]: policy}
    for url, entry in state["indexes"].items():
        if (not discovery_index_url(url, discovery=discovery) or not isinstance(entry, dict)
                or set(entry) != INDEX_KEYS or entry["status"] not in INDEX_STATUSES
                or type(entry["links"]) is not int or not 0 <= entry["links"] <= MAX_LINKS
                or entry["error"] is not None and (not isinstance(entry["error"], str) or len(entry["error"]) > 40)):
            raise ValueError("Invalid editorial discovery index entry")
        _days(entry, ("first_seen", "last_checked", "lastmod"), today)
        if (entry["status"] == "unread") != (entry["last_checked"] is None):
            raise ValueError("Discovery index check history is inconsistent")
    for url, entry in state["candidates"].items():
        if ((source_identity(url) or (None,))[0] != publisher or not isinstance(entry, dict)
                or set(entry) != CANDIDATE_KEYS or entry["status"] not in CANDIDATE_STATUSES
                or type(entry["attempts"]) is not int or not 0 <= entry["attempts"] <= 100000
                or entry["reason"] is not None and (not isinstance(entry["reason"], str) or len(entry["reason"]) > 80)):
            raise ValueError("Invalid editorial discovery candidate")
        _days(entry, ("first_seen", "last_attempt", "lastmod"), today)
        if bool(entry["attempts"]) != bool(entry["last_attempt"]) or (
                entry["status"] != "pending") != bool(entry["attempts"]):
            raise ValueError("Discovery candidate attempt history is inconsistent")
    if len(json.dumps(state, ensure_ascii=False).encode()) > MAX_STATE_BYTES:
        raise ValueError("Editorial discovery state exceeds its byte bound")
    return deepcopy(state)


def _days(entry, keys, today):
    for key in keys:
        value = entry[key]
        if key == "lastmod" and value == "":
            continue
        if key != "first_seen" and value is None:
            continue
        day = as_day(value)
        if day is None or key != "lastmod" and day > today:
            raise ValueError("Editorial discovery state has an invalid or future day")


def catalog_identities(rows, publisher=None):
    """Every source page identity the catalog already holds, aliases included."""
    found = set()
    for row in rows:
        urls = [row.get("url_fonte")]
        urls += [s.get("url") for s in row.get("fonti") or [] if isinstance(s, dict)]
        evidence = row.get(KEY) if isinstance(row.get(KEY), dict) else {}
        urls += [evidence.get(k) for k in ("requested_url", "final_url", "canonical_url")]
        for url in urls:
            identity = source_identity(url)
            if identity and (publisher is None or identity[0] == publisher):
                found.add(identity)
    return found


def seed_state(previous, *, rows, today, publisher, policy):
    state = (validate_state(previous, today=today, publisher=publisher, policy=policy)
             if previous is not None else
             {"schema": SCHEMA, "publisher": publisher, "indexes": {}, "candidates": {}})
    discovery = {PUBLISHERS[publisher]: policy}
    # A narrowed policy drops index pages it no longer covers.
    state["indexes"] = {u: e for u, e in state["indexes"].items()
                        if discovery_index_url(u, discovery=discovery)}
    for url in policy["seed_urls"]:
        state["indexes"].setdefault(url, _index_entry(today))
    known = catalog_identities(rows, publisher)
    state["candidates"] = {u: e for u, e in state["candidates"].items() if source_identity(u) not in known}
    return validate_state(state, today=today, publisher=publisher, policy=policy)


def _newest_first(day):
    """Sort key putting later ISO days first and undated entries last."""
    return "".join(chr(0x7F - ord(c)) for c in day) if day else "\x7f"


def _next_index(state, today, seeds=()):
    day = today.isoformat()
    ranked = []
    for order, (url, entry) in enumerate(state["indexes"].items()):
        if entry["last_checked"] == day:
            continue
        unread = entry["status"] == "unread"
        changed = bool(entry["lastmod"] and entry["last_checked"] and entry["lastmod"] > entry["last_checked"])
        # Unread first (seeds, then newest sitemap), then changed ones, then the oldest check.
        ranked.append((not unread, not changed, unread and url not in seeds,
                       _newest_first(entry["lastmod"]) if unread else "",
                       entry["last_checked"] or "", entry["first_seen"], order, url))
    return min(ranked)[-1] if ranked else None


def next_candidates(state, *, today, limit, recheck_after_days):
    """Never-read pages first (newest sitemap date first), then due rechecks."""
    day = today.isoformat()
    recheck = (today - timedelta(days=recheck_after_days)).isoformat()
    retry = (today - timedelta(days=UNAVAILABLE_RETRY_DAYS)).isoformat()
    ranked = []
    # Ties keep discovery order: a listing's own order (soonest first) is the best hint.
    for order, (url, entry) in enumerate(state["candidates"].items()):
        if entry["last_attempt"] == day:
            continue
        if entry["status"] == "pending":
            rank = 0
        elif entry["lastmod"] and entry["lastmod"] > entry["last_attempt"]:
            rank = 1   # the page changed after we last read it
        elif entry["status"] == "unavailable" and entry["last_attempt"] <= retry:
            rank = 2
        elif entry["last_attempt"] <= recheck:
            rank = 3
        else:
            continue
        ranked.append((rank, _newest_first(entry["lastmod"]), entry["last_attempt"] or "",
                       entry["first_seen"], order, url))
    return [item[-1] for item in sorted(ranked)[:limit]]


def extract_links(body, *, base_url, index_format):
    """(url, lastmod) pairs from a sitemap or every href of a listing page."""
    text = body.decode("utf-8", errors="replace")
    found = {}
    if index_format == "sitemap_xml":
        for match in LOC.finditer(text):
            loc = re.search(r"<loc>\s*([^<\s]+)\s*</loc>", match[2], re.I)
            mod = re.search(r"<lastmod>\s*([^<\s]+)\s*</lastmod>", match[2], re.I)
            if loc:
                found.setdefault(unescape(loc[1]), _lastmod(mod[1] if mod else ""))
    else:
        for href in HREF.findall(text):
            # A raw space in a listing href stands for the "+" of the canonical URL.
            url = urljoin(base_url, unescape(href.strip())).replace(" ", "+")
            found.setdefault(url, "")
    if len(found) > MAX_LINKS:
        raise ValueError("Publisher index exceeds its bounded link count")
    return list(found.items())


# ---------------------------------------------------------------- network

def acquire(rows, *, publisher, policy, previous_state, today, deadline=None, fetcher=None,
            monotonic=time.monotonic, sleep=time.sleep, now=None):
    """Read index pages and candidate pages for one publisher, politely and bounded.

Returns (state, pages, report). Pages are the observed bytes of candidate
detail pages read today; nothing is admitted here.
"""
    state = seed_state(previous_state, rows=rows, today=today, publisher=publisher, policy=policy)
    http = fetcher or _http
    now = now or (lambda: datetime.now(timezone.utc))
    started = monotonic()
    end = started + policy["max_seconds"]
    if deadline is not None:
        end = min(end, deadline)
    known = catalog_identities(rows, publisher)
    discovery = {PUBLISHERS[publisher]: policy}
    accept = INDEX_ACCEPT[policy["index_format"]]
    report = {"status": "running", "stop_reason": "budget_complete", "network_requests": 0,
              "robots": None, "index_pages_read": 0, "index_failures": {}, "links_seen": 0,
              "new_candidates_found": 0, "candidates_attempted": 0, "candidate_pages_read": 0,
              "candidate_failures": {}}
    pages = []

    def remaining():
        return end - monotonic()

    def get(url, kind):
        report["network_requests"] += 1
        body, final = http(url, timeout=min(18, max(.1, remaining())), max_bytes=MAX_BYTES, accept=kind)
        if final != url or not isinstance(body, bytes) or not 100 <= len(body) <= MAX_BYTES:
            raise ValueError("Discovery response changed destination or size")
        stamp = now()
        if stamp.tzinfo is None or stamp.date() != today:
            raise ValueError("Discovery read date differs from the candidate date")
        return body

    robots_url = "https://www." + publisher + "/robots.txt"
    if remaining() < 1:
        report.update(status="time_budget_exhausted", stop_reason="time_budget")
        return state, pages, report
    try:
        report["network_requests"] += 1
        raw, final = http(robots_url, timeout=min(18, remaining()), max_bytes=55_000, accept="text/plain")
        if final != robots_url or not isinstance(raw, bytes) or not 1 <= len(raw) <= 55_000:
            raise ValueError("Robots response changed destination or size")
        text = raw.decode("utf-8-sig", errors="strict")
        if not re.search(r"(?im)^\s*user-agent\s*:", text) or "<html" in text.lower():
            raise ValueError("Robots contains no readable policy")
        robots = RobotFileParser(robots_url)
        robots.parse(text.splitlines())
        pause = editorial._delay(robots, policy["min_delay_seconds"])
        report["robots"] = {"url": robots_url, "sha256": hashlib.sha256(raw).hexdigest(),
                            "bytes": len(raw), "pacing_seconds": pause}
    except (OSError, HTTPException, ValueError, UnicodeError) as error:
        report.update(status="robots_unavailable", stop_reason=failure_code(error))
        return state, pages, report

    for _ in range(policy["max_index_requests"]):
        url = _next_index(state, today, set(policy["seed_urls"]))
        if url is None:
            break
        if remaining() <= pause + 1:
            report["stop_reason"] = "time_budget"
            break
        entry = state["indexes"][url]
        entry.update(last_checked=today.isoformat(), error=None)
        if not robots.can_fetch(editorial.USER_AGENT, url):
            entry.update(status="robots_denied", error="robots_denied")
            continue
        sleep(pause)
        try:
            body = get(url, accept)
            links = extract_links(body, base_url=url, index_format=policy["index_format"])
        except (OSError, HTTPException, ValueError, UnicodeError) as error:
            code = failure_code(error)
            entry.update(status="unavailable", error=code)
            report["index_failures"][code] = report["index_failures"].get(code, 0) + 1
            continue
        entry.update(status="read", links=len(links))
        report["index_pages_read"] += 1
        report["links_seen"] += len(links)
        for link, lastmod in links:
            identity = source_identity(link)
            if identity and identity[0] == publisher:
                if identity in known or not _may_have_category(policy["category_rules"], link):
                    continue
                if link in state["candidates"]:
                    if lastmod:
                        state["candidates"][link]["lastmod"] = lastmod
                elif len(state["candidates"]) < MAX_CANDIDATES:
                    state["candidates"][link] = _candidate_entry(today, lastmod)
                    report["new_candidates_found"] += 1
            elif discovery_index_url(link, discovery=discovery):
                if link in state["indexes"]:
                    if lastmod:
                        state["indexes"][link]["lastmod"] = lastmod
                elif len(state["indexes"]) < MAX_INDEXES:
                    state["indexes"][link] = _index_entry(today, lastmod)

    if report["stop_reason"] == "budget_complete":
        for url in next_candidates(state, today=today, limit=policy["max_candidate_reads"],
                                   recheck_after_days=policy["recheck_after_days"]):
            if remaining() <= pause + 1:
                report["stop_reason"] = "time_budget"
                break
            entry = state["candidates"][url]
            entry.update(last_attempt=today.isoformat(), attempts=entry["attempts"] + 1, reason=None)
            report["candidates_attempted"] += 1
            if not robots.can_fetch(editorial.USER_AGENT, url):
                entry.update(status="robots_denied", reason="robots_denied")
                continue
            sleep(pause)
            try:
                body = get(url, "text/html")
            except (OSError, HTTPException, ValueError, UnicodeError) as error:
                code = failure_code(error)
                entry.update(status="unavailable", reason=code)
                report["candidate_failures"][code] = report["candidate_failures"].get(code, 0) + 1
                continue
            # Status is settled by admission; until then it was read today.
            entry.update(status="held", reason="read_not_evaluated")
            pages.append({"requested_url": url, "final_url": url, "read_on": today.isoformat(),
                          "body": body, "redirects": [], "redirect_observed": False})
            report["candidate_pages_read"] += 1
    report["status"] = "completed"
    report["elapsed_seconds"] = round(max(0, monotonic() - started), 3)
    return validate_state(state, today=today, publisher=publisher, policy=policy), pages, report


# ---------------------------------------------------------------- admission

@lru_cache(maxsize=1)
def _istat_regions():
    return json.loads((Path(__file__).resolve().parent / "data/istat-comuni-2026.json")
                      .read_text("utf-8"))["provinces_by_region"]


def _canonical_place(location):
    """ISTAT municipality, province code and region for an observed location."""
    normalized = editorial._normalized_location(location)
    if normalized is None:
        return None
    names = [city for city, province in _istat_regions()[normalized["region"]].items()
             if province == normalized["province"] and text_key(city) == text_key(location.get("city"))]
    if len(names) != 1:
        return None
    return {**normalized, "city": names[0]}


def _category(rules, url, name):
    for field, pattern, category in rules:
        if re.search(pattern, url if field == "url" else name, re.I):
            return category
    return None


def _may_have_category(rules, url):
    """Skip pages whose URL already rules out every app category (e.g. a sagra)."""
    return any(field == "name" or re.search(pattern, url, re.I) for field, pattern, _ in rules)


def _slug_options(name, city, url):
    from export_static import slugify
    base = slugify(name + "-" + city)[:80].strip("-") or "mercato"
    return base, base[:73].rstrip("-") + "-" + hashlib.sha256(url.encode()).hexdigest()[:6]


def candidate_row(document, *, read_on, today, policy, slug):
    """(raw row, normalized export row) for a parsed page, or (None, hold reason).

`slug` picks the identifier from its two allowed forms; the rest is a pure
function of the observed page, so a verifier rebuilds exactly the same row.
"""
    from export_static import concluded_reason, normalize
    from recurrence_refresh import refresh_record
    source, event = document["source"], document["event"]
    publisher, url = source["publisher"], source["requested_url"]
    if document["status"] != "parsed" or document["conflicts"]:
        return None, "source_conflict"
    if event.get("archive_marker") or event.get("edition_intervals") and all(
            str(i.get("end")) < today.isoformat() for i in event["edition_intervals"]):
        return None, "past_or_archived_edition"
    observed = event.get("observed_location") or event.get("location") or {}
    place = _canonical_place(observed)
    if place is None:
        return None, "istat_geography_unresolved"
    name = event.get("name")
    if (not isinstance(name, str) or not 3 <= len(name.strip()) <= 160 or "�" in name
            or any(ord(c) < 32 for c in name)):
        return None, "name_missing_or_unbounded"
    name = " ".join(name.split())
    category = _category(policy["category_rules"], url, name)
    if category is None:
        return None, "category_not_in_app"
    local = deepcopy(document)
    local["event"]["observed_location"] = deepcopy(observed)
    local["event"]["location"] = {**deepcopy(event.get("location") or {}),
                                  "city": place["city"], "province": place["province"],
                                  "region": place["region"]}
    recurrence = event.get("recurrence_text") or ""
    if not isinstance(recurrence, str) or len(recurrence) > FIELDS["ricorrenza_testo"] or not explicit_rule(recurrence):
        recurrence = ""
    market_id = slug(*_slug_options(name, place["city"], url))
    if market_id is None:
        return None, "identifier_collision"
    skeleton = {
        "slug": market_id, "nome": name, "citta": place["city"], "provincia": place["province"],
        "regione": place["region"], "indirizzo": "", "lat": None, "lng": None,
        "position_quality": "sconosciuta", "categoria": category, "tags": [],
        "status": "non_confermato", "orario_testo": "", "ricorrenza_testo": recurrence,
        "descrizione": "", "date": [], "date_quality": "sconosciuta",
        "proiezione_regola": None, "proiezione_generata_il": "", "proiezione_fonte": "",
        "confidence": 0, "fonte": publisher, "url_fonte": url,
        "fonti": [{"nome": publisher, "url": url}], "verificato_il": "", "aggiornato_il": "",
        "fonte_letta_il": read_on, "importato_il": today.isoformat()}
    # The re-read path binds the page, builds its evidence and field receipts,
    # assigns address/hours it can prove and limits the calendar to the page.
    row, outcome = editorial._update(skeleton, local, read_on=read_on, today=today)
    if outcome["status"] == "held":
        return None, outcome["reason"]
    if not row.get(KEY):
        return None, "source_evidence_not_bindable"
    # Ask the real downstream rules: the daily forecast, then the exporter.
    projected, _ = refresh_record(row, today)
    normalized, error = normalize(projected, today)
    if error:
        return None, "export_rejects_" + error
    # A date after today: a page whose only date is today would be hidden tomorrow.
    if not any(d > today.isoformat() for d in normalized["date"]) or concluded_reason(normalized, today):
        return None, "no_upcoming_date"
    return row, normalized


def _town(row):
    return text_key(row.get("regione")), text_key(row.get("citta"))


def _weekdays(row):
    from recurrence_refresh import forecast_rule
    rule = forecast_rule(row)
    if rule:
        return frozenset(rule.get("weekdays") or [rule.get("weekday")])
    return frozenset(d.weekday() for d in map(as_day, row.get("date") or []) if d)


def _generic_weekly(row):
    from catalog_quality_report import GENERIC_WEEKLY, key
    return bool(GENERIC_WEEKLY.match(key(row.get("nome"))))


def duplicate_reason(candidate, town_rows, *, strict=True):
    """(reason, existing ID) when `candidate` would be a second card, else None.

The general export rule (same venue and calendar, any source) plus the same
name in the same town. `strict` also holds a market on the same weekdays in the
same town with the same category, or a generic "mercato settimanale di ..."
candidate on a weekday the town already has: a possible copy whose address
is too vague to tell apart. The strongest matching reason is reported.
"""
    from export_static import comparable_market_name, same_market, same_venue
    others = [row for row in town_rows if row.get("slug") != candidate["slug"]]
    for row in others:
        if same_market(row, candidate) or same_venue(row, candidate):
            return "same_venue_and_calendar", row.get("slug")
    name = comparable_market_name(candidate["nome"])
    for row in others:
        if name and comparable_market_name(str(row.get("nome") or "")) == name:
            return "same_name_in_town", row.get("slug")
    days = _weekdays(candidate) if strict else None
    generic = strict and _generic_weekly(candidate)
    for row in others if days else ():
        if _weekdays(row) == days and (row.get("categoria") == candidate["categoria"] or generic):
            return "same_town_and_weekdays", row.get("slug")
    return None


def admit(rows, observations, *, today, config):
    """Admit new markets from parsed pages; deterministic for its verifier."""
    caps = _caps(config)
    result = deepcopy(rows)
    towns = {}
    for row in result:
        towns.setdefault(_town(row), []).append(row)
    taken = {row.get("slug") for row in result}
    known = catalog_identities(result)
    seen, outcomes, new_ids, counts = set(), [], [], Counter()
    for observed in observations:
        if not isinstance(observed, dict) or set(observed) != {"read_on", "parsed"}:
            raise ValueError("Discovery document lost its read date")
        document, read_on = observed["parsed"], observed["read_on"]
        source = editorial._valid_document(document, read_on, today)
        publisher, url = source["publisher"], source["requested_url"]
        if publisher not in PUBLISHERS or url in seen:
            raise ValueError("Repeated or unreviewed discovery page")
        seen.add(url)
        outcome = {"url": url, "publisher": publisher, "status": "held", "reason": None,
                   "market_id": None}
        if document["conflicts"]:
            outcome["conflicts"] = sorted({str(c.get("code")) for c in document["conflicts"]
                                           if isinstance(c, dict)})[:10]
        if source_identity(url) in known:
            outcome["reason"] = "already_in_catalog"
        elif caps[publisher] == 0:
            outcome["reason"] = "admission_disabled"
        else:
            def pick(base, hashed):
                return base if base not in taken else hashed if hashed not in taken else None
            try:
                row, normalized = candidate_row(document, read_on=read_on, today=today,
                                                policy=config["publishers"][publisher], slug=pick)
            except (ValueError, KeyError, TypeError) as error:
                # One unrepresentable page is a hold, never a failed daily run.
                row, normalized = None, "source_detail_not_representable"
                outcome["error_type"] = type(error).__name__
            if row is None:
                outcome["reason"] = normalized
            elif duplicate := duplicate_reason(normalized, towns.get(_town(normalized), [])):
                outcome["reason"], outcome["duplicate_of"] = duplicate
            elif sum(o["status"] == "admitted" and o["publisher"] == publisher for o in outcomes) >= caps[publisher]:
                outcome["reason"] = "per_run_cap_reached"
            else:
                result.append(row)
                towns.setdefault(_town(normalized), []).append(normalized)
                taken.add(row["slug"])
                known.add(source_identity(url))
                new_ids.append(row["slug"])
                outcome.update(status="admitted", market_id=row["slug"],
                               dates=len(normalized["date"]), date_quality=normalized["date_quality"])
        counts[outcome["reason"] or "admitted"] += 1
        outcomes.append(outcome)
    report = {"schema": SCHEMA, "date": today.isoformat(), "caps": caps,
              "input_sha256": fingerprint(rows), "output_sha256": fingerprint(result),
              "documents": deepcopy(list(observations)), "outcomes": outcomes,
              "new_market_ids": new_ids, "counts": dict(sorted(counts.items())),
              "coordinates_assigned": 0, "individual_openings_confirmed": 0,
              "authenticated_publisher_reuse_claimed": False}
    return result, report


def verify_admissions(before, after, report, *, today, config):
    """Rebuild every admission from the saved page facts; nothing else may change."""
    if (not isinstance(report, dict) or report.get("schema") != SCHEMA
            or report.get("date") != today.isoformat() or report.get("caps") != _caps(config)
            or report.get("input_sha256") != fingerprint(before)
            or report.get("output_sha256") != fingerprint(after)
            or report.get("coordinates_assigned") != 0 or report.get("individual_openings_confirmed") != 0
            or report.get("authenticated_publisher_reuse_claimed") is not False
            or not isinstance(report.get("documents"), list)
            or len(report["documents"]) > len(PUBLISHERS) * MAX_CANDIDATE_READS):
        raise ValueError("Invalid editorial discovery admission proof")
    expected, replay = admit(before, report["documents"], today=today, config=config)
    if expected != after or any(replay[k] != report.get(k) for k in ("outcomes", "new_market_ids", "counts")):
        raise ValueError("Discovery admissions cannot be rebuilt from the observed pages")
    if after[:len(before)] != before or len(after) - len(before) != len(report["new_market_ids"]):
        raise ValueError("Discovery admission changed or removed an existing market")
    for row in after[len(before):]:
        if (row.get("fonte") not in PUBLISHERS or row.get("verificato_il") or row.get("lat") is not None
                or row.get("lng") is not None or row.get("status") != "non_confermato"
                or row.get("date_quality") == "confermata"
                or not clean_editorial_evidence(row.get(KEY), row, today=today)):
            raise ValueError("Discovery admission lost its source evidence or claimed a verification")
    return {"release_safe": True, "retained_ids": len(before), "new_ids": len(after) - len(before)}


# ---------------------------------------------------------------- export proofs

def _source_page(observed):
    return {**deepcopy(observed["parsed"]["source"]), "read_on": observed["read_on"], "status": "parsed"}


def certificate_admissions(report, *, today):
    """Source proofs for later guards; they rebuild each admission themselves."""
    if not report or not report.get("new_market_ids"):
        return []
    if report.get("schema") != SCHEMA or report.get("date") != today.isoformat():
        raise ValueError("Stale editorial discovery admission report")
    documents = {d["parsed"]["source"]["requested_url"]: d for d in report["documents"]}
    result = [{"market_id": o["market_id"], "document": deepcopy(documents[o["url"]]),
               "source_page": _source_page(documents[o["url"]])}
              for o in report["outcomes"] if o["status"] == "admitted"]
    if [item["market_id"] for item in result] != report["new_market_ids"]:
        raise ValueError("Editorial admissions lost their source outcome")
    return result


def _visible(rows):
    return [r for r in rows if not r.get("duplicato_di") and not r.get("concluso")]


def check_exported_admission(row, observed, market_id, *, today, others):
    """The exported record is the page's market, with its proof, and no visible twin."""
    document, read_on = observed["parsed"], observed["read_on"]
    source = editorial._valid_document(document, read_on, today)
    policy = validate_policy(publisher=source["publisher"])
    def chosen(base, hashed):
        return market_id if market_id in (base, hashed) else None
    expected, _ = candidate_row(document, read_on=read_on, today=today, policy=policy, slug=chosen)
    if expected is None or row is None:
        raise ValueError("Exported editorial admission has no rebuildable source page")
    for field in ("slug", "nome", "citta", "provincia", "regione", "categoria", "fonte", "url_fonte"):
        if row.get(field) != expected[field]:
            raise ValueError("Exported editorial admission changed its identity: " + field)
    if (row.get("verificato_il") or row.get("lat") is not None or row.get("lng") is not None
            or row.get("date_quality") == "confermata"):
        raise ValueError("Exported editorial admission claims a verification or coordinates")
    if clean_editorial_evidence(row.get(KEY), row, today=today) != clean_editorial_evidence(
            expected[KEY], expected, today=today):
        raise ValueError("Exported editorial admission lost its exact page evidence")
    proofs = {(r["url"], r["sha256"]) for r in clean_receipts(row.get("riscontri_campi"), row, today=today)}
    if expected.get("riscontri_campi") and (source["requested_url"], source["html_sha256"]) not in proofs:
        raise ValueError("Exported editorial admission lost its field receipt")
    if not row.get("duplicato_di") and not row.get("concluso"):
        duplicate = duplicate_reason(row, [r for r in _visible(others) if _town(r) == _town(row)], strict=False)
        if duplicate:
            raise ValueError("Exported editorial admission is a second visible card: " + " ".join(map(str, duplicate)))
    return row


def verify_certified_admission(collision_rows, admission, by_id, today):
    """Hook for the shared later-source certificate (see happings_detail_enrichment)."""
    if not isinstance(admission, dict) or set(admission) != {"market_id", "document", "source_page"}:
        raise ValueError("Unexpected editorial admission proof fields")
    observed = admission["document"]
    if not isinstance(observed, dict) or set(observed) != {"read_on", "parsed"}:
        raise ValueError("Editorial admission lost its read date")
    if admission["source_page"] != _source_page(observed):
        raise ValueError("Editorial admission detached from its observed page")
    return check_exported_admission(by_id.get(admission["market_id"]), observed, admission["market_id"],
                                    today=today, others=collision_rows)


def verify_exported(rows, report, *, today, state_dir=None):
    """Final static proof: every admitted market survived export with its evidence."""
    if not isinstance(report, dict) or report.get("schema") != SCHEMA or report.get("date") != today.isoformat():
        raise ValueError("Editorial discovery final proof lost its date")
    by_id = {r["slug"]: r for r in rows}
    if len(by_id) != len(rows):
        raise ValueError("Editorial discovery export repeats identities")
    admissions = certificate_admissions(report.get("admission"), today=today)
    for item in admissions:
        check_exported_admission(by_id.get(item["market_id"]), item["document"], item["market_id"],
                                 today=today, others=rows)
    queues = {}
    if state_dir is not None:
        for publisher in ORDER:
            phase = report["publishers"][publisher]
            path = Path(state_dir) / state_filename(publisher)
            if phase["status"] in NO_NEW_STATE:
                queues[publisher] = "validated_previous" if path.is_file() else "absent"
                continue
            state = json.loads(path.read_text("utf-8"))
            if fingerprint(state) != phase["state_sha256"]:
                raise ValueError("Exported discovery queue differs from its report")
            queues[publisher] = "validated_report_bound"
    return {"schema": SCHEMA, "release_safe": True, "admitted_ids_checked": len(admissions),
            "queues": queues}


# ---------------------------------------------------------------- orchestration

def _read_state(path, *, publisher, policy, today):
    path = Path(path)
    if not path.is_file():
        return None
    if path.stat().st_size > MAX_STATE_BYTES:
        raise ValueError("Editorial discovery queue exceeds its byte bound")
    return validate_state(json.loads(path.read_text("utf-8")), today=today, publisher=publisher, policy=policy)


def _checkpoint(out, publisher):
    return Path(out) / "sources" / (PUBLISHERS[publisher] + "-discovery-pages.json")


def run(rows, *, out, state_dir, today, baseline_signature, policy_digest, config,
        offline=False, resume=False, fetchers=None, deadline=None,
        monotonic=time.monotonic, sleep=time.sleep, now=None):
    """Discover, read and admit for every configured publisher.

Hosts are read concurrently (each keeps its own pacing); admission then runs
once over all pages in a fixed publisher order, so two publishers listing the
same market cannot both add it. Returns (rows, report, admitted ids).
"""
    if not isinstance(today, date) or not baseline_signature or not policy_digest:
        raise ValueError("Missing editorial discovery context")
    if config != configuration(enabled=config.get("enabled")):
        raise ValueError("Editorial discovery policy changed during the run")
    started = monotonic()
    phases = {}

    def one(publisher):
        policy = config["publishers"][publisher]
        previous = _read_state(Path(state_dir) / state_filename(publisher), publisher=publisher,
                               policy=policy, today=today)
        context = {"date": today.isoformat(), "baseline": baseline_signature,
                   "pipeline_policy": policy_digest, "policy": policy, "catalog": fingerprint(rows),
                   "state_before": fingerprint(previous)}
        checkpoint = _checkpoint(out, publisher)
        if not _active(config, publisher):
            return previous, [], {"status": "disabled", "network_requests": 0}
        if resume:
            if not checkpoint.is_file():
                return previous, [], {"status": "resume_missing_evidence", "network_requests": 0}
            saved = json.loads(checkpoint.read_text("utf-8"))
            if saved.get("context") != context:
                raise ValueError("Editorial discovery resume belongs to another catalog or policy")
            state = validate_state(saved["state"], today=today, publisher=publisher, policy=policy)
            pages = [editorial._unpack(v, today=today) for v in saved["pages"]]
            return state, pages, {**saved["report"], "status": "resumed"}
        if offline:
            return previous, [], {"status": "offline_skipped", "network_requests": 0}
        state, pages, report = acquire(rows, publisher=publisher, policy=policy, previous_state=previous,
                                       today=today, deadline=deadline, fetcher=(fetchers or {}).get(publisher),
                                       monotonic=monotonic, sleep=sleep, now=now)
        _write_state(checkpoint, {"context": context, "state": state,
                            "pages": [editorial._pack(p) for p in pages], "report": report})
        return state, pages, report

    with ThreadPoolExecutor(max_workers=len(ORDER), thread_name_prefix="editorial-discovery") as workers:
        futures = {p: workers.submit(one, p) for p in ORDER}
        phases = {p: futures[p].result() for p in ORDER}

    observations, layout_holds = [], {}
    for publisher in ORDER:
        for page in phases[publisher][1]:
            try:
                parsed = editorial.parse_document(page["body"], requested_url=page["requested_url"],
                                                  final_url=page["final_url"], today=today)
                observations.append({"read_on": page["read_on"], "parsed": parsed})
            except (ValueError, KeyError, TypeError):
                layout_holds[page["requested_url"]] = "source_layout_unsupported"
    result, admission = admit(rows, observations, today=today, config=config)
    verify_admissions(rows, result, admission, today=today, config=config)
    outcome_by_url = {o["url"]: o for o in admission["outcomes"]}

    report = {"schema": SCHEMA, "date": today.isoformat(), "enabled": config["enabled"],
              "publishers": {}, "admission": admission}
    for publisher in ORDER:
        state, pages, phase = phases[publisher]
        phase = deepcopy(phase)
        if phase["status"] not in NO_NEW_STATE and state is not None:
            for url, entry in list(state["candidates"].items()):
                outcome = outcome_by_url.get(url)
                if outcome and outcome["status"] == "admitted":
                    del state["candidates"][url]
                elif outcome:
                    entry.update(status="held", reason=outcome["reason"])
                elif url in layout_holds:
                    entry.update(status="held", reason=layout_holds[url])
            state = validate_state(state, today=today, publisher=publisher,
                                   policy=config["publishers"][publisher])
            _write_state(Path(out) / state_filename(publisher), state)
            phase["state_sha256"] = fingerprint(state)
            phase["candidates_known"] = len(state["candidates"])
            phase["index_pages_known"] = len(state["indexes"])
        phase["layout_holds"] = sorted(u for u in layout_holds if (source_identity(u) or (None,))[0] == publisher)
        mine = [o for o in admission["outcomes"] if o["publisher"] == publisher]
        phase["admitted"] = sum(o["status"] == "admitted" for o in mine)
        phase["held_by_reason"] = dict(sorted(Counter(o["reason"] for o in mine if o["reason"]).items()))
        report["publishers"][publisher] = phase
    report["summary"] = {
        "new_candidates_found": sum(p.get("new_candidates_found", 0) for p in report["publishers"].values()),
        "candidate_pages_read": sum(p.get("candidate_pages_read", 0) for p in report["publishers"].values()),
        "admitted": len(admission["new_market_ids"]),
        "held_by_reason": dict(sorted(Counter(o["reason"] for o in admission["outcomes"] if o["reason"]).items())
                               + sorted(Counter(layout_holds.values()).items())),
        "network_requests": sum(p.get("network_requests", 0) for p in report["publishers"].values()),
        "elapsed_seconds": round(max(0, monotonic() - started), 3)}
    _write(Path(out) / REPORT_FILENAME, report)
    return result, report, set(admission["new_market_ids"])


def persist_states(report, *, out, source_dir, destination, today):
    """Copy only validated, report-bound discovery queues to the candidate."""
    if report.get("schema") != SCHEMA or report.get("date") != today.isoformat():
        raise ValueError("Discovery queue report changed its reference context")
    changed = False
    for publisher in ORDER:
        phase = report["publishers"][publisher]
        if phase["status"] in NO_NEW_STATE:
            continue
        policy = validate_policy(publisher=publisher)
        state = _read_state(Path(out) / state_filename(publisher), publisher=publisher, policy=policy, today=today)
        if state is None or fingerprint(state) != phase["state_sha256"]:
            raise ValueError("Discovery queue differs from its source report")
        previous = _read_state(Path(source_dir) / state_filename(publisher), publisher=publisher,
                               policy=policy, today=today)
        changed = changed or previous != state
        _write_state(Path(destination) / state_filename(publisher), state)
    return changed
