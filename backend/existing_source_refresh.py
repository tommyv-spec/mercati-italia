"""Bounded refresh of already-catalogued editorial and Roma source identities.

The existing MAIN publisher remains the only catalog writer. Editorial queues
travel inside its candidate data directory; raw responses stay in temporary
checkpoints. An observed field is never an independent opening confirmation.
"""
from __future__ import annotations

import json
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import date
from http.client import HTTPException
from pathlib import Path

import eventiesagre_detail_refresh as editorial
import citynews_detail_refresh as citynews
import citynews_detail_enrichment as citynews_evidence
import roma_d881_enrichment as roma
import source_roma_d881 as roma_source
from field_evidence import fingerprint

SCHEMA = 1
EDITORIAL_SECONDS = 360
CDC_RESERVED_SECONDS = 90
EDITORIAL_STATES = {
    "eventiesagre.it": "eventiesagre-detail-state.json",
    "cosedicasa.com": "cosedicasa-detail-state.json",
    "citynews": citynews.STATE_FILENAME,
}
STATE_FILENAMES = frozenset(EDITORIAL_STATES.values())
NO_NEW_STATE = {"disabled", "offline_skipped", "resume_missing_evidence"}


def configuration(*, enabled=True, citynews_policy=None):
    """Validate every source-level policy before the pipeline starts reading."""
    if type(enabled) is not bool:
        raise ValueError("Existing-source enablement must be an explicit boolean")
    return {
        "schema": SCHEMA,
        "enabled": enabled,
        "editorial": {
            **{publisher: editorial.validate_policy(publisher=publisher)
               for publisher in EDITORIAL_STATES if publisher != citynews.PUBLISHER},
            citynews.PUBLISHER: citynews.validate_policy(citynews_policy),
        },
        "roma": roma.load_policy(),
        "editorial_shared_seconds": EDITORIAL_SECONDS,
        "cosedicasa_reserved_seconds": CDC_RESERVED_SECONDS,
    }


def _write(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, ensure_ascii=False, sort_keys=True) + "\n", "utf-8")
    temporary.replace(path)


def _read_state(path, *, publisher, today):
    path = Path(path)
    if not path.is_file():
        return None
    reader = citynews if publisher == citynews.PUBLISHER else editorial
    if path.stat().st_size > reader.MAX_STATE_BYTES:
        raise ValueError("Editorial public queue exceeds the source reader's bound")
    kwargs = {} if publisher == citynews.PUBLISHER else {"publisher": publisher}
    return reader.validate_state(json.loads(path.read_text("utf-8")), today=today, **kwargs)


def run_editorial(rows, *, out, state_dir, today, baseline_signature,
                  policy_digest, config, offline=False, resume=False,
                  fetchers=None, monotonic=time.monotonic, deadline=None):
    """Read separate hosts concurrently; prove and merge only disjoint changes.

Each reader sees the same immutable baseline and retains its own pacing,
request limit and response checkpoint. Neither publisher waits behind the
other's time allowance. A shared catalog identity changed by both is rejected.
"""
    started = monotonic()
    end = min(started + EDITORIAL_SECONDS, deadline) if deadline is not None else started + EDITORIAL_SECONDS
    reports, preserve = {}, set()
    def read_publisher(publisher, filename):
        reader = citynews if publisher == citynews.PUBLISHER else editorial
        evidence = citynews_evidence if publisher == citynews.PUBLISHER else editorial
        source_kwargs = {} if publisher == citynews.PUBLISHER else {"publisher": publisher}
        allowance = config["editorial"][publisher]["max_seconds"]
        source_end = min(end, started + allowance)
        previous = _read_state(Path(state_dir) / filename, publisher=publisher, today=today)
        revised, report, protected = reader.run(
            rows, out=out, today=today, **source_kwargs,
            baseline_signature=baseline_signature, policy_digest=policy_digest,
            policy={**config["editorial"][publisher],
                    "enabled": config["enabled"] and config["editorial"][publisher]["enabled"]},
            previous_state=previous,
            offline=offline, resume=resume,
            fetcher=(fetchers or {}).get(publisher), deadline=source_end,
            monotonic=monotonic,
        )
        evidence.verify_changes(rows, revised, report["evidence"], today=today)
        if [row["slug"] for row in rows] != [row["slug"] for row in revised]:
            raise ValueError("Existing-source refresh changed the original identity set")
        return revised, report, protected

    with ThreadPoolExecutor(max_workers=len(EDITORIAL_STATES), thread_name_prefix="existing-source") as workers:
        pending = {publisher: workers.submit(read_publisher, publisher, filename)
                   for publisher, filename in EDITORIAL_STATES.items()}
        phases = {publisher: future.result() for publisher, future in pending.items()}
    changed = {}
    for publisher, (revised, report, protected) in phases.items():
        for old, new in zip(rows, revised):
            if old != new:
                if old["slug"] in changed:
                    raise ValueError("Two independent editorial readers changed the same identity")
                changed[old["slug"]] = new
        reports[publisher] = report
        preserve.update(protected)
    result = [changed.get(row["slug"], row) for row in rows]
    report = {"schema": SCHEMA, "date": today.isoformat(), "editorial": reports,
              "shared_budget_seconds": EDITORIAL_SECONDS,
              "execution": "independent_publishers_concurrent_disjoint_changes",
              "input_sha256": fingerprint(rows), "output_sha256": fingerprint(result),
              "changed_existing_ids": sorted(changed),
              "elapsed_seconds": round(monotonic() - started, 3)}
    _write(Path(out) / "existing-source-refresh.json", report)
    return result, report, preserve


def persist_editorial_states(report, *, out, source_dir, destination, today):
    """Copy only exactly validated and report-bound queues to the candidate."""
    if report.get("schema") != SCHEMA or report.get("date") != today.isoformat():
        raise ValueError("Editorial queue report changed its reference context")
    changed = False
    for publisher, filename in EDITORIAL_STATES.items():
        phase = report["editorial"][publisher]
        if phase["status"] in NO_NEW_STATE:
            continue
        state = _read_state(Path(out) / filename, publisher=publisher, today=today)
        if state is None or fingerprint(state) != fingerprint(phase["state"]):
            raise ValueError("Editorial public queue differs from its source report")
        previous = _read_state(Path(source_dir) / filename, publisher=publisher, today=today)
        changed = changed or previous != state
        _write(Path(destination) / filename, state)
    return changed


def verify_editorial_export(rows, report, *, today, state_dir=None):
    if (report.get("schema") != SCHEMA or report.get("date") != today.isoformat()
            or set(report.get("editorial", {})) != set(EDITORIAL_STATES)):
        raise ValueError("Editorial final proof lost a configured reader or its date")
    proofs, queues = {}, {}
    for publisher, phase in report["editorial"].items():
        evidence = citynews_evidence if publisher == citynews.PUBLISHER else editorial
        proofs[publisher] = evidence.verify_exported(rows, phase["evidence"], today=today)
        if state_dir is not None:
            state = _read_state(Path(state_dir) / EDITORIAL_STATES[publisher],
                                publisher=publisher, today=today)
            if phase["status"] not in NO_NEW_STATE:
                if state is None or fingerprint(state) != fingerprint(phase["state"]):
                    raise ValueError("Exported editorial queue differs from its validated source report")
                queues[publisher] = {"status": "validated_report_bound",
                                     "sha256": fingerprint(state)}
            else:
                queues[publisher] = {"status": "validated_previous" if state is not None else "absent"}
    return {"schema": SCHEMA, "release_safe": all(p["release_safe"] for p in proofs.values()),
            "publishers": proofs, "queues": queues}


def run_roma(rows, *, out, today, baseline_signature, policy_digest, config,
             offline=False, resume=False, fetcher=None, clock=None):
    """Refresh only Roma hours, after general calendar and municipality phases."""
    policy = config["roma"]
    if policy != roma.load_policy():
        raise ValueError("Roma source policy changed during the candidate run")
    context = {"schema": SCHEMA, "date": today.isoformat(),
               "baseline": baseline_signature, "pipeline_policy": policy_digest,
               "source_policy": fingerprint(policy), "catalog": fingerprint(rows)}
    checkpoint = Path(out) / "sources/roma-d881-snapshot.json"
    snapshot = None
    enabled = config["enabled"] and policy["enabled"]
    report = {"schema": SCHEMA, "source_id": roma_source.SOURCE_ID,
              "date": today.isoformat(), "enabled": enabled,
              "status": "disabled", "network_requests": 0}
    if enabled and not any(row.get("url_fonte") == roma_source.DATASET_PAGE for row in rows):
        report["status"] = "no_catalog_rows"
    elif enabled and resume:
        report["status"] = "resume_missing_evidence"
        if checkpoint.is_file():
            if checkpoint.stat().st_size > 2 * (roma_source.MAX_METADATA_BYTES + roma_source.MAX_CSV_BYTES):
                raise ValueError("Roma source checkpoint exceeds its bounded response sizes")
            saved = json.loads(checkpoint.read_text("utf-8"))
            if saved.get("context") != context:
                raise ValueError("Roma resume belongs to another source policy, date or catalog")
            snapshot = saved["snapshot"]
            report["status"] = "resumed_checkpoint"
    elif enabled and offline:
        report["status"] = "offline_skipped"
    elif enabled:
        requests = 0
        actual_fetch = fetcher or roma_source.fetch_public

        def counted_fetch(url):
            nonlocal requests
            requests += 1
            if requests > policy["max_requests"]:
                raise ValueError("Roma source exceeded its two-response request allowance")
            return actual_fetch(url)

        try:
            snapshot = roma_source.acquire(today=today, fetch=counted_fetch, clock=clock)
        except (OSError, HTTPException, ValueError, UnicodeError) as error:
            report.update(status="source_unavailable", error_type=type(error).__name__)
        else:
            report["status"] = "retrieved"
            _write(checkpoint, {"context": context, "snapshot": snapshot})
        report["network_requests"] = requests
    result, proof = rows, None
    if snapshot is not None:
        result, evidence = roma.preview(rows, snapshot, today=today, apply=True)
        proof = roma.verify_changes(rows, result, evidence, today=today)
        report.update(evidence)
        # At this point all other ordinary source/calendar repairs are done.
        # The subsequent Happings guard independently proves every remaining
        # mutation and compares the entire final catalog to that phase result.
        from export_static import normalize
        normalized = []
        for row in result:
            if row.get("url_fonte") == roma_source.DATASET_PAGE:
                value, error = normalize(row, today)
                if error or value is None:
                    raise ValueError("Roma source phase lost an existing normalized identity")
                normalized.append(value)
        export_proof = roma.verify_exported(rows, normalized, evidence, today=today)
        proof["normalized_cohort"] = export_proof
    report["release_safe"] = True
    report["phase_proof"] = proof
    _write(Path(out) / "roma-d881-refresh.json", report)
    return result, report


def verify_roma_fields(exported, report, *, today):
    """Confirm every accepted Roma hour and its receipt survive later phases.

Full identity/field checks are made by the Roma phase and the subsequent
whole-catalog Happings guard. This extra check tethers the owned fields to
the bytes actually published without excluding independent later receipts.
"""
    from field_evidence import clean_receipts
    if report.get("schema") != SCHEMA or report.get("date") != today.isoformat():
        raise ValueError("Roma field report changed its source date context")
    by_id = {row["slug"]: row for row in exported}
    checked = 0
    for change in report.get("changes", []):
        row = by_id.get(change["market_id"])
        if row is None:
            raise ValueError("A source-refreshed Roma identity disappeared")
        for field, values in change["fields"].items():
            if field == "orario_testo" and row.get(field) != values["after"]:
                raise ValueError("A source-refreshed Roma hour changed after its source proof")
            if field == "riscontri_campi":
                expected = [r for r in values["after"] if r.get("fonte_id") == roma_source.SOURCE_ID]
                actual = clean_receipts(row.get(field), row, today=today)
                if not expected or any(receipt not in actual for receipt in expected):
                    raise ValueError("Roma historical hours lost their exact dated source receipt")
        checked += 1
    return {"schema": SCHEMA, "release_safe": True, "source_changed_rows_checked": checked}
