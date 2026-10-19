"""Bounded Happings phase for the existing DEV Autopilot.

The policy is disabled by default. A current authenticated rights record is
also required before fetching or applying fields. Raw responses and per-market
receipts stay in the existing temporary candidate/checkpoint directory.
"""
from __future__ import annotations

import base64
import hashlib
import json
from copy import deepcopy
from datetime import date
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError

import happings_source_enrichment as source
from export_static import normalize

SCHEMA = 1
DEFAULT_POLICY = {"enabled": False}
MAX_CHECKPOINT_BYTES = source.MAX_REQUESTS_PER_RUN * source.MAX_RESPONSE_BYTES * 2 + 50_000


def digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def validate_policy(policy):
    if (not isinstance(policy, dict) or set(policy) - {"enabled"}
            or type(policy.get("enabled", False)) is not bool):
        raise ValueError("Unreviewed Happings Autopilot policy")
    return {"enabled": policy.get("enabled", False)}


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", "utf-8")
    temporary.replace(path)


def _rights(path):
    try:
        record = json.loads(path.read_text("utf-8"))
    except (OSError, UnicodeError, ValueError):
        return False, "invalid_or_missing_rights_record", None
    if (not isinstance(record, dict) or record.get("schema") != 1
            or record.get("publisher") != "Girolamo srls (Happings)"
            or record.get("documents_copied_to_github") is not False):
        return False, "invalid_or_missing_rights_record", digest(record)
    authenticated = record.get("republication_rights_authenticated") is True
    return authenticated, "authenticated" if authenticated else "blocked_rights", digest(record)


def _pack_page(page):
    requested, final, body = (page.get(key) for key in ("requested_url", "final_url", "html"))
    if (not source.allowed_url(requested, requested, final)
            or not isinstance(body, bytes) or not 300 <= len(body) <= source.MAX_RESPONSE_BYTES):
        raise ValueError("Untrusted Happings source checkpoint page")
    return {
        "requested_url": requested, "final_url": final,
        "html_sha256": hashlib.sha256(body).hexdigest(),
        "html_base64": base64.b64encode(body).decode("ascii"),
    }


def _unpack_pages(saved, context):
    if (not isinstance(saved, dict) or saved.get("schema") != SCHEMA
            or saved.get("context") != context or not isinstance(saved.get("pages"), list)
            or len(saved["pages"]) > source.MAX_REQUESTS_PER_RUN
            or saved.get("status") not in ("fetch_started", "retrieved", "unavailable")):
        raise ValueError("Happings resume context changed or source checkpoint is invalid")
    pages, seen = [], set()
    for entry in saved["pages"]:
        if not isinstance(entry, dict):
            raise ValueError("Happings source checkpoint lost its evidence")
        try:
            raw = base64.b64decode(entry["html_base64"], validate=True)
        except (KeyError, TypeError, ValueError):
            raise ValueError("Happings checkpoint HTML is invalid") from None
        page = {"requested_url": entry.get("requested_url"),
                "final_url": entry.get("final_url"), "html": raw}
        packed = _pack_page(page)
        if (packed != entry or entry["requested_url"] not in context["selected_urls"]
                or entry["requested_url"] in seen):
            raise ValueError("Happings checkpoint source or content hash changed")
        seen.add(entry["requested_url"])
        pages.append(page)
    if (saved["status"] == "retrieved"
            and [page["requested_url"] for page in pages] != context["selected_urls"]):
        raise ValueError("Happings completed checkpoint lost selected source pages")
    return pages


def _fetch_and_checkpoint(urls, path, context, fetcher=None):
    """Keep every completed page even if a later request fails or is interrupted."""
    saved = {"schema": SCHEMA, "context": context, "status": "fetch_started", "pages": []}
    _write_json(path, saved)

    def capture(url, **kwargs):
        raw, final = source._fetch_one(url, **kwargs)
        page = _pack_page({"requested_url": url, "final_url": final, "html": raw})
        if url not in urls or any(item["requested_url"] == url for item in saved["pages"]):
            raise ValueError("Happings repeated or unselected request")
        saved["pages"].append(page)
        _write_json(path, saved)
        return raw, final

    try:
        if fetcher is None:
            pages = source.fetch_pages(urls, permission_confirmed=True, page_fetch=capture)
        else:
            pages = fetcher(urls, permission_confirmed=True)
        if not isinstance(pages, list) or [p.get("requested_url") for p in pages] != urls:
            raise ValueError("Happings fetch did not preserve its selected page batch")
        saved["pages"] = [_pack_page(page) for page in pages]
        saved["status"] = "retrieved"
        _write_json(path, saved)
        return pages, None
    except (OSError, HTTPError, HTTPException, ValueError) as error:
        saved["status"] = "unavailable"
        saved["error_type"] = type(error).__name__
        _write_json(path, saved)
        return [], type(error).__name__


def run(base, *, policy, out, today, baseline_signature, pipeline_policy_digest,
        offline=False, resume=False, rights_path=None, fetcher=None):
    """Return (candidate rows, bounded evidence report, IDs export must retain)."""
    policy = validate_policy(policy)
    if (not isinstance(today, date) or type(offline) is not bool or type(resume) is not bool
            or not isinstance(baseline_signature, str) or not baseline_signature
            or not isinstance(pipeline_policy_digest, str) or not pipeline_policy_digest):
        raise ValueError("Invalid Happings Autopilot checkpoint context")
    # Existing identities remain protected even if the source is disabled,
    # unavailable or its permission changes after an earlier field repair.
    unchanged, empty_evidence = source.preview(base, [], today=today)
    preserve_ids = frozenset(row["slug"] for row in base if row.get("fonte") == source.PUBLISHER)
    authenticated, rights_state, rights_digest = _rights(Path(rights_path or source.RIGHTS_REVIEW_FILE))
    report = {
        "schema": SCHEMA, "publisher": source.PUBLISHER, "date": today.isoformat(),
        "enabled": policy["enabled"], "status": "disabled",
        "rights_state": rights_state, "rights_authenticated": authenticated,
        "rights_record_sha256": rights_digest, "input_sha256": digest(base),
        "protected_existing_market_ids": len(preserve_ids),
        "protected_ids_sha256": digest(sorted(preserve_ids)),
        "selected_urls": [], "source_pages": [], "source_evidence_reused": False,
        "max_index_pages_per_run": source.MAX_REQUESTS_PER_RUN,
        "evidence": empty_evidence,
    }
    updated = unchanged
    path = Path(out) / "sources" / "happings-pages.json"
    if policy["enabled"] and not authenticated:
        report["status"] = "blocked_rights"
    elif policy["enabled"]:
        urls = source.select_pages(base, today=today)
        report["selected_urls"] = urls
        context = {
            "today": today.isoformat(), "baseline_signature": baseline_signature,
            "input_sha256": report["input_sha256"], "policy_sha256": pipeline_policy_digest,
            "rights_sha256": rights_digest, "selected_urls": urls,
        }
        pages = []
        if not urls:
            report["status"] = "no_eligible_pages"
        elif resume:
            if not path.is_file():
                report["status"] = "resume_missing_evidence"
            else:
                if path.stat().st_size > MAX_CHECKPOINT_BYTES:
                    raise ValueError("Unbounded Happings resume checkpoint")
                saved = json.loads(path.read_text("utf-8"))
                pages = _unpack_pages(saved, context)
                report["source_evidence_reused"] = True
                if saved["status"] == "retrieved":
                    report["status"] = "resumed_checkpoint"
                else:
                    report["status"] = "unavailable"
                    report["retained_partial_evidence_pages"] = len(pages)
                    pages = []
        elif offline:
            report["status"] = "offline_skipped"
        else:
            pages, failure = _fetch_and_checkpoint(urls, path, context, fetcher)
            report["status"] = "unavailable" if failure else "retrieved"
            if failure:
                report["fetch_error_type"] = failure
        if pages:
            updated, report["evidence"] = source.preview(
                base, pages, today=today, apply=True, rights_verified=True
            )
            report["source_pages"] = deepcopy(report["evidence"]["source_pages"])
            changed_layouts = sum(page["status"] == "layout_changed" for page in report["source_pages"])
            if changed_layouts:
                report["status"] = ("layout_changed" if changed_layouts == len(pages)
                                    else "partial_layout_changed")
    source.safe_report(report["evidence"], base)
    verify_changes(base, updated, report)
    _write_json(Path(out) / "happings-enrichment.json", report)
    (Path(out) / "HAPPINGS_ENRICHMENT.md").write_text(markdown(report), "utf-8")
    return updated, report, preserve_ids


def verify_changes(before, after, report):
    """Independent field diff; source receipts cannot authorize other changes."""
    if (report.get("schema") != SCHEMA or report.get("publisher") != source.PUBLISHER
            or report.get("input_sha256") != digest(before)
            or [r["slug"] for r in before] != [r["slug"] for r in after]):
        raise ValueError("Happings field phase changed its baseline or market identities")
    evidence = report["evidence"]
    source.safe_report(evidence, before)
    proposals = {p["market_id"]: p for p in evidence["proposals"]}
    if len(proposals) != len(evidence["proposals"]):
        raise ValueError("Happings repeated a field proposal")
    changed = []
    for old, current in zip(before, after):
        if old == current:
            continue
        sid = old["slug"]
        fields = (set(old) ^ set(current)) | {
            key for key in set(old) | set(current) if old.get(key) != current.get(key)
        }
        receipt = proposals.get(sid)
        if (fields - {"indirizzo", "fonti"} or old.get("fonte") != source.PUBLISHER
                or str(old.get("indirizzo") or "").strip() or not receipt
                or report.get("enabled") is not True or report.get("rights_authenticated") is not True
                or receipt.get("apply_authorized") is not True
                or receipt.get("rights_gate_passed") is not True
                or receipt.get("field") != "indirizzo"
                or current.get("indirizzo") != receipt.get("candidate_value")
                or not source.allowed_url(old.get("url_fonte"), receipt.get("source_requested_url"),
                                          receipt.get("source_url"))):
            raise ValueError("Unapproved Happings market-field change: " + sid)
        links = deepcopy(old.get("fonti") or [])
        added = {"nome": source.SOURCE_EVIDENCE_NAME, "url": receipt["source_url"]}
        if added not in links:
            links.append(added)
        if current.get("fonti") != links:
            raise ValueError("Happings removed or rewrote existing source evidence: " + sid)
        changed.append(sid)
    if (sorted(changed) != evidence["changed_ids"]
            or len(changed) != evidence["field_changes"]):
        raise ValueError("Happings source report does not match actual field changes")
    return True


def verify_exported(before, revised, exported, report, *, today):
    """Check exact IDs and source-proven values in the actual exported details."""
    verify_changes(before, revised, report)
    original_ids = [row["slug"] for row in before]
    protected = {row["slug"] for row in before if row.get("fonte") == source.PUBLISHER}
    by_id = {row["slug"]: row for row in exported}
    exported_publisher_ids = {row["slug"] for row in exported
                              if row.get("fonte") == source.PUBLISHER}
    if (len(set(original_ids)) != len(original_ids) or len(by_id) != len(exported)
            or exported_publisher_ids != protected or not protected <= by_id.keys()):
        raise ValueError("Happings export lost, added or duplicated original market IDs")
    for row in revised:
        if row["slug"] not in protected:
            # Other sources retain their existing normalization, duplicate
            # handling and release gates. This phase cannot replace them.
            continue
        expected, error = normalize(row, today)
        if error or expected != by_id[row["slug"]]:
            raise ValueError("Happings final catalog differs from its proved fields: " + row["slug"])
    return {
        "schema": SCHEMA, "release_safe": True, "checked_market_ids": len(protected),
        "input_market_ids": len(before), "exported_market_ids": len(exported),
        "protected_happings_ids": report["protected_existing_market_ids"],
        "source_field_changes": report["evidence"]["field_changes"],
        "market_ids_deleted": len(set(original_ids) - by_id.keys()),
        "market_ids_added": len(by_id.keys() - set(original_ids)),
        "happings_ids_deleted": 0, "happings_ids_added": 0,
        "unapproved_field_changes": 0, "opening_verifications_created": 0,
    }


def markdown(report):
    evidence = report["evidence"]
    return (
        "# Happings — arricchimento nel ciclo DEV\n\n"
        f"- Stato: `{report['status']}`.\n"
        f"- Gate diritti: `{report['rights_state']}`.\n"
        f"- Identità Happings conservate: {report['protected_existing_market_ids']}.\n"
        f"- Pagine valutate: {evidence['pages_evaluated']} (limite: {source.MAX_REQUESTS_PER_RUN}).\n"
        f"- Indirizzi aggiunti: {evidence['field_changes']}.\n"
        "- Nessun orario, data, punto geografico o verifica di apertura aggiunto.\n"
        "- HTML e prove per scheda restano nei checkpoint temporanei del ciclo.\n"
    )
