"""Bounded reader of Roma Capitale's d881 market inventory.

Discover the current CSV from the real CKAN package response on every read.
The distribution upload time ranks files; AGGIORNATO dates each market row.
Neither a download nor an upload confirms a present-day opening.
"""
from __future__ import annotations

import base64
import binascii
import csv
import hashlib
import io
import ipaddress
import json
import re
import socket
import unicodedata
from datetime import date, datetime, timezone
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

SOURCE_ID = "roma-d881"
PUBLISHER = "Roma Capitale"
HOST = "dati.comune.roma.it"
DATASET_ID = "e2e30174-ba7f-4319-bf4a-c13f80278c0c"
DATASET_PAGE = "https://dati.comune.roma.it/catalog/dataset/d881"
METADATA_URL = "https://dati.comune.roma.it/catalog/api/3/action/package_show?id=" + DATASET_ID
MAX_METADATA_BYTES = 300_000
MAX_CSV_BYTES = 512_000
MAX_RESOURCES = 256
MAX_PHYSICAL_ROWS = 5_000
MAX_MARKET_ROWS = 300
MAX_READ_AGE_DAYS = 45
TIMEOUT_SECONDS = 20
UUID = r"[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}"
RESOURCE_PATH = re.compile(
    r"/catalog/(?:it/)?dataset/" + DATASET_ID + r"/resource/(" + UUID +
    r")/download/[A-Za-z0-9_-][A-Za-z0-9_.-]{0,179}\.csv"
)
DAYS = (("Lunedi", "lunedì"), ("Martedi", "martedì"), ("Mercoledi", "mercoledì"),
        ("Giovedi", "giovedì"), ("Venedi", "venerdì"), ("Sabato", "sabato"))
HEADERS = ("Municipio", "Nome_Mercato", "INDIRIZZO", "Civico", "Esp_Civico",
           "Altre_indicazioni", "CAP", "TIPOLOGIA", "Note_mercato", "POSTEGGI_TOTALI",
           "POSTEGGI_OCCUPATI", "NUMERO_OPERATORI", "POSTEGGI_ALIMENTARI", "POSTEGGI_NON_ALIMENTARI",
           *(field + "_" + day for day, _ in DAYS for field in ("Apertura", "Chiusura")),
           "Note_orari", "AGGIORNATO")
CSV_MIMES = {"text/csv", "text/plain", "application/csv", "application/octet-stream",
             "text/x-comma-separated-values"}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def corrupt_text(value):
    return bool(re.search(r"[\ufffd\ufffe\x00-\x08\x0b\x0c\x0e-\x1f\x7f\ud800-\udfff]|Ã|Â|â€", value))


def normalized(value):
    if not isinstance(value, str) or corrupt_text(value):
        return ""
    text = unicodedata.normalize("NFKD", value).casefold()
    text = "".join(char for char in text if not unicodedata.combining(char))
    return " ".join(re.findall(r"[a-z0-9]+", text))


def name_key(value):
    value = normalized(value)
    for prefix in ("mercato rionale ", "mercato "):
        if value.startswith(prefix):
            return value[len(prefix):]
    return value


def resource_url(url, resource_id=None):
    if not isinstance(url, str) or len(url) > 1000:
        return False
    try:
        parsed = urlsplit(url)
        match = RESOURCE_PATH.fullmatch(parsed.path)
        return bool(parsed.scheme == "https" and parsed.netloc == HOST and not parsed.query
                    and not parsed.fragment and match
                    and (resource_id is None or match.group(1) == resource_id))
    except ValueError:
        return False


def _utc(value, *, declared=False):
    if not isinstance(value, str) or len(value) > 40:
        raise ValueError("Invalid Roma source timestamp")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise ValueError("Invalid Roma source timestamp") from error
    if parsed.tzinfo is None:
        if not declared:
            raise ValueError("Roma read timestamp requires a timezone")
        # CKAN publishes naive timestamps. This is its declared upload time,
        # not a clock independently observed at a market.
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate key in Roma metadata")
        result[key] = value
    return result


def select_distribution(blob, *, read_at):
    """Select the unique newest declared CSV; never fall back to a stale pin."""
    if not isinstance(blob, bytes) or not 2 <= len(blob) <= MAX_METADATA_BYTES:
        raise ValueError("Roma metadata exceeds its byte budget")
    read = _utc(read_at)
    try:
        payload = json.loads(blob.decode("utf-8-sig"), object_pairs_hook=_no_duplicates)
    except (UnicodeError, json.JSONDecodeError) as error:
        raise ValueError("Malformed Roma dataset metadata") from error
    package = payload.get("result") if isinstance(payload, dict) else None
    if (not isinstance(payload, dict) or payload.get("success") is not True or not isinstance(package, dict)
            or package.get("id") != DATASET_ID or package.get("name") != "d881"
            or package.get("private") is not False or package.get("state") != "active"):
        raise ValueError("Roma metadata is not the approved public dataset")
    resources = package.get("resources")
    if not isinstance(resources, list) or not 1 <= len(resources) <= MAX_RESOURCES:
        raise ValueError("Unbounded or missing Roma distributions")
    package_modified = _utc(package.get("metadata_modified"), declared=True)
    if package_modified.date() > read.date():
        raise ValueError("Roma metadata declares a future upload date")
    candidates, seen = [], set()
    for item in resources:
        if not isinstance(item, dict):
            raise ValueError("Malformed Roma distribution metadata")
        if item.get("state") != "active" or str(item.get("format") or "").upper() != "CSV":
            continue
        resource_id, url = item.get("id"), item.get("url")
        if (not isinstance(resource_id, str) or not re.fullmatch(UUID, resource_id)
                or resource_id in seen or item.get("package_id") != DATASET_ID
                or not resource_url(url, resource_id)):
            raise ValueError("Roma CSV distribution is duplicated or outside its dataset")
        seen.add(resource_id)
        created = _utc(item.get("created"), declared=True)
        modified = _utc(item["last_modified"], declared=True) if item.get("last_modified") else created
        use_modified = bool(item.get("last_modified") and modified >= created)
        raw_version = item["last_modified"] if use_modified else item["created"]
        version = max(created, modified)
        if max(version.date(), created.date()) > read.date():
            raise ValueError("Roma CSV declares a future upload date")
        candidates.append({
            "id": resource_id, "url": url, "name": str(item.get("name") or "")[:200],
            "declared_updated_at": raw_version,
            "version_basis": "last_modified" if use_modified else "created",
            "created": item["created"], "last_modified": item.get("last_modified") or "",
            "license_claim": str(item.get("license_type") or "")[:300],
        })
    if not candidates:
        raise ValueError("Roma dataset has no approved CSV distribution")
    candidates.sort(key=lambda item: (_utc(item["declared_updated_at"], declared=True), item["id"]))
    newest = candidates[-1]
    if len(candidates) > 1 and _utc(candidates[-2]["declared_updated_at"], declared=True) == _utc(
            newest["declared_updated_at"], declared=True):
        raise ValueError("Roma newest distribution is ambiguous")
    return {**newest, "dataset_id": DATASET_ID, "dataset_url": DATASET_PAGE,
            "dataset_metadata_modified_at": package["metadata_modified"],
            "dataset_license_claim": str(package.get("license_id") or "")[:100],
            "eligible_distributions": [{"id": item["id"], "declared_updated_at": item["declared_updated_at"]}
                                       for item in candidates]}


def _row_date(value, read_at):
    if not re.fullmatch(r"\d{2}/\d{2}/\d{4}", value):
        raise ValueError("invalid_row_date")
    try:
        parsed = datetime.strptime(value, "%d/%m/%Y").date()
    except ValueError as error:
        raise ValueError("invalid_row_date") from error
    if parsed.year < 1900 or parsed > _utc(read_at).date():
        raise ValueError("future_or_invalid_row_date")
    return parsed.isoformat()


def _clock(value):
    if not re.fullmatch(r"(?:[01]?\d|2[0-3]):[0-5]\d", value):
        raise ValueError("invalid_or_missing_day_hours")
    return value.zfill(5)


def _facts(raw, *, row_number, read_at):
    if any(corrupt_text(value) for value in raw.values()):
        raise ValueError("corrupt_source_text")
    if any(len(value) > 1000 for value in raw.values()):
        raise ValueError("source_cell_too_long")
    name, street, district = raw["Nome_Mercato"], raw["INDIRIZZO"], raw["Municipio"]
    if (not 2 <= len(name) <= 160 or not 3 <= len(street) <= 250
            or not name_key(name) or not normalized(street)
            or not re.fullmatch(r"(?:[1-9]|1[0-5])", district)):
        raise ValueError("invalid_market_identity")
    updated = _row_date(raw["AGGIORNATO"], read_at)
    day_hours = []
    for key, label in DAYS:
        start, end = _clock(raw["Apertura_" + key]), _clock(raw["Chiusura_" + key])
        if start >= end:
            raise ValueError("invalid_or_overnight_day_hours")
        day_hours.append({"day": label, "start": start, "end": end})
    if raw["CAP"] and not re.fullmatch(r"\d{5}", raw["CAP"]):
        raise ValueError("invalid_postcode")
    composite = [name_key(name), normalized(street), district]
    return {"row_number": row_number, "source_row_key": "nome-sede-municipio:" + digest(composite),
            "name": name, "street": street, "municipio": int(district),
            "civic": raw["Civico"], "civic_suffix": raw["Esp_Civico"],
            "location_notes": raw["Altre_indicazioni"], "postcode": raw["CAP"],
            "type": raw["TIPOLOGIA"], "hours_by_day": day_hours,
            "hours_notes": raw["Note_orari"], "market_notes": raw["Note_mercato"],
            "source_updated_on": updated, "raw_fields": raw,
            "row_sha256": digest(raw)}


def parse_csv(blob, *, read_at):
    if not isinstance(blob, bytes) or not 30 <= len(blob) <= MAX_CSV_BYTES:
        raise ValueError("Roma CSV exceeds its byte budget")
    _utc(read_at)
    try:
        # The published file is CP1252. Support a future explicit UTF-8 file
        # without replacement decoding, which damaged earlier catalog names.
        text = blob.decode("utf-8-sig")
        encoding = "utf-8"
    except UnicodeDecodeError:
        try:
            text = blob.decode("cp1252")
            encoding = "cp1252"
        except UnicodeDecodeError as error:
            raise ValueError("Roma CSV has an unsupported encoding") from error
    try:
        reader = csv.reader(io.StringIO(text, newline=""), delimiter=";", strict=True)
        headers = [value.strip() for value in next(reader)]
        if len(headers) != len(HEADERS) or set(headers) != set(HEADERS):
            raise ValueError("Roma CSV header contract changed")
        facts, holds, annotations, blank = [], [], [], 0
        physical = 0
        for physical, values in enumerate(reader, start=1):
            if physical > MAX_PHYSICAL_ROWS:
                raise ValueError("Roma CSV exceeds its physical-row budget")
            if not values or not any(value.strip() for value in values):
                blank += 1
                continue
            if len(values) != len(headers):
                raise ValueError("Roma CSV contains a malformed-width row")
            raw = {key: value.strip() for key, value in zip(headers, values)}
            if not raw["Nome_Mercato"] and not raw["INDIRIZZO"]:
                # A municipality-only note is evidence, not a market or a
                # current cancellation. Keep the exact row for inspection.
                if (raw["Municipio"] and raw["Note_mercato"]
                        and all(not value for key, value in raw.items()
                                if key not in {"Municipio", "Note_mercato", "AGGIORNATO"})):
                    annotations.append({"row_number": physical + 1, "raw_fields": raw})
                    continue
            try:
                facts.append(_facts(raw, row_number=physical + 1, read_at=read_at))
            except ValueError as error:
                holds.append({"row_number": physical + 1, "reason": str(error), "raw_fields": raw})
            if len(facts) + len(holds) > MAX_MARKET_ROWS:
                raise ValueError("Roma CSV exceeds its market-row budget")
    except (StopIteration, csv.Error) as error:
        raise ValueError("Malformed Roma CSV") from error
    if not facts:
        raise ValueError("Roma CSV has no valid market rows")
    return {"encoding": encoding, "physical_rows": physical, "blank_rows": blank,
            "market_rows": len(facts) + len(holds), "rows": facts,
            "held_rows": holds, "annotations": annotations}


def _capture(blob, url, read_at):
    return {"url": url, "read_at": read_at, "bytes": len(blob),
            "sha256": hashlib.sha256(blob).hexdigest(),
            "body_base64": base64.b64encode(blob).decode("ascii")}


def make_snapshot(metadata_blob, csv_blob, *, metadata_read_at, csv_read_at, today):
    """Build a replayable snapshot from captured bytes and real read timestamps."""
    distribution = select_distribution(metadata_blob, read_at=metadata_read_at)
    if not isinstance(csv_blob, bytes) or not 30 <= len(csv_blob) <= MAX_CSV_BYTES:
        raise ValueError("Roma CSV exceeds its byte budget")
    snapshot = {"schema": 1, "source_id": SOURCE_ID,
                "metadata": _capture(metadata_blob, METADATA_URL, metadata_read_at),
                "csv": _capture(csv_blob, distribution["url"], csv_read_at)}
    parse_snapshot(snapshot, today=today)
    return snapshot


def parse_snapshot(snapshot, *, today):
    """Rebuild facts from bytes; never trust cached parsed rows or hashes alone."""
    if (type(today) is not date or not isinstance(snapshot, dict)
            or set(snapshot) != {"schema", "source_id", "metadata", "csv"}
            or snapshot.get("schema") != 1 or snapshot.get("source_id") != SOURCE_ID):
        raise ValueError("Invalid Roma source snapshot")
    bodies, times = {}, {}
    for kind, limit in (("metadata", MAX_METADATA_BYTES), ("csv", MAX_CSV_BYTES)):
        item = snapshot[kind]
        if (not isinstance(item, dict) or set(item) != {"url", "read_at", "bytes", "sha256", "body_base64"}
                or type(item.get("bytes")) is not int or not 1 <= item["bytes"] <= limit
                or not isinstance(item.get("body_base64"), str)
                or len(item["body_base64"]) > ((limit + 2) // 3) * 4):
            raise ValueError("Invalid Roma source capture")
        try:
            body = base64.b64decode(item["body_base64"], validate=True)
        except (ValueError, binascii.Error) as error:
            raise ValueError("Invalid Roma captured bytes") from error
        if len(body) != item["bytes"] or hashlib.sha256(body).hexdigest() != item["sha256"]:
            raise ValueError("Roma source bytes do not match their fingerprint")
        read = _utc(item["read_at"])
        if not 0 <= (today - read.date()).days <= MAX_READ_AGE_DAYS:
            raise ValueError("Roma capture is stale or in the future")
        bodies[kind], times[kind] = body, read
    if times["metadata"] > times["csv"] or (times["csv"] - times["metadata"]).total_seconds() > 3600:
        raise ValueError("Roma metadata and CSV are not one bounded acquisition")
    selected = select_distribution(bodies["metadata"], read_at=snapshot["metadata"]["read_at"])
    if snapshot["metadata"]["url"] != METADATA_URL or snapshot["csv"]["url"] != selected["url"]:
        raise ValueError("Roma CSV is not the latest observed dataset distribution")
    parsed = parse_csv(bodies["csv"], read_at=snapshot["csv"]["read_at"])
    return {"schema": 1, "source_id": SOURCE_ID, "publisher": PUBLISHER,
            "distribution": selected, "read_on": times["csv"].date().isoformat(),
            "metadata_sha256": snapshot["metadata"]["sha256"],
            "csv_sha256": snapshot["csv"]["sha256"], **parsed}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def fetch_public(url):
    """One public, no-redirect response; acquisition calls this at most twice."""
    is_metadata = url == METADATA_URL
    if not is_metadata and not resource_url(url):
        raise ValueError("Unapproved Roma public-data URL")
    answers = socket.getaddrinfo(HOST, 443, type=socket.SOCK_STREAM)
    if not answers or any(not ipaddress.ip_address(answer[4][0]).is_global for answer in answers):
        raise ValueError("Non-public Roma DNS target refused")
    limit = MAX_METADATA_BYTES if is_metadata else MAX_CSV_BYTES
    request = Request(url, headers={"User-Agent": "VintageryRomaOfficial/1.0",
                                   "Accept": "application/json" if is_metadata else "text/csv,text/plain",
                                   "Accept-Encoding": "identity"})
    with build_opener(NoRedirect).open(request, timeout=TIMEOUT_SECONDS) as response:
        mime = response.headers.get_content_type()
        allowed = {"application/json", "text/json"} if is_metadata else CSV_MIMES
        if response.status != 200 or response.geturl() != url or mime not in allowed:
            raise ValueError("Roma source returned an unexpected status, URL or MIME type")
        declared_size = response.headers.get("Content-Length")
        if declared_size and (not declared_size.isdigit() or int(declared_size) > limit):
            raise ValueError("Roma source response exceeds its byte budget")
        blob = response.read(limit + 1)
        if not blob or len(blob) > limit or (declared_size and len(blob) != int(declared_size)):
            raise ValueError("Roma source body is empty, truncated or oversized")
    return blob


def acquire(*, today=None, fetch=fetch_public, clock=None):
    """Return a JSON snapshot after exactly two successful bounded requests.

    fetch(url)->bytes and clock()->timezone-aware datetime are injectable for
    captured replay. Failed reads raise and never refresh catalogue evidence.
    The second URL is taken only from the just-read metadata response.
    """
    today = today or datetime.now(timezone.utc).date()
    clock = clock or (lambda: datetime.now(timezone.utc))
    if type(today) is not date or (fetch is fetch_public and today != datetime.now(timezone.utc).date()):
        raise ValueError("Live Roma acquisition requires the current UTC date")
    metadata_blob = fetch(METADATA_URL)
    metadata_read_at = clock().isoformat()
    selected = select_distribution(metadata_blob, read_at=metadata_read_at)
    csv_blob = fetch(selected["url"])
    csv_read_at = clock().isoformat()
    return make_snapshot(metadata_blob, csv_blob, metadata_read_at=metadata_read_at,
                         csv_read_at=csv_read_at, today=today)
