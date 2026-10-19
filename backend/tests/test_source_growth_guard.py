"""Negative tests for the independent, read-only source-growth gate."""
import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_growth_guard import validate_growth_source_lifecycle
from source_lifecycle import digest
from publisher_snapshot_date import make_snapshot_date_proof, ODS_STRATEGY

ROOT = Path(__file__).resolve().parents[2]
CONTRACTS = json.loads((ROOT / "backend/data/market-source-contracts.json").read_text("utf-8"))
MANIFEST = json.loads((ROOT / "public/data/v1/manifest.json").read_text("utf-8"))
DAY = date(2026, 10, 19)


def dynamic_proof(profile, count):
    """Synthetic complete body and metadata, never a claim of a live read."""
    body = json.dumps({
        "nhits": count,
        "records": [{"datasetid": profile["api_dataset_id"],
                     "recordid": f"test-record-{i}",
                     "fields": {"denominazione": f"Mercato di prova {i}",
                                "ubicazione": f"Via di prova {i}",
                                "tipologia": "mercato periodico",
                                "tipologia_mercato": "periodico",
                                "giorni_svolgimento": "Martedì",
                                "orario_svolgimento": "07:30-13:00"}}
                    for i in range(count)],
    }).encode("utf-8")
    metadata = json.dumps({
        "dataset_id": profile["api_dataset_id"],
        "metas": {"default": {
            "license": profile["source_metadata_license"],
            "data_processed": "2026-10-18T12:00:00+00:00",
            "modified_updates_on_data_change": False,
            "records_count": 249,
        }},
    }).encode("utf-8")
    return make_snapshot_date_proof(
        profile, body, before_metadata=metadata, after_metadata=metadata,
        read_on=DAY.isoformat(), today=DAY)


def fixture():
    raw = [p for p in CONTRACTS["raw_profiles"] if p.get("enabled") is True]
    sources = {}
    for p in raw:
        observed = p["min_rows"]
        proof = (dynamic_proof(p, observed)
                 if p.get("source_date_strategy") == ODS_STRATEGY else None)
        sha = "a" * 64
        if proof is not None:
            sha = proof["snapshot_sha256"]
        sources[p["id"]] = {
            "schema": 1,
            "source_id": p["id"],
            "source_url": p["resource_url"],
            "publisher": p["publisher"],
            "profile_fingerprint": digest(p),
            "source_snapshot_sha256": sha,
            "counts": {"rows_observed": observed},
            "catalog_records_imported": 0,
            "individual_market_openings_verified": 0,
            "license_reviewed_for_automatic_publication": False,
            "source_data_marked_current_by_fetch_time": False,
            "source_stage": {
                "source_id": p["id"],
                "source_url": p["resource_url"],
                "profile_sha256": digest(p),
                "source_snapshot_sha256": sha,
                "source_kind": p["row_kind"],
                "publisher_dataset_date": (proof["source_date"] if proof is not None
                                           else p["source_dataset_date"]),
                "source_read_on": DAY.isoformat(),
                "publication_enabled": False,
                "source_license_automatically_verified": False,
                "verified_openings_created": 0,
                "existing_market_identities_deleted": 0,
                "existing_market_ids_modified": 0,
                "precise_coordinates_created": 0,
                "directions_enabled": 0,
                "counts": {"raw_rows_scanned": observed,
                           "source_market_identities": observed - 1},
                "review_reason_counts": {"duplicate_publisher_identity": 1},
                "safe_candidates_not_published": observed - 2,
            },
        }
        if proof is not None:
            sources[p["id"]]["source_stage"]["source_date_proof"] = proof
    return {
        "schema": 1, "source_contract_schema": 1, "read_only": True,
        "reference_date": DAY.isoformat(),
        "registry_sha256": digest(CONTRACTS),
        "catalog_count": MANIFEST["total"],
        "checked_source_profiles": len(sources),
        "source_checks": {"source_level_raw_profiles_checked": len(sources)},
        "sources": sources,
        "market_imports": 0, "market_updates": 0,
        "market_confirmations": 0, "market_identity_deletions": 0,
    }


class SourceGrowthAuditGateTests(unittest.TestCase):
    def check(self, report):
        return validate_growth_source_lifecycle(report, MANIFEST, root=ROOT)

    def test_pinned_publisher_registries_allow_two_authorized_sources(self):
        report = fixture()
        result = self.check(report)
        self.assertEqual(result["sources_checked"], 2)
        self.assertEqual(result["market_ids_preserved"], MANIFEST["total"])

    def test_dynamic_date_advances_with_proof_and_fixed_legacy_stage_needs_none(self):
        report = fixture()
        for p in CONTRACTS["raw_profiles"]:
            if p.get("enabled") is not True:
                continue
            staged = report["sources"][p["id"]]["source_stage"]
            if p.get("source_date_strategy") == ODS_STRATEGY:
                self.assertGreater(staged["publisher_dataset_date"], p["source_dataset_date"])
            else:
                self.assertNotIn("source_date_proof", staged)
                self.assertEqual(staged["publisher_dataset_date"], p["source_dataset_date"])
        self.check(report)

    def test_dynamic_stage_requires_proof_even_without_publication(self):
        report = fixture()
        staged = report["sources"]["bologna-generic-venues"]["source_stage"]
        self.assertIs(staged["publication_enabled"], False)
        staged.pop("source_date_proof")
        with self.assertRaisesRegex(ValueError, "dynamic source date proof"):
            self.check(report)

    def test_dynamic_date_hash_and_read_date_must_match_actual_proof(self):
        for field, value in (("publisher_dataset_date", "2026-10-19"),
                             ("source_snapshot_sha256", "b" * 64),
                             ("source_read_on", "2026-10-18")):
            report = fixture()
            row = report["sources"]["bologna-generic-venues"]
            row["source_stage"][field] = value
            if field == "source_snapshot_sha256":
                row[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                self.check(report)

    def test_dynamic_read_is_checked_against_lifecycle_reference_date(self):
        report = fixture()
        report["reference_date"] = "2026-10-18"
        with self.assertRaisesRegex(ValueError, "read date is in the future"):
            self.check(report)
        for value in (None, "20261019", "2026-02-30", DAY, 20261019):
            report = fixture()
            report["reference_date"] = value
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "reference date"):
                self.check(report)

    def test_a_new_unapproved_source_is_not_auto_approved(self):
        report = fixture()
        report["sources"]["unreviewed-venue-feed"] = {}
        report["checked_source_profiles"] += 1
        with self.assertRaisesRegex(ValueError, "enabled publisher"):
            self.check(report)

    def test_missing_enabled_source_is_not_silently_ignored(self):
        report = fixture()
        report["sources"].pop(next(iter(report["sources"])))
        report["checked_source_profiles"] -= 1
        with self.assertRaisesRegex(ValueError, "enabled publisher"):
            self.check(report)

    def test_forged_individual_verification_is_rejected(self):
        for key, val in [
            ("market_imports", 1),
            ("market_confirmations", 1),
        ]:
            report = fixture()
            report[key] = val
            with self.subTest(field=key), self.assertRaises(ValueError):
                self.check(report)
        report = fixture()
        row = next(iter(report["sources"].values()))
        row["source_stage"]["verified_openings_created"] = 1
        with self.assertRaisesRegex(ValueError, "read-only staging"):
            self.check(report)

    def test_forged_geocoordinates_and_unapproved_source_fields_rejected(self):
        report = fixture()
        row = next(iter(report["sources"].values()))
        row["source_stage"]["precise_coordinates_created"] = 1
        with self.assertRaisesRegex(ValueError, "read-only staging"):
            self.check(report)
        report = fixture()
        row = next(iter(report["sources"].values()))
        row["source_data_marked_current_by_fetch_time"] = True
        with self.assertRaisesRegex(ValueError, "falsely certified"):
            self.check(report)

    def test_stage_must_match_actual_publisher_rows_and_hash(self):
        report = fixture()
        row = next(iter(report["sources"].values()))
        row["source_stage"]["counts"]["raw_rows_scanned"] = 99
        with self.assertRaisesRegex(ValueError, "source rows"):
            self.check(report)
        report = fixture()
        row = next(iter(report["sources"].values()))
        row["source_stage"]["profile_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "read-only staging"):
            self.check(report)

    def test_transport_outage_preserves_old_snapshot_but_not_false_freshness(self):
        report = fixture()
        row = next(iter(report["sources"].values()))
        row.update({"stale_snapshot_carry_forward": True,
                    "last_check_status": "transport_unavailable"})
        self.check(report)
        row["last_check_status"] = "contract_change_needs_review"
        with self.assertRaises(ValueError):
            self.check(report)

    def test_first_read_transport_outage_not_mistaken_for_missing_market(self):
        report = fixture()
        sid = next(iter(report["sources"]))
        profile = next(p for p in CONTRACTS["raw_profiles"] if p["id"] == sid)
        report["sources"][sid] = {
            "schema": 1, "source_id": sid, "publisher": profile["publisher"],
            "source_url": profile["resource_url"],
            "unavailable_no_market_inference": True,
            "last_check_status": "transport_unavailable", "fingerprints": {},
        }
        self.check(report)

    def test_contract_snapshot_pin_does_not_accept_rewritten_registry(self):
        report = fixture()
        policy = ROOT / "backend/autopilot_policy.json"
        text = policy.read_text("utf-8")
        self.assertIn('"reviewed_contract_blob_sha1"', text)
        # Tamper the on-disk contract only in a temporary sandbox.
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            dst = Path(tmp) / "backend"
            (dst / "data").mkdir(parents=True)
            (dst / "autopilot_policy.json").write_text(text, "utf-8")
            for name in ("market-source-contracts.json", "approved-source-admissions.json"):
                original = (ROOT / "backend/data" / name).read_text("utf-8")
                (dst / "data" / name).write_text(original + "\n", "utf-8")
            with self.assertRaisesRegex(ValueError, "Unreviewed changes"):
                validate_growth_source_lifecycle(report, MANIFEST, root=Path(tmp))


if __name__ == "__main__":
    unittest.main()
