"""Bounded Happings phase for the existing DEV Autopilot.

The policy is disabled by default. Fetching and applying fields require an
explicit project instruction or an authenticated publisher grant. These are
reported separately. Raw responses stay in the temporary checkpoint directory.
"""
from __future__ import annotations

import base64
import hashlib
import json
import re
from copy import deepcopy
from datetime import date
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError

import happings_source_enrichment as source
from export_static import normalize
import happings_detail_autopilot as details
import happings_legacy_resources as legacy

SCHEMA = 1
DEFAULT_POLICY = {"enabled": False}
MAX_CHECKPOINT_BYTES = source.MAX_REQUESTS_PER_RUN * source.MAX_RESPONSE_BYTES * 2 + 50_000


def digest(value):
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, ensure_ascii=False, separators=(",", ":")
    ).encode("utf-8")).hexdigest()


def validate_policy(policy):
    if (not isinstance(policy, dict) or set(policy) - {"enabled", "max_pages", "details", "legacy_resolution"}
            or type(policy.get("enabled", False)) is not bool
            or type(policy.get("max_pages", source.MAX_REQUESTS_PER_RUN)) is not int
            or not 1 <= policy.get("max_pages", source.MAX_REQUESTS_PER_RUN) <= source.MAX_REQUESTS_PER_RUN):
        raise ValueError("Unreviewed Happings Autopilot policy")
    result = {"enabled": policy.get("enabled", False),
              "max_pages": policy.get("max_pages", source.MAX_REQUESTS_PER_RUN)}
    if "details" in policy:
        result["details"] = details.validate_policy(policy["details"])
    if "legacy_resolution" in policy:
        result["legacy_resolution"] = legacy.validate_policy(policy["legacy_resolution"])
    return result


def _write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", "utf-8")
    temporary.replace(path)


def _rights(path, *, today):
    try:
        if path.stat().st_size > 65_536:
            raise ValueError("Unbounded Happings authorization record")
        record = json.loads(path.read_text("utf-8"))
    except (OSError, UnicodeError, ValueError):
        return source.authorization_status(None, today=today), None
    return source.authorization_status(record, today=today), digest(record)


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


def _valid_page_failure(failure):
    if (not isinstance(failure, dict)
            or set(failure) not in ({"requested_url", "error_type"}, {"requested_url", "error_type", "error_code"})
            or not isinstance(failure.get("error_type"), str)
            or not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", failure["error_type"])):
        return False
    if "error_code" in failure:
        return source.valid_failure_code(failure["error_code"])
    return True


def _unpack_pages(saved, context):
    if (not isinstance(saved, dict) or saved.get("schema") != SCHEMA
            or saved.get("context") != context or not isinstance(saved.get("pages"), list)
            or len(saved["pages"]) > source.MAX_REQUESTS_PER_RUN
            or saved.get("status") not in ("fetch_started", "retrieved", "partial_unavailable", "unavailable")):
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
    if [page["requested_url"] for page in pages] != [url for url in context["selected_urls"] if url in seen]:
        raise ValueError("Happings checkpoint changed selected source order")
    failures = saved.get("failures", [])
    if not isinstance(failures, list) or len(failures) > len(context["selected_urls"]):
        raise ValueError("Happings checkpoint lost failed page outcomes")
    failed = set()
    for failure in failures:
        if (not _valid_page_failure(failure)
                or failure.get("requested_url") not in context["selected_urls"]
                or failure["requested_url"] in seen | failed):
            raise ValueError("Happings checkpoint lost failed page identity")
        failed.add(failure["requested_url"])
    if [item["requested_url"] for item in failures] != [url for url in context["selected_urls"] if url in failed]:
        raise ValueError("Happings checkpoint changed failed source order")
    if (saved["status"] == "retrieved"
            and (failures or [page["requested_url"] for page in pages] != context["selected_urls"])):
        raise ValueError("Happings completed checkpoint lost selected source pages")
    if (saved["status"] in {"partial_unavailable", "unavailable"}
            and (seen | failed != set(context["selected_urls"])
                 or (saved["status"] == "partial_unavailable" and (not pages or not failures))
                 or (saved["status"] == "unavailable" and bool(pages)))):
        raise ValueError("Happings failed checkpoint lost selected source outcomes")
    return pages


def _fetch_and_checkpoint(urls, path, context, fetcher=None, *, robots=None, robots_error=None):
    """Keep every completed page even if a later request fails or is interrupted."""
    failures = []
    saved = {"schema": SCHEMA, "context": context, "status": "fetch_started", "pages": [],
             "failures": failures}
    _write_json(path, saved)
    attempted = set()

    def capture(url, **kwargs):
        if url not in urls or url in attempted:
            raise ValueError("Happings repeated or unselected request")
        attempted.add(url)
        raw, final = source._fetch_one(url, **kwargs)
        page = _pack_page({"requested_url": url, "final_url": final, "html": raw})
        saved["pages"].append(page)
        _write_json(path, saved)
        return raw, final

    try:
        if robots_error:
            raise ValueError("Publisher robots unavailable during legacy resource resolution")
        if fetcher is None:
            shared = {"robots": robots} if robots is not None else {}
            pages = source.fetch_pages(list(urls), permission_confirmed=True, page_fetch=capture,
                                       failures=failures, **shared)
        else:
            pages = fetcher(list(urls), permission_confirmed=True, failures=failures)
        if not isinstance(pages, list) or any(not isinstance(page, dict) for page in pages):
            raise ValueError("Happings fetch did not preserve its selected page batch")
        proposal = {**saved, "pages": [_pack_page(page) for page in pages]}
        _unpack_pages(proposal, context)
        if {page["requested_url"] for page in pages} | {item["requested_url"] for item in failures} != set(urls):
            raise ValueError("Happings fetch omitted a selected page outcome")
        saved["pages"] = proposal["pages"]
    except (OSError, HTTPError, HTTPException, ValueError) as error:
        saved["error_type"] = type(error).__name__
        # Completed, source-bound bytes remain useful if a later request
        # fails. Missing outcomes are explicit; no date or content is guessed.
        succeeded = {page["requested_url"] for page in saved["pages"]}
        known_failures = {item.get("requested_url"): item for item in failures
                          if _valid_page_failure(item) and item.get("requested_url") in urls}
        saved["failures"] = [known_failures.get(url, {"requested_url": url, "error_type": type(error).__name__})
                             for url in urls if url not in succeeded]
    saved["status"] = ("partial_unavailable" if saved["pages"] and saved["failures"]
                       else "unavailable" if saved["failures"] else "retrieved")
    pages = _unpack_pages(saved, context)
    _write_json(path, saved)
    return pages, saved


def _run_legacy(base, *, policy, out, today, context, previous_state_path=None,
                offline=False, resume=False, fetcher=None):
    """Discover resource URLs only; raw responses never become market facts here."""
    policy = legacy.validate_policy(policy)
    catalog = legacy.catalog_context(base)
    previous = None
    if previous_state_path and Path(previous_state_path).is_file():
        if Path(previous_state_path).stat().st_size > legacy.MAX_STATE_BYTES:
            raise ValueError("Unbounded persisted legacy resource frontier")
        previous = legacy.validate_state(json.loads(Path(previous_state_path).read_text("utf-8")), today=today)
    seeded = legacy.seed_state(base, state=previous, today=today, catalog=catalog)
    state = seeded
    context = {**context, "legacy_policy": policy, "initial_state_sha256": digest(seeded)}
    path = Path(out) / "sources" / "happings-legacy-pages.json"
    report = {"enabled": policy["enabled"], "status": "disabled",
              "state_before_sha256": digest(previous), "state_after_sha256": digest(state),
              "state_changed": previous != state, "available_resource_urls": [],
              "acquisition": {"requests_attempted": 0, "request_slots_used": 0,
                              "max_requests": policy["max_requests"], "max_seconds": policy["max_seconds"],
                              "elapsed_seconds": 0, "budget_stop": "not_run", "outcomes": []}}
    robots, robots_error = None, None

    def pack(captures):
        return [{**{k: v for k, v in capture.items() if k != "html"},
                 "html_base64": base64.b64encode(capture["html"]).decode("ascii")} for capture in captures]

    def checkpoint(current, acquisition, captures):
        snapshot = {**report, "status": "acquired", "acquisition": acquisition,
                    "state_after_sha256": digest(current), "state_changed": previous != current,
                    "available_resource_urls": legacy.known_resources(current, base, today=today, catalog=catalog)}
        _write_json(path, {"schema": SCHEMA, "context": context, "state": current,
                           "report": snapshot, "captures": pack(captures)})

    if policy["enabled"] and resume:
        if not path.is_file():
            report["status"] = "resume_missing_evidence"
        else:
            if path.stat().st_size > legacy.MAX_STATE_BYTES + legacy.MAX_REQUESTS * source.MAX_RESPONSE_BYTES * 2:
                raise ValueError("Unbounded legacy resource checkpoint")
            saved = json.loads(path.read_text("utf-8"))
            if (not isinstance(saved, dict) or set(saved) != {"schema", "context", "state", "report", "captures"}
                    or saved["schema"] != SCHEMA or saved["context"] != context
                    or not isinstance(saved["captures"], list) or len(saved["captures"]) > policy["max_requests"]):
                raise ValueError("Legacy resource resume context changed")
            state = legacy.validate_state(saved["state"], today=today)
            report = saved["report"]
            if (report.get("state_before_sha256") != digest(previous)
                    or report.get("state_after_sha256") != digest(state)
                    or report.get("state_changed") != (previous != state)
                    or report.get("available_resource_urls") != legacy.known_resources(state, base, today=today, catalog=catalog)
                    or report.get("acquisition", {}).get("max_requests") != policy["max_requests"]
                    or report.get("acquisition", {}).get("max_seconds") != policy["max_seconds"]
                    or type(report["acquisition"].get("request_slots_used")) is not int
                    or not 0 <= report["acquisition"]["request_slots_used"] <= policy["max_requests"]
                    or type(report["acquisition"].get("requests_attempted")) is not int
                    or not 0 <= report["acquisition"]["requests_attempted"] <= report["acquisition"]["request_slots_used"]):
                raise ValueError("Legacy resource checkpoint lost its request budget or state")
            origins = catalog["origins"]
            entries = {item["origin_url"]: item for item in state["resources"]}
            initial = {item["origin_url"]: item["proof"] for item in seeded["resources"]}
            changed = {url for url, item in entries.items() if item["proof"] != initial.get(url)}
            captured = set()
            for capture in saved["captures"]:
                if (not isinstance(capture, dict) or set(capture) != {
                        "origin_url", "requested_url", "final_url", "html_base64", "proof"}
                        or capture["origin_url"] not in changed or capture["origin_url"] in captured
                        or capture["final_url"] != capture["requested_url"]):
                    raise ValueError("Legacy checkpoint capture lost its original URL")
                try:
                    raw = base64.b64decode(capture["html_base64"], validate=True)
                except (TypeError, ValueError):
                    raise ValueError("Invalid legacy checkpoint HTML") from None
                entry = entries[capture["origin_url"]]
                proof, status = legacy.prove_resource(entry, capture["requested_url"], raw,
                                                      origins.get(capture["origin_url"], []), today=today)
                if status != "resolved" or proof != capture["proof"] or proof != entry["proof"]:
                    raise ValueError("Legacy resource proof is not bound to its captured HTML")
                captured.add(capture["origin_url"])
            if captured != changed:
                raise ValueError("Legacy checkpoint has an uncaptured resource success")
            report["status"] = "resumed_checkpoint"
    elif policy["enabled"] and offline:
        report["status"] = "offline_skipped"
    elif policy["enabled"]:
        if not legacy.pending_origins(state, base, today=today, catalog=catalog):
            report["status"] = "no_pending_legacy"
        else:
            try:
                robots = source.robots_allowed()
            except (OSError, HTTPException, ValueError) as error:
                robots_error = type(error).__name__
                report.update(status="robots_unavailable", error_type=robots_error)
            if robots is not None:
                arguments = {"fetcher": fetcher} if fetcher is not None else {}
                state, acquisition, captures = legacy.acquire(
                    base, state, today=today, robots=robots, max_requests=policy["max_requests"],
                    max_seconds=policy["max_seconds"], checkpoint=checkpoint, catalog=catalog, **arguments)
                report.update(status="acquired", acquisition=acquisition)
                checkpoint(state, acquisition, captures)
    report.update(state_after_sha256=digest(state), state_changed=previous != state,
                  available_resource_urls=legacy.known_resources(state, base, today=today, catalog=catalog),
                  pending_origin_urls=legacy.pending_origins(state, base, today=today, catalog=catalog),
                  known_origin_urls=len(state["resources"]))
    report["identity_unproven_rows"] = sum(not source._town_url_matches(row)
                                            for rows in catalog["origins"].values() for row in rows)
    _write_json(Path(out) / legacy.STATE_FILENAME, state)
    _write_json(Path(out) / "happings-legacy-resolution.json", report)
    return state, report, robots, robots_error


def _run_weekly(base, *, policy, out, today, baseline_signature, pipeline_policy_digest,
        offline=False, resume=False, rights_path=None, fetcher=None,
        legacy_state_path=None, legacy_fetcher=None):
    """Return (candidate rows, bounded evidence report, IDs export must retain)."""
    policy = validate_policy(policy)
    if (not isinstance(today, date) or type(offline) is not bool or type(resume) is not bool
            or not isinstance(baseline_signature, str) or not baseline_signature
            or not isinstance(pipeline_policy_digest, str) or not pipeline_policy_digest):
        raise ValueError("Invalid Happings Autopilot checkpoint context")
    # Existing identities remain protected even if the source is disabled,
    # unavailable or its permission changes after an earlier field repair.
    unchanged, empty_evidence = source.preview(base, [], today=today)
    publisher_ids = frozenset(row["slug"] for row in base if row.get("fonte") == source.PUBLISHER)
    preserve_ids = frozenset(row["slug"] for row in base)
    authorization, rights_digest = _rights(Path(rights_path or source.RIGHTS_REVIEW_FILE), today=today)
    report = {
        "schema": SCHEMA, "publisher": source.PUBLISHER, "date": today.isoformat(),
        "enabled": policy["enabled"], "status": "disabled",
        "rights_state": authorization["status"],
        "rights_authenticated": authorization["rights_authenticated"],
        "fetch_authorized": authorization["authorized"],
        "authorization_basis": authorization["basis"],
        "rights_record_sha256": rights_digest, "input_sha256": digest(base),
        "protected_existing_market_ids": len(publisher_ids),
        "protected_ids_sha256": digest(sorted(publisher_ids)),
        "protected_catalog_market_ids": len(preserve_ids),
        "protected_catalog_ids_sha256": digest(sorted(preserve_ids)),
        "selected_urls": [], "source_pages": [], "page_failures": [], "source_evidence_reused": False,
        "max_index_pages_per_run": policy["max_pages"],
        "evidence": empty_evidence,
    }
    updated = unchanged
    path = Path(out) / "sources" / "happings-pages.json"
    if policy["enabled"] and not authorization["authorized"]:
        report["status"] = "blocked_rights"
    elif policy["enabled"]:
        resource_urls, robots, robots_error, consumed = [], None, None, 0
        legacy_policy = policy.get("legacy_resolution", legacy.DEFAULT_POLICY)
        if legacy_policy["enabled"]:
            bounded_policy = {**legacy_policy, "max_requests": min(legacy_policy["max_requests"], policy["max_pages"])}
            _, report["legacy_resolution"], robots, robots_error = _run_legacy(
                base, policy=bounded_policy, out=out, today=today,
                context={"today": today.isoformat(), "baseline_signature": baseline_signature,
                         "input_sha256": report["input_sha256"], "policy_sha256": pipeline_policy_digest,
                         "rights_sha256": rights_digest}, previous_state_path=legacy_state_path,
                offline=offline, resume=resume, fetcher=legacy_fetcher)
            resource_urls = report["legacy_resolution"]["available_resource_urls"]
            consumed = report["legacy_resolution"]["acquisition"]["request_slots_used"]
        remaining = policy["max_pages"] - consumed
        urls = source.select_pages(base, today=today, limit=remaining, resource_urls=resource_urls) if remaining else []
        report["legacy_request_slots_used"] = consumed
        report["remaining_index_page_budget"] = remaining
        report["selected_urls"] = urls
        context = {
            "today": today.isoformat(), "baseline_signature": baseline_signature,
            "input_sha256": report["input_sha256"], "policy_sha256": pipeline_policy_digest,
            "rights_sha256": rights_digest, "selected_urls": urls,
        }
        if "legacy_resolution" in report:
            context["legacy_state_sha256"] = report["legacy_resolution"]["state_after_sha256"]
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
                succeeded = {page["requested_url"] for page in pages}
                failed = {item["requested_url"]: item for item in saved.get("failures", [])}
                report["page_failures"] = [failed.get(url, {"requested_url": url, "error_type": "InterruptedBatch"})
                                           for url in urls if url not in succeeded]
                if not report["page_failures"]:
                    report["status"] = "resumed_checkpoint"
                else:
                    report["status"] = "partial_unavailable" if pages else "unavailable"
                    report["retained_partial_evidence_pages"] = len(pages)
        elif offline:
            report["status"] = "offline_skipped"
        else:
            pages, saved = _fetch_and_checkpoint(urls, path, context, fetcher,
                                                 robots=robots, robots_error=robots_error)
            report["status"] = saved["status"]
            report["page_failures"] = deepcopy(saved["failures"])
            if saved.get("error_type"):
                report["fetch_error_type"] = saved["error_type"]
            if pages and saved["failures"]:
                report["retained_partial_evidence_pages"] = len(pages)
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


def _verify_weekly_changes(before, after, report):
    """Independent field diff; source receipts cannot authorize other changes."""
    if (report.get("schema") != SCHEMA or report.get("publisher") != source.PUBLISHER
            or report.get("input_sha256") != digest(before)
            or report.get("protected_catalog_market_ids") != len(before)
            or report.get("protected_catalog_ids_sha256") != digest(sorted(r["slug"] for r in before))
            or report.get("protected_existing_market_ids") != sum(r.get("fonte") == source.PUBLISHER for r in before)
            or report.get("protected_ids_sha256") != digest(sorted(
                r["slug"] for r in before if r.get("fonte") == source.PUBLISHER))
            or [r["slug"] for r in before] != [r["slug"] for r in after]):
        raise ValueError("Happings field phase changed its baseline or market identities")
    consumed = report.get("legacy_request_slots_used", 0)
    maximum = report.get("max_index_pages_per_run")
    if (type(consumed) is not int or not 0 <= consumed <= legacy.MAX_REQUESTS
            or type(maximum) is not int or not 1 <= maximum <= source.MAX_REQUESTS_PER_RUN
            or len(report.get("selected_urls", [])) + consumed > maximum
            or ("legacy_resolution" in report and consumed != report["legacy_resolution"]["acquisition"]["request_slots_used"])):
        raise ValueError("Legacy requests exceeded the shared Happings weekly budget")
    authorization_states = {
        "authenticated": (True, "authenticated_publisher_grant", True),
        "project_owner_authorized": (True, "explicit_project_owner_instruction", False),
        "blocked_rights": (False, None, False),
        "invalid_or_missing_rights_record": (False, None, False),
    }
    authorization = (report.get("fetch_authorized"), report.get("authorization_basis"),
                     report.get("rights_authenticated"))
    if (type(report.get("fetch_authorized")) is not bool
            or type(report.get("rights_authenticated")) is not bool
            or authorization_states.get(report.get("rights_state")) != authorization
            or (report["fetch_authorized"] and
                (not isinstance(report.get("rights_record_sha256"), str)
                 or not re.fullmatch(r"[0-9a-f]{64}", report["rights_record_sha256"])))):
        raise ValueError("Happings report misstates its actual authorization basis")
    evidence = report["evidence"]
    source.safe_report(evidence, before)
    if (evidence.get("date") != report.get("date")
            or report.get("source_pages") != evidence.get("source_pages")
            or any(page["requested_url"] not in report.get("selected_urls", [])
                   for page in evidence.get("source_pages", []))):
        raise ValueError("Happings report changed the selected page or observation date")
    proposals = {p["market_id"]: p for p in evidence["proposals"]}
    observations = {p["market_id"]: p for p in evidence["observations"]}
    retirements = {p["market_id"]: p for p in evidence["retirements"]}
    if (len(proposals) != len(evidence["proposals"])
            or len(observations) != len(evidence["observations"])
            or len(retirements) != len(evidence["retirements"])):
        raise ValueError("Happings repeated a field proposal or observation")
    observed_on = date.fromisoformat(report["date"])
    changed, address_changed = [], []
    for old, current in zip(before, after):
        sid = old["slug"]
        receipt = proposals.get(sid)
        observation = observations.get(sid)
        retirement = retirements.get(sid)
        expected = source.expected_record(old, proposal=receipt, observation=observation,
                                          retirement=retirement, today=observed_on)
        if expected != current:
            raise ValueError("Unapproved Happings market-field change: " + sid)
        if old == current:
            continue
        fields = (set(old) ^ set(current)) | {
            key for key in set(old) | set(current) if old.get(key) != current.get(key)
        }
        proof = observation or retirement
        allowed = ({"riscontri_campi"} if retirement else {"fonti", "riscontri_campi"}
                   if old.get("fonte") != source.PUBLISHER else {"indirizzo", "fonti", "riscontri_campi"})
        if (fields - allowed
                or report.get("enabled") is not True or report.get("fetch_authorized") is not True
                or report.get("authorization_basis") not in {
                    "explicit_project_owner_instruction", "authenticated_publisher_grant"}
                or not proof or proof.get("apply_authorized") is not True
                or source._record_relation(old, proof.get("source_requested_url"),
                                           proof.get("source_url")) != proof.get("source_relation")):
            raise ValueError("Unapproved Happings market-field change: " + sid)
        changed.append(sid)
        if old.get("indirizzo") != current.get("indirizzo"):
            if (not receipt or receipt.get("apply_authorized") is not True
                    or receipt.get("rights_gate_passed") is not True
                    or receipt.get("field") != "indirizzo"
                    or receipt.get("old_value") != str(old.get("indirizzo") or "")
                    or current.get("indirizzo") != receipt.get("candidate_value")):
                raise ValueError("Unapproved Happings address change: " + sid)
            address_changed.append(sid)
    if (sorted(address_changed) != evidence["changed_ids"]
            or len(address_changed) != evidence["field_changes"]
            or len(changed) != evidence["record_changes"]):
        raise ValueError("Happings source report does not match actual field changes")
    return True


def _weekly_rows(before, report):
    evidence = report["evidence"]
    proposals = {p["market_id"]: p for p in evidence["proposals"]}
    observations = {p["market_id"]: p for p in evidence["observations"]}
    retirements = {p["market_id"]: p for p in evidence["retirements"]}
    day = date.fromisoformat(report["date"])
    return [source.expected_record(row, proposal=proposals.get(row["slug"]),
                                   observation=observations.get(row["slug"]),
                                   retirement=retirements.get(row["slug"]), today=day)
            for row in before]


def run(base, *, policy, out, today, baseline_signature, pipeline_policy_digest,
        offline=False, resume=False, rights_path=None, fetcher=None,
        detail_fetcher=None, detail_state_path=None, detail_bootstrap=details.BOOTSTRAP,
        legacy_state_path=None, legacy_fetcher=None):
    """Run existing weekly repairs, then the source-bound detail mechanism."""
    policy = validate_policy(policy)
    updated, report, preserve_ids = _run_weekly(
        base, policy={key: policy[key] for key in ("enabled", "max_pages", "legacy_resolution") if key in policy},
        out=out, today=today, baseline_signature=baseline_signature,
        pipeline_policy_digest=pipeline_policy_digest, offline=offline, resume=resume,
        rights_path=rights_path, fetcher=fetcher, legacy_state_path=legacy_state_path,
        legacy_fetcher=legacy_fetcher)
    detail_policy = policy.get("details", details.DEFAULT_POLICY)
    if detail_policy["enabled"] and policy["enabled"] and report["fetch_authorized"]:
        updated, report["details"], state = details.run(
            updated, policy=detail_policy, out=out, today=today,
            baseline_signature=baseline_signature, pipeline_policy_digest=pipeline_policy_digest,
            previous_state_path=detail_state_path, offline=offline, resume=resume,
            fetcher=detail_fetcher, bootstrap=detail_bootstrap)
        new_ids = report["details"]["evidence"]["new_market_ids"]
        preserve_ids = preserve_ids | frozenset(new_ids)
        report["output_market_ids"] = len(updated)
        report["output_ids_sha256"] = digest(sorted(row["slug"] for row in updated))
        report["details_enabled"] = True
        report["detail_state_changed"] = report["details"]["state_changed"]
        verify_changes(base, updated, report)
        _write_json(Path(out) / "happings-enrichment.json", report)
        (Path(out) / "HAPPINGS_ENRICHMENT.md").write_text(markdown(report), "utf-8")
    return updated, report, preserve_ids


def verify_changes(before, after, report):
    if "details" not in report:
        return _verify_weekly_changes(before, after, report)
    if report.get("enabled") is not True or report.get("fetch_authorized") is not True:
        raise ValueError("Happings details lack the active project authorization")
    weekly_rows = _weekly_rows(before, report)
    _verify_weekly_changes(before, weekly_rows, report)
    if (report.get("output_market_ids") != len(after)
            or report.get("output_ids_sha256") != digest(sorted(row["slug"] for row in after))):
        raise ValueError("Happings details changed the certified identity set")
    return details.verify_changes(weekly_rows, after, report["details"],
                                  today=date.fromisoformat(report["date"]))


def verify_exported(before, revised, exported, report, *, today):
    """Check exact IDs and source-proven values in the actual exported details."""
    if not isinstance(today, date) or report.get("date") != today.isoformat():
        raise ValueError("Happings export changed its observation reference date")
    verify_changes(before, revised, report)
    original_ids = [row["slug"] for row in before]
    protected = set(original_ids)
    publisher_ids = {row["slug"] for row in before if row.get("fonte") == source.PUBLISHER}
    by_id = {row["slug"]: row for row in exported}
    exported_publisher_ids = {row["slug"] for row in exported
                              if row.get("fonte") == source.PUBLISHER}
    added = set(report.get("details", {}).get("evidence", {}).get("new_market_ids", []))
    if (len(set(original_ids)) != len(original_ids) or len(by_id) != len(exported)
            or added & protected or exported_publisher_ids != publisher_ids | added
            or protected | added != by_id.keys()):
        raise ValueError("Happings export lost, added or duplicated original market IDs")
    for row in revised:
        expected, error = normalize(row, today)
        if error or expected != by_id[row["slug"]]:
            raise ValueError("Happings final catalog differs from its proved fields: " + row["slug"])
    return {
        "schema": SCHEMA, "release_safe": True, "checked_market_ids": len(protected),
        "input_market_ids": len(before), "exported_market_ids": len(exported),
        "protected_happings_ids": report["protected_existing_market_ids"],
        "protected_catalog_market_ids": report["protected_catalog_market_ids"],
        "source_field_changes": report["evidence"]["field_changes"],
        "source_observed_markets": len(report["evidence"]["observed_ids"]),
        "secondary_observed_markets": len(report["evidence"]["secondary_observed_ids"]),
        "retired_source_support_markets": len(report["evidence"]["retired_ids"]),
        "source_record_changes": report["evidence"]["record_changes"],
        "market_ids_deleted": len(set(original_ids) - by_id.keys()),
        "market_ids_added": len(by_id.keys() - set(original_ids)),
        "happings_ids_deleted": 0, "happings_ids_added": len(added),
        "detail_pages_evaluated": len(report.get("details", {}).get("source_pages", [])),
        "unapproved_field_changes": 0, "opening_verifications_created": 0,
    }


def markdown(report):
    evidence = report["evidence"]
    result = (
        "# Happings — arricchimento nel ciclo DEV\n\n"
        f"- Stato: `{report['status']}`.\n"
        f"- Autorizzazione operativa: `{report['rights_state']}`.\n"
        f"- Concessione del titolare autenticata: {'sì' if report['rights_authenticated'] else 'no'}.\n"
        f"- Identità Happings conservate: {report['protected_existing_market_ids']}.\n"
        f"- Identità del catalogo conservate: {report['protected_catalog_market_ids']}.\n"
        f"- Pagine valutate: {evidence['pages_evaluated']} (limite: {report['max_index_pages_per_run']}).\n"
        f"- Pagine non disponibili: {len(report['page_failures'])}.\n"
        f"- Indirizzi recuperati o aggiornati: {evidence['field_changes']}.\n"
        f"- Schede con riscontri della fonte: {len(evidence['observed_ids'])}.\n"
        f"- Riscontri su schede di altre origini: {len(evidence['secondary_observed_ids'])}.\n"
        f"- Vecchi riscontri della fonte ritirati dopo una nuova prova discordante: {len(evidence['retired_ids'])}.\n"
        "- Gli elenchi provinciali aggiornano sedi e riscontri; le date esplicite appartengono al lettore dei dettagli.\n"
        "- I riscontri essenziali sono conservati con la scheda; HTML e rapporto dettagliato restano nei checkpoint temporanei.\n"
    )
    if "legacy_resolution" in report:
        legacy_report = report["legacy_resolution"]
        result += (
            "\n## Collegamenti comunali storici\n\n"
            f"- Stato: `{legacy_report['status']}`.\n"
            f"- URL di origine tracciati: {legacy_report['known_origin_urls']}.\n"
            f"- Risorse provinciali osservate: {len(legacy_report['available_resource_urls'])}.\n"
            f"- URL in attesa di lettura: {len(legacy_report['pending_origin_urls'])}.\n"
            f"- Schede con identità comunale ancora da provare: {legacy_report['identity_unproven_rows']}.\n"
            f"- Richieste HTTP: {legacy_report['acquisition']['requests_attempted']}; "
            f"slot utilizzati nel budget settimanale: {legacy_report['acquisition']['request_slots_used']}.\n"
            "- Originale, risposta HTTP e canonical dichiarato restano distinti. "
            "La risoluzione non corregge identità, province o indirizzi e non conferma aperture.\n"
        )
    if "details" in report:
        detail = report["details"]
        result += (
            "\n## Schede di dettaglio\n\n"
            f"- Stato: `{detail['status']}`.\n"
            f"- Dettagli letti: {len(detail['source_pages'])}.\n"
            f"- Nuove identità ammesse: {len(detail['evidence']['new_market_ids'])}.\n"
            f"- URL di dettaglio conosciuti: {detail['discovery'].get('known_detail_urls', 0)}.\n"
            f"- Dettagli ancora da leggere: {detail['discovery'].get('pending_detail_urls', 0)}.\n"
            f"- Richieste effettuate: {detail['discovery'].get('requests_attempted', 0)}; "
            f"durata: {detail['discovery'].get('elapsed_seconds', 0)} secondi; "
            f"fine del lotto: `{detail['discovery'].get('budget_stop', 'not_run')}`.\n"
            "- Indirizzi, orari, singole date ed eccezioni conservano la prova della fonte.\n"
            "- Date riportate dalla fonte; nessuna verifica umana o previsione oltre il calendario pubblicato.\n"
        )
    return result
