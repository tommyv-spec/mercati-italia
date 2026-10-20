import test from 'node:test'
import assert from 'node:assert/strict'
import { localDateISO, hasUpcomingDate, marketDateDisclosure } from '../src/lib/dateDisclosure.js'

const TODAY = new Date(2026, 9, 12, 12, 0)

test('missing or expired event list cannot be described as future forecasts', () => {
  assert.match(marketDateDisclosure([], 'prevista', TODAY), /Nessuna data futura/)
  assert.match(marketDateDisclosure([], 'confermata', TODAY), /Nessuna data futura/)
  assert.match(marketDateDisclosure(['2026-09-01'], 'confermata', TODAY), /Nessuna data futura/)
  assert.match(marketDateDisclosure(null, 'prevista', TODAY), /Nessuna data futura/)
  assert.match(marketDateDisclosure([], 'sconosciuta', TODAY), /Giorni e aperture da verificare/)
})

test('future planned dates always disclose uncertainty, confirmed future dates do not', () => {
  assert.match(marketDateDisclosure(['2026-10-13'], 'prevista', TODAY), /Date previste/)
  assert.match(marketDateDisclosure(['2026-10-13'], 'sconosciuta', TODAY), /Date previste/)
  assert.equal(marketDateDisclosure(['2026-10-13'], 'confermata', TODAY), '')
  assert.equal(marketDateDisclosure(['2026-10-12'], 'confermata', TODAY), '')
})

test('calendar dates are compared at browser local date, not UTC midnight', () => {
  assert.equal(localDateISO(TODAY), '2026-10-12')
  assert.equal(hasUpcomingDate(['2026-10-12'], TODAY), true)
  assert.equal(hasUpcomingDate(['2026-10-11'], TODAY), false)
  assert.equal(hasUpcomingDate(['garbage'], TODAY), false)
})

test('source-listed dates remain distinct from forecasts and human confirmation', () => {
  const reported = marketDateDisclosure(['2026-10-13'], 'riportata', TODAY)
  assert.match(reported, /Date riportate dalla fonte/)
  assert.doesNotMatch(reported, /Date previste|confermate|Verificato/)
  assert.match(marketDateDisclosure(['2026-10-13'], 'mista', TODAY), /Date previste e date riportate/)
  assert.match(marketDateDisclosure(['2025-10-13'], 'riportata', TODAY), /Nessuna data futura/)
})
