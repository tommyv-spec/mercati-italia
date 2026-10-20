"""Exact existing-record Citynews observations, separate from current truth.

An observed event edition never becomes an annual recurrence. This adapter
cannot add IDs, repair catalog geography or rename a market. A changed title,
edition or primary URL is a held join, including observed HTTP redirects.
"""
from __future__ import annotations

import json
import re
from collections import defaultdict
from copy import deepcopy
from datetime import date
from functools import lru_cache
from pathlib import Path

from citynews_layout import MAX_BYTES, parse_detail
from citynews_urls import source_identity
from editorial_calendar_scope import (
    KEY, apply_editorial_scope, blank_province_venue_or_title, build_evidence,
    calendar_conflicted, clean_editorial_evidence, geography_matches,
    istat_geography, text_key, valid_editorial_reported_dates,
)
from field_evidence import (
    FIELDS, as_day, clean_receipts, fingerprint, make_receipt,
    managed_update_allowed, mark_managed_fields, retire_superseded_receipts,
)

MANAGER = "citynews_detail"
MAX_DOCUMENTS = 64
MUTABLE = {"indirizzo", "orario_testo", KEY, "riscontri_campi", "date", "date_quality",
           "proiezione_regola", "proiezione_generata_il", "proiezione_fonte"}
SOURCE_KEYS = {"publisher", "source_id", "requested_url", "final_url", "canonical_url",
               "html_sha256", "bytes", "published_at", "modified_at", "hash_basis",
               "redirect_observed"}


def catalog_urls(rows):
    return sorted({r["url_fonte"] for r in rows if source_identity(r.get("url_fonte"))})


@lru_cache(maxsize=1)
def _regions():
    values = json.loads((Path(__file__).resolve().parent / "data/istat-comuni-2026.json").read_text())
    return {text_key(name): name for name in values["provinces_by_region"]}


def _normalized_location(observed):
    if text_key(observed.get("country")) not in {"", "it", "ita", "italia", "italy"}:
        return None
    city = text_key(observed.get("city"))
    province = str(observed.get("province") or "")
    region = text_key(observed.get("region"))
    candidates = [v for v in istat_geography() if v[0] == city
                  and (not region or v[2] == region)
                  and (not province or v[1] == province.upper())]
    if len(candidates) != 1:
        return None
    _, province, region = candidates[0]
    return {**observed, "province": province, "region": _regions()[region]}


def parse_document(blob, *, requested_url, final_url=None, today=None):
    """Keep raw observed locality and derive only unique ISTAT geography."""
    document = parse_detail(blob, requested_url=requested_url, final_url=final_url)
    event = document["event"]
    event["observed_location"] = deepcopy(event["location"])
    if document["status"] == "unsupported":
        return document
    normalized = _normalized_location(event["observed_location"])
    if normalized is None:
        document["conflicts"].append({"field": "identity", "code": "istat_geography_unresolved"})
        document["status"] = "held"
        event["calendar_complete"] = False
    else:
        event["location"] = normalized
    return document


def _valid_document(document, read_on, today):
    if (not isinstance(today, date) or not as_day(read_on)
            or not 0 <= (today - as_day(read_on)).days <= 45
            or not isinstance(document, dict) or set(document) != {
                "schema", "status", "source", "event", "conflicts", "warnings", "field_evidence"}
            or document.get("schema") != 1 or document.get("status") not in {"parsed", "held", "unsupported"}
            or not isinstance(document.get("source"), dict)
            or not isinstance(document.get("event"), dict)
            or not isinstance(document.get("conflicts"), list)
            or any(not isinstance(c, dict) or c.get("field") not in {"identity", "address", "hours", "calendar"}
                   for c in document["conflicts"])
            or not isinstance(document.get("warnings"), list)
            or not isinstance(document.get("field_evidence"), dict)):
        raise ValueError("Invalid bounded Citynews source document")
    source = document["source"]
    expected = source_identity(source.get("requested_url"))
    final = source_identity(source.get("final_url"))
    if (set(source) != SOURCE_KEYS or expected is None or final is None
            or final[0] != expected[0] or expected != (source.get("publisher"), source.get("source_id"))
            or type(source.get("redirect_observed")) is not bool
            or source["redirect_observed"] != (source["requested_url"] != source["final_url"])
            or not re.fullmatch(r"[0-9a-f]{64}", str(source.get("html_sha256") or ""))
            or type(source.get("bytes")) is not int or not 100 <= source["bytes"] <= MAX_BYTES
            or source.get("hash_basis") != "http_response_bytes"
            or source.get("modified_at") is not None
            or len(json.dumps(document, ensure_ascii=False).encode("utf-8")) > 64_000):
        raise ValueError("Citynews source proof changed identity, bound or publication semantics")
    event = document["event"]
    if document["status"] != "unsupported":
        observed = event.get("observed_location")
        normalized = _normalized_location(observed) if isinstance(observed, dict) else None
        if normalized is not None and event.get("location") != normalized:
            raise ValueError("Citynews derived geography differs from observed ISTAT locality")
        if normalized is None and not any(c.get("field") == "identity" for c in document["conflicts"]):
            raise ValueError("Unresolved Citynews locality lacks its identity hold")
    return source


def _select(row, document):
    event, source = document["event"], document["source"]
    if document["status"] == "unsupported":
        return "source_layout_unsupported"
    if source["requested_url"] != row.get("url_fonte") or source["final_url"] != source["requested_url"]:
        return "source_exact_url_changed"
    if source["canonical_url"] != source["requested_url"] or any(c.get("field") == "identity" for c in document["conflicts"]):
        return "source_identity_conflict"
    if not text_key(event.get("name")) or text_key(row.get("nome")) != text_key(event["name"]):
        return "source_exact_title_changed"
    if not geography_matches(row, event.get("location") or {}):
        return "source_geography_not_established"
    if not blank_province_venue_or_title(row, event):
        return "missing_province_requires_specific_exact_title_or_venue"
    if any("\ufffd" in str(v) for v in (event.get("name"), event["location"].get("city"), event["location"].get("address"))):
        return "source_text_encoding_damage"
    if any(c.get("field") == "address" for c in document["conflicts"]):
        return "source_venue_ambiguous"
    return None


def _held(row, reason):
    return row, {"slug": row["slug"], "status": "held", "reason": reason, "fields": []}


def _update(row, document, *, read_on, today):
    hold = _select(row, document)
    if hold:
        return _held(row, hold)
    event, source = document["event"], document["source"]
    previous = clean_editorial_evidence(row.get(KEY), row, today=today)
    if row.get(KEY) is not None and previous is None:
        return _held(row, "invalid_previous_editorial_evidence")
    if previous and previous["facts"].get("edition_intervals") != event.get("edition_intervals"):
        return _held(row, "source_edition_identity_changed")
    mode = "limit_forecasts"
    if (event.get("occurrences") and event.get("calendar_complete") and not event.get("archive_marker")
            and not calendar_conflicted(document["conflicts"])
            and not row.get("verificato_il") and not row.get("calendario_fonte")
            and (row.get("date_quality") not in {"confermata", "riportata"}
                 or previous and previous["calendar_mode"] == "reported_explicit")):
        mode = "reported_explicit"
    try:
        evidence = build_evidence(row, document, read_on=read_on, calendar_mode=mode)
    except (ValueError, TypeError, KeyError):
        return _held(row, "source_evidence_not_bindable")
    if previous and (evidence["read_on"] < previous["read_on"]
            or evidence["read_on"] == previous["read_on"] and evidence["source_sha256"] != previous["source_sha256"]):
        return _held(row, "source_version_ordering_not_proven")
    intervals = event.get("edition_intervals") or []
    historical = bool(intervals and all(i["end"] < today.isoformat() for i in intervals))
    proposed = {}
    # Bounds are the edition identity, not daily openings. Old/unknown or
    # conflicted editions cannot promote historical hours into current fields.
    if (intervals and not historical and not calendar_conflicted(document["conflicts"])
            and not any(v.get("status") in {"cancelled", "postponed"} for v in event.get("occurrences") or [])):
        for target, value, field in (("indirizzo", event["location"].get("address"), "address"),
                                     ("orario_testo", event.get("hours_text"), "hours")):
            if (isinstance(value, str) and value.strip() and len(value) <= FIELDS[target]
                    and not any(c.get("field") == field for c in document["conflicts"])):
                proposed[target] = value
    result = deepcopy(row)
    accepted, assigned, updated, holds = {}, [], [], []
    latest = None
    if proposed:
        latest = make_receipt({**row, **proposed}, values=proposed,
            source_url=row["url_fonte"], source_name=source["publisher"],
            source_id=source["source_id"], source_row=source["source_id"] + ":event-card",
            read_on=read_on, source_updated_on="", source_sha256=source["html_sha256"],
            scope="pagina", method="pagina_primaria_revisionata", fingerprint_kind="html_bytes")
        # A conflicting existing address is an identity hold unless this
        # exact engine proves a later owned correction for the same edition.
        current_address = str(row.get("indirizzo") or "")
        incoming_address = proposed.get("indirizzo")
        if (current_address and incoming_address and text_key(current_address) != text_key(incoming_address)
                and not managed_update_allowed(row, latest, "indirizzo", manager=MANAGER, today=today)):
            return _held(row, "existing_venue_conflict")
        for field, value in proposed.items():
            current = row.get(field) or ""
            if current == value:
                accepted[field] = value
            elif row.get("verificato_il") or field == "indirizzo" and row.get("position_quality") == "precisa":
                holds.append({"field": field, "reason": "human_verification_or_precise_location"})
            elif not current:
                result[field] = value; accepted[field] = value; assigned.append(field)
            elif managed_update_allowed(row, latest, field, manager=MANAGER, today=today):
                result[field] = value; accepted[field] = value; updated.append(field)
            else:
                holds.append({"field": field, "reason": "existing_field_not_owned_or_conflicting"})
        kept = retire_superseded_receipts(row, latest, today=today)
        if accepted:
            receipt = {**latest, "valori": accepted}
            if assigned:
                receipt = mark_managed_fields(receipt, assigned, manager=MANAGER)
            if updated:
                receipt = mark_managed_fields(receipt, updated, manager=MANAGER, previous=row)
            result["riscontri_campi"] = clean_receipts([*kept, receipt], result, today=today)
        elif kept != clean_receipts(row.get("riscontri_campi"), row, today=today):
            result["riscontri_campi"] = kept
    result[KEY] = evidence
    result, calendar_disposition = apply_editorial_scope(result, today=today)
    fields = sorted(k for k in set(row) | set(result) if row.get(k) != result.get(k))
    return result, {"slug": row["slug"], "status": "changed" if fields else "observed",
        "reason": "exact_url_title_municipality_and_edition", "fields": fields,
        "accepted_fields": accepted, "field_holds": holds, "historical_edition": historical,
        "calendar_mode": mode, "calendar_disposition": calendar_disposition,
        "before_sha256": fingerprint(row), "after_sha256": fingerprint(result)}


def _reconcile(rows, documents, *, today):
    result, outcomes, seen = deepcopy(rows), [], set()
    by_url = defaultdict(list)
    for i, row in enumerate(rows):
        by_url[row.get("url_fonte")].append(i)
    for observed in documents:
        if not isinstance(observed, dict) or set(observed) != {"read_on", "parsed"}:
            raise ValueError("Citynews source observation lost its acquisition date")
        doc, read_on = observed["parsed"], observed["read_on"]
        source = _valid_document(doc, read_on, today)
        url = source["requested_url"]
        if url in seen or url not in by_url:
            raise ValueError("Repeated or non-catalog Citynews primary URL")
        seen.add(url)
        indexes = by_url[url]
        eligible = [i for i in indexes if _select(rows[i], doc) is None]
        for index in indexes:
            if index in eligible and len(eligible) > 1:
                result[index], outcome = _held(rows[index], "multiple_exact_catalog_candidates")
            else:
                result[index], outcome = _update(rows[index], doc, read_on=read_on, today=today)
            outcomes.append({"url": url, **outcome})
    return result, outcomes


def preview(rows, documents, *, today):
    if (not isinstance(documents, list) or len(documents) > MAX_DOCUMENTS
            or len({r.get("slug") for r in rows}) != len(rows) or any(not r.get("slug") for r in rows)):
        raise ValueError("Unbounded Citynews batch or repeated catalog identities")
    result, outcomes = _reconcile(rows, documents, today=today)
    report = {"schema": 1, "publisher": "citynews", "date": today.isoformat(),
        "input_sha256": fingerprint(rows), "output_sha256": fingerprint(result),
        "documents": deepcopy(documents), "outcomes": outcomes,
        "changed_existing_ids": [v["slug"] for v in outcomes if v["status"] == "changed"],
        "new_market_ids": [], "removed_market_ids": [], "individual_openings_confirmed": 0,
        "coordinates_assigned": 0}
    verify_changes(rows, result, report, today=today)
    return result, report


def verify_changes(before, after, report, *, today):
    if (not isinstance(report, dict) or report.get("schema") != 1 or report.get("publisher") != "citynews"
            or report.get("date") != today.isoformat() or report.get("new_market_ids") != []
            or report.get("removed_market_ids") != [] or report.get("individual_openings_confirmed") != 0
            or report.get("coordinates_assigned") != 0
            or report.get("input_sha256") != fingerprint(before) or report.get("output_sha256") != fingerprint(after)
            or not isinstance(report.get("documents"), list) or len(report["documents"]) > MAX_DOCUMENTS
            or len({r.get("slug") for r in before}) != len(before)
            or [r.get("slug") for r in before] != [r.get("slug") for r in after]):
        raise ValueError("Invalid Citynews source candidate proof")
    expected, outcomes = _reconcile(before, report["documents"], today=today)
    if expected != after or outcomes != report.get("outcomes") or report.get("changed_existing_ids") != [
            v["slug"] for v in outcomes if v["status"] == "changed"]:
        raise ValueError("Citynews changes cannot be reconstructed from observed facts")
    if any({k for k in set(old) | set(new) if old.get(k) != new.get(k)} - MUTABLE for old, new in zip(before, after)):
        raise ValueError("Citynews refresh changed an immutable catalog field")
    return {"release_safe": True, "retained_ids": len(before), "new_ids": 0,
            "changed_existing_ids": len(report["changed_existing_ids"])}


def verify_exported(rows, report, *, today):
    catalog = {row["slug"]: row for row in rows}
    if len(catalog) != len(rows):
        raise ValueError("Citynews export repeats a catalog identity")
    documents = {v["parsed"]["source"]["requested_url"]: v for v in report.get("documents", [])}
    checked = 0
    for outcome in report.get("outcomes", []):
        if outcome["status"] == "held":
            continue
        row, observed = catalog.get(outcome["slug"]), documents.get(outcome["url"])
        if row is None or observed is None:
            raise ValueError("Citynews source or existing identity disappeared from export")
        _valid_document(observed["parsed"], observed["read_on"], today)
        evidence = clean_editorial_evidence(row.get(KEY), row, today=today)
        if (_select(row, observed["parsed"]) is not None or evidence is None
                or evidence != build_evidence(row, observed["parsed"], read_on=observed["read_on"],
                                               calendar_mode=outcome["calendar_mode"])):
            raise ValueError("Exported Citynews facts differ from the exact observed event")
        for field, value in outcome["accepted_fields"].items():
            if row.get(field) != value or not any(r["url"] == outcome["url"]
                    and r["sha256"] == evidence["source_sha256"] and r["letto_il"] == evidence["read_on"]
                    and r["fonte_aggiornata_il"] == "" and r["valori"].get(field) == value
                    for r in clean_receipts(row.get("riscontri_campi"), row, today=today)):
                raise ValueError("Citynews field lost its exact value or source-date semantics")
        scoped, _ = apply_editorial_scope(row, today=today)
        if any(row.get(k) != scoped.get(k) for k in ("date", "date_quality", "proiezione_regola",
                                                   "proiezione_generata_il", "proiezione_fonte")):
            raise ValueError("Export reanimated openings beyond the Citynews edition")
        if (evidence["calendar_mode"] == "reported_explicit" and row.get("date_quality") == "riportata"
                and not valid_editorial_reported_dates(row, today=today)):
            raise ValueError("Citynews reported dates lack explicit source proof")
        checked += 1
    return {"release_safe": True, "editorial_identities_checked": checked}


def verify_source_pages(pages, documents, *, today):
    """Acquisition/checkpoint guard: replay bytes, not self-reported hashes."""
    if not isinstance(pages, list) or len(pages) > MAX_DOCUMENTS or len(pages) != len(documents):
        raise ValueError("Citynews source bytes and parsed documents differ")
    seen = set()
    for page, observed in zip(pages, documents):
        if not isinstance(page, dict) or set(page) != {"requested_url", "final_url", "read_on", "html"}:
            raise ValueError("Invalid Citynews captured page proof")
        if page["requested_url"] in seen:
            raise ValueError("Repeated Citynews captured source URL")
        seen.add(page["requested_url"])
        expected = {"read_on": page["read_on"], "parsed": parse_document(page["html"],
            requested_url=page["requested_url"], final_url=page["final_url"], today=today)}
        _valid_document(expected["parsed"], expected["read_on"], today)
        if observed != expected:
            raise ValueError("Citynews saved facts differ from captured HTTP bytes")
    return {"source_pages_replayed": len(pages), "release_safe": True}
