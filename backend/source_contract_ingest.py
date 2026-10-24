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

from catalog_quality_report import VAGUE_ADDRESSES, key as addr_key
from lombardia_overlap import weekday_evidence
from source_lifecycle import (
    parse_rows, candidate_record, canonical, digest, validate_contracts,
    weekday as source_weekday,
)
from field_evidence import (
    FIELDS, MAX_READ_AGE, as_day, clean_receipts, fingerprint as evidence_fingerprint,
    make_receipt, managed_update_allowed, mark_managed_fields, valid_receipt,
    retire_superseded_receipts,
)
from publisher_snapshot_date import resolve_source_date
from source_freshness import source_date_evidence

MAX_STAGING_SOURCE_ROWS = 3000
MAX_PROFILE_MAX_NEW = 250
REPORT_EXAMPLES = 12
FIELD_MANAGER = "source_contract_ingest"
IDENTITY_FIELDS = ("nome", "citta", "regione", "provincia")
FIELD_REVIEW_REASONS = {
    "indirizzo": "source_address_changed",
    "ricorrenza_testo": "source_calendar_changed",
    "orario_testo": "source_hours_changed",
}
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


class PublishedSourceDriftError(ValueError):
    """A source identity or a field without managed provenance has changed."""

    def __init__(self, message, *, source_report=None):
        super().__init__(message)
        self.source_report = source_report or {}
        self.retirements = []


def _title(text):
    return str(text or "").strip().title()


def validate_format(profile):
    """Validate only deliberately supported declarative presentation options."""
    if not isinstance(profile,dict):
        raise ValueError("Missing source profile")
    fmt=profile.get("presentation",{})
    if not isinstance(fmt,dict) or set(fmt)-{"title_case_name","title_case_address",
                                             "address_suffix_name_prefix","name_prefix"}:
        raise ValueError("Unapproved presentation mapping keys")
    if fmt.get("title_case_name",False) not in (True,False):
        raise ValueError("Invalid name presentation policy")
    if fmt.get("title_case_address",False) not in (True,False):
        raise ValueError("Invalid address presentation policy")
    suffix=fmt.get("address_suffix_name_prefix")
    if suffix is not None and (not isinstance(suffix,str) or not 3<=len(suffix)<=100):
        raise ValueError("Missing approved source locality prefix")
    prefix=fmt.get("name_prefix")
    if prefix is not None and (not isinstance(prefix,str) or
                              not 2<=len(prefix.strip())<=30 or
                              not prefix.endswith(" ")):
        raise ValueError("Unreviewed presentation name prefix")
    if profile.get("row_kind") not in ("market_venue","market_venue_day"):
        raise ValueError("Administrative concessions/statistics cannot be admitted as markets")
    # Validate extraction separately from the reviewed release certificate.
    shadow=copy.deepcopy(profile)
    shadow["publication_mode"]="shadow_only"
    shadow["legal_reuse_reviewed"]=False
    shadow["max_new_ids_per_run"]=0
    validate_contracts({
        "schema":1,"publication_role":"review_only",
        "normalized_profiles":[],"raw_profiles":[shadow]
    })
    return fmt


def venue_row(profile,raw,today,*,source_date=None):
    fmt=validate_format(profile)
    record,reason,fingerprint=candidate_record(profile,raw,today=today,source_date=source_date)
    if record is None:
        return None,reason,None
    if fmt.get("title_case_name") is True:
        record["nome"]=_title(record["nome"])
    if fmt.get("name_prefix") and not canonical(record["nome"]).startswith(
            canonical(fmt["name_prefix"])):
        record["nome"]=(fmt["name_prefix"]+record["nome"])[:160]
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
    # "centro" and similar labels name no venue: same as no street.
    if addr_key(value) in VAGUE_ADDRESSES:
        return ""
    value=canonical(value)
    return re.sub(r"^(?:via|viale|piazza|piazzale|largo|corso)\s+","",value)


def _tokens(value):
    return [x for x in canonical(value).split()
            if x not in {"mercato","mercatino","settimanale","comunale",
                         "di","a","del","della","dei","delle","il","la","al","in"}]


def _review_reason(record, prior, candidate_day, *, allow_unlocated_city_summary=False):
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
        # Publisher-proved distinct physical venues need not be blocked by a
        # third-party city-wide page with neither street nor usable weekday.
        # Only contracts pinning a multi-venue threshold can use this exception.
        if allow_unlocated_city_summary and previous_days is None:
            return None
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


def _source_values(record):
    values = {field: record[field] for field, limit in FIELDS.items()
              if isinstance(record.get(field), str) and record[field].strip()
              and len(record[field]) <= limit}
    # A parser fallback describes uncertainty, not a publisher weekday.
    if not values.get("ricorrenza_testo", "").startswith("settimanale - "):
        values.pop("ricorrenza_testo", None)
    return values


def _source_receipt(profile, record, *, read_on, parsed_sha256, source_date, values=None):
    return make_receipt(
        record, values=_source_values(record) if values is None else values,
        source_url=profile["resource_url"],
        source_name=profile["publisher"], source_id=profile["id"],
        source_row=record["slug"], read_on=read_on,
        source_updated_on=source_date, source_sha256=parsed_sha256,
    )


def _source_hours_fill_allowed(profile, prior, receipt, *, today):
    """Fill only missing hours of the same contracted publisher venue.

    The source admission certificate is still required by ``apply_approved``.
    A blank field has no previous managed receipt, so require its existing
    source ID, geography and street to agree with this complete new receipt.
    Existing values retain the stricter managed-update rules.
    """
    current=prior.get("orario_testo")
    if (not (current is None or (isinstance(current,str) and not current.strip()))
            or prior.get("verificato_il") or not isinstance(receipt,dict)
            or not isinstance(today,date)):
        return False
    values=receipt.get("valori")
    read=as_day(receipt.get("letto_il"))
    if (not isinstance(values,dict) or not values.get("orario_testo")
            or not read or not 0<=(today-read).days<=MAX_READ_AGE
            or not canonical(prior.get("indirizzo"))
            or canonical(values.get("indirizzo"))!=canonical(prior.get("indirizzo"))
            or any(canonical(prior.get(field))!=canonical(profile.get(setting))
                   for field,setting in (("citta","municipality"),
                                         ("provincia","province"),("regione","region")))
            or not str(prior.get("slug") or "").startswith(profile["catalog_slug_prefix"])
            or prior.get("url_fonte")!=profile["attribution_url"]
            or receipt.get("riga_fonte")!=prior.get("slug")
            or receipt.get("fonte_id")!=profile["id"]
            or receipt.get("fonte")!=profile["publisher"]
            or receipt.get("url")!=profile["resource_url"]
            or receipt.get("ambito")!="dataset"
            or receipt.get("metodo")!="id_fonte"
            or receipt.get("impronta_tipo")!="publisher_parsed_json"):
        return False
    previous=[r for r in clean_receipts(prior.get("riscontri_campi"),prior,today=today)
              if all(r.get(k)==receipt.get(k) for k in (
                  "fonte_id","url","riga_fonte","metodo","ambito"))
              and r.get("impronta_tipo","publisher_parsed_json")==receipt["impronta_tipo"]]
    source_date=as_day(receipt.get("fonte_aggiornata_il"))
    for observed in previous:
        previous_date=as_day(observed.get("fonte_aggiornata_il"))
        # A previous observation can concern the address alone. It still
        # establishes the source version floor for this same publisher row.
        # Same-day reads have no reliable ordering in the date-only schema.
        if (read<=as_day(observed["letto_il"])
                or (previous_date and (not source_date or source_date<previous_date))):
            return False
    return valid_receipt(receipt,{**prior,**values},today=today)


def _hours_receipt_retained(row, receipt, *, today):
    """The hours actually saved must retain their complete source/ownership proof."""
    keys=("mercato","url","fonte","fonte_id","riga_fonte","letto_il",
          "fonte_aggiornata_il","sha256","impronta_tipo","ambito","metodo")
    return any(all(saved.get(k)==receipt.get(k) for k in keys)
               and all(saved["valori"].get(k)==v for k,v in receipt["valori"].items())
               and "orario_testo" in saved.get("campi_gestiti",[])
               and saved.get("gestore_campi")==FIELD_MANAGER
               for saved in clean_receipts(row.get("riscontri_campi"),row,today=today))


def _observed_row(prior, receipt, changes, *, today):
    result = copy.deepcopy(prior)
    for field, change in changes.items():
        result[field] = change["after"]
    result["riscontri_campi"] = clean_receipts(
        [*(prior.get("riscontri_campi") or []), receipt], result, today=today)
    if ("orario_testo" in changes and
            not _hours_receipt_retained(result,receipt,today=today)):
        raise ValueError("Source hours update lost its complete retained field receipt")
    for key, value in (("fonte_letta_il", receipt["letto_il"]),
                       ("fonte_aggiornata_il", receipt["fonte_aggiornata_il"])):
        # A newer address/hours observation cannot renew an old calendar.
        # Its actual dataset date remains visible in that field's receipt.
        if (key == "fonte_aggiornata_il" and
                ("ricorrenza_testo" not in receipt["valori"] or
                 receipt["valori"]["ricorrenza_testo"] != result.get("ricorrenza_testo"))):
            continue
        if not as_day(result.get(key)) or (as_day(value) and as_day(value) >= as_day(result[key])):
            result[key] = value
    return result


def _retired_row(prior, receipt, *, today):
    result=copy.deepcopy(prior)
    result["riscontri_campi"]=retire_superseded_receipts(prior,receipt,today=today)
    if not as_day(result.get("fonte_letta_il")) or as_day(receipt["letto_il"]) >= as_day(result["fonte_letta_il"]):
        result["fonte_letta_il"]=receipt["letto_il"]
    return result


def source_metadata(record):
    """Pin calendar-relevant provenance, including the export's legacy fallback."""
    result = {key: record.get(key) or "" for key in (
        "aggiornato_il", "fonte_letta_il", "importato_il", "verificato_il")}
    result["aggiornamento_ambito"] = "dataset" if record.get("aggiornamento_ambito") == "dataset" else ""
    result["fonte_aggiornata_il"] = source_date_evidence(record)["value"] or ""
    return result


def _update_proof(prior, receipt, changes, *, today, retire=False):
    result = (_retired_row(prior,receipt,today=today) if retire
              else _observed_row(prior, receipt, changes, today=today))
    return result, {
        "slug": prior["slug"], "changed_fields": changes, "action":"retire" if retire else "observe",
        "before_sha256": evidence_fingerprint(prior),
        "after_sha256": evidence_fingerprint(result), "receipt": receipt,
        "identity_after": {key:result.get(key) for key in ("slug", *IDENTITY_FIELDS)},
        "public_fields_after": {key:result.get(key) for key in FIELDS},
        "source_metadata_after": source_metadata(result),
        "observations_after": result["riscontri_campi"],
        "retired_observations": ([r for r in clean_receipts(prior.get("riscontri_campi"),prior,today=today)
                                  if r not in result["riscontri_campi"]] if retire else []),
    }


def observed_source_date(profile, observations, *, today):
    """Resolve the publisher date from independently bound source observations."""
    observations = observations or {}
    resolved = resolve_source_date(
        profile, proof=observations.get("source_date_proof"),
        snapshot_sha256=observations.get("source_snapshot_sha256"),
        read_on=observations.get("source_read_on"), today=today)
    if observations.get("publisher_dataset_date", resolved) != resolved:
        raise ValueError("Publisher dataset date differs from the observed snapshot proof")
    return resolved


def verify_update(profile, prior, result, proof, *, today, source_observations=None):
    """Rebuild the exact permitted field/observation diff from prior evidence."""
    source_date = observed_source_date(profile, source_observations, today=today)
    if (not isinstance(proof, dict) or set(proof) != {
            "slug", "changed_fields", "before_sha256", "after_sha256", "receipt",
            "identity_after", "observations_after", "action", "retired_observations", "public_fields_after",
            "source_metadata_after"}
            or proof.get("slug") != prior.get("slug")
            or proof.get("before_sha256") != evidence_fingerprint(prior)
            or proof.get("after_sha256") != evidence_fingerprint(result)
            or prior.get("url_fonte") != profile["attribution_url"]):
        raise ValueError("Independent generic source field proof differs from original record")
    changes, receipt = proof["changed_fields"], proof["receipt"]
    retire=proof.get("action")=="retire"
    target = ({**prior, **receipt.get("valori",{})} if retire and isinstance(receipt,dict) else result)
    if (not isinstance(changes, dict) or set(changes) - set(FIELDS)
            or proof.get("action") not in {"retire","observe"}
            or (retire and changes)
            or not isinstance(receipt, dict) or not valid_receipt(receipt, target, today=today)
            or receipt.get("fonte_id") != profile["id"]
            or receipt.get("fonte") != profile["publisher"]
            or receipt.get("url") != profile["resource_url"]
            or receipt.get("riga_fonte") != prior["slug"]
            or receipt.get("fonte_aggiornata_il") != source_date
            or (source_observations is not None and (
                receipt.get("sha256") != source_observations.get("source_parsed_sha256")
                or receipt.get("letto_il") != source_observations.get("source_read_on")))
            or receipt.get("ambito") != "dataset" or receipt.get("metodo") != "id_fonte"
            or receipt.get("impronta_tipo") != "publisher_parsed_json"):
        raise ValueError("Independent generic source receipt is not source-bound")
    plain = {k: copy.deepcopy(v) for k, v in receipt.items()
             if k not in {"campi_gestiti", "gestore_campi", "versioni_precedenti"}}
    for field, change in changes.items():
        if (not isinstance(change, dict) or set(change) != {"before", "after"}
                or change["before"] != prior.get(field)
                or change["after"] != receipt["valori"].get(field)
                or not (managed_update_allowed(prior, plain, field,
                                                manager=FIELD_MANAGER, today=today)
                        or (field=="orario_testo" and
                            _source_hours_fill_allowed(profile,prior,plain,today=today)))
                or (field == "indirizzo" and
                    (prior.get("lat") is not None or prior.get("lng") is not None))):
            raise ValueError("Independent generic source update lacks previous field ownership")
    expected_receipt = (mark_managed_fields(plain, changes, manager=FIELD_MANAGER, previous=prior)
                        if changes else plain)
    if receipt != expected_receipt:
        raise ValueError("Independent generic source receipt claims unassigned field ownership")
    expected = (_retired_row(prior,expected_receipt,today=today) if retire
                else _observed_row(prior, expected_receipt, changes, today=today))
    retired = ([r for r in clean_receipts(prior.get("riscontri_campi"),prior,today=today)
                if r not in expected.get("riscontri_campi",[])] if retire else [])
    if (expected != result
            or (retire and not retired)
            or proof["retired_observations"]!=retired
            or proof["identity_after"] != {key:result.get(key) for key in ("slug", *IDENTITY_FIELDS)}
            or proof["public_fields_after"] != {key:result.get(key) for key in FIELDS}
            or proof["source_metadata_after"] != source_metadata(result)
            or proof["observations_after"] != result.get("riscontri_campi")):
        raise ValueError("Independent generic source import changed an unapproved field")
    return len(changes)


def _stage(profile,raw_blob,base,*,today,observed_source_sha256=None,read_on=None,
           source_date_proof=None):
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
    read_on = str(read_on or today)
    if not as_day(read_on) or as_day(read_on) > today:
        raise ValueError("Source read date is invalid or later than the reference date")
    source_date = resolve_source_date(profile, proof=source_date_proof, blob=raw_blob,
                                      read_on=read_on, today=today)
    parsed_sha256 = evidence_fingerprint(sorted(source, key=digest))
    source_rows=[]
    id_counts=Counter()
    counters=Counter()
    examples=[]
    reasons=Counter()
    updates=[]
    retirements=[]
    field_audit=Counter()
    for item in source:
        counters["raw_rows_scanned"]+=1
        record,issue,fingerprint=venue_row(profile,item,today,source_date=source_date)
        if record is None:
            reasons[issue or "invalid_source_row"]+=1
            continue
        id_counts[record["slug"]]+=1
        source_rows.append((record,issue,item))
    candidates=[]
    seen=set()
    venue_fields=profile.get("venue_identity_fields",[])
    physical=Counter(tuple(canonical(item.get(field)) for field in venue_fields)
                     for _,_,item in source_rows) if venue_fields else Counter()
    # Same displayed market at one address may be several weekday rows or
    # different market categories. Preserve every source ID, but quarantine
    # all members until a reviewed source-level venue/day grouping exists.
    display_places=Counter((canonical(record['nome']),canonical(record['indirizzo']))
                           for record,_,_ in source_rows) if venue_fields else Counter()
    address_count=len({canonical(record["indirizzo"]) for record,_,_ in source_rows
                       if canonical(record["indirizzo"])})
    floor=profile.get("generic_city_aggregate_min_distinct_addresses",0)
    allow_city_summary=bool(floor and address_count>=floor)
    counters["publisher_distinct_address_count"]=address_count
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
        if (venue_fields and physical[tuple(canonical(item.get(f)) for f in venue_fields)]>1):
            reasons["repeated_venue_rows_require_grouping"]+=1
            continue
        if (venue_fields and display_places[(canonical(record['nome']),
                                             canonical(record['indirizzo']))]>1):
            reasons["same_place_name_multiple_source_rows"]+=1
            continue
        if any(canonical(token) in canonical(record["indirizzo"])
               for token in profile.get("hold_address_contains",[])):
            reasons["temporary_location_unreconciled"]+=1
            continue
        counters["source_market_identities"]+=1
        if issue:
            counters["informational_"+issue]+=1
        prior=old.get(sid)
        if prior is not None:
            counters["already_in_catalog_exact_source_id"]+=1
            if any(canonical(prior.get(field))!=canonical(record.get(field))
                   for field in IDENTITY_FIELDS) or prior.get("url_fonte") != profile["attribution_url"]:
                reasons["source_identity_changed"]+=1
                continue
            # Matching identity permits observations. Replacing an existing
            # value additionally requires its exact previous owned receipt.
            values = _source_values(record)
            # Preserve the existing display spelling when the contracted
            # normalization agrees (for example lunedì / lunedi).
            # Hours can include closure lists/ranges: punctuation is evidence,
            # so "1, 5 gennaio" must never compare equal to "1-5 gennaio".
            values = {field: prior[field] if field!="orario_testo"
                      and isinstance(prior.get(field), str)
                      and canonical(prior[field]) == canonical(value) else value
                      for field, value in values.items()}
            target = {**prior, **values}
            receipt = _source_receipt(profile, target, read_on=read_on,
                                      parsed_sha256=parsed_sha256, source_date=source_date, values=values)
            changes = {}
            held = False
            for field in FIELDS:
                incoming = receipt["valori"].get(field)
                if incoming is None:
                    field_audit[field + ":source_value_unavailable"] += 1
                elif prior.get(field) == incoming:
                    field_audit[field + ":observed_identical"] += 1
                elif ((managed_update_allowed(prior, receipt, field,
                                               manager=FIELD_MANAGER, today=today)
                       or (field=="orario_testo" and
                           _source_hours_fill_allowed(profile,prior,receipt,today=today)))
                      and not (field == "indirizzo" and
                               (prior.get("lat") is not None or prior.get("lng") is not None))):
                    changes[field] = {"before": prior.get(field), "after": incoming}
                    field_audit[field + ":managed_update_proposed"] += 1
                else:
                    reasons[FIELD_REVIEW_REASONS[field]] += 1
                    field_audit[field + ":review_needed"] += 1
                    held = True
            if held:
                if (retire_superseded_receipts(prior,receipt,today=today) !=
                        clean_receipts(prior.get("riscontri_campi"),prior,today=today)):
                    retired,proof=_update_proof(prior,receipt,{},today=today,retire=True)
                    retirements.append((retired,proof))
                continue
            if changes:
                receipt = mark_managed_fields(receipt, changes,
                                               manager=FIELD_MANAGER, previous=prior)
            result, proof = _update_proof(prior, receipt, changes, today=today)
            if result != prior:
                updates.append((result, proof))
            continue
        day=source_weekday(item.get(profile["weekday_field"]))
        cohort=by_city[(canonical(record.get("regione")),canonical(record.get("citta")))]
        collision=next((reason for r in cohort
                        if (reason:=_review_reason(
                            record,r,day,allow_unlocated_city_summary=allow_city_summary))),None)
        if collision:
            reasons[collision]+=1
            if len(examples)<REPORT_EXAMPLES:
                examples.append({
                    "source_identity_sha256":digest({"source":profile["id"],"id":sid}),
                    "review_reason":collision,"new_market_created":False,
                })
            continue
        counters["source_only_unambiguous_candidate_not_verified_event"]+=1
        receipt = _source_receipt(profile, record, read_on=read_on,
                                  parsed_sha256=parsed_sha256, source_date=source_date)
        record["riscontri_campi"] = [mark_managed_fields(
            receipt, receipt["valori"], manager=FIELD_MANAGER)]
        record["importato_il"] = read_on
        record["fonte_letta_il"] = read_on
        record["fonte_aggiornata_il"] = source_date
        for field in FIELDS:
            field_audit[field + (":new_source_value" if field in receipt["valori"]
                                else ":source_value_unavailable")] += 1
        candidates.append(record)
    for prior in base:
        if (prior["slug"].startswith(profile["catalog_slug_prefix"])
                and prior.get("url_fonte") == profile["attribution_url"]
                and prior["slug"] not in id_counts):
            reasons["source_identity_missing_or_changed"] += 1
    # A secondary consumer cannot confuse a partial source response with a
    # market closure; the complete original ID set is always kept.
    source_facts={
        "schema":1,"source_id":profile["id"],"publisher":profile["publisher"],
        "source_url":profile["resource_url"],"publisher_dataset_date":source_date,
        "source_snapshot_sha256":observed,
        "source_parsed_sha256":parsed_sha256,"source_read_on":read_on,
        "profile_sha256":digest(profile),
        "base_catalog_records":len(base),
        "source_kind":profile["row_kind"],
        "counts":dict(sorted(counters.items())),
        "review_reason_counts":dict(sorted(reasons.items())),
        "field_audit_counts":dict(sorted(field_audit.items())),
        "managed_fields_proposed":sum(len(proof["changed_fields"]) for _,proof in updates),
        "evidence_refreshes_proposed":len(updates),
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
    if source_date_proof is not None:
        source_facts["source_date_proof"] = copy.deepcopy(source_date_proof)
    return candidates,source_facts,updates,retirements


def stage(profile,raw_blob,base,*,today,observed_source_sha256=None,read_on=None,
          source_date_proof=None):
    candidates, report, _, _ = _stage(profile, raw_blob, base, today=today,
                                   observed_source_sha256=observed_source_sha256, read_on=read_on,
                                   source_date_proof=source_date_proof)
    return candidates, report


def authorize_contract(profile,admission,*,today):
    """Approve *a publisher source contract*, not each row individually.

    Admission must be recorded after independent rights and source ID review.
    A boolean 'licensed' alone is NOT sufficient; a reviewed attestation
    digests the exact approved source contract. Active sources are only those
    present in the versioned contract AND admission registry.
    """
    if not isinstance(admission,dict) or admission.get("mode")!="approved_dev_only":
        raise ValueError("Source has no reviewed DEV admission certificate")
    if (profile.get("publication_mode")!="approved_dev_only"
            or profile.get("legal_reuse_reviewed") is not True):
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
    return True


def authorize(profile,source_report,admission,*,today):
    """Authorize this source observation, after the exact contract and date proof."""
    authorize_contract(profile,admission,today=today)
    if source_report.get("profile_sha256") != digest(profile):
        raise ValueError("Source has no licensed, pinned DEV import contract")
    date_of_data=date.fromisoformat(observed_source_date(profile, source_report, today=today))
    if (today-date_of_data).days>profile["max_source_age_days"]:
        raise ValueError("Stale publisher source cannot begin unattended DEV admission")
    # Unresolved identity or unmanaged-field changes hold this source. Other
    # independently approved sources remain eligible in the activation loop.
    drift=source_report.get("review_reason_counts",{})
    if any(drift.get(reason,0) for reason in (
            "source_identity_changed", "source_identity_missing_or_changed",
            "source_address_changed", "source_calendar_changed", "source_hours_changed")):
        raise PublishedSourceDriftError(
            "Existing publisher identity or unmanaged field changed; review source",
            source_report=source_report,
        )
    return True


def apply_approved(profile,blob,existing,admission,*,today,read_on=None,source_date_proof=None):
    candidates,report,updates,retirements=_stage(
        profile,blob,existing,today=today,read_on=read_on,source_date_proof=source_date_proof)
    try:
        authorize(profile,report,admission,today=today)
    except PublishedSourceDriftError as exc:
        originals=_validate_existing(existing)
        for row,proof in retirements:
            verify_update(profile,originals[row["slug"]],row,proof,today=today,
                          source_observations=report)
        exc.retirements=retirements
        raise
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
    updated = {row["slug"]:row for row,_ in updates}
    for row, proof in updates:
        verify_update(profile, original[row["slug"]], row, proof, today=today,
                      source_observations=report)
    rows=[*(updated.get(row["slug"],row) for row in existing),*admitted]
    certificate={
        "schema":1,"publisher_id":profile["id"],
        "admission_certificate_sha256":digest(admission),
        "original_market_records":len(existing),"new_venue_ids":[row["slug"] for row in admitted],
        "new_venue_evidence":{row["slug"]:{
            "identity":{key:row.get(key) for key in ("slug",*IDENTITY_FIELDS)},
            "fields":{field:row.get(field) for field in FIELDS},
            "receipt":copy.deepcopy(row["riscontri_campi"][0]),
        } for row in admitted},
        "source_eligible_candidates":len(ordered),
        "deferred_candidate_count":len(deferred),
        "deferred_candidate_ids_sha256":digest([row["slug"] for row in deferred]),
        "catalog_records_after":len(rows),
        "old_ids_removed":0,"old_ids_modified":len(updates),
        "old_fields_modified":sum(len(proof["changed_fields"]) for _,proof in updates),
        "updates":[proof for _,proof in updates],
        "source_observations":report,
        "verified_events_created":0,
        "geocoordinates_created":0,"new_directions_enabled":0,
        "required_release_checks":["source_diff","static_export","duplicate_review",
                                   "mobile_navigation","security_no_billed_runtime"],
        "dev_only":True,
    }
    return rows,certificate
