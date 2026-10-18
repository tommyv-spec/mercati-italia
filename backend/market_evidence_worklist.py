#!/usr/bin/env python3
"""Evidence-oriented, no-deletion worklist over EVERY published market.

Each approved source layout is studied once and reused on each update.
MERCAP cross-matches use the already downloaded official source cohort,
never network queries for individual private/editorial listings. Sources
without reuse permission generate investigation tasks, not copied text.

Every run checks every market. A 31-day ID-sharded task list stays small
in Git while guaranteeing a recurring slot for all unresolved records.
No catalog edits, imports, confirmations, geocoding or paid APIs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from catalog_quality_report import VAGUE_ADDRESSES, key as address_key
from merge_catalog import load_existing
from official_enrichment import distance_km, hours_allowed
from publisher_quality_matrix import _source
from source_lombardia import SOURCE_PAGE
from source_reconciliation_audit import _place_key, _town_day
from lombardia_overlap import norm

SCHEMA=1
MAX_MARKETS=100_000
MAX_OFFICIAL_ROWS=3000
SHARDS=31
MAX_DAILY_TASKS=1200
TRACKED_FIELDS=("indirizzo","orario_testo","ricorrenza_testo","date","coordinates")
EVIDENCE_TYPES=frozenset((
    "same_source_id","unique_city_province_street_weekday",
    "city_weekday_only_unconfirmed_venue","no_usable_source_match",
))


def registry_check(cfg):
    expected={
        ("happings-weekly-or-detail","happings.com"),
        ("eventiesagre-event-index","eventiesagre.it"),
        ("cosedicasa-editorial-calendar","cosedicasa.com"),
        ("lombardia-mercap","Regione Lombardia – MERCap (CC0 1.0 dichiarata)"),
        ("milano-municipal","Comune di Milano - Open Data (CC BY 4.0)"),
    }
    if (not isinstance(cfg,dict) or cfg.get("schema")!=1
        or cfg.get("report_only") is not True
        or cfg.get("may_grant_source_reuse_rights") is not False
        or cfg.get("may_apply_field_changes") is not False
        or cfg.get("may_confirm_individual_market_dates") is not False
        or not isinstance(cfg.get("families"),list)
        or len(cfg["families"])!=5
        or {(x.get("id"),x.get("label")) for x in cfg["families"]}!=expected):
        raise ValueError("Unreviewed source-family contract or rights permission")
    for source in cfg["families"]:
        if (source.get("bulk_scrape_allowed") is not False
            or source.get("market_confirmation_allowed") is not False
            or not isinstance(source.get("automation"),str)
            or not set(source.get("fields_to_recheck",[]))<=set(TRACKED_FIELDS)):
            raise ValueError("Source-family profile attempts unauthorized extraction")
    return True


def family(label,cfg):
    return next((x for x in cfg["families"] if x["label"]==label), {
        "id":"unknown-source-requires-structure-and-rights-review",
        "rights":"not_approved",
        "automation":"find_independent_official_publisher_and_review_schema_first",
    })


def safe_url(u):
    try:
        p=urlsplit(str(u or ""))
        return p.scheme=="https" and bool(p.hostname) and not p.username and not p.password and p.port in (None,443)
    except ValueError:
        return False


def fields(m,today):
    street=str(m.get("indirizzo") or "").strip()
    dates=m.get("date") or []
    future=False
    if isinstance(dates,list):
        for item in dates[:370]:
            try:
                if date.fromisoformat(str(item))>=today:
                    future=True
                    break
            except (ValueError,TypeError):
                pass
    lat,lng=m.get("lat"),m.get("lng")
    point=(type(lat) in (int,float) and type(lng) in (int,float)
           and 35<=lat<=48 and 6<=lng<=20)
    return {
        "indirizzo": "missing" if not street else
            "vague" if address_key(street) in VAGUE_ADDRESSES else "present",
        "orario_testo": "present" if str(m.get("orario_testo") or "").strip() else "missing",
        "ricorrenza_testo":"present" if str(m.get("ricorrenza_testo") or "").strip() else "missing",
        "date":"upcoming_reported_or_forecast" if future else "missing_upcoming",
        "coordinates":"missing" if not point else
            "claimed_precise" if m.get("position_quality")=="precisa" else "indicative",
        "individual_verified_by_source":bool(m.get("verificato_il")),
        "date_quality":str(m.get("date_quality") or "sconosciuta"),
    }


def official_index(rows,today):
    if rows is None:
        return {},{},{},"source_not_downloaded"
    if not isinstance(rows,list) or len(rows)>MAX_OFFICIAL_ROWS:
        raise ValueError("Official source cohort is incomplete or unbounded")
    ids={}
    exact=defaultdict(list)
    town=defaultdict(list)
    stamps=set()
    for r in rows:
        if not isinstance(r,dict):
            raise ValueError("Publisher feed has non-record row")
        sid=r.get("slug")
        if (not isinstance(sid,str) or not sid.startswith("lo-mercap-")
            or sid in ids or r.get("regione")!="Lombardia"
            or r.get("url_fonte")!=SOURCE_PAGE
            or r.get("verificato_il") or r.get("date_quality")=="confermata"):
            raise ValueError("Unreviewed official record identity or confirmation")
        try:
            stamp=date.fromisoformat(str(r["aggiornato_il"])[:10])
        except (ValueError,KeyError,TypeError):
            raise ValueError("Missing source snapshot date") from None
        stamps.add(stamp)
        ids[sid]=r
        if (today-stamp).days < -1:
            raise ValueError("Official source date is in the future")
        if (today-stamp).days > 540:
            continue
        pk,td=_place_key(r),_town_day(r)
        if pk and td:
            exact[pk].append(r)
            town[td].append(r)
    if len(stamps)>1:
        raise ValueError("Source mixes distinct publisher snapshot timestamps")
    good=(stamps and -1<=(today-next(iter(stamps))).days<=540)
    return ids,exact,town,"fresh_dataset_not_market_confirmation" if good else "stale_or_empty_source"


def official_evidence(m,state,ids,exact,town,status):
    proof={"match":"no_usable_source_match","leads":[],"review_only":True}
    if m.get("regione")!="Lombardia" or status!="fresh_dataset_not_market_confirmation":
        return proof
    source=None
    day=_town_day(m)
    own=ids.get(m.get("slug"))
    if own and day and _town_day(own)==day and norm(own.get("citta"))==norm(m.get("citta")):
        source=own
        proof["match"]="same_source_id"
    else:
        location=_place_key(m)
        if location:
            options=exact.get(location,[])
            if len(options)==1:
                gap=distance_km(m,options[0])
                if gap is None or gap<=0.6:
                    source=options[0]
                    proof["match"]="unique_city_province_street_weekday"
                else:
                    proof["collision"]="coordinates_disagree"
            elif len(options)>1:
                proof["collision"]="multiple_official_venues_on_same_street_day"
        elif day and state["indirizzo"]!="present":
            options=town.get(day,[])
            if len(options)==1 and options[0].get("indirizzo"):
                sample=options[0]
                proof["match"]="city_weekday_only_unconfirmed_venue"
                proof["leads"].append({
                    "field":"indirizzo","candidate_value":str(sample["indirizzo"])[:180],
                    "source_id":sample["slug"],"source_url":SOURCE_PAGE,
                    "dataset_updated":sample["aggiornato_il"],
                    "confidence":"city_weekday_only_unconfirmed_venue",
                    "exact_venue_identity_confirmed":False,
                    "can_apply":False,"opening_verified":False,
                })
            elif len(options)>1:
                proof["collision"]="many_market_places_on_same_city_day"
    if source is not None:
        for field,val,usable in [
            ("orario_testo",source.get("orario_testo"),hours_allowed(source.get("orario_testo"))),
            ("indirizzo",source.get("indirizzo"),bool(source.get("indirizzo"))),
        ]:
            if state[field] not in ("missing","vague") or not usable:
                continue
            proof["leads"].append({
                "field":field,"candidate_value":str(val)[:180],
                "source_id":source["slug"],"source_url":SOURCE_PAGE,
                "dataset_updated":source["aggiornato_il"],
                "confidence":proof["match"],
                "exact_venue_identity_confirmed":True,
                "can_apply":(field=="orario_testo" and
                             proof["match"]=="unique_city_province_street_weekday") or
                             (field=="indirizzo" and proof["match"]=="same_source_id" and state[field]=="missing"),
                "opening_verified":False,
            })
    return proof


def analyze(markets,cfg,*,official=None,today=None,shards=SHARDS):
    today=today or date.today()
    registry_check(cfg)
    if (not isinstance(markets,list) or not 1<=len(markets)<=MAX_MARKETS
        or not isinstance(today,date) or not 1<=shards<=SHARDS):
        raise ValueError("Invalid retained national market inventory")
    ids=set()
    source_counts=Counter()
    gaps=Counter()
    per_source=defaultdict(Counter)
    matches=Counter()
    batch=[]
    needing_attention=0
    by_id,by_exact,by_town,official_status=official_index(official,today)
    for m in markets:
        if not isinstance(m,dict):
            raise ValueError("Malformed market record")
        sid=m.get("slug")
        if not isinstance(sid,str) or not sid or sid in ids:
            raise ValueError("Duplicate or missing original market identity")
        ids.add(sid)
        label=_source(m)
        source_counts[label]+=1
        st=fields(m,today)
        pending=[field for field in TRACKED_FIELDS if st[field] in
                 ("missing","vague","indicative","missing_upcoming")]
        if not st["individual_verified_by_source"]:
            pending.append("individual_edition_confirmation")
        if pending:
            needing_attention+=1
        for field in pending:
            gaps[field]+=1
            per_source[label][field]+=1
        rec=official_evidence(m,st,by_id,by_exact,by_town,official_status)
        matches[rec["match"]]+=1
        if rec.get("collision"):
            matches[rec["collision"]]+=1
        matches["review_only_field_candidates"]+=len(rec["leads"])
        matches["exact_field_evidence_candidates"]+=sum(
            1 for lead in rec["leads"] if lead["can_apply"])
        if not pending and not rec["leads"]:
            continue
        # Stable fair rotation; 31 dates cover every unresolved market ID.
        slot=int.from_bytes(hashlib.sha256(sid.encode()).digest()[:4],"big")%shards
        if slot!=today.toordinal()%shards:
            continue
        source=family(label,cfg)
        batch.append({
            "market_id":sid,"original_source":label[:170],
            "source_family":source["id"],"source_rights":source["rights"],
            "source_url":str(m.get("url_fonte") or "")[:500] if safe_url(m.get("url_fonte")) else "",
            "region":str(m.get("regione") or "")[:80],
            "city":str(m.get("citta") or "")[:120],
            "field_states":st,"search_fields":pending,
            "official_evidence":rec["leads"],"official_match":rec["match"],
            "source_conflict":rec.get("collision"),
            "next_source_action":source["automation"],
            "source_incomplete_record_retained":True,
            "any_field_updated":False,"edition_verified":False,
        })
    if len(batch)>MAX_DAILY_TASKS:
        raise ValueError("Worklist too large to retain all records in this shard")
    batch.sort(key=lambda r:(
        -source_counts[r["original_source"]],
        -len(r["search_fields"]),r["market_id"]))
    breakdown=[]
    for label,n in sorted(source_counts.items(),key=lambda x:(-x[1],x[0])):
        src=family(label,cfg)
        breakdown.append({
            "publisher":label,"records":n,"source_family":src["id"],
            "reuse_status":src["rights"],"next_automation":src["automation"],
            "missing_fields":dict(sorted(per_source[label].items())),
            "source_rows_removed":0,
        })
    return {
        "schema":SCHEMA,"as_of":today.isoformat(),"report_only":True,
        "original_market_ids_sha256":hashlib.sha256(
            "\n".join(sorted(ids)).encode()).hexdigest(),
        "market_records_scanned":len(markets),
        "market_identities_preserved":len(ids),
        "incomplete_market_records_retained":needing_attention,
        "distinct_source_labels":len(source_counts),
        "sources_by_volume":breakdown,
        "missing_by_field":dict(sorted(gaps.items())),
        "official_source_status":official_status,
        "official_source_records":len(by_id),
        "official_join_results":dict(sorted(matches.items())),
        "daily_shard":today.toordinal()%shards,"total_shards":shards,
        "daily_worklist":batch,"daily_worklist_count":len(batch),
        "source_refresh_does_not_verify_edition":True,
        "publisher_copyright_permissions_inferred":False,
        "source_rows_reused_from_unapproved_aggregators":0,
        "market_rows_removed":0,"market_rows_added":0,
        "market_fields_changed":0,"confirmed_openings_added":0,
        "coordinates_created":0,
    }


def validate(result,total):
    if (not isinstance(result,dict) or result.get("schema")!=SCHEMA
        or result.get("report_only") is not True
        or result.get("market_records_scanned")!=total
        or result.get("market_identities_preserved")!=total
        or result.get("source_refresh_does_not_verify_edition") is not True
        or result.get("publisher_copyright_permissions_inferred") is not False
        or not 1<=result.get("total_shards",0)<=SHARDS
        or len(result.get("daily_worklist",[]))!=result.get("daily_worklist_count")
        or len(result["daily_worklist"])>MAX_DAILY_TASKS
        or sum(x["records"] for x in result["sources_by_volume"])!=total
        or any(result.get(k)!=0 for k in (
            "source_rows_reused_from_unapproved_aggregators",
            "market_rows_removed","market_rows_added","market_fields_changed",
            "confirmed_openings_added","coordinates_created"))):
        raise ValueError("Worklist erased markets, invented verification or granted source rights")
    ids=set()
    for item in result["daily_worklist"]:
        sid=item.get("market_id")
        if not isinstance(sid,str) or sid in ids or item.get("source_incomplete_record_retained") is not True:
            raise ValueError("Worklist identity lost or duplicated")
        ids.add(sid)
        if item.get("any_field_updated") is not False or item.get("edition_verified") is not False:
            raise ValueError("Research worklist claimed market updates")
        for lead in item.get("official_evidence",[]):
            if (lead.get("source_url")!=SOURCE_PAGE
                or lead.get("opening_verified") is not False
                or lead.get("field") not in ("indirizzo","orario_testo")
                or lead.get("confidence") not in EVIDENCE_TYPES):
                raise ValueError("Evidence from unapproved publisher or invented opening")
    return True


def markdown(result):
    lines=[
        "# Completamento dei mercati esistenti — report fonte per fonte",
        "",
        "Tutti i mercati, anche incompleti, restano nel catalogo.",
        "Il dato aggiornato del publisher NON conferma l'apertura della singola edizione.",
        "",
        "- ID controllati e conservati: **"+str(result["market_records_scanned"])+"**",
        "- Etichette di fonte: **"+str(result["distinct_source_labels"])+"**",
        "- Casi nel lotto di lavoro del giorno: **"+str(result["daily_worklist_count"])+"**",
        "- Lotti rotanti: **"+str(result["total_shards"])+"**",
        "- Feed Lombardia: "+result["official_source_status"],
        "- Mercati aggiunti/rimossi/aggiornati automaticamente da questo report: **0**",
        "","## Campi ancora incerti o assenti","",
    ]
    for key,value in result["missing_by_field"].items():
        lines.append("- "+key+": **"+str(value)+"**")
    lines.extend(["","## Origini ordinate per numero di schede","",
                  "| Origine | Schede | Orari | Sedi | Trattamento |",
                  "|---|---:|---:|---:|---|"])
    for source in result["sources_by_volume"]:
        counts=source["missing_fields"]
        lines.append("| "+source["publisher"].replace("|","/")+
                     " | "+str(source["records"])+
                     " | "+str(counts.get("orario_testo",0))+
                     " | "+str(counts.get("indirizzo",0))+
                     " | "+source["source_family"]+" |")
    lines.extend(["","## Riscontri ufficiali per singola scheda",""])
    for key,value in result["official_join_results"].items():
        lines.append("- "+key+": "+str(value))
    lines.extend(["","La corrispondenza per solo Comune e giorno identifica",
                  "una possibile pista, NON la prova che la sede sia la stessa.",
                  "Le fonti commerciali senza autorizzazione sono trattate come",
                  "origini da confrontare con Comuni, organizzatori e open data,",
                  "non come archivi da copiare in massa.",""])
    return "\n".join(lines)+"\n"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,default=Path("public/data/v1/manifest.json"))
    p.add_argument("--contracts",type=Path,default=Path(
        "backend/data/market-evidence-source-families.json"))
    p.add_argument("--official-lombardia",type=Path)
    p.add_argument("--today",type=date.fromisoformat,default=date.today())
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    args=p.parse_args()
    markets=load_existing(args.manifest)
    cfg=json.loads(args.contracts.read_text("utf-8"))
    official=(json.loads(args.official_lombardia.read_text("utf-8"))
              if args.official_lombardia and args.official_lombardia.is_file() else None)
    original=[row["slug"] for row in markets]
    result=analyze(markets,cfg,official=official,today=args.today)
    validate(result,len(markets))
    if [row["slug"] for row in markets]!=original:
        raise ValueError("Worklist modified the original market identities")
    for dest in (args.out,args.report):
        dest.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(result,indent=2,sort_keys=True,ensure_ascii=False)+"\n","utf-8")
    args.report.write_text(markdown(result),"utf-8")
    print(json.dumps({
        "records_scanned":result["market_records_scanned"],
        "source_labels":result["distinct_source_labels"],
        "daily_tasks":result["daily_worklist_count"],
        "official_matches":result["official_join_results"],
        "market_updates":0,
    },ensure_ascii=False))


if __name__=="__main__":
    main()
