import { localDateISO } from './dateDisclosure.js'
import { citynewsSourceIdentity } from './citynewsIdentity.js'

const text = value => typeof value === 'string' ? value.trim() : ''
const list = value => Array.isArray(value) ? value : []
const calendarFields = new Set(['calendar', 'recurrence', 'edition', 'occurrences', 'suspensions'])
const statusLabels = {source_listed: '', rescheduled: 'Spostato', cancelled: 'Annullato', postponed: 'Rinviato'}

function validDate(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}$/.test(value)) return false
  const parsed = new Date(value + 'T12:00:00Z')
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value
}

function dateLabel(value) {
  return new Date(value + 'T12:00:00').toLocaleDateString('it-IT', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

function sourceIdentity(value) {
  try {
    const url = new URL(value)
    if (url.protocol !== 'https:' || url.username || url.password || url.port || url.search || url.hash) return null
    let match
    if (url.host === 'www.cosedicasa.com' &&
        (match = url.pathname.match(/^\/mercatini\/([a-z0-9]+(?:-[a-z0-9]+)*)\/?$/))) {
      return ['cosedicasa.com', match[1]]
    }
    if (url.host === 'www.eventiesagre.it' &&
        (match = url.pathname.match(/^\/(?:Mercatini|Eventi)_[A-Za-z+]+\/(\d+)_[^/]+\.html$/))) {
      return ['eventiesagre.it', match[1]]
    }
  } catch { /* A malformed URL is not displayable evidence. */ }
  return citynewsSourceIdentity(value)
}

function boundEvidence(market, today) {
  const proof = market?.editorialEvidence
  const bound = sourceIdentity(proof?.primary_url)
  const final = sourceIdentity(proof?.final_url)
  if (!proof || proof.schema !== 1 || proof.manager !== 'editorial-detail' ||
      proof.market?.slug !== market?.id || proof.primary_url !== market?.sourceUrl ||
      proof.requested_url !== proof.primary_url || !bound || !final ||
      bound[0] !== proof.publisher || bound[1] !== proof.source_id || final[0] !== bound[0] ||
      (final[1] !== bound[1] && (bound[0] !== 'cosedicasa.com' || proof.redirect_observed !== true)) ||
      !/^[a-f0-9]{64}$/.test(proof.source_sha256 || '') ||
      !Number.isInteger(proof.source_bytes) || proof.source_bytes < 100 || proof.source_bytes > 2500000 ||
      !validDate(proof.read_on) || proof.read_on > today ||
      !['limit_forecasts', 'reported_explicit'].includes(proof.calendar_mode) ||
      !proof.facts || typeof proof.facts !== 'object' || Array.isArray(proof.facts)) return null
  for (const field of ['published_on', 'modified_on']) {
    if (proof[field] && (!validDate(proof[field]) || proof[field] > proof.read_on)) return null
  }
  if (bound[1].startsWith('citynews-') && (
      proof.final_url !== proof.primary_url || proof.canonical_url !== proof.primary_url ||
      proof.redirect_observed !== false || proof.hash_basis !== 'http_response_bytes' || proof.modified_on ||
      proof.market.citta !== market.originalCity || proof.market.provincia !== market.province ||
      proof.market.regione !== market.region)) return null
  return proof
}

function conflictFields(proof) {
  return new Set(list(proof.conflicts).flatMap(item => {
    if (item && typeof item === 'object' && text(item.field)) return [item.field]
    return typeof item === 'string' && /calendar|edition|recurrence|archive_marker_date/.test(item) ? ['calendar'] : []
  }))
}

function intervals(facts) {
  return list(facts.edition_intervals).filter(item => item && validDate(item.start) &&
    validDate(item.end) && item.start <= item.end).slice(0, 100)
}

function occurrences(facts) {
  return list(facts.occurrences).filter(item => item && validDate(item.date) &&
    Object.hasOwn(statusLabels, item.status)).slice(0, 600)
}

function isPastEdition(facts, today) {
  if (facts.archive_marker === true) return true
  const bounds = intervals(facts)
  const dates = occurrences(facts)
  return (bounds.length > 0 || dates.length > 0) &&
    bounds.every(item => item.end < today) && dates.every(item => item.date < today)
}

function calendarExceptions(market) {
  return new Map(list(market?.calendarExceptions).filter(item => item && validDate(item.data))
    .map(item => [item.data, text(item.motivo)]))
}

const clock = value => typeof value === 'string' && /^(?:(?:[01]\d|2[0-3]):[0-5]\d|24:00)$/.test(value) ? value : ''
function occurrenceHours(item) {
  const start = clock(item.start_time), end = clock(item.end_time)
  if (start && end) return `${start}–${end}`
  if (start) return `Dalle ${start}; chiusura non indicata per questa data`
  if (end) return `Termine alle ${end}; apertura non indicata per questa data`
  return 'Orario del giorno non indicato'
}

/** Read time, editorial time and an edition's actual scope remain separate. */
export function editorialEvidenceView(market, now = new Date()) {
  const today = localDateISO(now)
  const proof = boundEvidence(market, today)
  if (!proof) return null
  const facts = proof.facts
  const exceptions = calendarExceptions(market)
  const fields = conflictFields(proof)
  const calendarConflict = [...fields].some(field => calendarFields.has(field))
  const historical = isPastEdition(facts, today)
  const notes = []
  if (historical) notes.push('La pagina descrive un’edizione passata. Le aperture attuali sono da verificare.')
  if (calendarConflict) notes.push('La fonte contiene indicazioni discordanti sul calendario. Le prossime aperture richiedono un riscontro.')
  else if (facts.calendar_complete !== true) notes.push('Il calendario nella pagina è incompleto; non permette di ricavare tutte le prossime aperture.')
  if (fields.has('hours')) notes.push('La fonte contiene orari discordanti, da verificare prima della visita.')
  if (fields.has('address')) notes.push('La fonte contiene indicazioni discordanti sull’indirizzo.')
  const factualNotes = ['conditions', 'hours_qualifications', 'scope_statements'].flatMap(key => list(facts[key]))
    .map(item => text(typeof item === 'string' ? item : item?.text)).filter(Boolean)
  notes.push(...factualNotes)
  const explicitDates = occurrences(facts)
  const singleDates = new Set(explicitDates.map(item => item.date))
  const rows = intervals(facts).filter(item => item.start !== item.end || !singleDates.has(item.start)).map(item => {
    const stopped = [...exceptions].filter(([day]) => item.start <= day && day <= item.end)
      .sort(([a], [b]) => a.localeCompare(b))
    const changes = stopped.map(([day, reason]) => `${dateLabel(day)}: Annullato${reason ? ' — ' + reason : ''}`)
    return {
      key: 'period/' + item.start + '/' + item.end, sortDate: item.start, kind: 'interval',
      label: item.start === item.end ? dateLabel(item.start) : `${dateLabel(item.start)} – ${dateLabel(item.end)}`,
      status: stopped.length ? item.start === item.end ? 'Annullato' : 'Variazioni nel periodo'
        : calendarConflict ? 'Periodo da verificare' : item.end < today ? 'Periodo passato' : 'Periodo riportato',
      hours: '', note: ['Il periodo non specifica le aperture dei singoli giorni.', ...changes].join(' '),
    }
  })
  for (const item of explicitDates) {
    const stopped = exceptions.has(item.date)
    rows.push({key: ['date', item.date, item.start_time, item.end_time, item.status].join('/'),
      sortDate: item.date, kind: 'date', label: dateLabel(item.date),
      status: stopped ? 'Annullato' : statusLabels[item.status] || (calendarConflict ? 'Data da verificare' : facts.archive_marker === true
        ? 'Data nella pagina archiviata' : item.date < today ? 'Data passata' : 'Data riportata'),
      hours: !stopped && !calendarConflict && !fields.has('hours') && facts.archive_marker !== true && ['source_listed', 'rescheduled'].includes(item.status)
        ? occurrenceHours(item) : '',
      note: [text(item.note), stopped ? exceptions.get(item.date) : ''].filter(Boolean).join(' · '),
    })
  }
  rows.sort((a, b) => a.sortDate.localeCompare(b.sortDate) || a.key.localeCompare(b.key))
  return {
    title: historical ? 'Edizione passata descritta dalla fonte' : 'Dettagli dell’edizione nella fonte',
    sourceName: proof.publisher === 'cosedicasa.com' ? 'Cose di Casa'
      : proof.publisher === 'eventiesagre.it' ? 'Eventi e Sagre' : `Citynews · ${proof.publisher}`,
    sourceUrl: proof.final_url, readOn: dateLabel(proof.read_on),
    editorialDate: proof.modified_on ? `Modifica dichiarata: ${dateLabel(proof.modified_on)}`
      : proof.published_on ? `Pubblicazione dichiarata: ${dateLabel(proof.published_on)}` : 'Data dei contenuti non dichiarata',
    historical, calendarConflict, notes: [...new Set(notes)], rows,
    hours: fields.has('hours') ? '' : text(facts.hours_text),
    hoursLabel: historical ? 'Orari riportati per l’edizione passata' : 'Orari riportati per questa edizione',
    recurrence: text(facts.recurrence_text),
  }
}

/** An archived edition cannot certify the older general catalog fields. */
export function editorialSummaryView(market, now = new Date()) {
  const evidence = editorialEvidenceView(market, now)
  const historical = evidence ? evidence.historical : market?.indexHoursScope === 'storico'
  return {
    evidence,
    hours: historical ? 'Orari attuali da verificare'
      : !evidence && !market?.sourceCalendar && market?.indexHoursScope === 'per_data'
        ? 'Vedi gli orari per data' : text(market?.hours),
    // The exact source recurrence, when available, remains in the edition
    // section. Do not repeat an older catalog rule under "Prossime date".
    recurrence: historical ? '' : text(market?.recurrence),
  }
}

/** General editorial hours never supply the missing hours of an explicit date. */
export function editorialHoursForDate(market, day, now = new Date()) {
  const proof = boundEvidence(market, localDateISO(now))
  if (!proof) return null
  if (!validDate(day)) return 'Orario per questa data da verificare'
  if (calendarExceptions(market).has(day)) return 'Annullato'
  const fields = conflictFields(proof)
  if ([...fields].some(field => calendarFields.has(field)) || fields.has('hours') || proof.facts.archive_marker === true) {
    return 'Orario per questa data da verificare'
  }
  const matches = occurrences(proof.facts).filter(item => item.date === day)
  if (!matches.length) return 'Orario per questa data non indicato'
  return [...new Set(matches.map(item => statusLabels[item.status] && item.status !== 'rescheduled'
    ? statusLabels[item.status] : occurrenceHours(item)))].join(' · ')
}
