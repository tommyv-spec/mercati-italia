#!/usr/bin/env python3
"""Bounded Rome XIII official map -> existing national catalog review (no import).

Municipio XIII publicly links to a My Maps document (published Dec 2024).
Nine place markers contain addresses and schedules, but no per-market 2026
verification dates. They are SEARCH LEADS only, not verified market openings,
navigable GPS points, or rights-cleared data for automatic republication.
"""
from __future__ import annotations

import argparse
import json
import math
import re
import unicodedata
from collections import Counter
from datetime import date
from pathlib import Path

from merge_catalog import load_existing
from recurrence_refresh import explicit_rule

MUNICIPAL_PAGE = "https://www.comune.roma.it/web/it/informazione-di-servizio.page?contentId=IDS1305104"
MAP_ID = "1qazVyQE42cRyzP-gMSxjZz8wX8iowbQ"
SOURCE_DATE = date(2024, 12, 16)
MAX_ROWS = 30
MAX_CATALOG = 100_000
CITY = "Roma"
REGION = "Lazio"

# Exact publisher street fragments, pre-reviewed from each KML marker.
# None may be used to auto-geocode or change a market record.
MARKER_STREETS = {
    "rm13-01": ("via aurelia",),
    "rm13-02": ("via di san silverio",),
    "rm13-03": ("borgo ticino",),
    "rm13-04": ("piazza ormea",),
    "rm13-05": ("via guido calcagnini",),
    "rm13-06": ("via di montespaccato","via gaetano mazzoni"),
    "rm13-07": ("via cornelia",),
    "rm13-08": ("viale di valle aurelia",),
    "rm13-09": ("via urbano ii","largo scarampi"),
}
NAME_STOP = frozenset({"mercato","mercati","rionale","rionali","settimanale","di","del","dei","della",
                        "su","via","piazza","largo","sede","impropria","scoperto"})


def key(value):
    s=unicodedata.normalize("NFKD",str(value or ""))
    ascii_text="".join(c for c in s if not unicodedata.combining(c))
    return " ".join(re.findall(r"[a-z0-9]+",ascii_text.casefold()))


def name_matches(official_name, record_name):
    requested=[x for x in key(official_name).split() if x not in NAME_STOP]
    present=key(record_name).split()
    return bool(requested) and all(x in present for x in requested)


def street_matches(marker, record):
    haystack=key(record.get("indirizzo"))
    if not haystack: return False
    return any(key(street) in haystack for street in MARKER_STREETS[marker["source_key"]])


def weekday_matches(marker, record):
    rule=explicit_rule(record.get("ricorrenza_testo"))
    if not rule or rule.get("kind")!="weekly":
        return None
    known=set(rule["weekdays"])
    observed=set(marker["source_weekdays"])
    return bool(known and observed and known.issubset(observed))


def distance_km(marker, record):
    lat,lon=record.get("lat"),record.get("lng")
    if (not isinstance(lat,(float,int)) or isinstance(lat,bool)
            or not isinstance(lon,(float,int)) or isinstance(lon,bool)):
        return None
    try:
        a,b=math.radians(float(marker["latitude"])),math.radians(float(lat))
        dl=math.radians(float(marker["longitude"])-float(lon))
        diff=b-a
        h=math.sin(diff/2)**2 + math.cos(a)*math.cos(b)*math.sin(dl/2)**2
        return 12742 * math.asin(min(1,math.sqrt(max(0,h))))
    except (ValueError,OverflowError):
        return None


def validate_map(source):
    if (not isinstance(source,dict) or source.get("schema")!=1
            or source.get("source_page")!=MUNICIPAL_PAGE
            or source.get("source_page_date")!=SOURCE_DATE.isoformat()
            or source.get("published_map_mid")!=MAP_ID
            or source.get("future_events_verified")!=0
            or source.get("visits_confirmed")!=0
            or source.get("imported_records_allowed")!=0
            or source.get("license_per_distribution_not_legally_reviewed") is not True
            or source.get("positions_are_map_markers_not_verified_navigation_points") is not True
            or source.get("expected_marker_count")!=9
            or not isinstance(source.get("observations"),list)
            or len(source["observations"])!=9):
        raise ValueError("Unreviewed official Rome XIII map inventory")
    ids=set()
    unique_place_and_day=set()
    for obs in source["observations"]:
        if not isinstance(obs,dict):
            raise ValueError("Non-object market source marker")
        identifier=obs.get("source_key")
        if identifier not in MARKER_STREETS or identifier in ids:
            raise ValueError("Non-approved or repeated source marker ID")
        ids.add(identifier)
        if (not isinstance(obs.get("source_name"),str) or
                not isinstance(obs.get("source_address"),str) or
                len(obs["source_name"])<3 or len(obs["source_address"])<10 or
                not isinstance(obs.get("source_schedule_excerpt"),str) or
                not isinstance(obs.get("source_weekdays"),list) or
                not obs["source_weekdays"] or
                any(type(d) is not int or not 0<=d<=6 for d in obs["source_weekdays"]) or
                len(set(obs["source_weekdays"]))!=len(obs["source_weekdays"]) or
                not (41.8<float(obs["latitude"])<42.05
                     and 12.3<float(obs["longitude"])<12.7)):
            raise ValueError("Malformed Rome publisher map name, location or schedule")
        identity=(key(obs["source_name"]),key(obs["source_address"]),tuple(obs["source_weekdays"]))
        if identity in unique_place_and_day:
            raise ValueError("Two source markers refer to the same name/address/day")
        unique_place_and_day.add(identity)
    if ids != set(MARKER_STREETS):
        raise ValueError("Official Rome map IDs unexpectedly changed")
    montes=[obs for obs in source["observations"] if key(obs["source_name"])=="montespaccato"]
    if len(montes)!=2 or (montes[0]["source_weekdays"]==montes[1]["source_weekdays"]
                           or key(montes[0]["source_address"])==key(montes[1]["source_address"])):
        raise ValueError("Distinct Montespaccato market venues cannot be collapsed")
    return source["observations"]


def review(rows, source, today=None):
    today=today or date.today()
    markers=validate_map(source)
    if not isinstance(rows,list) or not 1<=len(rows)<=MAX_CATALOG:
        raise ValueError("Unbounded/missing national market catalog")
    seen=set()
    city=[]
    for record in rows:
        sid=record.get("slug")
        if not isinstance(sid,str) or not sid or sid in seen:
            raise ValueError("Duplicate or invalid preserved market ID")
        seen.add(sid)
        if record.get("regione")==REGION and key(record.get("citta"))=="roma":
            city.append(record)

    observations=[]
    stats=Counter()
    for marker in markers:
        overlaps=[]
        for market in city:
            name=name_matches(marker["source_name"],market.get("nome"))
            street=street_matches(marker,market)
            day=weekday_matches(marker,market)
            if not (name or street):
                continue
            km=distance_km(marker,market)
            if km is not None and km>1.0:
                reason="coordinates_disagree_requires_source_review"
            elif name and street and day is not False:
                reason="same_venue_strong_review_candidate"
            elif street and day is True:
                reason="same_street_and_weekday_review_candidate"
            elif name and street:
                reason="same_name_street_calendar_ambiguous"
            else:
                reason="partial_name_or_street_review_only"
            overlaps.append({
                "published_market_id":market["slug"],"match_type":reason,
                "supports_name":name,"supports_street":street,
                "weekday_compatible":day,
                "distance_km":round(km,3) if km is not None else None,
            })
        overlaps.sort(key=lambda m:(
            0 if m["match_type"].startswith("same_venue_strong") else
            1 if m["match_type"].startswith("same_street") else 2,
            m["published_market_id"],
        ))
        if not overlaps:
            bucket="not_in_exact_match_sample_not_proof_of_missing_market"
        elif any(m["match_type"]=="coordinates_disagree_requires_source_review"
                 for m in overlaps):
            bucket="location_conflict_needs_review"
        elif len(overlaps)==1 and overlaps[0]["match_type"]=="same_venue_strong_review_candidate":
            bucket="strong_source_match_review_only"
        else:
            bucket="ambiguous_overlap_review_only"
        stats[bucket]+=1
        observations.append({
            "source_key":marker["source_key"],
            "market_name":marker["source_name"],
            "source_type":marker["source_category"],
            "source_street":marker["source_address"],
            "published_weekdays":marker["source_weekdays"],
            "publisher_marker_lat":marker["latitude"],
            "publisher_marker_lon":marker["longitude"],
            "review_bucket":bucket,
            "candidate_catalog_rows":len(overlaps),
            "examples":overlaps[:5],
            "source_verified_2026":False,
            "navigation_supported":False,
            "automatic_enrichment_allowed":False,
        })
    return {
        "schema":1,"role":"municipal_map_place_matching_only",
        "review_only":True,
        "source_page":MUNICIPAL_PAGE,
        "source_first_publication":SOURCE_DATE.isoformat(),
        "source_age_days":(today-SOURCE_DATE).days,
        "municipal_map_markers":len(markers),
        "rome_catalog_cards":len(city),
        "original_market_ids_preserved":len(rows),
        "source_market_ids_published":0,
        "market_cards_modified":0,
        "future_events_confirmed":0,
        "road_directions_enabled":0,
        "data_license_cleared_automatically":False,
        "counts":dict(sorted(stats.items())),
        "observations":observations,
    }


def markdown(report):
    out=[
        "# Roma Municipio XIII: 9 sedi dalla mappa comunale",
        "",
        "Fonte comunale pubblicata nel dicembre 2024, senza verifica per singolo mercato nel 2026.",
        "Le coordinate sono marker della mappa, NON punti per navigazione verificati.",
        "Nessuna scheda nazionale è stata modificata, creata o confermata.",
        "",
        f"- Sedi sulla mappa: **{report['municipal_map_markers']}**",
        f"- Schede Roma nel catalogo: **{report['rome_catalog_cards']}**",
        f"- Fonte vecchia di **{report['source_age_days']} giorni**; nessun calendario 2026 dichiarato confermato.",
        "",
        "| Sede sorgente | Tipo | Giorni | Matching | Schede candidate |",
        "|---|---|---|---|---:|",
    ]
    dow="Lu Ma Me Gi Ve Sa Do".split()
    for row in report["observations"]:
        days=", ".join(dow[d] for d in row["published_weekdays"])
        out.append(f"| {row['market_name']} ({row['source_key']}) | {row['source_type']} | "
                   f"{days} | {row['review_bucket']} | {row['candidate_catalog_rows']} |")
    out.extend(["",
                "## Regole per miglioramenti futuri",
                "",
                "- Cercare un documento comunale 2026 che confermi sede/giorni e diritto di riuso.",
                "- Non trasformare nomi uguali in doppioni: i due Montespaccato hanno sedi/giorni diversi.",
                "- Confrontare i dettagli della singola sede; non usare orari di categorie come orari effettivi.",
                "- Non sostituire indirizzi, punti, ID o fonti senza prova specifica.",
                "",
                "Fonte: "+MUNICIPAL_PAGE,
                ""])
    return "\n".join(out)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--source",type=Path,
                   default=Path("backend/data/roma-municipio-xiii-market-map-reviewed.json"))
    p.add_argument("--today",type=date.fromisoformat,default=date.today())
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    result=review(load_existing(a.manifest),json.loads(a.source.read_text("utf-8")),today=a.today)
    for target in (a.out,a.report):target.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n","utf-8")
    a.report.write_text(markdown(result),"utf-8")
    print("ROME_XIII_MARKET_EVIDENCE",json.dumps({
        "publisher_markers":result["municipal_map_markers"],
        "old_rome_cards_compared":result["rome_catalog_cards"],
        "catalog_market_ids_retained":result["original_market_ids_preserved"],
        "new_markets_confirmed":0,
        "source_conflicts":result["counts"].get("location_conflict_needs_review",0),
    }))


if __name__=="__main__":
    main()
