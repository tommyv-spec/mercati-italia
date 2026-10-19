"""Regression tests for the five independent publisher facts on 2026-10-12."""
import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/"backend"))

from publisher_exception_review import (
    apply_source_repairs, validate_evidence, verify_diff, evidence_digest,
    NAVIGATION_HOLD, COORD_HOLD, PROVENANCE
)
from recurrence_refresh import refresh_records, project_dates

ISTAT=json.loads((ROOT/"backend/data/istat-comuni-2026.json").read_text("utf-8"))
EVIDENCE=json.loads((ROOT/"backend/data/publisher-review-2026-10-12.json").read_text("utf-8"))
POLICY=json.loads((ROOT/"backend/autopilot_policy.json").read_text("utf-8"))
TODI="todi-artigianando-mostra-mercato-della-creativita-giardini-oberdan-artigianando"
COLLALTO="mercato-settimanale-di-centro-storico-di-collalto-in-provincia-mercato-settimana"
WEDNESDAY="mercato-settimanale-di-centro-storico-di-collalto-collalto-mercoledi"
TV1="mercatini-piazza-del-baratto-na"
TV2="mercatini-stoffaday-na"


def old_catalog():
    rows=[]
    for item in EVIDENCE["cases"]:
        expected=item["expected"]
        slug=item["slug"]
        if slug==TODI:
            predicted=["2026-10-18","2026-11-15","2026-12-20","2027-01-17"]
            cadence="mensile - terza domenica del mese"
            recurrence={"kind":"monthly_nth_weekday","ordinal":3,"weekday":6}
        elif slug==WEDNESDAY:
            predicted=project_dates({"kind":"weekly","weekdays":[2]},date(2026,10,12),120)
            cadence="settimanale - mercoledì"
            recurrence={"kind":"weekly","weekdays":[2]}
        elif slug==COLLALTO:
            predicted=[]
            cadence="Calendario da verificare: testo origine con mercati/località concatenati"
            recurrence=None
        else:
            predicted=[]
            cadence=""
            recurrence=None
        rows.append({
            "slug":slug,"nome":expected["name"],
            "citta":expected["city"],"provincia":expected["province"],
            "regione":expected["region"],"indirizzo":expected["address"],
            "lat":expected["lat"],"lng":expected["lng"],
            "position_quality":"non_verificata",
            "url_fonte":expected["source_url"],
            "fonte":"publisher","fonti":[{"nome":"publisher","url":expected["source_url"]}],
            "date":predicted,
            "date_quality":"prevista" if predicted else "sconosciuta",
            "ricorrenza_testo":cadence,
            "proiezione_regola":recurrence,
            "proiezione_fonte":"ricorrenza_testo" if predicted else "",
            "proiezione_generata_il":"2026-10-12" if predicted else "",
            "orario_testo":"","verificato_il":"","status":"non_confermato",
            "aggiornato_il":"2026-06-05",
        })
    return rows


def catalog_with_dated_todi_source():
    # Positive forecast fixture: the publisher explicitly declares this
    # content date. The separate legacy import timestamp remains unchanged.
    # This does not assign a new source date to the real catalog or register.
    rows=old_catalog()
    next(row for row in rows if row["slug"]==TODI)["fonte_aggiornata_il"]="2026-10-01"
    return rows


class ReviewedPublisherFacts(unittest.TestCase):
    NOW=date(2026,10,12)

    def test_five_exact_sources_pinned_to_istat_and_region_extent(self):
        by_id=validate_evidence(EVIDENCE,ISTAT)
        self.assertEqual(len(by_id),5)
        self.assertEqual(POLICY["reviewed_publisher_exceptions"]["evidence_sha256"],
                         evidence_digest(EVIDENCE))
        self.assertEqual([by_id[s]["target_city"] for s in (TODI,COLLALTO,WEDNESDAY)],
                         ["Todi","Susegana","Susegana"])

    def test_exact_fixes_never_delete_verify_or_replace_sources(self):
        original=old_catalog()
        frozen=copy.deepcopy(original)
        result,report=apply_source_repairs(original,ISTAT,EVIDENCE,today=self.NOW,apply=True)
        counts=report["counts"]
        self.assertEqual(counts["cities_corrected"],3)
        self.assertEqual(counts["unsafe_points_quarantined"],5)
        self.assertEqual(counts["navigation_held"],5)
        self.assertEqual(counts["winter_forecast_dates_filtered"],3)
        self.assertEqual(counts["titles_corrected"],2)
        self.assertEqual(counts["addresses_corrected"],1)
        self.assertEqual(counts["hours_filled"],1)
        self.assertEqual(len(result),5)
        self.assertEqual(original,frozen)
        proof=verify_diff(original,result,report,EVIDENCE)
        self.assertEqual(proof["approved_source_cases"],5)
        self.assertEqual(proof["publisher_urls_replaced"],0)
        self.assertEqual(proof["market_ids_deleted"],0)
        for before,after in zip(original,result):
            for key in ("slug","provincia","regione","url_fonte","fonte","fonti",
                        "verificato_il","status","aggiornato_il"):
                self.assertEqual(before[key],after[key],key)
            self.assertEqual(after["navigazione_sospesa_motivo"],NAVIGATION_HOLD)
            self.assertEqual(after["coordinate_sospese_motivo"],COORD_HOLD)
            self.assertEqual(after["coordinate_originali"],{"lat":before["lat"],"lng":before["lng"]})
            self.assertIsNone(after["lat"])
            self.assertIsNone(after["lng"])
            self.assertNotEqual(after["date_quality"],"confermata")
        now={row["slug"]:row for row in result}
        self.assertEqual(now[TODI]["date"],["2026-10-18"])
        self.assertIn("marzo a ottobre",now[TODI]["ricorrenza_testo"])
        self.assertEqual(now[TODI]["orario_testo"],"09:00–tramonto")
        self.assertEqual(now[TODI]["localita_ricostruita_da"],PROVENANCE)
        self.assertEqual(now[TV1]["citta"],"NA")
        self.assertEqual(now[TV2]["citta"],"NA")
        self.assertEqual(now[WEDNESDAY]["date"],frozen[2]["date"])

    def test_read_only_audit_does_not_touch_source(self):
        source=old_catalog()
        new,report=apply_source_repairs(source,ISTAT,EVIDENCE,today=self.NOW,apply=False)
        self.assertEqual(new,source)
        self.assertFalse(report["enabled"])
        self.assertEqual(report["changed_ids"],[])

    def test_idempotent_second_source_pass_after_forecast(self):
        first,_=apply_source_repairs(catalog_with_dated_todi_source(),ISTAT,EVIDENCE,today=self.NOW,apply=True)
        forecasted,_=refresh_records(first,self.NOW)
        again,report=apply_source_repairs(forecasted,ISTAT,EVIDENCE,today=self.NOW,apply=True)
        self.assertEqual(first,again)
        self.assertEqual(report["counts"]["cities_corrected"],0)
        self.assertEqual(report["counts"]["unsafe_points_quarantined"],0)
        self.assertEqual(report["counts"]["navigation_held"],0)
        # The generic forecast engine already represents the complete named
        # month range; the second source pass has no winter dates to remove.
        self.assertEqual(report["counts"]["winter_forecast_dates_filtered"],0)
        verify_diff(forecasted,again,report,EVIDENCE)

    def test_spring_return_is_predicted_not_confirmed(self):
        first,_=apply_source_repairs(catalog_with_dated_todi_source(),ISTAT,EVIDENCE,today=self.NOW,apply=True)
        jan=date(2027,1,20)
        forecasted,_=refresh_records(first,jan)
        after,_=apply_source_repairs(forecasted,ISTAT,EVIDENCE,today=jan,apply=True)
        todi=next(x for x in after if x["slug"]==TODI)
        self.assertEqual(todi["date"][:2],["2027-03-21","2027-04-18"])
        self.assertTrue(all(date.fromisoformat(d).month in range(3,11) for d in todi["date"]))
        self.assertEqual(todi["date_quality"],"prevista")

    def test_legacy_import_does_not_date_a_reviewed_seasonal_source(self):
        first,_=apply_source_repairs(old_catalog(),ISTAT,EVIDENCE,today=self.NOW,apply=True)
        todi=next(row for row in first if row["slug"]==TODI)
        todi["aggiornato_il"]="2027-01-20T09:00:00"
        todi["importato_il"]="2027-01-20T09:00:00+00:00"
        before=copy.deepcopy(todi)
        forecasted,report=refresh_records([todi],date(2027,1,20))
        self.assertEqual(forecasted,[before])
        self.assertEqual(report["reasons"],{"unknown_source_age":1})
        self.assertEqual(report["newly_dated"],0)
        self.assertEqual(report["unknown_source_dates_preserved_without_renewal"],1)
        self.assertEqual(forecasted[0]["proiezione_generata_il"],"2026-10-12")
        self.assertEqual(forecasted[0]["verificato_il"],"")

    def test_wrong_source_city_status_and_verified_claim_fail(self):
        bad=old_catalog()
        bad[0]["url_fonte"]="https://another.example/market"
        with self.assertRaisesRegex(ValueError,"publisher province drifted|Source identity"):
            apply_source_repairs(bad,ISTAT,EVIDENCE,today=self.NOW,apply=True)
        bad=old_catalog()
        bad[0]["date_quality"]="confermata"
        with self.assertRaisesRegex(ValueError,"Human-verified"):
            apply_source_repairs(bad,ISTAT,EVIDENCE,today=self.NOW,apply=True)
        bad=old_catalog()
        bad[1]["citta"]="Altro Comune"
        with self.assertRaisesRegex(ValueError,"Source field drifted"):
            apply_source_repairs(bad,ISTAT,EVIDENCE,today=self.NOW,apply=True)

    def test_unproven_source_or_geographic_anchor_fails(self):
        original=copy.deepcopy(EVIDENCE)
        original["cases"][0]["target_province"]="TV"
        with self.assertRaisesRegex(ValueError,"ISTAT"):
            validate_evidence(original,ISTAT)
        original=copy.deepcopy(EVIDENCE)
        point=original["cases"][0]["expected"]
        original["cases"][0]["anchor"]["lat"]=point["lat"]
        original["cases"][0]["anchor"]["lng"]=point["lng"]
        with self.assertRaisesRegex(ValueError,"outside the documented town"):
            validate_evidence(original,ISTAT)
        original=copy.deepcopy(EVIDENCE)
        original["cases"][-1]["region_extent"]["min_lat"]=42.0
        with self.assertRaisesRegex(ValueError,"Veneto extent"):
            validate_evidence(original,ISTAT)

    def test_changed_non_reviewed_market_and_fabricated_opening_fail(self):
        original=old_catalog()
        checked,report=apply_source_repairs(original,ISTAT,EVIDENCE,today=self.NOW,apply=True)
        tampered=copy.deepcopy(checked)
        tampered[0]["status"]="attivo"
        with self.assertRaisesRegex(ValueError,"Unapproved publisher source field"):
            verify_diff(original,tampered,report,EVIDENCE)
        tampered=copy.deepcopy(checked)
        tampered[1]["date"]=["2026-10-16"]
        with self.assertRaisesRegex(ValueError,"Other publisher calendar"):
            verify_diff(original,tampered,report,EVIDENCE)

    def test_missing_or_duplicate_original_id_aborts(self):
        rows=old_catalog()
        with self.assertRaisesRegex(ValueError,"vanished"):
            apply_source_repairs(rows[:-1],ISTAT,EVIDENCE,today=self.NOW,apply=True)
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            apply_source_repairs(rows+[rows[0]],ISTAT,EVIDENCE,today=self.NOW,apply=True)


if __name__=="__main__":
    unittest.main()
