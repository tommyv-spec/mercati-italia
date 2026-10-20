import test from 'node:test'
import assert from 'node:assert/strict'
import {validAddressConflict, cleanAddressConflicts, addressConflictView} from '../src/lib/sourceFieldConflicts.js'
import {destinationForMarket} from '../src/lib/marketDirections.js'
import {adaptMarket} from '../src/hooks/useMarkets.js'

const TODAY = '2026-10-20'
const record = {
  slug: 'mercato-settimanale-di-lucca-lucca-mercoledi', nome: 'Mercato settimanale di Lucca',
  citta: 'Lucca', provincia: 'LU', regione: 'Toscana', fonte: 'happings.com',
  url_fonte: 'https://www.happings.com/it/mercato-settimanale-a-lucca.html',
  indirizzo: 'Piazza del Carmine', ricorrenza_testo: 'settimanale - mercoledì',
  lat: 43.84, lng: 10.51, position_quality: 'non_verificata',
  date_quality: 'prevista', date: ['2026-10-21', '2026-10-28'],
}
// Factual fragment captured in LIVE7; identity association is separately
// reconstructed by the backend producer/guard. This is its UI contract fixture.
const fragment = 'Il mercato settimanale di Lucca si svolge a Piazzale Don Baroni il mercoledì e il sabato, dalle 8:00 alle 13:00. A Ponte a Moriano l’appuntamento è il martedì in Piazza del Popolo, dalle 8:00 alle 13:00. Queste indicazioni sostituiscono i vecchi riferimenti al mercato cittadino in Piazza del Carmine e in Via dei Bacchettoni.'
const envelope = {
  schema: 1, gestore: 'happings-weekly', campo: 'indirizzo',
  mercato: Object.fromEntries(['slug', 'nome', 'citta', 'provincia', 'regione', 'fonte', 'url_fonte']
    .map(key => [key, record[key]])),
  valore_catalogo: 'Piazza del Carmine', valore_fonte: 'Piazzale Don Baroni', giorno_settimana: 2,
  url_richiesto: 'https://www.happings.com/it/mercati-settimanali-a-lucca.html',
  url_finale: 'https://www.happings.com/it/mercati-settimanali-a-lucca-e-provincia/',
  letto_il: TODAY, sha256: '7da91da612bba4e282f50c0ea254a804d877c1c81bfbf65eaa1b54abe1e9e1fd', bytes: 146047,
  prova: {tipo: 'sostituzione_sede_esplicita',
    selettore: 'main#main article.hpe-editorial--local-guide .hpe-editorial-grid > .hpe-editorial-body > p:nth-child(2)',
    frammento: fragment, sede_precedente: 'Piazza del Carmine', sede_attuale: 'Piazzale Don Baroni'},
}
const clone = value => structuredClone(value)
const full = extra => adaptMarket({...record, id: record.slug, conflitti_campi: [clone(envelope)], ...extra})

test('explicit replacement is a review warning with exact source facts, not a rewritten address', () => {
  const original = clone(record)
  const proof = clone(envelope)
  assert.equal(validAddressConflict(proof, record, TODAY), true)
  const market = full()
  assert.equal(market.addressReviewRequired, true)
  assert.equal(market.locationReviewRequired, false, 'An address conflict does not imply an unknown city')
  assert.equal(market.address, record.indirizzo)
  assert.deepEqual([market.lat, market.lng, market.dates], [record.lat, record.lng, record.date])
  assert.deepEqual(addressConflictView(market, TODAY).map(item => ({
    saved: item.savedAddress, source: item.sourceAddress, url: item.sourceUrl, read: item.readOn,
  })), [{saved: record.indirizzo, source: 'Piazzale Don Baroni', url: envelope.url_finale, read: TODAY}])
  assert.deepEqual(proof, envelope)
  assert.deepEqual(record, original)
  assert.equal(validAddressConflict(proof, record, '2030-01-01'), true,
    'A contradiction does not expire just because its read date is old')
})

test('all seven identity fields and the exact saved address remain bound', () => {
  for (const field of ['slug', 'nome', 'citta', 'provincia', 'regione', 'fonte', 'url_fonte', 'indirizzo']) {
    const changed = {...record, [field]: record[field] + '-changed'}
    assert.equal(validAddressConflict(envelope, changed, TODAY), false, field)
    assert.deepEqual(cleanAddressConflicts([envelope], changed, TODAY), [], field)
  }
  const renamed = full({nome: 'Un altro mercato'})
  assert.equal(renamed.addressReviewRequired, false)
  assert.deepEqual(renamed.fieldConflicts, [])
})

test('Unicode address comparison matches the backend source-proof fold, independently of street classification', () => {
  const row = {...record, indirizzo: 'Via Straße'}
  const proof = clone(envelope)
  proof.valore_catalogo = proof.prova.sede_precedente = row.indirizzo
  proof.valore_fonte = proof.prova.sede_attuale = 'Via Strasse'
  proof.prova.frammento = 'Il mercato è in Via Strasse. Queste indicazioni sostituiscono i vecchi riferimenti in Via Straße.'
  assert.equal(validAddressConflict(proof, row, TODAY), true,
    'The backend lower/token comparison keeps this explicitly reported contradiction')
})

test('extra keys, invalid proof scope, bad source metadata and a vague alternative cannot raise a warning', () => {
  const changes = [
    item => { item.extra = true },
    item => { item.mercato.extra = true },
    item => { item.prova.extra = true },
    item => { item.schema = true },
    item => { item.campo = 'orario_testo' },
    item => { item.bytes = 2600001 },
    item => { item.bytes = true },
    item => { item.sha256 = 'z'.repeat(64) },
    item => { item.giorno_settimana = 7 },
    item => { item.letto_il = '2026-10-21' },
    item => { item.letto_il = '2026-02-31' },
    item => { item.url_finale = 'https://evil.example/it/mercati-settimanali-a-lucca-e-provincia/' },
    item => { item.url_finale = item.url_finale.replace('-lucca-', '-pisa-') },
    item => { item.url_richiesto += '?source=another' },
    item => { item.url_finale = item.url_finale.replace('/it/', '/old/../it/') },
    item => { item.prova.selettore = 'footer p:nth-child(1)' },
    item => { item.prova.selettore = item.prova.selettore.replace('(2)', '(201)') },
    item => { item.prova.frammento = fragment.replace('Queste indicazioni sostituiscono', 'Sono elencati anche') },
    item => { item.prova.frammento += ' Queste indicazioni sostituiscono i vecchi riferimenti.' },
    item => { item.prova.frammento = fragment.replace('Piazzale Don Baroni', 'Piazzale Don Baronio') },
    item => { item.prova.frammento = fragment.replace('Piazza del Carmine', 'Piazza del Carmineo') },
    item => { item.prova.frammento = fragment.replace('Il mercato', 'Il  mercato') },
    item => { item.valore_fonte = item.prova.sede_attuale = 'centro storico' },
    item => { item.valore_fonte = item.prova.sede_attuale = item.valore_catalogo },
  ]
  for (const [i, change] of changes.entries()) {
    const invalid = clone(envelope)
    change(invalid)
    assert.equal(validAddressConflict(invalid, record, TODAY), false, 'invalid variant ' + i)
  }
  assert.deepEqual(cleanAddressConflicts([envelope, envelope, envelope, envelope], record, TODAY), [])
  assert.equal(cleanAddressConflicts([envelope, clone(envelope)], record, TODAY).length, 1)
})

test('directions independently recheck the conflict even when its derived flag is false or absent', () => {
  for (const flag of [false, undefined]) {
    const market = {...full(), positionQuality: 'precisa', addressReviewRequired: flag}
    assert.equal(destinationForMarket(market, TODAY), null)
    assert.equal(addressConflictView(market, TODAY).length, 1)
  }
  const ordinary = full({conflitti_campi: []})
  assert.match(destinationForMarket(ordinary, TODAY), /Piazza del Carmine/)
  assert.equal(destinationForMarket({...ordinary, positionQuality: 'precisa'}, TODAY), '43.84,10.51')
  assert.equal(destinationForMarket({...ordinary, locationReviewRequired: true}, TODAY), null)
  assert.equal(destinationForMarket({...ordinary, address: 'centro'}, TODAY), null)
})

test('the compact index stays unchanged while regional loading retains only valid conflicts', async () => {
  const oldFetch = globalThis.fetch
  const calls = []
  const summary = [record.slug, record.nome, record.citta, record.regione, 'alimentare', [],
    record.lat, record.lng, record.position_quality, '', record.date_quality, record.date, '']
  globalThis.fetch = async url => {
    const name = new URL(url, 'https://local-fixture.invalid').pathname
    calls.push(name)
    const payload = name.endsWith('/manifest.json') ? {schema: 1, index_schema: 6,
      index_as_of: TODAY, total: 1, layout: 'regional', index: 'data/v1/index-address-conflict.json',
      regions: [{name: 'Toscana', count: 1, path: 'data/v1/regions/toscana-address-conflict.json'}]}
      : name.endsWith('/index-address-conflict.json') ? {schema: 1, markets: [summary]}
        : name.endsWith('/toscana-address-conflict.json') ? {schema: 1, markets: [{...record,
          conflitti_campi: [clone(envelope), {...clone(envelope), campo: 'nome'}]}]} : null
    assert.ok(payload, 'Unexpected request: ' + name)
    return {ok: true, json: async () => clone(payload)}
  }
  try {
    const loader = await import('../src/services/staticMarkets.js?address-conflict-regression')
    const list = (await loader.fetchMarkets()).map(item => adaptMarket(item))
    assert.equal(calls.length, 2)
    assert.equal(list[0].address, '')
    assert.deepEqual(list[0].fieldConflicts, [])
    const detail = await loader.fetchMarketById(record.slug)
    assert.equal(detail.conflitti_campi.length, 1)
    const market = adaptMarket(detail)
    assert.equal(market.addressReviewRequired, true)
    assert.equal(market.locationReviewRequired, false)
    assert.equal(destinationForMarket(market, TODAY), null)
    assert.equal(market.address, record.indirizzo)
    assert.deepEqual(market.dates, record.date)
    assert.equal(calls.length, 3, 'No publisher fetch or extra catalog request')
  } finally { globalThis.fetch = oldFetch }
})
