"""A live-style WordPress sitemap must enrich an old market without manual IDs."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from urllib.robotparser import RobotFileParser

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import happings_autopilot as phase

ROOT = "https://www.happings.com"
INDEX = ROOT + "/it/sitemap_index.xml"
POST = ROOT + "/post-sitemap.xml"
GO = ROOT + "/it/mercati-settimanali-a-gorizia-e-provincia/"
TOWN = ROOT + "/it/mercato-settimanale-a-gorizia.html"
DAY = date(2026, 10, 21)
CONTENT = b"""<!doctype html><html lang="it"><body>
<h1>Mercati settimanali a Gorizia</h1><div class="happings-seo-content">
<h3>Mercati del mercoled&#236; nei comuni di Gorizia</h3><ul>
<li>a Gorizia, in Piazza Vittoria (la mattina)</li></ul><p>Elenco provinciale dei mercati settimanali di Gorizia, con indicazioni dei luoghi per i visitatori e la loro consultazione.</p></div></body></html>"""


def robot():
    rp = RobotFileParser()
    rp.parse(("User-agent: *\nDisallow:\nSitemap: " + INDEX).splitlines())
    return rp


def xml(url, *, index):
    parent, element = ("sitemapindex", "sitemap") if index else ("urlset", "url")
    return ("<" + parent + "><" + element + "><loc>" + url + "</loc></"
            + element + "></" + parent + ">").encode()


def legacy_market():
    return {"slug": "happings-gorizia-mercoledi", "nome": "Mercato settimanale di Gorizia",
            "citta": "Gorizia", "provincia": "GO", "regione": "Friuli-Venezia Giulia",
            "categoria": "misto", "indirizzo": "", "fonte": "happings.com",
            "url_fonte": TOWN, "ricorrenza_testo": "settimanale - mercoledì",
            "orario_testo": "", "date": ["2026-10-28"], "date_quality": "prevista",
            "aggiornato_il": "2026-06-05", "verificato_il": "", "lat": None,
            "lng": None, "position_quality": "sconosciuta",
            "status": "non_confermato", "fonti": []}


class DirectoryAutopilotIntegrationTests(unittest.TestCase):
    def test_directory_finds_unlinked_province_and_uses_existing_field_guards(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            rights = out / "rights.json"
            rights.write_text(json.dumps({
                "schema": 1, "publisher": "Girolamo srls (Happings)",
                "documents_copied_to_github": False,
                "republication_rights_authenticated": True, "fixture_only": True,
            }), "utf-8")
            requested_xml = []
            requested_page = []

            def directory_fetch(url, *, robots):
                requested_xml.append(url)
                if url == ROOT+"/it/":
                    return b'<html><body><a href="/it/categoria-evento/mercati/">Mercati</a></body></html>', url
                return (xml(POST, index=True) if url == INDEX
                        else xml(GO, index=False)), url

            def weekly_fetch(urls, *, permission_confirmed, failures):
                requested_page.extend(urls)
                return [{"requested_url": url, "final_url": url, "html": CONTENT}
                        for url in urls]

            kwargs = dict(
                policy={"enabled": True, "max_pages": 6, "directory": {
                    "enabled": True, "max_requests": 4, "max_seconds": 60}},
                out=out / "output", today=DAY,
                baseline_signature="known-valid-baseline",
                pipeline_policy_digest="known-valid-policy",
                rights_path=rights, directory_fetcher=directory_fetch,
                fetcher=weekly_fetch,
            )
            before = [legacy_market()]
            with patch("happings_autopilot.source.robots_allowed", return_value=robot()):
                after, report, ids = phase.run(before, **kwargs)
            self.assertEqual(requested_xml, [ROOT+"/it/", INDEX, POST])
            self.assertEqual(requested_page, [GO])
            self.assertEqual(report["directory_request_slots_used"], 3)
            self.assertEqual(report["selected_urls"], [GO])
            self.assertLessEqual(len(requested_page) + report["directory_request_slots_used"], 6)
            self.assertEqual(after[0]["indirizzo"], "Piazza Vittoria")
            self.assertEqual(after[0]["slug"], before[0]["slug"])
            self.assertEqual(after[0]["url_fonte"], TOWN)
            self.assertEqual(after[0]["orario_testo"], "")
            self.assertEqual(ids, {"happings-gorizia-mercoledi"})
            self.assertTrue((out/"output/sources/happings-directory.json").is_file())

            with patch("happings_autopilot.source.robots_allowed",
                       side_effect=AssertionError("Resume must not fetch")):
                second, replay, _ = phase.run(before, **{**kwargs, "resume": True})
            self.assertEqual(after, second)
            self.assertTrue(replay["directory"]["resumed_checkpoint"])
            self.assertEqual(requested_xml, [ROOT+"/it/", INDEX, POST])
            self.assertEqual(requested_page, [GO])


if __name__ == "__main__":
    unittest.main()
