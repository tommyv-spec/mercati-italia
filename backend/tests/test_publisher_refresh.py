import hashlib
import json
import sys
import tempfile
import unittest
from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
from http.client import IncompleteRead
from unittest.mock import Mock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from field_evidence import clean_receipts
from publisher_refresh import (catalog_resources, rotate_sources, run,
                               validate_contracts, verify_changes, verify_exported, _download)


TODAY = date(2026, 10, 19)
URL = "https://example.org/mercati/"


def contracts():
    return {"schema": 1, "publication_channel": "dev-only", "sources": [{
        "source_id": "municipal-weekly", "publisher": "Comune - fixture",
        "url": URL, "parser": "municipal-key-value-v1", "enabled": True,
        "region": "Emilia-Romagna", "province": "RA", "category": "misto",
        "market_kind": "ordinary", "cadence": "weekly",
        "content_scope": {"tag": "div", "class": "entry-content"},
        "min_rows": 1, "max_rows": 10, "min_city_blocks": 1, "max_city_blocks": 5,
    }]}


def market(slug="market-one", **values):
    return {"slug": slug, "nome": "Mercato settimanale di Alfonsine",
            "citta": "Alfonsine", "provincia": "RA", "regione": "Emilia-Romagna",
            "categoria": "misto", "indirizzo": "centro", "orario_testo": "",
            "ricorrenza_testo": "Ogni giovedì", "url_fonte": "https://legacy.example/alfonsine",
            "fonte": "Catalogo precedente", "fonti": [], "date": ["2026-10-22"],
            "date_quality": "prevista", "aggiornato_il": "2026-01-01",
            "verificato_il": "", **values}


def page(*, day=TODAY, address="Piazza Gramsci", hours="dalle 08:00 alle 13:00",
         weekday="giovedì", extra="", scope="entry-content", content_day=None):
    body = (f'<html><body><div class="{scope}"><h2>Alfonsine</h2>'
            f'<p>Quando: ogni {weekday}</p><p>Dove: {address}</p>'
            f'<p>Orari: {hours}</p>{extra}'
            f'<p>Ultimo aggiornamento: {content_day or day.isoformat()}</p>'
            '</div></body></html>').encode()
    return {"url": URL, "body": body, "read_on": day.isoformat(),
            "sha256": hashlib.sha256(body).hexdigest()}


class PublisherRefreshTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def cycle(self, rows, snapshot=None, *, day=TODAY, resume=False, offline=False,
              config=None, output="run", baseline="same-baseline", fetcher=None):
        return run(rows, config or contracts(), out=self.root / output, today=day,
                   baseline_signature=baseline, policy_digest="same-policy",
                   resume=resume, offline=offline,
                   fetcher=fetcher or Mock(return_value=snapshot or page(day=day)))

    def test_whole_page_reads_once_for_all_catalog_matches(self):
        fetch = Mock(return_value=page())
        before = [market(f"market-{i}") for i in range(150)]
        after, report, protected = self.cycle(before, fetcher=fetch)
        self.assertEqual(fetch.call_count, 1)
        self.assertEqual(report["field_changes"], 300)
        self.assertEqual(len(protected), 150)
        self.assertEqual([r["slug"] for r in before], [r["slug"] for r in after])
        self.assertEqual(before[0]["indirizzo"], "centro")
        self.assertEqual(after[0]["indirizzo"], "Piazza Gramsci")
        self.assertEqual(after[0]["date"], before[0]["date"])
        self.assertEqual(after[0]["aggiornato_il"], before[0]["aggiornato_il"])

    def test_second_source_version_updates_managed_fields_with_history(self):
        first, _, _ = self.cycle([market()])
        next_day = TODAY + timedelta(days=1)
        second, report, _ = self.cycle(first, page(day=next_day, address="Piazza Nuova",
                                                 hours="dalle 09:00 alle 14:00"),
                                         day=next_day, output="next")
        self.assertEqual(report["field_changes"], 2)
        self.assertTrue(all(c["assignment"] == "managed_update" for c in report["changes"]))
        self.assertEqual(second[0]["indirizzo"], "Piazza Nuova")
        receipt = second[0]["riscontri_campi"][0]
        self.assertEqual(set(receipt["campi_gestiti"]), {"indirizzo", "orario_testo"})
        self.assertEqual(receipt["versioni_precedenti"][0]["valori"]["indirizzo"], "Piazza Gramsci")
        self.assertEqual(receipt["riga_fonte"], first[0]["riscontri_campi"][0]["riga_fonte"])
        verify_exported(second, report, today=next_day)

    def test_noop_reread_preserves_existing_ownership(self):
        first, _, _ = self.cycle([market()])
        next_day = TODAY + timedelta(days=1)
        reread = page()
        reread["read_on"] = next_day.isoformat()
        second, report, _ = self.cycle(first, reread, day=next_day, output="reread")
        self.assertEqual(report["field_changes"], 0)
        self.assertEqual(second[0]["riscontri_campi"][0]["campi_gestiti"],
                         first[0]["riscontri_campi"][0]["campi_gestiti"])
        later = next_day + timedelta(days=1)
        third, report, _ = self.cycle(second, page(day=later, address="Piazza Nuova"),
                                     day=later, output="later")
        self.assertEqual(report["field_changes"], 1)
        self.assertEqual(third[0]["indirizzo"], "Piazza Nuova")

    def test_preexisting_equal_value_does_not_become_managed(self):
        first, _, _ = self.cycle([market(indirizzo="Piazza Gramsci")])
        receipt = first[0]["riscontri_campi"][0]
        self.assertNotIn("indirizzo", receipt["campi_gestiti"])
        next_day = TODAY + timedelta(days=1)
        second, report, _ = self.cycle(first, page(day=next_day, address="Piazza Nuova"),
                                      day=next_day, output="next")
        self.assertEqual(second[0]["indirizzo"], "Piazza Gramsci")
        self.assertTrue(any(c["field"] == "indirizzo" for c in report["conflicts"]))
        self.assertFalse(any("indirizzo" in r["valori"] for r in second[0]["riscontri_campi"]))
        self.assertTrue(report["retired_evidence"])

    def test_human_edit_and_other_market_kind_are_preserved(self):
        first, _, _ = self.cycle([market()])
        first[0]["indirizzo"] = "Via Inserita Manualmente 12"
        special = market("other-market", nome="Mercatino antiquario di Alfonsine")
        next_day = TODAY + timedelta(days=1)
        second, report, _ = self.cycle(first + [special], page(day=next_day, address="Piazza Nuova"),
                                      day=next_day, output="next")
        self.assertEqual(second[0]["indirizzo"], first[0]["indirizzo"])
        self.assertEqual(second[1], special)
        self.assertEqual(report["field_changes"], 0)

    def test_fair_and_branded_farmers_market_do_not_match_generic_city_listing(self):
        fair = market(nome="Fiera del Raccolto")
        self.assertEqual(self.cycle([fair])[0], [fair])
        config = contracts()
        config["sources"][0]["market_kind"] = "farmers"
        branded = market(nome="Mercato Campagna Amica di Alfonsine", indirizzo="")
        self.assertEqual(self.cycle([branded], config=config)[0], [branded])

    def test_address_update_cannot_keep_a_precise_point_for_a_previous_venue(self):
        first, _, _ = self.cycle([market()])
        first[0].update(lat=44.5, lng=12.0, position_quality="precisa")
        next_day = TODAY + timedelta(days=1)
        second, report, _ = self.cycle(first, page(day=next_day, address="Piazza Nuova"),
                                      day=next_day, output="next")
        self.assertEqual(second[0]["indirizzo"], first[0]["indirizzo"])
        self.assertEqual(second[0]["lat"], first[0]["lat"])
        self.assertEqual(report["field_changes"], 0)
        self.assertTrue(any(c["reason"] == "human_verification_or_precise_location_requires_review"
                            for c in report["conflicts"]))

    def test_interrupted_http_response_holds_source_without_stopping_catalog(self):
        before = [market()]
        after, report, _ = self.cycle(before, fetcher=Mock(side_effect=IncompleteRead(b"partial")))
        self.assertEqual(after, before)
        self.assertEqual(report["selected_pages"][0]["status"], "source_held")

    def test_short_content_length_response_is_not_accepted_as_a_complete_page(self):
        response = MagicMock()
        response.__enter__.return_value = response
        response.url = URL
        response.headers = {"Content-Type": "text/html", "Content-Length": "200"}
        response.read.return_value = b"<html>partial</html>"
        opener = Mock()
        opener.open.return_value = response
        with patch("publisher_refresh.socket.getaddrinfo", return_value=[(2, 1, 6, "", ("93.184.216.34", 443))]), \
                patch("publisher_refresh.build_opener", return_value=opener):
            with self.assertRaisesRegex(ValueError, "Incomplete"):
                _download(URL, 1000, "text/html")

    def test_fraction_or_duplicate_venue_blocks_city_day_join(self):
        extra = '<p>Quando: ogni giovedì</p><p>Dove: Piazza Secondaria</p>'
        before = [market()]
        after, report, _ = self.cycle(before, page(extra=extra))
        self.assertEqual(after, before)
        self.assertEqual(report["field_changes"], 0)

    def test_changed_weekday_or_seasonal_rule_is_not_rebound(self):
        first, _, _ = self.cycle([market()])
        next_day = TODAY + timedelta(days=1)
        second, report, _ = self.cycle(first, page(day=next_day, weekday="venerdì"),
                                      day=next_day, output="next")
        self.assertEqual(first, second)
        seasonal = market(ricorrenza_testo="Ogni giovedì da giugno a settembre")
        self.assertEqual(self.cycle([seasonal], output="season")[0], [seasonal])

    def test_layout_or_hash_changes_hold_source_and_keep_catalog(self):
        for snapshot in [page(scope="changed-layout"), {**page(), "sha256": "0" * 64}]:
            with self.subTest(snapshot=snapshot["sha256"]):
                before = [market()]
                after, report, _ = self.cycle(before, snapshot)
                self.assertEqual(after, before)
                self.assertIn(report["selected_pages"][0]["status"], {"source_held", "layout_changed"})

    def test_resume_uses_exact_bytes_without_network_or_new_read_date(self):
        before = [market()]
        first, _, _ = self.cycle(before)
        fetch = Mock(side_effect=AssertionError("resume must not fetch"))
        second, report, _ = self.cycle(before, resume=True, offline=True, fetcher=fetch)
        fetch.assert_not_called()
        self.assertEqual(first, second)
        self.assertEqual(report["selected_pages"][0]["read_on"], TODAY.isoformat())
        self.assertEqual(report["selected_pages"][0]["status"], "resumed_checkpoint")

    def test_missing_or_wrong_context_resume_never_refetches(self):
        fetch = Mock(side_effect=AssertionError("resume must not fetch"))
        before = [market()]
        after, report, _ = self.cycle(before, resume=True, fetcher=fetch)
        self.assertEqual(report["selected_pages"][0]["status"], "resume_missing_evidence")
        self.cycle(before)
        after, report, _ = self.cycle(before, resume=True, baseline="changed", fetcher=fetch)
        self.assertEqual(after, before)
        self.assertEqual(report["selected_pages"][0]["status"], "source_held")
        fetch.assert_not_called()

    def test_same_day_change_or_regressing_content_date_does_not_replace(self):
        first, _, _ = self.cycle([market()])
        second, report, _ = self.cycle(first, page(address="Piazza Nuova"), output="same-day")
        self.assertEqual(second[0]["indirizzo"], first[0]["indirizzo"])
        next_day = TODAY + timedelta(days=1)
        second, report, _ = self.cycle(first, page(day=next_day, address="Piazza Nuova",
                                                 content_day="2025-01-01"), day=next_day, output="old")
        self.assertEqual(second[0]["indirizzo"], first[0]["indirizzo"])

    def test_export_guard_rejects_different_page_proof_or_lost_values(self):
        before = [market()]
        after, report, _ = self.cycle(before)
        altered = deepcopy(after)
        altered[0]["riscontri_campi"][0]["sha256"] = "a" * 64
        with self.assertRaises(ValueError):
            verify_exported(altered, report, today=TODAY)
        altered = deepcopy(after)
        altered[0]["indirizzo"] = "Another place"
        with self.assertRaises(ValueError):
            verify_changes(before, altered, report, today=TODAY)

    def test_rotation_cannot_starve_same_host_pages(self):
        profile = contracts()["sources"][0]
        profiles = [{**profile, "source_id": f"page-{i:03}", "url": f"https://example.org/{i:03}"}
                    for i in range(24)]
        seen = set()
        for offset in range(6):
            selected = rotate_sources(profiles, TODAY + timedelta(days=offset))
            self.assertLessEqual(len(selected), 4)
            seen.update(p["source_id"] for p in selected)
        self.assertEqual(len(seen), len(profiles))

    def test_mixed_host_rotation_reads_every_page_once_per_bounded_cycle(self):
        profile = contracts()["sources"][0]
        profiles = [{**profile, "source_id": f"page-{i:03}",
                     "url": f"https://{'large.example' if i < 30 else str(i) + '.example'}/{i:03}"}
                    for i in range(38)]
        visits = []
        for offset in range(8):
            batch = rotate_sources(profiles, TODAY + timedelta(days=offset))
            self.assertLessEqual(len(batch), 12)
            self.assertLessEqual(sum("large.example" in p["url"] for p in batch), 4)
            visits.extend(p["source_id"] for p in batch)
        self.assertEqual(len(visits), 38)
        self.assertEqual(len(set(visits)), 38)

    def test_full_catalog_url_inventory_keeps_unknown_and_blocked_sources(self):
        rows = [market("one", url_fonte=URL), market("two", url_fonte=URL + "?utm_source=test"),
                market("three", url_fonte="https://www.happings.com/venezia.html"),
                market("four", url_fonte="https://unknown.example/mercati"), market("five", url_fonte="")]
        report = catalog_resources(rows, contracts())
        self.assertEqual(report["markets"], 5)
        self.assertEqual(report["unique_primary_urls"], 4)
        self.assertEqual(report["market_dispositions"]["publisher_layout_active"], 2)
        self.assertEqual(report["market_dispositions"]["happings_gate_not_active"], 1)
        self.assertEqual(report["market_dispositions"]["source_layout_needed"], 1)
        self.assertEqual(report["market_dispositions"]["source_url_missing"], 1)

    def test_generic_dispatcher_cannot_bypass_dedicated_happings_gate(self):
        config = contracts()
        config["sources"][0]["url"] = "https://www.happings.com/venezia.html"
        with self.assertRaisesRegex(ValueError, "dedicated authorized phase"):
            validate_contracts(config)


if __name__ == "__main__":
    unittest.main()
