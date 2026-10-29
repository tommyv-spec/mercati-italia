#!/usr/bin/env python3
"""Rebuild data/istat-comuni-soppressi.json from ISTAT's two official lists.

Merged comuni ("Elenco comuni soppressi", back to 1861) and renamed ones
(name changes "CD" in "Variazioni amministrative e territoriali dal 1991").
municipality_reconciliation follows each old name to today's comune.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import zipfile
from pathlib import Path
from urllib.request import Request, urlopen

MERGED_URL = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-soppressi.zip"
RENAMED_URL = "https://www.istat.it/storage/codici-unita-amministrative/Variazioni-amministrative-e-territoriali-dal-1991.zip"
OUT = Path(__file__).resolve().parent / "data" / "istat-comuni-soppressi.json"


def read_csv(url):
    raw = urlopen(Request(url, headers={"User-Agent": "mercati-italia/istat"}), timeout=60).read()
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
    args = parser.parse_args()
    data = build()
    head = json.dumps({**data, "links": []}, ensure_ascii=False, indent=1)[:-len('[]\n}')]
    lines = ",\n".join(json.dumps(link, ensure_ascii=False) for link in data["links"])
    args.out.write_text(head + "[\n" + lines + "\n ]\n}\n", encoding="utf-8")
    print(len(data["links"]), "links ->", args.out)
