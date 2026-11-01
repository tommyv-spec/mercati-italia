const REPORT_MAIL = 'mailto:fuori.mercatini.sagre@gmail.com?subject=' + encodeURIComponent('Segnalazione Fuori Mercatini')

// What Fuori is, how to report a mistake, version. Dove and Quando live on Esplora.
export default function More() {
  return (
    <div className="more-screen">
      <div className="screen-head"><h1>Altro</h1></div>

      <div className="panel">
        <span className="eyebrow">Che cos'è Fuori</span>
        <p>Fuori raccoglie mercatini, fiere ed eventi di antiquariato, vintage, usato, artigianato e cibo in tutta Italia, insieme ai mercati comunali di ogni settimana.</p>
        <p>I dati vengono da fonti pubbliche: siti dei Comuni, portali di eventi e open data regionali. Ogni scheda dice da dove arriva e quando è stata letta. Le date «previste» vanno controllate sulla fonte prima di partire.</p>
        <p>Si usa gratis: nessun account, nessuna pubblicità. La posizione serve solo a ordinare i mercatini vicini e resta nel telefono.</p>
      </div>

      <div className="panel">
        <span className="eyebrow">Segnalazioni</span>
        <p>Un mercato manca, è sbagliato o non esiste più? <a href={REPORT_MAIL}>Scrivici</a>: la mail parte già compilata.</p>
      </div>

      <p className="note version">Fuori · Mercatini d'Italia · Versione 2.1 · Catalogo statico</p>
    </div>
  )
}
