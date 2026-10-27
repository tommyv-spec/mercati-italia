#!/usr/bin/env python3
"""Rebuild EXPLICIT recurring schedules without claiming editions are confirmed.

Only source-bound recurring rules may generate *forecast* dates:
- "settimanale - lunedì", "Ogni sabato", etc. (complete weekday names only)
- "mensile - prima domenica del mese", "ogni terza domenica del mese"
- specific *last* weekday of the month.
A generic "settimanale", "mensile", truncated weekdays or isolated dates are
NOT sufficient evidence. Do not infer recurrence from page titles or locations.

The source must be relatively recent and attributable; canceled/archived and
date-quality "confermata"/"riportata" records are not altered. This transforms
a snapshot in memory and never contacts or modifies Firebase/Cloudflare.
An import or source-read timestamp does not date the publisher's content.
Unknown content age leaves existing predictions untouched and cannot create
or renew a projection or its provenance timestamp. Explicit seasonal,
interval or exception limits in the original identity still retire incompatible
predictions, even when the publisher's content date is unknown.
"""
from __future__ import annotations

import argparse
import calendar
import json
import re
import unicodedata
from collections import Counter
from datetime import date, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit

from source_freshness import as_day, source_date_evidence, source_url_domain
from source_calendar import refresh_source_calendar
from field_evidence import clean_receipts, MAX_READ_AGE, receipt_age_limit
from lombardia_calendar_scope import calendar_scope, filter_dates, within_bounds
from editorial_calendar_scope import apply_editorial_scope

WEEKDAYS = ("lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica")
DAYS_PATTERN = re.compile(r"\b(?:lunedi|martedi|mercoledi|giovedi|venerdi|sabato|domenica)\b")
# "quinta" counts only right before a weekday: "la quinta edizione" is not a week.
# A fifth weekday exists in some months only; the projection skips the others.
ORDINAL_PATTERN = re.compile(r"\b(?:prim[oa]|second[oa]|terz[oa]|quart[oa]|ultim[oa]|quint[oa](?=\s+(?:"
                             + "|".join(WEEKDAYS) + r")\b))\b")
ORDINAL_INDEX = {"primo": 1, "prima": 1, "secondo": 2, "seconda": 2,
                 "terzo": 3, "terza": 3, "quarto": 4, "quarta": 4,
                 "quinto": 5, "quinta": 5, "ultimo": -1, "ultima": -1}
# "4° domenica", "3a domenica", "2^ sabato" are the same ordinals in digits.
# ° and ^ always mark an ordinal ("2^ e 4^" stays two ordinals, never one).
NUMERIC_ORDINAL = re.compile(r"\b([1-5])\s*(?:°|\^|[ao](?=\s+(?:" + "|".join(WEEKDAYS) + r")\b))\s*")
# "Primi sabato e domenica del mese": the month's Nth Sunday and the Saturday before it
# (31 Oct + 1 Nov for November), as the publisher's own next dates show.
WEEKEND_PLURALS = {"primi": 1, "secondi": 2, "terzi": 3, "quarti": 4, "ultimi": -1}
MONTHLY_WEEKEND = re.compile(r"\b(" + "|".join(WEEKEND_PLURALS) + r") sabato e domenica del mese\b")
# "primo e terzo sabato del mese", "1^ e 3^ sabato" (read as "prima e terza sabato"):
# several weeks of the month, written next to each other before ONE weekday.
_ORDINAL_WORD = r"(?:prim[oa]|second[oa]|terz[oa]|quart[oa]|ultim[oa]|quint[oa])"
JOINED_ORDINALS = re.compile(r"\b" + _ORDINAL_WORD + r"(?:\s*(?:,|\be\b)\s*" + _ORDINAL_WORD +
                             r")+\s+(?:" + "|".join(WEEKDAYS) + r")\b")
EVERY_WEEKDAY = re.compile(r"tutti i (?:" + "|".join(WEEKDAYS) + r")(?:\s*(?:,|\be\b)\s*(?:" +
                           "|".join(WEEKDAYS) + r"))*")
# "Mercoledì tutto l'anno": the weekday(s) every week of the year.
ALL_YEAR_WEEKDAYS = re.compile(r"(?:" + "|".join(WEEKDAYS) + r")(?:\s*(?:,|\be\b)\s*(?:" +
                               "|".join(WEEKDAYS) + r"))* tutto l\W?anno")

MAX_LOOKAHEAD_DAYS = 120
MAX_SOURCE_STALE_DAYS = 540
DEFAULT_INDEX_DATES = 16

MONTH_NAMES = ("gennaio|febbraio|marzo|aprile|maggio|giugno|luglio|agosto|"
               "settembre|ottobre|novembre|dicembre")
MONTH_NUMBERS = {name: i for i, name in enumerate(MONTH_NAMES.split("|"), 1)}
COMPLETE_MONTH_RANGE = re.compile(
    r"(?P<recurrence>.+?)(?:,\s*|\s+)da (?P<first>" + MONTH_NAMES +
    r") a (?P<last>" + MONTH_NAMES + r")"
)
NAMED_MONTH_RANGE = re.compile(r"da (" + MONTH_NAMES + r") a (" + MONTH_NAMES + r")")
_MONTH_LIST = r"(?:" + MONTH_NAMES + r")(?:\s*(?:,|\be\b|\bed\b)\s*(?:" + MONTH_NAMES + r"))*"
# "<rule> escluso agosto", "<rule> (esclusi i mesi di luglio e agosto)", "<rule> - ad
# esclusione del mese di agosto", "<rule> tranne luglio ed agosto": the rule in every
# other month. Anything after the months (a year, "a dicembre si svolge ...") fails.
COMPLETE_MONTH_EXCLUSION = re.compile(
    r"(?P<recurrence>.+?)\s*(?:,|-|\()?\s*"
    r"(?:esclus[oaie]|tranne|eccetto|(?:ad|con) esclusione|ad eccezione)"
    r"(?: (?:di|del|dei|delle))?(?: (?:i|il|la|le))?(?: mes[ei])?(?: di)? "
    r"(?P<months>" + _MONTH_LIST + r")\s*\)?\.?"
)
FULL_WEEKLY_RECURRENCE = re.compile(
    r"(?:settimanale(?:\s*[-:]\s*|\s+)|ogni\s+)(?:" + "|".join(WEEKDAYS) +
    r")(?:\s*(?:,|\be\b)\s*(?:" + "|".join(WEEKDAYS) + r"))*"
)
FULL_MONTHLY_RECURRENCE = re.compile(
    r"(?:(?:mensile(?:\s*[-:]\s*|\s+))|ogni\s+)?(?:(?:" +
    "|".join(ORDINAL_INDEX) + r") (?:" + "|".join(WEEKDAYS) + r") (?:del|al|di ogni) mese"
    r"|(?:" + "|".join(WEEKEND_PLURALS) + r") sabato e domenica del mese)"
)
SEASONAL_SCOPE = re.compile(
    r"\b(?:estiv[oaie]|invernal[ei]|primaveril[ei]|autunnal[ei]|stagional[ei])\b"
    r"|\b(?:in|d|durante l|durante la) (?:estate|inverno|primavera|autunno)\b"
    r"|\b(?:durante(?: la)?|nella|per la) stagione\b"
)
INTERVAL_SCOPE = re.compile(
    r"\b(?:quindicinal[ei]|bisettimanal[ei]|bimestral[ei]|trimestral[ei]|"
    r"semestral[ei]|alternat[oaie])\b|\bsettimane alterne\b"
    r"|\buna volta (?:l anno|all anno|ogni anno)\b"
    r"|\b(?:cadenza|frequenza) annuale\b"
)
INTERVAL_WORDS = {"uno": 1, "una": 1, "due": 2, "tre": 3, "quattro": 4,
                  "cinque": 5, "sei": 6, "sette": 7, "otto": 8, "nove": 9,
                  "dieci": 10, "quattordici": 14, "quindici": 15}
COUNTED_INTERVAL = re.compile(
    r"\b(?:ogni|una volta ogni) (\d{1,3}|" + "|".join(INTERVAL_WORDS) +
    r")\s*(gg|giorni?|settimane?|mesi|mese|anni|anno)\b"
)
CALENDAR_EXCEPTION_SCOPE = re.compile(
    r"\b(?:sospes[oaie]|annullat[oaie])\b|\bnon si svolge\b"
    r"|\bmercato (?:temporaneamente )?chiuso\b"
    r"|\b(?:tranne|eccetto|esclus[oaie]|salvo|ad eccezione|(?:ad|con) esclusione) "
    r"(?:(?:i|il|la|le|gli|dei|del|della|giorni|mese|mesi|di|\d{1,2}) ){0,3}"
    r"(?:festiv[oi]|festivita|natale|pasqua|capodanno|ferragosto|" +
    "|".join(WEEKDAYS) + "|" + MONTH_NAMES + r")\b"
    r"|\bchius[oaie] (?:in|a|nel mese di) (?:" + MONTH_NAMES +
    r"|natale|pasqua|capodanno|ferragosto)\b"
)
DATE_SCOPE_ATOM = (r"(?:\d{1,4}(?: \d{1,4}){0,2}(?: (?:" + MONTH_NAMES +
                   r")(?: \d{4})?)?|(?:" + MONTH_NAMES + r")(?: \d{4})?)")
DATE_RANGE_SCOPE = re.compile(
    r"\b(?:da|dal|dall) " + DATE_SCOPE_ATOM + r" (?:fino )?(?:a|al|all) " +
    DATE_SCOPE_ATOM + r"\b|\b(?:solo|soltanto|esclusivamente) (?:nel mese di |a |in )?"
    r"(?:" + MONTH_NAMES + r")\b"
)
NUMERIC_DATE_RANGE_SCOPE = re.compile(
    r"\b(?:da|dal|dall)\s+\d{1,2}\s*/\s*\d{1,2}"
    r"(?:\s*/\s*\d{2,4})?\s+(?:fino\s+)?(?:a|al|all)\s+"
    r"\d{1,2}\s*/\s*\d{1,2}(?:\s*/\s*\d{2,4})?\b"
)
DATE_RANGE_CONTEXT = re.compile(r"\b(?:" + MONTH_NAMES + r"|(?:19|20)\d{2})\b")
STREET_PREFIX = re.compile(
    r"\b(?:via|viale|viali|piazza|piazzale|piazzetta|corso|largo|passeggiata|"
    r"lungomare|lungolago|giardino|giardini|parco|strada|vicolo)\b"
)
TEMPORAL_SCOPE_REASONS = frozenset({
    "seasonal_scope_unrepresented", "interval_scope_unrepresented",
    "calendar_exception_scope_unrepresented", "date_range_scope_unrepresented",
    "source_calendar_scope_unrepresented",
})


@lru_cache(maxsize=1)
def _builtin_forecast_source_limits() -> tuple[tuple[str, str, int], ...]:
    path = Path(__file__).resolve().parent / "data/market-source-contracts.json"
    return forecast_source_limits(json.loads(path.read_text("utf-8")))


def forecast_source_limits(config=None) -> tuple[tuple[str, str, int], ...]:
    """Return reviewed (ID prefix, exact attribution URL, age limit) scopes.

    The default registry is loaded and validated once per process. Callers
    already holding an exact reviewed configuration can pass it directly.
    Disabling a reader does not remove its existing markets' age constraint.
    This only restricts projections; it cannot authorize source publication.
    """
    if config is None:
        return _builtin_forecast_source_limits()
    # source_lifecycle imports our pure recurrence parser; defer its import
    # until both modules are initialized rather than introduce an import cycle.
    from source_lifecycle import MARKET_KINDS, validate_contracts

    validate_contracts(config)
    limits = {}
    for profile in config["raw_profiles"]:
        if (profile.get("publication_mode") != "approved_dev_only"
                or profile.get("legal_reuse_reviewed") is not True
                or profile.get("row_kind") not in MARKET_KINDS):
            continue
        prefix, url = profile["catalog_slug_prefix"], profile["attribution_url"]
        if not isinstance(prefix, str) or not prefix:
            raise ValueError("Forecast source contract needs a stable ID prefix")
        maximum = profile.get("max_forecast_source_age_days", profile["max_source_age_days"])
        scope = (prefix, url)
        limits[scope] = min(maximum, limits.get(scope, maximum))
    return tuple((prefix, url, maximum) for (prefix, url), maximum in sorted(limits.items()))


def _primary_source_age_limit(record, max_stale_days, source_limits):
    slug, url = record.get("slug"), record.get("url_fonte")
    maximum = max_stale_days
    if isinstance(slug, str):
        for prefix, source_url, limit in source_limits:
            if slug.startswith(prefix) and url == source_url:
                maximum = min(maximum, limit)
    return maximum


def text_key(value: Any) -> str:
    raw = unicodedata.normalize("NFKD", str(value or ""))
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", raw.casefold()).strip()


def parse_source_day(value: Any) -> date | None:
    """Parse date syntax only; attribution is checked by source_date_evidence."""
    return as_day(value)


def _spelled_ordinals(value: Any) -> str:
    return NUMERIC_ORDINAL.sub(lambda m: ("", "prima ", "seconda ", "terza ", "quarta ", "quinta ")[int(m[1])],
                               text_key(value))


def explicit_rule(value: Any) -> dict | None:
    text = _spelled_ordinals(value)
    days = [WEEKDAYS.index(day) for day in dict.fromkeys(DAYS_PATTERN.findall(text))]
    if not days:
        return None

    # Monthly rules must be parsed before weekly. "Ogni prima domenica del
    # mese" is NOT a weekly Sunday market.
    monthly = "mensil" in text or "del mese" in text or "al mese" in text or "ogni mese" in text
    if monthly:
        ordinals = [m.group(0) for m in ORDINAL_PATTERN.finditer(text)]
        weekend = MONTHLY_WEEKEND.findall(text)
        if len(weekend) == 1 and days == [5, 6] and not ordinals:
            return {"kind": "monthly_nth_weekday", "weekday": 6,
                    "ordinal": WEEKEND_PLURALS[weekend[0]], "day_offsets": [-1, 0]}
        if len(days) != 1 or not ordinals:
            return None
        if len(ordinals) == 1:
            return {"kind": "monthly_nth_weekday", "weekday": days[0],
                    "ordinal": ORDINAL_INDEX[ordinals[0]]}
        # Several weeks only when they are all written together before the day.
        joined = JOINED_ORDINALS.search(text)
        weeks = sorted({ORDINAL_INDEX[o] for o in ordinals}, key=lambda n: (n == -1, n))
        if not joined or len(ORDINAL_PATTERN.findall(joined.group(0))) != len(ordinals) \
                or len(weeks) != len(ordinals):
            return None
        return {"kind": "monthly_nth_weekday", "weekday": days[0], "ordinals": weeks}

    # An occurrence has to say *every* named weekday or declare a weekly
    # cadence. Avoid picking unrelated weekdays from prose descriptions.
    if not ("settimanale" in text or re.search(r"\bogni\b", text) or EVERY_WEEKDAY.fullmatch(text)
            or ALL_YEAR_WEEKDAYS.fullmatch(text)):
        return None
    if "bisettimanale" in text or "quindicinal" in text or "alternat" in text:
        return None
    if ORDINAL_PATTERN.search(text):
        return None
    return {"kind": "weekly", "weekdays": sorted(set(days))}


def complete_monthly_rule(value: Any) -> dict | None:
    """The rule of a text that states one monthly rule and nothing else.

    "Prima domenica del mese" / "Ogni 2a domenica del mese" -> its rule.
    "... ad esclusione di agosto" -> the rule in the other months (active_months).
    "... dei mesi giugno, luglio" or any other qualifier -> None: the rule cannot
    carry it, so it must not be dropped.
    """
    text = _spelled_ordinals(value)
    if FULL_MONTHLY_RECURRENCE.fullmatch(text):
        return explicit_rule(text)
    rule = _complete_month_rule(value)
    return rule if rule and rule["kind"] == "monthly_nth_weekday" else None


def month_scope_text(rule: dict) -> str:
    """", esclusi luglio e agosto" or ", da marzo a ottobre": a rule's months, as
    _complete_month_rule reads them back ("" when it runs every month)."""
    names = MONTH_NAMES.split("|")
    active = rule.get("active_months") or list(range(1, 13))
    out = [m for m in range(1, 13) if m not in active]
    if not out:
        return ""
    starts = [m for m in active if (m - 2) % 12 + 1 not in active]
    if len(out) > len(active) and len(starts) == 1:  # one season: say where it starts and ends
        last = next(m for m in active if m % 12 + 1 not in active)
        return ", da " + names[starts[0] - 1] + " a " + names[last - 1]
    out = [names[m - 1] for m in out]
    return ", " + ("escluso " + out[0] if len(out) == 1 else
                   "esclusi " + ", ".join(out[:-1]) + " e " + out[-1])


def calendar_key(rule: dict) -> tuple:
    """Calendar part of "same market": (kind, weekdays, ordinal); month masks aside."""
    # A weekend ("terzi sabato e domenica") contains its Sunday: the same market as a
    # listing that names only that Sunday, like a month mask is.
    return (rule["kind"], tuple(rule.get("weekdays") or [rule.get("weekday")]),
            tuple(rule["ordinals"]) if rule.get("ordinals") else rule.get("ordinal"))


def _month_numbers(first: str, last: str) -> list[int]:
    start, end = MONTH_NUMBERS[first], MONTH_NUMBERS[last]
    if start <= end:
        return list(range(start, end + 1))
    return list(range(1, end + 1)) + list(range(start, 13))


def _complete_month_rule(value: Any) -> dict | None:
    """Represent only an entire recurring rule plus named months, with no year.

    A year, day-of-month boundary, exception or other trailing prose cannot be
    silently discarded. Keep the general explicit_rule parser unchanged for
    readers that use its existing schema to recognize possible cohorts.
    """
    text = _spelled_ordinals(value)
    if match := COMPLETE_MONTH_RANGE.fullmatch(text):
        months = _month_numbers(match["first"], match["last"])
    elif ((match := COMPLETE_MONTH_EXCLUSION.fullmatch(text))
          and text.count("(") == text.count(")") <= 1):
        # Owner rule (2026-10-27): "escluso agosto" is the rule in the other months.
        excluded = {MONTH_NUMBERS[m] for m in re.findall(MONTH_NAMES, match["months"])}
        months = [m for m in range(1, 13) if m not in excluded]
    else:
        return None
    body = match["recurrence"]
    if not (FULL_WEEKLY_RECURRENCE.fullmatch(body)
            or FULL_MONTHLY_RECURRENCE.fullmatch(body)):
        return None
    rule = explicit_rule(body)
    if not rule or not months:
        return None
    return {**rule, "active_months": months}


def rule_core(rule: dict) -> dict:
    """The cadence itself, without a source's month or day/month limits."""
    return {k: v for k, v in rule.items()
            if k in ("kind", "weekdays", "weekday", "ordinal", "ordinals", "day_offsets")}


def forecast_rule(record: dict) -> dict | None:
    """Derive forecast scope from complete text, never a saved metadata flag."""
    scope = calendar_scope(record)
    if scope is not None:
        rule = scope.get("rule")
        declared = explicit_rule(record.get("ricorrenza_testo"))
        # Raw boundaries cannot authorize a cadence that contradicts the
        # normalized schedule or an unsupported week-of-month qualifier.
        if rule and (declared is None or declared == rule_core(rule)):
            return rule
        return None
    return (_complete_month_rule(record.get("ricorrenza_testo"))
            or explicit_rule(record.get("ricorrenza_testo")))


def temporal_scope_hold(record: dict) -> str | None:
    """Explain temporal limits which the current projection rules cannot express.

    The original identity can retain a limit lost from a normalized weekly
    label. Inspect whole words in those fields and only the URL path: a host,
    query parameter, address or a place name such as Primavera is not a
    seasonal claim. No source date or partial recurrence receipt can erase
    this limit; the engine needs an actually representable bounded rule.

    This pure helper is also used by field readers before attesting a complete
    recurrence. It does not infer weekdays, seasons or dates from an identity.
    """
    if not isinstance(record, dict):
        return None
    source_scope = calendar_scope(record)
    if source_scope and source_scope["state"] in {"invalid", "ambiguous"}:
        return "source_calendar_scope_unrepresented"
    if source_scope and source_scope.get("rule"):
        declared = explicit_rule(record.get("ricorrenza_testo"))
        if ((declared and declared != rule_core(source_scope["rule"]))
                or not declared and re.search(r"\bmensile\b", text_key(record.get("ricorrenza_testo")))):
            return "source_calendar_scope_unrepresented"
    represented_rule = (forecast_rule(record) if source_scope
                        else _complete_month_rule(record.get("ricorrenza_testo")))
    represented_months = (represented_rule or {}).get("active_months")
    previous_rule = record.get("proiezione_regola")
    if (isinstance(previous_rule, dict) and "source_day_month_bounds" in previous_rule
            and (not source_scope or not source_scope.get("bounds"))):
        return "date_range_scope_unrepresented"
    if (isinstance(previous_rule, dict) and "active_months" in previous_rule
            and (not represented_rule or previous_rule != represented_rule
                 or not isinstance(previous_rule["active_months"], list)
                 or any(type(month) is not int for month in previous_rule["active_months"]))):
        # An old or self-declared month mask is not source evidence and must
        # not authorize a different cadence, season or an unbounded forecast.
        return "date_range_scope_unrepresented"
    def words(value):
        return " ".join(re.findall(r"[a-z0-9]+", text_key(value)))

    # A source title/slug can contain a real place: San Salvo + giovedì is
    # not "except Thursday", and Passeggiata d'Inverno is a street name.
    # Remove only complete declared place phrases from identity fields.
    # Calendar prose keeps its meaning, even if it mentions a similar word.
    city = words(record.get("citta"))
    # A malformed saved city such as "Riolo Terme (estivo)" is not an
    # unqualified place phrase: masking it would hide the very lost limit.
    places = set()
    if (not re.search(r"[()\[\]]", str(record.get("citta") or ""))
            and not SEASONAL_SCOPE.search(city) and not INTERVAL_SCOPE.search(city)
            and not COUNTED_INTERVAL.search(city)):
        places.add(city)
    street = words(record.get("indirizzo"))
    street_match = STREET_PREFIX.search(street)
    if street_match:
        places.add(street[street_match.start():])
    place_patterns = [re.compile(r"\b" + re.escape(place) + r"\b")
                      for place in sorted(places, key=len, reverse=True) if place]
    values = [(record.get(field), field in {"ricorrenza_testo", "ricorrenza_originale"})
              for field in ("ricorrenza_testo", "ricorrenza_originale", "nome", "nome_originale", "slug")]
    if source_scope:
        values.append((source_scope["identity"].get("ubicazione"), False))
    try:
        values.append((unquote(urlsplit(str(record.get("url_fonte") or "")).path), False))
    except ValueError:
        pass
    for value, calendar_prose in values:
        if not isinstance(value, str) or not value:
            continue
        text = words(value)
        if not calendar_prose:
            for pattern in place_patterns:
                text = pattern.sub(" ", text)
            text = " ".join(text.split())
        seasonal_terms = SEASONAL_SCOPE.findall(text)
        if seasonal_terms:
            # A complete window represents a generic "stagionale" label.
            # Do not infer the calendar meaning of "invernale", "in estate"
            # or another additional seasonal condition from that window.
            if not (source_scope and source_scope.get("limited") and represented_rule
                    and all(term in {"stagionale", "stagionali"} for term in seasonal_terms)):
                return "seasonal_scope_unrepresented"
        interval_terms = [m.group(0) for m in INTERVAL_SCOPE.finditer(text)]
        # "quindicinale" is represented when the publisher names its weeks
        # ("1^ e 3^") and the rule was built from exactly those weeks.
        named_fortnight = bool(source_scope and represented_rule
                               and (source_scope.get("rule") or {}).get("kind") == "monthly_nth_weekday"
                               and represented_rule == source_scope["rule"])
        if interval_terms and not (named_fortnight and all(
                term.startswith("quindicinal") for term in interval_terms)):
            return "interval_scope_unrepresented"
        for match in COUNTED_INTERVAL.finditer(text):
            number, unit = match.groups()
            count = int(number) if number.isdigit() else INTERVAL_WORDS[number]
            rule = explicit_rule(record.get("ricorrenza_testo")) or {}
            weekly = rule.get("kind") == "weekly"
            # Only intervals already expressed by the full parsed rule are
            # compatible. In particular, fourteen/fifteen days is never weekly.
            compatible = (
                weekly and unit in {"giorno", "giorni", "gg"} and (
                    count == 7 and len(rule["weekdays"]) == 1
                    or count == 1 and rule["weekdays"] == list(range(7)))
                or weekly and unit in {"settimana", "settimane"} and count == 1
                or rule.get("kind") == "monthly_nth_weekday"
                and unit in {"mese", "mesi"} and count == 1
            )
            if not compatible:
                return "interval_scope_unrepresented"
        if CALENDAR_EXCEPTION_SCOPE.search(text) and not (
                # "escluso agosto" that the forecast rule itself carries.
                calendar_prose and represented_months
                and (_complete_month_rule(value) or {}).get("active_months") == represented_months):
            return "calendar_exception_scope_unrepresented"
        # Bare number ranges can be opening hours. Require a month/year or
        # explicit day/month slash notation; 08:00 and 8.30 can be hours.
        for match in DATE_RANGE_SCOPE.finditer(text):
            if not DATE_RANGE_CONTEXT.search(match.group(0)):
                continue
            months = NAMED_MONTH_RANGE.fullmatch(match.group(0))
            if not (months and represented_months == _month_numbers(months[1], months[2])):
                return "date_range_scope_unrepresented"
        for numeric_range in NUMERIC_DATE_RANGE_SCOPE.finditer(text_key(value)):
            stated = re.findall(r"\d{1,4}", numeric_range.group(0))
            observed = (re.findall(r"\d{1,4}", " ".join(source_scope.get("bounds") or []))
                        if source_scope else [])
            if not represented_rule or stated != observed:
                return "date_range_scope_unrepresented"
    return None


def project_dates(rule: dict, today: date, horizon_days: int) -> list[str]:
    if not 7 <= horizon_days <= 365:
        raise ValueError("Horizon must be between 7 and 365 days")
    end = today + timedelta(days=horizon_days)
    active_months = rule.get("active_months")
    bounds = rule.get("source_day_month_bounds")
    if bounds is not None:
        if not isinstance(bounds, list) or len(bounds) != 2:
            raise ValueError("Unrecognized source day/month scope")
        within_bounds(today, bounds)  # Validate before iterating.
    if active_months is not None and (
            not isinstance(active_months, list) or not active_months
            or any(type(month) is not int or not 1 <= month <= 12 for month in active_months)
            or active_months != sorted(set(active_months))):
        raise ValueError("Unrecognized active month scope")
    if rule["kind"] == "weekly":
        weekdays = set(rule["weekdays"])
        return [(today + timedelta(days=i)).isoformat()
                for i in range(horizon_days + 1)
                if (today + timedelta(days=i)).weekday() in weekdays
                and (active_months is None or (today + timedelta(days=i)).month in active_months)
                and (bounds is None or within_bounds(today + timedelta(days=i), bounds))]
    if rule["kind"] == "monthly_nth_weekday":
        results = []
        year, month = today.year, today.month
        for i in range(15):
            y, m = year + (month + i - 1) // 12, (month + i - 1) % 12 + 1
            candidates = [date(y, m, d)
                          for d in range(1, calendar.monthrange(y, m)[1] + 1)
                          if date(y, m, d).weekday() == rule["weekday"]]
            for ordinal in rule.get("ordinals") or [rule["ordinal"]]:
                if ordinal == -1:
                    candidate = candidates[-1]
                elif len(candidates) >= ordinal:
                    candidate = candidates[ordinal - 1]
                else:
                    continue
                # A weekend belongs to its Sunday's month, also for months and bounds.
                if (active_months is not None and candidate.month not in active_months
                        or bounds is not None and not within_bounds(candidate, bounds)):
                    continue
                for offset in rule.get("day_offsets") or [0]:
                    day = candidate + timedelta(days=offset)
                    if today <= day <= end:
                        results.append(day.isoformat())
            if date(y, m, 1) > end:
                break
        return sorted(set(results))  # "quarto e ultimo" can be one day
    raise ValueError("Unrecognized recurrence kind")


def _refresh_record_base(original: dict, today: date, horizon_days: int = MAX_LOOKAHEAD_DAYS,
                   max_stale_days: int = MAX_SOURCE_STALE_DAYS, *,
                   source_limits=None) -> tuple[dict, str]:
    record = dict(original)
    if record.get("status") in {"archiviato", "annullato"}:
        return record, "inactive"
    source_calendar = refresh_source_calendar(record, today=today)
    if source_calendar is not None:
        return source_calendar, "explicit_source_calendar_preserved"
    if record.get("calendario_fonte") is not None:
        # Corrupt or identity-mismatched explicit dates cannot authorize a
        # fallback recurrence. Export will separately reject the bad proof.
        return record, "invalid_source_calendar_held"
    if record.get("date_quality") in {"confermata", "riportata"}:
        return record, "non_projected_source_date"
    if record.get("date_quality") not in {None, "", "prevista", "sconosciuta"}:
        return record, "unrecognized_date_quality"
    from field_conflicts import delisted_weekday
    if not record.get("verificato_il") and delisted_weekday(record, today=today):
        # Its own complete weekly page now lists the town only on other days.
        if record.get("date_quality") == "prevista" or record.get("date"):
            record["date"] = []
            record["date_quality"] = "sconosciuta"
            record["proiezione_regola"] = None
            record["proiezione_generata_il"] = ""
            record["proiezione_fonte"] = ""
        return record, "source_lists_town_on_other_weekdays"

    source_scope = calendar_scope(record)
    scope_hold = temporal_scope_hold(record)
    if record.get("verificato_il") and (source_scope or scope_hold or _complete_month_rule(record.get("ricorrenza_testo"))):
        # A complete scope still does not authorize changing a human review.
        return record, "verified_temporal_scope_preserved"
    if scope_hold:
        if (record.get("date_quality") == "prevista" or source_scope and (
                record.get("date") or record.get("proiezione_regola")
                or record.get("proiezione_generata_il") or record.get("proiezione_fonte"))):
            record["date"] = []
            record["date_quality"] = "sconosciuta"
            record["proiezione_regola"] = None
            record["proiezione_generata_il"] = ""
            record["proiezione_fonte"] = ""
        return record, scope_hold

    filtered_existing_source_scope = False
    if source_scope:
        retained = filter_dates(record.get("date") or [], source_scope)
        if retained != (record.get("date") or []):
            record["date"] = retained
            filtered_existing_source_scope = True
        if filtered_existing_source_scope or not retained and any(record.get(key) for key in (
                "proiezione_regola", "proiezione_generata_il", "proiezione_fonte")):
            # Do not claim that an earlier unbounded projection used the new
            # evidence. A fresh source may rebuild provenance below.
            record["proiezione_regola"] = None
            record["proiezione_generata_il"] = ""
            record["proiezione_fonte"] = ""
            if not retained:
                record["date_quality"] = "sconosciuta"

    rule = forecast_rule(record)
    if not rule:
        return record, "no_explicit_rule"

    # A weekly label in the original stable ID must never silently
    # override a contradictory explicitly declared source schedule.
    # This holds ONLY projections: documented/reported editions were
    # already returned above, and the market identity is never removed.
    match = re.search(
        r"-(lunedi|martedi|mercoledi|giovedi|venerdi|sabato|domenica)$",
        str(record.get("slug") or "").casefold(),
    )
    if (match and rule["kind"] == "weekly"
            and WEEKDAYS.index(match.group(1)) not in rule["weekdays"]):
        if record.get("date_quality") == "prevista" and record.get("date"):
            record["date"] = []
            record["date_quality"] = "sconosciuta"
            record["proiezione_regola"] = None
            record["proiezione_generata_il"] = ""
            record["proiezione_fonte"] = ""
        return record, "contradictory_weekday_identity_held"

    filtered_existing_month_scope = False
    if (record.get("date_quality") == "prevista" and record.get("date")
            and rule.get("active_months")):
        allowed = rule["active_months"]
        retained = [day for day in record["date"] if date.fromisoformat(day).month in allowed]
        if retained != record["date"]:
            # A complete explicit limit can retire incompatible old estimates
            # without dating a source, adding appointments or renewing proof.
            record["date"] = retained
            filtered_existing_month_scope = True
            if not retained:
                record["date_quality"] = "sconosciuta"
                record["proiezione_regola"] = None
                record["proiezione_generata_il"] = ""
                record["proiezione_fonte"] = ""

    if source_url_domain(record.get("url_fonte")) is None:
        return record, "no_attributable_source"
    if source_limits is None:
        source_limits = forecast_source_limits()
    source_age_limit = _primary_source_age_limit(record, max_stale_days, source_limits)
    source_evidence = source_date_evidence(record)
    updated = parse_source_day(source_evidence["value"])
    projection_basis = "ricorrenza_testo"
    if updated is None or not 0 <= (today - updated).days <= source_age_limit:
        # A secondary publisher can support this exact recurrence without
        # relabeling the age of the original source. Only current, matching
        # field observations qualify; addresses/hours and fresh imports do not.
        listed = [r for r in clean_receipts(record.get("riscontri_campi"), record, today=today)
                  if r["valori"].get("ricorrenza_testo") == record.get("ricorrenza_testo")
                  and 0 <= (today - parse_source_day(r["letto_il"])).days <= MAX_READ_AGE]
        dates = [(parse_source_day(r.get("fonte_aggiornata_il")),
                  min(max_stale_days, receipt_age_limit(r, "ricorrenza_testo"))) for r in listed]
        dates = [(d, limit) for d, limit in dates if d and 0 <= (today - d).days <= limit]
        if dates:
            # Independent current evidence keeps its own stricter age bound;
            # an expired primary publisher does not invalidate another source.
            updated, source_age_limit = max(dates)
            projection_basis = "riscontri_campi:ricorrenza_testo"
        elif undated := [r for r in listed if not r.get("fonte_aggiornata_il")]:
            # Owner rule (2026-10-25): a page read within MAX_READ_AGE that still
            # lists this exact recurrence keeps predictions renewing when the page
            # states no content date at all. A declared date keeps its own age
            # limits above. Support lapses with the read; the expiry below then
            # withdraws the predictions.
            updated = max(parse_source_day(r["letto_il"]) for r in undated)
            projection_basis = "riscontri_campi:ricorrenza_testo"
            source_age_limit = MAX_READ_AGE
    if (record.get("proiezione_fonte") == "riscontri_campi:ricorrenza_testo"
            and projection_basis != "riscontri_campi:ricorrenza_testo"
            and (updated is None or not 0 <= (today - updated).days <= source_age_limit)
            and record.get("date_quality") == "prevista"):
        # These dates were explicitly generated from field receipts. If that
        # support is withdrawn or expires, unknown primary age cannot keep
        # the old synthetic calendar alive. Legacy estimates with another
        # provenance, and publisher-reported/confirmed dates, are unaffected.
        record["date"] = []
        record["date_quality"] = "sconosciuta"
        record["proiezione_regola"] = None
        record["proiezione_generata_il"] = ""
        record["proiezione_fonte"] = ""
        return record, "expired_field_evidence_forecast"
    if updated is None:
        # Existing estimates are retained as estimates, with their original
        # provenance. A recent import/read is never a reason to extend them.
        return record, ("existing_forecast_source_scope_filtered" if filtered_existing_source_scope
                        else "existing_forecast_month_scope_filtered" if filtered_existing_month_scope
                        else "unknown_source_age")
    age = (today - updated).days
    if age < 0:
        return record, "source_from_future"
    if age > source_age_limit:
        # Never leave predicted future editions visible after their only
        # supporting source ages out. This is a safety downgrade, NOT a
        # deletion of the underlying market identity or source history.
        if record.get("date_quality") == "prevista" and record.get("date"):
            record["date"] = []
            record["date_quality"] = "sconosciuta"
            record["proiezione_regola"] = None
            record["proiezione_generata_il"] = ""
            record["proiezione_fonte"] = ""
            return record, "expired_stale_forecast"
        return record, "stale_source"

    # Clear any old *projected* dates and replace with rolling predictions,
    # so a year of past projections never accumulates. Source dates marked
    # confirmed/reported are handled above and left untouched.
    dates = project_dates(rule, today, horizon_days)
    if not dates:
        return record, "empty_projection"
    record["date"] = dates
    record["date_quality"] = "prevista"
    record["proiezione_regola"] = rule
    record["proiezione_generata_il"] = today.isoformat()
    record["proiezione_fonte"] = projection_basis
    return record, "renewed"


def refresh_record(original: dict, today: date, horizon_days: int = MAX_LOOKAHEAD_DAYS,
                   max_stale_days: int = MAX_SOURCE_STALE_DAYS, *, source_limits=None):
    updated, reason = _refresh_record_base(original, today, horizon_days, max_stale_days,
                                           source_limits=source_limits)
    scoped, editorial_reason = apply_editorial_scope(updated, today=today)
    return scoped, editorial_reason if scoped != updated else reason


def refresh_records(records: list[dict], today: date, horizon_days: int = MAX_LOOKAHEAD_DAYS,
                    max_stale_days: int = MAX_SOURCE_STALE_DAYS, *,
                    source_limits=None) -> tuple[list[dict], dict]:
    if source_limits is None:
        source_limits = forecast_source_limits()
    output = []
    counts = Counter()
    improved = 0
    changed = 0
    monthly = 0
    preserved_unknown = 0
    scope_dates_withdrawn = 0
    scope_forecasts_withdrawn = 0
    for original in records:
        updated, reason = refresh_record(original, today, horizon_days, max_stale_days,
                                         source_limits=source_limits)
        counts[reason] += 1
        if (reason in TEMPORAL_SCOPE_REASONS and original.get("date_quality") == "prevista"
                and original.get("date") and not updated.get("date")):
            scope_forecasts_withdrawn += 1
            scope_dates_withdrawn += len(original["date"])
        if (reason == "unknown_source_age" and original.get("date_quality") == "prevista"
                and original.get("date")):
            preserved_unknown += 1
        if reason == "renewed":
            if not any(date_value >= today.isoformat() for date_value in original.get("date", [])):
                improved += 1
            if updated["date"] != original.get("date"):
                changed += 1
            if updated["proiezione_regola"]["kind"] == "monthly_nth_weekday":
                monthly += 1
        output.append(updated)
    return output, {
        "date": today.isoformat(),
        "input_records": len(records),
        "output_records": len(output),
        "horizon_days": horizon_days,
        "max_source_stale_days": max_stale_days,
        "reasons": dict(sorted(counts.items())),
        "newly_dated": improved,
        "date_ranges_changed": changed,
        "monthly_rules_applied": monthly,
        "unknown_source_dates_preserved_without_renewal": preserved_unknown,
        "temporal_scope_holds": sum(counts.get(reason, 0) for reason in TEMPORAL_SCOPE_REASONS),
        "temporal_scope_forecasts_withdrawn": scope_forecasts_withdrawn,
        "temporal_scope_dates_withdrawn": scope_dates_withdrawn,
        "all_dates_marked_forecast": all(
            m.get("date_quality") == "prevista" for m in output
            if m.get("proiezione_fonte") in {
                "ricorrenza_testo", "riscontri_campi:ricorrenza_testo"}),
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path)
    parser.add_argument("--horizon-days", type=int, default=MAX_LOOKAHEAD_DAYS)
    parser.add_argument("--max-stale-days", type=int, default=MAX_SOURCE_STALE_DAYS)
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    original = json.loads(args.input.read_text("utf-8"))
    if not isinstance(original, list):
        raise ValueError("Forecast input must be a list of records")
    output, report = refresh_records(original, args.today, args.horizon_days,
                                      args.max_stale_days)
    if len(output) != len(original) or not report["all_dates_marked_forecast"]:
        raise ValueError("Forecast loss or incorrect provenance; refusing to write")
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
    if not args.dry_run:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(output, ensure_ascii=False, separators=(",", ":")) + "\n", "utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
