import unittest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from freshness_alert import build


def report(**metrics):
    return {"schema": 1, "metrics": {"total": 10, **metrics},
            "publisher_evidence": [{"publisher": "Lombardia", "status": "metadata_checked"}]}


class AlertTests(unittest.TestCase):
    def test_stable_signature_for_identical_freshness_state(self):
        first = build(report(without_documented_verification=9))
        second = build(report(without_documented_verification=9))
        self.assertEqual(first["signature"], second["signature"])
        self.assertTrue(first["attention_required"])
        self.assertIn("Firma stato", first["body"])

    def test_improvements_change_signature(self):
        older = build(report(source_date_outside_limit=8))
        newer = build(report(source_date_outside_limit=4))
        self.assertNotEqual(older["signature"], newer["signature"])

    def test_clean_snapshot_can_close_issue(self):
        clean = build(report(without_documented_verification=0))
        self.assertFalse(clean["attention_required"])

    def test_official_publisher_failure_triggers_review(self):
        value = report()
        value["publisher_evidence"][0]["status"] = "needs_review"
        out = build(value)
        self.assertTrue(out["attention_required"])
        self.assertEqual(out["problems"]["publisher_unavailable"], ["Lombardia"])

    def test_bad_report_rejected(self):
        with self.assertRaises(ValueError):
            build({"schema": 2, "metrics": {}})


if __name__ == "__main__":
    unittest.main()
