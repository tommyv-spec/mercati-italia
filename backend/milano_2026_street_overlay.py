#!/usr/bin/env python3
"""Carefully scoped existing-Milan-market street labels from the municipal PDF.

The 2024 DS291 source has no addresses. The 2026/10/01 city PDF has table
columns for actual market streets; verified PDF market names + weekdays
agree with independent city GIS IDs. Only the exactly reviewed 25 GIS IDs
may receive an address, never new market IDs, confirmations, dates or GPS.

Multi-street addresses describe an area, not a precise entrance.
"""
from __future__ import annotations

import hashlib
import json
import re
from copy import deepcopy
from datetime import date
from pathlib import Path

from milano_2026_overlay import (
    OLD_DATASET, PDF_DATE, PDF_DOCUMENT,
    OFFICIAL_PDF_SOURCE, PDF_TO_GIS_ALIAS,
    key, verified_pairs,
)

EVIDENCE_FILE=Path(__file__).resolve().parent/"data/milano-mss-reviewed-streets-2026-10-18.json"
SOURCE_COUNT=75
SOURCE_REVIEW_DAY="2026-10-18"
EXPECTED_BLOB="33ceda300fe8c1dbb121c34b96ebb26e048ffeb6"
LABEL_RE=re.compile(r"^(?:Via|Viale|Piazza|Piazzale|Largo|Bastioni|Ripa)\s",re.I)

def git_blob_sha(path):
    value=path.read_bytes()
    return hashlib.sha1(b"blob "+str(len(value)).encode()+b"\0"+value).hexdigest()

def source_rows(evidence,pdf,gis):
    if (not isinstance(evidence,dict) or evidence.get("schema")!=1
        or evidence.get("publisher")!="Comune di Milano"
        or evidence.get("publisher_document_date")!=PDF_DATE.isoformat()
        or evidence.get("publisher_report_url")!=PDF_DOCUMENT
        or evidence.get("reviewed_on")!=SOURCE_REVIEW_DAY
        or evidence.get("market_imports")!=0
        or evidence.get("individual_openings_confirmed")!=0
        or evidence.get("new_geocodes_authorized") is not False
        or not isinstance(evidence.get("entries"),list)
        or len(evidence["entries"])!=SOURCE_COUNT):
        raise ValueError("Unreviewed Milan street evidence changed")
    pairs,_=verified_pairs(pdf,gis)
    by_id={x["id"]:x for x in gis["records"]}
    pdf_days={}
    for obs in pdf["obs"]:
        pdf_days.setdefault(key(obs["name"]),set()).add(obs["weekday"])
    reviewed={}
    names=set()
    for row in evidence["entries"]:
        if not isinstance(row,dict):
            raise ValueError("Invalid Milan street certificate entry")
        ident=row.get("gis_id")
        name=row.get("pdf_market_name")
        days=row.get("weekdays")
        street=row.get("street_display")
        pages=row.get("pdf_pages")
        if (type(ident) is not int or ident not in pairs or ident in reviewed
            or not isinstance(name,str) or not name
            or not isinstance(days,list) or
                any(type(d) is not int or not 0<=d<=6 for d in days)
            or len(days)!=len(set(days))
            or sorted(days)!=pairs[ident]
            or sorted(days)!=sorted(pdf_days.get(key(name),[]))
            or key(PDF_TO_GIS_ALIAS.get(name,name))!=key(by_id[ident]["name"])
            or not isinstance(street,str) or not 7<=len(street)<=175
            or not LABEL_RE.match(street) or any(t in street for t in ("http:","https:","\n","@"))
            or not isinstance(pages,list) or not pages
            or any(type(p) is not int or not 1<=p<=10 for p in pages)
            or pages!=sorted(set(pages))
            or row.get("multiple_streets") not in (True,False)
            or row.get("venue_navigation_precision_upgraded") is not False):
            raise ValueError("Street venue/day does not match approved two-source identity")
        if key(name) in names:
            raise ValueError("Ambiguous repeated market name in reviewed streets")
        names.add(key(name))
        reviewed[ident]=row
    return reviewed

def integrate(base,evidence,pdf,gis,*,today=None,apply=False):
    today=today or date.today()
    if (not isinstance(base,list) or not isinstance(today,date)
            or type(apply) is not bool
            or len({x.get("slug") for x in base})!=len(base)):
        raise ValueError("Invalid catalog or mode for Milan street attribution")
    if (today-PDF_DATE).days<0 or (today-PDF_DATE).days>540:
        raise ValueError("Reviewed publisher PDF too old for automatic street reconciliation")
    reviewed=source_rows(evidence,pdf,gis)
    original_ids={x["slug"] for x in base}
    result=[]
    changed=[]
    statuses={"stale_source":0,"already_present":0,"added":0,"unpublished":0}
    samples=[]
    for src in base:
        out=deepcopy(src)
        if str(src.get("slug") or "").startswith("mi-mss-"):
            try: ident=int(src["slug"].removeprefix("mi-mss-"))
            except ValueError: ident=-1
            if ident in reviewed:
                entry=reviewed[ident]
                if (src.get("regione")!="Lombardia" or src.get("citta")!="Milano"
                        or src.get("url_fonte")!=OLD_DATASET):
                    raise ValueError("Milan official market identity mixed with another publisher")
                old=str(src.get("indirizzo") or "").strip()
                current=entry["street_display"]
                if old and old!=current:
                    raise ValueError("Publisher street conflicts with existing address: hold")
                if old==current:
                    statuses["already_present"]+=1
                elif not old and apply:
                    out["indirizzo"]=current
                    sources=out.get("fonti")
                    if sources is None:sources=[]
                    if not isinstance(sources,list) or any(not isinstance(v,dict) for v in sources):
                        raise ValueError("Invalid Milan original source attribution")
                    if OFFICIAL_PDF_SOURCE not in sources:
                        sources.append(dict(OFFICIAL_PDF_SOURCE))
                    out["fonti"]=sources
                    statuses["added"]+=1
                    changed.append(src["slug"])
                else:
                    statuses["unpublished"]+=1
                if len(samples)<SOURCE_COUNT:
                    samples.append({"id":src["slug"],"document_pages":entry["pdf_pages"],
                                    "multi_street_area_not_single_entrance":entry["multiple_streets"]})
        result.append(out)
    if len(result)!=len(base) or {x["slug"] for x in result}!=original_ids:
        raise ValueError("Milan street correction changed stable market IDs")
    return result,{
        "schema":1,"source":"Comune di Milano (official 2026 market street table)",
        "publisher_report_url":PDF_DOCUMENT,
        "data_source_date":PDF_DATE.isoformat(),
        "reviewed_gis_id_count":len(reviewed),
        "existing_market_addresses_added":statuses["added"],
        "already_present":statuses["already_present"],
        "not_changed_dry_run":statuses["unpublished"],
        "market_records_before":len(base),"market_records_after":len(result),
        "changed_ids":sorted(changed),
        "samples":samples,
        "all_unchanged_fields_preserved":True,
        "new_market_ids":0,"market_records_deleted":0,
        "future_market_openings_confirmed":0,
        "precise_market_coordinates_created":0,
        "navigation_precision_upgraded":False,
        "original_primary_sources_overwritten":0,
        "source_evidence_blob":EXPECTED_BLOB,
    }

def verify_diff(before,after,report,evidence,pdf,gis):
    reviewed=source_rows(evidence,pdf,gis)
    if (not isinstance(before,list) or not isinstance(after,list)
        or len(before)!=len(after) or report.get("schema")!=1
        or report.get("reviewed_gis_id_count")!=SOURCE_COUNT
        or report.get("source_evidence_blob")!=EXPECTED_BLOB
        or any(report.get(x)!=0 for x in (
            "new_market_ids","market_records_deleted",
            "future_market_openings_confirmed","precise_market_coordinates_created",
            "original_primary_sources_overwritten"))
        or report.get("navigation_precision_upgraded") is not False):
        raise ValueError("Unsafe source address release report")
    diffs=[]
    for old,new in zip(before,after):
        if old["slug"]!=new["slug"]:
            raise ValueError("Market ID changed by Milan street attribution")
        if old==new:
            continue
        try:ident=int(old["slug"].removeprefix("mi-mss-"))
        except ValueError:ident=-1
        if ident not in reviewed:
            raise ValueError("Unreviewed Milan source identity changed")
        if old.get("indirizzo"):
            raise ValueError("A previously populated Milan address was overwritten")
        changed={k for k in set(old)|set(new) if old.get(k)!=new.get(k)}
        if not changed<={"indirizzo","fonti"} or new.get("indirizzo")!=reviewed[ident]["street_display"]:
            raise ValueError("Unreviewed market field changed while enriching Milan street")
        prior=list(old.get("fonti") or [])
        current=list(new.get("fonti") or [])
        if not all(p in current for p in prior) or OFFICIAL_PDF_SOURCE not in current:
            raise ValueError("Original municipal sources not retained")
        diffs.append(old["slug"])
    if sorted(diffs)!=report.get("changed_ids") or len(diffs)!=report.get("existing_market_addresses_added"):
        raise ValueError("Missing or unexpected field-level source updates")
    return {"schema":1,"release_safe":True,"source_reviewed_entries":len(reviewed),
            "existing_addresses_added":len(diffs),
            "new_market_records":0,"confirmed_events":0,"new_navigation_points":0}
