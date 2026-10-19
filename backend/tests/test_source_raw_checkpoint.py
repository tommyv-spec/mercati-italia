"""Whole-source uniqueness must survive restart without a second source read."""
import copy
import json
import sys
import tempfile
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from autopilot import retrieve_sources, save_json, source_feed, source_raw_checkpoint
from source_lombardia import convert
from test_source_lombardia import payload, row


TODAY = date(2026, 10, 19)
POLICY = {"sources": [{
    "id": "lombardia", "enabled": True, "official": True,
    "min_records": 1100, "max_records": 3000, "license": "CC0 1.0",
}]}


class CompleteSourceCheckpointTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # The malformed ID is excluded from import, but its venue can still
        # compete with a valid row. It must remain in the complete snapshot.
        cls.raw = payload([row(30000 + i) for i in range(1100)] + [
            row("invalid-id", indirizzi="VIA ALTERNATIVA")
        ], date_str="2026-10-13")

    def test_fetch_once_retains_excluded_rows_and_resume_keeps_original_read(self):
        download = Mock(return_value=copy.deepcopy(self.raw))
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            with patch.dict("autopilot.SOURCE_FUNCTIONS", {"lombardia": (download, convert)}):
                first, status = retrieve_sources(POLICY, out, TODAY, False, False)
            download.assert_called_once_with()
            self.assertEqual(len(first), 1100)
            raw_cache = out / "sources/lombardia-raw.json"
            retained = source_raw_checkpoint("lombardia", raw_cache, first)
            self.assertEqual(retained, self.raw)
            self.assertEqual(len(retained["rows"]), 1101)
            self.assertEqual(status["lombardia"]["complete_raw_checkpoint"]["status"], "bound_snapshot")
            before = raw_cache.read_bytes()
            with patch("autopilot.source_feed", side_effect=AssertionError("no second read")):
                resumed, status = retrieve_sources(POLICY, out, TODAY + timedelta(days=1), True, True)
            self.assertEqual(resumed, first)
            self.assertEqual(raw_cache.read_bytes(), before)
            self.assertEqual(status["lombardia"]["status"], "resumed_checkpoint")
            self.assertFalse(status["lombardia"]["complete_raw_checkpoint"]["new_read_on_resume"])

    def test_mixed_or_tampered_raw_and_normalized_checkpoints_fail_before_use(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            with patch.dict("autopilot.SOURCE_FUNCTIONS", {"lombardia": (lambda: self.raw, convert)}):
                first, _ = retrieve_sources(POLICY, out, TODAY, False, False)
            normalized_cache = out / "sources/lombardia.json"
            raw_cache = out / "sources/lombardia-raw.json"
            envelope = json.loads(raw_cache.read_text("utf-8"))
            for target in ("raw", "normalized", "source"):
                with self.subTest(target=target):
                    changed_raw = copy.deepcopy(envelope)
                    changed_normalized = copy.deepcopy(first)
                    if target == "raw":
                        changed_raw["payload"]["rows"][-1]["indirizzi"] = "VIA DIVERSA"
                    elif target == "normalized":
                        changed_normalized[0]["indirizzo"] = "VIA DIVERSA"
                    else:
                        changed_raw["source_id"] = "milano"
                    save_json(raw_cache, changed_raw)
                    save_json(normalized_cache, changed_normalized)
                    with self.assertRaisesRegex(ValueError, "checkpoint integrity mismatch"):
                        retrieve_sources(POLICY, out, TODAY, True, True)

    def test_legacy_normalized_checkpoint_does_not_invent_complete_raw_data(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            with patch.dict("autopilot.SOURCE_FUNCTIONS", {"lombardia": (lambda: self.raw, convert)}):
                first = source_feed("lombardia", TODAY)
            save_json(out / "sources/lombardia.json", first)
            with patch("autopilot.source_feed", side_effect=AssertionError("no implicit download")):
                resumed, status = retrieve_sources(POLICY, out, TODAY, True, True)
            self.assertEqual(resumed, first)
            self.assertEqual(status["lombardia"]["complete_raw_checkpoint"]["status"], "not_supplied")
            self.assertIsNone(source_raw_checkpoint("lombardia", out / "sources/lombardia-raw.json", resumed))

    def test_failed_new_download_cannot_reuse_an_older_complete_read(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td)
            with patch.dict("autopilot.SOURCE_FUNCTIONS", {"lombardia": (lambda: self.raw, convert)}):
                retrieve_sources(POLICY, out, TODAY, False, False)
            before = (out / "sources/lombardia-raw.json").read_bytes()
            with patch("autopilot.source_feed", side_effect=OSError("source unavailable")), patch("autopilot.time.sleep"):
                rows, status = retrieve_sources(POLICY, out, TODAY, False, False)
            self.assertEqual(rows, [])
            self.assertEqual(status["lombardia"]["status"], "unavailable")
            self.assertNotIn("complete_raw_checkpoint", status["lombardia"])
            self.assertEqual((out / "sources/lombardia-raw.json").read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
