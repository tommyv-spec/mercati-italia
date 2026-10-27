"""Open Data Hub (Alto Adige / Südtirol) tourism events as market rows.

The reviewed query (/v1/Event, Source "lts") returns one item per event with
every date it is held on. A market is an event whose Italian title names a
market ("mercat"; the German "markt" only when no Italian title exists).
Each event is turned into one row per weekday it is held on:

- weekly ("annuale" / "stagionale"): at least MIN_WEEKLY_DATES distinct dates
  on that weekday, on at least MIN_WEEKLY_SHARE of the weeks between its first
  and last date (the real data splits cleanly: weekly markets >= 0.87, the
  rest <= 0.64). "annuale" when those dates fall in all 12 months;
  "stagionale" when their months form one continuous range, written in
  "mesi" as the forecast reader expects ("da marzo a ottobre"); any other
  month pattern is "stagionale_spezzata" (it may only fill other cards);
- "irregolare": a weekday held a few times but not weekly (Brennero's 34
  scattered Monday-Saturday dates, monthly flea markets). These rows are never
  markets themselves; they only compete in the town+weekday join.

Town: the event's own town when it is a comune (ODH files the Merano station
market under Lagundo), else the one comune named in it ("San Giacomo/Laives"),
else ODH's municipality ("Caldaro al Lago" and "Siusi" are frazioni).

LTS republishes a market each year as a new event: items with the same title,
municipality and street are one market (their dates are joined).
No request is made here and coordinates are never read.
"""
from __future__ import annotations

import re
import unicodedata
from collections import defaultdict
from datetime import date
from urllib.parse import parse_qs, urlsplit

CONTAINER = "opendatahub_event_v1"
DATE_STRATEGY = "opendatahub_last_change_v1"
HOST = "tourism.api.opendatahub.com"
PATH = "/v1/Event"
FIELDS = (
    "Id", "Source", "LicenseInfo.License", "LastChange",
    "Detail.it.Title", "Detail.de.Title",
    "ContactInfos.it.City", "ContactInfos.it.Address",
    "LocationInfo.MunicipalityInfo.Name.it",
    "EventDate.[*].From", "EventDate.[*].To", "EventDate.[*].Begin", "EventDate.[*].End",
)
COLUMNS = ("denominazione", "comune", "luogo", "giorni", "orario",
           "periodicita", "mesi", "dal", "al", "aggiornato")
WEEKDAYS = ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica")
MONTHS = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio",
          "agosto", "settembre", "ottobre", "novembre", "dicembre")
MIN_WEEKLY_DATES = 8
MIN_WEEKLY_SHARE = 0.8
MIN_COMPETING_DATES = 3
MAX_LOOKBACK_DAYS = 120
_ID = re.compile(r"[0-9A-Fa-f]{32}")
_DAY = re.compile(r"\d{4}-\d{2}-\d{2}")
_CLOCK = re.compile(r"(?:[01]\d|2[0-3]):[0-5]\d(?::00)?")


def _key(value):
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return " ".join(text.casefold().split())


def _list(value):
    return value if isinstance(value, list) else [] if value is None else [value]


def validate_profile(profile):
    """The reviewed query: the exact fields, a begin date set at read time, one page."""
    parts = urlsplit(profile.get("resource_url") or "")
    query = parse_qs(parts.query, keep_blank_values=True)
    days = profile.get("resource_begindate_days_before_read")
    if (profile.get("format") != "JSON" or parts.hostname != HOST or parts.path != PATH
            or set(query) != {"pagesize", "source", "begindate", "rawfilter", "fields"}
            or query["source"] != ["lts"] or query["begindate"] != ["{begindate}"]
            or query["fields"] != [",".join(FIELDS)]
            or query["pagesize"] != ["1000"]
            or type(days) is not int or not 0 <= days <= MAX_LOOKBACK_DAYS
            or profile.get("schema_columns") != list(COLUMNS)
            or profile.get("municipality_field") != "comune"
            or profile.get("source_date_strategy") != DATE_STRATEGY):
        raise ValueError("Unreviewed Open Data Hub event query or row mapping")


def request_url(profile, read_on):
    """The reviewed URL with its begin date: the read day minus the lookback."""
    day = date.fromisoformat(read_on).toordinal() - profile["resource_begindate_days_before_read"]
    return profile["resource_url"].replace("{begindate}", date.fromordinal(day).isoformat())


def _items(raw):
    if (not isinstance(raw, dict) or type(raw.get("TotalResults")) is not int
            or not isinstance(raw.get("Items"), list) or raw.get("TotalPages") not in (0, 1)
            or len(raw["Items"]) != raw["TotalResults"]):
        raise ValueError("Incomplete Open Data Hub event snapshot (more than one page)")
    for item in raw["Items"]:
        if not isinstance(item, dict) or set(item) != set(FIELDS):
            raise ValueError("Publisher changed Open Data Hub event fields")
        if not isinstance(item["Id"], str) or not _ID.fullmatch(item["Id"]):
            raise ValueError("Missing Open Data Hub event identity")
        if item["Source"] != "lts" or item["LicenseInfo.License"] != "CC0":
            raise ValueError("Open Data Hub event outside the reviewed CC0 LTS source")
    return raw["Items"]


def _title(item):
    italian = str(item["Detail.it.Title"] or "").strip()
    if italian:
        return italian if "mercat" in _key(italian) else ""
    german = str(item["Detail.de.Title"] or "").strip()
    return german if "markt" in _key(german) else ""


def _changed(item):
    value = str(item["LastChange"] or "")[:10]
    return value if _DAY.fullmatch(value) else ""


def last_change(raw):
    """Newest content change (LastChange) among the market events: the dataset date."""
    days = [_changed(item) for item in _items(raw) if _title(item)]
    if not any(days):
        raise ValueError("Open Data Hub snapshot has no dated market event")
    return max(days)


def season(months):
    """(periodicita, mesi) of a weekly market's months: one range or none."""
    if len(months) == 12:
        return "annuale", ""
    # One continuous (possibly year-crossing) range has exactly one first month.
    first = [m for m in months if (m - 2) % 12 + 1 not in months]
    last = [m for m in months if m % 12 + 1 not in months]
    if len(first) != 1 or len(last) != 1:
        return "stagionale_spezzata", ""
    return "stagionale", f"da {MONTHS[first[0] - 1]} a {MONTHS[last[0] - 1]}"


def rows(raw, is_municipality):
    """Market rows (COLUMNS) of one complete snapshot; see the module docstring."""
    groups = defaultdict(lambda: {"dates": set(), "hours": set(), "changed": "", "names": None})
    for item in _items(raw):
        title = _title(item)
        if not title:
            continue
        city = str(item["ContactInfos.it.City"] or "").strip()
        # "San Giacomo/Laives", "Collalbo - Renon": the one part that is a comune.
        named = [part.strip() for part in re.split(r"/|\s[-–|]\s", city) if is_municipality(part.strip())]
        town = city if city and is_municipality(city) else named[0] if len(named) == 1 else str(
            item["LocationInfo.MunicipalityInfo.Name.it"] or city).strip()
        street = str(item["ContactInfos.it.Address"] or "").strip()
        dates = [_list(item["EventDate.[*]." + part]) for part in ("From", "To", "Begin", "End")]
        if len({len(values) for values in dates}) != 1:
            continue  # misaligned projection: these dates can't be read safely
        for start, end, begin, close in zip(*dates):
            if (not isinstance(start, str) or not isinstance(end, str)
                    or start[:10] != end[:10] or not _DAY.fullmatch(start[:10])):
                continue  # a multi-day span is a festival period, not a market day
            day = date.fromisoformat(start[:10])
            group = groups[(_key(title), _key(town), _key(street), day.weekday())]
            group["dates"].add(day)
            group["hours"].add((str(begin or "")[:5], str(close or "")[:5])
                               if _CLOCK.fullmatch(str(begin or "")) and _CLOCK.fullmatch(str(close or ""))
                               else None)
            if _changed(item) >= group["changed"]:
                group["changed"], group["names"] = _changed(item), (title, town, street)
    result = []
    for (*_, weekday), group in groups.items():
        days = sorted(group["dates"])
        if len(days) < MIN_COMPETING_DATES:
            continue
        weeks = (days[-1] - days[0]).days // 7 + 1
        weekly = len(days) >= MIN_WEEKLY_DATES and len(days) >= MIN_WEEKLY_SHARE * weeks
        hours = next(iter(group["hours"])) if len(group["hours"]) == 1 else None
        title, town, street = group["names"]
        kind, months = season({d.month for d in days}) if weekly else ("irregolare", "")
        result.append({
            "denominazione": title, "comune": town, "luogo": street,
            "giorni": WEEKDAYS[weekday],
            "orario": f"{hours[0]} - {hours[1]}" if hours and hours[0] < hours[1]
                      and hours != ("00:00", "23:59") else "",
            "periodicita": kind, "mesi": months,
            "dal": days[0].isoformat(), "al": days[-1].isoformat(),
            "aggiornato": group["changed"],
        })
    return sorted(result, key=lambda row: (_key(row["comune"]), WEEKDAYS.index(row["giorni"]),
                                           _key(row["denominazione"]), _key(row["luogo"])))
