#!/usr/bin/env python3
"""Read-only official Lombardia MERCap source adapter.

ONE publisher market may have multiple rows, one per weekday. Preserve those
rows as separate stable scheduling identities. No license approval, event
confirmation, geocoding or public runtime calls. Timestamp refers to dataset
rowsUpdatedAt, not the individual municipal market.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler
from lombardia_calendar_scope import (
    IDENTITY_FIELDS, calendar_scope, filter_dates, scope_label, source_identity,
)

DATASET_ID = "68zx-njaw"
SOURCE_PAGE = "https://www.dati.lombardia.it/d/68zx-njaw"
METADATA_URL = "https://www.dati.lombardia.it/api/views/68zx-njaw.json"
API_URL = "https://www.dati.lombardia.it/resource/68zx-njaw.json"
PAGE_SIZE = 500
MAX_TOTAL_ROWS = 3000
MAX_PAGE_BYTES = 2_000_000
MAX_EXPECTED_SOURCE_AGE_DAYS = 540
MONTHS = ("gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno",
          "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre")
DAYS = ("lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica")
DAY_LABELS = ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica")
# The city of Milano has a separate municipal adapter. Until same-venue
# reconciliation is tested, do not introduce an overlapping second catalog.
EXCLUDED_CITIES = frozenset({"MILANO"})
# Preserve the source qualifiers needed for safe cross-source joins. The
# legacy public category remains unchanged; a broad "misto" label alone is
# not evidence that a market really has both merchandise sectors.


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def textkey(value):
    s = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(c for c in s if not unicodedata.combining(c)).casefold().strip()


def only_source_url(url):
    p = urlsplit(url)
    return (p.scheme == "https" and p.hostname == "www.dati.lombardia.it"
            and p.path in {urlsplit(METADATA_URL).path, urlsplit(API_URL).path}
            and not p.username and not p.password and p.port in (None, 443)
            and not p.fragment)


def request_json(url):
    if not only_source_url(url):
        raise ValueError("Lombardia official-data URL not on allowlist")
    request = Request(url, headers={
        "User-Agent": "MercatiItaliaLombardiaAdapter/1.0",
        "Accept": "application/json",
        "Accept-Encoding": "identity",
    })
    with build_opener(NoRedirect).open(request, timeout=20) as response:
        blob = response.read(MAX_PAGE_BYTES + 1)
    if len(blob) > MAX_PAGE_BYTES:
        raise ValueError("Lombardia data response exceeded byte limit")
    return json.loads(blob.decode("utf-8-sig"))


def downloaded_timestamp(metadata):
    if not isinstance(metadata, dict) or metadata.get("id") != DATASET_ID:
        raise ValueError("Official Lombardia dataset ID differs from allowlist")
    if str(metadata.get("licenseId") or "") != "CC0_10":
        raise ValueError("Unexpected publisher license metadata; manual rights review required")
    raw = metadata.get("rowsUpdatedAt")
    if not isinstance(raw, (int, float)) or isinstance(raw, bool):
        raise ValueError("Publisher dataset last-change timestamp missing")
    try:
        return datetime.fromtimestamp(raw, timezone.utc).date()
    except (OSError, ValueError, OverflowError) as e:
        raise ValueError("Invalid publisher dataset timestamp") from e


def download(fetch_json=None, page_size=PAGE_SIZE):
    fetch = fetch_json or request_json
    if not 1 <= page_size <= 1000:
        raise ValueError("Page size outside strict limits")
    before = fetch(METADATA_URL)
    updated = downloaded_timestamp(before)
    raw_count = fetch(API_URL + "?" + urlencode({"$select": "count(*) as n"}))
    if not isinstance(raw_count, list) or len(raw_count) != 1:
        raise ValueError("Count query returned unexpected shape")
    try:
        total = int(raw_count[0]["n"])
    except (KeyError, ValueError, TypeError) as e:
        raise ValueError("Invalid official source record count") from e
    if not 1100 <= total <= MAX_TOTAL_ROWS:
        raise ValueError(f"Unexpected Lombardia source count {total}; block partial import")
    items = []
    for offset in range(0, total, page_size):
        limit = min(page_size, total - offset)
        url = API_URL + "?" + urlencode({
            "$limit": limit, "$offset": offset, "$order": ":id",
        })
        page = fetch(url)
        if not isinstance(page, list) or len(page) != limit:
            raise ValueError("Incomplete official source page; keep previous version")
        items.extend(page)
    after = fetch(METADATA_URL)
    if (downloaded_timestamp(after) != updated or
            after.get("rowsUpdatedAt") != before.get("rowsUpdatedAt")):
        raise ValueError("Source changed during paginated read; rerun entire pipeline")
    if len(items) != total:
        raise ValueError("Source page count did not match official count")
    return {
        "dataset_id": DATASET_ID, "publisher_data_updated_at": updated.isoformat(),
        "publisher_update_scope": "entire_dataset_not_each_market",
        "expected_rows": total, "rows": items,
    }


def months_of_operation(value):
    if not value:
        return set()
    tokens = [textkey(t) for t in str(value).split(",")]
    months = {MONTHS.index(t) + 1 for t in tokens if t in MONTHS}
    if not months or len(months) != len(tokens):
        return set()
    return months


def weekday(value):
    token = textkey(value)
    return DAYS.index(token) if token in DAYS else None


def point(record):
    geo = record.get("location")
    if not isinstance(geo, dict) or geo.get("type") != "Point":
        return (None, None)
    values = geo.get("coordinates")
    if not isinstance(values, list) or len(values) != 2:
        return (None, None)
    try:
        longitude, latitude = float(values[0]), float(values[1])
        other_lon = float(record["geo_x"])
        other_lat = float(record["geo_y"])
    except (TypeError, ValueError, KeyError, OverflowError):
        return (None, None)
    if (not 7.8 <= longitude <= 11.8 or not 44.5 <= latitude <= 46.8
            or abs(longitude - other_lon) > 0.0005
            or abs(latitude - other_lat) > 0.0005):
        return (None, None)
    # Official coordinates are not proof of a precisely surveyed entrance.
    return (round(latitude, 6), round(longitude, 6))


def hour_span(record):
    def clean(value):
        value = str(value or "").strip()
        return value if re.fullmatch(r"(?:[01]\d|2[0-3]):[0-5]\d", value) else ""
    winter = (clean(record.get("dalle_ore_invernale")),
              clean(record.get("alle_ore_invernale")))
    summer = (clean(record.get("dalle_ore_estivo")),
              clean(record.get("alle_ore_estivo")))
    def usable(pair):
        return bool(pair[0] and pair[1] and pair != ("00:00", "00:00")
                    and pair[1] > pair[0])
    if usable(winter) and usable(summer) and winter == summer:
        return winter[0] + "–" + winter[1] + " (fonte comunale, da verificare)"
    parts = []
    if usable(winter):
        parts.append("Inverno: " + "–".join(winter))
    if usable(summer):
        parts.append("Estate: " + "–".join(summer))
    return "; ".join(parts) + (" (fonte comunale, da verificare)" if parts else "")


def projected_dates(day, months, today, limit=120):
    if day is None or not months:
        return []
    return [
        (today + timedelta(days=d)).isoformat()
        for d in range(limit + 1)
        if (today + timedelta(days=d)).weekday() == day
        and (today + timedelta(days=d)).month in months
    ]


def convert(payload, today=None):
    today = today or date.today()
    if (not isinstance(payload, dict) or payload.get("dataset_id") != DATASET_ID
            or payload.get("publisher_update_scope") != "entire_dataset_not_each_market"
            or not isinstance(payload.get("rows"), list)):
        raise ValueError("Official Lombardia adapter input contract mismatch")
    source_updated = date.fromisoformat(payload["publisher_data_updated_at"])
    source_age = (today - source_updated).days
    if source_age < -1:
        raise ValueError("Dataset update timestamp from the future")
    rows = payload["rows"]
    if len(rows) != payload.get("expected_rows") or not 1100 <= len(rows) <= MAX_TOTAL_ROWS:
        raise ValueError("Incomplete source snapshot")
    output, seen = [], set()
    excluded = Counter()
    for record in rows:
        if not isinstance(record, dict):
            raise ValueError("Non-object in official data feed")
        ident = str(record.get("codice_id") or "").strip()
        province = str(record.get("despro") or "").strip().upper()
        city = str(record.get("descom") or "").strip()
        istat = str(record.get("istat") or "").strip()
        if not (re.fullmatch(r"\d{1,12}", ident)
                and re.fullmatch(r"\d{1,7}", istat)
                and re.fullmatch(r"[A-Z]{2}", province)
                and re.search(r"[A-Za-zÀ-ÿ]", city)):
            excluded["missing_or_invalid_identity"] += 1
            continue
        if textkey(city) in {textkey(x) for x in EXCLUDED_CITIES}:
            excluded["milano_existing_city_adapter"] += 1
            continue
        day = weekday(record.get("giorno"))
        suffix = DAYS[day] if day is not None else "senza-giorno"
        slug = "lo-mercap-" + ident + "-" + suffix
        if slug in seen:
            raise ValueError("Ambiguous repeated source ID and weekday: " + slug)
        seen.add(slug)
        freq = textkey(record.get("periodicita_tipo"))
        months = months_of_operation(record.get("mesi_svolgimento"))
        supported = (freq in ("settimanale", "giornaliero")
                     and day is not None and bool(months)
                     and 0 <= source_age <= MAX_EXPECTED_SOURCE_AGE_DAYS)
        dates = projected_dates(day, months, today) if supported else []
        if dates and len(months) == 12:
            recurrence = "Ogni " + DAY_LABELS[day]
        elif dates:
            recurrence = "Giorno dichiarato " + DAY_LABELS[day] + "; mesi di attività limitati"
        else:
            recurrence = ("Periodicità: " + str(record.get("periodicita_tipo") or "da verificare")
                          + ("; giorno indicato " + DAY_LABELS[day] if day is not None else "")
                          + "; date da verificare")
        raw_address = str(record.get("indirizzi") or record.get("ubicazione") or "").strip()[:240]
        # A historical relocation note (e.g. "from October 2012 on Via...")
        # is not a current usable navigation address. Keep it as evidence,
        # but do not give the user confident directions to the older venue.
        historical_address_note = bool(re.search(
            r"\([^)]*\b20[0-3]\d\b[^)]*\)", raw_address
        ))
        address = "" if historical_address_note else raw_address
        label_address = re.sub(r"\([^)]*\)", "", raw_address).strip(" ,;-")
        label_address = re.sub(r"\b20[0-3]\d\b", "", label_address).strip(" ,;-")
        name = ("Mercato di " + city.title() + " – " + label_address.title()
                if label_address and not historical_address_note
                else "Mercato comunale di " + city.title() + " (sede da verificare)")
        latitude, longitude = point(record)
        descr = (
            "Sede censita nell'archivio MERCap della Regione Lombardia. "
            "La Regione aggiorna il dataset, ma il singolo Comune potrebbe non aver "
            "riconfermato questo mercato. Date e orari non sono confermati. "
            "Nome descrittivo composto da Comune e sede, non denominazione ufficiale. "
            "Codice fonte: " + ident + "."
        )
        if historical_address_note:
            descr += " Nota storica sulla sede, NON verificata: " + raw_address + "."
        identity = source_identity(record)
        boundary_label = scope_label(identity)
        if boundary_label:
            recurrence += "; " + boundary_label
        market = {
            "slug": slug,
            "nome": name[:158],
            "citta": city.title(), "provincia": province, "regione": "Lombardia",
            "indirizzo": address, "lat": latitude, "lng": longitude,
            "position_quality": "non_verificata" if latitude is not None else "sconosciuta",
            "categoria": "misto", "tags": ["mercato comunale", "MERCAP"],
            "status": "non_confermato",
            "date": dates, "date_quality": "prevista" if dates else "sconosciuta",
            "ricorrenza_testo": recurrence,
            "orario_testo": hour_span(record),
            "descrizione": descr,
            "fonte": "Regione Lombardia – MERCap (CC0 1.0 dichiarata)",
            "url_fonte": SOURCE_PAGE,
            "aggiornato_il": source_updated.isoformat(),
            "aggiornamento_ambito": "dataset",
            "id_fonte": ident,
            "identita_fonte": identity,
            "verificato_il": "",
            "confidence": 0,
        }
        scope = calendar_scope(market)
        market["date"] = filter_dates(dates, scope)
        market["date_quality"] = "prevista" if market["date"] else "sconosciuta"
        output.append(market)
    if len(output) < 1000:
        raise ValueError("Lombardia importer returned implausibly few valid records")
    return sorted(output, key=lambda x: x["slug"])


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, help="Fixture downloaded earlier from authorized source")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    payload = json.loads(args.input.read_text("utf-8")) if args.input else download()
    markets = convert(payload, today=args.today)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(markets, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print(json.dumps({
        "converted_records": len(markets),
        "forecasted": sum(bool(x["date"]) for x in markets),
        "unknown_days": sum(not x["date"] for x in markets),
        "exact_confirmed": 0,
    }))


if __name__ == "__main__":
    main()
