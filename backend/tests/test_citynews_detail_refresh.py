"""No-network tests of request accounting, queue progression and byte replay."""
import base64
from copy import deepcopy
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
import sys
import tempfile
import subprocess
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from citynews_detail_refresh import (
    DEFAULT_POLICY, MAX_BYTES, STATE_FILENAME, _pack, _unpack, catalog_urls,
    progress, run, seed_state, validate_policy, validate_state,
)
from citynews_transport import fetch as bounded_transport
from test_citynews_detail import TODAY, URL, html, row

ROBOTS = b"User-agent: *\nAllow: /\nCrawl-delay: 2\n"


class Clock:
    def __init__(self): self.seconds = 0
    def monotonic(self): return self.seconds
    def sleep(self, duration): self.seconds += duration
    def now(self): return datetime(2026, 10, 20, 18, 0, tzinfo=timezone.utc)


def rows(count=8, *, hosts=None):
    hosts = hosts or ["bolognatoday.it"]
    return [row(slug="citynews-" + str(i), url_fonte="https://www." + hosts[i % len(hosts)] + "/eventi/test-" + str(i) + ".html")
            for i in range(count)]


class QueueTests(unittest.TestCase):
    def setup_run(self, directory, *, fetcher=None, **changes):
        clock = Clock(); calls = []
        def fetch(url, **kwargs):
            calls.append(url)
            if fetcher: return fetcher(url, **kwargs)
            return (ROBOTS if url.endswith("/robots.txt") else html(canonical=url, schema_url=url)), url
        args = dict(out=directory, today=TODAY, baseline_signature="baseline-test", policy_digest="pipeline-test",
                    fetcher=fetch, monotonic=clock.monotonic, sleep=clock.sleep, now=clock.now)
        args.update(changes)
        return args, calls, clock

    def test_robots_count_inside_eight_total_requests_and_unread_queue_continues(self):
        hosts = ["arezzonotizie.it", "baritoday.it", "bolognatoday.it", "cagliaritoday.it",
                 "casertanews.it", "cataniatoday.it", "cesenatoday.it", "ferraratoday.it"]
        original = rows(hosts=hosts)
        with tempfile.TemporaryDirectory() as directory:
            args, calls, clock = self.setup_run(directory)
            result, first, _ = run(original, **args)
            self.assertEqual(len(calls), 8)
            self.assertEqual(first["network_requests"], 8)
            self.assertEqual(first["source_pages_read"], 4)
            self.assertEqual(first["progress"]["never_read"], 4)
            first_urls = {p["requested_url"] for p in first["source_pages"]}
            self.assertEqual(first["stop_reason"], "request_limit")
            second_dir = Path(directory) / "next"
            more, calls2, _ = self.setup_run(second_dir, previous_state=first["state"])
            _, second, _ = run(result, **more)
            self.assertEqual(len(calls2), 8)
            self.assertFalse(first_urls & {p["requested_url"] for p in second["source_pages"]})
            self.assertEqual(second["progress"]["never_read"], 0)
            self.assertEqual(second["state"]["last_completed_cycle"], 1)
            self.assertEqual(seed_state(original, second["state"], today=TODAY)["cycle"], 2)
            self.assertEqual([r["slug"] for r in result], [r["slug"] for r in original])

    def test_same_host_reuses_only_current_robots_and_respects_pacing(self):
        with tempfile.TemporaryDirectory() as directory:
            args, calls, clock = self.setup_run(directory)
            _, report, _ = run(rows(8), **args)
            self.assertEqual(sum(u.endswith("robots.txt") for u in calls), 1)
            self.assertEqual(report["source_pages_read"], 7)
            self.assertEqual(report["network_requests"], 8)
            self.assertGreaterEqual(clock.seconds, 14)

    def test_failed_detail_requests_respect_the_same_host_pacing(self):
        clock = Clock(); observed_times = []
        def fetch(url, **kwargs):
            if url.endswith("robots.txt"): return ROBOTS, url
            observed_times.append(clock.seconds)
            raise URLError("synthetic failure")
        with tempfile.TemporaryDirectory() as directory:
            args, _, _ = self.setup_run(directory, fetcher=fetch, monotonic=clock.monotonic, sleep=clock.sleep)
            _, report, _ = run(rows(3), **args)
            self.assertEqual(observed_times, [2, 4, 6])
            self.assertEqual(report["network_requests"], 4)

    def test_robots_denial_has_no_detail_http_or_fake_read(self):
        def denied(url, **kwargs):
            self.assertTrue(url.endswith("robots.txt"))
            return b"User-agent: *\nDisallow: /eventi/\n", url
        with tempfile.TemporaryDirectory() as directory:
            args, calls, _ = self.setup_run(directory, fetcher=denied)
            original = rows(2); result, report, _ = run(original, **args)
            self.assertEqual(result, original)
            self.assertEqual(len(calls), 1)
            self.assertEqual(report["source_pages_read"], 0)
            self.assertEqual(report["progress"]["never_read"], 2)
            self.assertTrue(all(a["status"] == "robots_denied" and not a["network_attempted"] for a in report["attempts"]))

    def test_robots_failure_is_counted_and_does_not_block_other_publishers(self):
        def fetch(url, **kwargs):
            if "baritoday.it" in url: raise URLError("captured test transport failure")
            return (ROBOTS if url.endswith("robots.txt") else html(canonical=url, schema_url=url)), url
        with tempfile.TemporaryDirectory() as directory:
            args, calls, _ = self.setup_run(directory, fetcher=fetch)
            _, report, _ = run(rows(2, hosts=["baritoday.it", "bolognatoday.it"]), **args)
            self.assertEqual(report["network_requests"], 3)
            self.assertEqual(report["source_pages_read"], 1)
            self.assertEqual(report["attempts"][0]["status"], "unavailable")
            self.assertFalse(report["attempts"][0]["network_attempted"])

    def test_observed_redirect_is_never_followed_into_another_edition(self):
        def fetch(url, **kwargs):
            if url.endswith("robots.txt"): return ROBOTS, url
            raise HTTPError(url, 301, "Moved", {"Location": url.replace("test", "other-edition")}, None)
        with tempfile.TemporaryDirectory() as directory:
            args, calls, _ = self.setup_run(directory, fetcher=fetch)
            original = rows(1); result, report, _ = run(original, **args)
            self.assertEqual(result, original)
            self.assertEqual(len(calls), 2)
            self.assertEqual(report["source_pages_read"], 0)
            self.assertEqual(report["requests"][1]["http_status"], 301)
            self.assertEqual(report["attempts"][0]["error_type"], "HTTPError")

    def test_bad_layout_and_oversized_field_hold_only_that_source(self):
        def fetch(url, **kwargs):
            if url.endswith("robots.txt"): return ROBOTS, url
            return html(title="x" * 5000, canonical=url, schema_url=url) if "test-0" in url else html(canonical=url, schema_url=url), url
        with tempfile.TemporaryDirectory() as directory:
            args, _, _ = self.setup_run(directory, fetcher=fetch)
            original = rows(2); result, report, _ = run(original, **args)
            self.assertEqual(result[0], original[0])
            self.assertNotEqual(result[1], original[1])
            self.assertEqual(report["source_pages_read"], 2)
            self.assertEqual(report["documents_parsed"], 1)
            self.assertEqual(report["attempts"][0]["status"], "layout_held")
            self.assertEqual(report["progress"]["never_read"], 0)
            self.assertIsNone(report["state"]["resources"][original[0]["url_fonte"]]["last_parsed"])

    def test_unknown_template_is_a_real_http_read_but_no_supported_extraction(self):
        def fetch(url, **kwargs):
            return (ROBOTS if url.endswith("robots.txt") else b"<html><body>" + b"unrecognized " * 20 + b"</body></html>"), url
        with tempfile.TemporaryDirectory() as directory:
            args, _, _ = self.setup_run(directory, fetcher=fetch)
            original = rows(1); result, report, _ = run(original, **args)
            self.assertEqual(result, original)
            self.assertEqual(report["source_pages_read"], 1)
            self.assertEqual(report["documents_parsed"], 0)
            self.assertEqual(report["evidence"]["outcomes"][0]["reason"], "source_layout_unsupported")

    def test_shared_deadline_stops_before_unattempted_request(self):
        with tempfile.TemporaryDirectory() as directory:
            args, calls, _ = self.setup_run(directory, deadline=1)
            original = rows(2); result, report, _ = run(original, **args)
            self.assertEqual(result, original)
            self.assertEqual(calls, [])
            self.assertEqual(report["stop_reason"], "time_budget")
            self.assertEqual(report["details_attempted"], 0)

    def test_deadline_expiring_between_loop_and_read_does_not_complete_an_attempt(self):
        ticks = iter([0, 0, 60, 60, 60, 60])
        with tempfile.TemporaryDirectory() as directory:
            args, calls, _ = self.setup_run(directory, monotonic=lambda: next(ticks, 60))
            original = rows(1); result, report, _ = run(original, **args)
            self.assertEqual(result, original)
            self.assertEqual(calls, [])
            self.assertEqual(report["network_requests"], 0)
            self.assertEqual(report["stop_reason"], "time_budget")
            self.assertEqual(report["state"]["last_completed_cycle"], 0)
            self.assertEqual(report["progress"]["attempted_in_cycle"], 0)

    def test_pacing_sleep_that_passes_deadline_does_not_claim_a_failed_http_read(self):
        with tempfile.TemporaryDirectory() as directory:
            args, calls, clock = self.setup_run(directory)
            args["sleep"] = lambda seconds: clock.sleep(seconds + 60)
            original = rows(1); result, report, _ = run(original, **args)
            self.assertEqual(result, original)
            self.assertEqual(len(calls), 1)
            self.assertEqual(report["network_requests"], 1)
            self.assertEqual(report["attempts"][0]["status"], "inflight")
            self.assertFalse(report["attempts"][0]["network_attempted"])
            self.assertEqual(report["state"]["last_completed_cycle"], 0)
            self.assertEqual(report["stop_reason"], "time_budget")

    def test_publisher_pacing_larger_than_remaining_budget_preserves_unread_resource(self):
        def fetch(url, **kwargs):
            self.assertTrue(url.endswith("robots.txt"))
            return b"User-agent: *\nAllow: /\nCrawl-delay: 10\n", url
        with tempfile.TemporaryDirectory() as directory:
            args, calls, _ = self.setup_run(directory, fetcher=fetch, policy={**DEFAULT_POLICY, "max_seconds": 5})
            original = rows(1); result, report, _ = run(original, **args)
            self.assertEqual(result, original)
            self.assertEqual(len(calls), 1)
            self.assertEqual(report["attempts"][0]["status"], "inflight")
            self.assertEqual(report["progress"]["attempted_in_cycle"], 0)
            self.assertEqual(report["progress"]["never_read"], 1)

    def test_resume_replays_captured_bytes_without_new_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            args, calls, _ = self.setup_run(directory)
            original = rows(2); result, report, keep = run(original, **args)
            def no_network(url, **kwargs): raise AssertionError("resume must not perform HTTP")
            replay, saved, saved_keep = run(original, **{**args, "resume": True, "fetcher": no_network})
            self.assertEqual(replay, result)
            self.assertEqual(saved["evidence"], report["evidence"])
            self.assertEqual(saved["state"], report["state"])
            self.assertEqual(saved["network_requests"], 0)
            self.assertEqual(saved["captured_network_requests"], 3)
            self.assertEqual(saved_keep, keep)
            self.assertEqual(json.loads((Path(directory) / STATE_FILENAME).read_text()), report["state"])

    def test_checkpoint_context_ids_state_counts_and_extra_fields_are_not_trusted(self):
        with tempfile.TemporaryDirectory() as directory:
            args, _, _ = self.setup_run(directory)
            original = rows(2); run(original, **args)
            path = Path(directory) / "sources/citynews-detail-pages.json"
            saved = json.loads(path.read_text())
            mutations = [lambda v: v["context"].update(baseline="other"),
                lambda v: v.update(extra=True), lambda v: v["state"]["resources"][original[0]["url_fonte"]].update(attempts=42),
                lambda v: v["attempts"][0].update(network_attempted=False),
                lambda v: v["requests"].append({"url": URL, "kind": "detail", "status": "started"}),
                lambda v: v["pages"][0].update(sha256="a" * 64),
                lambda v: v["pages"][0].update(read_on="2026-10-19"),
                lambda v: v["pages"][0].update(extra=True),
                lambda v: v["pages"].append(deepcopy(v["pages"][0]))]
            for mutate in mutations:
                with self.subTest(mutation=mutations.index(mutate)):
                    altered = deepcopy(saved); mutate(altered); path.write_text(json.dumps(altered))
                    with self.assertRaises(ValueError): run(original, **{**args, "resume": True})
            path.write_text(json.dumps(saved))
            with self.assertRaises(ValueError): run(original, **{**args, "resume": True, "policy_digest": "other"})
            with self.assertRaises(ValueError): run(original + [row(slug="extra")], **{**args, "resume": True})

    def test_replay_requires_robots_before_even_failed_or_interrupted_page_requests(self):
        with tempfile.TemporaryDirectory() as directory:
            args, _, _ = self.setup_run(directory)
            original = rows(1); run(original, **args)
            path = Path(directory) / "sources/citynews-detail-pages.json"
            saved = json.loads(path.read_text()); saved["requests"].reverse()
            saved["attempts"][0].update(robots_request=1, page_request=0)
            path.write_text(json.dumps(saved))
            with self.assertRaisesRegex(ValueError, "preceded or violated"):
                run(original, **{**args, "resume": True})
        def failed(url, **kwargs):
            if url.endswith("robots.txt"): return ROBOTS, url
            raise URLError("synthetic failure")
        with tempfile.TemporaryDirectory() as directory:
            args, _, _ = self.setup_run(directory, fetcher=failed)
            original = rows(1); run(original, **args)
            path = Path(directory) / "sources/citynews-detail-pages.json"
            saved = json.loads(path.read_text())
            saved["requests"][1] = {"url": original[0]["url_fonte"], "kind": "detail", "status": "started"}
            path.write_text(json.dumps(saved))
            with self.assertRaisesRegex(ValueError, "terminal failure"):
                run(original, **{**args, "resume": True})

    def test_hard_timeout_kills_and_reaps_a_blocked_worker_without_http(self):
        processes = []; original_popen = subprocess.Popen
        def blocked(argv, **kwargs):
            self.assertTrue(argv[1].endswith("citynews_transport.py"))
            self.assertEqual(argv[2:], ["--http-worker"])
            self.assertIs(kwargs["shell"], False)
            process = original_popen([sys.executable, "-c", "import time; time.sleep(30)"], **kwargs)
            processes.append(process)
            return process
        started = time.monotonic()
        with patch("citynews_transport.subprocess.Popen", side_effect=blocked):
            with self.assertRaises(TimeoutError):
                bounded_transport(URL, timeout=.1, max_bytes=MAX_BYTES, accept="text/html")
        self.assertLess(time.monotonic() - started, 2)
        self.assertEqual(len(processes), 1)
        self.assertIsNotNone(processes[0].returncode)

    def test_gzip_os_header_variation_is_portable_but_corruption_is_not(self):
        packed = _pack(html(), URL, TODAY.isoformat())
        for os_byte in (3, 255):
            variant = deepcopy(packed); body = bytearray(base64.b64decode(variant["body_gzip_base64"])); body[9] = os_byte
            variant["body_gzip_base64"] = base64.b64encode(body).decode()
            self.assertEqual(_unpack(variant, today=TODAY, kind="detail"), html())
        for compressed in (gzip.compress(html())[:-6], gzip.compress(b"x" * (MAX_BYTES + 1)), b"not gzip"):
            variant = deepcopy(packed); variant["body_gzip_base64"] = base64.b64encode(compressed).decode()
            with self.assertRaises(ValueError): _unpack(variant, today=TODAY, kind="detail")

    def test_disabled_offline_and_missing_resume_make_no_http_claim(self):
        for options in ({"offline": True}, {"resume": True}, {"policy": {**DEFAULT_POLICY, "enabled": False}}):
            with self.subTest(options=options), tempfile.TemporaryDirectory() as directory:
                args, calls, _ = self.setup_run(directory, **options)
                original = rows(1); result, report, _ = run(original, **args)
                self.assertEqual(result, original)
                self.assertEqual(calls, [])
                self.assertEqual(report["source_pages_read"], 0)
                self.assertEqual(report["network_requests"], 0)
                self.assertEqual(report["progress"]["never_read"], 1)

    def test_policy_cannot_add_ids_overwrite_unowned_fields_or_expand_budget(self):
        for changes in ({"max_requests": 9}, {"max_seconds": 61}, {"min_delay_seconds": 0},
                        {"new_market_ids_allowed": True}, {"overwrite_unowned_fields": True}):
            with self.assertRaises(ValueError): validate_policy({**DEFAULT_POLICY, **changes})
        state = seed_state(rows(1), today=TODAY)
        altered = deepcopy(state); altered["resources"][URL] = altered["resources"].pop(rows(1)[0]["url_fonte"])
        altered["resources"]["https://www.bolognatoday.it/eventi/"] = altered["resources"].pop(URL)
        with self.assertRaises(ValueError): validate_state(altered, today=TODAY)


if __name__ == "__main__":
    unittest.main()
