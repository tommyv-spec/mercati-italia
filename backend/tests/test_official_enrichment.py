import copy
import unittest
from datetime import date
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from official_enrichment import enrich, hours_allowed, distance_km
from export_static import normalize, prepare

TODAY=date(2026,10,12)


def old(slug="mercato-settimanale-di-albizzate-albizzate-martedi",
        city="Albizzate",street="Piazzale Sefro",day="martedì",
        lat=45.724163,lng=8.797983,hours="",**kwargs):
    row={
        "slug":slug,"nome":"Mercato settimanale di "+city,
        "regione":"Lombardia","citta":city,
        "indirizzo":street,"ricorrenza_testo":"settimanale - "+day,
        "date_quality":"prevista","date":["2026-10-13","2026-10-20"],
        "lat":lat,"lng":lng,"position_quality":"non_verificata",
        "orario_testo":hours,
        "fonte":"happings.com",
        "url_fonte":"https://www.happings.com/it/mercato-settimanale-a-albizzate.html",
        "aggiornato_il":"2026-06-05","verificato_il":"",
    }
    row.update(kwargs)
    return row


def official(sid="100001",city="Albizzate",street="PIAZZALE SEFRO",
             day="martedi",lat=45.72485,lng=8.79787,hours=None,**kw):
    row={
        "slug":"lo-mercap-"+sid+"-"+day,
        "id_fonte":sid,
        "regione":"Lombardia","citta":city,"indirizzo":street,
        "ricorrenza_testo":"Ogni martedì",
        "date_quality":"prevista","verificato_il":"",
        "orario_testo":hours or "08:00–13:00 (fonte comunale, da verificare)",
        "lat":lat,"lng":lng,"aggiornato_il":"2026-10-06",
        "url_fonte":"https://www.dati.lombardia.it/d/68zx-njaw"
    }
    row.update(kw)
    return row


class EnrichmentTests(unittest.TestCase):
    def test_observed_albizzate_regional_hours_fill_two_legacy_copies(self):
        before=[
            old(slug="mercato-settimanale-di-albizzate-albizzate"),
            old(),
        ]
        frozen=copy.deepcopy(before)
        enriched,report=enrich(before,[official()],today=TODAY)
        self.assertEqual(len(enriched),2)
        self.assertEqual(report["existing_market_hours_added"],2)
        self.assertEqual(report["official_source_attributions_added"],2)
        for entry in enriched:
            self.assertEqual(entry["orario_testo"],
                             "08:00–13:00 (fonte comunale, da verificare)")
            self.assertEqual(entry["aggiornato_il"],"2026-06-05")
            self.assertEqual(entry["fonte"],"happings.com")
            self.assertEqual(entry["date_quality"],"prevista")
            self.assertEqual(entry["verificato_il"],"")
            self.assertEqual(len(entry["fonti"]),2)
            self.assertEqual(entry["lat"],45.724163)
            normalized,error=normalize(entry,TODAY)
            self.assertIsNone(error)
            self.assertEqual(len(normalized["fonti"]),2)
        self.assertEqual(before,frozen)

    def test_observed_arsago_and_pogliano_are_distinct(self):
        arsago=old(slug="mercato-settimanale-di-arsago-seprio-arsago-seprio-mercoledi",
                   city="Arsago Seprio",street="Via Monici",day="mercoledì",
                   lat=45.689255,lng=8.732757)
        pogliano=old(slug="mercato-settimanale-di-pogliano-milanese-pogliano-milanese-venerdi",
                    city="Pogliano Milanese",street="Via europa",day="venerdì",
                    lat=45.539548,lng=8.996178)
        new,stats=enrich([arsago,pogliano],[
            official(sid="100004",city="Arsago Seprio",street="VIA MONICI",
                     day="mercoledi",lat=45.68906475,lng=8.73153404,
                     ricorrenza_testo="Ogni mercoledì"),
            official(sid="100551",city="Pogliano Milanese",street="VIA EUROPA",
                     day="venerdi",lat=45.53848875,lng=8.99526544,
                     ricorrenza_testo="Ogni venerdì",
                     hours="08:00–12:00 (fonte comunale, da verificare)")
        ],today=TODAY)
        self.assertEqual(stats["existing_market_hours_added"],2)
        self.assertEqual(new[0]["orario_testo"],"08:00–13:00 (fonte comunale, da verificare)")
        self.assertEqual(new[1]["orario_testo"],"08:00–12:00 (fonte comunale, da verificare)")

    def test_mismatched_city_address_day_or_coordinates_not_merged(self):
        oldrow=old()
        cases=[
            official(city="Rho"),
            official(street="VIA MONICI"),
            official(ricorrenza_testo="Ogni venerdì",slug="lo-mercap-100001-venerdi"),
            official(lat=45.8,lng=8.8),
            official(url_fonte="https://example.org/untrusted"),
        ]
        for idx,r in enumerate(cases):
            if idx==4:
                with self.assertRaisesRegex(ValueError,"contract"):
                    enrich([oldrow],[r],today=TODAY)
            else:
                result,stats=enrich([oldrow],[r],today=TODAY)
                self.assertEqual(result[0]["orario_testo"],"")
                self.assertEqual(stats["existing_market_hours_added"],0)

    def test_legacy_hours_never_replaced(self):
        oldrow=old(hours="08:30–13:30 (sito organizzatore)")
        value,report=enrich([oldrow],[official()],today=TODAY)
        self.assertEqual(value[0]["orario_testo"],oldrow["orario_testo"])
        self.assertEqual(report["existing_market_hours_added"],0)
        self.assertEqual(report["official_source_attributions_added"],1)

    def test_conflicting_two_official_markets_same_venue_day_skips(self):
        result,summary=enrich([old()],[official(),official(sid="100002")],today=TODAY)
        self.assertEqual(result[0]["orario_testo"],"")
        self.assertEqual(summary["existing_market_hours_added"],0)
        self.assertEqual(summary["counts"]["skipped_multiple_official_markets_same_venue_day"],2)

    def test_stale_source_and_unverified_hours_are_not_added(self):
        v,summary=enrich([old()],[official(aggiornato_il="2022-06-01")],today=TODAY)
        self.assertEqual(summary["existing_market_hours_added"],0)
        self.assertEqual(v[0]["orario_testo"],"")
        v,summary=enrich([old()],[official(orario_testo="sempre aperto")],today=TODAY)
        self.assertEqual(summary["existing_market_hours_added"],0)

    def test_already_enriched_returns_identical_records(self):
        first,_=enrich([old()],[official()],today=TODAY)
        second,report=enrich(first,[official()],today=TODAY)
        self.assertEqual(first,second)
        self.assertEqual(report["existing_market_hours_added"],0)
        self.assertEqual(report["official_source_attributions_added"],0)

    def test_no_verification_or_false_coordinates_ever_added(self):
        entry=old(verificato_il="2026-10-11",
                  date_quality="confermata")
        result,_=enrich([entry],[official()],today=TODAY)
        self.assertEqual(result[0]["verificato_il"],"2026-10-11")
        self.assertEqual(result[0]["date_quality"],"confermata")
        self.assertEqual(result[0]["position_quality"],"non_verificata")

    def test_protect_timezone_label_and_monthly_ambiguous_dates(self):
        self.assertFalse(hours_allowed("08:00–13:00"))
        self.assertFalse(hours_allowed("00:00–00:00 (fonte comunale, da verificare)"))
        self.assertFalse(hours_allowed("Sempre"))
        self.assertTrue(hours_allowed("08:00–13:00 (fonte comunale, da verificare)"))
        self.assertTrue(hours_allowed(
            "Inverno: 07:30–13:00; Estate: 07:00–13:00 (fonte comunale, da verificare)"
        ))
        self.assertIsNone(distance_km({"lat":None},{"lng":8}))

    def test_enrichment_keeps_export_identity_and_distinct_weekday(self):
        baseline=[old(),old(slug="legacy-other-day",day="venerdì")]
        updated,stats=enrich(baseline,[official()],today=TODAY)
        normalized,metrics=prepare(updated,TODAY)
        self.assertEqual(len(normalized),2)
        self.assertEqual(stats["exact_matches"],1)
        self.assertEqual(normalized[0]["slug"],"legacy-other-day")
        self.assertNotIn("orario_testo", {})
        self.assertEqual({x["slug"] for x in normalized},
                         {"mercato-settimanale-di-albizzate-albizzate-martedi","legacy-other-day"})


if __name__ == "__main__":
    unittest.main()
