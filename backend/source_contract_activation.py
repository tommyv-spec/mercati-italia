#!/usr/bin/env python3
"""Opt-in generic municipal source admission. Defaults to ZERO approved sources.

Approving a verified publisher is a change to TWO versioned JSON documents:
its source contract and the source-level admission certificate. This module
never makes a per-market approval, invents event confirmation or edits legacy
records. Bad/unavailable sources are isolated so the accepted dataset survives.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import date

from source_contract_ingest import apply_approved
from source_lifecycle import digest, validate_contracts
from source_probe import limited_fetch

MAX_APPROVALS = 8
MAX_NEW_PER_RUN = 250


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
        result[sid]=row
    if set(result)!=set(expected):
        raise ValueError("DEV-only publisher approval must match every active source contract")
    if sum(x["max_new_ids"] for x in result.values())>MAX_NEW_PER_RUN:
        raise ValueError("Too many new source identities allowed in one scheduled cycle")
    return result


def activate(config,registry,existing,*,today=None,offline=False,
             fetch=limited_fetch):
    today=today or date.today()
    approvals=validate_admissions(config,registry)
    if not isinstance(existing,list) or len({x.get("slug") for x in existing})!=len(existing):
        raise ValueError("Existing stable market IDs are missing or repeated")
    originals=list(existing)
    candidate=list(existing)
    profiles={p["id"]:p for p in config["raw_profiles"]}
    status=Counter()
    report={}
    for sid in sorted(approvals):
        profile=profiles[sid]
        cert=approvals[sid]
        if offline:
            report[sid]={"schema":1,"status":"offline_no_source_inference",
                         "new_market_ids":[],"existing_records_removed":0,
                         "individual_market_openings_confirmed":0}
            status["offline_skipped"]+=1
            continue
        try:
            blob,overflow=fetch(profile["resource_url"])
            if overflow or len(blob)>profile["max_bytes"]:
                raise ValueError("Approved publisher full snapshot exceeded authorized byte budget")
            additions,proof=apply_approved(profile,blob,candidate,cert,today=today)
            if proof["old_ids_modified"] or proof["old_ids_removed"] or proof["verified_events_created"]:
                raise ValueError("Source-level import changed previously approved market data")
            candidate=additions
            status["approved_sources_reconciled"]+=1
            status["new_source_venues_staged_for_DEV"]+=len(proof["new_venue_ids"])
            report[sid]={
                "schema":1,"status":"source_contract_approved_staged_only",
                "approval_sha256":digest(cert),
                "new_market_ids":proof["new_venue_ids"],
                "old_market_ids_preserved":proof["original_market_records"],
                "verified_market_openings_created":0,
                "new_navigation_enabled":0,"new_geocodes_created":0,
                "independent_static_validation_required":True,
            }
        except (ValueError,OSError,TimeoutError,UnicodeError,KeyError) as exc:
            # Treat an unreadable or incomplete SOURCE as deferred, never as
            # no-market or a municipal closure. Other approved sources proceed.
            report[sid]={
                "schema":1,"status":"publisher_source_held_for_review",
                "error_type":type(exc).__name__,
                "new_market_ids":[],
                "existing_records_removed":0,
                "individual_market_openings_confirmed":0,
            }
            status["publisher_sources_held"]+=1
    if candidate[:len(originals)]!=originals:
        raise ValueError("Source admission mutated a previously published market")
    # Stable, deterministic order of new official identities, independently
    # of publisher row order and parallel source registration order.
    candidate=[*originals,*sorted(candidate[len(originals):],key=lambda row:row["slug"])]
    ids=[x["slug"] for x in candidate]
    if len(ids)!=len(set(ids)) or len(candidate)>len(existing)+MAX_NEW_PER_RUN:
        raise ValueError("A generic source inserted duplicate or excess market identities")
    summary={
        "schema":1,"source_registry_sha256":digest(registry),
        "source_contract_sha256":digest(config),
        "publication_channel":"dev-only",
        "source_contracts_active":len(approvals),
        "original_market_ids":len(existing),"candidate_market_ids":len(candidate),
        "new_market_ids":sorted(ids[len(existing):]),
        "record_ids_deleted":0,"old_market_fields_changed":0,
        "new_market_openings_confirmed":0,"new_market_coordinates_created":0,
        "new_market_directions_enabled":0,
        "status_counts":dict(sorted(status.items())),
        "per_source":report,
        "requires_independent_release_qa":True,
    }
    return candidate,summary


def validate_release(before,after,report,config,registry):
    if (not isinstance(before,list) or not isinstance(after,list)
            or report.get("schema")!=1
            or report.get("source_registry_sha256")!=digest(registry)
            or report.get("source_contract_sha256")!=digest(config)
            or report.get("original_market_ids")!=len(before)
            or report.get("candidate_market_ids")!=len(after)
            or after[:len(before)]!=before
            or len(after)-len(before)!=len(report.get("new_market_ids",[]))
            or [x["slug"] for x in after[len(before):]]!=report.get("new_market_ids",[])
            or any(report.get(k)!=0 for k in (
                "record_ids_deleted","old_market_fields_changed",
                "new_market_openings_confirmed","new_market_coordinates_created",
                "new_market_directions_enabled"))):
        raise ValueError("Independent generic source release proof does not match exact original IDs")
    return {
        "schema":1,"stable_original_market_ids_checked":len(before),
        "source_approved_added_venue_id_count":len(after)-len(before),
        "old_market_records_changed":0,"market_openings_confirmed":0,
        "new_coordinates_created":0,"new_navigation_enabled":0,
        "source_registry_digest":report["source_registry_sha256"],
        "release_safe":True,
    }
