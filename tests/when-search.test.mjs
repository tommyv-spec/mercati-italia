import test from 'node:test'
import assert from 'node:assert/strict'
import { whenDays, firstDayIn, whenLabel, DEFAULT_WHEN } from '../src/lib/when.js'
import { searchMarkets, matchCities, queryWords } from '../src/lib/search.js'

const SUN = '2026-11-01'
const TUE = '2026-11-03'

test('this weekend keeps only days not yet past', () => {
  assert.deepEqual(whenDays(DEFAULT_WHEN, SUN), ['2026-11-01'])
  assert.deepEqual(whenDays(DEFAULT_WHEN, TUE), ['2026-11-07', '2026-11-08'])
  assert.deepEqual(whenDays({ kind: 'weekend', offset: 1 }, TUE), ['2026-11-14', '2026-11-15'])
})

test('today, tomorrow, seven days, a weekday, all dates', () => {
  assert.deepEqual(whenDays({ kind: 'oggi' }, TUE), [TUE])
  assert.deepEqual(whenDays({ kind: 'domani' }, TUE), ['2026-11-04'])
  const week = whenDays({ kind: '7giorni' }, TUE)
  assert.equal(week.length, 8)
  assert.equal(week[0], TUE)
  assert.equal(week[7], '2026-11-10')
  assert.deepEqual(whenDays({ kind: 'weekday', weekday: 5 }, TUE), ['2026-11-07'])
  assert.deepEqual(whenDays({ kind: 'weekday', weekday: 1 }, TUE), [TUE])
  assert.equal(whenDays({ kind: 'tutte' }, TUE), null)
})

test('first day in range and labels', () => {
  assert.equal(firstDayIn(['2026-11-08', '2026-11-07'], ['2026-11-07', '2026-11-08'], TUE), '2026-11-07')
  assert.equal(firstDayIn(['2026-11-20'], ['2026-11-07', '2026-11-08'], TUE), null)
  assert.equal(firstDayIn(['2026-10-01', '2026-11-20'], null, TUE), '2026-11-20')
  assert.equal(firstDayIn([], null, TUE), null)
  assert.equal(whenLabel(DEFAULT_WHEN), 'Questo weekend')
  assert.equal(whenLabel({ kind: 'weekday', weekday: 5 }), 'Sabato')
  assert.equal(whenLabel({ kind: 'tutte' }), 'Tutte le date')
})

const mk = (name, city, extra = {}) => ({ id: name, name, city, region: 'Toscana', category: 'Antiquariato', tags: [], dates: [], ...extra })

test('search matches the start of words, ignores accents, never inside a word', () => {
  assert.deepEqual(queryWords('  Città di Nardò '), ['citta', 'di', 'nardo'])
  const markets = [
    mk('Mercato di Sarezzo', 'Sarezzo', { region: 'Lombardia' }),
    mk('Fiera Antiquaria di Arezzo', 'Arezzo', { dates: ['2026-11-07'] }),
    mk('Mercatino di Nardò', 'Nardò', { region: 'Puglia' }),
    mk('Casalotti', 'Roma', { region: 'Lazio' }),
  ]
  assert.deepEqual(searchMarkets(markets, 'arezzo', TUE).map(m => m.name), ['Fiera Antiquaria di Arezzo'])
  assert.deepEqual(searchMarkets(markets, 'nardo', TUE).map(m => m.name), ['Mercatino di Nardò'])
  assert.deepEqual(searchMarkets(markets, 'fiera arez', TUE).map(m => m.name), ['Fiera Antiquaria di Arezzo'])
  assert.deepEqual(searchMarkets(markets, 'zzz', TUE), [])
})

test('a name match outranks a town match, then the next date decides', () => {
  const markets = [
    mk('Mercato settimanale', 'Arezzo', { dates: ['2026-11-04'] }),
    mk('Fiera Antiquaria di Arezzo', 'Arezzo', { dates: ['2026-11-07'] }),
    mk('Arezzo Vintage', 'Arezzo', { dates: ['2026-11-20'] }),
  ]
  assert.deepEqual(searchMarkets(markets, 'arezzo', TUE).map(m => m.name),
    ['Arezzo Vintage', 'Fiera Antiquaria di Arezzo', 'Mercato settimanale'])
})

test('cities are suggested by the start of their words', () => {
  const cities = ['Arezzo', 'Sarezzo', 'Reggio Emilia', 'Reggio Calabria', 'Reggello']
  assert.deepEqual(matchCities(cities, 'arezzo'), ['Arezzo'])
  assert.deepEqual(matchCities(cities, 'reggio'), ['Reggio Calabria', 'Reggio Emilia'])
  assert.deepEqual(matchCities(cities, 'reggio em'), ['Reggio Emilia'])
  assert.deepEqual(matchCities(cities, ''), [])
})

test('on an equal match an event comes before a weekly market', () => {
  const markets = [
    mk('Mercato settimanale di Arezzo', 'Arezzo', { dates: ['2026-11-04'], isEvent: false }),
    mk('Fiera Antiquaria di Arezzo', 'Arezzo', { dates: ['2026-11-07'], isEvent: true }),
  ]
  assert.deepEqual(searchMarkets(markets, 'arezzo', TUE).map(m => m.name), ['Fiera Antiquaria di Arezzo', 'Mercato settimanale di Arezzo'])
})
