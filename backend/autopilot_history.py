#!/usr/bin/env python3
"""Persist self-measured Autopilot scorecards and bounded trend history on DEV.

Written ONLY after security/browser QA passes. No user/location identifiers or
raw-source rows are stored in the long-term report: only aggregate counts,
quality gates, discoverable sources and prioritized methodology improvements.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

HISTORY_LIMIT = 104  # roughly 1 year at two checks per week


def summary(decision: dict, roadmap: dict | None, source_candidates: dict | None,
            run_id: str) -> dict:
    if decision.get("approved") is not True:
        raise ValueError("Cannot persist a failed candidate as a successful run")
    metric = decision.get("candidate", {})
    if "records" not in metric or "future_60" not in metric:
        raise ValueError("Incomplete quality report")
    return {
        "run_id": str(run_id),
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "quality_approved": True,
        "catalog_changed": bool(decision.get("has_changes")),
        "record_count": int(metric["records"]),
        "predicted_60d": int(metric["future_60"]),
        "predicted_90d": int(metric["future_90"]),
        "index_gzip_bytes": int(metric["indexed_gzip_bytes"]),
        "documented_verification_count": int(metric["verified"]),
        "precise_position_count": int(metric["precise"]),
        "hours_missing": int(metric["missing_hours"]),
        "source_candidates_scored": len((source_candidates or {}).get("candidates", [])),
        "source_scout_failures": len((source_candidates or {}).get("query_failures", {})),
        "top_improvement_priorities": [
            item["code"] for item in (roadmap or {}).get("queue", [])[:5]
        ],
        "failed_release_gates": [k for k, v in decision.get("gates", {}).items() if not v],
        "dev_only": True,
        "workflow_url": (
            "https://github.com/tommyv-spec/mercati-italia/actions/runs/" + str(run_id)
        ),
    }


def markdown(latest: dict) -> str:
    return "\n".join([
        "# Mercati Autopilot — ultimo stato automatico",
        "",
        "**Questo report viene aggiornato dagli script, non manualmente.**",
        "",
        f"- Ultimo run: [{latest['run_id']}]({latest['workflow_url']}) — UTC {latest['recorded_utc']}",
        f"- Qualità DEV: {'APPROVATA' if latest['quality_approved'] else 'BLOCCATA'}",
        f"- Nuova versione di dati: {'sì' if latest['catalog_changed'] else 'no (contenuto invariato)'}",
        f"- Schede nel catalogo: **{latest['record_count']:,}**",
        f"- Schede con date previste a +60 giorni: **{latest['predicted_60d']:,}**",
        f"- Schede con date previste a +90 giorni: **{latest['predicted_90d']:,}**",
        f"- Indice nazionale gzip: **{latest['index_gzip_bytes'] / 1024:.1f} KiB**",
        f"- Verifiche documentate: **{latest['documented_verification_count']}**",
        f"- Posizioni precise dichiarate: **{latest['precise_position_count']}**",
        f"- Orari mancanti: **{latest['hours_missing']:,}**",
        f"- Dataset pubblici candidati individuati: **{latest['source_candidates_scored']}** (licenze da verificare)",
        "",
        "## Prossimi miglioramenti calcolati",
        *[f"- {p}" for p in latest["top_improvement_priorities"]],
        "",
        "Il catalogo resta in DEV. Le date previste non sono conferme degli organizzatori.",
        "",
    ])


def save_history(folder: Path, item: dict):
    folder.mkdir(parents=True, exist_ok=True)
    history_file = folder / "history.jsonl"
    previous = []
    if history_file.is_file():
        for line in history_file.read_text("utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if isinstance(row, dict) and "run_id" in row:
                previous.append(row)
    previous = [row for row in previous if row["run_id"] != item["run_id"]]
    items = (previous + [item])[-HISTORY_LIMIT:]
    history_file.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True)+"\n" for row in items),
        encoding="utf-8"
    )
    (folder / "latest.json").write_text(
        json.dumps(item, ensure_ascii=False, sort_keys=True, indent=2)+"\n", "utf-8"
    )
    (folder / "LATEST.md").write_text(markdown(item), "utf-8")
    return len(items)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--decision", type=Path, required=True)
    p.add_argument("--roadmap", type=Path)
    p.add_argument("--sources", type=Path)
    p.add_argument("--run-id", required=True)
    p.add_argument("--out", type=Path, default=Path("reports/automation"))
    args = p.parse_args()
    value = summary(
        json.loads(args.decision.read_text("utf-8")),
        json.loads(args.roadmap.read_text("utf-8")) if args.roadmap and args.roadmap.exists() else None,
        json.loads(args.sources.read_text("utf-8")) if args.sources and args.sources.exists() else None,
        args.run_id
    )
    count = save_history(args.out, value)
    print(json.dumps({"last_run":value["run_id"],"quality_approved":True,
                      "history_entries":count,"candidates":value["source_candidates_scored"]},
                     ensure_ascii=False))


if __name__=="__main__":
    main()
