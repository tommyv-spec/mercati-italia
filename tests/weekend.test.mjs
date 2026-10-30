import test from 'node:test'
import assert from 'node:assert/strict'
import { weekendOf, inWeekend } from '../src/lib/weekend.js'

const d = s => new Date(s + 'T12:00:00')

test('this weekend is the coming Saturday+Sunday, or the current one on Sat/Sun', () => {
  assert.deepEqual([weekendOf(d('2026-10-30')).sat, weekendOf(d('2026-10-30')).sun], ['2026-10-31', '2026-11-01'])
  assert.equal(weekendOf(d('2026-10-31')).sat, '2026-10-31')
  assert.equal(weekendOf(d('2026-11-01')).sat, '2026-10-31')
  assert.equal(weekendOf(d('2026-11-02')).sat, '2026-11-07')
})

test('offset moves whole weekends and labels them', () => {
  const next = weekendOf(d('2026-10-30'), 1)
  assert.deepEqual([next.sat, next.sun], ['2026-11-07', '2026-11-08'])
  assert.equal(weekendOf(d('2026-10-30')).label, 'Questo weekend')
  assert.equal(next.label, 'Prossimo weekend')
  assert.equal(weekendOf(d('2026-10-30'), 2).label, 'Weekend del 14 novembre')
  assert.equal(weekendOf(d('2026-10-30')).sub, 'sabato 31 ottobre · domenica 1 novembre')
})

test('inWeekend checks either day', () => {
  const w = weekendOf(d('2026-10-30'))
  assert.equal(inWeekend(['2026-11-01'], w), true)
  assert.equal(inWeekend(['2026-11-03'], w), false)
})
