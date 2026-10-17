#!/usr/bin/env python3
"""Two exact-source Rome XIII coordinate holds, never positive geocoding.

Roma's published 2024 municipality map puts IRNERIO and CASALOTTI 6.2 and
10.7 km away from the same coarse 41.9,12.5 point in the existing catalog.
This does NOT establish an accurate 2026 point. Withdraw only the disproven
indicative coordinate and unsafe directions, retain the source coordinates
and every original field. Exact stable IDs and original source URL required.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from reviewed_city_evidence import point_distance_km, NAVIGATION_HOLD, COORD_HOLD
from roma_xiii_map_audit import validate_map
from merge_catalog import load_existing

SOURCE_GIT_BLOB_SHA = "21c5b8e0b9415238f3953021661e79cd85ac7385"
SOURCE_PAGE = "https://www.comune.roma.it/web/it/informazione-di-servizio.page?contentId=IDS1305104"
ORIGINAL_URL = "https://dati.comune.roma.it/catalog/dataset/d881"
OBSERVATION_DATE = "2026-10-12"
ORIGINAL_POINT = {"lat":41.9,"lng":12.5}
MIN_DISTANCE_KM = 3.0
MAX_CASES = 2

# Identifiers were checked in the actual 13,779-row catalog; not a fuzzy match.
CASES = {
    "irnerio-roma":{
        "name":"Irnerio","street":"Via Aurelia","map_key":"rm13-01",
    },
    "casalotti-roma":{
        "name":"Casalotti","street":"Via Borgo Ticino","map_key":"rm13-03",
    },
}
ALLOWED = frozenset({
    "lat","lng","position_quality",
    "coordinate_originali","coordinate_sospese_motivo",
    "navigazione_sospesa_motivo",
})


def git_blob_sha(path):
    data=Path(path).read_bytes()
    return hashlib.sha1(b"blob "+str(len(data)).encode()+b"\0"+data).hexdigest()


def validated_map(evidence):
    rows=validate_map(evidence)
    if evidence.get("source_page")!=SOURCE_PAGE or evidence.get("reviewed_on")!=OBSERVATION_DATE:
        raise ValueError("Rome municipality evidence no longer pinned to approved version")
    indexed={x["source_key"]:x for x in rows}
    for sid,c in CASES.items():
        item=indexed[c["map_key"]]
        if item["source_name"].casefold()!=c["name"].casefold():
            raise ValueError("Unreviewed Rome source name for "+sid)
        km=point_distance_km(
            [ORIGINAL_POINT["lat"],ORIGINAL_POINT["lng"]],
            [item["latitude"],item["longitude"]]
        )
        if not MIN_DISTANCE_KM<=km<=20:
            raise ValueError("Official map does not disprove known approximate point: "+sid)
    return indexed


def apply_holds(rows,evidence,*,apply=False):
    if type(apply) is not bool or not isinstance(rows,list) or not 1<=len(rows)<=100000:
        raise ValueError("Invalid explicit Rome coordinate quarantine")
    validated_map(evidence)
    ids=set()
    updated=[]
    changed=[]
    new_coordinate_holds=0
    new_navigation_holds=0
    already_held=0
    for row in rows:
        sid=row.get("slug")
        if not isinstance(sid,str) or not sid or sid in ids:
            raise ValueError("Invalid or duplicate stable ID in source quarantine")
        ids.add(sid)
        current=dict(row)
        case=CASES.get(sid)
        if case:
            if (row.get("citta")!="Roma" or row.get("regione")!="Lazio" or
                    row.get("url_fonte")!=ORIGINAL_URL or
                    row.get("nome")!=case["name"] or
                    row.get("indirizzo")!=case["street"] or
                    row.get("verificato_il") or
                    row.get("date_quality")=="confermata" or
                    row.get("status") in ("archiviato","annullato","attivo")):
                raise ValueError("Rome catalog source identity no longer matches reviewed case: "+sid)
            existing_point=(row.get("lat"),row.get("lng"))
            old=(ORIGINAL_POINT["lat"],ORIGINAL_POINT["lng"])
            is_old=(existing_point==old and row.get("position_quality")!="precisa")
            already=(existing_point==(None,None)
                     and row.get("coordinate_originali")==ORIGINAL_POINT
                     and row.get("coordinate_sospese_motivo")==COORD_HOLD
                     and row.get("navigazione_sospesa_motivo")==NAVIGATION_HOLD
                     and row.get("position_quality")=="sconosciuta")
            if not is_old and not already:
                raise ValueError("Source coordinates changed since Rome municipality review: "+sid)
            if apply and is_old:
                if row.get("coordinate_originali") or row.get("coordinate_sospese_motivo"):
                    raise ValueError("Unreviewed historical quarantine of "+sid)
                if row.get("navigazione_sospesa_motivo") not in (None,"",NAVIGATION_HOLD):
                    raise ValueError("Existing unrelated directions restriction needs review")
                current["lat"]=None
                current["lng"]=None
                current["position_quality"]="sconosciuta"
                current["coordinate_originali"]=dict(ORIGINAL_POINT)
                current["coordinate_sospese_motivo"]=COORD_HOLD
                current["navigazione_sospesa_motivo"]=NAVIGATION_HOLD
                new_coordinate_holds+=1
                if row.get("navigazione_sospesa_motivo")!=NAVIGATION_HOLD:
                    new_navigation_holds+=1
            if already: already_held+=1
            if current!=row:changed.append(sid)
        updated.append(current)
    if not set(CASES).issubset(ids):
        raise ValueError("Source-reviewed Rome market ID vanished from catalog")
    report={
        "schema":1,"enabled":apply,"review_only":not apply,
        "source_reference_date":"2024-12-16",
        "source_reviewed_on":OBSERVATION_DATE,
        "source_map_blob_sha1":SOURCE_GIT_BLOB_SHA,
        "record_count":len(rows),"identities_preserved":True,
        "source_links_replaced":0,"market_openings_confirmed":0,
        "market_calendar_dates_changed":0,"record_ids_added":0,
        "record_ids_removed":0,
        "source_cases":len(CASES),
        "new_coordinates_quarantined":new_coordinate_holds,
        "new_directions_blocked":new_navigation_holds,
        "already_quarantined":already_held,
        "changed_ids":sorted(changed),
    }
    return updated,report


def verify_diff(old,new,report,evidence):
    validated_map(evidence)
    if (not isinstance(old,list) or not isinstance(new,list)
            or len(old)!=len(new)
            or len({x["slug"] for x in old})!=len(old)
            or [x.get("slug") for x in old]!=[x.get("slug") for x in new]
            or report.get("schema")!=1
            or report.get("record_count")!=len(old)
            or report.get("source_cases")!=2
            or report.get("source_map_blob_sha1")!=SOURCE_GIT_BLOB_SHA
            or any(report.get(k)!=0 for k in (
                "source_links_replaced","market_openings_confirmed",
                "market_calendar_dates_changed","record_ids_added","record_ids_removed"))):
        raise ValueError("Unapproved Rome geolocation release report")
    altered=[]
    suspended=0
    routes=0
    for left,right in zip(old,new):
        changes={k for k in left.keys()|right.keys() if left.get(k)!=right.get(k)}
        sid=left["slug"]
        if changes and (sid not in CASES or changes-ALLOWED):
            raise ValueError("Quarantine altered unapproved source market field: "+sid)
        if changes:
            if not (right.get("lat") is None and right.get("lng") is None
                    and right.get("position_quality")=="sconosciuta"
                    and right.get("coordinate_originali")==ORIGINAL_POINT
                    and right.get("coordinate_sospese_motivo")==COORD_HOLD
                    and right.get("navigazione_sospesa_motivo")==NAVIGATION_HOLD):
                raise ValueError("Quarantine did not safely suspend coordinate/route: "+sid)
            if left.get("lat")!=right.get("lat"):
                suspended+=1
            if left.get("navigazione_sospesa_motivo")!=NAVIGATION_HOLD:
                routes+=1
            altered.append(sid)
    if (sorted(altered)!=report.get("changed_ids") or
            suspended!=report.get("new_coordinates_quarantined") or
            routes!=report.get("new_directions_blocked")):
        raise ValueError("Rome field-level proof disagrees with release report")
    return {
        "schema":1,"records_checked":len(old),
        "changed_source_market_ids":sorted(altered),
        "new_coordinate_holds":suspended,"new_navigation_holds":routes,
        "ids_added":0,"ids_deleted":0,"original_source_urls_lost":0,
        "event_verifications_created":0,"release_safe":True,
    }


def verify_static(manifest_path,evidence):
    validated_map(evidence)
    markets=load_existing(manifest_path)
    targets={r["slug"]:r for r in markets if r["slug"] in CASES}
    if set(targets)!=set(CASES):
        raise ValueError("Rome publisher reviewed cases missing from static assets")
    for sid,row in targets.items():
        if (row.get("lat") is not None or row.get("lng") is not None
                or row.get("position_quality")!="sconosciuta"
                or row.get("coordinate_originali")!=ORIGINAL_POINT
                or row.get("coordinate_sospese_motivo")!=COORD_HOLD
                or row.get("navigazione_sospesa_motivo")!=NAVIGATION_HOLD
                or row.get("url_fonte")!=ORIGINAL_URL
                or row.get("verificato_il")
                or row.get("date_quality")=="confermata"):
            raise ValueError("Unsafe Rome destination or source in static details: "+sid)
    public=manifest_path.parent.parent.parent
    manifest=json.loads(manifest_path.read_text("utf-8"))
    index=json.loads((public/manifest["index"]).read_text("utf-8"))
    indexed={str(x[0]):x for x in index["markets"] if x[0] in CASES}
    if set(indexed)!=set(CASES) or any(
            x[6] is not None or x[7] is not None or x[8]!="sconosciuta"
            for x in indexed.values()):
        raise ValueError("Search index exposes suspended Rome coordinates")
    return {
        "schema":1,"market_ids_in_catalog":len(markets),
        "rome_sources_guarded":len(targets),
        "current_coordinate_holds":len(targets),
        "current_navigation_holds":len(targets),
        "original_source_links_preserved":len(targets),
        "new_geocodes_added":0,"market_openings_verified":0,
        "release_safe":True,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--source",type=Path,default=Path("backend/data/roma-municipio-xiii-market-map-reviewed.json"))
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--apply",action="store_true")
    a=p.parse_args()
    source_file=a.source
    if git_blob_sha(source_file)!=SOURCE_GIT_BLOB_SHA:
        raise ValueError("Rome municipal source manifest changed after manual review")
    rows=load_existing(a.manifest)
    updated,report=apply_holds(rows,json.loads(source_file.read_text("utf-8")),apply=a.apply)
    for path in (a.out,a.report):path.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(updated,indent=2,ensure_ascii=False)+"\n","utf-8")
    a.report.write_text(json.dumps(report,indent=2,ensure_ascii=False)+"\n","utf-8")
    print("ROME_COORDINATE_QUARANTINE",json.dumps(report,ensure_ascii=False))


if __name__=="__main__":
    main()
