"""A saved response is identified by bounded bytes, not a gzip runtime header."""
import base64
from copy import deepcopy
from datetime import date
import gzip
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from urllib.robotparser import RobotFileParser

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import eventiesagre_detail_refresh as editorial
import happings_detail_autopilot as happings
import happings_detail_discovery as discovery
from test_eventiesagre_detail_refresh import html, row, URL

TODAY = date(2026, 10, 20)
PISA = "https://www.happings.com/it/happing/mercato-coperto-campagna-amica-di-pisa/"


def encode(body, *, os_byte=255, compresslevel=9):
    compressed = bytearray(gzip.compress(body, mtime=0, compresslevel=compresslevel))
    compressed[9] = os_byte
    return base64.b64encode(compressed).decode("ascii")


class CheckpointCompressionPortabilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.editorial_page = {"requested_url": URL, "final_url": URL,
            "read_on": TODAY.isoformat(), "redirects": [], "redirect_observed": False,
            "body": html()}
        cls.editorial_entry = editorial._pack(cls.editorial_page)
        cls.happings_body = (Path(__file__).parent / "fixtures/happings_detail/pisa.html").read_bytes()
        initial = discovery.seed_state(seed_urls=[PISA], observed_at=TODAY)
        robots = RobotFileParser()
        robots.parse(["User-agent: *", "Disallow:"])
        state, pages, acquisition = discovery.acquire(initial, today=TODAY, max_requests=1,
            max_seconds=420, robots=robots, fetcher=lambda url, **kw: (cls.happings_body, url),
            sleep=lambda _: None, clock=lambda: "2026-10-20T12:00:00+00:00")
        cls.context = {"baseline_signature": "unchanged-baseline", "policy_sha256": "unchanged-policy",
                       "date": TODAY.isoformat(), "details_policy": {"max_seconds": 420}}
        cls.happings_saved = {"schema": 1, "status": "completed", "context": cls.context,
            "pages": [happings._pack(page, today=TODAY) for page in pages],
            "state": state, "discovery": acquisition}

    def read(self, kind, entry):
        if kind == "editorial":
            return editorial._unpack(entry, today=TODAY)["body"]
        saved = deepcopy(self.happings_saved)
        saved["pages"] = [entry]
        return happings._unpack(saved, self.context, today=TODAY, max_requests=1)[1][0]["html"]

    def cases(self):
        return [("editorial", deepcopy(self.editorial_entry), "body_gzip_base64", self.editorial_page["body"]),
                ("happings", deepcopy(self.happings_saved["pages"][0]), "html_gzip_base64", self.happings_body)]

    def test_os_3_and_255_and_different_compression_levels_preserve_exact_evidence(self):
        for kind, original, key, body in self.cases():
            for os_byte in (3, 255):
                for level in (1, 9):
                    with self.subTest(kind=kind, os_byte=os_byte, compression=level):
                        entry = {**original, key: encode(body, os_byte=os_byte, compresslevel=level)}
                        self.assertEqual(self.read(kind, entry), body)
                        self.assertEqual(entry["sha256"], original["sha256"])
                        self.assertEqual(entry["bytes"], original["bytes"])

    def test_changed_body_hash_or_byte_count_is_rejected(self):
        for kind, original, key, body in self.cases():
            for mutation in ("body", "hash", "byte_count", "non_integer_byte_count"):
                entry = deepcopy(original)
                if mutation == "body":
                    entry[key] = encode(body + b"changed")
                elif mutation == "hash":
                    entry["sha256"] = "0" * 64
                elif mutation == "byte_count":
                    entry["bytes"] += 1
                else:
                    entry["bytes"] = float(entry["bytes"])
                with self.subTest(kind=kind, mutation=mutation), self.assertRaises(ValueError):
                    self.read(kind, entry)

    def test_truncated_gzip_corrupt_crc_and_invalid_deflate_are_rejected(self):
        for kind, original, key, body in self.cases():
            compressed = base64.b64decode(encode(body))
            bad_crc = compressed[:-8] + bytes([compressed[-8] ^ 1]) + compressed[-7:]
            invalid_deflate = compressed[:10] + b"\xff" * 20 + compressed[-8:]
            for label, payload in [("truncated", compressed[:-1]), ("crc", bad_crc),
                                   ("deflate", invalid_deflate)]:
                entry = {**original, key: base64.b64encode(payload).decode("ascii")}
                with self.subTest(kind=kind, mutation=label), self.assertRaises(ValueError):
                    self.read(kind, entry)

    def test_oversized_decompressed_response_is_rejected_before_full_inflation(self):
        for kind, original, key, body in self.cases():
            entry = {**original, key: encode(b"x" * (len(body) * 10))}
            module, bound = ((editorial, "MAX_BYTES") if kind == "editorial"
                             else (happings.weekly, "MAX_RESPONSE_BYTES"))
            with self.subTest(kind=kind), patch.object(module, bound, len(body)), self.assertRaises(ValueError):
                self.read(kind, entry)

    def test_missing_or_extra_metadata_is_rejected(self):
        for kind, original, key, body in self.cases():
            for mutation in ("extra", "missing"):
                entry = deepcopy(original)
                if mutation == "extra":
                    entry["unobserved_claim"] = "trusted"
                else:
                    del entry["sha256"]
                with self.subTest(kind=kind, mutation=mutation), self.assertRaises(ValueError):
                    self.read(kind, entry)

    def test_source_url_redirect_or_day_cannot_change_with_portable_encoding(self):
        for kind, original, key, body in self.cases():
            for mutation in ("foreign_url", "unobserved_redirect", "stale_read"):
                entry = {**original, key: encode(body, os_byte=255, compresslevel=1)}
                if mutation == "foreign_url":
                    entry["requested_url"] = "https://example.org/unobserved-market"
                elif mutation == "unobserved_redirect":
                    entry["final_url"] = "https://example.org/unobserved-market"
                else:
                    entry["read_on" if kind == "editorial" else "fetched_at"] = (
                        "2026-10-19" if kind == "editorial" else "2026-10-19T12:00:00+00:00")
                with self.subTest(kind=kind, mutation=mutation), self.assertRaises(ValueError):
                    self.read(kind, entry)

    def test_happings_still_requires_original_context_frontier_and_unique_pages(self):
        for mutation in ("baseline", "policy", "day", "frontier_hash", "duplicate_page"):
            saved = deepcopy(self.happings_saved)
            saved["pages"][0]["html_gzip_base64"] = encode(self.happings_body, os_byte=255)
            if mutation in {"baseline", "policy", "day"}:
                field = {"baseline": "baseline_signature", "policy": "policy_sha256", "day": "date"}[mutation]
                saved["context"][field] = "changed"
            elif mutation == "frontier_hash":
                saved["state"]["resources"][PISA]["last_sha256"] = "0" * 64
            else:
                saved["pages"].append(deepcopy(saved["pages"][0]))
            with self.subTest(mutation=mutation), self.assertRaises(ValueError):
                happings._unpack(saved, self.context, today=TODAY, max_requests=1)

    def test_editorial_queue_rejects_repeated_pages_even_with_valid_portable_bodies(self):
        entry = {**self.editorial_entry,
                 "body_gzip_base64": encode(self.editorial_page["body"], os_byte=255)}
        page = editorial._unpack(entry, today=TODAY)
        state = editorial.seed_state([row()], today=TODAY)
        with self.assertRaisesRegex(ValueError, "repeated a successful response"):
            editorial._verify_checkpoint_state(state, state, [], [page, page], today=TODAY)


if __name__ == "__main__":
    unittest.main()
