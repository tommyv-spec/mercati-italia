#!/usr/bin/env python3
"""Source rights and freshness evidence for exactly three vetted publishers.

Reads publisher DATASET METADATA only, never full records. Makes no changes
to source adapters, catalog, credentials, public API or verification badges.
Evidence is advisory and fail-closed: no source gets import permission.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import socket
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener

SCHEMA = 1
MAX_BYTES = 300_000
SPECS = (
    {
        "id": "0bb2a3cb-a3d0-44ef-9053-061006c8cd50",
        "slug": "bologna",
        "publisher": "Comune di Bologna",
        "endpoint": "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/mercati-e-fiere",
        "catalog_page": "https://www.dati.gov.it/node/view-dataset/dataset?id=0bb2a3cb-a3d0-44ef-9053-061006c8cd50",
        "dataset_key": "mercati-e-fiere",
        "market_record_note": "Dataset includes fairs and farmers markets; confirm types individually.",
    },
    {
        "id": "2e41941b-80fb-4ded-8330-427383f725f8",
        "slug": "lombardia",
        "publisher": "Regione Lombardia",
        "endpoint": "https://www.dati.lombardia.it/api/views/68zx-njaw.json",
        "catalog_page": "https://www.dati.gov.it/node/view-dataset/dataset?id=2e41941b-80fb-4ded-8330-427383f725f8",
        "dataset_key": "68zx-njaw",
        "market_record_note": "One market may have a row per weekday; municipality feed coverage may vary.",
    },
    {
        "id": "2d7352f7-7d9f-4be7-927b-de1b760993c3",
        "slug": "roma",
        "publisher": "Roma Capitale",
        "endpoint": "https://dati.comune.roma.it/catalog/api/3/action/package_show?id=e2e30174-ba7f-4319-bf4a-c13f80278c0c",
        "catalog_page": "https://www.dati.gov.it/node/view-dataset/dataset?id=2d7352f7-7d9f-4be7-927b-de1b760993c3",
        "dataset_key": "e2e30174-ba7f-4319-bf4a-c13f80278c0c",
        "resource_key": "61ae5f8b-8ac5-44c0-ad82-6d342d0c45d6",
        "market_record_note": "Selected CSV is explicitly Giugno 2022; historical hours cannot confirm 2026.",
    },
)
ENDPOINTS = frozenset(s["endpoint"] for s in SPECS)


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def metadata_fetch(url):
    """Never follow URLs supplied by downloaded metadata or source registry."""
    if url not in ENDPOINTS:
        raise ValueError("Unapproved publisher metadata endpoint")
    host = urlsplit(url).hostname
    for entry in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(entry[4][0]).is_global:
            raise ValueError("Refusing private DNS target")
    req = Request(url, headers={
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": "MercatiItaliaMetadataEvidence/1.0",
    })
    with build_opener(NoRedirect).open(req, timeout=15) as response:
        payload = response.read(MAX_BYTES + 1)
    if len(payload) > MAX_BYTES:
        raise ValueError("Official metadata response exceeded safe size limit")
    return payload


def date_value(raw):
    """Only ISO dates and UTC epoch seconds. Unknown timestamps stay unknown."""
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        try:
            if 0 < raw < 4102444800:
                return datetime.fromtimestamp(raw, tz=timezone.utc).date()
        except (OverflowError, OSError, ValueError):
            return None
    if not isinstance(raw, str) or not raw:
        return None
    try:
        return date.fromisoformat(raw[:10])
    except ValueError:
        return None


def license_code(raw):
    """Exact known identifiers only, no optimistic keyword matching."""
    if not isinstance(raw, str) or not raw.strip():
        return None
    normalized = raw.lower().replace("_", "-").strip()
    if ("creativecommons.org/publicdomain/zero/1.0" in normalized
            or re.search(r"\bcc0(?:\s|-)?1\.0\b", normalized)
            or normalized == "cc0"):
        return "CC0-1.0"
    if ("creativecommons.org/licenses/by/4.0" in normalized
            or "a21-ccby40" in normalized
            or re.search(r"\bcc[\s-]*by[\s-]*4\.0\b", normalized)
            or normalized == "cc-by4"):
        if ("nc" in normalized or "noncommercial" in normalized
                or "nd" in normalized or "sharealike" in normalized):
            return None
        return "CC-BY-4.0"
    return None


def license_fields(raw):
    if isinstance(raw, dict):
        return str(raw.get("name") or raw.get("title") or raw.get("id") or ""), (
            str(raw.get("termsLink") or raw.get("url") or "")
        )
    return str(raw or ""), ""


def bologna_metadata(value, spec):
    if not isinstance(value, dict) or value.get("dataset_id") != spec["dataset_key"]:
        raise ValueError("Bologna metadata returned different dataset")
    metas = value.get("metas") or {}
    if not isinstance(metas, dict):
        raise ValueError("Malformed Bologna dataset metadata")
    default = metas.get("default", metas)
    if not isinstance(default, dict):
        default = {}
    dcat = metas.get("dcat") or {}
    if not isinstance(dcat, dict):
        dcat = {}
    license_text, license_url = license_fields(
        default.get("license") or dcat.get("license"))
    updated = (
        date_value(default.get("modified"))
        or date_value(default.get("data_processed"))
    )
    return {
        "publisher_license": license_text,
        "publisher_license_url": license_url,
        "publisher_data_modified": updated,
        "provider_data_timestamp_type": "publisher_dataset_modified" if updated else "unknown",
        "publisher_metadata_modified": date_value(default.get("metadata_processed")),
        "publisher_identifier": value["dataset_id"],
        "distribution_specific_license": None,
        "resource_version_year": None,
    }


def lombardia_metadata(value, spec):
    if not isinstance(value, dict) or str(value.get("id", "")) != spec["dataset_key"]:
        raise ValueError("Lombardia metadata returned different dataset")
    license_text, license_url = license_fields(value.get("license"))
    return {
        "publisher_license": license_text,
        "publisher_license_url": license_url,
        "publisher_data_modified": date_value(value.get("rowsUpdatedAt")),
        "provider_data_timestamp_type": "publisher_rows_updated_at",
        "publisher_metadata_modified": date_value(value.get("viewLastModified")),
        "publisher_identifier": str(value["id"]),
        "distribution_specific_license": None,
        "resource_version_year": None,
    }


def roma_metadata(value, spec):
    if not isinstance(value, dict) or value.get("success") is not True:
        raise ValueError("Roma CKAN endpoint did not report success")
    meta = value.get("result")
    if not isinstance(meta, dict) or str(meta.get("id", "")) != spec["dataset_key"]:
        raise ValueError("Roma CKAN returned different dataset")
    resources = meta.get("resources") or []
    resource = next((r for r in resources if isinstance(r, dict)
                     and str(r.get("id", "")) == spec["resource_key"]), None)
    if resource is None:
        raise ValueError("Expected Roma June-2022 resource missing")
    license_text, license_url = license_fields(
        resource.get("license_type") or resource.get("license")
        or meta.get("license_title") or meta.get("license_id"))
    edition = (str(resource.get("name") or "") + " " +
               str(resource.get("url") or "")).lower()
    years = [int(y) for y in re.findall(r"(?<!\d)20\d{2}(?!\d)", edition)]
    return {
        "publisher_license": license_text,
        "publisher_license_url": license_url,
        "publisher_data_modified": date_value(resource.get("last_modified")),
        "provider_data_timestamp_type": "resource_last_modified",
        "publisher_metadata_modified": date_value(meta.get("metadata_modified")),
        "publisher_identifier": str(meta["id"]),
        "distribution_specific_license": bool(
            resource.get("license_type") or resource.get("license")),
        "resource_version_year": min(years) if years else None,
        "publisher_resource_id": spec["resource_key"],
    }


PARSERS = {"bologna": bologna_metadata, "lombardia": lombardia_metadata,
           "roma": roma_metadata}


def evaluate(registry, fetch=metadata_fetch, today=None, offline=False):
    today = today or date.today()
    if (not isinstance(registry, dict) or registry.get("schema") != 1
            or registry.get("record_imports") != 0
            or not isinstance(registry.get("sources"), list)):
        raise ValueError("Invalid or untrusted source registry")
    source_by_id = {item["id"]: item for item in registry["sources"]
                    if isinstance(item, dict) and item.get("id")}
    rows = []
    for spec in SPECS:
        item = source_by_id.get(spec["id"])
        out = {
            "source_id": spec["id"], "publisher": spec["publisher"],
            "catalog_page": spec["catalog_page"],
            "publisher_metadata_url": spec["endpoint"],
            "publisher_data_updated_at": None, "publisher_metadata_updated_at": None,
            "publisher_license_claim": None, "catalog_license_claim": (
                str(item.get("license") or "")[:180] if item else None
            ),
            "publisher_license_code": None, "catalog_license_code": None,
            "license_comparison": "not_evaluated",
            "status": "offline" if offline else "not_checked",
            "market_events_confirmed": 0,
            "import_permission_granted": False,
            "license_legally_reviewed": False,
            "record_level_freshness_verified": False,
            "publisher_claims_are_not_legal_review": True,
            "market_record_note": spec["market_record_note"],
            "review_required": ["license_terms", "attribution",
                                "market_identity", "operating_dates", "coverage"],
        }
        if not item:
            out["status"] = "registry_source_not_found"
            rows.append(out)
            continue
        out["catalog_license_code"] = license_code(out["catalog_license_claim"])
        if not offline:
            try:
                payload = fetch(spec["endpoint"])
                if isinstance(payload, dict):  # deterministic fixtures only
                    obj = payload
                    raw_sha = hashlib.sha256(json.dumps(
                        obj, sort_keys=True, separators=(",", ":")
                    ).encode()).hexdigest()
                else:
                    if not isinstance(payload, bytes) or len(payload) > MAX_BYTES:
                        raise ValueError("Invalid or oversized publisher metadata payload")
                    raw_sha = hashlib.sha256(payload).hexdigest()
                    obj = json.loads(payload.decode("utf-8-sig"))
                parsed = PARSERS[spec["slug"]](obj, spec)
                out["status"] = "metadata_checked"
                out["publisher_response_sha256"] = raw_sha
                out["publisher_identifier"] = parsed["publisher_identifier"]
                out["publisher_license_claim"] = parsed["publisher_license"][:200]
                out["publisher_license_reference"] = parsed["publisher_license_url"][:500]
                out["publisher_license_code"] = license_code(
                    parsed["publisher_license_url"]) or license_code(parsed["publisher_license"])
                out["distribution_specific_license"] = parsed["distribution_specific_license"]
                out["publisher_data_updated_at"] = (
                    parsed["publisher_data_modified"].isoformat()
                    if parsed["publisher_data_modified"] else None)
                out["publisher_metadata_updated_at"] = (
                    parsed["publisher_metadata_modified"].isoformat()
                    if parsed["publisher_metadata_modified"] else None)
                out["provider_data_timestamp_type"] = parsed["provider_data_timestamp_type"]
                if parsed["publisher_data_modified"]:
                    days = (today - parsed["publisher_data_modified"]).days
                    out["source_data_age_days"] = days
                    out["source_data_age_label"] = (
                        "future_timestamp_needs_review" if days < -1
                        else "dataset_updated_within_365d" if days <= 365
                        else "dataset_metadata_over_365d")
                else:
                    out["source_data_age_label"] = "dataset_update_unknown"
                if parsed["resource_version_year"]:
                    out["edition_year"] = parsed["resource_version_year"]
                    if parsed["resource_version_year"] < today.year:
                        out["review_required"].append("historical_resource_edition")
                first, second = out["publisher_license_code"], out["catalog_license_code"]
                out["license_comparison"] = (
                    "publisher_and_catalog_agree_review_required" if first and first == second
                    else "conflicting_claims_review_required" if first and second
                    else "publisher_claim_missing_review_required" if not first
                    else "national_catalog_claim_missing_review_required")
            except Exception as exc:
                out["status"] = "needs_review"
                out["error"] = type(exc).__name__ + ": " + str(exc)[:200]
        rows.append(out)
    return {
        "schema": SCHEMA,
        "reference_date": today.isoformat(),
        "offline": bool(offline),
        "source_requests_max": len(SPECS),
        "max_response_bytes_per_source": MAX_BYTES,
        "market_imports": 0,
        "market_events_confirmed": 0,
        "legal_license_approvals": 0,
        "source_evidence": rows,
    }


def markdown(report):
    lines = [
        "# Evidenze delle fonti: diritti e attualità",
        "",
        "I metadati ufficiali descrivono dataset; non confermano aperture, giorni o presenze nel 2026.",
        "Le licenze dichiarate sono confrontate, ma la verifica legale resta separata.",
        "Nessuna fonte è autorizzata all'import da questo controllo.",
        "",
        "| Fonte | Metadati | Licenza dichiarata | Confronto | Ultimo dato dichiarato |",
        "|---|---|---|---|---|",
    ]
    for row in report["source_evidence"]:
        publisher = row["publisher"].replace("|", "/")
        lic = str(row.get("publisher_license_code") or "non disponibile")
        lines.append(
            f"| {publisher} | {row['status']} | {lic} | "
            f"{row['license_comparison']} | {row['publisher_data_updated_at'] or 'sconosciuto'} |")
    lines.extend(["", "## Elementi da verificare", ""])
    for row in report["source_evidence"]:
        lines.extend([
            "### " + row["publisher"],
            "- [Pagina del catalogo nazionale](" + row["catalog_page"] + ")",
            "- [Endpoint ufficiale controllato](" + row["publisher_metadata_url"] + ")",
            "- Stato fonte: " + row["status"],
            "- Note: " + row["market_record_note"],
            "- Controlli ancora richiesti: " + ", ".join(row["review_required"]),
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
    registry = json.loads(args.registry.read_text("utf-8"))
    result = evaluate(registry, offline=args.offline)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n", "utf-8")
    args.report.write_text(markdown(result), "utf-8")
    print(json.dumps({
        "sources": len(result["source_evidence"]),
        "readable": sum(r["status"] == "metadata_checked" for r in result["source_evidence"]),
        "review_required": sum(r["status"] != "metadata_checked" for r in result["source_evidence"]),
        "market_imports": 0,
    }))


if __name__ == "__main__":
    main()
