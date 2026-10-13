#!/usr/bin/env python3
"""Persist self-measured Autopilot scorecards and bounded trend history on DEV.

Written ONLY after security/browser QA passes. No user/location identifiers or
raw-source rows are stored in the long-term report: only aggregate counts,
quality gates, discoverable sources and prioritized methodology improvements.
"""
from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from collections import Counter
from pathlib import Path
from roma_xiii_2026_venues import EXPECTED as ROMA_XIII_VENUE_IDS, EVIDENCE_FILE as ROMA_VENUE_EVIDENCE, checksum as roma_venue_digest

HISTORY_LIMIT = 400  # more than one year of daily checkpoint scorecards


def summary(decision: dict, roadmap: dict | None, source_candidates: dict | None,
            run_id: str, source_registry: dict | None = None,
            freshness: dict | None = None, rights: dict | None = None,
            lombardia_overlap: dict | None = None,
            bologna_overlap: dict | None = None,
            corciano_overlap: dict | None = None,
            official_enrichment: dict | None = None,
            catalog_quality: dict | None = None,
            visitor_display_audit: dict | None = None,
            municipality_report: dict | None = None,
            reviewed_cities: dict | None = None,
            reviewed_city_static_guard: dict | None = None,
            roma_xiii_static_guard: dict | None = None,
            roma_xiii_2026_report: dict | None = None,
            roma_xiii_2026_final_guard: dict | None = None,
            generic_admission_report: dict | None = None,
            generic_admission_static_guard: dict | None = None) -> dict:
    if decision.get("approved") is not True:
        raise ValueError("Cannot persist a failed candidate as a successful run")
    metric = decision.get("candidate", {})
    registry = source_registry or {}
    intake = registry.get("scan", {})
    classes = Counter(item.get("triage_class", "unknown")
                      for item in registry.get("sources", []))
    freshness_metrics = (freshness or {}).get("metrics", {})
    publisher_checks = (rights or {}).get("source_evidence", [])
    observed_quality = catalog_quality or {}
    municipalities = municipality_report or {}
    city_review = reviewed_cities or {}
    static_guard = reviewed_city_static_guard or {}
    rome_guard = roma_xiii_static_guard or {}
    market_intake = roma_xiii_2026_report or {}
    new_rome_static = roma_xiii_2026_final_guard or {}
    generic = generic_admission_report or {}
    generic_final = generic_admission_static_guard or {}
    generic_added_ids=generic.get("new_market_ids",[])
    if not isinstance(generic_added_ids,list) or len(set(generic_added_ids))!=len(generic_added_ids):
        raise ValueError("Untrusted generic approved source market ID list")
    generic_count=len(generic_added_ids)
    if generic and (
            generic.get("schema")!=1 or generic.get("enabled") is not True
            or generic.get("publication_channel")!="dev-only"
            or not 0<=generic_count<=250
            or generic.get("candidate_market_ids")!=metric.get("records")
            or generic.get("candidate_market_ids")!=generic.get("original_market_ids",0)+generic_count
            or any(generic.get(k)!=0 for k in (
                "record_ids_deleted","old_market_fields_changed",
                "new_market_openings_confirmed","new_market_coordinates_created",
                "new_market_directions_enabled"))):
        raise ValueError("Untrusted source-level generic publisher admission changes")
    if generic_final and (
            not generic or generic_final.get("schema")!=1
            or generic_final.get("release_safe") is not True
            or generic_final.get("market_records_checked")!=metric.get("records")
            or generic_final.get("new_source_venue_ids_verified")!=generic_count
            or generic_final.get("navigation_holds_in_index")!=generic_count
            or generic_final.get("new_precise_coordinates")!=0
            or generic_final.get("original_markets_deleted")!=0
            or generic_final.get("no_individual_market_openings_confirmed") is not True
            or generic_final.get("source_contracts_active")!=generic.get("source_contracts_active")):
        raise ValueError("Missing independent final generic publisher static safety guard")
    if generic and not generic_final:
        raise ValueError("Generic source approved import lacks its final published data proof")
    newly_added = market_intake.get("records_added",0)
    if market_intake:
        expected_source = roma_venue_digest(json.loads(ROMA_VENUE_EVIDENCE.read_text("utf-8")))
        new_ids = market_intake.get("new_market_ids",[])
        already_ids = market_intake.get("already_published_curated_ids",[])
        if (market_intake.get("schema") != 1 or market_intake.get("enabled") is not True
                or market_intake.get("source_manifest_sha256") != expected_source
                or market_intake.get("source_market_identities") != 8
                or market_intake.get("official_preexisting_plateatici") != 2
                or market_intake.get("candidate_venue_records") != 5
                or type(newly_added) is not int or not 0<=newly_added<=5
                or not isinstance(new_ids,list) or not isinstance(already_ids,list)
                or len(new_ids)!=newly_added or len(new_ids)+len(already_ids)!=5
                or not set(new_ids).issubset(ROMA_XIII_VENUE_IDS)
                or not set(already_ids).issubset(ROMA_XIII_VENUE_IDS)
                or set(new_ids).intersection(already_ids)
                or market_intake.get("new_market_count") != newly_added
                or market_intake.get("existing_catalog_records") + newly_added + generic_count != metric.get("records")
                or any(market_intake.get(key)!=0 for key in (
                    "records_removed","existing_records_changed",
                    "new_coordinates_added","new_opening_confirmations",
                    "new_human_verifications"))
                or market_intake.get("held_2026_fogaccia_tuesday_single_stall") is not True
                or market_intake.get("held_urbano_ii_relocation") is not True):
            raise ValueError("Untrusted source-bound Roma XIII market identity count")
    if new_rome_static and (
        not market_intake or new_rome_static.get("schema")!=1
        or new_rome_static.get("release_safe") is not True
        or new_rome_static.get("reviewed_source_digest") !=
            market_intake.get("source_manifest_sha256")
        or new_rome_static.get("market_count_in_final_manifest")!=metric.get("records")
        or new_rome_static.get("reviewed_2026_venue_identifiers")!=5
        or not 0<=new_rome_static.get("forecast_only_markets",-1)<=4
        or new_rome_static.get("route_holds_in_details")!=5
        or new_rome_static.get("route_holds_in_search_index")!=5
        or new_rome_static.get("original_publisher_source_links_retained")!=5
        or new_rome_static.get("geocoordinates_invented")!=0
        or new_rome_static.get("verified_future_markets_created")!=0
        or new_rome_static.get("excluded_fogaccia_tuesday_one_vendor") is not True
        or new_rome_static.get("excluded_pending_pineta_sacchetti_relocation") is not True
    ):
        raise ValueError("Untrusted current-source Roma XIII five-market static guard")
    if market_intake and not new_rome_static:
        raise ValueError("Roma XIII new markets lack a final independent source proof")
    if rome_guard and (
        rome_guard.get("schema") != 1 or
        rome_guard.get("release_safe") is not True or
        rome_guard.get("market_ids_in_catalog") != metric.get("records") or
        rome_guard.get("rome_sources_guarded") != 2 or
        rome_guard.get("current_coordinate_holds") != 2 or
        rome_guard.get("current_navigation_holds") != 2 or
        rome_guard.get("original_source_links_preserved") != 2 or
        rome_guard.get("new_geocodes_added") != 0 or
        rome_guard.get("market_openings_verified") != 0
    ):
        raise ValueError("Untrusted persistent Rome XIII map safety report")
    if static_guard and (
        static_guard.get("schema") != 1 or
        static_guard.get("evidence_sha256") !=
            "4ee7fe7ac44ee2111dde0d50926f9547827256a6c11361eb1d7eeb0fe6de802a" or
        static_guard.get("release_safe") is not True or
        static_guard.get("manifest_records") != metric.get("records") or
        static_guard.get("reviewed_cities_in_final_details") != 16 or
        static_guard.get("reviewed_cities_in_search_index") != 16 or
        static_guard.get("source_urls_preserved") != 16 or
        static_guard.get("navigation_routes_still_blocked") != 16 or
        static_guard.get("unsafe_coordinates_still_quarantined") != 7 or
        static_guard.get("individual_market_confirmations") != 0
    ):
        raise ValueError("Untrusted persistent publisher city safety report")
    if city_review and (
        city_review.get("schema") != 1 or
        city_review.get("reviewed_at") != "2026-10-12" or
        city_review.get("reviewed_evidence_digest") !=
            "4ee7fe7ac44ee2111dde0d50926f9547827256a6c11361eb1d7eeb0fe6de802a" or
        city_review.get("records_total") + newly_added + generic_count != metric.get("records") or
        any(city_review.get(k,0) != 0 for k in (
            "individual_events_confirmed","publisher_links_replaced",
            "opening_dates_added","market_records_deleted")) or
        not 0 <= int(city_review.get("counts",{}).get("city_fixed",0)) <= 16 or
        not 0 <= int(city_review.get("counts",{}).get("coordinates_quarantined",0)) <= 7 or
        not 0 <= int(city_review.get("counts",{}).get("navigation_hold_added",0)) <= 16
    ):
        raise ValueError("Untrusted manually reviewed publisher city quality report")
    if municipalities and (
        municipalities.get("schema") != 1
        or municipalities.get("source_file_sha256") !=
            "83842076860450f7e482daecea6b7a769f5f93d0bf5b0d48802b44896d7a26d5"
        or municipalities.get("istat_reference") != "2026-02-21"
        or municipalities.get("market_confirmations_created") != 0
        or municipalities.get("verified_dates_created") != 0
        or municipalities.get("coordinates_changed") != 0
        or municipalities.get("publisher_sources_replaced") != 0
        or municipalities.get("ids_preserved") is not True
        or int(municipalities.get("counts", {}).get("city_fixed", 0)) > 60
        or int(municipalities.get("counts", {}).get("records_calendar_quarantined", 0)) > 80
    ):
        raise ValueError("Untrusted official ISTAT municipality repair report")
    if observed_quality and (
        observed_quality.get("schema") != 1
        or observed_quality.get("review_only") is not True
        or observed_quality.get("market_updates_applied") != 0
        or observed_quality.get("market_confirmations_created") != 0
        or observed_quality.get("market_identities_deleted") != 0
        or observed_quality.get("quality_release_safe") is not True
    ):
        raise ValueError("Untrusted national catalog quality audit")
    observed_metrics=observed_quality.get("metrics",{})
    display = visitor_display_audit or {}
    visit_metrics = display.get("metrics", {})
    if display and (
        display.get("schema") != 1 or
        display.get("review_only") is not True or
        display.get("display_grouping_only") is not True or
        display.get("market_data_modified") is not False or
        visit_metrics.get("original_records") != metric.get("records") or
        visit_metrics.get("ids_retained") != metric.get("records") or
        any(visit_metrics.get(key) != 0 for key in (
            "market_identities_deleted", "event_confirmations_created",
            "verification_claims_created")) or
        not 0 <= int(visit_metrics.get("suppressed_repeat_buttons_only", -1))
            <= int(visit_metrics.get("original_records_in_reversible_groups", -1)) or
        (
            observed_quality and
            int(visit_metrics.get("malformed_source_city_labels_guarded_in_ui", -1))
            != int(observed_metrics.get("suspicious_city", -2))
        )
    ):
        raise ValueError("Untrusted reversible market display quality audit")
    overlaps = lombardia_overlap or {}
    bologna = bologna_overlap or {}
    corciano = corciano_overlap or {}
    enrichment = official_enrichment or {}
    if enrichment and (
        enrichment.get("schema") != 1 or
        enrichment.get("source_id") != "lombardia-mercap" or
        any(enrichment.get(k) != 0 for k in (
            "record_identity_changes","confirmed_date_changes",
            "individual_market_verifications","coordinates_overwritten",
            "primary_sources_overwritten","old_dataset_dates_overwritten"
        )) or
        int(enrichment.get("existing_market_hours_added",0)) < 0 or
        int(enrichment.get("legacy_records_changed",0)) < 0
    ):
        raise ValueError("Untrusted official enrichment quality claims")
    for item in (overlaps, bologna, corciano):
        if item and (item.get("schema") != 1
                     or item.get("market_confirmations", 0) != 0
                     or item.get("deleted_existing_records", 0) != 0
                     or item.get("accepted", 0) + item.get("quarantined", 0)
                        != item.get("source_total", 0)):
            raise ValueError("Untrusted official overlap report")
    if "records" not in metric or "future_60" not in metric:
        raise ValueError("Incomplete quality report")
    return {
        "run_id": str(run_id),
        "recorded_utc": datetime.now(timezone.utc).isoformat(),
        "quality_approved": True,
        "catalog_changed": bool(decision.get("has_changes")),
        "record_count": int(metric["records"]),
        "predicted_60d": int(metric["future_60"]),
        "predicted_90d": int(metric["future_90"]),
        "index_gzip_bytes": int(metric["indexed_gzip_bytes"]),
        "documented_verification_count": int(metric["verified"]),
        "precise_position_count": int(metric["precise"]),
        "hours_missing": int(metric["missing_hours"]),
        "source_candidates_scored": len((source_candidates or {}).get("candidates", [])),
        "source_scout_failures": len((source_candidates or {}).get("query_failures", {})),
        "source_registry_known": int(intake.get("total_known", 0)),
        "source_registry_new": int(intake.get("delta", {}).get("new", 0)),
        "source_registry_changed": int(intake.get("delta", {}).get("changed", 0)),
        "source_location_candidates": int(classes.get("market_location_candidate", 0)),
        "source_historical_statistics": int(classes.get("aggregated_statistics", 0)),
        "lombardia_source_total": int(overlaps.get("source_total", 0)),
        "lombardia_source_accepted": int(overlaps.get("accepted", 0)),
        "lombardia_source_quarantined": int(overlaps.get("quarantined", 0)),
        "bologna_source_total": int(bologna.get("source_total", 0)),
        "bologna_source_accepted": int(bologna.get("accepted", 0)),
        "bologna_source_quarantined": int(bologna.get("quarantined", 0)),
        "corciano_source_total": int(corciano.get("source_total", 0)),
        "corciano_source_accepted": int(corciano.get("accepted", 0)),
        "corciano_source_quarantined": int(corciano.get("quarantined", 0)),
        "corciano_source_sha256": str(corciano.get("source_csv_sha256") or ""),
        "official_enrichment_enabled": enrichment.get("enabled") is True,
        "official_enrichment_held_rows": int(enrichment.get("source_rows_screened",0)),
        "official_enrichment_exact_matches": int(enrichment.get("exact_matches",0)),
        "official_enrichment_hours_added": int(enrichment.get("existing_market_hours_added",0)),
        "official_enrichment_attributions_added": int(enrichment.get("official_source_attributions_added",0)),
        "municipality_istat_enabled": municipalities.get("enabled") is True,
        "municipality_city_fixed": int(municipalities.get("counts", {}).get("city_fixed", 0)),
        "municipality_titles_repaired": int(municipalities.get("counts", {}).get("contaminated_market_titles_fixed", 0)),
        "municipality_calendars_quarantined": int(municipalities.get("counts", {}).get("records_calendar_quarantined", 0)),
        "municipality_forecast_dates_removed": int(municipalities.get("counts", {}).get("forecast_days_quarantined", 0)),
        "municipality_needs_manual_review": int(municipalities.get("counts", {}).get("needs_manual_municipality_review", 0)),
        "reviewed_city_source_enabled": city_review.get("enabled") is True,
        "reviewed_city_source_corrected": int(city_review.get("counts",{}).get("city_fixed",0)),
        "reviewed_city_source_coordinates_quarantined": int(city_review.get("counts",{}).get("coordinates_quarantined",0)),
        "reviewed_city_source_navigation_blocked": int(city_review.get("counts",{}).get("navigation_hold_added",0)),
        "reviewed_city_source_navigation_held_total": int(static_guard.get("navigation_routes_still_blocked",0)),
        "reviewed_city_source_coordinates_held_total": int(static_guard.get("unsafe_coordinates_still_quarantined",0)),
        "reviewed_city_source_final_details_checked": int(static_guard.get("reviewed_cities_in_final_details",0)),
        "roma_xiii_coordinate_holds_active": int(rome_guard.get("current_coordinate_holds",0)),
        "roma_xiii_navigation_holds_active": int(rome_guard.get("current_navigation_holds",0)),
        "roma_xiii_2026_new_venues_this_run": newly_added,
        "generic_approved_publisher_contracts": int(generic.get("source_contracts_active",0)),
        "generic_approved_publisher_venues_added": generic_count,
        "generic_approved_publisher_forecasts_only": int(generic_final.get("source_weekly_forecasts_only",0)),
        "generic_approved_publisher_routes_suspended": int(generic_final.get("navigation_holds_in_index",0)),
        "roma_xiii_2026_reviewed_venues_active": int(new_rome_static.get("reviewed_2026_venue_identifiers",0)),
        "roma_xiii_2026_forecast_only_venues": int(new_rome_static.get("forecast_only_markets",0)),
        "roma_xiii_2026_navigation_suspended": int(new_rome_static.get("route_holds_in_details",0)),
        "all_reviewed_navigation_holds_active": (
            int(static_guard.get("navigation_routes_still_blocked",0))
            + int(rome_guard.get("current_navigation_holds",0))
        ),
        "all_reviewed_coordinate_holds_active": (
            int(static_guard.get("unsafe_coordinates_still_quarantined",0))
            + int(rome_guard.get("current_coordinate_holds",0))
        ),
        "quality_audit_record_total": int(observed_metrics.get("total",0)),
        "quality_unscheduled_false_labels": int(observed_metrics.get("future_date_quality_mismatch",0)),
        "quality_suspicious_cities": int(observed_metrics.get("suspicious_city",0)),
        "quality_potential_weekly_duplicate_groups": int(observed_metrics.get("review_only_duplicate_groups",0)),
        "quality_possible_duplicate_extra_rows": int(observed_metrics.get("review_only_potential_extra_rows",0)),
        "quality_future_dates_missing": int(observed_metrics.get("future_dates_missing",0)),
        "visitor_duplicate_visit_groups": int(visit_metrics.get("highly_supported_same_source_visit_groups",0)),
        "visitor_duplicate_buttons_avoided": int(visit_metrics.get("suppressed_repeat_buttons_only",0)),
        "visitor_original_market_ids_retained": int(visit_metrics.get("ids_retained",0)),
        "visitor_bad_city_labels_guarded": int(visit_metrics.get("malformed_source_city_labels_guarded_in_ui",0)),
        "source_age_within_30_days": int(freshness_metrics.get("source_date_within_30d", 0)),
        "source_recent_dataset_only": int(freshness_metrics.get("recent_dataset_only_update", 0)),
        "source_dataset_level_records": int(freshness_metrics.get("dataset_updated_not_specific_market", 0)),
        "source_age_over_limit": int(freshness_metrics.get("source_date_outside_limit", 0)),
        "source_date_unknown": int(freshness_metrics.get("source_date_unknown", 0)),
        "forecast_from_stale_sources": int(freshness_metrics.get("forecast_from_stale_or_unknown_source", 0)),
        "publisher_metadata_readable": sum(row.get("status") == "metadata_checked"
                                           for row in publisher_checks),
        "publisher_metadata_checked": len(publisher_checks),
        "freshness_warnings": list((freshness or {}).get("warnings", [])),
        "freshness_errors": list((freshness or {}).get("errors", [])),
        "top_improvement_priorities": [
            item["code"] for item in (roadmap or {}).get("queue", [])[:5]
        ],
        "failed_release_gates": [k for k, v in decision.get("gates", {}).items() if not v],
        "dev_only": True,
        "workflow_url": (
            "https://github.com/tommyv-spec/mercati-italia/actions/runs/" + str(run_id)
        ),
    }


def markdown(latest: dict) -> str:
    return "\n".join([
        "# Mercati Autopilot — ultimo stato automatico",
        "",
        "**Questo report viene aggiornato dagli script, non manualmente.**",
        "",
        f"- Ultimo run: [{latest['run_id']}]({latest['workflow_url']}) — UTC {latest['recorded_utc']}",
        f"- Qualità DEV: {'APPROVATA' if latest['quality_approved'] else 'BLOCCATA'}",
        f"- Nuova versione di dati: {'sì' if latest['catalog_changed'] else 'no (contenuto invariato)'}",
        f"- Schede nel catalogo: **{latest['record_count']:,}**",
        f"- Schede con date previste a +60 giorni: **{latest['predicted_60d']:,}**",
        f"- Schede con date previste a +90 giorni: **{latest['predicted_90d']:,}**",
        f"- Indice nazionale gzip: **{latest['index_gzip_bytes'] / 1024:.1f} KiB**",
        f"- Verifiche documentate: **{latest['documented_verification_count']}**",
        f"- Posizioni precise dichiarate: **{latest['precise_position_count']}**",
        f"- Orari mancanti: **{latest['hours_missing']:,}**",
        f"- Dataset pubblici candidati individuati: **{latest['source_candidates_scored']}** (licenze da verificare)",
        f"- Fonti conservate nello storico: **{latest['source_registry_known']}**; nuove: **{latest['source_registry_new']}**; aggiornate: **{latest['source_registry_changed']}**.",
        f"- Possibili elenchi/sedi: **{latest['source_location_candidates']}**; statistiche storiche aggregate: **{latest['source_historical_statistics']}**.",
        f"- Lombardia MERCap: **{latest['lombardia_source_accepted']}** record non ambigui su **{latest['lombardia_source_total']}**, in revisione **{latest['lombardia_source_quarantined']}**.",
        f"- Bologna: **{latest['bologna_source_accepted']}** record non ambigui su **{latest['bologna_source_total']}**, in revisione **{latest['bologna_source_quarantined']}** (fonte storica; nessuna verifica singolo evento).",
        f"- Corciano: **{latest['corciano_source_accepted']}** record senza conflitti su **{latest['corciano_source_total']}**, in revisione **{latest['corciano_source_quarantined']}**, impronta sorgente **{latest['corciano_source_sha256'] or 'non disponibile'}**.",
        f"- Enrichment ufficiale: {'attivo' if latest['official_enrichment_enabled'] else 'disattivo'}; **{latest['official_enrichment_hours_added']}** orari mancanti recuperati in questo run, **{latest['official_enrichment_attributions_added']}** fonti collegate, **{latest['official_enrichment_exact_matches']}** corrispondenze esatte su **{latest['official_enrichment_held_rows']}** record fonte in revisione.",
        f"- Riconciliazione ISTAT (21 febbraio 2026): {'attiva' if latest['municipality_istat_enabled'] else 'disattiva'}, **{latest['municipality_city_fixed']}** Comuni corretti e **{latest['municipality_titles_repaired']}** titoli ripuliti in questo run; **{latest['municipality_calendars_quarantined']}** calendari sospesi (**{latest['municipality_forecast_dates_removed']}** date previste), **{latest['municipality_needs_manual_review']}** casi ancora ambigui. Nessuna conferma di apertura generata.",
        f"- Revisione manuale di pagine originali e Comuni ISTAT: {'attiva' if latest['reviewed_city_source_enabled'] else 'in attesa'}; **{latest['reviewed_city_source_corrected']}** Comuni sistemati, **{latest['reviewed_city_source_coordinates_quarantined']}** punti geografici incompatibili sospesi, **{latest['reviewed_city_source_navigation_blocked']}** indicazioni stradali disabilitate in questo run. Nessuna verifica di mercato inventata.",
        f"- Protezioni ancora attive nel sito statico DEV: **{latest['reviewed_city_source_navigation_held_total']}** navigazioni sospese, **{latest['reviewed_city_source_coordinates_held_total']}** coordinate in quarantena, **{latest['reviewed_city_source_final_details_checked']}** schede verificate dopo esportazione. Questi sono totali attuali, non modifiche del singolo run.",
        f"- Roma Municipio XIII (mappa pubblicata nel 2024): **{latest['roma_xiii_coordinate_holds_active']}** coordinate ancora sospese e **{latest['roma_xiii_navigation_holds_active']}** percorsi bloccati. Totale protezioni con prova per tutte le fonti revisionate: **{latest['all_reviewed_coordinate_holds_active']}** coordinate e **{latest['all_reviewed_navigation_holds_active']}** navigazioni. Nessuna apertura 2026 confermata dal documento storico.",
        f"- Roma XIII nuove fonti comunali 2025–2026: **{latest['roma_xiii_2026_new_venues_this_run']}** schede aggiunte in questo run, **{latest['roma_xiii_2026_reviewed_venues_active']}** sedi distinte tutelate nel sito, **{latest['roma_xiii_2026_forecast_only_venues']}** con calendari solo previsti, **{latest['roma_xiii_2026_navigation_suspended']}** con indicazioni sospese. Fogaccia martedì (un operatore) e trasferimento Urbano II non importati.",
        f"- Import generico tramite contratti di interi dataset: **{latest['generic_approved_publisher_contracts']}** fonti con licenza e identità approvate, **{latest['generic_approved_publisher_venues_added']}** nuove schede in questo run, **{latest['generic_approved_publisher_forecasts_only']}** calendari solo previsti, **{latest['generic_approved_publisher_routes_suspended']}** indicazioni sospese. Nessuna singola apertura verificata automaticamente.",
        f"- Audit nazionale: **{latest['quality_unscheduled_false_labels']}** date dichiarate previste/confermate ma assenti, **{latest['quality_suspicious_cities']}** località da esaminare e **{latest['quality_potential_weekly_duplicate_groups']}** gruppi settimanali con possibile sovrapposizione (**{latest['quality_possible_duplicate_extra_rows']}** righe candidate, non cancellate).",
        f"- Miglioramento UX reversibile: **{latest['visitor_duplicate_visit_groups']}** gruppi provati dalla stessa fonte, **{latest['visitor_duplicate_buttons_avoided']}** pulsanti ripetuti evitati, **{latest['visitor_bad_city_labels_guarded']}** località anomale non mostrate come Comuni; **{latest['visitor_original_market_ids_retained']}** ID originali preservati.",
        f"- Fonti datate negli ultimi 30 giorni: **{latest['source_age_within_30_days']}**; oltre soglia: **{latest['source_age_over_limit']}**; senza data: **{latest['source_date_unknown']}**.",
        f"- Aggiornamenti del solo dataset (non dei singoli mercati): **{latest['source_dataset_level_records']}**, di cui recenti **{latest['source_recent_dataset_only']}**.",
        f"- Date previste con origine vecchia/sconosciuta: **{latest['forecast_from_stale_sources']}**.",
        f"- Metadati degli enti leggibili: **{latest['publisher_metadata_readable']}/{latest['publisher_metadata_checked']}**.",
        *[f"- ATTENZIONE fonte: {text}" for text in latest["freshness_warnings"]],
        *[f"- BLOCCO qualità: {text}" for text in latest["freshness_errors"]],
        "",
        "## Prossimi miglioramenti calcolati",
        *[f"- {p}" for p in latest["top_improvement_priorities"]],
        "",
        "Il catalogo resta in DEV. Le date previste non sono conferme degli organizzatori.",
        "",
    ])


def save_history(folder: Path, item: dict):
    folder.mkdir(parents=True, exist_ok=True)
    history_file = folder / "history.jsonl"
    previous = []
    if history_file.is_file():
        for line in history_file.read_text("utf-8").splitlines():
            if not line.strip():
                continue
            row = json.loads(line)
            if isinstance(row, dict) and "run_id" in row:
                previous.append(row)
    previous = [row for row in previous if row["run_id"] != item["run_id"]]
    items = (previous + [item])[-HISTORY_LIMIT:]
    history_file.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True)+"\n" for row in items),
        encoding="utf-8"
    )
    (folder / "latest.json").write_text(
        json.dumps(item, ensure_ascii=False, sort_keys=True, indent=2)+"\n", "utf-8"
    )
    (folder / "LATEST.md").write_text(markdown(item), "utf-8")
    return len(items)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--decision", type=Path, required=True)
    p.add_argument("--roadmap", type=Path)
    p.add_argument("--sources", type=Path)
    p.add_argument("--source-registry", type=Path)
    p.add_argument("--freshness", type=Path)
    p.add_argument("--source-evidence", type=Path)
    p.add_argument("--lombardia-overlap", type=Path)
    p.add_argument("--bologna-overlap", type=Path)
    p.add_argument("--corciano-overlap", type=Path)
    p.add_argument("--official-enrichment", type=Path)
    p.add_argument("--catalog-quality", type=Path)
    p.add_argument("--visitor-display-audit", type=Path)
    p.add_argument("--municipality-report", type=Path)
    p.add_argument("--reviewed-cities-report", type=Path)
    p.add_argument("--reviewed-city-static-guard", type=Path)
    p.add_argument("--roma-xiii-static-guard", type=Path)
    p.add_argument("--roma-xiii-2026-report", type=Path)
    p.add_argument("--roma-xiii-2026-final-guard", type=Path)
    p.add_argument("--generic-admission-report", type=Path)
    p.add_argument("--generic-admission-static-guard", type=Path)
    p.add_argument("--run-id", required=True)
    p.add_argument("--out", type=Path, default=Path("reports/automation"))
    args = p.parse_args()
    value = summary(
        json.loads(args.decision.read_text("utf-8")),
        json.loads(args.roadmap.read_text("utf-8")) if args.roadmap and args.roadmap.exists() else None,
        json.loads(args.sources.read_text("utf-8")) if args.sources and args.sources.exists() else None,
        args.run_id,
        json.loads(args.source_registry.read_text("utf-8"))
        if args.source_registry and args.source_registry.is_file() else None,
        json.loads(args.freshness.read_text("utf-8"))
        if args.freshness and args.freshness.is_file() else None,
        json.loads(args.source_evidence.read_text("utf-8"))
        if args.source_evidence and args.source_evidence.is_file() else None,
        json.loads(args.lombardia_overlap.read_text("utf-8"))
        if args.lombardia_overlap and args.lombardia_overlap.is_file() else None,
        json.loads(args.bologna_overlap.read_text("utf-8"))
        if args.bologna_overlap and args.bologna_overlap.is_file() else None,
        json.loads(args.corciano_overlap.read_text("utf-8"))
        if args.corciano_overlap and args.corciano_overlap.is_file() else None,
        json.loads(args.official_enrichment.read_text("utf-8"))
        if args.official_enrichment and args.official_enrichment.is_file() else None,
        json.loads(args.catalog_quality.read_text("utf-8"))
        if args.catalog_quality and args.catalog_quality.is_file() else None,
        json.loads(args.visitor_display_audit.read_text("utf-8"))
        if args.visitor_display_audit and args.visitor_display_audit.is_file() else None,
        json.loads(args.municipality_report.read_text("utf-8"))
        if args.municipality_report and args.municipality_report.is_file() else None,
        json.loads(args.reviewed_cities_report.read_text("utf-8"))
        if args.reviewed_cities_report and args.reviewed_cities_report.is_file() else None,
        json.loads(args.reviewed_city_static_guard.read_text("utf-8"))
        if args.reviewed_city_static_guard and args.reviewed_city_static_guard.is_file() else None,
        json.loads(args.roma_xiii_static_guard.read_text("utf-8"))
        if args.roma_xiii_static_guard and args.roma_xiii_static_guard.is_file() else None,
        json.loads(args.roma_xiii_2026_report.read_text("utf-8"))
        if args.roma_xiii_2026_report and args.roma_xiii_2026_report.is_file() else None,
        json.loads(args.roma_xiii_2026_final_guard.read_text("utf-8"))
        if args.roma_xiii_2026_final_guard and args.roma_xiii_2026_final_guard.is_file() else None,
        json.loads(args.generic_admission_report.read_text("utf-8"))
        if args.generic_admission_report and args.generic_admission_report.is_file() else None,
        json.loads(args.generic_admission_static_guard.read_text("utf-8"))
        if args.generic_admission_static_guard and args.generic_admission_static_guard.is_file() else None,
    )
    count = save_history(args.out, value)
    print(json.dumps({"last_run":value["run_id"],"quality_approved":True,
                      "history_entries":count,"candidates":value["source_candidates_scored"]},
                     ensure_ascii=False))


if __name__=="__main__":
    main()
