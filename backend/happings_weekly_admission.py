"""Admit uniquely evidenced Happings weekly venues not already in the catalogue.

Read ONLY the weekly HTML acquired by the existing authorized crawler.
One validated city + weekday + street row and a completely unoccupied
catalogue city/day are mandatory. Ambiguities remain visible in held reasons.
No future date, exact clock time, coordinate or opening verification is made up.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date

import happings_source_enrichment as source
from happings_weekly_layout import parse, fold, WEEKDAYS, province_page_key
from field_evidence import clean_receipts, mark_managed_fields
from stored_market_sibling_proposals import safe_stored_street

MAX_NEW = 32
MAX_PAGES = source.MAX_REQUESTS_PER_RUN
DEFAULT_POLICY = {"enabled": False, "max_new": 32}


def validate_policy(policy):
    if (not isinstance(policy, dict) or set(policy) - set(DEFAULT_POLICY)
            or type(policy.get("enabled", False)) is not bool
            or type(policy.get("max_new", MAX_NEW)) is not int
            or not 1 <= policy.get("max_new", MAX_NEW) <= MAX_NEW):
        raise ValueError("Unreviewed Happings weekly admission policy")
    return {**DEFAULT_POLICY, **policy}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def stable_id(region, province, city, day):
    identity = ":".join((fold(region), province, fold(city), str(day)))
    return "happings-weekly-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:20]


def _possible_existing(row, city, region, province, day):
    if (fold(row.get("citta")) != fold(city)
            or fold(row.get("regione")) != fold(region)
            or str(row.get("provincia") or "").upper() != province):
        return False
    # Different *proved* weekdays are distinct events. Unknown or differently
    # qualified calendars remain blockers instead of becoming duplicate IDs.
    reported_day = source._cohort_weekly_day(row)
    return reported_day is None or reported_day == day


def _new_row(event, *, region, province, source_url, read_on, page_hash, page_metadata):
    city, day, street = event["city"], event["weekday"], event["place"].strip()
    source_name = f"Mercato settimanale di {city}"
    row = {
        "slug": stable_id(region, province, city, day), "nome": source_name,
        "citta": city, "provincia": province, "regione": region,
        "indirizzo": street, "lat": None, "lng": None,
        "position_quality": "sconosciuta", "categoria": "misto", "tags": [],
        "status": "non_confermato", "orario_testo": "",
        "ricorrenza_testo": "settimanale - " + WEEKDAYS[day],
        "descrizione": "", "date": [], "date_quality": "sconosciuta",
        "proiezione_regola": None, "proiezione_generata_il": "",
        "proiezione_fonte": "", "confidence": 0, "fonte": source.PUBLISHER,
        "url_fonte": source_url,
        "fonti": [{"nome": source.SOURCE_EVIDENCE_NAME, "url": source_url}],
        "verificato_il": "", "aggiornato_il": "",
        "fonte_letta_il": read_on.isoformat(), "fonte_aggiornata_il": "",
        "importato_il": read_on.isoformat(),
    }
    evidence = {
        "source_url": source_url, "source_day": day,
        "observed_at": read_on.isoformat(), "source_html_sha256": page_hash,
    }
    if page_metadata is not None:
        evidence["page_metadata"] = page_metadata
    values = {"indirizzo": street, "ricorrenza_testo": row["ricorrenza_testo"]}
    proof = source._field_receipt(row, values, evidence)
    proof = mark_managed_fields(proof, list(values), manager=source.FIELD_MANAGER)
    if clean_receipts([proof], row, today=read_on) != [proof]:
        raise ValueError("New weekly venue lost its exact publisher receipt")
    row["riscontri_campi"] = [proof]
    return row


def preview(base, pages, *, today, apply=False, max_new=MAX_NEW):
    """Return (candidate catalog, evidence), never fetch or trust invented URLs."""
    if (type(today) is not date or not isinstance(base, list)
            or len(base) > source.MAX_MARKETS or not isinstance(pages, list)
            or len(pages) > MAX_PAGES or type(apply) is not bool
            or type(max_new) is not int or not 1 <= max_new <= MAX_NEW):
        raise ValueError("Invalid Happings weekly admission batch")
    initial = [r.get("slug") if isinstance(r, dict) else None for r in base]
    if (None in initial or any(not isinstance(s, str) or not s for s in initial)
            or len(set(initial)) != len(initial)):
        raise ValueError("Weekly admission requires unique protected baseline IDs")

    counts = Counter()
    page_receipts = []
    candidates = []
    observed_ids = set(initial)
    blocked_cohorts = set()
    areas = source._official_geography()[1]
    city_to_province = source._official_geography()[0]
    found = set()
    # Index the entire catalog once. Without this, a full nationwide read
    # recomputes the weekday rules for every source row and every market.
    by_city = defaultdict(list)
    for row in base:
        area_key = (fold(row.get("regione")),
                    str(row.get("provincia") or "").strip().upper(),
                    fold(row.get("citta")))
        by_city[area_key].append((row,source._cohort_weekly_day(row)))

    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("Missing source page evidence")
        requested, final, raw = [page.get(k) for k in ("requested_url", "final_url", "html")]
        if (not source.allowed_url(requested, requested, final)
                or not isinstance(raw, bytes)
                or not 300 <= len(raw) <= source.MAX_RESPONSE_BYTES
                or province_page_key(final) in found):
            raise ValueError("Unreviewed or duplicated Happings weekly admission source")
        found.add(province_page_key(final))
        area = areas.get(province_page_key(final), set())
        if len(area) != 1:
            raise ValueError("Unproved unique Italian publisher province")
        region_key, province = next(iter(area))
        source_hash = hashlib.sha256(raw).hexdigest()
        try:
            parsed = parse(raw, source_url=final, observed_on=today)
        except ValueError:
            counts["layout_unassessed"] += 1
            page_receipts.append({"url": final, "sha256": source_hash,
                                  "status": "layout_unassessed"})
            continue
        page_receipts.append({"url": final, "sha256": source_hash,
                              "status": "parsed", "rows": len(parsed.rows)})
        counts["rows_parsed"] += len(parsed.rows)
        grouped = defaultdict(list)
        for item in parsed.rows:
            grouped[(item["city_key"], item["weekday"])].append(item)
        for cohort, entries in grouped.items():
            city_key, day = cohort
            if len(entries) != 1:
                counts["multiple_source_venues_same_city_day"] += len(entries)
                continue
            event = entries[0]
            city = event["city"]
            if event.get("calendar_scope") or (event.get("editorial_scope")
                    and event["editorial_scope"].get("status") != "current"):
                counts["source_calendar_scope_not_ordinary_weekly"] += 1
                continue
            if (event.get("has_specific_location") is not True
                    or not safe_stored_street(event.get("place"))):
                counts["source_lacks_specific_street"] += 1
                continue
            if city_to_province.get((region_key, city_key)) != province:
                counts["municipality_not_ista_verified"] += 1
                continue
            matches = [row for row, event_day in
                       by_city.get((region_key,province,city_key), [])
                       if event_day is None or event_day == day]
            if matches:
                counts["existing_catalog_identity_or_collision"] += 1
                continue
            unique = (region_key, province, city_key, day)
            if unique in blocked_cohorts:
                counts["repeated_new_cohort"] += 1
                continue
            blocked_cohorts.add(unique)
            sid = stable_id(region_key, province, city, day)
            if sid in observed_ids:
                counts["stable_id_collision"] += 1
                continue
            observed_ids.add(sid)
            row = _new_row(event, region=region_key, province=province,
                           source_url=final, read_on=today, page_hash=source_hash,
                           page_metadata=getattr(parsed, "page_metadata", None))
            candidates.append(row)
            counts["candidates_unmatched"] += 1

    result = deepcopy(base)
    applied = sorted(candidates, key=lambda r: r["slug"])[:max_new] if apply else []
    result.extend(deepcopy(applied))
    counts["new_venues_admitted"] = len(applied)
    counts["new_venues_deferred_capacity"] = len(candidates) - len(applied) if apply else len(candidates)
    report = {"schema": 1, "date": today.isoformat(), "apply": apply,
              "max_new": max_new, "input_sha256": digest(base),
              "output_sha256": digest(result), "page_receipts": page_receipts,
              "counts": dict(sorted(counts.items())),
              "candidates": candidates, "added_ids": [r["slug"] for r in applied],
              "old_ids_preserved": initial == [r["slug"] for r in result[:len(base)]],
              "exact_times_inferred": False, "event_dates_inferred": False,
              "opening_verifications_created": 0, "coordinates_created": 0}
    return result, report


def verify_changes(before, after, report, *, today, pages):
    if (not isinstance(report, dict) or report.get("schema") != 1
            or report.get("date") != today.isoformat()
            or not isinstance(pages, list)):
        raise ValueError("Untrusted weekly source admission certificate")
    expected, proof = preview(before, pages, today=today, apply=report["apply"],
                              max_new=report["max_new"])
    if (after != expected or report != proof):
        raise ValueError("Happings weekly admission is not reproduced by captured HTML")
    return True
