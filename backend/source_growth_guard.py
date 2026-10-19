#!/usr/bin/env python3
"""Fail-closed read-only checks for the scheduled national source-growth audit.

The audit may inspect every enabled source contract, not just the first
municipality ever approved. Nothing here authorizes a market import.
The catalog publication has separate, stricter guards.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from source_contract_activation import validate_admissions
from source_contract_ingest import observed_source_date
from source_lifecycle import digest, validate_contracts


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _git_blob_sha1(data: bytes) -> str:
    return hashlib.sha1(b"blob " + str(len(data)).encode("ascii") + b"\0" + data).hexdigest()


def validate_growth_source_lifecycle(lifecycle: dict, manifest: dict,
                                     *, root: Path = Path(".")) -> dict:
    """Return a small count-only certificate, or raise ValueError.

    Registry changes require the existing policy-pinned Git blob SHA-1 values
    and one publisher-level approval certificate per approved source.
    The lifecycle can only read/stage source rows. It may never import,
    geocode, confirm an opening, or change an existing market.
    """
    root = Path(root)
    policy = _read_json(root / "backend/autopilot_policy.json")
    contract_path = root / "backend/data/market-source-contracts.json"
    registry_path = root / "backend/data/approved-source-admissions.json"
    contract_bytes = contract_path.read_bytes()
    approval_bytes = registry_path.read_bytes()
    if (policy.get("source_lifecycle", {}).get("enabled") is not True
            or policy.get("source_lifecycle", {}).get("reviewed_contract_blob_sha1")
               != _git_blob_sha1(contract_bytes)
            or policy.get("source_contract_admissions", {}).get("enabled") is not True
            or policy.get("source_contract_admissions", {}).get("approved_registry_blob_sha1")
               != _git_blob_sha1(approval_bytes)):
        raise ValueError("Unreviewed changes to source contracts or approval registry")

    contracts = json.loads(contract_bytes)
    approvals = json.loads(approval_bytes)
    validate_contracts(contracts)
    approved = validate_admissions(contracts, approvals)
    raw_profiles = {p["id"]: p for p in contracts["raw_profiles"] if p.get("enabled") is True}
    if len(raw_profiles) > 2:
        raise ValueError("Source-growth audit exceeded bounded daily source quota")
    for sid, certificate in approved.items():
        profile = raw_profiles.get(sid)
        if (not profile
                or certificate.get("reviewed_profile_sha256") != digest(profile)
                or certificate.get("mode") != "approved_dev_only"
                or certificate.get("source_record_kind") != profile["row_kind"]
                or certificate.get("identity_granularity") != profile["row_kind"]
                or certificate.get("publisher_license_evidence_url") != profile["attribution_url"]
                or certificate.get("source_specific_geo_approval") is not False):
            raise ValueError("Publisher profile does not match its reviewed DEV certificate")
    if (not isinstance(manifest, dict)
            or type(manifest.get("total")) is not int or manifest["total"] <= 0
            or not isinstance(lifecycle, dict)
            or lifecycle.get("schema") != 1
            or lifecycle.get("source_contract_schema") != 1
            or lifecycle.get("read_only") is not True
            or lifecycle.get("catalog_count") != manifest["total"]
            or lifecycle.get("registry_sha256") != digest(contracts)
            or any(type(lifecycle.get(field)) is not int or lifecycle[field] != 0
                   for field in ("market_imports", "market_updates",
                                 "market_confirmations", "market_identity_deletions"))):
        raise ValueError("Source lifecycle modified the catalog or lost source evidence")
    reference_value = lifecycle.get("reference_date")
    try:
        reference = date.fromisoformat(reference_value)
    except (TypeError, ValueError):
        raise ValueError("Source lifecycle needs an exact reference date") from None
    if reference.isoformat() != reference_value:
        raise ValueError("Source lifecycle needs an exact reference date")

    reports = lifecycle.get("sources")
    if (not isinstance(reports, dict) or set(reports) != set(raw_profiles)
            or lifecycle.get("checked_source_profiles") != len(reports)):
        raise ValueError("Audit did not cover the exact enabled publisher contracts")
    source_checks = lifecycle.get("source_checks")
    if (not isinstance(source_checks, dict)
            or any(type(value) is not int or value < 0 for value in source_checks.values())
            or source_checks.get("raw_schema_or_identity_change_requires_review", 0)):
        raise ValueError("Publisher source schema/identity changed: review required")

    for sid, row in reports.items():
        p = raw_profiles[sid]
        if not isinstance(row, dict) or row.get("source_id") != sid:
            raise ValueError("Malformed or misattributed source scan")
        if (row.get("source_url") != p["resource_url"]
                or row.get("publisher") != p["publisher"]
                or row.get("profile_fingerprint", digest(p)) != digest(p)):
            raise ValueError("Source scan does not belong to the reviewed publisher")
        for field in ("catalog_records_imported", "catalog_records_modified",
                      "individual_market_openings_verified",
                      "existing_record_ids_deleted", "new_precise_coordinates",
                      "new_directions_enabled"):
            if row.get(field, 0) != 0:
                raise ValueError("Source scan exceeded read-only market permissions")
        if (row.get("license_reviewed_for_automatic_publication", False) is not False
                or row.get("source_data_marked_current_by_fetch_time", False) is not False):
            raise ValueError("Source scan falsely certified license or current opening")

        # A network outage preserves previous evidence. A parser/schema
        # change NEVER inherits old approval silently.
        status = row.get("last_check_status")
        if status not in (None, "transport_unavailable"):
            raise ValueError("Changed publisher format/identity needs separate review")
        if row.get("unavailable_no_market_inference") is True:
            if row.get("source_snapshot_sha256"):
                raise ValueError("Unavailable source cannot invent a fresh snapshot")
            continue
        if row.get("stale_snapshot_carry_forward") is True and status != "transport_unavailable":
            raise ValueError("Old evidence cannot be presented as a new source read")

        snapshot = row.get("source_snapshot_sha256")
        if not isinstance(snapshot, str) or len(snapshot) != 64:
            raise ValueError("Source has neither validated snapshot nor outage status")
        staged = row.get("source_stage")
        counts = row.get("counts")
        if (not isinstance(staged, dict) or not isinstance(counts, dict)
                or staged.get("source_snapshot_sha256") != snapshot
                or staged.get("source_id") != sid
                or staged.get("source_url") != p["resource_url"]
                or staged.get("profile_sha256") != digest(p)
                or staged.get("publisher_dataset_date") != observed_source_date(
                    p, staged, today=reference)
                or staged.get("source_kind") != p["row_kind"]
                or staged.get("publication_enabled") is not False
                or staged.get("source_license_automatically_verified") is not False
                or any(staged.get(field) != 0 for field in
                       ("verified_openings_created",
                        "existing_market_identities_deleted",
                        "existing_market_ids_modified",
                        "precise_coordinates_created", "directions_enabled"))):
            raise ValueError("Raw source lacks safe, source-bound, read-only staging")
        categories = staged.get("counts")
        holds = staged.get("review_reason_counts")
        if not isinstance(categories, dict) or not isinstance(holds, dict):
            raise ValueError("Source staging lacks reconciliation counters")
        observed = counts.get("rows_observed")
        identities = categories.get("source_market_identities", 0)
        duplicate = holds.get("duplicate_publisher_identity", 0)
        safe = staged.get("safe_candidates_not_published")
        if (any(type(n) is not int or n < 0 for n in
                [observed, identities, duplicate, safe, *holds.values()])
                or categories.get("raw_rows_scanned") != observed
                or identities + duplicate > observed or safe > identities):
            raise ValueError("Publisher staging summary does not match source rows")

    return {"sources_checked": len(reports), "market_ids_preserved": manifest["total"],
            "market_imports": 0, "individual_openings_verified": 0}
