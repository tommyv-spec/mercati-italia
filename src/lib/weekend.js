import { localISO } from './display.js'

const longDay = date => date.toLocaleDateString('it-IT', { weekday: 'long' })
const dayMonth = date => date.getDate() + ' ' + date.toLocaleDateString('it-IT', { month: 'long' })

// Saturday+Sunday that contains `now` when it is Sat/Sun, else the coming one; `offset` weekends later.
export function weekendOf(now = new Date(), offset = 0) {
  const base = new Date(now); base.setHours(12, 0, 0, 0)
  const day = base.getDay()
  const sat = new Date(base)
  sat.setDate(base.getDate() + (day === 0 ? -1 : 6 - day) + offset * 7)
  const sun = new Date(sat); sun.setDate(sat.getDate() + 1)
  const label = offset === 0 ? 'Questo weekend' : offset === 1 ? 'Prossimo weekend' : 'Weekend del ' + dayMonth(sat)
  return {
    sat: localISO(sat), sun: localISO(sun), label,
    sub: longDay(sat) + ' ' + dayMonth(sat) + ' · ' + longDay(sun) + ' ' + dayMonth(sun),
  }
}

export function inWeekend(dates = [], weekend) {
  return dates.includes(weekend.sat) || dates.includes(weekend.sun)
}
