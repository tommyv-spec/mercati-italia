"""Build and independently audit a static DEV Happings field update.

Uses only verified local source facts. Nothing is published by this script.
"""
from __future__ import annotations

import argparse
import json
import shutil
from collections import Counter
from datetime import date
from pathlib import Path

from audit_dataset import audit
from autopilot import compare_candidates
from export_static import export, parse_dates
from happings_bulk_catalog_enrichment import enrich
from merge_catalog import load_existing
from validate_static import validate


def build(repo, snapshot, out, *, today):
    repo,snapshot,out=Path(repo),Path(snapshot),Path(out)
    manifest=repo/"public/data/v1/manifest.json"
    before=load_existing(manifest)
    after,report=enrich(before,snapshot,today=today)
    if not report["changes"] and not report["duplicate_markers"]:
        # Scheduled runs: an up-to-date catalog is success, not an error.
        print(json.dumps({"schema":1,"date":today.isoformat(),"no_changes":True}),flush=True)
        return {"schema":1,"date":today.isoformat(),"no_changes":True}
    policy=json.loads((repo/"backend/autopilot_policy.json").read_text("utf-8"))
    asset_dir=out/"public/data/v1"
    asset_dir.mkdir(parents=True,exist_ok=True)
    export(after,asset_dir,today=today,
           min_count=int(policy["gates"]["min_total_records"]),
           max_drop_ratio=float(policy["gates"]["max_record_loss_fraction"]),
           preserve_ids={r["slug"] for r in before})
    static_valid=validate(asset_dir/"manifest.json")
    normalized=load_existing(asset_dir/"manifest.json")
    old_by_id={r["slug"]:r for r in before}
    new_by_id={r["slug"]:r for r in normalized}
    if old_by_id.keys()!=new_by_id.keys():
        raise ValueError("Source enrichment introduced or removed market IDs")
    expected={p["id"]:p for p in report["changes"]}
    markers={p["id"]:p["duplicato_di"] for p in report["duplicate_markers"]}
    actual=Counter()
    rolled=0
    allowed={"indirizzo","orario_testo","ricorrenza_testo","riscontri_campi","fonti",
             "completezza","date","duplicato_di"}
    unexpected=[]
    for sid,old in old_by_id.items():
        new=new_by_id[sid]
        changed={k for k in set(old)|set(new) if old.get(k)!=new.get(k)}
        if changed-allowed:
            unexpected.append({"id":sid,"fields":sorted(changed-allowed)})
        if "date" in changed:
            if new.get("date")!=parse_dates(old.get("date"),today):
                raise ValueError("Exporter modified a non-expired calendar: "+sid)
            rolled+=1
        if ("duplicato_di" in changed) != (sid in markers) or new.get("duplicato_di","")!=markers.get(sid,old.get("duplicato_di","")):
            raise ValueError("Duplicate marker differs from the enrichment report: "+sid)
        entry=expected.get(sid)
        if entry:
            for field,value in entry["after"].items():
                # A cut weekday is the one nonempty value repaired here.
                if new.get(field)!=value or (field!="ricorrenza_testo" and str(old.get(field) or "").strip()):
                    raise ValueError("An enriched field was not preserved: "+sid+" "+field)
                actual["filled_"+field]+=1
            if "riscontri_campi" not in changed:
                raise ValueError("Source-backed update lacks an exported field proof: "+sid)
            proof=next((e for e in new.get("riscontri_campi") or []
                        if e.get("url")==entry["source"]
                        and e.get("sha256")==entry["source_html_sha256"]
                        and all(e.get("valori",{}).get(field)==value
                                for field,value in entry["after"].items())),None)
            if proof is None:
                raise ValueError("Export lost Happings HTML source evidence: "+sid)
        elif changed-{"date","duplicato_di"}:
            unexpected.append({"id":sid,"fields":sorted(changed)})
    if unexpected:
        raise ValueError("Unrelated catalog records changed: "+repr(unexpected[:8]))
    if actual["filled_indirizzo"]!=report["counts"].get("filled_indirizzo",0) or actual["filled_orario_testo"]!=report["counts"].get("filled_orario_testo",0):
        raise ValueError("Publisher field-count mismatch after export")
    old_audit=audit(manifest,today)
    new_audit=audit(asset_dir/"manifest.json",today)
    gate=compare_candidates(before,normalized,old_audit,new_audit,policy,
                            {"all_dates_marked_forecast":True},{})
    if gate["approved"] is not True:
        raise ValueError("Existing DEV release policy rejected source field update: "+json.dumps(gate["gates"],sort_keys=True))
    stats_before=Counter()
    stats_after=Counter()
    for row in before:
        if row.get("fonte")=="happings.com":
            stats_before["publisher_records"]+=1
            for field in ("indirizzo","orario_testo"):
                stats_before["nonempty_"+field]+=bool(str(row.get(field) or "").strip())
    for row in normalized:
        if row.get("fonte")=="happings.com":
            stats_after["publisher_records"]+=1
            for field in ("indirizzo","orario_testo"):
                stats_after["nonempty_"+field]+=bool(str(row.get(field) or "").strip())
    summary={
        "schema":1,"date":today.isoformat(),"baseline_records":len(before),
        "after_records":len(normalized),"baseline_publisher_fields":dict(stats_before),
        "after_publisher_fields":dict(stats_after),
        "address_fields_filled":actual["filled_indirizzo"],
        "qualitative_hour_fields_filled":actual["filled_orario_testo"],
        "cut_weekdays_repaired":actual["filled_ricorrenza_testo"],
        "duplicate_copies_marked":report["counts"]["duplicate_copies_marked"],
        "duplicate_marker_changes":len(markers),
        "existing_expired_calendar_rollovers":rolled,
        "source_pages_read_from_checksum_snapshot":report["snapshot_pages_checked"],
        "all_existing_market_ids_preserved":True,
        "old_unrelated_market_fields_changed":0,
        "no_fabricated_exact_clock_hours":True,
        "no_opening_verifications_claimed":True,
        "qa_gate_approved":True,
        "release_gate":gate["reason"],
        "manifest_content_signature":json.loads((asset_dir/"manifest.json").read_text("utf-8"))["content_signature"],
        "valid_static":static_valid,
    }
    out.mkdir(parents=True,exist_ok=True)
    (out/"happings-field-release-report.json").write_text(
        json.dumps(summary,ensure_ascii=False,indent=2,sort_keys=True)+"\n",encoding="utf-8")
    (out/"happings-field-changes.json").write_text(
        json.dumps(report,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(summary,ensure_ascii=False,sort_keys=True,default=str),flush=True)
    return summary


def install(repo, out):
    """Copy a built release into public/data/v1, keeping the version it replaces.

    Open tabs may still hold the previous manifest; anything older is removed.
    """
    target,built=Path(repo)/"public/data/v1",Path(out)/"public/data/v1"
    def assets(folder):
        manifest=json.loads((folder/"manifest.json").read_text("utf-8"))
        return {p.removeprefix("data/v1/") for p in
                [manifest["index"],*(r["path"] for r in manifest["regions"])]}
    keep=assets(target)|assets(built)
    for old in [*target.glob("index-*.json"),*target.glob("regions/*.json")]:
        if old.relative_to(target).as_posix() not in keep:
            old.unlink()
    for name in sorted(assets(built))+["manifest.json"]:
        shutil.copyfile(built/name,target/name)
    validate(target/"manifest.json")


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--repo",required=True,type=Path)
    parser.add_argument("--snapshot",required=True,type=Path)
    parser.add_argument("--out",required=True,type=Path)
    parser.add_argument("--today",default=date.today().isoformat(),type=date.fromisoformat)
    parser.add_argument("--install",action="store_true",
                        help="Copy an approved release into the repository's public/data/v1")
    args=parser.parse_args()
    summary=build(args.repo,args.snapshot,args.out,today=args.today)
    if args.install and not summary.get("no_changes"):
        install(args.repo,args.out)


if __name__=="__main__":
    main()
