import { useEffect, useId, useMemo, useState } from 'react'
import { distinctWeekdays, groupVenues, groupVenueAppointments, nextMatchingDate, WEEKDAY_LABELS } from '../lib/marketGrouping'
import { marketDateDisclosure } from '../lib/dateDisclosure'
import './WeeklyCityGroup.css'

function dateLabel(iso) {
  if (!iso) return 'Data da verificare'
  return new Date(iso + 'T12:00:00').toLocaleDateString('it-IT', {
    weekday: 'short', day: 'numeric', month: 'short',
  })
}

export default function WeeklyCityGroup({
  group, loadMarket, onOpenMarket, selectedWeekday = null, autoExpand = false,
}) {
  const panelId = useId()
  const [expanded, setExpanded] = useState(autoExpand)
  const [detailsById, setDetailsById] = useState({})
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState('')
  const [showUnknownVenues, setShowUnknownVenues] = useState(false)
  const [expandedSourceRecords, setExpandedSourceRecords] = useState({})

  const idsKey = group.markets.map(m => m.id).join('|')
  useEffect(() => {
    if (autoExpand) setExpanded(true)
  }, [autoExpand])

  // Fetch the regional static file only when someone actually wants to see
  // the venues. Multiple member requests share the same cached shard promise.
  useEffect(() => {
    if (!expanded) return undefined
    const missing = group.markets.filter(m => !detailsById[m.id])
    if (!missing.length) return undefined
    let cancelled = false
    setLoading(true)
    setLoadError('')
    Promise.allSettled(missing.map(m => loadMarket(m.id))).then(results => {
      if (cancelled) return
      const loaded = {}
      let failures = 0
      results.forEach((item, index) => {
        if (item.status === 'fulfilled' && item.value) {
          loaded[missing[index].id] = item.value
        } else {
          // A summary is still a valid and navigable original record.
          loaded[missing[index].id] = missing[index]
          failures++
        }
      })
      setDetailsById(prev => ({ ...prev, ...loaded }))
      if (failures) setLoadError('Alcune sedi non sono disponibili nei dettagli: riprova più tardi.')
      setLoading(false)
    })
    return () => { cancelled = true }
    // Intentionally refetch only missing IDs after filter/expanded transitions.
  }, [expanded, idsKey, loadMarket])

  const weekdays = useMemo(() => distinctWeekdays(group.markets), [group.markets])
  const next = useMemo(() => group.markets
    .map(m => nextMatchingDate(m.dates || [], selectedWeekday))
    .filter(Boolean).sort()[0] || null, [group.markets, selectedWeekday])

  const venues = useMemo(() => {
    if (!expanded) return []
    return groupVenues(group.markets.map(m => detailsById[m.id] || m))
  }, [group.markets, detailsById, expanded])

  const knownVenues = venues.filter(venue => venue.verifiedAddress)
  const unknownVenues = venues.filter(venue => !venue.verifiedAddress)
  // A record without an address may refer to a named venue in this city,
  // but source evidence is insufficient to assert that it does.
  const displayedVenues = [
    ...knownVenues,
    ...(showUnknownVenues || knownVenues.length === 0 ? unknownVenues : []),
  ]

  const uncertain = group.markets.some(m => m.dateQuality !== 'confermata')
  const disclosure = marketDateDisclosure(
    group.markets.flatMap(m => m.dates || []),
    uncertain ? 'prevista' : 'confermata'
  )

  return (
    <article className="weekly-city-card" data-testid="weekly-city-group"
      aria-label={`Mercati settimanali a ${group.city}`}>
      <div className="weekly-city-top">
        <span className="weekly-city-overline">Mercati settimanali · {group.city}</span>
        <span className="weekly-city-counter">{group.markets.length} schede</span>
      </div>
      <h2 className="weekly-city-heading">Mercati settimanali a {group.city}</h2>
      <div className="weekly-city-subtitle">
        <span>{weekdays.length ? `${weekdays.length} ${weekdays.length === 1 ? 'giornata' : 'giornate'} della settimana` : 'Calendario da verificare'}</span>
        {next && <span>Prossimo: {dateLabel(next)}</span>}
      </div>
      <div className="weekly-day-chips" aria-label="Giorni registrati">
        {weekdays.map(day => <span key={day}
          className={selectedWeekday === day ? 'weekly-day-chip highlighted' : 'weekly-day-chip'}>
          {WEEKDAY_LABELS[day]}
        </span>)}
      </div>
      {disclosure && (
        <p className="weekly-city-caution">{disclosure}</p>
      )}
      <button type="button" className="weekly-city-toggle"
        aria-controls={panelId} aria-expanded={expanded}
        onClick={() => setExpanded(v => !v)}>
        <span>{expanded ? 'Nascondi sedi e giornate' : 'Visualizza sedi e giornate'}</span>
        <span aria-hidden="true" className={expanded ? 'weekly-chevron open' : 'weekly-chevron'}>⌄</span>
      </button>
      {expanded && (
        <div id={panelId} className="weekly-city-panel">
          {loading && <div className="weekly-load" role="status">Caricamento sedi…</div>}
          {loadError && <p className="weekly-city-caution" role="alert">{loadError}</p>}
          {!loading && venues.length > 0 && (
            <>
              <p className="weekly-venue-total">
                {knownVenues.length} {knownVenues.length === 1 ? 'sede riportata' : 'sedi riportate'}
                {unknownVenues.length > 0 && ` · ${unknownVenues.length} ${unknownVenues.length === 1 ? 'scheda' : 'schede'} senza indirizzo`}.
                Ogni scheda e fonte resta accessibile. Le segnalazioni identiche sono raggruppate solo nella visualizzazione.
              </p>
              {unknownVenues.length > 0 && knownVenues.length > 0 && (
                <button type="button" className="weekly-unknown-toggle"
                  aria-expanded={showUnknownVenues}
                  onClick={() => setShowUnknownVenues(v => !v)}>
                  {showUnknownVenues ? 'Nascondi' : 'Mostra'}
                  {` ${unknownVenues.length} ${unknownVenues.length === 1 ? 'appuntamento' : 'appuntamenti'} senza sede identificata`}
                </button>
              )}
              {displayedVenues.map((venue, i) => (
                <section className="weekly-venue" key={venue.key}
                  data-known={venue.verifiedAddress ? 'true' : 'false'}
                  aria-label={venue.address || 'Sede da verificare'}>
                  <div className="weekly-venue-title-row">
                    <span className="weekly-venue-index">{i + 1}</span>
                    <div>
                      <h3 className="weekly-venue-title">{venue.address || 'Sede da verificare'}</h3>
                      {!venue.verifiedAddress && <p className="weekly-venue-note">
                        Indirizzo assente o troppo generico: non unito ad altre sedi
                      </p>}
                    </div>
                  </div>
                  <div className="weekly-appointment-list">
                    {groupVenueAppointments(venue.markets).map(visit => {
                      const market = visit.market
                      const date = nextMatchingDate(market.dates || [], selectedWeekday)
                      const expandedCopies = Boolean(expandedSourceRecords[visit.key])
                      return (
                        <div key={visit.key} className="weekly-appointment-group">
                          <button type="button" className="weekly-appointment"
                            onClick={() => onOpenMarket(market)}
                            aria-label={'Apri ' + dateLabel(date) + ', ' + (venue.address || group.city)}>
                            <span className="weekly-appointment-date">{dateLabel(date)}</span>
                            <span className="weekly-appointment-meta">
                              {market.hours || 'Orario da verificare'}
                              {market.dateQuality !== 'confermata' && <small> · Previsto</small>}
                            </span>
                            <span aria-hidden="true" className="weekly-appointment-arrow">›</span>
                          </button>
                          {visit.records.length > 1 && (
                            <>
                              <button type="button" className="weekly-duplicate-toggle"
                                aria-expanded={expandedCopies}
                                onClick={() => setExpandedSourceRecords(prev => ({
                                  ...prev, [visit.key]: !prev[visit.key],
                                }))}>
                                {visit.records.length} schede della stessa fonte
                                {' · '}{expandedCopies ? 'Nascondi originali' : 'Mostra originali'}
                              </button>
                              {expandedCopies && (
                                <div className="weekly-duplicate-records">
                                  {visit.records.map(record => (
                                    <button type="button" className="weekly-original-record"
                                      key={record.id} onClick={() => onOpenMarket(record)}>
                                      {record.name}{' · '}{record.hours || 'Orario da verificare'}
                                      <span aria-hidden="true">›</span>
                                    </button>
                                  ))}
                                </div>
                              )}
                            </>
                          )}
                        </div>
                      )
                    })}
                  </div>
                </section>
              ))}
            </>
          )}
        </div>
      )}
    </article>
  )
}
