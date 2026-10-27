"""One real publisher CSV, reusable staging, strict whole-source DEV admission."""
import copy
import json
import sys
import unittest
from datetime import date,timedelta
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_source_corciano import DATA
from source_corciano import parse_csv as old_csv, convert as old_convert
from source_lifecycle import parse_rows, digest, canonical
from source_contract_ingest import (
    validate_format, venue_row, stage, authorize, apply_approved,
    PublishedSourceDriftError,
)

PROFILE=json.loads((Path(__file__).resolve().parents[1]/
                    "data/market-source-contracts.json").read_text("utf-8"))["raw_profiles"][0]
TODAY=date(2026,10,13)
BLOB=DATA.encode("utf-8")


def _approved_profile():
    a=copy.deepcopy(PROFILE)
    a["publication_mode"]="approved_dev_only"
    a["legal_reuse_reviewed"]=True
    a["max_new_ids_per_run"]=4
    return a


def _approval(profile,date_="2026-10-13"):
    return {
      "schema":1,"mode":"approved_dev_only","source_id":profile["id"],
      "reviewed_profile_sha256":digest(profile),
      "publisher_license_evidence_url":profile["attribution_url"],
      "identity_granularity":profile["row_kind"],"reviewed_on":date_,
      "max_new_ids":4,"source_record_kind":"market_venue",
      "source_specific_geo_approval":False,
    }


def baseline():
    official=old_convert(old_csv(BLOB),TODAY)
    keep=[r for r in official if r["slug"] in (
        "pg-corciano-mercato-di-mantignana",
        "pg-corciano-mercato-di-san-mariano")]
    # Existing third-party listings, not proven distinct official venues.
    listings=[
      {"slug":"mercato-settimanale-di-corciano-corciano-mercoledi",
       "nome":"Mercato settimanale di Corciano",
       "citta":"Corciano","regione":"Umbria",
       "indirizzo":"Piazza Caduti","date":[],"ricorrenza_testo":"settimanale - mercoledì"},
      {"slug":"mercato-settimanale-a-corciano-corciano-venerdi",
       "nome":"Mercato settimanale a Corciano",
       "citta":"Corciano","regione":"Umbria",
       "indirizzo":"","date":[],"ricorrenza_testo":"settimanale - venerdì"},
    ]
    return keep+listings


def same_identity(expected,converted):
    # Coordinates are separately governed; NEVER use them for admission.
    for key in ("slug","nome","citta","regione","provincia",
                "indirizzo","orario_testo","ricorrenza_testo",
                "aggiornato_il","aggiornamento_ambito","status"):
        if canonical(expected.get(key))!=canonical(converted.get(key)):
            return False,key,expected.get(key),converted.get(key)
    return True,None,None,None


class GenericMunicipalContractTests(unittest.TestCase):
    def test_exact_four_real_venues_share_legacy_identity_address_hours_days(self):
        original=old_convert(old_csv(BLOB),TODAY)
        raw=parse_rows(PROFILE,BLOB)
        shadow=[]
        for source in raw:
            row,why,_=venue_row(PROFILE,source,TODAY)
            self.assertIsNotNone(row)
            self.assertIsNone(why)
            shadow.append(row)
        self.assertEqual(len(shadow),4)
        old_by={x["slug"]:x for x in original}
        self.assertEqual(set(old_by),{x["slug"] for x in shadow})
        for row in shadow:
            identical,field,left,right=same_identity(old_by[row["slug"]],row)
            self.assertTrue(identical,f"{row['slug']} {field}: {left!r} != {right!r}")
            self.assertEqual(row["date"],[])
            self.assertEqual(row["date_quality"],"sconosciuta")
            self.assertEqual(row["position_quality"],"sconosciuta")
            self.assertIsNone(row["lat"])
            self.assertIsNone(row["lng"])
            self.assertFalse(row["verificato_il"])
            self.assertEqual(row["navigazione_sospesa_motivo"],
                             "indirizzo_e_punto_sorgente_non_riconciliati")

    def test_baseline_identifies_two_exact_existing_two_legacy_collisions(self):
        old=baseline()
        frozen=copy.deepcopy(old)
        created,report=stage(PROFILE,BLOB,old,today=TODAY)
        self.assertEqual(created,[])
        self.assertEqual(old,frozen)
        self.assertEqual(report["counts"]["raw_rows_scanned"],4)
        self.assertEqual(report["counts"]["already_in_catalog_exact_source_id"],2)
        self.assertEqual(report["counts"]["source_market_identities"],4)
        self.assertEqual(report["safe_candidates_not_published"],0)
        self.assertEqual(sum(report["review_reason_counts"].values()),2)
        self.assertEqual(report["verified_openings_created"],0)
        self.assertEqual(report["existing_market_identities_deleted"],0)

    def test_no_disguised_market_event_or_source_stall_personal_data_in_report(self):
        proposals,report=stage(PROFILE,BLOB,baseline(),today=TODAY)
        text=json.dumps(report,ensure_ascii=False)
        self.assertNotIn("MERCATO DI MANTIGNANA",text)
        self.assertNotIn("CADUTI",text)
        self.assertNotIn("ALDO MORO",text)
        self.assertNotIn("geopoint",text.lower())
        self.assertTrue(all("source_identity_sha256" in x for x in report["examples_hashed"]))
        self.assertEqual(report["source_license_automatically_verified"],False)
        self.assertFalse(report["publication_enabled"])

    def test_new_distinct_venue_can_be_staged_but_not_published_implicitly(self):
        old=[{"slug":"legacy-elsewhere","nome":"Mercato a Firenze",
              "citta":"Firenze","regione":"Toscana","indirizzo":"Via Roma",
              "ricorrenza_testo":"settimanale - venerdì"}]
        preview,report=stage(PROFILE,BLOB,old,today=TODAY)
        self.assertEqual(len(preview),4)
        self.assertEqual(report["safe_candidates_not_published"],4)
        self.assertEqual(len(old),1)
        self.assertTrue(all(not x["verificato_il"] and x["lat"] is None for x in preview))
        with self.assertRaisesRegex(ValueError,"no reviewed DEV admission"):
            apply_approved(PROFILE,BLOB,old,None,today=TODAY)
        unapproved=copy.deepcopy(PROFILE)
        unapproved["publication_mode"]="shadow_only"
        unapproved["legal_reuse_reviewed"]=False
        unapproved["max_new_ids_per_run"]=0
        with self.assertRaisesRegex(ValueError,"licensed, pinned DEV"):
            apply_approved(unapproved,BLOB,old,_approval(unapproved),today=TODAY)

    def test_source_level_admission_guard_has_a_valid_synthetic_positive_case(self):
        # This is a fixture only: no real contract/certificate is enabled.
        profile=_approved_profile()
        src=[{"slug":"legacy-elsewhere","citta":"Firenze","regione":"Toscana",
              "nome":"Mercato a Firenze","indirizzo":"Via Roma"}]
        unmodified=copy.deepcopy(src)
        result,guard=apply_approved(profile,BLOB,src,_approval(profile),today=TODAY)
        self.assertEqual(src,unmodified)
        self.assertEqual(len(result),5)
        self.assertEqual(len(guard["new_venue_ids"]),4)
        self.assertEqual(guard["old_ids_modified"],0)
        self.assertEqual(guard["old_ids_removed"],0)
        self.assertEqual(guard["verified_events_created"],0)
        self.assertEqual(guard["geocoordinates_created"],0)
        self.assertTrue(guard["dev_only"])
        self.assertEqual(result[0],src[0])
        self.assertEqual(len(set(x["slug"] for x in result)),5)
        # Repeated scheduled runs are idempotent and add none.
        again,replay=apply_approved(profile,BLOB,result,_approval(profile),today=TODAY)
        self.assertEqual(again,result)
        self.assertEqual(replay["new_venue_ids"],[])

    def test_approved_source_is_admitted_in_ordered_daily_batches_not_blocked(self):
        profile=_approved_profile()
        certificate=_approval(profile)
        certificate["max_new_ids"]=2
        old=[{"slug":"legacy-elsewhere","nome":"Mercato a Firenze",
              "citta":"Firenze","regione":"Toscana","indirizzo":"Via Roma"}]
        shuffled=BLOB.decode("utf-8").splitlines()
        reversed_source=("\n".join([shuffled[0],*reversed(shuffled[1:])])+"\n").encode("utf-8")
        first,first_proof=apply_approved(profile,BLOB,old,certificate,today=TODAY)
        reverse,reverse_proof=apply_approved(
            profile,reversed_source,old,certificate,today=TODAY)
        self.assertEqual(first,reverse)
        self.assertEqual(first_proof["new_venue_ids"],reverse_proof["new_venue_ids"])
        self.assertEqual(len(first_proof["new_venue_ids"]),2)
        self.assertEqual(first_proof["source_eligible_candidates"],4)
        self.assertEqual(first_proof["deferred_candidate_count"],2)
        self.assertEqual(len(first_proof["deferred_candidate_ids_sha256"]),64)
        second,second_proof=apply_approved(profile,BLOB,first,certificate,today=TODAY)
        self.assertEqual(len(second),5)
        self.assertEqual(second_proof["deferred_candidate_count"],0)
        self.assertEqual(set(first_proof["new_venue_ids"]) &
                         set(second_proof["new_venue_ids"]),set())
        third,third_proof=apply_approved(profile,BLOB,second,certificate,today=TODAY)
        self.assertEqual(third,second)
        self.assertEqual(third_proof["new_venue_ids"],[])

    def test_unknown_venue_with_same_place_weekday_is_quarantined(self):
        src=[{"slug":"old-third-party-market","citta":"Corciano","regione":"Umbria",
              "indirizzo":"Piazza Giovanni Ercolani, Mantignana",
              "nome":"Mercato qualsiasi","ricorrenza_testo":"settimanale - lunedì"}]
        rows,report=stage(PROFILE,BLOB,src,today=TODAY)
        self.assertEqual(len(rows),3)
        self.assertEqual(report["review_reason_counts"]["venue_at_same_street_day"],1)
        self.assertFalse(any(x["slug"]=="pg-corciano-mercato-di-mantignana" for x in rows))

    def test_source_duplicate_identity_withheld_completely(self):
        input_=BLOB.decode("utf-8").splitlines(keepends=True)
        # Duplicate only the name/identity; source still has four rows.
        input_[-1]=input_[-1].replace("MERCATO DI ELLERA","MERCATO DI MANTIGNANA")
        csv_="".join(input_).encode()
        created,report=stage(
            PROFILE,csv_,
            [{"slug":"other","citta":"Firenze","regione":"Toscana"}],
            today=TODAY
        )
        self.assertEqual(report["review_reason_counts"]["duplicate_publisher_identity"],2)
        self.assertNotIn("pg-corciano-mercato-di-mantignana",{x["slug"] for x in created})
        self.assertEqual(len(created),2)

    def test_existing_publisher_fact_changes_block_remaining_batch(self):
        profile=_approved_profile()
        cert=_approval(profile)
        cert["max_new_ids"]=2
        old=[{"slug":"legacy-elsewhere","nome":"Mercato a Firenze",
              "citta":"Firenze","regione":"Toscana","indirizzo":"Via Roma"}]
        first,proof=apply_approved(profile,BLOB,old,cert,today=TODAY)
        self.assertEqual(proof["deferred_candidate_count"],2)
        changes=(
            ("nome","Nome completamente diverso","source_identity_changed"),
            ("indirizzo","Via inventata 100","source_address_changed"),
            ("ricorrenza_testo","settimanale - domenica","source_calendar_changed"),
            ("orario_testo","22:00 - 23:00","source_hours_changed"),
        )
        for field,replacement,reason in changes:
            with self.subTest(field=field):
                changed=copy.deepcopy(first)
                changed[1][field]=replacement
                frozen=copy.deepcopy(changed)
                preview,source_report=stage(profile,BLOB,changed,today=TODAY)
                self.assertEqual(len(preview),2)
                self.assertEqual(source_report["review_reason_counts"][reason],1)
                with self.assertRaisesRegex(
                        PublishedSourceDriftError,"review source"):
                    apply_approved(profile,BLOB,changed,cert,today=TODAY)
                self.assertEqual(changed,frozen)

    def test_two_cycles_update_only_three_previously_managed_source_fields(self):
        from field_evidence import field_states
        profile=_approved_profile()
        old=[{"slug":"elsewhere","citta":"Firenze","regione":"Toscana"}]
        first,_=apply_approved(profile,BLOB,old,_approval(profile),today=TODAY)
        frozen=copy.deepcopy(first)
        changed=BLOB.replace(
            b"MERCATO DI CORCIANO;MERCOLEDI;PIAZZA;CADUTI;3;1;07:30;14:00;",
            b"MERCATO DI CORCIANO;GIOVEDI;PIAZZA;NUOVA SEDE;3;1;08:00;13:00;")
        self.assertNotEqual(changed,BLOB)
        next_day=TODAY+timedelta(days=1)
        result,proof=apply_approved(profile,changed,first,_approval(profile),today=next_day)
        self.assertEqual(first,frozen)
        self.assertEqual([r["slug"] for r in result],[r["slug"] for r in first])
        self.assertEqual(proof["old_fields_modified"],3)
        self.assertEqual(proof["new_venue_ids"],[])
        updated=next(r for r in result if r["slug"]=="pg-corciano-mercato-di-corciano")
        self.assertEqual(updated["indirizzo"],"Piazza Nuova Sede, Corciano")
        self.assertEqual(updated["ricorrenza_testo"],"settimanale - giovedi")
        self.assertEqual(updated["orario_testo"],"08:00–13:00 (da verificare con il Comune)")
        self.assertEqual(updated["fonte_letta_il"],next_day.isoformat())
        self.assertEqual(updated["fonte_aggiornata_il"],"2026-01-07")
        self.assertFalse(updated["verificato_il"])
        self.assertEqual(updated["date"],[])
        self.assertEqual(updated["riscontri_campi"][0]["campi_gestiti"],
                         ["indirizzo","orario_testo","ricorrenza_testo"])
        self.assertTrue(updated["riscontri_campi"][0]["versioni_precedenti"])
        # A newly read old dataset is still old for hours/day freshness.
        self.assertEqual(field_states(updated,today=next_day)["orario_testo"],"riscontro_da_aggiornare")
        again,replay=apply_approved(profile,changed,result,_approval(profile),today=next_day)
        self.assertEqual(again,result)
        self.assertEqual(replay["old_ids_modified"],0)

    def test_identical_legacy_read_adds_evidence_without_claiming_field_ownership(self):
        profile=_approved_profile()
        legacy=old_convert(old_csv(BLOB),TODAY)
        result,proof=apply_approved(profile,BLOB,legacy,_approval(profile),today=TODAY)
        self.assertEqual(proof["old_fields_modified"],0)
        for before,after in zip(legacy,result):
            self.assertEqual({k:v for k,v in after.items()
                              if k not in {"riscontri_campi","fonte_letta_il","fonte_aggiornata_il"}},before)
            self.assertNotIn("campi_gestiti",after["riscontri_campi"][0])
        changed=BLOB.replace(b";CADUTI;",b";NUOVA SEDE;")
        with self.assertRaises(PublishedSourceDriftError):
            apply_approved(profile,changed,result,_approval(profile),today=TODAY+timedelta(days=1))

    def test_source_changed_on_same_day_cannot_establish_receipt_order(self):
        profile=_approved_profile()
        first,_=apply_approved(profile,BLOB,[{"slug":"other"}],_approval(profile),today=TODAY)
        with self.assertRaises(PublishedSourceDriftError):
            apply_approved(profile,BLOB.replace(b";CADUTI;",b";NUOVA SEDE;"),
                           first,_approval(profile),today=TODAY)

    def test_name_id_or_geography_drift_keeps_original_catalog(self):
        profile=_approved_profile()
        first,_=apply_approved(profile,BLOB,[{"slug":"other"}],_approval(profile),today=TODAY)
        frozen=copy.deepcopy(first)
        blob=BLOB.replace(b"MERCATO DI CORCIANO;",b"MERCATO DI NUOVO;",1)
        _,report=stage(profile,blob,first,today=TODAY+timedelta(days=1))
        self.assertEqual(report["review_reason_counts"]["source_identity_missing_or_changed"],1)
        with self.assertRaises(PublishedSourceDriftError):
            apply_approved(profile,blob,first,_approval(profile),today=TODAY+timedelta(days=1))
        self.assertEqual(first,frozen)
        for field,value in (("nome","Altro Mercato"),("citta","Perugia"),("provincia","TR")):
            changed=copy.deepcopy(first)
            changed[1][field]=value
            with self.subTest(field=field),self.assertRaises(PublishedSourceDriftError):
                apply_approved(profile,BLOB,changed,_approval(profile),today=TODAY+timedelta(days=1))

    def test_owned_address_with_later_coordinates_requires_location_review(self):
        profile=_approved_profile()
        first,_=apply_approved(profile,BLOB,[{"slug":"other"}],_approval(profile),today=TODAY)
        target=next(r for r in first if r["slug"]=="pg-corciano-mercato-di-corciano")
        target.update({"lat":43.1,"lng":12.2,"position_quality":"precisa"})
        frozen=copy.deepcopy(first)
        with self.assertRaises(PublishedSourceDriftError):
            apply_approved(profile,BLOB.replace(b";CADUTI;",b";NUOVA SEDE;"),
                           first,_approval(profile),today=TODAY+timedelta(days=1))
        self.assertEqual(first,frozen)

    def test_our_own_street_pin_never_blocks_the_source_moving_the_market(self):
        profile=_approved_profile()
        first,_=apply_approved(profile,BLOB,[{"slug":"other"}],_approval(profile),today=TODAY)
        target=next(r for r in first if r["slug"]=="pg-corciano-mercato-di-corciano")
        # The position step looks the pin up again from the new street on the same run.
        target.update({"lat":43.1,"lng":12.2,"position_quality":"approssimata","posizione_fonte":{
            "fonte":"openstreetmap","licenza":"ODbL-1.0","attribuzione":"© OpenStreetMap contributors",
            "osm":"way/1","tipo":"highway/residential","trovato":"Via Caduti, Corciano",
            "chiave":"via caduti|corciano|PG","cercato_il":"2026-10-25","lat":43.1,"lng":12.2}})
        result,_=apply_approved(profile,BLOB.replace(b";CADUTI;",b";NUOVA SEDE;"),
                                first,_approval(profile),today=TODAY+timedelta(days=1))
        moved=next(r for r in result if r["slug"]=="pg-corciano-mercato-di-corciano")
        self.assertNotEqual(moved["indirizzo"],target["indirizzo"])

    def test_unknown_publisher_weekday_is_neither_evidence_nor_a_replacement(self):
        profile=_approved_profile()
        first,_=apply_approved(profile,BLOB,[{"slug":"other"}],_approval(profile),today=TODAY)
        changed=BLOB.replace(b";MERCOLEDI;",b";NON INDICATO;")
        result,report=apply_approved(profile,changed,first,_approval(profile),today=TODAY+timedelta(days=1))
        target=next(r for r in result if r["slug"]=="pg-corciano-mercato-di-corciano")
        self.assertEqual(target["ricorrenza_testo"],"settimanale - mercoledi")
        current=[r for r in target["riscontri_campi"] if r["letto_il"]==(TODAY+timedelta(days=1)).isoformat()]
        self.assertTrue(current)
        self.assertNotIn("ricorrenza_testo",current[0]["valori"])
        self.assertEqual(report["old_fields_modified"],0)

    def test_stale_source_and_unverified_licenses_cannot_create_dev_ids(self):
        a=_approved_profile()
        old=[{"slug":"other","citta":"Firenze","regione":"Toscana"}]
        cert=_approval(a)
        beyond=date(2026,1,7)+timedelta(days=541)
        with self.assertRaisesRegex(ValueError,"Stale publisher"):
            apply_approved(a,BLOB,old,cert,today=beyond)
        a["legal_reuse_reviewed"]=False
        with self.assertRaisesRegex(ValueError,"licensed, pinned"):
            apply_approved(a,BLOB,old,cert,today=TODAY)

    def test_forged_authorization_and_publisher_rights_domain_blocked(self):
        a=_approved_profile()
        old=[{"slug":"other","citta":"Firenze","regione":"Toscana"}]
        for field,value in (
          ("reviewed_profile_sha256","0"*64),
          ("publisher_license_evidence_url","https://evil.example/licenses"),
          ("publisher_license_evidence_url","https://evil@comune.corciano.pg.it/licence"),
          ("source_specific_geo_approval",True),
          ("max_new_ids",1000),
          ("reviewed_on","2027-01-01"),
        ):
            certificate=_approval(a)
            certificate[field]=value
            with self.subTest(field=field,value=value),self.assertRaises(ValueError):
                apply_approved(a,BLOB,old,certificate,today=TODAY)

    def test_source_rows_changed_after_admission_snapshot_are_rejected(self):
        baseline_=[{"slug":"other","citta":"Firenze","regione":"Toscana"}]
        _,report=stage(PROFILE,BLOB,baseline_,today=TODAY)
        altered=BLOB.replace(b";CADUTI;",b";PIAZZA NUOVA;")
        with self.assertRaisesRegex(ValueError,"modified after"):
            stage(PROFILE,altered,baseline_,today=TODAY,
                  observed_source_sha256=report["source_snapshot_sha256"])

    def test_parser_rejects_broken_columns_without_partial_import(self):
        bad=BLOB.replace(b";long;lat;geopoint",b";long;latitude;geopoint")
        with self.assertRaisesRegex(ValueError,"changed CSV columns"):
            stage(PROFILE,bad,baseline(),today=TODAY)

    def test_contract_presentation_has_bounded_source_level_mapping(self):
        x=copy.deepcopy(PROFILE)
        x["presentation"]["address_suffix_name_prefix"]="CITY:"
        venue,reason,_=venue_row(x,parse_rows(x,BLOB)[0],TODAY)
        self.assertIsNone(venue)
        self.assertEqual(reason,"invalid_source_row")
        for key,value in (("unknown_script","exec"),("title_case_address",[])):
            y=copy.deepcopy(PROFILE)
            y["presentation"][key]=value
            with self.assertRaises(ValueError):
                validate_format(y)


if __name__=="__main__":
    unittest.main()
