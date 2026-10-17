#!/usr/bin/env python3
"""Conservative cross-source Lombardia overlap screening.

No automatic fuzzy deduplication. A location with a different well-evidenced
weekday can represent a distinct schedule. Same/unknown weekday is quarantined
from NEW import until a human-reviewed matching rule is available. Already
admitted stable source IDs are retained and updated in later daily runs.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from merge_catalog import load_existing
from recurrence_refresh import explicit_rule, WEEKDAYS

ALL_WEEKDAYS = set(range(7))
WEEK_SUFFIX = re.compile(r"-(lunedi|martedi|mercoledi|giovedi|venerdi|sabato|domenica)$")


def norm(text):
    s = unicodedata.normalize("NFKD", str(text or ""))
    s = "".join(x for x in s if not unicodedata.combining(x)).casefold()
    return re.sub(r"\s+", " ", s).strip()


def location_key(record, region="Lombardia"):
    city, street = norm(record.get("citta")), norm(record.get("indirizzo"))
    if (record.get("regione") != region or not city
            or len(street) < 8
            or street in {"centro storico", "centro", "piazza", "mercato", "da verificare"}
            or "da verificare" in street):
        return None
    return city, street


def weekday_evidence(record):
    """Return known full weekday set, or None if an isolated date is ambiguous."""
    slug = str(record.get("slug") or "")
    suffix = WEEK_SUFFIX.search(slug)
    rule = explicit_rule(record.get("ricorrenza_testo"))
    if suffix:
        days = {WEEKDAYS.index(suffix.group(1))}
        # A source identity label is not proof when an explicit schedule
        # contradicts it. Never use the wrong weekday to merge venues,
        # transfer hours or generate a false venue/day overlap.
        if rule and rule["kind"] == "weekly" and set(rule["weekdays"]) != days:
            return None
        return days
    if rule and rule["kind"] == "weekly":
        return set(rule["weekdays"])
    # Only multiple recurring future dates, all from the same weekday,
    # are enough to use a fallback day for display overlap screening.
    dates = record.get("date")
    if not isinstance(dates, list) or len(dates) < 2:
        return None
    parsed = []
    for value in dates:
        try:
            parsed.append(date.fromisoformat(str(value)))
        except ValueError:
            return None
    weekdays = {d.weekday() for d in parsed}
    return weekdays if len(weekdays) == 1 else None


def review(base, official, *, region="Lombardia", source_prefix="lo-mercap-", max_conflicts=500):
    """Generic allowlist-style official source review; default keeps MERCap behavior."""
    if (region not in ("Lombardia", "Emilia-Romagna")
            or source_prefix not in ("lo-mercap-", "bo-open-")
            or not 0 <= max_conflicts <= 500):
        raise ValueError("Unapproved source overlap configuration")
    if not isinstance(base, list) or not isinstance(official, list):
        raise ValueError("Expected record arrays")
    old_by_slug = {x["slug"]: x for x in base}
    if len(old_by_slug) != len(base):
        raise ValueError("Repeated baseline market identifier")
    indexed = defaultdict(list)
    for record in base:
        key = location_key(record, region)
        if key:
            indexed[key].append(record)
    accepted = []
    quarantine = []
    counters = Counter()
    for row in official:
        slug = str(row.get("slug") or "")
        if not slug.startswith(source_prefix):
            accepted.append(row)
            continue
        if slug in old_by_slug:
            accepted.append(row)
            counters["existing_lombardia_identity"] += 1
            continue
        key = location_key(row, region)
        same_place = indexed.get(key, []) if key else []
        if not same_place:
            accepted.append(row)
            counters["no_exact_venue_overlap"] += 1
            continue
        new_days = weekday_evidence(row)
        old_days = [weekday_evidence(x) for x in same_place]
        if new_days is not None and old_days and all(x is not None for x in old_days):
            matching = any(bool(new_days & old) for old in old_days)
            if not matching:
                accepted.append(row)
                counters["same_place_distinct_documented_day"] += 1
                continue
        reason = (
            "same_location_same_weekday" if new_days is not None
            and any(x is not None and bool(new_days & x) for x in old_days)
            else "same_location_unknown_or_conflicting_schedule"
        )
        counters["quarantined_" + reason] += 1
        quarantine.append({
            "official_slug": slug,
            "citta": str(row.get("citta") or "")[:120],
            "indirizzo": str(row.get("indirizzo") or "")[:240],
            "source_weekdays": sorted(new_days) if new_days is not None else [],
            "existing_market_ids": sorted(x["slug"] for x in same_place)[:8],
            "existing_market_days": [sorted(d) if d is not None else []
                                     for d in old_days[:8]],
            "reason": reason,
        })
    if len(quarantine) > max_conflicts:
        raise ValueError("Too many official source conflicts; stop automated update")
    return accepted, {
        "schema": 1, "review_only": True,
        "region": region, "source_prefix": source_prefix,
        "source_total": len(official),
        "accepted": len(accepted), "quarantined": len(quarantine),
        "counts": dict(sorted(counters.items())),
        "quarantined_examples": quarantine[:80],
        "market_confirmations": 0, "deleted_existing_records": 0,
    }


def markdown(report):
    lines = [
        "# Revisione sovrapposizioni " + str(report.get("region") or "Lombardia"),
        "",
        "Uno stesso indirizzo non dimostra che due schede sono lo stesso mercato.",
        "Le nuove schede con giorno uguale o ignoto vengono messe in revisione.",
        "Nessun record storico viene cancellato o dichiarato verificato.",
        "",
        f"- Sorgenti Lombardia: **{report['source_total']}**.",
        f"- Importabili senza conflitto esatto: **{report['accepted']}**.",
        f"- Da rivedere: **{report['quarantined']}**.",
    ]
    for reason,count in report["counts"].items():
        lines.append(f"- {reason}: {count}")
    lines.extend(["", "## Esempi da esaminare", ""])
    for example in report["quarantined_examples"][:25]:
        lines.append(
            f"- {example['citta']} · {example['indirizzo']} · "
            f"{example['official_slug']} ({example['reason']})"
        )
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--official", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--accepted", type=Path, required=True)
    args = p.parse_args()
    previous = load_existing(args.manifest)
    incoming = json.loads(args.official.read_text("utf-8"))
    rows, result = review(previous, incoming)
    for path in (args.out, args.report, args.accepted):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", "utf-8")
    args.report.write_text(markdown(result), "utf-8")
    args.accepted.write_text(json.dumps(rows, ensure_ascii=False) + "\n", "utf-8")
    print(json.dumps({key: result[key] for key in ("accepted", "quarantined", "counts")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
