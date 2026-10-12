#!/usr/bin/env python3
"""Five source-bound QA repairs: locations, bad map points, Todi winter calendar.

Only the exact original publisher records are eligible. No market ID, source
URL, human verification or confirmed occurrence can ever be created or removed.
The edits are replayable and fail closed when upstream source records drift.
"""
from __future__ import annotations

import hashlib
import json
from datetime import date
from pathlib import Path

from municipality_reconciliation import SOURCE_DATE, trusted_municipalities
from reviewed_city_evidence import point_distance_km, COORD_HOLD, NAVIGATION_HOLD, PROVENANCE

ALLOWED_IDS = {
    "todi-artigianando-mostra-mercato-della-creativita-giardini-oberdan-artigianando",
    "mercato-settimanale-di-centro-storico-di-collalto-in-provincia-mercato-settimana",
    "mercato-settimanale-di-centro-storico-di-collalto-collalto-mercoledi",
    "mercatini-piazza-del-baratto-na",
    "mercatini-stoffaday-na",
}
REVIEW_DAY = "2026-10-12"
VENETO_BOUNDS = {"min_lat": 44.65, "max_lat": 46.85,
                 "min_lng": 10.50, "max_lng": 13.32}
ALLOWED_FIELDS = {
    "citta", "citta_originale", "localita_ricostruita_da",
    "nome", "nome_originale", "indirizzo", "indirizzo_originale",
    "orario_testo", "orario_originale",
    "lat", "lng", "position_quality", "coordinate_originali",
    "coordinate_sospese_motivo", "navigazione_sospesa_motivo",
    "ricorrenza_testo", "ricorrenza_originale", "date", "date_quality",
    "proiezione_regola", "proiezione_fonte", "proiezione_generata_il",
    "stagionalita_fonte",
}
ROLE = ("Source-bound municipality identity, calendar season and geospatial "
        "quarantine only; no event confirmations")


def evidence_digest(evidence):
    return hashlib.sha256(json.dumps(
        evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def validate_evidence(evidence, istat):
    if (not isinstance(evidence, dict) or evidence.get("schema") != 1
            or evidence.get("reviewed_on") != REVIEW_DAY
            or evidence.get("istat_reference") != SOURCE_DATE
            or evidence.get("role") != ROLE
            or not isinstance(evidence.get("cases"), list)
            or {c.get("slug") for c in evidence["cases"]} != ALLOWED_IDS
            or len(evidence["cases"]) != len(ALLOWED_IDS)):
        raise ValueError("Unreviewed or incomplete source-pinned repair manifest")
    registry = trusted_municipalities(istat)
    by_id = {}
    for case in evidence["cases"]:
        slug = case["slug"]
        previous = case.get("expected")
        if (not isinstance(previous, dict)
                or set(previous) != {"name", "city", "province", "address",
                                    "lat", "lng", "region", "source_url"}
                or previous.get("region") not in {"Umbria", "Veneto"}
                or not str(previous.get("source_url","")).startswith("https://")
                or not isinstance(previous.get("lat"), (float,int))
                or not isinstance(previous.get("lng"), (float,int))
                or len(case.get("proof",[])) < 1
                or not all(isinstance(url,str) and url.startswith("https://")
                           for url in case["proof"])):
            raise ValueError("Missing exact previous source evidence: " + slug)
        target = case.get("target_city")
        if target:
            region = previous["region"]
            from catalog_quality_report import key
            matched = registry[region].get(key(target))
            if not matched or matched != (target, case.get("target_province")):
                raise ValueError("New municipality is not in exact ISTAT province")
        else:
            if slug not in {"mercatini-piazza-del-baratto-na", "mercatini-stoffaday-na"}:
                raise ValueError("Only unresolved TrevisoToday rows can lack a municipality")
            if previous["city"] != "NA" or previous["region"] != "Veneto":
                raise ValueError("Wrong unresolved source region/city")
        anchor = case.get("anchor")
        bounds = case.get("region_extent")
        if bool(anchor) == bool(bounds):
            raise ValueError("Each coordinate hold needs exactly one proof type")
        old_point = (previous["lat"], previous["lng"])
        if anchor:
            if (not isinstance(anchor.get("max_km"), (int,float))
                    or not 2 <= anchor["max_km"] <= 18
                    or not str(anchor.get("url","")).startswith("https://")
                    or point_distance_km(
                        old_point, (anchor.get("lat"),anchor.get("lng"))
                    ) <= anchor["max_km"]):
                raise ValueError("Source point not demonstrably outside the documented town")
        else:
            if bounds != VENETO_BOUNDS or (
                bounds["min_lat"] <= old_point[0] <= bounds["max_lat"] and
                bounds["min_lng"] <= old_point[1] <= bounds["max_lng"]
            ):
                raise ValueError("Publisher point is not outside conservative Veneto extent")
        if "season_months" in case and (
                slug != "todi-artigianando-mostra-mercato-della-creativita-giardini-oberdan-artigianando"
                or case["season_months"] != list(range(3,11))
                or case.get("publisher_update") != "2026-08-20"
                or not case.get("target_title")
                or not case.get("target_address")
                or case.get("target_hours") != "09:00–tramonto"):
            raise ValueError("Unproven seasonal forecast override")
        by_id[slug] = case
    if len(by_id) != 5:
        raise ValueError("Repeated source case")
    return by_id


def _set_value(row, field, expected_old, target, provenance_field=None):
    current = row.get(field)
    if current == target:
        if provenance_field and row.get(provenance_field, "") != str(expected_old or "")[:160]:
            raise ValueError("Already changed source lost its original evidence: " + field)
        return False
    if current != expected_old:
        raise ValueError("Source field drifted since review: " + field)
    if provenance_field:
        row[provenance_field] = str(expected_old or "")[:160]
    row[field] = target
    return True


def apply_source_repairs(rows, istat, evidence, *, today:date, apply:bool):
    if apply is not True and apply is not False:
        raise ValueError("Explicit apply flag required")
    if not isinstance(today,date) or not isinstance(rows,list) or not 1 <= len(rows) <= 100_000:
        raise ValueError("Invalid bounded publisher-source catalog")
    cases = validate_evidence(evidence, istat)
    output = []
    seen = set()
    changed_ids = []
    counts = dict(cases=5, cities_corrected=0, titles_corrected=0,
                  addresses_corrected=0, hours_filled=0, unsafe_points_quarantined=0,
                  navigation_held=0, winter_forecast_dates_filtered=0)
    for before in rows:
        slug = before.get("slug")
        if not isinstance(slug,str) or not slug or slug in seen:
            raise ValueError("Duplicate or missing market identity")
        seen.add(slug)
        row = dict(before)
        case = cases.get(slug)
        if case is None:
            output.append(row)
            continue
        ref = case["expected"]
        for field, original in (
            ("url_fonte", ref["source_url"]),
            ("regione", ref["region"]),
            ("provincia", ref["province"]),
        ):
            if before.get(field) != original:
                raise ValueError("Source identity or publisher province drifted: " + slug)
        if (before.get("verificato_il") or
                before.get("status") in {"attivo","confermato","annullato","archiviato"} or
                before.get("date_quality") in {"confermata","riportata"}):
            raise ValueError("Human-verified or reported event cannot be silently changed")
        if apply:
            target = case.get("target_city")
            if target:
                if _set_value(row, "citta", ref["city"], target, "citta_originale"):
                    counts["cities_corrected"] += 1
                if row.get("localita_ricostruita_da") not in (None,"",PROVENANCE):
                    raise ValueError("Municipality provenance was changed")
                row["localita_ricostruita_da"] = PROVENANCE
            elif row.get("citta") != ref["city"]:
                raise ValueError("Unknown city must remain unresolved")
            title = case.get("target_title")
            if title and _set_value(row,"nome",ref["name"],title,"nome_originale"):
                counts["titles_corrected"] += 1
            if not title and row.get("nome") != ref["name"]:
                raise ValueError("Event title drifted since publisher review")
            address = case.get("target_address")
            if address and _set_value(row,"indirizzo",ref["address"],address,"indirizzo_originale"):
                counts["addresses_corrected"] += 1
            if not address and row.get("indirizzo") != ref["address"]:
                raise ValueError("Venue address drifted since review")
            hours = case.get("target_hours")
            if hours and _set_value(row,"orario_testo", "", hours, "orario_originale"):
                counts["hours_filled"] += 1
            oldpoint = {"lat":ref["lat"],"lng":ref["lng"]}
            current = (row.get("lat"),row.get("lng"))
            if (current == (ref["lat"],ref["lng"]) and
                    row.get("position_quality") != "precisa"):
                row["lat"] = row["lng"] = None
                row["position_quality"] = "sconosciuta"
                row["coordinate_originali"] = oldpoint
                row["coordinate_sospese_motivo"] = COORD_HOLD
                counts["unsafe_points_quarantined"] += 1
            elif (current != (None,None)
                    or row.get("coordinate_originali") != oldpoint
                    or row.get("coordinate_sospese_motivo") != COORD_HOLD
                    or row.get("position_quality") != "sconosciuta"):
                raise ValueError("Changed coordinates do not match source-pinned quarantine")
            if row.get("navigazione_sospesa_motivo") not in (None,"",NAVIGATION_HOLD):
                raise ValueError("Unknown pre-existing navigation suspension")
            if row.get("navigazione_sospesa_motivo") != NAVIGATION_HOLD:
                row["navigazione_sospesa_motivo"] = NAVIGATION_HOLD
                counts["navigation_held"] += 1
            if "season_months" in case:
                text = "mensile - terza domenica del mese, da marzo a ottobre"
                if _set_value(row, "ricorrenza_testo",
                              "mensile - terza domenica del mese", text,
                              "ricorrenza_originale"):
                    pass
                all_dates = row.get("date") or []
                if not all(isinstance(day,str) and len(day)>=10 for day in all_dates):
                    raise ValueError("Untrusted predicted calendar dates")
                safe = [day for day in all_dates if date.fromisoformat(day[:10]).month in case["season_months"]]
                counts["winter_forecast_dates_filtered"] += len(all_dates)-len(safe)
                row["date"] = safe
                row["stagionalita_fonte"] = "Editore: da marzo a ottobre; novembre-febbraio sospesi"
                if not safe:
                    row["date_quality"] = "sconosciuta"
                    row["proiezione_regola"] = None
                    row["proiezione_fonte"] = ""
                    row["proiezione_generata_il"] = ""
                else:
                    if row.get("date_quality") != "prevista":
                        raise ValueError("Seasonal dates cannot be upgraded from unknown/confirmed")
                    rule = row.get("proiezione_regola") or {}
                    if (rule.get("kind")!="monthly_nth_weekday" or
                            rule.get("weekday")!=6 or rule.get("ordinal")!=3):
                        raise ValueError("Seasonal calendar source recurrence drifted")
                    row["proiezione_regola"] = dict(rule,active_months=case["season_months"])
        output.append(row)
        if row!=before:
            changed_ids.append(slug)
    if seen.intersection(cases) != set(cases):
        raise ValueError("A source-pinned repair ID vanished from the catalog")
    report = {
        "schema":1,"enabled":apply,"reviewed_on":REVIEW_DAY,
        "evidence_sha256":evidence_digest(evidence),
        "records_total":len(rows),"ids_preserved":True,
        "changed_ids":sorted(changed_ids),"counts":counts,
        "individual_events_confirmed":0,"publisher_urls_replaced":0,
        "new_appointments_added":0,"records_deleted":0,
    }
    return output, report


def verify_diff(before, after, report, evidence):
    expected_ids = {c["slug"] for c in evidence["cases"]}
    if (len(before) != len(after) or
            [r["slug"] for r in before] != [r["slug"] for r in after] or
            report.get("evidence_sha256") != evidence_digest(evidence) or
            report.get("records_total") != len(before)):
        raise ValueError("Source repair destroyed identity or report proof")
    changed = []
    for old,new in zip(before, after):
        fields = {k for k in old.keys()|new.keys() if old.get(k)!=new.get(k)}
        if fields:
            if old["slug"] not in expected_ids or fields - ALLOWED_FIELDS:
                raise ValueError("Unapproved publisher source field changed: "+old["slug"])
            for field in ("regione","provincia","url_fonte","fonti","verificato_il","status"):
                if old.get(field) != new.get(field):
                    raise ValueError("Immutable publisher identity/status modified")
            if old["slug"] != "todi-artigianando-mostra-mercato-della-creativita-giardini-oberdan-artigianando":
                for field in ("date","date_quality","ricorrenza_testo","proiezione_regola"):
                    if old.get(field) != new.get(field):
                        raise ValueError("Other publisher calendar was edited")
            changed.append(old["slug"])
    if sorted(changed) != report.get("changed_ids"):
        raise ValueError("Source report does not match exact field-level diff")
    return {"checked_ids":len(before),"approved_source_cases":5,
            "publisher_urls_replaced":0,"market_ids_deleted":0,
            "changed_market_ids":sorted(changed)}


def verify_static(manifest_path:Path, evidence, policy):
    from merge_catalog import load_existing
    from export_static import small_index
    cases = {c["slug"]:c for c in evidence["cases"]}
    if (policy.get("reviewed_publisher_exceptions",{}).get("enabled") is not True or
            policy["reviewed_publisher_exceptions"].get("evidence_sha256") != evidence_digest(evidence)):
        raise ValueError("Published source review policy fingerprint missing")
    rows = load_existing(manifest_path)
    matches = {r["slug"]:r for r in rows if r["slug"] in cases}
    if set(matches) != set(cases):
        raise ValueError("Reviewed publisher source missing from final regional shards")
    geoholds = routes = cities = 0
    for sid,case in cases.items():
        row = matches[sid]
        ref = case["expected"]
        if (row.get("url_fonte")!=ref["source_url"]
                or row.get("regione")!=ref["region"]
                or row.get("provincia")!=ref["province"]
                or row.get("citta")!=case.get("target_city",ref["city"])
                or row.get("navigazione_sospesa_motivo")!=NAVIGATION_HOLD
                or row.get("lat") is not None or row.get("lng") is not None
                or row.get("position_quality")!="sconosciuta"
                or row.get("coordinate_sospese_motivo")!=COORD_HOLD
                or row.get("coordinate_originali") != {"lat":ref["lat"],"lng":ref["lng"]}
                or row.get("verificato_il") or row.get("date_quality")=="confermata"):
            raise ValueError("Unsafe reviewed publisher source in published details: "+sid)
        geoholds += 1
        routes += 1
        if case.get("target_city"):
            if (row.get("citta_originale")!=str(ref["city"])[:160]
                    or row.get("localita_ricostruita_da")!=PROVENANCE):
                raise ValueError("Publisher town provenance lost in final detail")
            cities += 1
        if case.get("target_title") and (
                row.get("nome")!=case["target_title"] or
                row.get("nome_originale")!=str(ref["name"])[:160]):
            raise ValueError("Publisher title provenance lost")
        if case.get("target_address") and (
                row.get("indirizzo")!=case["target_address"] or
                row.get("indirizzo_originale")!=str(ref["address"])[:160] or
                row.get("orario_testo")!=case["target_hours"]):
            raise ValueError("Publisher Todi venue/time source lost")
        if "season_months" in case:
            if (any(date.fromisoformat(day).month not in case["season_months"]
                    for day in row.get("date",[]))
                    or row.get("ricorrenza_testo") !=
                        "mensile - terza domenica del mese, da marzo a ottobre"
                    or row.get("date_quality") not in
                        ({"prevista"} if row.get("date") else {"sconosciuta"})):
                raise ValueError("Todi winter prediction reappeared in DEV assets")
    manifest=json.loads(manifest_path.read_text("utf-8"))
    index_path=manifest_path.parent.parent.parent / manifest["index"]
    index=json.loads(index_path.read_text("utf-8"))
    from reviewed_city_static_guard import INDEX_FIELDS
    compact={x[0]:dict(zip(INDEX_FIELDS,x)) for x in index["markets"] if x[0] in cases}
    if set(compact) != set(cases):
        raise ValueError("Reviewed source missing from compact search index")
    for sid,row in matches.items():
        indexed=compact[sid]
        if (indexed["citta"]!=row["citta"] or indexed["lat"] is not None or
                indexed["lng"] is not None or indexed["date"]!=(row.get("date") or [])[:16] or
                indexed["date_quality"]!=row.get("date_quality")):
            raise ValueError("Index falsely reintroduced unsafe map point or date: "+sid)
    return {"schema":1,"records_checked":len(rows),
            "reviewed_source_cases":len(cases),
            "new_municipalities_reconciled":cities,
            "navigation_routes_held":routes,
            "false_geographic_points_quarantined":geoholds,
            "published_index_entries_checked":len(compact),
            "all_identities_preserved":True, "release_safe":True}
