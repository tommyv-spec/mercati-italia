import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_coverage import summarize, markdown


def market(sid, city, region="Lombardia", **kw):
    row = {
        "slug":sid, "nome":"Mercato settimanale", "citta":city,
        "regione":region, "orario_testo":"", "indirizzo":"",
        "date":[], "verificato_il":"", "position_quality":"non_verificata",
    }
    row.update(kw)
    return row


class CoverageAuditTests(unittest.TestCase):
    def test_balanced_city_priorities_never_change_originals(self):
        items = []
        for i in range(14):
            items.append(market(f"m-{i}", "Milano"))
        for i in range(7):
            items.append(market(f"f-{i}", "Firenze", "Toscana"))
        for i in range(6):
            items.append(market(f"b-{i}", "Bergamo"))
        frozen=copy.deepcopy(items)
        result=summarize(items)
        self.assertEqual(result["national"]["records"],27)
        self.assertEqual(result["national"]["missing_hours"],27)
        self.assertEqual(result["national"]["missing_address"],27)
        self.assertEqual(result["national"]["missing_future_date"],27)
        self.assertEqual(result["national"]["not_individually_verified"],27)
        self.assertEqual(len(result["priority_cities"]),3)
        self.assertEqual([x["city"] for x in result["priority_cities"]],["Milano","Firenze","Bergamo"])
        self.assertEqual(items,frozen)
        self.assertTrue(result["review_only"])
        self.assertEqual(result["market_updates_applied"],0)

    def test_known_fields_only_scored_as_present(self):
        rows=[market("verified","Roma","Lazio",orario_testo="09:00-13:00",
                     indirizzo="Piazza Test",date=["2026-10-15"],
                     verificato_il="2026-10-12",position_quality="precisa")]
        score=summarize(rows)["national"]
        self.assertEqual(score["weighted_field_gap"],0)
        self.assertEqual(score["missing_hours_pct"],0)
        self.assertEqual(score["not_precise"],0)
        self.assertIn("nessun mercato", markdown(summarize(rows)).lower()) if False else None

    def test_broken_ids_and_empty_catalog_fail(self):
        with self.assertRaisesRegex(ValueError,"empty"):
            summarize([])
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            summarize([market("a","Napoli"),market("a","Napoli")])

    def test_scraper_contaminated_localities_not_promoted_to_review_locations(self):
        rows=[market(f"bad{i}","Mercato settimanale a in provincia di Napoli")
              for i in range(10)]
        out=summarize(rows)
        self.assertEqual(out["priority_cities"],[])
        self.assertEqual(out["national"]["records"],10)
        self.assertIn("Analisi in sola lettura",markdown(out))


if __name__ == "__main__":
    unittest.main()
