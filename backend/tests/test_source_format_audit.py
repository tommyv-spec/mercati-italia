"""A source review must remain traceable without claiming current market truth."""
import copy
import hashlib
import json
import tempfile
import unittest
from datetime import date
from pathlib import Path

from source_format_audit import (build_report, classify_url, code_fingerprints,
                                 inventory, render_checklist, storage_snapshot)


class SourceFormatAuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        (self.root / "reader.py").write_text("VERSION = 1\n")
        self.url = "https://www.happings.com/it/mercati-settimanali-a-milano.html"
        self.rows = [{"slug": "market-a", "nome": "Mercato A", "citta": "Milano", "provincia": "MI", "regione": "Lombardia",
                      "url_fonte": self.url, "fonte": "happings", "indirizzo": "", "orario_testo": "",
                      "ricorrenza_testo": "lunedì", "date": ["2026-10-26"]}]
        self.fmt = classify_url(self.url)
        self.ledger = {"schema_version": 1, "checkins": [{"id": "review-1", "at": "2026-10-19T20:00:00+00:00",
            "summary": "Letto il campione e confrontati i campi."}], "tasks": [{"id": "fix-1", "status": "open",
            "title": "Conservare il periodo", "acceptance": "Il periodo delimita le date della stessa identità.",
            "format_ids": [self.fmt["format_id"]]}], "formats": [{**self.fmt,
            "scope": "primary_catalog", "reviewed_at": "2026-10-19T20:00:00+00:00",
            "primary_urls_sha256": inventory(self.rows)["formats"][0]["primary_urls_sha256"],
            "samples": [{"requested_url": self.url, "state": "read", "content_reviewed": True,
                "layout": "headings with weekly market rows", "field_map": {"address": "per market row"},
                "sha256": hashlib.sha256(b"observed sample").hexdigest(), "hash_basis": "http_response_bytes",
                "bytes": 15, "http_status": 200, "acquired_at": "2026-10-19T19:00:00+00:00"}],
            "checks": {key: {"state": "done", "note": "Confronto del campione documentato."}
                       for key in ("source_sample", "field_mapping", "parser_comparison", "storage_comparison")},
            "code_sha256": code_fingerprints(["reader.py"], self.root),
            "parser_comparison_basis": "replayed_sample", "sample_catalog_urls": [self.url],
            "storage_snapshot": storage_snapshot(self.rows, [self.url]), "todo_ids": ["fix-1"]}]}

    def tearDown(self):
        self.tmp.cleanup()

    def report(self, rows=None, ledger=None, today="2026-10-20"):
        return build_report(rows if rows is not None else self.rows,
                            ledger if ledger is not None else self.ledger,
                            today=today, repo_root=self.root)

    def test_catalog_counts_include_every_id_and_distinguish_www_from_publishers(self):
        rows = self.rows + [{**self.rows[0], "slug": "market-b", "url_fonte": self.url.replace("www.", "")}]
        out = inventory(rows)
        self.assertEqual((out["catalog_records"], out["primary_url_hostnames"], out["primary_hosts"]), (2, 2, 1))
        self.assertEqual(len(out["formats"]), 1)

    def test_duplicate_market_ids_are_not_silently_dropped(self):
        with self.assertRaises(ValueError):
            inventory(self.rows * 2)

    def test_inventory_order_is_deterministic(self):
        rows = self.rows + [{**self.rows[0], "slug": "market-b", "url_fonte": "https://example.org/events/one"}]
        self.assertEqual(inventory(rows), inventory(list(reversed(rows))))

    def test_formats_keep_legacy_detail_current_detail_and_category_variants_distinct(self):
        urls = [self.url, "https://www.happings.com/it/mercati-settimanali-ad-ancona.html",
                "https://www.happings.com/it/mercato-a-lana.html",
                "https://www.happings.com/it/mercati-settimanali-a-milano-e-provincia/",
                "https://www.happings.com/it/happing/mercato-lana/"]
        self.assertEqual(len({classify_url(u)["format_id"] for u in urls}), 5)
        self.assertNotEqual(classify_url("https://eventiesagre.it/Mercatini_Vari/123_a.html")["format_id"],
                            classify_url("https://eventiesagre.it/Eventi_Fiere/123_a.html")["format_id"])

    def test_unknown_paths_and_distinct_pdf_layouts_remain_separate(self):
        urls = ["https://example.org/a", "https://example.org/b", "https://example.org/a.pdf", "https://example.org/b.pdf"]
        self.assertEqual(len({classify_url(u)["format_id"] for u in urls}), 4)

    def test_malformed_concatenated_host_and_credentials_are_flagged(self):
        self.assertEqual(classify_url("https://wwwservizi.regione.emilia-romagna.itnote.asp?anno=2026")["url_kind"],
                         "possibly_concatenated_relative_url")
        for url in ("file:///tmp/source", "https://user:password@example.org/", "https://example.org:8999/"):
            self.assertEqual(classify_url(url)["url_kind"], "invalid_source_url")

    def test_reviewed_sample_does_not_close_correction_or_claim_market_truth(self):
        report = self.report()
        item = report["formats"][0]
        self.assertEqual(item["review_status"], "reviewed_sample")
        self.assertEqual(item["open_todo_ids"], ["fix-1"])
        self.assertFalse(item["data_truth_verified"])
        self.assertFalse(item["automatic_import_enabled_by_this_audit"])
        self.assertEqual(report["summary"]["network_reads_performed"], 0)
        self.assertIn("- [ ] **fix-1", render_checklist(report))

    def test_canonical_tag_or_other_format_does_not_prove_original_format(self):
        sample = self.ledger["formats"][0]["samples"][0]
        sample["requested_url"] = "https://www.happings.com/it/happing/lana/"
        sample["canonical_url"] = self.url
        item = self.report()["formats"][0]
        self.assertEqual(item["checks"]["source_sample"]["state"], "pending")
        self.assertEqual(item["checks"]["field_mapping"]["state"], "pending")

    def test_redirect_to_different_layout_requires_documented_scope_transition(self):
        sample = self.ledger["formats"][0]["samples"][0]
        sample["observed_final_url"] = "https://www.happings.com/it/happing/lana/"
        sample["canonical_url"] = sample["observed_final_url"]
        sample["layout"] = "current individual Event detail, not historical weekly list"
        self.assertEqual(self.report()["formats"][0]["checks"]["source_sample"]["state"], "pending")
        sample["layout_transition"] = {
            "observed_format_id": classify_url(sample["observed_final_url"])["format_id"],
            "basis": "observed_http_redirect",
            "note": "The original URL resolves to a current event detail. Only the returned layout was examined."}
        self.assertEqual(self.report()["formats"][0]["checks"]["source_sample"]["state"], "done")

    def test_canonical_transition_keeps_transport_unknown(self):
        sample = self.ledger["formats"][0]["samples"][0]
        sample["canonical_url_in_html"] = "https://www.happings.com/it/mercati-settimanali-a-milano-e-provincia/"
        sample["layout_transition"] = {
            "observed_format_id": classify_url(sample["canonical_url_in_html"])["format_id"],
            "basis": "html_canonical_and_scoped_layout", "note": "Current list observed; no HTTP redirect metadata exposed."}
        item = self.report()["formats"][0]
        self.assertEqual(item["checks"]["source_sample"]["state"], "done")
        self.assertNotIn("observed_final_url", item["samples"][0])

    def test_transition_cannot_claim_a_different_observation_channel(self):
        target = "https://www.happings.com/it/happing/lana/"
        for url_key, unproven_basis in (("canonical_url_in_html", "observed_http_redirect"),
                                       ("observed_final_url", "html_canonical_and_scoped_layout")):
            ledger = copy.deepcopy(self.ledger)
            sample = ledger["formats"][0]["samples"][0]
            sample[url_key] = target
            sample["layout_transition"] = {
                "observed_format_id": classify_url(target)["format_id"],
                "basis": unproven_basis, "note": "An unproven claim about the other channel."}
            with self.subTest(channel=url_key):
                self.assertEqual(self.report(ledger=ledger)["formats"][0]["checks"]["source_sample"]["state"], "pending")

    def test_conflicting_transport_and_canonical_layouts_remain_unresolved(self):
        sample = self.ledger["formats"][0]["samples"][0]
        sample["observed_final_url"] = "https://www.happings.com/it/happing/lana/"
        sample["canonical_url_in_html"] = "https://www.happings.com/it/mercato-lana.html"
        sample["layout_transition"] = {
            "observed_format_id": classify_url(sample["observed_final_url"])["format_id"],
            "basis": "observed_http_redirect", "note": "Only the transport destination is resolved."}
        self.assertEqual(self.report()["formats"][0]["checks"]["source_sample"]["state"], "pending")

    def test_successful_http_without_content_review_or_hash_does_not_complete_read(self):
        for key, value in (("content_reviewed", False), ("sha256", "invalid"), ("bytes", 0),
                           ("http_status", 503), ("state", "http_error"), ("field_map", {})):
            ledger = copy.deepcopy(self.ledger)
            ledger["formats"][0]["samples"][0][key] = value
            with self.subTest(key=key):
                self.assertEqual(self.report(ledger=ledger)["formats"][0]["checks"]["source_sample"]["state"], "pending")

    def test_connector_text_can_be_read_without_inventing_http_status(self):
        sample = self.ledger["formats"][0]["samples"][0]
        sample.update(http_status=None, hash_basis="connector_utf8_text")
        self.assertEqual(self.report()["formats"][0]["checks"]["source_sample"]["state"], "done")
        self.assertIsNone(sample["http_status"])

    def test_new_format_automatically_gets_unchecked_work(self):
        new = {**self.rows[0], "slug": "new-market", "url_fonte": "https://another.example.org/new-format"}
        report = self.report(self.rows + [new])
        item = next(f for f in report["formats"] if f["host"] == "another.example.org")
        self.assertEqual(item["review_status"], "not_reviewed")
        self.assertEqual(len(item["pending_checks"]), 4)
        self.assertIn("new_format", item["recheck_reasons"])

    def test_new_source_url_with_same_format_requires_recheck(self):
        new = {**self.rows[0], "slug": "new-market", "url_fonte": self.url.replace("milano", "torino")}
        item = self.report(self.rows + [new])["formats"][0]
        self.assertIn("catalog_source_urls_changed", item["recheck_reasons"])

    def test_changed_parser_reopens_parser_check_without_erasing_history(self):
        (self.root / "reader.py").write_text("VERSION = 2\n")
        item = self.report()["formats"][0]
        self.assertEqual(item["checks"]["parser_comparison"]["state"], "pending")
        self.assertEqual(self.ledger["formats"][0]["checks"]["parser_comparison"]["state"], "done")

    def test_legacy_caller_review_does_not_approve_new_shared_helpers(self):
        backend = self.root / "backend"
        backend.mkdir()
        caller = backend / "export_static.py"
        caller.write_text("VERSION = 1\n")
        entry = self.ledger["formats"][0]
        entry["code_sha256"] = {"backend/export_static.py": hashlib.sha256(caller.read_bytes()).hexdigest()}
        item = self.report()["formats"][0]
        self.assertEqual(item["checks"]["parser_comparison"]["state"], "pending")
        self.assertEqual(item["checks"]["source_sample"]["state"], "done")
        self.assertEqual(entry["checks"]["parser_comparison"]["state"], "done")

    def test_changed_index_or_conflict_helper_reopens_review_without_redating_source(self):
        backend = self.root / "backend"
        backend.mkdir()
        (backend / "export_static.py").write_text("VERSION = 1\n")
        for helper in ("compact_index.py", "field_conflicts.py"):
            (backend / helper).write_text("VERSION = 1\n")
        entry = self.ledger["formats"][0]
        original_sample = copy.deepcopy(entry["samples"])
        for helper in ("compact_index.py", "field_conflicts.py"):
            with self.subTest(helper=helper):
                entry["code_sha256"] = code_fingerprints(["backend/export_static.py"], self.root)
                self.assertEqual(self.report()["formats"][0]["checks"]["parser_comparison"]["state"], "done")
                (backend / helper).write_text("VERSION = 2\n")
                item = self.report()["formats"][0]
                self.assertEqual(item["checks"]["parser_comparison"]["state"], "pending")
                self.assertIn("parser_code_changed", item["recheck_reasons"])
                self.assertEqual(entry["samples"], original_sample)

    def test_changed_sample_fields_reopen_storage_check_only(self):
        changed = [{**self.rows[0], "indirizzo": "Via Nuova"}]
        item = self.report(changed)["formats"][0]
        self.assertEqual(item["checks"]["storage_comparison"]["state"], "pending")
        self.assertEqual(item["checks"]["source_sample"]["state"], "done")

    def test_changed_geography_or_source_metadata_reopens_storage_comparison(self):
        for key, value in (("citta", "Torino"), ("regione", "Piemonte"), ("fonte_aggiornata_il", "2026-10-20"),
                           ("eccezioni_calendario", [{"date": "2026-12-25", "status": "cancelled"}])):
            with self.subTest(key=key):
                self.assertEqual(self.report([{**self.rows[0], key: value}])["formats"][0]
                                 ["checks"]["storage_comparison"]["state"], "pending")

    def test_primary_storage_comparison_requires_nonempty_matching_sample(self):
        entry = self.ledger["formats"][0]
        entry.update(sample_catalog_urls=[], storage_snapshot=storage_snapshot(self.rows, []))
        self.assertEqual(self.report()["formats"][0]["checks"]["storage_comparison"]["state"], "pending")

    def test_aging_keeps_real_capture_date_and_opens_recheck(self):
        report = self.report(today="2026-11-21")
        item = report["formats"][0]
        self.assertIn("sample_review_due", item["recheck_reasons"])
        self.assertEqual(item["samples"][0]["acquired_at"], "2026-10-19T19:00:00+00:00")

    def test_historical_dry_run_cannot_claim_later_evidence(self):
        report = self.report(today="2026-10-18")
        item = report["formats"][0]
        self.assertIn("sample_after_report_date", item["recheck_reasons"])
        self.assertIn("checkin_after_report_date", item["recheck_reasons"])
        self.assertTrue(all(c["state"] == "pending" for c in item["checks"].values()))
        self.assertEqual(report["summary"]["formats_with_documented_source_read"], 0)

    def test_secondary_attribution_is_tracked_without_counting_market_twice(self):
        rows = copy.deepcopy(self.rows)
        rows[0]["fonti"] = [{"url": "https://official.example.org/source.pdf"}]
        report = self.report(rows)
        self.assertEqual(report["catalog_records"], 1)
        self.assertEqual(len(report["auxiliary_formats"]), 1)
        self.assertEqual(report["auxiliary_formats"][0]["catalog_records"], 0)

    def test_invalid_task_and_duplicate_entry_fail_loudly(self):
        ledger = copy.deepcopy(self.ledger)
        ledger["tasks"][0]["status"] = "done"
        with self.assertRaises(ValueError):
            self.report(ledger=ledger)
        self.ledger["formats"] *= 2
        with self.assertRaises(ValueError):
            self.report()

    def test_code_fingerprints_cannot_escape_repository(self):
        for path in ("../secrets", "/tmp/secrets"):
            with self.assertRaises(ValueError):
                code_fingerprints([path], self.root)

    def test_read_only_does_not_mutate_catalog_ledger_or_access_network(self):
        before = json.dumps([self.rows, self.ledger], sort_keys=True)
        self.report()
        self.assertEqual(json.dumps([self.rows, self.ledger], sort_keys=True), before)


if __name__ == "__main__":
    unittest.main()
