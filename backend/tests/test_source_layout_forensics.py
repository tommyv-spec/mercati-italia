"""Offline publisher HTML schema facts: never mistake present fields for absent ones."""
from __future__ import annotations
import copy
import json
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_layout_forensics import inspect,validate,SOURCE_TYPES,MAX_HTML_BYTES

HAPPINGS="https://www.happings.com/it/mercati-settimanali-a-venezia.html"
COSE="https://www.cosedicasa.com/mercatini/venezia-campo-san-maurizio"
EVENTI="https://www.eventiesagre.it/Mercatini_Filiera+Corta/21185843_Mercato+Settimanale+Di+Alba+Adriatica.html"

def market(source,city="Spinea",day="mercoledì"):
    return {
        "slug":"market-original-retained","url_fonte":source,"citta":city,
        "ricorrenza_testo":"settimanale - "+day,
        "indirizzo":"","orario_testo":"","date":[],"descrizione":"",
    }


class SourceFieldForensicsTests(unittest.TestCase):
    def test_happings_weekday_table_contains_address_but_not_clock_hours(self):
        html=b"""
        <html><body><div class="happings-seo-content">
          <h3>Mercati del mercoled&#236; nei comuni di Venezia</h3>
          <ul><li>a Spinea, in Villaggio dei Fiori (la mattina)</li>
              <li>a Dolo, in Piazza San Valentino (la mattina)</li></ul>
          <h3>Mercati del sabato nei comuni di Venezia</h3>
          <ul><li>a Spinea, in Piazza Fermi (la mattina)</li></ul>
        </div></body></html>"""
        src=market(HAPPINGS)
        frozen=copy.deepcopy(src)
        d=inspect(html,source_type="happings_weekly_index",url=HAPPINGS,market=src)
        self.assertTrue(validate(d))
        self.assertEqual(d["source_rows_detected"],3)
        self.assertEqual(d["individual_venue_matches"],1)
        self.assertEqual(d["source_row_match"],"same_city_single_day_source_row")
        self.assertTrue(d["source_field_presence"]["indirizzo"])
        self.assertTrue(d["source_field_presence"]["fascia_giornaliera"])
        self.assertFalse(d["source_field_presence"]["orario_preciso"])
        self.assertIn("indirizzo",d["source_present_catalog_missing"])
        self.assertNotIn("orario_preciso",d["source_present_catalog_missing"])
        self.assertNotIn("Villaggio dei Fiori",json.dumps(d))
        self.assertEqual(src,frozen)
        self.assertEqual(d["catalog_records_changed"],0)

    def test_happings_same_city_weekday_multiple_venues_cannot_join(self):
        html=b"""
        <div class="happings-seo-content">
        <h3>Mercati del mercoled&#236; nei comuni di Venezia</h3>
        <ul><li>a Spinea, in Piazza A (la mattina)</li>
            <li>a Spinea, in Piazza B (la mattina)</li></ul>
        </div>"""
        d=inspect(html,source_type="happings_weekly_index",url=HAPPINGS,market=market(HAPPINGS))
        self.assertEqual(d["individual_venue_matches"],2)
        self.assertEqual(d["source_row_match"],"ambiguous_source_venues_same_city_day")
        self.assertEqual(d["source_present_catalog_missing"],[])

    def test_cose_has_structured_fields_and_clock_hours_not_in_our_saved_record(self):
        html=b"""
        <html><head><meta property="article:modified_time"
            content="2026-05-06T09:46:45+00:00"></head>
        <body><article><h1>Mercatino antiquariato e usato di Venezia</h1>
        <div class="mercatini-mostre-row mercatini-mostre-date-big">
          <time datetime="2026-10-16">16 ottobre 2026</time>
          <time datetime="2026-10-18">18 ottobre 2026</time>
        </div>
        <p>Le manifestazioni si svolgono sempre dalle ore 9 alle 19.</p>
        <div class="mercatini-mostre-row mercatini-mostre-address">
          <strong>Luogo:</strong> Il Mercatino di Campo San Maurizio, campo San Maurizio
        </div>
        <div class="mercatini-mostre-row mercatini-mostre-suspension">
          <strong>Sospensioni:</strong> Da gennaio a maggio
        </div>
        <div class="mercatini-mostre-row mercatini-mostre-contacts">
          <strong>Contatti:</strong> original@example.com
        </div>
        <div class="mercatini-mostre-row mercatini-mostre-phone">
          <strong>Telefono:</strong> 347/1234567
        </div>
        <div class="mercatini-mostre-row mercatini-mostre-website">
          <strong>Sito web:</strong> example.org
        </div>
        <div class="mercatini-mostre-row mercatini-mostre-performer">
          <strong>Organizzatore:</strong> organizzatore protetto
        </div></article></body></html>"""
        d=inspect(html,source_type="cosedicasa_edition",url=COSE,market=market(COSE))
        self.assertTrue(validate(d))
        self.assertEqual(d["source_date_elements"],2)
        self.assertTrue(d["source_field_presence"]["orario_preciso"])
        self.assertTrue(d["source_field_presence"]["aggiornamento_publisher"])
        for field in ("indirizzo","sospensioni","organizzatore","telefono","contatti",
                      "sito_organizzatore","date_esplicite"):
            self.assertTrue(d["source_field_presence"][field],field)
        self.assertEqual(d["source_present_catalog_missing"][:], sorted(
            ["indirizzo","orario_preciso","date_esplicite",
             "sospensioni","organizzatore","aggiornamento_publisher"]))
        source_blob=json.dumps(d)
        for forbidden in ("original@example.com","347/1234567","organizzatore protetto","Campo San Maurizio"):
            self.assertNotIn(forbidden,source_blob)

    def test_eventiesagre_old_date_is_not_new_verified_opening(self):
        html=b"""
        <html><body>
        <span class="recapito grassetto">Dal: 02/01/2023</span>
        <span class="recapito grassetto">Al: 02/01/2023</span>
        <b>Evento Passato!</b>
        <article>
          <h1>Mercato Settimanale di Alba Adriatica</h1>
          <p>Quando si svolge: Luned&#236; tutto l'anno</p>
          <p>Dove fanno il mercato settimanale: Piazza del Popolo</p>
          <p>Orari del Mercato: Dalle 08:00 alle 13:00</p>
        </article>
        <div>Data ultimo aggiornamento pagina 2021-08-02</div>
        </body></html>"""
        r=market(EVENTI,"Alba Adriatica","lunedì")
        r["date"]=["2026-10-19"]
        d=inspect(html,source_type="eventiesagre_edition",url=EVENTI,market=r)
        self.assertTrue(d["source_field_presence"]["edizione_archiviata"])
        self.assertTrue(d["source_field_presence"]["orario_preciso"])
        self.assertTrue(d["source_field_presence"]["aggiornamento_publisher"])
        self.assertTrue(d["archived_source_has_future_predictions"])
        self.assertEqual(d["catalog_records_changed"],0)
        self.assertFalse(d["market_openings_verified"])
        self.assertNotIn("Piazza del Popolo",json.dumps(d))

    def test_invalid_publisher_url_and_unbounded_input_fail_closed(self):
        with self.assertRaises(ValueError):
            inspect(b"<html>x</html>"*30,source_type="happings_weekly_index",
                    url="https://www.evil.com/",market=market(HAPPINGS))
        with self.assertRaises(ValueError):
            inspect(b"<html>x</html>"*30,source_type="unknown",url=HAPPINGS)
        with self.assertRaises(ValueError):
            inspect(b"a"*(MAX_HTML_BYTES+1),
                    source_type="cosedicasa_edition",url=COSE)
        with self.assertRaises(ValueError):
            inspect(b"<div>hello</div>"*30,
                    source_type="cosedicasa_edition",url=COSE,
                    market=market("https://attacker.test/"))
        d=inspect(b"<div>hello</div>"*30,
                  source_type="cosedicasa_edition",url=COSE)
        d["source_automation_granted_by_audit"]=True
        with self.assertRaises(ValueError):
            validate(d)

if __name__=="__main__":
    unittest.main()
