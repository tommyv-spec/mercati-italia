#!/usr/bin/env python3
"""Read-only impact simulation for rolling predicted market dates.

Reads committed static shards, never fetches external sources, never writes
to the published catalog. Exports into a temporary directory to compare
actual index size, future search coverage, record counts and provenance.
"""
from __future__ import annotations
import argparse
import json
import tempfile
from datetime import date, timedelta
from pathlib import Path

from audit_dataset import audit
from export_static import export
from merge_catalog import load_existing
from recurrence_refresh import refresh_records


def simulate(manifest: Path, today: date, horizon_days=120, stale_days=540):
    old = audit(manifest, today)
    existing = load_existing(manifest)
    fresh, forecast = refresh_records(existing, today, horizon_days, stale_days)
    if len(fresh) != len(existing):
        raise ValueError("Source count changed during recurrence-only refresh")
    for before, after in zip(existing, fresh):
        if before["slug"] != after["slug"] or before.get("url_fonte") != after.get("url_fonte"):
            raise ValueError("Forecast mutated market identity/source evidence")

    with tempfile.TemporaryDirectory(prefix="mercati-recurrence-") as workdir:
        out = Path(workdir) / "public" / "data" / "v1"
        generated = export(fresh, out, today=today, min_count=12000,
                           max_drop_ratio=0.10)
        if generated["stats"]["accepted"] < int(old["snapshot_total"] * 0.98):
            raise ValueError("Too many markets were lost during read-only dry run")
        new = audit(out / "manifest.json", today)
    future_days = ("30", "60", "90")
    report = {
        "today": today.isoformat(),
        "baseline": {
            "records": old["snapshot_total"],
            "index_gzip_bytes": old["sizes"]["national_index_gzip_bytes"],
            "index_future_coverage": {k: old["compact_index_future_coverage"][k] for k in future_days},
            "full_future_coverage": {k: old["full_catalog_future_coverage"][k] for k in future_days},
        },
        "post_forecast": {
            "records": new["snapshot_total"],
            "index_gzip_bytes": new["sizes"]["national_index_gzip_bytes"],
            "index_future_coverage": {k: new["compact_index_future_coverage"][k] for k in future_days},
            "full_future_coverage": {k: new["full_catalog_future_coverage"][k] for k in future_days},
        },
        "forecast": forecast,
        "released": False,
        "assertions": {
            "record_count_preserved": new["snapshot_total"] == old["snapshot_total"],
            "no_confirmed_dates_invented": forecast["all_dates_marked_forecast"],
            "index_survives_60_days": new["compact_index_future_coverage"]["60"] >=
                old["compact_index_future_coverage"]["60"],
        },
    }
    if not all(report["assertions"].values()):
        raise ValueError("Dry-run quality gates failed")
    return report


if __name__ == "__main__":
    p=argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, default=Path("public/data/v1/manifest.json"))
    p.add_argument("--today", type=date.fromisoformat, default=date.today())
    p.add_argument("--out", type=Path, default=Path("reports/audit/recurrence-impact.json"))
    p.add_argument("--horizon-days", type=int, default=120)
    p.add_argument("--max-stale-days", type=int, default=540)
    args=p.parse_args()
    result=simulate(args.manifest, args.today, args.horizon_days, args.max_stale_days)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False)+"\n","utf-8")
    print(json.dumps(result, ensure_ascii=False, indent=2))
