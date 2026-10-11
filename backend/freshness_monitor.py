#!/usr/bin/env python3
"""Re-runnable freshness monitor for market catalogs and official source metadata.

A successful pipeline run is NOT a confirmation that the markets are current.
No network calls, edits, imports, date generation, or publisher approvals here.
The same inputs/reference date produce the same metrics and QA findings.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from merge_catalog import load_existing

SCHEMA = 1
MAX_EXAMPLES = 20


def as_day(value):
    if not isinstance(value, str) or not re.match(r"^\d{4}-\d\d-\d\d(?:$|[T ])", value):
        return None
    try:
        return date.fromisoformat(value[:10])
    except ValueError:
        return None


def days_since(value, today):
    parsed = as_day(value)
    return None if parsed is None else (today - parsed).days


def analyze(records, today, publisher_evidence=None, max_source_age_days=540):
    if not isinstance(records, list) or max_source_age_days < 1:
        raise ValueError("Invalid catalog or freshness policy")
    counts = Counter()
    by_origin = Counter()
    examples = {"stale_projected": [], "unknown_origin": [],
                "confirmation_without_evidence": [], "future_source_timestamp": []}
    unique = set()
    for row in records:
        if not isinstance(row, dict) or not row.get("slug"):
            raise ValueError("Catalog contains records with no market identity")
        slug = row["slug"]
        if slug in unique:
            raise ValueError("Duplicate source identity in market catalog")
        unique.add(slug)
        counts["total"] += 1

        age = days_since(row.get("aggiornato_il"), today)
        if age is None:
            counts["source_date_unknown"] += 1
            if len(examples["unknown_origin"]) < MAX_EXAMPLES:
                examples["unknown_origin"].append(slug)
        elif age < 0:
            counts["future_dated_source"] += 1
            if len(examples["future_source_timestamp"]) < MAX_EXAMPLES:
                examples["future_source_timestamp"].append(slug)
        elif age <= 30:
            counts["source_date_within_30d"] += 1
        elif age <= 90:
            counts["source_date_31_to_90d"] += 1
        elif age <= 365:
            counts["source_date_91_to_365d"] += 1
        elif age <= max_source_age_days:
            counts["source_date_366_to_limit"] += 1
        else:
            counts["source_date_outside_limit"] += 1

        if not row.get("verificato_il"):
            counts["without_documented_verification"] += 1
        else:
            counts["with_documented_verification"] += 1

        if row.get("date_quality") == "confermata" and not row.get("verificato_il"):
            counts["confirmation_without_documented_evidence"] += 1
            if len(examples["confirmation_without_evidence"]) < MAX_EXAMPLES:
                examples["confirmation_without_evidence"].append(slug)

        upcoming = [day for day in row.get("date", [])
                    if as_day(day) is not None and as_day(day) >= today]
        if upcoming:
            counts["with_any_future_date"] += 1
            if row.get("date_quality") == "prevista":
                counts["with_forecast_dates"] += 1
                if age is None or age < 0 or age > max_source_age_days:
                    counts["forecast_from_stale_or_unknown_source"] += 1
                    if len(examples["stale_projected"]) < MAX_EXAMPLES:
                        examples["stale_projected"].append(slug)

        if row.get("url_fonte"):
            url = urlsplit(str(row["url_fonte"]))
            if url.scheme not in ("https", "http") or not url.hostname:
                counts["invalid_primary_source_url"] += 1
            else:
                by_origin[url.hostname] += 1
        else:
            counts["missing_primary_source_url"] += 1

    source_reports = []
    metadata = publisher_evidence or {}
    if metadata:
        if (not isinstance(metadata, dict) or metadata.get("schema") != 1
                or metadata.get("market_imports") != 0):
            raise ValueError("Untrusted publisher metadata evidence")
        for entry in metadata.get("source_evidence", []):
            source_reports.append({
                "publisher": str(entry.get("publisher") or "")[:100],
                "status": str(entry.get("status") or "unknown")[:40],
                "last_publisher_data_change": entry.get("publisher_data_updated_at"),
                "license_comparison": entry.get("license_comparison"),
                "market_records_verified_by_metadata": 0,
            })
    counts = {name: int(n) for name, n in sorted(counts.items())}
    total = counts.get("total", 0)
    errors = []
    if counts.get("confirmation_without_documented_evidence", 0):
        errors.append("confirmed_events_without_documented_evidence")
    if counts.get("future_dated_source", 0):
        errors.append("source_timestamps_are_in_the_future")
    warnings = []
    if counts.get("without_documented_verification", 0) == total and total:
        warnings.append("no_record_has_documented_verification")
    if counts.get("forecast_from_stale_or_unknown_source", 0):
        warnings.append("future_predictions_have_stale_or_missing_source_dates")
    if counts.get("source_date_outside_limit", 0):
        warnings.append("source_data_older_than_allowed_forecast_window")
    if any(row["status"] not in ("metadata_checked", "offline")
           for row in source_reports):
        warnings.append("publisher_metadata_unavailable_or_changed")
    return {
        "schema": SCHEMA,
        "reference_date": today.isoformat(),
        "snapshot_measurement_not_event_verification": True,
        "max_source_age_days": max_source_age_days,
        "metrics": counts,
        "source_domains_top": [
            {"domain": name, "count": value}
            for name, value in by_origin.most_common(12)
        ],
        "publisher_evidence": source_reports,
        "examples": examples,
        "errors": errors,
        "warnings": warnings,
        "safe_for_automatic_quality_promotion": not errors,
        "catalog_was_modified": False,
    }


def markdown(result):
    m = result["metrics"]
    rows = [
        "# Mercati — controllo automatico di attualità",
        "",
        "**La data dell'ultimo script non è una verifica del mercato.**",
        "I dati sono aggiornabili solo quando l'ente pubblica prove nuove. Le "
        "ricorrenze previste rimangono stime.",
        "",
        f"- Data della misura: **{result['reference_date']}**.",
        f"- Schede totali: **{m.get('total', 0):,}**.",
        f"- Fonte datata entro 30 giorni: **{m.get('source_date_within_30d', 0):,}**.",
        f"- Fonte datata tra 31 e 365 giorni: **{m.get('source_date_31_to_90d', 0) + m.get('source_date_91_to_365d', 0):,}**.",
        f"- Fonte più vecchia del limite di {result['max_source_age_days']} giorni: **{m.get('source_date_outside_limit', 0):,}**.",
        f"- Fonti senza data: **{m.get('source_date_unknown', 0):,}**.",
        f"- Schede con date future previste: **{m.get('with_forecast_dates', 0):,}**.",
        f"- Previsioni basate su fonti troppo vecchie/sconosciute: **{m.get('forecast_from_stale_or_unknown_source', 0):,}**.",
        f"- Verifiche documentate: **{m.get('with_documented_verification', 0):,}**.",
        "",
        "## Alert",
        *[f"- BLOCCO: {line}" for line in result["errors"]],
        *[f"- Da correggere: {line}" for line in result["warnings"]],
        "",
        "## Enti controllati",
        "",
        "| Ente | Lettura metadati | Aggiornamento dati dichiarato |",
        "|---|---|---|",
    ]
    for item in result["publisher_evidence"]:
        rows.append(
            f"| {item['publisher'].replace('|', '/')} | "
            f"{item['status']} | {item['last_publisher_data_change'] or 'non disponibile'} |"
        )
    rows.extend([
        "", "## Limiti del sistema",
        "",
        "- Nessun download recente trasforma da solo una data prevista in confermata.",
        "- Una fonte datata da meno di 30 giorni può contenere appuntamenti non aggiornati.",
        "- I dati provenienti da siti terzi richiedono verifica delle condizioni di riuso.",
        "- In caso di anomalie, conservare il catalogo precedente e aprire una revisione.",
        "",
    ])
    return "\n".join(rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path,
                   default=Path("public/data/v1/manifest.json"))
    p.add_argument("--publisher-evidence", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--today", type=date.fromisoformat, default=date.today())
    p.add_argument("--max-source-age-days", type=int, default=540)
    p.add_argument("--fail-on-unsafe", action="store_true")
    args = p.parse_args()
    evidence = json.loads(args.publisher_evidence.read_text("utf-8")) if (
        args.publisher_evidence and args.publisher_evidence.is_file()) else None
    result = analyze(load_existing(args.manifest), args.today, evidence,
                     args.max_source_age_days)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    args.report.write_text(markdown(result), encoding="utf-8")
    print(json.dumps({
        "records": result["metrics"].get("total", 0),
        "errors": result["errors"], "warnings": result["warnings"],
        "safe_for_automatic_quality_promotion": result["safe_for_automatic_quality_promotion"],
    }, ensure_ascii=False))
    if args.fail_on_unsafe and not result["safe_for_automatic_quality_promotion"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
