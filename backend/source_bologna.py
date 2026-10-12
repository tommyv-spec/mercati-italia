#!/usr/bin/env python3
"""Bologna Opendatasoft municipal market *inventory* adapter.

Manual evidence: 249 records in mercati-e-fiere on 2026-10-12.
Exactly 48 are market (rionale/periodico) or farmers' markets;
the rest are fairs, single stalls and concession locations.
Opendatasoft v1 returns official 40-hex recordid, which v2 omits.

Publication policy:
* CC BY 4.0 as DECLARED by Comune di Bologna, attribution compulsory.
* Last actual data ingestion is 2025-04-02, not the later manually
  maintained modified field (2025-12-31), so NO 2026 dates are confirmed.
* Never invent a daily/weekly recurrence from complex prose.
* No production writes. Upstream changes fail closed with a QA checkpoint.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from datetime import date, datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from recurrence_refresh import explicit_rule, project_dates, WEEKDAYS

DATASET_ID = "mercati-e-fiere"
SOURCE_PAGE = "https://opendata.comune.bologna.it/explore/dataset/mercati-e-fiere/"
METADATA_URL = (
    "https://opendata.comune.bologna.it/api/explore/v2.1/"
    "catalog/datasets/mercati-e-fiere"
)
RECORDS_URL = (
    "https://opendata.comune.bologna.it/api/records/1.0/search/"
    "?dataset=mercati-e-fiere&rows=350"
)
MAX_BYTES = 1_500_000
MAX_ROWS = 400
MIN_ROWS = 220
MIN_MARKETS = 40
MAX_MARKETS = 65
MAX_SOURCE_AGE_DAYS = 540
FULL_WEEKDAYS = ("lunedi", "martedi", "mercoledi", "giovedi",
                 "venerdi", "sabato", "domenica")
WEEKLY_TOKEN = r"(?:lunedi|martedi|mercoledi|giovedi|venerdi|sabato|domenica)"
MONTH_ORDINAL = r"(?:primo|prima|secondo|seconda|terzo|terza|quarto|quarta|ultimo|ultima)"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def textkey(value):
    s = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join("".join(x for x in s if not unicodedata.combining(x))
                    .casefold().replace("–", "-").split())


def url_is_allowed(value):
    if value not in (METADATA_URL, RECORDS_URL):
        return False
    parts = urlsplit(value)
    return (parts.scheme == "https"
            and parts.hostname == "opendata.comune.bologna.it"
            and not parts.username and not parts.password
            and parts.port in (None, 443) and not parts.fragment)


def fetch_json(url):
    if not url_is_allowed(url):
        raise ValueError("Unapproved official Bologna endpoint")
    req = Request(url, headers={
        "Accept": "application/json",
        "Accept-Encoding": "identity",
        "User-Agent": "MercatiItaliaMunicipalInventory/1.0"
    })
    with build_opener(NoRedirect).open(req, timeout=20) as response:
        blob = response.read(MAX_BYTES + 1)
    if len(blob) > MAX_BYTES:
        raise ValueError("Bologna endpoint exceeded bounded response size")
    return json.loads(blob.decode("utf-8-sig"))


def metadata_info(raw):
    if not isinstance(raw, dict) or raw.get("dataset_id") != DATASET_ID:
        raise ValueError("Unexpected Bologna metadata dataset ID")
    meta = (raw.get("metas") or {}).get("default") or {}
    if meta.get("license") != "CC BY 4.0":
        raise ValueError("Bologna dataset license changed, rights review required")
    if meta.get("modified_updates_on_data_change") is not False:
        raise ValueError("Bologna modified-date semantics changed; review required")
    try:
        timestamp = datetime.fromisoformat(
            str(meta["data_processed"]).replace("Z", "+00:00")
        ).astimezone(timezone.utc)
        declared = datetime.fromisoformat(
            str(meta["modified"]).replace("Z", "+00:00")
        ).astimezone(timezone.utc)
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Official Bologna processing/date metadata unavailable") from exc
    if not isinstance(meta.get("records_count"), int):
        raise ValueError("Publisher market inventory count missing")
    if not MIN_ROWS <= meta["records_count"] <= MAX_ROWS:
        raise ValueError("Unexpected Bologna inventory size")
    return {
        "processed_date": timestamp.date().isoformat(),
        "declared_modified_date": declared.date().isoformat(),
        "expected_count": meta["records_count"],
        "license_claim": meta["license"],
        "scope": "dataset_not_each_market",
    }


def download(fetch=fetch_json):
    before = metadata_info(fetch(METADATA_URL))
    response = fetch(RECORDS_URL)
    if not isinstance(response, dict):
        raise ValueError("Malformed Bologna records response")
    records = response.get("records")
    if (response.get("nhits") != before["expected_count"]
            or not isinstance(records, list)
            or len(records) != before["expected_count"]):
        raise ValueError("Incomplete official Bologna snapshot, no partial import")
    after = metadata_info(fetch(METADATA_URL))
    if before != after:
        raise ValueError("Bologna dataset changed during download; rerun")
    return {
        "dataset_id": DATASET_ID,
        "publisher_data_updated_at": before["processed_date"],
        "publisher_claimed_modified_at": before["declared_modified_date"],
        "publisher_update_scope": before["scope"],
        "publisher_license_claim": before["license_claim"],
        "expected_rows": before["expected_count"],
        "rows": records,
    }


def schedule_rule(value):
    """Accept only complete, unambiguous weekday or monthly expressions."""
    s = textkey(value)
    # Explicit consecutive-day range: Lunedì-sabato, not "and holidays".
    m = re.fullmatch(r"(" + WEEKLY_TOKEN + r")\s*-\s*(" + WEEKLY_TOKEN + r")", s)
    if m:
        start, end = FULL_WEEKDAYS.index(m.group(1)), FULL_WEEKDAYS.index(m.group(2))
        return {"kind": "weekly", "weekdays": list(range(start, end + 1))} if start <= end else None
    # Explicit weekday list: Tuesday, Friday or Monday and Wednesday.
    if re.fullmatch(WEEKLY_TOKEN + r"(?:(?:,\s*|\s+e\s+)" + WEEKLY_TOKEN + r")*", s):
        days = sorted(set(FULL_WEEKDAYS.index(token) for token in
                          re.findall(WEEKLY_TOKEN, s)))
        return {"kind": "weekly", "weekdays": days}
    # No monthly dates if "excluding July/August" or extra weekday clause
    # could change the true edition calendar.
    if re.fullmatch(r"(?:ogni\s+)?"+MONTH_ORDINAL+r"\s+"+WEEKLY_TOKEN+r"\s+del\s+mese", s):
        rule = explicit_rule(s)
        return rule if rule and rule["kind"] == "monthly_nth_weekday" else None
    return None


def official_market(fields):
    kind, sub = textkey(fields.get("tipologia")), textkey(fields.get("tipologia_mercato"))
    return ((kind == "mercato" and sub in ("rionale", "periodico"))
            or kind == "mercato produttori agricoli")


def position(fields):
    point = fields.get("geopoint")
    if not isinstance(point, list) or len(point) != 2:
        return None, None
    try:
        lat, lon = float(fields["lat"]), float(fields["long"])
        point_lat, point_lon = float(point[0]), float(point[1])
    except (KeyError, ValueError, TypeError, OverflowError):
        return None, None
    if (44.40 <= lat <= 44.60 and 11.15 <= lon <= 11.50
            and abs(lat-point_lat) <= .0003 and abs(lon-point_lon) <= .0003):
        return round(lat, 6), round(lon, 6)
    return None, None


def category(fields):
    text = textkey(fields.get("specializzazione") or "")
    if "antiquariat" in text or "modernariat" in text:
        return "antiquariato"
    if "vintage" in text or "venti anni" in text:
        return "vintage_abbigliamento"
    if "alimentar" in text or "prodotti agricoli" in text:
        return "alimentare"
    if textkey(fields.get("tipologia")) == "mercato produttori agricoli":
        return "alimentare"
    return "misto"


def convert(payload, today=None):
    today = today or date.today()
    if (not isinstance(payload, dict) or payload.get("dataset_id") != DATASET_ID
            or payload.get("publisher_update_scope") != "dataset_not_each_market"
            or payload.get("publisher_license_claim") != "CC BY 4.0"
            or not isinstance(payload.get("rows"), list)
            or not MIN_ROWS <= len(payload["rows"]) <= MAX_ROWS
            or payload.get("expected_rows") != len(payload["rows"])):
        raise ValueError("Untrusted Bologna source snapshot")
    try:
        processed = date.fromisoformat(payload["publisher_data_updated_at"])
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Bologna source data timestamp missing") from exc
    source_age = (today - processed).days
    if source_age < 0:
        raise ValueError("Bologna source date in the future")
    allow_predictions = source_age <= MAX_SOURCE_AGE_DAYS
    result = []
    counts = Counter()
    ids = set()
    for source in payload["rows"]:
        if not isinstance(source, dict) or source.get("datasetid") != DATASET_ID:
            raise ValueError("Unknown row in Bologna source snapshot")
        rid = str(source.get("recordid") or "").lower()
        if not re.fullmatch(r"[0-9a-f]{40}", rid):
            raise ValueError("Official Bologna record identifier not stable or missing")
        if rid in ids:
            raise ValueError("Duplicate official Bologna record identifier")
        ids.add(rid)
        fields = source.get("fields")
        if not isinstance(fields, dict):
            raise ValueError("Missing Bologna source row fields")
        if not official_market(fields):
            counts["excluded_fairs_stalls_seasonal"] += 1
            continue
        name = str(fields.get("denominazione") or "").strip()
        raw_address = str(fields.get("ubicazione") or "").strip()
        if not name or not raw_address:
            raise ValueError("Curated Bologna market lacks name or location")
        place_uncertain = "trasferimento temporaneo" in textkey(raw_address)
        # Do not suggest potentially outdated relocation directions.
        address = "" if place_uncertain else raw_address[:240]
        kind = textkey(fields.get("tipologia"))
        subtype = textkey(fields.get("tipologia_mercato"))
        if kind == "mercato produttori agricoli":
            label = "Mercato dei produttori agricoli – " + name.title()
        elif subtype == "rionale":
            label = "Mercato rionale " + name.title()
        else:
            label = ("Mercato " if not textkey(name).startswith("mercato ") else "") + name.title()
        rule = schedule_rule(fields.get("giorni_svolgimento"))
        if allow_predictions and rule:
            dates = project_dates(rule, today, 120)
            if rule["kind"] == "weekly":
                recurrence = "settimanale - " + ", ".join(WEEKDAYS[i] for i in rule["weekdays"])
            else:
                recurrence = "mensile - " + textkey(fields["giorni_svolgimento"])
        else:
            dates = []
            recurrence = "Calendario da verificare presso il Comune"
        lat, lng = position(fields)
        origin_hours = str(fields.get("orario_svolgimento") or "").strip()
        hours = origin_hours[:130] + " (fonte da verificare)" if origin_hours else ""
        note = (
            "Scheda di mercato dal piano comunale di Bologna. "
            "Fonte con ultima elaborazione dati del " + processed.isoformat()
            + "; la data di ultima modifica dei metadati non prova nuovi appuntamenti. "
            "Giorni descritti dalla fonte: " + str(fields.get("giorni_svolgimento") or "non disponibili")[:180]
            + ". Nessuna edizione è confermata automaticamente."
        )
        if place_uncertain:
            note += " Posizione provvisoria nella fonte storica: " + raw_address[:150] + "."
        result.append({
            "slug": "bo-open-" + rid,
            "nome": label[:160], "citta": "Bologna", "provincia": "BO",
            "regione": "Emilia-Romagna", "indirizzo": address,
            "lat": lat, "lng": lng,
            "position_quality": "non_verificata" if lat is not None else "sconosciuta",
            "categoria": category(fields),
            "tags": ["mercato comunale", "mercato agricolo" if kind == "mercato produttori agricoli" else subtype],
            "status": "non_confermato", "date": dates,
            "date_quality": "prevista" if dates else "sconosciuta",
            "ricorrenza_testo": recurrence, "orario_testo": hours,
            "descrizione": note[:900],
            "fonte": "Comune di Bologna, dati aperti CC BY 4.0 (licenza dichiarata)",
            "url_fonte": SOURCE_PAGE,
            "aggiornato_il": processed.isoformat(),
            "aggiornamento_ambito": "dataset",
            "id_fonte": rid,
            "verificato_il": "",
            "confidence": 0,
        })
        counts["curated_markets"] += 1
    if not MIN_MARKETS <= len(result) <= MAX_MARKETS:
        raise ValueError("Bologna market classification changed; needs re-review")
    if len(result) + counts["excluded_fairs_stalls_seasonal"] != len(payload["rows"]):
        raise ValueError("Incomplete classification of publisher records")
    return sorted(result, key=lambda r: r["slug"])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", type=Path)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = p.parse_args()
    official = json.loads(args.input.read_text("utf-8")) if args.input else download()
    records = convert(official, today=args.today)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(records, indent=2, ensure_ascii=False)+"\n","utf-8")
    print(json.dumps({
        "curated":len(records), "source_rows":official["expected_rows"],
        "with_forecast_dates":sum(bool(row["date"]) for row in records),
        "review_only":True, "automatically_confirmed":0,
    }))


if __name__ == "__main__":
    main()
