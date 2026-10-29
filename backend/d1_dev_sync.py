"""Safely mirror a GitHub-QA-published static DEV catalog to the existing D1.

No extra services, paid runners, or frontend runtime database queries.
A successful GitHub Autopilot run and its immutable source/quality evidence
must match the *current* published DEV manifest and existing D1 head.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

import d1_incremental as incremental
from d1_catalog import DB_NAME, dataset_meta, remote_query, sql

REPO = "tommyv-spec/mercati-italia"
BRANCH = "improve/data-quality-security-performance-2026-10-11"
REMOTE = "https://github.com/" + REPO + ".git"
SHA = re.compile(r"^[0-9a-f]{40}$")
SIGNATURE = re.compile(r"^[0-9a-f]{64}$")


def command(*arguments: str, cwd: Path | None = None) -> str:
    result = subprocess.run(
        list(arguments), cwd=cwd, text=True, encoding="utf-8",
        errors="replace", capture_output=True, timeout=60, check=False
    )
    if result.returncode:
        raise ValueError("Cannot verify immutable GitHub DEV publication")
    return result.stdout.strip()


def verified_git(repo: Path, expected_git_sha: str) -> None:
    if not SHA.fullmatch(expected_git_sha):
        raise ValueError("Expected exact immutable Git SHA")
    local = command("git", "rev-parse", "HEAD", cwd=repo)
    remote = command("git", "remote", "get-url", "origin", cwd=repo)
    published = command("git", "ls-remote", "--heads", REMOTE,
                        "refs/heads/" + BRANCH, cwd=repo)
    if (local != expected_git_sha or remote != REMOTE
            or not published.startswith(expected_git_sha + "\t")
            or command("git", "status", "--porcelain", "--untracked-files=no",
                       cwd=repo)):
        raise ValueError("DEV checkout or remote ref differs from the approved Git SHA")


def verified_gha(run_id: str) -> dict:
    if not re.fullmatch(r"[0-9]{8,15}", run_id):
        raise ValueError("Invalid GitHub Actions run ID")
    run = json.loads(command("gh", "api", "repos/" + REPO + "/actions/runs/" + run_id))
    if (run.get("conclusion") != "success" or run.get("status") != "completed"
            or run.get("head_branch") != "main"
            or run.get("event") not in {"schedule", "push", "workflow_dispatch"}
            or run.get("repository", {}).get("full_name") != REPO
            or not str(run.get("name") or "").startswith("Mercati Autopilot")):
        raise ValueError("The exact official Autopilot run did not complete successfully")
    jobs = json.loads(command(
        "gh", "api", "repos/" + REPO + "/actions/runs/" + run_id + "/jobs?per_page=100"
    )).get("jobs")
    if not isinstance(jobs, list):
        raise ValueError("GitHub release job evidence is missing")
    required = {
        "Source → merge → recurrence → export → quality gates",
        "Security, compiled static site, mobile browser checks",
        "Update DEV catalog + separately hosted static preview",
    }
    succeeded = {job.get("name") for job in jobs
                 if isinstance(job, dict) and job.get("conclusion") == "success"}
    if not required.issubset(succeeded):
        raise ValueError("Approved candidate did not complete the final DEV publication job")
    return run


def preflight(decision: dict, quality: dict, admission: dict | None, *,
              meta: dict, previous_signature: str) -> dict:
    """Construct the D1 import proof only after validating the two QA gates."""
    if (not SIGNATURE.fullmatch(str(previous_signature))
            or not isinstance(decision, dict) or not isinstance(quality, dict)):
        raise ValueError("Missing exact QA provenance")
    candidate = decision.get("candidate") or {}
    before = decision.get("old") or {}
    gates = decision.get("gates") or {}
    # Keep all conditions explicit, even with a weekly admission final delta.
    if (decision.get("approved") is not True
            or decision.get("base_signature") != previous_signature
            or not SIGNATURE.fullmatch(str(decision.get("new_signature") or ""))
            or not isinstance(gates, dict) or len(gates) < 12
            or any(value is not True for value in gates.values())
            or gates.get("source_identities_immutable") is not True
            or gates.get("no_unreviewed_new_confirmations") is not True
            or gates.get("no_unreviewed_new_verifications") is not True
            or any(decision.get(key) for key in (
                "removed_source_ids", "dropped_source_evidence",
                "new_unreviewed_confirmations", "new_unreviewed_verifications",
                "unverified_confirmation_claims", "unexpected_verification_claims"))
            or type(before.get("records")) is not int
            or type(candidate.get("records")) is not int
            or candidate["records"] < before["records"]
            or decision.get("validated", {}).get("records") != candidate["records"]):
        raise ValueError("Autopilot release proof does not meet its own source safety contract")
    q_metrics = quality.get("metrics") or {}
    if (quality.get("schema") != 1 or quality.get("review_only") is not True
            or quality.get("quality_release_safe") is not True
            or quality.get("quality_regressions")
            or quality.get("market_updates_applied") != 0
            or quality.get("market_confirmations_created") != 0
            or q_metrics.get("total") != candidate["records"]
            or q_metrics.get("future_date_quality_mismatch", 0) != 0):
        raise ValueError("National quality QA gate did not approve the source candidate")
    if admission is None:
        if (decision["new_signature"] != meta["signature"]
                or candidate["records"] != meta["rows"]):
            raise ValueError("GitHub published manifest differs from final Autopilot candidate")
    else:
        if (not isinstance(admission, dict)
                or admission.get("status") != "dev_published"
                or admission.get("qa_gate_approved") is not True
                or admission.get("dev_published") is not True
                or admission.get("published_commit") != meta["git_sha"]
                or admission.get("manifest_signature") != meta["signature"]
                or admission.get("old_record_count") != candidate["records"]
                or admission.get("new_record_count") != meta["rows"]
                or admission.get("existing_market_ids_deleted") != 0
                or admission.get("existing_market_non_calendar_fields_changed") != 0
                or admission.get("source_claims_opening_verified") != 0
                or not isinstance(admission.get("added_ids"), list)
                or not 1 <= len(admission["added_ids"]) <= 32
                or meta["rows"] != candidate["records"] + len(admission["added_ids"])):
            raise ValueError("Source-admission publication proof does not match DEV")
    return {
        "qa_gate_approved": True,
        "all_existing_market_ids_preserved": True,
        "manifest_content_signature": meta["signature"],
        "after_records": meta["rows"],
        "old_unrelated_market_fields_changed": 0,
        "github_workflow_run_id": str(decision["job_id"]),
        "github_release_certificate": "exact_DEV_release_and_national_QA",
        "address_fields_filled": 0,
        "qualitative_hour_fields_filled": 0,
    }


def d1_current_signature() -> str:
    heads = incremental.channel_heads()
    if heads["dev"] is None:
        raise ValueError("Existing remote DEV D1 snapshot is missing")
    rows = remote_query("SELECT content_signature,status FROM catalog_datasets "
                        "WHERE dataset_id=" + sql(heads["dev"]))
    if len(rows) != 1 or rows[0]["status"] != "ready":
        raise ValueError("Remote DEV dataset is missing or unready")
    return rows[0]["content_signature"]


def sync(repo: Path, *, decision_file: Path, quality_file: Path,
         admission_file: Path | None = None, dry_run=True) -> dict:
    repo = Path(repo).resolve()
    git_sha = command("git", "rev-parse", "HEAD", cwd=repo)
    verified_git(repo, git_sha)
    meta = dataset_meta(repo / "public/data/v1/manifest.json", git_sha)
    incremental.required_schema()
    decision = json.loads(Path(decision_file).read_text(encoding="utf-8"))
    quality = json.loads(Path(quality_file).read_text(encoding="utf-8"))
    if str(decision.get("job_id")) == "":
        raise ValueError("Missing exact GitHub run")
    verified_gha(str(decision.get("job_id")))
    admission = (json.loads(Path(admission_file).read_text(encoding="utf-8"))
                 if admission_file is not None else None)
    previous_signature = d1_current_signature()
    # A repeated invocation on the already imported DEV head is a clean no-op.
    if previous_signature == meta["signature"]:
        # Code/report commits can advance DEV without changing catalog bytes.
        # Validate against the ORIGINAL immutable source SHA recorded on D1,
        # not the latest Git commit. Every market hash must still match.
        saved = remote_query(
            "SELECT source_git_sha FROM catalog_datasets WHERE dataset_id=" +
            sql(meta["id"]) + " AND status='ready'")
        if (len(saved) != 1 or not SHA.fullmatch(str(saved[0]["source_git_sha"]))):
            raise ValueError("Active D1 version has no valid original Git source")
        incremental.validate(repo / "public/data/v1/manifest.json")
        incremental.verify_existing(repo / "public/data/v1/manifest.json",
                                    saved[0]["source_git_sha"])
        return {"status": "already_mirrored", "dataset_id": meta["id"],
                "records": meta["rows"],
                "unchanged_data_new_git_sha": saved[0]["source_git_sha"] != git_sha}
    proof = preflight(decision, quality, admission, meta=meta,
                      previous_signature=previous_signature)
    # Last gate independently checks all source hashes and catalog identities.
    incremental.validate(repo / "public/data/v1/manifest.json")
    with tempfile.TemporaryDirectory(prefix="mercati-approved-d1-") as tmp:
        path = Path(tmp) / "verified-github-release.json"
        path.write_text(json.dumps(proof, sort_keys=True), encoding="utf-8")
        return incremental.run(
            repo / "public/data/v1/manifest.json",
            git_sha, path, Path(tmp) / "d1-progress.json",
            dry_run=dry_run
        )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--decision", type=Path, required=True)
    parser.add_argument("--quality", type=Path, required=True)
    parser.add_argument("--admission", type=Path)
    parser.add_argument("--import-dev", action="store_true")
    args = parser.parse_args()
    print(json.dumps(sync(args.repo, decision_file=args.decision, quality_file=args.quality,
                          admission_file=args.admission, dry_run=not args.import_dev),
                     ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
