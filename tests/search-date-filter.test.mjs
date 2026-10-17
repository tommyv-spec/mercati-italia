import test from 'node:test'
import assert from 'node:assert/strict'
import { effectiveDateFilter } from '../src/lib/searchDateFilter.js'

test('initial seven-day filter is bypassed when searching specific unscheduled markets', () => {
  assert.equal(effectiveDateFilter('7giorni', '', false), '7giorni')
  assert.equal(effectiveDateFilter('7giorni', '  ', false), '7giorni')
  assert.equal(effectiveDateFilter('7giorni', 'Mercatino delle Curiosità', false), null)
  assert.equal(effectiveDateFilter('7giorni', 'Cernobbio', false), null)
  assert.equal(effectiveDateFilter('7giorni', '', true), '7giorni')
})

test('search never overrides the date chip intentionally selected by the visitor', () => {
  for (const mode of ['oggi', 'weekend', '7giorni']) {
    assert.equal(effectiveDateFilter(mode, 'Mercatino delle Curiosità', true), mode)
  }
  assert.equal(effectiveDateFilter(null, 'mercato', true), null)
  assert.equal(effectiveDateFilter(null, '', false), null)
})
