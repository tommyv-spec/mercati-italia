#!/usr/bin/env python3
"""Bounded, source-level event discovery for Mercati d'Italia (DEV research ONLY).

Sources are reviewed per publisher and layout, not per event. Uses official
open-data fields or, for a proprietary listing, LINKS ONLY. Never copies third
party descriptions, marks an event verified, changes catalog IDs, or publishes.
A network outage cannot imply a market was cancelled.
"""
from __future__ import annotations

import argparse
import hashlib
import html
import ipaddress
import json
import re
import socket
import time
import unicodedata
from datetime import date, timedelta
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlencode, urlsplit, unquote, urlunsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from merge_catalog import load_existing

FIRENZE_URL = (
    "https://datigis.comune.fi.it/resources/open-data/eventi-a-firenze/"
    "feelflorence_eventi.geojson"
)
BOLOGNA_BASE = (
    "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/"
    "eventi-bologna-agenda-cultura/records"
)
EVENTI_BASE = "https://www.eventiesagre.it"
EVENTI_ROBOTS = EVENTI_BASE + "/robots.txt"
USER_AGENT = "MercatiItaliaReadOnlyEventLeadAudit/1.0 (+https://github.com/tommyv-spec/mercati-italia)"
MAX_BYTES = 900_000
MAX_OFFICIAL_ROWS = 2000
MAX_PAGE_RESULTS = 50
MAX_BOL_PAGES = 3
MAX_EXTERNAL_LIST_PAGES = 4
MAX_PERSISTED_LEADS = 320
MAX_SCAN_ERROR_LEN = 100
RUN_HORIZON_DAYS = 150
MARKET_TITLES = re.compile(
    r"\b(mercat(?:o|i|ino|ini)|antiquariat[oi]|artigianat[oi]|"
    r"modernariato|vintage|collezionism[oi]|sagr[ae]|"
    r"mostr[ae]\s+mercat[oi]|fiere?|filiera\s+corta)\b", re.I
)
IGNORE_TITLES = re.compile(
    r"\b(mercato\s+(?:nero|sonato|del\s+lavoro|finanziario)|"
    r"fiera\s+delle\s+idee|fiera\s+del\s+libro|sagra\s+della\s+lettura)\b",
    re.I,
)
# Deliberately bounded source taxonomy. "Fiere" and "sagre" are leads for
# follow-up, NOT automatically admissible market identities.
EVENTI_SECTIONS = ("Antiquariato", "Artigianato", "Collezionismo",
                  "Usato", "Filiera+Corta")
REGION_SLUGS = (
    "Toscana", "Emilia+Romagna", "Lombardia", "Veneto", "Piemonte",
    "Lazio", "Campania", "Puglia", "Sicilia", "Liguria",
    "Abruzzo", "Marche", "Umbria", "Sardegna", "Calabria",
    "Friuli+Venezia+Giulia", "Trentino+Alto+Adige", "Basilicata",
    "Molise", "Valle+D%27aosta",
)
VENUE_TOKEN_EXCLUDE = frozenset({
    "mercato", "mercatino", "mercatini", "mercati", "di", "del", "della",
    "delle", "dei", "e", "a", "in", "il", "la", "lo", "un", "una", "piazza",
    "mercatino", "settimanale", "antiquariato",
})


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def canonical(value):
    norm = unicodedata.normalize("NFKD", str(value or ""))
    norm = "".join(ch for ch in norm if not unicodedata.combining(ch)).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", norm))


def fingerprint(value):
    return hashlib.sha256(json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def official_date(value):
    if not isinstance(value, str) or not value.strip():
        return None
    raw = value.strip()[:10]
    try:
        if re.fullmatch(r"\d{2}/\d{2}/\d{4}", raw):
            return date(int(raw[6:]), int(raw[3:5]), int(raw[:2]))
        return date.fromisoformat(raw)
    except ValueError:
        return None


def kind_for_title(value):
    name = str(value or "").strip()
    if not name or IGNORE_TITLES.search(name) or not MARKET_TITLES.search(name):
        return None
    text = canonical(name)
    if "sagra" in text or "sagre" in text:
        return "related_sagra_review"
    if "fiera" in text or "fiere" in text:
        return "fair_review"
    if "antiquariato" in text or "modernariato" in text or "vintage" in text:
        return "antique_vintage_market_candidate"
    return "market_candidate"


def public_event_url(source, url):
    if not isinstance(url, str) or len(url) > 700:
        return False
    try:
        p = urlsplit(url)
        if (p.scheme != "https" or p.username or p.password or
                p.port not in (None, 443) or p.query or p.fragment):
            return False
        if source == "firenze-feelflorence":
            return p.hostname == "www.feelflorence.it" and p.path.startswith("/it/eventi/")
        if source == "bologna-agenda":
            return p.hostname == "culturabologna.it" and bool(
                re.fullmatch(r"/events/\d{1,12}", p.path))
    except ValueError:
        return False
    return False


def allowed_request(url):
    """Independent URL scope check: never follow redirects, never arbitrary hosts."""
    try:
        p = urlsplit(url)
        if (p.scheme != "https" or p.username or p.password or
                p.port not in (None, 443) or p.fragment):
            return False
        if url == FIRENZE_URL or url == EVENTI_ROBOTS:
            return True
        if (p.hostname == "opendata.comune.bologna.it"
                and p.path == urlsplit(BOLOGNA_BASE).path):
            from urllib.parse import parse_qs
            q = parse_qs(p.query, keep_blank_values=True)
            return (set(q) == {"where", "limit", "offset"}
                    and len(q["where"]) == len(q["limit"]) == len(q["offset"]) == 1
                    and q["where"][0].startswith("(start >= date'")
                    and len(q["where"][0]) < 500
                    and q["limit"][0] == str(MAX_PAGE_RESULTS)
                    and q["offset"][0] in {
                        str(i * MAX_PAGE_RESULTS) for i in range(MAX_BOL_PAGES)
                    })
        if p.hostname == "www.eventiesagre.it" and not p.query:
            return bool(re.fullmatch(
                r"/cerca/Mercatini/(?:Antiquariato|Artigianato|Collezionismo|Usato|Filiera\+Corta)"
                r"/mesi/(?:[A-Za-z0-9+%]+)/(?:prov/cit/rilib)", p.path)
                and p.path.split("/")[5] in REGION_SLUGS)
    except (ValueError, KeyError):
        return False
    return False


def guarded_fetch(url):
    """Strict outbound whitelist + public DNS + 900KB byte cap, no redirects."""
    if not allowed_request(url):
        raise ValueError("Unapproved discovery URL")
    host = urlsplit(url).hostname
    for entry in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(entry[4][0]).is_global:
            raise ValueError("Source resolved to a non-public address")
    request = Request(url, headers={
        "User-Agent": USER_AGENT, "Accept": "application/json,text/html,text/plain",
        "Accept-Encoding": "identity",
    })
    with build_opener(NoRedirect).open(request, timeout=12) as response:
        blob = response.read(MAX_BYTES + 1)
    if len(blob) > MAX_BYTES:
        raise ValueError("Source exceeded bounded discovery response size")
    return blob


def verify_registry(registry):
    if (not isinstance(registry, dict) or registry.get("schema") != 1
            or registry.get("publication_channel") != "dev-research-only"
            or registry.get("market_import_permission") is not False
            or registry.get("event_confirmation_permission") is not False
            or not isinstance(registry.get("sources"), list)):
        raise ValueError("Untrusted event discovery source registry")
    required = {
        "firenze-feelflorence": ("official_geojson", FIRENZE_URL),
        "bologna-agenda": ("official_odsv2", BOLOGNA_BASE),
        "eventiesagre-index": ("links_only_html", EVENTI_BASE),
    }
    if {entry.get("id") for entry in registry["sources"] if isinstance(entry, dict)} != set(required):
        raise ValueError("Source contracts cannot add unknown HTTP endpoints")
    if len(registry["sources"]) != len(required):
        raise ValueError("Duplicated source contracts")
    for entry in registry["sources"]:
        sid = entry["id"]
        if (entry.get("type") != required[sid][0] or
                entry.get("url") != required[sid][1] or
                entry.get("enabled") is not True or
                entry.get("publish_to_catalog") is not False or
                entry.get("may_confirm_dates") is not False or
                entry.get("may_create_coordinates") is not False or
                entry.get("mode") not in ("official_leads_only", "external_urls_only")
                or not isinstance(entry.get("publisher"), str)
                or not entry["publisher"]):
            raise ValueError("Publisher source contract exceeds discovery-only scope")
        if sid == "eventiesagre-index":
            if (entry["mode"] != "external_urls_only"
                    or entry.get("fields_saved") != ["source_event_id", "detail_url"]
                    or entry.get("rights_status") != "no_content_reuse_permission"):
                raise ValueError("Proprietary aggregator cannot supply event facts")
        elif (entry["mode"] != "official_leads_only"
              or entry.get("license") != "CC BY 4.0"):
            raise ValueError("Official event data needs a reviewed source license")
    return {item["id"]: item for item in registry["sources"]}


def build_bologna_url(today, offset=0):
    if not isinstance(today, date) or offset not in {
        i * MAX_PAGE_RESULTS for i in range(MAX_BOL_PAGES)
    }:
        raise ValueError("Invalid bounded API pagination")
    # Search is a SOURCE filter, not proof that the result is a market.
    words = ("mercat", "fier", "sagra", "artigian", "antiquariat", "vintage")
    filters = " OR ".join("search(title, '" + item + "')" for item in words)
    where = ("(start >= date'" + today.isoformat() + "' OR end >= date'"
             + today.isoformat() + "') AND (" + filters + ")")
    return BOLOGNA_BASE + "?" + urlencode({
        "where": where, "limit": MAX_PAGE_RESULTS, "offset": offset
    })


def _lead(source_id, original_id, title, city, start, end, url):
    kind = kind_for_title(title)
    if not kind or not public_event_url(source_id, url):
        return None
    if not isinstance(original_id, str) or not re.fullmatch(r"[a-zA-Z0-9_-]{1,65}", original_id):
        return None
    if start is None or end is None or end < start:
        return None
    return {
        "id": source_id + ":" + original_id,
        "source_id": source_id,
        "title": re.sub(r"\s+", " ", title).strip()[:160],
        "city": re.sub(r"\s+", " ", city).strip()[:70],
        "start": start.isoformat(),
        "end": end.isoformat(),
        "source_url": url,
        "kind": kind,
        "status": "source_lead_unverified",
        "opening_confirmed": False,
        "catalog_import_allowed": False,
    }


def parse_firenze(blob, today):
    payload = json.loads(blob)
    if (not isinstance(payload, dict) or payload.get("type") != "FeatureCollection"
            or not isinstance(payload.get("features"), list)
            or not 1 <= len(payload["features"]) <= MAX_OFFICIAL_ROWS
            or payload.get("totalFeatures", len(payload["features"])) != len(payload["features"])):
        raise ValueError("Official Firenze GeoJSON structure/count changed")
    seen, leads, rejected = set(), [], 0
    for item in payload["features"]:
        if (not isinstance(item, dict) or item.get("type") != "Feature"
                or not isinstance(item.get("properties"), dict)):
            raise ValueError("Unexpected Firenze feature schema")
        p = item["properties"]
        if not {"titolo", "comuni", "data_inizio", "data_fine", "feelflorence_link"} <= set(p):
            raise ValueError("Firenze publisher removed reviewed fields")
        event_id = item.get("id")
        if type(event_id) is not int or event_id < 1 or event_id in seen:
            raise ValueError("Duplicate or missing official Firenze event identity")
        seen.add(event_id)
        title = p.get("titolo") or ""
        start, end = official_date(p.get("data_inizio")), official_date(p.get("data_fine"))
        city = str(p.get("comuni") or "")
        if (start is None or end is None or end < today or
                start > today + timedelta(days=RUN_HORIZON_DAYS)
                or canonical(city) != "firenze"):
            rejected += 1
            continue
        candidate = _lead("firenze-feelflorence", str(event_id), title, city,
                          start, end, str(p.get("feelflorence_link") or ""))
        if candidate:
            leads.append(candidate)
        else:
            rejected += 1
    return leads, {
        "rows_examined": len(payload["features"]), "leads_found": len(leads),
        "not_matching_market_scope": rejected,
        "schema_digest": fingerprint(sorted(
            payload["features"][0]["properties"].keys())),
    }


def parse_bologna_pages(pages, today):
    if not isinstance(pages, list) or not pages or len(pages) > MAX_BOL_PAGES:
        raise ValueError("Unbounded official Bologna pages")
    total = None
    allrows, seen = [], set()
    for index, blob in enumerate(pages):
        payload = json.loads(blob)
        if (not isinstance(payload, dict) or type(payload.get("total_count")) is not int
                or not 0 <= payload["total_count"] <= MAX_PAGE_RESULTS * MAX_BOL_PAGES
                or not isinstance(payload.get("results"), list)
                or len(payload["results"]) > MAX_PAGE_RESULTS):
            raise ValueError("Bologna count or result schema changed")
        if total is None:
            total = payload["total_count"]
        if total != payload["total_count"]:
            raise ValueError("Bologna changed during paginated retrieval")
        if len(payload["results"]) != min(MAX_PAGE_RESULTS, max(0, total-index*MAX_PAGE_RESULTS)):
            raise ValueError("Incomplete Bologna official page")
        for item in payload["results"]:
            if not isinstance(item, dict) or not {
                "id", "title", "start", "url", "address"
            } <= set(item):
                raise ValueError("Missing Bologna event fields")
            eid = str(item["id"])
            if not eid.isdecimal() or eid in seen:
                raise ValueError("Duplicate official Bologna event ID")
            seen.add(eid)
            allrows.append(item)
    if len(allrows) != total:
        raise ValueError("Incomplete official Bologna publisher cohort")
    leads = []
    for item in allrows:
        start = official_date(item.get("start"))
        end = official_date(item.get("end")) or start
        if (start is None or end < today or
                start > today + timedelta(days=RUN_HORIZON_DAYS)):
            continue
        # No unlicensed source redirects or inferred event coordinates.
        lead = _lead("bologna-agenda", str(item["id"]),
                     item.get("title") or "", "Bologna", start, end,
                     str(item.get("url") or ""))
        if lead:
            leads.append(lead)
    return leads, {
        "rows_examined": len(allrows), "leads_found": len(leads),
        "not_matching_market_scope": len(allrows)-len(leads),
        "schema_digest": fingerprint(sorted(allrows[0].keys())) if allrows else None,
    }


class LinkIndexParser(HTMLParser):
    """Extract only href/ID *after* list heading, never the promoted links/text."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.heading_buffer = ""
        self.heading_count = 0
        self.links = []
        self.script_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.script_depth += 1
        if tag != "a" or self.heading_count != 1:
            return
        href = dict(attrs).get("href") or ""
        # No other category, host or URL is stored.
        p = urlsplit(html.unescape(href.strip()))
        if p.scheme or p.netloc or p.query or p.fragment:
            return
        match = re.fullmatch(
            r"/Mercatini_[A-Za-z+ ]{2,40}/(\d{4,12})_([A-Za-z0-9+%._'-]{1,160})\.html",
            p.path,
        )
        if match:
            url = EVENTI_BASE + p.path.replace(" ", "%20")
            if all(prev["id"] != match.group(1) for prev in self.links):
                self.links.append({"id": match.group(1), "url": url})

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.script_depth:
            self.script_depth -= 1

    def handle_data(self, data):
        if self.script_depth:
            return
        self.heading_buffer = (self.heading_buffer + " " + data)[-170:]
        if re.search(r"Elenco\s+Eventi\s+da\s+\d+\s+a\s+\d+\s+di\s+\d+",
                     self.heading_buffer, re.I):
            # Clear buffer to avoid counting the same header twice.
            self.heading_count += 1
            self.heading_buffer = ""


def parse_eventiesagre_links(blob, max_links=10):
    body = blob.decode("utf-8", errors="replace")
    parser = LinkIndexParser()
    parser.feed(body)
    parser.close()
    if parser.heading_count < 1:
        raise ValueError("Third-party listing markup changed: no list heading")
    if len(parser.links) > max_links:
        # More rows than the observed first-page budget: reject rather than
        # silently expanding a copyrighted site crawl.
        raise ValueError("Third-party listing exceeded bounded first-page quota")
    return parser.links


def check_robots(fetch, targets):
    raw = fetch(EVENTI_ROBOTS).decode("utf-8", errors="replace")
    if not raw or "user-agent:" not in raw.lower() or len(raw) > 64_000:
        raise ValueError("Publisher robots policy unavailable or malformed")
    robots = RobotFileParser()
    robots.parse(raw.splitlines())
    if any(not robots.can_fetch(USER_AGENT, url) for url in targets):
        raise ValueError("Publisher robots policy denies discovery index")
    return True


def planned_listing_urls(today):
    """Four section+region queries/day, rotates to all combinations."""
    seq = today.toordinal()
    urls = []
    # Three region slices; pairs of sections change independently per week.
    for i in range(2):
        reg = REGION_SLUGS[(seq*3 + i*7) % len(REGION_SLUGS)]
        section = EVENTI_SECTIONS[(seq//7 + i) % len(EVENTI_SECTIONS)]
        urls.append(EVENTI_BASE + "/cerca/Mercatini/" + section +
                    "/mesi/" + reg + "/prov/cit/rilib")
    assert len(urls) <= MAX_EXTERNAL_LIST_PAGES
    return urls


def _token_match(lead, existing):
    """Comparison hint only. Missing address prevents any auto-merge."""
    name = set(canonical(lead.get("title")).split())-VENUE_TOKEN_EXCLUDE
    city = canonical(lead.get("city"))
    if not city or len(name) < 2:
        return []
    matches = []
    for row in existing:
        if canonical(row.get("citta")) != city:
            continue
        if not row.get("indirizzo"):
            continue
        old = set(canonical(row.get("nome")).split())-VENUE_TOKEN_EXCLUDE
        if len(name & old) >= 2 and len(name & old) >= min(len(name), len(old)):
            matches.append(row.get("slug"))
        if len(matches) > 5:
            return []  # ambiguous/duplicated name, no positive matching claim
    return [x for x in matches if isinstance(x, str)]


def validate_previous(prior):
    if prior is None:
        return {}
    if (not isinstance(prior, dict) or prior.get("schema") != 1 or
            prior.get("research_only") is not True or
            prior.get("catalog_imports") != 0 or
            prior.get("individual_event_confirmations") != 0 or
            not isinstance(prior.get("leads"), list) or
            len(prior["leads"]) > MAX_PERSISTED_LEADS):
        raise ValueError("Untrusted persisted event-lead history")
    return {x["id"]: x for x in prior["leads"]
            if isinstance(x, dict) and isinstance(x.get("id"), str)}


def collect(registry, existing, *, today=None, previous=None,
            fetch=guarded_fetch, offline=False):
    today = today or date.today()
    if not isinstance(today, date) or not isinstance(existing, list):
        raise ValueError("Invalid reference date or catalog")
    sources = verify_registry(registry)
    prior = validate_previous(previous)
    fetched = []
    source_states = []
    all_leads = []
    if len({r.get("slug") for r in existing}) != len(existing):
        raise ValueError("Baseline has duplicate market IDs")

    def record(sid, status, checked, details=None, reason=None):
        row = {"id": sid, "state": status, "requests": checked,
               "catalog_market_imports": 0, "event_confirmations": 0}
        if details:
            row.update(details)
        if reason:
            row["reason_class"] = reason[:MAX_SCAN_ERROR_LEN]
        source_states.append(row)

    for sid in ("firenze-feelflorence", "bologna-agenda", "eventiesagre-index"):
        if offline:
            record(sid, "offline_skipped", 0)
            continue
        try:
            if sid == "firenze-feelflorence":
                raw = fetch(sources[sid]["url"])
                leads, summary = parse_firenze(raw, today)
                count = 1
            elif sid == "bologna-agenda":
                first = json.loads(fetch(build_bologna_url(today, 0)))
                total = first.get("total_count")
                if type(total) is not int or not 0 <= total <= MAX_PAGE_RESULTS * MAX_BOL_PAGES:
                    raise ValueError("Bologna query result exceeds bounded read budget")
                pages = [json.dumps(first).encode("utf-8")]
                for i in range(1, (total + MAX_PAGE_RESULTS - 1)//MAX_PAGE_RESULTS):
                    pages.append(fetch(build_bologna_url(today, i*MAX_PAGE_RESULTS)))
                leads, summary = parse_bologna_pages(pages, today)
                count = len(pages)
            else:
                targets = planned_listing_urls(today)
                check_robots(fetch, targets)
                links = []
                for url in targets:
                    if not allowed_request(url):
                        raise ValueError("Unreviewed external listing index URL")
                    # Source only supplies a link/ID; NEVER title/date/description.
                    for item in parse_eventiesagre_links(fetch(url)):
                        if item["id"] not in {x["id"] for x in links}:
                            links.append(item)
                    time.sleep(1)
                leads = [{
                    "id": "eventiesagre-index:" + x["id"],
                    "source_id": sid,
                    "source_url": x["url"],
                    "status": "external_pointer_only_no_fact_reuse",
                    "opening_confirmed": False,
                    "catalog_import_allowed": False,
                } for x in links]
                summary = {
                    "indexes_read": len(targets), "links_only": len(leads),
                    "descriptions_copied": 0, "publisher_events_verified": 0,
                }
                count = len(targets)+1
            fetched.extend(leads)
            all_leads.extend(leads)
            record(sid, "discovery_leads_only", count, summary)
        except (OSError, ValueError, UnicodeError, KeyError,
                json.JSONDecodeError, TimeoutError) as exc:
            # Do not infer a closure or loss from a source/robots outage.
            record(sid, "source_unavailable_or_schema_review", 0,
                   reason=type(exc).__name__)

    found = {}
    for lead in all_leads:
        if lead["id"] in found:
            raise ValueError("Source produced duplicate event lead identity")
        item = dict(lead)
        first = prior.get(item["id"])
        item["first_seen"] = (first.get("first_seen", today.isoformat())
                              if first else today.isoformat())
        item["last_seen"] = today.isoformat()
        if lead["source_id"] == "eventiesagre-index":
            item["possible_existing_market_ids"] = []
        else:
            item["possible_existing_market_ids"] = _token_match(lead, existing)
        found[item["id"]] = item
    # Previous leads may be retained temporarily as explicit historical
    # pointers (not "still available" or "event cancelled"). Ignore old
    # marketing claim and do not treat absence as confirmed cancellation.
    for sid, past in prior.items():
        if sid in found:
            continue
        old = official_date(past.get("last_seen"))
        if old and 0 <= (today-old).days <= 30:
            copy = dict(past)
            copy["status"] = "not_seen_again_not_a_market_closure"
            copy["possible_existing_market_ids"] = []
            found[sid] = copy
    listed = sorted(found.values(), key=lambda x: (
        x.get("last_seen", ""), x["id"]), reverse=True)[:MAX_PERSISTED_LEADS]
    return {
        "schema": 1, "reference_date": today.isoformat(),
        "research_only": True, "catalog_imports": 0,
        "catalog_updates": 0, "individual_event_confirmations": 0,
        "precise_coordinates_created": 0, "publisher_rights_inferred": False,
        "registry_digest": fingerprint(registry),
        "baseline_market_records": len(existing),
        "baseline_market_ids_preserved": len(existing),
        "checked_sources": source_states, "leads": listed,
        "fresh_official_leads": sum(
            x["source_id"] != "eventiesagre-index"
            and x["status"] == "source_lead_unverified"
            and x["last_seen"] == today.isoformat() for x in listed),
        "new_external_url_pointers": sum(
            x["source_id"] == "eventiesagre-index"
            and x["last_seen"] == today.isoformat() for x in listed),
        "new_market_records_created": 0,
    }


def validate_report(report, registry, original_count):
    sids = {x["id"] for x in verify_registry(registry).values()}
    if (report.get("schema") != 1 or report.get("research_only") is not True
            or report.get("registry_digest") != fingerprint(registry)
            or report.get("baseline_market_records") != original_count
            or report.get("baseline_market_ids_preserved") != original_count
            or {x.get("id") for x in report.get("checked_sources", [])} != sids
            or len(report.get("checked_sources", [])) != len(sids)
            or len(report.get("leads", [])) > MAX_PERSISTED_LEADS
            or any(report.get(k) != 0 for k in (
                "catalog_imports", "catalog_updates",
                "individual_event_confirmations",
                "precise_coordinates_created", "new_market_records_created"))):
        raise ValueError("Event discovery exceeded its read-only contract")
    for item in report["leads"]:
        sid = item.get("source_id")
        if sid not in sids or item.get("catalog_import_allowed") is not False:
            raise ValueError("Unapproved event lead source")
        if item.get("opening_confirmed") is not False:
            raise ValueError("Event lead falsely confirmed an opening")
        if sid == "eventiesagre-index" and any(k in item for k in (
            "title", "description", "start", "end", "city", "coordinates")):
            raise ValueError("Proprietary event text cannot be persisted")
    return True


def markdown(report):
    lines = [
        "# Mercati Italia — scoperta automatica eventi: solo segnali",
        "",
        "Nessun evento è stato aggiunto o confermato. Data di controllo: **" +
        report["reference_date"] + "**.",
        "Le assenze di una fonte o di un link NON provano la chiusura di un mercato.",
        "",
        "- Schede di mercato esistenti conservate: **" +
        str(report["baseline_market_ids_preserved"]) + "**",
        "- Segnali ufficiali nell'ultima scansione: **" +
        str(report["fresh_official_leads"]) + "**",
        "- Collegamenti esterni, non dati riutilizzabili: **" +
        str(report["new_external_url_pointers"]) + "**",
        "",
        "| Fonte | Stato | Richieste |",
        "|---|---|---:|",
    ]
    for item in report["checked_sources"]:
        lines.append("| " + item["id"] + " | " + item["state"] + " | " +
                     str(item["requests"]) + " |")
    lines.extend(["", "## Segnali da verificare presso Comune o organizzatore", ""])
    for item in report["leads"][:35]:
        link = item.get("source_url", "")
        title = item.get("title") if item["source_id"] != "eventiesagre-index" else "Link esterno (ID soltanto)"
        lines.append("- " + str(title).replace("|", "/").replace("\n", " ") +
                     " — " + link + " — stato: " + item["status"])
    lines.extend([
        "",
        "Non importare contenuti di EventiESagre: si raccolgono solo URL e ID.",
        "Non usare le date generiche di inizio/fine come apertura verificata.",
        "Le fonti ufficiali richiedono attribuzione CC BY 4.0.",
    ])
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--registry", type=Path, default=Path(
        "backend/data/event-lead-source-contracts.json"))
    p.add_argument("--manifest", type=Path, default=Path(
        "public/data/v1/manifest.json"))
    p.add_argument("--previous", type=Path, default=Path(
        "reports/automation/event-leads.json"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--offline", action="store_true")
    p.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = p.parse_args()
    reg = json.loads(args.registry.read_text("utf-8"))
    prior = (json.loads(args.previous.read_text("utf-8"))
             if args.previous.is_file() else None)
    baseline = load_existing(args.manifest)
    report = collect(reg, baseline, previous=prior, offline=args.offline,
                     today=args.today)
    validate_report(report, reg, len(baseline))
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, sort_keys=True, indent=2,
                                   ensure_ascii=False) + "\n", "utf-8")
    args.report.write_text(markdown(report), "utf-8")
    print(json.dumps({
        "sources": len(report["checked_sources"]),
        "official_leads": report["fresh_official_leads"],
        "external_pointers": report["new_external_url_pointers"],
        "markets_modified": 0, "verified_openings": 0,
    }))


if __name__ == "__main__":
    main()
