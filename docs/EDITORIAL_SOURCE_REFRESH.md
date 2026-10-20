# Existing editorial source refresh

This phase reads the Eventi e Sagre and Cose di Casa primary URLs already
attached to catalog records. It preserves the existing IDs and geography,
stores attributable factual evidence, and limits predictions to what the
source actually supports. It does not discover or admit new markets.

The separate Eventi e Sagre links-only research registry remains unchanged.
The policy for this phase records the user's instruction to automate factual
extraction from existing sources; it makes no claim of authenticated publisher
reuse rights. No article bodies, publisher images, or raw HTML are published.

## Components and API

- `backend/eventiesagre_detail_refresh.py` contains the bounded acquisition
  queue, adapters to the common fact envelope, exact existing-record join,
  field ownership updates, and semantic candidate/export guards.
- `backend/editorial_calendar_scope.py` validates `evidenza_editoriale` and
  preserves its edition limits through recurrence refresh and export.
- `backend/cosedicasa_layout.py` reads scoped structured CDC fields. EES uses
  the existing `eventiesagre_source_layout.py` reader.
- `backend/existing_source_refresh.py` coordinates the two publishers,
  combines only disjoint changes, persists validated state in the candidate,
  and verifies the final exported records.
- `backend/data/editorial-detail-refresh-policy.json` defines the actual
  operational limits. All modules use the Python standard library.

The reader entry point is:

```python
rows, report, preserve_ids = run(
    rows, out=temporary_output, today=today,
    baseline_signature=baseline_signature, policy_digest=policy_digest,
    publisher="eventiesagre.it", policy=validate_policy(publisher="eventiesagre.it"),
    previous_state=previous_state, deadline=shared_monotonic_deadline,
    offline=False, resume=False,
)
```

`verify_changes(before, after, report["evidence"], today=today)` reconstructs
the candidate from the captured source documents. `verify_exported` then
reconstructs each retained source fact and checks accepted values, receipts,
IDs, and calendar limits against the final export. Recomputing a row hash
does not authorize a different value or edition.

## Request budget and progress

| Publisher | Maximum detail URLs per cycle batch | Maximum acquisition time | Persistent queue |
| --- | ---: | ---: | --- |
| Eventi e Sagre | 64 | 210 seconds | `eventiesagre-detail-state.json` |
| Cose di Casa | 16 | 90 seconds | `cosedicasa-detail-state.json` |

The two hosts run concurrently against the same baseline. Each has its own
robots request, minimum two-second pacing, publisher-specified delay, queue,
temporary response checkpoint, and elapsed-time limit. A shared deadline can
shorten either allowance. Up to two actual same-publisher redirects are
recorded as ordered HTTP hops. EES must retain the numeric source identity
through every hop; CDC may retain a changed slug only with an observed
transport redirect and matching canonical destination. A canonical tag alone
does not establish a redirect.

Reports are `eventiesagre-detail-refresh.json` and
`cosedicasa-detail-refresh.json`; the orchestrator writes
`existing-source-refresh.json`. Public queues contain URLs, statuses,
read/attempt dates and hashes, not article bodies. Raw responses remain in
temporary `sources/*-detail-pages.json` checkpoints and are reused only when
the date, baseline, policy and prior queue match. Resume makes no network
requests. It cannot advance an unattempted URL or manufacture a successful
read. An empty eligible inventory finishes with `completed/no_catalog_rows`.

Progress distinguishes a complete cycle of **attempts** from a cycle where
**every source was successfully read**. `overdue_urls` uses actual successful
read dates; an unread source remains overdue. Neither metric guarantees that
the market itself is current. Publishing and pruning retain the exact two
queue filenames through the existing candidate publication path.

## Identity, field and calendar rules

The join requires the exact saved primary URL, the source's numeric EES ID or
original CDC identity, observed city/region, and an ISTAT-compatible province.
When the catalog province is blank, the saved city and region must identify
one ISTAT municipality, and the source must also match the exact venue or a
specific compatible title. The catalog province remains unchanged. A
nonempty conflicting province or venue stays held.

Multiple venue rows need an exact saved address and matching explicit
weekdays. Header hours or dates cannot migrate to another venue. A shared
source URL never implies that two catalog IDs are the same market.

Current factual addresses and hours may fill empty values. A nonempty value
can change only when an exact prior receipt proves that this engine assigned
it and a later source version supports the replacement. An unchanged reread
preserves proven ownership; merely observing a preexisting value does not
create ownership. Human verification and precise-location protections remain
in force. Historical edition hours and addresses are retained as evidence,
without being newly promoted as current top-level fields.

`evidenza_editoriale` keeps the original and final source URLs, source hash,
actual read date, separate publication/modification dates, edition bounds,
explicit occurrences, qualifications, source rows and field-specific
conflicts. Reading a page today never supplies a missing content date.

Explicit, conflict-free listed dates can be labeled `riportata`, with an
independent `valid_editorial_reported_dates` proof. They are never labeled
`confermata`. A date range is an edition boundary, not daily opening times.
Unresolved recurrence qualifications or conflicting calendars cannot generate
new dates. An archived edition can withdraw unsupported predictions while
retaining the existing ID; it does not establish permanent closure. Valid
independent calendars and confirmations are preserved.

## Validation and remaining measured checks

`reports/automation/editorial-reader-validation-20261020.json` separates the
five complete CDC HTTP captures from the 17 older EES parsed-fact snapshots.
The older EES connector audit retained source facts and hashes but not
original HTTP bytes, MIME/status, or the actual final transport URL. Those
missing values are not fabricated for a replay or imported into a live queue.

The CDC complete-capture replay was run against both the 13,824-record
checkout and the 13,856-record actual candidate, through disk export, JSON
reload and next-day offline recurrence/export. Existing IDs, source dates and
edition limits survive. Source-body hashes were checked before parsing.
The targeted tests also cover archive retention, multi-venue separation,
calendar conflicts, partial hours, redirects, queue fairness, checkpoint
tampering and three successive managed-field refreshes.

Commands from the repository root:

```sh
PYTHONPATH=backend python -m unittest discover -s backend/tests -p '*eventiesagre*' -q
PYTHONPATH=backend python -m unittest discover -s backend/tests -p test_cosedicasa_layout.py -q
```

The first live candidate must supply the EES HTTP observations that the
historical connector did not expose. Read failures and held joins remain
visible; a successful parser test or a complete attempt cycle does not mark
all source records as verified. Narrative extraction gaps, conflicting
catalog geography and ambiguous multi-venue identities remain separate
tasks in the source-format checklist.
