"""Recover source-stated Happings weekly fields and soft-merge repeated copies.

Offline, repeatable, conservative: reads the checksum-verified national crawl.
No source page URLs are invented; nonunique venues never get made-up streets.
Existing confirmed or nonempty fields remain untouched, except a weekday that
a legacy import cut short ("settimanale - me"), repaired only when the page
leaves exactly one possible day.

When the page lists ONE market for a town and weekday, every Happings record
citing it for that town/day is the same market: the most complete one is kept
and the others get "duplicato_di" (IDs stay; the app hides the copies).
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import date, datetime
from pathlib import Path

from export_static import data_value_score, dayparts, same_market, same_venue, shares_street, venue_slot
from field_evidence import _provenance_key, clean_receipts, mark_managed_fields, retire_superseded_receipts
from happings_full_reconciliation import _saved_page
from happings_weekly_layout import WEEKDAYS, fold, province_page_key
from merge_catalog import load_existing
from stored_market_sibling_proposals import same_generic_venue, safe_stored_street
import happings_source_enrichment as source

DAYPART = {
    "morning_not_clock_hours": "La mattina",
    "afternoon_not_clock_hours": "Il pomeriggio",
}
FIELDS = ("indirizzo", "orario_testo", "ricorrenza_testo")
WEEKDAY_TEXT = ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica")
CUT_WEEKLY = re.compile(r"settimanale(?: ([a-z]{1,7}))?")
CENTRE = re.compile(r"(?:in )?centro(?: storico| paese| citta)?")
CLOCK = re.compile(r"\b\d{1,2}[:.]\d\d\b")
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


def cut_weekday(row, page_days):
    """The one page weekday still allowed by a cut text, else None."""
    match = CUT_WEEKLY.fullmatch(fold(row.get("ricorrenza_testo")))
    if (not match or source.temporal_scope_hold(row)
            or source._weekly_day(row) is not None):
        return None
    prefix = match.group(1) or ""
    fits = [d for d in page_days if WEEKDAYS[d].startswith(prefix) and WEEKDAYS[d] != prefix]
    return fits[0] if len(fits) == 1 else None


def kept_record(rows, street=None, hours=None):
    """The visible card is the one that tells the visitor most: the listed street,
    a real street, exact clock hours; then stable (already kept stays). Dates do
    not decide: every member has upcoming ones."""
    already = {r.get("duplicato_di") for r in rows}
    page = {"indirizzo": street, "orario_testo": hours or ""}
    def listed(r):
        # Another source's card may name the listed street in its own spelling,
        # at a time of day the page doesn't contradict.
        if not street or source._same_place(r.get("indirizzo"), street):
            return bool(street)
        own, said = dayparts(r), dayparts(page)
        return (r.get("fonte") != source.PUBLISHER and not (own and said and not own & said)
                and shares_street(r, {**page, "citta": r.get("citta")}))
    return max(rows, key=lambda r: (listed(r),
                                    safe_stored_street(r.get("indirizzo")),
                                    bool(CLOCK.search(str(r.get("orario_testo") or ""))),
                                    r["slug"] in already, data_value_score(r),
                                    r.get("lat") is not None, -len(r["slug"]), r["slug"]))


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
    # Only changed values are assigned (managed); values the page still states
    # unchanged are observed, which keeps the proof - and forecasts - current.
    # Only a cut weekday (cut_weekday) is ever proposed over a nonempty
    # value; the broken text carries no claim to protect.
    assigned = [field for field, value in proposed.items() if value != row.get(field)]
    prior = {**row, "ricorrenza_testo": ""} if "ricorrenza_testo" in assigned else row
    if same_bytes:
        # A fixed parser can recover a field from the exact HTML already
        # witnessed by an older receipt. Merge that field into the SAME
        # proof; don't create a competing same-day source version.
        proof = deepcopy(same_bytes[0])
        proof["valori"].update(proposed)
    managed = (mark_managed_fields(proof, assigned, manager=source.FIELD_MANAGER, previous=prior)
               if assigned else proof)
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
    def qualified(entries):
        return any(e.get("calendar_scope") or
                   (e.get("editorial_scope") and
                    e["editorial_scope"].get("status") != "current")
                   for e in entries)
    town_days = defaultdict(set)
    for (region, province, city, day), entries in groups.items():
        if not qualified(entries):
            town_days[(region, province, city)].add(day)
    targets = defaultdict(list)
    others = defaultdict(list)
    repaired = {}
    catalog_ids = set()
    for row in catalog:
        sid = row.get("slug")
        if not sid or sid in catalog_ids:
            raise ValueError("Missing or duplicated market identity")
        catalog_ids.add(sid)
        if row.get("fonte") == source.PUBLISHER:
            # Match a cut weekday under the day its page proves; the
            # repaired text is proposed below with the same page receipt.
            day = cut_weekday(row, town_days.get((fold(row.get("regione")),
                str(row.get("provincia") or "").upper(), fold(row.get("citta"))), ()))
            view = row if day is None else {**row, "ricorrenza_testo": "settimanale - " + WEEKDAY_TEXT[day]}
            key = catalog_key(view)
            if key is not None:
                targets[key].append(view)
                if view is not row:
                    repaired[sid] = view["ricorrenza_testo"]
        elif (key := catalog_key(row)) is not None:
            others[key].append(row)
    # Any other source's card for the same market (export_static.same_venue: town,
    # calendar, street in either spelling) with upcoming dates may join a cohort,
    # so the visible card is the most detailed one whichever site has it.
    upcoming = today.isoformat()
    venues = defaultdict(list)
    for row in catalog:
        if (row.get("fonte") != source.PUBLISHER and not row.get("duplicato_di")
                and any(d >= upcoming for d in row.get("date") or []) and (slot := venue_slot(row))):
            venues[slot].append(row)
    output = deepcopy(catalog)
    index = {r["slug"]: i for i,r in enumerate(catalog)}
    changes = []
    confirmations = []
    holds = Counter()
    marks = {}
    evaluated = set()
    for key, entries in groups.items():
        if qualified(entries):
            holds["qualified_source_calendar"] += 1
            continue
        urls = {e["url"] for e in entries}
        if len(urls) != 1:
            holds["multiple_source_pages_for_cohort"] += 1
            continue
        url = next(iter(urls))
        primary = [r for r in targets.get(key, [])
                   if source.record_matches_page(r, url, url)]
        # Another source's generic weekly market ("Mercato settimanale di <town>")
        # on a town and weekday this page lists exactly once is that same market:
        # it gets the page's still-listed proof and joins the one-card cohort.
        secondary = others.get(key, []) if len(entries) == 1 else []
        if not primary and not secondary:
            holds["no_proven_happings_weekly_identity"] += 1
            continue
        evaluated.update(r["slug"] for r in primary + secondary)
        evidence = {
            "source_url": url, "source_day": key[3],
            "source_html_sha256": entries[0]["html_sha256"],
            "observed_at": entries[0]["read_on"],
        }
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
        # "in centro" is all the page says: record it as stated, only for the
        # single listed market and never beside a saved exact street.
        centre = (entries[0]["place"].strip()
                  if len(entries) == 1 and not precise
                  and CENTRE.fullmatch(fold(entries[0].get("place")))
                  and not any(safe_stored_street(r.get("indirizzo")) for r in primary)
                  else None)
        dayparts = {e.get("daypart") for e in entries}
        same_daypart = next(iter(dayparts)) if len(dayparts) == 1 else None
        hours = DAYPART.get(same_daypart)
        # A source page may list multiple different venues. We only propagate a
        # shared daypart when EVERY venue in that cohort has the same text.
        for row in primary:
            changeset = {}
            if row["slug"] in repaired:
                changeset["ricorrenza_testo"] = repaired[row["slug"]]
            if not str(row.get("indirizzo") or "").strip():
                if can_fill_street:
                    changeset["indirizzo"] = unique_street
                elif centre:
                    changeset["indirizzo"] = centre
            if hours and not str(row.get("orario_testo") or "").strip():
                changeset["orario_testo"] = hours
            # Every read restates what the page still says for this row: the
            # town on this weekday, plus its place and daypart when unchanged.
            # One proof per page row survives, so a partial restatement would
            # drop older proof; the weekday keeps forecasts renewing.
            stated = {"ricorrenza_testo": row["ricorrenza_testo"]}
            place = str(row.get("indirizzo") or "").strip()
            if len(entries) == 1 and place and source._same_place(place, entries[0].get("place")):
                stated["indirizzo"] = row["indirizzo"]
            if hours and row.get("orario_testo") == hours:
                stated["orario_testo"] = hours
            sample = entries[0]
            evidence = {
                "source_url": url, "source_day": key[3],
                "source_html_sha256": sample["html_sha256"],
                "observed_at": sample["read_on"],
            }
            index_position = index[row["slug"]]
            updated,reason = _update(catalog[index_position], {**stated, **changeset}, evidence, today=today)
            if reason:
                holds[reason] += 1
                continue
            if updated == catalog[index_position]:
                continue
            output[index_position] = updated
            if not changeset:
                confirmations.append({"id":row["slug"],"source":url,
                                      "source_html_sha256":sample["html_sha256"],"values":stated})
                stats["still_listed_proofs_refreshed"] += 1
                continue
            changes.append({"id":row["slug"],"fields":sorted(changeset),
                            "source":url,"source_html_sha256":sample["html_sha256"],
                            "after":changeset})
            stats["updated_records"] += 1
            for field in changeset:
                stats["filled_" + field] += 1
        # One listed market: every matching record is that market. Several
        # listed: only records sharing one exact listed street are.
        for row in secondary:
            stated = {"ricorrenza_testo": row["ricorrenza_testo"]}
            index_position = index[row["slug"]]
            updated, reason = _update(catalog[index_position], stated, evidence, today=today)
            if reason:
                holds["other_source_" + reason] += 1
                continue
            if updated != catalog[index_position]:
                output[index_position] = updated
                confirmations.append({"id": row["slug"], "source": url,
                                      "source_html_sha256": evidence["source_html_sha256"], "values": stated})
                stats["other_source_still_listed_proofs"] += 1
        current = [output[index[r["slug"]]] for r in primary + secondary]
        if len(entries) == 1:
            cohorts = [current]
        else:
            by_street = defaultdict(list)
            for r in current:
                street = r.get("indirizzo")
                if safe_stored_street(street) and any(source._same_place(street, e["place"]) for e in precise):
                    by_street[fold(street)].append(r)
            cohorts = list(by_street.values())
        for rows in cohorts:
            # Another source's card joins only as the same venue as EVERY member with a
            # real street: never through one member a page row already holds together.
            placed = [r for r in rows if venue_slot(r)]
            for other in venues.get(venue_slot(placed[0]), ()) if placed else ():
                if other["slug"] not in evaluated and all(same_venue(r, other) for r in placed):
                    rows.append(other)
                    placed.append(other)
                    evaluated.add(other["slug"])
                    stats["other_source_same_venue_joined"] += 1
            if len(rows) > 1:
                kept = kept_record(rows, unique_street, hours)
                marks.update({r["slug"]: kept["slug"] for r in rows if r is not kept})
    # Recompute markers only for records this run evaluated; others keep
    # theirs unless the kept record vanished or became a copy itself.
    # Copies merged by export_static.soft_merge_markers (any source) stay merged.
    by_slug = {row["slug"]: row for row in output}
    def twin_marker(row):
        kept = by_slug.get(row.get("duplicato_di"))
        return row["duplicato_di"] if kept and same_market(kept, row) else ""
    wanted = {row["slug"]: marks.get(row["slug"]) or twin_marker(row) if row["slug"] in evaluated
              else row.get("duplicato_di", "") for row in output}
    for sid, kept in wanted.items():
        if kept and wanted.get(kept, "x"):
            wanted[sid] = ""
    marker_changes = []
    for row in output:
        want = wanted[row["slug"]]
        if want != row.get("duplicato_di", ""):
            if want:
                row["duplicato_di"] = want
            else:
                del row["duplicato_di"]
            marker_changes.append({"id": row["slug"], "duplicato_di": want})
    stats["duplicate_copies_marked"] = len(marks)
    stats["duplicate_marker_changes"] = len(marker_changes)
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
        if delta and not delta.issubset(set(FIELDS)|{"fonti","riscontri_campi","duplicato_di"}):
            raise ValueError("Bulk Happings enrichment modified protected fields")
    return output,{"schema":1,"date":today.isoformat(),"publisher":"happings.com",
                   "snapshot_pages_checked":stats["weekly_pages"],
                   "counts":dict(sorted(stats.items())),
                   "holds":dict(sorted(holds.items())),
                   "changes":changes,"confirmations":confirmations,
                   "duplicate_markers":marker_changes,
                   "existing_ids_removed":0,
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
