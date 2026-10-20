import test from 'node:test'
import assert from 'node:assert/strict'
import { sourceCalendarView, sourceHoursForDate, sourceContacts, sourceDateLabel } from '../src/lib/sourceCalendar.js'

const TODAY = new Date(2026, 9, 20, 12)
const occurrence = (date, start, end, extra = {}) => ({
  date, start_time: start, end_time: end, status: 'source_listed', note: null, ...extra,
})
const market = (occurrences, more = {}) => ({
  hours: '07:30–12:30',
  sourceCalendar: {occorrenze: occurrences, intervalli: [], ambito_calendario: 'explicit_visible_list'},
  sourceDetail: {evento: {}}, ...more,
})

test('the dated Lana exception overrides general hours without filling a missing closing time', () => {
  const record = market([
    occurrence('2026-10-23', '07:30', '12:30'),
    occurrence('2026-10-30', '07:30', null),
    occurrence('2026-12-24', '07:30', '13:00', {note: '24 dicembre termina alle 13:00'}),
  ])
  assert.equal(sourceHoursForDate(record, '2026-12-24'), '07:30–13:00')
  assert.match(sourceHoursForDate(record, '2026-10-30'), /Dalle 07:30; chiusura non indicata/)
  assert.doesNotMatch(sourceHoursForDate(record, '2026-10-30'), /12:30/)
  const schedule = sourceCalendarView(record, TODAY)
  assert.equal(schedule.rows.length, 3)
  assert.equal(schedule.hasVariations, true)
  assert.equal(schedule.rows.at(-1).note, '24 dicembre termina alle 13:00')
  assert.match(schedule.rows.at(-1).label, /2026/)
})

test('split sessions on one day remain separate and a date has no invented fallback time', () => {
  const record = market([
    occurrence('2026-10-24', '08:00', '12:00'),
    occurrence('2026-10-24', '14:00', '18:00'),
  ])
  assert.equal(sourceHoursForDate(record, '2026-10-24'), '08:00–12:00 · 14:00–18:00')
  assert.equal(sourceCalendarView(record, TODAY).rows.length, 2)
  assert.equal(sourceHoursForDate(record, '2026-10-25'), 'Orario per questa data non indicato')
})

test('multi-day interval boundary times never become a daily 08:00–20:00 opening', () => {
  const bounds = {interval_start: '2026-10-24', interval_end: '2026-10-26'}
  const record = market([
    occurrence('2026-10-24', '08:00', null, bounds),
    occurrence('2026-10-25', null, null, bounds),
    occurrence('2026-10-26', null, '20:00', bounds),
  ])
  record.sourceCalendar.intervalli = [{start: '2026-10-24', end: '2026-10-26',
    start_time: '08:00', end_time: '20:00', hours_scope: 'interval_boundaries',
    continuous_opening_confirmed: false}]
  const schedule = sourceCalendarView(record, TODAY)
  assert.equal(schedule.rows.length, 1)
  assert.equal(schedule.rows[0].kind, 'interval')
  assert.match(schedule.rows[0].hours, /Inizio .*08:00; Termine .*20:00/)
  assert.doesNotMatch(schedule.rows[0].hours, /08:00–20:00/)
  assert.match(schedule.rows[0].note, /singoli giorni da verificare/)
  assert.equal(sourceHoursForDate(record, '2026-10-24'), 'Inizio del periodo alle 08:00')
  assert.equal(sourceHoursForDate(record, '2026-10-25'), 'Orario del singolo giorno da verificare')
  assert.equal(sourceHoursForDate(record, '2026-10-26'), 'Termine del periodo alle 20:00')
})

test('cancelled and postponed occurrences remain visible as notices, never active opening claims', () => {
  const record = market([
    occurrence('2026-10-24', '08:00', '12:00', {status: 'cancelled', note: 'Maltempo'}),
    occurrence('2026-10-25', '08:00', '12:00', {status: 'postponed'}),
  ])
  assert.equal(sourceHoursForDate(record, '2026-10-24'), 'Annullato')
  assert.equal(sourceHoursForDate(record, '2026-10-25'), 'Rinviato')
  const schedule = sourceCalendarView(record, TODAY)
  assert.deepEqual(schedule.rows.map(item => item.status), ['Annullato', 'Rinviato'])
  assert.deepEqual(schedule.rows.map(item => item.hours), ['', ''])
  assert.equal(schedule.rows[0].note, 'Maltempo')
})

test('cancelled and postponed multi-day editions are one labelled interval without opening claims', () => {
  for (const [status, label] of [['cancelled', 'Annullato'], ['postponed', 'Rinviato']]) {
    const bounds = {interval_start: '2026-10-24', interval_end: '2026-10-25', status}
    const record = market([
      occurrence('2026-10-24', '08:00', null, bounds),
      occurrence('2026-10-25', null, '20:00', bounds),
    ])
    record.sourceCalendar.intervalli = [{start: '2026-10-24', end: '2026-10-25',
      start_time: '08:00', end_time: '20:00', hours_scope: 'interval_boundaries',
      continuous_opening_confirmed: false, status}]
    const {rows} = sourceCalendarView(record, TODAY)
    assert.equal(rows.length, 1)
    assert.equal(rows[0].status, label)
    assert.equal(rows[0].hours, '')
    assert.equal(sourceHoursForDate(record, '2026-10-24'), label)
  }
})

test('authoritative calendar cancellations override every source session and compact general hours', () => {
  const record = market([
    occurrence('2026-10-24', '08:00', '12:00'),
    occurrence('2026-10-24', '14:00', '18:00'),
    occurrence('2026-10-25', '08:00', '12:00'),
  ], {calendarExceptions: [{data: '2026-10-24', motivo: 'Edizione annullata dal Comune'}]})
  const {rows} = sourceCalendarView(record, TODAY)
  assert.equal(sourceHoursForDate(record, '2026-10-24'), 'Annullato')
  assert.equal(sourceHoursForDate({...record, sourceCalendar: null}, '2026-10-24'), 'Annullato')
  assert.ok(rows.filter(row => row.sortDate === '2026-10-24')
    .every(row => row.status === 'Annullato' && row.hours === '' && row.note.includes('Comune')))
  assert.equal(rows.at(-1).hours, '08:00–12:00')
})

test('a cancellation within a period is attached to that interval and never shown as open that day', () => {
  const bounds = {interval_start: '2026-10-24', interval_end: '2026-10-26'}
  const record = market([
    occurrence('2026-10-24', '08:00', null, bounds),
    occurrence('2026-10-25', null, null, bounds),
    occurrence('2026-10-26', null, '20:00', bounds),
  ], {calendarExceptions: [{data: '2026-10-25', motivo: 'Chiusura comunicata dal Comune'}]})
  record.sourceCalendar.intervalli = [{start: '2026-10-24', end: '2026-10-26',
    start_time: '08:00', end_time: '20:00', hours_scope: 'interval_boundaries',
    continuous_opening_confirmed: false, status: 'source_listed'}]
  const {rows} = sourceCalendarView(record, TODAY)
  assert.equal(rows.length, 1)
  assert.equal(rows[0].status, 'Variazioni nel periodo')
  assert.match(rows[0].note, /25 ott 2026: Annullato — Chiusura comunicata dal Comune/)
  assert.equal(sourceHoursForDate(record, '2026-10-25'), 'Annullato')
  assert.equal(sourceHoursForDate(record, '2026-10-26'), 'Termine del periodo alle 20:00')
})

test('past editions retain their original year and invalid dates never become future occurrences', () => {
  const record = market([
    occurrence('2025-12-24', '08:00', '12:00'),
    occurrence('2026-02-31', '08:00', '12:00'),
  ])
  assert.deepEqual(sourceCalendarView(record, TODAY).rows, [])
  assert.equal(sourceDateLabel('2026-02-31'), 'Data da verificare')
  assert.match(sourceDateLabel('2025-12-24'), /2025/)
})

test('conditional notes survive with a clear limit for a source containing just one occurrence', () => {
  const record = market([occurrence('2026-10-24', '08:00', '12:00')])
  record.sourceCalendar.ambito_calendario = 'schema_occurrence_only'
  record.sourceDetail.evento = {
    conditions: ['Sospeso in caso di maltempo'],
    calendar_notes: ['Sospeso in caso di maltempo'],
    hours_qualifications: ['07:30–12:30'],
  }
  const {notes} = sourceCalendarView(record, TODAY)
  assert.equal(notes.filter(value => value === 'Sospeso in caso di maltempo').length, 1)
  assert.equal(notes.includes('07:30–12:30'), false)
  assert.match(notes.at(-1), /singola edizione/)
})

test('source contacts are plain scoped facts with safe link schemes', () => {
  const detail = {evento: {
    organizer: {name: 'Organizzatore riportato', url: 'javascript:alert(1)'},
    contacts: [
      {kind: 'telephone', value: '+39 055 123456'},
      {kind: 'email', value: 'info@example.com'},
      {kind: 'website', value: 'https://example.com/info'},
      {kind: 'website', value: 'javascript:alert(1)'},
      {kind: 'website', value: 'https://user:secret@example.com/'},
      {kind: 'email', value: 'info@example.com?body=changed'},
    ],
  }}
  const contacts = sourceContacts(detail)
  assert.equal(contacts.organizer.label, 'Organizzatore riportato')
  assert.equal(contacts.organizer.href, '')
  assert.deepEqual(contacts.links.map(item => item.href), [
    'tel:+39055123456', 'mailto:info@example.com', 'https://example.com/info',
  ])
})

test('legacy summaries keep their published general hours until full detail is loaded', () => {
  assert.equal(sourceHoursForDate({hours: '08:00–13:00'}, '2026-10-24'), '08:00–13:00')
  assert.equal(sourceHoursForDate({}, '2026-10-24'), 'Orario da verificare')
  assert.deepEqual(sourceCalendarView({}, TODAY).rows, [])
})
