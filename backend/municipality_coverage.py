#!/usr/bin/env python3
"""Read-only ISTAT municipality coverage: where to investigate missing venues.

Zero listed markets in one municipality does NOT mean that a market exists.
Compare Italian regional identities only, never infer new events or verify dates.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from pathlib import Path

from catalog_quality_report import suspicious_city
from merge_catalog import load_existing

PINNED_ISTAT_SHA = "83842076860450f7e482daecea6b7a769f5f93d0bf5b0d48802b44896d7a26d5"


def normalize_name(value):
    s = unicodedata.normalize("NFKD", str(value or "").casefold())
    ascii_text = "".join(ch for ch in s if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+", " ", ascii_text).strip()


def compare(markets: list[dict], istat: dict) -> dict:
    if not isinstance(markets, list) or not markets:
        raise ValueError("Empty catalog; cannot assess municipal coverage")
    if (istat.get("schema") != 1 or istat.get("reference_date") != "2026-02-21"
            or istat.get("source_file_sha256") != PINNED_ISTAT_SHA
            or istat.get("municipality_count") != 7894
            or not isinstance(istat.get("regions"),dict)):
        raise ValueError("ISTAT reference unexpectedly changed")
    registry = {}
    for region,names in istat["regions"].items():
        if not isinstance(region,str) or not isinstance(names,list):
            raise ValueError("Malformed official municipalities")
        mapping={}
        for name in names:
            norm=normalize_name(name)
            if not norm or norm in mapping:
                raise ValueError("Duplicate official municipality identity")
            mapping[norm]=name
        registry[region]=mapping
    if sum(len(names) for names in registry.values()) != istat["municipality_count"]:
        raise ValueError("Incomplete ISTAT municipality inventory")
    covered=defaultdict(set)
    unknown_city_examples=[]
    seen=set()
    for row in markets:
        sid=row.get("slug")
        if not isinstance(sid,str) or not sid or sid in seen:
            raise ValueError("Duplicate or missing catalog ID")
        seen.add(sid)
        region=row.get("regione")
        city=row.get("citta")
        if region not in registry or not isinstance(city,str):
            raise ValueError("Market region/city missing from declared catalogue")
        if suspicious_city(city):
            continue
        code=normalize_name(city)
        if code in registry[region]:
            covered[region].add(code)
        elif len(unknown_city_examples)<15:
            # May be frazioni, former municipalities, or source mistakes;
            # NEVER rename them based on approximate string similarity.
            unknown_city_examples.append({"region":region,"reported_city":city[:100]})
    rows=[]
    for region, municipalities in registry.items():
        matched=covered[region]
        missing=[name for code,name in municipalities.items() if code not in matched]
        # Hash-based sample avoids systematically picking municipalities
        # starting with "A". Sampling never adds hypothetical markets.
        examples=sorted(missing,key=lambda n:(
            hashlib.sha256((region+":"+n).encode()).hexdigest(),n))[:8]
        rows.append({
            "region":region,"istat_municipalities":len(municipalities),
            "with_at_least_one_catalog_market":len(matched),
            "without_catalog_market":len(missing),
            "represented_percent":round(100*len(matched)/len(municipalities),1),
            "unrepresented_examples_for_source_search":sorted(examples),
        })
    rows.sort(key=lambda r:(-r["without_catalog_market"],r["region"]))
    covered_total=sum(x["with_at_least_one_catalog_market"] for x in rows)
    return {
        "schema":1,"review_only":True,"istat_reference_date":"2026-02-21",
        "istat_original_sha256":PINNED_ISTAT_SHA,
        "catalog_market_ids_preserved":len(markets),
        "catalog_entries_added":0,"events_confirmed":0,
        "municipalities_total":7894,
        "municipalities_with_catalog_listings":covered_total,
        "municipalities_without_catalog_listings":7894-covered_total,
        "represented_percent":round(100*covered_total/7894,1),
        "regions":rows,
        "unmatched_city_examples":unknown_city_examples,
        "interpretation":"absence of a listing is NOT evidence a municipality has any active market",
    }


def markdown(result):
    out=[
        "# Mercati d'Italia — copertura dei Comuni ISTAT",
        "",
        "**Attenzione:** un Comune senza schede non implica che esista un mercato mancante.",
        "I risultati indicano dove cercare fonti comunali o regionali affidabili.",
        "",
        f"- Comuni ISTAT: **{result['municipalities_total']:,}**.",
        f"- Comuni con almeno una scheda nel catalogo: **{result['municipalities_with_catalog_listings']:,}** "
        f"({result['represented_percent']}%).",
        f"- Comuni senza schede in catalogo: **{result['municipalities_without_catalog_listings']:,}**.",
        f"- Schede esistenti conservate: **{result['catalog_market_ids_preserved']:,}**; nuove schede: **0**.",
        "",
        "| Regione | Comuni ufficiali | Con almeno una scheda | Senza schede | Copertura |",
        "|---|---:|---:|---:|---:|",
    ]
    for r in result["regions"]:
        out.append(f"| {r['region']} | {r['istat_municipalities']} | "
                   f"{r['with_at_least_one_catalog_market']} | {r['without_catalog_market']} | "
                   f"{r['represented_percent']}% |")
    out.extend(["","## Spunti distribuiti per nuove ricerche","",
                "Esempi selezionati stabilmente per regione (non sono mercati identificati).",""])
    for r in result["regions"]:
        out.append(f"- **{r['region']}:** " + ", ".join(
            r["unrepresented_examples_for_source_search"]))
    out.extend(["","## Come migliorare la quantità senza falsi dati","",
                "1. Individuare enti editori ufficiali per i Comuni senza schede.",
                "2. Controllare elenco mercati, strada, giorno, date aggiornamento dati e diritti di riuso.",
                "3. Confrontare sede/giorno con schede limitrofe: stesso mercato non deve essere duplicato.",
                "4. Importare solo mercati effettivi con provenienza, ID stabili, QA e nessuna falsa conferma.",
                ""])
    return "\n".join(out)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--istat",type=Path,default=Path("backend/data/istat-comuni-2026.json"))
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    a=p.parse_args()
    result=compare(load_existing(a.manifest),json.loads(a.istat.read_text("utf-8")))
    for path in (a.out,a.report):
        path.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n","utf-8")
    a.report.write_text(markdown(result),"utf-8")
    print("MUNICIPALITY_COVERAGE",json.dumps({
        "official":result["municipalities_total"],
        "represented":result["municipalities_with_catalog_listings"],
        "unrepresented":result["municipalities_without_catalog_listings"],
        "new_markets":0,
    }))


if __name__=="__main__":
    main()
