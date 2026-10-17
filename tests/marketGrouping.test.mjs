import test from 'node:test'
import assert from 'node:assert/strict'
import {
  isGenericCityWeeklyMarket, displayEntries, groupVenues, groupVenueAppointments, distinctWeekdays,
  nextMatchingDate, weekdayFromISO, reliableVenueAddress, shouldAutoExpandWeeklyGroup,
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

test('nationwide weekday filtering does not auto-fetch hundreds of regional venue shards', () => {
  const group = displayEntries(florence)[0]
  assert.equal(shouldAutoExpandWeeklyGroup(group, 5), false)
  assert.equal(shouldAutoExpandWeeklyGroup(group, 5, '', 'Mercato settimanale'), false)
  assert.equal(shouldAutoExpandWeeklyGroup(group, 5, 'Roma'), false)
  assert.equal(shouldAutoExpandWeeklyGroup(group, 5, 'Firenze'), true)
  assert.equal(shouldAutoExpandWeeklyGroup(group, 5, '', 'Firenze'), true)
  assert.equal(shouldAutoExpandWeeklyGroup(group, null, 'Firenze'), false)
})


const makeReported = (name, city, address, weekday, id, sourceUrl, dates, extra = {}) => ({
  id, name, city, region: 'Lombardia', address, category: 'Misto',
  dateQuality: 'prevista', status: 'non_confermato',
  dates, recurrence: 'settimanale - ' + weekday,
  sourceUrl, positionQuality: 'non_verificata',
  lat: 45.724163, lng: 8.797983, hours: '', ...extra,
})

test('observed Albizzate same page, venue and Tuesday displays one visit with both original IDs', () => {
  const url = 'https://www.happings.com/it/mercato-settimanale-a-albizzate.html'
  const dates = ['2026-10-13', '2026-10-20', '2026-10-27']
  const first = makeReported('Mercato settimanale di Albizzate', 'Albizzate',
    'Piazzale Sefro', 'martedì', 'mercato-settimanale-di-albizzate-albizzate',
    url, dates, { sourceUpdated: '2026-03-18' })
  const second = { ...first,
    id: 'mercato-settimanale-di-albizzate-albizzate-martedi',
    hours: '08:00–13:00 (fonte comunale, da verificare)',
    sourceUpdated: '2026-06-05',
  }
  const inputs = [first, second]
  const visits = groupVenueAppointments(inputs)
  assert.equal(visits.length, 1)
  assert.equal(visits[0].market.id, second.id)
  assert.equal(visits[0].records.length, 2)
  assert.deepEqual(visits[0].records.map(x => x.id).sort(), inputs.map(x => x.id).sort())
  assert.equal(inputs[0].hours, '', 'Original input is immutable')
  assert.equal(groupVenueAppointments(inputs)[0].key, second.id)
})

test('source, venue, day, future dates, category, hours, status and coordinates must agree', () => {
  const url = 'https://www.eventiesagre.it/Mercatini_Filiera+Corta/21181315_Mercato+Settimanale+Di+Breganze.html'
  const a = makeReported('Mercato settimanale di Breganze','Breganze',
    'Piazza Mazzini','mercoledì','first',url,
    ['2026-10-14','2026-10-21','2026-10-28'],
    { region:'Veneto',lat:45.704,lng:11.565,hours:'08:00–13:00' })
  const b = { ...a, id:'second' }
  assert.equal(groupVenueAppointments([a,b]).length,1)
  const conflicts = [
    { ...b,sourceUrl:'https://different.example/market' },
    { ...b,city:'Another city' },
    { ...b,address:'Piazza Roma' },
    { ...b,dates:['2026-10-21','2026-10-28'] },
    { ...b,dates:['2026-10-18','2026-10-25'] },
    { ...b,recurrence:'mensile - secondo mercoledì' },
    { ...b,hours:'15:00–20:00' },
    { ...b,lat:45.75 },
    { ...b,category:'Antiquariato' },
    { ...b,dateQuality:'confermata' },
    { ...b,lastVerified:'2026-10-11' },
    { ...b,id:'lo-mercap-100001-mercoledi' },
    { ...b,sourceUrl:'' },
  ]
  for (const item of conflicts) {
    assert.equal(groupVenueAppointments([a,item]).length,2,
      'Conflict must not be silently compressed: '+JSON.stringify(item))
  }
})

test('distinct Firenze weekdays and unknown venues preserve each original appointment', () => {
  const source='https://www.happings.com/it/mercati-settimanali-a-firenze.html'
  const items=florence.map(x=>({...x,category:'Misto',sourceUrl:source,
    recurrence:'settimanale - '+x.id.split('-').at(-1)}))
  const largo=groupVenues(items).find(x=>x.address==='Largo Monzani')
  assert.equal(groupVenueAppointments(largo.markets).length,3)
  const unknown=[...items,{...items[0],id:'other',address:'centro storico'}]
  assert.equal(groupVenues(unknown).filter(v=>!v.verifiedAddress).length,1)
  assert.deepEqual(groupVenueAppointments(items).map(v=>v.records.length),[1,1,1,1,1,1])
})

test('monthly series cannot be disguised as a weekly duplicate', () => {
  const url='https://www.eventiesagre.it/Mercatini/one.html'
  const a=makeReported('Mercatino settimanale di Breganze','Breganze',
    'Piazza Mazzini','mercoledì','a',url,
    ['2026-10-14','2026-11-11'],{region:'Veneto',lat:45.704,lng:11.565})
  assert.equal(groupVenueAppointments([a,{...a,id:'b'}]).length,2)
  assert.equal(groupVenueAppointments([a])[0].records.length,1)
})
