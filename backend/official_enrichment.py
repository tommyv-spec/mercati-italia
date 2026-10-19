#!/usr/bin/env python3
"""Reconcile official public-source evidence into previously published markets.

Manual observation FIRST (2026-10-12): Regione Lombardia MERCap entries
100001 Albizzate, 100004 Arsago Seprio and 100551 Pogliano Milanese list
street, weekday and hours absent from matching third-party market entries.
This module is a conservative generic *evidence* transfer, not fuzzy dedup.

Never changes stable IDs, event dates, recurrence, primary source, verified
status, city, coordinates or date-of-previous-source. Adds missing published
hours, and follows later versions only for fields explicitly owned by this
engine with the same source identity and an exact previous value receipt.
If the source cannot be joined confidently, keep the original untouched.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date
from pathlib import Path
from urllib.parse import unquote_plus

from lombardia_overlap import location_key, norm
from merge_catalog import load_existing
from field_evidence import (transfer_receipts, managed_update_allowed,
                            mark_managed_fields, clean_receipts,
                            retire_superseded_receipts)
from recurrence_refresh import WEEKDAYS
from source_lombardia import months_of_operation, weekday

# New trusted formats must be manually inspected and added to this allowlist,
# with negative tests before automatic enrichment. No remote user input.
TRUSTED_FEEDS = {
    "lombardia-mercap": {
        "source_prefix": "lo-mercap-",
        "region": "Lombardia",
        "url": "https://www.dati.lombardia.it/d/68zx-njaw",
        "name": "Regione Lombardia – MERCap (archivio regionale, date da verificare)",
        "observation_source_id": "lombardia",
        "max_age_days": 540,
    },
}
MAX_SOURCE_ROWS = 3000
MAX_ENRICHED_RECORDS = 500
MAX_DISTANCE_KM = 0.6
FIELD_MANAGER = "official_enrichment"

# Observed in the live MERCap snapshot read on 2026-10-19:
# 100126 VIA PALU', 101346 VIA CA' ZENUCCHI, 100368 PIAZZA G.ARDIZZONE, SNC,
# and 100378 PIAZZA DELLA PACE, /.  These are spelling/empty-civic markers.
# Numeric civic numbers and separators between several roads remain identity
# evidence: never drop them to manufacture a match.
EMPTY_CIVIC = re.compile(r",\s*(?:s\.?n\.?c\.?|[/\*])\s*$")
FINAL_ACCENT_MARK = re.compile(r"(?<=[a-z])'(?=\s|$)")
INITIAL_SPACING = re.compile(r"(?<=\b[a-z])\.(?=[a-z])")
ROAD_SEPARATOR = re.compile(
    r"\s*;\s*|\s*/\s*(?=(?:via|viale|piazza|piazzale|largo|corso)\b)"
)
# Used ONLY to detect conflicting possible venues, never to create a match.
LOCATING_CIVIC = re.compile(
    r"(?:,\s*|\s+(?:n\.?\s*|civico\s+)?)\d+(?:\s*[/\-]?\s*[a-z])?\s*$"
)
# Only the complete annual weekly formats observed in the two adapters can
# establish a generic join. A weekday in a slug, forecast or seasonal rule
# is insufficient: MERCap 38846 is fortnightly and 76670 is summer-only.
FULL_WEEKLY = re.compile(
    r"(?:ogni\s+|settimanale\s*[-:]\s*)(" + "|".join(WEEKDAYS) + r")"
)
DAY_WORDS = re.compile(r"\b(?:" + "|".join(WEEKDAYS) + r")\b")
DAY_SUFFIX = re.compile(r"-(" + "|".join(WEEKDAYS) + r")$")
SPECIALIZED_MARKET = re.compile(
    r"\b(?:filiera corta|produttori locali|campagna amica|coldiretti|slow food|"
    r"agricol\w*|contadin\w*|antiquar\w*|vintage|collezion\w*|biologic\w*|"
    r"artigian\w*)\b"
)

# Actual adapter strings: one time span or two labelled seasonal spans.
PAIR = r"(?:[01]\d|2[0-3]):[0-5]\d[–-](?:[01]\d|2[0-3]):[0-5]\d"
SIMPLE = re.compile(r"^" + PAIR + r" \(fonte comunale, da verificare\)$")
SEASONAL = re.compile(
    r"^(?:Inverno: "+PAIR+r"(?:; )?)?(?:Estate: "+PAIR+r")?"
    r" \(fonte comunale, da verificare\)$"
)


def hours_allowed(value):
    value = str(value or "").strip()
    if not value or len(value) > 160:
        return False
    if SIMPLE.fullmatch(value):
        values = re.findall(r"\d\d:\d\d", value)
    elif SEASONAL.fullmatch(value):
        values = re.findall(r"\d\d:\d\d", value)
    else:
        return False
    return len(values) in (2, 4) and all(
        end > start for start, end in zip(values[::2], values[1::2])
    )


def distance_km(a, b):
    try:
        lat1, lng1 = float(a["lat"]), float(a["lng"])
        lat2, lng2 = float(b["lat"]), float(b["lng"])
    except (KeyError, ValueError, TypeError, OverflowError):
        return None
    if not (40 <= lat1 <= 47 and 40 <= lat2 <= 47 and
            6 <= lng1 <= 19 and 6 <= lng2 <= 19):
        return None
    rad = math.pi / 180
    dlat = (lat2 - lat1) * rad
    dlng = (lng2 - lng1) * rad
    hav = (math.sin(dlat / 2)**2 +
           math.cos(lat1 * rad) * math.cos(lat2 * rad) *
           math.sin(dlng / 2)**2)
    return 12742.0 * math.asin(min(1.0, math.sqrt(hav)))


def evidence_key(record, region):
    location = location_key(record, region)
    if location is not None:
        location = (location[0], street_identity(record.get("indirizzo")))
    return location, explicit_annual_weekday(record)


def explicit_annual_weekday(record):
    """Return one explicitly weekly weekday, with no seasonal qualifiers.

    Identity suffixes may veto a contradictory rule, but can never supply
    a missing recurrence. Dates, including many generated dates, are ignored.
    """
    match = FULL_WEEKLY.fullmatch(norm(record.get("ricorrenza_testo")))
    if not match:
        return frozenset()
    day = match.group(1)
    suffix = DAY_SUFFIX.search(norm(record.get("slug")))
    if suffix and suffix.group(1) != day:
        return frozenset()
    return frozenset({WEEKDAYS.index(day)})


def street_identity(value):
    """Normalize observed spelling variants without losing venue boundaries."""
    text = norm(value).replace("’", "'")
    text = FINAL_ACCENT_MARK.sub("", text)
    text = EMPTY_CIVIC.sub("", text)
    text = INITIAL_SPACING.sub(". ", text)
    return " ".join(text.split())


def _street_conflict_keys(value):
    """Broader keys can veto an enrichment; they can never authorize one."""
    parts = ROAD_SEPARATOR.split(street_identity(value))
    keys = set()
    for part in parts:
        if part:
            keys.add(part)
            keys.add(LOCATING_CIVIC.sub("", part).strip())
    return {key for key in keys if len(key) >= 8}


def _generic_weekly_market(record):
    city = norm(record.get("citta"))
    name = norm(record.get("nome"))
    return bool(city and re.fullmatch(
        r"mercato settimanale (?:a|di|del|della) " + re.escape(city), name
    ))


def _ordinary_market_compatible(source, target):
    # A regional mixed market is not evidence for a producers' market or
    # named fair sharing the street. URL classification is also considered
    # because older records may have an overly broad stored category.
    if (norm(source.get("categoria")) != "misto"
            or norm(target.get("categoria")) != "misto"
            or not _generic_weekly_market(target)):
        return False
    for record in (source, target):
        tags = record.get("tags") or []
        fields = [record.get("nome"), record.get("url_fonte")]
        fields.extend(tags if isinstance(tags, list) else [tags])
        text = " ".join(norm(unquote_plus(str(value or ""))) for value in fields)
        text = re.sub(r"[\W_]+", " ", text)
        if SPECIALIZED_MARKET.search(text):
            return False
    return True


def official_identity_issue(source):
    """Validate raw cadence and merchandise type before any generic join.

    The adapter historically labels every MERCap row as mixed, including
    food-only 100370. Raw publisher fields, not that broad label, establish
    whether the official market is eligible for this generic transfer.
    """
    details = source.get("identita_fonte")
    if (not isinstance(details, dict) or type(details.get("schema")) is not int
            or details.get("schema") != 1):
        return "official_raw_identity_missing"
    if (norm(details.get("periodicita_tipo")) != "settimanale"
            or details.get("frequenza_settimanale") not in (None, "")
            or months_of_operation(details.get("mesi_svolgimento")) != set(range(1, 13))
            or frozenset({weekday(details.get("giorno"))}) != explicit_annual_weekday(source)):
        return "official_raw_recurrence_not_annual_weekly"

    def count(field):
        value = details.get(field)
        if (isinstance(value, bool) or not isinstance(value, (str, int))
                or not re.fullmatch(r"\d{1,6}", str(value))):
            return None
        return int(value)

    food, other, total = (count(field) for field in
                           ("n_post_alim", "n_post_non_alim", "n_post_tot"))
    if (food is None or other is None or total is None
            or food <= 0 or other <= 0 or food + other != total):
        return "official_mixed_market_type_not_proved"
    return ""


def enrich(base, held_official, *, source_id="lombardia-mercap", today=None):
    today = today or date.today()
    if source_id not in TRUSTED_FEEDS:
        raise ValueError("Unreviewed source enrichment is not allowed")
    spec = TRUSTED_FEEDS[source_id]
    if not isinstance(base, list) or not isinstance(held_official, list):
        raise ValueError("Invalid official enrichment input")
    if len(held_official) > MAX_SOURCE_ROWS:
        raise ValueError("Too many official rows for source enrichment")
    baseline = {}
    for record in base:
        slug = record.get("slug")
        if not slug or slug in baseline:
            raise ValueError("Duplicate/missing baseline market identity")
        baseline[slug] = record
    updated = {slug:dict(record) for slug,record in baseline.items()}
    by_key = defaultdict(list)
    legacy_by_location = defaultdict(list)
    counts = Counter()
    identity_conflicts = []
    seen_conflicts = set()

    def record_conflict(old, source, reason):
        identity = (old["slug"], source["slug"], reason)
        if identity in seen_conflicts:
            return
        seen_conflicts.add(identity)
        identity_conflicts.append({
            "published_id": old["slug"],
            "official_id": str(source.get("id_fonte") or source["slug"]),
            "official_slug": source["slug"],
            "reason": reason,
            "existing_recurrence": old.get("ricorrenza_testo"),
            "official_recurrence": source.get("ricorrenza_testo"),
            "existing_category": old.get("categoria"),
            "official_category": source.get("categoria"),
            "official_raw_identity": source.get("identita_fonte"),
            "existing_street": old.get("indirizzo"),
            "official_street": source.get("indirizzo"),
            "existing_hours": old.get("orario_testo"),
            "official_hours": source.get("orario_testo"),
            "existing_source_url": old.get("url_fonte"),
            "source_updated_on": source.get("aggiornato_il"),
            "source_url": spec["url"],
            "action": "held_without_evidence_transfer",
        })

    for row in base:
        if (row.get("regione") != spec["region"]
                or row["slug"].startswith(spec["source_prefix"])):
            continue
        key, weekdays = evidence_key(row, spec["region"])
        if key is not None:
            legacy_by_location[key].append(row)
        if key is not None and len(weekdays) == 1:
            by_key[(key,weekdays)].append(row)
        elif key is not None:
            counts["skipped_legacy_without_explicit_annual_weekday"] += 1

    incoming_by_key = defaultdict(list)
    source_conflict_index = defaultdict(set)
    source_exact_conflict_index = defaultdict(set)
    for official in held_official:
        if not isinstance(official, dict):
            raise ValueError("Invalid official record type")
        sid = str(official.get("slug") or "")
        if (not sid.startswith(spec["source_prefix"])
                or official.get("regione") != spec["region"]
                or official.get("url_fonte") != spec["url"]
                or official.get("verificato_il")
                or official.get("date_quality") == "confermata"):
            raise ValueError("Official evidence contract mismatch")
        last = str(official.get("aggiornato_il") or "")[:10]
        try:
            age = (today - date.fromisoformat(last)).days
        except (TypeError, ValueError):
            raise ValueError("Official evidence has no valid dataset date") from None
        if age < -1:
            raise ValueError("Official source timestamp is in the future")
        if age > spec["max_age_days"]:
            counts["skipped_stale_official_dataset"] += 1
            continue
        key, days = evidence_key(official, spec["region"])
        # Keep ambiguous-day rows as possible conflicts. Their missing day
        # cannot prove a different schedule or justify joining two venues.
        # An explicit seasonal/monthly weekday is useful ONLY as a conflict
        # veto. It still cannot create an annual weekly match.
        declared_days = set(DAY_WORDS.findall(norm(official.get("ricorrenza_testo"))))
        conflict_day = (WEEKDAYS.index(next(iter(declared_days)))
                        if len(declared_days) == 1 else None)
        conflict_town = (norm(official.get("citta")),
                         norm(official.get("provincia")), conflict_day)
        if key is not None:
            source_exact_conflict_index[(*conflict_town, key[1])].add(sid)
        for street in _street_conflict_keys(official.get("indirizzo")):
            source_conflict_index[(*conflict_town, street)].add(sid)
        raw_identity_issue = official_identity_issue(official)
        if key is not None and len(days) == 1 and not raw_identity_issue:
            incoming_by_key[(key,days)].append(official)
            for old in legacy_by_location.get(key, []):
                if not explicit_annual_weekday(old):
                    record_conflict(old, official, "legacy_recurrence_not_explicit_annual_weekly")
        elif key is not None and len(days) == 1:
            counts["skipped_official_raw_identity_unproved_or_conflicting"] += 1
            for old in legacy_by_location.get(key, []):
                record_conflict(old, official, raw_identity_issue)
        else:
            counts["skipped_no_exact_location_or_day"] += 1
            if key is not None and not days:
                counts["skipped_official_without_explicit_annual_weekday"] += 1
                for old in legacy_by_location.get(key, []):
                    record_conflict(old, official, "official_recurrence_not_explicit_annual_weekly")

    samples = []
    field_updates = []
    preserved_hours_differences = []
    touched = set()
    for key, source_rows in sorted(incoming_by_key.items(), key=str):
        if len(source_rows) != 1:
            counts["skipped_multiple_official_markets_same_venue_day"] += len(source_rows)
            continue
        source = source_rows[0]
        old_rows = by_key.get(key, [])
        if not old_rows:
            counts["skipped_no_exact_legacy_market"] += 1
            continue
        if not hours_allowed(source.get("orario_testo")):
            counts["skipped_no_safe_official_hours"] += 1
            continue
        for old in old_rows:
            slug = old["slug"]
            old_province = str(old.get("provincia") or "").strip().upper()
            src_province = str(source.get("provincia") or "").strip().upper()
            # Homonymous municipalities in different provinces are not
            # the same physical market, even when street/day strings match.
            if old_province and src_province and old_province != src_province:
                counts["skipped_province_conflict"] += 1
                continue
            # Ineligible seasonal/monthly sources still count as distinct
            # possible markets. Filtering their recurrence must not make a
            # previously ambiguous venue/day look unique.
            exact_ids = set()
            for conflict_day in (next(iter(key[1])), None):
                exact_ids.update(source_exact_conflict_index.get((
                    norm(source.get("citta")), norm(src_province),
                    conflict_day, key[0][1]), set()))
            if exact_ids != {str(source["slug"])}:
                counts["skipped_multiple_official_markets_same_venue_day"] += 1
                record_conflict(old, source, "other_official_market_at_same_venue_day")
                continue
            spelling_match = (location_key(old, spec["region"])
                              != location_key(source, spec["region"]))
            if spelling_match:
                # New spelling variants require the same complete municipal
                # identity and an ordinary weekly market, not a named fair
                # sharing a street. Keep previous exact matches compatible.
                if (not old_province or old_province != src_province
                        or not _generic_weekly_market(old)):
                    counts["skipped_spelling_match_without_full_identity"] += 1
                    continue
                city = norm(old.get("citta"))
                source_day = next(iter(key[1]))
                possible_ids = set()
                for street in _street_conflict_keys(old.get("indirizzo")):
                    for day in (source_day, None):
                        possible_ids.update(source_conflict_index.get(
                            (city, norm(old_province), day, street), set()))
                if possible_ids != {str(source["slug"])}:
                    counts["skipped_conflicting_civic_or_road_extent"] += 1
                    continue
            if not _ordinary_market_compatible(source, old):
                counts["skipped_market_type_unproved_or_conflicting"] += 1
                record_conflict(old, source, "market_type_unproved_or_conflicting")
                continue
            gap = distance_km(old,source)
            if gap is not None and gap > MAX_DISTANCE_KM:
                counts["skipped_coordinates_conflict"] += 1
                continue
            # A newer source version may change only a value previously
            # assigned by this engine. Coincident observations do not grant
            # ownership of a human/legacy field.
            present = str(old.get("orario_testo") or "").strip()
            official_entry = {"nome":spec["name"],"url":spec["url"]}
            revised = updated[slug]
            incoming_hours = str(source["orario_testo"])
            proposed = {**old, "orario_testo": incoming_hours}
            source_receipts = [receipt for receipt in transfer_receipts(
                source, proposed, {"orario_testo"}, today=today
            ) if (receipt.get("valori", {}).get("orario_testo") == incoming_hours
                  and receipt.get("fonte_id") == spec["observation_source_id"]
                  and receipt.get("url") == spec["url"]
                  and receipt.get("riga_fonte") == str(source.get("id_fonte") or source["slug"])
                  and receipt.get("metodo") == "sede_giorno_provincia")]
            managed_change = bool(present and present != incoming_hours and any(
                managed_update_allowed(old, receipt, "orario_testo",
                                       manager=FIELD_MANAGER, today=today)
                for receipt in source_receipts))
            if not present:
                revised["orario_testo"] = incoming_hours
                counts["hours_added"] += 1
                touched.add(slug)
            elif managed_change:
                revised["orario_testo"] = incoming_hours
                counts["managed_hours_updated"] += 1
                touched.add(slug)
            if not present or managed_change:
                field_updates.append({
                    "published_id": slug,
                    "official_id": str(source.get("id_fonte") or source["slug"]),
                    "official_slug": source["slug"],
                    "field": "orario_testo",
                    "before": present,
                    "after": revised["orario_testo"],
                    "existing_street": old.get("indirizzo"),
                    "official_street": source.get("indirizzo"),
                    "match": "observed_spelling" if spelling_match else "exact",
                    "action": "updated_managed_source_version" if managed_change else "filled_missing",
                    "previous_evidence": clean_receipts(
                        old.get("riscontri_campi"), old, today=today
                    ) if managed_change else [],
                })
            else:
                counts["existing_hours_preserved"] += 1
                if present != str(source["orario_testo"]):
                    counts["existing_hours_differ_from_official"] += 1
                    preserved_hours_differences.append({
                        "published_id": slug,
                        "official_slug": source["slug"],
                        "existing_street": old.get("indirizzo"),
                        "existing_hours": present,
                        "official_hours": source["orario_testo"],
                        "source_updated_on": source.get("aggiornato_il"),
                        "source_url": spec["url"],
                        "previous_evidence": clean_receipts(
                            old.get("riscontri_campi"), old, today=today
                        ),
                        "new_source_evidence": source_receipts,
                        "action": "held_without_managed_update_authorization",
                    })
            primary = {
                "nome":str(old.get("fonte") or ""),
                "url":str(old.get("url_fonte") or ""),
            }
            raw = old.get("fonti")
            links = [x for x in (raw if isinstance(raw,list) else [])
                     if isinstance(x,dict)]
            links = [x.copy() for x in links]
            if primary["nome"] or primary["url"]:
                if primary not in links: links.append(primary)
            if official_entry not in links:
                links.append(official_entry)
                counts["official_source_attributions_added"] += 1
                touched.add(slug)
            revised["fonti"] = links
            observations = transfer_receipts(
                source, revised, {"orario_testo"}, today=today
            )
            if present and present != incoming_hours and not managed_change:
                before_retirement = observations
                for incoming_receipt in source_receipts:
                    observations = retire_superseded_receipts(
                        {**revised, "riscontri_campi": observations}, incoming_receipt, today=today
                    )
                if observations != before_retirement:
                    counts["obsolete_source_claims_retired"] += 1
            if not present or managed_change:
                observations = [mark_managed_fields(
                    receipt, {"orario_testo"}, manager=FIELD_MANAGER, previous=old
                ) if (receipt.get("valori", {}).get("orario_testo") == incoming_hours
                      and receipt.get("fonte_id") == spec["observation_source_id"]
                      and receipt.get("url") == spec["url"]
                      and receipt.get("riga_fonte") == str(source.get("id_fonte") or source["slug"])
                      and receipt.get("metodo") == "sede_giorno_provincia")
                    else receipt for receipt in observations]
            if observations != (old.get("riscontri_campi") or []):
                revised["riscontri_campi"] = observations
                counts["field_observation_records_updated"] += 1
                touched.add(slug)
            counts["exact_matches"] += 1
            if spelling_match:
                counts["observed_spelling_matches"] += 1
            if len(samples) < 30:
                samples.append({
                    "published_id":slug,
                    "official_id":str(source.get("id_fonte") or source.get("slug"))[:50],
                    "street":str(old.get("indirizzo") or "")[:100],
                    "source_day":sorted(explicit_annual_weekday(source)),
                    "distance_km":round(gap,3) if gap is not None else None,
                    "changed_hours":not bool(present),
                })
    if len(touched) > MAX_ENRICHED_RECORDS:
        raise ValueError("Official source enrichment exceeds per-run limit")
    return [updated[x["slug"]] for x in base], {
        "schema":1,
        "source_id":source_id,
        "source_name":spec["name"],
        "review_only":True,
        "source_rows_screened":len(held_official),
        "legacy_records_changed":len(touched),
        "existing_market_hours_added":int(counts["hours_added"]),
        "managed_market_hours_updated":int(counts["managed_hours_updated"]),
        "official_source_attributions_added":int(counts["official_source_attributions_added"]),
        "field_observation_records_updated":int(counts["field_observation_records_updated"]),
        "exact_matches":int(counts["exact_matches"]),
        "counts":dict(sorted(counts.items())),
        "samples":samples,
        "field_updates":field_updates,
        "preserved_hours_differences":preserved_hours_differences,
        "identity_conflicts":identity_conflicts,
        "record_identity_changes":0,
        "confirmed_date_changes":0,
        "individual_market_verifications":0,
        "coordinates_overwritten":0,
        "primary_sources_overwritten":0,
        "old_dataset_dates_overwritten":0,
    }


def markdown(report):
    text = [
        "# Official source enrichment — legacy cards",
        "",
        "A previously published venue gets source-backed missing hours only",
        "after exact municipality, street and weekday matching, and a",
        "compatible map point when both coordinates are available.",
        "No forecast, human verification, original source, or identity changed.",
        "",
        f"- Held official rows screened: **{report['source_rows_screened']}**",
        f"- Existing market cards with added information: **{report['legacy_records_changed']}**",
        f"- Missing hours supplied from official regional source: **{report['existing_market_hours_added']}**",
        f"- Official source attributions attached: **{report['official_source_attributions_added']}**",
    ]
    for key, val in report["counts"].items():
        text.append(f"- {key}: {val}")
    text.extend(["", "## Example exact matches", ""])
    for sample in report["samples"]:
        text.append(
            f"- {sample['published_id']} ← {sample['official_id']} "
            f"(hours added: {sample['changed_hours']}, "
            f"venue distance: {sample['distance_km']} km)"
        )
    return "\n".join(text)+"\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path,required=True)
    p.add_argument("--official", type=Path,required=True)
    p.add_argument("--updated", type=Path,required=True)
    p.add_argument("--report", type=Path,required=True)
    p.add_argument("--summary", type=Path,required=True)
    args=p.parse_args()
    current=load_existing(args.manifest)
    candidates=json.loads(args.official.read_text("utf-8"))
    rows, report=enrich(current,candidates)
    for path in (args.updated,args.report,args.summary):
        path.parent.mkdir(parents=True,exist_ok=True)
    args.updated.write_text(json.dumps(rows,indent=2,ensure_ascii=False)+"\n","utf-8")
    args.report.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n","utf-8")
    args.summary.write_text(markdown(report),"utf-8")
    print(json.dumps({key:report[key] for key in
                      ("legacy_records_changed","existing_market_hours_added",
                       "official_source_attributions_added","source_rows_screened")},ensure_ascii=False))


if __name__ == "__main__":
    main()
