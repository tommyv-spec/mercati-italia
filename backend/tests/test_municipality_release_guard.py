import unittest
from copy import deepcopy
from datetime import date
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from municipality_reconciliation import reconcile
from municipality_release_guard import check
from test_municipality_reconciliation import REFERENCE, market

class MunicipalityReleaseGuardTests(unittest.TestCase):
    def source_case(self):
        original=market(
            "mercato-settimanale-di-castiglione-messer-marino-in-provincia-di-mercato-settima",
            "Castiglione Messer Marino, in provincia di... Mercato settimanale a Celenza Sul Trigno Il mercato settimanale di Celenza",
            "CH","Abruzzo",
            "Mercato settimanale di Castiglione Messer Marino, in provincia di... Mercato settimanale a Celenza Sul Trigno")
        return original

    def test_source_bound_city_cleanup_and_calendar_quarantine_pass(self):
        original=self.source_case()
        after,report=reconcile([original],REFERENCE,apply=True)
        result=check([original],after,report)
        self.assertEqual(result["checked_ids"],1)
        self.assertEqual(result["city_replacements"],1)
        self.assertEqual(result["contaminated_titles_repaired"],1)
        self.assertEqual(result["calendar_sources_quarantined"],1)
        self.assertEqual(result["forecast_dates_removed"],2)
        self.assertEqual(result["publisher_urls_or_human_verifications_changed"],0)
        self.assertEqual(original["date_quality"],"prevista")

    def test_repeat_is_idempotent(self):
        original=self.source_case()
        once,_=reconcile([original],REFERENCE,apply=True)
        second,report=reconcile(once,REFERENCE,apply=True)
        self.assertEqual(once,second)
        self.assertEqual(check(once,second,report)["changes"],0)

    def test_false_source_or_geocoordinates_do_not_pass_even_if_report_approved(self):
        original=self.source_case()
        updated,report=reconcile([original],REFERENCE,apply=True)
        for field,value in (("lat",10.0),("url_fonte","https://untrusted"),
                            ("verificato_il","2026-10-12"),("provincia","RM"),
                            ("indirizzo","Via diversa"),("status","confermato")):
            wrong=deepcopy(updated)
            wrong[0][field]=value
            with self.assertRaisesRegex(ValueError,"Unapproved municipality"):
                check([original],wrong,report)

    def test_unapproved_city_or_forecast_day_blocked(self):
        original=self.source_case()
        revised,report=reconcile([original],REFERENCE,apply=True)
        wrong=deepcopy(revised)
        wrong[0]["citta"]="Celenza sul Trigno"
        with self.assertRaisesRegex(ValueError,"approved ISTAT"):
            check([original],wrong,report)
        wrong=deepcopy(revised)
        wrong[0]["date"]=["2026-10-13"]
        with self.assertRaisesRegex(ValueError,"quarantine is incomplete"):
            check([original],wrong,report)

    def test_confirmed_or_verified_records_are_never_auto_rewritten(self):
        original=self.source_case()
        original["verificato_il"]="2026-10-11"
        revised,report=reconcile([original],REFERENCE,apply=True)
        self.assertEqual(revised,[original])
        self.assertEqual(check([original],revised,report)["changes"],0)

    def test_bad_istat_sha_and_counter_are_refused(self):
        original=self.source_case()
        revised,report=reconcile([original],REFERENCE,apply=True)
        fake={**report,"source_file_sha256":"0"*64}
        with self.assertRaisesRegex(ValueError,"Untrusted official"):
            check([original],revised,fake)
        fake=deepcopy(report)
        fake["counts"]["city_fixed"]=0
        with self.assertRaisesRegex(ValueError,"counter mismatch"):
            check([original],revised,fake)


if __name__=="__main__":
    unittest.main()
