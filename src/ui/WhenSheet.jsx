import Sheet from './Sheet.jsx'
import { whenLabel, WEEKDAY_NAMES } from '../lib/when.js'
import { weekendOf } from '../lib/weekend.js'
import { TODAY } from '../lib/display.js'

const SHORT = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']
const same = (a, b) => a.kind === b.kind && (a.offset || 0) === (b.offset || 0) && (a.weekday ?? null) === (b.weekday ?? null)

// Quando: one choice that Esplora and Mappa both follow.
export default function WhenSheet({ when, onPick, onClose }) {
  const options = [
    { kind: 'oggi' }, { kind: 'domani' },
    { kind: 'weekend', offset: 0, sub: weekendOf(TODAY, 0).sub },
    { kind: 'weekend', offset: 1, sub: weekendOf(TODAY, 1).sub },
    { kind: '7giorni' }, { kind: 'tutte', sub: 'Anche i mercatini senza una data prossima' },
  ]
  return (
    <Sheet title="Quando?" onClose={onClose}>
      <div className="when-grid">
        {options.map(o => (
          <button key={o.kind + (o.offset || '')} type="button" aria-pressed={same(o, when)}
            className={'opt opt-when' + (same(o, when) ? ' on' : '')} onClick={() => onPick({ kind: o.kind, offset: o.offset })}>
            <strong>{whenLabel(o)}</strong>{o.sub && <span className="opt-sub">{o.sub}</span>}
          </button>
        ))}
      </div>
      <div>
        <span className="eyebrow">Un giorno della settimana</span>
        <div className="weekday-row" aria-label="Scegli un giorno della settimana">
          {SHORT.map((day, i) => (
            <button key={day} type="button" aria-pressed={when.kind === 'weekday' && when.weekday === i}
              aria-label={'Mostra mercati del ' + WEEKDAY_NAMES[i]}
              className={'pill' + (when.kind === 'weekday' && when.weekday === i ? ' active' : '')}
              onClick={() => onPick({ kind: 'weekday', weekday: i })}>{day}</button>
          ))}
        </div>
      </div>
    </Sheet>
  )
}
