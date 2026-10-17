#!/usr/bin/env python3
"""Repeatable import of four weekly Corciano municipal open-data markets.

Observed manually on 2026-10-12 before code was written:
- CSV headers 'long' and 'lat' are MISLABELED. 'long' is latitude ~43,
  'lat' is longitude ~12. Check these against geopoint in the source.
- National catalog declared dataset update date: 07-01-2026.
  The municipal HTML page update (2026-07-27) does not verify market rows.
- The CSV has no official market ID. Stable IDs derive from exact
  market names; changes to names must be screened as new identities.
- All future dates are projections, never confirmed open days.
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
from datetime import date, timedelta
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

SOURCE_URL = (
    "https://comune.corciano.pg.it/download/oggetto_documenti/372/"
    "1O__Oelenco-mercati-settinamanali-comune-corciano.csv"
)
SOURCE_PAGE = "https://comune.corciano.pg.it/area_letturaDocumento/29645/pagsistema.html"
DATASET_DECLARED_DATE = "2026-01-07"  # dati.gov.it, not HTTP retrieval date
SOURCE_PAGE_LAST_UPDATED = "2026-07-27"  # page date, NOT per-market verification
MAX_SOURCE_AGE_DAYS = 540
MAX_BYTES = 16_384
SOURCE_COUNT_MIN = 4
SOURCE_COUNT_MAX = 8
HEADERS = (
    "denominazione", "giorni_svolgimento", "tipo_strada", "ubicazione",
    "numero_tot_posteggi", "numero_posteggi_riservati",
    "orario_svolgimento_dalle", "orario_svolgimento_alle",
    "long", "lat", "geopoint",
)
DAYS = ("lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica")
DISPLAY_DAYS = ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica")
POINT = re.compile(r"^\(\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\)$")
TIME = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def normalize(text):
    value = unicodedata.normalize("NFKD", str(text or ""))
    return "".join(c for c in value if not unicodedata.combining(c)).casefold().strip()


def slug_part(value):
    return re.sub(r"[^a-z0-9]+", "-", normalize(value)).strip("-")[:100]


def safe_url(url):
    parts = urlsplit(url)
    return (url == SOURCE_URL and parts.scheme == "https"
            and parts.hostname == "comune.corciano.pg.it"
            and parts.port in (None, 443) and not parts.username
            and not parts.password and not parts.fragment)


def fetch_csv(url=SOURCE_URL):
    if not safe_url(url):
        raise ValueError("Unapproved Corciano municipal data URL")
    for answer in socket.getaddrinfo("comune.corciano.pg.it", 443, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(answer[4][0]).is_global:
            raise ValueError("Non-public Corciano DNS target refused")
    req = Request(url, headers={
        "User-Agent": "MercatiItaliaCorcianoOfficial/1.0",
        "Accept": "text/csv,text/plain",
        "Accept-Encoding": "identity",
    })
    with build_opener(NoRedirect).open(req, timeout=20) as response:
        blob = response.read(MAX_BYTES + 1)
    if len(blob) > MAX_BYTES:
        raise ValueError("Corciano CSV exceeded size limit")
    return blob


def parse_csv(blob):
    if not isinstance(blob, bytes) or len(blob) > MAX_BYTES:
        raise ValueError("Corciano official file must be a bounded CSV")
    try:
        reader = csv.DictReader(io.StringIO(blob.decode("utf-8-sig")), delimiter=";")
        header = list(reader.fieldnames or [])
        if len(header) != len(HEADERS) or set(header) != set(HEADERS):
            raise ValueError("Corciano CSV schema changed, manual review required")
        records = list(reader)
    except UnicodeDecodeError as exc:
        raise ValueError("Unexpected CSV encoding") from exc
    if not SOURCE_COUNT_MIN <= len(records) <= SOURCE_COUNT_MAX:
        raise ValueError("Corciano source count changed beyond approved bounds")
    if any(row.get(None) is not None or
           any(row.get(header) is None for header in HEADERS) for row in records):
        raise ValueError("Corciano CSV contains malformed rows")
    return {
        "schema": 1,
        "publisher": "Comune di Corciano",
        "publisher_dataset_url": SOURCE_URL,
        "source_sha256": hashlib.sha256(blob).hexdigest(),
        "source_date_scope": "national_catalog_declared_dataset_date",
        "publisher_data_updated_at": DATASET_DECLARED_DATE,
        "publisher_page_updated_at": SOURCE_PAGE_LAST_UPDATED,
        "license_claim": "CC BY 4.0",
        "expected_rows": len(records),
        "rows": records,
    }


def download(fetch=fetch_csv):
    return parse_csv(fetch(SOURCE_URL))


def coordinates(row):
    """Manual schema proof: long=latitude and lat=longitude, NOT vice versa."""
    match = POINT.fullmatch(str(row.get("geopoint") or "").strip())
    if not match:
        raise ValueError("Corciano geopoint missing or malformed")
    try:
        latitude = float(row["long"])
        longitude = float(row["lat"])
        point_latitude = float(match.group(1))
        point_longitude = float(match.group(2))
    except (ValueError, TypeError, OverflowError, KeyError) as exc:
        raise ValueError("Corciano invalid coordinate values") from exc
    if not (43.00 <= latitude <= 43.25 and 12.15 <= longitude <= 12.50
            and abs(latitude - point_latitude) < 0.00001
            and abs(longitude - point_longitude) < 0.00001):
        raise ValueError("Corciano coordinates or schema differ from verified municipal sample")
    return round(latitude, 6), round(longitude, 6)


def project(day, today, horizon=120):
    return [(today + timedelta(days=i)).isoformat()
            for i in range(horizon + 1)
            if (today + timedelta(days=i)).weekday() == day]


def convert(payload, today=None):
    today = today or date.today()
    if not isinstance(payload, dict) or payload.get("schema") != 1:
        raise ValueError("Untrusted Corciano import payload")
    if (payload.get("publisher") != "Comune di Corciano"
            or payload.get("publisher_dataset_url") != SOURCE_URL
            or payload.get("publisher_data_updated_at") != DATASET_DECLARED_DATE
            or payload.get("source_date_scope") != "national_catalog_declared_dataset_date"
            or payload.get("license_claim") != "CC BY 4.0"
            or not isinstance(payload.get("source_sha256"), str)
            or not re.fullmatch("[0-9a-f]{64}", payload["source_sha256"])):
        raise ValueError("Official Corciano provenance contract changed")
    rows = payload.get("rows")
    if (not isinstance(rows, list) or
            payload.get("expected_rows") != len(rows)
            or not SOURCE_COUNT_MIN <= len(rows) <= SOURCE_COUNT_MAX):
        raise ValueError("Corciano inventory incomplete")
    data_day = date.fromisoformat(DATASET_DECLARED_DATE)
    age = (today - data_day).days
    if age < -1:
        raise ValueError("Corciano publisher dataset timestamp is in the future")
    permit_forecast = 0 <= age <= MAX_SOURCE_AGE_DAYS
    seen = set()
    out = []
    for item in rows:
        if not isinstance(item, dict):
            raise ValueError("Corciano market row not an object")
        name = str(item.get("denominazione") or "").strip()
        road_type = str(item.get("tipo_strada") or "").strip()
        street = str(item.get("ubicazione") or "").strip()
        day_name = normalize(item.get("giorni_svolgimento"))
        if (not name.startswith("MERCATO DI ")
                or not road_type or not street
                or not re.fullmatch("[A-ZÀ-Ÿ '.-]{3,100}", name)
                or day_name not in DAYS):
            raise ValueError("Corciano market identity/day does not meet observed schema")
        identifier = "pg-corciano-" + slug_part(name)
        if identifier in seen:
            raise ValueError("Duplicate derived Corciano market identity")
        seen.add(identifier)
        if normalize(road_type) not in ("piazza", "via", "viale", "piazzale"):
            raise ValueError("Corciano market address type not on reviewed allowlist")
        try:
            stalls = int(item["numero_tot_posteggi"])
            reserved = int(item["numero_posteggi_riservati"])
        except (ValueError, TypeError, KeyError) as exc:
            raise ValueError("Missing or invalid market stall counts") from exc
        if not (1 <= stalls <= 500 and 0 <= reserved <= stalls):
            raise ValueError("Market stall counts inconsistent")
        start = str(item.get("orario_svolgimento_dalle") or "").strip()
        end = str(item.get("orario_svolgimento_alle") or "").strip()
        if not (TIME.fullmatch(start) and TIME.fullmatch(end) and start < end):
            raise ValueError("Corciano operating-hour source schema changed")
        lat, lng = coordinates(item)
        weekday = DAYS.index(day_name)
        # Each record belongs to the same municipality. Frazione is part of
        # both display name and address, not a false autonomous city.
        locality = name.removeprefix("MERCATO DI ").title()
        address = road_type.title() + " " + street.title() + ", " + locality
        out.append({
            "slug": identifier,
            "nome": name.title(),
            "citta": "Corciano",
            "provincia": "PG",
            "regione": "Umbria",
            "indirizzo": address,
            "lat": lat, "lng": lng,
            "position_quality": "non_verificata",
            "categoria": "misto",
            "tags": ["mercato comunale", "mercato settimanale"],
            "status": "non_confermato",
            "date": project(weekday, today) if permit_forecast else [],
            "date_quality": "prevista" if permit_forecast else "sconosciuta",
            "ricorrenza_testo": "settimanale - " + DISPLAY_DAYS[weekday],
            "orario_testo": start + "–" + end + " (da verificare con il Comune)",
            "descrizione": (
                "Mercato settimanale censito dal Comune di Corciano: "
                + str(stalls) + " posteggi dichiarati, di cui "
                + str(reserved) + " riservati. "
                "Il catalogo nazionale dichiara la data dataset "
                + data_day.isoformat()
                + "; aggiornamento della pagina municipale "
                + SOURCE_PAGE_LAST_UPDATED
                + " non prova la conferma del singolo mercato. "
                "Il CSV ha coordinate con intestazioni invertite, "
                "confrontate con geopoint. Nessun appuntamento confermato."
            )[:900],
            "fonte": "Comune di Corciano, open data CC BY 4.0 (licenza dichiarata)",
            "url_fonte": SOURCE_PAGE,
            "aggiornato_il": DATASET_DECLARED_DATE,
            "aggiornamento_ambito": "dataset",
            "verificato_il": "",
            "confidence": 0,
            # Transient provenance used in source checkpoint; export_static
            # intentionally omits this internal hash from public records.
            "source_csv_sha256": payload["source_sha256"],
        })
    return sorted(out, key=lambda x: x["slug"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, help="Previously downloaded official bounded CSV")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    payload = parse_csv(args.input.read_bytes()) if args.input else download()
    markets = convert(payload, args.today)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(markets, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({
        "source_rows": payload["expected_rows"],
        "converted": len(markets),
        "source_sha256": payload["source_sha256"],
        "future_forecast": sum(bool(x["date"]) for x in markets),
        "source_updated_at_declared": DATASET_DECLARED_DATE,
        "verified_individual_markets": 0,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
