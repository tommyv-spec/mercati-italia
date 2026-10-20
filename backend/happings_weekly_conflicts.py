"""Explicit address replacements associated against the complete catalog.

This negative proof can qualify a saved address, never replace it. Merely
finding a different venue is insufficient: the current editorial paragraph
must name the old venue as replaced, and both source and catalog city/day
cohorts must be unique. Source documents are rebound to actual HTML before
application; later diff guards reconstruct the same bounded warnings.
"""
from __future__ import annotations

from collections import defaultdict
from copy import deepcopy
import hashlib
import json
import re

from happings_weekly_layout import fold, WEEKDAYS, MAX_PUBLISHER_ITEMS
from happings_editorial_weekly_layout import (CURRENT_HEADING, NARRATIVE, APPOINTMENT,
    DAY_PATTERN, _clock)

OLD_PLACES = re.compile(
    r"Queste indicazioni sostituiscono i vecchi riferimenti(?: al mercato cittadino)? in (.+)", re.I)
DOCUMENT_KEYS = {"schema", "requested_url", "final_url", "source_html_sha256",
                 "source_bytes", "editorial_sections", "rows", "page_metadata"}


def document_for(page, parsed):
    if not getattr(parsed, "editorial_sections", None):
        return None
    return {"schema": 1, "requested_url": page["requested_url"], "final_url": page["final_url"],
            "source_html_sha256": hashlib.sha256(page["html"]).hexdigest(),
            "source_bytes": len(page["html"]),
            "editorial_sections": deepcopy(parsed.editorial_sections), "rows": deepcopy(parsed.rows),
            "page_metadata": deepcopy(parsed.page_metadata)}


def verify_source_pages(documents, pages, *, today):
    """Bind every structured editorial document to the captured response bytes."""
    from happings_weekly_layout import parse
    expected = []
    for page in pages:
        try:
            parsed = parse(page["html"], source_url=page["final_url"], observed_on=today)
        except ValueError:
            continue
        document = document_for(page, parsed)
        if document is not None:
            expected.append(document)
    if documents != expected:
        raise ValueError("Happings editorial conflict evidence differs from captured HTML")
    return True


def _current_replacement(row):
    """Reconstruct only the narrow current paragraph grammar, not arbitrary prose."""
    from stored_market_sibling_proposals import safe_stored_street
    scope, evidence = row.get("editorial_scope"), row.get("source_evidence")
    if (not isinstance(scope, dict) or scope.get("status") != "current"
            or scope.get("reason") != "explicit_updated_section" or scope.get("notices")
            or not CURRENT_HEADING.fullmatch(fold(scope.get("heading")))
            or row.get("calendar_scope") or row.get("has_specific_location") is not True
            or not isinstance(evidence, dict)):
        return None
    text, paragraph, notice = (evidence.get(key) for key in ("text", "paragraph_text", "replacement_notice"))
    if (not all(isinstance(value, str) and 0 < len(value) <= 1200 for value in (text, paragraph, notice))
            or text not in paragraph or notice not in paragraph
            or paragraph.index(text) >= paragraph.index(notice)):
        return None
    statement = NARRATIVE.fullmatch(text) or APPOINTMENT.fullmatch(text)
    replacement = OLD_PLACES.fullmatch(notice)
    if statement is None or replacement is None:
        return None
    days = [WEEKDAYS.index(fold(value)) for value in re.findall(DAY_PATTERN, statement["days"], re.I)]
    if (type(row.get("weekday")) is not int or row["weekday"] not in days
            or row.get("city_key") != fold(statement["city"]) or row.get("city") != statement["city"]
            or row.get("place") != statement["place"]
            or row.get("clock_hours") != {"start_time": _clock(statement["start"]),
                                          "end_time": _clock(statement["end"])}):
        return None
    places = re.split(r"\s+e in\s+", replacement[1], flags=re.I)
    if not 1 <= len(places) <= 8 or any(not safe_stored_street(place) for place in places):
        return None
    return places


def _possible_days(row):
    # Ambiguous catalog weekdays also compete. A second card saying Wed in
    # its name and Thu in its recurrence cannot be dropped to prove uniqueness.
    text = fold(" ".join(str(row.get(key) or "") for key in ("nome", "slug", "ricorrenza_testo")))
    return {index for index, day in enumerate(WEEKDAYS) if re.search(r"\b" + day + r"\b", text)}


def propose(base, documents, *, today, apply_authorized, rights_gate_passed):
    import happings_source_enrichment as weekly
    if (not isinstance(documents, list) or len(documents) > weekly.MAX_REQUESTS_PER_RUN
            or type(apply_authorized) is not bool or type(rights_gate_passed) is not bool
            or apply_authorized and not rights_gate_passed):
        raise ValueError("Invalid Happings negative-evidence scope")
    if not documents:
        return []
    from field_conflicts import make_address_conflict
    catalog = defaultdict(list)
    for row in base:
        for day in _possible_days(row):
            catalog[(fold(row.get("citta")), str(row.get("provincia") or "").upper(), day)].append(row)
    result = []
    for document in documents:
        if (not isinstance(document, dict) or set(document) != DOCUMENT_KEYS or document.get("schema") != 1
                or not isinstance(document.get("rows"), list)
                or not 1 <= len(document["rows"]) <= MAX_PUBLISHER_ITEMS
                or len(json.dumps(document, ensure_ascii=False).encode()) > weekly.MAX_RESPONSE_BYTES
                or not weekly.allowed_url(document.get("requested_url"), document.get("requested_url"), document.get("final_url"))
                or not re.fullmatch(r"[0-9a-f]{64}", str(document.get("source_html_sha256") or ""))
                or type(document.get("source_bytes")) is not int
                or not 300 <= document["source_bytes"] <= weekly.MAX_RESPONSE_BYTES):
            raise ValueError("Unbounded or unbound Happings editorial source document")
        source = defaultdict(list)
        for row in document["rows"]:
            if not isinstance(row, dict) or type(row.get("weekday")) is not int or not 0 <= row["weekday"] <= 6:
                raise ValueError("Invalid Happings editorial source row")
            source[(row.get("city_key"), row["weekday"])].append(row)
        for pair, source_rows in source.items():
            if len(source_rows) != 1:
                continue
            src = source_rows[0]
            previous_places = _current_replacement(src)
            if previous_places is None:
                continue
            candidates = [row for row in base if row.get("fonte") == weekly.PUBLISHER
                          and fold(row.get("citta")) == pair[0] and weekly._weekly_day(row) == pair[1]
                          and weekly.record_matches_page(row, document["requested_url"], document["final_url"])]
            if len(candidates) != 1:
                continue
            target = candidates[0]
            cohort = catalog[(pair[0], str(target.get("provincia") or "").upper(), pair[1])]
            if (len(cohort) != 1 or cohort[0]["slug"] != target["slug"]
                    or target.get("indirizzo") not in previous_places
                    or fold(target["indirizzo"]) == fold(src["place"])):
                continue
            evidence = src["source_evidence"]
            try:
                conflict = make_address_conflict(
                    target, source_value=src["place"], source_day=pair[1],
                    requested_url=document["requested_url"], final_url=document["final_url"],
                    read_on=today.isoformat(), html_sha256=document["source_html_sha256"],
                    source_bytes=document["source_bytes"], selector=evidence["selector"],
                    fragment=evidence["paragraph_text"], today=today)
            except ValueError:
                continue
            item = {"market_id": target["slug"], "conflict": conflict,
                           "source_url": document["final_url"], "source_requested_url": document["requested_url"],
                           "source_html_sha256": document["source_html_sha256"], "source_relation": "primary",
                           **({"page_metadata": document["page_metadata"]} if document["page_metadata"] is not None else {}),
                           "source_city": target["citta"], "source_province": target["provincia"],
                           "source_region": target["regione"], "source_day": pair[1],
                           "source_value": src["place"], "observed_at": today.isoformat(),
                           "apply_authorized": apply_authorized, "rights_gate_passed": rights_gate_passed,
                           "individually_confirmed": False, "published_opening_verified": False,
                           "coordinate_added": False}
            permitted = apply_conflict(target, {**item, "apply_authorized": True,
                                                "rights_gate_passed": True}, today=today)
            if conflict not in permitted.get("conflitti_campi", []):
                # Capacity or non-ordered evidence stays held; an authorized
                # flag is not a claim that an unpersisted warning was applied.
                continue
            result.append(item)
    if len({item["market_id"] for item in result}) != len(result):
        raise ValueError("Repeated Happings negative-evidence identity")
    return result


def apply_conflict(before, item, *, today):
    result = deepcopy(before)
    if item is None:
        return result
    from field_conflicts import KEY, MAX_CONFLICTS, clean_conflicts, valid_conflict
    if (item.get("market_id") != before.get("slug")
            or not valid_conflict(item.get("conflict"), before, today=today)
            or item.get("observed_at") != today.isoformat()
            or type(item.get("apply_authorized")) is not bool
            or type(item.get("rights_gate_passed")) is not bool
            or item["apply_authorized"] and not item["rights_gate_passed"]):
        raise ValueError("Unbound Happings address warning")
    if not item["apply_authorized"]:
        return result
    prior = clean_conflicts(before.get(KEY, []), before, today=today)
    new = item["conflict"]
    # Same-day different source versions cannot silently supersede evidence.
    for old in prior:
        if old["url_finale"] == new["url_finale"] and old["letto_il"] >= new["letto_il"]:
            if old["letto_il"] > new["letto_il"] or old["sha256"] != new["sha256"]:
                return result
    retained = [old for old in prior if not (old["url_finale"] == new["url_finale"]
                 and old["giorno_settimana"] == new["giorno_settimana"])]
    if len(retained) >= MAX_CONFLICTS:
        return result
    result[KEY] = clean_conflicts([*retained, new], before, today=today)
    return result
