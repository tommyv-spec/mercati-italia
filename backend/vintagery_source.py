#!/usr/bin/env python3
"""Vintagery (vintagery.it), the owner's own market directory, read from a browser capture.

Owner decision 2026-10-27: include Vintagery's markets. Its site answers scripts with
a Vercel Security Checkpoint (HTTP 429), so the nightly never reads it and nothing
tries to get past that. About once a month the owner's Chrome (Claude in Chrome) runs
ops/vintagery/collect.js on vintagery.it; `python backend/vintagery_source.py <download>`
turns the downloaded file into the committed snapshot backend/data/vintagery-snapshot.json
(structured fields only, no HTML). See ops/vintagery/README.md.

One snapshot card = one Vintagery page, dated the day the browser read it (never the
day the nightly runs), so its facts age honestly: a card read more than 45 days ago is
no longer applied and the general freshness rules take over. Content date = the page's
"Scheda verificata il" day.

Three uses, all through the shared editorial machinery (never per market):
- new markets: editorial_discovery admits snapshot cards like candidate pages
  (same admission and duplicate rules, `max_new` per night; pages());
- then one autopilot step, apply(): Vintagery's own cards are re-read when a newer
  snapshot arrives (reread()), and markets another source already has (exactly one
  visible card with the same venue and calendar, or the same name in the town) get
  empty street/hours filled and a rule that reads the same restated, each with a
  receipt (fill()). verify() rebuilds the step; verify_exported() checks the export.

Facts kept: the stated rule (only when the shared reader reads the whole sentence,
nothing else on the page qualifies it and every date the page gives falls on it), the
next date unless Vintagery marks it "da confermare", other listed "Prossime date", clock
hours unless the page gives seasonal or per-edition hours, organiser/website/Instagram,
description. No coordinates. A kept rule is the card's calendar: predicted dates
("prevista", the usual horizon) while the page's check date is at most 180 days old and
its read at most 45 days old (editorial_calendar_scope.RULE_PAGE_PUBLISHERS); otherwise
only the listed dates count.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from collections import Counter
from copy import deepcopy
from datetime import date
from pathlib import Path

PUBLISHER = "vintagery.it"
SNAPSHOT_PATH = Path(__file__).resolve().parent / "data/vintagery-snapshot.json"
INDEX_URL = "https://vintagery.it/sitemap/mercatini-0.xml"
URL = re.compile(r"https://vintagery\.it/mercatini/([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})")
MAX_CARDS = 3000
MAX_SNAPSHOT_BYTES = 4_000_000
HASH_BASIS = "browser_captured_record"
TEXT_KEYS = ("name", "city", "region", "address", "schedule_notes", "frequency", "start_date",
             "start_time", "end_time", "organizer", "website", "instagram", "price_info",
             "description", "verified_on")
CARD_KEYS = {"id", "url", "read_on", "record", "unconfirmed", "tags", *TEXT_KEYS}
MONTHS = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto",
          "settembre", "ottobre", "novembre", "dicembre")
MONTH = "(?:" + "|".join(MONTHS) + ")"
CLOCK = re.compile(r"\b([01]?\d|2[0-3])[:.]([0-5]\d)\b")
CLOCK_RANGE = re.compile(r"\b([01]?\d|2[0-3])(?:[:.]([0-5]\d))?\s*[-–]\s*([01]?\d|2[0-3])(?:[:.]([0-5]\d))?\b")
SEASONAL_HOURS = re.compile(r"\b(?:invern|estat|estiv|orario indicato|orari diversi|variabil)", re.I)
# A rule sentence ends with its hours ("…, 9:00-18:00", "…, dalle 8 al tramonto"): not the rule.
HOURS_TAIL = re.compile(r"(?:,\s*|\s+)(?:(?:dalle?\s+(?:ore\s+)?)?\d{1,2}(?:[:.]\d{2})?\s*(?:[-–]|al(?:le)?)\s*"
                        r"(?:\d{1,2}(?:[:.]\d{2})?|tramonto)|dall.alba al tramonto|tutto il giorno|"
                        r"(?:la )?mattina|al mattino|pomeriggio)\s*$", re.I)
# Words the shared reader would silently ignore: the sentence says more than one rule.
QUALIFIER = re.compile(r"\b(?:(?:19|20)\d{2}|\d{1,2}\s+" + MONTH + r"|anticipat\w*|posticipat\w*|spostat\w*|"
                       r"solitamente|di solito|variazion\w*|variabil\w*|oltre|anche|inoltre|quando|"
                       r"eventual\w*|alcun\w*|più|piu|nei mesi|salvo|sospes\w*|annullat\w*|rinviat\w*|"
                       r"straordinar\w*|alternat\w*|tranne\s+(?:il|la|i|le|in caso)|meteo|maltempo|pioggia)\b", re.I)
NEXT_DATES = re.compile(r"^prossim[ae] dat[ae]\s*:\s*(.+)$", re.I)
DATE_GROUP = re.compile(r"((?:\d{1,2}\s*(?:,|\be\b)?\s*)+)\s+(" + MONTH + r")\s+(\d{4})", re.I)


def clean(value, limit=900):
    if value is None or value == "$undefined":
        return ""
    return " ".join(str(value).split())[:limit]


def source_identity(url):
    match = URL.fullmatch(str(url or ""))
    return (PUBLISHER, match[1]) if match else None


def _iso(value):
    try:
        return date.fromisoformat(value).isoformat() if re.fullmatch(r"\d{4}-\d{2}-\d{2}", str(value)) else ""
    except ValueError:
        return ""


def verified_day(text, read_on):
    """'26 ottobre' -> the latest such day on or before the read day; '26 ottobre 2025' as stated."""
    match = re.fullmatch(r"(\d{1,2}) (" + MONTH + r")(?: (\d{4}))?", clean(text).casefold())
    if not match or not _iso(read_on):
        return ""
    read = date.fromisoformat(read_on)
    month, day = MONTHS.index(match[2]) + 1, int(match[1])
    for year in ([int(match[3])] if match[3] else [read.year, read.year - 1]):
        try:
            found = date(year, month, day)
        except ValueError:
            return ""
        if found <= read:
            return found.isoformat()
    return ""


# ---------------------------------------------------------------- snapshot

def normalize_capture(raw):
    """The browser download ({id: record}) as the compact committed snapshot."""
    if not isinstance(raw, dict) or not 1 <= len(raw) <= MAX_CARDS:
        raise ValueError("Vintagery capture is not a bounded {id: card} object")
    cards, skipped = [], Counter()
    for key, rec in sorted(raw.items()):
        identity = source_identity(rec.get("url")) if isinstance(rec, dict) else None
        read_on = _iso(str((rec or {}).get("read_at") or "")[:10]) if isinstance(rec, dict) else ""
        if not identity or identity[1] != key or not read_on:
            skipped["invalid_card"] += 1
            continue
        card = {k: "" for k in TEXT_KEYS}
        card.update(id=key, url=rec["url"], read_on=read_on, unconfirmed=False, tags=[],
                    record=bool(rec.get("id") == key and not rec.get("parse_error")))
        if card["record"]:
            for k in ("name", "city", "region", "address", "schedule_notes", "frequency",
                      "organizer", "website", "instagram", "price_info"):
                card[k] = clean(rec.get(k), 600)
            card["description"] = clean(rec.get("description"), 900)
            card["start_date"] = _iso(rec.get("start_date"))
            card["start_time"], card["end_time"] = clean(rec.get("start_time"), 5), clean(rec.get("end_time"), 5)
            card["unconfirmed"] = rec.get("unconfirmed") is True
            card["tags"] = [clean(t, 40) for t in rec.get("tags") or [] if clean(t, 40)][:12]
            card["verified_on"] = verified_day(rec.get("verified"), read_on)
        else:
            # Undated "date annunciate di volta in volta" pages carry no record: counted, never admitted.
            card["name"] = clean(str(rec.get("title") or "").split(" — ")[0], 160)
        cards.append(card)
    days = [c["read_on"] for c in cards]
    snapshot = {"schema": 1, "publisher": PUBLISHER, "index": INDEX_URL,
                "read_from": min(days), "read_to": max(days), "cards": cards}
    return validate_snapshot(snapshot), dict(skipped)


def validate_snapshot(snapshot):
    if (not isinstance(snapshot, dict) or set(snapshot) != {"schema", "publisher", "index", "read_from", "read_to", "cards"}
            or snapshot["schema"] != 1 or snapshot["publisher"] != PUBLISHER or snapshot["index"] != INDEX_URL
            or not isinstance(snapshot["cards"], list) or not 1 <= len(snapshot["cards"]) <= MAX_CARDS):
        raise ValueError("Invalid Vintagery snapshot")
    seen = set()
    for card in snapshot["cards"]:
        if (not isinstance(card, dict) or set(card) != CARD_KEYS or card["id"] in seen
                or source_identity(card["url"]) != (PUBLISHER, card["id"]) or not _iso(card["read_on"])
                or not snapshot["read_from"] <= card["read_on"] <= snapshot["read_to"]
                or type(card["record"]) is not bool or type(card["unconfirmed"]) is not bool
                or not isinstance(card["tags"], list) or any(not isinstance(t, str) for t in card["tags"])
                or any(not isinstance(card[k], str) or len(card[k]) > 900 for k in TEXT_KEYS)
                or card["verified_on"] and not card["verified_on"] <= card["read_on"]):
            raise ValueError("Invalid Vintagery snapshot card")
        seen.add(card["id"])
    return snapshot


def load_snapshot(path=None):
    path = Path(path or SNAPSHOT_PATH)
    if not path.is_file():
        return None
    if path.stat().st_size > MAX_SNAPSHOT_BYTES:
        raise ValueError("Vintagery snapshot exceeds its byte bound")
    return validate_snapshot(json.loads(path.read_text("utf-8")))


def card_blob(card):
    """The bytes a card's proofs fingerprint: its canonical JSON."""
    return json.dumps(card, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def current_cards(snapshot, today):
    """Cards with a record, read in the last 45 days (the editorial read window)."""
    if snapshot is None:
        return []
    return [c for c in snapshot["cards"] if c["record"] and 0 <= (today - date.fromisoformat(c["read_on"])).days <= 45]


# ---------------------------------------------------------------- page facts

def street_and_province(address, city, region=""):
    """'Piazza Santa Lucia, 96100 Siracusa (SR)' -> ('Piazza Santa Lucia', 'SR'). A trailing
    region/"Italia" ('…, Manziana (RM), Lazio') and a frazione before the town
    ('56010 Lugnano - Vicopisano (PI)') go too. Fail closed: a street that still carries a
    postcode, a province code, the region or "Italia" is not separable and is left out."""
    text = re.sub(r",\s*italia\s*$", "", clean(address, 600), flags=re.I)
    if region:
        text = re.sub(r"(?:,\s*|\s*\(\s*)" + re.escape(region).replace(r"\-", "[- ]") + r"\s*\)?\s*$", "", text, flags=re.I)
    tail = None
    for match in re.finditer(r",\s*(?:\d{5}\s+)?(?:[^,()]{1,40}?\s+[-–]\s+)?" + re.escape(city)
                             + r"(?:\s*\(([A-Z]{2})\)|\s*\([^()\d]{3,30}\)|,\s*([A-Z]{2}))?(?=\s*(?:[.;]|$))",
                             text, re.I) if city else ():
        tail = match
    if tail and text[:tail.start()].strip(" ,;."):
        province = (tail[1] or tail[2] or "").upper()
        text = text[:tail.start()].strip(" ,;.")
    else:
        found = re.search(r"\(([A-Z]{2})\)\s*$", text)
        province = found[1] if found else ""
    if (re.search(r"\b\d{5}\b|\([A-Z]{2}\)|\bitalia\b", text)
            or region and re.search(re.escape(region).replace(r"\-", "[- ]"), text, re.I)):
        return "", province
    return text, province


def _clock(hour, minute):
    return f"{int(hour):02d}:{int(minute or 0):02d}"


def hours_text(card):
    """'08:00–13:00' from the record, unless the page gives other (seasonal, per-edition) hours."""
    times = []
    for value in (card["start_time"], card["end_time"]):
        match = re.fullmatch(r"([01]?\d|2[0-3]):([0-5]\d)", value)
        times.append(_clock(*match.groups()) if match else "")
    start, end = times
    if not start or not end or start >= end:
        return None, "hours_missing"
    notes = card["schedule_notes"]
    stated = {_clock(*m.groups()) for m in CLOCK.finditer(notes)}
    for m in CLOCK_RANGE.finditer(notes):
        stated |= {_clock(m[1], m[2]), _clock(m[3], m[4])}
    if SEASONAL_HOURS.search(notes) or stated - {start, end}:
        return None, "hours_seasonal_or_per_edition"
    return start + "–" + end, None


def _sentences(notes):
    return [s.strip(" .;") for s in re.split(r"(?<=[.;])\s+", notes) if s.strip(" .;")]


def rule_text(notes):
    """(rule, None) when the first sentence is a rule the shared reader reads in full and
    nothing else on the page qualifies it; else (None, reason)."""
    from recurrence_refresh import (FULL_MONTHLY_RECURRENCE, FULL_WEEKLY_RECURRENCE, JOINED_ORDINALS,
                                    _complete_month_rule, _spelled_ordinals, forecast_rule, temporal_scope_hold)
    sentences = _sentences(notes)
    if not sentences:
        return None, "rule_missing"
    # "giovedi'" is "giovedì" typed without the accent.
    rule = re.sub(r"([aeiou])'(?=[\s,.;)]|$)", lambda m: "àèìòù"["aeiou".index(m[1])], sentences[0])
    while (shorter := HOURS_TAIL.sub("", rule).strip(" ,")) != rule:
        rule = shorter
    rest = [s for s in sentences[1:] if not NEXT_DATES.match(s) and not SEASONAL_HOURS.match(s)
            and CLOCK_RANGE.sub("", CLOCK.sub("", s)).strip(" ,.;-–") != ""]
    if not rule or len(rule) > 180 or not forecast_rule({"ricorrenza_testo": rule}):
        return None, "rule_not_read"
    # The whole sentence must be the rule ("…, tutto l'anno" aside): the reader skips
    # trailing prose ("…, mercato dei privati sotto la Tettoia Nervi"), the card must not show it.
    core = re.sub(r",?\s*\(?\s*(?:per )?tutto l.anno\s*\)?", "", rule, flags=re.I).strip(" ,")
    text = _spelled_ordinals(core)
    joined = re.fullmatch(r"(?:ogni )?(" + JOINED_ORDINALS.pattern + r") (?:del|di ogni) mese", text)
    if not (FULL_WEEKLY_RECURRENCE.fullmatch(text) or FULL_MONTHLY_RECURRENCE.fullmatch(text)
            or joined or _complete_month_rule(core)):
        return None, "rule_with_other_text"
    if (temporal_scope_hold({"ricorrenza_testo": rule}) or QUALIFIER.search(rule)
            or any(QUALIFIER.search(s) or re.search(MONTH, s, re.I) for s in rest)):
        return None, "rule_qualified"
    return rule, None


def _rule_fits_dates(rule, card):
    """(rule, None) when every date the page gives from its read day on, Vintagery's own
    "da confermare" estimate included, falls on the rule; else (None, reason)."""
    from recurrence_refresh import forecast_rule, project_dates
    read = date.fromisoformat(card["read_on"])
    dates = [d for d in [card["start_date"], *(next_dates(card["schedule_notes"]) or [])] if d and d >= card["read_on"]]
    if not dates:
        return rule, None
    horizon = (date.fromisoformat(max(dates)) - read).days
    projected = set(project_dates(forecast_rule({"ricorrenza_testo": rule}), read, max(7, horizon))) if horizon <= 365 else set()
    return (rule, None) if set(dates) <= projected else (None, "listed_date_not_on_rule")


def next_dates(notes):
    """['2026-11-08', ...] from a 'Prossime date: 8 novembre 2026, ...' sentence; None if unreadable."""
    found = []
    for sentence in _sentences(notes):
        match = NEXT_DATES.match(sentence)
        if not match:
            continue
        body = match[1]
        groups = list(DATE_GROUP.finditer(body))
        if not groups or DATE_GROUP.sub("", body).strip(" ,e") != "":
            return None
        for group in groups:
            for day in re.findall(r"\d{1,2}", group[1]):
                try:
                    found.append(date(int(group[3]), MONTHS.index(group[2].casefold()) + 1, int(day)).isoformat())
                except ValueError:
                    return None
    return sorted(set(found))


def parse_detail(blob, *, requested_url):
    """One snapshot card as the shared editorial document (see cosedicasa_layout.parse_detail)."""
    card = json.loads(blob.decode("utf-8"))
    identity = source_identity(requested_url)
    if (not isinstance(card, dict) or set(card) != CARD_KEYS or card["url"] != requested_url
            or not identity or identity[1] != card["id"] or not card["record"]):
        raise ValueError("Vintagery card has no usable record")
    conflicts, warnings = [], []
    street, province = street_and_province(card["address"], card["city"], card["region"])
    hours, reason = hours_text(card)
    if reason:
        warnings.append(reason)
    rule, reason = rule_text(card["schedule_notes"])
    if reason:
        warnings.append(reason)
    if rule:
        rule, reason = _rule_fits_dates(rule, card)
        if reason:
            warnings.append(reason)
    listed = next_dates(card["schedule_notes"])
    if listed is None:
        conflicts.append({"field": "calendar", "code": "unparsed_next_dates", "values": [card["schedule_notes"][:300]]})
        listed = []
    days = []
    if card["unconfirmed"]:
        # Vintagery's own estimate ("Data da confermare"), not a date the page reports.
        warnings.append("next_date_unconfirmed")
    else:
        if card["start_date"]:
            days.append(card["start_date"])
            if listed and card["start_date"] >= card["read_on"] and card["start_date"] not in listed:
                conflicts.append({"field": "calendar", "code": "next_date_not_in_listed_dates",
                                  "values": [card["start_date"], listed]})
        days = sorted(set(days) | set(listed))
    start_time, end_time = (hours.split("–") if hours else (None, None))
    evidence = ["vintagery.it card record (browser capture)"]
    rows = [{"field": field, "value": card[field], "evidence": ["record." + field]}
            for field in ("organizer", "website", "instagram") if card[field]]
    return {
        "schema": 1, "status": "held" if conflicts else "parsed",
        "source": {"publisher": PUBLISHER, "source_id": card["id"], "requested_url": requested_url,
                   "final_url": requested_url, "canonical_url": None, "redirect_observed": False,
                   "html_sha256": hashlib.sha256(blob).hexdigest(), "bytes": len(blob),
                   "hash_basis": HASH_BASIS, "published_at": None,
                   "modified_at": card["verified_on"] or None},
        # "Antiquariato alle Rondinelle — Roncadelle": the town is not part of the name.
        "event": {"name": re.sub(r"\s+[—–-]\s+" + re.escape(card["city"]) + r"$", "", card["name"])
                  if card["city"] else card["name"],
                  "location": {"city": card["city"], "province": province, "region": card["region"],
                               "address": street if len(street) <= 300 else ""},
                  "hours_text": hours, "hours_intervals": [{"start": start_time, "end": end_time}] if hours else [],
                  "recurrence_text": rule, "archive_marker": False,
                  "edition_intervals": [{"start": d, "end": d} for d in days],
                  "occurrences": [{"date": d, "start_time": start_time, "end_time": end_time,
                                   "status": "source_listed", "evidence": evidence} for d in days],
                  "date_intervals": [], "calendar_complete": bool(days or rule) and not conflicts,
                  "calendar_scope": "explicit_visible_list" if days else
                  "recurring_statement_only" if rule else "unknown",
                  "scope_statements": [], "conditions": [], "calendar_rules": [], "suspensions": [],
                  "source_rows": rows, "description": card["description"],
                  "observed_location": {"city": card["city"], "province": province,
                                        "region": card["region"], "address": card["address"]}},
        "conflicts": conflicts, "warnings": warnings,
        "field_evidence": {"identity": {"selector": "record.id", "value": card["id"]},
                           "calendar": {"selector": "record.start_date; schedule_notes 'Prossime date'"},
                           "hours": {"selector": "record.start_time/end_time"},
                           "location": {"selector": "record.city/region/address"}},
    }


def page(card):
    """A snapshot card as an editorial page (see editorial_discovery.acquire)."""
    return {"requested_url": card["url"], "final_url": card["url"], "read_on": card["read_on"],
            "body": card_blob(card), "redirects": [], "redirect_observed": False}


# ---------------------------------------------------------------- new markets

def pages(rows, *, today, limit, snapshot=None):
    """At most `limit` current cards the catalog lacks: dated ones first, in an order that
    changes daily, so every card is tried within a few nights. A card already restated
    on another market by fill() is that market, not a candidate."""
    from editorial_discovery import catalog_identities
    from field_evidence import clean_receipts
    snapshot = load_snapshot() if snapshot is None else snapshot
    known = catalog_identities(rows, PUBLISHER)
    proved = {r["url"] for row in rows for r in clean_receipts(row.get("riscontri_campi"), row, today=today)
              if source_identity(r["url"])}
    candidates = [c for c in current_cards(snapshot, today)
                  if (PUBLISHER, c["id"]) not in known and c["url"] not in proved]
    salt = today.isoformat()
    candidates.sort(key=lambda c: (c["unconfirmed"] or not c["start_date"] or c["start_date"] <= salt,
                                   hashlib.sha256((salt + c["url"]).encode()).hexdigest()))
    return [page(c) for c in candidates[:limit]]


# ---------------------------------------------------------------- Vintagery's own cards

def reread(rows, *, today, snapshot=None):
    """Re-read Vintagery-owned cards when the snapshot holds a newer read of their page.

Returns (rows, proof): the proof is eventiesagre_detail_refresh.preview's, so that
module's verify_changes/verify_exported rebuild it from the saved page facts."""
    import eventiesagre_detail_refresh as editorial
    from editorial_calendar_scope import KEY, clean_editorial_evidence
    snapshot = load_snapshot() if snapshot is None else snapshot
    by_url = {c["url"]: c for c in current_cards(snapshot, today)}
    documents = []
    for row in rows:
        card = by_url.pop(row.get("url_fonte"), None)
        evidence = clean_editorial_evidence(row.get(KEY), row, today=today) if card else None
        if card and (evidence is None or card["read_on"] > evidence["read_on"]):
            documents.append({"read_on": card["read_on"], "parsed": editorial.parse_document(
                card_blob(card), requested_url=card["url"], today=today)})
    documents = documents[:editorial.PUBLISHERS[PUBLISHER]["max_details"]]
    return editorial.preview(rows, documents, today=today, publisher=PUBLISHER)


# ---------------------------------------------------------------- markets other sources have

FILL_MANAGER = "vintagery_fill"
FILL_METHOD = "nome_sede_comune_univoco"
FILL_FIELDS = ("indirizzo", "orario_testo", "ricorrenza_testo")
MAX_FILLS = 400


def _visible(rows):
    return [r for r in rows if not r.get("duplicato_di") and not r.get("concluso")]


def _match(candidate, town_rows):
    """The one visible card that is this market (same venue+calendar, or same name in the
    town), or (None, reason)."""
    from export_static import comparable_market_name, same_market, same_venue
    venue = [r for r in town_rows if same_market(r, candidate) or same_venue(r, candidate)]
    name = comparable_market_name(candidate["nome"])
    named = [r for r in town_rows if name and comparable_market_name(str(r.get("nome") or "")) == name]
    found = {r["slug"]: r for r in venue + named}
    if len(found) != 1:
        return None, "no_match" if not found else "several_matches"
    return next(iter(found.values())), None


def fill(rows, *, today, snapshot=None, limit=MAX_FILLS):
    """Fill empty fields of markets other sources already have; restate a matching rule.

Only one exact match per card, only cards no publisher field engine owns, never a
human-verified card, never a different value (held, counted by field). Every assigned
or restated value carries a receipt naming the Vintagery page and its read day."""
    import eventiesagre_detail_refresh as editorial
    from editorial_discovery import _canonical_place, _town
    from field_evidence import (FIELDS, MAX_RECEIPTS, clean_receipts, make_receipt, mark_managed_fields)
    from recurrence_refresh import forecast_rule
    snapshot = load_snapshot() if snapshot is None else snapshot
    result = deepcopy(rows)
    index = {r["slug"]: i for i, r in enumerate(result)}
    towns = {}
    for row in _visible(result):
        towns.setdefault(_town(row), []).append(row)
    outcomes, held, counts, touched = [], Counter(), Counter(), set()
    for card in current_cards(snapshot, today):
        outcome = {"url": card["url"], "status": "held", "reason": None}
        outcomes.append(outcome)
        try:
            document = editorial.parse_document(card_blob(card), requested_url=card["url"], today=today)
        except ValueError:
            outcome["reason"] = "record_unreadable"
            continue
        event = document["event"]
        place = _canonical_place(event.get("observed_location") or {})
        if place is None or document["conflicts"]:
            outcome["reason"] = "istat_geography_unresolved" if place is None else "source_conflict"
            continue
        values = {"indirizzo": event["location"].get("address") or "", "orario_testo": event.get("hours_text") or "",
                  "ricorrenza_testo": event.get("recurrence_text") or ""}
        candidate = {"slug": "vintagery:" + card["id"], "nome": " ".join(event["name"].split()),
                     "citta": place["city"], "provincia": place["province"], "regione": place["region"],
                     "fonte": PUBLISHER, **values}
        match, reason = _match(candidate, towns.get(_town(candidate), []))
        if match is None:
            outcome["reason"] = reason
            continue
        row = result[index[match["slug"]]]
        outcome["market_id"] = row["slug"]
        if row.get("fonte") == PUBLISHER or row["slug"] in touched:
            outcome["reason"] = "own_card_or_already_filled"
            continue
        if row.get("verificato_il"):
            outcome["reason"] = "human_verified"
            continue
        prior = clean_receipts(row.get("riscontri_campi"), row, today=today)
        if len(prior) >= MAX_RECEIPTS:
            outcome["reason"] = "receipt_slots_full"
            continue
        assigned, observed = {}, {}
        for field in FILL_FIELDS:
            value, current = values[field], row.get(field) or ""
            if not value or len(value) > FIELDS[field]:
                continue
            if field == "ricorrenza_testo" and current:
                card_rule, page_rule = forecast_rule(row), forecast_rule({"ricorrenza_testo": value})
                if card_rule and card_rule == page_rule:
                    observed[field] = current
                else:
                    held[field] += 1
            elif not current:
                assigned[field] = value
            elif current != value:
                held[field] += 1
            else:
                observed[field] = current
        if not assigned and not observed:
            outcome["reason"] = "nothing_to_fill_or_restate"
            continue
        if len(touched) >= limit:
            outcome["reason"] = "per_run_cap_reached"
            continue
        updated = {**row, **assigned}
        try:
            receipt = make_receipt(updated, values={**observed, **assigned}, source_url=card["url"],
                source_name=PUBLISHER, source_id="vintagery-card:" + card["id"], source_row=card["id"],
                read_on=card["read_on"], source_updated_on=card["verified_on"],
                source_sha256=document["source"]["html_sha256"], scope="pagina", method=FILL_METHOD,
                fingerprint_kind="publisher_parsed_json")
        except ValueError:
            outcome["reason"] = "source_values_not_receiptable"
            continue
        if assigned:
            receipt = mark_managed_fields(receipt, list(assigned), manager=FILL_MANAGER)
        updated["riscontri_campi"] = clean_receipts([*prior, receipt], updated, today=today)
        if not any(r["url"] == card["url"] for r in updated["riscontri_campi"]):
            outcome["reason"] = "receipt_not_kept"
            continue
        if updated == row:
            outcome["reason"] = "already_current"
            continue
        result[index[row["slug"]]] = updated
        touched.add(row["slug"])
        counts.update("filled:" + f for f in assigned)
        counts.update("restated:" + f for f in observed)
        outcome.update(status="changed", reason=None, assigned=assigned, observed=observed,
                       sha256=document["source"]["html_sha256"], read_on=card["read_on"])
    from field_evidence import fingerprint
    report = {"schema": 1, "date": today.isoformat(), "publisher": PUBLISHER,
              "snapshot_read_to": snapshot["read_to"] if snapshot else None,
              "input_sha256": fingerprint(rows), "output_sha256": fingerprint(result),
              "outcomes": outcomes, "changed_ids": sorted(touched),
              "summary": {"cards": len(outcomes), "markets_changed": len(touched), **dict(sorted(counts.items())),
                          "held_values_by_field": dict(sorted(held.items())),
                          "held_by_reason": dict(sorted(Counter(o["reason"] for o in outcomes
                                                                if o["reason"]).items()))}}
    return result, report


def apply(rows, *, today, snapshot=None):
    """The nightly step after editorial discovery: re-read own cards, then fill() the others."""
    snapshot = load_snapshot() if snapshot is None else snapshot
    reread_rows, proof = reread(rows, today=today, snapshot=snapshot)
    result, filled = fill(reread_rows, today=today, snapshot=snapshot)
    summary = {"snapshot_read_to": snapshot["read_to"] if snapshot else None,
               "own_cards_reread": len(proof["documents"]), "own_cards_changed": len(proof["changed_existing_ids"]),
               **filled["summary"]}
    return result, {"schema": 1, "date": today.isoformat(), "reread": proof, "fill": filled, "summary": summary}


def verify(before, after, report, *, today, snapshot=None):
    """Rebuild the whole step from the committed snapshot; only owned and filled fields may differ."""
    import eventiesagre_detail_refresh as editorial
    expected, replay = apply(before, today=today, snapshot=snapshot)
    if expected != after or replay != report:
        raise ValueError("Vintagery step cannot be rebuilt from the committed snapshot")
    middle, _ = reread(before, today=today, snapshot=snapshot)
    editorial.verify_changes(before, middle, report["reread"], today=today)
    allowed = set(FILL_FIELDS) | {"riscontri_campi"}
    for old, new in zip(middle, after):
        if {k for k in set(old) | set(new) if old.get(k) != new.get(k)} - allowed:
            raise ValueError("Vintagery fill changed a field it does not fill")
    return {"release_safe": True, "own_cards_changed": len(report["reread"]["changed_existing_ids"]),
            "filled_ids": len(report["fill"]["changed_ids"])}


def verify_exported(rows, report, *, today):
    """Owned cards kept their page facts; every filled value kept its receipt."""
    import eventiesagre_detail_refresh as editorial
    from field_evidence import clean_receipts
    editorial.verify_exported(rows, report["reread"], today=today)
    by_id = {r["slug"]: r for r in rows}
    checked = 0
    for outcome in report["fill"]["outcomes"]:
        if outcome["status"] != "changed":
            continue
        row = by_id.get(outcome["market_id"])
        if row is None:
            raise ValueError("A Vintagery-filled market disappeared from export")
        receipts = [r for r in clean_receipts(row.get("riscontri_campi"), row, today=today)
                    if r["url"] == outcome["url"] and r["sha256"] == outcome["sha256"]]
        for field, value in outcome["assigned"].items():
            if row.get(field) == value and not any(r["valori"].get(field) == value for r in receipts):
                raise ValueError("A Vintagery-filled field lost its receipt")
        checked += 1
    return {"release_safe": True, "own_cards_checked": len(report["reread"]["outcomes"]),
            "filled_ids_checked": checked}


# ---------------------------------------------------------------- CLI

def main(argv=None):
    parser = argparse.ArgumentParser(description="Turn a Vintagery browser download into the committed snapshot.")
    parser.add_argument("download", type=Path, help="vintagery_cards.json saved by ops/vintagery/collect.js")
    parser.add_argument("--out", type=Path, default=SNAPSHOT_PATH)
    args = parser.parse_args(argv)
    snapshot, skipped = normalize_capture(json.loads(args.download.read_text("utf-8")))
    text = json.dumps(snapshot, ensure_ascii=False, sort_keys=True, indent=0) + "\n"
    if len(text.encode("utf-8")) > MAX_SNAPSHOT_BYTES:
        raise SystemExit("Snapshot exceeds its byte bound")
    args.out.write_text(text, "utf-8", newline="\n")
    cards = snapshot["cards"]
    print(json.dumps({"cards": len(cards), "with_record": sum(c["record"] for c in cards),
                      "unconfirmed": sum(c["unconfirmed"] for c in cards), "skipped": skipped,
                      "read_from": snapshot["read_from"], "read_to": snapshot["read_to"]}))


if __name__ == "__main__":
    sys.exit(main())
