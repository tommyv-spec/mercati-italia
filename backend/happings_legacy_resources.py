"""Resolve observed legacy town links within the existing weekly request budget.

This frontier discovers resources, not market identities. A canonical URL is
kept distinct from an HTTP redirect and never replaces a catalog source URL.
Only an independently named province and compatible parsed city/weekday can
admit a resource. The weekly reader still applies every existing identity,
geography, weekday and street-conflict check to subsequently fetched pages.
"""
from __future__ import annotations

import hashlib
import re
import time
from copy import deepcopy
from datetime import date, datetime, timedelta, timezone
from html.parser import HTMLParser
from http.client import HTTPException
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

import happings_source_enrichment as source
from happings_weekly_layout import NON_CONTENT_TAGS, VOID_TAGS, fold, parse, province_page_key

SCHEMA = 1
STATE_FILENAME = "happings-legacy-resources.json"
MAX_RESOURCES = 10_000
MAX_REQUESTS = 2
MAX_SECONDS = 45
MAX_STATE_BYTES = 12_000_000
DEFAULT_POLICY = {"enabled": False, "max_requests": MAX_REQUESTS, "max_seconds": MAX_SECONDS}
REDIRECT_CODES = {301, 302, 303, 307, 308}
STATUSES = {"pending", "redirect_observed", "resolved", "unavailable", "robots_disallowed",
            "unreviewed_target", "invalid_layout", "scope_mismatch", "source_city_day_absent"}


def validate_policy(policy):
    if (not isinstance(policy, dict) or set(policy) - set(DEFAULT_POLICY)
            or type(policy.get("enabled", False)) is not bool
            or type(policy.get("max_requests", MAX_REQUESTS)) is not int
            or not 1 <= policy.get("max_requests", MAX_REQUESTS) <= MAX_REQUESTS
            or type(policy.get("max_seconds", MAX_SECONDS)) is not int
            or not 1 <= policy.get("max_seconds", MAX_SECONDS) <= MAX_SECONDS):
        raise ValueError("Unbounded Happings legacy resource policy")
    return {**DEFAULT_POLICY, **policy}


def legacy_url(url):
    """Only actual catalog links in the old municipal family are candidates."""
    if not isinstance(url, str) or len(url) > 350:
        return False
    try:
        p = urlsplit(url)
        return bool(p.scheme == "https" and p.netloc == "www.happings.com"
                    and not p.query and not p.fragment
                    and re.fullmatch(r"/it/mercato-settimanale-a-[a-z0-9][a-z0-9-]*\.html", p.path))
    except ValueError:
        return False


def _legacy_request_url(url):
    """Allow the observed slash variant for traversal, never synthesize it."""
    if not isinstance(url, str) or len(url) > 350:
        return False
    try:
        p = urlsplit(url)
        return bool(p.scheme == "https" and p.netloc == "www.happings.com"
                    and not p.query and not p.fragment
                    and re.fullmatch(r"/it/mercato-settimanale-a-[a-z0-9][a-z0-9-]*(?:\.html|/)", p.path))
    except ValueError:
        return False


def _target_allowed(item, url):
    if _scope(url) == (item["region"], item["province"]):
        return True
    # Real captures show old town.html -> same town/ -> province page.
    # Only the identical original slug can be an intermediate town URL.
    return bool(_legacy_request_url(url) and
                urlsplit(url).path.removesuffix(".html").rstrip("/") ==
                urlsplit(item["origin_url"]).path.removesuffix(".html").rstrip("/"))


def _day(value, today, *, optional=False):
    if value is None and optional:
        return None
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Legacy resource lost its observation date")
    parsed = date.fromisoformat(value)
    if parsed > today:
        raise ValueError("Legacy resource observation is in the future")
    return parsed


def _scope(url):
    areas = source._official_geography()[1].get(province_page_key(url), set())
    return next(iter(areas)) if len(areas) == 1 else None


def catalog_context(markets):
    # Validate IDs through the same catalog router; no alternate geocoder or
    # permissive recurrence parser is introduced by this resolver.
    routed = source.catalog_page_routes(markets)
    municipalities = source._official_geography()[0]
    found = {}
    for row in markets:
        city, region = fold(row.get("citta")), fold(row.get("regione"))
        province = str(row.get("provincia") or "").strip().upper()
        if (row["slug"] in routed or row.get("fonte") != source.PUBLISHER
                or not legacy_url(row.get("url_fonte")) or not source.same_generic_venue(row)
                or source._weekly_day(row) is None
                or municipalities.get((region, city)) != province):
            continue
        found.setdefault(row["url_fonte"], []).append(row)
    return {"routes": routed, "origins": {url: rows for url, rows in found.items()
            if len({(fold(r["regione"]), r["provincia"].upper()) for r in rows}) == 1}}


def _rows_by_origin(markets):
    return catalog_context(markets)["origins"]


def validate_state(state, *, today):
    if (not isinstance(today, date) or not isinstance(state, dict)
            or set(state) != {"schema", "publisher", "resources"}
            or state["schema"] != SCHEMA or state["publisher"] != source.PUBLISHER
            or not isinstance(state["resources"], list) or len(state["resources"]) > MAX_RESOURCES):
        raise ValueError("Unbounded Happings legacy resource state")
    seen = set()
    municipalities = source._official_geography()[0]
    keys = {"origin_url", "next_url", "region", "province", "city_keys", "first_seen_on",
            "last_attempt_on", "last_success_on", "attempts", "status", "last_error",
            "redirects", "proof"}
    for item in state["resources"]:
        if (not isinstance(item, dict) or set(item) != keys or not legacy_url(item["origin_url"])
                or item["origin_url"] in seen or item["status"] not in STATUSES
                or type(item["attempts"]) is not int or not 0 <= item["attempts"] <= 1_000_000
                or not isinstance(item["city_keys"], list) or not 1 <= len(item["city_keys"]) <= 100
                or item["city_keys"] != sorted(set(item["city_keys"]))
                or any(not isinstance(city, str) or fold(city) != city
                       or municipalities.get((item["region"], city)) != item["province"]
                       for city in item["city_keys"])
                or (item["last_error"] is not None and (not isinstance(item["last_error"], str)
                    or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", item["last_error"])))):
            raise ValueError("Legacy resource lost its catalog scope")
        seen.add(item["origin_url"])
        first = _day(item["first_seen_on"], today)
        attempt = _day(item["last_attempt_on"], today, optional=True)
        success = _day(item["last_success_on"], today, optional=True)
        if ((attempt is None) != (item["attempts"] == 0) or (attempt and attempt < first)
                or (success and (attempt is None or not first <= success <= attempt))):
            raise ValueError("Legacy resource observation order changed")
        if not isinstance(item["redirects"], list) or len(item["redirects"]) > 2:
            raise ValueError("Unbounded legacy redirect chain")
        cursor, visited = item["origin_url"], {item["origin_url"]}
        for redirect in item["redirects"]:
            if (not isinstance(redirect, dict)
                    or set(redirect) != {"requested_url", "location_url", "status_code", "observed_on"}
                    or redirect["requested_url"] != cursor or redirect["location_url"] in visited
                    or redirect["status_code"] not in REDIRECT_CODES
                    or not _target_allowed(item, redirect["location_url"])):
                raise ValueError("Legacy resource redirect left its proved scope")
            _day(redirect["observed_on"], today)
            cursor = redirect["location_url"]
            visited.add(cursor)
        if item["next_url"] != cursor:
            raise ValueError("Legacy resource target was not observed")
        proof = item["proof"]
        if proof is not None:
            if (not isinstance(proof, dict) or set(proof) != {
                    "requested_url", "final_url", "canonical_url", "resource_url", "source_html_sha256",
                    "observed_on", "province_heading", "source_rows", "matched_city_days"}
                    or proof["requested_url"] != cursor or proof["final_url"] != cursor
                    or _scope(proof["resource_url"]) != (item["region"], item["province"])
                    or proof["resource_url"] != (proof["canonical_url"] or proof["final_url"])
                    or (proof["canonical_url"] is not None and not province_page_key(proof["canonical_url"]))
                    or fold(proof["province_heading"]) != fold(province_page_key(proof["resource_url"]))
                    or not isinstance(proof["source_html_sha256"], str)
                    or not re.fullmatch(r"[a-f0-9]{64}", proof["source_html_sha256"])
                    or type(proof["source_rows"]) is not int or not 1 <= proof["source_rows"] <= 2200
                    or not isinstance(proof["matched_city_days"], list)
                    or not 1 <= len(proof["matched_city_days"]) <= 700):
                raise ValueError("Legacy resource lacks independent provincial page proof")
            for match in proof["matched_city_days"]:
                if (not isinstance(match, dict) or set(match) != {"city_key", "weekday"}
                        or match["city_key"] not in item["city_keys"]
                        or type(match["weekday"]) is not int or not 0 <= match["weekday"] <= 6):
                    raise ValueError("Legacy resource lost its observed city and weekday")
            if _day(proof["observed_on"], today) != success:
                raise ValueError("Legacy resource success date has no source proof")
        if (item["status"] == "resolved") != (proof is not None) or (success is not None) != (proof is not None):
            raise ValueError("Legacy resource falsely claims a successful resolution")
    if [item["origin_url"] for item in state["resources"]] != sorted(seen):
        raise ValueError("Legacy resource frontier order changed")
    return deepcopy(state)


def seed_state(markets, *, state=None, today, catalog=None):
    state = validate_state(state or {"schema": SCHEMA, "publisher": source.PUBLISHER, "resources": []}, today=today)
    entries = {item["origin_url"]: item for item in state["resources"]}
    catalog = catalog or catalog_context(markets)
    for url, rows in catalog["origins"].items():
        region, province = fold(rows[0]["regione"]), rows[0]["provincia"].upper()
        city_keys = sorted({fold(row["citta"]) for row in rows})
        if url in entries:
            if (entries[url]["region"], entries[url]["province"], entries[url]["city_keys"]) != (region, province, city_keys):
                raise ValueError("Legacy origin changed its catalog geography")
            continue
        entries[url] = {
            "origin_url": url, "next_url": url, "region": region, "province": province,
            "city_keys": city_keys, "first_seen_on": today.isoformat(), "last_attempt_on": None,
            "last_success_on": None, "attempts": 0, "status": "pending", "last_error": None,
            "redirects": [], "proof": None,
        }
    return validate_state({**state, "resources": [entries[url] for url in sorted(entries)]}, today=today)


def known_resources(state, markets, *, today, catalog=None):
    """Return observed URLs; this does not authorize any catalog field change."""
    state = validate_state(state, today=today)
    origins = (catalog or catalog_context(markets))["origins"]
    return sorted({item["proof"]["resource_url"] for item in state["resources"]
                   if item["proof"] and item["origin_url"] in origins
                   and any(source._catalog_geography_matches(row, item["proof"]["resource_url"])
                           and {"city_key": fold(row["citta"]), "weekday": source._weekly_day(row)}
                           in item["proof"]["matched_city_days"] for row in origins[item["origin_url"]])})


def pending_origins(state, markets, *, today, catalog=None):
    catalog = catalog or catalog_context(markets)
    origins = catalog["origins"]
    resources = known_resources(state, markets, today=today, catalog=catalog)
    covered = {_scope(url) for url in set(catalog["routes"].values())}
    for url in resources:
        if any(source.record_matches_page(row, url, url) for rows in origins.values() for row in rows):
            covered.add(_scope(url))
    candidates = []
    for item in state["resources"]:
        rows = origins.get(item["origin_url"], [])
        if not rows or item["proof"]:
            continue
        exact = any(source._town_url_matches(row) for row in rows)
        missing = (item["region"], item["province"]) not in covered
        # One proved resource covers the other exact municipal URLs in that
        # province; never spend five daily slots rediscovering the same page.
        if exact and not missing:
            continue
        attempted = _day(item["last_attempt_on"], today, optional=True)
        retry_days = 30 if item["status"] in {"unreviewed_target", "invalid_layout", "scope_mismatch", "source_city_day_absent"} else 7
        if attempted and item["status"] != "redirect_observed" and (today - attempted).days < retry_days:
            continue
        candidates.append((0 if exact and missing else 1 if missing else 2,
                           0 if item["status"] == "redirect_observed" else 1,
                           item["last_attempt_on"] or "0000-00-00", item["origin_url"]))
    return [entry[-1] for entry in sorted(candidates)]


class _PageScope(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack, self.canonicals, self.provinces = [], [], []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        hidden = (tag in NON_CONTENT_TAGS or "hidden" in values
                  or values.get("aria-hidden") == "true"
                  or any(frame[1] for frame in self.stack))
        if not hidden and tag == "link" and "canonical" in (values.get("rel") or "").lower().split():
            self.canonicals.append(values.get("href") or "")
            if len(self.canonicals) > 8:
                raise ValueError("Ambiguous canonical resource")
        if tag not in VOID_TAGS:
            self.stack.append([tag, hidden, [] if tag in {"h1", "h2"} else None])
            if len(self.stack) > 300:
                raise ValueError("Unbounded source page nesting")

    def handle_data(self, data):
        if any(frame[1] for frame in self.stack):
            return
        for frame in self.stack:
            if frame[2] is not None:
                if len(frame[2]) > 50 or len(data) > 1000:
                    raise ValueError("Unbounded provincial heading")
                frame[2].append(data)

    def handle_endtag(self, tag):
        index = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i][0] == tag), None)
        if index is None:
            return
        while len(self.stack) > index:
            _, hidden, parts = self.stack.pop()
            if not hidden and parts is not None:
                text = fold(" ".join(parts))
                match = re.fullmatch(r"mercati settimanali nei comuni in provincia di (.+)", text)
                if not match:
                    match = re.fullmatch(r"mercati settimanali (?:a|ad) (.+) e provincia", text)
                if match:
                    self.provinces.append(match[1])


def prove_resource(item, requested_url, raw, rows, *, today):
    if not isinstance(raw, bytes) or not 300 <= len(raw) <= source.MAX_RESPONSE_BYTES:
        raise ValueError("Unbounded legacy source HTML")
    document = _PageScope()
    document.feed(raw.decode("utf-8-sig", "replace"))
    document.close()
    canonicals = {urljoin(requested_url, href) for href in document.canonicals if href}
    if len(canonicals) > 1 or (document.canonicals and not canonicals):
        raise ValueError("Ambiguous legacy canonical")
    canonical = next(iter(canonicals)) if canonicals else None
    resource_url = canonical or requested_url
    if _scope(resource_url) != (item["region"], item["province"]):
        return None, "scope_mismatch"
    label = fold(province_page_key(resource_url))
    if not document.provinces or set(document.provinces) != {label}:
        return None, "scope_mismatch"
    parsed = parse(raw, source_url=resource_url)
    wanted = {(fold(row["citta"]), source._weekly_day(row)) for row in rows}
    found = sorted({(row["city_key"], row["weekday"]) for row in parsed.rows} & wanted)
    if not found:
        return None, "source_city_day_absent"
    return {
        "requested_url": requested_url, "final_url": requested_url,
        "canonical_url": canonical, "resource_url": resource_url,
        "source_html_sha256": hashlib.sha256(raw).hexdigest(), "observed_on": today.isoformat(),
        "province_heading": label, "source_rows": len(parsed.rows),
        "matched_city_days": [{"city_key": city, "weekday": day} for city, day in found],
    }, "resolved"


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def fetch_one(url, *, timeout=18):
    """Exactly one physical HTTP request; every redirect consumes another slot."""
    if not _legacy_request_url(url) and not province_page_key(url):
        raise ValueError("Unreviewed legacy request URL")
    source._public_dns("www.happings.com")
    request = Request(url, headers={"User-Agent": source.USER_AGENT,
                                   "Accept": "text/html", "Accept-Encoding": "identity"})
    try:
        response = build_opener(_NoRedirect()).open(request, timeout=timeout)
    except HTTPError as error:
        try:
            return {"requested_url": url, "final_url": error.url, "status_code": error.code,
                    "location": error.headers.get("Location"), "html": None}
        finally:
            error.close()
    with response:
        if response.status != 200 or "text/html" not in response.headers.get("Content-Type", "").lower():
            raise ValueError("Legacy source did not return a complete HTML response")
        body = response.read(source.MAX_RESPONSE_BYTES + 1)
        if not 300 <= len(body) <= source.MAX_RESPONSE_BYTES:
            raise ValueError("Unbounded legacy source response")
        return {"requested_url": url, "final_url": response.url, "status_code": response.status,
                "location": None, "html": body}


def acquire(markets, state, *, today, robots, max_requests=MAX_REQUESTS, max_seconds=MAX_SECONDS,
            fetcher=fetch_one, sleep=time.sleep, monotonic=time.monotonic,
            clock=lambda: datetime.now(timezone.utc), checkpoint=None, catalog=None):
    """Return (validated state, report, raw captures), checkpointing each request.

    A pre-request checkpoint records an interrupted attempt, never a source
    success. Caller subtracts attempted requests from the 16-page weekly
    budget and uses the same robots policy for both phases.
    """
    validate_policy({"enabled": True, "max_requests": max_requests, "max_seconds": max_seconds})
    started = monotonic()
    catalog = catalog or catalog_context(markets)
    state = seed_state(markets, state=state, today=today, catalog=catalog)
    origins = catalog["origins"]
    report = {"status": "completed", "requests_attempted": 0, "request_slots_used": 0, "max_requests": max_requests,
              "max_seconds": max_seconds, "elapsed_seconds": 0, "budget_stop": "queue_exhausted",
              "outcomes": [], "new_resources": []}
    captures = []
    initial = set(known_resources(state, markets, today=today, catalog=catalog))
    attempted_urls = set()

    def save():
        report["elapsed_seconds"] = round(max(0, monotonic() - started), 3)
        report["new_resources"] = sorted(set(known_resources(state, markets, today=today, catalog=catalog)) - initial)
        if checkpoint:
            checkpoint(deepcopy(state), deepcopy(report), deepcopy(captures))

    while report["request_slots_used"] < max_requests:
        candidates = pending_origins(state, markets, today=today, catalog=catalog)
        entries = {item["origin_url"]: item for item in state["resources"]}
        origin = next((url for url in candidates if entries[url]["next_url"] not in attempted_urls), None)
        if origin is None:
            break
        item = entries[origin]
        url = item["next_url"]
        now = clock()
        if not isinstance(now, datetime) or now.utcoffset() != timedelta(0) or now.date() != today:
            raise ValueError("Live legacy acquisition must use its actual UTC capture date")
        remaining = max_seconds - (monotonic() - started)
        delay = source._request_pause(robots)
        if remaining <= delay + 1:
            report["budget_stop"] = "elapsed_deadline"
            break
        if not robots.can_fetch(source.USER_AGENT, url):
            item.update(last_attempt_on=today.isoformat(), attempts=item["attempts"] + 1,
                        status="robots_disallowed", last_error="RobotsDisallowed")
            report["outcomes"].append({"origin_url": origin, "requested_url": url, "outcome": "robots_disallowed"})
            # Do not visit an unbounded denied frontier without spending a
            # slot: the reserved slot remains consumed in the weekly budget.
            report["request_slots_used"] += 1
            attempted_urls.add(url)
            save()
            continue
        sleep(delay)
        remaining = max_seconds - (monotonic() - started)
        if remaining <= 1:
            report["budget_stop"] = "elapsed_deadline"
            break
        report["requests_attempted"] += 1
        report["request_slots_used"] += 1
        attempted_urls.add(url)
        item.update(last_attempt_on=today.isoformat(), attempts=item["attempts"] + 1,
                    status="unavailable", last_error="InterruptedRequest")
        outcome = {"origin_url": origin, "requested_url": url, "outcome": "interrupted"}
        report["outcomes"].append(outcome)
        save()
        try:
            response = fetcher(url, timeout=min(18, remaining))
            if (not isinstance(response, dict) or response.get("requested_url") != url
                    or response.get("final_url") != url or type(response.get("status_code")) is not int):
                raise ValueError("Legacy transport lost the exact requested/final URL")
            status = response["status_code"]
            outcome["http_status"] = status
            if status in REDIRECT_CODES:
                location = response.get("location")
                target = urljoin(url, location) if isinstance(location, str) and len(location) <= 350 else None
                visited = {origin, *[r["location_url"] for r in item["redirects"]]}
                if (target in visited or len(item["redirects"]) >= 2
                        or not _target_allowed(item, target)):
                    item.update(status="unreviewed_target", last_error="UnreviewedRedirect")
                else:
                    item["redirects"].append({"requested_url": url, "location_url": target,
                                              "status_code": status, "observed_on": today.isoformat()})
                    item.update(next_url=target, status="redirect_observed", last_error=None)
            elif status == 200:
                raw = response.get("html")
                proof, result = prove_resource(item, url, raw, origins[origin], today=today)
                item.update(status=result, last_error=None if proof else result.title().replace("_", ""))
                if proof:
                    item.update(proof=proof, last_success_on=today.isoformat())
                    captures.append({"origin_url": origin, "requested_url": url,
                                     "final_url": url, "html": raw, "proof": deepcopy(proof)})
            else:
                item.update(status="unavailable", last_error="HTTPStatus" + str(status))
            outcome["outcome"] = item["status"]
        except (OSError, HTTPException, ValueError) as error:
            item.update(status="invalid_layout" if isinstance(error, ValueError) else "unavailable",
                        last_error=type(error).__name__)
            outcome.update(outcome=item["status"], error_type=type(error).__name__)
        save()
    if report["request_slots_used"] == max_requests:
        report["budget_stop"] = "request_budget"
    save()
    return validate_state(state, today=today), report, captures
