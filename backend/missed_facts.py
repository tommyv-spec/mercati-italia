#!/usr/bin/env python3
"""Facts a source states that the card a visitor sees does not show.

Owner objective (2026-10-29): capture everything each source says. A source that only
says "la mattina" or "centro" is accurate as given; a gap is a fact the source states
and the shown card lacks. Offline and read-only: it reads the pages the nightly already
downloaded (autopilot-output/sources/*-detail-pages.json), the readers' own reports and
the candidate catalog. Four kinds of gap:
  parser_missed    the page text states a time range the reader did not read as hours
  read_not_used    the reader read hours, a street or future dates; the shown card lacks them
  lost_in_merge    a hidden copy of the market has clock hours or a street the shown card lacks
  hidden_but_read  hidden as "fonte_non_riletta" although its own page was read in the
                   last CONCLUDED_UNREAD_DAYS days: the reader held the page, so nothing
                   reached the card (tonight's pages show what they state under read_not_used)
eventiesagre's template "08:00–13:00" is not a fact (CONTROLLO_FONTI S13). Happings event
pages measure their own per-field disposition; it is summed here, pages that are not
markets left out.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import json
import re
from collections import Counter, defaultdict
from datetime import date, timedelta
from pathlib import Path

from export_static import CONCLUDED_UNREAD_DAYS, exact_hours, own_source_last_read
from merge_catalog import load_existing
from quality_scorecard import CLOCK, page_reads
from stored_market_sibling_proposals import ADDRESS_PREFIX

EDITORIAL = ("eventiesagre", "cosedicasa")
HAPPINGS_GAPS = ("source_present_parser_missing", "source_present_parser_partial",
                 "source_present_parsed_held", "source_present_parsed_identity_unresolved")
NOT_A_MARKET = "source_category_or_event_is_not_a_market"
MAX_EXAMPLES = 15
STREET = re.compile(ADDRESS_PREFIX.pattern.removeprefix("^"), re.I)   # a street word anywhere
_T = r"(\d{1,2})(?:[:.](\d\d))?"
# "dalle 8 alle 19", "Dale ore 8 alle 19" (a real typo), "ore 9-13", "9:00 - 18:30".
RANGE = re.compile(rf"(?i)\b(?:dal+e|ore|h)\.?\s*(?:ore\s*)?{_T}\s*(?:alle|fino alle|-|–)\s*(?:ore\s*)?{_T}\b"
                   rf"|\b(\d{{1,2}})[:.](\d\d)\s*[-–]\s*(\d{{1,2}})[:.](\d\d)\b")
FOOTER = re.compile(r"(?i)P\.?\s?IVA|Tutti i diritti|Data ultimo aggiornamento|Diniego di responsabilit")


def page_text(body: bytes) -> str:
    """Visible text from the page title to the site footer (other pages' boilerplate out)."""
    html = body.decode("utf-8", "replace")
    html = re.sub(r"(?is)<(script|style|noscript)\b.*?</\1>", " ", html)
    start = html.lower().find("<h1")
    text = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", html[max(start, 0):]))
    end = FOOTER.search(text)
    return text[:end.start()] if end else text


def time_range(text: str):
    for m in RANGE.finditer(text):
        hours = [int(g) for g in (m.group(1, 3) if m.group(1) else m.group(5, 7))]
        if all(0 <= h <= 24 for h in hours) and hours[0] < hours[1]:
            return text[max(0, m.start() - 60):m.end() + 30].strip()
    return None


def clock(value) -> bool:
    return bool(CLOCK.search(str(value or "")))


def street(value) -> bool:
    return bool(STREET.search(str(value or "")))


def editorial_gaps(out: Path, by_url, by_slug, today):
    found = defaultdict(list)
    counts = defaultdict(Counter)
    for publisher in EDITORIAL:
        pages_file, report_file = out / f"sources/{publisher}-detail-pages.json", out / f"{publisher}-detail-refresh.json"
        if not pages_file.is_file() or not report_file.is_file():
            continue
        evidence = json.loads(report_file.read_text("utf-8")).get("evidence") or {}
        docs = {(d.get("parsed") or {}).get("source", {}).get("requested_url"): d.get("parsed") or {}
                for d in evidence.get("documents") or []}
        outcomes = {o.get("url"): o for o in evidence.get("outcomes") or []}
        for page in json.loads(pages_file.read_text("utf-8")).get("pages") or []:
            url = page["requested_url"]
            counts[publisher]["pages"] += 1
            cards = by_url.get(url) or by_url.get(page.get("final_url")) or []
            if not cards:
                continue
            card = by_slug.get(cards[0].get("duplicato_di"), cards[0])   # the card a visitor sees
            if card.get("concluso") in ("edizione_conclusa", "non_piu_elencato"):   # over, per its source
                continue
            doc = docs.get(url) or {}
            event = doc.get("event") or {}
            outcome = outcomes.get(url) or {}
            reason = outcome.get("reason") or "; ".join(map(str, outcome.get("field_holds") or [])) or "—"
            base = {"url": url, "slug": card["slug"], "reason": reason}
            read_clock = bool(event.get("hours_intervals")) or clock(event.get("hours_text"))
            if not read_clock and not clock(card.get("orario_testo")) \
                    and "publisher_default_hours" not in (doc.get("warnings") or []):
                body = gzip.decompress(base64.b64decode(page["body_gzip_base64"]))
                if snippet := time_range(page_text(body)):
                    found["parser_missed"].append({**base, "field": "orario", "page": snippet})
            if read_clock and not clock(card.get("orario_testo")):
                found["read_not_used"].append({**base, "field": "orario", "read": event.get("hours_text")})
            address = (event.get("observed_location") or event.get("location") or {}).get("address")
            if street(address) and not street(card.get("indirizzo")):
                found["read_not_used"].append({**base, "field": "indirizzo", "read": address})
            future = sorted(o["date"] for o in event.get("occurrences") or [] if str(o.get("date")) >= today.isoformat())
            if future and not any(str(d) >= today.isoformat() for d in card.get("date") or []):
                found["read_not_used"].append({**base, "field": "date", "read": future[:3]})
    for kind, items in found.items():
        for item in items:
            counts[next(p for p in EDITORIAL if p in item["url"])][kind] += 1
    return found, counts


def lost_in_merge(rows, by_slug):
    """A hidden copy states clock hours or a street that its shown card lacks."""
    lost = []
    for copy in rows:
        shown = by_slug.get(copy.get("duplicato_di"))
        if not shown or shown.get("concluso"):
            continue
        if exact_hours(copy) and not exact_hours(shown):
            lost.append({"field": "orario", "slug": shown["slug"], "shown": shown.get("orario_testo"),
                         "copy": copy["slug"], "copy_source": copy.get("fonte"), "read": copy.get("orario_testo")})
        if street(copy.get("indirizzo")) and not street(shown.get("indirizzo")):
            lost.append({"field": "indirizzo", "slug": shown["slug"], "shown": shown.get("indirizzo"),
                         "copy": copy["slug"], "copy_source": copy.get("fonte"), "read": copy.get("indirizzo")})
    return lost


def happings_gaps(out: Path):
    report = out / "happings-details.json"
    if not report.is_file():
        return {}, []
    coverage = (json.loads(report.read_text("utf-8")).get("evidence") or {}).get("field_coverage") or {}
    totals, examples = defaultdict(Counter), []
    for page in coverage.get("pages") or []:
        if page.get("catalog_hold_reason") == NOT_A_MARKET:
            continue
        for field, data in (page.get("fields") or {}).items():
            totals[field].update({k: v for k, v in (data.get("disposition") or {}).items() if k in HAPPINGS_GAPS and v})
        examples += [{"url": page.get("requested_url"), "field": e.get("field"), "disposition": e.get("disposition"),
                      "reason": "; ".join(e.get("hold_reasons") or []) or "—"}
                     for e in page.get("examples") or [] if e.get("disposition") in HAPPINGS_GAPS]
    return {f: dict(c) for f, c in totals.items() if c}, examples


def hidden_but_read(rows, reads, today):
    cutoff = (today - timedelta(days=CONCLUDED_UNREAD_DAYS)).isoformat()
    hidden = [r for r in rows if r.get("concluso") == "fonte_non_riletta" and own_source_last_read(r, reads) >= cutoff]
    return [{"slug": r["slug"], "url": r.get("url_fonte"), "source": r.get("fonte"),
             "read": own_source_last_read(r, reads)} for r in hidden]


def run(out: Path, today: date):
    catalog = out / "candidate/public/data/v1"
    rows = load_existing(catalog / "manifest.json")
    by_url, by_slug = defaultdict(list), {r["slug"]: r for r in rows}
    for row in rows:
        if row.get("url_fonte"):
            by_url[row["url_fonte"]].append(row)
    found, counts = editorial_gaps(out, by_url, by_slug, today)
    happings, happings_examples = happings_gaps(out)
    return {"date": today.isoformat(), "editorial": {p: dict(c) for p, c in counts.items()},
            "editorial_gaps": dict(found), "happings_fields": happings, "happings_examples": happings_examples,
            "lost_in_merge": lost_in_merge(rows, by_slug),
            "hidden_but_read": hidden_but_read(rows, page_reads(catalog), today)}


def markdown(result) -> str:
    lines = [f"# Fatti della fonte che la scheda non mostra — {result['date']}", "",
             "Una fonte che dice solo «la mattina» o «centro» è corretta così. Qui solo ciò che la fonte "
             "dice e la scheda visibile non mostra.", "",
             "| Fonte | Pagine lette | Ora scritta ma non letta | Letto ma non sulla scheda |",
             "|---|---:|---:|---:|"]
    for publisher, c in result["editorial"].items():
        lines.append(f"| {publisher} | {c.get('pages', 0)} | {c.get('parser_missed', 0)} | {c.get('read_not_used', 0)} |")
    for field, d in result["happings_fields"].items():
        lines.append(f"| happings ({field}) | — | {d.get('source_present_parser_missing', 0) + d.get('source_present_parser_partial', 0)} | "
                     f"{d.get('source_present_parsed_held', 0) + d.get('source_present_parsed_identity_unresolved', 0)} |")
    merge, hidden = result["lost_in_merge"], result["hidden_but_read"]
    by_source = Counter(h["source"] for h in hidden)
    lines += ["", f"- **Persi nell'unione dei doppioni**: {sum(m['field'] == 'orario' for m in merge)} orari e "
              f"{sum(m['field'] == 'indirizzo' for m in merge)} vie che una copia nascosta ha e la scheda mostrata no.",
              f"- **Nascoste come «fonte non riletta» ma con pagina letta negli ultimi {CONCLUDED_UNREAD_DAYS} giorni**: "
              f"{len(hidden)} ({', '.join(f'{s} {n}' for s, n in by_source.most_common(5)) or '—'}). Il lettore ha "
              "trattenuto la pagina: per quelle lette stanotte, cosa dice e il motivo sono sotto «Letto dal lettore»."]
    sections = [("Ora scritta nella pagina, non letta", result["editorial_gaps"].get("parser_missed") or [],
                 lambda i: f"`{i['field']}` [{i['slug']}]({i['url']}) — «{i['page']}»"),
                ("Letto dal lettore, non sulla scheda", result["editorial_gaps"].get("read_not_used") or [],
                 lambda i: f"`{i['field']}` [{i['slug']}]({i['url']}) — {i['read']!s:.100} — motivo: {i['reason']}"),
                ("Persi nell'unione dei doppioni", merge,
                 lambda i: f"`{i['field']}` {i['slug']} mostra «{i['shown']}», la copia {i['copy_source']} ha «{i['read']}»"),
                ("Happings: campi letti ma trattenuti", result["happings_examples"],
                 lambda i: f"`{i['field']}` {i['url']} — {i['reason']}"),
                ("Nascoste ma con pagina letta", hidden,
                 lambda i: f"{i['slug']} ({i['source']}) letta il {i['read']}")]
    for title, items, line in sections:
        if items:
            lines += ["", f"## {title} ({len(items)})", ""] + [f"- {line(i)}" for i in items[:MAX_EXAMPLES]]
    return "\n".join(lines) + "\n"


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--out-dir", type=Path, default=Path("autopilot-output"))
    p.add_argument("--json", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = p.parse_args()
    result = run(args.out_dir, args.today)
    args.json.write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    args.report.write_text(markdown(result), encoding="utf-8")
    print(json.dumps({"editorial": result["editorial"], "lost_in_merge": len(result["lost_in_merge"]),
                      "hidden_but_read": len(result["hidden_but_read"])}, ensure_ascii=False))


if __name__ == "__main__":
    main()
