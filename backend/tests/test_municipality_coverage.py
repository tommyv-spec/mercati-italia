import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from municipality_coverage import compare, normalize_name, markdown


ISTAT=json.loads((Path(__file__).resolve().parents[1]/"data"/"istat-comuni-2026.json").read_text("utf-8"))


def market(sid,city,region):
    return {"slug":sid,"citta":city,"regione":region}


class MunicipalityCoverageTests(unittest.TestCase):
    def test_real_7894_istat_municipalities_and_read_only_coverage(self):
        rows=[market("a","Roma","Lazio"),market("b","Milano","Lombardia"),
              market("c","Milano","Lombardia"),market("d","Firenze","Toscana")]
        old=copy.deepcopy(rows)
        out=compare(rows,ISTAT)
        self.assertEqual(out["municipalities_total"],7894)
        self.assertEqual(out["municipalities_with_catalog_listings"],3)
        self.assertEqual(out["municipalities_without_catalog_listings"],7891)
        self.assertEqual(out["catalog_market_ids_preserved"],4)
        self.assertEqual(out["catalog_entries_added"],0)
        self.assertEqual(rows,old)
        self.assertIn("non implica",markdown(out))
        self.assertEqual(sum(r["without_catalog_market"] for r in out["regions"]),7891)

    def test_accent_case_and_apostrophe_preserve_canonical_match(self):
        # No fuzzy guess. Only accents, case and punctuation can be neutralized.
        self.assertEqual(normalize_name("L'Aquila"),normalize_name("L’AQUILA"))
        self.assertEqual(normalize_name("Città di Castello"),normalize_name("citta di castello"))
        rows=[market("abruzzo","L’AQUILA","Abruzzo"),
              market("umbria","citta di castello","Umbria")]
        self.assertEqual(compare(rows,ISTAT)["municipalities_with_catalog_listings"],2)

    def test_scraper_city_and_missing_region_not_automatically_inferred(self):
        out=compare([market("bad","Mercato settimanale a in provincia di Milano","Lombardia")],ISTAT)
        self.assertEqual(out["municipalities_with_catalog_listings"],0)
        with self.assertRaisesRegex(ValueError,"region/city"):
            compare([market("bad","Milano","Fake Region")],ISTAT)

    def test_duplicate_ids_and_unverified_reference_fail(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            compare([market("id","Roma","Lazio"),market("id","Milano","Lombardia")],ISTAT)
        wrong=copy.deepcopy(ISTAT)
        wrong["source_file_sha256"]="f"*64
        with self.assertRaisesRegex(ValueError,"ISTAT reference"):
            compare([market("a","Roma","Lazio")],wrong)


if __name__=="__main__":
    unittest.main()
