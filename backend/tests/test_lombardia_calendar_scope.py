import json
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from export_static import normalize, prepare
from lombardia_calendar_scope import calendar_scope, filter_dates, within_bounds
from merge_catalog import combine
from official_enrichment import official_identity_issue
from recurrence_refresh import forecast_rule, refresh_record, temporal_scope_hold
from source_lombardia import convert


TODAY = date(2026, 10, 20)
FIXTURE = Path(__file__).parent / "fixtures/lombardia-calendar-scope/observed-boundaries-20261020.json"


class LombardiaCalendarScopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.fixture = json.loads(FIXTURE.read_text())
        # Only the 14 observed scope rows are captured. Synthetic, unrelated
        # filler satisfies the adapter's complete-feed count guard; it is not
        # presented as publisher evidence or written to a catalog.
        filler = {**cls.fixture["rows"][0], "descom": "COMUNE DI PROVA",
                  "ubicazione": "MERCATO SETTIMANALE DI PROVA", "dal": None, "al": None}
        cls.payload = {
            "dataset_id": "68zx-njaw", "publisher_data_updated_at": "2026-10-13",
            "publisher_update_scope": "entire_dataset_not_each_market", "expected_rows": 1100,
            "rows": cls.fixture["rows"] + [
                {**filler, "codice_id": str(700000 + i)} for i in range(1086)],
        }
        cls.converted = {r["slug"]: r for r in convert(cls.payload, today=TODAY)}

    def row(self, ident="216440", day="martedi"):
        return deepcopy(self.converted[f"lo-mercap-{ident}-{day}"])

    def test_three_observed_identities_remove_exactly_38_out_of_scope_forecasts(self):
        removed = {}
        for evidence in self.fixture["prior_catalog_evidence"]:
            if not evidence["forecast_dates_outside_explicit_boundary"]:
                continue
            row = deepcopy(self.converted[evidence["slug"]])
            old_dates = evidence["catalog_forecast_dates"]
            expected = sorted(set(old_dates) - set(evidence["forecast_dates_outside_explicit_boundary"]))
            self.assertEqual(row["date"], expected)
            row["date"] = old_dates
            row["date_quality"] = "prevista"
            row["proiezione_regola"] = {"kind": "weekly", "weekdays": [date.fromisoformat(old_dates[0]).weekday()]}
            row["proiezione_generata_il"] = "2026-10-01"
            row["proiezione_fonte"] = "ricorrenza_testo"
            refreshed, _ = refresh_record(row, TODAY)
            exported_directly, error = normalize(row, TODAY)
            self.assertIsNone(error)
            self.assertIsNone(exported_directly["proiezione_regola"])
            self.assertEqual(exported_directly["proiezione_generata_il"], "")
            self.assertEqual(exported_directly["proiezione_fonte"], "")
            exported_after_refresh, error = normalize(refreshed, TODAY)
            self.assertIsNone(error)
            for result in (refreshed, exported_directly, exported_after_refresh):
                self.assertEqual(result["date"], expected)
                self.assertEqual(result["slug"], evidence["slug"])
                self.assertEqual(result["id_fonte"], row["id_fonte"])
                self.assertEqual(result["verificato_il"], "")
                self.assertEqual(result["aggiornato_il"], "2026-10-13")
                self.assertEqual(result["aggiornamento_ambito"], "dataset")
                self.assertEqual(result["date_quality"], "prevista" if expected else "sconosciuta")
            removed[evidence["slug"]] = len(old_dates) - len(expected)
        self.assertEqual(removed, {"lo-mercap-100811-giovedi": 17,
                                  "lo-mercap-100361-sabato": 5,
                                  "lo-mercap-216440-martedi": 16})

    def test_all_observed_source_limits_and_names_survive_refresh_export_and_reload(self):
        observed_ids = {r["codice_id"] for r in self.fixture["rows"]}
        raw = [r for r in self.converted.values() if r["id_fonte"] in observed_ids]
        refreshed = [refresh_record(r, TODAY)[0] for r in raw]
        exported, report = prepare(refreshed, TODAY)
        self.assertEqual({r["slug"] for r in exported}, {r["slug"] for r in raw})
        self.assertEqual(report["same_source_duplicates_merged"], 0)
        by_id = {r["id_fonte"]: r for r in exported}
        for observed in self.fixture["rows"]:
            result = by_id[observed["codice_id"]]
            for key, value in observed.items():
                self.assertEqual(result["identita_fonte"][key], value)
            # Serialize/deserialize exactly like a daily static catalog read.
            reloaded = json.loads(json.dumps(result))
            renewed, _ = refresh_record(reloaded, TODAY)
            self.assertEqual(renewed["date"], result["date"])
            self.assertEqual(renewed["identita_fonte"], result["identita_fonte"])

    def test_compound_end_is_retained_literally_and_never_selects_one_candidate(self):
        row = self.row("101083", "mercoledi")
        self.assertEqual(row["date"], [])
        self.assertIn("31/12;14/06", row["ricorrenza_testo"])
        self.assertEqual(calendar_scope(row)["state"], "ambiguous")
        row["date"] = ["2026-10-21", "2026-10-28"]
        row["date_quality"] = "prevista"
        refreshed, reason = refresh_record(row, TODAY)
        self.assertEqual(reason, "source_calendar_scope_unrepresented")
        for result in (refreshed, normalize(row, TODAY)[0]):
            self.assertEqual(result["date"], [])
            self.assertEqual(result["identita_fonte"]["al"], "31/12;14/06")
            self.assertEqual(result["date_quality"], "sconosciuta")

    def test_yearless_boundaries_are_inclusive_and_can_cross_new_year(self):
        bounds = ["01/09", "30/06"]
        for value, allowed in (("2026-09-01", True), ("2027-06-30", True),
                               ("2027-07-01", False), ("2026-08-31", False)):
            self.assertEqual(within_bounds(date.fromisoformat(value), bounds), allowed)
        self.assertTrue(within_bounds(date(2028, 2, 29), ["29/02", "01/03"]))
        self.assertFalse(within_bounds(date(2027, 2, 28), ["29/02", "01/03"]))
        self.assertTrue(within_bounds(date(2027, 3, 1), ["29/02", "01/03"]))

    def test_complete_raw_scope_can_renew_within_a_future_season_without_becoming_reported(self):
        row = self.row("100811", "giovedi")
        result, reason = refresh_record(row, date(2027, 6, 25))
        self.assertEqual(reason, "renewed")
        self.assertTrue(result["date"])
        self.assertTrue(all("2027-07-01" <= day <= "2027-08-31" for day in result["date"]))
        self.assertEqual(result["date_quality"], "prevista")
        self.assertEqual(result["proiezione_regola"]["source_day_month_bounds"], ["01/07", "31/08"])
        self.assertEqual(result["aggiornato_il"], "2026-10-13")
        self.assertEqual(result["verificato_il"], "")

    def test_absent_and_full_year_limits_preserve_year_round_behavior(self):
        row = self.row("100361", "sabato")
        row["ricorrenza_testo"] = "Ogni sabato"
        for first, last in ((None, None), ("01/01", "31/12")):
            with self.subTest(first=first, last=last):
                row["identita_fonte"]["dal"], row["identita_fonte"]["al"] = first, last
                result, reason = refresh_record(row, TODAY)
                self.assertEqual(reason, "renewed")
                self.assertIn("2027-01-02", result["date"])
                self.assertEqual(result["date_quality"], "prevista")

    def test_incomplete_invalid_or_year_specific_limits_hold_instead_of_guessing(self):
        for first, last in (("01/07", None), (None, "31/08"), ("31/04", "31/08"),
                            ("01/07/2026", "31/08/2026"), ("1/7", "31/8"),
                            ("01/07;01/09", "31/10"), ("dal 01/07", "31/08")):
            with self.subTest(first=first, last=last):
                row = self.row()
                row["identita_fonte"]["dal"], row["identita_fonte"]["al"] = first, last
                result, reason = refresh_record(row, TODAY)
                self.assertEqual(reason, "source_calendar_scope_unrepresented")
                self.assertEqual(result["date"], [])
                exported, error = normalize(row, TODAY)
                self.assertIsNone(error)
                self.assertEqual(exported["date"], [])
                self.assertEqual(exported["identita_fonte"]["dal"], first)
                self.assertEqual(exported["identita_fonte"]["al"], last)

    def test_fresh_read_with_unknown_content_age_can_only_remove_old_out_of_scope_dates(self):
        row = self.row()
        row.update(aggiornato_il="", fonte_aggiornata_il="", fonte_letta_il="2026-10-20",
                   date=["2026-10-27", "2026-11-03"], proiezione_generata_il="2026-10-01")
        result, reason = refresh_record(row, TODAY)
        self.assertEqual(reason, "existing_forecast_source_scope_filtered")
        self.assertEqual(result["date"], ["2026-10-27"])
        self.assertEqual(result["aggiornato_il"], "")
        self.assertEqual(result["proiezione_generata_il"], "")
        self.assertEqual(result["fonte_letta_il"], "2026-10-20")
        stale = {**row, "aggiornato_il": "2023-01-01"}
        result, reason = refresh_record(stale, TODAY)
        self.assertEqual(reason, "expired_stale_forecast")
        self.assertEqual(result["date"], [])

    def test_publisher_reported_confirmed_and_human_reviewed_dates_are_not_rewritten(self):
        for changes in ({"date_quality": "riportata"}, {"date_quality": "confermata"},
                        {"verificato_il": "2026-10-19"}):
            with self.subTest(changes=changes):
                row = self.row()
                row.update(date=["2026-11-03"], **changes)
                result, _ = refresh_record(row, TODAY)
                self.assertEqual(result, row)
                exported, error = normalize(row, TODAY)
                self.assertIsNone(error)
                self.assertEqual(exported["date"], ["2026-11-03"])

    def test_bounds_are_bound_to_source_id_city_province_and_weekday(self):
        for field, value in (("id_fonte", "99999"), ("citta", "Milano"), ("provincia", "MI"),
                             ("slug", "lo-mercap-216440-domenica"), ("url_fonte", "https://example.org/other")):
            with self.subTest(field=field):
                row = self.row()
                row[field] = value
                result, reason = refresh_record(row, TODAY)
                self.assertEqual(reason, "source_calendar_scope_unrepresented")
                self.assertEqual(result["date"], [])
                exported, error = normalize(row, TODAY)
                self.assertIsNone(error)
                self.assertEqual(exported["date"], [])
                self.assertEqual(exported["identita_fonte"]["dal"], "01/04")

    def test_a_saved_projection_flag_cannot_replace_missing_raw_scope(self):
        row = self.row()
        row["proiezione_regola"] = forecast_rule(row)
        row.pop("identita_fonte")
        row["ricorrenza_testo"] = "Ogni martedì"
        result, reason = refresh_record(row, TODAY)
        self.assertEqual(reason, "date_range_scope_unrepresented")
        self.assertEqual(result["date"], [])

    def test_raw_seasonal_name_and_explicit_exceptions_are_not_erased_by_weekly_label(self):
        row = self.row()
        row["identita_fonte"]["dal"] = row["identita_fonte"]["al"] = None
        row["ricorrenza_testo"] = "Ogni martedì"
        self.assertEqual(temporal_scope_hold(row), "seasonal_scope_unrepresented")
        self.assertEqual(refresh_record(row, TODAY)[0]["date"], [])
        row = self.row()
        row["ricorrenza_testo"] += "; esclusi i festivi"
        self.assertEqual(temporal_scope_hold(row), "calendar_exception_scope_unrepresented")
        row = self.row()
        row["ricorrenza_testo"] = "Ogni domenica"
        self.assertEqual(temporal_scope_hold(row), "source_calendar_scope_unrepresented")
        row = self.row()
        row["nome"] = "Mercato invernale"
        self.assertEqual(temporal_scope_hold(row), "seasonal_scope_unrepresented")
        row = self.row()
        row["ricorrenza_testo"] = "Mercato mensile"
        self.assertEqual(temporal_scope_hold(row), "source_calendar_scope_unrepresented")

    def test_lost_normalized_qualifier_cannot_make_bounded_source_an_annual_donor(self):
        row = self.row()
        row["ricorrenza_testo"] = "Ogni martedì"
        self.assertEqual(official_identity_issue(row), "official_raw_recurrence_not_annual_weekly")
        row["identita_fonte"]["al"] = "31/12;14/06"
        self.assertEqual(official_identity_issue(row), "official_raw_recurrence_not_annual_weekly")

    def test_newer_observation_replaces_old_scope_without_inheriting_old_boundaries(self):
        old = self.row("100361", "sabato")
        incoming = deepcopy(old)
        incoming["aggiornato_il"] = "2026-10-20"
        incoming["identita_fonte"]["dal"] = incoming["identita_fonte"]["al"] = None
        incoming["ricorrenza_testo"] = "Ogni sabato"
        merged, _ = combine([old], [incoming])
        self.assertEqual(len(merged), 1)
        self.assertEqual(merged[0]["slug"], old["slug"])
        self.assertIsNone(merged[0]["identita_fonte"]["dal"])
        result, reason = refresh_record(merged[0], TODAY)
        self.assertEqual(reason, "renewed")
        self.assertIn("2027-01-02", result["date"])

    def test_merge_cannot_restore_unbounded_projection_metadata_for_an_empty_source_calendar(self):
        for ident, day in (("100811", "giovedi"), ("101083", "mercoledi")):
            with self.subTest(ident=ident):
                incoming = self.row(ident, day)
                old = {**incoming, "aggiornato_il": "2026-10-06",
                       "date_quality": "prevista", "date": ["2026-11-05"],
                       "proiezione_regola": {"kind": "weekly", "weekdays": [3]},
                       "proiezione_generata_il": "2026-10-19", "proiezione_fonte": "ricorrenza_testo"}
                merged, _ = combine([old], [incoming])
                self.assertEqual(merged[0]["date_quality"], "sconosciuta")
                refreshed, _ = refresh_record(merged[0], TODAY)
                for result in (refreshed, normalize(merged[0], TODAY)[0], normalize(refreshed, TODAY)[0]):
                    self.assertEqual(result["date"], [])
                    self.assertIsNone(result["proiezione_regola"])
                    self.assertEqual(result["proiezione_generata_il"], "")
                    self.assertEqual(result["proiezione_fonte"], "")
                    self.assertEqual(result["slug"], incoming["slug"])

    def test_invalid_saved_field_remains_held_after_export_and_second_refresh(self):
        row = self.row()
        row["identita_fonte"]["al"] = ["31/10", "31/12"]
        exported, error = normalize(row, TODAY)
        self.assertIsNone(error)
        self.assertEqual(exported["date"], [])
        self.assertTrue(exported["identita_fonte"]["scope_invalid"])
        result, reason = refresh_record(exported, TODAY)
        self.assertEqual(reason, "source_calendar_scope_unrepresented")
        self.assertEqual(result["date"], [])


if __name__ == "__main__":
    unittest.main()
