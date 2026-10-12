#!/usr/bin/env python3
"""One observed publisher page -> vetted ISTAT municipality -> safe replay.

The publisher pages were inspected manually before the evidence manifest was
written. This module NEVER guesses a city from arbitrary URLs, edits market
opening dates, assigns geocoded points or confirms market events.

For six grossly mismapped places, the previously displayed *approximate*
coordinate is withdrawn, with its source value retained in record details.
The source still needs an independent street/address reconciliation before
navigation can be offered. All identities and primary sources stay intact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import date
from pathlib import Path

from catalog_quality_report import suspicious_city
from municipality_reconciliation import (
    SOURCE_DATE, ISTAT_SHA, trusted_municipalities,
)

REVIEWED_ON = "2026-10-12"
PROVENANCE = "ISTAT comuni 2026-02-21; nome fonte e provincia"
NAVIGATION_HOLD = "indirizzo_e_punto_sorgente_non_riconciliati"
COORD_HOLD = "coordinate_sorgente_incompatibili_con_localita_documentata"
MAX_CASES = 20
MAX_COORDINATE_HOLDS = 8
MAX_KM = 20.0
ALLOWED_CHANGE_FIELDS = frozenset({
    "citta", "citta_originale", "localita_ricostruita_da",
    "navigazione_sospesa_motivo", "lat", "lng", "position_quality",
    "coordinate_originali", "coordinate_sospese_motivo",
})


def manifest_id(evidence):
    return hashlib.sha256(json.dumps(
        evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def point_distance_km(point, anchor):
    a, b = point
    lat2, lon2 = anchor
    if not all(isinstance(x, (float, int)) and not isinstance(x, bool)
               and math.isfinite(x) for x in (a, b, lat2, lon2)):
        raise ValueError("Invalid municipal coordinate reference")
    rad = math.pi / 180.0
    delta_lat = (lat2-a) * rad
    delta_lon = (lon2-b) * rad
    hav = (math.sin(delta_lat/2)**2 +
           math.cos(a*rad)*math.cos(lat2*rad)*math.sin(delta_lon/2)**2)
    return 12742.0 * math.asin(min(1.0, math.sqrt(max(hav, 0.0))))


def validate_evidence(evidence, official):
    if (not isinstance(evidence, dict) or evidence.get("schema") != 1
            or evidence.get("reviewed_on") != REVIEWED_ON
            or evidence.get("istat_ref") != SOURCE_DATE
            or evidence.get("istat_original_xlsx_sha256") != ISTAT_SHA
            or evidence.get("role") !=
               "municipality identity and navigation safety only; zero individual market or calendar confirmation"):
        raise ValueError("Unreviewed city-evidence schema or official source revision")
    rows = evidence.get("cases")
    if not isinstance(rows, list) or not 1 <= len(rows) <= MAX_CASES:
        raise ValueError("Curated municipality evidence exceeds reviewed limits")
    registry = trusted_municipalities(official)
    by_id = {}
    for case in rows:
        if not isinstance(case, dict):
            raise ValueError("Malformed manually examined municipality")
        slug = case.get("slug")
        target = case.get("target_city")
        region = case.get("region")
        if (not isinstance(slug, str) or len(slug) > 130 or not slug or
                slug in by_id or not isinstance(target, str) or
                region not in registry or
                not isinstance(case.get("expected_original_city"), str) or
                not suspicious_city(case["expected_original_city"]) or
                not str(case.get("expected_source_url") or "").startswith("https://") or
                case.get("publisher_page_reviewed_on") != REVIEWED_ON or
                case.get("evidence_type") !=
                    "original publisher page explicitly identifies municipal location; not an event-opening verification"):
            raise ValueError("Unreviewed or ambiguous fixed-source municipality")
        approved = registry[region].get(
            " ".join(__import__("catalog_quality_report").key(target).split())
        )
        if not approved or approved[0] != target or approved[1] != case.get("target_istat_province"):
            raise ValueError("ISTAT region/province municipality identity not proven")
        previous_province = case.get("expected_original_province", "")
        if previous_province and previous_province != approved[1]:
            raise ValueError("Original source province conflicts with ISTAT")
        point = case.get("coordinate_reference")
        if point is not None:
            if (not isinstance(point, dict) or
                    not str(point.get("source_url") or "").startswith("https://") or
                    not isinstance(point.get("observed_old_point"), list) or
                    len(point["observed_old_point"]) != 2 or
                    not 0.2 <= point.get("maximum_acceptable_km", -1) <= MAX_KM):
                raise ValueError("Untrusted geospatial quarantine proof")
            older = point["observed_old_point"]
            documented = (point.get("latitude"), point.get("longitude"))
            distance = point_distance_km(older, documented)
            if distance <= point["maximum_acceptable_km"]:
                raise ValueError("Publisher point is not disproved by reference")
        by_id[slug] = case
    return by_id


def apply_reviewed_cities(rows, official, evidence, *, apply=False):
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100_000:
        raise ValueError("Market catalog missing or too large for reviewed overlay")
    if apply is not True and apply is not False:
        raise ValueError("Explicit boolean application mode required")
    by_id = validate_evidence(evidence, official)
    seen = set()
    altered = []
    touched = []
    counts = {
        "cases": len(by_id), "city_fixed": 0, "coordinates_quarantined": 0,
        "navigation_hold_added": 0, "unchanged_already_reviewed": 0,
        "verified_market_claims_added": 0, "source_dates_modified": 0,
        "deleted_market_ids": 0,
    }
    for original in rows:
        slug = original.get("slug")
        if not isinstance(slug, str) or not slug or slug in seen:
            raise ValueError("Repeated/invalid market ID in municipal review")
        seen.add(slug)
        case = by_id.get(slug)
        changed = dict(original)
        if case is not None:
            if (original.get("regione") != case["region"]
                    or original.get("url_fonte") != case["expected_source_url"]
                    or str(original.get("provincia") or "") != case["expected_original_province"]):
                raise ValueError("Published source identity changed since manual review: "+slug)
            old_city = original.get("citta")
            previous = case["expected_original_city"]
            new_city = case["target_city"]
            first_application = old_city == previous
            already_reviewed = (
                old_city == new_city and
                original.get("citta_originale") == previous and
                original.get("localita_ricostruita_da") == PROVENANCE
            )
            if not first_application and not already_reviewed:
                raise ValueError("Unreviewed source municipality change: "+slug)
            if original.get("verificato_il") or original.get("date_quality") == "confermata":
                raise ValueError("Cannot alter human-verified/confirmed market: "+slug)
            if apply and first_application:
                changed["citta"] = new_city
                changed["citta_originale"] = previous[:160]
                changed["localita_ricostruita_da"] = PROVENANCE
                counts["city_fixed"] += 1
            if apply and changed.get("navigazione_sospesa_motivo") != NAVIGATION_HOLD:
                changed["navigazione_sospesa_motivo"] = NAVIGATION_HOLD
                counts["navigation_hold_added"] += 1
            geo = case.get("coordinate_reference")
            if geo and apply:
                original_point = (original.get("lat"), original.get("lng"))
                prior_point = geo["observed_old_point"]
                same_old = all(
                    isinstance(original_point[i], (int,float)) and
                    abs(original_point[i] - prior_point[i]) < 0.00001
                    for i in (0,1)
                )
                previously_quarantined = (
                    original_point == (None,None) and
                    original.get("coordinate_sospese_motivo") == COORD_HOLD and
                    original.get("coordinate_originali") ==
                        {"lat": prior_point[0], "lng": prior_point[1]}
                )
                if same_old:
                    if original.get("position_quality") == "precisa":
                        raise ValueError("Exact verified point cannot be quarantined by city centroid")
                    changed["lat"], changed["lng"] = None, None
                    changed["position_quality"] = "sconosciuta"
                    changed["coordinate_originali"] = {
                        "lat": original_point[0], "lng": original_point[1]
                    }
                    changed["coordinate_sospese_motivo"] = COORD_HOLD
                    counts["coordinates_quarantined"] += 1
                elif not previously_quarantined:
                    raise ValueError("Map coordinates changed after documented review: "+slug)
            if apply and not first_application and changed == original:
                counts["unchanged_already_reviewed"] += 1
            if changed != original:
                touched.append(slug)
        altered.append(changed)
    if seen.intersection(by_id) != set(by_id):
        raise ValueError("Manually reviewed ID no longer present in catalog")
    if (counts["city_fixed"] > MAX_CASES or
            counts["coordinates_quarantined"] > MAX_COORDINATE_HOLDS):
        raise ValueError("Unexpected overlarge municipality or coordinate edit")
    report = {
        "schema":1, "istat_reference": SOURCE_DATE,
        "reviewed_evidence_digest": manifest_id(evidence),
        "reviewed_at":REVIEWED_ON,
        "review_only": not apply,
        "records_total":len(rows), "ids_preserved": True,
        "counts":counts, "changed_ids":sorted(touched),
        "individual_events_confirmed":0,
        "publisher_links_replaced":0,
        "opening_dates_added":0,
        "market_records_deleted":0,
    }
    return altered, report


def verify_reviewed_diff(before, after, report, official, evidence):
    by_id = validate_evidence(evidence, official)
    if (not isinstance(before,list) or not isinstance(after,list) or
            len(before)!=len(after) or
            [x.get("slug") for x in before] != [x.get("slug") for x in after] or
            report.get("schema") != 1 or
            report.get("reviewed_evidence_digest") != manifest_id(evidence) or
            report.get("records_total") != len(before) or
            report.get("individual_events_confirmed") != 0 or
            report.get("publisher_links_replaced") != 0 or
            report.get("opening_dates_added") != 0 or
            report.get("market_records_deleted") != 0):
        raise ValueError("Untrusted manually reviewed municipality release")
    changed, city_updates, geo_suspensions, blocked_navigation = [], 0, 0, 0
    for left,right in zip(before,after):
        differences={k for k in left.keys()|right.keys() if left.get(k)!=right.get(k)}
        if not differences: continue
        sid=left["slug"]
        if sid not in by_id or differences-ALLOWED_CHANGE_FIELDS:
            raise ValueError("Unapproved market field modified: "+sid)
        case=by_id[sid]
        if left.get("verificato_il") or left.get("date_quality") == "confermata":
            raise ValueError("Verified or confirmed market changed without review")
        if left["citta"] != right["citta"]:
            if (right["citta"] != case["target_city"] or
                    right.get("citta_originale") != case["expected_original_city"][:160] or
                    right.get("localita_ricostruita_da") != PROVENANCE):
                raise ValueError("Changed municipality lacks source/ISTAT evidence")
            city_updates += 1
        if left.get("navigazione_sospesa_motivo") != right.get("navigazione_sospesa_motivo"):
            if right.get("navigazione_sospesa_motivo") != NAVIGATION_HOLD:
                raise ValueError("Unsafe route navigation review")
            blocked_navigation += 1
        if any(k in differences for k in ("lat","lng","position_quality",
                                            "coordinate_originali","coordinate_sospese_motivo")):
            if (not case.get("coordinate_reference")
                    or (right.get("lat"),right.get("lng"))!=(None,None)
                    or right.get("position_quality")!="sconosciuta"
                    or right.get("coordinate_sospese_motivo")!=COORD_HOLD
                    or right.get("coordinate_originali") != {
                        "lat":left.get("lat"),"lng":left.get("lng")}):
                raise ValueError("Coordinate quarantine lacks exact manual evidence")
            geo_suspensions += 1
        changed.append(sid)
    expected = report.get("counts") or {}
    if (set(changed) != set(report.get("changed_ids",[]))
            or city_updates != expected.get("city_fixed",0)
            or geo_suspensions != expected.get("coordinates_quarantined",0)
            or blocked_navigation != expected.get("navigation_hold_added",0)):
        raise ValueError("Manual evidence report does not match per-market changes")
    return {
        "schema":1, "records_checked":len(before), "identities_deleted":0,
        "cities_corrected":city_updates, "unsafe_points_suppressed":geo_suspensions,
        "navigation_routes_paused":blocked_navigation, "market_verifications_created":0,
        "proof_digest":manifest_id(evidence),
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--istat",type=Path,default=Path("backend/data/istat-comuni-2026.json"))
    p.add_argument("--evidence",type=Path,default=Path("backend/data/reviewed-city-evidence-2026-10-12.json"))
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--verify",type=Path,required=True)
    p.add_argument("--apply",action="store_true")
    args=p.parse_args()
    from merge_catalog import load_existing
    old=load_existing(args.manifest)
    official=json.loads(args.istat.read_text("utf-8"))
    evidence=json.loads(args.evidence.read_text("utf-8"))
    new,report=apply_reviewed_cities(old,official,evidence,apply=args.apply)
    verified=verify_reviewed_diff(old,new,report,official,evidence)
    for path,content in (
        (args.out,new),(args.report,report),(args.verify,verified)
    ):
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(json.dumps(content,ensure_ascii=False,indent=2)+"\n","utf-8")
    print("MANUAL_CITY_SOURCE_REVIEW",json.dumps(report["counts"],ensure_ascii=False))


if __name__=="__main__":
    main()
