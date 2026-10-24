"""Offline security tests for GH-approved DEV -> existing D1 bridge."""
from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import d1_dev_sync as mirror


class PublishedDevMirrorTests(unittest.TestCase):
    def setUp(self):
        self.signature = "d" * 64
        self.old_signature = "a" * 64
        self.git_sha = "e" * 40
        self.meta = {"id": "cat-" + self.signature[:28],
                     "signature": self.signature, "rows": 14039,
                     "git_sha": self.git_sha}
        self.decision = {
            "job_id": "40012405193",
            "approved": True, "base_signature": self.old_signature,
            "new_signature": self.signature,
            "old": {"records": 14007, "verified": 0},
            "candidate": {"records": 14039, "verified": 0},
            "validated": {"records": 14039},
            "removed_source_ids": 0, "dropped_source_evidence": [],
            "new_unreviewed_confirmations": [], "new_unreviewed_verifications": [],
            "unverified_confirmation_claims": [], "unexpected_verification_claims": [],
            "gates": {
                "forecast_60d": True, "forecast_quality_flags": True,
                "index_growth_budget": True, "index_under_absolute_budget": True,
                "max_new_records": True, "max_source_loss": True,
                "min_id_retention": True, "min_records": True,
                "never_upgrade_estimates_to_confirmed": True,
                "no_invented_human_verification": True,
                "no_unreviewed_new_confirmations": True,
                "no_unreviewed_new_verifications": True,
                "official_sources_available": True,
                "retain_old_source_evidence": True,
                "source_identities_immutable": True,
                "unavailable_official_sources_preserved": True,
                "unknown_source_share_budget": True
            }
        }
        self.quality = {
            "schema": 1, "review_only": True,
            "quality_release_safe": True, "quality_regressions": [],
            "market_updates_applied": 0, "market_confirmations_created": 0,
            "metrics": {"total": 14039, "future_date_quality_mismatch": 0}
        }

    def test_exact_autopilot_success_can_produce_bound_d1_proof(self):
        proof = mirror.preflight(
            self.decision, self.quality, None,
            meta=self.meta, previous_signature=self.old_signature
        )
        self.assertTrue(proof["qa_gate_approved"])
        self.assertTrue(proof["all_existing_market_ids_preserved"])
        self.assertEqual(proof["manifest_content_signature"], self.signature)
        self.assertEqual(proof["after_records"], 14039)
        self.assertEqual(proof["github_workflow_run_id"], "40012405193")

    def test_old_or_missing_source_proof_is_not_authorized(self):
        for field, bad in (
            ("approved", False),
            ("base_signature", "x" * 64),
            ("new_signature", "f" * 64),
            ("removed_source_ids", 1),
            ("new_unreviewed_confirmations", ["fake"]),
            ("dropped_source_evidence", [{"id": "missing"}]),
        ):
            with self.subTest(field=field):
                altered = copy.deepcopy(self.decision)
                altered[field] = bad
                with self.assertRaises(ValueError):
                    mirror.preflight(
                        altered, self.quality, None, meta=self.meta,
                        previous_signature=self.old_signature
                    )

    def test_untrusted_quality_report_still_blocks_database_write(self):
        for name, bad in (
            ("quality_release_safe", False),
            ("quality_regressions", [{"code": "new_unproven_duplicates"}]),
            ("market_confirmations_created", 1),
            ("review_only", False),
            ("metrics", {"total": 14008}),
        ):
            with self.subTest(field=name):
                q = copy.deepcopy(self.quality)
                q[name] = bad
                with self.assertRaises(ValueError):
                    mirror.preflight(
                        self.decision, q, None, meta=self.meta,
                        previous_signature=self.old_signature
                    )

    def test_source_gate_cannot_be_disabled_by_report_editor(self):
        altered = copy.deepcopy(self.decision)
        altered["gates"]["source_identities_immutable"] = False
        with self.assertRaises(ValueError):
            mirror.preflight(
                altered, self.quality, None, meta=self.meta,
                previous_signature=self.old_signature
            )

    def test_weekly_append_needs_exact_completed_publication_proof(self):
        initial = copy.deepcopy(self.decision)
        initial["candidate"]["records"] = 14007
        initial["validated"]["records"] = 14007
        initial["new_signature"] = "b" * 64
        prior_quality = copy.deepcopy(self.quality)
        prior_quality["metrics"]["total"] = 14007
        admission = {
            "status": "dev_published", "qa_gate_approved": True,
            "dev_published": True,
            "published_commit": self.git_sha,
            "manifest_signature": self.signature,
            "old_record_count": 14007, "new_record_count": 14039,
            "existing_market_ids_deleted": 0,
            "existing_market_non_calendar_fields_changed": 0,
            "source_claims_opening_verified": 0,
            "added_ids": [f"weekly-{n}" for n in range(32)],
        }
        result = mirror.preflight(
            initial, prior_quality, admission, meta=self.meta,
            previous_signature=self.old_signature
        )
        self.assertEqual(result["after_records"], 14039)
        for tampered in ("published_commit", "manifest_signature",
                         "old_record_count", "source_claims_opening_verified"):
            with self.subTest(field=tampered):
                bad = copy.deepcopy(admission)
                bad[tampered] = "wrong" if "commit" in tampered or "signature" in tampered else 1
                with self.assertRaises(ValueError):
                    mirror.preflight(
                        initial, prior_quality, bad, meta=self.meta,
                        previous_signature=self.old_signature
                    )

    def test_github_run_must_be_successful_and_from_trusted_main(self):
        run = {
            "conclusion": "success", "status": "completed", "head_branch": "main",
            "event": "schedule", "repository": {"full_name": mirror.REPO},
            "name": "Mercati Autopilot — scheduled DEV improvements",
        }
        with patch.object(mirror, "command", return_value=__import__("json").dumps(run)):
            self.assertEqual(mirror.verified_gha("40012405193")["conclusion"], "success")
        for key, wrong in (("conclusion", "failure"), ("head_branch", "fork"),
                           ("status", "in_progress"), ("event", "repository_dispatch")):
            with self.subTest(field=key):
                altered = {**run, key: wrong}
                with patch.object(mirror, "command", return_value=__import__("json").dumps(altered)):
                    with self.assertRaisesRegex(ValueError, "did not complete"):
                        mirror.verified_gha("40012405193")


    def test_already_mirrored_unchanged_data_uses_original_immutable_git_provenance(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory(prefix="d1-idempotent-") as folder:
            root = Path(folder)
            decision_file = root / "decision.json"
            quality_file = root / "quality.json"
            decision_file.write_text(json.dumps({"job_id": "40012405193"}), encoding="utf-8")
            quality_file.write_text("{}", encoding="utf-8")
            new_sha = self.git_sha
            old_sha = "f" * 40
            with (patch.object(mirror, "command", return_value=new_sha),
                  patch.object(mirror, "verified_git"),
                  patch.object(mirror, "verified_gha"),
                  patch.object(mirror, "dataset_meta", return_value=self.meta),
                  patch.object(mirror.incremental, "required_schema"),
                  patch.object(mirror, "d1_current_signature", return_value=self.signature),
                  patch.object(mirror, "remote_query", return_value=[{"source_git_sha": old_sha}]),
                  patch.object(mirror.incremental, "validate") as validation,
                  patch.object(mirror.incremental, "verify_existing") as exact_check,
                  patch.object(mirror.incremental, "run") as importer):
                response = mirror.sync(root, decision_file=decision_file,
                                       quality_file=quality_file, dry_run=False)
                self.assertEqual(response["status"], "already_mirrored")
                self.assertTrue(response["unchanged_data_new_git_sha"])
                self.assertEqual(exact_check.call_args.args[1], old_sha)
                validation.assert_called_once()
                importer.assert_not_called()

    def test_already_mirrored_rejects_invalid_original_git_source(self):
        import json
        import tempfile
        with tempfile.TemporaryDirectory(prefix="d1-idempotent-") as folder:
            root = Path(folder)
            (root / "decision.json").write_text(json.dumps({"job_id": "40012405193"}))
            (root / "quality.json").write_text("{}")
            with (patch.object(mirror, "command", return_value=self.git_sha),
                  patch.object(mirror, "verified_git"),
                  patch.object(mirror, "verified_gha"),
                  patch.object(mirror, "dataset_meta", return_value=self.meta),
                  patch.object(mirror.incremental, "required_schema"),
                  patch.object(mirror, "d1_current_signature", return_value=self.signature),
                  patch.object(mirror, "remote_query", return_value=[{"source_git_sha": "unknown"}])):
                with self.assertRaisesRegex(ValueError, "original Git source"):
                    mirror.sync(root, decision_file=root/"decision.json",
                                quality_file=root/"quality.json")


if __name__ == "__main__":
    unittest.main()
