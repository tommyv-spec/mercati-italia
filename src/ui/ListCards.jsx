import Icon from './Icon.jsx'
import MarketArt from './MarketArt.jsx'
import { categoryColor } from './CategoryIcon.jsx'
import { displayName, displayAddress, isFreeEntry, todayStr, localISO } from '../lib/display.js'
import { sourceHoursForDate } from '../lib/sourceCalendar.js'

// Shared facts for the three list styles. Class names .market-card / .card-name /
// .card-city / .card-distance / .market-card-open / .when are the nightly UI tests' contract.
const tomorrowStr = (() => { const d = new Date(); d.setDate(d.getDate() + 1); return localISO(d) })()
const dayLabel = iso => {
  const d = new Date(iso + 'T12:00:00')
  const label = d.toLocaleDateString('it-IT', { weekday: 'short' }).replace('.', '') + ' ' + d.getDate() + ' ' +
    d.toLocaleDateString('it-IT', { month: 'short' }).replace('.', '')
  return iso === todayStr ? 'Oggi · ' + label : iso === tomorrowStr ? 'Domani · ' + label : label
}
const SHORT_CATEGORY = { Antiquariato: 'Antico', 'Vintage e abbigliamento': 'Vintage', Usato: 'Usato', Artigianato: 'Artigiani', Alimentare: 'Cibo', Misto: 'Mercato' }
function facts(market, date, centreKm) {
  const raw = date ? sourceHoursForDate(market, date) : market.hours
  const clock = /^(\d{1,2})[:.](\d{2})\s*[–-]\s*(\d{1,2})[:.](\d{2})$/.exec((raw || '').trim())
  const gpsKm = Number.isFinite(market.distance) && market.distance >= 0.5 ? Math.round(market.distance) : null
  return {
    title: displayName(market),
    address: displayAddress(market),
    start: clock ? Number(clock[1]) + ':' + clock[2] : '',
    end: clock ? clock[3] + ':' + clock[4] : '',
    hours: clock ? Number(clock[1]) + ':' + clock[2] + '–' + clock[3] + ':' + clock[4] : '',
    sure: market.dateQuality === 'confermata' || market.dateQuality === 'riportata',
    free: isFreeEntry(market.entry),
    gpsKm,
    estimated: market.positionQuality !== 'precisa',
    centreKm: gpsKm === null && Number.isFinite(centreKm) && centreKm >= 1.5 ? Math.round(centreKm) : null,
    color: categoryColor(market.category),
  }
}
const Place = ({ market, f, className = 'place' }) => (
  <p className={className}>
    <Icon name="mapPin" size={13} strokeWidth={2} />
    <span><span className="card-city">{market.city}</span>{f.address ? ' · ' + f.address : ''}
      {f.gpsKm !== null && <span className="card-distance"> · circa {f.gpsKm} km{f.estimated ? ' (stimati)' : ''}</span>}
      {f.centreKm !== null && <span className="card-km"> · a {f.centreKm} km</span>}
    </span>
  </p>
)
const Fav = ({ market, isFav, onToggleFav, className = 'row-fav' }) => (
  <button type="button" className={className + (isFav ? ' on' : '')} aria-label={isFav ? 'Togli dai salvati' : 'Salva'}
    onClick={() => onToggleFav(market.id)}>
    <Icon name="bookmark" size={18} strokeWidth={isFav ? 2.4 : 1.8} />
  </button>
)
const Open = ({ market, title, onOpen }) => (
  <button type="button" className="market-card-open" onClick={() => onOpen(market)}><h3 className="card-name">{title}</h3></button>
)

// A ticket: coloured stub with the drawing and the opening time, perforated edge, details.
// Name first, then the place; the small line below says only what is not the norm.
export function TicketCard({ market, date, km, onOpen, onToggleFav, isFav, showDate = false }) {
  const f = facts(market, date, km)
  const status = !date ? 'Data da verificare' : f.sure ? '' : 'Data prevista'
  const shownDate = showDate && date
  return (
    <article className="market-card ticket" style={{ '--c': f.color }}>
      <div className="ticket-stub" aria-hidden="true">
        <MarketArt market={market} size={34} strokeWidth={1.6} />
        {f.start ? <><span className="ticket-time">{f.start}</span><span className="ticket-until">fino {f.end}</span></>
          : <span className="ticket-until">{SHORT_CATEGORY[market.category] || 'Mercato'}</span>}
      </div>
      <div className="ticket-body">
        <div className="top">
          <Open market={market} title={f.title} onOpen={onOpen} />
          <Fav market={market} isFav={isFav} onToggleFav={onToggleFav} />
        </div>
        <Place market={market} f={f} />
        {(shownDate || status || f.free) && (
          <p className="when">
            {shownDate && <span className="ticket-date">{dayLabel(date)}</span>}
            {status && <span className="unsure">{status}</span>}
            {f.free && <span className="free-tag"><Icon name="ticket" size={13} strokeWidth={2} />Gratis</span>}
          </p>
        )}
      </div>
    </article>
  )
}

// A calendar-like divider that opens each day.
export function DayDivider({ day, count, today, tomorrow }) {
  if (!day) return <h2 className="day-divider"><span className="dd-txt"><b>Senza una data prossima</b></span><span className="dd-n">{count}</span></h2>
  const d = new Date(day + 'T12:00:00')
  const weekday = d.toLocaleDateString('it-IT', { weekday: 'long' })
  const month = d.toLocaleDateString('it-IT', { month: 'long' })
  const hot = day === today ? 'Oggi' : day === tomorrow ? 'Domani' : ''
  return (
    <h2 className={'day-divider' + (hot ? ' hot' : '')}>
      <span className="dd-num">{d.getDate()}</span>
      <span className="dd-txt">{hot && <span className="dd-hot">{hot}</span>}<b>{weekday.charAt(0).toUpperCase() + weekday.slice(1)}</b> {month}</span>
      <span className="dd-n">{count} {count === 1 ? 'mercatino' : 'mercatini'}</span>
    </h2>
  )
}

// Tickets on the beige band, for lists without day headings (search, weekly markets, saved).
export function TicketList({ items, showDate = true, onOpen, onToggleFav, favorites, after }) {
  return (
    <div className="list-area">
      <div className="cards-col">
        {items.map(it => (
          <div key={it.market.id} className="ticket-wrap">
            <TicketCard market={it.market} date={it.day} km={it.km} showDate={showDate} onOpen={onOpen}
              onToggleFav={onToggleFav} isFav={favorites.has(it.market.id)} />
            {after && after(it)}
          </div>
        ))}
      </div>
    </div>
  )
}
