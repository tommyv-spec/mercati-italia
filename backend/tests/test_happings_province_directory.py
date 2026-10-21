"""Happings homepage and WordPress post-sitemaps are independently discovered."""
from __future__ import annotations
import sys,unittest
from datetime import date,timedelta
from pathlib import Path
from urllib.robotparser import RobotFileParser
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import happings_province_directory as directory
import happings_source_enrichment as source
from happings_weekly_layout import province_page_key

ROOT="https://www.happings.com"
HOME=ROOT+"/it/"
INDEX=ROOT+"/it/sitemap_index.xml"
POST1=ROOT+"/post-sitemap.xml"
POST2=ROOT+"/post-sitemap2.xml"
AQ=ROOT+"/it/mercati-settimanali-a-l-27aquila-e-provincia/"
FORLI=ROOT+"/it/mercati-settimanali-a-forl-c3-ac-e-cesena-e-provincia/"
GO=ROOT+"/it/mercati-settimanali-a-gorizia-e-provincia/"
SPANISH=ROOT+"/it/mercati-settimanali-a-barcelona-e-provincia/"
FR=ROOT+"/it/mercati-settimanali-nel-dipartimento-di-ain/"
TODAY=date(2026,10,21)
HTML=b"""<html><body>
<a href="/it/categoria-evento/mercati/">Mercati</a>
<a href="/it/eventi-a-pisa/">Eventi Pisa</a>
<a href="/it/category/eventi-nel-mondo-it/italia-it/">Italia</a>
<a href="/es/categoria-evento/mercati/">Mercados</a>
</body></html>"""


def robots(*,allowed=True,include_index=True):
    lines=["User-agent: *","Disallow:" if allowed else "Disallow: /"]
    if include_index:lines.append("Sitemap: "+INDEX)
    result=RobotFileParser()
    result.parse(lines)
    return result


def xml_urls(urls,*,is_index):
    tag="sitemap" if is_index else "url"
    parent="sitemapindex" if is_index else "urlset"
    return ("<"+parent+">"+"".join("<"+tag+"><loc>"+url+"</loc></"+tag+">" for url in urls)
            +"</"+parent+">").encode()


class HappingsProvinceDirectoryTests(unittest.TestCase):
    def test_wordpress_encoded_province_labels_are_checked_against_istat(self):
        expected={AQ:("abruzzo","AQ"),FORLI:("emilia romagna","FC"),
                  ROOT+"/it/mercati-settimanali-a-ascoli-e-provincia/":("marche","AP"),
                  ROOT+"/it/mercati-settimanali-a-pesaro-urbino-e-provincia/":("marche","PU"),
                  ROOT+"/it/mercati-settimanali-a-caltanisetta-e-provincia/":("sicilia","CL")}
        scope=source._official_geography()[1]
        for url,area in expected.items():
            with self.subTest(url=url):
                self.assertEqual(scope[province_page_key(url)],{area})
        self.assertIsNone(province_page_key(FR))

    def test_real_home_first_then_post_sitemaps_filter_foreign_regions(self):
        pages={HOME:HTML,INDEX:xml_urls([POST1,POST2,ROOT+"/happings_event-sitemap.xml"],is_index=True),
               POST1:xml_urls([AQ,SPANISH,FORLI,FR],is_index=False),
               POST2:xml_urls([GO,AQ,ROOT+"/bad"],is_index=False)}
        calls=[]
        def fetch(url,*,robots):
            calls.append(url)
            return pages[url],url
        urls,report=directory.discover(today=TODAY,robots=robots(),policy={"enabled":True,
                "max_requests":4,"max_seconds":60},fetcher=fetch,sleep=lambda _:None)
        self.assertEqual(urls,sorted([AQ,FORLI,GO]))
        self.assertEqual(calls,[HOME,INDEX,POST1,POST2])
        self.assertEqual(report["requests_used"],4)
        self.assertEqual(report["italian_province_scopes"],3)
        self.assertEqual(report["out_of_scope_urls"],3)
        self.assertEqual(report["post_sitemaps_deferred"],0)
        self.assertEqual(report["status"],"retrieved")
        self.assertIn(HOME+"categoria-evento/mercati/",report["homepage"]["market_category_urls"])
        self.assertIn(HOME+"eventi-a-pisa/",report["homepage"]["city_index_urls"])
        self.assertTrue(report["homepage"]["italy_portal_linked"])

    def test_more_sitemaps_rotate_and_do_not_exceed_shared_budget(self):
        posts=[POST1]+[ROOT+"/post-sitemap"+str(i)+".xml" for i in range(2,7)]
        pages={HOME:HTML,INDEX:xml_urls(posts,is_index=True)}
        for index,url in enumerate(posts):
            pages[url]=xml_urls([AQ if index%2 else GO],is_index=False)
        observed=set()
        for day in (TODAY+timedelta(days=i) for i in range(12)):
            calls=[]
            def fetch(url,*,robots):
                calls.append(url)
                return pages[url],url
            urls,report=directory.discover(today=day,robots=robots(),
                    policy={"enabled":True,"max_requests":3,"max_seconds":60},
                    fetcher=fetch,sleep=lambda _:None)
            observed.update(calls[2:])
            self.assertLessEqual(report["requests_used"],3)
            self.assertEqual(calls[0],HOME)
            self.assertEqual(report["post_sitemaps_deferred"],5)
            self.assertEqual(report["status"],"partial")
            self.assertTrue(urls)
        self.assertEqual(observed,set(posts))

    def test_robots_and_home_redirect_are_fail_closed(self):
        for rp in [None,robots(allowed=False),robots(include_index=False)]:
            urls,report=directory.discover(today=TODAY,robots=rp,
                    policy={"enabled":True},fetcher=lambda *_args,**_kwargs:
                    self.fail("unexpected request"),sleep=lambda _:None)
            self.assertEqual(urls,[])
            self.assertEqual(report["requests_used"],0)
        def redirect(url,*,robots):
            return HTML,INDEX
        urls,report=directory.discover(today=TODAY,robots=robots(),
                    policy={"enabled":True},fetcher=redirect,sleep=lambda _:None)
        self.assertEqual(urls,[])
        self.assertEqual(report["status"],"home_unavailable")
        self.assertEqual(report["requests_used"],1)

    def test_invalid_source_map_is_failure_not_market(self):
        def fetch(url,*,robots):
            if url==HOME:return HTML,url
            if url==INDEX:return xml_urls([POST1],is_index=True),url
            return b"<!DOCTYPE bomb><urlset></urlset>",url
        urls,report=directory.discover(today=TODAY,robots=robots(),
                   policy={"enabled":True},fetcher=fetch,sleep=lambda _:None)
        self.assertEqual(urls,[])
        self.assertEqual(report["status"],"partial")
        self.assertEqual(report["requests_used"],3)
        self.assertTrue(report["failures"])

    def test_policy_and_hostname_reject_unreviewed_urls(self):
        for u in [ROOT.replace("www","shop")+"/post-sitemap.xml",
                  POST1+"?watch=1",POST1+"#frag",POST1+"%2f"]:
            self.assertFalse(directory._post_sitemap(u))
        self.assertTrue(directory._post_sitemap(ROOT+"/post-sitemap11.xml"))
        for bad in [{"enabled":True,"max_requests":1},{"enabled":"true"},
                    {"enabled":True,"max_seconds":600},{"unexpected":True}]:
            with self.subTest(policy=bad):
                with self.assertRaises(ValueError):
                    directory.validate_policy(bad)


if __name__=="__main__":
    unittest.main()
