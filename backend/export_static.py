#!/usr/bin/env python3
"""Export checked market records to free Cloudflare Pages static assets.

Usage:
  python backend/export_static.py --input backend/mercati_clean.json
  python backend/export_static.py --input /tmp/export.json --dry-run
  python backend/export_static.py --firestore  # one-off migration, Admin SDK credentials

No user-facing request reads Firestore, KV, D1 or invokes a Worker.
Assets are content-addressed and served with long-lived cache headers.
The manifest is replaced last, after all new assets are written.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import unicodedata
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlsplit

CANONICAL_REGIONS = [
    "Abruzzo", "Basilicata", "Calabria", "Campania", "Emilia-Romagna",
    "Friuli Venezia Giulia", "Lazio", "Liguria", "Lombardia", "Marche",
    "Molise", "Piemonte", "Puglia", "Sardegna", "Sicilia", "Toscana",
    "Trentino-Alto Adige", "Umbria", "Valle d'Aosta", "Veneto",
]

VALID_STATUSES = {"attivo", "non_confermato", "annullato", "archiviato"}
VALID_CATEGORIES = {
    "alimentare", "antiquariato", "vintage_abbigliamento",
    "usato", "artigianato", "misto",
}
VALID_DATE_QUALITY = {"confermata", "riportata", "prevista", "sconosciuta"}
MAX_SINGLE_BYTES = 750_000
MAX_MARKET_BYTES = 24_000_000
MAX_FUTURE_DAYS = 550
ITALY_BOUNDS = (35.0, 48.0, 6.0, 19.6)


def slugify(text: str) -> str:
    ascii_text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", ascii_text.lower()).strip("-")[:100]


def canonical_region(name: str) -> str | None:
    key = slugify(name)
    lookup = {slugify(r): r for r in CANONICAL_REGIONS}
    lookup.update({
        "val-d-aosta": "Valle d'Aosta",
        "valle-daosta": "Valle d'Aosta",
        "trentino-altoadige": "Trentino-Alto Adige",
        "friuli-venezia-giulia": "Friuli Venezia Giulia",
    })
    return lookup.get(key)


def sanitize_url(value) -> str:
    candidate = safe_string(value, 650)
    parts = urlsplit(candidate)
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        return ""
    if parts.username or parts.password:
        return ""
    return candidate


def compact_json(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def safe_string(value, max_length=700) -> str:
    if value is None:
        return ""
    return str(value).strip()[:max_length]


def parse_dates(raw_dates, today: date) -> list[str]:
    if not isinstance(raw_dates, list):
        return []
    upper = today + timedelta(days=MAX_FUTURE_DAYS)
    dates = set()
    for raw in raw_dates:
        try:
            value = date.fromisoformat(str(raw))
            if today <= value <= upper:
                dates.add(value.isoformat())
        except ValueError:
            pass
    return sorted(dates)


def parse_location(raw: dict) -> tuple[float | None, float | None, str]:
    lat, lng = raw.get("lat"), raw.get("lng")
    if isinstance(lat, bool) or isinstance(lng, bool):
        return None, None, "sconosciuta"
    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError, OverflowError):
        return None, None, "sconosciuta"
    lat_min, lat_max, lng_min, lng_max = ITALY_BOUNDS
    if not (lat_min <= lat <= lat_max and lng_min <= lng <= lng_max):
        return None, None, "sconosciuta"
    # A valid point is not proof it represents the real market location.
    precision = raw.get("position_quality", "non_verificata")
    if precision not in {"precisa", "approssimata", "non_verificata"}:
        precision = "non_verificata"
    return round(lat, 6), round(lng, 6), precision


def normalize(raw: dict, today: date) -> tuple[dict | None, str | None]:
    if not isinstance(raw, dict):
        return None, "record_not_object"
    nome = safe_string(raw.get("nome"), 160)
    citta = safe_string(raw.get("citta"), 120)
    regione_raw = safe_string(raw.get("regione"), 80)
    if not all((nome, citta, regione_raw)):
        return None, "name_city_region_missing"
    if not re.search(r"[a-zA-ZÀ-ÖØ-öø-ÿ]", citta):
        return None, "invalid_city_name"
    regione = canonical_region(regione_raw)
    if not regione:
        return None, "not_italian_region"
    if raw.get("status") in ("archiviato", "annullato"):
        return None, "inactive_market"
    # Editions titled with a past year and no future dates are historical,
    # not upcoming markets. Leave raw records intact in the original source.
    editions = [int(year) for year in re.findall(r"\b20[0-3][0-9]\b", nome)]
    if editions and max(editions) < today.year and not parse_dates(raw.get("date"), today):
        return None, "historical_edition_without_future_date"
    # Categories outside the product scope (for example "sagra" or
    # "carnevale") must not silently turn into generic market records.
    raw_category = raw.get("categoria")
    if raw_category and raw_category not in VALID_CATEGORIES:
        return None, "excluded_non_market_category"
    if raw_category == "misto":
        # A generic category alone does not prove that a sagra/festival is a
        # market. Require an explicit market-related title before publishing.
        title = nome.lower()
        if not any(word in title for word in ("mercat", "market", "antiquar", "collezion", "brocant", "vintage", "fiera antiquaria")):
            return None, "generic_without_market_evidence"

    slug = safe_string(raw.get("slug"), 130) or slugify(nome + "-" + citta)
    if not re.fullmatch(r"[a-z0-9][a-z0-9-]*", slug):
        slug = slugify(nome + "-" + citta)
    if not slug:
        return None, "invalid_id"

    lat, lng, position_quality = parse_location(raw)
    status = raw.get("status") if raw.get("status") in VALID_STATUSES else "non_confermato"
    if status == "attivo" and not raw.get("verificato_il"):
        status = "non_confermato"
    category = raw.get("categoria") if raw.get("categoria") in VALID_CATEGORIES else "misto"
    quality = raw.get("date_quality", "prevista")
    if quality not in VALID_DATE_QUALITY:
        quality = "sconosciuta"

    confidence = raw.get("confidence", 0)
    try:
        confidence = int(confidence)
    except (ValueError, TypeError):
        confidence = 0
    confidence = max(0, min(confidence, 100))
    raw_tags = raw.get("tags") or []
    tags = sorted({safe_string(tag, 60) for tag in raw_tags if isinstance(tag, str)}) if isinstance(raw_tags, list) else []
    source = safe_string(raw.get("fonte") or raw.get("fonte_nome"), 100)
    source_url = sanitize_url(raw.get("url_fonte"))
    evidence = raw.get("fonti")
    evidence = evidence if isinstance(evidence, list) else []
    clean_sources = []
    for source_record in evidence:
        if not isinstance(source_record, dict):
            continue
        clean_sources.append({
            "nome": safe_string(source_record.get("nome"), 100),
            "url": sanitize_url(source_record.get("url")),
        })
    if source or source_url:
        primary = {"nome": source, "url": source_url}
        if primary not in clean_sources:
            clean_sources.append(primary)
    clean_sources = sorted(clean_sources, key=lambda record: (record["nome"], record["url"]))
    completeness = 25  # name + city + valid Italian region
    completeness += 15 if raw.get("indirizzo") else 0
    completeness += 15 if lat is not None and position_quality == "precisa" else (5 if lat is not None else 0)
    completeness += 15 if parse_dates(raw.get("date"), today) else 0
    completeness += 10 if raw.get("orario_testo") else 0
    completeness += 15 if source_url else 0
    completeness += 5 if raw.get("verificato_il") else 0

    result = {
        "slug": slug, "nome": nome, "citta": citta, "provincia": safe_string(raw.get("provincia"), 2),
        "regione": regione, "indirizzo": safe_string(raw.get("indirizzo"), 300),
        "lat": lat, "lng": lng, "position_quality": position_quality,
        "categoria": category, "tags": tags, "status": status,
        "orario_testo": safe_string(raw.get("orario_testo"), 180),
        "ricorrenza_testo": safe_string(raw.get("ricorrenza_testo"), 180),
        "descrizione": safe_string(raw.get("descrizione"), 900),
        "date": parse_dates(raw.get("date"), today),
        "date_quality": quality,
        "confidence": confidence,  # Legacy field; not a verification probability.
        "completezza": completeness,
        "fonte": source, "url_fonte": source_url,
        "fonti": clean_sources,
        "verificato_il": safe_string(raw.get("verificato_il"), 35),
        "aggiornato_il": safe_string(raw.get("aggiornato_il"), 35),
    }
    return result, None


def comparable_market_name(value: str) -> str:
    """Normalize harmless article/preposition variants without fuzzy guessing."""
    canonical = slugify(value).replace("-", " ")
    words = [
        word for word in canonical.split()
        if word not in {"a", "ad", "di", "da", "del", "della", "dello", "dell",
                        "dei", "degli", "delle", "al", "alla", "nel", "in"}
    ]
    return " ".join(words)


def specific_market_address(value: str) -> str:
    raw = (value or "").strip().lower()
    if not raw or len(raw) < 8:
        return ""
    if raw in {"centro", "centro storico", "centro città", "ce", "ce..."}:
        return ""
    return slugify(raw)


def source_duplicate_group(market: dict) -> tuple | None:
    url = market.get("url_fonte") or ""
    name = comparable_market_name(market.get("nome", ""))
    if not url or len(name) < 12:
        return None
    return (
        market.get("regione", "").casefold(),
        market.get("citta", "").casefold(),
        market.get("categoria", ""),
        url,
        name,
    )


def market_weekday_suffix(slug: str) -> str:
    match = re.search(r"-(lunedi|martedi|mercoledi|giovedi|venerdi|sabato|domenica)$", slug or "")
    return match.group(1) if match else ""


def safe_same_market(a: dict, b: dict) -> bool:
    """Never fuse different street markets or different weekday occurrences."""
    address_a = specific_market_address(a.get("indirizzo", ""))
    address_b = specific_market_address(b.get("indirizzo", ""))
    if address_a and address_b:
        if address_a != address_b:
            return False
    elif address_a or address_b:
        # A city-wide summary must not swallow one of its local street events.
        return False
    else:
        # Both vague/missing: merge only same documented weekday occurrence
        # and effectively identical point. Otherwise hold for manual review.
        suffix_a = market_weekday_suffix(a.get("slug", ""))
        suffix_b = market_weekday_suffix(b.get("slug", ""))
        if not suffix_a or suffix_a != suffix_b:
            return False
        if any(m.get("lat") is None or m.get("lng") is None for m in (a, b)):
            return False
        if abs(a["lat"] - b["lat"]) > 0.0003 or abs(a["lng"] - b["lng"]) > 0.0003:
            return False

    if a.get("position_quality") == "precisa" and b.get("position_quality") == "precisa":
        if a.get("lat") is not None and b.get("lat") is not None:
            if abs(a["lat"] - b["lat"]) > 0.002 or abs(a["lng"] - b["lng"]) > 0.002:
                return False
    return True


def data_value_score(market: dict) -> int:
    return (
        50 * bool(market.get("verificato_il"))
        + 30 * bool(market.get("date"))
        + 20 * bool(specific_market_address(market.get("indirizzo", "")))
        + 20 * (market.get("position_quality") == "precisa")
        + 10 * bool(market.get("orario_testo"))
        + min(10, len(market.get("descrizione", "")) // 100)
    )


def combine_safe_source_duplicates(records: list[dict]) -> tuple[list[dict], int]:
    """Merge only near-exact names from the SAME source and city.

    A shared source list URL is not enough: title and city must agree,
    and distinct specific addresses never merge automatically.
    """
    unique = []
    groups = {}
    merges = 0
    for item in records:
        group = source_duplicate_group(item)
        found = None
        for index in groups.get(group, []) if group else []:
            if safe_same_market(unique[index], item):
                found = index
                break
        if found is None:
            index = len(unique)
            unique.append(item)
            if group:
                groups.setdefault(group, []).append(index)
            continue

        old = unique[found]
        better = item if data_value_score(item) > data_value_score(old) else old
        merged = {**old, **better}
        merged["slug"] = old["slug"]  # stable bookmark identifier
        merged["date"] = sorted(set(old.get("date", []) + item.get("date", [])))
        merged["tags"] = sorted(set(old.get("tags", []) + item.get("tags", [])))
        links = old.get("fonti", []) + item.get("fonti", [])
        merged["fonti"] = sorted(
            { (src.get("nome",""), src.get("url","")) for src in links if isinstance(src, dict) }
        )
        merged["fonti"] = [{"nome": n, "url": u} for n, u in merged["fonti"]]
        # Never upgrade a date from estimated to confirmed by merging estimates.
        order = {"sconosciuta": 0, "prevista": 1, "riportata": 2, "confermata": 3}
        merged["date_quality"] = min(
            (old.get("date_quality", "sconosciuta"),
             item.get("date_quality", "sconosciuta")),
            key=lambda quality: order.get(quality, 0),
        )
        merged["completezza"] = max(old.get("completezza", 0), item.get("completezza", 0))
        unique[found] = merged
        merges += 1
    return unique, merges


def prepare(raw_records: list, today: date) -> tuple[list[dict], dict]:
    cleaned = []
    skipped = Counter()
    by_slug = {}
    collisions = []
    for raw in raw_records:
        result, error = normalize(raw, today)
        if error:
            skipped[error] += 1
            continue
        slug = result["slug"]
        if slug in by_slug:
            current = by_slug[slug]
            if result == current:
                skipped["exact_duplicate"] += 1
                continue
            # Do not erase two different markets sharing the same name/city.
            addr1 = slugify(current["indirizzo"])
            addr2 = slugify(result["indirizzo"])
            if addr1 and addr2 and addr1 != addr2:
                suffix = hashlib.sha256((result["indirizzo"] + result["url_fonte"]).encode()).hexdigest()[:8]
                slug = slug + "-" + suffix
                if slug in by_slug:
                    raise ValueError("Unresolvable market identifier collision: " + slug)
                result["slug"] = slug
                collisions.append(slug)
            else:
                # Conflicting versions of the same market require review.
                raise ValueError("Conflicting records with the same identifier: " + slug)
        by_slug[slug] = result
        cleaned.append(result)

    cleaned, safe_merged = combine_safe_source_duplicates(cleaned)
    cleaned.sort(key=lambda m: (m["regione"], m["citta"], m["nome"], m["slug"]))
    stats = {
        "same_source_duplicates_merged": safe_merged,
        "input": len(raw_records), "accepted": len(cleaned), "skipped": dict(skipped),
        "id_collisions_kept_separate": collisions,
        "with_coordinates": sum(m["lat"] is not None for m in cleaned),
        "with_source_url": sum(bool(m["url_fonte"]) for m in cleaned),
        "with_future_date": sum(bool(m["date"]) for m in cleaned),
        "human_verified": sum(bool(m["verificato_il"]) for m in cleaned),
        "by_region": dict(sorted(Counter(m["regione"] for m in cleaned).items())),
    }
    return cleaned, stats


# Small index contains all fields used by list/search/map, but not full
# descriptions, long date schedules, source evidence or street addresses.
# Clicking a card fetches just one cached region's full detail JSON.
INDEX_FIELDS = (
    "slug", "nome", "citta", "regione", "categoria", "tags",
    "lat", "lng", "position_quality", "orario_testo", "date_quality",
)


def small_index(markets: list[dict]) -> list[dict]:
    output = []
    for market in markets:
        row = {key: market[key] for key in INDEX_FIELDS if key in market}
        # Eight chronological dates suffice for today, weekend, and next
        # 7 days. The detail shard contains the full schedule.
        row["date"] = market["date"][:8]
        output.append(row)
    return output



def _write_asset(output: Path, relative: str, markets: list[dict]):
    body = compact_json({"schema": 1, "markets": markets})
    if len(body) > MAX_MARKET_BYTES:
        raise ValueError("Static asset too large: " + relative)
    digest = hashlib.sha256(body).hexdigest()[:14]
    path = "data/v1/" + relative.replace("{hash}", digest)
    target = output.parent.parent / path  # output == public/data/v1
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_bytes(body)
    return path


def export(records: list, out: Path, today: date | None = None,
           min_count: int = 1, max_drop_ratio: float = 0.20, dry_run: bool = False):
    now = today or date.today()
    markets, stats = prepare(records, now)
    if len(markets) < min_count:
        raise ValueError("Quality gate: too few accepted markets: " + str(stats))

    old_manifest_file = out / "manifest.json"
    previous = None
    if old_manifest_file.is_file():
        previous = json.loads(old_manifest_file.read_text("utf-8"))
        previous_count = int(previous.get("total", 0))
        if previous_count > 0 and len(markets) < previous_count * (1 - max_drop_ratio):
            raise ValueError("Quality gate: too many markets disappeared since last export")

    signature = hashlib.sha256(compact_json(markets)).hexdigest()
    if (previous and previous.get("content_signature") == signature
            and previous.get("index_schema") == 3
            and previous.get("index")
            and (out.parent.parent / previous["index"]).is_file()):
        return {"unchanged": True, "stats": stats, "manifest": previous}
    if dry_run:
        return {"unchanged": False, "stats": stats, "manifest": None}

    out.mkdir(parents=True, exist_ok=True)
    groups = {}
    for market in markets:
        groups.setdefault(market["regione"], []).append(market)

    body_size = len(compact_json({"schema": 1, "markets": markets}))
    if body_size <= MAX_SINGLE_BYTES:
        asset = _write_asset(out, "catalog-{hash}.json", markets)
        layout, part_entries = "single", {"catalog": asset}
    else:
        layout, part_entries = "regional", {"regions": []}
        for name, region_markets in sorted(groups.items()):
            file_name = "regions/" + slugify(name) + "-{hash}.json"
            path = _write_asset(out, file_name, region_markets)
            part_entries["regions"].append({"name": name, "count": len(region_markets), "path": path})

    # One lightweight global index fetch on page load; full regional datasets
    # are immutable and fetched only when a market detail is opened.
    index_path = _write_asset(out, "index-{hash}.json", small_index(markets))

    manifest = {
        "schema": 1, "layout": layout, "total": len(markets),
        "index": index_path,
        "index_schema": 3,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "content_signature": signature,
        "regions_summary": stats["by_region"],
        "quality": {
            "coordinate_count": stats["with_coordinates"],
            "dated_count": stats["with_future_date"],
            "source_url_count": stats["with_source_url"],
            "verified_count": stats["human_verified"],
        },
        **part_entries,
    }
    # Publish last: clients never see the new manifest before its files exist.
    temporary = old_manifest_file.with_suffix(".json.tmp")
    temporary.write_bytes(compact_json(manifest))
    temporary.replace(old_manifest_file)
    return {"unchanged": False, "stats": stats, "manifest": manifest}


def _from_firestore() -> list:
    # Read once during export, never on an end-user page request.
    import firebase_admin
    from firebase_admin import credentials, firestore
    import os
    if not firebase_admin._apps:
        path = os.getenv("FIREBASE_CREDENTIALS_PATH", "backend/serviceAccountKey.json")
        if Path(path).exists():
            firebase_admin.initialize_app(credentials.Certificate(path))
        else:
            firebase_admin.initialize_app()  # Application Default Credentials
    return [snapshot.to_dict() for snapshot in firestore.client().collection("mercati").stream()]


def main() -> int:
    parser = argparse.ArgumentParser()
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path)
    source.add_argument("--firestore", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("public/data/v1"))
    parser.add_argument("--min-count", type=int, default=1)
    parser.add_argument("--max-drop-ratio", type=float, default=0.20)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if args.min_count < 1 or not 0 <= args.max_drop_ratio < 1:
        parser.error("Invalid quality gate thresholds")

    records = _from_firestore() if args.firestore else json.loads(args.input.read_text("utf-8"))
    if isinstance(records, dict) and isinstance(records.get("markets"), list):
        records = records["markets"]
    if not isinstance(records, list):
        parser.error("Source must contain a list of markets")
    report = export(records, args.out, min_count=args.min_count,
                    max_drop_ratio=args.max_drop_ratio, dry_run=args.dry_run)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError) as exc:
        print("Export blocked: " + str(exc), file=sys.stderr)
        sys.exit(1)
