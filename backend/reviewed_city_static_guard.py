#!/usr/bin/env python3
"""Fail closed if a vetted city/navigation hold disappears from final DEV assets.

This checks the *exported* regional JSON and compact search index, not just the
intermediate Python catalog. It verifies the 13 publisher-reviewed cases already
approved by the independent ISTAT/source release guard. No source data is edited.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

NAVIGATION_HOLD = "indirizzo_e_punto_sorgente_non_riconciliati"
COORDINATE_HOLD = "coordinate_sorgente_incompatibili_con_localita_documentata"
PROVENANCE = "ISTAT comuni 2026-02-21; nome fonte e provincia"
INDEX_FIELDS = (
    "slug", "nome", "citta", "regione", "categoria", "tags",
    "lat", "lng", "position_quality", "orario_testo", "date_quality", "date",
)
REVIEWED_CASES = 13
COORDINATE_CASES = 6


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def evidence_digest(evidence: dict) -> str:
    return hashlib.sha256(json.dumps(
        evidence, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def _asset(public: Path, relative: str) -> Path:
    if (not isinstance(relative, str) or not relative.startswith("data/v1/")
            or not relative.endswith(".json") or ".." in relative):
        raise ValueError("Unsafe static asset path")
    path = (public / relative).resolve()
    if not path.is_relative_to(public.resolve()) or not path.is_file():
        raise ValueError("Static asset missing/outside public: " + relative)
    return path


def verify_static(manifest_path: Path, evidence_path: Path, policy_path: Path,
                  daily_report_path: Path) -> dict:
    policy = read_json(policy_path).get("reviewed_source_cities", {})
    if policy.get("enabled") is not True:
        raise ValueError("Previously approved navigation safety gate is disabled")
    evidence = read_json(evidence_path)
    digest = evidence_digest(evidence)
    if digest != policy.get("evidence_sha256"):
        raise ValueError("Publisher review evidence differs from pinned SHA-256")
    cases = evidence.get("cases")
    if (evidence.get("schema") != 1 or not isinstance(cases, list)
            or len(cases) != REVIEWED_CASES):
        raise ValueError("Reviewed source case list changed without approval")
    expected = {}
    for item in cases:
        slug = item.get("slug")
        if not isinstance(slug, str) or not slug or slug in expected:
            raise ValueError("Repeated or invalid approved market ID")
        if (not item.get("target_city") or not item.get("region")
                or not item.get("expected_source_url")
                or not item.get("expected_original_city")):
            raise ValueError("Incomplete publisher location evidence")
        expected[slug] = item

    report = read_json(daily_report_path)
    if (report.get("schema") != 1 or report.get("enabled") is not True
            or report.get("review_only") is not False
            or report.get("ids_preserved") is not True
            or report.get("reviewed_evidence_digest") != digest
            or any(report.get(field) != 0 for field in (
                "individual_events_confirmed", "publisher_links_replaced",
                "opening_dates_added", "market_records_deleted"))):
        raise ValueError("Publisher review release report does not match pinned evidence")

    manifest = read_json(manifest_path)
    if (manifest.get("schema") != 1 or manifest.get("index_schema") != 5
            or not isinstance(manifest.get("total"), int)
            or report.get("records_total") != manifest["total"]):
        raise ValueError("Static manifest and reviewed source counts disagree")
    if manifest.get("layout") == "regional":
        parts = manifest.get("regions")
    elif manifest.get("layout") == "single":
        parts = [{"path": manifest.get("catalog"), "count": manifest["total"]}]
    else:
        raise ValueError("Unsupported static catalog layout")
    if not isinstance(parts, list) or not parts:
        raise ValueError("Empty static catalog")

    public = manifest_path.resolve().parent.parent.parent
    inspected = {}
    total_records = 0
    for part in parts:
        payload = read_json(_asset(public, part.get("path")))
        rows = payload.get("markets")
        if (payload.get("schema") != 1 or not isinstance(rows, list)
                or len(rows) != part.get("count")):
            raise ValueError("Malformed full-detail regional shard")
        total_records += len(rows)
        for row in rows:
            slug = row.get("slug")
            if slug in expected:
                if slug in inspected:
                    raise ValueError("Duplicate reviewed ID in full market details: " + slug)
                inspected[slug] = row
    if total_records != manifest["total"] or set(inspected) != set(expected):
        raise ValueError("Approved source ID is missing from static full details")

    locations_checked = navigation_holds = coordinate_holds = sources_preserved = 0
    for slug, case in expected.items():
        row = inspected[slug]
        if (row.get("citta") != case["target_city"]
                or row.get("regione") != case["region"]
                or row.get("citta_originale") != case["expected_original_city"][:160]
                or row.get("localita_ricostruita_da") != PROVENANCE):
            raise ValueError("Reviewed city/provenance lost in final detail: " + slug)
        locations_checked += 1
        if row.get("navigazione_sospesa_motivo") != NAVIGATION_HOLD:
            raise ValueError("Unsafe directions re-enabled in static detail: " + slug)
        navigation_holds += 1
        original_url = case["expected_source_url"]
        if (row.get("url_fonte") != original_url
                or not any(isinstance(link, dict) and link.get("url") == original_url
                           for link in row.get("fonti", []))):
            raise ValueError("Original publisher URL lost in static detail: " + slug)
        sources_preserved += 1
        if (row.get("verificato_il") or row.get("date_quality") == "confermata"
                or row.get("status") == "attivo"):
            raise ValueError("Reviewed municipality is not proof of market opening: " + slug)
        geo = case.get("coordinate_reference")
        if geo:
            old_point = geo.get("observed_old_point")
            if (row.get("lat") is not None or row.get("lng") is not None
                    or row.get("position_quality") != "sconosciuta"
                    or row.get("coordinate_sospese_motivo") != COORDINATE_HOLD
                    or row.get("coordinate_originali") != {
                        "lat": old_point[0], "lng": old_point[1]
                    }):
                raise ValueError("Unsafe map point returned in static detail: " + slug)
            coordinate_holds += 1
    if coordinate_holds != COORDINATE_CASES:
        raise ValueError("Approved coordinate suspension count changed")

    index = read_json(_asset(public, manifest.get("index")))
    index_rows = index.get("markets")
    if (index.get("schema") != 1 or not isinstance(index_rows, list)
            or len(index_rows) != total_records):
        raise ValueError("Static search index is incomplete")
    indexed = {}
    for values in index_rows:
        if not isinstance(values, list) or len(values) != len(INDEX_FIELDS):
            raise ValueError("Unsafe static search index row")
        sid = values[0]
        if sid in expected:
            if sid in indexed:
                raise ValueError("Duplicate reviewed ID in search index: " + sid)
            indexed[sid] = dict(zip(INDEX_FIELDS, values))
    if set(indexed) != set(expected):
        raise ValueError("A reviewed market is missing from the search index")
    for sid, summary in indexed.items():
        detail = inspected[sid]
        if any(summary[key] != detail.get(key) for key in (
            "citta", "regione", "lat", "lng", "position_quality", "date_quality"
        )):
            raise ValueError("Review safety data differs between index and detail: " + sid)
    return {
        "schema": 1, "evidence_sha256": digest,
        "manifest_records": total_records,
        "reviewed_cities_in_final_details": locations_checked,
        "reviewed_cities_in_search_index": len(indexed),
        "source_urls_preserved": sources_preserved,
        "navigation_routes_still_blocked": navigation_holds,
        "unsafe_coordinates_still_quarantined": coordinate_holds,
        "individual_market_confirmations": 0,
        "release_safe": True,
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, required=True)
    parser.add_argument("--policy", type=Path, required=True)
    parser.add_argument("--daily-report", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = verify_static(args.manifest, args.evidence, args.policy, args.daily_report)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)+"\n", "utf-8")
    print("REVIEWED_CITY_STATIC_GUARD", json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
