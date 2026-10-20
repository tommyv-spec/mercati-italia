# Happings provincial local guide: scoped Lucca replay

This is an offline replay of response bytes already acquired by run `39487468359`. It performs no HTTP requests and does not change any public catalog file. The acquisition day remains **2026-10-20**; replaying the capture is not a new reading or a new confirmation of a market.

## Observed failure and scope

| Evidence | Captured value |
| --- | --- |
| Requested URL | `https://www.happings.com/it/mercati-settimanali-a-lucca.html` |
| Observed final URL | `https://www.happings.com/it/mercati-settimanali-a-lucca-e-provincia/` |
| Original HTML SHA-256 | `7da91da612bba4e282f50c0ea254a804d877c1c81bfbf65eaa1b54abe1e9e1fd` |
| Original response length | 146,047 bytes |
| Previous parser result | `layout_changed` |
| Existing primary cards linked to this province resource | 60 |

The response replaced `.happings-seo-content` with a bounded local-guide article: `main#main article.hpe-editorial--local-guide .hpe-editorial-grid > .hpe-editorial-body`. Its header independently names the province. This is a **new DOM variant of the existing provincial URL format**, with a material change in the scope of its sections.

The first section describes updated locations and weekdays for the city. It states two weekdays for Lucca at Piazzale Don Baroni and one appointment at Ponte a Moriano at Piazza del Popolo, each with explicit 08:00–13:00 clocks. The following section is explicitly historical and asks for verification: its **53 list rows have not all been reconfirmed**. Merely adding the new CSS class would incorrectly promote those 53 rows as current observations.

The revised reader preserves **56 source units: three current locality/weekday units and 53 historical units**. The latter retain their source facts, qualifiers and assignment/forecast holds. The current precise clocks are extracted as source facts; the weekly address mechanism does not write those clocks into catalog hours or create dated openings.

## Acceptance criteria

1. Require one recognized main article, the matching explicit province heading and one direct editorial body. Do not infer province identity solely from a URL. Footers, sidebars, related links and non-content elements cannot supply a market row.
2. Only an explicitly current section can support ordinary assignments. Historical, unverified and unmarked sections remain held. A later disclaimer qualifies the whole section. An unparsed competing market statement, including one in an unordered or ordered list without the reviewed weekday heading, holds all otherwise current rows in the same section.
3. Preserve all venues in ambiguity checks. The original city, province, weekday, nonempty-address and managed-field checks still apply. No source absence deletes a card; a historical list does not refresh its source age or generate current dates.
4. Preserve exact clocks and their explicit weekday/locality scope, without importing partial, reversed or equal clock ranges, unknown recurrence grammar, alternative places or an unreviewed municipality qualifier.
5. A saved conflicting address can receive a **negative field warning**, not a replacement, only when the current paragraph explicitly names that exact old address as replaced. Require one source venue for the city/day and one competing catalog identity across the whole catalog, including other publishers and records with conflicting weekday clues. No fuzzy or guessed association is allowed.
6. Keep every original market ID, address, GPS point, date, human-verification field and positive receipt intact. The only expected catalog delta in this capture is two bounded `conflitti_campi` envelopes. The shared UI must qualify the old address and prevent directions; it must not describe the new source address as an independently verified location.
7. Reconstruct the final warnings from the original raw checkpoint at release time. A consistently forged structured document and envelope with an unchanged source hash must fail. The caller supplies the known output directory; a report cannot choose an arbitrary input path. Missing raw bytes fail closed for this new evidence type.
8. Replaying the same capture is idempotent. Later source readings replace only the same ordered warning. Older or same-day conflicting versions and capacity limits stay held; an offline phase preserves existing valid warnings without claiming a new reading.

## Proofs and tests

`backend/tests/fixtures/happings_editorial_weekly_lucca_excerpt.html` is a **factual excerpt with a minimal synthetic wrapper**, not the original response. Its companion JSON retains the original response fingerprint, length, day, URLs and the separate fixture fingerprint. The full replay uses the untouched source checkpoint from the verified artifact.

The targeted suite covers the new section scopes and warning producer, the previous weekly parser, enrichment, field coverage, Happings phase guards and the shared field-conflict validator. It includes the two independent-review regressions: an ignored competing list and a forged document/envelope rejected against the original bytes.

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend:backend/tests python -m unittest \
  test_happings_editorial_weekly test_happings_weekly_layout \
  test_happings_source_enrichment test_happings_field_coverage \
  test_happings_autopilot test_field_conflicts -q
```

The replay command below compares the 14 saved provincial responses with the published parser at `6e58d56c50d29d81d985f1e7617628e23a8f81c7`, then exercises the revised public Happings phase, complete static export/reload and final source guard against all **13,888** records. It freezes the previously captured selection; modern details, legacy discovery and other publishers are deliberately skipped in this focused replay. It is not a new crawl or a full MAIN workflow execution.

```bash
PYTHONDONTWRITEBYTECODE=1 python \
  reports/automation/happings-lucca-layout-validation-20261020/replay.py \
  --repo /workspace/scratch/81e91a77b820/mercati-happings-lucca-repair \
  --artifact /tmp/vintagery-live-39487468359 \
  --output /tmp/happings-lucca-full-replay-20261020
```

`summary.json` records the exact input/output fingerprints, per-page result, scope counts and final guard. `all-60-lucca-comparison.json` enumerates every linked card and its changed field set. Complete before/after warning rows and the raw source checkpoint remain in the replay output for independent review.

## Checklist limits

This proof covers this DOM variant, its explicit historical/current section boundaries, the represented narrow narrative grammar and the 14 acquired provincial pages. It does not authenticate all unvisited provincial layouts, all legacy town redirects, arbitrary prose schedules or future editions. HAPP04/HAPP06 and wider discovery/coverage tasks stay open when their broader acceptance criteria are unmet. Final ledger fingerprints must be recomputed only after integration with index schema 6 and the final shared-helper dependency map; original acquisition dates must remain unchanged.
