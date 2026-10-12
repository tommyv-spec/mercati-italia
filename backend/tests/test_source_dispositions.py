import unittest
import sys
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_dispositions import reconcile

SRC={"lo-mercap-101-lunedi","lo-mercap-102-martedi",
     "lo-mercap-103-mercoledi","lo-mercap-104-giovedi"}
CAT={"lo-mercap-101-lunedi","lo-mercap-102-martedi"}


class SourceDispositionTests(unittest.TestCase):
    def test_exact_approved_partition_is_aggregated_without_leaking_raw_ids(self):
        result=reconcile(SRC,CAT,{"lo-mercap-103-mercoledi"},
                         reviewed_excluded_count=1,reviewed_accepted_count=3)
        self.assertEqual(result["outside_catalog_source_ids_not_necessarily_new_markets"],2)
        self.assertEqual(result["already_quarantined_by_venue_overlap_review"],1)
        self.assertEqual(result["remaining_identities_without_overlap_disposition"],1)
        self.assertTrue(result["exact_reviewed_id_partition_verified"])
        self.assertEqual(len(result["quarantine_source_id_set_sha256"]),64)
        self.assertNotIn("lo-mercap",str(result))

    def test_count_only_cannot_masquerade_as_source_specific_disposition(self):
        a=reconcile(SRC,CAT,reviewed_excluded_count=2)
        self.assertEqual(a["already_quarantined_by_venue_overlap_review"],0)
        self.assertEqual(a["remaining_identities_without_overlap_disposition"],2)
        self.assertTrue(a["screening_missing_exact_source_id_proof"])

    def test_different_ids_with_same_numeric_quarantine_are_not_hidden(self):
        with self.assertRaisesRegex(ValueError,"Already published"):
            reconcile(SRC,CAT,{"lo-mercap-101-lunedi","lo-mercap-103-mercoledi"},
                      reviewed_excluded_count=2,reviewed_accepted_count=2)
        with self.assertRaisesRegex(ValueError,"does not belong"):
            reconcile(SRC,CAT,{"lo-mercap-103-mercoledi","lo-mercap-999-venerdi"},
                      reviewed_excluded_count=2,reviewed_accepted_count=2)

    def test_source_and_accepted_counts_must_reconcile_completely(self):
        with self.assertRaisesRegex(ValueError,"Count of exact"):
            reconcile(SRC,CAT,{"lo-mercap-103-mercoledi"},
                      reviewed_excluded_count=2,reviewed_accepted_count=2)
        with self.assertRaisesRegex(ValueError,"Accepted source"):
            reconcile(SRC,CAT,{"lo-mercap-103-mercoledi"},
                      reviewed_excluded_count=1,reviewed_accepted_count=2)
        with self.assertRaisesRegex(ValueError,"Duplicate source"):
            reconcile(list(SRC)+[next(iter(SRC))],CAT)

    def test_new_source_rows_are_not_verified_openings_or_closed_when_missing(self):
        first=reconcile(SRC,CAT,{"lo-mercap-103-mercoledi"},
                        reviewed_excluded_count=1,reviewed_accepted_count=3)
        self.assertEqual(first["remaining_identities_without_overlap_disposition"],1)
        next_source=SRC-{"lo-mercap-104-giovedi"}
        rerun=reconcile(next_source,CAT,{"lo-mercap-103-mercoledi"},
                        reviewed_excluded_count=1,reviewed_accepted_count=2)
        self.assertEqual(rerun["remaining_identities_without_overlap_disposition"],0)
        self.assertNotIn("verified",str(rerun).lower())
        self.assertNotIn("closed",str(rerun).lower())


if __name__=="__main__":
    unittest.main()
