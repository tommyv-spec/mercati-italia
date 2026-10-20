"""Bounded Happings local guides with explicit current/historical sections.

The new container is not an authorization to refresh its whole contents.
Only a section explicitly described as current can supply ordinary weekly
rows. Historical/unconfirmed rows remain in the inventory and in ambiguity
checks, with assignment and forecasting held. Exact clocks are source facts;
the weekly address engine does not acquire permission to write hours here.
"""
from __future__ import annotations

import re
from types import SimpleNamespace

from happings_detail_layout import _Document, _Node, _classes, _walk, _text
from happings_weekly_layout import (fold, _weekday_heading, _source_row,
                                    RAW_ITEM, WEEKDAYS, MAX_PUBLISHER_ITEMS)

BODY_SELECTOR = "main#main article.hpe-editorial--local-guide .hpe-editorial-grid > .hpe-editorial-body"
MAX_SECTIONS = 40
MAX_STATEMENT = 1200
MAX_PARAGRAPH = 4000
IGNORE_TAGS = frozenset({"aside", "nav", "footer", "script", "style", "template", "noscript"})
HISTORICAL = re.compile(r"\b(?:storic[oaie]|archivio|elenco precedente)\b")
UNCERTAIN = re.compile(r"\b(?:da verificare|da confermare|da riconfermare|da aggiornare|"
                       r"non (?:sono |e |risultano |state |stati |ancora |tutte |tutti |"
                       r"interamente |stato |stata |stanno )*(?:ri)?confermat[oaie]|"
                       r"non (?:sono |e |state |stati |ancora |tutte |tutti )*"
                       r"(?:verificat[oaie]|aggiornat[oaie]))\b")
CURRENT_HEADING = re.compile(
    r"(?:(?P<city>.+) citta )?(?:sedi e giorni|sedi giorni e orari|mercati settimanali) "
    r"(?:aggiornati|attuali)")
DAY_PATTERN = r"(?:luned[iì]|marted[iì]|mercoled[iì]|gioved[iì]|venerd[iì]|sabato|domenica)"
DAYS_PATTERN = DAY_PATTERN + r"(?:(?:\s*,\s*(?:(?:e\s+)?il\s+)?|\s+e\s+(?:il\s+)?)" + DAY_PATTERN + r")*"
CLOCK_PATTERN = r"(?:[01]?\d|2[0-3])(?::[0-5]\d)?"
NARRATIVE = re.compile(
    r"Il mercato settimanale (?:di|ad?) (?P<city>.{2,120}?) si svolge (?:ad?|in) "
    r"(?P<place>.{3,240}?) il (?P<days>" + DAYS_PATTERN + r"),\s*"
    r"(?P<hours>dalle (?P<start>" + CLOCK_PATTERN + r") alle (?P<end>" + CLOCK_PATTERN + r"))", re.I)
APPOINTMENT = re.compile(
    r"Ad? (?P<city>.{2,120}?) l[’']appuntamento [èe] il (?P<days>" + DAYS_PATTERN + r") "
    r"in (?P<place>.{3,240}?),\s*"
    r"(?P<hours>dalle (?P<start>" + CLOCK_PATTERN + r") alle (?P<end>" + CLOCK_PATTERN + r"))", re.I)
MARKET_FACT = re.compile(DAY_PATTERN + r"|\b\d{1,2}:\d{2}\b|\bdalle?\s+\d", re.I)
REPLACEMENT = re.compile(r"Queste indicazioni sostituiscono i vecchi riferimenti\b.{1,900}", re.I)


def _children(node):
    return [child for child in node.children if isinstance(child, _Node)
            and child.tag not in IGNORE_TAGS]


def _visible_walk(node):
    if node.tag in IGNORE_TAGS:
        return
    yield node
    for child in _children(node):
        yield from _visible_walk(child)


def _body(raw, source_province):
    tree = _Document()
    tree.feed(raw.decode("utf-8-sig", "replace"))
    tree.close()
    mains = [node for node in _visible_walk(tree.root) if node.tag == "main"
             and node.attrs.get("id") == "main" and "hpe-editorial-main" in _classes(node)]
    articles = [node for main in mains for node in _visible_walk(main)
                if node.tag == "article" and "hpe-editorial--local-guide" in _classes(node)]
    if not articles:
        return None
    if len(mains) != 1 or len(articles) != 1:
        raise ValueError("Publisher editorial guide has repeated main content")
    article = articles[0]
    if any(frame is article or "hpe-editorial-body" in _classes(frame) for frame in tree.stack):
        raise ValueError("Publisher editorial guide is incomplete")
    if any("happings-seo-content" in _classes(node) for node in _visible_walk(tree.root)):
        raise ValueError("Publisher mixes two weekly layouts without reviewed scope")
    headers = [child for child in _children(article)
               if child.tag == "header" and "hpe-editorial-hero" in _classes(child)]
    titles = [node for header in headers for node in _visible_walk(header) if node.tag == "h1"]
    if len(titles) != 1:
        raise ValueError("Publisher editorial province heading is missing or repeated")
    title = re.fullmatch(r"mercati settimanali (?:a|ad) (.+) e provincia", fold(_text(titles[0])))
    if title is None or title[1] != fold(source_province):
        raise ValueError("Publisher editorial heading crossed or failed province scope")
    grids = [child for child in _children(article) if "hpe-editorial-grid" in _classes(child)]
    bodies = [child for grid in grids for child in _children(grid)
              if child.tag == "div" and "hpe-editorial-body" in _classes(child)]
    if len(grids) != 1 or len(bodies) != 1:
        raise ValueError("Publisher editorial body is missing or repeated")
    return bodies[0]


def _scope(heading, nodes):
    key = fold(heading)
    current = CURRENT_HEADING.fullmatch(key)
    if HISTORICAL.search(key):
        status, reason = "historical_unverified", "historical_source_section"
    elif UNCERTAIN.search(key):
        status, reason = "unverified", "unverified_source_section"
    elif current:
        status, reason = "current", "explicit_updated_section"
    else:
        status, reason = "unverified", "source_section_scope_not_proven"
    notices = []
    # A later disclaimer qualifies the entire same section, including text
    # before it. Reading order must not make the first venue falsely current.
    for _, node in nodes:
        if node.tag != "p":
            continue
        text = _text(node)
        if UNCERTAIN.search(fold(text)) or re.search(r"\belenco (?:storico|precedente)\b", fold(text)):
            notices.append(text[:MAX_PARAGRAPH])
    if notices and status == "current":
        status, reason = "unverified", "unverified_source_section"
    return {"status": status, "reason": reason, "heading": heading,
            "notices": notices, "heading_city": current["city"] if current else None}


def _clock(value):
    bits = value.split(":")
    return f"{int(bits[0]):02d}:{int(bits[1]) if len(bits) == 2 else 0:02d}"


def source_inventory(raw, *, source_province):
    """Read original bounded units for extraction and independent diagnostics.

    This never consults parser.rows or saved market values. Unknown current
    market prose holds its whole section instead of making another row unique.
    The source text remains available for replay; only bounded scope summaries
    enter the ordinary public automation report.
    """
    body = _body(raw, source_province)
    if body is None:
        return None
    sections = []
    active = None
    for ordinal, node in enumerate(_children(body), 1):
        if node.tag in {"h1", "h2"}:
            active = {"heading": _text(node), "nodes": [], "ordinal": ordinal}
            sections.append(active)
            if len(sections) > MAX_SECTIONS:
                raise ValueError("Publisher editorial guide exceeds section bound")
        elif active is not None:
            active["nodes"].append((ordinal, node))
        elif MARKET_FACT.search(_text(node)):
            raise ValueError("Publisher editorial market facts lack a section scope")
    units, summaries, headings = [], [], []
    for section in sections:
        scope = _scope(section["heading"], section["nodes"])
        rows = []
        weekday = None
        unparsed = 0
        for ordinal, node in section["nodes"]:
            selector = BODY_SELECTOR + f" > {node.tag}:nth-child({ordinal})"
            text = _text(node)
            if len(text) > MAX_PARAGRAPH and node.tag != "ul":
                raise ValueError("Publisher editorial statement exceeds bound")
            if node.tag.startswith("h") and node.tag[1:] in {"1", "2", "3", "4", "5", "6"}:
                weekday = _weekday_heading(text) if node.tag == "h3" else None
                if weekday is not None:
                    province = re.search(r"\bnei comuni di (.+)$", fold(text))
                    if province and province[1] != fold(source_province):
                        raise ValueError("Publisher editorial weekday heading crossed province")
                    headings.append(weekday)
                elif re.match(r"mercati (?:del|della)\b", fold(text)):
                    raise ValueError("Publisher editorial weekday heading is unreviewed")
            elif node.tag in {"ul", "ol"} and weekday is not None:
                if node.tag != "ul":
                    raise ValueError("Publisher editorial weekday list changed structure")
                children = _children(node)
                if not children or any(child.tag != "li" for child in children):
                    raise ValueError("Publisher editorial weekday list changed structure")
                for index, child in enumerate(children, 1):
                    value = _text(child)
                    match = RAW_ITEM.fullmatch(value)
                    if (not match or len(value) > MAX_STATEMENT or any(
                            desc is not child and desc.tag in {"li", "ul", "ol", "h1", "h2", "h3"}
                            for desc in _visible_walk(child))):
                        raise ValueError("Publisher editorial weekday item is unparsed")
                    rows.append({"city": match[1], "place": match[2], "weekday": weekday,
                                 "selector": selector + f" > li:nth-child({index})", "text": value,
                                 "clock_hours": None, "hours_text": "", "replacement_notice": "",
                                 "paragraph_text": value})
            elif node.tag == "p":
                # Sentences stay independently scoped. In particular a named
                # old location in a replacement notice is never a new venue.
                sentences = [part.strip().rstrip(".; ") for part in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-ÖØ-Þ])", text)]
                replacement = [part for part in sentences if REPLACEMENT.fullmatch(part)]
                for sentence in sentences:
                    if not sentence:
                        continue
                    primary = NARRATIVE.fullmatch(sentence)
                    match = primary or APPOINTMENT.fullmatch(sentence)
                    if match:
                        start, end = _clock(match["start"]), _clock(match["end"])
                        if (start >= end or len(sentence) > MAX_STATEMENT
                                or primary and scope["heading_city"]
                                and fold(match["city"]) != scope["heading_city"]
                                or re.search(r",|\b(?:ad?|oppure|presso|nel comune di)\b|\be in\b",
                                             match["place"], re.I)):
                            unparsed += 1
                            continue
                        days = [WEEKDAYS.index(fold(value)) for value in re.findall(DAY_PATTERN, match["days"], re.I)]
                        if len(set(days)) != len(days):
                            unparsed += 1
                            continue
                        for day in days:
                            rows.append({"city": match["city"], "place": match["place"], "weekday": day,
                                         "selector": selector, "text": sentence,
                                         "clock_hours": {"start_time": start, "end_time": end},
                                         "hours_text": match["hours"],
                                         "paragraph_text": text,
                                         "replacement_notice": replacement[0] if len(replacement) == 1 else ""})
                    elif MARKET_FACT.search(sentence) and not UNCERTAIN.search(fold(sentence)):
                        unparsed += 1
            elif MARKET_FACT.search(text):
                # A second venue in an unreviewed ul/ol is no less a
                # competitor than the same sentence in a paragraph.
                unparsed += 1
        if unparsed and scope["status"] == "current":
            scope = {**scope, "status": "unverified", "reason": "current_editorial_section_incomplete"}
        for row in rows:
            row["editorial_scope"] = scope
        units.extend(rows)
        if len(units) > MAX_PUBLISHER_ITEMS:
            raise ValueError("Publisher editorial guide exceeds source-row bound")
        if rows or unparsed:
            summaries.append({"selector": BODY_SELECTOR + f" > h2:nth-child({section['ordinal']})",
                              "status": scope["status"], "reason": scope["reason"],
                              "source_rows": len(rows), "unparsed_statements": unparsed,
                              "rows_with_exact_source_hours": sum(bool(row["clock_hours"]) for row in rows)})
    if not units:
        raise ValueError("Publisher editorial guide has no reviewed weekly facts")
    return {"units": units, "sections": summaries, "weekday_headings": headings}


def parse_editorial(raw, *, source_province):
    inventory = source_inventory(raw, source_province=source_province)
    if inventory is None:
        return None
    rows = []
    for unit in inventory["units"]:
        row = _source_row(unit["city"], unit["place"], unit["weekday"])
        scope = unit["editorial_scope"]
        row["editorial_scope"] = scope
        row["source_evidence"] = {key: unit[key] for key in (
            "selector", "text", "paragraph_text", "replacement_notice")}
        row["clock_hours"] = unit["clock_hours"]
        row["hours_text"] = unit["hours_text"]
        if scope["status"] != "current":
            qualifiers = list((row.get("calendar_scope") or {}).get("qualifiers", []))
            qualifiers.append({"field": "section", "text": scope["heading"], "reason": scope["reason"]})
            row["calendar_scope"] = {"status": "unrepresented", "qualifiers": qualifiers,
                                     "forecast_allowed": False, "assignment_allowed": False}
            row["has_specific_location"] = False
        rows.append(row)
    return SimpleNamespace(rows=rows, weekday_headings=inventory["weekday_headings"],
                           seo_blocks=0, editorial_sections=inventory["sections"],
                           layout="editorial_provincial_weekly_guide", page_metadata=None)
