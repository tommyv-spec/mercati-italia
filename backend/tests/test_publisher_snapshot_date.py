"""Synthetic snapshots only: no publisher request or real update is asserted."""
import base64
import copy
import hashlib
import json
from pathlib import Path
import sys
import unittest
from datetime import date

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from publisher_snapshot_date import (
    FIXED_STRATEGY, ODS_STRATEGY, MAX_METADATA_BYTES,
    validate_strategy, make_snapshot_date_proof, resolve_source_date,
)


TODAY = date(2026, 10, 19)
DATASET_ID = "synthetic-markets"


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")


def profile(*, filtered=True):
    return {
        "id": "synthetic-test-only", "publisher": "TEST publisher",
        "format": "JSON", "json_container": "opendatasoft_v1",
        "api_dataset_id": DATASET_ID,
        "resource_url": ("https://publisher.example/api/records/1.0/search/"
                         f"?dataset={DATASET_ID}&rows=3" + ("&q=type%3Amarket" if filtered else "")),
        "source_metadata_url": ("https://publisher.example/api/explore/v2.1/catalog/datasets/"
                                + DATASET_ID),
        "source_metadata_license": "CC BY 4.0",
        "source_date_strategy": ODS_STRATEGY,
        "source_dataset_date": "2025-04-02",
        "min_rows": 1, "max_rows": 3, "max_bytes": 65536,
    }


def body(*, count=2):
    return encoded({"nhits": count, "records": [
        {"datasetid": DATASET_ID, "recordid": f"synthetic-{n}",
         "fields": {"name": f"TEST venue {n}"}} for n in range(count)
    ]})


def metadata(*, timestamp="2025-04-02T14:33:42+00:00", count=5, **changes):
    default = {
        "license": "CC BY 4.0", "data_processed": timestamp,
        "modified": "2026-10-19T12:31:56+00:00",
        "modified_updates_on_data_change": False, "records_count": count,
    }
    default.update(changes)
    return encoded({"dataset_id": DATASET_ID, "metas": {"default": default}})


def proof_for(p=None, blob=None, before=None, after=None, *, read_on="2026-10-19"):
    p = profile() if p is None else p
    blob = body() if blob is None else blob
    before = metadata() if before is None else before
    after = before if after is None else after
    return make_snapshot_date_proof(p, blob, before_metadata=before,
                                    after_metadata=after, read_on=read_on, today=TODAY)


class PublisherSnapshotDateTests(unittest.TestCase):
    def test_legacy_fixed_date_is_not_changed_by_a_later_read(self):
        for strategy in (None, FIXED_STRATEGY):
            with self.subTest(strategy=strategy):
                p = {"source_dataset_date": "2025-04-02"}
                if strategy is not None:
                    p["source_date_strategy"] = strategy
                self.assertEqual(validate_strategy(p), FIXED_STRATEGY)
                self.assertEqual(resolve_source_date(p, read_on="2026-10-19", today=TODAY),
                                 "2025-04-02")
                with self.assertRaisesRegex(ValueError, "cannot override"):
                    resolve_source_date(p, proof=proof_for(), today=TODAY)
                with self.assertRaisesRegex(ValueError, "Fixed reviewed"):
                    proof_for(p)

    def test_invalid_strategy_or_reviewed_minimum_fails(self):
        for value in (None, "", "today", "modified", True, {}):
            with self.subTest(strategy=value):
                p = profile()
                p["source_date_strategy"] = value
                with self.assertRaises(ValueError):
                    validate_strategy(p)
        for value in (None, "2025-4-2", "2025-04-02T00:00:00Z", "2025-02-30"):
            with self.subTest(minimum=value):
                p = profile()
                p["source_dataset_date"] = value
                with self.assertRaises(ValueError):
                    validate_strategy(p)

    def test_metadata_contract_is_same_reviewed_endpoint_and_format(self):
        changes = [
            {"source_metadata_url": "https://elsewhere.example/api/explore/v2.1/catalog/datasets/" + DATASET_ID},
            {"source_metadata_url": profile()["source_metadata_url"] + "/"},
            {"source_metadata_url": profile()["source_metadata_url"] + "?q=arbitrary"},
            {"source_metadata_url": profile()["source_metadata_url"].replace("https://", "http://")},
            {"resource_url": profile()["resource_url"] + "&dataset=another"},
            {"resource_url": profile()["resource_url"] + "&start=1"},
            {"resource_url": profile()["resource_url"] + "&q=second"},
            {"source_metadata_license": ""}, {"api_dataset_id": "../other"},
            {"format": "CSV"}, {"json_container": "records"},
            {"min_rows": True}, {"max_rows": 0}, {"max_bytes": 65537},
        ]
        for change in changes:
            with self.subTest(change=change):
                p = profile()
                p.update(change)
                with self.assertRaises(ValueError):
                    validate_strategy(p)

    def test_new_read_and_metadata_modified_do_not_refresh_old_content(self):
        p, blob = profile(), body()
        original = copy.deepcopy(p)
        proof = proof_for(p, blob)
        self.assertEqual(proof["source_date"], "2025-04-02")
        self.assertEqual(proof["read_on"], "2026-10-19")
        self.assertEqual(proof["snapshot_sha256"], hashlib.sha256(blob).hexdigest())
        self.assertEqual(proof["dataset_records_count"], 5)
        self.assertEqual(proof["snapshot_records_count"], 2)
        self.assertEqual(resolve_source_date(p, proof=proof, blob=blob, today=TODAY), "2025-04-02")
        self.assertEqual(p, original)
        self.assertNotIn("verificato_il", proof)

    def test_updated_publisher_content_has_new_date_without_profile_mutation(self):
        p = profile()
        proof = proof_for(p, before=metadata(timestamp="2026-10-18T09:10:11.123456Z"))
        self.assertEqual(proof["source_date"], "2026-10-18")
        self.assertEqual(proof["data_processed_timestamp"], "2026-10-18T09:10:11.123456+00:00")
        self.assertEqual(p["source_dataset_date"], "2025-04-02")

    def test_same_day_timestamp_race_and_fractional_race_are_rejected(self):
        for later in ("2025-04-02T15:33:42+00:00", "2025-04-02T14:33:42.000001Z"):
            with self.subTest(later=later), self.assertRaisesRegex(ValueError, "changed during"):
                proof_for(after=metadata(timestamp=later))
        with self.assertRaisesRegex(ValueError, "changed during"):
            proof_for(after=metadata(count=6))

    def test_equivalent_explicit_timezones_are_same_instant(self):
        proof = proof_for(after=metadata(timestamp="2025-04-02T16:33:42+02:00"))
        self.assertEqual(proof["source_date"], "2025-04-02")
        self.assertNotEqual(proof["before_metadata_sha256"], proof["after_metadata_sha256"])

    def test_unrelated_metadata_modified_may_change_without_claiming_new_data(self):
        proof = proof_for(after=metadata(modified="2026-10-19T23:59:00Z"))
        self.assertEqual(proof["source_date"], "2025-04-02")
        self.assertEqual(resolve_source_date(profile(), proof=proof, blob=body(), today=TODAY),
                         "2025-04-02")

    def test_timestamp_requires_known_timezone_and_no_silent_precision_loss(self):
        for value in (
            None, "2025-04-02", "2025-04-02T14:33:42", "2025-04-02 14:33:42Z",
            "2025-04-02T14:33:42.1234567Z", "2025-04-02T14:33:42+00:60",
            "2025-04-02T14:33:42-00:00", "2025-04-02T25:33:42Z",
            "2025-02-30T14:33:42Z",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                proof_for(before=metadata(timestamp=value))

    def test_source_date_cannot_precede_minimum_or_follow_read_or_reference_date(self):
        for value in ("2025-04-01T23:59:59Z", "2026-10-20T00:00:00Z"):
            with self.subTest(value=value), self.assertRaisesRegex(ValueError, "future or precedes"):
                proof_for(before=metadata(timestamp=value))
        with self.assertRaisesRegex(ValueError, "future or precedes"):
            proof_for(before=metadata(timestamp="2026-10-19T12:00:00Z"), read_on="2026-10-18")
        with self.assertRaisesRegex(ValueError, "read date is in the future"):
            proof_for(read_on="2026-10-20")

    def test_license_semantics_and_dataset_identity_are_checked_in_both_reads(self):
        bad = json.loads(metadata())
        bad["dataset_id"] = "other-dataset"
        variants = [encoded(bad), metadata(license="UNKNOWN"),
                    metadata(modified_updates_on_data_change=True),
                    metadata(modified_updates_on_data_change=None),
                    metadata(count=True), metadata(count=-1)]
        for raw in variants:
            for side in ("before", "after"):
                with self.subTest(side=side, raw=raw), self.assertRaises(ValueError):
                    proof_for(**{side: raw})

    def test_filtered_snapshot_count_is_not_entire_dataset_count(self):
        proof = proof_for(before=metadata(count=249))
        self.assertEqual(proof["snapshot_records_count"], 2)
        self.assertEqual(proof["dataset_records_count"], 249)
        with self.assertRaisesRegex(ValueError, "counts do not match"):
            proof_for(before=metadata(count=1))

    def test_unfiltered_snapshot_must_account_for_entire_dataset(self):
        p = profile(filtered=False)
        self.assertEqual(proof_for(p, before=metadata(count=2))["dataset_records_count"], 2)
        with self.assertRaisesRegex(ValueError, "counts do not match"):
            proof_for(p)

    def test_partial_mixed_dataset_and_out_of_bounds_snapshots_are_rejected(self):
        variants = []
        short = json.loads(body())
        short["nhits"] = 3
        variants.append(encoded(short))
        mixed = json.loads(body())
        mixed["records"][0]["datasetid"] = "wrong-dataset"
        variants.append(encoded(mixed))
        for value in (True, 2.0, "2"):
            invalid = json.loads(body())
            invalid["nhits"] = value
            variants.append(encoded(invalid))
        variants.extend((body(count=0), body(count=4)))
        for raw in variants:
            with self.subTest(raw=raw), self.assertRaises(ValueError):
                proof_for(blob=raw)

    def test_bytes_and_json_are_bounded_and_unambiguous(self):
        for raw in (b"", b"x" * (MAX_METADATA_BYTES + 1), b"\xff", b"[]", b"{",
                    b'{"dataset_id":"one","dataset_id":"two"}', b'{"value":NaN}'):
            with self.subTest(raw=raw[:30]), self.assertRaises(ValueError):
                proof_for(before=raw)
        for raw in ("not bytes", b"x" * 65537,
                    b'{"nhits":2,"nhits":2,"records":[]}'):
            with self.subTest(raw=str(raw)[:30]), self.assertRaises(ValueError):
                proof_for(blob=raw)

    def test_guard_replay_requires_independently_retained_snapshot_hash(self):
        p, proof = profile(), proof_for()
        with self.assertRaisesRegex(ValueError, "independent source snapshot"):
            resolve_source_date(p, proof=proof, today=TODAY)
        self.assertEqual(resolve_source_date(p, proof=proof,
                         snapshot_sha256=hashlib.sha256(body()).hexdigest(),
                         read_on="2026-10-19", today=TODAY), "2025-04-02")
        with self.assertRaisesRegex(ValueError, "does not match"):
            resolve_source_date(p, proof=proof, snapshot_sha256="0" * 64, today=TODAY)
        with self.assertRaisesRegex(ValueError, "does not match the body"):
            resolve_source_date(p, proof=proof, blob=body(), snapshot_sha256="0" * 64, today=TODAY)

    def test_cached_proof_does_not_acquire_a_new_read_date(self):
        p, proof = profile(), proof_for()
        frozen = copy.deepcopy(proof)
        self.assertEqual(resolve_source_date(p, proof=proof, blob=body(),
                         today=date(2026, 10, 20)), "2025-04-02")
        with self.assertRaisesRegex(ValueError, "read date changed"):
            resolve_source_date(p, proof=proof, blob=body(), read_on="2026-10-20",
                                today=date(2026, 10, 20))
        self.assertEqual(proof, frozen)

    def test_proof_cannot_be_transferred_to_changed_body_or_profile(self):
        p, proof = profile(), proof_for()
        changed = json.loads(body())
        changed["records"][0]["fields"]["name"] = "TEST next value"
        with self.assertRaisesRegex(ValueError, "does not match"):
            resolve_source_date(p, proof=proof, blob=encoded(changed), today=TODAY)
        for key, value in (("publisher", "Other publisher"), ("id", "other-source"),
                           ("source_dataset_date", "2025-04-01")):
            other = copy.deepcopy(p)
            other[key] = value
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "does not match"):
                resolve_source_date(other, proof=proof, blob=body(), today=TODAY)

    def test_each_derived_proof_field_is_rechecked(self):
        proof = proof_for()
        changes = {
            "schema": True, "strategy": FIXED_STRATEGY,
            "profile_sha256": "0" * 64, "source_url": "https://other.example/",
            "snapshot_sha256": "0" * 64, "metadata_url": "https://other.example/",
            "dataset_id": "other-dataset", "read_on": "2026-10-20",
            "source_date": "2026-10-19", "data_processed_timestamp": "2026-10-19T12:00:00Z",
            "dataset_records_count": True, "snapshot_records_count": True,
            "before_metadata_sha256": "0" * 64, "after_metadata_sha256": "0" * 64,
        }
        for key, value in changes.items():
            changed = copy.deepcopy(proof)
            changed[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                resolve_source_date(profile(), proof=changed, blob=body(), today=TODAY)
        for changed in (None, {}, {**proof, "arbitrary_authorization": True}):
            with self.subTest(changed=str(changed)[:50]), self.assertRaises(ValueError):
                resolve_source_date(profile(), proof=changed, blob=body(), today=TODAY)

    def test_metadata_bytes_cannot_be_changed_even_with_a_new_hash(self):
        proof = proof_for()
        raw = metadata(license="changed license")
        proof["after_metadata_base64"] = base64.b64encode(raw).decode("ascii")
        proof["after_metadata_sha256"] = hashlib.sha256(raw).hexdigest()
        with self.assertRaisesRegex(ValueError, "license changed"):
            resolve_source_date(profile(), proof=proof, blob=body(), today=TODAY)

    def test_encoded_metadata_bounds_and_base64_are_checked_during_replay(self):
        for value in ("%%%", "A" * (4 * ((MAX_METADATA_BYTES + 2) // 3) + 4),
                      base64.b64encode(metadata()).decode("ascii") + "\n"):
            proof = proof_for()
            proof["before_metadata_base64"] = value
            with self.subTest(value=value[:30]), self.assertRaises(ValueError):
                resolve_source_date(profile(), proof=proof, blob=body(), today=TODAY)


if __name__ == "__main__":
    unittest.main()
