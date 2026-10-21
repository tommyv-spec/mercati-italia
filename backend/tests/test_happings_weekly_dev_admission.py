"""DEV admission must be reproducible, source-scoped and safe to rerun."""
from __future__ import annotations

import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import happings_weekly_dev_admission as a
from happings_weekly_admission import _new_row
from export_static import normalize

W="https://www.happings.com/it/mercati-settimanali-a-udine-e-provincia/"
X="https://www.happings.com/it/mercati-settimanali-a-pisa-e-provincia/"
SHA="abc123"


class Robots:
    def can_fetch(self,*_args):
        return True
    def crawl_delay(self,*_args):
        return None
    def request_rate(self,*_args):
        return None


class WeeklyDevAdmissionTests(unittest.TestCase):
    def test_only_publisher_verified_missing_venues_select_live_pages(self):
        with tempfile.TemporaryDirectory() as t:
            folder=Path(t)
            rows=[{"outcome":"new_venue_possible_needs_source_html_admission","urls":[W]},
                  {"outcome":"new_venue_possible_needs_source_html_admission","urls":[W,X]},
                  {"outcome":"source_location_vague","urls":[X]}]
            (folder/"list.json").write_text(json.dumps(rows),"utf-8")
            (folder/"qa.json").write_text(json.dumps({
                "dev_revision_analyzed":SHA,"source_content_complete":True,
                "snapshot_pages_completed":2313,"snapshot_pages_total":2313,
                "observed_source_pages":{"processed_parsed":2313}}),"utf-8")
            urls,n=a.candidate_pages(folder/"list.json",folder/"qa.json",dev_sha=SHA)
            self.assertEqual(urls,[X,W])
            self.assertEqual(n,2)
            with self.assertRaisesRegex(ValueError,"stale"):
                a.candidate_pages(folder/"list.json",folder/"qa.json",dev_sha="wrong")

    def test_full_static_proof_remains_valid_after_region_canonicalization(self):
        day=date(2026,10,21)
        raw=_new_row({"city":"Aquileia","weekday":1,"place":"Piazza San Giovanni"},
                     region="friuli venezia giulia",province="UD",source_url=W,
                     read_on=day,page_hash="a"*64,page_metadata=None)
        normalized, error=normalize(raw,day)
        self.assertIsNone(error)
        self.assertEqual(raw["regione"],"Friuli Venezia Giulia")
        self.assertEqual(raw["riscontri_campi"],normalized["riscontri_campi"])
        evidence={"added_ids":[raw["slug"]]}
        self.assertEqual(a.verify_catalog([], [normalized],evidence,today=day),[raw["slug"]])
        tampered={**normalized,"date_quality":"confermata"}
        with self.assertRaisesRegex(ValueError,"unverified"):
            a.verify_catalog([], [tampered],evidence,today=day)
        with self.assertRaisesRegex(ValueError,"protected"):
            a.verify_catalog([normalized], [],{"added_ids":[]},today=day)

    def test_encoded_country_and_robots_bound_live_html(self):
        with patch("happings_weekly_dev_admission.source.authorization_status",
                   return_value={"authorized":True}):
            pages=a.fetch_pages([W],today=date(2026,10,21),robots=Robots(),
                                fetcher=lambda url,robots:(b"x"*450,url),sleep=lambda _:None)
        self.assertEqual(pages[0]["requested_url"],W)
        self.assertEqual(len(pages[0]["html"]),450)
        with patch("happings_weekly_dev_admission.source.authorization_status",
                   return_value={"authorized":True}):
            with self.assertRaisesRegex(ValueError,"robots or URL scope"):
                a.fetch_pages(["https://www.happings.com.evil.test/foo/"],
                              today=date(2026,10,21),robots=Robots(),
                              sleep=lambda _:None)

    def test_cross_platform_encoding_is_mandatory(self):
        with patch("locale.getpreferredencoding",return_value="cp1252"):
            with self.assertRaisesRegex(ValueError,"UTF-8 mode"):
                a.ensure_utf8()
        with patch("locale.getpreferredencoding",return_value="utf-8"):
            a.ensure_utf8()

    def test_only_dedicated_checkout_may_publish_and_never_in_production(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            with self.assertRaisesRegex(ValueError,"dedicated"):
                a.checked_checkout(root)
            (root/".happings-dedicated-checkout").write_text("okay","utf-8")
            def pretend(repo,*args,**_):
                if args[0]=="remote":return "https://github.com/tommyv-spec/mercati-italia.git"
                if args[0]=="rev-parse":return a.BRANCH if args[1]=="--abbrev-ref" else SHA
                if args[0]=="status":return ""
                if args[0]=="ls-remote":return SHA+"\trefs/heads/"+a.BRANCH
                raise AssertionError(args)
            with patch.object(a,"git",side_effect=pretend):
                self.assertEqual(a.checked_checkout(root),SHA)
            with patch.object(a,"git",side_effect=lambda *_args,**_kw:"main"):
                with self.assertRaises(ValueError): a.checked_checkout(root)

    def test_publisher_html_is_durable_and_checksum_bound_locally(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            batch=[{"final_url":W,"html":b"X"*500,
                    "fetched_at":"2026-10-21T10:00:00+00:00"}]
            saved=a.archive_source_html(batch,root)
            self.assertEqual(len(saved),1)
            self.assertEqual(saved,a.archive_source_html(batch,root))
            evidence=root/"happings-source-html"/saved[0]["archive"]
            self.assertTrue(evidence.exists())
            self.assertFalse(json.loads((root/"happings-source-html-index.json")
                                        .read_text("utf-8"))["raw_html_published_to_github"])
            evidence.write_bytes(b"corrupt")
            with self.assertRaises(ValueError):
                a.archive_source_html(batch,root)

    def test_replay_exact_captured_autopilot_html_without_extra_requests(self):
        import happings_autopilot
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            (root/"sources").mkdir()
            page={"requested_url":W,"final_url":W,"html":b"x"*450}
            context={"today":"2026-10-21","selected_urls":[W],
                     "input_sha256":"a"*64,"rights_sha256":"b"*64}
            saved={"schema":1,"context":context,"status":"retrieved",
                   "pages":[happings_autopilot._pack_page(page)],
                   "failures":[]}
            report={"schema":1,"date":"2026-10-21","enabled":True,
                    "fetch_authorized":True,"selected_urls":[W],
                    "input_sha256":context["input_sha256"],
                    "rights_record_sha256":context["rights_sha256"]}
            checkpoint=root/"sources/happings-pages.json"
            checkpoint.write_text(json.dumps(saved),"utf-8")
            report_file=root/"happings-enrichment.json"
            report_file.write_text(json.dumps(report),"utf-8")
            observed,_=a.pages_from_autopilot(root,today=date(2026,10,21))
            self.assertEqual(len(observed),1)
            self.assertEqual(observed[0]["html"],page["html"])
            saved["pages"][0]["html_sha256"]="0"*64
            checkpoint.write_text(json.dumps(saved),"utf-8")
            with self.assertRaisesRegex(ValueError,"hash|changed"):
                a.pages_from_autopilot(root,today=date(2026,10,21))
            saved["pages"]=[happings_autopilot._pack_page(page)]
            checkpoint.write_text(json.dumps(saved),"utf-8")
            report["fetch_authorized"]=False
            report_file.write_text(json.dumps(report),"utf-8")
            with self.assertRaisesRegex(ValueError,"authorized"):
                a.pages_from_autopilot(root,today=date(2026,10,21))

    def test_atomic_manifest_updates_only_scoped_assets(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t)
            staged=root/"tmp"
            repo=root/"repo"
            (staged/"regions").mkdir(parents=True)
            (repo/"public/data/v1").mkdir(parents=True)
            (staged/"regions/region.json").write_text("new","utf-8")
            (staged/"manifest.json").write_text('{"schema":1}',"utf-8")
            (repo/"public/data/v1/manifest.json").write_text("old","utf-8")
            (repo/"public/data/v1/old-asset.json").write_text("stale","utf-8")
            (repo/"keep.txt").write_text("retained","utf-8")
            a.copy_into_checkout(staged,repo)
            self.assertEqual((repo/"public/data/v1/manifest.json").read_text(),"{" + '"schema":1' + "}")
            self.assertFalse((repo/"public/data/v1/old-asset.json").exists())
            self.assertEqual((repo/"keep.txt").read_text(),"retained")


if __name__=="__main__":
    unittest.main()
