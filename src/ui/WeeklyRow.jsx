// One weekly municipal market as a dense row: name on the left, hours on the right.
export default function WeeklyRow({ market, onOpen, sub = '' }) {
  return (
    <button type="button" className="weekly-row market-card-open" onClick={() => onOpen(market)}>
      <span className="name">{market.name}{sub && <span className="sub">{sub}</span>}</span>
      <span className="hours">{market.hours}</span>
    </button>
  )
}
