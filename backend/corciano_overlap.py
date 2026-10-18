#!/usr/bin/env python3
"""Corciano city/frazione/day overlap QA from manually observed baseline.

The official 2026 municipality CSV has four markets, including Wednesday
Corciano and Friday Ellera. A prior scraped index already has two Wednesday
Corciano entries and one unnamed Friday Corciano entry. Those official
candidates need human-level venue reconciliation before adding extra cards.

Fail-closed: retain legacy records, never fabricate confirmation or merge
by municipality alone. Already introduced source IDs remain stable.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

from lombardia_overlap import weekday_evidence
from merge_catalog import load_existing

SOURCE_PREFIX = "pg-corciano-"
REGION = "Umbria"
CITY = "corciano"


def norm(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(x for x in text if not unicodedata.combining(x)).casefold()
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def locality(name):
    return " ".join(x for x in norm(name).split()
                    if x not in ("mercato", "settimanale", "a", "di", "del", "dei", "della"))


def street_key(text):
    return " ".join(x for x in norm(text).split()
                    if x not in ("via", "viale", "piazza", "piazzale",
                                 "dei", "di", "della", "del", "delle"))


def review(existing, incoming):
    if not isinstance(existing, list) or not isinstance(incoming, list):
        raise ValueError("Expected official source and baseline lists")
    ids = {row["slug"] for row in existing}
    if len(ids) != len(existing):
        raise ValueError("Baseline contains repeated market identity")
    accepted, conflicts, types = [], [], Counter()
    source_hashes = {x.get("source_csv_sha256") for x in incoming
                     if isinstance(x, dict) and x.get("source_csv_sha256")}
    if len(source_hashes) > 1:
        raise ValueError("Corciano source file fingerprint varies between its rows")
    for record in incoming:
        sid = str(record.get("slug") or "")
        if (not sid.startswith(SOURCE_PREFIX) or record.get("regione") != REGION
                or norm(record.get("citta")) != CITY):
            raise ValueError("Unexpected official municipality source identity")
        if sid in ids:
            accepted.append(record)
            types["existing_official_source_id"] += 1
            continue
        day = weekday_evidence(record)
        local = locality(record.get("nome"))
        source_addr = street_key(record.get("indirizzo"))
        ambiguous = []
        reason = None
        for old in existing:
            if (old.get("regione") != REGION or
                    norm(old.get("citta")) != CITY or
                    old.get("slug","").startswith(SOURCE_PREFIX)):
                continue
            old_days = weekday_evidence(old)
            if day is not None and old_days is not None and not (day & old_days):
                continue
            old_local = locality(old.get("nome"))
            old_street = street_key(old.get("indirizzo"))
            same_name = bool(old_local and old_local == local)
            same_address = bool(old_street and source_addr and (
                old_street == source_addr or
                old_street in source_addr or source_addr in old_street
            ))
            generic_unknown_venue = not old_street and old_local == CITY
            if not (same_name or same_address or generic_unknown_venue):
                continue
            ambiguous.append(old)
            if generic_unknown_venue and old_local != local:
                reason = "generic_city_day_without_venue"
            elif same_name:
                reason = "same_market_name_and_weekday"
            else:
                reason = "same_street_and_weekday"
        if ambiguous:
            types["quarantined_" + reason] += 1
            conflicts.append({
                "official_slug": sid,
                "name": str(record.get("nome") or "")[:160],
                "day": sorted(day) if day else [],
                "reason": reason,
                "existing_market_ids": sorted(x["slug"] for x in ambiguous),
                "existing_sources": sorted(set(str(x.get("url_fonte") or "")
                                               for x in ambiguous)),
            })
        else:
            types["safe_distinct_official_market"] += 1
            accepted.append(record)
    if len(conflicts) > 8:
        raise ValueError("Too many Corciano municipality conflicts for unattended review")
    return accepted, {
        "schema": 1,
        "region": REGION,
        "source_prefix": SOURCE_PREFIX,
        "source_total": len(incoming),
        "accepted": len(accepted),
        "quarantined": len(conflicts),
        "counts": dict(sorted(types.items())),
        "quarantined_examples": conflicts,
        "source_csv_sha256": next(iter(source_hashes), None),
        "source_update_scope": "national_catalog_declared_dataset_date",
        "market_confirmations": 0,
        "deleted_existing_records": 0,
        "review_only": True,
    }


def markdown(report):
    rows = [
        "# Corciano — revisione giornaliera fonte municipale",
        "",
        "Il file originale dell'ente è letto ogni ciclo autorizzato.",
        "I mercati con uguale località e giorno, o con scheda cittadina generica",
        "senza indirizzo, restano in revisione: nessuna cancellazione o falsa verifica.",
        "",
        f"- Record della fonte: **{report['source_total']}**.",
        f"- Importabili senza sovrapposizione evidente: **{report['accepted']}**.",
        f"- In revisione: **{report['quarantined']}**.",
        f"- Fingerprint CSV (SHA-256): {report.get('source_csv_sha256') or 'non disponibile'}.",
    ]
    rows.extend(f"- {k}: {v}" for k,v in report["counts"].items())
    for c in report["quarantined_examples"]:
        rows.append(
            f"- {c['name']} · {c['reason']} · già presenti: "
            + ", ".join(c["existing_market_ids"])
        )
    rows.extend(["", "Fonte: https://comune.corciano.pg.it/area_letturaDocumento/29645/pagsistema.html",
                 "Date settimanali previste, non eventi confermati.", ""])
    return "\n".join(rows)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, required=True)
    p.add_argument("--official", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--accepted", type=Path, required=True)
    args = p.parse_args()
    base = load_existing(args.manifest)
    incoming = json.loads(args.official.read_text("utf-8"))
    accepted, report = review(base, incoming)
    for path in (args.out,args.report,args.accepted):
        path.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False)+"\n","utf-8")
    args.report.write_text(markdown(report),"utf-8")
    args.accepted.write_text(json.dumps(accepted, ensure_ascii=False)+"\n","utf-8")
    print(json.dumps({key:report[key] for key in ("source_total","accepted","quarantined","counts")},ensure_ascii=False))


if __name__ == "__main__":
    main()
