import { useMemo, useState } from 'react'
import Icon from '../ui/Icon.jsx'
import { TODAY, todayStr, localISO, formatDateIT, dateQualityLabel, dayHeaderLabel, getNextDate, uniqueByName } from '../lib/display.js'
import { downloadCalendarEvent } from '../lib/calendarFile.js'
import { reportUrl } from '../lib/report.js'
import { haversine } from '../services/staticMarkets.js'
import { italianKey } from '../lib/marketGrouping.js'
import { UNKNOWN_CITY_HELP, VENUE_UNCONFIRMED_HELP } from '../lib/locationQuality'
import { marketDateDisclosure } from '../lib/dateDisclosure.js'
import { mergeContacts, sourceCalendarView, sourceContacts, sourceHoursForDate } from '../lib/sourceCalendar.js'
import { editorialContacts, editorialSummaryView } from '../lib/editorialEvidence.js'
import { addressConflictView } from '../lib/sourceFieldConflicts.js'
import { destinationForMarket } from '../lib/marketDirections.js'

const longDate = iso => new Date(iso + 'T12:00:00').toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' })
const nextDay = iso => { const d = new Date(iso + 'T12:00:00'); d.setDate(d.getDate() + 1); return localISO(d) }
const isFree = text => /gratuit|libero/i.test(text || '')

// The market page in magazine order: what and when, next opening, facts, text, tips,
// nearby, provenance. Every safety note of the previous page is kept.
export default function Detail({
  market: m, loading, error, allMarkets, favorites, onToggleFav, onBack, onShare, onDirections,
  onCopyAddress, onOpen, onShowCity, onShowRegion,
}) {
  const [expanded, setExpanded] = useState(false)
  const isFav = favorites.has(m.id)
  const futureDates = useMemo(() => m.dates.filter(d => d >= todayStr).sort(), [m.dates])
  const nextDate = futureDates[0] || null
  const secondDate = nextDate && futureDates[1] === nextDay(nextDate) ? futureDates[1] : null
  const weekAhead = useMemo(() => { const d = new Date(TODAY); d.setDate(d.getDate() + 7); return localISO(d) }, [])
  const nearby = useMemo(() => Number.isFinite(m.lat) && Number.isFinite(m.lng) ? uniqueByName(allMarkets
    .filter(x => x.id !== m.id && Number.isFinite(x.lat) && Number.isFinite(x.lng) && x.dates.some(d => d >= todayStr && d <= weekAhead))
    .map(x => ({ market: x, km: haversine(m.lat, m.lng, x.lat, x.lng) }))
    .filter(x => x.km <= 30).sort((a, b) => a.km - b.km), item => item.market).slice(0, 4) : [], [m, allMarkets, weekAhead])
  const sameCity = useMemo(() => m.locationReviewRequired ? [] : uniqueByName(allMarkets
    .filter(x => x.id !== m.id && x.city === m.city && !x.locationReviewRequired && italianKey(x.name) !== italianKey(m.name))
    .sort((a, b) => (getNextDate(a.dates) || '9999').localeCompare(getNextDate(b.dates) || '9999'))), [m, allMarkets])
  const canNavigate = !loading && !error && Boolean(destinationForMarket(m))
  const sourceSchedule = sourceCalendarView(m)
  const summary = editorialSummaryView(m)
  const editorial = summary.evidence
  const contacts = mergeContacts(sourceContacts(m.sourceDetail), editorialContacts(m))
  const addressConflicts = addressConflictView(m)
  const confirmed = m.dateQuality === 'confermata' || m.dateQuality === 'riportata'
  const disclosure = marketDateDisclosure(m.dates, m.dateQuality)
  const hours = summary.hours || (sourceSchedule.rows.length ? 'Vedi gli orari delle singole date' : '')
  const longDescription = (m.description || '').length > 420

  return (
    <div className="detail-page rivista">
      <div className="detail-bar">
        <button type="button" className="detail-back ico-btn" aria-label="Indietro" onClick={onBack}><Icon name="chevronLeft" size={18} strokeWidth={2} /></button>
        <div className="detail-bar-actions">
          <button type="button" className="ico-btn" aria-label="Condividi questo mercato" onClick={() => onShare(m)}><Icon name="upload" size={18} /></button>
          <button type="button" className={'ico-btn' + (isFav ? ' on' : '')} aria-label={isFav ? 'Togli dall’agenda' : 'Salva in agenda'} onClick={() => onToggleFav(m.id)}>
            <Icon name="bookmark" size={18} strokeWidth={isFav ? 2.4 : 1.8} />
          </button>
        </div>
      </div>

      <div className="detail-head">
        <span className="eyebrow">{m.category}{summary.recurrence ? ' · ' + summary.recurrence : ''}</span>
        <h1 className="detail-title">{m.name}</h1>
        {loading && <div className="note">Caricamento dettagli completi…</div>}
        {error && <div role="alert" className="note">{error}. Sono visibili i dati sintetici.</div>}
        <p className="detail-place"><strong>{m.city}</strong>{m.region && <span className="muted"> · {m.region}</span>}</p>
      </div>

      <div className="next-panel">
        <span className="eyebrow">Prossima apertura</span>
        {nextDate ? (
          <>
            <div className="next-day">{dayHeaderLabel(nextDate)}</div>
            {secondDate && <div className="next-second">e {longDate(secondDate)}</div>}
            {sourceHoursForDate(m, nextDate) && <div className="next-hours">{sourceHoursForDate(m, nextDate)}</div>}
            <div className={confirmed ? 'ok' : 'note'}>
              {confirmed && <Icon name="check" size={14} strokeWidth={2.5} />}
              {dateQualityLabel(m.dateQuality)}{m.lastVerified ? ', letta il ' + m.lastVerified : ''}
            </div>
          </>
        ) : <div className="next-day">Date da verificare</div>}
        {disclosure && <p className="note">{disclosure}</p>}
        {m.concluded && <p role="note" className="note">Non più in programma: la fonte non indica nuove date.</p>}
        <div className="next-actions">
          <button type="button" className="btn-primary" onClick={() => onToggleFav(m.id)}>
            <Icon name="bell" size={18} color="currentColor" strokeWidth={2} />{isFav ? 'In agenda' : 'Ricordamelo'}
          </button>
          <button type="button" className="btn-secondary" onClick={() => onDirections(m)} disabled={!canNavigate}
            title={!canNavigate ? 'Dettagli o sede non sufficienti per navigare' : 'Apri indicazioni stradali'}>
            <Icon name="pin" size={18} strokeWidth={2} />Indicazioni
          </button>
        </div>
        {nextDate && (
          <button type="button" className="link" onClick={() => downloadCalendarEvent(m, nextDate, sourceHoursForDate(m, nextDate))}>
            Aggiungi al calendario
          </button>
        )}
        {futureDates.length > 1 && (
          <details className="source-calendar">
            <summary>Tutte le date previste ({futureDates.length})</summary>
            <div className="detail-dates-chips">
              {futureDates.map(d => {
                const dow = new Date(d + 'T00:00:00').getDay()
                return <span key={d} className={`date-chip ${d === todayStr ? 'today' : dow === 0 || dow === 6 ? 'weekend' : ''}`} title={sourceHoursForDate(m, d)}>{formatDateIT(d)}</span>
              })}
            </div>
          </details>
        )}
      </div>

      <div className="facts">
        <div className="fact"><b>Orario</b><span>{hours || 'Orari non disponibili'}</span></div>
        <div className="fact"><b>Dove</b><span className="detail-address">{m.address || 'Indirizzo non verificato'}</span></div>
        {m.entry && <div className="fact"><b>Ingresso</b><span className={isFree(m.entry) ? 'free' : ''}>{m.entry}</span></div>}
        {m.stalls && <div className="fact"><b>Banchi</b><span>Circa {m.stalls} secondo la fonte</span></div>}
        {!m.entry && !m.stalls && summary.recurrence && <div className="fact"><b>Cadenza</b><span>{summary.recurrence}</span></div>}
      </div>

      <div className="detail-notes">
        {sourceSchedule.notes.map((note, i) => <p key={note + i} className="note">{note}</p>)}
        {addressConflicts.length > 0 && <p className="note">Indirizzo salvato, discordante con la fonte</p>}
        {addressConflicts.map(conflict => (
          <div role="note" key={conflict.key}>
            <p className="note">La fonte indica invece: <strong>{conflict.sourceAddress}</strong>.{' '}
              <a href={conflict.sourceUrl} target="_blank" rel="noopener noreferrer">Happings</a>{' · pagina letta il ' + conflict.readOnLabel}</p>
          </div>
        ))}
        {m.locationReviewRequired && (
          <p role="note" className="note">{m.cityUncertain ? UNKNOWN_CITY_HELP : VENUE_UNCONFIRMED_HELP} Le indicazioni stradali per questa scheda sono disabilitate.</p>
        )}
        {m.positionQuality !== 'precisa' && (
          <p className="note">{m.positionFromOsm ? <>Posizione indicativa: la via, non il punto esatto del mercato ·{' '}
            <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors</a></>
            : 'Posizione indicativa o da verificare'}</p>
        )}
        {!canNavigate && !loading && (
          <p role="note" className="note">{addressConflicts.length > 0
            ? 'Indicazioni sospese: l’indirizzo salvato è discordante con la fonte.'
            : 'Indicazioni non disponibili: manca una sede riconciliata e verificabile.'}</p>
        )}
        {m.address?.trim() && (
          <button type="button" className="link" onClick={() => onCopyAddress(m)}
            title={addressConflicts.length > 0 ? 'Copia l’indirizzo salvato, segnalato come discordante' : 'Copia indirizzo'}>Copia l’indirizzo</button>
        )}
      </div>

      {(sourceSchedule.rows.length > 0 || editorial) && (
        <div className="detail-block">
          <h2>Dalla fonte</h2>
          {sourceSchedule.rows.length > 0 && (
            <details className="source-calendar" key={m.id} open={sourceSchedule.hasVariations || sourceSchedule.rows.length <= 3}>
              <summary>Date e orari riportati dalla fonte ({sourceSchedule.rows.length})</summary>
              <dl>
                {sourceSchedule.rows.map(row => (
                  <div key={row.key} className="source-calendar-row" data-period={row.kind === 'interval'}>
                    <dt>{row.label}</dt>
                    <dd>{row.status && <strong>{row.status}{row.hours ? ' · ' : ''}</strong>}{row.hours}
                      {row.note && <p className="source-calendar-note">{row.note}</p>}</dd>
                  </div>
                ))}
              </dl>
            </details>
          )}
          {editorial && (
            <div>
              <p className="note"><strong>{editorial.title}</strong></p>
              {editorial.notes.map((note, i) => <p key={note + i} className="note">{note}</p>)}
              {editorial.hours && <p><strong>{editorial.hoursLabel}:</strong> {editorial.hours}</p>}
              {editorial.recurrence && <p className="note">Cadenza descritta nella pagina: {editorial.recurrence}</p>}
              {editorial.rows.length > 0 && (
                <details className="source-calendar" key={m.id + '/editorial'} open={editorial.rows.length <= 3}>
                  <summary>Date e periodi descritti nella pagina ({editorial.rows.length})</summary>
                  <dl>
                    {editorial.rows.map(row => (
                      <div key={row.key} className="source-calendar-row" data-period={row.kind === 'interval'}>
                        <dt>{row.label}</dt>
                        <dd><strong>{row.status}{row.hours ? ' · ' : ''}</strong>{row.hours}
                          {row.note && <p className="source-calendar-note">{row.note}</p>}</dd>
                      </div>
                    ))}
                  </dl>
                </details>
              )}
              <p className="note"><a href={editorial.sourceUrl} target="_blank" rel="noopener noreferrer">{editorial.sourceName}</a>
                {' · pagina letta il ' + editorial.readOn}<br />{editorial.editorialDate}</p>
            </div>
          )}
        </div>
      )}

      {m.description && (
        <div className="detail-block">
          <h2>Il mercato</h2>
          <p className={longDescription && !expanded ? 'clamp' : ''}>{m.description}</p>
          {longDescription && <button type="button" className="link" onClick={() => setExpanded(v => !v)}>{expanded ? 'Mostra meno' : 'Leggi tutto'}</button>}
        </div>
      )}

      {m.tips && (
        <div className="tip">
          <span className="eyebrow">Consiglio pratico</span>
          <p>{m.tips}</p>
        </div>
      )}

      {nearby.length > 0 && (
        <div className="detail-block">
          <h2>Nei prossimi 7 giorni, qui vicino</h2>
          {nearby.map(({ market, km }) => (
            <button type="button" className="near" key={market.id} onClick={() => onOpen(market)}>
              <span className="d">{formatDateIT(getNextDate(market.dates))}</span>
              <span><span className="t">{market.name}</span><span className="s">{market.city} · circa {Math.max(1, Math.round(km))} km</span></span>
            </button>
          ))}
          <p className="note">Distanze indicative tra i punti sulla mappa, non tra gli ingressi dei mercati.</p>
        </div>
      )}

      {(contacts.organizer || contacts.links.length > 0) && (
        <div className="detail-block">
          <h2>Contatti riportati dalla fonte</h2>
          {contacts.organizer && <p>Organizzatore: {contacts.organizer.href
            ? <a href={contacts.organizer.href} target="_blank" rel="noopener noreferrer">{contacts.organizer.label}</a>
            : contacts.organizer.label}</p>}
          {contacts.links.map((contact, i) => (
            <p key={contact.href + i} style={{ overflowWrap: 'anywhere' }}><a href={contact.href} target="_blank" rel="noopener noreferrer">{contact.label}</a></p>
          ))}
        </div>
      )}

      {m.tags && m.tags.length > 0 && (
        <div className="detail-tags">{m.tags.map(t => <span key={t} className="tag">{t}</span>)}</div>
      )}

      <div className="provenance">
        {m.lastVerified ? 'Scheda verificata il ' + m.lastVerified : 'Verifica individuale non documentata'} · Fonte: {m.source || 'non disponibile'}
        {m.sourceUpdated ? (m.sourceUpdateScope === 'dataset'
          ? ' · dataset aggiornato il ' + m.sourceUpdated + ' (non verifica del singolo mercato)'
          : ' · data dichiarata dalla fonte: ' + m.sourceUpdated) : ''}
        {m.sourceUrl && <> · <a href={m.sourceUrl} target="_blank" rel="noopener noreferrer">Controlla la fonte originale</a></>}
        {(m.sourceEvidence || []).filter(s => s.url !== m.sourceUrl).slice(0, 3).map((s, i) => (
          <span key={s.url + i}> · Fonte aggiuntiva: <a href={s.url} target="_blank" rel="noopener noreferrer">{s.nome}</a></span>
        ))}
        {(m.fieldEvidence || []).map((evidence, i) => (
          <div key={evidence.sourceUrl + evidence.readOn + i} style={{ marginTop: 8 }}>
            <strong>{evidence.fields}: riscontro nella fonte</strong> ·{' '}
            <a href={evidence.sourceUrl} target="_blank" rel="noopener noreferrer">{evidence.sourceName}</a>
            {' · letta il ' + evidence.readOn} · {evidence.sourceDate ? 'data dei contenuti: ' + evidence.sourceDate : 'data dei contenuti non dichiarata'}
          </div>
        ))}
        {(m.calendarExceptions || []).filter(e => e.data >= todayStr).map((exception, i) => (
          <div key={exception.data + i} style={{ marginTop: 8 }}>
            <strong>{exception.data}: edizione annullata</strong> · {exception.motivo}{' '}
            <a href={exception.url} target="_blank" rel="noopener noreferrer">Fonte</a>
          </div>
        ))}
        <div style={{ marginTop: 10 }}>
          Informazioni non corrette? <a href={reportUrl(m)}>Segnala un errore</a>
          {m.region && <> · <button type="button" className="link" onClick={() => onShowRegion(m.region)}>Altri mercatini in {m.region} ›</button></>}
        </div>
      </div>

      {sameCity.length > 0 && (
        <div className="detail-block">
          <h2>Altri mercati a {m.city}</h2>
          {sameCity.slice(0, 5).map(market => (
            <button type="button" className="near" key={market.id} onClick={() => onOpen(market)}>
              <span className="d">{formatDateIT(getNextDate(market.dates))}</span>
              <span><span className="t">{market.name}</span><span className="s">{market.category}{market.hours ? ' · ' + market.hours : ''}</span></span>
            </button>
          ))}
          {sameCity.length > 5 && (
            <button type="button" className="btn-secondary" onClick={() => onShowCity(m.city)}>Vedi tutti i {sameCity.length + 1} mercati a {m.city}</button>
          )}
        </div>
      )}
    </div>
  )
}
