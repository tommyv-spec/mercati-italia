import test from 'node:test'
import assert from 'node:assert/strict'
import { guardVisitorRelease } from '../scripts/reversible-display-release-guard.mjs'

function sample(dup, count=14007, malformed=2) {
  return {
    schema: 1, review_only: true, display_grouping_only: true,
    market_data_modified: false,
    metrics: {
      original_records: count, ids_retained: count,
      suppressed_repeat_buttons_only: dup,
      original_records_in_reversible_groups: dup * 2,
      malformed_source_city_labels_guarded_in_ui: malformed,
      market_identities_deleted: 0, event_confirmations_created: 0,
      verification_claims_created: 0,
    },
  }
}
const quality = (count=14007, suspicious=2) => ({
  schema: 1, review_only: true,
  quality_release_safe: true, quality_regressions: [],
  metrics: {total: count, suspicious_city: suspicious},
})

test('historical report may lag, but identical published DEV and candidate never regress', () => {
  const result = guardVisitorRelease(sample(1008), sample(1008), quality(),
    {metrics: {suppressed_repeat_buttons_only: 699}})
  assert.equal(result.source, 'actual_published_dev_static_catalog')
  assert.equal(result.newly_observed_repeats, 0)
  assert.equal(result.historical_scorecard_stale, true)
  assert.equal(result.historical_scorecard_repeats, 699)
  assert.equal(result.published_suppressed_repeats, 1008)
})

test('candidate with new unsupported display groups still blocks', () => {
  assert.throws(
    () => guardVisitorRelease(sample(1008), sample(1500), quality(),
      {metrics: {suppressed_repeat_buttons_only: 699}}),
    /Newly introduced display duplicates/,
  )
})

test('suspicious municipality changes and identity deletion cannot be hidden by stale history', () => {
  assert.throws(() => guardVisitorRelease(sample(1008), sample(1008,14007,14), quality(14007,14)),
    /malformed municipality/)
  const missing = sample(1008)
  missing.metrics.ids_retained = 14006
  assert.throws(() => guardVisitorRelease(sample(1008), missing, quality()), /source identities/)
})

test('QA cannot approve a candidate previously rejected by independent catalog gate', () => {
  assert.throws(() => guardVisitorRelease(sample(1008), sample(1008), {
    ...quality(), quality_release_safe:false, quality_regressions:[{code:'unreviewed'}],
  }), /Unreviewed source/)
})

test('row count changes only when all new identifiers are retained', () => {
  const v = guardVisitorRelease(sample(1008), sample(1010,14012), quality(14012))
  assert.equal(v.candidate_records, 14012)
  assert.equal(v.newly_observed_repeats, 2)
  assert.equal(v.historical_scorecard_stale, false)
})
