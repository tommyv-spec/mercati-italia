import copy
import unittest
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalog_quality_report import analyze, suspicious_city, count_venue_weekday_groups


def mk(slug,city="Albizzate",region="Lombardia",street="Piazzale Sefro",
       recurrence="settimanale - martedì",future=None,quality="prevista",**kw):
    row={
        "slug":slug,"nome":"Mercato settimanale di "+city,
        "citta":city,"regione":region,"indirizzo":street,
        "ricorrenza_testo":recurrence,"orario_testo":"",
        "fonte":"happings.com","url_fonte":"https://example.org/markets/a",
        "date":future if future is not None else ["2026-10-13","2026-10-20"],
        "date_quality":quality,"lat":45.724163,"lng":8.797983,
        "verificato_il":"",
    }
    row.update(kw)
    return row


class CatalogQualityTests(unittest.TestCase):
    def test_real_albizzate_two_weekly_cards_are_review_only_not_merged(self):
        old=[
            mk("mercato-settimanale-di-albizzate-albizzate"),
            mk("mercato-settimanale-di-albizzate-albizzate-martedi"),
        ]
        frozen=copy.deepcopy(old)
        report=analyze(old)
        self.assertEqual(report["metrics"]["review_only_duplicate_groups"],1)
        self.assertEqual(report["metrics"]["review_only_potential_extra_rows"],1)
        self.assertEqual(report["metrics"]["hours_missing"],2)
        self.assertEqual(report["metrics"]["without_individual_verification"],2)
        self.assertTrue(report["potential_duplicates_are_not_confirmed"])
        self.assertEqual(report["market_updates_applied"],0)
        self.assertEqual(old,frozen)

    def test_weekday_or_location_distinction_does_not_create_a_duplicate(self):
        otherday=mk("market-friday",recurrence="settimanale - venerdì",
                     future=["2026-10-16","2026-10-23"])
        anotherstreet=mk("market-street",street="Via Monici")
        markets=[mk("market-tuesday"),otherday,anotherstreet]
        self.assertEqual(count_venue_weekday_groups(markets),[])

    def test_nongeneric_festivals_are_not_automatically_deduplicated(self):
        source=mk("green-festival",
                  nome="Green Market Festival",
                  street="Largo Dino Frisullo")
        another=mk("green-festival-x",nome="Green Market Christmas",
                   street="Largo Dino Frisullo")
        self.assertEqual(count_venue_weekday_groups([source,another]),[])

    def test_unknown_future_requires_unknown_quality(self):
        bad=mk("bad-quality",future=[],quality="prevista")
        wrong=analyze([bad])
        self.assertFalse(wrong["quality_release_safe"])
        self.assertEqual(wrong["metrics"]["future_date_quality_mismatch"],1)
        from export_static import normalize
        from datetime import date
        fixed,error=normalize(bad,date(2026,10,12))
        self.assertIsNone(error)
        self.assertEqual(fixed["date_quality"],"sconosciuta")
        good=analyze([fixed])
        self.assertTrue(good["quality_release_safe"])
        self.assertEqual(good["metrics"].get("future_date_quality_mismatch",0),0)

    def test_unambiguous_city_naming_anomalies_are_review_only(self):
        self.assertTrue(suspicious_city('"Mercatino delle Curiosità"'))
        self.assertTrue(suspicious_city(
            "Castiglione delle Stiviere, in provincia... Mercato settimanale a Cavriana"
        ))
        self.assertTrue(suspicious_city("Via Tiburtina - FROSINONE"))
        self.assertTrue(suspicious_city("AL"))
        # Italian municipalities really can be named Piazza Brembana,
        # Piazza al Serchio and Piazzatorre.
        self.assertFalse(suspicious_city("Piazza Brembana"))
        self.assertFalse(suspicious_city("Piazza al Serchio"))
        self.assertFalse(suspicious_city("Piazzatorre"))
        self.assertFalse(suspicious_city("San Pellegrino Terme"))

    def test_missing_hours_improve_without_claiming_human_verification(self):
        row=mk("one")
        report=analyze([row])
        newer={**row, "orario_testo":"08:00–13:00 (fonte comunale, da verificare)"}
        again=analyze([newer],report)
        self.assertEqual(again["baseline_delta"]["hours_missing"],-1)
        self.assertEqual(again["metrics"]["without_individual_verification"],1)
        self.assertEqual(again["market_confirmations_created"],0)

    def test_no_automatic_city_rewrites_or_erasure(self):
        original=mk("city-uncertain",city='"Mercatino delle Curiosità"')
        before=copy.deepcopy(original)
        result=analyze([original])
        self.assertEqual(result["metrics"]["suspicious_city"],1)
        self.assertEqual(original,before)
        self.assertEqual(result["market_identities_deleted"],0)

    def test_repeated_input_is_deterministic(self):
        market=mk("duplicate-input")
        a=analyze([market])
        self.assertEqual(a,analyze([market]))

    def test_invalid_previous_report_or_duplicate_ids_are_blocked(self):
        one=mk("duplicate")
        with self.assertRaisesRegex(ValueError,"Duplicate or missing"):
            analyze([one,one])
        with self.assertRaisesRegex(ValueError,"Untrusted prior"):
            analyze([one],{"schema":1,"review_only":False})
        with self.assertRaisesRegex(ValueError,"Invalid or unbounded"):
            analyze([])


if __name__=="__main__":
    unittest.main()
