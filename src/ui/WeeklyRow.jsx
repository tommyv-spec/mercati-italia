import { displayName } from '../lib/display.js'

// One weekly municipal market as a dense row: name on the left, hours on the right.
export default function WeeklyRow({ market, onOpen, sub = '' }) {
  return (
    <button type="button" className="weekly-row" onClick={() => onOpen(market)}>
      <span className="name">{displayName(market)}{sub && <span className="sub">{sub}</span>}</span>
      <span className="hours">{market.hours}</span>
    </button>
  )
}
