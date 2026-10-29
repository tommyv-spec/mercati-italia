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
from field_evidence import PUBLISHED_TOWN_FIXES, clean_receipts, identity, make_receipt, published_town
from municipality_reconciliation import CITY_FIX_BUDGET
from municipality_release_guard import check
from stored_market_sibling_proposals import same_generic_venue
from happings_weekly_admission import _possible_existing

REFERENCE=json.loads((Path(__file__).resolve().parents[1]/
                      "data/istat-comuni-2026.json").read_text(encoding="utf-8"))
OFFICIAL=trusted_municipalities(REFERENCE)
TODAY=date(2026,10,12)
TODAY_RECEIPT=date(2026,10,29)


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

    def test_no_automatic_changes_to_human_verified_market_claims(self):
        row=market("verified-text-city",
                   "Castiglione Messer Marino, in provincia di... Mercato settimanale a Celenza",
                   "CH","Abruzzo",
                   "Mercato settimanale di Castiglione Messer Marino, in provincia di...")
        row["verificato_il"]="2026-10-11"
        row["date_quality"]="confermata"
        original=copy.deepcopy(row)
        rows,report=reconcile([row],REFERENCE,apply=True)
        self.assertEqual(rows[0],original)
        self.assertEqual(report["counts"]["protected_verified_calendars"],1)
        self.assertEqual(report["market_confirmations_created"],0)

    def test_wrong_istat_metadata_blocks_wholesale_corrections(self):
        other={**REFERENCE,"source_file_sha256":"0"*64}
        with self.assertRaisesRegex(ValueError,"Unrecognized official ISTAT"):
            reconcile([market("one","NA","NA","Campania","Mercato a Somma Vesuviana")],other)
        with self.assertRaisesRegex(ValueError,"Repeated or missing"):
            r=market("duplicate","NA","NA","Campania","Mercato a Somma Vesuviana")
            reconcile([r,r],REFERENCE)


def happings(city, province, region, title=None, slug=None, **extra):
    row = market(slug or "card-" + city.lower().replace(" ", "-"), city, province, region,
                 title or "Mercato settimanale di " + city)
    return {**row, "indirizzo": "Piazza Roma", **extra}


class PublishedTownTests(unittest.TestCase):
    """S31: a source town that is not a comune shows the official one, as published elsewhere."""

    def fixed(self, row):
        out, report = reconcile([row], REFERENCE, apply=True)
        return out[0], report

    def test_each_rule_on_real_source_names(self):
        cases = [
            (happings("Atelena", "AQ", "Abruzzo"), "Ateleta", "spelling"),
            (happings("Nibbiano", "PC", "Emilia-Romagna"), "Alta Val Tidone", "former"),
            (happings("Ortonovo", "SP", "Liguria"), "Luni", "former"),  # renamed 2017
            (happings("Sestri Ponente", "GE", "Liguria"), "Genova", "former"),
            (happings("Africo Nuovo", "RC", "Calabria"), "Africo", "hamlet"),
            (happings("Celle", "SV", "Liguria"), "Celle Ligure", "hamlet"),
            # Capitals on a Rome card: Roma Capitale's market, not the town of Gerano.
            (happings("GRANO", "RM", "Lazio"), "Roma", "rome"),
            (happings("Limbade", "VV", "Calabria"), "Limbadi", "spelling"),
        ]
        for row, city, rule in cases:
            with self.subTest(row["citta"]):
                out, report = self.fixed(row)
                self.assertEqual(out["citta"], city)
                self.assertEqual(out["citta_originale"], row["citta"])
                self.assertEqual(out["localita_ricostruita_da"], PUBLISHED_TOWN_FIXES[rule])
                self.assertEqual(report["counts"]["published_town_" + rule], 1)
                self.assertEqual((out["slug"], out["lat"], out["date"]), (row["slug"], row["lat"], row["date"]))
        out, _ = self.fixed(happings("Atelena", "AQ", "Abruzzo"))
        self.assertEqual((out["nome"], out["nome_originale"]),
                         ("Mercato settimanale di Ateleta", "Mercato settimanale di Atelena"))
        out, _ = self.fixed(happings("Nibbiano", "PC", "Emilia-Romagna"))
        self.assertEqual(out["nome"], "Mercato settimanale di Nibbiano")  # still names the place

    def test_unclear_names_stay_as_published(self):
        rows = [
            happings("Sestri", "GE", "Liguria"),         # Sestri Levante or Sestri Ponente
            happings("Cecchina", "RM", "Lazio"),         # hamlet of Albano Laziale, not Rome
            happings("Forio 3", "NA", "Campania"),       # S15: the publisher's numbering
            happings("Genzano", "", "Lazio"),            # no province to narrow it
            happings("Capristrano", "VB", "Calabria"),   # VB is Piemonte's code: it waits
            {**happings("Atelena", "AQ", "Abruzzo", slug="other-source"), "fonte": "eventiesagre.it"},
            {**happings("Atelena", "AQ", "Abruzzo", slug="verified"), "verificato_il": "2026-10-01"},
        ]
        out, report = reconcile(copy.deepcopy(rows), REFERENCE, apply=True)
        self.assertEqual(out, rows)
        self.assertEqual(report["counts"]["published_town_protected"], 1)

    def test_receipts_and_happings_matching_see_the_published_card(self):
        row = happings("Atelena", "AQ", "Abruzzo")
        row["riscontri_campi"] = [make_receipt(
            row, values={"indirizzo": "Piazza Roma"}, source_url=row["url_fonte"],
            source_name="happings.com", source_id="happings-weekly", source_row="atelena:0",
            read_on="2026-10-28", source_updated_on="", source_sha256="a" * 64)]
        out, _ = self.fixed(row)
        self.assertNotEqual(out["citta"], row["citta"])
        self.assertEqual(identity(out), identity(row))
        self.assertEqual(clean_receipts(out["riscontri_campi"], out, today=TODAY_RECEIPT),
                         clean_receipts(row["riscontri_campi"], row, today=TODAY_RECEIPT))
        self.assertEqual(len(clean_receipts(out["riscontri_campi"], out, today=TODAY_RECEIPT)), 1)
        self.assertTrue(same_generic_venue(out))
        self.assertEqual(published_town(out), "Atelena")
        rome, _ = self.fixed(happings("CRATI", "RM", "Lazio"))
        self.assertTrue(same_generic_venue(rome))
        # The weekly page still lists "Atelena": the renamed card blocks a duplicate.
        self.assertTrue(_possible_existing(out, "Atelena", "Abruzzo", "AQ", 1))
        self.assertFalse(_possible_existing(out, "Ateleta", "Abruzzo", "AQ", 1))

    def test_nightly_budget_fixes_visible_cards_first_and_replays_unchanged(self):
        rows = [{**happings("Atelena", "AQ", "Abruzzo", slug=f"a-{i:02}"),
                 **({"duplicato_di": "x"} if i < 10 else {})} for i in range(70)]
        out, report = reconcile(rows, REFERENCE, apply=True)
        fixed = [r["slug"] for r in out if r["citta"] == "Ateleta"]
        self.assertEqual(len(fixed), CITY_FIX_BUDGET)
        self.assertEqual(report["counts"]["published_town_pending"], 10)
        self.assertTrue(all(int(slug[2:]) >= 10 for slug in fixed))
        self.assertEqual(check(rows, out, report)["city_replacements"], CITY_FIX_BUDGET)
        again, report = reconcile(out, REFERENCE, apply=True)
        self.assertEqual(sum(r["citta"] == "Ateleta" for r in again), 70)
        self.assertEqual(report["counts"]["published_town_pending"], 0)

    def test_guard_rejects_a_town_fix_with_another_label(self):
        row = happings("Africo Nuovo", "RC", "Calabria")
        out, report = reconcile([row], REFERENCE, apply=True)
        check([row], out, report)
        out[0]["localita_ricostruita_da"] = PUBLISHED_TOWN_FIXES["rome"]
        with self.assertRaisesRegex(ValueError, "provenance missing"):
            check([row], out, report)


if __name__=="__main__":
    unittest.main()
