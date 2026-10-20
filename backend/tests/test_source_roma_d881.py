import csv
import gzip
import io
import json
import sys
import unittest
from copy import deepcopy
from datetime import date, datetime, timezone
from email.message import Message
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import source_roma_d881 as source

FIXTURES = Path(__file__).with_name("fixtures") / "roma-d881"
METADATA = (FIXTURES / "metadata-2026-10-20.json").read_bytes()
CSV = gzip.decompress((FIXTURES / "mercati-rionali-agosto-2023.csv.gz").read_bytes())
CAPTURES = json.loads((FIXTURES / "captures-2026-10-20.json").read_text())
TODAY = date(2026, 10, 20)
READ_METADATA = CAPTURES[0]["fetched_at"]
READ_CSV = CAPTURES[1]["fetched_at"]


def metadata_with(mutator):
    value = json.loads(METADATA)
    mutator(value["result"])
    return json.dumps(value).encode("utf-8")


def csv_rows():
    records = list(csv.DictReader(io.StringIO(CSV.decode("cp1252")), delimiter=";"))
    return [{key.strip(): value for key, value in row.items()} for row in records]


def csv_with(mutator, *, encoding="cp1252"):
    rows = csv_rows()
    mutator(rows)
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=source.HEADERS, delimiter=";")
    writer.writeheader()
    writer.writerows(rows)
    return buffer.getvalue().encode(encoding)


def snapshot(blob=CSV, metadata=METADATA, *, day=TODAY):
    read_metadata = READ_METADATA if day == TODAY else day.isoformat() + "T12:00:00+00:00"
    read_csv = READ_CSV if day == TODAY else day.isoformat() + "T12:00:01+00:00"
    return source.make_snapshot(metadata, blob, metadata_read_at=read_metadata,
                                csv_read_at=read_csv, today=day)


def new_distribution(package, *, day="2026-10-21"):
    item = deepcopy(package["resources"][-1])
    item.update(id="a0000000-0000-4000-8000-000000000001", name="Synthetic future-format regression",
                created=day + "T08:00:00", last_modified=day + "T08:00:00")
    item["url"] = ("https://dati.comune.roma.it/catalog/it/dataset/" + source.DATASET_ID
                   + "/resource/" + item["id"] + "/download/synthetic-new-distribution.csv")
    package["resources"].insert(0, item)  # Ordering is not a version signal.
    package["metadata_modified"] = day + "T08:00:01"


class RomaReaderTests(unittest.TestCase):
    def test_real_latest_distribution_not_the_old_2022_pinned_resource(self):
        selected = source.select_distribution(METADATA, read_at=READ_METADATA)
        self.assertEqual(selected["id"], "cd515283-3079-42fe-a066-ced11b9a8387")
        self.assertEqual(selected["url"], CAPTURES[1]["requested_url"])
        self.assertEqual(len(selected["eligible_distributions"]), 8)
        self.assertEqual(selected["declared_updated_at"], "2023-09-25T08:32:43.034198")
        self.assertEqual(selected["last_modified"], "2023-09-25T08:32:42.964999")

    def test_real_cp1252_rows_blank_lines_and_municipality_note(self):
        parsed = source.parse_snapshot(snapshot(), today=TODAY)
        self.assertEqual(parsed["csv_sha256"], CAPTURES[1]["sha256"])
        self.assertEqual(parsed["metadata_sha256"], CAPTURES[0]["sha256"])
        self.assertEqual(parsed["encoding"], "cp1252")
        self.assertEqual((parsed["physical_rows"], parsed["blank_rows"], parsed["market_rows"]), (1003, 932, 70))
        self.assertEqual(len(parsed["rows"]), 70)
        self.assertEqual(parsed["held_rows"], [])
        self.assertEqual(len(parsed["annotations"]), 1)
        self.assertEqual(parsed["annotations"][0]["raw_fields"]["Note_mercato"],
                         "non ci sono mercati coperti o plateatici")
        self.assertEqual(sum(row["source_updated_on"] == "2023-04-30" for row in parsed["rows"]), 62)
        self.assertEqual(sum(row["source_updated_on"] == "2021-12-31" for row in parsed["rows"]), 8)
        names = {row["name"] for row in parsed["rows"]}
        self.assertIn("Nuovo Cinecittà", names)
        self.assertFalse(any("�" in name for name in names))

    def test_six_day_clocks_civic_postcode_and_qualifications_are_retained(self):
        rows = source.parse_snapshot(snapshot(), today=TODAY)["rows"]
        self.assertTrue(all(len(row["hours_by_day"]) == 6 for row in rows))
        self.assertFalse(any("domenica" == day["day"] for row in rows for day in row["hours_by_day"]))
        testaccio = next(row for row in rows if row["name"] == "Testaccio")
        self.assertEqual((testaccio["civic"], testaccio["civic_suffix"], testaccio["postcode"]), ("66", "C", "00153"))
        parioli = next(row for row in rows if row["name"] == "Parioli")
        self.assertIn("alcuni banchi", parioli["hours_notes"])
        self.assertTrue(all(day["end"] == "14:00" for day in parioli["hours_by_day"]))
        different = next(row for row in rows if len({day["end"] for day in row["hours_by_day"]}) > 1)
        self.assertGreater(len({day["end"] for day in different["hours_by_day"]}), 1)
        self.assertEqual(sum(bool(row["hours_notes"]) for row in rows), 5)
        self.assertEqual(sum(bool(row["market_notes"]) for row in rows), 3)

    def test_future_distribution_is_discovered_by_next_read_without_market_edits(self):
        tomorrow = date(2026, 10, 21)
        metadata = metadata_with(new_distribution)
        seen = []
        def fetch(url):
            seen.append(url)
            return metadata if url == source.METADATA_URL else CSV
        times = iter([datetime(2026, 10, 21, 12, tzinfo=timezone.utc),
                      datetime(2026, 10, 21, 12, 0, 1, tzinfo=timezone.utc)])
        captured = source.acquire(today=tomorrow, fetch=fetch, clock=lambda: next(times))
        self.assertEqual(len(seen), 2)
        self.assertEqual(seen[0], source.METADATA_URL)
        self.assertIn("/a0000000-0000-4000-8000-000000000001/", seen[1])
        self.assertEqual(captured["csv"]["url"], seen[1])
        parsed = source.parse_snapshot(captured, today=tomorrow)
        self.assertEqual(parsed["distribution"]["name"], "Synthetic future-format regression")
        self.assertEqual({row["source_updated_on"] for row in parsed["rows"]}, {"2021-12-31", "2023-04-30"})

    def test_reversed_resource_order_selects_same_actual_latest_file(self):
        metadata = metadata_with(lambda package: package["resources"].reverse())
        self.assertEqual(source.select_distribution(metadata, read_at=READ_METADATA)["id"],
                         source.select_distribution(METADATA, read_at=READ_METADATA)["id"])

    def test_newly_created_distribution_with_old_content_time_is_still_discovered(self):
        def edit(package):
            new_distribution(package)
            package["resources"][0]["last_modified"] = "2021-01-01T00:00:00"
        selected = source.select_distribution(metadata_with(edit), read_at="2026-10-21T12:00:00+00:00")
        self.assertEqual(selected["id"], "a0000000-0000-4000-8000-000000000001")
        self.assertEqual(selected["version_basis"], "created")
        self.assertEqual(selected["last_modified"], "2021-01-01T00:00:00")

    def test_ambiguous_or_future_distribution_does_not_fall_back(self):
        def duplicate(package):
            item = deepcopy(package["resources"][-1])
            item["id"] = "a0000000-0000-4000-8000-000000000001"
            item["url"] = item["url"].replace("cd515283-3079-42fe-a066-ced11b9a8387", item["id"])
            package["resources"].append(item)
        for metadata in (metadata_with(duplicate), metadata_with(new_distribution)):
            with self.assertRaises(ValueError):
                source.select_distribution(metadata, read_at=READ_METADATA)

    def test_distributions_are_bound_to_exact_dataset_host_and_resource_id(self):
        original = json.loads(METADATA)["result"]["resources"][-1]
        bad_urls = [original["url"].replace(source.HOST, "127.0.0.1"),
                    original["url"].replace(source.DATASET_ID, "a0000000-0000-4000-8000-000000000001"),
                    original["url"].replace(original["id"], "a0000000-0000-4000-8000-000000000001"),
                    original["url"] + "?download=1", original["url"] + "#fragment",
                    original["url"].replace("https:", "http:"),
                    original["url"].replace(source.HOST, "user@" + source.HOST),
                    original["url"].replace(source.HOST, source.HOST + ":8443")]
        for bad in bad_urls:
            with self.subTest(url=bad):
                metadata = metadata_with(lambda package: package["resources"][-1].update(url=bad))
                with self.assertRaises(ValueError):
                    source.select_distribution(metadata, read_at=READ_METADATA)

    def test_untrusted_metadata_and_duplicate_keys_rejected(self):
        bodies = [b"[]", b"{}", b'{"success":true,"success":false}',
                  metadata_with(lambda package: package.update(private=True)),
                  metadata_with(lambda package: package.update(id="another-package")),
                  metadata_with(lambda package: package["resources"][-1].update(package_id="other"))]
        for blob in bodies:
            with self.subTest(body=blob[:30]), self.assertRaises(ValueError):
                source.select_distribution(blob, read_at=READ_METADATA)

    def test_bad_clocks_dates_and_text_hold_source_row_without_silent_repair(self):
        for key, value in [("Apertura_Lunedi", "25:00"), ("Chiusura_Sabato", ""),
                           ("Chiusura_Martedi", "05:00"), ("AGGIORNATO", "31/02/2023"),
                           ("AGGIORNATO", "21/10/2026"), ("Nome_Mercato", "Nuovo �")]:
            body = csv_with(lambda rows: rows[0].update({key: value}), encoding="utf-8")
            parsed = source.parse_csv(body, read_at=READ_CSV)
            self.assertEqual(len(parsed["held_rows"]), 1)
            self.assertEqual(len(parsed["rows"]), 69)
            self.assertEqual(parsed["held_rows"][0]["raw_fields"][key], value)

    def test_schema_width_and_size_changes_fail_closed(self):
        for blob in (CSV.replace(b" AGGIORNATO", b" UNREVIEWED"),
                     CSV.replace(b"Note_orari", b" AGGIORNATO"),
                     CSV + b"a;b;c\n", b"a" * (source.MAX_CSV_BYTES + 1)):
            with self.assertRaises(ValueError):
                source.parse_csv(blob, read_at=READ_CSV)
        with self.assertRaises(ValueError):
            source.select_distribution(b"a" * (source.MAX_METADATA_BYTES + 1), read_at=READ_METADATA)

    def test_utf8_is_supported_without_replacement_decoding(self):
        body = CSV.decode("cp1252").encode("utf-8")
        parsed = source.parse_csv(body, read_at=READ_CSV)
        self.assertEqual(parsed["encoding"], "utf-8")
        self.assertEqual(parsed["rows"], source.parse_csv(CSV, read_at=READ_CSV)["rows"])

    def test_raw_snapshot_hash_url_read_time_and_latest_resource_are_bound(self):
        for kind, key, value in [("csv", "sha256", "0" * 64), ("csv", "bytes", 1),
                                 ("csv", "url", source.DATASET_PAGE),
                                 ("metadata", "read_at", "2026-10-20T17:30:00+00:00"),
                                 ("csv", "read_at", "2026-10-21T00:00:00+00:00"),
                                 ("csv", "read_at", "2026-10-20T17:17:02")]:
            item = snapshot()
            item[kind][key] = value
            with self.subTest(key=key), self.assertRaises(ValueError):
                source.parse_snapshot(item, today=TODAY)
        with self.assertRaisesRegex(ValueError, "stale"):
            source.parse_snapshot(snapshot(), today=date(2027, 1, 1))

    def test_failed_acquisition_stops_before_csv_and_creates_no_fresh_snapshot(self):
        seen = []
        def fetch(url):
            seen.append(url)
            raise OSError("offline test")
        with self.assertRaises(OSError):
            source.acquire(today=TODAY, fetch=fetch)
        self.assertEqual(seen, [source.METADATA_URL])

    def test_transport_blocks_private_or_empty_dns_and_unknown_urls_before_network(self):
        for answers in ([], [(2, 1, 6, "", ("127.0.0.1", 443))]):
            with patch.object(source.socket, "getaddrinfo", return_value=answers), \
                 patch.object(source, "build_opener") as opener:
                with self.assertRaisesRegex(ValueError, "DNS"):
                    source.fetch_public(source.METADATA_URL)
                opener.assert_not_called()
        with self.assertRaisesRegex(ValueError, "Unapproved"):
            source.fetch_public("https://example.invalid/file.csv")

    def test_transport_accepts_actual_csv_mime_and_enforces_response_boundaries(self):
        headers = Message()
        headers["Content-Type"] = "text/x-comma-separated-values"
        headers["Content-Length"] = str(len(CSV))
        response = MagicMock()
        response.__enter__.return_value = response
        response.status = 200
        response.geturl.return_value = CAPTURES[1]["requested_url"]
        response.headers = headers
        response.read.return_value = CSV
        with patch.object(source.socket, "getaddrinfo", return_value=[(2, 1, 6, "", ("8.8.8.8", 443))]), \
             patch.object(source, "build_opener") as opener:
            opener.return_value.open.return_value = response
            self.assertEqual(source.fetch_public(CAPTURES[1]["requested_url"]), CSV)
            response.read.assert_called_with(source.MAX_CSV_BYTES + 1)
            response.geturl.return_value = "https://example.invalid/redirected.csv"
            with self.assertRaises(ValueError):
                source.fetch_public(CAPTURES[1]["requested_url"])


if __name__ == "__main__":
    unittest.main()
