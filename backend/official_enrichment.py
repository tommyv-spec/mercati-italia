#!/usr/bin/env python3
"""Reconcile official public-source evidence into previously published markets.

Manual observation FIRST (2026-10-12): Regione Lombardia MERCap entries
100001 Albizzate, 100004 Arsago Seprio and 100551 Pogliano Milanese list
street, weekday and hours absent from matching third-party market entries.
This module is a conservative generic *evidence* transfer, not fuzzy dedup.

Never changes stable IDs, event dates, recurrence, primary source, verified
status, city, coordinates or date-of-previous-source. Adds missing published
hours and, with complete raw-source uniqueness, missing venues. Follows later
versions only for fields explicitly owned by this
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
                            retire_superseded_receipts, fingerprint, identity,
                            MAX_READ_AGE, SOURCE_AGE)
from catalog_quality_report import VAGUE_ADDRESSES, key as address_key
from recurrence_refresh import WEEKDAYS
from lombardia_calendar_scope import calendar_scope
from source_lombardia import (months_of_operation, weekday, convert as convert_lombardia,
                              DAY_LABELS)

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
UNIQUE_TOWN_METHOD = "comune_provincia_giorno_univoco"
# Every field used to authorize a join or a transfer must be reproduced from
# the complete raw payload, independently of its stored normalized checkpoint.
RAW_BOUND_FIELDS = (
    "slug", "id_fonte", "citta", "provincia", "regione", "indirizzo",
    "ricorrenza_testo", "orario_testo", "identita_fonte", "aggiornato_il",
    "categoria", "nome", "tags", "lat", "lng", "url_fonte",
)

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
    scope = calendar_scope(source)
    if scope and (scope["state"] in {"invalid", "ambiguous"} or scope.get("limited")):
        return "official_raw_recurrence_not_annual_weekly"
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


def _complete_raw_context(raw, normalized, *, today):
    """Validate the complete publisher snapshot before looking for uniqueness.

    Normalization can exclude rows (Milano or malformed identities). Every raw
    row still participates in the ambiguity check, including unknown weekdays,
    seasonal markets, and rows whose source ID or ISTAT code is unusable. A
    missing municipality/province cannot be safely scoped and closes this path.
    The established exact-venue path does not depend on this optional context.
    """
    if raw is None:
        return None, {"status": "not_supplied", "raw_rows_screened": 0}
    try:
        reproduced = convert_lombardia(raw, today=today)
    except (KeyError, TypeError, ValueError, OverflowError) as exc:
        return None, {"status": "invalid_complete_snapshot",
                      "reason": str(exc)[:160], "raw_rows_screened": 0}
    expected = {row["slug"]: row for row in reproduced}
    actual = {row.get("slug"): row for row in normalized if isinstance(row, dict)}
    report = {"status": "complete", "raw_rows_screened": len(raw["rows"]),
              "normalized_rows_reproduced": len(reproduced),
              "non_normalized_rows_still_screened": len(raw["rows"]) - len(reproduced),
              "sha256": fingerprint(raw),
              "source_updated_on": raw["publisher_data_updated_at"]}
    if (len(actual) != len(normalized) or set(expected) != set(actual)
            or any(any(row.get(field) != expected[slug].get(field)
                       for field in RAW_BOUND_FIELDS)
                   for slug, row in actual.items())):
        report["status"] = "raw_normalized_checkpoint_mismatch"
        return None, report
    by_town_day = defaultdict(list)
    by_source_id = defaultdict(list)
    for index, row in enumerate(raw["rows"]):
        town = norm(row.get("descom"))
        province = str(row.get("despro") or "").strip().upper()
        if not re.search(r"[a-z]", town) or not re.fullmatch(r"[A-Z]{2}", province):
            report["status"] = "raw_competitor_municipality_unknown"
            return None, report
        by_town_day[(town, province, weekday(row.get("giorno")))].append((index, row))
        by_source_id[str(row.get("codice_id") or "").strip()].append(row)
    # The raw checkpoint carries a publisher date, not a read date. Obtain
    # its actual read only from a valid observation of this entire dataset.
    reads = {proof["letto_il"] for row in normalized for proof in
             clean_receipts(row.get("riscontri_campi"), row, today=today)
             if (proof.get("fonte_id") == "lombardia"
                 and proof.get("url") == row.get("url_fonte")
                 and proof.get("riga_fonte") == str(row.get("id_fonte"))
                 and proof.get("metodo") == "id_fonte"
                 and proof.get("ambito") == "dataset"
                 and proof.get("impronta_tipo") == "publisher_parsed_json"
                 and proof.get("sha256") == report["sha256"]
                 and proof.get("fonte_aggiornata_il") == report["source_updated_on"]
                 and (today - date.fromisoformat(proof["letto_il"])).days <= MAX_READ_AGE)}
    report["read_on"] = max(reads) if reads else ""
    return {"by_town_day": by_town_day, "sha256": report["sha256"],
            "by_source_id": by_source_id, "read_on": report["read_on"],
            "source_updated_on": report["source_updated_on"]}, report


def _replaceable_venue(value):
    """Only absence or enumerated placeholders; short real addresses survive."""
    return (not str(value or "").strip()
            or address_key(value) in VAGUE_ADDRESSES)


# A publisher's part of the day ("La mattina") is a placeholder for exact
# official clock hours, but only when every official opening starts in it.
DAYPARTS = {"la mattina": (0, 12), "il pomeriggio": (12, 24)}


def _daypart_agrees(current, official):
    span = DAYPARTS.get(address_key(current))
    starts = re.findall(r"(\d\d):\d\d", str(official or ""))[::2]
    return bool(span and starts and hours_allowed(official)
                and all(span[0] <= int(hour) < span[1] for hour in starts))


PLACE_FILLER = frozenset((
    "via viale piazza piazzale largo corso vicolo strada localita loc frazione "
    "del della dei delle dello degli di da e ed il la le lo gli in al alla sp ss"
).split())


def _shares_place_word(saved, official):
    """Veto only: two venues naming no common distinctive word differ."""
    words = lambda value: {w for w in address_key(value).split()
                           if len(w) >= 3 and not w.isdigit() and w not in PLACE_FILLER}
    return bool(words(saved) & words(official))


def _town_binding_receipts(row, spec, *, today):
    return [receipt for receipt in clean_receipts(
        row.get("riscontri_campi"), row, today=today
    ) if (receipt.get("metodo") == UNIQUE_TOWN_METHOD
          and receipt.get("fonte_id") == spec["observation_source_id"]
          and receipt.get("url") == spec["url"]
          and receipt.get("ambito") == "dataset"
          and receipt.get("impronta_tipo") == "publisher_parsed_json")]


def _explicit_cadence_contradiction(raw):
    cadence = norm(raw.get("periodicita_tipo"))
    months = months_of_operation(raw.get("mesi_svolgimento"))
    return bool((cadence and cadence != "settimanale")
                or str(raw.get("frequenza_settimanale") or "").strip()
                or (months and months != set(range(1, 13))))


def _explicit_mixed_type_contradiction(raw):
    values = [raw.get(field) for field in ("n_post_alim", "n_post_non_alim", "n_post_tot")]
    if any(isinstance(value, bool) or not re.fullmatch(r"\d{1,6}", str(value)) for value in values):
        return False
    food, other, total = map(int, values)
    return bool(total > 0 and food + other == total and (food == 0 or other == 0))


def _retire_identity_contradictions(base, official, updated, context, spec, *, today,
                                    counts, touched, record_conflict):
    """Withdraw contradicted claims without rewriting a schedule or closing a market.

    A missing code, unread snapshot or unknown weekday is not a cancellation.
    Complete, ordered evidence that the same code changed its declared day,
    season, type or location can invalidate the earlier cross-source join.
    Accurate unchanged fields keep their original proof and source binding.
    If every claim is contradicted, ownership disappears with those claims;
    subsequent coincident observations cannot silently recreate that ownership.
    """
    if not context.get("read_on"):
        return
    by_source_id = defaultdict(list)
    for source in official:
        by_source_id[str(source.get("id_fonte") or "")].append(source)
    for original in base:
        old = updated[original["slug"]]
        if (old.get("regione") != spec["region"]
                or old["slug"].startswith(spec["source_prefix"])):
            continue
        days = explicit_annual_weekday(old)
        if len(days) != 1:
            continue
        day = next(iter(days))
        prior = clean_receipts(old.get("riscontri_campi"), old, today=today)
        for proof in prior:
            if (proof.get("fonte_id") != spec["observation_source_id"]
                    or proof.get("url") != spec["url"]
                    or proof.get("metodo") not in {UNIQUE_TOWN_METHOD, "sede_giorno_provincia"}
                    or proof.get("ambito") != "dataset"
                    or proof.get("impronta_tipo") != "publisher_parsed_json"
                    or context["read_on"] <= proof["letto_il"]
                    or context["sha256"] == proof["sha256"]
                    or context["source_updated_on"] < proof.get("fonte_aggiornata_il", "")):
                continue
            sid = proof["riga_fonte"]
            raw_rows = context["by_source_id"].get(sid, [])
            if not raw_rows:
                continue
            sources = by_source_id.get(sid, [])
            local = [raw for raw in raw_rows if norm(raw.get("descom")) == norm(old.get("citta"))
                     and norm(raw.get("despro")) == norm(old.get("provincia"))]
            same_day = [raw for raw in local if weekday(raw.get("giorno")) == day]
            compatible = [row for row in sources if norm(row.get("citta")) == norm(old.get("citta"))
                          and norm(row.get("provincia")) == norm(old.get("provincia"))
                          and explicit_annual_weekday(row) == days
                          and not official_identity_issue(row)
                          and _ordinary_market_compatible(row, old)]
            reason, fields = "", set()
            field_sources = sources
            if compatible:
                if (proof["metodo"] == "sede_giorno_provincia"
                        and all(location_key(row, spec["region"]) is not None
                                and street_identity(row.get("indirizzo")) != street_identity(old.get("indirizzo"))
                                for row in compatible)):
                    reason, fields = "bound_source_venue_changed", set(proof["valori"])
                else:
                    # The join can still be blocked by precise/conflicting
                    # coordinates or another source competitor. A held value
                    # must not retain an old claim explicitly contradicted by
                    # this same code. Approved updates already carry this
                    # version's receipt and fail the older-version test above.
                    reason = "bound_source_field_values_changed"
                    field_sources = compatible
            elif not local:
                reason, fields = "bound_source_municipality_changed", set(proof["valori"])
            elif not same_day and all(weekday(raw.get("giorno")) is not None for raw in local):
                reason, fields = "bound_source_weekday_changed", {"ricorrenza_testo"}
            elif same_day and all(_explicit_cadence_contradiction(raw) for raw in same_day):
                reason, fields = "bound_source_annual_recurrence_contradicted", {"ricorrenza_testo"}
            elif same_day and all(_explicit_mixed_type_contradiction(raw) for raw in same_day):
                reason, fields = "bound_source_market_type_changed", set(proof["valori"])
            else:
                continue
            if (proof["metodo"] == "sede_giorno_provincia"
                    and reason != "bound_source_field_values_changed"):
                fields = set(proof["valori"])
            # New field values from the same code can also contradict its old
            # venue/hour claims. Empty or ambiguous replacements are not used.
            for field in ("indirizzo", "orario_testo"):
                if field_sources and all(isinstance(row.get(field), str) and row[field].strip()
                                         and row[field] != old.get(field) for row in field_sources):
                    fields.add(field)
            fields &= set(proof["valori"])
            if not fields:
                continue
            revised = updated[old["slug"]]
            current = clean_receipts(revised.get("riscontri_campi"), revised, today=today)
            kept = []
            for receipt in deepcopy(current):
                if all(receipt.get(key) == proof.get(key) for key in
                       ("fonte_id", "url", "riga_fonte", "metodo", "ambito", "impronta_tipo")):
                    receipt["valori"] = {key: value for key, value in receipt["valori"].items()
                                          if key not in fields}
                kept.append(receipt)
            kept = clean_receipts(kept, revised, today=today)
            if kept == current:
                continue
            revised["riscontri_campi"] = kept
            counts["obsolete_source_claims_retired"] += 1
            counts["identity_contradiction_receipts_retired"] += 1
            counts["field_observation_records_updated"] += 1
            touched.add(old["slug"])
            evidence_source = sources[0] if sources else {
                "slug": spec["source_prefix"] + sid, "id_fonte": sid,
                "aggiornato_il": context["source_updated_on"]}
            record_conflict(old, evidence_source, reason, {
                "action": "retired_contradicted_source_claims_values_preserved",
                "retired_fields": sorted(fields), "previous_evidence": proof,
                "new_dataset_evidence": {
                    "url": spec["url"], "source_id": sid,
                    "read_on": context["read_on"], "source_updated_on": context["source_updated_on"],
                    "sha256": context["sha256"], "raw_rows_for_bound_code": deepcopy(raw_rows),
                },
            })


def _town_source_receipt(source, target, context, spec, *, today):
    """Retarget an actual raw-bound read only after the unique identity join.

    A legacy recurrence may receive evidence without being rewritten only when
    it equals one of two deterministic adapter renderings of the proved annual
    weekday. The source's raw cadence/months have already passed the strict
    identity gate; the target text is never copied as if the source said it.
    """
    for original in clean_receipts(source.get("riscontri_campi"), source, today=today):
        if (original.get("fonte_id") != spec["observation_source_id"]
                or original.get("url") != spec["url"]
                or original.get("riga_fonte") != str(source.get("id_fonte"))
                or original.get("metodo") != "id_fonte"
                or original.get("ambito") != "dataset"
                or original.get("impronta_tipo") != "publisher_parsed_json"
                or original.get("sha256") != context["sha256"]
                or original.get("fonte_aggiornata_il") != context["source_updated_on"]
                or (today - date.fromisoformat(original["letto_il"])).days > MAX_READ_AGE):
            continue
        age = (today - date.fromisoformat(original["fonte_aggiornata_il"])).days
        values = {field: value for field, value in original["valori"].items()
                  if field in {"indirizzo", "orario_testo"}
                  and age <= SOURCE_AGE[field]}
        if "orario_testo" in values and not hours_allowed(values["orario_testo"]):
            values.pop("orario_testo")
        if ("ricorrenza_testo" in original["valori"]
                and age <= SOURCE_AGE["ricorrenza_testo"]):
            day = next(iter(explicit_annual_weekday(source)))
            for rendering in ("Ogni " + DAY_LABELS[day],
                              "settimanale - " + DAY_LABELS[day]):
                if target.get("ricorrenza_testo") == rendering:
                    values["ricorrenza_testo"] = rendering
        if "indirizzo" not in values:
            continue
        item = deepcopy(original)
        item["mercato"] = identity(target)
        item["valori"] = values
        item["metodo"] = UNIQUE_TOWN_METHOD
        # Raw feed observations cannot delegate ownership across identities.
        for field in ("campi_gestiti", "gestore_campi", "versioni_precedenti"):
            item.pop(field, None)
        return item
    return None


def _enrich_unique_town(base, official, updated, context, spec, *, today,
                        counts, touched, field_updates, field_differences,
                        record_conflict, samples):
    candidates = defaultdict(list)
    for source in official:
        if (not official_identity_issue(source)
                and location_key(source, spec["region"]) is not None
                and not _replaceable_venue(source.get("indirizzo"))):
            day = next(iter(explicit_annual_weekday(source)))
            candidates[(norm(source.get("citta")),
                        str(source.get("provincia") or "").strip().upper(), day)].append(source)
    for old in base:
        if (old.get("regione") != spec["region"]
                or old["slug"].startswith(spec["source_prefix"])):
            continue
        bindings = _town_binding_receipts(old, spec, today=today)
        replacing_placeholder = _replaceable_venue(old.get("indirizzo"))
        vague_hours = address_key(old.get("orario_testo")) in DAYPARTS
        if not replacing_placeholder and not bindings and not vague_hours:
            continue
        counts["unique_town_targets_screened"] += 1
        days = explicit_annual_weekday(old)
        province = str(old.get("provincia") or "").strip().upper()
        if (len(days) != 1 or not _generic_weekly_market(old)
                or not re.fullmatch(r"[A-Z]{2}", province)):
            counts["held_unique_town_target_identity_incomplete"] += 1
            continue
        if not bindings and (old.get("verificato_il") or any(
                "indirizzo" in receipt["valori"] for receipt in
                clean_receipts(old.get("riscontri_campi"), old, today=today))):
            counts["held_unique_town_existing_venue_evidence"] += 1
            continue
        day = next(iter(days))
        key = (norm(old.get("citta")), province, day)
        eligible = [source for source in candidates.get(key, [])
                    if _ordinary_market_compatible(source, old)]
        if len(eligible) != 1:
            counts["held_unique_town_multiple_eligible_sources" if eligible
                   else "held_unique_town_no_eligible_source"] += 1
            for source in eligible:
                record_conflict(old, source, "multiple_eligible_markets_same_city_day")
            continue
        source = eligible[0]
        possible = (context["by_town_day"].get(key, [])
                    + context["by_town_day"].get((*key[:2], None), []))
        # Count raw rows, not just admitted source IDs. Malformed or duplicate
        # raw identities cannot disappear from this uniqueness proof.
        if (len(possible) != 1
                or str(possible[0][1].get("codice_id") or "").strip() != source["id_fonte"]):
            reason = ("raw_unknown_weekday_competitor" if any(
                weekday(raw.get("giorno")) is None for _, raw in possible)
                      else "raw_same_city_day_competitor")
            counts["held_unique_town_" + reason] += 1
            record_conflict(old, source, reason, {
                "raw_competitor_count": len(possible),
                "raw_competitors": [{"snapshot_row": index + 1,
                                    "source_id": str(raw.get("codice_id") or ""),
                                    "weekday": raw.get("giorno"),
                                    "periodicity": raw.get("periodicita_tipo"),
                                    "address": raw.get("indirizzi") or raw.get("ubicazione")}
                                   for index, raw in possible[:40]],
            })
            continue
        if bindings and {proof["riga_fonte"] for proof in bindings} != {source["id_fonte"]}:
            counts["held_unique_town_bound_source_identity_changed"] += 1
            record_conflict(old, source, "bound_source_identity_changed")
            continue
        gap = distance_km(old, source)
        if gap is not None and gap > MAX_DISTANCE_KM:
            counts["held_unique_town_coordinates_conflict"] += 1
            record_conflict(old, source, "coordinates_conflict")
            continue
        incoming = _town_source_receipt(source, old, context, spec, today=today)
        if incoming is None:
            counts["held_unique_town_without_current_raw_bound_receipt"] += 1
            continue
        if any((proof["letto_il"] > incoming["letto_il"]
                or (proof["letto_il"] == incoming["letto_il"]
                    and proof["sha256"] != incoming["sha256"])
                or (proof["fonte_aggiornata_il"]
                    and proof["fonte_aggiornata_il"] > incoming["fonte_aggiornata_il"]))
               for proof in bindings):
            counts["held_unique_town_source_version_unordered_or_regressed"] += 1
            continue
        if not replacing_placeholder and not bindings and not (
                _daypart_agrees(old.get("orario_testo"), incoming["valori"].get("orario_testo"))
                and _shares_place_word(old.get("indirizzo"), source.get("indirizzo"))):
            # Admitted only for its vague hours: a disagreeing daypart or a
            # different place may be another market, so attach no evidence.
            counts["held_unique_town_daypart_or_place_disagrees"] += 1
            continue
        revised = updated[old["slug"]]
        assignments = {}
        for field in ("indirizzo", "orario_testo"):
            if field not in incoming["valori"]:
                continue
            current, future = str(old.get(field) or ""), incoming["valori"][field]
            if current == future:
                continue
            # Exact official hours replace an agreeing "La mattina"; a saved
            # street sharing nothing with the official one vetoes (other market).
            missing = (not current.strip()
                       or (field == "indirizzo" and replacing_placeholder and not bindings)
                       or (field == "orario_testo" and _daypart_agrees(current, future)
                           and (replacing_placeholder
                                or _shares_place_word(old.get("indirizzo"), source.get("indirizzo")))))
            managed = managed_update_allowed(old, incoming, field,
                                             manager=FIELD_MANAGER, today=today)
            protected = (old.get("verificato_il") or
                         (field == "indirizzo" and old.get("position_quality") == "precisa"))
            if not protected and (missing or managed):
                revised[field] = future
                action = ("updated_managed_source_version" if managed else
                          "replaced_vague_placeholder" if current.strip() else "filled_missing")
                assignments[field] = action
                counter = ("managed_addresses_updated" if field == "indirizzo" else
                           "managed_hours_updated") if managed else (
                           "addresses_added" if field == "indirizzo" else "hours_added")
                counts[counter] += 1
                if action == "replaced_vague_placeholder":
                    counts["vague_addresses_replaced" if field == "indirizzo"
                           else "vague_hours_replaced"] += 1
                field_updates.append({
                    "published_id": old["slug"], "official_id": source["id_fonte"],
                    "official_slug": source["slug"], "field": field,
                    "before": current, "after": future, "match": UNIQUE_TOWN_METHOD,
                    "action": action, "raw_rows_screened": sum(
                        len(rows) for rows in context["by_town_day"].values()),
                    "new_source_evidence": deepcopy(incoming),
                    "previous_evidence": clean_receipts(old.get("riscontri_campi"), old,
                                                         today=today) if managed else [],
                })
                touched.add(old["slug"])
            else:
                counts["held_unique_town_unmanaged_" + field] += 1
                field_differences.append({
                    "published_id": old["slug"], "official_id": source["id_fonte"],
                    "official_slug": source["slug"], "field": field,
                    "before": current, "after": future,
                    "reason": ("human_verification_or_precise_location_requires_review"
                               if protected else "field_not_owned_by_same_source"),
                    "previous_evidence": clean_receipts(old.get("riscontri_campi"), old, today=today),
                    "new_source_evidence": incoming,
                    "action": "held_without_managed_update_authorization",
                })
        previous_receipts = clean_receipts(old.get("riscontri_campi"), old, today=today)
        retired = retire_superseded_receipts(old, incoming, today=today)
        if retired != previous_receipts:
            counts["obsolete_source_claims_retired"] += 1
        initial = {field for field, action in assignments.items()
                   if action != "updated_managed_source_version"}
        managed = set(assignments) - initial
        if initial:
            # Explicitly reviewed placeholders (vague venues, agreeing
            # dayparts) are the only nonempty values permitted on this path.
            incoming = mark_managed_fields(incoming, initial, manager=FIELD_MANAGER)
        if managed:
            incoming = mark_managed_fields(incoming, managed, manager=FIELD_MANAGER, previous=old)
        observations = clean_receipts([incoming, *retired], revised, today=today)
        if observations != (old.get("riscontri_campi") or []):
            revised["riscontri_campi"] = observations
            counts["field_observation_records_updated"] += 1
            touched.add(old["slug"])
        if (incoming["valori"].get("ricorrenza_testo") == old.get("ricorrenza_testo")
                and not any(proof["valori"].get("ricorrenza_testo") == old.get("ricorrenza_testo")
                            for proof in previous_receipts)):
            counts["recurrence_observations_added"] += 1
        primary = {"nome": str(old.get("fonte") or ""), "url": str(old.get("url_fonte") or "")}
        official_entry = {"nome": spec["name"], "url": spec["url"]}
        links = [dict(link) for link in (old.get("fonti") or []) if isinstance(link, dict)]
        if (primary["nome"] or primary["url"]) and primary not in links:
            links.append(primary)
        if official_entry not in links:
            links.append(official_entry)
            counts["official_source_attributions_added"] += 1
            touched.add(old["slug"])
        revised["fonti"] = links
        counts["municipality_day_unique_matches"] += 1
        if len(samples) < 30:
            samples.append({"published_id": old["slug"], "official_id": source["id_fonte"],
                            "street": source["indirizzo"], "source_day": [day],
                            "distance_km": round(gap, 3) if gap is not None else None,
                            "match": UNIQUE_TOWN_METHOD,
                            "changed_hours": "orario_testo" in assignments,
                            "changed_address": "indirizzo" in assignments})


def enrich(base, held_official, *, source_id="lombardia-mercap", today=None,
           raw_official=None):
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
    raw_context, raw_context_report = _complete_raw_context(
        raw_official, held_official, today=today)
    by_key = defaultdict(list)
    legacy_by_location = defaultdict(list)
    counts = Counter()
    identity_conflicts = []
    seen_conflicts = set()

    def record_conflict(old, source, reason, details=None):
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
            **(details or {}),
        })

    for row in base:
        if (row.get("regione") != spec["region"]
                or row["slug"].startswith(spec["source_prefix"])):
            continue
        # A venue first established by town/day uniqueness keeps that method
        # and source binding in later cycles. Missing raw context must not
        # silently switch it to the older, differently scoped venue join.
        if _town_binding_receipts(row, spec, today=today):
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
    preserved_field_differences = []
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
    if raw_context is not None:
        _enrich_unique_town(
            base, held_official, updated, raw_context, spec, today=today,
            counts=counts, touched=touched, field_updates=field_updates,
            field_differences=preserved_field_differences,
            record_conflict=record_conflict, samples=samples)
        _retire_identity_contradictions(
            base, held_official, updated, raw_context, spec, today=today,
            counts=counts, touched=touched, record_conflict=record_conflict)
    else:
        counts["unique_town_path_without_complete_raw_context"] += 1
    # The cap bounds what visitors see. Re-reading already-linked evidence on
    # a new day touches every linked record but changes no visible value, and
    # grows with coverage; it must not block the daily run.
    before = {row["slug"]: row for row in base}
    value_changes = {sid for sid in touched if any(
        updated[sid].get(field) != before[sid].get(field)
        for field in set(updated[sid]) | set(before[sid]) if field != "riscontri_campi")}
    if len(value_changes) > MAX_ENRICHED_RECORDS:
        raise ValueError("Official source enrichment exceeds per-run limit")
    return [updated[x["slug"]] for x in base], {
        "schema":1,
        "source_id":source_id,
        "source_name":spec["name"],
        "review_only":True,
        "source_rows_screened":len(held_official),
        "raw_identity_context":raw_context_report,
        "legacy_records_changed":len(touched),
        "records_with_value_changes":len(value_changes),
        "existing_market_addresses_added":int(counts["addresses_added"]),
        "vague_market_addresses_replaced":int(counts["vague_addresses_replaced"]),
        "managed_market_addresses_updated":int(counts["managed_addresses_updated"]),
        "existing_market_hours_added":int(counts["hours_added"]),
        "vague_market_hours_replaced":int(counts["vague_hours_replaced"]),
        "managed_market_hours_updated":int(counts["managed_hours_updated"]),
        "official_source_attributions_added":int(counts["official_source_attributions_added"]),
        "field_observation_records_updated":int(counts["field_observation_records_updated"]),
        "exact_matches":int(counts["exact_matches"]),
        "municipality_day_unique_matches":int(counts["municipality_day_unique_matches"]),
        "recurrence_observations_added":int(counts["recurrence_observations_added"]),
        "counts":dict(sorted(counts.items())),
        "samples":samples,
        "field_updates":field_updates,
        "preserved_hours_differences":preserved_hours_differences,
        "preserved_field_differences":preserved_field_differences,
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
        "Existing venues can receive published hours through exact street/day joins.",
        "Missing venues additionally require a unique municipality/province/weekday",
        "identity across the complete raw dataset, including nonimported competitors.",
        "Coordinates can veto a join; they never establish market identity.",
        "No forecast, human verification, original source, or identity changed.",
        "",
        f"- Held official rows screened: **{report['source_rows_screened']}**",
        f"- Existing market cards with added information: **{report['legacy_records_changed']}**",
        f"- Missing hours supplied from official regional source: **{report['existing_market_hours_added']}**",
        f"- Missing/vague venues supplied from the complete source: **{report.get('existing_market_addresses_added', 0)}**",
        f"- Managed venues updated from the same source ID: **{report.get('managed_market_addresses_updated', 0)}**",
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
    p.add_argument("--raw-official", type=Path,
                   help="Complete raw publisher payload required for unique town/day venue recovery")
    p.add_argument("--updated", type=Path,required=True)
    p.add_argument("--report", type=Path,required=True)
    p.add_argument("--summary", type=Path,required=True)
    args=p.parse_args()
    current=load_existing(args.manifest)
    candidates=json.loads(args.official.read_text("utf-8"))
    raw = json.loads(args.raw_official.read_text("utf-8")) if args.raw_official else None
    rows, report=enrich(current,candidates,raw_official=raw)
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
