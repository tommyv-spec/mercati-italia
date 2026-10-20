"""Bounded negative field evidence; never a replacement or positive receipt.

This module validates an already associated, explicit source contradiction.
The producer/release guard must separately reconstruct that association from
captured HTML and the complete catalogue. A matching envelope does not prove
that the alternative address is current, that a market opens, or that its GPS
is correct. The warning expires by binding when the saved identity/address
changes, not merely because time has passed since the source was read.
"""
from __future__ import annotations

import json
import re
from copy import deepcopy
from datetime import date

from field_evidence import as_day, safe_url
from happings_weekly_layout import fold, province_page_key
from stored_market_sibling_proposals import safe_stored_street

KEY = "conflitti_campi"
MANAGER = "happings-weekly"
MAX_CONFLICTS = 3
MAX_ADDRESS_LENGTH = 190
MAX_FRAGMENT_LENGTH = 1200
MAX_SOURCE_BYTES = 2_600_000
IDENTITY_LIMITS = {
    "slug": 130, "nome": 160, "citta": 120, "provincia": 2,
    "regione": 80, "fonte": 100, "url_fonte": 650,
}
ENVELOPE_KEYS = {
    "schema", "gestore", "campo", "mercato", "valore_catalogo", "valore_fonte",
    "giorno_settimana", "url_richiesto", "url_finale", "letto_il", "sha256",
    "bytes", "prova",
}
PROOF_KEYS = {"tipo", "selettore", "frammento", "sede_precedente", "sede_attuale"}
REPLACEMENT_NOTICE = "queste indicazioni sostituiscono i vecchi riferimenti"
SELECTOR = re.compile(
    r"main#main article\.hpe-editorial--local-guide \.hpe-editorial-grid"
    r" > \.hpe-editorial-body > p:nth-child\(([1-9][0-9]{0,2})\)"
)


def _text(value, limit):
    return bool(isinstance(value, str) and 0 < len(value) <= limit
                and value == " ".join(value.split())
                and not any(ord(char) < 32 or ord(char) == 127 for char in value))


def conflict_identity(row):
    """Exact saved identity, including the original primary source and name."""
    return {key: row.get(key) for key in IDENTITY_LIMITS}


def valid_conflict(item, row, *, today):
    """Validate structure/value binding only; never infer an association."""
    if (type(today) is not date or not isinstance(row, dict)
            or not isinstance(item, dict) or set(item) != ENVELOPE_KEYS
            or type(item.get("schema")) is not int or item["schema"] != 1
            or item.get("gestore") != MANAGER or item.get("campo") != "indirizzo"):
        return False
    market = item.get("mercato")
    if (not isinstance(market, dict) or set(market) != set(IDENTITY_LIMITS)
            or market != conflict_identity(row)
            or any(not _text(market[key], limit) for key, limit in IDENTITY_LIMITS.items())
            or not re.fullmatch(r"[A-Z]{2}", market["provincia"])
            or not safe_url(market["url_fonte"])):
        return False
    saved, source = item.get("valore_catalogo"), item.get("valore_fonte")
    if (saved != row.get("indirizzo")
            or not _text(saved, MAX_ADDRESS_LENGTH) or not _text(source, MAX_ADDRESS_LENGTH)
            or not safe_stored_street(saved) or not safe_stored_street(source)
            or fold(saved) == fold(source)):
        return False
    if (type(item.get("giorno_settimana")) is not int
            or not 0 <= item["giorno_settimana"] <= 6
            or type(item.get("bytes")) is not int or not 1 <= item["bytes"] <= MAX_SOURCE_BYTES
            or not isinstance(item.get("sha256"), str)
            or not re.fullmatch(r"[a-f0-9]{64}", item["sha256"])):
        return False
    read = as_day(item.get("letto_il"))
    if read is None or read > today:
        return False
    requested, final = item.get("url_richiesto"), item.get("url_finale")
    if (not _text(requested, 650) or not _text(final, 650)
            or not province_page_key(requested)
            or province_page_key(requested) != province_page_key(final)):
        return False
    proof = item.get("prova")
    if (not isinstance(proof, dict) or set(proof) != PROOF_KEYS
            or proof.get("tipo") != "sostituzione_sede_esplicita"
            or proof.get("sede_precedente") != saved
            or proof.get("sede_attuale") != source
            or not _text(proof.get("selettore"), 200)
            or not _text(proof.get("frammento"), MAX_FRAGMENT_LENGTH)):
        return False
    selector = SELECTOR.fullmatch(proof["selettore"])
    if selector is None or int(selector.group(1)) > 200:
        return False
    # Only the reviewed explicit replacement wording is representable now.
    # A mere different address or a historical row cannot create a warning.
    fragment = fold(proof["frammento"])
    if fragment.count(REPLACEMENT_NOTICE) != 1:
        return False
    current, replaced = fragment.split(REPLACEMENT_NOTICE)
    return (" " + fold(source) + " " in " " + current + " "
            and " " + fold(saved) + " " in " " + replaced + " ")


def clean_conflicts(value, row, *, today):
    """Retain only bound, bounded warnings, without mutating their inputs."""
    if not isinstance(value, list) or len(value) > MAX_CONFLICTS:
        return []
    distinct = {}
    for item in value:
        if valid_conflict(item, row, today=today):
            canonical = json.dumps(item, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            distinct[canonical] = deepcopy(item)
    return sorted(distinct.values(), key=lambda item: (
        item["letto_il"], item["url_finale"], item["sha256"],
        item["valore_fonte"], item["prova"]["selettore"], item["prova"]["frammento"],
    ), reverse=True)


def make_address_conflict(row, *, source_value, source_day, requested_url,
                          final_url, read_on, html_sha256, source_bytes,
                          selector, fragment, today):
    """Build only from an independently proved exact source/market association."""
    item = {
        "schema": 1, "gestore": MANAGER, "campo": "indirizzo",
        "mercato": conflict_identity(row), "valore_catalogo": row.get("indirizzo"),
        "valore_fonte": source_value, "giorno_settimana": source_day,
        "url_richiesto": requested_url, "url_finale": final_url,
        "letto_il": str(read_on), "sha256": html_sha256, "bytes": source_bytes,
        "prova": {
            "tipo": "sostituzione_sede_esplicita", "selettore": selector,
            "frammento": fragment, "sede_precedente": row.get("indirizzo"),
            "sede_attuale": source_value,
        },
    }
    if not valid_conflict(item, row, today=today):
        raise ValueError("Address conflict lacks exact bound explicit source replacement evidence")
    return item
