"""Recover source-stated Happings weekly dayparts and duplicate-record streets.

Offline, repeatable, conservative: reads the checksum-verified national crawl.
No source page URLs are invented; nonunique venues never get made-up streets.
Existing confirmed or nonempty fields remain untouched.
"""
from __future__ import annotations

import argparse
import json
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path

from field_evidence import _provenance_key, clean_receipts, mark_managed_fields, retire_superseded_receipts
from happings_full_reconciliation import _saved_page
from happings_weekly_layout import fold, province_page_key
from merge_catalog import load_existing
from stored_market_sibling_proposals import same_generic_venue, safe_stored_street
import happings_source_enrichment as source

DAYPART = {
    "morning_not_clock_hours": "La mattina",
    "afternoon_not_clock_hours": "Il pomeriggio",
}
FIELDS = ("indirizzo", "orario_testo")
MAX_RESTORED = 50000


def read_weekly_source(snapshot, *, today):
    snapshot = Path(snapshot)
    state = json.loads((snapshot / "checkpoint.json").read_text(encoding="utf-8"))
    queue, done = state.get("queue"), state.get("done")
    if (state.get("schema") != 1 or not isinstance(queue, list)
            or not isinstance(done, dict) or not 1 <= len(queue) <= MAX_RESTORED
            or len(set(queue)) != len(queue) or set(queue) != set(done)):
        raise ValueError("Source inventory is not complete and unique")
    municipalities, provinces = source._official_geography()
    groups = defaultdict(list)
    stats = Counter()
    for url in queue:
        info = done[url]
        if info.get("kind") != "weekly":
            continue
        fact = _saved_page(snapshot, url, info)
        if fact.get("status") != "parsed":
            raise ValueError("Unparsed weekly pages cannot be excluded silently")
        scope = provinces.get(province_page_key(url), set())
        if len(scope) != 1:
            raise ValueError("Source province page scope has no unique official identity")
        region, page_province = next(iter(scope))
        read_on = date.fromisoformat(fact["read_at"][:10])
        if read_on > today or (today - read_on).days > 45:
            raise ValueError("Source observation is future-dated or stale")
        rows = fact.get("markets")
        if not isinstance(rows, list) or len(rows) != fact.get("source_rows"):
            raise ValueError("Weekly source page lost observed market rows")
        stats["weekly_pages"] += 1
        stats["source_rows"] += len(rows)
        for row in rows:
            city = fold(row.get("city"))
            # Happings files towns under pre-2009 borders (Monza on the Milano
            # page) and lists quartieri, numbered stalls and renamed towns.
            # Dropping them left ~750 records without their stated daypart.
            # Only records that already cite this page get filled
            # (record_matches_page), so key on the ISTAT province when known.
            real_province = municipalities.get((region, city)) or page_province
            if real_province != page_province:
                stats["source_page_old_province_border"] += 1
            elif (region, city) not in municipalities:
                stats["source_town_not_istat_name"] += 1
            day = row.get("weekday")
            if type(day) is not int or not 0 <= day <= 6:
                raise ValueError("Invalid publisher weekday")
            groups[(region, real_province, city, day)].append({
                "url": url, "html_sha256": fact["html_sha256"],
                "read_on": read_on.isoformat(), "daypart": row.get("daypart"),
                "place": row.get("place"), "has_specific_location":
                    row.get("has_specific_location"),
                "calendar_scope": row.get("calendar_scope"),
                "editorial_scope": row.get("editorial_scope"),
            })
    return groups, stats


def catalog_key(row):
    day = source._weekly_day(row)
    if day is None or not same_generic_venue(row):
        return None
    return (fold(row.get("regione")),str(row.get("provincia") or "").upper(),
            fold(row.get("citta")),day)


def same_weekly_venue(rows):
    """Only identical generic names, weekdays and sources may share an anchor."""
    if not rows:
        return False
    def market_name(row):
        return fold(row.get("nome")).replace("mercato settimanale a ", "mercato settimanale di ")
    return (len({market_name(r) for r in rows}) == 1
            and len({fold(r.get("ricorrenza_testo")) for r in rows}) == 1
            and all(r.get("fonte") == source.PUBLISHER for r in rows))


def _update(row, proposed, evidence, *, today):
    if not proposed:
        return row, "nothing_source_backed_missing"
    if row.get("verificato_il"):
        return row, "human_verified_record_held"
    proof = source._field_receipt(row, proposed, evidence)
    if not source._version_is_ordered(row, proof, today):
        return row, "source_version_ordering_unproven"
    previous_receipts = clean_receipts(row.get("riscontri_campi"), row, today=today)
    same_bytes = [r for r in previous_receipts
                  if _provenance_key(r) == _provenance_key(proof)
                  and r["sha256"] == proof["sha256"]
                  and r["letto_il"] == proof["letto_il"]]
    if len(same_bytes) > 1:
        raise ValueError("Duplicate same-source market provenance")
    if same_bytes:
        # A fixed parser can recover a field from the exact HTML already
        # witnessed by an older receipt. Merge that field into the SAME
        # proof; don't create a competing same-day source version.
        merged = deepcopy(same_bytes[0])
        merged["valori"].update(proposed)
        managed = mark_managed_fields(
            merged, list(proposed), manager=source.FIELD_MANAGER,previous=row)
    else:
        managed = mark_managed_fields(
            proof, list(proposed), manager=source.FIELD_MANAGER,previous=row)
    result = deepcopy(row)
    result.update(proposed)
    kept = retire_superseded_receipts(row, managed, today=today)
    if same_bytes:
        kept = [r for r in kept if _provenance_key(r) != _provenance_key(managed)]
    result["riscontri_campi"] = clean_receipts([*kept, managed], result, today=today)
    if not any(all(r.get("valori",{}).get(field) == value
                   for field,value in proposed.items())
               and r.get("sha256") == evidence["source_html_sha256"]
               and r.get("url") == evidence["source_url"]
               for r in result.get("riscontri_campi") or []):
        raise ValueError("Publisher source values lost their identity-bound receipt: " + str(row.get("slug")))
    link = {"nome":source.SOURCE_EVIDENCE_NAME, "url":evidence["source_url"]}
    links = deepcopy(row.get("fonti") or [])
    if not isinstance(links, list) or any(not isinstance(x, dict) for x in links):
        raise ValueError("Invalid existing source links")
    if link not in links:
        links.append(link)
    result["fonti"] = links
    return result, None


def enrich(catalog, snapshot, *, today):
    if not isinstance(catalog, list) or not 1 <= len(catalog) <= 100000:
        raise ValueError("Unbounded market catalog")
    approved = source.authorization_status(
        json.loads(source.RIGHTS_REVIEW_FILE.read_text("utf-8")),today=today)
    if not approved.get("authorized"):
        raise ValueError("Happings source authorization expired")
    groups, stats = read_weekly_source(snapshot,today=today)
    targets = defaultdict(list)
    catalog_ids = set()
    for row in catalog:
        sid = row.get("slug")
        if not sid or sid in catalog_ids:
            raise ValueError("Missing or duplicated market identity")
        catalog_ids.add(sid)
        if row.get("fonte") == source.PUBLISHER:
            key = catalog_key(row)
            if key is not None:
                targets[key].append(row)
    output = deepcopy(catalog)
    index = {r["slug"]: i for i,r in enumerate(catalog)}
    changes = []
    holds = Counter()
    for key, entries in groups.items():
        if any(e.get("calendar_scope") or
               (e.get("editorial_scope") and
                e["editorial_scope"].get("status") != "current")
               for e in entries):
            holds["qualified_source_calendar"] += 1
            continue
        urls = {e["url"] for e in entries}
        if len(urls) != 1:
            holds["multiple_source_pages_for_cohort"] += 1
            continue
        url = next(iter(urls))
        primary = [r for r in targets.get(key, [])
                   if source.record_matches_page(r, url, url)]
        if not primary:
            holds["no_proven_happings_weekly_identity"] += 1
            continue
        precise = [e for e in entries if e.get("has_specific_location")
                   and safe_stored_street(e.get("place"))]
        unique_street = precise[0]["place"] if len(entries) == 1 and len(precise) == 1 else None
        anchors = [r for r in primary if unique_street
                   and safe_stored_street(r.get("indirizzo"))
                   and source._same_place(r["indirizzo"], unique_street)]
        # Do not assign one venue to competing exact addresses.
        conflict = bool(unique_street and any(
            safe_stored_street(r.get("indirizzo"))
            and not source._same_place(r["indirizzo"],unique_street) for r in primary))
        can_fill_street = bool(
            unique_street and not conflict and
            (len(primary) == 1 or anchors and same_weekly_venue(primary)))
        dayparts = {e.get("daypart") for e in entries}
        same_daypart = next(iter(dayparts)) if len(dayparts) == 1 else None
        hours = DAYPART.get(same_daypart)
        # A source page may list multiple different venues. We only propagate a
        # shared daypart when EVERY venue in that cohort has the same text.
        for row in primary:
            changeset = {}
            if can_fill_street and not str(row.get("indirizzo") or "").strip():
                changeset["indirizzo"] = unique_street
            if hours and not str(row.get("orario_testo") or "").strip():
                changeset["orario_testo"] = hours
            if not changeset:
                continue
            sample = entries[0]
            evidence = {
                "source_url": url, "source_day": key[3],
                "source_html_sha256": sample["html_sha256"],
                "observed_at": sample["read_on"],
            }
            updated,reason = _update(row, changeset, evidence, today=today)
            if reason:
                holds[reason] += 1
                continue
            index_position = index[row["slug"]]
            output[index_position] = updated
            changes.append({"id":row["slug"],"fields":sorted(changeset),
                            "source":url,"source_html_sha256":sample["html_sha256"],
                            "after":changeset})
            stats["updated_records"] += 1
            for field in changeset:
                stats["filled_" + field] += 1
    stats["source_group_keys"] = len(groups)
    stats["catalog_before"] = len(catalog)
    stats["catalog_after"] = len(output)
    if stats["updated_records"] != len(changes):
        raise ValueError("Change ledger missing source-backed row")
    for old,new in zip(catalog,output):
        if old["slug"] != new["slug"]:
            raise ValueError("Market order or identity changed")
        delta = {field for field in set(old)|set(new)
                 if old.get(field) != new.get(field)}
        if delta and not delta.issubset(set(FIELDS)|{"fonti","riscontri_campi"}):
            raise ValueError("Bulk Happings enrichment modified protected fields")
    return output,{"schema":1,"date":today.isoformat(),"publisher":"happings.com",
                   "snapshot_pages_checked":stats["weekly_pages"],
                   "counts":dict(sorted(stats.items())),
                   "holds":dict(sorted(holds.items())),
                   "changes":changes,"existing_ids_removed":0,
                   "invented_clock_times":0,"human_openings_confirmed":0}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest",type=Path,required=True)
    parser.add_argument("--snapshot",type=Path,required=True)
    parser.add_argument("--out",type=Path,required=True)
    parser.add_argument("--today",type=date.fromisoformat,default=date.today())
    args=parser.parse_args()
    catalog=load_existing(args.manifest)
    updated,report=enrich(catalog,args.snapshot,today=args.today)
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/"happings-bulk-field-candidate.json").write_text(
        json.dumps(updated,ensure_ascii=False,separators=(",",":"))+"\n",encoding="utf-8")
    (args.out/"happings-bulk-field-report.json").write_text(
        json.dumps(report,ensure_ascii=False,sort_keys=True,indent=2)+"\n",encoding="utf-8")
    print(json.dumps({k:v for k,v in report.items() if k!="changes"},
                     ensure_ascii=False,sort_keys=True),flush=True)

if __name__=="__main__":
    main()
