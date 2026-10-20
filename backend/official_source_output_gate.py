#!/usr/bin/env python3
"""Independent output contract for ALL five existing official market adapters.

A source adapter isn't trusted merely because its download succeeded.  Check
the NORMALIZED records before their provenance, calendar, geometry and URLs
can reach the candidate DEV market catalog.  Layout/rights are separately
approved in the pinned source registry.  This gate never authorizes a new
source, confirms a market, changes or geocodes any record.

One incorrectly extracted official row rejects the whole source batch;
the surrounding DEV pipeline treats the publisher as unavailable and retains
the old market cohort rather than publishing partial or wrongly-mapped facts.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from recurrence_refresh import WEEKDAYS, explicit_rule
from source_hours import MAX_HOURS_TEXT_LENGTH

CONTRACTS_PATH=Path(__file__).resolve().parent/"data/market-source-contracts.json"
ALLOWLIST=frozenset({"milano","firenze","lombardia","bologna","corciano"})
SOURCE_DATES_BOUND=4000
ITALY_LAT=(35.0,48.0)
ITALY_LNG=(6.0,19.0)
REGION_PROVINCES={"milano":("Lombardia",{"MI"}),
                  "firenze":("Toscana",{"FI"}),
                  "lombardia":("Lombardia",None),
                  "bologna":("Emilia-Romagna",{"BO"}),
                  "corciano":("Umbria",{"PG"})}
MAX_DATE_ROWS=160
SOURCE_DAY_SUFFIX=re.compile(r"-(lunedi|martedi|mercoledi|giovedi|venerdi|sabato|domenica)$")


def profile(source_id):
    if source_id not in ALLOWLIST:
        raise ValueError("Unreviewed official source adapter ID")
    registry=json.loads(CONTRACTS_PATH.read_text("utf-8"))
    if (registry.get("schema")!=1 or
            not isinstance(registry.get("normalized_profiles"),list)):
        raise ValueError("Normalized publisher admission registry changed")
    entries=registry["normalized_profiles"]
    if len(entries)!=len(ALLOWLIST) or {x.get("id") for x in entries}!=ALLOWLIST:
        raise ValueError("Unreviewed normalized source profile list")
    p=next(x for x in entries if x["id"]==source_id)
    if (p.get("publication_mode")!="existing_adapter_only" or
            p.get("identity_prefix") != {
                "milano":"mi-mss-","firenze":"fi-feelflorence-",
                "lombardia":"lo-mercap-","bologna":"bo-open-",
                "corciano":"pg-corciano-",
            }[source_id] or
            not isinstance(p.get("expected_precision"),list) or
            not 1<=int(p.get("min_records",0))<=int(p.get("max_records",0))<=SOURCE_DATES_BOUND):
        raise ValueError("Unapproved source output contract")
    return p


def _source_url_valid(source_id,url,p):
    if not isinstance(url,str) or len(url)>1200 or url!=url.strip():
        return False
    if url in p.get("source_pages",[]):
        return True
    if source_id=="firenze":
        if url=="https://opendata.comune.fi.it/page_dataset_show?id=mercati":
            return True
        try:
            link=urlsplit(url)
            return (link.scheme=="https" and
                    link.hostname=="www.feelflorence.it" and
                    link.path.startswith("/") and
                    not link.username and not link.password and
                    link.port in (None,443) and
                    not link.fragment and not link.query)
        except ValueError:
            return False
    return False


def _bounded_text(value,max_chars=250):
    return isinstance(value,str) and 0<len(value.strip())<=max_chars


def _safe_coords(row,p):
    lat,lng=row.get("lat"),row.get("lng")
    qual=row.get("position_quality")
    allowed=set(p["expected_precision"])
    if qual not in allowed:
        raise ValueError("Official publisher source asserted unreviewed GPS precision")
    if lat is None and lng is None:
        if qual not in {"sconosciuta"}:
            raise ValueError("No official point can have a geographic precision claim")
        return False
    if (type(lat) not in (int,float) or type(lng) not in (int,float)
            or not math.isfinite(lat) or not math.isfinite(lng)
            or not ITALY_LAT[0]<=lat<=ITALY_LAT[1]
            or not ITALY_LNG[0]<=lng<=ITALY_LNG[1]
            or qual=="sconosciuta"):
        raise ValueError("Missing, invalid or mismatched official market coordinates")
    return True


def inspect(source_id,rows,*,today=None,previous=None):
    today=today or date.today()
    p=profile(source_id)
    if (not isinstance(today,date) or not isinstance(rows,list) or
            not int(p["min_records"])<=len(rows)<=int(p["max_records"])):
        raise ValueError("Publisher returned incomplete or excessive market cohort")
    if previous is not None and (
        not isinstance(previous,dict) or
        previous.get("source_id")!=source_id or
        previous.get("market_confirmations")!=0 or
        previous.get("catalog_updates")!=0):
        raise ValueError("Untrusted previous publisher output report")
    ids=set()
    stats=Counter()
    source_dates=set()
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError("Publisher market record is not an object")
        slug=row.get("slug")
        if (not isinstance(slug,str) or not slug.startswith(p["identity_prefix"])
                or len(slug)>180 or slug in ids):
            raise ValueError("Source record identity missing, duplicated or from another adapter")
        ids.add(slug)
        region,provinces=REGION_PROVINCES[source_id]
        province=row.get("provincia")
        if (row.get("regione")!=region
                or not isinstance(province,str) or
                not re.fullmatch("[A-Z]{2}",province) or
                (provinces and province not in provinces)
                or not _bounded_text(row.get("citta"),120)
                or not _bounded_text(row.get("nome"),180)
                or not _source_url_valid(source_id,row.get("url_fonte"),p)):
            raise ValueError("Official publisher field mapping or provenance changed")
        if (row.get("status")!="non_confermato"
                or row.get("verificato_il") not in (None,"")
                or row.get("date_quality") not in ("prevista","sconosciuta")):
            raise ValueError("Source attempted to confirm an individual market without proof")
        if row.get("citta")!=row.get("citta").strip():
            raise ValueError("Publisher city extraction has leading/trailing junk")
        if row.get("indirizzo") is not None and (
                not isinstance(row["indirizzo"],str)
                or len(row["indirizzo"])>260):
            raise ValueError("Publisher address extraction changed type or exceeded bounds")
        if row.get("orario_testo") is not None and (
                not isinstance(row["orario_testo"],str)
                or len(row["orario_testo"])>MAX_HOURS_TEXT_LENGTH):
            raise ValueError("Publisher hours extraction changed type or exceeded bounds")
        if row.get("indirizzo"):stats["nonempty_address"]+=1
        if row.get("orario_testo"):stats["nonempty_hours"]+=1
        if _safe_coords(row,p):stats["source_coordinates_present"]+=1
        stamp=row.get("aggiornato_il")
        if not isinstance(stamp,str):
            raise ValueError("Publisher last dataset date is not a string")
        try:
            updated=date.fromisoformat(stamp)
        except ValueError:
            raise ValueError("Invalid publisher dataset timestamp") from None
        if updated>today:
            raise ValueError("Official source date is in future")
        source_dates.add(stamp)
        if len(source_dates)>1:
            raise ValueError("One source cohort mixes publisher dataset dates")
        dates=row.get("date")
        if not isinstance(dates,list) or len(dates)>MAX_DATE_ROWS:
            raise ValueError("Invalid or excessive source-calendar dates")
        if (dates and row["date_quality"]!="prevista") or (
                not dates and row["date_quality"]=="prevista"):
            raise ValueError("Source calendar dates and quality labels disagree")
        if dates:
            stats["forecasted_records"]+=1
        week=explicit_rule(row.get("ricorrenza_testo"))
        suff=SOURCE_DAY_SUFFIX.search(slug)
        if (week and week.get("kind")=="weekly" and suff and
                WEEKDAYS.index(suff.group(1)) not in week["weekdays"]):
            raise ValueError("Official stable weekday conflicts with the printed recurrence")
        seen_dates=set()
        for d in dates:
            if not isinstance(d,str) or d in seen_dates:
                raise ValueError("Repeated/invalid official market future date")
            try:
                day=date.fromisoformat(d)
            except ValueError:
                raise ValueError("Unparseable official market future date") from None
            if not today<=day<=date.fromordinal(today.toordinal()+365):
                raise ValueError("Official market forecast outside safe future horizon")
            if week and week.get("kind")=="weekly" and day.weekday() not in week["weekdays"]:
                raise ValueError("Market predicted on a weekday conflicting with official rule")
            seen_dates.add(d)
    source_day=next(iter(source_dates))
    footprint=hashlib.sha256("\n".join(sorted(ids)).encode("utf-8")).hexdigest()
    if previous is not None:
        previous_day=previous.get("official_dataset_timestamp")
        previous_sha=previous.get("identity_sha256")
        if (previous_day==source_day and previous_sha and
                previous_sha!=footprint):
            raise ValueError("Official market identities changed without a new publisher date")
        prior_n=previous.get("rows")
        if (type(prior_n)==int and prior_n>=int(p["min_records"])
                and len(rows)<prior_n*0.95):
            raise ValueError("Official market cohort shrunk beyond source review budget")
        prior_fields=previous.get("field_coverage",{})
        for field in ("nonempty_address","nonempty_hours","source_coordinates_present"):
            prev=prior_fields.get(field)
            if type(prev)==int and prior_n and prior_n>0:
                old_share=prev/prior_n
                new_share=stats[field]/len(rows)
                if new_share+0.12<old_share and prev>=5:
                    raise ValueError("Official publisher column completeness regressed: "+field)
    return {
        "schema":1,
        "source_id":source_id,
        "source_prefix":p["identity_prefix"],
        "region":p["region"],
        "rows":len(rows),
        "official_dataset_timestamp":source_day,
        "identity_sha256":footprint,
        "field_coverage":{
            "nonempty_address":int(stats["nonempty_address"]),
            "nonempty_hours":int(stats["nonempty_hours"]),
            "source_coordinates_present":int(stats["source_coordinates_present"]),
            "forecasted_records":int(stats["forecasted_records"]),
        },
        "dates_projected_not_confirmed":True,
        "catalog_updates":0,
        "market_confirmations":0,
        "new_coordinates_inferred":0,
        "new_market_identities_authorized":0,
        "source_raw_rows_persisted":False,
    }


def verify_gate(report):
    if (not isinstance(report,dict) or report.get("schema")!=1
            or report.get("source_id") not in ALLOWLIST
            or report.get("dates_projected_not_confirmed") is not True
            or report.get("source_raw_rows_persisted") is not False
            or any(report.get(k)!=0 for k in (
                "catalog_updates","market_confirmations",
                "new_coordinates_inferred","new_market_identities_authorized"))
            or type(report.get("rows")) is not int
            or report["rows"] < 1
            or not isinstance(report.get("field_coverage"),dict)):
        raise ValueError("Official source output QA failed to preserve market safeguards")
    return True
