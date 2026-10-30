import Icon from './Icon.jsx'

export const MAX_WEEKEND_OFFSET = 8

export default function WeekendStepper({ weekend, offset, onChange }) {
  return (
    <div className="stepper">
      <button type="button" aria-label="Weekend precedente" disabled={offset <= 0} onClick={() => onChange(offset - 1)}>
        <Icon name="chevronLeft" size={18} strokeWidth={2} />
      </button>
      <div>
        <div className="label">{weekend.label}</div>
        <span className="sub">{weekend.sub}</span>
      </div>
      <button type="button" aria-label="Weekend successivo" disabled={offset >= MAX_WEEKEND_OFFSET} onClick={() => onChange(offset + 1)}>
        <Icon name="chevronRight" size={18} strokeWidth={2} />
      </button>
    </div>
  )
}
