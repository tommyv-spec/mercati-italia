#!/usr/bin/env python3
"""Create one stable, testable GitHub issue payload for freshness debt.

This program does not contact GitHub, fetch data or send notifications.
The scheduler may use the JSON output to create/update one issue only when
the signal changes; repeating the same input is idempotent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

TITLE = "[Mercati autopilot] Dati da verificare"


def build(freshness, source_changes=None):
    if freshness.get("schema") != 1 or not isinstance(freshness.get("metrics"), dict):
        raise ValueError("Freshness report schema mismatch")
    m = freshness["metrics"]
    changes = source_changes or {}
    if changes and (changes.get("schema") != 1 or changes.get("imported_markets") != 0):
        raise ValueError("Invalid publisher change review")
    total = int(m.get("total", 0))
    problem = {
        "total": total,
        "without_verification": int(m.get("without_documented_verification", 0)),
        "stale_source": int(m.get("source_date_outside_limit", 0)),
        "unknown_source_date": int(m.get("source_date_unknown", 0)),
        "stale_forecast": int(m.get("forecast_from_stale_or_unknown_source", 0)),
        "unsupported_confirmation": int(m.get("confirmation_without_documented_evidence", 0)),
        "publisher_unavailable": sorted(
            str(p.get("publisher", "")) for p in freshness.get("publisher_evidence", [])
            if p.get("status") not in ("metadata_checked", "offline")
        ),
        "publisher_new_data_claims": sorted(
            str(p.get("publisher", "")) for p in changes.get("results", [])
            if p.get("change_type") == "publisher_data_date_advanced"
        ),
        "municipal_csv_changed": sorted(
            str(p.get("publisher", "")) for p in changes.get("results", [])
            if p.get("change_type") == "municipal_csv_bytes_changed"
        ),
    }
    if any(not isinstance(n, int) or n < 0 for n in problem.values()
           if isinstance(n, int)):
        raise ValueError("Invalid freshness metrics")
    attention = any((
        problem["without_verification"] > 0,
        problem["stale_source"] > 0,
        problem["unknown_source_date"] > 0,
        problem["stale_forecast"] > 0,
        problem["unsupported_confirmation"] > 0,
        bool(problem["publisher_unavailable"]),
        bool(problem["publisher_new_data_claims"]),
        bool(problem["municipal_csv_changed"]),
    ))
    signature = hashlib.sha256(json.dumps(
        problem, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode()).hexdigest()[:16]
    markdown = "\n".join([
        "Controllo automatico della qualità e attualità delle fonti, **non** un errore di deploy.",
        "Nessun orario o mercato è stato verificato automaticamente.",
        "",
        f"- Schede: {problem['total']:,}",
        f"- Senza verifica documentata: {problem['without_verification']:,}",
        f"- Fonte vecchia oltre soglia: {problem['stale_source']:,}",
        f"- Fonte senza data: {problem['unknown_source_date']:,}",
        f"- Date previste da fonte vecchia/sconosciuta: {problem['stale_forecast']:,}",
        f"- Date confermate senza prova: {problem['unsupported_confirmation']:,}",
        f"- Publisher non raggiungibili / metadati cambiati: {', '.join(problem['publisher_unavailable']) or 'nessuno'}",
        f"- Enti che dichiarano dati aggiornati rispetto al controllo precedente: {', '.join(problem['publisher_new_data_claims']) or 'nessuno'}",
        f"- CSV comunali cambiati (richiedono nuova verifica): {', '.join(problem['municipal_csv_changed']) or 'nessuno'}",
        "",
        "Correggere le fonti autorizzate e gli adapter ripetibili. Mai creare verifiche manuali fittizie.",
        "",
        f"Firma stato: {signature}",
    ])
    return {
        "title": TITLE,
        "attention_required": attention,
        "signature": signature,
        "problems": problem,
        "body": markdown,
    }


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--freshness", type=Path, required=True)
    p.add_argument("--source-changes", type=Path)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    data = json.loads(args.freshness.read_text("utf-8"))
    changes = json.loads(args.source_changes.read_text("utf-8")) if (
        args.source_changes and args.source_changes.is_file()) else None
    result = build(data, changes)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
                        encoding="utf-8")
    print(json.dumps({"attention_required": result["attention_required"],
                      "signature": result["signature"]}))


if __name__ == "__main__":
    main()
