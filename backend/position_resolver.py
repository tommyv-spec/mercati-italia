#!/usr/bin/env python3
"""Street-level map positions from OpenStreetMap — one general rule for every market.

Same steps for every source and town, no per-market or per-city cases:
1. A rounded point (at most 2 decimals, about 1 km) shared by markets at
   MIN_SHARED_VENUES or more different venues is a placeholder (a town or
   province centre reused for many markets). It is withdrawn: unknown is
   better than wrong. The old point stays in `coordinate_originali` for audit.
2. A visible market with a real street (or a named venue) and no point, a
   placeholder or a rounded point is looked up on OpenStreetMap Nominatim with
   one free-text query ("street, town, Italia"): at most one request per
   second, identifying User-Agent, never an e-mail, results cached in the
   repository (misses retried after 90 days), a bounded number per run.
3. A result is accepted only when it is street/venue level, in the record's
   own municipality and province (ISTAT), named after the same street, and -
   when the market had its own rounded point - within 15 km of it. Accepted
   points are "approssimata" (street level, never a verified stall position)
   with `posizione_fonte` naming OpenStreetMap (ODbL, attribution required).

Pilot 2026-10-25 (Roma d881 + Florence placeholders, 114 markets): 97
accepted, 97/97 confirmed by an independent reverse lookup. A structured
street/city query found nothing that the free-text query missed.
"""
from __future__ import annotations

import json
import math
import re
import time
import unicodedata
from datetime import date, timedelta
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import atomic_write
from catalog_quality_report import VAGUE_ADDRESSES, key
from reviewed_city_evidence import point_distance_km

NOMINATIM = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "MercatiItalia/1.0 (+https://github.com/tommyv-spec/mercati-italia)"
SOURCE = "openstreetmap"
ATTRIBUTION = "© OpenStreetMap contributors"
LICENSE = "ODbL-1.0"
PLACEHOLDER_REASON = "punto_segnaposto_condiviso"
ROUNDED_REASON = "punto_arrotondato_sostituito_da_via"
OWN_REASONS = frozenset({PLACEHOLDER_REASON, ROUNDED_REASON})
QUALITY = "approssimata"
# Measured on the DEV catalog 2026-10-25: 3 venues flag the city/province centres
# (Rome 41.9/12.5 with 97 venues, Florence, Milan, Turin, ...). 2 would also hide
# genuine pairs, e.g. "corso Vittorio Emanuele" / "... II" on one Pordenone point.
MIN_SHARED_VENUES = 3
MAX_DISTANCE_KM = 15.0
RETRY_MISS_DAYS = 90
MAX_CACHE_ENTRIES = 20_000
MIN_INTERVAL_SECONDS = 1.1
MAX_CONSECUTIVE_ERRORS = 3
ITALY_BOUNDS = (35.0, 48.0, 6.0, 19.6)

STREET = re.compile(
    r"\b(?:via|viale|vicolo|vico|piazza|piazzale|piazzetta|p\.?\s?zza|p\.?\s?za|corso|largo|"
    r"lungomare|lungolago|lungarno|lungotevere|strada|stradone|contrada|borgo|salita|"
    r"passeggiata|circonvallazione|galleria|calle|campo|campiello|fondamenta|riva)\b", re.I)
AREA_ONLY = re.compile(r"^(?:quartiere|zona|rione|localit[aà]|loc\.|frazione|fraz\.|area|centro)\b", re.I)
SEGMENT_END = re.compile(r"\s*(?:[,;(]|\s[-/]\s|\s(?:e|ed|o|oppure)\s|"
                         r"\s(?:ang\.?|angolo|tra|fino|presso|con|nei\s+pressi)\b)", re.I)
HOUSE_NUMBER = re.compile(r"[\s,.]*(?:(?:n\.?|nr\.?|civico)?\s*\d+\s*[a-z]?(?:\s*/\s*\d+)?|s\.?n\.?c\.?)\s*$",
                          re.I)
FILLER = frozenset((
    "via viale vicolo vico piazza piazzale piazzetta pzza pza corso largo lungomare lungolago "
    "lungarno lungotevere strada stradone contrada borgo salita passeggiata circonvallazione "
    "galleria calle campo campiello fondamenta riva localita loc frazione fraz "
    "del della dello dei degli delle dell di da dal dalla e ed il la le lo gli i in al alla "
    "ai agli alle all sul sulla san santa santo sant s ss sp "
    "mercato mercatino mercati settimanale comunale fiera"
).split())
# Words that name a kind of place, not which one: never enough on their own for a
# venue written without a street type ("Pieve centro" is not "Centro Polifunzionale").
GENERIC_PLACE = frozenset((
    "centro storico zona quartiere area parcheggio parco chiesa stazione scuola comune municipio "
    "palazzo giardino giardini pubblico pubblici polifunzionale sociale sportivo civico"
).split())


def fold(value) -> str:
    return key(value)


def distinctive_words(value) -> set[str]:
    return {word for word in fold(value).split()
            if len(word) >= 3 and not word.isdigit() and word not in FILLER}


def street_query(address, citta="") -> str | None:
    """The street (or named venue) a market's address points at, or None.

    Event titles in quotes, parentheses, second streets ("X e Y", "ang.") and
    house numbers are dropped so equal streets share one cache entry.
    """
    text = unicodedata.normalize("NFKC", str(address or "")).replace("\xa0", " ")
    if "�" in text:
        return None  # damaged characters: the lookup could only guess
    text = re.sub(r"[\"“”«»][^\"“”«»]*[\"“”«»]", " ", text)
    text = re.sub(r"\([^)]*\)", " ", text)
    text = " ".join(text.replace("’", "'").split()).strip(" ,;.-")
    if not text or fold(text) in VAGUE_ADDRESSES:
        return None
    match = STREET.search(text)
    if match:
        text = text[match.start():]
        end = SEGMENT_END.search(text, len(match.group(0)))
        if end:
            text = text[:end.start()]
    elif AREA_ONLY.match(text):
        return None  # a district or the centre is not a street-level place
    else:
        end = SEGMENT_END.search(text)
        text = text[:end.start()] if end and end.start() else text
        if not distinctive_words(text) - distinctive_words(citta) - GENERIC_PLACE:
            return None
    text = HOUSE_NUMBER.sub("", text).strip(" ,;.-'")
    town = fold(citta)
    if town:
        text = re.sub(r"\s+(?:di|a|ad|in)\s+" + r"\s+".join(map(re.escape, town.split())) + r"$",
                      "", text, flags=re.I) if fold(text).endswith(" " + town) else text
    # An address that only repeats the town's name is not a street.
    if len(fold(text)) < 6 or not distinctive_words(text) - distinctive_words(citta) or fold(text) in VAGUE_ADDRESSES:
        return None
    return text


# ---------------------------------------------------------------- points

def point(row):
    lat, lng = row.get("lat"), row.get("lng")
    if (isinstance(lat, bool) or isinstance(lng, bool)
            or not isinstance(lat, (int, float)) or not isinstance(lng, (int, float))
            or not (math.isfinite(lat) and math.isfinite(lng))):
        return None
    return (float(lat), float(lng))


def rounded(p) -> bool:
    """At most two decimals: a ~1 km grid point, never a surveyed position."""
    return p is not None and round(p[0], 2) == p[0] and round(p[1], 2) == p[1]


def excluded(row, held_ids=frozenset()) -> str | None:
    """Records another reviewed step owns, or that must stay as their source gave them today."""
    if row.get("slug") in held_ids:
        return "tenuto_invariato_oggi"
    if row.get("position_quality") == "precisa":
        return "posizione_precisa"
    if row.get("navigazione_sospesa_motivo"):
        return "navigazione_sospesa_da_altra_verifica"
    if row.get("coordinate_sospese_motivo") and row["coordinate_sospese_motivo"] not in OWN_REASONS:
        return "coordinate_sospese_da_altra_verifica"
    return None


def restore(row) -> dict:
    """Undo this step's own earlier edit, so every run recomputes from source facts + cache.

    A point a source wrote after us (different from the one we set) is a newer
    source fact and is kept.
    """
    src = row.get("posizione_fonte")
    ours = isinstance(src, dict) and src.get("fonte") == SOURCE
    reason = row.get("coordinate_sospese_motivo") if row.get("coordinate_sospese_motivo") in OWN_REASONS else None
    if not ours and not reason:
        return row
    out = {k: v for k, v in row.items() if k != "posizione_fonte"}
    original = None
    if reason:
        out.pop("coordinate_sospese_motivo")
        original = point(out.pop("coordinate_originali", None) or {})
    current = point(out)
    shown_by_us = (current is None and reason == PLACEHOLDER_REASON) or (
        ours and current == (src.get("lat"), src.get("lng")))
    if shown_by_us and out.get("position_quality") != "precisa":
        out["lat"], out["lng"] = original if original else (None, None)
        out["position_quality"] = "non_verificata" if original else "sconosciuta"
    return out


def venue(row) -> tuple:
    return (fold(row.get("citta")), fold(street_query(row.get("indirizzo"), row.get("citta")) or ""))


def visible(row, today: date) -> bool:
    """Shown to visitors: not a soft-merged copy and not concluded (same rule as the exporter)."""
    from export_static import concluded_reason
    return not row.get("duplicato_di") and not concluded_reason(row, today)


def placeholder_points(rows, today: date, min_venues=MIN_SHARED_VENUES) -> set:
    """Rounded points that visible markets at min_venues+ different venues share."""
    venues = {}
    for row in rows:
        p = point(row)
        if rounded(p) and visible(row, today):
            venues.setdefault(p, set()).add(venue(row))
    return {p for p, found in venues.items() if len(found) >= min_venues}


# ----------------------------------------------------------------- cache

def cache_key(street, citta, provincia) -> str:
    return "|".join(fold(value) for value in (street, citta, provincia))


def empty_cache() -> dict:
    return {"schema": 1, "attribution": ATTRIBUTION, "license": LICENSE, "source": NOMINATIM, "entries": {}}


def validate_cache(cache) -> dict:
    if (not isinstance(cache, dict) or cache.get("schema") != 1
            or cache.get("attribution") != ATTRIBUTION or cache.get("license") != LICENSE
            or not isinstance(cache.get("entries"), dict) or len(cache["entries"]) > MAX_CACHE_ENTRIES):
        raise ValueError("Geocode cache has an unexpected shape")
    lat_min, lat_max, lng_min, lng_max = ITALY_BOUNDS
    for name, entry in cache["entries"].items():
        if not isinstance(name, str) or name.count("|") != 2 or not isinstance(entry, dict):
            raise ValueError("Geocode cache entry has an unexpected key")
        date.fromisoformat(str(entry.get("queried_on", "")))
        if "miss" in entry:
            if set(entry) != {"queried_on", "miss", "query"} or not isinstance(entry["miss"], str):
                raise ValueError("Geocode cache miss has unexpected fields")
            continue
        p = point(entry)
        if (set(entry) != {"queried_on", "lat", "lng", "osm", "class", "type", "name", "query"}
                or p is None or not (lat_min <= p[0] <= lat_max and lng_min <= p[1] <= lng_max)
                or not re.fullmatch(r"(?:node|way|relation)/\d+", str(entry["osm"]))):
            raise ValueError("Geocode cache hit is not a bounded OpenStreetMap point")
    return cache


def load_cache(path) -> dict:
    path = Path(path)
    return validate_cache(json.loads(path.read_text("utf-8"))) if path.is_file() else empty_cache()


def save_cache(path, cache: dict):
    misses = sorted((entry["queried_on"], name) for name, entry in cache["entries"].items() if "miss" in entry)
    while len(cache["entries"]) > MAX_CACHE_ENTRIES and misses:
        del cache["entries"][misses.pop(0)[1]]  # oldest misses go first; hits stay
    validate_cache(cache)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(cache, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                   encoding="utf-8", newline="\n")
    atomic_write.replace(tmp, path)


# ------------------------------------------------------------ validation

TOWN_LEVEL = frozenset({"country", "state", "region", "province", "county", "municipality", "city",
                        "town", "village", "hamlet", "isolated_dwelling", "suburb", "quarter",
                        "neighbourhood", "city_district", "district", "borough", "locality", "farm",
                        "administrative"})
NOT_A_PLACE = frozenset({"boundary", "natural", "waterway", "landuse", "place"})


def municipality_names(address) -> set:
    names = set()
    for field in ("city", "town", "village", "municipality"):
        value = str(address.get(field) or "")
        names.add(fold(value))
        names.update(fold(part) for part in re.split(r"\s+-\s+|/", value))
    return names - {""}


def street_type(text) -> str | None:
    """'piazza', 'via', 'largo'... when the text starts with a street type."""
    match = STREET.match(fold(text))
    if not match:
        return None
    word = re.sub(r"[^a-z]", "", match.group(0))
    return {"pzza": "piazza", "pza": "piazza"}.get(word, word)


def same_street(street, hit, town="") -> bool:
    """The result is named after the market's street or venue (an exact town is not enough).

    Streets and squares are compared by their own name; a venue or shop also by
    the road it stands on (the next part of its display name). Several or
    bilingual names ("A; B", "Kirchplatz - Piazza Chiesa") count one by one. A
    street keeps its type: "Piazza S. Parisio" is not "Via San Parisio".
    """
    parts = [part for part in str(hit["name"]).split(",") if not part.strip().isdigit()]
    named = [name for part in (parts[:1] if hit["class"] in ("highway", "place") else parts[:2])
             for name in re.split(r";|\s+-\s+|/", part)]
    kind, words = street_type(street), distinctive_words(street) - distinctive_words(town)
    if kind is None:
        words -= GENERIC_PLACE
    return any(words & distinctive_words(name) and kind in (None, street_type(name)) for name in named)


def check_result(result, *, street, citta, provincia):
    """Checks of one Nominatim result that hold for every record with this key.

    Returns (cache hit, "") or (None, rejection reason).
    """
    try:
        lat, lng = float(result["lat"]), float(result["lon"])
    except (KeyError, TypeError, ValueError):
        return None, "risultato_non_valido"
    lat_min, lat_max, lng_min, lng_max = ITALY_BOUNDS
    if not (math.isfinite(lat) and math.isfinite(lng) and lat_min <= lat <= lat_max and lng_min <= lng <= lng_max):
        return None, "fuori_italia"
    category, kind = str(result.get("category") or ""), str(result.get("type") or "")
    if ((category in NOT_A_PLACE and not (category == "place" and kind == "square"))
            or str(result.get("addresstype") or "") in TOWN_LEVEL or kind in TOWN_LEVEL):
        return None, "solo_localita"
    address = result.get("address") if isinstance(result.get("address"), dict) else {}
    if fold(citta) not in municipality_names(address):
        return None, "comune_diverso"
    province = str(address.get("ISO3166-2-lvl6") or "")
    if provincia and province and province != "IT-" + provincia.upper():
        return None, "provincia_diversa"
    if not (result.get("osm_type") in ("node", "way", "relation") and str(result.get("osm_id", "")).isdigit()):
        return None, "risultato_non_valido"
    hit = {"lat": round(lat, 6), "lng": round(lng, 6),
           "osm": result["osm_type"] + "/" + str(result["osm_id"]),
           "class": category, "type": kind,
           "name": str(result.get("display_name") or "")[:300]}
    return (hit, "") if same_street(street, hit, citta) else (None, "via_diversa")


def choose(results, *, street, citta, provincia):
    """First of up to five results passing every check, else the first result's reason."""
    if not isinstance(results, list) or not results:
        return None, "nessun_risultato"
    first_reason = ""
    for result in results[:5]:
        hit, reason = (check_result(result, street=street, citta=citta, provincia=provincia)
                       if isinstance(result, dict) else (None, "risultato_non_valido"))
        if hit:
            return hit, ""
        first_reason = first_reason or reason
    return None, first_reason


# --------------------------------------------------------------- network

def query_text(street, citta) -> str:
    return street + ", " + citta + ", Italia"


def nominatim(text: str, *, timeout=20) -> list:
    """One free-text search. No e-mail or other personal data is ever sent."""
    params = {"q": text, "format": "jsonv2", "addressdetails": 1, "countrycodes": "it", "limit": 5}
    request = Request(NOMINATIM + "?" + urlencode(params),
                      headers={"User-Agent": USER_AGENT, "Accept": "application/json"})
    with urlopen(request, timeout=timeout) as response:
        body = response.read(2_000_001)
    if len(body) > 2_000_000:
        raise ValueError("Nominatim response too large")
    data = json.loads(body)
    if not isinstance(data, list):
        raise ValueError("Nominatim response is not a result list")
    return data


# ------------------------------------------------------------------ apply

def istat_provinces(istat: dict) -> dict:
    """{(region, folded town): province code} from the pinned ISTAT register."""
    return {(region, fold(town)): code
            for region, towns in istat["provinces_by_region"].items() for town, code in towns.items()}


def lookup_key(row, provinces):
    """(cache key, query text, province) for a market's street, or (None, skip reason, None)."""
    street = street_query(row.get("indirizzo"), row.get("citta"))
    if not street:
        return None, "no_street", None
    province = provinces.get((row.get("regione"), fold(row.get("citta"))))
    if province is None:
        return None, "town_not_istat", None
    return cache_key(street, row["citta"], province), query_text(street, row["citta"]), province


def _count(counter: dict, name: str):
    counter[name] = counter.get(name, 0) + 1


def resolve(rows, cache, *, today: date, istat: dict, lookup=None, held_ids=frozenset(),
            max_lookups=300, max_seconds=420.0, sleep=time.sleep, clock=time.monotonic):
    """Return (new rows, report). `lookup(text) -> results`, or None for cache only (offline)."""
    provinces = istat_provinces(istat)
    # Held records stay byte-identical; every other record first loses this step's own
    # earlier edit (also when another reviewed step now owns it), then is recomputed.
    rows = [row if row.get("slug") in held_ids else restore(row) for row in rows]
    placeholders = placeholder_points(rows, today)
    report = {
        "schema": 1, "today": today.isoformat(), "source": NOMINATIM, "attribution": ATTRIBUTION,
        "min_shared_venues": MIN_SHARED_VENUES, "max_distance_km": MAX_DISTANCE_KM,
        "max_lookups": max_lookups, "status": "offline_cache_only" if lookup is None else "complete",
        "records": len(rows), "excluded": {}, "placeholder_points": len(placeholders),
        "placeholders_withdrawn": 0, "needing_position": 0, "no_street": 0, "town_not_istat": 0,
        "keys_needed": 0, "lookups": 0, "cache_hits": 0, "cache_misses_reused": 0,
        "accepted": {"placeholder": 0, "no_point": 0, "rounded_point": 0}, "rejected": {},
        "errors": 0, "accepted_examples": [],
    }
    work = []  # (row index, kind, old point, cache key, query text, province)
    for index, row in enumerate(rows):
        reason = excluded(row, held_ids)
        if reason:
            _count(report["excluded"], reason)
            continue
        p = point(row)
        if p is not None and not rounded(p):
            continue
        kind = "no_point" if p is None else ("placeholder" if p in placeholders else "rounded_point")
        report["needing_position"] += 1
        if kind == "placeholder":
            rows[index] = row = {**row, "lat": None, "lng": None, "position_quality": "sconosciuta",
                                 "coordinate_originali": {"lat": p[0], "lng": p[1]},
                                 "coordinate_sospese_motivo": PLACEHOLDER_REASON}
            report["placeholders_withdrawn"] += 1
        name, text, province = lookup_key(row, provinces)
        if name is None:
            report[text] += 1
            continue
        work.append((index, kind, p, name, text, province, visible(row, today)))

    entries = cache["entries"]
    for name, entry in entries.items():
        # The cache never keeps a hit today's rules would refuse; it is retried like a miss.
        if "miss" not in entry and not same_street(name.split("|")[0], entry, name.split("|")[1]):
            entries[name] = {"queried_on": entry["queried_on"], "miss": "via_diversa", "query": entry["query"]}
    stale = (today - timedelta(days=RETRY_MISS_DAYS)).isoformat()
    priority = {"placeholder": 0, "no_point": 1, "rounded_point": 2}
    queue = {}
    for index, kind, _, name, text, province, shown in work:
        entry = entries.get(name)
        # Lookups are spent only on markets visitors can see; hidden copies reuse the cache.
        if shown and (entry is None or ("miss" in entry and entry["queried_on"] <= stale)):
            if name not in queue or priority[kind] < queue[name][0]:
                queue[name] = (priority[kind], text, rows[index]["citta"], province)
    keys = {item[3] for item in work}
    report["keys_needed"] = len(queue)
    report["cache_hits"] = sum(1 for name in keys if name in entries and "miss" not in entries[name])
    report["cache_misses_reused"] = sum(1 for name in keys
                                        if name in entries and "miss" in entries[name] and name not in queue)
    if lookup is not None:
        started, last, errors = clock(), None, 0
        for name, (_, text, citta, province) in sorted(queue.items(), key=lambda item: (item[1][0], item[0])):
            if report["lookups"] >= max_lookups:
                report["status"] = "budget_exhausted"
                break
            if clock() - started >= max_seconds:
                report["status"] = "time_exhausted"
                break
            if last is not None:
                sleep(max(0.0, MIN_INTERVAL_SECONDS - (clock() - last)))
            last = clock()
            report["lookups"] += 1
            try:
                results = lookup(text)
            except HTTPError as error:
                if error.code in (403, 429):
                    report["status"] = "stopped_http_" + str(error.code)
                    break
                results = None
            except (URLError, OSError, ValueError):
                results = None
            if results is None:
                report["errors"] += 1
                errors += 1
                if errors >= MAX_CONSECUTIVE_ERRORS:
                    report["status"] = "stopped_errors"
                    break
                continue  # errors are never cached: the key is retried next run
            errors = 0
            hit, reason = choose(results, street=name.split("|")[0], citta=citta, provincia=province)
            entries[name] = ({**hit, "queried_on": today.isoformat(), "query": text} if hit
                             else {"queried_on": today.isoformat(), "miss": reason, "query": text})

    for index, kind, old, name, *_ in work:
        entry = entries.get(name)
        if entry is None:
            reason = "non_ancora_cercato"
        elif "miss" in entry:
            reason = entry["miss"]
        elif (kind == "rounded_point"
              and point_distance_km(old, (entry["lat"], entry["lng"])) > MAX_DISTANCE_KM):
            # Only the market's own rough point bounds the distance. A placeholder is
            # a shared town/province centre, not this market's place: there the
            # municipality and province checks are the bound.
            reason = "lontano_dal_punto_originale"
        else:
            reason = ""
        if reason:
            _count(report["rejected"], reason)
            continue
        row = rows[index]
        source = {"fonte": SOURCE, "licenza": LICENSE, "attribuzione": ATTRIBUTION,
                  "osm": entry["osm"], "tipo": entry["class"] + "/" + entry["type"],
                  "trovato": entry["name"], "chiave": name, "cercato_il": entry["queried_on"],
                  "lat": entry["lat"], "lng": entry["lng"]}
        updated = {**row, "lat": entry["lat"], "lng": entry["lng"], "position_quality": QUALITY,
                   "posizione_fonte": source}
        if kind == "rounded_point":
            updated["coordinate_originali"] = {"lat": old[0], "lng": old[1]}
            updated["coordinate_sospese_motivo"] = ROUNDED_REASON
        rows[index] = updated
        report["accepted"][kind] += 1
        report["accepted_examples"].append({"slug": row["slug"], "key": name, "osm": entry["osm"],
                                            "tipo": source["tipo"], "trovato": entry["name"]})
    report["rejected"] = dict(sorted(report["rejected"].items()))
    report["excluded"] = dict(sorted(report["excluded"].items()))
    return rows, report


# ---------------------------------------------------------------- guards

POSITION_FIELDS = frozenset({"lat", "lng", "position_quality", "coordinate_originali",
                             "coordinate_sospese_motivo", "posizione_fonte"})
SOURCE_FIELDS = frozenset({"fonte", "licenza", "attribuzione", "osm", "tipo", "trovato", "chiave",
                           "cercato_il", "lat", "lng"})


def clean_position_source(value, row) -> dict | None:
    """The exporter keeps `posizione_fonte` only in its exact shape and for the point it describes."""
    if not isinstance(value, dict) or set(value) != SOURCE_FIELDS or row.get("position_quality") != QUALITY:
        return None
    try:
        date.fromisoformat(str(value["cercato_il"]))
        same_point = (float(value["lat"]), float(value["lng"])) == (row.get("lat"), row.get("lng"))
    except (TypeError, ValueError):
        return None
    if (not same_point or (value["fonte"], value["licenza"], value["attribuzione"]) != (SOURCE, LICENSE, ATTRIBUTION)
            or not re.fullmatch(r"(?:node|way|relation)/\d+", str(value["osm"]))
            or not all(isinstance(value[k], str) and len(value[k]) <= 300 for k in ("tipo", "trovato", "chiave"))
            or value["chiave"].count("|") != 2):
        return None
    return dict(value)


def _consistent(row) -> bool:
    """A row this step touched is in exactly one of its three end states."""
    src, reason = row.get("posizione_fonte"), row.get("coordinate_sospese_motivo")
    original = point(row.get("coordinate_originali") or {})
    if src is not None:
        return (clean_position_source(src, row) == src
                and (reason is None and original is None
                     or reason in OWN_REASONS and rounded(original)))
    return (reason == PLACEHOLDER_REASON and rounded(original)
            and row.get("lat") is None and row.get("lng") is None
            and row.get("position_quality") == "sconosciuta")


def verify_diff(before, after, *, held_ids=frozenset()) -> dict:
    """Independent diff guard: only position fields of records this step owns may change."""
    if [row["slug"] for row in before] != [row["slug"] for row in after]:
        raise ValueError("Position step added, removed or reordered market identities")
    changed = 0
    for left, right in zip(before, after):
        if left == right:
            continue
        fields = {k for k in left.keys() | right.keys() if left.get(k) != right.get(k)}
        if (fields - POSITION_FIELDS or left["slug"] in held_ids
                or excluded(left) and right != restore(left)
                or right.get("position_quality") == "precisa" and left.get("position_quality") != "precisa"
                or not (_consistent(right) or restore(right) == right)):
            raise ValueError("Position step changed an unowned field or record: " + right["slug"])
        changed += 1
    return {"schema": 1, "release_safe": True, "records_checked": len(after), "records_changed": changed,
            "fields_allowed": sorted(POSITION_FIELDS), "ids_added": 0, "ids_removed": 0}


def verify_static(rows, cache, *, today: date, istat: dict, held_ids=frozenset()) -> dict:
    """Final guard on the exported catalog: every OSM point is reproducible from the cache
    for the market's current address, and no visible market shows a placeholder point."""
    validate_cache(cache)
    provinces = istat_provinces(istat)
    entries = cache["entries"]
    owned = 0
    for row in rows:
        src, reason = row.get("posizione_fonte"), row.get("coordinate_sospese_motivo")
        if src is None and reason not in OWN_REASONS:
            continue
        owned += 1
        name, _, _ = lookup_key(row, provinces)
        entry = entries.get(src["chiave"]) if isinstance(src, dict) else None
        if (excluded(row) or not _consistent(row)
                or src is not None and (
                    entry is None or "miss" in entry or src["chiave"] != name
                    or (entry["lat"], entry["lng"], entry["osm"]) != (src["lat"], src["lng"], src["osm"])
                    or not same_street(name.split("|")[0], entry, name.split("|")[1]))):
            raise ValueError("Exported street-level position is not reproducible: " + row["slug"])
    shown = placeholder_points(rows, today)
    originals = {point(row["coordinate_originali"]) for row in rows
                 if row.get("coordinate_sospese_motivo") == PLACEHOLDER_REASON}
    leaks = [row["slug"] for row in rows
             if point(row) in shown | originals and visible(row, today)
             and not excluded(row, held_ids)]
    if leaks:
        raise ValueError("A visible market still shows a shared placeholder point: " + leaks[0])
    return {"schema": 1, "release_safe": True, "records_checked": len(rows),
            "records_with_resolver_fields": owned,
            "osm_positions": sum(1 for row in rows if row.get("posizione_fonte")),
            "placeholder_points_still_shown": 0, "precise_claims_created": 0}


def main(argv=None) -> int:
    """QA re-check of a candidate, independent of the run that produced it."""
    import argparse
    from merge_catalog import load_existing
    parser = argparse.ArgumentParser(description=main.__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--cache", type=Path, required=True)
    args = parser.parse_args(argv)
    report = json.loads(args.report.read_text("utf-8"))
    if report.get("enabled") is not True:
        print("Street-position step disabled by policy: nothing to verify.")
        return 0
    if (report["lookups"] > report["max_lookups"] or report["max_lookups"] > 300
            or report["diff_guard"].get("release_safe") is not True or "@" in USER_AGENT):
        raise ValueError("Street-position run exceeded its bound or lost its diff proof")
    istat = json.loads((Path(__file__).resolve().parent / "data" / "istat-comuni-2026.json").read_text("utf-8"))
    proof = verify_static(load_existing(args.manifest), load_cache(args.cache),
                          today=date.fromisoformat(report["today"]), istat=istat,
                          held_ids=frozenset(report["held_ids"]))
    print(json.dumps(proof, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
