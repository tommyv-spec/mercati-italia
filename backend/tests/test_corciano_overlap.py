import copy
import unittest
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from corciano_overlap import review
from source_corciano import parse_csv,convert
from test_source_corciano import DATA

NOW = __import__("datetime").date(2026,10,12)


def old(slug,name,day,street=""):
    return {
        "slug":slug,"nome":name,"citta":"Corciano","regione":"Umbria",
        "indirizzo":street,"ricorrenza_testo":"settimanale - "+day,
        "date":[],"url_fonte":"https://example.org/old",
    }


class CorcianoOverlapTests(unittest.TestCase):
    def source(self):
        return convert(parse_csv(DATA.encode("utf-8")), NOW)

    def legacy(self):
        return [
            old("mercato-settimanale-di-corciano-corciano",
                "Mercato Settimanale Di Corciano","mercoledì","Via Dei Caduti"),
            old("mercato-settimanale-di-corciano-corciano-mercoledi",
                "Mercato Settimanale Di Corciano","mercoledì","Via Dei Caduti"),
            old("mercato-settimanale-a-corciano-corciano-venerdi",
                "Mercato settimanale a Corciano","venerdì",""),
        ]

    def test_exact_manually_verified_baseline_approves_two_quarantines_two(self):
        data=self.source()
        accepted,report=review(self.legacy(), data)
        self.assertEqual(report["source_total"],4)
        self.assertEqual(report["accepted"],2)
        self.assertEqual(report["quarantined"],2)
        self.assertEqual({v["nome"] for v in accepted},
                         {"Mercato Di Mantignana","Mercato Di San Mariano"})
        reasons={c["reason"] for c in report["quarantined_examples"]}
        self.assertEqual(reasons,{
            "same_market_name_and_weekday",
            "generic_city_day_without_venue",
        })
        self.assertTrue(report["source_csv_sha256"])
        self.assertEqual(report["market_confirmations"],0)

    def test_replay_is_idempotent_when_official_source_ids_exist(self):
        existing=self.legacy()+self.source()
        accepted,report=review(existing,self.source())
        self.assertEqual(report["accepted"],4)
        self.assertEqual(report["quarantined"],0)
        self.assertEqual(report["counts"]["existing_official_source_id"],4)

    def test_different_day_same_city_not_duplicate(self):
        official=self.source()
        other=[old("legacy-wednesday","Mercato di Mantignana","mercoledì","Piazza Giovanni Ercolani")]
        approved,report=review(other,official)
        self.assertEqual(report["accepted"],4)
        self.assertEqual(report["quarantined"],0)

    def test_unrelated_city_not_duplicated(self):
        official=self.source()
        other=[old("legacy-roma","Mercato di Corciano","mercoledì","Piazza Caduti")]
        other[0]["citta"]="Perugia"
        approved,report=review(other,official)
        self.assertEqual(len(approved),4)

    def test_source_hash_mismatch_refused(self):
        source=self.source()
        source[1]["source_csv_sha256"]="a"*64
        with self.assertRaisesRegex(ValueError,"fingerprint varies"):
            review([],source)

    def test_not_mutated_and_same_input_same_output(self):
        current=self.legacy()
        incoming=self.source()
        frozen=copy.deepcopy((current,incoming))
        one=review(current,incoming)
        two=review(current,incoming)
        self.assertEqual(one,two)
        self.assertEqual((current,incoming),frozen)

    def test_rejects_unexpected_publisher_names(self):
        new=self.source()
        new[0]["regione"]="Lazio"
        with self.assertRaisesRegex(ValueError,"Unexpected official"):
            review([],new)


if __name__=="__main__":
    unittest.main()
