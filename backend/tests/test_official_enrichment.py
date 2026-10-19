import copy
import unittest
from datetime import date
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))

from official_enrichment import (enrich, hours_allowed, distance_km,
                                 street_identity, explicit_annual_weekday,
                                 official_identity_issue)
from field_evidence import attach_feed_observations, valid_receipt
from export_static import normalize, prepare
from source_lombardia import MONTHS

TODAY=date(2026,10,12)


def old(slug="mercato-settimanale-di-albizzate-albizzate-martedi",
        city="Albizzate",street="Piazzale Sefro",day="martedì",
        lat=45.724163,lng=8.797983,hours="",**kwargs):
    row={
        "slug":slug,"nome":"Mercato settimanale di "+city,
        "regione":"Lombardia","citta":city,
        "categoria":"misto", "tags":[],
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
        "categoria":"misto", "tags":["mercato comunale", "MERCAP"],
        "ricorrenza_testo":"Ogni martedì",
        "date_quality":"prevista","verificato_il":"",
        "orario_testo":hours or "08:00–13:00 (fonte comunale, da verificare)",
        "lat":lat,"lng":lng,"aggiornato_il":"2026-10-06",
        "url_fonte":"https://www.dati.lombardia.it/d/68zx-njaw"
    }
    row["identita_fonte"] = {
        "schema": 1, "periodicita_tipo": "SETTIMANALE", "giorno": day,
        "frequenza_settimanale": None,
        "mesi_svolgimento": ", ".join(m.upper() for m in MONTHS),
        "n_post_alim": "1", "n_post_non_alim": "1", "n_post_tot": "2",
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
        self.assertEqual(report["counts"]["existing_hours_differ_from_official"], 1)
        self.assertEqual(report["preserved_hours_differences"][0]["existing_hours"],
                         oldrow["orario_testo"])

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

    def test_conflicting_slug_weekday_or_province_cannot_transfer_hours(self):
        same_source = official(provincia="MI")
        contradicted = old(
            slug="mercato-settimanale-di-albizzate-albizzate-martedi",
            day="venerdì", provincia="MI"
        )
        result, report = enrich([contradicted], [same_source], today=TODAY)
        self.assertEqual(report["existing_market_hours_added"], 0)
        self.assertEqual(result[0]["orario_testo"], "")

        wrong_province = old(provincia="VA")
        result, report = enrich([wrong_province], [same_source], today=TODAY)
        self.assertEqual(report["existing_market_hours_added"], 0)
        self.assertEqual(report["counts"]["skipped_province_conflict"], 1)

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

    def test_observed_empty_civic_and_accent_spellings_recover_hours(self):
        # Exact spelling patterns observed in MERCap rows 100126, 101346,
        # 100368 and 100378. No expansion of names or street substrings.
        for existing, published in (
            ("Via Palù", "VIA PALU'"),
            ("Via Cà Zenucchi", "VIA CA' ZENUCCHI"),
            ("Piazza G. Ardizzone", "PIAZZA G.ARDIZZONE, SNC"),
            ("Piazza della Pace", "PIAZZA DELLA PACE, /"),
            ("Via Mauri", "VIA MAURI, S.N.C."),
        ):
            with self.subTest(street=existing):
                before = old(street=existing, provincia="VA")
                source = official(street=published, provincia="VA")
                result, report = enrich([before], [source], today=TODAY)
                self.assertEqual(report["existing_market_hours_added"], 1)
                self.assertEqual(report["counts"]["observed_spelling_matches"], 1)
                self.assertEqual(result[0]["indirizzo"], existing)
                self.assertEqual(result[0]["aggiornato_il"], before["aggiornato_il"])
                self.assertEqual(report["field_updates"][0]["official_street"], published)
                self.assertNotIn("riscontri_campi", result[0])

    def test_meaningful_civics_road_boundaries_and_initials_remain_distinct(self):
        for existing, published in (
            ("Via Roma", "VIA ROMA, 12"),
            ("Via Roma, 12", "VIA ROMA, 15"),
            ("Via Roma, 12/A", "VIA ROMA, 12/B"),
            ("Via Roma", "VIA ROMA; VIA MILANO"),
            ("Viale Caduti Via Indipendenza", "VIALE CADUTI/VIA INDIPENDENZA"),
            ("Via Roma; Via Milano", "VIA MILANO; VIA ROMA"),
            ("Via G. Garibaldi", "VIA GIUSEPPE GARIBALDI"),
            ("Via D'Adda", "VIA D ADDA"),
        ):
            with self.subTest(existing=existing, published=published):
                self.assertNotEqual(street_identity(existing), street_identity(published))
                result, report = enrich(
                    [old(street=existing, provincia="VA")],
                    [official(street=published, provincia="VA")], today=TODAY)
                self.assertEqual(report["existing_market_hours_added"], 0)
                self.assertEqual(result[0]["orario_testo"], "")

    def test_empty_civic_match_blocked_by_second_official_civic_or_extent(self):
        for other_street in ("VIA MAURI, 12", "VIA MAURI; VIA MILANO"):
            with self.subTest(other=other_street):
                result, report = enrich(
                    [old(street="Via Mauri", provincia="VA")],
                    [official(street="VIA MAURI, SNC", provincia="VA"),
                     official(sid="100002", street=other_street, provincia="VA")],
                    today=TODAY)
                self.assertEqual(report["existing_market_hours_added"], 0)
                self.assertEqual(report["counts"]["skipped_conflicting_civic_or_road_extent"], 1)
                self.assertEqual(result[0]["orario_testo"], "")

    def test_unknown_day_at_second_official_civic_is_not_proof_of_distinction(self):
        unknown = official(sid="100002", street="VIA MAURI, 12", provincia="VA",
                           day="senza-giorno", ricorrenza_testo="Date da verificare")
        result, report = enrich(
            [old(street="Via Mauri", provincia="VA")],
            [official(street="VIA MAURI, SNC", provincia="VA"), unknown], today=TODAY)
        self.assertEqual(report["existing_market_hours_added"], 0)
        self.assertEqual(result[0]["orario_testo"], "")

    def test_known_distinct_weekday_does_not_block_spelling_match(self):
        different_day = official(sid="100002", street="VIA MAURI, 12", provincia="VA",
                                 day="venerdi", ricorrenza_testo="Ogni venerdì")
        _, report = enrich(
            [old(street="Via Mauri", provincia="VA")],
            [official(street="VIA MAURI, SNC", provincia="VA"), different_day], today=TODAY)
        self.assertEqual(report["existing_market_hours_added"], 1)

    def test_normalized_duplicate_official_streets_block_both_candidates(self):
        _, report = enrich(
            [old(street="Via Palù", provincia="VA")],
            [official(street="VIA PALU'", provincia="VA"),
             official(sid="100002", street="VIA PALU'", provincia="VA")], today=TODAY)
        self.assertEqual(report["existing_market_hours_added"], 0)

    def test_spelling_match_requires_province_and_generic_market_identity(self):
        source = official(street="VIA PALU'", provincia="VA")
        for row in (old(street="Via Palù"),
                    old(street="Via Palù", provincia="VA", nome="Fiera dei fiori")):
            _, report = enrich([row], [source], today=TODAY)
            self.assertEqual(report["existing_market_hours_added"], 0)
            self.assertEqual(report["counts"]["skipped_spelling_match_without_full_identity"], 1)

    def test_source_observation_follows_only_identical_transferred_hours(self):
        source = official(street="VIA PALU'", provincia="VA", fonte="Regione Lombardia")
        observed = attach_feed_observations(
            "lombardia", {"fixture": "source row"}, [source], read_on=TODAY)[0]
        before = old(street="Via Palù", provincia="VA")
        result, report = enrich([before], [observed], today=TODAY)
        self.assertEqual(report["field_observation_records_updated"], 1)
        receipt = result[0]["riscontri_campi"][0]
        self.assertTrue(valid_receipt(receipt, result[0], today=TODAY))
        self.assertEqual(set(receipt["valori"]), {"orario_testo"})
        self.assertEqual(receipt["mercato"]["slug"], before["slug"])
        self.assertEqual(receipt["riga_fonte"], "100001")
        self.assertEqual(receipt["metodo"], "sede_giorno_provincia")
        self.assertEqual(receipt["letto_il"], "2026-10-12")
        second, repeated = enrich(result, [observed], today=TODAY)
        self.assertEqual(result, second)
        self.assertEqual(repeated["field_observation_records_updated"], 0)

    def test_conflicting_existing_hours_cannot_gain_source_observation(self):
        source = official(provincia="VA", fonte="Regione Lombardia")
        observed = attach_feed_observations(
            "lombardia", {"fixture": "source row"}, [source], read_on=TODAY)[0]
        before = old(provincia="VA", hours="09:00–12:00")
        result, report = enrich([before], [observed], today=TODAY)
        self.assertEqual(report["existing_market_hours_added"], 0)
        self.assertEqual(report["field_observation_records_updated"], 0)
        self.assertEqual(result[0]["orario_testo"], "09:00–12:00")
        self.assertNotIn("riscontri_campi", result[0])

    def test_slug_and_projected_dates_cannot_supply_missing_or_limited_recurrence(self):
        # Regression for MERCap 38846 (Breno, fortnightly) and 76670
        # (Corteno Golgi, summer only), which have valid weekday ID suffixes.
        unsupported = [
            "", "settimanale", "Date da verificare",
            "Periodicità: QUINDICINALE; giorno indicato martedì; date da verificare",
            "Periodicità: STAGIONALE; giorno indicato martedì; date da verificare",
            "Giorno dichiarato martedì; mesi di attività limitati",
            "mensile - primo martedì del mese", "Ogni primo martedì del mese",
            "Ogni martedì in estate", "settimanale - martedì (luglio e agosto)",
            "Ogni martedì e venerdì",
        ]
        for recurrence in unsupported:
            for side in ("source", "target"):
                with self.subTest(recurrence=recurrence, side=side):
                    source = official(provincia="VA", fonte="Regione Lombardia")
                    before = old(provincia="VA", hours=source["orario_testo"])
                    (source if side == "source" else before)["ricorrenza_testo"] = recurrence
                    source["date"] = ["2026-10-13", "2026-10-20", "2026-10-27"]
                    observed = attach_feed_observations(
                        "lombardia", {"fixture": "limited schedule"}, [source], read_on=TODAY)[0]
                    result, report = enrich([before], [observed], today=TODAY)
                    self.assertEqual(result, [before])
                    self.assertEqual(report["exact_matches"], 0)
                    self.assertEqual(report["field_observation_records_updated"], 0)
                    self.assertTrue(report["identity_conflicts"])

    def test_weekday_identity_suffix_is_only_a_contradiction_veto(self):
        self.assertEqual(explicit_annual_weekday(old()), frozenset({1}))
        self.assertEqual(explicit_annual_weekday(old(
            slug="mercato-settimanale-di-albizzate-albizzate-venerdi")), frozenset())
        self.assertEqual(explicit_annual_weekday(old(
            ricorrenza_testo="", date=["2026-10-13", "2026-10-20"])), frozenset())

    def test_specialized_market_type_does_not_borrow_generic_market_hours(self):
        cases = [
            old(categoria="alimentare"),
            old(categoria="antiquariato"),
            old(nome="Fiera dei fiori"),
            old(tags=["produttori locali"]),
            old(url_fonte="https://www.eventiesagre.it/Mercatini_Filiera+Corta/123.html"),
        ]
        for before in cases:
            with self.subTest(row=before):
                result, report = enrich([before], [official()], today=TODAY)
                self.assertEqual(result, [before])
                self.assertEqual(report["existing_market_hours_added"], 0)
                self.assertEqual(report["counts"]["skipped_market_type_unproved_or_conflicting"], 1)
                self.assertEqual(report["identity_conflicts"][0]["action"],
                                 "held_without_evidence_transfer")
        result, _ = enrich([old()], [official(categoria="alimentare")], today=TODAY)
        self.assertEqual(result, [old()])

    def test_filtered_seasonal_market_still_blocks_an_ambiguous_same_venue(self):
        seasonal = official(sid="100002", ricorrenza_testo=(
            "Periodicità: STAGIONALE; giorno indicato martedì; date da verificare"))
        before = old()
        result, report = enrich([before], [official(), seasonal], today=TODAY)
        self.assertEqual(result, [before])
        self.assertEqual(report["existing_market_hours_added"], 0)
        self.assertEqual(report["counts"]["skipped_multiple_official_markets_same_venue_day"], 1)

    def test_raw_source_qualifiers_veto_broad_normalized_category_and_recurrence(self):
        qualifiers = [
            {"periodicita_tipo": "QUINDICINALE"},
            {"periodicita_tipo": "GIORNALIERO"},
            {"frequenza_settimanale": "1^ e 3^"},
            {"mesi_svolgimento": "LUGLIO, AGOSTO"},
            {"giorno": "VENERDÌ"},
            # Live MERCap 100370, Saturday Castano Primo: food only.
            {"n_post_alim": "20", "n_post_non_alim": "0", "n_post_tot": "20"},
            {"n_post_alim": None}, {"n_post_non_alim": ""},
            {"n_post_non_alim": True}, {"n_post_non_alim": "1.5"},
            {"n_post_tot": "3"},
        ]
        for change in qualifiers:
            with self.subTest(qualifiers=change):
                source = official()
                source["identita_fonte"].update(change)
                before = old()
                result, report = enrich([before], [source], today=TODAY)
                self.assertEqual(result, [before])
                self.assertEqual(report["exact_matches"], 0)
                self.assertTrue(report["identity_conflicts"])
        missing = official()
        del missing["identita_fonte"]
        self.assertEqual(official_identity_issue(missing), "official_raw_identity_missing")
        self.assertEqual(enrich([old()], [missing], today=TODAY)[0], [old()])

    def test_engine_owned_hours_follow_same_official_row_newer_content(self):
        before = [old(provincia="VA"), old(slug="other-stable-copy", provincia="VA")]
        first_source = official(provincia="VA", fonte="Regione Lombardia")
        first_source = attach_feed_observations(
            "lombardia", {"version": 1}, [first_source], read_on=TODAY)[0]
        first, _ = enrich(before, [first_source], today=TODAY)
        for entry in first:
            self.assertEqual(entry["riscontri_campi"][0]["campi_gestiti"], ["orario_testo"])
        tomorrow = date(2026, 10, 13)
        next_source = official(provincia="VA", fonte="Regione Lombardia", aggiornato_il="2026-10-13",
                               hours="08:30–13:30 (fonte comunale, da verificare)")
        next_source = attach_feed_observations(
            "lombardia", {"version": 2}, [next_source], read_on=tomorrow)[0]
        changed, report = enrich(first, [next_source], today=tomorrow)
        self.assertEqual(report["existing_market_hours_added"], 0)
        self.assertEqual(report["managed_market_hours_updated"], 2)
        self.assertEqual([entry["slug"] for entry in changed], [entry["slug"] for entry in before])
        for old_entry, entry in zip(first, changed):
            self.assertEqual(entry["orario_testo"], next_source["orario_testo"])
            self.assertEqual(entry["date"], old_entry["date"])
            self.assertEqual(entry["aggiornato_il"], old_entry["aggiornato_il"])
            self.assertEqual(entry["riscontri_campi"][0]["versioni_precedenti"][0]["valori"],
                             {"orario_testo": old_entry["orario_testo"]})
        repeated, again = enrich(changed, [next_source], today=tomorrow)
        self.assertEqual(repeated, changed)
        self.assertEqual(again["managed_market_hours_updated"], 0)
        self.assertTrue(all(change["previous_evidence"] for change in report["field_updates"]))

    def test_noop_legacy_receipt_and_changed_source_id_cannot_authorize_overwrites(self):
        source = official(provincia="VA", fonte="Regione Lombardia")
        source = attach_feed_observations("lombardia", {"version": 1}, [source], read_on=TODAY)[0]
        plain = old(provincia="VA", hours=source["orario_testo"])
        observed, _ = enrich([plain], [source], today=TODAY)
        self.assertNotIn("campi_gestiti", observed[0]["riscontri_campi"][0])
        owned, _ = enrich([old(provincia="VA")], [source], today=TODAY)
        tomorrow = date(2026, 10, 13)
        for baseline, sid in ((observed, "100001"), (owned, "100002")):
            with self.subTest(source_id=sid):
                newer = official(sid=sid, provincia="VA", fonte="Regione Lombardia",
                                 hours="09:00–13:00 (fonte comunale, da verificare)")
                newer = attach_feed_observations("lombardia", {"version": 2}, [newer], read_on=tomorrow)[0]
                result, report = enrich(baseline, [newer], today=tomorrow)
                self.assertEqual(result[0]["orario_testo"], baseline[0]["orario_testo"])
                self.assertEqual(report["managed_market_hours_updated"], 0)


if __name__ == "__main__":
    unittest.main()
