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

    def write_project_authorization(self, **changes):
        self.write_rights(False)
        record = json.loads(self.rights.read_text("utf-8"))
        record["project_authorization"] = {
            "authorized": True, "basis": "explicit_project_owner_instruction",
            "recorded_on": TODAY.isoformat(),
            "scope": ["automated_extraction", "processing", "republication"],
            "publication_channel": "dev-only", "revoked": False,
            "instruction_reference": "Synthetic test: explicit project owner instruction",
            **changes,
        }
        self.rights.write_text(json.dumps(record), "utf-8")

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

    def test_explicit_project_instruction_enables_without_claiming_authenticated_grant(self):
        self.write_project_authorization()
        after, report, protected = self.run_phase()
        self.assertEqual(after[0]["indirizzo"], "Villaggio dei Fiori")
        self.assertTrue(report["fetch_authorized"])
        self.assertFalse(report["rights_authenticated"])
        self.assertEqual(report["rights_state"], "project_owner_authorized")
        self.assertEqual(report["authorization_basis"], "explicit_project_owner_instruction")
        exported, _ = prepare(after, TODAY, preserve_ids=protected)
        self.assertTrue(phase.verify_exported(self.base, after, exported, report, today=TODAY)["release_safe"])
        for field, value in (("rights_authenticated", True),
                             ("authorization_basis", "authenticated_publisher_grant")):
            changed = copy.deepcopy(report)
            changed[field] = value
            with self.subTest(field=field):
                with self.assertRaisesRegex(ValueError, "authorization basis"):
                    phase.verify_changes(self.base, after, changed)

    def test_revoked_or_future_project_instruction_is_not_used(self):
        for changes in ({"revoked": True}, {"authorized": False},
                        {"recorded_on": (TODAY + timedelta(days=1)).isoformat()}):
            with self.subTest(changes=changes):
                self.write_project_authorization(**changes)
                after, report, _ = self.run_phase()
                self.assertEqual(after, self.base)
                self.assertFalse(report["fetch_authorized"])
                self.assertFalse(report["rights_authenticated"])
                self.assertEqual(report["status"], "blocked_rights")
        self.fetcher.assert_not_called()

    def test_source_failure_keeps_all_market_facts(self):
        self.fetcher.side_effect = OSError("source is offline")
        after, report, _ = self.run_phase()
        self.assertEqual(after, self.base)
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(report["fetch_error_type"], "OSError")
        self.assertEqual(report["evidence"]["field_changes"], 0)

    def test_unselected_or_repeated_request_is_stopped_before_network(self):
        def unselected(urls, *, permission_confirmed, page_fetch, failures):
            page_fetch("https://www.happings.com/it/mercati-settimanali-a-modena.html")

        with patch.object(phase.source, "fetch_pages", side_effect=unselected), \
                patch.object(phase.source, "_fetch_one") as request:
            after, report, _ = self.run_phase(fetcher=None)
            self.assertEqual(after, self.base)
            self.assertEqual(report["status"], "unavailable")
            request.assert_not_called()

        def repeat_failed(urls, *, permission_confirmed, page_fetch, failures):
            try:
                page_fetch(urls[0])
            except OSError:
                page_fetch(urls[0])

        with patch.object(phase.source, "fetch_pages", side_effect=repeat_failed), \
                patch.object(phase.source, "_fetch_one", side_effect=OSError("offline")) as request:
            after, report, _ = self.run_phase(fetcher=None)
            self.assertEqual(after, self.base)
            self.assertEqual(report["status"], "unavailable")
            self.assertEqual(request.call_count, 1)

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

    def test_later_cycle_refreshes_only_source_owned_address_and_exact_evidence(self):
        first, first_report, _ = self.run_phase()
        next_day = TODAY + timedelta(days=7)
        self.fetcher.return_value = [{**pages()[0], "html": SAMPLE.replace(
            b"Villaggio dei Fiori", b"Piazza Nuova") }]
        revised, report, protected = self.run_phase(base=first, today=next_day)
        self.assertEqual(revised[0]["indirizzo"], "Piazza Nuova")
        self.assertEqual(report["evidence"]["field_changes"], 1)
        self.assertEqual(report["evidence"]["proposals"][0]["old_value"], "Villaggio dei Fiori")
        self.assertEqual(report["evidence"]["proposals"][0]["assignment"], "managed_update")
        self.assertNotEqual(report["source_pages"][0]["source_html_sha256"],
                            first_report["source_pages"][0]["source_html_sha256"])
        for field in ("slug", "date", "date_quality", "orario_testo", "lat", "lng", "verificato_il"):
            self.assertEqual(revised[0][field], first[0][field])
        exported, _ = prepare(revised, next_day, preserve_ids=protected)
        self.assertTrue(phase.verify_exported(first, revised, exported, report, today=next_day)["release_safe"])

    def test_equal_existing_address_is_observed_without_acquiring_replacement_rights(self):
        self.base[0]["indirizzo"] = "Villaggio dei Fiori"
        observed, report, _ = self.run_phase()
        self.assertEqual(report["evidence"]["field_changes"], 0)
        self.assertEqual(report["evidence"]["record_changes"], 1)
        self.assertTrue(observed[0]["riscontri_campi"])
        self.fetcher.return_value = [{**pages()[0], "html": SAMPLE.replace(
            b"Villaggio dei Fiori", b"Piazza Nuova") }]
        held, subsequent, _ = self.run_phase(base=observed, today=TODAY + timedelta(days=7))
        self.assertEqual(held[0]["indirizzo"], "Villaggio dei Fiori")
        self.assertEqual(subsequent["evidence"]["field_changes"], 0)

    def test_later_outage_preserves_original_evidence_read_date(self):
        first, _, _ = self.run_phase()
        self.fetcher.side_effect = OSError("publisher currently unavailable")
        unchanged, report, protected = self.run_phase(base=first, today=TODAY + timedelta(days=7))
        self.assertEqual(unchanged, first)
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(protected, {first[0]["slug"]})
        self.assertTrue(all(receipt["letto_il"] == TODAY.isoformat()
                            for receipt in unchanged[0]["riscontri_campi"]))

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

        def failure_after_one(urls, *, permission_confirmed, page_fetch, failures):
            self.assertTrue(permission_confirmed)
            self.assertEqual(len(urls), 2)
            page_fetch(urls[0])
            raise OSError("second page unavailable")

        def completed_page(url, **kwargs):
            blob = (SAMPLE if url == VENICE_OLD else
                    SAMPLE.replace(b"Venezia", b"Modena").replace(b"Spinea", b"Modena"))
            return blob, url.removesuffix(".html") + "-e-provincia/"

        with patch.object(phase.source, "fetch_pages", side_effect=failure_after_one), \
                patch.object(phase.source, "_fetch_one", side_effect=completed_page):
            after, report, _ = self.run_phase(fetcher=None)
        self.assertEqual(sum(bool(row["indirizzo"]) for row in after), 1)
        self.assertEqual(report["status"], "partial_unavailable")
        self.assertEqual(len(report["page_failures"]), 1)
        checkpoint_path = self.root / "output/sources/happings-pages.json"
        original_bytes = checkpoint_path.read_bytes()
        saved = json.loads(original_bytes)
        self.assertEqual(len(saved["pages"]), 1)
        self.assertEqual(saved["status"], "partial_unavailable")
        self.fetcher.reset_mock()
        replay, report, _ = self.run_phase(resume=True, offline=True)
        self.assertEqual(replay, after)
        self.assertEqual(report["status"], "partial_unavailable")
        self.assertEqual(report["retained_partial_evidence_pages"], 1)
        self.assertEqual(checkpoint_path.read_bytes(), original_bytes)
        self.fetcher.assert_not_called()

    def test_failed_first_page_does_not_discard_later_page(self):
        second_url = "https://www.happings.com/it/mercati-settimanali-a-modena.html"
        self.base.append({**market("modena-mercoledi", url=second_url), "citta": "Modena",
                          "nome": "Mercato settimanale di Modena", "provincia": "MO",
                          "regione": "Emilia-Romagna"})
        selected = phase.source.select_pages(self.base, today=TODAY)
        self.assertEqual(len(selected), 2)

        def one_failure(urls, *, permission_confirmed, failures):
            self.assertTrue(permission_confirmed)
            failures.append({"requested_url": urls[0], "error_type": "HTTPError"})
            url = urls[1]
            blob = (SAMPLE if url == VENICE_OLD else
                    SAMPLE.replace(b"Venezia", b"Modena").replace(b"Spinea", b"Modena"))
            return [{"requested_url": url, "final_url": url.removesuffix(".html") + "-e-provincia/",
                     "html": blob}]

        self.fetcher.side_effect = one_failure
        after, report, protected = self.run_phase()
        self.assertEqual(report["status"], "partial_unavailable")
        self.assertEqual(sum(bool(row["indirizzo"]) for row in after), 1)
        self.assertEqual(report["page_failures"], [{"requested_url": selected[0], "error_type": "HTTPError"}])
        exported, _ = prepare(after, TODAY, preserve_ids=protected)
        self.assertTrue(phase.verify_exported(self.base, after, exported, report, today=TODAY)["release_safe"])
        self.fetcher.reset_mock()
        self.fetcher.side_effect = AssertionError("Replay must not reread a missing page")
        replay, reused, _ = self.run_phase(resume=True, offline=True)
        self.assertEqual(replay, after)
        self.assertEqual(reused["page_failures"], report["page_failures"])
        self.fetcher.assert_not_called()

    def test_missing_page_outcome_cannot_be_reported_as_complete_fetch(self):
        second_url = "https://www.happings.com/it/mercati-settimanali-a-modena.html"
        self.base.append({**market("modena-mercoledi", url=second_url), "citta": "Modena",
                          "nome": "Mercato settimanale di Modena", "provincia": "MO",
                          "regione": "Emilia-Romagna"})
        # A replacement fetcher must explicitly report every failed page.
        self.fetcher.return_value = pages()
        after, report, _ = self.run_phase()
        self.assertEqual(after, self.base)
        self.assertEqual(report["status"], "unavailable")
        self.assertEqual(len(report["page_failures"]), 2)
        self.assertEqual(report["fetch_error_type"], "ValueError")

    def test_interrupted_checkpoint_reuses_completed_bytes_without_retrying_missing_page(self):
        second_url = "https://www.happings.com/it/mercati-settimanali-a-modena.html"
        self.base.append({**market("modena-mercoledi", url=second_url), "citta": "Modena",
                          "nome": "Mercato settimanale di Modena", "provincia": "MO",
                          "regione": "Emilia-Romagna"})

        def interrupt(urls, *, permission_confirmed, page_fetch, failures):
            page_fetch(urls[0])
            raise KeyboardInterrupt("synthetic interruption before next page")

        def completed_page(url, **kwargs):
            blob = (SAMPLE if url == VENICE_OLD else
                    SAMPLE.replace(b"Venezia", b"Modena").replace(b"Spinea", b"Modena"))
            return blob, url.removesuffix(".html") + "-e-provincia/"

        with patch.object(phase.source, "fetch_pages", side_effect=interrupt), \
                patch.object(phase.source, "_fetch_one", side_effect=completed_page):
            with self.assertRaises(KeyboardInterrupt):
                self.run_phase(fetcher=None)
        path = self.root / "output/sources/happings-pages.json"
        original_bytes = path.read_bytes()
        self.assertEqual(json.loads(original_bytes)["status"], "fetch_started")
        self.fetcher.side_effect = AssertionError("Interrupted replay made a request")
        after, report, _ = self.run_phase(resume=True, offline=True)
        self.assertEqual(sum(bool(row["indirizzo"]) for row in after), 1)
        self.assertEqual(report["status"], "partial_unavailable")
        self.assertEqual(report["page_failures"][0]["error_type"], "InterruptedBatch")
        self.assertEqual(path.read_bytes(), original_bytes)
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

    def test_dropped_weekday_warning_passes_the_phase_and_export_guards(self):
        # The page lists Spinea on Wednesday and Saturday only.
        base = [{**market("spinea-lunedi"), "ricorrenza_testo": "settimanale - lunedì"}]
        after, report, protected = self.run_phase(base=base)
        self.assertEqual(report["evidence"]["weekday_conflict_ids"], ["spinea-lunedi"])
        self.assertEqual(after[0]["conflitti_campi"][0]["campo"], "ricorrenza_testo")
        self.assertTrue(phase.verify_changes(base, after, report, source_pages=pages()))
        exported, _ = prepare(after, TODAY, preserve_ids=protected)
        proof = phase.verify_exported(base, after, exported, report, today=TODAY,
                                      source_checkpoint_dir=self.root / "output")
        self.assertTrue(proof["release_safe"])
        with self.assertRaises(ValueError):
            phase.verify_exported(base, after, exported, report, today=TODAY)

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
        with self.assertRaisesRegex(ValueError, "reference date"):
            phase.verify_exported(self.base, after, exported, report, today=TODAY + timedelta(days=1))

    def test_all_original_ids_survive_export_even_when_another_source_has_equal_values(self):
        first = {**market("weekly-a-firenze-mercoledi",street="Via Roma"),
                 "nome":"Mercato settimanale a Firenze","citta":"Firenze",
                 "regione":"Toscana","provincia":"FI","fonte":"Comune",
                 "url_fonte":"https://example.org/weekly-firenze"}
        second = {**first,"slug":"weekly-di-firenze-mercoledi",
                  "nome":"Mercato settimanale di Firenze"}
        base = [first,second]
        after, report, protected = self.run_phase(base=base,policy={"enabled":False})
        exported, stats = prepare(after,TODAY,preserve_ids=protected)
        self.assertEqual(len(exported),2)
        self.assertEqual(stats["same_source_duplicates_merged"],0)
        self.assertEqual(protected,{first["slug"],second["slug"]})
        proof=phase.verify_exported(base,after,exported,report,today=TODAY)
        self.assertTrue(proof["release_safe"])
        self.assertEqual(proof["checked_market_ids"],2)
        self.assertEqual(proof["market_ids_deleted"],0)
        self.assertEqual(proof["happings_ids_deleted"],0)

    def test_secondary_corroboration_reuses_same_fetch_and_protects_both_origins(self):
        self.base[0]["indirizzo"]="Villaggio dei Fiori"
        external={**market("external-origin",street="Villaggio dei Fiori"),"fonte":"eventiesagre.it",
                  "url_fonte":"https://www.eventiesagre.it/Mercatini_Filiera+Corta/12345_Mercato.html"}
        self.base.append(external)
        after,report,protected=self.run_phase()
        self.assertEqual(self.fetcher.call_count,1)
        self.assertEqual(self.fetcher.call_args.args[0],[VENICE_OLD])
        self.assertEqual(report["protected_existing_market_ids"],1)
        self.assertEqual(report["protected_catalog_market_ids"],2)
        self.assertEqual(protected,{row["slug"] for row in self.base})
        self.assertEqual(report["evidence"]["secondary_observed_ids"],["external-origin"])
        self.assertEqual(report["evidence"]["field_changes"],0)
        for key,value in external.items():
            if key!="fonti":self.assertEqual(after[1][key],value)
        exported,_=prepare(after,TODAY,preserve_ids=protected)
        proof=phase.verify_exported(self.base,after,exported,report,today=TODAY)
        self.assertEqual(proof["checked_market_ids"],2)
        self.assertEqual(proof["secondary_observed_markets"],1)
        self.assertTrue(proof["release_safe"])

    def test_export_rejects_missing_or_mutated_other_origin_and_forged_full_catalog_identity(self):
        self.base.append({**market("external-origin",street="Villaggio dei Fiori"),"fonte":"eventiesagre.it",
                          "url_fonte":"https://www.eventiesagre.it/Mercatini_Filiera+Corta/12345_Mercato.html"})
        after,report,protected=self.run_phase()
        exported,_=prepare(after,TODAY,preserve_ids=protected)
        with self.assertRaisesRegex(ValueError,"market IDs"):
            phase.verify_exported(self.base,after,[r for r in exported if r["fonte"]=="happings.com"],report,today=TODAY)
        for key,value in (("orario_testo","07:00-13:00"),("url_fonte",VENICE_OLD),("riscontri_campi",[])):
            forged=copy.deepcopy(exported)
            next(r for r in forged if r["slug"]=="external-origin")[key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,"proved fields"):
                phase.verify_exported(self.base,after,forged,report,today=TODAY)
        forged=copy.deepcopy(after)
        forged[1]["indirizzo"]="Via Nuova"
        with self.assertRaisesRegex(ValueError,"Unapproved"):
            phase.verify_changes(self.base,forged,report)
        for key,value in (("protected_catalog_market_ids",1),("protected_catalog_ids_sha256","0"*64)):
            forged=copy.deepcopy(report)
            forged[key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,"identities"):
                phase.verify_changes(self.base,after,forged)

    def test_retirement_only_cycle_passes_exact_guard_without_changing_market_values(self):
        self.base[0]["indirizzo"]="Villaggio dei Fiori"
        self.base.append({**market("external-origin",street="Villaggio dei Fiori"),"fonte":"eventiesagre.it",
                          "url_fonte":"https://www.eventiesagre.it/Mercatini_Filiera+Corta/12345_Mercato.html"})
        first,_,_=self.run_phase()
        self.fetcher.return_value=[{**pages()[0],"html":SAMPLE.replace(b"Villaggio dei Fiori",b"Piazza Nuova")}]
        later=TODAY+timedelta(days=7)
        after,report,protected=self.run_phase(base=first,today=later)
        self.assertEqual(report["evidence"]["observed_ids"],[])
        self.assertEqual(report["evidence"]["retired_ids"],["external-origin","spinea-mercoledi"])
        self.assertEqual(report["evidence"]["record_changes"],2)
        self.assertEqual(report["evidence"]["field_changes"],0)
        for old,current in zip(first,after):
            self.assertEqual({key for key in old if old[key]!=current[key]},{"riscontri_campi"})
        exported,_=prepare(after,later,preserve_ids=protected)
        proof=phase.verify_exported(first,after,exported,report,today=later)
        self.assertTrue(proof["release_safe"])
        self.assertEqual(proof["retired_source_support_markets"],2)
        forged=copy.deepcopy(after)
        forged[1]["riscontri_campi"]=first[1]["riscontri_campi"]
        with self.assertRaisesRegex(ValueError,"Unapproved"):
            phase.verify_changes(first,forged,report)

    def test_secondary_reread_and_outage_do_not_renew_read_dates_without_source(self):
        self.base[0]["indirizzo"]="Villaggio dei Fiori"
        self.base.append({**market("external-origin",street="Villaggio dei Fiori"),"fonte":"eventiesagre.it",
                          "url_fonte":"https://www.eventiesagre.it/Mercatini_Filiera+Corta/12345_Mercato.html"})
        first,_,_=self.run_phase()
        self.fetcher.side_effect=OSError("publisher unavailable")
        after,report,protected=self.run_phase(base=first,today=TODAY+timedelta(days=7))
        self.assertEqual(after,first)
        self.assertEqual(report["evidence"]["retirements"],[])
        self.assertEqual(report["evidence"]["secondary_observed_ids"],[])
        self.assertEqual(protected,{row["slug"] for row in self.base})
        self.assertEqual(after[1]["riscontri_campi"][0]["letto_il"],TODAY.isoformat())

    def test_invalid_policy_cannot_turn_on_extra_sources_or_raise_limits(self):
        for policy in ({"enabled": 1}, {"enabled": "true"},
                       {"enabled": True, "max_pages": 999},
                       {"enabled": True, "max_pages": 0},
                       {"enabled": True, "max_pages": True}, []):
            with self.subTest(policy=policy):
                with self.assertRaisesRegex(ValueError, "policy"):
                    self.run_phase(policy=policy)
        self.fetcher.assert_not_called()

    def test_configured_smaller_budget_limits_actual_page_batch(self):
        second_url = "https://www.happings.com/it/mercati-settimanali-a-modena.html"
        self.base.append({**market("modena-mercoledi", url=second_url), "citta": "Modena",
                          "nome": "Mercato settimanale di Modena", "provincia": "MO",
                          "regione": "Emilia-Romagna"})

        def single_page(urls, **kwargs):
            self.assertEqual(len(urls), 1)
            url = urls[0]
            blob = (SAMPLE if url == VENICE_OLD else
                    SAMPLE.replace(b"Venezia", b"Modena").replace(b"Spinea", b"Modena"))
            return [{"requested_url": url, "final_url": url.removesuffix(".html") + "-e-provincia/",
                     "html": blob}]

        self.fetcher.side_effect = single_page
        after, report, _ = self.run_phase(policy={"enabled": True, "max_pages": 1})
        self.assertEqual(report["max_index_pages_per_run"], 1)
        self.assertEqual(len(report["selected_urls"]), 1)
        self.assertEqual(report["evidence"]["field_changes"], 1)
        self.assertEqual(sum(bool(row["indirizzo"]) for row in after), 1)

    def test_existing_autopilot_runs_phase_before_export_and_all_release_gates(self):
        base_path = self.root / "public/data/v1"
        # This fixture explicitly supplies publisher content age. Import time
        # alone no longer authorizes extending a market's forecast.
        self.base[0]["fonte_aggiornata_il"] = "2026-10-13"
        export(self.base, base_path, today=TODAY)
        original_manifest = (base_path / "manifest.json").read_bytes()
        policy_path = self.root / "policy.json"
        policy_path.write_text(json.dumps(pipeline_policy()), "utf-8")
        args = Namespace(manifest=base_path / "manifest.json", policy=policy_path,
                         output=self.root / "autopilot-output", today=TODAY, offline=False, resume=False)
        with patch.object(phase.source, "RIGHTS_REVIEW_FILE", self.rights), \
                patch.object(phase.source, "fetch_pages", return_value=pages()), \
                patch("publisher_refresh.fetch_page", side_effect=OSError("fixture has no live pages")):
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
