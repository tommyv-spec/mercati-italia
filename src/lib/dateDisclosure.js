/**
 * Conservative disclosure for date forecasts in market details and groups.
 *
 * A planned or confirmed label without ANY upcoming source-bound date is
 * misleading. This function is pure, timezone-local and date-only.
 */
export function localDateISO(now = new Date()) {
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return [year, month, day].join('-')
}

export function hasUpcomingDate(dates, now = new Date()) {
  const today = localDateISO(now)
  return Array.isArray(dates) && dates.some(value =>
    typeof value === 'string' &&
    /^\d{4}-\d{2}-\d{2}$/.test(value) &&
    value >= today
  )
}

export function marketDateDisclosure(dates, quality, now = new Date()) {
  if (!hasUpcomingDate(dates, now)) {
    return 'Nessuna data futura disponibile. Giorni e aperture da verificare presso la fonte prima di partire.'
  }
  if (quality === 'confermata') return ''
  return 'Date previste, non confermate per ogni singola edizione. Controlla la fonte prima di partire.'
}
