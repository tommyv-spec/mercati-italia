"""Versioned, evidence-bound presentation flags for the lightweight index.

The reference day is stored in the manifest. Revalidating an old asset must
not change its projection merely because the validator runs on a later day.
Regional facts, dates and receipts are not changed by this module.
"""
from datetime import date

from editorial_calendar_scope import KEY, clean_editorial_evidence
from source_calendar import clean_source_calendar

INDEX_SCHEMA = 7
LEGACY_FIELDS = (
    "slug", "nome", "citta", "regione", "categoria", "tags",
    "lat", "lng", "position_quality", "orario_testo", "date_quality", "date",
)
# v7: "duplicato_di" names the kept record of a soft-merged copy ("" if none).
FIELDS = {4: LEGACY_FIELDS, 5: LEGACY_FIELDS, 6: LEGACY_FIELDS + ("ambito_orari",),
          7: LEGACY_FIELDS + ("ambito_orari", "duplicato_di")}
HOURS_SCOPES = {"", "per_data", "storico"}


def index_fields(schema):
    if type(schema) is not int or schema not in FIELDS:
        raise ValueError("Unsupported compact index version")
    return FIELDS[schema]


def index_options(manifest):
    schema = manifest.get("index_schema")
    index_fields(schema)
    reference = None
    if schema >= 6:
        value = manifest.get("index_as_of")
        try:
            reference = date.fromisoformat(value)
        except (TypeError, ValueError):
            raise ValueError("Compact index lost its evidence reference day") from None
        if reference.isoformat() != value:
            raise ValueError("Compact index reference day is not an exact ISO date")
    return {"schema": schema, "today": reference}


def hours_scope(row, *, today):
    if not isinstance(today, date):
        raise ValueError("Scoped index requires its declared evidence day")
    if row.get("calendario_fonte") is not None:
        if not clean_source_calendar(row["calendario_fonte"], row, today=today):
            raise ValueError("Index hours scope lacks a valid source calendar")
        return "per_data"
    if row.get(KEY) is not None:
        evidence = clean_editorial_evidence(row[KEY], row, today=today)
        if evidence is None:
            raise ValueError("Index hours scope lacks bound editorial evidence")
        facts = evidence["facts"]
        intervals = facts.get("edition_intervals", [])
        occurrences = facts.get("occurrences", [])
        day = today.isoformat()
        historical = facts["archive_marker"] or bool(intervals or occurrences) and (
            all(item["end"] < day for item in intervals)
            and all(item["date"] < day for item in occurrences))
        return "storico" if historical else "per_data"
    return ""


def project_index(markets, *, schema=5, today=None):
    """Default keeps the former helper contract; new exports request v7."""
    index_fields(schema)
    result = []
    for market in markets:
        values = [market.get(key) for key in LEGACY_FIELDS]
        values[-1] = (values[-1] or [])[:16]
        if schema >= 6:
            values.append(hours_scope(market, today=today))
        if schema >= 7:
            values.append(market.get("duplicato_di") or "")
        result.append(values)
    return result
