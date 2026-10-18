#!/usr/bin/env python3
"""Independent field-level parity QA for a generic source and an existing adapter.

Both converters read the SAME bounded original bytes. This isn't an
authorization for import: matching old source facts proves only that the
generic parser didn't lose identities, location labels, weekdays or hours.
A per-source legacy oracle may safely be removed after its parity is proven.
"""
from __future__ import annotations

import hashlib
import json
from collections import Counter
from datetime import date

from source_contract_ingest import venue_row, validate_format
from source_lifecycle import parse_rows, canonical, digest


SOURCE_FACT_FIELDS = (
    "slug","nome","citta","provincia","regione","indirizzo",
    "ricorrenza_testo","orario_testo","aggiornato_il",
    "aggiornamento_ambito","status","categoria",
)


def compare(profile,blob,legacy,*,today):
    if not isinstance(today,date) or not isinstance(legacy,list):
        raise ValueError("Source parity requires a publisher-day and trusted previous converter")
    validate_format(profile)
    parsed=parse_rows(profile,blob)
    generated=[]
    issues=Counter()
    for row in parsed:
        converted,reason,_=venue_row(profile,row,today)
        if converted is None:
            issues[reason or "source_row_rejected"]+=1
            continue
        generated.append(converted)
        if reason:
            issues["source_only_"+reason]+=1
    def unique(rows,label):
        out={}
        for row in rows:
            if not isinstance(row,dict) or not isinstance(row.get("slug"),str) or not row["slug"]:
                raise ValueError("Invalid stable source identity in "+label)
            if row["slug"] in out:
                raise ValueError("Duplicate stable source identity in "+label)
            out[row["slug"]]=row
        return out
    new=unique(generated,"shared parser")
    old=unique(legacy,"previous source adapter")
    missing=sorted(set(old)-set(new))
    added=sorted(set(new)-set(old))
    drift=Counter()
    changed=[]
    for sid in sorted(set(new)&set(old)):
        current,prior=new[sid],old[sid]
        differing=[field for field in SOURCE_FACT_FIELDS
                   if canonical(current.get(field))!=canonical(prior.get(field))]
        if differing:
            for field in differing:drift[field]+=1
            changed.append(digest({"source":profile["id"],"venue":sid}))
        if (current.get("lat") is not None or current.get("lng") is not None or
                current.get("position_quality")!="sconosciuta" or
                current.get("date") or current.get("date_quality")!="sconosciuta" or
                current.get("verificato_il") or
                current.get("status")!="non_confermato"):
            raise ValueError("Generic parser claimed verification, events or GPS")
    if any(row.get("verificato_il") or row.get("status")=="attivo"
           or row.get("date_quality")=="confermata" for row in old.values()):
        raise ValueError("Legacy source falsely certified a market opening")
    complete=(not missing and not added and not changed
              and not issues and len(new)==len(legacy))
    return {
        "schema":1,
        "source_id":profile["id"],
        "source_snapshot_sha256":hashlib.sha256(blob).hexdigest(),
        "profile_sha256":digest(profile),
        "review_only":True,"source_rows_in_file":len(parsed),
        "old_adapter_identities":len(old),"generic_adapter_identities":len(new),
        "identical_identity_ids":len(set(old)&set(new)),
        "legacy_only_market_ids_count":len(missing),
        "generic_only_market_ids_count":len(added),
        "changed_source_identity_count":len(changed),
        "changed_fields":dict(sorted(drift.items())),
        "source_row_issue_counts":dict(sorted(issues.items())),
        "changed_identity_hashes":sorted(changed)[:12],
        "no_market_openings_confirmed":True,
        "no_precise_coordinates_created":True,
        "new_market_identities_published":0,
        "old_market_identities_deleted":0,
        "parity_complete":complete,
    }


def verify(report,*,expect_identities=None):
    if (not isinstance(report,dict) or report.get("schema")!=1 or
            report.get("review_only") is not True or
            report.get("parity_complete") is not True or
            report.get("new_market_identities_published")!=0 or
            report.get("old_market_identities_deleted")!=0 or
            report.get("no_market_openings_confirmed") is not True or
            report.get("no_precise_coordinates_created") is not True or
            report.get("source_rows_in_file")!=report.get("generic_adapter_identities") or
            report.get("generic_adapter_identities")!=report.get("old_adapter_identities") or
            (expect_identities is not None and
             report.get("old_adapter_identities")!=expect_identities)):
        raise ValueError("Generic source contract does not reproduce the existing official adapter")
    return True
