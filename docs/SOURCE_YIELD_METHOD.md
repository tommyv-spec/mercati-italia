# Source yield: quantity + quality, without inventing markets

This audit measures *source usefulness*, not market truth. Its output
is an aggregate daily checkpoint and a bounded manual-review queue.

## Real observed baseline (12 October 2026)

- Original static catalog: 13,779 stable IDs across 20 regions.
- Source registry: 43 declared candidate datasets (many are duplicates,
  historic aggregate statistics, or stall/concession inventories).
- Test with vetted municipal Bologna adapter: 48 source entries.
- Bologna source content date: 2025-04-02. This is stale; today's
  retrieval and CKAN metadata change do NOT renew the market schedule.
- Original source IDs are not present in the catalog: 48. This alone
  does not prove distinct places.
- Exact conservative matching by Comune, normalized street, market name
  and supported weekday: 47 *possible* distinct venue candidates and
  1 unresolved overlap. All require fresh confirmation.
- Roma 2022 historical inventory and Piemonte archive endpoint timed
  out on the authorized PC during read-only checks. Treat these as
  unmeasured, never as zero potential candidates.
- Zero markets imported or verified by this audit.

## Repeatable method

1. Load the current static manifest and source registry; keep every ID.
2. Reject duplicate IDs, malformed probes or registry sources.
3. Remove misleading source categories from the growth queue:
   aggregate statistics, concession lists, stall counts, and feeds with
   an existing active adapter. These are NOT net-new catalogs.
4. Optionally use the already-reviewed, bounded Bologna adapter to
   inspect at most 65 records with a pinned source URL and date.
5. Compare actual rows without fuzzy merges. A title+address+weekday
   match is a strong *review lead*, not authority to overwrite the
   published listing. An unmatched ID is only a candidate.
6. Rank the remaining sources by actionable evidence, not dataset
   metadata modification date. Roma requires newer corroboration.
   Piemonte needs a working official endpoint. The ranked queue
   never grants import permission.
7. Publish only aggregate metrics and at most eight source IDs per
   review category. Do not persist full upstream vendor records.
8. Before any future importer: check publisher and distribution license,
   current place and timetable evidence, source row fingerprint,
   ID stability, overlap, rollback, all CI, and mobile. Schedule
   publication on DEV only.

## Commands

Offline without external downloads:

    python backend/source_yield_audit.py \
      --manifest public/data/v1/manifest.json \
      --registry reports/automation/source-registry.json \
      --municipalities reports/automation/municipality-coverage.json \
      --probes reports/automation/source-probes.json \
      --out /tmp/source-yield.json \
      --report /tmp/SOURCE_YIELD.md

For a bounded source-level observation, add --live-bologna. This
contacts only the pre-reviewed Bologna adapter endpoint. An unreachable
official feed yields an explicit unavailable status, not fabricated 0.

    python -m unittest discover -s backend/tests -q

## Automatic guardrails

- sources_imported == 0
- markets_added == 0
- markets_deleted == 0
- market_rows_edited == 0
- market_events_confirmed == 0
- official_license_verified_automatically == 0
- catalog_market_ids_retained == the published manifest total
- source scores and new source IDs are never market confirmations
- if live observation fails, unknown candidate counts remain null
- all long-term outputs are aggregate, not individual vendor data
- separate QA and read-only reporting jobs run outside Cloudflare
- no Firestore, Workers, D1 or KV reads occur during public browsing

Next stage, once new evidence is found: run a per-source adapter
in a dry-run with a bounded overlap report. Auto-publish only when
all source-specific tests pass and the publisher/license is approved.
