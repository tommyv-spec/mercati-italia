#!/usr/bin/env python3
"""Happings provincial weekly-index parser, offline and source-consent gated.

Separate *parsing the HTML already provided for an authorized review* from
*finding/fetching that HTML*. This module performs NO HTTP requests.

The October 2025 Happings terms require their written consent for robots
collecting content. Never use this module as authorization for live crawling,
bulk extraction, or a publisher content copy.

The source may contain venue locations and a morning/afternoon daypart, but
these are NOT exact clock hours, independent venue verification, or proof an
individual edition takes place. The persisted report NEVER contains source
body text, street labels or organizer contacts; just source/canonical URLs,
market IDs and field-presence/matching evidence.
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

from source_reconciliation_audit import _unambiguous_day
from stored_market_sibling_proposals import safe_stored_street

MAX_HTML_BYTES=2_600_000
MAX_PUBLISHER_ITEMS=2200
MAX_CATALOG=100_000
MAX_EXAMPLES=40
WEEKDAYS=("lunedi","martedi","mercoledi","giovedi","venerdi","sabato","domenica")
RAW_ITEM=re.compile(r"^\s*a\s+(.{2,120}?),\s+in\s+(.{3,240})\s*$",re.I)
DAY_PARTS={
    "mattina":"morning_not_clock_hours",
    "pomeriggio":"afternoon_not_clock_hours",
    "sera":"evening_not_clock_hours",
}
SOURCE_ORIGIN="www.happings.com"
VENICE_OLD="https://www.happings.com/it/mercati-settimanali-a-venezia.html"
VENICE_NEW="https://www.happings.com/it/mercati-settimanali-a-venezia-e-provincia/"


def fold(text):
    n=unicodedata.normalize("NFKD",str(text or ""))
    return " ".join(re.findall(r"[a-z0-9]+","".join(
        c for c in n if not unicodedata.combining(c)).lower()))


def _valid_page_url(url):
    try:
        p=urlsplit(str(url or ""))
        return (p.scheme=="https" and p.hostname==SOURCE_ORIGIN
                and not p.username and not p.password and p.port in (None,443)
                and not p.query and not p.fragment
                and bool(re.fullmatch(r"/it/mercati-settimanali-a-[a-z0-9-]+(?:\.html|/)",p.path)))
    except ValueError:
        return False


def _weekday_heading(value):
    text=fold(value)
    if not text.startswith("mercati del ") and not text.startswith("mercati della "):
        return None
    words=set(text.split())
    present=[i for i,v in enumerate(WEEKDAYS) if v in words]
    return present[0] if len(present)==1 else None


class WeeklyIndexParser(HTMLParser):
    """Only one reviewed HTML structure: .happings-seo-content h3 + ul>li."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack=[]
        self.current_weekday=None
        self.rows=[]
        self.weekday_headings=[]
        self.seo_blocks=0
        self.total_li=0

    def _in_listing(self):
        return any("happings-seo-content" in frame["classes"] for frame in self.stack)

    def handle_starttag(self,tag,attrs):
        klass=frozenset(str(dict(attrs).get("class") or "").split())
        if "happings-seo-content" in klass:
            self.seo_blocks+=1
        if tag=="li" and self._in_listing():
            self.total_li+=1
        self.stack.append({"tag":tag,"classes":klass,
                           "text":[] if tag in ("h3","li") else None,
                           "in_listing":self._in_listing()})

    def handle_data(self,data):
        text=" ".join(data.split())
        if not text:
            return
        for frame in self.stack:
            if frame["text"] is not None and len(frame["text"])<70:
                frame["text"].append(text[:370])

    def handle_endtag(self,tag):
        idx=next((i for i in range(len(self.stack)-1,-1,-1)
                  if self.stack[i]["tag"]==tag),None)
        if idx is None:
            return
        while len(self.stack)>idx:
            frame=self.stack.pop()
            if not frame["in_listing"]:
                continue
            data=" ".join(frame["text"] or []).strip()
            if frame["tag"]=="h3":
                day=_weekday_heading(data)
                # A changed/unrecognized weekday heading is not inherited
                # from the previous section; fail closed to prevent assigning
                # Thursday's items to Wednesday.
                self.current_weekday=day
                if day is not None:
                    self.weekday_headings.append(day)
            elif frame["tag"]=="li" and self.current_weekday is not None:
                match=RAW_ITEM.fullmatch(data)
                if not match:
                    continue
                city,place=match.groups()
                suffix=re.search(r"\s*\((la mattina|il mattino|al mattino|il pomeriggio|la sera)\)\s*$",
                                 place,re.I)
                daypart=None
                if suffix:
                    folded=fold(suffix.group(1))
                    daypart=next((v for token,v in DAY_PARTS.items() if token in folded),None)
                    place=place[:suffix.start()].strip()
                if not 2<=len(city.strip())<=120 or not 3<=len(place)<=240:
                    continue
                self.rows.append({
                    "city":city.strip(),
                    "city_key":fold(city),
                    "weekday":self.current_weekday,
                    "place":place,
                    "location_indicated":True,
                    "daypart":daypart,
                    "has_specific_location":safe_stored_street(place),
                })
                if len(self.rows)>MAX_PUBLISHER_ITEMS:
                    raise ValueError("Weekly HTML contains an excessive number of source rows")


def parse(html_bytes,*,source_url):
    if not _valid_page_url(source_url):
        raise ValueError("Source URL is outside the reviewed Happings provincial layout")
    if (not isinstance(html_bytes,bytes) or
            not 300<=len(html_bytes)<=MAX_HTML_BYTES):
        raise ValueError("Missing or unbounded reviewed weekly-index HTML")
    parser=WeeklyIndexParser()
    parser.feed(html_bytes.decode("utf-8-sig",errors="replace"))
    parser.close()
    if not parser.seo_blocks or not parser.weekday_headings or not parser.rows:
        raise ValueError("Publisher HTML no longer matches the reviewed day/venue layout")
    return parser


def _origins_equivalent(record_url,source_url):
    """Scope-normalized Happings old .html vs current province listing URL.

    Happings moved multiple historic ...a-{province}.html indexes to the
    canonical ...a-{province}-e-provincia/ format. Earlier QA recognized
    ONLY Venezia, wrongly reporting other provinces as zero matching rows.
    Both URLs must be valid HTTPS weekly INDEX pages of this exact host;
    city-level detail URLs are not admitted as equivalent by guessing.
    """
    if not _valid_page_url(record_url) or not _valid_page_url(source_url):
        return False

    def base(url):
        path=urlsplit(url).path
        return re.sub(r"(?:-e-provincia/|\\.html)$","",path)

    return base(record_url)==base(source_url)


def compare_saved_markets(original_rows,html_bytes,*,source_url,today=None):
    """Find field losses in one *already supplied* page. Never writes facts."""
    today=today or date.today()
    if (not isinstance(today,date) or not isinstance(original_rows,list)
            or not 1<=len(original_rows)<=MAX_CATALOG):
        raise ValueError("Invalid saved-market comparison")
    parsed=parse(html_bytes,source_url=source_url)
    by_city_day=defaultdict(list)
    for src in parsed.rows:
        by_city_day[(src["city_key"],src["weekday"])].append(src)
    seen=set()
    counts=Counter()
    examples=[]
    compared_ids=[]
    for row in original_rows:
        sid=row.get("slug") if isinstance(row,dict) else None
        if not isinstance(sid,str) or not sid or sid in seen:
            raise ValueError("Missing/repeated market identity")
        seen.add(sid)
        if row.get("fonte")!="happings.com" or not _origins_equivalent(row.get("url_fonte"),source_url):
            continue
        counts["same_publisher_page_catalog_rows"]+=1
        day=_unambiguous_day(row)
        if day is None:
            counts["cannot_prove_catalog_weekday"]+=1
            continue
        lookup=by_city_day.get((fold(row.get("citta")),day),[])
        compared_ids.append(sid)
        if len(lookup)==0:
            counts["no_matching_city_day_on_page"]+=1
        elif len(lookup)>1:
            counts["more_than_one_source_venue_on_city_day"]+=1
        else:
            source=lookup[0]
            counts["unique_city_day_source_item"]+=1
            old=row.get("indirizzo")
            hasold=safe_stored_street(old)
            if source["has_specific_location"] and not hasold:
                counts["saved_market_missing_source_location"]+=1
                if len(examples)<MAX_EXAMPLES:
                    examples.append({
                        "market_id":sid,
                        "source_day":WEEKDAYS[day],
                        "gap":"source_has_location_catalog_lacks_specific_street",
                        "source_venue_content_stored":False,
                        "can_auto_import_without_publisher_permission":False,
                        "market_confirmation":False,
                    })
            elif source["has_specific_location"] and hasold:
                if fold(old)==fold(source["place"]):
                    counts["source_and_saved_market_street_agree"]+=1
                else:
                    counts["source_and_saved_market_street_disagree_review_only"]+=1
            elif not source["has_specific_location"]:
                counts["source_only_has_vague_place"]+=1
            if source["daypart"]:
                counts["publisher_dayparts_not_exact_hours"]+=1
    return {
        "schema":1,"as_of":today.isoformat(),
        "source_id":"happings-weekly-area-index",
        "publisher_page_url":source_url,
        "source_html_sha256":hashlib.sha256(html_bytes).hexdigest(),
        "publisher_items_detected":len(parsed.rows),
        "source_weekday_headings":len(parsed.weekday_headings),
        "publisher_time_granularity":"daypart_not_clock_hours",
        "source_page_publication_date_is_not_market_verification":True,
        "saved_market_ids_examined":len(original_rows),
        "matching_legacy_market_records":counts["same_publisher_page_catalog_rows"],
        "counts":dict(sorted(counts.items())),
        "examples":examples,
        "source_street_values_persisted":False,
        "source_html_persisted":False,
        "source_scraping_permitted_by_this_audit":False,
        "catalog_records_added":0,
        "catalog_records_deleted":0,
        "catalog_fields_modified":0,
        "confirmed_market_editions_added":0,
        "precise_coordinates_created":0,
    }


def verify(report, original_count):
    if (report.get("schema")!=1 or report.get("saved_market_ids_examined")!=original_count
            or report.get("source_page_publication_date_is_not_market_verification") is not True
            or report.get("source_street_values_persisted") is not False
            or report.get("source_html_persisted") is not False
            or report.get("source_scraping_permitted_by_this_audit") is not False
            or any(report.get(field)!=0 for field in (
                "catalog_records_added","catalog_records_deleted","catalog_fields_modified",
                "confirmed_market_editions_added","precise_coordinates_created"))):
        raise ValueError("Happings source-layout audit exceeded its reviewed scope")
    return True


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--input-html",required=True,type=Path,
                   help="Previously obtained, authorized HTML sample; no live fetching")
    p.add_argument("--source-url",required=True)
    p.add_argument("--manifest",default="public/data/v1/manifest.json",type=Path)
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--today",type=date.fromisoformat,default=date.today())
    args=p.parse_args()
    from merge_catalog import load_existing
    source=load_existing(args.manifest)
    report=compare_saved_markets(source,args.input_html.read_bytes(),
                                 source_url=args.source_url,today=args.today)
    verify(report,len(source))
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n","utf-8")
    print(json.dumps({
        "rows_examined":report["saved_market_ids_examined"],
        "source_items":report["publisher_items_detected"],
        "source_fields_lost":report["counts"].get("saved_market_missing_source_location",0),
        "changes_to_markets":0,"publisher_scraping_requests":0,
    }))

if __name__=="__main__":
    main()
