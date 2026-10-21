"""Complete Happings source-to-DEV audit after the local full scrape finishes.

This watcher performs no Happings HTTP requests. It reads the atomic scraper
checkpoint and, after the last URL, compares saved source facts against the
newest DEV static catalog from a read-only GitHub fetch. No billed service or
production write. It can safely run alongside the active scraper.
"""
from __future__ import annotations
import argparse
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

from happings_full_reconciliation import analyze
from happings_detail_matching_report import run as audit_detail_matches
from happings_retry_failures import retry as retry_failures

DEV="improve/data-quality-security-performance-2026-10-11"


def progress(directory):
    path=Path(directory)/"checkpoint.json"
    if not path.is_file():
        return 0, None
    state=json.loads(path.read_text(encoding="utf-8"))
    if (state.get("schema") != 1 or not isinstance(state.get("queue"),list)
            or not isinstance(state.get("done"),dict)
            or len(set(state["queue"])) != len(state["queue"])
            or not set(state["done"]).issubset(state["queue"])):
        raise ValueError("Happings scan checkpoint corrupted during automated verification")
    return len(state["done"]), len(state["queue"])


def current_dev_catalog(repo, dest):
    """Extract only the trusted DEV catalog files, without modifying any branch."""
    repo=Path(repo)
    subprocess.run(["git","fetch","--quiet","origin",DEV],
                   cwd=repo,check=True,timeout=90)
    rev=subprocess.run(["git","rev-parse","FETCH_HEAD"],
                       cwd=repo,capture_output=True,text=True,check=True,timeout=15).stdout.strip()
    archive=subprocess.run(["git","archive","--format=zip","FETCH_HEAD",
                            "public/data/v1"],
                           cwd=repo,capture_output=True,check=True,timeout=90).stdout
    if not 10_000 <= len(archive) <= 150_000_000:
        raise ValueError("Unexpected DEV static catalog size")
    root=Path(dest).resolve()
    with zipfile.ZipFile(io.BytesIO(archive)) as z:
        for record in z.infolist():
            if record.is_dir():
                continue
            name=record.filename
            if (not name.startswith("public/data/v1/")
                    or ".." in Path(name).parts
                    or Path(name).is_absolute()):
                raise ValueError("DEV archive contained unreviewed path")
            target=(root/name).resolve()
            if not target.is_relative_to(root):
                raise ValueError("DEV archive path escapes expected folder")
            target.parent.mkdir(parents=True,exist_ok=True)
            target.write_bytes(z.read(record))
    manifest=root/"public"/"data"/"v1"/"manifest.json"
    if not manifest.is_file():
        raise ValueError("DEV catalog export has no manifest")
    return manifest, rev


def finish(snapshot, *, repo, out):
    snapshot,out=Path(snapshot),Path(out)
    count,total=progress(snapshot)
    out.mkdir(parents=True,exist_ok=True)
    if total is None or count!=total:
        return {"complete":False,"pages_completed":count,"pages_total":total}
    retries = retry_failures(snapshot)
    with tempfile.TemporaryDirectory(prefix="happings-dev-catalog-") as tmp:
        manifest,dev_sha=current_dev_catalog(repo,tmp)
        result=analyze(manifest,snapshot,out)
        # The match audit independently ties parsed events to existing IDs.
        detail_audit=audit_detail_matches(manifest,snapshot,out)
        result["detail_matching_counts"]=detail_audit["counts"]
        result["dev_revision_analyzed"]=dev_sha
        result["retry_summary"] = {
            "new_requests":retries["new_requests"],
            "recovered_in_this_run":retries["recovered_in_this_run"],
            "source_pages_unresolved":retries["source_pages_unresolved"],
        }
        result["source_content_complete"] = retries["source_content_complete"]
        (out/"happings-source-reconciliation.json").write_text(
            json.dumps(result,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    print("HAPPINGS_FULL_RECONCILIATION_COMPLETED" if retries["source_content_complete"]
          else "HAPPINGS_RECONCILIATION_WITH_SOURCE_GAPS",json.dumps({
        "dev":dev_sha,"pages":count,"market_groups":result["unique_weekly_city_day_groups"],
        "outcomes":result["outcomes"],
        "record_mutations":result["existing_catalog_id_mutations"]},
        ensure_ascii=False),flush=True)
    return {"complete":True,"source_content_complete":retries["source_content_complete"],
            "source_pages_unresolved":retries["source_pages_unresolved"],
            "pages_completed":count,"pages_total":total,"dev_sha":dev_sha}


def watch(snapshot, *, repo, out, interval_seconds=120, max_hours=48):
    if not 30<=interval_seconds<=3600 or not 1<=max_hours<=168:
        raise ValueError("Invalid bounded Happings finisher schedule")
    started=time.monotonic()
    last_reported=None
    while time.monotonic()-started < max_hours*3600:
        count,total=progress(snapshot)
        if (count,total)!=last_reported:
            print("HAPPINGS_SCAN_PROGRESS",count,total,flush=True)
            last_reported=count,total
        if total is not None and count==total:
            return finish(snapshot,repo=repo,out=out)
        time.sleep(interval_seconds)
    raise TimeoutError("Happings bulk scraper did not complete in the bounded watcher window")


def main():
    p=argparse.ArgumentParser()
    local=Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir())/"mercati-italia"
    p.add_argument("--snapshot",type=Path,default=local/"happings-full-crawl")
    p.add_argument("--out",type=Path,default=local/"happings-reconciliation")
    p.add_argument("--repo",type=Path,default=Path(__file__).resolve().parents[1])
    p.add_argument("--interval-seconds",type=int,default=120)
    p.add_argument("--max-hours",type=int,default=48)
    args=p.parse_args()
    watch(args.snapshot,repo=args.repo,out=args.out,
          interval_seconds=args.interval_seconds,max_hours=args.max_hours)


if __name__=="__main__":
    main()
