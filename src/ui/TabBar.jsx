import Icon from './Icon.jsx'

const TABS = [
  ['esplora', 'Esplora', 'compass'],
  ['mappa', 'Mappa', 'mapOutline'],
  ['agenda', 'Agenda', 'calendar'],
  ['altro', 'Altro', 'dots'],
]

export default function TabBar({ tab, onTab }) {
  return (
    <nav className="bottom-tabs" aria-label="Sezioni">
      {TABS.map(([id, label, icon]) => (
        <button key={id} type="button" className={'tab-btn' + (tab === id ? ' active' : '')} aria-current={tab === id ? 'page' : undefined}
          onClick={() => onTab(id)}>
          <Icon name={icon} size={22} strokeWidth={tab === id ? 2 : 1.6} />
          {label}
        </button>
      ))}
    </nav>
  )
}
