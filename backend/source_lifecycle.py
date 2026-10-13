#!/usr/bin/env python3
"""Source-level, declarative municipal data lifecycle (NO per-market scripts).

A source contract controls schema, row meaning, identity grain, legal state,
age, bounding and parsing. One code path applies to any approved CSV/JSON.
Reading a source is NOT proof of market openings and NEVER imports by itself.

Source-level contract changes require a Git review. The source registry, schema
probe and this process run automatically and produce actionable *exceptions*.
The normal daily catalog pipeline and already approved publisher importers
continue independently.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from merge_catalog import load_existing
from source_dispositions import reconcile as reconcile_reviewed_source_ids
from recurrence_refresh import WEEKDAYS, explicit_rule
from source_probe import limited_fetch, safe_url
from reviewed_city_evidence import NAVIGATION_HOLD

SCHEMA = 1
MAX_RAW_PROFILES = 8
MAX_NORMALIZED_PROFILES = 30
MAX_ROWS = 6000
MAX_PROFILE_BYTES = 65536
MAX_MARKDOWN_EXAMPLES = 10
MARKET_KINDS = frozenset({"market_venue", "market_venue_day"})
OTHER_KINDS = frozenset({"stall", "concession", "historical_capacity", "aggregate"})
WEEKDAYS_NORMAL = ("lunedi","martedi","mercoledi","giovedi",
                   "venerdi","sabato","domenica")
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]*")
ID_RE = re.compile(r"[a-z][a-z0-9-]{3,70}")


def canonical(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(c for c in text if not unicodedata.combining(c)).casefold()
    return re.sub(r"\s+"," ",re.sub(r"[^a-z0-9]+"," ",text)).strip()


def slug_part(value):
    return canonical(value).replace(" ","-")[:100]


def digest(value):
    return hashlib.sha256(json.dumps(
        value,sort_keys=True,ensure_ascii=False,separators=(",",":")
    ).encode("utf-8")).hexdigest()


def _public_https(url):
    try:
        p = urlsplit(str(url))
        return bool(p.scheme == "https" and p.hostname and
                    not p.username and not p.password and
                    p.port in (None,443) and not p.fragment)
    except ValueError:
        return False


def validate_contracts(config):
    if (not isinstance(config,dict) or config.get("schema")!=SCHEMA
            or config.get("publication_role")!="review_only"
            or not isinstance(config.get("normalized_profiles"),list)
            or not isinstance(config.get("raw_profiles"),list)
            or len(config["normalized_profiles"])>MAX_NORMALIZED_PROFILES
            or len(config["raw_profiles"])>MAX_RAW_PROFILES):
        raise ValueError("Unapproved source-level contract registry")
    ids=set()
    for kind, rows in (("normalized",config["normalized_profiles"]),
                       ("raw",config["raw_profiles"])):
        for item in rows:
            if not isinstance(item,dict):
                raise ValueError("Source contract entry is not an object")
            sid=item.get("id")
            if not isinstance(sid,str) or not ID_RE.fullmatch(sid) or sid in ids:
                raise ValueError("Repeated/invalid source contract ID")
            ids.add(sid)
            minimum=item.get("min_records" if kind=="normalized" else "min_rows")
            maximum=item.get("max_records" if kind=="normalized" else "max_rows")
            if (item.get("row_kind") not in MARKET_KINDS|OTHER_KINDS
                    or item.get("publication_mode") not in
                       ("shadow_only","existing_adapter_only")
                    or not isinstance(item.get("publisher"),str)
                    or not item["publisher"] or
                    type(minimum) is not int or type(maximum) is not int
                    or not 0<=minimum<=maximum<=MAX_ROWS):
                raise ValueError("Untrusted dataset granularity, bounds or publication policy")
            if kind=="normalized":
                if (item.get("publication_mode")!="existing_adapter_only"
                    or not item.get("identity_prefix")
                    or item.get("region") is None
                    or not isinstance(item.get("source_pages",[]),list)
                    or not isinstance(item.get("source_hosts",[]),list)
                    or not (item.get("source_pages") or item.get("source_hosts"))
                    or any(not _public_https(url) for url in item.get("source_pages",[]))
                    or any(not re.fullmatch(r"[a-z0-9.-]+",host)
                           for host in item.get("source_hosts",[]))
                    or not item.get("source_timestamp_scope")
                    or not isinstance(item.get("expected_precision"),list)):
                    raise ValueError("Unreviewed normalized-source adapter contract")
            else:
                if (item.get("publication_mode")!="shadow_only" or
                        item.get("legal_reuse_reviewed") is not False or
                        item.get("max_new_ids_per_run")!=0 or
                        item.get("coordinates")!="ignored_unless_independently_source_verified" or
                        item.get("source_date_scope")!="dataset_not_per_market" or
                        not safe_url(item.get("resource_url")) or
                        not _public_https(item.get("attribution_url")) or
                        item.get("format") not in ("CSV","JSON") or
                        type(item.get("max_bytes")) is not int or
                        not 100<=item["max_bytes"]<=MAX_PROFILE_BYTES or
                        not isinstance(item.get("schema_columns"),list) or
                        not 1<=len(item["schema_columns"])<=100 or
                        len(set(item["schema_columns"]))!=len(item["schema_columns"]) or
                        not isinstance(item.get("identity_fields"),list) or
                        not 1<=len(item["identity_fields"])<=4 or
                        not set(item["identity_fields"]).issubset(item["schema_columns"]) or
                        item.get("catalog_slug_prefix") is None or
                        item.get("municipality") is None or
                        item.get("region") is None or
                        not isinstance(item.get("source_dataset_date"),str) or
                        type(item.get("max_source_age_days")) is not int or
                        not 0<=item["max_source_age_days"]<=730):
                    raise ValueError("Raw source cannot be approved without schema/rights review")
                date.fromisoformat(item["source_dataset_date"])
                for name in ("name_field","weekday_field"):
                    if item.get(name) not in item["schema_columns"]:
                        raise ValueError("Market source field missing from inspected schema")
                for field in item.get("street_fields",[])+item.get("hours_fields",[]):
                    if field not in item["schema_columns"]:
                        raise ValueError("Source address/hour mapping not in reviewed schema")
                if len(item.get("hours_fields",[])) not in (0,2):
                    raise ValueError("Half a time range cannot be treated as hours")
                if (item.get("format")=="CSV" and item.get("delimiter") not in (",",";","\t")):
                    raise ValueError("Unsafe CSV delimiter")
                if item.get("row_kind") not in MARKET_KINDS and item.get("market_filter"):
                    raise ValueError("Administrative/statistical source is not a visitable market")
                filt=item.get("market_filter") or {}
                if filt and (filt.get("field") not in item["schema_columns"] or
                             not isinstance(filt.get("starts_with"),str) or
                             not filt["starts_with"]):
                    raise ValueError("Unreviewed raw source venue filter")
                # An unreviewed file can't invent a verified venue GPS point.
                if item.get("row_kind")=="market_venue_day" and item["weekday_field"] not in item["identity_fields"]:
                    raise ValueError("Multiple weekday records need weekday in stable identity")
                if not SLUG_RE.fullmatch(item["catalog_slug_prefix"]+"a"):
                    raise ValueError("Unapproved source-specific stable ID prefix")
    return config


def parse_rows(profile,blob):
    if (not isinstance(blob,bytes) or not blob or
            len(blob)>profile["max_bytes"]):
        raise ValueError("Full publisher file exceeds exact bounded size")
    try:
        decoded=blob.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise ValueError("Invalid publisher text encoding") from exc
    if profile["format"]=="CSV":
        r=csv.DictReader(io.StringIO(decoded),delimiter=profile["delimiter"])
        fields=list(r.fieldnames or [])
        if (profile.get("strict_schema") is True and
            (len(fields)!=len(profile["schema_columns"]) or
             set(fields)!=set(profile["schema_columns"]))):
            raise ValueError("Publisher changed CSV columns: require a reviewed contract update")
        if any(not f or f not in profile["schema_columns"] for f in fields):
            raise ValueError("Missing/extra CSV schema fields")
        rows=list(r)
        if any(None in row or any(v is None for v in row.values()) for row in rows):
            raise ValueError("Truncated or malformed publisher CSV row")
    else:
        raw=json.loads(decoded)
        if isinstance(raw,dict):
            raw=raw.get("records")
        if not isinstance(raw,list) or not all(isinstance(x,dict) for x in raw):
            raise ValueError("JSON publisher snapshot has no real venue records")
        rows=raw
        if any(set(row)!=set(profile["schema_columns"]) for row in rows):
            raise ValueError("Publisher changed JSON object schema")
    if not profile["min_rows"]<=len(rows)<=profile["max_rows"]:
        raise ValueError("Incomplete/expanded publisher snapshot outside source contract")
    return rows


def weekday(value):
    normalized=canonical(value)
    if normalized in WEEKDAYS_NORMAL:
        return WEEKDAYS_NORMAL.index(normalized)
    return None


def parse_hour(value):
    raw=str(value or "").strip()
    if re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d",raw):
        return raw
    return None


def candidate_record(profile,row,*,today):
    """In-memory conservative source candidate; NEVER marks a market verified."""
    if profile["row_kind"] not in MARKET_KINDS:
        return None,None,None
    filter_rule=profile.get("market_filter") or {}
    if filter_rule and not str(row.get(filter_rule["field"]) or "").startswith(filter_rule["starts_with"]):
        return None,"not_a_market_venue",None
    identity=[canonical(row.get(col)) for col in profile["identity_fields"]]
    name=str(row.get(profile["name_field"]) or "").strip()
    road=" ".join(str(row.get(col) or "").strip() for col in profile.get("street_fields",[])).strip()
    if (not all(identity) or not name or not road or
            len(name)>160 or len(road)>240):
        return None,"incomplete_venue_identity",None
    if len(profile["identity_fields"])==1:
        slug=profile["catalog_slug_prefix"]+slug_part(row[profile["identity_fields"][0]])
    else:
        slug=profile["catalog_slug_prefix"]+digest(identity)[:18]
    if not SLUG_RE.fullmatch(slug):
        return None,"bad_publisher_identity",None
    d=weekday(row.get(profile["weekday_field"]))
    start,end=(None,None)
    if profile.get("hours_fields"):
        a,b=profile["hours_fields"]
        start,end=parse_hour(row.get(a)),parse_hour(row.get(b))
        if start and end and start>=end:start=end=None
    updated=date.fromisoformat(profile["source_dataset_date"])
    age=(today-updated).days
    if age < 0:
        return None,"dataset_date_in_future",None
    forecast_eligible=(d is not None and age<=profile["max_source_age_days"])
    recurrence="settimanale - "+WEEKDAYS[d] if forecast_eligible else "Calendario da verificare"
    venue={
        "slug":slug,"nome":name[:160],
        "citta":profile["municipality"],"provincia":profile["province"],
        "regione":profile["region"],"indirizzo":road,
        "lat":None,"lng":None,"position_quality":"sconosciuta",
        "navigazione_sospesa_motivo":NAVIGATION_HOLD,
        "categoria":"misto","tags":["mercato comunale"],"status":"non_confermato",
        "date":[],"date_quality":"sconosciuta",
        "ricorrenza_testo":recurrence,
        "orario_testo":(start+"–"+end+" (da verificare con il Comune)") if start and end else "",
        "descrizione":(
          "Sede in un dataset comunale, non apertura confermata. "
          "Data riferita all'intero dataset: "+updated.isoformat()+
          ". Coordinate e percorso stradale non verificati."
        ),
        "fonte":profile["publisher"]+" — dati ufficiali, licenza da verificare",
        "url_fonte":profile["attribution_url"],
        "aggiornato_il":updated.isoformat(),"aggiornamento_ambito":"dataset",
        "verificato_il":"","confidence":0,
    }
    facthash=digest({"name":canonical(name),"address":canonical(road),
                     "day":d,"start":start,"end":end,
                     "publisher_dataset_date":updated.isoformat()})
    issue="schedule_unknown" if d is None else (
        "source_old_no_future_forecast" if not forecast_eligible else None)
    if profile.get("hours_fields") and not (start and end):
        issue=issue or "hours_missing_or_invalid"
    return venue,issue,facthash


def _baseline(catalog):
    if not isinstance(catalog,list) or not 1<=len(catalog)<=100000:
        raise ValueError("Invalid original market catalog for source reconciliation")
    by_slug={}
    places={}
    for x in catalog:
        sid=x.get("slug")
        if not isinstance(sid,str) or not sid or sid in by_slug:
            raise ValueError("Untrusted catalog ID set")
        by_slug[sid]=x
        key=(canonical(x.get("regione")),canonical(x.get("citta")),
             canonical(x.get("indirizzo")))
        if key[-1]:places.setdefault(key,[]).append(sid)
    return by_slug,places


def inspect_raw(profile,blob,catalog,previous=None,today=None):
    today=today or date.today()
    rows=parse_rows(profile,blob)
    prior=previous or {}
    if prior and (prior.get("schema")!=1 or
                  prior.get("source_id")!=profile["id"] or
                  prior.get("source_url")!=profile["resource_url"]):
        raise ValueError("History belongs to another source; refuse comparison")
    old_ids,places=_baseline(catalog)
    hashes={}
    counts=Counter()
    preview=[]
    distinct_names=set()
    accepted_ids=set()
    for row in rows:
        counts["rows_observed"]+=1
        if profile["row_kind"] in OTHER_KINDS:
            counts["non_venue_administrative_rows"]+=1
            continue
        venue,reason,fingerprint=candidate_record(profile,row,today=today)
        if venue is None:
            counts[reason]+=1
            continue
        key=venue["slug"]
        if key in accepted_ids:
            counts["duplicate_publisher_market_identity"]+=1
            # A duplicate name may mean several concessions or several
            # physical venues. NEVER merge them by row number or overwrite.
            continue
        accepted_ids.add(key)
        distinct_names.add(canonical(venue["nome"]))
        ident=digest({"publisher":profile["id"],"stable_slug":key})
        hashes[ident]=fingerprint
        counts["distinct_market_identities"]+=1
        if reason:counts["needs_review_"+reason]+=1
        if key in old_ids:
            counts["already_in_catalog_exact_source_id"]+=1
        else:
            counts["identity_not_in_existing_catalog"]+=1
            vk=(canonical(venue["regione"]),canonical(venue["citta"]),
                canonical(venue["indirizzo"]))
            if places.get(vk):
                counts["possible_same_street_other_publisher"]+=1
            if len(preview)<MAX_MARKDOWN_EXAMPLES:
                preview.append({"stable_identity_hash":ident[:16],
                                "review_state":"possible_existing_venue"
                                if places.get(vk) else "source_level_new_candidate",
                                "publication_permission":"none"})
        # A source-level review must never change status, opening verification
        # or geographic coordinates; only a signed DEV importer can do so.
    if counts["duplicate_publisher_market_identity"]:
        counts["rejected_identity_collisions"]=counts["duplicate_publisher_market_identity"]
    before=prior.get("fingerprints",{}) if prior else {}
    if not isinstance(before,dict):
        raise ValueError("Prior source identity hashes malformed")
    current=set(hashes);older=set(before)
    # Missing source rows are not closures; old catalogue entries remain.
    diff={
        "first_observation":not bool(prior),
        "added_source_identities_since_last_scan":len(current-older) if prior else 0,
        "missing_source_identities_since_last_scan":len(older-current) if prior else 0,
        "changed_source_identities_since_last_scan":sum(
           before[key]!=hashes[key] for key in current&older
        ) if prior else 0,
        "same_source_identities_since_last_scan":sum(
           before[key]==hashes[key] for key in current&older
        ) if prior else 0,
    }
    age=(today-date.fromisoformat(profile["source_dataset_date"])).days
    report={
        "schema":1,"source_id":profile["id"],"publisher":profile["publisher"],
        "source_url":profile["resource_url"],"publisher_dataset_date":profile["source_dataset_date"],
        "publisher_data_age_days":age,
        "source_data_scope":profile["source_date_scope"],
        "license_reviewed_for_automatic_publication":False,
        "row_kind":profile["row_kind"],
        "source_snapshot_sha256":hashlib.sha256(blob).hexdigest(),
        "profile_fingerprint":digest(profile),
        "source_schema_columns_sha256":digest(sorted(profile["schema_columns"])),
        "catalog_records_compared":len(catalog),
        "counts":dict(sorted(counts.items())),
        "market_names_distinct_not_new_events":len(distinct_names),
        "fingerprints":dict(sorted(hashes.items())),
        "diff":diff,
        "examples_hashes_only":preview,
        "individual_market_openings_verified":0,
        "catalog_records_imported":0,
        "catalog_records_modified":0,
        "existing_record_ids_deleted":0,
        "new_precise_coordinates":0,
        "new_directions_enabled":0,
        "review_required":True,
        "source_data_marked_current_by_fetch_time":False,
    }
    return report


def inspect_normalized(profile, records, catalog, prior=None, review_metrics=None,
                       reviewed_excluded_ids=None):
    if not isinstance(records,list) or not profile["min_records"]<=len(records)<=profile["max_records"]:
        raise ValueError("Source record counts beyond contract: "+profile["id"])
    by_slug,_=_baseline(catalog)
    seen=set()
    current={}
    counts=Counter()
    for row in records:
        if not isinstance(row,dict):
            raise ValueError("Publisher adapter record not a market object")
        sid=row.get("slug")
        if (not isinstance(sid,str) or not sid.startswith(profile["identity_prefix"])
                or sid in seen or not SLUG_RE.fullmatch(sid)):
            raise ValueError("Source namespace collision or duplicate identity: "+profile["id"])
        seen.add(sid)
        source_url=row.get("url_fonte","")
        hostname=urlsplit(str(source_url)).hostname
        if (not _public_https(source_url) or
            source_url not in profile.get("source_pages",[]) and
            hostname not in profile.get("source_hosts",[]) or
            row.get("regione")!=profile["region"] or
            row.get("date_quality") in ("confermata","riportata") or
            row.get("verificato_il") or
            row.get("status") in ("attivo","annullato","archiviato") or
            row.get("position_quality") not in profile["expected_precision"]):
            raise ValueError("Publisher adapter violated original venue/date/source contract: "+sid)
        counts["source_records_scanned"]+=1
        if sid in by_slug:counts["existing_ids_seen_in_catalog"]+=1
        else: counts["source_ids_not_yet_in_catalog"]+=1
        if row.get("orario_testo"):counts["hours_present"]+=1
        if row.get("indirizzo"):counts["address_present"]+=1
        if row.get("date_quality")=="prevista":counts["forecast_only_not_confirmed"]+=1
        if row.get("lat") is not None:counts["coordinates_not_opening_proof"]+=1
        current[digest({"source":profile["id"],"stable_slug":sid})]=digest({
            "source_id":sid,"name":canonical(row.get("nome")),
            "city":canonical(row.get("citta")),"address":canonical(row.get("indirizzo")),
            "hours":str(row.get("orario_testo") or ""),
            "recurrence":str(row.get("ricorrenza_testo") or ""),
            "dataset_date":str(row.get("aggiornato_il") or "")[:10],
        })
    before=(prior or {}).get("fingerprints",{})
    if before and not isinstance(before,dict):
        raise ValueError("Invalid previous normalized market source state")
    missing=set(before)-set(current)
    screened=review_metrics or {}
    if not isinstance(screened,dict):
        raise ValueError("Untrusted official-source overlap status")
    quarantine=screened.get("quarantined_review",0)
    if (type(quarantine) is not int or quarantine<0
            or quarantine>profile["max_records"]):
        raise ValueError("Untrusted source overlap quarantine count")
    # Counts alone NEVER prove which source IDs an overlap screen held.
    # Exact IDs are ephemeral and come from the reviewed source cohort, not
    # user-provided metadata. Only aggregate counts/digest enter the report.
    source_screening=reconcile_reviewed_source_ids(
        seen,set(by_slug),
        reviewed_excluded_ids=reviewed_excluded_ids,
        reviewed_excluded_count=quarantine,
        reviewed_accepted_count=screened.get("accepted_after_overlap_qa")
        if reviewed_excluded_ids is not None else None,
    )
    return {
        "schema":1,"source_id":profile["id"],"publisher":profile["publisher"],
        "source_data_scope":profile["source_timestamp_scope"],
        "row_kind":profile["row_kind"],
        "profile_fingerprint":digest(profile),
        "catalog_records_compared":len(catalog),
        "counts":dict(sorted(counts.items())),
        "source_screening":source_screening,
        "fingerprints":dict(sorted(current.items())),
        "diff":{
           "first_observation":not bool(prior),
           "new_source_identities_since_last_scan":len(set(current)-set(before)) if prior else 0,
           "missing_source_identities_since_last_scan":len(missing) if prior else 0,
           "changed_existing_identities_since_last_scan":sum(
             current[k]!=before[k] for k in set(current)&set(before)
           ) if prior else 0,
        },
        "vanished_source_ids_do_not_imply_market_closed":True,
        "confirmed_events_created":0,"market_records_imported":0,
        "market_records_edited":0,"market_ids_deleted":0,
    }


def run(config,catalog,*,source_dir=None,previous=None,source_status=None,
        source_dispositions=None,probe_raw=False,stage_raw=False,
        raw_fetch=limited_fetch,today=None):
    today=today or date.today()
    if stage_raw and not probe_raw:
        raise ValueError("Staging requires a complete newly sampled source snapshot")
    validate_contracts(config)
    by_old = (previous or {}).get("sources",{})
    if previous is not None and (
        previous.get("schema")!=1 or previous.get("source_contract_schema")!=1
        or not isinstance(by_old,dict)):
        raise ValueError("Previous source lifecycle report is invalid")
    reports={}
    status=Counter()
    if source_dir is not None:
        root=Path(source_dir)
        for profile in config["normalized_profiles"]:
            sid=profile["id"];cached=root/(sid+".json")
            if not cached.is_file():
                status["source_snapshot_absent_not_market_closure"]+=1
                continue
            rec=json.loads(cached.read_text("utf-8"))
            reports[sid]=inspect_normalized(
                profile,rec,catalog,by_old.get(sid),
                (source_status or {}).get(sid),
                (source_dispositions or {}).get(sid),
            )
            status["existing_adapter_snapshots_inspected"]+=1
    if probe_raw:
        enabled=[p for p in config["raw_profiles"] if p.get("enabled") is True]
        if len(enabled)>2:
            raise ValueError("Unbounded daily raw source probe quota")
        for profile in enabled:
            sid=profile["id"]
            try:
                blob,too_large=raw_fetch(profile["resource_url"])
                if too_large or len(blob)>profile["max_bytes"]:
                    raise ValueError("Publisher file exceeds approved response size")
                reports[sid]=inspect_raw(profile,blob,catalog,by_old.get(sid),today)
                if stage_raw and profile["row_kind"] in MARKET_KINDS:
                    # Reuse the SAME downloaded bytes; never publish candidate
                    # rows and never re-request the source.
                    from source_contract_ingest import stage as stage_source_venues
                    staged,source_stage=stage_source_venues(
                        profile,blob,catalog,today=today,
                        observed_source_sha256=reports[sid]["source_snapshot_sha256"],
                    )
                    if (source_stage.get("existing_market_identities_deleted")!=0
                            or source_stage.get("verified_openings_created")!=0
                            or source_stage.get("precise_coordinates_created")!=0
                            or source_stage.get("safe_candidates_not_published")!=len(staged)):
                        raise ValueError("Generic staging falsely published or verified a market")
                    reports[sid]["source_stage"]=source_stage
                    status["source_only_stage_reviews"]+=1
                status["source_level_raw_profiles_checked"]+=1
            except (ValueError,OSError,TimeoutError) as exc:
                # Unavailable HTTPS endpoint != vanished market. A parser
                # ValueError is DISTINCT: the publisher may have changed
                # schema, granularity or ID meaning. Never treat it as success.
                is_contract_error=isinstance(exc,ValueError)
                classification=("contract_change_needs_review" if is_contract_error
                                else "transport_unavailable")
                if sid in by_old:
                    reports[sid]={**by_old[sid],
                                  "stale_snapshot_carry_forward":True,
                                  "last_check_status":classification,
                                  "last_check_error_class":type(exc).__name__}
                else:
                    reports[sid]={"schema":1,"source_id":sid,
                                  "publisher":profile["publisher"],
                                  "source_url":profile["resource_url"],
                                  "unavailable_no_market_inference":True,
                                  "last_check_status":classification,
                                  "last_check_error_class":type(exc).__name__,
                                  "fingerprints":{}}
                if is_contract_error:
                    status["raw_schema_or_identity_change_requires_review"]+=1
                else:
                    status["raw_source_unavailable_no_market_inference"]+=1
    return {
       "schema":1,"source_contract_schema":1,
       "reference_date":today.isoformat(),
       "registry_sha256":digest(config),
       "read_only":True,
       "market_imports":0,"market_updates":0,"market_confirmations":0,
       "market_identity_deletions":0,
       "source_checks":dict(sorted(status.items())),
       "sources":reports,
       "checked_source_profiles":len(reports),
       "catalog_count":len(catalog),
    }


def markdown(report):
    lines=[
      "# Source lifecycle — manutenzione automatica di dataset, non mercati uno per uno",
      "",
      "Le fonti hanno un contratto per schema, identità, formato, granularità, data e diritti.",
      "Nessuna riga di venditore, concessione o testo grezzo viene persistita qui.",
      "La data di lettura non prova che un mercato abbia aperto oggi.",
      "",
      f"- Schede nazionali confrontate: **{report['catalog_count']:,}**",
      f"- Fonti controllate: **{report['checked_source_profiles']}**",
      f"- Record di mercato importati da questo audit: **{report['market_imports']}**",
      f"- Aperture individuali verificate: **{report['market_confirmations']}**",
      "",
      "| Fonte | Stato | ID fonte fuori catalogo (non nuovi mercati) | Già trattenuti dal controllo sovrapposizioni | Residui senza esito del filtro | Proposte in staging | Collisioni da valutare | Fatti cambiati | ID non più visti (non chiusi) |",
      "|---|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for sid,row in sorted(report["sources"].items()):
        counts=row.get("counts",{})
        d=row.get("diff",{})
        state=("schema/identità cambiati: revisione della fonte richiesta"
               if row.get("last_check_status")=="contract_change_needs_review"
               else "non disponibile / vecchio checkpoint" if row.get("stale_snapshot_carry_forward")
               else "non disponibile" if row.get("unavailable_no_market_inference")
               else "sola verifica, non apertura confermata")
        missing=d.get("missing_source_identities_since_last_scan",
                      d.get("missing_source_identities_since_last_scan",0))
        changed=d.get("changed_source_identities_since_last_scan",
                      d.get("changed_existing_identities_since_last_scan",0))
        new=counts.get("identity_not_in_existing_catalog",
                       counts.get("source_ids_not_yet_in_catalog",0))
        screened=row.get("source_screening") or {}
        already=screened.get("already_quarantined_by_venue_overlap_review",0)
        unclassified=screened.get("remaining_identities_without_overlap_disposition",new)
        source_stage=row.get("source_stage") or {}
        safe_ideas=source_stage.get("safe_candidates_not_published",0)
        collisions=sum((source_stage.get("review_reason_counts") or {}).values())
        lines.append(
            f"| {sid} | {state} | {new} | {already} | "
            f"{unclassified} | {safe_ideas} | {collisions} | {changed} | {missing} |"
        )
    lines.extend(["",
     "## Aggiunta di nuove fonti (senza nuovi script per Comune)",
     "",
     "1. Scoprire il dataset nella coda automatica e verificare a livello di **fonte** editore, diritti, struttura, data e contenuto.",
     "2. Registrarne il contratto JSON: colonne, identità stabile, una riga=sede/giorno/posteggio, schema atteso, budget dimensione e data effettiva.",
     "3. Gli stessi parser e controlli confrontano in automatico tutti i record ad ogni aggiornamento.",
     "4. Fonti nuove/modificate, identità collidenti, sedi dubbie o dati storici sono trattenuti in revisione: nessun market/evento inventato.",
     "5. Gli adapter esistenti continuano a gestire gli import già revisionati. La promozione di altri contratti richiede qualità/licenza/gate DEV separati.",
     "",
     "Le proposte in staging non sono mercati nuovi o aperti: richiedono diritti, identità e QA. Le collisioni segnalano possibili doppioni e sedi non distinguibili.",
     "Questo report non elimina mercati scomparsi da una sorgente e non assegna nuova navigazione GPS.",
     "",
    ])
    return "\n".join(lines)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--contracts",type=Path,default=Path("backend/data/market-source-contracts.json"))
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--source-dir",type=Path)
    p.add_argument("--previous",type=Path)
    p.add_argument("--probe-raw",action="store_true")
    p.add_argument("--stage-raw",action="store_true")
    p.add_argument("--today",type=date.fromisoformat,default=date.today())
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    args=p.parse_args()
    cfg=json.loads(args.contracts.read_text("utf-8"))
    catalog=load_existing(args.manifest)
    prior=json.loads(args.previous.read_text("utf-8")) if (
        args.previous and args.previous.is_file()) else None
    result=run(cfg,catalog,source_dir=args.source_dir,previous=prior,
               probe_raw=args.probe_raw,stage_raw=args.stage_raw,today=args.today)
    for path in (args.out,args.report):
        path.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,sort_keys=True,indent=2)+"\n","utf-8")
    args.report.write_text(markdown(result),"utf-8")
    print("SOURCE_LIFECYCLE",json.dumps({
       "source_profiles":result["checked_source_profiles"],
       "source_checks":result["source_checks"],"imports":0,
       "confirmed_events":0,"original_market_ids":result["catalog_count"],
    },ensure_ascii=False))


if __name__=="__main__":
    main()
