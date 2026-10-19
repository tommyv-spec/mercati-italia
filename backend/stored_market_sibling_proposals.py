#!/usr/bin/env python3
"""Find market addresses ALREADY contained in another saved card of SAME source.

No network, no copying from third party sites, no paid provider. A Happings
provincial index sometimes generated 2–3 copies of "Mercato settimanale di
Spinea" with the same original URL, municipality, province and weekday.
One saved copy has "Villaggio dei Fiori", the other copies omit it.

This read-only audit proposes exact internal evidence transfers, but does not
copy data into a market: city/day can contain multiple distinct venues,
publisher terms forbid unlicensed automated collection, and a single
remaining saved address is not proof it is the only venue in that town.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from catalog_quality_report import VAGUE_ADDRESSES, key as addr_key
from merge_catalog import load_existing
from recurrence_refresh import explicit_rule
from source_reconciliation_audit import _unambiguous_day
from lombardia_overlap import norm

SOURCE="happings.com"
MAX_ROWS=100_000
MAX_RESULTS=1400
ADDRESS_PREFIX=re.compile(
    r"^(?:via|viale|vicolo|vico|corso|piazza|piazzale|piazzetta|largo|"
    r"lungomare|strada|villaggio|campo|parco|borgo|frazione|contrada)\b",re.I
)
BAD_PHRASES=("mercati in ","mercati settimanali","sagra","fiera",
             "su richiesta","consultare","da definire","presso gli stand")


def publisher_url_family(url):
    """Classify historic source URL layouts without issuing any network request.

    The legacy catalog contains `-a-{province}.html`, `-ad-{province}.html`,
    and individual town pages. Treat unsupported or obsolete URLs as a
    forensic failure category, not proof the related market is closed.
    """
    try:
        p=urlsplit(str(url or ""))
        if (p.scheme!="https" or p.hostname!="www.happings.com"
            or p.username or p.password or p.port not in (None,443)
            or p.query or p.fragment):
            return "unreviewed_origin_or_query"
    except ValueError:
        return "unreviewed_origin_or_query"
    if re.fullmatch(r"/it/mercati-settimanali-a-[a-z0-9-]+\.html",p.path):
        return "province_index_old_a"
    if re.fullmatch(r"/it/mercati-settimanali-ad-[a-z0-9-]+\.html",p.path):
        return "province_index_old_ad"
    if re.fullmatch(r"/it/mercati-settimanali-a-[a-z0-9-]+-e-provincia/",p.path):
        return "province_index_canonical"
    if re.fullmatch(r"/it/mercato-settimanale-a-[a-z0-9-]+\.html",p.path):
        return "town_detail_legacy"
    return "other_historical_layout"


def same_generic_venue(row):
    """Named festivals and differently themed venues must NOT be joined."""
    name=norm(row.get("nome"))
    city=norm(row.get("citta"))
    if not city:return False
    return bool(re.fullmatch(r"mercato settimanale (?:a|di|del|della) "+re.escape(city),name))


def safe_stored_street(value):
    raw=str(value or "").strip()
    key=norm(raw)
    if (not 7<=len(raw)<=190 or not ADDRESS_PREFIX.match(key)
        or addr_key(raw) in VAGUE_ADDRESSES
        or any(blocked in key for blocked in BAD_PHRASES)):
        return False
    return True


def source_group_key(row):
    """Original URL + municipality/province + exact, unambiguous weekly day."""
    if row.get("fonte")!=SOURCE or not same_generic_venue(row):
        return None
    source=str(row.get("url_fonte") or "")
    try:
        p=urlsplit(source)
        if (p.scheme!="https" or p.hostname!="www.happings.com"
            or p.username or p.password or p.port not in (None,443)):
            return None
    except ValueError:return None
    region=norm(row.get("regione"))
    province=norm(row.get("provincia"))
    city=norm(row.get("citta"))
    day=_unambiguous_day(row)
    if not region or len(province)!=2 or not city or day is None:
        return None
    return (source,region,province,city,day)


def analyze(rows,*,today=None):
    today=today or date.today()
    if (not isinstance(rows,list) or not 1<=len(rows)<=MAX_ROWS
        or not isinstance(today,date)):
        raise ValueError("Invalid or incomplete saved market cohort")
    ids=set()
    groups=defaultdict(list)
    format_counters=defaultdict(Counter)
    checked=0
    for row in rows:
        if not isinstance(row,dict) or not isinstance(row.get("slug"),str):
            raise ValueError("Source row identity missing")
        sid=row["slug"]
        if sid in ids:
            raise ValueError("Duplicated original market ID")
        ids.add(sid)
        if row.get("fonte")==SOURCE:
            checked+=1
            shape=publisher_url_family(row.get("url_fonte"))
            format_counters[shape]["records"]+=1
            if not str(row.get("indirizzo") or "").strip():
                format_counters[shape]["address_missing"]+=1
            if not safe_stored_street(row.get("indirizzo")):
                format_counters[shape]["address_not_specific"]+=1
            if not str(row.get("orario_testo") or "").strip():
                format_counters[shape]["hours_missing"]+=1
        key=source_group_key(row)
        if key:groups[key].append(row)
    counts=Counter()
    examples=[]
    receipts=[]
    for key,cards in groups.items():
        candidates=defaultdict(list)
        blanks=[]
        for card in cards:
            addr=card.get("indirizzo")
            if safe_stored_street(addr):
                candidates[addr_key(addr)].append(card)
            elif not str(addr or "").strip() or addr_key(addr) in VAGUE_ADDRESSES:
                blanks.append(card)
        if not blanks:continue
        if len(candidates)!=1:
            counts["multiple_or_missing_unique_venue_proofs"]+=len(blanks)
            if len(candidates)>1:
                counts["more_than_one_known_street_in_same_city_day"]+=1
            continue
        donor=next(iter(candidates.values()))
        donor.sort(key=lambda x:x["slug"])
        source_record=donor[0]
        for recipient in blanks:
            if recipient["slug"]==source_record["slug"]:
                continue
            # Same province, weekly day and original source URL are necessary
            # but INSUFFICIENT for an automatic update when multiple physical
            # markets might exist. Record evidence for independent review.
            obj={
                "target_market_id":recipient["slug"],
                "existing_record_with_street_id":source_record["slug"],
                "source_url":key[0],
                "source_region":str(recipient.get("regione") or "")[:70],
                "source_city":str(recipient.get("citta") or "")[:110],
                "field":"indirizzo",
                "internal_street_already_stored":str(source_record["indirizzo"])[:190],
                "match":"same_saved_publisher_url_city_province_weekday_one_known_street",
                "source_timestamp_scope":"legacy_import_not_publisher_verification",
                "not_independent_venue_confirmation":True,
                "automatic_fill_authorized":False,
                "source_html_accessed":False,
                "market_modified":False,
                "market_opening_confirmed":False,
            }
            receipts.append(obj)
            counts["address_already_saved_in_related_source_card"]+=1
            if len(examples)<40:examples.append(obj)
    if len(receipts)>MAX_RESULTS:
        raise ValueError("Unbounded candidate count: require reviewed batching instead")
    return {
        "schema":1,"as_of":today.isoformat(),
        "source":"happings.com","catalog_markets":len(rows),
        "market_identities_preserved":len(ids),
        "legacy_publisher_records_examined":checked,
        "source_url_layouts":{
            category:dict(sorted(stat.items()))
            for category,stat in sorted(format_counters.items())
        },
        "eligible_identity_groups":len(groups),
        "field_sibling_candidates":len(receipts),
        "counts":dict(sorted(counts.items())),
        # Full per-market review queue is stored only in the short-lived
        # runner artifact. It is NOT committed to Git every day.
        "candidate_records":receipts,
        "examples":examples,
        "all_proposals_review_only":True,
        "source_automation_consent_inferred":False,
        "original_market_records_deleted":0,
        "catalog_fields_updated":0,
        "market_openings_confirmed":0,
        "new_map_coordinates_added":0,
    }


def verify(report,original_size):
    if (not isinstance(report,dict) or report.get("schema")!=1
        or report.get("market_identities_preserved")!=original_size
        or report.get("catalog_markets")!=original_size
        or report.get("all_proposals_review_only") is not True
        or report.get("source_automation_consent_inferred") is not False
        or any(report.get(k)!=0 for k in (
            "original_market_records_deleted","catalog_fields_updated",
            "market_openings_confirmed","new_map_coordinates_added"))
        or report.get("field_sibling_candidates")>MAX_RESULTS
        or report.get("field_sibling_candidates")!=len(report.get("candidate_records",[]))
        or sum(z.get("records",0) for z in report.get("source_url_layouts",{}).values())
            !=report.get("legacy_publisher_records_examined")):
        raise ValueError("Unapproved internal publisher sibling transfers")
    for item in report.get("examples",[]):
        if (item.get("automatic_fill_authorized") is not False
            or item.get("source_html_accessed") is not False
            or item.get("market_modified") is not False
            or not safe_stored_street(item.get("internal_street_already_stored"))):
            raise ValueError("Sibling source proof granted unreviewed field write")
    return True


def markdown(report):
    return "\n".join([
        "# Indirizzi già nel catalogo, persi in altre copie dello stesso mercato",
        "",
        "Analisi **senza accesso al sito Happings** o altri siti editoriali.",
        "Gli stessi ID, Comune, provincia, giorno e URL originale non bastano",
        "a certificare l'unicità della sede in un intero Comune.",
        "",
        "- Schede nazionali controllate: **"+str(report["catalog_markets"])+"**",
        "- Schede Happings controllate: **"+str(report["legacy_publisher_records_examined"])+"**",
        "- Candidate che hanno già un indirizzo in un'altra scheda: **"+
              str(report["field_sibling_candidates"])+"**",
        "- Gruppi con più sedi note: **"+
              str(report["counts"].get("more_than_one_known_street_in_same_city_day",0))+"**",
        "- Campi riempiti senza prova indipendente: **0**",
        "",
        "## Formati sorgente archiviati e perdite associate","",
        "| Struttura URL | Schede | Indirizzo assente | Sede non specifica | Orari assenti |",
        "|---|---:|---:|---:|---:|",
        *[
            "| "+name+" | "+str(f.get("records",0))+
            " | "+str(f.get("address_missing",0))+
            " | "+str(f.get("address_not_specific",0))+
            " | "+str(f.get("hours_missing",0))+" |"
            for name,f in sorted(report["source_url_layouts"].items(),
                                 key=lambda x:-x[1].get("records",0))
        ],
        "",
        "Le vecchie pagine `ad-...` possono non essere più raggiungibili:",
        "non cancellare mai le schede; controllare origine e redirect prima",
        "di abilitare la stessa struttura del parser automatico.",
        "",
        "## Esempi prioritari da confrontare con Comuni o dataset autorizzati", "",
        *[
            "- "+x["target_market_id"]+" ← "+x["existing_record_with_street_id"]+
            " (sede già archiviata: "+x["internal_street_already_stored"]+")"
            for x in report["examples"][:25]
        ],
        "",
        "Ogni proposta conserva entrambi gli ID, lo stesso URL fonte originale",
        "e una ragione esplicita per cui non viene promossa a sede verificata.",
    ])+"\n"


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",type=Path,default=Path("public/data/v1/manifest.json"))
    parser.add_argument("--today",type=date.fromisoformat,default=date.today())
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--summary",type=Path,required=True)
    args=parser.parse_args()
    original=load_existing(args.manifest)
    snap=[x["slug"] for x in original]
    report=analyze(original,today=args.today)
    verify(report,len(original))
    if snap!=[x["slug"] for x in original]:
        raise ValueError("Sibling audit unexpectedly changed original market identities")
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.summary.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,indent=2,ensure_ascii=False,sort_keys=True)+"\n","utf-8")
    args.summary.write_text(markdown(report),"utf-8")
    print(json.dumps({"happings_rows":report["legacy_publisher_records_examined"],
                      "already_stored_address_candidates":report["field_sibling_candidates"],
                      "markets_modified":0,"scraping_requests":0},ensure_ascii=False))


if __name__=="__main__":
    main()
