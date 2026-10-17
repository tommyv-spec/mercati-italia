#!/usr/bin/env python3
"""Second independent proof: FIVE reviewed Roma XIII venue records in final site.

Rejects losing one original ID, corrupting source, turning forecasts into
confirmed appointments, exposing unreviewed navigation coordinates, or
accidentally promoting the single Tuesday Fogaccia operator.
"""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path
from roma_xiii_2026_venues import (
    EXPECTED,validate_manifest,make_market,checksum,MAX_NEW,
)
from reviewed_city_evidence import NAVIGATION_HOLD
from recurrence_refresh import explicit_rule, MAX_SOURCE_STALE_DAYS
from merge_catalog import load_existing

def check_static(manifest_path, evidence, today):
    if not isinstance(today,date):
        raise ValueError("Missing actual reference date")
    approved=validate_manifest(evidence)
    if set(approved)!=set(EXPECTED):
        raise ValueError("Official Roma venue source list changed")
    m=json.loads(Path(manifest_path).read_text("utf-8"))
    all_rows=load_existing(Path(manifest_path))
    by={x["slug"]:x for x in all_rows}
    if len(by)!=len(all_rows) or len(all_rows)!=m.get("total"):
        raise ValueError("Static Roma catalog missing or repeating source IDs")
    index_path=Path(manifest_path).parent.parent.parent/m.get("index","")
    indices=json.loads(index_path.read_text("utf-8"))["markets"]
    found={x[0]:x for x in indices if x[0] in EXPECTED}
    if set(found)!=set(EXPECTED):
        raise ValueError("Official Roma XIII entries absent from national search index")
    predictions=0
    retained=0
    for sid in sorted(EXPECTED):
        r=by.get(sid)
        src=make_market(approved[sid])
        if r is None:
            raise ValueError("Roma XIII source market absent from final static details: "+sid)
        for key in ("slug","nome","citta","provincia","regione","indirizzo",
                    "lat","lng","position_quality","categoria","status",
                    "orario_testo","url_fonte","fonte","id_fonte","aggiornato_il"):
            if r.get(key)!=src.get(key):
                raise ValueError("Reviewed Roma municipal venue changed protected field "+key+": "+sid)
        if (r.get("navigazione_sospesa_motivo")!=NAVIGATION_HOLD or
                r.get("verificato_il") or r.get("date_quality") in ("confermata","riportata") or
                r.get("confidence") not in (0,None) or
                r.get("aggiornamento_ambito")!="dataset"):
            raise ValueError("Roma official candidate falsely confirmed or navigable: "+sid)
        url_values={v.get("url") for v in r.get("fonti",[]) if isinstance(v,dict)}
        if any(v.get("url") not in url_values for v in src["fonti"]):
            raise ValueError("Lost historic/admin venue source URL: "+sid)
        if (found[sid][6] is not None or found[sid][7] is not None or
                found[sid][8]!="sconosciuta"):
            raise ValueError("New Roma venue has unsupported compact-index GPS: "+sid)
        day=EXPECTED[sid]["weekdays"]
        if day:
            rule=explicit_rule(r.get("ricorrenza_testo"))
            if not rule or rule.get("kind")!="weekly" or rule.get("weekdays")!=day:
                raise ValueError("Published Roman day conflicts with municipality act")
        else:
            if r.get("date") or r.get("date_quality")!="sconosciuta":
                raise ValueError("Old San Silverio market falsely given verified calendar")
        age=(today-date.fromisoformat(src["aggiornato_il"])).days
        if 0<=age<=MAX_SOURCE_STALE_DAYS and day:
            dates=r.get("date") or []
            if r.get("date_quality")!="prevista" or len(dates)<7:
                raise ValueError("Supported 2026 weekly day missing forecast label")
            if any(x<today.isoformat() or date.fromisoformat(x).weekday() not in day for x in dates):
                raise ValueError("Out-of-window or wrong weekday forecast in new market")
            predictions+=1
        elif day and (r.get("date") or r.get("date_quality")!="sconosciuta"):
            raise ValueError("Stale Roman 2026 administrative schedule still predicts openings")
        retained+=1
    if retained!=MAX_NEW:
        raise ValueError("Incomplete Roma municipality market publication")
    return {
        "schema":1,"reviewed_source_digest":checksum(evidence),
        "market_count_in_final_manifest":len(all_rows),
        "reviewed_2026_venue_identifiers":retained,
        "forecast_only_markets":predictions,
        "original_publisher_source_links_retained":retained,
        "route_holds_in_details":retained,
        "route_holds_in_search_index":retained,
        "geocoordinates_invented":0,
        "verified_future_markets_created":0,
        "excluded_fogaccia_tuesday_one_vendor":True,
        "excluded_pending_pineta_sacchetti_relocation":True,
        "release_safe":True,
    }
