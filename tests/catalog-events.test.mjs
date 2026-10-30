import test from 'node:test'
import assert from 'node:assert/strict'
import { decodeEventRows, mergeEventFields } from '../src/services/staticMarkets.js'

const rows = [['fiera', 'Piazza Grande', 'primo weekend del mese', 'Testo breve.', 'Ingresso gratuito', 'Arriva presto']]

test('decodeEventRows builds a slug map and rejects bad rows', () => {
  const map = decodeEventRows({ schema: 1, markets: rows })
  assert.equal(map.get('fiera').indirizzo, 'Piazza Grande')
  assert.equal(map.get('fiera').consigli, 'Arriva presto')
  assert.equal(decodeEventRows({ schema: 2, markets: rows }), null)
  assert.equal(decodeEventRows({ schema: 1, markets: [['x', 'only-two']] }), null)
})

test('mergeEventFields fills missing fields and flags events; fallback without a map', () => {
  const events = decodeEventRows({ schema: 1, markets: rows })
  const merged = mergeEventFields({ slug: 'fiera', categoria: 'antiquariato', tags: [], indirizzo: '' }, events)
  assert.equal(merged.isEvent, true)
  assert.equal(merged.indirizzo, 'Piazza Grande')
  assert.equal(merged.descrizione, 'Testo breve.')
  const weekly = mergeEventFields({ slug: 'w', categoria: 'misto', tags: ['settimanale'] }, events)
  assert.equal(weekly.isEvent, false)
  assert.equal(mergeEventFields({ slug: 'fiera', categoria: 'antiquariato', tags: [] }, null).isEvent, true)
  assert.equal(mergeEventFields({ slug: 'w', categoria: 'misto', tags: [] }, null).isEvent, false)
})
