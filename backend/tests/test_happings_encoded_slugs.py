"""Safe support for observed percent-encoded Happings WordPress titles."""
import sys,unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from happings_detail_urls import detail_url
from happings_detail_discovery import url_kind,seed_state,ingest_pages
from happings_detail_layout import detail_url as parser_url
from source_calendar import detail_url as evidence_url
ROOT="https://www.happings.com/it/happing/"
URLS=[
 ROOT+"l%e2%88%9eplab/",
 ROOT+"yog%c2%b7amiga-morning-yoga/",
 ROOT+"raduno-%f0%9d%90%8f%f0%9d%90%80%f0%9d%90%91%f0%9d%90%80%f0%9d%90%93%f0%9d%90%80-%f0%9d%90%82%f0%9d%90%8e%f0%9d%90%8d-%f0%9d%90%8d%f0%9d%90%80%f0%9d%90%91%f0%9d%90%94%f0%9d%90%93%f0%9d%90%8e/",
 ROOT+"turandot-non-esiste-how-i-met-puccini%e2%93%a1-series-special-edition-%c2%b7-lucca-comics-games-2026/",
]
BAD=[
 ROOT,"https://evil.example/it/happing/mercato/",
 ROOT+"mercato%2fciao/",ROOT+"%2e%2e/",ROOT+"mercato%5csegreto/",
 ROOT+"mercato%252f/",ROOT+"mercato%00/",
 ROOT+"mercato%E2%88%9e/",ROOT+"mercato%zz/",
 ROOT+"mercato%3ffoo/",ROOT+"mercato%23bar/",
 ROOT+"mercato/?q=1",ROOT+"mercato/#x",
 ROOT+"mercato%2f..%2fprivate/",
]

class HappingsEncodedSlugs(unittest.TestCase):
    def test_all_live_encoded_event_slugs_are_admissible_as_source_urls(self):
        for url in URLS:
            with self.subTest(url=url):
                self.assertTrue(detail_url(url))
                self.assertEqual(url_kind(url),"detail")
                self.assertEqual(parser_url(url),url)
                self.assertTrue(evidence_url(url))
    def test_unsafe_or_noncanonical_encoded_urls_rejected_by_all_consumers(self):
        for url in BAD:
            with self.subTest(url=url):
                self.assertFalse(detail_url(url))
                self.assertIsNone(url_kind(url))
                self.assertIsNone(parser_url(url))
                self.assertFalse(evidence_url(url))
    def test_sitemap_observation_keeps_exact_encoded_url_and_real_hash(self):
        target=URLS[0]
        source="https://www.happings.com/happings_event-sitemap.xml"
        body=("<urlset><url><loc>"+target+"</loc></url></urlset>").encode()
        after,stats=ingest_pages(seed_state(observed_at=date(2026,10,21)),
                [{"requested_url":source,"final_url":source,"html":body}],
                observed_at=date(2026,10,21))
        self.assertEqual(stats["new_detail_urls"],1)
        self.assertEqual(after["resources"][target]["kind"],"detail")
        self.assertEqual(after["resources"][target]["status"],"unread")
if __name__=="__main__":
    unittest.main()
