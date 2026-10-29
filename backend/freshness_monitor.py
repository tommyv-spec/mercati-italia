#!/usr/bin/env python3
"""Re-runnable freshness monitor for market catalogs and official source metadata.

A successful pipeline run is NOT a confirmation that the markets are current.
No network calls, edits, imports, date generation, or publisher approvals here.
The same inputs/reference date produce the same metrics and QA findings.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path

from export_static import own_source_last_read
from field_evidence import audit as audit_field_evidence
from merge_catalog import load_existing
from quality_scorecard import page_reads as detail_page_reads
from source_freshness import as_day, source_date_evidence, source_url_domain

SCHEMA = 1
MAX_EXAMPLES = 20


def days_since(value, today):
    parsed = as_day(value)
    return None if parsed is None else (today - parsed).days


def analyze(records, today, publisher_evidence=None, max_source_age_days=540, page_reads=None):
    if not isinstance(records, list) or max_source_age_days < 1:
        raise ValueError("Invalid catalog or freshness policy")
    counts = Counter()
    by_origin = Counter()
    by_source = defaultdict(Counter)
    age_states = Counter({"unknown": 0, "recent": 0, "historical": 0, "future": 0})
    unknown_reasons = Counter()
    examples = {"stale_projected": [], "unknown_origin": [],
                "confirmation_without_evidence": [], "future_source_timestamp": []}
    unique = set()
    for row in records:
        if not isinstance(row, dict) or not row.get("slug"):
            raise ValueError("Catalog contains records with no market identity")
        slug = row["slug"]
        if slug in unique:
            raise ValueError("Duplicate source identity in market catalog")
        unique.add(slug)
        row_counts = Counter(total=1)
        evidence = source_date_evidence(row)
        dataset_only = evidence["scope"] == "dataset"
        if dataset_only:
            row_counts["dataset_updated_not_specific_market"] += 1
        elif row.get("aggiornamento_ambito") == "dataset":
            row_counts["dataset_marker_without_source_date_evidence"] += 1

        # Import/read times and an unqualified legacy timestamp say nothing
        # about when the publisher last changed the source content.
        age = days_since(evidence["value"], today)
        if age is None:
            row_counts["source_date_unknown"] += 1
            age_states["unknown"] += 1
            unknown_reasons[evidence["reason"]] += 1
            if row.get("aggiornato_il"):
                row_counts["legacy_update_timestamp_without_source_date"] += 1
            if len(examples["unknown_origin"]) < MAX_EXAMPLES:
                examples["unknown_origin"].append(slug)
        elif age < 0:
            row_counts["future_dated_source"] += 1
            age_states["future"] += 1
            if len(examples["future_source_timestamp"]) < MAX_EXAMPLES:
                examples["future_source_timestamp"].append(slug)
        else:
            row_counts["source_date_from_" + evidence["basis"]] += 1
            age_states["recent" if age <= 30 else "historical"] += 1
            if age <= 30:
                row_counts["source_date_within_30d"] += 1
                if dataset_only:
                    row_counts["recent_dataset_only_update"] += 1
            elif age <= 90:
                row_counts["source_date_31_to_90d"] += 1
            elif age <= 365:
                row_counts["source_date_91_to_365d"] += 1
            elif age <= max_source_age_days:
                row_counts["source_date_366_to_limit"] += 1
            if age > max_source_age_days:
                row_counts["source_date_outside_limit"] += 1

        # A read is the last read of the market's OWN source, the publishers' page
        # re-read cycles included (they do not rewrite fonte_letta_il on every card).
        for field, metric, value in (("importato_il", "import", row.get("importato_il")),
                                     ("fonte_letta_il", "source_read", own_source_last_read(row, page_reads))):
            timestamp_age = days_since(value, today)
            if timestamp_age is None:
                row_counts["without_" + metric + "_timestamp"] += 1
                if row.get(field):
                    row_counts["invalid_" + metric + "_timestamp"] += 1
            else:
                row_counts["with_" + metric + "_timestamp"] += 1
                if timestamp_age < 0:
                    row_counts["future_" + metric + "_timestamp"] += 1
                elif timestamp_age <= 30:
                    row_counts[metric + "_within_30d"] += 1

        if not row.get("verificato_il"):
            row_counts["without_documented_verification"] += 1
        else:
            row_counts["with_documented_verification"] += 1

        if row.get("date_quality") == "confermata" and not row.get("verificato_il"):
            row_counts["confirmation_without_documented_evidence"] += 1
            if len(examples["confirmation_without_evidence"]) < MAX_EXAMPLES:
                examples["confirmation_without_evidence"].append(slug)

        upcoming = [day for day in row.get("date", [])
                    if as_day(day) is not None and as_day(day) >= today]
        if upcoming:
            row_counts["with_any_future_date"] += 1
            if row.get("date_quality") == "prevista":
                row_counts["with_forecast_dates"] += 1
                if age is None or age < 0 or age > max_source_age_days:
                    row_counts["forecast_from_stale_or_unknown_source"] += 1
                    if len(examples["stale_projected"]) < MAX_EXAMPLES:
                        examples["stale_projected"].append(slug)

        domain = source_url_domain(row.get("url_fonte"))
        if domain:
            by_origin[domain] += 1
        elif row.get("url_fonte"):
            row_counts["invalid_primary_source_url"] += 1
        else:
            row_counts["missing_primary_source_url"] += 1
        publisher = str(row.get("fonte") or "fonte sconosciuta")
        by_source[(publisher, domain or "unknown")].update(row_counts)
        counts.update(row_counts)

    source_reports = []
    metadata = publisher_evidence or {}
    if metadata:
        if (not isinstance(metadata, dict) or metadata.get("schema") != 1
                or metadata.get("market_imports") != 0):
            raise ValueError("Untrusted publisher metadata evidence")
        for entry in metadata.get("source_evidence", []):
            source_reports.append({
                "publisher": str(entry.get("publisher") or "")[:100],
                "status": str(entry.get("status") or "unknown")[:40],
                "last_publisher_data_change": entry.get("publisher_data_updated_at"),
                "license_comparison": entry.get("license_comparison"),
                "market_records_verified_by_metadata": 0,
            })
    counts = {name: int(n) for name, n in sorted(counts.items())}
    total = counts.get("total", 0)
    errors = []
    if counts.get("confirmation_without_documented_evidence", 0):
        errors.append("confirmed_events_without_documented_evidence")
    if counts.get("future_dated_source", 0):
        errors.append("source_timestamps_are_in_the_future")
    warnings = []
    if counts.get("without_documented_verification", 0) == total and total:
        warnings.append("no_record_has_documented_verification")
    if counts.get("source_date_unknown", 0):
        warnings.append("source_content_dates_are_unproven")
    if counts.get("forecast_from_stale_or_unknown_source", 0):
        warnings.append("future_predictions_have_stale_or_missing_source_dates")
    if counts.get("source_date_outside_limit", 0):
        warnings.append("source_data_older_than_allowed_forecast_window")
    if any(row["status"] not in ("metadata_checked", "offline")
           for row in source_reports):
        warnings.append("publisher_metadata_unavailable_or_changed")
    field_audit = audit_field_evidence(records, today=today)
    return {
        "schema": SCHEMA,
        "reference_date": today.isoformat(),
        "snapshot_measurement_not_event_verification": True,
        "max_source_age_days": max_source_age_days,
        "measurement_semantics": {
            "source_age": "publisher content date; not read/import time or individual event verification",
            "recent_source": "known content date within 30 days, including dataset-wide dates",
            "historical_source": "known content date more than 30 days old",
            "unknown_source": "content date not supported by a typed date or a reviewed legacy dataset adapter",
            "verification": "recorded verificato_il values; this report does not authenticate their underlying proof",
        },
        "metrics": counts,
        "source_content_age_states": dict(sorted(age_states.items())),
        "source_date_unknown_reasons": dict(sorted(unknown_reasons.items())),
        "source_domains_top": [
            {"domain": name, "count": value}
            for name, value in by_origin.most_common(12)
        ],
        "source_summaries": [
            {"publisher": publisher, "domain": domain,
             "metrics": dict(sorted(values.items()))}
            for (publisher, domain), values in sorted(by_source.items())
        ],
        "field_evidence": {k: v for k, v in field_audit.items() if k != "markets"},
        "publisher_evidence": source_reports,
        "examples": examples,
        "errors": errors,
        "warnings": warnings,
        "safe_for_automatic_quality_promotion": not errors,
        "catalog_was_modified": False,
    }


def markdown(result):
    m = result["metrics"]
    rows = [
        "# Mercati — controllo automatico di attualità",
        "",
        "**La data dell'ultimo script non è una verifica del mercato.**",
        "Il controllo distingue importazione, lettura della fonte, data dichiarata "
        "del contenuto e riscontri dei singoli campi. Le ricorrenze previste rimangono stime.",
        "",
        f"- Data della misura: **{result['reference_date']}**.",
        f"- Schede totali: **{m.get('total', 0):,}**.",
        f"- Fonti misurate (nome e dominio): **{len(result.get('source_summaries', [])):,}**.",
        f"- Importazione registrata entro 30 giorni: **{m.get('import_within_30d', 0):,}**.",
        f"- Lettura della fonte registrata entro 30 giorni: **{m.get('source_read_within_30d', 0):,}**.",
        f"- Fonte datata entro 30 giorni: **{m.get('source_date_within_30d', 0):,}**.",
        f"- Di cui solo aggiornamento dataset, non del singolo mercato: **{m.get('recent_dataset_only_update', 0):,}**.",
        f"- Schede con aggiornamento soltanto del dataset: **{m.get('dataset_updated_not_specific_market', 0):,}**.",
        f"- Fonte datata tra 31 e 365 giorni: **{m.get('source_date_31_to_90d', 0) + m.get('source_date_91_to_365d', 0):,}**.",
        f"- Fonte più vecchia del limite di {result['max_source_age_days']} giorni: **{m.get('source_date_outside_limit', 0):,}**.",
        f"- Schede con età del contenuto della fonte non comprovata: **{m.get('source_date_unknown', 0):,}**.",
        f"- Timestamp legacy che non provano l'età della fonte: **{m.get('legacy_update_timestamp_without_source_date', 0):,}**.",
        f"- Schede con date future previste: **{m.get('with_forecast_dates', 0):,}**.",
        f"- Previsioni basate su fonti troppo vecchie/sconosciute: **{m.get('forecast_from_stale_or_unknown_source', 0):,}**.",
        f"- Date di verifica registrate nel catalogo: **{m.get('with_documented_verification', 0):,}**.",
        "",
        "## Alert",
        "",
        *[f"- BLOCCO: {line}" for line in result["errors"]],
        *[f"- Da correggere: {line}" for line in result["warnings"]],
        "",
        "## Metadati degli enti",
        "",
        "| Ente | Lettura metadati | Aggiornamento dati dichiarato |",
        "|---|---|---|",
    ]
    for item in result["publisher_evidence"]:
        rows.append(
            f"| {item['publisher'].replace('|', '/')} | "
            f"{item['status']} | {item['last_publisher_data_change'] or 'non disponibile'} |"
        )
    rows.extend([
        "", "## Copertura di tutte le fonti del catalogo", "",
        "La data del contenuto riguarda la fonte o l'intero dataset. Non certifica "
        "che ogni mercato sia tuttora attivo. Un'età sconosciuta rimane tale anche "
        "quando l'importazione o la lettura sono recenti.", "",
        "| Fonte | Dominio | Schede | Contenuto entro 30 g | Contenuto oltre 30 g | Età sconosciuta | Lettura entro 30 g |",
        "|---|---|---:|---:|---:|---:|---:|",
    ])
    for item in result.get("source_summaries", []):
        sm = item["metrics"]
        historical = (sm.get("total", 0) - sm.get("source_date_unknown", 0)
                      - sm.get("future_dated_source", 0) - sm.get("source_date_within_30d", 0))
        source_name = item["publisher"].replace("|", "/").replace("\n", " ").replace("\r", " ")
        rows.append(
            f"| {source_name} | {item['domain']} | {sm.get('total', 0)} | "
            f"{sm.get('source_date_within_30d', 0)} | {historical} | "
            f"{sm.get('source_date_unknown', 0)} | {sm.get('source_read_within_30d', 0)} |"
        )
    fm = result.get("field_evidence", {}).get("metrics", {})
    rows.extend([
        "", "## Riscontri sui campi", "",
        "Una lettura recente vale soltanto per i valori e l'identità presenti nella prova. "
        "La tabella non conferma aperture future o coordinate.", "",
        "| Campo | Mancante | Presente senza riscontro | Riscontro e fonte recenti | Riscontro recente, età fonte sconosciuta | Riscontro da aggiornare |",
        "|---|---:|---:|---:|---:|---:|",
    ])
    for field, label in (("indirizzo", "Sede"), ("orario_testo", "Orari"),
                         ("ricorrenza_testo", "Giorni")):
        values = [fm.get(field + ":" + state, 0) for state in (
            "mancante", "senza_riscontro_documentato", "riscontrato_fonte_recente",
            "riscontrato_data_fonte_sconosciuta", "riscontro_da_aggiornare")]
        rows.append(f"| {label} | " + " | ".join(str(n) for n in values) + " |")
    refresh = result.get("source_refresh", {})
    if refresh:
        coverage = refresh.get("source_url_coverage", {})
        rows.extend([
            "", "## Funzionamento del recupero automatico", "",
            f"URL primari distinti nel catalogo: {coverage.get('unique_primary_urls', 0)}. "
            "Le pagine riconosciute vengono lette una volta per tutti i mercati collegabili. "
            "Una fonte senza lettore resta nella coda di copertura: non viene conteggiata come controllata.", "",
            "| Pagina sorgente | Esito del ciclo | Schede collegate | Campi aggiornati |",
            "|---|---|---:|---:|",
        ])
        for page in refresh.get("selected_pages", []):
            rows.append(f"| {page['source_id']} | {page['status']} | "
                        f"{page.get('matched_markets', 0)} | {page.get('changed_fields', 0)} |")
        rows.extend(["", f"Conflitti mantenuti in revisione: {refresh.get('conflicts', 0)}.", ""])
    rows.extend([
        "", "## Limiti del sistema",
        "",
        "- Nessun download recente trasforma da solo una data prevista in confermata.",
        "- Una fonte datata da meno di 30 giorni può contenere appuntamenti non aggiornati.",
        "- Importato il, fonte letta il e fonte aggiornata il sono misure distinte. "
        "Il vecchio campo aggiornato_il, da solo, non prova una data della fonte.",
        "- Le date di verifica già registrate non vengono retroattivamente validate da questo report.",
        "- I dati provenienti da siti terzi richiedono verifica delle condizioni di riuso.",
        "- In caso di anomalie, conservare il catalogo precedente e aprire una revisione.",
        "",
    ])
    return "\n".join(rows)


def add_refresh_evidence(result, decision, manifest_signature):
    """Reuse the candidate's own bounded report in the existing daily report.

    No scheduler changes or extra network requests. A sibling report from
    another catalog/day must never be presented as this catalog's check.
    """
    if (decision.get("new_signature") != manifest_signature or
            decision.get("today") != result["reference_date"]):
        raise ValueError("Automatic source refresh report belongs to another catalog or day")
    refresh = decision.get("publisher_refresh")
    if refresh is None:
        return result
    if (not isinstance(refresh, dict) or refresh.get("release_safe") is not True or
            refresh.get("source_url_coverage", {}).get("markets") != result["metrics"].get("total")):
        raise ValueError("Automatic source coverage lacks its final release proof")
    result["source_refresh"] = refresh
    if any(p.get("status") in {"source_held", "layout_changed", "resume_missing_evidence"}
           for p in refresh.get("selected_pages", [])):
        result["warnings"].append("publisher_refresh_incomplete")
    if refresh.get("conflicts", 0):
        result["warnings"].append("publisher_refresh_conflicting_fields")
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path,
                   default=Path("public/data/v1/manifest.json"))
    p.add_argument("--publisher-evidence", type=Path)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--today", type=date.fromisoformat, default=date.today())
    p.add_argument("--max-source-age-days", type=int, default=540)
    p.add_argument("--fail-on-unsafe", action="store_true")
    args = p.parse_args()
    evidence = json.loads(args.publisher_evidence.read_text("utf-8")) if (
        args.publisher_evidence and args.publisher_evidence.is_file()) else None
    result = analyze(load_existing(args.manifest), args.today, evidence,
                     args.max_source_age_days, detail_page_reads(args.manifest.parent))
    refresh_decision = args.out.parent / "release-decision.json"
    if refresh_decision.is_file():
        add_refresh_evidence(result, json.loads(refresh_decision.read_text("utf-8")),
                             json.loads(args.manifest.read_text("utf-8"))["content_signature"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                        encoding="utf-8")
    args.report.write_text(markdown(result), encoding="utf-8")
    print(json.dumps({
        "records": result["metrics"].get("total", 0),
        "errors": result["errors"], "warnings": result["warnings"],
        "safe_for_automatic_quality_promotion": result["safe_for_automatic_quality_promotion"],
    }, ensure_ascii=False))
    if args.fail_on_unsafe and not result["safe_for_automatic_quality_promotion"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
