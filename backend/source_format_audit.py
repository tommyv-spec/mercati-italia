#!/usr/bin/env python3
"""Inventory existing source URL formats and retain evidence-backed review tasks.

This report does not fetch pages, change market fields, activate readers or
grant reuse rights. A URL shape is a review unit, not proof of a shared DOM.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from urllib.parse import parse_qsl, urlsplit

FIELDS = ("indirizzo", "orario_testo", "ricorrenza_testo", "date")
CHECKS = ("source_sample", "field_mapping", "parser_comparison", "storage_comparison")
CHECK_LABELS = {"source_sample": "Fonte letta", "field_mapping": "Campi letti",
                "parser_comparison": "Parser confrontato", "storage_comparison": "Catalogo confrontato"}
DEFAULT_LEDGER = Path(__file__).resolve().parent / "data" / "source-format-review-ledger.json"
DEFAULT_REPO_ROOT = Path(__file__).resolve().parent.parent
CITYNEWS_EXTRA = {"arezzonotizie.it", "casertanews.it", "brindisireport.it"}
KNOWN_PATTERNS = {
    "emiliaromagnaturismo.it": [(r"/it/eventi/[^/]+/?", "/it/eventi/{slug}", "tourism_event_detail")],
    "eventi.bergamo.it": [(r"/evento/[^/]+/?", "/evento/{slug}/", "wordpress_event_detail")],
    "umbriaeventi.com": [(r"/[^/]+-\d+\.htm", "/{slug}-{id}.htm", "event_detail_legacy"),
                         (r"/eventi/[^/]+-\d+/?", "/eventi/{slug}-{id}", "event_detail_current")],
    "solosagre.it": [(r"/mostre-e-mercatini/[^/]+/[^/]+/[^/]+/[^/]+\.html", "/mostre-e-mercatini/{regione}/{provincia}/{comune}/{slug}.html", "event_detail")],
    "trentino.com": [(r"/it/calendario/dettagli/[^/]+/?", "/it/calendario/dettagli/{slug}/#{edizione}", "calendar_event_detail")],
    "pugliainfesta.it": [(r"/evento/\d+/[^/]+\.html", "/evento/{id}/{slug}.html", "event_detail")],
    "feelflorence.it": [(r"/it/punti-di-interesse/[^/]+/?", "/it/punti-di-interesse/{slug}", "tourism_place_detail")],
}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                     separators=(",", ":")).encode()).hexdigest()


def classify_url(url):
    """Keep every unknown route explicit instead of approving a whole host."""
    try:
        p = urlsplit(str(url or ""))
        host = (p.hostname or "").lower().removeprefix("www.")
        if p.scheme not in {"http", "https"} or not host or p.username or p.password:
            raise ValueError("not a public source URL")
        if p.port not in {None, 80, 443}:
            raise ValueError("unexpected port")
    except ValueError:
        host, pattern, kind = "invalid-source-url", str(url or ""), "invalid_source_url"
    else:
        path = p.path or "/"
        pattern, kind = path, "literal_route_needs_layout_review"
        if re.search(r"\.(?:it|com|org)(?:note|index)\.(?:asp|php)$", host):
            kind = "possibly_concatenated_relative_url"
        elif host == "happings.com":
            if re.fullmatch(r"/it/mercati-settimanali-a-[^/]+\.html", path):
                pattern, kind = "/it/mercati-settimanali-a-{provincia}.html", "happings_province_legacy_a"
            elif re.fullmatch(r"/it/mercati-settimanali-ad-[^/]+\.html", path):
                pattern, kind = "/it/mercati-settimanali-ad-{provincia}.html", "happings_province_legacy_ad"
            elif re.fullmatch(r"/it/mercati-settimanali-(?:a|ad)-[^/]+-e-provincia/?", path):
                pattern, kind = "/it/mercati-settimanali-{a|ad}-{provincia}-e-provincia/", "happings_province_current"
            elif re.fullmatch(r"/it/happing/[^/]+/?", path):
                pattern, kind = "/it/happing/{slug}/", "happings_event_detail_current"
            elif re.fullmatch(r"/it/[^/]+\.html", path):
                pattern, kind = "/it/{scheda-comunale}.html", "happings_town_legacy"
        elif host == "eventiesagre.it" and re.fullmatch(r"/[^/]+/\d+_[^/]+\.html", path):
            pattern = "/" + path.split("/")[1] + "/{id}_{slug}.html"
            kind = "eventiesagre_event_detail"
        elif host == "cosedicasa.com" and re.fullmatch(r"/mercatini/[^/]+/?", path):
            pattern, kind = "/mercatini/{slug}", "cosedicasa_market_calendar"
        elif host.endswith("today.it") or host in CITYNEWS_EXTRA:
            if path.startswith("/eventi/tipo/"):
                pattern, kind = "/eventi/tipo/{filtri}/", "citynews_event_index"
            elif path.startswith("/eventi/") and path.endswith(".html"):
                pattern, kind = "/eventi/{percorso-evento}.html", "citynews_event_detail"
            elif path.startswith("/tag/"):
                pattern, kind = "/tag/{tag}/", "citynews_tag_index"
            elif path.endswith(".html"):
                pattern, kind = "/" + path.strip("/").split("/")[0] + "/{articolo}.html", "citynews_news_article"
        else:
            for expr, shape, source_kind in KNOWN_PATTERNS.get(host, []):
                if re.fullmatch(expr, path):
                    pattern, kind = shape, source_kind
                    break
            if path == "/":
                kind = "publisher_homepage"
            if path.endswith(".pdf"):
                kind = "pdf_document_requires_individual_layout_review"
        # Parameters identify distinct applications, not separate event IDs.
        keys = sorted({key for key, _ in parse_qsl(p.query, keep_blank_values=True)})
        if keys:
            pattern += "?" + "&".join(key + "={value}" for key in keys)
    return {"format_id": host + "--" + digest([host, pattern])[:12],
            "host": host, "url_pattern": pattern, "url_kind": kind,
            "classification_basis": "URL_shape_not_DOM_verification"}


def inventory(rows):
    groups = {}
    secondary = defaultdict(set)
    seen_ids = set()
    for row in rows:
        identity = row.get("slug")
        if not isinstance(identity, str) or not identity or identity in seen_ids:
            raise ValueError("Catalog inventory requires unique, nonempty market IDs")
        seen_ids.add(identity)
        url = str(row.get("url_fonte") or "")
        f = classify_url(url)
        item = groups.setdefault(f["format_id"], {**f, "ids": [], "urls": set(),
            "source_labels": Counter(), "empty_fields": Counter(), "sample_scores": {}})
        item["ids"].append(identity)
        item["urls"].add(url)
        item["source_labels"][str(row.get("fonte") or "")] += 1
        empty = [name for name in FIELDS if not row.get(name)]
        item["empty_fields"].update(empty)
        item["sample_scores"][url] = max(len(empty), item["sample_scores"].get(url, 0))
        for source in row.get("fonti", []) or []:
            if isinstance(source, dict) and isinstance(source.get("url"), str):
                secondary[source["url"]].add(identity)
    primary_urls = {u for g in groups.values() for u in g["urls"]}
    result = []
    for g in groups.values():
        ids, urls, scores = g.pop("ids"), g.pop("urls"), g.pop("sample_scores")
        g.update({"catalog_records": len(ids), "catalog_ids_sha256": digest(sorted(ids)),
            "unique_primary_urls": len(urls), "primary_urls_sha256": digest(sorted(urls)),
            "sample_candidates": sorted(urls, key=lambda u: (-scores[u], u))[:3],
            "source_labels": dict(sorted(g["source_labels"].items())),
            "empty_fields": {field: g["empty_fields"].get(field, 0) for field in FIELDS}})
        result.append(g)
    return {"catalog_records": len(rows), "catalog_ids_sha256": digest(sorted(seen_ids)),
        "primary_source_labels": len({str(r.get("fonte") or "") for r in rows}),
        "primary_hosts": len({g["host"] for g in result}),
        "primary_url_hostnames": len({(urlsplit(u).hostname or "").lower()
                                      for u in primary_urls if classify_url(u)["host"] != "invalid-source-url"}),
        "unique_primary_urls": len(primary_urls),
        "formats": sorted(result, key=lambda g: (-g["catalog_records"], g["format_id"])),
        "additional_attribution_urls": [{"url": u, "catalog_records": len(ids),
            **classify_url(u)} for u, ids in sorted(secondary.items()) if u not in primary_urls]}


def storage_snapshot(rows, sample_urls):
    """Fingerprint complete exported sample rows, including geography and source evidence."""
    urls = set(sample_urls)
    selected = [row for row in rows if row.get("url_fonte") in urls]
    return {"records": len(selected), "sha256": digest(sorted(selected, key=lambda r: r["slug"]))}


def code_fingerprints(paths, repo_root=DEFAULT_REPO_ROOT):
    """Resolve local repository files only; an absent adapter is recorded as absent."""
    root = Path(repo_root).resolve()
    result = {}
    for name in paths:
        path = Path(name)
        resolved = (root / path).resolve()
        if path.is_absolute() or ".." in path.parts or not resolved.is_relative_to(root):
            raise ValueError("Audit code paths must remain inside the repository")
        result[name] = hashlib.sha256(resolved.read_bytes()).hexdigest() if resolved.is_file() else None
    return result


def _iso_day(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00")).date()
    except (ValueError, TypeError):
        raise ValueError("Review evidence needs an ISO observation date") from None


def _valid_sample(sample, format_id):
    """A redirected URL can be reviewed, but cannot silently approve a historical DOM."""
    if classify_url(sample.get("requested_url"))["format_id"] != format_id:
        return False
    if sample.get("state") != "read" or sample.get("content_reviewed") is not True:
        return False
    if not sample.get("layout") or not sample.get("field_map"):
        return False
    if not re.fullmatch(r"[a-f0-9]{64}", str(sample.get("sha256", ""))):
        return False
    if sample.get("hash_basis") not in {"http_response_bytes", "connector_utf8_text"}:
        return False
    if not isinstance(sample.get("bytes"), int) or sample["bytes"] <= 0:
        return False
    if sample.get("http_status") is not None and sample["http_status"] != 200:
        return False
    transport_formats = {classify_url(sample[key])["format_id"] for key in
                         ("observed_final_url", "final_url", "transport_final_url")
                         if sample.get(key)} - {format_id}
    canonical_formats = {classify_url(sample[key])["format_id"] for key in
                         ("canonical_url", "canonical_url_in_html")
                         if sample.get(key)} - {format_id}
    target_formats = transport_formats | canonical_formats
    if target_formats:
        transition = sample.get("layout_transition", {})
        if (len(target_formats) != 1 or transition.get("observed_format_id") not in target_formats
                or transition.get("basis") not in {"observed_http_redirect", "html_canonical_and_scoped_layout"}
                or not transition.get("note")):
            return False
        evidence_channel = (transport_formats if transition["basis"] == "observed_http_redirect"
                            else canonical_formats)
        if transition["observed_format_id"] not in evidence_channel:
            return False
    _iso_day(sample.get("acquired_at"))
    return True


def _validate_ledger(ledger):
    if ledger.get("schema_version") != 1:
        raise ValueError("Unsupported source format review ledger")
    entries, tasks, checkins = {}, {}, {}
    for target, objects, key in ((entries, ledger.get("formats", []), "format_id"),
                                 (tasks, ledger.get("tasks", []), "id"),
                                 (checkins, ledger.get("checkins", []), "id")):
        for obj in objects:
            ident = obj.get(key)
            if not isinstance(ident, str) or not ident or ident in target:
                raise ValueError("Review IDs must be unique and nonempty")
            target[ident] = obj
    for task in tasks.values():
        if task.get("status") not in {"open", "in_progress", "done"}:
            raise ValueError("Unknown TODO status")
        if not task.get("acceptance"):
            raise ValueError("TODOs require a concrete acceptance condition")
        if task["status"] == "done" and not task.get("resolution"):
            raise ValueError("Completed TODOs need a recorded resolution")
        if any(f not in entries for f in task.get("format_ids", [])):
            raise ValueError("TODO references an unknown review format")
    for entry in entries.values():
        if any(t not in tasks for t in entry.get("todo_ids", [])):
            raise ValueError("Review references an unknown TODO")
        for name, check in entry.get("checks", {}).items():
            if name not in CHECKS or check.get("state") not in {"done", "partial", "pending"}:
                raise ValueError("Unknown review check or state")
            if check.get("state") != "pending" and not check.get("note"):
                raise ValueError("Completed or partial checks need a reason")
    for checkin in checkins.values():
        _iso_day(checkin.get("at"))
        if not checkin.get("summary"):
            raise ValueError("Check-ins need a summary")
    return entries, tasks


def build_report(rows, ledger, *, today=None, repo_root=DEFAULT_REPO_ROOT):
    """Refresh the TODO inventory offline without relabelling yesterday's samples as new reads."""
    today = today or date.today()
    if isinstance(today, str):
        today = date.fromisoformat(today)
    inv = inventory(rows)
    entries, tasks = _validate_ledger(ledger)
    primary_ids = {f["format_id"] for f in inv["formats"]}
    additional = []
    # Secondary attribution URLs are inventoried even when not manually registered yet.
    for attribution in inv["additional_attribution_urls"]:
        if attribution["format_id"] not in primary_ids and not any(
                a["format_id"] == attribution["format_id"] for a in additional):
            additional.append({**classify_url(attribution["url"]), "catalog_records": 0,
                               "sample_candidates": [attribution["url"]], "scope": "additional_attribution"})
    for ident, entry in entries.items():
        if ident not in primary_ids and not any(a["format_id"] == ident for a in additional):
            additional.append({k: entry.get(k) for k in ("format_id", "host", "url_pattern", "url_kind")})
            additional[-1].update(catalog_records=0, sample_candidates=[], scope=entry.get("scope", "historical_format"))

    def review(item, primary):
        ident = item["format_id"]
        entry = entries.get(ident, {})
        checks = {name: dict(entry.get("checks", {}).get(name, {"state": "pending", "note": "Da verificare."}))
                  for name in CHECKS}
        reasons = []
        samples = entry.get("samples", [])
        recognized = [s for s in samples if _valid_sample(s, ident)]
        good = [s for s in recognized if _iso_day(s["acquired_at"]) <= today]
        if len(recognized) != len(good):
            reasons.append("sample_after_report_date")
        if not good:
            for name in ("source_sample", "field_mapping"):
                if checks[name]["state"] == "done":
                    checks[name] = {"state": "pending", "note": "Manca una lettura riconosciuta e documentata di questo formato."}
        if checks["parser_comparison"]["state"] == "done":
            previous = entry.get("code_sha256", {})
            current = code_fingerprints(previous, repo_root)
            if not previous or not entry.get("parser_comparison_basis"):
                checks["parser_comparison"] = {"state": "pending", "note": "Manca il confronto documentato con il codice."}
            elif previous != current:
                checks["parser_comparison"] = {"state": "pending", "note": "Il codice confrontato è cambiato: ripetere il confronto."}
                reasons.append("parser_code_changed")
        if checks["storage_comparison"]["state"] == "done":
            urls = entry.get("sample_catalog_urls", [])
            previous = entry.get("storage_snapshot")
            if not isinstance(urls, list) or not previous or (primary and (not urls or not previous.get("records"))):
                checks["storage_comparison"] = {"state": "pending", "note": "Manca la fotografia dei campi confrontati."}
            elif any(classify_url(u)["format_id"] != ident for u in urls):
                checks["storage_comparison"] = {"state": "pending", "note": "Il confronto salvato riguarda un altro formato."}
            elif storage_snapshot(rows, urls) != previous:
                checks["storage_comparison"] = {"state": "pending", "note": "I campi del campione nel catalogo sono cambiati: riconfrontare."}
                reasons.append("sample_catalog_fields_changed")
        reviewed_at = entry.get("reviewed_at")
        if reviewed_at:
            review_day = _iso_day(reviewed_at)
            if review_day > today:
                # Historical dry runs may predate this ledger. Preserve its
                # history, but never count later evidence as known on that day.
                reasons.append("checkin_after_report_date")
                checks = {name: {"state": "pending", "note": "Check-in successivo alla data simulata del report."}
                          for name in CHECKS}
            elif (today - review_day).days > entry.get("review_interval_days", 30):
                reasons.append("sample_review_due")
        if primary and entry.get("primary_urls_sha256") and entry["primary_urls_sha256"] != item["primary_urls_sha256"]:
            reasons.append("catalog_source_urls_changed")
        if not entry:
            reasons.append("new_format")
        pending = [name for name, check in checks.items() if check["state"] != "done"]
        active_todos = [t for t in entry.get("todo_ids", []) if tasks[t]["status"] != "done"]
        status = "reviewed_sample" if not pending and not reasons else "partial_review" if good or any(
            c["state"] in {"done", "partial"} for c in checks.values()) else "not_reviewed"
        return {**item, "scope": "primary_catalog" if primary else item.get("scope", "auxiliary_resource"),
                "review_status": status, "reviewed_at": reviewed_at, "checks": checks,
                "pending_checks": pending, "recheck_reasons": reasons,
                "samples": samples, "evidence_report": entry.get("evidence_report"),
                "findings": entry.get("findings", []), "todo_ids": entry.get("todo_ids", []),
                "open_todo_ids": active_todos, "data_truth_verified": False,
                "automatic_import_enabled_by_this_audit": False}

    primary = [review(item, True) for item in inv.pop("formats")]
    auxiliary = [review(item, False) for item in sorted(additional, key=lambda x: x["format_id"])]
    stats = Counter(f["review_status"] for f in primary)
    pending_tasks = [t for t in tasks.values() if t["status"] != "done"]
    return {"schema_version": 1, "generated_for_date": today.isoformat(),
        "method": "Exhaustive URL-format inventory; bounded real-page samples; source/parser/storage comparisons. URL patterns are not proven DOM-equivalence classes.",
        "scope_limit": "Reviewing a source format is not verification of every market, field or future edition. Rebuilding this report performs no network reads.",
        **inv, "summary": {"primary_format_units": len(primary),
            "formats_with_sample_attempt": sum(bool(f["samples"]) for f in primary),
            "formats_with_documented_source_read": sum(f["checks"]["source_sample"]["state"] == "done" for f in primary),
            "reviewed_sample_formats": stats["reviewed_sample"], "partial_review_formats": stats["partial_review"],
            "unreviewed_formats": stats["not_reviewed"], "auxiliary_format_units": len(auxiliary),
            "formats_with_open_corrections": sum(bool(f["open_todo_ids"]) for f in primary),
            "formats_requiring_recheck": sum(bool(f["recheck_reasons"]) for f in primary),
            "open_tasks": len(pending_tasks), "completed_tasks": len(tasks) - len(pending_tasks),
            "network_reads_performed": 0, "catalog_records_modified": 0},
        "formats": primary, "auxiliary_formats": auxiliary,
        "checkins": ledger.get("checkins", []), "tasks": list(tasks.values())}


def render_checklist(report):
    """A checked audit step means examined, never complete/correct market data."""
    def cell(value):
        return str(value or "—").replace("|", "\\|").replace("\n", " ")

    stats = report["summary"]
    lines = ["# Verifica dei formati delle fonti", "", f"Generato per il {report['generated_for_date']}.", "",
        f"Catalogo: **{report['catalog_records']:,} schede**, **{report['unique_primary_urls']:,} URL primari**, "
        f"**{report['primary_url_hostnames']} hostname** ({report['primary_hosts']} dopo l’unificazione di `www`).", "",
        f"**{stats['primary_format_units']} unità di formato URL**: {stats['reviewed_sample_formats']} con confronto del campione completato, "
        f"{stats['partial_review_formats']} parziali, {stats['unreviewed_formats']} da verificare. "
        f"Le {stats['auxiliary_format_units']} unità ausiliarie non aumentano il numero delle schede.", "",
        "Le spunte indicano una verifica eseguita sul campione. Non attestano che tutte le schede siano corrette, "
        "aggiornate o complete. I TODO indicano separatamente le correzioni e i raccordi ancora da realizzare. "
        "Il report quotidiano legge il catalogo e questo registro senza effettuare nuove richieste alle fonti.", "",
        "## Check-in", ""]
    for checkin in report["checkins"]:
        lines.append(f"- **{cell(checkin['at'])} — {cell(checkin['id'])}**: {cell(checkin['summary'])}")
    lines += ["", "## Checklist dei formati primari", "", "Legenda: ✓ completato sul campione; ◐ parziale; ○ da verificare.", "",
        "| Formato / fonte | Schede | Fonte | Campi | Parser | Catalogo | TODO aperti |",
        "| --- | ---: | :---: | :---: | :---: | :---: | --- |"]
    glyph = {"done": "✓", "partial": "◐", "pending": "○"}
    for f in report["formats"]:
        label = f"`{cell(f['host'])}` · `{cell(f['url_pattern'])}`"
        flags = " | ".join(glyph[f["checks"][name]["state"]] for name in CHECKS)
        todos = ", ".join(f["open_todo_ids"]) or ("Verificare nuovo formato" if f["recheck_reasons"] else "—")
        lines.append(f"| {label} | {f['catalog_records']} | {flags} | {cell(todos)} |")
    lines += ["", "## Evidenze e prossime azioni per formato", ""]
    for f in [*report["formats"], *report["auxiliary_formats"]]:
        lines += [f"### {cell(f['format_id'])}", "", f"`{cell(f['url_pattern'])}` — {cell(f['scope'])}.", ""]
        if f.get("reviewed_at"):
            lines.append(f"Ultimo check-in: {f['reviewed_at']}.")
        for name in CHECKS:
            c = f["checks"][name]
            lines.append(f"- [{'x' if c['state'] == 'done' else ' '}] {CHECK_LABELS[name]}: {cell(c['note'])}")
        for sample in f["samples"]:
            lines.append(f"- Campione: {sample.get('requested_url', '')} — {cell(sample.get('state'))}, "
                         f"lettura {cell(sample.get('acquired_at'))}; SHA-256 `{cell(sample.get('sha256'))}`.")
        for finding in f["findings"]:
            lines.append(f"- Riscontro: {cell(finding)}")
        if f["recheck_reasons"]:
            lines.append("- Da riconfrontare: " + ", ".join(f["recheck_reasons"]) + ".")
        if f["evidence_report"]:
            lines.append(f"- Dettagli: `{f['evidence_report']}`.")
        lines.append("")
    lines += ["## TODO del meccanismo", ""]
    for task in report["tasks"]:
        lines += [f"- [{'x' if task['status'] == 'done' else ' '}] **{cell(task['id'])} — {cell(task['title'])}** "
                  f"({cell(task.get('priority', 'normal'))}; {cell(task['status'])}). "
                  f"Criterio di chiusura: {cell(task['acceptance'])}"]
        if task.get("resolution"):
            lines[-1] += f" Esito: {cell(task['resolution'])}"
    return "\n".join(lines).rstrip() + "\n"


def compact_status(report):
    """History-safe per-format progress for the existing daily publisher report."""
    def item(f):
        return {k: f[k] for k in ("format_id", "host", "url_pattern", "catalog_records", "review_status",
                                 "reviewed_at", "pending_checks", "recheck_reasons", "open_todo_ids")}
    return {"schema_version": 1, "summary": report["summary"],
            "generated_for_date": report["generated_for_date"],
            "ledger": "backend/data/source-format-review-ledger.json",
            "checklist": "reports/automation/SOURCE_FORMAT_CHECKLIST.md",
            "formats": [item(f) for f in report["formats"]],
            "auxiliary_formats": [item(f) for f in report["auxiliary_formats"]]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, default=Path("public/data/v1/manifest.json"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--ledger", type=Path, default=DEFAULT_LEDGER)
    parser.add_argument("--markdown", type=Path)
    parser.add_argument("--today", type=date.fromisoformat, default=date.today())
    parser.add_argument("--inventory-only", action="store_true")
    args = parser.parse_args()
    from merge_catalog import load_existing
    rows = load_existing(args.manifest)
    report = inventory(rows) if args.inventory_only else build_report(
        rows, json.loads(args.ledger.read_text("utf-8")), today=args.today)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", "utf-8")
    if args.markdown and not args.inventory_only:
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(render_checklist(report), "utf-8")
    print(json.dumps(report.get("summary", {k: v for k, v in report.items()
        if k not in {"formats", "additional_attribution_urls"}})))


if __name__ == "__main__":
    main()
