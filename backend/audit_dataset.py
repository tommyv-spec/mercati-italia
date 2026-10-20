#!/usr/bin/env python3
"""Read-only audit of every immutable market shard and its lightweight index.

This script never scrapes, changes or publishes market data. Use from the repo
root: python backend/audit_dataset.py --out reports/audit/dataset.json
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta
import gzip
import json
from pathlib import Path
import re
import unicodedata
from urllib.parse import urlparse


def flatkey(value: str) -> str:
    norm = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", norm.lower().strip())


def as_date(value) -> date | None:
    try:
        return date.fromisoformat(str(value)[:10])
    except (ValueError, TypeError):
        return None


def first_nonempty(v, fallback="unknown"):
    return str(v) if v else fallback


def audit(manifest_path: Path, today: date | None = None) -> dict:
    today = today or date.today()
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    public_root = manifest_path.resolve().parents[2]
    index_path = public_root / manifest["index"]
    index_blob = index_path.read_bytes()
    index = json.loads(index_blob)
    records = []
    compressed_regions = 0
    raw_regions = 0
    if manifest.get("layout") == "single":
        parts = [{"path": manifest["catalog"], "count": manifest["total"], "name": "catalog"}]
    elif manifest.get("layout") == "regional":
        parts = manifest["regions"]
    else:
        raise ValueError("Unsupported catalog layout")
    for part in parts:
        shard = (public_root / part["path"]).read_bytes()
        raw_regions += len(shard)
        compressed_regions += len(gzip.compress(shard, compresslevel=6))
        chunk = json.loads(shard)["markets"]
        if len(chunk) != part["count"]:
            raise ValueError("Part size mismatch: " + part["name"])
        records.extend(chunk)

    assert manifest["total"] == len(records), "Snapshot total differs from published manifest"
    assert len(index["markets"]) == len(records), "Index record count mismatch"
    from compact_index import index_fields, index_options, project_index
    assert index["markets"] == project_index(records, **index_options(manifest)), "Compact index differs from its records"

    by_category = Counter()
    by_source = Counter()
    by_domain = Counter()
    by_status = Counter()
    by_region = Counter()
    by_date_quality = Counter()
    by_position_quality = Counter()
    missing = Counter()
    stale = Counter()
    date_counts = Counter()
    coord_groups = defaultdict(list)
    city_variants = defaultdict(set)
    city_codes = Counter()
    year_titles = []
    city_same_coords = defaultdict(list)
    all_dates = []
    doc_lengths = []
    max_dates = []
    precise_sample = []
    rows_verified_without_confirmation = []

    for record in records:
        by_category[first_nonempty(record.get("categoria"))] += 1
        by_source[first_nonempty(record.get("fonte"))] += 1
        by_region[first_nonempty(record.get("regione"))] += 1
        by_status[first_nonempty(record.get("status"))] += 1
        by_date_quality[first_nonempty(record.get("date_quality"))] += 1
        quality = first_nonempty(record.get("position_quality"))
        by_position_quality[quality] += 1
        u = record.get("url_fonte") or ""
        if not u:
            missing["source_url"] += 1
        else:
            by_domain[first_nonempty(urlparse(u).hostname)] += 1

        if not record.get("orario_testo"):
            missing["hours"] += 1
        if not record.get("descrizione"):
            missing["description"] += 1
        if not record.get("indirizzo"):
            missing["address"] += 1
        if not record.get("verificato_il"):
            missing["verified_at"] += 1
        if not record.get("aggiornato_il"):
            missing["source_updated_at"] += 1
        address = flatkey(record.get("indirizzo") or "")
        if not address or address in {"centro", "centro storico", "ce", "ce...", "centro citta"}:
            missing["missing_or_vague_address"] += 1
        if not re.search(r"\b(via|viale|piazza|corso|strada|vicolo|largo|piazzale|piazzetta|contrada|mercato|parco|borgo)\b", address):
            missing["no_streetlike_address"] += 1
        if not record.get("date"):
            missing["future_dates"] += 1
        dates = [d for raw in record.get("date") or [] if (d := as_date(raw))]
        all_dates.extend(dates)
        if dates:
            max_dates.append(max(dates))
        upd = as_date(record.get("aggiornato_il"))
        if upd is None:
            stale["unknown_source_update_date"] += 1
        else:
            age = (today - upd).days
            if age > 365:
                stale["source_older_than_365d"] += 1
            if age > 730:
                stale["source_older_than_730d"] += 1
            if age > 1095:
                stale["source_older_than_1095d"] += 1
        if quality == "precisa" and not record.get("verificato_il"):
            rows_verified_without_confirmation.append(record["slug"])
        lat, lng = record.get("lat"), record.get("lng")
        if isinstance(lat, (float, int)) and isinstance(lng, (float, int)):
            coord_groups[(round(lat, 4), round(lng, 4))].append(record["slug"])
            city_same_coords[(record.get("regione"), flatkey(record.get("citta")), round(lat, 4), round(lng, 4))].append(record["slug"])
        else:
            missing["coordinates"] += 1
        city = record.get("citta") or ""
        city_variants[(record.get("regione"), flatkey(city))].add(city)
        if len(city) == 2 and city.upper() == city and city.isalpha():
            city_codes[city] += 1
        if re.search(r"\b20(?:1[0-9]|2[0-9])\b", record.get("nome") or ""):
            year_titles.append(record["slug"])
        doc_lengths.append(len((record.get("descrizione") or "").strip()))

    for days in [0, 7, 30, 60, 90, 120, 180, 240, 365]:
        moment = today + timedelta(days=days)
        selected = sum(1 for m in records if any(str(d) >= moment.isoformat() for d in m.get("date", [])))
        date_counts[str(days)] = selected

    schema_cols = index_fields(manifest["index_schema"])
    index_dates = []
    summary_items = []
    for row in index["markets"]:
        if not isinstance(row, list) or len(row) != len(schema_cols):
            raise ValueError("Index schema row malformed")
        m = dict(zip(schema_cols, row))
        summary_items.append(m)
        dates = [d for raw in m.get("date") or [] if (d := as_date(raw))]
        index_dates.append(max(dates) if dates else None)
    index_remaining = {
        str(days): sum(1 for end in index_dates if end is not None and end >= today + timedelta(days=days))
        for days in [0, 7, 30, 60, 90, 120, 180, 240]
    }

    suspected_generic_city = sum(1 for m in records if
        flatkey(m.get("nome")).startswith("mercato settimanale ") and m.get("citta"))
    coord_clusters = sorted(coord_groups.items(), key=lambda entry: len(entry[1]), reverse=True)
    suspect_city_clusters = sorted(city_same_coords.items(), key=lambda entry: len(entry[1]), reverse=True)
    variant_examples = [
        {"region": key[0], "normalized_city": key[1], "variants": sorted(names)}
        for key, names in city_variants.items() if len(names) > 1
    ]
    variant_examples.sort(key=lambda v: (-len(v["variants"]), v["region"], v["normalized_city"]))
    def top_count(counter, size=12):
        return [{"name": name, "count": count} for name, count in counter.most_common(size)]
    def pct(value):
        return round(100 * value / len(records), 2) if records else 0

    metrics = {
        "audit_generated_at": datetime.now().astimezone().isoformat(),
        "today": today.isoformat(),
        "manifest_generated_at": manifest["generated_at"],
        "snapshot_total": len(records),
        "regions_count": len({m.get("regione") for m in records}),
        "sizes": {
            "national_index_bytes": len(index_blob),
            "national_index_gzip_bytes": len(gzip.compress(index_blob, compresslevel=6)),
            "regional_shards_bytes": raw_regions,
            "regional_shards_gzip_bytes_total": compressed_regions,
            "all_static_data_bytes": len(index_blob) + raw_regions,
        },
        "fields_missing": dict(missing),
        "fields_missing_percent": {key: pct(v) for key, v in missing.items()},
        "date_quality": dict(by_date_quality),
        "position_quality": dict(by_position_quality),
        "category": dict(by_category),
        "status": dict(by_status),
        "region": dict(by_region),
        "sources": top_count(by_source, 20),
        "source_domains": top_count(by_domain, 20),
        "source_freshness": dict(stale),
        "full_catalog_future_coverage": dict(date_counts),
        "compact_index_future_coverage": index_remaining,
        "distinct_city_labels": len({(m.get("regione"), m.get("citta")) for m in records}),
        "cities_with_variant_spellings": len(variant_examples),
        "variant_city_samples": variant_examples[:20],
        "two_letter_city_codes": dict(city_codes.most_common(20)),
        "repeated_coordinates": [
            {"lat": xy[0], "lng": xy[1], "records": len(rows)}
            for xy, rows in coord_clusters[:12]
        ],
        "repeated_city_centers": [
            {"region": key[0], "city": key[1], "lat": key[2], "lng": key[3], "records": len(rows)}
            for key, rows in suspect_city_clusters[:15] if len(rows) > 4
        ],
        "generic_weekly_city_name_records": suspected_generic_city,
        "record_titles_with_year": len(year_titles),
        "documented_verified_records": len(records) - missing["verified_at"],
        "precise_coordinates_but_no_human_verification": len(rows_verified_without_confirmation),
        "written_human_certification": "none assessed: this script counts only explicitly documented verified_at fields",
    }
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("public/data/v1/manifest.json"))
    parser.add_argument("--out", type=Path, default=Path("reports/audit/dataset.json"))
    args = parser.parse_args()
    report = audit(args.manifest)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "records": report["snapshot_total"],
        "field_missing_pct": report["fields_missing_percent"],
        "positions": report["position_quality"],
        "quality": report["date_quality"],
        "source_domains": report["source_domains"][:6],
        "index_gzip_kib": round(report["sizes"]["national_index_gzip_bytes"]/1024, 2),
        "index_remaining_days_60": report["compact_index_future_coverage"]["60"],
        "distinct_city_labels": report["distinct_city_labels"],
        "cities_with_variant_spellings": report["cities_with_variant_spellings"],
    }, ensure_ascii=False, indent=2))
