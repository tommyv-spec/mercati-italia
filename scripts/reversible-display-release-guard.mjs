#!/usr/bin/env node
/**
 * Source-preserving DEV release guard for the visitor's reversible grouping.
 *
 * The previous history file is informational only: it may lag behind the
 * already published catalog. Compare candidate against the real DEV baseline
 * captured from the same immutable checkout, before replacing static assets.
 */
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

function boundedCount(value, name) {
  if (!Number.isInteger(value) || value < 0 || value > 100000) {
    throw new Error('Invalid visitor grouping count: ' + name)
  }
  return value
}

export function guardVisitorRelease(baseline, candidate, catalog, history = null) {
  if (baseline?.schema !== 1 || candidate?.schema !== 1 ||
      baseline.review_only !== true || candidate.review_only !== true ||
      baseline.display_grouping_only !== true || candidate.display_grouping_only !== true ||
      baseline.market_data_modified !== false || candidate.market_data_modified !== false ||
      catalog?.schema !== 1 || catalog.review_only !== true ||
      catalog.quality_release_safe !== true || (catalog.quality_regressions || []).length !== 0) {
    throw new Error('Unreviewed source or reversible grouping audit')
  }

  const before = baseline.metrics || {}
  const after = candidate.metrics || {}
  const quality = catalog.metrics || {}
  const baselineCount = boundedCount(before.original_records, 'published ID count')
  const currentCount = boundedCount(after.original_records, 'candidate ID count')
  const actualRows = boundedCount(quality.total, 'catalog ID count')
  const originalDuplicated = boundedCount(before.suppressed_repeat_buttons_only, 'published grouping')
  const candidateDuplicated = boundedCount(after.suppressed_repeat_buttons_only, 'candidate grouping')
  const malformedOld = boundedCount(before.malformed_source_city_labels_guarded_in_ui, 'published city labels')
  const malformedNew = boundedCount(after.malformed_source_city_labels_guarded_in_ui, 'candidate city labels')
  const qualityMalformed = boundedCount(quality.suspicious_city, 'quality city labels')
  if (currentCount !== actualRows || baselineCount > currentCount ||
      before.ids_retained !== baselineCount || after.ids_retained !== currentCount ||
      malformedNew !== qualityMalformed ||
      after.market_identities_deleted !== 0 || before.market_identities_deleted !== 0 ||
      after.event_confirmations_created !== 0 || before.event_confirmations_created !== 0 ||
      after.verification_claims_created !== 0 || before.verification_claims_created !== 0 ||
      candidateDuplicated > after.original_records_in_reversible_groups ||
      originalDuplicated > before.original_records_in_reversible_groups) {
    throw new Error('Visitor grouping contradicted source identities or catalog quality')
  }
  if (malformedNew > malformedOld + 10) {
    throw new Error('New malformed municipality labels increased beyond safety budget')
  }
  const maximum = Math.max(50, Math.floor(originalDuplicated * 1.35))
  if (candidateDuplicated > maximum) {
    throw new Error('Newly introduced display duplicates exceed the published DEV safety budget')
  }

  const saved = history?.metrics?.suppressed_repeat_buttons_only
  const historical = Number.isInteger(saved) ? saved : null
  return {
    schema: 1,
    source: 'actual_published_dev_static_catalog',
    published_records: baselineCount,
    candidate_records: currentCount,
    published_suppressed_repeats: originalDuplicated,
    candidate_suppressed_repeats: candidateDuplicated,
    allowed_maximum: maximum,
    newly_observed_repeats: Math.max(0, candidateDuplicated - originalDuplicated),
    historical_scorecard_repeats: historical,
    historical_scorecard_stale: historical !== null && historical !== originalDuplicated,
    ids_preserved: true,
    newly_introduced_regression: false,
    production_modified: false,
  }
}

function run() {
  const args = process.argv.slice(2)
  function opt(name) {
    const index = args.indexOf(name)
    if (index < 0 || index >= args.length - 1) throw new Error('Missing ' + name)
    return args[index + 1]
  }
  const read = (file) => JSON.parse(fs.readFileSync(file, 'utf8'))
  const candidate = read(opt('--candidate'))
  const baseline = read(opt('--baseline'))
  const catalog = read(opt('--catalog-quality'))
  const historical = opt('--previous-scorecard')
  const report = guardVisitorRelease(baseline, candidate, catalog,
                                     fs.existsSync(historical) ? read(historical) : null)
  const output = opt('--out')
  fs.mkdirSync(path.dirname(path.resolve(output)), {recursive: true})
  fs.writeFileSync(output, JSON.stringify(report, null, 2) + '\n', 'utf8')
  console.log('VISITOR_DEV_RELEASE_GUARD', JSON.stringify(report))
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  try { run() } catch (error) {
    console.error('VISITOR_DEV_RELEASE_BLOCKED', error)
    process.exitCode = 2
  }
}
