#!/usr/bin/env python3
"""Bounded read-only schema sampling of explicitly approved official hosts.

Samples a few response bytes only; never executes remote data, persists source
rows, verifies an event, or imports a market. No arbitrary catalog URL fetching.
"""
from __future__ import annotations

import argparse
import csv
import io
import ipaddress
import json
import re
import socket
import unicodedata
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

HOSTS = frozenset({
    "opendata.comune.bologna.it",
    "www.dati.lombardia.it",
    "dati.comune.roma.it",
})
MAX_PROBES = 3
MAX_BYTES = 65536
COLUMN_ALIASES = {
    "name": ("nome_mercato", "mercato", "denominazione", "nome", "name"),
    "address": ("indirizzo", "via", "piazza", "ubicazione", "localizzazione", "sede"),
    "municipality": ("comune", "citta", "città", "municipio", "descom", "istat_comune"),
    "weekday": ("giorno", "giorni", "periodicita", "periodicità", "settimana", "frequenza"),
    "hours": ("orario", "apertura", "chiusura", "orari"),
    "latitude": ("latitudine", "latitude", "lat"),
    "longitude": ("longitudine", "longitude", "lng", "lon"),
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def safe_url(url):
    if not isinstance(url, str) or len(url) > 1100:
        return False
    try:
        p = urlsplit(url)
        return (p.scheme == "https" and p.hostname in HOSTS
                and not p.username and not p.password
                and p.port in (None, 443) and not p.fragment)
    except ValueError:
        return False


def sample_target(source):
    for resource in source.get("resources", [])[:5]:
        url = resource.get("url", "")
        if not safe_url(url):
            continue
        p = urlsplit(url)
        if p.hostname == "www.dati.lombardia.it":
            m = re.search(r"/api/views/([a-z0-9]{4}-[a-z0-9]{4})/rows\.csv", p.path)
            if m:
                return ("https://www.dati.lombardia.it/resource/" + m.group(1)
                        + ".json?%24limit=5", "JSON")
        if p.hostname == "opendata.comune.bologna.it":
            m = re.search(r"/catalog/datasets/([a-z0-9-]+)/exports/csv", p.path)
            if m:
                return ("https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/"
                        + m.group(1) + "/records?limit=5", "JSON")
        if resource.get("format", "").upper() == "CSV":
            return url, "CSV"
    return None, None


def ensure_public_dns(host):
    for entry in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM):
        address = entry[4][0]
        if not ipaddress.ip_address(address).is_global:
            raise ValueError("non-public DNS address refused")


def limited_fetch(url):
    if not safe_url(url):
        raise ValueError("unapproved official host")
    ensure_public_dns(urlsplit(url).hostname)
    request = Request(url, headers={
        "User-Agent": "MercatiItaliaReadOnlySchemaProbe/1.0",
        "Range": f"bytes=0-{MAX_BYTES - 1}",
        "Accept": "application/json,text/csv",
        "Accept-Encoding": "identity",
    })
    with build_opener(NoRedirect).open(request, timeout=10) as response:
        payload = response.read(MAX_BYTES + 1)
        return payload[:MAX_BYTES], len(payload) > MAX_BYTES


def column_name(value):
    normalized = unicodedata.normalize("NFKD", str(value)).encode(
        "ascii", "ignore").decode("ascii").casefold()
    return re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")


def infer_columns(columns):
    found = {}
    for concept, aliases in COLUMN_ALIASES.items():
        possible = []
        for original in columns:
            name = column_name(original)
            if any(alias == name or name.startswith(alias + "_")
                   or name.endswith("_" + alias) for alias in aliases):
                possible.append(original)
        if possible:
            found[concept] = possible[:6]
    return found


def extract_columns(blob, fmt, truncated=False):
    decoded = blob.decode("utf-8-sig", errors="replace")
    if fmt == "CSV":
        first_line = decoded.splitlines()[0] if decoded.splitlines() else ""
        delimiter = ";" if first_line.count(";") > first_line.count(",") else ","
        reader = csv.reader(io.StringIO(decoded), delimiter=delimiter)
        fields = next(reader, [])
    elif fmt == "JSON":
        if truncated:
            raise ValueError("JSON exceeds bounded preview; no partial parse")
        value = json.loads(decoded)
        if isinstance(value, dict):
            records = value.get("results") or value.get("features") or value.get("data") or []
        else:
            records = value
        if not isinstance(records, list) or not records:
            raise ValueError("No structured rows in response")
        sample = records[0]
        if not isinstance(sample, dict):
            raise ValueError("Rows are not objects")
        fields = list(sample.get("properties", sample).keys())
    else:
        raise ValueError("Unsupported preview format")
    fields = [str(x).strip()[:120] for x in fields if str(x).strip()][:100]
    if not fields:
        raise ValueError("No column names found")
    return fields


def survey(registry, fetch=limited_fetch, offline=False):
    if registry.get("record_imports") != 0 or registry.get("schema") != 1:
        raise ValueError("Untrusted or incompatible source registry")
    results = []
    for source in registry.get("sources", []):
        if len(results) >= MAX_PROBES:
            break
        if source.get("triage_class") == "aggregated_statistics":
            continue
        if "existing_milano_adapter_covers_dataset" in source.get("triage_reasons", []):
            continue
        url, fmt = sample_target(source)
        if not url:
            continue
        report = {
            "id": source["id"], "title": source["title"], "sample_url": url,
            "format": fmt, "status": "offline_skipped" if offline else "not_started",
            "source_license_verified": False, "events_confirmed": 0,
            "adapter_enabled": False, "fields": [], "field_hints": {},
        }
        if not offline:
            try:
                data, truncated = fetch(url)
                fields = extract_columns(data, fmt, truncated)
                report["fields"] = fields
                report["field_hints"] = infer_columns(fields)
                report["status"] = "schema_preview_only"
                report["sample_bytes"] = len(data)
                report["truncated"] = truncated
            except Exception as exc:
                report["status"] = "needs_review"
                report["error"] = type(exc).__name__ + ": " + str(exc)[:180]
        results.append(report)
    return {
        "schema": 1, "metadata_only": True, "imports": 0,
        "verified_event_count": 0, "checked_hosts": sorted(HOSTS),
        "max_requests": MAX_PROBES, "max_read_bytes_per_request": MAX_BYTES,
        "reports": results,
    }


def markdown(data):
    lines = [
        "# Campioni limitati — proposte di schema",
        "",
        "Solo lettura da una lista chiusa di domini ufficiali. Nessun record pubblicato.",
        "Campi rilevati e corrispondenze sono suggerimenti, non dati verificati.",
        "",
    ]
    for item in data["reports"]:
        lines.extend([
            "## " + item["title"].replace("\n", " ").replace("#", ""),
            "- Esito: " + item["status"],
            "- Formato: " + item["format"],
            "- Campi: " + ", ".join(item["fields"][:24]),
            "- Possibili mappature: " + json.dumps(item["field_hints"], ensure_ascii=False),
            "- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.",
            "",
        ])
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--registry", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args()
    data = survey(json.loads(args.registry.read_text("utf-8")), offline=args.offline)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n", "utf-8")
    args.report.write_text(markdown(data), "utf-8")
    print(json.dumps({"sampled": len(data["reports"]),
                      "schema_preview": sum(x["status"] == "schema_preview_only" for x in data["reports"]),
                      "imports": 0}))


if __name__ == "__main__":
    main()
