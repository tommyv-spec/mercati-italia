#!/usr/bin/env python3
"""Conservative source-bound forecast renewal for Milano weekly market cards.

Two independent municipal publications are required:
- stable GIS market ID + weekdays from Comune di Milano's GIS service
- market name + same weekdays in municipal PDF dated 2026-10-01
Neither publication verifies individual future opening days. Only the
existing 'mi-mss-ID' card can be updated, and future dates remain PREVISTA.
The old source URL, coordinates, identity, primary attribution and market
verification fields are never replaced. No market records are added/deleted.
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date
from pathlib import Path

from recurrence_refresh import explicit_rule

PDF_DOCUMENT = (
    "https://www2.comune.milano.it/documents/87339536/190972166/"
    "MSS+-+ubicazioni%2Corari%2Corganici+1+Ottobre+2026.pdf/"
    "d5b13a87-b9de-7c48-5674-65c4151565c3?t=1790841765683"
)
GIS_PAGE_START = ("https://gisportal.comune.milano.it/server/rest/services/"
                  "D_SUAP_Specialistica_autorizzazioni_concessioni/"
                  "MSS_Mercati_Settimanali_Scoperti/MapServer/0/query?")
OLD_DATASET = "https://dati.comune.milano.it/dataset/ds291-economia-mercati-settimanali-scoperti"
PDF_DATE = date(2026, 10, 1)
MAX_SOURCE_AGE_DAYS = 540
MAX_RECONCILED = 84
WEEKDAYS = ("lunedì","martedì","mercoledì","giovedì","venerdì","sabato","domenica")

# Reviewed identities, not fuzzy matches. The Sunday Pagano MM1 and Friday
# Pagano market are distinct, and may NEVER collapse to one identity.
PDF_TO_GIS_ALIAS = {
    "ZAMAGNA/PARAVIA":"zamagna",
    "MORETTO DA BS":"m. da brescia",
    "GRATOSOGLIO SUD":"gratosoglio S",
    "BENEDETTO MARCELLO":"b marcello",
    "BARIGOZZI":"barigozzi mazz",
    "TRAVERSI":"antona traversi",
    "GRATOSOGLIO NORD":"gratosoglio N",
    "PAGANO":"pagano (V alpini)",
    "CREMA":"crema piacenza",
    "RIPA":"ripa pta ticinese",
    "VALVASSORI PERONI":"v. peroni",
    "PAGANO MM1":"mario pagano M1",
    "PONTI":"ponti e.",  # GIS label "Ettore Ponti"; the only Ponti in both, Monday
}
# The PDF's Ciccotti street note mentions an active construction closure.
# The excerpt's layout does not prove whether the entire market is affected.
HOLD_MARKETS = frozenset({"ciccotti"})
OFFICIAL_PDF_SOURCE = {
    "nome": "Comune di Milano — Mercati settimanali scoperti (report ubicazioni, 01/10/2026; date previste)",
    "url": PDF_DOCUMENT,
}


def key(value):
    decomposed = unicodedata.normalize("NFKD", str(value or ""))
    clean = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9]+"," ",clean.casefold()).strip()


def verified_pairs(pdf, gis):
    """Return per-GIS approved weekday sets and an independent review report."""
    if (not isinstance(pdf, dict) or pdf.get("schema") != 1 or
            pdf.get("publisher") != "Comune di Milano" or
            pdf.get("publisher_document_date") != PDF_DATE.isoformat() or
            pdf.get("publisher_report_url") != PDF_DOCUMENT or
            pdf.get("record_confirmations") != 0 or
            pdf.get("automatic_import_permission") is not False or
            not isinstance(pdf.get("obs"), list) or len(pdf["obs"]) != 87 or
            pdf.get("expected_rows") != 87 or pdf.get("expected_distinct_market_names") != 80):
        raise ValueError("Unreviewed or changed official 2026 PDF observation manifest")
    if (not isinstance(gis, dict) or gis.get("schema") != 1 or
            gis.get("publisher") != "Comune di Milano" or
            gis.get("record_count") != 84 or
            gis.get("not_a_current_market_verification") is not True or
            not str(gis.get("source_url","")).startswith(GIS_PAGE_START) or
            not isinstance(gis.get("records"),list) or len(gis["records"]) != 84):
        raise ValueError("Unreviewed or changed official Milan GIS snapshot")
    by_name, ids = {}, set()
    for row in gis["records"]:
        sid, name, days = row.get("id"),row.get("name"),row.get("weekdays")
        if (not isinstance(sid,int) or isinstance(sid,bool) or sid<1 or sid>2000
                or sid in ids or not isinstance(name,str) or not name.strip()
                or key(name) in by_name or not isinstance(days,list)
                or not days or any(type(day) is not int or not 0<=day<=6 for day in days)
                or len(set(days))!=len(days) or row.get("status")!="attivo"):
            raise ValueError("Invalid/repeated Milan GIS identity or schedule")
        ids.add(sid)
        by_name[key(name)]=row
    by_pdf=defaultdict(set)
    pairs=set()
    for row in pdf["obs"]:
        name, day=row.get("name"),row.get("weekday")
        if (not isinstance(name,str) or not name.strip() or
                type(day) is not int or not 0<=day<=6 or
                type(row.get("municipio")) is not int or not 1<=row["municipio"]<=9):
            raise ValueError("Corrupt publisher PDF name/weekday")
        k=(key(name),day)
        if k in pairs: raise ValueError("PDF market row was copied twice")
        pairs.add(k)
        target=PDF_TO_GIS_ALIAS.get(name, name)
        by_pdf[key(target)].add(day)
    if len({k[0] for k in pairs}) != 80:
        raise ValueError("Publisher PDF distinct-market count changed")
    matched={}
    counts=Counter()
    ambiguous=[]
    for pdf_name, days in by_pdf.items():
        row=by_name.get(pdf_name)
        if not row:
            counts["pdf_names_without_exact_or_approved_alias"]+=1
            if len(ambiguous)<12:ambiguous.append(pdf_name)
            continue
        if key(row["name"]) in HOLD_MARKETS:
            counts["held_possible_temporary_closure"]+=1
            continue
        gis_days=set(row["weekdays"])
        if days != gis_days:
            counts["held_missing_or_conflicting_weekdays"]+=1
            if len(ambiguous)<12:
                ambiguous.append(row["name"]+": GIS "+str(sorted(gis_days))
                                 +" versus PDF "+str(sorted(days)))
            continue
        matched[row["id"]]=sorted(days)
        counts["municipal_market_ids_with_two_source_day_agreement"]+=1
        counts["matched_weekday_rows"]+=len(days)
    if not 40<=len(matched)<=MAX_RECONCILED:
        raise ValueError("Milan dual-source weekday agreement fell outside approved range")
    return matched, {
        "schema":1,
        "citywide_reported_markets_not_asserted_as_distinct_records":93,
        "gis_market_ids":len(ids),
        "pdf_weekday_rows":len(pdf["obs"]),
        "pdf_distinct_name_labels":80,
        "counts":dict(sorted(counts.items())),
        "matched_ids":sorted(matched),
        "held_examples":ambiguous,
        "future_events_confirmed":0,
        "net_new_market_ids_authorized":0,
    }


def reconcile(rows, pdf, gis, *, today=None, apply=False):
    """Overlay recent schedule source evidence only on previously known IDs."""
    today=today or date.today()
    if type(apply) is not bool or not isinstance(rows,list) or not 1<=len(rows)<=100000:
        raise ValueError("Invalid Milan overlay mode/catalog")
    approved,evidence_report=verified_pairs(pdf,gis)
    age=(today-PDF_DATE).days
    in_window=0<=age<=MAX_SOURCE_AGE_DAYS
    output=[]
    seen=set()
    counts=Counter()
    modified_ids=[]
    for original in rows:
        sid=original.get("slug")
        if not isinstance(sid,str) or not sid or sid in seen:
            raise ValueError("Duplicate/missing stable market ID")
        seen.add(sid)
        nextrow=deepcopy(original)
        if sid.startswith("mi-mss-"):
            try:
                key_id=int(sid[7:])
            except ValueError:
                counts["held_unrecognized_milan_id"]+=1
                output.append(nextrow)
                continue
            if key_id in approved:
                if (original.get("regione")!="Lombardia"
                        or original.get("citta")!="Milano"
                        or original.get("url_fonte")!=OLD_DATASET):
                    raise ValueError("Milan municipal ID re-used by conflicting publisher "+sid)
                if (original.get("verificato_il") or original.get("date_quality") in
                        ("confermata","riportata")
                        or original.get("status") in ("archiviato","annullato","attivo")):
                    counts["held_previously_verified_or_inactive"]+=1
                elif not in_window:
                    counts["held_stale_oct2026_pdf"]+=1
                else:
                    rule=explicit_rule(original.get("ricorrenza_testo"))
                    newdays=approved[key_id]
                    if rule and (rule.get("kind")!="weekly" or
                                 rule.get("weekdays")!=newdays):
                        counts["held_existing_weekday_conflict"]+=1
                    else:
                        stamp=str(original.get("aggiornato_il") or "")[:10]
                        if stamp and stamp > PDF_DATE.isoformat():
                            counts["held_newer_source_already_present"]+=1
                        elif apply:
                            nextrow["aggiornato_il"]=PDF_DATE.isoformat()
                            nextrow["aggiornamento_ambito"]="dataset"
                            # The PDF is the content proving this schedule: an older
                            # declared date (the 2024 open-data file) must not age it out.
                            if str(nextrow.get("fonte_aggiornata_il") or "") < PDF_DATE.isoformat():
                                nextrow["fonte_aggiornata_il"]=PDF_DATE.isoformat()
                            nextrow["ricorrenza_testo"]="settimanale - "+", ".join(
                                WEEKDAYS[d] for d in newdays)
                            origin=list(nextrow.get("fonti") or [])
                            if not all(isinstance(v,dict) for v in origin):
                                raise ValueError("Untrusted Milan original source list")
                            prior={"nome":str(original.get("fonte") or ""),
                                   "url":str(original.get("url_fonte") or "")}
                            if prior not in origin:origin.append(prior)
                            if OFFICIAL_PDF_SOURCE not in origin:
                                origin.append(dict(OFFICIAL_PDF_SOURCE))
                            nextrow["fonti"]=origin
                            counts["current_two_source_weekday_facts_applied"]+=1
                        else:
                            counts["candidate_existing_market_schedules"]+=1
        if nextrow != original: modified_ids.append(sid)
        output.append(nextrow)
    if len(output)!=len(rows) or len({x["slug"] for x in output})!=len(rows):
        raise ValueError("Source reconcile changed market identities")
    report={
        "schema":1,"review_only":not apply,"publisher_report_date":PDF_DATE.isoformat(),
        "source_age_days":age,"reconciled_id_count":len(approved),
        "records_total":len(rows),"records_deleted":0,"records_added":0,
        "verified_future_events_created":0,"confirmed_dates_created":0,
        "coordinates_changed":0,"primary_sources_changed":0,
        "modified_ids":sorted(modified_ids),
        "counts":dict(sorted(counts.items())),"evidence":evidence_report,
    }
    return output,report


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--pdf",type=Path,default=Path("backend/data/milano-mss-oct2026-observations.json"))
    p.add_argument("--gis",type=Path,default=Path("backend/data/milano-mss-gis-reviewed.json"))
    p.add_argument("--today",type=date.fromisoformat,default=date.today())
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--apply",action="store_true")
    args=p.parse_args()
    from merge_catalog import load_existing
    a,b=reconcile(load_existing(args.manifest),json.loads(args.pdf.read_text("utf-8")),
                  json.loads(args.gis.read_text("utf-8")),today=args.today,apply=args.apply)
    for path in (args.out,args.report):path.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(a,ensure_ascii=False,indent=2)+"\n","utf-8")
    args.report.write_text(json.dumps(b,ensure_ascii=False,indent=2)+"\n","utf-8")
    print("MILANO_RECONCILIATION",json.dumps({
        "eligible":b["reconciled_id_count"],"modified":len(b["modified_ids"]),
        "confirmed_future_events":0,
    }))


if __name__=="__main__":
    main()
