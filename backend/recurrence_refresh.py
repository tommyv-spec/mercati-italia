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
or renew a projection or its provenance timestamp.
"""
from __future__ import annotations

import argparse
import calendar
import json
import re
import unicodedata
from collections import Counter
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from source_freshness import as_day, source_date_evidence, source_url_domain
from field_evidence import clean_receipts, MAX_READ_AGE, SOURCE_AGE

WEEKDAYS = ("lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica")
DAYS_PATTERN = re.compile(r"\b(?:lunedi|martedi|mercoledi|giovedi|venerdi|sabato|domenica)\b")
ORDINAL_PATTERN = re.compile(r"\b(?:prim[oa]|second[oa]|terz[oa]|quart[oa]|ultim[oa])\b")
ORDINAL_INDEX = {"primo": 1, "prima": 1, "secondo": 2, "seconda": 2,
                 "terzo": 3, "terza": 3, "quarto": 4, "quarta": 4,
                 "ultimo": -1, "ultima": -1}

MAX_LOOKAHEAD_DAYS = 120
MAX_SOURCE_STALE_DAYS = 540
DEFAULT_INDEX_DATES = 16


def text_key(value: Any) -> str:
    raw = unicodedata.normalize("NFKD", str(value or ""))
    raw = "".join(c for c in raw if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", raw.casefold()).strip()


def parse_source_day(value: Any) -> date | None:
    """Parse date syntax only; attribution is checked by source_date_evidence."""
    return as_day(value)


def explicit_rule(value: Any) -> dict | None:
    text = text_key(value)
    days = [WEEKDAYS.index(day) for day in dict.fromkeys(DAYS_PATTERN.findall(text))]
    if not days:
        return None

    # Monthly rules must be parsed before weekly. "Ogni prima domenica del
    # mese" is NOT a weekly Sunday market.
    monthly = "mensil" in text or "del mese" in text or "al mese" in text
    if monthly:
        ordinals = [m.group(0) for m in ORDINAL_PATTERN.finditer(text)]
        if len(ordinals) != 1 or len(days) != 1:
            return None
        return {"kind": "monthly_nth_weekday", "weekday": days[0],
                "ordinal": ORDINAL_INDEX[ordinals[0]]}

    # An occurrence has to say *every* named weekday or declare a weekly
    # cadence. Avoid picking unrelated weekdays from prose descriptions.
    if not ("settimanale" in text or re.search(r"\bogni\b", text)):
        return None
    if "bisettimanale" in text or "quindicinal" in text or "alternat" in text:
        return None
    if ORDINAL_PATTERN.search(text):
        return None
    return {"kind": "weekly", "weekdays": sorted(set(days))}


def project_dates(rule: dict, today: date, horizon_days: int) -> list[str]:
    if not 7 <= horizon_days <= 365:
        raise ValueError("Horizon must be between 7 and 365 days")
    end = today + timedelta(days=horizon_days)
    if rule["kind"] == "weekly":
        weekdays = set(rule["weekdays"])
        return [(today + timedelta(days=i)).isoformat()
                for i in range(horizon_days + 1)
                if (today + timedelta(days=i)).weekday() in weekdays]
    if rule["kind"] == "monthly_nth_weekday":
        results = []
        year, month = today.year, today.month
        for i in range(15):
            y, m = year + (month + i - 1) // 12, (month + i - 1) % 12 + 1
            candidates = [date(y, m, d)
                          for d in range(1, calendar.monthrange(y, m)[1] + 1)
                          if date(y, m, d).weekday() == rule["weekday"]]
            ordinal = rule["ordinal"]
            if ordinal == -1:
                candidate = candidates[-1]
            elif len(candidates) >= ordinal:
                candidate = candidates[ordinal - 1]
            else:
                continue
            if today <= candidate <= end:
                results.append(candidate.isoformat())
            if date(y, m, 1) > end:
                break
        return results
    raise ValueError("Unrecognized recurrence kind")


def refresh_record(original: dict, today: date, horizon_days: int = MAX_LOOKAHEAD_DAYS,
                   max_stale_days: int = MAX_SOURCE_STALE_DAYS) -> tuple[dict, str]:
    record = dict(original)
    if record.get("status") in {"archiviato", "annullato"}:
        return record, "inactive"
    if record.get("date_quality") in {"confermata", "riportata"}:
        return record, "non_projected_source_date"
    if record.get("date_quality") not in {None, "", "prevista", "sconosciuta"}:
        return record, "unrecognized_date_quality"

    rule = explicit_rule(record.get("ricorrenza_testo"))
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

    if source_url_domain(record.get("url_fonte")) is None:
        return record, "no_attributable_source"
    source_evidence = source_date_evidence(record)
    updated = parse_source_day(source_evidence["value"])
    projection_basis = "ricorrenza_testo"
    if updated is None or not 0 <= (today - updated).days <= max_stale_days:
        # A secondary publisher can support this exact recurrence without
        # relabeling the age of the original source. Only current, matching
        # field observations qualify; addresses/hours and fresh imports do not.
        dates = [parse_source_day(r.get("fonte_aggiornata_il")) for r in
                 clean_receipts(record.get("riscontri_campi"), record, today=today)
                 if r["valori"].get("ricorrenza_testo") == record.get("ricorrenza_testo")
                 and (today - parse_source_day(r["letto_il"])).days <= MAX_READ_AGE]
        dates = [d for d in dates if d and
                 0 <= (today - d).days <= min(max_stale_days, SOURCE_AGE["ricorrenza_testo"])]
        if dates:
            updated = max(dates)
            projection_basis = "riscontri_campi:ricorrenza_testo"
    if (record.get("proiezione_fonte") == "riscontri_campi:ricorrenza_testo"
            and projection_basis != "riscontri_campi:ricorrenza_testo"
            and (updated is None or not 0 <= (today - updated).days <= max_stale_days)
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
        return record, "unknown_source_age"
    age = (today - updated).days
    if age < 0:
        return record, "source_from_future"
    if age > max_stale_days:
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


def refresh_records(records: list[dict], today: date, horizon_days: int = MAX_LOOKAHEAD_DAYS,
                    max_stale_days: int = MAX_SOURCE_STALE_DAYS) -> tuple[list[dict], dict]:
    output = []
    counts = Counter()
    improved = 0
    changed = 0
    monthly = 0
    preserved_unknown = 0
    for original in records:
        updated, reason = refresh_record(original, today, horizon_days, max_stale_days)
        counts[reason] += 1
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
