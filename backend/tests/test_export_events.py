import os
import sys
import unittest
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from datetime import date  # noqa: E402
from export_static import EVENTS_FIELDS, date_hours, events_rows, is_weekly_market, short_description  # noqa: E402

TODAY = date(2026, 11, 3)


class EventsFileTests(unittest.TestCase):
    def test_weekly_by_rule_or_tag(self):
        self.assertTrue(is_weekly_market({"proiezione_regola": {"kind": "weekly", "weekdays": [2]}}))
        self.assertTrue(is_weekly_market({"tags": ["mercato comunale"]}))
        self.assertTrue(is_weekly_market({"tags": ["MERCAP"]}))
        self.assertFalse(is_weekly_market({"proiezione_regola": {"kind": "monthly_nth_weekday"}, "tags": ["antiquariato"]}))
        self.assertFalse(is_weekly_market({"categoria": "misto"}))

    def test_weekday_only_recurrence_is_weekly(self):
        # Farmers' markets list their weekdays and hours: weekly in all but name.
        self.assertTrue(is_weekly_market({"ricorrenza_testo": "venerdì 15:30–20:00; sabato 08:30–13:00."}))
        self.assertTrue(is_weekly_market({"ricorrenza_testo": "martedì 08:00–20:00; giovedì 08:00–20:00; sabato 08:00–14:00."}))
        self.assertTrue(is_weekly_market({"ricorrenza_testo": "Ogni martedì mattina"}))
        self.assertTrue(is_weekly_market({"ricorrenza_testo": "tutti i sabati"}))
        self.assertFalse(is_weekly_market({"ricorrenza_testo": "Ogni prima domenica del mese"}))
        self.assertFalse(is_weekly_market({"ricorrenza_testo": "sabato 31 ottobre e domenica 1 novembre"}))
        self.assertFalse(is_weekly_market({"ricorrenza_testo": ""}))
        # No recurrence sentence, but the hours field spells out a weekly timetable.
        self.assertTrue(is_weekly_market({"ricorrenza_testo": "", "orario_testo": "lunedì 08:00–12:00; lunedì 15:00–18:00; martedì 08:00–12:00."}))
        self.assertFalse(is_weekly_market({"ricorrenza_testo": "", "orario_testo": "09:00–19:00"}))

    def test_short_description_cuts_on_sentence_then_word(self):
        self.assertEqual(short_description("Breve."), "Breve.")
        long_text = "Prima frase lunga. " * 10 + "Seconda frase che non entra."
        cut = short_description(long_text, limit=60)
        self.assertTrue(cut.endswith("…"))
        self.assertLessEqual(len(cut), 61)
        self.assertEqual(short_description("a" * 300, limit=240), "a" * 240 + "…")
        self.assertEqual(short_description(None), "")

    def test_events_rows_skip_weekly_concluded_and_merged(self):
        markets = [
            {"slug": "fiera", "indirizzo": "Piazza Grande", "ricorrenza_testo": "primo weekend",
             "descrizione": "Testo.", "ingresso": "Ingresso gratuito", "consigli": "Arriva presto",
             "tags": ["antiquariato"], "proiezione_regola": None},
            {"slug": "weekly", "tags": ["settimanale"]},
            {"slug": "gone", "concluso": "fonte_non_riletta"},
            {"slug": "copy", "duplicato_di": "fiera"},
        ]
        rows = events_rows(markets, today=TODAY)
        self.assertEqual(rows, [["fiera", "Piazza Grande", "primo weekend", "Testo.", "Ingresso gratuito", "Arriva presto", {}]])
        self.assertEqual(EVENTS_FIELDS, ("slug", "indirizzo", "ricorrenza_testo", "descrizione", "ingresso", "consigli", "orari_date"))

    def test_date_hours_only_where_the_source_gives_one_exact_range(self):
        def occ(day, start="08:00", end="18:00", status="source_listed", **more):
            return {"date": day, "start_time": start, "end_time": end, "status": status, **more}
        market = {"date": ["2026-11-07", "2026-11-08", "2026-11-14", "2026-11-15", "2026-11-21", "2026-11-22", "2026-11-28"],
                  "eccezioni_calendario": [{"data": "2026-11-14", "motivo": "maltempo"}],
                  "calendario_fonte": {"occorrenze": [
                      occ("2026-11-07"),
                      occ("2026-11-08", end=None),                                     # closing time unknown
                      occ("2026-11-14"),                                               # cancelled by an exception
                      occ("2026-11-15", status="postponed"),
                      occ("2026-11-21", interval_start="2026-11-21", interval_end="2026-11-22"),  # period, not a day
                      occ("2026-11-28"), occ("2026-11-28", start="15:00", end="19:00"),  # two different times
                  ]}}
        self.assertEqual(date_hours(market, today=TODAY), {"2026-11-07": "08:00–18:00"})
        # Without a source calendar or bound editorial evidence the list keeps the general hours.
        self.assertEqual(date_hours({"date": ["2026-11-07"], "orario_testo": "08:00–18:00"}, today=TODAY), {})
        self.assertEqual(date_hours({"date": ["2026-11-07"], "evidenza_editoriale": {"forged": True}}, today=TODAY), {})



class EventsFileLifecycleTests(unittest.TestCase):
    """The events asset must survive every step that copies or prunes catalog files."""

    def setUp(self):
        import tempfile
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def catalog(self, folder, **changes):
        from export_static import export
        from test_eventiesagre_detail_refresh import TODAY, row
        return export([row(**changes)], folder / "public/data/v1", today=TODAY)["manifest"]

    def test_validator_requires_a_matching_events_file(self):
        from export_static import _write_asset, compact_json
        from validate_static import validate
        out = self.root / "public/data/v1"
        manifest = self.catalog(self.root)
        self.assertEqual(validate(out / "manifest.json")["records"], 1)
        events = self.root / "public" / manifest["events"]
        events.unlink()
        with self.assertRaisesRegex(ValueError, "Missing events file"):
            validate(out / "manifest.json")
        manifest["events"] = _write_asset(out, "eventi-{hash}.json", [["forged", "", "", "", "", ""]])
        (out / "manifest.json").write_bytes(compact_json(manifest))
        with self.assertRaisesRegex(ValueError, "Events file differs"):
            validate(out / "manifest.json")

    def test_nightly_pruning_keeps_the_events_file(self):
        from autopilot import prune_old_assets
        out = self.root / "public/data/v1"
        manifest = self.catalog(self.root)
        (out / "eventi-00000000000000.json").write_text("{}")
        prune_old_assets(out, {}, manifest)
        self.assertTrue((self.root / "public" / manifest["events"]).is_file())
        self.assertFalse((out / "eventi-00000000000000.json").exists())

    def test_happings_bulk_install_copies_the_events_file(self):
        from happings_bulk_catalog_publish import install
        from validate_static import validate
        repo, built = self.root / "repo", self.root / "built"
        old = self.catalog(repo)
        new = self.catalog(built, nome="Mercatino rinominato")
        install(repo, built)
        target = repo / "public/data/v1"
        self.assertTrue((repo / "public" / new["events"]).is_file())
        self.assertEqual(validate(target / "manifest.json")["records"], 1)
        self.assertTrue(old["events"] == new["events"] or (repo / "public" / old["events"]).is_file())


if __name__ == "__main__":
    unittest.main()
