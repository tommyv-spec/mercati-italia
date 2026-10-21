"""Discover Italian Happings weekly-index URLs from the publisher's live sitemaps.

The sitemap is only an index of possible source pages. An ISTAT-unique province
scope is required before a discovered URL can enter the existing weekly reader.
No market identity, date, address or opening time is inferred from a sitemap.
Network use is bounded, robots-aware and shares the existing weekly page budget.
"""
from __future__ import annotations

import hashlib
import re
import time
from datetime import date
from html.parser import HTMLParser
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from xml.etree import ElementTree

import happings_source_enrichment as source
from happings_weekly_layout import province_page_key

HOMEPAGE = "https://www.happings.com/it/"
INDEX = "https://www.happings.com/it/sitemap_index.xml"
POST_MAP = re.compile(r"/post-sitemap(?:[2-9]|[1-9][0-9]+)?\.xml")
MAX_BYTES = source.MAX_RESPONSE_BYTES
MAX_LINKS = 10_000
MAX_REQUESTS = 8
MAX_SECONDS = 90
DEFAULT_POLICY = {"enabled": False, "max_requests": 4, "max_seconds": 60}


def validate_policy(policy):
    if (not isinstance(policy, dict) or set(policy) - set(DEFAULT_POLICY)
            or type(policy.get("enabled", False)) is not bool
            or type(policy.get("max_requests", 4)) is not int
            or not 2 <= policy.get("max_requests", 4) <= MAX_REQUESTS
            or type(policy.get("max_seconds", 60)) is not int
            or not 1 <= policy.get("max_seconds", 60) <= MAX_SECONDS):
        raise ValueError("Unreviewed Happings province directory policy")
    return {**DEFAULT_POLICY, **policy}


def _same_host(url):
    if not isinstance(url, str) or len(url) > 1000 or any(ord(c) < 33 for c in url):
        return False
    try:
        p = urlsplit(url)
        return (p.scheme == "https" and p.netloc == "www.happings.com"
                and not p.query and not p.fragment and not any(c in p.path for c in ("%", "\\")))
    except ValueError:
        return False


def _post_sitemap(url):
    return _same_host(url) and bool(POST_MAP.fullmatch(urlsplit(url).path))


def _locations(raw, *, index):
    if not isinstance(raw, bytes) or not 12 <= len(raw) <= MAX_BYTES:
        raise ValueError("Happings sitemap has invalid size")
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise ValueError("Happings sitemap contains an unreviewed declaration")
    root = ElementTree.fromstring(raw)
    ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}" if root.tag.startswith("{") else ""
    expected_root = ns + ("sitemapindex" if index else "urlset")
    expected_entry = ns + ("sitemap" if index else "url")
    if root.tag != expected_root:
        raise ValueError("Happings sitemap changed layout")
    result = []
    for element in root:
        if element.tag != expected_entry:
            continue
        locations = [item.text for item in element if item.tag == ns + "loc"]
        if len(locations) != 1 or not isinstance(locations[0], str):
            raise ValueError("Happings sitemap has ambiguous location")
        result.append(locations[0].strip())
        if len(result) > MAX_LINKS:
            raise ValueError("Happings sitemap has too many links")
    return result


class _HomeNavigation(HTMLParser):
    """Record only observed public, Italian, same-host navigation links."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hrefs = set()

    def handle_starttag(self, tag, attrs):
        if tag == "a" and len(self.hrefs) < MAX_LINKS:
            target = dict(attrs).get("href")
            if isinstance(target, str):
                absolute = urljoin(HOMEPAGE, target)
                if _same_host(absolute) and urlsplit(absolute).path.startswith("/it/"):
                    self.hrefs.add(absolute)


def _home_navigation(raw):
    if not isinstance(raw, bytes) or not 12 <= len(raw) <= MAX_BYTES:
        raise ValueError("Happings homepage exceeded reviewed bounds")
    parser = _HomeNavigation()
    parser.feed(raw.decode("utf-8-sig", "strict"))
    parser.close()
    market_categories = sorted(url for url in parser.hrefs
                               if re.fullmatch(r"https://www\.happings\.com/it/categoria-evento/[a-z0-9-]+/", url)
                               and re.search(r"mercat|antiquar|vintage|pulci|usato", url))
    location_categories = sorted(url for url in parser.hrefs
                                 if re.fullmatch(r"https://www\.happings\.com/it/eventi-a-[a-z0-9-]+/", url))
    return {"sha256": hashlib.sha256(raw).hexdigest(),
            "market_category_urls": market_categories[:100],
            "city_index_urls": location_categories[:300],
            "italy_portal_linked": "https://www.happings.com/it/category/eventi-nel-mondo-it/italia-it/" in parser.hrefs,
            "same_host_links": len(parser.hrefs)}


class _RejectRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ValueError("Happings sitemap redirected outside observed source URL")


def fetch_one(url, *, robots):
    """Fetch only the public homepage or observed XML sitemaps."""
    if (not _same_host(url) or not (url in {INDEX, HOMEPAGE} or _post_sitemap(url))
            or robots is None or not robots.can_fetch(source.USER_AGENT, url)):
        raise ValueError("Unreviewed or robots-disallowed Happings sitemap")
    source._public_dns("www.happings.com")
    request = Request(url, headers={"User-Agent": source.USER_AGENT,
                                    "Accept": "text/html" if url == HOMEPAGE else "application/xml,text/xml",
                                    "Accept-Encoding": "identity"})
    with build_opener(_RejectRedirect()).open(request, timeout=18) as response:
        mime = str(response.headers.get("Content-Type", "")).split(";", 1)[0].strip().lower()
        expected = {"text/html"} if url == HOMEPAGE else {"application/xml", "text/xml"}
        if (response.status != 200 or response.url != url or mime not in expected):
            raise ValueError("Unexpected Happings sitemap transport or MIME")
        body = response.read(MAX_BYTES + 1)
    if not 12 <= len(body) <= MAX_BYTES:
        raise ValueError("Happings sitemap exceeded its byte limit")
    return body, url


def discover(*, today, robots, policy, fetcher=None, sleep=time.sleep,
             monotonic=time.monotonic):
    """Return only observed Italian province URLs and a bounded audit report.

    Every attempted sitemap consumes a slot from the *weekly* page budget.
    When more post sitemaps appear than fit, rotate the chosen maps by date.
    A missing/invalid sitemap is not interpreted as evidence a market closed.
    """
    policy = validate_policy(policy)
    if type(today) is not date:
        raise ValueError("Directory discovery needs its actual run date")
    report = {"enabled": policy["enabled"], "status": "disabled",
              "requests_used": 0, "max_requests": policy["max_requests"],
              "max_seconds": policy["max_seconds"], "post_sitemaps_listed": 0,
              "post_sitemaps_attempted": 0, "post_sitemaps_deferred": 0,
              "candidate_urls": 0, "out_of_scope_urls": 0,
              "italian_province_urls": 0, "italian_province_scopes": 0,
              "homepage": {}, "source_sitemaps": [], "failures": []}
    if not policy["enabled"]:
        return [], report
    if (robots is None or not hasattr(robots, "site_maps")
            or INDEX not in (robots.site_maps() or [])
            or not robots.can_fetch(source.USER_AGENT, INDEX)):
        report["status"] = "robots_index_unavailable"
        return [], report

    fetcher = fetcher or fetch_one
    started = monotonic()
    delay = source._request_pause(robots)

    def attempt(url):
        if (report["requests_used"] >= policy["max_requests"]
                or monotonic() - started + delay >= policy["max_seconds"]):
            return None, "elapsed_or_request_budget"
        if not robots.can_fetch(source.USER_AGENT, url):
            return None, "robots_denied"
        sleep(delay)
        if monotonic() - started >= policy["max_seconds"]:
            return None, "elapsed_or_request_budget"
        report["requests_used"] += 1
        try:
            raw, final = fetcher(url, robots=robots)
            if final != url:
                raise ValueError("Publisher sitemap redirected")
            return raw, None
        except (OSError, HTTPError, ValueError, ElementTree.ParseError) as error:
            return None, type(error).__name__

    # The actual website homepage is always the first visited content page.
    # Its category/city navigation acts as an independent map of site types.
    home_body, home_error = attempt(HOMEPAGE)
    if home_error:
        report["status"] = "home_unavailable"
        report["failures"].append({"url": HOMEPAGE, "reason": home_error})
        return [], report
    try:
        report["homepage"] = _home_navigation(home_body)
    except ValueError as error:
        report["status"] = "home_layout_changed"
        report["failures"].append({"url": HOMEPAGE, "reason": type(error).__name__})
        return [], report

    raw, error = attempt(INDEX)
    if error:
        report["status"] = "index_unavailable"
        report["failures"].append({"url": INDEX, "reason": error})
        return [], report
    try:
        posts = sorted(set(url for url in _locations(raw, index=True) if _post_sitemap(url)))
    except (ValueError, ElementTree.ParseError) as error:
        report["status"] = "index_layout_changed"
        report["failures"].append({"url": INDEX, "reason": type(error).__name__})
        return [], report

    report["post_sitemaps_listed"] = len(posts)
    available = policy["max_requests"] - report["requests_used"]
    if len(posts) > available:
        start = (today.toordinal() * available) % len(posts)
        selected = [posts[(start + i) % len(posts)] for i in range(available)]
    else:
        selected = posts
    report["post_sitemaps_deferred"] = len(posts) - len(selected)
    recognized = source._official_geography()[1]
    found = set()
    provinces = set()
    for url in selected:
        raw, error = attempt(url)
        report["post_sitemaps_attempted"] += int(error != "elapsed_or_request_budget")
        if error:
            report["failures"].append({"url": url, "reason": error})
            continue
        try:
            locations = _locations(raw, index=False)
        except (ValueError, ElementTree.ParseError) as error:
            report["failures"].append({"url": url, "reason": type(error).__name__})
            continue
        report["source_sitemaps"].append({"url": url, "sha256": hashlib.sha256(raw).hexdigest(),
                                          "locations": len(locations)})
        for candidate in locations:
            key = province_page_key(candidate) if _same_host(candidate) else None
            report["candidate_urls"] += 1
            areas = recognized.get(key, set())
            if not key or len(areas) != 1:
                report["out_of_scope_urls"] += 1
                continue
            found.add(candidate)
            provinces.update(areas)
    report["italian_province_urls"] = len(found)
    report["italian_province_scopes"] = len(provinces)
    report["status"] = ("partial" if report["failures"] or report["post_sitemaps_deferred"]
                        else "retrieved")
    return sorted(found), report
