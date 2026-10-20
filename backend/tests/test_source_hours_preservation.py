"""Complete hours and qualifications survive the actual official-source chain.

The fixture contains saved public-source objects and minimal pre-fix catalog
fields, with acquisition receipts. All metadata bracketing here is an offline
replay, not a claim that CI has read the publisher or confirmed an opening.
"""
import copy
import json
import re
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from export_static import export, normalize, INDEX_FIELDS
from field_evidence import attach_feed_observations, field_states, make_receipt, valid_receipt
from merge_catalog import combine, load_existing
from official_source_output_gate import inspect as inspect_official_source_output
from publisher_snapshot_date import make_snapshot_date_proof
from source_bologna import convert as convert_bologna
from source_contract_activation import activate, validate_release
from source_contract_ingest import apply_approved, verify_update, PublishedSourceDriftError
from source_firenze import convert as convert_firenze, SOURCE_UPDATED
from source_hours import HoursTextTooLong, MAX_HOURS_TEXT_LENGTH
from source_lifecycle import candidate_record, parse_rows
from test_source_bologna import snapshot as dedicated_bologna_fixture

DAY = date(2026, 10, 19)
FIXTURE = json.loads((ROOT / "tests/fixtures/source_hours_20261019.json").read_text("utf-8"))
CONFIG = json.loads((ROOT / "data/market-source-contracts.json").read_text("utf-8"))
REGISTRY = json.loads((ROOT / "data/approved-source-admissions.json").read_text("utf-8"))
BO = next(p for p in CONFIG["raw_profiles"] if p["id"] == "bologna-generic-venues")
ADMISSION = next(p for p in REGISTRY["approvals"] if p["source_id"] == BO["id"])
EXPECTED = FIXTURE["expected_nine_seasonal_hours"]
TARGET = sorted(EXPECTED)[0]
QUALIFICATION = "(indicazioni della fonte; da verificare con il Comune)"


def encoded(value):
    return json.dumps(value, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def source_blob(hours=None):
    payload = copy.deepcopy(FIXTURE["bologna_original_query"])
    if hours is not None:
        row = next(r for r in payload["records"] if "bo-open-" + r["recordid"] == TARGET)
        row["fields"]["orario_svolgimento"] = hours
    return encoded(payload)


def baseline():
    return copy.deepcopy(FIXTURE["baseline_bologna39_and_two_overlap_guards"])


def bound_date(blob):
    meta = encoded(FIXTURE["bologna_original_metadata"])
    return make_snapshot_date_proof(BO, blob, before_metadata=meta, after_metadata=meta,
                                    read_on=str(DAY), today=DAY)


def apply_source(before=None, blob=None):
    before = baseline() if before is None else before
    blob = source_blob() if blob is None else blob
    return apply_approved(BO, blob, before, ADMISSION, today=DAY,
                          read_on=str(DAY), source_date_proof=bound_date(blob))


def activation(blob, before):
    config, registry = copy.deepcopy(CONFIG), copy.deepcopy(REGISTRY)
    config["raw_profiles"] = [copy.deepcopy(BO)]
    registry["approvals"] = [copy.deepcopy(ADMISSION)]
    values = {BO["resource_url"]: blob,
              BO["source_metadata_url"]: encoded(FIXTURE["bologna_original_metadata"])}
    def fetch(url):
        return values[url], False
    after, report = activate(config, registry, before, today=DAY, read_on=str(DAY), fetch=fetch)
    validate_release(before, after, report, config, registry)
    return after, report


class OfficialHoursPreservationTests(unittest.TestCase):
    def test_firenze_preserves_all_closures_in_receipts_detail_and_index(self):
        source = copy.deepcopy(FIXTURE["firenze_original_geojson"])
        rows = convert_firenze(source)
        inspect_official_source_output("firenze", rows, today=DAY)
        observed = attach_feed_observations("firenze", source, rows, read_on=str(DAY))
        inspect_official_source_output("firenze", observed, today=DAY)
        merged, stats = combine(copy.deepcopy(FIXTURE["baseline_firenze4"]), observed)
        self.assertEqual(stats["merged"], 4)
        expected = {"fi-feelflorence-" + str(f["id"]): f["properties"]["orari"].strip()
                    for f in source["features"]}
        # The lost tail includes fifteen more dates after the first range.
        closures = re.findall(r"\d{2}-\d{2}-\d{4}", expected["fi-feelflorence-4"])
        self.assertEqual(len(closures), 17)
        self.assertGreater(len(expected["fi-feelflorence-4"]), 180)
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp) / "public"
            out = public / "data/v1"
            result = export(merged, out, today=DAY)
            saved = load_existing(out / "manifest.json")
            index = json.loads((public / result["manifest"]["index"]).read_text())["markets"]
            compact = {r[0]: dict(zip(INDEX_FIELDS, r)) for r in index}
            self.assertEqual(len(saved), 4)
            for row in saved:
                self.assertEqual(row["orario_testo"], expected[row["slug"]])
                self.assertEqual(compact[row["slug"]]["orario_testo"], expected[row["slug"]])
                self.assertEqual(row["date"], [])
                self.assertEqual(row["date_quality"], "sconosciuta")
                self.assertEqual(row["status"], "non_confermato")
                self.assertEqual(row["aggiornato_il"], SOURCE_UPDATED)
                self.assertFalse(row["verificato_il"])
                self.assertEqual(field_states(row, today=DAY)["orario_testo"],
                                 "riscontro_da_aggiornare")
                self.assertTrue(any(r["valori"].get("orario_testo") == row["orario_testo"]
                                    and valid_receipt(r, row, today=DAY)
                                    for r in row["riscontri_campi"]))
        # Independent schedules for the two floors are kept in the same text.
        self.assertIn("Primo Piano", expected["fi-feelflorence-1"])
        self.assertIn("Chiuso: 25 dicembre", expected["fi-feelflorence-1"])

    def test_nine_real_bologna_seasonal_hours_survive_approved_chain_and_export(self):
        before = baseline()
        frozen = copy.deepcopy(before)
        after, report = activation(source_blob(), before)
        self.assertEqual(before, frozen)
        self.assertEqual(report["old_market_fields_changed"], 9)
        self.assertEqual(set(report["updated_market_ids"]), set(EXPECTED))
        self.assertEqual(report["new_market_ids"], [])
        self.assertEqual([r["slug"] for r in after], [r["slug"] for r in before])
        for previous, row in zip(before, after):
            # Hours observations cannot update the calendar, identity or source age.
            for key, value in previous.items():
                if key != "orario_testo":
                    self.assertEqual(row.get(key), value, (row["slug"], key))
            if row["slug"] not in EXPECTED:
                self.assertEqual(row.get("orario_testo"), previous.get("orario_testo"))
                continue
            wanted = EXPECTED[row["slug"]] + " " + QUALIFICATION
            self.assertEqual(row["orario_testo"], wanted)
            self.assertEqual(row["date"], [])
            self.assertEqual(row["aggiornato_il"], "2025-04-02")
            self.assertFalse(row["verificato_il"])
            self.assertEqual(field_states(row, today=DAY)["orario_testo"], "riscontro_da_aggiornare")
        with tempfile.TemporaryDirectory() as tmp:
            public = Path(tmp) / "public"
            out = public / "data/v1"
            result = export(after, out, today=DAY, preserve_ids={r["slug"] for r in before})
            saved = {r["slug"]: r for r in load_existing(out / "manifest.json")}
            index = json.loads((public / result["manifest"]["index"]).read_text())["markets"]
            compact = {r[0]: dict(zip(INDEX_FIELDS, r)) for r in index}
            for sid, hours in EXPECTED.items():
                wanted = hours + " " + QUALIFICATION
                self.assertEqual(saved[sid]["orario_testo"], wanted)
                self.assertEqual(compact[sid]["orario_testo"], wanted)
                self.assertTrue(any(r["valori"].get("orario_testo") == wanted
                                    and "orario_testo" in r.get("campi_gestiti", [])
                                    for r in saved[sid]["riscontri_campi"]))
        again, repeat = activation(source_blob(), after)
        self.assertEqual(again, after)
        self.assertEqual(repeat["old_market_fields_changed"], 0)
        self.assertEqual(repeat["evidence_updated_market_ids"], [])

    def test_long_generic_hours_preserve_final_exclusion_without_interpreting_it(self):
        hours = (
            "Da giugno a settembre: 18:00-21:00; da ottobre a maggio: 16:00-19:30. "
            "In occasione delle festività l'orario è comunicato dal Comune. "
            "Chiuso il 25 dicembre e il 1 gennaio; eventuali recuperi sono pubblicati separatamente."
        )
        self.assertGreater(len(hours), 180)
        after, proof = apply_source(blob=source_blob(hours))
        row = next(r for r in after if r["slug"] == TARGET)
        exported, error = normalize(row, DAY)
        self.assertIsNone(error)
        self.assertEqual(exported["orario_testo"], hours + " " + QUALIFICATION)
        self.assertEqual(exported["date"], [])
        self.assertEqual(exported["date_quality"], "sconosciuta")
        self.assertTrue(any(r["valori"].get("orario_testo") == exported["orario_testo"]
                            for r in exported["riscontri_campi"]))
        self.assertEqual(proof["verified_events_created"], 0)

    def test_dedicated_bologna_adapter_preserves_tail_but_remains_separate_path(self):
        # This adapter is not the generic reader used by the 39 current cards.
        payload = dedicated_bologna_fixture()
        hours = (
            "Estivo: 18:00-21:00. Invernale: 16:00-19:30. "
            "Le aperture straordinarie e gli eventuali recuperi sono comunicati "
            "separatamente dal Comune. Chiuso il 25 dicembre e il 1 gennaio."
        )
        self.assertGreater(len(hours), 130)
        payload["rows"][0]["fields"]["orario_svolgimento"] = hours
        row = next(r for r in convert_bologna(payload, today=DAY)
                   if r["slug"] == "bo-open-" + payload["rows"][0]["recordid"])
        exported, error = normalize(row, DAY)
        self.assertIsNone(error)
        self.assertEqual(exported["orario_testo"], hours + " (fonte da verificare)")
        self.assertEqual(exported["date"], [])
        self.assertEqual(exported["aggiornato_il"], "2025-04-02")

    def test_seasonal_hours_changes_are_included_in_source_fingerprint(self):
        rows = parse_rows(BO, source_blob())
        raw = next(r for r in rows if "bo-open-" + r["recordid"] == TARGET)
        previous, issue, old_hash = candidate_record(BO, raw, today=DAY)
        changed = {**raw, "orario_svolgimento": EXPECTED[TARGET] + "; chiuso nei festivi"}
        later, later_issue, new_hash = candidate_record(BO, changed, today=DAY)
        self.assertNotEqual(old_hash, new_hash)
        self.assertEqual(issue, later_issue)
        self.assertEqual(later["date"], previous["date"])
        self.assertEqual(later["ricorrenza_testo"], previous["ricorrenza_testo"])
        self.assertTrue(later["orario_testo"].endswith(QUALIFICATION))

    def test_blank_hours_cannot_regress_or_tie_a_previous_address_observation(self):
        for read_on, updated_on in (("2026-10-18", "2026-06-01"),
                                    ("2026-10-19", "2025-04-02")):
            with self.subTest(read_on=read_on, updated_on=updated_on):
                before = baseline()
                prior = next(r for r in before if r["slug"] == TARGET)
                prior["riscontri_campi"] = [make_receipt(
                    prior, values={"indirizzo": prior["indirizzo"]},
                    source_url=BO["resource_url"], source_name=BO["publisher"],
                    source_id=BO["id"], source_row=TARGET, read_on=read_on,
                    source_updated_on=updated_on, source_sha256="a" * 64)]
                frozen = copy.deepcopy(before)
                with self.assertRaises(PublishedSourceDriftError):
                    apply_source(before)
                self.assertEqual(before, frozen)
                self.assertEqual(field_states(prior, today=DAY)["orario_testo"], "mancante")
        # An older read of the same non-regressive dataset can be extended,
        # provided the new full receipt really survives consolidation.
        before = baseline()
        prior = next(r for r in before if r["slug"] == TARGET)
        prior["riscontri_campi"] = [make_receipt(
            prior, values={"indirizzo": prior["indirizzo"]},
            source_url=BO["resource_url"], source_name=BO["publisher"],
            source_id=BO["id"], source_row=TARGET, read_on="2026-10-18",
            source_updated_on="2025-04-02", source_sha256="a" * 64)]
        after, _ = apply_source(before)
        row = next(r for r in after if r["slug"] == TARGET)
        self.assertTrue(any(r["valori"].get("orario_testo") == row["orario_testo"]
                            and "orario_testo" in r.get("campi_gestiti", [])
                            and r["letto_il"] == str(DAY)
                            for r in row["riscontri_campi"]))

    def test_later_closure_range_does_not_reuse_the_previous_list_as_source_evidence(self):
        old_text = "Orari 09:00-18:00; chiusure: 1, 5 gennaio"
        new_text = "Orari 09:00-18:00; chiusure: 1-5 gennaio"
        before, _ = apply_source(blob=source_blob(old_text))
        later_day = date(2026, 10, 20)
        blob = source_blob(new_text)
        meta = encoded(FIXTURE["bologna_original_metadata"])
        proof = make_snapshot_date_proof(
            BO, blob, before_metadata=meta, after_metadata=meta,
            read_on=str(later_day), today=later_day)
        after, certificate = apply_approved(
            BO, blob, before, ADMISSION, today=later_day,
            read_on=str(later_day), source_date_proof=proof)
        row = next(r for r in after if r["slug"] == TARGET)
        self.assertEqual(certificate["old_fields_modified"], 1)
        self.assertEqual(row["orario_testo"], new_text + " " + QUALIFICATION)
        hours_proof = next(r for r in row["riscontri_campi"] if "orario_testo" in r["valori"])
        self.assertEqual(hours_proof["valori"]["orario_testo"], row["orario_testo"])
        self.assertEqual(hours_proof["letto_il"], str(later_day))
        self.assertTrue(any(r["valori"].get("orario_testo") == old_text + " " + QUALIFICATION
                            for r in hours_proof["versioni_precedenti"]))
        self.assertEqual(row["date"], [])
        self.assertEqual(row["aggiornato_il"], "2025-04-02")
        self.assertFalse(row["verificato_il"])

    def test_existing_hours_location_identity_or_verification_conflicts_still_hold(self):
        changes = (
            {"orario_testo": "09:00–12:00"},
            {"indirizzo": "Via di un'altra sede 9"},
            {"citta": "Imola"},
            {"provincia": "FE"},
            {"regione": "Lazio"},
            {"url_fonte": "https://example.org/another-source"},
            {"slug": "bo-open-" + "0" * 40},
            {"verificato_il": str(DAY)},
        )
        for change in changes:
            with self.subTest(change=change):
                before = baseline()
                row = next(r for r in before if r["slug"] == TARGET)
                row.update(change)
                frozen = copy.deepcopy(before)
                with self.assertRaises(PublishedSourceDriftError):
                    apply_source(before)
                self.assertEqual(before, frozen)

    def test_independent_verifier_rejects_missing_or_mismatched_source_receipt(self):
        before = baseline()
        after, certificate = apply_source(before)
        previous = next(r for r in before if r["slug"] == TARGET)
        row = next(r for r in after if r["slug"] == TARGET)
        proof = next(p for p in certificate["updates"] if p["slug"] == TARGET)
        observations = certificate["source_observations"]
        self.assertEqual(verify_update(BO, previous, row, proof, today=DAY,
                                       source_observations=observations), 1)
        for change in (
            None,
            {"fonte_id": "another-source"},
            {"url": "https://example.org/another-resource"},
            {"riga_fonte": "bo-open-" + "0" * 40},
            {"sha256": "0" * 64},
            {"valori": {"orario_testo": row["orario_testo"]}},
            {"valori": {"orario_testo": row["orario_testo"], "indirizzo": "Via diversa"}},
        ):
            with self.subTest(change=change):
                tampered = copy.deepcopy(proof)
                if change is None:
                    tampered["receipt"] = None
                else:
                    tampered["receipt"].update(change)
                with self.assertRaises(ValueError):
                    verify_update(BO, previous, row, tampered, today=DAY,
                                  source_observations=observations)

    def test_oversized_hours_hold_sources_without_writing_partial_qualifications(self):
        hours = "Orari stagionali: " + "x" * MAX_HOURS_TEXT_LENGTH + "; chiuso il 25 dicembre"
        firenze = copy.deepcopy(FIXTURE["firenze_original_geojson"])
        firenze["features"][-1]["properties"]["orari"] = hours
        with self.assertRaisesRegex(HoursTextTooLong, "hours_text_too_long"):
            convert_firenze(firenze)
        payload = dedicated_bologna_fixture()
        payload["rows"][0]["fields"]["orario_svolgimento"] = hours
        with self.assertRaisesRegex(HoursTextTooLong, "hours_text_too_long"):
            convert_bologna(payload, today=DAY)
        before = baseline()
        # Also count the qualification: 2,000 source characters do not leave
        # room to silently remove the uncertainty suffix.
        for text in (hours, "x" * MAX_HOURS_TEXT_LENGTH):
            with self.subTest(characters=len(text)):
                with self.assertRaises(HoursTextTooLong):
                    apply_source(before, source_blob(text))
                after, report = activation(source_blob(text), before)
                self.assertEqual(after, before)
                self.assertEqual(report["per_source"][BO["id"]]["error_type"], "HoursTextTooLong")
                self.assertEqual(report["per_source"][BO["id"]]["status"],
                                 "publisher_source_held_for_review")

    def test_oversized_export_keeps_previous_manifest_and_assets_unchanged(self):
        rows = convert_firenze(copy.deepcopy(FIXTURE["firenze_original_geojson"]))
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "public/data/v1"
            export(rows, out, today=DAY)
            before = {str(p.relative_to(out)): p.read_bytes() for p in out.rglob("*") if p.is_file()}
            rows[-1]["orario_testo"] = "x" * MAX_HOURS_TEXT_LENGTH + "; chiuso nei festivi"
            with self.assertRaisesRegex(HoursTextTooLong, "hours_text_too_long"):
                export(rows, out, today=DAY)
            self.assertEqual({str(p.relative_to(out)): p.read_bytes()
                              for p in out.rglob("*") if p.is_file()}, before)


if __name__ == "__main__":
    unittest.main()
