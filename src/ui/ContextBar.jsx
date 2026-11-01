import Icon from './Icon.jsx'

// "Dove" and "Quando", always in view: one tap opens the sheet to change each.
export default function ContextBar({ whereLabel, whenLabel, onWhere, onWhen, barRef }) {
  return (
    <div className="context-bar" ref={barRef}>
      <button type="button" className="ctx" onClick={onWhere}>
        <Icon name="mapPin" size={17} strokeWidth={2} />
        <span className="ctx-text"><span className="ctx-k">Dove</span><span className="ctx-v">{whereLabel}</span></span>
        <Icon name="chevronDown" size={16} strokeWidth={2.2} />
      </button>
      <button type="button" className="ctx" onClick={onWhen}>
        <Icon name="calendar" size={17} strokeWidth={2} />
        <span className="ctx-text"><span className="ctx-k">Quando</span><span className="ctx-v">{whenLabel}</span></span>
        <Icon name="chevronDown" size={16} strokeWidth={2.2} />
      </button>
    </div>
  )
}
