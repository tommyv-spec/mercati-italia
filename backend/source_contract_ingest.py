#!/usr/bin/env python3
"""Generic CSV/JSON municipal venue staging and opt-in, source-approved DEV admission.

No market-specific rules. A source contract supplies fields/identity/format.
A source-level release certificate authorizes a whole vetted publisher source;
without that certificate this module is *read only*. Never claims current
opening, repairs uncertain coordinates, or removes a historic catalog ID.

Importantly the absence of a cross-source venue match is NOT a verified event.
New rows may only be staged, then admitted to DEV by an independent policy.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from lombardia_overlap import weekday_evidence
from source_lifecycle import (
    parse_rows, candidate_record, canonical, digest, validate_contracts,
    weekday as source_weekday,
)

MAX_STAGING_SOURCE_ROWS = 3000
MAX_PROFILE_MAX_NEW = 250
REPORT_EXAMPLES = 12
REVIEW_REASON = frozenset({
    "venue_at_same_street_day", "same_named_market_in_city",
    "generic_city_market_day", "source_identity_changed",
    "duplicate_publisher_identity", "invalid_source_row",
})
SAFE_PREVIEW = frozenset({
    "slug","nome","citta","provincia","regione","indirizzo",
    "orario_testo","ricorrenza_testo","lat","lng","position_quality",
    "categoria","tags","date","date_quality","status","verificato_il",
    "aggiornato_il","aggiornamento_ambito","url_fonte","fonte",
    "navigazione_sospesa_motivo","confidence","descrizione",
})


def _title(text):
    return str(text or "").strip().title()


def validate_format(profile):
    """Validate only deliberately supported declarative presentation options."""
    if not isinstance(profile,dict):
        raise ValueError("Missing source profile")
    fmt=profile.get("presentation",{})
    if not isinstance(fmt,dict) or set(fmt)-{"title_case_name","title_case_address",
                                             "address_suffix_name_prefix"}:
        raise ValueError("Unapproved presentation mapping keys")
    if fmt.get("title_case_name",False) not in (True,False):
        raise ValueError("Invalid name presentation policy")
    if fmt.get("title_case_address",False) not in (True,False):
        raise ValueError("Invalid address presentation policy")
    suffix=fmt.get("address_suffix_name_prefix")
    if suffix is not None and (not isinstance(suffix,str) or not 3<=len(suffix)<=100):
        raise ValueError("Missing approved source locality prefix")
    if profile.get("row_kind") not in ("market_venue","market_venue_day"):
        raise ValueError("Administrative concessions/statistics cannot be admitted as markets")
    # The current registry validator accepts only shadow sources. Do not
    # broaden its release permissions via a mapping flag.
    shadow=copy.deepcopy(profile)
    shadow["publication_mode"]="shadow_only"
    shadow["legal_reuse_reviewed"]=False
    shadow["max_new_ids_per_run"]=0
    validate_contracts({
        "schema":1,"publication_role":"review_only",
        "normalized_profiles":[],"raw_profiles":[shadow]
    })
    return fmt


def venue_row(profile,raw,today):
    fmt=validate_format(profile)
    record,reason,fingerprint=candidate_record(profile,raw,today=today)
    if record is None:
        return None,reason,None
    if fmt.get("title_case_name") is True:
        record["nome"]=_title(record["nome"])
    if fmt.get("title_case_address") is True:
        record["indirizzo"]=_title(record["indirizzo"])
    if fmt.get("address_suffix_name_prefix"):
        name=str(raw.get(profile["name_field"]) or "").strip()
        prefix=fmt["address_suffix_name_prefix"]
        if not name.startswith(prefix) or not name.removeprefix(prefix).strip():
            return None,"invalid_source_row",None
        locality=_title(name.removeprefix(prefix))
        record["indirizzo"]+=", "+locality
    # Explicit rules are weekly predictions only. A source event is not
    # confirmed and does not get a precise map point from this transformer.
    if (record.get("verificato_il") or record.get("date") or
            record.get("date_quality")!="sconosciuta" or
            record.get("status")!="non_confermato" or
            record.get("lat") is not None or record.get("lng") is not None):
        raise ValueError("Declarative stage accidentally verified or geocoded a venue")
    if set(record)-SAFE_PREVIEW:
        raise ValueError("New source record introduced unreviewed output columns")
    return record,reason,fingerprint


def _location(value):
    """Normalize locality suffix conservatively; NEVER geocode it."""
    value=canonical(value)
    return re.sub(r"^(?:via|viale|piazza|piazzale|largo|corso)\s+","",value)


def _tokens(value):
    return [x for x in canonical(value).split()
            if x not in {"mercato","mercatino","settimanale","comunale",
                         "di","a","del","della","dei","delle","il","la","al","in"}]


def _review_reason(record, prior, candidate_day):
    # A source with no reliable street/day or a generic city listing cannot
    # automatically disambiguate a new venue from a legacy public calendar.
    if (canonical(prior.get("citta"))!=canonical(record.get("citta"))
            or canonical(prior.get("regione"))!=canonical(record.get("regione"))):
        return None
    previous_days=weekday_evidence(prior)
    if candidate_day is not None and previous_days is not None:
        if candidate_day not in previous_days:
            return None
    # Unknown calendar is *more* ambiguous, never evidence of a distinct day.
    old_place=_location(prior.get("indirizzo"))
    new_place=_location(record.get("indirizzo"))
    if old_place and new_place and old_place==new_place:
        return "venue_at_same_street_day"
    old_name=_tokens(prior.get("nome"))
    new_name=_tokens(record.get("nome"))
    if old_name and new_name and old_name==new_name:
        return "same_named_market_in_city"
    city=_tokens(prior.get("citta"))
    # A generic old listing at municipality level with no street can mask an
    # established market on the same day. Flag, do not silently create an ID.
    if not old_place and city and old_name==city:
        return "generic_city_market_day"
    return None


def _validate_existing(base):
    if not isinstance(base,list) or not 1<=len(base)<=100000:
        raise ValueError("Invalid complete baseline market dataset")
    seen=set()
    for record in base:
        if not isinstance(record,dict):
            raise ValueError("Malformed existing market")
        sid=record.get("slug")
        if not isinstance(sid,str) or not sid or sid in seen:
            raise ValueError("Repeated original market identity")
        seen.add(sid)
    return {r["slug"]:r for r in base}


def stage(profile,raw_blob,base,*,today,observed_source_sha256=None):
    """Create a complete ephemeral candidate set, but never modify baseline."""
    if not isinstance(today,date):
        raise ValueError("Need publisher-local reference date")
    fmt=validate_format(profile)
    old=_validate_existing(base)
    source=parse_rows(profile,raw_blob)
    if len(source)>MAX_STAGING_SOURCE_ROWS:
        raise ValueError("Source too large for safe staging")
    observed=hashlib.sha256(raw_blob).hexdigest()
    if observed_source_sha256 is not None and observed!=observed_source_sha256:
        raise ValueError("Source snapshot was modified after it was reviewed")
    source_rows=[]
    id_counts=Counter()
    counters=Counter()
    examples=[]
    reasons=Counter()
    for item in source:
        counters["raw_rows_scanned"]+=1
        record,issue,fingerprint=venue_row(profile,item,today)
        if record is None:
            reasons[issue or "invalid_source_row"]+=1
            continue
        id_counts[record["slug"]]+=1
        source_rows.append((record,issue,item))
    candidates=[]
    seen=set()
    by_city=defaultdict(list)
    for prior in base:
        by_city[(canonical(prior.get("regione")),canonical(prior.get("citta")))].append(prior)
    for record,issue,item in source_rows:
        sid=record["slug"]
        if sid in seen:
            continue
        seen.add(sid)
        if id_counts[sid]!=1:
            reasons["duplicate_publisher_identity"]+=id_counts[sid]
            continue
        counters["source_market_identities"]+=1
        if issue:
            counters["informational_"+issue]+=1
        prior=old.get(sid)
        if prior is not None:
            counters["already_in_catalog_exact_source_id"]+=1
            # Changed venue identity under same slug is not automatically
            # overwritten, even if the source has a newer HTTP timestamp.
            for field in ("citta","regione","provincia","indirizzo"):
                if (canonical(prior.get(field))!=canonical(record.get(field))):
                    reasons["source_identity_changed"]+=1
                    break
            continue
        day=source_weekday(item.get(profile["weekday_field"]))
        cohort=by_city[(canonical(record.get("regione")),canonical(record.get("citta")))]
        collision=next((reason for r in cohort
                        if (reason:=_review_reason(record,r,day))),None)
        if collision:
            reasons[collision]+=1
            if len(examples)<REPORT_EXAMPLES:
                examples.append({
                    "source_identity_sha256":digest({"source":profile["id"],"id":sid}),
                    "review_reason":collision,"new_market_created":False,
                })
            continue
        counters["source_only_unambiguous_candidate_not_verified_event"]+=1
        candidates.append(record)
    # A secondary consumer cannot confuse a partial source response with a
    # market closure; the complete original ID set is always kept.
    source_facts={
        "schema":1,"source_id":profile["id"],"publisher":profile["publisher"],
        "source_url":profile["resource_url"],"publisher_dataset_date":profile["source_dataset_date"],
        "source_snapshot_sha256":observed,
        "profile_sha256":digest(profile),
        "base_catalog_records":len(base),
        "source_kind":profile["row_kind"],
        "counts":dict(sorted(counters.items())),
        "review_reason_counts":dict(sorted(reasons.items())),
        "safe_candidates_not_published":len(candidates),
        "examples_hashed":examples,
        "existing_market_identities_deleted":0,
        "existing_market_ids_modified":0,
        "verified_openings_created":0,
        "precise_coordinates_created":0,
        "directions_enabled":0,
        "publication_enabled":False,
        "source_license_automatically_verified":False,
        "source_schema_readonly":True,
    }
    return candidates,source_facts


def authorize(profile,source_report,admission,*,today):
    """Approve *a publisher source contract*, not each row individually.

    Admission must be recorded after independent rights and source ID review.
    A boolean 'licensed' alone is NOT sufficient; a reviewed attestation
    digests the exact approved source contract. There are no active licenses
    or publisher authorizations in the default repository.
    """
    if not isinstance(admission,dict) or admission.get("mode")!="approved_dev_only":
        raise ValueError("Source has no reviewed DEV admission certificate")
    if (profile.get("publication_mode")!="approved_dev_only"
            or profile.get("legal_reuse_reviewed") is not True
            or source_report.get("profile_sha256") != digest(profile)):
        raise ValueError("Source has no licensed, pinned DEV import contract")
    expected_keys={
       "schema","mode","source_id","reviewed_profile_sha256",
       "publisher_license_evidence_url","identity_granularity",
       "reviewed_on","max_new_ids","source_record_kind",
       "source_specific_geo_approval",
    }
    if set(admission)!=expected_keys:
        raise ValueError("A field is missing in the source approval attestation")
    from urllib.parse import urlsplit
    from source_lifecycle import _public_https
    license_url=admission.get("publisher_license_evidence_url")
    host=urlsplit(str(license_url)).hostname
    source_host=urlsplit(profile["resource_url"]).hostname
    if (admission.get("schema")!=1
            or admission.get("source_id")!=profile["id"]
            or admission.get("reviewed_profile_sha256")!=digest(profile)
            or admission.get("identity_granularity")!=profile["row_kind"]
            or admission.get("source_record_kind")!=profile["row_kind"]
            or not isinstance(license_url,str) or not _public_https(license_url)
            or host not in {source_host, urlsplit(profile["attribution_url"]).hostname}
            or admission.get("source_specific_geo_approval") is not False
            or type(admission.get("max_new_ids")) is not int
            or not 0<admission["max_new_ids"]<=MAX_PROFILE_MAX_NEW
            or admission["max_new_ids"]>profile.get("max_new_ids_per_run",0)):
        raise ValueError("Source DEV approval lacks independently reviewed rights/identity policy")
    reviewed=date.fromisoformat(admission["reviewed_on"])
    if not date(2025,1,1)<=reviewed<=today:
        raise ValueError("Source admission attestation has invalid review date")
    date_of_data=date.fromisoformat(profile["source_dataset_date"])
    if (today-date_of_data).days>profile["max_source_age_days"]:
        raise ValueError("Stale publisher source cannot begin unattended DEV admission")
    return True


def apply_approved(profile,blob,existing,admission,*,today):
    candidates,report=stage(profile,blob,existing,today=today)
    authorize(profile,report,admission,today=today)
    # Enforce the reviewed per-run cap by taking a deterministic batch.
    # Remaining eligible IDs stay out of the catalog until the next cycle.
    # Never use mutable publisher row order to select who is admitted.
    ordered=sorted(candidates,key=lambda row:row["slug"])
    admitted=ordered[:admission["max_new_ids"]]
    deferred=ordered[admission["max_new_ids"]:]
    original=_validate_existing(existing)
    if not all(row["slug"] not in original and row["status"]=="non_confermato"
               and not row["verificato_il"] and not row["date"]
               and row["date_quality"]=="sconosciuta"
               and row["lat"] is None and row["lng"] is None for row in candidates):
        raise ValueError("Unsafe source candidate surfaced after approval")
    # Return the original list as-is, with additions only. Caller must still
    # pass the standard static export/diff/mobile QA and never write PROD.
    rows=[*existing,*admitted]
    certificate={
        "schema":1,"publisher_id":profile["id"],
        "admission_certificate_sha256":digest(admission),
        "original_market_records":len(existing),"new_venue_ids":[row["slug"] for row in admitted],
        "source_eligible_candidates":len(ordered),
        "deferred_candidate_count":len(deferred),
        "deferred_candidate_ids_sha256":digest([row["slug"] for row in deferred]),
        "catalog_records_after":len(rows),
        "old_ids_removed":0,"old_ids_modified":0,
        "verified_events_created":0,
        "geocoordinates_created":0,"new_directions_enabled":0,
        "required_release_checks":["source_diff","static_export","duplicate_review",
                                   "mobile_navigation","security_no_billed_runtime"],
        "dev_only":True,
    }
    return rows,certificate
