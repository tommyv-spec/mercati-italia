#!/usr/bin/env python3
"""Strict before/after checker for source-bound ISTAT municipality cleanup.

No network, fuzzy geocoding, hidden edits or implicit verification. Only
approved display-town/title/projection-quarantine fields may change.
This checker is used by Autopilot *and* can replay GitHub CI checkpoints.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from municipality_reconciliation import (
    ISTAT_SHA, SOURCE_DATE, PROJECTION_WARNING,
    source_city_cross_contamination,
)
from province_reconciliation import (
    KEY as PROVINCE_PROOF, MAX_TOTAL_CHANGES, REGISTRY_SHA256,
    valid_proof as valid_province_proof, verify_supplement,
)

MAX_CHANGED = MAX_TOTAL_CHANGES
MAX_CITY_FIXES = 60
MAX_QUARANTINES = 80
ALLOWED = frozenset({
    "citta", "citta_originale", "localita_ricostruita_da",
    "nome", "nome_originale", "date", "date_quality",
    "ricorrenza_testo", "ricorrenza_originale", "proiezione_regola",
    "proiezione_fonte", "proiezione_generata_il",
    "calendario_sospeso_motivo",
    "provincia", PROVINCE_PROOF,
})


def check(original, revised, report):
    if (not isinstance(original, list) or not isinstance(revised, list)
            or not isinstance(report, dict)
            or report.get("schema") != 1
            or report.get("istat_reference") != SOURCE_DATE
            or report.get("source_file_sha256") != ISTAT_SHA
            or report.get("records_total") != len(original)
            or report.get("records_total") != len(revised)
            or report.get("ids_preserved") is not True
            or report.get("market_confirmations_created") != 0
            or report.get("verified_dates_created") != 0
            or report.get("coordinates_changed") != 0
            or report.get("publisher_sources_replaced") != 0):
        raise ValueError("Untrusted official municipality release report")
    before_ids = [x["slug"] for x in original]
    after_ids = [x["slug"] for x in revised]
    if before_ids != after_ids or len(set(before_ids)) != len(before_ids):
        raise ValueError("Municipality release changed or duplicated a market ID")
    approved = {
        x["slug"]: x for x in report.get("examples", [])
        if x.get("suggested_city") and x.get("changed")
    }
    touched = 0
    cities = 0
    provinces = 0
    names = 0
    calendar_quarantined = 0
    calendar_days_cleared = 0
    samples = []
    for before, after in zip(original, revised):
        changes = {key for key in before.keys() | after.keys()
                   if before.get(key) != after.get(key)}
        if not changes:
            continue
        slug = before["slug"]
        touched += 1
        if changes - ALLOWED:
            raise ValueError(f"Unapproved municipality data field modification: {slug}: {sorted(changes-ALLOWED)}")
        if before.get("verificato_il") or before.get("date_quality") == "confermata":
            raise ValueError("Verified or confirmed market must never be rewritten: " + slug)
        if "provincia" in changes:
            if (changes != {"provincia", PROVINCE_PROOF}
                    or not valid_province_proof(after.get(PROVINCE_PROOF), after)):
                raise ValueError("Unapproved municipality province proof or unrelated field modification: " + slug)
            provinces += 1
        elif PROVINCE_PROOF in changes:
            raise ValueError("Province provenance changed without administrative correction: " + slug)
        city_changed = before.get("citta") != after.get("citta")
        if city_changed:
            case = approved.get(slug)
            if not case or case.get("suggested_city") != after.get("citta"):
                raise ValueError("Municipality city change lacks approved ISTAT example: " + slug)
            if (after.get("citta_originale") != str(before.get("citta") or "")[:160]
                    or after.get("localita_ricostruita_da") !=
                        "ISTAT comuni 2026-02-21; nome fonte e provincia"):
                raise ValueError("Official ISTAT city correction provenance missing: " + slug)
            cities += 1
        elif changes.intersection({"citta_originale","localita_ricostruita_da"}):
            raise ValueError("City provenance changed without municipality change: " + slug)
        if "nome" in changes:
            if (not city_changed
                    or after.get("nome") != "Mercato settimanale di " + after["citta"]
                    or after.get("nome_originale") != str(before.get("nome") or "")[:160]):
                raise ValueError("Scraper title cleaned without independently justified municipality: " + slug)
            names += 1
        has_schedule_edit = bool(changes.intersection({
            "date", "date_quality", "ricorrenza_testo", "ricorrenza_originale",
            "proiezione_regola", "proiezione_fonte", "proiezione_generata_il",
            "calendario_sospeso_motivo",
        }))
        if has_schedule_edit:
            if not source_city_cross_contamination(
                before.get("citta_originale") or before.get("citta")
            ):
                raise ValueError("Source calendar cleared without cross-city evidence: " + slug)
            if (after.get("date") != []
                    or after.get("date_quality") != "sconosciuta"
                    or after.get("ricorrenza_testo") != PROJECTION_WARNING
                    or after.get("calendario_sospeso_motivo") !=
                       "testo_sorgente_localita_concatenate"):
                raise ValueError("Cross-city calendar quarantine is incomplete: " + slug)
            if before.get("date"):
                calendar_quarantined += 1
                calendar_days_cleared += len(before["date"])
        if len(samples) < 30:
            samples.append({
                "slug":slug, "old_city":str(before.get("citta") or "")[:110],
                "new_city":str(after.get("citta") or "")[:110],
                "changes":sorted(changes),
            })
    counts = report.get("counts") or {}
    for label, observed in (
        ("city_fixed", cities),
        ("province_fixed", provinces),
        ("contaminated_market_titles_fixed", names),
        ("records_calendar_quarantined", calendar_quarantined),
        ("forecast_days_quarantined", calendar_days_cleared),
    ):
        if counts.get(label, 0) != observed:
            raise ValueError(f"Municipality correction counter mismatch {label}: {observed} vs {counts.get(label)}")
    province_report = report.get("province_corrections")
    if province_report is not None:
        actual_provinces = verify_supplement(
            original, revised, province_report, apply=report.get("review_only") is False)
        if (actual_provinces != provinces
                or counts.get("province_candidates", 0) != province_report["eligible"]
                or counts.get("province_pending", 0) != province_report["pending"]
                or counts.get("province_protected", 0) != province_report["protected"]):
            raise ValueError("Administrative province correction counter mismatch")
    elif provinces:
        raise ValueError("Province correction lacks complete pinned registry proof")
    if (touched > MAX_CHANGED or cities > MAX_CITY_FIXES
            or calendar_quarantined > MAX_QUARANTINES):
        raise ValueError("Municipality cleanup exceeds bounded daily modification budget")
    return {
        "schema":1, "checked_ids":len(original), "market_identities_deleted":0,
        "changes":touched,"city_replacements":cities,
        "province_replacements":provinces,
        "province_pending":counts.get("province_pending", 0),
        "province_protected":counts.get("province_protected", 0),
        "contaminated_titles_repaired":names,
        "calendar_sources_quarantined":calendar_quarantined,
        "forecast_dates_removed":calendar_days_cleared,
        "publisher_urls_or_human_verifications_changed":0,
        "source_istat_sha":ISTAT_SHA,
        "samples":samples,
    }


def verify_exported(original, municipal_rows, report, exported):
    """Tether final province values and proofs to the checked municipality phase.

    Later publisher phases may add their independently verified source facts.
    They cannot silently replace a province or drop its administrative proof.
    New publisher-admitted IDs are checked by their separate admission guards.
    """
    phase = check(original, municipal_rows, report)
    if not isinstance(exported, list) or len(exported) > 100_000:
        raise ValueError("Unbounded final catalog for municipality province guard")
    by_id = {row["slug"]: row for row in exported}
    if len(by_id) != len(exported):
        raise ValueError("Duplicate final market identity in municipality guard")
    expected_proofs = {row["slug"]: row for row in municipal_rows if PROVINCE_PROOF in row}
    final_proofs = {row["slug"]: row for row in exported if PROVINCE_PROOF in row}
    if set(expected_proofs) != set(final_proofs):
        raise ValueError("Final ISTAT province proof set changed or a corrected ID disappeared")
    checked = 0
    for row in municipal_rows:
        final = by_id.get(row["slug"])
        if final is not None:
            if final.get("provincia") != row.get("provincia"):
                raise ValueError("Final province differs from checked municipality phase: " + row["slug"])
            checked += 1
        if row["slug"] in expected_proofs:
            if (not valid_province_proof(row[PROVINCE_PROOF], row)
                    or not valid_province_proof(final.get(PROVINCE_PROOF), final)
                    or final[PROVINCE_PROOF] != row[PROVINCE_PROOF]):
                raise ValueError("Final administrative province proof lost or altered: " + row["slug"])
    return {
        "schema": 1, "release_safe": True, "checked_existing_provinces": checked,
        "province_corrections_this_run": phase["province_replacements"],
        "administrative_proofs_preserved": len(expected_proofs),
        "source_registry_sha256": REGISTRY_SHA256,
        "source_receipts_rewritten": 0, "market_openings_confirmed": 0,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--before",required=True,type=Path)
    p.add_argument("--after",required=True,type=Path)
    p.add_argument("--report",required=True,type=Path)
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args()
    a=json.loads(args.before.read_text("utf-8"))
    b=json.loads(args.after.read_text("utf-8"))
    r=json.loads(args.report.read_text("utf-8"))
    result=check(a,b,r)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n","utf-8")
    print("MUNICIPALITY_RELEASE_GATE",json.dumps({
        k:result[k] for k in ("checked_ids","city_replacements","calendar_sources_quarantined",
                            "forecast_dates_removed","publisher_urls_or_human_verifications_changed")
    },ensure_ascii=False))


if __name__=="__main__":
    main()
