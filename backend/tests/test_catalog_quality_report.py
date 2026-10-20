import copy
from datetime import date
import unittest
from pathlib import Path
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from catalog_quality_report import analyze, suspicious_city, count_venue_weekday_groups
from field_evidence import make_receipt


def mk(slug,city="Albizzate",region="Lombardia",street="Piazzale Sefro",
       recurrence="settimanale - martedì",future=None,quality="prevista",**kw):
    row={
        "slug":slug,"nome":"Mercato settimanale di "+city,
        "citta":city,"regione":region,"indirizzo":street,
        "ricorrenza_testo":recurrence,"orario_testo":"",
        "fonte":"happings.com","url_fonte":"https://example.org/markets/a",
        "date":future if future is not None else ["2026-10-13","2026-10-20"],
        "date_quality":quality,"lat":45.724163,"lng":8.797983,
        "verificato_il":"",
    }
    row.update(kw)
    return row


def overlap_recovery_catalog():
    """Reproduce the failed run's 765 -> 859 overlap arithmetic with stable IDs."""
    baseline = [mk(f"known-{i}-{j}", city=f"Existing town {i}", provincia="VA")
                for i in range(765) for j in range(2)]
    baseline += [mk(f"recovered-{i}-{j}", city=f"Recovered town {i}",
                    street="" if j else "centro", provincia="VA")
                 for i in range(94) for j in range(2)]
    candidate = copy.deepcopy(baseline)
    for row in candidate:
        if row["slug"].startswith("recovered-"):
            row["indirizzo"] = "Piazza della Repubblica"
            receipt_for_address(row)
    return baseline, candidate


def receipt_for_address(row):
    row["riscontri_campi"] = [make_receipt(
        row, values={"indirizzo": row["indirizzo"]},
        source_url="https://www.dati.lombardia.it/d/68zx-njaw",
        source_name="Regione Lombardia", source_id="lombardia",
        source_row=row["citta"], read_on="2026-10-20",
        source_updated_on="2026-10-13", source_sha256="a" * 64,
        method="comune_provincia_giorno_univoco")]


class CatalogQualityTests(unittest.TestCase):
    def test_real_albizzate_two_weekly_cards_are_review_only_not_merged(self):
        old=[
            mk("mercato-settimanale-di-albizzate-albizzate"),
            mk("mercato-settimanale-di-albizzate-albizzate-martedi"),
        ]
        frozen=copy.deepcopy(old)
        report=analyze(old)
        self.assertEqual(report["metrics"]["review_only_duplicate_groups"],1)
        self.assertEqual(report["metrics"]["review_only_potential_extra_rows"],1)
        self.assertEqual(report["metrics"]["hours_missing"],2)
        self.assertEqual(report["metrics"]["without_individual_verification"],2)
        self.assertTrue(report["potential_duplicates_are_not_confirmed"])
        self.assertEqual(report["market_updates_applied"],0)
        self.assertEqual(old,frozen)

    def test_weekday_or_location_distinction_does_not_create_a_duplicate(self):
        otherday=mk("market-friday",recurrence="settimanale - venerdì",
                     future=["2026-10-16","2026-10-23"])
        anotherstreet=mk("market-street",street="Via Monici")
        markets=[mk("market-tuesday"),otherday,anotherstreet]
        self.assertEqual(count_venue_weekday_groups(markets),[])

    def test_nongeneric_festivals_are_not_automatically_deduplicated(self):
        source=mk("green-festival",
                  nome="Green Market Festival",
                  street="Largo Dino Frisullo")
        another=mk("green-festival-x",nome="Green Market Christmas",
                   street="Largo Dino Frisullo")
        self.assertEqual(count_venue_weekday_groups([source,another]),[])

    def test_unknown_future_requires_unknown_quality(self):
        bad=mk("bad-quality",future=[],quality="prevista")
        wrong=analyze([bad])
        self.assertFalse(wrong["quality_release_safe"])
        self.assertEqual(wrong["metrics"]["future_date_quality_mismatch"],1)
        from export_static import normalize
        from datetime import date
        fixed,error=normalize(bad,date(2026,10,12))
        self.assertIsNone(error)
        self.assertEqual(fixed["date_quality"],"sconosciuta")
        good=analyze([fixed])
        self.assertTrue(good["quality_release_safe"])
        self.assertEqual(good["metrics"].get("future_date_quality_mismatch",0),0)

    def test_unambiguous_city_naming_anomalies_are_review_only(self):
        self.assertTrue(suspicious_city('"Mercatino delle Curiosità"'))
        self.assertTrue(suspicious_city(
            "Castiglione delle Stiviere, in provincia... Mercato settimanale a Cavriana"
        ))
        self.assertTrue(suspicious_city("Via Tiburtina - FROSINONE"))
        self.assertTrue(suspicious_city("AL"))
        # Italian municipalities really can be named Piazza Brembana,
        # Piazza al Serchio and Piazzatorre.
        self.assertFalse(suspicious_city("Piazza Brembana"))
        self.assertFalse(suspicious_city("Piazza al Serchio"))
        self.assertFalse(suspicious_city("Piazzatorre"))
        self.assertFalse(suspicious_city("San Pellegrino Terme"))

    def test_missing_hours_improve_without_claiming_human_verification(self):
        row=mk("one")
        report=analyze([row])
        newer={**row, "orario_testo":"08:00–13:00 (fonte comunale, da verificare)"}
        again=analyze([newer],report)
        self.assertEqual(again["baseline_delta"]["hours_missing"],-1)
        self.assertEqual(again["metrics"]["without_individual_verification"],1)
        self.assertEqual(again["market_confirmations_created"],0)

    def test_no_automatic_city_rewrites_or_erasure(self):
        original=mk("city-uncertain",city='"Mercatino delle Curiosità"')
        before=copy.deepcopy(original)
        result=analyze([original])
        self.assertEqual(result["metrics"]["suspicious_city"],1)
        self.assertEqual(original,before)
        self.assertEqual(result["market_identities_deleted"],0)

    def test_sudden_invalid_city_growth_blocks_future_quality_promotion(self):
        base=analyze([mk("first")])
        additions=[mk("bad-"+str(i), city='"Mercatino delle Curiosità"')
                   for i in range(7)]
        candidate=analyze([mk("first")]+additions,base)
        self.assertFalse(candidate["quality_release_safe"])
        self.assertEqual(candidate["quality_regressions"][0]["code"],"suspicious_city")
        self.assertGreater(candidate["baseline_delta"]["suspicious_city"],5)
        self.assertEqual(candidate["market_updates_applied"],0)

    def test_small_intentional_source_growth_can_be_review_only(self):
        base=analyze([mk("first")])
        candidate=analyze([mk("first"),
                           mk("suspicious",city='"Street Market"')],base)
        self.assertTrue(candidate["quality_release_safe"])
        self.assertEqual(candidate["metrics"]["suspicious_city"],1)
        self.assertEqual(candidate["market_confirmations_created"],0)

    def test_repeated_input_is_deterministic(self):
        market=mk("duplicate-input")
        a=analyze([market])
        self.assertEqual(a,analyze([market]))

    def test_invalid_previous_report_or_duplicate_ids_are_blocked(self):
        one=mk("duplicate")
        with self.assertRaisesRegex(ValueError,"Duplicate or missing"):
            analyze([one,one])
        with self.assertRaisesRegex(ValueError,"Untrusted prior"):
            analyze([one],{"schema":1,"review_only":False})
        with self.assertRaisesRegex(ValueError,"Invalid or unbounded"):
            analyze([])

    def test_documented_missing_address_recovery_preserves_raw_overlap_totals(self):
        baseline, candidate = overlap_recovery_catalog()
        original = copy.deepcopy((baseline, candidate))
        previous = analyze(baseline)
        report = analyze(candidate, previous, baseline_rows=baseline, today=date(2026,10,20))
        self.assertTrue(report["quality_release_safe"])
        self.assertEqual(previous["metrics"]["review_only_potential_extra_rows"], 765)
        self.assertEqual(report["metrics"]["review_only_potential_extra_rows"], 859)
        self.assertEqual(report["baseline_delta"]["review_only_potential_extra_rows"], 94)
        review = report["overlap_growth_review"]
        self.assertEqual(review["source_supported_revealed_extra_rows"], 94)
        self.assertEqual(review["unexplained_group_growth"], 0)
        self.assertEqual((baseline, candidate), original)
        self.assertEqual(report["market_identities_deleted"], 0)
        self.assertEqual(report["market_confirmations_created"], 0)

    def test_previous_summary_without_baseline_rows_keeps_original_gate(self):
        baseline, candidate = overlap_recovery_catalog()
        report = analyze(candidate, analyze(baseline), today=date(2026,10,20))
        self.assertFalse(report["quality_release_safe"])
        self.assertEqual(report["quality_regressions"][0]["maximum_permitted_increase"], 77)
        self.assertEqual(report["overlap_growth_review"]["source_supported_revealed_extra_rows"], 0)

    def test_unsupported_recovery_or_mismatched_proof_still_blocks(self):
        baseline, candidate = overlap_recovery_catalog()
        previous = analyze(baseline)
        for tamper in ("missing", "identity", "value", "hash", "future_read"):
            with self.subTest(tamper=tamper):
                changed = copy.deepcopy(candidate)
                for row in changed:
                    if not row["slug"].startswith("recovered-"):
                        continue
                    proof = row["riscontri_campi"][0]
                    if tamper == "missing":
                        row["riscontri_campi"] = []
                    elif tamper == "identity":
                        proof["mercato"]["slug"] = "unrelated-market"
                    elif tamper == "value":
                        proof["valori"]["indirizzo"] = "Via Indipendenza"
                    elif tamper == "hash":
                        proof["sha256"] = "invalid"
                    else:
                        proof["letto_il"] = "2026-10-21"
                report = analyze(changed, previous, baseline_rows=baseline, today=date(2026,10,20))
                self.assertFalse(report["quality_release_safe"])
                self.assertEqual(report["overlap_growth_review"]["unexplained_group_growth"], 94)

    def test_new_ids_cannot_be_explained_by_another_records_address_recovery(self):
        baseline, candidate = overlap_recovery_catalog()
        for row in candidate:
            if row["slug"].startswith("recovered-") and row["slug"].endswith("-1"):
                row["slug"] += "-new"
                receipt_for_address(row)
        # Retain the old identities too. The new overlapping records have
        # valid receipts, but did not exist in the published baseline.
        candidate += [copy.deepcopy(row) for row in baseline
                      if row["slug"].startswith("recovered-") and row["slug"].endswith("-1")]
        report = analyze(candidate, analyze(baseline), baseline_rows=baseline, today=date(2026,10,20))
        self.assertFalse(report["quality_release_safe"])
        self.assertEqual(report["overlap_growth_review"]["source_supported_revealed_extra_rows"], 0)

    def test_supported_recoveries_cannot_offset_unexplained_new_market_groups(self):
        baseline, recovered = overlap_recovery_catalog()
        for disappear_old_groups in (False, True):
            with self.subTest(disappear_old_groups=disappear_old_groups):
                candidate = copy.deepcopy(recovered)
                for i in range(94):
                    extra = mk(f"new-duplicate-{i}", city=f"Existing town {i + 200}", provincia="VA")
                    receipt_for_address(extra)
                    candidate.append(extra)
                if disappear_old_groups:
                    # Old overlaps disappearing elsewhere cannot cancel
                    # the unexplained growth of new market identities.
                    for row in candidate:
                        if row["slug"] in {f"known-{i}-0" for i in range(94)}:
                            row["indirizzo"] = "Via Indipendenza"
                report = analyze(candidate, analyze(baseline), baseline_rows=baseline,
                                 today=date(2026,10,20))
                self.assertFalse(report["quality_release_safe"])
                review = report["overlap_growth_review"]
                self.assertEqual(review["source_supported_revealed_extra_rows"], 94)
                self.assertEqual(review["unexplained_group_growth"], 94)
                self.assertEqual(report["quality_regressions"][0]["maximum_permitted_increase"], 77)

    def test_existing_venue_or_identity_changes_cannot_excuse_overlap_growth(self):
        base, candidate = overlap_recovery_catalog()
        for field, value in (("indirizzo", "Via Indipendenza"), ("provincia", "MI"),
                             ("url_fonte", "https://example.org/different-source"),
                             ("nome", "Mercato settimanale a altra località"),
                             ("ricorrenza_testo", "settimanale - venerdì"),
                             ("verificato_il", "2026-10-19"),
                             ("position_quality", "precisa")):
            with self.subTest(field=field):
                baseline = copy.deepcopy(base)
                for row in baseline:
                    if row["slug"].startswith("recovered-"):
                        row[field] = value
                report = analyze(candidate, analyze(baseline), baseline_rows=baseline,
                                 today=date(2026,10,20))
                self.assertFalse(report["quality_release_safe"])
                self.assertEqual(report["overlap_growth_review"]["source_supported_revealed_extra_rows"], 0)

    def test_old_address_evidence_and_unbound_baseline_cannot_authorize_recovery(self):
        baseline, candidate = overlap_recovery_catalog()
        for row in baseline:
            if row["slug"].startswith("recovered-") and row["indirizzo"]:
                receipt_for_address(row)
        previous = analyze(baseline)
        report = analyze(candidate, previous, baseline_rows=baseline, today=date(2026,10,20))
        self.assertFalse(report["quality_release_safe"])
        self.assertEqual(report["overlap_growth_review"]["source_supported_revealed_extra_rows"], 0)
        previous["metrics"]["total"] += 1
        report = analyze(candidate, previous, baseline_rows=baseline, today=date(2026,10,20))
        self.assertFalse(report["quality_release_safe"])
        self.assertEqual(report["overlap_growth_review"]["status"], "baseline_summary_mismatch")


if __name__=="__main__":
    unittest.main()
