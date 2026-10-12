#!/usr/bin/env python3
"""Reconcile official public-source evidence into previously published markets.

Manual observation FIRST (2026-10-12): Regione Lombardia MERCap entries
100001 Albizzate, 100004 Arsago Seprio and 100551 Pogliano Milanese list
street, weekday and hours absent from matching third-party market entries.
This module is a conservative generic *evidence* transfer, not fuzzy dedup.

Never changes stable IDs, event dates, recurrence, primary source, verified
status, city, coordinates or date-of-previous-source. Adds only missing
published hours with mandatory warning and a distinct official source link.
If the source cannot be joined confidently, keep the original untouched.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date
from pathlib import Path

from lombardia_overlap import location_key, weekday_evidence
from merge_catalog import load_existing

# New trusted formats must be manually inspected and added to this allowlist,
# with negative tests before automatic enrichment. No remote user input.
TRUSTED_FEEDS = {
    "lombardia-mercap": {
        "source_prefix": "lo-mercap-",
        "region": "Lombardia",
        "url": "https://www.dati.lombardia.it/d/68zx-njaw",
        "name": "Regione Lombardia – MERCap (archivio regionale, date da verificare)",
        "max_age_days": 540,
    },
}
MAX_SOURCE_ROWS = 3000
MAX_ENRICHED_RECORDS = 500
MAX_DISTANCE_KM = 0.6

# Actual adapter strings: one time span or two labelled seasonal spans.
PAIR = r"(?:[01]\d|2[0-3]):[0-5]\d[–-](?:[01]\d|2[0-3]):[0-5]\d"
SIMPLE = re.compile(r"^" + PAIR + r" \(fonte comunale, da verificare\)$")
SEASONAL = re.compile(
    r"^(?:Inverno: "+PAIR+r"(?:; )?)?(?:Estate: "+PAIR+r")?"
    r" \(fonte comunale, da verificare\)$"
)


def hours_allowed(value):
    value = str(value or "").strip()
    if not value or len(value) > 160:
        return False
    if SIMPLE.fullmatch(value):
        values = re.findall(r"\d\d:\d\d", value)
    elif SEASONAL.fullmatch(value):
        values = re.findall(r"\d\d:\d\d", value)
    else:
        return False
    return len(values) in (2, 4) and all(
        end > start for start, end in zip(values[::2], values[1::2])
    )


def distance_km(a, b):
    try:
        lat1, lng1 = float(a["lat"]), float(a["lng"])
        lat2, lng2 = float(b["lat"]), float(b["lng"])
    except (KeyError, ValueError, TypeError, OverflowError):
        return None
    if not (40 <= lat1 <= 47 and 40 <= lat2 <= 47 and
            6 <= lng1 <= 19 and 6 <= lng2 <= 19):
        return None
    rad = math.pi / 180
    dlat = (lat2 - lat1) * rad
    dlng = (lng2 - lng1) * rad
    hav = (math.sin(dlat / 2)**2 +
           math.cos(lat1 * rad) * math.cos(lat2 * rad) *
           math.sin(dlng / 2)**2)
    return 12742.0 * math.asin(min(1.0, math.sqrt(hav)))


def evidence_key(record, region):
    return location_key(record, region), (
        frozenset(weekday_evidence(record) or ())
    )


def enrich(base, held_official, *, source_id="lombardia-mercap", today=None):
    today = today or date.today()
    if source_id not in TRUSTED_FEEDS:
        raise ValueError("Unreviewed source enrichment is not allowed")
    spec = TRUSTED_FEEDS[source_id]
    if not isinstance(base, list) or not isinstance(held_official, list):
        raise ValueError("Invalid official enrichment input")
    if len(held_official) > MAX_SOURCE_ROWS:
        raise ValueError("Too many official rows for source enrichment")
    baseline = {}
    for record in base:
        slug = record.get("slug")
        if not slug or slug in baseline:
            raise ValueError("Duplicate/missing baseline market identity")
        baseline[slug] = record
    updated = {slug:dict(record) for slug,record in baseline.items()}
    by_key = defaultdict(list)
    for row in base:
        if row.get("regione") != spec["region"]:
            continue
        key, weekdays = evidence_key(row, spec["region"])
        if key is not None and len(weekdays) == 1 and not row["slug"].startswith(spec["source_prefix"]):
            by_key[(key,weekdays)].append(row)

    incoming_by_key = defaultdict(list)
    counts = Counter()
    for official in held_official:
        if not isinstance(official, dict):
            raise ValueError("Invalid official record type")
        sid = str(official.get("slug") or "")
        if (not sid.startswith(spec["source_prefix"])
                or official.get("regione") != spec["region"]
                or official.get("url_fonte") != spec["url"]
                or official.get("verificato_il")
                or official.get("date_quality") == "confermata"):
            raise ValueError("Official evidence contract mismatch")
        last = str(official.get("aggiornato_il") or "")[:10]
        try:
            age = (today - date.fromisoformat(last)).days
        except (TypeError, ValueError):
            raise ValueError("Official evidence has no valid dataset date") from None
        if age < -1:
            raise ValueError("Official source timestamp is in the future")
        key, days = evidence_key(official, spec["region"])
        if key is not None and len(days) == 1:
            incoming_by_key[(key,days)].append(official)
        else:
            counts["skipped_no_exact_location_or_day"] += 1

    samples = []
    touched = set()
    for key, source_rows in sorted(incoming_by_key.items(), key=str):
        if len(source_rows) != 1:
            counts["skipped_multiple_official_markets_same_venue_day"] += len(source_rows)
            continue
        source = source_rows[0]
        old_rows = by_key.get(key, [])
        if not old_rows:
            counts["skipped_no_exact_legacy_market"] += 1
            continue
        if not hours_allowed(source.get("orario_testo")):
            counts["skipped_no_safe_official_hours"] += 1
            continue
        for old in old_rows:
            slug = old["slug"]
            gap = distance_km(old,source)
            if gap is not None and gap > MAX_DISTANCE_KM:
                counts["skipped_coordinates_conflict"] += 1
                continue
            # No existing hour overwrites: a contradictory source requires
            # human reconciliation. This also handles verified records.
            present = str(old.get("orario_testo") or "").strip()
            official_entry = {"nome":spec["name"],"url":spec["url"]}
            revised = updated[slug]
            if not present:
                revised["orario_testo"] = str(source["orario_testo"])
                counts["hours_added"] += 1
                touched.add(slug)
            else:
                counts["existing_hours_preserved"] += 1
            primary = {
                "nome":str(old.get("fonte") or ""),
                "url":str(old.get("url_fonte") or ""),
            }
            raw = old.get("fonti")
            links = [x for x in (raw if isinstance(raw,list) else [])
                     if isinstance(x,dict)]
            links = [x.copy() for x in links]
            if primary["nome"] or primary["url"]:
                if primary not in links: links.append(primary)
            if official_entry not in links:
                links.append(official_entry)
                counts["official_source_attributions_added"] += 1
                touched.add(slug)
            revised["fonti"] = links
            counts["exact_matches"] += 1
            if len(samples) < 30:
                samples.append({
                    "published_id":slug,
                    "official_id":str(source.get("id_fonte") or source.get("slug"))[:50],
                    "street":str(old.get("indirizzo") or "")[:100],
                    "source_day":sorted(weekday_evidence(source) or []),
                    "distance_km":round(gap,3) if gap is not None else None,
                    "changed_hours":not bool(present),
                })
    if len(touched) > MAX_ENRICHED_RECORDS:
        raise ValueError("Official source enrichment exceeds per-run limit")
    return [updated[x["slug"]] for x in base], {
        "schema":1,
        "source_id":source_id,
        "source_name":spec["name"],
        "review_only":True,
        "source_rows_screened":len(held_official),
        "legacy_records_changed":len(touched),
        "existing_market_hours_added":int(counts["hours_added"]),
        "official_source_attributions_added":int(counts["official_source_attributions_added"]),
        "exact_matches":int(counts["exact_matches"]),
        "counts":dict(sorted(counts.items())),
        "samples":samples,
        "record_identity_changes":0,
        "confirmed_date_changes":0,
        "individual_market_verifications":0,
        "coordinates_overwritten":0,
        "primary_sources_overwritten":0,
        "old_dataset_dates_overwritten":0,
    }


def markdown(report):
    text = [
        "# Official source enrichment — legacy cards",
        "",
        "A previously published venue gets source-backed missing hours only",
        "after exact municipality, street and weekday matching, and a",
        "compatible map point when both coordinates are available.",
        "No forecast, human verification, original source, or identity changed.",
        "",
        f"- Held official rows screened: **{report['source_rows_screened']}**",
        f"- Existing market cards with added information: **{report['legacy_records_changed']}**",
        f"- Missing hours supplied from official regional source: **{report['existing_market_hours_added']}**",
        f"- Official source attributions attached: **{report['official_source_attributions_added']}**",
    ]
    for key, val in report["counts"].items():
        text.append(f"- {key}: {val}")
    text.extend(["", "## Example exact matches", ""])
    for sample in report["samples"]:
        text.append(
            f"- {sample['published_id']} ← {sample['official_id']} "
            f"(hours added: {sample['changed_hours']}, "
            f"venue distance: {sample['distance_km']} km)"
        )
    return "\n".join(text)+"\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path,required=True)
    p.add_argument("--official", type=Path,required=True)
    p.add_argument("--updated", type=Path,required=True)
    p.add_argument("--report", type=Path,required=True)
    p.add_argument("--summary", type=Path,required=True)
    args=p.parse_args()
    current=load_existing(args.manifest)
    candidates=json.loads(args.official.read_text("utf-8"))
    rows, report=enrich(current,candidates)
    for path in (args.updated,args.report,args.summary):
        path.parent.mkdir(parents=True,exist_ok=True)
    args.updated.write_text(json.dumps(rows,indent=2,ensure_ascii=False)+"\n","utf-8")
    args.report.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n","utf-8")
    args.summary.write_text(markdown(report),"utf-8")
    print(json.dumps({key:report[key] for key in
                      ("legacy_records_changed","existing_market_hours_added",
                       "official_source_attributions_added","source_rows_screened")},ensure_ascii=False))


if __name__ == "__main__":
    main()
