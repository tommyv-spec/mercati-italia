import unittest
from datetime import date, timedelta
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from recurrence_refresh import explicit_rule, project_dates, refresh_record, refresh_records


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
        "date":["2026-10-17","2026-10-24"],
        "date_quality":"prevista",
        "fonte":"happings.com",
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
        old=record(aggiornato_il="2024-05-27",fonte="Comune di Milano - CC BY",
                   proiezione_fonte="ricorrenza_testo", proiezione_generata_il="2026-10-01")
        renewed,reason=refresh_record(old,self.now)
        self.assertEqual(reason,"expired_stale_forecast")
        self.assertEqual(renewed["slug"],old["slug"])
        self.assertEqual(renewed["date"],[])
        self.assertEqual(renewed["date_quality"],"sconosciuta")
        self.assertEqual(renewed["proiezione_fonte"],"")
        self.assertEqual(old["date"],["2026-10-17","2026-10-24"])

    def test_stale_source_without_forecast_is_idempotent(self):
        old=record(aggiornato_il="2024-05-27",date=[],date_quality="sconosciuta")
        newer,reason=refresh_record(old,self.now)
        self.assertEqual(reason,"stale_source")
        self.assertEqual(newer,old)

    def test_expired_forecast_cannot_renew_without_updated_source(self):
        old=record(aggiornato_il="2024-05-27",
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

    def test_guard_max_horizon(self):
        with self.assertRaises(ValueError):
            refresh_record(record(),self.now,horizon_days=730)


if __name__=="__main__":
    unittest.main()
