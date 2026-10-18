"""Every publisher must be audited, even if absent from official source registry."""
from __future__ import annotations
import copy
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from publisher_quality_matrix import (
    analyze,validate,markdown,_day_conflict,_projected_weekday_conflict,
    _safe_origin,REGISTERED_DATASET_ADAPTERS,
)

TODAY=date(2026,10,18)
REGISTRY={
    "schema":1,"record_imports":0,
    "sources":[
        {"id":"2e41941b-80fb-4ded-8330-427383f725f8",
         "title":"Mercati su aree pubbliche","organization":"Regione Lombardia",
         "triage_score":24,"triage_class":"market_location_candidate"},
        {"id":"cov-c","title":"Posteggi","organization":"Regione Veneto",
         "triage_score":9,"triage_class":"concession_registry"},
        {"id":"cov-d","title":"Censimento","organization":"Regione Lazio",
         "triage_score":5,"triage_class":"aggregated_statistics"},
        {"id":"cov-e","title":"Fiere","organization":"Ente","triage_score":12,
         "triage_class":"mixed_events_candidate"},
    ],
}
PROBES={"schema":1,"imports":0,"verified_event_count":0,
        "probe_history":{"cov-e":{"status":"schema_preview_only","viability":"venue_inventory_missing_visit_days"}}}


def row(id,fonte,url,*,city="Brescia",address="Via Roma",
        day="venerdi",recurrence=None,updated="2026-10-01",
        hours="",dates=None,quality="prevista",coordinates=(45.3,10.2)):
    return {
        "slug":id,"fonte":fonte,"url_fonte":url,
        "citta":city,"regione":"Lombardia",
        "indirizzo":address,"ricorrenza_testo":recurrence if recurrence is not None else "Ogni "+day,
        "aggiornato_il":updated,"orario_testo":hours,
        "date":dates if dates is not None else ["2026-10-23"],
        "date_quality":quality,"lat":coordinates[0],"lng":coordinates[1],
        "position_quality":"non_verificata","verificato_il":"",
    }


def sample():
    return [
        row("mercato-happings-brescia-venerdi","happings.com",
            "https://www.happings.com/it/mercati-settimanali-a-brescia-e-provincia/",
            address="",dates=[],updated="2024-01-01"),
        row("mercato-happings-bergamo-venerdi","happings.com",
            "https://www.happings.com/it/happing/mercato-bergamo/",
            city="Bergamo",recurrence="Ogni martedì",address="Centro",dates=[]),
        row("mercatino-anti-bologna-domenica","eventiesagre.it",
            "https://www.eventiesagre.it/Mercatini_Antiquariato/1234_Anno-2022.html",
            city="Bologna",updated="",hours="08:00 - 13:00",dates=[]),
        row("mercato-cosedicasa-brescia-venerdi","cosedicasa.com",
            "https://www.cosedicasa.com/mercatini/brescia-piazza",
            day="venerdi",recurrence="Ogni seconda domenica del mese",
            dates=["2026-10-25"]),
        row("lo-mercap-20001-venerdi","Regione Lombardia – MERCap (CC0 1.0 dichiarata)",
            "https://www.dati.lombardia.it/d/68zx-njaw",
            updated="2026-10-13",address="VIA PIAZZA",hours="08:00–13:00 (fonte comunale, da verificare)"),
        row("untracked-comune-noon","Comune di X",
            "https://www.comune.x.it/dati/",coordinates=(None,None),dates=[]),
    ]


class PublisherQualityMatrixTests(unittest.TestCase):
    def test_every_catalog_publisher_and_every_discovered_dataset_is_present(self):
        rows=sample()
        frozen=copy.deepcopy(rows)
        data=analyze(rows,REGISTRY,probes=PROBES,today=TODAY)
        self.assertEqual(rows,frozen)
        self.assertEqual(data["catalog_record_count"],len(rows))
        self.assertEqual(data["catalog_source_labels_count"],5)
        self.assertEqual(data["official_candidate_dataset_count"],4)
        self.assertEqual(data["market_updates"],0)
        self.assertEqual(data["market_confirmations"],0)
        self.assertTrue(validate(data,REGISTRY))
        self.assertEqual(sum(x["records"] for x in data["publishers"]),len(rows))
        self.assertEqual(data["publishers"][0]["publisher"],"happings.com")
        self.assertEqual(data["publishers"][0]["records"],2)
        self.assertEqual(len(data["candidate_datasets"]),4)

    def test_large_legacy_source_gaps_not_measured_as_official_confirmation(self):
        d=analyze(sample(),REGISTRY,today=TODAY)
        h=next(x for x in d["publishers"] if x["publisher"]=="happings.com")
        self.assertEqual(h["fields"]["hours_missing"],2)
        self.assertEqual(h["fields"]["address_missing"],1)
        self.assertEqual(h["fields"]["stored_source_or_import_date_older_than_540d"],1)
        self.assertEqual(h["fields"]["slug_conflicts_with_explicit_weekday"],1)
        self.assertFalse(h["automatic_import_authorized_by_this_audit"])
        self.assertIn("weekly_area_index",h["layout"])
        self.assertIn("third_party_event",next(x for x in d["publishers"] if x["publisher"]=="eventiesagre.it")["kind"])

    def test_monthly_rules_not_mislabeled_weekly(self):
        self.assertFalse(_day_conflict(sample()[3]))
        m=row("mercato-vecchio-brescia-venerdi","happings.com",
              "https://www.happings.com/it/happing/name",
              recurrence="settimanale - lunedì")
        self.assertTrue(_day_conflict(m))
        m["ricorrenza_testo"]="Ogni venerdì"
        self.assertFalse(_day_conflict(m))

    def test_forecast_date_must_follow_explicit_weekday(self):
        m=row("mercato-abc-venerdi","happings.com",
              "https://www.happings.com/it/happing/example",dates=["2026-10-19"],
              recurrence="Ogni venerdì")
        self.assertTrue(_projected_weekday_conflict(m))
        m["date_quality"]="confermata"
        self.assertFalse(_projected_weekday_conflict(m))
        m["date_quality"]="prevista"
        m["date"]=["2026-10-23","2026-10-30"]
        self.assertFalse(_projected_weekday_conflict(m))

    def test_missing_url_or_imprecise_coordinates_are_research_flags(self):
        m=row("p","happings.com","http://notsecure.org/p",
              address="Centro",coordinates=(None,None),dates=[])
        d=analyze([m],REGISTRY,today=TODAY)
        flags=d["publishers"][0]["fields"]
        self.assertEqual(flags["source_url_invalid_or_missing"],1)
        self.assertEqual(flags["address_generic_not_navigable"],1)
        self.assertEqual(flags["coordinates_missing"],1)
        self.assertFalse(_safe_origin("https://user:pass@evil.com/market"))
        self.assertFalse(_safe_origin("http://host.example/"))
        self.assertTrue(_safe_origin("https://www.happings.com/it/happing/mercato/"))

    def test_candidate_concession_rows_are_not_counted_as_markets(self):
        d=analyze(sample(),REGISTRY,probes=PROBES,today=TODAY)
        c={x["dataset_id"]:x for x in d["candidate_datasets"]}
        self.assertEqual(c["cov-c"]["review_status"],"concession_registry_not_market_venues")
        self.assertEqual(c["cov-d"]["review_status"],"statistics_not_event_venues")
        self.assertEqual(c["cov-e"]["review_status"],"schema_sampled_review_only")
        self.assertIsNone(c["cov-e"]["actual_market_count_estimated"])
        self.assertEqual(c["2e41941b-80fb-4ded-8330-427383f725f8"]["review_status"],"already_integrated_adapter")
        self.assertTrue(all(x["new_market_imports_authorized_by_this_audit"] is False for x in c.values()))

    def test_source_records_count_change_is_not_inferred_as_market_closure(self):
        prior=analyze(sample(),REGISTRY,today=TODAY)
        next_rows=sample()[1:]
        d=analyze(next_rows,REGISTRY,previous=prior,today=TODAY)
        h=next(x for x in d["publishers"] if x["publisher"]=="happings.com")
        self.assertEqual(h["count_delta_since_last_audit"],-1)
        self.assertEqual(d["markets_deleted"],0)
        self.assertTrue(d["research_only"])

    def test_qa_refuses_untrusted_registry_duplicate_and_false_imports(self):
        for bad in (
            {"schema":1,"record_imports":1,"sources":REGISTRY["sources"]},
            {"schema":1,"record_imports":0,"sources":[REGISTRY["sources"][0]]*2},
            {"schema":1,"record_imports":0,"sources":[]},
        ):
            with self.assertRaises(ValueError):
                analyze(sample(),bad,today=TODAY)
        d=analyze(sample(),REGISTRY,today=TODAY)
        d["market_confirmations"]=1
        with self.assertRaisesRegex(ValueError,"cannot infer permissions"):
            validate(d,REGISTRY)

    def test_document_contains_all_publishers_and_not_claimed_reuse(self):
        d=analyze(sample(),REGISTRY,probes=PROBES,today=TODAY)
        md=markdown(d)
        for source in ("Happings","EventiESagre","cosedicasa","Regione Lombardia"):
            self.assertIn(source.casefold(),md.casefold())
        self.assertIn("NESSUNA",md.upper())
        self.assertIn("49" if len(REGISTRY["sources"])==49 else "4",md)

    def test_no_unsafe_review_flags_from_source_count_alone(self):
        d=analyze(sample(),REGISTRY,today=TODAY)
        h=next(x for x in d["publishers"] if x["publisher"]=="happings.com")
        self.assertGreater(h["priority_workload_score_not_evidence"],h["records"])
        self.assertEqual(h["actual_individual_market_validations"],0)
        self.assertEqual(d["source_snapshot_rows_reused"],0)

if __name__=="__main__":
    unittest.main()
