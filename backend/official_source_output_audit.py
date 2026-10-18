#!/usr/bin/env python3
"""Check every reviewed municipality/regional adapter against live publisher rows.

Requires no secrets and never writes catalog rows. Reports only counts,
provenance dates and stable-ID hashes, never publisher row texts. On an outage,
the previous report is preserved as last-known evidence (not marked current).
"""
from __future__ import annotations
import argparse
import json
from datetime import date
from pathlib import Path

from autopilot import source_feed
from official_source_output_gate import inspect,verify_gate

SCHEMA=1
ALL_SOURCES=("lombardia","milano","bologna","firenze","corciano")


def validate_previous(previous):
    if previous is None:
        return {}
    if (not isinstance(previous,dict) or previous.get("schema")!=SCHEMA
            or previous.get("research_only") is not True
            or previous.get("catalog_updates")!=0
            or previous.get("market_openings_confirmed")!=0
            or not isinstance(previous.get("sources"),list)
            or {x.get("source_id") for x in previous["sources"]}!=set(ALL_SOURCES)):
        raise ValueError("Untrusted prior official publisher audit")
    return {x["source_id"]:x for x in previous["sources"]}


def run(*,fetch=source_feed,today=None,previous=None,offline=False):
    today=today or date.today()
    if not isinstance(today,date):
        raise ValueError("Invalid audit date")
    prior=validate_previous(previous)
    rows=[]
    for sid in ALL_SOURCES:
        historical=prior.get(sid,{})
        last_good=historical.get("current_publisher_gate") or historical.get("last_good_publisher_gate")
        if last_good is not None:
            if last_good.get("source_id")!=sid or not verify_gate(last_good):
                raise ValueError("Prior source output evidence changed or belongs to another publisher")
        result={
            "source_id":sid,
            "source_checked_as_of":today.isoformat(),
            "status":"offline_skipped" if offline else "not_checked",
            "rows_loaded_into_catalog":0,
            "new_market_openings_confirmed":0,
            "new_market_coordinates_created":0,
        }
        if offline:
            if last_good:
                result["last_good_publisher_gate"]=last_good
                result["last_good_as_of"]=historical.get("last_good_as_of") or historical.get("source_checked_as_of")
            rows.append(result)
            continue
        try:
            official=fetch(sid,today)
            gate=inspect(sid,official,today=today,previous=last_good)
            verify_gate(gate)
            result["current_publisher_gate"]=gate
            result["status"]="source_output_passed"
            result["last_good_as_of"]=today.isoformat()
        except (OSError,ValueError,TypeError,UnicodeError,TimeoutError) as exc:
            result["status"]="publisher_unavailable_or_mapping_contract_changed"
            result["failure_class"]=type(exc).__name__
            if last_good:
                result["last_good_publisher_gate"]=last_good
                result["last_good_as_of"]=historical.get("last_good_as_of") or historical.get("source_checked_as_of")
        rows.append(result)
    return {
        "schema":SCHEMA,"as_of":today.isoformat(),
        "research_only":True,"sources":rows,
        "sources_scoped_to_existing_official_adapters":len(ALL_SOURCES),
        "source_batches_passed":sum(x["status"]=="source_output_passed" for x in rows),
        "source_batches_unavailable_or_changed":sum(
            x["status"]=="publisher_unavailable_or_mapping_contract_changed" for x in rows),
        "full_catalog_source_labels_covered_separately":True,
        "source_dataset_date_is_not_market_verification":True,
        "market_rows_copied_to_audit":0,
        "catalog_updates":0,
        "market_openings_confirmed":0,
        "new_market_IDs_published":0,
        "new_precise_market_positions_inferred":0,
    }


def validate(report):
    if (not isinstance(report,dict) or report.get("schema")!=SCHEMA
            or report.get("research_only") is not True
            or report.get("source_dataset_date_is_not_market_verification") is not True
            or len(report.get("sources",[]))!=len(ALL_SOURCES)
            or {x.get("source_id") for x in report["sources"]}!=set(ALL_SOURCES)
            or any(report.get(k)!=0 for k in (
                "market_rows_copied_to_audit","catalog_updates",
                "market_openings_confirmed","new_market_IDs_published",
                "new_precise_market_positions_inferred"))):
        raise ValueError("Official source live QA report is not read-only")
    for row in report["sources"]:
        if row.get("rows_loaded_into_catalog")!=0 or row.get("new_market_openings_confirmed")!=0:
            raise ValueError("Official source audit illegally claimed event import/confirmation")
        if row.get("current_publisher_gate") is not None:
            if row.get("status")!="source_output_passed":
                raise ValueError("Unavailable source falsely marked current")
            verify_gate(row["current_publisher_gate"])
        if row.get("last_good_publisher_gate") is not None:
            if row.get("status")=="source_output_passed":
                raise ValueError("Current source proof duplicated into historical proof")
            verify_gate(row["last_good_publisher_gate"])
    return True


def markdown(report):
    lines=[
        "# Qualità live dei cinque adapter ufficiali — solo DEV",
        "",
        "La scansione dei cataloghi editoriali di Happings/EventiESagre/Cose di Casa",
        "è un lavoro distinto: non è autorizzata la copia automatica dei testi.",
        "Un dato publisher vecchio o mancante NON conferma chiusura o aperture.",
        "",
        "| Fonte | Controllo | Righe originali normalizzate | Indirizzi | Orari | Coordinate | Data dataset |",
        "|---|---|---:|---:|---:|---:|---|",
    ]
    for x in report["sources"]:
        g=x.get("current_publisher_gate")
        if g is None:
            lines.append("| "+x["source_id"]+" | "+x["status"]+" | — | — | — | — | — |")
        else:
            f=g["field_coverage"]
            lines.append("| "+x["source_id"]+" | superato | "+str(g["rows"])+
                         " | "+str(f["nonempty_address"])+" | "+str(f["nonempty_hours"])+
                         " | "+str(f["source_coordinates_present"])+" | "+
                         g["official_dataset_timestamp"]+" |")
    lines.extend(["", "I numeri della data sono quelli del **dataset**, non",
                  "una conferma dell'apertura del singolo mercato.",
                  "Nessuna modifica al catalogo e nessun mercato aggiunto.",""])
    return "\n".join(lines)


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--report",required=True,type=Path)
    p.add_argument("--previous",type=Path,default=Path(
        "reports/automation/official-source-output-qa.json"))
    p.add_argument("--offline",action="store_true")
    p.add_argument("--today",type=date.fromisoformat,default=date.today())
    a=p.parse_args()
    old=json.loads(a.previous.read_text("utf-8")) if a.previous.is_file() else None
    output=run(today=a.today,previous=old,offline=a.offline)
    validate(output)
    for path in (a.out,a.report):path.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(output,ensure_ascii=False,sort_keys=True,indent=2)+"\n","utf-8")
    a.report.write_text(markdown(output)+"\n","utf-8")
    print(json.dumps({"passed":output["source_batches_passed"],
                      "unavailable_or_changed":output["source_batches_unavailable_or_changed"],
                      "source_count":len(output["sources"]),
                      "catalog_updates":0,"market_confirmations":0}))


if __name__=="__main__":
    main()
