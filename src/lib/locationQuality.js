/**
 * Conservative screen of corrupt scraped city labels.
 *
 * Mirrors the read-only backend/catalog_quality_report.py classifier;
 * does NOT try to derive a municipality from an event title or URL.
 * Source data remains unchanged, and the user can still search by title.
 */
const SUSPICIOUS_TERMS = [
  ' in provincia', 'mercato settimanale a ', 'fiere, mostre e mercati',
  ' http://', ' https://', ' il mercato settimanale di ',
]
const PROVINCE_ABBREVIATIONS_MISTAKEN_FOR_CITIES =
  new Set(['AL','BS','MI','BG','BO','FI','RM','NA'])

export function isSuspiciousCityName(city) {
  const raw = String(city || '').trim()
  const folded = raw.toLocaleLowerCase('it')
  return raw.length > 68 ||
    raw.startsWith('"') || raw.startsWith('“') || raw.startsWith('”') ||
    PROVINCE_ABBREVIATIONS_MISTAKEN_FOR_CITIES.has(raw.toUpperCase()) ||
    SUSPICIOUS_TERMS.some(term => folded.includes(term)) ||
    (/^(via|viale|corso)\s/i.test(raw) && raw.includes('-'))
}

export function safeCityLabel(city) {
  return isSuspiciousCityName(city) ? 'Località da verificare' : String(city || '')
}

export const UNKNOWN_CITY_HELP =
  'La località riportata dalla fonte non identifica con sicurezza un Comune. Controlla la fonte originale prima di spostarti.'
