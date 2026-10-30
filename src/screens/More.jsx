import Icon from '../ui/Icon.jsx'

const REPORT_MAIL = 'mailto:fuori.mercatini.sagre@gmail.com?subject=' + encodeURIComponent('Segnalazione Fuori Mercatini')

// Position choice (GPS, a city, none), what Fuori is, how to report, version.
export default function More({
  locationMode, positionStatus, positionError, canUseDistance, manualCity, setManualCity, cities,
  onUseGps, onChooseCity, onNoLocation, onConfirmCity,
}) {
  const option = (mode, icon, title, sub, onClick) => (
    <button type="button" className={'loc-option' + (locationMode === mode ? ' active' : '')} onClick={onClick}>
      <span className="ico-btn" aria-hidden="true"><Icon name={icon} size={18} /></span>
      <span><strong>{title}</strong><span className="sub">{sub}</span></span>
    </button>
  )
  return (
    <div className="more-screen">
      <div className="screen-head"><h1>Altro</h1></div>

      <div className="panel">
        <span className="eyebrow">Posizione</span>
        <p className="note">Scegli come trovare i mercati vicino a te.</p>
        <div className="loc-options">
          {option('auto', 'compass', 'Usa la mia posizione',
            positionStatus === 'ready' ? 'Posizione attiva' : positionStatus === 'requesting' ? 'Richiesta in corso…' : 'Richiede il tuo consenso', onUseGps)}
          {option('manual', 'mapPin', 'Scegli una città', 'Inserisci manualmente', onChooseCity)}
          {option('none', 'x', 'Non ora', 'Naviga senza posizione', onNoLocation)}
        </div>
        {positionError && <p role="alert" className="note">{positionError}</p>}
        {canUseDistance && <p className="note">Distanze calcolate rispetto alla tua posizione. Alcuni mercati hanno solo coordinate indicative.</p>}
        {locationMode === 'manual' && (
          <>
            <div className="manual-city-input">
              <input list="available-market-cities" placeholder="Es. Firenze" value={manualCity} aria-label="Città"
                onChange={e => setManualCity(e.target.value)}
                onKeyDown={e => { if (e.key === 'Enter') onConfirmCity() }} />
              <datalist id="available-market-cities">
                {cities.map(city => <option key={city} value={city} />)}
              </datalist>
              <button type="button" className="btn-primary" onClick={onConfirmCity}>Filtra città</button>
            </div>
            <p className="note">La città selezionata filtra i risultati. Non equivale alla posizione GPS.</p>
          </>
        )}
      </div>

      <div className="panel">
        <span className="eyebrow">Informazioni</span>
        <p>Fuori raccoglie mercatini, fiere ed eventi di antiquariato, vintage, usato, artigianato e cibo in tutta Italia, insieme ai mercati comunali settimanali.</p>
        <p>I dati vengono da fonti pubbliche: siti dei Comuni, portali di eventi e open data regionali. Ogni scheda dice da dove arriva e quando è stata letta. Le date previste vanno sempre controllate sulla fonte prima di partire.</p>
        <p>Il catalogo è statico e si legge gratis: nessun account, nessuna pubblicità, nessun tracciamento.</p>
      </div>

      <div className="panel">
        <span className="eyebrow">Segnalazioni</span>
        <p>Un mercato manca, è sbagliato o non esiste più? <a href={REPORT_MAIL}>Scrivici</a>: la mail parte già compilata.</p>
      </div>

      <p className="note version">Fuori · Mercatini d'Italia · Versione 2.0 · Catalogo statico</p>
    </div>
  )
}
