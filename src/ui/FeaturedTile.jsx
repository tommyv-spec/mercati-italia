import CategoryIcon, { categoryColor } from './CategoryIcon.jsx'
import Icon from './Icon.jsx'
import { displayName, displayAddress, isFreeEntry } from '../lib/display.js'

const DAY = iso => new Date(iso + 'T12:00:00').toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' }).replace(/\./g, '')

// A poster in the category colour: its drawing large in the corner, date · city, name, place.
export default function FeaturedTile({ market, date, onOpen }) {
  return (
    <button type="button" className="feat" style={{ background: categoryColor(market.category) }} onClick={() => onOpen(market)}>
      <span className="feat-art" aria-hidden="true"><CategoryIcon category={market.category} size={150} strokeWidth={1.1} /></span>
      <span className="feat-eyebrow">{date ? DAY(date) + ' · ' : ''}{market.city}</span>
      <span className="feat-title">{displayName(market)}</span>
      <span className="feat-sub">{displayAddress(market) || market.region}</span>
      <span className="feat-foot">
        <span className="feat-cat">{market.category}</span>
        {isFreeEntry(market.entry) && <span className="feat-pill"><Icon name="ticket" size={12} strokeWidth={2} /> Gratis</span>}
      </span>
    </button>
  )
}
