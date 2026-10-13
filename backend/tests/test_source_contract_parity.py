import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_corciano import convert,parse_csv
from source_contract_parity import compare,verify
from test_source_corciano import DATA

TODAY=date(2026,10,13)
BLOB=DATA.encode("utf-8")
PROFILE=json.loads(
  (Path(__file__).resolve().parents[1]/"data/market-source-contracts.json").read_text("utf-8")
)["raw_profiles"][0]


class SourceContractParityTests(unittest.TestCase):
    def test_true_original_four_row_corciano_source_reproduces_every_safe_fact(self):
        reference=convert(parse_csv(BLOB),TODAY)
        frozen=copy.deepcopy(reference)
        qa=compare(PROFILE,BLOB,reference,today=TODAY)
        self.assertTrue(verify(qa,expect_identities=4))
        self.assertTrue(qa["parity_complete"])
        self.assertEqual(qa["identical_identity_ids"],4)
        self.assertEqual(qa["legacy_only_market_ids_count"],0)
        self.assertEqual(qa["generic_only_market_ids_count"],0)
        self.assertEqual(qa["changed_fields"],{})
        self.assertEqual(qa["new_market_identities_published"],0)
        self.assertEqual(qa["old_market_identities_deleted"],0)
        self.assertEqual(reference,frozen)
        self.assertNotIn("MERCATO DI MANTIGNANA",json.dumps(qa))

    def test_unexpected_changed_legacy_hours_prevent_generic_source_promotion(self):
        legacy=convert(parse_csv(BLOB),TODAY)
        legacy[0]["orario_testo"]="09:30–10:00 (da verificare con il Comune)"
        report=compare(PROFILE,BLOB,legacy,today=TODAY)
        self.assertFalse(report["parity_complete"])
        self.assertEqual(report["changed_fields"]["orario_testo"],1)
        self.assertEqual(report["changed_source_identity_count"],1)
        with self.assertRaisesRegex(ValueError,"does not reproduce"):
            verify(report,expect_identities=4)

    def test_missing_original_source_identity_not_mistaken_for_market_closed(self):
        legacy=convert(parse_csv(BLOB),TODAY)
        report=compare(PROFILE,BLOB,legacy[:-1],today=TODAY)
        self.assertFalse(report["parity_complete"])
        self.assertEqual(report["generic_only_market_ids_count"],1)
        self.assertEqual(report["old_market_identities_deleted"],0)
        self.assertFalse(report["parity_complete"])

    def test_contract_changing_market_address_halts_parity(self):
        profile=copy.deepcopy(PROFILE)
        profile["presentation"].pop("address_suffix_name_prefix")
        legacy=convert(parse_csv(BLOB),TODAY)
        result=compare(profile,BLOB,legacy,today=TODAY)
        self.assertEqual(result["changed_fields"]["indirizzo"],4)
        self.assertFalse(result["parity_complete"])

    def test_no_original_market_confirmation_can_be_accepted_as_parity(self):
        legacy=convert(parse_csv(BLOB),TODAY)
        legacy[0]["date_quality"]="confermata"
        with self.assertRaisesRegex(ValueError,"Legacy source falsely"):
            compare(PROFILE,BLOB,legacy,today=TODAY)


if __name__=="__main__":
    unittest.main()
