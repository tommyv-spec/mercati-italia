#!/usr/bin/env python3
"""Refresh whole publisher pages through reviewed layout contracts.

There are no market IDs or field values in the source configuration. Each
selected URL is read once and compared with every eligible catalog record.
Only explicit, unique source identities can supply fields. Subsequent edits
require the exact previous evidence of a field managed by this engine.
"""
from __future__ import annotations

import base64
import hashlib
import ipaddress
import json
import math
import re
import socket
import time
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, datetime, timezone
from pathlib import Path
from http.client import HTTPException
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from urllib.request import Request, build_opener, HTTPRedirectHandler
from urllib.robotparser import RobotFileParser

from catalog_quality_report import VAGUE_ADDRESSES, key as address_key
from field_evidence import (FIELDS, as_day, clean_receipts, fingerprint, identity,
                            make_receipt, managed_update_allowed, mark_managed_fields,
                            retire_superseded_receipts, safe_url)
from official_enrichment import explicit_annual_weekday
from recurrence_refresh import explicit_rule, text_key
from publisher_page_parser import parse_page

MANAGER = "publisher_refresh"
MAX_PAGES = 12
MAX_PER_HOST = 4
MAX_BYTES = 1_000_000
USER_AGENT = "MercatiItaliaSourceRefresh/1.0"
SPECIAL = re.compile(r"\b(?:contadin\w*|agricol\w*|filiera corta|campagna amica|coldiretti|"
                     r"biologic\w*|antiquar\w*|artigian\w*|collezion\w*|vintage|usato)\b")
FARMERS = re.compile(r"\b(?:contadin\w*|agricol\w*|filiera corta|campagna amica|coldiretti)\b")


def canonical_url(value):
    if not isinstance(value, str):
        return ""
    try:
        p = urlsplit(value)
        if p.scheme not in {"https", "http"} or not p.hostname or p.username or p.password:
            return ""
        query = [(k, v) for k, v in parse_qsl(p.query, keep_blank_values=True)
                 if not k.casefold().startswith("utm_") and k.casefold() not in {"fbclid", "gclid"}]
        return urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path, urlencode(query), ""))
    except ValueError:
        return ""


def validate_contracts(config):
    if (not isinstance(config, dict) or config.get("schema") != 1 or
            config.get("publication_channel") != "dev-only" or
            not isinstance(config.get("sources"), list) or len(config["sources"]) > 200):
        raise ValueError("Invalid publisher refresh contracts")
    seen, urls = set(), set()
    for p in config["sources"]:
        if not isinstance(p, dict):
            raise ValueError("Publisher contract is not an object")
        sid, url = p.get("source_id"), p.get("url")
        if (not isinstance(sid, str) or not re.fullmatch(r"[a-z][a-z0-9-]{3,80}", sid) or
                sid in seen or not safe_url(url) or url in urls or
                p.get("parser") != "municipal-key-value-v1" or
                p.get("market_kind") not in {"ordinary", "farmers"} or
                type(p.get("enabled")) is not bool or
                not isinstance(p.get("publisher"), str) or not 1 <= len(p["publisher"]) <= 140 or
                not isinstance(p.get("region"), str) or not p["region"] or
                not re.fullmatch(r"[A-Z]{2}", str(p.get("province", ""))) or
                type(p.get("min_rows")) is not int or type(p.get("max_rows")) is not int or
                not 1 <= p["min_rows"] <= p["max_rows"] <= 300 or
                type(p.get("min_city_blocks")) is not int or
                type(p.get("max_city_blocks")) is not int or
                not 1 <= p["min_city_blocks"] <= p["max_city_blocks"] <= 150):
            raise ValueError("Unreviewed publisher layout, geography or size bounds")
        # This dispatcher cannot bypass a publisher's dedicated rights gate.
        if urlsplit(url).hostname.removeprefix("www.") == "happings.com":
            raise ValueError("Happings must use its dedicated authorized phase")
        seen.add(sid)
        urls.add(url)
    return config


def rotate_sources(profiles, today, limit=MAX_PAGES):
    if type(limit) is not int or not 1 <= limit <= MAX_PAGES:
        raise ValueError("Unbounded publisher rotation")
    groups = defaultdict(list)
    for profile in sorted((p for p in profiles if p.get("enabled")), key=lambda p: p["url"]):
        groups[urlsplit(profile["url"]).hostname].append(profile)
    if not groups:
        return []
    total = sum(map(len, groups.values()))
    days = max(math.ceil(total / limit), max(math.ceil(len(p) / MAX_PER_HOST) for p in groups.values()))
    # Construct complete daily batches, instead of advancing over URLs later
    # skipped by the host cap. Every source appears once in the cycle.
    for cycle_length in range(days, total + 1):
        batches = [[] for _ in range(cycle_length)]
        loads = [Counter() for _ in batches]
        complete = True
        for host, entries in sorted(groups.items(), key=lambda x: (-len(x[1]), x[0])):
            for profile in entries:
                options = [i for i in range(cycle_length)
                           if len(batches[i]) < limit and loads[i][host] < MAX_PER_HOST]
                if not options:
                    complete = False
                    break
                chosen = min(options, key=lambda i: (len(batches[i]), loads[i][host], i))
                batches[chosen].append(profile)
                loads[chosen][host] += 1
            if not complete:
                break
        if complete:
            return batches[today.toordinal() % cycle_length]
    raise ValueError("Publisher profiles cannot fit within bounded daily batches")


def _happings_page_reads(rows, report, today):
    """Read dispositions belong to this day and the protected source cohort.

    A fetched province page is not proof that every market on it matched.
    This helper reports acquisition only; field receipts remain separate.
    """
    from happings_source_enrichment import allowed_url
    from happings_weekly_layout import province_page_key

    added = set()
    if isinstance(report, dict) and isinstance(report.get("details"), dict):
        added = set(report["details"].get("evidence", {}).get("new_market_ids", []))
        ids = sorted(row["slug"] for row in rows)
        if (not added <= set(ids) or report.get("output_market_ids") != len(rows)
                or report.get("output_ids_sha256") != fingerprint(ids)):
            return {}, set()
    protected = sorted(row["slug"] for row in rows
                       if row.get("fonte") == "happings.com" and row["slug"] not in added)
    catalog_ids = sorted(row["slug"] for row in rows if row["slug"] not in added)
    if (not isinstance(report, dict) or report.get("schema") != 1
            or report.get("publisher") != "happings.com"
            or report.get("date") != today.isoformat()
            or report.get("enabled") is not True or report.get("fetch_authorized") is not True
            or report.get("protected_existing_market_ids") != len(protected)
            or report.get("protected_ids_sha256") != fingerprint(protected)
            or report.get("protected_catalog_market_ids") != len(catalog_ids)
            or report.get("protected_catalog_ids_sha256") != fingerprint(catalog_ids)
            or not isinstance(report.get("selected_urls"), list)
            or not isinstance(report.get("source_pages"), list)
            or not isinstance(report.get("page_failures"), list)):
        return {}, set()
    selected = {province_page_key(url) for url in report["selected_urls"]}
    if None in selected or len(selected) != len(report["selected_urls"]):
        return {}, set()
    observed = {}
    for page in report["source_pages"]:
        if not isinstance(page, dict):
            return {}, set()
        requested, final = page.get("requested_url"), page.get("final_url")
        key = province_page_key(requested)
        if (key not in selected or key in observed
                or not allowed_url(requested, requested, final)
                or not re.fullmatch(r"[0-9a-f]{64}", str(page.get("source_html_sha256", "")))
                or page.get("status") not in {"parsed", "layout_changed"}):
            return {}, set()
        observed[key] = ("layout_changed" if page["status"] == "layout_changed" else
                         "resumed_checkpoint" if report.get("source_evidence_reused") is True else "retrieved")
    for page in report["page_failures"]:
        if not isinstance(page, dict):
            return {}, set()
        key = province_page_key(page.get("requested_url"))
        if (key not in selected or key in observed or
                not re.fullmatch(r"[A-Za-z][A-Za-z0-9_]{0,79}", str(page.get("error_type", "")))):
            return {}, set()
        observed[key] = "unavailable"
    default = {"offline_skipped": "offline_skipped", "resume_missing_evidence": "resume_missing_evidence"}.get(
        report.get("status"), "not_observed")
    for key in selected:
        observed.setdefault(key, default)
    return observed, selected


def _happings_detail_reads(rows, report, today):
    """Acquisition proof for details, separate from a successful identity match."""
    from happings_detail_discovery import url_kind
    from datetime import datetime

    if (not isinstance(report, dict) or report.get("enabled") is not True
            or report.get("fetch_authorized") is not True or report.get("date") != today.isoformat()
            or not isinstance(report.get("details"), dict)):
        return {}
    detail = report["details"]
    if (detail.get("enabled") is not True or detail.get("date") != today.isoformat()
            or report.get("output_market_ids") != len(rows)
            or report.get("output_ids_sha256") != fingerprint(sorted(row["slug"] for row in rows))):
        return {}
    acquisition = detail.get("source_pages")
    parsed = detail.get("evidence", {}).get("source_pages")
    if not isinstance(acquisition, list) or not isinstance(parsed, list) or len(acquisition) != len(parsed):
        return {}
    result = {}
    for transport, content in zip(acquisition, parsed):
        url = transport.get("requested_url")
        try:
            read = datetime.fromisoformat(transport.get("fetched_at", ""))
        except (TypeError, ValueError):
            return {}
        if (url_kind(url) != "detail" or transport.get("final_url") != url or url in result
                or read.tzinfo is None or read.date() != today
                or content.get("requested_url") != url or content.get("final_url") != url
                or content.get("read_on") != today.isoformat()
                or content.get("html_sha256") != transport.get("sha256")
                or not re.fullmatch(r"[0-9a-f]{64}", str(transport.get("sha256", "")))):
            return {}
        result[url] = ("layout_changed" if content.get("status") == "layout_changed"
                       else "content_conflict" if content.get("status") == "conflict"
                       else "resumed_checkpoint" if detail.get("source_evidence_reused")
                       else "retrieved")
    for item in detail.get("discovery", {}).get("outcomes", []):
        url = item.get("requested_url")
        if url_kind(url) == "detail" and item.get("status") in {"unavailable", "robots_denied"}:
            result[url] = item["status"]
    return result


def _editorial_reader_coverage(rows, report, publisher, today):
    """Configured URL support and observed reads are separate evidence."""
    from editorial_calendar_scope import source_identity
    from eventiesagre_detail_refresh import validate_redirects
    from citynews_urls import source_identity as citynews_identity

    grouped_citynews = publisher == "citynews"

    def reviewed_identity(url):
        if grouped_citynews:
            return citynews_identity(url)
        bound = source_identity(url)
        return bound if bound and bound[0] == publisher else None

    if (not isinstance(report, dict) or report.get("schema") != 1
            or report.get("publisher") != publisher or report.get("date") != today.isoformat()
            or type(report.get("enabled")) is not bool):
        return None
    state = {"enabled": report["enabled"], "default": "not_observed", "reads": {},
             "contents": {}, "proofs": {}, "outcomes": {}, "layout_holds": set()}
    if grouped_citynews and report.get("state") is not None:
        # An observed unsupported template remains an explicit limitation on
        # later unselected/offline runs. It is never relabelled as today's read.
        from citynews_detail_refresh import validate_state
        try:
            queue = validate_state(report["state"], today=today)
            if set(queue["resources"]) != {row.get("url_fonte") for row in rows
                                           if reviewed_identity(row.get("url_fonte"))}:
                return state
            state["layout_holds"] = {url for url, item in queue["resources"].items()
                                     if item["status"] == "layout_held" and item["last_read"]}
        except (TypeError, ValueError):
            return state
    if not state["enabled"]:
        state["default"] = "disabled"
        return state
    status = report.get("status")
    if status in {"offline_skipped", "resume_missing_evidence", "robots_unavailable"}:
        state["default"] = status
        return state
    if status not in {"completed", "resumed", "running", "time_budget_exhausted"}:
        return state
    attempts, pages = report.get("attempts"), report.get("source_pages")
    holds, evidence = report.get("parse_holds", []), report.get("evidence")
    limit = 8 if grouped_citynews else 64 if publisher == "eventiesagre.it" else 16
    if (not isinstance(attempts, list) or len(attempts) > limit or not isinstance(pages, list)
            or len(pages) > len(attempts) or not isinstance(holds, list)
            or not isinstance(evidence, dict) or evidence.get("schema") != 1 or evidence.get("publisher") != publisher
            or evidence.get("date") != today.isoformat()
            or not isinstance(evidence.get("documents"), list)
            or not isinstance(evidence.get("outcomes"), list)):
        return state
    targets = {row.get("url_fonte") for row in rows if reviewed_identity(row.get("url_fonte"))}
    indexed, documents, parse_holds, acquired = {}, {}, set(), {}
    outcomes = {}
    catalog = {row["slug"]: row for row in rows}
    try:
        for attempt in attempts:
            url = attempt["url"]
            if (url not in targets or url in indexed or type(attempt.get("network_attempted")) is not bool
                    or attempt.get("status") not in {"retrieved", "layout_held", "unavailable", "robots_denied", "inflight"}
                    or attempt["status"] in {"retrieved", "layout_held"} and not attempt["network_attempted"]):
                return state
            indexed[url] = attempt
        for hold in holds:
            url = hold["url"]
            if url in parse_holds or url not in indexed or indexed[url]["status"] != "layout_held":
                return state
            parse_holds.add(url)
        for entry in evidence["documents"]:
            document = entry["parsed"]
            source = document["source"]
            url = source["requested_url"]
            bound = reviewed_identity(url)
            unsupported = grouped_citynews and document.get("status") == "unsupported"
            if (url in documents or url not in indexed or document.get("schema") != 1
                    or as_day(entry.get("read_on")) != today
                    or not bound or source.get("publisher") != bound[0]
                    or grouped_citynews and source.get("source_id") != bound[1]
                    or unsupported and url not in parse_holds
                    or not unsupported and (url in parse_holds or document.get("status") not in {"parsed", "held"})):
                return state
            documents[url] = document
        for page in pages:
            url, final = page["requested_url"], page["final_url"]
            expected, actual = reviewed_identity(url), reviewed_identity(final)
            if grouped_citynews:
                if final != url or page.get("redirects", []) != []:
                    return state
                redirected = False
            else:
                redirected = validate_redirects(url, final, page.get("redirects", []))
            if (url not in indexed or url in acquired or not expected or not actual
                    or actual[0] != expected[0]
                    or publisher == "eventiesagre.it" and actual != expected
                    or page.get("redirect_observed", False) is not redirected
                    or indexed[url]["status"] not in {"retrieved", "layout_held"}
                    or as_day(page.get("read_on")) != today
                    or type(page.get("bytes")) is not int or not 100 <= page["bytes"] <= 2_500_000
                    or not re.fullmatch(r"[0-9a-f]{64}", str(page.get("sha256") or ""))):
                return state
            document = documents.get(url)
            if document:
                source = document["source"]
                if (source.get("final_url") != final or source.get("html_sha256") != page["sha256"]
                        or source.get("bytes") != page["bytes"]):
                    return state
            elif url not in parse_holds:
                return state
            acquired[url] = page
        if (set(acquired) != {url for url, attempt in indexed.items()
                             if attempt["status"] in {"retrieved", "layout_held"}}
                or set(documents) | parse_holds != set(acquired)
                or report.get("source_pages_read") != len(acquired)
                or report.get("documents_parsed") != sum(d["status"] != "unsupported" for d in documents.values())
                or report.get("details_attempted") != len(indexed)):
            return state
        for outcome in evidence["outcomes"]:
            sid, value = outcome.get("slug"), outcome.get("status")
            row = catalog.get(sid)
            if (row is None or sid in outcomes or row.get("url_fonte") not in documents
                    or value not in {"held", "changed", "unchanged", "observed"}):
                return state
            outcomes[sid] = value
    except (KeyError, TypeError, ValueError, AttributeError):
        return state
    state["default"] = "not_selected"
    state["outcomes"] = outcomes
    for url, attempt in indexed.items():
        value = attempt["status"]
        state["reads"][url] = ("resumed_checkpoint" if value == "retrieved" and status == "resumed" else value)
        if url in acquired:
            page = acquired[url]
            state["proofs"][url] = {key: page[key] for key in ("requested_url", "final_url", "read_on", "bytes", "sha256")}
            if page.get("redirect_observed") is True:
                state["proofs"][url].update(redirect_observed=True, redirects=deepcopy(page["redirects"]))
            state["contents"][url] = documents[url]["status"] if url in documents else "layout_held"
    return state


def _roma_reader_coverage(rows, report, today):
    from source_roma_d881 import DATASET_PAGE, SOURCE_ID, parse_snapshot

    if (not isinstance(report, dict) or report.get("schema") != 1
            or report.get("source_id") != SOURCE_ID or report.get("date") != today.isoformat()
            or type(report.get("enabled")) is not bool):
        return None
    state = {"enabled": report["enabled"], "default": "not_observed", "reads": {},
             "contents": {}, "proofs": {}, "outcomes": {}}
    if not state["enabled"]:
        state["default"] = "disabled"
        return state
    status = report.get("status")
    if status in {"offline_skipped", "unavailable", "not_selected", "resume_missing_evidence"}:
        state["default"] = status
        return state
    if status not in {"retrieved", "resumed_checkpoint", "cached_snapshot"}:
        return state
    try:
        document = parse_snapshot(report.get("snapshot"), today=today)
        if document != report.get("document") or not isinstance(report.get("outcomes"), list):
            return state
        catalog = {row["slug"]: row for row in rows}
        outcomes = {}
        for outcome in report["outcomes"]:
            sid, value = outcome.get("market_id"), outcome.get("status")
            if (sid not in catalog or sid in outcomes or catalog[sid].get("url_fonte") != DATASET_PAGE
                    or value not in {"held", "enriched", "observed", "candidate"}):
                return state
            outcomes[sid] = value
    except (KeyError, TypeError, ValueError, AttributeError):
        return state
    state["outcomes"] = outcomes
    state["reads"][DATASET_PAGE] = "cached_snapshot" if document["read_on"] != today.isoformat() else status
    state["contents"][DATASET_PAGE] = "parsed_historical_inventory"
    state["proofs"][DATASET_PAGE] = {"read_on": document["read_on"],
        "metadata_sha256": document["metadata_sha256"], "csv_sha256": document["csv_sha256"],
        "resource_url": document["distribution"]["url"], "source_date_scope": "per_row_AGGIORNATO"}
    return state


def _existing_source_coverage(rows, report, today):
    """Validate the optional orchestrator report without granting new sources."""
    if (not isinstance(report, dict) or report.get("schema") != 1
            or report.get("date") != today.isoformat() or not isinstance(report.get("editorial"), dict)):
        return {}
    result = {"editorial": {}}
    for publisher in ("eventiesagre.it", "cosedicasa.com", "citynews"):
        if publisher in report["editorial"]:
            state = _editorial_reader_coverage(rows, report["editorial"][publisher], publisher, today)
            if state:
                result["editorial"][publisher] = state
    if report.get("roma") is not None:
        state = _roma_reader_coverage(rows, report["roma"], today)
        if state:
            result["roma"] = state
    return result


def _existing_reader(row, states):
    if not states:
        return None
    from editorial_calendar_scope import source_identity
    from citynews_urls import source_identity as citynews_identity
    url = row.get("url_fonte")
    if "citynews" in states["editorial"] and citynews_identity(url):
        return "citynews-detail", "citynews_existing_detail", states["editorial"]["citynews"]
    bound = source_identity(url)
    if bound and bound[0] in states["editorial"]:
        publisher = bound[0]
        label = "eventiesagre" if publisher == "eventiesagre.it" else "cosedicasa"
        return label + "-detail", label + "_existing_detail", states["editorial"][publisher]
    if states.get("roma"):
        from source_roma_d881 import DATASET_PAGE
        if (url == DATASET_PAGE and text_key(row.get("citta")) == "roma"
                and row.get("provincia") == "RM" and text_key(row.get("regione")) == "lazio"):
            return "roma-d881", "roma_d881_existing_inventory", states["roma"]
    return None


def catalog_resources(rows, config, *, official_urls=(), happings_enabled=False,
                      source_contracts=None, source_admissions=None, source_policy=(),
                      source_status=None, admissions_enabled=False, admission_report=None,
                      happings_report=None, happings_details_enabled=False, today=None,
                      existing_source_report=None):
    """Describe configured readers separately from this run's source availability.

    Admission comes from the existing exact source certificate, never from a
    discovery/license claim or a successful HTTP response. This report grants
    no permissions and says nothing about individual market verification.
    """
    from source_contract_activation import validate_admissions
    from source_contract_ingest import authorize_contract
    from source_lifecycle import digest, validate_contracts as validate_source_contracts

    today = today or date.today()
    existing_sources = _existing_source_coverage(rows, existing_source_report, today)
    happings_enabled = (happings_enabled is True and (
        happings_report is None or isinstance(happings_report, dict)
        and happings_report.get("enabled") is True and happings_report.get("fetch_authorized") is True))
    happings_details_enabled = (happings_enabled and happings_details_enabled is True
                                and (happings_report is None or
                                     happings_report.get("details", {}).get("enabled") is True))
    detail_reads = _happings_detail_reads(rows, happings_report, today) if happings_details_enabled else {}
    known = {canonical_url(p["url"]): p for p in config["sources"]}
    official = {canonical_url(u) for u in official_urls}
    policies = {p["id"]: p for p in source_policy if isinstance(p, dict) and "id" in p}
    source_status = source_status or {}
    normalized, raw = [], []
    contract_state = "missing" if source_contracts is None else "invalid"
    registry_state = "missing" if source_admissions is None else "invalid"
    approvals = None
    if source_contracts is not None:
        try:
            validate_source_contracts(source_contracts)
            normalized = source_contracts["normalized_profiles"]
            raw = source_contracts["raw_profiles"]
            contract_state = "valid"
            if source_admissions is not None:
                approvals = validate_admissions(source_contracts, source_admissions)
                registry_state = "valid"
        except (ValueError, TypeError, KeyError):
            pass
    observed_contracts = {}
    if (approvals is not None and isinstance(admission_report, dict)
            and admission_report.get("source_contract_sha256") == digest(source_contracts)
            and admission_report.get("source_registry_sha256") == digest(source_admissions)
            and admission_report.get("reference_date") == today.isoformat()
            and isinstance(admission_report.get("per_source"), dict)):
        observed_contracts = admission_report["per_source"]
    generic_routes = {}
    for profile in raw:
        sid = profile["id"]
        mode, layout = "source_contract_registry_missing", "approval_required"
        if registry_state == "invalid":
            mode = "source_contract_registry_invalid"
        elif approvals is not None:
            if sid not in approvals:
                mode = "source_contract_not_approved"
            elif admissions_enabled is not True or profile.get("enabled") is not True:
                mode, layout = "source_contract_disabled", "disabled"
            else:
                try:
                    # Reader coverage is configured capability. Runtime date
                    # proof and source availability belong to the read status.
                    authorize_contract(profile, approvals[sid], today=today)
                    mode, layout = "source_contract_active", "supported"
                except (ValueError, TypeError, KeyError):
                    mode = "source_contract_review_required"
        detail = observed_contracts.get(sid, {})
        read_status = (detail.get("source_read_mode") or detail.get("status") or "not_observed")
        if layout == "disabled":
            read_status = "disabled"
        elif layout != "supported":
            read_status = "not_observed"
        route = {"source_id": sid, "reader": "source_contract", "mode": mode,
                 "source_layout_status": layout, "source_read_status": read_status}
        for value in (profile["attribution_url"], profile["resource_url"]):
            generic_routes.setdefault(canonical_url(value), []).append(route)
    groups = defaultdict(list)
    for row in rows:
        url = canonical_url(row.get("url_fonte"))
        groups[url].append(row)
    happings_routes, secondary_routes, happings_reads, happings_selected = {}, {}, {}, set()
    if happings_enabled:
        from happings_source_enrichment import catalog_page_routes, secondary_catalog_page_routes
        from happings_weekly_layout import province_page_key

        # Reuse the fetcher's actual source routes. A host match cannot make
        # old town pages, thematic events or ambiguous geography supported.
        happings_routes = catalog_page_routes(rows)
        secondary_routes = secondary_catalog_page_routes(rows)
        happings_reads, happings_selected = _happings_page_reads(rows, happings_report, today)
    route_reads = {url: happings_reads.get(province_page_key(url),
                    "not_selected" if happings_selected else "not_observed")
                   for url in set(happings_routes.values()) | set(secondary_routes.values())}
    resource_groups = []
    for url, group in sorted(groups.items()):
        if happings_enabled and (urlsplit(url).hostname or "").removeprefix("www.") == "happings.com":
            routes = defaultdict(list)
            for row in group:
                routes[happings_routes.get(row.get("slug"), "")].append(row)
            # One saved town URL may identify namesakes in two provinces, or
            # mix proved and unproved identities. Count each route honestly.
            resource_groups.extend((url, subset, route) for route, subset in sorted(routes.items()))
        else:
            # Raw source URLs and Roma geography must remain exact even when
            # the display canonicalizer groups tracking URLs or mixed rows.
            cohorts = defaultdict(list)
            for row in group:
                route = _existing_reader(row, existing_sources)
                cohorts[route[0] if route else ""].append(row)
            resource_groups.extend((url, subset, "") for _, subset in sorted(cohorts.items()))
    resources = []
    for url, group, happings_page in resource_groups:
        host = urlsplit(url).hostname or ""
        readers = list(generic_routes.get(url, []))
        existing_reader = _existing_reader(group[0], existing_sources)
        if existing_reader:
            sid, existing_mode, state = existing_reader
            exact_url = group[0]["url_fonte"]
            enabled = state["enabled"]
            reader = {"source_id": sid, "reader": "existing_source_detail", "mode": existing_mode,
                "source_layout_status": "supported" if enabled else "disabled",
                "source_read_status": state["reads"].get(exact_url, state["default"]),
                "market_outcome_statuses": dict(Counter(state["outcomes"].get(row["slug"], "not_evaluated") for row in group))}
            if sid == "citynews-detail":
                reader["reader_configured"] = enabled
                if enabled and (exact_url in state["layout_holds"]
                                or state["contents"].get(exact_url) in {"unsupported", "layout_held"}):
                    reader["source_layout_status"] = "unsupported"
            if exact_url in state["contents"]:
                reader["source_content_status"] = state["contents"][exact_url]
            if exact_url in state["proofs"]:
                reader["source_acquisition"] = state["proofs"][exact_url]
            readers.append(reader)
        for profile in normalized:
            if (url not in {canonical_url(u) for u in profile.get("source_pages", [])}
                    and not (host in profile.get("source_hosts", []) and
                             any(str(r.get("slug", "")).startswith(profile["identity_prefix"])
                                 for r in group))):
                continue
            sid = profile["id"]
            enabled = (policies.get(sid, {}).get("enabled") is True
                       and policies.get(sid, {}).get("official") is True)
            readers.append({
                "source_id": sid, "reader": "official_adapter",
                "mode": "official_adapter" if enabled else "official_adapter_disabled",
                "source_layout_status": "supported" if enabled else "disabled",
                "source_read_status": source_status.get(sid, {}).get("status", "not_observed")
                    if enabled else "disabled",
            })
        layout, read_status = "unsupported", "not_read"
        if url in known:
            mode = "publisher_layout_active" if known[url]["enabled"] else "publisher_layout_disabled"
            layout = "supported" if known[url]["enabled"] else "disabled"
            read_status = "not_observed" if known[url]["enabled"] else "disabled"
        elif host.removeprefix("www.") == "happings.com":
            from happings_detail_discovery import url_kind
            if not happings_enabled:
                mode, layout, read_status = "happings_gate_not_active", "disabled", "disabled"
            elif happings_details_enabled and url_kind(url) == "detail":
                mode, layout = "happings_event_detail", "supported"
                default = (happings_report or {}).get("details", {}).get("status")
                read_status = detail_reads.get(url, "offline_skipped" if default == "offline_skipped"
                                               else "not_selected")
            elif not happings_page:
                mode, layout, read_status = "happings_source_scope_unproven", "unsupported", "not_read"
            else:
                mode, layout = "happings_province_index", "supported"
                read_status = route_reads[happings_page]
            readers = []
        elif readers:
            # A failed read cannot erase the known layout. If two approved
            # paths cover one URL, show a successful read before an unavailable
            # one, while retaining both exact reader dispositions below.
            selected = min(readers, key=lambda r: (
                {"supported": 0, "approval_required": 1, "disabled": 2, "unsupported": 3}[r["source_layout_status"]],
                r["source_read_status"] not in {"retrieved", "cached_snapshot", "resumed_checkpoint",
                                                "source_contract_approved_staged_only"},
                r["reader"] != ("official_adapter" if r["source_layout_status"] == "supported"
                                 else "source_contract"), r["source_id"],
            ))
            mode, layout = selected["mode"], selected["source_layout_status"]
            read_status = selected["source_read_status"]
        elif source_contracts is None and url in official:
            # Compatibility for callers without a declarative registry.
            mode, layout, read_status = "official_adapter", "supported", "not_observed"
        else:
            mode = "source_layout_needed" if url else "source_url_missing"
        resource = {
            "url": url, "host": host, "markets": len(group), "mode": mode,
            "source_layout_status": layout, "source_read_status": read_status,
            "missing_address": sum(not str(r.get("indirizzo") or "").strip() for r in group),
            "missing_hours": sum(not str(r.get("orario_testo") or "").strip() for r in group),
        }
        if readers:
            resource["readers"] = sorted(readers, key=lambda r: (r["reader"], r["source_id"]))
        if happings_page:
            resource["source_route_url"] = happings_page
            resource["source_route_method"] = ("province_index" if province_page_key(url) is not None
                                               else "province_index_join")
        elif mode == "happings_event_detail":
            resource["source_route_url"] = url
            resource["source_route_method"] = "exact_event_detail"
        elif existing_reader and mode == existing_reader[1]:
            resource["source_route_url"] = group[0]["url_fonte"]
            resource["source_route_method"] = "exact_existing_source"
        secondary = Counter(secondary_routes[row["slug"]] for row in group
                            if row.get("slug") in secondary_routes)
        if secondary:
            # Existing-address eligibility is distinct from a matched field
            # receipt. It cannot turn the original publisher into a reader.
            resource["secondary_corroboration_routes"] = [
                {"publisher": "happings.com", "source_route_url": route,
                 "eligible_markets": count, "source_read_status": route_reads[route]}
                for route, count in sorted(secondary.items())]
        resources.append(resource)
    return {"schema": 1, "markets": len(rows), "unique_primary_urls": len(groups),
            "hosts": len({x["host"] for x in resources if x["host"]}),
            "source_contract_configuration": contract_state,
            "source_admission_registry": registry_state,
            "market_layout_statuses": dict(Counter({state: sum(x["markets"] for x in resources
                if x["source_layout_status"] == state) for state in {x["source_layout_status"] for x in resources}})),
            "market_read_statuses": dict(Counter({state: sum(x["markets"] for x in resources
                if x["source_read_status"] == state) for state in {x["source_read_status"] for x in resources}})),
            "market_dispositions": dict(Counter({mode: sum(x["markets"] for x in resources if x["mode"] == mode)
                                                for mode in {x["mode"] for x in resources}})),
            "secondary_corroboration": {
                "publisher": "happings.com", "mode": "existing_address_exact_match",
                "counts_describe": "comparison_eligibility",
                "eligible_markets": len(secondary_routes),
                "unique_source_urls": len(set(secondary_routes.values())),
                "market_read_statuses": dict(Counter(route_reads[url] for url in secondary_routes.values())),
            },
            "resources": resources}


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, newurl):
        return None


def _download(url, max_bytes, mime):
    host = urlsplit(url).hostname
    if not safe_url(url):
        raise ValueError("Unsafe publisher URL")
    for answer in socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(answer[4][0]).is_global:
            raise ValueError("Publisher hostname resolved to a private address")
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept": mime,
                                    "Accept-Encoding": "identity"})
    with build_opener(NoRedirect).open(request, timeout=18) as response:
        content_type = response.headers.get("Content-Type", "").casefold()
        if response.url != url or mime not in content_type:
            raise ValueError("Publisher URL or content type changed")
        length = response.headers.get("Content-Length")
        expected_bytes = int(length) if length is not None else None
        if (response.headers.get("Content-Encoding", "identity").casefold() not in {"", "identity"}
                or (expected_bytes is not None and not 1 <= expected_bytes <= max_bytes)):
            raise ValueError("Unsupported or oversized publisher response")
        blob = response.read(max_bytes + 1)
        if not blob or len(blob) > max_bytes or (expected_bytes is not None and len(blob) != expected_bytes):
            raise ValueError("Incomplete or oversized publisher response")
    return blob


def fetch_page(profile, *, robots_cache):
    url = profile["url"]
    origin = "https://" + urlsplit(url).netloc
    if origin not in robots_cache:
        robots_url = origin + "/robots.txt"
        raw = _download(robots_url, 55_000, "text/plain")
        robots = RobotFileParser(robots_url)
        robots.parse(raw.decode("utf-8", errors="strict").splitlines())
        robots_cache[origin] = robots
    robots = robots_cache[origin]
    if not robots.can_fetch(USER_AGENT, url):
        raise ValueError("Publisher robots policy does not allow this page")
    delay = robots.crawl_delay(USER_AGENT) or robots.crawl_delay("*") or 2
    rate = robots.request_rate(USER_AGENT) or robots.request_rate("*")
    if rate:
        delay = max(delay, rate.seconds / rate.requests)
    if delay > 30:
        raise ValueError("Publisher pacing exceeds this bounded run")
    time.sleep(max(2, delay))
    blob = _download(url, MAX_BYTES, "text/html")
    return {"url": url, "body": blob, "read_on": datetime.now(timezone.utc).date().isoformat(),
            "sha256": hashlib.sha256(blob).hexdigest()}


def _write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")
    temp.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", "utf-8")
    temp.replace(path)


def _page(snapshot, profile, today):
    if not isinstance(snapshot, dict):
        raise ValueError("Missing source page observation")
    blob, read = snapshot.get("body"), as_day(snapshot.get("read_on"))
    if (snapshot.get("url") != profile["url"] or not isinstance(blob, bytes) or
            not 1 <= len(blob) <= MAX_BYTES or not read or read > today or
            (today - read).days > 45 or
            snapshot.get("sha256") != hashlib.sha256(blob).hexdigest()):
        raise ValueError("Source page identity, age or hash changed")
    return snapshot


def _municipalities(profile):
    data = json.loads((Path(__file__).resolve().parent / "data/istat-comuni-2026.json").read_text())
    region = profile["region"]
    return [{"citta": name, "provincia": province, "regione": region}
            for name, province in data["provinces_by_region"][region].items()
            if province == profile["province"]]


def _same_kind(row, source):
    title = text_key(row.get("nome"))
    city = re.escape(text_key(row.get("citta")))
    name = text_key(title + " " + str(row.get("url_fonte") or "").replace("-", " "))
    if source["market_kind"] == "farmers":
        # A generic farmers' listing does not establish the identity of a
        # branded initiative merely because both sell agricultural products.
        return bool(re.fullmatch(r"(?:il )?mercato (?:contadino|dei contadini|agricolo|degli agricoltori) "
                                 r"(?:a|di) " + city, title)) and not re.search(
                                     r"\b(?:campagna amica|coldiretti|slow food)\b", name)
    return bool(re.fullmatch(r"(?:il )?mercato (?:settimanale )?(?:a|di|del|della) " + city, title)) \
        and not SPECIAL.search(name) and row.get("categoria") in {None, "", "misto", "alimentare"}


def _place(value):
    return re.sub(r"\s+", " ", text_key(value)).strip(" .,;")


def _target(row, source_rows, source_id, today):
    province, region, city = row.get("provincia"), row.get("regione"), text_key(row.get("citta"))
    candidates = [r for r in source_rows if r["provincia"] == province and r["regione"] == region
                  and text_key(r["citta"]) == city and _same_kind(row, r)]
    weekdays = explicit_annual_weekday(row)
    if len(weekdays) != 1:
        return None, "no_single_explicit_annual_weekday"
    candidates = [r for r in candidates if r["weekday"] in weekdays]
    receipts = clean_receipts(row.get("riscontri_campi"), row, today=today)
    bound = {r["riga_fonte"] for r in receipts if r["fonte_id"] == source_id
             and r.get("gestore_campi") == MANAGER and r.get("campi_gestiti")}
    owned = [r for r in candidates if r["source_row_id"] in bound]
    if (len(owned) == 1 and owned[0]["identity_unique"]
            and owned[0]["comune_giorno_univoco"] and owned[0]["cadenza"] == "weekly"
            and not owned[0]["sedi_alternative"]):
        return owned[0], "managed_source_identity"
    options = candidates
    if len(options) != 1 or not options[0]["identity_unique"] or not options[0]["comune_giorno_univoco"]:
        return None, "multiple_or_missing_source_venues"
    source = options[0]
    if source["cadenza"] != "weekly" or source["sedi_alternative"]:
        return None, "non_weekly_or_alternative_venue"
    before, after = _place(row.get("indirizzo")), _place(source["indirizzo"])
    if before and before == after:
        return source, "same_venue_weekday"
    if address_key(row.get("indirizzo") or "") in VAGUE_ADDRESSES and before:
        if not source.get("localita"):
            return source, "unique_city_centre_venue"
    if not before:
        description = _place(row.get("descrizione"))
        if after and len(after) >= 7 and re.search(r"(?<!\w)" + re.escape(after) + r"(?!\w)", description):
            return source, "explicit_venue_in_saved_description"
        if source["market_kind"] == "farmers" and not source.get("localita"):
            return source, "named_farmers_market_and_weekday"
    return None, "venue_identity_not_established"


def reconcile(rows, parsed, profile, snapshot, *, today):
    output = deepcopy(rows)
    changes, matched, conflicts, retired = [], [], [], []
    held = Counter()
    if not parsed.get("complete"):
        return output, {"changes": [], "matched": [], "conflicts": [], "retired": [],
                        "held_reasons": {}, "status": "layout_changed"}
    if parsed.get("source_sha256") != snapshot["sha256"]:
        raise ValueError("Parser evidence does not match the observed HTML")
    for row in output:
        if row.get("regione") != profile["region"] or row.get("provincia") != profile["province"]:
            continue
        source, reason = _target(row, parsed["rows"], profile["source_id"], today)
        if source is None:
            held[reason] += 1
            continue
        original = deepcopy(row)
        prior_receipts = clean_receipts(original.get("riscontri_campi"), original, today=today)
        proposed = {k: source.get(k) for k in ("indirizzo", "orario_testo")
                    if isinstance(source.get(k), str) and 0 < len(source[k]) <= FIELDS[k]}
        source_rule = {"kind": "weekly", "weekdays": [source["weekday"]]}
        if explicit_rule(row.get("ricorrenza_testo")) == source_rule:
            proposed["ricorrenza_testo"] = row["ricorrenza_testo"]
        if not proposed:
            continue

        def observation(values, target):
            return make_receipt(
                target, values=values, source_url=profile["url"],
                source_name=profile["publisher"], source_id=profile["source_id"],
                source_row=source["source_row_id"], read_on=snapshot["read_on"],
                source_updated_on=parsed.get("fonte_aggiornata_il", ""),
                source_sha256=snapshot["sha256"], scope="pagina",
                method="pagina_primaria_revisionata", fingerprint_kind="html_bytes")

        latest = observation(proposed, {**original, **proposed})
        same_source = [r for r in prior_receipts if all(r.get(k) == latest.get(k) for k in
            ("fonte_id", "url", "riga_fonte", "metodo", "ambito", "impronta_tipo"))]
        if any(r["letto_il"] > latest["letto_il"] or
               (r["letto_il"] == latest["letto_il"] and r["sha256"] != latest["sha256"]) or
               (r.get("fonte_aggiornata_il") and
                latest.get("fonte_aggiornata_il", "") < r["fonte_aggiornata_il"])
               for r in same_source):
            held["source_version_ordering_not_proven"] += 1
            conflicts.append({"slug": row["slug"], "source_id": profile["source_id"],
                              "reason": "source_version_ordering_not_proven",
                              "previous_evidence": same_source, "source_proof": latest})
            continue
        accepted, initial, updates = {}, [], []
        for field, value in proposed.items():
            current = row.get(field) or ""
            if current == value:
                accepted[field] = value
                continue
            if original.get("verificato_il") or (field == "indirizzo" and
                                                    original.get("position_quality") == "precisa"):
                conflicts.append({"slug": row["slug"], "field": field, "source_id": profile["source_id"],
                                  "reason": "human_verification_or_precise_location_requires_review",
                                  "retained_value": current, "observed_value": value,
                                  "previous_evidence": [r for r in prior_receipts if field in r["valori"]],
                                  "source_proof": latest})
                continue
            fillable = not current or (field == "indirizzo"
                and address_key(current) in VAGUE_ADDRESSES and not row.get("verificato_il")
                and not any(field in r["valori"] for r in prior_receipts))
            allowed_update = managed_update_allowed(original, latest, field, manager=MANAGER, today=today)
            if fillable or allowed_update:
                row[field] = value
                accepted[field] = value
                (initial if fillable else updates).append(field)
                changes.append({"slug": row["slug"], "field": field, "before": current, "after": value,
                                "source_id": profile["source_id"], "source_row_id": source["source_row_id"],
                                "url": profile["url"], "match": reason,
                                "assignment": "initial" if fillable else "managed_update",
                                "source_proof": latest})
            else:
                conflicts.append({"slug": row["slug"], "field": field, "source_id": profile["source_id"],
                                  "reason": "existing_field_not_owned_or_sources_disagree",
                                  "retained_value": current, "observed_value": value,
                                  "previous_evidence": [r for r in prior_receipts if field in r["valori"]],
                                  "source_proof": latest})
        kept = retire_superseded_receipts(original, latest, today=today)
        if kept != prior_receipts:
            retired.append({"slug": row["slug"], "before": prior_receipts, "after": kept,
                            "source_proof": latest})
        if kept != prior_receipts or accepted:
            row["riscontri_campi"] = kept
        if accepted:
            receipt = observation(accepted, row)
            if initial:
                receipt = mark_managed_fields(receipt, initial, manager=MANAGER)
            if updates:
                receipt = mark_managed_fields(receipt, updates, manager=MANAGER, previous=original)
            row["riscontri_campi"] = clean_receipts([*kept, receipt], row, today=today)
            link = {"nome": profile["publisher"], "url": profile["url"]}
            links = list(row.get("fonti") or [])
            if link not in links:
                links.append(link)
            row["fonti"] = links
            matched.append({"slug": row["slug"], "source_id": profile["source_id"],
                            "values": accepted, "source_proof": receipt})
    return output, {"changes": changes, "matched": matched, "conflicts": conflicts,
                    "retired": retired, "held_reasons": dict(held), "status": "parsed"}


def run(rows, config, *, out, today, baseline_signature, policy_digest,
        offline=False, resume=False, fetcher=None):
    validate_contracts(config)
    before = deepcopy(rows)
    selected = rotate_sources(config["sources"], today)
    context = {"baseline": baseline_signature, "policy": policy_digest,
               "contracts": fingerprint(config), "today": today.isoformat()}
    result, changes, matched, conflicts, retired, pages = deepcopy(rows), [], [], [], [], []
    robots_cache = {}
    for profile in selected:
        path = Path(out) / "sources/publisher-pages" / (profile["source_id"] + ".json")
        status = {"source_id": profile["source_id"], "url": profile["url"], "status": "offline_skipped"}
        snapshot = None
        try:
            if resume:
                if not path.is_file():
                    status["status"] = "resume_missing_evidence"
                else:
                    if path.stat().st_size > MAX_BYTES * 2:
                        raise ValueError("Oversized publisher checkpoint")
                    saved = json.loads(path.read_text("utf-8"))
                    if saved.get("context") != context:
                        raise ValueError("Publisher checkpoint belongs to another catalog or policy")
                    snapshot = {**saved["snapshot"], "body": base64.b64decode(saved["snapshot"]["body_base64"], validate=True)}
                    status["status"] = "resumed_checkpoint"
            elif not offline:
                snapshot = fetcher(profile) if fetcher else fetch_page(profile, robots_cache=robots_cache)
                status["status"] = "retrieved"
            if snapshot is not None:
                snapshot = _page(snapshot, profile, today)
                if not resume:
                    packed = {k: snapshot[k] for k in ("url", "read_on", "sha256")}
                    packed["body_base64"] = base64.b64encode(snapshot["body"]).decode("ascii")
                    _write(path, {"schema": 1, "context": context, "snapshot": packed})
                parser_contract = {**profile, "municipalities": _municipalities(profile)}
                parsed = parse_page(snapshot["body"], source_url=profile["url"], contract=parser_contract)
                result, applied = reconcile(result, parsed, profile, snapshot, today=today)
                status.update({"read_on": snapshot["read_on"], "sha256": snapshot["sha256"],
                               "content_date": parsed.get("fonte_aggiornata_il", ""),
                               "parser_metrics": parsed.get("metrics", {}), "layout_complete": parsed.get("complete", False),
                               "changed_fields": len(applied["changes"]), "matched_markets": len(applied["matched"]),
                               "held_reasons": applied["held_reasons"], "parser_issues": parsed.get("issues", [])})
                if applied["status"] == "layout_changed":
                    status["status"] = "layout_changed"
                changes.extend(applied["changes"])
                matched.extend(applied["matched"])
                conflicts.extend(applied["conflicts"])
                retired.extend(applied["retired"])
        except (OSError, HTTPException, ValueError, KeyError, TypeError) as exc:
            status.update({"status": "source_held", "error_type": type(exc).__name__})
        pages.append(status)
    report = {"schema": 1, "date": today.isoformat(), "input_sha256": fingerprint(before),
              "source_contract_sha256": fingerprint(config), "selected_pages": pages,
              "changes": changes, "matched": matched, "conflicts": conflicts, "retired_evidence": retired,
              "markets_with_field_changes": len({x["slug"] for x in changes}),
              "field_changes": len(changes), "market_ids_added": 0, "market_ids_deleted": 0,
              "individual_openings_confirmed": 0}
    verify_changes(before, result, report, today=today)
    _write(Path(out) / "publisher-refresh.json", report)
    return result, report, {x["slug"] for x in [*matched, *retired]}


def verify_changes(before, after, report, *, today):
    if (report.get("input_sha256") != fingerprint(before) or
            [r["slug"] for r in before] != [r["slug"] for r in after]):
        raise ValueError("Publisher refresh changed the catalog identity set")
    expected = {(x["slug"], x["field"]): x for x in report["changes"]}
    actual = set()
    for old, new in zip(before, after):
        altered = {k for k in set(old) | set(new) if old.get(k) != new.get(k)}
        if altered - set(FIELDS) - {"fonti", "riscontri_campi"}:
            raise ValueError("Publisher refresh changed an unproved field")
        if any(link not in (new.get("fonti") or []) for link in (old.get("fonti") or [])):
            raise ValueError("Publisher refresh removed an existing source attribution")
        for field in altered & set(FIELDS):
            key = (new["slug"], field)
            change = expected.get(key)
            if not change or (old.get(field) or "") != change["before"] or new[field] != change["after"]:
                raise ValueError("Publisher field diff does not match its source proof")
            proof = change["source_proof"]
            if old.get("verificato_il") or (field == "indirizzo" and old.get("position_quality") == "precisa"):
                raise ValueError("Publisher update would invalidate a human check or precise location")
            if not clean_receipts([proof], {**old, **proof["valori"]}, today=today):
                raise ValueError("Publisher field lacks a valid exact source observation")
            if change.get("assignment") == "managed_update":
                if not managed_update_allowed(old, proof, field, manager=MANAGER, today=today):
                    raise ValueError("Publisher replaced a field it does not manage")
            elif ((old.get(field) or "") and
                  (field != "indirizzo" or address_key(old[field]) not in VAGUE_ADDRESSES or
                   old.get("verificato_il") or any(field in r["valori"] for r in
                       clean_receipts(old.get("riscontri_campi"), old, today=today)))):
                raise ValueError("Publisher overwrote a pre-existing field")
            actual.add(key)
    if actual != set(expected):
        raise ValueError("Publisher refresh reported changes it did not make")
    return verify_exported(after, report, today=today)


def verify_exported(rows, report, *, today):
    catalog = {r["slug"]: r for r in rows}
    for match in report["matched"]:
        row = catalog.get(match["slug"])
        if row is None:
            raise ValueError("Publisher-supported market disappeared from export")
        receipts = clean_receipts(row.get("riscontri_campi"), row, today=today)
        proof = match["source_proof"]
        for field, value in match["values"].items():
            if row.get(field) != value or not any(
                    all(r.get(k) == proof.get(k) for k in
                        ("fonte_id", "url", "riga_fonte", "sha256", "letto_il", "fonte_aggiornata_il", "impronta_tipo"))
                    and r["valori"].get(field) == value for r in receipts):
                raise ValueError("Publisher-supported field lost its value or evidence")
    return {"release_safe": True, "field_changes_checked": len(report["changes"]),
            "matched_fields_checked": sum(len(x["values"]) for x in report["matched"])}
