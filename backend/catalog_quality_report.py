#!/usr/bin/env python3
"""Read-only national market quality audit: actual usability, not raw row count.

Grounded manual examples from 2026-10-12:
- Published Lombardia market of Albizzate appears multiple times with same
  venue/weekday, and approved official hours can be linked to its legacy cards.
- Some scraped "citta" values are event titles such as '"Mercatino delle
  Curiosità"' or merged paragraphs "... in provincia ... Mercato settimanale".
- Historical and unscheduled markets could carry date_quality="prevista"
  even though their future-date list is empty. Export must demote the label.

NEVER deletes, merges, renames, geocodes or confirms records. Potentially
repeated venue/day groups are review leads; not proven duplicates because
multiple independent markets may share a physical location.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path

from lombardia_overlap import weekday_evidence
from merge_catalog import load_existing

VERSION = 1
MAX_EXAMPLES = 35
MAX_MARKETS = 100_000
SUSPICIOUS_TEXT = (
    " in provincia", "mercato settimanale a ", "fiere, mostre e mercati",
    " http://", " https://", " il mercato settimanale di ",
)
VAGUE_ADDRESSES = {
    "centro", "centro storico", "sede da verificare", "da verificare",
    "piazza", "via", "viale", "citta", "zona centro",
    "non disponibile", "sconosciuto", "varie sedi",
}
GENERIC_WEEKLY = re.compile(
    r"^mercat(?:o|ino) settimanale (?:di|a|ad|del|della|in|nel|nella) "
)


def key(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", "".join(
        c for c in text if not unicodedata.combining(c)
    ).casefold()).split())


def suspicious_city(city):
    original = str(city or "").strip()
    folded = key(original)
    # Do not blindly flag legitimate municipalities Piazza Brembana,
    # Piazza al Serchio or Piazzatorre.
    return bool(
        len(original) > 68
        or original.startswith(('"', "“", "”"))
        or original.upper() in {"AL", "BS", "MI", "BG", "BO", "FI", "RM", "NA"}
        or any(term in original.casefold() for term in SUSPICIOUS_TEXT)
        or (
            folded.startswith(("via ", "viale ", "corso "))
            and "-" in original
        )
    )


def count_venue_weekday_groups(records):
    groups = defaultdict(list)
    for row in records:
        label = key(row.get("nome"))
        if not GENERIC_WEEKLY.match(label):
            continue
        region, city = key(row.get("regione")), key(row.get("citta"))
        address = key(row.get("indirizzo"))
        if (not region or not city or not address
                or address in VAGUE_ADDRESSES or len(address) < 8):
            continue
        days = weekday_evidence(row)
        if days is None or len(days) != 1:
            continue
        day = next(iter(days))
        groups[(region, city, address, day)].append(row)
    duplicates = []
    for (_, _, _, weekday), same in groups.items():
        if len(same) < 2:
            continue
        duplicates.append({
            "region": same[0].get("regione",""),
            "city": same[0].get("citta",""),
            "address": same[0].get("indirizzo",""),
            "weekday": int(weekday),
            "records": len(same),
            "source_count": len(set(x.get("url_fonte") or x.get("fonte") or ""
                                    for x in same)),
            "examples": sorted(x["slug"] for x in same)[:6],
        })
    duplicates.sort(key=lambda r: (
        -r["records"],r["region"],r["city"],r["address"],r["weekday"]
    ))
    return duplicates


def analyze(rows, previous=None):
    if not isinstance(rows,list) or not 1 <= len(rows) <= MAX_MARKETS:
        raise ValueError("Invalid or unbounded market catalog")
    if previous is not None and (
        not isinstance(previous,dict) or previous.get("schema") != VERSION
        or previous.get("review_only") is not True
        or previous.get("market_updates_applied",0) != 0
    ):
        raise ValueError("Untrusted prior quality snapshot")
    seen = set()
    region = defaultdict(lambda:Counter())
    source_counts = Counter()
    suspect = []
    missing_future_with_label = []
    count=Counter()
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError("Non-object market record")
        slug=row.get("slug")
        if not isinstance(slug,str) or not slug or slug in seen:
            raise ValueError("Duplicate or missing market identity")
        seen.add(slug)
        reg=str(row.get("regione") or "sconosciuta")
        source=str(row.get("fonte") or "sconosciuta")
        source_counts[source] += 1
        region[reg]["markets"] += 1
        count["total"] += 1
        if not row.get("orario_testo"):
            count["hours_missing"] += 1
            region[reg]["hours_missing"] += 1
        if not row.get("indirizzo"):
            count["address_missing"] += 1
            region[reg]["address_missing"] += 1
        if row.get("lat") is None or row.get("lng") is None:
            count["coordinates_missing"] += 1
            region[reg]["coordinates_missing"] += 1
        if not row.get("url_fonte"):
            count["publisher_url_missing"] += 1
            region[reg]["publisher_url_missing"] += 1
        if not row.get("verificato_il"):
            count["without_individual_verification"] += 1
        if not row.get("date"):
            count["future_dates_missing"] += 1
            region[reg]["future_dates_missing"] += 1
            if row.get("date_quality") in ("prevista","confermata"):
                count["future_date_quality_mismatch"] += 1
                if len(missing_future_with_label) < MAX_EXAMPLES:
                    missing_future_with_label.append({
                        "slug":slug,"region":reg,
                        "name":str(row.get("nome") or "")[:100],
                        "date_quality":row.get("date_quality"),
                    })
        if suspicious_city(row.get("citta")):
            count["suspicious_city"] += 1
            region[reg]["suspicious_city"] += 1
            if len(suspect) < MAX_EXAMPLES:
                suspect.append({
                    "slug":slug,"region":reg,
                    "city":str(row.get("citta") or "")[:145],
                    "name":str(row.get("nome") or "")[:145],
                    "source":source[:100],
                })
    repeats=count_venue_weekday_groups(rows)
    count["review_only_duplicate_groups"] = len(repeats)
    count["review_only_potential_extra_rows"] = sum(r["records"]-1 for r in repeats)
    present = sorted(({
        "region":name,
        **dict(values),
    } for name,values in region.items()), key=lambda x:x["region"])
    top_sources=sorted((
        {"source":name,"records":value}
        for name,value in source_counts.items()
    ), key=lambda x:(-x["records"],x["source"]))[:12]
    prior_counts=(previous or {}).get("metrics",{})
    metrics=dict(sorted(count.items()))
    return {
        "schema": VERSION,
        "review_only": True,
        "market_updates_applied": 0,
        "market_confirmations_created": 0,
        "market_identities_deleted": 0,
        "metrics": metrics,
        "per_region":present,
        "top_sources":top_sources,
        "suspicious_city_examples":suspect,
        "unscheduled_forecast_label_examples":missing_future_with_label,
        "potential_duplicate_weekly_venue_examples":repeats[:MAX_EXAMPLES],
        "potential_duplicates_are_not_confirmed": True,
        "baseline_delta": {name:int(metrics.get(name,0))-int(prior_counts.get(name,0))
                           for name in ("total","hours_missing","address_missing",
                                        "coordinates_missing","future_dates_missing",
                                        "future_date_quality_mismatch",
                                        "suspicious_city","review_only_potential_extra_rows")}
            if previous is not None else {},
        "quality_release_safe": count["future_date_quality_mismatch"] == 0,
    }


def markdown(report):
    m=report["metrics"]
    out=[
        "# Qualità reale del catalogo — audit nazionale automatico",
        "",
        "**Solo analisi, zero modifiche alle schede e zero nuove conferme.**",
        "Un mercato trovato due volte nello stesso luogo e giorno può essere una",
        "duplicazione *oppure* un mercato distinto: nessuna fusione automatica.",
        "",
        f"- Schede: **{m.get('total',0):,}**.",
        f"- Orari mancanti: **{m.get('hours_missing',0):,}**.",
        f"- Indirizzi mancanti: **{m.get('address_missing',0):,}**.",
        f"- Coordinate mancanti: **{m.get('coordinates_missing',0):,}**.",
        f"- Date future mancanti: **{m.get('future_dates_missing',0):,}**.",
        f"- Schede senza data ma erroneamente dichiarate previste/confermate: **{m.get('future_date_quality_mismatch',0):,}**.",
        f"- Località da verificare: **{m.get('suspicious_city',0):,}**.",
        f"- Possibili doppioni (solo mercati settimanali, stesso indirizzo/giorno): **{m.get('review_only_duplicate_groups',0):,}** gruppi, **{m.get('review_only_potential_extra_rows',0):,}** righe in eccesso potenziali.",
        f"- Verifiche umane documentate mancanti: **{m.get('without_individual_verification',0):,}**.",
        "",
        "## Fonte di provenienza (primi editori)",
        "",
        "| Fonte | Schede |","|---|---:|",
    ]
    out.extend(f"| {x['source'].replace('|','/')} | {x['records']:,} |"
               for x in report["top_sources"])
    out.extend(["","## Regioni","",
                "| Regione | Schede | Orari mancanti | Indirizzi mancanti |",
                "|---|---:|---:|---:|"])
    out.extend(
        f"| {r['region']} | {r.get('markets',0):,} | "
        f"{r.get('hours_missing',0):,} | {r.get('address_missing',0):,} |"
        for r in report["per_region"]
    )
    out.extend(["", "## Località da verificare (campione limitato)", ""])
    out.extend(
        "- "+r["region"]+" · "+r["city"]+" · "+r["slug"]
        for r in report["suspicious_city_examples"][:20]
    )
    out.extend(["","## Possibili doppioni (nessuna eliminazione)", ""])
    out.extend(
        f"- {r['region']}, {r['city']} · {r['address']} · "
        f"giorno={r['weekday']} · {r['records']} righe"
        for r in report["potential_duplicate_weekly_venue_examples"][:20]
    )
    out.extend([
        "", "Il report misura completezza e anomalie, NON l'accuratezza",
        "effettiva degli orari, la reale apertura o la qualità legale",
        "delle fonti. Le date future restano previste finché non",
        "confermate con prova dal singolo organizzatore.", "",
    ])
    return "\n".join(out)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--previous",type=Path)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args()
    records=load_existing(args.manifest)
    previous=json.loads(args.previous.read_text("utf-8")) if (
        args.previous and args.previous.is_file()) else None
    result=analyze(records,previous)
    for path in (args.out,args.report): path.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,ensure_ascii=False)+"\n","utf-8")
    args.report.write_text(markdown(result),"utf-8")
    print(json.dumps({
        "markets":result["metrics"]["total"],
        "missing_hours":result["metrics"].get("hours_missing",0),
        "missing_future_dates":result["metrics"].get("future_dates_missing",0),
        "false_forecast_labels":result["metrics"].get("future_date_quality_mismatch",0),
        "suspect_cities":result["metrics"].get("suspicious_city",0),
        "duplicate_review_groups":result["metrics"].get("review_only_duplicate_groups",0),
        "safe_for_release":result["quality_release_safe"]
    },ensure_ascii=False))


if __name__=="__main__":
    main()
