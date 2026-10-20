#!/usr/bin/env python3
"""Field-specific publisher observations, separate from event confirmation.

An observation binds an existing identity and exact field values to a source
row/page, a real read date and a content fingerprint. It is invalidated when
identity or values change. Reading an old document never makes it current.
No observation in this module confirms a future opening or a map position.
"""
from __future__ import annotations

import hashlib
import json
import re
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date
from urllib.parse import urlsplit
from source_hours import MAX_HOURS_TEXT_LENGTH

FIELDS = {"indirizzo": 300, "orario_testo": MAX_HOURS_TEXT_LENGTH, "ricorrenza_testo": 180}
LABELS = {"indirizzo": "sede", "orario_testo": "orari", "ricorrenza_testo": "giorni"}
SOURCE_AGE = {"indirizzo": 365, "orario_testo": 180, "ricorrenza_testo": 180}
MAX_READ_AGE = 45
MAX_RECEIPTS = 6
MAX_MANAGED_HISTORY = 6
MANAGER_ID = re.compile(r"[a-z][a-z0-9_-]{0,63}")
FEED_IDS = {"milano", "firenze", "lombardia", "corciano", "bologna"}
METHODS = {"id_fonte", "sede_giorno_provincia", "pagina_primaria_revisionata",
           "comune_provincia_giorno_univoco"}
FINGERPRINT_KINDS = {"publisher_parsed_json", "reviewed_factual_excerpt", "web_extracted_text",
                     "html_bytes", "pdf_bytes"}
RECEIPT_KEYS = {"schema", "mercato", "valori", "url", "fonte", "fonte_id", "riga_fonte",
                "letto_il", "fonte_aggiornata_il", "sha256", "impronta_tipo", "ambito", "metodo",
                "campi_gestiti", "gestore_campi"}


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def identity(row):
    return {k: str(row.get(k) or "") for k in ("slug", "citta", "provincia", "regione")}


def as_day(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        return None


def safe_url(value):
    if not isinstance(value, str) or not 8 < len(value) <= 1200:
        return False
    try:
        u = urlsplit(value)
        return bool(u.scheme == "https" and u.hostname and not u.username and
                    not u.password and u.port in (None, 443) and not u.fragment)
    except ValueError:
        return False


def _managed_fields(receipt):
    """Ownership is explicit and never inferred from a coincident value."""
    fields = receipt.get("campi_gestiti")
    manager = receipt.get("gestore_campi")
    if (not isinstance(fields, list) or not fields or len(fields) > len(FIELDS)
            or not isinstance(manager, str) or not MANAGER_ID.fullmatch(manager)
            or any(not isinstance(field, str) or field not in FIELDS for field in fields)
            or len(set(fields)) != len(fields)):
        return set()
    return set(fields) & set(receipt.get("valori") or {})


def _provenance_key(receipt):
    return tuple(receipt.get(key) for key in
                 ("fonte_id", "url", "riga_fonte", "metodo", "ambito")) + (
        receipt.get("impronta_tipo", "publisher_parsed_json"),)


def _clean_management(receipt):
    fields = _managed_fields(receipt)
    if not fields:
        for key in ("campi_gestiti", "gestore_campi", "versioni_precedenti"):
            receipt.pop(key, None)
        return receipt
    receipt["campi_gestiti"] = sorted(fields)
    history = []
    seen = set()
    prior = receipt.get("versioni_precedenti")
    if isinstance(prior, list):
        for raw in prior[:MAX_MANAGED_HISTORY]:
            if not isinstance(raw, dict):
                continue
            item = {key: deepcopy(value) for key, value in raw.items() if key in RECEIPT_KEYS}
            if not isinstance(item.get("valori"), dict):
                continue
            item["valori"] = {key: value for key, value in item["valori"].items() if key in fields}
            item["campi_gestiti"] = sorted(_managed_fields(item))
            historical_row = {**(receipt.get("mercato") or {}), **item["valori"]}
            if (not item["campi_gestiti"]
                    or item.get("mercato") != receipt.get("mercato")
                    or item.get("gestore_campi") != receipt.get("gestore_campi")
                    or _provenance_key(item) != _provenance_key(receipt)
                    or not valid_receipt(item, historical_row, today=as_day(receipt.get("letto_il")))
                    or item["letto_il"] >= receipt.get("letto_il", "")):
                continue
            key = (item["letto_il"], item["sha256"], fingerprint(item["valori"]))
            if key not in seen:
                history.append(item)
                seen.add(key)
    if history:
        receipt["versioni_precedenti"] = sorted(history, key=lambda x: x["letto_il"], reverse=True)
    else:
        receipt.pop("versioni_precedenti", None)
    return receipt


def _carry_management(winner, earlier):
    """A same-value reread preserves ownership, but cannot create it."""
    if (_provenance_key(winner) != _provenance_key(earlier)
            or not _source_date_not_regressed(earlier, winner)):
        return winner
    transferable = {field for field in _managed_fields(earlier)
                    if field in winner["valori"] and
                    winner["valori"][field] == earlier["valori"].get(field)}
    if not transferable:
        return winner
    current = _managed_fields(winner)
    if current and winner.get("gestore_campi") != earlier.get("gestore_campi"):
        return winner
    winner["gestore_campi"] = earlier["gestore_campi"]
    winner["campi_gestiti"] = sorted(current | transferable)
    history = list(winner.get("versioni_precedenti") or [])
    history.extend(earlier.get("versioni_precedenti") or [])
    if history:
        winner["versioni_precedenti"] = history[:MAX_MANAGED_HISTORY]
    return _clean_management(winner)


def _source_date_not_regressed(previous, future):
    old_date = as_day(previous.get("fonte_aggiornata_il"))
    new_date = as_day(future.get("fonte_aggiornata_il"))
    return not old_date or bool(new_date and new_date >= old_date)


def _later_source_version(previous, future):
    """Both inputs have already passed exact-value receipt validation."""
    return bool(_provenance_key(previous) == _provenance_key(future)
                and future["letto_il"] > previous["letto_il"]
                and future["sha256"] != previous["sha256"]
                and _source_date_not_regressed(previous, future))


def retire_superseded_receipts(row, next_receipt, *, today):
    """Retire only source claims contradicted by its proven newer version.

    The caller first establishes the same source/market identity. This never
    changes field values or removes claims from another source. Keep the old
    receipt in the caller's conflict report when an update is held. Unchanged
    fields in a mixed receipt retain their original, accurately dated proof.
    """
    prior = clean_receipts(row.get("riscontri_campi"), row, today=today)
    if not isinstance(next_receipt, dict) or not isinstance(next_receipt.get("valori"), dict):
        return prior
    proposed = {**row, **{field: value for field, value in next_receipt["valori"].items()
                         if field in FIELDS}}
    prospective = clean_receipts([next_receipt], proposed, today=today)
    if not prospective:
        return prior
    future = prospective[0]
    kept = []
    for receipt in prior:
        if _later_source_version(receipt, future):
            receipt["valori"] = {
                field: value for field, value in receipt["valori"].items()
                if field not in future["valori"] or future["valori"][field] == value
            }
        kept.append(receipt)
    return clean_receipts(kept, row, today=today)


def managed_update_allowed(row, next_receipt, field, *, manager, today):
    """Permit replacing only an exact value previously assigned by manager.

    The caller must first prove stable market/source identity independently.
    Scope the proposed receipt to the target identity after that join. This
    helper handles each of the three public fields independently, requires a
    later real read and changed content hash, and rejects publisher-date
    regression or competing source/manual evidence. Same-day rereads cannot
    establish ordering with the current date-only observation schema.
    """
    if (field not in FIELDS or not isinstance(manager, str) or not MANAGER_ID.fullmatch(manager)
            or not isinstance(today, date) or not isinstance(row, dict)
            or row.get("verificato_il") or not isinstance(next_receipt, dict)):
        return False
    values = next_receipt.get("valori")
    if not isinstance(values, dict) or field not in values:
        return False
    current, incoming = row.get(field), values[field]
    if not isinstance(current, str) or not current.strip() or incoming == current:
        return False
    proposed = {**row, field: incoming}
    prospective = clean_receipts([next_receipt], proposed, today=today)
    if not prospective or prospective[0]["valori"].get(field) != incoming:
        return False
    future = prospective[0]
    read = as_day(future["letto_il"])
    if (today - read).days > MAX_READ_AGE:
        return False
    prior = [receipt for receipt in clean_receipts(row.get("riscontri_campi"), row, today=today)
             if field in receipt["valori"]]
    if (not prior or any(_provenance_key(receipt) != _provenance_key(future) for receipt in prior)):
        return False
    owned = [receipt for receipt in prior if field in _managed_fields(receipt)
             and receipt.get("gestore_campi") == manager]
    if not owned:
        return False
    previous = max(owned, key=lambda receipt: receipt["letto_il"])
    return bool(future["letto_il"] > max(receipt["letto_il"] for receipt in prior)
                and _later_source_version(previous, future))


def mark_managed_fields(receipt, fields, *, manager, previous=None):
    """Mark actual engine assignments; never call this for a no-op match.

    Pass the prior market row when replacing an allowed managed value. The
    previous source proof is retained as bounded, nonrecursive history.
    A receipt merely observing a pre-existing field gains no ownership.
    """
    if (not isinstance(receipt, dict) or not isinstance(manager, str)
            or not MANAGER_ID.fullmatch(manager)
            or (previous is not None and not isinstance(previous, dict))):
        raise ValueError("Invalid field manager or receipt")
    requested = set(fields)
    if not requested or requested - set(FIELDS) or requested - set(receipt.get("valori") or {}):
        raise ValueError("Managed assignment fields lack exact source values")
    item = deepcopy(receipt)
    existing = _managed_fields(item)
    if existing and item.get("gestore_campi") != manager:
        raise ValueError("Cannot take over another engine's managed field")
    if previous is not None:
        for field in requested:
            if str(previous.get(field) or "").strip() and not managed_update_allowed(
                    previous, item, field, manager=manager, today=as_day(item.get("letto_il"))):
                raise ValueError("A pre-existing field lacks managed update authorization")
    item["gestore_campi"] = manager
    item["campi_gestiti"] = sorted(existing | requested)
    history = list(item.get("versioni_precedenti") or [])
    if isinstance(previous, dict):
        for old in clean_receipts(previous.get("riscontri_campi"), previous,
                                  today=as_day(item.get("letto_il"))):
            fields = requested & _managed_fields(old)
            if (not fields or old.get("gestore_campi") != manager
                    or _provenance_key(old) != _provenance_key(item)):
                continue
            entry = {key: deepcopy(value) for key, value in old.items() if key in RECEIPT_KEYS}
            entry["valori"] = {field: old["valori"][field] for field in fields}
            entry["campi_gestiti"] = sorted(fields)
            history.insert(0, entry)
            history.extend(old.get("versioni_precedenti") or [])
    if history:
        item["versioni_precedenti"] = history[:MAX_MANAGED_HISTORY]
    return _clean_management(item)


def make_receipt(row, *, values, source_url, source_name, source_id,
                 source_row, read_on, source_updated_on, source_sha256,
                 scope="dataset", method="id_fonte", fingerprint_kind="publisher_parsed_json"):
    receipt = {
        "schema": 1, "mercato": identity(row), "valori": dict(values),
        "url": source_url, "fonte": source_name, "fonte_id": source_id,
        "riga_fonte": str(source_row), "letto_il": str(read_on),
        "fonte_aggiornata_il": str(source_updated_on or ""),
        "sha256": source_sha256, "impronta_tipo": fingerprint_kind,
        "ambito": scope, "metodo": method,
    }
    if not valid_receipt(receipt, row, today=as_day(str(read_on))):
        raise ValueError("Invalid field observation or mismatched target values")
    return receipt


def valid_receipt(receipt, row, *, today):
    if not isinstance(today, date) or not isinstance(receipt, dict):
        return False
    if receipt.get("schema") != 1 or receipt.get("mercato") != identity(row):
        return False
    vals = receipt.get("valori")
    if not isinstance(vals, dict) or not vals or set(vals) - set(FIELDS):
        return False
    for field, value in vals.items():
        if (not isinstance(value, str) or not value.strip() or
                len(value) > FIELDS[field] or value != row.get(field)):
            return False
    if ("campi_gestiti" in receipt or "gestore_campi" in receipt) and (
            not _managed_fields(receipt) or
            set(receipt.get("campi_gestiti") or []) - set(vals)):
        return False
    read = as_day(receipt.get("letto_il"))
    updated = as_day(receipt.get("fonte_aggiornata_il"))
    if not read or read > today or (updated and updated > read):
        return False
    if receipt.get("fonte_aggiornata_il") and not updated:
        return False
    return bool(safe_url(receipt.get("url")) and
                isinstance(receipt.get("fonte"), str) and
                0 < len(receipt["fonte"]) <= 140 and
                isinstance(receipt.get("fonte_id"), str) and
                0 < len(receipt["fonte_id"]) <= 100 and
                isinstance(receipt.get("riga_fonte"), str) and
                0 < len(receipt["riga_fonte"]) <= 160 and
                re.fullmatch(r"[0-9a-f]{64}", str(receipt.get("sha256", ""))) and
                receipt.get("impronta_tipo", "publisher_parsed_json") in FINGERPRINT_KINDS and
                receipt.get("ambito") in {"dataset", "pagina"} and
                receipt.get("metodo") in METHODS)


def clean_receipts(value, row, *, today):
    """Drop stale VALUE claims, retaining still-matching fields independently."""
    if not isinstance(value, list) or len(value) > 30:
        return []
    chosen = {}
    for raw in value:
        if not isinstance(raw, dict) or not isinstance(raw.get("valori"), dict):
            continue
        receipt = deepcopy(raw)
        receipt["valori"] = {k: v for k, v in receipt["valori"].items()
                             if k in FIELDS and v == row.get(k)}
        _clean_management(receipt)
        if not valid_receipt(receipt, row, today=today):
            continue
        key = _provenance_key(receipt)
        if key not in chosen:
            chosen[key] = receipt
        else:
            if receipt["letto_il"] > chosen[key]["letto_il"]:
                winner, earlier = receipt, chosen[key]
            else:
                winner, earlier = chosen[key], receipt
            # A no-op reread must not reset the publisher-version floor.
            # Keep the accurately dated previous proof when the new read
            # rolls the content date back or loses a formerly known date.
            if not _source_date_not_regressed(earlier, winner):
                winner, earlier = earlier, winner
            chosen[key] = _carry_management(winner, earlier)
    return sorted(chosen.values(), key=lambda x: (x["letto_il"], x["url"], x["riga_fonte"]),
                  reverse=True)[:MAX_RECEIPTS]


def clean_exceptions(value, row, *, today):
    """Only dated, source-bound cancellations; never infer holidays or closures."""
    if not isinstance(value, list) or len(value) > 100:
        return []
    results = {}
    for item in value:
        if not isinstance(item, dict) or item.get("mercato") != identity(row):
            continue
        day, read = as_day(item.get("data")), as_day(item.get("letto_il"))
        if (not day or not read or read > today or
                not safe_url(item.get("url")) or
                not re.fullmatch(r"[0-9a-f]{64}", str(item.get("sha256", ""))) or
                not isinstance(item.get("motivo"), str) or not 1 <= len(item["motivo"]) <= 240 or
                not isinstance(item.get("fonte_id"), str) or not 1 <= len(item["fonte_id"]) <= 100):
            continue
        # Keep a bounded history; a documented cancellation is not revoked
        # just because its evidence is older than the ordinary-read interval.
        if abs((day - today).days) <= 550:
            results[(item["data"], item["url"])] = deepcopy(item)
    return [results[k] for k in sorted(results)]


def attach_feed_observations(source_id, raw, rows, *, read_on):
    """Call only after a successful real adapter download and output gate.

Fingerprint is canonical parsed publisher JSON, not HTTP bytes. Dates in the
normalized, reviewed adapters refer to the publisher dataset/document.
"""
    if source_id not in FEED_IDS or not isinstance(rows, list):
        raise ValueError("Unreviewed field observation source")
    sha = fingerprint(raw)
    output = []
    for original in rows:
        row = deepcopy(original)
        values = {k: row[k] for k, limit in FIELDS.items()
                  if isinstance(row.get(k), str) and row[k].strip() and len(row[k]) <= limit}
        row["fonte_letta_il"] = str(read_on)
        row["fonte_aggiornata_il"] = str(row.get("aggiornato_il") or "")
        if values:
            row["riscontri_campi"] = [make_receipt(
                row, values=values, source_url=row["url_fonte"],
                source_name=row["fonte"], source_id=source_id,
                source_row=row.get("id_fonte") or row["slug"], read_on=read_on,
                source_updated_on=row["fonte_aggiornata_il"], source_sha256=sha)]
        output.append(row)
    return output


def transfer_receipts(source, target, fields, *, today):
    """After an independent exact venue/day join, retain only identical values."""
    records = list(target.get("riscontri_campi") or [])
    for receipt in clean_receipts(source.get("riscontri_campi"), source, today=today):
        values = {k: v for k, v in receipt["valori"].items()
                  if k in fields and target.get(k) == v}
        if not values:
            continue
        item = deepcopy(receipt)
        item["mercato"] = identity(target)
        item["valori"] = values
        item["metodo"] = "sede_giorno_provincia"
        records.append(item)
    return clean_receipts(records, target, today=today)


def field_states(row, *, today):
    receipts = clean_receipts(row.get("riscontri_campi"), row, today=today)
    states = {}
    for field in FIELDS:
        if not str(row.get(field) or "").strip():
            states[field] = "mancante"
            continue
        evidence = [r for r in receipts if field in r["valori"]]
        if not evidence:
            states[field] = "senza_riscontro_documentato"
            continue
        recent = [r for r in evidence if (today - as_day(r["letto_il"])).days <= MAX_READ_AGE]
        current = [r for r in recent if as_day(r["fonte_aggiornata_il"]) and
                   (today - as_day(r["fonte_aggiornata_il"])).days <= SOURCE_AGE[field]]
        states[field] = ("riscontrato_fonte_recente" if current else
                         "riscontrato_data_fonte_sconosciuta" if any(
                             not r["fonte_aggiornata_il"] for r in recent) else
                         "riscontro_da_aggiornare")
    return states


def audit(rows, *, today):
    """Full catalog denominator, field coverage, and per-publisher work queue."""
    total = Counter()
    publishers = defaultdict(Counter)
    markets = []
    seen = set()
    for row in rows:
        slug = row.get("slug")
        if not slug or slug in seen:
            raise ValueError("Field audit requires every unique catalog identity")
        seen.add(slug)
        publisher = str(row.get("fonte") or "fonte sconosciuta")
        states = field_states(row, today=today)
        total["markets"] += 1
        publishers[publisher]["markets"] += 1
        supported = sum(s == "riscontrato_fonte_recente" for s in states.values())
        if supported:
            total["markets_with_recent_field_evidence"] += 1
            publishers[publisher]["markets_with_recent_field_evidence"] += 1
        if supported == len(FIELDS):
            total["markets_with_all_three_fields_source_supported"] += 1
            publishers[publisher]["markets_with_all_three_fields_source_supported"] += 1
        for field, state in states.items():
            total[field + ":" + state] += 1
            publishers[publisher][field + ":" + state] += 1
        markets.append({"slug": slug, "fonte": publisher, "campi": states})
    return {
        "schema": 1, "date": today.isoformat(),
        "meaning": "Riscontri puntuali dei campi; non conferme di apertura o coordinate",
        "read_age_limit_days": MAX_READ_AGE, "source_age_limit_days": SOURCE_AGE,
        "metrics": dict(sorted(total.items())),
        "publishers": [{"publisher": k, **dict(v)} for k, v in sorted(publishers.items())],
        "markets": markets,
    }
