"""Unattended local Happings source refresh + complete QA, no publication.

Intended for one daily OS task on the user's authorized computer. No paid
service, no GitHub workflow, no local Docker and no automatic overwrite of DEV
market records. Uses the existing per-snapshot lock and source robots policy.
"""
from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from happings_bulk_refresh import refresh
from happings_bulk_finisher import finish
from happings_bulk_snapshot import write_json

DEFAULT_ROOT = Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir()) / "mercati-italia"


def run(*, snapshot, out, repo, max_pages=70, discovery_days=1):
    snapshot, out, repo = map(Path, (snapshot, out, repo))
    out.mkdir(parents=True, exist_ok=True)
    status_file = out / "happings-local-run.json"
    started_at = datetime.now(timezone.utc).isoformat()
    result = {
        "schema": 1, "started_at": started_at, "status": "running",
        "snapshot": str(snapshot), "repo": str(repo),
        "max_pages": max_pages, "discovery_days": discovery_days,
        "production_modified": False, "github_paid_services_used": False,
    }
    write_json(status_file,result)
    try:
        refreshed = refresh(snapshot,max_pages=max_pages,discovery_days=discovery_days)
        # Discovery can append more pages than the bounded per-run budget.
        # That is ordinary progress, not a failed crawl or a complete QA.
        if refreshed.get("pages_pending",0):
            result.update(status="in_progress",refresh=refreshed,
                          qa={"complete":False,"reason":"new_source_pages_pending"},
                          completed_at=datetime.now(timezone.utc).isoformat())
        else:
            finished = finish(snapshot,repo=repo,out=out)
            if finished.get("complete") is not True:
                raise ValueError("Happings first-pass snapshot must be complete before reporting")
            result.update(status="completed",refresh=refreshed,qa=finished,
                          completed_at=datetime.now(timezone.utc).isoformat())
    except Exception as error:
        result.update(status="failed",error_type=type(error).__name__,
                      error=str(error)[:600],
                      completed_at=datetime.now(timezone.utc).isoformat())
        write_json(status_file,result)
        raise
    write_json(status_file,result)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--snapshot",type=Path,default=DEFAULT_ROOT/"happings-full-crawl")
    parser.add_argument("--out",type=Path,default=DEFAULT_ROOT/"happings-reconciliation")
    parser.add_argument("--repo",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--max-pages",type=int,default=70)
    parser.add_argument("--discovery-days",type=int,default=1)
    args=parser.parse_args()
    result=run(snapshot=args.snapshot,out=args.out,repo=args.repo,
               max_pages=args.max_pages,discovery_days=args.discovery_days)
    print(json.dumps({"status":result["status"],
        "refresh":result["refresh"],"qa":result["qa"]},
        ensure_ascii=False,sort_keys=True),flush=True)


if __name__ == "__main__":
    main()
