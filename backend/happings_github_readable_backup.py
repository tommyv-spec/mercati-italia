"""Create transparent, reproducible Happings source-fact JSON backup shards.

No opaque binaries, local paths, tokens or GitHub paid services. Each source
document is validated against the local SHA-256 checkpoint before export.
"""
from __future__ import annotations
import argparse
import gzip
import hashlib
import json
from pathlib import Path
from happings_full_reconciliation import _saved_page

MAX_SHARD=145_000
REPORTS={"happings-source-reconciliation.json",
         "happings-source-worklist.json","happings-detail-match-report.json",
         "happings-detail-match-worklist.json","happings-detail-join-audit.json",
         "happings-detail-join-worklist.json","happings-weekly-admission.json",
         "weekly-candidate-dry-run.json","happings-source-html-index.json"}

def encode(v):
    return (json.dumps(v,ensure_ascii=False,sort_keys=True,
                       separators=(",",":"))+"\n").encode("utf-8")
def sha(v):
    return hashlib.sha256(v).hexdigest()

def run(root,out):
    root,out=Path(root),Path(out)
    checkpoint=root/"happings-full-crawl/checkpoint.json"
    snapshot=root/"happings-full-crawl"
    state=json.loads(checkpoint.read_text("utf-8"))
    queue,done=state.get("queue"),state.get("done")
    if (state.get("schema")!=1 or not isinstance(queue,list)
            or not isinstance(done,dict) or not 1<=len(queue)<=50_000 or len(done)!=len(queue)
            or len(set(queue))!=len(queue) or set(done)!=set(queue)):
        raise ValueError("Refusing incomplete Happings source snapshot")
    out.mkdir(parents=True,exist_ok=True)
    manifest={"schema":1,"format":"public-source-facts-json-v1",
              "source_pages":len(queue),"original_checkpoint_sha256":sha(checkpoint.read_bytes()),
              "source_facts_are_html_parses_not_original_html":True,
              "shards":[],"reports":[]}
    current=[];currentbytes=0;idx=0
    def flush():
        nonlocal current,currentbytes,idx
        if not current:return
        name=f"source-facts-{idx:03}.json"
        body=encode({"schema":1,"pages":current})
        (out/name).write_bytes(body)
        manifest["shards"].append({"path":name,"sha256":sha(body),"bytes":len(body),"records":len(current)})
        idx+=1;current=[];currentbytes=0
    for position,url in enumerate(queue):
        entry=done[url]
        fact=_saved_page(snapshot,url,entry)
        item={"ordinal":position,"url":url,"checkpoint_entry":entry,
              "fact":fact}
        size=len(encode(item))
        if current and currentbytes+size>MAX_SHARD:flush()
        current.append(item);currentbytes+=size
    flush()
    for report in sorted((root/"happings-reconciliation").glob("*.json")):
        if report.name not in REPORTS:continue
        obj=json.loads(report.read_text("utf-8"))
        is_list=isinstance(obj,list)
        values=obj if is_list else [obj]
        chunks=[];batches=[];counter=0
        def write_batch(rows):
            nonlocal counter
            name=f"report-{report.stem}-{counter:03}.json"
            body=encode({"schema":1,"items":rows})
            (out/name).write_bytes(body)
            chunks.append({"path":name,"sha256":sha(body),"bytes":len(body),"records":len(rows)})
            counter+=1
        for item in values:
            val=encode(item)
            if batches and sum(len(encode(x)) for x in batches)+len(val)>MAX_SHARD:
                write_batch(batches);batches=[]
            batches.append(item)
        if batches:write_batch(batches)
        manifest["reports"].append({"original":report.name,"is_list":is_list,"chunks":chunks})
    proof=root/"audit-run-39652026641/happings-postrelease-proof.json"
    if proof.is_file():
        value=json.loads(proof.read_text("utf-8"))
        name="report-happings-postrelease-proof-000.json"
        body=encode({"schema":1,"items":[value]})
        (out/name).write_bytes(body)
        manifest["reports"].append({"original":"happings-postrelease-proof.json",
            "is_list":False,"chunks":[{"path":name,"sha256":sha(body),"bytes":len(body),"records":1}]})
    raw=encode(manifest)
    (out/"manifest.json").write_bytes(raw)
    print(json.dumps({"page_shards":len(manifest["shards"]),"reports":len(manifest["reports"]),
        "source_pages":len(queue),"manifest_sha256":sha(raw),
        "total_files":len(list(out.glob("*.json"))),
        "total_bytes":sum(f.stat().st_size for f in out.glob("*.json"))},sort_keys=True),flush=True)
    return manifest

def _verified_json_bytes(path, declaration, message):
    """Read exact source bytes, tolerating ONLY Git's Windows final CRLF.

    Plain-Git text archives are one-line JSON ending with LF. On Windows
    core.autocrlf=true changes that final line ending to CRLF in the worktree.
    The original SHA-256 must still match after reversing precisely that one
    transport transformation; any other change remains a hard failure.
    """
    raw=Path(path).read_bytes()
    def matches(blob):
        return len(blob)==declaration["bytes"] and sha(blob)==declaration["sha256"]
    if matches(raw):
        return raw
    if raw.endswith(b"\r\n"):
        original=raw[:-2]+b"\n"
        if matches(original):
            return original
    raise ValueError(message)


def verify(out):
    out=Path(out);m=json.loads((out/"manifest.json").read_text("utf-8"))
    seen=set();count=0
    for section in m["shards"]:
        body=_verified_json_bytes(
            out/section["path"],section,"Happings source shard hash mismatch")
        entries=json.loads(body)["pages"]
        if len(entries)!=section["records"]:raise ValueError("Truncated Happings source chunk")
        for item in entries:
            if item["ordinal"] in seen or item["fact"]["url"]!=item["url"]:
                raise ValueError("Duplicated or detached publisher source facts")
            seen.add(item["ordinal"]);count+=1
    if count!=m["source_pages"] or seen!=set(range(count)):
        raise ValueError("Not all indexed Happings source documents were backed up")
    for report in m["reports"]:
        for part in report["chunks"]:
            raw=_verified_json_bytes(
                out/part["path"],part,"Report shard hash mismatch")
            if len(json.loads(raw)["items"])!=part["records"]:
                raise ValueError("Report shard item count mismatch")
    return count


def restore(source, destination):
    """Rebuild a refreshable snapshot from GitHub's transparent source facts.

    Restored gzips may differ byte-for-byte from the originals; we compute new
    hashes of the actual files. Original source HTML SHA-256 is preserved.
    Never overwrite an active crawler or existing user files.
    """
    import re
    from happings_weekly_layout import _valid_page_url
    from happings_detail_discovery import url_kind
    from happings_full_reconciliation import _saved_page

    source,destination=Path(source),Path(destination)
    if destination.exists() and any(destination.iterdir()):
        raise ValueError("Restore needs an empty destination; active source files are protected")
    if verify(source)<1:
        raise ValueError("The source archive contains no validated documents")
    manifest=json.loads((source/"manifest.json").read_text("utf-8"))
    by_ordinal={}
    for shard in manifest["shards"]:
        payload=json.loads((source/shard["path"]).read_text("utf-8"))
        for record in payload["pages"]:
            index,url,entry,fact=(record.get(key) for key in
                                  ("ordinal","url","checkpoint_entry","fact"))
            if (type(index) is not int or index<0 or index>=manifest["source_pages"]
                    or index in by_ordinal or not isinstance(url,str)
                    or not (_valid_page_url(url) or url_kind(url)=="detail")
                    or not isinstance(entry,dict) or entry.get("status") not in
                        {"parsed","unassessed","unavailable","robots_denied"}
                    or not isinstance(fact,dict) or fact.get("url")!=url
                    or fact.get("status")!=entry.get("status")
                    or not re.fullmatch("[a-f0-9]{64}",str(entry.get("facts_sha256") or ""))):
                raise ValueError("A backed-up page has an untrusted identity or checksum")
            by_ordinal[index]=(url,entry,fact)
    if len(by_ordinal)!=manifest["source_pages"]:
        raise ValueError("Missing ordinal in GitHub Happings backup")

    destination.mkdir(parents=True,exist_ok=True)
    snapshot=destination/"happings-full-crawl"
    reports=destination/"happings-reconciliation"
    (snapshot/"pages").mkdir(parents=True)
    reports.mkdir(parents=True)
    done={};queue=[]
    for position in range(manifest["source_pages"]):
        url,old_entry,fact=by_ordinal[position]
        raw=(json.dumps(fact,sort_keys=True,ensure_ascii=False,
                        default=str)+"\n").encode("utf-8")
        packed=gzip.compress(raw,mtime=0)
        output=snapshot/"pages"/(hashlib.sha256(url.encode("utf-8")).hexdigest()+".json.gz")
        output.write_bytes(packed)
        queue.append(url)
        done[url]={**old_entry,"facts_sha256":sha(packed),
                   "original_gzip_sha256":old_entry["facts_sha256"]}
    state={"schema":1,"started_at":min(
        (fact.get("read_at") for _,_,fact in by_ordinal.values()
         if isinstance(fact.get("read_at"),str)),default=""),
           "queue":queue,"done":done,"discovery":{}}
    (snapshot/"checkpoint.json").write_bytes(encode(state))
    for report in manifest["reports"]:
        name=report.get("original")
        if (not isinstance(name,str) or not re.fullmatch(r"[a-z0-9-]+\.json",name)
                or (reports/name).exists()):
            raise ValueError("Unsafe or repeated report name")
        items=[]
        for chunk in report["chunks"]:
            items.extend(json.loads((source/chunk["path"]).read_text("utf-8"))["items"])
        if not report.get("is_list") and len(items)!=1:
            raise ValueError("A source report lost its single-object identity")
        (reports/name).write_bytes(encode(items if report["is_list"] else items[0]))
    for url in queue:
        _saved_page(snapshot,url,done[url])
    return {"source_pages_restored":len(queue),
            "reports_restored":len(manifest["reports"]),
            "new_checkpoint_sha256":sha((snapshot/"checkpoint.json").read_bytes()),
            "original_checkpoint_sha256":manifest["original_checkpoint_sha256"],
            "byte_identical_gzip_claimed":False,
            "source_html_sha256_preserved":True}


if __name__=="__main__":
    ap=argparse.ArgumentParser()
    ap.add_argument("--root",type=Path)
    ap.add_argument("--out",type=Path,required=True)
    ap.add_argument("--restore-to",type=Path)
    args=ap.parse_args()
    if args.restore_to:
        print("RESTORED",json.dumps(restore(args.out,args.restore_to)))
    elif args.root:
        run(args.root,args.out)
        print("VERIFIED",verify(args.out))
    else:
        print("VERIFIED",verify(args.out))
