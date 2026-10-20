import test from 'node:test'
import assert from 'node:assert/strict'
import {decodeIndexRecords} from '../src/services/staticMarkets.js'
import {adaptMarket} from '../src/hooks/useMarkets.js'
import {sourceHoursForDate} from '../src/lib/sourceCalendar.js'
import {editorialSummaryView} from '../src/lib/editorialEvidence.js'

const DAY = '2026-10-20'
const current = ["lana-example", "Mercatino", "Lana", "Trentino-Alto Adige", "misto", [],
  null, null, "sconosciuta", "10:00–19:30", "riportata", ["2026-12-24"]]
const manifest = {index_schema: 6, index_as_of: DAY}

test('versions 4 and 5 remain twelve columns; version 6 requires its exact flag and reference day', () => {
  for (const version of [4, 5]) {
    assert.equal(decodeIndexRecords([current], {index_schema: version})[0].orario_testo, '10:00–19:30')
    assert.equal(decodeIndexRecords([current], {index_schema: version})[0].ambito_orari, undefined)
    assert.throws(() => decodeIndexRecords([[...current, 'storico']], {index_schema: version}))
  }
  for (const flag of ['', 'per_data', 'storico']) {
    assert.equal(decodeIndexRecords([[...current, flag]], manifest)[0].ambito_orari, flag)
  }
  for (const value of [current, [...current, 'confirmed'], [...current, 'storico', 'extra']]) {
    assert.throws(() => decodeIndexRecords([value], manifest))
  }
  for (const value of [undefined, '2026-02-31', '20261020']) {
    assert.throws(() => decodeIndexRecords([[...current, 'storico']], {...manifest, index_as_of: value}))
  }
  assert.throws(() => decodeIndexRecords([{slug: 'another', ambito_orari: 'storico'}], manifest))
  assert.throws(() => decodeIndexRecords([current], {index_schema: 7}))
  assert.equal(decodeIndexRecords([current], {})[0].slug, current[0], 'Keep unversioned legacy previews')
  assert.equal(decodeIndexRecords([{slug: 'legacy', ambito_orari: 'storico'}], {})[0].ambito_orari, '')
})

test('the first compact list shows a qualified label; regional facts and per-date hours remain exact', async () => {
  const oldFetch = globalThis.fetch
  const historic = ['historical-example', 'Edizione passata', 'Lavarone', 'Trentino-Alto Adige', 'misto', [],
    null, null, 'sconosciuta', '20:00–20:00', 'sconosciuta', [], 'storico']
  const detail = {slug: current[0], nome: current[1], citta: current[2], regione: current[3],
    categoria: 'misto', orario_testo: current[9], date_quality: 'riportata', date: current[11],
    calendario_fonte: {occorrenze: [{date: '2026-12-24', start_time: '10:00', end_time: '13:00', status: 'source_listed'}]}}
  const calls = []
  globalThis.fetch = async value => {
    const name = new URL(value, 'https://catalog.example').pathname
    calls.push(name)
    const payload = name.endsWith('/manifest.json') ? {...manifest, schema: 1, total: 2,
      layout: 'regional', index: 'data/v1/index-scope.json', regions: [{name: current[3], count: 2,
        path: 'data/v1/regions/trentino-scope.json'}]}
      : name.endsWith('/index-scope.json') ? {schema: 1, markets: [[...current, 'per_data'], historic]}
        : name.endsWith('/trentino-scope.json') ? {schema: 1, markets: [detail,
          {slug: historic[0], nome: historic[1], citta: historic[2], regione: historic[3],
            orario_testo: historic[9], date: []}]} : null
    assert.ok(payload, 'No publisher or unexpected HTTP request')
    return {ok: true, json: async () => structuredClone(payload)}
  }
  try {
    const loader = await import('../src/services/staticMarkets.js?scope-six-regression')
    const list = (await loader.fetchMarkets()).map(item => adaptMarket(item))
    assert.deepEqual(list.map(item => item.indexHoursScope), ['per_data', 'storico'])
    assert.equal(sourceHoursForDate(list[0], '2026-12-24'), 'Vedi gli orari per data')
    assert.equal(sourceHoursForDate(list[1], null), 'Orari attuali da verificare')
    assert.equal(editorialSummaryView(list[1]).hours, 'Orari attuali da verificare')
    assert.equal(list[0].hours, '10:00–19:30', 'Scope does not overwrite source fields')
    assert.equal(list[1].hours, '20:00–20:00', 'Historical catalog data is not replaced by a placeholder')
    assert.equal(calls.length, 2, 'The initial list does not download regional evidence')
    const full = adaptMarket(await loader.fetchMarketById(current[0]))
    assert.equal(full.hours, '10:00–19:30')
    assert.equal(sourceHoursForDate({...full, indexHoursScope: 'per_data'}, '2026-12-24'), '10:00–13:00')
    assert.equal(calls.length, 3)
  } finally {
    globalThis.fetch = oldFetch
  }
})

test('an ordinary legacy row without bound scope preserves its existing display', () => {
  const ordinary = adaptMarket({id: current[0], orario_testo: '07:00–13:00', ricorrenza_testo: 'Ogni martedì'})
  assert.equal(sourceHoursForDate(ordinary, '2026-10-27'), '07:00–13:00')
  assert.equal(editorialSummaryView(ordinary).recurrence, 'Ogni martedì')
})
