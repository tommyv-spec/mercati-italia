"""Offline D1 catalog regression tests: real SQLite schema, no production mutation."""
from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import d1_catalog as d


class D1CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        schema = Path(__file__).resolve().parents[2]/"db/cloudflare/0001_catalog.sql"
        self.db.executescript(schema.read_text(encoding="utf-8"))

    def manifest(self, rows):
        region = self.base/"public/data/v1/regions"
        region.mkdir(parents=True, exist_ok=True)
        raw = (json.dumps({"schema":1,"markets":rows}, ensure_ascii=False,
                          separators=(",",":"))+"\n").encode("utf-8")
        h = hashlib.sha256(raw).hexdigest()
        name = f"test-{h[:14]}.json"
        (region/name).write_bytes(raw)
        manifest = {"schema":1,"layout":"regional","total":len(rows),
                    "content_signature":"f"*64,
                    "regions":[{"path":"data/v1/regions/"+name,"count":len(rows)}]}
        target = self.base/"public/data/v1/manifest.json"
        target.write_text(json.dumps(manifest),encoding="utf-8")
        return target

    def sample(self, slug):
        return {"slug":slug,"nome":"Mercato d'Ottobre",
                "regione":"Toscana","provincia":"FI",
                "citta":"Firenze","fonte":"happings.com",
                "orario_testo":"La mattina","indirizzo":"Piazza dell'Unità",
                "date_quality":"sconosciuta","date":[]}

    def test_only_dev_can_be_activated_after_count_verified(self):
        path = self.manifest([self.sample("happings-test-uno"),
                              self.sample("happings-test-due")])
        meta = d.dataset_meta(path,"a"*40)
        self.assertEqual(len(list(d.manifest_rows(path))),2)
        self.db.executescript(d.dataset_create_sql(meta))
        cmds = [d.market_statement(meta,row) for row in d.manifest_rows(path)]
        chunks = list(d.chunked(cmds))
        self.assertEqual(sum(count for _,count in chunks),2)
        for body,n in chunks:
            self.db.executescript(body)
        self.db.execute(
            "UPDATE catalog_datasets SET status='ready' WHERE dataset_id=? "
            "AND expected_rows=(SELECT COUNT(*) FROM catalog_markets WHERE dataset_id=?)",
            (meta["id"],meta["id"]))
        self.db.execute("UPDATE catalog_channels SET dataset_id=? WHERE channel='dev'",
                        (meta["id"],))
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM catalog_markets").fetchone()[0],2)
        self.assertIsNone(self.db.execute(
            "SELECT dataset_id FROM catalog_channels WHERE channel='prod'").fetchone()[0])
        rows = self.db.execute(
            "SELECT payload_json FROM catalog_markets ORDER BY slug").fetchall()
        self.assertTrue(all("La mattina" in x[0] for x in rows))
        self.assertIn("Piazza dell'Unità", rows[0][0])

    def test_replay_changes_nothing_and_preserves_production_pointer(self):
        path = self.manifest([self.sample("same-id")])
        meta = d.dataset_meta(path,"b"*40)
        self.db.executescript(d.dataset_create_sql(meta))
        stmt = next(d.market_statement(meta,r) for r in d.manifest_rows(path))
        self.db.executescript(stmt+stmt)
        self.assertEqual(self.db.execute(
            "SELECT COUNT(*) FROM catalog_markets").fetchone()[0],1)
        self.assertIsNone(self.db.execute(
            "SELECT dataset_id FROM catalog_channels WHERE channel='prod'").fetchone()[0])

    def test_reject_corrupted_regional_hash(self):
        p=self.manifest([self.sample("hash-test")])
        region=next((p.parents[2]/"data/v1/regions").glob("*.json"))
        region.write_bytes(region.read_bytes()+b"tampered")
        with self.assertRaisesRegex(ValueError,"SHA-256 mismatch"):
            list(d.manifest_rows(p))

    def test_reject_duplicate_markets(self):
        p=self.manifest([self.sample("dup"),self.sample("dup")])
        with self.assertRaisesRegex(ValueError,"duplicate"):
            list(d.manifest_rows(p))

    def test_source_facts_proof_is_not_optional(self):
        from gzip import compress
        url="https://www.happings.com/it/happing/market-fixture/"
        snapshot=self.base/"source"
        (snapshot/"pages").mkdir(parents=True)
        encoded=compress(json.dumps({"url":url,"status":"parsed",
                    "read_at":"2026-10-22T10:00:00+00:00",
                    "html_sha256":"c"*64}).encode("utf-8"))
        (snapshot/"pages"/(d.digest(url.encode("utf-8"))+".json.gz")).write_bytes(encoded)
        entry={"kind":"detail","status":"parsed","facts_sha256":d.digest(encoded)}
        stmt=d.source_statement(snapshot,url,entry)
        self.assertIn("INSERT INTO happings_source_facts",stmt)
        entry["facts_sha256"]="0"*64
        with self.assertRaisesRegex(ValueError,"hash mismatches"):
            d.source_statement(snapshot,url,entry)

    def test_sql_escape_and_statement_limits(self):
        self.assertEqual(d.sql("Bob's market"),"'Bob''s market'")
        with self.assertRaisesRegex(ValueError,"Null byte"):
            d.sql("bad\x00row")
        meta={"id":"cat-test"}
        too_big=self.sample("big")
        too_big["descrizione"]="A"*110000
        with self.assertRaisesRegex(ValueError,"query limit"):
            d.market_statement(meta,too_big)


if __name__ == "__main__":
    unittest.main()
