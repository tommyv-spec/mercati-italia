"""Synthetic ODS snapshots exercise the complete generic refresh boundary.

No fixture in this module was fetched from a live publisher. The Bologna
contract supplies a reusable format; IDs, venues, bodies, timestamps and
admission certificates below are deliberately synthetic. Every activation
uses a transport double that checks metadata -> body -> metadata ordering.
"""
import copy
import hashlib
import json
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, call

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from export_static import export
from merge_catalog import load_existing
from publisher_snapshot_date import make_snapshot_date_proof
from recurrence_refresh import explicit_rule, forecast_source_limits, refresh_records
from source_contract_activation import activate, validate_release, verify_static
from source_contract_ingest import apply_approved, stage, verify_update
from source_lifecycle import digest


DATA_DIR = Path(__file__).resolve().parents[1] / "data"
BASE_CONFIG = json.loads((DATA_DIR / "market-source-contracts.json").read_text("utf-8"))
TODAY = date(2026, 10, 19)
OLD_DATA_DAY = "2025-04-02"
DATASET = "mercati-e-fiere"
RECORD_IDS = ("1" * 40, "2" * 40)


def synthetic_profile():
    profile = copy.deepcopy(next(
        item for item in BASE_CONFIG["raw_profiles"]
        if item["id"] == "bologna-generic-venues"
    ))
    profile.update({
        "id": "fixture-bologna-dynamic",
        "publisher": "Publisher sintetico per test ODS",
        "catalog_slug_prefix": "fixture-ods-",
        "min_rows": 2,
        "max_rows": 2,
        "max_new_ids_per_run": 2,
        "source_dataset_date": OLD_DATA_DAY,
        "source_date_strategy": "opendatasoft_data_processed_v1",
        "source_metadata_url": (
            "https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/"
            + DATASET
        ),
        "source_metadata_license": "CC BY 4.0",
        "notes": "Entirely synthetic integration fixture; never a live publisher observation.",
    })
    return profile


def certificate(profile):
    return {
        "schema": 1,
        "mode": "approved_dev_only",
        "source_id": profile["id"],
        "reviewed_profile_sha256": digest(profile),
        "publisher_license_evidence_url": profile["attribution_url"],
        "identity_granularity": profile["row_kind"],
        "reviewed_on": "2026-10-18",
        "max_new_ids": 2,
        "source_record_kind": profile["row_kind"],
        "source_specific_geo_approval": False,
    }


def configured(*profiles):
    profiles = profiles or (synthetic_profile(),)
    config = {
        "schema": 1,
        "publication_role": "review_only",
        "normalized_profiles": [],
        "raw_profiles": list(profiles),
    }
    registry = {
        "schema": 1,
        "publication_channel": "dev-only",
        "user_event_confirmations_allowed": False,
        "approvals": [certificate(profile) for profile in profiles],
    }
    return config, registry


def body(*, address="Via Fittizia Alfa", hours="08:00-13:00", weekday="mercoledì", dataset=DATASET):
    values = (
        ("Fittizio Alfa", address, weekday, hours),
        ("Fittizio Beta", "Piazza Fittizia Beta", "venerdì", "07:30-12:30"),
    )
    records = [{
        "datasetid": dataset,
        "recordid": record_id,
        "fields": {
            "denominazione": name,
            "ubicazione": venue,
            "tipologia": "mercato",
            "tipologia_mercato": "rionale",
            "giorni_svolgimento": weekday,
            "orario_svolgimento": opening,
        },
    } for record_id, (name, venue, weekday, opening) in zip(RECORD_IDS, values)]
    return json.dumps({"nhits": len(records), "records": records},
                      ensure_ascii=False, sort_keys=True).encode("utf-8")


def metadata(processed, *, dataset=DATASET, editorial_day=TODAY.isoformat()):
    # The source query is filtered. The global dataset is allowed to contain
    # more records, but its count must never be smaller than the full response.
    return json.dumps({
        "dataset_id": dataset,
        "metas": {"default": {
            "title": "Synthetic market inventory for integration tests",
            "license": "CC BY 4.0",
            "data_processed": processed,
            "metadata_processed": editorial_day + "T16:00:00+02:00",
            "modified": editorial_day + "T16:00:00+02:00",
            "modified_updates_on_data_change": False,
            "records_count": 80,
        }},
    }, sort_keys=True).encode("utf-8")


def sequence_transport(*steps):
    sequence = iter(steps)

    def fetch(url):
        expected_url, payload = next(sequence)
        if url != expected_url:
            raise AssertionError(f"Unexpected synthetic fetch order: {url!r} != {expected_url!r}")
        return payload, False

    return Mock(side_effect=fetch)


def snapshot_steps(profile, blob, before, after=None):
    return (
        (profile["source_metadata_url"], before),
        (profile["resource_url"], blob),
        (profile["source_metadata_url"], before if after is None else after),
    )


def baseline():
    return [{
        "slug": "fixture-unrelated-firenze",
        "nome": "Mercato fittizio esterno",
        "citta": "Firenze",
        "provincia": "FI",
        "regione": "Toscana",
        "indirizzo": "Piazza Fittizia Esterna",
        "status": "non_confermato",
    }]


class DynamicSourceRefreshIntegrationTests(unittest.TestCase):
    def fixture_read(self, config, registry, existing, blob, meta, *, day=TODAY, **kwargs):
        profile = config["raw_profiles"][0]
        steps = snapshot_steps(profile, blob, meta)
        fetch = sequence_transport(*steps)
        result, report = activate(config, registry, existing, today=day,
                                  read_on=day.isoformat(), fetch=fetch, **kwargs)
        self.assertEqual(fetch.call_args_list, [call(url) for url, _ in steps])
        self.assertEqual(report["per_source"][profile["id"]]["status"],
                         "source_contract_approved_staged_only")
        return result, report

    def roundtrip(self, records, report, config, registry, path, *, day=TODAY):
        projected, _ = refresh_records(records, day, 120, 540,
                                        source_limits=forecast_source_limits(config))
        preserve = set(report["new_market_ids"]) | set(report["evidence_updated_market_ids"])
        export(projected, path, today=day, min_count=1, preserve_ids=preserve)
        self.assertTrue(verify_static(path / "manifest.json", report, config, registry, day)
                        ["release_safe"])
        return load_existing(path / "manifest.json")

    def test_editorial_processing_today_does_not_rejuvenate_old_publisher_data(self):
        config, registry = configured()
        profile = config["raw_profiles"][0]
        blob = body()
        meta = metadata(OLD_DATA_DAY + "T10:30:00+02:00")
        result, report = self.fixture_read(config, registry, baseline(), blob, meta)
        observed = report["per_source"][profile["id"]]["source_observations"]
        self.assertEqual(observed["publisher_dataset_date"], OLD_DATA_DAY)
        self.assertEqual(observed["source_date_proof"]["source_date"], OLD_DATA_DAY)
        self.assertEqual(observed["source_date_proof"]["read_on"], TODAY.isoformat())
        self.assertEqual(observed["source_date_proof"]["snapshot_sha256"],
                         hashlib.sha256(blob).hexdigest())
        self.assertEqual(len(report["new_market_ids"]), 2)
        for record in result[1:]:
            self.assertEqual(record["aggiornato_il"], OLD_DATA_DAY)
            self.assertEqual(record["fonte_aggiornata_il"], OLD_DATA_DAY)
            self.assertEqual(record["fonte_letta_il"], TODAY.isoformat())
            self.assertEqual(record["riscontri_campi"][0]["fonte_aggiornata_il"], OLD_DATA_DAY)
            self.assertEqual(record["ricorrenza_testo"], "Calendario da verificare")
        self.assertTrue(validate_release(baseline(), result, report, config, registry)["release_safe"])
        with TemporaryDirectory() as temporary:
            final = self.roundtrip(result, report, config, registry,
                                   Path(temporary) / "public/data/v1")
        for record in final:
            if record["slug"] in report["new_market_ids"]:
                self.assertEqual(record["date_quality"], "sconosciuta")
                self.assertEqual(record["date"], [])
                self.assertFalse(record["verificato_il"])

    def test_new_source_id_owns_fields_and_second_snapshot_updates_them_after_export(self):
        config, registry = configured()
        profile = config["raw_profiles"][0]
        first, one = self.fixture_read(config, registry, baseline(), body(),
                                      metadata("2026-10-18T08:00:00+00:00"))
        market_id = profile["catalog_slug_prefix"] + RECORD_IDS[0]
        first_record = next(row for row in first if row["slug"] == market_id)
        first_receipt = first_record["riscontri_campi"][0]
        self.assertEqual(first_receipt["gestore_campi"], "source_contract_ingest")
        self.assertEqual(set(first_receipt["campi_gestiti"]),
                         {"indirizzo", "orario_testo", "ricorrenza_testo"})
        tomorrow = TODAY + timedelta(days=1)
        changed = body(address="Piazza Fittizia Nuova", hours="09:00-14:30")
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "public/data/v1"
            before = self.roundtrip(first, one, config, registry, path)
            second, two = self.fixture_read(
                config, registry, before, changed,
                metadata("2026-10-20T08:00:00+00:00", editorial_day=tomorrow.isoformat()),
                day=tomorrow,
            )
            self.assertEqual([row["slug"] for row in second], [row["slug"] for row in before])
            self.assertEqual(two["new_market_ids"], [])
            self.assertEqual(two["updated_market_ids"], [market_id])
            self.assertEqual(two["old_market_fields_changed"], 2)
            self.assertTrue(validate_release(before, second, two, config, registry)["release_safe"])
            final = self.roundtrip(second, two, config, registry, path, day=tomorrow)
        actual = next(row for row in final if row["slug"] == market_id)
        self.assertEqual(actual["indirizzo"], "Piazza Fittizia Nuova")
        self.assertEqual(actual["orario_testo"], "09:00–14:30 (da verificare con il Comune)")
        self.assertEqual(actual["fonte_aggiornata_il"], tomorrow.isoformat())
        newest = next(receipt for receipt in actual["riscontri_campi"]
                      if receipt["fonte_aggiornata_il"] == tomorrow.isoformat())
        self.assertEqual(newest["gestore_campi"], "source_contract_ingest")
        self.assertTrue(newest["versioni_precedenti"])
        observation = two["per_source"][profile["id"]]["source_observations"]
        self.assertEqual(observation["publisher_dataset_date"], tomorrow.isoformat())
        update = next(item for item in two["per_source"][profile["id"]]["updates"]
                      if item["slug"] == market_id)
        prior = next(row for row in before if row["slug"] == market_id)
        after = next(row for row in second if row["slug"] == market_id)
        self.assertEqual(verify_update(profile, prior, after, update, today=tomorrow,
                                       source_observations=observation), 2)
        with self.assertRaises(ValueError):
            verify_update(profile, prior, after, update, today=tomorrow)

    def test_identical_preexisting_values_are_observed_without_becoming_managed(self):
        config, registry = configured()
        profile = config["raw_profiles"][0]
        seed, _ = self.fixture_read(config, registry, baseline(), body(),
                                   metadata("2026-10-18T08:00:00Z"))
        market_id = profile["catalog_slug_prefix"] + RECORD_IDS[0]
        existing = copy.deepcopy(seed)
        target = next(row for row in existing if row["slug"] == market_id)
        # Model a historical source record published before managed receipts.
        for field in ("riscontri_campi", "importato_il", "fonte_letta_il", "fonte_aggiornata_il"):
            target.pop(field, None)
        observed, report = self.fixture_read(config, registry, existing, body(),
                                            metadata("2026-10-19T08:00:00Z"))
        target_after = next(row for row in observed if row["slug"] == market_id)
        self.assertEqual(report["old_market_fields_changed"], 0)
        self.assertTrue(target_after["riscontri_campi"])
        for receipt in target_after["riscontri_campi"]:
            self.assertNotIn("campi_gestiti", receipt)
            self.assertNotIn("gestore_campi", receipt)
        tomorrow = TODAY + timedelta(days=1)
        changed = body(address="Via Fittizia Non Autorizzata", hours="09:00-15:00")
        meta = metadata("2026-10-20T08:00:00Z", editorial_day=tomorrow.isoformat())
        fetch = sequence_transport(*snapshot_steps(profile, changed, meta))
        result, held = activate(config, registry, observed, today=tomorrow,
                                read_on=tomorrow.isoformat(), fetch=fetch)
        after = next(row for row in result if row["slug"] == market_id)
        self.assertEqual(after["indirizzo"], target_after["indirizzo"])
        self.assertEqual(after["orario_testo"], target_after["orario_testo"])
        self.assertEqual([row["slug"] for row in result], [row["slug"] for row in observed])
        self.assertEqual(held["old_market_fields_changed"], 0)
        self.assertEqual(held["per_source"][profile["id"]]["status"], "publisher_source_held_for_review")
        self.assertTrue(validate_release(observed, result, held, config, registry)["release_safe"])
        self.assertTrue(all(not receipt.get("campi_gestiti")
                            for receipt in after.get("riscontri_campi", [])))

    def test_cached_replay_preserves_date_and_exact_proof_without_network(self):
        config, registry = configured()
        profile = config["raw_profiles"][0]
        with TemporaryDirectory() as temporary:
            first, one = self.fixture_read(config, registry, baseline(), body(),
                                          metadata("2026-10-18T08:00:00Z"),
                                          source_cache=temporary)
            checkpoints = [path for path in Path(temporary).glob("*.json")
                           if path.name != "context.json"]
            self.assertEqual(len(checkpoints), 1)
            path = checkpoints[0]
            saved_bytes = path.read_bytes()
            saved = json.loads(saved_bytes)
            original_proof = one["per_source"][profile["id"]]["source_observations"]["source_date_proof"]
            self.assertEqual(saved["source_date_proof"], original_proof)
            no_network = Mock(side_effect=AssertionError("Cached fixture must not access the network"))
            for resume, offline in ((True, False), (True, True), (False, False)):
                with self.subTest(resume=resume, offline=offline):
                    replay, report = activate(config, registry, baseline(), today=TODAY,
                        read_on=(TODAY + timedelta(days=1)).isoformat(), source_cache=temporary,
                        resume=resume, offline=offline, fetch=no_network)
                    self.assertEqual(replay, first)
                    source = report["per_source"][profile["id"]]
                    self.assertEqual(source["source_read_on"], TODAY.isoformat())
                    self.assertEqual(source["source_observations"]["source_date_proof"], original_proof)
                    self.assertEqual(path.read_bytes(), saved_bytes)
            no_network.assert_not_called()

    def test_current_address_and_hours_without_weekday_do_not_rejuvenate_old_calendar(self):
        config, registry = configured()
        profile = config["raw_profiles"][0]
        historic_day = date(2025, 4, 3)
        registry["approvals"][0]["reviewed_on"] = historic_day.isoformat()
        first, _ = self.fixture_read(
            config, registry, baseline(), body(),
            metadata(OLD_DATA_DAY + "T08:00:00Z", editorial_day=historic_day.isoformat()),
            day=historic_day,
        )
        market_id = profile["catalog_slug_prefix"] + RECORD_IDS[0]
        original = next(row for row in first if row["slug"] == market_id)
        self.assertEqual(explicit_rule(original["ricorrenza_testo"]),
                         {"kind": "weekly", "weekdays": [2]})
        self.assertIn("ricorrenza_testo", original["riscontri_campi"][0]["campi_gestiti"])
        for unavailable_day in (None, "su richiesta"):
            with self.subTest(publisher_weekday=unavailable_day):
                current, report = self.fixture_read(
                    config, registry, first, body(weekday=unavailable_day),
                    metadata("2026-10-19T08:00:00Z"),
                )
                actual = next(row for row in current if row["slug"] == market_id)
                self.assertEqual(actual["ricorrenza_testo"], original["ricorrenza_testo"])
                self.assertEqual(actual["fonte_aggiornata_il"], OLD_DATA_DAY)
                self.assertEqual(actual["aggiornato_il"], OLD_DATA_DAY)
                new_receipts = [receipt for receipt in actual["riscontri_campi"]
                                if receipt["fonte_aggiornata_il"] == TODAY.isoformat()]
                self.assertTrue(new_receipts)
                self.assertTrue(all("ricorrenza_testo" not in receipt["valori"]
                                    for receipt in new_receipts))
                self.assertEqual(report["old_market_fields_changed"], 0)
                projected, _ = refresh_records(current, TODAY, 120, 540,
                                               source_limits=forecast_source_limits(config))
                final = next(row for row in projected if row["slug"] == market_id)
                self.assertEqual(final["date"], [])
                self.assertEqual(final["date_quality"], "sconosciuta")
                self.assertFalse(final["verificato_il"])

    def test_static_guard_rejects_global_date_rejuvenation_on_observed_existing_id(self):
        config, registry = configured()
        profile = config["raw_profiles"][0]
        historic_day = date(2025, 4, 3)
        registry["approvals"][0]["reviewed_on"] = historic_day.isoformat()
        first, _ = self.fixture_read(
            config, registry, baseline(), body(),
            metadata(OLD_DATA_DAY + "T08:00:00Z", editorial_day=historic_day.isoformat()),
            day=historic_day,
        )
        current, report = self.fixture_read(config, registry, first, body(weekday=None),
                                            metadata("2026-10-19T08:00:00Z"))
        market_id = profile["catalog_slug_prefix"] + RECORD_IDS[0]
        self.assertIn(market_id, report["evidence_updated_market_ids"])
        self.assertEqual(report["new_market_ids"], [])
        with TemporaryDirectory() as temporary:
            output = Path(temporary) / "public/data/v1"
            self.roundtrip(current, report, config, registry, output)
            manifest_path = output / "manifest.json"
            manifest = json.loads(manifest_path.read_text("utf-8"))
            parts = ([manifest["catalog"]] if manifest["layout"] == "single"
                     else [part["path"] for part in manifest["regions"]])
            changed = False
            for relative in parts:
                path = output.parents[1] / relative
                value = json.loads(path.read_text("utf-8"))
                records = value["markets"] if isinstance(value, dict) else value
                for row in records:
                    if row["slug"] == market_id:
                        self.assertEqual(row["fonte_aggiornata_il"], OLD_DATA_DAY)
                        # Simulate an export regression, preserving every
                        # source receipt, report, field value and index entry.
                        row["fonte_aggiornata_il"] = TODAY.isoformat()
                        changed = True
                path.write_text(json.dumps(value, ensure_ascii=False), encoding="utf-8")
            self.assertTrue(changed)
            with self.assertRaises(ValueError):
                verify_static(manifest_path, report, config, registry, TODAY)

    def test_second_read_obeys_the_source_forecast_limit_even_below_global_staleness(self):
        config, registry = configured()
        profile = config["raw_profiles"][0]
        blob = body()
        meta = metadata("2026-10-18T08:00:00Z")
        first, one = self.fixture_read(config, registry, baseline(), blob, meta)
        later = TODAY + timedelta(days=400)
        source_age = (later - date.fromisoformat("2026-10-18")).days
        self.assertGreater(source_age, profile["max_forecast_source_age_days"])
        self.assertLess(source_age, 540)
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "public/data/v1"
            before = self.roundtrip(first, one, config, registry, path)
            second, two = self.fixture_read(config, registry, before, blob, meta, day=later)
            self.assertEqual(two["new_market_ids"], [])
            self.assertEqual(two["old_market_fields_changed"], 0)
            self.assertEqual([row["slug"] for row in second], [row["slug"] for row in before])
            # A consumer omitting the publisher-specific cap would generate
            # forecasts from a 401-day-old source because its generic cap is 540.
            uncapped, _ = refresh_records(second, later, 120, 540, source_limits=())
            affected = set(two["evidence_updated_market_ids"])
            self.assertTrue(affected)
            self.assertTrue(all(row["date"] for row in uncapped if row["slug"] in affected))
            export(uncapped, path, today=later, min_count=1, preserve_ids=affected)
            with self.assertRaises(ValueError):
                verify_static(path / "manifest.json", two, config, registry, later)
            final = self.roundtrip(second, two, config, registry, path, day=later)
        for row in final:
            if row["slug"] in affected:
                self.assertEqual(row["date"], [])
                self.assertEqual(row["date_quality"], "sconosciuta")
                self.assertEqual(row["fonte_aggiornata_il"], "2026-10-18")

    def test_regenerated_publisher_record_id_holds_source_without_rebinding_market(self):
        config, registry = configured()
        profile = config["raw_profiles"][0]
        first, one = self.fixture_read(config, registry, baseline(), body(),
                                      metadata("2026-10-18T08:00:00Z"))
        tomorrow = TODAY + timedelta(days=1)
        changed = json.loads(body(hours="09:30-14:00"))
        changed["records"][0]["recordid"] = "3" * 40
        changed_blob = json.dumps(changed, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.assertNotEqual(hashlib.sha256(changed_blob).hexdigest(),
                            hashlib.sha256(body()).hexdigest())
        changed_meta = metadata("2026-10-20T08:00:00Z", editorial_day=tomorrow.isoformat())
        with TemporaryDirectory() as temporary:
            path = Path(temporary) / "public/data/v1"
            before = self.roundtrip(first, one, config, registry, path)
            steps = snapshot_steps(profile, changed_blob, changed_meta)
            fetch = sequence_transport(*steps)
            result, held = activate(config, registry, before, today=tomorrow,
                                    read_on=tomorrow.isoformat(), fetch=fetch)
        self.assertEqual(fetch.call_args_list, [call(url) for url, _ in steps])
        self.assertEqual(result, before)
        self.assertEqual(held["new_market_ids"], [])
        self.assertEqual(held["updated_market_ids"], [])
        self.assertEqual(held["evidence_updated_market_ids"], [])
        self.assertEqual(held["old_market_fields_changed"], 0)
        source = held["per_source"][profile["id"]]
        self.assertEqual(source["status"], "publisher_source_held_for_review")
        self.assertGreater(source["field_review_needed"]["source_identity_missing_or_changed"], 0)
        self.assertNotIn(profile["catalog_slug_prefix"] + "3" * 40,
                         {row["slug"] for row in result})
        self.assertTrue(validate_release(before, result, held, config, registry)["release_safe"])

    def test_same_day_metadata_race_holds_only_that_source_and_preserves_existing_markets(self):
        profile = synthetic_profile()
        config, registry = configured(profile)
        existing, _ = self.fixture_read(config, registry, baseline(), body(),
                                       metadata("2026-10-18T08:00:00Z"))
        other = copy.deepcopy(profile)
        other.update({
            "id": "fixture-second-dynamic",
            "catalog_slug_prefix": "fixture-second-ods-",
            "municipality": "Ferrara", "province": "FE",
            "api_dataset_id": "fixture-other-markets",
            "resource_url": profile["resource_url"].replace(DATASET, "fixture-other-markets"),
            "source_metadata_url": profile["source_metadata_url"].replace(DATASET, "fixture-other-markets"),
        })
        config, registry = configured(profile, other)
        first_meta = metadata("2026-10-19T08:00:00.100000Z")
        second_meta = metadata("2026-10-19T08:00:00.200000Z")
        other_blob = body(dataset=other["api_dataset_id"])
        other_meta = metadata("2026-10-19T07:00:00Z", dataset=other["api_dataset_id"])
        fetch = sequence_transport(
            *snapshot_steps(profile, body(address="Via Fittizia Durante La Corsa"), first_meta, second_meta),
            *snapshot_steps(other, other_blob, other_meta),
        )
        frozen = copy.deepcopy(existing)
        with TemporaryDirectory() as temporary:
            result, report = activate(config, registry, existing, today=TODAY,
                read_on=TODAY.isoformat(), fetch=fetch, source_cache=temporary)
            checkpoint_sources = [json.loads(path.read_text("utf-8")).get("source_url")
                                  for path in Path(temporary).glob("*.json")
                                  if path.name != "context.json"]
            self.assertNotIn(profile["resource_url"], checkpoint_sources)
            self.assertIn(other["resource_url"], checkpoint_sources)
        self.assertEqual(existing, frozen)
        self.assertEqual(result[:len(existing)], existing)
        self.assertEqual(report["per_source"][profile["id"]]["status"], "publisher_source_held_for_review")
        self.assertEqual(report["per_source"][other["id"]]["status"], "source_contract_approved_staged_only")
        self.assertEqual(report["status_counts"]["publisher_sources_held"], 1)
        self.assertEqual(report["status_counts"]["approved_sources_reconciled"], 1)
        self.assertEqual(len(report["new_market_ids"]), 2)
        self.assertTrue(all(mid.startswith(other["catalog_slug_prefix"]) for mid in report["new_market_ids"]))
        self.assertTrue(validate_release(existing, result, report, config, registry)["release_safe"])

    def test_stage_and_apply_reject_missing_altered_or_rebound_snapshot_proof(self):
        profile = synthetic_profile()
        blob = body()
        meta = metadata("2026-10-18T08:00:00Z")
        proof = make_snapshot_date_proof(profile, blob, before_metadata=meta,
            after_metadata=meta, read_on=TODAY.isoformat(), today=TODAY)
        corrupted = copy.deepcopy(proof)
        corrupted["source_date"] = TODAY.isoformat()
        rebound = copy.deepcopy(profile)
        rebound["notes"] += " Synthetic revised contract."
        cases = (
            ("missing", profile, blob, None),
            ("altered date", profile, blob, corrupted),
            ("different bytes", profile, blob + b"\n", proof),
            ("different reviewed contract", rebound, blob, proof),
        )
        for label, current, payload, source_proof in cases:
            with self.subTest(case=label, boundary="stage"), self.assertRaises(ValueError):
                stage(current, payload, baseline(), today=TODAY, read_on=TODAY.isoformat(),
                      source_date_proof=source_proof)
            with self.subTest(case=label, boundary="apply"), self.assertRaises(ValueError):
                apply_approved(current, payload, baseline(), certificate(current),
                    today=TODAY, read_on=TODAY.isoformat(), source_date_proof=source_proof)

    def test_release_and_static_guards_reject_an_unproved_report_date_or_missing_proof(self):
        config, registry = configured()
        profile = config["raw_profiles"][0]
        result, report = self.fixture_read(config, registry, baseline(), body(),
                                          metadata(OLD_DATA_DAY + "T10:30:00+02:00"))
        for missing in (False, True):
            with self.subTest(missing_proof=missing), TemporaryDirectory() as temporary:
                changed_report = copy.deepcopy(report)
                changed_rows = copy.deepcopy(result)
                source = changed_report["per_source"][profile["id"]]
                if missing:
                    del source["source_observations"]["source_date_proof"]
                else:
                    # Keep the report and public receipts internally consistent,
                    # but leave the actual metadata/body proof at its old date.
                    source["source_observations"]["publisher_dataset_date"] = TODAY.isoformat()
                    for row in changed_rows[1:]:
                        row["aggiornato_il"] = TODAY.isoformat()
                        row["fonte_aggiornata_il"] = TODAY.isoformat()
                        row["riscontri_campi"][0]["fonte_aggiornata_il"] = TODAY.isoformat()
                        source["new_venue_evidence"][row["slug"]]["receipt"] = copy.deepcopy(row["riscontri_campi"][0])
                with self.assertRaises(ValueError):
                    validate_release(baseline(), changed_rows, changed_report, config, registry)
                path = Path(temporary) / "public/data/v1"
                export(changed_rows, path, today=TODAY, min_count=1,
                       preserve_ids=set(report["new_market_ids"]))
                with self.assertRaises(ValueError):
                    verify_static(path / "manifest.json", changed_report, config, registry, TODAY)


if __name__ == "__main__":
    unittest.main()
