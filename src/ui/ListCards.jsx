import Icon from './Icon.jsx'
import MarketArt from './MarketArt.jsx'
import { categoryColor } from './CategoryIcon.jsx'
import { displayName, displayAddress, isFreeEntry } from '../lib/display.js'
import { sourceHoursForDate } from '../lib/sourceCalendar.js'

// Shared facts for the three list styles. Class names .market-card / .card-name /
// .card-city / .card-distance / .market-card-open / .when are the nightly UI tests' contract.
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
const When = ({ f, date, children }) => (
  <span className="when">
    {children}
    {!date ? 'Data da verificare' : f.sure
      ? <span className="sure"><Icon name="check" size={12} strokeWidth={2.8} />confermata</span>
      : <span className="unsure">prevista</span>}
  </span>
)
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
export function TicketCard({ market, date, km, onOpen, onToggleFav, isFav }) {
  const f = facts(market, date, km)
  return (
    <article className="market-card ticket" style={{ '--c': f.color }}>
      <div className="ticket-stub" aria-hidden="true">
        <MarketArt market={market} size={34} strokeWidth={1.6} />
        {f.start ? <><span className="ticket-time">{f.start}</span><span className="ticket-until">fino {f.end}</span></>
          : <span className="ticket-until">{SHORT_CATEGORY[market.category] || 'Mercato'}</span>}
      </div>
      <div className="ticket-body">
        <div className="top">
          <When f={f} date={date}><span className="ticket-cat">{market.category}</span></When>
          <Fav market={market} isFav={isFav} onToggleFav={onToggleFav} />
        </div>
        <Open market={market} title={f.title} onOpen={onOpen} />
        <Place market={market} f={f} />
        {market.description && <p className="desc">{market.description}</p>}
        {f.free && <div className="foot"><span className="pill-free"><Icon name="ticket" size={13} strokeWidth={2} />Gratis</span></div>}
      </div>
    </article>
  )
}

// A small poster: coloured header with the drawing, category and hours; details below.
export function PosterCard({ market, date, km, onOpen, onToggleFav, isFav }) {
  const f = facts(market, date, km)
  const pattern = 'pc-p' + (market.id.length % 3)
  return (
    <article className={'market-card poster-card ' + pattern} style={{ '--c': f.color }}>
      <div className="pc-head">
        <span className="pc-eyebrow">{market.category}{f.hours ? ' · ' + f.hours : ''}</span>
        <span className="pc-art" aria-hidden="true"><MarketArt market={market} size={84} strokeWidth={1.15} /></span>
        <Fav market={market} isFav={isFav} onToggleFav={onToggleFav} className="pc-fav" />
      </div>
      <div className="pc-body">
        <When f={f} date={date} />
        <Open market={market} title={f.title} onOpen={onOpen} />
        <Place market={market} f={f} />
        {market.description && <p className="desc">{market.description}</p>}
        {f.free && <div className="foot"><span className="pill-free"><Icon name="ticket" size={13} strokeWidth={2} />Gratis</span></div>}
      </div>
    </article>
  )
}

// A grid tile: picture on top (drawing, time), short title, town.
export function GridTile({ market, date, km, onOpen, onToggleFav, isFav }) {
  const f = facts(market, date, km)
  return (
    <article className="market-card grid-tile" style={{ '--c': f.color }}>
      <div className="gt-visual" aria-hidden="true">
        <MarketArt market={market} size={58} strokeWidth={1.35} />
        {f.start && <span className="gt-time">{f.hours}</span>}
      </div>
      <Fav market={market} isFav={isFav} onToggleFav={onToggleFav} className="gt-fav" />
      <div className="gt-body">
        <When f={f} date={date} />
        <Open market={market} title={f.title} onOpen={onOpen} />
        <Place market={market} f={{ ...f, address: '' }} className="place gt-place" />
        {f.free && <span className="pill-free"><Icon name="ticket" size={12} strokeWidth={2} />Gratis</span>}
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
