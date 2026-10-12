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
from lombardia_overlap import review as review_lombardia_overlaps, markdown as lombardia_overlap_markdown
from recurrence_refresh import refresh_records
from source_lifecycle import run as inspect_source_contracts, markdown as source_lifecycle_markdown
from milano_2026_overlay import reconcile as reconcile_milano_2026, PDF_DATE as MILAN_PDF_DATE
from milano_2026_release_guard import verify as verify_milano_2026_diff, verify_exported as verify_milano_2026_exported
from roma_xiii_2026_venues import (
    integrate as add_curated_roma_2026_venues,
    validate_added as verify_curated_roma_2026_additions,
    EVIDENCE_FILE as ROMA_2026_VENUE_EVIDENCE_FILE,
)
from roma_xiii_2026_release_guard import check_static as check_curated_roma_2026_static
from roma_xiii_geo_hold import (
    apply_holds as apply_roma_xiii_holds,
    verify_diff as verify_roma_xiii_diff,
    verify_static as verify_roma_xiii_static,
    git_blob_sha as roma_source_git_blob_sha,
    SOURCE_GIT_BLOB_SHA as ROMA_XIII_SOURCE_BLOB,
)
from publisher_exception_review import (
    apply_source_repairs, verify_diff as verify_publisher_diff,
    verify_static as verify_publisher_static, evidence_digest as publisher_digest,
)
import source_milano
import source_firenze
import source_lombardia
import source_bologna
import source_corciano
from corciano_overlap import review as review_corciano_overlaps, markdown as corciano_overlap_markdown
from official_enrichment import enrich as enrich_official_records, markdown as official_enrichment_markdown
from municipality_release_guard import check as check_municipality_changes
from reviewed_city_evidence import (
    apply_reviewed_cities, verify_reviewed_diff, manifest_id as reviewed_city_manifest_id,
    REVIEWED_ON as REVIEWED_CITY_DATE
)
from municipality_reconciliation import (
    reconcile as reconcile_official_municipalities,
    markdown as municipality_review_markdown, ISTAT_SHA as TRUSTED_ISTAT_SHA,
    SOURCE_DATE as TRUSTED_ISTAT_DATE,
)

SCHEMA = 1
PHASES = ("baseline", "sources", "enrichment", "merge", "municipalities",
          "source_lifecycle", "reviewed_cities", "milano_2026", "roma_2026_venues", "forecast",
          "reviewed_publishers", "roma_geo_hold", "export", "quality")
SOURCE_FUNCTIONS = {
    "milano": (source_milano.download, source_milano.convert),
    "firenze": (source_firenze.download, source_firenze.convert),
    # Integration is registered, but not enabled by daily policy until its
    # full dry-run source/quality/mobile audit succeeds.
    "lombardia": (source_lombardia.download, source_lombardia.convert),
    # Read-only inventory adapter. Disabled in daily policy until a
    # separately tested full official-source audit explicitly approves it.
    "bologna": (source_bologna.download, source_bologna.convert),
    # First observed manually on four official CSV rows; requires full audit
    # before the daily source policy can enable unattended collection.
    "corciano": (source_corciano.download, source_corciano.convert),
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
    # Do not catch TypeError from an importer: a malformed publisher schema
    # must fail closed, not silently retry another call signature.
    return convert(raw) if source_id == "firenze" else convert(raw, today=today)


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
    if source_status.get("lombardia", {}).get("status") not in ("retrieved", "resumed_checkpoint"):
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
                       policy: dict, forecast_stats: dict, sources_status: dict,
                       reviewed_city_corrections: dict | None = None) -> dict:
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
    reviewed_city_corrections = reviewed_city_corrections or {}
    if len(reviewed_city_corrections) > 60:
        raise ValueError("Unbounded ISTAT-approved municipality changes")
    approved_city_updates = []
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
            proposed = reviewed_city_corrections.get(sid)
            approved = (
                isinstance(proposed, str)
                and proposed == after.get("citta")
                and before.get("regione") == after.get("regione")
                and before.get("citta") != after.get("citta")
                and after.get("citta_originale") == str(before.get("citta") or "")[:160]
                and after.get("localita_ricostruita_da") ==
                    "ISTAT comuni 2026-02-21; nome fonte e provincia"
                and after.get("provincia") == before.get("provincia")
            )
            if approved:
                approved_city_updates.append(sid)
            else:
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
        "municipalities_reconciled": len(approved_city_updates),
        "municipality_update_ids": sorted(approved_city_updates)[:25],
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
    enrichment_policy = policy.get("enrichment", {})
    if (not isinstance(enrichment_policy, dict)
            or set(enrichment_policy) - {"enabled","source"}
            or enrichment_policy.get("enabled", False) not in (True, False)
            or (enrichment_policy.get("enabled") and
                enrichment_policy.get("source") != "lombardia-mercap")):
        raise ValueError("Unreviewed official enrichment policy")
    municipal_policy = policy.get("municipalities", {})
    if (not isinstance(municipal_policy, dict)
            or set(municipal_policy) - {"enabled", "reference_date", "source_sha256"}
            or municipal_policy.get("enabled", False) not in (True, False)
            or (municipal_policy.get("enabled") and (
                municipal_policy.get("reference_date") != TRUSTED_ISTAT_DATE
                or municipal_policy.get("source_sha256") != TRUSTED_ISTAT_SHA
            ))):
        raise ValueError("Unreviewed ISTAT municipal reconciliation policy")
    reviewed_policy = policy.get("reviewed_source_cities", {})
    if (not isinstance(reviewed_policy, dict)
            or set(reviewed_policy) - {"enabled", "reviewed_on", "evidence_sha256"}
            or reviewed_policy.get("enabled", False) not in (True,False)
            or (reviewed_policy.get("enabled") and (
                municipal_policy.get("enabled") is not True
                or reviewed_policy.get("reviewed_on") != REVIEWED_CITY_DATE
                or not isinstance(reviewed_policy.get("evidence_sha256"),str)
                or len(reviewed_policy["evidence_sha256"]) != 64
            ))):
        raise ValueError("Unapproved reviewed-city evidence policy")
    publisher_policy = policy.get("reviewed_publisher_exceptions", {})
    publisher_enabled = isinstance(publisher_policy, dict) and publisher_policy.get("enabled") is True
    if (not isinstance(publisher_policy, dict)
            or set(publisher_policy) - {"enabled", "reviewed_on", "evidence_sha256"}
            or (reviewed_policy.get("enabled") is True and not publisher_enabled)
            or (publisher_enabled and (
                publisher_policy.get("reviewed_on") != "2026-10-12"
                or not isinstance(publisher_policy.get("evidence_sha256"),str)
                or len(publisher_policy["evidence_sha256"]) != 64
                or municipal_policy.get("enabled") is not True))):
        raise ValueError("Five approved publisher exception protections cannot be disabled")
    # A newly reviewed municipal PDF is permitted to renew only existing
    # Milano weekly forecasts where the independent official GIS agrees.
    # The pinned Git-blob IDs make a changed source an explicit code review.
    milano_policy = policy.get("milano_2026_dual_source", {})
    milano_enabled = isinstance(milano_policy, dict) and milano_policy.get("enabled") is True
    if (not isinstance(milano_policy, dict)
            or set(milano_policy) - {"enabled", "document_date", "pdf_blob_sha1", "gis_blob_sha1"}
            or milano_policy.get("enabled", False) not in (True, False)
            or (milano_enabled and (
                milano_policy.get("document_date") != MILAN_PDF_DATE.isoformat()
                or milano_policy.get("pdf_blob_sha1") != "87ac8ce87140d34ca7c399a1e32f30d587488571"
                or milano_policy.get("gis_blob_sha1") != "523643489c0a27b8fabd2272e4b1e5205249d2e7"
                or not any(item.get("id") == "milano" and item.get("enabled") is True
                           for item in policy["sources"])
            ))):
        raise ValueError("Unreviewed 2026 Milan publisher-source evidence policy")

    # A referenced 2024 municipal map disproves two approximate Rome city
    # points. It may only remove those points and stop unsafe directions;
    # never auto-geocode or confirm a 2026 market.
    roma_hold_policy = policy.get("roma_xiii_coordinate_holds", {})
    roma_holds_enabled = isinstance(roma_hold_policy, dict) and roma_hold_policy.get("enabled") is True
    if (not isinstance(roma_hold_policy, dict)
            or set(roma_hold_policy) - {"enabled", "reviewed_on", "source_blob_sha1"}
            or roma_hold_policy.get("enabled", False) not in (True, False)
            or (roma_holds_enabled and (
                roma_hold_policy.get("reviewed_on") != "2026-10-12"
                or roma_hold_policy.get("source_blob_sha1") != ROMA_XIII_SOURCE_BLOB
            ))):
        raise ValueError("Unreviewed Rome XIII coordinate hold policy")

    # Eight official municipality identities: two already published, five
    # source-supported distinct venues, and one unverified relocation held.
    # Only the five pinned IDs can enter DEV. A refreshed publisher document
    # must be approved explicitly; no runtime inference or bulk import.
    roma_venues_policy = policy.get("roma_xiii_2026_venues", {})
    roma_venues_enabled = isinstance(roma_venues_policy, dict) and roma_venues_policy.get("enabled") is True
    if (not isinstance(roma_venues_policy, dict)
            or set(roma_venues_policy) - {"enabled","reviewed_on","evidence_blob_sha1"}
            or roma_venues_policy.get("enabled",False) not in (True,False)
            or (roma_venues_enabled and (
                roma_venues_policy.get("reviewed_on") != "2026-10-13"
                or roma_venues_policy.get("evidence_blob_sha1")
                    != "de49718515825371f97d8968b2d8630c8db0999a"
                or roma_holds_enabled is not True
            ))):
        raise ValueError("Unapproved municipal 2026 Rome venue expansion policy")

    # All source-level contracts use one schema/identity/freshness engine.
    # Their report is read-only; no new market may enter via this stage.
    lifecycle_policy = policy.get("source_lifecycle", {})
    lifecycle_enabled = isinstance(lifecycle_policy,dict) and lifecycle_policy.get("enabled") is True
    if (not isinstance(lifecycle_policy,dict) or
            set(lifecycle_policy)-{"enabled","reviewed_contract_blob_sha1"} or
            lifecycle_policy.get("enabled",False) not in (True,False) or
            (lifecycle_enabled and lifecycle_policy.get("reviewed_contract_blob_sha1")
             != "a2e2853bc9467aad5f3c3f3b44c9e7b03c3c2320")):
        raise ValueError("Unreviewed reusable source contract schema")

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
    raw_fetched = len(feeds)
    # Exact per-source IDs are kept *only in memory* for reconciliation
    # with the generic lifecycle. They are never written in public assets.
    source_dispositions = {}
    report = {
        "schema": 1, "review_only": True, "source_total": 0,
        "accepted": 0, "quarantined": 0, "counts": {},
        "quarantined_examples": [], "market_confirmations": 0,
        "deleted_existing_records": 0,
    }
    if source_status.get("lombardia", {}).get("status") in ("retrieved", "resumed_checkpoint"):
        candidates = [x for x in feeds if str(x["slug"]).startswith("lo-mercap-")]
        reviewed, report = review_lombardia_overlaps(old_rows, candidates)
        if len(reviewed) < 950:
            raise ValueError("Lombardia: too many records overlap with the baseline; manual QA")
        selected = {x["slug"] for x in reviewed}
        source_dispositions["lombardia"] = sorted(
            {x["slug"] for x in candidates} - selected
        )
        feeds = [x for x in feeds if not str(x["slug"]).startswith("lo-mercap-")
                 or x["slug"] in selected]
        source_status["lombardia"]["accepted_after_overlap_qa"] = len(reviewed)
        source_status["lombardia"]["quarantined_review"] = report["quarantined"]
    save_json(out / "lombardia-overlaps.json", report)
    (out / "LOMBARDIA_OVERLAPS.md").write_text(
        lombardia_overlap_markdown(report), encoding="utf-8")
    bologna_report = {
        "schema": 1, "region": "Emilia-Romagna", "source_prefix": "bo-open-",
        "review_only": True, "source_total": 0, "accepted": 0,
        "quarantined": 0, "counts": {}, "quarantined_examples": [],
        "market_confirmations": 0, "deleted_existing_records": 0,
    }
    if source_status.get("bologna", {}).get("status") in ("retrieved", "resumed_checkpoint"):
        bologna_rows = [r for r in feeds if str(r["slug"]).startswith("bo-open-")]
        vetted, bologna_report = review_lombardia_overlaps(
            old_rows, bologna_rows, region="Emilia-Romagna",
            source_prefix="bo-open-", max_conflicts=48
        )
        if len(vetted) < 8:
            raise ValueError("Bologna: excessive exact venue overlaps; review before import")
        vetted_ids = {r["slug"] for r in vetted}
        source_dispositions["bologna"] = sorted(
            {r["slug"] for r in bologna_rows} - vetted_ids
        )
        feeds = [r for r in feeds if not str(r["slug"]).startswith("bo-open-")
                 or r["slug"] in vetted_ids]
        source_status["bologna"]["accepted_after_overlap_qa"] = len(vetted)
        source_status["bologna"]["quarantined_review"] = bologna_report["quarantined"]
    save_json(out / "bologna-overlaps.json", bologna_report)
    (out / "BOLOGNA_OVERLAPS.md").write_text(
        lombardia_overlap_markdown(bologna_report), encoding="utf-8")
    corciano_report = {
        "schema": 1, "region": "Umbria", "source_prefix": "pg-corciano-",
        "review_only": True, "source_total": 0, "accepted": 0,
        "quarantined": 0, "counts": {}, "quarantined_examples": [],
        "market_confirmations": 0, "deleted_existing_records": 0,
    }
    if source_status.get("corciano", {}).get("status") in ("retrieved", "resumed_checkpoint"):
        official_rows = [r for r in feeds if str(r["slug"]).startswith("pg-corciano-")]
        screened, corciano_report = review_corciano_overlaps(old_rows, official_rows)
        accepted_ids = {r["slug"] for r in screened}
        source_dispositions["corciano"] = sorted(
            {r["slug"] for r in official_rows} - accepted_ids
        )
        feeds = [r for r in feeds if not str(r["slug"]).startswith("pg-corciano-")
                 or r["slug"] in accepted_ids]
        source_status["corciano"]["accepted_after_overlap_qa"] = len(screened)
        source_status["corciano"]["quarantined_review"] = corciano_report["quarantined"]
        source_status["corciano"]["source_csv_sha256"] = (
            official_rows[0].get("source_csv_sha256") if official_rows else None
        )
    save_json(out / "corciano-overlaps.json", corciano_report)
    (out / "CORCIANO_OVERLAPS.md").write_text(
        corciano_overlap_markdown(corciano_report), encoding="utf-8")
    checkpoint(out, "sources", {
        "total_fetched": raw_fetched, "total_after_review": len(feeds),
        "sources": source_status,
        "lombardia_overlap_quarantined": report["quarantined"],
        "bologna_overlap_quarantined": bologna_report["quarantined"],
        "corciano_overlap_quarantined": corciano_report["quarantined"],
    })
    # Source contracts are evaluated from existing fetch-once checkpoints.
    # Do not issue a second request, invent an event or edit a market here.
    lifecycle_report = {
        "schema":1,"source_contract_schema":1,"reference_date":args.today.isoformat(),
        "read_only":True,"market_imports":0,"market_updates":0,
        "market_confirmations":0,"market_identity_deletions":0,
        "catalog_count":len(old_rows),"sources":{},"checked_source_profiles":0,
        "source_checks":{},
    }
    if lifecycle_enabled:
        profile_file=Path(__file__).resolve().parent / "data" / "market-source-contracts.json"
        data=profile_file.read_bytes()
        pinned=hashlib.sha1(
            b"blob "+str(len(data)).encode()+b"\0"+data
        ).hexdigest()
        if pinned!=lifecycle_policy["reviewed_contract_blob_sha1"]:
            raise ValueError("Publisher contract registry changed without source-level review")
        prior_path=Path("reports/automation/source-lifecycle.json")
        prior=read_json(prior_path) if prior_path.is_file() else None
        lifecycle_report=inspect_source_contracts(
            read_json(profile_file),old_rows,
            source_dir=out/"sources",previous=prior,
            source_status=source_status,
            source_dispositions=source_dispositions,today=args.today
        )
    if any(lifecycle_report.get(k)!=0 for k in (
            "market_imports","market_updates","market_confirmations","market_identity_deletions")):
        raise ValueError("A source-quality audit may not alter market data")
    save_json(out/"source-lifecycle.json",lifecycle_report)
    (out/"SOURCE_LIFECYCLE.md").write_text(
        source_lifecycle_markdown(lifecycle_report),encoding="utf-8"
    )
    checkpoint(out,"source_lifecycle",{
        "enabled":lifecycle_enabled,
        "profiles_inspected":lifecycle_report["checked_source_profiles"],
        "source_checks":lifecycle_report["source_checks"],
        "new_markets_imported":0,"event_verifications_created":0,
    })
    # Correlate blocked exact venue/day public records with older market
    # cards. Never promote event verification, dates or primary identity.
    enrichment_report = {
        "schema":1, "source_id":"lombardia-mercap", "source_rows_screened":0,
        "review_only":True, "legacy_records_changed":0,
        "existing_market_hours_added":0, "official_source_attributions_added":0,
        "exact_matches":0, "counts":{}, "samples":[],
        "record_identity_changes":0, "confirmed_date_changes":0,
        "individual_market_verifications":0, "coordinates_overwritten":0,
        "primary_sources_overwritten":0, "old_dataset_dates_overwritten":0,
    }
    enriched_base = old_rows
    if enrichment_policy.get("enabled") and (
            source_status.get("lombardia", {}).get("status")
            in ("retrieved","resumed_checkpoint")):
        approved_ids = {r["slug"] for r in feeds
                        if str(r["slug"]).startswith("lo-mercap-")}
        held = [r for r in read_json(out / "sources" / "lombardia.json")
                if r["slug"] not in approved_ids]
        enriched_base, enrichment_report = enrich_official_records(
            old_rows, held, source_id="lombardia-mercap", today=args.today
        )
        enrichment_report["enabled"] = True
    else:
        enrichment_report["enabled"] = bool(enrichment_policy.get("enabled"))
    save_json(out / "official-enrichment.json", enrichment_report)
    (out / "OFFICIAL_ENRICHMENT.md").write_text(
        official_enrichment_markdown(enrichment_report), encoding="utf-8")
    checkpoint(out, "enrichment", {
        "enabled": enrichment_report["enabled"],
        "updated_legacy_rows": enrichment_report["legacy_records_changed"],
        "hours_added": enrichment_report["existing_market_hours_added"],
        "source_attributions_added": enrichment_report["official_source_attributions_added"],
    })
    merged, merge_stats = combine(enriched_base, feeds)
    merged, absent_stats = quarantine_absent_official_lombardia(
        merged, old_rows, feeds, source_status
    )
    merge_stats.update(absent_stats)
    if not merged or len(merged) < int(policy["gates"]["min_total_records"]):
        raise ValueError("Merge produced implausible record count")
    save_json(out / "intermediate" / "merged.json", merged)
    checkpoint(out, "merge", merge_stats)
    municipality_report = {
        "schema": 1, "istat_reference": TRUSTED_ISTAT_DATE,
        "source_file_sha256": TRUSTED_ISTAT_SHA,
        "review_only": True, "enabled": False,
        "records_total": len(merged), "ids_preserved": True,
        "market_confirmations_created": 0, "verified_dates_created": 0,
        "coordinates_changed": 0, "publisher_sources_replaced": 0,
        "counts": {}, "examples": [], "unresolved_examples": [],
    }
    reviewed_city_corrections = {}
    municipality_rows = merged
    if municipal_policy.get("enabled"):
        ref_path = Path(__file__).resolve().parent / "data" / "istat-comuni-2026.json"
        reference = read_json(ref_path)
        municipality_rows, municipality_report = reconcile_official_municipalities(
            merged, reference, apply=True
        )
        municipality_report["enabled"] = True
        if [r["slug"] for r in merged] != [r["slug"] for r in municipality_rows]:
            raise ValueError("Municipality reconciliation modified stable record IDs")
        for original, current in zip(merged, municipality_rows):
            if original.get("citta") != current.get("citta"):
                reviewed_city_corrections[current["slug"]] = current["citta"]
        if (len(reviewed_city_corrections) !=
                municipality_report["counts"].get("city_fixed", 0)):
            raise ValueError("ISTAT city corrections do not match the review report")
        if (len(reviewed_city_corrections) > 60
                or municipality_report["counts"].get("records_calendar_quarantined", 0) > 80):
            raise ValueError("Municipality repair exceeds bounded safety thresholds")
        save_json(out / "intermediate" / "municipalities.json", municipality_rows)
    save_json(out / "municipality-reconciliation.json", municipality_report)
    (out / "MUNICIPALITY_RECONCILIATION.md").write_text(
        municipality_review_markdown(municipality_report), encoding="utf-8"
    )
    municipality_guard = check_municipality_changes(
        merged, municipality_rows, municipality_report
    )
    save_json(out / "municipality-release-guard.json", municipality_guard)
    checkpoint(out, "municipalities", {
        "allowed_source_changes": municipality_guard["changes"],
        "safeguarded_IDs": municipality_guard["checked_ids"],
        "enabled": bool(municipality_report["enabled"]),
        "city_fixed": municipality_report["counts"].get("city_fixed", 0),
        "calendar_quarantined": municipality_report["counts"].get(
            "records_calendar_quarantined", 0
        ),
        "manual_review": municipality_report["counts"].get(
            "needs_manual_municipality_review", 0
        ),
        "source_istat_sha": TRUSTED_ISTAT_SHA,
    })
    # Reviewed publisher city headings are not automatically inferred by ISTAT.
    # This opt-in second proof chain can change only displayed city plus
    # quarantine demonstrably false map points / unvalidated directions.
    reviewed_rows = municipality_rows
    reviewed_report = {
        "schema":1, "enabled":False, "review_only":True,
        "records_total":len(municipality_rows), "changed_ids":[],
        "reviewed_at":REVIEWED_CITY_DATE,
        "individual_events_confirmed":0, "publisher_links_replaced":0,
        "opening_dates_added":0, "market_records_deleted":0,
        "counts":{"cases":0,"city_fixed":0,"coordinates_quarantined":0,
                  "navigation_hold_added":0},
    }
    reviewed_certificate = {
        "schema":1, "records_checked":len(municipality_rows), "identities_deleted":0,
        "cities_corrected":0, "unsafe_points_suppressed":0,
        "navigation_routes_paused":0, "market_verifications_created":0,
    }
    if reviewed_policy.get("enabled"):
        reference_file = Path(__file__).resolve().parent / "data" / "istat-comuni-2026.json"
        evidence_file = Path(__file__).resolve().parent / "data" / "reviewed-city-evidence-2026-10-12.json"
        verified_reference = read_json(reference_file)
        original_evidence = read_json(evidence_file)
        if reviewed_city_manifest_id(original_evidence) != reviewed_policy["evidence_sha256"]:
            raise ValueError("Reviewed manual municipality evidence changed without reapproval")
        reviewed_rows, reviewed_report = apply_reviewed_cities(
            municipality_rows, verified_reference, original_evidence, apply=True
        )
        reviewed_report["enabled"] = True
        reviewed_certificate = verify_reviewed_diff(
            municipality_rows, reviewed_rows, reviewed_report,
            verified_reference, original_evidence
        )
        if len(reviewed_rows) != len(municipality_rows):
            raise ValueError("Manual source city review changed catalog cardinality")
        for original, current in zip(municipality_rows, reviewed_rows):
            if original["slug"] != current["slug"]:
                raise ValueError("Manual source review changed market identity")
            if original.get("citta") != current.get("citta"):
                if current["slug"] in reviewed_city_corrections:
                    raise ValueError("Same source city changed by both ISTAT and manual review")
                reviewed_city_corrections[current["slug"]] = current["citta"]
        if reviewed_certificate["cities_corrected"] != reviewed_report["counts"]["city_fixed"]:
            raise ValueError("Manual source city review proof counts do not match")
        save_json(out / "intermediate" / "reviewed-cities.json", reviewed_rows)
    save_json(out / "reviewed-cities.json", reviewed_report)
    save_json(out / "reviewed-cities-release-guard.json", reviewed_certificate)
    checkpoint(out, "reviewed_cities", {
        "enabled":bool(reviewed_report["enabled"]),
        "cities_corrected":reviewed_certificate["cities_corrected"],
        "points_quarantined":reviewed_certificate["unsafe_points_suppressed"],
        "navigation_suspended":reviewed_certificate["navigation_routes_paused"],
    })
    # Apply the exact two-source proof *before* rolling recurrence dates.
    # Report data-level source freshness, not individual event confirmation.
    milano_rows = reviewed_rows
    milano_report = {
        "schema":1, "enabled":False, "review_only":True,
        "records_total":len(reviewed_rows), "records_added":0,"records_deleted":0,
        "verified_future_events_created":0, "confirmed_dates_created":0,
        "coordinates_changed":0, "primary_sources_changed":0,
        "reconciled_id_count":0, "modified_ids":[], "counts":{},
    }
    milano_guard = {
        "schema":1, "stable_ids_checked":len(reviewed_rows), "milan_source_changes":0,
        "market_ids_added":0, "market_ids_removed":0, "verified_events_added":0,
        "source_originals_lost":0, "coordinates_edited":0, "release_safe":True,
        "enabled":False,
    }
    if milano_enabled:
        pdf_path = Path(__file__).resolve().parent / "data" / "milano-mss-oct2026-observations.json"
        gis_path = Path(__file__).resolve().parent / "data" / "milano-mss-gis-reviewed.json"
        def pinned_git_blob_sha(path):
            data = path.read_bytes()
            return hashlib.sha1(b"blob " + str(len(data)).encode() + b"\0" + data).hexdigest()
        if (pinned_git_blob_sha(pdf_path) != milano_policy["pdf_blob_sha1"]
                or pinned_git_blob_sha(gis_path) != milano_policy["gis_blob_sha1"]):
            raise ValueError("Pinned Milan publisher files changed without source review")
        pdf_evidence = read_json(pdf_path)
        gis_evidence = read_json(gis_path)
        milano_rows, milano_report = reconcile_milano_2026(
            reviewed_rows, pdf_evidence, gis_evidence, today=args.today, apply=True
        )
        milano_report["enabled"] = True
        milano_guard = verify_milano_2026_diff(
            reviewed_rows, milano_rows, milano_report, pdf_evidence, gis_evidence
        )
        if milano_guard.get("release_safe") is not True:
            raise ValueError("Milan publisher change failed independent field proof")
        save_json(out / "intermediate" / "milano-2026.json", milano_rows)
    save_json(out / "milano-2026-review.json", milano_report)
    save_json(out / "milano-2026-diff-guard.json", milano_guard)
    checkpoint(out, "milano_2026", {
        "enabled":milano_enabled,
        "approved_existing_market_ids":milano_report["reconciled_id_count"],
        "source_fields_renewed":len(milano_report["modified_ids"]),
        "verified_openings_created":0,
    })

    # Existing market source records remain untouched. Official 2026 market
    # venue identities are inserted before forecast regeneration. This is the
    # only place where these five pinned new IDs may enter the daily catalog.
    roma_2026_source = None
    roma_2026_report = {
        "schema":1,"enabled":False,"review_only":True,
        "existing_catalog_records":len(milano_rows),
        "new_market_ids":[],"already_published_curated_ids":[],
        "candidate_venue_records":0,"new_market_count":0,
        "records_added":0,"records_removed":0,"existing_records_changed":0,
        "new_coordinates_added":0,"new_opening_confirmations":0,
        "new_human_verifications":0,
    }
    roma_2026_diff = {
        "schema":1,"old_market_records_checked":len(milano_rows),
        "approved_official_market_additions":0,
        "original_records_modified":0,"source_urls_lost":0,
        "verified_events_created":0,"precise_geocodes_created":0,
        "directions_activated":0,"safe":True,"enabled":False,
    }
    if roma_venues_enabled:
        if (roma_source_git_blob_sha(ROMA_2026_VENUE_EVIDENCE_FILE)
                != roma_venues_policy["evidence_blob_sha1"]):
            raise ValueError("Reviewed 2026 Roma XIII market identity evidence changed")
        roma_2026_source = read_json(ROMA_2026_VENUE_EVIDENCE_FILE)
        before_roma = milano_rows
        milano_rows,roma_2026_report = add_curated_roma_2026_venues(
            before_roma,roma_2026_source,apply=True,today=args.today
        )
        roma_2026_diff = verify_curated_roma_2026_additions(
            before_roma,milano_rows,roma_2026_report,roma_2026_source
        )
        if roma_2026_diff.get("safe") is not True:
            raise ValueError("Review-only Roma market imported without exact evidence")
        save_json(out / "intermediate" / "roma-2026-venues.json", milano_rows)
    save_json(out / "roma-xiii-2026-venues.json",roma_2026_report)
    save_json(out / "roma-xiii-2026-venues-diff-guard.json",roma_2026_diff)
    checkpoint(out,"roma_2026_venues",{
        "enabled":roma_venues_enabled,
        "new_market_identifiers":roma_2026_report["new_market_ids"],
        "source_records_added":roma_2026_report["records_added"],
        "already_published":len(roma_2026_report["already_published_curated_ids"]),
        "source_event_confirmations":0,
    })

    projected, forecast_stats = refresh_records(
        milano_rows, args.today, policy["forecast"]["days"],
        policy["forecast"]["max_source_age_days"])
    if len(projected) != len(merged) + roma_2026_report["records_added"]:
        raise ValueError("Forecast must never remove market identities")
    save_json(out / "intermediate" / "forecasted.json", projected)
    checkpoint(out, "forecast", forecast_stats)

    if publisher_enabled:
        # Independently vetted publisher facts are applied *after* generic rolling
        # recurrence, so the normal 120-day expansion cannot reanimate Todi's
        # documented winter closure on a later daily run.
        pinned_publisher = read_json(
            Path(__file__).resolve().parent / "data" / "publisher-review-2026-10-12.json"
        )
        if publisher_digest(pinned_publisher) != publisher_policy["evidence_sha256"]:
            raise ValueError("Publisher-reviewed location/calendar evidence digest changed")
        publisher_istat = read_json(Path(__file__).resolve().parent / "data" / "istat-comuni-2026.json")
        source_fixed, publisher_report = apply_source_repairs(
            projected, publisher_istat, pinned_publisher, today=args.today, apply=True
        )
        publisher_diff = verify_publisher_diff(projected, source_fixed, publisher_report, pinned_publisher)
        for left, right in zip(projected, source_fixed):
            if left.get("citta") != right.get("citta"):
                if right["slug"] in reviewed_city_corrections:
                    raise ValueError("Both municipality overlays changed the same original source city")
                reviewed_city_corrections[right["slug"]] = right["citta"]
        if len(source_fixed) != len(projected):
            raise ValueError("Publisher repair removed a market identity")
        projected = source_fixed
        save_json(out / "intermediate" / "reviewed-publishers.json", projected)
        save_json(out / "publisher-exception-review.json", publisher_report)
        save_json(out / "publisher-exception-diff-guard.json", publisher_diff)
        checkpoint(out, "reviewed_publishers", publisher_report["counts"])

    # Two specific source contradictions: generic centre-of-Rome map point is
    # 6–11 km from the explicitly named 2024 municipal venues. Old points
    # are retained for audit; never substitute old map markers as new geocodes.
    rome_source=None
    rome_report={
        "schema":1,"enabled":False,"review_only":True,"record_count":len(projected),
        "source_cases":0,"record_ids_added":0,"record_ids_removed":0,
        "market_openings_confirmed":0,"source_links_replaced":0,
        "market_calendar_dates_changed":0,"changed_ids":[],
        "new_coordinates_quarantined":0,"new_directions_blocked":0,
    }
    rome_certificate={
        "schema":1,"records_checked":len(projected),"changed_source_market_ids":[],
        "new_coordinate_holds":0,"new_navigation_holds":0,"ids_added":0,
        "ids_deleted":0,"original_source_urls_lost":0,
        "event_verifications_created":0,"release_safe":True,"enabled":False,
    }
    if roma_holds_enabled:
        source_file=Path(__file__).resolve().parent / "data" / "roma-municipio-xiii-market-map-reviewed.json"
        if roma_source_git_blob_sha(source_file)!=roma_hold_policy["source_blob_sha1"]:
            raise ValueError("Pinned public Municipio XIII reference changed")
        rome_source=read_json(source_file)
        before_rome=projected
        projected,rome_report=apply_roma_xiii_holds(projected,rome_source,apply=True)
        rome_certificate=verify_roma_xiii_diff(
            before_rome,projected,rome_report,rome_source
        )
        if rome_certificate.get("release_safe") is not True:
            raise ValueError("Rome coordinate-only quarantine changed an unreviewed field")
        save_json(out / "intermediate" / "rome-before-geo-holds.json", before_rome)
        save_json(out / "intermediate" / "rome-after-geo-holds.json", projected)
    save_json(out / "roma-xiii-geo-holds.json", rome_report)
    save_json(out / "roma-xiii-diff-guard.json", rome_certificate)
    checkpoint(out, "roma_geo_hold", {
        "enabled":roma_holds_enabled,
        "source_markets":2 if roma_holds_enabled else 0,
        "new_points_quarantined":rome_report["new_coordinates_quarantined"],
        "new_navigation_holds":rome_report["new_directions_blocked"],
        "opening_verifications_created":0,
    })

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
    if publisher_enabled:
        publisher_static = verify_publisher_static(
            dest / "manifest.json", pinned_publisher, policy
        )
        if publisher_static.get("release_safe") is not True:
            raise ValueError("Reviewed publisher coordinates/dates missing from final DEV files")
        save_json(out / "publisher-exception-static-safety.json", publisher_static)
    if roma_holds_enabled:
        roma_final_proof=verify_roma_xiii_static(dest / "manifest.json",rome_source)
        if roma_final_proof.get("release_safe") is not True:
            raise ValueError("The exported catalog restored unsafe Rome source coordinates")
        save_json(out / "roma-xiii-static-guard.json", roma_final_proof)
    if roma_venues_enabled:
        venue_static_proof = check_curated_roma_2026_static(
            dest / "manifest.json", roma_2026_source, args.today
        )
        if venue_static_proof.get("release_safe") is not True:
            raise ValueError("Approved Roman municipality identities lost in final static assets")
        save_json(out / "roma-xiii-2026-venues-static-guard.json", venue_static_proof)
    new_report = audit(dest / "manifest.json", args.today)
    new_rows = load_existing(dest / "manifest.json")
    if milano_enabled:
        # The Milano guard is a *same-ID* source audit. Its source baseline
        # predates the separately reviewed five Roma venue additions on the
        # first run only; the independently source-proven new IDs must not be
        # mistaken for a Milano identity mutation.
        reviewed_roma_added = set(roma_2026_report["new_market_ids"])
        if reviewed_roma_added and (
                len(reviewed_roma_added) != roma_2026_report["records_added"]
                or any(not x.startswith("rm13-") for x in reviewed_roma_added)):
            raise ValueError("Untrusted Roma market IDs in Milano source proof")
        milano_comparable = [x for x in new_rows if x["slug"] not in reviewed_roma_added]
        milano_static_guard = verify_milano_2026_exported(
            old_rows, milano_comparable, milano_report, pdf_evidence, gis_evidence, args.today
        )
        if milano_static_guard.get("quality_safe") is not True:
            raise ValueError("Reviewed Milano 2026 forecasts lost source/safety in final assets")
        save_json(out / "milano-2026-static-guard.json", milano_static_guard)
    findings = compare_candidates(old_rows, new_rows, old_report, new_report, policy,
                                  forecast_stats, source_status,
                                  reviewed_city_corrections=reviewed_city_corrections)
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
