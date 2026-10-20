"""Synthetic, network-free tests of observed legacy-resource traversal.

The HTML below reproduces the reviewed canonical/headings/list structure; it
is deliberately not represented as a saved original Happings response.
"""
from __future__ import annotations

import base64
import copy
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch
from urllib.robotparser import RobotFileParser

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import autopilot
import happings_autopilot as phase
import happings_legacy_resources as legacy
import happings_source_enrichment as source
from export_static import export
from merge_catalog import load_existing
from test_happings_autopilot import pipeline_policy

TODAY = date(2026, 10, 20)
TRIESTE = "https://www.happings.com/it/mercato-settimanale-a-trieste.html"
TRIESTE_PAGE = "https://www.happings.com/it/mercati-settimanali-a-trieste-e-provincia/"
GORIZIA_PAGE = "https://www.happings.com/it/mercati-settimanali-a-gorizia-e-provincia/"


def market(slug="fixture-trieste", *, city="Trieste", province="TS", region="Friuli-Venezia Giulia", url=TRIESTE):
    return {"slug": slug, "nome": "Mercato settimanale di " + city, "citta": city,
            "provincia": province, "regione": region, "categoria": "misto",
            "indirizzo": "", "fonte": "happings.com", "url_fonte": url,
            "ricorrenza_testo": "settimanale - mercoledì", "orario_testo": "",
            "date": ["2026-10-21"], "date_quality": "prevista",
            "aggiornato_il": "2026-06-05", "verificato_il": "",
            "lat": None, "lng": None, "position_quality": "sconosciuta",
            "status": "non_confermato", "fonti": []}


def html(*, canonical=TRIESTE_PAGE, province="Trieste", cities=("Trieste",), heading=True):
    title = f"<h2>Mercati settimanali nei comuni in provincia di {province}</h2>" if heading else ""
    canonical_link = f'<link rel="canonical" href="{canonical}">' if canonical else ""
    rows = "".join(f"<li>a {city}, in Piazza del Mercato (la mattina)</li>" for city in cities)
    return (f'<!doctype html><html><head>{canonical_link}</head><body>{title}'
            f'<div class="happings-seo-content"><h3>Mercati del mercoledì nei comuni di {province}</h3>'
            f'<ul>{rows}</ul></div><footer>Documento sintetico per test automatico; '
            'non costituisce una acquisizione della fonte.</footer></body></html>').encode()


def response(url, *, body=None, status=200, location=None):
    return {"requested_url": url, "final_url": url, "status_code": status,
            "location": location, "html": body}


def robots(text="User-agent: *\nDisallow:\n"):
    result = RobotFileParser()
    result.parse(text.splitlines())
    return result


def acquire(base, *, state=None, today=TODAY, **kwargs):
    return legacy.acquire(base, legacy.seed_state(base, state=state, today=today),
                          today=today, robots=kwargs.pop("robots", robots()),
                          sleep=kwargs.pop("sleep", lambda delay: None),
                          clock=kwargs.pop("clock", lambda: datetime.combine(today, datetime.min.time(), timezone.utc)),
                          **kwargs)


class LegacyResolverTests(unittest.TestCase):
    def test_observed_canonical_is_not_claimed_as_http_redirect(self):
        base = [market()]
        before = copy.deepcopy(base)
        state, report, captures = acquire(base, fetcher=Mock(return_value=response(TRIESTE, body=html())))
        self.assertEqual(base, before)
        self.assertEqual(report["requests_attempted"], 1)
        self.assertEqual(state["resources"][0]["redirects"], [])
        proof = state["resources"][0]["proof"]
        self.assertEqual(proof["requested_url"], TRIESTE)
        self.assertEqual(proof["final_url"], TRIESTE)
        self.assertEqual(proof["canonical_url"], TRIESTE_PAGE)
        self.assertEqual(captures[0]["html"], html())
        resources = legacy.known_resources(state, base, today=TODAY)
        self.assertEqual(source.catalog_page_routes(base), {})
        self.assertEqual(source.catalog_page_routes(base, resource_urls=resources), {base[0]["slug"]: TRIESTE_PAGE})
        updated, evidence = source.preview(base, [{"requested_url": TRIESTE_PAGE, "final_url": TRIESTE_PAGE,
                                                  "html": html()}], today=TODAY, apply=True, rights_verified=True)
        self.assertEqual(updated[0]["indirizzo"], "Piazza del Mercato")
        self.assertEqual(updated[0]["url_fonte"], TRIESTE)
        self.assertEqual(updated[0]["verificato_il"], "")
        self.assertEqual(updated[0]["date"], base[0]["date"])
        self.assertTrue(source.safe_report(evidence, base))

    def test_each_real_redirect_uses_a_slot_and_resumes_target_next_day(self):
        first_fetch = Mock(return_value=response(TRIESTE, status=301, location=TRIESTE_PAGE))
        first, report, captures = acquire([market()], max_requests=1, fetcher=first_fetch)
        self.assertEqual(report["requests_attempted"], 1)
        self.assertEqual(report["budget_stop"], "request_budget")
        self.assertEqual(captures, [])
        self.assertEqual(first["resources"][0]["next_url"], TRIESTE_PAGE)
        self.assertIsNone(first["resources"][0]["last_success_on"])
        second_fetch = Mock(return_value=response(TRIESTE_PAGE, body=html()))
        second, report, _ = acquire([market()], state=first, today=TODAY + timedelta(days=1), fetcher=second_fetch)
        self.assertEqual(second_fetch.call_args.args, (TRIESTE_PAGE,))
        self.assertEqual(len(second["resources"][0]["redirects"]), 1)
        self.assertEqual(second["resources"][0]["proof"]["requested_url"], TRIESTE_PAGE)
        self.assertEqual(report["requests_attempted"], 1)

    def test_original_and_redirect_can_complete_with_two_bounded_requests(self):
        fetcher = Mock(side_effect=[response(TRIESTE, status=302, location=TRIESTE_PAGE),
                                   response(TRIESTE_PAGE, body=html())])
        state, report, _ = acquire([market()], fetcher=fetcher)
        self.assertEqual(report["requests_attempted"], 2)
        self.assertEqual(state["resources"][0]["status"], "resolved")
        self.assertEqual([call.args[0] for call in fetcher.call_args_list], [TRIESTE, TRIESTE_PAGE])

    def test_two_observed_redirects_continue_to_province_body_in_next_daily_run(self):
        intermediate = "https://www.happings.com/it/mercato-settimanale-a-trieste/"
        fetcher = Mock(side_effect=[response(TRIESTE, status=301, location=intermediate),
                                   response(intermediate, status=301, location=TRIESTE_PAGE)])
        first, report, captures = acquire([market()], fetcher=fetcher)
        self.assertEqual(report["requests_attempted"], 2)
        self.assertEqual(captures, [])
        self.assertEqual(first["resources"][0]["next_url"], TRIESTE_PAGE)
        self.assertEqual(first["resources"][0]["status"], "redirect_observed")
        next_fetch = Mock(return_value=response(TRIESTE_PAGE, body=html()))
        second, report, _ = acquire([market()], state=first, today=TODAY + timedelta(days=1), fetcher=next_fetch)
        next_fetch.assert_called_once()
        self.assertEqual(next_fetch.call_args.args[0], TRIESTE_PAGE)
        self.assertEqual(second["resources"][0]["status"], "resolved")
        self.assertEqual(len(second["resources"][0]["redirects"]), 2)

    def test_redirect_to_different_town_slug_is_held(self):
        target = "https://www.happings.com/it/mercato-settimanale-a-muggia/"
        fetcher = Mock(return_value=response(TRIESTE, status=301, location=target))
        state, _, _ = acquire([market()], fetcher=fetcher)
        fetcher.assert_called_once()
        self.assertEqual(state["resources"][0]["status"], "unreviewed_target")

    def test_one_proved_province_covers_other_exact_town_links(self):
        base = [market("cormons", city="Cormons", province="GO",
                       url="https://www.happings.com/it/mercato-settimanale-a-cormons.html"),
                market("gorizia", city="Gorizia", province="GO",
                       url="https://www.happings.com/it/mercato-settimanale-a-gorizia.html")]
        fetcher = Mock(side_effect=lambda url, **kwargs: response(url, body=html(
            canonical=GORIZIA_PAGE, province="Gorizia", cities=("Cormons", "Gorizia"))))
        state, report, _ = acquire(base, fetcher=fetcher)
        self.assertEqual(fetcher.call_count, 1)
        self.assertEqual(report["requests_attempted"], 1)
        self.assertEqual(legacy.pending_origins(state, base, today=TODAY), [])
        self.assertEqual(set(source.catalog_page_routes(base, resource_urls=report["new_resources"])), {"cormons", "gorizia"})

    def test_malformed_town_identity_is_not_repaired_by_broad_province_page(self):
        origin = "https://www.happings.com/it/mercato-settimanale-a-citt---sant-angelo.html"
        page = "https://www.happings.com/it/mercati-settimanali-a-pescara-e-provincia/"
        base = [market("ambiguous-slug", city="Città Sant'Angelo", province="PE", region="Abruzzo", url=origin)]
        raw = html(canonical=page, province="Pescara", cities=("Città Sant'Angelo",))
        state, report, _ = acquire(base, fetcher=Mock(return_value=response(origin, body=raw)))
        self.assertEqual(report["new_resources"], [page])
        self.assertFalse(source._town_url_matches(base[0]))
        self.assertEqual(source.catalog_page_routes(base, resource_urls=[page]), {})
        updated, evidence = source.preview(base, [{"requested_url": page, "final_url": page, "html": raw}],
                                          today=TODAY, apply=True, rights_verified=True)
        self.assertEqual(updated, base)
        self.assertEqual(evidence["record_changes"], 0)

    def test_scope_and_explicit_city_weekday_are_required(self):
        for raw, status in (
            (html(heading=False), "scope_mismatch"),
            (html(province="Gorizia"), "scope_mismatch"),
            (html(cities=("Muggia",)), "source_city_day_absent"),
            (html().replace(b"mercoled\xc3\xac", b"gioved\xc3\xac"), "source_city_day_absent"),
            (html(canonical="https://evil.example/it/mercati-settimanali-a-trieste-e-provincia/"), "scope_mismatch"),
        ):
            with self.subTest(status=status, raw=raw[:80]):
                state, report, captures = acquire([market()], fetcher=Mock(return_value=response(TRIESTE, body=raw)))
                self.assertEqual(state["resources"][0]["status"], status)
                self.assertIsNone(state["resources"][0]["last_success_on"])
                self.assertEqual(report["new_resources"], [])
                self.assertEqual(captures, [])

    def test_cross_scope_and_private_query_redirects_are_never_followed(self):
        for target in (GORIZIA_PAGE, "http://www.happings.com/it/mercati-settimanali-a-trieste.html",
                       "https://127.0.0.1/", TRIESTE_PAGE + "?page=1", "https://www.happings.com/private"):
            with self.subTest(target=target):
                fetcher = Mock(return_value=response(TRIESTE, status=301, location=target))
                state, report, _ = acquire([market()], fetcher=fetcher)
                self.assertEqual(fetcher.call_count, 1)
                self.assertEqual(state["resources"][0]["status"], "unreviewed_target")
                self.assertEqual(report["new_resources"], [])

    def test_unavailable_preserves_success_timestamps_and_rotates_to_other_origins(self):
        base = [market(), market("gorizia", city="Gorizia", province="GO",
                                url="https://www.happings.com/it/mercato-settimanale-a-gorizia.html")]
        fetcher = Mock(side_effect=lambda url, **kwargs: response(url, status=404))
        state, report, _ = acquire(base, fetcher=fetcher)
        self.assertEqual(report["requests_attempted"], 2)
        self.assertTrue(all(item["last_success_on"] is None for item in state["resources"]))
        again = Mock()
        after, report, _ = acquire(base, state=state, today=TODAY + timedelta(days=1), fetcher=again)
        again.assert_not_called()
        self.assertEqual(after, state)
        self.assertEqual(report["requests_attempted"], 0)

    def test_only_observed_catalog_urls_enter_queue_and_missing_geography_is_held(self):
        base = [market(), market("query", url=TRIESTE + "?id=2"),
                market("invented", city="Missing Town"), market("wrong-province", province="GO"),
                market("private", url="https://127.0.0.1/it/mercato-settimanale-a-trieste.html")]
        state = legacy.seed_state(base, today=TODAY)
        self.assertEqual([item["origin_url"] for item in state["resources"]], [TRIESTE])
        self.assertEqual(legacy.known_resources(state, base, today=TODAY), [])

    def test_request_deadline_and_robots_delays_are_not_evaded(self):
        fetcher = Mock()
        delay = Mock()
        initial = legacy.seed_state([market()], today=TODAY)
        state, report, _ = acquire([market()], state=initial, max_seconds=3, fetcher=fetcher, sleep=delay)
        self.assertEqual(report["budget_stop"], "elapsed_deadline")
        self.assertEqual(state, initial)
        fetcher.assert_not_called()
        delay.assert_not_called()
        paced = Mock()
        acquire([market()], fetcher=Mock(return_value=response(TRIESTE, body=html())), sleep=paced,
                robots=robots("User-agent: *\nCrawl-delay: 8\nDisallow:\n"))
        paced.assert_called_once_with(8)

    def test_robots_denial_spends_bounded_slot_but_makes_no_http_request(self):
        fetcher = Mock()
        state, report, _ = acquire([market()], robots=robots("User-agent: *\nDisallow: /it/\n"), fetcher=fetcher)
        fetcher.assert_not_called()
        self.assertEqual(report["requests_attempted"], 0)
        self.assertEqual(report["request_slots_used"], 1)
        self.assertEqual(state["resources"][0]["status"], "robots_disallowed")

    def test_live_clock_cannot_relabel_old_capture_day(self):
        fetcher = Mock()
        with self.assertRaisesRegex(ValueError, "actual UTC"):
            acquire([market()], fetcher=fetcher,
                    clock=lambda: datetime(2026, 10, 21, tzinfo=timezone.utc))
        fetcher.assert_not_called()

    def test_transport_uses_same_dns_guard_and_has_no_automatic_redirect(self):
        with patch.object(source, "_public_dns", side_effect=ValueError("private address")), \
                patch.object(legacy, "build_opener") as opener:
            with self.assertRaisesRegex(ValueError, "private address"):
                legacy.fetch_one(TRIESTE)
            opener.assert_not_called()
        self.assertIsNone(legacy._NoRedirect().redirect_request(None, None, 301, None, None, TRIESTE_PAGE))

    def test_state_cannot_forge_new_host_redirect_or_success(self):
        state, _, _ = acquire([market()], fetcher=Mock(return_value=response(TRIESTE, body=html())))
        for change in (lambda item: item.update(next_url=TRIESTE_PAGE),
                       lambda item: item["proof"].update(resource_url="https://evil.example/"),
                       lambda item: item.update(last_success_on="2026-10-21"),
                       lambda item: item.update(proof=None)):
            forged = copy.deepcopy(state)
            change(forged["resources"][0])
            with self.assertRaises(ValueError):
                legacy.validate_state(forged, today=TODAY)


class LegacyAutopilotTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.rights = self.root / "rights.json"
        self.rights.write_text(json.dumps({"schema": 1, "publisher": "Girolamo srls (Happings)",
                                          "documents_copied_to_github": False,
                                          "republication_rights_authenticated": True}), "utf-8")
        self.fetcher = Mock(return_value=response(TRIESTE, body=html()))
        self.base = [market()]
        self.policy = {"enabled": True, "max_pages": 2, "legacy_resolution": {"enabled": True}}
        self.real_acquire = legacy.acquire

    def run_phase(self, **changes):
        arguments = {"policy": self.policy, "out": self.root / "out", "today": TODAY,
                     "baseline_signature": "test-base", "pipeline_policy_digest": "test-policy",
                     "rights_path": self.rights, "legacy_fetcher": self.fetcher,
                     "fetcher": lambda urls, **kwargs: [{"requested_url": url, "final_url": url, "html": html()}
                                                        for url in urls]}
        arguments.update(changes)

        def timed_acquire(*args, **kwargs):
            return self.real_acquire(*args, **kwargs, sleep=lambda delay: None,
                                     clock=lambda: datetime(2026, 10, 20, tzinfo=timezone.utc))

        with patch.object(legacy, "acquire", side_effect=timed_acquire), \
                patch.object(source, "robots_allowed", return_value=robots()):
            return phase.run(self.base, **arguments)

    def test_budget_is_shared_and_all_fields_still_have_weekly_page_proof(self):
        updated, report, protected = self.run_phase()
        self.assertEqual(report["legacy_request_slots_used"], 1)
        self.assertEqual(report["remaining_index_page_budget"], 1)
        self.assertEqual(report["selected_urls"], [TRIESTE_PAGE])
        self.assertEqual(updated[0]["indirizzo"], "Piazza del Mercato")
        self.assertEqual(protected, {self.base[0]["slug"]})
        self.assertTrue(phase.verify_changes(self.base, updated, report))
        proof = report["evidence"]["observations"][0]
        self.assertEqual(proof["source_requested_url"], TRIESTE_PAGE)
        self.assertNotEqual(proof["source_requested_url"], TRIESTE)
        forged = copy.deepcopy(report)
        forged["legacy_request_slots_used"] = 2
        with self.assertRaisesRegex(ValueError, "shared Happings"):
            phase.verify_changes(self.base, updated, forged)

    def test_checkpoint_resume_replays_raw_resource_proof_without_network(self):
        first, report, _ = self.run_phase()
        self.fetcher.reset_mock()
        resumed, repeated, _ = self.run_phase(resume=True)
        self.fetcher.assert_not_called()
        self.assertEqual(resumed, first)
        self.assertEqual(repeated["legacy_resolution"]["status"], "resumed_checkpoint")
        self.assertEqual(repeated["evidence"], report["evidence"])

    def test_checkpoint_tampered_source_body_is_rejected(self):
        self.run_phase()
        path = self.root / "out/sources/happings-legacy-pages.json"
        saved = json.loads(path.read_text("utf-8"))
        saved["captures"][0]["html_base64"] = base64.b64encode(html(cities=("Muggia",))).decode()
        path.write_text(json.dumps(saved), "utf-8")
        with self.assertRaisesRegex(ValueError, "captured HTML"):
            self.run_phase(resume=True)

    def test_bounded_weekly_error_code_survives_partial_checkpoint_and_resume(self):
        def fail(urls, *, failures, **kwargs):
            failures.extend({"requested_url": url, "error_type": "ValueError",
                             "error_code": "response_mime_changed"} for url in urls)
            return []
        updated, first, _ = self.run_phase(fetcher=fail)
        self.assertEqual(updated, self.base)
        self.assertEqual(first["page_failures"][0]["error_code"], "response_mime_changed")
        _, resumed, _ = self.run_phase(resume=True)
        self.assertEqual(resumed["page_failures"], first["page_failures"])
        path = self.root / "out/sources/happings-pages.json"
        saved = json.loads(path.read_text())
        saved["failures"][0]["error_code"] = "untrusted remote exception text"
        path.write_text(json.dumps(saved), "utf-8")
        with self.assertRaisesRegex(ValueError, "failed page identity"):
            self.run_phase(resume=True)

    def test_interrupted_request_is_not_resumed_as_a_success(self):
        self.fetcher.side_effect = KeyboardInterrupt
        with self.assertRaises(KeyboardInterrupt):
            self.run_phase()
        self.fetcher.side_effect = AssertionError("resume must not access network")
        updated, report, _ = self.run_phase(resume=True)
        self.assertEqual(updated, self.base)
        self.assertEqual(report["legacy_resolution"]["available_resource_urls"], [])
        self.assertEqual(report["legacy_resolution"]["acquisition"]["outcomes"][0]["outcome"], "interrupted")

    def test_offline_and_missing_evidence_do_not_resolve_or_fetch(self):
        for changes, status in (({"offline": True}, "offline_skipped"),
                                ({"resume": True}, "resume_missing_evidence")):
            with self.subTest(changes=changes):
                updated, report, _ = self.run_phase(**changes)
                self.assertEqual(updated, self.base)
                self.assertEqual(report["legacy_resolution"]["status"], status)
        self.fetcher.assert_not_called()

    def test_existing_publisher_keeps_state_only_queue_progress(self):
        base_path = self.root / "public/data/v1"
        # A still-future forecast without publisher-age proof is retained,
        # never renewed. This isolates a real state-only publication.
        self.base[0]["date"] = ["2027-01-27"]
        export(self.base, base_path, today=TODAY)
        baseline_signature = json.loads((base_path / "manifest.json").read_text())["content_signature"]
        policy = pipeline_policy()
        policy["happings_enrichment"] = self.policy
        policy_path = self.root / "policy.json"
        policy_path.write_text(json.dumps(policy), "utf-8")
        args = Namespace(manifest=base_path / "manifest.json", policy=policy_path,
                         output=self.root / "pipeline", today=TODAY, offline=False, resume=False)

        def timed_acquire(*args, **kwargs):
            return self.real_acquire(*args, **kwargs, fetcher=lambda url, **options: response(url, status=404),
                                     sleep=lambda delay: None,
                                     clock=lambda: datetime(2026, 10, 20, tzinfo=timezone.utc))

        with patch.object(source, "RIGHTS_REVIEW_FILE", self.rights), \
                patch.object(source, "robots_allowed", return_value=robots()), \
                patch.object(legacy, "acquire", side_effect=timed_acquire), \
                patch("publisher_refresh.fetch_page", side_effect=OSError("offline fixture")):
            result = autopilot.run(args)
        candidate_root = args.output / "candidate/public/data/v1"
        self.assertTrue(result["approved"])
        self.assertTrue(result["happings_legacy_state_changed"])
        self.assertTrue(result["has_changes"])
        self.assertEqual(result["new_signature"], baseline_signature)
        state = legacy.validate_state(json.loads((candidate_root / legacy.STATE_FILENAME).read_text()), today=TODAY)
        self.assertEqual(state["resources"][0]["status"], "unavailable")
        self.assertEqual(len(load_existing(candidate_root / "manifest.json")), 1)
        manifest = json.loads((candidate_root / "manifest.json").read_text())
        autopilot.prune_old_assets(candidate_root, manifest, manifest)
        self.assertTrue((candidate_root / legacy.STATE_FILENAME).is_file())
        self.assertFalse((base_path / legacy.STATE_FILENAME).exists())


if __name__ == "__main__":
    unittest.main()
