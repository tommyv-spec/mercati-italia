"""An already-stored venue can be a lead, not proof of a unique city market."""
from __future__ import annotations
import copy
import sys
import unittest
from pathlib import Path
from datetime import date
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from stored_market_sibling_proposals import (
    analyze,verify,safe_stored_street,source_group_key,
)
from merge_catalog import load_existing

TODAY=date(2026,10,18)
VENICE="https://www.happings.com/it/mercati-settimanali-a-venezia.html"

def market(suffix,address="",*,city="Spinea",day="mercoledì",
           url=VENICE,name=None,publisher="happings.com",province="VE"):
    return {
        "slug":"mercato-settimanale-"+suffix,
        "nome":name or "Mercato settimanale di "+city,
        "fonte":publisher,"url_fonte":url,
        "regione":"Veneto","provincia":province,"citta":city,
        "indirizzo":address,"ricorrenza_testo":"settimanale - "+day,
        "date_quality":"prevista","date":["2026-10-21"],
        "orario_testo":"","verificato_il":"",
    }

class StoredPublisherSiblingAuditTests(unittest.TestCase):
    def test_two_missing_spinea_addresses_are_candidates_not_new_facts(self):
        rows=[market("a-spinea-spinea-mercoledi"),
              market("di-spinea-spinea"),
              market("di-spinea-spinea-mercoledi","Villaggio dei Fiori")]
        before=copy.deepcopy(rows)
        report=analyze(rows,today=TODAY)
        self.assertTrue(verify(report,3))
        self.assertEqual(report["field_sibling_candidates"],2)
        self.assertEqual(report["legacy_publisher_records_examined"],3)
        self.assertEqual(report["market_identities_preserved"],3)
        self.assertEqual(rows,before)
        for x in report["examples"]:
            self.assertTrue(x["not_independent_venue_confirmation"])
            self.assertFalse(x["automatic_fill_authorized"])
            self.assertFalse(x["source_html_accessed"])
            self.assertEqual(x["internal_street_already_stored"],"Villaggio dei Fiori")
        self.assertEqual(report["catalog_fields_updated"],0)

    def test_distinct_streets_same_city_and_day_must_not_transfer(self):
        rows=[market("missing"),market("street-a","Via Roma"),
              market("street-b","Piazza Fermi")]
        report=analyze(rows,today=TODAY)
        self.assertEqual(report["field_sibling_candidates"],0)
        self.assertEqual(report["counts"]["more_than_one_known_street_in_same_city_day"],1)

    def test_original_publisher_url_province_weekday_are_hard_identity_boundaries(self):
        main=market("known","Piazza Fermi",day="sabato")
        variant=[
            market("unknown",day="mercoledì"),
            market("unknown",day="sabato",province="PD"),
            market("unknown",day="sabato",url="https://www.happings.com/it/mercati-settimanali-a-padova.html"),
            market("unknown",day="sabato",city="Mirano"),
            market("unknown",day="sabato",publisher="cosedicasa.com"),
        ]
        for v in variant:
            with self.subTest(market=v):
                result=analyze([main,v],today=TODAY)
                self.assertEqual(result["field_sibling_candidates"],0)

    def test_nongeneric_named_venues_are_not_grouped_even_same_city(self):
        original=market("generic","Villaggio dei Fiori")
        named=market("branded",name="Mercatino vintage dei Fiori")
        result=analyze([original,named],today=TODAY)
        self.assertEqual(result["field_sibling_candidates"],0)

    def test_vague_and_likely_navigation_nonaddresses_are_excluded(self):
        for address in ("in centro","centro storico","Via mercati in Toscana",
                        "Via","mercati in Liguria","", "www.website.it",
                        "spazio pubblico"):
            with self.subTest(address=address):
                self.assertFalse(safe_stored_street(address))
        self.assertTrue(safe_stored_street("Piazza Fermi"))
        self.assertTrue(safe_stored_street("Villaggio dei Fiori"))
        self.assertTrue(safe_stored_street("Via Roma"))

    def test_no_false_weekday_join_if_slug_disagrees(self):
        wrong=market("di-spinea-spinea-sabato",address="")
        wrong["ricorrenza_testo"]="settimanale - mercoledì"
        correct=market("di-spinea-spinea-mercoledi",address="Villaggio dei Fiori")
        self.assertIsNone(source_group_key(wrong))
        result=analyze([wrong,correct],today=TODAY)
        self.assertEqual(result["field_sibling_candidates"],0)

    def test_audit_never_changes_record_count_or_permissions(self):
        result=analyze([market("a"),market("b","Via Roma")],today=TODAY)
        result["catalog_fields_updated"]=1
        with self.assertRaises(ValueError):
            verify(result,2)
        with self.assertRaisesRegex(ValueError,"Duplicated"):
            analyze([market("same"),market("same")],today=TODAY)

    def test_full_real_catalog_finds_internal_source_quality_opportunities(self):
        manifest=Path(__file__).resolve().parents[2]/"public/data/v1/manifest.json"
        if not manifest.is_file():
            self.skipTest("Full publisher catalog not mounted")
        rows=load_existing(manifest)
        original_ids=[r["slug"] for r in rows]
        report=analyze(rows,today=TODAY)
        self.assertTrue(verify(report,len(rows)))
        self.assertGreater(report["legacy_publisher_records_examined"],9000)
        self.assertGreater(report["field_sibling_candidates"],200)
        self.assertLess(report["field_sibling_candidates"],1300)
        self.assertEqual([r["slug"] for r in rows],original_ids)
        self.assertEqual(report["original_market_records_deleted"],0)

if __name__=="__main__":
    unittest.main()
