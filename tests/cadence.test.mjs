import test from 'node:test'
import assert from 'node:assert/strict'
import { fallbackIsEvent, WEEKLY_TAGS } from '../src/lib/cadence.js'

test('fallback: weekly tags and misto are weekly, the rest are events', () => {
  assert.equal(fallbackIsEvent({ categoria: 'antiquariato', tags: [] }), true)
  assert.equal(fallbackIsEvent({ categoria: 'misto', tags: [] }), false)
  assert.equal(fallbackIsEvent({ categoria: 'alimentare', tags: ['mercato comunale'] }), false)
  assert.equal(fallbackIsEvent({ categoria: 'alimentare', tags: ['MERCAP'] }), false)
  assert.equal(fallbackIsEvent({ categoria: 'usato', tags: ['vintage'] }), true)
  assert.ok(WEEKLY_TAGS.has('settimanale'))
})
