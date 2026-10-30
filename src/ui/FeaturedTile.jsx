import { CATEGORY_COLORS } from '../lib/display.js'

const DAY = iso => new Date(iso + 'T12:00:00').toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' }).replace(/\./g, '')

// A poster-like tile in the category colour: date · city, name, place, free entry.
export default function FeaturedTile({ market, date, onOpen }) {
  const color = CATEGORY_COLORS[market.category] || '#6C6255'
  return (
    <button type="button" className="feat" style={{ background: color }} onClick={() => onOpen(market)}>
      <span className="feat-num" aria-hidden="true">{date ? Number(date.slice(8, 10)) : ''}</span>
      <span className="feat-eyebrow">{date ? DAY(date) + ' · ' : ''}{market.city}</span>
      <span className="feat-title">{market.name}</span>
      <span className="feat-sub">{market.address || market.region}</span>
      <span className="feat-foot">
        <span className="feat-cat">{market.category}</span>
        {market.entry && /gratuit|libero/i.test(market.entry) && <span className="feat-pill">Ingresso gratuito</span>}
      </span>
    </button>
  )
}
