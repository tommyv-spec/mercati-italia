"""Observed province pages must be scanned even absent legacy catalog identities."""
import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from happings_source_enrichment import select_pages
ROOT="https://www.happings.com/it/"
GO=ROOT+"mercati-settimanali-a-gorizia-e-provincia/"
SP=ROOT+"mercati-settimanali-a-barcelona-e-provincia/"
AR=ROOT+"mercati-settimanali-a-arezzo-e-provincia/"
LEGACY=ROOT+"mercati-settimanali-a-arezzo.html"

class DiscoveredSourceRotation(unittest.TestCase):
    def test_new_italian_province_is_selected_without_preexisting_local_row(self):
        rows=[{"slug":"ex-1","nome":"un esempio",
            "fonte":"other.example","regione":"Toscana","provincia":"AR",
            "citta":"Arezzo","url_fonte":"https://other.example/" }]
        self.assertEqual(select_pages(rows,today=date(2026,10,21),
                         limit=16,resource_urls=[GO,SP]),[GO])
    def test_canonical_new_page_wins_over_observed_historic_alias(self):
        rows=[{"slug":"ex-1","nome":"un esempio",
            "fonte":"other.example","regione":"Toscana","provincia":"AR",
            "citta":"Arezzo","url_fonte":"https://other.example/" }]
        self.assertEqual(select_pages(rows,today=date(2026,10,21),limit=16,
                         resource_urls=[LEGACY,AR]),[AR])
    def test_no_invented_province_from_catalog_without_observed_link(self):
        rows=[{"slug":"ex-1","nome":"un esempio",
            "fonte":"other.example","regione":"Toscana","provincia":"AR",
            "citta":"Arezzo","url_fonte":"https://other.example/" }]
        self.assertEqual(select_pages(rows,today=date(2026,10,21),limit=16),[])
if __name__=="__main__":
    unittest.main()
