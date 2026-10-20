"""Read one observed Citynews event card, without discovery or forecasting.

Only the primary article header's Dove/Quando cards supply address, hours
and edition dates. A matching head Event corroborates identity and locality;
its URL may be an organizer link and never replaces the observed page URL.
Programme times, related cards and publisher contacts do not supply facts.
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

from citynews_urls import source_identity
from source_hours import preserve_hours_text

MAX_BYTES = 2_500_000
MAX_NODES = 60_000
MAX_FIELD = 4000
VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"})
IGNORED = frozenset({"script", "style", "noscript", "nav", "footer", "aside", "form", "button", "svg", "template"})
MONTHS = dict(zip(("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
                  "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"), range(1, 13)))
CLOCK = r"(?:[01]?\d|2[0-3])(?:[:.,]\d{2})?|24(?:[:.,]00)?"
HOURS_PAIR = re.compile(r"(?:dalle?\s+(?:ore\s+)?)?(" + CLOCK + r")\s*(?:-|–|alle|al|a)\s*(?:ore\s+)?(" + CLOCK + r")", re.I)
HEADER = "article.l-entry > header.l-entry__header"
WHERE = HEADER + " .l-grid__item[Dove]"
WHEN = HEADER + " .l-grid__item[Quando]"


def clean(value):
    value = " ".join(unescape(str(value or "")).split())
    if len(value) > MAX_FIELD:
        raise ValueError("Citynews field exceeds its bound")
    return value


def key(value):
    value = unicodedata.normalize("NFKD", clean(value)).casefold()
    return " ".join(re.findall(r"[a-z0-9]+", "".join(c for c in value if not unicodedata.combining(c))))


@dataclass
class Node:
    tag: str
    attrs: dict = field(default_factory=dict)
    children: list = field(default_factory=list)
    parent: object = None


class Document(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root, self.count = Node("root"), 0
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        self.count += 1
        if self.count > MAX_NODES or len(self.stack) > 150:
            raise ValueError("Citynews document exceeds its structural bound")
        if tag in {"p", "li"} and self.stack[-1].tag == tag:
            self.stack.pop()
        node = Node(tag, dict(attrs), parent=self.stack[-1])
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

    def handle_data(self, value):
        self.stack[-1].children.append(value)


def classes(node):
    return set(str(node.attrs.get("class") or "").split())


def walk(node, *, scoped=False):
    if scoped and node.tag in IGNORED:
        return
    yield node
    for child in node.children:
        if isinstance(child, Node):
            yield from walk(child, scoped=scoped)


def text(node):
    if node.tag in IGNORED:
        return ""
    return clean(" ".join(c if isinstance(c, str) else text(c) for c in node.children))


def body_text(node):
    """Scan bounded document prose without turning it into a saved field."""
    if node.tag in IGNORED:
        return ""
    return " ".join(c if isinstance(c, str) else body_text(c) for c in node.children)


def raw(node):
    return "".join(c if isinstance(c, str) else raw(c) for c in node.children)


def nodes(scope, *, tag=None, cls=None):
    return [n for n in walk(scope, scoped=True)
            if (tag is None or n.tag == tag) and (cls is None or cls in classes(n))]


def _objects(value, depth=0):
    if depth > 5:
        raise ValueError("Citynews schema nesting exceeds its bound")
    if isinstance(value, list):
        if len(value) > 100:
            raise ValueError("Citynews schema list exceeds its bound")
        for item in value:
            yield from _objects(item, depth + 1)
    elif isinstance(value, dict):
        yield value
        if "@graph" in value:
            yield from _objects(value["@graph"], depth + 1)


def _has_type(item, expected):
    value = item.get("@type")
    return value == expected or isinstance(value, list) and expected in value


def _day(value):
    if not isinstance(value, str):
        return None
    try:
        if re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
            d, m, y = map(int, value.split("/"))
            result = date(y, m, d)
        elif re.fullmatch(r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:\d{2}))?", value):
            result = date.fromisoformat(value[:10])
            if "T" in value:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
        else:
            return None
        return result.isoformat() if 2000 <= result.year <= 2100 else None
    except ValueError:
        return None


def _clock(value):
    parts = re.split(r"[:.,]", value)
    hour, minute = int(parts[0]), int(parts[1]) if len(parts) == 2 else 0
    return f"{hour:02}:{minute:02}" if 0 <= hour <= 24 and 0 <= minute < 60 and (hour < 24 or minute == 0) else None


def _hours(value):
    """Parse only complete simple labels; retain all qualified text verbatim."""
    pair = HOURS_PAIR.fullmatch(value)
    single = re.fullmatch(r"(?:dalle?\s+(?:ore\s+)?|ore\s+)?(" + CLOCK + r")", value, re.I)
    if pair:
        start, end = _clock(pair[1]), _clock(pair[2])
        if start and end and start < end:
            return [{"start": start, "end": end, "evidence": [WHEN + " .u-label-011"]}]
    if single:
        start = _clock(single[1])
        if start:
            return [{"start": start, "end": None, "evidence": [WHEN + " .u-label-011"]}]
    return []


def _empty(source):
    return {"schema": 1, "status": "unsupported", "source": source,
        "event": {"name": None, "location": {"name": None, "address": None, "city": None,
                    "province": None, "region": None, "country": None},
            "hours_text": None, "hours_intervals": [], "hours_qualifications": [],
            "recurrence_text": None, "archive_marker": False,
            "edition_intervals": [], "occurrences": [], "date_intervals": [],
            "calendar_complete": False, "calendar_scope": "edition_bounds",
            "calendar_rules": [], "suspensions": [], "scope_statements": [],
            "conditions": [], "source_rows": [], "forecast_rule": None},
        "conflicts": [], "warnings": [], "field_evidence": {}}


def parse_detail(html, *, requested_url, final_url=None):
    """Return the common factual envelope; never attach an acquisition date."""
    identity = source_identity(requested_url)
    final_url = final_url or requested_url
    final_identity = source_identity(final_url)
    if (identity is None or final_identity is None or identity[0] != final_identity[0]
            or not isinstance(html, bytes) or not 100 <= len(html) <= MAX_BYTES):
        raise ValueError("Citynews detail requires bounded bytes and an observed reviewed origin")
    result = _empty({"publisher": identity[0], "source_id": identity[1],
        "requested_url": requested_url, "final_url": final_url, "canonical_url": None,
        "html_sha256": hashlib.sha256(html).hexdigest(), "bytes": len(html),
        "published_at": None, "modified_at": None, "hash_basis": "http_response_bytes",
        "redirect_observed": requested_url != final_url})
    source, event, conflicts = result["source"], result["event"], result["conflicts"]
    proof, warnings = result["field_evidence"], result["warnings"]
    doc = Document()
    doc.feed(html.decode("utf-8-sig", errors="replace")); doc.close()
    heads = [n for n in walk(doc.root) if n.tag == "head"]
    articles = nodes(doc.root, tag="article", cls="l-entry")
    if len(heads) != 1 or len(articles) != 1:
        warnings.append("unique_primary_event_article_not_found")
        return result
    header = nodes(articles[0], tag="header", cls="l-entry__header")
    bodies = nodes(articles[0], tag="section", cls="l-entry__body")
    if len(header) != 1 or len(bodies) != 1:
        warnings.append("primary_event_header_or_body_not_found")
        return result
    titles = nodes(header[0], tag="h1", cls="l-entry__title")
    if len(titles) != 1 or not text(titles[0]):
        warnings.append("unique_event_title_not_found")
        return result
    event["name"] = text(titles[0]); proof["name"] = [HEADER + " h1.l-entry__title"]
    canonical = [n.attrs.get("href") for n in walk(heads[0])
                 if n.tag == "link" and n.attrs.get("rel") == "canonical"]
    if len(canonical) != 1 or canonical[0] != final_url:
        conflicts.append({"field": "identity", "code": "canonical_does_not_bind_observed_page"})
    elif canonical:
        source["canonical_url"] = canonical[0]
    if requested_url != final_url:
        conflicts.append({"field": "identity", "code": "redirect_changes_exact_event_identity"})
    cards = {}
    for card in nodes(header[0], cls="l-grid__item"):
        labels = [n for n in card.children if isinstance(n, Node) and n.tag == "span" and "u-label-03" in classes(n)]
        if len(labels) == 1:
            label = key(text(labels[0]))
            cards.setdefault(label, []).append(card)
    if any(len(cards.get(label, [])) != 1 for label in ("dove", "quando")):
        warnings.append("event_editorial_variant_without_unique_dove_quando")
        return result
    events = []
    schema_unreadable = False
    for script in [n for n in walk(heads[0]) if n.tag == "script" and n.attrs.get("type", "").lower() == "application/ld+json"]:
        if len(raw(script).encode("utf-8")) > 200_000:
            warnings.append("oversized_json_ld")
            schema_unreadable = True
            continue
        try:
            objects = list(_objects(json.loads(raw(script))))
        except (ValueError, RecursionError):
            warnings.append("invalid_json_ld")
            schema_unreadable = True
            continue
        events.extend(n for n in objects if _has_type(n, "Event"))
    if len(events) != 1:
        conflicts.append({"field": "identity", "code": "unique_primary_schema_event_not_found"})
        result["status"] = "held"
        return result
    if schema_unreadable:
        conflicts.append({"field": "identity", "code": "schema_event_uniqueness_not_established"})
    schema = events[0]
    if not isinstance(schema.get("name"), str) or key(schema["name"]) != key(event["name"]):
        conflicts.append({"field": "identity", "code": "visible_and_schema_title_disagree"})
    schema_url = schema.get("url")
    if isinstance(schema_url, str) and schema_url != final_url:
        if urlsplit(schema_url).hostname == urlsplit(final_url).hostname:
            conflicts.append({"field": "identity", "code": "schema_url_names_another_event"})
        else:
            warnings.append("schema_event_url_is_external_not_page_identity")

    where, when = cards["dove"][0], cards["quando"][0]
    places = [n for n in nodes(where, tag="a") if str(n.attrs.get("href") or "").startswith("/eventi/location/")]
    addresses = [n for n in nodes(where, tag="a") if n.attrs.get("href") == "#map"]
    if len(places) == 1:
        event["location"]["name"] = text(places[0]) or None
        proof["location.name"] = [WHERE + " a[href^=/eventi/location/]"]
    elif len(places) > 1:
        conflicts.append({"field": "address", "code": "multiple_visible_venues"})
    if len(addresses) == 1 and key(text(addresses[0])) not in {"", "indirizzo non disponibile"}:
        event["location"]["address"] = text(addresses[0])
        proof["location.address"] = [WHERE + " a[href=#map]"]
    elif len(addresses) > 1:
        conflicts.append({"field": "address", "code": "multiple_visible_addresses"})
    location = schema.get("location")
    if not isinstance(location, dict) or not _has_type(location, "Place"):
        conflicts.append({"field": "identity", "code": "schema_place_missing"})
        location = {}
    if event["location"]["name"] and location.get("name") and key(location["name"]) != key(event["location"]["name"]):
        conflicts.append({"field": "address", "code": "visible_and_schema_venue_disagree"})
    observed = location.get("address")
    event["location"]["raw_address"] = clean(observed) if isinstance(observed, str) else None
    if isinstance(observed, dict) and _has_type(observed, "PostalAddress"):
        event["location"]["city"] = clean(observed.get("addressLocality")) or None
        event["location"]["province"] = clean(observed.get("addressRegion")) or None
        event["location"]["country"] = clean(observed.get("addressCountry")) or None
        if event["location"]["address"] and key(observed.get("streetAddress")) != key(event["location"]["address"]):
            conflicts.append({"field": "address", "code": "visible_and_schema_street_disagree"})
    elif isinstance(observed, str):
        # The reviewed schema serializes street, municipality, district. The
        # street must be the exact visible #map value; commas in a street are
        # removed with that complete prefix, not guessed as municipality cuts.
        street = event["location"]["address"]
        if street and clean(observed).startswith(street + ","):
            tail = clean(observed)[len(street) + 1:]
            event["location"]["city"] = clean(tail.split(",")[0]) or None
        elif not street and observed.lstrip().startswith(","):
            event["location"]["city"] = clean(observed.lstrip()[1:].split(",")[0]) or None
        elif street:
            conflicts.append({"field": "address", "code": "visible_and_schema_street_disagree"})
    if event["location"]["city"]:
        proof["location.city"] = ["head Event.location.address: explicit municipality component"]
    else:
        warnings.append("source_municipality_not_explicit")

    date_text = text(when)
    span = re.match(r"^Quando\s+Dal\s+(\d{2}/\d{2}/\d{4})\s+al\s+(\d{2}/\d{2}/\d{4})(?:\s|$)", date_text, re.I)
    start, end = (_day(span[1]), _day(span[2])) if span else (None, None)
    if not start or not end or start > end:
        conflicts.append({"field": "calendar", "code": "visible_edition_bounds_unparsed"})
    else:
        event["edition_intervals"] = [{"start": start, "end": end}]
        proof["edition_intervals"] = [WHEN + " visible Dal/Al dates"]
        schema_start, schema_end = _day(schema.get("startDate")), _day(schema.get("endDate"))
        if schema_start != start or schema.get("endDate") is not None and schema_end != end:
            conflicts.append({"field": "calendar", "code": "visible_and_schema_edition_disagree"})
        title_years = set(re.findall(r"(?<!\d)(20\d{2}|2100)(?!\d)", event["name"]))
        if title_years and start[:4] not in title_years:
            conflicts.append({"field": "calendar", "code": "title_edition_year_disagrees"})
            proof["calendar.title_year"] = [HEADER + " h1.l-entry__title: explicit year"]
    hours = nodes(when, tag="span", cls="u-label-011")
    if len(hours) > 1:
        conflicts.append({"field": "hours", "code": "multiple_visible_hours_labels"})
    elif len(hours) == 1:
        literal = preserve_hours_text(text(hours[0]))
        if key(literal) not in {"", "orario non disponibile", "orari non disponibili"}:
            event["hours_text"] = literal
            event["hours_intervals"] = _hours(literal)
            proof["hours_text"] = [WHEN + " .u-label-011"]
            if not event["hours_intervals"]:
                event["hours_qualifications"] = [literal]
            if HOURS_PAIR.fullmatch(literal) and not event["hours_intervals"]:
                conflicts.append({"field": "hours", "code": "clock_interval_not_ordered_or_valid"})
            if re.search(r"\b(?:vari|programma|vedi|concert[oi]|laboratori[oi]|workshop|spettacol[oi]|allestimento|prove|dj set|visite guidate)\b", key(literal)):
                conflicts.append({"field": "hours", "code": "programme_hours_scope_unrepresented"})
        else:
            warnings.append("hours_not_published")
    # Programme content cannot fill any positive field. Explicit uncertainty
    # in the event body can hold its calendar without claiming cancellation.
    for paragraph in nodes(bodies[0], tag="p"):
        statement = body_text(paragraph)
        qualification = re.search(r"\b(?:annullat[oaie]|rinviat[oaie]|posticipat[oaie]|sospes[oaie])\b", statement, re.I)
        if qualification:
            # Retain the exact qualifying term, not an unrelated programme
            # or a whole article. Its unresolved scope holds the calendar.
            event["scope_statements"].append(qualification[0])
            proof.setdefault("scope_statements", []).append("article.l-entry section.l-entry__body p")
    if event["scope_statements"]:
        conflicts.append({"field": "calendar", "code": "event_body_calendar_qualification_unresolved"})
    schema_status = str(schema.get("eventStatus") or "").split("/")[-1]
    if schema_status in {"EventCancelled", "EventPostponed"} and start != end:
        event["conditions"].append(schema_status)
        proof["conditions"] = ["head Event.eventStatus"]
        conflicts.append({"field": "calendar", "code": "non_open_edition_status"})
    event["calendar_complete"] = bool(start and end and not any(c["field"] in {"calendar", "identity"} for c in conflicts))
    if start and start == end and event["calendar_complete"]:
        interval = event["hours_intervals"][0] if len(event["hours_intervals"]) == 1 else {}
        status = {"EventCancelled": "cancelled", "EventPostponed": "postponed", "EventRescheduled": "rescheduled"}.get(schema_status, "source_listed")
        event["occurrences"] = [{"date": start, "start_time": interval.get("start"), "end_time": interval.get("end"), "status": status,
                                  "evidence": [WHEN + " explicit single date"]}]
        event["calendar_scope"] = "explicit_visible_list"
    bylines = [n for n in nodes(articles[0], tag="section") if any("l-entry__byline" in c for c in classes(n))]
    times = [n for byline in bylines for n in nodes(byline, tag="time")]
    if len(times) == 1:
        literal = text(times[0])
        match = re.fullmatch(r"(\d{1,2})\s+(" + "|".join(MONTHS) + r")\s+(\d{4})\s+\d{2}:\d{2}", literal, re.I)
        if match:
            try:
                source["published_at"] = date(int(match[3]), MONTHS[match[2].lower()], int(match[1])).isoformat()
                proof["source.published_at"] = ["article.l-entry section.l-entry__byline time: " + literal]
            except ValueError:
                warnings.append("invalid_publication_date")
        else:
            warnings.append("publication_date_unparsed")
    elif len(times) > 1:
        warnings.append("multiple_publication_times_unresolved")
    result["status"] = "held" if conflicts else "parsed"
    return result


parse = parse_detail
