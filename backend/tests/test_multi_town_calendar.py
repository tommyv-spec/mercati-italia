"""Multi-town official calendars: PDF tables, yearly discovery, town/day fills."""
import copy
import importlib.util
import json
import sys
import unittest
import unittest.mock
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from publisher_snapshot_date import (discover_document, make_landing_page_proof,
                                     resolve_source_date)
from source_contract_activation import activate, validate_release
from source_contract_ingest import apply_fill, stage, town_day_fills, verify_fill
from source_lifecycle import (candidate_record, clock_range, digest, parse_rows,
                              validate_contracts, weekdays)

CONTRACTS = json.loads((Path(__file__).resolve().parents[1] /
                        "data/market-source-contracts.json").read_text("utf-8"))
VENETO = next(p for p in CONTRACTS["raw_profiles"] if p["id"] == "veneto-calendario-mercati")
TODAY = date(2026, 10, 25)
COLUMNS = ["provincia", "comune", "luogo", "denominazione", "periodicita", "dal_al",
           "cadenza", "giorni", "orario"]
HEADER = ["Provincia", "Comune", "Luogo", "Mercato", "Periodicita", "Dal Al",
          "Cadenza", "Giorni", "Orario"]
DOC = ("https://www.regione.veneto.it/documents/10713/12114597/"
       "Calendario+regionale+mercati+2026.pdf/be79e5c1-ceae-4e76-8207-3b49630ae080")
HAS_PDF = importlib.util.find_spec("pdfplumber") is not None


def profile(**changes):
    """The reviewed Veneto contract on a small nine-column table."""
    p = copy.deepcopy(VENETO)
    p.update({"schema_columns": COLUMNS, "pdf_header": HEADER, "min_rows": 1, "max_rows": 50})
    p.update(changes)
    return p


def row(comune, luogo, giorni, orario="dalle ore 7,30 alle ore 13,30", nome="Mercato settimanale",
        periodicita="annuale", cadenza="settimanale", provincia="Belluno"):
    return dict(zip(COLUMNS, [provincia, comune, luogo, nome, periodicita, "", cadenza,
                              giorni, orario]))


def table_pdf(pages):
    """A minimal ruled-table PDF (Helvetica, WinAnsi) with one table per page."""
    widths, height = [70, 90, 150, 120, 70, 50, 70, 110, 190], 16
    objects, kids = [], []

    def add(body):
        objects.append(body)
        return len(objects)

    font = add(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica /Encoding /WinAnsiEncoding >>")
    pages_id = len(objects) + 2 * len(pages) + 1
    for rows in pages:
        ops, top = [], 760
        for r, cells in enumerate(rows):
            x = 20
            for w, text in zip(widths, cells):
                safe = text.encode("cp1252").replace(b"\\", b"\\\\").replace(b"(", b"\\(").replace(b")", b"\\)")
                ops.append(b"BT /F1 6 Tf %d %d Td (" % (x + 2, top - (r + 1) * height + 5) + safe + b") Tj ET")
                x += w
        bottom, right = top - len(rows) * height, 20 + sum(widths)
        for r in range(len(rows) + 1):
            ops.append(b"20 %d m %d %d l S" % (top - r * height, right, top - r * height))
        x = 20
        for w in [0, *widths]:
            x += w
            ops.append(b"%d %d m %d %d l S" % (x, top, x, bottom))
        stream = b"\n".join(ops)
        content = add(b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream")
        kids.append(add(b"<< /Type /Page /Parent %d 0 R /MediaBox [0 0 1000 800] /Contents %d 0 R "
                        b"/Resources << /Font << /F1 %d 0 R >> >> >>" % (pages_id, content, font)))
    add(b"<< /Type /Pages /Kids [" + b" ".join(b"%d 0 R" % k for k in kids)
        + b"] /Count %d >>" % len(kids))
    catalog = add(b"<< /Type /Catalog /Pages %d 0 R >>" % pages_id)
    out, offsets = bytearray(b"%PDF-1.4\n"), []
    for number, body in enumerate(objects, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objects) + 1)
    out += b"".join(b"%010d 00000 n \n" % offset for offset in offsets)
    out += b"trailer\n<< /Size %d /Root %d 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
        len(objects) + 1, catalog, xref)
    return bytes(out)


def landing(year=2026, text="Calendario regionale dei mercati"):
    return (f'<p>Elenco {year}: <a href="/documents/10713/12114597/Calendario+regionale+'
            f'mercati+{year}.pdf/be79e5c1-ceae-4e76-8207-3b49630ae080">{text} </a>'
            f'<a href="/documents/10713/0/Antiquariato+{year}.pdf/536c8c2e-cbd0-4e29-a644-'
            f'd1d00eff35d7">mercatini</a></p>').encode("utf-8")


def market(slug, citta, ricorrenza, **fields):
    base = {"slug": slug, "nome": "Mercato settimanale di " + citta, "citta": citta,
            "provincia": "BL", "regione": "Veneto", "indirizzo": "", "orario_testo": "La mattina",
            "ricorrenza_testo": ricorrenza, "categoria": "misto", "fonte": "happings.com",
            "url_fonte": "https://www.happings.com/it/" + slug + ".html", "status": "non_confermato",
            "lat": 46.2, "lng": 12.0, "position_quality": "non_verificata", "verificato_il": ""}
    base.update(fields)
    return base


class ParserTests(unittest.TestCase):
    def test_italian_clock_ranges_and_weekday_lists(self):
        for text in ("dalle ore 7,30 alle ore 13,30", "7.30-13.30", "dalle 7,30 alle ore13,30",
                     "dalle ore 7,30 ale ore 13;30"):
            self.assertIn(clock_range(text), ("07:30–13:30",))
        self.assertEqual(clock_range("dalle ore 8 alle ore 13"), "08:00–13:00")
        for text in ("invernale: dalle ore 7,30 alle ore 13,00; estivo dalle ore 7,30 alle ore 13,30",
                     "ddaallllee oorree 88,,0000 aallllee oorree 1133,,0000",
                     "dalle ore 13,00 alle ore 8,00", "dalle ore 16,00 alle ore 2,00 del giorno successivo"):
            self.assertIsNone(clock_range(text))
        self.assertEqual(weekdays("martedì, venerdì"), (1, 4))
        self.assertEqual(weekdays("lunedì e giovedì"), (0, 3))
        self.assertIsNone(weekdays("o giovedì o venerdì o sabato"))
        self.assertIsNone(weekdays("ogni terzo lunedì del mese"))

    def test_row_municipality_province_lists_hours_and_exclusions(self):
        p = profile()
        record, issue, _ = candidate_record(p, row("ARSIE'", "Piazza Marconi", "martedì, venerdì"),
                                            today=TODAY, source_date="2026-01-01")
        self.assertIsNone(issue)
        self.assertEqual((record["citta"], record["provincia"]), ("Arsiè", "BL"))
        self.assertEqual(record["ricorrenza_testo"], "settimanale - martedi, venerdi")
        self.assertEqual(record["orario_testo"], "07:30–13:30 (da verificare con il Comune)")
        # A province column error never overrides ISTAT (Cinto Caomaggiore is VE).
        record, _, _ = candidate_record(p, row("CINTO CAOMAGGIORE", "Via Roma", "lunedì",
                                               provincia="Vicenza"), today=TODAY, source_date="2026-01-01")
        self.assertEqual(record["provincia"], "VE")
        seasonal = row("ALLEGHE", "Via Lungolago", "martedì", periodicita="stagionale")
        stall = row("BELLUNO", "Via Duomo", "sabato", nome='Posteggi isolati "Auditorium"')
        typo = row("VILLANOVA DI CAMPOSAMPERO", "Via X", "giovedì", provincia="Padova")
        self.assertEqual(candidate_record(p, seasonal, today=TODAY)[1], "not_a_market_venue")
        self.assertEqual(candidate_record(p, stall, today=TODAY)[1], "not_a_market_venue")
        self.assertEqual(candidate_record(p, typo, today=TODAY)[1], "municipality_not_in_istat")
        garbled, _, _ = candidate_record(p, row("AGORDO", "Piazza", "mercoledì", orario="ddaallllee"),
                                         today=TODAY, source_date="2026-01-01")
        self.assertEqual(garbled["orario_testo"], "")
        named, _, _ = candidate_record(p, row("AGORDO", "Piazza Libertà", "mercoledì", nome="Capoluogo"),
                                       today=TODAY, source_date="2026-01-01")
        empty, _, _ = candidate_record(p, row("AGORDO", "Piazza Libertà", "giovedì", nome=""),
                                       today=TODAY, source_date="2026-01-01")
        self.assertEqual(named["nome"], "Mercato di Agordo – Capoluogo")
        self.assertEqual(empty["nome"], "Mercato settimanale di Agordo")

    def test_contract_options_are_validated(self):
        for change in ({"municipality": "Agordo"}, {"pdf_header": HEADER[:3]},
                       {"hours_text_format": "free_text"}, {"weekday_lists": "yes"},
                       {"exclude_rows_containing": {"unknown": ["isolat"]}},
                       {"resource_discovery": {"link_text": "x", "href_pattern": "/a"}},
                       {"existing_market_fill": {"max_records_per_run": 5000}},
                       {"place_name_template": "Mercato di {citta}"}):
            with self.subTest(change=change):
                bad = copy.deepcopy(CONTRACTS)
                bad["raw_profiles"][-1] = profile(**change)
                with self.assertRaises(ValueError):
                    validate_contracts(bad)


class DiscoveryTests(unittest.TestCase):
    def test_finds_this_year_then_last_year_and_rejects_ambiguity(self):
        url, year = discover_document(VENETO, landing(), read_on="2026-10-25")
        self.assertEqual((url, year), (DOC, 2026))
        self.assertEqual(discover_document(VENETO, landing(2026), read_on="2027-01-05")[1], 2026)
        with self.assertRaisesRegex(ValueError, "No current yearly document"):
            discover_document(VENETO, landing(2024), read_on="2026-10-25")
        with self.assertRaisesRegex(ValueError, "No current yearly document"):
            discover_document(VENETO, landing(text="Altro documento"), read_on="2026-10-25")
        twice = landing() + landing().replace(b"be79e5c1", b"aa79e5c1")
        with self.assertRaisesRegex(ValueError, "Several yearly documents"):
            discover_document(VENETO, twice, read_on="2026-10-25")

    def test_year_is_the_content_date_and_proof_is_bound(self):
        proof = make_landing_page_proof(VENETO, landing(), DOC, 2026, b"%PDF", read_on="2026-10-25",
                                        today=TODAY)
        self.assertEqual(resolve_source_date(VENETO, proof=proof, blob=b"%PDF", today=TODAY),
                         "2026-01-01")
        for key, value in (("document_year", 2025), ("source_date", "2026-10-25"),
                           ("document_url", DOC.replace("2026", "2027"))):
            forged = dict(proof, **{key: value})
            with self.subTest(key=key), self.assertRaises(ValueError):
                resolve_source_date(VENETO, proof=forged, blob=b"%PDF", today=TODAY)
        with self.assertRaises(ValueError):
            resolve_source_date(VENETO, proof=proof, blob=b"%PDF-other", today=TODAY)


@unittest.skipUnless(HAS_PDF, "pdfplumber not installed")
class PdfTableTests(unittest.TestCase):
    def test_every_page_needs_the_reviewed_header(self):
        first = [["CALENDARIO 2026"] + [""] * 8, HEADER,
                 list(row("AGORDO", "Piazza Libertà", "mercoledì").values())]
        second = [HEADER, list(row("ALLEGHE", "Via Lungolago", "martedì e venerdì").values())]
        rows = parse_rows(profile(), table_pdf([first, second]))
        self.assertEqual([r["comune"] for r in rows], ["AGORDO", "ALLEGHE"])
        self.assertEqual(rows[1]["giorni"], "martedì e venerdì")
        changed = [["Provincia", "Comune", "Via"] + HEADER[3:]] + first[2:]
        for pages in ([first, second[1:]], [changed]):
            with self.subTest(pages=len(pages)), self.assertRaises(ValueError):
                parse_rows(profile(), table_pdf(pages))
        with self.assertRaisesRegex(ValueError, "Unreadable publisher PDF"):
            parse_rows(profile(), b"%PDF-1.4 broken")


class TownDayFillTests(unittest.TestCase):
    def run_fill(self, base, source):
        return town_day_fills(profile(), source, base, today=TODAY, read_on="2026-10-25",
                              source_date="2026-01-01", parsed_sha256="b" * 64)

    def test_unique_town_day_fills_vague_values_with_bound_receipts(self):
        target = market("mercato-settimanale-di-agordo-agordo-mercoledi", "Agordo",
                        "settimanale - mercoledì", indirizzo="Pia")
        other_day = market("mercato-settimanale-di-alleghe-alleghe-martedi", "Alleghe",
                           "settimanale - martedì", orario_testo="08:00–12:00")
        source = [row("AGORDO", "Piazza della Libertà", "mercoledì"),
                  row("AGORDO", "Via Duomo", "sabato", nome="Posteggi isolati"),
                  row("ALLEGHE", "Via Lungolago", "martedì", orario="dalle ore 8,00 alle ore 13,00")]
        proofs, counts = self.run_fill([target, other_day], source)
        by_slug = {proof["slug"]: proof for proof in proofs}
        fill = by_slug[target["slug"]]
        self.assertEqual(fill["changed_fields"], {
            "indirizzo": {"before": "Pia", "after": "Piazza della Libertà"},
            "orario_testo": {"before": "La mattina",
                             "after": "07:30–13:30 (da verificare con il Comune)"}})
        # Better (exact) hours are kept; the matching street is only observed.
        self.assertEqual(by_slug[other_day["slug"]]["changed_fields"],
                         {"indirizzo": {"before": "", "after": "Via Lungolago"}})
        self.assertEqual(counts["kept_existing_orario_testo"], 1)
        after = apply_fill(target, fill, profile(), today=TODAY)
        observations = {"source_parsed_sha256": "b" * 64, "source_read_on": "2026-10-25"}
        with unittest.mock.patch("source_contract_ingest.observed_source_date",
                                 return_value="2026-01-01"):
            self.assertEqual(verify_fill(profile(), target, after, fill, today=TODAY,
                                         source_observations=observations), 2)
            self.assertIn({"nome": VENETO["publisher"], "url": VENETO["attribution_url"]}, after["fonti"])
            self.assertEqual(after["riscontri_campi"][0]["metodo"], "comune_provincia_giorno_univoco")
            for field, value in (("nome", "Altro"), ("orario_testo", "09:00–12:00")):
                tampered = dict(after, **{field: value})
                with self.subTest(field=field), self.assertRaises(ValueError):
                    verify_fill(profile(), target, tampered, fill, today=TODAY,
                                source_observations=observations)

    def test_ambiguous_or_conflicting_matches_are_held(self):
        one = market("mercato-settimanale-di-agordo-agordo-mercoledi", "Agordo", "settimanale - mercoledì")
        two = market("mercato-settimanale-a-agordo-agordo-mercoledi", "Agordo", "settimanale - mercoledì",
                     fonte="eventiesagre.it")
        source = [row("AGORDO", "Piazza della Libertà", "mercoledì")]
        self.assertEqual(self.run_fill([one, two], source)[1]["held_several_catalog_markets_same_town_day"], 2)
        seasonal = row("AGORDO", "Via Lago", "mercoledì", periodicita="stagionale")
        self.assertEqual(self.run_fill([one], source + [seasonal])[1]
                         ["held_several_official_markets_same_town_day"], 1)
        street = dict(one, indirizzo="Via Garibaldi")
        self.assertEqual(self.run_fill([street], source)[1]["held_different_street"], 1)
        farmers = dict(one, nome="Mercato Campagna Amica di Agordo")
        self.assertEqual(self.run_fill([farmers], source)[1]["held_market_type_not_ordinary"], 1)
        verified = dict(one, verificato_il="2026-10-01")
        self.assertEqual(self.run_fill([verified], source)[1]["held_human_verified_market"], 1)
        afternoon = row("AGORDO", "Piazza della Libertà", "mercoledì", orario="dalle ore 15,00 alle ore 19,00")
        proofs, counts = self.run_fill([one], [afternoon])
        self.assertEqual(counts["kept_existing_orario_testo"], 1)
        self.assertNotIn("orario_testo", proofs[0]["changed_fields"])


class NewMarketTests(unittest.TestCase):
    def test_new_venue_needs_a_free_town_day_and_locality(self):
        p = profile()
        source = [row("AGORDO", "Piazza della Libertà", "mercoledì"),
                  row("AGORDO", "Via Roma", "sabato"),
                  row("ALPAGO", "Piazzetta Santa Maria - Pieve d'Alpago", "giovedì")]
        base = [market("mercato-settimanale-di-agordo-agordo-mercoledi", "Agordo", "settimanale - mercoledì"),
                market("mercato-settimanale-di-pieve-d-alpago", "Pieve d'Alpago", "settimanale - giovedì")]
        proof = make_landing_page_proof(p, landing(), DOC, 2026, b"%PDF", read_on="2026-10-25",
                                        today=TODAY)
        with unittest.mock.patch("source_contract_ingest.parse_rows", return_value=source):
            candidates, report = stage(p, b"%PDF", base, today=TODAY, read_on="2026-10-25",
                                       source_date_proof=proof)
        self.assertEqual([(c["citta"], c["ricorrenza_testo"]) for c in candidates],
                         [("Agordo", "settimanale - sabato")])
        # The generic-name rule already holds Agordo; the merged-town rule holds
        # Alpago, whose catalog market is filed under its old name Pieve d'Alpago.
        self.assertEqual(report["review_reason_counts"], {
            "existing_market_same_locality_day": 1, "generic_city_market_day": 1})
        named = copy.deepcopy(base)
        named[0]["nome"] = "Mercato del mercoledì"
        with unittest.mock.patch("source_contract_ingest.parse_rows", return_value=source):
            _, report = stage(p, b"%PDF", named, today=TODAY, read_on="2026-10-25",
                              source_date_proof=proof)
        self.assertEqual(report["review_reason_counts"]["existing_market_same_town_day"], 1)


@unittest.skipUnless(HAS_PDF, "pdfplumber not installed")
class ActivationTests(unittest.TestCase):
    def test_daily_activation_discovers_reads_fills_admits_and_is_independently_checked(self):
        p = profile(min_rows=2)
        cfg = copy.deepcopy(CONTRACTS)
        cfg["raw_profiles"] = [p]
        reg = {"schema": 1, "publication_channel": "dev-only", "description": "test",
               "user_event_confirmations_allowed": False, "approvals": [{
                   "schema": 1, "mode": "approved_dev_only", "source_id": p["id"],
                   "reviewed_profile_sha256": digest(p),
                   "publisher_license_evidence_url": p["attribution_url"],
                   "identity_granularity": p["row_kind"], "reviewed_on": "2026-10-25",
                   "max_new_ids": 5, "source_record_kind": p["row_kind"],
                   "source_specific_geo_approval": False}]}
        pdf = table_pdf([[HEADER, list(row("AGORDO", "Piazza della Libertà", "mercoledì").values()),
                          list(row("ALLEGHE", "Via Lungolago", "martedì").values())]])
        calls = []

        def fetch(url, max_bytes=65536):
            calls.append(url)
            body = landing() if url == p["resource_url"] else pdf
            return body, len(body) > max_bytes

        base = [market("mercato-settimanale-di-agordo-agordo-mercoledi", "Agordo", "settimanale - mercoledì"),
                {"slug": "unrelated", "nome": "Mercato", "citta": "Firenze", "regione": "Toscana",
                 "provincia": "FI", "indirizzo": "Piazza", "status": "non_confermato"}]
        after, report = activate(cfg, reg, base, today=TODAY, fetch=fetch, read_on="2026-10-25")
        self.assertEqual(len(calls), 2)
        self.assertEqual(report["filled_market_ids"], [base[0]["slug"]])
        self.assertEqual(len(report["new_market_ids"]), 1)
        new = after[-1]
        self.assertEqual((new["citta"], new["status"], new["lat"]), ("Alleghe", "non_confermato", None))
        self.assertEqual(after[0]["orario_testo"], "07:30–13:30 (da verificare con il Comune)")
        self.assertTrue(validate_release(base, after, report, cfg, reg)["release_safe"])
        tampered = copy.deepcopy(after)
        tampered[0]["indirizzo"] = "Via Inventata"
        with self.assertRaises(ValueError):
            validate_release(base, tampered, report, cfg, reg)
        hidden = copy.deepcopy(report)
        hidden["filled_market_ids"] = []
        with self.assertRaises(ValueError):
            validate_release(base, after, hidden, cfg, reg)
        # Next day: same file, no drift, no duplicate admission; the fill is
        # re-proved (new read date) and keeps this engine's field ownership.
        later = date(2026, 10, 26)
        again, second = activate(cfg, reg, after, today=later, fetch=fetch, read_on=later.isoformat())
        self.assertEqual(second["new_market_ids"], [])
        fill = second["per_source"][p["id"]]["fills"][0]
        self.assertEqual((fill["slug"], fill["changed_fields"]), (base[0]["slug"], {}))
        receipt = again[0]["riscontri_campi"][0]
        self.assertEqual((receipt["letto_il"], receipt["gestore_campi"]),
                         ("2026-10-26", "source_contract_town_day"))
        self.assertTrue(validate_release(after, again, second, cfg, reg)["release_safe"])


if __name__ == "__main__":
    unittest.main()
