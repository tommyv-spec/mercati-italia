#!/usr/bin/env python3
"""Replay original LIVE7 weekly responses; no HTTP and no source re-dating."""
from __future__ import annotations

import argparse
from collections import Counter
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import types
from unittest.mock import patch

parser = argparse.ArgumentParser()
parser.add_argument("--repo", type=Path, required=True)
parser.add_argument("--artifact", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()
sys.path.insert(0, str(args.repo / "backend"))
import happings_autopilot as phase
import happings_source_enrichment as source
import happings_weekly_layout as weekly
from export_static import export, normalize
from merge_catalog import load_existing

DAY = date(2026, 10, 20)
OLD_REF = "6e58d56c50d29d81d985f1e7617628e23a8f81c7"
args.output.mkdir(parents=True, exist_ok=True)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write(name, value):
    (args.output / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def old_module(name):
    text = subprocess.check_output(["git", "show", OLD_REF + ":backend/" + name + ".py"], cwd=args.repo)
    module = types.ModuleType("baseline_" + name)
    module.__file__ = str(args.repo / "backend" / (name + ".py"))
    sys.modules[module.__name__] = module
    exec(compile(text, module.__file__, "exec"), module.__dict__)
    return module


manifest_path = args.artifact / "candidate/public/data/v1/manifest.json"
manifest = json.loads(manifest_path.read_text())
base = load_existing(manifest_path)
saved = json.loads((args.artifact / "sources/happings-pages.json").read_text())
assert saved["context"]["today"] == DAY.isoformat()
pages = phase._unpack_pages(saved, saved["context"])
old_weekly = old_module("happings_weekly_layout")
old_source = old_module("happings_source_enrichment")
old_source.parse = old_weekly.parse

comparisons = []
editorial_pages = []
for page in pages:
    current = weekly.parse(page["html"], source_url=page["final_url"], observed_on=DAY)
    item = {"requested_url": page["requested_url"], "final_url": page["final_url"],
            "sha256": hashlib.sha256(page["html"]).hexdigest(), "bytes": len(page["html"]),
            "read_on": DAY.isoformat(), "current_source_rows": len(current.rows)}
    try:
        previous = old_weekly.parse(page["html"], source_url=page["final_url"], observed_on=DAY)
    except ValueError:
        item["previous_status"] = "layout_changed"
        item["current_status"] = "parsed_editorial_scopes"
        assert getattr(current, "editorial_sections", None)
        item["editorial_sections"] = current.editorial_sections
        editorial_pages.append(page)
    else:
        assert previous.rows == current.rows
        assert previous.page_metadata == current.page_metadata
        item.update(previous_status="parsed", current_status="parsed", extracted_rows_byte_equivalent=True,
                    page_metadata_equal=True)
    comparisons.append(item)
assert len(pages) == 14 and len(editorial_pages) == 1
old_after, old_report = old_source.preview(base, pages, today=DAY, apply=True, rights_verified=True)
assert old_source.safe_report(old_report, base)

full_policy = json.loads((args.repo / "backend/autopilot_policy.json").read_text())
policy = {**full_policy["happings_enrichment"], "details": {"enabled": False},
          "legacy_resolution": {"enabled": False}}
selected = [page["requested_url"] for page in pages]


def captured(urls, **kwargs):
    assert urls == selected
    assert kwargs.get("permission_confirmed") is True
    return pages


# This is an extraction/release replay of the already selected responses,
# not another queue scheduling test or a claim of fresh network acquisition.
with patch.object(source, "select_pages", return_value=selected), patch(
        "urllib.request.OpenerDirector.open", side_effect=AssertionError("No HTTP in captured replay")):
    after, report, protected = phase.run(
        base, policy=policy, out=args.output, today=DAY,
        baseline_signature=manifest["content_signature"], pipeline_policy_digest=phase.digest(full_policy),
        fetcher=captured)
    assert phase.verify_changes(base, after, report, source_pages=pages)
    exported = export(after, args.output / "candidate/public/data/v1", today=DAY,
                      min_count=len(base), preserve_ids=protected)
    rows = load_existing(args.output / "candidate/public/data/v1/manifest.json")
    guard = phase.verify_exported(base, after, rows, report, today=DAY, source_checkpoint_dir=args.output)
    offline, offline_report, _ = phase.run(
        rows, policy=policy, out=args.output / "offline-followup", today=DAY,
        baseline_signature=exported["manifest"]["content_signature"],
        pipeline_policy_digest=phase.digest(full_policy), offline=True,
        fetcher=lambda *a, **k: (_ for _ in ()).throw(AssertionError("Offline fetch")))
assert offline == rows
assert [row["slug"] for row in base] == [row["slug"] for row in after]
assert {row["slug"] for row in rows} == {row["slug"] for row in base}
changes = []
for old, new in zip(base, after):
    if old != new:
        fields = {key for key in old.keys() | new.keys() if old.get(key) != new.get(key)}
        assert fields == {"conflitti_campi"}
        changes.append({"market_id": old["slug"], "fields": sorted(fields),
                        "before": old, "after": new})
assert len(changes) == 2
assert old_after == base
assert all(normalize(row, DAY)[0] == next_row for row, next_row in
           zip(sorted(after, key=lambda row: row["slug"]), sorted(rows, key=lambda row: row["slug"])))
page = editorial_pages[0]
parsed = weekly.parse(page["html"], source_url=page["final_url"], observed_on=DAY)
linked = [row for row in base if source.record_matches_page(row, page["requested_url"], page["final_url"])]
assert len(linked) == 60
by_id = {row["slug"]: row for row in after}
all60 = [{"market_id": row["slug"], "unchanged": row == by_id[row["slug"]],
          "fields_changed": sorted(key for key in row.keys() | by_id[row["slug"]].keys()
                                    if row.get(key) != by_id[row["slug"]].get(key))} for row in linked]
counts = Counter(row["editorial_scope"]["status"] for row in parsed.rows)
write("changed-rows.json", changes)
write("all-60-lucca-comparison.json", all60)
summary = {
    "schema": 1, "mode": "CACHED_REPLAY", "actual_network_requests": 0,
    "artifact_run": "39487468359", "source_date_preserved": DAY.isoformat(),
    "baseline_code": OLD_REF, "baseline_manifest_sha256": sha(manifest_path),
    "source_checkpoint_sha256": sha(args.artifact / "sources/happings-pages.json"),
    "baseline_records": len(base), "output_records": len(rows),
    "source_pages": comparisons, "unchanged_layout_pages": 13,
    "new_editorial_layout_pages": 1, "all_60_compared": len(all60),
    "editorial_source_scopes": dict(counts),
    "record_changes": len(changes), "changed_fields": {"conflitti_campi": len(changes)},
    "all_other_record_fields_identical": True, "all_ids_preserved": True,
    "old_parser_replay_record_changes": old_report["record_changes"],
    "field_values_changed": report["evidence"]["field_changes"],
    "historical_rows_never_promoted": all(row["calendar_scope"] and not row["has_specific_location"]
        for row in parsed.rows if row["editorial_scope"]["status"] == "historical_unverified"),
    "current_clock_facts_parsed_not_applied": sum(row["clock_hours"] is not None for row in parsed.rows),
    "static_guard": guard, "export_stats": exported["stats"],
    "output_manifest_sha256": sha(args.output / "candidate/public/data/v1/manifest.json"),
    "offline_followup_identical": offline == rows,
    "offline_status": offline_report["status"],
    "scope_limit": "Frozen captured weekly selection; details, legacy discovery and other publishers skipped. Not a fresh crawl or a full MAIN workflow run.",
}
write("summary.json", summary)
print(json.dumps({key: summary[key] for key in ("mode", "baseline_records", "output_records",
    "unchanged_layout_pages", "new_editorial_layout_pages", "editorial_source_scopes", "record_changes",
    "all_other_record_fields_identical", "field_values_changed", "offline_followup_identical")}, ensure_ascii=False))
