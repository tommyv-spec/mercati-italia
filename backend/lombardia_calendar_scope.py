"""Retain MERCap's raw identity and constrain forecasts to its declared scope.

The publisher's ``dal``/``al`` values are yearless day/month boundaries, not
edition dates. They can restrict an independently supported weekly forecast;
they cannot confirm an opening, provide a missing year or refresh the source.
Compound, incomplete and invalid boundaries remain evidence and hold forecasts.
"""
from __future__ import annotations

import re
import unicodedata
from datetime import date

SOURCE_PAGE = "https://www.dati.lombardia.it/d/68zx-njaw"
DAYS = ("lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica")
MONTHS = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
          "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre")
IDENTITY_FIELDS = (
    "codice_id", "descom", "despro", "istat", "ubicazione", "indirizzi",
    "periodicita_tipo", "giorno", "frequenza_settimanale", "mesi_svolgimento",
    "dal", "al", "n_post_alim", "n_post_non_alim", "n_post_tot",
)


def textkey(value):
    value = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(c for c in value if not unicodedata.combining(c)).casefold().strip()


def source_identity(raw):
    """Copy observed qualifiers without replacing missing values or truncating."""
    values = {key: raw.get(key) for key in IDENTITY_FIELDS}
    if any(value is not None and (type(value) not in (str, int)
            or len(str(value)) > 2048) for value in values.values()):
        raise ValueError("Unrepresentable MERCap source identity field")
    return {"schema": 1, "scope_schema": 1, **values}


def retained_identity(record):
    """Keep bounded raw fields in the exported detail, including ambiguous text.

    A corrupt saved representation is retained as an explicit invalid marker;
    dropping it would let a subsequent refresh recreate an unbounded calendar.
    """
    raw = record.get("identita_fonte")
    if not isinstance(raw, dict):
        return None
    if not (str(record.get("slug") or "").startswith("lo-mercap-")
            or record.get("url_fonte") == SOURCE_PAGE):
        return None
    output = {"schema": raw.get("schema")}
    if "scope_schema" in raw:
        output["scope_schema"] = raw["scope_schema"]
    invalid = raw.get("scope_invalid") is True
    for key in IDENTITY_FIELDS:
        if key not in raw:
            continue
        value = raw[key]
        if value is None or type(value) in (str, int) and len(str(value)) <= 2048:
            output[key] = value
        else:
            invalid = True
    if type(output["schema"]) is not int or output["schema"] != 1:
        output["schema"] = 1
        invalid = True
    if "scope_schema" in output and (type(output["scope_schema"]) is not int
                                     or output["scope_schema"] != 1):
        output["scope_schema"] = 1
        invalid = True
    if invalid:
        output["scope_invalid"] = True
    return output


def day_month(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}/\d{2}", value.strip()):
        return None
    day, month = map(int, value.strip().split("/"))
    try:
        date(2000, month, day)  # February 29 is a valid yearless boundary.
    except ValueError:
        return None
    return month, day


def within_bounds(value, bounds):
    """Inclusive yearless interval, including intervals crossing New Year."""
    first, last = (day_month(part) for part in bounds)
    if first is None or last is None:
        raise ValueError("Invalid source day/month boundaries")
    current = (value.month, value.day)
    return first <= current <= last if first <= last else current >= first or current <= last


def calendar_scope(record):
    """Reconstruct scope from this exact publisher identity, not saved flags.

    Old schema-1 identities did not contain boundaries. They remain compatible
    and cannot manufacture scope; a fresh adapter observation supplies it.
    """
    raw = record.get("identita_fonte")
    if not isinstance(raw, dict) or not any(key in raw for key in ("scope_schema", "dal", "al", "scope_invalid")):
        return None
    details = retained_identity(record)
    if details is None:
        return None
    invalid = {"state": "invalid", "identity": details, "rule": None}
    if (details.get("scope_invalid") or details.get("scope_schema") != 1
            or record.get("url_fonte") != SOURCE_PAGE
            or textkey(record.get("regione")) != "lombardia"):
        return invalid
    ident = str(details.get("codice_id") or "").strip()
    weekday = textkey(details.get("giorno"))
    suffix = weekday if weekday in DAYS else "senza-giorno"
    city = textkey(details.get("descom"))
    if (not re.fullmatch(r"\d{1,12}", ident) or str(record.get("id_fonte")) != ident
            or record.get("slug") != f"lo-mercap-{ident}-{suffix}"
            or not city or city not in {textkey(record.get("citta")), textkey(record.get("citta_originale"))}
            or textkey(details.get("despro")) != textkey(record.get("provincia"))):
        return invalid
    first, last = details.get("dal"), details.get("al")
    bounds = None
    if first not in (None, "") or last not in (None, ""):
        if day_month(first) is None or day_month(last) is None:
            return {"state": "ambiguous", "identity": details, "rule": None}
        bounds = [first.strip(), last.strip()]
    tokens = [textkey(token) for token in str(details.get("mesi_svolgimento") or "").split(",")]
    months = sorted({MONTHS.index(token) + 1 for token in tokens if token in MONTHS})
    if not months or len(months) != len(tokens):
        months = []
    supported = (textkey(details.get("periodicita_tipo")) in {"settimanale", "giornaliero"}
                 and details.get("frequenza_settimanale") in (None, "")
                 and weekday in DAYS and bool(months))
    rule = {"kind": "weekly", "weekdays": [DAYS.index(weekday)]} if supported else None
    if rule is not None and len(months) < 12:
        rule["active_months"] = months
    if rule is not None and bounds:
        rule["source_day_month_bounds"] = bounds
    return {"state": "bounded" if bounds else "unbounded", "identity": details,
            "bounds": bounds, "months": months, "rule": rule,
            "limited": bool(bounds and bounds != ["01/01", "31/12"] or months and len(months) < 12)}


def filter_dates(values, scope):
    """Only remove incompatible predictions; never synthesize an occurrence."""
    if scope is None:
        return list(values)
    if scope["state"] in {"invalid", "ambiguous"}:
        return []
    output = []
    for value in values:
        try:
            parsed = date.fromisoformat(value)
        except (TypeError, ValueError):
            continue
        if scope["bounds"] and not within_bounds(parsed, scope["bounds"]):
            continue
        if scope["months"] and parsed.month not in scope["months"]:
            continue
        output.append(value)
    return output


def scope_label(details):
    """Display the literal publisher limits even when they are not parseable."""
    first, last = details.get("dal"), details.get("al")
    if first in (None, "") and last in (None, ""):
        return ""
    if day_month(first) == (1, 1) and day_month(last) == (12, 31):
        return ""
    label = f"periodo dichiarato: dal {first or 'non indicato'} al {last or 'non indicato'}"
    if day_month(first) is None or day_month(last) is None:
        label += " (limiti da verificare)"
    return label
