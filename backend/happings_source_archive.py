"""Portable, checksum-bound archive for Happings source evidence and audits.

No paid GitHub storage/API/runner. Generates deterministic small Git-friendly
binary parts rather than adding 2,313 files to a live website or Git LFS.
Publishing is a separate reviewed DEV repository operation.

make --data-dir PATH --out PATH [--publisher-run-artifact PATH]
verify --out PATH
restore --out PATH --destination PATH  (refuse any overwrite)
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import re
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

from happings_full_reconciliation import _saved_page

SCHEMA=1
PART_SIZE=192*1024
MAX_MEMBERS=2600
MAX_ARCHIVE_BYTES=20_000_000
MAX_SINGLE_MEMBER=13_000_000
MAX_TOTAL_UNPACKED=38_000_000
SAFE_NAME=re.compile(r"(?:snapshot/(?:pages/[a-f0-9]{64}\.json\.gz|(?:checkpoint|summary|refresh-status|retry-status)\.json)|"
                     r"reports/(?:[a-z0-9-]+\.json|happings-source-html/[a-f0-9-]+\.html\.gz)|"
                     r"publication/(?:happings-enrichment\.json|happings-weekly-admission\.json|"
                     r"happings-postrelease-proof\.json|sources/happings-pages\.json))\Z")


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def members(data_dir, publisher_run_artifact=None):
    directory=Path(data_dir)
    snapshot=directory/"happings-full-crawl"
    reports=directory/"happings-reconciliation"
    if not (snapshot/"checkpoint.json").is_file():
        raise ValueError("No source checkpoint to publish on GitHub")
    state=json.loads((snapshot/"checkpoint.json").read_text("utf-8"))
    queue,done=state.get("queue"),state.get("done")
    if (state.get("schema")!=1 or not isinstance(queue,list)
            or not isinstance(done,dict) or not 1<=len(queue)<=MAX_MEMBERS
            or len(queue)!=len(done) or set(queue)!=set(done)):
        raise ValueError("Refusing incomplete or untrusted publisher snapshot")
    if any(item.get("status")!="parsed" for item in done.values()):
        raise ValueError("Publisher extraction failures must remain visible and be retried")
    for url,entry in done.items():
        _saved_page(snapshot,url,entry)
    collected={}
    for file in sorted(snapshot.glob("*.json")):
        if file.name not in {"checkpoint.json","summary.json","retry-status.json","refresh-status.json"}:
            continue
        collected["snapshot/"+file.name]=file.read_bytes()
    for file in sorted((snapshot/"pages").glob("*.json.gz")):
        collected["snapshot/pages/"+file.name]=file.read_bytes()
    if len([key for key in collected if key.startswith("snapshot/pages/")])!=len(queue):
        raise ValueError("Source fact inventory has extra or missing page records")
    for file in sorted(reports.glob("*.json")):
        if file.name=="happings-local-run.json":
            # Avoid leaking Windows username, local paths, process or device.
            info=json.loads(file.read_text("utf-8"))
            report={"schema":1,"status":info.get("status"),
                    "finished_at":info.get("completed_at"),
                    "sources_processed":info.get("qa",{}).get("pages_total"),
                    "dev_revision_analyzed":info.get("qa",{}).get("dev_sha")}
            collected["reports/local-run-public.json"]=(json.dumps(
                report,ensure_ascii=False,sort_keys=True)+"\n").encode("utf-8")
        else:
            collected["reports/"+file.name]=file.read_bytes()
    for file in sorted((reports/"happings-source-html").glob("*.html.gz")):
        collected["reports/happings-source-html/"+file.name]=file.read_bytes()
    if publisher_run_artifact:
        qa=Path(publisher_run_artifact)
        for file in ("happings-enrichment.json","happings-weekly-admission.json",
                     "happings-postrelease-proof.json","sources/happings-pages.json"):
            full=qa/file
            if full.is_file():
                collected["publication/"+file]=full.read_bytes()
        if "publication/happings-postrelease-proof.json" not in collected:
            raise ValueError("Cannot archive DEV admission without its independent proof")
    if len(collected)>MAX_MEMBERS+32:
        raise ValueError("Too many source fact files")
    for name,raw in collected.items():
        if not SAFE_NAME.fullmatch(name) or not 1<=len(raw)<=MAX_SINGLE_MEMBER:
            raise ValueError("Unreviewed or excessive archive member: "+name)
    return collected,{"source_pages":len(queue),
                      "source_page_statuses":{"parsed":len(queue)},
                      "source_snapshot_sha256":sha((snapshot/"checkpoint.json").read_bytes()),
                      "publisher":"happings.com",
                      "project_source":"tommyv-spec/mercati-italia"}


def build(data_dir,out,*,publisher_run_artifact=None):
    files,source=members(data_dir,publisher_run_artifact)
    out=Path(out)
    out.mkdir(parents=True,exist_ok=True)
    zip_buffer=io.BytesIO()
    meta=[]
    with zipfile.ZipFile(zip_buffer,"w",compression=zipfile.ZIP_DEFLATED,
                         compresslevel=8,allowZip64=False) as archive:
        for name in sorted(files):
            body=files[name]
            entry=zipfile.ZipInfo(name,(1980,1,1,0,0,0))
            entry.compress_type=zipfile.ZIP_DEFLATED
            archive.writestr(entry,body,compress_type=zipfile.ZIP_DEFLATED,compresslevel=8)
            meta.append({"path":name,"bytes":len(body),"sha256":sha(body)})
    packed=zip_buffer.getvalue()
    if len(packed)>MAX_ARCHIVE_BYTES:
        raise ValueError("Snapshot too large for the free plain-Git quota budget")
    pieces=[]
    for index,start in enumerate(range(0,len(packed),PART_SIZE)):
        part=packed[start:start+PART_SIZE]
        name=f"happings-facts-part-{index:03}.bin"
        (out/name).write_bytes(part)
        (out/(name+".b64")).write_text(base64.b64encode(part).decode("ascii")+"\n",
                                        encoding="ascii")
        pieces.append({"path":name,"bytes":len(part),"sha256":sha(part)})
    descriptor={
        "schema":SCHEMA,"format":"deterministic-zip-chunks",
        "generated_on":date.today().isoformat(),
        "publisher":"happings.com",
        "target":"GitHub ordinary Git blobs; no Git LFS or paid storage",
        "source":source,"compressed_archive_sha256":sha(packed),
        "compressed_bytes":len(packed),
        "member_count":len(meta),
        "members":meta,
        "part_size":PART_SIZE,
        "parts":pieces
    }
    (out/"archive-manifest.json").write_text(
        json.dumps(descriptor,ensure_ascii=False,sort_keys=True,indent=2)+"\n","utf-8")
    print(json.dumps({"members":len(files),"pages":source["source_pages"],
                      "archive_bytes":len(packed),"parts":len(pieces),
                      "source_sha256":source["source_snapshot_sha256"]},sort_keys=True),flush=True)
    return descriptor


def verified_bytes(out):
    out=Path(out)
    descriptor=json.loads((out/"archive-manifest.json").read_text("utf-8"))
    if (descriptor.get("schema")!=SCHEMA or descriptor.get("format")!="deterministic-zip-chunks"
            or not isinstance(descriptor.get("parts"),list)
            or not 1<=len(descriptor["parts"])<=150
            or not isinstance(descriptor.get("members"),list)
            or not 1<=len(descriptor["members"])<=MAX_MEMBERS+32):
        raise ValueError("Invalid GitHub archive manifest")
    parts=[]
    for index,entry in enumerate(descriptor["parts"]):
        if entry.get("path")!=f"happings-facts-part-{index:03}.bin":
            raise ValueError("Archive chunk numbering changed")
        data=(out/entry["path"]).read_bytes()
        if not 0<len(data)<=PART_SIZE or len(data)!=entry.get("bytes") or sha(data)!=entry.get("sha256"):
            raise ValueError("GitHub archive chunk hash or size mismatch")
        parts.append(data)
    packed=b"".join(parts)
    if (len(packed)!=descriptor.get("compressed_bytes")
            or len(packed)>MAX_ARCHIVE_BYTES
            or sha(packed)!=descriptor.get("compressed_archive_sha256")):
        raise ValueError("GitHub archive global checksum mismatch")
    expected={item["path"]:item for item in descriptor["members"]}
    if len(expected)!=len(descriptor["members"]):
        raise ValueError("Duplicate manifest member names")
    verified={}
    with zipfile.ZipFile(io.BytesIO(packed),"r") as archive:
        names=archive.namelist()
        if len(names)!=len(expected) or len(set(names))!=len(names) or set(names)!=set(expected):
            raise ValueError("GitHub ZIP entries do not match reviewed manifest")
        total=0
        for path in names:
            meta=expected[path]
            if not SAFE_NAME.fullmatch(path):
                raise ValueError("ZIP entry is outside Happings source scope")
            entry=archive.getinfo(path)
            if entry.is_dir() or entry.file_size>MAX_SINGLE_MEMBER:
                raise ValueError("Unexpected ZIP metadata or size")
            total+=entry.file_size
            if total>MAX_TOTAL_UNPACKED:
                raise ValueError("ZIP total unpacked bytes exceed safe budget")
            raw=archive.read(path)
            if len(raw)!=meta["bytes"] or sha(raw)!=meta["sha256"]:
                raise ValueError("Source fact ZIP checksum mismatch")
            verified[path]=raw
    return descriptor,verified


def restore(out,destination):
    descriptor,contents=verified_bytes(out)
    target=Path(destination)
    if target.exists() and any(target.iterdir()):
        raise ValueError("Refusing restore over an existing local source catalog")
    target.mkdir(parents=True,exist_ok=True)
    for name,body in contents.items():
        path=target.joinpath(*name.split("/"))
        if not path.resolve().is_relative_to(target.resolve()):
            raise ValueError("Unsafe restore traversal")
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_bytes(body)
    return {"restored_files":len(contents),
            "source_pages":descriptor["source"]["source_pages"],
            "destination":str(target)}


def main():
    ap=argparse.ArgumentParser()
    sub=ap.add_subparsers(dest="operation",required=True)
    make=sub.add_parser("make")
    make.add_argument("--data-dir",type=Path,required=True)
    make.add_argument("--out",type=Path,required=True)
    make.add_argument("--publisher-run-artifact",type=Path)
    verify=sub.add_parser("verify")
    verify.add_argument("--out",type=Path,required=True)
    restore_cmd=sub.add_parser("restore")
    restore_cmd.add_argument("--out",type=Path,required=True)
    restore_cmd.add_argument("--destination",type=Path,required=True)
    args=ap.parse_args()
    if args.operation=="make":
        build(args.data_dir,args.out,publisher_run_artifact=args.publisher_run_artifact)
    elif args.operation=="verify":
        descriptor,contents=verified_bytes(args.out)
        print(json.dumps({"verified":True,"members":len(contents),
                          "source_pages":descriptor["source"]["source_pages"]}))
    elif args.operation=="restore":
        print(json.dumps(restore(args.out,args.destination),sort_keys=True))


if __name__=="__main__":
    main()
