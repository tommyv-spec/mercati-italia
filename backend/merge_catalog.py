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
        # For equal verification, prefer the more recently updated source.
        if str(incoming.get("aggiornato_il", "")) >= str(existing.get("aggiornato_il", "")):
            best, other = incoming, existing
        else:
            best, other = existing, incoming
    merged = {**other, **best}
    merged["slug"] = existing["slug"]  # never break bookmarked stable IDs
    # Fill blanks, but never turn an estimated date into a confirmed date.
    for name, value in other.items():
        if merged.get(name) in (None, "", []) and value not in (None, "", []):
            merged[name] = value
    merged["fonti"] = _source_evidence(existing) + [
        f for f in _source_evidence(incoming) if f not in _source_evidence(existing)
    ]
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
        matches = candidate_names.get(key, []) if key[-1] else []
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
