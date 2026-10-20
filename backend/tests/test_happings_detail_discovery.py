"""Observed sitemap/HTML discovery, fair refresh and bounded checkpoint tests."""
from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.robotparser import RobotFileParser

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import happings_detail_discovery as discovery

TODAY = date(2026, 10, 20)
STAMP = "2026-10-20T15:32:05+00:00"
ROOT = "https://www.happings.com"
INDEX = ROOT + "/it/sitemap_index.xml"
MAP = ROOT + "/happings_event-sitemap.xml"
PISA = ROOT + "/it/happing/mercato-coperto-campagna-amica-di-pisa/"
LANA = ROOT + "/it/happing/mercato-del-venerdi-mattina-a-lana/"
PESCIA = ROOT + "/it/happing/mercato-di-campagna-amica-di-pescia/"
ROBOTS = ("User-agent: *\nDisallow:\nSitemap: " + INDEX + "\n").encode()
HTML = b"<!doctype html><html><body><h1>Observed event</h1></body></html>"
FIXTURES = Path(__file__).parent / "fixtures"


def robots(text=ROBOTS):
    robot = RobotFileParser()
    robot.parse(text.decode().splitlines())
    return robot


def page(url, body):
    return {"requested_url": url, "final_url": url, "html": body}


def sitemap(urls):
    return ("<urlset>" + "".join(f"<url><loc>{url}</loc><lastmod>2099-01-01</lastmod></url>"
                                for url in urls) + "</urlset>").encode()


def acquire(state, **kwargs):
    return discovery.acquire(state, today=TODAY, max_requests=kwargs.pop("max_requests", 4),
                             robots=kwargs.pop("robots", robots()), sleep=kwargs.pop("sleep", lambda _: None),
                             clock=lambda: STAMP, **kwargs)


class HappingsDetailDiscoveryTests(unittest.TestCase):
    def test_live_index_fixture_only_discovers_the_thirteen_event_sitemaps(self):
        raw = (FIXTURES / "happings_sitemap_index_20261020.xml").read_bytes()
        state = discovery.seed_state(observed_at=TODAY, robots_text=ROBOTS)
        state, report = discovery.ingest_pages(state, [page(INDEX, raw)], observed_at=TODAY)
        self.assertEqual(report["new_sitemap_urls"], 13)
        self.assertEqual(report["links_outside_scope"], 9)
        self.assertEqual(len(state["resources"]), 14)
        self.assertEqual(state["resources"][MAP]["origins"][0], {
            "kind": "sitemap_loc", "url": INDEX, "observed_at": TODAY.isoformat(),
            "sha256": hashlib.sha256(raw).hexdigest(),
        })
        self.assertEqual(state["resources"][MAP]["status"], "unread")

    def test_actual_sitemap_excerpt_ignores_image_urls_and_lastmod(self):
        raw = (FIXTURES / "happings_sitemap_excerpt_20261020.xml").read_bytes()
        state, report = discovery.ingest_pages(discovery.empty_state(), [page(MAP, raw)], observed_at=TODAY)
        self.assertEqual(report["new_detail_urls"], 3)
        for item in state["resources"].values():
            self.assertEqual(item["discovered_at"], TODAY.isoformat())
            self.assertIsNone(item["last_success"])
            self.assertIsNone(item["last_success_at"])

    def test_bootstrap_records_original_sitemap_captures_but_keeps_details_unread(self):
        index = (FIXTURES / "happings_sitemap_index_20261020.xml").read_bytes()
        events = sitemap([PISA, LANA])
        captures = []
        for url, raw in ((INDEX, index), (MAP, events)):
            captures.append({**page(url, raw), "http_status": 200, "content_type": "text/xml; charset=UTF-8",
                             "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(), "captured_at": STAMP})
        state = discovery.seed_state(observed_at=TODAY, robots_text=ROBOTS)
        after, report = discovery.import_observed_pages(state, captures, observed_at=TODAY)
        self.assertEqual(report["imported_sitemaps"], 2)
        self.assertEqual(report["network_requests_performed"], 0)
        self.assertEqual(after["resources"][MAP]["last_success_at"], STAMP)
        self.assertEqual(after["resources"][PISA]["status"], "unread")
        self.assertIsNone(after["resources"][PISA]["last_sha256"])
        repeated, report = discovery.import_observed_pages(after, captures, observed_at=TODAY)
        self.assertEqual(repeated, after)
        self.assertEqual(report["already_imported_sitemaps"], 2)
        for change in ({"sha256": "0" * 64}, {"captured_at": "2026-10-21T00:00:00+00:00"},
                       {"http_status": 206}, {"requested_url": PISA, "final_url": PISA}):
            with self.subTest(change=change):
                with self.assertRaises(ValueError):
                    discovery.import_observed_pages(state, [{**captures[0], **change}], observed_at=TODAY)

    def test_seeds_never_construct_detail_slugs_from_existing_market_names(self):
        row = {"nome": "Mercato coperto Campagna Amica di Pisa", "citta": "Pisa",
               "url_fonte": ROOT + "/it/mercato-settimanale-a-pisa.html"}
        state = discovery.seed_state(catalog_rows=[row], observed_at=TODAY)
        self.assertEqual(state, discovery.empty_state())
        row["fonti"] = [{"url": PISA}]
        state = discovery.seed_state(catalog_rows=[row], seed_urls=[PISA], observed_at=TODAY)
        self.assertEqual(list(state["resources"]), [PISA])
        self.assertEqual({o["kind"] for o in state["resources"][PISA]["origins"]},
                         {"catalog_url", "explicit_seed"})

    def test_url_scope_excludes_alternate_hosts_languages_queries_and_encoded_paths(self):
        bad = [PISA.replace("https:", "http:"), PISA.replace("www.", ""),
               PISA.replace("www.happings.com", "www.happings.com.evil.example"),
               PISA.replace("www.happings.com", "user@www.happings.com"),
               PISA.replace("www.happings.com", "127.0.0.1"), PISA + "?id=1", PISA + "#x",
               PISA.replace("/it/", "/en/"), PISA.replace("/it/", "/%69t/"),
               PISA.replace("www.happings.com", "www.happings.com:443"),
               ROOT + "/post-sitemap.xml", ROOT + "/it/wp-json/oembed", "javascript:alert(1)"]
        for url in bad:
            with self.subTest(url=url):
                self.assertIsNone(discovery.url_kind(url))
        self.assertEqual(discovery.url_kind(PISA), "detail")
        self.assertEqual(discovery.url_kind(MAP.replace(".xml", "13.xml")), "sitemap")

    def test_html_links_are_candidates_not_identity_claims_and_skip_scripts_templates(self):
        raw = (f'<html><a href="/it/happing/mercato-di-campagna-amica-di-pescia/">Other market</a>'
               f'<a href="{PESCIA}">Duplicate</a><script>"<a href=\"{LANA}\">"</script>'
               f'<template><template></template><a href="{LANA}"></a></template>'
               '<a href="https://evil.example/">x</a></html>').encode()
        state, report = discovery.ingest_pages(discovery.empty_state(), [page(PISA, raw)], observed_at=TODAY)
        self.assertEqual(report["new_detail_urls"], 1)
        self.assertEqual(list(state["resources"]), [PESCIA])
        self.assertEqual(state["resources"][PESCIA]["origins"][0]["kind"], "html_link")
        self.assertNotIn("market_id", state["resources"][PESCIA])

    def test_sitemap_entities_wrong_namespace_and_duplicate_locations_fail_closed(self):
        bodies = [b'<!DOCTYPE x [<!ENTITY a "x">]><urlset/>',
                  b'<urlset xmlns="https://evil.example/schema"/>',
                  (f'<urlset><url><loc>{PISA}</loc><loc>{LANA}</loc></url></urlset>').encode(),
                  b'<not-a-sitemap/>']
        for raw in bodies:
            with self.subTest(raw=raw):
                with self.assertRaises(ValueError):
                    discovery.ingest_pages(discovery.empty_state(), [page(MAP, raw)], observed_at=TODAY)

    def test_link_and_frontier_bounds_are_explicit_errors(self):
        with patch.object(discovery, "MAX_LINKS_PER_PAGE", 1):
            with self.assertRaisesRegex(ValueError, "link bound"):
                discovery.ingest_pages(discovery.empty_state(), [page(MAP, sitemap([PISA, LANA]))], observed_at=TODAY)
        with patch.object(discovery, "MAX_RESOURCES", 1):
            with self.assertRaisesRegex(ValueError, "frontier"):
                discovery.seed_state(seed_urls=[PISA, LANA], observed_at=TODAY)

    def test_budget_includes_sitemaps_then_detail_and_never_fetches_robots_again(self):
        state = discovery.seed_state(seed_urls=[PISA], robots_text=ROBOTS, observed_at=TODAY)
        bodies = {INDEX: (f'<sitemapindex><sitemap><loc>{MAP}</loc></sitemap></sitemapindex>').encode(),
                  MAP: sitemap([PISA, LANA, PESCIA]), PISA: HTML}
        fetched = []
        def fetch(url, **kwargs):
            fetched.append(url)
            return bodies[url], url
        after, pages, report = acquire(state, max_requests=3, fetcher=fetch)
        self.assertEqual(fetched, [INDEX, MAP, PISA])
        self.assertEqual(report["requests_attempted"], 3)
        self.assertEqual(report["sitemaps_read"], 2)
        self.assertEqual(report["details_read"], 1)
        self.assertEqual(report["robots_fetches"], 0)
        self.assertEqual([p["requested_url"] for p in pages], [PISA])
        self.assertEqual(pages[0]["fetched_at"], STAMP)
        self.assertEqual(after["resources"][PISA]["last_success_at"], STAMP)
        self.assertEqual(after["resources"][LANA]["status"], "unread")
        self.assertEqual(state["resources"][PISA]["status"], "unread")

    def test_acquisition_preserves_success_when_another_page_fails_and_backoff_survives(self):
        state = discovery.seed_state(seed_urls=[PISA, LANA], observed_at=TODAY)
        def fetch(url, **kwargs):
            if url == LANA:
                raise OSError("unavailable")
            return HTML, url
        after, pages, report = acquire(state, fetcher=fetch)
        self.assertEqual(len(pages), 1)
        self.assertEqual(report["requests_attempted"], 2)
        self.assertEqual(after["resources"][LANA]["status"], "unavailable")
        self.assertEqual(after["resources"][LANA]["next_due"], "2026-10-21")
        self.assertEqual(discovery.next_requests(after, today=TODAY, limit=4), [])
        self.assertEqual(discovery.next_requests(after, today=TODAY + timedelta(days=1), limit=4), [LANA])

    def test_interruption_checkpoint_retains_prior_html_and_does_not_repeat_same_day(self):
        state = discovery.seed_state(seed_urls=[PISA, LANA, PESCIA], observed_at=TODAY)
        snapshots = []
        count = 0
        def fetch(url, **kwargs):
            nonlocal count
            count += 1
            if count == 2:
                raise KeyboardInterrupt()
            return HTML, url
        with self.assertRaises(KeyboardInterrupt):
            acquire(state, fetcher=fetch, checkpoint=lambda *args: snapshots.append(args))
        saved, pages, report = snapshots[-1]
        self.assertEqual(len(pages), 1)
        self.assertEqual(pages[0]["html"], HTML)
        inflight = report["inflight"]["requested_url"]
        self.assertTrue(report["inflight"]["network_attempted"])
        self.assertEqual(saved["resources"][inflight]["status"], "fetching")
        self.assertNotIn(inflight, discovery.next_requests(saved, today=TODAY, limit=4))
        self.assertEqual(report["requests_attempted"], 2)

    def test_due_rereads_cannot_be_starved_by_a_large_unseen_frontier(self):
        state = discovery.seed_state(seed_urls=[PISA, LANA, PESCIA], observed_at=TODAY)
        state, _, _ = acquire(state, fetcher=lambda url, **kw: (HTML, url))
        later = TODAY + timedelta(days=7)
        new = [ROOT + f"/it/happing/mercato-new-{i}/" for i in range(20)]
        state = discovery.seed_state(state, seed_urls=new, observed_at=later)
        selected = discovery.next_requests(state, today=later, limit=9)
        self.assertEqual(len(selected), 9)
        self.assertEqual(len(set(selected) & {PISA, LANA, PESCIA}), 3)
        self.assertEqual(len(set(selected) & set(new)), 6)

    def test_catalog_seeds_and_market_slug_priority_do_not_become_matching_evidence(self):
        generic = ROOT + "/it/happing/aaa-concerto/"
        unknown_name = ROOT + "/it/happing/zzzz/"
        state, _ = discovery.ingest_pages(discovery.empty_state(), [page(MAP, sitemap([generic, PISA, unknown_name]))], observed_at=TODAY)
        state = discovery.seed_state(state, catalog_rows=[{"url_fonte": unknown_name}], observed_at=TODAY)
        self.assertEqual(discovery.next_requests(state, today=TODAY, limit=3), [unknown_name, PISA, generic])
        self.assertFalse(any("category" in r or "market_id" in r for r in state["resources"].values()))

    def test_refresh_priority_reserves_both_unseen_and_other_event_slots(self):
        primary = [ROOT + f"/it/happing/mercato-{i}/" for i in range(12)]
        other = [ROOT + f"/it/happing/concerto-{i}/" for i in range(6)]
        oldest_unseen = ROOT + "/it/happing/ancora-da-leggere/"
        state, _ = discovery.ingest_pages(discovery.empty_state(),
            [page(MAP, sitemap(primary + other + [oldest_unseen]))], observed_at=TODAY)
        later = TODAY + timedelta(days=7)
        for url in primary + other:
            state["resources"][url].update(last_attempt=TODAY.isoformat(), last_success=TODAY.isoformat(),
                last_success_at=STAMP, last_sha256=hashlib.sha256(HTML).hexdigest(),
                attempts=1, status="retrieved", next_due=later.isoformat())
        new_market = ROOT + "/it/happing/mercato-nuovo/"
        state, _ = discovery.ingest_pages(state, [page(MAP, sitemap([new_market]))], observed_at=later)
        selected = discovery.next_requests(state, today=later, limit=9)
        self.assertEqual(len(set(selected) & set(primary)), 6)
        self.assertEqual(len(set(selected) & set(other)), 1)
        self.assertEqual(selected[2], new_market)
        self.assertEqual(selected[5], oldest_unseen)
        self.assertEqual(len(set(selected)), 9)

    def test_first_pass_gets_majority_slots_when_unread_outnumbers_due_refresh(self):
        primary = [ROOT + f"/it/happing/mercato-gia-letto-{i}/" for i in range(18)]
        other = [ROOT + f"/it/happing/concerto-gia-letto-{i}/" for i in range(6)]
        old_unread = ROOT + "/it/happing/zz-vecchia-pagina/"
        state, _ = discovery.ingest_pages(discovery.empty_state(),
            [page(MAP, sitemap(primary + other + [old_unread]))], observed_at=TODAY)
        later = TODAY + timedelta(days=7)
        for url in primary + other:
            state["resources"][url].update(
                last_attempt=TODAY.isoformat(), last_success=TODAY.isoformat(),
                last_success_at=STAMP, last_sha256=hashlib.sha256(HTML).hexdigest(),
                attempts=1, status="retrieved", next_due=later.isoformat())
        fresh = [ROOT + f"/it/happing/mercato-mai-letto-{i}/" for i in range(36)]
        state, _ = discovery.ingest_pages(state, [page(MAP, sitemap(fresh))], observed_at=later)
        selected = discovery.next_requests(state, today=later, limit=9)
        self.assertEqual(len(selected), 9)
        self.assertEqual(len(set(selected)), 9)
        self.assertEqual(len(set(selected) & set(primary)), 2)
        self.assertEqual(len(set(selected) & set(other)), 1)
        self.assertEqual(len(set(selected) & (set(fresh) | {old_unread})), 6)
        self.assertIn(old_unread, selected)  # oldest first despite newly discovered market slugs
        self.assertEqual(discovery.next_requests(state, today=later, limit=9), selected)
        self.assertTrue(all(state["resources"][url]["status"] != "fetching" for url in selected))

    def test_elapsed_limit_before_delay_preserves_unread_frontier(self):
        state = discovery.seed_state(seed_urls=[PISA], observed_at=TODAY)
        fetch, pause = Mock(), Mock()
        after, pages, report = acquire(state, fetcher=fetch, sleep=pause,
                                       max_seconds=2, monotonic=lambda: 0)
        self.assertEqual(after, state)
        self.assertEqual(pages, [])
        fetch.assert_not_called()
        pause.assert_not_called()
        self.assertEqual(report["budget_stop"], "elapsed_limit")
        self.assertEqual(report["max_seconds"], 2)

    def test_elapsed_limit_after_delay_leaves_selected_url_unattempted(self):
        state = discovery.seed_state(seed_urls=[PISA], observed_at=TODAY)
        now = [0]
        def pause(_):
            now[0] += 5
        fetch = Mock()
        after, pages, report = acquire(state, fetcher=fetch, sleep=pause,
                                       max_seconds=4, monotonic=lambda: now[0])
        self.assertEqual(after, state)
        fetch.assert_not_called()
        self.assertEqual(report["elapsed_seconds"], 5)
        self.assertEqual(report["budget_stop"], "elapsed_limit")

    def test_elapsed_stop_retains_prior_html_and_unstarted_remaining_work(self):
        state = discovery.seed_state(seed_urls=[PISA, LANA], observed_at=TODAY)
        now, snapshots = [0], []
        def pause(seconds):
            now[0] += seconds
        def fetch(url, **kwargs):
            now[0] += 1
            return HTML, url
        after, pages, report = acquire(state, fetcher=fetch, sleep=pause,
            max_seconds=7, monotonic=lambda: now[0], checkpoint=lambda *args: snapshots.append(args))
        self.assertEqual(report["requests_attempted"], 1)
        self.assertEqual(report["elapsed_seconds"], 4)
        self.assertEqual(report["budget_stop"], "elapsed_limit")
        self.assertEqual(len(pages), 1)
        remaining = ({PISA, LANA} - {pages[0]["requested_url"]}).pop()
        self.assertEqual(after["resources"][remaining], state["resources"][remaining])
        self.assertEqual(snapshots[-1], (after, pages, report))

    def test_deadline_crossed_in_checkpoint_restores_unstarted_request(self):
        state = discovery.seed_state(seed_urls=[PISA], observed_at=TODAY)
        now, snapshots = [0], []
        def save(*args):
            snapshots.append(args)
            if (args[2].get("inflight") or {}).get("network_attempted"):
                now[0] += 10
        fetch = Mock()
        after, pages, report = acquire(state, fetcher=fetch, checkpoint=save,
                                       max_seconds=5, monotonic=lambda: now[0])
        self.assertEqual(after, state)
        fetch.assert_not_called()
        self.assertEqual(report["requests_attempted"], 0)
        self.assertEqual(report["outcomes"], [])
        self.assertIsNone(report["inflight"])
        self.assertEqual(report["budget_stop"], "elapsed_limit")
        self.assertEqual(snapshots[-1], (after, pages, report))

    def test_128_page_request_budget_is_bounded_and_reported(self):
        urls = [ROOT + f"/it/happing/mercato-{i}/" for i in range(129)]
        state = discovery.seed_state(seed_urls=urls, observed_at=TODAY)
        after, pages, report = acquire(state, max_requests=128, fetcher=lambda url, **kw: (HTML, url))
        self.assertEqual(report["requests_attempted"], 128)
        self.assertEqual(len(pages), 128)
        self.assertEqual(report["pending_detail_urls"], 1)
        self.assertEqual(report["budget_stop"], "request_limit")
        self.assertEqual(report["max_seconds"], 420)

    def test_robots_denial_never_calls_fetcher(self):
        state = discovery.seed_state(seed_urls=[PISA], observed_at=TODAY)
        fetcher = Mock()
        after, pages, report = acquire(state, robots=robots(b"User-agent: *\nDisallow: /it/happing/\n"), fetcher=fetcher)
        fetcher.assert_not_called()
        self.assertEqual(report["requests_attempted"], 0)
        self.assertEqual(after["resources"][PISA]["status"], "robots_denied")
        self.assertEqual(pages, [])

    def test_redirect_response_is_held_without_changing_the_original_url(self):
        state = discovery.seed_state(seed_urls=[PISA], observed_at=TODAY)
        after, pages, report = acquire(state, fetcher=lambda *a, **k: (HTML, LANA))
        self.assertEqual(pages, [])
        self.assertEqual(after["resources"][PISA]["status"], "unavailable")
        self.assertNotIn(LANA, after["resources"])

    def test_live_clock_cannot_relabel_a_historical_fetch(self):
        state = discovery.seed_state(seed_urls=[PISA], observed_at=TODAY)
        for stamp in ("2026-10-21T00:00:00+00:00", "2026-10-20T15:00:00+02:00", "2026-10-20T15:00:00"):
            with self.subTest(stamp=stamp):
                after, pages, report = discovery.acquire(state, today=TODAY, max_requests=1,
                    robots=robots(), sleep=lambda _: None, fetcher=lambda url, **kw: (HTML, url),
                    clock=lambda: stamp)
                self.assertEqual(pages, [])
                self.assertIsNone(after["resources"][PISA]["last_success"])
                self.assertEqual(report["outcomes"][0]["error_type"], "ValueError")

    def test_altered_provenance_future_dates_and_hashes_are_rejected_before_fetch(self):
        state = discovery.seed_state(seed_urls=[PISA], observed_at=TODAY)
        cases = []
        altered = copy.deepcopy(state); altered["resources"][PISA]["origins"][0]["url"] = LANA; cases.append(altered)
        altered = copy.deepcopy(state); altered["resources"][PISA]["discovered_at"] = "2026-10-21"; cases.append(altered)
        altered = copy.deepcopy(state); altered["resources"][PISA]["last_sha256"] = "bad"; cases.append(altered)
        for item in cases:
            with self.subTest(item=item):
                with self.assertRaises(ValueError):
                    acquire(item, fetcher=Mock())

    def test_budget_bounds_do_not_allow_bool_or_unbounded_values(self):
        for value in (-1, 129, True, "3"):
            with self.subTest(value=value):
                with self.assertRaises(ValueError):
                    acquire(discovery.empty_state(), max_requests=value, fetcher=Mock())
        for value in (0, 421, True, "420"):
            with self.subTest(max_seconds=value), self.assertRaises(ValueError):
                acquire(discovery.empty_state(), max_seconds=value, fetcher=Mock())

    def test_http_layer_requires_public_dns_exact_url_status_and_content_type(self):
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.url = PISA
        response.status = 200
        response.headers = {"Content-Type": "text/html; charset=UTF-8"}
        response.read.return_value = HTML
        opener = Mock()
        opener.open.return_value = response
        with patch.object(discovery.weekly, "_public_dns") as dns:
            self.assertEqual(discovery.fetch_one(PISA, robots=robots(), opener=opener), (HTML, PISA))
            dns.assert_called_once_with("www.happings.com")
        for field, value in (("url", LANA), ("status", 206), ("headers", {"Content-Type": "application/json"})):
            original = getattr(response, field)
            setattr(response, field, value)
            with self.subTest(field=field), patch.object(discovery.weekly, "_public_dns"):
                with self.assertRaises(ValueError):
                    discovery.fetch_one(PISA, robots=robots(), opener=opener)
            setattr(response, field, original)
        opener.reset_mock()
        with patch.object(discovery.weekly, "_public_dns", side_effect=ValueError("private address")):
            with self.assertRaises(ValueError):
                discovery.fetch_one(PISA, robots=robots(), opener=opener)
        opener.open.assert_not_called()

    def test_http_redirects_are_rejected_before_any_second_request(self):
        with self.assertRaisesRegex(ValueError, "without following"):
            discovery._NoRedirects().redirect_request(None, None, 302, "redirect", {}, LANA)


if __name__ == "__main__":
    unittest.main()
