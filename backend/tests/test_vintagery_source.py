"""Vintagery browser snapshot: normalising, page facts, admission, re-read and fill.

Synthetic cards only; the committed snapshot is never read here.
"""
from copy import deepcopy
from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import editorial_discovery as discovery
import eventiesagre_detail_refresh as editorial
import vintagery_source as vg
from editorial_calendar_scope import KEY
from export_static import normalize
from field_evidence import clean_receipts
from recurrence_refresh import refresh_record
from test_eventiesagre_detail_refresh import row

TODAY = date(2026, 10, 20)
UUID = "30d6a0e2-fca1-4f5a-be10-038cd5c9672f"
URL = "https://vintagery.it/mercatini/" + UUID


def card(**changes):
    result = {"id": UUID, "url": URL, "read_on": "2026-10-20", "record": True,
              "name": "Mercatino dell'Antiquariato di Prova — Bologna", "city": "Bologna",
              "region": "Emilia-Romagna", "address": "Piazza Santo Stefano, 40125 Bologna (BO)",
              "schedule_notes": "Terza domenica del mese, esclusi luglio e agosto, 8:00-18:00",
              "frequency": "mensile", "start_date": "2026-11-15", "unconfirmed": False,
              "start_time": "08:00", "end_time": "18:00", "organizer": "Associazione Prova",
              "website": "", "instagram": "", "price_info": "Ingresso libero",
              "description": "Antiquariato e collezionismo in piazza.", "tags": ["antiquariato"],
              "verified_on": "2026-10-19", "status": "", "tips": "Arrivare presto."}
    result.update(changes)
    return result


def snapshot(*cards):
    days = [c["read_on"] for c in cards]
    return vg.validate_snapshot({"schema": 1, "publisher": vg.PUBLISHER, "index": vg.INDEX_URL,
                                 "read_from": min(days), "read_to": max(days), "cards": list(cards)})


def parsed(item, today=TODAY):
    return editorial.parse_document(vg.card_blob(item), requested_url=item["url"], today=today)


def elsewhere():
    return row(slug="mercato-altrove", nome="Mercato Di Altrove", citta="Rimini", provincia="RN",
               regione="Emilia-Romagna", url_fonte="https://www.eventiesagre.it/Mercatini_Vari/1_Altrove.html")


def admitted(snap, rows=None):
    rows = rows or [elsewhere()]
    observations = [{"read_on": p["read_on"], "parsed": editorial.parse_document(
        p["body"], requested_url=p["requested_url"], today=TODAY)}
        for p in vg.pages(rows, today=TODAY, limit=10, snapshot=snap)]
    config = discovery.configuration()
    result, report = discovery.admit(rows, observations, today=TODAY, config=config)
    discovery.verify_admissions(rows, result, report, today=TODAY, config=config)
    return result, report


class SnapshotTests(unittest.TestCase):
    def test_capture_keeps_records_counts_undated_pages_and_dates_the_check(self):
        raw = {UUID: {"id": UUID, "url": URL, "name": "X", "read_at": "2026-01-03T10:00:00Z",
                      "verified": "28 dicembre", "start_date": "2026-01-11", "tags": ["vintage"]},
               "8abfcc97-a7d4-40b0-bdf2-4d94262c1189": {
                   "url": "https://vintagery.it/mercatini/8abfcc97-a7d4-40b0-bdf2-4d94262c1189",
                   "title": "Hobbisti — Siracusa, orari e date | Vintagery", "parse_error": True,
                   "read_at": "2026-01-03T10:01:00Z"},
               "bad": {"url": "https://example.com/x", "read_at": "2026-01-03T10:00:00Z"}}
        snap, skipped = vg.normalize_capture(raw)
        first, undated = sorted(snap["cards"], key=lambda c: c["id"])
        self.assertEqual(skipped, {"invalid_card": 1, "page_without_market_fields": 1})
        self.assertEqual((first["verified_on"], first["read_on"], first["record"]), ("2025-12-28", "2026-01-03", True))
        self.assertEqual((undated["record"], undated["name"]), (False, "Hobbisti"))
        with self.assertRaises(ValueError):
            vg.validate_snapshot({**snap, "cards": [{**first, "html": "<p>"}]})

    def test_rule_hours_and_dates_are_kept_only_when_nothing_qualifies_them(self):
        self.assertEqual(vg.rule_text("Terza domenica del mese, esclusi luglio e agosto, 8:00-18:00")[0],
                         "Terza domenica del mese, esclusi luglio e agosto")
        self.assertEqual(vg.rule_text("Ogni martedì mattina")[0], "Ogni martedì")
        for notes in ("Terza domenica del mese, esclusi giugno, luglio e agosto. A dicembre 2026 anticipato a martedì 8",
                      "Domenica, solitamente prima domenica del mese",
                      "Prima domenica del mese. Sospensione estiva dal 1° luglio al 31 agosto",
                      "Date variabili. Nel 2026: 15 marzo, 2 giugno"):
            self.assertIsNone(vg.rule_text(notes)[0], notes)
        self.assertEqual(vg.hours_text(card())[0], "08:00–18:00")
        self.assertEqual(vg.hours_text(card(schedule_notes="Ogni giovedì. Inverno 8.30-17, estate 8.30-18"))[1],
                         "hours_seasonal_or_per_edition")
        self.assertEqual(vg.next_dates("Ogni seconda domenica. Prossime date: 8 novembre 2026, 13 dicembre 2026."),
                         ["2026-11-08", "2026-12-13"])
        self.assertEqual(vg.street_and_province("Piazza Santa Lucia, 96100 Siracusa (SR)", "Siracusa"),
                         ("Piazza Santa Lucia", "SR"))

    def test_page_facts_bind_the_town_and_never_report_an_unconfirmed_date(self):
        document = parsed(card())
        event = document["event"]
        self.assertEqual(document["status"], "parsed")
        self.assertEqual((event["name"], event["location"]["province"], event["location"]["address"]),
                         ("Mercatino dell'Antiquariato di Prova", "BO", "Piazza Santo Stefano"))
        self.assertEqual([o["date"] for o in event["occurrences"]], ["2026-11-15"])
        self.assertEqual(document["source"]["modified_at"], "2026-10-19")
        unconfirmed = parsed(card(unconfirmed=True))
        self.assertEqual(unconfirmed["event"]["occurrences"], [])
        self.assertIn("next_date_unconfirmed", unconfirmed["warnings"])
        listed = parsed(card(schedule_notes="Terza domenica del mese. Prossime date: 22 novembre 2026."))
        self.assertEqual(listed["conflicts"][0]["code"], "next_date_not_in_listed_dates")


class AdmissionTests(unittest.TestCase):
    def test_new_market_carries_page_evidence_reported_date_and_contacts(self):
        result, report = admitted(snapshot(card()))
        self.assertEqual(report["counts"], {"admitted": 1})
        new = result[-1]
        self.assertEqual((new["nome"], new["indirizzo"], new["orario_testo"], new["categoria"]),
                         ("Mercatino dell'Antiquariato di Prova", "Piazza Santo Stefano", "08:00–18:00", "antiquariato"))
        self.assertEqual(new["ricorrenza_testo"], "Terza domenica del mese, esclusi luglio e agosto")
        self.assertEqual(new["descrizione"], "Antiquariato e collezionismo in piazza.")
        self.assertEqual(new[KEY]["publisher"], vg.PUBLISHER)
        self.assertEqual(new[KEY]["hash_basis"], vg.HASH_BASIS)
        self.assertIn({"field": "organizer", "value": "Associazione Prova", "evidence": ["record.organizer"]},
                      new[KEY]["facts"]["source_rows"])
        # The page's rule is its calendar: predicted dates, the listed one among them.
        exported = normalize(refresh_record(new, TODAY)[0], TODAY)[0]
        self.assertEqual((exported["date"], exported["date_quality"]),
                         (["2026-11-15", "2026-12-20", "2027-01-17"], "prevista"))
        observed = report["documents"][0]
        discovery.check_exported_admission(exported, observed, new["slug"], today=TODAY, others=[exported])

    def test_predictions_follow_the_check_and_read_ages(self):
        result, _ = admitted(snapshot(card()))
        projected = refresh_record(result[-1], TODAY)[0]
        dates = lambda day: refresh_record(projected, day)[0]["date"]
        self.assertEqual(dates(date(2026, 12, 4))[:2], ["2026-12-20", "2027-01-17"])
        # Read 46 days ago: the page no longer supports predictions.
        self.assertEqual(dates(date(2026, 12, 5)), [])
        # A check date already over 180 days old at the read: only the listed date counts.
        result, _ = admitted(snapshot(card(verified_on="2026-04-01")))
        exported = normalize(refresh_record(result[-1], TODAY)[0], TODAY)[0]
        self.assertEqual((exported["date"], exported["date_quality"]), (["2026-11-15"], "riportata"))

    def test_a_date_off_the_rule_means_the_rule_is_not_taken(self):
        document = parsed(card(start_date="2026-11-22"))
        self.assertIsNone(document["event"]["recurrence_text"])
        self.assertIn("listed_date_not_on_rule", document["warnings"])

    def test_a_bounded_read_rotates_through_every_card(self):
        cards = [card(id=u, url="https://vintagery.it/mercatini/" + u) for u in (
            UUID, "8abfcc97-a7d4-40b0-bdf2-4d94262c1189", "b42af7e2-8c19-437e-9ee8-337deffe8697")]
        snap = snapshot(*cards)
        seen = {p["requested_url"] for day in (TODAY, date(2026, 10, 21))
                for p in vg.pages([elsewhere()], today=day, limit=2, snapshot=snap)}
        self.assertEqual(seen, {c["url"] for c in cards})
        self.assertEqual(len(vg.pages([elsewhere()], today=TODAY, limit=1000, snapshot=snap)), 3)

    def test_unconfirmed_dates_and_known_markets_are_held(self):
        # "Da confermare": the date is dropped, the stated rule still predicts.
        result, report = admitted(snapshot(card(unconfirmed=True)))
        self.assertEqual(report["counts"], {"admitted": 1})
        self.assertEqual(normalize(refresh_record(result[-1], TODAY)[0], TODAY)[0]["date"][:1], ["2026-11-15"])
        _, report = admitted(snapshot(card(unconfirmed=True, schedule_notes="Date variabili")))
        self.assertEqual(report["counts"], {"no_upcoming_date": 1})
        same = row(slug="prova-bologna", nome="Mercatino dell'Antiquariato di Prova", ricorrenza_testo="",
                   url_fonte="https://www.eventiesagre.it/Mercatini_Vari/2_Prova.html", categoria="antiquariato")
        _, report = admitted(snapshot(card()), rows=[same])
        self.assertEqual(report["counts"], {"same_name_in_town": 1})

    def test_own_cards_are_reread_only_from_a_newer_snapshot(self):
        result, _ = admitted(snapshot(card()))
        same, proof = vg.reread(result, today=TODAY, snapshot=snapshot(card()))
        self.assertEqual((same, proof["documents"]), (result, []))
        later = date(2026, 10, 21)
        newer = snapshot(card(read_on="2026-10-21", start_date="2026-12-20", verified_on="2026-10-21"))
        revised, report = vg.apply(result, today=later, snapshot=newer)
        vg.verify(result, revised, report, today=later, snapshot=newer)
        self.assertEqual(report["summary"]["own_cards_changed"], 1)
        self.assertEqual(revised[-1][KEY]["read_on"], "2026-10-21")
        self.assertEqual([o["date"] for o in revised[-1][KEY]["facts"]["occurrences"]], ["2026-12-20"])
        exported = [normalize(refresh_record(r, later)[0], later)[0] for r in revised]
        self.assertTrue(vg.verify_exported(exported, report, today=later)["release_safe"])
        self.assertEqual(exported[-1]["date"][:2], ["2026-11-15", "2026-12-20"])


class FillTests(unittest.TestCase):
    def market(self=None, **changes):
        return row(**{"slug": "prova-bologna", "nome": "Mercatino dell'Antiquariato di Prova",
                      "ricorrenza_testo": "mensile - terza domenica del mese, esclusi luglio e agosto",
                      "url_fonte": "https://www.eventiesagre.it/Mercatini_Vari/2_Prova.html",
                      "categoria": "antiquariato", **changes})

    def test_empty_fields_are_filled_and_the_same_rule_is_restated_with_receipts(self):
        before = [self.market(), elsewhere()]
        after, report = vg.apply(before, today=TODAY, snapshot=snapshot(card()))
        vg.verify(before, after, report, today=TODAY, snapshot=snapshot(card()))
        filled = after[0]
        self.assertEqual((filled["indirizzo"], filled["orario_testo"]), ("Piazza Santo Stefano", "08:00–18:00"))
        self.assertEqual(filled["ricorrenza_testo"], before[0]["ricorrenza_testo"])
        receipt = clean_receipts(filled["riscontri_campi"], filled, today=TODAY)[0]
        self.assertEqual((receipt["url"], receipt["letto_il"], receipt["fonte_aggiornata_il"]),
                         (URL, "2026-10-20", "2026-10-19"))
        self.assertEqual(set(receipt["valori"]), {"indirizzo", "orario_testo", "ricorrenza_testo"})
        self.assertEqual(receipt["campi_gestiti"], ["indirizzo", "orario_testo"])
        self.assertEqual(report["summary"]["markets_changed"], 1)
        vg.verify_exported([normalize(r, TODAY)[0] for r in after], report, today=TODAY)
        tampered = deepcopy(after)
        tampered[0]["nome"] = "Altro"
        with self.assertRaises(ValueError):
            vg.verify(before, tampered, report, today=TODAY, snapshot=snapshot(card()))

    def test_different_values_and_uncertain_matches_change_nothing(self):
        before = [self.market(orario_testo="09:00–13:00", indirizzo="Piazza Maggiore",
                              ricorrenza_testo="Ogni sabato")]
        after, report = vg.fill(before, today=TODAY, snapshot=snapshot(card()))
        self.assertEqual(after, before)
        self.assertEqual(report["summary"]["held_values_by_field"],
                         {"indirizzo": 1, "orario_testo": 1, "ricorrenza_testo": 1})
        twins = [self.market(), self.market(slug="prova-bologna-2", url_fonte="https://www.eventiesagre.it/Mercatini_Vari/3_Prova.html")]
        after, report = vg.fill(twins, today=TODAY, snapshot=snapshot(card()))
        self.assertEqual((after, report["summary"]["held_by_reason"]), (twins, {"several_matches": 1}))


PAGE = ("Salta al contenutoVintagery … No, grazie Mercatini/Toscana/CarraraantiquariatoMercatino di Prova "
        "Carrara, Toscana Torna a luglioRicordameloProssima aperturaTorna a luglioScheda verificata il 17 ottobre "
        "Come arrivareOrario09:00–19:00IngressoGratuitoDovePiazza Menconi, 54033 Carrara (MS)Indicazioni"
        "OrganizzatoreAssociazione Prova Orari e cadenzaOgni domenica di luglio e agosto. Edizione 2026: 14-16 dicembre."
        "Il mercatoAntiquariato sul mare.Questo weekend, qui vicino…Consiglio praticoArrivare presto.antiquariatoRecensioni")


class UndatedPageTests(unittest.TestCase):
    def test_the_visible_labels_give_the_card_fields(self):
        page = vg.page_card({"title": "Mercatino di Prova — Carrara, orari e date | Vintagery",
                             "page_text": PAGE, "tags": ["antiquariato"]}, "2026-10-20")
        self.assertEqual((page["name"], page["city"], page["region"], page["status"]),
                         ("Mercatino di Prova", "Carrara", "Toscana", "Torna a luglio"))
        self.assertEqual((page["start_time"], page["end_time"], page["price_info"], page["tips"]),
                         ("09:00", "19:00", "Gratuito", "Arrivare presto."))
        self.assertEqual((page["address"], page["organizer"], page["verified_on"]),
                         ("Piazza Menconi, 54033 Carrara (MS)", "Associazione Prova", "2026-10-17"))
        self.assertEqual(vg.written_dates(page["schedule_notes"], "2026-10-20"),
                         ["2026-12-14", "2026-12-15", "2026-12-16"])
        self.assertEqual(vg.written_dates("Esempi: 22 novembre 2026. Dal 1° giugno al 15 novembre 2026", "2026-10-20"), [])
        self.assertIsNone(vg.page_card({"title": "X — Y, orari e date | Vintagery", "page_text": "Categoria generale"}, "2026-10-20"))

    def test_an_undated_market_enters_with_its_own_status_and_no_date(self):
        undated = card(start_date="", schedule_notes="Date annunciate di volta in volta",
                       status="Date annunciate di volta in volta")
        result, report = admitted(snapshot(undated))
        self.assertEqual(report["counts"], {"admitted": 1})
        exported = normalize(refresh_record(result[-1], TODAY)[0], TODAY)[0]
        self.assertEqual(exported["date"], [])
        self.assertEqual([c["text"] for c in exported[KEY]["facts"]["conditions"]],
                         ["Prossima apertura: Date annunciate di volta in volta"])
        _, report = admitted(snapshot({**undated, "status": ""}))
        self.assertEqual(report["counts"], {"no_upcoming_date": 1})
        _, report = admitted(snapshot({**undated, "address": "Piazza A; in estate Piazza B, Bologna"}))
        self.assertEqual(report["counts"], {"source_conflict": 1})

    def test_a_frazione_is_its_comune_and_a_unique_town_beats_the_page_province(self):
        self.assertEqual(vg.resolve_town("Marina di Carrara", "Toscana",
                                         "Piazza Menconi, 54033 Marina di Carrara, Carrara (MS), Toscana, Italia", ""),
                         ("Carrara", "MS", "Marina di Carrara"))
        self.assertEqual(vg.resolve_town("Olbia", "Sardegna", "Via Cavour, Olbia (SS)", "SS"), ("Olbia", "OT", ""))
        self.assertEqual(vg.resolve_town("Reggio Emilia", "Emilia-Romagna", "Via Roma", "")[0], "Reggio nell'Emilia")


class ExtraFieldTests(unittest.TestCase):
    def test_entry_tips_and_tags_reach_new_and_matched_cards(self):
        result, _ = admitted(snapshot(card(price_info="Ingresso libero")))
        new = normalize(refresh_record(result[-1], TODAY)[0], TODAY)[0]
        self.assertEqual((new["ingresso"], new["consigli"], new["tags"]),
                         ("Ingresso libero", "Arrivare presto.", ["antiquariato"]))
        before = [FillTests.market(None, tags=["mercato"]), elsewhere()]
        after, report = vg.apply(before, today=TODAY, snapshot=snapshot(card()))
        vg.verify(before, after, report, today=TODAY, snapshot=snapshot(card()))
        self.assertEqual((after[0]["ingresso"], after[0]["consigli"], after[0]["tags"]),
                         ("Ingresso libero", "Arrivare presto.", ["antiquariato", "mercato"]))
        self.assertTrue(vg.verify_exported([normalize(r, TODAY)[0] for r in after], report, today=TODAY)["release_safe"])


class MonitoringTests(unittest.TestCase):
    A, B, C, D = (UUID, "8abfcc97-a7d4-40b0-bdf2-4d94262c1189", "b42af7e2-8c19-437e-9ee8-337deffe8697",
                  "a65ea088-44eb-4504-aacf-346d2d7f113b")

    def raw(self, key, read_at):
        return {"id": key, "url": "https://vintagery.it/mercatini/" + key, "name": "M", "city": "Bologna",
                "region": "Emilia-Romagna", "read_at": read_at + "T10:00:00Z", "start_date": "2026-11-15"}

    def test_a_daily_read_replaces_adds_drops_and_never_renews_unread_cards(self):
        old = snapshot(*[card(id=k, url="https://vintagery.it/mercatini/" + k) for k in (self.A, self.B, self.C)])
        download = {"schema": 2, "mode": "daily", "listing_day": "2026-10-28", "listing": [self.A, self.B, self.D],
                    "cards": {self.A: self.raw(self.A, "2026-10-28"), self.D: self.raw(self.D, "2026-10-28")}}
        merged, report = vg.merge_download(old, download)
        reads = {c["id"]: c["read_on"] for c in merged["cards"]}
        self.assertEqual(reads, {self.A: "2026-10-28", self.B: "2026-10-20", self.D: "2026-10-28"})
        self.assertEqual({k: report[k] for k in ("re_read", "new", "kept", "gone")},
                         {"re_read": 1, "new": 1, "kept": 1, "gone": 1})
        with self.assertRaises(ValueError):  # a blocked sitemap read never empties the snapshot
            vg.merge_download(old, {**download, "listing": [self.D]})

    def test_the_plan_rereads_passed_dates_then_the_oldest_reads(self):
        cards = [card(id=self.A, url="https://vintagery.it/mercatini/" + self.A, read_on="2026-10-20"),
                 card(id=self.B, url="https://vintagery.it/mercatini/" + self.B, read_on="2026-10-21",
                      start_date="2026-10-25", verified_on="2026-10-20"),
                 card(id=self.C, url="https://vintagery.it/mercatini/" + self.C, read_on="2026-10-22")]
        today_plan = vg.plan(snapshot(*cards), today=date(2026, 10, 28), per_day=2)
        self.assertEqual(today_plan, {"day": "2026-10-28", "fetch": [self.B[:8], self.A[:8]]})
        # A card the last sitemap listing named that we don't hold yet goes first.
        today_plan = vg.plan(snapshot(*cards), today=date(2026, 10, 28), per_day=2,
                             listing=[self.A, self.D, self.C])
        self.assertEqual(today_plan["fetch"], [self.D[:8], self.B[:8]])


if __name__ == "__main__":
    unittest.main()
