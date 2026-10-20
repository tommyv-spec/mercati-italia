"""Read one Eventi e Sagre detail page without network or calendar projection.

The category prefixes share a detail layout. Identity comes only from the
matching event card; content ends before navigation, related events and the
publisher footer. A page read, its editorial modification and an edition's
dates are different evidence. JSON-LD is checked against visible fields and
never supplies opening hours from midnight / end-of-day date placeholders.

The result retains source intervals, archive state, scope limits and conflicts
for a future evidence adapter. RawMarket/CleanMarket cannot yet round-trip all
of those fields. ``legacy_fields`` therefore withholds forecasts which that
older cleaner could produce without preserving their calendar limits. It does
not discard archived records or turn absence/conflict into a catalog deletion.
Descriptions are returned only in memory for the existing legacy interface;
audit reports should retain field presence and hashes, not editorial body text.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from dataclasses import dataclass, field
from datetime import date, datetime
from html.parser import HTMLParser
from urllib.parse import unquote_plus, urlsplit


MAX_BYTES = 2_500_000
MAX_NODES = 60_000
VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input",
                  "link", "meta", "param", "source", "track", "wbr"})
IGNORED = frozenset({"script", "style", "noscript", "nav", "footer", "aside",
                     "form", "svg", "template", "button"})
BLOCKS = frozenset({"p", "div", "li", "ul", "ol", "section", "article", "table",
                    "tr", "td", "th", "h1", "h2", "h3", "h4", "blockquote"})
EXCLUDED_IDS = frozenset({"correlati", "newsComune", "opzioniEvento", "serviziComune",
                          "vetrine", "condividi"})
DAY = r"(?:luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)"
STREET = re.compile(r"\b(?:via|viale|piazza|p\.zza|p\.za|piazzale|corso|largo|"
                    r"lungomare|lungolago|vicolo|contrada|giardini|parco)\b", re.I)
TIME = r"(?:[01]?\d|2[0-4])(?:[.:,][0-5]\d)?"
HOURS = re.compile(r"\b(?:dalle?\s+(?:ore\s+)?|ore\s+)"
                   r"(?P<start>" + TIME + r")\s*(?:alle?\s+(?:ore\s+)?|[-–—]\s*)"
                   r"(?P<end>" + TIME + r")(?![\d:.,])", re.I)
START_ONLY = re.compile(r"\bdalle?\s+(?:ore\s+)?(" + TIME + r")(?![\d:.,])", re.I)
RECURRENCE = re.compile(r"\b(?:ogni\s+|tutt[ie]\s+[ie]\s+|"
                        r"(?:il|la)\s+(?:prim[oa]|second[oa]|terz[oa]|quart[oa]|ultim[oa])\s+)"
                        r"[^.!?\n]{0,70}" + DAY + r"\b", re.I)
SCOPE = re.compile(r"\b(?:tranne|eccetto|esclus[oaie]|sospes[oaie]|sospension[ei]|"
                   r"estiv[oaie]|invernal[ei]|maltempo|annullat[oaie]|fino\s+al|dal\s+\d)", re.I)
SIMPLE_RULE = re.compile(r"ogni\s+(?:(?:prima|primo|seconda|secondo|terza|terzo|quarta|quarto|"
                         r"ultima|ultimo)\s+)?" + DAY + r"(?:\s+del\s+mese)?", re.I)


def _clean(value):
    return " ".join(str(value or "").split())


def _key(value):
    text = unicodedata.normalize("NFKD", _clean(value).casefold())
    return " ".join(re.sub(r"[^\w]+", " ", "".join(
        c for c in text if not unicodedata.combining(c))).split())


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
            raise ValueError("Eventi e Sagre HTML exceeds parser bounds")
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


def _walk(node):
    yield node
    for child in node.children:
        if isinstance(child, _Node):
            yield from _walk(child)


def _classes(node):
    return set(str(node.attrs.get("class") or "").split())


def _lines(node):
    result, current = [], []

    def flush():
        line = _clean("".join(current))
        if line:
            result.append(line)
        current.clear()

    def visit(n):
        if n.tag in IGNORED or n.attrs.get("id") in EXCLUDED_IDS:
            return
        if n.tag in BLOCKS or n.tag == "br":
            flush()
        for item in n.children:
            if isinstance(item, str):
                current.append(item)
            else:
                visit(item)
        if n.tag in BLOCKS:
            flush()

    visit(node)
    flush()
    return result


def _text(node):
    return " ".join(_lines(node))


def _raw_text(node):
    return "".join(x if isinstance(x, str) else _raw_text(x) for x in node.children)


def _event_id(url):
    try:
        p = urlsplit(url)
        if (p.scheme != "https" or p.hostname != "www.eventiesagre.it" or p.username
                or p.password or p.port not in (None, 443) or p.query or p.fragment):
            return None
        m = re.fullmatch(r"/(?:Mercatini|Eventi)_[A-Za-z+]+/(\d+)_[^/]+\.html", p.path)
        return m.group(1) if m else None
    except ValueError:
        return None


def _date(value):
    for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt).date().isoformat()
        except (ValueError, TypeError):
            pass
    return None


def _clock(value):
    parts = re.split(r"[.:,]", value)
    hour, minute = int(parts[0]), int(parts[1]) if len(parts) == 2 else 0
    if hour > 24 or minute > 59 or hour == 24 and minute:
        return None
    return f"{hour:02}:{minute:02}"


def _hours(line):
    label = re.match(r"^Orari(?:o)?(?:\s+del\s+mercato)?\s*:\s*(.*)$", line, re.I)
    if label and re.match(r"\d", label.group(1)):
        line = "ore " + label.group(1)
    found = []
    for match in HOURS.finditer(line):
        start, end = _clock(match["start"]), _clock(match["end"])
        if start and end and start != end:
            found.append(start + "–" + end)
    return list(dict.fromkeys(found))


def _recurrences(lines):
    values = []
    for line in lines:
        label = re.match(r"^(?:quando\s+si\s+svolge|giorni\s+di\s+svolgimento)\s*:\s*(.+)$", line, re.I)
        if label:
            value = label.group(1)
        else:
            match = RECURRENCE.search(line)
            if not match:
                match = re.search(r"\b[1-4]\s*[aª°^]?\s*" + DAY +
                                  r"\s+(?:di\s+)?ogni\s+mese\b", line, re.I)
            if not match:
                continue
            # Keep qualifiers in the same sentence instead of retaining only
            # the first weekday token and losing "tranne agosto" / seasonality.
            value = re.split(r"[.!?](?:\s|$)", line[match.start():], maxsplit=1)[0]
        if re.search(DAY, value, re.I):
            values.append(_clean(value))
    return list(dict.fromkeys(values))


def _locality(card):
    values = set()
    for node in _walk(card):
        if node.tag != "a":
            continue
        p = urlsplit(str(node.attrs.get("href") or ""))
        if p.hostname not in (None, "www.eventiesagre.it"):
            continue
        parts = p.path.strip("/").split("/")
        if len(parts) < 8 or parts[0] != "cerca" or parts[-1] != "rilib":
            continue
        region, province, city = [unquote_plus(x) for x in parts[-4:-1]]
        visible = _text(node)
        if re.fullmatch(r"[A-Z]{2}", province) and city and _key(visible) == _key(city):
            values.add((visible, province, region))
    return values


def _jsonld(root, source_id, issues):
    events = []
    invalid = 0
    for node in _walk(root):
        if node.tag != "script" or node.attrs.get("type") != "application/ld+json":
            continue
        try:
            value = json.loads(_raw_text(node))
        except (ValueError, RecursionError):
            invalid += 1
            continue
        objects = value if isinstance(value, list) else [value]
        for obj in objects:
            if isinstance(obj, dict) and isinstance(obj.get("@graph"), list):
                objects = [*objects, *obj["@graph"]]
        for obj in objects:
            if (isinstance(obj, dict) and obj.get("@type") == "Event"
                    and _event_id(str(obj.get("url") or "")) == source_id):
                events.append(obj)
    if invalid:
        issues.append("invalid_jsonld_ignored")
    return events, invalid


def parse_eventiesagre_html(blob, source_url, *, today=None):
    """Return scoped factual fields plus explicit uncertainty, without writes.

    ``source_rows`` holds repeated Luogo/Giorni/Orario blocks separately. They
    must not be flattened into one market; this function creates no catalog IDs.
    A valid JSON-LD date is only compared with the event card, not assumed to be
    an opening time, every day in an interval, or independent corroboration.
    """
    today = today or date.today()
    source_id = _event_id(source_url)
    if (not source_id or not isinstance(today, date) or not isinstance(blob, bytes)
            or not 100 <= len(blob) <= MAX_BYTES):
        raise ValueError("Invalid bounded Eventi e Sagre detail sample")
    document = _Document()
    document.feed(blob.decode("utf-8-sig", errors="replace"))
    document.close()
    cards = [n for n in _walk(document.root) if n.attrs.get("id") == "schedaEvento"]
    contents = [n for n in _walk(document.root) if n.attrs.get("id") == "contenuto"]
    if len(cards) != 1 or len(contents) != 1:
        raise ValueError("Eventi e Sagre detail scopes are absent or ambiguous")
    card, content = cards[0], contents[0]
    numbers = re.findall(r"\bNumero\s+Evento\s*:\s*(\d+)\b", _text(card), re.I)
    headings = [n for n in content.children if isinstance(n, _Node) and n.tag == "h1"]
    if numbers != [source_id] or len(headings) > 1:
        raise ValueError("Eventi e Sagre event identity does not match its URL")
    issues = []
    left = [n for n in card.children if isinstance(n, _Node) and "SX" in _classes(n)]
    if len(left) != 1:
        raise ValueError("Eventi e Sagre event card columns are ambiguous")
    left = left[0]
    titles = [n for n in left.children if isinstance(n, _Node)
              and {"titolo", "recapito"} <= _classes(n) and not any(x.tag == "a" for x in _walk(n))]
    if len(titles) != 1 or not _text(titles[0]):
        raise ValueError("Eventi e Sagre card title is absent or ambiguous")
    name = _text(headings[0]) if headings else _text(titles[0])
    if _key(_text(titles[0])) != _key(name):
        raise ValueError("Eventi e Sagre card and content titles disagree")
    if not headings:
        issues.append("article_heading_absent_card_identity_used")
    localities = _locality(left)
    city, province, region = next(iter(localities)) if len(localities) == 1 else ("", "", "")
    if len(localities) != 1:
        issues.append("locality_missing_or_ambiguous")

    # The real content container also encloses related events. Stop at its
    # first direct divider / navigation block, and never scan the whole page.
    body_nodes, h3 = [], []
    for node in content.children:
        if not isinstance(node, _Node):
            continue
        if (node.tag == "hr" or node.attrs.get("id") in EXCLUDED_IDS
                or {"recapito", "freccia"} <= _classes(node)):
            break
        if node.tag == "h3":
            h3.append(node)
        elif node.tag not in {"h1", "h2"} and "displayStampaNone" not in _classes(node):
            body_nodes.append(node)
    header_lines = [line for node in h3 for line in _lines(node)]
    body_lines = [line for node in body_nodes for line in _lines(node)]
    if len(h3) != 1:
        issues.append("edition_heading_missing_or_ambiguous")
    header_places = re.findall(r"(?:^|[-–]|\b)([^()]+)\(([A-Z]{2})\)\s*$", " ".join(header_lines))
    if city and header_places:
        place, code = header_places[-1]
        if code != province or not _key(place).endswith(_key(city)):
            issues.append("card_heading_locality_conflict")
            city = province = region = ""

    card_lines = _lines(left)
    start = [_date(m.group(1)) for line in card_lines
             if (m := re.fullmatch(r"Dal:\s*(\d{2}/\d{2}/\d{4})", line, re.I))]
    end = [_date(m.group(1)) for line in card_lines
           if (m := re.fullmatch(r"Al:\s*(\d{2}/\d{2}/\d{4})", line, re.I))]
    intervals = []
    if len(start) == len(end) == 1 and start[0] and end[0] and start[0] <= end[0]:
        intervals = [{"start": start[0], "end": end[0]}]
    else:
        issues.append("edition_dates_missing_or_invalid")
    archived = any(n.attrs.get("id") == "eventopassato" and "evento passato" in _text(n).casefold()
                   for n in _walk(card))
    past = bool(intervals and intervals[0]["end"] < today.isoformat())
    if archived and intervals and intervals[0]["end"] >= today.isoformat():
        issues.append("archive_marker_date_conflict")

    updated_values = []
    for node in content.children:
        if not isinstance(node, _Node):
            continue
        m = re.fullmatch(r"Data ultimo aggiornamento pagina (\d{4}-\d{2}-\d{2})(?: \d{2}:\d{2}:\d{2})?", _text(node))
        if m and _date(m.group(1)):
            updated_values.append(m.group(1))
    updated_values = list(dict.fromkeys(updated_values))
    updated = updated_values[0] if len(updated_values) == 1 and updated_values[0] <= today.isoformat() else ""
    if updated_values and not updated:
        issues.append("publisher_date_conflict_or_future")

    events, invalid_ld = _jsonld(document.root, source_id, issues)
    for event in events:
        if intervals and any(str(event[key])[:10] != intervals[0][boundary]
                             for key, boundary in (("startDate", "start"), ("endDate", "end"))
                             if event.get(key)):
            issues.append("jsonld_visible_edition_conflict")
        loc = event.get("location")
        loc = loc.get("address") if isinstance(loc, dict) else None
        if isinstance(loc, dict) and city and loc.get("addressLocality") and _key(loc["addressLocality"]) != _key(city):
            issues.append("jsonld_visible_locality_conflict")

    card_addresses = []
    after_where = False
    for node in left.children:
        if not isinstance(node, _Node):
            continue
        value = _text(node)
        if value.casefold() == "dove:":
            after_where = True
            continue
        if after_where and any(x.tag == "a" for x in _walk(node)):
            break
        if after_where and "recapito" in _classes(node) and STREET.search(value):
            card_addresses.append(value)

    source_rows, current = [], None
    for line in body_lines:
        if (m := re.fullmatch(r"Luogo\s*:\s*(.+)", line, re.I)):
            current = {"address": m.group(1), "recurrence": "", "hours": ""}
            source_rows.append(current)
        elif current and (m := re.fullmatch(r"Giorni\s+di\s+svolgimento\s*:\s*(.+)", line, re.I)):
            current["recurrence"] = m.group(1)
        elif current and re.match(r"Orari(?:o)?\s*:", line, re.I):
            current["hours"] = "; ".join(_hours(line))
    unique_rows = list({(r["address"], r["recurrence"], r["hours"]): r for r in source_rows}.values())
    multiple_locations = len(unique_rows) > 1
    if multiple_locations:
        issues.append("multiple_market_rows_require_separate_identity")

    body_addresses = []
    for line in body_lines:
        m = re.fullmatch(r"(?:Dove fanno il mercato(?: settimanale)?|Luogo|Indirizzo|Sede)\s*:\s*(.+)", line, re.I)
        if m and STREET.search(m.group(1)):
            body_addresses.append(m.group(1))
        elif STREET.match(line) and len(line) <= 180:
            body_addresses.append(line)
        elif city:
            # Bounded location prose may put a lower-case street before the
            # already identified municipality. Do not grab arbitrary street
            # mentions from a programme, another town or a publisher address.
            m = re.match(r"^In\s+(.{3,120}?)\s+(?:ad?|nel\s+Comune\s+di)\s+"
                         + re.escape(city) + r"(?:\s|[,.;:]|$)", line, re.I)
            if m and STREET.match(m.group(1)):
                body_addresses.append(m.group(1))
            m = re.search(r"\bmercatin[oi]\b[^.;:]{0,80}\ballestit[oi]\s+in\s+"
                          r"([^;.!?]{3,120})(?:[;.!?]|$)", line, re.I)
            if m and STREET.match(m.group(1)):
                body_addresses.append(m.group(1))
    address_options = list({_key(x): x for x in [*card_addresses, *body_addresses]}.values())
    if len(address_options) > 1 and not multiple_locations:
        issues.append("visible_address_conflict")
    address = address_options[0] if len(address_options) == 1 and not multiple_locations else ""

    header_hours = list(dict.fromkeys(h for line in header_lines for h in _hours(line)))
    body_hours = list(dict.fromkeys(h for line in body_lines
                                  if re.match(r"Orari(?:o)?(?:\s+del\s+mercato)?\s*:", line, re.I)
                                  for h in _hours(line)))
    hour_options = list(dict.fromkeys([*header_hours, *body_hours]))
    hours = hour_options[0] if len(hour_options) == 1 and not multiple_locations else ""
    if len(hour_options) > 1 and not multiple_locations:
        issues.append("visible_hours_conflict")
    if not hour_options and not multiple_locations:
        starts = list(dict.fromkeys(_clock(m.group(1)) for line in header_lines
                                    if (m := START_ONLY.search(line))))
        if len(starts) == 1 and starts[0]:
            hours = "Dalle " + starts[0]

    recurrences = _recurrences(body_lines)
    recurrence = recurrences[0] if len(recurrences) == 1 and not multiple_locations else ""
    if len(recurrences) > 1 and not multiple_locations:
        issues.append("multiple_recurrence_statements")
    scope_lines = [line for line in body_lines if SCOPE.search(line)]
    blocking = {"locality_missing_or_ambiguous", "card_heading_locality_conflict",
                "jsonld_visible_locality_conflict", "multiple_market_rows_require_separate_identity",
                "multiple_recurrence_statements", "jsonld_visible_edition_conflict"}
    safe_recurrence = bool(recurrence and SIMPLE_RULE.fullmatch(recurrence) and not scope_lines
                           and not archived and not past and not intervals
                           and not blocking.intersection(issues))
    # Single-day editions remain source evidence, including past dates. Never
    # expand a span or attach today's read/modified date to the market calendar.
    single_dates = [r["start"] for r in intervals if r["start"] == r["end"]]
    if any(code in issues for code in ("jsonld_visible_edition_conflict", "archive_marker_date_conflict")):
        single_dates = []
    legacy = {"nome": name, "citta": city, "provincia": province, "regione": region,
              "indirizzo": address, "orario_raw": hours,
              "ricorrenza_raw": recurrence if safe_recurrence else "", "date_raw": single_dates}
    return {"schema": 1, "layout": "eventiesagre_detail_v1" if headings else "eventiesagre_card_only_v1", "source_url": source_url,
            "source_id": source_id, "source_sha256": hashlib.sha256(blob).hexdigest(),
            "source_modified_on": updated, "archive_marker": archived, "edition_is_past": past,
            "edition_intervals": intervals, "jsonld_events_matched": len(events),
            "invalid_jsonld_blocks": invalid_ld, "recurrence_text": recurrence,
            "recurrence_statements": recurrences, "scope_statements": scope_lines,
            "source_rows": unique_rows, "issues": sorted(set(issues)),
            "legacy_fields": legacy, "description_text": " ".join(body_lines),
            "market_openings_verified": False, "network_requests": 0}
