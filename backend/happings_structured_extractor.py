#!/usr/bin/env python3
"""Happings provincial market tables: source-first extraction QA (OFFLINE ONLY).

Read a bounded, separately obtained HTML sample and understand the publisher
layout ONCE, rather than trusting old Firestore imports. Can recover city,
weekday, venue text and coarse day-part from a provincial table in memory.

This is intentionally NOT a network scraper. The provided authorization PDF
(AUT-SCRAP-2026, 2026-10-19 review) has unfilled grantor/beneficiary details,
"[Inserire Data]" and no visible signature; it says effectiveness begins on
signature and does not transfer content IP. Until execution/authorized reuse
is independently evidenced, no background fetch, bulk copying, or automatic
source-derived field writes are enabled. No HTML or protected text is saved
to Git reports. Raw parser values remain ephemeral in process memory.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from merge_catalog import load_existing
from source_reconciliation_audit import _unambiguous_day
from lombardia_overlap import norm

MAX_HTML_BYTES = 2_500_000
MAX_MARKET_ROWS = 2500
MAX_CATALOG_ROWS = 100_000
MAX_REPORT_EXAMPLES = 24
WEEKDAYS = ("lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica")
WEEKDAY_WORD = re.compile(r"\b(?:lunedi|martedi|mercoledi|giovedi|venerdi|sabato|domenica)\b")
INDEX_PATH = re.compile(r"^/it/mercati-settimanali-a(?:d)?-([a-z0-9-]+?)(?:-e-provincia)?(?:\.html|/)$")
VENUE_LINE = re.compile(r"^\s*a(?:d)?\s+([^,]{2,140}),\s*in\s+(.{3,300})$", re.I)
TIME_SUFFIX = re.compile(r"\s*\((la mattina|il pomeriggio|tutto il giorno|la sera)\)\s*$", re.I)
DAYPARTS = {
    "la mattina":"morning_no_clock_time",
    "il pomeriggio":"afternoon_no_clock_time",
    "tutto il giorno":"whole_day_no_clock_time",
    "la sera":"evening_no_clock_time",
}
SKIP = frozenset({"script","style","noscript","template"})

def simplified(value):
    raw=unicodedata.normalize("NFKD",str(value or ""))
    raw="".join(c for c in raw if not unicodedata.combining(c)).lower()
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",raw)).strip()

def source_index_key(url):
    """Canonical /...-e-provincia/ and old .html URLs share ONE publisher key."""
    if not isinstance(url,str):
        return None
    try:
        parsed=urlsplit(url)
        if (parsed.scheme!="https" or parsed.hostname!="www.happings.com"
            or parsed.username or parsed.password or parsed.port not in (None,443)
            or parsed.query or parsed.fragment):
            return None
        match=INDEX_PATH.fullmatch(parsed.path)
    except ValueError:
        return None
    return match.group(1) if match else None

def _parse_day(heading):
    text=simplified(heading)
    if not text.startswith("mercati del ") and not text.startswith("mercati della "):
        return None
    names=WEEKDAY_WORD.findall(text)
    if len(set(names))!=1:
        return None
    return WEEKDAYS.index(names[0])

def _clean_venue(text):
    raw=re.sub(r"\s+"," ",str(text)).strip()
    m=TIME_SUFFIX.search(raw)
    daypart=DAYPARTS.get(simplified(m.group(1)),"unknown") if m else "unknown"
    if m: raw=raw[:m.start()].strip(" ,-")
    return raw,daypart

class ProvincialPage(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack=[]
        self.ignored=0
        self.current_day=None
        self.rows=[]
        self.h3_weekday_count=0
        self.section_seen=False
        self.section_characters=0
        self.modified_at=""
        self.duplicate_rows=0
        self._row_fingerprints=set()
        self.malformed_items=0

    def handle_starttag(self,tag,attrs):
        props=dict(attrs)
        classes=set(str(props.get("class") or "").split())
        if tag=="meta" and props.get("property")=="article:modified_time":
            value=str(props.get("content") or "")
            if re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d(?:\.\d+)?(?:Z|[+-]\d\d:\d\d)",value):
                self.modified_at=value
        if tag in SKIP:
            self.ignored+=1
        if "happings-seo-content" in classes:
            self.section_seen=True
        self.stack.append({
            "tag":tag,
            "classes":classes,
            "text":[] if tag in ("h3","li") else None,
        })

    def handle_startendtag(self,tag,attrs):
        self.handle_starttag(tag,attrs)
        self.handle_endtag(tag)

    def _in_section(self):
        return any("happings-seo-content" in x["classes"] for x in self.stack)

    def _inside_list(self):
        return any(x["tag"]=="ul" for x in self.stack)

    def handle_data(self,data):
        if self.ignored or not self._in_section():
            return
        text=" ".join(data.split())
        if not text:return
        self.section_characters+=len(text)
        if self.section_characters>MAX_HTML_BYTES:
            raise ValueError("Unbounded publisher section text")
        for node in self.stack:
            if node["text"] is not None and len(node["text"])<100:
                node["text"].append(text[:400])

    def handle_endtag(self,tag):
        found=next((i for i in range(len(self.stack)-1,-1,-1)
                    if self.stack[i]["tag"]==tag),None)
        if found is None:return
        section=self._in_section()
        within_list=self._inside_list()
        removed=self.stack[found:]
        for node in reversed(removed):
            content=" ".join(node["text"] or []).strip()
            if node["tag"]=="h3" and section:
                self.current_day=_parse_day(content)
                if self.current_day is not None:
                    self.h3_weekday_count+=1
            elif node["tag"]=="li" and section and within_list and self.current_day is not None:
                m=VENUE_LINE.fullmatch(content)
                if not m:
                    self.malformed_items+=1
                    continue
                city=" ".join(m.group(1).split())
                address,daypart=_clean_venue(m.group(2))
                if (not 2<=len(city)<=140 or not 3<=len(address)<=260
                    or not simplified(city) or not simplified(address)):
                    self.malformed_items+=1
                    continue
                key=(simplified(city),self.current_day,simplified(address))
                if key in self._row_fingerprints:
                    self.duplicate_rows+=1
                    continue
                self._row_fingerprints.add(key)
                if len(self.rows)>=MAX_MARKET_ROWS:
                    raise ValueError("Publisher list exceeded bounded venue count")
                self.rows.append({
                    "municipality":city,
                    "weekday":self.current_day,
                    "venue_label":address,
                    "daypart":daypart,
                    "clock_hours":None,
                    "individual_event_verified":False,
                })
        self.stack=self.stack[:found]
        self.ignored=max(0,self.ignored-sum(1 for n in removed if n["tag"] in SKIP))

def parse_page(blob,*,original_url,canonical_url=None):
    """Pure parser. No URLs are opened, no file is written."""
    orig=source_index_key(original_url)
    resolved=source_index_key(canonical_url or original_url)
    if not orig or not resolved or orig!=resolved:
        raise ValueError("Source index URL, canonical and municipality scope disagree")
    if not isinstance(blob,bytes) or not 300<=len(blob)<=MAX_HTML_BYTES:
        raise ValueError("Unbounded or empty publisher HTML sample")
    parser=ProvincialPage()
    parser.feed(blob.decode("utf-8-sig",errors="replace"))
    parser.close()
    if not parser.section_seen or not parser.h3_weekday_count or not parser.rows:
        raise ValueError("Publisher HTML layout drift: no recognized weekday/venue table")
    return {
        "kind":"happings_weekly_provincial",
        "index_key":orig,
        "original_url":original_url,
        "canonical_url":canonical_url or original_url,
        "modified_at_article_not_individual_venue":parser.modified_at,
        "source_bytes_sha256":hashlib.sha256(blob).hexdigest(),
        "section_weekday_headings":parser.h3_weekday_count,
        "distinct_venue_rows":len(parser.rows),
        "identical_rows_collapsed":parser.duplicate_rows,
        "unrecognized_list_items":parser.malformed_items,
        "rows":parser.rows,  # IN MEMORY ONLY, never serialized by the audit CLI
        "publisher_reuse_grant_verified":False,
        "edition_openings_confirmed":0,
    }

def compare_saved(page,markets,*,province):
    """Surface missing fields without saving the unpublished address text."""
    if (not isinstance(province,str) or not re.fullmatch(r"[A-Z]{2}",province)
        or not isinstance(markets,list) or len(markets)>MAX_CATALOG_ROWS
        or not isinstance(page,dict) or not isinstance(page.get("rows"),list)):
        raise ValueError("Invalid province, original markets or source sample")
    index=defaultdict(list)
    for src in page["rows"]:
        index[(simplified(src["municipality"]),src["weekday"])].append(src)
    result=Counter()
    examples=[]
    ids=set()
    candidates=[]
    for record in markets:
        if not isinstance(record,dict):
            raise ValueError("Malformed market row")
        ident=record.get("slug")
        if not isinstance(ident,str) or not ident or ident in ids:
            raise ValueError("Lost/duplicate market identity in comparison")
        ids.add(ident)
        if (record.get("fonte")!="happings.com"
            or str(record.get("provincia") or "").upper()!=province
            or source_index_key(record.get("url_fonte"))!=page["index_key"]):
            continue
        result["catalog_records_from_this_original_index"]+=1
        day=_unambiguous_day(record)
        if day is None:
            result["stored_weekday_ambiguous"]+=1
            continue
        possible=index.get((simplified(record.get("citta")),day),[])
        if not possible:
            result["publisher_venue_missing_for_city_day"]+=1
            continue
        if len(possible)>1:
            result["publisher_has_multiple_distinct_venues_same_city_day"]+=1
            continue
        candidate=possible[0]
        old=simplified(record.get("indirizzo"))
        new=simplified(candidate["venue_label"])
        if old and old==new:
            result["already_stored_matching_venue"]+=1
            continue
        kind="missing_address" if not old or old in ("centro","centro storico") else "conflicting_address"
        result[kind]+=1
        # Source record exists and appears uniquely in that INDEX, but a
        # second independent official source must certify venue identity
        # before adding a street to the public site.
        info={
            "market_id":ident,
            "evidence_type":"source_page_has_distinct_venue",
            "field":"indirizzo",
            "finding":kind,
            "source_index_key":page["index_key"],
            "source_page_sha256":page["source_bytes_sha256"],
            "source_venue_sha256":hashlib.sha256(new.encode()).hexdigest(),
            "source_weekday":day,
            "daypart":candidate["daypart"],
            "publisher_article_changed_at":page["modified_at_article_not_individual_venue"],
            "source_text_copied_to_report":False,
            "identity_fully_independently_confirmed":False,
            "may_autowrite_catalog":False,
            "individual_opening_confirmed":False,
        }
        candidates.append(info)
        if len(examples)<MAX_REPORT_EXAMPLES:examples.append(info)
    return {
        "schema":1,
        "source_index_key":page["index_key"],
        "publisher_document_hash":page["source_bytes_sha256"],
        "region_scoped_province":province,
        "parsed_venue_rows":len(page["rows"]),
        "market_ids_preserved":len(ids),
        "counts":dict(sorted(result.items())),
        "example_findings":examples,
        "candidate_count":len(candidates),
        "candidate_target_ids_sha256":hashlib.sha256(
            "\n".join(sorted(x["market_id"] for x in candidates)).encode()).hexdigest(),
        "all_original_rows_retained":True,
        "source_html_persisted":False,
        "publisher_venue_values_persisted":False,
        "scraping_automation_enabled":False,
        "publisher_ip_license_inferred":False,
        "market_updates":0,
        "verified_openings":0,
        "precise_coordinates_created":0,
    }

def validate(report,expected_markets):
    if (not isinstance(report,dict) or report.get("schema")!=1
        or report.get("market_ids_preserved")!=expected_markets
        or report.get("all_original_rows_retained") is not True
        or report.get("source_html_persisted") is not False
        or report.get("publisher_venue_values_persisted") is not False
        or report.get("scraping_automation_enabled") is not False
        or report.get("publisher_ip_license_inferred") is not False
        or any(report.get(x)!=0 for x in (
            "market_updates","verified_openings","precise_coordinates_created"))):
        raise ValueError("Source comparison cannot change the catalog or grant scraping rights")
    for item in report.get("example_findings",[]):
        if (item.get("source_text_copied_to_report") is not False
            or item.get("may_autowrite_catalog") is not False
            or item.get("individual_opening_confirmed") is not False
            or item.get("field")!="indirizzo"
            or not re.fullmatch(r"[0-9a-f]{64}",item.get("source_venue_sha256",""))):
            raise ValueError("Source comparison failed field-only provenance checks")
    return True

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--html",type=Path,required=True,help="Separately obtained Happings provincial HTML sample; NO web fetch")
    p.add_argument("--url",required=True,help="Historical source URL in our catalog")
    p.add_argument("--canonical-url",help="Actual canonical Happings URL, if redirected")
    p.add_argument("--province",required=True)
    p.add_argument("--manifest",type=Path,default=Path("public/data/v1/manifest.json"))
    p.add_argument("--out",type=Path,required=True,help="Counts, IDs and hashes only: never source rows")
    args=p.parse_args()
    old=load_existing(args.manifest)
    parsed=parse_page(args.html.read_bytes(),original_url=args.url,canonical_url=args.canonical_url)
    report=compare_saved(parsed,old,province=args.province.upper())
    validate(report,len(old))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n","utf-8")
    print(json.dumps({
        "market_records_preserved":len(old),
        "source_venue_rows":parsed["distinct_venue_rows"],
        "missing_address_found":report["counts"].get("missing_address",0),
        "conflicting_stored_address":report["counts"].get("conflicting_address",0),
        "source_automation_enabled":False,
        "catalog_writes":0,
    },ensure_ascii=False))
if __name__=="__main__":
    main()
