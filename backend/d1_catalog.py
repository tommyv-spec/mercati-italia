"""Source-backed Mercati Italia catalog -> dedicated EU Cloudflare D1.

Uses no GitHub artifact or billed runner; Windows OAuth stays with Wrangler.
Remote imports are idempotent and resumable via D1 chunk receipts. The PROD
channel is NEVER changed by this command.
"""
from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path

DB_NAME = "mercati-italia-catalog"
MAX_ROWS = 30000
MAX_ROW_SQL_BYTES = 90000
MAX_CHUNK_BYTES = 1500000
MAX_CHUNK_ROWS = 700
MAX_IMPORT_WRITES = 50000
MAX_DATABASE_BYTES = 450 * 1024 * 1024
REGION_HASH = re.compile(r"-([0-9a-f]{14})\.json$")
HEX64 = re.compile(r"[a-f0-9]{64}\Z")


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def sql(value) -> str:
    value = str(value if value is not None else "")
    if "\x00" in value:
        raise ValueError("Null byte cannot occur in SQL")
    return "'" + value.replace("'", "''") + "'"


def wrangler_path() -> list[str]:
    custom = os.environ.get("MERCATI_WRANGLER_JS")
    if custom:
        p = Path(custom)
        if not p.is_file():
            raise ValueError("Configured Wrangler is absent")
        return [shutil.which("node") or "node", str(p)]
    exe = shutil.which("wrangler")
    if exe:
        return [exe]
    cache = Path(os.environ.get("LOCALAPPDATA", "")) / "npm-cache" / "_npx"
    versions = sorted(cache.glob("*/node_modules/wrangler/bin/wrangler.js"))
    if not versions:
        raise RuntimeError("Wrangler is unavailable; no paid service will be installed")
    return [shutil.which("node") or "node", str(versions[-1])]


def cli(*args: str, timeout=240) -> str:
    command = [*wrangler_path(), "d1", *args]
    completed = subprocess.run(command, text=True, encoding="utf-8",
                               errors="replace", capture_output=True, timeout=timeout)
    if completed.returncode:
        raise RuntimeError("Cloudflare D1 command failed: " +
                           (completed.stderr or completed.stdout)[-1800:])
    return completed.stdout


def remote_query(statement: str):
    raw = cli("execute", DB_NAME, "--remote", "--json", "--command", statement,
              timeout=90)
    parsed = json.loads(raw)
    if not isinstance(parsed, list) or not parsed or parsed[0].get("success") is not True:
        raise ValueError("Unexpected D1 query result")
    return parsed[0].get("results") or []


def scalar(statement: str, field: str):
    rows = remote_query(statement)
    if len(rows) != 1 or field not in rows[0]:
        raise ValueError("D1 scalar query returned an unexpected result")
    return rows[0][field]


def execute_file(path: Path):
    cli("execute", DB_NAME, "--remote", "--file", str(path), "--yes", timeout=300)


def manifest_rows(manifest_file: Path):
    manifest_file = Path(manifest_file)
    manifest_bytes = manifest_file.read_bytes()
    manifest = json.loads(manifest_bytes)
    if (manifest.get("schema") != 1 or manifest.get("layout") != "regional"
            or type(manifest.get("total")) is not int
            or not 1 <= manifest["total"] <= MAX_ROWS
            or not isinstance(manifest.get("regions"), list)
            or not 1 <= len(manifest["regions"]) <= 20
            or not re.fullmatch("[a-f0-9]{64}", str(manifest.get("content_signature")))):
        raise ValueError("Untrusted static catalog manifest")
    seen = set()
    public_dir = manifest_file.parents[2]
    for region in manifest["regions"]:
        rel = region.get("path")
        if (not isinstance(rel, str) or not rel.startswith("data/v1/regions/")
                or ".." in rel or not REGION_HASH.search(rel)):
            raise ValueError("Unsafe hashed regional source asset")
        path = public_dir / rel
        raw = path.read_bytes()
        h = REGION_HASH.search(rel).group(1)
        if not digest(raw).startswith(h):
            raise ValueError("Regional source SHA-256 mismatch: " + rel)
        data = json.loads(raw)
        rows = data.get("markets")
        if (data.get("schema") != 1 or not isinstance(rows, list)
                or len(rows) != region.get("count")):
            raise ValueError("Regional source count is incorrect: " + rel)
        for row in rows:
            slug = row.get("slug") if isinstance(row, dict) else None
            if (not isinstance(slug, str) or not slug or slug in seen
                    or not all(isinstance(row.get(key), str) and row[key]
                               for key in ("nome", "citta", "regione"))):
                raise ValueError("Catalog has missing, duplicate or malformed market ID")
            seen.add(slug)
            yield row
    if len(seen) != manifest["total"]:
        raise ValueError("Incomplete catalog across regional source assets")


def dataset_meta(manifest_file: Path, git_sha: str):
    m = json.loads(Path(manifest_file).read_text(encoding="utf-8"))
    if not re.fullmatch("[a-f0-9]{40}", git_sha):
        raise ValueError("Catalog requires an immutable Git commit")
    return {
        "id": "cat-" + m["content_signature"][:28],
        "signature": m["content_signature"],
        "manifest_sha": digest(Path(manifest_file).read_bytes()),
        "git_sha": git_sha,
        "rows": m["total"],
    }


def dataset_create_sql(meta):
    return (
        "INSERT OR IGNORE INTO catalog_datasets "
        "(dataset_id,content_signature,manifest_sha256,source_git_sha,expected_rows,status) "
        "VALUES (" + ",".join(sql(meta[k]) for k in
                             ("id", "signature", "manifest_sha", "git_sha", "rows")) +
        ",'loading');\n"
    )


def market_statement(meta, row):
    data = json.dumps(row, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    data_sha = digest(data.encode("utf-8"))
    fields = [meta["id"], row["slug"], row["nome"], row["citta"],
              row.get("provincia") or "", row["regione"], row.get("fonte") or "",
              data, data_sha]
    statement = ("INSERT INTO catalog_markets "
                 "(dataset_id,slug,nome,citta,provincia,regione,fonte,payload_json,payload_sha256) "
                 "VALUES (" + ",".join(map(sql, fields)) + ") "
                 "ON CONFLICT(dataset_id,slug) DO UPDATE SET "
                 "payload_json=excluded.payload_json, payload_sha256=excluded.payload_sha256 "
                 "WHERE catalog_markets.payload_sha256!=excluded.payload_sha256;\n")
    if len(statement.encode("utf-8")) > MAX_ROW_SQL_BYTES:
        raise ValueError("Market SQL statement exceeds D1 query limit: " + row["slug"])
    return statement


def source_statement(snapshot: Path, url: str, entry: dict):
    p = snapshot / "pages" / (digest(url.encode("utf-8")) + ".json.gz")
    raw = p.read_bytes()
    if digest(raw) != entry.get("facts_sha256"):
        raise ValueError("Happings source fact hash mismatches its checkpoint")
    fact = json.loads(gzip.decompress(raw))
    if fact.get("url") != url or fact.get("status") != entry.get("status"):
        raise ValueError("Happings saved facts detached from original URL")
    html_sha = fact.get("html_sha256") or ""
    if html_sha and not HEX64.fullmatch(html_sha):
        raise ValueError("Happings HTML fingerprint is invalid")
    kind = entry.get("kind", "unknown")
    if kind not in ("weekly", "detail", "unknown"):
        raise ValueError("Untrusted Happings source type")
    values = [url, html_sha, digest(gzip.decompress(raw)), fact["read_at"],
              kind, entry["status"], base64.b64encode(raw).decode("ascii")]
    statement = ("INSERT INTO happings_source_facts "
                 "(source_url,html_sha256,facts_sha256,observed_at,source_type,source_status,facts_gzip_base64) "
                 "VALUES (" + ",".join(map(sql, values)) + ") "
                 "ON CONFLICT(source_url) DO UPDATE SET "
                 "html_sha256=excluded.html_sha256, facts_sha256=excluded.facts_sha256, "
                 "observed_at=excluded.observed_at, source_type=excluded.source_type, "
                 "source_status=excluded.source_status, facts_gzip_base64=excluded.facts_gzip_base64 "
                 "WHERE happings_source_facts.facts_sha256!=excluded.facts_sha256;\n")
    if len(statement.encode("utf-8")) > MAX_ROW_SQL_BYTES:
        raise ValueError("Source fact SQL statement exceeds D1 query limit: " + url)
    return statement


def chunked(statements):
    lines, size, n = [], 0, 0
    for stmt in statements:
        blob = stmt.encode("utf-8")
        if lines and (size + len(blob) > MAX_CHUNK_BYTES or n >= MAX_CHUNK_ROWS):
            yield "".join(lines), n
            lines, size, n = [], 0, 0
        lines.append(stmt)
        size += len(blob)
        n += 1
    if lines:
        yield "".join(lines), n


def stored_receipts(table: str, key: str, value: str):
    rows = remote_query(
        "SELECT chunk_no,chunk_sha256,num_records FROM " + table +
        " WHERE " + key + "=" + sql(value) + " ORDER BY chunk_no"
    )
    return {int(r["chunk_no"]): r for r in rows}


def check_database_budget(writes: int):
    if not 1 <= writes <= MAX_IMPORT_WRITES:
        raise ValueError("Requested D1 writes exceed fixed free-tier safety budget")
    raw = cli("info", DB_NAME, "--json", timeout=90)
    info = json.loads(raw)
    size = info.get("file_size") or info.get("database_size") or info.get("size") or 0
    if int(size) > MAX_DATABASE_BYTES:
        raise ValueError("D1 database above conservative 450 MB import threshold")


def import_statements(statements, *, table, key, value, output_log: Path):
    receipts = stored_receipts(table, key, value)
    counter = 0
    uploaded = 0
    output_log.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="mercati-d1-sql-") as temp:
        for i, (body, count) in enumerate(chunked(statements)):
            chunk_hash = digest(body.encode("utf-8"))
            previous = receipts.get(i)
            if previous:
                if (previous["chunk_sha256"] != chunk_hash or
                        int(previous["num_records"]) != count):
                    raise ValueError("Remote chunk receipt disagrees with local source")
                counter += count
                continue
            marker = ("INSERT INTO " + table +
                      "(" + key + ",chunk_no,chunk_sha256,num_records) VALUES (" +
                      ",".join([sql(value), str(i), sql(chunk_hash), str(count)]) + ");\n")
            file = Path(temp) / f"part-{i:05}.sql"
            file.write_text(body + marker, encoding="utf-8", newline="\n")
            execute_file(file)
            file.unlink()
            rows = stored_receipts(table, key, value)
            if (i not in rows or rows[i]["chunk_sha256"] != chunk_hash
                    or int(rows[i]["num_records"]) != count):
                raise ValueError("D1 import chunk lacks a verified remote checkpoint")
            receipts = rows
            counter += count
            uploaded += count
            output_log.write_text(
                json.dumps({"status":"in_progress","processed":counter,"uploaded":uploaded,
                            "chunks_verified":len(receipts),"last_chunk":i,
                            "target":value},sort_keys=True)+"\n",encoding="utf-8")
            print(json.dumps({"d1_checkpoint":i,"rows":counter,"new_rows":uploaded}),
                  flush=True)
    return counter, uploaded


def import_catalog(manifest_file: Path, git_sha: str, *, proof_file: Path, output_log: Path):
    manifest_file = Path(manifest_file)
    meta = dataset_meta(manifest_file, git_sha)
    proof = json.loads(Path(proof_file).read_text(encoding="utf-8"))
    if (proof.get("qa_gate_approved") is not True or
            proof.get("manifest_content_signature") != meta["signature"] or
            proof.get("after_records") != meta["rows"] or
            proof.get("old_unrelated_market_fields_changed") != 0):
        raise ValueError("Source-field release proof does not match the DEV catalog")
    check_database_budget(meta["rows"] + 2000)
    prior = remote_query("SELECT content_signature,manifest_sha256,expected_rows "
                         "FROM catalog_datasets WHERE dataset_id=" + sql(meta["id"]))
    if prior and (prior[0]["content_signature"] != meta["signature"] or
                  prior[0]["manifest_sha256"] != meta["manifest_sha"] or
                  prior[0]["expected_rows"] != meta["rows"]):
        raise ValueError("Dataset ID was reused for different contents")
    if not prior:
        with tempfile.TemporaryDirectory() as t:
            p = Path(t)/"init.sql"
            p.write_text(dataset_create_sql(meta),encoding="utf-8")
            execute_file(p)
    total,uploaded = import_statements(
        (market_statement(meta,row) for row in manifest_rows(manifest_file)),
        table="catalog_import_chunks",key="dataset_id",value=meta["id"],
        output_log=output_log)
    if total != meta["rows"]:
        raise ValueError("D1 import omitted catalog records")
    verified = remote_query(
        "SELECT (SELECT COUNT(*) FROM catalog_markets WHERE dataset_id=" + sql(meta["id"]) +
        ") AS markets, (SELECT COALESCE(SUM(num_records),0) FROM catalog_import_chunks "
        "WHERE dataset_id=" + sql(meta["id"]) + ") AS receipts"
    )
    if len(verified)!=1 or any(int(verified[0][x])!=meta["rows"] for x in ("markets","receipts")):
        raise ValueError("D1 remote market count or chunk receipt count is wrong")
    status = ("UPDATE catalog_datasets SET status='ready', "
              "ready_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE dataset_id=" +
              sql(meta["id"])+" AND expected_rows=" + str(meta["rows"]) +
              " AND status IN ('loading','ready');")
    remote_query(status)
    # The change of DEV pointer is atomic. PROD is not read or written here.
    previous = remote_query("SELECT dataset_id FROM catalog_channels WHERE channel='dev'")
    prior_dev = previous[0]["dataset_id"] if previous else None
    evidence = json.dumps({"source":"DEV GitHub static catalog","git_sha":git_sha,
                           "catalog_signature":meta["signature"],
                           "Happings_field_proof":proof.get("address_fields_filled"),
                           "Happings_hours_proof":proof.get("qualitative_hour_fields_filled")},
                          ensure_ascii=False,sort_keys=True)
    event_id = digest((meta["id"]+"|dev|"+str(prior_dev)).encode("utf-8"))
    remote_query(
        "INSERT OR IGNORE INTO release_audit"
        "(event_id,channel,old_dataset_id,new_dataset_id,decision,evidence_json) VALUES (" +
        ",".join(map(sql,[event_id,"dev",prior_dev,meta["id"],"source_QA_passed",evidence])) + ")"
    )
    remote_query(
        "UPDATE catalog_channels SET dataset_id=" + sql(meta["id"]) +
        ",activated_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') "
        "WHERE channel='dev' AND EXISTS (SELECT 1 FROM catalog_datasets "
        "WHERE dataset_id=" + sql(meta["id"]) + " AND status='ready')")
    current = remote_query("SELECT channel,dataset_id FROM catalog_channels ORDER BY channel")
    actual = {r["channel"]:r["dataset_id"] for r in current}
    if actual.get("dev")!=meta["id"]:
        raise ValueError("DEV channel head was not activated")
    if not any(r["channel"]=="prod" for r in current):
        raise ValueError("PROD channel disappeared")
    summary = {"status":"dev_imported","dataset_id":meta["id"],
               "records":total,"uploaded_in_this_run":uploaded,
               "dev_head":actual.get("dev"),"prod_head":actual.get("prod"),
               "manifest_signature":meta["signature"]}
    output_log.write_text(json.dumps(summary,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(summary,sort_keys=True),flush=True)
    return summary


def import_facts(snapshot:Path, *, output_log:Path):
    snapshot=Path(snapshot)
    state=json.loads((snapshot/"checkpoint.json").read_text(encoding="utf-8"))
    queue,done=state.get("queue"),state.get("done")
    if (state.get("schema")!=1 or not isinstance(queue,list)
            or not isinstance(done,dict) or not 1<=len(queue)<=50000
            or set(queue)!=set(done) or len(queue)!=len(set(queue))):
        raise ValueError("Incomplete Happings crawl checkpoint")
    import_id = "happings-" + digest((snapshot/"checkpoint.json").read_bytes())[:24]
    check_database_budget(len(queue)+1000)
    total,uploaded = import_statements(
        (source_statement(snapshot,url,done[url]) for url in queue),
        table="source_import_chunks",key="import_id",value=import_id,
        output_log=output_log)
    actual=scalar("SELECT COUNT(*) AS count FROM happings_source_facts", "count")
    if total!=len(queue) or int(actual)<len(queue):
        raise ValueError("Happings remote source facts are incomplete")
    report={"status":"source_imported","observations":len(queue),
            "uploaded_in_this_run":uploaded,"remote_source_facts":int(actual),
            "import_id":import_id}
    output_log.write_text(json.dumps(report,sort_keys=True)+"\n",encoding="utf-8")
    print(json.dumps(report,sort_keys=True),flush=True)
    return report


def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("action",choices=("catalog","sources","status"))
    ap.add_argument("--manifest",type=Path)
    ap.add_argument("--source-git-sha")
    ap.add_argument("--proof",type=Path)
    ap.add_argument("--snapshot",type=Path)
    ap.add_argument("--output-log",type=Path)
    args=ap.parse_args()
    default=Path(os.environ.get("LOCALAPPDATA") or tempfile.gettempdir())/"mercati-italia"
    output=args.output_log or default/"d1-catalog-sync-checkpoint.json"
    if args.action=="catalog":
        if not all((args.manifest,args.source_git_sha,args.proof)):
            ap.error("catalog requires manifest, source-git-sha and proof")
        import_catalog(args.manifest,args.source_git_sha,proof_file=args.proof,output_log=output)
    elif args.action=="sources":
        if not args.snapshot:
            ap.error("sources requires snapshot")
        import_facts(args.snapshot,output_log=output)
    else:
        print(json.dumps(remote_query(
            "SELECT channel,dataset_id,activated_at FROM catalog_channels ORDER BY channel"),
            sort_keys=True))


if __name__=="__main__":
    main()
