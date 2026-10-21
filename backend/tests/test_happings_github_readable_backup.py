"""Restore full Happings facts and provenance from the public JSON archive."""
from __future__ import annotations
import gzip,hashlib,json,sys,tempfile,unittest
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import happings_github_readable_backup as backup
from happings_full_reconciliation import _saved_page

URL="https://www.happings.com/it/mercati-settimanali-a-gorizia-e-provincia/"
def fixture(root):
    source=root/"sources";snapshot=source/"happings-full-crawl"
    reports=source/"happings-reconciliation"
    (snapshot/"pages").mkdir(parents=True)
    reports.mkdir()
    now=datetime.now(timezone.utc).isoformat()
    fact={"url":URL,"status":"parsed","kind":"weekly","read_at":now,
          "bytes":1100,"html_sha256":"a"*64,"source_rows":1,
          "markets":[{"city":"Gorizia","place":"Piazza Vittoria","weekday":2}]}
    raw=gzip.compress(json.dumps(fact,ensure_ascii=False).encode())
    fname=hashlib.sha256(URL.encode()).hexdigest()+".json.gz"
    (snapshot/"pages"/fname).write_bytes(raw)
    entry={"status":"parsed","kind":"weekly","read_at":now,
           "facts_sha256":hashlib.sha256(raw).hexdigest(),"source_rows":1}
    (snapshot/"checkpoint.json").write_text(
        json.dumps({"schema":1,"queue":[URL],"done":{URL:entry},
                    "started_at":now,"discovery":{}},ensure_ascii=False),"utf-8")
    (reports/"happings-source-worklist.json").write_text(
        json.dumps([{"url":URL,"city":"Gorizia"}]),"utf-8")
    (reports/"happings-source-reconciliation.json").write_text(
        json.dumps({"source_pages":1,"correct":True}),"utf-8")
    (reports/"happings-local-run.json").write_text(
        json.dumps({"username":"PRIVATE-WINDOWS-USER","status":"completed"}),"utf-8")
    return source,fact

class BackupTests(unittest.TestCase):
    def test_restore_semantically_matches_each_original_page(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)
            source,fact=fixture(root)
            archive=root/"archive"
            manifest=backup.run(source,archive)
            self.assertEqual(manifest["source_pages"],1)
            self.assertEqual(backup.verify(archive),1)
            target=root/"restored"
            report=backup.restore(archive,target)
            self.assertEqual(report["source_pages_restored"],1)
            self.assertEqual(report["reports_restored"],2)
            self.assertTrue(report["source_html_sha256_preserved"])
            state=json.loads((target/"happings-full-crawl/checkpoint.json").read_text("utf-8"))
            restored=_saved_page(target/"happings-full-crawl",URL,state["done"][URL])
            self.assertEqual(restored,fact)
            self.assertEqual(state["done"][URL]["original_gzip_sha256"],
                             manifest_source_sha(source,URL))
            self.assertEqual(json.loads((target/"happings-reconciliation/happings-source-worklist.json").read_text("utf-8")),
                             [{"url":URL,"city":"Gorizia"}])
            self.assertFalse((target/"happings-reconciliation/happings-local-run.json").exists())
            with self.assertRaisesRegex(ValueError,"empty destination"):
                backup.restore(archive,target)

    def test_changed_chunk_is_rejected_without_restoring(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td);source,_=fixture(root);out=root/"archive"
            manifest=backup.run(source,out)
            path=out/manifest["shards"][0]["path"]
            path.write_bytes(path.read_bytes()+b"tamper")
            with self.assertRaisesRegex(ValueError,"hash mismatch"):
                backup.verify(out)
            with self.assertRaisesRegex(ValueError,"hash mismatch"):
                backup.restore(out,root/"empty")
            self.assertFalse((root/"empty").exists())

def manifest_source_sha(source,url):
    data=json.loads((source/"happings-full-crawl/checkpoint.json").read_text("utf-8"))
    return data["done"][url]["facts_sha256"]

if __name__=="__main__":
    unittest.main()
