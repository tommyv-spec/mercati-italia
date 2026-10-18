"""Source layout probes cannot become unauthorized bulk scrapers or market facts."""
from __future__ import annotations
import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from publisher_template_monitor import (
    TEMPLATES,MAX_TEMPLATES,inspect,safe_url,robots_allowed,survey,
    validate,markdown,
)
TODAY=date(2026,10,18)
DATES=("23 Ottobre 2026","30 Ottobre 2026","06 Novembre 2026","13 Novembre 2026")


def html_example(t):
    if t["id"]=="happings-weekly-area":
        body=(
            "<article><h1>Mercati settimanali a Milano e provincia</h1>"
            "<h2>Mercati settimanali nei comuni di Milano</h2>"
            "<h3>Mercati del mercoledì nei comuni di Milano</h3>"
            "<ul>"+"".join("<li>a Milano, in Via Roma (la mattina)</li>"
                              for _ in range(8))+"</ul>"
            "<h3>Mercati del venerdì nei comuni di Milano</h3></article>")
    elif t["id"]=="happings-event-detail":
        body=(
            "<main><h1>Mercato del venerdì mattina a Lana</h1>"
            "<p>Data 23 Ottobre 2026 · ora speciale</p>"
            "<h2>Tutte le date</h2><ul>"
            +"".join("<li>"+v+" · 07:30</li>" for v in DATES)
            +"</ul><h2>Informazioni utili</h2>"
            "<p>Organizzatore Comune di Lana.</p></main>")
    else:
        body=(
            "<html><body><h1>Mercatino antiquariato e usato di Bologna</h1>"
            "<p>Secondi sabato e domenica del mese</p><p>"
            "Luogo: piazza Santo Stefano</p><p>Organizzatore: Comune di Bologna</p>"
            "<p>Sospensioni: luglio e agosto</p><p>Prossime date: novembre 2026</p>"
            "<p>Contatto privato alice@example.com e 3291234567</p></body></html>")
    return ("<!doctype html>"+body).encode("utf-8")


class PublisherTemplateMonitorTests(unittest.TestCase):
    def test_layouts_match_three_different_real_template_structures(self):
        self.assertEqual(len(TEMPLATES),3)
        for t in TEMPLATES:
            with self.subTest(t=t["id"]):
                info=inspect(html_example(t),t)
                self.assertTrue(info["layout_valid_for_template_comparison"])
                self.assertEqual(info["missing_required_markers"],[])
                self.assertIs(info["publisher_text_persisted"],False)
                raw=json.dumps(info)
                self.assertNotIn("alice@example.com",raw)
                self.assertNotIn("Lana",raw)
                self.assertNotIn("3291234567",raw)
                self.assertNotIn("07:30",raw)

    def test_different_template_is_flagged_as_drift_not_imported(self):
        text=b"<html><h1>Generic publication</h1><p>No weekly index or market info</p></html>"
        info=inspect(text+b" "*220,TEMPLATES[0])
        self.assertFalse(info["layout_valid_for_template_comparison"])
        self.assertIn("single_market_h1",info["missing_required_markers"])
        self.assertEqual(info["importable_market_rows"],0)

    def test_allowlist_refuses_arbitrary_hosts_and_third_party_detail_urls(self):
        for t in TEMPLATES:
            self.assertTrue(safe_url(t["url"]))
            self.assertTrue(safe_url(t["robots"]))
        for url in (
            "https://www.cosedicasa.com/mercatini/another",
            "https://www.happings.com/it/mercati-settimanali-a-roma/",
            "http://www.happings.com/it/happing/mercato/",
            "https://example.org/robots.txt",
            "https://www.happings.com/robots.txt?debug=1",
            "https://www.eventiesagre.it/Mercatini_X/4321_name.html",
        ):
            with self.subTest(url=url):
                self.assertFalse(safe_url(url))

    def test_robots_respected_on_every_page(self):
        target=TEMPLATES[0]["url"]
        self.assertTrue(robots_allowed(b"User-agent: *\nAllow: /\n",target))
        self.assertFalse(robots_allowed(
            b"User-agent: *\nDisallow: /it/mercati-settimanali-a-milano-e-provincia/\n",target))
        with self.assertRaisesRegex(ValueError,"no user agents"):
            robots_allowed(b"# empty robots",target)

    def test_all_three_templates_probed_with_only_two_robots_requests(self):
        calls=[]
        def fetch(url):
            calls.append(url)
            if url.endswith("robots.txt"):
                return b"User-agent: *\nAllow: /\n"
            t=next(x for x in TEMPLATES if x["url"]==url)
            return html_example(t)
        report=survey(fetch=fetch,today=TODAY)
        self.assertTrue(validate(report))
        self.assertEqual(report["publishers_checked"],2)
        self.assertEqual(len(report["templates"]),MAX_TEMPLATES)
        self.assertEqual(len(calls),5)
        self.assertTrue(all(x["state"]=="schema_unchanged_or_sufficient" for x in report["templates"]))
        self.assertEqual(report["market_imports"],0)
        self.assertEqual(report["event_confirmations"],0)
        reporttext=json.dumps(report)+markdown(report)
        self.assertNotIn("alice@example.com",reporttext)
        self.assertNotIn("Lana",reporttext)

    def test_denied_robots_does_not_trigger_page_request(self):
        urls=[]
        def fetch(url):
            urls.append(url)
            if url.endswith("robots.txt"):
                return b"User-agent: *\nDisallow: /\n"
            raise AssertionError("Blocked origin must not be fetched")
        report=survey(fetch=fetch,today=TODAY)
        self.assertTrue(all(x["state"]=="robots_denied" for x in report["templates"]))
        self.assertEqual(len(urls),2)
        self.assertTrue(validate(report))

    def test_outage_or_markup_change_retains_unverified_report(self):
        def fetch(url):
            if url.endswith("robots.txt"):
                return b"User-agent: *\nAllow: /\n"
            return b"error "*90
        first=survey(fetch=fetch,today=TODAY)
        self.assertTrue(all(x["state"]=="schema_changed_review_required"
                            for x in first["templates"]))
        self.assertEqual(first["market_imports"],0)
        second=survey(fetch=lambda _: (_ for _ in ()).throw(OSError("network offline")),
                      previous=first,today=TODAY)
        self.assertTrue(all(x["state"]=="unavailable_or_format_review"
                            for x in second["templates"]))
        self.assertTrue(validate(second))

    def test_previous_source_fingerprint_change_is_only_a_signal(self):
        def fetch(url):
            if url.endswith("robots.txt"):
                return b"User-agent: *\nAllow: /\n"
            return html_example(next(x for x in TEMPLATES if x["url"]==url))
        old=survey(fetch=fetch,today=TODAY)
        again=survey(fetch=fetch,previous=old,today=TODAY)
        self.assertTrue(all(x["field_markers_changed_since_previous"] is False
                            for x in again["templates"]))
        self.assertEqual(again["catalog_updates"],0)

    def test_rejects_false_permissions_or_copied_source(self):
        old=survey(offline=True,today=TODAY)
        bad=copy.deepcopy(old)
        bad["source_data_copied"]=True
        with self.assertRaises(ValueError):
            validate(bad)
        bad=copy.deepcopy(old)
        bad["templates"][0]["market_catalog_updates"]=1
        with self.assertRaises(ValueError):
            validate(bad)
        with self.assertRaises(ValueError):
            survey(previous={"schema":1,"research_only":False},
                   offline=True,today=TODAY)

if __name__=="__main__":
    unittest.main()
