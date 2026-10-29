"""Observed Happings details in the existing DEV cycle, with durable progress.

The frontier contains URLs and transport history, never an inferred market.
Only a parsed, reconciled detail can update a field or admit a distinct venue.
Raw HTML is compressed in the temporary run checkpoint; no login, browser,
paid service, or additional scheduled job is needed.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import zlib
from copy import deepcopy
from datetime import date, datetime, timedelta
from http.client import HTTPException
from pathlib import Path
from urllib.error import HTTPError

import happings_detail_discovery as discovery
import happings_source_enrichment as weekly
import atomic_write

SCHEMA = 1
STATE_FILENAME = "happings-discovery.json"
BOOTSTRAP = Path(__file__).resolve().parent / "data/happings-detail-discovery-seed.json"
MAX_STATE_BYTES = 45_000_000
MAX_CHECKPOINT_BYTES = discovery.MAX_REQUESTS * weekly.MAX_RESPONSE_BYTES * 2 + MAX_STATE_BYTES
DEFAULT_POLICY = {"enabled": False, "max_requests": 128, "max_seconds": 420,
                  "admit_new": False, "max_new": 32, "home_navigation": False}


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def validate_policy(policy):
    if (not isinstance(policy, dict) or set(policy) - set(DEFAULT_POLICY)
            or type(policy.get("enabled", False)) is not bool
            or type(policy.get("admit_new", False)) is not bool
            or type(policy.get("home_navigation", False)) is not bool
            or type(policy.get("max_requests", DEFAULT_POLICY["max_requests"])) is not int
            or not 1 <= policy.get("max_requests", DEFAULT_POLICY["max_requests"]) <= discovery.MAX_REQUESTS
            or type(policy.get("max_seconds", DEFAULT_POLICY["max_seconds"])) is not int
            or not 1 <= policy.get("max_seconds", DEFAULT_POLICY["max_seconds"]) <= discovery.MAX_SECONDS
            or type(policy.get("max_new", 32)) is not int
            or not 1 <= policy.get("max_new", 32) <= 32):
        raise ValueError("Unreviewed Happings detail policy")
    return {**DEFAULT_POLICY, **policy}


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", "utf-8")
    atomic_write.replace(temporary, path)


def load_state(path, *, today, bootstrap=BOOTSTRAP):
    """A persisted frontier is authoritative; corrupt state is never reset."""
    path = Path(path) if path is not None else None
    if path is not None and path.is_file():
        if path.stat().st_size > MAX_STATE_BYTES:
            raise ValueError("Happings discovery state exceeds the size limit")
        state = json.loads(path.read_text("utf-8"))
        return discovery.validate_state(state, today=today), "persisted"
    if bootstrap is not None and Path(bootstrap).is_file():
        if Path(bootstrap).stat().st_size > MAX_STATE_BYTES:
            raise ValueError("Happings initial inventory exceeds the size limit")
        state = json.loads(Path(bootstrap).read_text("utf-8"))
        discovery.validate_state(state)
        # Historical replays cannot claim observations made after their date.
        if all(r["discovered_at"] <= today.isoformat() for r in state["resources"].values()):
            return discovery.validate_state(state, today=today), "observed_bootstrap"
    return discovery.empty_state(), "empty"


def _page_metadata(page, *, today):
    requested, final = page.get("requested_url"), page.get("final_url")
    raw, fetched = page.get("html"), page.get("fetched_at")
    try:
        stamp = datetime.fromisoformat(fetched)
    except (ValueError, TypeError):
        raise ValueError("Detail checkpoint lost its actual acquisition time") from None
    if (discovery.url_kind(requested) != "detail" or final != requested
            or not isinstance(raw, bytes) or not 12 <= len(raw) <= weekly.MAX_RESPONSE_BYTES
            or stamp.tzinfo is None or stamp.utcoffset() != timedelta(0) or stamp.date() != today):
        raise ValueError("Untrusted Happings detail checkpoint page")
    return {"requested_url": requested, "final_url": final, "fetched_at": fetched,
            "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _pack(page, *, today):
    return {**_page_metadata(page, today=today),
            "html_gzip_base64": base64.b64encode(gzip.compress(page["html"], mtime=0)).decode("ascii")}


def _unpack(saved, context, *, today, max_requests):
    if (not isinstance(saved, dict) or saved.get("schema") != SCHEMA
            or saved.get("context") != context
            or saved.get("status") not in {"running", "completed"}
            or not isinstance(saved.get("pages"), list)
            or len(saved["pages"]) > max_requests
            or not isinstance(saved.get("discovery"), dict)):
        raise ValueError("Happings detail resume context changed")
    state = discovery.validate_state(saved.get("state"), today=today)
    acquisition = saved["discovery"]
    outcomes = acquisition.get("outcomes")
    inflight = acquisition.get("inflight")
    if (acquisition.get("max_requests") != max_requests
            or acquisition.get("max_seconds") != context["details_policy"]["max_seconds"]
            or not isinstance(outcomes, list) or len(outcomes) > max_requests
            or inflight is not None and not isinstance(inflight, dict)
            or saved["status"] == "completed" and inflight is not None
            or len(outcomes) + int(inflight is not None) > max_requests):
        raise ValueError("Happings detail checkpoint changed its request or duration budget")
    outcome_urls, successful_details = set(), {}
    attempted = 0
    for outcome in outcomes + ([inflight] if inflight is not None else []):
        url = outcome.get("requested_url")
        resource = state["resources"].get(url)
        if (not resource or url in outcome_urls or discovery.url_kind(url) != outcome.get("kind")
                or type(outcome.get("network_attempted")) is not bool
                or resource["last_attempt"] != today.isoformat()):
            raise ValueError("Happings detail checkpoint changed its request identities")
        outcome_urls.add(url)
        attempted += int(outcome["network_attempted"])
        if outcome is inflight:
            if resource["status"] != "fetching" or outcome.get("status") is not None:
                raise ValueError("Happings detail pending request lost its frontier state")
            continue
        if outcome.get("status") != resource["status"] or outcome.get("status") not in {
                "retrieved", "unavailable", "robots_denied"}:
            raise ValueError("Happings detail checkpoint changed a request outcome")
        if outcome["status"] == "retrieved":
            if (outcome["network_attempted"] is not True or outcome.get("final_url") != url
                    or outcome.get("sha256") != resource["last_sha256"]
                    or outcome.get("fetched_at") != resource["last_success_at"]
                    or resource["last_success"] != today.isoformat()
                    or type(outcome.get("bytes")) is not int
                    or not 12 <= outcome["bytes"] <= weekly.MAX_RESPONSE_BYTES):
                raise ValueError("Happings detail acquired response lost its provenance")
            if outcome["kind"] == "detail":
                successful_details[url] = outcome
        elif outcome.get("error_type") != resource["last_error"]:
            raise ValueError("Happings detail failure lost its cause")
    if (acquisition.get("requests_attempted") != attempted
            or acquisition.get("details_read") != len(successful_details)
            or acquisition.get("sitemaps_read") != sum(
                o.get("kind") == "sitemap" and o.get("status") == "retrieved" for o in outcomes)):
        raise ValueError("Happings detail checkpoint changed its acquisition counts")
    pages, seen = [], set()
    for entry in saved["pages"]:
        if (not isinstance(entry, dict) or set(entry) != {
                "requested_url", "final_url", "fetched_at", "bytes", "sha256", "html_gzip_base64"}
                or type(entry["bytes"]) is not int):
            raise ValueError("Invalid Happings detail checkpoint entry")
        try:
            zipped = base64.b64decode(entry["html_gzip_base64"], validate=True)
            with gzip.GzipFile(fileobj=io.BytesIO(zipped)) as stream:
                raw = stream.read(weekly.MAX_RESPONSE_BYTES + 1)
        except (KeyError, TypeError, ValueError, OSError, EOFError, zlib.error):
            raise ValueError("Invalid compressed Happings detail evidence") from None
        page = {"requested_url": entry.get("requested_url"), "final_url": entry.get("final_url"),
                "fetched_at": entry.get("fetched_at"), "html": raw}
        # Validate the decompressed evidence, irrespective of the gzip OS byte
        # or compression output chosen by the producing Python/zlib runtime.
        metadata = {k: v for k, v in entry.items() if k != "html_gzip_base64"}
        if _page_metadata(page, today=today) != metadata or entry["requested_url"] in seen:
            raise ValueError("Happings detail evidence was repeated or changed")
        resource = state["resources"].get(entry["requested_url"])
        outcome = successful_details.get(entry["requested_url"])
        if (not resource or resource["last_sha256"] != entry["sha256"]
                or resource["last_success"] != today.isoformat()
                or resource.get("last_success_at") != entry["fetched_at"]
                or not outcome or outcome["bytes"] != entry["bytes"]):
            raise ValueError("Happings detail checkpoint disagrees with its frontier")
        seen.add(entry["requested_url"])
        pages.append(page)
    if seen != set(successful_details):
        raise ValueError("Happings detail checkpoint lost successful source bytes")
    if [p["requested_url"] for p in pages] != [o["requested_url"] for o in outcomes
            if o["kind"] == "detail" and o["status"] == "retrieved"]:
        raise ValueError("Happings detail checkpoint changed the response order")
    return state, pages, deepcopy(saved["discovery"])


def _source_pages(pages):
    return [{"requested_url": p["requested_url"], "final_url": p["final_url"],
             "fetched_at": p["fetched_at"], "bytes": len(p["html"]),
             "sha256": hashlib.sha256(p["html"]).hexdigest()} for p in pages]


def run(base, *, policy, out, today, baseline_signature, pipeline_policy_digest,
        previous_state_path=None, offline=False, resume=False, fetcher=None,
        bootstrap=BOOTSTRAP):
    """Return (candidate, report, frontier); caller has already authorized DEV."""
    from happings_detail_enrichment import preview

    policy = validate_policy(policy)
    if (type(today) is not date or type(offline) is not bool or type(resume) is not bool
            or not isinstance(baseline_signature, str) or not baseline_signature
            or not isinstance(pipeline_policy_digest, str) or not pipeline_policy_digest):
        raise ValueError("Invalid Happings detail run context")
    state, origin = load_state(previous_state_path, today=today, bootstrap=bootstrap)
    report = {"schema": SCHEMA, "publisher": weekly.PUBLISHER, "date": today.isoformat(),
              "enabled": policy["enabled"], "status": "disabled", "policy": policy,
              "input_sha256": digest(base), "state_origin": origin,
              "state_before_sha256": digest(state), "source_pages": [],
              "source_evidence_reused": False, "discovery": {}, "evidence": {},
              "robots_requests": 0}
    context = {"date": today.isoformat(), "baseline_signature": baseline_signature,
               "policy_sha256": pipeline_policy_digest, "input_sha256": digest(base),
               "state_sha256": digest(state), "details_policy": policy}
    checkpoint_path = Path(out) / "sources/happings-detail-pages.json"
    pages = []
    if policy["enabled"] and resume:
        if not checkpoint_path.is_file():
            report["status"] = "resume_missing_evidence"
        else:
            if checkpoint_path.stat().st_size > MAX_CHECKPOINT_BYTES:
                raise ValueError("Unbounded Happings detail checkpoint")
            saved = json.loads(checkpoint_path.read_text("utf-8"))
            state, pages, report["discovery"] = _unpack(
                saved, context, today=today, max_requests=policy["max_requests"])
            report["source_evidence_reused"] = True
            report["status"] = ("resumed_checkpoint" if saved["status"] == "completed"
                                else "resumed_partial_checkpoint")
    elif policy["enabled"] and offline:
        report["status"] = "offline_skipped"
    elif policy["enabled"]:
        robot_bytes = []

        def robots_fetch(url, **kwargs):
            report["robots_requests"] += 1
            raw, final = weekly._fetch_one(url, **kwargs)
            robot_bytes.append(raw)
            return raw, final

        try:
            robots = weekly.robots_allowed(robots_fetch)
            state = discovery.seed_state(state, catalog_rows=base, observed_at=today,
                                         robots_text=robot_bytes[0].decode("utf-8-sig"), seed_home=policy["home_navigation"])

            def checkpoint(current_state, current_pages, current_report):
                write_json(checkpoint_path, {
                    "schema": SCHEMA, "context": context, "status": "running",
                    "state": current_state, "pages": [_pack(p, today=today) for p in current_pages],
                    "discovery": current_report,
                })

            state, pages, report["discovery"] = discovery.acquire(
                state, today=today, max_requests=policy["max_requests"], robots=robots,
                fetcher=fetcher, checkpoint=checkpoint, max_seconds=policy["max_seconds"])
            write_json(checkpoint_path, {
                "schema": SCHEMA, "context": context, "status": "completed", "state": state,
                "pages": [_pack(p, today=today) for p in pages], "discovery": report["discovery"],
            })
            outcomes = report["discovery"].get("outcomes", [])
            failures = any(x.get("status") != "retrieved" for x in outcomes)
            report["status"] = ("partial_unavailable" if failures and pages else "unavailable"
                                if failures else "retrieved" if pages else "discovery_only")
        except (OSError, HTTPError, HTTPException, ValueError) as error:
            # A failed source cannot delete a saved venue or invent a retry.
            report["status"] = "unavailable"
            report["error_type"] = type(error).__name__
            if checkpoint_path.is_file():
                saved = json.loads(checkpoint_path.read_text("utf-8"))
                state, pages, report["discovery"] = _unpack(
                    saved, context, today=today, max_requests=policy["max_requests"])
                if pages:
                    report["status"] = "partial_unavailable"
    after, evidence = preview(base, pages, today=today, apply=policy["enabled"],
                              admit_new=policy["admit_new"], max_new=policy["max_new"])
    report["evidence"] = evidence
    report["source_pages"] = _source_pages(pages)
    report["state_after_sha256"] = digest(state)
    report["state_changed"] = report["state_before_sha256"] != report["state_after_sha256"]
    report["output_sha256"] = digest(after)
    verify_changes(base, after, report, today=today)
    write_json(Path(out) / "happings-details.json", report)
    write_json(Path(out) / STATE_FILENAME, state)
    return after, report, state


def verify_changes(before, after, report, *, today):
    from happings_detail_enrichment import verify_changes as verify_detail_changes

    if (report.get("schema") != SCHEMA or report.get("publisher") != weekly.PUBLISHER
            or report.get("date") != today.isoformat()
            or report.get("input_sha256") != digest(before)
            or report.get("output_sha256") != digest(after)
            or type(report.get("enabled")) is not bool):
        raise ValueError("Happings detail phase changed its context")
    policy = validate_policy(report.get("policy"))
    if report["enabled"] != policy["enabled"] or (not policy["enabled"] and before != after):
        raise ValueError("Disabled Happings detail phase changed the catalog")
    pages = report.get("source_pages")
    if (not isinstance(pages, list) or len(pages) > policy["max_requests"]
            or len({p.get("requested_url") for p in pages}) != len(pages)):
        raise ValueError("Happings detail source page budget changed")
    for p in pages:
        if (discovery.url_kind(p.get("requested_url")) != "detail"
                or p.get("final_url") != p.get("requested_url")):
            raise ValueError("Happings detail evidence crossed source URLs")
    parsed = report["evidence"].get("source_pages")
    if not isinstance(parsed, list) or len(parsed) != len(pages):
        raise ValueError("Happings detail parse lost its acquired page set")
    for acquired, interpreted in zip(pages, parsed):
        if (interpreted.get("requested_url") != acquired["requested_url"]
                or interpreted.get("final_url") != acquired["final_url"]
                or interpreted.get("html_sha256") != acquired["sha256"]
                or interpreted.get("bytes") != acquired["bytes"]
                or interpreted.get("read_on") != today.isoformat()):
            raise ValueError("Happings detail parse changed its transport evidence")
    if (report["evidence"].get("admit_new") is not policy["admit_new"]
            or report["evidence"].get("max_new") != policy["max_new"]
            or report["evidence"].get("apply") is not policy["enabled"]):
        raise ValueError("Happings detail admission changed the run policy")
    verify_detail_changes(before, after, report["evidence"], today=today)
    return True
