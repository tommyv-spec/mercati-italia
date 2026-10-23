"""Versioned *delta-only* DEV imports for the existing Cloudflare D1 catalog.

The current 14k-row DEV snapshot remains the immutable base. Later versions
store only additions and modified market payloads, never copies of unchanged
rows. This module does not write to the PROD channel or the public site.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from d1_catalog import (
    DB_NAME, MAX_DATABASE_BYTES, MAX_IMPORT_WRITES, MAX_ROWS,
    check_database_budget, cli, dataset_create_sql, dataset_meta, digest,
    execute_file, import_statements, manifest_rows, remote_query, sql,
)
from validate_static import validate

SCHEMA = Path(__file__).resolve().parents[1] / "db/cloudflare/0002_incremental.sql"
TABLES = ("catalog_dataset_parents", "catalog_market_changes", "catalog_delta_import_chunks")
PAGE_SIZE = 2000
MAX_DEPTH = 128


def canonical_hash(row: dict) -> str:
    return digest(json.dumps(row, sort_keys=True, ensure_ascii=False,
                             separators=(",", ":")).encode("utf-8"))


def required_schema() -> None:
    names = {r["name"] for r in remote_query(
        "SELECT name FROM sqlite_schema WHERE type='table' "
        "AND name IN ('catalog_dataset_parents','catalog_market_changes',"
        "'catalog_delta_import_chunks')"
    )}
    if names != set(TABLES):
        raise ValueError("Incremental D1 schema absent. Run 'migrate' first.")


def migrate() -> None:
    # Only CREATE TABLE/INDEX IF NOT EXISTS: repeated application is harmless.
    execute_file(SCHEMA)
    required_schema()


def lineage_sql(dataset_id: str) -> str:
    return (
        "WITH RECURSIVE ancestry(dataset_id,depth) AS ("
        "SELECT dataset_id,0 FROM catalog_datasets WHERE dataset_id=" + sql(dataset_id) +
        " UNION ALL SELECT p.parent_dataset_id,a.depth+1 "
        "FROM catalog_dataset_parents p JOIN ancestry a ON a.dataset_id=p.dataset_id "
        "WHERE a.depth<" + str(MAX_DEPTH) + ") "
    )


def check_lineage(dataset_id: str) -> None:
    statement = (lineage_sql(dataset_id) +
        "SELECT a.dataset_id,a.depth FROM ancestry a ORDER BY a.depth DESC LIMIT 1")
    roots = remote_query(statement)
    if len(roots) != 1:
        raise ValueError("Catalog version is missing")
    root = roots[0]["dataset_id"]
    if remote_query("SELECT dataset_id FROM catalog_dataset_parents WHERE dataset_id=" + sql(root)):
        raise ValueError("Incremental version chain is too deep or cyclic")
    if not remote_query("SELECT dataset_id FROM catalog_datasets WHERE dataset_id=" +
                        sql(root) + " AND status='ready'"):
        raise ValueError("Snapshot ancestor is not ready")
    if not remote_query("SELECT slug FROM catalog_markets WHERE dataset_id=" +
                        sql(root) + " LIMIT 1"):
        raise ValueError("Snapshot ancestor has no stored markets")


def effective_hashes_sql(dataset_id: str, *, after: str = "", limit: int = PAGE_SIZE) -> str:
    """Resolve one immutable version: most recent delta wins, base fills gaps."""
    if not 1 <= limit <= PAGE_SIZE:
        raise ValueError("Unsafe D1 result page size")
    return (
        lineage_sql(dataset_id) +
        ", latest AS ("
        " SELECT m.slug,m.payload_sha256,"
        " ROW_NUMBER() OVER(PARTITION BY m.slug ORDER BY a.depth) AS priority"
        " FROM catalog_market_changes m JOIN ancestry a ON m.dataset_id=a.dataset_id"
        "), root AS ("
        " SELECT a.dataset_id FROM ancestry a "
        " WHERE NOT EXISTS(SELECT 1 FROM catalog_dataset_parents p WHERE p.dataset_id=a.dataset_id)"
        " ORDER BY a.depth DESC LIMIT 1"
        "), effective AS ("
        " SELECT slug,payload_sha256 FROM latest WHERE priority=1"
        " UNION ALL"
        " SELECT b.slug,b.payload_sha256 FROM catalog_markets b "
        " WHERE b.dataset_id=(SELECT dataset_id FROM root)"
        " AND NOT EXISTS(SELECT 1 FROM latest WHERE latest.slug=b.slug)"
        ") SELECT slug,payload_sha256 FROM effective"
        " WHERE slug>" + sql(after) +
        " ORDER BY slug LIMIT " + str(limit)
    )


def effective_hashes(dataset_id: str) -> dict[str, str]:
    check_lineage(dataset_id)
    result: dict[str, str] = {}
    last = ""
    for _ in range((MAX_ROWS // PAGE_SIZE) + 3):
        page = remote_query(effective_hashes_sql(dataset_id, after=last))
        if not page:
            return result
        for item in page:
            slug, fingerprint = item["slug"], item["payload_sha256"]
            if not isinstance(slug, str) or slug <= last or slug in result:
                raise ValueError("Unsorted, duplicate or invalid D1 market identity")
            if not re.fullmatch(r"[a-f0-9]{64}", str(fingerprint)):
                raise ValueError("Invalid D1 market payload hash")
            result[slug] = fingerprint
            last = slug
        if len(result) > MAX_ROWS:
            raise ValueError("Exceeded bounded catalog size")
        if len(page) < PAGE_SIZE:
            return result
    raise ValueError("D1 effective catalog exceeded page budget")


def plan_delta(previous: dict[str, str], rows: list[dict]):
    target: dict[str, str] = {}
    by_slug: dict[str, dict] = {}
    for row in rows:
        slug = row["slug"]
        if slug in target:
            raise ValueError("Duplicate market ID in incoming release")
        target[slug] = canonical_hash(row)
        by_slug[slug] = row
    removed = sorted(set(previous) - set(target))
    if removed:
        raise ValueError("Incremental release would remove existing market IDs: " +
                         repr(removed[:8]))
    modified = [by_slug[slug] for slug in sorted(target)
                if previous.get(slug) != target[slug]]
    added = sum(slug not in previous for slug in target)
    return target, modified, {
        "previous": len(previous), "target": len(target),
        "added": added, "modified": len(modified) - added,
        "unchanged": len(target) - len(modified),
        "stored_changes": len(modified),
    }


def change_statement(dataset_id: str, row: dict) -> str:
    # Immutable dataset: a repeated attempt never overwrites earlier data.
    payload = json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    vals = [dataset_id, row["slug"], row["nome"], row["citta"],
            row.get("provincia") or "", row["regione"], row.get("fonte") or "",
            payload, digest(payload.encode("utf-8"))]
    statement = (
        "INSERT OR IGNORE INTO catalog_market_changes "
        "(dataset_id,slug,nome,citta,provincia,regione,fonte,payload_json,payload_sha256)"
        " VALUES (" + ",".join(map(sql, vals)) + ");\n"
    )
    if len(statement.encode("utf-8")) > 90000:
        raise ValueError("D1 SQL statement exceeds safe maximum: " + row["slug"])
    return statement


def proof_check(proof_file: Path, meta: dict) -> dict:
    proof = json.loads(Path(proof_file).read_text(encoding="utf-8"))
    if (proof.get("qa_gate_approved") is not True
            or proof.get("all_existing_market_ids_preserved") is not True
            or proof.get("manifest_content_signature") != meta["signature"]
            or proof.get("after_records") != meta["rows"]
            or proof.get("old_unrelated_market_fields_changed") != 0):
        raise ValueError("DEV QA proof does not authorize this exact catalog")
    return proof


def free_write_guard(changed_rows: int) -> None:
    """Fail closed before crossing a conservative Workers Free D1 write budget."""
    check_database_budget(max(1, changed_rows + 100))
    usage = json.loads(cli("info", DB_NAME, "--json", timeout=90))
    last_day = usage.get("rows_written_24h")
    if type(last_day) is not int or last_day < 0:
        raise ValueError("Current D1 free-tier usage unavailable; do not write")
    if last_day + changed_rows + 200 > 85000:
        raise ValueError("D1 free-tier write safety headroom exhausted: " +
                         str(last_day) + " already written over 24h")


def channel_heads() -> dict[str, str | None]:
    rows = remote_query(
        "SELECT channel,dataset_id FROM catalog_channels ORDER BY channel"
    )
    heads = {r["channel"]: r["dataset_id"] for r in rows}
    if set(heads) != {"dev", "prod"}:
        raise ValueError("DEV/PROD isolation cannot be confirmed")
    return heads


def dataset_record(meta: dict, parent: str):
    rows = remote_query(
        "SELECT d.content_signature,d.manifest_sha256,d.source_git_sha,"
        "d.expected_rows,d.status,p.parent_dataset_id "
        "FROM catalog_datasets d LEFT JOIN catalog_dataset_parents p "
        "ON p.dataset_id=d.dataset_id WHERE d.dataset_id=" + sql(meta["id"])
    )
    if len(rows) > 1:
        raise ValueError("Duplicate D1 dataset identity")
    if rows:
        item = rows[0]
        if (item["content_signature"] != meta["signature"]
                or item["manifest_sha256"] != meta["manifest_sha"]
                or int(item["expected_rows"]) != meta["rows"]
                or item["parent_dataset_id"] != parent):
            raise ValueError("Immutable D1 dataset ID or parent was changed")
    return rows


def register_version(meta: dict, parent: str) -> None:
    with __import__("tempfile").TemporaryDirectory(prefix="mercati-d1-incremental-") as work:
        path = Path(work) / "create.sql"
        path.write_text(
            dataset_create_sql(meta) +
            "INSERT OR IGNORE INTO catalog_dataset_parents(dataset_id,parent_dataset_id)"
            " VALUES (" + sql(meta["id"]) + "," + sql(parent) + ");\n",
            encoding="utf-8"
        )
        execute_file(path)
    if not dataset_record(meta, parent):
        raise ValueError("Remote incremental version registration failed")


def audit_and_verify(meta: dict, parent: str, stats: dict, proof: dict) -> None:
    evidence = json.dumps({
        "source": "DEV QA-approved static catalog",
        "git_sha": meta["git_sha"], "content_signature": meta["signature"],
        "changes": stats, "address_fields_filled": proof.get("address_fields_filled"),
        "qualitative_hour_fields_filled": proof.get("qualitative_hour_fields_filled"),
    }, ensure_ascii=False, sort_keys=True)
    event = digest((meta["id"] + "|dev|" + parent).encode("utf-8"))
    # On an interrupted run, redoing this audit is safe and does not write PROD.
    remote_query(
        "INSERT OR IGNORE INTO release_audit "
        "(event_id,channel,old_dataset_id,new_dataset_id,decision,evidence_json)"
        " SELECT " + ",".join(map(sql, [
            event, "dev", parent, meta["id"], "incremental_source_QA_passed", evidence
        ])) +
        " WHERE EXISTS(SELECT 1 FROM catalog_channels WHERE channel='dev'"
        " AND dataset_id=" + sql(meta["id"]) + ")"
    )
    stored = remote_query(
        "SELECT event_id FROM release_audit WHERE event_id=" + sql(event) +
        " AND channel='dev' AND old_dataset_id=" + sql(parent) +
        " AND new_dataset_id=" + sql(meta["id"])
    )
    if len(stored) != 1:
        raise ValueError("DEV pointer lacks immutable release audit")


def verify_state(dataset_id: str, hashes: dict[str, str]) -> None:
    actual = effective_hashes(dataset_id)
    if actual != hashes:
        changed = sum(actual.get(slug) != sha for slug, sha in hashes.items())
        raise ValueError("D1 full identity/hash verification failed: expected=" +
                         str(len(hashes)) + " actual=" + str(len(actual)) +
                         " different=" + str(changed))


def prepare(manifest_file: Path, git_sha: str, proof_file: Path):
    manifest_file = Path(manifest_file)
    validate(manifest_file)  # strict signature, regional shards and index
    meta = dataset_meta(manifest_file, git_sha)
    proof = proof_check(proof_file, meta)
    rows = list(manifest_rows(manifest_file))
    if len(rows) != meta["rows"]:
        raise ValueError("Incomplete static release after validation")
    return meta, proof, rows


def run(manifest_file: Path, git_sha: str, proof_file: Path,
        output_log: Path, *, dry_run: bool = False) -> dict:
    required_schema()
    meta, proof, rows = prepare(manifest_file, git_sha, proof_file)
    heads = channel_heads()
    parent = heads["dev"]
    if parent is None:
        raise ValueError("Existing DEV snapshot required; first use d1_catalog.py catalog")
    previous = effective_hashes(parent)
    target, changes, stats = plan_delta(previous, rows)
    if heads["dev"] == meta["id"]:
        verify_state(parent, target)
        result = {"status": "already_active", "dataset_id": meta["id"],
                  "dev_head": parent, "prod_head": heads["prod"], **stats}
        if not dry_run:
            source = remote_query(
                "SELECT parent_dataset_id FROM catalog_dataset_parents WHERE dataset_id=" +
                sql(meta["id"])
            )
            if source:
                audit_and_verify(meta, source[0]["parent_dataset_id"], stats, proof)
        return result
    if not dataset_record(meta, parent) and dry_run:
        return {"status": "planned", "dataset_id": meta["id"],
                "parent": parent, "prod_head": heads["prod"], **stats}
    if dry_run:
        return {"status": "resume_planned", "dataset_id": meta["id"],
                "parent": parent, "prod_head": heads["prod"], **stats}
    free_write_guard(len(changes))
    if not dataset_record(meta, parent):
        register_version(meta, parent)
    uploaded = 0
    if changes:
        processed, uploaded = import_statements(
            (change_statement(meta["id"], row) for row in changes),
            table="catalog_delta_import_chunks", key="dataset_id",
            value=meta["id"], output_log=output_log
        )
        if processed != len(changes):
            raise ValueError("D1 delta chunk checkpoints are incomplete")
    verify_state(meta["id"], target)
    remote_query(
        "UPDATE catalog_datasets SET status='ready',"
        " ready_at=COALESCE(ready_at,strftime('%Y-%m-%dT%H:%M:%fZ','now')) "
        "WHERE dataset_id=" + sql(meta["id"]) + " AND expected_rows=" +
        str(meta["rows"]) + " AND status IN ('loading','ready')"
    )
    # Optimistic compare-and-swap: another DEV release must not be overwritten.
    remote_query(
        "UPDATE catalog_channels SET dataset_id=" + sql(meta["id"]) +
        ",activated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now')"
        " WHERE channel='dev' AND dataset_id=" + sql(parent) +
        " AND EXISTS(SELECT 1 FROM catalog_datasets WHERE dataset_id=" +
        sql(meta["id"]) + " AND status='ready')"
    )
    final = channel_heads()
    if final["dev"] != meta["id"]:
        raise ValueError("Concurrent DEV release changed; pointer not overwritten")
    if final["prod"] != heads["prod"]:
        raise ValueError("PROD pointer changed during import; stop for manual review")
    audit_and_verify(meta, parent, stats, proof)
    result = {"status": "dev_incremental_imported",
              "dataset_id": meta["id"], "parent": parent,
              "dev_head": final["dev"], "prod_head": final["prod"],
              "uploaded_in_this_run": uploaded, **stats}
    output_log.parent.mkdir(parents=True, exist_ok=True)
    output_log.write_text(json.dumps(result, sort_keys=True) + "\n", encoding="utf-8")
    return result


def verify_existing(manifest_file: Path, git_sha: str) -> dict:
    """Read-only full-hash match of the already active DEV version to Git assets."""
    required_schema()
    manifest_file = Path(manifest_file)
    validate(manifest_file)
    meta = dataset_meta(manifest_file, git_sha)
    head = channel_heads()
    if head["dev"] != meta["id"]:
        raise ValueError("This manifest is not the active DEV dataset")
    rows = list(manifest_rows(manifest_file))
    hashes = {r["slug"]: canonical_hash(r) for r in rows}
    if len(hashes) != meta["rows"]:
        raise ValueError("Duplicate or lost market identity in export")
    verify_state(head["dev"], hashes)
    return {"status": "dev_full_hashes_verified", "records": len(hashes),
            "dataset_id": head["dev"], "prod_head": head["prod"]}


def main():
    parser = argparse.ArgumentParser(description="Safe incremental D1 DEV catalog")
    parser.add_argument("action", choices=("migrate", "plan", "import", "status", "verify"))
    parser.add_argument("--manifest", type=Path)
    parser.add_argument("--source-git-sha")
    parser.add_argument("--proof", type=Path)
    parser.add_argument("--output-log", type=Path)
    args = parser.parse_args()
    if args.action == "migrate":
        migrate()
        print(json.dumps({"status": "incremental_schema_ready", "database": DB_NAME}))
    elif args.action == "status":
        required_schema()
        print(json.dumps(channel_heads(), sort_keys=True))
    elif args.action == "verify":
        if not all((args.manifest, args.source_git_sha)):
            parser.error("verify requires --manifest and --source-git-sha")
        print(json.dumps(verify_existing(args.manifest, args.source_git_sha),
                         ensure_ascii=False, sort_keys=True))
    else:
        if not all((args.manifest, args.source_git_sha, args.proof)):
            parser.error("plan/import requires --manifest, --source-git-sha and --proof")
        output = args.output_log or Path(__import__("tempfile").gettempdir()) / "mercati-d1-incremental.json"
        print(json.dumps(run(args.manifest, args.source_git_sha, args.proof,
                             output, dry_run=args.action == "plan"),
                         ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()
