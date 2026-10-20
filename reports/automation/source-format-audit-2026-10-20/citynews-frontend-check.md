# Citynews: evidence in the existing detail interface

Checked on 2026-10-20 against the exported captured-source candidate. This is
an offline display replay, not a new source acquisition or publication.

## Completed checks

- [x] The detail interface now admits the same 28 reviewed Citynews origins
  and exact event-detail paths as the backend. Indexes, location pages,
  credentials, queries, fragments, ports, redirects and unreviewed hosts do
  not become Citynews evidence links.
- [x] The source ID is independently derived from the exact URL, using the
  same bounded ASCII SHA-256 identity as the backend. Tests compare all
  reviewed origins, the 27 captured fixture URLs and padding boundaries
  against Node's native crypto implementation.
- [x] Full regional JSON, the existing React adapter and the display model
  preserve the editorial proof and the original municipality/province/region.
- [x] Read dates remain separate from declared publication dates. A read of
  an old edition does not become a current opening, a content modification
  date or a human verification.
- [x] Partial hours, date-specific hours and programme qualifications remain
  scoped. Missing per-date hours do not inherit global market hours. Calendar
  conflicts and cancellations suppress opening claims.
- [x] Authoritative calendar exceptions also override the editorial detail
  list; an exception within an interval appears on that interval.
- [x] New Citynews field receipts bind the exact source URL, source ID,
  event-card row, raw hash and saved field values. Other sources retain their
  existing receipt behavior.

## Actual exported candidate

The candidate has **13,856 identities**. All **11 Citynews editorial proofs**
survive the complete static-loader → React-adapter → display-model path.
All **11 describe past editions** and receive historical labels. No unlisted
future date receives global hours. This replay reads eight existing static
catalog files and makes **zero HTTP requests**. Full observations, source
hashes and original publication/read dates are in `citynews-frontend-replay.json`.

Validation: all 11 Node test files pass; the focused Citynews file contains
nine passing semantic tests. The production Vite build passes. No backend,
published catalog, remote branch or workflow was changed by this patch.

## Scope remaining outside this check

The UI does not repair held source joins or infer current opening dates from
past editions. Live acquisition and publication remain the existing pipeline's
responsibility. These display checks do not claim that all 57 configured
Citynews URLs were read successfully.
