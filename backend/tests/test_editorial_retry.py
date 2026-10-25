"""Retry fairness, interrupted requests and real worker termination, offline."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import editorial_transport as transport
import eventiesagre_detail_refresh as reader

# One second after the configured reader deadline (policy file), whatever its value.
PAST_DEADLINE = reader.validate_policy()["max_seconds"] + 1
from test_eventiesagre_detail_refresh import (
    TODAY, URL, html, row, cdc_row, CDC_FIXTURES, CDC_SAMPLES,
)

ROBOTS = b"User-agent: *\nAllow: /\nCrawl-delay: 2\n"
OBSERVED = Path(__file__).parent / "fixtures/editorial_retry/observed_failures_20261020.json"


class Clock:
    def __init__(self, today=TODAY): self.seconds, self.today = 0., today
    def monotonic(self): return self.seconds
    def sleep(self, seconds): self.seconds += seconds
    def now(self): return datetime.combine(self.today, datetime.min.time(), timezone.utc)


class EditorialRetryTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.out = Path(self.directory.name)
        self.clock = Clock()
        self.calls, self.failures = [], set()

    def fetch(self, url, **kwargs):
        self.calls.append(url)
        if url.endswith("/robots.txt"): return ROBOTS, url
        if url in self.failures: raise URLError(socket.gaierror(-3, "test DNS failure"))
        if "cosedicasa.com" in url:
            return (CDC_FIXTURES / CDC_SAMPLES["bologna"]["fixture_file"]).read_bytes(), url
        numeric = url.split("/")[-1].split("_")[0]
        return html(event_id=numeric), url

    def execute(self, rows=None, **changes):
        args = dict(out=self.out, today=self.clock.today, baseline_signature="retry-test",
                    policy_digest="unchanged-policy", fetcher=self.fetch,
                    monotonic=self.clock.monotonic, sleep=self.clock.sleep, now=self.clock.now)
        args.update(changes)
        return reader.run(rows or [row()], **args)

    def inventory(self, count):
        return [row(slug="existing-" + str(i), url_fonte=URL.replace("12345_", str(10000+i) + "_"))
                for i in range(count)]

    def test_eight_observed_failures_migrate_without_fabricating_a_failure_streak_or_read(self):
        fixture = json.loads(OBSERVED.read_text())
        old = fixture["state"]
        self.assertEqual(len(old["resources"]), 8)
        self.assertTrue(all(v["error_type"] == "URLError" and v["network_attempted"] for v in fixture["attempts"]))
        migrated = reader.validate_state(old, today=TODAY)
        self.assertEqual(migrated["schema"], 2)
        for url, entry in migrated["resources"].items():
            self.assertEqual({k: entry[k] for k in old["resources"][url]}, old["resources"][url])
            self.assertEqual(entry["failure_count"], 0)
            self.assertIsNone(entry["last_error_code"])
            self.assertEqual(entry["next_retry_on"], "2026-10-21")
        self.assertEqual(reader.next_requests(migrated, today=TODAY, limit=64), [])
        self.assertEqual(set(reader.next_requests(migrated, today=TODAY+timedelta(days=1), limit=64)), set(old["resources"]))
        self.assertEqual(reader.validate_state(migrated, today=TODAY), migrated)
        self.assertEqual(old["schema"], 1)

    def test_legacy_inflight_cannot_keep_an_unproved_completed_cycle(self):
        old = reader.seed_state([row()], today=TODAY)
        old["schema"] = 1
        for name in ("failure_count", "next_retry_on", "last_error_code"):
            old["resources"][URL].pop(name)
        old["resources"][URL].update(status="inflight", attempts=1, last_attempt=TODAY.isoformat(), attempt_cycle=1)
        old.update(last_completed_cycle=1, last_completed_on=TODAY.isoformat())
        migrated = reader.validate_state(old, today=TODAY)
        self.assertEqual(migrated["resources"][URL]["attempt_cycle"], 0)
        self.assertEqual(migrated["last_completed_cycle"], 0)
        self.assertIsNone(migrated["resources"][URL]["last_read"])

    def test_backoff_1_2_4_7_and_success_reset_for_both_publishers(self):
        for publisher in ("eventiesagre.it", "cosedicasa.com"):
            with self.subTest(publisher=publisher):
                original = row() if publisher == "eventiesagre.it" else cdc_row("bologna")
                url = original["url_fonte"]
                self.failures = {url}; self.clock = Clock(); previous = None
                for failure_number, delay in enumerate((1, 2, 4, 7, 7), 1):
                    _, report, _ = self.execute([original], publisher=publisher, previous_state=previous)
                    item = report["state"]["resources"][url]
                    self.assertEqual(item["failure_count"], failure_number)
                    self.assertEqual(item["last_error_code"], "dns_error")
                    self.assertEqual(item["next_retry_on"], (self.clock.today+timedelta(days=delay)).isoformat())
                    self.assertEqual(report["source_pages_read"], 0)
                    self.assertTrue(report["attempts"][0]["network_attempted"])
                    previous = report["state"]
                    self.clock = Clock(self.clock.today+timedelta(days=delay))
                self.failures.clear()
                _, success, _ = self.execute([original], publisher=publisher, previous_state=previous)
                item = success["state"]["resources"][url]
                self.assertEqual(item["failure_count"], 0)
                self.assertIsNone(item["next_retry_on"])
                self.assertIsNone(item["last_error_code"])
                self.assertEqual(item["last_read"], self.clock.today.isoformat())

    def test_failed_refresh_retains_last_success_hash_and_catalog_evidence(self):
        updated, first, _ = self.execute()
        self.clock = Clock(TODAY+timedelta(days=1)); self.failures.add(URL)
        unchanged, failed, _ = self.execute(updated, previous_state=first["state"])
        self.assertEqual(unchanged, updated)
        for key in ("last_read", "sha256", "last_parsed"):
            self.assertEqual(failed["state"]["resources"][URL][key], first["state"]["resources"][URL][key])
        self.assertEqual(failed["progress"]["retry_pending"], 1)
        self.assertEqual(failed["source_pages_read"], 0)

    def test_due_retries_are_reserved_with_fresh_urls_and_one_request_runs_advance_turn(self):
        rows = self.inventory(30)
        state = reader.seed_state(rows, today=TODAY-timedelta(days=2))
        failed = {r["url_fonte"] for r in rows[:8]}
        for url in failed:
            state["resources"][url].update(status="unavailable", attempts=1,
                last_attempt=(TODAY-timedelta(days=2)).isoformat(), attempt_cycle=1,
                last_error="URLError", last_error_code="dns_error", failure_count=1,
                next_retry_on=(TODAY-timedelta(days=1)).isoformat())
        chosen = reader.next_requests(state, today=TODAY, limit=8)
        self.assertEqual(sum(url in failed for url in chosen), 2)
        self.assertEqual(len(set(chosen)), 8)
        self.failures = failed
        chosen_one = []
        for index in range(4):
            self.clock = Clock(TODAY+timedelta(days=index))
            _, report, _ = self.execute(rows, previous_state=state,
                                       policy={**reader.DEFAULT_POLICY, "max_details": 1})
            chosen_one.append(report["attempts"][0]["url"])
            state = report["state"]
        self.assertEqual(sum(url in failed for url in chosen_one), 1)
        self.assertEqual(len(set(chosen_one) - failed), 3)

    def test_cooldown_or_same_day_failure_performs_no_robot_or_detail_http(self):
        self.failures.add(URL)
        _, failed, _ = self.execute()
        self.calls.clear()
        _, cooling, _ = self.execute(previous_state=failed["state"])
        self.assertEqual(self.calls, [])
        self.assertEqual(cooling["stop_reason"], "no_due_resources")
        self.assertEqual(cooling["progress"]["retry_pending"], 1)
        self.assertEqual(cooling["progress"]["retry_due"], 0)

    def test_deadline_expiring_before_robots_does_not_claim_an_attempt(self):
        ticks = iter([0, 0, PAST_DEADLINE])
        _, report, _ = self.execute(monotonic=lambda:next(ticks, PAST_DEADLINE))
        self.assertEqual(self.calls, [])
        self.assertEqual(report["network_requests"], 0)
        self.assertEqual(report["details_attempted"], 0)
        self.assertEqual(report["stop_reason"], "time_budget")
        self.assertFalse(report["progress"]["attempt_cycle_complete"])

    def test_sleep_overrun_leaves_source_unchanged_and_no_failed_http(self):
        def oversleep(seconds): self.clock.seconds=PAST_DEADLINE
        _, report, _ = self.execute(sleep=oversleep)
        self.assertEqual(self.calls, [reader.ROBOTS])
        self.assertEqual(report["network_requests"], 1)
        self.assertEqual(report["attempts"], [])
        self.assertEqual(report["state"], reader.seed_state([row()], today=TODAY))
        self.assertEqual(report["stop_reason"], "time_budget")

    def test_checkpoint_io_consuming_deadline_rolls_back_unstarted_http(self):
        write = reader._write
        def slow_write(path, value):
            write(path, value)
            if isinstance(value, dict) and value.get("attempts"):
                self.clock.seconds = PAST_DEADLINE
        with patch.object(reader, "_write", side_effect=slow_write):
            _, report, _ = self.execute()
        self.assertEqual(self.calls, [reader.ROBOTS])
        self.assertEqual(report["network_requests"], 1)
        self.assertEqual(report["attempts"], [])
        self.assertEqual(report["state"], reader.seed_state([row()], today=TODAY))
        _, resumed, _ = self.execute(resume=True, fetcher=lambda *a, **k:self.fail("HTTP on resume"))
        self.assertEqual(resumed["state"], report["state"])

    def test_deadline_after_observed_redirect_remains_inflight_and_resumes_without_http(self):
        def redirect(url, **kwargs):
            if url.endswith("robots.txt"): return ROBOTS, url
            self.clock.seconds=PAST_DEADLINE
            raise HTTPError(url,301,"moved",{"Location":url.replace("Mercato+Di+Esempio", "Altro+Slug")},None)
        _, report, _ = self.execute(fetcher=redirect)
        item = report["state"]["resources"][URL]
        self.assertEqual(item["status"], "inflight")
        self.assertEqual(item["attempt_cycle"], 0)
        self.assertEqual(item["next_retry_on"], "2026-10-21")
        self.assertEqual(report["network_requests"], 2)
        self.assertEqual(report["attempts"][0]["request_count"], 1)
        self.assertFalse(report["progress"]["attempt_cycle_complete"])
        _, again, _ = self.execute(resume=True, fetcher=lambda *a,**k:self.fail("HTTP on resume"))
        self.assertEqual(again["state"], report["state"])

    def test_interrupted_http_checkpoint_cannot_be_promoted_to_a_terminal_failure(self):
        def interrupted(url, **kwargs):
            if url.endswith("robots.txt"): return ROBOTS, url
            raise KeyboardInterrupt("local interruption before HTTP outcome")
        with self.assertRaises(KeyboardInterrupt): self.execute(fetcher=interrupted)
        _, resumed, _ = self.execute(resume=True, fetcher=lambda *a,**k:self.fail("HTTP on resume"))
        self.assertEqual(resumed["state"]["resources"][URL]["attempt_cycle"], 0)
        path=self.out/"sources/eventiesagre-detail-pages.json"
        saved=json.loads(path.read_text())
        saved["attempts"][0].update(status="unavailable", error_type="URLError", error_code="transport_error")
        with self.assertRaisesRegex(ValueError, "terminal failure"):
            reader._verify_checkpoint_state(reader.seed_state([row()],today=TODAY),saved["state"],saved["attempts"],[],today=TODAY)

    def test_retry_metadata_and_request_counts_are_reconstructed_on_resume(self):
        self.failures.add(URL); self.execute()
        path=self.out/"sources/eventiesagre-detail-pages.json"; original=json.loads(path.read_text())
        mutations=[lambda v:v["state"]["resources"][URL].update(failure_count=9),
                   lambda v:v["state"]["resources"][URL].update(next_retry_on="2026-10-27"),
                   lambda v:v["state"]["resources"][URL].update(last_read="2026-10-20",sha256="a"*64),
                   lambda v:v.update(network_requests=3),
                   lambda v:v["attempts"][0].update(network_attempted=False),
                   lambda v:v["attempts"][0]["requests"][0].update(status="started")]
        for mutate in mutations:
            altered=deepcopy(original);mutate(altered);path.write_text(json.dumps(altered))
            with self.subTest(mutation=mutations.index(mutate)), self.assertRaises(ValueError):
                self.execute(resume=True)

    def test_pacing_exceeding_budget_is_held_without_unbound_robot_policy(self):
        def too_slow(url, **kwargs):
            self.assertTrue(url.endswith("robots.txt"))
            return b"User-agent: *\nAllow: /\nCrawl-delay: 60\n",url
        _, report, _ = self.execute(fetcher=too_slow)
        self.assertEqual(report["status"], "robots_unavailable")
        self.assertEqual(report["attempts"], [])
        self.assertEqual(report["progress"]["cycle_attempted"],0)


class EditorialTransportTests(unittest.TestCase):
    def test_blocked_worker_is_killed_and_reaped_with_no_network(self):
        original_popen=subprocess.Popen; processes=[]
        def blocked(*args,**kwargs):
            process=original_popen([sys.executable,"-c","import time; time.sleep(30)"],
                stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL)
            processes.append(process);return process
        started=time.monotonic()
        with patch.object(transport.subprocess,"Popen",side_effect=blocked), self.assertRaises(TimeoutError) as failure:
            transport.fetch(URL,timeout=.1,max_bytes=500,accept="text/html")
        self.assertLess(time.monotonic()-started,2)
        self.assertIsNotNone(processes[0].returncode)
        self.assertEqual(transport.failure_code(failure.exception),"deadline_exceeded")

    def test_source_allowlist_is_unchanged_and_rejected_before_worker_start(self):
        urls=["https://www.bolognatoday.it/eventi/example.html","https://127.0.0.1/robots.txt",
              "https://www.eventiesagre.it.evil.example/robots.txt","http://www.eventiesagre.it/robots.txt",
              "https://www.cosedicasa.com/mercatini/foo?other=1"]
        with patch.object(transport.subprocess,"Popen",side_effect=AssertionError("worker should not start")):
            for url in urls:
                with self.subTest(url=url),self.assertRaises(ValueError):
                    transport.fetch(url,timeout=1,max_bytes=500,accept="text/html")

    def test_interrupted_worker_is_killed_reaped_and_original_cause_is_reraised(self):
        original_popen = subprocess.Popen
        for interruption in (KeyboardInterrupt("local cancellation"), OSError("local I/O interruption")):
            processes = []
            def interrupted(*args, **kwargs):
                process = original_popen([sys.executable, "-c", "import time; time.sleep(30)"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
                communicate = process.communicate
                def once(*args, **kwargs):
                    process.communicate = communicate
                    raise interruption
                process.communicate = once
                processes.append(process)
                return process
            try:
                with self.subTest(cause=type(interruption).__name__), \
                     patch.object(transport.subprocess, "Popen", side_effect=interrupted), \
                     self.assertRaises(type(interruption)) as failure:
                    transport.fetch(URL, timeout=1, max_bytes=500, accept="text/html")
                self.assertIs(failure.exception, interruption)
                self.assertIsNotNone(processes[0].returncode)
                self.assertIsNotNone(processes[0].poll())
            finally:
                for process in processes:
                    if process.poll() is None:
                        process.kill()
                        process.communicate()

    def test_transport_diagnostics_distinguish_observed_causes_without_error_text(self):
        cases=[(URLError(socket.gaierror(-3,"private text")),"dns_error"),
               (URLError(TimeoutError("private text")),"transport_timeout"),
               (URLError(ssl.SSLCertVerificationError(1,"private text")),"tls_certificate_error"),
               (URLError("undifferentiated old failure"),"transport_error"),
               (HTTPError(URL,429,"private text",{},None),"http_429")]
        for error,code in cases:
            self.assertEqual(transport.failure_code(error),code)

    def test_observed_redirect_header_survives_worker_but_is_not_followed(self):
        destination=URL.replace("Mercato+Di+Esempio","Altro+Slug")
        payload=json.dumps({"ok":False,"error_type":"HTTPError","error_code":"http_other",
                            "http_status":301,"location":destination}).encode()+b"\n"
        class Process:
            returncode=0
            def communicate(self,*args,**kwargs):return payload,b""
        with patch.object(transport.subprocess,"Popen",return_value=Process()) as opened:
            with self.assertRaises(HTTPError) as failure:
                transport.fetch(URL,timeout=1,max_bytes=500,accept="text/html")
        self.assertEqual(opened.call_count,1)
        self.assertEqual(failure.exception.headers["Location"],destination)
        self.assertEqual(failure.exception.code,301)


if __name__ == "__main__":
    unittest.main()
