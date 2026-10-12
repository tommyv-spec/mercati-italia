#!/usr/bin/env python3
"""Exact, reproducible dataset-row disposition, not guessed market creation.

Compare every stable SOURCE row ID to (1) baseline catalog IDs and (2)
the exact set suppressed by that source's already-approved venue-overlap
review. A matching *count* is not evidence that the same IDs were screened.

This module neither updates a market nor decides if the source's venue
really exists or opens. Keep source IDs ephemeral; publish only counts
and a digest of the held set so audits remain small and do not leak rows.
"""
from __future__ import annotations

import hashlib
import json


def reconcile(source_ids, catalog_ids, reviewed_excluded_ids=None,
              *, reviewed_excluded_count=None, reviewed_accepted_count=None):
    if (not isinstance(source_ids, (list, tuple, set))
            or not isinstance(catalog_ids, (list, tuple, set))):
        raise ValueError("Source and catalog identity sets are required")
    for label, items in (("source", source_ids), ("catalog", catalog_ids)):
        if any(not isinstance(x, str) or not x or len(x)>180 for x in items):
            raise ValueError("Invalid "+label+" market identifiers")
        if len(set(items))!=len(items):
            raise ValueError("Duplicate "+label+" market identity")
    ids=set(source_ids)
    catalog=set(catalog_ids)
    outside=ids-catalog
    if reviewed_excluded_ids is None:
        if reviewed_excluded_count not in (None,0):
            # A numeric '233 excluded' is not a source identity proof.
            # Report unresolved, do not silently mark 233 IDs as handled.
            return {
                "outside_catalog_source_ids_not_necessarily_new_markets":len(outside),
                "already_quarantined_by_venue_overlap_review":0,
                "remaining_identities_without_overlap_disposition":len(outside),
                "screening_missing_exact_source_id_proof":True,
                "source_screening_counts_are_not_market_opening_proofs":True,
            }
        return {
            "outside_catalog_source_ids_not_necessarily_new_markets":len(outside),
            "already_quarantined_by_venue_overlap_review":0,
            "remaining_identities_without_overlap_disposition":len(outside),
            "screening_missing_exact_source_id_proof":False,
            "source_screening_counts_are_not_market_opening_proofs":True,
        }
    if not isinstance(reviewed_excluded_ids,(list,tuple,set)):
        raise ValueError("Invalid reviewed source identity partition")
    if (any(not isinstance(x,str) or not x or len(x)>180 for x in reviewed_excluded_ids)
            or len(set(reviewed_excluded_ids))!=len(reviewed_excluded_ids)):
        raise ValueError("Duplicate/malformed reviewed official source IDs")
    excluded=set(reviewed_excluded_ids)
    if not excluded <= ids:
        raise ValueError("Reviewed excluded ID does not belong to this source snapshot")
    if excluded & catalog:
        raise ValueError("Already published ID was incorrectly declared quarantined")
    if type(reviewed_excluded_count) is not int or reviewed_excluded_count!=len(excluded):
        raise ValueError("Count of exact reviewed exclusions differs from source QA report")
    if type(reviewed_accepted_count) is not int or reviewed_accepted_count!=len(ids)-len(excluded):
        raise ValueError("Accepted source ID count and reviewed partition differ")
    newly=outside-excluded
    return {
        "outside_catalog_source_ids_not_necessarily_new_markets":len(outside),
        "already_quarantined_by_venue_overlap_review":len(excluded),
        "remaining_identities_without_overlap_disposition":len(newly),
        "screening_missing_exact_source_id_proof":False,
        "exact_reviewed_id_partition_verified":True,
        "quarantine_source_id_set_sha256":hashlib.sha256(
            json.dumps(sorted(excluded),ensure_ascii=False,separators=(",",":")).encode()
        ).hexdigest(),
        "source_screening_counts_are_not_market_opening_proofs":True,
    }
