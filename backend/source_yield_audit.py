#!/usr/bin/env python3
"""Read-only source yield audit. Never equate a dataset or new ID to a market."""
from __future__ import annotations
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from catalog_quality_report import key, VAGUE_ADDRESSES

BOLOGNA_ID = "0bb2a3cb-a3d0-44ef-9053-061006c8cd50"
ROMA_ID = "2d7352f7-7d9f-4be7-927b-de1b760993c3"
PIEMONTE_ID = "26c619d9-ecf8-4882-910e-925a4fb459ec"
BOLOGNA_URL = "https://opendata.comune.bologna.it/explore/dataset/mercati-e-fiere/"
BOLOGNA_DATE = "2025-04-02"
EXISTING = {
    "2e41941b-80fb-4ded-8330-427383f725f8": "Lombardia MERCap",
    "62be39fe-adbe-464a-84b1-85bc060b75d2": "Corciano",
    "0b6c9c3c-a6c4-43b6-91f5-9445ee3cb09b": "Milano",
}
MAX_SOURCE_ROWS = 65
MAX_CATALOG = 100_000
MAX_REGISTRY = 400
MAX_SAMPLES = 8

def specific_place(value):
    normalized = key(value)
    return normalized if len(normalized) >= 7 and normalized not in VAGUE_ADDRESSES else ""

def documented_days(record):
    from lombardia_overlap import weekday_evidence
    days = weekday_evidence(record)
    return frozenset(days) if days is not None and len(days) else frozenset()

def compare_bologna(catalog, observations, today):
    """Count concrete source rows, strong overlaps and unresolved new venues."""
    if not isinstance(observations,list) or not 1<=len(observations)<=MAX_SOURCE_ROWS:
        raise ValueError("Source observation outside vetted bounds")
    catalog_ids=set()
    names=defaultdict(list)
    places=defaultdict(list)
    for row in catalog:
        slug=row.get("slug")
        if not isinstance(slug,str) or not slug or slug in catalog_ids:
            raise ValueError("Catalog ID collision")
        catalog_ids.add(slug)
        place=specific_place(row.get("indirizzo"))
        prefix=(key(row.get("regione")),key(row.get("citta")))
        if place: places[prefix+(place,)].append(row)
        if row.get("nome"): names[prefix+(key(row["nome"]),)].append(row)
    counts=Counter()
    samples={"strong":[],"ambiguous":[],"possible_distinct":[]}
    fingerprints=[]
    for source in observations:
        if (not isinstance(source,dict)
                or source.get("regione")!="Emilia-Romagna"
                or source.get("citta")!="Bologna"
                or source.get("url_fonte")!=BOLOGNA_URL
                or source.get("verificato_il") or source.get("date_quality")=="confermata"
                or str(source.get("aggiornato_il"))[:10]!=BOLOGNA_DATE):
            raise ValueError("Unapproved or unreviewed Bologna source row")
        slug=source.get("slug")
        if not isinstance(slug,str) or not slug.startswith("bo-open-") or slug in fingerprints:
            raise ValueError("Invalid Bologna identity")
        fingerprints.append(slug)
        counts["observed_source_rows"]+=1
        if slug in catalog_ids:
            counts["same_id_already_published"]+=1
            continue
        counts["new_ids_not_new_market_proof"]+=1
        prefix=(key(source["regione"]),key(source["citta"]))
        place=specific_place(source.get("indirizzo"))
        site=places.get(prefix+(place,),[]) if place else []
        same_name=names.get(prefix+(key(source.get("nome")),),[])
        days=documented_days(source)
        overlaps=[r for r in site if key(r.get("nome"))==key(source.get("nome"))
                  and days and documented_days(r) and days.intersection(documented_days(r))]
        if len(overlaps)==1 and len(site)==1:
            bucket="strong"
            counts["strong_exact_place_day_overlaps"]+=1
            if not overlaps[0].get("orario_testo") and source.get("orario_testo"):
                counts["missing_hours_on_strong_match"]+=1
        elif site or same_name:
            bucket="ambiguous"
            counts["possible_duplicate_places_or_names"]+=1
        else:
            bucket="possible_distinct"
            counts["possible_new_venues_unconfirmed"]+=1
        samples[bucket].append(slug)
        if not source.get("date"):
            counts["rows_without_explicit_visit_dates"]+=1
    if sum(counts[k] for k in (
            "same_id_already_published","strong_exact_place_day_overlaps",
            "possible_duplicate_places_or_names","possible_new_venues_unconfirmed")) != len(observations):
        raise ValueError("Unaccounted official records")
    return {
        "schema":1,"actual_dataset_date":BOLOGNA_DATE,
        "source_age_days":(today-date.fromisoformat(BOLOGNA_DATE)).days,
        "source_ids_sha256":hashlib.sha256("\n".join(sorted(fingerprints)).encode()).hexdigest(),
        "counts":dict(sorted(counts.items())),
        "samples_for_review":{k:sorted(v)[:MAX_SAMPLES] for k,v in samples.items()},
        "records_imported":0,"events_confirmed":0,"catalog_data_changed":False,
    }

def audit(catalog,registry,municipalities,probes,today,observations=None,error=""):
    if (not isinstance(catalog,list) or not 1<=len(catalog)<=MAX_CATALOG
            or registry.get("schema")!=1 or registry.get("record_imports")!=0
            or not isinstance(registry.get("sources"),list)
            or not 1<=len(registry["sources"])<=MAX_REGISTRY
            or probes.get("schema")!=1
            or municipalities.get("review_only") is not True
            or municipalities.get("catalog_market_ids_preserved")!=len(catalog)):
        raise ValueError("Untrusted source/city coverage inputs")
    ids=[row.get("slug") for row in catalog]
    if len(set(ids))!=len(ids) or any(not isinstance(s,str) or not s for s in ids):
        raise ValueError("Missing or duplicate original market IDs")
    if len(set(s.get("id") for s in registry["sources"]))!=len(registry["sources"]):
        raise ValueError("Repeated source ID in registry")
    field_probes=probes.get("probe_history",{})
    if not isinstance(field_probes,dict): raise ValueError("Invalid source probes")
    bo=compare_bologna(catalog,observations,today) if observations is not None else None
    ranked=[]
    for src in registry["sources"]:
        if not isinstance(src,dict) or not src.get("id") or not src.get("title"):
            raise ValueError("Malformed source registry")
        sid=src["id"]
        group=src.get("triage_class","unknown")
        schema=field_probes.get(sid,{}).get("viability","not_sampled")
        if group=="aggregated_statistics" or schema=="historical_aggregate_not_venues":
            priority,stage,action=-100,"statistics_not_events","Ignore aggregated historical statistics for market visits."
        elif group=="concession_registry" or schema=="concession_registry_without_visit_schedule":
            priority,stage,action=-90,"vendor_concessions_not_events","Exclude vendor/stall concession records from market catalog."
        elif sid in EXISTING:
            priority,stage,action=-60,"already_integrated","Improve field-level joins; do not import these twice."
        elif sid==BOLOGNA_ID:
            priority,stage=80,"observed_candidate_venues" if bo else "vetted_adapter_not_sampled"
            action="Check 2026 municipality schedule and exact venue identities before allowing import."
        elif sid==ROMA_ID:
            priority,stage,action=64,"historical_hours_lead","Find a current Roma municipal record to corroborate 2022 addresses and opening hours."
        elif sid==PIEMONTE_ID:
            priority,stage,action=60,"unreachable_candidate_source","Restore official dataset endpoint or find replacement, then inspect actual municipality rows."
        elif group=="market_location_candidate":
            priority,stage,action=35,"schema_and_rights_review","Check live row schema, source date, attribution and calendar before integration."
        elif group=="mixed_events_candidate" and (
                "posteggi" in str(src["title"]).casefold() or
                "stalls_not_necessarily_visitable_markets" in src.get("triage_reasons",[])):
            priority,stage,action=-45,"stalls_not_market_visits","Posteggi and concessions are not proof of an operating market or visit date."
        elif group=="mixed_events_candidate":
            priority,stage,action=12,"events_and_stalls_mixed","Separate periodic markets from fairs and vendors; do not auto-import."
        else:
            priority,stage,action=5,"metadata_only","Check the actual dataset before considering as new markets."
        item={
            "source_id":sid,"title":str(src["title"])[:240],
            "publisher":str(src.get("organization") or "")[:160],
            "source_type":group,"schema_type":schema,
            "stage":stage,"priority":priority,
            "dataset_date_declared":str(src.get("publisher_data_updated_at") or src.get("data_modified") or "")[:35],
            "license_needs_review":True,
            "actual_rows_examined":bo["counts"]["observed_source_rows"] if sid==BOLOGNA_ID and bo else None,
            "possible_distinct_venues":bo["counts"].get("possible_new_venues_unconfirmed",0) if sid==BOLOGNA_ID and bo else None,
            "candidate_status":("sampled_bounded" if bo else "not_available" if error else "not_requested") if sid==BOLOGNA_ID else "not_sampled",
            "next_action":action,"market_entries_added":0,"individual_events_confirmed":0,
        }
        if sid==BOLOGNA_ID and error: item["observation_error"]=str(error)[:150]
        ranked.append(item)
    ranked.sort(key=lambda x:(-x["priority"],x["title"],x["source_id"]))
    review_queue=[r for r in ranked if r["priority"]>0][:12]
    return {
        "schema":1,"date":today.isoformat(),"review_only":True,
        "catalog_market_ids_retained":len(catalog),
        "sources_checked":len(registry["sources"]),
        "actual_source_samples_checked":1 if bo else 0,
        "bologna_observation":bo,
        "priority_queue":review_queue,
        "all_sources":ranked,
        "sources_imported":0,"markets_added":0,"markets_deleted":0,
        "market_rows_edited":0,"market_events_confirmed":0,
        "official_license_verified_automatically":0,
        "unrepresented_municipalities_are_not_market_claims":
            municipalities.get("municipalities_without_catalog_listings"),
    }

def markdown(report):
    b=report.get("bologna_observation")
    c=b["counts"] if b else {}
    lines=[
        "# Fonti ufficiali — resa osservata e prossime verifiche","",
        "**Audit in sola lettura. Nessun ID, mercato o calendario modificato.**","",
        f"- Fonti catalogate: **{report['sources_checked']}**",
        f"- Schede conservate: **{report['catalog_market_ids_retained']}**",
        f"- Fonti con righe ricontrollate ora: **{report['actual_source_samples_checked']}**",
        f"- Bologna: **{c.get('observed_source_rows','n.d.')}** schede ufficiali osservate.",
        f"- Nuovi ID Bologna (non mercati certificati nuovi): **{c.get('new_ids_not_new_market_proof','n.d.')}**.",
        f"- Possibili sedi distinte, ancora da verificare: **{c.get('possible_new_venues_unconfirmed','n.d.')}**.",
        f"- Possibili sovrapposizioni tra fonti: **{c.get('possible_duplicate_places_or_names','n.d.')}**.",
        f"- Source data Bologna: **{b['actual_dataset_date'] if b else 'non disponibili'}**; non e' una conferma di apertura.","",
        "## Priorita basate sulla resa, non sul punteggio dei metadati","",
        "| Priorita | Fonte | Stato | Righe viste | Candidati distinti | Azione |",
        "|---:|---|---|---:|---:|---|",
    ]
    for i,item in enumerate(report["priority_queue"][:12],1):
        a=item["actual_rows_examined"];n=item["possible_distinct_venues"]
        lines.append(f"| {i} | {item['title'].replace('|','/')} | {item['stage']} | "
                     f"{a if a is not None else 'n.d.'} | "
                     f"{n if n is not None else 'n.d.'} | "
                     f"{item['next_action'].replace('|','/')} |")
    lines.extend(["","Fonti gia integrate, concessioni e statistiche non contano come nuovi mercati.",
                  "Le fonti con righe non accessibili restano non misurate, non diventano zero.",""])
    return "\n".join(lines)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--registry",type=Path,required=True)
    p.add_argument("--municipalities",type=Path,required=True)
    p.add_argument("--probes",type=Path,required=True)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--today",type=date.fromisoformat,default=date.today())
    p.add_argument("--live-bologna",action="store_true")
    args=p.parse_args()
    from merge_catalog import load_existing
    base=load_existing(args.manifest)
    reg=json.loads(args.registry.read_text("utf-8"))
    mun=json.loads(args.municipalities.read_text("utf-8"))
    probes=json.loads(args.probes.read_text("utf-8"))
    observations=None
    error=""
    if args.live_bologna:
        try:
            import source_bologna
            observations=source_bologna.convert(source_bologna.download(),today=args.today)
        except (OSError,ValueError,TimeoutError,TypeError,KeyError) as exc:
            error=type(exc).__name__+": "+str(exc)[:130]
    report=audit(base,reg,mun,probes,args.today,observations,error)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    args.report.write_text(markdown(report),encoding="utf-8")
    print("SOURCE_YIELD",json.dumps({"sources":report["sources_checked"],
         "market_records_added":report["markets_added"],
         "sampled":report["actual_source_samples_checked"],
         "candidate_venues":(report["bologna_observation"] or {}).get("counts",{}).get("possible_new_venues_unconfirmed")},
        ensure_ascii=False))

if __name__=="__main__":
    main()
