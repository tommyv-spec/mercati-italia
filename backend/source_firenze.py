#!/usr/bin/env python3
"""Comune di Firenze / FeelFlorence historical market locations.

Official GeoJSON published by Comune di Firenze under CC BY 4.0.
The portal reports data updated 03/03/2023, so these locations must not
be represented as newly confirmed for October 2026.

Dataset:
https://opendata.comune.fi.it/page_dataset_show?id=mercati
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from urllib.request import Request, urlopen

SOURCE = "https://datigis.comune.fi.it/resources/open-data/mercati/feelflorence_mercati.geojson"
SOURCE_PAGE = "https://opendata.comune.fi.it/page_dataset_show?id=mercati"
SOURCE_UPDATED = "2023-03-03"


def classify(name: str, desc: str) -> str:
    joined = (name + " " + desc).casefold()
    if "pulci" in joined or "usato" in joined:
        return "usato"
    if any(t in joined for t in ("gastronomi", "alimentar", "carne", "pesce", "verdura", "frutta")):
        return "alimentare"
    return "misto"


def _coords(feature: dict):
    geom = feature.get("geometry") or {}
    if geom.get("type") != "Point":
        return None, None
    point = geom.get("coordinates")
    if not isinstance(point, list) or len(point) < 2:
        return None, None
    try:
        lon, lat = float(point[0]), float(point[1])
    except (ValueError, TypeError):
        return None, None
    if not (43.7 <= lat <= 43.86 and 11.1 <= lon <= 11.4):
        return None, None
    return lat, lon


def convert(collection: dict) -> list[dict]:
    if not isinstance(collection, dict) or collection.get("type") != "FeatureCollection":
        raise ValueError("Expected GeoJSON FeatureCollection")
    features = collection.get("features")
    if not isinstance(features, list) or not features:
        raise ValueError("Missing official market features")
    output, seen = [], set()
    for feat in features:
        if not isinstance(feat, dict) or feat.get("type") != "Feature":
            continue
        props = feat.get("properties") or {}
        name = str(props.get("nome") or "").strip()
        fid = str(feat.get("id") or "").strip()
        if not name or not fid:
            continue
        if fid in seen:
            raise ValueError("Duplicate Firenze market feature id: " + fid)
        seen.add(fid)
        lat, lon = _coords(feat)
        detail = str(props.get("feelflorence_link") or "").strip()
        if not detail.startswith("https://www.feelflorence.it/"):
            detail = SOURCE_PAGE
        description = str(props.get("descrizione") or "").strip()
        category = classify(name, description)
        output.append({
            "slug": "fi-feelflorence-" + fid,
            "nome": name, "citta": "Firenze", "provincia": "FI", "regione": "Toscana",
            "indirizzo": str(props.get("indirizzo") or "").strip(),
            "lat": lat, "lng": lon,
            "position_quality": "precisa" if lat is not None else "sconosciuta",
            "categoria": category,
            "tags": ["mercato storico"],
            "status": "non_confermato",
            "date": [],
            "date_quality": "sconosciuta",
            "ricorrenza_testo": "Consulta il sito ufficiale per aperture e variazioni",
            "orario_testo": str(props.get("orari") or "").strip()[:180],
            "descrizione": description[:900],
            "fonte": "Comune di Firenze - FeelFlorence (CC BY 4.0)",
            "url_fonte": detail,
            "aggiornato_il": SOURCE_UPDATED,
            "confidence": 0,
        })
    return output


def download():
    req = Request(SOURCE, headers={"User-Agent": "MercatiItaliaOpenData/1.0"})
    with urlopen(req, timeout=30) as resp:
        blob = resp.read(2_000_001)
    if len(blob) > 2_000_000:
        raise ValueError("Firenze GeoJSON unexpectedly large")
    return json.loads(blob.decode("utf-8-sig"))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    collection = json.loads(args.input.read_text("utf-8")) if args.input else download()
    rows = convert(collection)
    if not 1 <= len(rows) <= 200:
        raise ValueError("Official Firenze market feed returned implausible count")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n", "utf-8")
    print("Firenze official market records:", len(rows))


if __name__ == "__main__":
    main()
