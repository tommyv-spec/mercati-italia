"""Configured DEV detail run really begins with the linked homepage."""
from __future__ import annotations
import sys,tempfile,unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch
from urllib.robotparser import RobotFileParser
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import happings_detail_autopilot as runner
import happings_detail_discovery as discovery

HOME=discovery.HOMEPAGE
CATEGORY=HOME+"categoria-evento/mercati/"
MARKET=HOME+"happing/mercato-coperto-campagna-amica-di-pisa/"
ROBOTS="User-agent: *\nDisallow:\nSitemap: https://www.happings.com/it/sitemap_index.xml\n"
FIXTURE=Path(__file__).parent/"fixtures/happings_detail/pisa.html"
TODAY=date(2026,10,21)

class HappingsHomeAutopilotTests(unittest.TestCase):
    def test_active_policy_starts_home_and_replays_without_new_http(self):
        requests=[]
        content={
            HOME:b'<html><body><a href="/it/categoria-evento/mercati/">Mercati</a></body></html>',
            CATEGORY:b'<html><body><a href="/it/happing/mercato-coperto-campagna-amica-di-pisa/">Pisa</a></body></html>',
            MARKET:FIXTURE.read_bytes(),
            HOME+"sitemap_index.xml":b"<sitemapindex></sitemapindex>",
        }
        def network(url,*,robots):
            requests.append(url)
            return content[url],url
        def fetch_robots(url,**kwargs):
            if url!="https://www.happings.com/robots.txt":raise AssertionError(url)
            return ROBOTS.encode(),url
        def allow(fetch):
            fetch("https://www.happings.com/robots.txt")
            p=RobotFileParser()
            p.parse(ROBOTS.splitlines())
            return p
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)
            kwargs=dict(policy={"enabled":True,"max_requests":4,"max_seconds":420,
                               "home_navigation":True},
                        out=out,today=TODAY,baseline_signature="home-crawl",
                        pipeline_policy_digest="home-policy",
                        bootstrap=None,fetcher=network)
            original_acquire = discovery.acquire

            def reproducible_acquire(*args, **settings):
                # This is a historical fixture for 2026-10-21. The production
                # crawler correctly rejects capture timestamps from other
                # days, so pin the mocked acquisition clock to the fixture's
                # date. A real sleep would only slow down this HTTP-free test.
                return original_acquire(
                    *args, **settings,
                    clock=lambda: "2026-10-21T12:00:00+00:00",
                    sleep=lambda _: None,
                )

            with (patch("happings_detail_autopilot.weekly._fetch_one",side_effect=fetch_robots),
                  patch("happings_detail_autopilot.weekly.robots_allowed",side_effect=allow),
                  patch("happings_detail_autopilot.discovery.acquire",
                        side_effect=reproducible_acquire)):
                after,report,state=runner.run([],**kwargs)
            self.assertEqual(after,[])
            self.assertEqual(requests,[HOME,CATEGORY,HOME+"sitemap_index.xml",MARKET])
            self.assertEqual(report["discovery"]["home_read"],1)
            self.assertEqual(report["discovery"]["archives_read"],1)
            self.assertEqual(report["discovery"]["details_read"],1)
            self.assertEqual(state["resources"][MARKET]["status"],"retrieved")
            with patch("happings_detail_autopilot.weekly._fetch_one",
                       side_effect=AssertionError("No HTTP on resume")):
                replay,repeat,same=runner.run([],**{**kwargs,"resume":True})
            self.assertEqual(replay,after)
            self.assertEqual(same,state)
            self.assertTrue(repeat["source_evidence_reused"])

if __name__=="__main__":
    unittest.main()
