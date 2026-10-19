import unittest
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from recurrence_refresh import explicit_rule, project_dates, refresh_record, refresh_records
from field_evidence import make_receipt


class ExplicitRules(unittest.TestCase):
    def test_weekly_day_from_both_formats(self):
        self.assertEqual(explicit_rule("settimanale - lunedì"), {"kind":"weekly","weekdays":[0]})
        self.assertEqual(explicit_rule("Ogni sabato"), {"kind":"weekly","weekdays":[5]})
        self.assertEqual(explicit_rule("Ogni martedì e giovedì"), {"kind":"weekly","weekdays":[1,3]})

    def test_monthly_not_misclassified_as_weekly(self):
        self.assertEqual(explicit_rule("ogni prima domenica del mese"),
                         {"kind":"monthly_nth_weekday","weekday":6,"ordinal":1})
        self.assertEqual(explicit_rule("mensile - terza domenica del mese"),
                         {"kind":"monthly_nth_weekday","weekday":6,"ordinal":3})
        self.assertEqual(explicit_rule("mensile - ultima domenica del mese"),
                         {"kind":"monthly_nth_weekday","weekday":6,"ordinal":-1})

    def test_ambiguous_never_generates_dates(self):
        for value in ("mensile", "settimanale", "Appuntamenti Fissi Settimanali",
                      "settimanale - m", "settimanale - ...", "ogni due settimane",
                      "ogni sabato alternato", "quarta settimana",
                      "mercato di sabato", "2026-11-25", "", None):
            with self.subTest(value=value):
                self.assertIsNone(explicit_rule(value))

    def test_dates_for_first_and_last_monthly_weekday(self):
        d=date(2026,10,11)
        first=project_dates(explicit_rule("prima domenica del mese"),d,120)
        self.assertEqual(first, ["2026-11-01","2026-12-06","2027-01-03","2027-02-07"][:len(first)])
        last=project_dates(explicit_rule("ultima domenica del mese"),d,120)
        self.assertEqual(last[:3], ["2026-10-25","2026-11-29","2026-12-27"])

    def test_weekly_horizon(self):
        dates=project_dates(explicit_rule("settimanale - sabato"),date(2026,10,11),120)
        self.assertEqual(dates[0],"2026-10-17")
        self.assertGreaterEqual(len(dates),16)
        self.assertTrue(all((date.fromisoformat(d).weekday()==5) for d in dates))


def record(**kw):
    return {
        "slug":"mercato-settimanale-di-firenze-firenze-sabato",
        "ricorrenza_testo":"settimanale - sabato",
        "aggiornato_il":"2026-02-09T09:00:00",
        "fonte_aggiornata_il":"2026-02-09",
        "date":["2026-10-17","2026-10-24"],
        "date_quality":"prevista",
        "fonte":"Fonte fixture con data dichiarata",
        "url_fonte":"https://example.com/weekly-firenze",
        "status":"non_confermato",
        **kw,
    }


class RefreshTests(unittest.TestCase):
    now=date(2026,10,11)

    def test_weekly_projection_renews_old_forecast_only(self):
        original=record()
        newer,reason=refresh_record(original,self.now)
        self.assertEqual(reason,"renewed")
        self.assertGreaterEqual(len(newer["date"]),16)
        self.assertEqual(newer["date"][0],"2026-10-17")
        self.assertEqual(newer["date_quality"],"prevista")
        self.assertEqual(newer["proiezione_fonte"],"ricorrenza_testo")
        self.assertEqual(newer["proiezione_generata_il"],"2026-10-11")
        self.assertEqual(original["date"],["2026-10-17","2026-10-24"],"must not mutate original")

    def test_empty_future_dates_are_recovered_without_claiming_confirmation(self):
        renewed,reason=refresh_record(record(date=[]),self.now)
        self.assertEqual(reason,"renewed")
        self.assertEqual(renewed["date"][0],"2026-10-17")
        self.assertEqual(renewed["date_quality"],"prevista")

    def test_confirmed_or_reported_dates_are_not_expanded(self):
        for quality in ("confermata","riportata"):
            old=record(date_quality=quality,date=["2026-10-17"])
            renewed,reason=refresh_record(old,self.now)
            self.assertEqual(reason,"non_projected_source_date")
            self.assertEqual(old,renewed)

    def test_stale_official_2024_predictions_expire_without_deleting_market(self):
        old=record(aggiornato_il="2024-05-27",fonte_aggiornata_il="2024-05-27",
                   fonte="Comune di Milano - CC BY",
                   proiezione_fonte="ricorrenza_testo", proiezione_generata_il="2026-10-01")
        renewed,reason=refresh_record(old,self.now)
        self.assertEqual(reason,"expired_stale_forecast")
        self.assertEqual(renewed["slug"],old["slug"])
        self.assertEqual(renewed["date"],[])
        self.assertEqual(renewed["date_quality"],"sconosciuta")
        self.assertEqual(renewed["proiezione_fonte"],"")
        self.assertEqual(old["date"],["2026-10-17","2026-10-24"])

    def test_stale_source_without_forecast_is_idempotent(self):
        old=record(aggiornato_il="2024-05-27",fonte_aggiornata_il="2024-05-27",
                   date=[],date_quality="sconosciuta")
        newer,reason=refresh_record(old,self.now)
        self.assertEqual(reason,"stale_source")
        self.assertEqual(newer,old)

    def test_expired_forecast_cannot_renew_without_updated_source(self):
        old=record(aggiornato_il="2024-05-27",fonte_aggiornata_il="2024-05-27",
                   date=["2026-10-17"],date_quality="prevista")
        expired,reason=refresh_record(old,self.now)
        self.assertEqual(reason,"expired_stale_forecast")
        again,reason_again=refresh_record(expired,self.now)
        self.assertEqual(reason_again,"stale_source")
        self.assertEqual(again,expired)

    def test_canceled_not_reanimated(self):
        newer,reason=refresh_record(record(status="annullato"),self.now)
        self.assertEqual(reason,"inactive")
        self.assertEqual(newer["date"],["2026-10-17","2026-10-24"])

    def test_missing_source_is_not_invented(self):
        older,reason=refresh_record(record(url_fonte=""),self.now)
        self.assertEqual(reason,"no_attributable_source")
        self.assertNotIn("proiezione_generata_il",older)

    def test_no_computed_date_incomplete_weekday(self):
        incomplete,reason=refresh_record(record(ricorrenza_testo="settimanale - m"),self.now)
        self.assertEqual(reason,"no_explicit_rule")
        self.assertEqual(incomplete["date"],["2026-10-17","2026-10-24"])

    def test_refresh_is_idempotent_on_same_day(self):
        one,stats1=refresh_records([record()],self.now)
        two,stats2=refresh_records(one,self.now)
        self.assertEqual(one,two)
        self.assertEqual(stats2["date_ranges_changed"],0)
        self.assertTrue(stats2["all_dates_marked_forecast"])

    def test_monthly_ordinal_is_not_weekly(self):
        monthly,why=refresh_record(record(
            ricorrenza_testo="mensile - seconda domenica del mese",date=[]
        ),self.now)
        self.assertEqual(why,"renewed")
        self.assertEqual(monthly["date"][:3],["2026-10-11","2026-11-08","2026-12-13"])

    def test_contradictory_source_weekday_holds_only_predicted_dates(self):
        original=record(ricorrenza_testo="Ogni martedì",
                        date=["2026-10-17","2026-10-24"])
        updated,reason=refresh_record(original,self.now)
        self.assertEqual(reason,"contradictory_weekday_identity_held")
        self.assertEqual(updated["slug"],original["slug"])
        self.assertEqual(updated["date"],[])
        self.assertEqual(updated["date_quality"],"sconosciuta")
        self.assertEqual(original["date"],["2026-10-17","2026-10-24"])

    def test_contradictory_weekday_does_not_change_reported_or_monthly_dates(self):
        original=record(ricorrenza_testo="Ogni martedì",date_quality="riportata")
        updated,reason=refresh_record(original,self.now)
        self.assertEqual(reason,"non_projected_source_date")
        self.assertEqual(updated,original)
        # A monthly nth-weekday event is not a weekly day-label claim:
        month=record(ricorrenza_testo="mensile - seconda domenica del mese",date=[])
        result,reason=refresh_record(month,self.now)
        self.assertEqual(reason,"renewed")
        self.assertEqual(result["date_quality"],"prevista")

    def test_multi_weekday_rule_may_contain_day_from_slug(self):
        original=record(ricorrenza_testo="Ogni martedì e sabato",date=[])
        result,reason=refresh_record(original,self.now)
        self.assertEqual(reason,"renewed")
        self.assertEqual(len(result["date"])>20,True)

    def test_guard_max_horizon(self):
        with self.assertRaises(ValueError):
            refresh_record(record(),self.now,horizon_days=730)

    def test_recent_import_timestamp_does_not_renew_existing_forecasts(self):
        original = record(fonte_aggiornata_il="", aggiornato_il="2026-10-11T09:00:00",
                          importato_il="2026-10-11T09:00:00+00:00",
                          proiezione_fonte="ricorrenza_testo", proiezione_generata_il="2026-10-01",
                          proiezione_regola={"kind": "weekly", "weekdays": [5]}, verificato_il="")
        before = deepcopy(original)
        updated, reason = refresh_record(original, self.now)
        self.assertEqual(reason, "unknown_source_age")
        self.assertEqual(updated, before)
        self.assertEqual(original, before)
        again, report = refresh_records([updated], self.now + timedelta(days=1))
        self.assertEqual(again, [before])
        self.assertEqual(report["unknown_source_dates_preserved_without_renewal"], 1)
        self.assertEqual(report["date_ranges_changed"], 0)
        self.assertEqual(report["newly_dated"], 0)

    def test_recent_source_read_without_content_date_cannot_create_dates(self):
        original = record(fonte_aggiornata_il="", fonte_letta_il="2026-10-11", date=[],
                          date_quality="sconosciuta", aggiornato_il="2026-10-11T09:00:00")
        updated, reason = refresh_record(original, self.now)
        self.assertEqual(reason, "unknown_source_age")
        self.assertEqual(updated, original)
        self.assertNotIn("proiezione_generata_il", updated)

    def test_reading_an_old_source_today_does_not_renew_its_forecast(self):
        original = record(fonte_aggiornata_il="2020-01-01", fonte_letta_il="2026-10-11",
                          importato_il="2026-10-11T09:00:00+00:00", aggiornato_il="2026-10-11T09:00:00")
        updated, reason = refresh_record(original, self.now)
        self.assertEqual(reason, "expired_stale_forecast")
        self.assertEqual(updated["date"], [])
        self.assertEqual(updated["slug"], original["slug"])
        self.assertEqual(updated["fonte_aggiornata_il"], "2020-01-01")
        self.assertNotIn("verificato_il", updated)

    def test_generic_dataset_marker_does_not_prove_content_age(self):
        original = record(fonte_aggiornata_il="", aggiornamento_ambito="dataset",
                          aggiornato_il="2026-10-10")
        updated, reason = refresh_record(original, self.now)
        self.assertEqual(reason, "unknown_source_age")
        self.assertEqual(updated, original)

    def test_reviewed_legacy_dataset_date_still_supports_explicit_forecasts(self):
        original = record(slug="lo-mercap-fixture-sabato", fonte_aggiornata_il="",
                          aggiornamento_ambito="dataset", aggiornato_il="2026-10-06",
                          url_fonte="https://www.dati.lombardia.it/d/68zx-njaw")
        updated, reason = refresh_record(original, self.now)
        self.assertEqual(reason, "renewed")
        self.assertGreaterEqual(len(updated["date"]), 16)
        self.assertEqual(updated["aggiornato_il"], "2026-10-06")
        self.assertEqual(updated["fonte_aggiornata_il"], "")
        self.assertNotIn("verificato_il", updated)

    def test_invalid_or_future_content_date_cannot_hide_behind_recent_import(self):
        for content, expected in (("2026-10-10Tinvalid", "unknown_source_age"),
                                  ("2027-01-01", "source_from_future")):
            with self.subTest(content=content):
                original = record(fonte_aggiornata_il=content, aggiornato_il="2026-10-10T09:00:00")
                updated, reason = refresh_record(original, self.now)
                self.assertEqual(reason, expected)
                self.assertEqual(updated, original)

    def test_declared_content_date_still_requires_a_valid_source_url(self):
        for url in ("https://", "https://[invalid", "https://example.org:bad"):
            with self.subTest(url=url):
                original = record(url_fonte=url)
                updated, reason = refresh_record(original, self.now)
                self.assertEqual(reason, "no_attributable_source")
                self.assertEqual(updated, original)

    def test_exact_recent_recurrence_receipt_can_support_rolling_forecast(self):
        original = record(fonte_aggiornata_il="", aggiornato_il="2026-10-10")
        receipt = make_receipt(original, values={"ricorrenza_testo": original["ricorrenza_testo"]},
            source_url="https://comune.example/mercati", source_name="Comune", source_id="primary-page",
            source_row="stable-weekly-identity", read_on=self.now.isoformat(),
            source_updated_on="2026-10-01", source_sha256="a" * 64,
            method="pagina_primaria_revisionata", scope="pagina", fingerprint_kind="html_bytes")
        original["riscontri_campi"] = [receipt]
        updated, reason = refresh_record(original, self.now)
        self.assertEqual(reason, "renewed")
        self.assertEqual(updated["date_quality"], "prevista")
        self.assertEqual(updated["fonte_aggiornata_il"], "")
        self.assertEqual(updated["aggiornato_il"], original["aggiornato_il"])
        self.assertEqual(updated["proiezione_fonte"], "riscontri_campi:ricorrenza_testo")
        for field, value in (("fonte_aggiornata_il", ""), ("fonte_aggiornata_il", "2025-10-01"),
                             ("letto_il", "2026-07-01")):
            with self.subTest(field=field, value=value):
                unproved = deepcopy(original)
                unproved["riscontri_campi"][0][field] = value
                self.assertEqual(refresh_record(unproved, self.now)[1], "unknown_source_age")

    def field_supported_projection(self):
        original = record(fonte_aggiornata_il="", aggiornato_il="2024-01-01",
                          indirizzo="Piazza della Repubblica")
        original["riscontri_campi"] = [make_receipt(
            original, values={"ricorrenza_testo": original["ricorrenza_testo"],
                              "indirizzo": original["indirizzo"]},
            source_url="https://comune.example/mercati", source_name="Comune",
            source_id="primary-page", source_row="stable-weekly-identity",
            read_on=self.now.isoformat(), source_updated_on="2026-10-01",
            source_sha256="a" * 64, method="pagina_primaria_revisionata",
            scope="pagina", fingerprint_kind="html_bytes")]
        projected, reason = refresh_record(original, self.now)
        self.assertEqual(reason, "renewed")
        self.assertEqual(projected["proiezione_fonte"], "riscontri_campi:ricorrenza_testo")
        return projected

    def test_withdrawn_recurrence_receipt_retires_only_its_generated_calendar(self):
        before = self.field_supported_projection()
        # The new source contradicts the day. The evidence layer has removed
        # that claim while preserving the independently unchanged address.
        before["riscontri_campi"][0]["valori"].pop("ricorrenza_testo")
        frozen = deepcopy(before)
        result, reason = refresh_record(before, self.now + timedelta(days=1))
        self.assertEqual(reason, "expired_field_evidence_forecast")
        self.assertEqual(result["date"], [])
        self.assertEqual(result["date_quality"], "sconosciuta")
        self.assertEqual(result["proiezione_fonte"], "")
        self.assertEqual(result["proiezione_generata_il"], "")
        self.assertIsNone(result["proiezione_regola"])
        for field in ("slug", "indirizzo", "ricorrenza_testo", "aggiornato_il",
                      "fonte_aggiornata_il", "riscontri_campi", "status"):
            self.assertEqual(result[field], before[field])
        self.assertEqual(before, frozen)
        repeated, _ = refresh_record(result, self.now + timedelta(days=1))
        self.assertEqual(repeated, result)

    def test_expired_field_read_cannot_preserve_its_forecast_using_unknown_primary_age(self):
        before = self.field_supported_projection()
        result, reason = refresh_record(before, self.now + timedelta(days=46))
        self.assertEqual(reason, "expired_field_evidence_forecast")
        self.assertEqual(result["date"], [])
        self.assertEqual(result["riscontri_campi"], before["riscontri_campi"])

    def test_another_current_recurrence_receipt_or_primary_source_can_keep_forecasting(self):
        before = self.field_supported_projection()
        other = deepcopy(before["riscontri_campi"][0])
        other["fonte_id"] = "independent-other-page"
        other["url"] = "https://organizzatore.example/calendario"
        before["riscontri_campi"][0]["valori"].pop("ricorrenza_testo")
        before["riscontri_campi"].append(other)
        after, reason = refresh_record(before, self.now + timedelta(days=1))
        self.assertEqual(reason, "renewed")
        self.assertTrue(after["date"])
        # An unusable future date on the primary must not hide an otherwise
        # current independent receipt or falsely retire its calendar.
        before["fonte_aggiornata_il"] = (self.now + timedelta(days=3)).isoformat()
        after, reason = refresh_record(before, self.now + timedelta(days=1))
        self.assertEqual(reason, "renewed")
        self.assertEqual(after["proiezione_fonte"], "riscontri_campi:ricorrenza_testo")
        before["riscontri_campi"] = []
        before["fonte_aggiornata_il"] = self.now.isoformat()
        after, reason = refresh_record(before, self.now + timedelta(days=1))
        self.assertEqual(reason, "renewed")
        self.assertEqual(after["proiezione_fonte"], "ricorrenza_testo")

    def test_field_withdrawal_preserves_legacy_and_reported_calendars(self):
        for quality, basis, expected in (
                ("prevista", "ricorrenza_testo", "unknown_source_age"),
                ("confermata", "riscontri_campi:ricorrenza_testo", "non_projected_source_date"),
                ("riportata", "riscontri_campi:ricorrenza_testo", "non_projected_source_date")):
            with self.subTest(quality=quality, basis=basis):
                before = self.field_supported_projection()
                before["riscontri_campi"] = []
                before["date_quality"] = quality
                before["proiezione_fonte"] = basis
                after, reason = refresh_record(before, self.now + timedelta(days=1))
                self.assertEqual(reason, expected)
                self.assertEqual(after, before)


if __name__=="__main__":
    unittest.main()
