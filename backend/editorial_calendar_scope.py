"""Identity-bound facts and calendar limits from an existing editorial source.

An edition interval is a bound, not a list of daily openings.  This helper
never creates recurrence dates, moves an identity, or calls an old edition a
permanent closure.  Publisher facts, the editorial date, the acquisition date
and any independent confirmation remain separate through refresh and export.
"""
from __future__ import annotations

import json
import re
import unicodedata
from copy import deepcopy
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from field_evidence import MAX_READ_AGE, SOURCE_AGE, as_day, clean_receipts, identity

KEY = "evidenza_editoriale"
MANAGER = "editorial-detail"
MAX_EVIDENCE_BYTES = 64_000
MAX_FUTURE_DAYS = 550
EVENT_FIELDS = {
    "name", "location", "hours_text", "hours_intervals", "recurrence_text",
    "archive_marker", "edition_intervals", "occurrences", "date_intervals",
    "calendar_complete", "calendar_scope", "calendar_rules", "suspensions",
    "scope_statements", "conditions", "source_rows", "hours_qualifications",
    "forecast_rule", "selected_row", "selected_row_id", "observed_location",
}
CALENDAR_FIELDS = {"calendar", "recurrence", "edition", "occurrences", "suspensions"}
PROJECTION_FIELDS = {"proiezione_regola": None, "proiezione_generata_il": "", "proiezione_fonte": ""}


def text_key(value):
    value = unicodedata.normalize("NFKD", str(value or "")).casefold()
    value = "".join(c for c in value if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w]+", " ", value).split())


@lru_cache(maxsize=1)
def istat_geography():
    values = json.loads((Path(__file__).resolve().parent / "data/istat-comuni-2026.json").read_text(encoding="utf-8"))
    return frozenset((text_key(city), province, text_key(region))
        for region, cities in values["provinces_by_region"].items()
        for city, province in cities.items())


def geography_matches(row, location):
    """Bind observed geography without filling a missing catalog province.

A missing province is permitted only when the observed and saved city/region
identify one ISTAT municipality. A source province cannot resolve a namesake
that the saved record's own geography leaves ambiguous.
"""
    city, region = text_key(location.get("city")), text_key(location.get("region"))
    province = location.get("province")
    if (not city or not region or city != text_key(row.get("citta"))
            or region != text_key(row.get("regione"))
            or (city, province, region) not in istat_geography()):
        return False
    saved = row.get("provincia")
    if saved:
        return saved == province
    return len({v for v in istat_geography() if v[0] == city and v[2] == region}) == 1


def specific_title_match(left, right, city):
    generic = {"mercato", "mercatino", "mercatini", "mercati", "di", "del", "della",
        "delle", "dei", "degli", "a", "il", "la", "e", "in", "da", "dell", "l",
        "settimanale", "mensile", "giornaliero", "antiquariato", "usato", "artigianato",
        "alimentare", "misto", "abbigliamento", "vintage"} | set(text_key(city).split())
    a, b = text_key(left), text_key(right)
    specific_a, specific_b = set(a.split()) - generic, set(b.split()) - generic
    return bool(specific_a and specific_b and (a == b or a in b or b in a or specific_a == specific_b))


def blank_province_venue_or_title(row, facts):
    if row.get("provincia"):
        return True
    address = text_key((facts.get("location") or {}).get("address"))
    return bool(address and address == text_key(row.get("indirizzo"))) or specific_title_match(
        row.get("nome"), facts.get("name"), row.get("citta"))


def source_identity(url):
    """Return a reviewed publisher and source ID, never a guessed URL."""
    if not isinstance(url, str) or not 20 <= len(url) <= 1200:
        return None
    try:
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.username or parsed.password
                or parsed.port not in (None, 443) or parsed.query or parsed.fragment):
            return None
        if parsed.netloc == "www.eventiesagre.it":
            match = re.fullmatch(r"/(?:Mercatini|Eventi)_[A-Za-z+]+/(\d+)_[^/]+\.html", parsed.path)
            if match:
                return "eventiesagre.it", match[1]
        if parsed.netloc == "www.cosedicasa.com":
            match = re.fullmatch(r"/mercatini/([a-z0-9]+(?:-[a-z0-9]+)*)/?", parsed.path)
            if match:
                return "cosedicasa.com", match[1]
    except ValueError:
        pass
    # A narrow existing-detail adapter owns its reviewed origins and exact
    # URL grammar; this does not enable arbitrary Citynews hosts or indexes.
    from citynews_urls import source_identity as citynews_identity
    return citynews_identity(url)


def _bounded(value, depth=0):
    if depth > 7:
        return False
    if value is None or type(value) in (bool, int):
        return True
    if isinstance(value, str):
        return len(value) <= 4000 and not any(ord(c) < 32 and c not in "\n\t\r" for c in value)
    if isinstance(value, list):
        return len(value) <= 600 and all(_bounded(v, depth + 1) for v in value)
    return bool(isinstance(value, dict) and len(value) <= 50 and all(
        isinstance(k, str) and len(k) <= 100 and _bounded(v, depth + 1) for k, v in value.items()))


def calendar_conflicted(conflicts):
    return any((isinstance(c, dict) and c.get("field") in CALENDAR_FIELDS)
               or isinstance(c, str) and any(w in c for w in
                   ("calendar", "edition", "recurrence", "archive_marker_date"))
               for c in conflicts)


def clean_editorial_evidence(value, row, *, today):
    """Validate saved factual scope without treating its read date as freshness."""
    if not isinstance(today, date) or not isinstance(value, dict) or not _bounded(value):
        return None
    if len(json.dumps(value, ensure_ascii=False).encode("utf-8")) > MAX_EVIDENCE_BYTES:
        return None
    required = {"schema", "manager", "market", "primary_url", "publisher", "source_id",
                "requested_url", "final_url", "canonical_url", "redirect_observed", "source_sha256", "source_bytes",
                "read_on", "published_on", "modified_on", "hash_basis", "calendar_mode", "facts",
                "conflicts", "warnings", "field_evidence"}
    if (set(value) != required or value.get("schema") != 1 or value.get("manager") != MANAGER
            or value.get("market") != identity(row) or value.get("primary_url") != row.get("url_fonte")):
        return None
    expected = source_identity(value["primary_url"])
    final_identity = source_identity(value.get("final_url"))
    observed_alias = bool(expected and expected[0] == "cosedicasa.com"
        and value.get("redirect_observed") is True and final_identity
        and final_identity[0] == expected[0] and value["final_url"] != value["requested_url"])
    if (expected is None or expected != (value.get("publisher"), value.get("source_id"))
            or value.get("requested_url") != value["primary_url"]
            or type(value.get("redirect_observed")) is not bool
            or final_identity != expected and not observed_alias
            or value.get("canonical_url") is not None
            and source_identity(value["canonical_url"]) != (final_identity if observed_alias else expected)
            or not re.fullmatch(r"[0-9a-f]{64}", str(value.get("source_sha256") or ""))
            or type(value.get("source_bytes")) is not int
            or not 100 <= value["source_bytes"] <= 2_500_000
            or value.get("hash_basis") not in {"http_response_bytes", "connector_utf8_text"}):
        return None
    read = as_day(value.get("read_on"))
    if not read or read > today:
        return None
    for field in ("modified_on", "published_on"):
        parsed = as_day(value.get(field))
        if value.get(field) and (not parsed or parsed > read):
            return None
    facts = value.get("facts")
    if (not isinstance(facts, dict) or set(facts) - EVENT_FIELDS
            or not isinstance(facts.get("name"), str) or not facts["name"].strip()
            or not isinstance(facts.get("location"), dict)
            or type(facts.get("archive_marker")) is not bool
            or type(facts.get("calendar_complete")) is not bool
            or not isinstance(facts.get("calendar_scope"), str)
            or not isinstance(value.get("conflicts"), list)
            or not isinstance(value.get("warnings"), list)
            or not isinstance(value.get("field_evidence"), dict)
            or value.get("calendar_mode") not in {"limit_forecasts", "reported_explicit"}):
        return None
    place = facts["location"]
    if not geography_matches(row, place) or not blank_province_venue_or_title(row, facts):
        return None
    intervals = facts.get("edition_intervals", [])
    if not isinstance(intervals, list) or len(intervals) > 100:
        return None
    for interval in intervals:
        if not isinstance(interval, dict) or set(interval) != {"start", "end"}:
            return None
        start, end = as_day(interval["start"]), as_day(interval["end"])
        if not start or not end or not 2000 <= start.year <= end.year <= 2100 or start > end:
            return None
    occurrences = facts.get("occurrences", [])
    if not isinstance(occurrences, list) or len(occurrences) > 600:
        return None
    seen = set()
    for occurrence in occurrences:
        if not isinstance(occurrence, dict) or not as_day(occurrence.get("date")):
            return None
        day = as_day(occurrence["date"])
        if not 2000 <= day.year <= 2100 or occurrence.get("status") not in {
                "source_listed", "cancelled", "postponed", "rescheduled"}:
            return None
        signature = (occurrence["date"], occurrence.get("start_time"), occurrence.get("end_time"))
        if signature in seen:
            return None
        seen.add(signature)
        for clock in (occurrence.get("start_time"), occurrence.get("end_time")):
            if clock is not None and not isinstance(clock, str):
                return None
            if clock is not None and not re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d|24:00", clock):
                return None
        if intervals and not any(i["start"] <= occurrence["date"] <= i["end"] for i in intervals):
            return None
    if value["calendar_mode"] == "reported_explicit" and (
            not occurrences or not facts["calendar_complete"] or facts["archive_marker"]
            or calendar_conflicted(value["conflicts"])):
        return None
    result = deepcopy(value)
    if facts.get("forecast_rule") is not None:
        # The saved source text is the evidence; its rule is derived. Re-read it
        # with the current parser every time, so a parser fix corrects old
        # evidence (e.g. "2^ domenica" once read as every Sunday) and a stored
        # rule can never be trusted on its own.
        # Import at call time: recurrence_refresh may import this helper.
        from recurrence_refresh import explicit_rule
        result["facts"]["forecast_rule"] = explicit_rule(facts.get("recurrence_text"))
    return result


def build_evidence(row, document, *, read_on, calendar_mode="limit_forecasts"):
    source = document["source"]
    result = {
        "schema": 1, "manager": MANAGER, "market": identity(row),
        "primary_url": row["url_fonte"], "publisher": source["publisher"],
        "source_id": source["source_id"], "requested_url": source["requested_url"],
        "final_url": source["final_url"], "canonical_url": source.get("canonical_url"),
        "redirect_observed": source.get("redirect_observed", False),
        "source_sha256": source["html_sha256"], "source_bytes": source["bytes"],
        "hash_basis": source.get("hash_basis", "http_response_bytes"),
        "read_on": read_on, "published_on": (source.get("published_at") or "")[:10],
        "modified_on": (source.get("modified_at") or "")[:10],
        "calendar_mode": calendar_mode,
        "facts": {k: deepcopy(v) for k, v in document["event"].items() if k in EVENT_FIELDS},
        "conflicts": deepcopy(document.get("conflicts", [])),
        "warnings": deepcopy(document.get("warnings", [])),
        "field_evidence": deepcopy(document.get("field_evidence", {})),
    }
    if clean_editorial_evidence(result, row, today=as_day(read_on)) is None:
        raise ValueError("Editorial facts lack an exact source/market binding")
    return result


def _independently_supported(row, evidence, today):
    if row.get("verificato_il") or row.get("date_quality") == "confermata":
        return True
    if row.get("calendario_fonte") is not None:
        from source_calendar import clean_source_calendar
        if clean_source_calendar(row["calendario_fonte"], row, today=today):
            return True
    if row.get("date_quality") == "riportata" and evidence["calendar_mode"] != "reported_explicit":
        return True
    for receipt in clean_receipts(row.get("riscontri_campi"), row, today=today):
        updated = as_day(receipt.get("fonte_aggiornata_il"))
        # Same rule as recurrence_refresh: a dated proof keeps its age limit; an
        # undated one counts as "still listed" while it was read recently.
        if (receipt.get("url") != evidence["primary_url"]
                and receipt["valori"].get("ricorrenza_testo") == row.get("ricorrenza_testo")
                and (not receipt.get("fonte_aggiornata_il")
                     or updated and 0 <= (today - updated).days <= SOURCE_AGE["ricorrenza_testo"])
                and 0 <= (today - as_day(receipt["letto_il"])).days <= MAX_READ_AGE):
            return True
    return False


def _reported_dates(row, evidence, today):
    from field_evidence import clean_exceptions
    excluded = {v["data"] for v in clean_exceptions(row.get("eccezioni_calendario"), row, today=today)}
    last = (today + timedelta(days=MAX_FUTURE_DAYS)).isoformat()
    return sorted({v["date"] for v in evidence["facts"]["occurrences"]
        if v["status"] in {"source_listed", "rescheduled"}
        and today.isoformat() <= v["date"] <= last and v["date"] not in excluded})


def valid_editorial_reported_dates(row, *, today):
    """Independent proof for the label 'riportata', never 'confermata'."""
    evidence = clean_editorial_evidence(row.get(KEY), row, today=today)
    if not evidence or evidence["calendar_mode"] != "reported_explicit":
        return False
    dates = _reported_dates(row, evidence, today)
    return bool(dates and row.get("date_quality") == "riportata" and row.get("date") == dates
        and all(not row.get(k) for k in PROJECTION_FIELDS))


def apply_editorial_scope(row, *, today):
    """Return (row, disposition); call after recurrence and during export.

The helper can restrict existing predictions or retain explicitly listed
dates. It cannot expand an interval or derive a new recurrence. A corrupted
stored scope is held rather than silently falling back to an old forecast.
"""
    if row.get(KEY) is None:
        return row, "no_editorial_evidence"
    evidence = clean_editorial_evidence(row[KEY], row, today=today)
    if evidence is None:
        raise ValueError("Invalid editorial source evidence")
    result = deepcopy(row)
    if _independently_supported(row, evidence, today):
        return result, "independent_calendar_preserved"
    facts = evidence["facts"]
    if evidence["calendar_mode"] == "reported_explicit":
        result["date"] = _reported_dates(row, evidence, today)
        result["date_quality"] = "riportata" if result["date"] else "sconosciuta"
        for key, empty in PROJECTION_FIELDS.items():
            if key in result:
                result[key] = empty
        return result, "explicit_editorial_dates_retained"
    if row.get("date_quality") not in {None, "", "prevista", "sconosciuta"}:
        return result, "non_projected_calendar_preserved"
    intervals = facts.get("edition_intervals", [])
    if facts["archive_marker"]:
        reason = "archived_edition_forecast_held"
    elif calendar_conflicted(evidence["conflicts"]):
        reason = "conflicting_editorial_calendar_held"
    elif facts.get("scope_statements") or facts.get("suspensions") or facts.get("calendar_rules"):
        reason = "unresolved_editorial_calendar_qualifications"
    elif not facts.get("forecast_rule") or not facts["calendar_complete"]:
        reason = "editorial_recurrence_not_proven"
    elif not intervals:
        reason = "editorial_edition_scope_missing"
    else:
        from recurrence_refresh import explicit_rule
        reason = ("editorial_edition_scope_filtered"
                  if facts["forecast_rule"] == explicit_rule(row.get("ricorrenza_testo"))
                  else "editorial_recurrence_conflicts_with_catalog")
    old_dates = list(row.get("date") or [])
    kept = [d for d in old_dates if isinstance(d, str) and as_day(d) and as_day(d) >= today
            and any(i["start"] <= d <= i["end"] for i in intervals)] \
        if reason == "editorial_edition_scope_filtered" else []
    result["date"] = kept
    if not kept:
        result["date_quality"] = "sconosciuta"
        for key, empty in PROJECTION_FIELDS.items():
            if key in result:
                result[key] = empty
    return result, reason


def retain_editorial_evidence(raw, result, *, today):
    """Exporter hook, after ordinary fields and projection metadata are built."""
    if raw.get(KEY) is None:
        return result
    evidence = clean_editorial_evidence(raw[KEY], result, today=today)
    if evidence is None:
        raise ValueError("Export changed or lost the editorial source binding")
    result = {**result, KEY: evidence}
    return apply_editorial_scope(result, today=today)[0]
