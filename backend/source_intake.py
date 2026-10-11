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


def fingerprint(row):
    # Harvest timestamps are NOT proof of changes to municipal market data.
    fields = ("title", "organization", "data_modified", "license",
              "license_status", "resources")
    payload = {key: row[key] for key in fields}
    return hashlib.sha256(json.dumps(
        payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def evaluate(scout, previous=None):
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
    ranked = sorted(stored.values(), key=lambda s: (
        s["not_seen_in_latest_sample"], -int(s.get("score", 0)), s["id"]
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
    def escape(value):
        return clean(value, 240).replace("|", "/").replace(chr(96), "'")
    lines = [
        "# Fonti candidate — coda automatica di verifica", "",
        "**Metadati da dati.gov.it, non mercati verificati.** Nessun dataset viene importato.",
        "Licenza, editore, attualità dei calendari e schema reale richiedono prove.", "",
        f"- Fonti note: **{scan['total_known']}**; viste ora: **{scan['candidates_seen']}**.",
        f"- Nuove: **{scan['delta']['new']}**; cambiate: **{scan['delta']['changed']}**.",
        f"- Query fallite: **{scan['query_failures']}**; offline: **{scan['offline']}**.",
        "- La ricerca restituisce solo i primi risultati. Una fonte non vista non è stata cancellata.",
        "- Una modifica ai metadati NON dimostra che siano cambiati mercati o orari.", "",
        "| Priorità | Dataset | Editore dichiarato | Licenza dichiarata | Data dati dichiarata |",
        "|---:|---|---|---|---|",
    ]
    for i, source in enumerate(result["sources"][:20], 1):
        lines.append(
            f"| {i} | {escape(source['title'])} | {escape(source['organization'])} | "
            f"{escape(source['license']) or 'da verificare'} | "
            f"{escape(source['data_modified']) or 'sconosciuta'} |"
        )
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
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    scout = json.loads(args.scout.read_text(encoding="utf-8"))
    prior = json.loads(args.previous.read_text(encoding="utf-8")) if args.previous.is_file() else None
    result = evaluate(scout, prior)
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
