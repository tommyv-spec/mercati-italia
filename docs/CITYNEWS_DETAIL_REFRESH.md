# Existing Citynews event details

This reader handles existing primary detail URLs on the 28 Citynews origins
reviewed in the source-format audit. The current catalog contains **57 exact
detail URLs for 62 records**. Event indexes, tag indexes and news articles
(another 30 catalog records) are outside this adapter.

## Factual scope

`citynews_layout.parse_detail()` reads the unique primary event article. The
header's **Dove** and **Quando** cards supply address, hours and edition bounds;
one matching head `Event` corroborates title, dates and an explicit municipality.
The visible address must agree with its schema address. A schema organizer URL
does not replace the page URL. Footer contacts, navigation, related events and
programme times cannot supply these fields.

The parser preserves partial and qualified hours. It does not invent closing
times, daily openings inside an interval, an annual recurrence, or a year from
the current date or URL. Equal/reversed clock endpoints, accessory programme
hours and conflicting edition years stay held. Reading an old edition retains
historical facts and cannot recertify current address or hours. Publication,
source modification and real acquisition dates remain distinct; the observed
template does not provide a verified modification date.

`citynews_detail_enrichment` binds the existing primary URL, exact normalized
title and ISTAT municipality/province/region. It preserves the raw observed
location separately. It cannot rename a record, repair geography, add IDs,
replace an independent calendar or overwrite unowned values. A changed edition
on a previously bound URL is held. Managed field updates require a later read,
changed source bytes, stable edition and an ownership receipt without competing
manual or source evidence.

## Recurring phase contract

`citynews_detail_refresh.run()` has the same caller pattern as the existing
editorial reader:

```python
candidate, report, preserve_ids = run(
    rows, out=checkpoint_directory, today=today,
    baseline_signature=baseline_signature, policy_digest=policy_digest,
    policy=validate_policy(), previous_state=published_state,
    offline=False, resume=False, deadline=existing_shared_deadline,
)
```

Default and maximum allowances are **8 total HTTP attempts** and **60 seconds
of transport time**. Robots, failures and detail requests all consume the same
request cap. The caller's existing deadline can only shorten the allowance.
The fixed local Python transport worker can be killed and reaped on expiry
even while DNS, TLS, headers or response body reads are blocked. There is no
retry, redirect follow, extra service or dependency. Failed requests respect
the same per-host pacing as successful reads.

The phase returns `report["state"]`, also written to
`citynews-detail-state.json`. The orchestrator must validate and persist this
file in the candidate data directory. The queue uses exact catalog URLs and
advances through unattempted resources before starting another cycle. A timeout
before a detail request remains unfinished; it is not a fabricated failed read
or a completed cycle. A successful HTTP response with an unsupported layout is
a read, but does not count as a successful extraction.

The report filename is `citynews-detail-refresh.json`. Its acquisition fields
match the existing editorial report convention:

- `attempts`, with exact URL, status and `network_attempted` for detail HTTP;
- `source_pages`, with requested/final URL, actual `read_on`, bytes and SHA256;
- `source_pages_read`, `documents_parsed`, `parse_holds` and `progress`;
- `evidence`, consumed by `verify_changes()` and `verify_exported()`;
- `network_requests`, zero during offline checkpoint resume, and
  `captured_network_requests` for the earlier saved acquisition.

Raw HTML and robots remain in the temporary response checkpoint, with bounded
decompression, byte/hash validation and exact baseline/policy/day/queue binding.
Gzip operating-system header differences are permitted; changed decompressed
bytes, extra fields, duplicate URLs, forged counts or reordered robots/detail
proofs are rejected. Resume reparses the actual saved bytes without HTTP.

The shared `editorial_calendar_scope.source_identity()` delegates only the exact
Citynews URL grammar to `citynews_urls`. Existing exporter and frontend hooks
can therefore retain `evidenza_editoriale`; no new public evidence schema is
introduced. `existing_source_refresh` dispatches this reader as the `citynews`
member of its editorial report and runs it concurrently with EES and Cose di Casa.
Its 60-second allowance stays inside the existing shared 360-second deadline;
the MAIN job's 20-minute timeout is unchanged. The explicit configuration lives
under `existing_source_refresh.citynews` in `autopilot_policy.json`.

The normal Autopilot exports the validated queue into its candidate, protects it
from obsolete-asset pruning, and compares that actual exported file with the
source report in the final guard. The existing MAIN publisher remains the only
writer to DEV. Coverage uses only exact reviewed detail URL shapes and reports
current acquisition separately from parsed content and per-record outcomes.
An observed unsupported template remains unsupported on subsequent unselected
or offline passes, even though its reader route is configured. A failed join is
not a failed HTTP response, and neither signifies a confirmed market opening.
This change does not modify the links-only event research registry or any
catalog data file. Activation in the remote recurring job follows publication
of the reviewed code; a local captured-byte replay is not a live source refresh.

## Evidence reviewed

The 2026-10-20 bounded capture visited the 28 already inventoried samples with
robots checks. It obtained 27 HTML responses; Padova failed before detail HTTP.
The fixture manifest records the distinct hashes of the original HTTP bytes
and of the factual DOM excerpts. Full articles and publisher contacts are not
copied into fixtures. Raw and excerpt parser results are equal.

The full-catalog replay retains 13,856 identities and adds only 11 historical
evidence objects. The other 19 record joins remain held: 13 catalog/source
geography mismatches, 2 records without an explicit source municipality, 2
changed titles, 1 unsupported Lecco detail variant and 1 Viterbo redirect to a
different February edition. No current address, hours, dates or confirmation
is changed by these samples. This is extraction and provenance coverage, not
an assertion that every source event is current or independently confirmed.
