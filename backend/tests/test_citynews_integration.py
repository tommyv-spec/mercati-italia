"""Citynews joins the existing candidate pipeline; no test uses HTTP."""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import existing_source_refresh as integration
import citynews_detail_refresh as citynews
import eventiesagre_detail_refresh as editorial
from export_static import normalize
from publisher_refresh import catalog_resources
from test_citynews_detail import TODAY, URL, html, row
from test_citynews_detail_refresh import rows as queue_rows
from test_eventiesagre_detail_refresh import (
    URL as EES_URL, CDC, CDC_FIXTURES, CDC_SAMPLES, cdc_row,
    html as ees_html, row as ees_row,
)

ROBOTS = b"User-agent: *\nAllow: /\nCrawl-delay: 2\n"
STAMP = datetime(2026, 10, 20, 18, tzinfo=timezone.utc)


class CitynewsIntegrationTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.config = integration.configuration()

    def args(self, **changes):
        args = dict(out=self.root / "run", state_dir=self.root / "previous",
                    today=TODAY, baseline_signature="catalog-baseline",
                    policy_digest="complete-policy", config=self.config,
                    monotonic=lambda: 100.0, deadline=250.0)
        args.update(changes)
        return args

    def run_sources(self, before, *, barrier=None, unsupported=False, **changes):
        calls, deadlines = [], {}
        lock = threading.Lock()
        sample = CDC_SAMPLES["bologna"]
        bodies = {EES_URL: ees_html(), sample["requested_url"]:
                  (CDC_FIXTURES / sample["fixture_file"]).read_bytes()}

        def fetch(url, **kwargs):
            with lock:
                calls.append(url)
            if url.endswith("/robots.txt"):
                if barrier:
                    barrier.wait(timeout=5)
                return ROBOTS, url
            if url in bodies:
                return bodies[url], url
            if unsupported:
                return b"<html><body>" + b"unrecognized template " * 20 + b"</body></html>", url
            return html(canonical=url, schema_url=url), url

        original_editorial, original_citynews = editorial.run, citynews.run

        def reader(original, label, *args, **kwargs):
            deadlines[label] = kwargs["deadline"]
            kwargs.update(sleep=lambda _: None, now=lambda: STAMP)
            return original(*args, **kwargs)

        def existing(*args, **kwargs):
            return reader(original_editorial, kwargs["publisher"], *args, **kwargs)

        def city(*args, **kwargs):
            return reader(original_citynews, "citynews", *args, **kwargs)

        with patch.object(editorial, "run", side_effect=existing), \
                patch.object(citynews, "run", side_effect=city):
            result = integration.run_editorial(before, **self.args(
                fetchers={publisher: fetch for publisher in integration.EDITORIAL_STATES}, **changes))
        return result, calls, deadlines

    def test_three_concurrent_readers_keep_separate_proofs_and_shorter_deadlines(self):
        before = [ees_row(), cdc_row("bologna"), row()]
        original = deepcopy(before)
        (after, report, preserve), calls, deadlines = self.run_sources(
            before, barrier=threading.Barrier(3))
        self.assertEqual(before, original)
        self.assertEqual([r["slug"] for r in after], [r["slug"] for r in before])
        self.assertEqual(preserve, {r["slug"] for r in before})
        cdc_limit = editorial.validate_policy(publisher=CDC)["max_seconds"]
        self.assertEqual(deadlines, {"eventiesagre.it": 250.0, CDC: min(250.0, 100.0 + cdc_limit),
                                     "citynews": 160.0})
        self.assertEqual(report["shared_budget_seconds"], integration.EDITORIAL_SECONDS)
        self.assertEqual(len(calls), 6)
        self.assertEqual(after[2]["date"], ["2026-11-01"])
        self.assertEqual(after[2]["date_quality"], "riportata")
        self.assertEqual(after[2]["status"], before[2]["status"])
        self.assertFalse(after[2]["evidenza_editoriale"]["modified_on"])
        normalized = [normalize(value, TODAY)[0] for value in after]
        proof = integration.verify_editorial_export(normalized, report, today=TODAY)
        self.assertTrue(proof["release_safe"])
        self.assertEqual(set(proof["publishers"]), set(integration.EDITORIAL_STATES))
        normalized[2]["date"] = ["2027-11-01"]
        with self.assertRaises(ValueError):
            integration.verify_editorial_export(normalized, report, today=TODAY)

    def test_queue_is_persisted_protected_from_pruning_and_used_by_next_run(self):
        before = queue_rows(8, hosts=["arezzonotizie.it", "baritoday.it", "bolognatoday.it", "cagliaritoday.it",
            "casertanews.it", "cataniatoday.it", "cesenatoday.it", "ferraratoday.it"])
        (after, report, _), calls, _ = self.run_sources(before)
        phase = report["editorial"]["citynews"]
        self.assertEqual(phase["network_requests"], 8)
        self.assertEqual(phase["source_pages_read"], 4)
        candidate = self.root / "candidate/public/data/v1"
        self.assertTrue(integration.persist_editorial_states(report, out=self.root / "run",
            source_dir=self.root / "previous", destination=candidate, today=TODAY))
        from autopilot import prune_old_assets
        from happings_detail_autopilot import STATE_FILENAME as HAPPINGS_STATE
        from happings_legacy_resources import STATE_FILENAME as LEGACY_STATE
        (candidate / HAPPINGS_STATE).write_text('{"untouched":"detail"}')
        (candidate / LEGACY_STATE).write_text('{"untouched":"legacy"}')
        saved = {p.name: p.read_bytes() for p in candidate.glob("*.json")}
        (candidate / "obsolete-asset.json").write_text("{}")
        self.assertEqual(prune_old_assets(candidate, {}, {}), 1)
        self.assertEqual(saved, {p.name: p.read_bytes() for p in candidate.glob("*.json")})
        normalized = [normalize(value, TODAY)[0] for value in after]
        proof = integration.verify_editorial_export(normalized, report, today=TODAY, state_dir=candidate)
        self.assertEqual(proof["queues"]["citynews"]["status"], "validated_report_bound")
        first_urls = {page["requested_url"] for page in phase["source_pages"]}
        (_, second, _), calls2, _ = self.run_sources(after, out=self.root / "second", state_dir=candidate)
        next_phase = second["editorial"]["citynews"]
        self.assertEqual(next_phase["network_requests"], 8)
        self.assertFalse(first_urls & {page["requested_url"] for page in next_phase["source_pages"]})
        self.assertEqual(next_phase["progress"]["never_read"], 0)
        self.assertEqual(next_phase["state"]["last_completed_cycle"], 1)
        queue = candidate / citynews.STATE_FILENAME
        changed = json.loads(queue.read_text())
        next(iter(changed["resources"].values()))["attempts"] += 1
        citynews.validate_state(changed, today=TODAY)
        queue.write_text(json.dumps(changed))
        with self.assertRaisesRegex(ValueError, "Exported editorial queue"):
            integration.verify_editorial_export(normalized, report, today=TODAY, state_dir=candidate)

    def test_resume_keeps_exact_source_bytes_and_does_not_invoke_transport(self):
        before = [row()]
        (after, report, _), _, _ = self.run_sources(before)
        with patch.object(citynews, "_http", side_effect=AssertionError("unexpected HTTP")), \
                patch.object(editorial, "_http", side_effect=AssertionError("unexpected HTTP")):
            resumed, saved, _ = integration.run_editorial(before, **self.args(resume=True))
        self.assertEqual(resumed, after)
        self.assertEqual(saved["editorial"]["citynews"]["state"], report["editorial"]["citynews"]["state"])
        self.assertEqual(saved["editorial"]["citynews"]["network_requests"], 0)
        self.assertEqual(saved["editorial"]["citynews"]["captured_network_requests"], 2)

    def test_unknown_citynews_template_remains_unsupported_after_persistent_offline_run(self):
        before = [row()]
        (after, report, _), _, _ = self.run_sources(before, unsupported=True)
        self.assertEqual(before, after)
        result = catalog_resources(after, {"sources": []}, today=TODAY, existing_source_report=report)
        self.assertEqual(result["market_layout_statuses"], {"unsupported": 1})
        self.assertEqual(result["market_read_statuses"], {"layout_held": 1})
        reader = result["resources"][0]["readers"][0]
        self.assertTrue(reader["reader_configured"])
        self.assertEqual(reader["source_content_status"], "unsupported")
        candidate = self.root / "candidate"
        integration.persist_editorial_states(report, out=self.root / "run", source_dir=self.root / "previous",
            destination=candidate, today=TODAY)
        (_, offline, _), calls, _ = self.run_sources(before, out=self.root / "offline", state_dir=candidate, offline=True)
        self.assertEqual(calls, [])
        later = catalog_resources(before, {"sources": []}, today=TODAY, existing_source_report=offline)
        self.assertEqual(later["market_layout_statuses"], {"unsupported": 1})
        self.assertEqual(later["market_read_statuses"], {"offline_skipped": 1})

    def test_configured_citynews_route_never_covers_other_host_or_index_or_tracking(self):
        before = [row(), row(slug="index", url_fonte="https://www.bolognatoday.it/eventi/"),
                  row(slug="news", url_fonte="https://www.bolognatoday.it/cronaca/mercato.html"),
                  row(slug="foreign", url_fonte=URL.replace("bolognatoday.it", "unknown.it")),
                  row(slug="tracking", url_fonte=URL + "?utm_source=x")]
        (after, report, _), _, _ = self.run_sources(before)
        covered = catalog_resources(after, {"sources": []}, today=TODAY, existing_source_report=report)
        self.assertEqual(covered["market_layout_statuses"], {"supported": 1, "unsupported": 4})
        self.assertEqual(covered["market_read_statuses"], {"retrieved": 1, "not_read": 4})
        tampered = deepcopy(report)
        tampered["editorial"]["citynews"]["source_pages"][0]["sha256"] = "a" * 64
        invalid = catalog_resources(after, {"sources": []}, today=TODAY, existing_source_report=tampered)
        self.assertEqual(invalid["market_read_statuses"], {"not_observed": 1, "not_read": 4})

    def test_citynews_policy_cannot_raise_budget_or_admit_new_market_ids(self):
        policy = self.config["editorial"]["citynews"]
        for changes in ({"max_requests": 9}, {"max_seconds": 61}, {"new_market_ids_allowed": True},
                        {"overwrite_unowned_fields": True}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                integration.configuration(citynews_policy={**policy, **changes})


if __name__ == "__main__":
    unittest.main()
