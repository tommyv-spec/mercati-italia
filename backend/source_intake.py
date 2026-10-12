#!/usr/bin/env python3
"""Track bounded official-source metadata without importing market records.

Catalog search results are leads, not proof of licensing, live events, or
coordinates. No network requests or source execution take place here.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

VERSION = 1
MAX_SOURCES = 400
MAX_SCOUT_ROWS = 80
MAX_EVENTS = 200
FORMATS = {"CSV", "JSON", "GEOJSON", "KML", "XLS", "XLSX"}


def clean(value, limit=240):
    return re.sub(r"\s+", " ", str(value or "")).strip()[:limit]


def clean_url(value):
    value = clean(value, 1000)
    try:
        p = urlsplit(value)
        if (p.scheme != "https" or not p.hostname or p.username or p.password
                or p.port not in (None, 443) or p.fragment
                or p.hostname in {"localhost", "127.0.0.1"}):
            return ""
    except ValueError:
        return ""
    return value


def normalize(item):
    if not isinstance(item, dict):
        raise ValueError("Source metadata row must be an object")
    ident = clean(item.get("id"), 160)
    title = clean(item.get("title"), 240)
    if not ident or not title:
        raise ValueError("Source metadata missing ID or title")
    resources = []
    for resource in (item.get("resources") or [])[:5]:
        if not isinstance(resource, dict):
            continue
        fmt = clean(resource.get("format"), 16).upper()
        url = clean_url(resource.get("url"))
        if fmt in FORMATS and url:
            resources.append({
                "format": fmt, "url": url, "name": clean(resource.get("name"), 150)
            })
    if not resources:
        raise ValueError("Source lacks a secure structured-data URL")
    resources.sort(key=lambda x: (x["format"], x["url"]))
    score = item.get("score", 0)
    if not isinstance(score, (int, float)) or not -100 <= score <= 100:
        raise ValueError("Source score is invalid")
    return {
        "id": ident,
        "title": title,
        "organization": clean(item.get("organization"), 180),
        "metadata_modified": clean(item.get("metadata_modified"), 30),
        "data_modified": clean(item.get("data_modified"), 30),
        "license": clean(item.get("license"), 180),
        "license_status": clean(item.get("license_status"), 70),
        "score": int(score),
        "resources": resources,
        "automatic_import_allowed": False,
        "review_required": ["publisher_authority", "license_terms",
                            "actual_schema", "data_freshness", "record_sample"],
    }



def published_data_date(raw):
    value = clean(raw, 30)
    try:
        if re.match(r"^\d{4}-\d\d-\d\d", value):
            return date.fromisoformat(value[:10])
        if re.match(r"^\d\d-\d\d-\d{4}$", value):
            day, month, year = map(int, value.split("-"))
            return date(year, month, day)
    except ValueError:
        pass
    return None


def triage(row, today):
    """Rank likely useful *source reviews*, never market reliability or truth."""
    title = row["title"].casefold()
    score = int(row["score"])
    reasons = []
    bucket = "general_market_candidate"
    stats = ("residenti per posto", "metri quadri", "numero posti settore",
             "per circoscrizione", "numero di stand", "numero di posteggi")
    if any(word in title for word in stats):
        bucket = "aggregated_statistics"
        score -= 18
        reasons.append("aggregated_statistics_not_market_schedule")
    elif "mercati settimanali" in title or "mercati su aree pubbliche" in title:
        bucket = "market_location_candidate"
        score += 8
    elif "mercati rionali" in title:
        bucket = "market_location_candidate"
        score += 6
    elif "censimento dei mercati" in title:
        bucket = "market_location_candidate"
        score += 5
    elif "mercati e fiere" in title or "fiere e mercati" in title:
        bucket = "mixed_events_candidate"
        score += 3
    if "posteggi" in title and bucket != "aggregated_statistics":
        score -= 4
        reasons.append("stalls_not_necessarily_visitable_markets")

    # A historical year in a title is much stronger evidence of obsolescence
    # than a newly harvested CKAN metadata_modified timestamp.
    title_years = [int(value) for value in re.findall(r"\b20\d{2}\b", title)]
    if title_years and max(title_years) < today.year - 2:
        score -= 8
        reasons.append("historical_year_in_title")
    declared = published_data_date(row.get("data_modified"))
    if declared is None:
        reasons.append("source_data_freshness_unknown")
    else:
        age = (today - declared).days
        if age < -30:
            reasons.append("future_dated_metadata_requires_check")
        elif age <= 365:
            score += 6
            reasons.append("publisher_reports_recent_dataset_date")
        elif age <= 730:
            score += 2
        elif age > 1825:
            score -= 7
            reasons.append("source_data_older_than_five_years")
        else:
            score -= 3
            reasons.append("source_data_older_than_two_years")

    if row["license_status"] != "claimed_open_license_review_required":
        score -= 4
        reasons.append("license_not_identified")
    paths = " ".join(item["url"].casefold() for item in row["resources"])
    if "f758d24c-8805-40b0-9a72-a8aac06d1e98" in paths:
        score -= 10
        reasons.append("existing_milano_adapter_covers_dataset")
    # Resource names like mercati_rionali_giugno_2022 also matter if the
    # catalog does not declare a data modification date.
    if not declared:
        filenames = [item["url"].split("?")[0].rsplit("/", 1)[-1] for item in row["resources"]]
        fileyears = [int(y) for name in filenames
                     for y in re.findall(r"(?<!\d)20\d{2}(?!\d)", name)]
        if fileyears and max(fileyears) < today.year - 2:
            score -= 5
            reasons.append("historical_year_in_resource_filename")
    return score, bucket, reasons


def fingerprint(row):
    # Harvest timestamps are NOT proof of changes to municipal market data.
    fields = ("title", "organization", "data_modified", "license",
              "license_status", "resources")
    payload = {key: row[key] for key in fields}
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def evaluate(scout, previous=None, publisher_evidence=None, schema_evidence=None):
    if publisher_evidence and (
        not isinstance(publisher_evidence, dict)
        or publisher_evidence.get("schema") != 1
        or publisher_evidence.get("market_imports") != 0
        or not isinstance(publisher_evidence.get("source_evidence"), list)
    ):
        raise ValueError("Untrusted publisher evidence; no auto import")
    if schema_evidence is not None and (
        not isinstance(schema_evidence, dict)
        or schema_evidence.get("schema") != 1
        or schema_evidence.get("imports") != 0
        or schema_evidence.get("verified_event_count") != 0
        or not isinstance(schema_evidence.get("probe_history"), dict)
        or len(schema_evidence["probe_history"]) > MAX_SOURCES
    ):
        raise ValueError("Untrusted municipal schema evidence")
    schemas = (schema_evidence or {}).get("probe_history", {})
    audited = {
        item.get("source_id"): item
        for item in (publisher_evidence or {}).get("source_evidence", [])
        if isinstance(item, dict) and item.get("status") == "metadata_checked"
    }
    if not isinstance(scout, dict) or scout.get("metadata_only") is not True:
        raise ValueError("Only read-only national-catalog metadata is accepted")
    rows = scout.get("candidates")
    if not isinstance(rows, list) or len(rows) > MAX_SCOUT_ROWS:
        raise ValueError("Source discovery exceeded bounded candidate limit")
    old = previous or {"schema": VERSION, "sources": [], "events": []}
    if old.get("schema") != VERSION or not isinstance(old.get("sources"), list):
        raise ValueError("Unknown source registry schema")
    if len(old["sources"]) > MAX_SOURCES:
        raise ValueError("Prior source registry exceeds safety limit")
    stored = {}
    for item in old["sources"]:
        if not isinstance(item, dict) or not clean(item.get("id"), 160):
            raise ValueError("Malformed previously stored source")
        if item["id"] in stored:
            raise ValueError("Duplicate previous source ID")
        stored[item["id"]] = item.copy()

    timestamp = clean(scout.get("generated_at_utc"), 50)
    if not timestamp:
        raise ValueError("Source discovery missing timestamp")
    errors = scout.get("query_failures") or {}
    if not isinstance(errors, dict):
        raise ValueError("Malformed source-discovery failure report")
    offline = scout.get("offline_mode") is True
    truncated = scout.get("truncated") is True
    # Only a bounded slice of search results is ever observed.
    # An absent match is NEVER a deletion signal.
    usable = not errors and not offline and not truncated
    changes = {"new": 0, "changed": 0, "unchanged": 0,
               "not_seen_in_sample": 0}
    seen = set()
    events = list(old.get("events", []))[-MAX_EVENTS:]
    for raw in rows:
        row = normalize(raw)
        ident = row["id"]
        if ident in seen:
            raise ValueError("Duplicate source ID in a discovery snapshot")
        seen.add(ident)
        fp = fingerprint(row)
        before = stored.get(ident)
        if before is None:
            kind = "new"
            row["first_seen_utc"] = timestamp
        else:
            kind = "unchanged" if before.get("fingerprint") == fp else "changed"
            row["first_seen_utc"] = before.get("first_seen_utc") or timestamp
        changes[kind] += 1
        row["last_seen_utc"] = timestamp
        row["fingerprint"] = fp
        row["not_seen_in_latest_sample"] = False
        stored[ident] = row
        if kind != "unchanged":
            events.append({"at_utc": timestamp, "id": ident, "type": kind})
    if len(stored) > MAX_SOURCES:
        raise ValueError("Discovery would exceed bounded source-registry storage")
    if usable:
        for ident, item in stored.items():
            if ident not in seen:
                item["not_seen_in_latest_sample"] = True
                changes["not_seen_in_sample"] += 1
    scan_date = published_data_date(timestamp)
    if scan_date is None:
        raise ValueError("Source discovery timestamp is not a valid ISO date")
    for item in stored.values():
        official = audited.get(item["id"])
        declared = published_data_date(official.get("publisher_data_updated_at")) if official else None
        if declared:
            # Rank from a more specific official processing/rows timestamp
            # instead of a national catalog's manually set modified value.
            screened = {**item, "data_modified": declared.isoformat()}
            score, category, reasons = triage(screened, scan_date)
            item["publisher_data_updated_at"] = declared.isoformat()
            item["publisher_timestamp_type"] = clean(
                official.get("provider_data_timestamp_type"), 70)
            reasons.append("official_publisher_date_preferred_over_catalog_date")
        else:
            score, category, reasons = triage(item, scan_date)
            item.pop("publisher_data_updated_at", None)
            item.pop("publisher_timestamp_type", None)
        observed = schemas.get(item["id"]) or {}
        kind = observed.get("viability")
        if kind == "historical_aggregate_not_venues":
            category = "aggregated_statistics"
            score -= 24
            reasons.append("real_csv_schema_contains_only_annual_counts")
        elif kind == "concession_registry_without_visit_schedule":
            category = "concession_registry"
            score -= 18
            reasons.append("real_csv_schema_tracks_concessions_not_market_openings")
        elif kind == "market_venue_schedule_candidate":
            score += 6
            reasons.append("bounded_csv_schema_has_venue_address_and_weekday")
        if kind in (
            "historical_aggregate_not_venues",
            "concession_registry_without_visit_schedule",
            "market_venue_schedule_candidate",
            "venue_inventory_missing_visit_days",
            "manual_schema_review_required",
        ):
            item["schema_viability"] = kind
            item["schema_observed_at"] = clean(observed.get("checked_date"), 15)
            reasons.append("source_schema_observed_read_only_no_auto_import")
        else:
            item.pop("schema_viability", None)
            item.pop("schema_observed_at", None)
        item["triage_score"], item["triage_class"], item["triage_reasons"] = (
            score, category, reasons
        )
    ranked = sorted(stored.values(), key=lambda s: (
        s["not_seen_in_latest_sample"], -s["triage_score"], s["id"]
    ))
    return {
        "schema": VERSION, "last_scan_utc": timestamp,
        "discovery_is_bounded": True, "record_imports": 0,
        "source_licenses_verified_by_automation": 0,
        "sample_reliable_for_missing_match": usable,
        "scan": {
            "candidates_seen": len(seen), "total_known": len(ranked),
            "query_failures": len(errors), "offline": offline,
            "truncated": truncated, "delta": changes,
        },
        "sources": ranked,
        "events": events[-MAX_EVENTS:],
    }


def markdown(result):
    scan = result["scan"]
    kinds = Counter(item["triage_class"] for item in result["sources"])
    def escape(value):
        return clean(value, 240).replace("|", "/").replace(chr(96), "'")
    lines = [
        "# Fonti candidate — coda automatica di verifica", "",
        "**Metadati da dati.gov.it, non mercati verificati.** Nessun dataset viene importato.",
        "Licenza, editore, attualità dei calendari e schema reale richiedono prove.", "",
        f"- Fonti note: **{scan['total_known']}**; viste ora: **{scan['candidates_seen']}**.",
        f"- Nuove: **{scan['delta']['new']}**; cambiate: **{scan['delta']['changed']}**.",
        f"- Query fallite: **{scan['query_failures']}**; offline: **{scan['offline']}**.",
        f"- Probabili elenchi/sedi: **{kinds.get('market_location_candidate', 0)}**; statistiche aggregate: **{kinds.get('aggregated_statistics', 0)}**.",
        "- Il punteggio indica solo la priorità della verifica. NON è una misura di affidabilità.",
        "- La ricerca restituisce solo i primi risultati. Una fonte non vista non è stata cancellata.",
        "- Una modifica ai metadati NON dimostra che siano cambiati mercati o orari.", "",
        "| Priorità | Punti | Dataset | Tipo | Schema osservato | Editore dichiarato | Data ufficiale analizzata (se disponibile) |",
        "|---:|---:|---|---|---|---|---|",
    ]
    for i, source in enumerate(result["sources"][:20], 1):
        lines.append(
            f"| {i} | {source['triage_score']} | {escape(source['title'])} | "
            f"{escape(source['triage_class'])} | {escape(source.get('schema_viability') or 'non esplorato')} | {escape(source['organization'])} | "
            f"{escape(source.get('publisher_data_updated_at') or source['data_modified']) or 'sconosciuta'} |"
        )
    lines.extend(["", "## Risorse candidate prioritarie (URL non verificati)", ""])
    for source in result["sources"][:12]:
        resource = source["resources"][0]
        url = resource["url"]
        for character, escaped in [("(", "%28"), (")", "%29"),
                                   ("[", "%5B"), ("]", "%5D"),
                                   ("<", "%3C"), (">", "%3E"), ("|", "%7C")]:
            url = url.replace(character, escaped)
        lines.append(f"- {escape(source['title'])}: [{resource['format']}]({url})")
    lines.extend(["", "## Protocollo necessario per aggiungere una fonte", "",
        "1. Confermare che l'ente pubblica davvero il dataset e la risorsa.",
        "2. Verificare licenza e condizioni della singola distribuzione.",
        "3. Leggere un campione limitato e verificare lo schema.",
        "4. Separare calendari attuali da archivi storici, senza inventare conferme.",
        "5. Creare adapter con ID stabili, provenienza e test di regressione.",
        "6. Inserire l'adapter nella allowlist solo dopo QA.", ""])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scout", type=Path, required=True)
    parser.add_argument("--previous", type=Path,
                        default=Path("reports/automation/source-registry.json"))
    parser.add_argument("--publisher-evidence", type=Path,
                        default=Path("reports/automation/source-evidence.json"))
    parser.add_argument("--schema-evidence", type=Path)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    scout = json.loads(args.scout.read_text(encoding="utf-8"))
    prior = json.loads(args.previous.read_text(encoding="utf-8")) if args.previous.is_file() else None
    evidence = json.loads(args.publisher_evidence.read_text(encoding="utf-8")) if (
        args.publisher_evidence and args.publisher_evidence.is_file()) else None
    schema = json.loads(args.schema_evidence.read_text("utf-8")) if (
        args.schema_evidence and args.schema_evidence.is_file()) else None
    result = evaluate(scout, prior, evidence, schema)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    args.report.write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"sources_known": result["scan"]["total_known"],
                      "new": result["scan"]["delta"]["new"],
                      "changed": result["scan"]["delta"]["changed"],
                      "imports": 0}, ensure_ascii=False))


if __name__ == "__main__":
    main()
