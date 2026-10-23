"""Platform-independent accented ISTAT identity regression.

The pinned municipality JSON is UTF-8. On Windows, implicit cp1252 decoding
caused mojibake in the regional editorial evidence gate (six broken rows).
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from editorial_calendar_scope import geography_matches, istat_geography, text_key


class ISTATEncodingTests(unittest.TestCase):
    def test_canonical_accented_names_survive_utf8_source_read(self):
        found = istat_geography()
        self.assertEqual(len(found), 7894)
        cases = (
            ("Forlì", "FC", "Emilia-Romagna"),
            ("Ciriè", "TO", "Piemonte"),
            ("Mondovì", "CN", "Piemonte"),
            ("Portobuffolè", "TV", "Veneto"),
        )
        for city, province, region in cases:
            with self.subTest(city=city):
                self.assertIn((text_key(city), province, text_key(region)), found)

    def test_city_evidence_matches_exact_province_and_region(self):
        for city, province, region in (
                ("Forlì", "FC", "Emilia-Romagna"),
                ("Ciriè", "TO", "Piemonte"),
                ("Mondovì", "CN", "Piemonte"),
                ("Portobuffolè", "TV", "Veneto")):
            with self.subTest(city=city):
                row = {"citta": city, "provincia": province, "regione": region}
                observed = {"city": city, "province": province, "region": region}
                self.assertTrue(geography_matches(row, observed))
                self.assertFalse(geography_matches(
                    row, {**observed, "province": "RM"}))


if __name__ == "__main__":
    unittest.main()
