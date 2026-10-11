import json
import tempfile
import unittest
from argparse import Namespace
from datetime import date
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from autopilot import (
    compare_candidates, prune_old_assets, retrieve_sources, run,
)
from export_static import export


TODAY = date(2026, 10, 11)


def market(slug, recurrence="settimanale - sabato"):
    return {
        "slug": slug,
        "nome": "Mercato settimanale di Firenze",
        "citta": "Firenze", "regione": "Toscana", "provincia": "FI",
        "categoria": "misto", "indirizzo": "Piazza I Maggio",
        "date": ["2026-10-17", "2026-10-24"],
        "date_quality": "prevista", "ricorrenza_testo": recurrence,
        "status": "non_confermato", "aggiornato_il": "2026-02-11",
        "url_fonte": "https://example.org/markets/firenze",
        "fonte": "public fixture",
    }


def policy():
    return {
        "schema": 1, "sources": [{
            "id":"milano", "enabled":True,"official":True,
            "min_records":1, "max_records":1000,"license":"CC BY 4.0"
        }],
        "forecast": {"days":120,"max_source_age_days":540,
                     "min_records_with_future_date_at_plus_60_days":1},
        "gates": {
            "min_total_records": 1, "max_record_loss_fraction": 0.03,
            "min_id_retention_fraction": 0.99, "max_new_ids_per_run": 10,
            "max_gzip_index_bytes": 800000, "max_index_growth_fraction": 10,
            "max_unknown_source_share_increase": 0.01,
            "allow_new_confident_date_claims": False,
            "allow_new_human_verified_claims": False,
        },
        "publication": {
            "channel":"dev-only","production_merge":False,
            "require_security_audit":True,"require_mobile_smoke":True,
        }
    }


class AutopilotTests(unittest.TestCase):
    def test_offline_end_to_end_does_not_change_original(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            base = folder / "public" / "data" / "v1"
            export([market("fi-saturday"), market("fi-saturday-2")], base,
                   today=TODAY)
            original_manifest = (base / "manifest.json").read_bytes()
            out = folder / "candidate"
            config = folder / "policy.json"
            config.write_text(json.dumps(policy()))
            args = Namespace(manifest=base / "manifest.json", policy=config,
                             output=out,today=TODAY,offline=True,resume=False)
            findings = run(args)
            self.assertTrue(findings["approved"])
            self.assertTrue(findings["has_changes"])
            self.assertGreater(findings["candidate"]["future_60"], 0)
            self.assertEqual((base/"manifest.json").read_bytes(),original_manifest)
            self.assertTrue((out/"candidate"/"public"/"data"/"v1"/"manifest.json").exists())
            self.assertEqual(findings["added_source_ids"],0)
            self.assertEqual(findings["removed_source_ids"],0)
            for phase in ("baseline","sources","merge","forecast","export","quality"):
                self.assertTrue((out/"checkpoints"/(phase+".json")).is_file())
            self.assertFalse(findings["published"])

    def test_resume_reuses_checkpoint_without_touching_network(self):
        with tempfile.TemporaryDirectory() as td:
            folder=Path(td)
            base=folder/"public"/"data"/"v1"
            export([market("fi-a")],base,today=TODAY)
            config=folder/"policy.json"
            config.write_text(json.dumps(policy()))
            args=Namespace(manifest=base/"manifest.json", policy=config,
                           output=folder/"job",today=TODAY,offline=True,resume=False)
            run(args)
            args.resume=True
            found=run(args)
            self.assertTrue(found["approved"])

    def test_never_promote_unverified_to_confirmed(self):
        previous={"slug":"a", "date_quality":"prevista",
                  "date":["2026-10-17"],"verificato_il":"",
                  "url_fonte":"https://example.org"}
        current={**previous,"date_quality":"confermata"}
        old={"snapshot_total":1,"compact_index_future_coverage":{"60":0,"90":0},
             "sizes":{"national_index_gzip_bytes":300},"fields_missing":{},
             "documented_verified_records":0,"position_quality":{}}
        newer={**old,"compact_index_future_coverage":{"60":5,"90":1}}
        config=policy()
        config["forecast"]["min_records_with_future_date_at_plus_60_days"]=1
        verdict=compare_candidates([previous],[current],old,newer,config,
                                   {"all_dates_marked_forecast":True},{})
        self.assertFalse(verdict["approved"])
        self.assertFalse(verdict["gates"]["never_upgrade_estimates_to_confirmed"])

    def test_losing_source_evidence_blocks_release(self):
        prev={"slug":"a","url_fonte":"https://example.org/old",
              "date_quality":"prevista","verificato_il":""}
        newer={**prev, "url_fonte":"https://other.org/new", "fonti":[]}
        report={"snapshot_total":1,"compact_index_future_coverage":{"60":10,"90":5},
                "sizes":{"national_index_gzip_bytes":300},"fields_missing":{},
                "documented_verified_records":0,"position_quality":{}}
        verdict=compare_candidates([prev],[newer],report,report,policy(),
                                   {"all_dates_marked_forecast":True},{})
        self.assertFalse(verdict["gates"]["retain_old_source_evidence"])

    def test_unapproved_source_ids_fail_closed(self):
        bad=policy()
        bad["sources"]=[{"id":"random-internet", "enabled":True,"official":True}]
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaisesRegex(ValueError,"Unapproved source"):
                retrieve_sources(bad,Path(td),TODAY,offline=True,resume=False)

    def test_pruning_preserves_previous_immutable_assets(self):
        with tempfile.TemporaryDirectory() as td:
            root=Path(td)/"public"
            folder=root/"data"/"v1"
            folder.mkdir(parents=True)
            (folder/"old-index.json").write_text("{}")
            (folder/"new-index.json").write_text("{}")
            (folder/"unreferenced.json").write_text("{}")
            old={"index":"data/v1/old-index.json"}
            new={"index":"data/v1/new-index.json"}
            removed=prune_old_assets(folder,old,new)
            self.assertEqual(removed,1)
            self.assertTrue((folder/"old-index.json").exists())
            self.assertTrue((folder/"new-index.json").exists())
            self.assertFalse((folder/"unreferenced.json").exists())



    def test_added_verified_or_confirmed_market_is_quarantined(self):
        old = market("existing")
        new = market("new")
        new["date_quality"] = "confermata"
        new["verificato_il"] = "2026-10-12"
        base_report = {
            "snapshot_total": 1,
            "compact_index_future_coverage": {"60": 2, "90": 2},
            "sizes": {"national_index_gzip_bytes": 300},
            "fields_missing": {"source_url": 0},
            "documented_verified_records": 0,
            "position_quality": {},
        }
        new_report = {**base_report, "snapshot_total": 2}
        verdict = compare_candidates([old], [old, new], base_report, new_report,
                                     policy(), {"all_dates_marked_forecast": True},
                                     {"milano": {"status": "retrieved"}})
        self.assertFalse(verdict["approved"])
        self.assertFalse(verdict["gates"]["no_unreviewed_new_confirmations"])
        self.assertFalse(verdict["gates"]["no_unreviewed_new_verifications"])
        self.assertEqual(verdict["new_unreviewed_confirmations"], ["new"])

    def test_failed_official_source_blocks_unattended_release(self):
        row = market("existing")
        report = {
            "snapshot_total": 1,
            "compact_index_future_coverage": {"60": 2, "90": 2},
            "sizes": {"national_index_gzip_bytes": 300},
            "fields_missing": {"source_url": 0},
            "documented_verified_records": 0,
            "position_quality": {},
        }
        verdict = compare_candidates([row], [row], report, report, policy(),
                                     {"all_dates_marked_forecast": True},
                                     {"milano": {"status": "unavailable", "error": "HTTP 503"}})
        self.assertFalse(verdict["approved"])
        self.assertFalse(verdict["gates"]["official_sources_available"])

    def test_source_evidence_and_city_cannot_regress_unnoticed(self):
        old = market("existing")
        changed = {**old, "citta": "Pisa", "url_fonte": "",
                   "fonti": [{"url": old["url_fonte"]}]}
        report = {
            "snapshot_total": 1,
            "compact_index_future_coverage": {"60": 2, "90": 2},
            "sizes": {"national_index_gzip_bytes": 300},
            "fields_missing": {"source_url": 0},
            "documented_verified_records": 0,
            "position_quality": {},
        }
        new_report = {**report, "fields_missing": {"source_url": 1}}
        verdict = compare_candidates([old], [changed], report, new_report,
                                     policy(), {"all_dates_marked_forecast": True}, {})
        self.assertFalse(verdict["approved"])
        self.assertFalse(verdict["gates"]["source_identities_immutable"])
        self.assertFalse(verdict["gates"]["unknown_source_share_budget"])
        self.assertEqual(verdict["changed_market_identities"], ["existing"])

    def test_resume_requires_identical_reference_date(self):
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td)
            base = folder / "public" / "data" / "v1"
            export([market("fi-a")], base, today=TODAY)
            config = folder / "policy.json"
            config.write_text(json.dumps(policy()))
            args = Namespace(manifest=base / "manifest.json", policy=config,
                             output=folder / "job", today=TODAY,
                             offline=True, resume=False)
            run(args)
            args.today = date(2026, 10, 12)
            args.resume = True
            with self.assertRaisesRegex(ValueError, "reference date changed"):
                run(args)

if __name__ == "__main__":
    unittest.main()
