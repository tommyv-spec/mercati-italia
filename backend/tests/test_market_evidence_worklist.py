"""All incomplete market identities remain and every field has provenance."""
from __future__ import annotations
import copy
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from market_evidence_worklist import analyze, validate, registry_check, fields, family
from merge_catalog import load_existing
from source_lombardia import SOURCE_PAGE
CONTRACTS=json.loads((ROOT/"data/market-evidence-source-families.json").read_text("utf-8"))
TODAY=date(2026,10,18)


def market(sid,*,city="Pogliano Milanese",province="MI",street="",day="venerdì",
           hours="",publisher="happings.com",date_quality="prevista",coordinate=None):
    lat,lng=coordinate or (45.539,8.996)
    return {
        "slug":sid,"regione":"Lombardia","provincia":province,"citta":city,
        "nome":"Mercato settimanale di "+city,"indirizzo":street,
        "ricorrenza_testo":"Ogni "+day,
        "orario_testo":hours,"date":[(TODAY+timedelta(days=5)).isoformat()],
        "date_quality":date_quality,"fonte":publisher,
        "url_fonte":"https://www.happings.com/it/happing/test-pogliano",
        "lat":lat,"lng":lng,"position_quality":"non_verificata",
        "verificato_il":"","aggiornato_il":"2026-10-13",
        "status":"non_confermato",
    }


def official(sid="100551",*,city="Pogliano Milanese",province="MI",
             street="VIA EUROPA",day="venerdì",hours="08:00–12:00 (fonte comunale, da verificare)",
             coords=(45.5384,8.9953)):
    return {
        "slug":"lo-mercap-"+sid+"-venerdi","regione":"Lombardia",
        "provincia":province,"citta":city,"nome":"Mercato di "+city,
        "indirizzo":street,"ricorrenza_testo":"Ogni "+day,
        "orario_testo":hours,"date_quality":"prevista",
        "verificato_il":"","lat":coords[0],"lng":coords[1],
        "aggiornato_il":"2026-10-06","url_fonte":SOURCE_PAGE,
    }


class PerMarketEvidenceTests(unittest.TestCase):
    def test_five_source_layouts_are_known_but_never_grant_scraping_rights(self):
        self.assertTrue(registry_check(CONTRACTS))
        self.assertEqual(family("happings.com",CONTRACTS)["id"],
                         "happings-weekly-or-detail")
        self.assertEqual(family("unknown-town-site",CONTRACTS)["rights"],
                         "not_approved")
        for field in ("may_grant_source_reuse_rights","may_apply_field_changes",
                      "may_confirm_individual_market_dates"):
            bad=copy.deepcopy(CONTRACTS)
            bad[field]=True
            with self.subTest(field=field),self.assertRaises(ValueError):
                registry_check(bad)
        bad=copy.deepcopy(CONTRACTS)
        bad["families"][0]["bulk_scrape_allowed"]=True
        with self.assertRaises(ValueError):
            registry_check(bad)

    def test_all_incomplete_market_rows_and_legacy_sources_are_retained(self):
        rows=[
            market("m-one"),
            market("m-two",publisher="eventiesagre.it",street="Centro"),
            market("m-three",publisher="cosedicasa.com",street="Via Roma",
                   hours="09:00–13:00"),
            market("m-four",publisher="Comune inesistente",city="Ferrara",
                   province="FE",street="Via Nuova"),
        ]
        original=copy.deepcopy(rows)
        report=analyze(rows,CONTRACTS,today=TODAY,shards=1)
        self.assertTrue(validate(report,len(rows)))
        self.assertEqual(rows,original)
        self.assertEqual(report["market_records_scanned"],len(rows))
        self.assertEqual(report["market_identities_preserved"],len(rows))
        self.assertEqual(report["market_rows_removed"],0)
        self.assertEqual(report["market_rows_added"],0)
        self.assertEqual(report["market_fields_changed"],0)
        self.assertEqual(report["confirmed_openings_added"],0)
        self.assertEqual(report["distinct_source_labels"],4)
        self.assertEqual({x["market_id"] for x in report["daily_worklist"]},
                         {x["slug"] for x in rows})
        self.assertEqual(report["missing_by_field"]["individual_edition_confirmation"],4)
        self.assertTrue(all(x["source_incomplete_record_retained"] for x in report["daily_worklist"]))

    def test_source_unique_town_day_only_is_not_an_address_confirmation(self):
        entry=market("m-no-address")
        report=analyze([entry],CONTRACTS,official=[official()],today=TODAY,shards=1)
        self.assertTrue(validate(report,1))
        task=report["daily_worklist"][0]
        self.assertEqual(task["official_match"],"city_weekday_only_unconfirmed_venue")
        lead=task["official_evidence"][0]
        self.assertEqual(lead["field"],"indirizzo")
        self.assertEqual(lead["source_id"],"lo-mercap-100551-venerdi")
        self.assertFalse(lead["can_apply"])
        self.assertFalse(lead["opening_verified"])
        self.assertFalse(lead["exact_venue_identity_confirmed"])
        self.assertEqual(entry["indirizzo"],"")

    def test_exact_street_weekday_supports_missing_hours_but_not_verification(self):
        entry=market("legacy-pogliano-venerdi",street="Via Europa")
        report=analyze([entry],CONTRACTS,official=[official()],today=TODAY,shards=1)
        task=report["daily_worklist"][0]
        self.assertEqual(task["official_match"],"unique_city_province_street_weekday")
        proof=task["official_evidence"][0]
        self.assertEqual(proof["field"],"orario_testo")
        self.assertTrue(proof["can_apply"])
        self.assertFalse(proof["opening_verified"])
        self.assertEqual(proof["source_url"],SOURCE_PAGE)
        self.assertEqual(entry["orario_testo"],"")
        self.assertEqual(report["official_join_results"]["exact_field_evidence_candidates"],1)

    def test_different_province_date_conflict_and_coordinates_are_not_matched(self):
        cases=[
            market("m-wrongprovince",street="Via Europa",province="VA"),
            market("m-wrongday",street="Via Europa",day="martedì"),
            market("m-faraway",street="Via Europa",coordinate=(46.4,9.5)),
        ]
        for row in cases:
            with self.subTest(slug=row["slug"]):
                result=analyze([row],CONTRACTS,official=[official()],today=TODAY,shards=1)
                task=result["daily_worklist"][0]
                self.assertEqual(task["official_evidence"],[])
                self.assertEqual(row["orario_testo"],"")

    def test_two_official_venues_same_city_day_never_guess_street(self):
        official_two=official(sid="100552",street="VIA TORINO")
        report=analyze([market("unknown")],CONTRACTS,official=[official(),official_two],
                       today=TODAY,shards=1)
        row=report["daily_worklist"][0]
        self.assertEqual(row["official_match"],"no_usable_source_match")
        self.assertEqual(row["source_conflict"],"many_market_places_on_same_city_day")
        self.assertEqual(row["official_evidence"],[])

    def test_same_source_id_can_find_missing_street_without_creating_new_market(self):
        src=official()
        old=market(src["slug"],street="",publisher="Regione Lombardia – MERCap (CC0 1.0 dichiarata)")
        old["url_fonte"]=SOURCE_PAGE
        report=analyze([old],CONTRACTS,official=[src],today=TODAY,shards=1)
        matches=report["daily_worklist"][0]["official_evidence"]
        matching=next(x for x in matches if x["field"]=="indirizzo")
        self.assertTrue(matching["can_apply"])
        self.assertEqual(report["market_fields_changed"],0)

    def test_stale_official_snapshots_cannot_supply_fresh_evidence(self):
        src=official()
        src["aggiornato_il"]="2023-01-01"
        result=analyze([market("legacy",street="Via Europa")],CONTRACTS,official=[src],
                       today=TODAY,shards=1)
        self.assertEqual(result["official_source_status"],"stale_or_empty_source")
        self.assertEqual(result["daily_worklist"][0]["official_evidence"],[])

    def test_weekday_mismatch_with_slug_is_not_accepted(self):
        row=market("mercato-pogliano-venerdi",street="Via Europa",day="martedì")
        out=analyze([row],CONTRACTS,official=[official()],today=TODAY,shards=1)
        self.assertEqual(out["daily_worklist"][0]["official_evidence"],[])

    def test_31_day_rotation_is_fair_no_truncation_and_full_audit_every_day(self):
        records=[market("venue-"+str(i),street="" if i%2 else "Centro")
                 for i in range(310)]
        seen=set()
        for offset in range(31):
            d=TODAY+timedelta(days=offset)
            out=analyze(records,CONTRACTS,today=d)
            self.assertTrue(validate(out,310))
            self.assertEqual(out["market_records_scanned"],310)
            seen.update(x["market_id"] for x in out["daily_worklist"])
        self.assertEqual(seen,{x["slug"] for x in records})

    def test_real_national_catalog_every_market_is_kept_in_review(self):
        manifest=ROOT.parent/"public/data/v1/manifest.json"
        if not manifest.exists():
            self.skipTest("Catalog only becomes available after source migration")
        originals=load_existing(manifest)
        self.assertGreater(len(originals),12_000)
        before={m["slug"] for m in originals}
        report=analyze(originals,CONTRACTS,today=TODAY)
        self.assertTrue(validate(report,len(originals)))
        self.assertEqual(report["market_identities_preserved"],len(before))
        self.assertEqual(len(before),len(originals))
        self.assertGreaterEqual(report["distinct_source_labels"],40)
        self.assertGreater(len(report["daily_worklist"]),0)
        self.assertEqual(before,{m["slug"] for m in originals})
        self.assertEqual(report["market_rows_removed"],0)

    def test_invalid_source_signature_and_duplicate_market_ids_fail_closed(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            analyze([market("x"),market("x")],CONTRACTS,today=TODAY)
        corrupt=official()
        corrupt["url_fonte"]="https://evil.example/market"
        with self.assertRaises(ValueError):
            analyze([market("m")],CONTRACTS,official=[corrupt],today=TODAY)
        bad=official()
        bad["verificato_il"]="2026-10-18"
        with self.assertRaises(ValueError):
            analyze([market("m")],CONTRACTS,official=[bad],today=TODAY)
        result=analyze([market("m")],CONTRACTS,today=TODAY,shards=1)
        result["market_rows_removed"]=1
        with self.assertRaises(ValueError):
            validate(result,1)

if __name__=="__main__":
    unittest.main()
