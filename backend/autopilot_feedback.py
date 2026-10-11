#!/usr/bin/env python3
"""Measure where automation should invest next, without inventing evidence.

Produces a prioritized improvement queue from measured catalog QA. This file
never edits markets or authoritatively verifies times, addresses or licenses.
It can run after every autopilot cycle and surface testable tasks as a report.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path


def measure_issue(code: str, severity: int, affected: int, total: int,
                  automation_possible: str, action: str, acceptance: str,
                  confidence: float = 0.9, implementation_cost: int = 3) -> dict:
    prevalence = affected / max(total, 1)
    # Higher prevalence / confidence / severity and lower effort -> higher priority.
    score = round(severity * (0.25 + prevalence) * confidence /
                  max(1, implementation_cost), 3)
    return {
        "code": code, "priority_score": score,
        "severity": severity, "affected_records": affected,
        "affected_percent": round(prevalence * 100, 2),
        "mode": automation_possible, "action": action,
        "acceptance": acceptance,
    }


def opportunities(metrics: dict, prior_metrics: dict | None = None) -> dict:
    total = int(metrics["snapshot_total"])
    missing = metrics.get("fields_missing", {})
    sources = metrics.get("sources", [])
    sources_top = sources[0] if sources else {"name":"none","count":0}
    coord_precise = metrics.get("position_quality", {}).get("precisa", 0)
    date60 = int(metrics.get("compact_index_future_coverage", {}).get("60", 0))
    city_duplicates = metrics.get("cities_with_variant_spellings", 0)
    no_verified = missing.get("verified_at", total)
    missing_source = missing.get("source_url", 0)
    issues = [
        measure_issue("verified_source_evidence", 10, no_verified, total,
            "requires primary-source verification",
            "Prioritize signed municipal/organizer confirmation and provenance per item; never create verified flags from predictions.",
            "Increase documented 'verificato_il' by accepting only auditable primary-source evidence; spot-check a sample.",
            implementation_cost=9),
        measure_issue("opening_hours_coverage", 7, missing.get("hours", 0), total,
            "official connector automation + review",
            "Find source datasets with explicit opening hours. Import field only with direct provenance and last-updated date.",
            "Higher hourly coverage in next audited snapshot without filling placeholders as known hours.",
            implementation_cost=5),
        measure_issue("location_precision", 8, total - coord_precise, total,
            "official structured-data source connectors",
            "Prefer municipality coordinates and street addresses. Never assign municipal centroid as exact market pin.",
            "Measured increase in precise coordinates with official source references and regional distribution.",
            implementation_cost=7),
        measure_issue("recurring_date_coverage", 9, max(0, total-date60), total,
            "deterministic recurrence engine",
            "Refresh only explicit source-bound recurrences, keep 'prevista' labels, quarantine historical/unknown schedules.",
            "At least 8,000 forecastable markets still have dates at +60 days without increasing false confirmations.",
            implementation_cost=2),
        measure_issue("supplier_concentration", 8, sources_top.get("count", 0), total,
            "automated government open-data discovery + source-adapter review",
            "Discover public municipal CSV/GeoJSON datasets; verify license, then develop a reviewed importer. Do not scrape unauthorized portals.",
            "No single unaudited source dominates 75% of the catalog; all permitted reuse documented.",
            implementation_cost=7),
        measure_issue("cities_normalization", 5, int(city_duplicates), total,
            "deterministic rules and golden tests",
            "Create canonical municipality/province IDs; keep homonymous cities separate and fix two-letter province-as-city errors.",
            "Zero duplicate case-only city labels in filters; correct homonymous cities using region/province.",
            implementation_cost=3),
        measure_issue("source_attribution", 9, missing_source, total,
            "source provenance validation",
            "Quarantine records without an attributable, licensed original URL rather than silently publishing them.",
            "All newly added records have attributable provenance and license review status.",
            implementation_cost=3),
    ]
    if prior_metrics:
        previous = int(prior_metrics.get("compact_index_future_coverage",{}).get("60", 0))
        if date60 + 100 < previous:
            issues.append(measure_issue("date_coverage_regression", 10, previous - date60, total,
                "auto fail-closed monitoring",
                "Investigate source breakages or stale snapshots; refuse publication pending diagnosis.",
                "Restore coverage without inventing event dates.",
                implementation_cost=1))
    issues.sort(key=lambda x: (-x["priority_score"], x["code"]))
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "catalog_records": total,
        "date_coverage_60_days": date60,
        "top_source": sources_top,
        "metrics_are_observed_not_verified_events": True,
        "queue": issues,
    }


def as_markdown(result: dict) -> str:
    lines = [
        "# Mercati Autopilot — miglioramento continuo",
        "",
        "**Priorità generate automaticamente dai dati.** Nessun evento viene verificato, aggiunto o cancellato da questo report.",
        "",
        f"Catalogo: **{result['catalog_records']:,}** record | Copertura +60 giorni: **{result['date_coverage_60_days']:,}**",
        "",
        "| Priorità | Ambito | Copertura problema | Automazione |",
        "|---:|---|---:|---|",
    ]
    for i, issue in enumerate(result["queue"], 1):
        lines.append(f"| {i} | {issue['code']} | {issue['affected_percent']}% | {issue['mode']} |")
    lines.append("")
    for issue in result["queue"]:
        lines.extend([
            f"## {issue['code']}",
            f"**Metodo:** {issue['action']}",
            f"**Criterio di accettazione:** {issue['acceptance']}",
            "",
        ])
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, default=Path("public/data/v1/manifest.json"))
    p.add_argument("--metrics", type=Path)
    p.add_argument("--previous", type=Path)
    p.add_argument("--out", type=Path, default=Path("autopilot-output/roadmap.json"))
    args = p.parse_args()
    if args.metrics:
        metrics=json.loads(args.metrics.read_text("utf-8"))
    else:
        from audit_dataset import audit
        metrics=audit(args.manifest)
    previous=json.loads(args.previous.read_text("utf-8")) if args.previous else None
    result=opportunities(metrics,previous)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n","utf-8")
    args.out.with_suffix(".md").write_text(as_markdown(result),"utf-8")
    print(json.dumps({
        "priorities":[i["code"] for i in result["queue"][:5]],
        "catalog":result["catalog_records"],
        "date_coverage_60_days":result["date_coverage_60_days"]
    },ensure_ascii=False,indent=2))


if __name__=="__main__":
    main()
