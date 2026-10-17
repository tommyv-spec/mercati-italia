import copy
import unittest
from datetime import date
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from source_bologna import (
    DATASET_ID, METADATA_URL, RECORDS_URL, schedule_rule,
    official_market, position, download, convert, fetch_json,
)
from export_static import normalize

TODAY = date(2026, 10, 12)


def row(num, typ="mercato", subtype="periodico", name=None,
        day="Venerdì", location="piazza VIII Agosto", **kwargs):
    fields = {
        "denominazione": name or ("LA PIAZZOLA" if num in (1,2) else f"PIAZZA {num}"),
        "tipologia": typ, "tipologia_mercato": subtype,
        "giorni_svolgimento": day, "ubicazione": location,
        "orario_svolgimento": "08:00-17:00",
        "specializzazione": "non alimentare",
        "lat":44.5003894498474, "long":11.345360315865,
        "geopoint":[44.5003894498474, 11.345360315865],
    }
    fields.update(kwargs)
    return {
        "datasetid":DATASET_ID,
        "recordid":f"{num:040x}",
        "fields":fields,
        "record_timestamp":"2025-04-02T14:32:57.843Z",
    }


def snapshot(processed="2025-04-02", rows=None):
    if rows is None:
        curated=(
            [row(1,day="Venerdì"),row(2,day="Sabato")]
            +[row(3+i,typ="mercato",subtype="rionale",day="Lunedì-sabato")
              for i in range(9)]
            +[row(12+i,typ="mercato",subtype="periodico",
                  day="Martedì da marzo a giugno e da settembre a dicembre")
              for i in range(17)]
            +[row(29+i,typ="mercato produttori agricoli",subtype=None,day="Mercoledì")
              for i in range(20)]
        )
        excluded=([row(49+i,typ="fiera",subtype="periodico") for i in range(31)]
                  +[row(80+i,typ="mercato",subtype="a turno giornaliero")
                    for i in range(59)]
                  +[row(139+i,typ="mercato",subtype="giornaliero periferico")
                    for i in range(4)]
                  +[row(143+i,typ="mercato",subtype="mercato diffuso A")
                    for i in range(27)]
                  +[row(170+i,typ="mercato",subtype="mercato diffuso B")
                    for i in range(43)]
                  +[row(213+i,typ="mercato",subtype="stagionale")
                    for i in range(37)])
        # Filler count matches the genuine official 2026 snapshot: 249
        # 48 curated + 201 out-of-scope
        rows=curated+excluded
        assert len(rows)==249
    return {
        "dataset_id":DATASET_ID,
        "publisher_data_updated_at":processed,
        "publisher_claimed_modified_at":"2025-12-31",
        "publisher_update_scope":"dataset_not_each_market",
        "publisher_license_claim":"CC BY 4.0",
        "expected_rows":len(rows),
        "rows":rows,
    }


def meta(processed="2025-04-02", license="CC BY 4.0"):
    return {"dataset_id":DATASET_ID,"metas":{"default":{
        "license":license,
        "data_processed":processed+"T14:33:42+00:00",
        "modified":"2025-12-31T12:31:56+00:00",
        "modified_updates_on_data_change":False,
        "records_count":249,
    }}}


class BolognaSourceTests(unittest.TestCase):
    def test_real_classification_48_not_249(self):
        found=convert(snapshot(),today=TODAY)
        self.assertEqual(len(found),48)
        self.assertTrue(all(r["slug"].startswith("bo-open-") for r in found))
        self.assertTrue(all(r["date"] == [] for r in found),
                        "last processed April 2025 is too old to forecast October 2026")
        self.assertTrue(all(r["date_quality"]=="sconosciuta" for r in found))
        self.assertTrue(all(r["aggiornamento_ambito"]=="dataset" for r in found))
        self.assertTrue(all(not r["verificato_il"] for r in found))

    def test_real_la_piazzola_friday_and_saturday_survive_separately(self):
        converted=convert(snapshot(),today=TODAY)
        la_piazzola=[x for x in converted if x["nome"]=="Mercato La Piazzola"]
        self.assertEqual(len(la_piazzola),2)
        self.assertNotEqual(la_piazzola[0]["slug"],la_piazzola[1]["slug"])
        self.assertTrue(all(not x["date"] for x in la_piazzola))
        replay=convert(snapshot(),today=TODAY)
        self.assertEqual(converted,replay)

    def test_if_publisher_updates_future_forecast_only_simple_weekdays(self):
        converted=convert(snapshot("2026-10-01"),today=TODAY)
        weekly=[x for x in converted if x["nome"]=="Mercato La Piazzola"]
        self.assertEqual(len(weekly),2)
        self.assertTrue(all(x["date_quality"]=="prevista" for x in weekly))
        self.assertEqual({date.fromisoformat(x["date"][0]).weekday() for x in weekly},{4,5})
        # Real complex seasonal wording is intentionally NOT interpreted
        # as every Tuesday across the year.
        seasonal = next(x for x in converted if x["id_fonte"] == f"{12:040x}")
        self.assertEqual(seasonal["date"], [])
        self.assertEqual(seasonal["date_quality"], "sconosciuta")
        self.assertEqual(seasonal["ricorrenza_testo"], "Calendario da verificare presso il Comune")

    def test_monthly_complex_exclusions_not_promoted(self):
        self.assertIsNone(schedule_rule(
            "Seconda domenica e sabato antecedente di ogni mese escluso luglio ed agosto"))
        self.assertIsNone(schedule_rule(
            "Primo martedì di ogni mese ad esclusione di luglio e agosto"))
        self.assertIsNone(schedule_rule(
            "Martedì da marzo a giugno e da settembre a dicembre"))
        self.assertIsNone(schedule_rule("Lunedì-domenica e festivi"))
        self.assertEqual(schedule_rule("Lunedì-sabato"),
                         {"kind":"weekly","weekdays":[0,1,2,3,4,5]})
        self.assertEqual(schedule_rule("Martedì, venerdì"),
                         {"kind":"weekly","weekdays":[1,4]})
        self.assertEqual(schedule_rule("Ogni seconda domenica del mese"),
                         {"kind":"monthly_nth_weekday","weekday":6,"ordinal":2})

    def test_no_fake_precise_coordinates_from_indicative_publisher_point(self):
        out=convert(snapshot(),today=TODAY)
        self.assertTrue(all(r["position_quality"] != "precisa" for r in out))
        lat,lng=position(snapshot()["rows"][0]["fields"])
        self.assertAlmostEqual(lat,44.500389,places=5)
        invalid=copy.deepcopy(snapshot()["rows"][0]["fields"])
        invalid["geopoint"]=[44.1,11.3]
        self.assertEqual(position(invalid),(None,None))

    def test_relocation_street_not_navigable_and_metadata_preserved(self):
        s=snapshot()
        s["rows"][0]["fields"]["ubicazione"]="piazza della Pace (trasferimento temporaneo da via Felice Battaglia)"
        converted=convert(s,today=TODAY)
        record=next(x for x in converted if x["id_fonte"]==f"{1:040x}")
        self.assertEqual(record["indirizzo"],"")
        self.assertIn("trasferimento temporaneo",record["descrizione"])
        normalized,error=normalize(record,TODAY)
        self.assertIsNone(error)
        self.assertEqual(normalized["indirizzo"],"")
        self.assertEqual(normalized["id_fonte"],f"{1:040x}")

    def test_real_recordid_required_for_any_curated_record(self):
        s=snapshot()
        s["rows"][0]["recordid"]="not-an-official-identifier"
        with self.assertRaisesRegex(ValueError,"identifier"):
            convert(s,today=TODAY)
        s=snapshot()
        s["rows"][1]["recordid"]=s["rows"][0]["recordid"]
        with self.assertRaisesRegex(ValueError,"Duplicate"):
            convert(s,today=TODAY)

    def test_no_fair_or_single_stall_imports(self):
        out=convert(snapshot(),today=TODAY)
        self.assertFalse(any("Fiera di San Luca" in x["nome"] for x in out))
        self.assertFalse(any("a turno giornaliero" in x["tags"] for x in out))
        self.assertEqual(len({x["slug"] for x in out}),48)

    def test_one_bounded_request_with_official_identifiers_and_frozen_dataset(self):
        queries=[]
        def fetch(url):
            queries.append(url)
            if url==METADATA_URL:return meta()
            if url==RECORDS_URL:return {
                "nhits":249, "records":snapshot()["rows"],
            }
            self.fail("Unexpected URL")
        result=download(fetch)
        self.assertEqual(result["expected_rows"],249)
        self.assertEqual(queries,[METADATA_URL,RECORDS_URL,METADATA_URL])

    def test_changed_dataset_or_partial_download_fails_closed(self):
        state={"reads":0}
        def change(url):
            if url==METADATA_URL:
                state["reads"]+=1
                return meta("2025-04-02" if state["reads"]==1 else "2025-04-03")
            return {"nhits":249,"records":snapshot()["rows"]}
        with self.assertRaisesRegex(ValueError,"changed during"):
            download(change)
        def short(url):
            return meta() if url==METADATA_URL else {"nhits":249,"records":snapshot()["rows"][:30]}
        with self.assertRaisesRegex(ValueError,"Incomplete"):
            download(short)

    def test_wrong_license_or_wrong_modification_semantics_blocks(self):
        with self.assertRaisesRegex(ValueError,"license changed"):
            download(lambda url: meta(license="UNKNOWN") if url==METADATA_URL
                     else {"nhits":249,"records":snapshot()["rows"]})
        def auto_changed(url):
            value=meta()
            value["metas"]["default"]["modified_updates_on_data_change"]=True
            return value if url==METADATA_URL else {"nhits":249,"records":snapshot()["rows"]}
        with self.assertRaisesRegex(ValueError,"semantics changed"):
            download(auto_changed)

    def test_no_external_unreviewed_urls(self):
        with self.assertRaisesRegex(ValueError,"Unapproved"):
            fetch_json("https://example.com/internal")


if __name__=="__main__":
    unittest.main()
