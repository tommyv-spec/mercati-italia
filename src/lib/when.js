import { localISO } from './display.js'
import { weekendOf } from './weekend.js'
import { weekdayFromISO } from './marketGrouping.js'

// "Quando": one choice for the whole app. kind = oggi | domani | weekend (offset) |
// 7giorni | weekday (0 = lunedì) | tutte.
export const DEFAULT_WHEN = { kind: 'weekend', offset: 0 }
export const WEEKDAY_NAMES = ['lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato', 'domenica']

const addDays = (iso, n) => { const d = new Date(iso + 'T12:00:00'); d.setDate(d.getDate() + n); return localISO(d) }

// The days the choice covers, oldest first; null means no limit (all dates, undated too).
export function whenDays(when, today) {
  switch (when?.kind) {
    case 'oggi': return [today]
    case 'domani': return [addDays(today, 1)]
    case 'weekend': {
      const w = weekendOf(new Date(today + 'T12:00:00'), when.offset || 0)
      return [w.sat, w.sun].filter(day => day >= today)
    }
    case '7giorni': return Array.from({ length: 8 }, (_, i) => addDays(today, i))
    case 'weekday': return Array.from({ length: 7 }, (_, i) => addDays(today, i)).filter(day => weekdayFromISO(day) === when.weekday)
    default: return null
  }
}

// The first date of a market inside the chosen days (any future date when there is no limit).
export function firstDayIn(dates = [], days, today) {
  const sorted = [...dates].sort()
  if (!days) return sorted.find(day => day >= today) || null
  const wanted = new Set(days)
  return sorted.find(day => wanted.has(day)) || null
}

export function whenLabel(when) {
  switch (when?.kind) {
    case 'oggi': return 'Oggi'
    case 'domani': return 'Domani'
    case 'weekend': return (when.offset || 0) === 0 ? 'Questo weekend' : (when.offset === 1 ? 'Prossimo weekend' : 'Tra ' + when.offset + ' weekend')
    case '7giorni': return 'Prossimi 7 giorni'
    case 'weekday': { const name = WEEKDAY_NAMES[when.weekday] || ''; return name.charAt(0).toUpperCase() + name.slice(1) }
    default: return 'Tutte le date'
  }
}
