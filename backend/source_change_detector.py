#!/usr/bin/env python3
"""Deterministic diff of publisher dataset metadata between scheduled scans.

This is a lead for new adapter/QA work, never proof that an individual
market was updated, licensed, open or confirmed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def compare(now, prior=None, corciano_current=None, corciano_previous=None):
    if now.get("schema") != 1 or now.get("market_imports") != 0:
        raise ValueError("Invalid publisher-evidence snapshot")
    if prior is not None and (
        prior.get("schema") != 1 or prior.get("market_imports") != 0
    ):
        raise ValueError("Invalid previously recorded evidence")
    by_id = {
        item["source_id"]: item for item in (prior or {}).get("source_evidence", [])
        if item.get("source_id")
    }
    results = []
    counts = {
        "first_observation": 0,
        "unchanged": 0,
        "publisher_metadata_changed": 0,
        "publisher_data_date_advanced": 0,
        "publisher_data_date_rolled_back": 0,
        "timestamp_interpretation_corrected": 0,
        "recovered": 0,
        "publisher_unavailable": 0,
        "municipal_csv_bytes_changed": 0,
        "municipal_csv_first_observation": 0,
    }
    for row in now.get("source_evidence", []):
        sid = row.get("source_id")
        if not sid:
            raise ValueError("Publisher record missing stable ID")
        old = by_id.get(sid)
        if row.get("status") != "metadata_checked":
            kind = "publisher_unavailable"
        elif old is None:
            kind = "first_observation"
        elif old.get("status") != "metadata_checked":
            kind = "recovered"
        else:
            old_date = old.get("publisher_data_updated_at")
            new_date = row.get("publisher_data_updated_at")
            old_semantics = old.get("provider_data_timestamp_type")
            new_semantics = row.get("provider_data_timestamp_type")
            if old_semantics and new_semantics and old_semantics != new_semantics:
                # A corrected ingestion-vs-manual-modification policy is
                # our interpretation change, not a supplier data rollback.
                kind = "timestamp_interpretation_corrected"
            elif old_date and new_date and new_date > old_date:
                kind = "publisher_data_date_advanced"
            elif old_date and new_date and new_date < old_date:
                kind = "publisher_data_date_rolled_back"
            elif old.get("publisher_response_sha256") != row.get("publisher_response_sha256"):
                kind = "publisher_metadata_changed"
            else:
                kind = "unchanged"
        counts[kind] += 1
        results.append({
            "source_id": sid,
            "publisher": str(row.get("publisher") or "")[:100],
            "change_type": kind,
            "prior_data_date": old.get("publisher_data_updated_at") if old else None,
            "current_data_date": row.get("publisher_data_updated_at"),
            "prior_timestamp_kind": old.get("provider_data_timestamp_type") if old else None,
            "current_timestamp_kind": row.get("provider_data_timestamp_type"),
            "events_confirmed": 0,
            "automatic_import_allowed": False,
        })
    # Corciano's CSV has no row-level timestamp. A publisher file byte
    # change is a reviewable signal, not proof of current market hours.
    if corciano_current is not None:
        now_csv, old_csv = corciano_current, corciano_previous or {}
        if (now_csv.get("schema") != 1 or
                now_csv.get("source_prefix") != "pg-corciano-" or
                now_csv.get("market_confirmations") != 0 or
                now_csv.get("deleted_existing_records") != 0):
            raise ValueError("Untrusted current municipality review")
        if corciano_previous is not None and (
            old_csv.get("schema") != 1 or
            old_csv.get("source_prefix") != "pg-corciano-"
        ):
            raise ValueError("Untrusted previous municipality review")
        new_hash = now_csv.get("source_csv_sha256")
        old_hash = old_csv.get("source_csv_sha256")
        if now_csv.get("source_total", 0):
            if (not isinstance(new_hash, str) or len(new_hash) != 64
                    or any(c not in "0123456789abcdef" for c in new_hash)):
                raise ValueError("Municipal CSV source SHA missing")
            if not old_hash:
                kind = "municipal_csv_first_observation"
            elif old_hash != new_hash:
                kind = "municipal_csv_bytes_changed"
            else:
                kind = "unchanged"
            counts[kind] += 1
            results.append({
                "source_id": "corciano-municipal-csv",
                "publisher": "Comune di Corciano",
                "change_type": kind,
                "prior_data_date": None,
                "current_data_date": None,
                "publisher_file_sha256": new_hash,
                "dataset_date_still_requires_review": True,
                "events_confirmed": 0,
                "automatic_import_allowed": False,
            })
    return {
        "schema": 1,
        "reference_date": now.get("reference_date"),
        "dataset_timestamp_changes_are_not_record_confirmations": True,
        "imported_markets": 0,
        "results": results,
        "counts": counts,
    }


def markdown(report):
    lines = [
        "# Modifiche dichiarate dai publisher",
        "",
        "Un metadato aggiornato non equivale a un calendario verificato.",
        "Questo controllo serve a individuare dove testare un importer già autorizzato.",
        "",
        "| Fonte | Tipo modifica | Data precedente | Data corrente |",
        "|---|---|---|---|",
    ]
    for item in report["results"]:
        lines.append(
            f"| {item['publisher'].replace('|', '/')} | {item['change_type']} | "
            f"{item['prior_data_date'] or '-'} | {item['current_data_date'] or '-'} |"
        )
    lines.extend(["", "Nessuna licenza, evento o import viene approvato automaticamente.", ""])
    return "\n".join(lines)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--current", type=Path, required=True)
    p.add_argument("--previous", type=Path,
                   default=Path("reports/automation/source-evidence.json"))
    p.add_argument("--corciano-current", type=Path)
    p.add_argument("--corciano-previous", type=Path,
                   default=Path("reports/automation/corciano-overlaps.json"))
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    args = p.parse_args()
    current = json.loads(args.current.read_text("utf-8"))
    previous = json.loads(args.previous.read_text("utf-8")) if args.previous.is_file() else None
    now_csv = json.loads(args.corciano_current.read_text("utf-8")) if (
        args.corciano_current and args.corciano_current.is_file()) else None
    old_csv = json.loads(args.corciano_previous.read_text("utf-8")) if (
        args.corciano_previous and args.corciano_previous.is_file()) else None
    value = compare(current, previous, now_csv, old_csv)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    args.report.write_text(markdown(value), encoding="utf-8")
    print(json.dumps(value["counts"]))


if __name__ == "__main__":
    main()
