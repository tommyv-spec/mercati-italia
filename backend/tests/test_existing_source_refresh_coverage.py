"""Coverage means a reviewed route and an observed read, not present-day truth."""
import gzip
import json
import sys
import unittest
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from publisher_refresh import catalog_resources
import source_roma_d881 as roma


TODAY = date(2026, 10, 20)
CDC = "https://www.cosedicasa.com/mercatini/bologna-piazza-s-stefano"
EES = "https://www.eventiesagre.it/Mercatini_Antiquariato/1001_Mercato+Esempio.html"


def row(slug, url, **values):
    return {"slug": slug, "nome": "Mercato di esempio", "citta": "Bologna",
            "provincia": "BO", "regione": "Emilia-Romagna", "url_fonte": url,
            "indirizzo": "", "orario_testo": "", **values}


def editorial(publisher, samples=(), *, status="completed", enabled=True):
    attempts, pages, documents, outcomes, holds = [], [], [], [], []
    for sample in samples:
        url, action, slugs = sample[:3]
        final = sample[3] if len(sample) > 3 else url
        attempts.append({"url": url, "status": action,
                         "network_attempted": action != "robots_denied"})
        if action in {"retrieved", "layout_held"}:
            proof = {"requested_url": url, "final_url": final,
                     "read_on": TODAY.isoformat(), "bytes": 1234, "sha256": "a" * 64}
            if final != url:
                proof.update(redirect_observed=True, redirects=[{"from": url, "to": final, "status": 301}])
            pages.append(proof)
            if action == "layout_held":
                holds.append({"url": url, "reason": "ValueError"})
                continue
            documents.append({"read_on": TODAY.isoformat(), "parsed": {
                "schema": 1, "status": "parsed", "source": {
                    "publisher": publisher, "requested_url": url, "final_url": final,
                    "html_sha256": proof["sha256"], "bytes": proof["bytes"]}}})
            outcomes.extend({"slug": slug, "status": "unchanged"} for slug in slugs)
    return {"schema": 1, "publisher": publisher, "date": TODAY.isoformat(),
            "enabled": enabled, "status": status, "attempts": attempts,
            "source_pages": pages, "parse_holds": holds, "details_attempted": len(attempts),
            "source_pages_read": len(pages), "documents_parsed": len(documents),
            "evidence": {"schema": 1, "publisher": publisher, "date": TODAY.isoformat(),
                         "documents": documents, "outcomes": outcomes}}


def combined(*reports, roma_report=None, today=TODAY):
    return {"schema": 1, "date": today.isoformat(),
            "editorial": {report["publisher"]: report for report in reports}, "roma": roma_report}


def coverage(rows, report=None, *, today=TODAY):
    return catalog_resources(rows, {"sources": []}, today=today, existing_source_report=report)


def roma_report(*, read_day=TODAY):
    fixtures = Path(roma.__file__).parent / "tests/fixtures/roma-d881"
    snapshot = roma.make_snapshot(
        (fixtures / "metadata-2026-10-20.json").read_bytes(),
        gzip.decompress((fixtures / "mercati-rionali-agosto-2023.csv.gz").read_bytes()),
        metadata_read_at=read_day.isoformat() + "T12:00:00+00:00",
        csv_read_at=read_day.isoformat() + "T12:00:01+00:00", today=read_day)
    return {"schema": 1, "source_id": roma.SOURCE_ID, "date": TODAY.isoformat(),
            "enabled": True, "status": "retrieved", "snapshot": snapshot,
            "document": roma.parse_snapshot(snapshot, today=TODAY), "outcomes": []}


class ExistingSourceCoverageTests(unittest.TestCase):
    def test_existing_callers_keep_prior_unsupported_output(self):
        rows = [row("cdc", CDC), row("ees", EES)]
        self.assertEqual(coverage(rows), catalog_resources(rows, {"sources": []}, today=TODAY))
        self.assertEqual(coverage(rows)["market_read_statuses"], {"not_read": 2})
        self.assertNotIn("readers", coverage(rows)["resources"][0])

    def test_configured_reader_requires_exact_url_shape_not_publisher_host(self):
        rows = [row("cdc", CDC), row("ees", EES), row("other", "https://www.cosedicasa.com/notizie/x"),
                row("home", "https://www.eventiesagre.it/"), row("insecure", CDC.replace("https:", "http:"))]
        report = combined(editorial("cosedicasa.com"), editorial("eventiesagre.it"))
        result = coverage(rows, report)
        self.assertEqual(result["market_layout_statuses"], {"supported": 2, "unsupported": 3})
        self.assertEqual(result["market_read_statuses"], {"not_selected": 2, "not_read": 3})

    def test_http_read_content_hold_and_market_identity_hold_are_separate(self):
        rows = [row("a", CDC), row("b", CDC)]
        report = editorial("cosedicasa.com", [(CDC, "retrieved", ["a", "b"])])
        report["evidence"]["documents"][0]["parsed"]["status"] = "held"
        report["evidence"]["outcomes"] = [{"slug": "a", "status": "changed"}, {"slug": "b", "status": "held"}]
        result = coverage(rows, combined(report))
        self.assertEqual(result["market_read_statuses"], {"retrieved": 2})
        resource = result["resources"][0]
        self.assertEqual(resource["markets"], 2)
        self.assertEqual(resource["readers"][0]["source_content_status"], "held")
        self.assertEqual(resource["readers"][0]["market_outcome_statuses"], {"changed": 1, "held": 1})
        self.assertEqual(resource["readers"][0]["source_acquisition"]["read_on"], TODAY.isoformat())
        self.assertNotIn("individually_confirmed", result)

    def test_attempt_failures_layout_holds_and_unselected_urls_are_counted_individually(self):
        urls = [CDC + suffix for suffix in ("", "-two", "-three", "-four", "-five")]
        rows = [row(str(i), url) for i, url in enumerate(urls)]
        report = editorial("cosedicasa.com", [(urls[0], "retrieved", ["0"]),
            (urls[1], "layout_held", []), (urls[2], "unavailable", []), (urls[3], "robots_denied", [])])
        result = coverage(rows, combined(report))
        self.assertEqual(result["market_read_statuses"], {
            "retrieved": 1, "layout_held": 1, "unavailable": 1, "robots_denied": 1, "not_selected": 1})
        layout = next(r for r in result["resources"] if r["url"] == urls[1])["readers"][0]
        self.assertEqual(layout["source_content_status"], "layout_held")
        self.assertEqual(layout["market_outcome_statuses"], {"not_evaluated": 1})

    def test_read_proof_cannot_change_dates_hashes_bytes_final_url_or_outcome_identity(self):
        base = editorial("cosedicasa.com", [(CDC, "retrieved", ["a"])])
        mutations = [lambda r: r["source_pages"][0].update(read_on="2026-10-19"),
            lambda r: r["source_pages"][0].update(sha256="b" * 64),
            lambda r: r["source_pages"][0].update(bytes=1235),
            lambda r: r["source_pages"][0].update(final_url=CDC + "-another"),
            lambda r: r["evidence"]["outcomes"][0].update(slug="unknown"),
            lambda r: r.update(source_pages_read=2),
            lambda r: r["attempts"][0].update(network_attempted=False),
            lambda r: r["source_pages"].clear()]
        for edit in mutations:
            report = deepcopy(base)
            edit(report)
            with self.subTest(edit=edit):
                result = coverage([row("a", CDC)], combined(report))
                self.assertEqual(result["market_layout_statuses"], {"supported": 1})
                self.assertEqual(result["market_read_statuses"], {"not_observed": 1})
                self.assertNotIn("source_acquisition", result["resources"][0]["readers"][0])

    def test_redirect_proof_allows_cdc_slug_alias_but_never_other_publisher_or_ees_id(self):
        final = CDC + "-renamed"
        report = editorial("cosedicasa.com", [(CDC, "retrieved", ["a"], final)])
        result = coverage([row("a", CDC)], combined(report))
        self.assertEqual(result["market_read_statuses"], {"retrieved": 1})
        self.assertEqual(result["resources"][0]["readers"][0]["source_acquisition"]["final_url"], final)
        unproven = deepcopy(report)
        unproven["source_pages"][0].pop("redirects")
        self.assertEqual(coverage([row("a", CDC)], combined(unproven))["market_read_statuses"], {"not_observed": 1})
        report = editorial("eventiesagre.it", [(EES, "retrieved", ["a"], EES.replace("1001_", "1002_"))])
        self.assertEqual(coverage([row("a", EES)], combined(report))["market_read_statuses"], {"not_observed": 1})
        report = editorial("cosedicasa.com", [(CDC, "retrieved", ["a"], EES)])
        self.assertEqual(coverage([row("a", CDC)], combined(report))["market_read_statuses"], {"not_observed": 1})

    def test_disabled_offline_and_resume_are_not_relabelled_as_live_reads(self):
        for status, enabled, expected in [("disabled", False, "disabled"),
            ("offline_skipped", True, "offline_skipped"), ("resume_missing_evidence", True, "resume_missing_evidence"),
            ("robots_unavailable", True, "robots_unavailable"), ("resumed", True, "resumed_checkpoint")]:
            report = editorial("cosedicasa.com", [(CDC, "retrieved", ["a"])], status=status, enabled=enabled)
            with self.subTest(status=status):
                self.assertEqual(coverage([row("a", CDC)], combined(report))["market_read_statuses"], {expected: 1})

    def test_stale_or_wrong_publisher_report_does_not_configure_reader(self):
        report = combined(editorial("cosedicasa.com"))
        report["editorial"]["cosedicasa.com"]["publisher"] = "eventiesagre.it"
        self.assertEqual(coverage([row("a", CDC)], report)["market_layout_statuses"], {"unsupported": 1})
        report = combined(editorial("cosedicasa.com"), today=TODAY - timedelta(days=1))
        self.assertEqual(coverage([row("a", CDC)], report)["market_layout_statuses"], {"unsupported": 1})

    def test_tracking_url_cannot_inherit_same_canonical_urls_reviewed_reader(self):
        rows = [row("a", CDC), row("b", CDC + "?utm_source=x")]
        result = coverage(rows, combined(editorial("cosedicasa.com", [(CDC, "retrieved", ["a"])])))
        self.assertEqual(result["unique_primary_urls"], 1)
        self.assertEqual(result["market_layout_statuses"], {"supported": 1, "unsupported": 1})
        self.assertEqual(result["market_read_statuses"], {"retrieved": 1, "not_read": 1})
        self.assertEqual(len(result["resources"]), 2)

    def test_roma_route_requires_exact_dataset_and_valid_city_province_region(self):
        valid = row("a", roma.DATASET_PAGE, citta="Roma", provincia="RM", regione="Lazio")
        rows = [valid, {**valid, "slug": "b", "citta": "Milano"},
                {**valid, "slug": "c", "provincia": ""},
                {**valid, "slug": "d", "url_fonte": roma.DATASET_PAGE + "?utm_source=x"},
                {**valid, "slug": "e", "url_fonte": roma.DATASET_PAGE.replace("d881", "d882")}]
        report = {"schema": 1, "source_id": roma.SOURCE_ID, "date": TODAY.isoformat(),
                  "enabled": True, "status": "offline_skipped"}
        result = coverage(rows, combined(roma_report=report))
        self.assertEqual(result["market_layout_statuses"], {"supported": 1, "unsupported": 4})
        self.assertEqual(result["market_read_statuses"], {"offline_skipped": 1, "not_read": 4})

    def test_roma_read_is_reconstructed_from_csv_bytes_with_historical_date_scope(self):
        rows = [row("a", roma.DATASET_PAGE, citta="Roma", provincia="RM", regione="Lazio")]
        report = roma_report()
        report["outcomes"] = [{"market_id": "a", "status": "held", "reason": "identity_conflict"}]
        result = coverage(rows, combined(roma_report=report))
        self.assertEqual(result["market_read_statuses"], {"retrieved": 1})
        reader = result["resources"][0]["readers"][0]
        self.assertEqual(reader["source_content_status"], "parsed_historical_inventory")
        self.assertEqual(reader["source_acquisition"]["source_date_scope"], "per_row_AGGIORNATO")
        self.assertEqual(reader["market_outcome_statuses"], {"held": 1})
        self.assertEqual({r["source_updated_on"] for r in report["document"]["rows"]}, {"2021-12-31", "2023-04-30"})

    def test_roma_tampered_snapshot_or_document_does_not_count_as_read(self):
        rows = [row("a", roma.DATASET_PAGE, citta="Roma", provincia="RM", regione="Lazio")]
        base = roma_report()
        for edit in [lambda r: r["snapshot"]["csv"].update(sha256="f" * 64),
                     lambda r: r["document"]["rows"][0].update(source_updated_on=TODAY.isoformat()),
                     lambda r: r.update(outcomes=[{"market_id": "unrelated", "status": "enriched"}])]:
            report = deepcopy(base)
            edit(report)
            self.assertEqual(coverage(rows, combined(roma_report=report))["market_read_statuses"], {"not_observed": 1})

    def test_prior_roma_read_is_cached_not_a_new_read_today(self):
        rows = [row("a", roma.DATASET_PAGE, citta="Roma", provincia="RM", regione="Lazio")]
        report = roma_report(read_day=TODAY - timedelta(days=1))
        self.assertEqual(coverage(rows, combined(roma_report=report))["market_read_statuses"], {"cached_snapshot": 1})

    def test_coverage_does_not_change_catalog_or_report(self):
        rows = [row("a", CDC)]
        report = combined(editorial("cosedicasa.com", [(CDC, "retrieved", ["a"])]))
        prior = json.dumps([rows, report], sort_keys=True)
        coverage(rows, report)
        self.assertEqual(prior, json.dumps([rows, report], sort_keys=True))


if __name__ == "__main__":
    unittest.main()
