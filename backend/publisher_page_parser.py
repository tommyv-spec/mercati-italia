#!/usr/bin/env python3
"""Parse a bounded publisher page of municipality / Quando / Dove / Orari blocks.

Pure extraction: no HTTP, catalog writes, geocoding or calendar prediction.
The contract names a *page format*, its ordinary market kind and a municipality
gazetteer. It never supplies market addresses, hours, weekdays or catalog IDs.

Required contract keys: source_id, category, market_kind (ordinary/farmers),
cadence (weekly), content_scope ({tag, class and/or id}), municipalities
([{citta, provincia, regione, istat?, aliases?}]). Optional start_heading and
end_heading delimit one section; cardinality bounds detect incomplete layouts.

source_row_id deliberately excludes mutable venue/hours and DOM position. If
the publisher gives two venues for the same municipality/locality/day/kind,
both rows survive with identity_unique=False. A consumer must check that flag,
comune_giorno_univoco, cadenza and issues before joining a catalog record.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import date
from html.parser import HTMLParser
from urllib.parse import urlsplit


MAX_HTML_BYTES = 5_000_000
MAX_NODES = 100_000
MAX_ROWS = 3000
WEEKDAYS = ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica")
MONTHS = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
          "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre")
DAY_PATTERN = r"luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica"
DAY_RE = re.compile(r"\b(" + DAY_PATTERN + r")\b", re.I)
DAY_RANGE = re.compile(r"\b(?:dal|da)\s+(?:" + DAY_PATTERN +
                       r")\s+(?:al|a)\s+(?:" + DAY_PATTERN + r")\b", re.I)
FIELD_RE = re.compile(
    r"^\s*(quando|dove|orari(?:o)?\s+(?:annual[ei]|di\s+vendita)|orari(?:o)?|frazioni|info)\s*:\s*(.*)$", re.I)
FIELD_NAMES = {"quando": "when", "dove": "where", "orario": "hours", "orari": "hours",
               "orari annuali": "hours", "orario annuale": "hours",
               "orario di vendita": "hours", "orari di vendita": "hours",
               "frazioni": "fractions", "info": "info"}
TIME_RE = re.compile(
    r"(?<![\d:.])(?:dalle?\s+)?(?:ore\s+)?"
    r"(?P<start>\d{1,2}(?:[.:]\d{2})?)\s*"
    r"(?:alle?\s+|[–—-]\s*)(?:ore\s+)?(?P<end>\d{1,2}(?:[.:]\d{2})?)"
    r"(?![\d:]|\.\d)", re.I)
UPDATED_RE = re.compile(
    r"\b(?:aggiornat[oa]\s+(?:al|il)|ultimo\s+aggiornamento)\s*:?\s*"
    r"(?P<day>\d{1,2}/\d{1,2}/\d{4}|\d{4}-\d{2}-\d{2})", re.I)
VOID = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input",
                  "link", "meta", "param", "source", "track", "wbr"})
IGNORE = frozenset({"script", "style", "nav", "header", "footer", "aside", "template",
                    "noscript", "svg", "form", "button"})
BLOCK_TAGS = frozenset({"p", "div", "section", "article", "li", "ul", "ol", "dl", "dt",
                        "dd", "table", "tr", "td", "th", "blockquote",
                        "h1", "h2", "h3", "h4", "h5", "h6"})
EMPHASIS = frozenset({"strong", "b", "dt", "th", "h1", "h2", "h3", "h4", "h5", "h6"})


def _clean(value):
    return " ".join(str(value or "").split())


def _key(value):
    text = unicodedata.normalize("NFKD", _clean(value).casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    return " ".join(re.sub(r"[^\w]+", " ", text).split())


DAY_INDEX = {_key(value): i for i, value in enumerate(WEEKDAYS)}


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
        self.nodes = 0

    def handle_starttag(self, tag, attrs):
        self.nodes += 1
        if self.nodes > MAX_NODES or len(self.stack) > 200:
            raise ValueError("Publisher HTML exceeds parser bounds")
        # HTML permits omitted closing p/li tags. Mirror only those local
        # boundaries; do not recover a missing content container by guessing.
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


@dataclass
class _Line:
    text: str
    heading: bool
    index: int
    block_tag: str
    block_key: int


def _lines(scope):
    result, parts = [], []

    def flush():
        value = _clean("".join(text for text, *_ in parts))
        if value:
            emphasized = all(bold for text, bold, *_ in parts if text.strip())
            first = next(part for part in parts if part[0].strip())
            result.append(_Line(value, emphasized, len(result), first[2], first[3]))
        parts.clear()

    def visit(node, bold=False, container=None):
        if node.tag in IGNORE:
            return
        if node.tag == "br":
            flush()
            return
        if node.tag in BLOCK_TAGS:
            flush()
            container = node
        container = container or scope
        bold = bold or node.tag in EMPHASIS
        for child in node.children:
            if isinstance(child, str):
                parts.append((child, bold, container.tag, id(container)))
            else:
                visit(child, bold, container)
        if node.tag in BLOCK_TAGS:
            flush()

    visit(scope)
    flush()
    return result


def _field(line):
    match = FIELD_RE.match(line.text)
    if match:
        label = _key(match.group(1))
        return ("hours" if label.startswith("orari") else FIELD_NAMES[label]), _clean(match.group(2))
    # Definition lists and heading/value layouts often omit the colon.
    if line.heading and _key(line.text) in FIELD_NAMES:
        return FIELD_NAMES[_key(line.text)], ""
    if re.match(r"^info\b", line.text, re.I):
        return "info", ""
    return None


def _issue(issues, code, *, severity="error", line=None, city=None, detail=None):
    item = {"code": code, "severity": severity}
    if line is not None:
        item["line"] = line
    if city:
        item["istat"] = city["istat"]
        item["citta"] = city["citta"]
    if detail:
        item["detail"] = _clean(detail)[:180]
    issues.append(item)


def _validate_contract(contract):
    if not isinstance(contract, dict):
        raise ValueError("Missing publisher page contract")
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{1,79}", str(contract.get("source_id", ""))):
        raise ValueError("Invalid publisher source_id")
    if (not isinstance(contract.get("category"), str) or
            not 1 <= len(contract["category"].strip()) <= 60 or
            contract.get("market_kind") not in {"ordinary", "farmers"} or
            contract.get("cadence") != "weekly"):
        raise ValueError("Explicit page market kind, category and cadence required")
    scope = contract.get("content_scope")
    if (not isinstance(scope, dict) or not scope or set(scope) - {"tag", "class", "id"}
            or any(not isinstance(v, str) or not v.strip() for v in scope.values())):
        raise ValueError("Explicit bounded content_scope required")
    for name in ("start_heading", "end_heading"):
        if contract.get(name) is not None and (
                not isinstance(contract[name], str) or not 1 <= len(contract[name]) <= 200):
            raise ValueError("Invalid publisher section delimiter")
    for name, default in (("min_rows", 1), ("max_rows", MAX_ROWS),
                          ("min_city_blocks", 1), ("max_city_blocks", MAX_ROWS)):
        value = contract.get(name, default)
        if type(value) is not int or not 0 <= value <= MAX_ROWS:
            raise ValueError("Invalid publisher cardinality bound")
    for low, high in (("min_rows", "max_rows"), ("min_city_blocks", "max_city_blocks")):
        if contract.get(low, 1) > contract.get(high, MAX_ROWS):
            raise ValueError("Reversed publisher cardinality bounds")
    municipalities = contract.get("municipalities")
    if not isinstance(municipalities, (list, tuple)) or not 1 <= len(municipalities) <= 10_000:
        raise ValueError("Municipality gazetteer is required")
    lookup = defaultdict(dict)
    for entry in municipalities:
        if (not isinstance(entry, dict) or
                (entry.get("istat") not in (None, "") and
                 not re.fullmatch(r"\d{6}", str(entry.get("istat")))) or
                any(not isinstance(entry.get(k), str) or not entry[k].strip()
                    for k in ("citta", "provincia", "regione"))):
            raise ValueError("Invalid ISTAT municipality identity")
        aliases = entry.get("aliases", [])
        if not isinstance(aliases, (list, tuple)) or any(not isinstance(a, str) for a in aliases):
            raise ValueError("Invalid municipality heading aliases")
        city = {k: str(entry[k]).strip() for k in ("citta", "provincia", "regione")}
        city["istat"] = str(entry.get("istat") or "").strip()
        names = [city["citta"], "Comune di " + city["citta"],
                 city["citta"] + " (" + city["provincia"] + ")", *aliases]
        for name in names:
            if _key(name):
                lookup[_key(name)][(city["istat"], *_city_key(city))] = city
    return {key: list(value.values()) for key, value in lookup.items()}


def _source_date(root, lines, issues):
    visible, metadata = set(), set()
    for line in lines:
        for match in UPDATED_RE.finditer(line.text):
            raw = match.group("day")
            try:
                if "/" in raw:
                    day, month, year = map(int, raw.split("/"))
                    visible.add(date(year, month, day).isoformat())
                else:
                    visible.add(date.fromisoformat(raw).isoformat())
            except ValueError:
                _issue(issues, "invalid_source_updated_on", line=line.index)
    for node in _walk(root):
        if (node.tag == "meta" and
                node.attrs.get("property", node.attrs.get("name")) == "article:modified_time"):
            value = node.attrs.get("content", "")
            try:
                metadata.add(date.fromisoformat(value[:10]).isoformat())
            except (TypeError, ValueError):
                _issue(issues, "invalid_source_updated_on")
    candidates = visible | metadata
    if len(candidates) > 1:
        _issue(issues, "conflicting_source_updated_on")
        return None
    return next(iter(candidates), None)


def _days(value):
    return sorted({DAY_INDEX[_key(match.group())] for match in DAY_RE.finditer(value)})


def _cadence(value, ordinary):
    text = _key(value)
    if re.search(r"\b(?:settimane alterne|ogni (?:due|2) settimane|quindicinale|ogni (?:quindici|15) giorni)\b", text):
        return "fortnightly"
    if re.search(r"\b(?:prim[oaie]|second[oaie]|terz[oaie]|quart[oaie]|ultim[oaie]|mensil\w*)\b", text):
        return "monthly_or_qualified"
    if re.search(r"\b(?:estiv\w*|invernal\w*|estate|inverno|solo|stagionale)\b", text):
        return "seasonal_or_qualified"
    if re.search(r"\b(?:" + "|".join(MONTHS) + r"|20\d{2})\b", text):
        return "dated_or_qualified"
    return ordinary


def _daypart(value):
    matches = []
    for word, pattern in (("mattina", r"\bmattin[ao]\b"),
                          ("pomeriggio", r"\bpomeriggio\b"), ("sera", r"\bsera\b")):
        if re.search(pattern, value, re.I):
            matches.append(word)
    return "; ".join(matches)


def _hour(value):
    parts = re.split(r"[.:]", value)
    hour, minute = int(parts[0]), int(parts[1]) if len(parts) == 2 else 0
    if not 0 <= hour <= 23 or not 0 <= minute <= 59:
        return None
    return f"{hour:02d}:{minute:02d}"


def _period(value):
    text = _key(value).strip()
    if text in {"", "e", "annuali", "annuale"}:
        return ""
    if text in {"estivo", "estiva", "estate", "in estate"}:
        return "Estate"
    if text in {"invernale", "inverno", "in inverno"}:
        return "Inverno"
    month = "(" + "|".join(MONTHS) + ")"
    single = re.fullmatch(r"(?:a |in |nel mese di )?" + month, text)
    if single:
        return single.group(1)
    pair = re.fullmatch(r"(?:da |dal )?" + month + r"\s+(?:a |al )?" + month, text)
    if pair:
        return pair.group(1) + "–" + pair.group(2)
    return None


def _hours(value):
    """Return explicit time spans, preserving the scope of each month/season."""
    if not value:
        return "", [], []
    spans, end = [], 0
    for match in TIME_RE.finditer(value):
        prefix = value[end:match.start()].strip(" \t\n/;,:.–—-")
        period = _period(prefix)
        start, finish = _hour(match.group("start")), _hour(match.group("end"))
        if period is None or not start or not finish or finish <= start:
            return "", [], ["unparsed_or_invalid_hours"]
        spans.append({"periodo": period, "inizio": start, "fine": finish})
        end = match.end()
    if not spans:
        return "", [], ([] if _key(value) in {"mattina", "mattino", "pomeriggio", "sera"}
                         else ["unparsed_or_invalid_hours"])
    if value[end:].strip(" \t\n.;,/–—-"):
        return "", [], ["unparsed_or_invalid_hours"]
    # Do not flatten overlapping unnamed and named periods into a broad range.
    if len(spans) > 1 and any(x["periodo"] for x in spans) and not all(x["periodo"] for x in spans):
        return "", [], ["unparsed_or_invalid_hours"]
    formatted = []
    for i, span in enumerate(spans):
        period = span["periodo"]
        if i == 0 and period:
            period = period[0].upper() + period[1:]
        formatted.append((period + ": " if period else "") + span["inizio"] + "–" + span["fine"])
    return "; ".join(formatted), spans, []


def _alternatives(address):
    pieces = re.split(r"\s+(?:e\s*/\s*o|oppure|o)\s+", address, flags=re.I)
    return [_clean(piece) for piece in pieces] if len(pieces) > 1 else []


def _venues(value, days):
    """Keep a shared multi-street venue intact; split only explicit day labels."""
    hints = []
    for match in re.finditer(r"\(([^()]*)\)", value):
        selected = _days(match.group(1))
        remainder = DAY_RE.sub("", match.group(1))
        if selected and not remainder.strip(" ,/;&e–—-"):
            hints.append((match, selected))
    if not hints:
        if _days(value):
            return [], ["unmapped_venue_weekday"]
        return [(day, _clean(value), _alternatives(value)) for day in days], []
    result, used, end = [], set(), 0
    for match, selected in hints:
        address = _clean(value[end:match.start()].strip(" ,;–—-"))
        if not address or not set(selected) <= set(days):
            return [], ["venue_weekday_conflict"]
        for day in selected:
            result.append((day, address, _alternatives(address)))
            used.add(day)
        end = match.end()
    if value[end:].strip(" ,;.–—-") or used != set(days):
        return [], ["unmapped_venue_weekday"]
    return result, []


def _fraction_rows(value):
    # Every fraction must supply its own weekday and venue. Parent hours and
    # venue are never inherited by a fraction.
    parts = re.split(r"\s+[–—-]\s+(?=[^()]+\bil\s+(?:" + DAY_PATTERN + r")\b)", value, flags=re.I)
    result = []
    for part in parts:
        match = re.fullmatch(
            r"\s*(?P<locality>[^():]+?)\s+(?P<when>il\s+(?:" + DAY_PATTERN +
            r")\b[^()]*)\s*\((?P<where>[^()]+)\)\s*[.;]?\s*", part, re.I)
        if not match:
            return [], ["unparsed_fraction"]
        result.append((_clean(match.group("locality")), _clean(match.group("when")),
                       _clean(match.group("where"))))
    return result, []


def _source_id(contract, city, locality, weekday):
    # The bundled ISTAT-derived gazetteer currently contains municipality
    # names/provinces, not numeric codes. Optional numeric metadata must not
    # change an already stable source identity when it is later supplied.
    identity = [*_city_key(city), _key(locality), weekday, contract["market_kind"]]
    digest = hashlib.sha256(json.dumps(identity, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
    return contract["source_id"] + "-" + digest[:20]


def _city_key(city):
    return tuple(_key(city[name]) for name in ("regione", "provincia", "citta"))


def _row(contract, source_url, updated, city, *, locality, when, day, address,
         alternatives, hours_text, hours, row_issues):
    return {
        "source_id": contract["source_id"],
        "source_row_id": _source_id(contract, city, locality, day),
        "url_fonte": source_url, **city, "localita": locality,
        "categoria": contract["category"], "market_kind": contract["market_kind"],
        "giorno": WEEKDAYS[day], "weekday": day,
        "cadenza": _cadence(when, contract["cadence"]), "quando_testo": when,
        # A qualifier beside one of several named weekdays need not apply to
        # every weekday. Keep the complete source text and do not spread it.
        "fascia_giorno": _daypart(when) if len(_days(when)) == 1 else "", "indirizzo": address,
        "sedi_alternative": alternatives, "orario_testo": hours_text, "orari": hours,
        "fonte_aggiornata_il": updated, "identity_unique": True,
        "comune_giorno_univoco": True,
        "issues": sorted(set(row_issues + (["alternative_venues"] if alternatives else []))),
    }


def _block_rows(block, contract, source_url, updated, issues):
    city, lines = block["city"], block["lines"]
    fields, pending, last_block, in_info = [], None, None, False
    for line in lines:
        found = _field(line)
        if found:
            if pending:
                _issue(issues, "empty_field", line=pending[2], city=city)
                pending = None
            kind, value = found
            if kind == "info":
                in_info = True
                last_block = None
                continue
            in_info = False
            if value:
                fields.append((kind, value, line.index))
                last_block = line.block_key
            else:
                pending = (kind, "", line.index)
        elif pending:
            fields.append((pending[0], line.text, pending[2]))
            pending = None
            last_block = line.block_key
        elif not in_info:
            # A visual break inside a label value is not a new market. Keep
            # explicit continued fractions/day-address pairs, while flagging
            # new unknown labelled fields instead of silently losing them.
            previous = fields[-1] if fields and line.block_key == last_block else None
            if previous and previous[0] == "fractions" and not _fraction_rows(line.text)[1]:
                fields[-1] = (previous[0], previous[1] + " – " + line.text, previous[2])
            elif previous and previous[0] == "where" and _days(line.text):
                fields[-1] = (previous[0], previous[1] + ", " + line.text, previous[2])
            elif previous and previous[0] == "when" and _days(line.text):
                fields[-1] = (previous[0], previous[1] + "; " + line.text, previous[2])
            elif (_days(line.text) or TIME_RE.search(line.text) or
                  re.match(r"^[\w\s]{2,50}:", line.text)):
                _issue(issues, "unparsed_market_line", line=line.index, city=city)
    if pending:
        _issue(issues, "empty_field", line=pending[2], city=city)
    groups, fractions = [], []
    group = {"when": "", "where": [], "hours": []}
    for kind, value, line in fields:
        if kind == "fractions":
            fractions.append((value, line))
        elif kind == "when":
            if group["when"]:
                groups.append(group)
                group = {"when": "", "where": [], "hours": []}
            group["when"] = value
        elif kind == "where":
            group["where"].append(value)
        elif kind == "hours":
            group["hours"].append(value)
    if any(group.values()):
        groups.append(group)
    rows = []
    for group in groups:
        when = group["when"]
        days = _days(when)
        if not days or not group["where"] or DAY_RANGE.search(when):
            _issue(issues, "missing_or_unsupported_when_where", line=block["line"], city=city)
            continue
        hours_text, hours, hours_issues = _hours("; ".join(group["hours"]))
        for code in hours_issues:
            _issue(issues, code, severity="review", line=block["line"], city=city)
        for where in group["where"]:
            venues, venue_issues = _venues(where, days)
            for code in venue_issues:
                _issue(issues, code, line=block["line"], city=city)
            for day, address, alternatives in venues:
                if not address or len(address) > 500:
                    _issue(issues, "invalid_venue", line=block["line"], city=city)
                    continue
                rows.append(_row(contract, source_url, updated, city, locality="", when=when,
                                 day=day, address=address, alternatives=alternatives,
                                 hours_text=hours_text, hours=hours, row_issues=hours_issues))
    for value, line in fractions:
        records, fraction_issues = _fraction_rows(value)
        for code in fraction_issues:
            _issue(issues, code, line=line, city=city)
        for locality, when, address in records:
            for day in _days(when):
                rows.append(_row(contract, source_url, updated, city, locality=locality, when=when,
                                 day=day, address=address, alternatives=_alternatives(address),
                                 hours_text="", hours=[], row_issues=[]))
    if not rows:
        _issue(issues, "municipality_without_parsed_rows", line=block["line"], city=city)
    return rows


def parse_page(html: str | bytes, *, source_url: str, contract: dict) -> dict:
    """Extract every supported source row and explicitly report partial parses.

    `source_sha256` hashes the supplied bytes (UTF-8 bytes when passed a str).
    `fonte_aggiornata_il` is read solely from explicit visible update text or
    article:modified_time metadata. Reading a cache never changes this date.
    """
    lookup = _validate_contract(contract)
    parts = urlsplit(source_url)
    if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
        raise ValueError("Publisher evidence requires an HTTPS source URL")
    if not isinstance(html, (str, bytes)):
        raise TypeError("Expected publisher HTML bytes or text")
    raw = html.encode("utf-8") if isinstance(html, str) else html
    if not 0 < len(raw) <= MAX_HTML_BYTES:
        raise ValueError("Publisher HTML exceeds parser bounds")
    text = html if isinstance(html, str) else raw.decode("utf-8-sig")
    document = _Document()
    document.feed(text)
    document.close()
    issues, rows = [], []
    result = {"rows": rows, "issues": issues, "metrics": {}, "complete": False,
              "fonte_aggiornata_il": None, "source_sha256": hashlib.sha256(raw).hexdigest()}
    selector = contract["content_scope"]
    scopes = [node for node in _walk(document.root) if (
        (not selector.get("tag") or node.tag == selector["tag"].lower()) and
        (not selector.get("id") or node.attrs.get("id") == selector["id"]) and
        (not selector.get("class") or selector["class"] in (node.attrs.get("class") or "").split())
    )]
    if len(scopes) != 1:
        _issue(issues, "content_scope_not_unique")
        result["metrics"] = {"content_scopes": len(scopes), "city_blocks": 0, "rows": 0}
        return result
    all_lines = _lines(scopes[0])
    updated = _source_date(document.root, all_lines, issues)
    result["fonte_aggiornata_il"] = updated
    low, high = 0, len(all_lines)
    for key in ("start_heading", "end_heading"):
        marker = contract.get(key)
        if marker is None:
            continue
        matches = [i for i, line in enumerate(all_lines) if line.heading and _key(line.text) == _key(marker)]
        if len(matches) != 1:
            _issue(issues, "section_delimiter_not_unique", detail=key)
            result["metrics"] = {"content_scopes": 1, "city_blocks": 0, "rows": 0}
            return result
        if key == "start_heading":
            low = matches[0] + 1
        else:
            high = matches[0]
    if low >= high:
        _issue(issues, "empty_or_reversed_section")
        result["metrics"] = {"content_scopes": 1, "city_blocks": 0, "rows": 0}
        return result
    blocks, current, orphan_heading, orphan_reported = [], None, None, False
    for line in all_lines[low:high]:
        if UPDATED_RE.search(line.text):
            continue
        found = _field(line)
        matches = lookup.get(_key(line.text), []) if line.heading else []
        if matches:
            current = None
            orphan_heading = None
            if len(matches) != 1:
                _issue(issues, "ambiguous_municipality_heading", line=line.index, detail=line.text)
                continue
            current = {"city": matches[0], "lines": [], "line": line.index}
            blocks.append(current)
            continue
        pending_value = bool(current and current["lines"] and
                             _field(current["lines"][-1]) and
                             _field(current["lines"][-1])[1] == "" and
                             (line.block_key == current["lines"][-1].block_key or
                              line.block_tag == "dd"))
        if line.heading and not found and not _days(line.text) and not pending_value:
            current = None
            orphan_heading, orphan_reported = line, False
            continue
        if current is not None:
            current["lines"].append(line)
        elif found and found[0] != "info" and orphan_heading and not orphan_reported:
            _issue(issues, "unknown_municipality_heading", line=orphan_heading.index,
                   detail=orphan_heading.text)
            orphan_reported = True
    for block in blocks:
        rows.extend(_block_rows(block, contract, source_url, updated, issues))
        if len(rows) > MAX_ROWS:
            raise ValueError("Publisher page exceeds row bounds")
    identities = Counter(row["source_row_id"] for row in rows)
    city_days = defaultdict(list)
    for row in rows:
        city_days[(*_city_key(row), row["weekday"], row["market_kind"])].append(row)
    for row in rows:
        if identities[row["source_row_id"]] > 1:
            row["identity_unique"] = False
            row["issues"].append("duplicate_source_identity")
        cohort = city_days[(*_city_key(row), row["weekday"], row["market_kind"])]
        if len(cohort) > 1 or row["sedi_alternative"]:
            row["comune_giorno_univoco"] = False
            row["issues"].append("multiple_venues_in_municipality_day")
        row["issues"] = sorted(set(row["issues"]))
    for count, minimum, maximum, code in (
            (len(rows), contract.get("min_rows", 1), contract.get("max_rows", MAX_ROWS), "row_count_outside_contract"),
            (len(blocks), contract.get("min_city_blocks", 1), contract.get("max_city_blocks", MAX_ROWS), "city_count_outside_contract")):
        if not minimum <= count <= maximum:
            _issue(issues, code)
    result["metrics"] = {
        "content_scopes": 1, "city_blocks": len(blocks), "rows": len(rows),
        "unique_source_row_ids": len(identities),
        "ambiguous_source_identities": sum(count > 1 for count in identities.values()),
        "ambiguous_municipality_days": sum(
            len(cohort) > 1 or any(r["sedi_alternative"] for r in cohort) for cohort in city_days.values()),
        "fraction_rows": sum(bool(row["localita"]) for row in rows),
        "rows_with_numeric_hours": sum(bool(row["orari"]) for row in rows),
    }
    result["complete"] = not any(issue["severity"] == "error" for issue in issues)
    return result
