import json
import sys
import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from export_static import export, normalize
from field_evidence import make_receipt
from merge_catalog import load_existing
from municipality_reconciliation import reconcile
from municipality_release_guard import check, verify_exported
from province_reconciliation import KEY, REGISTRY_SHA256, valid_proof
from test_municipality_reconciliation import REFERENCE, TODAY, market


def wrong_province(slug="monza-market", publisher="happings.com"):
    row = market(slug, "Monza", "MI", "Lombardia", "Mercato settimanale di Monza")
    row.update(fonte=publisher,
               url_fonte="https://www.happings.com/it/mercati-settimanali-a-milano.html",
               indirizzo="Piazza del Duomo", orario_testo="08:00-13:00")
    return row


class ProvinceReconciliationTests(unittest.TestCase):
    def test_exact_city_region_reconciles_every_publisher_with_only_admin_proof(self):
        before = [wrong_province(str(index), publisher) for index, publisher in enumerate(
            ("happings.com", "milanopocket.it", "sagreumbre.it", "other publisher"))]
        saved = deepcopy(before)
        after, report = reconcile(before, REFERENCE, apply=True)
        for old, new in zip(before, after):
            self.assertEqual(new["provincia"], "MB")
            self.assertEqual({key for key in old.keys() | new.keys()
                              if old.get(key) != new.get(key)}, {"provincia", KEY})
            self.assertTrue(valid_proof(new[KEY], new))
            self.assertEqual(new[KEY]["data_riferimento"], "2026-02-21")
            self.assertNotIn("letto_il", new[KEY])
            self.assertEqual(new[KEY]["sha256_registro"], REGISTRY_SHA256)
        self.assertEqual(before, saved)
        self.assertEqual(report["counts"]["province_fixed"], 4)
        self.assertEqual(check(before, after, report)["province_replacements"], 4)

    def test_missing_ambiguous_or_wrong_region_identity_and_blank_province_are_held(self):
        cases = [
            {**wrong_province("district"), "citta": "Roma Centro", "regione": "Lazio", "provincia": "MI"},
            {**wrong_province("wrong-region"), "regione": "Toscana"},
            {**wrong_province("two-cities"), "citta": "Monza Milano"},
            {**wrong_province("empty-province"), "provincia": ""},
            {**wrong_province("bad-code"), "provincia": "Milano"},
        ]
        after, report = reconcile(cases, REFERENCE, apply=True)
        self.assertEqual(after, cases)
        self.assertEqual(report["counts"]["province_fixed"], 0)
        self.assertEqual(check(cases, after, report)["changes"], 0)

    def test_source_receipts_calendars_and_human_claims_are_not_rewritten(self):
        receipt_row = wrong_province("actual-receipt")
        receipt_row["riscontri_campi"] = [make_receipt(
            receipt_row, values={"indirizzo": receipt_row["indirizzo"]},
            source_url=receipt_row["url_fonte"], source_name="Existing source",
            source_id="fixture", source_row="row-one", read_on=TODAY.isoformat(),
            source_updated_on="", source_sha256="a" * 64, scope="pagina",
            method="comune_provincia_giorno_univoco", fingerprint_kind="html_bytes")]
        cases = [receipt_row]
        for field in ("calendario_fonte", "dettaglio_fonte", "evidenza_editoriale",
                      "eccezioni_calendario", "identita_fonte", "id_fonte",
                      "citta_originale", "localita_ricostruita_da"):
            cases.append({**wrong_province(field), field: {"existing": "proof"}})
        cases.extend([
            {**wrong_province("human"), "verificato_il": "2026-10-11"},
            {**wrong_province("confirmed"), "date_quality": "confermata"},
        ])
        after, report = reconcile(cases, REFERENCE, apply=True)
        self.assertEqual(after, cases)
        self.assertEqual(report["counts"]["province_protected"], len(cases))
        self.assertEqual(check(cases, after, report)["changes"], 0)

    def test_same_80_total_budget_progresses_80_80_60_then_idempotent(self):
        rows = [wrong_province(f"market-{index:03}") for index in range(220)]
        rows.reverse()
        all_ids = [row["slug"] for row in rows]
        for count, pending in ((80, 140), (80, 60), (60, 0), (0, 0)):
            after, report = reconcile(rows, REFERENCE, apply=True)
            self.assertEqual(report["counts"]["province_fixed"], count)
            self.assertEqual(report["counts"]["province_pending"], pending)
            self.assertEqual(check(rows, after, report)["changes"], count)
            self.assertEqual([row["slug"] for row in after], all_ids)
            self.assertEqual(report["province_corrections"]["total_change_budget"], 80)
            selected = [proof["mercato"]["slug"] for proof in report["province_corrections"]["proofs"]]
            self.assertEqual(selected, sorted(selected))
            rows = after
        self.assertTrue(all(row["provincia"] == "MB" for row in rows))

    def test_existing_city_and_calendar_changes_consume_same_total_budget(self):
        city_case = market(
            "mercato-dei-contadini-a-somma-vesuviana-somma-vesuviana",
            "NA", "NA", "Campania", "Mercato Dei Contadini A Somma Vesuviana", "", [])
        cases = [city_case, *[wrong_province(f"market-{index:03}") for index in range(80)]]
        after, report = reconcile(cases, REFERENCE, apply=True)
        self.assertEqual(report["counts"]["city_fixed"], 1)
        self.assertEqual(report["counts"]["province_fixed"], 79)
        self.assertEqual(report["counts"]["province_pending"], 1)
        self.assertEqual(check(cases, after, report)["changes"], 80)

    def test_metadata_only_pin_cannot_hide_tampered_istat_correspondence(self):
        modified = deepcopy(REFERENCE)
        modified["provinces_by_region"]["Lombardia"]["Monza"] = "CO"
        with self.assertRaisesRegex(ValueError, "pinned content"):
            reconcile([wrong_province()], modified, apply=True)

    def test_report_and_receipt_tamper_or_unrelated_field_change_fail_closed(self):
        before = [wrong_province()]
        after, report = reconcile(before, REFERENCE, apply=True)
        for field, value in (("provincia", "CO"), ("lat", 10.0),
                             ("indirizzo", "Via diversa"), ("nome", "Another market"),
                             ("date", []), ("aggiornato_il", "2026-10-12")):
            bad = deepcopy(after)
            bad[0][field] = value
            with self.assertRaises(ValueError, msg=field):
                check(before, bad, report)
        for field, value in (("provincia_originale", "RM"), ("sha256_registro", "0" * 64),
                             ("data_riferimento", "2026-10-12"), ("schema", True)):
            bad = deepcopy(after)
            forged_report = deepcopy(report)
            bad[0][KEY][field] = value
            forged_report["province_corrections"]["proofs"][0][field] = value
            with self.assertRaises(ValueError, msg=field):
                check(before, bad, forged_report)
        shuffled = [wrong_province(f"market-{index:03}") for index in range(81)]
        changed, summary = reconcile(shuffled, REFERENCE, apply=True)
        changed[0] = shuffled[0]
        replacement, _ = reconcile([shuffled[-1]], REFERENCE, apply=True)
        changed[-1] = replacement[0]
        summary["province_corrections"]["proofs"][0] = replacement[0][KEY]
        with self.assertRaisesRegex(ValueError, "pinned ISTAT replay"):
            check(shuffled, changed, summary)

    def test_review_only_keeps_catalog_and_administration_dates_unchanged(self):
        before = [wrong_province()]
        after, report = reconcile(before, REFERENCE, apply=False)
        self.assertEqual(before, after)
        self.assertEqual(report["counts"]["province_candidates"], 1)
        self.assertEqual(report["counts"]["province_fixed"], 0)
        self.assertEqual(check(before, after, report)["changes"], 0)

    def test_normalization_export_offline_roundtrip_and_final_guard_keep_proof(self):
        original, error = normalize(wrong_province(), TODAY)
        self.assertIsNone(error)
        before = [original]
        after, report = reconcile(before, REFERENCE, apply=True)
        with tempfile.TemporaryDirectory() as folder:
            dest = Path(folder) / "data/v1"
            export(after, dest, today=TODAY)
            final = load_existing(dest / "manifest.json")
            self.assertEqual(final, after)
            self.assertEqual(verify_exported(before, after, report, final)["administrative_proofs_preserved"], 1)
            again, next_report = reconcile(final, REFERENCE, apply=True)
            self.assertEqual(again, final)
            self.assertEqual(next_report["counts"]["province_fixed"], 0)
            self.assertTrue(verify_exported(final, again, next_report, final)["release_safe"])
        for change in ("missing", "province", "proof", "identity"):
            bad = deepcopy(after)
            if change == "missing":
                bad = []
            elif change == "province":
                bad[0]["provincia"] = "MI"
            elif change == "proof":
                bad[0].pop(KEY)
            else:
                bad[0]["citta"] = "Milano"
            with self.assertRaises(ValueError, msg=change):
                verify_exported(before, after, report, bad)
        forged = deepcopy(after[0])
        forged[KEY]["sha256_registro"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "Invalid or identity-mismatched"):
            normalize(forged, TODAY)

    def test_final_guard_rejects_later_unproved_province_change(self):
        untouched = {**wrong_province("already-correct"), "provincia": "MB"}
        before = [wrong_province(), untouched]
        after, report = reconcile(before, REFERENCE, apply=True)
        bad = deepcopy(after)
        bad[1]["provincia"] = "MI"
        with self.assertRaisesRegex(ValueError, "Final province differs"):
            verify_exported(before, after, report, bad)

    def test_province_correction_only_keeps_the_page_that_still_lists_the_town(self):
        import happings_source_enrichment as source
        before = [wrong_province()]
        after, _ = reconcile(before, REFERENCE, apply=True)
        # Happings has no Monza page: MB towns stay on the Milano page.
        milano = "https://www.happings.com/it/mercati-settimanali-a-milano-e-provincia/"
        bergamo = "https://www.happings.com/it/mercati-settimanali-a-bergamo-e-provincia/"
        self.assertTrue(source._catalog_geography_matches(after[0], milano))
        self.assertFalse(source._catalog_geography_matches(after[0], bergamo))

    def test_non_istat_names_match_only_their_own_province_page(self):
        import happings_source_enrichment as source
        roma = "https://www.happings.com/it/mercati-settimanali-a-roma-e-provincia/"
        quartiere = market("casilino", "CASILINO", "RM", "Lazio", "Mercato settimanale di CASILINO")
        self.assertTrue(source._catalog_geography_matches(quartiere, roma))
        # A known ISTAT town filed under the wrong province is still rejected.
        viterbo = market("viterbo", "Viterbo", "RM", "Lazio", "Mercato settimanale di Viterbo")
        self.assertFalse(source._catalog_geography_matches(viterbo, roma))


if __name__ == "__main__":
    unittest.main()
