import { useMemo } from 'react'
import Icon from '../ui/Icon.jsx'
import WeeklyRow from '../ui/WeeklyRow.jsx'
import { weekdayFromISO, italianKey } from '../lib/marketGrouping.js'
import { getNextDate, todayStr } from '../lib/display.js'

const DAYS = ['Lunedì', 'Martedì', 'Mercoledì', 'Giovedì', 'Venerdì', 'Sabato', 'Domenica']

// Every weekly municipal market of one town, grouped by weekday, today first.
export default function Weekly({ city, markets, onOpen, onBack }) {
  const groups = useMemo(() => {
    const key = italianKey(city)
    const rows = markets.filter(m => !m.isEvent && !m.concluded && italianKey(m.city) === key)
    const byDay = new Map()
    for (const m of rows) {
      const next = getNextDate(m.dates)
      const idx = next ? weekdayFromISO(next) : 'nd'
      if (!byDay.has(idx)) byDay.set(idx, [])
      byDay.get(idx).push(m)
    }
    const todayIdx = weekdayFromISO(todayStr)
    const order = [...Array(7).keys()].map(i => (todayIdx + i) % 7).filter(i => byDay.has(i))
    const result = order.map(i => ({ key: i, label: DAYS[i], today: i === todayIdx, rows: byDay.get(i) }))
    if (byDay.has('nd')) result.push({ key: 'nd', label: 'Giorno da verificare', today: false, rows: byDay.get('nd') })
    for (const g of result) g.rows.sort((a, b) => a.name.localeCompare(b.name, 'it'))
    return result
  }, [city, markets])
  const total = groups.reduce((n, g) => n + g.rows.length, 0)

  return (
    <div className="weekly-screen">
      <button type="button" className="back-home" onClick={onBack}><Icon name="chevronLeft" size={16} strokeWidth={2.2} /> Home</button>
      <h1>Mercati settimanali a {city}</h1>
      <p className="note" style={{ marginTop: 0 }}>{total} mercati comunali · tocca un mercato per orari e indirizzo</p>
      {groups.length === 0 && <div className="empty">Nessun mercato settimanale in catalogo per {city}.</div>}
      {groups.map(g => (
        <section key={g.key}>
          <h2>{g.today && <span className="eyebrow-hot">Oggi · </span>}{g.label}</h2>
          {g.rows.map(m => <WeeklyRow key={m.id} market={m} onOpen={onOpen} sub={m.address} />)}
        </section>
      ))}
    </div>
  )
}
