#!/usr/bin/env python3
"""Export checked market records to free Cloudflare Pages static assets.

Usage:
  python backend/export_static.py --input backend/mercati_clean.json
  python backend/export_static.py --input /tmp/export.json --dry-run
  python backend/export_static.py --firestore  # one-off migration, Admin SDK credentials

No user-facing request reads Firestore, KV, D1 or invokes a Worker.
Assets are content-addressed and served with long-lived cache headers.
The manifest is replaced last, after all new assets are written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from field_evidence import PUBLISHED_TOWN_FIXES, as_published, clean_receipts, clean_exceptions
from field_conflicts import KEY as FIELD_CONFLICTS, clean_conflicts
from source_calendar import clean_source_calendar, clean_source_detail, source_calendar_dates
from source_freshness import source_date_evidence
from source_hours import preserve_hours_text
from province_reconciliation import KEY as PROVINCE_PROOF, retained_proof as retained_province_proof
from lombardia_calendar_scope import calendar_scope, filter_dates, retained_identity
from editorial_calendar_scope import (
    KEY as EDITORIAL_EVIDENCE, clean_editorial_evidence,
    apply_editorial_scope, retain_editorial_evidence,
)
from urllib.parse import urlsplit
from compact_index import INDEX_SCHEMA, LEGACY_FIELDS, project_index
from position_resolver import (GENERIC_PLACE, OWN_REASONS as RESOLVER_HOLDS, clean_position_source,
                               distinctive_words, street_type)

CANONICAL_REGIONS = [
    "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna",
    "Friuli Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche",
    "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana",
    "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto",
]

VALID_STATUSES = {"attivo", "non_confermato", "annullato", "archiviato"}
VALID_CATEGORIES = {
    "alimentare", "antiquariato", "vintage_abbigliamento",
    "usato", "artigianato", "misto",
}
VALID_DATE_QUALITY = {"confermata", "riportata", "prevista", "sconosciuta"}
HOURS_CONTENT = re.compile(r"\d|mattin|pomerigg|sera|giorn|nott", re.I)
# eventiesagre's page footer ("Eventiesagre.it (D) é un marchio depositato ...")
# was read into descriptions; everything from it on is the site's, not the market's.
SITE_FOOTER = re.compile(r"\s*(?:Eventiesagre\.\s*i\s*t?\s*)?\(D\)\s*é\s+un\s+marchio.*", re.I | re.S)
MAX_SINGLE_BYTES = 750_000
MAX_MARKET_BYTES = 24_000_000
MAX_FUTURE_DAYS = 550
COORDINATE_HOLDS = frozenset({"coordinate_sorgente_incompatibili_con_localita_documentata"}) | RESOLVER_HOLDS
ITALY_BOUNDS = (35.0, 48.0, 6.0, 19.6)


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")[:100]


def canonical_region(name: str) -> str | None:
    key = slugify(name)
    lookup = {slugify(r): r for r in CANONICAL_REGIONS}
    lookup.update({
        "val-d-aosta": "Valle d'Aosta",
        "valle-daosta": "Valle d'Aosta",
        "trentino-altoadige": "Trentino-Alto Adige",
        "friuli-venezia-giulia": "Friuli Venezia Giulia",
    })
    return lookup.get(key)


def sanitize_url(value) -> str:
    candidate = safe_string(value, 650)
    parts = urlsplit(candidate)
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        return ""
    if parts.username or parts.password:
        return ""
    return candidate


def compact_json(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def safe_string(value, max_length=700) -> str:
    if value is None:
        return ""
    return str(value).strip()[:max_length]


def parse_dates(raw_dates, today: date) -> list[str]:
    if not isinstance(raw_dates, list):
        return []
    upper = today + timedelta(days=MAX_FUTURE_DAYS)
    dates = set()
    for raw in raw_dates:
        try:
            value = date.fromisoformat(str(raw))
            if today <= value <= upper:
                dates.add(value.isoformat())
        except ValueError:
            pass
    return sorted(dates)


def parse_location(raw: dict) -> tuple[float | None, float | None, str]:
    lat, lng = raw.get("lat"), raw.get("lng")
    if isinstance(lat, bool) or isinstance(lng, bool):
        return None, None, "sconosciuta"
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError, OverflowError):
        return None, None, "sconosciuta"
    lat_min, lat_max, lng_min, lng_max = ITALY_BOUNDS
    if not (lat_min <= lat <= lat_max and lng_min <= lng <= lng_max):
        return None, None, "sconosciuta"
    # A valid point is not proof it represents the real market location.
    precision = raw.get("position_quality", "non_verificata")
    if precision not in {"precisa", "approssimata", "non_verificata"}:
        precision = "non_verificata"
    return round(lat, 6), round(lng, 6), precision


def normalize(raw: dict, today: date) -> tuple[dict | None, str | None]:
    if not isinstance(raw, dict):
        return None, "record_not_object"
    editorial_evidence = None
    if raw.get(EDITORIAL_EVIDENCE) is not None:
        editorial_evidence = clean_editorial_evidence(raw[EDITORIAL_EVIDENCE], raw, today=today)
        if editorial_evidence is None:
            return None, "invalid_editorial_source_evidence"
        raw, _ = apply_editorial_scope(raw, today=today)
    nome = safe_string(raw.get("nome"), 160)
    citta = safe_string(raw.get("citta"), 120)
    regione_raw = safe_string(raw.get("regione"), 80)
    if not all((nome, citta, regione_raw)):
        return None, "name_city_region_missing"
    if not re.search(r"[a-zA-ZÀ-ÖØ-öø-ÿ]", citta):
        return None, "invalid_city_name"
    regione = canonical_region(regione_raw)
    if not regione:
        return None, "not_italian_region"
    if raw.get("status") in ("archiviato", "annullato"):
        return None, "inactive_market"
    # Editions titled with a past year and no future dates are historical,
    # not upcoming markets. Leave raw records intact in the original source.
    editions = [int(year) for year in re.findall(r"\b20[0-3][0-9]\b", nome)]
    if (editions and max(editions) < today.year and not parse_dates(raw.get("date"), today)
            and editorial_evidence is None):
        return None, "historical_edition_without_future_date"
    # Categories outside the product scope (for example "sagra" or
    # "carnevale") must not silently turn into generic market records.
    raw_category = raw.get("categoria")
    if raw_category and raw_category not in VALID_CATEGORIES:
        return None, "excluded_non_market_category"
    if raw_category == "misto":
        # A generic category alone does not prove that a sagra/festival is a
        # market. Require an explicit market-related title before publishing.
        title = nome.lower()
        if not any(word in title for word in ("mercat", "market", "antiquar", "collezion", "brocant", "vintage", "fiera antiquaria")):
            return None, "generic_without_market_evidence"

    slug = safe_string(raw.get("slug"), 130) or slugify(nome + "-" + citta)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        slug = slugify(nome + "-" + citta)
    if not slug:
        return None, "invalid_id"

    lat, lng, position_quality = parse_location(raw)
    status = raw.get("status") if raw.get("status") in VALID_STATUSES else "non_confermato"
    if status == "attivo" and not raw.get("verificato_il"):
        status = "non_confermato"
    category = raw.get("categoria") if raw.get("categoria") in VALID_CATEGORIES else "misto"
    source_calendar = clean_source_calendar(raw.get("calendario_fonte"), raw, today=today)
    if raw.get("calendario_fonte") is not None and source_calendar is None:
        return None, "invalid_source_calendar"
    use_source_calendar = bool(source_calendar and not raw.get("verificato_il")
                               and raw.get("date_quality") != "confermata")
    future_dates = (source_calendar_dates(source_calendar, raw, today=today)
                    if use_source_calendar else parse_dates(raw.get("date"), today))
    exceptions = clean_exceptions(raw.get("eccezioni_calendario"), raw, today=today)
    excluded_dates = {item["data"] for item in exceptions}
    future_dates = [value for value in future_dates if value not in excluded_dates]
    quality = raw.get("date_quality", "sconosciuta")
    if quality not in VALID_DATE_QUALITY:
        quality = "sconosciuta"
    if use_source_calendar:
        quality = "riportata"
    source_scope = calendar_scope(raw)
    scope_filtered = False
    if quality not in {"confermata", "riportata"} and not raw.get("verificato_il") and source_scope:
        retained = filter_dates(future_dates, source_scope)
        scope_filtered = retained != future_dates or not retained
        future_dates = retained
    # A record with no upcoming occurrence cannot advertise a planned or
    # confirmed future date. Preserve source/verification provenance, but
    # avoid promising dates that are absent or already in the past.
    if not future_dates:
        quality = "sconosciuta"

    confidence = raw.get("confidence", 0)
    try:
        confidence = int(confidence)
    except (ValueError, TypeError):
        confidence = 0
    confidence = max(0, min(confidence, 100))
    raw_tags = raw.get("tags") or []
    tags = sorted({safe_string(tag, 60) for tag in raw_tags if isinstance(tag, str)}) if isinstance(raw_tags, list) else []
    source = safe_string(raw.get("fonte") or raw.get("fonte_nome"), 100)
    source_url = sanitize_url(raw.get("url_fonte"))
    evidence = raw.get("fonti")
    evidence = evidence if isinstance(evidence, list) else []
    clean_sources = []
    for source_record in evidence:
        if not isinstance(source_record, dict):
            continue
        clean_sources.append({
            "nome": safe_string(source_record.get("nome"), 100),
            "url": sanitize_url(source_record.get("url")),
        })
    if source or source_url:
        primary = {"nome": source, "url": source_url}
        if primary not in clean_sources:
            clean_sources.append(primary)
    clean_sources = sorted(clean_sources, key=lambda record: (record["nome"], record["url"]))
    hours = preserve_hours_text(raw.get("orario_testo"))
    # No time and no part of the day: another column's value ("NA" = the Napoli
    # province code, "Gratis"), not hours.
    if not HOURS_CONTENT.search(hours):
        hours = ""
    completeness = 25  # name + city + valid Italian region
    completeness += 15 if raw.get("indirizzo") else 0
    completeness += 15 if lat is not None and position_quality == "precisa" else (5 if lat is not None else 0)
    completeness += 15 if future_dates else 0
    completeness += 10 if hours else 0
    completeness += 15 if source_url else 0
    completeness += 5 if raw.get("verificato_il") else 0

    result = {
        "slug": slug, "nome": nome, "citta": citta, "provincia": safe_string(raw.get("provincia"), 2),
        "regione": regione, "indirizzo": safe_string(raw.get("indirizzo"), 300),
        "lat": lat, "lng": lng, "position_quality": position_quality,
        "categoria": category, "tags": tags, "status": status,
        "orario_testo": hours,
        "ricorrenza_testo": safe_string(raw.get("ricorrenza_testo"), 180),
        "descrizione": SITE_FOOTER.sub("", safe_string(raw.get("descrizione"), 900)),
        "date": future_dates,
        "date_quality": quality,
        "proiezione_regola": raw.get("proiezione_regola") if isinstance(raw.get("proiezione_regola"), dict) else None,
        "proiezione_generata_il": safe_string(raw.get("proiezione_generata_il"), 10),
        "proiezione_fonte": safe_string(raw.get("proiezione_fonte"), 45),
        "confidence": confidence,  # Legacy field; not a verification probability.
        "completezza": completeness,
        "fonte": source, "url_fonte": source_url,
        "fonti": clean_sources,
        "verificato_il": safe_string(raw.get("verificato_il"), 35),
        "aggiornato_il": safe_string(raw.get("aggiornato_il"), 35),
    }
    # Scope=dataset means a bulk publisher update is not proof that this
    # particular market was inspected or confirmed.
    if raw.get("aggiornamento_ambito") == "dataset":
        result["aggiornamento_ambito"] = "dataset"
    if raw.get("id_fonte"):
        result["id_fonte"] = safe_string(raw.get("id_fonte"), 40)
    # Soft merge: the copy keeps its ID (favourites, receipts) but the app
    # shows only the kept record. Checked against the whole export in prepare().
    if raw.get("duplicato_di"):
        result["duplicato_di"] = safe_string(raw.get("duplicato_di"), 130)
    identity = retained_identity(raw)
    if identity is not None:
        result["identita_fonte"] = identity
    # No upcoming date left (e.g. a season just ended): no projection either, or
    # the next night's forecast gate sees a projected record that is not "prevista".
    # The rule itself stays in ricorrenza_testo and is re-derived every night.
    if scope_filtered or not future_dates:
        result["proiezione_regola"] = None
        result["proiezione_generata_il"] = ""
        result["proiezione_fonte"] = ""
    # Retain provenance when repairing only the displayed municipality
    # against the official ISTAT register. Never imply the event was verified.
    if raw.get("localita_ricostruita_da") in ("ISTAT comuni 2026-02-21; nome fonte e provincia",
                                             *PUBLISHED_TOWN_FIXES.values()):
        result["localita_ricostruita_da"] = raw["localita_ricostruita_da"]
        result["citta_originale"] = safe_string(raw.get("citta_originale"), 160)
    province_proof = retained_province_proof(raw, result)
    if province_proof is not None:
        result[PROVINCE_PROOF] = province_proof
    if raw.get("nome_originale"):
        result["nome_originale"] = safe_string(raw.get("nome_originale"), 160)
    # Publisher-reviewed venue and season evidence is preserved in the lazy
    # detail only. Never claim the publisher proved an individual event date.
    if raw.get("indirizzo_originale"):
        result["indirizzo_originale"] = safe_string(raw.get("indirizzo_originale"), 160)
    if raw.get("stagionalita_fonte") == "Editore: da marzo a ottobre; novembre-febbraio sospesi":
        result["stagionalita_fonte"] = raw["stagionalita_fonte"]
        result["ricorrenza_originale"] = safe_string(raw.get("ricorrenza_originale"), 180)
    if raw.get("navigazione_sospesa_motivo") == "indirizzo_e_punto_sorgente_non_riconciliati":
        result["navigazione_sospesa_motivo"] = raw["navigazione_sospesa_motivo"]
    # Every withdrawn point stays auditable, whichever general step withdrew it.
    if raw.get("coordinate_sospese_motivo") in COORDINATE_HOLDS:
        original_point = raw.get("coordinate_originali")
        if (isinstance(original_point, dict) and
                isinstance(original_point.get("lat"), (int,float)) and
                isinstance(original_point.get("lng"), (int,float))):
            result["coordinate_sospese_motivo"] = raw["coordinate_sospese_motivo"]
            result["coordinate_originali"] = {
                "lat":float(original_point["lat"]),
                "lng":float(original_point["lng"]),
            }
    position_source = clean_position_source(raw.get("posizione_fonte"), result)
    if position_source:  # street-level OpenStreetMap point (ODbL): attribution travels with it
        result["posizione_fonte"] = position_source
    if raw.get("calendario_sospeso_motivo") == "testo_sorgente_localita_concatenate":
        result["calendario_sospeso_motivo"] = "testo_sorgente_localita_concatenate"
        result["ricorrenza_originale"] = safe_string(raw.get("ricorrenza_originale"), 180)
    for field in ("importato_il", "fonte_letta_il"):
        value = safe_string(raw.get(field), 35)
        if value:
            result[field] = value
    # Entry price and practical tips the source states (vintagery.it); detail only.
    for field, limit in (("ingresso", 160), ("consigli", 900)):
        value = safe_string(raw.get(field), limit)
        if value:
            result[field] = value
    content_date = source_date_evidence(raw)
    if content_date["value"]:
        result["fonte_aggiornata_il"] = content_date["value"]
    receipts = clean_receipts(raw.get("riscontri_campi"), result, today=today)
    if receipts:
        result["riscontri_campi"] = receipts
    conflicts = clean_conflicts(raw.get(FIELD_CONFLICTS), result, today=today)
    if conflicts:
        result[FIELD_CONFLICTS] = conflicts
    if exceptions:
        result["eccezioni_calendario"] = clean_exceptions(exceptions, result, today=today)
    if source_calendar:
        result["calendario_fonte"] = clean_source_calendar(source_calendar, result, today=today)
    source_detail = clean_source_detail(raw.get("dettaglio_fonte"), result, today=today)
    if raw.get("dettaglio_fonte") is not None and source_detail is None:
        return None, "invalid_source_detail"
    if source_detail:
        result["dettaglio_fonte"] = source_detail
    result = retain_editorial_evidence(raw, result, today=today)
    stalls = stall_count(result)
    if stalls:
        result["posteggi"] = stalls
    return result, None


def stall_count(result: dict) -> int | None:
    """Stalls the source states, read from its own data already kept on the card:
    MERCap's licensed pitches (n_post_tot) or cosedicasa's exhibitors."""
    identity = result.get("identita_fonte") or {}
    facts = (result.get(EDITORIAL_EVIDENCE) or {}).get("facts") or {}
    values = [] if identity.get("scope_invalid") is True else [identity.get("n_post_tot")]
    values += [row.get("value") for row in facts.get("source_rows") or []
               if isinstance(row, dict) and row.get("field") == "exhibitors"]
    for value in values:
        text = str(value or "").strip()
        # Only a plain count: "1.100" or "3o" is not read as a number.
        if re.fullmatch(r"\d{1,4}", text) and 0 < int(text) <= 2000:
            return int(text)
    return None


def comparable_market_name(value: str) -> str:
    """Normalize harmless article/preposition variants without fuzzy guessing."""
    canonical = slugify(value).replace("-", " ")
    words = [
        word for word in canonical.split()
        if word not in {"a", "ad", "di", "da", "del", "della", "dello", "dell",
                        "dei", "degli", "delle", "al", "alla", "nel", "in"}
    ]
    return " ".join(words)


def specific_market_address(value: str) -> str:
    raw = (value or "").strip().lower()
    if not raw or len(raw) < 8:
        return ""
    if raw in {"centro", "centro storico", "centro città", "ce", "ce..."}:
        return ""
    return slugify(raw)


def source_duplicate_group(market: dict) -> tuple | None:
    market = as_published(market)  # duplicates are found on the source's own town and title
    url = market.get("url_fonte") or ""
    name = comparable_market_name(market.get("nome", ""))
    if not url or len(name) < 12:
        return None
    return (
        market.get("regione", "").casefold(),
        market.get("citta", "").casefold(),
        market.get("categoria", ""),
        url,
        name,
    )


def market_weekday_suffix(slug: str) -> str:
    match = re.search(r"-(lunedi|martedi|mercoledi|giovedi|venerdi|sabato|domenica)$", slug or "")
    return match.group(1) if match else ""


def safe_same_market(a: dict, b: dict) -> bool:
    """Never fuse different street markets or different weekday occurrences."""
    # MERCap assigns an official stable code to each market. Two different
    # codes are distinct source identities even at one street/day; grouping
    # is a UI choice, not a reason to delete a publisher record.
    if (str(a.get("slug", "")).startswith(("lo-mercap-", "bo-open-", "pg-corciano-"))
            or str(b.get("slug", "")).startswith(("lo-mercap-", "bo-open-", "pg-corciano-"))):
        return False
    suffix_a = market_weekday_suffix(a.get("slug", ""))
    suffix_b = market_weekday_suffix(b.get("slug", ""))
    # A day-specific record cannot absorb another day or a summary.
    if suffix_a != suffix_b:
        return False
    address_a = specific_market_address(a.get("indirizzo", ""))
    address_b = specific_market_address(b.get("indirizzo", ""))
    if address_a and address_b:
        if address_a != address_b:
            return False
    elif address_a or address_b:
        # A city-wide summary must not swallow one of its local street events.
        return False
    else:
        # Both vague/missing: merge only same documented weekday occurrence
        # and effectively identical point. Otherwise hold for manual review.
        suffix_a = market_weekday_suffix(a.get("slug", ""))
        suffix_b = market_weekday_suffix(b.get("slug", ""))
        if not suffix_a or suffix_a != suffix_b:
            return False
        if any(m.get("lat") is None or m.get("lng") is None for m in (a, b)):
            return False
        if abs(a["lat"] - b["lat"]) > 0.0003 or abs(a["lng"] - b["lng"]) > 0.0003:
            return False

    if a.get("position_quality") == "precisa" and b.get("position_quality") == "precisa":
        if a.get("lat") is not None and b.get("lat") is not None:
            if abs(a["lat"] - b["lat"]) > 0.002 or abs(a["lng"] - b["lng"]) > 0.002:
                return False
    return True


def data_value_score(market: dict) -> int:
    return (
        50 * bool(market.get("verificato_il"))
        + 30 * bool(market.get("date"))
        + 20 * bool(specific_market_address(market.get("indirizzo", "")))
        + 20 * (market.get("position_quality") == "precisa")
        + 10 * bool(market.get("orario_testo"))
        + min(10, len(market.get("descrizione", "")) // 100)
    )


def combine_safe_source_duplicates(records: list[dict], *, preserve_ids=None) -> tuple[list[dict], int]:
    """Merge only near-exact names from the SAME source and city.

    A shared source list URL is not enough: title and city must agree,
    and distinct specific addresses never merge automatically.
    """
    protected = frozenset(preserve_ids or ()) | frozenset(
        row["slug"] for row in records
        if row.get("riscontri_campi") or row.get("eccezioni_calendario")
        or row.get(EDITORIAL_EVIDENCE) or row.get(FIELD_CONFLICTS)
    )
    unique = []
    groups = {}
    merges = 0
    for item in records:
        # Normalized field/cancellation evidence belongs to this exact ID.
        # Keep protected rows out of both sides of duplicate matching.
        if item["slug"] in protected:
            unique.append(item)
            continue
        group = source_duplicate_group(item)
        found = None
        for index in groups.get(group, []) if group else []:
            if safe_same_market(unique[index], item):
                found = index
                break
        if found is None:
            index = len(unique)
            unique.append(item)
            if group:
                groups.setdefault(group, []).append(index)
            continue

        old = unique[found]
        better = item if data_value_score(item) > data_value_score(old) else old
        merged = {**old, **better}
        # The street-position step's fields describe the kept point: never mix two records'.
        for field in ("posizione_fonte", "coordinate_sospese_motivo", "coordinate_originali"):
            if field not in better and old.get("coordinate_sospese_motivo") not in COORDINATE_HOLDS - RESOLVER_HOLDS:
                merged.pop(field, None)
        merged["slug"] = old["slug"]  # stable bookmark identifier
        merged["date"] = sorted(set(old.get("date", []) + item.get("date", [])))
        merged["tags"] = sorted(set(old.get("tags", []) + item.get("tags", [])))
        links = old.get("fonti", []) + item.get("fonti", [])
        merged["fonti"] = sorted(
            { (src.get("nome",""), src.get("url","")) for src in links if isinstance(src, dict) }
        )
        merged["fonti"] = [{"nome": n, "url": u} for n, u in merged["fonti"]]
        # Never upgrade a date from estimated to confirmed by merging estimates.
        order = {"sconosciuta": 0, "prevista": 1, "riportata": 2, "confermata": 3}
        merged["date_quality"] = min(
            (old.get("date_quality", "sconosciuta"),
             item.get("date_quality", "sconosciuta")),
            key=lambda quality: order.get(quality, 0),
        )
        merged["completezza"] = max(old.get("completezza", 0), item.get("completezza", 0))
        unique[found] = merged
        merges += 1
    return unique, merges


def twin_key(row: dict) -> tuple:
    """Records with equal keys are the same market from the same source row."""
    row = as_published(row)
    return (row.get("fonte"), row.get("url_fonte"), row.get("id_fonte") or "",
            row.get("regione"), str(row.get("citta") or "").casefold(),
            comparable_market_name(str(row.get("nome") or "")), slugify(row.get("indirizzo") or ""),
            row.get("orario_testo") or "", str(row.get("ricorrenza_testo") or "").casefold(),
            tuple(row.get("date") or []))


def venue_slot(row: dict) -> tuple | None:
    """Region, town and calendar of a market at a real street (None when any is unknown)."""
    from catalog_quality_report import VAGUE_ADDRESSES, key
    from recurrence_refresh import calendar_key, forecast_rule
    street = str(row.get("indirizzo") or "").strip()
    if not street or key(street) in VAGUE_ADDRESSES or len(slugify(street)) < 6:
        return None
    rule = forecast_rule(row)
    row = as_published(row)
    if rule:
        calendar = calendar_key(rule)
    else:
        days = tuple(sorted({date.fromisoformat(d).weekday() for d in row.get("date") or []}))
        if not days:
            return None
        calendar = ("dates", days, None)
    return (row.get("regione"), slugify(row.get("citta") or ""), calendar)


STREET_PARTS = re.compile(r"\s*(?:[,;(/]|\s-\s|\s(?:e|ed|o)\s)\s*", re.I)


def street_names(row: dict) -> set:
    """(type, distinctive words) of each street an address names:
    "Via Sorte, Via Rampinelli" -> {("via", {"sorte"}), ("via", {"rampinelli"})}."""
    town = distinctive_words(as_published(row).get("citta") or "")
    names = set()
    for part in STREET_PARTS.split(str(row.get("indirizzo") or "")):
        kind, words = street_type(part.strip()), frozenset(distinctive_words(part) - town)
        if kind and words:
            names.add((kind, words))
    return names


def shares_street(a: dict, b: dict) -> bool:
    """Both addresses name one street, spelled either way: "piazza G. Rossa" is
    "Piazza Guido Rossa"; "Piazza Roma" is not "Via Roma", and "Piazza della Chiesa"
    is not "Piazza Dalla Chiesa" (a shorter name must keep a real name word)."""
    return (slugify(a.get("indirizzo") or "") == slugify(b.get("indirizzo") or "")
            or any(ka == kb and (wa == wb or (wa < wb or wb < wa) and min(wa, wb, key=len) - GENERIC_PLACE)
                   for ka, wa in street_names(a) for kb, wb in street_names(b)))


def dayparts(row: dict) -> set:
    """Parts of the day ("mattina", "pomeriggio") the hours start in or name; empty if unknown."""
    text = str(row.get("orario_testo") or "").casefold()
    parts = {"mattina" if int(h) < 12 else "pomeriggio"
             for h in re.findall(r"\b(\d{1,2})[:.]\d\d", text)[::2]}
    return parts | {part for stem, part in (("mattin", "mattina"), ("pomerigg", "pomeriggio"),
                                            ("sera", "pomeriggio")) if stem in text}


def same_venue(a: dict, b: dict) -> bool:
    """Same town, calendar and street, and times of day that don't contradict each other
    ("La mattina" vs "13:00–19:00" may be a second, afternoon market)."""
    slot, pa, pb = venue_slot(a), dayparts(a), dayparts(b)
    return (slot is not None and slot == venue_slot(b) and not (pa and pb and not pa & pb)
            and shares_street(a, b))


def same_market(kept: dict, copy: dict) -> bool:
    """The one definition of a soft-merged copy, shared by export, enrichment and checks."""
    if twin_key(kept) == twin_key(copy):
        return True
    return kept.get("fonte") != copy.get("fonte") and same_venue(kept, copy)


def soft_merge_markers(rows: list[dict]) -> tuple[dict[str, str], Counter]:
    """{copy: kept} for every source: identical records, then the same venue and
    calendar listed by different sources. IDs stay; the app shows the kept one."""
    kept_ids = {r["duplicato_di"] for r in rows if r.get("duplicato_di")}
    markers, counts = {}, Counter()
    def merge(groups, label, one_per_source):
        for group in groups.values():
            # Two records already kept for other copies cannot fold into each other;
            # two different records of one source at one venue are ambiguous.
            if (len(group) < 2 or sum(r["slug"] in kept_ids for r in group) > 1
                    or one_per_source and len({r.get("fonte") for r in group}) != len(group)):
                continue
            kept = max(group, key=lambda r: (r["slug"] in kept_ids, data_value_score(r),
                                             -len(r["slug"]), r["slug"]))
            if not kept.get("date") and any(r.get("date") for r in group):
                continue  # never hide the only cards with upcoming dates
            markers.update({r["slug"]: kept["slug"] for r in group if r is not kept})
            kept_ids.add(kept["slug"])  # never becomes a copy later: no chains
            counts[label] += len(group) - 1
    twins, venues = defaultdict(list), defaultdict(list)
    for row in rows:
        if not row.get("duplicato_di"):
            twins[twin_key(row)].append(row)
    merge(twins, "exact_twins", False)
    slots = defaultdict(list)
    for row in rows:
        if not row.get("duplicato_di") and row["slug"] not in markers and (slot := venue_slot(row)):
            slots[slot].append(row)
    for slot, group in slots.items():
        while group:
            venue = [group.pop(0)]
            for row in venue:  # grows while read: every record linked by a shared street
                linked = [other for other in group if shares_street(row, other)]
                venue += linked
                group = [other for other in group if other not in linked]
            # Only when every pair is the same venue: a chain ("Via A" / "Via A, Via B" /
            # "Via B") or clashing times of day stay separate cards.
            if all(same_venue(a, b) for a, b in combinations(venue, 2)):
                venues[(slot, venue[0]["slug"])] = venue
    merge(venues, "same_venue_other_source", True)
    return markers, counts


def _host(url) -> str:
    try:
        return urlsplit(str(url or "")).netloc.lower().removeprefix("www.")
    except ValueError:  # a malformed source URL ("http://[") has no host
        return ""


def own_source_last_read(row: dict, page_reads=None) -> str:
    """Last day the market's OWN source was read; proofs from other sites don't count."""
    own = _host(row.get("url_fonte"))
    evidence = row.get(EDITORIAL_EVIDENCE) if isinstance(row.get(EDITORIAL_EVIDENCE), dict) else {}
    days = [str(row.get("fonte_letta_il") or "")[:10], (page_reads or {}).get(row.get("url_fonte"), ""),
            str(evidence.get("read_on") or "")[:10]]
    days += [str(r.get("letto_il") or "")[:10] for r in row.get("riscontri_campi") or []
             if isinstance(r, dict) and _host(r.get("url")) == own]
    return max((d for d in days if re.fullmatch(r"\d{4}-\d\d-\d\d", d)), default="")


CONCLUDED_UNREAD_DAYS = 90


def concluded_reason(row: dict, today: date, source_reads=None) -> str:
    """Why a market is no longer scheduled ("" if it still is). Same rule for every source:
    no upcoming date, no recurrence that can produce one, and either its own source shows
    the edition is over or nobody has re-read that source for CONCLUDED_UNREAD_DAYS.
    No upcoming date and its own complete weekly page listing the town only on other
    weekdays (field_conflicts.delisted_weekday) is "non_piu_elencato".
    An official dataset entry counts as unread only while the dataset itself is still
    read for other markets (it dropped this one); a dataset nobody re-reads keeps its
    venues. source_reads: {fonte: last day any of its markets was read}."""
    from recurrence_refresh import forecast_rule
    from field_conflicts import delisted_weekday
    if any(str(d) >= today.isoformat() for d in row.get("date") or []):
        return ""
    # Its own complete weekly page lists the town only on other days: the
    # weekday text can no longer produce a date.
    if not row.get("verificato_il") and delisted_weekday(row, today=today):
        return "non_piu_elencato"
    if forecast_rule(row):
        return ""
    evidence = row.get(EDITORIAL_EVIDENCE) if isinstance(row.get(EDITORIAL_EVIDENCE), dict) else {}
    facts = evidence.get("facts") if isinstance(evidence.get("facts"), dict) else {}
    editions = [i for i in facts.get("edition_intervals") or [] if isinstance(i, dict)]
    if facts.get("archive_marker") is True or editions and all(str(i.get("end")) < today.isoformat() for i in editions):
        return "edizione_conclusa"
    cutoff = (today - timedelta(days=CONCLUDED_UNREAD_DAYS)).isoformat()
    if own_source_last_read(row) < cutoff:
        if row.get("aggiornamento_ambito") == "dataset" and (source_reads or {}).get(row.get("fonte"), "") < cutoff:
            return ""
        return "fonte_non_riletta"
    return ""


# Fields the exporter derives itself (never carried over from the input).
DERIVED_FIELDS = ("concluso",)


def matches_export(expected: dict, actual: dict | None, exported_by_id: dict) -> bool:
    """A normalize() result equals its exported record, allowing export-derived fields."""
    if actual is None:
        return False
    kept = exported_by_id.get(actual.get("duplicato_di"))
    dropped = set(DERIVED_FIELDS)
    if "duplicato_di" not in expected and kept is not None and same_market(kept, actual):
        dropped.add("duplicato_di")
    return expected == {k: v for k, v in actual.items() if k not in dropped}


def prepare(raw_records: list, today: date, *, preserve_ids=None) -> tuple[list[dict], dict]:
    if preserve_ids is not None and (
            not isinstance(preserve_ids, (set, frozenset))
            or any(not isinstance(sid, str) or not sid for sid in preserve_ids)):
        raise ValueError("Protected market IDs must be a set of nonempty source identifiers")
    protected = set(preserve_ids or ())
    for raw in raw_records:
        if isinstance(raw, dict) and (
                clean_receipts(raw.get("riscontri_campi"), raw, today=today)
                or clean_exceptions(raw.get("eccezioni_calendario"), raw, today=today)
                or clean_conflicts(raw.get(FIELD_CONFLICTS), raw, today=today)
                or clean_editorial_evidence(raw.get(EDITORIAL_EVIDENCE), raw, today=today)):
            # Protect before normalization/collision handling: changing the
            # slug of a valid source claim would silently lose its proof.
            protected.add(str(raw.get("slug") or ""))
    cleaned = []
    skipped = Counter()
    by_slug = {}
    collisions = []
    for raw in raw_records:
        result, error = normalize(raw, today)
        if error:
            skipped[error] += 1
            continue
        slug = result["slug"]
        if (result.get("riscontri_campi") or result.get("eccezioni_calendario")
                or result.get(EDITORIAL_EVIDENCE) or result.get(FIELD_CONFLICTS)):
            protected.add(slug)
        if slug in by_slug:
            if slug in protected:
                raise ValueError("Repeated protected market identifier: " + slug)
            current = by_slug[slug]
            if result == current:
                skipped["exact_duplicate"] += 1
                continue
            # Do not erase two different markets sharing the same name/city.
            addr1 = slugify(current["indirizzo"])
            addr2 = slugify(result["indirizzo"])
            if addr1 and addr2 and addr1 != addr2:
                suffix = hashlib.sha256((result["indirizzo"] + result["url_fonte"]).encode()).hexdigest()[:8]
                slug = slug + "-" + suffix
                if slug in by_slug:
                    raise ValueError("Unresolvable market identifier collision: " + slug)
                result["slug"] = slug
                collisions.append(slug)
            else:
                # Conflicting versions of the same market require review.
                raise ValueError("Conflicting records with the same identifier: " + slug)
        by_slug[slug] = result
        cleaned.append(result)

    if protected - by_slug.keys():
        lost = sorted(protected - by_slug.keys())
        raise ValueError("Export normalization removed or changed protected market identifiers: "
                         + ", ".join(lost[:10]) + f" ({len(lost)}; skipped: {dict(skipped)})")
    cleaned, safe_merged = combine_safe_source_duplicates(cleaned, preserve_ids=protected)
    merged, merge_counts = soft_merge_markers(cleaned)
    source_reads = {}
    for row in cleaned:
        source_reads[row["fonte"]] = max(source_reads.get(row["fonte"], ""), own_source_last_read(row))
    for row in cleaned:
        if row["slug"] in merged:
            row["duplicato_di"] = merged[row["slug"]]
        # Hidden, never deleted: old links and favourites still open it.
        # A copy (merged now or in an earlier run) is already hidden behind its kept record.
        elif not row.get("duplicato_di") and (reason := concluded_reason(row, today, source_reads)):
            row["concluso"] = reason
    by_id = {row["slug"]: row for row in cleaned}
    for row in cleaned:
        if "duplicato_di" not in row:
            continue
        kept = by_id.get(row["duplicato_di"])
        if (kept is None or "duplicato_di" in kept
                or kept["regione"] != row["regione"]
                # Same town, whichever source's spelling ("Torre De' Passeri" / "Torre De'Passeri").
                or slugify(as_published(kept)["citta"]) != slugify(as_published(row)["citta"])):
            raise ValueError("Soft-merged copy must point to a kept record in its town: " + row["slug"])
    for row in cleaned:
        if (row.get("riscontri_campi") and
                clean_receipts(row["riscontri_campi"], row, today=today) != row["riscontri_campi"]):
            raise ValueError("Export changed a field receipt's identity or values")
        if (row.get("eccezioni_calendario") and
                clean_exceptions(row["eccezioni_calendario"], row, today=today) != row["eccezioni_calendario"]):
            raise ValueError("Export changed a cancellation's market identity")
        if (row.get(FIELD_CONFLICTS) and
                clean_conflicts(row[FIELD_CONFLICTS], row, today=today) != row[FIELD_CONFLICTS]):
            raise ValueError("Export changed an address conflict's identity or saved value")
    cleaned.sort(key=lambda m: (m["regione"], m["citta"], m["nome"], m["slug"]))
    stats = {
        "same_source_duplicates_merged": safe_merged,
        "exact_twins_soft_merged": merge_counts["exact_twins"],
        "same_venue_other_source_soft_merged": merge_counts["same_venue_other_source"],
        "concluded_hidden": dict(Counter(m["concluso"] for m in cleaned if m.get("concluso"))),
        "input": len(raw_records), "accepted": len(cleaned), "skipped": dict(skipped),
        "id_collisions_kept_separate": collisions,
        "with_coordinates": sum(m["lat"] is not None for m in cleaned),
        "with_source_url": sum(bool(m["url_fonte"]) for m in cleaned),
        "with_future_date": sum(bool(m["date"]) for m in cleaned),
        "human_verified": sum(bool(m["verificato_il"]) for m in cleaned),
        "by_region": dict(sorted(Counter(m["regione"] for m in cleaned).items())),
    }
    return cleaned, stats


# Small index contains all fields used by list/search/map, but not full
# descriptions, long date schedules, source evidence or street addresses.
# Clicking a card fetches just one cached region's full detail JSON.
# Schema 4: compact positional rows for fast first paint on slow mobile networks.
# Full descriptive text and source metadata stay in the lazy-loaded regional file.
INDEX_FIELDS = LEGACY_FIELDS

def small_index(markets: list[dict], *, schema=5, today=None) -> list[list]:
    return project_index(markets, schema=schema, today=today)



def _write_asset(output: Path, relative: str, markets: list[dict]):
    body = compact_json({"schema": 1, "markets": markets})
    if len(body) > MAX_MARKET_BYTES:
        raise ValueError("Static asset too large: " + relative)
    digest = hashlib.sha256(body).hexdigest()[:14]
    path = "data/v1/" + relative.replace("{hash}", digest)
    target = output.parent.parent / path  # output == public/data/v1
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(body)
    return path


def export(records: list, out: Path, today: date | None = None,
           min_count: int = 1, max_drop_ratio: float = 0.20, dry_run: bool = False,
           *, preserve_ids=None):
    now = today or date.today()
    markets, stats = prepare(records, now, preserve_ids=preserve_ids)
    if len(markets) < min_count:
        raise ValueError("Quality gate: too few accepted markets: " + str(stats))

    old_manifest_file = out / "manifest.json"
    previous = None
    if old_manifest_file.is_file():
        previous = json.loads(old_manifest_file.read_text("utf-8"))
        previous_count = int(previous.get("total", 0))
        if previous_count > 0 and len(markets) < previous_count * (1 - max_drop_ratio):
            raise ValueError("Quality gate: too many markets disappeared since last export")

    signature = hashlib.sha256(compact_json(markets)).hexdigest()
    if (previous and previous.get("content_signature") == signature
            and previous.get("index_schema") == INDEX_SCHEMA
            and previous.get("index_as_of") == now.isoformat()
            and previous.get("index")
            and (out.parent.parent / previous["index"]).is_file()):
        return {"unchanged": True, "stats": stats, "manifest": previous}
    if dry_run:
        return {"unchanged": False, "stats": stats, "manifest": None}

    out.mkdir(parents=True, exist_ok=True)
    groups = {}
    for market in markets:
        groups.setdefault(market["regione"], []).append(market)

    body_size = len(compact_json({"schema": 1, "markets": markets}))
    if body_size <= MAX_SINGLE_BYTES:
        asset = _write_asset(out, "catalog-{hash}.json", markets)
        layout, part_entries = "single", {"catalog": asset}
    else:
        layout, part_entries = "regional", {"regions": []}
        for name, region_markets in sorted(groups.items()):
            file_name = "regions/" + slugify(name) + "-{hash}.json"
            path = _write_asset(out, file_name, region_markets)
            part_entries["regions"].append({"name": name, "count": len(region_markets), "path": path})

    # One lightweight global index fetch on page load; full regional datasets
    # are immutable and fetched only when a market detail is opened.
    index_path = _write_asset(out, "index-{hash}.json", small_index(markets, schema=INDEX_SCHEMA, today=now))

    manifest = {
        "schema": 1, "layout": layout, "total": len(markets),
        "index": index_path,
        "index_schema": INDEX_SCHEMA,
        "index_as_of": now.isoformat(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "content_signature": signature,
        "regions_summary": stats["by_region"],
        "quality": {
            "coordinate_count": stats["with_coordinates"],
            "dated_count": stats["with_future_date"],
            "source_url_count": stats["with_source_url"],
            "verified_count": stats["human_verified"],
        },
        **part_entries,
    }
    # Publish last: clients never see the new manifest before its files exist.
    temporary = old_manifest_file.with_suffix(".json.tmp")
    temporary.write_bytes(compact_json(manifest))
    temporary.replace(old_manifest_file)
    return {"unchanged": False, "stats": stats, "manifest": manifest}


def _from_firestore() -> list:
    # Read once during export, never on an end-user page request.
    import firebase_admin
    from firebase_admin import credentials, firestore
    import os
    if not firebase_admin._apps:
        path = os.getenv("FIREBASE_CREDENTIALS_PATH", "backend/serviceAccountKey.json")
        if Path(path).exists():
            firebase_admin.initialize_app(credentials.Certificate(path))
        else:
            firebase_admin.initialize_app()  # Application Default Credentials
    return [snapshot.to_dict() for snapshot in firestore.client().collection("mercati").stream()]


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path)
    source.add_argument("--firestore", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("public/data/v1"))
    parser.add_argument("--min-count", type=int, default=1)
    parser.add_argument("--max-drop-ratio", type=float, default=0.20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.min_count < 1 or not 0 <= args.max_drop_ratio < 1:
        parser.error("Invalid quality gate thresholds")

    records = _from_firestore() if args.firestore else json.loads(args.input.read_text("utf-8"))
    if isinstance(records, dict) and isinstance(records.get("markets"), list):
        records = records["markets"]
    if not isinstance(records, list):
        parser.error("Source must contain a list of markets")
    report = export(records, args.out, min_count=args.min_count,
                    max_drop_ratio=args.max_drop_ratio, dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print("Export blocked: " + str(exc), file=sys.stderr)
        sys.exit(1)
