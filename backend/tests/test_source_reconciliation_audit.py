"""Read-only Lombardia MERCap reconciliation: no invented venue matches."""
from __future__ import annotations

import copy
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_reconciliation_audit import analyze, markdown

TODAY = date(2026, 10, 18)
SOURCE = "https://www.dati.lombardia.it/d/68zx-njaw"


def old(slug="legacy-pogliano-venerdi", street="Via Europa",
        city="Pogliano Milanese", province="MI", day="venerdi",
        hours="", coords=(45.53849, 8.99526), **extra):
    x = {
        "slug": slug, "regione": "Lombardia", "citta": city,
        "provincia": province, "indirizzo": street,
        "nome": "Mercato settimanale di " + city,
        "orario_testo": hours, "ricorrenza_testo": "Ogni " + day,
        "lat": coords[0], "lng": coords[1],
        "position_quality": "non_verificata",
        "url_fonte": "https://example.org/old", "verificato_il": "",
    }
    x.update(extra)
    return x


def official(n=1000):
    rows = []
    for i in range(n):
        rows.append({
            "slug": f"lo-mercap-{20000+i}-venerdi",
            "regione": "Lombardia", "citta": f"Citta {i}",
            "provincia": "PV", "indirizzo": f"Via Prova {i}",
            "nome": f"Mercato di Citta {i}",
            "orario_testo": "08:00–13:00 (fonte comunale, da verificare)",
            "ricorrenza_testo": "Ogni venerdì",
            "date_quality": "prevista", "verificato_il": "",
            "aggiornato_il": "2026-10-06", "url_fonte": SOURCE,
            "lat": None, "lng": None,
        })
    rows[0].update({
        "slug": "lo-mercap-100551-venerdi", "citta": "Pogliano Milanese",
        "provincia": "MI", "indirizzo": "VIA EUROPA",
        "lat": 45.53848875, "lng": 8.99526544,
    })
    return rows


class RegionalMatchingTests(unittest.TestCase):
    def test_real_venue_city_street_day_finds_missing_hours_without_writing(self):
        original = [old()]
        snapshot = copy.deepcopy(original)
        source = official()
        source_frozen = copy.deepcopy(source)
        result = analyze(original, source, today=TODAY)
        self.assertEqual(original, snapshot)
        self.assertEqual(source, source_frozen)
        self.assertEqual(result["baseline_catalog_records"], 1)
        self.assertEqual(result["counts"]["eligible_legacy_missing_hours_strong_match"], 1)
        self.assertEqual(result["counts"]["eligible_hours_source_id_held_or_not_published"], 1)
        self.assertEqual(result["market_updates_applied"], 0)
        self.assertEqual(result["individual_openings_confirmed"], 0)
        self.assertEqual(result["precise_coordinates_created"], 0)
        self.assertIn("legacy-pogliano-venerdi", markdown(result))

    def test_already_published_source_venue_is_a_distinct_matching_class(self):
        x = official()
        baseline = [old(),dict(x[0])]
        result = analyze(baseline, x, today=TODAY)
        self.assertEqual(result["counts"]["eligible_hours_source_id_already_published"], 1)
        self.assertEqual(result["counts"]["same_source_id_already_in_catalog"], 1)

    def test_bad_province_day_address_and_coordinates_do_not_match(self):
        changes = [
            old(province="BG"),
            old(day="lunedi"),
            old(street="Piazza del Comune"),
            old(coords=(46.2, 9.7)),
        ]
        for market in changes:
            with self.subTest(market=market):
                result = analyze([market], official(), today=TODAY)
                self.assertEqual(
                    result["counts"].get("eligible_legacy_missing_hours_strong_match",0),0)

    def test_duplicate_official_venue_day_never_enriches_a_legacy_market(self):
        group=official()
        group[1].update({
            "citta":group[0]["citta"],"provincia":group[0]["provincia"],
            "indirizzo":group[0]["indirizzo"],
        })
        result=analyze([old()],group,today=TODAY)
        self.assertEqual(result["counts"].get("eligible_legacy_missing_hours_strong_match",0),0)
        self.assertEqual(result["counts"]["strong_key_ambiguous_official_venue_day"],1)

    def test_missing_address_never_gets_auto_filled_even_with_nearby_point(self):
        result=analyze([old(street="")],official(),today=TODAY)
        self.assertEqual(result["counts"]["weak_missing_address_one_venue_nearby_review_only"],1)
        self.assertEqual(result["market_updates_applied"],0)
        self.assertEqual(result["counts"].get("eligible_legacy_missing_hours_strong_match",0),0)

    def test_exact_source_id_can_report_missing_fields_not_modify_them(self):
        f=official()
        source_card=dict(f[0])
        source_card["indirizzo"]=""
        source_card["orario_testo"]=""
        result=analyze([source_card],f,today=TODAY)
        self.assertEqual(result["counts"]["exact_source_id_missing_hours"],1)
        self.assertEqual(result["counts"]["exact_source_id_missing_address"],1)
        self.assertEqual(source_card["indirizzo"],"")
        self.assertEqual(source_card["orario_testo"],"")

    def test_snapshot_contract_rejects_duplicate_stale_or_foreign_sources(self):
        bad=official()
        bad[1]["slug"]=bad[0]["slug"]
        with self.assertRaisesRegex(ValueError, "Repeated"):
            analyze([old()],bad,today=TODAY)
        bad=official()
        bad[0]["aggiornato_il"]="2022-01-01"
        with self.assertRaisesRegex(ValueError, "old or future"):
            analyze([old()],bad,today=TODAY)
        bad=official()
        bad[0]["url_fonte"]="https://example.net/corrupt"
        with self.assertRaisesRegex(ValueError, "reviewed MERCap identity"):
            analyze([old()],bad,today=TODAY)
        with self.assertRaisesRegex(ValueError,"incomplete"):
            analyze([old()],official(100)[:100],today=TODAY)
        with self.assertRaisesRegex(ValueError,"Duplicate existing"):
            analyze([old(),old()],official(),today=TODAY)

    def test_source_identity_conflicts_are_not_mistaken_for_new_confirmation(self):
        same=official()
        mismatch=dict(same[0])
        mismatch["citta"]="Milano"
        result=analyze([mismatch],same,today=TODAY)
        self.assertEqual(result["counts"]["same_source_id_location_conflict"],1)
        self.assertEqual(result["individual_openings_confirmed"],0)


if __name__=="__main__":
    unittest.main()
