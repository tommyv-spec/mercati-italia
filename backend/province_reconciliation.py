"""Bounded administrative province repair from exact pinned ISTAT identities.

This says only which province contains an already named municipality. It does
not verify a market, its source page, location, calendar or operating status.
Publisher receipts are never rewritten to fit a corrected province.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from copy import deepcopy
from functools import lru_cache
from pathlib import Path
from types import MappingProxyType

KEY = "riconciliazione_provincia"
METHOD = "comune_regione_esatti_istat"
SOURCE_DATE = "2026-02-21"
SOURCE_URL = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.xlsx"
SOURCE_SHA256 = "83842076860450f7e482daecea6b7a769f5f93d0bf5b0d48802b44896d7a26d5"
REGISTRY_SHA256 = "6e94770332bd5d979dabfb8f9f3cefd714712912cc5543f94a5688fbdd772a14"
REFERENCE = Path(__file__).resolve().parent / "data/istat-comuni-2026.json"
MAX_TOTAL_CHANGES = 80
MAX_RECORDS = 100_000
PROTECTED_PROVENANCE = (
    "riscontri_campi", "calendario_fonte", "dettaglio_fonte",
    "evidenza_editoriale", "eccezioni_calendario", "identita_fonte",
    "id_fonte", "citta_originale", "localita_ricostruita_da",
    "navigazione_sospesa_motivo", "coordinate_sospese_motivo", KEY,
)


def _fold(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", "".join(
        char for char in text if not unicodedata.combining(char)
    ).casefold()).split())


def _digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode()).hexdigest()


def _registry(reference):
    # Pin the actual extracted correspondence, not just the original file's
    # declared hash. A forged municipality/province entry with intact metadata
    # must not authorize a change or validate a final exported receipt.
    if not isinstance(reference, dict) or _digest(reference) != REGISTRY_SHA256:
        raise ValueError("ISTAT province registry differs from pinned content")
    if (reference.get("reference_date") != SOURCE_DATE
            or reference.get("source") != SOURCE_URL
            or reference.get("source_file_sha256") != SOURCE_SHA256):
        raise ValueError("ISTAT province registry has untrusted source metadata")
    result = {}
    for region, cities in reference["regions"].items():
        for name in cities:
            identity = (region, _fold(name))
            if identity in result:
                raise ValueError("Ambiguous ISTAT municipality within region")
            result[identity] = (name, reference["provinces_by_region"][region][name])
    if len(result) != 7894:
        raise ValueError("Incomplete pinned ISTAT province correspondence")
    return MappingProxyType(result)


@lru_cache(maxsize=1)
def pinned_registry():
    return _registry(json.loads(REFERENCE.read_text(encoding="utf-8")))


def _identity(row):
    return {field: row.get(field) for field in ("slug", "citta", "regione")}


def _target(row, registry):
    city, region = row.get("citta"), row.get("regione")
    if not isinstance(city, str) or not city.strip() or not isinstance(region, str):
        return None
    return registry.get((region, _fold(city)))


def _proof(row, target):
    return {
        "schema": 1, "metodo": METHOD, "mercato": _identity(row),
        "comune_istat": target[0], "provincia_originale": row["provincia"],
        "provincia": target[1], "fonte": SOURCE_URL,
        "data_riferimento": SOURCE_DATE, "sha256_fonte": SOURCE_SHA256,
        "sha256_registro": REGISTRY_SHA256,
    }


def valid_proof(value, row):
    """An administrative proof is tied to this exact identity and province."""
    if (not isinstance(value, dict) or not isinstance(row, dict)
            or type(value.get("schema")) is not int):
        return False
    target = _target(row, pinned_registry())
    previous = value.get("provincia_originale")
    if (not target or row.get("provincia") != target[1]
            or not isinstance(row.get("slug"), str) or not row["slug"]
            or not isinstance(previous, str) or not re.fullmatch(r"[A-Z]{2}", previous)
            or previous == target[1]):
        return False
    original = {**row, "provincia": previous}
    return value == _proof(original, target)


def retained_proof(raw, normalized):
    """Do not silently discard provenance while retaining its correction."""
    if KEY not in raw:
        return None
    value = raw[KEY]
    if not valid_proof(value, raw) or not valid_proof(value, normalized):
        raise ValueError("Invalid or identity-mismatched ISTAT province proof")
    return deepcopy(value)


def _eligible(row, registry):
    target = _target(row, registry)
    previous = row.get("provincia")
    if (not target or not isinstance(previous, str)
            or not re.fullmatch(r"[A-Z]{2}", previous) or previous == target[1]):
        return None, None
    if (row.get("verificato_il") or row.get("date_quality") == "confermata"
            or any(row.get(field) for field in PROTECTED_PROVENANCE)):
        return None, "existing_source_or_verification_proof"
    return _proof(row, target), None


def supplement(original, legacy_rows, reference=None, *, apply=False):
    """Use only the remaining slots in the existing 80-record total budget.

    Already corrected records leave the pending set naturally. Sorting by
    stable ID makes successive published runs deterministic without another
    checkpoint or any per-market configuration. Existing city/calendar edits
    retain their priority and cannot be combined with a province edit.
    """
    if (not isinstance(original, list) or not isinstance(legacy_rows, list)
            or not 1 <= len(original) <= MAX_RECORDS
            or len(original) != len(legacy_rows) or type(apply) is not bool):
        raise ValueError("Unbounded province reconciliation inputs")
    registry = _registry(reference) if reference is not None else pinned_registry()
    before_ids = [row.get("slug") for row in original]
    if (any(not isinstance(sid, str) or not sid for sid in before_ids)
            or len(set(before_ids)) != len(before_ids)
            or before_ids != [row.get("slug") for row in legacy_rows]):
        raise ValueError("Province reconciliation changed or duplicated market IDs")
    occupied = sum(before != after for before, after in zip(original, legacy_rows))
    if occupied > MAX_TOTAL_CHANGES:
        raise ValueError("Municipality cleanup exceeds bounded daily modification budget")
    available = MAX_TOTAL_CHANGES - occupied
    candidates, protected = [], []
    for index, (before, row) in enumerate(zip(original, legacy_rows)):
        if KEY in row and not valid_proof(row[KEY], row):
            raise ValueError("Existing ISTAT province proof is invalid")
        if before != row:
            continue
        proof, reason = _eligible(row, registry)
        if proof:
            candidates.append((row["slug"], index, proof))
        elif reason:
            protected.append(row["slug"])
    candidates.sort(key=lambda item: item[0])
    selected = candidates[:available] if apply else []
    result = [dict(row) for row in legacy_rows]
    for _, index, proof in selected:
        result[index]["provincia"] = proof["provincia"]
        result[index][KEY] = proof
    report = {
        "schema": 1, "metodo": METHOD, "source_registry_sha256": REGISTRY_SHA256,
        "review_only": not apply, "total_change_budget": MAX_TOTAL_CHANGES,
        "prior_municipality_changes": occupied, "remaining_slots": available,
        "eligible": len(candidates), "applied": len(selected),
        "pending": len(candidates) - len(selected), "protected": len(protected),
        "proofs": [proof for _, _, proof in selected],
        "protected_examples": sorted(protected)[:35],
    }
    return result, report


def verify_supplement(original, revised, report, *, apply):
    """Rebuild selection and exact values; a reported allowlist is insufficient."""
    if not isinstance(report, dict):
        raise ValueError("Missing administrative province correction proof")
    legacy_rows = []
    for before, after in zip(original, revised):
        changes = {field for field in before.keys() | after.keys()
                   if before.get(field) != after.get(field)}
        if "provincia" in changes or KEY in changes:
            if changes != {"provincia", KEY}:
                raise ValueError("Province reconciliation changed unrelated market fields")
            legacy_rows.append(before)
        else:
            legacy_rows.append(after)
    expected, expected_report = supplement(original, legacy_rows, apply=apply)
    if expected != revised or expected_report != report:
        raise ValueError("Administrative province changes differ from pinned ISTAT replay")
    return len(report["proofs"])
