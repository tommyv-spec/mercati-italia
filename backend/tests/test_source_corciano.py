import csv
import hashlib
import io
import unittest
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from source_corciano import (
    SOURCE_URL, DATASET_DECLARED_DATE, HEADERS, download, parse_csv,
    convert, coordinates, safe_url, project, fetch_csv
)
from export_static import normalize

DATA = (
    "denominazione;giorni_svolgimento;tipo_strada;ubicazione;numero_tot_posteggi;"
    "numero_posteggi_riservati;orario_svolgimento_dalle;orario_svolgimento_alle;"
    "long;lat;geopoint\n"
    "MERCATO DI MANTIGNANA;LUNEDI;PIAZZA;GIOVANNI ERCOLANI;5;1;07:30;14:00;"
    "43.16083199538295;12.285842603579857;(43.16083199538295,12.285842603579857)\n"
    "MERCATO DI SAN MARIANO;MARTEDI;VIA;ALDO MORO;8;2;07:30;14:00;"
    "43.089055028914366;12.309725879769752;(43.089055028914366,12.309725879769752)\n"
    "MERCATO DI CORCIANO;MERCOLEDI;PIAZZA;CADUTI;3;1;07:30;14:00;"
    "43.12865722653829;12.28622486563546;(43.12865722653829,12.28622486563546)\n"
    "MERCATO DI ELLERA;VENERDI;PIAZZA;DELLA CROCE ROSSA;15;3;07:30;14:00;"
    "43.10389696931246;12.317285858345878;(43.10389696931246,12.317285858345878)\n"
)
TODAY = date(2026, 10, 12)


def raw(data=DATA):
    return data.encode("utf-8")


class CorcianoTests(unittest.TestCase):
    def test_real_four_records_not_four_different_cities(self):
        item = parse_csv(raw())
        self.assertEqual(item["expected_rows"], 4)
        self.assertEqual(item["source_sha256"], hashlib.sha256(raw()).hexdigest())
        rows = convert(item, TODAY)
        self.assertEqual(len(rows), 4)
        self.assertEqual({r["citta"] for r in rows}, {"Corciano"})
        self.assertEqual({r["regione"] for r in rows}, {"Umbria"})
        self.assertEqual({r["provincia"] for r in rows}, {"PG"})
        self.assertEqual({r["date_quality"] for r in rows}, {"prevista"})
        self.assertEqual({r["aggiornato_il"] for r in rows}, {DATASET_DECLARED_DATE})
        self.assertEqual({r["aggiornamento_ambito"] for r in rows}, {"dataset"})
        self.assertTrue(all(not r["verificato_il"] for r in rows))
        self.assertTrue(all(r["position_quality"] != "precisa" for r in rows))

    def test_inverted_headers_are_corrected_from_real_geopoint_evidence(self):
        item = parse_csv(raw())
        self.assertEqual(coordinates(item["rows"][0]), (43.160832, 12.285843))
        self.assertEqual(coordinates(item["rows"][1]), (43.089055, 12.309726))
        self.assertEqual(coordinates(item["rows"][2]), (43.128657, 12.286225))
        self.assertEqual(coordinates(item["rows"][3]), (43.103897, 12.317286))
        out = convert(item, TODAY)
        first = next(r for r in out if r["nome"] == "Mercato Di Mantignana")
        self.assertIn("Piazza Giovanni Ercolani, Mantignana", first["indirizzo"])
        self.assertEqual(first["lat"], 43.160832)
        self.assertEqual(first["lng"], 12.285843)
        self.assertEqual(first["date_quality"], "prevista")
        self.assertEqual(date.fromisoformat(first["date"][0]).weekday(), 0)

    def test_weekday_calendar_has_no_unverified_confirmations(self):
        rows = convert(parse_csv(raw()), TODAY)
        weekdays = {r["nome"]: date.fromisoformat(r["date"][0]).weekday() for r in rows}
        self.assertEqual(weekdays["Mercato Di Mantignana"], 0)
        self.assertEqual(weekdays["Mercato Di San Mariano"], 1)
        self.assertEqual(weekdays["Mercato Di Corciano"], 2)
        self.assertEqual(weekdays["Mercato Di Ellera"], 4)
        for item in rows:
            self.assertTrue(all(date.fromisoformat(v) >= TODAY for v in item["date"]))
            self.assertEqual(item["status"], "non_confermato")
            norm, reason = normalize(item, TODAY)
            self.assertIsNone(reason)
            self.assertEqual(norm["position_quality"], "non_verificata")
            self.assertEqual(norm["aggiornamento_ambito"], "dataset")
            self.assertNotIn("source_csv_sha256", norm)

    def test_source_freshness_uses_declared_dataset_not_page_update(self):
        rows = convert(parse_csv(raw()), TODAY)
        self.assertEqual(rows[0]["aggiornato_il"], "2026-01-07")
        self.assertNotEqual(rows[0]["aggiornato_il"], "2026-07-27")
        old = convert(parse_csv(raw()), date(2027, 10, 13))
        self.assertTrue(all(not r["date"] for r in old))
        self.assertTrue(all(r["date_quality"] == "sconosciuta" for r in old))

    def test_changed_latitude_columns_fail_closed(self):
        incorrectly_labeled = raw().decode().replace(
            "43.16083199538295;12.285842603579857;",
            "12.285842603579857;43.16083199538295;"
        )
        with self.assertRaisesRegex(ValueError, "coordinates or schema"):
            convert(parse_csv(raw(incorrectly_labeled)), TODAY)

    def test_broken_geopoint_is_not_trusted(self):
        broken = raw().decode().replace(
            "(43.16083199538295,12.285842603579857)",
            "(44.000000,11.000000)")
        with self.assertRaisesRegex(ValueError, "coordinates or schema"):
            convert(parse_csv(raw(broken)), TODAY)

    def test_unknown_day_rejected_no_guessing(self):
        broken = raw().decode().replace(";LUNEDI;",";SETTIMANALE;")
        with self.assertRaisesRegex(ValueError, "identity/day"):
            convert(parse_csv(raw(broken)), TODAY)

    def test_broken_hour_and_stall_count_rejected(self):
        for value in (raw().decode().replace(";07:30;14:00;",";00:00;00:00;",1),
                      raw().decode().replace(";5;1;",";1;5;",1)):
            with self.assertRaises(ValueError):
                convert(parse_csv(raw(value)), TODAY)

    def test_partial_source_and_malformed_structure_rejected(self):
        rows=raw().decode().splitlines(keepends=True)
        with self.assertRaisesRegex(ValueError, "count changed"):
            parse_csv(raw("".join(rows[:-1])))
        with self.assertRaisesRegex(ValueError, "schema changed"):
            parse_csv(raw().replace(b";long;lat;geopoint", b";lng;lat;geopoint"))
        with self.assertRaisesRegex(ValueError, "bounded CSV"):
            parse_csv(raw(b"x" * 16385))

    def test_duplicate_derived_source_identity_refused(self):
        lines=raw().decode().splitlines(keepends=True)
        lines[-1]=lines[1]
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            convert(parse_csv(raw("".join(lines))), TODAY)

    def test_official_download_exact_url_and_same_bytes(self):
        seen = []
        def fixture(url):
            seen.append(url)
            return raw()
        src = download(fixture)
        self.assertEqual(src["source_sha256"], hashlib.sha256(raw()).hexdigest())
        self.assertEqual(seen, [SOURCE_URL])
        self.assertTrue(safe_url(SOURCE_URL))
        with self.assertRaisesRegex(ValueError, "Unapproved"):
            fetch_csv("https://example.invalid/private.csv")

    def test_replay_produces_exactly_same_market_records(self):
        blob = raw()
        one = convert(parse_csv(blob), TODAY)
        two = convert(parse_csv(blob), TODAY)
        self.assertEqual(one, two)


if __name__ == "__main__":
    unittest.main()
