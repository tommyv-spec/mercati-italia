"""Audit all Happings detail-page fields against stable DEV market identities.

The snapshot owns the original HTTP URL, original HTML fingerprint and a
checksum-validated extracted fact. This pass never alters market records.
Matching requires the reviewed Happings name/venue/calendar/geography rules.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

import happings_detail_enrichment as matching
from field_evidence import published_town
from happings_full_reconciliation import _saved_page
from merge_catalog import load_existing


def audit(catalog, snapshot, *, today):
    if not isinstance(catalog, list) or type(today) is not date:
        raise ValueError("A dated, source-bound DEV catalog is required")
    snapshot = Path(snapshot)
    state = json.loads((snapshot / "checkpoint.json").read_text(encoding="utf-8"))
    queue, done = state.get("queue"), state.get("done")
    if (state.get("schema") != 1 or not isinstance(queue, list)
            or not isinstance(done, dict)
            or len(set(queue)) != len(queue)
            or not set(done).issubset(queue)):
        raise ValueError("Untrusted Happings source frontier")
    by_city = defaultdict(list)
    by_url = defaultdict(list)
    market_ids = set()
    for row in catalog:
        sid = row.get("slug") if isinstance(row, dict) else None
        if not sid or sid in market_ids:
            raise ValueError("Catalog identity is missing or repeated")
        market_ids.add(sid)
        key = (matching.fold(row.get("regione")), str(row.get("provincia") or "").upper(),
               matching.fold(published_town(row)))
        by_city[key].append(row)
        links = {row.get("url_fonte")}
        for link in row.get("fonti") or []:
            if isinstance(link, dict):
                links.add(link.get("url"))
        detail = row.get("dettaglio_fonte")
        if isinstance(detail, dict):
            links.add(detail.get("url"))
        for link in links:
            if isinstance(link, str) and link:
                by_url[link].append(row)

    counters = Counter()
    worklist = []
    example = defaultdict(list)
    for url in queue:
        metadata = done.get(url)
        if not isinstance(metadata, dict) or metadata.get("kind") != "detail":
            continue
        fact = _saved_page(snapshot, url, metadata)
        if fact.get("status") != "parsed":
            counters["event_pages_unavailable_or_unassessed"] += 1
            continue
        counters["event_pages_parsed"] += 1
        if fact.get("market_classified") is not True:
            continue
        counters["market_detail_pages_parsed"] += 1
        event = fact.get("event")
        docsource = fact.get("source")
        if (not isinstance(event, dict) or not isinstance(docsource, dict)
                or docsource.get("requested_url") != url
                or docsource.get("html_sha256") != fact.get("html_sha256")):
            raise ValueError("Happings extracted event detached from observed source")
        doc = {"event": event, "source": docsource}
        geo = matching.geography(event)
        category = matching._category(event)
        location = event.get("location") or {}
        conflicts = fact.get("conflicts") or []
        occurrences = event.get("occurrences") or []
        has_hours = bool(event.get("hours_text"))
        item = {
            "url": url, "html_sha256":fact["html_sha256"],
            "observed_at":fact["read_at"], "event_name":event.get("name"),
            "category":event.get("category"), "geo":geo,
            "street":location.get("street_address"),
            "hours_text_present":has_hours,
            "hours_interval_count":len(event.get("hours_intervals") or []),
            "source_occurrence_count":len(occurrences),
            "source_calendar_complete":event.get("calendar_complete") is True,
            "source_conflicts":len(conflicts),
        }
        if category is None:
            item["status"]="market_classification_inconsistent"
        elif geo is None:
            item["status"]="municipality_not_unique_istat"
        else:
            city, province, region = geo
            candidates = list({r["slug"]:r for r in (
                by_city.get((matching.fold(region),province,matching.fold(city)),[]) +
                by_url.get(url,[]))}.values())
            target, why, possible = matching._matches(candidates,doc,geo,today)
            item["match_method"]=why
            item["possible_existing_ids"]=sorted(r["slug"] for r in possible)[:20]
            if target is None:
                item["status"] = "ambiguous_existing_identity" if possible else "possible_new_market"
                if not possible:
                    try:
                        proposal, reason = matching._new_market(
                            doc,geo,date.fromisoformat(fact["read_at"][:10]),today)
                        item["new_market_has_complete_admission_facts"] = proposal is not None
                        item["candidate_held_reason"] = reason
                    except (ValueError, TypeError, KeyError) as error:
                        item["new_market_has_complete_admission_facts"] = False
                        item["candidate_held_reason"] = type(error).__name__
            else:
                sid=target["slug"]
                item["status"]="uniquely_matched_existing"
                item["matched_market_id"]=sid
                item["target_hours_missing"]=not bool(str(target.get("orario_testo") or "").strip())
                item["target_address_missing"]=not bool(str(target.get("indirizzo") or "").strip())
                item["target_dates_not_source_reported"]=target.get("date_quality") != "riportata"
                item["target_source_url_matches"]=target.get("url_fonte")==url
                if item["target_hours_missing"] and has_hours and not conflicts:
                    counters["matched_existing_hours_missing_in_catalog"] += 1
                if item["target_address_missing"] and location.get("street_address") and not conflicts:
                    counters["matched_existing_address_missing_in_catalog"] += 1
                if item["target_dates_not_source_reported"] and occurrences and not conflicts:
                    counters["matched_existing_source_dates_missing_in_catalog"] += 1
                counters["uniquely_matched_existing_with_hours"] += int(has_hours)
                counters["uniquely_matched_existing_with_source_dates"] += int(bool(occurrences))
        counters[item["status"]] += 1
        if conflicts:
            counters["market_details_with_source_conflicts"] += 1
        if len(example[item["status"]]) < 8:
            example[item["status"]].append({key:item.get(key) for key in (
                "url","event_name","matched_market_id","match_method",
                "candidate_held_reason","new_market_has_complete_admission_facts",
                "target_hours_missing")})
        worklist.append(item)
    result={
        "schema":1,
        "catalog_records":len(catalog),
        "source_pages_total":len(queue),
        "market_detail_pages_checked":len(worklist),
        "counts":dict(sorted(counters.items())),
        "samples":dict(example),
        "existing_record_mutations":0,
        "new_market_ids_admitted":0,
        "no_inferred_date_time_or_geography":True,
        "source_url_checksums_required":True,
    }
    return result,worklist


def run(manifest,snapshot,out,*,today=None):
    today=today or date.today()
    rows=load_existing(Path(manifest))
    summary,items=audit(rows,snapshot,today=today)
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    (out/"happings-detail-match-report.json").write_text(
        json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    (out/"happings-detail-match-worklist.json").write_text(
        json.dumps(items,ensure_ascii=False,sort_keys=True)+"\n",encoding="utf-8")
    return summary
