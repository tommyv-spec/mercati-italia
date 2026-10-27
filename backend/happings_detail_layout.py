"""Read the current Happings event detail, without network or forecasting.

The visible event and its matching Event JSON-LD are compared. The publisher's
date list remains a list of source assertions, not independently confirmed
openings. Missing closing times and years are never synthesized. Related
events, navigation and publisher contacts do not belong to the event.

Descriptions stay in the in-memory parser result for context and qualification;
audit reports should publish field presence/hash evidence instead of body copy.
"""
from __future__ import annotations

import hashlib
import json
import math
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from html import unescape as html_unescape
from html.parser import HTMLParser
from urllib.parse import urlsplit
from happings_detail_urls import detail_url as valid_detail_url

SCHEMA = 1
MAX_BYTES = 2_600_000
MAX_NODES = 60_000
MAX_OCCURRENCES = 1500
MAX_FIELD_CHARS = 20_000
VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input",
                  "link", "meta", "param", "source", "track", "wbr"})
IGNORED = frozenset({"script", "style", "noscript", "template", "nav", "footer",
                     "form", "button", "svg"})
EXCLUDED = frozenset({"happings-related-events", "happings-related-card",
                       "happings-social-box", "happings-event-popularity",
                       "happings-claim-modal"})
BLOCKS = frozenset({"div", "p", "li", "ul", "ol", "section", "article", "h1",
                    "h2", "h3", "h4", "h5", "tr", "td", "th", "br"})
MONTHS = dict(zip(("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
                   "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"),
                  range(1, 13)))
DATE_PATTERN = r"(?P<day>\d{1,2})\s+(?P<month>" + "|".join(MONTHS) + r")\s+(?P<year>\d{4})"
DATE_RE = re.compile(DATE_PATTERN, re.I)
DATE_REFERENCE_RE = re.compile(r"(?<!\d)(?P<day>\d{1,2})\s+(?P<month>" + "|".join(MONTHS)
                               + r")(?:\s+(?P<year>\d{4}))?\b", re.I)
EDITION_RANGE_RE = re.compile(r"(?<!\d)(?P<start>\d{1,2})\s*[-–—]\s*(?P<end>\d{1,2})\s+(?P<month>"
                              + "|".join(MONTHS) + r")(?:\s+(?P<year>\d{4}))?\b", re.I)
CLOCK = r"(?:[01]?\d|2[0-3])[:.][0-5]\d|24[:.]00"
HOURS_RE = re.compile(r"(?<![\d.:])(?P<start>" + CLOCK + r")\s*(?:[-–—]|alle|a)\s*(?P<end>" + CLOCK + r")(?!\d|[.:]\d)", re.I)
CLOCK_RE = re.compile(r"(?<![\d.:])(" + CLOCK + r")(?!\d|[.:]\d)")
WEEKDAYS = re.compile(r"\b(?:luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)\b", re.I)
WEEKDAY_NUMBERS = {name: i for i, name in enumerate(("lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica"))}
QUALIFICATION = re.compile(r"\b(?:fino\s+al|dal\s+\d|al\s+\d|tranne|eccetto|esclus[oaie]|"
                           r"chius[oaie]|chiude|termina|sospes[oaie]|annullat[oaie]|"
                           r"straordinari[oaie]|estiv[oaie]|invernal[ei]|stagional[ei])\b", re.I)


def _clean(value):
    return " ".join(str(value or "").split())


def _key(value):
    # The page's JSON-LD keeps HTML codes ("&#8211;", "&amp;") that its visible
    # text shows decoded; compare the decoded text, or every such title "differs".
    value = unicodedata.normalize("NFKD", _clean(html_unescape(str(value or ""))).casefold())
    return " ".join(re.findall(r"[a-z0-9]+", "".join(
        c for c in value if not unicodedata.combining(c))))


def detail_url(url):
    """Return only a valid exact observed event URL."""
    return url if valid_detail_url(url) else None


@dataclass
class _Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)


class _Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node("root")
        self.stack = [self.root]
        self.count = 0

    def handle_starttag(self, tag, attrs):
        self.count += 1
        if self.count > MAX_NODES or len(self.stack) > 150:
            raise ValueError("Happings detail exceeds HTML bounds")
        if tag in {"p", "li"} and self.stack[-1].tag == tag:
            self.stack.pop()
        node = _Node(tag, dict(attrs))
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        for i in range(len(self.stack) - 1, 0, -1):
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        self.stack[-1].children.append(data)


def _classes(node):
    return set(str(node.attrs.get("class") or "").split())


def _walk(node, *, scoped=False):
    if scoped and (node.tag in IGNORED or _classes(node) & EXCLUDED):
        return
    yield node
    for child in node.children:
        if isinstance(child, _Node):
            yield from _walk(child, scoped=scoped)


def _select(node, klass):
    return [n for n in _walk(node, scoped=True) if klass in _classes(n)]


def _raw(node):
    return "".join(c if isinstance(c, str) else _raw(c) for c in node.children)


def _lines(node):
    lines, current = [], []

    def flush():
        text = _clean("".join(current))
        if text:
            if len(text) > MAX_FIELD_CHARS:
                raise ValueError("Happings detail field exceeds bounds")
            lines.append(text)
        current.clear()

    def visit(n):
        if n.tag in IGNORED or _classes(n) & EXCLUDED:
            return
        if n.tag in BLOCKS:
            flush()
        for child in n.children:
            if isinstance(child, str):
                current.append(child)
            else:
                visit(child)
        if n.tag in BLOCKS:
            flush()
    visit(node)
    flush()
    return lines


def _text(node):
    return " ".join(_lines(node))


def _date(value):
    match = DATE_RE.fullmatch(_clean(value))
    if not match:
        return None
    try:
        return date(int(match["year"]), MONTHS[match["month"].casefold()],
                    int(match["day"])).isoformat()
    except ValueError:
        return None


def _clock(value):
    if not isinstance(value, str) or not re.fullmatch(CLOCK, value):
        return None
    h, m = value.replace(".", ":").split(":")
    return f"{int(h):02}:{int(m):02}"


def _intervals(value):
    return [{"start": _clock(m["start"]), "end": _clock(m["end"])}
            for m in HOURS_RE.finditer(str(value or ""))]


def _iso(value):
    if not isinstance(value, str):
        return None
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        try:
            return {"date": date.fromisoformat(value).isoformat(), "time": None,
                    "offset": None}
        except ValueError:
            return None
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2})?", value):
        return None
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return {"date": stamp.date().isoformat(), "time": stamp.strftime("%H:%M"),
                "offset": stamp.strftime("%z") or None}
    except ValueError:
        return None


def _safe_text(value):
    if not isinstance(value, str) or not _clean(value):
        return None
    if len(value) > MAX_FIELD_CHARS:
        raise ValueError("Happings structured field exceeds bounds")
    return _clean(value)


def _external_url(value):
    try:
        p = urlsplit(value)
        if (p.scheme in {"https", "http"} and p.hostname and not p.username
                and not p.password and len(value) <= 2000):
            return value
    except (ValueError, TypeError):
        pass
    return None


def _same_address(structured, visible, city):
    left, right = _key(structured), _key(visible)
    town = _key(city)
    return bool(left and right and (left == right or town and right == left + " " + town))


def _address_core(value):
    # Postal/locality suffixes can use reviewed bilingual municipality labels;
    # this comparison concerns the street, not municipality reconciliation.
    return _key(re.split(r",\s*\d{5}\b", value, maxsplit=1)[0])


def _description_intervals(lines):
    result, warnings = [], []
    for line in lines:
        years = set(re.findall(r"\b(?:19|20)\d{2}\b", line))
        for match in EDITION_RANGE_RE.finditer(line):
            year = match["year"] or (next(iter(years)) if len(years) == 1 else None)
            if not year:
                warnings.append("unyearred_edition_range")
                continue
            try:
                start = date(int(year), MONTHS[match["month"].casefold()], int(match["start"]))
                end = date(int(year), MONTHS[match["month"].casefold()], int(match["end"]))
            except ValueError:
                warnings.append("invalid_edition_range")
                continue
            if end < start:
                warnings.append("invalid_edition_range")
                continue
            item = {"start": start.isoformat(), "end": end.isoformat(),
                    "start_time": None, "end_time": None,
                    "hours_scope": "interval_boundaries", "continuous_opening_confirmed": False,
                    "status": "source_listed",
                    "evidence": [".happings-event-description-card explicit edition range"]}
            if item not in result:
                result.append(item)
    return result, warnings


def _schema_events(value):
    """Only top-level/graph Event nodes; never related ItemList descendants."""
    items = value if isinstance(value, list) else [value]
    for item in items:
        if not isinstance(item, dict):
            continue
        types = item.get("@type")
        if types == "Event" or isinstance(types, list) and "Event" in types:
            yield item
        graph = item.get("@graph")
        if isinstance(graph, list):
            for child in graph:
                if isinstance(child, dict) and child.get("@type") == "Event":
                    yield child


def parse_detail(html, *, requested_url, final_url=None):
    """Return a source-bound event and explicit conflicts; never project dates."""
    final_url = final_url or requested_url
    if not detail_url(requested_url) or not detail_url(final_url):
        raise ValueError("Unreviewed Happings detail URL")
    if isinstance(html, str):
        raw = html.encode("utf-8")
    elif isinstance(html, bytes):
        raw = html
    else:
        raise ValueError("Happings detail needs HTML bytes or text")
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("Happings detail response exceeds bounds")
    document = _Document()
    document.feed(raw.decode("utf-8-sig", "replace"))
    document.close()
    root = document.root
    conflicts, warnings, evidence, schema_pairs = [], [], {}, []

    def conflict(field_name, code, values):
        item = {"field": field_name, "code": code, "values": values}
        if item not in conflicts:
            conflicts.append(item)

    def proven(field_name, selector):
        evidence.setdefault(field_name, [])
        if selector not in evidence[field_name]:
            evidence[field_name].append(selector)

    source = {"requested_url": requested_url, "final_url": final_url,
              "canonical_url": None, "html_sha256": hashlib.sha256(raw).hexdigest(),
              "bytes": len(raw), "published_at": None, "modified_at": None}
    event = {"name": None, "source_id": None, "category": None,
             "location": {"name": None, "street_address": None, "city": None,
                          "province": None, "region": None, "country": None},
             "hours_text": None, "hours_intervals": [], "occurrences": [],
             "edition_interval": None, "recurrence_text": None, "description": None,
             "organizer": None, "contacts": [], "geo": None, "event_status": None,
             "calendar_notes": [], "visible_location": None,
             "related_detail_urls": [], "hours_qualifications": [],
             "sidebar_hours_text": None, "all_day": None,
             "calendar_complete": False, "calendar_scope": None,
             "date_intervals": [], "conditions": [], "subevents": [],
             "hours_scope": "not_indicated", "source_links": [],
             "admission_text": None}
    result = {"schema": SCHEMA, "status": "parsed", "source": source, "event": event,
              "conflicts": conflicts, "warnings": warnings, "field_evidence": evidence}
    canonical = [_clean(n.attrs.get("href")) for n in _walk(root)
                 if n.tag == "link" and "canonical" in str(n.attrs.get("rel") or "").split()]
    canonical = list(dict.fromkeys(canonical))
    if len(canonical) == 1:
        source["canonical_url"] = canonical[0]
        if canonical[0] != final_url:
            conflict("identity", "canonical_mismatch", canonical)
    elif len(canonical) > 1:
        conflict("identity", "multiple_canonicals", canonical)
    for origin, target in (("article:published_time", "published_at"),
                           ("article:modified_time", "modified_at")):
        stamps = list(dict.fromkeys(n.attrs.get("content") for n in _walk(root)
                                    if n.tag == "meta" and n.attrs.get("property") == origin
                                    and _iso(n.attrs.get("content"))))
        if len(stamps) == 1:
            source[target] = stamps[0]
        elif len(stamps) > 1:
            conflict(target, "multiple_editorial_timestamps", stamps)

    heroes = _select(root, "happings-event-hero")
    contents = _select(root, "happings-event-content")
    sidebars = _select(root, "happings-event-sidebar")
    if len(heroes) != 1 or len(contents) != 1 or len(sidebars) > 1:
        result["status"] = "layout_changed"
        warnings.append("expected_one_event_hero_and_content")
        return result
    hero, content = heroes[0], contents[0]
    titles = [_text(n) for n in _walk(hero, scoped=True) if n.tag == "h1"]
    if len(titles) != 1 or not titles[0]:
        result["status"] = "layout_changed"
        warnings.append("expected_one_event_title")
        return result
    event["name"] = titles[0]
    proven("name", ".happings-event-hero h1")
    categories = list(dict.fromkeys(_text(n) for n in _select(hero, "happings-event-category")))
    if len(categories) == 1:
        event["category"] = categories[0]
        proven("category", ".happings-event-hero .happings-event-category")
    elif len(categories) > 1:
        conflict("category", "multiple_categories", categories)

    schemas, schema_errors = [], 0
    editorial_stamps = {key: [source[key]] if source[key] else [] for key in ("published_at", "modified_at")}
    for n in _walk(root):
        if n.tag != "script" or n.attrs.get("type") != "application/ld+json":
            continue
        try:
            value = json.loads(_raw(n))
        except (ValueError, RecursionError):
            schema_errors += 1
            continue
        graph = value.get("@graph", []) if isinstance(value, dict) else []
        metadata_nodes = [value] + graph if isinstance(graph, list) else [value]
        for metadata in metadata_nodes:
            if (not isinstance(metadata, dict) or metadata.get("@type") != "WebPage"
                    or metadata.get("url") != final_url):
                continue
            for source_key, json_key in (("published_at", "datePublished"), ("modified_at", "dateModified")):
                stamp = metadata.get(json_key)
                if _iso(stamp):
                    editorial_stamps[source_key].append(stamp)
                    proven(source_key, "WebPage[url=final_url]." + json_key)
        candidates = list(_schema_events(value))
        if n.attrs.get("id") == "happings-event-schema":
            schemas.extend(candidates)
        else:
            schemas.extend(x for x in candidates if x.get("url") == final_url)
    if schema_errors:
        warnings.append("invalid_json_ld")
    for key, stamps in editorial_stamps.items():
        distinct = list(dict.fromkeys(stamps))
        if len(distinct) == 1:
            source[key] = distinct[0]
        elif len(distinct) > 1:
            source[key] = None
            conflict(key, "conflicting_editorial_timestamps", distinct)
    schema = None
    if len(schemas) == 1:
        candidate = schemas[0]
        if candidate.get("url") != final_url:
            conflict("identity", "schema_url_mismatch", [candidate.get("url"), final_url])
        elif _key(candidate.get("name")) != _key(event["name"]):
            conflict("identity", "schema_title_mismatch", [candidate.get("name"), event["name"]])
        else:
            schema = candidate
            proven("identity", "script#happings-event-schema Event.url/name")
    elif len(schemas) > 1:
        conflict("identity", "multiple_event_schemas", [x.get("url") for x in schemas])
    else:
        warnings.append("missing_matching_event_schema")

    descriptions = [n for n in _select(content, "happings-event-description-card")
                    if "happings-event-performances" not in _classes(n)]
    lines = [line for n in descriptions for line in _lines(n)]
    if lines:
        event["description"] = "\n".join(lines)
        recurrence = []
        for line in lines:
            if WEEKDAYS.search(line):
                # Keep the whole qualifying sentence, including exceptions.
                if "Le aperture settimanali riportate dalla fonte sono:" in line:
                    value = line.split("Le aperture settimanali riportate dalla fonte sono:", 1)[1]
                    value = re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-Ü])", value, maxsplit=1)[0]
                else:
                    value = line
                recurrence.append(_clean(value))
        if recurrence:
            event["recurrence_text"] = "\n".join(recurrence)
            proven("recurrence_text", ".happings-event-content .happings-event-description-card")
            for value in recurrence:
                pairs = {(x["start"], x["end"]) for x in _intervals(value)}
                days = {_key(x[0]) for x in WEEKDAYS.finditer(value)}
                if len(pairs) > 1 or len(days) > 1:
                    event["hours_qualifications"].append(value)
        event["date_intervals"], range_warnings = _description_intervals(lines)
        warnings.extend(range_warnings)
        admission = []
        for line in lines:
            for match in re.finditer(r"\b(?:L[’']ingresso|Ingresso|Accesso|Il biglietto|Biglietti)\s+[^.!?\n]{0,200}", line, re.I):
                sentence = match[0].strip()
                if re.search(r"\b(?:gratuit[oaie]|liber[oaie]|pagamento|euro|EUR|prezzo|costo)\b|€", sentence, re.I):
                    admission.append(sentence)
        if admission:
            event["admission_text"] = ". ".join(dict.fromkeys(admission))
            proven("admission_text", ".happings-event-description-card admission statement")

    sidebar_fields = {}
    sidebar = sidebars[0] if sidebars else None
    if sidebar is not None:
        for n in _select(sidebar, "happings-event-info-item"):
            strong = [x for x in _walk(n, scoped=True) if x.tag == "strong"]
            if not strong:
                continue
            label = _key(_text(strong[0]))
            paragraphs = [_text(x) for x in _walk(n, scoped=True) if x.tag == "p"]
            value = "\n".join(x for x in paragraphs if x)
            if label in sidebar_fields and sidebar_fields[label][0] != value:
                conflict(label, "duplicate_sidebar_field", [sidebar_fields[label][0], value])
            else:
                sidebar_fields[label] = (value, n)
        source_ids = list(dict.fromkeys(str(n.attrs.get("data-event-id")) for n in _walk(sidebar)
                                        if "happings-social-box" in _classes(n)
                                        and str(n.attrs.get("data-event-id") or "").isdigit()))
        if len(source_ids) == 1:
            event["source_id"] = source_ids[0]
            proven("source_id", ".happings-event-sidebar [data-event-id]")
        elif len(source_ids) > 1:
            conflict("identity", "multiple_event_ids", source_ids)

    if schema:
        location = schema.get("location")
        if isinstance(location, dict):
            address = location.get("address")
            event["location"]["name"] = _safe_text(location.get("name"))
            if isinstance(address, dict):
                for target, origin in (("street_address", "streetAddress"), ("city", "addressLocality"),
                                       ("region", "addressRegion"), ("country", "addressCountry")):
                    event["location"][target] = _safe_text(address.get(origin))
                    if event["location"][target]:
                        proven(target, "Event.location.address." + origin)
                event["location"]["postal_code"] = _safe_text(address.get("postalCode"))
            elif address is not None:
                warnings.append("unstructured_schema_address")
            geo = location.get("geo")
            if isinstance(geo, dict):
                try:
                    lat, lon = float(geo.get("latitude")), float(geo.get("longitude"))
                    if not math.isfinite(lat + lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
                        raise ValueError
                    event["geo"] = {"latitude": lat, "longitude": lon,
                                    "precision": "publisher_point_unverified"}
                    proven("geo", "Event.location.geo")
                except (ValueError, TypeError, OverflowError):
                    warnings.append("invalid_schema_coordinates")
        elif location is not None:
            conflict("location", "multiple_or_unstructured_locations", [location])
        event["event_status"] = _safe_text(schema.get("eventStatus"))
        org = schema.get("organizer")
        if isinstance(org, dict):
            event["organizer"] = {"name": _safe_text(org.get("name")),
                                  "url": _external_url(org.get("url"))}
            proven("organizer", "Event.organizer")

    if "dove si svolge" in sidebar_fields:
        value, node = sidebar_fields["dove si svolge"]
        place_lines = [v for v in value.splitlines() if v]
        event["visible_location"] = value
        if place_lines:
            visible_address = place_lines[-1]
            street, city = (event["location"].get(k) for k in ("street_address", "city"))
            if street and not _same_address(street, visible_address, city):
                conflict("street_address", "visible_schema_address_mismatch", [street, visible_address])
            proven("visible_location", ".happings-event-sidebar Dove si svolge")
    for line in lines:
        for sentence in re.split(r"[.!?](?:\s|$)", line):
            match = re.search(r"\bLa sede(?:\s+del\s+(?:mercato|mercatino|evento))?\s+[èe]\s+(.+)", sentence, re.I)
            if not match:
                continue
            address = re.search(r"(?:^|\bin\s+)((?:Via|Viale|Piazza|Piazzale|Corso|Largo|Vicolo|Lungomare)\b.+)$", match[1], re.I)
            structured = event["location"].get("street_address")
            if address and structured and _address_core(structured) != _address_core(address[1]):
                conflict("street_address", "description_schema_address_mismatch", [structured, address[1]])

    if "orario" in sidebar_fields:
        event["hours_text"] = sidebar_fields["orario"][0] or None
        event["sidebar_hours_text"] = event["hours_text"]
        event["hours_intervals"] = _intervals(event["hours_text"])
        proven("hours_text", ".happings-event-sidebar Orario")

    summary_hours = []
    for summary in _select(content, "happings-event-auto-summary"):
        for line in _lines(summary):
            period = re.fullmatch(r"Il periodo indicato va dal (.+?) al (.+?)\.?", line, re.I)
            if period:
                start, end = _date(period[1]), _date(period[2].rstrip("."))
                if start and end and start <= end:
                    interval = {"start": start, "end": end}
                    if event["edition_interval"] and event["edition_interval"] != interval:
                        conflict("edition_interval", "multiple_edition_intervals", [event["edition_interval"], interval])
                    event["edition_interval"] = interval
                    proven("edition_interval", ".happings-event-auto-summary periodo")
                else:
                    warnings.append("unparsed_edition_interval")
            hours = re.fullmatch(r"L[’']orario indicato [èe] (.+?)\.?", line, re.I)
            if hours:
                summary_hours.append(hours[1].rstrip("."))
            address = re.fullmatch(r"L[’']indirizzo indicato [èe] (.+?)\.?", line, re.I)
            if address and event["location"].get("street_address"):
                visible = address[1].rstrip(".")
                if not _same_address(event["location"]["street_address"], visible, event["location"].get("city")):
                    conflict("street_address", "summary_schema_address_mismatch", [event["location"]["street_address"], visible])
    if summary_hours:
        for value in summary_hours:
            if event["hours_text"] and _intervals(value) != event["hours_intervals"]:
                conflict("hours_text", "summary_sidebar_hours_mismatch", [event["hours_text"], value])
        if not event["hours_text"] and len(set(summary_hours)) == 1:
            event["hours_text"] = summary_hours[0]
            event["hours_intervals"] = _intervals(summary_hours[0])
            proven("hours_text", ".happings-event-auto-summary orario")

    if re.search(r"\b(?:tutt[oa]\s+(?:il\s+)?giorno|(?:intera\s+giornata|giornata\s+intera))\b",
                 str(event["hours_text"] or ""), re.I):
        event["all_day"] = True

    occurrences = []
    performances = _select(content, "happings-event-performances")
    for performance in performances:
        for n in _walk(performance, scoped=True):
            if n.tag != "li":
                continue
            line = _text(n)
            if len(occurrences) >= MAX_OCCURRENCES:
                raise ValueError("Happings date list exceeds bounds")
            matches = list(DATE_RE.finditer(line))
            if len(matches) != 1:
                event["calendar_notes"].append(line)
                warnings.append("unparsed_performance_date")
                continue
            day = _date(matches[0][0])
            before, after = line[:matches[0].start()].strip(), line[matches[0].end():].strip(" ·–-")
            if not day or before and not WEEKDAYS.fullmatch(before):
                event["calendar_notes"].append(line)
                warnings.append("unparsed_performance_date")
                continue
            if before and WEEKDAY_NUMBERS.get(_key(before)) != date.fromisoformat(day).weekday():
                conflict("occurrences", "weekday_date_mismatch", [line])
            times = list(CLOCK_RE.finditer(after))
            spans = _intervals(after)
            if len(spans) > 1 or len(times) > 2 or len(times) == 2 and not spans:
                event["calendar_notes"].append(line)
                warnings.append("unparsed_performance_hours")
                continue
            start = spans[0]["start"] if spans else _clock(times[0][1]) if times else None
            end = spans[0]["end"] if spans else None
            remainder = HOURS_RE.sub("", after) if spans else CLOCK_RE.sub("", after)
            note = _clean(remainder.strip(" ·–-;:,")) or None
            cancelled = bool(re.search(r"\b(?:annullat[oa]|cancellat[oa]|sospes[oa])\b", note or "", re.I))
            occurrence = {"date": day, "start_time": start, "end_time": end,
                          "status": "cancelled" if cancelled else "source_listed",
                          "note": note, "evidence": [".happings-event-performances li"]}
            if occurrence not in occurrences:
                occurrences.append(occurrence)
    if occurrences:
        proven("occurrences", ".happings-event-performances li")

    if schema:
        start, end = _iso(schema.get("startDate")), _iso(schema.get("endDate"))
        if schema.get("startDate") and start is None:
            warnings.append("invalid_schema_start_date")
        if schema.get("endDate") and end is None:
            warnings.append("invalid_schema_end_date")
        if start and (event["all_day"] or start["time"] == "00:00"
                      and not any(x["start_time"] == "00:00" for x in occurrences)
                      and not any(x["start"] == "00:00" for x in event["hours_intervals"])):
            start = {**start, "time": None}
            if end:
                end = {**end, "time": None}
            warnings.append("all_day_or_midnight_schema_clock_withheld")
        if start:
            schema_date = start["date"]
            matching = [x for x in occurrences if x["date"] == schema_date]
            status = ("cancelled" if str(event["event_status"]).endswith("EventCancelled")
                      else "postponed" if str(event["event_status"]).endswith("EventPostponed")
                      else "rescheduled" if str(event["event_status"]).endswith("EventRescheduled")
                      else "source_listed")
            if end and end["date"] < schema_date:
                conflict("occurrences", "schema_end_precedes_start", [schema.get("startDate"), schema.get("endDate")])
            elif end and end["date"] != schema_date:
                # Keep the interval boundaries. They are not universal daily
                # clock hours and never imply overnight continuous opening.
                event["schema_interval"] = {"start": schema.get("startDate"), "end": schema.get("endDate")}
                same_interval = [x for x in event["date_intervals"] if x["start"] == schema_date and x["end"] == end["date"]]
                if len(same_interval) == 1:
                    item = same_interval[0]
                    item["start_time"], item["end_time"] = start["time"], end["time"]
                    item["status"] = status
                    item["evidence"].append("Event.startDate/endDate interval")
                else:
                    event["date_intervals"].append({"start": schema_date, "end": end["date"],
                                                   "start_time": start["time"], "end_time": end["time"],
                                                   "hours_scope": "interval_boundaries", "continuous_opening_confirmed": False,
                                                   "status": status,
                                                   "evidence": ["Event.startDate/endDate interval"]})
            elif matching:
                same_time = [x for x in matching if x["start_time"] == start["time"] or x["start_time"] is None]
                if len(same_time) != 1:
                    conflict("occurrences", "schema_performance_start_mismatch", [schema.get("startDate"), matching])
                else:
                    item = same_time[0]
                    if end and item["end_time"] and item["end_time"] != end["time"]:
                        conflict("occurrences", "schema_performance_end_mismatch", [schema.get("endDate"), item])
                    if status != "source_listed" and item["status"] not in {status, "source_listed"}:
                        conflict("occurrences", "schema_performance_status_mismatch", [status, item["status"]])
                    item["start_time"] = item["start_time"] or start["time"]
                    item["end_time"] = item["end_time"] or (end["time"] if end else None)
                    item["status"] = status if status != "source_listed" else item["status"]
                    item["evidence"].append("Event.startDate/endDate")
            elif performances and occurrences:
                conflict("occurrences", "schema_date_absent_from_performances", [schema_date])
            else:
                occurrences.append({"date": schema_date, "start_time": start["time"],
                                    "end_time": end["time"] if end and end["date"] == schema_date else None,
                                    "status": status, "note": None,
                                    "evidence": ["Event.startDate/endDate"]})
                proven("occurrences", "Event.startDate/endDate")
            if start["time"] and end and end["date"] == schema_date and end["time"]:
                # Compared once the description's per-day hours are merged (below);
                # until then the sidebar hours are the reference, as always.
                schema_pairs.append(({"start": start["time"], "end": end["time"]},
                                     list(event["hours_intervals"])))

    if "data" in sidebar_fields:
        visible_date = _date(sidebar_fields["data"][0])
        if visible_date and schema and _iso(schema.get("startDate")):
            if visible_date != _iso(schema.get("startDate"))["date"]:
                conflict("occurrences", "sidebar_schema_date_mismatch", [visible_date, schema.get("startDate")])
        elif not visible_date:
            text = sidebar_fields["data"][0]
            matches = list(DATE_RE.finditer(text))
            valid_range = (len(matches) == 2 and text[:matches[0].start()].strip().casefold() in {"", "dal"}
                           and text[matches[0].end():matches[1].start()].strip().casefold() in {"-", "–", "—", "al"}
                           and not text[matches[1].end():].strip(" ."))
            if valid_range:
                dates = [_date(m[0]) for m in matches]
                start_stamp, end_stamp = (_iso(schema.get(k)) if schema else None for k in ("startDate", "endDate"))
                if None in dates or dates[0] > dates[1]:
                    warnings.append("unparsed_sidebar_date")
                elif start_stamp and end_stamp and dates != [start_stamp["date"], end_stamp["date"]]:
                    conflict("occurrences", "sidebar_schema_interval_mismatch", [dates, schema.get("startDate"), schema.get("endDate")])
            else:
                warnings.append("unparsed_sidebar_date")
    # An explicitly described Saturday/Sunday edition may state only its
    # beginning and end. Apply those times only at those exact boundaries.
    for line in lines:
        if not re.search(r"\b(?:ciascuna|ogni)\s+edizione\b", line, re.I):
            continue
        begin = re.search(r"\b(?:inizio|apertura)\s+alle\s+(" + CLOCK + r")\s+del\s+(" + WEEKDAYS.pattern[2:-2] + r")", line, re.I)
        finish = re.search(r"\b(?:conclusione|chiusura)\s+alle\s+(" + CLOCK + r")\s+della?\s+(" + WEEKDAYS.pattern[2:-2] + r")", line, re.I)
        if not begin or not finish:
            continue
        for interval in event["date_intervals"]:
            if (date.fromisoformat(interval["start"]).weekday() == WEEKDAY_NUMBERS.get(_key(begin[2]))
                    and date.fromisoformat(interval["end"]).weekday() == WEEKDAY_NUMBERS.get(_key(finish[2]))):
                beginning, ending = _clock(begin[1]), _clock(finish[1])
                if (interval["start_time"] not in (None, beginning) or interval["end_time"] not in (None, ending)):
                    conflict("occurrences", "edition_boundary_hours_mismatch", [interval, line])
                else:
                    interval["start_time"], interval["end_time"] = beginning, ending
                    interval["evidence"].append(".happings-event-description-card edition boundary hours")
    for interval in event["date_intervals"]:
        begin, finish = date.fromisoformat(interval["start"]), date.fromisoformat(interval["end"])
        if (finish - begin).days > 31:
            warnings.append("long_schema_interval_not_enumerated")
            continue
        for offset in range((finish - begin).days + 1):
            day = (begin + timedelta(days=offset)).isoformat()
            existing = [x for x in occurrences if x["date"] == day]
            if len(existing) > 1:
                conflict("occurrences", "edition_interval_has_multiple_sessions", [day, existing])
                continue
            if existing:
                item = existing[0]
            else:
                item = {"date": day, "start_time": None, "end_time": None,
                        "status": "source_listed", "note": None, "evidence": []}
                occurrences.append(item)
            start_clock = interval["start_time"] if day == interval["start"] else None
            end_clock = interval["end_time"] if day == interval["end"] else None
            if (start_clock and item["start_time"] and item["start_time"] != start_clock
                    or end_clock and item["end_time"] and item["end_time"] != end_clock):
                conflict("occurrences", "interval_performance_hours_mismatch", [interval, item])
            else:
                item["start_time"] = item["start_time"] or start_clock
                item["end_time"] = item["end_time"] or end_clock
            item["interval_start"], item["interval_end"] = interval["start"], interval["end"]
            item["evidence"] = list(dict.fromkeys(item["evidence"] + interval["evidence"]))
            if interval.get("status") != "source_listed":
                if item["status"] not in {"source_listed", interval["status"]}:
                    conflict("occurrences", "interval_performance_status_mismatch", [interval, item])
                else:
                    item["status"] = interval["status"]
        proven("date_intervals", "; ".join(interval["evidence"]))
    interval = event["edition_interval"]
    if interval:
        outside = [x["date"] for x in occurrences if not interval["start"] <= x["date"] <= interval["end"]]
        if outside:
            conflict("occurrences", "occurrence_outside_edition", outside)

    # Qualifiers belong to the hours value, not just to a discarded description.
    # Match an unyearred day/month only to a unique explicitly yearred date in
    # this same page; this is a source join, not calendar projection.
    for line in lines:
        if re.search(r"\b(?:annullat[oaie]|cancellat[oaie]|sospes[oaie])\b", line, re.I):
            event["calendar_notes"].append(line)
            if re.search(r"\b(?:in\s+caso\s+di|se\s+(?:piove|maltempo))\b", line, re.I):
                event["conditions"].append(line)
                proven("conditions", ".happings-event-description-card conditional cancellation")
            else:
                warnings.append("unresolved_calendar_cancellation")
        if QUALIFICATION.search(line) and CLOCK_RE.search(line):
            sentences = re.split(r"(?<=[!?])\s+|(?<=\.)\s+(?=[A-ZÀ-Ü])", line)
            for sentence in sentences:
                if QUALIFICATION.search(sentence) and CLOCK_RE.search(sentence):
                    event["hours_qualifications"].append(sentence)
            refs = list(DATE_REFERENCE_RE.finditer(line))
            for position, ref in enumerate(refs):
                finish = refs[position + 1].start() if position + 1 < len(refs) else len(line)
                clause = re.split(r"[;!?]|\.(?:\s|$)", line[ref.end():finish], maxsplit=1)[0]
                end_match = re.search(r"\b(?:termina|chiude)\s+(?:alle\s+|ore\s+)(" + CLOCK + r")(?!\d|[.:]\d)", clause, re.I)
                pair = _intervals(clause)
                if not end_match and not pair:
                    continue
                day, month = int(ref["day"]), MONTHS[ref["month"].casefold()]
                matching = [x for x in occurrences
                            if int(x["date"][5:7]) == month and int(x["date"][8:10]) == day
                            and (not ref["year"] or int(x["date"][:4]) == int(ref["year"]))]
                if len(matching) != 1:
                    warnings.append("date_specific_hours_without_unique_explicit_date")
                    continue
                item = matching[0]
                new_start = pair[0]["start"] if len(pair) == 1 else None
                new_end = _clock(end_match[1]) if end_match else pair[0]["end"] if len(pair) == 1 else None
                if not new_end or len(pair) > 1:
                    warnings.append("unparsed_date_specific_hours")
                    continue
                if item["end_time"] and item["end_time"] != new_end:
                    conflict("occurrences", "prose_performance_end_mismatch", [item["date"], item["end_time"], new_end])
                elif new_start and item["start_time"] and item["start_time"] != new_start:
                    conflict("occurrences", "prose_performance_start_mismatch", [item["date"], item["start_time"], new_start])
                else:
                    item["end_time"] = new_end
                    item["start_time"] = item["start_time"] or new_start
                    item["evidence"].append(".happings-event-description-card date-specific hours")
                    item["note"] = _clean(ref[0] + clause)
                    proven("occurrences", ".happings-event-description-card date-specific hours")
    if event["hours_qualifications"]:
        event["hours_qualifications"] = list(dict.fromkeys(event["hours_qualifications"]))
        # A sidebar "15:00 - 13:00" beside "martedì 15:00–19:00; giovedì 08:30–13:00"
        # is the first listed start and the last listed end: a summary, not hours.
        per_day = [i for line in event["hours_qualifications"] if WEEKDAYS.search(line)
                   for i in _intervals(line)]
        sidebar = _intervals(event["hours_text"])
        if (len(per_day) > 1 and len(sidebar) == 1
                and sidebar[0] == {"start": per_day[0]["start"], "end": per_day[-1]["end"]}):
            warnings.append("sidebar_hours_summarize_weekday_hours")
            event["hours_text"] = None
            schema_pairs = [(pair, per_day) for pair, _ in schema_pairs]
        event["hours_text"] = "\n".join(([event["hours_text"]] if event["hours_text"] else [])
                                         + event["hours_qualifications"])
        # Keep these intervals explicitly qualified by their text. Callers must
        # never choose the first pair as one universal schedule.
        event["hours_intervals"] = _intervals(event["hours_text"])
        proven("hours_text", ".happings-event-description-card hour qualifications")
    for pair, reference in schema_pairs:
        if reference and pair not in reference:
            conflict("hours_text", "schema_sidebar_hours_mismatch", [pair, reference])
    # Some pages put a workshop into the same generic "performances" list.
    # Remove that start from the market schedule only when the body explicitly
    # names the ancillary activity, exactly one date is possible, and the time
    # differs from the main schema event. Preserve its facts separately.
    primary_start = _iso(schema.get("startDate")) if schema else None
    for line in lines:
        if not re.search(r"\b(?:laboratorio|concerto|spettacolo|workshop)\b", line, re.I):
            continue
        pairs = _intervals(line)
        if len(pairs) != 1:
            continue
        candidate_rows = [x for x in occurrences if x["start_time"] == pairs[0]["start"]
                          and not (primary_start and x["date"] == primary_start["date"]
                                   and x["start_time"] == primary_start["time"])]
        explicit_days = [_date(m[0]) for m in DATE_RE.finditer(line)]
        if explicit_days:
            candidate_rows = [x for x in candidate_rows if x["date"] in explicit_days]
        if len(candidate_rows) == 1 and (explicit_days or len({x["date"] for x in occurrences}) == 1):
            item = candidate_rows[0]
            event["subevents"].append({"date": item["date"], "start_time": pairs[0]["start"],
                                      "end_time": pairs[0]["end"], "kind": "ancillary_activity",
                                      "text": line, "evidence": [".happings-event-description-card ancillary activity",
                                                                    ".happings-event-performances li"]})
            occurrences.remove(item)
            proven("subevents", ".happings-event-description-card ancillary activity")
        elif candidate_rows:
            warnings.append("ambiguous_ancillary_performance")
    # Duplicate dates with different times remain separate explicit sessions.
    event["occurrences"] = sorted(occurrences, key=lambda x: (x["date"], x["start_time"] or "", x["end_time"] or ""))

    if sidebar is not None:
        for label, (value, node) in sidebar_fields.items():
            if label in {"organizzatore", "organizer", "organizzato da"}:
                anchors = [n for n in _walk(node, scoped=True) if n.tag == "a"]
                name = value or (_text(anchors[0]) if anchors else None)
                link = _external_url(anchors[0].attrs.get("href")) if anchors else None
                visible_org = {"name": name, "url": link}
                if event["organizer"] and _key(event["organizer"].get("name")) != _key(name):
                    conflict("organizer", "visible_schema_organizer_mismatch", [event["organizer"], visible_org])
                elif name:
                    event["organizer"] = visible_org
                    proven("organizer", ".happings-event-sidebar Organizzatore")
            if label not in {"contatti", "telefono", "email", "e mail", "sito web", "sito ufficiale", "organizzatore", "organizer", "organizzato da"}:
                continue
            for n in _walk(node, scoped=True):
                if n.tag != "a":
                    continue
                href = str(n.attrs.get("href") or "")
                if href.startswith("mailto:") and re.fullmatch(r"[^\s?@]+@[^\s?@]+\.[^\s?@]+", href[7:]):
                    contact = {"kind": "email", "value": href[7:]}
                elif href.startswith("tel:") and re.fullmatch(r"[+\d() .-]{5,40}", href[4:]):
                    contact = {"kind": "telephone", "value": href[4:]}
                elif label in {"sito web", "sito ufficiale"} and _external_url(href):
                    contact = {"kind": "website", "value": href}
                else:
                    continue
                if contact not in event["contacts"]:
                    event["contacts"].append(contact)
                    proven("contacts", ".happings-event-sidebar " + label)

    for card in descriptions:
        for paragraph in (n for n in _walk(card, scoped=True) if n.tag == "p"):
            text = _text(paragraph)
            if re.match(r"^(?:Fonte|Fonti)\s+(?:ufficiale|ufficiali)\s*:", text, re.I):
                for anchor in (n for n in _walk(paragraph, scoped=True) if n.tag == "a"):
                    url = _external_url(anchor.attrs.get("href"))
                    if url and url not in event["source_links"]:
                        event["source_links"].append(url)
                        proven("source_links", ".happings-event-description-card declared source links")
            if not re.match(r"^(?:Per\s+(?:informazioni|info)|Contatti\b|Informazioni\s+e\s+contatti\b)", text, re.I):
                continue
            contacts = []
            for match in re.finditer(r"\b(?:telefono|tel\.?)\s*:?\s*(\+?\d[\d ()/-]{3,35}\d)", text, re.I):
                contacts.append({"kind": "telephone", "value": _clean(match[1])})
            for match in re.finditer(r"\b(?:email|e-mail)\s*:?\s*([A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})\b", text, re.I):
                contacts.append({"kind": "email", "value": match[1]})
            for match in re.finditer(r"https?://[^\s<>]+", text):
                url = _external_url(match[0].rstrip(".,;:)"))
                if url:
                    contacts.append({"kind": "website", "value": url})
            for contact in contacts:
                if contact not in event["contacts"]:
                    event["contacts"].append(contact)
                    proven("contacts", ".happings-event-description-card explicit contact paragraph")
            if re.search(r"\S*\*\S*@\S*\*\S*", text):
                warnings.append("source_contact_email_obscured")

    # Links are discovery candidates only, with no identity or field authority.
    for n in _walk(content):
        if n.tag == "a" and "happings-related-card" in _classes(n):
            url = detail_url(n.attrs.get("href"))
            if url and url != final_url and url not in event["related_detail_urls"]:
                event["related_detail_urls"].append(url)
    result["warnings"] = list(dict.fromkeys(warnings))
    event["hours_scope"] = ("interval_boundaries" if event["date_intervals"]
                             else "event_hours" if event["hours_text"] else "not_indicated")
    if event["date_intervals"]:
        # The sidebar may compress a Saturday-start/Sunday-end into "9–19".
        # Persist a scoped statement so downstream generic hours consumers do
        # not turn two boundary times into daily hours or continuous opening.
        if any(x["start_time"] or x["end_time"] for x in event["date_intervals"]):
            if not re.search(r"non\s+attesta\s+l[’']apertura\s+notturna", event["hours_text"] or "", re.I):
                labels = []
                for interval in event["date_intervals"]:
                    if not interval["start_time"] and not interval["end_time"]:
                        continue
                    start_label = date.fromisoformat(interval["start"]).strftime("%d/%m/%Y")
                    end_label = date.fromisoformat(interval["end"]).strftime("%d/%m/%Y")
                    labels.append("Inizio edizione: " + start_label
                                  + (" ore " + interval["start_time"] if interval["start_time"] else "")
                                  + "; fine edizione: " + end_label
                                  + (" ore " + interval["end_time"] if interval["end_time"] else ""))
                event["hours_text"] = ". ".join(labels) + ". Questi orari indicano i confini dell’edizione; non attestano gli orari giornalieri o l’apertura continuativa."
                if event["hours_qualifications"]:
                    event["hours_text"] += " " + " ".join(event["hours_qualifications"])
                proven("hours_text", "explicit edition boundary dates/times; daily hours not asserted")
        event["hours_intervals"] = []
    calendar_holds = {"unparsed_performance_date", "unparsed_performance_hours",
                      "invalid_schema_start_date", "invalid_schema_end_date",
                      "long_schema_interval_not_enumerated", "unparsed_edition_interval",
                      "unyearred_edition_range", "invalid_edition_range",
                      "date_specific_hours_without_unique_explicit_date",
                      "unparsed_date_specific_hours", "unresolved_calendar_cancellation",
                      "ambiguous_ancillary_performance"}
    event["calendar_complete"] = bool(event["occurrences"]) and not (
        calendar_holds.intersection(warnings)
        or any(x["field"] in {"occurrences", "edition_interval", "identity", "hours_text"} for x in conflicts))
    event["calendar_scope"] = "explicit_visible_list" if performances else "schema_occurrence_only" if occurrences else None
    if conflicts:
        result["status"] = "conflict"
    return result


# The public alias keeps adapter call sites short without a second implementation.
parse = parse_detail
