#!/usr/bin/env python3
"""Add only five individually reviewed Municipio XIII market venue identities.

The official 2026 DD CS/647 lists Casalotti/Ormea, Fogaccia, Torrevecchia,
Valle Aurelia; September 2025 municipal resolution names San Silverio.
A 2024 KML holds two Fogaccia markers; Tuesday currently has one stall and
temporary relocation, so only Saturday is a candidate. Urbano II / Pineta
Sacchetti awaits evidence of completion of planned move. All cards have NO
verified event, NO geocoded point, NO navigation, and do not copy vendor PII.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import date
from pathlib import Path
from collections import Counter

from merge_catalog import load_existing
from recurrence_refresh import WEEKDAYS, explicit_rule
from reviewed_city_evidence import NAVIGATION_HOLD
from export_static import normalize

REVIEWED = "2026-10-13"
DOC_2026 = "https://www.comune.roma.it/web-resources/cms/documents/MunXIII_DD647_2026_Graduatorie_mercati.pdf"
DOC_ORMEA = "https://www.comune.roma.it/web-resources/cms/documents/Determina_17723_24_02_2025_venerd_firm.pdf"
DOC_SILVERIO = "https://www.comune.roma.it/web/it/bando-concorso.page?contentId=BEC1343579"
DOC_MOVE = "https://www.comune.roma.it/web/it/bando-concorso.page?contentId=BEC1533869"
HISTORICAL_AMA = "https://www.comune.roma.it/web-resources/cms/documents/Contratto_AMA_2024__2025_Allegato_7_Carta_Municipale_Municipio_13.pdf"
CATALOG_SOURCE = "https://dati.comune.roma.it/catalog/dataset/d881"
MAX_NEW = 5
EXPECTED_EXISTING = {"irnerio-roma":"Via Aurelia","casalotti-roma":"Via Borgo Ticino"}
EVIDENCE_FILE = Path(__file__).resolve().parent/"data/roma-xiii-verified-venue-evidence-2026-10-13.json"

EXPECTED = {
    "rm13-plateatico-san-silverio":{
        "name":"Mercato plateatico San Silverio",
        "address":"Via di San Silverio","source_date":"2025-09-24",
        "weekdays":[],"url":DOC_SILVERIO,
    },
    "rm13-salt-casalotti-ormea":{
        "name":"Mercato saltuario Casalotti – Piazza Ormea",
        "address":"Piazza Ormea","source_date":"2026-03-31",
        "weekdays":[0,4],"url":DOC_2026,
    },
    "rm13-salt-fogaccia-sabato":{
        "name":"Mercato saltuario Fogaccia – sabato",
        "address":"Via Cornelia (parcheggio con accesso adiacente alla scuola Anna Frank)",
        "source_date":"2026-03-31","weekdays":[5],"url":DOC_2026,
    },
    "rm13-salt-torrevecchia":{
        "name":"Mercato saltuario Torrevecchia",
        "address":"Via di Torrevecchia","source_date":"2026-03-31",
        "weekdays":[0,4],"url":DOC_2026,
    },
    "rm13-salt-valle-aurelia":{
        "name":"Mercato saltuario Valle Aurelia",
        "address":"Viale di Valle Aurelia","source_date":"2026-03-31",
        "weekdays":[3],"url":DOC_2026,
    },
}
# These are *identity* aliases, not fuzzy merging hints.
SOURCE_ALIASES={
    "rm13-plateatico-san-silverio":["san silverio","aurelio"],
    "rm13-salt-casalotti-ormea":["casalotti","ormea"],
    "rm13-salt-fogaccia-sabato":["fogaccia","montespaccato"],
    "rm13-salt-torrevecchia":["torrevecchia"],
    "rm13-salt-valle-aurelia":["valle aurelia"],
}
EXCEPT_ALREADY_EXISTING=frozenset(EXPECTED_EXISTING)


def checksum(data):
    return hashlib.sha256(json.dumps(
        data,sort_keys=True,ensure_ascii=False,separators=(",",":")
    ).encode()).hexdigest()


def validate_manifest(evidence):
    if (not isinstance(evidence,dict) or evidence.get("schema")!=1
            or evidence.get("reviewed_at")!=REVIEWED
            or evidence.get("municipality")!="Roma"
            or evidence.get("region")!="Lazio"
            or evidence.get("expected_physical_market_identities")!=8
            or evidence.get("reviewed_existing_market_ids")!=2
            or evidence.get("approved_new_venue_candidates")!=5
            or evidence.get("quarantine_only_market_identities")!=1
            or evidence.get("direct_pdf_2026")!=DOC_2026
            or evidence.get("municipal_2025_ormea_return")!=DOC_ORMEA
            or evidence.get("municipal_2025_san_silverio")!=DOC_SILVERIO
            or evidence.get("municipal_2026_fogaccia_tuesday_move")!=DOC_MOVE
            or evidence.get("historical_markets_reference")!=HISTORICAL_AMA
            or not isinstance(evidence.get("entities"),list)
            or len(evidence["entities"])!=8):
        raise ValueError("Unapproved eight-source municipality review")
    p=evidence.get("source_policy")
    if not isinstance(p,dict) or len(p)!=6 or not all(v is True for v in p.values()):
        raise ValueError("Rome source policy now implies event verification or geocoding")
    seen=set(); candidates={}
    for x in evidence["entities"]:
        key=x.get("canonical_id")
        if not key or key in seen:
            raise ValueError("Duplicated original municipal market identity")
        seen.add(key)
        status=x.get("record_status")
        if status=="candidate_approved_for_guarded_DEV":
            sid=x.get("slug")
            if sid not in EXPECTED or sid in candidates:
                raise ValueError("Unreviewed new market ID")
            expected=EXPECTED[sid]
            for actual,reference in (
                (x.get("name"),expected["name"]),
                (x.get("street"),expected["address"]),
                (x.get("source_date"),expected["source_date"]),
                (x.get("source_day_numbers"),expected["weekdays"]),
                (x.get("publisher_url"),expected["url"]),
            ):
                if actual!=reference:
                    raise ValueError("Municipal 2026 venue name/location/day differs from reviewed source")
            if not isinstance(x.get("notes"),str) or len(x["notes"])<40:
                raise ValueError("No disclaimer on old source status")
            if sid=="rm13-salt-casalotti-ormea" and x.get("additional_source_url")!=DOC_ORMEA:
                raise ValueError("Ormea 2025 restoration proof missing")
            if sid=="rm13-salt-fogaccia-sabato":
                other=x.get("quarantined_other_day") or {}
                if other.get("weekday")!=1 or other.get("evidence_url")!=DOC_MOVE:
                    raise ValueError("Fogaccia Tuesday temporary one-stall move not quarantined")
            candidates[sid]=x
        elif status=="already_published":
            if x.get("existing_slug") not in EXPECT_EXISTING:
                raise ValueError("Unrecognized already-published Roman market")
        elif status=="quarantine_only":
            if key!="pineta-sacchetti-urbano-ii" or not x.get("reason"):
                raise ValueError("Wrong withheld relocation source")
        else:
            raise ValueError("Unreviewed source promotion status")
    if set(candidates)!=set(EXPECTED) or set(seen)!={
        "irnerio","casalotti-plateatico","aurelio-san-silverio",
        "pineta-sacchetti-urbano-ii","casalotti-ormea-saltuario",
        "fogaccia","torrevecchia-saltuario","valle-aurelia-saltuario",
    }:
        raise ValueError("Missing or extra municipal market identities")
    return candidates


def make_market(source):
    sid=source["slug"]
    case=EXPECTED[sid]
    day=case["weekdays"]
    recurrence=("settimanale - "+", ".join(WEEKDAYS[x] for x in day)) if day else (
        "Orari e giorni da verificare presso il Municipio XIII")
    source_name="Roma Capitale, Municipio XIII — fonte amministrativa (apertura non confermata)"
    extra=[{"nome":source_name,"url":case["url"]}]
    if sid=="rm13-salt-casalotti-ormea":
        extra.append({"nome":"Roma Capitale — ricollocamento Ormea 2025","url":DOC_ORMEA})
    if sid=="rm13-plateatico-san-silverio":
        extra.append({"nome":"Roma Capitale — elenco comunale mercati 2024–25","url":HISTORICAL_AMA})
    note=(source["notes"]+" Fonte: "+case["source_date"]+
          ". Programma settimanale soltanto previsto, non conferma di aperture o presenza operatori."
          " Il punto esatto di navigazione necessita verifica.")
    market={
        "slug":sid,"nome":case["name"],"citta":"Roma","provincia":"RM",
        "regione":"Lazio","indirizzo":case["address"],
        "lat":None,"lng":None,"position_quality":"sconosciuta",
        "navigazione_sospesa_motivo":NAVIGATION_HOLD,
        "categoria":"misto","tags":["mercato comunale",source["official_kind"]],
        "status":"non_confermato","date":[],"date_quality":"sconosciuta",
        "ricorrenza_testo":recurrence,"orario_testo":"",
        "descrizione":note[:900],
        "fonte":source_name,"url_fonte":case["url"],"fonti":extra,
        "id_fonte":sid,"aggiornato_il":case["source_date"],
        "aggiornamento_ambito":"dataset",
        "verificato_il":"","confidence":0,
    }
    if day:
        rule=explicit_rule(market["ricorrenza_testo"])
        if not rule or rule.get("kind")!="weekly" or rule["weekdays"]!=day:
            raise ValueError("Publisher weekday would not be safely forecast")
    return market


def venue_clash(base, incoming):
    """Reject actual same city / name / street, not speculative similar names."""
    import re,unicodedata
    def key(x):
        s=unicodedata.normalize("NFKD",str(x or ""))
        return re.sub(r"[^a-z0-9]+"," ", "".join(
            ch for ch in s if not unicodedata.combining(ch)
        ).casefold()).strip()
    needle=key(incoming["nome"])
    street=key(incoming["indirizzo"])
    for item in base:
        if key(item.get("citta"))!="roma" or key(item.get("regione"))!="lazio":
            continue
        if needle==key(item.get("nome")) and street==key(item.get("indirizzo")):
            return item["slug"]
        # Protect a generic exact market's alternate historic name at the same
        # street. This does NOT conflate Ormea with the plateatico Casalotti.
        label=key(item.get("nome"))
        if street==key(item.get("indirizzo")) and any(
            alias==label for alias in SOURCE_ALIASES[incoming["slug"]]
        ):
            return item["slug"]
    return None


def integrate(base,evidence,*,apply=False,today=None):
    if type(apply) is not bool or not isinstance(base,list) or not 1<=len(base)<=100000:
        raise ValueError("Untrusted existing source catalog")
    today=today or date.today()
    cases=validate_manifest(evidence)
    original={r.get("slug"):r for r in base}
    if None in original or len(original)!=len(base):
        raise ValueError("Missing or repeated existing IDs")
    for sid,street in EXPECTED_EXISTING.items():
        match=original.get(sid)
        if (match is None or match.get("citta")!="Roma"
                or match.get("regione")!="Lazio"
                or match.get("indirizzo")!=street
                or match.get("url_fonte")!=CATALOG_SOURCE):
            raise ValueError("Existing Rome plateatico market source moved: "+sid)
    candidate=[make_market(cases[sid]) for sid in sorted(cases)]
    proposed=[]
    added=[]
    already=[]
    for x in candidate:
        sid=x["slug"]
        prior=original.get(sid)
        if prior:
            # In a subsequent run, all published source IDs must remain
            # attributed, explicitly non-confirmed, and non-navigable.
            if (prior.get("nome")!=x["nome"] or prior.get("citta")!="Roma" or
                prior.get("regione")!="Lazio" or
                prior.get("indirizzo")!=x["indirizzo"] or
                prior.get("url_fonte")!=x["url_fonte"] or
                prior.get("id_fonte")!=x["id_fonte"] or
                prior.get("navigazione_sospesa_motivo")!=NAVIGATION_HOLD or
                prior.get("lat") is not None or prior.get("lng") is not None or
                prior.get("verificato_il") or
                prior.get("date_quality")=="confermata" or
                prior.get("status")!="non_confermato" or
                prior.get("aggiornato_il")!=x["aggiornato_il"]):
                raise ValueError("Reviewed Rome venue was edited without source approval: "+sid)
            original_links={v.get("url") for v in prior.get("fonti",[])
                            if isinstance(v,dict)}
            if set(v["url"] for v in x["fonti"]) - original_links:
                raise ValueError("Rome venue lost municipality document evidence: "+sid)
            already.append(sid)
            continue
        collision=venue_clash(base,x)
        if collision:
            raise ValueError("Possible venue collision "+sid+" with "+collision)
        if (today-date.fromisoformat(x["aggiornato_il"])).days < 0:
            raise ValueError("Official source date cannot be future")
        normalized,error=normalize(x,today)
        if error or normalized is None:
            raise ValueError("Official source venue not accepted by exporter: "+str(error))
        added.append(sid)
        proposed.append(x)
    if len(added)+len(already)!=MAX_NEW:
        raise ValueError("Partial Rome XIII curated source upload")
    rows=(base+proposed) if apply else list(base)
    report={
        "schema":1,"enabled":apply,"review_only":not apply,
        "source_manifest_sha256":checksum(evidence),
        "source_updated":"2026-03-31",
        "existing_catalog_records":len(base),
        "source_market_identities":8,
        "official_preexisting_plateatici":2,
        "candidate_venue_records":MAX_NEW,
        "new_market_ids":sorted(added) if apply else [],
        "review_only_potential_ids":sorted(added) if not apply else [],
        "already_published_curated_ids":sorted(already),
        "new_market_count":len(added) if apply else 0,
        "records_added":len(added) if apply else 0,
        "records_removed":0,"existing_records_changed":0,
        "new_coordinates_added":0,
        "new_opening_confirmations":0,
        "new_human_verifications":0,
        "forecast_days_documented":[0,3,4,5],
        "held_2026_fogaccia_tuesday_single_stall":True,
        "held_urbano_ii_relocation":True,
        "total_resulting_records":len(rows),
    }
    return rows,report


def validate_added(old,new,report,evidence):
    if (not isinstance(old,list) or not isinstance(new,list) or
            report.get("schema")!=1 or report.get("enabled") is not True or
            report.get("records_removed")!=0 or
            report.get("existing_records_changed")!=0 or
            report.get("new_coordinates_added")!=0 or
            report.get("new_opening_confirmations")!=0 or
            report.get("new_human_verifications")!=0 or
            report.get("source_manifest_sha256")!=checksum(evidence) or
            new[:len(old)]!=old):
        raise ValueError("Rome XIII insert changed existing market data or provenance")
    additions=new[len(old):]
    if (len(additions)!=report.get("records_added")
            or sorted(x["slug"] for x in additions)!=report.get("new_market_ids")
            or len(additions)>5 or
            not all(x.get("navigazione_sospesa_motivo")==NAVIGATION_HOLD
                    and x.get("lat") is None and x.get("lng") is None
                    and not x.get("verificato_il") for x in additions)):
        raise ValueError("Unapproved Roma venue IDs or unsafe navigation")
    return {
        "schema":1,"old_market_records_checked":len(old),
        "approved_official_market_additions":len(additions),
        "original_records_modified":0,"source_urls_lost":0,
        "verified_events_created":0,
        "precise_geocodes_created":0,"directions_activated":0,
        "safe":True,
    }


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--evidence",type=Path,default=EVIDENCE_FILE)
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--apply",action="store_true")
    a=p.parse_args()
    source=json.loads(a.evidence.read_text("utf-8"))
    rows,report=integrate(load_existing(a.manifest),source,apply=a.apply)
    for q in (a.out,a.report):q.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+"\n","utf-8")
    a.report.write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n","utf-8")
    print("ROMA_XIII_CURATED_VENUES",json.dumps({
        "reviewed_identities":8,"added_to_candidate":report["new_market_count"],
        "already_present":len(report["already_published_curated_ids"]),
        "original_ids_modified":0,"verified_openings":0,
    }))
if __name__=="__main__":
    main()
