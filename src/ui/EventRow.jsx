import Icon from './Icon.jsx'
import { CATEGORY_COLORS, dateQualityLabel, todayStr, localISO } from '../lib/display.js'

const MONTH = iso => new Date(iso + 'T12:00:00').toLocaleDateString('it-IT', { month: 'short' }).replace('.', '')
const WEEKDAY = iso => new Date(iso + 'T12:00:00').toLocaleDateString('it-IT', { weekday: 'short' }).replace('.', '')
const tomorrowStr = (() => { const d = new Date(); d.setDate(d.getDate() + 1); return localISO(d) })()

// One market in a magazine list: a date leaf on the left, then category · place,
// name, facts line, two-line description, quiet quality line. Class names
// .market-card / .card-name / .card-city / .card-distance / .market-card-open are
// the DOM contract of the nightly UI tests.
export default function EventRow({ market, date = null, twoDays = false, onOpen, onToggleFav, isFav, hot = true }) {
  const color = CATEGORY_COLORS[market.category] || '#6C6255'
  const confirmed = market.dateQuality === 'confermata' || market.dateQuality === 'riportata'
  const facts = [market.address, market.hours].filter(Boolean).join(' · ')
  const km = Number.isFinite(market.distance) && market.distance >= 0.5 ? Math.round(market.distance) : null
  const hotLabel = hot && date === todayStr ? 'Oggi' : hot && date === tomorrowStr ? 'Domani' : ''
  return (
    <article className="market-card event-row">
      <div className={'leaf' + (date ? '' : ' leaf-empty')} aria-hidden="true">
        {date ? <>
          <span className="leaf-day">{Number(date.slice(8, 10))}</span>
          <span className="leaf-mon">{twoDays ? WEEKDAY(date) + '·' + WEEKDAY(nextDay(date)) : WEEKDAY(date) + ' ' + MONTH(date)}</span>
        </> : <Icon name="calendar" size={18} />}
      </div>
      <div className="body">
        <div className="top">
          <span className="eyebrow">
            {hotLabel && <span className="eyebrow-hot">{hotLabel} · </span>}
            <span className="cat" style={{ color }}><span className="dot" style={{ background: color }} />{market.category}</span>
            {' · '}<span className="card-city">{market.city}</span>{market.region ? ' · ' + market.region : ''}
          </span>
          <button type="button" className={'row-fav' + (isFav ? ' on' : '')}
            aria-label={isFav ? 'Togli dall’agenda' : 'Salva in agenda'} onClick={() => onToggleFav(market.id)}>
            <Icon name="bookmark" size={18} strokeWidth={isFav ? 2.4 : 1.8} />
          </button>
        </div>
        <button type="button" className="market-card-open" onClick={() => onOpen(market)}>
          <h3 className="card-name">{market.name}</h3>
        </button>
        {(facts || market.entry || km !== null) && (
          <p className="meta">
            {facts}
            {market.entry && <>{facts ? ' · ' : ''}<span className="free">{market.entry}</span></>}
            {km !== null && <span className="card-distance">{facts || market.entry ? ' · ' : ''}circa {km} km{market.positionQuality !== 'precisa' ? ' (stimati)' : ''}</span>}
          </p>
        )}
        {market.description && <p className="desc">{market.description}</p>}
        <div className="foot">
          {confirmed
            ? <span className="ok"><Icon name="check" size={14} strokeWidth={2.5} />Data confermata dalla fonte</span>
            : <span>{market.dates.length ? dateQualityLabel(market.dateQuality) : 'Data da verificare'}</span>}
          {market.tags.filter(t => t.toLowerCase() !== market.category.toLowerCase()).slice(0, 1).map(t => <span key={t} className="tag">{t}</span>)}
        </div>
      </div>
    </article>
  )
}

function nextDay(iso) { const d = new Date(iso + 'T12:00:00'); d.setDate(d.getDate() + 1); return localISO(d) }
