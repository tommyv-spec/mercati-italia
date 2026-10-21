"""National Happings checkpoint reconciliation is source scoped and read-only."""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from happings_full_reconciliation import analyze

ROOT="https://www.happings.com"
GO=ROOT+"/it/mercati-settimanali-a-gorizia-e-provincia/"
AL=ROOT+"/it/mercati-settimanali-a-alessandria-e-provincia/"


def market():
    return {"slug":"happings-gorizia","fonte":"happings.com","nome":"Mercato settimanale di Gorizia",
            "regione":"Friuli-Venezia Giulia","provincia":"GO","citta":"Gorizia",
            "indirizzo":"","ricorrenza_testo":"settimanale - mercoledì",
            "orario_testo":"","date":[],"date_quality":"sconosciuta"}


def snapshot(root, observations):
    page_dir=root/"pages"
    page_dir.mkdir(parents=True,exist_ok=True)
    seen={}
    for url, city, street, weekday in observations:
        is_go=url==GO
        row={"city":city,"weekday":weekday,"place":street,
             "calendar_scope":None,"editorial_scope":None,
             "has_specific_location":True,"daypart":"morning_not_clock_hours"}
        evidence={"url":url,"final_url":url,"status":"parsed","kind":"weekly",
                  "read_at":datetime.now(timezone.utc).isoformat(),
                  "bytes":800,"html_sha256":"a"*64,"source_rows":1,"markets":[row]}
        raw=gzip.compress((json.dumps(evidence,sort_keys=True)+"\n").encode("utf-8"))
        (page_dir/(hashlib.sha256(url.encode()).hexdigest()+".json.gz")).write_bytes(raw)
        seen[url]={"status":"parsed","kind":"weekly","facts_sha256":hashlib.sha256(raw).hexdigest()}
    (root/"checkpoint.json").write_text(json.dumps({"schema":1,"queue":list(seen),
        "done":seen,"started_at":datetime.now(timezone.utc).isoformat()}),"utf-8")


class FullHappingsReconciliationTests(unittest.TestCase):
    def test_reconciles_one_source_blank_address_without_modifying_catalog(self):
        baseline=[market()]
        with tempfile.TemporaryDirectory() as folder:
            tmp=Path(folder)
            snapshot(tmp,[(GO,"Gorizia","Piazza Vittoria",2)])
            with patch("happings_full_reconciliation.load_existing",return_value=baseline):
                before=json.dumps(baseline,sort_keys=True)
                result=analyze(tmp/"unused-manifest.json",tmp,tmp/"audit")
                self.assertEqual(json.dumps(baseline,sort_keys=True),before)
            self.assertEqual(result["unique_weekly_city_day_groups"],1)
            self.assertEqual(result["outcomes"]["existing_blank_address_recoverable_by_live_reader"],1)
            self.assertEqual(result["catalog_happings_field_coverage"]["addresses_blank"],1)
            self.assertEqual(result["observed_weekly_dayparts"]["morning_not_clock_hours"],1)
            self.assertEqual(result["new_catalog_ids_admitted"],0)
            self.assertEqual(len(json.loads((tmp/"audit/happings-source-worklist.json").read_text())),1)

    def test_province_leak_is_quarantined_and_istat_result_is_shown(self):
        with tempfile.TemporaryDirectory() as folder:
            tmp=Path(folder)
            snapshot(tmp,[(AL,"Biella","Piazza Cisterna",2)])
            with patch("happings_full_reconciliation.load_existing",return_value=[]):
                summary=analyze(tmp/"unused-manifest.json",tmp,tmp/"audit")
            self.assertEqual(summary["outcomes"]["source_city_outside_index_province"],1)
            work=json.loads((tmp/"audit/happings-source-worklist.json").read_text())
            self.assertEqual(work[0]["actual_istat_province"],"BI")
            self.assertEqual(work[0]["new_catalog_ids_admitted"] if "new_catalog_ids_admitted" in work[0] else 0,0)

    def test_missing_catalog_market_is_candidate_only(self):
        with tempfile.TemporaryDirectory() as folder:
            tmp=Path(folder)
            snapshot(tmp,[(GO,"Gorizia","Piazza Vittoria",2)])
            with patch("happings_full_reconciliation.load_existing",return_value=[]):
                summary=analyze(tmp/"unused-manifest.json",tmp,tmp/"audit")
            self.assertEqual(summary["outcomes"]["new_venue_possible_needs_source_html_admission"],1)
            self.assertEqual(summary["new_catalog_ids_admitted"],0)

    def test_altered_compressed_facts_fail_before_reporting(self):
        with tempfile.TemporaryDirectory() as folder:
            tmp=Path(folder)
            snapshot(tmp,[(GO,"Gorizia","Piazza Vittoria",2)])
            target=next((tmp/"pages").glob("*.json.gz"))
            target.write_bytes(target.read_bytes()+b"tampered")
            with patch("happings_full_reconciliation.load_existing",return_value=[]):
                with self.assertRaisesRegex(ValueError,"hash"):
                    analyze(tmp/"unused-manifest.json",tmp,tmp/"audit")


if __name__=="__main__":
    unittest.main()
