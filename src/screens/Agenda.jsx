import { useMemo } from 'react'
import EventRow from '../ui/EventRow.jsx'
import Section from '../ui/Section.jsx'
import { TODAY, todayStr, getNextDate, localISO } from '../lib/display.js'
import { weekendOf, inWeekend } from '../lib/weekend.js'
import { downloadCalendarEvent } from '../lib/calendarFile.js'
import { sourceHoursForDate } from '../lib/sourceCalendar.js'

const shortDay = iso => {
  const d = new Date(iso + 'T12:00:00')
  return d.toLocaleDateString('it-IT', { weekday: 'short' }) + ' ' + d.getDate() + ' ' + d.toLocaleDateString('it-IT', { month: 'short' })
}

// Saved markets by when they open next; the weekend's events as suggestions when empty.
export default function Agenda({ markets, favorites, onOpen, onToggleFav, onExplore }) {
  const weekend = useMemo(() => weekendOf(TODAY, 0), [])
  const saved = useMemo(() => markets.filter(m => favorites.has(m.id))
    .map(m => ({ market: m, next: getNextDate(m.dates) }))
    .sort((a, b) => (a.next || '9999').localeCompare(b.next || '9999')), [markets, favorites])
  const groups = useMemo(() => {
    const out = { oggi: [], weekend: [], prossimi: [], senza: [] }
    for (const item of saved) {
      if (!item.next) out.senza.push(item)
      else if (item.next === todayStr) out.oggi.push(item)
      else if (inWeekend([item.next], weekend)) out.weekend.push(item)
      else out.prossimi.push(item)
    }
    return out
  }, [saved, weekend])
  const suggestions = useMemo(() => markets
    .filter(m => m.isEvent && !m.concluded && inWeekend(m.dates, weekend) && !favorites.has(m.id))
    .sort((a, b) => (b.description ? 1 : 0) - (a.description ? 1 : 0) || a.name.localeCompare(b.name, 'it'))
    .slice(0, 3), [markets, weekend, favorites])

  const row = ({ market, next }) => (
    <div key={market.id} className="agenda-item">
      <EventRow market={market} date={next} onOpen={onOpen} onToggleFav={onToggleFav} isFav />
      {next && (
        <button type="button" className="link agenda-cal" onClick={() => downloadCalendarEvent(market, next, sourceHoursForDate(market, next))}>
          Aggiungi al calendario
        </button>
      )}
    </div>
  )
  const block = (title, items) => items.length > 0 && <Section title={title}>{items.map(row)}</Section>

  return (
    <div className="agenda-screen">
      <div className="screen-head">
        <h1>Agenda</h1>
        <p className="note">I mercati che hai salvato, dal più vicino nel tempo. Le notifiche push automatiche non sono ancora attive. Controlla sempre se la data è confermata prima di partire.</p>
      </div>
      {saved.length === 0 ? (
        <>
          <div className="empty">
            Nessun mercato salvato.<br />Salva un mercato dalla ricerca per vederlo qui.<br />
            <button type="button" className="btn-secondary" onClick={onExplore}>Cerca mercati</button>
          </div>
          {suggestions.length > 0 && (
            <Section title="Da salvare questo weekend">
              {suggestions.map(m => <EventRow key={m.id} market={m} date={m.dates.includes(weekend.sat) ? weekend.sat : weekend.sun} onOpen={onOpen} onToggleFav={onToggleFav} isFav={false} />)}
            </Section>
          )}
        </>
      ) : (
        <>
          {block('Oggi', groups.oggi)}
          {block(weekend.label, groups.weekend)}
          {block('Prossimi', groups.prossimi)}
          {block('Senza una data prossima', groups.senza)}
          {groups.senza.length > 0 && <p className="note" style={{ padding: '8px 20px 0' }}>Per questi mercati la fonte non indica una data futura: verifica la fonte ufficiale.</p>}
        </>
      )}
    </div>
  )
}
