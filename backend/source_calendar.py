"""Bounded, identity-bound source calendars and detail facts.

Explicit publisher dates remain reported dates. A saved page is neither a
human confirmation nor permission to extend its calendar into another year.
This module has no crawler, exporter or catalogue imports.
"""
from __future__ import annotations

import json
import math
import re
from copy import deepcopy
from datetime import date, timedelta
from urllib.parse import urlsplit
from happings_detail_urls import detail_url as valid_detail_url

from field_evidence import as_day, clean_exceptions, identity

MANAGER = "happings-detail"
MAX_OCCURRENCES = 600
MAX_FUTURE_DAYS = 550
MAX_DETAIL_BYTES = 24_000
DETAIL_FIELDS = {"name", "category", "source_id", "location", "hours_text",
                 "hours_intervals", "recurrence_text", "description",
                 "organizer", "contacts", "geo", "event_status", "calendar_notes",
                 "hours_qualifications", "sidebar_hours_text", "visible_location",
                 "calendar_complete", "calendar_scope", "conditions", "subevents",
                 "all_day", "schema_interval", "hours_scope", "source_links", "admission_text"}


def detail_url(value):
    return valid_detail_url(value)


def _provenance(value, row, today):
    if (not isinstance(today, date) or not isinstance(value, dict)
            or value.get("schema") != 1 or value.get("gestore") != MANAGER
            or value.get("mercato") != identity(row)
            or not detail_url(value.get("url"))
            or not detail_url(value.get("url_richiesto"))
            or not isinstance(value.get("fonte_id"), str)
            or not 1 <= len(value["fonte_id"]) <= 100
            or not re.fullmatch(r"[0-9a-f]{64}", str(value.get("sha256") or ""))):
        return False
    read = as_day(value.get("letto_il"))
    updated = as_day(value.get("fonte_aggiornata_il"))
    published = as_day(value.get("fonte_pubblicata_il"))
    return bool(read and read <= today
                and (not value.get("fonte_aggiornata_il") or updated and updated <= read)
                and (not value.get("fonte_pubblicata_il") or published and published <= read))


def _clock(value):
    return value is None or isinstance(value, str) and bool(
        re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value))


def clean_source_calendar(value, row, *, today):
    """Return the complete calendar only if every occurrence is intact."""
    if not _provenance(value, row, today):
        return None
    occurrences = value.get("occorrenze")
    if value.get("ambito_calendario") not in {"explicit_visible_list", "schema_occurrence_only"}:
        return None
    intervals = value.get("intervalli", [])
    if not isinstance(intervals, list) or len(intervals) > 100:
        return None
    interval_keys = set()
    for interval in intervals:
        if not isinstance(interval, dict) or set(interval) - {
                "start", "end", "start_time", "end_time", "hours_scope",
                "continuous_opening_confirmed", "status", "evidence"}:
            return None
        start, end = as_day(interval.get("start")), as_day(interval.get("end"))
        evidence = interval.get("evidence")
        if (not start or not end or not 0 <= (end - start).days <= 60
                or interval.get("hours_scope") != "interval_boundaries"
                or interval.get("continuous_opening_confirmed") is not False
                or interval.get("status", "source_listed") not in {
                    "source_listed", "cancelled", "postponed", "rescheduled"}
                or not _clock(interval.get("start_time")) or not _clock(interval.get("end_time"))
                or not isinstance(evidence, list) or not 1 <= len(evidence) <= 12
                or any(not isinstance(e, str) or not 1 <= len(e) <= 240 for e in evidence)):
            return None
        interval_keys.add((interval["start"], interval["end"]))
    if len(interval_keys) != len(intervals):
        return None
    if not isinstance(occurrences, list) or not 1 <= len(occurrences) <= MAX_OCCURRENCES:
        return None
    result, seen = [], set()
    for item in occurrences:
        if not isinstance(item, dict) or set(item) - {
                "date", "start_time", "end_time", "status", "evidence", "note",
                "interval_start", "interval_end"}:
            return None
        day = as_day(item.get("date"))
        evidence = item.get("evidence")
        if (not day or not 2000 <= day.year <= 2100
                or item.get("status") not in {"source_listed", "cancelled", "postponed", "rescheduled"}
                or not _clock(item.get("start_time"))
                or not _clock(item.get("end_time"))
                or not isinstance(evidence, list) or not 1 <= len(evidence) <= 12
                or any(not isinstance(e, str) or not 1 <= len(e) <= 240 for e in evidence)
                or item.get("note") is not None and (
                    not isinstance(item["note"], str) or len(item["note"]) > 500)):
            return None
        associated = (item.get("interval_start"), item.get("interval_end"))
        if any(associated) and (associated not in interval_keys or not
                as_day(associated[0]) <= day <= as_day(associated[1])):
            return None
        if item.get("end_time") is not None and item.get("start_time") is None and (
                not all(associated) or item["date"] != item.get("interval_end")):
            return None
        # One source date can contain split opening windows. Identical rows
        # are rejected, while distinct windows survive without flattening.
        key = (item["date"], item.get("start_time"), item.get("end_time"))
        if key in seen:
            return None
        seen.add(key)
        result.append(deepcopy(item))
    interval = value.get("intervallo_edizione")
    if interval is not None:
        if not isinstance(interval, dict) or set(interval) != {"start", "end"}:
            return None
        start, end = as_day(interval.get("start")), as_day(interval.get("end"))
        if not start or not end or start > end or any(
                not start <= as_day(item["date"]) <= end for item in result):
            return None
    cleaned = {k: deepcopy(value[k]) for k in (
        "schema", "gestore", "mercato", "url", "url_richiesto", "fonte_id",
        "letto_il", "fonte_aggiornata_il", "fonte_pubblicata_il", "sha256") if k in value}
    cleaned["occorrenze"] = sorted(result, key=lambda x: (
        x["date"], x.get("start_time") or "", x.get("end_time") or ""))
    cleaned["intervallo_edizione"] = deepcopy(interval)
    cleaned["ambito_calendario"] = value["ambito_calendario"]
    cleaned["intervalli"] = deepcopy(intervals)
    return cleaned


def source_calendar_dates(value, row, *, today):
    calendar = clean_source_calendar(value, row, today=today)
    if not calendar:
        return []
    end = today + timedelta(days=MAX_FUTURE_DAYS)
    excluded = {item["data"] for item in clean_exceptions(row.get("eccezioni_calendario"), row, today=today)}
    return sorted({item["date"] for item in calendar["occorrenze"]
                   if item["status"] in {"source_listed", "rescheduled"}
                   and item["date"] not in excluded
                   and today <= as_day(item["date"]) <= end})


def _bounded_value(value, depth=0):
    if depth > 6:
        return False
    if value is None or isinstance(value, bool):
        return True
    if isinstance(value, str):
        return len(value) <= 4000 and not any(ord(char) < 32 and char not in "\n\t\r" for char in value)
    if isinstance(value, (float, int)):
        return math.isfinite(value) and abs(value) < 1e12
    if isinstance(value, list):
        return len(value) <= 60 and all(_bounded_value(v, depth + 1) for v in value)
    return bool(isinstance(value, dict) and len(value) <= 40 and all(
        isinstance(k, str) and len(k) <= 120 and _bounded_value(v, depth + 1)
        for k, v in value.items()))


def clean_source_detail(value, row, *, today):
    if not _provenance(value, row, today):
        return None
    facts = value.get("evento")
    if (not isinstance(facts, dict) or set(facts) - DETAIL_FIELDS
            or not _bounded_value(facts)
            or not isinstance(facts.get("name"), str) or not facts["name"].strip()
            or len(json.dumps(facts, ensure_ascii=False).encode("utf-8")) > MAX_DETAIL_BYTES):
        return None
    result = {k: deepcopy(value[k]) for k in (
        "schema", "gestore", "mercato", "url", "url_richiesto", "fonte_id",
        "letto_il", "fonte_aggiornata_il", "fonte_pubblicata_il", "sha256") if k in value}
    result["evento"] = deepcopy(facts)
    return result


def refresh_source_calendar(row, *, today):
    """Keep only listed dates and never fall through to a recurring forecast."""
    calendar = clean_source_calendar(row.get("calendario_fonte"), row, today=today)
    if not calendar:
        return None
    result = deepcopy(row)
    result["calendario_fonte"] = calendar
    if row.get("verificato_il") or row.get("date_quality") == "confermata":
        return result
    result["date"] = source_calendar_dates(calendar, row, today=today)
    result["date_quality"] = "riportata" if result["date"] else "sconosciuta"
    result["proiezione_regola"] = None
    result["proiezione_generata_il"] = ""
    result["proiezione_fonte"] = ""
    return result
