#!/usr/bin/env python3
"""Rebuild a committed snapshot under newer normalization rules with no DB calls."""
import argparse
import json
from pathlib import Path

from merge_catalog import load_existing
from export_static import export
from validate_static import validate


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("public/data/v1/manifest.json"))
    parser.add_argument("--prune-stale", action="store_true",
                        help="Safe only before first production release")
    args = parser.parse_args()
    if not args.manifest.exists():
        raise ValueError("No snapshot to reprocess")
    old = json.loads(args.manifest.read_text("utf-8"))
    old_paths = ([old["catalog"]] if old.get("layout") == "single"
                 else [part["path"] for part in old["regions"]])
    baseline = load_existing(args.manifest)
    result = export(baseline, args.manifest.parent, min_count=20, max_drop_ratio=0.1)
    checked = validate(args.manifest)
    if args.prune_stale:
        latest = result["manifest"]
        new_paths = set(([latest["catalog"]] if latest["layout"] == "single"
                         else [part["path"] for part in latest["regions"]]))
        root = args.manifest.parent.parent.parent
        for path in old_paths:
            if path not in new_paths:
                candidate = root / path
                if candidate.is_file():
                    candidate.unlink()
    print(json.dumps({"quality": result["stats"], "validated": checked},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
