#!/usr/bin/env python3
"""Small, consent-aware template health probes for largest legacy publishers.

Read 2 Happings page formats and 1 Cose di Casa editorial example, each
exact allowlisted URL, and compare generic *schema signals*, not copyrighted
text. Never persist markup, event names, contacts, times, locations or dates.
This is NOT an importer and cannot authorize copied data.
"""
from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import re
import socket
import unicodedata
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener
from urllib.robotparser import RobotFileParser

MAX_BYTES=2_500_000
MAX_ROBOTS=45_000
MAX_TEMPLATES=3
USER_AGENT="MercatiItaliaPublisherSchemaAudit/1.0 (+https://github.com/tommyv-spec/mercati-italia)"
TEMPLATES=(
    {"id":"happings-weekly-area",
     "publisher":"happings.com",
     "url":"https://www.happings.com/it/mercati-settimanali-a-milano-e-provincia/",
     "robots":"https://www.happings.com/robots.txt",
     "type":"weekly_area_index",
     "required":["single_market_h1","weekday_section_headings","weekly_venue_list_entries"]},
    {"id":"happings-event-detail",
     "publisher":"happings.com",
     "url":"https://www.happings.com/it/happing/mercato-del-venerdi-mattina-a-lana/",
     "robots":"https://www.happings.com/robots.txt",
     "type":"event_detail_calendar",
     "required":["single_market_h1","detail_calendar_heading","detail_information_heading"]},
    {"id":"cosedicasa-monthly",
     "publisher":"cosedicasa.com",
     "url":"https://www.cosedicasa.com/mercatini/bologna-piazza-s-stefano",
     "robots":"https://www.cosedicasa.com/robots.txt",
     "type":"monthly_editorial_exception",
     "required":["single_market_h1","editorial_location_label","editorial_organizer_label"]},
)
ENDPOINTS={x["url"] for x in TEMPLATES}|{x["robots"] for x in TEMPLATES}
NAMES=("lunedi","martedi","mercoledi","giovedi","venerdi","sabato","domenica")


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self,request,fp,code,msg,headers,newurl):
        return None


def safe_url(url):
    if url not in ENDPOINTS:
        return False
    try:
        p=urlsplit(url)
        return (p.scheme=="https" and p.hostname in
                ("www.happings.com","www.cosedicasa.com")
                and not p.username and not p.password
                and p.port in (None,443) and not p.fragment and not p.query)
    except ValueError:
        return False


def protected_fetch(url):
    if not safe_url(url):
        raise ValueError("Unreviewed publisher URL")
    p=urlsplit(url)
    for answer in socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(answer[4][0]).is_global:
            raise ValueError("Private DNS address blocked")
    req=Request(url,headers={"User-Agent":USER_AGENT,
                             "Accept":"text/plain" if url.endswith("robots.txt") else "text/html",
                             "Accept-Encoding":"identity"})
    with build_opener(NoRedirect).open(req,timeout=12) as response:
        mime=response.headers.get("Content-Type","").lower()
        if ("text/plain" not in mime if url.endswith("robots.txt")
                else "text/html" not in mime and "application/xhtml" not in mime):
            raise ValueError("publisher_response_mime_changed")
        limit=MAX_ROBOTS if url.endswith("robots.txt") else MAX_BYTES
        payload=response.read(limit+1)
        if len(payload)>limit:
            raise ValueError("publisher_response_exceeds_bounded_limit")
        return payload


def robots_allowed(blob,url):
    if not safe_url(url) or not blob or len(blob)>MAX_ROBOTS:
        raise ValueError("Robots policy is unavailable or untrusted")
    text=blob.decode("utf-8-sig",errors="replace")
    if "user-agent:" not in text.casefold():
        raise ValueError("Robots policy contains no user agents")
    robots=RobotFileParser()
    robots.parse(text.splitlines())
    return robots.can_fetch(USER_AGENT,url)


class TemplateParser(HTMLParser):
    """Discovers expected structure in memory, without storing source text."""
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.active=[]
        self.counters={"h1":0,"h2":0,"h3":0,"li":0,"body_characters_examined":0}
        self.bits=set()
        self.rolling=""
        self.markets_index_items=0
        self.index_day_headings=0
        self.calendar_items=0
        self._inside_ignored=0

    def handle_starttag(self,tag,attrs):
        if tag in {"script","style","noscript"}:
            self._inside_ignored+=1
        self.active.append(tag)
        if tag in self.counters:self.counters[tag]+=1
        if self.counters.get("body_characters_examined",0)>MAX_BYTES:
            raise ValueError("Unbounded publisher template body")

    def handle_endtag(self,tag):
        if tag in {"script","style","noscript"} and self._inside_ignored:
            self._inside_ignored-=1
        if tag in self.active:
            # Only tracked nesting is needed; malformed pages are still
            # admissible as layout observation, not trusted for reimport.
            self.active=self.active[:len(self.active)-1-self.active[::-1].index(tag)]

    def handle_data(self,data):
        if self._inside_ignored:
            return
        text=" ".join(str(data).split())
        self.counters["body_characters_examined"]+=len(text)
        if self.counters["body_characters_examined"]>MAX_BYTES:
            raise ValueError("Publisher page exceeded bounded text volume")
        if not text:
            return
        here=self.active[-1] if self.active else ""
        lowered="".join(ch for ch in unicodedata.normalize("NFKD", text)
                        if not unicodedata.combining(ch)).casefold()
        if here=="h1" and ("mercat" in lowered or "antiquariato" in lowered):
            self.bits.add("market_h1_seen")
        if here in ("h2","h3"):
            if "tutte le date" in lowered:
                self.bits.add("detail_calendar_heading")
            if "informazioni utili" in lowered:
                self.bits.add("detail_information_heading")
            if here=="h3" and "mercati del" in lowered and any(x in lowered for x in NAMES):
                self.index_day_headings+=1
        if here=="li":
            if lowered.startswith("a ") and ", in " in lowered:
                self.markets_index_items+=1
            if re.search(r"\b20(?:25|26|27)\b",lowered) and re.search(r"\d{1,2}\s+\S+",lowered):
                self.calendar_items+=1
        self.rolling=(self.rolling+" "+lowered)[-600:]
        if "luogo:" in self.rolling:
            self.bits.add("editorial_location_label")
        if "organizzatore:" in self.rolling:
            self.bits.add("editorial_organizer_label")
        if "sospensioni:" in self.rolling:
            self.bits.add("editorial_suspensions_warning")
        if "prossime date:" in self.rolling or "prossima data:" in self.rolling:
            self.bits.add("editorial_next_dates_label")


def inspect(html_blob,template):
    if (not isinstance(html_blob,bytes) or
            not 200<=len(html_blob)<=MAX_BYTES or
            template.get("id") not in {x["id"] for x in TEMPLATES}):
        raise ValueError("Invalid or unexpected publisher example")
    parser=TemplateParser()
    parser.feed(html_blob.decode("utf-8-sig",errors="replace"))
    parser.close()
    markers=set(parser.bits)
    if parser.counters["h1"]==1 and "market_h1_seen" in markers:
        markers.add("single_market_h1")
    if parser.index_day_headings>=2:
        markers.add("weekday_section_headings")
    if parser.markets_index_items>=8:
        markers.add("weekly_venue_list_entries")
    observed=sorted(markers)
    expected=set(template["required"])
    return {
        "template_id":template["id"],
        "publisher":template["publisher"],
        "source_format":template["type"],
        "observed_markers":observed,
        "missing_required_markers":sorted(expected-markers),
        "document_structure_counts":{
            "h1":parser.counters["h1"],
            "weekday_group_headings":parser.index_day_headings,
            "weekly_list_entries_not_individual_verified_markets":parser.markets_index_items,
            "calendar_list_entries_not_confirmed":parser.calendar_items,
            "editorial_suspensions_warning_present":"editorial_suspensions_warning" in markers,
        },
        "page_sha256_for_change_alert_only":hashlib.sha256(html_blob).hexdigest(),
        "layout_valid_for_template_comparison":not bool(expected-markers),
        "publisher_text_persisted":False,
        "individual_markets_verified":0,
        "importable_market_rows":0,
    }


def survey(*,fetch=protected_fetch,offline=False,today=None,previous=None):
    today=today or date.today()
    if not isinstance(today,date):
        raise ValueError("Invalid source audit date")
    if previous is not None and (
        not isinstance(previous,dict) or previous.get("schema")!=1
        or previous.get("research_only") is not True
        or previous.get("market_imports")!=0
        or previous.get("event_confirmations")!=0):
        raise ValueError("Untrusted prior source template report")
    prior={x["template_id"]:x for x in (previous or {}).get("templates",[])
           if isinstance(x,dict) and isinstance(x.get("template_id"),str)}
    robot_cache={}
    result=[]
    for t in TEMPLATES[:MAX_TEMPLATES]:
        row={
            "template_id":t["id"],"publisher":t["publisher"],
            "sample_url":t["url"],"type":t["type"],
            "state":"offline_skipped" if offline else "not_checked",
            "requests":0,"source_openings_confirmed":0,
            "publisher_text_persisted":False,"market_catalog_updates":0,
        }
        if not offline:
            try:
                if t["robots"] not in robot_cache:
                    robot_cache[t["robots"]]=fetch(t["robots"])
                    row["requests"]+=1
                if not robots_allowed(robot_cache[t["robots"]],t["url"]):
                    row["state"]="robots_denied"
                else:
                    page=fetch(t["url"])
                    row["requests"]+=1
                    signals=inspect(page,t)
                    row.update(signals)
                    row["state"]=("schema_unchanged_or_sufficient"
                                  if signals["layout_valid_for_template_comparison"]
                                  else "schema_changed_review_required")
                    previous_markers=prior.get(t["id"],{}).get("observed_markers")
                    if previous_markers is not None:
                        row["field_markers_changed_since_previous"]=(
                            sorted(previous_markers)!=signals["observed_markers"])
                    else:
                        row["field_markers_changed_since_previous"]=None
            except (OSError,UnicodeError,ValueError,TimeoutError) as exc:
                row["state"]="unavailable_or_format_review"
                row["reason_type"]=type(exc).__name__
                row["reason_code"]=str(exc) if isinstance(exc, ValueError) and str(exc) in (
                    "publisher_response_mime_changed",
                    "publisher_response_exceeds_bounded_limit",
                    "Unreviewed publisher URL",
                    "Private DNS address blocked",
                ) else "transport_or_markup_review"
        result.append(row)
    return {
        "schema":1,"reference_date":today.isoformat(),
        "research_only":True,"templates":result,
        "template_count":len(result),
        "publishers_checked":len(set(x["publisher"] for x in result)),
        "max_pages_per_publisher":2,"pages_with_full_text_copied":0,
        "robots_policies_enforced":True,
        "market_imports":0,"event_confirmations":0,
        "catalog_updates":0,"source_data_copied":False,
    }


def validate(report):
    if (not isinstance(report,dict) or report.get("schema")!=1
        or report.get("research_only") is not True
        or report.get("robots_policies_enforced") is not True
        or report.get("source_data_copied") is not False
        or report.get("template_count")!=len(TEMPLATES)
        or {x.get("template_id") for x in report.get("templates",[])}
              !={t["id"] for t in TEMPLATES}
        or any(report.get(k)!=0 for k in (
            "pages_with_full_text_copied","market_imports",
            "event_confirmations","catalog_updates"))
        or any(x.get("publisher_text_persisted") is not False
               or x.get("market_catalog_updates")!=0
               or x.get("source_openings_confirmed")!=0
               for x in report["templates"])):
        raise ValueError("Template health check cannot authorize reuse or event confirmation")
    return True


def markdown(report):
    out=[
        "# Verifica dei layout degli editori principali — sola lettura",
        "",
        "Happings: indice settimanale per provincia e scheda evento sono due",
        "strutture diverse. Cose di Casa: calendario mensile ed eccezioni.",
        "Una pagina raggiungibile NON conferma apertura, indirizzo o date.",
        "",
        "| Template | Stato | Marcatori mancanti | Richieste |",
        "|---|---|---|---:|",
    ]
    for x in report["templates"]:
        out.append("| "+x["template_id"]+" | "+x["state"]+
                   " | "+", ".join(x.get("missing_required_markers",[]))+
                   " | "+str(x["requests"])+" |")
    out.extend(["","Nessun testo originale, evento, contatto o data viene registrato.",
                "Per nuove fonti: prima conferma dei diritti di riuso e dello",
                "schema. Eventuali variazioni del markup vanno in quarantena.",""])
    return "\n".join(out)+"\n"


def main():
    p=argparse.ArgumentParser()
    p.add_argument("--out",required=True,type=Path)
    p.add_argument("--report",required=True,type=Path)
    p.add_argument("--previous",type=Path)
    p.add_argument("--offline",action="store_true")
    p.add_argument("--today",type=date.fromisoformat,default=date.today())
    a=p.parse_args()
    old=json.loads(a.previous.read_text("utf-8")) if a.previous and a.previous.is_file() else None
    result=survey(offline=a.offline,today=a.today,previous=old)
    validate(result)
    for x in (a.out,a.report):x.parent.mkdir(parents=True,exist_ok=True)
    a.out.write_text(json.dumps(result,indent=2,ensure_ascii=False,sort_keys=True)+"\n","utf-8")
    a.report.write_text(markdown(result),"utf-8")
    print(json.dumps({
        "templates_checked":len(result["templates"]),
        "healthy_layouts":sum(x["state"]=="schema_unchanged_or_sufficient"
                              for x in result["templates"]),
        "publishers":result["publishers_checked"],
        "market_imports":0,"events_confirmed":0,
    }))
if __name__=="__main__":
    main()
