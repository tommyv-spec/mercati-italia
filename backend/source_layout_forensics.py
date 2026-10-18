#!/usr/bin/env python3
"""Explain where an already-published market lost source fields (offline audit).

This is deliberately NOT a network scraper. The publisher's HTML is supplied
manually as an ephemeral sample, studied once for each versioned page layout.
Only field-presence, counts, calendar risk, and the matching market's slug
leave the process: no copied HTML, editorial text, personal data, or events.

Happings' Oct 2025 terms explicitly forbid automated collection without
written permission. Its provincial tables can be studied but must not become
a bulk data feed. EventiESagre and Cose di Casa likewise need rights review.
Official licensed adapters are handled separately by the guarded Autopilot.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

from recurrence_refresh import explicit_rule

MAX_HTML_BYTES=2_600_000
DAYS=("lunedi","martedi","mercoledi","giovedi","venerdi","sabato","domenica")
SOURCE_TYPES={
    "happings_weekly_index":("www.happings.com","publisher_automation_permission_required"),
    "cosedicasa_edition":("www.cosedicasa.com","editorial_content_reuse_not_approved"),
    "eventiesagre_edition":("www.eventiesagre.it","editorial_content_reuse_not_approved"),
}
HOURLY=re.compile(
    r"\b(?:dalle?\s+(?:ore\s+)?|ore\s+|orari?\s*(?:del\s+mercato|estivo|invernale)?\s*:?\s*(?:dalle?\s+)?)"
    r"(?:[01]?\d|2[0-4])(?::[0-5]\d)?\s*(?:alle?|fino\s+alle|[-–])\s*"
    r"(?:[01]?\d|2[0-4])(?::[0-5]\d)?\b",re.I,
)
DAY_RE=re.compile(r"\b(?:lunedi|martedi|mercoledi|giovedi|venerdi|sabato|domenica)\b")
MARKET_LIST=re.compile(r"^\s*a\s+([^,]{1,120}),\s*in\s+(.{3,240}?)\s*$",re.I)
ARCHIVED_MARKER=re.compile(r"\bEvento\s+Passato\b",re.I)
PAST_DATE=re.compile(r"\b(?:Dal|Al):\s*(\d{2}/\d{2}/\d{4})\b",re.I)
STRUCTURED_CLASSES={
    "mercatini-mostre-address":"indirizzo",
    "mercatini-mostre-suspension":"sospensioni",
    "mercatini-mostre-contacts":"contatti",
    "mercatini-mostre-website":"sito_organizzatore",
    "mercatini-mostre-performer":"organizzatore",
    "mercatini-mostre-phone":"telefono",
    "mercatini-mostre-date-big":"date_esplicite",
}


def text_key(value):
    raw=unicodedata.normalize("NFKD",str(value or ""))
    return re.sub(r"\s+"," ",re.sub(
        r"[^a-z0-9]+"," ","".join(ch for ch in raw if not unicodedata.combining(ch)).lower()
    )).strip()


def _weekday(text):
    found=[DAYS.index(d) for d in dict.fromkeys(DAY_RE.findall(text_key(text)))]
    return found[0] if len(found)==1 else None


def _safe_source_type(kind,url):
    if kind not in SOURCE_TYPES:
        raise ValueError("Unknown or unapproved publisher source layout")
    host=urlsplit(url)
    if (host.scheme!="https" or host.hostname!=SOURCE_TYPES[kind][0]
        or host.username or host.password or host.port not in (None,443)):
        raise ValueError("Publisher sample URL does not match its reviewed layout")


class SourceSignals(HTMLParser):
    """Extracts ephemeral label signals, never publisher text in the report."""
    def __init__(self,kind):
        super().__init__(convert_charrefs=True)
        self.kind=kind
        self.stack=[]
        self.visible=[]
        self.site_day=None
        self.site_rows=[]
        self.field_flags=set()
        self.explicit_dates=0
        self.publisher_modified=False
        self.jsonld=False
        self.skip=0

    def handle_starttag(self,tag,attrs):
        attrs=dict(attrs)
        classes=set(str(attrs.get("class") or "").split())
        if tag in ("script","style","noscript"):
            self.skip+=1
        if tag=="script" and attrs.get("type")=="application/ld+json":
            self.jsonld=True
        if tag=="meta" and attrs.get("property")=="article:modified_time":
            self.publisher_modified=bool(attrs.get("content"))
        tracked=(
            tag in ("h3","li","time","strong")
            or bool(classes.intersection(STRUCTURED_CLASSES))
        )
        node={"tag":tag,"classes":classes,"buffer":[] if tracked else None}
        self.stack.append(node)
        if tag=="time" and any("mercatini-mostre-date-big" in v["classes"] for v in self.stack):
            self.explicit_dates+=1

    def handle_endtag(self,tag):
        pos=next((i for i in range(len(self.stack)-1,-1,-1)
                  if self.stack[i]["tag"]==tag),None)
        if pos is None:
            return
        while len(self.stack)>pos:
            node=self.stack.pop()
            value=" ".join(node["buffer"] or []).strip()
            if value:
                if ("mercatini-mostre" in " ".join(node["classes"])):
                    for cls,field in STRUCTURED_CLASSES.items():
                        if cls in node["classes"]:
                            self.field_flags.add(field)
                if (node["tag"]=="h3" and self.kind=="happings_weekly_index"
                    and self._in_happings()):
                    day=_weekday(value)
                    if day is not None and "mercati del" in text_key(value):
                        self.site_day=day
                if (node["tag"]=="li" and self.kind=="happings_weekly_index"
                    and self.site_day is not None and self._in_happings()):
                    match=MARKET_LIST.match(value)
                    if match:
                        city,addr=match.groups()
                        self.site_rows.append({
                            "city":text_key(city),"day":self.site_day,
                            "has_venue":bool(addr.strip()),
                            "morning_only":"mattina" in text_key(addr),
                        })
            if node["tag"] in ("script","style","noscript") and self.skip:
                self.skip-=1

    def _in_happings(self):
        return any("happings-seo-content" in x["classes"] for x in self.stack)

    def handle_data(self,data):
        if self.skip: return
        raw=" ".join(data.split())
        if not raw:return
        if len(self.visible)<8000:
            self.visible.append(raw[:350])
        for node in self.stack:
            if node["buffer"] is not None and len(node["buffer"])<35:
                node["buffer"].append(raw[:350])

    def finish(self):
        # These are local in-memory text fragments, not persisted copyrighted
        # publisher descriptions or contacts.
        return " ".join(self.visible)


def inspect(html_blob,*,source_type,url,market=None,today=None):
    today=today or date.today()
    _safe_source_type(source_type,url)
    if (not isinstance(html_blob,bytes)
        or not 200<=len(html_blob)<=MAX_HTML_BYTES
        or not isinstance(today,date)):
        raise ValueError("Missing or unbounded publisher HTML example")
    parser=SourceSignals(source_type)
    parser.feed(html_blob.decode("utf-8-sig",errors="replace"))
    parser.close()
    all_text=parser.finish()
    original={v:False for v in (
        "indirizzo","giorno","orario_preciso","fascia_giornaliera",
        "date_esplicite","ricorrenza","sospensioni",
        "organizzatore","telefono","contatti","sito_organizzatore",
        "aggiornamento_publisher","edizione_archiviata",
    )}
    match_type="not_compared"
    venue_matches=0
    if source_type=="happings_weekly_index":
        original["giorno"]=bool(parser.site_rows)
        original["indirizzo"]=any(x["has_venue"] for x in parser.site_rows)
        original["fascia_giornaliera"]=any(x["morning_only"] for x in parser.site_rows)
        original["aggiornamento_publisher"]=parser.publisher_modified
        if isinstance(market,dict):
            city=text_key(market.get("citta"))
            rule=explicit_rule(market.get("ricorrenza_testo"))
            weekday=rule["weekdays"][0] if rule and rule.get("kind")=="weekly" and len(rule["weekdays"])==1 else None
            selected=[x for x in parser.site_rows if x["city"]==city and x["day"]==weekday]
            venue_matches=len(selected)
            if len(selected)==1:
                original["indirizzo"]=selected[0]["has_venue"]
                original["fascia_giornaliera"]=selected[0]["morning_only"]
                match_type="same_city_single_day_source_row"
            elif len(selected)>1:
                match_type="ambiguous_source_venues_same_city_day"
                original["indirizzo"]=False
            else:
                match_type="source_row_not_found"
    elif source_type=="cosedicasa_edition":
        original["indirizzo"]="indirizzo" in parser.field_flags
        original["date_esplicite"]=parser.explicit_dates>=2
        original["ricorrenza"]=bool(re.search(r"\b(?:mensile|ogni|primo|prima|secondi|terzi)\b",text_key(all_text)))
        original["sospensioni"]="sospensioni" in parser.field_flags
        for field in ("organizzatore","telefono","contatti","sito_organizzatore"):
            original[field]=field in parser.field_flags
        original["aggiornamento_publisher"]=parser.publisher_modified
        original["orario_preciso"]=bool(HOURLY.search(all_text))
    else:
        original["indirizzo"]=bool(re.search(r"\bDove\s+fanno\s+il\s+mercato\b|\bPiazza\s+Del\s+Popolo\b",all_text,re.I))
        original["giorno"]=bool(DAY_RE.search(text_key(all_text)))
        original["ricorrenza"]=bool(re.search(r"\bquando\s+si\s+svolge\b",text_key(all_text)))
        original["orario_preciso"]=bool(HOURLY.search(all_text))
        original["date_esplicite"]=len(PAST_DATE.findall(all_text))>=1
        original["edizione_archiviata"]=bool(ARCHIVED_MARKER.search(all_text))
        original["aggiornamento_publisher"]=bool(re.search("data ultimo aggiornamento pagina",text_key(all_text)))
    output={
        "schema":1,"source_family":source_type,
        "source_url":url,
        "rights_status":SOURCE_TYPES[source_type][1],
        "sample_hash":hashlib.sha256(html_blob).hexdigest(),
        "sample_bytes":len(html_blob),
        "source_field_presence":original,
        "source_rows_detected":len(parser.site_rows),
        "individual_venue_matches":venue_matches,
        "source_row_match":match_type,
        "source_date_elements":parser.explicit_dates,
        "source_html_saved":False,
        "source_body_saved":False,
        "publisher_contacts_saved":False,
        "source_market_data_imported":False,
        "market_openings_verified":False,
        "catalog_records_changed":0,
        "source_automation_granted_by_audit":False,
    }
    if market is not None:
        if not isinstance(market,dict) or not market.get("slug") or market.get("url_fonte")!=url:
            raise ValueError("Market provenance does not match the original publisher URL")
        catalog={
            "indirizzo":bool(str(market.get("indirizzo") or "").strip()),
            "giorno":bool(str(market.get("ricorrenza_testo") or "").strip()),
            "orario_preciso":bool(str(market.get("orario_testo") or "").strip()),
            "date_esplicite":bool(market.get("date")),
            "ricorrenza":bool(str(market.get("ricorrenza_testo") or "").strip()),
            "sospensioni":bool(market.get("stagionalita_fonte")),
            "organizzatore":bool("Org:" in str(market.get("descrizione") or "")),
            "aggiornamento_publisher":False,  # importer date is NOT publisher date
        }
        omissions=[
            field for field in catalog
            if original.get(field) and not catalog[field]
            and (source_type!="happings_weekly_index" or
                 match_type=="same_city_single_day_source_row")
        ]
        output["market_id"]=market["slug"]
        output["catalog_field_presence"]=catalog
        output["source_present_catalog_missing"]=sorted(omissions)
        output["archived_source_has_future_predictions"]=bool(
            original["edizione_archiviata"] and market.get("date"))
        output["catalogue_fields_corrected_by_this_audit"]=0
    return output


def validate(result):
    if (not isinstance(result,dict) or result.get("schema")!=1
        or result.get("source_html_saved") is not False
        or result.get("publisher_contacts_saved") is not False
        or result.get("source_market_data_imported") is not False
        or result.get("market_openings_verified") is not False
        or result.get("source_automation_granted_by_audit") is not False
        or result.get("catalog_records_changed")!=0):
        raise ValueError("Source-layout audit attempted to save protected material or confirm openings")
    return True


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--source-type",required=True,choices=sorted(SOURCE_TYPES))
    p.add_argument("--url",required=True)
    p.add_argument("--html",required=True,type=Path,help="Manually reviewed ephemeral publisher source HTML")
    p.add_argument("--market-record",type=Path)
    p.add_argument("--out",required=True,type=Path)
    args=p.parse_args()
    market=json.loads(args.market_record.read_text("utf-8")) if args.market_record else None
    report=inspect(args.html.read_bytes(),source_type=args.source_type,
                   url=args.url,market=market)
    validate(report)
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n","utf-8")
    print(json.dumps({
        "source":args.source_type,"fields_visible":sum(report["source_field_presence"].values()),
        "lost_in_saved_market":report.get("source_present_catalog_missing",[]),
        "events_confirmed":0,"catalog_edits":0,
    },ensure_ascii=False))

if __name__=="__main__":
    main()
