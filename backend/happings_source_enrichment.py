#!/usr/bin/env python3
"""Publisher-specific Happings market-field repair with strict provenance.

A Happings index is a town + weekday + market-area directory, NOT an exact
time schedule or individually confirmed weekly opening. Parse once per
publisher layout, compare with existing source-URL-scoped identities, and
fill only blank addresses after a unique source row AND no catalog conflict.

Default mode is a no-write read-only field audit. Live HTTP is opt-in,
budgeted, robots-aware, and denied unless rights verification is explicitly
enabled. User-provided PDFs aren't stored in this repository. The uploaded
examples have no cryptographic PDF signature, so they aren't themselves a
machine-verifiable authorization token; see docs/HAPPINGS_RIGHTS_REVIEW.md.
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
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser

from happings_weekly_layout import parse, fold, _valid_page_url
from stored_market_sibling_proposals import same_generic_venue, safe_stored_street
from source_reconciliation_audit import _unambiguous_day
from merge_catalog import load_existing

SCHEMA=1
PUBLISHER="happings.com"
ROBOTS="https://www.happings.com/robots.txt"
MAX_REQUESTS_PER_RUN=2
MAX_RESPONSE_BYTES=2_600_000
MAX_MARKETS=100_000
MAX_UPDATES_PER_RUN=200
MIN_REQUEST_PAUSE_SECONDS=3
USER_AGENT="MercatiItaliaMarketFields/1.0 (+https://github.com/tommyv-spec/mercati-italia)"
SOURCE_EVIDENCE_NAME="Happings — elenco settimanale (sede indicativa; apertura non verificata)"
SOURCE_ALLOWED_PATH=re.compile(
    r"/it/mercati-settimanali-a-[a-z0-9-]+(?:\.html|/)$"
)

class GuardedRedirects(HTTPRedirectHandler):
    def __init__(self, expected):
        super().__init__()
        self.expected=expected
        self.hops=0

    def redirect_request(self, request, fp, code, msg, headers, newurl):
        self.hops+=1
        if self.hops>2 or not _valid_page_url(newurl):
            raise ValueError("Source redirect left reviewed Happings province layout")
        # Only province-specific old .html --> canonical -e-provincia/
        # changes from the same company. Never read an arbitrary path.
        if self.expected.split(".html")[0].split("-e-provincia/")[0] not in (
            newurl.split(".html")[0].split("-e-provincia/")[0],
        ):
            raise ValueError("Publisher redirect crossed province")
        return super().redirect_request(request,fp,code,msg,headers,newurl)


def _public_dns(host):
    for addr in socket.getaddrinfo(host,443,type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(addr[4][0]).is_global:
            raise ValueError("Publisher hostname resolved to private address")


def _fetch_one(url, *, opener=None, limit=MAX_RESPONSE_BYTES):
    if not _valid_page_url(url) and url!=ROBOTS:
        raise ValueError("Unapproved publisher URL")
    _public_dns("www.happings.com")
    request=Request(url,headers={
        "User-Agent":USER_AGENT,
        "Accept":"text/plain" if url==ROBOTS else "text/html",
        "Accept-Encoding":"identity",
    })
    opener=opener or build_opener(GuardedRedirects(url))
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
    except (OSError,HTTPError):
        raise ValueError("Publisher robots unavailable: no automatic fetching") from None
    if len(raw)>55_000 or len(raw)<12:
        raise ValueError("Untrusted robots response")
    text=raw.decode("utf-8-sig","replace")
    if "user-agent:" not in text.lower():
        raise ValueError("Publisher robots has no policy")
    robot=RobotFileParser()
    robot.parse(text.splitlines())
    return robot


def allowed_url(record_url,source_url,final_url):
    """Exact old URL/canonical pair, never unreviewed other publisher pages."""
    if record_url==source_url:
        return True
    if record_url==final_url:
        return True
    for p in (record_url,source_url,final_url):
        if not _valid_page_url(p):
            return False
    # Convert old .../mercati-settimanali-a-{province}.html to
    # current .../mercati-settimanali-a-{province}-e-provincia/.
    def base(s):
        path=urlsplit(s).path
        return re.sub(r"(?:-e-provincia/|\.html)$","",path)
    return base(record_url)==base(source_url)==base(final_url)


def _same_place(a,b):
    return fold(a)==fold(b)


def _eligible_field(row):
    # Never replace a specific street by scraped text. For the first release
    # don't even replace "centro" -- it is a currently visible source claim.
    return not str(row.get("indirizzo") or "").strip()


def _blocked_source_cohort(rows,source_city,weekday):
    """Any conflicting saved nonempty street makes source mapping ambiguous."""
    stored={
        fold(r.get("indirizzo"))
        for r in rows
        if fold(r.get("citta"))==source_city and _unambiguous_day(r)==weekday
        and safe_stored_street(r.get("indirizzo"))
    }
    return stored


def preview(base, pages, *, today=None, apply=False, rights_verified=False):
    """Preview or apply strictly bounded proven location fields.

    pages: list of {"requested_url", "final_url", "html": bytes}.
    The HTML must come from previously permitted requests. The algorithm
    never downloads anything itself and never changes IDs/date/GPS/status.
    """
    today=today or date.today()
    if (not isinstance(today,date) or not isinstance(base,list)
        or not 1<=len(base)<=MAX_MARKETS or not isinstance(pages,list)
        or len(pages)>MAX_REQUESTS_PER_RUN or type(apply) is not bool):
        raise ValueError("Invalid publisher source batch")
    if apply and rights_verified is not True:
        raise ValueError("Cannot write publisher fields without reviewed rights")
    frozen=deepcopy(base)
    ids=set()
    for row in base:
        sid=row.get("slug") if isinstance(row,dict) else None
        if not isinstance(sid,str) or not sid or sid in ids:
            raise ValueError("Missing or duplicate original market ID")
        ids.add(sid)

    proposals=[]
    counters=Counter()
    seen_page=set()
    for page in pages:
        requested=page.get("requested_url")
        final=page.get("final_url")
        blob=page.get("html")
        if (not _valid_page_url(requested) or not _valid_page_url(final)
            or requested in seen_page or not allowed_url(requested,requested,final)):
            raise ValueError("Out-of-scope or repeated source page")
        seen_page.add(requested)
        parser=parse(blob,source_url=final)
        source=defaultdict(list)
        for entry in parser.rows:
            source[(entry["city_key"],entry["weekday"])].append(entry)
        counters["html_market_rows"]+=len(parser.rows)
        matched=[
            r for r in base if r.get("fonte")==PUBLISHER and
            same_generic_venue(r) and
            allowed_url(r.get("url_fonte"),requested,final)
        ]
        groups=defaultdict(list)
        for record in matched:
            day=_unambiguous_day(record)
            if day is None:
                counters["identity_weekday_unproven"]+=1
                continue
            groups[(fold(record.get("citta")),day)].append(record)
        for pair,matching_rows in groups.items():
            entries=source.get(pair,[])
            if len(entries)!=1:
                counters["no_unique_source_market_city_weekday"]+=len(matching_rows)
                continue
            street=entries[0]["place"].strip()
            if not safe_stored_street(street):
                counters["publisher_only_vague_or_area_location"]+=len(matching_rows)
                continue
            known=_blocked_source_cohort(matching_rows,*pair)
            if known and known!={fold(street)}:
                counters["conflicting_previously_saved_location"]+=len(matching_rows)
                continue
            for row in matching_rows:
                if not _eligible_field(row):
                    counters["already_has_street_or_vague_original"]+=1
                    continue
                receipt={
                    "market_id":row["slug"],
                    "field":"indirizzo",
                    "old_value":"",
                    "candidate_value":street,
                    "source_url":final,
                    "source_requested_url":requested,
                    "evidence_method":"publisher_weekday_index_unique_city_and_day_no_conflicting_street",
                    "source_day":pair[1],
                    "observed_at":today.isoformat(),
                    "individually_confirmed":False,
                    "published_opening_verified":False,
                    "coordinate_added":False,
                    "rights_gate_passed":bool(rights_verified),
                    "apply_authorized":bool(apply and rights_verified),
                }
                proposals.append(receipt)
    if len(proposals)>MAX_UPDATES_PER_RUN:
        raise ValueError("Too many publisher-field mutations per run")
    if len({p["market_id"] for p in proposals})!=len(proposals):
        raise ValueError("Overlapping source pages proposed conflicting target IDs")
    if apply:
        by_id={p["market_id"]:p for p in proposals}
        updated=[]
        for r in base:
            new=deepcopy(r)
            proposal=by_id.get(r["slug"])
            if proposal:
                if r.get("indirizzo"):
                    raise ValueError("Publisher tried to overwrite existing street")
                new["indirizzo"]=proposal["candidate_value"]
                evidence=new.get("fonti")
                if evidence is None:evidence=[]
                if not isinstance(evidence,list) or any(not isinstance(x,dict) for x in evidence):
                    raise ValueError("Publisher source list is invalid")
                original_source={"nome":SOURCE_EVIDENCE_NAME,"url":proposal["source_url"]}
                if original_source not in evidence:
                    evidence.append(original_source)
                new["fonti"]=evidence
            updated.append(new)
    else:
        updated=deepcopy(base)
    if [r["slug"] for r in updated]!=[r["slug"] for r in base] or len(updated)!=len(base):
        raise ValueError("A source field correction changed catalog identities")
    # Independent exact diff: never change dates, GPS, city, status, primary
    # publisher or any other displayed field. No new market verification.
    changes=[]
    for before,after in zip(frozen,updated):
        diff={k for k in set(before)|set(after) if before.get(k)!=after.get(k)}
        if not diff:continue
        if not apply or diff-{"indirizzo","fonti"}:
            raise ValueError("Publisher source changed unapproved market fields")
        receipt=next((p for p in proposals if p["market_id"]==before["slug"]),None)
        if not receipt or after.get("indirizzo")!=receipt["candidate_value"]:
            raise ValueError("Source address changed without single-row evidence")
        changes.append(before["slug"])
    report={
        "schema":SCHEMA,"date":today.isoformat(),
        "publisher":PUBLISHER,"pages_evaluated":len(pages),
        "market_ids_before":len(base),"market_ids_after":len(updated),
        "parser_counts":dict(sorted(counters.items())),
        "field_candidates":len(proposals),"field_changes":len(changes),
        "proposals":proposals,"changed_ids":sorted(changes),
        "source_copyright_copying_not_required":True,
        "market_rows_deleted":0,"market_rows_inserted":0,
        "market_openings_verified":0,"new_geographic_points":0,
        "source_primary_links_replaced":0,
    }
    return updated,report


def fetch_pages(urls, *, permission_confirmed=False,
                robots_fetch=_fetch_one, page_fetch=_fetch_one,
                sleep=time.sleep):
    if permission_confirmed is not True:
        raise ValueError("No automated fetch without explicit publisher-rights approval")
    if not isinstance(urls,list) or not 1<=len(urls)<=MAX_REQUESTS_PER_RUN:
        raise ValueError("Publisher requests exceed max pages per run")
    if len(set(urls))!=len(urls) or any(not _valid_page_url(u) for u in urls):
        raise ValueError("Publisher URL not from an approved weekly-index family")
    robots=robots_allowed(robots_fetch)
    result=[]
    for i,url in enumerate(urls):
        if not robots.can_fetch(USER_AGENT,url):
            raise ValueError("Publisher robots policy denied requested weekly index")
        if i:sleep(MIN_REQUEST_PAUSE_SECONDS)
        raw,canonical=page_fetch(url)
        if not allowed_url(url,url,canonical):
            raise ValueError("Publisher redirected to a different market region")
        result.append({"requested_url":url,"final_url":canonical,"html":raw})
    return result


def safe_report(report,base):
    if (report.get("schema")!=SCHEMA or report.get("market_ids_before")!=len(base)
        or report.get("market_ids_after")!=len(base)
        or report.get("field_changes")!=len(report.get("changed_ids",[]))
        or report.get("field_candidates")!=len(report.get("proposals",[]))
        or any(report.get(k)!=0 for k in (
            "market_rows_deleted","market_rows_inserted",
            "market_openings_verified","new_geographic_points",
            "source_primary_links_replaced"))):
        raise ValueError("Publisher data release exceeded allowed source fields")
    for p in report["proposals"]:
        if (p.get("field")!="indirizzo"
            or p.get("individually_confirmed") is not False
            or p.get("published_opening_verified") is not False
            or p.get("coordinate_added") is not False):
            raise ValueError("Publisher proposal falsely claims a checked opening")
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
        "verified_market_openings_created":0,
        "geocoded_market_locations_created":0,
        "unapproved_publisher_field_overwrites":0,
        "bulk_crawling_enabled":False,
    }


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--manifest",type=Path,default=Path("public/data/v1/manifest.json"))
    ap.add_argument("--input-html",action="append",type=Path,
                    help="Approved source HTML fixture, no external requests")
    ap.add_argument("--source-url",action="append",help="Original Happings provincial URL")
    ap.add_argument("--live",action="store_true",help="Make at most 2 sequential, robots-approved source fetches")
    ap.add_argument("--permission-confirmed",action="store_true",
                    help="Explicitly attest that a valid publisher license was independently verified")
    ap.add_argument("--apply",action="store_true",help="Propose field-only changes; never auto-publish")
    ap.add_argument("--today",type=date.fromisoformat,default=date.today())
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--summary",type=Path,required=True)
    ap.add_argument("--candidate-markets",type=Path)
    args=ap.parse_args()
    if not args.source_url or len(args.source_url)>MAX_REQUESTS_PER_RUN:
        raise ValueError("Select 1-2 reviewed province pages")
    if args.live and args.input_html:
        raise ValueError("Cannot mix live and previously reviewed source HTML")
    if args.live:
        pages=fetch_pages(args.source_url,permission_confirmed=args.permission_confirmed)
    else:
        if not args.input_html or len(args.input_html)!=len(args.source_url):
            raise ValueError("Offline examples must match each exact source URL")
        pages=[
            {"requested_url":url,"final_url":url,"html":p.read_bytes()}
            for url,p in zip(args.source_url,args.input_html)
        ]
    original=load_existing(args.manifest)
    result,report=preview(original,pages,today=args.today,apply=args.apply,
                          rights_verified=args.permission_confirmed)
    safe_report(report,original)
    for f in (args.out,args.summary,args.candidate_markets):
        if f is not None:f.parent.mkdir(parents=True,exist_ok=True)
    # Full per-market field receipts remain short-lived artifacts: no
    # copyright-heavy publisher pages in git, and no 13k-row JSON commits.
    args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n","utf-8")
    args.summary.write_text(json.dumps(summarize(report),indent=2,ensure_ascii=False)+"\n","utf-8")
    if args.candidate_markets:
        args.candidate_markets.write_text(json.dumps(result,ensure_ascii=False)+"\n","utf-8")
    print(json.dumps(summarize(report),ensure_ascii=False))


if __name__=="__main__":
    main()
