import copy
import json
import sys
import unittest
from datetime import date
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from roma_xiii_map_audit import (
    validate_map,review,MARKER_STREETS,MUNICIPAL_PAGE,
)

ROOT=Path(__file__).resolve().parents[1]
SOURCE=json.loads((ROOT/"data/roma-municipio-xiii-market-map-reviewed.json").read_text("utf-8"))


def m(sid,name,street,recurrence="settimanale - martedì",lat=None,lng=None):
    return {
        "slug":sid,"nome":name,"regione":"Lazio","citta":"Roma",
        "indirizzo":street,"ricorrenza_testo":recurrence,
        "lat":lat,"lng":lng,
        "status":"non_confermato","date_quality":"sconosciuta",
        "verificato_il":"","url_fonte":"https://existing.example/market",
    }


class RomeMunicipalMapTests(unittest.TestCase):
    def test_nine_really_distinct_source_points_and_two_montespaccato_venues(self):
        markers=validate_map(SOURCE)
        self.assertEqual(len(markers),9)
        self.assertEqual(len(MARKER_STREETS),9)
        self.assertEqual(sum(x["source_name"]=="MONTESPACCATO" for x in markers),2)
        self.assertEqual(markers[5]["source_weekdays"],[1])
        self.assertEqual(markers[6]["source_weekdays"],[5])
        self.assertNotEqual(markers[5]["source_address"],markers[6]["source_address"])

    def test_nonmatched_place_is_a_lead_not_new_market(self):
        original=[m("rm-existing","Mercato in altra zona","Piazza Testaccio",
                    "settimanale - lunedì")]
        frozen=copy.deepcopy(original)
        result=review(original,SOURCE,today=date(2026,10,12))
        self.assertEqual(result["municipal_map_markers"],9)
        self.assertEqual(result["original_market_ids_preserved"],1)
        self.assertEqual(result["source_market_ids_published"],0)
        self.assertEqual(result["market_cards_modified"],0)
        self.assertEqual(result["future_events_confirmed"],0)
        self.assertEqual(result["road_directions_enabled"],0)
        self.assertEqual(result["counts"]["not_in_exact_match_sample_not_proof_of_missing_market"],9)
        self.assertEqual(original,frozen)

    def test_match_exact_street_and_weekday_but_only_review_not_edit(self):
        records=[
            m("rome-irnerio","Mercato rionale Irnerio","Via Aurelia 483",
              "settimanale - martedì",41.897769,12.424633),
            m("rome-mont-1","Mercato Montespaccato","Via di Montespaccato",
              "settimanale - martedì",41.90849,12.39526),
            m("rome-mont-2","Mercato Montespaccato","Via Cornelia",
              "settimanale - sabato",41.90923,12.39822),
        ]
        report=review(records,SOURCE,today=date(2026,10,12))
        irnerio=next(x for x in report["observations"] if x["source_key"]=="rm13-01")
        self.assertEqual(irnerio["review_bucket"],"strong_source_match_review_only")
        self.assertEqual(irnerio["candidate_catalog_rows"],1)
        for sid in ("rm13-06","rm13-07"):
            item=next(x for x in report["observations"] if x["source_key"]==sid)
            self.assertGreaterEqual(item["candidate_catalog_rows"],2)
            self.assertTrue(item["automatic_enrichment_allowed"] is False)
        self.assertEqual(report["market_cards_modified"],0)

    def test_coordinate_disagreement_holds_record_even_if_name_and_street_match(self):
        wrong=[m("wrong","Mercato Irnerio","Via Aurelia 483",
                 "settimanale - martedì",41.11,12.94)]
        result=review(wrong,SOURCE)
        sample=result["observations"][0]
        self.assertEqual(sample["review_bucket"],"location_conflict_needs_review")
        self.assertEqual(sample["examples"][0]["match_type"],
                         "coordinates_disagree_requires_source_review")

    def test_unreviewed_license_or_renamed_marker_refuses_source(self):
        changed=copy.deepcopy(SOURCE)
        changed["imported_records_allowed"]=1
        with self.assertRaisesRegex(ValueError,"Unreviewed"):
            validate_map(changed)
        changed=copy.deepcopy(SOURCE)
        changed["observations"][6]["source_key"]="rm13-06"
        with self.assertRaisesRegex(ValueError,"repeated"):
            validate_map(changed)
        changed=copy.deepcopy(SOURCE)
        changed["observations"][6]["source_address"]=changed["observations"][5]["source_address"]
        with self.assertRaisesRegex(ValueError,"cannot be collapsed"):
            validate_map(changed)

    def test_duplicate_market_ids_are_rejected_and_no_location_inference(self):
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            review([m("same","Mercato A","Via A"),m("same","Mercato B","Via B")],SOURCE)
        bad=[m("bad","Mercato Irnerio","Via Aurelia 483",lat=30,lng=0)]
        report=review(bad,SOURCE)
        self.assertEqual(report["market_cards_modified"],0)


if __name__=="__main__":
    unittest.main()
