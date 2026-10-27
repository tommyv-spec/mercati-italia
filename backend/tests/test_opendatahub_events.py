"""Open Data Hub (Alto Adige) market events: rows, town rule, licence and date proof."""
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import opendatahub_events as odh
from publisher_snapshot_date import make_event_change_proof, resolve_source_date
from source_lifecycle import candidate_record, istat_municipality, parse_rows, validate_contracts

CONTRACTS = json.loads((Path(__file__).resolve().parents[1] / "data/market-source-contracts.json")
                       .read_text("utf-8"))
PROFILE = next(p for p in CONTRACTS["raw_profiles"] if p["id"] == "altoadige-odh-mercati")
TODAY = date(2026, 10, 27)


def weekly(first, weeks, step=7):
    return [(first + timedelta(days=i * step)).isoformat() + "T00:00:00" for i in range(weeks)]


def event(title, city, dates, *, municipality=None, address="Piazza Municipio",
          hours=("08:00:00", "13:00:00"), uid="A", changed="2026-10-20T08:00:00+00:00", **extra):
    item = dict.fromkeys(odh.FIELDS)
    item.update({"Id": uid * 32, "Source": "lts", "LicenseInfo.License": "CC0", "LastChange": changed,
                 "Detail.it.Title": title, "Detail.de.Title": None,
                 "ContactInfos.it.City": city, "ContactInfos.it.Address": address,
                 "LocationInfo.MunicipalityInfo.Name.it": municipality or city,
                 "EventDate.[*].From": dates, "EventDate.[*].To": dates,
                 "EventDate.[*].Begin": [hours[0]] * len(dates), "EventDate.[*].End": [hours[1]] * len(dates)})
    item.update(extra)
    return item


def snapshot(*items):
    return {"TotalResults": len(items), "TotalPages": 1, "Items": list(items)}


def comune(name):
    return istat_municipality("Trentino-Alto Adige", name) is not None


class OpenDataHubRowsTests(unittest.TestCase):
    def test_weekly_year_round_seasonal_and_scattered_weekdays(self):
        rows = odh.rows(snapshot(
            event("Mercato settimanale a Ora", "Ora", weekly(date(2026, 1, 7), 52), uid="A"),
            event("Mercato dei contadini a Brunico", "Brunico", weekly(date(2026, 3, 6), 35), uid="B"),
            # Brennero: 34 dates spread over Monday-Saturday is no weekly market.
            event("Mercato tradizionale al Brennero", "Brennero",
                  weekly(date(2026, 2, 5), 34, step=9), uid="C"),
        ), comune)
        by = {(r["comune"], r["giorni"]): r for r in rows}
        self.assertEqual(by[("Ora", "mercoledì")]["periodicita"], "annuale")
        self.assertEqual(by[("Ora", "mercoledì")]["orario"], "08:00 - 13:00")
        self.assertEqual(by[("Brunico", "venerdì")]["periodicita"], "stagionale")
        self.assertEqual({r["periodicita"] for r in rows if r["comune"] == "Brennero"}, {"irregolare"})

    def test_town_rule_prefers_event_town_then_named_comune_then_municipality(self):
        dates = weekly(date(2026, 1, 2), 52)
        rows = odh.rows(snapshot(
            event("Grande mercato settimanale di Merano", "Merano", dates, municipality="Lagundo", uid="A"),
            event("Mercatino contadino a San Giacomo", "San Giacomo/Laives", dates,
                  municipality="Bolzano", uid="B"),
            event("Mercato del contadino", "Caldaro al Lago", dates,
                  municipality="Caldaro sulla Strada del Vino", uid="C"),
        ), comune)
        self.assertEqual({r["comune"] for r in rows},
                         {"Merano", "Laives", "Caldaro sulla Strada del Vino"})

    def test_yearly_entries_of_one_market_are_joined_and_non_markets_skipped(self):
        rows = odh.rows(snapshot(
            event("Ogni Venerdì mercato settimanale a Laces", "Laces", weekly(date(2025, 6, 13), 30), uid="A"),
            event("Ogni Venerdì mercato settimanale a Laces", "Laces", weekly(date(2026, 1, 9), 52),
                  uid="B", hours=("08:00:00", "12:30:00")),
            event("Trasmettere emozioni su tela - Galleria", "Egna", weekly(date(2026, 1, 6), 52), uid="C"),
        ), comune)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["dal"], "2025-06-13")
        self.assertEqual(rows[0]["orario"], "")  # two different published hours: none is shown

    def test_only_complete_cc0_lts_snapshots_are_read(self):
        good = event("Mercato", "Ora", weekly(date(2026, 1, 7), 52))
        for bad in ({**good, "LicenseInfo.License": "CC-BY"}, {**good, "Source": "nobis"},
                    {**good, "Id": "urn:event:1"}):
            with self.assertRaises(ValueError):
                odh.rows(snapshot(bad), comune)
        with self.assertRaises(ValueError):
            odh.rows({"TotalResults": 2, "TotalPages": 2, "Items": [good]}, comune)


class OpenDataHubContractTests(unittest.TestCase):
    def blob(self):
        return json.dumps(snapshot(
            event("Mercato settimanale ad Ora", "Ora", weekly(date(2026, 1, 7), 52), uid="A"),
            event("Mercato dei contadini a Brunico", "Brunico", weekly(date(2026, 3, 6), 35), uid="B"),
            event("Mercatino di Natale a Ora", "Ora", weekly(date(2026, 1, 7), 52), uid="C"),
        )).encode("utf-8")

    def test_contract_validates_and_needs_its_query(self):
        validate_contracts(CONTRACTS)
        changed = {**PROFILE, "resource_url": PROFILE["resource_url"].replace("source=lts&", "")}
        with self.assertRaises(ValueError):
            odh.validate_profile(changed)
        self.assertIn("begindate=2026-08-28&", odh.request_url(PROFILE, "2026-10-27"))

    def test_seasonal_rows_fill_only_and_christmas_markets_are_excluded(self):
        profile = {**PROFILE, "min_rows": 1}  # the real bound is 20 rows
        records = {r["denominazione"]: candidate_record(profile, r, today=TODAY, source_date="2026-10-20")
                   for r in parse_rows(profile, self.blob())}
        ora, issue, _ = records["Mercato settimanale ad Ora"]
        self.assertIsNone(issue)
        self.assertEqual(ora["ricorrenza_testo"], "settimanale - mercoledi")
        self.assertEqual(ora["orario_testo"], "08:00–13:00 (da verificare con il Comune)")
        self.assertIsNotNone(records["Mercato dei contadini a Brunico"][0])  # a market row: may fill
        self.assertNotIn({"periodicita": "stagionale"}, PROFILE["new_market_filters_any"])
        self.assertIsNone(records["Mercatino di Natale a Ora"][0])

    def test_content_date_is_newest_market_change_not_read_time(self):
        blob = self.blob()
        proof = make_event_change_proof(PROFILE, blob, read_on="2026-10-27", today=TODAY)
        self.assertEqual(proof["source_date"], "2026-10-20")
        self.assertEqual(resolve_source_date(PROFILE, proof=proof, blob=blob, today=TODAY), "2026-10-20")
        with self.assertRaises(ValueError):
            resolve_source_date(PROFILE, proof={**proof, "source_date": "2026-10-27"}, blob=blob, today=TODAY)


if __name__ == "__main__":
    unittest.main()
