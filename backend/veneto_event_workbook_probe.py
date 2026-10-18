#!/usr/bin/env python3
"""Bounded, read-only structural audit of Regione Veneto 2026 sagre/fiere XLSX.

A publisher event row is NOT a verified opening or a permanent market.
Only workbook schema, sheet counts and content fingerprint can be written
to the report: no names of organizers, events, phone numbers or raw rows.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import ipaddress
import json
import re
import socket
import xml.etree.ElementTree as ET
import zipfile
from collections import Counter
from datetime import date
from pathlib import Path
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

SOURCE = ("https://elezioni2020.regione.veneto.it/documents/10713/13530434/"
          "Calendario%2BSagre%2Be%2BFiere%2B08.10.2026.xlsx/"
          "ebd944f5-d5ec-4826-bbc4-faa0a6edce98")
LANDING = ("https://elezioni2020.regione.veneto.it/web/attivita-produttive/"
           "somministrazione-alimenti-e-bevande-nelle-sagre-e-nelle-fiere")
MAX_BYTES = 1_600_000
MAX_TOTAL_UNCOMPRESSED = 18_000_000
MAX_SINGLE_XML = 6_000_000
MAX_SHEETS = 12
MAX_ROWS = 25_000
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
SHEET_RE = re.compile(r"xl/worksheets/sheet[0-9]{1,2}\.xml$")
ALIAS = {
    "event": ("manifestazione", "denominazione", "evento", "sagra", "fiera", "titolo"),
    "municipality": ("comune", "municipio", "localita", "citta"),
    "province": ("provincia", "prov", "sigla provincia"),
    "location": ("luogo", "localizzazione", "indirizzo", "via", "piazza", "sede"),
    "start_date": ("inizio", "dal", "data inizio", "data di inizio"),
    "end_date": ("fine", "al", "data fine", "data di fine"),
    "organizer": ("organizzatore", "pro loco", "associazione"),
}
USER_AGENT="MercatiItaliaWorkbookSchemaAudit/1.0 (+https://github.com/tommyv-spec/mercati-italia)"

class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None

def _xml(data):
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("Untrusted XLSX XML has external entity declarations")
    return ET.fromstring(data)

def guarded_download(url=SOURCE):
    if url != SOURCE:
        raise ValueError("Unreviewed publisher XLSX URL")
    p=urlsplit(url)
    if p.scheme!="https" or p.hostname!="elezioni2020.regione.veneto.it":
        raise ValueError("Unexpected official publisher host")
    for entry in socket.getaddrinfo(p.hostname,443,type=socket.SOCK_STREAM):
        if not ipaddress.ip_address(entry[4][0]).is_global:
            raise ValueError("Untrusted XLSX host resolved to private network")
    req=Request(url,headers={"User-Agent":USER_AGENT,
                             "Accept":"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                             "Accept-Encoding":"identity"})
    with build_opener(NoRedirect).open(req,timeout=20) as response:
        blob=response.read(MAX_BYTES+1)
    if not 500<=len(blob)<=MAX_BYTES:
        raise ValueError("Missing or unbounded publisher XLSX")
    return blob

def _col_number(ref):
    letters=re.match(r"[A-Z]+",str(ref or "").upper())
    if not letters:
        return None
    value=0
    for ch in letters.group(0):
        value=value*26+(ord(ch)-64)
    return value if 1<=value<=150 else None

def _shared(z):
    if "xl/sharedStrings.xml" not in z.namelist():
        return []
    data=z.read("xl/sharedStrings.xml")
    if len(data)>MAX_SINGLE_XML:
        raise ValueError("XLSX shared strings exceed safe size")
    root=_xml(data)
    strings=[]
    for node in root.findall(NS+"si"):
        if len(strings)>=100_000:
            raise ValueError("Unbounded workbook string table")
        strings.append("".join(t.text or "" for t in node.iter(NS+"t"))[:400])
    return strings

def _cell(cell,shared):
    typ=cell.attrib.get("t")
    if typ=="inlineStr":
        node=cell.find(NS+"is")
        return "".join(n.text or "" for n in node.iter(NS+"t"))[:400] if node is not None else ""
    v=cell.find(NS+"v")
    raw=v.text if v is not None and v.text is not None else ""
    if typ=="s":
        try: return shared[int(raw)]
        except (IndexError,ValueError,TypeError): raise ValueError("Bad workbook shared-string index")
    return str(raw)[:400]

def _meaning(token):
    fold=" ".join(re.sub(r"[^a-z0-9]+"," ",str(token or "").casefold()).split())
    return sorted(k for k,aliases in ALIAS.items() if any(
        fold==alias or (len(alias)>=5 and fold.startswith(alias+" "))
        for alias in aliases
    ))

def analyze(blob,*,today=None):
    today=today or date.today()
    if not isinstance(today,date) or not isinstance(blob,bytes) or not 500<=len(blob)<=MAX_BYTES:
        raise ValueError("Missing official Excel source or unsafe response bounds")
    if not zipfile.is_zipfile(io.BytesIO(blob)):
        raise ValueError("Publisher did not return an XLSX ZIP")
    with zipfile.ZipFile(io.BytesIO(blob)) as z:
        infos=z.infolist()
        if len(infos)>500 or sum(x.file_size for x in infos)>MAX_TOTAL_UNCOMPRESSED:
            raise ValueError("XLSX archive decompression limit exceeded")
        invalid = []
        for entry in infos:
            name = entry.filename
            # Ordinary Excel print layout may include an opaque
            # printerSettings*.bin. We never read these settings. Keep
            # blocking macros, OLE embeddings and all OTHER binary files.
            is_inert_printer_settings = bool(re.fullmatch(
                r"xl/printerSettings/printerSettings[0-9]{1,3}\.bin", name))
            reason = (
                "unsafe_path" if name.startswith("/") or ".." in name.split("/")
                else "external_reference" if "externalLinks/" in name
                else "macro_or_embedded_binary"
                if ("vbaProject.bin" in name or "embeddings/" in name or
                    "activeX/" in name or
                    (name.endswith(".bin") and not is_inert_printer_settings))
                else "oversize_xml_member" if entry.file_size > MAX_SINGLE_XML
                else None
            )
            if reason:
                invalid.append({"path":name[:95],
                                "bytes":entry.file_size,
                                "reason":reason})
        if invalid:
            # Structural metadata only. Never log any event/organizer rows.
            raise ValueError("Publisher XLSX needs structural review: " +
                             json.dumps(invalid[:4], sort_keys=True))
        worksheets=sorted((x.filename for x in infos if SHEET_RE.fullmatch(x.filename)))
        if not 1<=len(worksheets)<=MAX_SHEETS:
            raise ValueError("Missing or excessive XLSX worksheets")
        shared=_shared(z)
        summaries=[]
        for fname in worksheets:
            data=z.read(fname)
            if len(data)>MAX_SINGLE_XML:
                raise ValueError("XLSX sheet exceeds bounded XML size")
            root=_xml(data)
            sheet_data=root.find(".//"+NS+"sheetData")
            if sheet_data is None:
                raise ValueError("Workbook has no sheet data")
            rows=sheet_data.findall(NS+"row")
            if len(rows)>MAX_ROWS:
                raise ValueError("Unbounded official worksheet")
            candidates=[]
            numeric=0
            for n,row in enumerate(rows):
                if n<22:
                    cols={}
                    for c in row.findall(NS+"c"):
                        idx=_col_number(c.attrib.get("r",""))
                        if idx:
                            cols[idx]=_cell(c,shared)
                    if cols:
                        header=[v for _,v in sorted(cols.items())]
                        concepts=sorted({concept for value in header for concept in _meaning(value)})
                        candidates.append((len(concepts),len(header),n,header,concepts,int(row.attrib.get("r",n+1)),cols))
                # Structural count only; no raw row contents stored.
                if row.findall(NS+"c"):
                    numeric+=1
            best=sorted(candidates,key=lambda x:(-x[0],-x[1],x[2]))[0] if candidates else None
            headers=best[3] if best and best[0]>=2 else []
            if len(headers)>80:
                headers=headers[:80]
            # Suppress anything that looks like a personal email/phone in a
            # mistakenly selected header row, but do not claim a reviewed schema.
            if any("@" in h or len(h)>100 or re.search(r"\d{6,}",h) for h in headers):
                headers=[]
            # Find the published field positions ONCE per source layout.
            # This does not inspect or persist event details outside RAM.
            role_columns = {}
            if headers:
                for index,label in best[6].items():
                    h = " ".join(str(label).casefold().split())
                    if "denominazione" in h or h == "manifestazione":
                        role_columns.setdefault("event",index)
                    elif h == "comune":
                        role_columns.setdefault("municipality",index)
                    elif h.startswith("periodo") or "periodo e orario" in h:
                        role_columns.setdefault("period",index)
                    elif h.startswith("sito web") or h.startswith("pagina social"):
                        role_columns.setdefault("website",index)
            counters = Counter()
            distinct_towns = set()
            if {"event","municipality","period"} <= set(role_columns):
                for row in rows[best[2]+1:]:
                    fields = {}
                    for cell in row.findall(NS+"c"):
                        number = _col_number(cell.attrib.get("r",""))
                        if number in role_columns.values():
                            fields[number]=_cell(cell,shared)
                    title = str(fields.get(role_columns["event"],"")).strip()
                    town = str(fields.get(role_columns["municipality"],"")).strip()
                    period = str(fields.get(role_columns["period"],"")).strip()
                    if not title or not town:
                        counters["rows_without_named_event_and_town"] += 1
                        continue
                    counters["rows_with_named_event_and_town_not_verified"] += 1
                    distinct_towns.add(" ".join(town.casefold().split()))
                    if period:
                        counters["rows_with_period_text_not_confirmed"] += 1
                    if re.search(r"\b20(?:25|26|27)\b", period):
                        counters["rows_with_year_in_period_text"] += 1
                    if role_columns.get("website") and fields.get(role_columns["website"]):
                        counters["rows_with_publisher_web_field"] += 1
                    title_fold = title.casefold()
                    if re.search(r"\bsagr[ae]\b",title_fold):
                        counters["sagra_named_rows_not_verified"] += 1
                    elif re.search(r"\bfier[ae]\b",title_fold):
                        counters["fiera_named_rows_not_verified"] += 1
                    elif re.search(r"\bmercat(?:o|i|ino|ini)\b",title_fold):
                        counters["market_like_title_rows_not_verified"] += 1
                    else:
                        counters["other_named_manifestation_rows"] += 1
            counters["distinct_municipality_labels_not_canonical_ISTAT"] = len(distinct_towns)
            # No event name, municipality value, personal field, link or
            # date content is retained in the report: only aggregate counts.
            summaries.append({
                "sheet":fname.split("/")[-1],
                "nonempty_rows":numeric,
                "likely_header_row":best[5] if headers else None,
                "header_field_names_only":headers,
                "matched_concepts":best[4] if headers else [],
                "source_schema_review_required":not bool(headers),
                "source_entries_not_new_markets":max(0,numeric-(best[2]+1 if headers else 0)),
                "aggregate_row_classification_only":dict(sorted(counters.items())),
            })
    return {
        "schema":1, "reference_date":today.isoformat(), "publisher":"Regione Veneto",
        "publisher_landing_url":LANDING,
        "publisher_source_url":SOURCE,
        "publisher_page_date_last_checked":"2026-10-08",
        "source_kind":"temporary_sagre_and_fairs_not_weekly_markets",
        "source_sha256":hashlib.sha256(blob).hexdigest(),
        "compressed_source_bytes":len(blob),
        "worksheets":summaries,
        "sheet_count":len(summaries),
        "schema_only":True, "source_rights_to_copy_event_rows_reviewed":False,
        "market_catalog_imports":0, "market_catalog_updates":0,
        "verified_market_openings":0, "event_rows_persisted":0,
    }

def markdown(info):
    result=[
        "# Veneto sagre e fiere 2026 — schema XLSX ufficiale (sola lettura)",
        "",
        "Pagina regionale consultata il 18 ottobre 2026; il documento è indicato come aggiornato all'8 ottobre.",
        "La data ufficiale indica la pubblicazione del calendario, NON la conferma della singola festa.",
        "Nessun dato di evento, contatto, coordinate, giorno o appuntamento è importato.",
        "",
        "- Workbook: "+info["publisher_source_url"],
        "- SHA-256 download: "+info["source_sha256"],
        "- Dimensione scaricata: "+str(info["compressed_source_bytes"])+" byte",
        "- Fogli strutturali: "+str(info["sheet_count"]),
        "",
    ]
    for sheet in info["worksheets"]:
        result.extend([
            "## "+sheet["sheet"],
            "- Righe non vuote (include intestazioni/strutture): "+str(sheet["nonempty_rows"]),
            "- Intestazione rilevata in riga: "+str(sheet["likely_header_row"]),
            "- Campi rilevati per tipo: "+", ".join(sheet["matched_concepts"]),
            "- Intestazioni campo, solo schema: "+", ".join(sheet["header_field_names_only"]),
            "- Eventi classificati SOLO per conteggi: "+json.dumps(sheet["aggregate_row_classification_only"],ensure_ascii=False,sort_keys=True),
            "- **Stato:** revisione struttura/riuso necessaria; nessuna importazione",
            "",
        ])
    return "\n".join(result)+"\n"

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--input",type=Path)
    ap.add_argument("--out",required=True,type=Path)
    ap.add_argument("--report",required=True,type=Path)
    ap.add_argument("--today",type=date.fromisoformat,default=date.today())
    args=ap.parse_args()
    try:
        blob=args.input.read_bytes() if args.input else guarded_download()
    except OSError as exc:
        print("VENETO_TRANSPORT_UNAVAILABLE", type(exc).__name__)
        raise SystemExit(3) from None
    except ValueError as exc:
        print("VENETO_SOURCE_SCOPE_REVIEW", str(exc)[:500])
        raise SystemExit(4) from None
    try:
        info=analyze(blob,today=args.today)
    except ValueError as exc:
        print("VENETO_XLSX_SCHEMA_REVIEW", str(exc)[:500])
        raise SystemExit(4) from None
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.report.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(info,indent=2,ensure_ascii=False)+"\n","utf-8")
    args.report.write_text(markdown(info),"utf-8")
    print(json.dumps({"sheets":info["sheet_count"],
                      "nonempty_sheet_rows":sum(x["nonempty_rows"] for x in info["worksheets"]),
                      "headers_observed":sum(bool(x["header_field_names_only"]) for x in info["worksheets"]),
                      "market_imports":0,"verified_events":0}))
if __name__=="__main__":
    main()
