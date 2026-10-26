#!/usr/bin/env python3
"""Source-level, declarative municipal data lifecycle (NO per-market scripts).

A source contract controls schema, row meaning, identity grain, legal state,
age, bounding and parsing. One code path applies to any approved CSV/JSON.
Reading a source is NOT proof of market openings and NEVER imports by itself.

Source-level contract changes require a Git review. The source registry, schema
probe and this process run automatically and produce actionable *exceptions*.
The normal daily catalog pipeline and already approved publisher importers
continue independently.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import unicodedata
from collections import Counter
from datetime import date, datetime, timezone
from http.client import HTTPException
from pathlib import Path
from urllib.parse import urlsplit, parse_qs

from merge_catalog import load_existing
from source_dispositions import reconcile as reconcile_reviewed_source_ids
from recurrence_refresh import WEEKDAYS, complete_monthly_rule, explicit_rule
from source_probe import limited_fetch, safe_url
from reviewed_city_evidence import NAVIGATION_HOLD
from publisher_snapshot_date import resolve_source_date, validate_strategy
from source_hours import preserve_hours_text

SCHEMA = 1
MAX_RAW_PROFILES = 8
MAX_NORMALIZED_PROFILES = 30
MAX_ROWS = 6000
MAX_PROFILE_BYTES = 65536
# A published PDF table (one regional calendar) is larger than a CSV export.
MAX_DOCUMENT_BYTES = 4_000_000
MAX_PDF_PAGES = 60
# Daily quota of publisher contracts read over the network in one run.
MAX_ENABLED_RAW_PROFILES = 4
MAX_MARKDOWN_EXAMPLES = 10
# market_venue_month: one row = one venue on one monthly calendar
# ("Prima domenica del mese"), read from recurrence_field.
MONTH_KIND = "market_venue_month"
MARKET_KINDS = frozenset({"market_venue", "market_venue_day", MONTH_KIND})
CATEGORIES = frozenset({"misto","alimentare","antiquariato","artigianato","usato","vintage_abbigliamento"})
MONTHLY_ORDINALS = {1: ("primo", "prima"), 2: ("secondo", "seconda"), 3: ("terzo", "terza"),
                    4: ("quarto", "quarta"), -1: ("ultimo", "ultima")}
OTHER_KINDS = frozenset({"stall", "concession", "historical_capacity", "aggregate"})
WEEKDAYS_NORMAL = ("lunedi","martedi","mercoledi","giovedi",
                   "venerdi","sabato","domenica")
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
ID_RE = re.compile(r"[a-z][a-z0-9-]{3,70}")


def canonical(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold()
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",text)).strip()


def slug_part(value):
    return canonical(value).replace(" ","-")[:100]


def digest(value):
    return hashlib.sha256(json.dumps(
        value,sort_keys=True,ensure_ascii=False,separators=(",",":")
    ).encode("utf-8")).hexdigest()


def _public_https(url):
    try:
        p = urlsplit(str(url))
        return bool(p.scheme == "https" and p.hostname and
                    not p.username and not p.password and
                    p.port in (None,443) and not p.fragment)
    except ValueError:
        return False


def _short_texts(values, low, high, limit):
    return (isinstance(values,list) and 1<=len(values)<=limit
            and all(isinstance(v,str) and low<=len(v.strip())<=high for v in values))


def validate_multi_town_options(item):
    """Declarative options for official calendars that list many municipalities."""
    columns=item["schema_columns"]
    if item.get("municipality_field") is not None and (
            item["municipality_field"] not in columns or item.get("province") is not None):
        raise ValueError("Row municipality column must be reviewed; ISTAT supplies its province")
    if (item.get("format")=="PDF") != (item.get("pdf_header") is not None):
        raise ValueError("A PDF table needs its exact reviewed header, and only PDFs have one")
    if item.get("pdf_header") is not None and (
            not isinstance(item["pdf_header"],list) or len(item["pdf_header"])!=len(columns)
            or any(not isinstance(cell,str) or len(cell)>200 for cell in item["pdf_header"])):
        raise ValueError("PDF header must name every reviewed column")
    for flag in ("weekday_lists","new_market_requires_free_town_day","pdf_header_repeats"):
        if item.get(flag,False) not in (True,False):
            raise ValueError("Invalid boolean source option: "+flag)
    if "pdf_header_repeats" in item and item.get("pdf_header") is None:
        raise ValueError("Only a PDF table has a header to repeat")
    if item.get("hours_text_format") is not None and (
            item["hours_text_format"]!="italian_clock_range" or not item.get("hours_text_field")):
        raise ValueError("Unknown hours text format")
    excluded=item.get("exclude_rows_containing",{})
    if (not isinstance(excluded,dict) or len(excluded)>4
            or any(k not in columns or not _short_texts(v,3,40,6) for k,v in excluded.items())):
        raise ValueError("Invalid non-market row exclusion")
    for option,fields in (("empty_name_template",("{citta}",)),
                          ("place_name_template",("{citta}","{nome}"))):
        template=item.get(option)
        if template is not None and (not isinstance(template,str) or not 8<=len(template)<=80
                                     or any(field not in template for field in fields)):
            raise ValueError("Invalid market name template")
    found=item.get("resource_discovery")
    if found is not None:
        if (not isinstance(found,dict) or set(found)!={"link_text","href_pattern"}
                or not isinstance(found["link_text"],str) or not 3<=len(found["link_text"])<=120
                or not isinstance(found["href_pattern"],str) or "{year}" not in found["href_pattern"]
                or len(found["href_pattern"])>300
                or item.get("source_date_strategy")!="landing_page_year_v1"):
            raise ValueError("Unreviewed yearly document discovery rule")
        try:
            re.compile(found["href_pattern"].replace("{year}","2026"))
        except re.error as exc:
            raise ValueError("Invalid yearly document link pattern") from exc
    fill=item.get("existing_market_fill")
    if item.get("row_kind")==MONTH_KIND and fill is None:
        raise ValueError("A monthly calendar names the market categories it is about")
    # A monthly calendar names which markets it may fill (antiques, not farmers).
    if fill is not None and (
            not isinstance(fill,dict) or "max_records_per_run" not in fill
            or set(fill)-{"max_records_per_run","categories"}
            or type(fill["max_records_per_run"]) is not int
            or not 1<=fill["max_records_per_run"]<=500
            or item.get("row_kind") not in MARKET_KINDS
            or ("categories" in fill or item.get("row_kind")==MONTH_KIND) and (
                not isinstance(fill.get("categories"),list) or not fill["categories"]
                or not set(fill["categories"])<=CATEGORIES)):
        raise ValueError("Invalid existing-market field fill policy")


def pdf_table_rows(profile, blob):
    """Read every table row of a reviewed PDF calendar (pdfplumber, MIT).

    Each page must repeat the exact reviewed header with the reviewed number
    of columns. Only blank or one-cell title rows may precede it; anything else
    means the publisher changed the layout and the contract needs a review.
    Rows below the header are returned as-is (totals rows fail row validation).
    With "pdf_header_repeats": false the header is printed on the first page
    only; later pages continue its table and may not print it again.
    """
    try:
        import pdfplumber
    except ImportError as exc:  # isolated like any unreadable source
        raise ValueError("PDF reader unavailable: install backend/requirements.txt") from exc
    header=[canonical(cell) for cell in profile["pdf_header"]]
    columns=profile["schema_columns"]
    repeats=profile.get("pdf_header_repeats",True)
    rows=[]
    try:
        with pdfplumber.open(io.BytesIO(blob)) as pdf:
            if not 1<=len(pdf.pages)<=MAX_PDF_PAGES:
                raise ValueError("PDF page count outside the reviewed bound")
            for number,page in enumerate(pdf.pages):
                headers=0 if repeats or number==0 else 1
                for table in page.extract_tables():
                    for raw in table:
                        cells=[" ".join(str(c or "").split()) for c in raw]
                        if len(cells)!=len(columns):
                            raise ValueError("Publisher changed PDF table columns")
                        if not any(cells):
                            continue
                        if [canonical(c) for c in cells]==header:
                            headers+=1
                        elif sum(bool(c) for c in cells)<=1 and not headers:
                            continue  # title or spacer above the header
                        elif headers:
                            rows.append(dict(zip(columns,cells)))
                        else:
                            raise ValueError("PDF data row before the reviewed header")
                if headers!=1:
                    raise ValueError("Every PDF page needs exactly one reviewed header")
    except ValueError:
        raise
    except Exception as exc:  # malformed/hostile PDF: treat as unreadable source
        raise ValueError("Unreadable publisher PDF: "+type(exc).__name__) from exc
    return rows


def weekdays(value):
    """'martedì, venerdì' / 'lunedì e giovedì' -> (1, 4); anything else -> None."""
    parts=[canonical(p) for p in re.split(r",|\s+e\s+",str(value or ""))]
    if not parts or any(p not in WEEKDAYS_NORMAL for p in parts):
        return None
    return tuple(sorted({WEEKDAYS_NORMAL.index(p) for p in parts}))


_CLOCK=r"([01]?\d|2[0-3])(?:\s*[.,:;]\s*([0-5]\d))?"
_CLOCK_RANGE=re.compile(r"(?:dalle\s+(?:ore\s*)?)?"+_CLOCK+
                        r"\s*(?:-|–|al{1,2}e\s+(?:ore\s*)?)\s*"+_CLOCK)


def clock_range(value):
    """'dalle ore 7,30 alle ore 13,30' / '7.30-13.30' -> '07:30–13:30'.

    One complete range only: seasonal, split or qualified hours return None.
    """
    match=_CLOCK_RANGE.fullmatch(" ".join(str(value or "").casefold().split()))
    if not match:
        return None
    h1,m1,h2,m2=(int(x or 0) for x in match.groups())
    if (h1,m1)>=(h2,m2):
        return None
    return f"{h1:02d}:{m1:02d}–{h2:02d}:{m2:02d}"


def istat_municipality(region, name):
    """Exact ISTAT 2026 spelling and province for a municipality, or None."""
    from catalog_quality_report import key
    return _istat_registry().get(region,{}).get(key(name))


def _istat_registry():
    global _ISTAT
    if _ISTAT is None:
        from municipality_reconciliation import trusted_municipalities
        _ISTAT=trusted_municipalities(json.loads(
            (Path(__file__).resolve().parent/"data/istat-comuni-2026.json").read_text("utf-8")))
    return _ISTAT


_ISTAT=None


def excluded_row(profile, row):
    return any(canonical(token) in canonical(row.get(field))
               for field,tokens in profile.get("exclude_rows_containing",{}).items()
               for token in tokens)


def validate_contracts(config):
    if (not isinstance(config,dict) or config.get("schema")!=SCHEMA
            or config.get("publication_role")!="review_only"
            or not isinstance(config.get("normalized_profiles"),list)
            or not isinstance(config.get("raw_profiles"),list)
            or len(config["normalized_profiles"])>MAX_NORMALIZED_PROFILES
            or len(config["raw_profiles"])>MAX_RAW_PROFILES):
        raise ValueError("Unapproved source-level contract registry")
    ids=set()
    for kind, rows in (("normalized",config["normalized_profiles"]),
                       ("raw",config["raw_profiles"])):
        for item in rows:
            if not isinstance(item,dict):
                raise ValueError("Source contract entry is not an object")
            sid=item.get("id")
            if not isinstance(sid,str) or not ID_RE.fullmatch(sid) or sid in ids:
                raise ValueError("Repeated/invalid source contract ID")
            ids.add(sid)
            minimum=item.get("min_records" if kind=="normalized" else "min_rows")
            maximum=item.get("max_records" if kind=="normalized" else "max_rows")
            if (item.get("row_kind") not in MARKET_KINDS|OTHER_KINDS
                    or item.get("publication_mode") not in
                       ("shadow_only","existing_adapter_only","approved_dev_only")
                    or not isinstance(item.get("publisher"),str)
                    or not item["publisher"] or
                    type(minimum) is not int or type(maximum) is not int
                    or not 0<=minimum<=maximum<=MAX_ROWS):
                raise ValueError("Untrusted dataset granularity, bounds or publication policy")
            if kind=="normalized":
                if (item.get("publication_mode")!="existing_adapter_only"
                    or not item.get("identity_prefix")
                    or item.get("region") is None
                    or not isinstance(item.get("source_pages",[]),list)
                    or not isinstance(item.get("source_hosts",[]),list)
                    or not (item.get("source_pages") or item.get("source_hosts"))
                    or any(not _public_https(url) for url in item.get("source_pages",[]))
                    or any(not re.fullmatch(r"[a-z0-9.-]+",host)
                           for host in item.get("source_hosts",[]))
                    or not item.get("source_timestamp_scope")
                    or not isinstance(item.get("expected_precision"),list)):
                    raise ValueError("Unreviewed normalized-source adapter contract")
            else:
                mode=item.get("publication_mode")
                if (mode not in ("shadow_only","approved_dev_only") or
                        (mode=="shadow_only" and (
                            item.get("legal_reuse_reviewed") is not False or
                            item.get("max_new_ids_per_run")!=0)) or
                        (mode=="approved_dev_only" and (
                            item.get("legal_reuse_reviewed") is not True or
                            type(item.get("max_new_ids_per_run")) is not int or
                            not 1 <= item["max_new_ids_per_run"] <= 250)) or
                        item.get("coordinates")!="ignored_unless_independently_source_verified" or
                        item.get("source_date_scope")!="dataset_not_per_market" or
                        not safe_url(item.get("resource_url")) or
                        not _public_https(item.get("attribution_url")) or
                        item.get("format") not in ("CSV","JSON","PDF") or
                        type(item.get("max_bytes")) is not int or
                        not 100<=item["max_bytes"]<=(
                            MAX_DOCUMENT_BYTES if item.get("format")=="PDF" else MAX_PROFILE_BYTES) or
                        not isinstance(item.get("schema_columns"),list) or
                        not 1<=len(item["schema_columns"])<=100 or
                        len(set(item["schema_columns"]))!=len(item["schema_columns"]) or
                        not isinstance(item.get("identity_fields"),list) or
                        not 1<=len(item["identity_fields"])<=4 or
                        not set(item["identity_fields"]).issubset(item["schema_columns"]) or
                        item.get("catalog_slug_prefix") is None or
                        # One municipality per file, or a reviewed column that
                        # names each row's municipality (multi-town calendars).
                        (item.get("municipality") is None) == (item.get("municipality_field") is None) or
                        item.get("region") is None or
                        not isinstance(item.get("source_dataset_date"),str) or
                        type(item.get("max_source_age_days")) is not int or
                        not 0<=item["max_source_age_days"]<=730):
                    raise ValueError("Raw source cannot be approved without schema/rights review")
                date.fromisoformat(item["source_dataset_date"])
                validate_strategy(item)
                forecast_age=item.get("max_forecast_source_age_days",item["max_source_age_days"])
                if (type(forecast_age) is not int
                        or not 0<=forecast_age<=item["max_source_age_days"]):
                    raise ValueError("Forecast age exceeds reviewed source date quality")
                if item.get("json_container") is not None:
                    if (item["format"]!="JSON"
                            or item["json_container"]!="opendatasoft_v1"
                            or not re.fullmatch(r"[a-z0-9-]{3,80}",str(item.get("api_dataset_id") or ""))
                            or parse_qs(urlsplit(item["resource_url"]).query).get("dataset")!=[item["api_dataset_id"]]
                            or "recordid" not in item["schema_columns"]
                            or "recordid" not in item["identity_fields"]):
                        raise ValueError("Unknown publisher JSON envelope or identity")
                for fields_key in ("venue_identity_fields",):
                    fields=item.get(fields_key,[])
                    if (not isinstance(fields,list) or len(fields)>5
                            or any(f not in item["schema_columns"] for f in fields)
                            or len(set(fields))!=len(fields)):
                        raise ValueError("Unreviewed physical venue key")
                market_rules=item.get("market_filters_any",[])
                if (not isinstance(market_rules,list) or len(market_rules)>8
                        or any(not isinstance(r,dict) or not r or len(r)>4 or
                               any(k not in item["schema_columns"]
                                   or not isinstance(v,str) or not 1<=len(v)<=80
                                   for k,v in r.items()) for r in market_rules)):
                    raise ValueError("Unreviewed explicit market type filter")
                held=item.get("hold_address_contains",[])
                if (not isinstance(held,list) or len(held)>6
                        or any(not isinstance(s,str) or not 3<=len(s)<=80 for s in held)):
                    raise ValueError("Invalid unsafe address hold rule")
                city_floor=item.get("generic_city_aggregate_min_distinct_addresses",0)
                if type(city_floor) is not int or not 0<=city_floor<=100 or (
                        city_floor and city_floor<10):
                    raise ValueError("Generic city override requires many official venues")
                if item.get("hours_text_field") is not None and (
                        item["hours_text_field"] not in item["schema_columns"]):
                    raise ValueError("Unreviewed source hour text field")
                cmap=item.get("category_map")
                if cmap is not None:
                    if (not isinstance(cmap,dict)
                            or cmap.get("field") not in item["schema_columns"]
                            or not isinstance(cmap.get("values"),dict)
                            or len(cmap["values"])>12
                            or any(not isinstance(k,str) or not k
                                   or v not in CATEGORIES
                                   for k,v in cmap["values"].items())):
                        raise ValueError("Unreviewed market category mapping")
                if item.get("category","misto") not in CATEGORIES:
                    raise ValueError("Unreviewed market category")
                validate_multi_town_options(item)
                monthly=item.get("row_kind")==MONTH_KIND
                if monthly and (item.get("weekday_field") is not None
                                or item.get("recurrence_field") not in item["identity_fields"]):
                    raise ValueError("A monthly calendar row needs its recurrence in stable identity")
                for name in ("name_field","recurrence_field" if monthly else "weekday_field"):
                    # No name column: every row is named by the reviewed template.
                    if item.get(name) not in item["schema_columns"] and not (
                            name=="name_field" and item.get(name) is None
                            and item.get("empty_name_template")):
                        raise ValueError("Market source field missing from inspected schema")
                for field in item.get("street_fields",[])+item.get("hours_fields",[]):
                    if field not in item["schema_columns"]:
                        raise ValueError("Source address/hour mapping not in reviewed schema")
                if len(item.get("hours_fields",[])) not in (0,2):
                    raise ValueError("Half a time range cannot be treated as hours")
                if (item.get("format")=="CSV" and item.get("delimiter") not in (",",";","\t")):
                    raise ValueError("Unsafe CSV delimiter")
                if item.get("row_kind") not in MARKET_KINDS and item.get("market_filter"):
                    raise ValueError("Administrative/statistical source is not a visitable market")
                filt=item.get("market_filter") or {}
                if filt and (filt.get("field") not in item["schema_columns"] or
                             not isinstance(filt.get("starts_with"),str) or
                             not filt["starts_with"]):
                    raise ValueError("Unreviewed raw source venue filter")
                # An unreviewed file can't invent a verified venue GPS point.
                if item.get("row_kind")=="market_venue_day" and item["weekday_field"] not in item["identity_fields"]:
                    raise ValueError("Multiple weekday records need weekday in stable identity")
                if not SLUG_RE.fullmatch(item["catalog_slug_prefix"]+"a"):
                    raise ValueError("Unapproved source-specific stable ID prefix")
    return config


def parse_rows(profile,blob):
    if (not isinstance(blob,bytes) or not blob or
            len(blob)>profile["max_bytes"]):
        raise ValueError("Full publisher file exceeds exact bounded size")
    if profile["format"]=="PDF":
        rows=pdf_table_rows(profile,blob)
        if not profile["min_rows"]<=len(rows)<=profile["max_rows"]:
            raise ValueError("Incomplete/expanded publisher snapshot outside source contract")
        return rows
    try:
        decoded=blob.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Invalid publisher text encoding") from exc
    if profile["format"]=="CSV":
        r=csv.DictReader(io.StringIO(decoded),delimiter=profile["delimiter"])
        fields=list(r.fieldnames or [])
        if (profile.get("strict_schema") is True and
            (len(fields)!=len(profile["schema_columns"]) or
             set(fields)!=set(profile["schema_columns"]))):
            raise ValueError("Publisher changed CSV columns: require a reviewed contract update")
        if any(not f or f not in profile["schema_columns"] for f in fields):
            raise ValueError("Missing/extra CSV schema fields")
        rows=list(r)
        if any(None in row or any(v is None for v in row.values()) for row in rows):
            raise ValueError("Truncated or malformed publisher CSV row")
    else:
        raw=json.loads(decoded)
        if profile.get("json_container")=="opendatasoft_v1":
            if (not isinstance(raw,dict) or type(raw.get("nhits")) is not int
                    or not isinstance(raw.get("records"),list)
                    or raw["nhits"]!=len(raw["records"])):
                raise ValueError("Incomplete Opendatasoft publisher query snapshot")
            rows=[]
            for item in raw["records"]:
                if (not isinstance(item,dict)
                        or item.get("datasetid")!=profile["api_dataset_id"]
                        or not isinstance(item.get("fields"),dict)
                        or not isinstance(item.get("recordid"),str)
                        or not re.fullmatch(r"[0-9a-f]{40}",item["recordid"])):
                    raise ValueError("Missing official Opendatasoft stable record identity")
                fields=item["fields"]
                if not set(fields).issubset(profile["schema_columns"]):
                    raise ValueError("Unexpected Opendatasoft source field")
                row={col:fields.get(col) for col in profile["schema_columns"]
                     if col!="recordid"}
                row["recordid"]=item["recordid"]
                rows.append(row)
        else:
            if isinstance(raw,dict):
                raw=raw.get("records")
            if not isinstance(raw,list) or not all(isinstance(x,dict) for x in raw):
                raise ValueError("JSON publisher snapshot has no real venue records")
            rows=raw
        if any(set(row)!=set(profile["schema_columns"]) for row in rows):
            raise ValueError("Publisher changed JSON object schema")
    if not profile["min_rows"]<=len(rows)<=profile["max_rows"]:
        raise ValueError("Incomplete/expanded publisher snapshot outside source contract")
    return rows


def weekday(value):
    normalized=canonical(value)
    if normalized in WEEKDAYS_NORMAL:
        return WEEKDAYS_NORMAL.index(normalized)
    return None


def parse_hour(value):
    raw=str(value or "").strip()
    if re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",raw):
        return raw
    return None


def candidate_record(profile,row,*,today,source_date=None):
    """In-memory conservative source candidate; NEVER marks a market verified."""
    if profile["row_kind"] not in MARKET_KINDS:
        return None,None,None
    filter_rule=profile.get("market_filter") or {}
    if filter_rule and not str(row.get(filter_rule["field"]) or "").startswith(filter_rule["starts_with"]):
        return None,"not_a_market_venue",None
    typed_filters=profile.get("market_filters_any",[])
    if typed_filters and not any(
            all(canonical(row.get(key))==canonical(value) for key,value in rule.items())
            for rule in typed_filters):
        return None,"not_a_market_venue",None
    if excluded_row(profile,row):
        return None,"not_a_market_venue",None
    if profile.get("municipality_field"):
        place=istat_municipality(profile["region"],row.get(profile["municipality_field"]))
        if place is None:
            return None,"municipality_not_in_istat",None
        city,province=place
    else:
        city,province=profile["municipality"],profile["province"]
    identity=[canonical(row.get(col)) for col in profile["identity_fields"]]
    name=str(row.get(profile.get("name_field")) or "").strip()
    if not name:
        name=str(profile.get("empty_name_template") or "").replace("{citta}",city)
    elif profile.get("place_name_template") and "mercat" not in canonical(name):
        # A bare locality/street ("Capoluogo", "Marsango") is not a market name.
        name=profile["place_name_template"].replace("{citta}",city).replace("{nome}",name)
    road=" ".join(str(row.get(col) or "").strip() for col in profile.get("street_fields",[])).strip()
    if (not all(identity) or not name or not road or
            len(name)>160 or len(road)>240):
        return None,"incomplete_venue_identity",None
    if len(profile["identity_fields"])==1:
        slug=profile["catalog_slug_prefix"]+slug_part(row[profile["identity_fields"][0]])
    else:
        slug=profile["catalog_slug_prefix"]+digest(identity)[:18]
    if not SLUG_RE.fullmatch(slug):
        return None,"bad_publisher_identity",None
    monthly=profile["row_kind"]==MONTH_KIND
    if monthly:
        # Exclusions, month lists or dates the rule can't carry: no calendar.
        rule=complete_monthly_rule(row.get(profile["recurrence_field"]))
        d=rule["weekday"] if rule else None
    elif profile.get("weekday_lists"):
        days=weekdays(row.get(profile["weekday_field"]))
        d=list(days) if days else None
    else:
        d=weekday(row.get(profile["weekday_field"]))
        days=None if d is None else (d,)
    start,end=(None,None)
    if profile.get("hours_fields"):
        a,b=profile["hours_fields"]
        start,end=parse_hour(row.get(a)),parse_hour(row.get(b))
        if start and end and start>=end:start=end=None
    # The caller supplies a resolved snapshot date during ingestion. Pure
    # parser previews may still inspect the reviewed minimum without fetching.
    updated=date.fromisoformat(source_date or profile["source_dataset_date"])
    age=(today-updated).days
    if age < 0:
        return None,"dataset_date_in_future",None
    forecast_eligible=(d is not None and age<=profile.get(
        "max_forecast_source_age_days",profile["max_source_age_days"]))
    if not forecast_eligible:
        recurrence="Calendario da verificare"
    elif monthly:
        # domenica is the only feminine weekday: "prima domenica", "primo sabato".
        recurrence=("mensile - "+MONTHLY_ORDINALS[rule["ordinal"]][d==6]+" "
                    +WEEKDAYS[d]+" del mese")
    else:
        recurrence="settimanale - "+", ".join(WEEKDAYS[x] for x in days)
    raw_hours=""
    if profile.get("hours_text_field"):
        raw_hours=preserve_hours_text(row.get(profile["hours_text_field"]))
        span=clock_range(raw_hours) if profile.get("hours_text_format") else None
        match=re.fullmatch(r"((?:[01]\d|2[0-3]):[0-5]\d)\s*[-–]\s*((?:[01]\d|2[0-3]):[0-5]\d)",raw_hours)
        if span:
            start,end=span.split("–")
        elif match and match.group(1)<match.group(2):
            start,end=match.groups()
        elif raw_hours:
            # A separate numeric range cannot discard qualifications in the
            # publisher's text field, including seasonal hours or closures.
            start=end=None
    if start and end:
        hours=preserve_hours_text(start+"–"+end, qualification="(da verificare con il Comune)")
    elif profile.get("hours_text_format"):
        # Only one complete clock range is published; seasonal, split or
        # damaged PDF text stays out of the card (it is still fingerprinted).
        hours=""
    else:
        hours=preserve_hours_text(
            raw_hours, qualification="(indicazioni della fonte; da verificare con il Comune)")
    c_map=profile.get("category_map") or {}
    category=next((value for key,value in c_map.get("values",{}).items()
                   if canonical(row.get(c_map["field"]))==canonical(key)),
                  profile.get("category","misto"))
    venue={
        "slug":slug,"nome":name[:160],
        "citta":city,"provincia":province,
        "regione":profile["region"],"indirizzo":road,
        "lat":None,"lng":None,"position_quality":"sconosciuta",
        "navigazione_sospesa_motivo":NAVIGATION_HOLD,
        "categoria":category,"tags":["mercato comunale"],"status":"non_confermato",
        "date":[],"date_quality":"sconosciuta",
        "ricorrenza_testo":recurrence,
        "orario_testo":hours,
        "descrizione":(
          "Sede in un dataset comunale, non apertura confermata. "
          "Data riferita all'intero dataset: "+updated.isoformat()+
          ". Coordinate e percorso stradale non verificati."
        ),
        "fonte":profile["publisher"]+" — dati ufficiali; apertura non confermata",
        "url_fonte":profile["attribution_url"],
        "aggiornato_il":updated.isoformat(),"aggiornamento_ambito":"dataset",
        "verificato_il":"","confidence":0,
    }
    facts={"name":canonical(name),"address":canonical(road),
           "day":d,"start":start,"end":end,
           "publisher_dataset_date":updated.isoformat()}
    if monthly:
        facts["ordinal"]=rule["ordinal"] if rule else None
    if raw_hours and not (start and end):
        facts["hours_text"]=raw_hours
    facthash=digest(facts)
    issue="schedule_unknown" if d is None else (
        "source_old_no_future_forecast" if not forecast_eligible else None)
    if profile.get("hours_fields") and not (start and end):
        issue=issue or "hours_missing_or_invalid"
    return venue,issue,facthash


def _baseline(catalog):
    if not isinstance(catalog,list) or not 1<=len(catalog)<=100000:
        raise ValueError("Invalid original market catalog for source reconciliation")
    by_slug={}
    places={}
    for x in catalog:
        sid=x.get("slug")
        if not isinstance(sid,str) or not sid or sid in by_slug:
            raise ValueError("Untrusted catalog ID set")
        by_slug[sid]=x
        key=(canonical(x.get("regione")),canonical(x.get("citta")),
             canonical(x.get("indirizzo")))
        if key[-1]:places.setdefault(key,[]).append(sid)
    return by_slug,places


def inspect_raw(profile,blob,catalog,previous=None,today=None,*,source_date_proof=None,read_on=None):
    today=today or date.today()
    read_on=str(read_on or today)
    source_date=resolve_source_date(profile, proof=source_date_proof, blob=blob,
                                    read_on=read_on, today=today)
    rows=parse_rows(profile,blob)
    prior=previous or {}
    if prior and (prior.get("schema")!=1 or
                  prior.get("source_id")!=profile["id"] or
                  prior.get("source_url")!=profile["resource_url"]):
        raise ValueError("History belongs to another source; refuse comparison")
    old_ids,places=_baseline(catalog)
    hashes={}
    counts=Counter()
    preview=[]
    distinct_names=set()
    accepted_ids=set()
    for row in rows:
        counts["rows_observed"]+=1
        if profile["row_kind"] in OTHER_KINDS:
            counts["non_venue_administrative_rows"]+=1
            continue
        venue,reason,fingerprint=candidate_record(profile,row,today=today,source_date=source_date)
        if venue is None:
            counts[reason]+=1
            continue
        key=venue["slug"]
        if key in accepted_ids:
            counts["duplicate_publisher_market_identity"]+=1
            # A duplicate name may mean several concessions or several
            # physical venues. NEVER merge them by row number or overwrite.
            continue
        accepted_ids.add(key)
        distinct_names.add(canonical(venue["nome"]))
        ident=digest({"publisher":profile["id"],"stable_slug":key})
        hashes[ident]=fingerprint
        counts["distinct_market_identities"]+=1
        if reason:counts["needs_review_"+reason]+=1
        if key in old_ids:
            counts["already_in_catalog_exact_source_id"]+=1
        else:
            counts["identity_not_in_existing_catalog"]+=1
            vk=(canonical(venue["regione"]),canonical(venue["citta"]),
                canonical(venue["indirizzo"]))
            if places.get(vk):
                counts["possible_same_street_other_publisher"]+=1
            if len(preview)<MAX_MARKDOWN_EXAMPLES:
                preview.append({"stable_identity_hash":ident[:16],
                                "review_state":"possible_existing_venue"
                                if places.get(vk) else "source_level_new_candidate",
                                "publication_permission":"none"})
        # A source-level review must never change status, opening verification
        # or geographic coordinates; only a signed DEV importer can do so.
    if counts["duplicate_publisher_market_identity"]:
        counts["rejected_identity_collisions"]=counts["duplicate_publisher_market_identity"]
    before=prior.get("fingerprints",{}) if prior else {}
    if not isinstance(before,dict):
        raise ValueError("Prior source identity hashes malformed")
    current=set(hashes);older=set(before)
    # Missing source rows are not closures; old catalogue entries remain.
    diff={
        "first_observation":not bool(prior),
        "added_source_identities_since_last_scan":len(current-older) if prior else 0,
        "missing_source_identities_since_last_scan":len(older-current) if prior else 0,
        "changed_source_identities_since_last_scan":sum(
           before[key]!=hashes[key] for key in current&older
        ) if prior else 0,
        "same_source_identities_since_last_scan":sum(
           before[key]==hashes[key] for key in current&older
        ) if prior else 0,
    }
    age=(today-date.fromisoformat(source_date)).days
    report={
        "schema":1,"source_id":profile["id"],"publisher":profile["publisher"],
        "source_url":profile["resource_url"],"publisher_dataset_date":source_date,
        "source_read_on":read_on,
        "publisher_data_age_days":age,
        "source_data_scope":profile["source_date_scope"],
        "license_reviewed_for_automatic_publication":False,
        "row_kind":profile["row_kind"],
        "source_snapshot_sha256":hashlib.sha256(blob).hexdigest(),
        "profile_fingerprint":digest(profile),
        "source_schema_columns_sha256":digest(sorted(profile["schema_columns"])),
        "catalog_records_compared":len(catalog),
        "counts":dict(sorted(counts.items())),
        "market_names_distinct_not_new_events":len(distinct_names),
        "fingerprints":dict(sorted(hashes.items())),
        "diff":diff,
        "examples_hashes_only":preview,
        "individual_market_openings_verified":0,
        "catalog_records_imported":0,
        "catalog_records_modified":0,
        "existing_record_ids_deleted":0,
        "new_precise_coordinates":0,
        "new_directions_enabled":0,
        "review_required":True,
        "source_data_marked_current_by_fetch_time":False,
    }
    if source_date_proof is not None:
        report["source_date_proof"]=source_date_proof
    return report


def inspect_normalized(profile, records, catalog, prior=None, review_metrics=None,
                       reviewed_excluded_ids=None):
    if not isinstance(records,list) or not profile["min_records"]<=len(records)<=profile["max_records"]:
        raise ValueError("Source record counts beyond contract: "+profile["id"])
    by_slug,_=_baseline(catalog)
    seen=set()
    current={}
    counts=Counter()
    for row in records:
        if not isinstance(row,dict):
            raise ValueError("Publisher adapter record not a market object")
        sid=row.get("slug")
        if (not isinstance(sid,str) or not sid.startswith(profile["identity_prefix"])
                or sid in seen or not SLUG_RE.fullmatch(sid)):
            raise ValueError("Source namespace collision or duplicate identity: "+profile["id"])
        seen.add(sid)
        source_url=row.get("url_fonte","")
        hostname=urlsplit(str(source_url)).hostname
        if (not _public_https(source_url) or
            source_url not in profile.get("source_pages",[]) and
            hostname not in profile.get("source_hosts",[]) or
            row.get("regione")!=profile["region"] or
            row.get("date_quality") in ("confermata","riportata") or
            row.get("verificato_il") or
            row.get("status") in ("attivo","annullato","archiviato") or
            row.get("position_quality") not in profile["expected_precision"]):
            raise ValueError("Publisher adapter violated original venue/date/source contract: "+sid)
        counts["source_records_scanned"]+=1
        if sid in by_slug:counts["existing_ids_seen_in_catalog"]+=1
        else: counts["source_ids_not_yet_in_catalog"]+=1
        if row.get("orario_testo"):counts["hours_present"]+=1
        if row.get("indirizzo"):counts["address_present"]+=1
        if row.get("date_quality")=="prevista":counts["forecast_only_not_confirmed"]+=1
        if row.get("lat") is not None:counts["coordinates_not_opening_proof"]+=1
        current[digest({"source":profile["id"],"stable_slug":sid})]=digest({
            "source_id":sid,"name":canonical(row.get("nome")),
            "city":canonical(row.get("citta")),"address":canonical(row.get("indirizzo")),
            "hours":str(row.get("orario_testo") or ""),
            "recurrence":str(row.get("ricorrenza_testo") or ""),
            "dataset_date":str(row.get("aggiornato_il") or "")[:10],
        })
    before=(prior or {}).get("fingerprints",{})
    if before and not isinstance(before,dict):
        raise ValueError("Invalid previous normalized market source state")
    missing=set(before)-set(current)
    screened=review_metrics or {}
    if not isinstance(screened,dict):
        raise ValueError("Untrusted official-source overlap status")
    quarantine=screened.get("quarantined_review",0)
    if (type(quarantine) is not int or quarantine<0
            or quarantine>profile["max_records"]):
        raise ValueError("Untrusted source overlap quarantine count")
    # Counts alone NEVER prove which source IDs an overlap screen held.
    # Exact IDs are ephemeral and come from the reviewed source cohort, not
    # user-provided metadata. Only aggregate counts/digest enter the report.
    source_screening=reconcile_reviewed_source_ids(
        seen,set(by_slug),
        reviewed_excluded_ids=reviewed_excluded_ids,
        reviewed_excluded_count=quarantine,
        reviewed_accepted_count=screened.get("accepted_after_overlap_qa")
        if reviewed_excluded_ids is not None else None,
    )
    return {
        "schema":1,"source_id":profile["id"],"publisher":profile["publisher"],
        "source_data_scope":profile["source_timestamp_scope"],
        "row_kind":profile["row_kind"],
        "profile_fingerprint":digest(profile),
        "catalog_records_compared":len(catalog),
        "counts":dict(sorted(counts.items())),
        "source_screening":source_screening,
        "fingerprints":dict(sorted(current.items())),
        "diff":{
           "first_observation":not bool(prior),
           "new_source_identities_since_last_scan":len(set(current)-set(before)) if prior else 0,
           "missing_source_identities_since_last_scan":len(missing) if prior else 0,
           "changed_existing_identities_since_last_scan":sum(
             current[k]!=before[k] for k in set(current)&set(before)
           ) if prior else 0,
        },
        "vanished_source_ids_do_not_imply_market_closed":True,
        "confirmed_events_created":0,"market_records_imported":0,
        "market_records_edited":0,"market_ids_deleted":0,
    }


def run(config,catalog,*,source_dir=None,previous=None,source_status=None,
        source_dispositions=None,probe_raw=False,stage_raw=False,
        raw_fetch=limited_fetch,today=None,raw_read_on=None):
    today=today or date.today()
    raw_read_on=str(raw_read_on or datetime.now(timezone.utc).date())
    if stage_raw and not probe_raw:
        raise ValueError("Staging requires a complete newly sampled source snapshot")
    validate_contracts(config)
    by_old = (previous or {}).get("sources",{})
    if previous is not None and (
        previous.get("schema")!=1 or previous.get("source_contract_schema")!=1
        or not isinstance(by_old,dict)):
        raise ValueError("Previous source lifecycle report is invalid")
    reports={}
    status=Counter()
    if source_dir is not None:
        root=Path(source_dir)
        for profile in config["normalized_profiles"]:
            sid=profile["id"];cached=root/(sid+".json")
            if not cached.is_file():
                status["source_snapshot_absent_not_market_closure"]+=1
                continue
            rec=json.loads(cached.read_text("utf-8"))
            reports[sid]=inspect_normalized(
                profile,rec,catalog,by_old.get(sid),
                (source_status or {}).get(sid),
                (source_dispositions or {}).get(sid),
            )
            status["existing_adapter_snapshots_inspected"]+=1
    if probe_raw:
        enabled=[p for p in config["raw_profiles"] if p.get("enabled") is True]
        if len(enabled)>MAX_ENABLED_RAW_PROFILES:
            raise ValueError("Unbounded daily raw source probe quota")
        for profile in enabled:
            sid=profile["id"]
            try:
                from source_contract_activation import read_source_snapshot
                blob,date_proof=read_source_snapshot(
                    profile,fetch=raw_fetch,read_on=raw_read_on,today=today)
                reports[sid]=inspect_raw(profile,blob,catalog,by_old.get(sid),today,
                                         source_date_proof=date_proof,read_on=raw_read_on)
                if stage_raw and profile["row_kind"] in MARKET_KINDS:
                    # Reuse the SAME downloaded bytes; never publish candidate
                    # rows and never re-request the source.
                    from source_contract_ingest import stage as stage_source_venues
                    staged,source_stage=stage_source_venues(
                        profile,blob,catalog,today=today,
                        observed_source_sha256=reports[sid]["source_snapshot_sha256"],
                        source_date_proof=date_proof,read_on=raw_read_on,
                    )
                    if (source_stage.get("existing_market_identities_deleted")!=0
                            or source_stage.get("verified_openings_created")!=0
                            or source_stage.get("precise_coordinates_created")!=0
                            or source_stage.get("safe_candidates_not_published")!=len(staged)):
                        raise ValueError("Generic staging falsely published or verified a market")
                    reports[sid]["source_stage"]=source_stage
                    status["source_only_stage_reviews"]+=1
                status["source_level_raw_profiles_checked"]+=1
            except (ValueError,OSError,TimeoutError,HTTPException) as exc:
                # Unavailable HTTPS endpoint != vanished market. A parser
                # ValueError is DISTINCT: the publisher may have changed
                # schema, granularity or ID meaning. Never treat it as success.
                is_contract_error=isinstance(exc,ValueError)
                classification=("contract_change_needs_review" if is_contract_error
                                else "transport_unavailable")
                if sid in by_old:
                    reports[sid]={**by_old[sid],
                                  "stale_snapshot_carry_forward":True,
                                  "last_check_status":classification,
                                  "last_check_error_class":type(exc).__name__}
                else:
                    reports[sid]={"schema":1,"source_id":sid,
                                  "publisher":profile["publisher"],
                                  "source_url":profile["resource_url"],
                                  "unavailable_no_market_inference":True,
                                  "last_check_status":classification,
                                  "last_check_error_class":type(exc).__name__,
                                  "fingerprints":{}}
                if is_contract_error:
                    status["raw_schema_or_identity_change_requires_review"]+=1
                else:
                    status["raw_source_unavailable_no_market_inference"]+=1
    return {
       "schema":1,"source_contract_schema":1,
       "reference_date":today.isoformat(),
       "registry_sha256":digest(config),
       "read_only":True,
       "market_imports":0,"market_updates":0,"market_confirmations":0,
       "market_identity_deletions":0,
       "source_checks":dict(sorted(status.items())),
       "sources":reports,
       "checked_source_profiles":len(reports),
       "catalog_count":len(catalog),
    }


def markdown(report):
    lines=[
      "# Source lifecycle — manutenzione automatica di dataset, non mercati uno per uno",
      "",
      "Le fonti hanno un contratto per schema, identità, formato, granularità, data e diritti.",
      "Nessuna riga di venditore, concessione o testo grezzo viene persistita qui.",
      "La data di lettura non prova che un mercato abbia aperto oggi.",
      "",
      f"- Schede nazionali confrontate: **{report['catalog_count']:,}**",
      f"- Fonti controllate: **{report['checked_source_profiles']}**",
      f"- Record di mercato importati da questo audit: **{report['market_imports']}**",
      f"- Aperture individuali verificate: **{report['market_confirmations']}**",
      "",
      "| Fonte | Stato | ID fonte fuori catalogo (non nuovi mercati) | Già trattenuti dal controllo sovrapposizioni | Residui senza esito del filtro | Proposte in staging | Collisioni da valutare | Fatti cambiati | ID non più visti (non chiusi) |",
      "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for sid,row in sorted(report["sources"].items()):
        counts=row.get("counts",{})
        d=row.get("diff",{})
        state=("schema/identità cambiati: revisione della fonte richiesta"
               if row.get("last_check_status")=="contract_change_needs_review"
               else "non disponibile / vecchio checkpoint" if row.get("stale_snapshot_carry_forward")
               else "non disponibile" if row.get("unavailable_no_market_inference")
               else "sola verifica, non apertura confermata")
        missing=d.get("missing_source_identities_since_last_scan",
                      d.get("missing_source_identities_since_last_scan",0))
        changed=d.get("changed_source_identities_since_last_scan",
                      d.get("changed_existing_identities_since_last_scan",0))
        new=counts.get("identity_not_in_existing_catalog",
                       counts.get("source_ids_not_yet_in_catalog",0))
        screened=row.get("source_screening") or {}
        already=screened.get("already_quarantined_by_venue_overlap_review",0)
        unclassified=screened.get("remaining_identities_without_overlap_disposition",new)
        source_stage=row.get("source_stage") or {}
        safe_ideas=source_stage.get("safe_candidates_not_published",0)
        collisions=sum((source_stage.get("review_reason_counts") or {}).values())
        lines.append(
            f"| {sid} | {state} | {new} | {already} | "
            f"{unclassified} | {safe_ideas} | {collisions} | {changed} | {missing} |"
        )
    lines.extend(["",
     "## Aggiunta di nuove fonti (senza nuovi script per Comune)",
     "",
     "1. Scoprire il dataset nella coda automatica e verificare a livello di **fonte** editore, diritti, struttura, data e contenuto.",
     "2. Registrarne il contratto JSON: colonne, identità stabile, una riga=sede/giorno/posteggio, schema atteso, budget dimensione e data effettiva.",
     "3. Gli stessi parser e controlli confrontano in automatico tutti i record ad ogni aggiornamento.",
     "4. Fonti nuove/modificate, identità collidenti, sedi dubbie o dati storici sono trattenuti in revisione: nessun market/evento inventato.",
     "5. Gli adapter esistenti continuano a gestire gli import già revisionati. La promozione di altri contratti richiede qualità/licenza/gate DEV separati.",
     "",
     "Le proposte in staging non sono mercati nuovi o aperti: richiedono diritti, identità e QA. Le collisioni segnalano possibili doppioni e sedi non distinguibili.",
     "Questo report non elimina mercati scomparsi da una sorgente e non assegna nuova navigazione GPS.",
     "",
    ])
    return "\n".join(lines)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--contracts",type=Path,default=Path("backend/data/market-source-contracts.json"))
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--source-dir",type=Path)
    p.add_argument("--previous",type=Path)
    p.add_argument("--probe-raw",action="store_true")
    p.add_argument("--stage-raw",action="store_true")
    p.add_argument("--today",type=date.fromisoformat,default=date.today())
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    args=p.parse_args()
    cfg=json.loads(args.contracts.read_text("utf-8"))
    catalog=load_existing(args.manifest)
    prior=json.loads(args.previous.read_text("utf-8")) if (
        args.previous and args.previous.is_file()) else None
    result=run(cfg,catalog,source_dir=args.source_dir,previous=prior,
               probe_raw=args.probe_raw,stage_raw=args.stage_raw,today=args.today)
    for path in (args.out,args.report):
        path.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n","utf-8")
    args.report.write_text(markdown(result),"utf-8")
    print("SOURCE_LIFECYCLE",json.dumps({
       "source_profiles":result["checked_source_profiles"],
       "source_checks":result["source_checks"],"imports":0,
       "confirmed_events":0,"original_market_ids":result["catalog_count"],
    },ensure_ascii=False))


if __name__=="__main__":
    main()
