#!/usr/bin/env python3
"""Read-only, source-pinned comparison of four 2026 Bologna municipal leads.

Never import markets from press releases or infer a weekday from announced hours.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

from catalog_quality_report import key
from merge_catalog import load_existing

SOURCE = ("https://www.comune.bologna.it/novita/comunicati-stampa/"
          "due-nuovi-mercati-sperimentali-navile-e-borgo-panigale-reno")
PUBLISHED = date(2026, 6, 15)
EXPECTED = {
    "bo-municipal-2026-navile-ca-bianca":
        ("Via della Cà Bianca", "planned_not_verified_started", "15:00–19:00", None, ()),
    "bo-municipal-2026-borgo-lorenzetti":
        ("Via Lorenzetti", "planned_not_verified_started", "15:00–19:00", None, ()),
    "bo-municipal-2026-puntoni-carta":
        ("Piazza Puntoni", "previously_reported_active", "09:00–18:00",
         "mercoledì", (3, 4, 5, 6, 9, 10, 11, 12)),
    "bo-municipal-2026-vetulonia-ortofrutta":
        ("Via Vetulonia, Piazzetta", "previously_reported_active", "07:00–14:00",
         ("lunedì", "venerdì"), ()),
}


def validate_evidence(evidence):
    if (not isinstance(evidence, dict)
            or evidence.get("schema") != 1
            or evidence.get("publisher_url") != SOURCE
            and not any(x.get("url") == SOURCE for x in evidence.get("sources", []))
            or evidence.get("reviewed_on") != "2026-10-12"
            or evidence.get("city") != "Bologna"
            or evidence.get("region") != "Emilia-Romagna"
            or evidence.get("reuse_licence_review_required") is not True
            or evidence.get("automatic_import_allowed") is not False
            or evidence.get("market_records_added") != 0
            or evidence.get("events_confirmed") != 0
            or evidence.get("coordinates_created") != 0
            or not isinstance(evidence.get("leads"), list)
            or len(evidence["leads"]) != 4
            or {x.get("lead_id") for x in evidence["leads"]} != set(EXPECTED)):
        raise ValueError("Unreviewed municipal lead evidence or import rights")
    valid_source = any(
        isinstance(source,dict) and source.get("url") == SOURCE
        and source.get("published_on") == PUBLISHED.isoformat()
        and source.get("publisher") == "Comune di Bologna"
        for source in evidence.get("sources", [])
    )
    if not valid_source:
        raise ValueError("Untrusted original municipality publication date")
    for x in evidence["leads"]:
        published_days = x.get("weekday")
        if isinstance(published_days, list):
            published_days = tuple(published_days)
        actual = (x.get("street"), x.get("source_edition_status"),
                  x.get("declared_hours"), published_days,
                  tuple(x.get("active_months", ())))
        if actual != EXPECTED[x["lead_id"]] or x.get("ready_for_catalog") is not False:
            raise ValueError("Municipal street, schedule or publication status changed")
    return evidence["leads"]


def same_street_only(first, other):
    """A shared street may host different markets. Never claim same event."""
    a, b = key(first), key(other)
    return bool(a and b and (a == b or a.startswith(b + " ") or b.startswith(a + " ")))


def audit(rows, evidence, today):
    leads = validate_evidence(evidence)
    if not isinstance(today, date) or today < PUBLISHED:
        raise ValueError("Municipal publication is newer than audit date")
    if not isinstance(rows, list) or not 1 <= len(rows) <= 100000:
        raise ValueError("Invalid full market catalog")
    unique = set()
    bologna = []
    for item in rows:
        if not isinstance(item, dict) or not isinstance(item.get("slug"), str):
            raise ValueError("Missing market identity")
        ident = item["slug"]
        if not ident or ident in unique:
            raise ValueError("Duplicate or missing original market ID")
        unique.add(ident)
        if item.get("regione") == "Emilia-Romagna" and key(item.get("citta")) == "bologna":
            bologna.append(item)
    observations = []
    for lead in leads:
        same = [row for row in bologna
                if same_street_only(lead["street"], row.get("indirizzo"))]
        observations.append({
            "lead_id": lead["lead_id"], "street": lead["street"],
            "municipal_status": lead["source_edition_status"],
            "overlapping_street_market_ids": sorted(row["slug"] for row in same)[:8],
            "overlapping_street_count": len(same),
            "market_opening_individually_verified": False,
            "catalog_publication_approved": False,
        })
    return {
        "schema": 1, "review_only": True, "as_of": today.isoformat(),
        "evidence_source": SOURCE,
        "original_publisher_date": PUBLISHED.isoformat(),
        "catalog_ids_preserved": len(rows),
        "bologna_catalog_entries": len(bologna),
        "pinned_municipal_leads": len(observations),
        "planned_market_starts_not_verified": 2,
        "historically_reported_open_in_june": 2,
        "without_same_street_record": sum(x["overlapping_street_count"] == 0 for x in observations),
        "needs_current_opening_and_rights_review": True,
        "market_rows_imported": 0, "verified_openings_created": 0,
        "calendar_dates_created": 0, "coordinate_points_invented": 0,
        "observations": observations,
    }


def markdown(report):
    lines = [
        "# Bologna 2026 — fonti comunali recenti da riconciliare", "",
        "Rapporto automatico **in sola lettura**. Le notizie non sono "
        "conferme delle prossime aperture.", "",
        "Fonte: " + SOURCE, "",
        "- Schede nazionali conservate: " + str(report["catalog_ids_preserved"]),
        "- Schede con Comune Bologna: " + str(report["bologna_catalog_entries"]),
        "- Lead comunali: " + str(report["pinned_municipal_leads"]),
        "- Senza corrispondenze della stessa via nelle schede Bologna: "
          + str(report["without_same_street_record"]),
        "- Nuove aperture confermate o mercati importati: **0**", "",
        "| Luogo | Stato | Possibili sovrapposizioni per via |",
        "|---|---|---:|",
    ]
    for row in report["observations"]:
        lines.append(f"| {row['street']} | {row['municipal_status']} | "
                     f"{row['overlapping_street_count']} |")
    lines += ["", "Serve una fonte recente sull'effettivo avvio, il giorno, "
               "le edizioni e i diritti di riutilizzo. "
               "Una coincidenza di indirizzo non prova un duplicato.", ""]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, default=Path(
        "backend/data/bologna-municipal-leads-2026.json"))
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--report", type=Path, required=True)
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = parser.parse_args()
    rows = load_existing(args.manifest)
    evidence = json.loads(args.evidence.read_text("utf-8"))
    result = audit(rows, evidence, args.today)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True,
                                   indent=2) + "\n", encoding="utf-8")
    args.report.write_text(markdown(result), encoding="utf-8")
    print("BOLOGNA_2026_SOURCE_LEADS", json.dumps({
        "leads": result["pinned_municipal_leads"],
        "unmatched_streets": result["without_same_street_record"],
        "original_market_ids": result["catalog_ids_preserved"],
        "imports": result["market_rows_imported"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
