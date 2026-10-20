"""Bounded discovery of observed Happings detail URLs, with a resumable frontier.

Discovery is not an identity match. A link in a sitemap or a related-event card
only makes the linked page eligible for reading; the detail reconciler must
still prove which existing market, if any, it describes. No URL slug is built
from a market name and no publication date is fabricated from a fetch date.

The caller owns authorization and the *shared* request budget. It supplies the
already-read robots policy and persists the returned state for the next run.
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
from xml.etree import ElementTree

import happings_source_enrichment as weekly

SCHEMA = 1
MAX_RESOURCES = 50_000
MAX_LINKS_PER_PAGE = 20_000
MAX_ORIGINS = 4
MAX_REQUESTS = 128
MAX_SECONDS = 420
MAX_RESPONSE_BYTES = weekly.MAX_RESPONSE_BYTES
REFRESH_DAYS = 7
DETAIL_PATH = re.compile(r"/it/happing/[a-z0-9][a-z0-9-]{0,239}/$")
SITEMAP_PATH = re.compile(r"(?:/it/sitemap_index|/happings_event-sitemap\d*)\.xml$")
MARKET_SLUG = re.compile(r"mercat|antiquar|antichit|vintage|brocant|usato|pulci", re.I)
SHA256 = re.compile(r"[0-9a-f]{64}$")
ORIGIN_KINDS = {"catalog_url", "explicit_seed", "robots_sitemap", "sitemap_loc", "html_link"}
STATUSES = {"unread", "fetching", "retrieved", "unavailable", "robots_denied"}


def _same_host_url(url):
    if not isinstance(url, str) or len(url) > 1000 or any(ord(c) < 33 for c in url):
        return False
    try:
        p = urlsplit(url)
        return (p.scheme == "https" and p.netloc == "www.happings.com"
                and p.hostname == "www.happings.com" and not p.username
                and not p.password and p.port is None and not p.query
                and not p.fragment and not any(c in p.path for c in ("%", "\\")))
    except ValueError:
        return False


def url_kind(url):
    """Only the observed Italian detail and Yoast Happing sitemap families."""
    if not _same_host_url(url):
        return None
    path = urlsplit(url).path
    if DETAIL_PATH.fullmatch(path):
        return "detail"
    if SITEMAP_PATH.fullmatch(path):
        return "sitemap"
    return None


def _day(value):
    if type(value) is date:
        return value.isoformat()
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Discovery needs an explicit ISO observation date")
    return date.fromisoformat(value).isoformat()


def empty_state():
    return {"schema": SCHEMA, "publisher": weekly.PUBLISHER, "resources": {}}


def validate_state(state, *, today=None):
    """Reject altered/foreign frontier entries before making a request."""
    if (not isinstance(state, dict) or set(state) != {"schema", "publisher", "resources"}
            or state.get("schema") != SCHEMA or state.get("publisher") != weekly.PUBLISHER
            or not isinstance(state.get("resources"), dict)
            or len(state["resources"]) > MAX_RESOURCES):
        raise ValueError("Invalid Happings detail discovery state")
    day = _day(today) if today is not None else None
    keys = {"kind", "discovered_at", "origins", "last_attempt", "last_success",
            "last_success_at",
            "last_sha256", "last_error", "status", "attempts", "failures", "next_due"}
    for url, resource in state["resources"].items():
        if (not isinstance(resource, dict) or set(resource) != keys
                or url_kind(url) != resource.get("kind") or resource.get("kind") is None
                or resource.get("status") not in STATUSES
                or not isinstance(resource.get("origins"), list)
                or not 1 <= len(resource["origins"]) <= MAX_ORIGINS
                or any(type(resource.get(k)) is not int or not 0 <= resource[k] <= 1_000_000
                       for k in ("attempts", "failures"))
                or resource["failures"] > resource["attempts"]):
            raise ValueError("Untrusted Happings detail frontier resource")
        observed = _day(resource["discovered_at"])
        due = _day(resource["next_due"])
        if day and observed > day:
            raise ValueError("Discovery state contains future observations")
        for field in ("last_attempt", "last_success"):
            if resource[field] is not None:
                stamp = _day(resource[field])
                if stamp < observed or (day and stamp > day):
                    raise ValueError("Discovery state has inconsistent observation dates")
        if resource["last_success"] and (resource["last_attempt"] is None
                                         or resource["last_success"] > resource["last_attempt"]):
            raise ValueError("Discovery success preceded its request")
        exact = resource["last_success_at"]
        if exact is not None:
            if not isinstance(exact, str):
                raise ValueError("Discovery acquisition timestamp is invalid")
            stamp = datetime.fromisoformat(exact)
            if (stamp.tzinfo is None or stamp.utcoffset() != timedelta(0)
                    or stamp.date().isoformat() != resource["last_success"]):
                raise ValueError("Discovery acquisition time differs from the observed date")
        if resource["last_sha256"] is not None and (not isinstance(resource["last_sha256"], str)
                                                     or not SHA256.fullmatch(resource["last_sha256"])):
            raise ValueError("Discovery response hash is invalid")
        if resource["last_error"] is not None and (not isinstance(resource["last_error"], str)
                                                   or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", resource["last_error"])):
            raise ValueError("Discovery error type is invalid")
        for origin in resource["origins"]:
            if (not isinstance(origin, dict)
                    or set(origin) != {"kind", "url", "observed_at", "sha256"}
                    or origin.get("kind") not in ORIGIN_KINDS
                    or not _same_host_url(origin.get("url"))):
                raise ValueError("Discovery origin is invalid")
            stamp = _day(origin["observed_at"])
            if stamp < observed or (day and stamp > day):
                raise ValueError("Discovery origin has an invalid observation date")
            digest = origin["sha256"]
            if origin["kind"] in {"catalog_url", "explicit_seed"}:
                if origin["url"] != url or digest is not None:
                    raise ValueError("An unfetched seed cannot claim source evidence")
            elif not isinstance(digest, str) or not SHA256.fullmatch(digest):
                raise ValueError("Discovered links need the actual source content hash")
            if origin["kind"] == "robots_sitemap" and origin["url"] != weekly.ROBOTS:
                raise ValueError("A sitemap seed needs the observed robots source")
            if origin["kind"] == "sitemap_loc" and url_kind(origin["url"]) != "sitemap":
                raise ValueError("Sitemap link has no sitemap origin")
        if resource["status"] == "unread" and (resource["attempts"] or resource["last_attempt"] is not None):
            raise ValueError("Unread resource claims an earlier fetch")
        if bool(resource["last_success"]) != bool(resource["last_success_at"]) or bool(resource["last_success"]) != bool(resource["last_sha256"]):
            raise ValueError("Successful discovery response lost its hash or acquisition time")
        if resource["status"] == "retrieved" and (resource["last_success"] != resource["last_attempt"]
                                                   or resource["last_success"] is None
                                                   or resource["failures"] or resource["last_error"] is not None):
            raise ValueError("Completed discovery response has inconsistent evidence")
        if resource["status"] != "unread" and (not resource["attempts"] or resource["last_attempt"] is None):
            raise ValueError("Attempted discovery response lost its request date")
        if due < observed:
            raise ValueError("Discovery schedule precedes discovery")
    return state


def _remember(state, url, origin):
    kind = url_kind(url)
    if kind is None:
        return False
    resources = state["resources"]
    if url not in resources:
        if len(resources) >= MAX_RESOURCES:
            raise ValueError("Happings discovery frontier exceeds its reviewed bound")
        resources[url] = {
            "kind": kind, "discovered_at": origin["observed_at"], "origins": [origin],
            "last_attempt": None, "last_success": None, "last_sha256": None,
            "last_success_at": None,
            "last_error": None, "status": "unread", "attempts": 0, "failures": 0,
            "next_due": origin["observed_at"],
        }
        return True
    previous = resources[url]["origins"]
    # Retain stable provenance; an identical repeated read is not a new seed.
    signature = lambda value: (value["kind"], value["url"], value["sha256"])
    if signature(origin) not in {signature(item) for item in previous} and len(previous) < MAX_ORIGINS:
        previous.append(origin)
    return False


def seed_state(state=None, *, catalog_rows=(), seed_urls=(), robots_text=None, observed_at):
    """Seed only URLs actually present in the catalog, request, or robots body."""
    day = _day(observed_at)
    result = deepcopy(empty_state() if state is None else validate_state(state, today=day))
    for row in catalog_rows:
        if not isinstance(row, dict):
            raise ValueError("Invalid catalog seed")
        for url in [row.get("url_fonte"), *(item.get("url") for item in (row.get("fonti") or [])
                                           if isinstance(item, dict))]:
            if url_kind(url) == "detail":
                _remember(result, url, {"kind": "catalog_url", "url": url,
                                       "observed_at": day, "sha256": None})
    for url in seed_urls:
        if url_kind(url) != "detail":
            raise ValueError("Explicit seed must be an observed Happings detail URL")
        _remember(result, url, {"kind": "explicit_seed", "url": url,
                               "observed_at": day, "sha256": None})
    if robots_text is not None:
        raw = robots_text.encode("utf-8") if isinstance(robots_text, str) else robots_text
        if not isinstance(raw, bytes) or not 12 <= len(raw) <= 55_000:
            raise ValueError("Invalid robots discovery evidence")
        text = raw.decode("utf-8-sig", "strict")
        if "user-agent:" not in text.casefold():
            raise ValueError("Robots response lacks a policy")
        digest = hashlib.sha256(raw).hexdigest()
        for line in text.splitlines():
            match = re.fullmatch(r"\s*Sitemap:\s*(\S+)\s*", line, re.I)
            if match and url_kind(match[1]) == "sitemap":
                _remember(result, match[1], {"kind": "robots_sitemap", "url": weekly.ROBOTS,
                                            "observed_at": day, "sha256": digest})
    return validate_state(result, today=day)


class _Links(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.links = []
        self.non_content = []

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style", "template", "noscript"}:
            self.non_content.append(tag)
        if tag == "a" and not self.non_content:
            href = dict(attrs).get("href")
            if isinstance(href, str):
                if len(self.links) >= MAX_LINKS_PER_PAGE:
                    raise ValueError("Happings source exceeds its reviewed link bound")
                self.links.append(href)

    def handle_endtag(self, tag):
        if tag in self.non_content:
            position = len(self.non_content) - 1 - self.non_content[::-1].index(tag)
            self.non_content = self.non_content[:position]


def _observed_links(body, final_url):
    text = body.decode("utf-8-sig", "strict")
    if url_kind(final_url) != "sitemap":
        parser = _Links()
        parser.feed(text)
        parser.close()
        return "html_link", [urljoin(final_url, href) for href in parser.links]
    # Reject entity definitions before parsing; the sitemap is bounded UTF-8.
    if "<!DOCTYPE" in text.upper() or "<!ENTITY" in text.upper():
        raise ValueError("Sitemap contains unreviewed XML declarations")
    root = ElementTree.fromstring(text)
    namespace = "{http://www.sitemaps.org/schemas/sitemap/0.9}" if root.tag.startswith("{") else ""
    if root.tag not in {namespace + "sitemapindex", namespace + "urlset"}:
        raise ValueError("Publisher sitemap changed its structure")
    expected = namespace + ("sitemap" if root.tag == namespace + "sitemapindex" else "url")
    links = []
    for item in root:
        if item.tag != expected:
            continue
        loc = [entry for entry in item if entry.tag == namespace + "loc"]
        if len(loc) != 1 or not isinstance(loc[0].text, str):
            raise ValueError("Publisher sitemap has ambiguous locations")
        links.append(loc[0].text.strip())
        if len(links) > MAX_LINKS_PER_PAGE:
            raise ValueError("Sitemap exceeds its reviewed link bound")
    return "sitemap_loc", links


def ingest_pages(state, pages, *, observed_at):
    """Read observed links, retaining HTTP final URLs separately from HTML data."""
    day = _day(observed_at)
    result = deepcopy(validate_state(state, today=day))
    report = {"pages_observed": 0, "new_detail_urls": 0, "new_sitemap_urls": 0,
              "links_outside_scope": 0}
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("Discovery page is invalid")
        requested, final, body = (page.get(k) for k in ("requested_url", "final_url", "html"))
        if (not _same_host_url(requested) or not _same_host_url(final)
                or not isinstance(body, bytes) or not 12 <= len(body) <= MAX_RESPONSE_BYTES):
            raise ValueError("Discovery page has invalid origin or content")
        if url_kind(requested) in {"detail", "sitemap"} and requested != final:
            raise ValueError("A changed detail or sitemap URL requires an explicit review")
        relation, links = _observed_links(body, final)
        digest = hashlib.sha256(body).hexdigest()
        for url in sorted(set(links)):
            kind = url_kind(url)
            if kind is None or (relation == "html_link" and kind != "detail"):
                report["links_outside_scope"] += 1
                continue
            added = _remember(result, url, {"kind": relation, "url": final,
                                           "observed_at": day, "sha256": digest})
            report[f"new_{kind}_urls"] += int(added)
        report["pages_observed"] += 1
    return validate_state(result, today=day), report


def import_observed_pages(state, pages, *, observed_at):
    """Bootstrap only actually captured sitemaps, without relabeling their date.

    Each page contains ``html`` bytes and the capture metadata fields
    ``requested_url``, ``final_url``, ``http_status``, ``content_type``, ``bytes``,
    ``sha256``, ``captured_at``. Supply the robots-seeded index before its child
    sitemaps. Detail pages remain unread until the parser/reconciler pipeline
    processes them; this helper deliberately rejects detail HTML.

    The return is ``(state, report)``. It makes no network requests. Attempts and
    success timestamps describe the supplied original HTTP captures, not this
    local import. Identical imports are idempotent; older or tied contradictory
    captures cannot displace a newer recorded source observation.
    """
    day = _day(observed_at)
    result = deepcopy(validate_state(state, today=day))
    report = {"imported_sitemaps": 0, "already_imported_sitemaps": 0,
              "new_detail_urls": 0, "new_sitemap_urls": 0,
              "network_requests_performed": 0, "original_captures": []}
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("Captured sitemap metadata is invalid")
        url, final, body = (page.get(k) for k in ("requested_url", "final_url", "html"))
        if (url_kind(url) != "sitemap" or final != url or url not in result["resources"]
                or page.get("http_status") != 200 or not isinstance(body, bytes)
                or not 12 <= len(body) <= MAX_RESPONSE_BYTES
                or type(page.get("bytes")) is not int or page["bytes"] != len(body)
                or page.get("sha256") != hashlib.sha256(body).hexdigest()
                or not isinstance(page.get("content_type"), str)
                or page["content_type"].split(";", 1)[0].strip().casefold() not in {"text/xml", "application/xml"}):
            raise ValueError("Captured sitemap lost its observed URL, bytes, MIME or HTTP proof")
        exact = page.get("captured_at")
        if not isinstance(exact, str):
            raise ValueError("Captured sitemap lost its original acquisition timestamp")
        stamp = datetime.fromisoformat(exact)
        if stamp.tzinfo is None or stamp.utcoffset() != timedelta(0) or stamp.date().isoformat() > day:
            raise ValueError("Captured sitemap needs a nonfuture UTC acquisition timestamp")
        capture_day = stamp.date().isoformat()
        resource = result["resources"][url]
        if capture_day < resource["discovered_at"]:
            raise ValueError("Sitemap capture predates its recorded discovery")
        previous = resource["last_success_at"]
        if previous is not None:
            old = datetime.fromisoformat(previous)
            if stamp < old or (stamp == old and page["sha256"] != resource["last_sha256"]):
                raise ValueError("Sitemap capture regresses or contradicts the existing observation")
            if stamp == old:
                report["already_imported_sitemaps"] += 1
                continue
        result, found = ingest_pages(result, [page], observed_at=capture_day)
        resource = result["resources"][url]
        resource.update({"attempts": resource["attempts"] + 1, "failures": 0,
                         "status": "retrieved", "last_attempt": capture_day,
                         "last_success": capture_day, "last_success_at": exact,
                         "last_sha256": page["sha256"], "last_error": None,
                         "next_due": (stamp.date() + timedelta(days=REFRESH_DAYS)).isoformat()})
        report["imported_sitemaps"] += 1
        for field in ("new_detail_urls", "new_sitemap_urls"):
            report[field] += found[field]
        report["original_captures"].append({key: page[key] for key in (
            "requested_url", "final_url", "http_status", "content_type", "bytes", "sha256", "captured_at")})
    return validate_state(result, today=day), report


def next_requests(state, *, today, limit, sitemap_quota=2):
    """Prioritize relevant refresh while reserving discovery/background slots."""
    day = _day(today)
    validate_state(state, today=day)
    if type(limit) is not int or not 0 <= limit <= MAX_REQUESTS:
        raise ValueError("Discovery request budget is invalid")
    if type(sitemap_quota) is not int or not 0 <= sitemap_quota <= MAX_REQUESTS:
        raise ValueError("Discovery sitemap budget is invalid")
    due = [(url, item) for url, item in state["resources"].items()
           if item["next_due"] <= day and item["last_attempt"] != day]
    key = lambda pair: (pair[1]["next_due"], pair[1]["last_attempt"] or "0001-01-01", pair[0])
    maps = [url for url, item in sorted(due, key=key) if item["kind"] == "sitemap"]
    details = [(url, item) for url, item in sorted(due, key=key) if item["kind"] == "detail"]
    def priority(pair):
        url, item = pair
        # These are crawl priorities, never a market identity or category claim.
        seeded = any(origin["kind"] in {"catalog_url", "explicit_seed"} for origin in item["origins"])
        return (0 if seeded else 1 if MARKET_SLUG.search(urlsplit(url).path) else 2, *key(pair))
    unseen = sorted([pair for pair in details if pair[1]["last_success"] is None], key=priority)
    unseen_oldest = sorted(unseen, key=key)
    refresh = [pair for pair in details if pair[1]["last_success"] is not None]
    primary_refresh = sorted([pair for pair in refresh if priority(pair)[0] < 2], key=key)
    other_refresh = sorted([pair for pair in refresh if priority(pair)[0] == 2], key=key)
    chosen_maps = maps[:min(limit, sitemap_quota)]
    selected = list(chosen_maps)
    # While more pages have never been read than are due for refresh, give
    # the first pass most slots. Otherwise the regular 7-day refresh wave
    # can keep the unseen frontier waiting for months despite a healthy
    # daily request budget. This is scheduling only, never an identity claim.
    initial_crawl = bool(refresh) and len(unseen) > len(refresh)
    turn = sum(item["attempts"] for item in state["resources"].values() if item["kind"] == "detail")
    while len(selected) < limit and (unseen or primary_refresh or other_refresh):
        slot = turn % 9
        if initial_crawl:
            # 6/9 new (including 2 oldest-first), 2/9 relevant rereads,
            # and 1/9 unrelated rereads. Keep the 7-day queue alive.
            preferred = (unseen_oldest if slot in {1, 5} else
                         other_refresh if slot == 8 else
                         primary_refresh if slot in {3, 7} else unseen)
        else:
            # Once coverage catches up, favor source freshness as before.
            preferred = (unseen if slot == 2 else unseen_oldest if slot == 5
                         else other_refresh if slot == 8 else primary_refresh)
        pool = preferred or primary_refresh or unseen or other_refresh
        pair = pool.pop(0)
        selected.append(pair[0])
        if pair in unseen:
            unseen.remove(pair)
        if pair in unseen_oldest:
            unseen_oldest.remove(pair)
        turn += 1
    return selected


class _NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError("Discovery target redirected; retain it for review without following")


def fetch_one(url, *, robots, opener=None):
    """One public same-host request. Redirects never spend an uncounted request."""
    kind = url_kind(url)
    if kind is None or robots is None or not robots.can_fetch(weekly.USER_AGENT, url):
        raise ValueError("Discovery request is outside reviewed URLs or robots policy")
    weekly._public_dns("www.happings.com")
    opener = opener or build_opener(_NoRedirects())
    request = Request(url, headers={"User-Agent": weekly.USER_AGENT,
                                   "Accept": "application/xml,text/xml" if kind == "sitemap" else "text/html",
                                   "Accept-Encoding": "identity"})
    with opener.open(request, timeout=18) as response:
        mime = str(response.headers.get("Content-Type", "")).split(";", 1)[0].strip().casefold()
        expected = {"text/xml", "application/xml"} if kind == "sitemap" else {"text/html"}
        if response.status != 200 or mime not in expected or response.url != url:
            raise ValueError("Discovery response changed its URL or content type")
        body = response.read(MAX_RESPONSE_BYTES + 1)
        if not 12 <= len(body) <= MAX_RESPONSE_BYTES:
            raise ValueError("Discovery response exceeds its reviewed size")
    return body, url


def acquire(state, *, today, max_requests, robots, fetcher=None, checkpoint=None,
            sleep=time.sleep, sitemap_quota=2, clock=None, max_seconds=MAX_SECONDS,
            monotonic=time.monotonic):
    """Consume at most the caller's remaining budget and checkpoint each result.

    ``checkpoint(state, pages, report)`` is called immediately before each
    request and after its result, including failures. Its arguments are copies;
    ``pages`` holds every successful detail response so far, with original bytes
    and acquisition timestamps. Interrupted requests are not retried that day.

    No delay or request starts after the monotonic elapsed budget. A request
    already in progress can finish; its existing socket timeout still applies.
    Unstarted frontier entries remain unchanged for the next run. Reports expose
    ``max_seconds``, ``elapsed_seconds`` and ``budget_stop`` (``elapsed_limit``,
    ``request_limit`` or ``queue_exhausted``).

    Only detail pages are returned to the detail parser. Sitemap lastmod values
    never become observed freshness or event dates. A failed response stays due
    after a bounded backoff; it cannot erase an earlier catalog observation.
    """
    started = monotonic()
    day = _day(today)
    result = deepcopy(validate_state(state, today=day))
    if type(max_requests) is not int or not 0 <= max_requests <= MAX_REQUESTS:
        raise ValueError("Discovery request budget is invalid")
    if type(max_seconds) is not int or not 1 <= max_seconds <= MAX_SECONDS:
        raise ValueError("Discovery elapsed budget is invalid")
    if robots is None:
        raise ValueError("Discovery requires the already-observed robots policy")
    fetcher = fetcher or fetch_one
    clock = clock or (lambda: datetime.now(timezone.utc).isoformat())
    delay = weekly._request_pause(robots)
    pages = []
    report = {"max_requests": max_requests, "max_seconds": max_seconds,
              "elapsed_seconds": 0.0, "budget_stop": None, "requests_attempted": 0,
              "sitemaps_read": 0, "details_read": 0, "new_detail_urls": 0,
              "new_sitemap_urls": 0, "outcomes": [], "robots_fetches": 0,
              "inflight": None}
    def elapsed():
        report["elapsed_seconds"] = round(max(0.0, monotonic() - started), 6)
        return report["elapsed_seconds"]

    def save_checkpoint():
        elapsed()
        if checkpoint is not None:
            checkpoint(deepcopy(result), deepcopy(pages), deepcopy(report))

    maps_used = 0
    for _ in range(max_requests):
        if elapsed() >= max_seconds:
            report["budget_stop"] = "elapsed_limit"
            break
        choice = next_requests(result, today=day, limit=1,
                               sitemap_quota=max(0, sitemap_quota - maps_used))
        if not choice:
            report["budget_stop"] = "queue_exhausted"
            break
        url = choice[0]
        allowed = robots.can_fetch(weekly.USER_AGENT, url)
        # Leave the selected URL completely untouched if its required delay
        # would consume the remaining acquisition window.
        if elapsed() + (delay if allowed else 0) >= max_seconds:
            report["budget_stop"] = "elapsed_limit"
            break
        if allowed:
            sleep(delay)
        if elapsed() >= max_seconds:
            report["budget_stop"] = "elapsed_limit"
            break
        resource = result["resources"][url]
        original = deepcopy(resource)
        resource["last_attempt"] = day
        resource["attempts"] += 1
        resource["status"] = "fetching"
        resource["next_due"] = (date.fromisoformat(day) + timedelta(days=1)).isoformat()
        outcome = {"requested_url": url, "kind": resource["kind"], "network_attempted": False}
        report["inflight"] = deepcopy(outcome)
        save_checkpoint()
        try:
            if not allowed:
                resource["status"] = "robots_denied"
                raise ValueError("Publisher robots denied this discovery URL")
            if elapsed() >= max_seconds:
                result["resources"][url] = original
                report["inflight"] = None
                report["budget_stop"] = "elapsed_limit"
                break
            outcome["network_attempted"] = True
            report["requests_attempted"] += 1
            report["inflight"] = deepcopy(outcome)
            save_checkpoint()
            if elapsed() >= max_seconds:
                result["resources"][url] = original
                report["requests_attempted"] -= 1
                report["inflight"] = None
                report["budget_stop"] = "elapsed_limit"
                break
            body, final = fetcher(url, robots=robots)
            captured_at = clock()
            if (not isinstance(captured_at, str)
                    or datetime.fromisoformat(captured_at).tzinfo is None
                    or datetime.fromisoformat(captured_at).utcoffset() != timedelta(0)
                    or datetime.fromisoformat(captured_at).date().isoformat() != day):
                raise ValueError("Acquisition clock does not match the run date")
            page = {"requested_url": url, "final_url": final, "html": body,
                    "fetched_at": captured_at}
            new_state, found = ingest_pages(result, [page], observed_at=day)
            result = new_state
            resource = result["resources"][url]
            resource.update({"last_success": day, "last_success_at": captured_at,
                             "last_sha256": hashlib.sha256(body).hexdigest(),
                             "last_error": None, "status": "retrieved", "failures": 0,
                             "next_due": (date.fromisoformat(day) + timedelta(days=REFRESH_DAYS)).isoformat()})
            for key in ("new_detail_urls", "new_sitemap_urls"):
                report[key] += found[key]
            report["sitemaps_read" if resource["kind"] == "sitemap" else "details_read"] += 1
            if resource["kind"] == "detail":
                pages.append(page)
            outcome.update({"status": "retrieved", "final_url": final,
                            "sha256": resource["last_sha256"], "bytes": len(body),
                            "fetched_at": captured_at})
        except (OSError, HTTPError, HTTPException, ValueError, ElementTree.ParseError) as error:
            resource = result["resources"][url]
            resource["status"] = "robots_denied" if resource["status"] == "robots_denied" else "unavailable"
            resource["failures"] += 1
            resource["last_error"] = type(error).__name__
            cooldown = min(REFRESH_DAYS, 2 ** min(resource["failures"] - 1, 3))
            resource["next_due"] = (date.fromisoformat(day) + timedelta(days=cooldown)).isoformat()
            outcome.update({"status": resource["status"], "error_type": resource["last_error"]})
        report["outcomes"].append(outcome)
        report["inflight"] = None
        if resource["kind"] == "sitemap":
            maps_used += 1
        validate_state(result, today=day)
        save_checkpoint()
    report["budget_stop"] = report["budget_stop"] or "request_limit"
    report["known_detail_urls"] = sum(r["kind"] == "detail" for r in result["resources"].values())
    report["known_sitemap_urls"] = sum(r["kind"] == "sitemap" for r in result["resources"].values())
    report["pending_detail_urls"] = sum(r["kind"] == "detail" and r["last_success"] is None
                                        for r in result["resources"].values())
    save_checkpoint()
    return result, pages, report
