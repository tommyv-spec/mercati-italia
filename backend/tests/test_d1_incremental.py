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
        # A version without an actual immutable base must be rejected.
        self.db.execute(
            "DELETE FROM catalog_markets WHERE dataset_id='cat-base'"
        )
        with self.assertRaisesRegex(ValueError, "no stored markets"):
            inc.effective_hashes("cat-v2")

    def test_original_git_provenance_is_immutable(self):
        self.add_delta("cat-v2", "cat-base", [], 2, "d" * 64)
        meta = {"id": "cat-v2", "signature": "d" * 64,
                "manifest_sha": "a" * 64, "git_sha": "c" * 40, "rows": 2}
        self.assertEqual(len(inc.dataset_record(meta, "cat-base")), 1)
        meta["git_sha"] = "f" * 40
        with self.assertRaisesRegex(ValueError, "was changed"):
            inc.dataset_record(meta, "cat-base")

    def test_unready_intermediate_version_cannot_serve_children(self):
        self.add_delta("cat-v2", "cat-base", [], 2, "d" * 64)
        self.add_delta("cat-v3", "cat-v2", [], 2, "e" * 64)
        self.db.execute(
            "UPDATE catalog_datasets SET status='loading' WHERE dataset_id='cat-v2'")
        with self.assertRaisesRegex(ValueError, "unready parent"):
            inc.effective_hashes("cat-v3")

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


    def release_files(self, rows):
        root = self.folder / "public/data/v1"
        (root / "regions").mkdir(parents=True, exist_ok=True)
        raw = (json.dumps({"schema": 1, "markets": rows}, ensure_ascii=False,
                          separators=(",", ":")) + "\n").encode("utf-8")
        hashed = base.digest(raw)[:14]
        (root / "regions" / ("test-" + hashed + ".json")).write_bytes(raw)
        manifest = root / "manifest.json"
        manifest.write_text(json.dumps({
            "schema": 1, "layout": "regional", "total": len(rows),
            "content_signature": "f" * 64,
            "regions": [{
                "path": "data/v1/regions/test-" + hashed + ".json",
                "count": len(rows),
            }],
        }), encoding="utf-8")
        proof = self.folder / "proof.json"
        proof.write_text(json.dumps({
            "qa_gate_approved": True,
            "all_existing_market_ids_preserved": True,
            "manifest_content_signature": "f" * 64,
            "after_records": len(rows),
            "old_unrelated_market_fields_changed": 0,
        }), encoding="utf-8")
        return manifest, proof

    def test_import_end_to_end_updates_dev_only_and_replay_is_noop(self):
        changed = self.market("mercato-uno", "09:00-12:00")
        added = self.market("mercato-tre", "15:00-18:00")
        manifest, proof = self.release_files([changed, self.original[1], added])
        log = self.folder / "checkpoint.json"
        written_statements = []

        def apply_file(file):
            self.db.executescript(Path(file).read_text(encoding="utf-8"))

        def import_chunks(statements, **kwargs):
            entries = list(statements)
            written_statements.extend(entries)
            for statement in entries:
                self.db.executescript(statement)
            return len(entries), len(entries)

        with (patch.object(inc, "validate", return_value={"records": 3}),
              patch.object(inc, "free_write_guard", return_value=None),
              patch.object(inc, "execute_file", side_effect=apply_file),
              patch.object(inc, "import_statements", side_effect=import_chunks)):
            planned = inc.run(manifest, "e" * 40, proof, log, dry_run=True)
            self.assertEqual(planned["stored_changes"], 2)
            self.assertEqual(inc.channel_heads()["dev"], "cat-base")
            result = inc.run(manifest, "e" * 40, proof, log)
            self.assertEqual(result["status"], "dev_incremental_imported")
            self.assertEqual(result["uploaded_in_this_run"], 2)
            self.assertEqual(inc.channel_heads()["dev"], result["dataset_id"])
            self.assertIsNone(inc.channel_heads()["prod"])
            self.assertEqual(len(written_statements), 2)
            self.assertEqual(self.query(
                "SELECT COUNT(*) AS n FROM catalog_markets")[0]["n"], 2)
            self.assertEqual(self.query(
                "SELECT COUNT(*) AS n FROM release_audit")[0]["n"], 1)
            again = inc.run(manifest, "e" * 40, proof, log)
            self.assertEqual(again["status"], "already_active")
            self.assertEqual(again["stored_changes"], 0)
            self.assertEqual(len(written_statements), 2)
            self.assertEqual(self.query(
                "SELECT COUNT(*) AS n FROM release_audit")[0]["n"], 1)

    def test_free_plan_guard_uses_current_24_hour_usage(self):
        with (patch.object(inc, "check_database_budget") as checked,
              patch.object(inc, "cli", return_value=json.dumps({
                  "rows_written_24h": 84899
              }))):
            with self.assertRaisesRegex(ValueError, "headroom exhausted"):
                inc.free_write_guard(100)
            self.assertTrue(checked.called)
        with (patch.object(inc, "check_database_budget") as checked,
              patch.object(inc, "cli", return_value=json.dumps({
                  "rows_written_24h": 60817
              }))):
            inc.free_write_guard(100)
            self.assertTrue(checked.called)


if __name__ == "__main__":
    unittest.main()
