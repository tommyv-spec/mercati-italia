import unittest
from datetime import date
from pathlib import Path
from urllib.parse import parse_qs, urlsplit
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from source_lombardia import (DATASET_ID, API_URL, METADATA_URL, download,
    convert, weekday, months_of_operation, point, hour_span, projected_dates)


def row(id, day="VENERDÌ", freq="SETTIMANALE", city="POGLIANO MILANESE",
        months=None, **extras):
    out = {
        "codice_id": str(id), "despro": "MI", "istat": "15176",
        "descom": city, "ubicazione": "VIA EUROPA", "indirizzi": "VIA EUROPA",
        "periodicita_tipo": freq, "giorno": day,
        "mesi_svolgimento": months or (
            "GENNAIO, FEBBRAIO, MARZO, APRILE, MAGGIO, GIUGNO, "
            "LUGLIO, AGOSTO, SETTEMBRE, OTTOBRE, NOVEMBRE, DICEMBRE"
        ),
        "dalle_ore_invernale": "08:00", "alle_ore_invernale": "12:00",
        "dalle_ore_estivo": "08:00", "alle_ore_estivo": "12:00",
        "geo_x": "8.99526544", "geo_y": "45.53848875",
        "location": {"type":"Point","coordinates":[8.99526544,45.53848875]},
    }
    out.update(extras)
    return out


def payload(rows, date_str="2026-10-06"):
    return {
        "dataset_id": DATASET_ID, "publisher_data_updated_at": date_str,
        "publisher_update_scope": "entire_dataset_not_each_market",
        "rows": rows, "expected_rows": len(rows),
    }


class LombardiaTests(unittest.TestCase):
    now = date(2026, 10, 12)

    def test_official_weekly_row_projects_but_never_confirms(self):
        items = [row(20000+i) for i in range(1100)]
        result = convert(payload(items), today=self.now)
        first = result[0]
        self.assertEqual(first["slug"], "lo-mercap-20000-venerdi")
        self.assertEqual(first["date_quality"], "prevista")
        self.assertEqual(date.fromisoformat(first["date"][0]).weekday(), 4)
        self.assertEqual(first["aggiornato_il"], "2026-10-06")
        self.assertEqual(first["aggiornamento_ambito"], "dataset")
        self.assertEqual(first["verificato_il"], "")
        self.assertNotEqual(first["status"], "attivo")
        self.assertEqual(first["position_quality"], "non_verificata")

    def test_daily_multi_weekday_id_keeps_distinct_schedule_rows(self):
        items = [row(100234, day=x, freq="GIORNALIERO",city="VIGEVANO",
                     istat="18177", despro="PV")
                 for x in ["LUNEDÌ", "MARTEDÌ", "MERCOLEDÌ", "GIOVEDÌ", "VENERDÌ", "SABATO", "DOMENICA"]]
        items += [row(30000+i) for i in range(1093)]
        output = convert(payload(items), today=self.now)
        same = [x for x in output if x["id_fonte"] == "100234"]
        self.assertEqual(len(same), 7)
        self.assertEqual({x["slug"] for x in same}, {
            "lo-mercap-100234-"+d for d in
            ("lunedi", "martedi", "mercoledi", "giovedi",
             "venerdi", "sabato", "domenica")
        })

    def test_unknown_frequency_or_weekday_never_gets_future_dates(self):
        items = [row(30000+i, day=None, freq=None) for i in range(1100)]
        for market in convert(payload(items), today=self.now):
            self.assertEqual(market["date"], [])
            self.assertEqual(market["date_quality"], "sconosciuta")

    def test_biweekly_and_monthly_never_guess_calendar(self):
        items = [row(30000+i, freq="QUINDICINALE" if i%2 else "MENSILE") for i in range(1100)]
        self.assertTrue(all(not market["date"] for market in
                            convert(payload(items), today=self.now)))

    def test_partial_months_only_generate_within_declared_months(self):
        items = [row(30000+i, months="LUGLIO, AGOSTO") for i in range(1100)]
        output = convert(payload(items),today=date(2026, 7, 1))
        self.assertTrue(output[0]["date"])
        self.assertTrue(all(int(d[5:7]) in (7,8) for d in output[0]["date"]))
        self.assertNotIn("Ogni ", output[0]["ricorrenza_testo"])
        self.assertEqual(months_of_operation("GENNAIO, MAGGIO"),{1,5})
        self.assertEqual(months_of_operation("GENNAIO, TBD"),set())

    def test_future_schedules_expire_when_publisher_dataset_stale(self):
        items = [row(30000+i) for i in range(1100)]
        out = convert(payload(items, date_str="2023-01-01"), today=self.now)
        self.assertTrue(all(not x["date"] for x in out))

    def test_repeated_identity_and_same_day_blocks_partial_import(self):
        items = [row(30000+i) for i in range(1099)] + [row(30000)]
        with self.assertRaisesRegex(ValueError, "Ambiguous repeated"):
            convert(payload(items),today=self.now)

    def test_coordinate_requires_agreement_with_geopoint(self):
        correct = row(1)
        self.assertEqual(point(correct), (45.538489,8.995265))
        incorrect = row(2, geo_x="8000", geo_y="4500")
        self.assertEqual(point(incorrect), (None, None))
        self.assertEqual(hour_span(row(3, dalle_ore_invernale="00:00",
                     alle_ore_invernale="00:00")), 
                     "Estate: 08:00–12:00 (fonte comunale, da verificare)")

    def test_do_not_duplicate_existing_milano_city_adapter(self):
        items = [row(30000+i) for i in range(1099)]
        items.append(row(99999, city="MILANO", istat="15146"))
        out = convert(payload(items),today=self.now)
        self.assertEqual(len(out),1099)
        self.assertNotIn("Milano",set(x["citta"] for x in out))

    def test_missing_identity_quarantines_without_human_verification(self):
        items = [row(30000+i) for i in range(1099)]
        items.append(row(99999, descom=""))
        out = convert(payload(items),today=self.now)
        self.assertEqual(len(out),1099)

    def test_official_counts_are_paged_deterministically(self):
        from datetime import datetime, timezone
        source_time = int(datetime(2026,10,6,tzinfo=timezone.utc).timestamp())
        calls=[]
        def fake(url):
            calls.append(url)
            if url == METADATA_URL:
                return {"id": DATASET_ID, "licenseId": "CC0_10",
                        "rowsUpdatedAt": source_time}
            query = parse_qs(urlsplit(url).query)
            if "$select" in query:
                return [{"n":"1100"}]
            start = int(query["$offset"][0])
            limit = int(query["$limit"][0])
            self.assertEqual(query["$order"],[":id"])
            return [row(30000+i) for i in range(start,start+limit)]
        data=download(fake,page_size=500)
        self.assertEqual(data["expected_rows"],1100)
        self.assertEqual(len(data["rows"]),1100)
        self.assertEqual(len(calls),6)

    def test_bad_page_size_or_partial_response_is_rejected(self):
        with self.assertRaises(ValueError):
            download(lambda u: [],page_size=1200)
        from datetime import datetime, timezone
        ts=int(datetime(2026,10,6,tzinfo=timezone.utc).timestamp())
        def short(url):
            if url == METADATA_URL:
                return {"id": DATASET_ID,"licenseId":"CC0_10",
                        "rowsUpdatedAt":ts}
            if "$select" in parse_qs(urlsplit(url).query):
                return [{"n":"1100"}]
            return []
        with self.assertRaisesRegex(ValueError,"Incomplete official source page"):
            download(short)

    def test_known_weekday_names(self):
        self.assertEqual(weekday("VENERDÌ"),4)
        self.assertEqual(weekday("sabato"),5)
        self.assertIsNone(weekday("giorno non disponibile"))
        self.assertEqual(len(projected_dates(4,set(range(1,13)),self.now)),17)


if __name__ == "__main__":
    unittest.main()
