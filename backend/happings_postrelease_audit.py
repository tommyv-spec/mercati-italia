"""Independently verify the exact source-backed Happings weekly DEV commit.

Read-only and repeatable. Checks the actual committed static JSON before and
after a Happings admission, not merely the counters reported by its author.
The same original publisher HTML is replayed from the scheduled Autopilot
checkpoint. No GitHub API, new runner, write permissions or network crawl.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from datetime import date
from pathlib import Path

from export_static import normalize, parse_dates
from happings_weekly_admission import preview, verify_changes, MAX_NEW
from happings_weekly_dev_admission import pages_from_autopilot
from happings_bulk_snapshot import write_json

REF = re.compile(r"(?:[a-f0-9]{7,40}|HEAD(?:\^[0-9]?)?)\Z")
MAX_BLOB = 24_000_000


def git_blob(repo, rev, path):
    if (not REF.fullmatch(rev) or not isinstance(path,str)
            or not re.fullmatch(r"public/data/v1/[a-z0-9/.-]+\.json",path)
            or ".." in path or "//" in path):
        raise ValueError("Untrusted static Git revision or file path")
    result = subprocess.run(
        ["git", "show", rev + ":" + path], cwd=repo,
        capture_output=True, timeout=30)
    if result.returncode or len(result.stdout) > MAX_BLOB:
        raise ValueError("Missing or oversized committed static asset: " + path)
    return result.stdout


def committed_catalog(repo, revision):
    """Read source data from the specified immutable Git tree only."""
    repo = Path(repo)
    manifest = json.loads(git_blob(repo,revision,"public/data/v1/manifest.json"))
    if (manifest.get("schema")!=1 or manifest.get("layout")!="regional"
            or type(manifest.get("total")) is not int
            or not 1 <= manifest["total"] <= 100_000
            or not isinstance(manifest.get("regions"),list)
            or not 1 <= len(manifest["regions"]) <= 30):
        raise ValueError("Untrusted DEV regional catalog manifest")
    items = {}
    for region in manifest["regions"]:
        if not isinstance(region,dict) or not isinstance(region.get("path"),str):
            raise ValueError("Invalid source region reference")
        path="public/"+region["path"]
        raw=git_blob(repo,revision,path)
        match=re.search(r"-([a-f0-9]{14})\.json$",path)
        if not match or not hashlib.sha256(raw).hexdigest().startswith(match.group(1)):
            raise ValueError("Static catalog source asset hash mismatch")
        data=json.loads(raw)
        markets=data.get("markets")
        if (data.get("schema")!=1 or not isinstance(markets,list)
                or len(markets)!=region.get("count")):
            raise ValueError("Stored market region count or schema is invalid")
        for market in markets:
            key=market.get("slug") if isinstance(market,dict) else None
            if not isinstance(key,str) or not key or key in items:
                raise ValueError("Missing or duplicate committed market identity")
            items[key]=market
    if len(items)!=manifest["total"]:
        raise ValueError("Saved Happings catalog count differs from region assets")
    return manifest,items


def _same_committed_record_or_expired_dates(before, after, today):
    """Independent post-commit proof of the exporter's date-only expiry.

    This does not delegate to the publisher's admission validator: any
    identity, source field, address, hour, or future-calendar change fails.
    """
    if before == after:
        return True
    if not isinstance(before, dict) or not isinstance(after, dict):
        return False
    if ({k: v for k, v in before.items() if k != "date"} !=
            {k: v for k, v in after.items() if k != "date"}):
        return False
    return (isinstance(before.get("date"), list)
            and isinstance(after.get("date"), list)
            and after["date"] == parse_dates(before["date"], today))


def verify_cohort(before, after, admission, publisher_pages, *, today):
    """Independently prove new source records and bounded date-only rollover."""
    if (not isinstance(before,dict) or not isinstance(after,dict)
            or not isinstance(admission,dict) or not isinstance(publisher_pages,list)
            or type(today) is not date):
        raise ValueError("Invalid source commit comparison context")
    added=set(after)-set(before)
    removed=set(before)-set(after)
    changed={key for key in before if key in after and before[key]!=after[key]}
    ids=admission.get("added_ids")
    hashes=admission.get("source_page_hashes")
    if (admission.get("status")!="dev_published"
            or admission.get("dev_published") is not True
            or admission.get("qa_gate_approved") is not True
            or not isinstance(ids,list) or len(set(ids))!=len(ids)
            or not isinstance(hashes,list) or not hashes
            or removed or not added or len(added)>MAX_NEW
            or any(not _same_committed_record_or_expired_dates(
                before[sid],after[sid],today) for sid in changed)
            or admission.get("existing_market_records_changed") != len(changed)
            or admission.get("existing_market_dates_expired") != len(changed)
            or admission.get("existing_market_non_calendar_fields_changed") != 0
            or added!=set(ids)
            or len(before)!=admission.get("old_record_count")
            or len(after)!=admission.get("new_record_count")):
        raise ValueError("DEV publication changed or misreported an existing market identity")

    observed = {p["final_url"]: hashlib.sha256(p["html"]).hexdigest()
                for p in publisher_pages}
    declared = {h.get("url"):h.get("sha256") for h in hashes if isinstance(h,dict)}
    if (len(observed)!=len(publisher_pages)
            or len(declared)!=len(hashes)
            or observed!=declared):
        raise ValueError("Publisher source HTML differs from the published commit evidence")
    old_rows=list(before.values())
    reproduced,evidence=preview(old_rows,publisher_pages,today=today,apply=True,max_new=MAX_NEW)
    verify_changes(old_rows,reproduced,evidence,today=today,pages=publisher_pages)
    if set(evidence["added_ids"])!=added:
        raise ValueError("New DEV identities cannot be replayed from saved publisher HTML")
    for row in reproduced[len(old_rows):]:
        normalized,error=normalize(row,today)
        if error or normalized!=after.get(row["slug"]):
            raise ValueError("A newly committed market differs from its source-reproduced fields")
    for sid in added:
        record=after[sid]
        if (record.get("status")!="non_confermato" or record.get("verificato_il")
                or record.get("date") or record.get("orario_testo")
                or record.get("date_quality")!="sconosciuta"
                or record.get("lat") is not None or record.get("lng") is not None):
            raise ValueError("New weekly venue claims an unverified opening or invented date/coordinate")
    return {
        "schema":1,"publisher":"happings.com","release_safe":True,
        "source_html_pages_replayed":len(publisher_pages),
        "published_new_market_ids":len(added),
        "existing_market_ids_preserved":len(before),
        "existing_record_content_changes":len(changed),
        "existing_calendar_rollovers":len(changed),
        "existing_non_calendar_changes":0,
        "market_ids_deleted":0,
        "invented_opening_verifications":0,
        "invented_exact_hours":0,
        "invented_coordinates":0,
        "date":today.isoformat(),
        "added_ids":sorted(added),
    }


def run(*, repo, before_ref, after_ref, source_dir, admission_path, output, today=None):
    today=today or date.today()
    repo=Path(repo)
    admission=json.loads(Path(admission_path).read_text("utf-8"))
    if (not REF.fullmatch(before_ref) or not REF.fullmatch(after_ref)
            or admission.get("published_commit")!=subprocess.run(
                ["git","rev-parse",after_ref],cwd=repo,text=True,
                capture_output=True,check=True,timeout=20).stdout.strip()
            or admission.get("dev_baseline")!=subprocess.run(
                ["git","rev-parse",before_ref],cwd=repo,text=True,
                capture_output=True,check=True,timeout=20).stdout.strip()):
        raise ValueError("Saved publication report does not identify both committed Git revisions")
    old_manifest,old=committed_catalog(repo,before_ref)
    new_manifest,new=committed_catalog(repo,after_ref)
    pages,_=pages_from_autopilot(source_dir,today=today)
    result=verify_cohort(old,new,admission,pages,today=today)
    if new_manifest["content_signature"]!=admission.get("manifest_signature"):
        raise ValueError("Published manifest differs from the admitted source release")
    result.update(
        old_catalog_records=old_manifest["total"],
        new_catalog_records=new_manifest["total"],
        before_ref=admission["dev_baseline"],
        after_ref=admission["published_commit"],
        manifest_signature=new_manifest["content_signature"])
    write_json(output,result)
    return result


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--repo",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--before",required=True)
    parser.add_argument("--after",required=True)
    parser.add_argument("--source-dir",type=Path,required=True)
    parser.add_argument("--admission",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    args=parser.parse_args()
    print(json.dumps(run(repo=args.repo,before_ref=args.before,after_ref=args.after,
       source_dir=args.source_dir,admission_path=args.admission,output=args.out),
       ensure_ascii=False,sort_keys=True))


if __name__=="__main__":
    main()
