#!/usr/bin/env python3
"""Deterministic municipality repair and corrupted-schedule quarantine.

FIRST performed manually on real 2026-10-12 market records and compared with
7,894 official ISTAT municipalities (21 Feb 2026), exact region and province.
No coordinates are moved, no market is verified, no market ID is deleted.

City fixes require an independently published province mapping AND identical
municipality tokens in original name / original source-bound slug. Contaminated
scraper text can belong to two different cities with DIFFERENT opening days:
never project either weekday from that content without new evidence.
"""
from __future__ import annotations

import argparse
import difflib
import json
import re
from collections import Counter, defaultdict
from copy import deepcopy
from pathlib import Path

from catalog_quality_report import key, suspicious_city
from field_evidence import PUBLISHED_TOWN_FIXES
from merge_catalog import load_existing
from province_reconciliation import supplement as reconcile_provinces

SOURCE_DATE = "2026-02-21"
SOURCE_URL = "https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/"
SOURCE_XLSX = "https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.xlsx"
ISTAT_SHA = "83842076860450f7e482daecea6b7a769f5f93d0bf5b0d48802b44896d7a26d5"
PROJECTION_WARNING = "Calendario da verificare: testo origine con mercati/località concatenati"
MAX_SUGGESTIONS = 100
MAX_AUTOMATIC_FIXES = 60
MAX_FORECAST_QUARANTINE = 80
# Town rules for cards whose source town is not itself a comune (S31). Only
# happings.com: its steps read the card as published (field_evidence.as_published).
FORMER_REFERENCE = Path(__file__).resolve().parent / "data" / "istat-comuni-soppressi.json"
PUBLISHED_TOWN_SOURCE = "happings.com"
ROME_INVENTORY_SOURCE = "dati.comune.roma.it"  # Roma Capitale's own market list (d881)
SPELLING_CUTOFF = 0.85
CITY_FIX_BUDGET = 60  # town changes a night allowed by Autopilot and the release guard
TOTAL_CHANGE_BUDGET = 80  # province_reconciliation.MAX_TOTAL_CHANGES
RULE_ORDER = ("spelling", "former", "hamlet", "rome")
ALIASES = {
    "Valle d'Aosta/Vallée d'Aoste": "Valle d'Aosta",
    "Friuli-Venezia Giulia": "Friuli Venezia Giulia",
    "Trentino-Alto Adige/Südtirol": "Trentino-Alto Adige",
}


def slugkey(s):
    return key(s).replace(" ", "-")


def trusted_municipalities(data):
    if (not isinstance(data,dict) or data.get("schema") != 1
            or data.get("reference_date") != SOURCE_DATE
            or data.get("source") != SOURCE_XLSX
            or data.get("source_file_sha256") != ISTAT_SHA
            or data.get("municipality_count") != 7894
            or not isinstance(data.get("regions"), dict)
            or not isinstance(data.get("provinces_by_region"), dict)):
        raise ValueError("Unrecognized official ISTAT municipality revision")
    names = {}
    for region,values in data["regions"].items():
        codes=data["provinces_by_region"].get(region)
        if not isinstance(values,list) or not isinstance(codes,dict):
            raise ValueError("Missing ISTAT municipality-province correspondence")
        registry={}
        for name in values:
            if not isinstance(name,str) or name not in codes:
                raise ValueError("Malformed ISTAT municipality record")
            province=codes[name]
            if not isinstance(province,str) or not re.fullmatch(r"[A-Z]{2}",province):
                raise ValueError("Invalid ISTAT province code")
            k=key(name)
            if not k or k in registry:
                raise ValueError("Repeated municipality identity in ISTAT source")
            registry[k]=(name,province)
        if len(registry)!=len(values):
            raise ValueError("ISTAT record count mismatch")
        names[region]=registry
    if len(names)!=20 or sum(map(len,names.values()))!=7894:
        raise ValueError("Incomplete nationwide ISTAT reference")
    return names


def former_links(data):
    """Old name -> names it became: ISTAT merges (back to 1861) and renames (since 1991)."""
    if (not isinstance(data, dict) or data.get("schema") != 1
            or not isinstance(data.get("links"), list) or len(data["links"]) < 2500):
        raise ValueError("Unrecognized ISTAT former-comuni list")
    links = defaultdict(set)
    for old, new, kind in data["links"]:
        if kind not in ("soppresso", "rinominato"):
            raise ValueError("Unknown ISTAT comune change")
        links[key(old)].add(key(new))
    return links


def _today(name, links, current, seen=()):
    """Today's comuni an old name leads to, through later merges and renames."""
    found = set()
    for nxt in links.get(name, ()):
        if nxt not in seen:
            found |= {nxt} if nxt in current else _today(nxt, links, current, seen + (name,))
    return found


def published_town_proposal(record, official, former, rome_markets):
    """(rule, comune) for a happings.com town that is not a comune of its region.

    former:   a merged or renamed comune, followed to today's (Nibbiano -> Alta Val Tidone);
    hamlet:   "<comune> <more words>" (Africo Nuovo), or the start of exactly one
              current or former comune (Celle -> Celle Ligure; "Sestri" stays: Ponente
              was a comune too);
    rome:     a Roma Capitale market name, or a capitals-only label on a Rome card
              (Happings copies Roma Capitale's list, which writes names in capitals);
    spelling: exactly one comune of the province, and no former one, within a typo.
    Every rule looks only inside the card's province.
    """
    registry = official.get(record.get("regione"))
    town = str(record.get("citta") or "").strip()
    name = key(town)
    province = str(record.get("provincia") or "").strip().upper()
    # Scraper text gluing two markets together is the title rule's case, never ours.
    if (record.get("fonte") != PUBLISHED_TOWN_SOURCE or not registry or not name
            or name in registry or not re.fullmatch(r"[A-Z]{2}", province)
            or suspicious_city(town)):
        return None
    # A province code of another region contradicts the card: it waits (province rule).
    pool = {n: v for n, v in registry.items() if v[1] == province}
    if not pool:
        return None

    def leads(old):
        return former.get(old, set()) & pool.keys()
    numbered = re.fullmatch(r".+\s\d{1,2}", town)  # S15: the publisher's numbering
    found = leads(name)
    if found:
        return ("former", pool[next(iter(found))][0]) if len(found) == 1 else None
    if not numbered:
        heads = [n for n in pool if name.startswith(n + " ")]
        if heads:
            return "hamlet", pool[max(heads, key=len)][0]
        starts = ({n for n in pool if n.startswith(name + " ")}
                  | {old for old in former if old.startswith(name + " ") and leads(old)})
        if starts:
            only = next(iter(starts))
            return ("hamlet", pool[only][0]) if len(starts) == 1 and only in pool else None
    if province == "RM" and "roma" in pool and (name in rome_markets or town.upper() == town):
        return "rome", pool["roma"][0]
    if numbered:
        return None
    close = difflib.get_close_matches(name, list(pool), n=2, cutoff=SPELLING_CUTOFF)
    rivals = difflib.get_close_matches(name, [old for old in former if leads(old)], n=1,
                                       cutoff=SPELLING_CUTOFF)
    return ("spelling", pool[close[0]][0]) if len(close) == 1 and not rivals else None


def source_city_cross_contamination(raw):
    city=key(raw)
    return (
        ("mercato settimanale a " in city and "mercato settimanale di " in city)
        or (" in provincia" in city and "mercato settimanale" in city)
        or (" in pro " in city and "mercato settimanale" in city)
    )


def municipality_proposals(market, official):
    region=market.get("regione")
    origcity=str(market.get("citta") or "").strip()
    title=str(market.get("nome") or "").strip()
    slug=str(market.get("slug") or "")
    province=str(market.get("provincia") or "").upper()
    if not suspicious_city(origcity) or region not in official:
        return []
    registry=official[region]
    tn=key(title)
    sk=slugkey(slug)
    candidates=[]
    def add(typ,n,score):
        if n not in registry:return
        city,required_province=registry[n]
        if required_province!=province:return
        cslug=slugkey(city)
        if typ=="city_prefix":
            if not (tn.startswith("mercato settimanale di "+n)
                    and slug.startswith("mercato-settimanale-di-"+cslug)):
                return
        elif typ=="title_prefix":
            if not (slug.startswith(cslug+"-") and title.startswith(title.split(",",1)[0]+",")):
                return
        elif typ=="title_suffix":
            if not (cslug in sk and tn.endswith((" a "+n," di "+n," in "+n))):
                return
        candidates.append({"city":city,"province":required_province,
                           "method":typ,"score":score,"length":len(n)})
    # Derive potential first municipality from the malformed field, but
    # only when it matches the *beginning* of the source-bound weekly title.
    rawprefix=re.split(r",|\.\.\.| in provincia|\s+-\s*fraz|\s+\(",
                       origcity,flags=re.I)[0].strip(' "“”')
    add("city_prefix",key(rawprefix),30)
    # "Cernobbio, Mercatino ..." and "Frosinone, ..." titles.
    if "," in title:
        add("title_prefix",key(title.split(",",1)[0]),20)
    # Only bounded regions are scanned, and the official longest entire
    # municipality suffix wins (Piano di Sorrento, not Sorrento).
    for municipality in registry:
        if len(municipality)<5: continue
        if tn.endswith((" a "+municipality," di "+municipality,
                        " in "+municipality)):
            add("title_suffix",municipality,20)
    candidates.sort(key=lambda row:(-row["score"],-row["length"],row["city"]))
    # No city rewrite if two incomparable candidates have the same strength.
    if len(candidates)>1 and (
        candidates[0]["score"],candidates[0]["length"]
    ) == (
        candidates[1]["score"],candidates[1]["length"]
    ) and candidates[0]["city"]!=candidates[1]["city"]:
        return []
    return candidates[:4]


def reconcile(rows, official_reference, *, apply=False, former_reference=None):
    if not isinstance(rows,list) or not 1<=len(rows)<=100_000:
        raise ValueError("Unbounded market catalog")
    if apply is not True and apply is not False:
        raise ValueError("Explicit boolean apply mode required")
    official=trusted_municipalities(official_reference)
    seen=set(); result=[]; cases=[]; counts=Counter()
    for record in rows:
        if not isinstance(record,dict) or not isinstance(record.get("slug"),str):
            raise ValueError("Invalid market record")
        slug=record["slug"]
        if not slug or slug in seen:raise ValueError("Repeated or missing market identity")
        seen.add(slug)
        changed=dict(record)
        suspect=suspicious_city(record.get("citta"))
        original_bad_city=(record.get("citta_originale")
                           if record.get("citta_originale") else record.get("citta"))
        dangerous=source_city_cross_contamination(original_bad_city)
        proposals=municipality_proposals(record,official) if suspect else []
        preferred=proposals[0] if proposals else None
        # Never rewrite a human-verified, explicitly confirmed source.
        # Such collisions require a source review, not our normalization.
        if preferred and (record.get("verificato_il") or
                          record.get("date_quality") == "confermata"):
            preferred=None
            counts["protected_verified_municipalities"]+=1
        if suspect:
            counts["suspicious_before"]+=1
            if preferred:counts["city_candidates_istat_province_title"]+=1
            else:counts["needs_manual_municipality_review"]+=1
        if dangerous:
            counts["cross_market_scraper_text"]+=1
            if record.get("date"):
                counts["unsafe_future_calendar_candidates"]+=1
        if apply and preferred:
            old_city=str(record.get("citta") or "")
            changed["citta"]=preferred["city"]
            changed["citta_originale"]=(
                str(record.get("citta_originale") or old_city)[:160]
            )
            changed["localita_ricostruita_da"]="ISTAT comuni 2026-02-21; nome fonte e provincia"
            if changed["citta"]!=old_city:
                counts["city_fixed"]+=1
                # Scraper's concatenated weekly title falsely described
                # two markets as one. Display a bounded accurate generic
                # identity, not both cities concatenated.
                if dangerous and preferred["method"]=="city_prefix" and (
                        key(record.get("nome")).startswith(
                        "mercato settimanale di "+key(preferred["city"]))):
                    changed["nome_originale"]=str(record.get("nome") or "")[:160]
                    changed["nome"]="Mercato settimanale di "+preferred["city"]
                    counts["contaminated_market_titles_fixed"]+=1
        if apply and dangerous and (
                record.get("verificato_il") or
                record.get("date_quality") == "confermata"):
            counts["protected_verified_calendars"]+=1
        elif apply and dangerous:
            if record.get("date"):
                counts["forecast_days_quarantined"]+=len(record["date"])
                counts["records_calendar_quarantined"]+=1
            if changed.get("ricorrenza_testo")!=PROJECTION_WARNING:
                changed["ricorrenza_originale"]=str(
                    record.get("ricorrenza_originale") or
                    record.get("ricorrenza_testo") or "")[:180]
                changed["ricorrenza_testo"]=PROJECTION_WARNING
            changed["date"]=[]
            changed["date_quality"]="sconosciuta"
            changed["proiezione_regola"]=None
            changed["proiezione_fonte"]=""
            changed["proiezione_generata_il"]=""
            changed["calendario_sospeso_motivo"]="testo_sorgente_localita_concatenate"
        if suspect and len(cases)<MAX_SUGGESTIONS:
            cases.append({
                "slug":slug,
                "original_city":str(original_bad_city)[:160],
                "source":str(record.get("url_fonte") or "")[:500],
                "region":record.get("regione"),
                "province":record.get("provincia"),
                "method":preferred["method"] if preferred else None,
                "suggested_city":preferred["city"] if preferred else None,
                "calendar_cross_contaminated":dangerous,
                "future_dates_before":len(record.get("date") or []),
                "changed": changed!=record if apply else False,
            })
        result.append(changed)
    if (counts["city_candidates_istat_province_title"]>MAX_AUTOMATIC_FIXES
            or counts["unsafe_future_calendar_candidates"]>MAX_FORECAST_QUARANTINE):
        raise ValueError("Unexpected municipality anomaly growth; manual source review")
    fix_published_towns(rows, result, official, cases, counts, apply=apply,
                        former_reference=former_reference)
    result, province_report = reconcile_provinces(
        rows, result, official_reference, apply=apply)
    counts.update({
        "province_candidates": province_report["eligible"],
        "province_fixed": province_report["applied"],
        "province_pending": province_report["pending"],
        "province_protected": province_report["protected"],
    })
    report={
        "schema":1, "istat_reference":SOURCE_DATE,
        "source_file_sha256":ISTAT_SHA,
        "review_only":not apply,
        "records_total":len(rows),
        "ids_preserved":len(result)==len(rows),
        "market_confirmations_created":0,
        "verified_dates_created":0,
        "coordinates_changed":0,
        "publisher_sources_replaced":0,
        "counts":dict(sorted(counts.items())),
        "province_corrections":province_report,
        "examples":cases,
        "unresolved_examples":[case for case in cases
                               if not case["suggested_city"]][:35],
    }
    return result,report


def fix_published_towns(rows, result, official, cases, counts, *, apply, former_reference=None):
    """Show the official comune of a source town (S31), keeping the source's spelling.

    Bounded by the nightly budgets the guard enforces; the rest waits for later nights.
    """
    links = former_links(former_reference if former_reference is not None
                         else json.loads(FORMER_REFERENCE.read_text(encoding="utf-8")))
    current = {name for registry in official.values() for name in registry}
    former = {old: _today(old, links, current) for old in links}
    rome_markets = {re.sub(r"\s+[ivx]+$", "", key(row.get("nome")))
                    for row in rows if row.get("fonte") == ROME_INVENTORY_SOURCE}
    ours = set(PUBLISHED_TOWN_FIXES.values())
    proposals = []
    for index, row in enumerate(result):
        if row.get("localita_ricostruita_da") not in (None, "", *ours):
            continue
        found = published_town_proposal(row, official, former, rome_markets)
        if not found:
            continue
        if row.get("verificato_il") or row.get("date_quality") == "confermata":
            counts["published_town_protected"] += 1
            continue
        # Visible cards first; duplicates and concluded markets wait.
        hidden = bool(row.get("duplicato_di") or row.get("concluso"))
        proposals.append(((hidden, RULE_ORDER.index(found[0]), row["slug"]), index, *found))
    proposals.sort()
    touched = sum(before != after for before, after in zip(rows, result))
    budget = max(0, min(CITY_FIX_BUDGET - counts["city_fixed"], TOTAL_CHANGE_BUDGET - touched))
    selected = proposals[:budget] if apply else []
    counts["published_town_candidates"] = len(proposals)
    counts["published_town_pending"] = len(proposals) - len(selected)
    for _, index, rule, city in selected:
        row = dict(result[index])
        slug = row["slug"]
        old_city, old_name = str(row.get("citta") or ""), str(row.get("nome") or "")
        row["citta"] = city
        row["citta_originale"] = str(row.get("citta_originale") or old_city)[:160]
        row["localita_ricostruita_da"] = PUBLISHED_TOWN_FIXES[rule]
        if rule == "spelling" and key(old_name) in (
                "mercato settimanale di " + key(old_city), "mercato settimanale a " + key(old_city)):
            row["nome_originale"] = old_name[:160]
            row["nome"] = "Mercato settimanale di " + city
            counts["source_titles_respelled"] += 1
        result[index] = row
        counts["city_fixed"] += 1
        counts["published_town_" + rule] += 1
        cases.append({
            "slug": slug, "original_city": old_city[:160], "source": str(row.get("url_fonte") or "")[:500],
            "region": row.get("regione"), "province": row.get("provincia"), "method": rule,
            "label": row["localita_ricostruita_da"], "suggested_city": city,
            "calendar_cross_contaminated": False,
            "future_dates_before": len(row.get("date") or []), "changed": True,
        })


def markdown(report):
    counts=report["counts"]
    text=[
        "# Comune ISTAT — riconciliazione conservativa",
        "",
        "Fonte: "+SOURCE_URL,
        "File originale ISTAT aggiornato al 21 febbraio 2026, licenza CC BY 4.0.",
        "Questo controllo non dimostra che un mercato sia aperto.",
        "",
        f"- Record analizzati: {report['records_total']}",
        f"- Località già sospette: {counts.get('suspicious_before',0)}",
        f"- Proposte supportate da Comune/provincia ISTAT e titolo: {counts.get('city_candidates_istat_province_title',0)}",
        f"- Da verificare manualmente: {counts.get('needs_manual_municipality_review',0)}",
        f"- Calendari potenzialmente confusi fra mercati diversi: {counts.get('unsafe_future_calendar_candidates',0)}",
        f"- Comuni corretti in DEV: {counts.get('city_fixed',0)}",
        f"- Località della fonte ricondotte al comune ISTAT (S31): {counts.get('published_town_candidates',0)}, "
        f"in attesa entro il tetto notturno: {counts.get('published_town_pending',0)}",
        f"- Record con date previste sospese: {counts.get('records_calendar_quarantined',0)}",
        f"- Province riconciliate con Comune e regione ISTAT: {counts.get('province_fixed',0)}",
        f"- Province in attesa del prossimo ciclo entro il tetto complessivo di 80 modifiche: {counts.get('province_pending',0)}",
        f"- Conflitti di provincia protetti da prove/verifiche preesistenti: {counts.get('province_protected',0)}",
        "",
        "Nessun ID, fonte principale, coordinata o verifica umana viene cambiato.",
        "La provincia amministrativa non convalida la pagina fonte né l'apertura del mercato.",
        "Le date sospese richiedono nuova prova della fonte, non un altro giorno indovinato.",
        "",
        "## Casi da rivedere", "",
    ]
    for item in report["unresolved_examples"][:20]:
        text.append("- "+item["region"]+" · "+item["original_city"]+" · "+item["slug"])
    return "\n".join(text)+"\n"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--manifest",type=Path,required=True)
    p.add_argument("--reference",type=Path,default=Path("backend/data/istat-comuni-2026.json"))
    p.add_argument("--out",type=Path,required=True)
    p.add_argument("--report",type=Path,required=True)
    p.add_argument("--updated",type=Path)
    p.add_argument("--apply",action="store_true")
    args=p.parse_args()
    if args.apply and not args.updated:
        raise ValueError("Apply mode requires explicit temporary output file")
    old=load_existing(args.manifest)
    source=json.loads(args.reference.read_text(encoding="utf-8"))
    after,summary=reconcile(old,source,apply=args.apply)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(summary,ensure_ascii=False,indent=2)+"\n",encoding="utf-8")
    args.report.write_text(markdown(summary),encoding="utf-8")
    if args.updated:
        args.updated.parent.mkdir(parents=True,exist_ok=True)
        args.updated.write_text(json.dumps(after,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(summary["counts"],ensure_ascii=False))


if __name__=="__main__":
    main()
