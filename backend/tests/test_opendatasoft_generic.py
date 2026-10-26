"""Generic Opendatasoft source contract: fixture-only, no network in CI."""
import copy
import hashlib
import json
import sys
import unittest
from datetime import date
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from source_lifecycle import validate_contracts,parse_rows,candidate_record,digest
from source_contract_ingest import stage,venue_row
from source_contract_activation import activate,validate_release
from publisher_snapshot_date import make_snapshot_date_proof

CONFIG=json.loads((ROOT/"data/market-source-contracts.json").read_text("utf8"))
REGISTRY=json.loads((ROOT/"data/approved-source-admissions.json").read_text("utf8"))
BO=next(p for p in CONFIG["raw_profiles"] if p["id"]=="bologna-generic-venues")
DAY=date(2026,10,13)


def fixture_profile():
    p=copy.deepcopy(BO)
    p.update(min_rows=10,max_rows=30)
    return p


def fixture():
    rows=[]
    for n in range(12):
        agri=(n%3==0)
        fields={
          "denominazione":f"MERCATO SEDE {n}",
          "ubicazione":f"Via Dimostrativa {n}",
          "tipologia":"mercato produttori agricoli" if agri else "mercato",
          "giorni_svolgimento":"Martedì" if n%2 else "Lunedì-sabato",
          "orario_svolgimento":"07:30-13:00" if n%2 else "Estivo: 18:00-20:00",
        }
        if not agri: fields["tipologia_mercato"]="periodico"
        rows.append(fields)
    # Same named market, same address on different days: hold BOTH.
    for day in ("Venerdì","Sabato"):
        rows.append({"denominazione":"MERCATO A TURNI","ubicazione":"Piazza Turni",
                     "tipologia":"mercato","tipologia_mercato":"periodico",
                     "giorni_svolgimento":day,"orario_svolgimento":"08:00-13:00"})
    # Same display identity, two categories: no automatic collapse or duplicate.
    rows += [
      {"denominazione":"PIAZZA CONDIVISA","ubicazione":"Piazza Condivisa",
       "tipologia":"mercato","tipologia_mercato":"rionale",
       "giorni_svolgimento":"Lunedì-sabato"},
      {"denominazione":"PIAZZA CONDIVISA","ubicazione":"Piazza Condivisa",
       "tipologia":"mercato produttori agricoli","giorni_svolgimento":"Domenica"},
      {"denominazione":"TEMPORANEO","ubicazione":"Piazza Nuova (trasferimento temporaneo)",
       "tipologia":"mercato","tipologia_mercato":"periodico",
       "giorni_svolgimento":"Martedì"},
      {"denominazione":"POSTEGGIO SOLITARIO","ubicazione":"Via Dimostrativa Extra",
       "tipologia":"mercato","tipologia_mercato":"a turno giornaliero",
       "giorni_svolgimento":"Martedì"},
      {"denominazione":"FIERA","ubicazione":"Via Fiera",
       "tipologia":"fiera","giorni_svolgimento":"Domenica"},
    ]
    official=[]
    for idx,fields in enumerate(rows):
        official.append({"datasetid":"mercati-e-fiere",
                         "recordid":hashlib.sha1(f"item-{idx}".encode()).hexdigest(),
                         "fields":fields})
    return official


def blob(items=None,total=None):
    items=fixture() if items is None else items
    return json.dumps({"nhits":len(items) if total is None else total,
                       "records":items},ensure_ascii=False,separators=(",",":")).encode("utf8")


def metadata_blob():
    # Synthetic publisher metadata; the current portal date cannot replace
    # the older dataset date used by these parser/identity fixtures.
    return json.dumps({"dataset_id":"mercati-e-fiere", "metas":{"default":{
        "license":"CC BY 4.0", "records_count":249,
        "modified_updates_on_data_change":False,
        "data_processed":"2025-04-02T06:00:00Z",
        "metadata_processed":"2026-10-13T06:00:00Z",
    }}}).encode()


def fixture_date_proof(profile,body):
    return make_snapshot_date_proof(profile,body,before_metadata=metadata_blob(),
        after_metadata=metadata_blob(),read_on=DAY.isoformat(),today=DAY)


def config_and_registry(profile=None,quota=5):
    profile=copy.deepcopy(profile or fixture_profile())
    config=copy.deepcopy(CONFIG)
    config["raw_profiles"]=[profile]
    approval=copy.deepcopy(next(x for x in REGISTRY["approvals"]
                               if x["source_id"]=="bologna-generic-venues"))
    approval["reviewed_profile_sha256"]=digest(profile)
    approval["max_new_ids"]=quota
    approval["reviewed_on"]=DAY.isoformat()
    registry=copy.deepcopy(REGISTRY)
    registry["approvals"]=[approval]
    return config,registry


def generic_baseline():
    return [{"slug":"generic-city","citta":"Bologna","regione":"Emilia-Romagna",
             "nome":"Mercato settimanale di Bologna","indirizzo":"",
             "ricorrenza_testo":"","status":"non_confermato"}]


class OpendatasoftReusableSourceTests(unittest.TestCase):
    def test_source_registry_enables_exactly_four_reviewed_publishers(self):
        self.assertTrue(validate_contracts(CONFIG))
        self.assertEqual(len(REGISTRY["approvals"]),4)
        self.assertEqual(BO["catalog_slug_prefix"],"bo-open-")
        self.assertEqual(BO["max_forecast_source_age_days"],365)
        self.assertEqual(BO["source_dataset_date"],"2025-04-02")

    def test_nested_json_projection_retains_sha1_source_ids_without_personal_fields(self):
        parsed=parse_rows(fixture_profile(),blob())
        self.assertEqual(len(parsed),19)
        self.assertEqual(len({x["recordid"] for x in parsed}),19)
        self.assertTrue(all(set(x)==set(BO["schema_columns"]) for x in parsed))
        self.assertTrue(all("datasetid" not in x and "geometry" not in x for x in parsed))
        self.assertIsNone(parsed[0]["tipologia_mercato"])

    def test_json_count_identity_and_dataset_change_all_fail_closed(self):
        p=fixture_profile()
        with self.assertRaisesRegex(ValueError,"Incomplete Opendatasoft"):
            parse_rows(p,blob(total=999))
        corrupt=fixture()
        corrupt[1]["recordid"]="not-a-hash"
        with self.assertRaisesRegex(ValueError,"stable record identity"):
            parse_rows(p,blob(corrupt))
        corrupt=fixture()
        corrupt[1]["datasetid"]="other-dataset"
        with self.assertRaisesRegex(ValueError,"stable record identity"):
            parse_rows(p,blob(corrupt))
        corrupt=fixture()
        corrupt[0]["fields"]["unreviewed_operator_personal_details"]="secret"
        with self.assertRaisesRegex(ValueError,"Unexpected Opendatasoft"):
            parse_rows(p,blob(corrupt))

    def test_venue_age_does_not_become_2026_opening_forecast(self):
        p=fixture_profile()
        row=parse_rows(p,blob())[1]
        parsed,_,_=candidate_record(p,row,today=DAY)
        self.assertEqual(parsed["aggiornato_il"],"2025-04-02")
        self.assertEqual(parsed["date"],[])
        self.assertEqual(parsed["status"],"non_confermato")
        self.assertEqual(parsed["ricorrenza_testo"],"Calendario da verificare")
        self.assertEqual(parsed["orario_testo"],"07:30–13:00 (da verificare con il Comune)")
        self.assertIsNone(parsed["lat"])
        self.assertIsNone(parsed["lng"])
        agricultural=parse_rows(p,blob())[0]
        av,_,_=venue_row(p,agricultural,DAY)
        self.assertEqual(av["categoria"],"alimentare")
        self.assertTrue(av["nome"].startswith("Mercato "))

    def test_declared_filter_keeps_only_real_market_and_quarantines_stalls(self):
        p=fixture_profile()
        baseline=generic_baseline()
        out,report=stage(p,blob(),baseline,today=DAY,source_date_proof=fixture_date_proof(p,blob()))
        self.assertEqual(len(out),12)
        holds=report["review_reason_counts"]
        self.assertEqual(holds["not_a_market_venue"],2)
        self.assertEqual(holds["repeated_venue_rows_require_grouping"],2)
        self.assertEqual(holds["same_place_name_multiple_source_rows"],2)
        self.assertEqual(holds["temporary_location_unreconciled"],1)
        self.assertTrue(all(x["status"]=="non_confermato" and x["date"]==[]
                            and x["lat"] is None for x in out))
        self.assertTrue(report["counts"]["publisher_distinct_address_count"]>=10)

    def test_no_override_when_source_cannot_prove_ten_distinct_addresses(self):
        p=fixture_profile()
        p["generic_city_aggregate_min_distinct_addresses"]=10
        small=fixture()[:10]
        small[9]["fields"]["ubicazione"]="Via Dimostrativa 8"
        p["min_rows"]=1
        proposed,report=stage(p,blob(small),generic_baseline(),today=DAY,
                             source_date_proof=fixture_date_proof(p,blob(small)))
        self.assertEqual(proposed,[])
        self.assertEqual(report["review_reason_counts"]["generic_city_market_day"],10)

    def test_bounded_deterministic_batches_and_offline_have_no_implicit_claims(self):
        cfg,registry=config_and_registry(quota=5)
        fetch=lambda url:(metadata_blob() if "/api/explore/" in url else blob(),False)
        source=generic_baseline()
        added=[]
        for expected in (5,5,2,0):
            result,report=activate(cfg,registry,source,today=DAY,fetch=fetch,read_on=DAY)
            self.assertEqual(len(result)-len(source),expected)
            self.assertEqual(len(report["new_market_ids"]),expected)
            self.assertTrue(validate_release(source,result,report,cfg,registry)["release_safe"])
            added.extend(report["new_market_ids"])
            source=result
        self.assertEqual(len(added),12)
        self.assertEqual(len(set(added)),12)
        offline,off=activate(cfg,registry,source,today=DAY,offline=True,
                             fetch=lambda url:(_ for _ in ()).throw(AssertionError()))
        self.assertEqual(offline,source)
        self.assertEqual(off["new_market_ids"],[])

    def test_autopilot_rejects_registry_or_contract_sha_tampering(self):
        import argparse
        import tempfile
        from autopilot import run
        policy=json.loads((ROOT/"autopilot_policy.json").read_text("utf8"))
        for key, sha_key, message in (
                ("source_contract_admissions","approved_registry_blob_sha1",
                 "Unapproved generically admitted municipal source policy"),
                ("source_lifecycle","reviewed_contract_blob_sha1",
                 "Unreviewed reusable source contract schema")):
            edited=copy.deepcopy(policy)
            edited[key][sha_key]="0"*40
            with tempfile.TemporaryDirectory() as temp:
                path=Path(temp)/"policy.json"
                path.write_text(json.dumps(edited),encoding="utf8")
                args=argparse.Namespace(
                    manifest=ROOT.parents[0]/"public/data/v1/manifest.json",
                    policy=path,output=Path(temp)/"output",
                    today=DAY,offline=True,resume=False)
                with self.subTest(key=key),self.assertRaisesRegex(ValueError,message):
                    run(args)

    def test_approval_does_not_accept_unreviewed_contract_rewrite(self):
        profile=fixture_profile()
        changes=[
            ("max_forecast_source_age_days",731),
            ("json_container","not_verified"),
            ("api_dataset_id","unrelated"),
            ("market_filters_any",[{"unknown_field":"rionale"}]),
            ("generic_city_aggregate_min_distinct_addresses",1),
            ("hold_address_contains",[""]),
            ("venue_identity_fields",["unknown_field"]),
            ("hours_text_field","private_field"),
        ]
        for name,bad in changes:
            p=copy.deepcopy(profile)
            p[name]=bad
            cfg,_=config_and_registry(p)
            with self.subTest(name=name),self.assertRaises(ValueError):
                validate_contracts(cfg)
        cfg,registry=config_and_registry()
        profile=cfg["raw_profiles"][0]
        profile["max_new_ids_per_run"]=250
        # An otherwise valid profile rewrite invalidates its certificate and
        # must fail before any source read or catalog mutation.
        self.assertTrue(validate_contracts(cfg))
        baseline=generic_baseline()
        frozen=copy.deepcopy(baseline)
        fetch_calls=[]

        def forbidden_fetch(url):
            fetch_calls.append(url)
            self.fail("Unapproved profile must be rejected before source fetch")

        with self.assertRaisesRegex(
                ValueError,"Source approval does not match the exact enabled/disabled profile"):
            activate(cfg,registry,baseline,today=DAY,read_on=DAY,fetch=forbidden_fetch)
        self.assertEqual(fetch_calls,[])
        self.assertEqual(baseline,frozen)

if __name__=="__main__":
    unittest.main()
