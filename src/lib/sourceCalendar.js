import { localDateISO } from './dateDisclosure.js'

const active = new Set(['source_listed', 'rescheduled'])
const statusLabels = {
  source_listed: '', cancelled: 'Annullato', postponed: 'Rinviato', rescheduled: 'Spostato',
}
const text = value => typeof value === 'string' ? value.trim() : ''
const clock = value => typeof value === 'string' && /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(value)
  ? value : ''

function validDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  const day = new Date(value + 'T12:00:00Z')
  return Number.isFinite(day.getTime()) && day.toISOString().slice(0, 10) === value
}

export function sourceDateLabel(value) {
  return validDate(value) ? new Date(value + 'T12:00:00').toLocaleDateString('it-IT', {
    weekday: 'short', day: 'numeric', month: 'short', year: 'numeric',
  }) : 'Data da verificare'
}

function occurrenceHours(item) {
  const start = clock(item.start_time)
  const end = clock(item.end_time)
  if (start && end) return `${start}–${end}`
  if (start) return `Dalle ${start}; chiusura non indicata per questa data`
  if (end) return `Termine alle ${end}; apertura non indicata per questa data`
  return 'Orario del giorno non indicato'
}

function upcomingOccurrences(calendar, today) {
  if (!calendar || !Array.isArray(calendar.occorrenze)) return []
  return calendar.occorrenze.filter(item => item && validDate(item.date) &&
    item.date >= today && Object.hasOwn(statusLabels, item.status))
}

function calendarExceptions(market, today) {
  const exceptions = new Map()
  for (const item of Array.isArray(market?.calendarExceptions) ? market.calendarExceptions : []) {
    if (!item || !validDate(item.data) || item.data < today) continue
    const reasons = exceptions.get(item.data) || []
    if (text(item.motivo) && !reasons.includes(text(item.motivo))) reasons.push(text(item.motivo))
    exceptions.set(item.data, reasons)
  }
  return exceptions
}

const intervalKey = item => item.interval_start + '/' + item.interval_end

/** Never spread a time range over every day in a multi-day interval. */
export function sourceCalendarView(market, now = new Date()) {
  const calendar = market?.sourceCalendar
  const facts = market?.sourceDetail?.evento || {}
  const today = localDateISO(now)
  const exceptions = calendarExceptions(market, today)
  const intervals = (Array.isArray(calendar?.intervalli) ? calendar.intervalli : [])
    .filter(item => item && validDate(item.start) && validDate(item.end) &&
      item.start <= item.end && item.end >= today &&
      item.hours_scope === 'interval_boundaries' && item.continuous_opening_confirmed === false &&
      Object.hasOwn(statusLabels, item.status || 'source_listed'))
  const intervalKeys = new Set(intervals.map(item => item.start + '/' + item.end))
  const occurrences = upcomingOccurrences(calendar, today).map(item => exceptions.has(item.date)
    ? {...item, status: 'cancelled', note: [...new Set([text(item.note), ...exceptions.get(item.date)])]
      .filter(Boolean).join(' · ')} : item)
  const rows = occurrences
    .filter(item => !intervalKeys.has(intervalKey(item)))
    .map(item => ({
      key: [item.date, item.start_time, item.end_time, item.status].join('/'),
      sortDate: item.date, label: sourceDateLabel(item.date),
      hours: active.has(item.status) ? occurrenceHours(item) : '',
      status: statusLabels[item.status], note: text(item.note), kind: 'date',
    }))
  for (const item of intervals) {
    const status = item.status || 'source_listed'
    const notices = new Map()
    for (const occurrence of occurrences.filter(value => intervalKey(value) === item.start + '/' + item.end)) {
      if (occurrence.status !== status || exceptions.has(occurrence.date)) {
        notices.set(occurrence.date, `${sourceDateLabel(occurrence.date)}: ${statusLabels[occurrence.status] || 'Riportato dalla fonte'}${text(occurrence.note) ? ' — ' + text(occurrence.note) : ''}`)
      }
    }
    for (const [day, reasons] of exceptions) {
      if (item.start <= day && day <= item.end && !notices.has(day)) {
        notices.set(day, `${sourceDateLabel(day)}: Annullato${reasons.length ? ' — ' + reasons.join(' · ') : ''}`)
      }
    }
    const boundaries = []
    if (clock(item.start_time)) boundaries.push(`Inizio ${sourceDateLabel(item.start)}, ore ${item.start_time}`)
    if (clock(item.end_time)) boundaries.push(`Termine ${sourceDateLabel(item.end)}, ore ${item.end_time}`)
    rows.push({
      key: item.start + '/' + item.end, sortDate: item.start,
      label: `${sourceDateLabel(item.start)} – ${sourceDateLabel(item.end)}`,
      hours: active.has(status) ? boundaries.join('; ') || 'Orari del periodo non indicati' : '',
      status: statusLabels[status] || (notices.size ? 'Variazioni nel periodo' : ''), kind: 'interval',
      note: [active.has(status) ? 'Il periodo è riportato dalla fonte. Aperture e orari dei singoli giorni da verificare.' : '',
        ...[...notices].sort(([a], [b]) => a.localeCompare(b)).map(([, notice]) => notice)]
        .filter(Boolean).join(' '),
    })
  }
  for (const [day, reasons] of exceptions) {
    if (occurrences.some(item => item.date === day) || intervals.some(item => item.start <= day && day <= item.end)) continue
    rows.push({key: day + '/exception', sortDate: day, label: sourceDateLabel(day),
      hours: '', status: 'Annullato', note: reasons.join(' · '), kind: 'date'})
  }
  rows.sort((a, b) => a.sortDate.localeCompare(b.sortDate) || a.key.localeCompare(b.key))
  const notes = [...new Set(['conditions', 'calendar_notes', 'hours_qualifications']
    .flatMap(key => Array.isArray(facts[key]) ? facts[key] : [])
    .map(text).filter(value => value && !text(market?.hours).includes(value)))]
  if (calendar?.ambito_calendario === 'schema_occurrence_only') {
    notes.push('La fonte riporta questa singola edizione. Altri appuntamenti non sono disponibili nel calendario letto.')
  }
  const hasVariations = rows.some(row => row.kind === 'interval' || row.note || row.status) ||
    new Set(rows.map(row => row.hours)).size > 1
  return { rows, notes, hasVariations }
}

/** Use only the hours attached to the selected date; never fill missing ends. */
export function sourceHoursForDate(market, day) {
  if (calendarExceptions(market, day).has(day)) return 'Annullato'
  if (!market?.sourceCalendar) return text(market?.hours) || 'Orario da verificare'
  if (!validDate(day)) return text(market?.hours) || 'Orario da verificare'
  const occurrences = upcomingOccurrences(market.sourceCalendar, day)
    .filter(item => item.date === day)
  if (!occurrences.length) return 'Orario per questa data non indicato'
  return [...new Set(occurrences.map(item => {
    if (!active.has(item.status)) return statusLabels[item.status]
    if (item.interval_start || item.interval_end) {
      const interval = (market.sourceCalendar.intervalli || []).find(value => value.start === item.interval_start && value.end === item.interval_end)
      if (interval && interval.status && !active.has(interval.status)) return statusLabels[interval.status] || 'Stato da verificare'
      if (item.date === item.interval_start && clock(item.start_time)) return `Inizio del periodo alle ${item.start_time}`
      if (item.date === item.interval_end && clock(item.end_time)) return `Termine del periodo alle ${item.end_time}`
      return 'Orario del singolo giorno da verificare'
    }
    return occurrenceHours(item)
  }))].join(' · ')
}

function website(value) {
  try {
    const url = new URL(value)
    return ['https:', 'http:'].includes(url.protocol) && !url.username && !url.password ? url.href : ''
  } catch { return '' }
}

export function sourceContacts(detail) {
  const facts = detail?.evento || {}
  const organizer = facts.organizer && text(facts.organizer.name)
    ? { label: facts.organizer.name, href: website(facts.organizer.url) } : null
  const links = (Array.isArray(facts.contacts) ? facts.contacts : []).flatMap(item => {
    const value = text(item?.value)
    if (item?.kind === 'email' && /^[^\s?@]+@[^\s?@]+\.[^\s?@]+$/.test(value)) {
      return [{ label: value, href: 'mailto:' + value }]
    }
    if (item?.kind === 'telephone' && /^[+\d() .-]{5,40}$/.test(value) && /\d/.test(value)) {
      return [{ label: value, href: 'tel:' + value.replace(/[() .-]/g, '') }]
    }
    const href = item?.kind === 'website' ? website(value) : ''
    return href ? [{ label: 'Sito indicato dalla fonte', href }] : []
  })
  return { organizer, links }
}
