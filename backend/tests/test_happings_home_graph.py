"""Observed HTML navigation from /it/ complements Yoast's event sitemap."""
import sys
import unittest
from datetime import date
from pathlib import Path
from urllib.robotparser import RobotFileParser
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import happings_detail_discovery as discovery

HOME = "https://www.happings.com/it/"
ARCHIVE = HOME + "categoria-evento/mercati/"
ARCHIVE2 = ARCHIVE + "page/2/"
ARCHIVE3 = ARCHIVE + "page/3/"
EVENT = HOME + "happing/mercato-coperto-campagna-amica-di-pisa/"
UNDERSCORE = HOME + "happing/bisatti_canino_ballista/"
INDEX = HOME + "sitemap_index.xml"
MAP = "https://www.happings.com/happings_event-sitemap.xml"
SPANISH = "https://www.happings.com/es/categoria-evento/mercati/"
ROBOT_TEXT = ("User-agent: *\nDisallow:\nSitemap: " + INDEX + "\n")
TODAY = date(2026, 10, 21)


def html(*links):
    return ("<!doctype html><html lang='it'><body><h1>Happings</h1>"
            + "".join('<a href="' + url + '">link</a>' for url in links)
            + "</body></html>").encode()


def sitemap(parent, links):
    return ("<" + parent + ">"
            + "".join("<" + ("sitemap" if parent == "sitemapindex" else "url")
                      + "><loc>" + link + "</loc></"
                      + ("sitemap" if parent == "sitemapindex" else "url") + ">" for link in links)
            + "</" + parent + ">").encode()


def robots():
    r = RobotFileParser()
    r.parse(ROBOT_TEXT.splitlines())
    return r


class HomeArchiveDiscoveryTests(unittest.TestCase):
    def test_real_home_and_market_archive_urls_are_scoped(self):
        self.assertEqual(discovery.url_kind(HOME), "home")
        self.assertEqual(discovery.url_kind(ARCHIVE), "archive")
        self.assertEqual(discovery.url_kind(ARCHIVE2), "archive")
        self.assertEqual(discovery.url_kind(EVENT), "detail")
        self.assertIsNone(discovery.url_kind(SPANISH))
        self.assertIsNone(discovery.url_kind(ARCHIVE + "?per_page=100"))
        self.assertIsNone(discovery.url_kind(HOME + "categoria-evento/concerti/"))
        self.assertIsNone(discovery.url_kind("https://www.evil.example/it/"))
        self.assertIsNone(discovery.url_kind(ARCHIVE + "page/10000/"))

    def test_home_seed_requires_robots_and_preserves_legacy_tests(self):
        ordinary = discovery.seed_state(robots_text=ROBOT_TEXT, observed_at=TODAY)
        self.assertNotIn(HOME, ordinary["resources"])
        seeded = discovery.seed_state(robots_text=ROBOT_TEXT, observed_at=TODAY, seed_home=True)
        self.assertIn(HOME, seeded["resources"])
        self.assertIn(INDEX, seeded["resources"])
        with self.assertRaises(ValueError):
            discovery.seed_state(observed_at=TODAY, seed_home=True)

    def test_crawls_real_links_from_home_to_archive_page_2_and_event(self):
        captures = {
            HOME: html(ARCHIVE, SPANISH, HOME+"categoria-evento/concerti/"),
            ARCHIVE: html(EVENT, ARCHIVE2),
            ARCHIVE2: html(EVENT, ARCHIVE3),
            INDEX: sitemap("sitemapindex", [MAP]),
            MAP: sitemap("urlset", [EVENT]),
            EVENT: html(HOME, ARCHIVE),
        }
        requested = []
        def fetch(url, *, robots):
            requested.append(url)
            return captures[url], url

        seeded = discovery.seed_state(robots_text=ROBOT_TEXT, observed_at=TODAY, seed_home=True)
        after, pages, report = discovery.acquire(
            seeded, today=TODAY, robots=robots(), max_requests=6,
            max_seconds=420, fetcher=fetch, sleep=lambda _: None,
            clock=lambda: "2026-10-21T08:00:00+00:00")
        self.assertEqual(requested[0], HOME)
        self.assertEqual(requested[:3], [HOME, ARCHIVE, ARCHIVE2])
        self.assertEqual(report["home_read"], 1)
        self.assertEqual(report["archives_read"], 2)
        self.assertEqual(report["new_archive_urls"], 3)
        self.assertEqual(report["details_read"], 1)
        self.assertEqual([page["requested_url"] for page in pages], [EVENT])
        self.assertEqual(report["known_archive_urls"], 3)
        self.assertEqual(report["pending_archive_urls"], 1)
        self.assertNotIn(SPANISH, after["resources"])
        self.assertNotIn(HOME + "categoria-evento/concerti/", after["resources"])
        self.assertEqual(after["resources"][ARCHIVE3]["status"], "unread")

    def test_home_links_need_evidence_hash_and_archive_rejects_redirect(self):
        seeded = discovery.seed_state(robots_text=ROBOT_TEXT, observed_at=TODAY, seed_home=True)
        after, counts = discovery.ingest_pages(seeded, [{
            "requested_url": HOME, "final_url": HOME, "html": html(ARCHIVE)}], observed_at=TODAY)
        self.assertEqual(counts["new_archive_urls"], 1)
        proof = after["resources"][ARCHIVE]["origins"][0]
        self.assertEqual(proof["kind"], "html_link")
        self.assertEqual(proof["url"], HOME)
        self.assertEqual(len(proof["sha256"]), 64)
        with self.assertRaises(ValueError):
            discovery.ingest_pages(seeded, [{"requested_url": ARCHIVE,
                "final_url": SPANISH, "html": html(EVENT)}], observed_at=TODAY)


if __name__ == "__main__":
    unittest.main()
