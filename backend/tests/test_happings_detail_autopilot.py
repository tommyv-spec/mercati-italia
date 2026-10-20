"""Source -> discovery checkpoint -> detail -> exported catalog proofs."""
import copy
import json
import sys
import tempfile
import unittest
import contextlib
import io
from argparse import Namespace
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import happings_detail_autopilot as phase
import happings_detail_discovery as discovery
from export_static import normalize, export
from merge_catalog import load_existing
from recurrence_refresh import refresh_record
from happings_autopilot import run as run_happings, verify_exported
from autopilot import prune_old_assets, run as run_autopilot
from publisher_refresh import catalog_resources

TODAY = date(2026, 10, 20)
PISA = "https://www.happings.com/it/happing/mercato-coperto-campagna-amica-di-pisa/"
LANA = "https://www.happings.com/it/happing/mercato-del-venerdi-mattina-a-lana/"
FIXTURES = Path(__file__).parent / "fixtures/happings_detail"
ROBOTS = b"User-agent: *\nDisallow:\n"
POLICY = {"enabled": True, "max_requests": 1, "admit_new": True, "max_new": 1}


def original():
    return {"slug": "pisa-weekly-other-venue", "nome": "Mercato settimanale di Pisa",
            "citta": "Pisa", "provincia": "PI", "regione": "Toscana",
            "indirizzo": "Piazza Vettovaglie", "orario_testo": "",
            "categoria": "alimentare", "date": [], "date_quality": "sconosciuta",
            "ricorrenza_testo": "settimanale - martedì", "status": "non_confermato",
            "fonte": "happings.com", "url_fonte": "https://www.happings.com/it/mercato-settimanale-a-pisa.html",
            "fonti": [], "verificato_il": "", "aggiornato_il": "",
            "lat": None, "lng": None, "position_quality": "sconosciuta"}


class HappingsDetailAutopilotTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.state_path = self.root / "previous-state.json"
        self.seed(PISA)
        self.base = [original()]
        self.fetch_calls = []

    def seed(self, *urls):
        state = discovery.seed_state(seed_urls=urls, observed_at=TODAY)
        self.state_path.write_text(json.dumps(state), "utf-8")

    def fetch(self, url, **kwargs):
        self.fetch_calls.append(url)
        name = {PISA: "pisa", LANA: "lana"}.get(url)
        if not name:
            raise OSError("No test response for this discovered page")
        return (FIXTURES / (name + ".html")).read_bytes(), url

    def execute(self, **changes):
        arguments = {"policy": POLICY, "out": self.root / "run", "today": TODAY,
                     "baseline_signature": "test-baseline", "pipeline_policy_digest": "test-policy",
                     "previous_state_path": self.state_path, "bootstrap": None,
                     "fetcher": self.fetch}
        arguments.update(changes)
        acquire = discovery.acquire
        with patch.object(phase.weekly, "_fetch_one", return_value=(ROBOTS, phase.weekly.ROBOTS)), \
                patch.object(discovery, "acquire", side_effect=lambda *a, **k: acquire(
                    *a, **k, sleep=lambda _: None,
                    clock=lambda: arguments["today"].isoformat() + "T12:00:00+00:00")):
            return phase.run(self.base, **arguments)

    def test_source_facts_survive_real_export_without_touching_other_pisa_market(self):
        before = copy.deepcopy(self.base)
        rows, report, state = self.execute()
        self.assertEqual(self.base, before)
        self.assertEqual(rows[0], before[0])
        self.assertEqual(len(rows), 2)
        market = rows[1]
        self.assertEqual(market["indirizzo"], "VIA del Chiassatello, 64/65")
        self.assertEqual(market["date_quality"], "riportata")
        self.assertEqual(len(market["date"]), 10)
        self.assertEqual(market["date"][-1], "2026-12-26")
        dest = self.root / "public/data/v1"
        export(rows, dest, TODAY, preserve_ids={r["slug"] for r in rows})
        saved = {r["slug"]: r for r in load_existing(dest / "manifest.json")}[market["slug"]]
        for key in ("calendario_fonte", "dettaglio_fonte", "date", "orario_testo", "indirizzo"):
            self.assertEqual(saved[key], market[key])
        self.assertIsNone(saved["lat"])
        self.assertFalse(saved["verificato_il"])
        self.assertEqual(state["resources"][PISA]["last_success"], TODAY.isoformat())
        self.assertEqual(report["status"], "retrieved")

    def test_resume_uses_same_bytes_without_new_requests_or_freshness(self):
        first, first_report, state = self.execute()
        self.fetch_calls.clear()
        second, report, second_state = self.execute(resume=True)
        self.assertEqual(self.fetch_calls, [])
        self.assertEqual(first, second)
        self.assertEqual(state, second_state)
        self.assertEqual(report["source_pages"], first_report["source_pages"])
        self.assertEqual(report["status"], "resumed_checkpoint")

    def test_completed_checkpoint_cannot_drop_a_successful_page(self):
        self.execute()
        path = self.root / "run/sources/happings-detail-pages.json"
        saved = json.loads(path.read_text())
        saved["pages"] = []
        path.write_text(json.dumps(saved))
        with self.assertRaisesRegex(ValueError, "lost successful source bytes"):
            self.execute(resume=True)

    def test_checkpoint_cannot_change_budget_counts_hash_or_state(self):
        self.execute()
        path = self.root / "run/sources/happings-detail-pages.json"
        original_saved = json.loads(path.read_text())
        for mutation in ("count", "hash", "state", "policy"):
            saved = copy.deepcopy(original_saved)
            if mutation == "count":
                saved["discovery"]["requests_attempted"] += 1
            elif mutation == "hash":
                saved["pages"][0]["sha256"] = "a" * 64
            elif mutation == "state":
                saved["state"]["resources"][PISA]["last_success_at"] = "2026-10-20T13:00:00+00:00"
            else:
                saved["context"]["details_policy"]["admit_new"] = False
            path.write_text(json.dumps(saved))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                self.execute(resume=True)

    def test_interrupted_second_request_keeps_first_detail_for_resume(self):
        self.seed(PISA, LANA)
        def interrupt(url, **kwargs):
            if url == LANA:
                raise KeyboardInterrupt("simulated worker interruption")
            return self.fetch(url, **kwargs)
        policy = {**POLICY, "max_requests": 2, "max_new": 2}
        with self.assertRaises(KeyboardInterrupt):
            self.execute(policy=policy, fetcher=interrupt)
        rows, report, _ = self.execute(policy=policy, resume=True)
        self.assertEqual(report["status"], "resumed_partial_checkpoint")
        self.assertEqual(len(rows), 2)
        self.assertEqual(report["source_pages"][0]["requested_url"], PISA)

    def test_transport_report_cannot_diverge_from_parsed_evidence(self):
        rows, report, _ = self.execute()
        report["source_pages"][0]["sha256"] = "a" * 64
        with self.assertRaisesRegex(ValueError, "transport evidence"):
            phase.verify_changes(self.base, rows, report, today=TODAY)

    def test_old_source_calendar_does_not_project_new_dates(self):
        rows, _, _ = self.execute()
        future = date(2027, 1, 2)
        market, reason = refresh_record(rows[1], future)
        self.assertEqual(reason, "explicit_source_calendar_preserved")
        self.assertEqual(market["date"], [])
        self.assertEqual(market["date_quality"], "sconosciuta")
        exported, error = normalize(market, future)
        self.assertIsNone(error)
        self.assertEqual(exported["date"], [])
        self.assertTrue(exported["calendario_fonte"]["occorrenze"])

    def test_invalid_calendar_is_not_exported_or_used_for_forecasts(self):
        rows, _, _ = self.execute()
        market = rows[1]
        market["calendario_fonte"]["mercato"]["citta"] = "Firenze"
        market["date_quality"] = "sconosciuta"
        market["ricorrenza_testo"] = "Ogni sabato"
        self.assertEqual(refresh_record(market, TODAY)[1], "invalid_source_calendar_held")
        self.assertEqual(normalize(market, TODAY)[1], "invalid_source_calendar")

    def test_offline_does_not_fetch_or_relabel_existing_frontier(self):
        before = json.loads(self.state_path.read_text())
        rows, report, after = self.execute(offline=True)
        self.assertEqual(self.fetch_calls, [])
        self.assertEqual(rows, self.base)
        self.assertEqual(before, after)
        self.assertEqual(report["status"], "offline_skipped")

    def test_durable_frontier_survives_asset_pruning(self):
        folder = self.root / "public/data/v1"
        folder.mkdir(parents=True)
        (folder / phase.STATE_FILENAME).write_text(self.state_path.read_text())
        (folder / "unused.json").write_text("{}")
        self.assertEqual(prune_old_assets(folder, {}, {}), 1)
        self.assertTrue((folder / phase.STATE_FILENAME).is_file())

    def test_detail_policy_requires_bounded_integer_limits(self):
        for change in ({"max_requests": 33}, {"max_requests": True}, {"max_new": 0},
                       {"admit_new": 1}, {"enabled": "true"}, {"unreviewed": True}):
            with self.subTest(change=change), self.assertRaises(ValueError):
                phase.validate_policy({**POLICY, **change})

    def test_weekly_and_detail_phase_have_one_verified_export_and_honest_coverage(self):
        acquire = discovery.acquire
        with patch.object(phase.weekly, "_fetch_one", return_value=(ROBOTS, phase.weekly.ROBOTS)), \
                patch.object(discovery, "acquire", side_effect=lambda *a, **k: acquire(
                    *a, **k, sleep=lambda _: None, clock=lambda: "2026-10-20T12:00:00+00:00")):
            rows, report, preserved = run_happings(
                self.base, policy={"enabled": True, "details": POLICY}, out=self.root / "combined",
                today=TODAY, baseline_signature="base", pipeline_policy_digest="policy",
                detail_fetcher=self.fetch, detail_state_path=self.state_path, detail_bootstrap=None)
        dest = self.root / "combined/public/data/v1"
        export(rows, dest, TODAY, preserve_ids=preserved)
        exported = load_existing(dest / "manifest.json")
        proof = verify_exported(self.base, rows, exported, report, today=TODAY)
        self.assertTrue(proof["release_safe"])
        self.assertEqual(proof["happings_ids_added"], 1)
        self.assertEqual(proof["market_ids_deleted"], 0)
        coverage = catalog_resources(exported, {"sources": []}, today=TODAY,
                                     happings_enabled=True, happings_details_enabled=True,
                                     happings_report=report)
        detail = next(r for r in coverage["resources"] if r["url"] == PISA)
        self.assertEqual(detail["mode"], "happings_event_detail")
        self.assertEqual(detail["source_read_status"], "retrieved")

    def test_full_pipeline_persists_sitemap_progress_when_catalog_is_unchanged(self):
        catalog = self.root / "full/public/data/v1"
        export(self.base, catalog, TODAY, preserve_ids={self.base[0]["slug"]})
        robots = b"User-agent: *\nDisallow:\nSitemap: https://www.happings.com/it/sitemap_index.xml\n"
        state = discovery.seed_state(robots_text=robots.decode(), observed_at=TODAY)
        (catalog / phase.STATE_FILENAME).write_text(json.dumps(state))
        policy = {"schema": 1, "sources": [],
                  "happings_enrichment": {"enabled": True, "details": POLICY},
                  "forecast": {"days": 120, "max_source_age_days": 540,
                               "min_records_with_future_date_at_plus_60_days": 0},
                  "gates": {"min_total_records": 1, "max_record_loss_fraction": 0,
                            "min_id_retention_fraction": 1, "max_new_ids_per_run": 1,
                            "max_gzip_index_bytes": 524288, "max_index_growth_fraction": 1,
                            "max_unknown_source_share_increase": 0,
                            "allow_new_confident_date_claims": False,
                            "allow_new_human_verified_claims": False},
                  "publication": {"channel": "dev-only", "production_merge": False,
                                  "require_security_audit": True, "require_mobile_smoke": True}}
        policy_path = self.root / "policy.json"
        policy_path.write_text(json.dumps(policy))
        acquire = discovery.acquire
        sitemap = (Path(__file__).parent / "fixtures/happings_sitemap_index_20261020.xml").read_bytes()
        with patch.object(phase.weekly, "_fetch_one", return_value=(robots, phase.weekly.ROBOTS)), \
                patch.object(discovery, "fetch_one", side_effect=lambda url, **kwargs: (sitemap, url)), \
                patch.object(discovery, "acquire", side_effect=lambda *a, **k: acquire(
                    *a, **k, sleep=lambda _: None, clock=lambda: "2026-10-20T12:00:00+00:00")), \
                patch("publisher_refresh.fetch_page", side_effect=OSError("fixture: no unrelated source request")), \
                contextlib.redirect_stdout(io.StringIO()):
            decision = run_autopilot(Namespace(manifest=catalog / "manifest.json", policy=policy_path,
                                              output=self.root / "full-output", today=TODAY,
                                              offline=False, resume=False))
        self.assertTrue(decision["approved"])
        self.assertEqual(decision["base_signature"], decision["new_signature"])
        self.assertTrue(decision["has_changes"])
        self.assertTrue(decision["happings_discovery_state_changed"])
        after = json.loads((self.root / "full-output/candidate/public/data/v1" / phase.STATE_FILENAME).read_text())
        self.assertGreater(len(after["resources"]), len(state["resources"]))
        self.assertEqual(after["resources"]["https://www.happings.com/it/sitemap_index.xml"]["last_success"],
                         TODAY.isoformat())


if __name__ == "__main__":
    unittest.main()
