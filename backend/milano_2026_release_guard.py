#!/usr/bin/env python3
"""Independent field-level release proof for two-source Milan forecast updates."""
from __future__ import annotations
from milano_2026_overlay import (
    PDF_DATE, PDF_DOCUMENT, OFFICIAL_PDF_SOURCE, OLD_DATASET,
    verified_pairs, WEEKDAYS,
)
from recurrence_refresh import explicit_rule

ALLOWED = frozenset({"aggiornato_il","aggiornamento_ambito",
                     "ricorrenza_testo","fonti","fonte_aggiornata_il"})


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
                or b.get("aggiornamento_ambito")!="dataset"
                or "fonte_aggiornata_il" in fields and b.get("fonte_aggiornata_il")!=PDF_DATE.isoformat()):
            raise ValueError("Official source and forecast scope changed: "+slug)
        rule=explicit_rule(b.get("ricorrenza_testo"))
        if not rule or rule.get("kind")!="weekly" or rule["weekdays"]!=matches[id_]:
            raise ValueError("New weekdays do not match exact publisher evidence: "+slug)
        original=list(a.get("fonti") or [])
        primary={"nome":str(a.get("fonte") or ""),"url":str(a.get("url_fonte") or "")}
        enriched=b.get("fonti")
        if (not isinstance(enriched,list)
                or OFFICIAL_PDF_SOURCE not in enriched
                or primary not in enriched
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


def verify_exported(before, after, report, pdf, gis, today):
    """Check published regional details, not merely the intermediate overlay.

    A valid original PDF/GIS pair does not grant new IDs or opening confirmations.
    All 77 reviewed Milano IDs must retain PDF evidence and only forecast dates
    when the 2026 schedule is still within the approved 540-day source window.
    """
    from datetime import date
    if not isinstance(today, date):
        raise ValueError("Real reference date required for final Milan proof")
    admission_certificate = report.get("happings_detail_admission_certificate")
    separately_proved = 0
    if admission_certificate is not None:
        from happings_detail_enrichment import verify_source_admission_certificate
        after, separately_proved = verify_source_admission_certificate(
            before, after, admission_certificate, today)
    matched, _ = verified_pairs(pdf, gis)
    if (len(matched) != 77 or not isinstance(before, list) or
            not isinstance(after, list) or len(before) != len(after) or
            report.get("schema") != 1 or report.get("enabled") is not True or
            report.get("records_total") != len(before) or
            report.get("verified_future_events_created") != 0 or
            report.get("confirmed_dates_created") != 0 or
            report.get("records_added") != 0 or
            report.get("records_deleted") != 0):
        raise ValueError("Milan 2026 source/market contract changed before publication")
    before_by = {x["slug"]:x for x in before}
    after_by = {x["slug"]:x for x in after}
    if len(before_by) != len(before) or set(before_by) != set(after_by):
        raise ValueError("Final Milan catalog lost or added market IDs")

    covered = {}
    source_modified = set(report.get("modified_ids", []))
    if len(source_modified) > 77:
        raise ValueError("Unbounded 2026 Milan schedule changes")
    for official_id, weekdays in matched.items():
        slug = "mi-mss-" + str(official_id)
        old = before_by.get(slug)
        current = after_by.get(slug)
        if old is None or current is None:
            raise ValueError("A reviewed Milan municipal stable ID disappeared")
        # Existing identities, venues and status remain unchanged even if
        # some older historic location is no longer visitable.
        for field in ("slug","nome","citta","provincia","regione","indirizzo",
                      "lat","lng","position_quality","status","url_fonte",
                      "fonte","verificato_il","orario_testo","categoria"):
            if old.get(field) != current.get(field):
                raise ValueError("Unsafe Milan source field changed in exported JSON: "+slug)
        if (current.get("aggiornato_il") != PDF_DATE.isoformat() or
                current.get("aggiornamento_ambito") != "dataset" or
                current.get("url_fonte") != OLD_DATASET or
                current.get("verificato_il") or
                current.get("date_quality") == "confermata"):
            raise ValueError("Milan official PDF misrepresented as verified event: "+slug)
        old_source = {"nome":str(old.get("fonte") or ""),"url":str(old.get("url_fonte") or "")}
        all_sources = current.get("fonti")
        if (not isinstance(all_sources,list) or
                OFFICIAL_PDF_SOURCE not in all_sources or
                old_source not in all_sources):
            raise ValueError("Milan original publisher or new source missing: "+slug)
        parsed = explicit_rule(current.get("ricorrenza_testo"))
        if (not parsed or parsed.get("kind")!="weekly" or
                parsed.get("weekdays")!=weekdays):
            raise ValueError("Final Milan market weekdays disagree with PDF and GIS: "+slug)
        age=(today-PDF_DATE).days
        fresh = 0<=age<=540
        if fresh:
            future = current.get("date")
            if (current.get("date_quality")!="prevista" or not isinstance(future,list)
                    or len(future)<8 or any(x < today.isoformat() for x in future)):
                raise ValueError("Final Milan schedule is not conservatively forecast: "+slug)
        elif current.get("date") or current.get("date_quality")!="sconosciuta":
            raise ValueError("Expired Milan schedule still advertises future occurrences: "+slug)
        covered[slug]=current
    if source_modified - set(covered):
        raise ValueError("Milan source report cites an unreviewed official market ID")
    proof = {
        "schema":1,"reviewed_milan_ids":len(covered),
        "publisher_document_date":PDF_DATE.isoformat(),
        "forecast_labeled_not_confirmed":sum(x.get("date_quality")=="prevista" for x in covered.values()),
        "preserved_original_sources":len(covered),
        "unchanged_stable_market_ids":len(before),
        "confirmed_market_events_created":0,"market_records_added":0,
        "market_records_deleted":0,
        "quality_safe":True,
    }
    if admission_certificate is not None:
        proof["separately_proved_happings_admissions"] = separately_proved
    return proof
