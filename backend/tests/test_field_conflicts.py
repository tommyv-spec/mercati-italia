"""Negative evidence never replaces a field or becomes positive confirmation."""
from copy import deepcopy
from datetime import date
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from export_static import export, normalize, prepare
from field_conflicts import (KEY, MAX_CONFLICTS, MAX_SOURCE_BYTES, clean_conflicts,
                             make_address_conflict, valid_conflict)
from field_evidence import field_states
from merge_catalog import combine, load_existing
from validate_static import validate

TODAY = date(2026, 10, 20)
REQUESTED = "https://www.happings.com/it/mercati-settimanali-a-lucca.html"
FINAL = "https://www.happings.com/it/mercati-settimanali-a-lucca-e-provincia/"
SELECTOR = ("main#main article.hpe-editorial--local-guide .hpe-editorial-grid"
            " > .hpe-editorial-body > p:nth-child(2)")
# Exact relevant paragraph from the captured LIVE #7 provincial page. The
# test does not claim to establish the separate full-catalogue association.
FRAGMENT = (
    "Il mercato settimanale di Lucca si svolge a Piazzale Don Baroni il mercoledì "
    "e il sabato, dalle 8:00 alle 13:00. A Ponte a Moriano l’appuntamento è il "
    "martedì in Piazza del Popolo, dalle 8:00 alle 13:00. Queste indicazioni "
    "sostituiscono i vecchi riferimenti al mercato cittadino in Piazza del "
    "Carmine e in Via dei Bacchettoni."
)


def market(**changes):
    row = {
        "slug": "mercato-settimanale-a-lucca-mercoledi", "nome": "Mercato settimanale a Lucca",
        "citta": "Lucca", "provincia": "LU", "regione": "Toscana", "categoria": "misto",
        "fonte": "happings.com", "url_fonte": REQUESTED, "indirizzo": "Piazza del Carmine",
        "ricorrenza_testo": "Ogni mercoledì", "orario_testo": "", "date": ["2026-10-21"],
        "date_quality": "prevista", "verificato_il": "", "status": "non_confermato",
        "lat": 43.84, "lng": 10.5, "position_quality": "non_verificata",
    }
    return {**row, **changes}


def conflict(row=None, **changes):
    row = row or market()
    args = {
        "source_value": "Piazzale Don Baroni", "source_day": 2,
        "requested_url": REQUESTED, "final_url": FINAL, "read_on": "2026-10-20",
        "html_sha256": "7da91da612bba4e282f50c0ea254a804d877c1c81bfbf65eaa1b54abe1e9e1fd",
        "source_bytes": 48_000, "selector": SELECTOR, "fragment": FRAGMENT, "today": TODAY,
    }
    return make_address_conflict(row, **{**args, **changes})


class FieldConflictTests(unittest.TestCase):
    def test_explicit_negative_evidence_does_not_replace_or_verify_any_field(self):
        row = market()
        proof = conflict(row)
        before = deepcopy(row)
        self.assertTrue(valid_conflict(proof, row, today=TODAY))
        bound = {**row, KEY: [proof]}
        baseline, error = normalize(row, TODAY)
        result, result_error = normalize(bound, TODAY)
        self.assertIsNone(error)
        self.assertIsNone(result_error)
        self.assertEqual(result.pop(KEY), [proof])
        self.assertEqual(result, baseline)
        self.assertEqual(row, before)
        self.assertEqual(field_states(bound, today=TODAY), field_states(row, today=TODAY))
        self.assertEqual(field_states(bound, today=TODAY)["indirizzo"], "senza_riscontro_documentato")
        self.assertNotIn("riscontri_campi", bound)
        self.assertEqual(proof["prova"]["sede_precedente"], row["indirizzo"])

    def test_every_saved_identity_component_is_bound_exactly(self):
        row = market()
        proof = conflict(row)
        for key in ("slug", "nome", "citta", "provincia", "regione", "fonte", "url_fonte"):
            with self.subTest(key=key):
                revised = {**row, key: row[key] + "-changed"}
                self.assertFalse(valid_conflict(proof, revised, today=TODAY))
                self.assertEqual(clean_conflicts([proof], revised, today=TODAY), [])
        for replacement in ("Piazzale Don Baroni", "Piazza diversa", "", None):
            with self.subTest(address=replacement):
                revised = {**row, "indirizzo": replacement}
                self.assertEqual(clean_conflicts([proof], revised, today=TODAY), [])
                output, error = normalize({**revised, KEY: [proof]}, TODAY)
                self.assertIsNone(error)
                self.assertNotIn(KEY, output)

    def test_shape_and_hash_bounds_are_strict(self):
        row, proof = market(), conflict()
        mutations = [
            {"schema": True}, {"schema": 2}, {"gestore": "unknown"}, {"campo": "orario_testo"},
            {"extra": "not allowed"}, {"sha256": "a" * 63}, {"sha256": "A" * 64},
            {"bytes": True}, {"bytes": 0}, {"bytes": MAX_SOURCE_BYTES + 1},
            {"giorno_settimana": True}, {"giorno_settimana": -1}, {"giorno_settimana": 7},
            {"letto_il": "2026-10-21"}, {"letto_il": "2026-02-30"},
            {"letto_il": "2026-10-20T00:00:00Z"},
            {"mercato": {**proof["mercato"], "extra": "ignored"}},
            {"prova": {**proof["prova"], "extra": "ignored"}},
        ]
        for change in mutations:
            with self.subTest(change=change):
                self.assertFalse(valid_conflict({**proof, **change}, row, today=TODAY))
        for missing in proof:
            revised = {k: v for k, v in proof.items() if k != missing}
            with self.subTest(missing=missing):
                self.assertFalse(valid_conflict(revised, row, today=TODAY))

    def test_province_urls_are_exact_reviewed_shapes_and_same_scope(self):
        row, proof = market(), conflict()
        invalid = (
            "http://www.happings.com/it/mercati-settimanali-a-lucca.html",
            "https://happings.com/it/mercati-settimanali-a-lucca.html",
            "https://www.happings.com.evil.test/it/mercati-settimanali-a-lucca.html",
            "https://user@www.happings.com/it/mercati-settimanali-a-lucca.html",
            "https://www.happings.com:444/it/mercati-settimanali-a-lucca.html",
            "https://www.happings.com/it/happing/mercato-a-lucca/",
            "https://www.happings.com/it/mercato-settimanale-a-lucca.html",
            "https://www.happings.com/it/mercati-settimanali-a-pisa-e-provincia/",
            FINAL + "?claimed_source=lucca", FINAL + "#source", FINAL + "../",
        )
        for key in ("url_richiesto", "url_finale"):
            for url in invalid:
                with self.subTest(key=key, url=url):
                    self.assertFalse(valid_conflict({**proof, key: url}, row, today=TODAY))

    def test_old_read_remains_a_warning_not_a_recent_or_positive_source_claim(self):
        proof = conflict(read_on="2021-01-01")
        row = market(**{KEY: [proof]})
        self.assertTrue(valid_conflict(proof, row, today=TODAY))
        self.assertEqual(clean_conflicts(row[KEY], row, today=TODAY), [proof])
        self.assertEqual(field_states(row, today=TODAY)["indirizzo"], "senza_riscontro_documentato")

    def test_mere_disagreement_absence_and_reversed_or_unbounded_fragments_are_rejected(self):
        row, proof = market(), conflict()
        bad_fragments = (
            "Il mercato è in Piazzale Don Baroni. Prima era in Piazza del Carmine.",
            "Piazza del Carmine. Queste indicazioni sostituiscono i vecchi riferimenti a Piazzale Don Baroni.",
            "Piazzale Don Baroni. Queste indicazioni sostituiscono i vecchi riferimenti al centro storico.",
            FRAGMENT + " " + FRAGMENT, FRAGMENT + "\n", FRAGMENT + "x" * 1200,
        )
        for text in bad_fragments:
            item = {**proof, "prova": {**proof["prova"], "frammento": text}}
            with self.subTest(fragment=text[:80]):
                self.assertFalse(valid_conflict(item, row, today=TODAY))
        for key, text in (("sede_precedente", "Via dei Bacchettoni"),
                          ("sede_attuale", "Piazza del Popolo")):
            self.assertFalse(valid_conflict({**proof, "prova": {**proof["prova"], key: text}}, row, today=TODAY))
        self.assertFalse(valid_conflict({**proof, "prova": {**proof["prova"], "tipo": "different_address"}}, row, today=TODAY))

    def test_address_substrings_and_equivalent_old_new_addresses_are_not_conflicts(self):
        with self.assertRaises(ValueError):
            conflict(source_value="PIAZZA DEL CARMINE")
        with self.assertRaises(ValueError):
            conflict(market(indirizzo="Via dei Bacche"))
        for place in ("centro storico", "Lucca", "Via X", "sede da definire", "Via X " + "x" * 190):
            with self.subTest(place=place), self.assertRaises(ValueError):
                conflict(source_value=place)

    def test_selector_is_bound_to_reviewed_current_paragraph_structure(self):
        proof, row = conflict(), market()
        for selector in ("body", "p:nth-child(2)", SELECTOR.replace("(2)", "(0)"),
                         SELECTOR.replace("(2)", "(201)"), SELECTOR.replace("(2)", "(02)"),
                         SELECTOR.replace(" > p:", " > ul > li:"), SELECTOR + " span"):
            item = {**proof, "prova": {**proof["prova"], "selettore": selector}}
            with self.subTest(selector=selector):
                self.assertFalse(valid_conflict(item, row, today=TODAY))

    def test_cleaning_is_bounded_copied_deduplicated_and_deterministic(self):
        proof, row = conflict(), market()
        newer = deepcopy(proof)
        older = conflict(read_on="2026-10-19")
        inputs = [older, newer, deepcopy(older)]
        snapshot = deepcopy(inputs)
        result = clean_conflicts(inputs, row, today=TODAY)
        self.assertEqual(result, [newer, older])
        self.assertEqual(inputs, snapshot)
        result[0]["prova"]["frammento"] = "changed"
        self.assertEqual(inputs, snapshot)
        for value in (None, {}, proof, [proof] * (MAX_CONFLICTS + 1)):
            self.assertEqual(clean_conflicts(value, row, today=TODAY), [])
        self.assertEqual(clean_conflicts([{**proof, "sha256": "bad"}, proof], row, today=TODAY), [proof])

    def test_valid_negative_evidence_protects_identity_from_export_merging(self):
        first = market(slug="first-id")
        second = market(slug="second-id")
        second[KEY] = [conflict(second)]
        rows, stats = prepare([first, second], TODAY)
        self.assertEqual({r["slug"] for r in rows}, {"first-id", "second-id"})
        self.assertEqual(stats["same_source_duplicates_merged"], 0)
        duplicate = {**second, "indirizzo": "Via dei Bacchettoni"}
        with self.assertRaisesRegex(ValueError, "protected"):
            prepare([second, duplicate], TODAY)

    def test_invalid_negative_envelope_cannot_acquire_export_identity_protection(self):
        first = market(slug="first-id")
        second = market(slug="second-id")
        bad = conflict(second)
        bad["sha256"] = "invalid"
        rows, stats = prepare([first, {**second, KEY: [bad]}], TODAY)
        self.assertEqual(len(rows), 1)
        self.assertEqual(stats["same_source_duplicates_merged"], 1)
        self.assertNotIn(KEY, rows[0])

    def test_same_id_merge_and_full_static_roundtrip_preserve_negative_evidence_only(self):
        row = market()
        row[KEY] = [conflict(row)]
        merged, _ = combine([row], [{**market(), "fonte_letta_il": "2026-10-20"}])
        self.assertEqual(merged[0][KEY], row[KEY])
        expected, error = normalize(merged[0], TODAY)
        self.assertIsNone(error)
        with tempfile.TemporaryDirectory() as directory:
            public = Path(directory) / "public"
            export(merged, public / "data/v1", today=TODAY)
            manifest = public / "data/v1/manifest.json"
            self.assertEqual(validate(manifest)["records"], 1)
            exported = load_existing(manifest)
            self.assertEqual(exported, [expected])
            self.assertEqual(exported[0][KEY], row[KEY])
            second_public = Path(directory) / "again/public"
            export(exported, second_public / "data/v1", today=TODAY)
            self.assertEqual(load_existing(second_public / "data/v1/manifest.json"), exported)
            m = json.loads(manifest.read_text())
            index = json.loads((public / m["index"]).read_text())
            self.assertNotIn(KEY, json.dumps(index))
            self.assertEqual(exported[0]["indirizzo"], "Piazza del Carmine")
            self.assertEqual(exported[0]["lat"], row["lat"])
            self.assertEqual(exported[0]["lng"], row["lng"])
            self.assertEqual(exported[0]["date"], row["date"])
            self.assertEqual(exported[0]["verificato_il"], "")


if __name__ == "__main__":
    unittest.main()
