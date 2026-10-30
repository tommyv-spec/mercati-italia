import { Fragment } from 'react'
import Icon from '../ui/Icon.jsx'
import SearchField from '../ui/SearchField.jsx'
import Pill from '../ui/Pill.jsx'
import EventRow from '../ui/EventRow.jsx'
import Skeleton from '../ui/Skeleton.jsx'
import WeeklyCityGroup from '../components/WeeklyCityGroup.jsx'
import { WEEKDAY_LABELS, shouldAutoExpandWeeklyGroup } from '../lib/marketGrouping.js'
import { getNextDate, dayHeaderLabel } from '../lib/display.js'

const DATE_PILLS = [['oggi', 'Oggi'], ['weekend', 'Questo weekend'], ['7giorni', 'Prossimi 7 giorni']]
const WEEKDAY_LONG = ['lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato', 'domenica']

// The full list with today's filter engine: compact band, one tools row, day headers.
export default function List({
  headerRef, query, onQuery, onHome, loading, error,
  filteredMarkets, groupedList, visibleCount, onMore,
  activeDateFilter, onDateFilter, weekdayFilter, onWeekday, onClearWeekday,
  filterCity, filterRegion, filterCategories, onRemoveCity, onRemoveRegion, onRemoveCategories, onResetAll,
  activeFilterCount, onOpenFilters,
  canUseDistance, filterDistance, includeEstimatedNearby, onToggleEstimated,
  positionStatus, positionError, onNearby,
  sortBy, onSort, showSort, setShowSort, viewMode, setViewMode,
  userLat, userLng, favorites, onToggleFav, onOpen, getMarketDetails, dataMode,
  eventsOnly = false, onToggleEventsOnly,
}) {
  const nearbyLabel = positionStatus === 'ready'
    ? (includeEstimatedNearby ? 'Vicino a me · posizioni indicative' : 'Vicino a me · 50 km, posizioni precise')
    : positionStatus === 'requesting' ? 'Cerco la posizione…' : 'Mercati vicino a me'
  const countText = loading ? 'Caricamento mercati statici...'
    : `${filteredMarkets.length.toLocaleString('it-IT')} ${activeDateFilter
      ? 'appuntament' + (filteredMarkets.length === 1 ? 'o' : 'i') + ' ' + (activeDateFilter === 'oggi' ? 'previsti oggi' : activeDateFilter === 'weekend' ? 'previsti nel weekend' : 'previsti nei prossimi 7 giorni')
      : 'sched' + (filteredMarkets.length === 1 ? 'a' : 'e') + ' nel catalogo'}${filterCity ? ' · ' + filterCity : filterRegion ? ' · ' + filterRegion : !canUseDistance ? ' · Italia' : ''}`
    + (viewMode === 'lista' && groupedList.length < filteredMarkets.length ? ` · ${groupedList.length.toLocaleString('it-IT')} schede` : '')
  const dayOf = e => e.kind === 'group'
    ? e.markets.map(x => getNextDate(x.dates)).filter(Boolean).sort()[0] || null
    : getNextDate(e.market.dates)

  return (
    <div className="list-screen">
      <div className="band band-compact" ref={headerRef}>
        <div className="band-top">
          <button type="button" className="back-home" onClick={onHome}><Icon name="chevronLeft" size={16} strokeWidth={2.2} /> Home</button>
          <span className="eyebrow">Mercatini d'Italia</span>
        </div>
        <SearchField value={query} onChange={onQuery} />
      </div>

      <div className="list-tools">
        <Pill onClick={onOpenFilters}><Icon name="filter" size={13} />{' '}Filtri{activeFilterCount > 0 ? ' · ' + activeFilterCount : ''}</Pill>
        <div className="sort-wrap">
          <Pill onClick={() => setShowSort(!showSort)}><Icon name="sort" size={13} />{' '}Ordina</Pill>
          {showSort && (
            <div className="sort-dropdown">
              {[['data', 'Data', 'calendar'], ['distanza', 'Distanza', 'mapPin']].map(([key, label, icon]) => (
                <button key={key} type="button" className={`sort-option ${sortBy === key ? 'active' : ''}`}
                  disabled={key === 'distanza' && !canUseDistance}
                  title={key === 'distanza' && !canUseDistance ? 'Attiva la posizione per ordinare per distanza' : ''}
                  onClick={() => { onSort(key); setShowSort(false) }}>
                  <Icon name={icon} size={16} /> {label}
                  {sortBy === key && <Icon name="check" size={16} color="#B94439" />}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <div className="list-tools">
        <button type="button" className={'pill' + (canUseDistance ? ' active' : '')} onClick={onNearby} disabled={positionStatus === 'requesting'}>
          <Icon name="mapPin" size={13} />{' '}{nearbyLabel}
        </button>
        {DATE_PILLS.map(([key, label]) => (
          <Pill key={key} active={activeDateFilter === key} onClick={() => onDateFilter(key)}>{label}</Pill>
        ))}
      </div>
      {positionError && <div role="alert" className="list-note" style={{ color: '#A5443D' }}>{positionError}</div>}

      <div className="weekday-row" aria-label="Filtra per giorno della settimana">
        {WEEKDAY_LABELS.map((day, i) => (
          <button key={day} type="button" aria-pressed={weekdayFilter === i} aria-label={'Mostra mercati del ' + WEEKDAY_LONG[i]}
            className={'pill' + (weekdayFilter === i ? ' active' : '')} onClick={() => onWeekday(i)}>{day}</button>
        ))}
        {weekdayFilter !== null && (
          <button type="button" className="pill" onClick={onClearWeekday} aria-label="Togli filtro giorno">×</button>
        )}
      </div>

      {(filterCity || filterRegion || filterCategories.length > 0 || eventsOnly) && (
        <div className="active-chips">
          {eventsOnly && <Pill active onClick={onToggleEventsOnly}>Solo mercatini ed eventi ×</Pill>}
          {filterCity && <Pill active onClick={onRemoveCity}>Città: {filterCity} ×</Pill>}
          {filterRegion && <Pill active onClick={onRemoveRegion}>Regione: {filterRegion} ×</Pill>}
          {filterCategories.length > 0 && <Pill active onClick={onRemoveCategories}>Categorie ×</Pill>}
          <Pill onClick={onResetAll}>Azzera filtri</Pill>
        </div>
      )}
      {canUseDistance && filterDistance < 100 && (
        <div role="note" className="list-note">
          {includeEstimatedNearby
            ? 'Mostriamo anche mercati con coordinate non verificate. Alcuni possono non essere davvero vicini.'
            : 'Nel raggio mostriamo solo mercati con posizione precisa. Altri mercati possono mancare.'}
          <br />
          <Pill onClick={onToggleEstimated}>{includeEstimatedNearby ? 'Escludi posizioni indicative' : 'Mostra anche posizioni indicative'}</Pill>
        </div>
      )}

      <div className="results-count">
        <span>{countText}</span>
        {dataMode === 'demo' && <span className="tag">DEMO</span>}
      </div>

      {error && !loading && (
        <div role="alert" className="empty-state">
          <div className="empty-title">Catalogo temporaneamente non disponibile</div>
          <div className="empty-text">{error}</div>
        </div>
      )}

      {loading ? (
        <div className="markets-list rivista"><Skeleton rows={3} /></div>
      ) : (
        <div className="markets-list rivista">
          {groupedList.length > 0 ? (
            <>
              {groupedList.slice(0, visibleCount).map((entry, i, shown) => {
                const showDay = sortBy !== 'distanza' && (i === 0 || dayOf(entry) !== dayOf(shown[i - 1]))
                return (
                  <Fragment key={entry.key}>
                    {showDay && <h2 className="day-header">{dayHeaderLabel(dayOf(entry))}</h2>}
                    {entry.kind === 'group'
                      ? <WeeklyCityGroup group={entry} loadMarket={getMarketDetails} onOpenMarket={onOpen}
                          selectedWeekday={weekdayFilter}
                          autoExpand={shouldAutoExpandWeeklyGroup(entry, weekdayFilter, filterCity, query)} />
                      : <EventRow market={entry.market} when="" showBadge={false} onOpen={onOpen}
                          onToggleFav={onToggleFav} isFav={favorites.has(entry.market.id)} />}
                  </Fragment>
                )
              })}
              {visibleCount < groupedList.length && (
                <button type="button" className="btn-secondary" style={{ margin: '18px auto 30px', display: 'block' }} onClick={onMore}>
                  Mostra altre schede ({Math.min(visibleCount, groupedList.length)} di {groupedList.length})
                </button>
              )}
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-title">Nessun mercato trovato</div>
              <div className="empty-text">
                {canUseDistance && filterDistance < 100 && !includeEstimatedNearby
                  ? 'Nessun mercato con posizione precisa in questo raggio e periodo. Puoi includere quelli con posizione indicativa.'
                  : 'Prova a cambiare data, distanza, città o categoria.'}
              </div>
              {canUseDistance && filterDistance < 100 && !includeEstimatedNearby && (
                <button type="button" className="btn-secondary" onClick={onToggleEstimated}>Mostra posizioni indicative</button>
              )}
              <br />
              <button type="button" className="btn-secondary" onClick={onResetAll}>Reimposta</button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
