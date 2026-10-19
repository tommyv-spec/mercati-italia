"""Network-free proofs for the opt-in Happings DEV phase and exported IDs."""
from __future__ import annotations

import base64
import copy
import json
import sys
import tempfile
import unittest
from argparse import Namespace
from datetime import date, timedelta
from http.client import IncompleteRead
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import happings_autopilot as phase
from autopilot import run as run_autopilot
from export_static import export, prepare
from merge_catalog import load_existing
from happings_weekly_layout import VENICE_OLD, VENICE_NEW

TODAY = date(2026, 10, 19)
SAMPLE = b"""<!doctype html><html lang="it"><body>
<h1>Mercati settimanali a Venezia</h1><div class="happings-seo-content">
<h3>Mercati del mercoled&#236; nei comuni di Venezia</h3><ul>
<li>a Spinea, in Villaggio dei Fiori (la mattina)</li>
<li>a Dolo, in Piazza San Valentino (la mattina)</li></ul>
<h3>Mercati del sabato nei comuni di Venezia</h3><ul>
<li>a Spinea, in Piazza Fermi (la mattina)</li></ul></div></body></html>"""


def market(slug="spinea-mercoledi", *, street="", url=VENICE_OLD):
    return {
        "slug": slug, "nome": "Mercato settimanale di Spinea", "citta": "Spinea",
        "provincia": "VE", "regione": "Veneto", "categoria": "misto",
        "indirizzo": street, "fonte": "happings.com", "url_fonte": url,
        "ricorrenza_testo": "settimanale - mercoledì", "orario_testo": "",
        "date": ["2026-10-21"], "date_quality": "prevista",
        "aggiornato_il": "2026-06-05", "verificato_il": "",
        "lat": None, "lng": None, "position_quality": "sconosciuta",
        "status": "non_confermato", "fonti": [],
    }


def pages():
    return [{"requested_url": VENICE_OLD, "final_url": VENICE_NEW, "html": SAMPLE}]


def pipeline_policy():
    return {
        "schema": 1, "sources": [], "happings_enrichment": {"enabled": True},
        "forecast": {"days": 120, "max_source_age_days": 540,
                     "min_records_with_future_date_at_plus_60_days": 1},
        "gates": {"min_total_records": 1, "max_record_loss_fraction": 0,
                  "min_id_retention_fraction": 1, "max_new_ids_per_run": 0,
                  "max_gzip_index_bytes": 524288, "max_index_growth_fraction": 20,
                  "max_unknown_source_share_increase": 0,
                  "allow_new_confident_date_claims": False,
                  "allow_new_human_verified_claims": False},
        "publication": {"channel": "dev-only", "production_merge": False,
                        "require_security_audit": True, "require_mobile_smoke": True},
    }


class HappingsAutopilotTests(unittest.TestCase):
    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.addCleanup(self.folder.cleanup)
        self.root = Path(self.folder.name)
        self.rights = self.root / "fixture-rights.json"
        self.write_rights(True)
        self.fetcher = Mock(return_value=pages())
        self.base = [market()]

    def write_rights(self, authenticated):
        self.rights.write_text(json.dumps({
            "schema": 1, "publisher": "Girolamo srls (Happings)",
            "documents_copied_to_github": False,
            "republication_rights_authenticated": authenticated,
            "fixture_only": True,
        }), "utf-8")

    def run_phase(self, **changes):
        arguments = {
            "policy": {"enabled": True}, "out": self.root / "output", "today": TODAY,
            "baseline_signature": "fixture-baseline", "pipeline_policy_digest": "fixture-policy",
            "rights_path": self.rights, "fetcher": self.fetcher,
        }
        base = changes.pop("base", self.base)
        arguments.update(changes)
        return phase.run(base, **arguments)

    def test_default_disabled_still_protects_preexisting_happings_ids(self):
        after, report, protected = self.run_phase(policy=phase.DEFAULT_POLICY)
        self.assertEqual(after, self.base)
        self.assertEqual(report["status"], "disabled")
        self.assertEqual(protected, {self.base[0]["slug"]})
        self.assertEqual(report["evidence"]["field_changes"], 0)
        self.fetcher.assert_not_called()
        self.assertFalse((self.root / "output/sources/happings-pages.json").exists())

    def test_enabled_policy_without_current_rights_is_explicitly_blocked(self):
        self.write_rights(False)
        for flags in ({}, {"offline": True}, {"resume": True}):
            with self.subTest(flags=flags):
                after, report, protected = self.run_phase(**flags)
                self.assertEqual(after, self.base)
                self.assertEqual(report["status"], "blocked_rights")
                self.assertFalse(report["rights_authenticated"])
                self.assertEqual(protected, {self.base[0]["slug"]})
        self.fetcher.assert_not_called()

    def test_invalid_or_missing_rights_record_cannot_fetch(self):
        self.rights.write_text("{}", "utf-8")
        self.assertEqual(self.run_phase()[1]["status"], "blocked_rights")
        self.rights.unlink()
        self.assertEqual(self.run_phase()[1]["status"], "blocked_rights")
        self.fetcher.assert_not_called()

    def test_source_failure_keeps_all_market_facts(self):
        self.fetcher.side_effect = OSError("source is offline")
        after, report, _ = self.run_phase()
        self.assertEqual(after, self.base)
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(report["fetch_error_type"], "OSError")
        self.assertEqual(report["evidence"]["field_changes"], 0)

    def test_truncated_http_response_is_a_source_outage_not_a_pipeline_abort(self):
        self.fetcher.side_effect = IncompleteRead(b"", 100)
        after, report, _ = self.run_phase()
        self.assertEqual(after, self.base)
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(report["fetch_error_type"], "IncompleteRead")
        self.assertEqual(report["evidence"]["field_changes"], 0)

    def test_changed_publisher_layout_has_its_own_state(self):
        invalid = b"<html><body>" + b"<p>Publisher layout changed</p>" * 15 + b"</body></html>"
        self.fetcher.return_value = [{**pages()[0], "html": invalid}]
        after, report, _ = self.run_phase()
        self.assertEqual(after, self.base)
        self.assertEqual(report["status"], "layout_changed")
        self.assertEqual(report["source_pages"][0]["status"], "layout_changed")
        self.assertEqual(report["evidence"]["field_changes"], 0)

    def test_one_changed_layout_does_not_hide_successful_other_page(self):
        modena_url = "https://www.happings.com/it/mercati-settimanali-a-modena.html"
        modena = {**market("modena-mercoledi", url=modena_url), "citta": "Modena",
                  "nome": "Mercato settimanale di Modena", "provincia": "MO",
                  "regione": "Emilia-Romagna"}
        self.base.append(modena)
        invalid = b"<html><body>" + b"<p>Publisher layout changed</p>" * 15 + b"</body></html>"
        response = {
            VENICE_OLD: {**pages()[0], "html": invalid},
            modena_url: {"requested_url": modena_url,
                         "final_url": modena_url.removesuffix(".html") + "-e-provincia/",
                         "html": SAMPLE.replace(b"Venezia", b"Modena").replace(b"Spinea", b"Modena")},
        }
        self.fetcher.side_effect = lambda urls, **kwargs: [response[url] for url in urls]
        after, report, _ = self.run_phase()
        self.assertEqual(report["status"], "partial_layout_changed")
        self.assertEqual(after[0]["indirizzo"], "")
        self.assertEqual(after[1]["indirizzo"], "Villaggio dei Fiori")
        self.assertEqual(report["evidence"]["field_changes"], 1)
        self.assertEqual({p["status"] for p in report["source_pages"]}, {"parsed", "layout_changed"})

    def test_authorized_fixture_changes_only_blank_address_and_attribution(self):
        original = copy.deepcopy(self.base)
        after, report, protected = self.run_phase()
        self.assertEqual(self.base, original)
        self.assertEqual(report["status"], "retrieved")
        self.assertEqual(report["evidence"]["field_changes"], 1)
        self.assertEqual(after[0]["indirizzo"], "Villaggio dei Fiori")
        self.assertTrue(phase.verify_changes(original, after, report))
        exported, _ = prepare(after, TODAY, preserve_ids=protected)
        proof = phase.verify_exported(original, after, exported, report, today=TODAY)
        self.assertTrue(proof["release_safe"])
        checkpoint = json.loads((self.root / "output/sources/happings-pages.json").read_text())
        self.assertEqual(base64.b64decode(checkpoint["pages"][0]["html_base64"]), SAMPLE)
        self.assertEqual(checkpoint["status"], "retrieved")

    def test_resume_replays_exact_html_without_network_even_when_offline(self):
        first, original_report, _ = self.run_phase()
        checkpoint_path = self.root / "output/sources/happings-pages.json"
        checkpoint_bytes = checkpoint_path.read_bytes()
        self.fetcher.reset_mock()
        self.fetcher.side_effect = AssertionError("resume made a new request")
        for offline in (False, True):
            after, report, _ = self.run_phase(resume=True, offline=offline)
            self.assertEqual(after, first)
            self.assertEqual(report["status"], "resumed_checkpoint")
            self.assertTrue(report["source_evidence_reused"])
            self.assertEqual(report["evidence"], original_report["evidence"])
            self.assertEqual(checkpoint_path.read_bytes(), checkpoint_bytes)
        self.fetcher.assert_not_called()

    def test_resume_missing_evidence_does_not_start_new_requests(self):
        after, report, _ = self.run_phase(resume=True)
        self.assertEqual(after, self.base)
        self.assertEqual(report["status"], "resume_missing_evidence")
        self.fetcher.assert_not_called()

    def test_offline_without_resume_preserves_checkpoint_without_reusing_it(self):
        self.run_phase()
        checkpoint_path = self.root / "output/sources/happings-pages.json"
        original_bytes = checkpoint_path.read_bytes()
        self.fetcher.reset_mock()
        after, report, _ = self.run_phase(offline=True)
        self.assertEqual(after, self.base)
        self.assertEqual(report["status"], "offline_skipped")
        self.assertEqual(checkpoint_path.read_bytes(), original_bytes)
        self.fetcher.assert_not_called()

    def test_resume_rejects_changed_baseline_policy_date_and_input(self):
        self.run_phase()
        self.fetcher.reset_mock()
        for changes in (
            {"today": TODAY + timedelta(days=1)},
            {"baseline_signature": "another-baseline"},
            {"pipeline_policy_digest": "another-policy"},
            {"base": [{**self.base[0], "descrizione": "changed source fact"}]},
        ):
            with self.subTest(changes=changes):
                with self.assertRaisesRegex(ValueError, "resume context"):
                    self.run_phase(resume=True, **changes)
        self.fetcher.assert_not_called()

    def test_revoked_rights_do_not_replay_previously_collected_pages(self):
        self.run_phase()
        checkpoint_path = self.root / "output/sources/happings-pages.json"
        original_bytes = checkpoint_path.read_bytes()
        self.write_rights(False)
        self.fetcher.reset_mock()
        after, report, _ = self.run_phase(resume=True, offline=True)
        self.assertEqual(after, self.base)
        self.assertEqual(report["status"], "blocked_rights")
        self.assertEqual(checkpoint_path.read_bytes(), original_bytes)
        self.fetcher.assert_not_called()

    def test_changed_rights_fingerprint_requires_new_run_not_old_checkpoint(self):
        self.run_phase()
        record = json.loads(self.rights.read_text())
        record["review_version"] = "another-test-fixture"
        self.rights.write_text(json.dumps(record), "utf-8")
        self.fetcher.reset_mock()
        with self.assertRaisesRegex(ValueError, "resume context"):
            self.run_phase(resume=True)
        self.fetcher.assert_not_called()

    def test_resume_rejects_tampered_html_or_receipt_hash(self):
        self.run_phase()
        checkpoint_path = self.root / "output/sources/happings-pages.json"
        original = json.loads(checkpoint_path.read_text())
        self.fetcher.reset_mock()
        for field, value in (("html_sha256", "0" * 64),
                             ("html_base64", base64.b64encode(SAMPLE + b"changed").decode())):
            bad = copy.deepcopy(original)
            bad["pages"][0][field] = value
            checkpoint_path.write_text(json.dumps(bad), "utf-8")
            with self.assertRaisesRegex(ValueError, "content hash"):
                self.run_phase(resume=True)
        self.fetcher.assert_not_called()

    def test_partial_evidence_survives_later_request_failure_and_resume(self):
        second_url = "https://www.happings.com/it/mercati-settimanali-a-modena.html"
        self.base.append({
            **market("modena-mercoledi", url=second_url),
            "nome": "Mercato settimanale di Modena", "citta": "Modena",
            "provincia": "MO", "regione": "Emilia-Romagna",
        })

        def failure_after_one(urls, *, permission_confirmed, page_fetch):
            self.assertTrue(permission_confirmed)
            self.assertEqual(len(urls), 2)
            page_fetch(urls[0])
            raise OSError("second page unavailable")

        def completed_page(url, **kwargs):
            return SAMPLE, url.removesuffix(".html") + "-e-provincia/"

        with patch.object(phase.source, "fetch_pages", side_effect=failure_after_one), \
                patch.object(phase.source, "_fetch_one", side_effect=completed_page):
            after, report, _ = self.run_phase(fetcher=None)
        self.assertEqual(after, self.base)
        self.assertEqual(report["status"], "unavailable")
        checkpoint_path = self.root / "output/sources/happings-pages.json"
        original_bytes = checkpoint_path.read_bytes()
        saved = json.loads(original_bytes)
        self.assertEqual(len(saved["pages"]), 1)
        self.assertEqual(saved["status"], "unavailable")
        self.fetcher.reset_mock()
        replay, report, _ = self.run_phase(resume=True, offline=True)
        self.assertEqual(replay, self.base)
        self.assertEqual(report["retained_partial_evidence_pages"], 1)
        self.assertEqual(checkpoint_path.read_bytes(), original_bytes)
        self.fetcher.assert_not_called()

    def test_export_prevents_newly_equal_addresses_from_deleting_either_id(self):
        self.base.append(market("second-spinea-mercoledi", street="Villaggio dei Fiori"))
        after, report, protected = self.run_phase()
        exported, stats = prepare(after, TODAY, preserve_ids=protected)
        self.assertEqual(len(exported), 2)
        self.assertEqual(stats["same_source_duplicates_merged"], 0)
        self.assertTrue(phase.verify_exported(self.base, after, exported, report, today=TODAY)["release_safe"])
        again, noop, retained = self.run_phase(base=after, policy={"enabled": False})
        repeated, _ = prepare(again, TODAY, preserve_ids=retained)
        self.assertEqual(len(repeated), 2)
        self.assertTrue(phase.verify_exported(after, again, repeated, noop, today=TODAY)["release_safe"])

    def test_final_export_guard_rejects_missing_ids_and_other_field_changes(self):
        after, report, protected = self.run_phase()
        exported, _ = prepare(after, TODAY, preserve_ids=protected)
        with self.assertRaisesRegex(ValueError, "market IDs"):
            phase.verify_exported(self.base, after, [], report, today=TODAY)
        for field, value in (("orario_testo", "08:00-13:00"), ("lat", 45.0),
                             ("fonti", []), ("completezza", 100),
                             ("date_quality", "confermata")):
            changed = copy.deepcopy(exported)
            changed[0][field] = value
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "proved fields"):
                    phase.verify_exported(self.base, after, changed, report, today=TODAY)
        altered_candidate = copy.deepcopy(after)
        altered_candidate[0]["orario_testo"] = "08:00-13:00"
        with self.assertRaisesRegex(ValueError, "Unapproved"):
            phase.verify_changes(self.base, altered_candidate, report)

    def test_happings_guard_does_not_replace_other_sources_duplicate_rules(self):
        first = {**market("weekly-a-firenze-mercoledi",street="Via Roma"),
                 "nome":"Mercato settimanale a Firenze","citta":"Firenze",
                 "regione":"Toscana","provincia":"FI","fonte":"Comune",
                 "url_fonte":"https://example.org/weekly-firenze"}
        second = {**first,"slug":"weekly-di-firenze-mercoledi",
                  "nome":"Mercato settimanale di Firenze"}
        base = [first,second]
        after, report, protected = self.run_phase(base=base,policy={"enabled":False})
        exported, stats = prepare(after,TODAY,preserve_ids=protected)
        self.assertEqual(len(exported),1)
        self.assertEqual(stats["same_source_duplicates_merged"],1)
        proof=phase.verify_exported(base,after,exported,report,today=TODAY)
        self.assertTrue(proof["release_safe"])
        self.assertEqual(proof["checked_market_ids"],0)
        self.assertEqual(proof["market_ids_deleted"],1)
        self.assertEqual(proof["happings_ids_deleted"],0)

    def test_invalid_policy_cannot_turn_on_extra_sources_or_raise_limits(self):
        for policy in ({"enabled": 1}, {"enabled": "true"},
                       {"enabled": True, "max_pages": 999}, []):
            with self.subTest(policy=policy):
                with self.assertRaisesRegex(ValueError, "policy"):
                    self.run_phase(policy=policy)
        self.fetcher.assert_not_called()

    def test_existing_autopilot_runs_phase_before_export_and_all_release_gates(self):
        base_path = self.root / "public/data/v1"
        export(self.base, base_path, today=TODAY)
        original_manifest = (base_path / "manifest.json").read_bytes()
        policy_path = self.root / "policy.json"
        policy_path.write_text(json.dumps(pipeline_policy()), "utf-8")
        args = Namespace(manifest=base_path / "manifest.json", policy=policy_path,
                         output=self.root / "autopilot-output", today=TODAY, offline=False, resume=False)
        with patch.object(phase.source, "RIGHTS_REVIEW_FILE", self.rights), \
                patch.object(phase.source, "fetch_pages", return_value=pages()):
            result = run_autopilot(args)
        self.assertTrue(result["approved"])
        self.assertEqual(result["removed_source_ids"], 0)
        self.assertEqual(result["happings_enrichment"]["field_changes"], 1)
        self.assertTrue(result["happings_enrichment"]["release_safe"])
        self.assertEqual((base_path / "manifest.json").read_bytes(), original_manifest)
        candidate = load_existing(args.output / "candidate/public/data/v1/manifest.json")
        self.assertEqual(candidate[0]["indirizzo"], "Villaggio dei Fiori")
        self.assertEqual(candidate[0]["date_quality"], "prevista")
        for path in ("checkpoints/happings_enrichment.json", "happings-enrichment.json",
                     "happings-enrichment-static-guard.json"):
            self.assertTrue((args.output / path).is_file())


if __name__ == "__main__":
    unittest.main()
