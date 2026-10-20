"""Bounded refresh of Eventi e Sagre URLs already belonging to catalog IDs.

No discovery, new market admission, geocoding, or publisher-rights claim is
performed here. The separate links-only research registry is not consulted or
changed. Factual observations and their edition limits are reconstructed in
the diff guard and remain attributable after a later offline refresh.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import ipaddress
import json
import re
import socket
import time
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, datetime, timezone
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

from editorial_calendar_scope import (
    KEY, apply_editorial_scope, build_evidence, calendar_conflicted,
    blank_province_venue_or_title, clean_editorial_evidence, geography_matches,
    istat_geography, source_identity, text_key, valid_editorial_reported_dates,
)
from eventiesagre_source_layout import MAX_BYTES, parse_eventiesagre_html
from field_evidence import (
    FIELDS, as_day, clean_receipts, fingerprint, make_receipt,
    managed_update_allowed, mark_managed_fields, retire_superseded_receipts,
)
from recurrence_refresh import explicit_rule

PUBLISHER = "eventiesagre.it"
MANAGER = "eventiesagre_detail"
ROBOTS = "https://www.eventiesagre.it/robots.txt"
STATE_FILENAME = "eventiesagre-detail-state.json"
REPORT_FILENAME = "eventiesagre-detail-refresh.json"
POLICY_PATH = Path(__file__).resolve().parent / "data/editorial-detail-refresh-policy.json"
USER_AGENT = "MercatiItaliaEditorialRefresh/1.0"
MAX_RESOURCES = 6000
MAX_STATE_BYTES = 6_000_000
MAX_DETAILS = 64
MAX_SECONDS = 360
DEFAULT_POLICY = {"enabled": True, "max_details": 64, "max_seconds": 210,
                  "min_delay_seconds": 2, "overdue_after_days": 45,
                  "new_market_ids_allowed": False, "overwrite_unowned_fields": False}
STATUSES = {"unread", "inflight", "retrieved", "layout_held", "unavailable", "robots_denied"}
MUTABLE = set(FIELDS) | {KEY, "riscontri_campi", "fonti", "date", "date_quality",
                       "proiezione_regola", "proiezione_generata_il", "proiezione_fonte"}
BLOCKING_IDENTITY = {"locality_missing_or_ambiguous", "card_heading_locality_conflict",
                     "jsonld_visible_locality_conflict"}
CALENDAR_ISSUES = {"edition_dates_missing_or_invalid", "archive_marker_date_conflict",
                   "jsonld_visible_edition_conflict", "multiple_recurrence_statements"}
PUBLISHERS = {"eventiesagre.it": {"policy_key": "eventiesagre", "stem": "eventiesagre",
                 "manager": MANAGER, "max_details": 64, "max_seconds": 210},
              "cosedicasa.com": {"policy_key": "cosedicasa", "stem": "cosedicasa",
                 "manager": "cosedicasa_detail", "max_details": 16, "max_seconds": 90}}


def state_filename(publisher=PUBLISHER):
    return PUBLISHERS[publisher]["stem"] + "-detail-state.json"


def report_filename(publisher=PUBLISHER):
    return PUBLISHERS[publisher]["stem"] + "-detail-refresh.json"


def validate_policy(policy=None, *, publisher=PUBLISHER):
    if publisher not in PUBLISHERS:
        raise ValueError("Unreviewed editorial publisher")
    limits = PUBLISHERS[publisher]
    if policy is None:
        registry = json.loads(POLICY_PATH.read_text("utf-8"))
        if registry.get("schema") != 1 or registry.get("publication_channel") != "dev-only":
            raise ValueError("Invalid editorial source policy")
        policy = registry.get(limits["policy_key"])
    if (not isinstance(policy, dict) or set(policy) != set(DEFAULT_POLICY)
            or type(policy["enabled"]) is not bool
            or type(policy["max_details"]) is not int or not 1 <= policy["max_details"] <= limits["max_details"]
            or type(policy["max_seconds"]) is not int or not 1 <= policy["max_seconds"] <= limits["max_seconds"]
            or type(policy["min_delay_seconds"]) is not int or not 2 <= policy["min_delay_seconds"] <= 30
            or type(policy["overdue_after_days"]) is not int or not 1 <= policy["overdue_after_days"] <= 45
            or policy["new_market_ids_allowed"] is not False
            or policy["overwrite_unowned_fields"] is not False):
        raise ValueError("Unreviewed editorial request or update policy")
    return deepcopy(policy)


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", "utf-8")
    temporary.replace(path)


def catalog_urls(rows, *, publisher=PUBLISHER):
    if publisher not in PUBLISHERS:
        raise ValueError("Unreviewed editorial publisher")
    return sorted({r["url_fonte"] for r in rows
                   if (source_identity(r.get("url_fonte")) or (None,))[0] == publisher})


def _resource(today):
    return {"first_seen": today.isoformat(), "last_attempt": None, "last_read": None,
            "last_parsed": None, "sha256": None, "status": "unread", "attempts": 0,
            "attempt_cycle": 0, "read_cycle": 0, "last_error": None}


def validate_state(state, *, today, publisher=None):
    publisher = publisher or (state.get("publisher") if isinstance(state, dict) else None)
    if publisher not in PUBLISHERS:
        raise ValueError("Unreviewed editorial queue publisher")
    if (not isinstance(state, dict) or set(state) != {"schema", "publisher", "cycle",
            "cycle_started_on", "last_completed_cycle", "last_completed_on", "resources"}
            or state.get("schema") != 1 or state.get("publisher") != publisher
            or type(state.get("cycle")) is not int or not 1 <= state["cycle"] <= 100000
            or type(state.get("last_completed_cycle")) is not int
            or not 0 <= state["last_completed_cycle"] <= state["cycle"]
            or not isinstance(state.get("resources"), dict) or len(state["resources"]) > MAX_RESOURCES
            or not as_day(state.get("cycle_started_on"))
            or as_day(state["cycle_started_on"]) > today):
        raise ValueError("Invalid editorial queue state")
    completed = as_day(state.get("last_completed_on"))
    if bool(state["last_completed_cycle"]) != bool(completed) or completed and completed > today:
        raise ValueError("Editorial cycle completion date is invalid")
    for url, entry in state["resources"].items():
        if (source_identity(url) or (None,))[0] != publisher or not isinstance(entry, dict):
            raise ValueError("Editorial queue URL is outside the reviewed publisher")
        if (set(entry) != set(_resource(today)) or entry.get("status") not in STATUSES
                or type(entry.get("attempts")) is not int or entry["attempts"] < 0
                or type(entry.get("attempt_cycle")) is not int
                or type(entry.get("read_cycle")) is not int
                or not 0 <= entry["read_cycle"] <= entry["attempt_cycle"] <= state["cycle"]):
            raise ValueError("Editorial resource counters or status are invalid")
        for field in ("first_seen", "last_attempt", "last_read", "last_parsed"):
            value = entry[field]
            if value is not None and (not as_day(value) or as_day(value) > today):
                raise ValueError("Editorial queue contains future or invalid observations")
        if not entry["first_seen"] or bool(entry["attempts"]) != bool(entry["last_attempt"]):
            raise ValueError("Editorial queue lost its attempt history")
        if entry["last_read"] and (not entry["last_attempt"] or entry["last_read"] > entry["last_attempt"]):
            raise ValueError("Editorial read precedes its attempt history")
        if entry["last_parsed"] and (not entry["last_read"] or entry["last_parsed"] > entry["last_read"]):
            raise ValueError("Editorial parsed date lacks a read")
        if bool(entry["sha256"]) != bool(entry["last_read"]) or entry["sha256"] and not re.fullmatch(
                r"[0-9a-f]{64}", entry["sha256"]):
            raise ValueError("Editorial read lacks its content fingerprint")
        if entry["last_error"] is not None and (not isinstance(entry["last_error"], str)
                                               or len(entry["last_error"]) > 100):
            raise ValueError("Editorial queue error is unbounded")
    return state


def seed_state(rows, previous=None, *, today, publisher=PUBLISHER):
    urls = catalog_urls(rows, publisher=publisher)
    if len(urls) > MAX_RESOURCES:
        raise ValueError("Existing editorial source inventory exceeds its limit")
    state = deepcopy(validate_state(previous, today=today, publisher=publisher)) if previous is not None else {
        "schema": 1, "publisher": publisher, "cycle": 1,
        "cycle_started_on": today.isoformat(), "last_completed_cycle": 0,
        "last_completed_on": None, "resources": {}}
    state["resources"] = {url: state["resources"].get(url, _resource(today)) for url in urls}
    if urls and all(v["attempt_cycle"] == state["cycle"] for v in state["resources"].values()):
        state["last_completed_cycle"] = state["cycle"]
        state["last_completed_on"] = max(v["last_attempt"] for v in state["resources"].values())
        state["cycle"] += 1
        state["cycle_started_on"] = today.isoformat()
    return validate_state(state, today=today, publisher=publisher)


def progress(state, *, today, overdue_after_days=45):
    validate_state(state, today=today)
    entries = state["resources"]
    attempted = sum(v["attempt_cycle"] == state["cycle"] for v in entries.values())
    read = sum(v["read_cycle"] == state["cycle"] for v in entries.values())
    overdue = sorted(url for url, v in entries.items() if not v["last_read"]
                     or (today - as_day(v["last_read"])).days > overdue_after_days)
    return {"cycle": state["cycle"], "cycle_started_on": state["cycle_started_on"],
            "resources": len(entries), "cycle_attempted": attempted, "cycle_read": read,
            "cycle_remaining": len(entries) - attempted,
            "attempt_cycle_complete": bool(entries) and attempted == len(entries),
            "successful_read_cycle_complete": bool(entries) and read == len(entries),
            "last_completed_cycle": state["last_completed_cycle"],
            "never_read": sum(v["last_read"] is None for v in entries.values()),
            "overdue_after_days": overdue_after_days, "overdue_urls": overdue,
            "statuses": dict(sorted(Counter(v["status"] for v in entries.values()).items())),
            "market_freshness_guaranteed": False}


def _geography():
    return istat_geography()


def _normalized_location(location):
    """Resolve only an observed municipality/province/region via ISTAT."""
    city = text_key(location.get("city"))
    region = text_key(location.get("region"))
    province = str(location.get("province") or "")
    candidates = [v for v in _geography() if v[0] == city and (not region or v[2] == region)]
    if province:
        if re.fullmatch(r"[A-Za-z]{2}", province):
            candidates = [v for v in candidates if v[1] == province.upper()]
        else:
            named = text_key(re.sub(r"^(?:provincia|città metropolitana)\s+di\s+", "", province, flags=re.I))
            parts = [text_key(p) for p in re.split(r"[-–—/]\s*|\s+e\s+", named) if p.strip()]
            candidates = [v for v in candidates if all((part, v[1], v[2]) in _geography() for part in parts)]
    if len(candidates) != 1:
        return None
    match = candidates[0]
    canonical_regions = json.loads((Path(__file__).resolve().parent / "data/istat-comuni-2026.json").read_text())["provinces_by_region"]
    region_name = next(name for name in canonical_regions if text_key(name) == match[2])
    return {**location, "province": match[1], "region": region_name}


def _conflict(code):
    field = ("identity" if code in BLOCKING_IDENTITY else
             "calendar" if code in CALENDAR_ISSUES else
             "address" if code == "visible_address_conflict" else
             "hours" if code == "visible_hours_conflict" else None)
    return {"field": field, "code": code} if field else None


def parse_document(blob, *, requested_url, final_url=None, today):
    """Adapt the existing pure parser into the shared editorial-facts envelope."""
    expected = source_identity(requested_url)
    final_url = final_url or requested_url
    if (expected is None or expected[0] not in PUBLISHERS
            or (source_identity(final_url) or (None,))[0] != expected[0]
            or expected[0] == PUBLISHER and source_identity(final_url) != expected):
        raise ValueError("Editorial redirect changed the numeric source identity")
    if expected[0] == "cosedicasa.com":
        from cosedicasa_layout import parse_detail
        document = parse_detail(blob, requested_url=requested_url, final_url=final_url)
        if document["status"] == "unsupported":
            raise ValueError("Cose di Casa detail layout changed")
        source = document["source"]
        # Keep original identity and the actual HTTP destination separately.
        # A canonical tag alone can never manufacture an observed redirect.
        source.update(source_id=expected[1], hash_basis="http_response_bytes",
                      redirect_observed=final_url != requested_url)
        observed = deepcopy(document["event"]["location"])
        document["event"]["observed_location"] = observed
        normalized = _normalized_location(observed)
        if normalized is None:
            document["conflicts"].append({"field": "identity", "code": "istat_geography_unresolved"})
            document["status"] = "held"
        else:
            document["event"]["location"] = normalized
        document["event"]["forecast_rule"] = None
        return document
    parsed = parse_eventiesagre_html(blob, final_url, today=today)
    fields = parsed["legacy_fields"]
    issues = parsed["issues"]
    conflicts = [c for issue in issues if (c := _conflict(issue))]
    intervals = deepcopy(parsed["edition_intervals"])
    recurrence = parsed["recurrence_text"]
    complete = bool(intervals and not calendar_conflicted(conflicts))
    occurrences = [{"date": v["start"], "start_time": None, "end_time": None,
                    "status": "source_listed", "evidence": ["visible event card Dal/Al"]}
                   for v in intervals if v["start"] == v["end"]] if complete else []
    document = {
        "schema": 1, "status": "held" if conflicts else "parsed",
        "source": {"publisher": PUBLISHER, "source_id": parsed["source_id"],
            "requested_url": requested_url, "final_url": final_url, "canonical_url": None,
            "redirect_observed": final_url != requested_url,
            "html_sha256": parsed["source_sha256"], "bytes": len(blob),
            "hash_basis": "http_response_bytes",
            "published_at": None, "modified_at": parsed["source_modified_on"] or None},
        "event": {"name": fields["nome"], "location": {
            "city": fields["citta"], "province": fields["provincia"],
            "region": fields["regione"], "address": fields["indirizzo"]},
            "hours_text": fields["orario_raw"], "hours_intervals": [],
            "recurrence_text": recurrence, "archive_marker": parsed["archive_marker"],
            "edition_intervals": intervals, "occurrences": occurrences,
            "date_intervals": [], "calendar_complete": complete,
            "calendar_scope": "edition_bounds", "calendar_rules": [], "suspensions": [],
            "scope_statements": deepcopy(parsed["scope_statements"]), "conditions": [],
            "source_rows": deepcopy(parsed["source_rows"]),
            "forecast_rule": explicit_rule(recurrence)},
        "conflicts": conflicts,
        "warnings": [v for v in issues if _conflict(v) is None],
        "field_evidence": {
            "identity": {"selector": "#schedaEvento Numero Evento; #contenuto > h1",
                         "value": parsed["source_id"]},
            "location": {"selector": "#schedaEvento .SX; scoped Luogo/Indirizzo blocks"},
            "hours": {"selector": "#contenuto > h3; scoped Orario blocks"},
            "calendar": {"selector": "#schedaEvento Dal/Al and #eventopassato"},
        },
    }
    return document


def _valid_document(document, read_on, today):
    if (not isinstance(document, dict) or set(document) != {
            "schema", "status", "source", "event", "conflicts", "warnings", "field_evidence"}
            or document.get("schema") != 1 or document.get("status") not in {"parsed", "held"}
            or not isinstance(document.get("source"), dict)
            or not isinstance(document.get("event"), dict)
            or not isinstance(document.get("conflicts"), list)
            or not isinstance(document.get("warnings"), list)
            or not isinstance(document.get("field_evidence"), dict)
            or not as_day(read_on) or not 0 <= (today - as_day(read_on)).days <= 45):
        raise ValueError("Invalid bounded editorial source document")
    source = document["source"]
    expected = source_identity(source.get("requested_url"))
    if (expected is None or expected[0] not in PUBLISHERS
            or (source.get("publisher"), source.get("source_id")) != expected
            or (source_identity(source.get("final_url")) or (None,))[0] != expected[0]
            or expected[0] == PUBLISHER and source_identity(source.get("final_url")) != expected
            or not re.fullmatch(r"[0-9a-f]{64}", str(source.get("html_sha256") or ""))
            or type(source.get("bytes")) is not int or not 100 <= source["bytes"] <= MAX_BYTES):
        raise ValueError("Editorial source proof changed identity or hash")
    if len(json.dumps(document, ensure_ascii=False).encode("utf-8")) > 64_000:
        raise ValueError("Editorial extracted evidence exceeds its bound")
    return source


def _same_title(left, right, city):
    a, b = text_key(left), text_key(right)
    if not a or not b:
        return False
    if a == b or a in b or b in a:
        return True
    generic = {"mercato", "mercatino", "mercatini", "mercati", "di", "del", "della",
               "delle", "dei", "a", "il", "la", "e", "in", "da"} | set(text_key(city).split())
    significant = set(a.split()) - generic
    return bool(significant and significant == set(b.split()) - generic)


def _days(text):
    names = ("lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica")
    words = set(text_key(text).split())
    return {i for i, name in enumerate(names) if name in words}


def _select(row, document):
    event = document["event"]
    place = event.get("location") or {}
    if not geography_matches(row, place):
        return None, "source_geography_not_established"
    if any(c.get("field") == "identity" for c in document["conflicts"]):
        return None, "source_identity_conflict"
    if any("\ufffd" in str(v) for v in (event.get("name"), place.get("city"), place.get("address"))):
        return None, "source_text_encoding_damage"
    original = text_key(row.get("indirizzo"))
    source_rows = [v for v in event.get("source_rows") or [] if isinstance(v, dict)
                   and {"address", "hours", "recurrence"} <= set(v)]
    if len(source_rows) > 1:
        days = _days(row.get("ricorrenza_testo"))
        candidates = [r for r in source_rows if original and text_key(r.get("address")) == original
                      and days and _days(r.get("recurrence")) == days]
        if len(candidates) != 1:
            return None, "multiple_venues_need_exact_address_and_days"
        selected = deepcopy(candidates[0])
        selected["source_row_id"] = document["source"]["source_id"] + ":" + fingerprint(
            [text_key(selected["address"]), text_key(selected["recurrence"])])[:24]
        return selected, "exact_source_venue_and_days"
    if not blank_province_venue_or_title(row, event):
        return None, "missing_province_requires_exact_venue_or_specific_title"
    address = str(place.get("address") or "")
    incoming = text_key(address)
    if original and incoming and original != incoming:
        # A later managed single-venue address may move, but identity still
        # needs the same title and source card. Ownership is checked below.
        manager = PUBLISHERS[document["source"]["publisher"]]["manager"]
        managed = any(r.get("gestore_campi") == manager and "indirizzo" in r.get("campi_gestiti", [])
                      for r in row.get("riscontri_campi") or [] if isinstance(r, dict))
        if not managed or not _same_title(row.get("nome"), event.get("name"), place.get("city")):
            return None, "existing_venue_conflict"
    elif not (original and incoming and original == incoming) and not _same_title(
            row.get("nome"), event.get("name"), place.get("city")):
        return None, "source_title_and_venue_not_established"
    if any(c.get("field") == "address" for c in document["conflicts"]):
        return None, "source_venue_ambiguous"
    source_row_id = document["source"]["source_id"] + ":single"
    if len(source_row_id) > 160:
        source_row_id = "source:" + fingerprint(source_row_id) + ":single"
    return {"address": address, "hours": event.get("hours_text") or "",
            "recurrence": event.get("recurrence_text") or "",
            "source_row_id": source_row_id}, "exact_existing_source_identity"


def _ordered(previous, incoming):
    return not previous or bool(incoming["read_on"] >= previous["read_on"]
        and not (incoming["read_on"] == previous["read_on"]
                 and incoming["source_sha256"] != previous["source_sha256"])
        and not (previous["modified_on"] and (not incoming["modified_on"]
                                             or incoming["modified_on"] < previous["modified_on"])))


def _bound_document(document, selected):
    local = deepcopy(document)
    publisher = document["source"]["publisher"]
    event = local["event"]
    event["selected_row"] = {k: v for k, v in selected.items() if k != "source_row_id"}
    event["selected_row_id"] = selected["source_row_id"]
    event["location"]["address"] = selected["address"]
    event["hours_text"], event["recurrence_text"] = selected["hours"], selected["recurrence"]
    event["forecast_rule"] = explicit_rule(selected["recurrence"]) if publisher == PUBLISHER else None
    source_rows = [v for v in event.get("source_rows") or [] if isinstance(v, dict)
                   and {"address", "hours", "recurrence"} <= set(v)]
    if len(source_rows) > 1:
        # The header edition is shared, its hours and recurrence are not.
        local["conflicts"] = [c for c in local["conflicts"] if c.get("code") != "multiple_recurrence_statements"]
    return local


def _update(row, document, *, read_on, today):
    selected, match = _select(row, document)
    if selected is None:
        return row, {"slug": row["slug"], "status": "held", "reason": match, "fields": []}
    result, local = deepcopy(row), _bound_document(document, selected)
    publisher = document["source"]["publisher"]
    manager = PUBLISHERS[publisher]["manager"]
    event = local["event"]
    previous = clean_editorial_evidence(row.get(KEY), row, today=today)
    if row.get(KEY) is not None and previous is None:
        return row, {"slug": row["slug"], "status": "held", "reason": "invalid_previous_editorial_evidence", "fields": []}
    mode = "limit_forecasts"
    if (event.get("occurrences") and event["calendar_complete"] and not event["archive_marker"]
            and not calendar_conflicted(local["conflicts"])
            and not row.get("verificato_il") and not row.get("calendario_fonte")
            and (row.get("date_quality") not in {"confermata", "riportata"}
                 or previous and previous["calendar_mode"] == "reported_explicit")):
        mode = "reported_explicit"
    try:
        evidence = build_evidence(result, local, read_on=read_on, calendar_mode=mode)
    except ValueError:
        # A future/invalid editorial date or unsupported factual shape holds
        # this join; it is not a transport failure or reason to erase the ID.
        return row, {"slug": row["slug"], "status": "held", "reason": "source_evidence_not_bindable", "fields": []}
    if not _ordered(previous, evidence):
        return row, {"slug": row["slug"], "status": "held", "reason": "source_version_ordering_not_proven", "fields": []}
    result[KEY] = evidence
    archive = event["archive_marker"] or bool(event["edition_intervals"] and all(
        interval["end"] < today.isoformat() for interval in event["edition_intervals"]))
    proposed = {}
    # Old editions remain factual history. Their reread cannot re-certify the
    # current address/hours merely because the page was edited recently.
    if not archive:
        for target, source_field in (("indirizzo", "address"), ("orario_testo", "hours")):
            value = selected[source_field]
            if isinstance(value, str) and value.strip() and len(value) <= FIELDS[target]:
                if not any(c.get("field") == ("address" if target == "indirizzo" else "hours")
                           for c in local["conflicts"]):
                    proposed[target] = value
    # Recurrence text is retained in facts. It is not promoted without its
    # full editorial meaning; scope alone must never authorize an expansion.
    accepted, assigned, updated, holds = {}, [], [], []
    prior = clean_receipts(row.get("riscontri_campi"), row, today=today)
    latest = None
    if proposed:
        receipt_id = PUBLISHERS[publisher]["stem"] + "-detail:" + document["source"]["source_id"]
        if len(receipt_id) > 100:
            receipt_id = PUBLISHERS[publisher]["stem"] + "-detail:" + fingerprint(document["source"]["source_id"])
        latest = make_receipt({**row, **proposed}, values=proposed,
            source_url=row["url_fonte"], source_name=publisher, source_id=receipt_id,
            source_row=selected["source_row_id"], read_on=read_on,
            source_updated_on=evidence["modified_on"], source_sha256=evidence["source_sha256"],
            scope="pagina", method="pagina_primaria_revisionata",
            fingerprint_kind="web_extracted_text" if evidence["hash_basis"] == "connector_utf8_text" else "html_bytes")
        for field, value in proposed.items():
            current = row.get(field) or ""
            if current == value:
                accepted[field] = value
            elif row.get("verificato_il") or field == "indirizzo" and row.get("position_quality") == "precisa":
                holds.append({"field": field, "reason": "human_verification_or_precise_location"})
            elif not current:
                result[field] = value
                accepted[field] = value
                assigned.append(field)
            elif managed_update_allowed(row, latest, field, manager=manager, today=today):
                result[field] = value
                accepted[field] = value
                updated.append(field)
            else:
                holds.append({"field": field, "reason": "existing_field_not_owned_or_conflicting"})
        kept = retire_superseded_receipts(row, latest, today=today)
        if accepted:
            receipt = {**latest, "valori": accepted}
            if assigned:
                receipt = mark_managed_fields(receipt, assigned, manager=manager)
            if updated:
                receipt = mark_managed_fields(receipt, updated, manager=manager, previous=row)
            result["riscontri_campi"] = clean_receipts([*kept, receipt], result, today=today)
        elif kept != prior:
            result["riscontri_campi"] = kept
    result, calendar_reason = apply_editorial_scope(result, today=today)
    changed = sorted(k for k in set(row) | set(result) if row.get(k) != result.get(k))
    return result, {"slug": row["slug"], "status": "changed" if changed else "observed",
        "reason": match, "fields": changed, "accepted_fields": accepted,
        "field_holds": holds, "calendar_disposition": calendar_reason,
        "calendar_mode": mode,
        "historical_edition": archive, "source_row_id": selected["source_row_id"],
        "before_sha256": fingerprint(row), "after_sha256": fingerprint(result)}


def _reconcile(rows, documents, *, today):
    result, outcomes, seen = deepcopy(rows), [], set()
    for observed in documents:
        if not isinstance(observed, dict) or set(observed) != {"read_on", "parsed"}:
            raise ValueError("Editorial document lost its actual read date")
        doc, read_on = observed["parsed"], observed["read_on"]
        source = _valid_document(doc, read_on, today)
        url = source["requested_url"]
        if url in seen:
            raise ValueError("Repeated editorial primary URL in a cycle batch")
        seen.add(url)
        matches = [i for i, r in enumerate(result) if r.get("url_fonte") == url]
        if not matches:
            raise ValueError("Editorial document is not an existing catalog primary URL")
        for index in matches:
            result[index], outcome = _update(result[index], doc, read_on=read_on, today=today)
            outcomes.append({"url": url, **outcome})
    return result, outcomes


def preview(rows, documents, *, today, publisher=PUBLISHER):
    if publisher not in PUBLISHERS or any(v.get("parsed", {}).get("source", {}).get("publisher") != publisher for v in documents):
        raise ValueError("Mixed or unreviewed editorial publisher batch")
    if len(documents) > PUBLISHERS[publisher]["max_details"] or len({r.get("slug") for r in rows}) != len(rows):
        raise ValueError("Unbounded editorial batch or repeated catalog identities")
    result, outcomes = _reconcile(rows, documents, today=today)
    report = {"schema": 1, "publisher": publisher, "date": today.isoformat(),
        "input_sha256": fingerprint(rows), "output_sha256": fingerprint(result),
        "documents": deepcopy(documents), "outcomes": outcomes,
        "changed_existing_ids": [v["slug"] for v in outcomes if v["status"] == "changed"],
        "new_market_ids": [], "removed_market_ids": [], "individual_openings_confirmed": 0,
        "coordinates_assigned": 0, "authenticated_publisher_reuse_claimed": False}
    verify_changes(rows, result, report, today=today)
    return result, report


def verify_changes(before, after, report, *, today):
    if (not isinstance(report, dict) or report.get("schema") != 1 or report.get("publisher") not in PUBLISHERS
            or report.get("date") != today.isoformat() or report.get("new_market_ids") != []
            or report.get("removed_market_ids") != [] or report.get("individual_openings_confirmed") != 0
            or report.get("coordinates_assigned") != 0 or report.get("authenticated_publisher_reuse_claimed") is not False
            or report.get("input_sha256") != fingerprint(before) or report.get("output_sha256") != fingerprint(after)
            or not isinstance(report.get("documents"), list)
            or len(report["documents"]) > PUBLISHERS[report["publisher"]]["max_details"]):
        raise ValueError("Invalid editorial candidate proof")
    if [r.get("slug") for r in before] != [r.get("slug") for r in after]:
        raise ValueError("Editorial refresh changed the original identity list")
    if any(v.get("parsed", {}).get("source", {}).get("publisher") != report["publisher"] for v in report["documents"]):
        raise ValueError("Editorial certificate mixed publisher identities")
    expected, outcomes = _reconcile(before, report["documents"], today=today)
    if expected != after or outcomes != report.get("outcomes") or report.get("changed_existing_ids") != [
            v["slug"] for v in outcomes if v["status"] == "changed"]:
        raise ValueError("Editorial candidate cannot be reconstructed from the observed source facts")
    for old, new in zip(before, after):
        if {k for k in set(old) | set(new) if old.get(k) != new.get(k)} - MUTABLE:
            raise ValueError("Editorial refresh altered an unowned catalog field")
    return {"release_safe": True, "retained_ids": len(before), "new_ids": 0,
            "changed_existing_ids": len(report["changed_existing_ids"])}


def verify_exported(rows, report, *, today):
    catalog = {r["slug"]: r for r in rows}
    if len(catalog) != len(rows):
        raise ValueError("Editorial export contains repeated identities")
    documents = {v["parsed"]["source"]["requested_url"]: v for v in report.get("documents", [])}
    checked = 0
    for outcome in report.get("outcomes", []):
        if outcome["status"] == "held":
            continue
        row = catalog.get(outcome["slug"])
        observed = documents.get(outcome["url"])
        if row is None or observed is None:
            raise ValueError("Editorial-supported identity or source disappeared from export")
        evidence = clean_editorial_evidence(row.get(KEY), row, today=today)
        if (not evidence or evidence["read_on"] != observed["read_on"]
                or evidence["source_sha256"] != observed["parsed"]["source"]["html_sha256"]
                or evidence["facts"].get("selected_row_id") != outcome["source_row_id"]):
            raise ValueError("Editorial-supported row lost its exact source evidence")
        _valid_document(observed["parsed"], observed["read_on"], today)
        selected, _ = _select(row, observed["parsed"])
        if selected is None or evidence != build_evidence(row,
                _bound_document(observed["parsed"], selected), read_on=observed["read_on"],
                calendar_mode=outcome.get("calendar_mode")):
            raise ValueError("Exported editorial facts differ from the observed source document")
        for field, value in outcome["accepted_fields"].items():
            if row.get(field) != value or not any(
                    r["url"] == outcome["url"] and r["sha256"] == evidence["source_sha256"]
                    and r["valori"].get(field) == value
                    for r in clean_receipts(row.get("riscontri_campi"), row, today=today)):
                raise ValueError("Editorial-supported field lost its value or receipt")
        scoped, _ = apply_editorial_scope(row, today=today)
        if any(row.get(k) != scoped.get(k) for k in ("date", "date_quality", "proiezione_regola",
                                                   "proiezione_generata_il", "proiezione_fonte")):
            raise ValueError("Export reanimated dates outside the editorial evidence")
        if (evidence["calendar_mode"] == "reported_explicit" and row.get("date_quality") == "riportata"
                and not valid_editorial_reported_dates(row, today=today)):
            raise ValueError("Editorial reported dates lack independent occurrence proof")
        checked += 1
    return {"release_safe": True, "editorial_identities_checked": checked}


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def _http(url, *, timeout, max_bytes, accept):
    # Every network target is a fixed publisher host and is checked before
    # each request; redirected destinations are checked separately below.
    host = urlsplit(url).hostname
    if host not in {"www.eventiesagre.it", "www.cosedicasa.com"}:
        raise ValueError("Unreviewed editorial transport host")
    for item in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(item[4][0]).is_global:
            raise ValueError("Editorial publisher DNS is not public")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept,
                                    "Accept-Encoding": "identity"})
    with build_opener(_NoRedirect).open(request, timeout=timeout) as response:
        if (response.geturl() != url or response.status != 200
                or accept not in response.headers.get("Content-Type", "").casefold()
                or response.headers.get("Content-Encoding", "identity").casefold() not in {"", "identity"}):
            raise ValueError("Editorial response type or destination changed")
        length = response.headers.get("Content-Length")
        expected = int(length) if length is not None else None
        if expected is not None and not 1 <= expected <= max_bytes:
            raise ValueError("Editorial response exceeds its byte limit")
        body = response.read(max_bytes + 1)
        if not body or len(body) > max_bytes or expected is not None and expected != len(body):
            raise ValueError("Editorial response is incomplete or oversized")
    return body, url


def _delay(robots, minimum):
    delay = max(minimum, robots.crawl_delay(USER_AGENT) or robots.crawl_delay("*") or 0)
    rate = robots.request_rate(USER_AGENT) or robots.request_rate("*")
    if rate and rate.requests > 0:
        delay = max(delay, rate.seconds / rate.requests)
    if delay > 30:
        raise ValueError("Editorial publisher pacing exceeds the bounded run")
    return delay


def _pack(page):
    body = page["body"]
    return {k: v for k, v in page.items() if k != "body"} | {
        "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest(),
        "body_gzip_base64": base64.b64encode(gzip.compress(body, mtime=0)).decode("ascii")}


def validate_redirects(requested_url, final_url, redirects):
    """Validate the actual bounded HTTP chain; canonical tags are not hops."""
    expected = source_identity(requested_url)
    if expected is None or not isinstance(redirects, list) or len(redirects) > 2:
        raise ValueError("Invalid editorial transport alias proof")
    target, seen = requested_url, {requested_url}
    for hop in redirects:
        if (not isinstance(hop, dict) or set(hop) != {"from", "to", "status"}
                or hop["from"] != target or type(hop["status"]) is not int
                or hop["status"] not in {301, 302, 303, 307, 308}
                or not isinstance(hop["to"], str) or hop["to"] in seen):
            raise ValueError("Editorial redirect proof lost its ordered HTTP chain")
        incoming = source_identity(hop["to"])
        if (incoming is None or incoming[0] != expected[0]
                or expected[0] == PUBLISHER and incoming != expected):
            raise ValueError("Editorial redirect changed publisher or numeric source ID")
        target = hop["to"]
        seen.add(target)
    if target != final_url:
        raise ValueError("Editorial final destination has no observed redirect chain")
    return bool(redirects)


def _unpack(entry, *, today):
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(base64.b64decode(entry["body_gzip_base64"], validate=True))) as stream:
            body = stream.read(MAX_BYTES + 1)
    except (OSError, ValueError, TypeError, KeyError, EOFError):
        raise ValueError("Invalid compressed editorial checkpoint") from None
    page = {k: entry.get(k) for k in ("requested_url", "final_url", "read_on", "redirects", "redirect_observed")}
    page["body"] = body
    if (not 100 <= len(body) <= MAX_BYTES or _pack(page) != entry
            or as_day(page["read_on"]) != today
            or type(page["redirect_observed"]) is not bool
            or page["redirect_observed"] != validate_redirects(
                page["requested_url"], page["final_url"], page["redirects"])):
        raise ValueError("Editorial checkpoint content or identity changed")
    return page


def _verify_checkpoint_state(before, after, attempts, pages, *, today):
    """Unattempted URLs cannot acquire reads or completed cycles on resume."""
    expected = deepcopy(before)
    page_by_url = {v["requested_url"]: v for v in pages}
    if len(page_by_url) != len(pages):
        raise ValueError("Editorial checkpoint repeated a successful response")
    for attempt in attempts:
        if (not isinstance(attempt, dict) or set(attempt) - {"url", "status", "network_attempted", "error_type"}
                or not {"url", "status", "network_attempted"} <= set(attempt)
                or type(attempt["network_attempted"]) is not bool
                or attempt["status"] not in STATUSES - {"unread"}
                or attempt["url"] not in expected["resources"]):
            raise ValueError("Invalid editorial checkpoint attempt")
        entry = expected["resources"][attempt["url"]]
        entry.update(last_attempt=today.isoformat(), attempts=entry["attempts"] + 1,
                     attempt_cycle=before["cycle"], status=attempt["status"], last_error=None)
        if attempt["status"] in {"retrieved", "layout_held"}:
            page = page_by_url.get(attempt["url"])
            if page is None or not attempt["network_attempted"]:
                raise ValueError("Editorial checkpoint read lacks its HTTP response")
            entry.update(last_read=page["read_on"], read_cycle=before["cycle"],
                         sha256=hashlib.sha256(page["body"]).hexdigest())
            try:
                parse_document(page["body"], requested_url=page["requested_url"],
                               final_url=page["final_url"], today=today)
                parsed = True
            except (ValueError, KeyError, TypeError):
                parsed = False
            if parsed != (attempt["status"] == "retrieved"):
                raise ValueError("Editorial checkpoint parse status differs from its saved bytes")
            if parsed:
                entry["last_parsed"] = page["read_on"]
            else:
                entry["last_error"] = "SourceLayoutChanged"
        elif attempt["status"] == "robots_denied":
            if attempt["network_attempted"]:
                raise ValueError("Robots-denied editorial request claims an HTTP read")
            entry["last_error"] = "RobotsDenied"
        elif attempt["status"] == "unavailable":
            error = attempt.get("error_type")
            if not isinstance(error, str) or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,99}", error):
                raise ValueError("Editorial checkpoint failure lost its error type")
            entry["last_error"] = error
    if expected == after:
        return
    if expected["resources"] and all(v["attempt_cycle"] == before["cycle"] for v in expected["resources"].values()):
        expected["last_completed_cycle"] = before["cycle"]
        expected["last_completed_on"] = today.isoformat()
    if expected != after:
        raise ValueError("Editorial checkpoint changed unobserved queue history")


def run(rows, *, out, today, baseline_signature, policy_digest, policy=None,
        previous_state=None, offline=False, resume=False, fetcher=None,
        deadline=None, monotonic=time.monotonic, sleep=time.sleep, now=None, publisher=PUBLISHER):
    """Return (candidate, report, preserve_ids); state is in report['state'].

`deadline` is an optional shared monotonic editorial deadline. EES and CDC
may run concurrently with independent per-host queues and pacing. Resume only
replays captured responses and makes no new request. Public state contains
URLs and transport history; raw responses stay in the temporary checkpoint.
"""
    policy = validate_policy(policy, publisher=publisher)
    if not isinstance(today, date) or not baseline_signature or not policy_digest:
        raise ValueError("Missing editorial candidate context")
    out = Path(out)
    state = seed_state(rows, previous_state, today=today, publisher=publisher)
    state_before = deepcopy(state)
    robots_url = "https://www." + publisher + "/robots.txt"
    context = {"date": today.isoformat(), "baseline": baseline_signature,
        "pipeline_policy": policy_digest, "policy": policy, "catalog": fingerprint(rows),
        "state_before": fingerprint(state)}
    checkpoint = out / ("sources/" + PUBLISHERS[publisher]["stem"] + "-detail-pages.json")
    started = monotonic()
    end = min(started + policy["max_seconds"], deadline) if deadline is not None else started + policy["max_seconds"]
    http = fetcher or _http
    now = now or (lambda: datetime.now(timezone.utc))
    pages, attempts = [], []
    robots_proof = None
    network_requests = 0
    status, stop_reason = "disabled", "disabled"

    def save_checkpoint():
        _write(checkpoint, {"schema": 1, "context": context, "state": state,
            "pages": [_pack(v) for v in pages], "attempts": attempts,
            "robots": robots_proof, "network_requests": network_requests})

    if policy["enabled"] and resume:
        status, stop_reason = "resume_missing_evidence", "resume_missing_evidence"
        if checkpoint.is_file():
            if checkpoint.stat().st_size > MAX_DETAILS * MAX_BYTES * 2 + MAX_STATE_BYTES:
                raise ValueError("Editorial checkpoint exceeds its size limit")
            saved = json.loads(checkpoint.read_text("utf-8"))
            if saved.get("schema") != 1 or saved.get("context") != context:
                raise ValueError("Editorial resume belongs to a different baseline, policy or queue")
            state = deepcopy(validate_state(saved.get("state"), today=today, publisher=publisher))
            if set(state["resources"]) != set(catalog_urls(rows, publisher=publisher)):
                raise ValueError("Editorial checkpoint contains URLs outside the current catalog")
            pages = [_unpack(v, today=today) for v in saved.get("pages", [])]
            attempts = saved.get("attempts")
            if (not isinstance(attempts, list) or len(attempts) > policy["max_details"]
                    or len(pages) > len(attempts) or len({v["url"] for v in attempts}) != len(attempts)
                    or any(v["url"] not in state["resources"] for v in attempts)):
                raise ValueError("Editorial checkpoint changed its attempted source set")
            success = {v["url"]: v for v in attempts if v.get("status") in {"retrieved", "layout_held"}}
            if {v["requested_url"] for v in pages} != set(success):
                raise ValueError("Editorial checkpoint lost a successful HTTP response")
            for page in pages:
                item = state["resources"][page["requested_url"]]
                if item["last_read"] != page["read_on"] or item["sha256"] != hashlib.sha256(page["body"]).hexdigest():
                    raise ValueError("Editorial checkpoint disagrees with its persisted state")
            _verify_checkpoint_state(state_before, state, attempts, pages, today=today)
            robots_proof = saved.get("robots")
            recorded_requests = saved.get("network_requests")
            attempted_http = sum(v["network_attempted"] for v in attempts)
            if (type(recorded_requests) is not int or not 0 <= recorded_requests <= 1 + 3 * policy["max_details"]
                    or recorded_requests < bool(robots_proof) + attempted_http
                    or pages and not robots_proof):
                raise ValueError("Editorial checkpoint transport counts are inconsistent")
            status, stop_reason = "resumed", "saved_checkpoint_only"
    elif policy["enabled"] and offline:
        status, stop_reason = "offline_skipped", "offline"
    elif policy["enabled"]:
        status, stop_reason = "running", "queue_exhausted"
        pending = sorted((url for url, v in state["resources"].items()
                          if v["attempt_cycle"] < state["cycle"]),
                         key=lambda url: (state["resources"][url]["last_attempt"] or "", url))
        if not state["resources"]:
            status, stop_reason = "completed", "no_catalog_rows"
        robots = None
        if pending and end - monotonic() >= 1:
            try:
                stamp = now()
                if stamp.tzinfo is None or stamp.date() != today:
                    raise ValueError("Live editorial read date differs from the candidate date")
                network_requests += 1
                raw, final = http(robots_url, timeout=min(18, max(.1, end - monotonic())),
                                  max_bytes=55_000, accept="text/plain")
                if final != robots_url or not isinstance(raw, bytes) or not 1 <= len(raw) <= 55_000:
                    raise ValueError("Editorial robots response changed destination or size")
                text = raw.decode("utf-8-sig", errors="strict")
                if not re.search(r"(?im)^\s*user-agent\s*:", text) or "<html" in text.lower():
                    raise ValueError("Editorial robots contains no readable policy")
                robots = RobotFileParser(robots_url)
                robots.parse(text.splitlines())
                pause = _delay(robots, policy["min_delay_seconds"])
                robots_proof = {"url": robots_url, "read_on": stamp.date().isoformat(),
                                "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw),
                                "pacing_seconds": pause}
            except (OSError, HTTPException, ValueError, UnicodeError) as error:
                status, stop_reason = "robots_unavailable", type(error).__name__
        elif pending:
            status, stop_reason = "time_budget_exhausted", "time_budget"
        if robots is not None:
            for url in pending:
                if len(attempts) >= policy["max_details"]:
                    stop_reason = "detail_limit"
                    break
                if end - monotonic() <= pause + 1:
                    stop_reason = "time_budget"
                    break
                entry = state["resources"][url]
                entry.update(last_attempt=today.isoformat(), attempts=entry["attempts"] + 1,
                             attempt_cycle=state["cycle"], status="inflight", last_error=None)
                attempt = {"url": url, "status": "inflight", "network_attempted": False}
                attempts.append(attempt)
                save_checkpoint()
                if not robots.can_fetch(USER_AGENT, url):
                    entry.update(status="robots_denied", last_error="RobotsDenied")
                    attempt.update(status="robots_denied")
                    save_checkpoint()
                    continue
                target, redirects = url, []
                try:
                    for hop in range(3):
                        if end - monotonic() <= pause + 1:
                            raise TimeoutError("Editorial shared deadline exhausted")
                        sleep(pause)
                        remaining = end - monotonic()
                        if remaining <= 0:
                            raise TimeoutError("Editorial shared deadline exhausted")
                        network_requests += 1
                        attempt["network_attempted"] = True
                        try:
                            body, final = http(target, timeout=min(18, remaining), max_bytes=MAX_BYTES, accept="text/html")
                            break
                        except HTTPError as error:
                            if error.code not in {301, 302, 303, 307, 308} or hop == 2:
                                raise
                            redirected = urljoin(target, error.headers.get("Location", ""))
                            redirect_identity = source_identity(redirected)
                            if (not redirect_identity or redirect_identity[0] != publisher
                                    or publisher == PUBLISHER and redirect_identity != source_identity(url)
                                    or not robots.can_fetch(USER_AGENT, redirected)):
                                raise ValueError("Editorial redirect changed source ID or robots scope") from None
                            redirects.append({"from": target, "to": redirected, "status": error.code})
                            target = redirected
                    if ((source_identity(final) or (None,))[0] != publisher
                            or publisher == PUBLISHER and source_identity(final) != source_identity(url) or final != target
                            or not isinstance(body, bytes) or not 100 <= len(body) <= MAX_BYTES):
                        raise ValueError("Editorial response changed its exact source identity")
                    stamp = now()
                    if stamp.tzinfo is None or stamp.date() != today:
                        raise ValueError("Editorial acquisition crossed the candidate date")
                    page = {"requested_url": url, "final_url": final,
                            "read_on": stamp.date().isoformat(), "body": body,
                            "redirects": redirects,
                            "redirect_observed": validate_redirects(url, final, redirects)}
                    pages.append(page)
                    entry.update(last_read=page["read_on"], read_cycle=state["cycle"],
                                 sha256=hashlib.sha256(body).hexdigest(), status="retrieved")
                    try:
                        parse_document(body, requested_url=url, final_url=final, today=today)
                        entry["last_parsed"] = page["read_on"]
                    except (ValueError, KeyError, TypeError):
                        entry.update(status="layout_held", last_error="SourceLayoutChanged")
                    attempt["status"] = entry["status"]
                except (OSError, HTTPException, ValueError, TypeError) as error:
                    entry.update(status="unavailable", last_error=type(error).__name__)
                    attempt.update(status="unavailable", error_type=type(error).__name__)
                save_checkpoint()
            status = "completed"
    if state["resources"] and all(v["attempt_cycle"] == state["cycle"] for v in state["resources"].values()):
        state["last_completed_cycle"] = state["cycle"]
        state["last_completed_on"] = today.isoformat()
    documents, parse_holds = [], []
    for page in pages:
        try:
            doc = parse_document(page["body"], requested_url=page["requested_url"],
                                 final_url=page["final_url"], today=today)
            documents.append({"read_on": page["read_on"], "parsed": doc})
        except (ValueError, KeyError, TypeError) as error:
            parse_holds.append({"url": page["requested_url"], "reason": type(error).__name__})
    result, evidence = preview(rows, documents, today=today, publisher=publisher)
    report = {"schema": 1, "publisher": publisher, "date": today.isoformat(), "enabled": policy["enabled"],
        "status": status, "stop_reason": stop_reason, "policy": policy,
        "network_requests": network_requests, "details_attempted": len(attempts),
        "source_pages_read": len(pages), "documents_parsed": len(documents),
        "robots": robots_proof, "attempts": attempts, "parse_holds": parse_holds,
        "source_pages": [{k: v for k, v in _pack(page).items() if k != "body_gzip_base64"} for page in pages],
        "elapsed_seconds": round(max(0, monotonic() - started), 3),
        "state": validate_state(state, today=today, publisher=publisher),
        "progress": progress(state, today=today, overdue_after_days=policy["overdue_after_days"]),
        "evidence": evidence}
    if not resume and policy["enabled"] and not offline:
        save_checkpoint()
    _write(out / state_filename(publisher), state)
    _write(out / report_filename(publisher), report)
    preserve = {v["slug"] for v in evidence["outcomes"] if v["status"] != "held"}
    return result, report, preserve
