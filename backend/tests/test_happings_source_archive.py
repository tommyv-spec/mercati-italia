"""Happings portable GitHub archive is reproducible, scoped and fail-closed."""
from __future__ import annotations

import gzip
import hashlib
import json
import tempfile
import unittest
from datetime import datetime,timezone
from pathlib import Path
from unittest.mock import patch

from sys import path as syspath
syspath.insert(0,str(Path(__file__).resolve().parents[1]))
import happings_source_archive as archive

URL="https://www.happings.com/it/mercati-settimanali-a-gorizia-e-provincia/"


def source_fixture(root):
    data=root/"data"
    snap=data/"happings-full-crawl"
    reports=data/"happings-reconciliation"
    (snap/"pages").mkdir(parents=True)
    reports.mkdir(parents=True)
    fact={"url":URL,"status":"parsed","kind":"weekly","read_at":
          datetime.now(timezone.utc).isoformat(),"bytes":1000,
          "html_sha256":"a"*64,"source_rows":1,"markets":[
              {"city":"Gorizia","weekday":1,"place":"Piazza della Vittoria"}]}
    raw=gzip.compress(json.dumps(fact).encode())
    (snap/"pages"/(hashlib.sha256(URL.encode()).hexdigest()+".json.gz")).write_bytes(raw)
    state={"schema":1,"queue":[URL],"done":{URL:{
        "status":"parsed","kind":"weekly","read_at":fact["read_at"],
        "facts_sha256":hashlib.sha256(raw).hexdigest()}}}
    (snap/"checkpoint.json").write_text(json.dumps(state),"utf-8")
    (reports/"happings-source-worklist.json").write_text('[]',"utf-8")
    (reports/"happings-local-run.json").write_text(
        json.dumps({"status":"completed","repo":"C:/private/user",
            "snapshot":"C:/private/data","qa":{"pages_total":1,"dev_sha":"a"*40}}),"utf-8")
    return data


class HappingsArchiveTests(unittest.TestCase):
    def test_scoped_archive_restores_facts_without_private_machine_paths(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            data=source_fixture(root)
            out=root/"bundle"
            a=archive.build(data,out)
            self.assertEqual(a["source"]["source_pages"],1)
            d,files=archive.verified_bytes(out)
            self.assertEqual(len(files),4)
            self.assertNotIn("C:/private/",b"".join(files.values()).decode("utf-8","ignore"))
            self.assertEqual(d["compressed_archive_sha256"],
                             a["compressed_archive_sha256"])
            target=root/"restored"
            result=archive.restore(out,target)
            self.assertEqual(result["restored_files"],4)
            self.assertTrue((target/"snapshot/checkpoint.json").is_file())
            with self.assertRaisesRegex(ValueError,"existing local source catalog"):
                archive.restore(out,target)

    def test_tampered_part_detected_before_restore(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            out=root/"bundle"
            archive.build(source_fixture(root),out)
            part=out/"happings-facts-part-000.bin"
            part.write_bytes(part.read_bytes()+b"forged")
            with self.assertRaisesRegex(ValueError,"chunk hash or size"):
                archive.verified_bytes(out)
            self.assertFalse((root/"restored").exists())

    def test_checkpoint_missing_page_never_archived(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            data=source_fixture(root)
            state=data/"happings-full-crawl/checkpoint.json"
            j=json.loads(state.read_text("utf-8"))
            j["done"].clear()
            state.write_text(json.dumps(j),"utf-8")
            with self.assertRaisesRegex(ValueError,"incomplete"):
                archive.build(data,root/"out")

    def test_untrusted_member_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            data=source_fixture(root)
            (data/"happings-reconciliation"/"../../evil").resolve()
            (data/"happings-reconciliation"/"credentials.txt").write_text(
                "secret",encoding="utf-8")
            a=archive.build(data,root/"out")
            _,files=archive.verified_bytes(root/"out")
            self.assertNotIn("reports/credentials.txt",files)
            self.assertEqual(a["source"]["source_pages"],1)


if __name__=="__main__":
    unittest.main()
