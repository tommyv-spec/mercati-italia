"""Source-fact detail matching never promotes unverified catalog changes."""
from __future__ import annotations

import gzip
import hashlib
import json
import sys
import tempfile
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import happings_detail_matching_report as report

DAY=date(2026,10,21)
PISA="https://www.happings.com/it/happing/mercato-coperto-campagna-amica-di-pisa/"
SHA="7"*64


def market():
    return {"slug":"existing-pisa","nome":"Mercato coperto di Pisa","citta":"Pisa",
            "regione":"Toscana","provincia":"PI","fonte":"happings.com",
            "url_fonte":PISA,"orario_testo":"","indirizzo":"","date_quality":"prevista"}


def fixture(root,*,conflicts=None):
    page={"url":PISA,"status":"parsed","kind":"detail","read_at":"2026-10-21T09:00:00+00:00",
          "html_sha256":SHA,"bytes":650,"market_classified":True,
          "conflicts":conflicts or [],
          "source":{"requested_url":PISA,"final_url":PISA,"html_sha256":SHA},
          "event":{"name":"Mercato coperto di Pisa","category":"mercati",
                   "hours_text":"Sabato 07:30–12:30",
                   "hours_intervals":[{"weekday":5,"start":"07:30","end":"12:30"}],
                   "occurrences":[{"date":"2026-10-24"}],
                   "location":{"street_address":"Via della Pesa 1","city":"Pisa",
                               "province":"PI","region":"Toscana"}}}
    payload=gzip.compress((json.dumps(page,sort_keys=True)+"\n").encode("utf-8"))
    (root/"pages").mkdir(parents=True)
    (root/"pages"/(hashlib.sha256(PISA.encode()).hexdigest()+".json.gz")).write_bytes(payload)
    state={"schema":1,"queue":[PISA],"done":{PISA:{
        "status":"parsed","kind":"detail",
        "facts_sha256":hashlib.sha256(payload).hexdigest()}}}
    (root/"checkpoint.json").write_text(json.dumps(state),"utf-8")
    return page


class DetailMatchingReportTests(unittest.TestCase):
    def test_unique_existing_detects_recoverable_fields_without_changing_catalog(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            fixture(root)
            existing=[market()]
            original=json.dumps(existing,sort_keys=True)
            with patch.object(report.matching,"geography",return_value=("Pisa","PI","Toscana")),\
                 patch.object(report.matching,"_category",return_value="misto"),\
                 patch.object(report.matching,"_matches",
                              return_value=(existing[0],"exact_page",[existing[0]])):
                stats,items=report.audit(existing,root,today=DAY)
            self.assertEqual(json.dumps(existing,sort_keys=True),original)
            self.assertEqual(stats["counts"]["uniquely_matched_existing"],1)
            self.assertEqual(stats["counts"]["matched_existing_hours_missing_in_catalog"],1)
            self.assertEqual(stats["counts"]["matched_existing_address_missing_in_catalog"],1)
            self.assertEqual(stats["counts"]["matched_existing_source_dates_missing_in_catalog"],1)
            self.assertEqual(stats["existing_record_mutations"],0)
            self.assertEqual(items[0]["matched_market_id"],"existing-pisa")

    def test_conflicting_source_never_counts_as_safe_field_recovery(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            fixture(root,conflicts=[{"field":"hours_text","code":"different_times"}])
            row=market()
            with patch.object(report.matching,"geography",return_value=("Pisa","PI","Toscana")),\
                 patch.object(report.matching,"_category",return_value="misto"),\
                 patch.object(report.matching,"_matches",return_value=(row,"exact_page",[row])):
                stats,_=report.audit([row],root,today=DAY)
            self.assertEqual(stats["counts"]["market_details_with_source_conflicts"],1)
            self.assertNotIn("matched_existing_hours_missing_in_catalog",stats["counts"])

    def test_fake_source_checksum_fails_closed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)
            fixture(root)
            stored=next((root/"pages").glob("*"))
            stored.write_bytes(stored.read_bytes()+b"tampered")
            with self.assertRaisesRegex(ValueError,"hash"):
                report.audit([],root,today=DAY)


if __name__=="__main__":
    unittest.main()
