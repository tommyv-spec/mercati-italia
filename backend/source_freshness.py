"""Separate publisher content dates from source reads and catalog imports.

No legacy scrape timestamp is retroactively treated as publisher evidence.
The small legacy fallback covers only the existing reviewed dataset adapters;
new adapters should write ``fonte_aggiornata_il`` from actual source metadata.
Neither timestamp is an individual market verification.
"""
from __future__ import annotations

import re
from datetime import date, datetime
from urllib.parse import urlsplit

# These adapters already use publisher metadata or dated public documents,
# never the current import time, for their legacy aggiornato_il field.
# Lombardia's date comes from rowsUpdatedAt and Bologna's from data_processed.
_REVIEWED_LEGACY_DATASETS = (
    ("lo-mercap-", "https://www.dati.lombardia.it/d/68zx-njaw", None),
    ("bo-open-", "https://opendata.comune.bologna.it/explore/dataset/mercati-e-fiere/", None),
    ("pg-corciano-", "https://comune.corciano.pg.it/area_letturaDocumento/29645/pagsistema.html",
     frozenset({"2026-01-07"})),
    ("mi-mss-", "https://dati.comune.milano.it/dataset/ds291-economia-mercati-settimanali-scoperti",
     frozenset({"2026-10-01"})),
    ("rm13-salt-", "https://www.comune.roma.it/web-resources/cms/documents/MunXIII_DD647_2026_Graduatorie_mercati.pdf",
     frozenset({"2026-03-31"})),
    ("rm13-plateatico-san-silverio", "https://www.comune.roma.it/web/it/bando-concorso.page?contentId=BEC1343579",
     frozenset({"2025-09-24"})),
)


def as_day(value):
    """Read an actual ISO date/timestamp, never a valid prefix of bad text."""
    if not isinstance(value, str):
        return None
    value = value.strip()
    if not re.fullmatch(r"\d{4}-\d\d-\d\d(?:[T ].+)?", value):
        return None
    try:
        if len(value) == 10:
            return date.fromisoformat(value)
        return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def source_url_domain(value):
    """Validate attribution syntax without making any network request."""
    if not isinstance(value, str):
        return None
    try:
        parsed = urlsplit(value)
        if (parsed.scheme not in {"http", "https"} or not parsed.hostname
                or parsed.username or parsed.password or parsed.port == 0):
            return None
        return parsed.hostname.casefold()
    except ValueError:
        return None


def source_date_evidence(row):
    """Return a source content date and its scope, or an explicit unknown.

    A recent read/import, page-fetch success, global publisher report or
    ``verificato_il`` does not supply a missing content date.
    """
    unknown = {"value": None, "basis": "unknown", "scope": "unknown",
               "reason": "source_content_date_unproven"}
    if not isinstance(row, dict):
        return {**unknown, "reason": "invalid_market_record"}
    if source_url_domain(row.get("url_fonte")) is None:
        return {**unknown, "reason": "missing_attributable_source"}
    declared = row.get("fonte_aggiornata_il")
    if declared not in (None, ""):
        parsed = as_day(declared)
        if parsed is None:
            return {**unknown, "reason": "invalid_declared_source_date"}
        return {
            "value": parsed.isoformat(), "basis": "declared_source_content",
            "scope": "dataset" if row.get("aggiornamento_ambito") == "dataset" else "source_content",
            "reason": "explicit_publisher_content_date",
        }
    legacy = row.get("aggiornato_il")
    # The original scraper used a timestamp with a time for catalog writes.
    # A bare dataset marker must never turn such a timestamp into source proof.
    if (row.get("aggiornamento_ambito") != "dataset" or not isinstance(legacy, str)
            or len(legacy) != 10 or as_day(legacy) is None):
        return unknown
    slug, url = str(row.get("slug") or ""), row.get("url_fonte")
    for prefix, exact_url, dates in _REVIEWED_LEGACY_DATASETS:
        if slug.startswith(prefix) and url == exact_url and (dates is None or legacy in dates):
            return {"value": legacy, "basis": "reviewed_legacy_dataset", "scope": "dataset",
                    "reason": "reviewed_adapter_publisher_metadata_or_document"}
    return {**unknown, "reason": "unreviewed_legacy_dataset_timestamp"}
