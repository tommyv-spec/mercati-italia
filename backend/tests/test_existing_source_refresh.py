"""Integration boundaries for concurrent readers, queues and Roma evidence.

EES uses synthetic observed-layout HTML; CDC uses labelled parser fixtures.
Roma uses the original captured metadata and losslessly compressed CSV. No
test makes a network request or treats a read timestamp as source freshness.
"""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import existing_source_refresh as integration
import eventiesagre_detail_refresh as editorial
from export_static import normalize
from field_evidence import field_states
from test_eventiesagre_detail_refresh import (
    TODAY, URL, CDC, CDC_FIXTURES, CDC_SAMPLES, cdc_row,
    document, html, row,
)
from test_roma_d881_enrichment import row as roma_row
from test_source_roma_d881 import METADATA, CSV, READ_METADATA, READ_CSV


class ExistingSourceIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.config = integration.configuration()

    def args(self, **changes):
        result = dict(out=self.root / "run", state_dir=self.root / "previous",
                      today=TODAY, baseline_signature="catalog-baseline",
                      policy_digest="complete-pipeline-policy", config=self.config)
        result.update(changes)
        return result

    def captured_editorial_run(self, rows, *, barrier=None, **changes):
        calls = []
        lock = threading.Lock()
        sample = CDC_SAMPLES["bologna"]
        bodies = {URL: html(), sample["requested_url"]:
                  (CDC_FIXTURES / sample["fixture_file"]).read_bytes()}

        def fetch(url, **kwargs):
            with lock:
                calls.append(url)
            if url.endswith("/robots.txt"):
                if barrier:
                    barrier.wait(timeout=5)
                return b"User-agent: *\nDisallow:\n", url
            return bodies[url], url

        original = editorial.run

        def bounded_reader(*args, **kwargs):
            kwargs.update(sleep=lambda _: None,
                          now=lambda: datetime(2026, 10, 20, 12, tzinfo=timezone.utc))
            return original(*args, **kwargs)

        args = self.args(fetchers={"eventiesagre.it": fetch, CDC: fetch}, **changes)
        with patch.object(editorial, "run", side_effect=bounded_reader):
            result = integration.run_editorial(rows, **args)
        return result, calls

    def test_independent_hosts_read_concurrently_and_merge_source_proved_changes(self):
        before = [row(), cdc_row("bologna")]
        untouched = deepcopy(before)
        (after, report, protected), calls = self.captured_editorial_run(
            before, barrier=threading.Barrier(2))
        self.assertEqual(before, untouched)
        self.assertEqual([r["slug"] for r in after], [r["slug"] for r in before])
        self.assertEqual(set(report["changed_existing_ids"]), {r["slug"] for r in before})
        self.assertEqual(protected, {r["slug"] for r in before})
        self.assertEqual(after[0]["orario_testo"], "08:00–13:00")
        self.assertEqual(after[1]["orario_testo"], "08:30–18:00")
        self.assertEqual(len(calls), 4)
        normalized = [normalize(r, TODAY)[0] for r in after]
        self.assertTrue(integration.verify_editorial_export(normalized, report, today=TODAY)["release_safe"])
        for publisher, phase in report["editorial"].items():
            expected = 0 if publisher == "citynews" else 1
            read_key = "read_in_cycle" if publisher == "citynews" else "cycle_read"
            self.assertEqual(phase["source_pages_read"], expected, publisher)
            self.assertEqual(phase["progress"][read_key], expected, publisher)

    def test_even_individually_valid_readers_cannot_both_change_one_identity(self):
        before = [row()]
        revised, proof = editorial.preview(before, [document()], today=TODAY)
        # A faulty adapter returning the other publisher's valid proof must
        # still be rejected when the two proven changes overlap.
        def duplicate_reader(*args, **kwargs):
            return deepcopy(revised), {"evidence": deepcopy(proof)}, {before[0]["slug"]}
        with patch.object(editorial, "run", side_effect=duplicate_reader):
            with self.assertRaisesRegex(ValueError, "same identity"):
                integration.run_editorial(before, **self.args())

    def test_reader_deadlines_share_wall_clock_but_keep_separate_host_limits(self):
        deadlines = {}
        original = editorial.run
        def observe(*args, **kwargs):
            deadlines[kwargs["publisher"]] = kwargs["deadline"]
            return original(*args, **kwargs)
        with patch.object(editorial, "run", side_effect=observe):
            integration.run_editorial([row(), cdc_row("bologna")],
                **self.args(offline=True, monotonic=lambda: 100.0, deadline=500.0))
        self.assertEqual(deadlines, {"eventiesagre.it": 500.0, CDC: 400.0})

    def test_global_disabled_configuration_never_reads_eligible_sources(self):
        config = integration.configuration(enabled=False)
        before = [row(), cdc_row("bologna"), roma_row()]
        with patch.object(editorial, "_http", side_effect=AssertionError("disabled editorial read")), \
                patch.object(integration.roma_source, "fetch_public", side_effect=AssertionError("disabled Roma read")):
            after, editorial_report, _ = integration.run_editorial(before,
                **self.args(config=config, offline=False))
            final, roma_report = integration.run_roma(after,
                **self.roma_args(config=config, offline=False))
        self.assertEqual(final, before)
        self.assertTrue(all(p["status"] == "disabled" and p["network_requests"] == 0
                            for p in editorial_report["editorial"].values()))
        self.assertEqual(roma_report["status"], "disabled")
        self.assertEqual(roma_report["network_requests"], 0)

    def test_successful_queues_survive_candidate_pruning_and_offline_refresh(self):
        before = [row(), cdc_row("bologna")]
        (_, report, _), _ = self.captured_editorial_run(before)
        candidate = self.root / "candidate/public/data/v1"
        changed = integration.persist_editorial_states(report, out=self.root / "run",
            source_dir=self.root / "previous", destination=candidate, today=TODAY)
        self.assertTrue(changed)
        saved = {name: (candidate / name).read_bytes() for name in integration.STATE_FILENAMES}
        from autopilot import prune_old_assets
        (candidate / "obsolete-region.json").write_text("{}")
        self.assertEqual(prune_old_assets(candidate, {}, {}), 1)
        self.assertEqual(saved, {name: (candidate / name).read_bytes() for name in saved})
        with patch.object(editorial, "_http", side_effect=AssertionError("offline network read")):
            after, offline, _ = integration.run_editorial(before,
                **self.args(out=self.root / "offline", state_dir=candidate, offline=True))
        self.assertEqual(after, before)
        for phase in offline["editorial"].values():
            self.assertEqual(phase["status"], "offline_skipped")
            self.assertEqual(phase["network_requests"], 0)
        self.assertFalse(integration.persist_editorial_states(offline,
            out=self.root / "offline", source_dir=candidate, destination=candidate, today=TODAY))
        self.assertEqual(saved, {name: (candidate / name).read_bytes() for name in saved})

    def test_state_report_binding_rejects_a_different_valid_queue(self):
        rows = [row(), cdc_row("bologna")]
        (_, report, _), _ = self.captured_editorial_run(rows)
        publisher = "eventiesagre.it"
        empty_history = editorial.seed_state(rows, today=TODAY, publisher=publisher)
        (self.root / "run" / integration.EDITORIAL_STATES[publisher]).write_text(json.dumps(empty_history))
        with self.assertRaisesRegex(ValueError, "differs from its source report"):
            integration.persist_editorial_states(report, out=self.root / "run",
                source_dir=self.root / "previous", destination=self.root / "candidate", today=TODAY)

    def test_source_bound_past_year_identity_survives_export_and_next_offline_day(self):
        from editorial_calendar_scope import KEY
        from export_static import export
        from merge_catalog import load_existing
        from recurrence_refresh import refresh_record
        before = row(nome="Mercato Di Bologna 2018")
        archived = document(html(start="01/01/2018", end="31/12/2018", archived=True).replace(
            b"Mercato Di Bologna", b"Mercato Di Bologna 2018"))
        rows, evidence = editorial.preview([before], [archived], today=TODAY)
        self.assertEqual(rows[0][KEY]["facts"]["edition_intervals"][0]["end"], "2018-12-31")
        self.assertEqual(rows[0]["date"], [])
        self.assertEqual(rows[0]["orario_testo"], "")
        output = self.root / "historical/public/data/v1"
        export(rows, output, today=TODAY, min_count=1, preserve_ids={before["slug"]})
        loaded = load_existing(output / "manifest.json")
        self.assertEqual([r["slug"] for r in loaded], [before["slug"]])
        self.assertTrue(editorial.verify_exported(loaded, evidence, today=TODAY)["release_safe"])
        next_day = TODAY + timedelta(days=1)
        refreshed, _ = refresh_record(loaded[0], next_day)
        normalized, error = normalize(refreshed, next_day)
        self.assertIsNone(error)
        self.assertEqual(normalized["slug"], before["slug"])
        self.assertEqual(normalized["date"], [])
        self.assertEqual(normalized[KEY]["read_on"], TODAY.isoformat())

    def roma_args(self, **changes):
        args = self.args(**changes)
        args.pop("state_dir")
        return args

    def test_roma_capture_resume_preserves_old_row_dates_through_final_export(self):
        before = [roma_row(fonte_aggiornata_il="2021-12-31", fonte_letta_il="2026-06-05")]
        calls = []
        def fetch(url):
            calls.append(url)
            return METADATA if len(calls) == 1 else CSV
        stamps = iter(map(datetime.fromisoformat, (READ_METADATA, READ_CSV)))
        after, report = integration.run_roma(before, **self.roma_args(
            fetcher=fetch, clock=lambda: next(stamps)))
        self.assertEqual(report["network_requests"], 2)
        self.assertEqual(report["status"], "retrieved")
        self.assertEqual(after[0]["fonte_aggiornata_il"], "2021-12-31")
        self.assertEqual(after[0]["fonte_letta_il"], "2026-06-05")
        self.assertEqual(field_states(after[0], today=TODAY)["orario_testo"], "riscontro_da_aggiornare")
        self.assertTrue(report["phase_proof"]["normalized_cohort"]["valid"])
        with patch.object(integration.roma_source, "fetch_public", side_effect=AssertionError("resume network read")):
            resumed, checkpoint = integration.run_roma(before, **self.roma_args(resume=True))
        self.assertEqual(resumed, after)
        self.assertEqual(checkpoint["status"], "resumed_checkpoint")
        self.assertEqual(checkpoint["network_requests"], 0)
        normalized = [normalize(after[0], TODAY)[0]]
        self.assertTrue(integration.verify_roma_fields(normalized, report, today=TODAY)["release_safe"])
        normalized[0]["orario_testo"] = "08:00–20:00"
        with self.assertRaisesRegex(ValueError, "hour changed"):
            integration.verify_roma_fields(normalized, report, today=TODAY)

    def test_roma_resume_rejects_catalog_or_policy_context_replacement(self):
        stamps = iter(map(datetime.fromisoformat, (READ_METADATA, READ_CSV)))
        integration.run_roma([roma_row()], **self.roma_args(
            fetcher=lambda url: METADATA if url == integration.roma_source.METADATA_URL else CSV,
            clock=lambda: next(stamps)))
        for changes in ({"baseline_signature": "different"}, {"policy_digest": "different"}):
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, "another source policy"):
                integration.run_roma([roma_row()], **self.roma_args(resume=True, **changes))
        with self.assertRaisesRegex(ValueError, "another source policy"):
            integration.run_roma([roma_row(indirizzo="Via diversa")], **self.roma_args(resume=True))

    def test_roma_unavailable_source_never_refreshes_any_existing_field(self):
        before = [roma_row(fonte_aggiornata_il="2021-12-31")]
        def fail(url):
            raise OSError("fixture transport unavailable")
        after, report = integration.run_roma(before, **self.roma_args(fetcher=fail))
        self.assertEqual(after, before)
        self.assertEqual(report["status"], "source_unavailable")
        self.assertEqual(report["network_requests"], 1)
        self.assertIsNone(report["phase_proof"])
        self.assertFalse((self.root / "run/sources/roma-d881-snapshot.json").exists())


if __name__ == "__main__":
    unittest.main()
