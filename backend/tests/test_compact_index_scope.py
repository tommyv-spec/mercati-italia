"""The small index qualifies source-specific hours without editing the facts."""
from copy import deepcopy
from datetime import timedelta
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from compact_index import index_fields, index_options, project_index
from export_static import _write_asset, compact_json, export
from validate_static import validate
from autopilot import index_payload_changed
from audit_dataset import audit
from eventiesagre_detail_refresh import preview
import happings_detail_enrichment
from test_eventiesagre_detail_refresh import TODAY, document, html, row
from test_happings_detail_enrichment import observed_page


class CompactIndexScopeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.out = Path(self.temp.name) / "public/data/v1"

    def editorial(self, *, past=True):
        source = document(html(start="01/01/2018" if past else "01/01/2026",
            end="31/12/2018" if past else "31/12/2026", archived=past))
        return preview([row(orario_testo="20:00–20:00")], [source], today=TODAY)[0][0]

    def test_old_edition_read_today_qualifies_hours_without_modifying_any_fact(self):
        record = self.editorial()
        original = deepcopy(record)
        values = project_index([record], schema=6, today=TODAY)[0]
        self.assertEqual(values[12], "storico")
        self.assertEqual(values[9], "20:00–20:00")
        self.assertEqual(len(values), 13)
        self.assertEqual(record, original)
        self.assertNotIn(record["evidenza_editoriale"], values)

    def test_real_lana_christmas_eve_hours_require_the_source_calendar(self):
        records, _ = happings_detail_enrichment.preview([], [observed_page("lana")],
            today=TODAY, apply=True, admit_new=True)
        self.assertEqual(len(records), 1)
        record = records[0]
        christmas = [v for v in record["calendario_fonte"]["occorrenze"] if v["date"] == "2026-12-24"]
        self.assertEqual(len(christmas), 1)
        self.assertEqual(christmas[0]["end_time"], "13:00")
        self.assertEqual(project_index(records, schema=6, today=TODAY)[0][12], "per_data")
        self.assertEqual(project_index(records, schema=6, today=TODAY)[0][9], record["orario_testo"])

    def test_invalid_source_identity_never_creates_a_historical_hint(self):
        record = self.editorial()
        record["evidenza_editoriale"]["market"]["slug"] = "another-market"
        with self.assertRaisesRegex(ValueError, "bound editorial"):
            project_index([record], schema=6, today=TODAY)
        ordinary = row(ambito_orari="storico")
        self.assertEqual(project_index([ordinary], schema=6, today=TODAY)[0][12], "")

    def test_historical_asset_validation_uses_declared_day_not_validation_day(self):
        record = self.editorial(past=False)
        expected = project_index([record], schema=6, today=TODAY)
        self.assertEqual(expected[0][12], "per_data")
        future_classification = project_index([record], schema=6, today=TODAY + timedelta(days=500))
        self.assertEqual(future_classification[0][12], "storico")
        manifest = {"index_schema": 6, "index_as_of": TODAY.isoformat()}
        self.assertEqual(project_index([record], **index_options(manifest)), expected)
        for value in (None, "2026-02-31", "20261020", "2026-10-20T00:00:00Z"):
            with self.subTest(day=value), self.assertRaises(ValueError):
                index_options({"index_schema": 6, "index_as_of": value})

    def test_export_upgrades_v5_index_with_identical_regional_facts_and_is_idempotent(self):
        record = self.editorial()
        first = export([record], self.out, today=TODAY)["manifest"]
        public = self.out.parent.parent
        regional_before = (public / first["catalog"]).read_bytes()
        old = {**first, "index_schema": 5,
               "index": _write_asset(self.out, "index-{hash}.json", project_index(
                   json.loads(regional_before)["markets"], schema=5))}
        old.pop("index_as_of")
        (self.out / "manifest.json").write_bytes(compact_json(old))
        self.assertEqual(validate(self.out / "manifest.json")["records"], 1)
        self.assertEqual(audit(self.out / "manifest.json", today=TODAY)["snapshot_total"], 1)
        upgraded = export([record], self.out, today=TODAY)
        current = upgraded["manifest"]
        self.assertFalse(upgraded["unchanged"])
        self.assertEqual(current["index_schema"], 7)
        self.assertEqual(current["content_signature"], old["content_signature"])
        self.assertEqual(current["catalog"], old["catalog"])
        self.assertEqual((public / current["catalog"]).read_bytes(), regional_before)
        self.assertTrue(index_payload_changed(old, current))
        self.assertEqual(validate(self.out / "manifest.json")["records"], 1)
        self.assertEqual(audit(self.out / "manifest.json", today=TODAY)["snapshot_total"], 1)
        again = export([record], self.out, today=TODAY)
        self.assertTrue(again["unchanged"])
        self.assertFalse(index_payload_changed(current, again["manifest"]))
        self.assertFalse(index_payload_changed(current, {**current, "index_as_of": "2026-10-21"}))

    def test_static_validation_rejects_a_forged_scope_even_with_a_new_correct_asset_hash(self):
        manifest = export([row()], self.out, today=TODAY)["manifest"]
        public = self.out.parent.parent
        values = json.loads((public / manifest["index"]).read_text())["markets"]
        values[0][12] = "storico"
        manifest["index"] = _write_asset(self.out, "index-{hash}.json", values)
        (self.out / "manifest.json").write_bytes(compact_json(manifest))
        with self.assertRaisesRegex(ValueError, "index differs"):
            validate(self.out / "manifest.json")

    def test_same_regional_facts_get_a_historical_flag_after_the_last_edition_day(self):
        source = document(html(start="01/01/2026", end="20/10/2026", archived=False))
        record = preview([row(date=[])], [source], today=TODAY)[0][0]
        first = export([record], self.out, today=TODAY)["manifest"]
        public = self.out.parent.parent
        before = (public / first["catalog"]).read_bytes()
        self.assertEqual(json.loads((public / first["index"]).read_text())["markets"][0][12], "per_data")
        second = export([record], self.out, today=TODAY + timedelta(days=1))
        after = second["manifest"]
        self.assertFalse(second["unchanged"])
        self.assertEqual(after["content_signature"], first["content_signature"])
        self.assertEqual(after["catalog"], first["catalog"])
        self.assertEqual((public / after["catalog"]).read_bytes(), before)
        self.assertEqual(json.loads((public / after["index"]).read_text())["markets"][0][12], "storico")
        self.assertTrue(index_payload_changed(first, after))
        self.assertEqual(validate(self.out / "manifest.json")["records"], 1)
        third = export([record], self.out, today=TODAY + timedelta(days=2))["manifest"]
        self.assertEqual(third["index"], after["index"])
        self.assertNotEqual(third["index_as_of"], after["index_as_of"])
        self.assertFalse(index_payload_changed(after, third), "Reference day alone is not new content")

    def test_versions_four_to_seven_have_exact_distinct_shapes(self):
        record = row()
        for schema in (4, 5):
            values = project_index([record], schema=schema)
            self.assertEqual(len(values[0]), 12)
            self.assertEqual(index_options({"index_schema": schema}), {"schema": schema, "today": None})
        self.assertEqual(len(index_fields(6)), 13)
        self.assertEqual(index_fields(7)[-1], "duplicato_di")
        self.assertEqual(project_index([record], schema=7, today=TODAY)[0][13], "")
        for schema in (None, 3, 8, True, "6"):
            with self.subTest(schema=schema), self.assertRaises(ValueError):
                index_fields(schema)


if __name__ == "__main__":
    unittest.main()
