"""Nationwide Happings source-to-catalog reconciliation from observed page facts.

Read-only. Every source row is audited, including nonmatches, wrong provinces,
vague streets and conflicting venues. This is a factual worklist, not a market
publication, confirmation of operation, or authority to override old fields.
A second, source-HTML-bound admission/field gate is required to apply changes.

Usage:
  python backend/happings_full_reconciliation.py \
    --manifest public/data/v1/manifest.json --snapshot SNAPSHOT_DIR --out QA_DIR
"""
from __future__ import annotations

import argparse
import gzip
import io
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path

import happings_source_enrichment as source
from happings_bulk_snapshot import valid_queue
from field_evidence import published_town
from happings_weekly_layout import fold, province_page_key
from merge_catalog import load_existing
from stored_market_sibling_proposals import same_generic_venue, safe_stored_street

MAX_PAGES = 50_000
MAX_GZIP = 3_000_000
MAX_DECOMPRESSED_FACT_BYTES = 5_000_000
MAX_RECORDS = 100_000
HASH = re.compile(r"[a-f0-9]{64}\Z")


def _sha(raw):
    return hashlib.sha256(raw).hexdigest()


def _saved_page(snapshot, url, entry):
    """Fail closed if an observed page or its source provenance is altered."""
    if (not isinstance(url, str) or not isinstance(entry, dict)
            or not HASH.fullmatch(_sha(url.encode("utf-8")))
            or entry.get("status") not in {"parsed", "unassessed", "unavailable", "robots_denied"}
            or entry.get("kind") not in {"weekly", "detail", "unknown"}):
        raise ValueError("Invalid Happings checkpoint entry")
    filename = snapshot / "pages" / (_sha(url.encode("utf-8")) + ".json.gz")
    if not filename.is_file() or not 5 <= filename.stat().st_size <= MAX_GZIP:
        raise ValueError("Missing or oversized Happings source fact file: " + url)
    raw = filename.read_bytes()
    if _sha(raw) != entry.get("facts_sha256"):
        raise ValueError("Modified Happings fact-file hash: " + url)
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(raw)) as compressed:
            decoded=compressed.read(MAX_DECOMPRESSED_FACT_BYTES+1)
        if len(decoded)>MAX_DECOMPRESSED_FACT_BYTES:
            raise ValueError("Unbounded decompressed Happings fact file")
        fact=json.loads(decoded)
    except (OSError, ValueError, UnicodeError) as error:
        raise ValueError("Corrupt or oversized Happings fact file") from error
    if (not isinstance(fact, dict) or fact.get("url") != url
            or fact.get("status") != entry["status"]
            or (fact.get("kind", "unknown") != entry["kind"])
            or not isinstance(fact.get("read_at"), str)):
        raise ValueError("Happings fact detached from its original URL")
    if fact.get("status") in {"parsed", "unassessed"} and (
            not HASH.fullmatch(str(fact.get("html_sha256") or ""))
            or type(fact.get("bytes")) is not int or fact["bytes"] <= 0):
        raise ValueError("Happings page lost source HTML hash")
    return fact


def _base_catalog(markets):
    if not isinstance(markets, list) or len(markets) > MAX_RECORDS:
        raise ValueError("Unbounded comparison catalog")
    by_day = defaultdict(list)
    uncertain = defaultdict(list)
    for row in markets:
        if not isinstance(row, dict) or not row.get("slug"):
            raise ValueError("Catalog has missing market identity")
        area = (fold(row.get("regione")),
                str(row.get("provincia") or "").strip().upper(),
                fold(published_town(row)))
        day = source._cohort_weekly_day(row)
        if day is None:
            uncertain[area].append(row)
        else:
            by_day[(*area,day)].append(row)
    return by_day, uncertain


def _safe_date(stamp):
    if not isinstance(stamp, str):
        return False
    try:
        d = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
        return d.tzinfo is not None and d.date() <= date.today()
    except ValueError:
        return False


def _categorize(ident, readings, by_day, uncertain, municipalities):
    region, province, city, weekday = ident
    originals = [row for _,row in readings]
    source_urls = sorted(set(url for url,_ in readings))
    places = {fold(row.get("place")) for row in originals}
    actual_province = municipalities.get((region,city))
    indexed_provinces = sorted({
        row.get("_source_page_province", province) for row in originals})
    incorrect_source_province = (
        actual_province is not None
        and any(p != actual_province for p in indexed_provinces))
    all_source_pages_mislabelled = (
        incorrect_source_province
        and all(p != actual_province for p in indexed_provinces))
    base = {"region":region, "province":province, "city":city,
            "weekday":weekday, "urls":source_urls,
            "places": sorted(places), "source_rows":len(readings),
            "source_page_provinces":indexed_provinces,
            "actual_istat_province":actual_province,
            "source_province_mislabelled":incorrect_source_province}
    if actual_province is None:
        return {**base,"outcome":"source_city_not_istat_resolved"}
    if actual_province != province:
        raise ValueError("Source row was not grouped under its verified ISTAT province")
    if len(places) > 1:
        return {**base,"outcome":"ambiguous_multiple_source_streets"}
    if any(row.get("calendar_scope") for row in originals):
        return {**base,"outcome":"source_calendar_qualified"}
    if any(row.get("editorial_scope") and row["editorial_scope"].get("status") != "current"
           for row in originals):
        return {**base,"outcome":"historical_or_unverified_section"}
    street = originals[0].get("place")
    precise = bool(all(row.get("has_specific_location") for row in originals)
                   and isinstance(street, str) and safe_stored_street(street))
    current = by_day.get(ident, [])
    unknown = uncertain.get((region,province,city), [])
    primary = [r for r in current if r.get("fonte") == source.PUBLISHER
               and same_generic_venue(r)]
    saved_address = {fold(r.get("indirizzo")) for r in current if str(r.get("indirizzo") or "").strip()}
    base.update(street=street, has_specific_location=precise,
                existing_ids=sorted(r["slug"] for r in current),
                existing_primary_happings_ids=sorted(r["slug"] for r in primary),
                uncertain_calendar_ids=sorted(r["slug"] for r in unknown)[:10])
    if not precise:
        return {**base,"outcome":"source_location_vague"}
    if len(current) == 0:
        if unknown:
            return {**base,"outcome":"new_blocked_unknown_existing_calendar"}
        if all_source_pages_mislabelled:
            return {**base,"outcome":"new_venue_bad_source_province_needs_second_confirmation"}
        return {**base,"outcome":"new_venue_possible_needs_source_html_admission"}
    if len(primary) != 1 or len(current) != 1:
        if any(fold(r.get("indirizzo")) == fold(street) for r in current):
            return {**base,"outcome":"existing_location_supported_but_identity_ambiguous"}
        return {**base,"outcome":"existing_market_identity_ambiguous"}
    row = primary[0]
    existing_street = str(row.get("indirizzo") or "").strip()
    if not existing_street:
        if all_source_pages_mislabelled:
            return {**base,"outcome":"existing_blank_address_bad_source_province_needs_review"}
        return {**base,"outcome":"existing_blank_address_recoverable_by_live_reader"}
    if fold(existing_street) == fold(street):
        return {**base,"outcome":"existing_address_supported"}
    return {**base,"outcome":"existing_address_conflict_requires_source_review"}


def analyze(manifest, snapshot, out):
    manifest, snapshot, out = map(Path, (manifest,snapshot,out))
    state = json.loads((snapshot / "checkpoint.json").read_text("utf-8"))
    queue = state.get("queue")
    saved = state.get("done")
    if (state.get("schema") != 1 or not isinstance(queue, list)
            or not 1 <= len(queue) <= MAX_PAGES or len(set(queue)) != len(queue)
            or not isinstance(saved, dict) or not set(saved).issubset(queue)):
        raise ValueError("Invalid Happings bulk snapshot checkpoint")
    valid_queue(queue)

    catalog = load_existing(manifest)
    h_rows = [row for row in catalog if row.get("fonte") == source.PUBLISHER]
    catalog_fields = {
        "records":len(h_rows),
        "addresses_blank":sum(not str(row.get("indirizzo") or "").strip() for row in h_rows),
        "addresses_specific":sum(safe_stored_street(row.get("indirizzo")) for row in h_rows),
        "hours_text_available":sum(bool(str(row.get("orario_testo") or "").strip()) for row in h_rows),
        "recurrence_text_available":sum(bool(str(row.get("ricorrenza_testo") or "").strip()) for row in h_rows),
        "dates_source_reported":sum(row.get("date_quality") == "riportata" for row in h_rows),
        "dates_predicted":sum(row.get("date_quality") == "prevista" for row in h_rows),
    }
    original_ids = [item["slug"] for item in catalog]
    if len(original_ids) != len(set(original_ids)):
        raise ValueError("Duplicate catalog identities before reconciliation")
    by_day, unknown = _base_catalog(catalog)
    provinces = source._official_geography()[1]
    municipalities = source._official_geography()[0]
    groups = defaultdict(list)
    page_metrics = Counter()
    event_metrics = Counter()
    event_examples = []
    failed_pages = []
    daily_urls = set()
    pages_by_scope = defaultdict(list)
    weekly_dayparts = Counter()

    for url in queue:
        if url not in saved:
            continue
        fact = _saved_page(snapshot,url,saved[url])
        status = fact["status"]
        page_metrics["processed_"+status] += 1
        if not _safe_date(fact["read_at"]):
            raise ValueError("Happings source observation has invalid UTC date")
        if status != "parsed":
            failed_pages.append({"url":url,"status":status,
                                 "error":fact.get("parse_error",fact.get("error"))})
            continue
        if fact.get("kind") == "weekly":
            page_metrics["weekly_pages_parsed"] += 1
            page_scope = provinces.get(province_page_key(url),set())
            if len(page_scope) != 1:
                raise ValueError("Unreconciled Happings province URL")
            region, province = next(iter(page_scope))
            pages_by_scope[(region,province)].append(url)
            rows = fact.get("markets")
            if not isinstance(rows, list) or len(rows) > 2200:
                raise ValueError("Happings source market rows invalid")
            if len(rows) != fact.get("source_rows"):
                raise ValueError("Happings summary lost parsed source rows")
            for row in rows:
                if (not isinstance(row,dict) or not isinstance(row.get("city"),str)
                        or type(row.get("weekday")) is not int
                        or not 0 <= row["weekday"] <= 6
                        or not isinstance(row.get("place"),str)):
                    raise ValueError("Invalid observed market row")
                city = fold(row["city"])
                actual_province = municipalities.get((region,city))
                if actual_province is None:
                    page_metrics["weekly_rows_city_not_istat_resolved"] += 1
                elif actual_province != province:
                    page_metrics["weekly_rows_source_province_mislabelled"] += 1
                else:
                    page_metrics["weekly_rows_source_province_matches_istat"] += 1
                # Keep the publisher's page heading as evidence but match a
                # resolved municipality against its real ISTAT province.
                # A wrong publisher heading must never change a catalog
                # record's official region or province.
                ident = (region,actual_province or province,city,row["weekday"])
                groups[ident].append((url,{**row,"_source_page_province":province}))
                page_metrics["weekly_source_rows"] += 1
                weekly_dayparts[str(row.get("daypart") or "not_supplied")] += 1
        elif fact.get("kind") == "detail":
            page_metrics["detail_pages_parsed"] += 1
            if fact.get("market_classified") is True:
                event_metrics["detail_events_recognized_as_market"] += 1
                event = fact.get("event") or {}
                location = event.get("location") or {}
                if location.get("street_address"):
                    event_metrics["detail_markets_with_street"] += 1
                if event.get("hours_text"):
                    event_metrics["detail_markets_with_hours_text"] += 1
                if event.get("hours_intervals"):
                    event_metrics["detail_markets_with_hours_intervals"] += 1
                if event.get("occurrences"):
                    event_metrics["detail_markets_with_explicit_occurrences"] += 1
                if fact.get("conflicts"):
                    event_metrics["detail_markets_with_source_conflict"] += 1
                if len(event_examples) < 12:
                    event_examples.append({"url":url,"name":event.get("name"),
                        "city":location.get("city"),"hours":bool(event.get("hours_text")),
                        "occurrences":len(event.get("occurrences") or [])})

    worklist = []
    outcomes = Counter()
    samples = defaultdict(list)
    for ident, group in sorted(groups.items()):
        item = _categorize(ident,group,by_day,unknown,municipalities)
        worklist.append(item)
        outcomes[item["outcome"]] += 1
        if len(samples[item["outcome"]]) < 12:
            samples[item["outcome"]].append(item)
    totals = {
        "schema":1,
        "scope":"all completed Happings source pages, not proof of an individually verified opening",
        "snapshot_started_at":state.get("started_at"),
        "snapshot_pages_total":len(queue),
        "snapshot_pages_completed":len(saved),
        "snapshot_pages_pending":len(queue)-len(saved),
        "catalog_records":len(catalog),
        "catalog_happings_primary_records":len(h_rows),
        "catalog_happings_field_coverage":catalog_fields,
        "observed_weekly_dayparts":dict(sorted(weekly_dayparts.items())),
        "observed_source_pages":dict(sorted(page_metrics.items())),
        "observed_detail_market_fields":dict(sorted(event_metrics.items())),
        "unique_weekly_city_day_groups":len(groups),
        "outcomes":dict(sorted(outcomes.items())),
        "existing_catalog_ids_preserved":len(original_ids),
        "existing_catalog_id_mutations":0,
        "new_catalog_ids_admitted":0,
        "source_errors":failed_pages[:40],
        "samples":samples,
        "sample_detail_market_events":event_examples,
        "source_province_pages_with_identical_istat_scope":{
           ":".join(area):len(pages) for area,pages in pages_by_scope.items() if len(pages)>1
        },
        "coverage_note":"Publisher source may have no exact hours or future dates. Qualitative dayparts are not clock times.",
    }
    out.mkdir(parents=True,exist_ok=True)
    (out/"happings-source-worklist.json").write_text(
        json.dumps(worklist,ensure_ascii=False,sort_keys=True)+"\n","utf-8")
    (out/"happings-source-reconciliation.json").write_text(
        json.dumps(totals,ensure_ascii=False,indent=2,sort_keys=True)+"\n","utf-8")
    return totals


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest",required=True)
    p.add_argument("--snapshot",required=True)
    p.add_argument("--out",required=True)
    a = p.parse_args()
    result = analyze(a.manifest,a.snapshot,a.out)
    print(json.dumps({k:result[k] for k in (
        "snapshot_pages_total","snapshot_pages_completed","snapshot_pages_pending",
        "catalog_records","catalog_happings_primary_records",
        "unique_weekly_city_day_groups","outcomes",
        "observed_source_pages","observed_detail_market_fields")},
        ensure_ascii=False,indent=2))


if __name__ == "__main__":
    main()
