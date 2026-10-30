import Icon from './Icon.jsx'

// Bottom sheet with every filter: categories, region, city, radius. Pending values
// live in the App shell; Applica copies them into the active filters.
export default function FilterSheet({
  onClose, cats, catColors, pendingCats, setPendingCats, regions, pendingRegion, setPendingRegion,
  cities, pendingCity, setPendingCity, pendingDist, setPendingDist, canUseDistance, onReset, onApply,
}) {
  return (
    <>
      <div className="sheet-backdrop" onClick={onClose} />
      <div className="sheet" role="dialog" aria-label="Filtri">
        <div className="sheet-head">
          <h2>Filtri</h2>
          <button type="button" className="ico-btn" aria-label="Chiudi" onClick={onClose}><Icon name="x" size={18} /></button>
        </div>
        <div>
          <span className="eyebrow">Categoria</span>
          <div className="sheet-cats">
            {cats.map(cat => {
              const active = pendingCats.includes(cat)
              const color = catColors[cat]
              return (
                <button key={cat} type="button" aria-pressed={active}
                  className={'pill' + (active ? ' active' : '')}
                  style={active ? { background: color, borderColor: color } : undefined}
                  onClick={() => setPendingCats(prev => prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat])}>
                  {cat}
                </button>
              )
            })}
          </div>
        </div>
        <label>
          <span className="eyebrow">Regione</span>
          <select value={pendingRegion} onChange={e => { setPendingRegion(e.target.value); setPendingCity('') }}>
            <option value="">Tutte le regioni</option>
            {regions.map(r => <option key={r} value={r}>{r}</option>)}
          </select>
        </label>
        <label>
          <span className="eyebrow">Città</span>
          <select value={pendingCity} onChange={e => setPendingCity(e.target.value)}>
            <option value="">Tutte le città</option>
            {cities.map(c => <option key={c} value={c}>{c}</option>)}
          </select>
        </label>
        <div>
          <span className="eyebrow">Distanza massima</span>
          <div className="sheet-range"><span>5 km</span><span>{pendingDist} km</span></div>
          <input type="range" min={5} max={100} step={5} value={pendingDist} disabled={!canUseDistance}
            aria-label="Distanza massima in chilometri" onChange={e => setPendingDist(Number(e.target.value))} />
          {!canUseDistance && <p className="note">Per usare il raggio, attiva la posizione in Impostazioni.</p>}
        </div>
        <div className="sheet-foot">
          <button type="button" className="btn-secondary" onClick={onReset}>Reimposta filtri</button>
          <button type="button" className="btn-primary" onClick={onApply}>Applica filtri</button>
        </div>
      </div>
    </>
  )
}
