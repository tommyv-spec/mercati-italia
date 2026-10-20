"""Read-only diagnostics for information lost between source, parser and catalog.

The presence probe reads only already acquired Happings market blocks. It does
not infer source absence from an empty catalog or parser value, perform matching,
authorize assignments, or prove an opening. Source rows and catalog records have
separate denominators: three saved duplicates never become three source venues.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date

from happings_detail_layout import (_Document, _Node, _classes, _key, _lines,
    _raw, _select, _text, _walk, CLOCK_RE, DATE_RE, MONTHS, WEEKDAYS)
from stored_market_sibling_proposals import safe_stored_street

FIELDS = ("indirizzo", "orario_testo", "ricorrenza_testo", "date")
PRESENCE = ("precise", "qualitative", "unclassified", "absent_in_reviewed_scope", "unassessed")
READER = ("parsed", "partial", "missing", "withheld_conflict", "not_applicable", "unassessed")
STATES = ("source_absent", "source_qualitative", "source_unclassified", "source_unassessed",
          "source_present_parser_missing", "source_present_parser_partial", "source_present_parser_held_conflict",
          "source_present_parsed_identity_unresolved", "source_present_parsed_held",
          "source_present_parsed_available", "source_present_parsed_retained_as_detail",
          "source_present_parsed_supported", "source_present_parsed_applied")
DAYPART = re.compile(r"\b(?:mattin[ao]|pomeriggio|sera|tutt[oa] (?:il )?giorno)\b", re.I)
INTEGER_CLOCK_RANGE = re.compile(r"\bdalle?\s+(?:[01]?\d|2[0-3])\s+alle?\s+(?:[01]?\d|2[0-4])\b", re.I)
VAGUE_PLACE = re.compile(r"(?:il )?centro(?: storico| cittadino)?|(?:varie |tutte le )?(?:vie|piazze)(?: del centro)?|zona centrale")
DAY_NAMES = ("lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica")
MAX_EXAMPLES = 24


def _tree(html):
    if not isinstance(html, bytes) or not 1 <= len(html) <= 2_600_000:
        return None
    try:
        tree = _Document()
        tree.feed(html.decode("utf-8-sig", "replace"))
        tree.close()
        return tree.root
    except (ValueError, RecursionError):
        return None


def _clock_tokens(text):
    text = str(text or "")
    return {m[1].replace(".", ":").zfill(5) for m in CLOCK_RE.finditer(text)
            if not re.search(r"(?:€|\bEUR)\s*$", text[max(0, m.start() - 10):m.start()], re.I)
            and not re.match(r"\s*(?:€|EUR\b|euro\b)", text[m.end():m.end() + 12], re.I)}


def _dated_tokens(text):
    """Recognize complete source dates, not month/day statements lacking a year."""
    result = set()
    for match in DATE_RE.finditer(str(text or "")):
        try:
            result.add(date(int(match["year"]), MONTHS[match["month"].lower()], int(match["day"])).isoformat())
        except ValueError:
            pass
    for match in re.finditer(r"(?<!\d)(\d{4})-(\d{2})-(\d{2})(?!\d)", str(text or "")):
        try:
            result.add(date(*map(int, match.groups())).isoformat())
        except ValueError:
            pass
    for match in re.finditer(r"(?<!\d)(\d{1,2})/(\d{1,2})/(\d{4})(?!\d)", str(text or "")):
        try:
            day, month, year = map(int, match.groups())
            result.add(date(year, month, day).isoformat())
        except ValueError:
            pass
    return result


def _address_presence(values):
    values = [str(value).strip() for value in values if str(value or "").strip()]
    if not values:
        return "absent_in_reviewed_scope"
    # The source can state a precise street with a separate seasonal qualifier.
    # That is a held scope, not a vague/missing address. No value is assigned here.
    cores = [re.split(r"\s*\(|\b(?:dalle?|orari?|ore)\s+\d", value, maxsplit=1, flags=re.I)[0].strip(" ,;")
             for value in values]
    if any(safe_stored_street(value) for value in cores):
        return "precise"
    if all(VAGUE_PLACE.fullmatch(_key(value)) for value in cores):
        return "qualitative"
    return "unclassified"


def _hours_presence(text):
    if _clock_tokens(text) or INTEGER_CLOCK_RANGE.search(text):
        return "precise"
    if DAYPART.search(text):
        return "qualitative"
    return "absent_in_reviewed_scope"


def _empty_fields():
    return {field: {"source_presence": Counter(), "reader": Counter(), "disposition": Counter(),
                    "catalog_values_applied": 0, "catalog_values_supported": 0,
                    "catalog_values_available": 0, "catalog_detail_only": 0}
            for field in FIELDS}


def _page(html, requested, final, layout):
    return {"requested_url": requested, "final_url": final,
            "source_html_sha256": hashlib.sha256(html).hexdigest(), "layout": layout,
            "probe_status": "assessed", "source_units": 0, "catalog_page_pairs_considered": 0,
            "catalog_page_pairs_linked": 0, "fields": _empty_fields(), "examples": []}


def _observe(page, unit, field, presence, parsed, *, destinations=(), held=False, reasons=()):
    reader = ("unassessed" if presence == "unassessed" else "not_applicable"
              if presence == "absent_in_reviewed_scope" else parsed)
    if presence != "precise":
        state = {"qualitative": "source_qualitative", "unclassified": "source_unclassified",
                 "absent_in_reviewed_scope": "source_absent", "unassessed": "source_unassessed"}[presence]
    elif reader in {"missing", "partial"}:
        state = "source_present_parser_" + reader
    elif reader == "withheld_conflict":
        state = "source_present_parser_held_conflict"
    elif held and not destinations:
        state = "source_present_parsed_held"
    else:
        state = "source_present_parsed_identity_unresolved"
        for disposition in ("applied", "supported", "available", "retained_as_detail"):
            if disposition in destinations:
                state = "source_present_parsed_" + disposition
                break
    item = page["fields"][field]
    item["source_presence"][presence] += 1
    item["reader"][reader] += 1
    item["disposition"][state] += 1
    for disposition, key in (("applied", "catalog_values_applied"), ("supported", "catalog_values_supported"),
                             ("available", "catalog_values_available"), ("retained_as_detail", "catalog_detail_only")):
        item[key] += sum(value == disposition for value in destinations)
    if len(page["examples"]) < MAX_EXAMPLES and not any(
            example["field"] == field and example["disposition"] == state for example in page["examples"]):
        page["examples"].append({"source_unit": unit, "field": field, "source_presence": presence,
                                 "reader": reader, "disposition": state,
                                 "hold_reasons": sorted(set(reasons))})


def _finish(page):
    for field in FIELDS:
        item = page["fields"][field]
        item["source_units_denominator"] = page["source_units"]
        for name, values in (("source_presence", PRESENCE), ("reader", READER), ("disposition", STATES)):
            item[name] = {value: item[name].get(value, 0) for value in values}
            if sum(item[name].values()) != page["source_units"]:
                raise ValueError("Happings diagnostic denominator differs from source units")
        item["linked_precise_source_units"] = sum(item["disposition"]["source_present_parsed_" + state]
                                                   for state in ("available", "supported", "applied"))
    return page


def weekly_page_coverage(html, parsed, *, requested_url, final_url, observations=(),
                         considered_ids=(), holds=None, before=None, after=None):
    """Inspect original listing text independently of extracted field values."""
    page = _page(html, requested_url, final_url, "provincial_weekly_index")
    from happings_editorial_weekly_layout import source_inventory
    from happings_weekly_layout import province_page_key
    try:
        editorial = source_inventory(html, source_province=province_page_key(final_url))
    except (ValueError, RecursionError):
        editorial = None
    if editorial is not None:
        return _editorial_weekly_coverage(page, editorial, parsed, observations=observations,
                                          considered_ids=considered_ids, holds=holds,
                                          before=before, after=after)
    root = _tree(html)
    blocks = _select(root, "happings-seo-content") if root else []
    if len(blocks) != 1:
        page["probe_status"] = "unassessed_layout"
        return _finish(page)
    before, after, holds = before or {}, after or {}, holds or {}
    observations = [item for item in observations if item.get("source_url") == final_url
                    and item.get("source_html_sha256") == page["source_html_sha256"]]
    page["catalog_page_pairs_considered"] = len(set(considered_ids))
    page["catalog_page_pairs_linked"] = len({item["market_id"] for item in observations})
    parsed_by_key = defaultdict(list)
    for row in getattr(parsed, "rows", []):
        parsed_by_key[(_key(row.get("city_label") or row.get("city")), row.get("weekday"),
                       _key(row.get("place_label") or row.get("place")))].append(row)
    weekday = None
    # The probe deliberately does not use parser.rows as its source inventory:
    # a known li omitted by a changed reader must remain visible in diagnostics.
    for node in _walk(blocks[0], scoped=True):
        if node.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            text = _key(_text(node))
            day = re.fullmatch(r"mercati (?:del|della) (" + "|".join(DAY_NAMES)
                               + r")(?: nei comuni di .+)?", text)
            weekday = DAY_NAMES.index(day[1]) if node.tag == "h3" and day else None
        if node.tag != "li":
            continue
        page["source_units"] += 1
        ordinal = page["source_units"]
        text = _text(node)
        match = re.fullmatch(r"\s*ad?\s+(.+?),\s+in\s+(.+?)\s*", text, re.I)
        if match is None or weekday is None or any(n is not node and n.tag == "li" for n in _walk(node, scoped=True)):
            for field in FIELDS:
                _observe(page, ordinal, field, "unassessed", "unassessed")
            continue
        city, place = match.groups()
        place_label = re.sub(r"\s*\((?:la mattina|il mattino|al mattino|il pomeriggio|la sera)\)\s*$", "", place, flags=re.I)
        key = (_key(city), weekday, _key(place_label))
        candidates = parsed_by_key.get(key, [])
        source = candidates.pop(0) if candidates else None
        pair = (_key((source or {}).get("city") or city), weekday)
        linked = [item for item in observations
                  if (_key(item.get("source_city")), item.get("source_day")) == pair
                  and _key(item.get("source_value")) == _key((source or {}).get("place") or place_label)]
        reasons = holds.get(pair, [])
        scope_held = bool(source and source.get("calendar_scope"))
        # Matching holds are reporting outcomes only; they cannot create links.
        held = scope_held or any(reason not in {"no_unique_source_market_city_weekday"} for reason in reasons)
        presences = {"indirizzo": _address_presence([place]), "orario_testo": _hours_presence(place),
                     "ricorrenza_testo": "precise",
                     "date": "precise" if _dated_tokens(place) else "qualitative"
                     if scope_held and any(q.get("reason") == "date_range_scope_unrepresented"
                                          for q in source["calendar_scope"]["qualifiers"])
                     else "absent_in_reviewed_scope"}
        for field in FIELDS:
            parsed_field = bool(source and (field == "indirizzo" and source.get("place")
                                or field == "ricorrenza_testo" and source.get("weekday") == weekday
                                or field == "orario_testo" and presences[field] == "qualitative" and source.get("daypart")
                                or field == "date" and presences[field] == "qualitative" and scope_held))
            destinations = []
            for item in linked:
                if field not in item.get("values", {}):
                    continue
                sid = item["market_id"]
                if not item.get("apply_authorized"):
                    destinations.append("available")
                elif sid in after and after[sid].get(field) == item["values"][field]:
                    destinations.append("applied" if before.get(sid, {}).get(field) != after[sid].get(field) else "supported")
            _observe(page, ordinal, field, presences[field], "parsed" if parsed_field else "missing",
                     destinations=destinations, held=held, reasons=reasons or
                     (["publisher_calendar_scope_unrepresented"] if scope_held else []))
    if not page["source_units"]:
        page["probe_status"] = "unassessed_layout"
    elif any(item["source_presence"]["unassessed"] for item in page["fields"].values()):
        page["probe_status"] = "partially_assessed"
    return _finish(page)


def _editorial_weekly_coverage(page, inventory, parsed, *, observations=(),
                              considered_ids=(), holds=None, before=None, after=None):
    """Probe original editorial units even if the extraction dropped a field."""
    page["layout"] = "editorial_provincial_weekly_guide"
    before, after, holds = before or {}, after or {}, holds or {}
    observations = [item for item in observations if item.get("source_url") == page["final_url"]
                    and item.get("source_html_sha256") == page["source_html_sha256"]]
    page["catalog_page_pairs_considered"] = len(set(considered_ids))
    page["catalog_page_pairs_linked"] = len({item["market_id"] for item in observations})
    rows = defaultdict(list)
    for row in getattr(parsed, "rows", []):
        rows[(_key(row.get("city_label")), row.get("weekday"), _key(row.get("place_label")))].append(row)
    for ordinal, unit in enumerate(inventory["units"], 1):
        page["source_units"] += 1
        place = re.sub(r"\s*\((?:la mattina|il mattino|al mattino|il pomeriggio|la sera)\)\s*$", "",
                       unit["place"], flags=re.I)
        key = (_key(unit["city"]), unit["weekday"], _key(place))
        candidates = rows.get(key, [])
        source = candidates.pop(0) if candidates else None
        pair = (_key((source or {}).get("city") or unit["city"]), unit["weekday"])
        scope_held = unit["editorial_scope"]["status"] != "current" or bool(source and source.get("calendar_scope"))
        reasons = holds.get(pair, []) or ([unit["editorial_scope"]["reason"]] if scope_held else [])
        linked = [item for item in observations
                  if (_key(item.get("source_city")), item.get("source_day")) == pair
                  and _key(item.get("source_value")) == _key((source or {}).get("place") or place)]
        presences = {"indirizzo": _address_presence([unit["place"]]),
                     "orario_testo": _hours_presence(unit["hours_text"] or unit["place"]),
                     "ricorrenza_testo": "precise", "date": "absent_in_reviewed_scope"}
        for field in FIELDS:
            present = bool(source and (field == "indirizzo" and source.get("place")
                           or field == "ricorrenza_testo" and source.get("weekday") == unit["weekday"]
                           or field == "orario_testo" and (source.get("clock_hours") or source.get("daypart"))))
            destinations = []
            for item in linked:
                if field not in item.get("values", {}):
                    continue
                sid = item["market_id"]
                if not item.get("apply_authorized"):
                    destinations.append("available")
                elif sid in after and after[sid].get(field) == item["values"][field]:
                    destinations.append("applied" if before.get(sid, {}).get(field) != after[sid].get(field)
                                        else "supported")
            _observe(page, ordinal, field, presences[field], "parsed" if present else "missing",
                     destinations=destinations, held=scope_held or bool(reasons), reasons=reasons)
    return _finish(page)


def _event_schemas(root, url, title):
    """Only Event nodes explicitly bound to this observed URL and visible title."""
    def values(value):
        if isinstance(value, list):
            for item in value:
                yield from values(item)
        elif isinstance(value, dict):
            kind = value.get("@type")
            if kind == "Event" or isinstance(kind, list) and "Event" in kind:
                yield value
            if isinstance(value.get("@graph"), list):
                yield from values(value["@graph"])
    # Head and event content only. A script in the footer cannot supply facts.
    def scripts(node, excluded=False):
        excluded = excluded or node.tag in {"footer", "nav", "template", "noscript"} or bool(
            _classes(node) & {"happings-related-events", "happings-related-card", "happings-social-box"})
        if excluded:
            return
        if node.tag == "script" and node.attrs.get("type") == "application/ld+json":
            yield node
        for child in node.children:
            if isinstance(child, _Node):
                yield from scripts(child, excluded)
    for script in scripts(root):
        try:
            value = json.loads(_raw(script))
        except (ValueError, RecursionError):
            continue
        for event in values(value):
            if event.get("url") == url and _key(event.get("name")) == _key(title):
                yield event


def _detail_probe(html, final_url):
    root = _tree(html)
    if root is None:
        return None
    heroes, contents, sidebars = (_select(root, klass) for klass in
                                 ("happings-event-hero", "happings-event-content", "happings-event-sidebar"))
    if len(heroes) != 1 or len(contents) != 1 or len(sidebars) > 1:
        return None
    titles = [_text(node) for node in _walk(heroes[0], scoped=True) if node.tag == "h1"]
    if len(titles) != 1 or not titles[0]:
        return None
    addresses, hours, dated_hours, dates, recurrence = [], [], [], [], []
    for sidebar in sidebars:
        for item in _select(sidebar, "happings-event-info-item"):
            labels = [_text(n) for n in _walk(item, scoped=True) if n.tag == "strong"]
            paragraphs = [_text(n) for n in _walk(item, scoped=True) if n.tag == "p"]
            if not labels:
                continue
            label = _key(labels[0])
            if label == "orario":
                hours.extend(paragraphs)
            elif label == "dove si svolge" and paragraphs:
                addresses.append(paragraphs[-1])
            elif label == "data":
                dates.extend(paragraphs)
    for summary in _select(contents[0], "happings-event-auto-summary"):
        for line in _lines(summary):
            key = _key(line)
            if key.startswith("l indirizzo indicato e "):
                addresses.append(re.split(r"[èe]\s+", line, maxsplit=1)[-1].rstrip("."))
            elif key.startswith("l orario indicato e "):
                hours.append(line)
            elif key.startswith("il periodo indicato "):
                dates.append(line)
    for description in _select(contents[0], "happings-event-description-card"):
        if "happings-event-performances" in _classes(description):
            dates.extend(_lines(description))
        else:
            for line in _lines(description):
                if WEEKDAYS.search(line):
                    recurrence.append(line)
                if re.search(r"\b(?:orari?|ore|dalle?|alle?|apertur[ae]|inizi[oa]|conclusione|chiusur[ae])\b", line, re.I):
                    hours.append(line)
    for performance in _select(contents[0], "happings-event-performances"):
        lines = _lines(performance)
        dates.extend(lines)
        dated_hours.extend(lines)
    for event in _event_schemas(root, final_url, titles[0]):
        location = event.get("location")
        address = location.get("address") if isinstance(location, dict) else None
        if isinstance(address, dict):
            addresses.append(address.get("streetAddress"))
        for key in ("startDate", "endDate"):
            if event.get(key):
                dates.append(str(event[key]))
                clock = re.match(r"\d{4}-\d{2}-\d{2}T(\d{2}:\d{2})", str(event[key]))
                # Midnight is a common date-only schema placeholder; do not
                # diagnose a lost midnight opening from that encoding alone.
                if clock and clock[1] != "00:00":
                    dated_hours.append(clock[1])
    event_hours = "\n".join(hours)
    all_hours = event_hours + "\n" + "\n".join(dated_hours)
    return {"indirizzo": _address_presence(addresses),
            "orario_testo": _hours_presence(all_hours),
            "ricorrenza_testo": "precise" if recurrence else "absent_in_reviewed_scope",
            "date": "precise" if _dated_tokens("\n".join(dates)) else "unclassified" if dates else "absent_in_reviewed_scope",
            "clock_tokens": _clock_tokens(all_hours),
            "event_hours_present": _hours_presence(event_hours) != "absent_in_reviewed_scope",
            "date_tokens": _dated_tokens("\n".join(dates))}


def _retained_dates(event):
    values = [str(item.get("date") or "") for item in event.get("occurrences", []) if isinstance(item, dict)]
    for item in [event.get("edition_interval"), *event.get("date_intervals", [])]:
        if isinstance(item, dict):
            values.extend(str(item.get(key) or "") for key in ("start", "end"))
    if isinstance(event.get("schema_interval"), dict):
        values.extend(str(value) for value in event["schema_interval"].values())
    return _dated_tokens("\n".join(values))


def _detail_destination(field, document, outcome, *, before, after, applied):
    sid = outcome.get("market_id")
    if outcome.get("status") not in {"matched", "new_venue_admitted", "new_venue_candidate"} or not sid:
        return []
    if not applied:
        return ["available"]
    row = after.get(sid)
    if not row:
        return []
    source = document.get("source") or {}
    url, sha = source.get("final_url"), source.get("html_sha256")
    if field == "date":
        proof = row.get("calendario_fonte") or {}
        supported = proof.get("url") == url and proof.get("sha256") == sha
    else:
        supported = any(item.get("url") == url and item.get("sha256") == sha
                        and field in item.get("valori", {}) and item["valori"][field] == row.get(field)
                        for item in row.get("riscontri_campi", []) if isinstance(item, dict))
    if supported:
        return ["applied" if before.get(sid, {}).get(field) != row.get(field) else "supported"]
    detail = row.get("dettaglio_fonte") or {}
    return ["retained_as_detail"] if detail.get("url") == url and detail.get("sha256") == sha else []


def detail_page_coverage(html, document, outcome, *, before=None, after=None, applied=False):
    source = document.get("source") or {}
    page = _page(html, source.get("requested_url"), source.get("final_url"), "event_detail")
    probe = _detail_probe(html, source.get("final_url"))
    if probe is None:
        page["probe_status"] = "unassessed_layout"
        return _finish(page)
    page["source_units"] = 1
    before, after = before or {}, after or {}
    possible = set(outcome.get("possible_market_ids") or [])
    if outcome.get("market_id"):
        possible.add(outcome["market_id"])
    page["catalog_page_pairs_considered"] = len(possible & (set(before) | set(after)))
    page["catalog_page_pairs_linked"] = int(outcome.get("status") in {"matched", "new_venue_admitted"})
    page["catalog_outcome"] = outcome.get("status")
    page["catalog_hold_reason"] = outcome.get("reason")
    page["new_venue_candidates_not_catalog_records"] = int(outcome.get("status") == "new_venue_candidate")
    event = document.get("event") or {}
    page["parsed_hours_scope"] = event.get("hours_scope")
    page["parsed_calendar_scope"] = event.get("calendar_scope")
    dated_hours = any(item.get("start_time") or item.get("end_time")
                      for item in [*event.get("occurrences", []), *event.get("date_intervals", [])])
    reader = {"indirizzo": bool((event.get("location") or {}).get("street_address")),
              "orario_testo": bool(event.get("hours_text")) if probe["event_hours_present"] else dated_hours,
              "ricorrenza_testo": bool(event.get("recurrence_text")),
              "date": bool(_retained_dates(event))}
    hours = _clock_tokens(event.get("hours_text"))
    for item in [*event.get("occurrences", []), *event.get("date_intervals", []), *event.get("subevents", [])]:
        hours.update(_clock_tokens(str(item.get("start_time") or "") + " " + str(item.get("end_time") or "")))
    for item in event.get("hours_intervals", []):
        hours.update(_clock_tokens(str(item.get("start") or "") + " " + str(item.get("end") or "")))
    for field in FIELDS:
        parsed = "parsed" if reader[field] else "missing"
        if field == "orario_testo" and reader[field] and probe["clock_tokens"] - hours:
            parsed = "partial"
        if field == "date" and reader[field] and probe["date_tokens"] - _retained_dates(event):
            parsed = "partial"
        conflict_fields = {item.get("field") for item in document.get("conflicts", []) if isinstance(item, dict)}
        relevant = {"indirizzo": {"street_address", "location", "identity"},
                    "orario_testo": {"hours_text", "hours_intervals", "identity"},
                    "ricorrenza_testo": {"recurrence_text", "identity"},
                    "date": {"occurrences", "edition_interval", "date_intervals", "identity"}}[field]
        if parsed in {"missing", "partial"} and conflict_fields & relevant:
            parsed = "withheld_conflict"
        reasons = list(outcome.get("field_holds") or [])
        if outcome.get("reason"):
            reasons.append(outcome["reason"])
        held = bool(document.get("conflicts")) or outcome.get("reason") in {
            "source_detail_not_representable", "source_category_or_event_is_not_a_market"}
        # A parsed conflicting value is a deliberate source hold, never a read
        # or applied fact. Missing values remain independently observable gaps.
        destinations = _detail_destination(field, document, outcome, before=before, after=after, applied=applied)
        if outcome.get("status") == "matched" and not destinations:
            held = True
        _observe(page, 1, field, probe[field], parsed, destinations=destinations, held=held, reasons=reasons)
    return _finish(page)


def aggregate_coverage(pages):
    fields = _empty_fields()
    total = sum(page["source_units"] for page in pages)
    for page in pages:
        for field, item in page["fields"].items():
            for name in ("source_presence", "reader", "disposition"):
                fields[field][name].update(item[name])
            for name in ("catalog_values_applied", "catalog_values_supported", "catalog_values_available", "catalog_detail_only"):
                fields[field][name] += item[name]
    aggregate = _finish({"source_units": total, "fields": fields})
    return {"schema": 1, "scope": "already_acquired_recognized_market_blocks_only",
            "source_absence_is_not_inferred_from_catalog_or_parser": True,
            "unit": "physical_source_listing_row_or_detail_event",
            "catalog_unit": "source_page_and_catalog_record_pair",
            "pages_supplied": len(pages),
            "pages_unassessed": sum(page["probe_status"] == "unassessed_layout" for page in pages),
            "pages_partially_assessed": sum(page["probe_status"] == "partially_assessed" for page in pages),
            "source_units": total,
            "catalog_page_pairs_considered": sum(page["catalog_page_pairs_considered"] for page in pages),
            "catalog_page_pairs_linked": sum(page["catalog_page_pairs_linked"] for page in pages),
            "new_venue_candidates_not_catalog_records": sum(page.get("new_venue_candidates_not_catalog_records", 0) for page in pages),
            "fields": aggregate["fields"], "pages": pages,
            "field_values_or_source_html_copied": False, "market_openings_verified": 0,
            "limits": ["Absence applies only to the recognized source blocks examined, not every page of the publisher.",
                       "Unrecognized layouts remain unassessed; they never count as source absence.",
                       "Precise clock facts may be qualified or specific to a date; they do not imply universal opening hours.",
                       "Linked or applied fields remain publisher assertions, not independently confirmed openings."]}
