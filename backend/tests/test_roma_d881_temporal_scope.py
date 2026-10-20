"""Hours receipts must never authorize an old, unrelated recurrence."""
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from recurrence_refresh import refresh_record
from roma_d881_enrichment import preview
from test_source_roma_d881 import TODAY, snapshot
from test_roma_d881_enrichment import row, future_snapshot


class RomaTemporalScopeTests(unittest.TestCase):
    def test_fresh_hours_receipt_cannot_renew_unproved_recurrence_in_forecaster(self):
        original = row(ricorrenza_testo="settimanale - domenica", date=["2026-10-25"],
                       date_quality="prevista", fonte_aggiornata_il="2021-12-31",
                       fonte_letta_il="2026-06-05")
        first, _ = preview([original], snapshot(), today=TODAY, apply=True)
        tomorrow = date(2026, 10, 21)
        fresh, _ = preview(first, future_snapshot(), today=tomorrow, apply=True)
        old_forecast, old_reason = refresh_record(original, tomorrow)
        fresh_forecast, fresh_reason = refresh_record(fresh[0], tomorrow)
        self.assertEqual(fresh_reason, old_reason)
        for field in ("date", "date_quality", "proiezione_regola", "proiezione_fonte"):
            self.assertEqual(fresh_forecast.get(field), old_forecast.get(field), field)


if __name__ == "__main__":
    unittest.main()
