import Icon from './Icon.jsx'
import { getDateBadge, dateQualityLabel } from '../lib/display.js'

// One market in a magazine list: eyebrow (when · where), name, facts line, two-line
// description, quiet quality line. Class names .market-card / .card-name / .card-city /
// .card-distance / .market-card-open are the DOM contract of the nightly UI tests.
export default function EventRow({ market, when, onOpen, onToggleFav, isFav, showBadge = true }) {
  const badge = showBadge ? getDateBadge(market.dates) : null
  const confirmed = market.dateQuality === 'confermata' || market.dateQuality === 'riportata'
  const facts = [market.address, market.hours].filter(Boolean).join(' · ')
  const km = Number.isFinite(market.distance) && market.distance >= 0.5 ? Math.round(market.distance) : null
  return (
    <article className="market-card event-row">
      <div className="top">
        <span className="eyebrow">
          {badge && badge.tone === 'today' && <span className="eyebrow-hot">{badge.label} · </span>}
          {when ? when + ' · ' : ''}
          <span className="card-city">{market.city}</span>{market.region ? ' · ' + market.region : ''}
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
        {market.tags.slice(0, 2).map(t => <span key={t} className="tag">{t}</span>)}
      </div>
    </article>
  )
}
