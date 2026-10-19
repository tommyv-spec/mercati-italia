#!/usr/bin/env python3
"""Merge existing static snapshot with new source feeds, conservatively.

Old verified fields win over estimated scraped fields. The importer does not
delete unseen records when an upstream website omits a market temporarily.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from source_freshness import source_date_evidence, as_day, source_url_domain

_WEEKDAY_NAMES = "lunedi|martedi|mercoledi|giovedi|venerdi|sabato|domenica"
_WEEKLY_RECURRENCE = re.compile(r"(?:ogni\s+|settimanale\s*[-:]\s*)(" + _WEEKDAY_NAMES + r")")
_WEEKDAY_SUFFIX = re.compile(r"-(" + _WEEKDAY_NAMES + r")$")

def _read_file(path):
    value = json.loads(Path(path).read_text("utf-8"))
    if isinstance(value, dict) and "markets" in value:
        return value["markets"]
    if not isinstance(value, list):
        raise ValueError("Expected list of markets in " + str(path))
    return value


def load_existing(manifest_path: Path) -> list:
    if not manifest_path.is_file():
        return []
    manifest = json.loads(manifest_path.read_text("utf-8"))
    public_dir = manifest_path.parent.parent.parent
    if manifest.get("layout") == "single":
        entries = [manifest["catalog"]]
    elif manifest.get("layout") == "regional":
        entries = [part["path"] for part in manifest["regions"]]
    else:
        raise ValueError("Invalid base catalog")
    records = []
    for relative in entries:
        if not relative.startswith("data/v1/") or ".." in relative:
            raise ValueError("Unsafe source manifest path")
        records.extend(_read_file(public_dir / relative))
    if len(records) != manifest.get("total"):
        raise ValueError("Previous catalog is incomplete")
    return records


def _name(text):
    text = unicodedata.normalize("NFKD", str(text)).encode("ascii", "ignore").decode().lower()
    text = re.sub(r"\b(mercato|mercatino|di|del|della|dei|delle)\b", " ", text)
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def _location_key(record):
    addr = _name(record.get("indirizzo", ""))
    return (_name(record.get("regione", "")), _name(record.get("citta", "")),
            _name(record.get("nome", "")), addr)


def _explicit_weekday(record):
    """Require a complete weekly rule; a slug or sample date cannot supply it."""
    value = record.get("ricorrenza_testo")
    if not isinstance(value, str):
        return None
    text = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower().strip()
    match = _WEEKLY_RECURRENCE.fullmatch(text)
    if not match:
        return None
    day = match.group(1)
    suffix = _WEEKDAY_SUFFIX.search(str(record.get("slug") or ""))
    return day if not suffix or suffix.group(1) == day else None


def _compatible_location_identity(existing, incoming):
    """Additional proof required before joining two different stable IDs."""
    for row in (existing, incoming):
        if (row.get("riscontri_campi") or row.get("eccezioni_calendario")
                or str(row.get("slug") or "").startswith(("lo-mercap-", "bo-open-", "pg-corciano-"))):
            return False
    province = str(existing.get("provincia") or "").strip().upper()
    source = str(existing.get("fonte") or "").strip().casefold()
    source_url = existing.get("url_fonte")
    day = _explicit_weekday(existing)
    return bool(
        _location_key(existing) == _location_key(incoming)
        and re.fullmatch(r"[A-Z]{2}", province)
        and province == str(incoming.get("provincia") or "").strip().upper()
        and existing.get("categoria")
        and existing.get("categoria") == incoming.get("categoria")
        and source and source == str(incoming.get("fonte") or "").strip().casefold()
        and source_url_domain(source_url) and source_url == incoming.get("url_fonte")
        and day is not None and day == _explicit_weekday(incoming)
    )


def _source_evidence(record) -> list:
    evidence = record.get("fonti")
    if isinstance(evidence, list):
        sources = [source for source in evidence if isinstance(source, dict)]
    else:
        sources = []
    if record.get("fonte") or record.get("url_fonte"):
        sources.append({"nome": record.get("fonte", ""), "url": record.get("url_fonte", "")})
    unique = {}
    for source in sources:
        key = (str(source.get("nome", "")), str(source.get("url", "")))
        unique[key] = {"nome": key[0], "url": key[1]}
    return list(unique.values())


def _merge(existing, incoming):
    old_verified = bool(existing.get("verificato_il"))
    new_verified = bool(incoming.get("verificato_il"))
    if old_verified and not new_verified:
        best, other = existing, incoming
    elif new_verified and not old_verified:
        best, other = incoming, existing
    else:
        # A later import is not a newer publisher fact. Compare documented
        # content dates first. Unknown dates cannot outrank known evidence.
        old_date = source_date_evidence(existing)["value"]
        new_date = source_date_evidence(incoming)["value"]
        same_source = existing.get("url_fonte") == incoming.get("url_fonte")
        old_read = as_day(existing.get("fonte_letta_il"))
        new_read = as_day(incoming.get("fonte_letta_il"))
        prefer_new = bool(new_date and (not old_date or new_date >= old_date))
        if not old_date and not new_date and same_source and new_read:
            prefer_new = old_read is None or new_read >= old_read
        if prefer_new:
            best, other = incoming, existing
        else:
            best, other = existing, incoming
    merged = {**other, **best}
    # A timestamp belongs to the winning primary source. The dictionary
    # overlay must not inherit a different publisher's missing date/read.
    for timestamp in ("importato_il", "fonte_letta_il", "fonte_aggiornata_il"):
        if not best.get(timestamp):
            merged.pop(timestamp, None)
    merged["slug"] = existing["slug"]  # never break bookmarked stable IDs
    # Fill blanks, but never turn an estimated date into a confirmed date.
    # Blank in a newer authoritative feed can mean the old dates are no
    # longer supported. Never resurrect old projected dates or copy a
    # different source's verification/status metadata into the new record.
    evidence_fields = {
        "date", "date_quality", "aggiornato_il", "verificato_il", "status",
        "proiezione_regola", "proiezione_generata_il", "proiezione_fonte",
        "confidence", "completezza",
        "importato_il", "fonte_letta_il", "fonte_aggiornata_il", "riscontri_campi",
    }
    for name, value in other.items():
        if name in evidence_fields:
            continue
        if merged.get(name) in (None, "", []) and value not in (None, "", []):
            merged[name] = value
    merged["fonti"] = _source_evidence(existing) + [
        f for f in _source_evidence(incoming) if f not in _source_evidence(existing)
    ]
    # Keep independently sourced field receipts. Export rebinds them to the
    # final exact values and keeps only the latest observation per source row.
    field_receipts = []
    for evidence_row in (existing, incoming):
        if isinstance(evidence_row.get("riscontri_campi"), list):
            field_receipts.extend(evidence_row["riscontri_campi"])
    if field_receipts:
        merged["riscontri_campi"] = field_receipts
    return merged


def combine(base: list, incoming: list) -> tuple[list, dict]:
    output = {}
    matched = 0
    candidate_names = {}
    for record in base:
        slug = record.get("slug")
        if not slug:
            continue
        if slug in output:
            raise ValueError("Repeated existing slug: " + slug)
        output[slug] = record.copy()
        key = _location_key(record)
        if key[-1]:  # require an actual matching street/address
            candidate_names.setdefault(key, []).append(slug)

    for record in incoming:
        slug = record.get("slug")
        if not slug:
            continue
        if slug in output:
            output[slug] = _merge(output[slug], record)
            matched += 1
            continue
        key = _location_key(record)
        # A street/name candidate is only a lead. Require compatible source,
        # province, category and explicit recurrence, and keep any identity
        # carrying field or cancellation evidence independent.
        matches = [candidate for candidate in candidate_names.get(key, [])
                   if key[-1] and _compatible_location_identity(output[candidate], record)]
        if len(matches) == 1:
            chosen = matches[0]
            output[chosen] = _merge(output[chosen], record)
            matched += 1
        else:
            output[slug] = record.copy()
    result = sorted(output.values(), key=lambda row: (
        row.get("regione", ""), row.get("citta", ""), row.get("nome", ""), row["slug"]
    ))
    return result, {"base": len(base), "incoming": len(incoming),
                    "merged": matched, "total": len(result)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-manifest", type=Path, default=Path("public/data/v1/manifest.json"))
    parser.add_argument("--new", type=Path, action="append", required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    prior = load_existing(args.base_manifest)
    newly = [record for path in args.new for record in _read_file(path)]
    merged, stats = combine(prior, newly)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(merged, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps(stats, indent=2))


if __name__ == "__main__":
    main()
