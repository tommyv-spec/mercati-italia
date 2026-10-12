#!/usr/bin/env python3
"""Independent field-level release proof for two-source Milan forecast updates."""
from __future__ import annotations
from milano_2026_overlay import (
    PDF_DATE, PDF_DOCUMENT, OFFICIAL_PDF_SOURCE, OLD_DATASET,
    verified_pairs, WEEKDAYS,
)
from recurrence_refresh import explicit_rule

ALLOWED = frozenset({"aggiornato_il","aggiornamento_ambito",
                     "ricorrenza_testo","fonti"})


def verify(before, after, report, pdf, gis):
    matches,_=verified_pairs(pdf,gis)
    if (not isinstance(before,list) or not isinstance(after,list)
            or len(before)!=len(after)
            or [x.get("slug") for x in before] != [x.get("slug") for x in after]
            or report.get("schema")!=1
            or report.get("records_total")!=len(before)
            or any(report.get(k)!=0 for k in (
                "records_deleted","records_added","verified_future_events_created",
                "confirmed_dates_created","coordinates_changed","primary_sources_changed"))):
        raise ValueError("Milan publisher proof violates identity/confirmation constraints")
    changed=[]
    for a,b in zip(before,after):
        fields={k for k in a.keys()|b.keys() if a.get(k)!=b.get(k)}
        if not fields:continue
        slug=a["slug"]
        if fields-ALLOWED or not slug.startswith("mi-mss-"):
            raise ValueError("Non-source market field changed: "+slug)
        try:id_=int(slug[7:])
        except ValueError:raise ValueError("Milan edited an invalid official ID: "+slug) from None
        if id_ not in matches or a.get("regione")!="Lombardia" or a.get("citta")!="Milano":
            raise ValueError("Milan change not covered by both publishers: "+slug)
        if (a.get("url_fonte")!=OLD_DATASET or b.get("url_fonte")!=OLD_DATASET
                or a.get("verificato_il") or a.get("date_quality") in ("confermata","riportata")
                or b.get("aggiornato_il")!=PDF_DATE.isoformat()
                or b.get("aggiornamento_ambito")!="dataset"):
            raise ValueError("Official source and forecast scope changed: "+slug)
        rule=explicit_rule(b.get("ricorrenza_testo"))
        if not rule or rule.get("kind")!="weekly" or rule["weekdays"]!=matches[id_]:
            raise ValueError("New weekdays do not match exact publisher evidence: "+slug)
        original=list(a.get("fonti") or [])
        enriched=b.get("fonti")
        if (not isinstance(enriched,list)
                or OFFICIAL_PDF_SOURCE not in enriched
                or any(old not in enriched for old in original)):
            raise ValueError("Original source evidence lost: "+slug)
        changed.append(slug)
    if sorted(changed)!=report.get("modified_ids"):
        raise ValueError("Milan changed IDs do not match signed report")
    if len(changed)>84:
        raise ValueError("Milan released too many source updates")
    return {
        "schema":1,"stable_ids_checked":len(before),
        "milan_source_changes":len(changed),"market_ids_added":0,
        "market_ids_removed":0,"verified_events_added":0,
        "source_originals_lost":0,"coordinates_edited":0,
        "publisher_document":PDF_DOCUMENT,
        "publisher_document_date":PDF_DATE.isoformat(),
        "release_safe":True,
    }
