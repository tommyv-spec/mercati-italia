import test from 'node:test'
import assert from 'node:assert/strict'
import { createHash } from 'node:crypto'
import { readFileSync } from 'node:fs'
import { CITYNEWS_HOSTS, citynewsSourceIdentity } from '../src/lib/citynewsIdentity.js'
import { editorialEvidenceView, editorialHoursForDate } from '../src/lib/editorialEvidence.js'
import { fieldEvidenceSummary } from '../src/lib/fieldEvidence.js'
import { adaptMarket } from '../src/hooks/useMarkets.js'

const TODAY = new Date(2026, 9, 20, 12)
const URL = 'https://www.bolognatoday.it/eventi/mercato-edizione-test-2026.html'
const sourceId = value => 'citynews-' + createHash('sha256').update(value).digest('hex').slice(0, 24)
const identity = {slug: 'citynews-example', citta: 'Bologna', provincia: 'BO', regione: 'Emilia-Romagna'}
const occurrence = (date, start_time = null, end_time = null, status = 'source_listed') =>
  ({date, start_time, end_time, status})

// Deliberately synthetic proof: tests exercise display, never claim a live event.
function rawMarket(facts = {}, proof = {}) {
  return {...identity, id: identity.slug, nome: 'Mercato delle curiosità di Bologna 2026',
    fonte: 'bolognatoday.it', url_fonte: URL, orario_testo: '09:00–18:00', indirizzo: 'Via della Fonte, 4',
    date: [], date_quality: 'sconosciuta', riscontri_campi: [],
    evidenza_editoriale: {schema: 1, manager: 'editorial-detail', market: {...identity},
      primary_url: URL, requested_url: URL, final_url: URL, canonical_url: URL,
      publisher: 'bolognatoday.it', source_id: sourceId(URL), redirect_observed: false,
      source_sha256: 'a'.repeat(64), source_bytes: 1500, hash_basis: 'http_response_bytes',
      read_on: '2026-10-20', published_on: '2026-02-14', modified_on: null,
      calendar_mode: 'limit_forecasts', conflicts: [], warnings: [], field_evidence: {},
      facts: {name: 'Mercato delle curiosità di Bologna 2026', location: {}, hours_text: 'Dalle 9 alle 18',
        hours_qualifications: [], archive_marker: false, calendar_complete: true,
        edition_intervals: [{start: '2026-02-21', end: '2026-02-22'}], occurrences: [],
        conditions: [], recurrence_text: '', ...facts}, ...proof}}
}

function withReceipt() {
  const row = rawMarket()
  row.riscontri_campi = [{schema: 1, mercato: {...identity},
    valori: {indirizzo: row.indirizzo, orario_testo: row.orario_testo},
    url: URL, fonte: 'bolognatoday.it', fonte_id: sourceId(URL),
    riga_fonte: sourceId(URL) + ':event-card', letto_il: '2026-10-20', fonte_aggiornata_il: '',
    sha256: 'a'.repeat(64), impronta_tipo: 'html_bytes', ambito: 'pagina',
    metodo: 'pagina_primaria_revisionata', gestore_campi: 'citynews_detail',
    campi_gestiti: ['indirizzo', 'orario_testo']}]
  return row
}

test('the UI allows exactly the reviewed backend hosts and derives the same URL identity', () => {
  const backend = readFileSync(new globalThis.URL('../backend/citynews_urls.py', import.meta.url), 'utf8')
  const hosts = [...backend.matchAll(/"([a-z]+\.it)"/g)].map(match => match[1]).sort()
  assert.deepEqual([...CITYNEWS_HOSTS].sort(), hosts)
  const fixtures = JSON.parse(readFileSync(new globalThis.URL(
    '../backend/tests/fixtures/citynews_detail/manifest.json', import.meta.url), 'utf8'))
  const urls = [...hosts.map(host => `https://www.${host}/eventi/mercato-2026.html`),
    ...fixtures.results.flatMap(item => [item.requested_url, item.final_url])]
  // Exercise SHA padding boundaries and the longest permitted ASCII detail URL.
  for (const length of [55, 56, 63, 64, 119, 120, 511, 1200]) {
    const prefix = 'https://www.bolognatoday.it/eventi/'
    urls.push(prefix + 'a'.repeat(length - prefix.length - 5) + '.html')
  }
  for (const url of urls) {
    assert.deepEqual(citynewsSourceIdentity(url), [new globalThis.URL(url).hostname.slice(4), sourceId(url)])
  }
})

test('unreviewed, altered, normalized or index URLs cannot become Citynews evidence links', () => {
  for (const url of [URL.replace('www.', ''), URL.replace('www.', 'other.'),
    URL.replace('bolognatoday.it', 'bolognatoday.it.attacker.example'),
    URL.replace('bolognatoday.it', 'unreviewedtoday.it'), URL.replace('https:', 'http:'),
    URL.replace('www.', 'user:pass@www.'), URL.replace('.it/', '.it:443/'),
    URL.replace('/eventi/', '/eventi/location/'), URL.replace('/eventi/', '/eventi/tipo/'),
    URL.replace('/eventi/', '/eventi/../eventi/'), URL.replace('/eventi/', '/eventi/%2e%2e/eventi/'),
    URL.replace('/eventi/', '/cronaca/'), URL + '?download=1', URL + '#section', URL + '\n',
    URL.replace('https:', 'HTTPS:'), URL.replace('www.', 'WWW.'),
    'https://www.bolognatoday.it/eventi/', 'javascript:alert(1)',
    'https://www.bolognatoday.it/eventi/' + 'a'.repeat(1200) + '.html']) {
    assert.equal(citynewsSourceIdentity(url), null, url)
    const row = rawMarket({}, {primary_url: url, requested_url: url, final_url: url, canonical_url: url,
      source_id: sourceId(url)})
    row.url_fonte = url
    assert.equal(editorialEvidenceView(adaptMarket(row), TODAY), null, url)
  }
})

test('Citynews historical facts survive the real adapter with separate publication and read dates', () => {
  const record = adaptMarket(rawMarket({hours_text: 'dalle 15 del 21 febbraio',
    hours_qualifications: ['dalle 15 del 21 febbraio']}))
  const view = editorialEvidenceView(record, TODAY)
  assert.equal(view.sourceName, 'Citynews · bolognatoday.it')
  assert.equal(view.sourceUrl, URL)
  assert.equal(view.historical, true)
  assert.match(view.title, /Edizione passata/)
  assert.match(view.hoursLabel, /edizione passata/)
  assert.equal(view.hours, 'dalle 15 del 21 febbraio')
  assert.equal(view.editorialDate, 'Pubblicazione dichiarata: 14 feb 2026')
  assert.equal(view.readOn, '20 ott 2026')
  assert.equal(view.rows.length, 1)
  assert.equal(view.rows[0].hours, '')
  assert.match(view.notes.join(' '), /aperture attuali sono da verificare/)
  assert.equal(record.lastVerified, '')
  assert.equal(record.sourceUpdated, '')
  assert.doesNotMatch(JSON.stringify(view), /Verificato il|Confermato|2027/)
})

test('Citynews evidence cannot move across municipality, province, URL, hash identity or an observed redirect', () => {
  for (const field of ['citta', 'provincia', 'regione']) {
    const row = rawMarket()
    row[field] = 'other'
    assert.equal(editorialEvidenceView(adaptMarket(row), TODAY), null)
  }
  for (const proof of [{source_id: 'citynews-' + 'f'.repeat(24)},
    {publisher: 'romatoday.it'}, {canonical_url: URL.replace('test-', 'other-')},
    {final_url: URL.replace('test-', 'other-'), redirect_observed: true},
    {hash_basis: 'connector_utf8_text'}, {modified_on: '2026-10-20'}]) {
    assert.equal(editorialEvidenceView(adaptMarket(rawMarket({}, proof)), TODAY), null)
  }
  const missingProvince = rawMarket()
  missingProvince.provincia = ''
  missingProvince.evidenza_editoriale.market.provincia = ''
  assert.ok(editorialEvidenceView(adaptMarket(missingProvince), TODAY),
    'A backend-proved blank province stays blank instead of being filled in the browser')
})

test('qualified, partial and programme hours retain their distinct Citynews scope', () => {
  const partial = adaptMarket(rawMarket({edition_intervals: [{start: '2026-11-01', end: '2026-11-01'}],
    occurrences: [occurrence('2026-11-01', '08:30')], hours_text: 'Dalle 8:30'}))
  assert.equal(editorialHoursForDate(partial, '2026-11-01', TODAY),
    'Dalle 08:30; chiusura non indicata per questa data')
  assert.equal(editorialHoursForDate(partial, '2026-11-02', TODAY), 'Orario per questa data non indicato')
  const qualified = 'Venerdì dalle 12 alle 20; sabato e domenica dalle 9 alle 20'
  const multi = adaptMarket(rawMarket({edition_intervals: [{start: '2026-11-06', end: '2026-11-08'}],
    hours_text: qualified, hours_qualifications: [qualified]}))
  assert.equal(editorialEvidenceView(multi, TODAY).hours, qualified)
  assert.equal(editorialEvidenceView(multi, TODAY).rows[0].hours, '')
  assert.equal(editorialHoursForDate(multi, '2026-11-07', TODAY), 'Orario per questa data non indicato')
  for (const [literal, code] of [['Concerto dalle 21 alle 23', 'programme_hours_scope_unrepresented'],
    ['Dalle 9 alle 9', 'clock_interval_not_ordered_or_valid']]) {
    const held = adaptMarket(rawMarket({hours_text: literal, hours_qualifications: [literal],
      occurrences: [occurrence('2026-02-21')]}, {conflicts: [{field: 'hours', code}]}))
    const view = editorialEvidenceView(held, TODAY)
    assert.equal(view.hours, '')
    assert.equal(view.rows.find(row => row.kind === 'date').hours, '')
    assert.ok(view.notes.includes(literal))
    assert.equal(editorialHoursForDate(held, '2026-02-21', TODAY), 'Orario per questa data da verificare')
  }
})

test('Citynews calendar disagreement and cancellation never become opening confirmations', () => {
  const conflict = adaptMarket(rawMarket({edition_intervals: [{start: '2027-11-01', end: '2027-11-01'}],
    occurrences: [occurrence('2027-11-01', '09:00', '18:00')]},
  {conflicts: [{field: 'calendar', code: 'title_edition_year_disagrees'}]}))
  const view = editorialEvidenceView(conflict, TODAY)
  assert.equal(view.calendarConflict, true)
  assert.equal(view.rows[0].status, 'Data da verificare')
  assert.equal(view.rows[0].hours, '')
  for (const [status, label] of [['cancelled', 'Annullato'], ['postponed', 'Rinviato']]) {
    const stopped = adaptMarket(rawMarket({edition_intervals: [{start: '2026-11-01', end: '2026-11-01'}],
      occurrences: [occurrence('2026-11-01', '09:00', '18:00', status)]}))
    assert.equal(editorialEvidenceView(stopped, TODAY).rows[0].status, label)
    assert.equal(editorialEvidenceView(stopped, TODAY).rows[0].hours, '')
    assert.equal(editorialHoursForDate(stopped, '2026-11-01', TODAY), label)
  }
})

test('Citynews field receipts bind their exact source but never invent a modification date', () => {
  const [receipt] = fieldEvidenceSummary(withReceipt(), '2026-10-20')
  assert.equal(receipt.sourceName, 'bolognatoday.it')
  assert.equal(receipt.sourceUrl, URL)
  assert.equal(receipt.readOn, '2026-10-20')
  assert.equal(receipt.sourceDate, '')
  assert.equal(receipt.fields, 'Sede, Orari')
  for (const patch of [{fonte_id: 'citynews-' + 'b'.repeat(24)},
    {url: URL.replace('/eventi/', '/eventi/location/')}, {url: URL + '?query=1'},
    {url: URL.replace('bolognatoday.it', 'attacker.example')}, {fonte: 'romatoday.it'},
    {riga_fonte: sourceId(URL) + ':other'}, {impronta_tipo: 'publisher_parsed_json'},
    {metodo: 'id_fonte'}, {fonte_aggiornata_il: '2026-02-14'}, {sha256: ''}]) {
    const row = withReceipt()
    Object.assign(row.riscontri_campi[0], patch)
    assert.deepEqual(fieldEvidenceSummary(row, '2026-10-20'), [], JSON.stringify(patch))
  }
})

test('authoritative exceptions override editorial dates and qualify a multi-day period', () => {
  const row = rawMarket({edition_intervals: [{start: '2026-11-01', end: '2026-11-03'}],
    occurrences: [occurrence('2026-11-01', '09:00', '18:00'), occurrence('2026-11-02', '09:00', '18:00')]})
  row.eccezioni_calendario = [{data: '2026-11-01', motivo: 'Annullamento comunicato dal Comune'}]
  const market = adaptMarket(row)
  const view = editorialEvidenceView(market, TODAY)
  const date = view.rows.find(item => item.kind === 'date' && item.sortDate === '2026-11-01')
  assert.equal(date.status, 'Annullato')
  assert.equal(date.hours, '')
  assert.match(date.note, /Comune/)
  const period = view.rows.find(item => item.kind === 'interval')
  assert.equal(period.status, 'Variazioni nel periodo')
  assert.match(period.note, /1 nov 2026: Annullato — Annullamento comunicato dal Comune/)
  assert.equal(editorialHoursForDate(market, '2026-11-01', TODAY), 'Annullato')
  assert.equal(editorialHoursForDate(market, '2026-11-02', TODAY), '09:00–18:00')
})

test('regional lazy loading preserves Citynews evidence through the actual React adapter', async () => {
  const previous = globalThis.fetch
  const seen = []
  const row = rawMarket()
  const summary = [row.slug, row.nome, row.citta, row.regione, 'misto', [], null, null,
    'sconosciuta', row.orario_testo, 'sconosciuta', []]
  globalThis.fetch = async url => {
    const path = String(url)
    seen.push(path)
    if (new globalThis.URL(path, 'https://catalog.example').pathname.endsWith('/manifest.json')) return {ok: true, json: async () => ({
      schema: 1, layout: 'regional', total: 1, index: 'data/v1/index-citynews.json',
      regions: [{name: row.regione, count: 1, path: 'data/v1/regions/emilia-romagna-citynews.json'}],
    })}
    if (path.endsWith('/index-citynews.json')) return {ok: true, json: async () => ({schema: 1, markets: [summary]})}
    if (path.endsWith('/emilia-romagna-citynews.json')) return {ok: true, json: async () => ({schema: 1, markets: [row]})}
    throw new Error('Unexpected request: ' + path)
  }
  try {
    const {fetchMarkets, fetchMarketById} = await import('../src/services/staticMarkets.js')
    const [compact] = await fetchMarkets()
    assert.equal(editorialEvidenceView(adaptMarket(compact), TODAY), null)
    const detailed = await fetchMarketById(row.slug)
    assert.deepEqual(detailed.evidenza_editoriale, row.evidenza_editoriale)
    const view = editorialEvidenceView(adaptMarket(detailed), TODAY)
    assert.equal(view.historical, true)
    assert.equal(view.sourceUrl, URL)
    assert.equal(view.readOn, '20 ott 2026')
    assert.equal(seen.length, 3)
    assert.ok(seen.every(path => path.startsWith('/data/v1/')), 'Only published static catalog files are fetched')
  } finally { globalThis.fetch = previous }
})
