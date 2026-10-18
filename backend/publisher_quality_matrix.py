#!/usr/bin/env python3
"""Per-publisher, full-catalog quality audit ordered by REAL entry count.

All existing source labels get an audit, not just the official data.gov.it
candidate datasets. This module is read-only: a large legacy aggregator is
not approved for bulk re-scraping or event confirmation by appearing here.

A "source date" in a card may be an import timestamp, NOT a venue check.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit

from catalog_quality_report import VAGUE_ADDRESSES, key as text_key, suspicious_city
from merge_catalog import load_existing
from recurrence_refresh import explicit_rule, parse_source_day

SCHEMA=1
MAX_MARKETS=100_000
MAX_PUBLISHERS=2000
MAX_REGISTRY_SOURCES=450
MAX_EXAMPLES=5
MAX_SOURCE_DATE_AGE=540
WEEKDAYS=("lunedi","martedi","mercoledi","giovedi","venerdi","sabato","domenica")
SUFFIX_DAY=re.compile(r"-(lunedi|martedi|mercoledi|giovedi|venerdi|sabato|domenica)$")

# This classification is explicitly NOT an import or rights approval.
REVIEWED_KINDS={
    "happings.com":("legacy_aggregator","weekly_area_index_and_event_details","publisher_rights_unreviewed"),
    "eventiesagre.it":("third_party_event_aggregator","regional_listing_and_details","urls_only_no_bulk_content_reuse"),
    "cosedicasa.com":("editorial_event_calendar","monthly_recurrence_with_exceptions","publisher_rights_unreviewed"),
    "Regione Lombardia – MERCap (CC0 1.0 dichiarata)":(
        "regional_open_data_adapter","one_market_id_per_weekday","existing_adapter_source_scope"),
    "Comune di Milano - Open Data (CC BY 4.0)":(
        "municipal_open_data_adapter","one_venue_with_weekdays","existing_adapter_source_scope"),
    "Comune di Bologna — dati ufficiali; apertura non confermata":(
        "municipal_open_data_adapter","market_venues_mixed_with_fairs","existing_adapter_source_scope"),
}
REGISTERED_DATASET_ADAPTERS={
    "2e41941b-80fb-4ded-8330-427383f725f8":"lombardia",
    "62be39fe-adbe-464a-84b1-85bc060b75d2":"corciano",
    "0bb2a3cb-a3d0-44ef-9053-061006c8cd50":"bologna",
    "0b6c9c3c-a6c4-43b6-91f5-9445ee3cb09b":"milano",
}
VALID_STATUS={
    "metadata_candidate_only","schema_sampled_review_only","already_integrated_adapter",
    "approved_dev_only","statistics_not_event_venues","concession_registry_not_market_venues",
}


def _validate_registry(registry,probes=None):
    if (not isinstance(registry,dict) or registry.get("schema")!=1
        or registry.get("record_imports")!=0
        or not isinstance(registry.get("sources"),list)
        or not 1<=len(registry["sources"])<=MAX_REGISTRY_SOURCES):
        raise ValueError("Untrusted official source discovery registry")
    ids=set()
    for s in registry["sources"]:
        sid=s.get("id") if isinstance(s,dict) else None
        if not isinstance(sid,str) or not sid or sid in ids:
            raise ValueError("Missing/repeated discovered source ID")
        ids.add(sid)
    if probes is not None and (
        not isinstance(probes,dict) or probes.get("schema")!=1
        or probes.get("imports")!=0 or probes.get("verified_event_count")!=0
        or not isinstance(probes.get("probe_history"),dict)
    ):
        raise ValueError("Untrusted schema-preview history")
    return ids


def _source(row):
    raw=row.get("fonte")
    label=str(raw or "").strip()
    if not label:
        url=str(row.get("url_fonte") or "")
        host=urlsplit(url).hostname if url.startswith("https://") else None
        label=host or "[publisher unknown]"
    if len(label)>170:
        return "[invalid publisher label]"
    return label


def _safe_origin(url):
    if not isinstance(url,str) or not url or len(url)>1800:
        return False
    try:
        p=urlsplit(url)
        return (p.scheme=="https" and bool(p.hostname)
                and not p.username and not p.password
                and p.port in (None,443))
    except ValueError:
        return False


def _day_conflict(row):
    """Slug/day conflict with explicit WEEKLY rule; monthlies are different."""
    slug=str(row.get("slug") or "").casefold()
    m=SUFFIX_DAY.search(slug)
    if not m:
        return False
    rule=explicit_rule(row.get("ricorrenza_testo"))
    if not rule or rule.get("kind")!="weekly":
        return False
    return WEEKDAYS.index(m.group(1)) not in set(rule.get("weekdays") or ())


def _projected_weekday_conflict(row):
    if row.get("date_quality")!="prevista":
        return False
    rule=explicit_rule(row.get("ricorrenza_testo"))
    if not rule or rule.get("kind")!="weekly":
        return False
    dates=row.get("date")
    if not isinstance(dates,list) or not dates:
        return False
    allowed=set(rule.get("weekdays") or ())
    # Check all bounded dates; never reinterpret individual old editions.
    for raw in dates[:130]:
        try:
            if date.fromisoformat(str(raw)).weekday() not in allowed:
                return True
        except ValueError:
            return True
    return False


def _field_problems(row,today):
    bad=[]
    address=str(row.get("indirizzo") or "").strip()
    hours=str(row.get("orario_testo") or "").strip()
    if not address:
        bad.append("address_missing")
    elif text_key(address) in VAGUE_ADDRESSES:
        bad.append("address_generic_not_navigable")
    if not hours:
        bad.append("hours_missing")
    if not row.get("date"):
        bad.append("future_dates_missing")
    if row.get("lat") is None or row.get("lng") is None:
        bad.append("coordinates_missing")
    # Unsupported *confidence* labels are review cases, not fabricated fixes.
    if row.get("position_quality")=="precisa" and (
        row.get("lat") is None or row.get("lng") is None):
        bad.append("precise_position_without_coordinates")
    if not _safe_origin(row.get("url_fonte")):
        bad.append("source_url_invalid_or_missing")
    if suspicious_city(row.get("citta")):
        bad.append("suspicious_city")
    if _day_conflict(row):
        bad.append("slug_conflicts_with_explicit_weekday")
    if _projected_weekday_conflict(row):
        bad.append("forecast_dates_disagree_with_weekday")
    if row.get("date_quality") in ("prevista","confermata") and not row.get("date"):
        bad.append("forecast_quality_without_dates")
    observed=parse_source_day(row.get("aggiornato_il"))
    if observed is None:
        bad.append("source_or_import_date_unknown")
    else:
        age=(today-observed).days
        if age>MAX_SOURCE_DATE_AGE:
            bad.append("stored_source_or_import_date_older_than_540d")
        elif age < -1:
            bad.append("stored_date_in_future")
    # source date NEVER means individual event verification.
    return bad


def _publisher_action(label):
    kind,layout,rights=REVIEWED_KINDS.get(label,(
        "other_legacy_or_publisher","unclassified_source_page","source_rights_and_structure_require_review"))
    if label=="happings.com":
        next_action=("Audit catalog rows against publisher's weekly province lists and "
                     "event detail page formats. Prefer a separate current municipal "
                     "source for hours, street and seasonal exceptions; do not reimport "
                     "commercial source content or certify schedules from scraping.")
    elif label=="eventiesagre.it":
        next_action=("Use existing two-page rotating URLs-only discovery, then verify "
                     "dates/street with independent organizer/Comune; exclude expired editions.")
    elif label=="cosedicasa.com":
        next_action=("Check monthly recurrence and summer suspensions against a current "
                     "official organizer. Editorial 'next date' is not event confirmation; "
                     "do not republish copyrighted detail content.")
    elif "MERC" in label or "Lombardia" in label:
        next_action=("Run source-row identity and town+street+weekday checks from the "
                     "approved official MERCap adapter. Quarantine conflicting venue/day.")
    elif "Comune" in label or "dati." in label:
        next_action=("Check adapter source-row schema, stable venue IDs, source freshness "
                     "and accurate address/day mapping before applying any allowed fields.")
    else:
        next_action=("Identify original publisher and distribution rights; gather a bounded "
                     "schema sample and independent official evidence before field changes.")
    return {
        "kind":kind,"layout":layout,"rights_classification":rights,
        "automatic_import_authorized_by_this_audit":False,
        "automatic_source_row_reuse_authorized_by_this_audit":False,
        "next_action":next_action,
    }


def _score(records,counts):
    """Workload score, NOT trust, permissions, or number of true errors."""
    return (
        records + 3*counts["address_missing"] + 2*counts["hours_missing"]
        + counts["future_dates_missing"]
        + 2*counts["stored_source_or_import_date_older_than_540d"]
        + 6*counts["address_generic_not_navigable"]
        + 8*counts["slug_conflicts_with_explicit_weekday"]
        + 8*counts["forecast_dates_disagree_with_weekday"]
        + 10*counts["suspicious_city"]
    )


def analyze(rows,registry,*,probes=None,previous=None,today=None):
    today=today or date.today()
    if not isinstance(today,date) or not isinstance(rows,list) or not 1<=len(rows)<=MAX_MARKETS:
        raise ValueError("Invalid catalog size")
    _validate_registry(registry,probes)
    if previous is not None and (
        not isinstance(previous,dict) or previous.get("schema")!=SCHEMA
        or previous.get("research_only") is not True
        or previous.get("market_updates")!=0
        or previous.get("market_confirmations")!=0):
        raise ValueError("Untrusted prior source-level quality report")
    groups=defaultdict(Counter)
    samples=defaultdict(lambda:defaultdict(list))
    ids=set()
    for row in rows:
        if not isinstance(row,dict):
            raise ValueError("Market row is not an object")
        slug=row.get("slug")
        if not isinstance(slug,str) or not slug or slug in ids:
            raise ValueError("Missing or duplicate original market identity")
        ids.add(slug)
        label=_source(row)
        groups[label]["records"]+=1
        problems=_field_problems(row,today)
        for problem in problems:
            groups[label][problem]+=1
            if len(samples[label][problem])<MAX_EXAMPLES:
                samples[label][problem].append(slug)
    if len(groups)>MAX_PUBLISHERS:
        raise ValueError("Unbounded publisher cardinality")
    publishers=[]
    old_by_label={x["publisher"]:x for x in previous.get("publishers",[])} if previous else {}
    for label,c in groups.items():
        count=int(c["records"])
        rows_dict={k:int(v) for k,v in sorted(c.items())}
        meta=_publisher_action(label)
        old=old_by_label.get(label,{})
        before=old.get("records")
        publishers.append({
            "publisher":label, "records":count, "count_delta_since_last_audit":
                count-before if type(before)==int else None,
            "priority_workload_score_not_evidence":_score(count,c),
            "fields":rows_dict,
            "sample_id_only":{k:v for k,v in sorted(samples[label].items())},
            "actual_individual_market_validations":0,
            **meta,
        })
    publishers.sort(key=lambda x:(-x["records"],-x["priority_workload_score_not_evidence"],x["publisher"]))
    history=(probes or {}).get("probe_history",{})
    candidates=[]
    seen_sources=set()
    for src in registry["sources"]:
        sid=src["id"]
        if sid in seen_sources:
            raise ValueError("Repeated source ID")
        seen_sources.add(sid)
        triage=str(src.get("triage_class") or "")
        status="metadata_candidate_only"
        if triage=="aggregated_statistics":
            status="statistics_not_event_venues"
        elif triage=="concession_registry":
            status="concession_registry_not_market_venues"
        elif sid in REGISTERED_DATASET_ADAPTERS:
            status="already_integrated_adapter"
        elif history.get(sid):
            status="schema_sampled_review_only"
        if status not in VALID_STATUS:
            raise ValueError("Unrecognized candidate triage state")
        schema_review=history.get(sid,{}).get("viability")
        # Counts of stalls/concessions are not venue counts; never estimate
        # how many markets a discovery-only row might yield.
        candidates.append({
            "dataset_id":sid,"title":str(src.get("title") or "")[:190],
            "publisher":str(src.get("organization") or "")[:120],
            "triage_class":triage, "triage_score_not_market_yield":
                int(src.get("triage_score") or 0),
            "review_status":status, "schema_observation":
                str(schema_review)[:100] if schema_review else None,
            "record_count_measured":None,
            "actual_market_count_estimated":None,
            "market_events_confirmed":0,
            "new_market_imports_authorized_by_this_audit":False,
        })
    candidates.sort(key=lambda x:(
        0 if x["review_status"]=="already_integrated_adapter" else
        1 if x["triage_class"]=="market_location_candidate" else
        2 if x["triage_class"]=="general_market_candidate" else
        3 if x["triage_class"]=="mixed_events_candidate" else 9,
        -x["triage_score_not_market_yield"],x["dataset_id"]))
    if sum(x["records"] for x in publishers)!=len(rows):
        raise ValueError("A publisher lost catalog records during the audit")
    prev_names=set(old_by_label)
    all_names=set(groups)
    return {
        "schema":SCHEMA,
        "as_of":today.isoformat(),
        "research_only":True,
        "catalog_record_count":len(rows),
        "catalog_source_labels_count":len(publishers),
        "official_candidate_dataset_count":len(candidates),
        "source_labels_added_since_previous":sorted(all_names-prev_names) if previous else [],
        "source_labels_missing_since_previous":sorted(prev_names-all_names) if previous else [],
        "publishers":publishers,
        "candidate_datasets":candidates,
        "source_dates_are_not_per_market_confirmation":True,
        "aggregate_gaps_are_not_proven_source_errors":True,
        "source_count_is_not_number_of_independent_venues":True,
        "source_permissions_inferred":False,
        "market_updates":0,"market_confirmations":0,
        "markets_added":0,"markets_deleted":0,
        "source_snapshot_rows_reused":0,
    }


def validate(report,registry):
    if (not isinstance(report,dict) or report.get("schema")!=SCHEMA
        or report.get("research_only") is not True
        or report.get("source_dates_are_not_per_market_confirmation") is not True
        or report.get("source_permissions_inferred") is not False
        or any(report.get(k)!=0 for k in (
            "market_updates","market_confirmations","markets_added","markets_deleted",
            "source_snapshot_rows_reused"))
        or not isinstance(report.get("publishers"),list)
        or sum(x["records"] for x in report["publishers"])!=report.get("catalog_record_count")
        or len(report["publishers"])!=report.get("catalog_source_labels_count")
        or len(report.get("candidate_datasets",[]))!=len(registry.get("sources",[]))
        or any(x["automatic_import_authorized_by_this_audit"] is not False
               or x["automatic_source_row_reuse_authorized_by_this_audit"] is not False
               for x in report["publishers"])
        or any(x["new_market_imports_authorized_by_this_audit"] is not False
               for x in report["candidate_datasets"])
        or any(a["records"]<b["records"] for a,b in zip(
            report["publishers"],report["publishers"][1:]))):
        raise ValueError("Publisher audit cannot infer permissions or change catalog rows")
    return True


def _safe(value):
    return str(value or "").replace("|","/").replace("\n"," ").replace("\r"," ")[:170]


def markdown(report):
    publishers=report["publishers"]
    out=[
        "# Audit di ogni fonte nel catalogo — per numero reale di schede",
        "",
        "**Sola lettura.** Questo report copre TUTTE le fonti attualmente ",
        "presenti nel catalogo e, separatamente, le fonti ufficiali candidate.",
        "Nessun dato viene riletto o ripubblicato dal sito terzo.",
        "",
        "- Schede controllate: **"+str(report["catalog_record_count"])+"**",
        "- Fonti distinte nelle schede: **"+str(len(publishers))+"**",
        "- Dataset ufficiali candidati: **"+str(report["official_candidate_dataset_count"])+"**",
        "- Nuovi eventi certificati: **0**; schede modificate: **0**",
        "",
        "## 1. Fonti che abbiamo già, ordinate per numero di schede",
        "",
        "| Fonte | Record | Orari vuoti | Indirizzi vuoti | Coordinate vuote | Data fonte/import >540gg | Contraddizioni giorni | Modello |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for x in publishers:
        c=x["fields"]
        out.append("| "+_safe(x["publisher"])+" | "+str(x["records"])+
                   " | "+str(c.get("hours_missing",0))+" | "+str(c.get("address_missing",0))+
                   " | "+str(c.get("coordinates_missing",0))+
                   " | "+str(c.get("stored_source_or_import_date_older_than_540d",0))+
                   " | "+str(c.get("slug_conflicts_with_explicit_weekday",0))+
                   " | "+_safe(x["layout"])+" |")
    out.extend(["","## 2. Interventi sulle fonti più grandi",""])
    for x in publishers[:9]:
        out.extend(["### "+_safe(x["publisher"])+" — "+str(x["records"])+" schede",
                    "- Carenze strutturali: **non** prova che il dato originale sia scorretto.",
                    "- Licenze: "+_safe(x["rights_classification"]),
                    "- Prossimo passo: "+_safe(x["next_action"]),
                    ""])
    out.extend(["## 3. Tutti i dataset ufficiali candidati (nessuna importazione automatica)","",
                "| Dataset | Editore | Priorità metadati | Stato campione | Classe |",
                "|---|---|---:|---|---|"])
    for src in report["candidate_datasets"]:
        out.append("| "+_safe(src["title"])+
                   " | "+_safe(src["publisher"])+
                   " | "+str(src["triage_score_not_market_yield"])+
                   " | "+_safe(src["review_status"])+
                   " | "+_safe(src["triage_class"])+" |")
    out.extend(["","## Condizioni per un aggiornamento automatico reale","",
                "- Una modifica a un calendario editoriale NON verifica l'apertura della sede.",
                "- La data di import del record NON è la data di verifica del mercato.",
                "- Il sistema deve verificare schema, licenza e granularità prima di un nuovo adattatore.",
                "- Nessuna fusione o aggiunta di orari se Comune/sede/giorno si contraddicono.",
                "- Una fonte può scomparire temporaneamente senza che il mercato sia chiuso.",
                "- Le coordinate del centro Comune non sono l'ingresso del mercato.",""])
    return "\n".join(out)+"\n"


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--manifest",type=Path,default=Path("public/data/v1/manifest.json"))
    parser.add_argument("--registry",type=Path,default=Path("reports/automation/source-registry.json"))
    parser.add_argument("--probes",type=Path,default=Path("reports/automation/source-probes.json"))
    parser.add_argument("--previous",type=Path)
    parser.add_argument("--today",type=date.fromisoformat,default=date.today())
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--report",type=Path,required=True)
    a=parser.parse_args()
    old=load_existing(a.manifest)
    sources=json.loads(a.registry.read_text("utf-8"))
    probes=json.loads(a.probes.read_text("utf-8")) if a.probes.is_file() else None
    prior=json.loads(a.previous.read_text("utf-8")) if a.previous and a.previous.is_file() else None
    report=analyze(old,sources,probes=probes,previous=prior,today=a.today)
    validate(report,sources)
    for p in (a.out,a.report):p.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(report,sort_keys=True,indent=2,ensure_ascii=False)+"\n","utf-8")
    a.report.write_text(markdown(report),"utf-8")
    print(json.dumps({
        "sources_in_catalog":report["catalog_source_labels_count"],
        "official_candidates":report["official_candidate_dataset_count"],
        "cards_inspected":report["catalog_record_count"],
        "top_source":report["publishers"][0]["publisher"],
        "top_source_cards":report["publishers"][0]["records"],
        "market_updates":0,
    },ensure_ascii=False))
if __name__=="__main__":
    main()
