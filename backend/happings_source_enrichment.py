#!/usr/bin/env python3
"""Publisher-specific Happings market-field repair with strict provenance.

A Happings index is a town + weekday + market-area directory, NOT an exact
time schedule or individually confirmed weekly opening. Parse once per
publisher layout, compare with existing source-URL-scoped identities, and
fill missing addresses or refresh this engine's earlier assignments only
after a unique source row and no catalog conflict.

The same acquired pages can corroborate another origin's already identical
street and weekday. Those secondary observations never assign field values
or acquire ownership. A later unambiguous source contradiction retires only
that publisher's old support, preserving the saved market and other sources.

Default mode is a no-write field audit. The project owner's explicit
instruction authorizes the configured, bounded DEV crawler. That instruction
is recorded separately from authentication of publisher documents. Requests
remain robots-aware and every changed field must have exact source evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import socket
import time
import unicodedata
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date
from http.client import HTTPException
from functools import lru_cache
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser

from happings_weekly_layout import parse, fold, _valid_page_url, province_page_key
from happings_page_metadata import clean_page_metadata
from stored_market_sibling_proposals import same_generic_venue, safe_stored_street
from source_reconciliation_audit import _unambiguous_day
from recurrence_refresh import explicit_rule, temporal_scope_hold
from merge_catalog import load_existing
from municipality_reconciliation import trusted_municipalities
from field_evidence import (clean_receipts, make_receipt, managed_update_allowed,
                            mark_managed_fields, retire_superseded_receipts, safe_url)

SCHEMA=1
PUBLISHER="happings.com"
ROBOTS="https://www.happings.com/robots.txt"
MAX_REQUESTS_PER_RUN=16
MAX_RESPONSE_BYTES=2_600_000
MAX_MARKETS=100_000
MAX_UPDATES_PER_RUN=2000
MIN_REQUEST_PAUSE_SECONDS=3
USER_AGENT="MercatiItaliaMarketFields/1.0 (+https://github.com/tommyv-spec/mercati-italia)"
RIGHTS_REVIEW_FILE=Path(__file__).resolve().parent/"data/happings-rights-review.json"
WEEKLY_PAGES_FILE=Path(__file__).resolve().parent/"data/happings-weekly-pages.json"


def saved_weekly_pages():
    """Every Italian province page; a province whose old markets cite a retired
    .html route (Verbania, Trieste...) is otherwise never read by the rotation."""
    return json.loads(WEEKLY_PAGES_FILE.read_text("utf-8"))["urls"]
MUNICIPALITIES_FILE=Path(__file__).resolve().parent/"data/istat-comuni-2026.json"
SOURCE_EVIDENCE_NAME="Happings — elenco settimanale (sede indicativa; apertura non verificata)"
FIELD_MANAGER="happings-weekly-index"
# Provinces created in 2009 that have no Happings page of their own: Happings
# still lists their towns on the parent province page.
PAGE_EXTRA_PROVINCES={"milano":{"MB"},"bari":{"BT"},"foggia":{"BT"}}
FAILURE_CODES=frozenset({
    "redirect_hop_limit", "redirect_loop", "redirect_unreviewed", "redirect_crossed_province",
    "robots_denied_requested", "robots_denied_redirect", "robots_unavailable", "robots_invalid",
    "crawl_delay_exceeded", "source_url_unreviewed", "source_dns_not_public", "dns_failure",
    "response_mime_changed", "response_size_exceeded", "final_url_unreviewed",
    "http_error", "connection_error", "timeout", "response_incomplete", "validation_failed",
})


def valid_failure_code(value):
    """Allow bounded diagnostics in checkpoints without copying exception text."""
    return isinstance(value,str) and bool(
        value in FAILURE_CODES or re.fullmatch(r"http_[45]\d\d",value))


def failure_code(error):
    """Expose a stable operational reason; raw remote text/URLs stay private."""
    if isinstance(error,HTTPError):
        return "http_"+str(error.code) if type(error.code) is int and 400<=error.code<=599 else "http_error"
    if isinstance(error,socket.gaierror):
        return "dns_failure"
    if isinstance(error,TimeoutError):
        return "timeout"
    if isinstance(error,OSError):
        return "connection_error"
    if isinstance(error,HTTPException):
        return "response_incomplete"
    return {
        "Publisher redirect exceeds bounded hop count":"redirect_hop_limit",
        "Publisher redirect repeats an observed URL":"redirect_loop",
        "Source redirect left reviewed Happings province layout":"redirect_unreviewed",
        "Publisher redirect crossed province":"redirect_crossed_province",
        "Publisher redirected to a different market region":"redirect_crossed_province",
        "Publisher robots policy denied requested weekly index":"robots_denied_requested",
        "Publisher robots policy denied redirected weekly index":"robots_denied_redirect",
        "Publisher robots unavailable: no automatic fetching":"robots_unavailable",
        "Untrusted robots response":"robots_invalid",
        "Publisher robots has no policy":"robots_invalid",
        "Publisher crawl delay exceeds this bounded run":"crawl_delay_exceeded",
        "Unapproved publisher URL":"source_url_unreviewed",
        "Publisher hostname resolved to private address":"source_dns_not_public",
        "Publisher changed response MIME type":"response_mime_changed",
        "Publisher response exceeds bounded size":"response_size_exceeded",
        "Publisher response exceeds bounded source page size":"response_size_exceeded",
        "Publisher sent an unreviewed target URL":"final_url_unreviewed",
    }.get(str(error),"validation_failed")


def authorization_status(record, *, today=None):
    """Project instructions and publisher authentication are distinct facts."""
    today=today or date.today()
    blocked={"authorized":False,"status":"blocked_rights","basis":None,
             "rights_authenticated":False}
    if (not isinstance(today,date) or not isinstance(record,dict)
            or record.get("schema")!=1
            or record.get("publisher")!="Girolamo srls (Happings)"
            or record.get("documents_copied_to_github") is not False):
        return {**blocked,"status":"invalid_or_missing_rights_record"}
    if record.get("republication_rights_authenticated") is True:
        return {"authorized":True,"status":"authenticated",
                "basis":"authenticated_publisher_grant","rights_authenticated":True}
    instruction=record.get("project_authorization")
    if not isinstance(instruction,dict):
        return blocked
    if not isinstance(instruction.get("recorded_on"),str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}",instruction["recorded_on"]):
        return blocked
    try:
        recorded=date.fromisoformat(instruction.get("recorded_on",""))
    except (ValueError,TypeError):
        return blocked
    if (instruction.get("authorized") is True and instruction.get("revoked") is False
            and instruction.get("basis")=="explicit_project_owner_instruction"
            and instruction.get("publication_channel")=="dev-only"
            and isinstance(instruction.get("scope"),list)
            and all(isinstance(item,str) for item in instruction["scope"])
            and sorted(instruction["scope"])==["automated_extraction","processing","republication"]
            and isinstance(instruction.get("instruction_reference"),str)
            and 10<=len(instruction["instruction_reference"])<=500 and recorded<=today):
        return {"authorized":True,"status":"project_owner_authorized",
                "basis":"explicit_project_owner_instruction","rights_authenticated":False}
    return blocked

@lru_cache(maxsize=1)
def _official_geography():
    """Reuse the reviewed local ISTAT reference; never infer a province by majority."""
    reference=trusted_municipalities(json.loads(MUNICIPALITIES_FILE.read_text("utf-8")))
    municipalities={}
    page_areas=defaultdict(set)
    for region, cities in reference.items():
        for name, province in cities.values():
            municipalities[(fold(region),fold(name))]=province
            page_areas[fold(name).replace(" ","-")].add((fold(region),province))
    # These historic publisher province labels differ from the ISTAT
    # municipality name. They identify a scope, not an observed redirect.
    for source_name, municipal_name in {
        "reggio-calabria":"reggio-di-calabria",
        "reggio-emilia":"reggio-nell-emilia",
        "massa-carrara":"massa",
        "ascoli":"ascoli-piceno",
        "caltanisetta":"caltanissetta",
        "forli-e-cesena":"forli",
        "pesaro-urbino":"pesaro",
        # Sardinian provinces under their historic names (ISTAT CI/VS/OG).
        "carbonia-iglesias":"carbonia",
        "medio-campidano":"sanluri",
        "ogliastra":"tortoli",
    }.items():
        page_areas[source_name]=set(page_areas[municipal_name])
    return municipalities,page_areas


def _catalog_geography_matches(row, source_url):
    municipalities,page_areas=_official_geography()
    region=fold(row.get("regione"))
    province=str(row.get("provincia") or "").strip().upper()
    city=fold(row.get("citta"))
    key=province_page_key(source_url)
    expected=page_areas.get(key,set())
    if len(expected)!=1:
        return False
    page_region,page_province=next(iter(expected))
    official=municipalities.get((region,city))
    if (region,province)==(page_region,page_province):
        # Quartieri (Roma), numbered stalls and renamed towns have no ISTAT
        # entry; a known town must still sit in this province.
        return official in (province,None)
    return (region==page_region and official==province
            and province in PAGE_EXTRA_PROVINCES.get(key,()))


def _request_pause(robots):
    delay=MIN_REQUEST_PAUSE_SECONDS
    if robots is not None:
        delay=max(delay,robots.crawl_delay(USER_AGENT) or 0)
        rate=robots.request_rate(USER_AGENT)
        if rate and rate.requests>0:
            delay=max(delay,rate.seconds/rate.requests)
    if delay>60:
        raise ValueError("Publisher crawl delay exceeds this bounded run")
    return delay

class GuardedRedirects(HTTPRedirectHandler):
    def __init__(self, expected, robots=None, sleep=time.sleep):
        super().__init__()
        self.expected=expected
        self.hops=0
        self.robots=robots
        self.sleep=sleep
        self.seen={expected}

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        self.hops+=1
        if self.hops>2:
            raise ValueError("Publisher redirect exceeds bounded hop count")
        if newurl in self.seen:
            raise ValueError("Publisher redirect repeats an observed URL")
        # Observed 2026-10-20 for Crotone/Cuneo: legacy .html -> same
        # exact slug + / -> reviewed -e-provincia/. The middle URL is
        # transport only, never a catalog alias or an accepted final page.
        intermediate=(self.hops==1 and _valid_page_url(self.expected)
                      and self.expected.endswith(".html")
                      and newurl==self.expected[:-5]+"/")
        if not intermediate and not _valid_page_url(newurl):
            raise ValueError("Source redirect left reviewed Happings province layout")
        # Only province-specific old .html --> canonical -e-provincia/
        # changes from the same company. Never read an arbitrary path.
        if not intermediate and province_page_key(self.expected)!=province_page_key(newurl):
            raise ValueError("Publisher redirect crossed province")
        if self.robots is not None and not self.robots.can_fetch(USER_AGENT,newurl):
            raise ValueError("Publisher robots policy denied redirected weekly index")
        self.seen.add(newurl)
        self.sleep(_request_pause(self.robots))
        return super().redirect_request(request,fp,code,msg,headers,newurl)


def _public_dns(host):
    for addr in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(addr[4][0]).is_global:
            raise ValueError("Publisher hostname resolved to private address")


def _fetch_one(url, *, opener=None, limit=MAX_RESPONSE_BYTES, robots=None):
    if not _valid_page_url(url) and url!=ROBOTS:
        raise ValueError("Unapproved publisher URL")
    _public_dns("www.happings.com")
    request=Request(url,headers={
        "User-Agent":USER_AGENT,
        "Accept":"text/plain" if url==ROBOTS else "text/html",
        "Accept-Encoding":"identity",
    })
    opener=opener or build_opener(GuardedRedirects(url,robots))
    with opener.open(request,timeout=18) as resp:
        mime=str(resp.headers.get("Content-Type","")).casefold()
        wanted="text/plain" if url==ROBOTS else "text/html"
        if wanted not in mime:
            raise ValueError("Publisher changed response MIME type")
        raw=resp.read(limit+1)
        final=resp.url
        if len(raw)>limit:
            raise ValueError("Publisher response exceeds bounded size")
        if url!=ROBOTS and not _valid_page_url(final):
            raise ValueError("Publisher sent an unreviewed target URL")
    return raw,final


def robots_allowed(fetch=_fetch_one):
    try:
        raw,real_url=fetch(ROBOTS,limit=55_000)
    except (OSError,HTTPError,HTTPException):
        raise ValueError("Publisher robots unavailable: no automatic fetching") from None
    if real_url!=ROBOTS or not isinstance(raw,bytes) or len(raw)>55_000 or len(raw)<12:
        raise ValueError("Untrusted robots response")
    text=raw.decode("utf-8-sig","replace")
    if "user-agent:" not in text.lower():
        raise ValueError("Publisher robots has no policy")
    robot=RobotFileParser()
    robot.parse(text.splitlines())
    return robot


def allowed_url(record_url,source_url,final_url):
    """Exact old URL/canonical pair, never unreviewed other publisher pages."""
    # Validate all three URLs BEFORE comparing any two. Otherwise a
    # redirect to another province can be accepted merely because the
    # saved catalog URL equals the requested URL.
    for p in (record_url,source_url,final_url):
        if not _valid_page_url(p):
            return False
    # Convert old .../mercati-settimanali-a-{province}.html to
    # current .../mercati-settimanali-a-{province}-e-provincia/.
    return province_page_key(record_url)==province_page_key(source_url)==province_page_key(final_url)


def _same_place(a,b):
    return fold(a)==fold(b)


def _eligible_field(row):
    # Only a blank street qualifies for an initial assignment. Nonempty
    # values, including vague labels, require separate managed-update proof.
    return not str(row.get("indirizzo") or "").strip()


def _old_happings_encoded_slug(name):
    """Model only observed legacy WordPress loss of one non-ASCII town letter.

    Happings old /it/mercato-settimanale-a-{town}.html URLs represent a
    non-ASCII character as TWO literal dashes. Ordinary punctuation or spaces
    use one dash. Never infer a partial/nearest city from a broken URL.
    """
    value=unicodedata.normalize("NFC",name).casefold()
    return "".join(char if ("a"<=char<="z" or "0"<=char<="9") else
                   "--" if char.isalpha() else "-" for char in value)


@lru_cache(maxsize=1)
def _reviewed_old_town_slugs():
    """Cross-check lost-accent URL slug against every 2026 ISTAT town.

    A matching URL is accepted only when it resolves to precisely ONE
    municipality in the known province. The original URL and provenance
    are never rewritten or treated as a redirect.
    """
    source=trusted_municipalities(
        json.loads(MUNICIPALITIES_FILE.read_text(encoding="utf-8")))
    resolved=defaultdict(set)
    for region,places in source.items():
        for official,province in places.values():
            slug=_old_happings_encoded_slug(official)
            if "--" in slug:
                resolved[(fold(region),province,slug)].add(fold(official))
    return {key:next(iter(towns)) for key,towns in resolved.items() if len(towns)==1}


def _town_url_matches(row):
    """Recognize only the existing municipal URL family and its exact town."""
    url=row.get("url_fonte")
    if not isinstance(url,str):
        return False
    try:
        parsed=urlsplit(url)
        if (parsed.scheme!="https" or parsed.netloc!="www.happings.com"
                or parsed.query or parsed.fragment):
            return False
        match=re.fullmatch(r"/it/mercato-settimanale-a-([a-z0-9][a-z0-9-]*)\.html",parsed.path)
        if not match:
            return False
        slug=match[1]
        if fold(slug.replace("-"," "))==fold(row.get("citta")):
            return True
        if "--" not in slug:
            return False
        province=str(row.get("provincia") or "").upper()
        return (_reviewed_old_town_slugs().get(
            (fold(row.get("regione")),province,slug))==fold(row.get("citta")))
    except ValueError:
        return False


def record_matches_page(row, requested_url, final_url):
    """A municipal link is a geographic join, never an invented redirect."""
    if (row.get("fonte")!=PUBLISHER or not same_generic_venue(row)
            or not allowed_url(requested_url,requested_url,final_url)
            or not _catalog_geography_matches(row,final_url)
            or _weekly_day(row) is None):
        return False
    return (allowed_url(row.get("url_fonte"),requested_url,final_url)
            or _town_url_matches(row))


def record_matches_secondary_page(row, requested_url, final_url):
    """Potential corroboration only; an existing street must also match the HTML.

    A different primary publisher never authorizes address assignments. The
    source URL stays untouched and the secondary receipt owns no existing field.
    """
    original=row.get("url_fonte")
    return bool(row.get("fonte") and row.get("fonte")!=PUBLISHER
                and safe_url(original)
                and urlsplit(original).hostname.removeprefix("www.")!="happings.com"
                and same_generic_venue(row)
                and row.get("categoria") in (None,"","misto","alimentare")
                and safe_stored_street(row.get("indirizzo"))
                and allowed_url(requested_url,requested_url,final_url)
                and _catalog_geography_matches(row,final_url)
                and _weekly_day(row) is not None)


def _record_relation(row, requested_url, final_url):
    if record_matches_page(row,requested_url,final_url):
        return "primary"
    if record_matches_secondary_page(row,requested_url,final_url):
        return "secondary"
    return None


def catalog_page_routes(markets, *, resource_urls=()):
    """Route existing identities to catalog or independently observed resources.

    The optional URLs come from the bounded legacy resolver's validated
    receipts. They do not alter the town identity predicate or field proof.
    """
    if not isinstance(markets,list) or not 0<=len(markets)<=MAX_MARKETS:
        raise ValueError("Unbounded publisher catalog routes")
    if (not isinstance(resource_urls,(list,tuple)) or len(resource_urls)>10_000
            or any(not _valid_page_url(url) for url in resource_urls)):
        raise ValueError("Unreviewed publisher resource URLs")
    by_area=defaultdict(set)
    seen=set()
    for row in markets:
        if not isinstance(row,dict) or not isinstance(row.get("slug"),str) or not row["slug"]:
            raise ValueError("Publisher scheduling requires intact source identities")
        if row["slug"] in seen:
            raise ValueError("Repeated legacy market ID in publisher scheduling")
        seen.add(row["slug"])
        url=row.get("url_fonte")
        if (row.get("fonte")==PUBLISHER and _valid_page_url(url)
                and _catalog_geography_matches(row,url)):
            by_area[(fold(row.get("regione")),str(row.get("provincia") or "").strip().upper())].add(url)
    page_areas=_official_geography()[1]
    for url in resource_urls:
        areas=page_areas.get(province_page_key(url),set())
        if len(areas)==1:
            by_area[next(iter(areas))].add(url)
    representatives={area:min(urls,key=lambda url:(province_page_key(url),url))
                     for area,urls in by_area.items()}
    routes={}
    for row in markets:
        url=representatives.get((fold(row.get("regione")),str(row.get("provincia") or "").strip().upper()))
        if url and record_matches_page(row,url,url):
            routes[row["slug"]]=url
    return routes


def secondary_catalog_page_routes(markets):
    """Corroboration capacity using only pages already in the primary rotation.

    This is neither primary-reader coverage nor proof of an actual field match.
    No secondary card can introduce another URL or increase the fetch budget.
    """
    primary=catalog_page_routes(markets)
    pages={}
    for row in markets:
        if row["slug"] in primary:
            area=(fold(row.get("regione")),str(row.get("provincia") or "").strip().upper())
            pages[area]=primary[row["slug"]]
    routes={}
    for row in markets:
        area=(fold(row.get("regione")),str(row.get("provincia") or "").strip().upper())
        url=pages.get(area)
        if url and record_matches_secondary_page(row,url,url):
            routes[row["slug"]]=url
    return routes


def _cohort_weekly_day(row):
    """A qualified weekly market still supplies a possible venue conflict.

    Recognizing its weekday does not attest season, hours or opening state.
    Those extra claims keep the record out of automatic source assignments.
    """
    rule=explicit_rule(row.get("ricorrenza_testo"))
    if not rule or rule.get("kind")!="weekly" or len(rule.get("weekdays",[]))!=1:
        return None
    day=_unambiguous_day(row)
    return day if day==rule["weekdays"][0] else None


def _weekly_day(row):
    """Only a complete simple weekly formula can receive a source claim."""
    if temporal_scope_hold(row) or not re.fullmatch(r"(?:settimanale|ogni|tutti i) (?:lunedi|martedi|mercoledi|giovedi|venerdi|sabato|domenica)",
                        fold(row.get("ricorrenza_testo"))):
        return None
    return _cohort_weekly_day(row)


def _blocked_source_cohort(rows,source_city,weekday):
    """Any conflicting saved nonempty street makes source mapping ambiguous."""
    stored={
        fold(r.get("indirizzo"))
        for r in rows
        if fold(r.get("citta"))==source_city and _cohort_weekly_day(r)==weekday
        and safe_stored_street(r.get("indirizzo"))
    }
    return stored


def select_pages(markets, *, today=None, limit=MAX_REQUESTS_PER_RUN, resource_urls=()):
    """Stable source rotation continues after addresses have been filled."""
    today=today or date.today()
    if (not isinstance(today,date) or not isinstance(markets,list)
        or not 1<=len(markets)<=MAX_MARKETS or type(limit) is not int
        or not 1<=limit<=MAX_REQUESTS_PER_RUN):
        raise ValueError("Unbounded publisher page scheduling")
    # An observed Italian index is worth reading even if no old market exists
    # in that area. Otherwise a previously missing province never gets read.
    # Market admission remains a separate, source-evidenced decision.
    routes=catalog_page_routes(markets,resource_urls=resource_urls)
    pool=set(routes.values())
    areas=_official_geography()[1]
    for url in resource_urls:
        if _valid_page_url(url) and len(areas.get(province_page_key(url),()))==1:
            pool.add(url)
    # Use one physical page per equivalent province key. Prefer the current
    # observed -e-provincia/ variant over historic .html routes.
    by_key={}
    for url in sorted(pool,key=lambda url:(not url.endswith("-e-provincia/"),url)):
        by_key.setdefault(province_page_key(url),url)
    ranked=sorted(by_key.values(),key=lambda url:(province_page_key(url),url))
    if not ranked:
        return []
    start=(today.toordinal()*limit)%len(ranked)
    return [ranked[(start+i)%len(ranked)] for i in range(min(limit,len(ranked)))]


def _field_receipt(row, values, evidence):
    return make_receipt(
        {**row, **values}, values=values, source_url=evidence["source_url"],
        source_name=SOURCE_EVIDENCE_NAME,
        source_id="happings-weekly-"+province_page_key(evidence["source_url"]),
        source_row=province_page_key(evidence["source_url"])+":"+fold(row["citta"])+":"+str(evidence["source_day"]),
        read_on=evidence["observed_at"], source_updated_on="",
        source_sha256=evidence["source_html_sha256"], scope="pagina",
        method=("comune_provincia_giorno_univoco" if row.get("fonte")==PUBLISHER
                else "sede_giorno_provincia"), fingerprint_kind="html_bytes",
        page_metadata=evidence.get("page_metadata"))


def _version_is_ordered(row, receipt, today):
    keys=("fonte_id","url","riga_fonte","metodo","ambito","impronta_tipo")
    prior=[r for r in clean_receipts(row.get("riscontri_campi"),row,today=today)
           if all(r.get(k)==receipt.get(k) for k in keys)]
    return not any(r["letto_il"]>receipt["letto_il"] or
                   (r["letto_il"]==receipt["letto_il"] and r["sha256"]!=receipt["sha256"]) or
                   bool(r.get("fonte_aggiornata_il")) for r in prior)


def _retirement_change(before, proof, *, today):
    prior=clean_receipts(before.get("riscontri_campi"),before,today=today)
    kept=retire_superseded_receipts(before,proof,today=today)
    provenance=("fonte_id","url","riga_fonte","metodo","ambito","impronta_tipo")
    retired=[receipt for receipt in prior if "indirizzo" in receipt["valori"]
             and not any(all(receipt.get(key)==current.get(key) for key in provenance)
                         and current["valori"].get("indirizzo")==receipt["valori"]["indirizzo"]
                         for current in kept)]
    return kept,retired


def _retirement_for(before, evidence, *, today):
    """A new unique source row may disprove its old claim without changing data."""
    if _same_place(before.get("indirizzo"),evidence["source_value"]):
        return None
    values={"indirizzo":evidence["source_value"]}
    proof=_field_receipt(before,values,evidence)
    if not _version_is_ordered(before,proof,today):
        return None
    _,retired=_retirement_change(before,proof,today=today)
    if not retired:
        return None
    return {**evidence,"values":values,"source_proof":proof,
            "retired_fields":["indirizzo"],"retired_receipts":retired}


def expected_record(before, proposal=None, observation=None, *, today, retirement=None, address_conflict=None):
    """Reconstruct exact permitted fields and receipts for the release guard."""
    if address_conflict is not None:
        if proposal is not None or observation is not None:
            raise ValueError("A contradictory address cannot also acquire positive support")
        from happings_weekly_conflicts import apply_conflict
        previous=expected_record(before,today=today,retirement=retirement)
        return apply_conflict(previous,address_conflict,today=today)
    result=deepcopy(before)
    if retirement is not None:
        if (proposal is not None or observation is not None
                or retirement.get("market_id")!=before.get("slug")
                or retirement.get("source_relation")!=_record_relation(
                    before,retirement.get("source_requested_url"),retirement.get("source_url"))
                or retirement.get("source_relation") not in {"primary","secondary"}
                or retirement.get("source_day")!=_weekly_day(before)
                or retirement.get("observed_at")!=today.isoformat()
                or not safe_stored_street(retirement.get("source_value"))
                or type(retirement.get("apply_authorized")) is not bool
                or type(retirement.get("rights_gate_passed")) is not bool
                or (retirement["apply_authorized"] and not retirement["rights_gate_passed"])):
            raise ValueError("Source retirement lost its exact identity or authorization")
        expected=_retirement_for(before,retirement,today=today)
        if expected is None or expected!=retirement:
            raise ValueError("Source retirement has no exact later contradictory receipt")
        if retirement["apply_authorized"]:
            result["riscontri_campi"]=_retirement_change(before,retirement["source_proof"],today=today)[0]
        return result
    if observation is None:
        if proposal is not None:
            raise ValueError("Address proposal has no persistent source observation")
        return result
    values=observation.get("values")
    relation=_record_relation(before,observation.get("source_requested_url"),observation.get("source_url"))
    if (not isinstance(values,dict) or set(values)!={"indirizzo","ricorrenza_testo"}
            or values["ricorrenza_testo"]!=before.get("ricorrenza_testo")
            or not safe_stored_street(values.get("indirizzo"))
            or not _same_place(values["indirizzo"],observation.get("source_value"))
            or relation not in {"primary","secondary"} or observation.get("source_relation")!=relation
            or observation.get("market_id")!=before.get("slug")
            or observation.get("source_day")!=_weekly_day(before)
            or observation.get("observed_at")!=today.isoformat()
            or type(observation.get("apply_authorized")) is not bool
            or type(observation.get("rights_gate_passed")) is not bool
            or (observation["apply_authorized"] and not observation["rights_gate_passed"])):
        raise ValueError("Source observation lost its exact identity or values")
    if relation=="secondary" and (proposal is not None or values["indirizzo"]!=before.get("indirizzo")):
        raise ValueError("A secondary source cannot assign or own an existing market field")
    plain=_field_receipt(before,values,observation)
    if not _version_is_ordered(before,plain,today):
        raise ValueError("Publisher source version ordering is unproven")
    proof=plain
    if proposal is None:
        if values["indirizzo"]!=before.get("indirizzo"):
            raise ValueError("Observation cannot assign a field without a proposal")
    else:
        if (proposal.get("market_id")!=before["slug"] or proposal.get("field")!="indirizzo"
                or proposal.get("candidate_value")!=values["indirizzo"]
                or proposal.get("old_value")!=str(before.get("indirizzo") or "")
                or values["indirizzo"]==before.get("indirizzo")
                or any(proposal.get(k)!=observation.get(k) for k in (
                    "source_url","source_requested_url","source_html_sha256","source_city",
                    "source_province","source_region","source_day","observed_at",
                    "source_relation","apply_authorized","rights_gate_passed"))
                or before.get("verificato_il") or before.get("position_quality")=="precisa"):
            raise ValueError("Unapproved publisher address assignment")
        initial=_eligible_field(before)
        if proposal.get("assignment")!=("initial" if initial else "managed_update"):
            raise ValueError("Publisher address assignment type changed")
        if not initial and not managed_update_allowed(before,plain,"indirizzo",manager=FIELD_MANAGER,today=today):
            raise ValueError("Publisher cannot overwrite an unowned or contradicted address")
        proof=mark_managed_fields(plain,["indirizzo"],manager=FIELD_MANAGER,previous=before)
    if observation.get("source_proof")!=proof:
        raise ValueError("Publisher field receipt differs from its exact observed values")
    if not observation["apply_authorized"]:
        return result
    result["indirizzo"]=values["indirizzo"]
    kept=retire_superseded_receipts(before,plain,today=today)
    result["riscontri_campi"]=clean_receipts([*kept,proof],result,today=today)
    links=deepcopy(before.get("fonti") or [])
    if not isinstance(links,list) or any(not isinstance(x,dict) for x in links):
        raise ValueError("Publisher source list is invalid")
    added={"nome":SOURCE_EVIDENCE_NAME,"url":observation["source_url"]}
    if added not in links:
        links.append(added)
    result["fonti"]=links
    return result


def preview(base, pages, *, today=None, apply=False, rights_verified=False):
    """Observe compatible fields and refresh only this engine's assignments."""
    today=today or date.today()
    if (not isinstance(today,date) or not isinstance(base,list)
            or not 1<=len(base)<=MAX_MARKETS or not isinstance(pages,list)
            or len(pages)>MAX_REQUESTS_PER_RUN or type(apply) is not bool
            or type(rights_verified) is not bool):
        raise ValueError("Invalid publisher source batch")
    if apply and rights_verified is not True:
        raise ValueError("Cannot write publisher fields without reviewed rights or project authorization")
    ids=[r.get("slug") if isinstance(r,dict) else None for r in base]
    if any(not isinstance(sid,str) or not sid for sid in ids) or len(set(ids))!=len(ids):
        raise ValueError("Missing or duplicate original market ID")
    proposals=[]
    observations=[]
    retirements=[]
    counters=Counter()
    seen_page=set()
    page_results=[]
    coverage_inputs=[]
    editorial_documents=[]
    secondary_routes=secondary_catalog_page_routes(base) if pages else {}
    for page in pages:
        if not isinstance(page,dict):
            raise ValueError("Invalid publisher page evidence")
        requested,final,blob=(page.get(k) for k in ("requested_url","final_url","html"))
        if (not allowed_url(requested,requested,final)
                or province_page_key(requested) in seen_page):
            raise ValueError("Out-of-scope or repeated source page")
        seen_page.add(province_page_key(requested))
        if not isinstance(blob,bytes) or not 300<=len(blob)<=MAX_RESPONSE_BYTES:
            raise ValueError("Missing or unbounded reviewed weekly-index HTML")
        page_receipt={"requested_url":requested,"final_url":final,
                      "source_html_sha256":hashlib.sha256(blob).hexdigest()}
        try:
            parser=parse(blob,source_url=final,observed_on=today)
        except ValueError:
            counters["source_pages_layout_changed"]+=1
            page_results.append({**page_receipt,"status":"layout_changed"})
            coverage_inputs.append((page,None,[],{}))
            continue
        if parser.page_metadata is not None:
            page_receipt["page_metadata"]=parser.page_metadata
        if getattr(parser,"editorial_sections",None):
            from happings_weekly_conflicts import document_for
            editorial_documents.append(document_for(page,parser))
            page_receipt["editorial_sections"]=deepcopy(parser.editorial_sections)
            counters["publisher_editorial_current_rows"]+=sum(
                item["source_rows"] for item in parser.editorial_sections if item["status"]=="current")
            counters["publisher_editorial_historical_rows"]+=sum(
                item["source_rows"] for item in parser.editorial_sections if item["status"]=="historical_unverified")
            counters["publisher_editorial_unverified_rows"]+=sum(
                item["source_rows"] for item in parser.editorial_sections if item["status"]=="unverified")
        page_results.append({**page_receipt,"status":"parsed","source_rows":len(parser.rows)})
        source=defaultdict(list)
        for entry in parser.rows:
            source[(entry["city_key"],entry["weekday"])].append(entry)
        counters["html_market_rows"]+=len(parser.rows)
        matched=[r for r in base if r.get("fonte")==PUBLISHER and same_generic_venue(r)
                 and (allowed_url(r.get("url_fonte"),requested,final) or
                      (_town_url_matches(r) and _catalog_geography_matches(r,final)))]
        matched.extend(r for r in base if r["slug"] in secondary_routes
                       and allowed_url(secondary_routes[r["slug"]],requested,final))
        coverage_holds=defaultdict(list)
        coverage_inputs.append((page,parser,[r["slug"] for r in matched],coverage_holds))
        # A competing ordinary weekly venue remains a collision regardless
        # of where its existing address or qualified calendar came from.
        cohort=[r for r in base if same_generic_venue(r)
                and _catalog_geography_matches(r,final)]
        groups=defaultdict(list)
        for record in matched:
            if not _catalog_geography_matches(record,final):
                counters["identity_geography_unproven"]+=1
                continue
            day=_weekly_day(record)
            if day is None:
                counters["identity_weekday_unproven"]+=1
                continue
            groups[(fold(record.get("citta")),day)].append(record)
        for pair,matching_rows in groups.items():
            entries=source.get(pair,[])
            if len(entries)!=1:
                counters["no_unique_source_market_city_weekday"]+=len(matching_rows)
                coverage_holds[pair].append("no_unique_source_market_city_weekday")
                continue
            if entries[0].get("calendar_scope"):
                scope=(entries[0].get("editorial_scope") or {}).get("status")
                reason=("publisher_historical_section_held" if scope=="historical_unverified"
                        else "publisher_unverified_section_held" if scope=="unverified"
                        else "publisher_calendar_scope_unrepresented")
                counters[reason]+=len(matching_rows)
                coverage_holds[pair].append(reason)
                continue
            street=entries[0]["place"].strip()
            if entries[0].get("has_specific_location") is not True or not safe_stored_street(street):
                counters["publisher_only_vague_or_area_location"]+=len(matching_rows)
                coverage_holds[pair].append("publisher_only_vague_or_area_location")
                continue
            def evidence_for(row):
                return {
                    "market_id":row["slug"],"source_url":final,"source_requested_url":requested,
                    "source_html_sha256":page_receipt["source_html_sha256"],
                    **({"page_metadata":page_receipt["page_metadata"]}
                       if "page_metadata" in page_receipt else {}),
                    "source_city":row["citta"],"source_province":row["provincia"],
                    "source_region":row["regione"],"source_day":pair[1],
                    "source_value":street,"observed_at":today.isoformat(),
                    "source_relation":"primary" if row.get("fonte")==PUBLISHER else "secondary",
                    "evidence_method":("secondary_exact_existing_street_province_city_weekday"
                        if row.get("fonte")!=PUBLISHER else
                        "publisher_weekday_index_unique_city_and_day_no_conflicting_street"
                        if allowed_url(row.get("url_fonte"),requested,final)
                        else "town_link_same_province_city_weekday"),
                    "individually_confirmed":False,"published_opening_verified":False,
                    "coordinate_added":False,"rights_gate_passed":bool(rights_verified),
                    "apply_authorized":bool(apply and rights_verified),
                }
            conflicting=False
            for existing in cohort:
                if (fold(existing.get("citta"))!=pair[0] or _cohort_weekly_day(existing)!=pair[1]
                        or not safe_stored_street(existing.get("indirizzo"))
                        or _same_place(existing["indirizzo"],street)):
                    continue
                proof=_field_receipt(existing,{"indirizzo":street},evidence_for(existing))
                if (not record_matches_page(existing,requested,final)
                        or existing.get("position_quality")=="precisa"
                        or not managed_update_allowed(existing,proof,"indirizzo",manager=FIELD_MANAGER,today=today)):
                    conflicting=True
                    break
            if conflicting:
                counters["conflicting_previously_saved_location"]+=len(matching_rows)
                coverage_holds[pair].append("conflicting_previously_saved_location")
            for row in matching_rows:
                common=evidence_for(row)
                current=str(row.get("indirizzo") or "")
                if conflicting or (common["source_relation"]=="secondary" and not _same_place(current,street)):
                    retirement=_retirement_for(row,common,today=today)
                    if retirement is not None:
                        retirements.append(retirement)
                    if not conflicting:
                        counters["secondary_existing_street_disagrees"]+=1
                        coverage_holds[pair].append("secondary_existing_street_disagrees")
                    continue
                value=current if _same_place(current,street) else street
                values={"indirizzo":value,"ricorrenza_testo":row["ricorrenza_testo"]}
                plain=_field_receipt(row,values,common)
                if not _version_is_ordered(row,plain,today):
                    counters["source_version_ordering_not_proven"]+=1
                    coverage_holds[pair].append("source_version_ordering_not_proven")
                    continue
                proposal=None
                proof=plain
                if value!=current:
                    initial=_eligible_field(row)
                    managed=managed_update_allowed(row,plain,"indirizzo",manager=FIELD_MANAGER,today=today)
                    if (row.get("verificato_il") or row.get("position_quality")=="precisa"
                            or not (initial or managed)):
                        counters["already_has_street_or_vague_original"]+=1
                        coverage_holds[pair].append("already_has_street_or_vague_original")
                        continue
                    proposal={**common,"field":"indirizzo","old_value":current,
                              "candidate_value":value,"assignment":"initial" if initial else "managed_update"}
                    proof=mark_managed_fields(plain,["indirizzo"],manager=FIELD_MANAGER,previous=row)
                    proposals.append(proposal)
                observation={**common,"values":values,"source_proof":proof}
                observations.append(observation)
    if len(proposals)>MAX_UPDATES_PER_RUN:
        raise ValueError("Too many publisher-field mutations per run")
    if len({p["market_id"] for p in observations})!=len(observations):
        raise ValueError("Overlapping source pages proposed conflicting target IDs")
    by_proposal={p["market_id"]:p for p in proposals}
    by_observation={p["market_id"]:p for p in observations}
    by_retirement={p["market_id"]:p for p in retirements}
    if len(by_retirement)!=len(retirements) or set(by_retirement)&set(by_observation):
        raise ValueError("Overlapping source pages mixed observations and retirements")
    from happings_weekly_conflicts import propose as propose_address_conflicts, verify_source_pages
    verify_source_pages(editorial_documents,pages,today=today)
    address_conflicts=propose_address_conflicts(base,editorial_documents,today=today,
        apply_authorized=bool(apply and rights_verified),rights_gate_passed=bool(rights_verified))
    by_conflict={item["market_id"]:item for item in address_conflicts}
    if set(by_conflict)&(set(by_proposal)|set(by_observation)):
        raise ValueError("Address conflict overlaps a positive Happings assignment")
    updated=[expected_record(r,by_proposal.get(r["slug"]),by_observation.get(r["slug"]),today=today,
                             retirement=by_retirement.get(r["slug"]),address_conflict=by_conflict.get(r["slug"])) for r in base]
    address_changes=sorted(r["slug"] for r,n in zip(base,updated) if r.get("indirizzo")!=n.get("indirizzo"))
    report={
        "schema":SCHEMA,"date":today.isoformat(),"publisher":PUBLISHER,
        "pages_evaluated":len(pages),"source_pages":page_results,
        "market_ids_before":len(base),"market_ids_after":len(updated),
        "parser_counts":dict(sorted(counters.items())),
        "field_candidates":len(proposals),"field_changes":len(address_changes),
        "proposals":proposals,"changed_ids":address_changes,
        "observations":observations,
        "observed_ids":sorted(o["market_id"] for o in observations if o["apply_authorized"]),
        "secondary_observed_ids":sorted(o["market_id"] for o in observations
                                        if o["apply_authorized"] and o["source_relation"]=="secondary"),
        "retirements":retirements,
        "retired_ids":sorted(o["market_id"] for o in retirements if o["apply_authorized"]),
        "record_changes":sum(r!=n for r,n in zip(base,updated)),
        "editorial_documents":editorial_documents,
        "editorial_apply_authorized":bool(apply and rights_verified),
        "editorial_rights_gate_passed":bool(rights_verified),
        "address_conflicts":address_conflicts,
        "address_conflict_ids":sorted(item["market_id"] for item in address_conflicts if item["apply_authorized"]),
        "source_copyright_copying_not_required":True,
        "market_rows_deleted":0,"market_rows_inserted":0,
        "market_openings_verified":0,"new_geographic_points":0,"source_primary_links_replaced":0,
    }
    from happings_field_coverage import aggregate_coverage, weekly_page_coverage
    coverage_before={row["slug"]:row for row in base}
    coverage_after={row["slug"]:row for row in updated}
    report["field_coverage"]=aggregate_coverage([
        weekly_page_coverage(page["html"],parsed,requested_url=page["requested_url"],final_url=page["final_url"],
            observations=observations,considered_ids=considered,holds=holds,
            before=coverage_before,after=coverage_after)
        for page,parsed,considered,holds in coverage_inputs])
    return updated,report


def fetch_pages(urls, *, permission_confirmed=False,
                robots_fetch=_fetch_one, page_fetch=_fetch_one,
                sleep=time.sleep, failures=None, robots=None):
    if permission_confirmed is not True:
        raise ValueError("No automated fetch without active project authorization")
    if not isinstance(urls,list) or not 1<=len(urls)<=MAX_REQUESTS_PER_RUN:
        raise ValueError("Publisher requests exceed max pages per run")
    if (any(not _valid_page_url(u) for u in urls)
            or len({province_page_key(u) for u in urls})!=len(urls)):
        raise ValueError("Publisher URL not from an approved weekly-index family")
    if failures is not None and (not isinstance(failures,list) or failures):
        raise ValueError("Publisher page failures must start as an empty list")
    robots=robots_allowed(robots_fetch) if robots is None else robots
    delay=_request_pause(robots)
    result=[]
    for i,url in enumerate(urls):
        try:
            if not robots.can_fetch(USER_AGENT,url):
                raise ValueError("Publisher robots policy denied requested weekly index")
            sleep(delay)
            raw,canonical=page_fetch(url,robots=robots)
            if not allowed_url(url,url,canonical):
                raise ValueError("Publisher redirected to a different market region")
            if not robots.can_fetch(USER_AGENT,canonical):
                raise ValueError("Publisher robots policy denied redirected weekly index")
            if not isinstance(raw,bytes) or not 300<=len(raw)<=MAX_RESPONSE_BYTES:
                raise ValueError("Publisher response exceeds bounded source page size")
            result.append({"requested_url":url,"final_url":canonical,"html":raw})
        except (OSError,HTTPError,HTTPException,ValueError) as error:
            if failures is None:
                raise
            failures.append({"requested_url":url,"error_type":type(error).__name__,
                             "error_code":failure_code(error)})
    return result


def safe_report(report,base,*,source_pages=None):
    if (report.get("schema")!=SCHEMA or report.get("market_ids_before")!=len(base)
            or report.get("market_ids_after")!=len(base)
            or report.get("field_changes")!=len(report.get("changed_ids",[]))
            or report.get("field_candidates")!=len(report.get("proposals",[]))
            or any(report.get(k)!=0 for k in (
                "market_rows_deleted","market_rows_inserted","market_openings_verified",
                "new_geographic_points","source_primary_links_replaced"))):
        raise ValueError("Publisher data release exceeded allowed source fields")
    try:
        today=date.fromisoformat(report["date"])
    except (ValueError,TypeError,KeyError):
        raise ValueError("Invalid publisher observation date") from None
    by_id={row["slug"]:row for row in base}
    proposals=report.get("proposals",[])
    observations=report.get("observations",[])
    retirements=report.get("retirements",[])
    address_conflicts=report.get("address_conflicts",[])
    page_receipts=report.get("source_pages",[])
    if (not isinstance(proposals,list) or not isinstance(observations,list) or not isinstance(retirements,list)
            or not isinstance(address_conflicts,list)
            or len(by_id)!=len(base) or len(page_receipts)!=report.get("pages_evaluated")
            or len(page_receipts)>MAX_REQUESTS_PER_RUN or len(proposals)>MAX_UPDATES_PER_RUN
            or any(not isinstance(p,dict) for p in [*proposals,*observations,*retirements,*address_conflicts])
            or len({p.get("market_id") for p in proposals})!=len(proposals)
            or len({p.get("market_id") for p in observations})!=len(observations)
            or len({p.get("market_id") for p in retirements})!=len(retirements)
            or len({p.get("market_id") for p in address_conflicts})!=len(address_conflicts)):
        raise ValueError("Publisher report has repeated or missing evidence identities")
    observed_pages={}
    seen_provinces=set()
    for page in page_receipts:
        key=(page.get("requested_url"),page.get("final_url"))
        digest=page.get("source_html_sha256")
        if (not allowed_url(key[0],key[0],key[1]) or key in observed_pages
                or province_page_key(key[0]) in seen_provinces
                or not isinstance(digest,str) or not re.fullmatch(r"[0-9a-f]{64}",digest)
                or page.get("status") not in {"parsed","layout_changed"}):
            raise ValueError("Publisher report has invalid source page evidence")
        if ("page_metadata" in page and clean_page_metadata(
                page["page_metadata"],final_url=key[1],read_on=today) is None):
            raise ValueError("Publisher page editorial metadata lost its exact scope")
        observed_pages[key]=page
        seen_provinces.add(province_page_key(key[0]))
    secondary_routes=(secondary_catalog_page_routes(base) if any(
        item.get("source_relation")=="secondary" for item in [*observations,*retirements]) else {})
    from happings_weekly_conflicts import propose as propose_address_conflicts
    documents=report.get("editorial_documents",[])
    if (not isinstance(documents,list) or len(documents)>len(observed_pages)
            or any(not isinstance(document,dict) for document in documents)
            or len({(document.get("requested_url"),document.get("final_url"))
                    for document in documents})!=len(documents)):
        raise ValueError("Editorial source documents are repeated or unbounded")
    if documents:
        from happings_weekly_conflicts import verify_source_pages
        if not isinstance(source_pages,list) or not 1<=len(source_pages)<=MAX_REQUESTS_PER_RUN:
            raise ValueError("Editorial field warnings require their captured source pages at the release guard")
        verify_source_pages(documents,source_pages,today=today)
    for document in documents:
        source=observed_pages.get((document.get("requested_url"),document.get("final_url")))
        if (source is None or source["status"]!="parsed"
                or document.get("source_html_sha256")!=source["source_html_sha256"]
                or document.get("editorial_sections")!=source.get("editorial_sections")
                or document.get("page_metadata")!=source.get("page_metadata")):
            raise ValueError("Editorial conflict document lost its exact observed page")
    expected_conflicts=propose_address_conflicts(base,documents,today=today,
        apply_authorized=report.get("editorial_apply_authorized",False),
        rights_gate_passed=report.get("editorial_rights_gate_passed",False))
    if expected_conflicts!=address_conflicts:
        raise ValueError("Address conflicts differ from exact unique source replacements")
    for item in [*proposals,*observations,*retirements,*address_conflicts]:
        target=by_id.get(item.get("market_id"))
        source=observed_pages.get((item.get("source_requested_url"),item.get("source_url")))
        if (item.get("individually_confirmed") is not False
                or item.get("published_opening_verified") is not False or item.get("coordinate_added") is not False):
            raise ValueError("Publisher proposal falsely claims a checked opening")
        if (not target or not source or source["status"]!="parsed"
                or _record_relation(target,item.get("source_requested_url"),item.get("source_url")) not in {"primary","secondary"}
                or item.get("source_relation")!=_record_relation(
                    target,item.get("source_requested_url"),item.get("source_url"))
                or (item["source_relation"]=="secondary" and not allowed_url(
                    secondary_routes.get(target["slug"]),item.get("source_requested_url"),item.get("source_url")))
                or item.get("source_html_sha256")!=source["source_html_sha256"]
                or item.get("page_metadata")!=source.get("page_metadata")
                or item.get("source_city")!=target.get("citta")
                or item.get("source_province")!=target.get("provincia")
                or item.get("source_region")!=target.get("regione")
                or item.get("source_day")!=_weekly_day(target)
                or item.get("observed_at")!=report["date"]
                or not safe_stored_street(item.get("source_value"))):
            raise ValueError("Publisher proposal lost its exact source and target evidence")
    by_proposal={p["market_id"]:p for p in proposals}
    by_observation={p["market_id"]:p for p in observations}
    by_retirement={p["market_id"]:p for p in retirements}
    by_conflict={p["market_id"]:p for p in address_conflicts}
    if (not set(by_proposal)<=set(by_observation) or set(by_retirement)&set(by_observation)
            or set(by_conflict)&(set(by_proposal)|set(by_observation))):
        raise ValueError("Publisher address proposal has no source observation")
    address_changes=[]
    changed=[]
    for sid in set(by_observation)|set(by_proposal)|set(by_retirement)|set(by_conflict):
        original=by_id[sid]
        expected=expected_record(original,by_proposal.get(sid),by_observation.get(sid),today=today,
                                 retirement=by_retirement.get(sid),address_conflict=by_conflict.get(sid))
        if expected!=original:
            changed.append(sid)
        if original.get("indirizzo")!=expected.get("indirizzo"):
            address_changes.append(sid)
    if (sorted(address_changes)!=report["changed_ids"]
            or len(changed)!=report.get("record_changes")
            or sorted(o["market_id"] for o in observations if o["apply_authorized"])!=report.get("observed_ids")
            or sorted(o["market_id"] for o in observations
                      if o["apply_authorized"] and o["source_relation"]=="secondary")!=report.get("secondary_observed_ids")
            or sorted(o["market_id"] for o in retirements if o["apply_authorized"])!=report.get("retired_ids")):
        raise ValueError("Publisher changes do not match explicitly authorized proposals")
    if sorted(item["market_id"] for item in address_conflicts if item["apply_authorized"])!=report.get("address_conflict_ids",[]):
        raise ValueError("Publisher negative evidence lost its applied identities")
    return True


def summarize(report):
    return {
        "schema":1,"date":report["date"],
        "publisher":PUBLISHER,
        "pages_evaluated":report["pages_evaluated"],
        "market_ids_preserved":report["market_ids_before"],
        "field_candidates":report["field_candidates"],
        "field_changes":report["field_changes"],
        "parser_counts":report["parser_counts"],
        "source_pages":report.get("source_pages",[]),
        "field_coverage":report.get("field_coverage"),
        "verified_market_openings_created":0,
        "geocoded_market_locations_created":0,
        "unapproved_publisher_field_overwrites":0,
        "max_pages_per_run":MAX_REQUESTS_PER_RUN,
        "observed_markets":len(report.get("observed_ids",[])),
        "secondary_observed_markets":len(report.get("secondary_observed_ids",[])),
        "retired_source_support_markets":len(report.get("retired_ids",[])),
        "record_changes":report.get("record_changes",0),
        "calendar_content_dates_inferred":0,
    }


def offline_pages(source_urls, input_html_paths, final_urls=None):
    """Replay real source HTML from disk with its observed canonical redirect.

    The crawler writes no HTML to Git. This also makes a one-off, licensed
    publisher sample reproducible without falsely pretending old .html URLs
    are still the canonical source page.
    """
    if (not isinstance(source_urls,list) or not isinstance(input_html_paths,list)
        or not 1<=len(source_urls)<=MAX_REQUESTS_PER_RUN
        or len(source_urls)!=len(input_html_paths)
        or (final_urls is not None and (
            not isinstance(final_urls,list) or len(final_urls)!=len(source_urls)))):
        raise ValueError("Offline publisher sample URLs and files must align")
    pages=[]
    for i,(original,filepath) in enumerate(zip(source_urls,input_html_paths)):
        final=final_urls[i] if final_urls is not None else original
        if not allowed_url(original,original,final):
            raise ValueError("Offline publisher sample redirect crossed province or layout")
        source=Path(filepath).read_bytes()
        if not 300<=len(source)<=MAX_RESPONSE_BYTES:
            raise ValueError("Offline publisher sample exceeds bounded page size")
        pages.append({"requested_url":original,"final_url":final,"html":source})
    return pages


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",type=Path,default=Path("public/data/v1/manifest.json"))
    ap.add_argument("--input-html",action="append",type=Path,
                    help="Approved source HTML fixture, no external requests")
    ap.add_argument("--source-url",action="append",help="Original Happings provincial URL")
    ap.add_argument("--source-final-url",action="append",
                    help="Observed same-province HTTPS canonical URL for an offline HTML sample")
    ap.add_argument("--auto-select",action="store_true",
                    help="Rotate over the source URLs already in the saved market catalog")
    ap.add_argument("--live",action="store_true",help="Use the bounded, authorized robots-aware source reader")
    ap.add_argument("--permission-confirmed",action="store_true",
                    help="Legacy option; authorization comes from the recorded project instruction")
    ap.add_argument("--apply",action="store_true",help="Propose field-only changes; never auto-publish")
    ap.add_argument("--today",type=date.fromisoformat,default=date.today())
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--summary",type=Path,required=True)
    ap.add_argument("--candidate-markets",type=Path)
    args=ap.parse_args()
    rights_record=json.loads(RIGHTS_REVIEW_FILE.read_text("utf-8"))
    authorization=authorization_status(rights_record,today=args.today)
    if (args.live or args.apply) and not authorization["authorized"]:
        raise ValueError("Publisher extraction has no active project authorization")
    original=load_existing(args.manifest)
    if args.auto_select:
        if args.source_url:
            raise ValueError("Choose manual pages OR reproducible source-level rotation")
        args.source_url=select_pages(original,today=args.today)
    if not args.source_url or len(args.source_url)>MAX_REQUESTS_PER_RUN:
        raise ValueError("Select 1-16 reviewed province pages")
    if args.live and (args.input_html or args.source_final_url):
        raise ValueError("Cannot mix live fetching and manually reviewed source HTML/redirects")
    if args.live:
        pages=fetch_pages(args.source_url,permission_confirmed=authorization["authorized"])
    else:
        pages=offline_pages(args.source_url,args.input_html,args.source_final_url)
    result,report=preview(original,pages,today=args.today,apply=args.apply,
                          rights_verified=authorization["authorized"])
    safe_report(report,original,source_pages=pages)
    for f in (args.out,args.summary,args.candidate_markets):
        if f is not None:f.parent.mkdir(parents=True,exist_ok=True)
    # Raw pages and the detailed comparison stay in temporary checkpoints.
    # Compact field receipts persist with the catalog for later refreshes.
    args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n","utf-8")
    args.summary.write_text(json.dumps(summarize(report),indent=2,ensure_ascii=False)+"\n","utf-8")
    if args.candidate_markets:
        args.candidate_markets.write_text(json.dumps(result,ensure_ascii=False)+"\n","utf-8")
    print(json.dumps(summarize(report),ensure_ascii=False))


if __name__=="__main__":
    main()
