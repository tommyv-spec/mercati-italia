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
from recurrence_refresh import calendar_key, complete_monthly_rule, explicit_rule, forecast_rule
from source_lifecycle import (
    MARKET_KINDS, MONTH_KIND, WEEKDAYS_NORMAL, parse_rows, candidate_record, canonical, digest,
    excluded_row, istat_municipality, validate_contracts, weekday as source_weekday,
    weekdays as source_weekdays,
)
from official_enrichment import DAYPARTS, SPECIALIZED_MARKET, _shares_place_word
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
# Fields of OTHER publishers' markets proved by a unique municipality+weekday
# join with a contracted multi-town calendar (never by its row ID).
FILL_MANAGER = "source_contract_town_day"
FILL_METHOD = "comune_provincia_giorno_univoco"
# Monthly calendars join on municipality + calendar ("prima domenica del mese").
FILL_METHOD_MONTH = "comune_provincia_ricorrenza_univoca"
FILL_FIELDS = ("indirizzo", "orario_testo")
EXACT_SOURCE_HOURS = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d–(?:[01]\d|2[0-3]):[0-5]\d \(da verificare con il Comune\)")
ORDINARY_CATEGORIES = frozenset({"misto", "alimentare"})
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
    if profile.get("row_kind") not in MARKET_KINDS:
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


def _market_calendar(row):
    """(kind, weekdays, ordinal) of a market's recurrence, or None: the export's venue_slot key."""
    rule=forecast_rule(row)
    return calendar_key(rule) if rule else None


def _market_slots(profile, row):
    """Slots a catalog market occupies: its weekdays, or its one monthly calendar."""
    if profile["row_kind"]!=MONTH_KIND:
        return weekday_evidence(row)
    key=_market_calendar(row)
    return {key} if key and key[0]=="monthly_nth_weekday" else None


def _review_reason(record, prior, candidate_day, *, allow_unlocated_city_summary=False,
                   calendar=None):
    # A source with no reliable street/day or a generic city listing cannot
    # automatically disambiguate a new venue from a legacy public calendar.
    if (canonical(prior.get("citta"))!=canonical(record.get("citta"))
            or canonical(prior.get("regione"))!=canonical(record.get("regione"))):
        return None
    previous_days=weekday_evidence(prior)
    if calendar is not None:
        # A monthly venue: another known calendar is another market.
        if _market_calendar(prior) not in (None, calendar):
            return None
    elif candidate_day is not None and previous_days is not None:
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


def _town_day_taken(record, cohort, unresolved_localities, profile=None):
    """A new official venue must not duplicate a market already listed.

    Any visible market of the same municipality on one of its weekdays (on
    its monthly calendar, for a monthly source) may be this venue under
    another publisher's name or street: hold, never guess.
    Markets filed under a locality that is no ISTAT municipality (a merged
    town or frazione) count when the candidate's name/street names it.
    """
    monthly=profile is not None and profile["row_kind"]==MONTH_KIND
    slots=(lambda row:_market_slots(profile,row)) if monthly else weekday_evidence
    unit="calendar" if monthly else "day"
    days=slots(record)
    if not days:
        return "new_market_calendar_unknown" if monthly else "new_market_weekday_unknown"
    for prior in cohort:
        if not prior.get("duplicato_di") and (slots(prior) or set()) & days:
            return "existing_market_same_town_"+unit
        # An antiques card with no readable calendar may be this very market.
        if (monthly and not prior.get("duplicato_di") and _market_calendar(prior) is None
                and _fill_target_type(profile,prior)):
            return "existing_same_type_market_calendar_unknown"
    text=" "+canonical(" ".join(str(record.get(field) or "")
                                for field in ("nome","indirizzo","citta")))+" "
    for prior in unresolved_localities:
        place=canonical(prior.get("citta"))
        if (not prior.get("duplicato_di") and len(place)>=3 and " "+place+" " in text
                and (slots(prior) or set()) & days):
            return "existing_market_same_locality_"+unit
    return None


def _source_point(row):
    """A map point some source gave. Our OpenStreetMap street pin is not one: it is
    looked up again from the address every run, so it never blocks a street fix."""
    from position_resolver import clean_position_source
    return ((row.get("lat") is not None or row.get("lng") is not None)
            and clean_position_source(row.get("posizione_fonte"), row) is None)


def _placeholder_street(value):
    """No usable venue: empty, a vague label or a truncated scrap ("pia")."""
    text=addr_key(value)
    return not text or text in VAGUE_ADDRESSES or len(text.replace(" ",""))<6


def _replaceable_hours(current, official):
    """Empty, or a part of the day that every official opening starts in."""
    current=str(current or "").strip()
    if not current:
        return True
    span=DAYPARTS.get(addr_key(current))
    return bool(span and EXACT_SOURCE_HOURS.fullmatch(official or "")
                and span[0]<=int(official[:2])<span[1])


def _ordinary_market(row):
    tags=row.get("tags") or []
    text=" ".join(canonical(v) for v in [row.get("nome"),row.get("url_fonte"),
                                         *(tags if isinstance(tags,list) else [tags])])
    return canonical(row.get("categoria")) in ORDINARY_CATEGORIES and not SPECIALIZED_MARKET.search(text)


def _row_days(profile, row):
    """Weekdays a source row may run on; unknown wording competes for every day."""
    value=row.get(profile["weekday_field"])
    days=source_weekdays(value)
    if days is None:
        text=" "+canonical(value)+" "
        days=tuple(i for i,name in enumerate(WEEKDAYS_NORMAL) if " "+name+" " in text) or tuple(range(7))
    return days


def _row_slots(profile, row):
    """Slots a source row may hold; a monthly row with no monthly rule holds them all ("*")."""
    if profile["row_kind"]!=MONTH_KIND:
        return _row_days(profile,row)
    # The bare rule, even when exclusions follow it: such a row still is that market.
    rule=explicit_rule(row.get(profile["recurrence_field"]))
    return (calendar_key(rule),) if rule and rule["kind"]=="monthly_nth_weekday" else ("*",)


def _fill_target_type(profile, row):
    """Weekly calendars fill ordinary markets; others the categories their contract names."""
    categories=profile["existing_market_fill"].get("categories")
    return row.get("categoria") in categories if categories else _ordinary_market(row)


def _fill_link(profile):
    return {"nome":profile["publisher"],"url":profile["attribution_url"]}


def _with_link(row, link):
    primary={"nome":str(row.get("fonte") or ""),"url":str(row.get("url_fonte") or "")}
    links=[dict(item) for item in (row.get("fonti") or []) if isinstance(item,dict)]
    if (primary["nome"] or primary["url"]) and primary not in links:
        links.append(primary)
    if link not in links:
        links.append(link)
    return links


def town_day_fills(profile, source, base, *, today, read_on, source_date, parsed_sha256,
                   claimed=frozenset()):
    """Official street/hours for OTHER publishers' markets, by municipality+weekday.

    A market is joined only when, for each of its weekdays, it is the only
    visible weekly market of its municipality in the catalog AND the complete
    source has exactly one market row there (seasonal, daily or unparsed rows
    compete too; non-market rows such as single stalls do not). A saved real
    street must share a distinctive word with the official one. Only empty or
    vague values are filled (or values this engine owns, from a newer version);
    better data is never overwritten. Returns proofs and a reason count.

    A monthly calendar (row_kind market_venue_month) joins the same way on
    municipality + calendar ("prima domenica del mese", the export's
    same-market key) and fills markets of the categories its contract names.
    Its row must state the rule and nothing else (no exclusions it can't
    carry). When the card's own recurrence text states exactly that rule, the
    receipt also records it: the calendar still lists this market.
    """
    region=profile["region"]
    monthly=profile["row_kind"]==MONTH_KIND
    unit="calendar" if monthly else "day"
    counts=Counter()
    competitors=defaultdict(set)
    official={}
    qualified=set()
    for index,row in enumerate(source):
        if excluded_row(profile,row):
            continue
        place=(istat_municipality(region,row.get(profile["municipality_field"]))
               if profile.get("municipality_field") else
               (profile["municipality"],profile["province"]))
        if place is None:
            continue
        for day in _row_slots(profile,row):
            competitors[(canonical(place[0]),day)].add(index)
        record,issue,_=candidate_record(profile,row,today=today,source_date=source_date)
        if record is not None and issue is None:
            official[index]=record
        elif record is not None and issue=="schedule_unknown":
            qualified.add(index)
    slots=defaultdict(list)
    for row in base:
        if row.get("regione")==region and not row.get("duplicato_di"):
            for day in _market_slots(profile,row) or ():
                slots[(canonical(row.get("citta")),day)].append(row["slug"])
    link=_fill_link(profile)
    proofs=[]
    for target in sorted(base,key=lambda row:row["slug"]):
        days=_market_slots(profile,target)
        if (target.get("regione")!=region or target.get("duplicato_di") or not days
                or target["slug"].startswith(profile["catalog_slug_prefix"])
                or target["slug"] in claimed):
            continue
        counts[("monthly" if monthly else "weekly")+"_markets_screened"]+=1
        city=canonical(target.get("citta"))
        place=istat_municipality(region,target.get("citta"))
        sources={frozenset(competitors.get((city,day),set())|competitors.get((city,"*"),set()))
                 for day in days}
        reason=None
        if target.get("verificato_il"):
            reason="human_verified_market"
        elif not _fill_target_type(profile,target):
            reason="market_type_not_in_contract" if monthly else "market_type_not_ordinary"
        elif place and target.get("provincia") and target["provincia"]!=place[1]:
            reason="province_differs"
        elif any(len(slots[(city,day)])>1 for day in days):
            reason="several_catalog_markets_same_town_"+unit
        elif frozenset() in sources:
            reason="no_official_market_town_"+unit
        elif any(len(ids)>1 for ids in sources):
            reason="several_official_markets_same_town_"+unit
        elif len(sources)!=1:
            reason="weekdays_in_different_official_rows"
        if reason:
            counts["held_"+reason]+=1
            continue
        index=next(iter(next(iter(sources))))
        record=official.get(index)
        if record is None:
            counts["held_official_calendar_qualified" if monthly and index in qualified else
                   "held_official_market_not_annual_"+("monthly" if monthly else "weekly")]+=1
            continue
        if not days<=(_market_slots(profile,record) or set()):
            counts["held_weekday_sets_differ"]+=1
            continue
        street=record["indirizzo"]
        if not _placeholder_street(target.get("indirizzo")) and not _shares_place_word(
                target.get("indirizzo"),street):
            counts["held_different_street"]+=1
            continue
        values={"indirizzo":street}
        if EXACT_SOURCE_HOURS.fullmatch(record["orario_testo"]):
            values["orario_testo"]=record["orario_testo"]
        if monthly and (complete_monthly_rule(target.get("ricorrenza_testo"))
                        ==complete_monthly_rule(record["ricorrenza_testo"])):
            # Still listed: the card's own words, never the calendar's.
            values["ricorrenza_testo"]=target["ricorrenza_testo"]
        values={k:v for k,v in values.items() if len(v)<=FIELDS[k]}
        method=FILL_METHOD_MONTH if monthly else FILL_METHOD
        receipt_for=lambda row,vals:make_receipt(
            row,values=vals,source_url=profile["resource_url"],source_name=profile["publisher"],
            source_id=profile["id"],source_row=record["slug"],read_on=read_on,
            source_updated_on=source_date,source_sha256=parsed_sha256,method=method)
        probe=receipt_for({**target,**values},values)
        changes,managed={},set()
        for field,value in values.items():
            current=target.get(field)
            if current==value:
                continue
            if managed_update_allowed(target,probe,field,manager=FILL_MANAGER,today=today):
                managed.add(field)
            elif not (_placeholder_street(current) and target.get("position_quality")!="precisa"
                      if field=="indirizzo" else _replaceable_hours(current,value)):
                counts["kept_existing_"+field]+=1
                continue
            changes[field]={"before":current,"after":value}
        result=copy.deepcopy(target)
        for field,change in changes.items():
            result[field]=change["after"]
        observed={k:v for k,v in values.items() if result.get(k)==v}
        if not observed:
            counts["matched_nothing_to_record"]+=1
            continue
        receipt=receipt_for(result,observed)
        initial=set(changes)-managed
        if initial:
            receipt=mark_managed_fields(receipt,initial,manager=FILL_MANAGER)
        if managed:
            receipt=mark_managed_fields(receipt,managed,manager=FILL_MANAGER,previous=target)
        result["fonti"]=_with_link(target,link)
        result["riscontri_campi"]=clean_receipts(
            [*(target.get("riscontri_campi") or []),receipt],result,today=today)
        # A same-source reread merges with the earlier receipt (keeping its
        # field ownership); the new read itself must survive that merge.
        if not any(saved["valori"]==receipt["valori"] and all(
                saved.get(k)==receipt.get(k) for k in ("fonte_id","riga_fonte","metodo","letto_il","sha256"))
                for saved in result["riscontri_campi"]):
            counts["held_receipt_not_retained"]+=1
            continue
        if result==target:
            continue
        counts["matched_markets"]+=1
        for field in changes:
            counts["filled_"+field]+=1
        if "ricorrenza_testo" in receipt["valori"]:
            counts["recurrence_still_listed"]+=1
        proofs.append({"slug":target["slug"],"source_row":record["slug"],
                       "changed_fields":changes,"receipt":receipt,
                       "before_sha256":evidence_fingerprint(target),
                       "after_sha256":evidence_fingerprint(result)})
    # Per-run cap on visible changes; evidence refreshes are not capped.
    limit=profile["existing_market_fill"]["max_records_per_run"]
    visible=[proof for proof in proofs if proof["changed_fields"]]
    deferred={proof["slug"] for proof in visible[limit:]}
    counts["deferred_to_next_run"]=len(deferred)
    return [proof for proof in proofs if proof["slug"] not in deferred],dict(sorted(counts.items()))


def apply_fill(row, proof, profile, *, today):
    result=copy.deepcopy(row)
    for field,change in proof["changed_fields"].items():
        result[field]=change["after"]
    result["fonti"]=_with_link(row,_fill_link(profile))
    result["riscontri_campi"]=clean_receipts(
        [*(row.get("riscontri_campi") or []),proof["receipt"]],result,today=today)
    return result


def verify_fill(profile, prior, result, proof, *, today, source_observations):
    """Independently check one town/day fill: exact diff, prior gap, bound receipt."""
    source_date=observed_source_date(profile,source_observations,today=today)
    if (not isinstance(proof,dict) or set(proof)!={"slug","source_row","changed_fields","receipt",
                                                    "before_sha256","after_sha256"}
            or proof["slug"]!=prior.get("slug")
            or proof["before_sha256"]!=evidence_fingerprint(prior)
            or proof["after_sha256"]!=evidence_fingerprint(result)
            or prior.get("regione")!=profile["region"] or prior.get("verificato_il")
            or prior.get("duplicato_di")
            or prior["slug"].startswith(profile["catalog_slug_prefix"])
            or not str(proof["source_row"]).startswith(profile["catalog_slug_prefix"])):
        raise ValueError("Town/day fill proof does not belong to this market or source")
    changes,receipt=proof["changed_fields"],proof["receipt"]
    if (not isinstance(changes,dict) or set(changes)-set(FILL_FIELDS)
            or not isinstance(receipt,dict) or not valid_receipt(receipt,result,today=today)
            or receipt.get("fonte_id")!=profile["id"] or receipt.get("fonte")!=profile["publisher"]
            or receipt.get("url")!=profile["resource_url"]
            or receipt.get("riga_fonte")!=proof["source_row"]
            or receipt.get("metodo")!=(FILL_METHOD_MONTH if profile["row_kind"]==MONTH_KIND
                                       else FILL_METHOD)
            or receipt.get("ambito")!="dataset"
            or receipt.get("impronta_tipo")!="publisher_parsed_json"
            or receipt.get("sha256")!=source_observations.get("source_parsed_sha256")
            or receipt.get("letto_il")!=source_observations.get("source_read_on")
            or receipt.get("fonte_aggiornata_il")!=source_date
            or (changes and (receipt.get("gestore_campi")!=FILL_MANAGER
                             or not set(changes)<=set(receipt.get("campi_gestiti") or [])))):
        raise ValueError("Town/day fill receipt is not bound to the observed source")
    plain={k:copy.deepcopy(v) for k,v in receipt.items()
           if k not in {"campi_gestiti","gestore_campi","versioni_precedenti"}}
    for field,change in changes.items():
        before=prior.get(field)
        if (not isinstance(change,dict) or set(change)!={"before","after"}
                or change["before"]!=before or change["after"]!=receipt["valori"].get(field)
                or not (managed_update_allowed(prior,plain,field,manager=FILL_MANAGER,today=today)
                        or (field=="indirizzo" and _placeholder_street(before)
                            and prior.get("position_quality")!="precisa")
                        or (field=="orario_testo" and _replaceable_hours(before,change["after"])))):
            raise ValueError("Town/day fill overwrote a value it may not replace")
    if apply_fill(prior,proof,profile,today=today)!=result:
        raise ValueError("Town/day fill changed an unreported field")
    return len(changes)


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
    if not values.get("ricorrenza_testo", "").startswith(("settimanale - ", "mensile - ")):
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
            or not _same_contract_geography(profile, prior)
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


def _same_contract_geography(profile, row):
    if profile.get("municipality_field"):
        return (row.get("regione") == profile["region"]
                and istat_municipality(profile["region"], row.get("citta"))
                == (row.get("citta"), row.get("provincia")))
    return not any(canonical(row.get(field))!=canonical(profile.get(setting))
                   for field,setting in (("citta","municipality"),
                                         ("provincia","province"),("regione","region")))


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
                or (field == "indirizzo" and _source_point(prior))):
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
    by_province=defaultdict(list)
    for prior in base:
        by_city[(canonical(prior.get("regione")),canonical(prior.get("citta")))].append(prior)
        if istat_municipality(prior.get("regione"),prior.get("citta")) is None:
            by_province[(canonical(prior.get("regione")),canonical(prior.get("provincia")))].append(prior)
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
                      and not (field == "indirizzo" and _source_point(prior))):
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
        # Rows outside new_market_filters_any (a seasonal market) only fill/update.
        new_rules=profile.get("new_market_filters_any")
        if new_rules and not any(all(canonical(item.get(k))==canonical(v) for k,v in rule.items())
                                 for rule in new_rules):
            reasons["not_eligible_as_new_market"]+=1
            continue
        monthly=profile["row_kind"]==MONTH_KIND
        day=None if monthly else source_weekday(item.get(profile["weekday_field"]))
        calendar=_market_calendar(record) if monthly else None
        cohort=by_city[(canonical(record.get("regione")),canonical(record.get("citta")))]
        collision=next((reason for r in cohort
                        if (reason:=_review_reason(
                            record,r,day,allow_unlocated_city_summary=allow_city_summary,
                            calendar=calendar))),None)
        if not collision and profile.get("new_market_requires_free_town_day"):
            collision=_town_day_taken(record, cohort, by_province.get(
                (canonical(record.get("regione")),canonical(record.get("provincia"))),[]), profile)
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
    return candidates,source_facts,updates,retirements,source


def stage(profile,raw_blob,base,*,today,observed_source_sha256=None,read_on=None,
          source_date_proof=None):
    candidates, report, _, _, _ = _stage(profile, raw_blob, base, today=today,
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
    candidates,report,updates,retirements,source=_stage(
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
    fills, fill_counts = [], {}
    if profile.get("existing_market_fill"):
        fills, fill_counts = town_day_fills(
            profile, source, existing, today=today, read_on=report["source_read_on"],
            source_date=report["publisher_dataset_date"],
            parsed_sha256=report["source_parsed_sha256"], claimed=set(updated))
        for proof in fills:
            updated[proof["slug"]] = apply_fill(original[proof["slug"]], proof, profile, today=today)
            verify_fill(profile, original[proof["slug"]], updated[proof["slug"]], proof,
                        today=today, source_observations=report)
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
        "fills":fills,"fill_counts":fill_counts,
        "source_observations":report,
        "verified_events_created":0,
        "geocoordinates_created":0,"new_directions_enabled":0,
        "required_release_checks":["source_diff","static_export","duplicate_review",
                                   "mobile_navigation","security_no_billed_runtime"],
        "dev_only":True,
    }
    return rows,certificate
