"""trentino.com market calendar (APT tourist boards and Comuni) as market rows.

Owner decision 2026-10-27: read it like eventiesagre/cosedicasa ("expand");
robots.txt allows the two paths read here (never /api/ or /map/).

One read = every page of the calendar search for topic 15 ("Fiere, mercati e
shopping") over a window around the read day (plain GET, the filter is
base64 "tpc:15;d:<from>,<to>"; 15 results on page 1, then 30), then the page
of each event whose title names a market. An event page lists EVERY date of
its series as schema.org microdata (data-date, "Inizio: 07:15", "Fine: 14:00")
plus the place ("Trento") and address ("Trento, centro storico"). The read is
kept as one compact JSON snapshot (no HTML); rows come from the same weekly /
seasonal row builder as the Open Data Hub events (opendatahub_events.market_rows).

Town: the address starts with the comune ("Castel Ivano, Strigno, nel paese");
the event's place may be a frazione and stays in the street. Wordings that name
no street ("nel paese", "in centro", "centro storico") become "centro".
Content date: the newest listed market date on or before the read day, and
only while the calendar still lists a later one (it covers the read day).
"""
from __future__ import annotations

import base64
import html
import json
import re
import unicodedata
from datetime import date, timedelta

from opendatahub_events import COLUMNS, market_rows

CONTAINER = "trentino_calendar_v1"
DATE_STRATEGY = "trentino_listed_dates_v1"
HOST = "www.trentino.com"
RESOURCE_URL = "https://www.trentino.com/it/manifestazioni/results/"
DETAIL_URL = "https://www.trentino.com/it/calendario/dettagli/{}/"
TOPIC = 15
MAX_PAGE_BYTES = 600_000
SLUG = re.compile(r"[a-z0-9][a-z0-9_-]{2,120}")
_HEADING = re.compile(r"(\d+) Manifestazion[ei]\s*\((\d+) - (\d+)\)")
_ITEM = re.compile(r'<li class="ui-cell e\d+" data-id="\d+">(.*?)</li>', re.S)
_ITEM_LINK = re.compile(r'href="/it/calendario/dettagli/([^/"#?]+)/#\d{4}-\d{2}-\d{2}"')
_ITEM_NAME = re.compile(r'itemprop="name" content="([^"]*)"')
_TITLE = re.compile(r"<h1[^>]*>(.*?)</h1>", re.S)
_LOCATION = re.compile(r'<div id="event-location">\s*<meta itemprop="name" content="([^"]*)"\s*/?>'
                       r'\s*<meta itemprop="address" content="([^"]*)"')
_COUNT = re.compile(r"<strong>(\d+) appuntament[oi]</strong>")
_DATE_DIV = re.compile(r'<div itemscope itemtype="http://schema.org/Event"[^>]*class="date"[^>]*>')
_ATTR = re.compile(r'(data-date|data-time-start|data-time-end)="([^"]*)"')
_CLOCK = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d")
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
# Places, not streets: "nel paese", "in centro paese", "per le vie del paese"
# (a street after a dash is kept: "in centro paese - Corso Dante").
_VAGUE = re.compile(r"(?:in |nel |per le vie del )?(?:centro(?: storico| paese| del paese)?|paese)"
                    r"(?:\s+[-–]\s+(.+))?", re.I)
_IN_STREET = re.compile(r"^(?:in|nel|nella)\s+(?=(?:via|viale|piazza|piazzale|p\.zza|corso|largo|vicolo)\b)",
                        re.I)


def _key(value):
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return " ".join(text.casefold().split())


def validate_profile(profile):
    """The reviewed search: topic 15, a bounded window and page budget, the shared row mapping."""
    window = (profile.get("search_days_before_read"), profile.get("search_days_after_read"))
    if (profile.get("format") != "JSON" or profile.get("resource_url") != RESOURCE_URL
            or any(type(days) is not int or not 0 <= days <= 60 for days in window)
            or sum(window) < 14
            or any(type(profile.get(k)) is not int or not 1 <= profile[k] <= 120
                   for k in ("max_search_pages", "max_event_pages"))
            or profile.get("schema_columns") != list(COLUMNS)
            or profile.get("municipality_field") != "comune"
            or profile.get("source_date_strategy") != DATE_STRATEGY):
        raise ValueError("Unreviewed trentino.com calendar search or row mapping")


def _window(profile, read_on):
    day = date.fromisoformat(read_on)
    return (day - timedelta(days=profile["search_days_before_read"]),
            day + timedelta(days=profile["search_days_after_read"]))


def search_url(profile, read_on, page=1):
    first, last = _window(profile, read_on)
    sid = base64.b64encode(f"tpc:{TOPIC};d:{first},{last}".encode()).decode()
    return RESOURCE_URL + ("" if page == 1 else f"{page}/") + "?sid=" + sid


def request_url(profile, read_on):
    """First search page of the read: the URL the date proof names."""
    return search_url(profile, read_on)


def _text(body):
    try:
        return body.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("trentino.com page is not UTF-8") from exc


def search_page(page):
    """(total, first, last, [(slug, name)]) of one search result page."""
    heading = _HEADING.search(page)
    if not heading:
        raise ValueError("trentino.com changed its calendar search page")
    total, first, last = map(int, heading.groups())
    items = []
    for body in _ITEM.findall(page):
        link, name = _ITEM_LINK.search(body), _ITEM_NAME.search(body)
        if not link or not name or not SLUG.fullmatch(link.group(1)):
            raise ValueError("trentino.com changed its calendar search results")
        items.append((link.group(1), html.unescape(name.group(1)).strip()))
    if not 1 <= first <= last <= total or len(items) != last - first + 1:
        raise ValueError("Incomplete trentino.com calendar search page")
    return total, first, last, items


def event_page(slug, page):
    """One event: its title, place, address and every listed (day, start, end)."""
    title, location, count = _TITLE.search(page), _LOCATION.search(page), _COUNT.search(page)
    dates = []
    for tag in _DATE_DIV.findall(page):
        attrs = dict(_ATTR.findall(tag))
        day = attrs.get("data-date", "")
        begin = attrs.get("data-time-start", "").removeprefix("Inizio: ")
        end = attrs.get("data-time-end", "").removeprefix("Fine: ")
        if not _DAY.fullmatch(day):
            raise ValueError("trentino.com changed its event dates")
        dates.append([day, begin if _CLOCK.fullmatch(begin) else "", end if _CLOCK.fullmatch(end) else ""])
    if not title or not location or not count or int(count.group(1)) != len(dates):
        raise ValueError("trentino.com changed its event page (title, place or date list)")
    return {"slug": slug, "title": html.unescape(title.group(1)).strip(),
            "place": html.unescape(location.group(1)).strip(),
            "address": html.unescape(location.group(2)).strip(), "dates": dates}


def is_market(profile, title):
    """Only market events are opened; the contract's exclusions are skipped up front."""
    text = _key(title)
    return "mercat" in text and not any(
        _key(token) in text for token in profile.get("exclude_rows_containing", {}).get("denominazione", []))


def snapshot(profile, get, read_on):
    """Read every search page of the window, then each market's event page (get(url) -> bytes)."""
    found, page, seen = {}, 1, 0
    while True:
        if page > profile["max_search_pages"]:
            raise ValueError("trentino.com search exceeds the reviewed page budget")
        total, first, last, items = search_page(_text(get(search_url(profile, read_on, page))))
        if first != seen + 1:
            raise ValueError("trentino.com search pages skipped or repeated results")
        seen = last
        for slug, name in items:
            if is_market(profile, name):
                found.setdefault(slug, name)
        if last == total:
            break
        page += 1
    if len(found) > profile["max_event_pages"]:
        raise ValueError("trentino.com lists more market events than the reviewed budget")
    events = [event_page(slug, _text(get(DETAIL_URL.format(slug)))) for slug in sorted(found)]
    first, last = _window(profile, read_on)
    return json.dumps({"schema": 1, "read_on": read_on, "window": [first.isoformat(), last.isoformat()],
                       "events": events}, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _events(raw):
    if (not isinstance(raw, dict) or set(raw) != {"schema", "read_on", "window", "events"}
            or raw["schema"] != 1 or not isinstance(raw["read_on"], str) or not _DAY.fullmatch(raw["read_on"])
            or not isinstance(raw["events"], list)):
        raise ValueError("Invalid trentino.com calendar snapshot")
    for event in raw["events"]:
        if (not isinstance(event, dict) or set(event) != {"slug", "title", "place", "address", "dates"}
                or not all(isinstance(event[k], str) for k in ("slug", "title", "place", "address"))
                or not isinstance(event["dates"], list)
                or any(not isinstance(d, list) or len(d) != 3 or not _DAY.fullmatch(str(d[0]))
                       for d in event["dates"])):
            raise ValueError("Invalid trentino.com calendar event")
    return raw["events"]


def last_change(raw):
    """Content date: the newest listed market date on or before the read day."""
    read_on = raw.get("read_on") if isinstance(raw, dict) else None
    days = {d[0] for event in _events(raw) for d in event["dates"]}
    past = [day for day in days if day <= read_on]
    if not past or not any(day > read_on for day in days):
        raise ValueError("trentino.com calendar lists no market date around the read day")
    return max(past)


def street(rest):
    """The address after the comune: real streets kept, wordings that name none become "centro"."""
    parts = []
    for part in rest.split(", ") if rest else []:
        text = _IN_STREET.sub("", part.strip())
        vague = _VAGUE.fullmatch(text)
        if vague:
            text = vague.group(1) or "centro"
        parts.append(text)
    return ", ".join(parts)


def rows(raw, is_municipality):
    """Market rows (COLUMNS) of one snapshot; see the module docstring."""
    events = []
    for event in _events(raw):
        address, place = event["address"], event["place"]
        town, _, rest = address.partition(", ")
        if not is_municipality(town) and is_municipality(place):
            town, rest = place, address.removeprefix(place).removeprefix(", ")
        days = [(date.fromisoformat(day), begin, end) for day, begin, end in event["dates"]]
        events.append((event["title"], town, street(rest), "", days))
    return market_rows(events)
