#!/usr/bin/env python3
"""Bounded, read-only municipal market DATA audit, not a dataset-date scout.

A CSV changed in October can contain expired vendor concessions from 2024.
This checker inspects the contents of a few CKAN municipal source CSVs/day,
never counts stalls or concessions as individual markets, and never imports.
Only aggregate quality metrics and hashes are persisted; no vendor rows.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import ipaddress
import json
import re
import socket
import unicodedata
from datetime import date
from pathlib import Path
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

HOST = "opendata.boxxapps.com"
CATALOG = "https://opendata.boxxapps.com/api/3/action/package_search"
UUID = r"[0-9a-f]{8}-(?:[0-9a-f]{4}-){3}[0-9a-f]{12}"
CSV_PATH = re.compile(
    rf"^/dataset/{UUID}/resource/{UUID}/download/[a-zA-Z0-9_.-]+\.csv$")
MAX_META_BYTES = 600_000
MAX_CSV_BYTES = 80_000
MAX_CSV_PER_RUN = 3
PAGE_SIZE = 15
MAX_OFFSETS = 6
MAX_HISTORY = 180
WEEKDAYS = {"lunedi","martedi","mercoledi","giovedi","venerdi","sabato","domenica"}
VERSION = 1


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def key(value):
    normalized = unicodedata.normalize("NFKD", str(value or ""))
    return re.sub(r"[^a-z0-9]+","_", "".join(
        ch for ch in normalized if not unicodedata.combining(ch)
    ).casefold()).strip("_")


def allowed(url: str, *, metadata=False) -> bool:
    try:
        p = urlsplit(url)
        if (p.scheme != "https" or p.hostname != HOST or
                p.port not in (None,443) or p.username or p.password or p.fragment):
            return False
        if metadata:
            return p.path == "/api/3/action/package_search" and bool(re.fullmatch(
                r"(?:q=fiere\+mercati|q=fiere%20mercati)&rows=15&start=(?:0|15|30|45|60|75)",
                p.query))
        return not p.query and bool(CSV_PATH.fullmatch(p.path))
    except (ValueError, TypeError):
        return False


def public_dns():
    for item in socket.getaddrinfo(HOST, 443, type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(item[4][0]).is_global:
            raise ValueError("Non-public CKAN source IP rejected")


def limited_fetch(url, *, metadata=False):
    if not allowed(url, metadata=metadata):
        raise ValueError("Source URL not in exact CKAN host/path allowlist")
    public_dns()
    max_bytes = MAX_META_BYTES if metadata else MAX_CSV_BYTES
    req = Request(url, headers={
        "User-Agent":"MercatiItaliaMunicipalDataFreshnessAudit/1.0",
        "Accept":"application/json" if metadata else "text/csv,text/plain",
        "Accept-Encoding":"identity",
    })
    with build_opener(NoRedirect).open(req, timeout=12) as resp:
        blob = resp.read(max_bytes+1)
    if len(blob) > max_bytes:
        raise ValueError("Municipal source exceeds limited read budget")
    return blob


def make_catalog_url(reference: date):
    start = (reference.toordinal() % MAX_OFFSETS) * PAGE_SIZE
    return CATALOG + "?" + urlencode({
        "q":"fiere mercati","rows":PAGE_SIZE,"start":start
    })


def select_catalog(raw: bytes):
    if not isinstance(raw, (bytes, bytearray)) or len(raw) > MAX_META_BYTES:
        raise ValueError("CKAN metadata too large")
    data=json.loads(raw)
    if data.get("success") is not True:
        raise ValueError("CKAN metadata discovery failed")
    block=data.get("result") or {}
    datasets=block.get("results")
    if not isinstance(datasets,list) or len(datasets)>PAGE_SIZE:
        raise ValueError("Unbounded CKAN dataset discovery")
    selected=[]
    for source in datasets:
        if not isinstance(source,dict) or source.get("private") is True:
            continue
        sid=source.get("id")
        if (not isinstance(sid,str) or not re.fullmatch(UUID,sid)
                or source.get("license_id") != "CC-BY-4.0"):
            continue
        title=str(source.get("title") or "")
        if not ("mercati" in key(title) or "mercato" in key(title)):
            continue
        resources=[r for r in source.get("resources",[]) if isinstance(r,dict)
                   and str(r.get("format","")).upper()=="CSV"
                   and allowed(r.get("url"))]
        if not resources:
            continue
        resource=resources[0]
        selected.append({
            "id":sid,"title":title[:150],
            "publisher":str(source.get("publisher_name") or
                            (source.get("organization") or {}).get("title") or "")[:120],
            "source_modified_claim":str(source.get("modified") or "")[:25],
            "resource_id":str(resource.get("id") or "")[:40],
            "resource_url":resource["url"],
            "resource_last_modified":str(resource.get("last_modified") or "")[:40],
            "claimed_license":"CC-BY-4.0",
        })
    return selected, int(block.get("count",0))


def date_dmy(value):
    if not isinstance(value,str) or not re.fullmatch(r"\d{2}/\d{2}/\d{4}",value.strip()):
        return None
    try:
        return date(int(value[6:10]),int(value[3:5]),int(value[:2]))
    except ValueError:
        return None


def profile_csv(blob: bytes, today: date):
    if not isinstance(blob,(bytes,bytearray)) or len(blob)>MAX_CSV_BYTES:
        raise ValueError("Unbounded source CSV")
    txt=blob.decode("utf-8-sig",errors="strict")
    if "\x00" in txt:
        raise ValueError("Invalid NUL in source CSV")
    first=txt.splitlines()[0] if txt.splitlines() else ""
    delimiter=";" if first.count(";")>first.count(",") else ","
    reader=csv.DictReader(io.StringIO(txt),delimiter=delimiter)
    original_headers=reader.fieldnames or []
    fields=[key(x) for x in original_headers]
    if (not fields or len(fields)>60 or len(set(fields))!=len(fields)
            or not any(x in fields for x in ("nome_mercato","nome"))):
        raise ValueError("Unexpected market CSV schema")
    rows=list(reader)
    if len(rows)>10_000 or any(row.get(None) is not None for row in rows):
        raise ValueError("Malformed or unbounded CSV records")
    normalized=[{key(k):str(v or "").strip() for k,v in r.items()} for r in rows]
    has_concession={"data_validita_concessione","data_scadenza_concessione"} <= set(fields)
    has_stall={"inizio_periodo","fine_periodo","tipo_posteggio"} <= set(fields)
    weekday_field=next((k for k in ("giorno","giorni_svolgimento","giorno_settimana")
                        if k in fields),None)
    name_field="nome_mercato" if "nome_mercato" in fields else "nome"
    venue_field=next((k for k in ("indirizzo","ubicazione","via","sede")
                       if k in fields),None)
    hours_field=next((k for k in ("orario","orario_svolgimento","orari")
                       if k in fields),None)
    expired_concessions=sum(
        (end is not None and end < today)
        for row in normalized
        for end in [date_dmy(row.get("data_scadenza_concessione"))]
    ) if has_concession else 0
    expired_periods=sum(
        (end is not None and end < today)
        for row in normalized
        for end in [date_dmy(row.get("fine_periodo"))]
    ) if has_stall else 0
    days=sum(key(row.get(weekday_field,"")) in WEEKDAYS for row in normalized) if weekday_field else 0
    addresses=sum(bool(row.get(venue_field)) for row in normalized) if venue_field else 0
    hours=sum(bool(row.get(hours_field)) for row in normalized) if hours_field else 0
    distinct=len(set(row.get(name_field,"").casefold().strip() for row in normalized
                     if row.get(name_field,"").strip()))
    # Never mistake 29 concessions for 29 distinct markets.
    if has_concession:
        kind="concessions_not_market_visits"
    elif has_stall:
        kind="historic_stall_capacity_not_market_visits"
    elif days>0 and addresses>0 and distinct>0:
        kind="venue_schedule_review_candidate"
    else:
        kind="no_sufficient_venue_schedule_evidence"
    return {
        "csv_sha256":hashlib.sha256(blob).hexdigest(),
        "source_rows_read":len(normalized),
        "distinct_market_names_not_new_markets":distinct,
        "explicit_valid_weekdays":days,
        "rows_with_addresses":addresses,
        "rows_with_hours":hours,
        "expired_concession_rows":expired_concessions,
        "historical_stall_rows":expired_periods,
        "source_kind":kind,
        "fields":fields[:40],
        "market_import_permission":False,
        "markets_confirmed":0,
    }


def audit(*, reference: date, previous=None, fetch=limited_fetch, offline=False):
    previous=previous or {"schema":VERSION,"history":{}}
    history=dict(previous.get("history") or {})
    if previous.get("schema")!=VERSION or len(history)>MAX_HISTORY:
        raise ValueError("Invalid previous dataset audit history")
    if offline:
        return {"schema":VERSION,"review_only":True,"offline":True,"imports":0,
                "verified_events":0,"reference_date":reference.isoformat(),
                "catalog_total":None,"sample_limit":MAX_CSV_PER_RUN,
                "history":history,"sources":[],"errors":[]}
    url=make_catalog_url(reference)
    try:
        selected,total=select_catalog(fetch(url,metadata=True))
    except Exception as e:
        return {"schema":VERSION,"review_only":True,"offline":False,"imports":0,
                "verified_events":0,"reference_date":reference.isoformat(),
                "catalog_total":None,"sample_limit":MAX_CSV_PER_RUN,
                "history":history,"sources":[],"errors":[type(e).__name__+": "+str(e)[:140]]}
    # Prefer unseen resources, then changed sources, then least-recent checks.
    selected.sort(key=lambda item:(
        0 if item["id"] not in history else (
            1 if history[item["id"]].get("resource_last_modified") != item["resource_last_modified"] else 2),
        history.get(item["id"],{}).get("checked_on",""),
        item["id"],
    ))
    reports=[]
    for source in selected[:MAX_CSV_PER_RUN]:
        item={k:v for k,v in source.items() if k!="resource_url"}
        item.update({"status":"review_required","market_import_permission":False,"markets_confirmed":0})
        try:
            metrics=profile_csv(fetch(source["resource_url"],metadata=False),reference)
            item.update(metrics)
            item["status"]="sampled_complete_csv"
        except Exception as e:
            item["error"]=type(e).__name__+": "+str(e)[:140]
        reports.append(item)
        history[source["id"]]={
            "checked_on":reference.isoformat(),
            "resource_last_modified":source["resource_last_modified"],
            "status":item["status"],
            "kind":item.get("source_kind","needs_review"),
        }
    if len(history)>MAX_HISTORY:
        history=dict(sorted(history.items(),key=lambda x:x[1].get("checked_on",""))[-MAX_HISTORY:])
    return {
        "schema":VERSION,"review_only":True,"offline":False,"imports":0,
        "verified_events":0,"reference_date":reference.isoformat(),
        "catalog_total":total,"sample_limit":MAX_CSV_PER_RUN,
        "history":history,"sources":reports,"errors":[],
    }


def markdown(report):
    out=[
        "# Audit approfondito dataset comunali mercati (solo lettura)",
        "",
        "La data 'aggiornato' del portale **non prova** che righe, concessioni o calendari siano attuali.",
        "Sono ispezionati fino a 3 CSV al giorno; nessun record o dato personale viene salvato.",
        "Nessuna fonte viene abilitata all'importazione.",
        "",
        f"- Dataset trovati dalla ricerca CKAN: **{report['catalog_total'] if report['catalog_total'] is not None else 'non disponibile'}**.",
        f"- Dataset con campione storico: **{len(report['history'])}**.",
        f"- Campioni in questo run: **{len(report['sources'])}**.",
        "",
    ]
    for s in report["sources"]:
        out += ["## "+s["title"].replace("#","").replace("\n"," "),
            "- Editore dichiarato: "+s["publisher"],
            "- Stato: "+s["status"],
            "- Data modifica dichiarata: "+s["source_modified_claim"],
            "- Categoria dei record: "+s.get("source_kind","da verificare"),
            "- Righe amministrative lette: "+str(s.get("source_rows_read","n.d.")),
            "- Nomi distinti (NON mercato nuovo): "+str(s.get("distinct_market_names_not_new_markets","n.d.")),
            "- Concessioni scadute: "+str(s.get("expired_concession_rows","n.d.")),
            "- Righe di posteggi storici: "+str(s.get("historical_stall_rows","n.d.")),
            "- Giorni settimanali espliciti: "+str(s.get("explicit_valid_weekdays","n.d.")),
            "- Campi: "+", ".join(s.get("fields",[])[:24]),
            ""]
    for error in report["errors"]:
        out.append("- Problema di raccolta: "+error)
    out += ["","Le sedi saranno aggiunte solo dopo confronto con catalogo, identità univoche,",
            "verifica giorni/sede e fonte ufficiale attuale. Nessun calendario ricavato da concessioni.",""]
    return "\n".join(out)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--previous",type=Path)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--today",type=date.fromisoformat,default=date.today())
    p.add_argument("--offline",action="store_true")
    a=p.parse_args()
    old=json.loads(a.previous.read_text("utf-8")) if a.previous and a.previous.is_file() else None
    result=audit(reference=a.today,previous=old,offline=a.offline)
    for path in (a.out,a.report):
        path.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n","utf-8")
    a.report.write_text(markdown(result),"utf-8")
    print("MUNICIPAL_ROW_FRESHNESS_AUDIT",json.dumps({
        "datasets_reported":result["catalog_total"],
        "csv_sampled":len(result["sources"]),"source_errors":len(result["errors"]),
        "markets_imported":result["imports"],
    }))


if __name__=="__main__":
    main()
