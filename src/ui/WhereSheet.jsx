import Sheet from './Sheet.jsx'
import Icon from './Icon.jsx'

// Dove: near me (GPS), a town, or the whole of Italy.
export default function WhereSheet({ where, cities, manualCity, setManualCity, onGps, onCity, onItaly, onClose, positionStatus, positionError }) {
  return (
    <Sheet title="Dove cerchi?" onClose={onClose}>
      <button type="button" className={'opt' + (where.mode === 'gps' ? ' on' : '')} onClick={onGps} disabled={positionStatus === 'requesting'}>
        <span className="opt-ico"><Icon name="navigation" size={18} strokeWidth={2} /></span>
        <span><strong>{positionStatus === 'requesting' ? 'Cerco la posizione…' : 'Usa la mia posizione'}</strong>
          <span className="opt-sub">Mercatini entro 50 km da te. Il telefono ti chiede il permesso.</span></span>
      </button>
      {positionError && <p role="alert" className="note">{positionError}</p>}
      <div className={'opt opt-city' + (where.mode === 'city' ? ' on' : '')}>
        <span className="opt-ico"><Icon name="mapPin" size={18} strokeWidth={2} /></span>
        <span style={{ flex: 1, minWidth: 0 }}>
          <strong>Una città</strong>
          <span className="opt-sub">Mercatini entro 50 km e i mercati settimanali della città.</span>
          <span className="manual-city-input">
            <input list="available-market-cities" placeholder="Scrivi una città" value={manualCity} aria-label="Città"
              onChange={e => setManualCity(e.target.value)} onKeyDown={e => { if (e.key === 'Enter') onCity() }} />
            <datalist id="available-market-cities">{cities.map(city => <option key={city} value={city} />)}</datalist>
            <button type="button" className="btn-primary" onClick={onCity}>Mostra</button>
          </span>
        </span>
      </div>
      <button type="button" className={'opt' + (where.mode === 'italia' ? ' on' : '')} onClick={onItaly}>
        <span className="opt-ico"><Icon name="compass" size={18} strokeWidth={2} /></span>
        <span><strong>Tutta Italia</strong><span className="opt-sub">Tutti i mercatini, divisi per regione.</span></span>
      </button>
    </Sheet>
  )
}
