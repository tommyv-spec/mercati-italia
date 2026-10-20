import json
import sys
import tempfile
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from field_evidence import field_states
from export_static import normalize
from roma_d881_enrichment import (preview, verify_changes, verify_exported,
                                  hours_text, load_policy, EXPECTED_POLICY)
from source_roma_d881 import DATASET_PAGE, digest, parse_snapshot
from test_source_roma_d881 import (TODAY, snapshot, csv_with, metadata_with,
                                 new_distribution)


def row(name="Testaccio", address="Via Aldo Manuzio", **changes):
    value = {"slug": "existing-test-market", "nome": name, "citta": "Roma", "provincia": "RM",
             "regione": "Lazio", "indirizzo": address, "categoria": "alimentare",
             "orario_testo": "", "descrizione": "Plateatico — Municipio 1",
             "date": [], "date_quality": "sconosciuta", "ricorrenza_testo": "",
             "status": "non_confermato", "lat": 41.9, "lng": 12.5,
             "position_quality": "non_verificata", "verificato_il": "",
             "fonte": "dati.comune.roma.it", "url_fonte": DATASET_PAGE,
             "aggiornato_il": "2026-06-05T08:13:03.665593",
             "fonti": [{"nome": "dati.comune.roma.it", "url": DATASET_PAGE}]}
    value.update(changes)
    return value


def future_snapshot(*, updated="21/10/2026", close="18:30", day=date(2026, 10, 21)):
    def edit(rows):
        item = next(item for item in rows if item["Nome_Mercato"] == "Testaccio")
        item["AGGIORNATO"] = updated
        item["Chiusura_Martedi"] = close
    metadata = metadata_with(lambda package: new_distribution(package, day=day.isoformat()))
    return snapshot(csv_with(edit), metadata, day=day)


class RomaEnrichmentTests(unittest.TestCase):
    def test_exact_unique_existing_match_keeps_identity_street_dates_and_coordinates(self):
        base = [row()]
        result, report = preview(base, snapshot(), today=TODAY, apply=True)
        self.assertEqual(report["counts"], {"enriched": 1})
        self.assertEqual(report["new_market_ids"], [])
        self.assertEqual(len(result), 1)
        for field in set(base[0]) - {"orario_testo", "riscontri_campi"}:
            self.assertEqual(result[0][field], base[0][field], field)
        self.assertNotIn("fonte_aggiornata_il", result[0])
        self.assertNotIn("fonte_letta_il", result[0])
        self.assertIn("31/12/2021", result[0]["orario_testo"])
        self.assertIn("Domenica non indicata", result[0]["orario_testo"])
        self.assertEqual(field_states(result[0], today=TODAY)["orario_testo"], "riscontro_da_aggiornare")
        receipt = result[0]["riscontri_campi"][0]
        self.assertEqual(receipt["fonte_aggiornata_il"], "2021-12-31")
        self.assertEqual(receipt["letto_il"], TODAY.isoformat())
        self.assertEqual(receipt["metodo"], "nome_sede_comune_univoco")
        self.assertEqual(receipt["campi_gestiti"], ["orario_testo"])
        self.assertEqual(receipt["impronta_tipo"], "publisher_parsed_json")

    def test_noop_preview_never_changes_catalogue_or_timestamps(self):
        base = [row()]
        original = deepcopy(base)
        result, report = preview(base, snapshot(), today=TODAY)
        self.assertEqual(result, original)
        self.assertEqual(base, original)
        self.assertEqual(report["changes"], [])
        self.assertEqual(report["outcomes"][0]["status"], "candidate")

    def test_all_six_different_weekday_pairs_and_qualified_stall_hours_survive(self):
        facts = parse_snapshot(snapshot(), today=TODAY)["rows"]
        for fact in facts:
            text = hours_text(fact)
            for day in fact["hours_by_day"]:
                self.assertIn(day["day"] + " " + day["start"] + "–" + day["end"], text)
            for key in ("hours_notes", "market_notes"):
                if fact[key]:
                    self.assertIn(fact[key], text)
        fact = next(item for item in facts if item["name"] == "Parioli")
        self.assertIn("alcuni banchi", hours_text(fact))
        self.assertNotIn("07:00–23:00", hours_text(fact))

    def test_held_names_streets_and_geographies_never_fuzzy_match(self):
        variants = [row(name="Nuovo Cinecitt�", address="Largo Giulio Capitolino"),
                    row(name="Prati", address="Piazza dell'Unit�"),
                    row(name="Testacci"), row(address="Via Aldo Manuzzio"), row(address=""),
                    row(provincia="MI"), row(citta="Romano"), row(regione="Lombardia"),
                    row(descrizione="Plateatico — Municipio 9")]
        for item in variants:
            with self.subTest(item=item["nome"] + item["indirizzo"]):
                result, report = preview([item], snapshot(), today=TODAY, apply=True)
                self.assertEqual(result, [item])
                self.assertEqual(report["outcomes"][0]["status"], "held")

    def test_primary_dataset_url_required_not_host_or_secondary_link(self):
        for url in (DATASET_PAGE + "?other=1", "https://dati.comune.roma.it/catalog/dataset/other",
                    "https://example.org/testaccio"):
            base = [row(url_fonte=url)]
            result, report = preview(base, snapshot(), today=TODAY, apply=True)
            self.assertEqual(result, base)
            self.assertEqual(report["outcomes"], [])

    def test_duplicate_source_identity_even_with_bad_hours_is_ambiguous(self):
        def add_duplicate(rows):
            duplicate = deepcopy(next(item for item in rows if item["Nome_Mercato"] == "Testaccio"))
            duplicate["Apertura_Lunedi"] = "not a clock"
            rows.append(duplicate)
        base = [row()]
        result, report = preview(base, snapshot(csv_with(add_duplicate)), today=TODAY, apply=True)
        self.assertEqual(result, base)
        self.assertEqual(report["outcomes"][0]["reason"], "ambiguous_source_identity")

    def test_duplicate_catalogue_tuple_is_held_and_duplicate_id_rejected(self):
        base = [row(), row(slug="another-existing-id")]
        result, report = preview(base, snapshot(), today=TODAY, apply=True)
        self.assertEqual(result, base)
        self.assertEqual(report["counts"]["ambiguous_catalog_identity"], 2)
        with self.assertRaises(ValueError):
            preview([row(), row()], snapshot(), today=TODAY, apply=True)

    def test_corrupt_source_row_is_held_without_dropping_existing_market(self):
        def corrupt(rows):
            next(item for item in rows if item["Nome_Mercato"] == "Testaccio")["Apertura_Lunedi"] = "25:00"
        base = [row()]
        result, report = preview(base, snapshot(csv_with(corrupt)), today=TODAY, apply=True)
        self.assertEqual(result, base)
        self.assertEqual(report["outcomes"][0]["reason"], "source_row_held")

    def test_new_distribution_updates_owned_hours_but_never_the_old_recurrence(self):
        base = [row(ricorrenza_testo="settimanale - domenica", date=["2026-10-25"],
                    date_quality="prevista", fonte_aggiornata_il="2021-12-31",
                    fonte_letta_il="2026-06-05")]
        first, _ = preview(base, snapshot(), today=TODAY, apply=True)
        tomorrow = date(2026, 10, 21)
        future, report = preview(first, future_snapshot(), today=tomorrow, apply=True)
        self.assertIn("martedì 07:00–18:30", future[0]["orario_testo"])
        self.assertIn("21/10/2026", future[0]["orario_testo"])
        self.assertEqual(future[0]["slug"], base[0]["slug"])
        for field in ("ricorrenza_testo", "date", "date_quality", "fonte_aggiornata_il", "fonte_letta_il"):
            self.assertEqual(future[0][field], base[0][field], field)
        self.assertEqual(field_states(future[0], today=tomorrow)["orario_testo"], "riscontrato_fonte_recente")
        receipt = future[0]["riscontri_campi"][0]
        self.assertEqual(receipt["fonte_aggiornata_il"], "2026-10-21")
        self.assertEqual(receipt["versioni_precedenti"][0]["fonte_aggiornata_il"], "2021-12-31")
        self.assertEqual(report["calendars_generated"], 0)

    def test_user_changes_newer_proofs_and_source_date_regression_block_overwrite(self):
        first, _ = preview([row()], snapshot(), today=TODAY, apply=True)
        manual = deepcopy(first)
        manual[0]["orario_testo"] = "Orari confermati direttamente dal Comune: 09:00–12:00"
        tomorrow = date(2026, 10, 21)
        for base, captured in [(manual, future_snapshot()),
                               (first, future_snapshot(updated="30/04/2020"))]:
            result, report = preview(base, captured, today=tomorrow, apply=True)
            self.assertEqual(result, base)
            self.assertEqual(report["outcomes"][0]["reason"], "existing_hours_conflict")

    def test_nonempty_existing_hours_and_verified_records_are_not_taken_over(self):
        for original in (row(orario_testo="07:00–14:00"), row(verificato_il="2026-10-19")):
            result, report = preview([original], snapshot(), today=TODAY, apply=True)
            self.assertEqual(result, [original])
            self.assertEqual(report["outcomes"][0]["status"], "held")

    def test_same_value_preexisting_text_gains_evidence_but_not_ownership(self):
        fact = next(item for item in parse_snapshot(snapshot(), today=TODAY)["rows"] if item["name"] == "Testaccio")
        result, _ = preview([row(orario_testo=hours_text(fact))], snapshot(), today=TODAY, apply=True)
        self.assertNotIn("campi_gestiti", result[0]["riscontri_campi"][0])
        tomorrow = date(2026, 10, 21)
        later, report = preview(result, future_snapshot(), today=tomorrow, apply=True)
        self.assertEqual(later, result)
        self.assertEqual(report["outcomes"][0]["reason"], "existing_hours_conflict")

    def test_fresh_read_of_same_old_document_stays_stale_and_idempotent(self):
        first, _ = preview([row()], snapshot(), today=TODAY, apply=True)
        same, report = preview(first, snapshot(), today=TODAY, apply=True)
        self.assertEqual(same, first)
        self.assertEqual(report["changes"], [])
        tomorrow = date(2026, 10, 21)
        later, _ = preview(first, snapshot(day=tomorrow), today=tomorrow, apply=True)
        self.assertEqual(later[0]["orario_testo"], first[0]["orario_testo"])
        self.assertEqual(field_states(later[0], today=tomorrow)["orario_testo"], "riscontro_da_aggiornare")
        self.assertEqual(later[0]["riscontri_campi"][0]["letto_il"], "2026-10-21")
        self.assertEqual(later[0]["riscontri_campi"][0]["campi_gestiti"], ["orario_testo"])

    def test_final_verifier_reconstructs_from_bytes_not_recomputed_hashes(self):
        base = [row()]
        result, report = preview(base, snapshot(), today=TODAY, apply=True)
        forged = deepcopy(result)
        forged[0]["orario_testo"] = "08:00–20:00"
        forged_report = deepcopy(report)
        forged_report["output_sha256"] = digest(forged)
        with self.assertRaises(ValueError):
            verify_changes(base, forged, forged_report, today=TODAY)
        forged_report = deepcopy(report)
        forged_report["document"]["rows"][0]["source_updated_on"] = "2026-10-20"
        with self.assertRaisesRegex(ValueError, "captured source bytes"):
            verify_changes(base, result, forged_report, today=TODAY)
        for field, value in [("indirizzo", "Invented street"), ("date", ["2026-10-21"]),
                             ("lat", 42.0), ("fonte_aggiornata_il", "2026-10-20")]:
            forged = deepcopy(result)
            forged[0][field] = value
            forged_report = deepcopy(report)
            forged_report["output_sha256"] = digest(forged)
            with self.subTest(field=field), self.assertRaises(ValueError):
                verify_changes(base, forged, forged_report, today=TODAY)

    def test_export_preserves_stale_evidence_and_checks_held_record_too(self):
        base = [row(), row(name="Prati", address="Piazza dell'Unit�", slug="existing-held")]
        result, report = preview(base, snapshot(), today=TODAY, apply=True)
        exported = [normalize(item, TODAY)[0] for item in result]
        proof = verify_exported(base, exported, report, today=TODAY)
        self.assertEqual(proof["checked_count"], 2)
        self.assertEqual(field_states(exported[0], today=TODAY)["orario_testo"], "riscontro_da_aggiornare")
        exported[1]["indirizzo"] = "Piazza dell'Unità"
        with self.assertRaises(ValueError):
            verify_exported(base, exported, report, today=TODAY)

    def test_bounded_policy_is_explicit_and_cannot_enable_admissions(self):
        self.assertEqual(load_policy(), EXPECTED_POLICY)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "policy.json"
            changed = deepcopy(EXPECTED_POLICY)
            changed["admit_new"] = True
            path.write_text(json.dumps(changed))
            with self.assertRaises(ValueError):
                load_policy(path)


if __name__ == "__main__":
    unittest.main()
