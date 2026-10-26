"""Release check for the weekly Happings catalog update."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from happings_bulk_catalog_publish import expected_marker


class ExpectedMarkerTests(unittest.TestCase):
    def test_reported_marker_wins_even_when_the_exporter_already_derives_it(self):
        self.assertEqual(expected_marker("copy", {"duplicato_di": "kept"}, {"copy": "kept"}), "kept")

    def test_unreported_record_keeps_the_baseline_marker(self):
        self.assertEqual(expected_marker("copy", {"duplicato_di": "kept"}, {}), "kept")
        self.assertEqual(expected_marker("solo", {}, {}), "")

    def test_a_swapped_pair_leaves_the_new_visible_card_without_marker(self):
        # Baseline: ees -> happ. The enrichment reports happ -> ees.
        self.assertEqual(expected_marker("ees", {"duplicato_di": "happ"}, {"happ": "ees"}), "")
        self.assertEqual(expected_marker("happ", {}, {"happ": "ees"}), "ees")


if __name__ == "__main__":
    unittest.main()
