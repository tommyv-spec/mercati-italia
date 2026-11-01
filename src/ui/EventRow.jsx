import Icon from './Icon.jsx'
import { CategoryTile, categoryColor } from './CategoryIcon.jsx'
import { displayName, displayAddress, isFreeEntry, todayStr, localISO } from '../lib/display.js'
import { sourceHoursForDate } from '../lib/sourceCalendar.js'

const tomorrowStr = (() => { const d = new Date(); d.setDate(d.getDate() + 1); return localISO(d) })()
const dayLabel = iso => {
  const d = new Date(iso + 'T12:00:00')
  return d.toLocaleDateString('it-IT', { weekday: 'short' }).replace('.', '') + ' ' + d.getDate() + ' ' +
    d.toLocaleDateString('it-IT', { month: 'short' }).replace('.', '')
}
// A clock time fits the "when" line; a weekly timetable belongs on the market page.
const shortHours = text => (text && text.length <= 13 && /\d/.test(text) ? text : '')

// One market in a list: category tile, when (and how sure), short title, place,
// two lines of description, a Gratis mark. Class names .market-card / .card-name /
// .card-city / .card-distance / .market-card-open are the nightly UI tests' contract.
export default function EventRow({ market, date = null, twoDays = false, onOpen, onToggleFav, isFav, hot = true, showDate = true }) {
  const title = displayName(market)
  const address = displayAddress(market)
  const hours = shortHours(date ? sourceHoursForDate(market, date) : market.hours)
  const sure = market.dateQuality === 'confermata' || market.dateQuality === 'riportata'
  const hotLabel = hot && date === todayStr ? 'Oggi' : hot && date === tomorrowStr ? 'Domani' : ''
  const km = Number.isFinite(market.distance) && market.distance >= 0.5 ? Math.round(market.distance) : null
  const free = isFreeEntry(market.entry)
  // Under a day heading the date is already said: only the hours, when a clock time is known.
  const when = [
    showDate || !date ? (date ? (twoDays ? dayLabel(date) + ' e dom' : dayLabel(date)) : 'Data da verificare')
      : (twoDays ? 'Sabato e domenica' : ''),
    hours,
  ].filter(Boolean).join(' · ')
  const tag = market.tags.find(t => t.toLowerCase() !== market.category.toLowerCase() && t.length < 18)
  return (
    <article className="market-card event-row" style={{ '--c': categoryColor(market.category) }}>
      <CategoryTile category={market.category} />
      <div className="body">
        <div className="top">
          <span className="when">
            {hotLabel && <b className="hot">{hotLabel}{when ? ' · ' : ''}</b>}
            {when}
            {date && (sure
              ? <span className={'sure' + (when || hotLabel ? '' : ' lead')}><Icon name="check" size={13} strokeWidth={2.6} />confermata</span>
              : <span className={'unsure' + (when || hotLabel ? '' : ' lead')}>prevista</span>)}
          </span>
          <button type="button" className={'row-fav' + (isFav ? ' on' : '')}
            aria-label={isFav ? 'Togli dall’agenda' : 'Salva in agenda'} onClick={() => onToggleFav(market.id)}>
            <Icon name="bookmark" size={18} strokeWidth={isFav ? 2.4 : 1.8} />
          </button>
        </div>
        <button type="button" className="market-card-open" onClick={() => onOpen(market)}>
          <h3 className="card-name">{title}</h3>
        </button>
        <p className="place">
          <Icon name="mapPin" size={13} strokeWidth={2} />
          <span><span className="card-city">{market.city}</span>{address ? ' · ' + address : ''}
            {km !== null && <span className="card-distance"> · circa {km} km{market.positionQuality !== 'precisa' ? ' (stimati)' : ''}</span>}
          </span>
        </p>
        {market.description && <p className="desc">{market.description}</p>}
        {(free || tag) && (
          <div className="foot">
            {free && <span className="pill-free"><Icon name="ticket" size={13} strokeWidth={2} />Gratis</span>}
            {tag && <span className="tag">{tag}</span>}
          </div>
        )}
      </div>
    </article>
  )
}
