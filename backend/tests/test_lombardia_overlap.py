import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lombardia_overlap import review, weekday_evidence


def market(slug, city="Pogliano Milanese", address="VIA EUROPA",
           daytext="", dates=None):
    return {
        "slug": slug, "citta": city, "regione": "Lombardia",
        "indirizzo": address,
        "ricorrenza_testo": daytext,
        "date": dates or [],
    }


class OverlapSafetyTests(unittest.TestCase):
    def test_bologna_uses_same_conservative_replayable_overlap_rules(self):
        old = market("legacy-bo-sabato", city="Bologna", address="piazza VIII Agosto",
                     daytext="Ogni sabato")
        old["regione"] = "Emilia-Romagna"
        incoming = market("bo-open-fcc9f1", city="Bologna", address="piazza VIII Agosto",
                          daytext="settimanale - sabato")
        incoming["regione"] = "Emilia-Romagna"
        kept, result = review([old], [incoming], region="Emilia-Romagna",
                              source_prefix="bo-open-", max_conflicts=30)
        self.assertEqual(kept, [])
        self.assertEqual(result["quarantined"], 1)
        self.assertEqual(result["region"], "Emilia-Romagna")
        incoming["indirizzo"] = "via Bentini"
        kept, result = review([old], [incoming], region="Emilia-Romagna",
                              source_prefix="bo-open-", max_conflicts=30)
        self.assertEqual(kept, [incoming])
        self.assertEqual(result["quarantined"], 0)

    def test_same_location_same_weekday_quarantines_new_identity(self):
        old = market("mercato-settimanale-di-pogliano-milanese-venerdi")
        new = market("lo-mercap-100551-venerdi")
        accepted, report = review([old], [new])
        self.assertEqual(accepted, [])
        self.assertEqual(report["quarantined"], 1)
        self.assertEqual(report["quarantined_examples"][0]["existing_market_ids"], [old["slug"]])

    def test_same_location_different_weekday_remains_distinct(self):
        old = market("mercato-settimanale-di-pogliano-milanese-lunedi")
        new = market("lo-mercap-100551-venerdi")
        selected, report = review([old], [new])
        self.assertEqual(selected, [new])
        self.assertEqual(report["quarantined"], 0)
        self.assertEqual(report["counts"]["same_place_distinct_documented_day"], 1)

    def test_unknown_weekday_quarantines_both_directions(self):
        old = market("mercato-settimanale-di-pogliano-milanese")
        known = market("lo-mercap-100551-venerdi")
        unknown = market("lo-mercap-100551-senza-giorno")
        result, report = review([old], [known,unknown])
        self.assertEqual(len(result), 0)
        self.assertEqual(report["quarantined"], 2)

    def test_unchanged_lombardia_identity_always_admitted(self):
        original = market("lo-mercap-100551-venerdi")
        proposed = {**original, "aggiornato_il": "2026-10-06"}
        kept, report = review([original], [proposed])
        self.assertEqual(kept, [proposed])
        self.assertEqual(report["quarantined"], 0)

    def test_different_streets_keep_separate_records(self):
        old = market("old-market")
        new = market("lo-mercap-100551-venerdi", address="VIA MARTIRI")
        kept, stats = review([old], [new])
        self.assertEqual(kept, [new])
        self.assertEqual(stats["quarantined"], 0)

    def test_strong_weekday_rule_is_usable_evidence(self):
        old = market("old", daytext="Ogni martedì")
        self.assertEqual(weekday_evidence(old), {1})
        self.assertIsNone(weekday_evidence(market("old", dates=["2026-10-13"])))
        self.assertEqual(weekday_evidence(
            market("old", dates=["2026-10-13", "2026-10-20"])), {1})

    def test_never_modifies_source_or_existing_record(self):
        old = market("old")
        new = market("lo-mercap-100551-venerdi")
        oldcopy=old.copy()
        newcopy=new.copy()
        review([old], [new])
        self.assertEqual(old,oldcopy)
        self.assertEqual(new,newcopy)


if __name__=="__main__":
    unittest.main()
