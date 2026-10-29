#!/usr/bin/env python3
"""Rebuild data/istat-comuni-soppressi.json from ISTAT's two official lists.

Merged comuni ("Elenco comuni soppressi", back to 1861) and renamed ones
(name changes "CD" in "Variazioni amministrative e territoriali dal 1991").
municipality_reconciliation follows each old name to today's comune.

--check (weekly, ops/workflows/istat-reference-check.yml) only compares ISTAT's published
files with the pinned copies of both lists, and fails when ISTAT has published new ones.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import time
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

MERGED_URL = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-soppressi.zip"
RENAMED_URL = "https://www.istat.it/storage/codici-unita-amministrative/Variazioni-amministrative-e-territoriali-dal-1991.zip"
OUT = Path(__file__).resolve().parent / "data" / "istat-comuni-soppressi.json"
CURRENT = OUT.parent / "istat-comuni-2026.json"


def fetch(url, tries=3):
    # istat.it is sometimes slow (one read took over 60 s): a slow night is not an alarm.
    for attempt in range(tries):
        try:
            return urlopen(Request(url, headers={"User-Agent": "mercati-italia/istat"}), timeout=120).read()
        except OSError:
            if attempt == tries - 1:
                raise
            time.sleep(30)


def check():
    """URLs of the ISTAT files that no longer match our pinned copies."""
    current = json.loads(CURRENT.read_text(encoding="utf-8"))
    pins = [(s["url"], s["sha256"]) for s in json.loads(OUT.read_text(encoding="utf-8"))["sources"]]
    pins.append((current["source"], current["source_file_sha256"]))
    changed = []
    for url, sha in pins:
        if hashlib.sha256(fetch(url)).hexdigest() != sha:
            changed.append(url)
        time.sleep(3)
    return changed


def read_csv(url):
    raw = fetch(url)
    with zipfile.ZipFile(io.BytesIO(raw)) as archive:
        name = next(n for n in archive.namelist() if n.lower().endswith(".csv"))
        text = archive.read(name).decode("latin-1")
    return hashlib.sha256(raw).hexdigest(), list(csv.DictReader(io.StringIO(text), delimiter=";"))


def build():
    merged_sha, merged = read_csv(MERGED_URL)
    renamed_sha, changes = read_csv(RENAMED_URL)
    links = {(r["Denominazione Comune"].strip(), r["Denominazione Comune associato alla variazione"].strip(), "soppresso")
             for r in merged}
    links |= {(r["Denominazione Comune"].strip(),
               r["Denominazione Comune associata alla variazione o nuova denominazione"].strip(), "rinominato")
              for r in changes if r["Tipo variazione"] == "CD"}
    links = sorted(link for link in links if all(link))
    if len(links) < 2500:
        raise ValueError("ISTAT former-comuni lists look incomplete")
    return {
        "schema": 1,
        "attribution": "© ISTAT – Elenco comuni soppressi; Variazioni amministrative e territoriali dal 1991, CC BY 4.0",
        "sources": [{"url": MERGED_URL, "sha256": merged_sha}, {"url": RENAMED_URL, "sha256": renamed_sha}],
        "source_license": "https://www.istat.it/note-legali/",
        "links": [list(link) for link in links],
    }


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=OUT)
    parser.add_argument("--check", action="store_true", help="only compare with the pinned copies")
    args = parser.parse_args()
    if args.check:
        changed = check()
        for url in changed:
            print("ISTAT_LIST_CHANGED", url)
        print("ISTAT_LISTS_CURRENT" if not changed else
              "Rebuild the pinned list(s), then review the town rules (CONTROLLO_FONTI S31)")
        raise SystemExit(1 if changed else 0)
    data = build()
    head = json.dumps({**data, "links": []}, ensure_ascii=False, indent=1)[:-len('[]\n}')]
    lines = ",\n".join(json.dumps(link, ensure_ascii=False) for link in data["links"])
    args.out.write_text(head + "[\n" + lines + "\n ]\n}\n", encoding="utf-8")
    print(len(data["links"]), "links ->", args.out)
