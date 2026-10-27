#!/usr/bin/env python3
"""Happings provincial weekly-index parser, offline and provenance-scoped.

Separate *parsing the HTML already provided for an authorized review* from
*finding/fetching that HTML*. This module performs NO HTTP requests.

The project owner's explicit scraping instruction is recorded by the
dedicated acquisition path. This parser performs no authorization decision,
PDF-signature verification, live crawling, or publication by itself.

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
from happings_page_metadata import parse_page_metadata

MAX_HTML_BYTES=2_600_000
MAX_PUBLISHER_ITEMS=2200
MAX_CATALOG=100_000
MAX_EXAMPLES=40
WEEKDAYS=("lunedi","martedi","mercoledi","giovedi","venerdi","sabato","domenica")
RAW_ITEM=re.compile(r"^\s*ad?\s+(.{2,120}?),\s+in\s+(.{3,240})\s*$",re.I)
DAY_PARTS={
    "mattina":"morning_not_clock_hours",
    "mattino":"morning_not_clock_hours",
    "pomeriggio":"afternoon_not_clock_hours",
    "sera":"evening_not_clock_hours",
}
SOURCE_ORIGIN="www.happings.com"
VENICE_OLD="https://www.happings.com/it/mercati-settimanali-a-venezia.html"
VENICE_NEW="https://www.happings.com/it/mercati-settimanali-a-venezia-e-provincia/"
PROVINCE_PAGE_PATH=re.compile(
    r"/it/mercati-settimanali-(?:a|ad)-"
    r"(?P<province>[a-z0-9]+(?:-[a-z0-9]+)*?)(?:\.html|-e-provincia/)$"
)
VOID_TAGS=frozenset(("area","base","br","col","embed","hr","img",
                     "input","link","meta","param","source","track","wbr"))
NON_CONTENT_TAGS=frozenset(("script","style","template","noscript"))
WEEKDAY_HEADING=re.compile(
    r"^mercati (?:del|della) ("+"|".join(WEEKDAYS)+r")"
    r"(?: nei comuni di [a-z0-9]+(?: [a-z0-9]+)*)?$"
)
EXACT_TIME_CONTEXT=re.compile(
    r"\b(?:[01]?\d|2[0-4])[:.][0-5]\d\b|"
    r"\b(?:orari?|ore|dalle?|alle?)\s*\d",re.I,
)
UNREVIEWED_LOCATION_CONTEXT=re.compile(
    r"\b(?:sospes[oaie]|annullat[oaie]|trasferit[oaie]|spostat[oaie]|"
    r"temporaneamente|provvisori[oaie]|esclus[oaie]|eccetto|tranne|"
    r"solo|festivi)\b"
)
SEASONAL_QUALIFIER=re.compile(
    r"\b(?:estate|inverno|primavera|autunno|estiv[oaie]|invernal[ei]|"
    r"primaveril[ei]|autunnal[ei]|stagional[ei])\b")
INTERVAL_QUALIFIER=re.compile(
    r"\b(?:quindicinal[ei]|bisettimanal[ei]|alternat[oaie])\b|\bsettimane alterne\b|"
    r"\bogni\s*(?:\d{1,3}|due|tre|quattordici|quindici)\s*(?:gg|giorni?|settimane?|mesi)\b")
GEOGRAPHIC_SEASON_NAME=re.compile(
    r"(?:via|viale|vicolo|piazza|piazzale|passeggiata|lungomare|largo|corso) "
    r"(?:(?:d|di|del|della|dell|delle) )?(?:estate|inverno|primavera|autunno)(?: \d+[a-z]?)?")


def _calendar_qualifiers(label, field):
    """Split explicit trailing source qualifiers without changing a geonym.

    A retained incomplete qualifier forbids an ordinary weekly assignment.
    No season boundary, interval anchor or future edition is inferred here.
    """
    qualifiers=[]

    def add(text):
        key=fold(text)
        kinds=[]
        if SEASONAL_QUALIFIER.search(key):
            kinds.append("seasonal_scope_unrepresented")
        if INTERVAL_QUALIFIER.search(key):
            kinds.append("interval_scope_unrepresented")
        # Use the existing conservative calendar grammar for explicit month
        # or dated windows. Do not leave "da giugno a settembre" inside an
        # otherwise ordinary address, and never manufacture a missing year.
        from recurrence_refresh import temporal_scope_hold
        if temporal_scope_hold({"ricorrenza_testo":text})=="date_range_scope_unrepresented":
            kinds.append("date_range_scope_unrepresented")
        for kind in kinds:
            qualifiers.append({"field":field,"text":text,"reason":kind})
        return bool(kinds)

    # Parentheses make the annotation boundary explicit. Keep the complete
    # original label separately; do not rewrite the saved market identity.
    while (match:=re.fullmatch(r"(.*?)\s*\(([^()]*)\)\s*",label)):
        if not match.group(1).strip() or not add(match.group(2).strip()):
            break
        label=match.group(1).strip()
    if field=="place":
        # These complete street-name forms are geographic, not calendar
        # prose: Passeggiata d'Inverno / Via dell'Estate. A separate qualifier
        # is still retained above and can never be masked by this exemption.
        if not GEOGRAPHIC_SEASON_NAME.fullmatch(fold(label)):
            add(label)
    return label,qualifiers


def fold(text):
    n=unicodedata.normalize("NFKD",str(text or ""))
    return " ".join(re.findall(r"[a-z0-9]+","".join(
        c for c in n if not unicodedata.combining(c)).lower()))


def _canonical_province_slug(slug):
    """Normalize *observed* WordPress hex-escaped province labels, not URLs.

    Happings emits /l-27aquila/ and /forl-c3-ac-e-cesena/. These fragments
    encode an apostrophe or UTF-8 bytes as hyphen-separated hexadecimal.
    Interpret them only for comparing with unique ISTAT province scopes.
    """
    def decode(match):
        try:
            value = bytes.fromhex(match.group(0)[1:].replace("-", "")).decode("utf-8")
        except (UnicodeError, ValueError):
            return match.group(0)
        if not all(char.isprintable() for char in value):
            return match.group(0)
        if not any(ord(char) > 127 or char in "'’" for char in value):
            return match.group(0)
        return value

    expanded = re.sub(r"(?:-[0-9a-f]{2})+", decode, slug)
    return fold(expanded.replace("-", " ")).replace(" ", "-")


def province_page_key(url):
    """Return a syntactic province key, not proof a redirect actually occurred.

    Only historic a-/ad- .html listings and the reviewed -e-provincia/
    layout are in scope. Callers retain both observed URLs; this function
    neither creates a canonical URL nor admits individual town details.
    """
    try:
        p=urlsplit(str(url or ""))
        if (p.scheme!="https" or p.hostname!=SOURCE_ORIGIN
                or p.username or p.password or p.port not in (None,443)
                or p.query or p.fragment):
            return None
        match=PROVINCE_PAGE_PATH.fullmatch(p.path)
        return _canonical_province_slug(match.group("province")) if match else None
    except ValueError:
        return None


def _valid_page_url(url):
    return province_page_key(url) is not None


def _weekday_heading(value):
    text=fold(value)
    match=WEEKDAY_HEADING.fullmatch(text)
    if not match:
        return None
    # Extra qualifiers such as "sospesi" or "straordinari" must not be
    # interpreted as the ordinary recurring market section.
    return WEEKDAYS.index(match.group(1))


def _source_row(city, place, weekday):
    """Keep the reviewed list grammar identical across bounded containers."""
    city_label=city.strip()
    suffix=re.search(r"\s*\((la mattina|il mattino|al mattino|il pomeriggio|la sera)\)\s*$",
                     place,re.I)
    daypart=None
    if suffix:
        folded=fold(suffix.group(1))
        daypart=next((v for token,v in DAY_PARTS.items() if token in folded),None)
        place=place[:suffix.start()].strip()
    place_label=place
    city,city_qualifiers=_calendar_qualifiers(city.strip(),"city")
    # "Ancona 11": the publisher numbers several markets of one town; no comune
    # name ends in a number. city_label keeps the published text.
    city=re.sub(r"\s+\d{1,2}$","",city.strip())
    place,place_qualifiers=_calendar_qualifiers(place,"place")
    qualifiers=city_qualifiers+place_qualifiers
    if not 2<=len(city.strip())<=120 or not 3<=len(place)<=240:
        raise ValueError("Publisher weekly row exceeds reviewed field bounds")
    return {
        "city":city.strip(),"city_key":fold(city),"city_label":city_label,
        "weekday":weekday,"place":place,"place_label":place_label,
        "calendar_scope":({"status":"unrepresented","qualifiers":qualifiers,
                           "forecast_allowed":False,"assignment_allowed":False}
                          if qualifiers else None),
        "location_indicated":True,"daypart":daypart,
        "has_specific_location":(safe_stored_street(place)
                                 and not EXACT_TIME_CONTEXT.search(place)
                                 and not UNREVIEWED_LOCATION_CONTEXT.search(fold(place))
                                 and not qualifiers),
    }


class WeeklyIndexParser(HTMLParser):
    """Only one reviewed HTML structure: .happings-seo-content h3 + ul>li."""

    def __init__(self,source_province=None):
        super().__init__(convert_charrefs=True)
        self.stack=[]
        self.current_weekday=None
        self.source_province=fold(source_province)
        self.rows=[]
        self.weekday_headings=[]
        self.seo_blocks=0
        self.total_li=0
        self.unparsed_listing_items=0
        self.unknown_weekday_headings=0

    def _in_listing(self):
        return (not any(frame["non_content"] for frame in self.stack)
                and any("happings-seo-content" in frame["classes"] for frame in self.stack))

    def handle_starttag(self,tag,attrs):
        klass=frozenset(str(dict(attrs).get("class") or "").split())
        non_content=(tag in NON_CONTENT_TAGS
                     or any(frame["non_content"] for frame in self.stack))
        if "happings-seo-content" in klass and not non_content:
            self.seo_blocks+=1
            self.current_weekday=None
        in_listing=self._in_listing() and not non_content
        if in_listing and tag in ("h1","h2","h3","h4","h5","h6"):
            self.current_weekday=None
        if tag=="li" and in_listing:
            self.total_li+=1
            if self.total_li>MAX_PUBLISHER_ITEMS:
                raise ValueError("Weekly HTML contains an excessive number of source rows")
        if not non_content and tag in ("ul","ol","li","h1","h2","h3","h4","h5","h6"):
            for frame in self.stack:
                if frame["listing_row"]:
                    frame["unreviewed_children"]=True
        if tag in VOID_TAGS:
            return
        listing_row=(tag=="li" and in_listing and bool(self.stack)
                     and self.stack[-1]["tag"]=="ul"
                     and not any(frame["tag"]=="li" for frame in self.stack))
        self.stack.append({"tag":tag,"classes":klass,
                           "text":[] if in_listing and tag in ("h1","h2","h3","li") else None,
                           "text_truncated":False,
                           "unreviewed_children":False,
                           "listing_row":listing_row,
                           "weekday":self.current_weekday,
                           "non_content":non_content,
                           "in_listing":in_listing})

    def handle_data(self,data):
        if any(frame["non_content"] for frame in self.stack):
            return
        text=" ".join(data.split())
        if not text:
            return
        for frame in self.stack:
            if frame["text"] is not None:
                if len(frame["text"])>=70 or len(text)>370:
                    frame["text_truncated"]=True
                if len(frame["text"])<70:
                    frame["text"].append(text[:370])

    def handle_endtag(self,tag):
        idx=next((i for i in range(len(self.stack)-1,-1,-1)
                  if self.stack[i]["tag"]==tag),None)
        if idx is None:
            return
        while len(self.stack)>idx:
            frame=self.stack.pop()
            if frame["non_content"]:
                continue
            if "happings-seo-content" in frame["classes"]:
                self.current_weekday=None
            if not frame["in_listing"]:
                continue
            data=" ".join(frame["text"] or []).strip()
            if frame["tag"] in ("h1","h2"):
                scope=re.fullmatch(
                    r"mercati settimanali nei comuni in provincia di (.+)",fold(data))
                if (scope and self.source_province
                        and scope.group(1)!=self.source_province):
                    raise ValueError("Publisher heading crossed province")
            if frame["tag"]=="h3":
                day=None if frame["text_truncated"] else _weekday_heading(data)
                # A changed/unrecognized weekday heading is not inherited
                # from the previous section; fail closed to prevent assigning
                # Thursday's items to Wednesday.
                self.current_weekday=day
                if day is not None:
                    # An explicit province in the reviewed heading is also
                    # evidence: a URL alone must not mask a wrong HTML file.
                    scope=re.search(r"\bnei comuni di (.+)$",fold(data))
                    if (scope and self.source_province
                            and scope.group(1)!=self.source_province):
                        raise ValueError("Publisher weekday heading crossed province")
                    self.weekday_headings.append(day)
                elif re.match(r"mercati (?:del|della)\b",fold(data)):
                    self.unknown_weekday_headings+=1
            elif frame["tag"]=="li" and frame["weekday"] is not None:
                match=(None if not frame["listing_row"] or frame["text_truncated"]
                       or frame["unreviewed_children"]
                       else RAW_ITEM.fullmatch(data))
                if not match:
                    self.unparsed_listing_items+=1
                    continue
                try:
                    entry=_source_row(*match.groups(),frame["weekday"])
                except ValueError:
                    self.unparsed_listing_items+=1
                    continue
                self.rows.append(entry)
                if len(self.rows)>MAX_PUBLISHER_ITEMS:
                    raise ValueError("Weekly HTML contains an excessive number of source rows")


def parse(html_bytes,*,source_url,observed_on=None):
    if not _valid_page_url(source_url):
        raise ValueError("Source URL is outside the reviewed Happings provincial layout")
    if (not isinstance(html_bytes,bytes) or
            not 300<=len(html_bytes)<=MAX_HTML_BYTES):
        raise ValueError("Missing or unbounded reviewed weekly-index HTML")
    from happings_editorial_weekly_layout import parse_editorial
    editorial=parse_editorial(html_bytes,source_province=province_page_key(source_url))
    if editorial is not None:
        editorial.page_metadata=parse_page_metadata(html_bytes,final_url=source_url,
                                                     read_on=observed_on or date.today())
        return editorial
    parser=WeeklyIndexParser(source_province=province_page_key(source_url))
    parser.feed(html_bytes.decode("utf-8-sig",errors="replace"))
    parser.close()
    incomplete_listing=any("happings-seo-content" in frame["classes"]
                           for frame in parser.stack)
    if (parser.unparsed_listing_items or parser.unknown_weekday_headings
            or incomplete_listing):
        # Silently dropping a second venue makes the first falsely unique.
        # Quarantine this page until its changed layout has been reviewed.
        raise ValueError("Publisher weekday layout has unparsed listing items or headings, or is incomplete")
    if not parser.seo_blocks or not parser.weekday_headings or not parser.rows:
        raise ValueError("Publisher HTML no longer matches the reviewed day/venue layout")
    parser.page_metadata=parse_page_metadata(html_bytes,final_url=source_url,
                                             read_on=observed_on or date.today())
    return parser


def _origins_equivalent(record_url,source_url):
    """Scope-normalized Happings old .html vs current province listing URL.

    Happings moved multiple historic ...a-{province}.html indexes to the
    canonical ...a-{province}-e-provincia/ format. Earlier QA recognized
    ONLY Venezia, wrongly reporting other provinces as zero matching rows.
    Both URLs must be valid HTTPS weekly INDEX pages of this exact host;
    city-level detail URLs are not admitted as equivalent by guessing.
    """
    record_key=province_page_key(record_url)
    return record_key is not None and record_key==province_page_key(source_url)


def compare_saved_markets(original_rows,html_bytes,*,source_url,today=None):
    """Find field losses in one *already supplied* page. Never writes facts."""
    today=today or date.today()
    if (not isinstance(today,date) or not isinstance(original_rows,list)
            or not 1<=len(original_rows)<=MAX_CATALOG):
        raise ValueError("Invalid saved-market comparison")
    parsed=parse(html_bytes,source_url=source_url,observed_on=today)
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
            elif source.get("calendar_scope"):
                counts["publisher_calendar_scope_unrepresented"]+=1
            elif not source["has_specific_location"]:
                counts["source_only_has_vague_place"]+=1
            if source["daypart"]:
                counts["publisher_dayparts_not_exact_hours"]+=1
    from happings_field_coverage import aggregate_coverage, weekly_page_coverage
    field_coverage=aggregate_coverage([weekly_page_coverage(html_bytes,parsed,
        requested_url=source_url,final_url=source_url,considered_ids=compared_ids)])
    exact_hours=field_coverage["fields"]["orario_testo"]["source_presence"]["precise"]
    dayparts=field_coverage["fields"]["orario_testo"]["source_presence"]["qualitative"]
    return {
        "schema":1,"as_of":today.isoformat(),
        "source_id":"happings-weekly-area-index",
        "publisher_page_url":source_url,
        "source_html_sha256":hashlib.sha256(html_bytes).hexdigest(),
        "publisher_items_detected":len(parsed.rows),
        "source_weekday_headings":len(parsed.weekday_headings),
        "publisher_time_granularity":("clock_information_present_reader_gap" if exact_hours
                                      else "daypart_not_clock_hours" if dayparts else "not_indicated"),
        "field_coverage":field_coverage,
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
