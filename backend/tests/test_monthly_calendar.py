"""Monthly official calendars (row_kind market_venue_month): Regione Veneto antiques 2026."""
import copy
import importlib.util
import json
import sys
import tempfile
import unittest
import unittest.mock
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from export_static import export, venue_slot
from merge_catalog import load_existing
from publisher_snapshot_date import discover_document, make_landing_page_proof
from recurrence_refresh import (calendar_key, complete_monthly_rule, forecast_source_limits,
                                refresh_record, refresh_records)
from source_contract_activation import activate, validate_release, verify_static
from source_contract_ingest import apply_fill, stage, town_day_fills, verify_fill
from source_lifecycle import candidate_record, digest, parse_rows, validate_contracts
from test_multi_town_calendar import (HEADER as WEEKLY_HEADER, market, profile as weekly_profile,
                                      row as weekly_row, table_pdf)

CONTRACTS = json.loads((Path(__file__).resolve().parents[1] /
                        "data/market-source-contracts.json").read_text("utf-8"))
ANTIQ = next(p for p in CONTRACTS["raw_profiles"] if p["id"] == "veneto-calendario-antiquariato")
TODAY = date(2026, 10, 25)
COLUMNS = ["provincia", "comune", "luogo", "periodicita", "dal_al", "cadenza", "cadenza_ampia",
           "giorni", "orario"]
HEADER = ["Provincia", "Comune", "Luogo", "Periodicita", "Dal Al", "Cadenza", "Cadenza ampia",
          "Giorni", "Orario"]
DOC = ("https://www.regione.veneto.it/documents/10713/12114597/"
       "Calendario+mercatini+usato+2026.pdf/7ca1a502-6de9-4e5e-a247-4ec2f3e6cf3d")
HAS_PDF = importlib.util.find_spec("pdfplumber") is not None


def profile(**changes):
    """The reviewed antiques contract on a small nine-column table."""
    p = copy.deepcopy(ANTIQ)
    p.update({"schema_columns": COLUMNS, "pdf_header": HEADER, "min_rows": 1, "max_rows": 50})
    p.update(changes)
    return p


def row(comune, luogo, giorni, orario="dalle ore 8,00 alle ore 18,00", periodicita="annuale",
        cadenza="mensile", provincia="Padova"):
    return dict(zip(COLUMNS, [provincia, comune, luogo, periodicita, "", cadenza, "", giorni, orario]))


def card(slug, citta, ricorrenza, **fields):
    fields = {"provincia": "PD", "categoria": "antiquariato", "fonte": "cosedicasa.com", **fields}
    return market(slug, citta, ricorrenza, **fields)


def landing(year=2026):
    """Both yearly links of the real page: weekly calendar and antiques calendar."""
    return (f'<a href="/documents/10713/12114597/Calendario+regionale+marcati+{year}.pdf/'
            f'be79e5c1-ceae-4e76-8207-3b49630ae080">Calendario regionale dei mercati </a>'
            f'<p>Di seguito si pubblica l\'elenco aggiornato per l\'anno {year} dei<a href="/documents/'
            f'10713/12114597/Calendario+mercatini+usato+{year}.pdf/7ca1a502-6de9-4e5e-a247-'
            f'4ec2f3e6cf3d"> <strong>mercatini dell\'antiquariato</strong></a><a href="/documents/'
            f'10713/0/Antiquariato+-+calendario+mercatini+2020.pdf/536c8c2e-cbd0-4e29-a644-'
            f'd1d00eff35d7"><span>d</span></a>el Veneto</p>').encode("utf-8")


class MonthlyRuleTests(unittest.TestCase):
    def test_only_a_bare_monthly_rule_is_complete(self):
        for text, rule in (("Prima domenica del mese", (6, 1)), ("ogni prima domenica del mese", (6, 1)),
                           ("Ogni 4° Domenica Del Mese", (6, 4)), ("Terzo sabato del mese", (5, 3)),
                           ("mensile - ultima domenica del mese", (6, -1))):
            with self.subTest(text=text):
                found = complete_monthly_rule(text)
                self.assertEqual((found["weekday"], found["ordinal"]), rule)
        for text in ("Seconda domenica del mese ad esclusione del mese di agosto",
                     "Terza domenica di ogni mese tranne luglio ed agosto",
                     "Quarta domenica dei mesi giugno, luglio, agosto, settembre",
                     "Seconda domenica prima di Pasqua", "sabato", "26 luglio e 14 agosto",
                     "mensile - terza domenica del mese, da marzo a ottobre"):
            with self.subTest(text=text):
                self.assertIsNone(complete_monthly_rule(text))

    def test_calendar_key_is_the_export_same_market_key(self):
        rule = complete_monthly_rule("Prima domenica del mese")
        self.assertEqual(calendar_key(rule), ("monthly_nth_weekday", (6,), 1))
        listed = card("x", "Brugine", "Ogni 1° Domenica Del Mese", indirizzo="Villa Roberti")
        self.assertEqual(venue_slot(listed)[2], calendar_key(rule))


class MonthlyRowTests(unittest.TestCase):
    def test_rows_become_monthly_antiques_records_or_are_held(self):
        p = profile()
        record, issue, _ = candidate_record(p, row("BRUGINE", "Villa Roberti", "ogni prima domenica del mese"),
                                            today=TODAY, source_date="2026-01-01")
        self.assertIsNone(issue)
        self.assertEqual((record["nome"], record["citta"], record["provincia"], record["categoria"]),
                         ("Mercatino dell'antiquariato di Brugine", "Brugine", "PD", "antiquariato"))
        self.assertEqual(record["ricorrenza_testo"], "mensile - prima domenica del mese")
        self.assertEqual(record["orario_testo"], "08:00–18:00 (da verificare con il Comune)")
        # Exclusions the rule can't carry: no calendar, never a shortened one.
        held, issue, _ = candidate_record(p, row("PADOVA", "Prato della Valle",
                                                 "Terza domenica del mese ad esclusione di agosto"),
                                          today=TODAY, source_date="2026-01-01")
        self.assertEqual((issue, held["ricorrenza_testo"]), ("schedule_unknown", "Calendario da verificare"))
        for other in (row("ASIAGO", "Piazza Carli", "Terza domenica del mese", periodicita="stagionale"),
                      row("OCCHIOBELLO", "Via Eridania", "Quarta domenica del mese",
                          cadenza="di più ampia durata")):
            self.assertEqual(candidate_record(p, other, today=TODAY)[1], "not_a_market_venue")
        seasonal, _, _ = candidate_record(p, row("ROVIGO", "Piazza V. Emanuele II", "Prima domenica del mese",
                                                 orario="dalle ore 8,30 alle ore 17,30 (periodo invernale) - "
                                                        "dalle ore 8,30 alle ore 20,30 (periodo estivo)"),
                                          today=TODAY, source_date="2026-01-01")
        self.assertEqual(seasonal["orario_testo"], "")

    def test_every_written_rule_reads_back_as_itself(self):
        p = profile()
        for ordinal, word in ((1, "Primo"), (2, "Secondo"), (3, "Terzo"), (4, "Quarto"), (-1, "Ultimo")):
            for day, name in ((5, "sabato"), (6, "domenica")):
                text = (word[:-1] + "a" if day == 6 else word) + " " + name + " del mese"
                record, _, _ = candidate_record(p, row("LIMENA", "Via Roma", text), today=TODAY,
                                                source_date="2026-01-01")
                self.assertEqual(complete_monthly_rule(record["ricorrenza_testo"]),
                                 {"kind": "monthly_nth_weekday", "weekday": day, "ordinal": ordinal})

    def test_contract_options_are_validated(self):
        index = [p["id"] for p in CONTRACTS["raw_profiles"]].index(ANTIQ["id"])
        good = copy.deepcopy(CONTRACTS)
        good["raw_profiles"][index] = profile()
        self.assertTrue(validate_contracts(good))
        for change in ({"weekday_field": "giorni"}, {"identity_fields": ["provincia", "comune", "luogo"]},
                       {"existing_market_fill": {"max_records_per_run": 10}}, {"existing_market_fill": None},
                       {"existing_market_fill": {"max_records_per_run": 10, "categories": ["antichita"]}},
                       {"pdf_header_repeats": "no"}, {"category": "antichita"},
                       {"empty_name_template": None}):
            with self.subTest(change=change):
                bad = copy.deepcopy(CONTRACTS)
                bad["raw_profiles"][index] = profile(**change)
                with self.assertRaises(ValueError):
                    validate_contracts(bad)

    def test_each_calendar_finds_its_own_yearly_document(self):
        weekly = next(p for p in CONTRACTS["raw_profiles"] if p["id"] == "veneto-calendario-mercati")
        self.assertEqual(discover_document(ANTIQ, landing(), read_on="2026-10-26"), (DOC, 2026))
        self.assertIn("regionale+marcati+2026", discover_document(weekly, landing(), read_on="2026-10-26")[0])


@unittest.skipUnless(HAS_PDF, "pdfplumber not installed")
class HeaderOnFirstPageTests(unittest.TestCase):
    def test_later_pages_continue_the_first_page_table(self):
        first = [["CALENDARIO 2026"] + [""] * 8, HEADER,
                 list(row("BRUGINE", "Villa Roberti", "Prima domenica del mese").values())]
        second = [list(row("LIMENA", "Via Roma", "Terza domenica del mese").values()),
                  list(row("CALTO", "Via Est", "Primo sabato del mese").values())]
        rows = parse_rows(profile(), table_pdf([first, second]))
        self.assertEqual([r["comune"] for r in rows], ["BRUGINE", "LIMENA", "CALTO"])
        with self.assertRaises(ValueError):  # a second header: the layout changed
            parse_rows(profile(), table_pdf([first, [HEADER] + second]))
        with self.assertRaises(ValueError):  # the default still wants it on every page
            parse_rows(profile(pdf_header_repeats=True), table_pdf([first, second]))


class MonthlyFillTests(unittest.TestCase):
    def run_fill(self, base, source, today=TODAY):
        return town_day_fills(profile(), source, base, today=today, read_on=today.isoformat(),
                              source_date="2026-01-01", parsed_sha256="b" * 64)

    def test_unique_town_calendar_fills_and_records_the_card_recurrence(self):
        target = card("mercatino-antiquariato-brugine", "Brugine", "Ogni 1° Domenica Del Mese")
        months = card("mercatino-antiquariato-limena", "Limena",
                      "mensile - terza domenica del mese, da marzo a ottobre", orario_testo="09:00–12:00")
        source = [row("BRUGINE", "Villa Roberti", "ogni prima domenica del mese"),
                  row("LIMENA", "Via Roma", "Terza domenica del mese")]
        proofs, counts = self.run_fill([target, months], source)
        by_slug = {proof["slug"]: proof for proof in proofs}
        fill = by_slug[target["slug"]]
        self.assertEqual(fill["changed_fields"], {
            "indirizzo": {"before": "", "after": "Villa Roberti"},
            "orario_testo": {"before": "La mattina", "after": "08:00–18:00 (da verificare con il Comune)"}})
        receipt = fill["receipt"]
        # Still listed: the card's own words, dated with the calendar's content date.
        self.assertEqual(receipt["valori"]["ricorrenza_testo"], "Ogni 1° Domenica Del Mese")
        self.assertEqual((receipt["metodo"], receipt["fonte_aggiornata_il"]),
                         ("comune_provincia_ricorrenza_univoca", "2026-01-01"))
        # A month range the calendar doesn't state is not attested; exact hours are kept.
        self.assertNotIn("ricorrenza_testo", by_slug[months["slug"]]["receipt"]["valori"])
        self.assertEqual(by_slug[months["slug"]]["changed_fields"],
                         {"indirizzo": {"before": "", "after": "Via Roma"}})
        self.assertEqual((counts["recurrence_still_listed"], counts["kept_existing_orario_testo"]), (1, 1))
        after = apply_fill(target, fill, profile(), today=TODAY)
        observations = {"source_parsed_sha256": "b" * 64, "source_read_on": TODAY.isoformat()}
        with unittest.mock.patch("source_contract_ingest.observed_source_date", return_value="2026-01-01"):
            self.assertEqual(verify_fill(profile(), target, after, fill, today=TODAY,
                                         source_observations=observations), 2)
            for field, value in (("ricorrenza_testo", "Ogni 2a Domenica Del Mese"), ("indirizzo", "Via X")):
                with self.subTest(field=field), self.assertRaises(ValueError):
                    verify_fill(profile(), target, dict(after, **{field: value}), fill, today=TODAY,
                                source_observations=observations)

    def test_doubtful_matches_are_held(self):
        one = card("antiquariato-brugine-a", "Brugine", "mensile - prima domenica del mese")
        two = card("antiquariato-brugine-b", "Brugine", "Ogni Prima Domenica Del Mese", fonte="eventiesagre.it")
        source = [row("BRUGINE", "Villa Roberti", "Prima domenica del mese")]
        for base, extra, reason in (
                ([one, two], [], "held_several_catalog_markets_same_town_calendar"),
                ([one], [row("BRUGINE", "Piazza", "Seconda domenica prima di Pasqua")],
                 "held_several_official_markets_same_town_calendar"),
                ([dict(one, categoria="alimentare")], [], "held_market_type_not_in_contract"),
                ([dict(one, ricorrenza_testo="mensile - terza domenica del mese")], [],
                 "held_no_official_market_town_calendar"),
                ([dict(one, indirizzo="Piazza Garibaldi")], [], "held_different_street")):
            with self.subTest(reason=reason):
                self.assertEqual(self.run_fill(base, source + extra)[1][reason], len(base))
        for text, reason in (("Prima domenica del mese escluso agosto", "held_official_calendar_qualified"),
                             ("Prima domenica del mese", "held_official_market_not_annual_monthly")):
            seasonal = "stagionale" if reason.endswith("monthly") else "annuale"
            counts = self.run_fill([one], [row("BRUGINE", "Villa Roberti", text, periodicita=seasonal)])[1]
            self.assertEqual(counts[reason], 1)

    def test_still_listed_recurrence_renews_only_within_its_age_limit(self):
        target = card("mercatino-antiquariato-brugine", "Brugine", "mensile - prima domenica del mese",
                      date=[], date_quality="sconosciuta")
        source = [row("BRUGINE", "Villa Roberti", "Prima domenica del mese")]
        # Owner rule (2026-10-27): the yearly calendar counts until its year ends.
        for day, first in ((date(2026, 3, 1), ["2026-03-01", "2026-04-05"]),
                           (date(2026, 10, 26), ["2026-11-01", "2026-12-06"]), (date(2027, 1, 1), None)):
            with self.subTest(day=day):
                (fill,), _ = self.run_fill([target], source, today=day)
                after = apply_fill(target, fill, profile(), today=day)
                projected, reason = refresh_record(after, day, source_limits=())
                if first:
                    self.assertEqual((reason, projected["proiezione_fonte"], projected["date"][:2]),
                                     ("renewed", "riscontri_campi:ricorrenza_testo", first))
                else:  # the 2026 calendar no longer covers 2027: nothing renews
                    self.assertNotEqual(reason, "renewed")
                    self.assertEqual(projected["date"], [])


class MonthlyNewMarketTests(unittest.TestCase):
    def test_new_venue_needs_a_free_town_calendar(self):
        p = profile()
        source = [row("LIMENA", "Via Roma", "Prima domenica del mese"),
                  row("BRUGINE", "Villa Roberti", "Prima domenica del mese"),
                  row("CALTO", "Via dell'Industria", "Primo sabato del mese", provincia="Rovigo"),
                  row("ROVIGO", "Piazza V. Emanuele II", "Prima domenica del mese", provincia="Rovigo"),
                  row("ADRIA", "Piazza Groto", "secondo sabato del mese escluso agosto", provincia="Rovigo")]
        base = [card("antiquariato-brugine", "Brugine", "mensile - prima domenica del mese",
                     indirizzo="Villa Roberti, via Roma"),
                card("antiquariato-calto", "Calto", "mensile - terza domenica del mese", provincia="RO",
                     indirizzo="Piazza Roma"),
                card("antiquariato-rovigo", "Rovigo", "", provincia="RO", indirizzo="Piazza Garibaldi")]
        proof = make_landing_page_proof(p, landing(), DOC, 2026, b"%PDF", read_on="2026-10-25", today=TODAY)
        with unittest.mock.patch("source_contract_ingest.parse_rows", return_value=source):
            candidates, report = stage(p, b"%PDF", base, today=TODAY, read_on="2026-10-25",
                                       source_date_proof=proof)
        self.assertEqual([(c["citta"], c["ricorrenza_testo"], c["categoria"]) for c in candidates], [
            ("Limena", "mensile - prima domenica del mese", "antiquariato"),
            ("Calto", "mensile - primo sabato del mese", "antiquariato")])
        # Calto's other monthly calendar is another market; Rovigo's antiques card
        # with no readable calendar may be this very one.
        self.assertEqual(report["review_reason_counts"], {
            "existing_market_same_town_calendar": 1, "existing_same_type_market_calendar_unknown": 1,
            "new_market_calendar_unknown": 1})


@unittest.skipUnless(HAS_PDF, "pdfplumber not installed")
class BothCalendarsActivationTests(unittest.TestCase):
    def test_weekly_and_monthly_calendars_run_together_and_pass_every_check(self):
        weekly, antiques = weekly_profile(), profile()
        cfg = copy.deepcopy(CONTRACTS)
        cfg["raw_profiles"] = [antiques, weekly]
        reg = {"schema": 1, "publication_channel": "dev-only", "description": "test",
               "user_event_confirmations_allowed": False, "approvals": [{
                   "schema": 1, "mode": "approved_dev_only", "source_id": p["id"],
                   "reviewed_profile_sha256": digest(p),
                   "publisher_license_evidence_url": p["attribution_url"],
                   "identity_granularity": p["row_kind"], "reviewed_on": "2026-10-25",
                   "max_new_ids": 5, "source_record_kind": p["row_kind"],
                   "source_specific_geo_approval": False} for p in (antiques, weekly)]}
        pdfs = {"mercatini+usato": table_pdf([[HEADER] + [list(r.values()) for r in (
                    row("BRUGINE", "Villa Roberti", "ogni prima domenica del mese"),
                    row("LIMENA", "Via Roma", "Prima domenica del mese"))]]),
                "regionale+marcati": table_pdf([[WEEKLY_HEADER, list(weekly_row(
                    "AGORDO", "Piazza della Libertà", "mercoledì").values())]])}

        def fetch(url, max_bytes=65536):
            body = landing() if url == antiques["resource_url"] else next(
                pdf for key, pdf in pdfs.items() if key in url)
            return body, len(body) > max_bytes

        base = [market("mercato-settimanale-di-agordo-agordo-mercoledi", "Agordo", "settimanale - mercoledì"),
                card("mercatino-antiquariato-brugine", "Brugine", "mensile - prima domenica del mese")]
        after, report = activate(cfg, reg, base, today=TODAY, fetch=fetch, read_on=TODAY.isoformat())
        self.assertEqual({sid: s["status"] for sid, s in report["per_source"].items()},
                         {p["id"]: "source_contract_approved_staged_only" for p in (antiques, weekly)})
        self.assertEqual(report["filled_market_ids"], sorted(r["slug"] for r in base))
        self.assertEqual(len(report["new_market_ids"]), 1)
        new = after[-1]
        self.assertEqual((new["citta"], new["ricorrenza_testo"], new["lat"]),
                         ("Limena", "mensile - prima domenica del mese", None))
        self.assertTrue(validate_release(base, after, report, cfg, reg)["release_safe"])
        # Static export: the new monthly market gets predicted first Sundays only.
        projected, _ = refresh_records(after, TODAY, 120, 540, source_limits=forecast_source_limits(cfg))
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder)
            export(projected, path, today=TODAY, min_count=1,
                   preserve_ids=set(report["new_market_ids"]) | set(report["evidence_updated_market_ids"]))
            self.assertTrue(verify_static(path / "manifest.json", report, cfg, reg, TODAY)["release_safe"])
            exported = {r["slug"]: r for r in load_existing(path / "manifest.json")}
        self.assertEqual(exported[new["slug"]]["date"][:2], ["2026-11-01", "2026-12-06"])
        self.assertEqual(exported[new["slug"]]["date_quality"], "prevista")


if __name__ == "__main__":
    unittest.main()
