"""Existing-record enrichment from exact Roma d881 source rows.

No admissions, coordinates, address replacements, recurrences or calendars.
Only the six explicitly dated weekday hours are assigned. Full row facts,
including historical conditions, remain bound to the original CSV bytes.
"""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date
from pathlib import Path

from field_evidence import (clean_receipts, field_states, make_receipt,
                            managed_update_allowed, mark_managed_fields,
                            retire_superseded_receipts)
from source_hours import preserve_hours_text
from source_roma_d881 import (SOURCE_ID, PUBLISHER, DATASET_PAGE, MAX_METADATA_BYTES,
                              MAX_CSV_BYTES, MAX_MARKET_ROWS, MAX_PHYSICAL_ROWS,
                              corrupt_text, digest, name_key, normalized, parse_snapshot)

MANAGER = "roma-d881"
MATCH_METHOD = "nome_sede_comune_univoco"
MAX_CATALOG_ROWS = 50_000
POLICY_PATH = Path(__file__).with_name("data") / "roma-d881-policy.json"
EXPECTED_POLICY = {
    "schema": 1, "enabled": True, "source_id": SOURCE_ID,
    "max_requests": 2, "max_metadata_bytes": MAX_METADATA_BYTES,
    "max_csv_bytes": MAX_CSV_BYTES, "max_market_rows": MAX_MARKET_ROWS,
    "max_physical_rows": MAX_PHYSICAL_ROWS, "admit_new": False,
    "assign_coordinates": False, "replace_addresses": False,
    "generate_calendar": False, "managed_hours_updates": True,
}
ALLOWED_FIELDS = {"orario_testo", "riscontri_campi"}


def load_policy(path=POLICY_PATH):
    policy = json.loads(Path(path).read_text("utf-8"))
    if policy != EXPECTED_POLICY or any(type(policy[key]) is not type(value)
                                         for key, value in EXPECTED_POLICY.items()):
        raise ValueError("Roma d881 policy differs from the reviewed bounded contract")
    return policy


def _catalog(rows):
    if not isinstance(rows, list) or len(rows) > MAX_CATALOG_ROWS:
        raise ValueError("Invalid Roma enrichment catalogue")
    ids = [row.get("slug") if isinstance(row, dict) else None for row in rows]
    if any(not isinstance(item, str) or not item for item in ids) or len(set(ids)) != len(ids):
        raise ValueError("Catalogue IDs are missing or duplicated")


def _scope(row):
    return (row.get("url_fonte") == DATASET_PAGE and normalized(row.get("citta")) == "roma"
            and row.get("provincia") == "RM" and normalized(row.get("regione")) == "lazio")


def _key(name, street):
    return name_key(name), normalized(street)


def _district(row):
    found = re.findall(r"\bmunicipio\s+(\d{1,2})\b", str(row.get("descrizione") or ""), flags=re.I)
    return {int(value) for value in found}


def hours_text(fact):
    """All six source clocks and every qualification, with its actual date."""
    day = date.fromisoformat(fact["source_updated_on"]).strftime("%d/%m/%Y")
    text = "Orari riportati nella fonte aggiornata al " + day + "; attualità da verificare. "
    text += "; ".join(item["day"] + " " + item["start"] + "–" + item["end"]
                      for item in fact["hours_by_day"]) + "."
    if fact["hours_notes"]:
        text += " Note orari nella stessa riga: " + fact["hours_notes"] + "."
    if fact["market_notes"]:
        text += " Note sul mercato nella stessa riga: " + fact["market_notes"] + "."
    text += " Domenica non indicata nella fonte."
    return preserve_hours_text(text)


def _receipt(row, fact, document, value):
    return make_receipt(
        {**row, "orario_testo": value}, values={"orario_testo": value},
        source_url=DATASET_PAGE, source_name=PUBLISHER + ", dataset d881",
        source_id=SOURCE_ID, source_row=fact["source_row_key"],
        read_on=document["read_on"], source_updated_on=fact["source_updated_on"],
        source_sha256=fact["row_sha256"], scope="dataset", method=MATCH_METHOD,
        fingerprint_kind="publisher_parsed_json")


def _evaluate(base, document, *, today, apply):
    result = deepcopy(base)
    target_keys = defaultdict(list)
    source_keys = defaultdict(list)
    facts_by_number = {fact["row_number"]: fact for fact in document["rows"]}
    for fact in document["rows"] + document["held_rows"]:
        raw = fact["raw_fields"]
        source_keys[_key(raw.get("Nome_Mercato"), raw.get("INDIRIZZO"))].append(fact["row_number"])
    for row in base:
        if _scope(row):
            target_keys[_key(row.get("nome"), row.get("indirizzo"))].append(row["slug"])
    outcomes, changes, matched_source_rows, matched_ids = [], [], set(), []
    for index, row in enumerate(base):
        if row.get("url_fonte") != DATASET_PAGE:
            continue
        outcome = {"market_id": row["slug"], "status": "held", "reason": None,
                   "source_row": None, "source_updated_on": None, "assigned_fields": []}
        key = _key(row.get("nome"), row.get("indirizzo"))
        if not _scope(row):
            outcome["reason"] = "source_geography_mismatch"
        elif any(corrupt_text(str(row.get(field) or "")) for field in ("nome", "indirizzo")):
            outcome["reason"] = "corrupt_catalog_identity"
        elif not all(key):
            outcome["reason"] = "missing_exact_name_or_street"
        elif len(target_keys[key]) != 1:
            outcome["reason"] = "ambiguous_catalog_identity"
        elif not source_keys[key]:
            outcome["reason"] = "no_exact_source_name_and_street"
        elif len(source_keys[key]) != 1:
            outcome["reason"] = "ambiguous_source_identity"
        else:
            number = source_keys[key][0]
            fact = facts_by_number.get(number)
            outcome["source_row"] = number
            if fact is None:
                outcome["reason"] = "source_row_held"
            elif _district(row) and _district(row) != {fact["municipio"]}:
                outcome["reason"] = "municipio_conflict"
            else:
                matched_source_rows.add(number)
                matched_ids.append(row["slug"])
                outcome["source_updated_on"] = fact["source_updated_on"]
                _assign(row, result, index, fact, document, outcome, changes,
                        today=today, apply=apply)
        outcomes.append(outcome)
    counters = Counter(outcome["status"] for outcome in outcomes)
    counters.update(outcome["reason"] for outcome in outcomes if outcome["reason"])
    return result, {
        "outcomes": outcomes, "changes": changes, "matched_ids": matched_ids,
        "changed_ids": [item["market_id"] for item in changes],
        "unmatched_source_rows": sorted(set(facts_by_number) - matched_source_rows),
        "counts": dict(sorted(counters.items())),
    }


def _assign(row, result, index, fact, document, outcome, changes, *, today, apply):
    try:
        value = hours_text(fact)
    except ValueError:
        outcome["reason"] = "source_hours_not_representable"
        return
    current = row.get("orario_testo")
    if current is not None and not isinstance(current, str):
        outcome["reason"] = "invalid_existing_hours"
        return
    prospective = _receipt(row, fact, document, value)
    assigned = []
    if not str(current or "").strip():
        if row.get("verificato_il"):
            outcome["reason"] = "verified_record_requires_review"
            return
        assigned = ["orario_testo"]
    elif current != value:
        if not managed_update_allowed(row, prospective, "orario_testo", manager=MANAGER, today=today):
            outcome["reason"] = "existing_hours_conflict"
            return
        assigned = ["orario_testo"]
    revised = deepcopy(row)
    revised["orario_testo"] = value
    prior = retire_superseded_receipts(row, prospective, today=today)
    if assigned:
        prospective = mark_managed_fields(prospective, assigned, manager=MANAGER, previous=row)
    revised["riscontri_campi"] = clean_receipts(prior + [prospective], revised, today=today)
    if not any(item.get("fonte_id") == SOURCE_ID and item["valori"].get("orario_testo") == value
               for item in revised["riscontri_campi"]):
        outcome["reason"] = "source_receipt_capacity_conflict"
        return
    # Row dates qualify these hours only. Setting the catalogue's primary
    # source dates would also refresh unrelated, unproved recurrence rules.
    outcome["assigned_fields"] = assigned
    outcome["hours_evidence_state"] = field_states(revised, today=today)["orario_testo"]
    outcome["status"] = "enriched" if assigned else "observed"
    if not apply:
        outcome["status"] = "candidate" if assigned else "observation_candidate"
    fields = {key: {"before": deepcopy(row.get(key)), "after": deepcopy(revised.get(key))}
              for key in sorted(set(row) | set(revised)) if row.get(key) != revised.get(key)}
    if apply and fields:
        if set(fields) - ALLOWED_FIELDS:
            raise ValueError("Roma enrichment attempted an unrelated field change")
        result[index] = revised
        changes.append({"market_id": row["slug"], "source_row": fact["row_number"], "fields": fields})


def preview(base, snapshot, *, today, apply=False):
    """Return (rows, report); existing identities/order and all other fields stay.

    The report carries the original bounded source snapshot, full structured
    historical facts and the exact field diff. apply=False never changes rows.
    Only fields assigned by this manager can later follow a newer row version.
    """
    _catalog(base)
    if type(today) is not date or type(apply) is not bool:
        raise ValueError("Invalid Roma enrichment date or apply flag")
    document = parse_snapshot(snapshot, today=today)
    result, evaluation = _evaluate(base, document, today=today, apply=apply)
    report = {"schema": 1, "source_id": SOURCE_ID, "date": today.isoformat(),
              "apply": apply, "input_sha256": digest(base), "output_sha256": digest(result),
              "snapshot": deepcopy(snapshot), "document": document, **evaluation,
              "new_market_ids": [], "coordinates_assigned": 0, "calendars_generated": 0,
              "individually_confirmed": False}
    verify_changes(base, result, report, today=today)
    return result, report


def verify_changes(before, after, report, *, today):
    """Reconstruct every change from the original metadata and CSV bytes."""
    _catalog(before)
    _catalog(after)
    if (type(today) is not date or not isinstance(report, dict) or report.get("schema") != 1
            or report.get("source_id") != SOURCE_ID or report.get("date") != today.isoformat()
            or type(report.get("apply")) is not bool or report.get("new_market_ids") != []
            or type(report.get("coordinates_assigned")) is not int or report["coordinates_assigned"] != 0
            or type(report.get("calendars_generated")) is not int or report["calendars_generated"] != 0
            or report.get("individually_confirmed") is not False
            or report.get("input_sha256") != digest(before) or report.get("output_sha256") != digest(after)):
        raise ValueError("Roma audit is not bound to its catalogue inputs and policy")
    document = parse_snapshot(report.get("snapshot"), today=today)
    if document != report.get("document"):
        raise ValueError("Roma parsed facts differ from the captured source bytes")
    expected, evaluation = _evaluate(before, document, today=today, apply=report["apply"])
    if expected != after or any(report.get(key) != value for key, value in evaluation.items()):
        raise ValueError("Roma changes cannot be reconstructed from source facts")
    if [row["slug"] for row in before] != [row["slug"] for row in after]:
        raise ValueError("Roma enrichment changed existing IDs or row order")
    for old, new in zip(before, after):
        if any(old.get(key) != new.get(key) for key in (set(old) | set(new)) - ALLOWED_FIELDS):
            raise ValueError("Roma enrichment changed a protected market field")
        if str(old.get("indirizzo") or "") != str(new.get("indirizzo") or ""):
            raise ValueError("Roma enrichment changed an existing street")
    return {"valid": True, "input_count": len(before), "output_count": len(after),
            "matched": len(report["matched_ids"]), "changed": len(report["changed_ids"]),
            "new_market_ids": [], "calendars_generated": 0}


def verify_exported(before, exported, report, *, today):
    """Validate this phase's Roma cohort in the final normalized catalogue.

    Later unrelated source phases may add/update other market records. This
    verifies every original Roma identity and every normalized Roma field,
    including held records, against a fresh replay of the original bytes.
    """
    from export_static import matches_export, normalize
    _catalog(exported)
    document = parse_snapshot(report.get("snapshot"), today=today)
    after, _ = _evaluate(before, document, today=today, apply=report.get("apply"))
    verify_changes(before, after, report, today=today)
    by_id = {row["slug"]: row for row in exported}
    checked = []
    for row in after:
        if row.get("url_fonte") != DATASET_PAGE:
            continue
        expected, reason = normalize(row, today)
        if expected is None or reason or not matches_export(expected, by_id.get(row["slug"]), by_id):
            raise ValueError("Roma exported record differs from its source-bound normalized result: " + row["slug"])
        checked.append(row["slug"])
    return {"valid": True, "checked_ids": checked, "checked_count": len(checked)}
