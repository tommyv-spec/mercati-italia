"""Read Cose di Casa market facts without network access or date forecasting.

Only the primary ``#post-content.mercatini-mostre-wrapper`` and its matching
Event object contribute facts. Edition bounds, selected dates, recurring rules
and suspensions remain different claims. Reading an article today does not make
its event current; generated JSON-LD dates do not override the visible calendar.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from html import unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit

MAX_BYTES = 2_600_000
MAX_NODES = 60_000
MAX_FIELD = 20_000
MAX_DATES = 600
PREFIX = "#post-content .mercatini-mostre-"
MONTHS = dict(zip(("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
                   "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"), range(1, 13)))
MONTH = "(?:" + "|".join(MONTHS) + ")"
WEEKDAYS = {name: i for i, name in enumerate(("lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica"))}
ORDINALS = {"prima": 1, "primo": 1, "seconda": 2, "secondo": 2,
            "terza": 3, "terzo": 3, "quarta": 4, "quarto": 4, "ultima": -1, "ultimo": -1}
CLOCK = r"(?:[01]?\d|2[0-3])(?:[:,.]\d{2})?|24(?::00|,00|\.00)?"
HOURS = re.compile(r"\bdalle?\s+(?:ore\s+)?(?P<start>" + CLOCK + r")\s+(?:alle|al|a)\s+(?:ore\s+)?(?P<end>" + CLOCK + r"|tramonto)\b", re.I)
VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"})
IGNORED = frozenset({"script", "style", "noscript", "nav", "footer", "aside", "form", "button", "svg", "template"})


def _clean(value):
    text = " ".join(unescape(str(value or "")).split())
    if len(text) > MAX_FIELD:
        raise ValueError("Cose di Casa field exceeds bounds")
    return text


def _key(value):
    value = unicodedata.normalize("NFKD", _clean(value).casefold())
    return " ".join(re.findall(r"[a-z0-9]+", "".join(c for c in value if not unicodedata.combining(c))))


def source_url(value):
    """Validate an observed URL; no canonical slug is manufactured."""
    if not isinstance(value, str) or len(value) > 700:
        return None
    try:
        parsed = urlsplit(value)
        if (parsed.scheme == "https" and parsed.netloc == "www.cosedicasa.com"
                and not parsed.query and not parsed.fragment
                and re.fullmatch(r"/mercatini/[a-z0-9]+(?:-[a-z0-9]+)*/?", parsed.path)):
            return value
    except ValueError:
        pass
    return None


@dataclass
class _Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)
    parent: object = None


class _Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("root")
        self.stack = [self.root]
        self.count = 0

    def handle_starttag(self, tag, attrs):
        self.count += 1
        if self.count > MAX_NODES or len(self.stack) > 150:
            raise ValueError("Cose di Casa document exceeds bounds")
        if tag in {"p", "li"} and self.stack[-1].tag == tag:
            self.stack.pop()
        node = _Node(tag, dict(attrs), parent=self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                del self.stack[index:]
                return

    def handle_data(self, value):
        self.stack[-1].children.append(value)


def _classes(node):
    return set(str(node.attrs.get("class") or "").split())


def _walk(node, *, scoped=False):
    if scoped and node.tag in IGNORED:
        return
    yield node
    for child in node.children:
        if isinstance(child, _Node):
            yield from _walk(child, scoped=scoped)


def _text(node):
    if node.tag in IGNORED:
        return ""
    return _clean(" ".join(c if isinstance(c, str) else _text(c) for c in node.children))


def _raw(node):
    return "".join(c if isinstance(c, str) else _raw(c) for c in node.children)


def _rows(scope, suffix):
    return [node for node in _walk(scope, scoped=True)
            if "mercatini-mostre-" + suffix in _classes(node)]


def _value(node):
    return re.sub(r"^[^:]{1,40}:\s*", "", _text(node), count=1).strip()


def _iso_day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        parsed = date.fromisoformat(value)
        return parsed.isoformat() if 2000 <= parsed.year <= 2100 else None
    except ValueError:
        return None


def _timestamp(value):
    if not isinstance(value, str):
        return None
    if _iso_day(value):
        return value
    try:
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})", value):
            datetime.fromisoformat(value.replace("Z", "+00:00"))
            return value
    except ValueError:
        pass
    return None


def _italian_day(value):
    match = re.fullmatch(r"(\d{1,2})\s+(" + MONTH + r")\s+(\d{4})", _clean(value), re.I)
    if not match:
        return None
    try:
        return date(int(match[3]), MONTHS[match[2].lower()], int(match[1])).isoformat()
    except ValueError:
        return None


def _clock(value):
    if value.casefold() == "tramonto":
        return None
    pieces = re.split(r"[:,.]", value)
    hour, minute = int(pieces[0]), int(pieces[1]) if len(pieces) > 1 else 0
    if hour > 24 or minute > 59 or hour == 24 and minute != 0:
        return None
    return f"{hour:02}:{minute:02}"


def _json_objects(value):
    if isinstance(value, list):
        for child in value:
            yield from _json_objects(child)
    elif isinstance(value, dict):
        yield value
        if "@graph" in value:
            yield from _json_objects(value["@graph"])


def _has_type(item, value):
    kind = item.get("@type")
    return kind == value or isinstance(kind, list) and value in kind


def _locality(value):
    match = re.fullmatch(r"(.+?)\s*\(([^()]+)\)", _clean(value))
    return (match[1].strip(), match[2].strip()) if match else (_clean(value) or None, None)


def _json_text(value):
    return _clean(value) or None if isinstance(value, str) else None


def _bound_ranges(value, *, evidence):
    """Keep yearless claims yearless, including recurring suspension bounds."""
    pattern = (r"\bda(?:ll?['’a]?|l)?\s*(\d{1,2})\s+(" + MONTH + r")"
               r"(?:\s+(\d{4}))?\s+(?:a|al|all?['’a]?)\s*(\d{1,2})\s+(" + MONTH + r")(?:\s+(\d{4}))?")
    result = []
    for match in re.finditer(pattern, value, re.I):
        sd, sm, sy, ed, em, ey = match.groups()
        sy, ey = int(sy) if sy else None, int(ey) if ey else None
        # A shared trailing year in the same range explicitly qualifies it.
        if not sy and ey:
            sy = ey
        start = {"day": int(sd), "month": MONTHS[sm.lower()], "year": sy}
        end = {"day": int(ed), "month": MONTHS[em.lower()], "year": ey}
        try:
            date(sy or 2000, start["month"], start["day"])
            date(ey or 2000, end["month"], end["day"])
        except ValueError:
            continue
        result.append({"start": start, "end": end, "evidence": [evidence]})
    return result


def _explicit_text_dates(value):
    """Parse only a complete single date or a same-month, explicit-year range."""
    day = _italian_day(value)
    if day:
        return [(day, day)]
    match = re.fullmatch(r"(\d{1,2})\s*[-–—]\s*(\d{1,2})\s+(" + MONTH + r")\s+(\d{4})", _clean(value), re.I)
    if match:
        try:
            start = date(int(match[4]), MONTHS[match[3].lower()], int(match[1]))
            end = date(int(match[4]), MONTHS[match[3].lower()], int(match[2]))
            return [(start.isoformat(), end.isoformat())] if start <= end else []
        except ValueError:
            pass
    return []


def _date_rows(node):
    """Keep the visual br-delimited groups; ten endpoints are not ten editions."""
    rows, current = [], []
    def flush():
        if any(isinstance(x, _Node) or _clean(x) for x in current):
            rows.append(current[:])
        current.clear()
    def visit(item):
        if isinstance(item, str):
            current.append(item)
        elif item.tag == "br":
            flush()
        elif item.tag == "time":
            current.append(item)
        elif item.tag not in IGNORED:
            if item.tag in {"p", "li"}:
                flush()
            for child in item.children:
                visit(child)
            if item.tag in {"p", "li"}:
                flush()
    for child in node.children:
        visit(child)
    flush()
    return rows


def parse_detail(html, *, requested_url, final_url=None):
    """Return field-scoped facts; callers add the observed acquisition time."""
    if not source_url(requested_url) or final_url is not None and not source_url(final_url):
        raise ValueError("Unreviewed Cose di Casa source URL")
    if not isinstance(html, (str, bytes)):
        raise ValueError("Cose di Casa input must be HTML bytes or text")
    blob = html.encode("utf-8") if isinstance(html, str) else html
    if not blob or len(blob) > MAX_BYTES:
        raise ValueError("Cose di Casa HTML exceeds byte bounds")
    try:
        text = blob.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("Cose di Casa input is not UTF-8") from error
    document = _Document()
    document.feed(text)
    nodes = list(_walk(document.root))
    conflicts, warnings, evidence = [], [], {}
    result = {"schema": 1, "status": "unsupported", "source": {
        "publisher": "cosedicasa.com", "source_id": None,
        "requested_url": requested_url, "final_url": final_url,
        "canonical_url": None, "html_sha256": hashlib.sha256(blob).hexdigest(),
        "bytes": len(blob), "published_at": None, "modified_at": None},
        "event": {"name": None, "location": {"city": None, "province": None,
            "region": None, "address": None}, "hours_text": None, "hours_intervals": [],
            "recurrence_text": None, "archive_marker": False, "edition_intervals": [],
            "occurrences": [], "date_intervals": [], "calendar_complete": False,
            "calendar_scope": "unknown", "scope_statements": [], "conditions": [],
            "calendar_rules": [], "suspensions": [], "source_rows": []},
        "conflicts": conflicts, "warnings": warnings, "field_evidence": evidence}
    source, event = result["source"], result["event"]

    def conflict(field_name, code, values):
        path = field_name if field_name.startswith("location.") else None
        if field_name == "location.address":
            field_name = "address"
        elif field_name in {"location.city", "location.province", "location.region"}:
            field_name = "identity"
        item = {"field": field_name, "code": code, "values": values}
        if path:
            item["path"] = path
        if item not in conflicts:
            conflicts.append(item)

    def record(field_name, value, selector):
        if value is not None and value != "":
            event["source_rows"].append({"field": field_name, "value": value, "evidence": [selector]})
            evidence.setdefault(field_name, []).append(selector)

    canonicals = list(dict.fromkeys(n.attrs.get("href") for n in nodes
        if n.tag == "link" and "canonical" in str(n.attrs.get("rel", "")).lower().split()))
    if len(canonicals) == 1 and source_url(canonicals[0]):
        source["canonical_url"] = canonicals[0]
        if final_url and final_url != canonicals[0]:
            conflict("identity", "canonical_differs_observed_final", [final_url, canonicals[0]])
        elif final_url is None and requested_url != canonicals[0]:
            warnings.append("canonical_change_without_transport_evidence")
    elif canonicals:
        conflict("identity", "unreviewed_or_multiple_canonical", canonicals)
    bound_url = source["canonical_url"] or final_url or requested_url
    source["source_id"] = urlsplit(bound_url).path.rstrip("/").rsplit("/", 1)[-1]
    scopes = [node for node in nodes if node.attrs.get("id") == "post-content"
              and "mercatini-mostre-wrapper" in _classes(node)]
    if len(scopes) != 1:
        warnings.append("primary_market_wrapper_missing_or_ambiguous")
        return result
    scope = scopes[0]
    parent = scope.parent
    titles = [n for n in _walk(parent, scoped=True) if n.tag == "h1"]
    if len(titles) != 1 or not _text(titles[0]):
        warnings.append("primary_market_title_missing_or_ambiguous")
        return result
    event["name"] = _text(titles[0])
    evidence["name"] = ["#content h1"]
    objects = []
    for node in nodes:
        if node.tag == "script" and node.attrs.get("type", "").lower() == "application/ld+json":
            try:
                objects.extend(_json_objects(json.loads(_raw(node))))
            except (ValueError, RecursionError):
                warnings.append("invalid_json_ld")
    events = [item for item in objects if _has_type(item, "Event") and item.get("url") == bound_url]
    unique_events = {json.dumps(item, sort_keys=True, ensure_ascii=False): item for item in events}
    schema = next(iter(unique_events.values()), {}) if len(unique_events) == 1 else {}
    if len(unique_events) > 1:
        conflict("identity", "multiple_self_events", [len(unique_events)])
    if not schema:
        warnings.append("matching_event_schema_absent")
    elif _key(schema.get("name")) != _key(event["name"]):
        conflict("identity", "schema_event_name_differs_primary", [event["name"], _clean(schema.get("name"))])
        schema = {}
    for key, prop, schema_key in (("modified_at", "article:modified_time", "dateModified"),
                                  ("published_at", "article:published_time", "datePublished")):
        claims = [n.attrs.get("content") for n in nodes if n.tag == "meta" and n.attrs.get("property") == prop]
        claims += [item.get(schema_key) for item in objects if (_has_type(item, "WebPage") or _has_type(item, "Article"))
                   and (item.get("url") == bound_url or str(item.get("@id") or "").split("#")[0] == bound_url)
                   and item.get(schema_key)]
        claims = list({json.dumps(value, sort_keys=True, ensure_ascii=False): value
                       for value in claims}.values())
        valid = [value for value in claims if _timestamp(value)]
        if len(valid) == 1 and len(valid) == len(claims):
            source[key] = valid[0]
        elif claims:
            conflict("source." + key, "invalid_or_conflicting_source_timestamp", claims)

    def single(suffix, field_name, *, label=True):
        values = list(dict.fromkeys((_value(n) if label else _text(n)) for n in _rows(scope, suffix)))
        values = [v for v in values if v]
        if len(values) > 1:
            conflict(field_name, "multiple_structured_values", values)
            return None
        if values:
            record(field_name, values[0], PREFIX + suffix)
            return values[0]
        return None

    visible_city, visible_province = _locality(single("content-title", "location.city", label=False))
    visible_address = single("address", "location.address")
    visible_region = single("region", "location.region")
    place = schema.get("location") if isinstance(schema.get("location"), dict) else {}
    address = place.get("address") if isinstance(place.get("address"), dict) else {}
    schema_city, schema_province = _locality(_json_text(address.get("addressLocality")))
    for field_name, visible, structured in (
            ("city", visible_city, schema_city), ("province", visible_province, schema_province),
            ("address", visible_address, _json_text(address.get("streetAddress"))),
            ("region", visible_region, _json_text(address.get("addressRegion")))):
        if visible and structured and _key(visible) != _key(structured):
            conflict("location." + field_name, "visible_schema_location_disagree", [visible, structured])
        else:
            event["location"][field_name] = visible or structured
            if structured:
                evidence.setdefault("location." + field_name, []).append("self Event.location.address")
    for suffix, name in (("performer", "organizer"), ("phone", "phone"),
                         ("contacts", "contacts"), ("website", "website"), ("expo", "exhibitors")):
        single(suffix, name)
    geo = place.get("geo")
    if isinstance(geo, dict):
        try:
            latitude, longitude = float(geo.get("latitude")), float(geo.get("longitude"))
            if -90 <= latitude <= 90 and -180 <= longitude <= 180:
                record("publisher_geo", {"latitude": str(geo["latitude"]),
                    "longitude": str(geo["longitude"]), "precision": "publisher_point_unverified"},
                    "self Event.location.geo")
        except (TypeError, ValueError):
            warnings.append("invalid_publisher_coordinates")

    descriptions = [_text(n) for n in _rows(scope, "times")]
    if len(descriptions) > 1:
        conflict("hours", "multiple_primary_description_blocks", [len(descriptions)])
    body = descriptions[0] if len(descriptions) == 1 else ""
    body_key = _key(body)
    event["archive_marker"] = bool(re.search(r"\b(?:evento passato|edizione conclusa|manifestazione conclusa)\b", body_key))
    sentences = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ü“\"'])", body)
    hour_claims = []
    for sentence in sentences:
        matches = list(HOURS.finditer(sentence))
        if not matches:
            continue
        key = _key(sentence)
        auxiliary = bool(re.search(r"\b(?:percorso|laboratorio|giochi dei nonni|concerto|musica live|spettacolo|spettacoli|dj set)\b", key))
        if auxiliary and not re.search(r"\bmercat(?:o|ino|ini)\b", key):
            warnings.append("auxiliary_activity_hours_not_market_hours")
            continue
        for match in matches:
            start, end = _clock(match["start"]), _clock(match["end"])
            if not start or start == "24:00" or end is None and match["end"].lower() != "tramonto":
                warnings.append("invalid_market_clock_interval")
                continue
            claim = {"start": start, "end": end}
            if claim not in hour_claims:
                hour_claims.append(claim)
        if re.search(r"\b(?:fino|solo|tranne|eccetto|esclus|sabato|domenica|festiv|ferial)\w*\b", key):
            event["scope_statements"].append({"kind": "hours_qualification", "text": sentence, "evidence": [PREFIX + "times"]})
    if len(hour_claims) == 1 and not any(c["field"] == "hours" for c in conflicts):
        event["hours_intervals"] = hour_claims
        claim = hour_claims[0]
        event["hours_text"] = claim["start"] + "–" + (claim["end"] or "tramonto")
        qualifications = [item["text"] for item in event["scope_statements"]
                          if item["kind"] == "hours_qualification"]
        if qualifications:
            event["hours_text"] += "; " + " ".join(dict.fromkeys(qualifications))
        evidence["hours_text"] = [PREFIX + "times: main market schedule"]
    elif len(hour_claims) > 1:
        conflict("hours", "multiple_market_hour_claims_require_scope", hour_claims)
    for sentence in sentences:
        if re.search(r"\b(?:maltempo|annullat|sospes|straordinari|esclus|variabil)\w*\b", _key(sentence)):
            if "maltempo" in _key(sentence):
                event["conditions"].append({"kind": "weather_condition", "text": sentence,
                    "evidence": [PREFIX + "times"]})
            elif "straordinari" in _key(sentence):
                event["scope_statements"].append({"kind": "extra_edition_claim", "text": sentence,
                    "evidence": [PREFIX + "times"]})
                if not re.search(r"\b(?:20\d{2}|2100)\b", sentence):
                    warnings.append("extra_edition_year_unknown")
            elif re.search(r"\b(?:annullat|cancellat)\w*\b", _key(sentence)):
                conflict("calendar", "unscoped_cancellation_language", [sentence])

    # Recurring statements are retained, never projected by this parser.
    ordinal = re.search(r"\b(" + "|".join(ORDINALS) + r")\s+(" + "|".join(WEEKDAYS) + r")\s+del mese\b", body_key)
    if ordinal:
        rule = {"kind": "monthly_ordinal", "ordinal": ORDINALS[ordinal[1]],
                "weekday": WEEKDAYS[ordinal[2]], "relative_day_offsets": [0],
                "included_months": [], "excluded_months": [], "evidence": [PREFIX + "times"]}
        if re.search(r"\bsabato (?:antecedente|precedente)\b", body_key) and rule["weekday"] == 6:
            rule["relative_day_offsets"] = [-1, 0]
        month_range = re.search(r"\bda(?:l mese di)?\s+(" + MONTH + r")\s+a(?:l mese di)?\s+(" + MONTH + r")\b", body_key)
        if month_range:
            start, end = MONTHS[month_range[1]], MONTHS[month_range[2]]
            rule["included_months"] = list(range(start, end + 1)) if start <= end else list(range(start, 13)) + list(range(1, end + 1))
        excluded = re.search(r"\besclus[ioae]\s+((?:" + MONTH + r")(?:\s*(?:e|,)\s*(?:" + MONTH + r"))*)", body_key)
        if excluded:
            rule["excluded_months"] = sorted({MONTHS[m] for m in re.findall(MONTH, excluded[1])})
        event["calendar_rules"].append(rule)
    if "date variabili" in body_key:
        weekdays = sorted({number for name, number in WEEKDAYS.items() if re.search(r"\b" + name + r"\b", body_key)})
        event["calendar_rules"].append({"kind": "selected_dates_only", "weekdays": weekdays,
            "evidence": [PREFIX + "times"]})
    if re.search(r"\bogni (?:giorno|sera)\b", body_key):
        event["calendar_rules"].append({"kind": "daily_within_edition", "evidence": [PREFIX + "times"]})

    claims = []
    date_blocks = _rows(scope, "date-big")
    if len(date_blocks) != 1:
        warnings.append("calendar_header_missing_or_ambiguous")
    else:
        for index, group in enumerate(_date_rows(date_blocks[0])):
            times = [x for x in group if isinstance(x, _Node)]
            visible = _clean(" ".join(_text(x) if isinstance(x, _Node) else x for x in group))
            selector = PREFIX + "date-big:row[" + str(index + 1) + "]"
            if not times:
                if visible:
                    event["recurrence_text"] = visible
                    record("recurrence_text", visible, selector)
                continue
            parsed = [_iso_day(n.attrs.get("datetime")) for n in times]
            if any(not day or _italian_day(_text(node)) != day for day, node in zip(parsed, times)):
                conflict("calendar", "visible_date_datetime_disagree_or_invalid", [visible, parsed])
                continue
            connective = _clean(" ".join(x for x in group if isinstance(x, str)))
            if len(times) == 1:
                claims.append((parsed[0], parsed[0], selector))
            elif len(times) == 2 and connective in {"-", "–", "—", "al", "a"} and parsed[0] <= parsed[1]:
                claims.append((parsed[0], parsed[1], selector))
            else:
                conflict("calendar", "ambiguous_visible_date_group", [visible])
    for node in _rows(scope, "suspension"):
        text = _text(node)
        label = _key(text.split(":", 1)[0])
        value = _value(node)
        if label in {"prossima data", "prossime date"}:
            parsed = _explicit_text_dates(value)
            record("next_dates", value, PREFIX + "suspension:label=Prossime date")
            if not parsed:
                conflict("calendar", "unparsed_explicit_next_dates", [value])
            claims.extend((start, end, PREFIX + "suspension:label=Prossime date") for start, end in parsed)
        elif label == "sospensioni":
            ranges = _bound_ranges(value, evidence=PREFIX + "suspension:label=Sospensioni")
            event["suspensions"].extend(ranges)
            record("suspensions", value, PREFIX + "suspension:label=Sospensioni")
            if value and not ranges:
                conflict("calendar", "unparsed_suspension_scope", [value])
        else:
            warnings.append("unrecognized_suspension_row_label")
    if len(claims) > MAX_DATES:
        raise ValueError("Cose di Casa date claims exceed bounds")
    pairs = {}
    for start, end, selector in claims:
        pairs.setdefault((start, end), []).append(selector)
    for (start, end), selectors in sorted(pairs.items()):
        event["edition_intervals"].append({"start": start, "end": end})
        if start == end:
            event["occurrences"].append({"date": start, "start_time": None, "end_time": None,
                "status": "source_listed", "evidence": selectors})
        else:
            event["date_intervals"].append({"start": start, "end": end,
                "start_time": None, "end_time": None, "hours_scope": "edition_bounds",
                "continuous_opening_confirmed": False, "status": "source_listed", "evidence": selectors})
    if pairs:
        event["calendar_scope"] = "edition_bounds" if event["date_intervals"] else "explicit_visible_list"
        evidence["calendar"] = list(dict.fromkeys(selector for selectors in pairs.values() for selector in selectors))
    elif event["calendar_rules"]:
        event["calendar_scope"] = "recurring_statement_only"
    schema_start, schema_end = _iso_day(schema.get("startDate")), _iso_day(schema.get("endDate"))
    if schema_start and schema_end:
        record("schema_edition", {"start": schema_start, "end": schema_end}, "self Event.startDate/endDate")
        if pairs and (schema_start, schema_end) not in pairs:
            conflict("calendar", "schema_dates_not_visible_calendar", [schema_start, schema_end])
        elif not pairs:
            warnings.append("schema_dates_without_visible_date_evidence")
        if ordinal:
            parsed = date.fromisoformat(schema_start)
            rule = event["calendar_rules"][0]
            nth = (parsed.day - 1) // 7 + 1
            if parsed.weekday() != rule["weekday"] or rule["ordinal"] > 0 and nth != rule["ordinal"]:
                conflict("calendar", "schema_date_outside_visible_recurrence", [schema_start, rule["weekday"], rule["ordinal"]])
        schema_status = {"https://schema.org/EventScheduled": "source_listed",
                         "https://schema.org/EventCancelled": "cancelled",
                         "https://schema.org/EventPostponed": "postponed",
                         "https://schema.org/EventRescheduled": "rescheduled"}.get(schema.get("eventStatus"))
        if schema_status and schema_status != "source_listed":
            record("schema_event_status", schema_status, "self Event.eventStatus")
            for occurrence in event["occurrences"]:
                if schema_start == schema_end == occurrence["date"]:
                    occurrence["status"] = schema_status
                    occurrence["evidence"].append("self Event.eventStatus")
            for interval in event["date_intervals"]:
                if interval["start"] == schema_start and interval["end"] == schema_end:
                    interval["status"] = schema_status
                    interval["evidence"].append("self Event.eventStatus")
    elif schema.get("startDate") or schema.get("endDate"):
        conflict("calendar", "invalid_schema_edition_dates", [schema.get("startDate"), schema.get("endDate")])
    if ordinal and event["calendar_rules"][0]["relative_day_offsets"] == [-1, 0] and re.search(r"\bsecondi sabato e domenica\b", _key(event["recurrence_text"])):
        conflict("calendar", "ordinal_saturday_differs_preceding_saturday", [event["recurrence_text"], "Saturday preceding the second Sunday"])
    body_bounds = _bound_ranges(body, evidence=PREFIX + "times")
    for bound in body_bounds:
        event["scope_statements"].append({"kind": "edition_bounds_claim", **bound})
        if pairs and not any((date.fromisoformat(start).month, date.fromisoformat(start).day,
                             date.fromisoformat(end).month, date.fromisoformat(end).day) ==
                (bound["start"]["month"], bound["start"]["day"], bound["end"]["month"], bound["end"]["day"])
                for start, end in pairs):
            conflict("calendar", "description_visible_edition_bounds_disagree",
                     [bound, [{"start": start, "end": end} for start, end in pairs]])
    for start, end in pairs:
        for suspension in event["suspensions"]:
            low, high = suspension["start"], suspension["end"]
            for day in (date.fromisoformat(start), date.fromisoformat(end)):
                if low["year"] and day.year != low["year"]:
                    continue
                lo, hi, point = (low["month"], low["day"]), (high["month"], high["day"]), (day.month, day.day)
                overlap = lo <= point <= hi if lo <= hi else point >= lo or point <= hi
                if overlap:
                    conflict("calendar", "listed_date_during_suspension", [day.isoformat(), suspension])
    if event["calendar_rules"] and event["recurrence_text"] is None:
        record("calendar_rules", event["calendar_rules"], PREFIX + "times")
    calendar_incomplete = {"extra_edition_year_unknown", "calendar_header_missing_or_ambiguous",
                           "invalid_json_ld", "unrecognized_suspension_row_label"}
    event["calendar_complete"] = (bool(pairs) and not calendar_incomplete.intersection(warnings)
        and not any(c["field"] in {"calendar", "identity"} for c in conflicts))
    result["status"] = "held" if conflicts else "parsed"
    return result


parse = parse_detail
