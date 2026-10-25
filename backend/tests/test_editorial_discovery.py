"""Discovery of new editorial markets: index pages, bounded reads, admission, proofs.

Synthetic Eventi e Sagre pages reuse the observed-layout helper; no network.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import editorial_discovery as discovery
from editorial_calendar_scope import KEY
from export_static import normalize
from happings_detail_enrichment import combine_admission_certificates, verify_source_admission_certificate
from recurrence_refresh import refresh_record
from test_eventiesagre_detail_refresh import TODAY, URL, document, html, row

EES = "eventiesagre.it"
CDC = "cosedicasa.com"
OTHER = "https://www.eventiesagre.it/Mercatini_Filiera+Corta/67890_Mercato+Di+Altrove.html"
SEED = "https://www.eventiesagre.it/cerca/Mercatini/Filiera+Corta/mesi/reg/prov/cit/rilib"


def existing(**changes):
    """A catalog market elsewhere: Bologna's new page is not in the catalog."""
    return row(**{"slug": "mercato-di-altrove", "nome": "Mercato Di Altrove", "citta": "Rimini",
                  "provincia": "RN", "url_fonte": OTHER, **changes})


def config(**changes):
    result = discovery.configuration()
    for publisher in discovery.ORDER:
        result["publishers"][publisher].update(changes)
    return result


def observed(blob=None):
    return document(blob or html())


def exported(rows):
    return [normalize(refresh_record(r, TODAY)[0], TODAY)[0] for r in rows]


class PolicyAndIndexTests(unittest.TestCase):
    def test_reviewed_policy_is_explicit_about_rights_and_fails_closed(self):
        policy = discovery.validate_policy(publisher=EES)
        self.assertIs(policy["new_market_ids_allowed"], True)
        self.assertIs(policy["reuse_permission_verified"], False)
        for bad in ({"new_market_ids_allowed": "yes"}, {"reuse_permission_verified": True},
                    {"seed_urls": ["https://www.example.com/sitemap.xml"]}, {"max_new": 99},
                    {"category_rules": [["url", "x", "sagra"]]}, {"min_delay_seconds": 1}):
            with self.assertRaises(ValueError, msg=bad):
                discovery.validate_policy({**policy, **bad}, publisher=EES)

    def test_links_come_from_sitemaps_with_dates_or_listing_hrefs(self):
        xml = (b"<urlset><url><loc>https://www.cosedicasa.com/mercatini/a-b</loc>"
               b"<lastmod>2026-10-23T16:02:14+00:00</lastmod></url></urlset>")
        self.assertEqual(discovery.extract_links(xml, base_url="https://www.cosedicasa.com/s.xml",
                                                 index_format="sitemap_xml"),
                         [("https://www.cosedicasa.com/mercatini/a-b", "2026-10-23")])
        page = b'<a href="/Mercatini_Filiera Corta/1_X.html">x</a><a href="pag-1.htm">'
        links = discovery.extract_links(page, base_url=SEED + "/", index_format="html_links")
        self.assertIn(("https://www.eventiesagre.it/Mercatini_Filiera+Corta/1_X.html", ""), links)


class AcquisitionTests(unittest.TestCase):
    def fetcher(self, calls, pages):
        def fetch(url, **kwargs):
            calls.append((url, kwargs["accept"]))
            if url.endswith("/robots.txt"):
                return b"User-agent: *\nDisallow: /Mercatini_Vari/\n", url
            return pages[url], url
        return fetch

    def test_bounded_polite_reads_skip_catalog_pages_and_robots_denials(self):
        policy = {**discovery.validate_policy(publisher=EES), "max_candidate_reads": 2}
        listing = (f'<a href="{URL}">new</a><a href="{OTHER}">known</a>'
                   '<a href="https://www.eventiesagre.it/Mercatini_Vari/5_Y.html">denied</a>'
                   '<a href="https://www.eventiesagre.it/Eventi_Sagre/6_Z.html">sagra</a>').encode()
        calls, sleeps = [], []
        state, pages, report = discovery.acquire(
            [existing()], publisher=EES, policy=policy, previous_state=None, today=TODAY,
            fetcher=self.fetcher(calls, {**{s: listing for s in policy["seed_urls"]}, URL: html()}),
            sleep=sleeps.append, now=lambda: datetime(2026, 10, 20, 12, tzinfo=timezone.utc))
        self.assertEqual(report["status"], "completed")
        self.assertTrue(all(pause >= 2 for pause in sleeps))
        self.assertNotIn(OTHER, state["candidates"])          # already in the catalog
        self.assertNotIn("https://www.eventiesagre.it/Eventi_Sagre/6_Z.html", state["candidates"])
        self.assertEqual(state["candidates"]["https://www.eventiesagre.it/Mercatini_Vari/5_Y.html"]["status"],
                         "robots_denied")
        self.assertEqual([p["requested_url"] for p in pages], [URL])
        self.assertEqual(report["index_pages_read"], policy["max_index_requests"])
        self.assertLessEqual(report["candidates_attempted"], 2)
        # A second run the same day never re-reads what it already attempted.
        again = discovery.next_candidates(state, today=TODAY, limit=5, recheck_after_days=30)
        self.assertNotIn(URL, again)


class AdmissionTests(unittest.TestCase):
    def test_new_page_becomes_a_catalog_shaped_market_with_page_proofs(self):
        before = [existing()]
        after, report = discovery.admit(before, [observed()], today=TODAY, config=config())
        self.assertEqual(report["counts"], {"admitted": 1})
        new = after[-1]
        self.assertEqual(new["slug"], "mercato-di-bologna-bologna")
        self.assertEqual((new["fonte"], new["url_fonte"], new["citta"], new["provincia"], new["regione"]),
                         (EES, URL, "Bologna", "BO", "Emilia-Romagna"))
        self.assertEqual((new["categoria"], new["status"], new["lat"], new["verificato_il"]),
                         ("alimentare", "non_confermato", None, ""))
        self.assertEqual(new["indirizzo"], "Via della Fonte, 4")
        self.assertEqual(new[KEY]["primary_url"], URL)
        self.assertEqual(new["riscontri_campi"][0]["gestore_campi"], "eventiesagre_detail")
        shown = exported([new])[0]
        self.assertTrue(shown["date"] and shown["date_quality"] == "prevista")
        self.assertTrue(discovery.verify_admissions(before, after, report, today=TODAY, config=config())["release_safe"])
        tampered = deepcopy(after)
        tampered[-1]["nome"] = "Mercato Inventato"
        with self.assertRaises(ValueError):
            discovery.verify_admissions(before, tampered, report, today=TODAY, config=config())

    def test_holds_old_editions_duplicates_disabled_policy_and_cap(self):
        cases = {
            "past_or_archived_edition": ([existing()], html(start="01/01/2021", end="31/12/2021", archived=True)),
            "same_venue_and_calendar": ([existing(citta="Bologna", provincia="BO", indirizzo="Via della Fonte, 4",
                                                   fonte="happings.com", nome="Altro Nome")], None),
            "same_name_in_town": ([existing(citta="Bologna", provincia="BO", nome="Mercato di Bologna",
                                            ricorrenza_testo="ogni sabato")], None),
            "same_town_and_weekdays": ([existing(citta="Bologna", provincia="BO", nome="Mercato Contadino",
                                                 categoria="alimentare")], None),
            "already_in_catalog": ([existing(url_fonte=URL)], None),
        }
        for reason, (before, blob) in cases.items():
            after, report = discovery.admit(before, [observed(blob)], today=TODAY, config=config())
            self.assertEqual((after, report["outcomes"][0]["reason"]), (before, reason), reason)
        for settings, reason in (({"new_market_ids_allowed": False}, "admission_disabled"),
                                 ({"enabled": False}, "admission_disabled")):
            _, report = discovery.admit([existing()], [observed()], today=TODAY, config=config(**settings))
            self.assertEqual(report["outcomes"][0]["reason"], reason)
        capped = config()
        capped["publishers"][EES]["max_new"] = 1
        second = document(html(event_id="54321").replace(b"Bologna", b"Imola"),
                          url="https://www.eventiesagre.it/Mercatini_Filiera+Corta/54321_Mercato+Di+Imola.html")
        _, report = discovery.admit([existing()], [observed(), second], today=TODAY, config=capped)
        self.assertEqual([o["reason"] for o in report["outcomes"]], [None, "per_run_cap_reached"])


class ExportProofTests(unittest.TestCase):
    def test_exported_admission_and_shared_certificate_are_rebuilt_from_page_facts(self):
        before = [existing()]
        after, admission = discovery.admit(before, [observed()], today=TODAY, config=config())
        final = exported(after)
        report = {"schema": 1, "date": TODAY.isoformat(), "admission": admission,
                  "publishers": {p: {"status": "offline_skipped"} for p in discovery.ORDER}}
        self.assertEqual(discovery.verify_exported(final, report, today=TODAY)["admitted_ids_checked"], 1)
        certificate = combine_admission_certificates(
            None, discovery.certificate_admissions(admission, today=TODAY), today=TODAY)
        cohort, count = verify_source_admission_certificate(exported(before), final, certificate, TODAY)
        self.assertEqual((count, [r["slug"] for r in cohort]), (1, ["mercato-di-altrove"]))
        twin = dict(final[0], slug="later-twin", nome="Mercato Di Bologna", citta="Bologna", provincia="BO")
        with self.assertRaisesRegex(ValueError, "second visible card"):
            discovery.verify_exported(final + [twin], report, today=TODAY)
        changed = deepcopy(final)
        changed[-1]["citta"] = "Imola"
        with self.assertRaises(ValueError):
            discovery.verify_exported(changed, report, today=TODAY)


class OrchestrationTests(unittest.TestCase):
    def test_offline_run_reads_nothing_and_live_run_persists_a_report_bound_queue(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            args = dict(out=root / "run", state_dir=root / "previous", today=TODAY,
                        baseline_signature="base", policy_digest="policy", config=discovery.configuration())
            rows, report, ids = discovery.run([existing()], offline=True, **args)
            self.assertEqual((rows, ids, report["summary"]["network_requests"]), ([existing()], set(), 0))
            self.assertFalse(discovery.persist_states(report, out=root / "run", source_dir=root / "previous",
                                                      destination=root / "dest", today=TODAY))

            def fetch(url, **kwargs):
                if url.endswith("/robots.txt"):
                    return b"User-agent: *\nDisallow:\n", url
                if url == URL:
                    return html(), url
                if "cosedicasa" in url:
                    return b"<sitemapindex></sitemapindex>" + b" " * 100, url
                return f'<a href="{URL}">x</a>'.ljust(120).encode(), url
            rows, report, ids = discovery.run(
                [existing()], fetchers={EES: fetch, CDC: fetch}, sleep=lambda _: None,
                now=lambda: datetime(2026, 10, 20, 12, tzinfo=timezone.utc), **{**args, "out": root / "live"})
            self.assertEqual(ids, {"mercato-di-bologna-bologna"})
            self.assertEqual(report["summary"]["admitted"], 1)
            self.assertTrue(discovery.persist_states(report, out=root / "live", source_dir=root / "previous",
                                                     destination=root / "dest", today=TODAY))
            state = json.loads((root / "dest" / discovery.state_filename(EES)).read_text("utf-8"))
            self.assertNotIn(URL, state["candidates"])         # admitted: now a catalog page
            proof = discovery.verify_exported(exported(rows), report, today=TODAY, state_dir=root / "dest")
            self.assertEqual(proof["queues"][EES], "validated_report_bound")


if __name__ == "__main__":
    unittest.main()
