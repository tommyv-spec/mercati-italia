"""Safely install a QA-approved Happings static bundle in a DEV checkout.

Preserve other publisher checkpoints beside public/data/v1; only replace the
content-addressed static index, 20 regional shards and the manifest.
This script never pushes, merges production or contacts GitHub.
"""
from __future__ import annotations
import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

from validate_static import validate


def _git(repo, *args):
    proc = subprocess.run(["git", *args], cwd=repo, capture_output=True,
                          text=True, encoding="utf-8", errors="replace",timeout=30)
    if proc.returncode:
        raise ValueError("Git "+args[0]+" failed: "+proc.stderr[:200])
    return proc.stdout.strip()


def stage(repo, bundle, *, report_path):
    repo,bundle,report_path=Path(repo).resolve(),Path(bundle).resolve(),Path(report_path)
    target=repo/"public/data/v1"
    old=json.loads((target/"manifest.json").read_text("utf-8"))
    new=json.loads((bundle/"manifest.json").read_text("utf-8"))
    report=json.loads(report_path.read_text("utf-8"))
    if (_git(repo,"status","--porcelain","--untracked-files=no")
            or _git(repo,"rev-parse","--abbrev-ref","HEAD") == "main"):
        raise ValueError("Only a clean, non-production checkout may be staged")
    if (old.get("layout")!="regional" or new.get("layout")!="regional"
            or old.get("total")!=new.get("total")
            or new.get("total")!=report.get("after_records")
            or report.get("baseline_records")!=old.get("total")
            or new.get("content_signature")!=report.get("manifest_content_signature")
            or report.get("qa_gate_approved") is not True
            or report.get("all_existing_market_ids_preserved") is not True
            or report.get("old_unrelated_market_fields_changed") != 0
            or report.get("no_fabricated_exact_clock_hours") is not True
            or report.get("no_opening_verifications_claimed") is not True):
        raise ValueError("Publisher field candidate does not match approved static proof")
    def norm(path):
        if not isinstance(path,str) or not path.startswith("data/v1/"):
            raise ValueError("Unknown publisher static asset path")
        return path.removeprefix("data/v1/")
    paths=[norm(new.get("index"))]
    for region in new.get("regions") or []:
        if not isinstance(region,dict):
            raise ValueError("Invalid region")
        paths.append(norm(region.get("path")))
    expected={"manifest.json",*paths}
    if (len(new.get("regions") or [])!=20 or len(paths)!=21 or len(expected)!=22
            or not re.fullmatch(r"index-[0-9a-f]{14}\.json",paths[0])
            or any(not re.fullmatch(r"regions/[a-z-]+-[0-9a-f]{14}\.json",p)
                   for p in paths[1:])):
        raise ValueError("Untrusted regional market file layout")
    files={p.relative_to(bundle).as_posix() for p in bundle.rglob("*.json")}
    if files!=expected:
        raise ValueError("Candidate bundle contains missing or unreviewed files")
    if old.get("content_signature")==new.get("content_signature"):
        return {"status":"already_current","files_changed":0,
                "market_records":new["total"]}
    # Validate the complete source-built static candidate BEFORE any local edit.
    audit=validate(bundle/"manifest.json")
    if audit["records"]!=new["total"]:
        raise ValueError("Candidate validator disagrees with the source manifest")
    for item in expected:
        src=bundle/item
        dest=target/item
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.is_file() or dest.read_bytes()!=src.read_bytes():
            shutil.copyfile(src,dest)
    # Never remove source checkpoints or editorial states in the same folder.
    # Only stale content-addressed market shards and compact indices are pruned.
    for prior in target.glob("index-*.json"):
        if prior.name not in expected:
            prior.unlink()
    for prior in (target/"regions").glob("*.json"):
        if "regions/"+prior.name not in expected:
            prior.unlink()
    if (target/"manifest.json").read_bytes()!=(bundle/"manifest.json").read_bytes():
        raise ValueError("Installed market manifest differs from original proof")
    confirmed=validate(target/"manifest.json")
    if confirmed["records"]!=new["total"]:
        raise ValueError("Installed catalog invalid")
    changed=_git(repo,"status","--porcelain","--untracked-files=no").splitlines()
    return {"status":"staged_and_validated","files_changed":len(changed),
            "market_records":new["total"],"quality_gate":"approved",
            "manifest_signature":new["content_signature"],
            "preserved_auxiliary_data":True}


def main():
    a=argparse.ArgumentParser()
    a.add_argument("--repo",type=Path,required=True)
    a.add_argument("--bundle",type=Path,required=True)
    a.add_argument("--report",type=Path,required=True)
    arg=a.parse_args()
    result=stage(arg.repo,arg.bundle,report_path=arg.report)
    print(json.dumps(result,sort_keys=True))


if __name__=="__main__":
    main()
