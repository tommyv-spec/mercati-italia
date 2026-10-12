import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from municipality_reconciliation import (
    reconcile, municipality_proposals, source_city_cross_contamination,
    trusted_municipalities, PROJECTION_WARNING
)
from export_static import normalize

REFERENCE=json.loads((Path(__file__).resolve().parents[1]/
                      "data/istat-comuni-2026.json").read_text(encoding="utf-8"))
OFFICIAL=trusted_municipalities(REFERENCE)
TODAY=date(2026,10,12)


def market(slug,city,province,region,title,day="settimanale - martedì",dates=None):
    return {
        "slug":slug,"citta":city,"provincia":province,"regione":region,
        "nome":title,"ricorrenza_testo":day,
        "date": dates if dates is not None else ["2026-10-13","2026-10-20"],
        "date_quality":"prevista","status":"non_confermato",
        "fonte":"happings.com","url_fonte":"https://www.happings.com/it/mercati-settimanali-a-chieti.html",
        "lat":42.7,"lng":14.2,"verificato_il":"",
        "aggiornato_il":"2026-03-18",
    }


class OfficialMunicipalityTests(unittest.TestCase):
    def test_istat_2026_reference_has_real_municipalities_and_no_fake_city(self):
        self.assertEqual(len(OFFICIAL),20)
        self.assertEqual(sum(map(len,OFFICIAL.values())),7894)
        self.assertEqual(OFFICIAL["Lombardia"]["piazza brembana"][0],"Piazza Brembana")
        self.assertEqual(OFFICIAL["Veneto"]["castegnero nanto"][0],"Castegnero Nanto")
        self.assertEqual(OFFICIAL["Abruzzo"]["castiglione messer marino"][1],"CH")

    def test_real_chieti_merged_scrape_prefers_source_first_municipality_and_quarantines_wrong_tuesday(self):
        row=market("mercato-settimanale-di-castiglione-messer-marino-in-provincia-di-mercato-settima",
            "Castiglione Messer Marino, in provincia di... Mercato settimanale a Celenza Sul Trigno Il mercato settimanale di Celenza",
            "CH","Abruzzo",
            "Mercato settimanale di Castiglione Messer Marino, in provincia di... Mercato settimanale a Celenza Sul Trigno Il mercato settimanale di Celenza Sul Trigno")
        before=copy.deepcopy(row)
        out,report=reconcile([row],REFERENCE,apply=True)
        self.assertEqual(out[0]["citta"],"Castiglione Messer Marino")
        self.assertEqual(out[0]["nome"],"Mercato settimanale di Castiglione Messer Marino")
        self.assertEqual(out[0]["date"],[])
        self.assertEqual(out[0]["date_quality"],"sconosciuta")
        self.assertEqual(out[0]["ricorrenza_testo"],PROJECTION_WARNING)
        self.assertEqual(out[0]["ricorrenza_originale"],before["ricorrenza_testo"])
        self.assertEqual(out[0]["citta_originale"],before["citta"])
        self.assertEqual(out[0]["verificato_il"],"")
        self.assertEqual(out[0]["lat"],before["lat"])
        self.assertEqual(report["counts"]["records_calendar_quarantined"],1)
        self.assertEqual(report["market_confirmations_created"],0)
        self.assertEqual(before,row)

    def test_province_alias_city_like_na_is_not_municipality_but_recoverable(self):
        row=market("mercato-dei-contadini-a-somma-vesuviana-somma-vesuviana",
            "NA","NA","Campania","Mercato Dei Contadini A Somma Vesuviana",
            "",[])
        row["url_fonte"]="https://www.eventiesagre.it/Mercatini_Filiera+Corta/21157853_Mercato+Dei+Contadini+a+Somma+Vesuviana.html"
        out,report=reconcile([row],REFERENCE,apply=True)
        self.assertEqual(out[0]["citta"],"Somma Vesuviana")
        self.assertEqual(out[0]["date"],[])
        self.assertEqual(out[0]["date_quality"],"prevista")
        # Export, not reconciliation, demotes impossible empty-data label.
        fixed,err=normalize(out[0],TODAY)
        self.assertIsNone(err)
        self.assertEqual(fixed["date_quality"],"sconosciuta")
        self.assertEqual(out[0]["url_fonte"],row["url_fonte"])

    def test_longest_complete_municipality_suffix_wins(self):
        row=market("mercato-della-terra-a-piano-di-sorrento-piano-di-sorrento",
            "NA","NA","Campania","Mercato della Terra a Piano Di Sorrento")
        out,_=reconcile([row],REFERENCE,apply=True)
        self.assertEqual(out[0]["citta"],"Piano di Sorrento")

    def test_real_piazza_brembana_and_piazza_al_serchio_remain_unchanged(self):
        cases=[
            market("weekly-piazza-brembana","Piazza Brembana","BG",
                   "Lombardia","Mercato settimanale di Piazza Brembana"),
            market("weekly-piazza-al-serchio","Piazza al Serchio","LU",
                   "Toscana","Mercato settimanale di Piazza al Serchio"),
        ]
        rows,report=reconcile(cases,REFERENCE,apply=True)
        self.assertEqual(cases,rows)
        self.assertEqual(report["counts"].get("city_fixed",0),0)

    def test_mismatched_province_blocks_automatic_rewrite(self):
        original=market("mercato-dei-contadini-a-somma-vesuviana-somma-vesuviana",
            "NA","RM","Campania","Mercato Dei Contadini A Somma Vesuviana")
        rows,report=reconcile([original],REFERENCE,apply=True)
        self.assertEqual(rows[0],original)
        self.assertEqual(report["counts"]["needs_manual_municipality_review"],1)

    def test_ambiguous_prefix_with_different_embedded_market_no_calendar_inference(self):
        original=market("wrong-unknown",
            "Castellammare di Stabia 1, in provincia di... Mercato settimanale a Castello di Cisterna Il mercato settimanale di Caste",
            "NA","Campania",
            "Mercato settimanale di Castellammare di Stabia 1, in provincia di... Mercato settimanale a Castello di Cisterna")
        rows,report=reconcile([original],REFERENCE,apply=True)
        self.assertEqual(rows[0]["citta"],original["citta"])
        self.assertEqual(rows[0]["date"],[])
        self.assertEqual(rows[0]["date_quality"],"sconosciuta")
        self.assertEqual(report["counts"]["needs_manual_municipality_review"],1)

    def test_replay_after_export_is_idempotent_and_never_reprojects_quarantined_dates(self):
        row=market("mercato-settimanale-di-castiglione-messer-marino-in-provincia-di-mercato-settima",
            "Castiglione Messer Marino, in provincia di... Mercato settimanale a Celenza Sul Trigno Il mercato settimanale di Celenza",
            "CH","Abruzzo",
            "Mercato settimanale di Castiglione Messer Marino, in provincia di... Mercato settimanale a Celenza Sul Trigno")
        once,_=reconcile([row],REFERENCE,apply=True)
        normalized,error=normalize(once[0],TODAY)
        self.assertIsNone(error)
        again,stats=reconcile([normalized],REFERENCE,apply=True)
        self.assertEqual(again[0]["date"],[])
        self.assertEqual(again[0]["ricorrenza_testo"],PROJECTION_WARNING)
        self.assertEqual(again[0]["citta_originale"],row["citta"])
        self.assertEqual(again[0]["calendario_sospeso_motivo"],
                         "testo_sorgente_localita_concatenate")
        self.assertEqual(again[0]["ricorrenza_originale"],"settimanale - martedì")
        self.assertEqual(stats["counts"].get("city_fixed",0),0)
        self.assertEqual(once[0]["verificato_il"],"")

    def test_read_only_suggestion_mode_never_changes_original(self):
        row=market("mercato-settimanale-di-castiglione-messer-marino-in-provincia-di-mercato-settima",
            "Castiglione Messer Marino, in provincia di... Mercato settimanale a Celenza Sul Trigno Il mercato settimanale di Celenza",
            "CH","Abruzzo",
            "Mercato settimanale di Castiglione Messer Marino, in provincia di...")
        source=copy.deepcopy(row)
        observed,summary=reconcile([row],REFERENCE,apply=False)
        self.assertEqual(observed,[row])
        self.assertEqual(row,source)
        self.assertTrue(summary["review_only"])
        self.assertEqual(summary["counts"]["city_candidates_istat_province_title"],1)

    def test_preserves_catalog_ids_and_never_invents_event_confirmation(self):
        rows=[
            market("somma-market","NA","NA","Campania","Mercato a Somma Vesuviana"),
            market("cernobbio-market",'"Mercatino delle Curiosità"',"",
                   "Lombardia","Cernobbio, Mercatino delle Curiosità"),
        ]
        changed,report=reconcile(rows,REFERENCE,apply=True)
        self.assertEqual([r["slug"] for r in rows],[r["slug"] for r in changed])
        self.assertEqual(rows[0]["url_fonte"],changed[0]["url_fonte"])
        self.assertEqual(report["verified_dates_created"],0)
        self.assertEqual(report["market_confirmations_created"],0)
        self.assertEqual(report["publisher_sources_replaced"],0)

    def test_wrong_istat_metadata_blocks_wholesale_corrections(self):
        other={**REFERENCE,"source_file_sha256":"0"*64}
        with self.assertRaisesRegex(ValueError,"Unrecognized official ISTAT"):
            reconcile([market("one","NA","NA","Campania","Mercato a Somma Vesuviana")],other)
        with self.assertRaisesRegex(ValueError,"Repeated or missing"):
            r=market("duplicate","NA","NA","Campania","Mercato a Somma Vesuviana")
            reconcile([r,r],REFERENCE)


if __name__=="__main__":
    unittest.main()
