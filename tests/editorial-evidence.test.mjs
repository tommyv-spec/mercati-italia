import test from 'node:test'
import assert from 'node:assert/strict'
import { editorialContacts, editorialEvidenceView, editorialHoursForDate, editorialSummaryView } from '../src/lib/editorialEvidence.js'
import { mergeContacts, sourceHoursForDate } from '../src/lib/sourceCalendar.js'

const TODAY = new Date(2026, 9, 20, 12)
const URL = 'https://www.cosedicasa.com/mercatini/bologna-piazza-s-stefano'
const occurrence = (day, start = null, end = null, status = 'source_listed') => ({
  date: day, start_time: start, end_time: end, status,
})
function market(facts = {}, more = {}) {
  return {id: 'market-example', sourceUrl: URL, hours: '09:00–18:00',
    editorialEvidence: {
      schema: 1, manager: 'editorial-detail', market: {slug: 'market-example'},
      primary_url: URL, requested_url: URL, final_url: URL, canonical_url: URL,
      redirect_observed: false, publisher: 'cosedicasa.com', source_id: 'bologna-piazza-s-stefano',
      source_sha256: 'a'.repeat(64), source_bytes: 1234, read_on: '2026-10-20',
      published_on: '2024-01-01', modified_on: '2025-01-07',
      calendar_mode: 'limit_forecasts', conflicts: [], warnings: [],
      facts: {name: 'Mercato di esempio', location: {}, hours_text: '09:00–18:00',
        archive_marker: false, calendar_complete: true, edition_intervals: [],
        occurrences: [], conditions: [], recurrence_text: '', ...facts}, ...more,
    }}
}

test('an edition interval remains one period without daily dates or implied daily hours', () => {
  const record = market({edition_intervals: [{start: '2026-11-07', end: '2026-11-08'}]})
  const view = editorialEvidenceView(record, TODAY)
  assert.equal(view.rows.length, 1)
  assert.equal(view.rows[0].kind, 'interval')
  assert.match(view.rows[0].label, /7 nov 2026 – 8 nov 2026/)
  assert.equal(view.rows[0].hours, '')
  assert.match(view.rows[0].note, /non specifica le aperture dei singoli giorni/)
  assert.equal(editorialHoursForDate(record, '2026-11-08', TODAY), 'Orario per questa data non indicato')
})

test('a recently read old edition retains its original year and labels historical hours', () => {
  const record = market({edition_intervals: [{start: '2025-06-01', end: '2025-08-31'}]})
  const view = editorialEvidenceView(record, TODAY)
  assert.equal(view.historical, true)
  assert.match(view.title, /Edizione passata/)
  assert.match(view.hoursLabel, /edizione passata/)
  assert.match(view.rows[0].label, /2025/)
  assert.equal(view.rows[0].status, 'Periodo passato')
  assert.match(view.notes.join(' '), /aperture attuali sono da verificare/)
  assert.doesNotMatch(view.notes.join(' '), /chiuso definitivamente/)
})

test('explicit past selected dates are historical even without a broad edition interval', () => {
  const record = market({occurrences: [occurrence('2026-09-11'), occurrence('2026-09-25')]})
  const view = editorialEvidenceView(record, TODAY)
  assert.equal(view.historical, true)
  assert.equal(view.rows.length, 2)
  assert.ok(view.rows.every(row => row.status === 'Data passata'))
  assert.doesNotMatch(JSON.stringify(view), /2027/)
})

test('a visible single date and its identical edition bound are shown only once', () => {
  const record = market({occurrences: [occurrence('2026-06-05'), occurrence('2026-06-12')],
    edition_intervals: [{start: '2026-06-05', end: '2026-06-05'}, {start: '2026-06-12', end: '2026-06-12'}]})
  const view = editorialEvidenceView(record, TODAY)
  assert.equal(view.rows.length, 2)
  assert.ok(view.rows.every(row => row.kind === 'date'))
  assert.equal(view.historical, true)
})

test('date conflicts suppress per-date opening claims while independent hours remain source facts', () => {
  const record = market({occurrences: [occurrence('2026-10-25', '09:00', '18:00')]},
    {conflicts: [{field: 'calendar', code: 'source_calendar_disagrees'}]})
  const view = editorialEvidenceView(record, TODAY)
  assert.equal(view.calendarConflict, true)
  assert.match(view.notes.join(' '), /indicazioni discordanti sul calendario/)
  assert.equal(view.rows[0].status, 'Data da verificare')
  assert.equal(view.rows[0].hours, '')
  assert.equal(view.hours, '09:00–18:00')
  assert.equal(editorialHoursForDate(record, '2026-10-25', TODAY), 'Orario per questa data da verificare')
})

test('conflicting hours are not selected silently from the source facts', () => {
  const record = market({occurrences: [occurrence('2026-10-25', '09:00', '18:00')]},
    {conflicts: [{field: 'hours', code: 'hours_disagree'}]})
  const view = editorialEvidenceView(record, TODAY)
  assert.equal(view.hours, '')
  assert.equal(view.rows[0].hours, '')
  assert.match(view.notes.join(' '), /orari discordanti/)
})

test('partial and midnight hours stay attached to exact source dates without general fallback', () => {
  const record = market({occurrences: [occurrence('2026-10-25', '09:00'),
    occurrence('2026-10-26', '18:00', '24:00')]}, {calendar_mode: 'reported_explicit'})
  assert.equal(editorialHoursForDate(record, '2026-10-25', TODAY), 'Dalle 09:00; chiusura non indicata per questa data')
  assert.equal(editorialHoursForDate(record, '2026-10-26', TODAY), '18:00–24:00')
  assert.equal(editorialHoursForDate(record, '2026-10-27', TODAY), 'Orario per questa data non indicato')
  assert.equal(editorialEvidenceView(record, TODAY).rows.length, 2)
})

test('cancelled and postponed dates remain notices with no opening hours', () => {
  const record = market({occurrences: [occurrence('2026-10-25', '09:00', '18:00', 'cancelled'),
    occurrence('2026-10-26', '09:00', '18:00', 'postponed')]})
  const view = editorialEvidenceView(record, TODAY)
  assert.deepEqual(view.rows.map(row => row.status), ['Annullato', 'Rinviato'])
  assert.deepEqual(view.rows.map(row => row.hours), ['', ''])
  assert.equal(editorialHoursForDate(record, '2026-10-25', TODAY), 'Annullato')
  assert.equal(editorialHoursForDate(record, '2026-10-26', TODAY), 'Rinviato')
})

test('a monthly rule and an extra date without a year never generate UI calendar dates', () => {
  const record = market({calendar_complete: false, recurrence_text: 'Terza domenica, da marzo a ottobre',
    calendar_rules: [{kind: 'monthly_ordinal', ordinal: 3, weekday: 6}],
    scope_statements: [{kind: 'extra_edition_claim', text: 'Edizione straordinaria l’11 novembre, anno non indicato'}],
    conditions: [{kind: 'weather_condition', text: 'Annullato in caso di maltempo'}]})
  const view = editorialEvidenceView(record, TODAY)
  assert.deepEqual(view.rows, [])
  assert.equal(view.recurrence, 'Terza domenica, da marzo a ottobre')
  assert.match(view.notes.join(' '), /anno non indicato/)
  assert.match(view.notes.join(' '), /in caso di maltempo/)
  assert.match(view.notes.join(' '), /calendario nella pagina è incompleto/)
})

test('the read date does not replace editorial date or become an individual verification', () => {
  const view = editorialEvidenceView(market(), TODAY)
  assert.equal(view.readOn, '20 ott 2026')
  assert.equal(view.editorialDate, 'Modifica dichiarata: 7 gen 2025')
  assert.equal(view.sourceName, 'Cose di Casa')
  assert.equal(view.sourceUrl, URL)
  assert.doesNotMatch(JSON.stringify(view), /Verificato il|Confermato|verificato_il|lastVerified/)
  const noContentDate = market({}, {modified_on: null, published_on: null})
  assert.equal(editorialEvidenceView(noContentDate, TODAY).editorialDate, 'Data dei contenuti non dichiarata')
})

test('evidence belonging to another market, source, day or unsafe URL is not displayed', () => {
  for (const override of [{market: {slug: 'another'}}, {primary_url: URL + '-other'},
    {publisher: 'unreviewed.example'}, {source_id: 'another'}, {source_sha256: ''},
    {read_on: '2026-10-21'}, {read_on: '2026-02-31'}, {source_bytes: 1},
    {final_url: 'javascript:alert(1)'}, {modified_on: '2026-10-21'}]) {
    assert.equal(editorialEvidenceView(market({}, override), TODAY), null)
  }
  assert.equal(editorialEvidenceView({}, TODAY), null)
})

test('an observed CDC alias links to the actual final page; canonical alone does not prove it', () => {
  const final = URL + '-renamed'
  assert.equal(editorialEvidenceView(market({}, {final_url: final, canonical_url: final}), TODAY), null)
  const view = editorialEvidenceView(market({}, {final_url: final, canonical_url: final, redirect_observed: true}), TODAY)
  assert.equal(view.sourceUrl, final)
})

test('general date tooltip uses exact editorial occurrence without changing Happings calendar priority', () => {
  const record = market({occurrences: [occurrence('2026-10-25', '09:00')]})
  // Keep this regression independent of the wall-clock date used by the UI.
  record.editorialEvidence.read_on = '2020-01-01'
  record.editorialEvidence.published_on = null
  record.editorialEvidence.modified_on = null
  assert.match(sourceHoursForDate(record, '2026-10-25'), /chiusura non indicata/)
  assert.doesNotMatch(sourceHoursForDate(record, '2026-10-25'), /18:00/)
  record.sourceCalendar = {occorrenze: [occurrence('2026-10-25', '07:30', '12:30')]}
  assert.equal(sourceHoursForDate(record, '2026-10-25'), '07:30–12:30')
  record.calendarExceptions = [{data: '2026-10-25', motivo: 'Edizione annullata'}]
  assert.equal(sourceHoursForDate(record, '2026-10-25'), 'Annullato')
})

test('archived hours do not present an older complete time range as current', () => {
  const record = market({archive_marker: true, hours_text: 'Dalle 20:00',
    edition_intervals: [{start: '2023-08-18', end: '2023-08-18'}],
    recurrence_text: 'Edizione del 18 agosto 2023'})
  record.hours = '20:00–20:00'
  record.recurrence = 'Mensile'
  const original = structuredClone(record)
  const summary = editorialSummaryView(record, TODAY)
  assert.equal(summary.hours, 'Orari attuali da verificare')
  assert.equal(summary.recurrence, '')
  assert.equal(summary.evidence.hours, 'Dalle 20:00')
  assert.equal(summary.evidence.recurrence, 'Edizione del 18 agosto 2023')
  assert.match(summary.evidence.hoursLabel, /edizione passata/)
  assert.deepEqual(record, original)
})

test('past edition bounds qualify the summary even without an archive marker', () => {
  const record = market({hours_text: 'Dalle 10:00',
    edition_intervals: [{start: '2025-05-23', end: '2025-05-26'}]})
  record.hours = '18:00–24:00'
  record.recurrence = 'Ogni domenica'
  const summary = editorialSummaryView(record, TODAY)
  assert.equal(summary.hours, 'Orari attuali da verificare')
  assert.equal(summary.recurrence, '')
  assert.equal(summary.evidence.hours, 'Dalle 10:00')
  assert.equal(summary.evidence.rows[0].status, 'Periodo passato')
})

test('a current edition keeps existing general hours and recurrence unchanged', () => {
  const record = market({edition_intervals: [{start: '2026-10-01', end: '2026-12-31'}]})
  record.recurrence = 'Ogni domenica'
  const summary = editorialSummaryView(record, TODAY)
  assert.equal(summary.evidence.historical, false)
  assert.equal(summary.hours, record.hours)
  assert.equal(summary.recurrence, record.recurrence)
})

test('missing or unbound historical evidence cannot change the general summary', () => {
  const records = [market({archive_marker: true}, {market: {slug: 'another-market'}}),
    market({archive_marker: true}, {read_on: '2026-10-21'}),
    {hours: '07:00–13:00', recurrence: 'Ogni martedì'}]
  for (const record of records) {
    record.recurrence = 'Ogni martedì'
    const summary = editorialSummaryView(record, TODAY)
    assert.equal(summary.evidence, null)
    assert.equal(summary.hours, record.hours)
    assert.equal(summary.recurrence, record.recurrence)
  }
})

test('the organiser, phones, emails and websites on the page become contact links', () => {
  const rows = [
    {field: 'organizer', value: 'Associazione mON! snc'},
    {field: 'phone', value: '346/0430009; 0322/231111'},
    {field: 'contacts', value: 'mon.mercatino@gmail.com'},
    {field: 'website', value: 'http://m-on.info/; www.comune.arona.no.it'},
    {field: 'facebook', value: 'https://www.facebook.com/lasoffittainpiazza/'},
    {field: 'exhibitors', value: '100'},
    {field: 'website', value: 'javascript:alert(1)'},
  ]
  const contacts = editorialContacts(market({source_rows: rows}), TODAY)
  assert.deepEqual(contacts.organizer, {label: 'Associazione mON! snc', href: ''})
  assert.deepEqual(contacts.links.map(item => item.href), [
    'tel:3460430009', 'tel:0322231111', 'mailto:mon.mercatino@gmail.com',
    'http://m-on.info/', 'https://www.comune.arona.no.it/', 'https://www.facebook.com/lasoffittainpiazza/'])
  assert.equal(contacts.links[3].label, 'm-on.info')
  // Evidence bound to another market shows nothing.
  assert.deepEqual(editorialContacts({...market({source_rows: rows}), id: 'other'}, TODAY), {organizer: null, links: []})
  const merged = mergeContacts({organizer: null, links: [{label: 'x', href: 'tel:3460430009'}]}, contacts)
  assert.equal(merged.organizer.label, 'Associazione mON! snc')
  assert.equal(merged.links.length, 6)
})
