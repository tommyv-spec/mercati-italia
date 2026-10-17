"""Only structural XLSX features may leave the temporary source inspection."""
from __future__ import annotations

import io
import json
import sys
import unittest
import zipfile
from datetime import date
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from veneto_event_workbook_probe import analyze, guarded_download, markdown, SOURCE

NS="http://schemas.openxmlformats.org/spreadsheetml/2006/main"

def make_sheet(names,rows=2):
    cells=[]
    for i,n in enumerate(names):
        # use inline strings and explicit column refs
        col=chr(65+i)
        cells.append(f'<c r="{col}3" t="inlineStr"><is><t>{n}</t></is></c>')
    body=''.join(
        f'<row r="{j+4}"><c r="A{j+4}" t="inlineStr"><is><t>'
        f'Private person {j} - private{j}@example.net</t></is></c>'
        f'<c r="B{j+4}" t="inlineStr"><is><t>Comune prova</t></is></c></row>'
        for j in range(rows)
    )
    return (f'<worksheet xmlns="{NS}"><sheetData>'
            f'<row r="1"><c r="A1" t="inlineStr"><is><t>Calendario 2026</t></is></c></row>'
            f'<row r="3">{"".join(cells)}</row>{body}'
            f'</sheetData></worksheet>').encode()

def xlsx(custom=None, sheets=1):
    f=io.BytesIO()
    with zipfile.ZipFile(f,"w",zipfile.ZIP_DEFLATED) as z:
        z.writestr("xl/workbook.xml","<workbook/>")
        for i in range(sheets):
            z.writestr(f"xl/worksheets/sheet{i+1}.xml",
                       custom if custom is not None else make_sheet(
                           ["Manifestazione", "Comune", "Provincia", "Luogo",
                            "Data Inizio", "Data Fine"]))
    return f.getvalue()

class VenetoXLSXSourceTests(unittest.TestCase):
    def test_publisher_headers_found_without_copying_event_rows(self):
        info=analyze(xlsx(), today=date(2026,10,18))
        self.assertEqual(info["sheet_count"],1)
        self.assertEqual(info["workheets"] if "workheets" in info else info["worksheets"][0]["likely_header_row"],3)
        self.assertEqual(info["worksheets"][0]["source_entries_not_new_markets"],2)
        self.assertIn("municipality",info["worksheets"][0]["matched_concepts"])
        self.assertIn("start_date",info["worksheets"][0]["matched_concepts"])
        self.assertEqual(info["market_catalog_imports"],0)
        self.assertEqual(info["event_rows_persisted"],0)
        output=json.dumps(info)+markdown(info)
        self.assertNotIn("private0@example.net",output)
        self.assertNotIn("Private person 0",output)

    def test_multi_sheet_reports_only_bounded_aggregate_schema(self):
        info=analyze(xlsx(sheets=2))
        self.assertEqual(info["sheet_count"],2)
        self.assertEqual(sum(x["nonempty_rows"] for x in info["worksheets"]),8)

    def test_reject_invalid_binary_and_xml_entity_injection(self):
        with self.assertRaisesRegex(ValueError,"ZIP"):
            analyze(b"x"*800)
        xx=make_sheet(["Manifestazione","Comune"]).replace(
            b"<worksheet",b'<!DOCTYPE foo [<!ENTITY x SYSTEM "file:///etc/passwd">]><worksheet',1
        )
        with self.assertRaisesRegex(ValueError,"external entity"):
            analyze(xlsx(custom=xx))

    def test_reject_macro_archive_and_unbounded_sheet_size(self):
        with zipfile.ZipFile(io.BytesIO(xlsx()),"r") as z:
            files={n:z.read(n) for n in z.namelist()}
        f=io.BytesIO()
        with zipfile.ZipFile(f,"w",zipfile.ZIP_DEFLATED) as z:
            for k,v in files.items():
                z.writestr(k,v)
            z.writestr("xl/vbaProject.bin",b"macro")
        with self.assertRaisesRegex(ValueError,"macro"):
            analyze(f.getvalue())
        with self.assertRaisesRegex(ValueError,"unsafe response"):
            analyze(b"J"*2_000_000)

    def test_external_download_url_cannot_be_replaced(self):
        with self.assertRaisesRegex(ValueError,"Unreviewed"):
            guarded_download("https://example.org/official.xlsx")
        self.assertTrue(SOURCE.startswith("https://elezioni2020.regione.veneto.it/"))

if __name__=="__main__":
    unittest.main()
