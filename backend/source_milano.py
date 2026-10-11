#!/usr/bin/env python3
"""Official open-data importer: Comune di Milano DS291 weekly outdoor markets.

Dataset source and attribution:
https://dati.comune.milano.it/dataset/ds291-economia-mercati-settimanali-scoperti
License: Creative Commons Attribution 4.0.
The currently linked resource describes the May 2024 situation, not a live
confirmation for October 2026. All projected future dates are marked PREVISTA.
"""
from __future__ import annotations

import argparse
import json
from datetime import date, timedelta
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE_PAGE = "https://dati.comune.milano.it/dataset/ds291-economia-mercati-settimanali-scoperti"
SOURCE_JSON = (
    "https://dati.comune.milano.it/dataset/"
    "f758d24c-8805-40b0-9a72-a8aac06d1e98/resource/"
    "b07ed03a-d198-4a16-9eb5-744cb406f3eb/download/mss-mag24_final.json"
)
WEEKDAYS = [
    ("LUNEDI", "lunedì", 0),
    ("MARTEDI", "martedì", 1),
    ("MERCOLEDI", "mercoledì", 2),
    ("GIOVEDI", "giovedì", 3),
    ("VENERDI", "venerdì", 4),
    ("SABATO", "sabato", 5),
    ("DOMENICA", "domenica", 6),
]
SOURCE_DATE = "2024-05-27"


def _value(row: dict, *candidates: str):
    for candidate in candidates:
        value = row.get(candidate)
        if value is not None and str(value).strip():
            return value
    return None


def _flag(value) -> bool:
    return str(value).strip().lower() in {"x", "si", "sì", "1", "true", "yes"}


def _weekdays(row: dict) -> list[tuple[str, int]]:
    days = [(label, number) for key, label, number in WEEKDAYS if _flag(row.get(key))]
    if days:
        return days
    text = str(_value(row, "giorno", "GIORNO") or "").upper()
    abbr = {"LUN": 0, "MAR": 1, "MER": 2, "GIO": 3, "VEN": 4, "SAB": 5, "DOM": 6}
    values = {abbr[x] for x in __import__("re").findall(r"\b(?:LUN|MAR|MER|GIO|VEN|SAB|DOM)\b", text)}
    return [(name, number) for _, name, number in WEEKDAYS if number in values]


def _future_dates(days: list[tuple[str, int]], today: date, horizon=56) -> list[str]:
    weekdays = {number for _, number in days}
    return [
        (today + timedelta(days=delta)).isoformat()
        for delta in range(horizon)
        if (today + timedelta(days=delta)).weekday() in weekdays
    ]


def _coordinate(row: dict, keys: tuple[str, ...]):
    value = _value(row, *keys)
    try:
        return float(value) if value is not None else None
    except (ValueError, TypeError):
        return None


def convert(records: list[dict], today: date | None = None) -> list[dict]:
    today = today or date.today()
    markets = []
    seen = set()
    for row in records:
        if not isinstance(row, dict):
            continue
        status = str(_value(row, "status mss", "STATUS") or "").strip().lower()
        if status and status not in {"attivo", "active"}:
            continue
        name = str(_value(row, "nome MSS", "MERCATO", "mercato") or "").strip()
        ident = str(_value(row, "ID", "id") or "").strip()
        if not name or not ident or ident in seen:
            continue
        seen.add(ident)
        days = _weekdays(row)
        day_names = ", ".join(label for label, _ in days)
        street = str(_value(row, "INDIRIZZO", "indirizzo", "via", "VIA", "LOCALIZZAZIONE") or "").strip()
        postcode = str(_value(row, "CAP") or "").strip()
        lat = _coordinate(row, ("LAT_Y_4326", "LATITUDINE", "latitudine", "lat", "LAT"))
        lng = _coordinate(row, ("LONG_X_4326", "LONGITUDINE", "longitudine", "lng", "LON", "lon"))
        if lat is None or lng is None or not (45.35 <= lat <= 45.65 and 9.0 <= lng <= 9.45):
            lat, lng = None, None
        # Never geocode the municipality centroid as a precise market point.
        area = str(_value(row, "NIL") or "").strip()
        details = "Mercato settimanale scoperto nel Comune di Milano."
        if area:
            details += " Zona: " + area + "."
        markets.append({
            "slug": "mi-mss-" + ident,
            "nome": "Mercato di " + name.strip().title(),
            "citta": "Milano", "provincia": "MI", "regione": "Lombardia",
            "indirizzo": street + (", " + postcode if postcode and street else ""),
            "lat": lat, "lng": lng,
            "position_quality": "precisa" if lat is not None else "sconosciuta",
            "categoria": "misto",
            "tags": ["mercato settimanale", "all'aperto"],
            "status": "non_confermato",
            "date": _future_dates(days, today),
            "date_quality": "prevista",
            "ricorrenza_testo": "Ogni " + day_names if days else "Da verificare",
            "orario_testo": str(_value(row, "orari", "ORARI") or "").strip(),
            "descrizione": details,
            "fonte": "Comune di Milano - Open Data (CC BY 4.0)",
            "url_fonte": SOURCE_PAGE,
            "aggiornato_il": SOURCE_DATE,
            "confidence": 0,  # no fabricated probability or fresh verification
        })
    return markets


def download(url=SOURCE_JSON) -> list:
    request = Request(url, headers={"User-Agent": "MercatiItaliaDataImporter/1.0 (+data-quality)"})
    with urlopen(request, timeout=30) as response:
        if response.status != 200:
            raise OSError("Milano dataset HTTP " + str(response.status))
        blob = response.read(15_000_001)
    if len(blob) > 15_000_000:
        raise ValueError("Milano dataset unexpectedly large")
    records = json.loads(blob.decode("utf-8-sig"))
    if not isinstance(records, list):
        raise ValueError("Milano dataset expected JSON array")
    return records


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, help="Use a local downloaded official JSON file")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    rows = json.loads(args.input.read_text("utf-8")) if args.input else download()
    markets = convert(rows)
    if not markets:
        raise ValueError("Importer returned no active markets; check upstream dataset schema")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(markets, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print("Milano official-source records:", len(markets))
    print("With coordinates:", sum(m["lat"] is not None for m in markets))
    print("With projected dates:", sum(bool(m["date"]) for m in markets))


if __name__ == "__main__":
    main()
