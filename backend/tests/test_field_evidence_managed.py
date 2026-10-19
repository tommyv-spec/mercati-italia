import copy
import sys
import unittest
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from field_evidence import (FIELDS, MAX_MANAGED_HISTORY, clean_receipts, fingerprint,
                            make_receipt, managed_update_allowed, mark_managed_fields,
                            valid_receipt, retire_superseded_receipts)

MANAGER = "fixture_ingest"
FIRST = date(2026, 10, 20)
SECOND = date(2026, 10, 21)


def market():
    return {"slug": "fixture-stable-id", "citta": "Comune", "provincia": "MI",
            "regione": "Lombardia", "indirizzo": "Piazza Comune",
            "orario_testo": "08:00–13:00", "ricorrenza_testo": "Ogni martedì",
            "verificato_il": ""}


def observation(row, *, version=1, read=FIRST, updated="2026-10-19", **extra):
    args = dict(source_url="https://comune.example/mercati.json", source_name="Comune",
                source_id="official_fixture", source_row="stable-1", read_on=read,
                source_updated_on=updated, source_sha256=fingerprint({"version": version}))
    args.update(extra)
    return make_receipt(row, values={field: row[field] for field in FIELDS}, **args)


def managed_market():
    row = market()
    row["riscontri_campi"] = [mark_managed_fields(observation(row), set(FIELDS), manager=MANAGER)]
    return row


class ManagedFieldTests(unittest.TestCase):
    def test_all_three_fields_follow_later_version_and_keep_previous_proof(self):
        for field, new_value in {"indirizzo": "Piazza Comune, 2", "orario_testo": "09:00–13:00",
                                 "ricorrenza_testo": "Ogni mercoledì"}.items():
            with self.subTest(field=field):
                before = managed_market()
                proposed = {**before, field: new_value}
                receipt = observation(proposed, version=2, read=SECOND, updated="2026-10-20")
                self.assertTrue(managed_update_allowed(before, receipt, field, manager=MANAGER, today=SECOND))
                managed = mark_managed_fields(receipt, {field}, manager=MANAGER, previous=before)
                proposed["riscontri_campi"] = clean_receipts(
                    [*before["riscontri_campi"], managed], proposed, today=SECOND)
                result = proposed["riscontri_campi"][0]
                self.assertEqual(set(result["campi_gestiti"]), set(FIELDS))
                self.assertEqual(result["versioni_precedenti"][0]["valori"], {field: before[field]})
                self.assertEqual(result["versioni_precedenti"][0]["sha256"], before["riscontri_campi"][0]["sha256"])
                self.assertTrue(valid_receipt(result, proposed, today=SECOND))

    def test_multi_field_new_receipt_can_be_evaluated_one_field_at_a_time(self):
        before = managed_market()
        proposed = {**before, "indirizzo": "Piazza Nuova", "orario_testo": "09:00–13:00"}
        receipt = observation(proposed, version=2, read=SECOND)
        for field in ("indirizzo", "orario_testo"):
            self.assertTrue(managed_update_allowed(before, receipt, field, manager=MANAGER, today=SECOND))

    def test_observing_an_existing_value_never_grants_ownership(self):
        before = market()
        before["riscontri_campi"] = [observation(before)]
        same = observation(before, read=SECOND)
        before["riscontri_campi"] = clean_receipts([*before["riscontri_campi"], same], before, today=SECOND)
        self.assertNotIn("campi_gestiti", before["riscontri_campi"][0])
        proposed = {**before, "orario_testo": "09:00–13:00"}
        next_read = date(2026, 10, 22)
        receipt = observation(proposed, version=2, read=next_read)
        self.assertFalse(managed_update_allowed(before, receipt, "orario_testo", manager=MANAGER, today=next_read))
        with self.assertRaisesRegex(ValueError, "pre-existing"):
            mark_managed_fields(receipt, {"orario_testo"}, manager=MANAGER, previous=before)

    def test_manual_edit_or_human_verification_blocks_automatic_change(self):
        for edit in ({"orario_testo": "10:00–12:00"}, {"verificato_il": "2026-10-20"}):
            with self.subTest(edit=edit):
                before = managed_market()
                before.update(edit)
                proposed = {**before, "orario_testo": "09:00–13:00"}
                receipt = observation(proposed, version=2, read=SECOND)
                self.assertFalse(managed_update_allowed(before, receipt, "orario_testo", manager=MANAGER, today=SECOND))

    def test_other_engine_or_changed_target_identity_cannot_take_over(self):
        before = managed_market()
        proposed = {**before, "orario_testo": "09:00–13:00"}
        receipt = observation(proposed, version=2, read=SECOND)
        self.assertFalse(managed_update_allowed(before, receipt, "orario_testo", manager="other_engine", today=SECOND))
        for key, value in (("slug", "different-id"), ("citta", "Altro Comune"), ("provincia", "VA")):
            changed = copy.deepcopy(receipt)
            changed["mercato"][key] = value
            self.assertFalse(managed_update_allowed(before, changed, "orario_testo", manager=MANAGER, today=SECOND))

    def test_competing_source_row_url_method_or_hash_kind_blocks_update(self):
        variants = [
            {"source_url": "https://other.example/mercati.json"}, {"source_id": "other_source"},
            {"source_row": "other-row"}, {"method": "pagina_primaria_revisionata"},
            {"scope": "pagina"}, {"fingerprint_kind": "html_bytes"},
        ]
        for extra in variants:
            with self.subTest(extra=extra):
                before = managed_market()
                before["riscontri_campi"].append(observation(before, **extra))
                self.assertEqual(len(clean_receipts(before["riscontri_campi"], before, today=SECOND)), 2)
                proposed = {**before, "orario_testo": "09:00–13:00"}
                receipt = observation(proposed, version=2, read=SECOND)
                self.assertFalse(managed_update_allowed(before, receipt, "orario_testo", manager=MANAGER, today=SECOND))

    def test_old_same_day_unchanged_hash_and_regressed_source_dates_block(self):
        before = managed_market()
        proposed = {**before, "orario_testo": "09:00–13:00"}
        cases = [
            {"read": FIRST}, {"read": FIRST - timedelta(days=1)},
            {"version": 1}, {"updated": "2026-10-18"}, {"updated": ""},
        ]
        for extra in cases:
            with self.subTest(extra=extra):
                args = {"version": 2, "read": SECOND, "updated": "2026-10-19", **extra}
                receipt = observation(proposed, **args)
                self.assertFalse(managed_update_allowed(before, receipt, "orario_testo", manager=MANAGER, today=SECOND))
        receipt = observation(proposed, version=2, read=SECOND)
        self.assertFalse(managed_update_allowed(before, receipt, "orario_testo", manager=MANAGER,
                                               today=SECOND + timedelta(days=46)))

    def test_unknown_source_dates_remain_unknown_while_versions_are_ordered_by_reads(self):
        before = market()
        before["riscontri_campi"] = [mark_managed_fields(
            observation(before, updated=""), {"orario_testo"}, manager=MANAGER)]
        proposed = {**before, "orario_testo": "09:00–13:00"}
        receipt = observation(proposed, version=2, read=SECOND, updated="")
        self.assertTrue(managed_update_allowed(before, receipt, "orario_testo", manager=MANAGER, today=SECOND))
        managed = mark_managed_fields(receipt, {"orario_testo"}, manager=MANAGER, previous=before)
        self.assertEqual(managed["fonte_aggiornata_il"], "")
        self.assertEqual(managed["versioni_precedenti"][0]["fonte_aggiornata_il"], "")

    def test_identical_reread_preserves_only_previously_managed_fields(self):
        before = market()
        owned = mark_managed_fields(observation(before), {"orario_testo"}, manager=MANAGER)
        reread = observation(before, read=SECOND)
        result = clean_receipts([owned, reread], before, today=SECOND)[0]
        self.assertEqual(result["campi_gestiti"], ["orario_testo"])
        self.assertEqual(result["letto_il"], str(SECOND))
        with self.assertRaisesRegex(ValueError, "pre-existing"):
            mark_managed_fields(reread, {"indirizzo"}, manager=MANAGER, previous=before)

    def test_noop_reread_cannot_reset_publisher_version_floor(self):
        for updated in ("2026-10-18", ""):
            for reversed_order in (False, True):
                with self.subTest(updated=updated, reversed_order=reversed_order):
                    before = managed_market()
                    previous = copy.deepcopy(before["riscontri_campi"][0])
                    reread = observation(before, version=2, read=SECOND, updated=updated)
                    receipts = [previous, reread]
                    if reversed_order:
                        receipts.reverse()
                    before["riscontri_campi"] = clean_receipts(receipts, before, today=SECOND)
                    self.assertEqual(before["riscontri_campi"], [previous])
                    third = SECOND + timedelta(days=1)
                    proposed = {**before, "orario_testo": "09:00–13:00"}
                    next_receipt = observation(proposed, version=3, read=third, updated=updated)
                    self.assertFalse(managed_update_allowed(
                        before, next_receipt, "orario_testo", manager=MANAGER, today=third))
                    restored = observation(proposed, version=3, read=third, updated="2026-10-19")
                    self.assertTrue(managed_update_allowed(
                        before, restored, "orario_testo", manager=MANAGER, today=third))

    def test_missing_and_whitespace_fields_can_be_marked_after_actual_fill(self):
        for missing in (None, "", "  "):
            before = {**market(), "orario_testo": missing}
            receipt = observation(market())
            marked = mark_managed_fields(receipt, {"orario_testo"}, manager=MANAGER, previous=before)
            self.assertEqual(marked["campi_gestiti"], ["orario_testo"])

    def test_history_is_bounded_nonrecursive_and_validates_after_repeated_changes(self):
        before = managed_market()
        for version in range(2, 13):
            read = FIRST + timedelta(days=version)
            proposed = {**before, "orario_testo": f"08:{version:02d}–13:00"}
            receipt = observation(proposed, version=version, read=read, updated=str(read))
            self.assertTrue(managed_update_allowed(before, receipt, "orario_testo", manager=MANAGER, today=read))
            next_receipt = mark_managed_fields(receipt, {"orario_testo"}, manager=MANAGER, previous=before)
            proposed["riscontri_campi"] = clean_receipts([next_receipt], proposed, today=read)
            self.assertTrue(valid_receipt(proposed["riscontri_campi"][0], proposed, today=read))
            before = proposed
        history = before["riscontri_campi"][0]["versioni_precedenti"]
        self.assertEqual(len(history), MAX_MANAGED_HISTORY)
        self.assertTrue(all("versioni_precedenti" not in receipt for receipt in history))

    def test_contradicted_source_claim_is_retired_without_changing_value_or_other_proof(self):
        before = managed_market()
        other = observation(before, source_id="independent_source")
        before["riscontri_campi"].append(other)
        frozen = copy.deepcopy(before)
        proposed = {**before, "orario_testo": "09:00–13:00"}
        next_receipt = observation(proposed, version=2, read=SECOND)
        kept = retire_superseded_receipts(before, next_receipt, today=SECOND)
        self.assertEqual(before, frozen)
        own = next(r for r in kept if r["fonte_id"] == "official_fixture")
        independent = next(r for r in kept if r["fonte_id"] == "independent_source")
        self.assertNotIn("orario_testo", own["valori"])
        self.assertNotIn("orario_testo", own["campi_gestiti"])
        self.assertEqual(own["letto_il"], str(FIRST))
        self.assertEqual(independent, other)
        self.assertEqual(own["valori"]["indirizzo"], before["indirizzo"])

    def test_unordered_or_regressed_source_version_does_not_retire_receipt(self):
        before = managed_market()
        proposed = {**before, "orario_testo": "09:00–13:00"}
        for change in ({"read": FIRST}, {"version": 1}, {"updated": "2026-10-18"},
                       {"source_row": "other-row"}):
            with self.subTest(change=change):
                receipt = observation(proposed, **{"version": 2, "read": SECOND, **change})
                self.assertEqual(retire_superseded_receipts(before, receipt, today=SECOND),
                                 before["riscontri_campi"])


if __name__ == "__main__":
    unittest.main()
