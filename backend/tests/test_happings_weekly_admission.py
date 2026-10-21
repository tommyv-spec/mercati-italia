"""Source-bound market admission never invents hours, dates or duplicate IDs."""
from __future__ import annotations
import copy
import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import happings_weekly_admission as weekly
from export_static import normalize
ROOT="https://www.happings.com"
INDEX=ROOT+"/it/mercati-settimanali-a-gorizia-e-provincia/"
SPAIN=ROOT+"/it/mercati-settimanali-a-barcelona-e-provincia/"
DAY=date(2026,10,21)
HTML=b"""<!doctype html><html lang="it"><body>
<h1>Mercati settimanali a Gorizia</h1><div class="happings-seo-content">
<h3>Mercati del mercoled&#236; nei comuni di Gorizia</h3><ul>
<li>a Gorizia, in Piazza Vittoria (la mattina)</li></ul>
<p>Elenco provinciale dei mercati settimanali di Gorizia, con indicazioni dei luoghi per i visitatori e la consultazione.</p>
</div></body></html>"""


def pages(raw=HTML, url=INDEX):
    return [{"requested_url":url,"final_url":url,"html":raw}]


def legacy():
    return {"slug":"legacy","nome":"Mercato settimanale di Gorizia",
            "citta":"Gorizia","regione":"Friuli-Venezia Giulia","provincia":"GO",
            "indirizzo":"Piazza Vittoria","ricorrenza_testo":"settimanale - mercoledì",
            "status":"non_confermato","fonte":"happings.com",
            "url_fonte":ROOT+"/it/mercato-settimanale-a-gorizia.html",
            "date":[],"date_quality":"sconosciuta"}


class WeeklyAdmissionTests(unittest.TestCase):
    def test_missing_market_is_created_only_from_unique_source_evidence(self):
        old=[{"slug":"other","citta":"Pisa","regione":"Toscana","provincia":"PI",
              "nome":"Altra scheda","ricorrenza_testo":"settimanale - sabato"}]
        after,report=weekly.preview(old,pages(),today=DAY,apply=True)
        self.assertEqual(len(after),2)
        row=after[-1]
        self.assertEqual(row["citta"],"Gorizia")
        self.assertEqual(row["indirizzo"],"Piazza Vittoria")
        self.assertEqual(row["url_fonte"],INDEX)
        self.assertEqual(row["date"],[])
        self.assertEqual(row["orario_testo"],"")
        self.assertEqual(row["verificato_il"],"")
        self.assertEqual(row["status"],"non_confermato")
        self.assertEqual(row["ricorrenza_testo"],"settimanale - mercoledi")
        self.assertEqual(len(row["riscontri_campi"]),1)
        self.assertEqual(report["added_ids"],[row["slug"]])
        self.assertTrue(weekly.verify_changes(old,after,report,today=DAY,pages=pages()))
        exported,error=normalize(row,DAY)
        self.assertIsNone(error)
        self.assertEqual(exported["slug"],row["slug"])
    def test_existing_market_blocks_any_duplicate(self):
        original=[legacy()]
        after,report=weekly.preview(original,pages(),today=DAY,apply=True)
        self.assertEqual(after,original)
        self.assertEqual(report["added_ids"],[])
        self.assertGreater(report["counts"]["existing_catalog_identity_or_collision"],0)
    def test_replay_reproduces_stable_id(self):
        a,_=weekly.preview([],pages(),today=DAY,apply=True)
        b,_=weekly.preview([],pages(),today=DAY,apply=True)
        self.assertEqual(a,b)
        self.assertEqual(len(a),1)
    def test_tampered_receipt_or_fake_opening_is_rejected(self):
        before=[]
        after,report=weekly.preview(before,pages(),today=DAY,apply=True)
        for change in ("date","orario_testo","indirizzo","verificato_il"):
            tampered=copy.deepcopy(after)
            tampered[0][change]=["2026-10-28"] if change=="date" else "invented"
            with self.subTest(change=change):
                with self.assertRaisesRegex(ValueError,"not reproduced"):
                    weekly.verify_changes(before,tampered,report,today=DAY,pages=pages())
    def test_foreign_province_rejected(self):
        with self.assertRaises(ValueError):
            weekly.preview([],pages(url=SPAIN),today=DAY,apply=True)
    def test_multiple_rows_for_same_city_weekday_are_held(self):
        raw=HTML.replace(b"</ul>",b"<li>a Gorizia, in Piazza Grande (la mattina)</li></ul>")
        after,report=weekly.preview([],pages(raw),today=DAY,apply=True)
        self.assertEqual(after,[])
        self.assertGreater(report["counts"]["multiple_source_venues_same_city_day"],0)


if __name__=="__main__":
    unittest.main()
