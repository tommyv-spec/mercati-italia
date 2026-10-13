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

from source_contract_ingest import MAX_STAGING_SOURCE_ROWS, apply_approved
from source_lifecycle import digest, validate_contracts
from source_probe import limited_fetch
from reviewed_city_evidence import NAVIGATION_HOLD

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
            status["eligible_venues_deferred_to_next_run"]+=proof["deferred_candidate_count"]
            report[sid]={
                "schema":1,"status":"source_contract_approved_staged_only",
                "approval_sha256":digest(cert),
                "new_market_ids":proof["new_venue_ids"],
                "source_eligible_candidates":proof["source_eligible_candidates"],
                "deferred_candidate_count":proof["deferred_candidate_count"],
                "deferred_candidate_ids_sha256":proof["deferred_candidate_ids_sha256"],
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
    approved=validate_admissions(config,registry)
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
    raw_profiles={p["id"]:p for p in config["raw_profiles"]}
    if report.get("source_contracts_active")!=len(approved):
        raise ValueError("Independent source approval count does not match registry")
    new_by_source={}
    for sid in approved:
        source=report.get("per_source",{}).get(sid)
        if (not isinstance(source,dict)
                or source.get("status") not in (
                    "source_contract_approved_staged_only",
                    "publisher_source_held_for_review",
                    "offline_no_source_inference"
                ) or not isinstance(source.get("new_market_ids"),list)):
            raise ValueError("Missing independent publisher import disposition")
        new_by_source[sid]=source["new_market_ids"]
        if source["status"]!="source_contract_approved_staged_only":
            if source["new_market_ids"]:
                raise ValueError("Unavailable/offline publisher cannot claim new market IDs")
        else:
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
                    or any(ch not in "0123456789abcdef" for ch in pending_hash)):
                raise ValueError("Approved publisher exceeded quota or lost deferred proof")
    if sorted(x for values in new_by_source.values() for x in values)!=report["new_market_ids"]:
        raise ValueError("Individual source additions do not match complete publisher reports")
    for record in after[len(before):]:
        sid=record["slug"]
        matching=[raw_profiles[x] for x in approved
                  if sid in new_by_source[x]]
        if len(matching)!=1:
            raise ValueError("New market ID has no unique approved source")
        origin=matching[0]
        if (not sid.startswith(origin["catalog_slug_prefix"])
                or record.get("url_fonte")!=origin["attribution_url"]
                or record.get("aggiornato_il")!=origin["source_dataset_date"]
                or record.get("aggiornamento_ambito")!="dataset"
                or record.get("status")!="non_confermato"
                or record.get("date_quality")!="sconosciuta"
                or record.get("date")
                or record.get("verificato_il")
                or record.get("lat") is not None
                or record.get("lng") is not None
                or record.get("position_quality")!="sconosciuta"
                or record.get("navigazione_sospesa_motivo")!=NAVIGATION_HOLD):
            raise ValueError("Unsafe field in source-approved DEV market candidate: "+sid)
    return {
        "schema":1,"stable_original_market_ids_checked":len(before),
        "source_approved_added_venue_id_count":len(after)-len(before),
        "old_market_records_changed":0,"market_openings_confirmed":0,
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
    from recurrence_refresh import explicit_rule
    from reviewed_city_static_guard import INDEX_FIELDS
    if not isinstance(today,date):
        raise ValueError("Final publisher source check needs a reference date")
    approved=validate_admissions(config,registry)
    manifest_path=Path(manifest_path)
    manifest=json.loads(manifest_path.read_text("utf-8"))
    source_ids=report.get("new_market_ids",[])
    if (report.get("schema")!=1
            or report.get("publication_channel")!="dev-only"
            or report.get("source_registry_sha256")!=digest(registry)
            or report.get("source_contract_sha256")!=digest(config)
            or report.get("source_contracts_active")!=len(approved)
            or not isinstance(source_ids,list) or len(source_ids)!=len(set(source_ids))
            or not isinstance(manifest.get("total"),int)
            or report.get("candidate_market_ids")!=manifest["total"]
            or manifest["total"]<report.get("original_market_ids",0)
            or manifest["total"]-report["original_market_ids"]!=len(source_ids)):
        raise ValueError("Final public catalog does not match generic source admission proof")
    rows=load_existing(manifest_path)
    if len(rows)!=manifest["total"]:
        raise ValueError("Final generic source output has incomplete regional records")
    catalog={x["slug"]:x for x in rows}
    indexed_path=manifest_path.parent.parent.parent/manifest["index"]
    index=json.loads(indexed_path.read_text("utf-8"))
    by_index={x[0]:x for x in index["markets"] if x and x[0] in source_ids}
    if len(by_index)!=len(source_ids):
        raise ValueError("Approved publisher identity absent from compact search index")
    profiles={p["id"]:p for p in config["raw_profiles"]}
    scoped={}
    for sid in approved:
        detail=report.get("per_source",{}).get(sid)
        if not isinstance(detail,dict):
            raise ValueError("Publisher report lacks source-level review outcome")
        for market_id in detail.get("new_market_ids",[]):
            if market_id in scoped:
                raise ValueError("Duplicated publisher source identity")
            scoped[market_id]=profiles[sid]
    if set(scoped)!=set(source_ids):
        raise ValueError("Unattributed publisher markets in static export")
    dates_predicted=0
    for sid in source_ids:
        row=catalog.get(sid)
        source=scoped[sid]
        if row is None:
            raise ValueError("Approved market missing from full regional details")
        if (row.get("url_fonte")!=source["attribution_url"]
                or row.get("aggiornato_il")!=source["source_dataset_date"]
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
        compact=dict(zip(INDEX_FIELDS,by_index[sid]))
        if (compact.get("lat") is not None or compact.get("lng") is not None
                or compact.get("position_quality")!="sconosciuta"
                or compact.get("date_quality")!=row.get("date_quality")):
            raise ValueError("Generic source index restored navigation or unsafe dates")
        rule=explicit_rule(row.get("ricorrenza_testo"))
        if row.get("date_quality")=="prevista":
            if (rule is None or rule.get("kind")!="weekly"
                    or not row.get("date")
                    or (today-date.fromisoformat(source["source_dataset_date"])).days>
                       source.get("max_forecast_source_age_days",source["max_source_age_days"])
                    or any(item<today.isoformat() or
                           date.fromisoformat(item).weekday() not in rule["weekdays"]
                           for item in row["date"])):
                raise ValueError("Invalid publisher-source weekly forecast in static catalog")
            dates_predicted+=1
        elif row.get("date"):
            raise ValueError("Unconfirmed generic source has an unlabelled market date")
    return {
        "schema":1,"source_contracts_active":len(approved),
        "market_records_checked":len(rows),
        "new_source_venue_ids_verified":len(source_ids),
        "source_weekly_forecasts_only":dates_predicted,
        "navigation_holds_in_index":len(source_ids),
        "no_individual_market_openings_confirmed":True,
        "new_precise_coordinates":0,
        "original_markets_deleted":0,
        "release_safe":True,
    }
