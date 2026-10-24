#!/usr/bin/env python3
"""One short weekly page on data quality, for people, not for the pipeline.

Reads the published static catalog (what visitors see), compares it with the
previous run kept in a small history file, and lists red flags: a figure that
dropped, a source not read recently, an automatic job that failed. Read-only
on the catalog; it writes only the report and the history.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import date, timedelta
from pathlib import Path

from catalog_quality_report import VAGUE_ADDRESSES, key
from merge_catalog import load_existing

CLOCK = re.compile(r"\b\d{1,2}[:.]\d\d\b")
DROP_ALERT = 2.0        # percentage points lost since the previous run
STALE_SOURCE_DAYS = 8   # a source read weekly or daily should never exceed this
HISTORY_KEEP = 104      # two years of weekly runs
TOP_SOURCES = 8


def classify(row, today):
    hours = str(row.get("orario_testo") or "").strip()
    place = str(row.get("indirizzo") or "").strip()
    soon = (today + timedelta(days=30)).isoformat()
    return {
        "orari_esatti": bool(CLOCK.search(hours)),
        "solo_fascia": bool(hours) and not CLOCK.search(hours),
        "via_reale": bool(place) and key(place) not in VAGUE_ADDRESSES,
        "solo_centro": bool(place) and key(place) in VAGUE_ADDRESSES,
        "date_30_giorni": any(today.isoformat() <= d <= soon for d in row.get("date") or []),
        "posizione": row.get("lat") is not None,
    }


def last_read(row):
    days = [str(row.get("fonte_letta_il") or "")[:10]]
    days += [str(r.get("letto_il") or "")[:10] for r in row.get("riscontri_campi") or []
             if isinstance(r, dict)]
    return max((d for d in days if re.fullmatch(r"\d{4}-\d\d-\d\d", d)), default="")


def measure(rows, today):
    visible = [r for r in rows if not r.get("duplicato_di")]
    total = defaultdict(int)
    by_source = defaultdict(lambda: defaultdict(int))
    read = defaultdict(str)
    for row in visible:
        source = str(row.get("fonte") or "sconosciuta")
        flags = classify(row, today)
        for name, value in flags.items():
            total[name] += value
            by_source[source][name] += value
        by_source[source]["schede"] += 1
        read[source] = max(read[source], last_read(row))
    pct = lambda part, whole: round(100 * part / whole, 1) if whole else 0.0
    sources = sorted(by_source, key=lambda s: -by_source[s]["schede"])
    return {
        "date": today.isoformat(), "schede": len(rows), "visibili": len(visible),
        "copie_unite": len(rows) - len(visible),
        "percentuali": {name: pct(value, len(visible)) for name, value in total.items()},
        "fonti": {s: {"schede": by_source[s]["schede"], "letta_il": read[s],
                      **{n: pct(by_source[s][n], by_source[s]["schede"]) for n in total}}
                  for s in sources},
    }


def red_flags(current, previous, jobs, today):
    flags = []
    for job, state in sorted((jobs or {}).items()):
        if state.get("status") != "ok":
            flags.append(f"Il job **{job}** non è andato a buon fine (ultimo tentativo {state.get('at', '?')}).")
    if previous:
        for name, value in current["percentuali"].items():
            before = previous["percentuali"].get(name)
            if before is not None and before - value > DROP_ALERT and name not in ("solo_fascia", "solo_centro"):
                flags.append(f"**{LABELS[name]}** è sceso da {before}% a {value}%.")
        if current["visibili"] < previous["visibili"] * 0.98:
            flags.append(f"Le schede visibili sono scese da {previous['visibili']} a {current['visibili']}.")
    for source, data in list(current["fonti"].items())[:TOP_SOURCES]:
        if data["letta_il"] and (today - date.fromisoformat(data["letta_il"])).days > STALE_SOURCE_DAYS:
            flags.append(f"La fonte **{source}** non viene riletta dal {data['letta_il']}.")
    return flags


LABELS = {"orari_esatti": "Orari esatti", "solo_fascia": "Solo mattina/pomeriggio",
          "via_reale": "Via precisa", "solo_centro": "Solo «centro»",
          "date_30_giorni": "Date nei prossimi 30 giorni", "posizione": "Posizione sulla mappa"}


def markdown(current, previous, flags, jobs):
    delta = lambda name: ("" if not previous or name not in previous["percentuali"] else
                          f" ({current['percentuali'][name] - previous['percentuali'][name]:+.1f})")
    lines = [f"# Qualità dei dati — {current['date']}", "",
             "Pagina aggiornata in automatico. Tra parentesi: variazione rispetto al controllo precedente"
             + (f" ({previous['date']})." if previous else "."), "",
             "## Semaforo", "",
             ("🟢 Tutto regolare." if not flags else "🔴 **Da guardare:**"), ""]
    lines += [f"- {f}" for f in flags]
    if jobs:
        lines += ["", "| Job automatico | Esito | Quando |", "|---|---|---|"]
        lines += [f"| {j} | {'✅' if s.get('status') == 'ok' else '❌'} | {s.get('at', '')} |"
                  for j, s in sorted(jobs.items())]
    lines += ["", "## Cosa vede chi usa l'app", "",
              f"**{current['visibili']:,}** mercati visibili ({current['copie_unite']:,} copie doppie unite e nascoste).", "",
              "| Dato | Mercati |", "|---|---:|"]
    lines += [f"| {LABELS[n]} | {current['percentuali'][n]}%{delta(n)} |" for n in LABELS]
    lines += ["", "## Per fonte", "",
              "| Fonte | Mercati | Orari esatti | Via precisa | Date 30 gg | Letta il |",
              "|---|---:|---:|---:|---:|---|"]
    for source, d in list(current["fonti"].items())[:TOP_SOURCES]:
        lines.append(f"| {source} | {d['schede']:,} | {d['orari_esatti']}% | {d['via_reale']}% | "
                     f"{d['date_30_giorni']}% | {d['letta_il'] or '—'} |")
    return "\n".join(lines) + "\n"


def run(manifest, history_path, report_path, *, today, jobs=None):
    current = measure(load_existing(manifest), today)
    history = json.loads(history_path.read_text("utf-8")) if history_path.is_file() else []
    previous = next((h for h in reversed(history) if h["date"] < current["date"]), None)
    flags = red_flags(current, previous, jobs, today)
    history = [h for h in history if h["date"] != current["date"]] + [current]
    history_path.parent.mkdir(parents=True, exist_ok=True)
    history_path.write_text(json.dumps(history[-HISTORY_KEEP:], ensure_ascii=False, indent=1) + "\n",
                            encoding="utf-8", newline="\n")
    report_path.write_text(markdown(current, previous, flags, jobs), encoding="utf-8", newline="\n")
    return current, flags


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", type=Path, default=Path("public/data/v1/manifest.json"))
    p.add_argument("--history", type=Path, default=Path("reports/quality-history.json"))
    p.add_argument("--report", type=Path, default=Path("reports/QUALITA.md"))
    p.add_argument("--jobs", type=Path, help="JSON {job: {status: ok|failed, at: ...}} from the scheduler")
    p.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = p.parse_args()
    jobs = json.loads(args.jobs.read_text("utf-8")) if args.jobs and args.jobs.is_file() else None
    current, flags = run(args.manifest, args.history, args.report, today=args.today, jobs=jobs)
    print(json.dumps({"visibili": current["visibili"], "red_flags": len(flags)}, ensure_ascii=False))


if __name__ == "__main__":
    main()
