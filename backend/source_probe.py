#!/usr/bin/env python3
"""Bounded read-only schema sampling of explicitly approved official hosts.

Samples a few response bytes only; never executes remote data, persists source
rows, verifies an event, or imports a market. No arbitrary catalog URL fetching.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import ipaddress
import json
import re
import socket
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler

HOSTS = frozenset({
    "opendata.comune.bologna.it",
    "www.dati.lombardia.it",
    "dati.comune.roma.it",
    # Manually opened and checked official CSV endpoints. Other paths on
    # these hosts are NOT trusted just because the DNS suffix matches.
    "comune.corciano.pg.it",
    "dati.veneto.it",
    "dati.lazio.it",
})
# These source IDs have a vetted adapter or completed manual source review.
# Health is measured by the adapter, not a redundant unbounded scout.
KNOWN_VETTED_SOURCE_IDS = frozenset({
    "2e41941b-80fb-4ded-8330-427383f725f8",  # Lombardia MERCap
    "62be39fe-adbe-464a-84b1-85bc060b75d2",  # Corciano
    "0bb2a3cb-a3d0-44ef-9053-061006c8cd50",  # Bologna
    "0b6c9c3c-a6c4-43b6-91f5-9445ee3cb09b",  # Milano
})
MAX_PROBES = 3
MAX_BYTES = 65536
# Exact matches are intentional. A name-like suffix may describe a district,
# note or year, not the market name. Projected x/y is never labeled lat/lon.
COLUMN_ALIASES = {
    "name": ("nome_mercato", "denominazione_mercato", "denominazione", "nome", "name"),
    "address": ("indirizzo", "indirizzi", "via", "piazza", "ubicazione",
                "localizzazione", "sede"),
    "municipality": ("comune", "citta", "descom", "nome_comune"),
    "district": ("municipio", "nome_quartiere", "nome_zona", "zona", "quartiere"),
    "weekday": ("giorno", "giorni_svolgimento", "giorno_settimana",
                "periodicita", "periodicita_tipo", "frequenza"),
    "hours": ("orario", "orari", "orario_svolgimento", "note_orari",
              "dalle_ore_invernale", "alle_ore_invernale",
              "dalle_ore_estivo", "alle_ore_estivo"),
    "latitude": ("latitudine", "latitude", "lat"),
    "longitude": ("longitudine", "longitude", "lng", "lon", "long"),
    "geometry_requires_crs_review": ("geo_x", "geo_y", "geopoint", "location"),
    "market_type": ("tipologia", "tipologia_mercato", "fiera_mercato"),
    "concession_period": ("data_validita_concessione", "data_scadenza_concessione"),
    "statistics_year": ("anno", "anno_rilevazione"),
    "statistics_count": ("mercati", "numero_mercati", "attivazioni", "cessazioni"),
    "notes": ("note_mercato", "altre_indicazioni"),
    "stable_id_candidate": ("codice_id", "codice_mercato", "id"),
}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def safe_url(url):
    if not isinstance(url, str) or len(url) > 1100:
        return False
    try:
        p = urlsplit(url)
        if (p.scheme != "https" or p.hostname not in HOSTS or
                p.username or p.password or p.port not in (None,443)
                or p.fragment):
            return False
        if p.hostname in {"dati.veneto.it","dati.lazio.it","comune.corciano.pg.it"} and p.query:
            return False
        if p.hostname == "dati.veneto.it":
            return bool(re.fullmatch(
                r"/SpodCkanApi/api/2/rest/dataset/[0-9a-f-]{36}\.csv",p.path))
        if p.hostname == "dati.lazio.it":
            return bool(re.fullmatch(
                r"/dataset/[0-9a-f-]{36}/resource/[0-9a-f-]{36}/download/[A-Za-z0-9_.-]+\.csv",
                p.path))
        if p.hostname == "comune.corciano.pg.it":
            return p.path == (
                "/download/oggetto_documenti/372/"
                "1O__Oelenco-mercati-settinamanali-comune-corciano.csv")
        return True
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
            matched = name in aliases
            if concept == "hours" and name.startswith(
                ("apertura_", "chiusura_", "dalle_ore_", "alle_ore_", "orario_")
            ):
                matched = True
            if matched:
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



def schema_viability(fields, hints):
    """Pure source-schema triage: never authorize reuse, import or verification."""
    present = {column_name(field) for field in fields}
    if ({"comune", "anno", "mercati"} <= present and
            ("attivazioni" in present or "cessazioni" in present)):
        return "historical_aggregate_not_venues"
    if {"data_validita_concessione","data_scadenza_concessione"} <= present:
        return "concession_registry_without_visit_schedule"
    if hints.get("name") and hints.get("address") and hints.get("weekday"):
        return "market_venue_schedule_candidate"
    if hints.get("name") and hints.get("address"):
        return "venue_inventory_missing_visit_days"
    return "manual_schema_review_required"


def survey(registry, fetch=limited_fetch, offline=False,
           previous=None, reference_date=None):
    if registry.get("record_imports") != 0 or registry.get("schema") != 1:
        raise ValueError("Untrusted or incompatible source registry")
    if previous is not None and (
        not isinstance(previous, dict) or previous.get("schema") != 1
        or previous.get("imports") != 0 or
        previous.get("verified_event_count") != 0
    ):
        raise ValueError("Untrusted previous bounded source schema history")
    date_key = (reference_date or date.today()).isoformat()
    history = dict((previous or {}).get("probe_history", {}))
    if len(history) > 400:
        raise ValueError("Source schema history exceeds retained upper bound")
    # Backfill the previous report once for compatible old schema snapshots.
    # This avoids re-querying the identical top three sources daily.
    for past in (previous or {}).get("reports", []):
        sid = str(past.get("id") or "")
        if sid and sid not in history:
            history[sid] = {
                "checked_date": str((previous or {}).get("reference_date") or date_key),
                "status": past.get("status"),
                "viability": past.get("schema_viability") or "legacy_probe",
                "column_fingerprint": None,
            }
    candidates = []
    for source in registry.get("sources", []):
        if source.get("id") in KNOWN_VETTED_SOURCE_IDS:
            continue
        if source.get("triage_class") == "aggregated_statistics":
            continue
        if "existing_milano_adapter_covers_dataset" in source.get("triage_reasons", []):
            continue
        url, fmt = sample_target(source)
        if not url:
            continue
        prior=history.get(source["id"], {})
        candidates.append((
            1 if prior else 0, str(prior.get("checked_date") or ""),
            -int(source.get("triage_score",0)), source["id"],
            source, url, fmt,
        ))
    # First inspect NEVER-observed official datasets, then oldest probes.
    # Stable tie breaks guarantee deterministic replay and bounded load.
    candidates.sort(key=lambda t:t[:4])
    results = []
    for _,_,_,_,source,url,fmt in candidates[:MAX_PROBES]:
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
                blockers = []
                if not report["field_hints"].get("name"):
                    blockers.append("explicit_market_name_missing")
                if not report["field_hints"].get("municipality"):
                    blockers.append("municipality_must_be_validated_from_publisher_context")
                if (report["field_hints"].get("geometry_requires_crs_review")
                        and not (report["field_hints"].get("latitude")
                                 and report["field_hints"].get("longitude"))):
                    blockers.append("geometry_crs_and_coordinate_units_unknown")
                report["review_blockers"] = blockers
                report["schema_viability"] = schema_viability(fields, report["field_hints"])
                report["status"] = "schema_preview_only"
                report["sample_bytes"] = len(data)
                report["truncated"] = truncated
            except Exception as exc:
                report["status"] = "needs_review"
                report["error"] = type(exc).__name__ + ": " + str(exc)[:180]
        results.append(report)
        fingerprint = hashlib.sha256(json.dumps(
            report.get("fields",[]), sort_keys=True,
            ensure_ascii=False, separators=(",",":")
        ).encode("utf-8")).hexdigest()
        history[source["id"]] = {
            "checked_date": date_key,
            "status": report["status"],
            "viability": report.get("schema_viability","manual_schema_review_required"),
            "column_fingerprint": fingerprint if report.get("fields") else None,
        }
    if len(history) > 400:
        raise ValueError("Schema history exceeded maximum source count")
    return {
        "schema": 1, "metadata_only": True, "imports": 0,
        "reference_date":date_key,
        "eligible_sources":len(candidates),
        "unreviewed_sources_remaining":sum(source["id"] not in history for _,_,_,_,source,_,_ in candidates),
        "probe_history":dict(sorted(history.items())),
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
        f"Fonti strutturate ammesse per probing: **{data.get('eligible_sources',0)}**; mai osservate: **{data.get('unreviewed_sources_remaining',0)}**.",
        "Ogni run controlla fino a tre fonti in rotazione, mantenendo uno storico bounded dei soli schemi.",
        "",
    ]
    for item in data["reports"]:
        lines.extend([
            "## " + item["title"].replace("\n", " ").replace("#", ""),
            "- Esito: " + item["status"],
            "- Formato: " + item["format"],
            "- Campi: " + ", ".join(item["fields"][:24]),
            "- Possibili mappature: " + json.dumps(item["field_hints"], ensure_ascii=False),
            "- Valore dello schema per futuri importatori: " + item.get("schema_viability","da controllare"),
            "- Punti da risolvere: " + ", ".join(item.get("review_blockers", [])),
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
    parser.add_argument("--previous", type=Path,
                        default=Path("reports/automation/source-probes.json"))
    args = parser.parse_args()
    before = json.loads(args.previous.read_text("utf-8")) if args.previous.is_file() else None
    data = survey(json.loads(args.registry.read_text("utf-8")),
                  offline=args.offline, previous=before)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(data, ensure_ascii=False, sort_keys=True, indent=2) + "\n", "utf-8")
    args.report.write_text(markdown(data), "utf-8")
    print(json.dumps({"sampled": len(data["reports"]),
                      "schema_preview": sum(x["status"] == "schema_preview_only" for x in data["reports"]),
                      "imports": 0}))


if __name__ == "__main__":
    main()
