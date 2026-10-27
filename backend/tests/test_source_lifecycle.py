import copy
import csv
import io
import json
import sys
import unittest
from datetime import date,timedelta
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from source_lifecycle import (
    validate_contracts,parse_rows,inspect_raw,inspect_normalized,
    candidate_record,weekday,run,digest,markdown
)

FULL_CFG=json.loads((Path(__file__).resolve().parents[1]/
                     "data/market-source-contracts.json").read_text("utf-8"))
CFG=copy.deepcopy(FULL_CFG)
# Existing Corciano fixture is intentionally independent of Bologna.
CFG["raw_profiles"]=CFG["raw_profiles"][:1]
RAW=CFG["raw_profiles"][0]
OFFICIAL=next(x for x in CFG["normalized_profiles"] if x["id"]=="corciano")
HEADER=RAW["schema_columns"]
NAMES=("MERCATO DI CORCIANO","MERCATO DI ELLERA",
       "MERCATO DI MANTIGNANA","MERCATO DI SAN MARIANO")
WEEKDAYS=("Lunedì","Martedì","Mercoledì","Giovedì")


def raw_rows():
    return [{
        "denominazione":name,
        "giorni_svolgimento":WEEKDAYS[i],
        "tipo_strada":"Piazza",
        "ubicazione":("Via delle Fonti" if i==0 else f"Test Municipio {i}"),
        "numero_tot_posteggi":"14",
        "numero_posteggi_riservati":"2",
        "orario_svolgimento_dalle":"08:00",
        "orario_svolgimento_alle":"13:00",
        # Crucial: known mislabeled provider columns. Never geocode them.
        "long":"43.10","lat":"12.35","geopoint":"(43.10, 12.35)",
    } for i,name in enumerate(NAMES)]


def csv_blob(rows=None,fields=None):
    out=io.StringIO()
    writer=csv.DictWriter(out,fieldnames=fields or HEADER,delimiter=";")
    writer.writeheader()
    writer.writerows(rows if rows is not None else raw_rows())
    return out.getvalue().encode("utf-8")


def catalog():
    return [
      {"slug":"pg-corciano-mercato-di-corciano",
       "nome":"Mercato di Corciano","citta":"Corciano",
       "regione":"Umbria","indirizzo":"Piazza Via delle Fonti",
       "url_fonte":RAW["attribution_url"],
       "status":"non_confermato","date_quality":"sconosciuta"},
      {"slug":"pg-corciano-mercato-di-ellera",
       "nome":"Mercato di Ellera","citta":"Corciano",
       "regione":"Umbria","indirizzo":"Piazza Altra",
       "url_fonte":RAW["attribution_url"],
       "status":"non_confermato","date_quality":"sconosciuta"},
      {"slug":"legacy-bologna-market","nome":"Mercato settimanale",
       "citta":"Bologna","regione":"Emilia-Romagna",
       "indirizzo":"Via del Mercato","url_fonte":"https://example.org/",
       "status":"non_confermato","date_quality":"sconosciuta"}
    ]


class DeclarativeSourceLifecycleTests(unittest.TestCase):
    def test_contracts_cover_five_existing_adapters_and_five_raw_sources(self):
        c=validate_contracts(FULL_CFG)
        self.assertEqual(len(c["normalized_profiles"]),5)
        self.assertEqual(len(c["raw_profiles"]),5)
        self.assertEqual(RAW["source_date_scope"],"dataset_not_per_market")
        self.assertEqual(RAW["publication_mode"],"approved_dev_only")
        self.assertEqual(RAW["max_new_ids_per_run"],2)

    def test_real_corciano_csv_schema_inferred_without_source_specific_code(self):
        source=catalog()
        old=copy.deepcopy(source)
        result=inspect_raw(RAW,csv_blob(),source,today=date(2026,10,13))
        counts=result["counts"]
        self.assertEqual(counts["rows_observed"],4)
        self.assertEqual(counts["distinct_market_identities"],4)
        self.assertEqual(counts["already_in_catalog_exact_source_id"],2)
        self.assertEqual(counts["identity_not_in_existing_catalog"],2)
        self.assertEqual(result["market_names_distinct_not_new_events"],4)
        self.assertEqual(result["catalog_records_imported"],0)
        self.assertEqual(result["individual_market_openings_verified"],0)
        self.assertEqual(result["license_reviewed_for_automatic_publication"],False)
        self.assertEqual(result["source_data_scope"],"dataset_not_per_market")
        self.assertEqual(result["diff"]["first_observation"],True)
        self.assertEqual(source,old)

    def test_source_update_changes_only_one_identity_not_other_markets(self):
        first=inspect_raw(RAW,csv_blob(),catalog(),today=date(2026,10,13))
        changed=raw_rows()
        changed[0]["orario_svolgimento_alle"]="14:00"
        second=inspect_raw(RAW,csv_blob(changed),catalog(),first,today=date(2026,10,13))
        d=second["diff"]
        self.assertFalse(d["first_observation"])
        self.assertEqual(d["changed_source_identities_since_last_scan"],1)
        self.assertEqual(d["added_source_identities_since_last_scan"],0)
        self.assertEqual(d["missing_source_identities_since_last_scan"],0)
        self.assertEqual(d["same_source_identities_since_last_scan"],3)
        repeat=inspect_raw(RAW,csv_blob(changed),catalog(),second,today=date(2026,10,13))
        self.assertEqual(repeat["diff"]["changed_source_identities_since_last_scan"],0)

    def test_missing_source_row_is_not_market_closure_or_record_deletion(self):
        approved=copy.deepcopy(RAW);approved["min_rows"]=3
        first=inspect_raw(approved,csv_blob(),catalog())
        second=inspect_raw(approved,csv_blob(raw_rows()[:-1]),catalog(),first)
        self.assertEqual(second["diff"]["missing_source_identities_since_last_scan"],1)
        self.assertEqual(second["catalog_records_modified"],0)
        self.assertEqual(second["existing_record_ids_deleted"],0)
        self.assertEqual(second["catalog_records_imported"],0)

    def test_duplicate_concessions_not_counted_as_visitable_market_rows(self):
        p=copy.deepcopy(RAW)
        p["row_kind"]="concession"
        p["market_filter"]={}
        report=inspect_raw(p,csv_blob(),catalog())
        self.assertEqual(report["counts"]["non_venue_administrative_rows"],4)
        self.assertNotIn("distinct_market_identities",report["counts"])
        self.assertEqual(report["catalog_records_imported"],0)

    def test_nessun_giorno_does_not_invent_next_market_occurrences(self):
        data=raw_rows()
        data[2]["giorni_svolgimento"]="Nessun giorno"
        report=inspect_raw(RAW,csv_blob(data),catalog())
        self.assertEqual(report["counts"]["needs_review_schedule_unknown"],1)
        self.assertEqual(weekday("Nessun giorno"),None)
        record,reason,_=candidate_record(RAW,data[2],today=date(2026,10,13))
        self.assertEqual(reason,"schedule_unknown")
        self.assertEqual(record["ricorrenza_testo"],"Calendario da verificare")
        self.assertEqual(record["date"],[])
        self.assertEqual(record["date_quality"],"sconosciuta")

    def test_publisher_metadata_date_does_not_confirm_individual_openings(self):
        a=raw_rows()[0]
        x,_,_=candidate_record(RAW,a,today=date(2026,10,13))
        self.assertEqual(x["aggiornato_il"],"2026-01-07")
        self.assertEqual(x["aggiornamento_ambito"],"dataset")
        self.assertEqual(x["date"],[])
        self.assertEqual(x["status"],"non_confermato")
        self.assertFalse(x["verificato_il"])
        self.assertIsNone(x["lat"])
        self.assertIsNone(x["lng"])
        self.assertEqual(x["position_quality"],"sconosciuta")
        self.assertTrue(x["navigazione_sospesa_motivo"])

    def test_old_source_cannot_project_a_new_calendar_forever(self):
        expired=date.fromisoformat(RAW["source_dataset_date"])+timedelta(days=541)
        a,issue,_=candidate_record(RAW,raw_rows()[0],today=expired)
        self.assertEqual(issue,"source_old_no_future_forecast")
        self.assertEqual(a["ricorrenza_testo"],"Calendario da verificare")
        self.assertFalse(a["date"])

    def test_invalid_and_expanded_csv_fail_before_applying_venue_information(self):
        with self.assertRaisesRegex(ValueError,"changed CSV columns"):
            parse_rows(RAW,csv_blob(rows=[
                {k:v for k,v in item.items() if k!="geopoint"}
                for item in raw_rows()],fields=HEADER[:-1]))
        with self.assertRaisesRegex(ValueError,"outside source contract"):
            parse_rows(RAW,csv_blob(rows=raw_rows()[:2]))
        with self.assertRaisesRegex(ValueError,"bounded size"):
            parse_rows(RAW,b"X"*17000)

    def test_same_name_in_two_source_rows_is_held_not_fabricated(self):
        a=raw_rows()
        a[3]["denominazione"]=a[0]["denominazione"]
        report=inspect_raw(RAW,csv_blob(a),catalog())
        self.assertEqual(report["counts"]["duplicate_publisher_market_identity"],1)
        self.assertEqual(report["counts"]["distinct_market_identities"],3)
        self.assertEqual(report["catalog_records_imported"],0)

    def test_ssrf_unreviewed_licence_and_imprecise_identity_are_blocked(self):
        for field,value in (
           ("resource_url","http://localhost/private"),
           ("resource_url","https://comune.corciano.pg.it.attacker.test/sample.csv"),
           ("publication_mode","approved_dev"),
           ("legal_reuse_reviewed",False),
           ("max_new_ids_per_run",999),
           ("coordinates","taken_as_precise_without_independent_check"),
           ("source_date_scope","per_market_confirmed"),
        ):
            cfg=copy.deepcopy(CFG)
            cfg["raw_profiles"][0][field]=value
            with self.subTest(field=field),self.assertRaises(ValueError):
                validate_contracts(cfg)
        cfg=copy.deepcopy(CFG)
        cfg["raw_profiles"][0]["row_kind"]="market_venue_day"
        with self.assertRaisesRegex(ValueError,"weekday in stable identity"):
            validate_contracts(cfg)

    def test_normalized_source_profile_detects_safe_existing_and_new_ids(self):
        examples=[]
        for i in range(4):
            examples.append({
                "slug":"pg-corciano-mercato-di-"+("corciano","ellera","mantignana","san-mariano")[i],
                "nome":"Mercato Comunale "+str(i),
                "citta":"Corciano","regione":"Umbria","indirizzo":"Via Test "+str(i),
                "url_fonte":RAW["attribution_url"],"status":"non_confermato",
                "date_quality":"prevista","verificato_il":"",
                "position_quality":"non_verificata",
                "orario_testo":"08:00 - 13:00",
                "ricorrenza_testo":"settimanale - lunedì",
                "aggiornato_il":"2026-01-07",
            })
        original=copy.deepcopy(examples)
        report=inspect_normalized(OFFICIAL,examples,catalog())
        self.assertEqual(report["counts"]["existing_ids_seen_in_catalog"],2)
        self.assertEqual(report["counts"]["source_ids_not_yet_in_catalog"],2)
        self.assertEqual(report["counts"]["forecast_only_not_confirmed"],4)
        self.assertEqual(report["market_records_imported"],0)
        self.assertEqual(examples,original)
        later=inspect_normalized(OFFICIAL,examples,catalog(),report)
        self.assertEqual(later["diff"]["new_source_identities_since_last_scan"],0)
        self.assertEqual(later["diff"]["changed_existing_identities_since_last_scan"],0)
        examples[0]["url_fonte"]="https://unexpected-website.invalid/market"
        with self.assertRaisesRegex(ValueError,"source contract"):
            inspect_normalized(OFFICIAL,examples,catalog())

    def test_generic_source_screening_does_not_reopen_known_overlap_quarantine(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as work:
            source_folder=Path(work)
            rows=[]
            for i,name in enumerate(("corciano","ellera","mantignana","san-mariano")):
                rows.append({
                    "slug":"pg-corciano-mercato-di-"+name,
                    "nome":"Mercato di "+name,
                    "citta":"Corciano","regione":"Umbria","indirizzo":"Piazza Test "+str(i),
                    "url_fonte":RAW["attribution_url"],
                    "status":"non_confermato","date_quality":"prevista",
                    "verificato_il":"","position_quality":"non_verificata",
                    "orario_testo":"08:00 - 13:00",
                    "ricorrenza_testo":"settimanale - lunedì",
                    "aggiornato_il":"2026-01-07",
                })
            (source_folder/"corciano.json").write_text(json.dumps(rows),"utf-8")
            excluded_ids=[rows[2]["slug"],rows[3]["slug"]]
            checked_status={"corciano":{"status":"retrieved","quarantined_review":2,
                                        "accepted_after_overlap_qa":2}}
            result=run(CFG,catalog(),source_dir=source_folder,
                       source_status=checked_status,
                       source_dispositions={"corciano":excluded_ids})
            scan=result["sources"]["corciano"]["source_screening"]
            self.assertEqual(scan["outside_catalog_source_ids_not_necessarily_new_markets"],2)
            self.assertEqual(scan["already_quarantined_by_venue_overlap_review"],2)
            self.assertEqual(scan["remaining_identities_without_overlap_disposition"],0)
            self.assertTrue(scan["exact_reviewed_id_partition_verified"])
            self.assertEqual(len(scan["quarantine_source_id_set_sha256"]),64)
            self.assertTrue(scan["source_screening_counts_are_not_market_opening_proofs"])
            # A matching NUMBER alone must not hide unresolved source IDs.
            unproven=run(CFG,catalog(),source_dir=source_folder,
                         source_status=checked_status)
            pending=unproven["sources"]["corciano"]["source_screening"]
            self.assertEqual(pending["already_quarantined_by_venue_overlap_review"],0)
            self.assertEqual(pending["remaining_identities_without_overlap_disposition"],2)
            self.assertTrue(pending["screening_missing_exact_source_id_proof"])
            with self.assertRaisesRegex(ValueError,"Already published"):
                run(CFG,catalog(),source_dir=source_folder,
                    source_status=checked_status,
                    source_dispositions={"corciano":[rows[0]["slug"],rows[3]["slug"]]})
            with self.assertRaisesRegex(ValueError,"Count of exact reviewed exclusions"):
                run(CFG,catalog(),source_dir=source_folder,
                    source_status={"corciano":{"quarantined_review":1,
                                              "accepted_after_overlap_qa":3}},
                    source_dispositions={"corciano":excluded_ids})
            self.assertEqual(result["market_imports"],0)
            self.assertIn("Già trattenuti dal controllo",markdown(result))
            with self.assertRaisesRegex(ValueError,"overlap quarantine"):
                run(CFG,catalog(),source_dir=source_folder,
                    source_status={"corciano":{"quarantined_review":"unbounded"}})

    def test_online_errors_leave_prior_checkpoint_not_erase_markets(self):
        first=run(CFG,catalog(),probe_raw=True,raw_fetch=lambda url:(csv_blob(),False))
        self.assertEqual(first["source_checks"]["source_level_raw_profiles_checked"],1)
        self.assertEqual(first["market_imports"],0)
        second=run(CFG,catalog(),previous=first,probe_raw=True,
                   raw_fetch=lambda url:(_ for _ in ()).throw(OSError("offline")))
        self.assertEqual(second["source_checks"]["raw_source_unavailable_no_market_inference"],1)
        item=second["sources"][RAW["id"]]
        self.assertTrue(item["stale_snapshot_carry_forward"])
        self.assertEqual(item["fingerprints"],first["sources"][RAW["id"]]["fingerprints"])
        self.assertNotIn("Secret Name",json.dumps(second))
        self.assertIn("non disponibile",markdown(second))

    def test_schema_change_is_explicit_review_not_a_transport_outage(self):
        first=run(CFG,catalog(),probe_raw=True,raw_fetch=lambda url:(csv_blob(),False))
        wrong=csv_blob(rows=[
            {k:v for k,v in item.items() if k!="geopoint"}
            for item in raw_rows()],fields=HEADER[:-1])
        changed=run(CFG,catalog(),previous=first,probe_raw=True,
                    raw_fetch=lambda url:(wrong,False))
        self.assertEqual(changed["source_checks"]["raw_schema_or_identity_change_requires_review"],1)
        self.assertNotIn("raw_source_unavailable_no_market_inference",
                         changed["source_checks"])
        self.assertEqual(changed["sources"][RAW["id"]]["last_check_status"],
                         "contract_change_needs_review")
        self.assertEqual(changed["market_imports"],0)
        self.assertEqual(changed["market_identity_deletions"],0)
        self.assertIn("schema/identità cambiati",markdown(changed))

    def test_daily_generic_staging_reuses_source_fetch_and_never_imports(self):
        calls=[]
        blob=csv_blob()
        def fetch(url):
            calls.append(url)
            return blob,False
        report=run(CFG,catalog(),probe_raw=True,stage_raw=True,
                   raw_fetch=fetch,today=date(2026,10,13),raw_read_on="2026-10-13")
        self.assertEqual(len(calls),1)
        self.assertEqual(report["source_checks"]["source_only_stage_reviews"],1)
        source=report["sources"][RAW["id"]]
        staging=source["source_stage"]
        self.assertEqual(staging["source_snapshot_sha256"],source["source_snapshot_sha256"])
        self.assertEqual(staging["counts"]["raw_rows_scanned"],4)
        self.assertEqual(staging["counts"]["already_in_catalog_exact_source_id"],2)
        self.assertEqual(staging["safe_candidates_not_published"],2)
        self.assertEqual(staging["publication_enabled"],False)
        self.assertEqual(staging["existing_market_identities_deleted"],0)
        self.assertEqual(staging["precise_coordinates_created"],0)
        self.assertEqual(report["market_imports"],0)
        self.assertIn("Proposte in staging",markdown(report))
        with self.assertRaisesRegex(ValueError,"Staging requires"):
            run(CFG,catalog(),stage_raw=True)

    def test_raw_market_names_or_vendor_sensitive_fields_never_persist(self):
        blob=csv_blob()
        report=inspect_raw(RAW,blob,catalog())
        text=json.dumps(report,ensure_ascii=False)
        self.assertNotIn("MERCATO DI CORCIANO",text)
        self.assertNotIn("Via delle Fonti",text)
        self.assertEqual(len(report["fingerprints"]),4)
        self.assertEqual(report["counts"]["rows_observed"],4)
        self.assertNotEqual(digest(report),"")

if __name__=="__main__":
    unittest.main()
