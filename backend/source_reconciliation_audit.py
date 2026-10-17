#!/usr/bin/env python3
"""Read-only, source-level MERCap matching against all existing Lombardia cards.

This AUDIT measures field-only repairs using the already approved official
MERCAP adapter. It does NOT publish a change, invent an opening, add an ID,
rewrite source provenance, or interpret approximate GPS as an entrance.
Raw publisher rows are never persisted by this audit.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from lombardia_overlap import location_key, norm, weekday_evidence
from official_enrichment import hours_allowed, distance_km
from merge_catalog import load_existing
from source_lombardia import (
    SOURCE_PAGE, convert as convert_lombardia, download as download_lombardia,
)

SOURCE_PREFIX = "lo-mercap-"
SOURCE_REGION = "Lombardia"
MAX_CATALOG = 80_000
MAX_SOURCE = 3_000
MAX_SAMPLES = 24
MAX_AGE_DAYS = 540

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                      separators=(",", ":")).encode("utf-8")).hexdigest()

def _place_key(row):
    """Town, province and physical street are required for strict comparisons."""
    loc = location_key(row, SOURCE_REGION)
    if loc is None:
        return None
    province = norm(row.get("provincia"))
    if province and not (len(province) == 2 and province.isalpha()):
        return None
    days = weekday_evidence(row)
    if days is None or len(days) != 1:
        return None
    return (loc[0], province, loc[1], next(iter(days)))

def _town_day(row):
    if row.get("regione") != SOURCE_REGION:
        return None
    city = norm(row.get("citta"))
    province = norm(row.get("provincia"))
    days = weekday_evidence(row)
    if not city or len(province) != 2 or days is None or len(days) != 1:
        return None
    return (city, province, next(iter(days)))

def _valid_official(row, today):
    if (not isinstance(row, dict) or row.get("regione") != SOURCE_REGION or
        row.get("url_fonte") != SOURCE_PAGE or
        not str(row.get("slug") or "").startswith(SOURCE_PREFIX) or
        row.get("verificato_il") or
        row.get("date_quality") == "confermata"):
        raise ValueError("Publisher record violates reviewed MERCap identity contract")
    try:
        source_day = date.fromisoformat(str(row.get("aggiornato_il")))
    except (TypeError, ValueError):
        raise ValueError("Unrecognized official publisher data date") from None
    source_age = (today-source_day).days
    if not -1 <= source_age <= MAX_AGE_DAYS:
        # Reject instead of counting stale official rows as candidates.
        raise ValueError("Official publisher snapshot too old or future dated")
    return source_day

def _compatible_coords(old, source):
    distance = distance_km(old, source)
    # GPS is exclusively a conflict signal. It never creates a positive match.
    return distance is None or distance <= 0.6

def analyze(catalog, official, *, today=None):
    today = today or date.today()
    if (not isinstance(today, date) or not isinstance(catalog, list) or
        not isinstance(official, list) or
        not 1 <= len(catalog) <= MAX_CATALOG or
        not 1_000 <= len(official) <= MAX_SOURCE):
        raise ValueError("Unbounded or incomplete market/source snapshot")
    old_by_slug = {}
    for row in catalog:
        if not isinstance(row, dict) or not isinstance(row.get("slug"), str) or not row["slug"]:
            raise ValueError("Missing existing market identity")
        if row["slug"] in old_by_slug:
            raise ValueError("Duplicate existing market IDs")
        old_by_slug[row["slug"]] = row
    official_ids = set()
    official_exact = defaultdict(list)
    official_by_town = defaultdict(list)
    dates = set()
    counts = Counter()
    for row in official:
        dates.add(_valid_official(row,today))
        sid = row["slug"]
        if sid in official_ids:
            raise ValueError("Repeated official venue/day source identity")
        official_ids.add(sid)
        key = _place_key(row)
        if key is not None:
            official_exact[key].append(row)
        town = _town_day(row)
        if town is not None and row.get("indirizzo"):
            official_by_town[town].append(row)
    if len(dates) != 1:
        raise ValueError("Partial or inconsistent publisher source dates")
    before = [dict(x) for x in catalog]
    samples = {"hours_strong": [], "missing_address_weak": [],
               "hours_collision": [], "exact_id_missing_fields": []}
    matched_old = set()
    for sid, source in ((r["slug"],r) for r in official):
        if sid not in old_by_slug:
            counts["official_source_id_absent_from_catalog_not_new_market_proof"] += 1
            continue
        old = old_by_slug[sid]
        counts["same_source_id_already_in_catalog"] += 1
        if (norm(old.get("citta")) != norm(source.get("citta")) or
            old.get("regione") != source.get("regione") or
            (old.get("provincia") and source.get("provincia") and
             norm(old["provincia"]) != norm(source["provincia"]))):
            counts["same_source_id_location_conflict"] += 1
            continue
        if not old.get("orario_testo") and hours_allowed(source.get("orario_testo")):
            counts["exact_source_id_missing_hours"] += 1
            if len(samples["exact_id_missing_fields"]) < MAX_SAMPLES:
                samples["exact_id_missing_fields"].append(sid)
        if (not old.get("indirizzo") and source.get("indirizzo")
                and _town_day(old) == _town_day(source)):
            counts["exact_source_id_missing_address"] += 1
            if len(samples["exact_id_missing_fields"]) < MAX_SAMPLES:
                samples["exact_id_missing_fields"].append(sid)
        if (old.get("orario_testo") and source.get("orario_testo") and
            old["orario_testo"] != source["orario_testo"]):
            counts["same_source_id_hour_conflicts_review_only"] += 1
        if (old.get("indirizzo") and source.get("indirizzo") and
            norm(old["indirizzo"]) != norm(source["indirizzo"])):
            counts["same_source_id_street_conflicts_review_only"] += 1

    for old in catalog:
        if old.get("regione") != SOURCE_REGION or old["slug"].startswith(SOURCE_PREFIX):
            continue
        counts["legacy_lombardia_records_checked"] += 1
        town = _town_day(old)
        key = _place_key(old)
        if key is not None:
            possible = official_exact.get(key, [])
            # Historical cards sometimes have an empty province.
            # No source can enrich when multiple official venues share
            # the same street+weekday or the province is uncertain.
            if len(possible) > 1:
                counts["strong_key_ambiguous_official_venue_day"] += 1
                if len(samples["hours_collision"]) < MAX_SAMPLES:
                    samples["hours_collision"].append(old["slug"])
            elif len(possible) == 1:
                source = possible[0]
                if not _compatible_coords(old,source):
                    counts["strong_key_coordinate_conflict"] += 1
                    continue
                counts["strong_city_province_street_day_matches"] += 1
                if not old.get("orario_testo") and hours_allowed(source.get("orario_testo")):
                    counts["eligible_legacy_missing_hours_strong_match"] += 1
                    matched_old.add(old["slug"])
                    if source["slug"] in old_by_slug:
                        counts["eligible_hours_source_id_already_published"] += 1
                    else:
                        counts["eligible_hours_source_id_held_or_not_published"] += 1
                    if len(samples["hours_strong"]) < MAX_SAMPLES:
                        samples["hours_strong"].append({
                            "legacy_id": old["slug"],
                            "source_id": source["slug"],
                            "field": "orario_testo",
                            "action": "review_only",
                        })
                elif old.get("orario_testo") and source.get("orario_testo"):
                    counts["same_venue_hours_present_do_not_overwrite"] += 1
                else:
                    counts["same_venue_no_usable_official_hours"] += 1
            else:
                counts["legacy_no_exact_street_day_match"] += 1
            continue
        if not old.get("indirizzo") and town is not None:
            # The old position often points at the town centroid: do NOT
            # auto-fill an address from distance alone. Only flag a case
            # when exactly one official market has that town+weekday.
            choices = official_by_town.get(town, [])
            if len(choices) == 1:
                source = choices[0]
                geo_distance = distance_km(old,source)
                if geo_distance is not None and geo_distance <= 0.15:
                    counts["weak_missing_address_one_venue_nearby_review_only"] += 1
                    if len(samples["missing_address_weak"]) < MAX_SAMPLES:
                        samples["missing_address_weak"].append(old["slug"])
                else:
                    counts["missing_address_without_grounded_venue"] += 1
            elif len(choices) > 1:
                counts["missing_address_multiple_official_venues"] += 1
            else:
                counts["missing_address_no_matching_official_town_day"] += 1
        else:
            counts["legacy_no_safe_street_or_day"] += 1

    if before != catalog:
        raise ValueError("Source reconciliation mutated input market data")
    return {
        "schema": 1, "reference_date": today.isoformat(), "region": SOURCE_REGION,
        "source": SOURCE_PAGE, "official_dataset_updated_at": next(iter(dates)).isoformat(),
        "official_row_count": len(official),
        "official_snapshot_digest": digest([{
            "slug": r["slug"],"city":r.get("citta"),"address":r.get("indirizzo"),
            "day":sorted(weekday_evidence(r) or []),"hours":r.get("orario_testo")
        } for r in official]),
        "baseline_catalog_records": len(catalog),
        "counts": dict(sorted(counts.items())), "examples": samples,
        "documented_strong_hour_candidate_ids_sha256": digest(sorted(matched_old)),
        "read_only": True, "proposals_require_independent_release_gate": True,
        "market_updates_applied": 0, "markets_added": 0, "markets_deleted": 0,
        "individual_openings_confirmed": 0, "precise_coordinates_created": 0,
        "new_directions_enabled": 0, "legacy_primary_sources_changed": 0,
    }

def markdown(report):
    c = report["counts"]
    out = ["# Lombardia MERCap — confronto aggiornamento campi esistenti",
           "",
           "Solo ricerca. Il dato ufficiale regionale non verifica la singola apertura.",
           "Coordinate indicative mai utilizzate per confermare una sede.",
           "",
           "- Schede nazionali conservate: **" + str(report["baseline_catalog_records"]) + "**",
           "- Righe ufficiali esaminate: **" + str(report["official_row_count"]) + "**",
           "- Data dichiarata del dataset: **" + report["official_dataset_updated_at"] + "**",
           "- Legacy con orario vuoto e città+provincia+via+giorno univoci: **" +
           str(c.get("eligible_legacy_missing_hours_strong_match",0)) + "**",
           "- Legacy con indirizzo vuoto vicine a una sola sede: **" +
           str(c.get("weak_missing_address_one_venue_nearby_review_only",0)) +
           "** (soltanto ricerca; possibile centro comunale)",
           "- Campi aggiornati da questo job: **0**",
           "", "## Conteggi e motivi di blocco", ""]
    out += ["- "+k+": **"+str(v)+"**" for k,v in sorted(c.items())]
    out += ["","## Campioni con provenienza", ""]
    for x in report["examples"]["hours_strong"][:MAX_SAMPLES]:
        out.append("- " + x["legacy_id"] + " ← " + x["source_id"] +
                   " (solo proposta orario, nessun import)")
    return "\n".join(out) + "\n"

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, default=Path("public/data/v1/manifest.json"))
    p.add_argument("--source-json", type=Path,
                   help="Optional previously downloaded and vetted official adapter output")
    p.add_argument("--today", type=date.fromisoformat, default=date.today())
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    baseline = load_existing(args.manifest)
    if args.source_json:
        official = json.loads(args.source_json.read_text("utf-8"))
    else:
        official = convert_lombardia(download_lombardia(), today=args.today)
    result = analyze(baseline, official, today=args.today)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False,
                                   sort_keys=True)+"\n","utf-8")
    args.report.write_text(markdown(result),"utf-8")
    print(json.dumps({
        "source_rows":result["official_row_count"],
        "strong_missing_hours":result["counts"].get("eligible_legacy_missing_hours_strong_match",0),
        "weak_missing_address":result["counts"].get("weak_missing_address_one_venue_nearby_review_only",0),
        "catalog_updates":0, "confirmed_events":0,
    }))

if __name__ == "__main__":
    main()
