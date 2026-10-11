import test from 'node:test'
import assert from 'node:assert/strict'
import {
  isGenericCityWeeklyMarket, displayEntries, groupVenues, distinctWeekdays,
  nextMatchingDate, weekdayFromISO, reliableVenueAddress,
} from '../src/lib/marketGrouping.js'

const make = (day, address, i) => ({
  id: 'mercato-settimanale-di-firenze-firenze-' + day,
  name: 'Mercato settimanale di Firenze',
  city: 'Firenze',
  region: 'Toscana',
  dateQuality: 'prevista',
  dates: [
    '2026-10-' + String([12, 13, 14, 15, 16, 17][i]).padStart(2, '0'),
    '2026-10-' + String([19, 20, 21, 22, 23, 24][i]).padStart(2, '0'),
  ],
  address,
  hours: '',
  positionQuality: 'non_verificata',
})

const florence = [
  make('lunedi', 'Largo Monzani', 0),
  make('martedi', 'Cascina Rossa (Piante e Fiori)', 1),
  make('mercoledi', 'Largo Monzani', 2),
  make('giovedi', 'Largo Monzani', 3),
  make('venerdi', 'Cintola', 4),
  make('sabato', 'Piazza i maggio', 5),
]

test('six Firenze city records render as one city card, four venues after detail load', () => {
  const entries = displayEntries(florence)
  assert.equal(entries.length, 1)
  assert.equal(entries[0].kind, 'group')
  assert.equal(entries[0].markets.length, 6)
  assert.deepEqual(distinctWeekdays(entries[0].markets), [0, 1, 2, 3, 4, 5])
  const venues = groupVenues(florence)
  assert.equal(venues.length, 4)
  const largo = venues.find(v => v.address === 'Largo Monzani')
  assert.ok(largo)
  assert.equal(largo.markets.length, 3)
  assert.equal(venues.find(v => v.address === 'Piazza i maggio').markets.length, 1)
  assert.equal(florence.length, 6, 'display grouping must not mutate source array')
})

test('Saturday filter keeps only Piazza I maggio and shows one auto-expandable weekly group', () => {
  const saturday = florence.filter(m => m.dates.some(d => weekdayFromISO(d) === 5))
  assert.equal(saturday.length, 1)
  assert.equal(saturday[0].address, 'Piazza i maggio')
  assert.equal(displayEntries(saturday).length, 1)
  assert.equal(displayEntries(saturday)[0].kind, 'market')
  assert.equal(displayEntries(saturday, { keepSingleWeeklyGroups: true })[0].kind, 'group')
  assert.equal(nextMatchingDate(saturday[0].dates, 5, new Date(2026, 9, 11)), '2026-10-17')
})

test('unknown seventh Firenze record stays unsited and does not merge with Monday address', () => {
  const unknownMonday = {
    ...florence[0],
    id: 'mercato-settimanale-a-firenze-firenze-lunedi',
    name: 'Mercato settimanale a Firenze',
    address: '',
  }
  const entries = displayEntries([...florence, unknownMonday])
  assert.equal(entries.length, 1)
  assert.equal(entries[0].markets.length, 7)
  const venues = groupVenues([...florence, unknownMonday])
  assert.equal(venues.filter(v => v.verifiedAddress).length, 4)
  assert.equal(venues.filter(v => !v.verifiedAddress).length, 1)
  assert.equal(venues.find(v => v.address === 'Largo Monzani').markets.length, 3)
})

test('named neighborhood markets never collapse into generic city-wide group', () => {
  const extra = { ...florence[0], id: 'san-lorenzo', name: 'Mercato di San Lorenzo' }
  assert.equal(isGenericCityWeeklyMarket(extra), false)
  const entries = displayEntries([...florence, extra])
  assert.equal(entries.length, 2)
  assert.equal(entries.find(e => e.kind === 'market').market.id, 'san-lorenzo')
})

test('different cities and regions are never combined', () => {
  const elsewhere = { ...florence[0], id: 'other-city', city: 'Prato', name: 'Mercato settimanale di Prato' }
  const diffRegion = { ...florence[0], id: 'other-region', region: 'Lazio' }
  assert.equal(displayEntries([...florence, elsewhere, diffRegion]).length, 3)
})

test('different physical addresses remain separate; generic/absent addresses never merge', () => {
  assert.equal(reliableVenueAddress('centro'), '')
  assert.equal(reliableVenueAddress('ce...'), '')
  assert.equal(reliableVenueAddress('Largo Monzani'), 'largo monzani')
  const sameUnknown = [
    { ...florence[0], address: '' },
    { ...florence[2], address: 'centro' },
  ]
  assert.equal(groupVenues(sameUnknown).length, 2)
  const sameStreetDifferentNumber = [
    { ...florence[0], address: 'Via Roma 1' },
    { ...florence[2], address: 'Via Roma 11' },
  ]
  assert.equal(groupVenues(sameStreetDifferentNumber).length, 2)
})

test('same address but conflicting precise coordinates remain distinct', () => {
  const a = { ...florence[0], positionQuality: 'precisa', lat: 43.77, lng: 11.25 }
  const b = { ...florence[2], positionQuality: 'precisa', lat: 43.78, lng: 11.28 }
  assert.equal(groupVenues([a, b]).length, 2)
})

test('weekday parsing safely preserves Italian local calendar day', () => {
  assert.equal(weekdayFromISO('2026-10-11'), 6)
  assert.equal(weekdayFromISO('2026-10-17'), 5)
  assert.equal(weekdayFromISO('2026-13-40'), null)
  assert.equal(weekdayFromISO('2026-10-17T12:00'), null)
})
