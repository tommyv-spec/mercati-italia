"""Bind a publisher's dataset date to one bounded, already approved snapshot.

This module performs no requests and grants no admission or reuse permission.
``data_processed`` describes the dataset, never a verification of each market.
The caller obtains metadata before and after the body from the exact reviewed
endpoint and retains this proof with that body's SHA-256 and actual read date.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import json
import re
from datetime import date, datetime, timezone
from urllib.parse import parse_qs, urlsplit


FIXED_STRATEGY = "fixed_reviewed"
ODS_STRATEGY = "opendatasoft_data_processed_v1"
MAX_METADATA_BYTES = 65_536
_PROOF_KEYS = frozenset({
    "schema", "strategy", "profile_sha256", "source_url", "snapshot_sha256",
    "metadata_url", "dataset_id", "read_on", "source_date",
    "data_processed_timestamp", "dataset_records_count", "snapshot_records_count",
    "before_metadata_base64", "before_metadata_sha256",
    "after_metadata_base64", "after_metadata_sha256",
})
_DATE = re.compile(r"\d{4}-\d{2}-\d{2}\Z")
_TIMESTAMP = re.compile(
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})\Z"
)
_SHA256 = re.compile(r"[0-9a-f]{64}\Z")


def _iso_date(value, label):
    if not isinstance(value, str) or not _DATE.fullmatch(value):
        raise ValueError(f"Invalid {label}: an exact ISO date is required")
    try:
        return date.fromisoformat(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {label}") from exc


def _integer(value, label, *, minimum=0, maximum=1_000_000_000):
    if type(value) is not int or not minimum <= value <= maximum:
        raise ValueError(f"Invalid {label}")
    return value


def _sha256(blob):
    return hashlib.sha256(blob).hexdigest()


def _profile_digest(profile):
    try:
        encoded = json.dumps(profile, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError("Invalid source profile for snapshot proof") from exc
    return _sha256(encoded)


def _https_parts(value, label):
    if not isinstance(value, str) or not 1 <= len(value) <= 4096:
        raise ValueError(f"Invalid {label}")
    try:
        parts = urlsplit(value)
        if (parts.scheme != "https" or not parts.hostname
                or parts.username is not None or parts.password is not None
                or parts.fragment or parts.port not in (None, 443)
                or any(ch.isspace() or ord(ch) < 32 for ch in value)):
            raise ValueError(f"Invalid {label}")
    except ValueError as exc:
        raise ValueError(f"Invalid {label}") from exc
    return parts


def validate_strategy(profile):
    """Validate declarative date semantics; return the strategy without mutation.

    The legacy reviewed date remains the minimum for a dynamic strategy. This
    validation says nothing about whether a profile has an admission certificate.
    """
    if not isinstance(profile, dict):
        raise ValueError("Missing source date profile")
    _iso_date(profile.get("source_dataset_date"), "reviewed source dataset date")
    strategy = profile.get("source_date_strategy", FIXED_STRATEGY)
    if strategy == FIXED_STRATEGY:
        return strategy
    if strategy != ODS_STRATEGY:
        raise ValueError("Unsupported source date strategy")
    dataset_id = profile.get("api_dataset_id")
    if (profile.get("format") != "JSON"
            or profile.get("json_container") != "opendatasoft_v1"
            or not isinstance(dataset_id, str)
            or not re.fullmatch(r"[a-z0-9-]{3,80}", dataset_id)):
        raise ValueError("Dynamic source date requires the reviewed Opendatasoft format")
    resource = _https_parts(profile.get("resource_url"), "source resource URL")
    metadata = _https_parts(profile.get("source_metadata_url"), "source metadata URL")
    expected_metadata = (
        f"https://{resource.netloc}/api/explore/v2.1/catalog/datasets/{dataset_id}"
    )
    query = parse_qs(resource.query, keep_blank_values=True)
    if (resource.path != "/api/records/1.0/search/"
            or query.get("dataset") != [dataset_id]
            or query.get("start", ["0"]) != ["0"]
            or len(query.get("q", [])) > 1
            or profile["source_metadata_url"] != expected_metadata
            or metadata.query):
        raise ValueError("Source metadata URL or dataset does not match the approved resource")
    license_claim = profile.get("source_metadata_license")
    if (not isinstance(license_claim, str) or not 1 <= len(license_claim) <= 200
            or license_claim != license_claim.strip()):
        raise ValueError("Missing reviewed source metadata license claim")
    minimum = _integer(profile.get("min_rows"), "minimum source rows", minimum=1,
                       maximum=100_000)
    _integer(profile.get("max_rows"), "maximum source rows", minimum=minimum,
             maximum=100_000)
    _integer(profile.get("max_bytes"), "maximum source bytes", minimum=100,
             maximum=65_536)
    return strategy


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON key in source snapshot evidence")
        result[key] = value
    return result


def _invalid_constant(value):
    raise ValueError("Non-finite JSON value in source snapshot evidence")


def _json_bytes(blob, limit, label):
    if not isinstance(blob, bytes) or not 1 <= len(blob) <= limit:
        raise ValueError(f"Invalid or oversized {label} bytes")
    try:
        value = json.loads(blob.decode("utf-8"), object_pairs_hook=_unique_object,
                           parse_constant=_invalid_constant)
    except (ValueError, UnicodeError, RecursionError) as exc:
        raise ValueError(f"Invalid {label} JSON") from exc
    if not isinstance(value, dict):
        raise ValueError(f"Invalid {label} JSON object")
    return value


def _read_date(read_on, today):
    if not isinstance(today, date) or isinstance(today, datetime):
        raise ValueError("Invalid snapshot reference date")
    read_date = _iso_date(read_on, "source read date")
    if read_date > today:
        raise ValueError("Source read date is in the future")
    return read_date


def _metadata(profile, blob, *, read_date):
    value = _json_bytes(blob, MAX_METADATA_BYTES, "source metadata")
    if value.get("dataset_id") != profile["api_dataset_id"]:
        raise ValueError("Publisher metadata dataset identity changed")
    metas = value.get("metas")
    default = metas.get("default") if isinstance(metas, dict) else None
    if not isinstance(default, dict):
        raise ValueError("Missing publisher dataset metadata")
    if default.get("license") != profile["source_metadata_license"]:
        raise ValueError("Publisher metadata license changed")
    if default.get("modified_updates_on_data_change") is not False:
        raise ValueError("Publisher modification semantics changed")
    raw_timestamp = default.get("data_processed")
    if not isinstance(raw_timestamp, str) or not _TIMESTAMP.fullmatch(raw_timestamp):
        raise ValueError("Publisher data_processed requires a complete timezone timestamp")
    if raw_timestamp[-1] != "Z":
        offset = raw_timestamp[-6:]
        if int(offset[1:3]) > 23 or int(offset[4:6]) > 59 or offset == "-00:00":
            raise ValueError("Invalid or unknown publisher timestamp timezone")
    try:
        timestamp = datetime.fromisoformat(raw_timestamp.replace("Z", "+00:00"))
        timestamp = timestamp.astimezone(timezone.utc)
    except (ValueError, OverflowError) as exc:
        raise ValueError("Invalid publisher data_processed timestamp") from exc
    minimum = _iso_date(profile["source_dataset_date"], "reviewed source dataset date")
    if not minimum <= timestamp.date() <= read_date:
        raise ValueError("Publisher source date is future or precedes the reviewed minimum")
    count = _integer(default.get("records_count"), "publisher dataset records count")
    return timestamp, count


def _snapshot_count(profile, blob):
    value = _json_bytes(blob, profile["max_bytes"], "source snapshot")
    records = value.get("records")
    count = _integer(value.get("nhits"), "snapshot records count",
                     minimum=profile["min_rows"], maximum=profile["max_rows"])
    if not isinstance(records, list) or len(records) != count:
        raise ValueError("Incomplete source snapshot records")
    if any(not isinstance(row, dict) or row.get("datasetid") != profile["api_dataset_id"]
           for row in records):
        raise ValueError("Source snapshot record dataset identity changed")
    return count


def _build_proof(profile, *, snapshot_sha256, snapshot_count, before_metadata,
                 after_metadata, read_on, today):
    read_date = _read_date(read_on, today)
    before = _metadata(profile, before_metadata, read_date=read_date)
    after = _metadata(profile, after_metadata, read_date=read_date)
    if before != after:
        raise ValueError("Publisher dataset changed during the source snapshot read")
    timestamp, dataset_count = before
    _integer(snapshot_count, "snapshot records count", minimum=profile["min_rows"],
             maximum=profile["max_rows"])
    query = parse_qs(urlsplit(profile["resource_url"]).query, keep_blank_values=True)
    filtered = bool(query.get("q", [""])[0].strip())
    if dataset_count < snapshot_count or (not filtered and dataset_count != snapshot_count):
        raise ValueError("Publisher dataset and source snapshot counts do not match")
    if not isinstance(snapshot_sha256, str) or not _SHA256.fullmatch(snapshot_sha256):
        raise ValueError("Invalid source snapshot SHA-256")
    return {
        "schema": 1,
        "strategy": ODS_STRATEGY,
        "profile_sha256": _profile_digest(profile),
        "source_url": profile["resource_url"],
        "snapshot_sha256": snapshot_sha256,
        "metadata_url": profile["source_metadata_url"],
        "dataset_id": profile["api_dataset_id"],
        "read_on": read_on,
        "source_date": timestamp.date().isoformat(),
        "data_processed_timestamp": timestamp.isoformat(timespec="microseconds"),
        "dataset_records_count": dataset_count,
        "snapshot_records_count": snapshot_count,
        "before_metadata_base64": base64.b64encode(before_metadata).decode("ascii"),
        "before_metadata_sha256": _sha256(before_metadata),
        "after_metadata_base64": base64.b64encode(after_metadata).decode("ascii"),
        "after_metadata_sha256": _sha256(after_metadata),
    }


def make_snapshot_date_proof(profile, blob, *, before_metadata: bytes,
                             after_metadata: bytes, read_on: str, today: date) -> dict:
    """Create evidence from the exact body and bracketing metadata bytes."""
    if validate_strategy(profile) != ODS_STRATEGY:
        raise ValueError("Fixed reviewed source dates do not take a dynamic snapshot proof")
    count = _snapshot_count(profile, blob)
    return _build_proof(
        profile, snapshot_sha256=_sha256(blob), snapshot_count=count,
        before_metadata=before_metadata, after_metadata=after_metadata,
        read_on=read_on, today=today,
    )


def _proof_metadata(proof, prefix):
    encoded = proof.get(f"{prefix}_metadata_base64")
    if (not isinstance(encoded, str) or not encoded
            or len(encoded) > 4 * ((MAX_METADATA_BYTES + 2) // 3)):
        raise ValueError("Invalid or oversized encoded source metadata proof")
    try:
        blob = base64.b64decode(encoded, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("Invalid base64 source metadata proof") from exc
    if (not 1 <= len(blob) <= MAX_METADATA_BYTES
            or base64.b64encode(blob).decode("ascii") != encoded
            or _sha256(blob) != proof.get(f"{prefix}_metadata_sha256")):
        raise ValueError("Source metadata proof bytes or hash changed")
    return blob


def resolve_source_date(profile, *, proof=None, blob=None, snapshot_sha256=None,
                        read_on=None, today: date) -> str:
    """Resolve a date only after checking the original profile and snapshot.

    Static/export guards may omit the body but must supply its independently
    retained SHA-256. A cached proof keeps its actual read date; it cannot acquire
    a new read date from ``today`` or a new publisher date from catalog imports.
    """
    strategy = validate_strategy(profile)
    if strategy == FIXED_STRATEGY:
        if proof is not None:
            raise ValueError("A snapshot proof cannot override a fixed reviewed source date")
        return profile["source_dataset_date"]
    if (not isinstance(proof, dict) or set(proof) != _PROOF_KEYS
            or type(proof.get("schema")) is not int or proof["schema"] != 1
            or type(proof.get("dataset_records_count")) is not int
            or type(proof.get("snapshot_records_count")) is not int):
        raise ValueError("Missing or invalid dynamic source date proof")
    if read_on is not None and read_on != proof["read_on"]:
        raise ValueError("Source date proof read date changed")
    if blob is not None:
        count = _snapshot_count(profile, blob)
        body_hash = _sha256(blob)
        if snapshot_sha256 is not None and snapshot_sha256 != body_hash:
            raise ValueError("Source snapshot SHA-256 does not match the body")
        snapshot_sha256 = body_hash
    else:
        if snapshot_sha256 is None:
            raise ValueError("Dynamic source date requires an independent source snapshot SHA-256")
        count = proof.get("snapshot_records_count")
    expected = _build_proof(
        profile, snapshot_sha256=snapshot_sha256, snapshot_count=count,
        before_metadata=_proof_metadata(proof, "before"),
        after_metadata=_proof_metadata(proof, "after"),
        read_on=proof["read_on"], today=today,
    )
    # Exact comparison checks both metadata hashes, derived counts/dates, body
    # hash, original profile digest, and both reviewed endpoint identities.
    if proof != expected or type(proof.get("dataset_records_count")) is not int:
        raise ValueError("Source snapshot date proof does not match the profile or observation")
    return expected["source_date"]
