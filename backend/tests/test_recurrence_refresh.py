import json
import unittest
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from recurrence_refresh import (
    explicit_rule, forecast_source_limits, project_dates, refresh_record, refresh_records,
    temporal_scope_hold, forecast_rule,
)
from field_evidence import make_receipt


class ExplicitRules(unittest.TestCase):
    def test_weekly_day_from_both_formats(self):
        self.assertEqual(explicit_rule("settimanale - lunedì"), {"kind":"weekly","weekdays":[0]})
        self.assertEqual(explicit_rule("Ogni sabato"), {"kind":"weekly","weekdays":[5]})
        self.assertEqual(explicit_rule("Ogni martedì e giovedì"), {"kind":"weekly","weekdays":[1,3]})

    def test_digit_ordinals_and_tutti_i_read_like_their_words(self):
        monthly = lambda day, nth: {"kind": "monthly_nth_weekday", "weekday": day, "ordinal": nth}
        for text, rule in (("Ogni 4° Domenica Del Mese", monthly(6, 4)), ("Ogni 3a Domenica Del Mese", monthly(6, 3)),
                           ("1^ lunedì del mese", monthly(0, 1)), ("tutti i\nVenerdi", {"kind": "weekly", "weekdays": [4]}),
                           ("tutti i sabato e domenica", {"kind": "weekly", "weekdays": [5, 6]}),
                           ("Mercoledì tutto l'anno", {"kind": "weekly", "weekdays": [2]}),
                           ("martedì e venerdì tutto l’anno", {"kind": "weekly", "weekdays": [1, 4]}),
                           ("Domenica tutto l'anno tranne agosto", None),
                           # Two ordinals are two weeks, never one; prose after "tutti i" is not a rule.
                           ("2^ e 4^ martedì del mese", {"kind": "monthly_nth_weekday", "weekday": 1, "ordinals": [2, 4]}),
                           ("primo e terzo sabato del mese", {"kind": "monthly_nth_weekday", "weekday": 5, "ordinals": [1, 3]}),
                           ("la prima domenica del mese e il terzo sabato", None),
                           ("tutti i venerdì dal 23 giugno al 25 agosto", None)):
            with self.subTest(text=text):
                self.assertEqual(explicit_rule(text), rule)

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


class TemporalScopeForecastGuards(unittest.TestCase):
    now = date(2026, 10, 19)
    forecast_fields = {"date", "date_quality", "proiezione_regola",
                       "proiezione_generata_il", "proiezione_fonte"}

    def test_qualifier_is_found_in_each_original_identity_field(self):
        for field, value, expected in (
            ("nome", "Mercato settimanale estivo", "seasonal_scope_unrepresented"),
            ("nome_originale", "Mercato di Firenze (stagionale)", "seasonal_scope_unrepresented"),
            ("slug", "mercato-invernale-firenze-sabato", "seasonal_scope_unrepresented"),
            ("url_fonte", "https://organizzatore.example/mercato--estivo-.html",
             "seasonal_scope_unrepresented"),
            ("url_fonte", "https://organizzatore.example/mercato%20%28ogni%2015gg%29",
             "interval_scope_unrepresented"),
            ("ricorrenza_originale", "Ogni sabato alternato", "interval_scope_unrepresented"),
            ("ricorrenza_testo", "Ogni sabato durante la stagione", "seasonal_scope_unrepresented"),
        ):
            with self.subTest(field=field, value=value):
                original = record(**{field: value})
                frozen = deepcopy(original)
                self.assertEqual(temporal_scope_hold(original), expected)
                self.assertEqual(original, frozen)

    def test_seven_observed_shapes_retire_122_predictions_for_unknown_and_recent_sources(self):
        # Source identities from the real catalog, with deterministic copies of
        # its 19 Oct 2026 projection horizon. No production data are loaded or
        # patched by this test, and the implementation has no market-ID rules.
        cases = (
            ("Ramiseto (estivo)", "ramiseto--estivo-", 3),
            ("Ravenna", "ravenna--estivo-", 6),
            ("Ravenna", "ravenna--estivo-", 0),
            ("Riolo Terme", "riolo-terme--estivo-", 0),
            ("Riolo Terme (estivo)", "riolo-terme--estivo-", 0),
            ("Poggiorsini", "poggiorsini--ogni-15gg-", 4),
            ("Poggiorsini (ogni 15gg)", "poggiorsini--ogni-15gg-", 4),
        )
        weekdays = ("lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica")
        for source_date in ("", "2026-10-18"):
            originals = []
            for i, (name, page, day) in enumerate(cases):
                dates = [(self.now + timedelta(days=d)).isoformat() for d in range(121)
                         if (self.now + timedelta(days=d)).weekday() == day]
                originals.append(record(
                    slug="original-stable-id-" + str(i), nome="Mercato settimanale di " + name,
                    ricorrenza_testo="settimanale - " + weekdays[day],
                    fonte="happings.com", url_fonte="https://www.happings.com/it/mercato-settimanale-a-" + page + ".html",
                    fonte_aggiornata_il=source_date, aggiornato_il="2026-10-19T09:00:00",
                    indirizzo="Piazza della Repubblica", lat=43.77, lon=11.25,
                    verificato_il="", date=dates,
                    proiezione_regola={"kind": "weekly", "weekdays": [day]},
                    proiezione_generata_il="2026-10-19", proiezione_fonte="ricorrenza_testo",
                    fonti=[{"nome": "Fonte originale", "url": "https://example.com/originale"}],
                    riscontri_campi=[]))
            frozen = deepcopy(originals)
            with self.subTest(source_date=source_date):
                self.assertEqual(sum(len(row["date"]) for row in originals), 122)
                updated, report = refresh_records(originals, self.now)
                self.assertEqual(report["reasons"], {"seasonal_scope_unrepresented": 5,
                                                      "interval_scope_unrepresented": 2})
                self.assertEqual(report["temporal_scope_holds"], 7)
                self.assertEqual(report["temporal_scope_forecasts_withdrawn"], 7)
                self.assertEqual(report["temporal_scope_dates_withdrawn"], 122)
                self.assertEqual(report["newly_dated"], 0)
                self.assertEqual([r["slug"] for r in updated], [r["slug"] for r in originals])
                for before, after in zip(originals, updated):
                    self.assertEqual(after["date"], [])
                    self.assertEqual(after["date_quality"], "sconosciuta")
                    self.assertIsNone(after["proiezione_regola"])
                    self.assertEqual(after["proiezione_generata_il"], "")
                    self.assertEqual(after["proiezione_fonte"], "")
                    self.assertEqual({k: v for k, v in after.items() if k not in self.forecast_fields},
                                     {k: v for k, v in before.items() if k not in self.forecast_fields})
                self.assertEqual(originals, frozen)

    def test_temporal_limits_block_new_dates_without_inventing_a_bounded_rule(self):
        for title in ("Mercato estivo", "Mercato invernale", "Mercato ogni 15gg",
                      "Mercato ogni due settimane", "Mercato una volta all'anno"):
            with self.subTest(title=title):
                original = record(nome=title, date=[], date_quality="sconosciuta",
                                  fonte_aggiornata_il="2026-10-18")
                updated, reason = refresh_record(original, self.now)
                self.assertTrue(reason.endswith("scope_unrepresented"))
                self.assertEqual(updated, original)
                self.assertNotIn("proiezione_generata_il", updated)

    def test_calendar_exception_and_date_range_retire_even_with_unparseable_or_unknown_age(self):
        for recurrence, expected in (
            ("quindicinale", "interval_scope_unrepresented"),
            ("Ogni sabato, esclusi i festivi", "calendar_exception_scope_unrepresented"),
            ("Ogni sabato tranne agosto", "calendar_exception_scope_unrepresented"),
            ("Ogni sabato da giugno a settembre 2026", "date_range_scope_unrepresented"),
            ("Ogni sabato dal 1 giugno al 31 agosto", "date_range_scope_unrepresented"),
            ("Ogni sabato dal 01/06 al 31/08", "date_range_scope_unrepresented"),
            ("Ogni sabato soltanto nel mese di luglio", "date_range_scope_unrepresented"),
            ("Mercato sospeso", "calendar_exception_scope_unrepresented"),
        ):
            with self.subTest(recurrence=recurrence):
                original = record(ricorrenza_testo=recurrence, fonte_aggiornata_il="")
                updated, reason = refresh_record(original, self.now)
                self.assertEqual(reason, expected)
                self.assertEqual(updated["date"], [])
                self.assertEqual(updated["ricorrenza_testo"], recurrence)

    def test_reported_confirmed_and_human_reviewed_data_are_preserved(self):
        for patch_fields, expected in (
            ({"date_quality": "riportata"}, "non_projected_source_date"),
            ({"date_quality": "confermata"}, "non_projected_source_date"),
            ({"verificato_il": "2026-10-18"}, "verified_temporal_scope_preserved"),
            ({"date_quality": "sconosciuta", "date": [], "verificato_il": "2026-10-18"},
             "verified_temporal_scope_preserved"),
        ):
            with self.subTest(patch_fields=patch_fields):
                original = record(nome="Mercato estivo", **patch_fields)
                updated, reason = refresh_record(original, self.now)
                self.assertEqual(reason, expected)
                self.assertEqual(updated, original)

    def test_explicit_closed_month_cannot_generate_saturdays_during_the_closure(self):
        for source_date in ("", "2026-07-19"):
            with self.subTest(source_date=source_date):
                original = record(ricorrenza_testo="Ogni sabato, chiuso in agosto",
                                  fonte_aggiornata_il=source_date, date=["2026-08-01"])
                self.assertEqual(temporal_scope_hold(original), "calendar_exception_scope_unrepresented")
                updated, reason = refresh_record(original, date(2026, 7, 20))
                self.assertEqual(reason, "calendar_exception_scope_unrepresented")
                self.assertEqual(updated["date"], [])
                self.assertEqual(updated["date_quality"], "sconosciuta")
                self.assertEqual(updated["ricorrenza_testo"], original["ricorrenza_testo"])
                self.assertEqual(original["date"], ["2026-08-01"])

    def test_explicit_holiday_exception_cannot_generate_the_excluded_friday(self):
        for source_date in ("", "2026-10-18"):
            with self.subTest(source_date=source_date):
                original = record(slug="source-identity-venerdi",
                                  ricorrenza_testo="Ogni venerdì, eccetto Natale",
                                  fonte_aggiornata_il=source_date, date=["2026-12-25"])
                self.assertEqual(temporal_scope_hold(original), "calendar_exception_scope_unrepresented")
                updated, reason = refresh_record(original, self.now)
                self.assertEqual(reason, "calendar_exception_scope_unrepresented")
                self.assertEqual(updated["date"], [])
                self.assertEqual(updated["date_quality"], "sconosciuta")
                self.assertEqual(updated["slug"], original["slug"])
                self.assertEqual(original["date"], ["2026-12-25"])

    def test_unclassified_dates_are_not_removed_as_if_they_were_computed(self):
        original = record(nome="Mercato estivo", date_quality="sconosciuta")
        updated, reason = refresh_record(original, self.now)
        self.assertEqual(reason, "seasonal_scope_unrepresented")
        self.assertEqual(updated, original)

    def test_partial_recent_recurrence_receipt_does_not_erase_a_seasonal_identity(self):
        original = record(nome_originale="Mercato di Firenze (estivo)", fonte_aggiornata_il="")
        original["riscontri_campi"] = [make_receipt(
            original, values={"ricorrenza_testo": original["ricorrenza_testo"]},
            source_url="https://comune.example/mercati", source_name="Comune",
            source_id="weekly-only", source_row="weekly-venue", read_on=self.now.isoformat(),
            source_updated_on="2026-10-18", source_sha256="a" * 64,
            method="pagina_primaria_revisionata", scope="pagina", fingerprint_kind="html_bytes")]
        updated, reason = refresh_record(original, self.now)
        self.assertEqual(reason, "seasonal_scope_unrepresented")
        self.assertEqual(updated["date"], [])
        self.assertEqual(updated["riscontri_campi"], original["riscontri_campi"])
        repeated, second_reason = refresh_record(updated, self.now + timedelta(days=1))
        self.assertEqual(second_reason, reason)
        self.assertEqual(repeated, updated)

    def test_whole_words_and_temporal_context_avoid_place_and_transport_false_positives(self):
        for fields in (
            {"nome": "Mercato di Primavera", "citta": "Primavera"},
            {"nome": "Festival di Sestino", "url_fonte": "https://example.com/mercato-a-sestino"},
            {"nome": "Mercato delle Quattro Stagioni"},
            {"nome": "Natale Di Luci", "url_fonte": "https://example.com/natale-di-luci"},
            {"nome": "Mercato settimanale annuale", "ricorrenza_testo": "Cadenza settimanale annuale: sabato"},
            {"nome": "Mercato settimanale di Chiusa di Pesio"},
            {"nome": "Mercato settimanale in Inverno e Monteleone", "citta": "Inverno e Monteleone"},
            {"nome": "Mercato settimanale a San Salvo", "citta": "San Salvo",
             "slug": "mercato-settimanale-a-san-salvo-san-salvo-giovedi",
             "ricorrenza_testo": "settimanale - giovedì"},
            {"nome": "Mercatino di Merano, Passeggiata d'Inverno", "citta": "Merano",
             "indirizzo": '"Mercatino delle Pulci", Passeggiata d\'Inverno',
             "ricorrenza_testo": "mensile - ultimo sabato del mese"},
            {"nome": "Mercato in Via del Mercato Estivo", "indirizzo": "Via del Mercato Estivo"},
            {"url_fonte": "https://mercato-estivo.example/mercati?campagna=estivo#ogni-15gg"},
            {"url_fonte": "https://example.com/2026/06/15/mercati"},
            {"nome": "Mercato: dalle 8 alle 13", "orario_testo": "08:00–13:00"},
            {"ricorrenza_testo": "Ogni sabato, da 08:00 a 13:00"},
            {"ricorrenza_testo": "Ogni sabato, dal 08:00 al 13:00"},
            {"ricorrenza_testo": "Ogni sabato, dalle 8.30 alle 13.30"},
            {"ricorrenza_testo": "Ogni sabato, dal 8.30 al 13.30"},
        ):
            with self.subTest(fields=fields):
                original = record(**fields)
                self.assertIsNone(temporal_scope_hold(original))
                self.assertEqual(refresh_record(original, self.now)[1], "renewed")

    def test_declared_place_does_not_hide_a_separate_real_calendar_qualifier(self):
        original = record(nome="Mercato estivo in Passeggiata d'Inverno",
                          citta="Merano", indirizzo="Passeggiata d'Inverno")
        self.assertEqual(temporal_scope_hold(original), "seasonal_scope_unrepresented")
        original = record(nome="Mercato di San Salvo", citta="San Salvo",
                          ricorrenza_testo="Ogni sabato, salvo festivi")
        self.assertEqual(temporal_scope_hold(original), "calendar_exception_scope_unrepresented")
        original = record(nome="Mercato settimanale di Riolo Terme (estivo)",
                          citta="Riolo Terme (estivo)")
        self.assertEqual(temporal_scope_hold(original), "seasonal_scope_unrepresented")

    def test_intervals_already_fully_represented_by_the_rule_remain_supported(self):
        for title, recurrence in (
            ("Mercato ogni 7 giorni", "Ogni sabato"),
            ("Mercato ogni settimana", "Ogni sabato"),
            ("Mercato ogni 1 settimana", "Ogni martedì e sabato"),
            ("Mercato ogni 1 mese", "mensile - prima domenica del mese"),
            ("Mercato ogni giorno", "Ogni lunedì, martedì, mercoledì, giovedì, venerdì, sabato e domenica"),
        ):
            with self.subTest(title=title):
                original = record(nome=title, ricorrenza_testo=recurrence)
                self.assertIsNone(temporal_scope_hold(original))
                self.assertEqual(refresh_record(original, self.now)[1], "renewed")
        contradictory = record(nome="Mercato ogni 7 giorni", ricorrenza_testo="Ogni martedì e sabato")
        self.assertEqual(temporal_scope_hold(contradictory), "interval_scope_unrepresented")


class RepresentedMonthScopes(unittest.TestCase):
    cadence = "mensile - terza domenica del mese, da marzo a ottobre"
    rule = {"kind": "monthly_nth_weekday", "weekday": 6, "ordinal": 3,
            "active_months": list(range(3, 11))}

    def monthly_record(self, **extra):
        return record(slug="independent-monthly-source", ricorrenza_testo=self.cadence,
                      proiezione_regola=deepcopy(self.rule), **extra)

    def test_complete_month_scope_is_derived_without_changing_reader_rule_schema(self):
        original = self.monthly_record()
        self.assertEqual(explicit_rule(self.cadence),
                         {"kind": "monthly_nth_weekday", "weekday": 6, "ordinal": 3})
        self.assertEqual(forecast_rule(original), self.rule)
        self.assertIsNone(temporal_scope_hold(original))
        original.pop("proiezione_regola")
        self.assertEqual(forecast_rule(original), self.rule, "the text supplies the complete month scope")

    def test_recent_generic_monthly_source_returns_in_spring_with_forecast_provenance(self):
        original = self.monthly_record(fonte_aggiornata_il="2026-10-01", date=[],
                                       date_quality="sconosciuta")
        frozen = deepcopy(original)
        updated, reason = refresh_record(original, date(2027, 1, 20))
        self.assertEqual(reason, "renewed")
        self.assertEqual(updated["date"][:2], ["2027-03-21", "2027-04-18"])
        self.assertTrue(all(date.fromisoformat(day).month in range(3, 11) for day in updated["date"]))
        self.assertEqual(updated["date_quality"], "prevista")
        self.assertEqual(updated["proiezione_regola"], self.rule)
        self.assertEqual(updated["proiezione_fonte"], "ricorrenza_testo")
        self.assertEqual(original, frozen)

    def test_weekly_and_cross_year_month_ranges_never_generate_inactive_months(self):
        for text, months, first_day in (
            ("Ogni sabato, da giugno a settembre", [6, 7, 8, 9], "2026-09-26"),
            ("Ogni sabato, da novembre a febbraio", [1, 2, 11, 12], "2026-11-07"),
        ):
            with self.subTest(text=text):
                original = record(ricorrenza_testo=text, fonte_aggiornata_il="2026-09-19", date=[])
                self.assertEqual(forecast_rule(original)["active_months"], months)
                updated, reason = refresh_record(original, date(2026, 9, 20))
                self.assertEqual(reason, "renewed")
                self.assertEqual(updated["date"][0], first_day)
                self.assertTrue(all(date.fromisoformat(day).month in months for day in updated["date"]))

    def test_year_day_boundary_and_other_clauses_cannot_hide_behind_a_month_range(self):
        for recurrence in (
            self.cadence + " 2026", self.cadence + ", eccetto Natale",
            self.cadence + ", chiuso in agosto", self.cadence + ", ogni 15gg",
            self.cadence + ", dalle 8 alle 13",
            "mensile - terza domenica del mese, dal 15 marzo al 31 ottobre",
        ):
            with self.subTest(recurrence=recurrence):
                original = record(ricorrenza_testo=recurrence, fonte_aggiornata_il="2026-10-18")
                self.assertNotIn("active_months", forecast_rule(original) or {})
                self.assertIsNotNone(temporal_scope_hold(original))
                updated, _ = refresh_record(original, date(2026, 10, 19))
                self.assertEqual(updated["date"], [])
        original = self.monthly_record(nome_originale="Mercato annuale estivo")
        self.assertEqual(temporal_scope_hold(original), "seasonal_scope_unrepresented")

    def test_self_declared_or_conflicting_month_mask_cannot_override_the_source_text(self):
        for saved in (
            {**self.rule, "active_months": [1, 2]},
            {**self.rule, "active_months": tuple(range(3, 11))},
            {**self.rule, "active_months": [3, 3, 4]},
            {**self.rule, "weekday": 5},
        ):
            with self.subTest(saved=saved):
                original = self.monthly_record(fonte_aggiornata_il="2026-10-18")
                original["proiezione_regola"] = saved
                updated, reason = refresh_record(original, date(2026, 10, 19))
                self.assertEqual(reason, "date_range_scope_unrepresented")
                self.assertEqual(updated["date"], [])
        no_text_scope = self.monthly_record()
        no_text_scope["ricorrenza_testo"] = "mensile - terza domenica del mese"
        self.assertEqual(temporal_scope_hold(no_text_scope), "date_range_scope_unrepresented")

    def test_unknown_source_preserves_only_existing_compatible_dates_without_renewal(self):
        original = self.monthly_record(
            fonte_aggiornata_il="", aggiornato_il="2027-01-20T09:00:00",
            importato_il="2027-01-20T09:00:00+00:00", date=["2026-10-18"],
            proiezione_generata_il="2026-10-12", proiezione_fonte="ricorrenza_testo")
        frozen = deepcopy(original)
        unchanged, reason = refresh_record(original, date(2027, 1, 20))
        self.assertEqual(reason, "unknown_source_age")
        self.assertEqual(unchanged, frozen)
        original["date"].append("2026-11-15")
        filtered, reason = refresh_record(original, date(2027, 1, 20))
        self.assertEqual(reason, "existing_forecast_month_scope_filtered")
        self.assertEqual(filtered["date"], ["2026-10-18"])
        self.assertEqual(filtered["proiezione_generata_il"], "2026-10-12")
        self.assertEqual(filtered["fonte_aggiornata_il"], "")
        empty = self.monthly_record(fonte_aggiornata_il="", date=[], date_quality="sconosciuta")
        self.assertEqual(refresh_record(empty, date(2027, 1, 20)), (empty, "unknown_source_age"))

    def test_direct_projection_rejects_malformed_month_scope(self):
        for months in ([], [True], [0, 13], [3, 3], [10, 3], ["3"], (3, 4)):
            with self.subTest(months=months):
                with self.assertRaisesRegex(ValueError, "active month scope"):
                    project_dates({**self.rule, "active_months": months}, date(2026, 10, 19), 120)

    def test_month_scope_does_not_authorize_changes_to_reported_or_human_reviewed_dates(self):
        for protection in ({"date_quality": "riportata"}, {"date_quality": "confermata"},
                           {"verificato_il": "2026-10-18"}):
            with self.subTest(protection=protection):
                original = self.monthly_record(**protection)
                self.assertEqual(refresh_record(original, date(2026, 10, 19))[0], original)


class SourceContractForecastLimits(unittest.TestCase):
    now = date(2026, 10, 19)

    def config(self):
        config = json.loads((Path(__file__).resolve().parents[1] /
                             "data/market-source-contracts.json").read_text("utf-8"))
        profile = deepcopy(next(p for p in config["raw_profiles"]
                                if p["id"] == "bologna-generic-venues"))
        profile.update(id="fixture-approved-feed", catalog_slug_prefix="fixture-approved-")
        return {"schema": 1, "publication_role": "review_only",
                "normalized_profiles": [], "raw_profiles": [profile]}

    def scoped_record(self, config, age=400, **extra):
        profile = config["raw_profiles"][0]
        updated = (self.now - timedelta(days=age)).isoformat()
        return record(slug=profile["catalog_slug_prefix"] + "venue",
                      url_fonte=profile["attribution_url"],
                      fonte_aggiornata_il=updated, aggiornato_il=updated,
                      proiezione_fonte="ricorrenza_testo",
                      proiezione_generata_il="2026-10-01", **extra)

    def test_validated_contract_limits_include_disabled_reader_and_age_fallback(self):
        config = self.config()
        profile = config["raw_profiles"][0]
        profile["enabled"] = False
        self.assertEqual(forecast_source_limits(config),
                         ((profile["catalog_slug_prefix"], profile["attribution_url"], 365),))
        profile.pop("max_forecast_source_age_days")
        self.assertEqual(forecast_source_limits(config)[0][2], profile["max_source_age_days"])
        profile["max_forecast_source_age_days"] = profile["max_source_age_days"] + 1
        with self.assertRaisesRegex(ValueError, "Forecast age"):
            forecast_source_limits(config)

    def test_shadow_contract_does_not_claim_an_approved_projection_scope(self):
        config = self.config()
        config["raw_profiles"][0].update(publication_mode="shadow_only",
                                        legal_reuse_reviewed=False, max_new_ids_per_run=0)
        self.assertEqual(forecast_source_limits(config), ())

    def test_existing_400_day_forecast_expires_and_preserves_market_identity(self):
        config = self.config()
        original = self.scoped_record(config)
        before = deepcopy(original)
        limits = forecast_source_limits(config)
        expired, reason = refresh_record(original, self.now, source_limits=limits)
        self.assertEqual(reason, "expired_stale_forecast")
        self.assertEqual(expired["date"], [])
        self.assertEqual(expired["date_quality"], "sconosciuta")
        self.assertEqual(expired["proiezione_fonte"], "")
        self.assertEqual(expired["slug"], original["slug"])
        self.assertEqual(expired["ricorrenza_testo"], original["ricorrenza_testo"])
        self.assertEqual(expired["fonte_aggiornata_il"], original["fonte_aggiornata_il"])
        self.assertEqual(original, before)
        repeated, second_reason = refresh_record(expired, self.now, source_limits=limits)
        self.assertEqual(second_reason, "stale_source")
        self.assertEqual(repeated, expired)

    def test_forecast_boundary_and_global_limit_remain_conservative(self):
        config = self.config()
        limits = forecast_source_limits(config)
        self.assertEqual(refresh_record(self.scoped_record(config, 365), self.now,
                                        source_limits=limits)[1], "renewed")
        self.assertEqual(refresh_record(self.scoped_record(config, 366), self.now,
                                        source_limits=limits)[1], "expired_stale_forecast")
        self.assertEqual(refresh_record(self.scoped_record(config, 350), self.now,
                                        max_stale_days=300, source_limits=limits)[1],
                         "expired_stale_forecast")
        for quality in ("riportata", "confermata"):
            source = self.scoped_record(config, 400, date_quality=quality)
            self.assertEqual(refresh_record(source, self.now, source_limits=limits),
                             (source, "non_projected_source_date"))

    def test_scope_requires_both_stable_prefix_and_exact_source_url(self):
        config = self.config()
        limits = forecast_source_limits(config)
        for change in ({"slug": "unrelated-source-venue"},
                       {"url_fonte": "https://altro-comune.example/mercati"}):
            source = self.scoped_record(config)
            source.update(change)
            with self.subTest(change=change):
                self.assertEqual(refresh_record(source, self.now, source_limits=limits)[1],
                                 "renewed")
        generic = self.scoped_record(config, age=541)
        generic["slug"] = "unrelated-source-venue"
        self.assertEqual(refresh_record(generic, self.now, source_limits=limits)[1],
                         "expired_stale_forecast")

    def test_current_independent_receipt_can_support_expired_primary_with_own_limit(self):
        config = self.config()
        limits = forecast_source_limits(config)
        for content_age, expected in ((180, "renewed"), (181, "expired_stale_forecast")):
            source = self.scoped_record(config)
            source["riscontri_campi"] = [make_receipt(
                source, values={"ricorrenza_testo": source["ricorrenza_testo"]},
                source_url="https://organizzatore.example/mercati", source_name="Organizzatore",
                source_id="independent-calendar", source_row="weekly-venue",
                read_on=self.now.isoformat(),
                source_updated_on=(self.now - timedelta(days=content_age)).isoformat(),
                source_sha256="b" * 64, method="pagina_primaria_revisionata",
                scope="pagina", fingerprint_kind="html_bytes")]
            with self.subTest(content_age=content_age):
                result, reason = refresh_record(source, self.now, source_limits=limits)
                self.assertEqual(reason, expected)
                if reason == "renewed":
                    self.assertEqual(result["proiezione_fonte"], "riscontri_campi:ricorrenza_testo")
                    self.assertEqual(result["fonte_aggiornata_il"], source["fonte_aggiornata_il"])

    def test_batch_resolves_registry_once_and_default_scopes_apply(self):
        config = self.config()
        limits = forecast_source_limits(config)
        with patch("recurrence_refresh.forecast_source_limits", return_value=limits) as resolve:
            output, report = refresh_records([self.scoped_record(config) for _ in range(3)], self.now)
        resolve.assert_called_once_with()
        self.assertEqual(report["reasons"], {"expired_stale_forecast": 3})
        self.assertTrue(all(not row["date"] for row in output))
        defaults = forecast_source_limits()
        self.assertIs(defaults, forecast_source_limits())
        prefix, source_url, maximum = next(scope for scope in defaults if scope[0] == "bo-open-")
        existing = self.scoped_record(config)
        existing.update(slug=prefix + "fixture", url_fonte=source_url)
        self.assertEqual(maximum, 365)
        self.assertEqual(refresh_record(existing, self.now)[1], "expired_stale_forecast")


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
        for field, value in (("fonte_aggiornata_il", "2025-10-01"), ("letto_il", "2026-07-01")):
            with self.subTest(field=field, value=value):
                unproved = deepcopy(original)
                unproved["riscontri_campi"][0][field] = value
                self.assertEqual(refresh_record(unproved, self.now)[1], "unknown_source_age")

    def test_yearly_official_calendar_stays_current_until_its_year_ends(self):
        original = record(fonte_aggiornata_il="", aggiornato_il="2026-10-10")
        def listed(source_id, published, today):
            row = deepcopy(original)
            row["riscontri_campi"] = [make_receipt(
                row, values={"ricorrenza_testo": row["ricorrenza_testo"]},
                source_url="https://www.regione.veneto.it/calendario.pdf",
                source_name="Regione del Veneto", source_id=source_id, source_row="ve-calant-x",
                read_on=today.isoformat(), source_updated_on=published, source_sha256="d" * 64,
                method="id_fonte", scope="dataset", fingerprint_kind="publisher_parsed_json")]
            return refresh_record(row, today)[1]
        # The 2026 calendar is dated 1 January: past the 180-day limit, still current.
        self.assertEqual(listed("veneto-calendario-antiquariato", "2026-01-01", self.now), "renewed")
        self.assertEqual(listed("veneto-calendario-antiquariato", "2026-01-01", date(2026, 12, 31)), "renewed")
        for source_id, published, today in (
                ("veneto-calendario-antiquariato", "2026-01-01", date(2027, 1, 1)),
                ("veneto-calendario-antiquariato", "2026-01-02", self.now),
                ("independent-other-page", "2026-01-01", self.now)):
            with self.subTest(source_id=source_id, published=published, today=today):
                self.assertEqual(listed(source_id, published, today), "unknown_source_age")

    def test_page_still_listing_an_undated_recurrence_keeps_forecasts_renewing(self):
        original = record(fonte_aggiornata_il="", aggiornato_il="2026-10-10",
                          proiezione_fonte="ricorrenza_testo", proiezione_generata_il="2026-09-01")
        def listed(read_on):
            row = deepcopy(original)
            row["riscontri_campi"] = [make_receipt(
                row, values={"ricorrenza_testo": row["ricorrenza_testo"]},
                source_url="https://www.happings.com/it/x/", source_name="Happings",
                source_id="weekly-page", source_row="page:town:2", read_on=read_on,
                source_updated_on="", source_sha256="c" * 64,
                method="comune_provincia_giorno_univoco", scope="pagina", fingerprint_kind="html_bytes")]
            return row
        renewed, reason = refresh_record(listed((self.now - timedelta(days=45)).isoformat()), self.now)
        self.assertEqual(reason, "renewed")
        self.assertEqual(renewed["proiezione_fonte"], "riscontri_campi:ricorrenza_testo")
        self.assertEqual(renewed["date_quality"], "prevista")
        self.assertTrue(renewed["date"] and renewed["date"][-1] <= (self.now + timedelta(days=120)).isoformat())
        # The page stopped listing it (no read for 46 days): its forecasts lapse.
        lapsed = listed((self.now - timedelta(days=46)).isoformat())
        lapsed.update(date=renewed["date"], proiezione_fonte=renewed["proiezione_fonte"])
        result, reason = refresh_record(lapsed, self.now)
        self.assertEqual(reason, "expired_field_evidence_forecast")
        self.assertEqual(result["date"], [])

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
