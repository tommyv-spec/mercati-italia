#!/usr/bin/env python3
"""Rank research-only bulk data sources against measured catalog gaps.

No network calls, importing, geocoding or individual market verification.
The regional gaps are upper bounds, NOT counts of safely matchable records.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.parse import urlsplit

TARGETS = frozenset({"name", "address", "weekday", "hours",
                     "seasonality", "coordinates", "category"})
RIGHTS_STATES = frozenset({
    "not_reviewed", "existing_vetted_adapter", "permission_required",
    "odbl_compatibility_review_required", "per_dataset_review_required",
    "historical_reference_only",
})
SCOPE = frozenset({"regional", "national", "network"})


def _safe_https(url):
    try:
        p = urlsplit(str(url))
        return (p.scheme == "https" and bool(p.hostname)
                and not p.username and not p.password
                and p.port in (None, 443) and not p.fragment)
    except ValueError:
        return False


def analyze(registry, coverage):
    if (not isinstance(registry, dict)
            or registry.get("schema") != 1
            or registry.get("review_only") is not True
            or registry.get("automatic_import_allowed") is not False
            or registry.get("market_imports") != 0
            or registry.get("market_confirmations") != 0
            or not isinstance(registry.get("sources"), list)
            or not 1 <= len(registry["sources"]) <= 30):
        raise ValueError("Research registry cannot grant import permission")
    if (not isinstance(coverage, dict)
            or coverage.get("schema") != 1
            or coverage.get("review_only") is not True
            or coverage.get("market_updates_applied") != 0
            or not isinstance(coverage.get("by_region"), list)
            or not isinstance(coverage.get("national"), dict)
            or type(coverage["national"].get("records")) is not int):
        raise ValueError("Untrusted historical catalog gap report")
    by_region = {x["region"]: x for x in coverage["by_region"]}
    observed = set()
    priorities = set()
    output = []
    for source in registry["sources"]:
        if not isinstance(source, dict):
            raise ValueError("Invalid research source")
        sid = source.get("id")
        priority = source.get("priority")
        if (not isinstance(sid, str) or not sid
                or sid in observed or type(priority) is not int
                or not 1 <= priority <= 100 or priority in priorities
                or source.get("scope") not in SCOPE
                or source.get("rights_status") not in RIGHTS_STATES
                or not _safe_https(source.get("url"))
                or not _safe_https(source.get("landing_url"))
                or not isinstance(source.get("field_targets"), list)
                or not source["field_targets"]
                or not set(source["field_targets"]) <= TARGETS
                or source.get("automatic_import_allowed", False) is not False
                or source.get("market_imports", 0) != 0
                or source.get("market_confirmations", 0) != 0
                or source.get("publication_mode") is not None):
            raise ValueError("Unreviewed or unsafe high-yield candidate")
        observed.add(sid)
        priorities.add(priority)
        region = source.get("region")
        if source["scope"] == "regional":
            if not isinstance(region, str) or region not in by_region:
                raise ValueError("Regional research target absent from measured catalog")
            entry = by_region[region]
            # This region-wide figure is NEVER interpreted as the number of
            # matches with a source: no candidate rows have been read.
            upper = {
                "baseline_records_in_region": int(entry["records"]),
                "missing_hours_in_region": int(entry["missing_hours"])
                    if "hours" in source["field_targets"] else None,
                "missing_addresses_in_region": int(entry["missing_address"])
                    if "address" in source["field_targets"] else None,
                "imprecise_positions_in_region": int(entry["not_precise"])
                    if "coordinates" in source["field_targets"] else None,
                "not_verified_by_this_report": True,
            }
        else:
            if region is not None:
                raise ValueError("National thematic sources cannot claim regional match coverage")
            upper = None
        output.append({
            "id": sid, "priority": priority, "publisher": source["publisher"],
            "url": source["url"], "source_kind": source["source_kind"],
            "scope": source["scope"], "region": region,
            "field_targets": source["field_targets"],
            "rights_status": source["rights_status"],
            "already_has_connector": bool(source["existing_connector"]),
            "gap_upper_bounds_not_measured_matches": upper,
            "verified_matches": None, "market_updates_applied": 0,
            "future_openings_verified": 0,
            "next_action": source["next_action"],
        })
    output.sort(key=lambda item: item["priority"])
    return {
        "schema": 1, "research_only": True,
        "read_only": True, "regional_gap_snapshot_record_count":
        coverage["national"]["records"],
        "regional_gap_report_may_be_older_than_current_catalog": True,
        "sources": output, "markets_imported": 0, "markets_updated": 0,
        "openings_confirmed": 0,
    }


def markdown(result):
    rows = [
        "# Candidate fonti ad alto impatto — solo riconciliazione",
        "",
        "**Nessun mercato è stato aggiunto o verificato da questo report.**",
        "I numeri regionali sono i problemi nell'ultimo audit salvato,",
        "**non** quanti dati riusciremo a correggere con queste fonti.",
        "Il report di copertura potrebbe essere più vecchio del catalogo corrente.",
        "",
        "| Priorità | Fonte | Tipo | Regioni | Campi | Diritti / utilizzo |",
        "|---:|---|---|---|---|---|",
    ]
    for item in result["sources"]:
        fields = ", ".join(item["field_targets"])
        rows.append(
            f'| {item["priority"]} | [{item["publisher"]}]({item["url"]}) '
            f'| {item["source_kind"]} | {item["region"] or "Italia / rete"} '
            f'| {fields} | {item["rights_status"]} |')
    rows.extend(["", "## Margini misurati e prossimo passo", ""])
    for item in result["sources"]:
        rows.append(f'### {item["priority"]}. {item["publisher"]}: {item["id"]}')
        gaps = item["gap_upper_bounds_not_measured_matches"]
        if gaps:
            rows.append(
                f'- Ultimo audit regionale: {gaps["baseline_records_in_region"]:,} schede. '
                f'Orari assenti: {gaps["missing_hours_in_region"] if gaps["missing_hours_in_region"] is not None else "n/d"}; '
                f'indirizzi assenti: {gaps["missing_addresses_in_region"] if gaps["missing_addresses_in_region"] is not None else "n/d"}; '
                f'posizioni indicative: {gaps["imprecise_positions_in_region"] if gaps["imprecise_positions_in_region"] is not None else "n/d"}.')
        else:
            rows.append("- Copertura nazionale/tematica: **sovrapposizioni reali non ancora misurate**.")
        rows.append("- Permessi / stato: " + item["rights_status"])
        rows.append("- Da fare: " + item["next_action"])
        rows.append("")
    return "\n".join(rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--registry", type=Path,
                   default=Path("backend/data/high-yield-source-leads-2026-10-17.json"))
    p.add_argument("--coverage", type=Path,
                   default=Path("reports/automation/data-coverage.json"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    registry = json.loads(args.registry.read_text("utf-8"))
    coverage = json.loads(args.coverage.read_text("utf-8"))
    result = analyze(registry, coverage)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False,
                                   indent=2, sort_keys=True) + "\n", "utf-8")
    args.report.write_text(markdown(result), "utf-8")
    print(json.dumps({"sources": len(result["sources"]), "imports": 0,
                      "updates": 0, "event_confirmations": 0}))


if __name__ == "__main__":
    main()
