"""Post-commit static checks are separate from the original publisher writer."""
from __future__ import annotations

import hashlib
import sys
import unittest
from datetime import date
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import happings_postrelease_audit as audit
from happings_weekly_admission import _new_row
from export_static import normalize

URL="https://www.happings.com/it/mercati-settimanali-a-udine-e-provincia/"
DAY=date(2026,10,21)
HTML=b"observed publisher html"*25


def inputs():
    old={"slug":"other-friuli","nome":"Mercatino diverso","citta":"Udine",
         "regione":"Friuli Venezia Giulia","provincia":"UD",
         "fonte":"other"}
    raw=_new_row({"city":"Aquileia","weekday":1,"place":"Piazza San Giovanni"},
            region="friuli venezia giulia",province="UD",source_url=URL,
            read_on=DAY,page_hash=hashlib.sha256(HTML).hexdigest(),
            page_metadata=None)
    row,err=normalize(raw,DAY)
    assert not err
    page={"requested_url":URL,"final_url":URL,"html":HTML}
    report={"schema":1,"status":"dev_published","dev_published":True,
            "qa_gate_approved":True,"added_ids":[raw["slug"]],
            "old_record_count":1,"new_record_count":2,
            "existing_market_records_changed":0,
            "existing_market_dates_expired":0,
            "existing_market_non_calendar_fields_changed":0,
            "source_page_hashes":[{"url":URL,"sha256":hashlib.sha256(HTML).hexdigest()}]}
    return old,raw,row,page,report


class PostreleaseTests(unittest.TestCase):
    def test_source_replay_verifies_exact_added_record(self):
        old,raw,row,page,report=inputs()
        with patch.object(audit,"preview",
                          return_value=([old,raw],{"added_ids":[raw["slug"]]})),\
             patch.object(audit,"verify_changes") as verifier:
            summary=audit.verify_cohort(
                {old["slug"]:old},{old["slug"]:old,row["slug"]:row},
                report,[page],today=DAY)
        self.assertTrue(summary["release_safe"])
        self.assertEqual(summary["published_new_market_ids"],1)
        self.assertEqual(summary["existing_record_content_changes"],0)
        verifier.assert_called_once()

    def test_reject_existing_catalog_mutation(self):
        old,raw,row,page,report=inputs()
        modified={**old,"nome":"Altered existing venue"}
        with self.assertRaisesRegex(ValueError,"existing market"):
            audit.verify_cohort({old["slug"]:old},
                {old["slug"]:modified,row["slug"]:row},
                report,[page],today=DAY)

    def test_independent_date_expiry_without_other_mutations(self):
        old,raw,row,page,report=inputs()
        before={**old,"date":["2026-10-20","2026-10-21","2026-10-22"],
                "date_quality":"prevista","orario_testo":"08:00 - 13:00"}
        after={**before,"date":["2026-10-21","2026-10-22"]}
        proof={**report,"existing_market_records_changed":1,
               "existing_market_dates_expired":1}
        with patch.object(audit,"preview",
                          return_value=([before,raw],{"added_ids":[raw["slug"]]})),\
             patch.object(audit,"verify_changes"):
            summary=audit.verify_cohort(
                {before["slug"]:before},
                {before["slug"]:after,row["slug"]:row},
                proof,[page],today=DAY)
        self.assertEqual(summary["existing_calendar_rollovers"],1)
        self.assertEqual(summary["existing_non_calendar_changes"],0)
        for tamper in (
            {**after,"date":["2026-10-22"]},
            {**after,"date":["2026-10-21","2026-10-22","2026-10-23"]},
            {**after,"orario_testo":"opened, verified"},
            {**after,"fonte":"fabricated"},
        ):
            with self.subTest(tamper=tamper):
                with self.assertRaisesRegex(ValueError,"existing market"):
                    audit.verify_cohort(
                        {before["slug"]:before},
                        {before["slug"]:tamper,row["slug"]:row},
                        proof,[page],today=DAY)
        with self.assertRaisesRegex(ValueError,"existing market"):
            audit.verify_cohort(
                {before["slug"]:before},
                {before["slug"]:after,row["slug"]:row},
                report,[page],today=DAY)

    def test_reject_saved_source_html_change(self):
        old,raw,row,page,report=inputs()
        forged={**page,"html":b"unrelated bytes"}
        with self.assertRaisesRegex(ValueError,"source HTML"):
            audit.verify_cohort({old["slug"]:old},
                {old["slug"]:old,row["slug"]:row},
                report,[forged],today=DAY)

    def test_reject_fake_future_date(self):
        old,raw,row,page,report=inputs()
        tampered={**row,"date":["2026-11-03"],"date_quality":"riportata"}
        with patch.object(audit,"preview",
                          return_value=([old,raw],{"added_ids":[raw["slug"]]})),\
             patch.object(audit,"verify_changes"):
            with self.assertRaisesRegex(ValueError,"source-reproduced"):
                audit.verify_cohort({old["slug"]:old},
                    {old["slug"]:old,row["slug"]:tampered},
                    report,[page],today=DAY)

    def test_reject_unreviewed_asset_paths(self):
        from tempfile import TemporaryDirectory
        with TemporaryDirectory() as tmp:
            for rev,path in [("HEAD","public/../../../etc/passwd"),
                             ("../../main","public/data/v1/manifest.json"),
                             ("HEAD","public/data/v1/private.txt")]:
                with self.assertRaisesRegex(ValueError,"Untrusted"):
                    audit.git_blob(Path(tmp),rev,path)


if __name__=="__main__":
    unittest.main()
