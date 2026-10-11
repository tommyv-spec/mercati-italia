#!/usr/bin/env python3
"""Mercati d'Italia Autopilot — repeatable, auditable, fail-closed DEV pipeline.

A scheduled runner invokes THIS script, not a chain of copied inline commands.
Sources are fetched once per run (official importers only); source content
is untrusted evidence. No LLM inference, bulk geocoding or runtime DB writes.

Phase checkpoints: baseline, sources, merge, forecast, export, quality.
After each phase an atomic JSON checkpoint is saved. Reruns can resume with
--resume from downloaded GitHub Actions artifacts, provided baseline and policy
fingerprints match. Only an APPROVED candidate may be copied to the DEV branch.
The caller is responsible for CI/security/browser tests before promotion.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import date, datetime, timezone
from pathlib import Path

from audit_dataset import audit
from export_static import export
from merge_catalog import combine, load_existing
from recurrence_refresh import refresh_records
import source_milano
import source_firenze
import source_lombardia

SCHEMA = 1
PHASES = ("baseline", "sources", "merge", "forecast", "export", "quality")
SOURCE_FUNCTIONS = {
    "milano": (source_milano.download, source_milano.convert),
    "firenze": (source_firenze.download, source_firenze.convert),
    # Integration is registered, but not enabled by daily policy until its
    # full dry-run source/quality/mobile audit succeeds.
    "lombardia": (source_lombardia.download, source_lombardia.convert),
}


def digest(value) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def save_json(path: Path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    tmp.replace(path)


def read_json(path: Path):
    return json.loads(path.read_text("utf-8"))


def checkpoint(out: Path, phase: str, data):
    if phase not in PHASES:
        raise ValueError("Unknown checkpoint phase")
    item = {
        "phase": phase, "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "result": data,
    }
    save_json(out / "checkpoints" / (phase + ".json"), item)
    print("AUTOPILOT_CHECKPOINT", phase,
          json.dumps(data, ensure_ascii=False, sort_keys=True)[:2400], flush=True)


def source_feed(source_id: str, today: date):
    if source_id not in SOURCE_FUNCTIONS:
        raise ValueError("Source not on allowlist: " + source_id)
    download, convert = SOURCE_FUNCTIONS[source_id]
    raw = download()
    try:
        clean = convert(raw, today=today)
    except TypeError:
        clean = convert(raw)
    return clean


def retrieve_sources(policy: dict, out: Path, today: date, offline: bool, resume: bool) -> tuple[list, dict]:
    records = []
    status = {}
    for source in policy["sources"]:
        if not source.get("enabled", False):
            continue
        sid = source["id"]
        if sid not in SOURCE_FUNCTIONS or not source.get("official"):
            raise ValueError("Unapproved source configured: " + sid)
        cache = out / "sources" / (sid + ".json")
        mode = "offline_skipped"
        if resume and cache.is_file():
            fetched = read_json(cache)
            mode = "resumed_checkpoint"
        elif offline:
            fetched = []
        else:
            fetched = None
            errors = []
            for attempt in range(2):
                try:
                    fetched = source_feed(sid, today)
                    mode = "retrieved"
                    break
                except Exception as exc:
                    errors.append(type(exc).__name__ + ": " + str(exc)[:180])
                    if attempt == 0:
                        time.sleep(2)
            if fetched is None:
                mode = "unavailable"
                fetched = []
                status[sid] = {"status": mode, "error": errors[-1]}
        if mode not in ("offline_skipped", "unavailable"):
            low, high = int(source["min_records"]), int(source["max_records"])
            if not isinstance(fetched, list) or not low <= len(fetched) <= high:
                raise ValueError(
                    f"Official source {sid} returned {len(fetched) if isinstance(fetched,list) else 'invalid'} "
                    f"records, expected {low}..{high}; quarantine instead of import"
                )
            for rec in fetched:
                if not isinstance(rec, dict) or not rec.get("slug"):
                    raise ValueError(f"Source {sid} produced a record without a stable ID")
            save_json(cache, fetched)
        records.extend(fetched)
        status[sid] = {
            **status.get(sid, {}), "status": mode, "records": len(fetched),
            "official": True, "license_claim": source["license"],
        }
    return records, status



def quarantine_absent_official_lombardia(merged, base, fresh, source_status):
    """If an enabled source succeeds, remove unsupported forecasts for missing IDs.

    No market identities are deleted. One isolated removal is quarantined;
    a large shrink blocks the run rather than implying municipal closures.
    """
    if source_status.get("lombardia", {}).get("status") != "retrieved":
        return merged, {"lombardia_absent": 0, "lombardia_quarantined": 0}
    old = {x["slug"]: x for x in base
           if str(x.get("slug", "")).startswith("lo-mercap-")}
    new_ids = {x["slug"] for x in fresh
               if str(x.get("slug", "")).startswith("lo-mercap-")}
    missing = set(old) - new_ids
    allowed = max(3, int(len(old) * 0.02)) if old else 0
    if len(missing) > allowed:
        raise ValueError(
            f"Lombardia official source removed {len(missing)}/{len(old)} "
            "previously imported rows: refuse mass calendar invalidation"
        )
    changed = 0
    output = []
    for row in merged:
        if row["slug"] not in missing or row.get("verificato_il"):
            output.append(row)
            continue
        updated = row.copy()
        if row.get("date_quality") == "prevista":
            updated["date"] = []
            updated["date_quality"] = "sconosciuta"
            updated["proiezione_regola"] = None
            updated["proiezione_fonte"] = ""
            updated["proiezione_generata_il"] = ""
            updated["ricorrenza_testo"] = (
                "Non presente nell'ultimo dataset regionale; date da verificare"
            )
            changed += 1
        message = "Non rilevato nell'ultima estrazione ufficiale regionale."
        if message not in str(updated.get("descrizione") or ""):
            updated["descrizione"] = (str(updated.get("descrizione") or "") +
                                     " " + message).strip()
        output.append(updated)
    return output, {
        "lombardia_absent": len(missing),
        "lombardia_quarantined": changed,
    }


def compact_quality(report: dict):
    return {
        "records": report["snapshot_total"],
        "future_60": int(report["compact_index_future_coverage"]["60"]),
        "future_90": int(report["compact_index_future_coverage"]["90"]),
        "indexed_gzip_bytes": report["sizes"]["national_index_gzip_bytes"],
        "unknown_dates": report["fields_missing"].get("future_dates", 0),
        "missing_hours": report["fields_missing"].get("hours", 0),
        "verified": report["documented_verified_records"],
        "precise": report["position_quality"].get("precisa", 0),
    }


def compare_candidates(old_rows: list, new_rows: list, old_report: dict, new_report: dict,
                       policy: dict, forecast_stats: dict, sources_status: dict) -> dict:
    gate = policy["gates"]
    fgate = policy["forecast"]
    old_by_id = {item["slug"]: item for item in old_rows}
    new_by_id = {item["slug"]: item for item in new_rows}
    if len(old_by_id) != len(old_rows) or len(new_by_id) != len(new_rows):
        raise ValueError("Duplicate market ID found during policy evaluation")
    old_ids, new_ids = set(old_by_id), set(new_by_id)
    retained, removed, added = old_ids & new_ids, old_ids - new_ids, new_ids - old_ids
    loss_ratio = len(removed) / max(1, len(old_ids))
    retention_ratio = len(retained) / max(1, len(old_ids))
    old_index = old_report["sizes"]["national_index_gzip_bytes"]
    new_index = new_report["sizes"]["national_index_gzip_bytes"]
    baseline_gzip = max(1, old_index)
    dates_marked_confirmed = []
    verified_fabricated = []
    source_lost = []
    identity_changed = []
    # A new official feed cannot silently create a human verification or turn
    # a projected date into a confirmed calendar occurrence.
    new_confirmed = sorted(sid for sid in added
                           if new_by_id[sid].get("date_quality") == "confermata")
    new_verified = sorted(sid for sid in added
                          if new_by_id[sid].get("verificato_il"))

    def place_identity(record):
        return tuple(" ".join(str(record.get(field) or "").casefold().split())
                     for field in ("regione", "citta"))

    for sid in retained:
        before, after = old_by_id[sid], new_by_id[sid]
        if place_identity(before) != place_identity(after):
            identity_changed.append(sid)
        if before.get("date_quality") != "confermata" and after.get("date_quality") == "confermata":
            dates_marked_confirmed.append(sid)
        if not before.get("verificato_il") and after.get("verificato_il"):
            verified_fabricated.append(sid)
        prev_url = before.get("url_fonte")
        if prev_url and prev_url != after.get("url_fonte"):
            evidence = {str(source.get("url", "")) for source in after.get("fonti", [])
                        if isinstance(source, dict)}
            if prev_url not in evidence:
                source_lost.append(sid)
    old_unknown_share = old_report["fields_missing"].get("source_url", 0) / max(1, len(old_rows))
    new_unknown_share = new_report["fields_missing"].get("source_url", 0) / max(1, len(new_rows))
    source_health = all(
        entry.get("status") in ("retrieved", "resumed_checkpoint", "offline_skipped")
        for entry in sources_status.values()
    )
    checks = {
        "min_records": len(new_rows) >= int(gate["min_total_records"]),
        "max_source_loss": loss_ratio <= float(gate["max_record_loss_fraction"]),
        "min_id_retention": retention_ratio >= float(gate["min_id_retention_fraction"]),
        "max_new_records": len(added) <= int(gate["max_new_ids_per_run"]),
        "no_unreviewed_new_confirmations": not new_confirmed,
        "no_unreviewed_new_verifications": not new_verified,
        "unknown_source_share_budget": (
            new_unknown_share - old_unknown_share <=
            float(gate["max_unknown_source_share_increase"]) + 1e-12
        ),
        "official_sources_available": source_health,
        "forecast_60d": new_report["compact_index_future_coverage"]["60"] >=
            int(fgate["min_records_with_future_date_at_plus_60_days"]),
        "index_under_absolute_budget": new_index <= int(gate["max_gzip_index_bytes"]),
        "index_growth_budget": (new_index / baseline_gzip - 1) <=
            float(gate["max_index_growth_fraction"]),
        "never_upgrade_estimates_to_confirmed": not dates_marked_confirmed,
        "no_invented_human_verification": not verified_fabricated,
        "retain_old_source_evidence": not source_lost,
        "forecast_quality_flags": bool(forecast_stats.get("all_dates_marked_forecast", False)),
        "source_identities_immutable": not identity_changed,
    }
    ok = all(checks.values())
    return {
        "approved": ok,
        "reason": "all_policies_pass" if ok else "release_gate_rejected",
        "old": compact_quality(old_report),
        "candidate": compact_quality(new_report),
        "retained_source_ids": len(retained),
        "added_source_ids": len(added),
        "removed_source_ids": len(removed),
        "added_id_sample": sorted(added)[:20],
        "removed_id_sample": sorted(removed)[:20],
        "unverified_confirmation_claims": dates_marked_confirmed[:15],
        "unexpected_verification_claims": verified_fabricated[:15],
        "dropped_source_evidence": source_lost[:15],
        "new_unreviewed_confirmations": new_confirmed[:15],
        "new_unreviewed_verifications": new_verified[:15],
        "changed_market_identities": sorted(identity_changed)[:15],
        "unknown_source_share_before": round(old_unknown_share, 6),
        "unknown_source_share_after": round(new_unknown_share, 6),
        "sources": sources_status,
        "forecasts": forecast_stats,
        "gates": checks,
    }


def prune_old_assets(output: Path, old_manifest: dict, new_manifest: dict):
    """Keep the current and prior generation for immutable-client safety.

    Old clients can continue using their hashed manifest references while the
    new browser session loads the updated index. Prune only older generations
    outside those two; never remove any new/old manifest referenced file.
    """
    def assets(manifest):
        paths = {manifest.get("index"), manifest.get("catalog")}
        paths.update(part.get("path") for part in manifest.get("regions", []))
        return {s for s in paths if s}
    keep = assets(old_manifest) | assets(new_manifest)
    root = output.parent.parent
    removed = 0
    for file in output.rglob("*.json"):
        if file.name == "manifest.json":
            continue
        relative = file.relative_to(root).as_posix()
        if relative not in keep:
            file.unlink()
            removed += 1
    return removed


def run(args):
    start = time.monotonic()
    manifest_path = args.manifest.resolve()
    policy = read_json(args.policy)
    if policy.get("schema") != SCHEMA or policy.get("publication", {}).get("channel") != "dev-only":
        raise ValueError("Policy schema mismatch or production publication forbidden")
    if policy["publication"].get("production_merge", False):
        raise ValueError("Autopilot cannot publish production")
    if not policy["publication"].get("require_security_audit") or not policy["publication"].get("require_mobile_smoke"):
        raise ValueError("Production-grade QA gates cannot be disabled")
    if policy["gates"].get("allow_new_confident_date_claims") is not False or (
        policy["gates"].get("allow_new_human_verified_claims") is not False
    ):
        raise ValueError("Autopilot must never create unreviewed confirmation or human-verification claims")
    unknown_budget = float(policy["gates"]["max_unknown_source_share_increase"])
    if not 0 <= unknown_budget <= 0.05:
        raise ValueError("Unknown-source regression budget must be between 0 and 5%")

    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    checkpoint_dir = out / "checkpoints"
    status = {
        "schema": SCHEMA, "job_id": os.getenv("GITHUB_RUN_ID") or "local",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "dev_only": True, "base_ref": os.getenv("GITHUB_REF_NAME", ""),
        "candidate_approved": False,
        "reason": "not_yet_evaluated",
    }
    save_json(out / "status.json", status)
    old_manifest = read_json(manifest_path)
    policy_id = digest(policy)
    baseline_id = old_manifest.get("content_signature")
    if not baseline_id:
        raise ValueError("Baseline must have a content signature")
    previous = checkpoint_dir / "baseline.json"
    if args.resume and previous.exists():
        prior = read_json(previous)["result"]
        if (prior.get("baseline_signature") != baseline_id
                or prior.get("policy_digest") != policy_id
                or prior.get("today") != args.today.isoformat()):
            raise ValueError("Cannot resume: baseline, policy or reference date changed; start a new run")

    old_report = audit(manifest_path, args.today)
    old_rows = load_existing(manifest_path)
    checkpoint(out, "baseline", {
        "baseline_signature": baseline_id, "policy_digest": policy_id,
        "today": args.today.isoformat(), **compact_quality(old_report),
    })

    feeds, source_status = retrieve_sources(policy, out, args.today, args.offline, args.resume)
    checkpoint(out, "sources", {
        "total_fetched": len(feeds), "sources": source_status,
    })
    merged, merge_stats = combine(old_rows, feeds)
    merged, absent_stats = quarantine_absent_official_lombardia(
        merged, old_rows, feeds, source_status
    )
    merge_stats.update(absent_stats)
    if not merged or len(merged) < int(policy["gates"]["min_total_records"]):
        raise ValueError("Merge produced implausible record count")
    save_json(out / "intermediate" / "merged.json", merged)
    checkpoint(out, "merge", merge_stats)
    projected, forecast_stats = refresh_records(
        merged, args.today, policy["forecast"]["days"],
        policy["forecast"]["max_source_age_days"])
    if len(projected) != len(merged):
        raise ValueError("Forecast must never remove market identities")
    save_json(out / "intermediate" / "forecasted.json", projected)
    checkpoint(out, "forecast", forecast_stats)

    # Work on a temp copy. Rejected candidates never touch public/data/v1.
    dest = out / "candidate" / "public" / "data" / "v1"
    if dest.exists():
        shutil.rmtree(dest)
    shutil.copytree(manifest_path.parent, dest)
    exported = export(projected, dest, today=args.today,
                      min_count=int(policy["gates"]["min_total_records"]),
                      max_drop_ratio=float(policy["gates"]["max_record_loss_fraction"]))
    result_manifest = read_json(dest / "manifest.json")
    checkpoint(out, "export", {
        "records": result_manifest["total"],
        "index": result_manifest["index"],
        "index_schema": result_manifest["index_schema"],
        "unchanged": bool(exported["unchanged"]),
        "content_signature": result_manifest["content_signature"],
    })

    from validate_static import validate
    validated = validate(dest / "manifest.json")
    new_report = audit(dest / "manifest.json", args.today)
    new_rows = load_existing(dest / "manifest.json")
    findings = compare_candidates(old_rows, new_rows, old_report, new_report, policy,
                                  forecast_stats, source_status)
    findings["validated"] = validated
    findings["base_signature"] = baseline_id
    findings["new_signature"] = result_manifest["content_signature"]
    findings["elapsed_seconds"] = round(time.monotonic() - start, 2)
    findings["has_changes"] = baseline_id != result_manifest["content_signature"]
    findings["job_id"] = status["job_id"]
    findings["today"] = args.today.isoformat()
    findings["published"] = False
    if findings["approved"]:
        findings["pruned_obsolete_assets"] = prune_old_assets(dest, old_manifest, result_manifest)
    checkpoint(out, "quality", {
        "approved": findings["approved"],
        "reason": findings["reason"],
        "checks": findings["gates"],
        "records": result_manifest["total"],
        "index_gzip_bytes": findings["candidate"]["indexed_gzip_bytes"],
        "future_60": findings["candidate"]["future_60"],
    })
    save_json(out / "release-decision.json", findings)
    status.update({
        "completed_at": datetime.now(timezone.utc).isoformat(),
        "candidate_approved": findings["approved"],
        "candidate_changed": findings["has_changes"],
        "reason": findings["reason"],
        "baseline_signature": baseline_id,
        "candidate_signature": findings["new_signature"],
    })
    save_json(out / "status.json", status)

    print("AUTOPILOT_RELEASE_DECISION",
          json.dumps({key: findings[key] for key in
                      ["approved", "reason", "has_changes", "elapsed_seconds"]}))
    if not findings["approved"]:
        raise ValueError("Quality gates rejected candidate: " +
                         json.dumps({key: value for key, value in findings["gates"].items()
                                     if not value}))
    return findings


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("public/data/v1/manifest.json"))
    parser.add_argument("--policy", type=Path, default=Path("backend/autopilot_policy.json"))
    parser.add_argument("--output", type=Path, default=Path("autopilot-output"))
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    parser.add_argument("--offline", action="store_true", help="Never fetch remote sources; test existing snapshot.")
    parser.add_argument("--resume", action="store_true", help="Reuse source checkpoints if baseline/policy unchanged.")
    args = parser.parse_args()
    run(args)


if __name__ == "__main__":
    try:
        main()
    except (ValueError, RuntimeError, OSError, KeyError) as exc:
        print("AUTOPILOT_BLOCKED", type(exc).__name__, str(exc), file=sys.stderr)
        sys.exit(2)
