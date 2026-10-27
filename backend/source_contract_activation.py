#!/usr/bin/env python3
"""Generic municipal updates for contracts in the reviewed admission registry.

Approving a verified publisher is a change to TWO versioned JSON documents:
its source contract and the source-level admission certificate. This module
never makes a per-market approval or invents event confirmation. Existing
fields change only with exact previous engine ownership and new source proof.
Bad/unavailable sources are isolated so the accepted dataset survives.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
from collections import Counter
from datetime import date, datetime, timezone
from http.client import HTTPException
from pathlib import Path
from urllib.parse import urlsplit

from source_contract_ingest import (
    FIELD_MANAGER, MAX_STAGING_SOURCE_ROWS, PublishedSourceDriftError, apply_approved,
    authorize, observed_source_date, source_metadata, verify_fill, verify_update,
)
from field_evidence import FIELDS, as_day, clean_receipts, fingerprint, valid_receipt
from source_lifecycle import _public_https, digest, validate_contracts
from source_probe import limited_fetch
from publisher_snapshot_date import (
    LANDING_STRATEGY, MAX_LANDING_BYTES, MAX_METADATA_BYTES, ODH_STRATEGY, TRENTINO_STRATEGY,
    discover_document, make_event_change_proof, make_landing_page_proof, make_snapshot_date_proof,
    resolve_source_date, validate_strategy,
)
from opendatahub_events import request_url
import trentino_calendar
from reviewed_city_evidence import NAVIGATION_HOLD
import atomic_write

MAX_APPROVALS = 8
MAX_NEW_PER_RUN = 250


def _atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    atomic_write.replace(temporary, path)


def _cache_context(source_cache, config, registry, existing, today, resume):
    if source_cache is None:
        return None, None
    directory = Path(source_cache)
    context = {"schema": 1, "baseline_sha256": fingerprint(existing),
               "source_contract_sha256": digest(config), "source_registry_sha256": digest(registry),
               "reference_date": today.isoformat()}
    path = directory / "context.json"
    if path.exists():
        previous = json.loads(path.read_text("utf-8"))
        if resume and previous != context:
            raise ValueError("Cannot resume generic sources: baseline, contracts or reference date changed")
    elif resume:
        return directory, digest(context)
    if not resume:
        _atomic_json(path, context)
    return directory, digest(context)


def read_source_snapshot(profile, *, fetch, read_on, today):
    """Read one complete source version, bracketing dynamic data with metadata."""
    strategy = validate_strategy(profile)
    dynamic = strategy != "fixed_reviewed"
    if not as_day(read_on) or as_day(read_on) > today:
        raise ValueError("Real source read date is later than the requested reference date")

    def bounded(url, limit):
        body, overflow = (fetch(url, max_bytes=limit)
                          if strategy in (LANDING_STRATEGY, ODH_STRATEGY, TRENTINO_STRATEGY)
                          else fetch(url))
        if not isinstance(body, bytes) or overflow or not 0 < len(body) <= limit:
            raise ValueError("Approved publisher full snapshot exceeded authorized byte budget")
        return body

    if strategy == LANDING_STRATEGY:
        # The stable landing page names this year's file; its URL changes yearly.
        landing = bounded(profile["resource_url"], MAX_LANDING_BYTES)
        document_url, year = discover_document(profile, landing, read_on=read_on)
        blob = bounded(document_url, profile["max_bytes"])
        proof = make_landing_page_proof(profile, landing, document_url, year, blob,
                                        read_on=read_on, today=today)
        resolve_source_date(profile, proof=proof, blob=blob, read_on=read_on, today=today)
        return blob, proof

    if strategy in (ODH_STRATEGY, TRENTINO_STRATEGY):
        if strategy == ODH_STRATEGY:
            # Events still running or ended within the lookback: the begin date follows the read day.
            blob = bounded(request_url(profile, read_on), profile["max_bytes"])
        else:
            # Every search page of the window, then each market's page: one compact snapshot.
            blob = trentino_calendar.snapshot(
                profile, lambda url: bounded(url, trentino_calendar.MAX_PAGE_BYTES), read_on)
            if len(blob) > profile["max_bytes"]:
                raise ValueError("Approved publisher full snapshot exceeded authorized byte budget")
        proof = make_event_change_proof(profile, blob, read_on=read_on, today=today)
        resolve_source_date(profile, proof=proof, blob=blob, read_on=read_on, today=today)
        return blob, proof

    before = bounded(profile["source_metadata_url"], MAX_METADATA_BYTES) if dynamic else None
    blob = bounded(profile["resource_url"], profile["max_bytes"])
    after = bounded(profile["source_metadata_url"], MAX_METADATA_BYTES) if dynamic else None
    proof = (make_snapshot_date_proof(profile, blob, before_metadata=before,
        after_metadata=after, read_on=read_on, today=today) if dynamic else None)
    resolve_source_date(profile, proof=proof, blob=blob, read_on=read_on, today=today)
    return blob, proof


def _source_snapshot(profile, *, cache, context, memory, resume, offline, fetch, read_on, today):
    url = profile["resource_url"]
    # A dynamic proof is bound to the exact reviewed profile digest. Two
    # profiles pointing to one URL cannot share each other's date assertion.
    key = (digest({"url": url, "profile": digest(profile)}) if
           profile.get("source_date_strategy", "fixed_reviewed") != "fixed_reviewed" else digest(url))
    path = cache / (key + ".json") if cache is not None else None
    saved = memory.get(key)
    if saved is None and path is not None and path.exists():
        if path.stat().st_size > (profile["max_bytes"] + 2 * MAX_METADATA_BYTES) * 2 + 8192:
            raise ValueError("Oversized approved source checkpoint")
        stored = json.loads(path.read_text("utf-8"))
        if not isinstance(stored, dict):
            raise ValueError("Invalid source checkpoint object")
        if stored.get("context_sha256") == context:
            saved = stored
        elif resume:
            raise ValueError("Source checkpoint belongs to a different approved run")
    if saved is not None:
        if (saved.get("schema") != 1 or saved.get("source_url") != url
                or saved.get("context_sha256") != context
                or not as_day(saved.get("source_read_on"))
                or as_day(saved["source_read_on"]) > today):
            raise ValueError("Invalid source checkpoint provenance")
        if (not isinstance(saved.get("body_base64"), str) or
                len(saved["body_base64"]) > 4 * ((profile["max_bytes"] + 2) // 3)):
            raise ValueError("Invalid or oversized source checkpoint encoding")
        blob = base64.b64decode(saved["body_base64"], validate=True)
        if len(blob) > profile["max_bytes"] or hashlib.sha256(blob).hexdigest() != saved.get("sha256"):
            raise ValueError("Source checkpoint content fingerprint changed")
        proof = saved.get("source_date_proof")
        resolve_source_date(profile, proof=proof, blob=blob,
                            read_on=saved["source_read_on"], today=today)
        memory[key] = saved
        return blob, saved["source_read_on"], "resumed_checkpoint" if resume else "cached_snapshot", proof
    if resume or offline:
        return None, None, "resume_checkpoint_missing" if resume else "offline_no_source_inference", None
    blob, proof = read_source_snapshot(profile, fetch=fetch, read_on=read_on, today=today)
    saved = {"schema": 1, "source_url": url, "context_sha256": context,
             "source_read_on": read_on, "sha256": hashlib.sha256(blob).hexdigest(),
             "body_base64": base64.b64encode(blob).decode("ascii")}
    if proof is not None:
        saved["source_date_proof"] = proof
    memory[key] = saved
    if path is not None:
        _atomic_json(path, saved)
    return blob, read_on, "retrieved", proof


def validate_admissions(config, registry):
    validate_contracts(config)
    if (not isinstance(registry,dict)
            or registry.get("schema")!=1
            or registry.get("publication_channel")!="dev-only"
            or registry.get("user_event_confirmations_allowed") is not False
            or not isinstance(registry.get("approvals"),list)
            or len(registry["approvals"])>MAX_APPROVALS):
        raise ValueError("Malformed or overly permissive generic source approval registry")
    expected={p["id"]:p for p in config["raw_profiles"]
              if p.get("publication_mode")=="approved_dev_only"}
    result={}
    for row in registry["approvals"]:
        if not isinstance(row,dict):
            raise ValueError("Invalid publisher approval entry")
        sid=row.get("source_id")
        if not isinstance(sid,str) or sid in result or sid not in expected:
            raise ValueError("Missing, duplicate or unapproved source import identity")
        if (type(row.get("max_new_ids")) is not int
                or row["max_new_ids"]<1
                or row["max_new_ids"]>expected[sid]["max_new_ids_per_run"]):
            raise ValueError("Source approval could exceed reviewed per-source growth allowance")
        if (type(expected[sid].get("enabled")) is not bool
                or row.get("reviewed_profile_sha256") != digest(expected[sid])):
            raise ValueError("Source approval does not match the exact enabled/disabled profile")
        # A disabled profile still needs the same structural certificate.
        # Dataset age and source-row drift are runtime checks in authorize().
        profile = expected[sid]
        license_url = row.get("publisher_license_evidence_url")
        reviewed = as_day(row.get("reviewed_on"))
        if (set(row) != {"schema", "mode", "source_id", "reviewed_profile_sha256",
                         "publisher_license_evidence_url", "identity_granularity", "reviewed_on",
                         "max_new_ids", "source_record_kind", "source_specific_geo_approval"}
                or row.get("schema") != 1 or row.get("mode") != "approved_dev_only"
                or row.get("identity_granularity") != profile["row_kind"]
                or row.get("source_record_kind") != profile["row_kind"]
                or row.get("source_specific_geo_approval") is not False
                or not isinstance(license_url, str) or not _public_https(license_url)
                or urlsplit(license_url).hostname not in {
                    urlsplit(profile["resource_url"]).hostname,
                    urlsplit(profile["attribution_url"]).hostname}
                or not reviewed or reviewed < date(2025, 1, 1)
                or row["reviewed_on"] != reviewed.isoformat()):
            raise ValueError("Source approval certificate has inconsistent rights or identity fields")
        result[sid]=row
    if set(result)!=set(expected):
        raise ValueError("DEV-only publisher approval must match every active source contract")
    if sum(x["max_new_ids"] for x in result.values())>MAX_NEW_PER_RUN:
        raise ValueError("Too many new source identities allowed in one scheduled cycle")
    return result


def active_profile_count(config, approvals):
    """Count enabled profiles only after validating the complete registry."""
    return sum(p["id"] in approvals and p.get("enabled") is True
               for p in config["raw_profiles"])


def _validate_disabled_disposition(profile, source):
    disabled = profile.get("enabled") is False
    if disabled != (source.get("status") == "source_contract_disabled"):
        raise ValueError("Publisher disposition differs from its reviewed enabled switch")
    if disabled and any(source.get(key) for key in (
            "new_market_ids", "updates", "updated_fields_count", "source_observations", "fills",
            "source_read_on", "source_read_mode", "source_snapshot_sha256", "new_venue_evidence",
            "source_date_proof")):
        raise ValueError("Disabled publisher cannot claim reads, additions or field changes")


def activate(config,registry,existing,*,today=None,offline=False,
             fetch=limited_fetch,source_cache=None,resume=False,read_on=None):
    today=today or date.today()
    approvals=validate_admissions(config,registry)
    if not isinstance(existing,list) or len({x.get("slug") for x in existing})!=len(existing):
        raise ValueError("Existing stable market IDs are missing or repeated")
    originals=list(existing)
    candidate=list(existing)
    read_on = str(read_on or datetime.now(timezone.utc).date())
    cache, context = _cache_context(source_cache, config, registry, existing, today, resume)
    snapshots = {}
    claimed_updates = set()
    claimed_fills = set()
    profiles={p["id"]:p for p in config["raw_profiles"]}
    status=Counter()
    report={}
    for sid in sorted(approvals):
        profile=profiles[sid]
        cert=approvals[sid]
        if profile["enabled"] is False:
            report[sid] = {"schema": 1, "status": "source_contract_disabled",
                           "new_market_ids": [], "updates": [], "updated_fields_count": 0,
                           "existing_records_removed": 0,
                           "individual_market_openings_confirmed": 0}
            status["source_contracts_disabled"] += 1
            continue
        try:
            blob, observed_on, mode, date_proof = _source_snapshot(
                profile, cache=cache, context=context, memory=snapshots, resume=resume,
                offline=offline, fetch=fetch, read_on=read_on, today=today)
            if blob is None:
                report[sid]={"schema":1,"status":mode,
                             "new_market_ids":[],"updates":[],"existing_records_removed":0,
                             "individual_market_openings_confirmed":0}
                status["resume_skipped" if resume else "offline_skipped"]+=1
                continue
            additions,proof=apply_approved(profile,blob,candidate,cert,today=today,read_on=observed_on,
                                          source_date_proof=date_proof)
            changed = {p["slug"] for p in proof["updates"]}
            filled = {p["slug"] for p in proof["fills"]}
            original_ids = {row["slug"] for row in originals}
            if (proof["old_ids_removed"] or proof["verified_events_created"]
                    or (changed | filled) & (claimed_updates | claimed_fills) or changed & filled
                    or len(filled) != len(proof["fills"])
                    or any(mid not in original_ids for mid in changed | filled)):
                raise ValueError("Source-level import lost or multiply claimed a prior market identity")
            source_before = {row["slug"]:row for row in candidate}
            source_after = {row["slug"]:row for row in additions}
            for update in proof["updates"]:
                verify_update(profile, source_before[update["slug"]], source_after[update["slug"]],
                              update, today=today, source_observations=proof["source_observations"])
            filled_fields = sum(
                verify_fill(profile, source_before[fill["slug"]], source_after[fill["slug"]], fill,
                            today=today, source_observations=proof["source_observations"])
                for fill in proof["fills"])
            candidate=additions
            claimed_updates.update(changed)
            claimed_fills.update(filled)
            status["other_publishers_market_fields_filled"]+=filled_fields
            status["approved_sources_reconciled"]+=1
            status["new_source_venues_staged_for_DEV"]+=len(proof["new_venue_ids"])
            status["eligible_venues_deferred_to_next_run"]+=proof["deferred_candidate_count"]
            status["existing_source_fields_updated"]+=proof["old_fields_modified"]
            status["existing_source_evidence_refreshed"]+=proof["old_ids_modified"]
            report[sid]={
                "schema":1,"status":"source_contract_approved_staged_only",
                "approval_sha256":digest(cert),
                "source_read_mode":mode,"source_read_on":observed_on,
                "updates":proof["updates"],"updated_fields_count":proof["old_fields_modified"],
                "fills":proof["fills"],"filled_fields_count":filled_fields,
                "fill_counts":proof["fill_counts"],
                "source_observations":proof["source_observations"],
                "new_market_ids":proof["new_venue_ids"],
                "new_venue_evidence":proof["new_venue_evidence"],
                "source_eligible_candidates":proof["source_eligible_candidates"],
                "deferred_candidate_count":proof["deferred_candidate_count"],
                "deferred_candidate_ids_sha256":proof["deferred_candidate_ids_sha256"],
                "old_market_ids_preserved":proof["original_market_records"],
                "verified_market_openings_created":0,
                "new_navigation_enabled":0,"new_geocodes_created":0,
                "independent_static_validation_required":True,
            }
        except (ValueError,OSError,TimeoutError,UnicodeError,KeyError,HTTPException) as exc:
            # Treat an unreadable or incomplete SOURCE as deferred, never as
            # no-market or a municipal closure. Other approved sources proceed.
            is_drift=isinstance(exc,PublishedSourceDriftError)
            retirements=getattr(exc,"retirements",[])
            retired_rows={}
            original_ids={row["slug"] for row in originals}
            source_before={row["slug"]:row for row in candidate}
            for row,proof in retirements:
                mid=row["slug"]
                if mid in claimed_updates or mid not in original_ids or proof.get("action")!="retire":
                    raise ValueError("Source retirement ambiguously claimed an existing market")
                verify_update(profile,source_before[mid],row,proof,today=today,
                              source_observations=getattr(exc,"source_report",{}))
                retired_rows[mid]=row
            if retired_rows:
                candidate=[retired_rows.get(row["slug"],row) for row in candidate]
                claimed_updates.update(retired_rows)
                status["source_evidence_retirements"]+=len(retired_rows)
            report[sid]={
                "schema":1,"status":"publisher_source_held_for_review",
                "error_type":type(exc).__name__,
                "hold_reason":("previously_published_identity_calendar_or_hours_changed"
                               if is_drift else "unavailable_or_invalid_source"),
                "new_market_ids":[],
                "updates":[proof for _,proof in retirements],"updated_fields_count":0,
                "approval_sha256":digest(cert),
                "source_observations":getattr(exc,"source_report",{}),
                "field_review_needed":getattr(exc,"source_report",{}).get("review_reason_counts",{}),
                "field_audit_counts":getattr(exc,"source_report",{}).get("field_audit_counts",{}),
                "source_read_on":getattr(exc,"source_report",{}).get("source_read_on"),
                "source_snapshot_sha256":getattr(exc,"source_report",{}).get("source_snapshot_sha256"),
                "existing_records_removed":0,
                "individual_market_openings_confirmed":0,
            }
            status["publisher_sources_held"]+=1
            if is_drift:
                status["published_source_drift_held"]+=1
    if [r["slug"] for r in candidate[:len(originals)]] != [r["slug"] for r in originals]:
        raise ValueError("Source admission mutated a previously published market identity")
    # Stable, deterministic order of new official identities, independently
    # of publisher row order and parallel source registration order.
    candidate=[*candidate[:len(originals)],*sorted(candidate[len(originals):],key=lambda row:row["slug"])]
    ids=[x["slug"] for x in candidate]
    if len(ids)!=len(set(ids)) or len(candidate)>len(existing)+MAX_NEW_PER_RUN:
        raise ValueError("A generic source inserted duplicate or excess market identities")
    summary={
        "schema":1,"source_registry_sha256":digest(registry),
        "reference_date":today.isoformat(),
        "source_contract_sha256":digest(config),
        "publication_channel":"dev-only",
        "source_contracts_active":active_profile_count(config, approvals),
        "source_contracts_approved":len(approvals),
        "original_market_ids":len(existing),"candidate_market_ids":len(candidate),
        "new_market_ids":sorted(ids[len(existing):]),
        "record_ids_deleted":0,"old_market_fields_changed":sum(
            len(p["changed_fields"]) for detail in report.values() for p in detail.get("updates",[])),
        "updated_market_ids":sorted({p["slug"] for detail in report.values()
                                     for p in detail.get("updates",[]) if p["changed_fields"]}),
        "evidence_updated_market_ids":sorted(claimed_updates),
        "filled_market_ids":sorted(claimed_fills),
        "filled_fields_count":sum(detail.get("filled_fields_count",0) for detail in report.values()),
        "new_market_openings_confirmed":0,"new_market_coordinates_created":0,
        "new_market_directions_enabled":0,
        "status_counts":dict(sorted(status.items())),
        "per_source":report,
        "requires_independent_release_qa":True,
    }
    validate_release(existing,candidate,summary,config,registry)
    return candidate,summary


def _validate_source_observation(profile,certificate,source,*,today,held=False):
    observations=source.get("source_observations")
    if (not isinstance(observations,dict)
            or observations.get("source_id")!=profile["id"]
            or observations.get("profile_sha256")!=digest(profile)
            or observations.get("source_url")!=profile["resource_url"]
            or observations.get("publisher")!=profile["publisher"]
            or any(not isinstance(observations.get(key),str) or
                   len(observations[key])!=64 or
                   any(ch not in "0123456789abcdef" for ch in observations[key])
                   for key in ("source_snapshot_sha256","source_parsed_sha256"))
            or source.get("approval_sha256")!=digest(certificate)
            or observations.get("source_read_on")!=source.get("source_read_on")
            or not as_day(source.get("source_read_on"))
            or as_day(source["source_read_on"])>today
            or not isinstance(source.get("updates"),list)):
        raise ValueError("Independent source observation differs from the read snapshot")
    try:
        authorize(profile,observations,certificate,today=today)
    except PublishedSourceDriftError:
        if not held:
            raise
    else:
        if held:
            raise ValueError("Source evidence retirement has no documented field conflict")
    return observations


def validate_release(before,after,report,config,registry):
    approved=validate_admissions(config,registry)
    reference = as_day(report.get("reference_date"))
    if (not isinstance(before,list) or not isinstance(after,list)
            or not reference
            or report.get("schema")!=1
            or report.get("source_registry_sha256")!=digest(registry)
            or report.get("source_contract_sha256")!=digest(config)
            or report.get("original_market_ids")!=len(before)
            or report.get("candidate_market_ids")!=len(after)
            or [row.get("slug") for row in after[:len(before)]] != [row.get("slug") for row in before]
            or len({row.get("slug") for row in after}) != len(after)
            or len(after)-len(before)!=len(report.get("new_market_ids",[]))
            or [x["slug"] for x in after[len(before):]]!=report.get("new_market_ids",[])
            or any(report.get(k)!=0 for k in (
                "record_ids_deleted",
                "new_market_openings_confirmed","new_market_coordinates_created",
                "new_market_directions_enabled"))):
        raise ValueError("Independent generic source release proof does not match exact original IDs")
    raw_profiles={p["id"]:p for p in config["raw_profiles"]}
    if (report.get("source_contracts_active")!=active_profile_count(config, approved)
            or report.get("source_contracts_approved", len(approved)) != len(approved)):
        raise ValueError("Independent source approval count does not match registry")
    before_by = {row["slug"]:row for row in before}
    after_by = {row["slug"]:row for row in after}
    updated = {}
    filled = {}
    field_count = 0
    filled_count = 0
    new_by_source={}
    for sid in approved:
        source=report.get("per_source",{}).get(sid)
        if (not isinstance(source,dict)
                or source.get("status") not in (
                    "source_contract_approved_staged_only",
                    "publisher_source_held_for_review",
                    "offline_no_source_inference", "resume_checkpoint_missing",
                    "source_contract_disabled",
                ) or not isinstance(source.get("new_market_ids"),list)):
            raise ValueError("Missing independent publisher import disposition")
        _validate_disabled_disposition(raw_profiles[sid], source)
        new_by_source[sid]=source["new_market_ids"]
        observations=None
        if source["status"]!="source_contract_approved_staged_only":
            if source["new_market_ids"] or source.get("fills") or (source.get("updates") and (
                    source["status"]!="publisher_source_held_for_review" or
                    any(p.get("action")!="retire" for p in source["updates"]))):
                raise ValueError("Unavailable/offline publisher cannot claim new market IDs or field updates")
            if source.get("updates"):
                observations=_validate_source_observation(
                    raw_profiles[sid],approved[sid],source,today=reference,held=True)
        else:
            observations=_validate_source_observation(raw_profiles[sid],approved[sid],source,today=reference)
            count=source.get("source_eligible_candidates")
            pending=source.get("deferred_candidate_count")
            pending_hash=source.get("deferred_candidate_ids_sha256")
            if (source.get("approval_sha256")!=digest(approved[sid])
                    or len(source["new_market_ids"])>approved[sid]["max_new_ids"]
                    or type(count) is not int or type(pending) is not int
                    or not 0<=pending<=count<=MAX_STAGING_SOURCE_ROWS
                    or count!=len(source["new_market_ids"])+pending
                    or not isinstance(pending_hash,str)
                    or len(pending_hash)!=64
                    or any(ch not in "0123456789abcdef" for ch in pending_hash)
                    or not isinstance(source.get("new_venue_evidence"),dict)
                    or set(source["new_venue_evidence"])!=set(source["new_market_ids"])):
                raise ValueError("Approved publisher exceeded quota or lost deferred proof")
        source_fields = 0
        for proof in source.get("updates",[]):
            mid = proof.get("slug") if isinstance(proof,dict) else None
            if (mid not in before_by or mid in updated
                    or proof.get("receipt",{}).get("sha256") != observations.get("source_parsed_sha256")
                    or proof.get("receipt",{}).get("letto_il") != source["source_read_on"]):
                raise ValueError("Independent generic source update lost source or original identity")
            source_fields += verify_update(raw_profiles[sid], before_by[mid], after_by[mid],
                                           proof, today=reference, source_observations=observations)
            updated[mid] = proof
        if source_fields != source.get("updated_fields_count",0):
            raise ValueError("Independent generic source field update count differs")
        field_count += source_fields
        source_filled = 0
        for proof in source.get("fills",[]):
            mid = proof.get("slug") if isinstance(proof,dict) else None
            if mid not in before_by or mid in updated or mid in filled:
                raise ValueError("Town/day fill lost or multiply claimed an original identity")
            source_filled += verify_fill(raw_profiles[sid], before_by[mid], after_by[mid], proof,
                                         today=reference, source_observations=observations)
            filled[mid] = proof
        if source_filled != source.get("filled_fields_count",0):
            raise ValueError("Independent town/day fill count differs")
        filled_count += source_filled
    if (field_count != report.get("old_market_fields_changed")
            or sorted(updated) != report.get("evidence_updated_market_ids")
            or sorted(mid for mid, proof in updated.items() if proof["changed_fields"])
               != report.get("updated_market_ids")
            or set(updated) & set(filled)
            or sorted(filled) != report.get("filled_market_ids", [])
            or filled_count != report.get("filled_fields_count", 0)
            or any(after_by[mid] != row for mid,row in before_by.items()
                   if mid not in updated and mid not in filled)):
        raise ValueError("Independent generic source diff changed unreported original fields")
    if sorted(x for values in new_by_source.values() for x in values)!=report["new_market_ids"]:
        raise ValueError("Individual source additions do not match complete publisher reports")
    for record in after[len(before):]:
        sid=record["slug"]
        matching=[raw_profiles[x] for x in approved
                  if sid in new_by_source[x]]
        if len(matching)!=1:
            raise ValueError("New market ID has no unique approved source")
        origin=matching[0]
        source_report = report["per_source"][origin["id"]]
        source_date = observed_source_date(origin, source_report["source_observations"], today=reference)
        receipts = record.get("riscontri_campi")
        if (not sid.startswith(origin["catalog_slug_prefix"])
                or record.get("url_fonte")!=origin["attribution_url"]
                or record.get("aggiornato_il")!=source_date
                or record.get("aggiornamento_ambito")!="dataset"
                or record.get("status")!="non_confermato"
                or record.get("date_quality")!="sconosciuta"
                or record.get("date")
                or record.get("verificato_il")
                or record.get("lat") is not None
                or record.get("lng") is not None
                or record.get("position_quality")!="sconosciuta"
                or record.get("navigazione_sospesa_motivo")!=NAVIGATION_HOLD
                or record.get("importato_il") != source_report["source_read_on"]
                or record.get("fonte_letta_il") != source_report["source_read_on"]
                or record.get("fonte_aggiornata_il") != source_date):
            raise ValueError("Unsafe field in source-approved DEV market candidate: "+sid)
        if (not isinstance(receipts,list) or len(receipts) != 1
                or not valid_receipt(receipts[0],record,today=reference)
                or receipts[0].get("fonte_id") != origin["id"]
                or receipts[0].get("url") != origin["resource_url"]
                or receipts[0].get("riga_fonte") != sid
                or receipts[0].get("letto_il") != source_report["source_read_on"]
                or receipts[0].get("fonte_aggiornata_il") != source_date
                or receipts[0].get("sha256") != source_report["source_observations"]["source_parsed_sha256"]
                or receipts[0].get("gestore_campi") != FIELD_MANAGER
                or receipts[0].get("campi_gestiti") != sorted(receipts[0]["valori"])):
            raise ValueError("New publisher venue lacks exact initial managed field evidence")
        if source_report["new_venue_evidence"].get(sid)!={
                "identity":{key:record.get(key) for key in ("slug","nome","citta","regione","provincia")},
                "fields":{field:record.get(field) for field in FIELDS},"receipt":receipts[0]}:
            raise ValueError("New publisher fields differ from admitted snapshot evidence")
    return {
        "schema":1,"stable_original_market_ids_checked":len(before),
        "source_approved_added_venue_id_count":len(after)-len(before),
        "old_market_records_changed":len(updated),"old_market_fields_changed":field_count,
        "other_publishers_markets_filled":len(filled),"other_publishers_fields_filled":filled_count,
        "market_openings_confirmed":0,
        "new_coordinates_created":0,"new_navigation_enabled":0,
        "source_registry_digest":report["source_registry_sha256"],
        "release_safe":True,
    }


def verify_static(manifest_path,report,config,registry,today):
    """Independently review final lazy-loaded regional JSON AND compact index.

    The approved publisher's data date may authorize *predicted weekly dates*,
    never confirmed individual opening events. We never invent navigation.
    """
    from pathlib import Path
    from merge_catalog import load_existing
    from recurrence_refresh import explicit_rule, forecast_source_limits, project_dates, refresh_record
    from source_lifecycle import MONTH_KIND
    from compact_index import index_fields, index_options, project_index
    if not isinstance(today,date):
        raise ValueError("Final publisher source check needs a reference date")
    approved=validate_admissions(config,registry)
    forecast_limits=forecast_source_limits(config)
    manifest_path=Path(manifest_path)
    manifest=json.loads(manifest_path.read_text("utf-8"))
    projection_options = index_options(manifest)
    fields = index_fields(manifest["index_schema"])
    source_ids=report.get("new_market_ids",[])
    evidence_ids=report.get("evidence_updated_market_ids",[])
    rows=load_existing(manifest_path)
    if not isinstance(manifest.get("total"),int) or len(rows)!=manifest["total"]:
        raise ValueError("Final generic source output has incomplete regional records")
    admission_certificate=report.get("happings_detail_admission_certificate")
    separately_proved=0
    later_ids=set()
    cohort_total=len(rows)
    if admission_certificate is not None:
        from happings_detail_enrichment import verify_source_admission_certificate
        if (not isinstance(admission_certificate,dict)
                or not isinstance(admission_certificate.get("admissions"),list)
                or any(not isinstance(item,dict) or not isinstance(item.get("market_id"),str)
                       for item in admission_certificate["admissions"])):
            raise ValueError("Invalid later publisher admission certificate")
        later_ids={item["market_id"] for item in admission_certificate["admissions"]}
        if (not isinstance(source_ids,list) or not isinstance(evidence_ids,list)
                or later_ids & (set(source_ids)|set(evidence_ids))):
            raise ValueError("Two publishers claim the same new or updated market identity")
        # This source's historical report stores its cohort size, while the
        # later Happings phase retains independently reconstructable page
        # facts. Validate the complete rows before excluding those exact IDs
        # from this source's count. Keep the actual manifest and index below.
        cohort=[row for row in rows if row["slug"] not in later_ids]
        cohort,separately_proved=verify_source_admission_certificate(
            cohort,rows,admission_certificate,today)
        cohort_total=len(cohort)
    if (report.get("schema")!=1
            or report.get("publication_channel")!="dev-only"
            or report.get("source_registry_sha256")!=digest(registry)
            or report.get("source_contract_sha256")!=digest(config)
            or report.get("source_contracts_active")!=active_profile_count(config, approved)
            or report.get("source_contracts_approved", len(approved)) != len(approved)
            or not isinstance(source_ids,list) or len(source_ids)!=len(set(source_ids))
            or not isinstance(evidence_ids,list) or len(evidence_ids)!=len(set(evidence_ids))
            or set(evidence_ids) & set(source_ids)
            or report.get("candidate_market_ids")!=cohort_total
            or cohort_total<report.get("original_market_ids",0)
            or cohort_total-report["original_market_ids"]!=len(source_ids)):
        raise ValueError("Final public catalog does not match generic source admission proof")
    catalog={x["slug"]:x for x in rows}
    indexed_path=manifest_path.parent.parent.parent/manifest["index"]
    index=json.loads(indexed_path.read_text("utf-8"))
    checked_ids=set(source_ids)|set(evidence_ids)|later_ids
    by_index={x[0]:x for x in index["markets"] if x and x[0] in checked_ids}
    if len(by_index)!=len(checked_ids):
        raise ValueError("Approved publisher identity absent from compact search index")
    for mid in checked_ids:
        if by_index[mid] != project_index([catalog[mid]], **projection_options)[0]:
            raise ValueError("Publisher source facts lost in compact search index")
    profiles={p["id"]:p for p in config["raw_profiles"]}
    scoped={}
    updated={}
    observed_dates={}
    for sid in approved:
        detail=report.get("per_source",{}).get(sid)
        if not isinstance(detail,dict):
            raise ValueError("Publisher report lacks source-level review outcome")
        _validate_disabled_disposition(profiles[sid], detail)
        if detail.get("status") == "source_contract_approved_staged_only":
            observations = _validate_source_observation(profiles[sid], approved[sid], detail, today=today)
            observed_dates[sid] = observed_source_date(profiles[sid], observations, today=today)
        elif detail.get("updates"):
            if (detail.get("status") != "publisher_source_held_for_review"
                    or any(proof.get("action") != "retire" for proof in detail["updates"])
                    or detail.get("new_market_ids")):
                raise ValueError("Unavailable source cannot claim new static fields or venues")
            observations = _validate_source_observation(
                profiles[sid], approved[sid], detail, today=today, held=True)
            observed_dates[sid] = observed_source_date(profiles[sid], observations, today=today)
        elif detail.get("new_market_ids"):
            raise ValueError("New static venues have no approved source observation")
        for market_id in detail.get("new_market_ids",[]):
            if market_id in scoped:
                raise ValueError("Duplicated publisher source identity")
            scoped[market_id]=profiles[sid]
        for proof in detail.get("updates",[]):
            market_id=proof.get("slug")
            if market_id in updated:
                raise ValueError("Duplicated publisher field update identity")
            updated[market_id]=(profiles[sid],proof)
    if set(scoped)!=set(source_ids):
        raise ValueError("Unattributed publisher markets in static export")
    if (set(updated)!=set(evidence_ids)
            or sum(len(proof["changed_fields"]) for _,proof in updated.values())
               != report.get("old_market_fields_changed")
            or sorted(mid for mid,(_,proof) in updated.items() if proof["changed_fields"])
               != report.get("updated_market_ids")):
        raise ValueError("Unattributed publisher field updates in static export")
    for mid,(source,proof) in updated.items():
        row=catalog.get(mid)
        observations=report["per_source"][source["id"]]["source_observations"]
        receipt=proof.get("receipt",{})
        target=({**row,**proof["receipt"]["valori"]} if row and proof.get("action")=="retire" else row)
        if (row is None or proof.get("identity_after") != {
                key:row.get(key) for key in ("slug","nome","citta","regione","provincia")}
                or row.get("url_fonte")!=source["attribution_url"]
                or proof.get("public_fields_after")!={field:row.get(field) for field in FIELDS}
                or proof.get("source_metadata_after") != source_metadata(row)
                or not valid_receipt(proof.get("receipt"),target,today=today)
                or receipt.get("fonte_aggiornata_il") != observed_dates[source["id"]]
                or receipt.get("sha256") != observations.get("source_parsed_sha256")
                or receipt.get("letto_il") != observations.get("source_read_on")
                or receipt.get("fonte_id") != source["id"]
                or receipt.get("url") != source["resource_url"]
                or receipt.get("riga_fonte") != mid
                or any(row.get(field)!=change.get("after")
                       for field,change in proof["changed_fields"].items())):
            raise ValueError("Managed publisher fields or identity changed during static export")
        expected=proof.get("observations_after")
        actual=clean_receipts(row.get("riscontri_campi"),row,today=today)
        if (not isinstance(expected,list) or clean_receipts(expected,row,today=today)!=expected
                or actual!=expected):
            raise ValueError("Managed publisher field evidence lost during static export")
        if row.get("date_quality") == "prevista":
            calendar, _ = refresh_record(row, today, source_limits=forecast_limits)
            if calendar.get("date_quality") != "prevista" or not calendar.get("date"):
                raise ValueError("Existing publisher calendar exceeds its source freshness contract")
        compact=dict(zip(fields,by_index[mid]))
        if compact.get("orario_testo")!=row.get("orario_testo"):
            raise ValueError("Managed publisher hours lost in compact search index")
    dates_predicted=0
    for sid in source_ids:
        row=catalog.get(sid)
        source=scoped[sid]
        source_date=observed_dates[source["id"]]
        observations=report["per_source"][source["id"]]["source_observations"]
        evidence=report["per_source"][source["id"]].get("new_venue_evidence",{}).get(sid)
        if row is None:
            raise ValueError("Approved market missing from full regional details")
        if (not isinstance(evidence,dict)
                or evidence.get("identity")!={key:row.get(key) for key in (
                    "slug","nome","citta","regione","provincia")}
                or evidence.get("fields")!={field:row.get(field) for field in FIELDS}
                or not valid_receipt(evidence.get("receipt"),row,today=today)
                or evidence["receipt"].get("fonte_aggiornata_il") != source_date
                or evidence["receipt"].get("sha256") != observations.get("source_parsed_sha256")
                or evidence["receipt"].get("letto_il") != observations.get("source_read_on")
                or evidence["receipt"].get("fonte_id") != source["id"]
                or evidence["receipt"].get("url") != source["resource_url"]
                or evidence["receipt"].get("riga_fonte") != sid
                or row.get("riscontri_campi")!=[evidence["receipt"]]):
            raise ValueError("New publisher field evidence lost or changed during static export")
        if (row.get("url_fonte")!=source["attribution_url"]
                or row.get("aggiornato_il")!=source_date
                or row.get("fonte_aggiornata_il")!=source_date
                or row.get("fonte_letta_il")!=observations.get("source_read_on")
                or row.get("importato_il")!=observations.get("source_read_on")
                or row.get("aggiornamento_ambito")!="dataset"
                or row.get("status")!="non_confermato"
                or row.get("verificato_il")
                or row.get("date_quality") not in ("prevista","sconosciuta")
                or row.get("navigazione_sospesa_motivo")!=NAVIGATION_HOLD
                or row.get("lat") is not None or row.get("lng") is not None
                or row.get("position_quality")!="sconosciuta"
                or not any(isinstance(link,dict) and
                           link.get("url")==source["attribution_url"]
                           for link in row.get("fonti",[]))):
            raise ValueError("Generic source's market metadata, GPS or provenance unsafe: "+sid)
        compact=dict(zip(fields,by_index[sid]))
        if (compact.get("lat") is not None or compact.get("lng") is not None
                or compact.get("position_quality")!="sconosciuta"
                or compact.get("date_quality")!=row.get("date_quality")):
            raise ValueError("Generic source index restored navigation or unsafe dates")
        rule=explicit_rule(row.get("ricorrenza_testo"))
        if row.get("date_quality")=="prevista":
            monthly=source["row_kind"]==MONTH_KIND and rule and rule["kind"]=="monthly_nth_weekday"
            if (rule is None or rule.get("kind")!="weekly" and not monthly
                    or not row.get("date")
                    or (today-date.fromisoformat(source_date)).days>
                       source.get("max_forecast_source_age_days",source["max_source_age_days"])
                    or any(item<today.isoformat() or
                           (item not in project_dates(rule,today,365) if monthly else
                            date.fromisoformat(item).weekday() not in rule["weekdays"])
                           for item in row["date"])):
                raise ValueError("Invalid publisher-source weekly forecast in static catalog")
            dates_predicted+=1
        elif row.get("date"):
            raise ValueError("Unconfirmed generic source has an unlabelled market date")
    result = {
        "schema":1,"source_contracts_active":active_profile_count(config, approved),
        "source_contracts_approved":len(approved),
        "market_records_checked":len(rows),
        "new_source_venue_ids_verified":len(source_ids),
        "existing_source_evidence_ids_checked":len(evidence_ids),
        "existing_source_fields_updated":report["old_market_fields_changed"],
        "source_admission_report_sha256":digest(report),
        "existing_source_evidence_ids_sha256":digest(sorted(evidence_ids)),
        "catalog_content_signature":manifest.get("content_signature"),
        "source_weekly_forecasts_only":dates_predicted,
        "navigation_holds_in_index":len(source_ids),
        "no_individual_market_openings_confirmed":True,
        "new_precise_coordinates":0,
        "original_markets_deleted":0,
        "release_safe":True,
    }
    if admission_certificate is not None:
        result["separately_proved_happings_admissions"]=separately_proved
    return result
