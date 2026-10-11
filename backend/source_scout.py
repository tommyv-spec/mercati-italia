#!/usr/bin/env python3
"""Autonomous but read-only public Italian open-data source discovery.

Searches a *bounded number* of official national catalog metadata records.
Never downloads bulk CSVs, never scrapes non-permitted websites, never imports
new markets, and never treats claimed license metadata as confirmed rights.
Any new importer must pass adapter tests and license review before activation.

API: https://www.dati.gov.it/opendata/api/3/action/package_search
"""
from __future__ import annotations

import argparse
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

CATALOG = "https://www.dati.gov.it/opendata/api/3/action/package_search"
QUERIES = ("mercati settimanali", "mercati ambulanti", "mercati rionali", "fiere mercati")
FORMAT_SCORE = {"GEOJSON": 9, "JSON": 8, "CSV": 8, "XLSX": 5, "XLS": 3, "KML": 4}
BAD_TOPICS = ("borsa", "finanziar", "immobil", "lavoro", "credito", "azioni", "prezzi",
              "supermercati", "analisi del mercato", "marketing")
POSITIVE = ("mercati", "mercato settimanale", "commercio su area pubblica", "mercati rionali",
            "commercio ambulante", "fiere e mercati")
MAX_JSON_BYTES = 2_500_000
ROWS_PER_QUERY = 22


def clean_text(value):
    return re.sub(r"\s+", " ", str(value or "")).strip()


def api_query(term: str, timeout: float = 20.0) -> list:
    query = urlencode({"q": term, "rows": ROWS_PER_QUERY})
    target = CATALOG + "?" + query
    if urlsplit(target).hostname != "www.dati.gov.it":
        raise ValueError("Metadata requests may only target Italy's national catalog")
    request = Request(target, headers={
        "User-Agent": "MercatiItaliaOfficialMetadataScout/1.0 (limited read-only discovery)",
        "Accept": "application/json",
    })
    with urlopen(request, timeout=timeout) as response:
        blob = response.read(MAX_JSON_BYTES + 1)
    if len(blob) > MAX_JSON_BYTES:
        raise ValueError("Government CKAN metadata response exceeded safety limit")
    payload = json.loads(blob)
    if payload.get("success") is not True:
        raise ValueError("CKAN API did not return a successful result")
    result = payload.get("result", {}).get("results", [])
    if not isinstance(result, list):
        raise ValueError("CKAN package_search result malformed")
    return result


def license_status(row: dict) -> str:
    text = clean_text(row.get("license_id") or row.get("license_title")).lower()
    if any(x in text for x in ("cc-by-4", "cc_by_4", "cc by 4", "creativecommons.org/licenses/by/4.0",
                               "cc0", "creativecommons.org/publicdomain/zero")):
        return "claimed_open_license_review_required"
    return "manual_license_review_required"


def candidate(row: dict) -> dict | None:
    if not isinstance(row, dict):
        return None
    title = clean_text(row.get("title"))
    plain = title.lower()
    if not title or any(bad in plain for bad in BAD_TOPICS) or not any(pos in plain for pos in POSITIVE):
        return None
    sources = []
    for item in row.get("resources") or []:
        if not isinstance(item, dict):
            continue
        format_name = clean_text(item.get("format")).upper().replace(".", "")
        url = clean_text(item.get("url"))
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname:
            continue
        if format_name not in FORMAT_SCORE:
            continue
        sources.append({
            "url": url[:1000],
            "format": format_name,
            "name": clean_text(item.get("name"))[:150],
        })
    if not sources:
        return None
    org = row.get("organization") or {}
    if not isinstance(org, dict):
        org = {}
    status = license_status(row)
    modified = clean_text(row.get("metadata_modified") or row.get("modified"))
    freshness = 0
    try:
        if modified:
            year = int(modified[:4])
            freshness = 3 if year >= 2025 else (1 if year >= 2023 else 0)
    except ValueError:
        pass
    score = max(FORMAT_SCORE[s["format"]] for s in sources) + freshness
    score += 5 if ("settimanali" in plain or "mercati rionali" in plain) else 0
    score += 2 if status == "claimed_open_license_review_required" else 0
    return {
        "id": clean_text(row.get("id") or row.get("name"))[:160],
        "title": title[:240],
        "organization": clean_text(org.get("title") or row.get("author"))[:180],
        "metadata_modified": modified[:30],
        "license": clean_text(row.get("license_title") or row.get("license_id"))[:180],
        "license_status": status,
        "score": score,
        "resources": sorted(sources, key=lambda s: -FORMAT_SCORE[s["format"]])[:5],
        "automatic_import_allowed": False,
        "next_action": "Review license, actual schema and municipal provenance; build vetted adapter + tests.",
    }


def discover(offline: bool = False, fixtures: dict | None = None) -> dict:
    candidates = {}
    errors = {}
    for term in QUERIES:
        if fixtures is not None:
            records = fixtures.get(term, [])
        elif offline:
            records = []
        else:
            try:
                records = api_query(term)
            except Exception as exc:
                errors[term] = type(exc).__name__ + ": " + str(exc)[:250]
                records = []
        for row in records:
            item = candidate(row)
            if item and item["id"]:
                candidates[item["id"]] = item
    ranked = sorted(candidates.values(), key=lambda d: (-d["score"], d["title"]))
    return {
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "catalog": CATALOG,
        "queries": list(QUERIES),
        "query_failures": errors,
        "metadata_only": True,
        "no_unapproved_source_imports": True,
        "candidates": ranked[:80],
    }


def markdown(result: dict) -> str:
    lines = [
        "# Fonti ufficiali candidate — rilevamento automatico",
        "",
        "Questo elenco **non** autorizza il riuso dei dati. È generato da metadati nazionali;",
        "ogni fonte richiede revisione licenza, schema, aggiornamento e un adapter verificato.",
        "",
        f"Dataset candidati: **{len(result['candidates'])}**; query fallite: **{len(result['query_failures'])}**.",
        "",
        "| Punteggio | Dataset | Ente dichiarato | Licenza da verificare |",
        "|---:|---|---|---|",
    ]
    for entry in result["candidates"][:30]:
        title = entry["title"].replace("|", " / ")
        org = entry["organization"].replace("|", " / ")
        lines.append(f"| {entry['score']} | {title} | {org} | {entry['license']} |")
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out", type=Path, default=Path("autopilot-output/official-candidates.json"))
    p.add_argument("--offline", action="store_true")
    args = p.parse_args()
    result = discover(offline=args.offline)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    args.out.with_suffix(".md").write_text(markdown(result), encoding="utf-8")
    print(json.dumps({
        "candidates": len(result["candidates"]),
        "query_failures": result["query_failures"],
        "new_source_imports": 0
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
