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
from datetime import date
from pathlib import Path

from field_evidence import clean_receipts, identity
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


def _venue_weekday_groups(records):
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
    return groups


def count_venue_weekday_groups(records):
    groups = _venue_weekday_groups(records)
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


def _supported_address_revelation(before, after, *, today):
    """Recognize a missing-field recovery, never a changed established venue.

    The source adapters independently authorize and verify their assignments.
    This audit also requires their exact, identity-bound field receipt; an
    unchanged ID alone cannot excuse a new venue/day overlap.
    """
    stable = ("slug", "nome", "citta", "provincia", "regione", "categoria",
              "fonte", "url_fonte", "ricorrenza_testo")
    if (any(before.get(field) != after.get(field) for field in stable)
            or identity(before) != identity(after)
            or weekday_evidence(before) != weekday_evidence(after)):
        return False
    old_address, new_address = key(before.get("indirizzo")), key(after.get("indirizzo"))
    if old_address == new_address:
        return True
    if (old_address and old_address not in VAGUE_ADDRESSES
            or before.get("verificato_il")
            or before.get("position_quality") == "precisa"
            or any("indirizzo" in proof["valori"] for proof in clean_receipts(
                before.get("riscontri_campi"), before, today=today))):
        return False
    return any(proof["valori"].get("indirizzo") == after.get("indirizzo")
               for proof in clean_receipts(after.get("riscontri_campi"), after, today=today))


def _overlap_growth(rows, baseline_rows, previous, *, today):
    """Explain newly observable overlaps without hiding them or deleting IDs."""
    result = {
        "status": "baseline_unavailable", "source_supported_revealed_extra_rows": 0,
        "source_supported_revealed_groups": 0, "examples": [],
    }
    if baseline_rows is None or previous is None:
        return result
    # Reuse the catalog validation, including unique stable IDs and bounds.
    baseline_report = analyze(baseline_rows)
    baseline_metrics = baseline_report["metrics"]
    if any(baseline_metrics.get(field, 0) != previous.get("metrics", {}).get(field, 0)
           for field in ("total", "review_only_potential_extra_rows")):
        result["status"] = "baseline_summary_mismatch"
        return result
    old_by_id = {row["slug"]: row for row in baseline_rows}
    before_groups = _venue_weekday_groups(baseline_rows)
    after_groups = _venue_weekday_groups(rows)
    unexplained = positive_growth = explained = 0
    for group_key, members in sorted(after_groups.items()):
        before_extra = max(0, len(before_groups.get(group_key, [])) - 1)
        increase = max(0, len(members) - 1 - before_extra)
        if not increase:
            continue
        positive_growth += increase
        supported = all(row["slug"] in old_by_id and _supported_address_revelation(
            old_by_id[row["slug"]], row, today=today) for row in members)
        if not supported:
            unexplained += increase
            continue
        explained += increase
        result["source_supported_revealed_groups"] += 1
        if len(result["examples"]) < MAX_EXAMPLES:
            result["examples"].append({
                "region": members[0].get("regione"), "city": members[0].get("citta"),
                "address": members[0].get("indirizzo"), "weekday": group_key[3],
                "revealed_extra_rows": increase,
                "retained_ids": sorted(row["slug"] for row in members)[:6],
            })
    result.update({
        "status": "compared_to_baseline_records",
        "baseline_records": len(baseline_rows),
        "baseline_potential_extra_rows": baseline_metrics["review_only_potential_extra_rows"],
        "positive_group_growth": positive_growth,
        "source_supported_revealed_extra_rows": explained,
        "unexplained_group_growth": unexplained,
    })
    return result


def analyze(rows, previous=None, *, baseline_rows=None, today=None):
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
    overlap_growth = _overlap_growth(
        rows, baseline_rows, previous, today=today or date.today())
    regressions=[]
    if previous is not None:
        for code, margin in (("suspicious_city",5),
                             ("review_only_potential_extra_rows",25)):
            old_value=int(prior_counts.get(code,0))
            new_value=int(metrics.get(code,0))
            # Flag genuinely large increases, not tiny day-to-day noise.
            allowance=max(margin,(old_value+9)//10)
            increase = new_value-old_value
            explained = 0
            if (code == "review_only_potential_extra_rows"
                    and overlap_growth["status"] == "compared_to_baseline_records"):
                explained = overlap_growth["source_supported_revealed_extra_rows"]
                # Disappearing old groups cannot offset an unexplained new
                # group. All raw counts remain in metrics and baseline_delta.
                increase = max(increase - explained,
                               overlap_growth["unexplained_group_growth"])
            if increase>allowance:
                regression = {
                    "code":code,"before":old_value,"after":new_value,
                    "maximum_permitted_increase":allowance,
                }
                if (code == "review_only_potential_extra_rows"
                        and overlap_growth["status"] == "compared_to_baseline_records"):
                    regression.update({"source_supported_revealed_extra_rows": explained,
                                       "unexplained_increase": increase})
                regressions.append(regression)
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
        "overlap_growth_review": overlap_growth,
        "baseline_delta": {name:int(metrics.get(name,0))-int(prior_counts.get(name,0))
                           for name in ("total","hours_missing","address_missing",
                                        "coordinates_missing","future_dates_missing",
                                        "future_date_quality_mismatch",
                                        "suspicious_city","review_only_potential_extra_rows")}
            if previous is not None else {},
        "quality_regressions":regressions,
        "quality_release_safe": (
            count["future_date_quality_mismatch"] == 0 and not regressions
        ),
    }



def analyze_release(rows, previous=None, *, baseline_rows=None, today=None):
    """Compare a proposed release with the ACTUAL published baseline.

    The last compact summary can lag behind an already published DEV catalog.
    Such drift is reported, never treated as new candidate changes. All candidate
    overlap growth remains subject to the same source-receipt checks and limits.
    """
    if previous is None or baseline_rows is None:
        return analyze(rows, previous, baseline_rows=baseline_rows, today=today)
    # Validate the old summary contract even when it is stale. A forged summary
    # must not be able to suppress quality checks.
    if (not isinstance(previous, dict) or previous.get("schema") != VERSION
            or previous.get("review_only") is not True
            or previous.get("market_updates_applied", 0) != 0):
        raise ValueError("Untrusted prior quality snapshot")
    observed_baseline = analyze(baseline_rows)
    report = analyze(rows, observed_baseline,
                     baseline_rows=baseline_rows, today=today)
    old = previous.get("metrics") or {}
    current = observed_baseline["metrics"]
    fields = ("total", "hours_missing", "address_missing",
              "review_only_duplicate_groups",
              "review_only_potential_extra_rows", "suspicious_city",
              "future_dates_missing")
    changes = {key: int(current.get(key, 0)) - int(old.get(key, 0))
               for key in fields}
    report["comparison_anchor"] = "actual_published_DEV_catalog"
    report["previous_scorecard_drift"] = {
        "status": "stale" if any(changes.values()) else "aligned",
        "differences": changes,
        "comparison_is_not_market_mutation": True,
        "new_candidate_regressions_still_block": True,
    }
    return report


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
        f"- Gate qualità: **{'APPROVATO' if report['quality_release_safe'] else 'BLOCCATO'}**.",
        *[f"- REGRESSIONE: {r['code']} {r['before']} → {r['after']} (soglia +{r['maximum_permitted_increase']})"
          for r in report.get('quality_regressions',[])],
    ]
    growth = report.get("overlap_growth_review", {})
    if growth.get("status") == "compared_to_baseline_records":
        out.extend([
            f"- Sovrapposizioni rese visibili dal recupero documentato di indirizzi su ID già presenti: **{growth['source_supported_revealed_extra_rows']:,}** righe potenziali in **{growth['source_supported_revealed_groups']:,}** gruppi; restano tutte nel conteggio da rivedere.",
            f"- Incremento dei gruppi senza questa prova: **{growth['unexplained_group_growth']:,}** righe potenziali; le soglie del gate restano invariate.",
        ])
    out.extend(["", "## Fonte di provenienza (primi editori)", "",
                "| Fonte | Schede |", "|---|---:|"])
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
    parser.add_argument("--baseline-manifest", type=Path,
                        default=Path(__file__).resolve().parents[1] / "public/data/v1/manifest.json",
                        help="Published catalog used to prove retained-ID address recoveries; missing baseline keeps the original strict gate.")
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    args=parser.parse_args()
    records=load_existing(args.manifest)
    previous=json.loads(args.previous.read_text("utf-8")) if (
        args.previous and args.previous.is_file()) else None
    baseline_rows = load_existing(args.baseline_manifest) if (
        previous is not None and args.baseline_manifest.is_file()) else None
    result=analyze_release(records,previous,baseline_rows=baseline_rows)
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
