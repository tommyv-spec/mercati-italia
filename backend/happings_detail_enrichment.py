"""Match Happings detail pages to identities and retain their complete facts.

The detail's explicit dates are publisher reports, not forecasts or human
confirmations. Existing identities are preserved. Distinct new venues can be
admitted only when explicitly enabled by the surrounding DEV pipeline.
"""
from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections import Counter
from copy import deepcopy
from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlsplit

from field_evidence import (FIELDS, as_day, clean_receipts, identity, make_receipt,
                            managed_update_allowed, mark_managed_fields,
                            retire_superseded_receipts)
from source_calendar import (DETAIL_FIELDS, MANAGER, clean_source_calendar,
                             clean_source_detail, detail_url, source_calendar_dates)

PUBLISHER = "happings.com"
SOURCE_NAME = "Happings — scheda evento (informazioni riportate dalla fonte)"
MAX_PAGES = 128
MAX_MARKETS = 100_000
MAX_NEW_MARKETS = 64
MAX_CHANGED_MARKETS = 2000
MUNICIPALITIES_FILE = Path(__file__).resolve().parent / "data/istat-comuni-2026.json"
WEEKDAYS = ("lunedi", "martedi", "mercoledi", "giovedi", "venerdi", "sabato", "domenica")
MUTABLE_FIELDS = {"indirizzo", "orario_testo", "ricorrenza_testo", "riscontri_campi",
                  "fonti", "calendario_fonte", "dettaglio_fonte", "date", "date_quality",
                  "proiezione_regola", "proiezione_generata_il", "proiezione_fonte"}


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
                                     separators=(",", ":")).encode("utf-8")).hexdigest()


def fold(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    return " ".join(re.findall(r"[a-z0-9]+", "".join(
        char for char in text.casefold() if not unicodedata.combining(char))))


def _name(value):
    return " ".join(word for word in fold(value).split() if word not in {
        "a", "ad", "di", "da", "del", "della", "dello", "dell", "dei", "degli",
        "delle", "al", "alla", "nel", "in", "il", "lo", "la", "i", "gli", "le"})


def _distinctive_name(value, city):
    words = set(_name(value).split()) - set(fold(city).split())
    return bool(words - {"mercato", "mercati", "mercatino", "mercatini",
                         "settimanale", "settimanali", "mattina", "mattino", "pomeriggio", "sera",
                         *WEEKDAYS})


def _specific_address(value):
    # Reuse the existing reviewed street rule without introducing an export
    # import cycle: this is called only during enrichment, never normalizing.
    from stored_market_sibling_proposals import safe_stored_street
    return isinstance(value, str) and len(value) <= 300 and safe_stored_street(value)


@lru_cache(maxsize=1)
def _municipalities():
    from municipality_reconciliation import trusted_municipalities
    reference = trusted_municipalities(json.loads(MUNICIPALITIES_FILE.read_text("utf-8")))
    result = {}
    for region, cities in reference.items():
        for name, province in cities.values():
            result.setdefault(fold(name), []).append((name, province, region))
    return result


def geography(event):
    location = event.get("location")
    if not isinstance(location, dict) or location.get("country") not in (None, "", "IT", "Italia", "Italy"):
        return None
    city, region, province = (location.get(key) for key in ("city", "region", "province"))
    if not isinstance(city, str) or not city.strip() or not (region or province):
        return None
    matches = [row for row in _municipalities().get(fold(city), [])
               if (not region or fold(row[2]) == fold(region))
               and (not province or fold(row[1]) == fold(province))]
    return matches[0] if len(matches) == 1 else None


def _url(document):
    source = document.get("source") or {}
    return source.get("final_url") or source.get("requested_url")


def _page_identity(row, url):
    if row.get("url_fonte") == url:
        return True
    # A retained, identity-bound proof is stronger than an arbitrary link in
    # fonti. Its valid shape is checked separately before it can match.
    detail = row.get("dettaglio_fonte")
    return bool(isinstance(detail, dict) and detail.get("url") == url
                and detail.get("mercato") == identity(row) and detail.get("gestore") == MANAGER)


def _days(row):
    from recurrence_refresh import explicit_rule
    rule = explicit_rule(row.get("ricorrenza_testo"))
    if isinstance(rule, dict) and rule.get("kind") == "weekly":
        return set(rule.get("weekdays") or [])
    return set()


def _event_days(event):
    return {as_day(item.get("date")).weekday() for item in event.get("occurrences") or []
            if isinstance(item, dict) and as_day(item.get("date"))}


def _nominal_days(event):
    text = fold(str(event.get("name") or "") + " " + str(event.get("recurrence_text") or ""))
    explicit = {index for index, day in enumerate(WEEKDAYS) if re.search(r"\b" + day + r"\b", text)}
    days = _event_days(event)
    if explicit:
        qualifiers = fold(" ".join(str(event.get(key) or "") for key in (
            "description", "hours_qualifications", "conditions", "calendar_notes")))
        extra_dates_explained = bool(re.search(
            r"\b(?:straordinari[oaie]|eccezion\w*|anticipat[oaie]|posticipat[oaie])\b", qualifiers))
        return explicit if days <= explicit or extra_dates_explained else set()
    return days if len(days) == 1 else set()


def _street_same(left, right):
    # Punctuation in house numbers matters: 64/65 must not equal 6465 or
    # 64-65. Only case, accents, whitespace and a separating comma differ.
    def key(value):
        value = unicodedata.normalize("NFKD", str(value or "")).casefold()
        value = "".join(c for c in value if not unicodedata.combining(c))
        return " ".join(value.replace(",", " ").split())
    return bool(key(left) and key(left) == key(right))


def _matches(base, document, geo, today):
    event, url = document["event"], _url(document)
    city, province, region = geo
    street = (event.get("location") or {}).get("street_address")
    days = _event_days(event)
    nominal_days = _nominal_days(event)
    source_category = _category(event)
    exact, possible = [], []
    for row in base:
        source_links = row.get("fonti") if isinstance(row.get("fonti"), list) else []
        mentions_url = (_page_identity(row, url) or any(
            isinstance(link, dict) and link.get("url") == url for link in source_links))
        if (fold(row.get("citta")) != fold(city) or row.get("provincia") != province
                or fold(row.get("regione")) != fold(region)):
            if mentions_url:
                possible.append(row)
            continue
        same_name = _name(row.get("nome_originale") or row.get("nome")) == _name(event.get("name"))
        same_street = _street_same(row.get("indirizzo"), street)
        row_days = _days(row)
        compatible_days = bool(nominal_days and row_days and nominal_days <= row_days)
        generic_names = (not _distinctive_name(row.get("nome"), city)
                         and not _distinctive_name(event.get("name"), city))
        same_generic = generic_names and same_street and compatible_days
        # Weak overlap may block admitting a duplicate, but never permits
        # assigning fields. A published compound street can contain the
        # exact source venue, and generic weekly titles can differ while
        # naming the same weekday market with an unresolved venue label.
        source_street_key = fold(street)
        compound_street = bool(len(source_street_key) >= 8 and re.search(
            r"\b" + re.escape(source_street_key) + r"\b", fold(row.get("indirizzo"))))
        same_type = bool(source_category and source_category != "misto" and
                         (row.get("categoria") == source_category or
                          source_category == "antiquariato" and "antiquar" in fold(row.get("nome"))))
        observed_page = _page_identity(row, url) and (
            row.get("url_fonte") == url or clean_source_detail(row.get("dettaglio_fonte"), row, today=today))
        if (mentions_url or observed_page or same_name or same_street and bool(days & row_days)
                or generic_names and compatible_days or compound_street and same_type):
            possible.append(row)
        if not same_name and not same_generic:
            continue
        if row_days and days and not compatible_days:
            continue
        if str(row.get("indirizzo") or "").strip() and not same_street:
            # A changed venue still needs an existing managed receipt before
            # reassignment; it cannot justify adding a duplicate venue.
            if not observed_page:
                continue
        if observed_page or same_generic or (same_name and _distinctive_name(event.get("name"), city)
                             and (same_street or compatible_days)) or (
                same_name and same_street and compatible_days):
            exact.append(row)
    if len(exact) == 1 and all(row["slug"] == exact[0]["slug"] for row in possible):
        return exact[0], "exact_page" if _page_identity(exact[0], url) else "name_place_schedule", possible
    return None, "ambiguous_existing_identity" if possible else "new_source_venue", possible


def _provenance(row, document, read_on):
    source = document["source"]
    url = _url(document)
    def source_date(key):
        value = source.get(key)
        if not isinstance(value, str):
            return ""
        try:
            day = datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return ""
        if day > read_on:
            raise ValueError("Publisher metadata date is later than its observed read")
        return day.isoformat()
    return {"schema": 1, "gestore": MANAGER, "mercato": identity(row),
            "url": url, "url_richiesto": source["requested_url"],
            "fonte_id": "happings-detail-" + hashlib.sha256(url.encode()).hexdigest()[:32],
            "letto_il": read_on.isoformat(), "fonte_aggiornata_il": source_date("modified_at"),
            "fonte_pubblicata_il": source_date("published_at"),
            "sha256": source["html_sha256"]}


def _detail_and_calendar(row, document, read_on, today):
    provenance = _provenance(row, document, read_on)
    event = document["event"]
    detail = clean_source_detail({**provenance, "evento": {
        key: deepcopy(event[key]) for key in DETAIL_FIELDS if key in event}}, row, today=today)
    if detail is None:
        raise ValueError("Publisher detail facts exceed the reviewed schema")
    calendar = None
    if event.get("occurrences") and event.get("calendar_complete") is True:
        calendar = clean_source_calendar({**provenance,
            "occorrenze": deepcopy(event["occurrences"]),
            "intervalli": deepcopy(event.get("date_intervals") or []),
            "ambito_calendario": event.get("calendar_scope"),
            "intervallo_edizione": deepcopy(event.get("edition_interval"))}, row, today=today)
        if calendar is None:
            raise ValueError("Publisher occurrence list is invalid or incomplete")
    return detail, calendar


def _ordered(row, provenance, today):
    previous = [clean_source_detail(row.get("dettaglio_fonte"), row, today=today),
                clean_source_calendar(row.get("calendario_fonte"), row, today=today)]
    previous.extend(receipt for receipt in clean_receipts(row.get("riscontri_campi"), row, today=today)
                    if receipt.get("url") == provenance["url"])
    for item in previous:
        if not item or item.get("url") != provenance["url"]:
            continue
        if (item["letto_il"] > provenance["letto_il"]
                or item["letto_il"] == provenance["letto_il"] and item["sha256"] != provenance["sha256"]
                or item.get("fonte_aggiornata_il") and (
                    not provenance.get("fonte_aggiornata_il") or
                    provenance["fonte_aggiornata_il"] < item["fonte_aggiornata_il"])):
            return False
    return True


def _receipt(row, values, provenance):
    return make_receipt({**row, **values}, values=values,
        source_url=provenance["url"], source_name=SOURCE_NAME,
        source_id=provenance["fonte_id"], source_row=provenance["fonte_id"],
        read_on=provenance["letto_il"], source_updated_on=provenance["fonte_aggiornata_il"],
        source_sha256=provenance["sha256"], scope="pagina",
        method="pagina_primaria_revisionata" if row.get("fonte") == PUBLISHER else "sede_giorno_provincia",
        fingerprint_kind="html_bytes")


def _apply_existing(row, document, read_on, today):
    result, held = deepcopy(row), []
    detail, calendar = _detail_and_calendar(row, document, read_on, today)
    if not _ordered(row, detail, today):
        return result, ["source_version_ordering_not_proven"]
    event = document["event"]
    if event.get("occurrences") and event.get("calendar_complete") is not True:
        held.append("source_calendar_is_partial")
    proposed = {"indirizzo": (event.get("location") or {}).get("street_address"),
                "orario_testo": event.get("hours_text"),
                "ricorrenza_testo": event.get("recurrence_text")}
    values, changed = {}, []
    primary = row.get("fonte") == PUBLISHER
    street = proposed["indirizzo"]
    if (_specific_address(street) and str(row.get("indirizzo") or "").strip()
            and not _street_same(row["indirizzo"], street)):
        proof = _receipt(row, {"indirizzo": street}, detail)
        if (not primary or row.get("verificato_il") or row.get("position_quality") == "precisa"
                or not managed_update_allowed(row, proof, "indirizzo", manager=MANAGER, today=today)):
            # Avoid mixing the hours/calendar of a newly reported place with
            # an older saved place that this engine is not allowed to change.
            return result, ["source_address_conflicts_with_unowned_or_verified_venue"]
    for field, value in proposed.items():
        if not isinstance(value, str) or not value.strip() or len(value) > FIELDS[field]:
            continue
        if field == "indirizzo" and not _specific_address(value):
            continue
        current = str(row.get(field) or "")
        equal = _street_same(current, value) if field == "indirizzo" else current == value
        if equal:
            values[field] = current
            continue
        if field == "ricorrenza_testo" and not calendar:
            held.append("recurrence_requires_retained_source_calendar")
            continue
        if not primary:
            held.append("secondary_source_cannot_assign_" + field)
            continue
        receipt = _receipt(row, {field: value}, detail)
        managed = managed_update_allowed(row, receipt, field, manager=MANAGER, today=today)
        if (row.get("verificato_il") or field == "indirizzo" and row.get("position_quality") == "precisa"
                or current.strip() and not managed):
            held.append("existing_unowned_or_verified_" + field)
            continue
        values[field] = value
        result[field] = value
        changed.append(field)
    if values:
        receipt = _receipt(result, values, detail)
        if changed:
            receipt = mark_managed_fields(receipt, changed, manager=MANAGER, previous=row)
        previous = retire_superseded_receipts(row, receipt, today=today)
        result["riscontri_campi"] = clean_receipts([*previous, receipt], result, today=today)
        if not any(item.get("url") == detail["url"] and item.get("sha256") == detail["sha256"]
                   and all(item.get("valori", {}).get(key) == values[key] for key in values)
                   for item in result["riscontri_campi"]):
            raise ValueError("Publisher values lost their exact field proof")
    result["dettaglio_fonte"] = detail
    if calendar and primary:
        previous = clean_source_calendar(row.get("calendario_fonte"), row, today=today)
        owned = bool(previous and previous["url"] == calendar["url"]
                     and set(row.get("date") or []) <= {item["date"] for item in previous["occorrenze"]})
        if (previous and previous["ambito_calendario"] == "explicit_visible_list"
                and calendar["ambito_calendario"] != "explicit_visible_list"):
            held.append("calendar_source_scope_became_partial")
        elif row.get("verificato_il") or row.get("date_quality") == "confermata" or (
                row.get("date_quality") == "riportata" and not owned):
            held.append("existing_unowned_or_confirmed_calendar")
        else:
            result["calendario_fonte"] = calendar
            result["date"] = source_calendar_dates(calendar, result, today=today)
            result["date_quality"] = "riportata" if result["date"] else "sconosciuta"
            result["proiezione_regola"] = None
            result["proiezione_generata_il"] = ""
            result["proiezione_fonte"] = ""
    links = deepcopy(row.get("fonti") or [])
    if not isinstance(links, list) or any(not isinstance(item, dict) for item in links):
        raise ValueError("Existing source list is invalid")
    new_link = {"nome": SOURCE_NAME, "url": detail["url"]}
    if new_link not in links:
        links.append(new_link)
    result["fonti"] = links
    return result, held


def stable_id(url):
    if not detail_url(url):
        raise ValueError("Unreviewed Happings detail URL")
    name = urlsplit(url).path.rstrip("/").rsplit("/", 1)[1]
    return "happings-" + name[:82].rstrip("-") + "-" + hashlib.sha256(url.encode()).hexdigest()[:12]


def _category(event):
    category = fold(event.get("category"))
    name = fold(event.get("name"))
    description = fold(event.get("description"))
    # These are source taxonomy labels observed in market detail templates.
    # A financial-market talk or a concert inside a Christmas market has a
    # perfectly valid Event schema, venue and time, but is not a market.
    market_categories = {"mercati", "mercatini", "mercatini dell antiquariato",
                         "mercatini di antiquariato", "mercati contadini",
                         "enogastronomia", "shopping", "natale"}
    if category not in market_categories or not re.search(r"\bmercat(?:o|i|ino|ini)\b", name):
        return None
    if re.search(r"\b(?:concerto|concerti|spettacolo|spettacoli|conferenza|convegno|incontro|talk)\b", name):
        return None
    if category == "natale" and (":" in str(event.get("name") or "") or any(
            phrase in description for phrase in ("fa parte del mercatino", "tipologia incontri",
                "coro giovanile", "banda musicale", "concerto", "si esibiscono"))):
        return None
    text = name + " " + category
    if any(word in text for word in ("campagna amica", "contadino", "contadini", "alimentare")):
        return "alimentare"
    if "antiquar" in text:
        return "antiquariato"
    if "artigian" in text:
        return "artigianato"
    if "usato" in text:
        return "usato"
    return "misto"


def _new_market(document, geo, read_on, today):
    event, url = document["event"], _url(document)
    city, province, region = geo
    street = (event.get("location") or {}).get("street_address")
    category = _category(event)
    if not category or not _specific_address(street):
        return None, "new_venue_requires_market_type_and_specific_address"
    if not isinstance(event.get("name"), str) or not 3 <= len(event["name"]) <= 160:
        return None, "new_venue_name_unbounded"
    hours = event.get("hours_text") or ""
    recurrence = event.get("recurrence_text") or ""
    if not isinstance(hours, str) or len(hours) > FIELDS["orario_testo"]:
        return None, "new_venue_hours_unbounded"
    # Recurrence is preserved as source prose only. No calendar projection
    # is needed or authorized when the page enumerates its occurrences.
    if not isinstance(recurrence, str) or len(recurrence) > FIELDS["ricorrenza_testo"]:
        recurrence = ""
    row = {"slug": stable_id(url), "nome": event["name"], "citta": city,
           "provincia": province, "regione": region, "indirizzo": street,
           "lat": None, "lng": None, "position_quality": "sconosciuta",
           "categoria": category, "tags": [], "status": "non_confermato",
           "orario_testo": hours, "ricorrenza_testo": recurrence,
           "descrizione": str(event.get("description") or "")[:900],
           "date": [], "date_quality": "sconosciuta",
           "proiezione_regola": None, "proiezione_generata_il": "", "proiezione_fonte": "",
           "confidence": 0, "fonte": PUBLISHER, "url_fonte": url,
           "fonti": [{"nome": SOURCE_NAME, "url": url}], "verificato_il": "",
           "aggiornato_il": "", "fonte_letta_il": read_on.isoformat(),
           "fonte_aggiornata_il": "", "importato_il": today.isoformat()}
    detail, calendar = _detail_and_calendar(row, document, read_on, today)
    if not calendar:
        return None, "new_venue_requires_explicit_source_dates"
    dates = source_calendar_dates(calendar, row, today=today)
    if not dates:
        return None, "new_venue_has_no_upcoming_source_date"
    row["dettaglio_fonte"], row["calendario_fonte"] = detail, calendar
    row["fonte_aggiornata_il"] = detail["fonte_aggiornata_il"]
    row["date"], row["date_quality"] = dates, "riportata"
    values = {field: row[field] for field in FIELDS if row.get(field)}
    receipt = mark_managed_fields(_receipt(row, values, detail), values, manager=MANAGER)
    row["riscontri_campi"] = [receipt]
    return row, None


def _read_day(page, today):
    value = page.get("read_on")
    timestamp = page.get("fetched_at") or page.get("captured_at")
    if value is None and isinstance(timestamp, str):
        try:
            stamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("Naive publisher acquisition timestamp")
            value = stamp.date().isoformat()
        except ValueError:
            raise ValueError("Invalid publisher acquisition timestamp") from None
    read = as_day(value)
    if not read or read > today or (today - read).days > 45:
        raise ValueError("Missing, future or expired publisher read date")
    return read


def _evaluate_document(result, by_id, touched, document, read_on, today, report, outcome):
    """All source-specific failures are caught before a result row is replaced."""
    event = document.get("event") or {}
    if _category(event) is None:
        outcome["reason"] = "source_category_or_event_is_not_a_market"
        return
    geo = geography(event)
    if geo is None:
        outcome["reason"] = "source_geography_not_exact_istat_identity"
        return
    row, match, possible = _matches(result, document, geo, today)
    outcome["matching"] = match
    outcome["possible_market_ids"] = [item["slug"] for item in possible]
    if row and row["slug"] in touched:
        outcome["reason"] = "more_than_one_detail_for_existing_identity"
    elif row:
        updated, holds = _apply_existing(row, document, read_on, today)
        outcome.update(market_id=row["slug"], field_holds=holds, status="matched", reason=None)
        touched.add(row["slug"])
        if updated != row:
            fields = sorted(key for key in set(row) | set(updated) if row.get(key) != updated.get(key))
            report["changes"].append({"market_id": row["slug"], "source_url": _url(document),
                "before_sha256": digest(row), "after_sha256": digest(updated),
                "fields": fields, "applied": report["apply"]})
            if report["apply"]:
                result[by_id[row["slug"]]] = updated
                report["changed_existing_ids"].append(row["slug"])
    elif possible:
        outcome["reason"] = match
    else:
        candidate, reason = _new_market(document, geo, read_on, today)
        if candidate is None:
            outcome["reason"] = reason
        elif candidate["slug"] in by_id:
            outcome["reason"] = "source_id_collision"
        else:
            report["candidates"].append(candidate)
            outcome.update(status="new_venue_candidate", market_id=candidate["slug"],
                           reason=None if report["admit_new"] else "new_venue_admission_disabled")
            if report["apply"] and report["admit_new"]:
                if len(report["new_market_ids"]) >= report["max_new"]:
                    outcome.update(status="held", reason="new_venue_batch_limit")
                    return
                by_id[candidate["slug"]] = len(result)
                result.append(candidate)
                touched.add(candidate["slug"])
                report["new_market_ids"].append(candidate["slug"])
                outcome["status"] = "new_venue_admitted"


def preview(base, pages, *, today, apply=False, admit_new=False, max_new=32):
    """Parse observed bytes, update exact existing matches, and stage new venues."""
    if (not isinstance(today, date) or not isinstance(base, list) or len(base) > MAX_MARKETS
            or not isinstance(pages, list) or len(pages) > MAX_PAGES
            or type(apply) is not bool or type(admit_new) is not bool
            or type(max_new) is not int or not 1 <= max_new <= MAX_NEW_MARKETS):
        raise ValueError("Invalid Happings detail batch")
    ids = [row.get("slug") if isinstance(row, dict) else None for row in base]
    if any(not isinstance(sid, str) or not sid for sid in ids) or len(ids) != len(set(ids)):
        raise ValueError("Existing catalogue identities are missing or duplicated")
    from happings_detail_layout import parse_detail
    report = {"schema": 1, "publisher": PUBLISHER, "date": today.isoformat(),
              "apply": apply, "admit_new": admit_new, "max_new": max_new, "input_sha256": digest(base),
              "source_pages": [], "documents": [], "outcomes": [], "changes": [],
              "new_market_ids": [], "changed_existing_ids": [], "candidates": [],
              "individually_confirmed": False, "coordinates_assigned": 0}
    result = deepcopy(base)
    by_id = {row["slug"]: index for index, row in enumerate(result)}
    seen, touched, counters = set(), set(), Counter()
    for page in pages:
        if not isinstance(page, dict):
            raise ValueError("Invalid Happings detail page")
        read_on = _read_day(page, today)
        requested, final, html = (page.get(key) for key in ("requested_url", "final_url", "html"))
        if not detail_url(requested) or not detail_url(final or requested):
            raise ValueError("Out-of-scope Happings detail page")
        if not isinstance(html, bytes) or not 100 <= len(html) <= 2_600_000:
            raise ValueError("Missing or unbounded Happings detail bytes")
        try:
            document = parse_detail(html, requested_url=requested, final_url=final or requested)
        except ValueError:
            document = {"schema": 1, "status": "layout_changed", "event": {}, "conflicts": [],
                "source": {"requested_url": requested, "final_url": final or requested,
                           "canonical_url": None, "html_sha256": hashlib.sha256(html).hexdigest(),
                           "bytes": len(html)}, "warnings": ["source_detail_parse_failed"]}
        url = _url(document)
        if url in seen:
            raise ValueError("Repeated canonical detail in one source batch")
        seen.add(url)
        page_proof = {**deepcopy(document.get("source") or {}), "read_on": read_on.isoformat(),
                      "status": document.get("status")}
        report["source_pages"].append(page_proof)
        report["documents"].append({"read_on": read_on.isoformat(), "parsed": deepcopy(document)})
        outcome = {"url": url, "read_on": read_on.isoformat(), "status": "held",
                   "market_id": None, "reason": None, "field_holds": []}
        if document.get("status") != "parsed" or document.get("conflicts"):
            outcome["reason"] = "source_layout_or_content_conflict"
            outcome["conflicts"] = deepcopy(document.get("conflicts") or [])
        else:
            try:
                _evaluate_document(result, by_id, touched, document, read_on, today, report, outcome)
            except ValueError as error:
                outcome.update(status="held", market_id=None,
                               reason="source_detail_not_representable", error_type=type(error).__name__)
        counters[outcome["status"]] += 1
        if outcome["reason"]:
            counters[outcome["reason"]] += 1
        report["outcomes"].append(outcome)
    if len(report["changed_existing_ids"]) > MAX_CHANGED_MARKETS:
        raise ValueError("Happings detail enrichment batch exceeded")
    report["counts"] = dict(sorted(counters.items()))
    report["output_sha256"] = digest(result)
    verify_changes(base, result, report, today=today)
    from happings_field_coverage import aggregate_coverage, detail_page_coverage
    coverage_before = {row["slug"]: row for row in base}
    coverage_after = {row["slug"]: row for row in result}
    report["field_coverage"] = aggregate_coverage([
        detail_page_coverage(page["html"],document["parsed"],outcome,
                             before=coverage_before,after=coverage_after,applied=apply)
        for page,document,outcome in zip(pages,report["documents"],report["outcomes"])])
    return result, report


def verify_changes(before, after, report, *, today):
    if (not isinstance(report, dict) or report.get("schema") != 1
            or report.get("publisher") != PUBLISHER or report.get("date") != today.isoformat()
            or type(report.get("apply")) is not bool or type(report.get("admit_new")) is not bool
            or type(report.get("max_new")) is not int or not 1 <= report["max_new"] <= MAX_NEW_MARKETS
            or report.get("individually_confirmed") is not False or report.get("coordinates_assigned") != 0):
        raise ValueError("Invalid detail audit policy or confirmation claim")
    if report.get("input_sha256") != digest(before) or report.get("output_sha256") != digest(after):
        raise ValueError("Happings detail candidate changed after its source audit")
    documents, pages, outcomes = (report.get(key) for key in ("documents", "source_pages", "outcomes"))
    if (not all(isinstance(items, list) for items in (documents, pages, outcomes))
            or not len(documents) == len(pages) == len(outcomes) <= MAX_PAGES):
        raise ValueError("Detail results lost their parsed source pages")
    # Reconstruct the allowed changes from retained parsed source facts. A
    # caller cannot make an altered value pass by recomputing result hashes,
    # changing a receipt, or attaching another page's calendar to the row.
    expected = deepcopy(before)
    replay_ids = {row["slug"]: index for index, row in enumerate(expected)}
    replay = {"apply": report["apply"], "admit_new": report["admit_new"], "max_new": report["max_new"],
              "changes": [], "new_market_ids": [], "changed_existing_ids": [], "candidates": []}
    replay_counts, seen_urls, touched = Counter(), set(), set()
    for document_record, page, actual_outcome in zip(documents, pages, outcomes):
        if not isinstance(document_record, dict) or set(document_record) != {"read_on", "parsed"}:
            raise ValueError("Detail source lacks its acquisition date")
        document = document_record["parsed"]
        read_on = as_day(document_record["read_on"])
        if (not isinstance(document, dict) or not read_on or read_on > today
                or (today - read_on).days > 45 or not isinstance(document.get("source"), dict)):
            raise ValueError("Detail source acquisition date or content is invalid")
        source = document["source"]
        url = _url(document)
        if (not detail_url(url) or not detail_url(source.get("requested_url")) or url in seen_urls
                or not re.fullmatch(r"[0-9a-f]{64}", str(source.get("html_sha256") or ""))
                or type(source.get("bytes")) is not int or not 100 <= source["bytes"] <= 2_600_000
                or page != {**source, "read_on": read_on.isoformat(), "status": document.get("status")}):
            raise ValueError("Detail source proof is not bound to the observed source page")
        seen_urls.add(url)
        outcome = {"url": url, "read_on": read_on.isoformat(), "status": "held",
                   "market_id": None, "reason": None, "field_holds": []}
        if document.get("status") != "parsed" or document.get("conflicts"):
            outcome["reason"] = "source_layout_or_content_conflict"
            outcome["conflicts"] = deepcopy(document.get("conflicts") or [])
        else:
            try:
                _evaluate_document(expected, replay_ids, touched, document, read_on, today, replay, outcome)
            except ValueError as error:
                outcome.update(status="held", market_id=None,
                               reason="source_detail_not_representable", error_type=type(error).__name__)
        if outcome != actual_outcome:
            raise ValueError("Detail matching outcome differs from its parsed source facts")
        replay_counts[outcome["status"]] += 1
        if outcome["reason"]:
            replay_counts[outcome["reason"]] += 1
    if expected != after or any(replay[key] != report.get(key) for key in (
            "changes", "new_market_ids", "changed_existing_ids", "candidates")) or dict(
                sorted(replay_counts.items())) != report.get("counts"):
        raise ValueError("Detail candidate cannot be reconstructed from the observed source facts")
    old = {row["slug"]: row for row in before}
    new = {row["slug"]: row for row in after}
    if len(new) != len(after) or not set(old) <= set(new):
        raise ValueError("Happings detail enrichment removed or merged existing identities")
    added = set(new) - set(old)
    if added != set(report.get("new_market_ids") or []) or added and not (
            report.get("apply") is True and report.get("admit_new") is True):
        raise ValueError("Happings detail admission lacks its enabled report")
    changes = {item["market_id"]: item for item in report.get("changes") or [] if item.get("applied")}
    altered = {sid for sid in old if old[sid] != new[sid]}
    if altered != set(changes) or altered != set(report.get("changed_existing_ids") or []):
        raise ValueError("Existing detail changes have no exact source report")
    for sid in altered:
        left, right = old[sid], new[sid]
        fields = {key for key in set(left) | set(right) if left.get(key) != right.get(key)}
        proof = changes[sid]
        if (fields - MUTABLE_FIELDS or proof.get("before_sha256") != digest(left)
                or proof.get("after_sha256") != digest(right) or sorted(fields) != proof.get("fields")
                or not clean_source_detail(right.get("dettaglio_fonte"), right, today=today)):
            raise ValueError("Happings detail altered identity or lost source facts")
        for field in ("indirizzo", "orario_testo", "ricorrenza_testo"):
            if field in fields and not any(
                    field in receipt.get("campi_gestiti", [])
                    and receipt.get("gestore_campi") == MANAGER
                    and receipt.get("valori", {}).get(field) == right.get(field)
                    for receipt in clean_receipts(right.get("riscontri_campi"), right, today=today)):
                raise ValueError("Happings detail assignment lost its managed field proof")
    for sid in added:
        row = new[sid]
        if (sid != stable_id(row.get("url_fonte")) or row.get("fonte") != PUBLISHER
                or row.get("verificato_il") or row.get("status") != "non_confermato"
                or row.get("lat") is not None or row.get("lng") is not None
                or row.get("position_quality") != "sconosciuta"
                or row.get("date_quality") != "riportata"
                or not _specific_address(row.get("indirizzo"))
                or not clean_source_detail(row.get("dettaglio_fonte"), row, today=today)
                or row.get("date") != source_calendar_dates(row.get("calendario_fonte"), row, today=today)
                or not row.get("date")):
            raise ValueError("New Happings venue lost its exact source identity or calendar")
    return {"existing_ids_preserved": len(old), "new_market_ids": len(added),
            "changed_existing_ids": len(altered), "individually_confirmed": 0}


def cert_from_detail_evidence(evidence, *, today):
    """Carry only source proofs for independently admitted identities.

    The full detail diff is verified by the caller before this certificate is
    attached to another source's historical same-ID audit. Candidate bodies
    are deliberately omitted: the receiving guard must reconstruct them.
    """
    if not isinstance(evidence, dict) or not isinstance(today, date):
        raise ValueError("Invalid Happings admission evidence")
    ids = evidence.get("new_market_ids")
    if not isinstance(ids, list) or len(ids) != len(set(ids)) or len(ids) > MAX_NEW_MARKETS:
        raise ValueError("Unbounded or duplicated Happings admissions")
    if not ids:
        return None
    if (evidence.get("schema") != 1 or evidence.get("publisher") != PUBLISHER
            or evidence.get("date") != today.isoformat()
            or evidence.get("apply") is not True or evidence.get("admit_new") is not True
            or type(evidence.get("max_new")) is not int
            or not len(ids) <= evidence["max_new"] <= MAX_NEW_MARKETS):
        raise ValueError("Happings admissions lack an enabled bounded policy")
    documents, pages, outcomes = (evidence.get(k) for k in ("documents", "source_pages", "outcomes"))
    if (not all(isinstance(items, list) for items in (documents, pages, outcomes))
            or not len(documents) == len(pages) == len(outcomes) <= MAX_PAGES):
        raise ValueError("Happings admissions lost source observations")
    admissions = []
    for doc, page, outcome in zip(documents, pages, outcomes):
        if outcome.get("status") == "new_venue_admitted":
            if outcome.get("market_id") not in ids:
                raise ValueError("Unexpected Happings admission outcome")
            admissions.append({"market_id": outcome["market_id"],
                               "document": deepcopy(doc), "source_page": deepcopy(page)})
    if [item["market_id"] for item in admissions] != ids:
        raise ValueError("Happings admitted identities lost their source outcome")
    return {"schema": 1, "publisher": PUBLISHER, "date": today.isoformat(),
            "max_new": evidence["max_new"], "admissions": admissions}


def verify_source_admission_certificate(before, after, certificate, today):
    """Prove later source admissions, then return a strict same-ID cohort.

    No certificate preserves the historical guard's behavior. A certificate
    must explain every added identity and reproduce its entire normalized
    exported record from bound source facts. Existing rows stay in the cohort.
    """
    if certificate is None:
        return after, 0
    if (not isinstance(today, date) or not isinstance(before, list)
            or not isinstance(after, list) or len(before) > MAX_MARKETS
            or len(after) > MAX_MARKETS + MAX_NEW_MARKETS
            or not isinstance(certificate, dict) or set(certificate) != {
                "schema", "publisher", "date", "max_new", "admissions"}
            or certificate.get("schema") != 1 or certificate.get("publisher") != PUBLISHER
            or certificate.get("date") != today.isoformat()
            or type(certificate.get("max_new")) is not int
            or not 1 <= certificate["max_new"] <= MAX_NEW_MARKETS):
        raise ValueError("Invalid or stale Happings admission certificate")
    admissions = certificate.get("admissions")
    if not isinstance(admissions, list) or not 1 <= len(admissions) <= certificate["max_new"]:
        raise ValueError("Unbounded Happings admission certificate")
    old_ids = [row.get("slug") for row in before if isinstance(row, dict)]
    new_ids = [row.get("slug") for row in after if isinstance(row, dict)]
    claimed = [item.get("market_id") for item in admissions if isinstance(item, dict)]
    if (len(old_ids) != len(before) or len(new_ids) != len(after)
            or len(claimed) != len(admissions)
            or any(not isinstance(sid, str) or not sid for sid in old_ids + new_ids + claimed)
            or len(set(old_ids)) != len(old_ids) or len(set(new_ids)) != len(new_ids)
            or len(set(claimed)) != len(claimed) or set(old_ids) & set(claimed)
            or set(new_ids) != set(old_ids) | set(claimed)):
        raise ValueError("Happings certificate removed or failed to prove catalog identities")
    from export_static import normalize
    by_id = {row["slug"]: row for row in after}
    comparable = [row for row in after if row["slug"] not in set(claimed)]
    collision_rows = list(comparable)
    seen_urls = set()
    for admission in admissions:
        if set(admission) != {"market_id", "document", "source_page"}:
            raise ValueError("Unexpected Happings admission proof fields")
        record, page = admission["document"], admission["source_page"]
        if not isinstance(record, dict) or set(record) != {"parsed", "read_on"}:
            raise ValueError("Happings admission lost its source acquisition date")
        document, read_on = record["parsed"], _read_day(record, today)
        if (not isinstance(document, dict) or document.get("schema") != 1
                or document.get("status") != "parsed" or document.get("conflicts")
                or not isinstance(document.get("source"), dict)
                or not isinstance(document.get("event"), dict)):
            raise ValueError("Happings admission source is not a parsed market")
        source, url = document["source"], _url(document)
        if (not detail_url(url) or not detail_url(source.get("requested_url"))
                or source.get("canonical_url") != url or url in seen_urls
                or not re.fullmatch(r"[0-9a-f]{64}", str(source.get("html_sha256") or ""))
                or type(source.get("bytes")) is not int or not 100 <= source["bytes"] <= 2_600_000
                or page != {**source, "read_on": read_on.isoformat(), "status": "parsed"}
                or admission["market_id"] != stable_id(url)):
            raise ValueError("Happings admission detached from its observed source page")
        seen_urls.add(url)
        geo = geography(document["event"])
        if geo is None or _category(document["event"]) is None:
            raise ValueError("Happings admission lacks exact geography or market category")
        matched, _, possible = _matches(collision_rows, document, geo, today)
        if matched or possible:
            raise ValueError("Happings admission overlaps an existing market identity")
        expected, reason = _new_market(document, geo, read_on, today)
        if expected is None:
            raise ValueError("Happings admission has no complete source calendar: " + str(reason))
        normalized, error = normalize(expected, today)
        if error or normalized != by_id[admission["market_id"]]:
            raise ValueError("Happings exported admission differs from parsed source facts")
        # Later source pages must not create a second version of this venue;
        # the current candidate was excluded above, avoiding self-collision.
        collision_rows.append(normalized)
    return comparable, len(admissions)
