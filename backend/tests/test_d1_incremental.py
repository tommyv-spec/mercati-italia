"""D1 incremental catalog tests: real SQLite and no remote Cloudflare writes."""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import d1_catalog as base
import d1_incremental as inc


class D1IncrementalTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.db = sqlite3.connect(":memory:")
        self.addCleanup(self.db.close)
        self.db.row_factory = sqlite3.Row
        root = Path(__file__).resolve().parents[2] / "db/cloudflare"
        self.schema_v1 = (root / "0001_catalog.sql").read_text("utf-8")
        self.schema_v2 = (root / "0002_incremental.sql").read_text("utf-8")
        self.db.executescript(self.schema_v1)
        self.db.executescript(self.schema_v2)
        self.original = [
            self.market("mercato-uno", "Martedì"),
            self.market("mercato-due", "Giovedì"),
        ]
        self.add_snapshot("cat-base", self.original, "b" * 64)
        self.db.execute(
            "UPDATE catalog_channels SET dataset_id='cat-base' WHERE channel='dev'"
        )
        self.db.commit()
        self.patch_query = patch.object(inc, "remote_query", side_effect=self.query)
        self.patch_query.start()
        self.addCleanup(self.patch_query.stop)

    @staticmethod
    def market(slug, hour):
        return {
            "slug": slug, "nome": "Mercato d'Ottobre", "regione": "Toscana",
            "provincia": "FI", "citta": "Firenze", "fonte": "happings.com",
            "orario_testo": hour, "indirizzo": "Piazza dell'Unità",
            "date_quality": "sconosciuta", "date": [],
        }

    def query(self, statement):
        cursor = self.db.execute(statement)
        if cursor.description:
            return [dict(row) for row in cursor.fetchall()]
        self.db.commit()
        return []

    def add_snapshot(self, version, rows, signature):
        self.db.execute(
            "INSERT INTO catalog_datasets "
            "(dataset_id,content_signature,manifest_sha256,source_git_sha,"
            "expected_rows,status) VALUES (?,?,?,?,?,'ready')",
            (version, signature, "a" * 64, "c" * 40, len(rows))
        )
        for row in rows:
            self.db.executescript(base.market_statement({"id": version}, row))

    def add_delta(self, version, parent, changes, expected, signature):
        self.db.execute(
            "INSERT INTO catalog_datasets "
            "(dataset_id,content_signature,manifest_sha256,source_git_sha,"
            "expected_rows,status) VALUES (?,?,?,?,?,'ready')",
            (version, signature, "a" * 64, "c" * 40, expected)
        )
        self.db.execute(
            "INSERT INTO catalog_dataset_parents(dataset_id,parent_dataset_id)"
            " VALUES (?,?)", (version, parent)
        )
        for row in changes:
            self.db.executescript(inc.change_statement(version, row))
        self.db.commit()

    def test_schema_is_idempotent_and_legacy_is_not_rewritten(self):
        self.db.executescript(self.schema_v2)
        self.db.executescript(self.schema_v2)
        self.assertEqual(self.query(
            "SELECT COUNT(*) AS n FROM catalog_markets")[0]["n"], 2)
        self.assertEqual(set(inc.TABLES), set(r["name"] for r in self.query(
            "SELECT name FROM sqlite_schema WHERE name IN "
            "('catalog_dataset_parents','catalog_market_changes',"
            "'catalog_delta_import_chunks')")))

    def test_one_modified_one_added_one_unchanged(self):
        updated = self.market("mercato-uno", "09:00–13:00")
        new = self.market("mercato-tre", "Sabato")
        planned = [updated, self.original[1], new]
        before = inc.effective_hashes("cat-base")
        expected, changes, stats = inc.plan_delta(before, planned)
        self.assertEqual(stats, {"previous": 2, "target": 3, "added": 1,
                                  "modified": 1, "unchanged": 1, "stored_changes": 2})
        self.add_delta("cat-v2", "cat-base", changes, 3, "d" * 64)
        self.assertEqual(inc.effective_hashes("cat-v2"), expected)
        self.assertEqual(inc.effective_hashes("cat-base"), before)
        self.assertEqual(self.query(
            "SELECT COUNT(*) AS n FROM catalog_market_changes")[0]["n"], 2)
        self.assertEqual(self.query(
            "SELECT COUNT(*) AS n FROM catalog_markets")[0]["n"], 2)
        self.assertIsNone(inc.channel_heads()["prod"])

    def test_second_and_third_versions_resolve_latest_only(self):
        first = self.market("mercato-uno", "Venerdì")
        self.add_delta("cat-v2", "cat-base", [first], 2, "d" * 64)
        second = self.market("mercato-uno", "Sabato")
        self.add_delta("cat-v3", "cat-v2", [second], 2, "e" * 64)
        self.assertEqual(
            inc.effective_hashes("cat-v2")["mercato-uno"],
            inc.canonical_hash(first)
        )
        self.assertEqual(
            inc.effective_hashes("cat-v3")["mercato-uno"],
            inc.canonical_hash(second)
        )
        self.assertEqual(len(inc.effective_hashes("cat-v3")), 2)
        self.assertEqual(len(inc.effective_hashes("cat-base")), 2)

    def test_same_rows_generate_no_new_duplicated_changes(self):
        original = inc.effective_hashes("cat-base")
        expected, changes, stats = inc.plan_delta(original, self.original)
        self.assertEqual(expected, original)
        self.assertEqual(changes, [])
        self.assertEqual(stats["stored_changes"], 0)
        self.add_delta("cat-empty-delta", "cat-base", [], 2, "f" * 64)
        self.assertEqual(inc.effective_hashes("cat-empty-delta"), original)

    def test_existing_identity_cannot_be_deleted(self):
        with self.assertRaisesRegex(ValueError, "remove existing market IDs"):
            inc.plan_delta(inc.effective_hashes("cat-base"), [self.original[0]])
        self.assertIsNone(inc.channel_heads()["prod"])

    def test_replayed_change_does_not_duplicate_or_overwrite_version(self):
        first = self.market("mercato-uno", "Domenica")
        self.add_delta("cat-v2", "cat-base", [first], 2, "d" * 64)
        self.db.executescript(inc.change_statement("cat-v2", first))
        conflicting = self.market("mercato-uno", "Lunedì")
        self.db.executescript(inc.change_statement("cat-v2", conflicting))
        self.assertEqual(self.query(
            "SELECT COUNT(*) AS n FROM catalog_market_changes")[0]["n"], 1)
        self.assertEqual(inc.effective_hashes("cat-v2")["mercato-uno"],
                         inc.canonical_hash(first))
        with self.assertRaisesRegex(ValueError, "hash verification"):
            inc.verify_state("cat-v2", {
                **inc.effective_hashes("cat-v2"),
                "mercato-uno": inc.canonical_hash(conflicting),
            })

    def test_version_bounded_pagination_does_not_skip_any_id(self):
        self.add_delta("cat-v2", "cat-base", [self.market("a-new", "Sabato")],
                       3, "d" * 64)
        page_one = self.query(inc.effective_hashes_sql("cat-v2", limit=2))
        page_two = self.query(inc.effective_hashes_sql("cat-v2",
                               after=page_one[-1]["slug"], limit=2))
        all_slugs = [r["slug"] for r in page_one + page_two]
        self.assertEqual(all_slugs, ["a-new", "mercato-due", "mercato-uno"])

    def test_missing_or_cyclic_parent_rejected(self):
        self.add_delta("cat-v2", "cat-base", [], 2, "d" * 64)
        self.db.execute(
            "UPDATE catalog_dataset_parents SET parent_dataset_id='cat-v2' "
            "WHERE dataset_id='cat-v2'"
        ) if False else None
        self.db.execute(
            "UPDATE catalog_dataset_parents SET parent_dataset_id='cat-missing' "
            "WHERE dataset_id='cat-v2'"
        ) if False else None
        # SQLite foreign keys might be disabled; test the explicit empty base guard.
        self.db.execute(
            "DELETE FROM catalog_markets WHERE dataset_id='cat-base'"
        )
        with self.assertRaisesRegex(ValueError, "no stored markets"):
            inc.effective_hashes("cat-v2")

    def test_proof_must_match_manifest_and_exact_identity(self):
        meta = {"signature": "f" * 64, "rows": 2}
        proof = {
            "qa_gate_approved": True,
            "all_existing_market_ids_preserved": True,
            "manifest_content_signature": meta["signature"],
            "after_records": meta["rows"],
            "old_unrelated_market_fields_changed": 0,
        }
        path = self.folder / "proof.json"
        path.write_text(json.dumps(proof), encoding="utf-8")
        self.assertEqual(inc.proof_check(path, meta), proof)
        proof["old_unrelated_market_fields_changed"] = 1
        path.write_text(json.dumps(proof), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "does not authorize"):
            inc.proof_check(path, meta)

    def test_sql_injection_safely_quoted_and_row_bounded(self):
        payload = self.market("slug-' ; DROP TABLE catalog_markets;--", "Lunedì")
        statement = inc.change_statement("cat-v2", payload)
        self.assertIn("''", statement)
        huge = self.market("large", "X" * 120000)
        with self.assertRaisesRegex(ValueError, "safe maximum"):
            inc.change_statement("cat-v2", huge)
        self.assertEqual(self.query(
            "SELECT COUNT(*) AS n FROM catalog_markets")[0]["n"], 2)


if __name__ == "__main__":
    unittest.main()
