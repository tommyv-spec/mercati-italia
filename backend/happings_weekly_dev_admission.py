"""Repeatable, fail-closed Happings weekly admission to DEV, never production.

Live publisher HTML, not an old worklist or invented metadata, is the
admission source. Existing market IDs and source fields remain immutable;
only the exporter's exact deterministic removal of expired dates is allowed.
A separate replay verifier and the existing static QA,
autopilot release gate and fast-forward-only Git update guard the transition.

This runs AFTER daily source discovery/reconciliation on the user's computer.
Its report, source pages and proof stay local; only clean static assets go DEV.
"""
from __future__ import annotations

import argparse
import gzip
import io
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime, timezone
from pathlib import Path

from audit_dataset import audit
from autopilot import compare_candidates, prune_old_assets
from export_static import export, parse_dates
from happings_bulk_snapshot import write_json
from happings_weekly_admission import MAX_NEW, preview, verify_changes
import happings_source_enrichment as source
from merge_catalog import load_existing
from validate_static import validate

BRANCH = "improve/data-quality-security-performance-2026-10-11"
MAX_SOURCE_PAGES = 16
MAX_WORKLIST_BYTES = 12_000_000
MAX_HTML_BYTES = 2_600_000
MAX_CATALOG_CHANGES = 80


def ensure_utf8():
    """Fail loudly on non-UTF-8 machines; no city names may be mojibake."""
    import locale
    preferred = locale.getpreferredencoding(False).replace("-", "").replace("_", "").lower()
    if preferred not in ("utf8", "utf8sig"):
        raise ValueError("Happings admission requires Python UTF-8 mode (-X utf8 or PYTHONUTF8=1)")


def git(repo, *args, timeout=90):
    p = subprocess.run(["git", *args], cwd=repo, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if p.returncode:
        raise ValueError("Git " + args[0] + " failed: " + p.stderr[:350])
    return p.stdout.strip()


def checked_checkout(repo, *, allow_dirty=False, allow_stale_remote=False):
    repo = Path(repo).resolve()
    if not (repo / ".happings-dedicated-checkout").is_file():
        raise ValueError("Weekly DEV admission requires the dedicated local checkout")
    if git(repo, "remote", "get-url", "origin") not in {
            "https://github.com/tommyv-spec/mercati-italia.git",
            "https://github.com/tommyv-spec/mercati-italia"}:
        raise ValueError("Weekly DEV publication destination changed")
    if git(repo, "rev-parse", "--abbrev-ref", "HEAD") != BRANCH:
        raise ValueError("Weekly admission cannot write a non-DEV branch")
    if not allow_dirty and git(repo, "status", "--porcelain", "--untracked-files=no"):
        raise ValueError("Weekly admission cannot overwrite local tracked changes")
    current = git(repo, "rev-parse", "HEAD")
    remote = git(repo, "ls-remote", "origin", "refs/heads/" + BRANCH).split()[0]
    # Read-only source/ISTAT previews are pinned to their local catalog
    # revision. If DEV moves during a long publisher crawl, no catalog is
    # written here, so the preview can still be independently checked.
    # Publication must ALWAYS reject a newer remote DEV baseline.
    if current != remote and not allow_stale_remote:
        raise ValueError("Weekly admission baseline no longer matches remote DEV")
    return current


def candidate_pages(worklist_path, qa_path, *, dev_sha, max_pages=MAX_SOURCE_PAGES):
    path, qa_path = Path(worklist_path), Path(qa_path)
    if type(max_pages) is not int or not 1 <= max_pages <= MAX_SOURCE_PAGES:
        raise ValueError("Unbounded Happings source batch")
    if not path.is_file() or not 2 <= path.stat().st_size <= MAX_WORKLIST_BYTES:
        raise ValueError("No current bounded Happings reconciliation worklist")
    if not qa_path.is_file() or qa_path.stat().st_size > 1_000_000:
        raise ValueError("No current Happings full-source QA report")
    summary = json.loads(qa_path.read_text("utf-8"))
    if (summary.get("dev_revision_analyzed") != dev_sha
            or summary.get("source_content_complete") is not True
            or summary.get("snapshot_pages_completed") != summary.get("snapshot_pages_total")
            or not isinstance(summary.get("observed_source_pages"), dict)):
        raise ValueError("Cannot use stale or incomplete Happings reconciliation")
    queue = json.loads(path.read_text("utf-8"))
    if not isinstance(queue, list) or len(queue) > 50_000:
        raise ValueError("Unbounded weekly identity queue")
    urls = set()
    for item in queue:
        if not isinstance(item, dict):
            raise ValueError("Malformed source proposal")
        if item.get("outcome") != "new_venue_possible_needs_source_html_admission":
            continue
        pages = item.get("urls")
        if not isinstance(pages, list) or not 1 <= len(pages) <= 5:
            raise ValueError("Unbounded candidate publisher URLs")
        for url in pages:
            if not source._valid_page_url(url):
                raise ValueError("Unreviewed Happings weekly source URL")
            urls.add(url)
    return sorted(urls)[:max_pages], len(urls)


def fetch_pages(urls, *, today, sleep=time.sleep, robots=None, fetcher=None):
    if not urls or len(urls) > MAX_SOURCE_PAGES:
        raise ValueError("Invalid Happings admission source frontier")
    rights = json.loads(source.RIGHTS_REVIEW_FILE.read_text("utf-8"))
    if not source.authorization_status(rights, today=today)["authorized"]:
        raise ValueError("Happings project scraping authorization no longer active")
    robots = robots or source.robots_allowed()
    fetcher = fetcher or source._fetch_one
    pause = source._request_pause(robots)
    pages = []
    for url in urls:
        if not source._valid_page_url(url) or not robots.can_fetch(source.USER_AGENT, url):
            raise ValueError("Publisher robots or URL scope denies admission page")
        sleep(pause)
        raw, final = fetcher(url, robots=robots)
        if (not source.allowed_url(url,url,final) or not isinstance(raw,bytes)
                or not 300 <= len(raw) <= MAX_HTML_BYTES):
            raise ValueError("Publisher response changed its reviewed weekly format")
        pages.append({"requested_url":url,"final_url":final,
                      "html":raw,"fetched_at":datetime.now(timezone.utc).isoformat()})
    return pages


def archive_source_html(pages, out):
    """Keep bounded publisher HTML locally for future parser regressions.

    Files are never put into the GitHub catalog. Deterministic gzip content
    and independent SHA-256 allow an offline HTML-to-market replay.
    """
    root=Path(out)/"happings-source-html"
    root.mkdir(parents=True,exist_ok=True)
    archived=[]
    for page in pages:
        raw=page["html"]
        url=page["final_url"]
        source_sha=hashlib.sha256(raw).hexdigest()
        name=hashlib.sha256(url.encode("utf-8")).hexdigest()+"-"+source_sha[:16]+".html.gz"
        file=root/name
        if file.exists():
            if file.stat().st_size>MAX_HTML_BYTES:
                raise ValueError("Publisher HTML archive exceeds bounded compressed size")
            try:
                with gzip.GzipFile(fileobj=io.BytesIO(file.read_bytes())) as opened:
                    decoded=opened.read(MAX_HTML_BYTES+1)
            except (OSError, EOFError, ValueError) as error:
                raise ValueError("Previous source HTML archive is corrupt") from error
            if decoded!=raw:
                raise ValueError("Previous source HTML archive fails its checksum")
        else:
            packed=gzip.compress(raw,mtime=0)
            part=file.with_name(name+".part")
            part.write_bytes(packed)
            part.replace(file)
        archived.append({"url":url,"sha256":source_sha,
                         "html_bytes":len(raw),"archive":name,
                         "fetched_at":page.get("fetched_at")})
    write_json(Path(out)/"happings-source-html-index.json",{
        "schema":1,"pages":archived,
        "raw_html_published_to_github":False
    })
    return archived


def pages_from_autopilot(source_dir, *, today):
    """Replay the existing Autopilot's publisher capture without refetching.

    Never trust a report-supplied arbitrary file path. Rebuild the exact raw
    bytes from the fixed candidate artifact path and verify the original
    checkpoint's URLs, SHA-256 and release-context digest.
    """
    import happings_autopilot as autopilot_happings

    folder=Path(source_dir)
    report_path=folder/"happings-enrichment.json"
    if not report_path.is_file() or report_path.stat().st_size>8_000_000:
        raise ValueError("Untrusted Autopilot Happings source report")
    report=json.loads(report_path.read_text("utf-8"))
    if (report.get("schema") != 1 or report.get("date") != today.isoformat()
            or report.get("enabled") is not True
            or report.get("fetch_authorized") is not True
            or not isinstance(report.get("selected_urls"),list)):
        raise ValueError("Weekly archive lacks active authorized source acquisition")
    urls=report["selected_urls"]
    if not urls:
        return [],report
    file=folder/"sources/happings-pages.json"
    if not file.is_file() or file.stat().st_size>autopilot_happings.MAX_CHECKPOINT_BYTES:
        raise ValueError("Happings HTML acquisition checkpoint missing or unbounded")
    saved=json.loads(file.read_text("utf-8"))
    context=saved.get("context") if isinstance(saved,dict) else None
    if (not isinstance(context,dict) or
            context.get("today") != report["date"]
            or context.get("selected_urls") != urls
            or context.get("input_sha256") != report["input_sha256"]
            or context.get("rights_sha256") != report["rights_record_sha256"]):
        raise ValueError("Happings weekly checkpoint did not match source report")
    pages=autopilot_happings._unpack_pages(saved,context)
    return pages,report


def _same_protected_market_or_date_rollover(before, after, *, today):
    """Allow only the exporter's deterministic removal of out-of-window dates.

    Existing source identity, addresses, times, provenance, and future dates
    remain immutable. This is *not* permission to alter a protected event.
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


def verify_catalog(before, after, evidence, *, today):
    """Independent normalized diff; only expected date expiry may change."""
    original = {row["slug"]:row for row in before}
    candidate = {row["slug"]:row for row in after}
    additions = set(candidate) - set(original)
    if (len(original) != len(before) or len(candidate) != len(after)
            or not set(original).issubset(candidate)
            or additions != set(evidence.get("added_ids") or [])
            or not additions or len(additions) > MAX_NEW
            or any(not _same_protected_market_or_date_rollover(
                row, candidate[sid], today=today) for sid,row in original.items())):
        raise ValueError("Weekly candidate changed protected identity or source fields")
    for sid in additions:
        row=candidate[sid]
        if (row.get("status") != "non_confermato" or row.get("verificato_il")
                or row.get("date") or row.get("date_quality") != "sconosciuta"
                or row.get("lat") is not None or row.get("lng") is not None
                or row.get("orario_testo") or row.get("fonte") != source.PUBLISHER
                or not row.get("riscontri_campi")):
            raise ValueError("Weekly source claimed unverified opening, date or coordinates")
    return sorted(additions)


def stage_candidate(repo, base, pages, *, today, max_new, tmp_root):
    old_manifest = Path(repo) / "public/data/v1/manifest.json"
    old_rows = base
    expanded, evidence = preview(old_rows,pages,today=today,apply=True,max_new=max_new)
    verify_changes(old_rows,expanded,evidence,today=today,pages=pages)
    ids = verify_catalog(old_rows,expanded,evidence,today=today) if evidence["added_ids"] else []
    if not ids:
        return None, {"added_ids":[],"source_pages":len(pages),
                      "candidates_found":len(evidence.get("candidates") or []),
                      "deferred":0,"status":"no_new_admissible_markets"}
    output = Path(tmp_root)/"public/data/v1"
    shutil.copytree(old_manifest.parent,output)
    old_snapshot=json.loads(old_manifest.read_text("utf-8"))
    policy=json.loads((Path(repo)/"backend/autopilot_policy.json").read_text("utf-8"))
    export(expanded,output,today=today,
           min_count=int(policy["gates"]["min_total_records"]),
           max_drop_ratio=float(policy["gates"]["max_record_loss_fraction"]),
           preserve_ids=set(r["slug"] for r in old_rows))
    validated=validate(output/"manifest.json")
    normalized=load_existing(output/"manifest.json")
    proven=verify_catalog(old_rows,normalized,evidence,today=today)
    if proven!=ids or validated["records"] != len(normalized):
        raise ValueError("Source-proved venue identities were changed by static exporter")
    old_audit=audit(old_manifest,today)
    new_audit=audit(output/"manifest.json",today)
    release=compare_candidates(old_rows,normalized,old_audit,new_audit,policy,
                               {"all_dates_marked_forecast":True},{})
    if release["approved"] is not True:
        raise ValueError("Existing DEV quality gate rejected weekly admissions: "+
                         json.dumps(release["gates"],sort_keys=True))
    fresh=json.loads((output/"manifest.json").read_text("utf-8"))
    prune_old_assets(output,old_snapshot,fresh)
    old_by_id = {row["slug"]: row for row in old_rows}
    natural_date_rollovers = sum(
        old_by_id[row["slug"]].get("date") != row.get("date")
        for row in normalized if row["slug"] in old_by_id)
    return output, {
        "status":"qa_approved", "added_ids":ids,
        "source_pages":len(pages),
        "candidates_found":len(evidence["candidates"]),
        "deferred":evidence["counts"]["new_venues_deferred_capacity"],
        "old_record_count":len(old_rows),
        "new_record_count":len(normalized),
        "manifest_signature":fresh["content_signature"],
        "source_page_hashes":[{
            "url":p["final_url"],"sha256":hashlib.sha256(p["html"]).hexdigest(),
            "size":len(p["html"])} for p in pages],
        "existing_market_records_changed":natural_date_rollovers,
        "existing_market_dates_expired":natural_date_rollovers,
        "existing_market_non_calendar_fields_changed":0,
        "existing_market_ids_deleted":0,
        "source_claims_opening_verified":0,
        "qa_gate_approved":True
    }


def copy_into_checkout(candidate_dir, repo):
    """Write assets before manifest; stage only the reviewed static directory."""
    target=Path(repo)/"public/data/v1"
    expected={x.relative_to(candidate_dir) for x in candidate_dir.rglob("*") if x.is_file()}
    for path in candidate_dir.rglob("*"):
        if not path.is_file() or path.name == "manifest.json":
            continue
        dest=target/path.relative_to(candidate_dir)
        dest.parent.mkdir(parents=True,exist_ok=True)
        if not dest.is_file() or dest.read_bytes()!=path.read_bytes():
            shutil.copyfile(path,dest)
    for old in target.rglob("*.json"):
        if old.name == "manifest.json":
            continue
        if old.relative_to(target) not in expected:
            old.unlink()
    manifest=target/"manifest.json"
    replacement=manifest.with_suffix(".json.part")
    replacement.write_bytes((candidate_dir/"manifest.json").read_bytes())
    replacement.replace(manifest)


def publish_to_dev(repo, candidate_dir, *, expected_sha, report, out):
    if checked_checkout(repo) != expected_sha:
        raise ValueError("DEV moved between validation and publication")
    copy_into_checkout(candidate_dir,repo)
    git(repo,"add","-A","--","public/data/v1")
    paths=[p for p in git(repo,"diff","--cached","--name-only").splitlines() if p]
    if (not paths or len(paths)>MAX_CATALOG_CHANGES
            or any(not p.startswith("public/data/v1/") for p in paths)):
        raise ValueError("Weekly admission staged unexpected paths")
    git(repo,"commit","-m",
        "DEV: admit source-proved Happings weekly venues ("+str(len(report["added_ids"]))+")")
    result=git(repo,"rev-parse","HEAD")
    try:
        git(repo,"push","origin","HEAD:refs/heads/"+BRANCH,timeout=120)
    except ValueError:
        # Never force-push or rebase this automated admission transaction.
        raise ValueError("DEV changed or write denied; commit left only in dedicated local checkout")
    report["published_commit"]=result
    report["status"]="dev_published"
    write_json(Path(out)/"happings-weekly-admission.json",report)
    return result


def run(repo, out, *, today=None, max_pages=MAX_SOURCE_PAGES,
        max_new=MAX_NEW, publish=False, fetcher=None, robots=None, sleep=time.sleep):
    ensure_utf8()
    repo,out=Path(repo).resolve(),Path(out)
    today=today or date.today()
    if type(publish) is not bool or type(max_new) is not int or not 1<=max_new<=MAX_NEW:
        raise ValueError("Invalid bounded DEV-only admission mode")
    baseline=checked_checkout(repo,allow_dirty=not publish,allow_stale_remote=not publish)
    queue=out/"happings-source-worklist.json"
    qa=out/"happings-source-reconciliation.json"
    urls,pages_total=candidate_pages(queue,qa,dev_sha=baseline,max_pages=max_pages)
    if not urls:
        result={"schema":1,"status":"no_new_candidates","dev_baseline":baseline,
                "candidate_source_pages":0,"added_ids":[],"dev_published":False}
        write_json(out/"happings-weekly-admission.json",result)
        return result
    html_pages=fetch_pages(urls,today=today,fetcher=fetcher,robots=robots,sleep=sleep)
    html_archive=archive_source_html(html_pages,out)
    with tempfile.TemporaryDirectory(prefix="happings-weekly-dev-") as workspace:
        source_rows=load_existing(repo/"public/data/v1/manifest.json")
        staged,report=stage_candidate(repo,source_rows,html_pages,
                                      today=today,max_new=max_new,tmp_root=workspace)
        report.update(schema=1,dev_baseline=baseline,
                      html_archived_locally=len(html_archive),
                      source_pages_eligible=pages_total,
                      publication_requested=publish,
                      dev_published=False,
                      evaluated_on=today.isoformat())
        write_json(out/"happings-weekly-admission.json",report)
        if staged is not None and publish:
            publish_to_dev(repo,staged,expected_sha=baseline,report=report,out=out)
            report["dev_published"]=True
            write_json(out/"happings-weekly-admission.json",report)
    return report


def run_from_autopilot(repo, source_dir, out, *, today=None,
                       max_pages=MAX_SOURCE_PAGES, max_new=MAX_NEW,
                       publish=False):
    """Additional protected DEV phase of the already-existing scheduled job."""
    ensure_utf8()
    repo,out=Path(repo).resolve(),Path(out)
    today=today or date.today()
    if type(publish) is not bool or type(max_new) is not int or not 1<=max_new<=MAX_NEW:
        raise ValueError("Invalid DEV publication settings")
    if type(max_pages) is not int or not 1<=max_pages<=MAX_SOURCE_PAGES:
        raise ValueError("Unbounded same-run Happings source selection")
    baseline=checked_checkout(repo,allow_dirty=not publish,allow_stale_remote=not publish)
    raw,origin=pages_from_autopilot(source_dir,today=today)
    source_pages=raw[:max_pages]
    if not source_pages:
        report={"schema":1,"status":"no_eligible_source_pages",
                "added_ids":[],"dev_baseline":baseline,
                "source_pages_evaluated":0,"dev_published":False}
        write_json(out/"happings-weekly-admission.json",report)
        return report
    observed=archive_source_html(source_pages,out)
    with tempfile.TemporaryDirectory(prefix="happings-weekly-dev-") as workspace:
        base=load_existing(repo/"public/data/v1/manifest.json")
        staged,report=stage_candidate(repo,base,source_pages,today=today,
                                      max_new=max_new,tmp_root=workspace)
        report.update(schema=1,dev_baseline=baseline,
                      source_pages_eligible=len(raw),
                      html_archived_locally=len(observed),
                      publication_requested=publish,dev_published=False,
                      source_mode="reused_autopilot_checkpoint",
                      source_context_sha256=hashlib.sha256(
                          (Path(source_dir)/"sources/happings-pages.json").read_bytes()).hexdigest(),
                      evaluated_on=today.isoformat())
        write_json(out/"happings-weekly-admission.json",report)
        if staged is not None and publish:
            publish_to_dev(repo,staged,expected_sha=baseline,report=report,out=out)
            report["dev_published"]=True
            write_json(out/"happings-weekly-admission.json",report)
    return report


def main():
    parser=argparse.ArgumentParser()
    base=Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir())/"mercati-italia"
    parser.add_argument("--repo",type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out",type=Path,default=base/"happings-reconciliation")
    parser.add_argument("--max-pages",type=int,default=MAX_SOURCE_PAGES)
    parser.add_argument("--max-new",type=int,default=MAX_NEW)
    parser.add_argument("--publish-dev",action="store_true")
    parser.add_argument("--from-autopilot-output",type=Path)
    args=parser.parse_args()
    try:
        if args.from_autopilot_output:
            result=run_from_autopilot(
                args.repo,args.from_autopilot_output,args.out,
                max_pages=args.max_pages,max_new=args.max_new,
                publish=args.publish_dev)
        else:
            result=run(args.repo,args.out,max_pages=args.max_pages,max_new=args.max_new,
                       publish=args.publish_dev)
    except Exception as error:
        write_json(Path(args.out)/"happings-weekly-admission.json",{
            "schema":1, "status":"failed", "error_type":type(error).__name__,
            "error":str(error)[:450],
            "failed_at":datetime.now(timezone.utc).isoformat(),
            "publication_requested":bool(args.publish_dev),
            "production_modified":False
        })
        raise
    print(json.dumps(result,ensure_ascii=False,sort_keys=True),flush=True)


if __name__=="__main__":
    main()
