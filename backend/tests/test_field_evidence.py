"""Evidence is tied to exact fields, dates and identities, never a whole event."""
import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from field_evidence import (attach_feed_observations, audit, clean_receipts,
                            field_states, make_receipt)
from merge_catalog import combine
from source_freshness import source_date_evidence

TODAY = date(2026, 10, 19)


def market(**changes):
    row = {"slug": "field-fixture", "nome": "Mercato fixture", "citta": "Firenze",
           "provincia": "FI", "regione": "Toscana", "indirizzo": "Via Test",
           "orario_testo": "08:00-13:00", "ricorrenza_testo": "Ogni lunedì",
           "fonte": "Fonte fixture", "url_fonte": "https://example.org/market",
           "aggiornato_il": "2026-10-01", "date": ["2026-10-26"],
           "date_quality": "prevista", "verificato_il": "", "status": "non_confermato"}
    row.update(changes)
    return row


def receipt(row, *, fields=("indirizzo", "orario_testo", "ricorrenza_testo"),
            read="2026-10-19", content_date="2026-10-01"):
    return make_receipt(row, values={field: row[field] for field in fields},
                        source_url="https://example.org/source", source_name="Fonte fixture",
                        source_id="fixture", source_row="row-1", read_on=read,
                        source_updated_on=content_date, source_sha256="a" * 64)


class FieldEvidenceTests(unittest.TestCase):
    def test_changed_field_loses_only_its_own_observation(self):
        original = market()
        proof = receipt(original)
        changed = market(indirizzo="Via diversa", riscontri_campi=[proof])
        cleaned = clean_receipts(changed["riscontri_campi"], changed, today=TODAY)
        self.assertEqual(set(cleaned[0]["valori"]), {"orario_testo", "ricorrenza_testo"})
        states = field_states(changed, today=TODAY)
        self.assertEqual(states["indirizzo"], "senza_riscontro_documentato")
        self.assertEqual(states["orario_testo"], "riscontrato_fonte_recente")
        self.assertIn("indirizzo", proof["valori"])

    def test_different_market_identity_cannot_reuse_an_observation(self):
        original = market()
        for change in ({"slug": "other-market"}, {"citta": "Prato"},
                       {"provincia": "PO"}, {"regione": "Lazio"}):
            with self.subTest(change=change):
                changed = {**original, **change, "riscontri_campi": [receipt(original)]}
                self.assertEqual(clean_receipts(changed["riscontri_campi"], changed, today=TODAY), [])

    def test_historical_source_read_today_is_not_current_evidence(self):
        row = market()
        row["riscontri_campi"] = [receipt(row, content_date="2020-01-01")]
        self.assertEqual(set(field_states(row, today=TODAY).values()), {"riscontro_da_aggiornare"})

    def test_unknown_source_date_is_not_filled_from_a_recent_read(self):
        row = market()
        row["riscontri_campi"] = [receipt(row, content_date="")]
        self.assertEqual(set(field_states(row, today=TODAY).values()),
                         {"riscontrato_data_fonte_sconosciuta"})
        self.assertEqual(row["verificato_il"], "")

    def test_recent_source_content_does_not_refresh_an_old_read(self):
        row = market()
        row["riscontri_campi"] = [receipt(row, read="2026-08-01", content_date="2026-08-01")]
        self.assertEqual(set(field_states(row, today=TODAY).values()), {"riscontro_da_aggiornare"})

    def test_age_limits_are_specific_to_each_field(self):
        row = market()
        row["riscontri_campi"] = [receipt(row, content_date="2026-03-01")]
        states = field_states(row, today=TODAY)
        self.assertEqual(states["indirizzo"], "riscontrato_fonte_recente")
        self.assertEqual(states["orario_testo"], "riscontro_da_aggiornare")
        self.assertEqual(states["ricorrenza_testo"], "riscontro_da_aggiornare")

    def test_future_or_badly_bound_source_dates_are_rejected(self):
        row = market()
        proof = receipt(row)
        for changes in ({"letto_il": "2026-10-20"}, {"fonte_aggiornata_il": "2026-10-20"},
                        {"fonte_aggiornata_il": "2026-02-30"}, {"sha256": "not-a-fingerprint"}):
            with self.subTest(changes=changes):
                self.assertEqual(clean_receipts([{**proof, **changes}], row, today=TODAY), [])

    def test_one_supported_field_does_not_verify_all_fields_or_opening(self):
        first = market()
        first["riscontri_campi"] = [receipt(first, fields=("indirizzo",))]
        second = market(slug="other", fonte="Fonte diversa")
        before = deepcopy([first, second])
        result = audit([first, second], today=TODAY)
        self.assertEqual(result["metrics"]["markets"], 2)
        self.assertEqual(result["metrics"]["markets_with_recent_field_evidence"], 1)
        self.assertEqual(result["metrics"].get("markets_with_all_three_fields_source_supported", 0), 0)
        self.assertEqual(sum(item["markets"] for item in result["publishers"]), 2)
        self.assertEqual(len(result["markets"]), 2)
        self.assertEqual([first, second], before)

    def test_live_adapter_attachment_keeps_source_content_date_distinct_from_read(self):
        original = market(aggiornato_il="2020-01-01")
        result = attach_feed_observations("firenze", {"fixture": "raw publisher data"},
                                          [original], read_on="2026-10-19")
        row = result[0]
        self.assertEqual(row["fonte_letta_il"], "2026-10-19")
        self.assertEqual(row["fonte_aggiornata_il"], "2020-01-01")
        self.assertEqual(set(field_states(row, today=TODAY).values()), {"riscontro_da_aggiornare"})
        self.assertEqual(row["date"], original["date"])
        self.assertEqual(row["verificato_il"], "")
        self.assertNotIn("fonte_letta_il", original)


class EvidenceMergeRegressionTests(unittest.TestCase):
    def test_later_legacy_import_cannot_beat_a_documented_publisher_date(self):
        old = market(fonte_aggiornata_il="2026-01-01", indirizzo="Via documentata")
        incoming = market(aggiornato_il="2026-10-19T12:00:00",
                          url_fonte="https://other.example/import", indirizzo="Via da import")
        rows, _ = combine([old], [incoming])
        self.assertEqual(rows[0]["indirizzo"], old["indirizzo"])
        self.assertEqual(rows[0]["url_fonte"], old["url_fonte"])
        self.assertEqual(rows[0]["fonte_aggiornata_il"], "2026-01-01")

    def test_incoming_publisher_date_beats_a_later_unqualified_legacy_import(self):
        old = market(aggiornato_il="2026-10-19T12:00:00", indirizzo="Via legacy")
        incoming = market(aggiornato_il="2026-01-01", fonte_aggiornata_il="2026-01-01",
                          url_fonte="https://other.example/source", indirizzo="Via documentata")
        rows, _ = combine([old], [incoming])
        self.assertEqual(rows[0]["indirizzo"], incoming["indirizzo"])
        self.assertEqual(rows[0]["url_fonte"], incoming["url_fonte"])
        self.assertEqual(rows[0]["slug"], old["slug"])

    def test_timestamps_never_move_from_losing_to_winning_primary_source(self):
        old = market(verificato_il="2026-09-01")
        incoming = market(url_fonte="https://other.example/source", fonte_aggiornata_il="2026-10-01",
                          fonte_letta_il="2026-10-19", importato_il="2026-10-19T12:00:00+00:00")
        rows, _ = combine([old], [incoming])
        self.assertEqual(rows[0]["url_fonte"], old["url_fonte"])
        for field in ("fonte_aggiornata_il", "fonte_letta_il", "importato_il"):
            self.assertNotIn(field, rows[0])

    def test_newer_content_date_does_not_inherit_the_other_sources_read_time(self):
        old = market(fonte_aggiornata_il="2026-01-01", fonte_letta_il="2026-10-19")
        incoming = market(url_fonte="https://other.example/source", fonte_aggiornata_il="2026-10-01")
        rows, _ = combine([old], [incoming])
        self.assertEqual(rows[0]["url_fonte"], incoming["url_fonte"])
        self.assertNotIn("fonte_letta_il", rows[0])

    def test_new_read_without_dates_does_not_resurrect_old_forecasts_or_date_source(self):
        old = market()
        incoming = market(fonte_letta_il="2026-10-19", date=[], date_quality="sconosciuta")
        rows, _ = combine([old], [incoming])
        self.assertEqual(rows[0]["date"], [])
        self.assertEqual(rows[0]["date_quality"], "sconosciuta")
        self.assertEqual(source_date_evidence(rows[0])["basis"], "unknown")
        self.assertEqual(old["date"], ["2026-10-26"])


if __name__ == "__main__":
    unittest.main()
