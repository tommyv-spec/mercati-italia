#!/usr/bin/env python3
"""Read-only coverage map: prioritize field improvements, never invent markets.

The national totals alone hide where missing hours, addresses and actionable
dates cluster. This report gives bounded regional and municipality queues with
no changes to IDs, sources or visitor data.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from catalog_quality_report import suspicious_city
from merge_catalog import load_existing

FIELDS = (
    "missing_hours", "missing_address", "missing_future_date",
    "not_precise", "not_individually_verified",
)
WEIGHTS = {
    "missing_hours": 3, "missing_address": 2, "missing_future_date": 3,
    "not_precise": 1, "not_individually_verified": 2,
}


def summarize(rows: list[dict]) -> dict:
    if not isinstance(rows, list) or not rows:
        raise ValueError("Cannot score incomplete/empty catalog")
    seen = set()
    regions = defaultdict(list)
    cities = defaultdict(list)
    for row in rows:
        sid = row.get("slug")
        if not isinstance(sid, str) or not sid or sid in seen:
            raise ValueError("Duplicate or missing market ID in data coverage audit")
        seen.add(sid)
        reg = row.get("regione")
        city = row.get("citta")
        if not isinstance(reg, str) or not reg:
            raise ValueError("Missing market region")
        regions[reg].append(row)
        if isinstance(city, str) and city.strip() and not suspicious_city(city):
            cities[(reg, city.strip())].append(row)

    def metrics(group):
        result = {
            "records": len(group),
            "missing_hours": sum(not str(x.get("orario_testo") or "").strip() for x in group),
            "missing_address": sum(not str(x.get("indirizzo") or "").strip() for x in group),
            "missing_future_date": sum(not x.get("date") for x in group),
            "not_precise": sum(x.get("position_quality") != "precisa" for x in group),
            "not_individually_verified": sum(not x.get("verificato_il") for x in group),
        }
        result["weighted_field_gap"] = sum(result[k] * WEIGHTS[k] for k in FIELDS)
        result["missing_hours_pct"] = round(
            100 * result["missing_hours"] / result["records"], 1)
        result["missing_address_pct"] = round(
            100 * result["missing_address"] / result["records"], 1)
        return result

    national = metrics(rows)
    by_region = []
    for region, subset in regions.items():
        by_region.append({"region": region, **metrics(subset)})
    by_region.sort(key=lambda x: (-x["weighted_field_gap"], x["region"]))

    city_candidates = [
        {"region": reg, "city": city, **metrics(group)}
        for (reg, city), group in cities.items()
        if len(group) >= 5
    ]
    city_candidates.sort(key=lambda x: (-x["weighted_field_gap"], -x["records"],
                                        x["region"], x["city"]))
    focus = []
    per_region = defaultdict(int)
    for item in city_candidates:
        if per_region[item["region"]] < 2:
            focus.append(item)
            per_region[item["region"]] += 1
        if len(focus) == 16:
            break
    return {
        "schema": 1, "review_only": True, "market_updates_applied": 0,
        "market_confirmations_created": 0, "market_identities_deleted": 0,
        "source_evidence_replaced": 0,
        "national": national,
        "by_region": by_region,
        "priority_cities": focus,
        "priority_city_method": "weighted missing field count, max 2 municipalities/region, min 5 records",
    }


def markdown(result: dict) -> str:
    n = result["national"]
    out = [
        "# Mercati d'Italia — priorità di qualità dei dati",
        "",
        "**Analisi in sola lettura.** Nessun mercato, dato fonte o appuntamento modificato.",
        "",
        f"- Schede: **{n['records']:,}**",
        f"- Senza orari: **{n['missing_hours']:,}** ({n['missing_hours_pct']}%)",
        f"- Senza indirizzo: **{n['missing_address']:,}** ({n['missing_address_pct']}%)",
        f"- Senza prossime date: **{n['missing_future_date']:,}**",
        f"- Senza coordinate precise verificate: **{n['not_precise']:,}**",
        f"- Senza verifica singola documentata: **{n['not_individually_verified']:,}**",
        "",
        "## Regioni da migliorare (volume di dati mancanti, non punteggio di affidabilità)",
        "",
        "| Regione | Schede | Senza orario | Senza indirizzo | Senza prossima data | Gap pesato |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for r in result["by_region"]:
        out.append(f"| {r['region']} | {r['records']} | {r['missing_hours']} "
                   f"| {r['missing_address']} | {r['missing_future_date']} "
                   f"| {r['weighted_field_gap']} |")
    out += [
        "", "## Comuni da verificare prima",
        "",
        "Fino a due per regione. È una coda di approfondimento: **non** prova che gli orari online siano corretti.",
        "",
        "| Comune | Regione | Schede | Orari mancanti | Indirizzi mancanti | Date mancanti |",
        "|---|---|---:|---:|---:|---:|",
    ]
    for c in result["priority_cities"]:
        out.append(f"| {c['city'].replace('|','')} | {c['region']} | {c['records']} "
                   f"| {c['missing_hours']} | {c['missing_address']} "
                   f"| {c['missing_future_date']} |")
    out += ["", "Prima arricchire le schede con prove publisher concordanti, "
            "poi cercare sedi davvero nuove con ID separati e controllo dei doppioni.", ""]
    return "\n".join(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    result = summarize(load_existing(args.manifest))
    for path in (args.out, args.report):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", "utf-8")
    args.report.write_text(markdown(result), "utf-8")
    print("MARKET_COVERAGE", json.dumps(result["national"], ensure_ascii=False))


if __name__ == "__main__":
    main()
