# Publisher page parser fixtures

These two structural HTML fixtures exercise the generic, offline parser in
`backend/publisher_page_parser.py`. They preserve the factual market values and
the relevant layout of the original publisher pages, including headings, labels,
line breaks, fractions and alternative locations. Editorial prose, images and
contact text have been omitted. They are regression inputs, not a registry of
manual changes to catalog records.

| Fixture | Source updated | Whole-page replay |
| --- | --- | --- |
| `bassa-romagna-weekly.html` | 2026-03-23 | 20 rows, 9 municipality blocks, 7 fraction rows |
| `bassa-romagna-farmers.html` | 2026-01-27 | 6 rows, 6 municipality blocks |

The source URLs and acquisition date, 2026-10-19, are recorded in
`html-fixture-provenance.json`. Its `sha256` values identify the exact structural
fixture bytes committed here. The separate `original_source_sha256` values
identify the original acquired HTML bytes. The fixture is explicitly classified
as `structural_factual_fixture`; its hash does not claim to identify an unchanged
publisher page. Full original HTML is retained only as temporary replay input.
Acquisition dates and explicit publisher update dates describe different events.

The original HTML and the reduced fixtures produced the same identities,
locations, weekdays, numeric and seasonal hours, cadence, ambiguity flags and
publisher update dates for all 26 extracted rows. The fixtures retain these
important cases:

- Conselice has central-town and Lavezzola markets on Saturday, so a municipality
  and weekday alone do not identify one venue.
- Cotignola expresses alternative venues using `e/o`; these remain alternatives
  in one source row rather than becoming invented separate markets.
- Farmers markets have their own market kind. Explicit seasonal hour ranges
  remain separate, and Sant'Agata sul Santerno retains its fortnightly cadence.
- `Mattina` is qualitative information and does not supply numeric opening hours.

The tests cover every extracted row, changes in source addresses and hours with
stable source identity, layout variations, ignored page noise and incomplete or
ambiguous input. They do not infer whether a future edition will open.

Run the focused suite from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s backend/tests -p 'test_publisher_page_parser.py'
```
