import { Fragment } from 'react'
import Icon from '../ui/Icon.jsx'
import SearchField from '../ui/SearchField.jsx'
import Section from '../ui/Section.jsx'
import EventRow from '../ui/EventRow.jsx'
import FeaturedTile from '../ui/FeaturedTile.jsx'
import Skeleton from '../ui/Skeleton.jsx'
import ContextBar from '../ui/ContextBar.jsx'
import CategoryIcon, { categoryColor } from '../ui/CategoryIcon.jsx'
import WeeklyCityGroup from '../components/WeeklyCityGroup.jsx'
import { shouldAutoExpandWeeklyGroup } from '../lib/marketGrouping.js'
import { dayHeaderLabel, localISO } from '../lib/display.js'
import { TicketCard, PosterCard, GridTile, DayDivider } from '../ui/ListCards.jsx'

export const CATEGORY_FILTERS = [
  { key: 'tutti', label: 'Tutti' },
  { key: 'antiquariato', label: 'Antiquariato', cats: ['Antiquariato'] },
  { key: 'vintage', label: 'Vintage e usato', cats: ['Vintage e abbigliamento', 'Usato'] },
  { key: 'artigianato', label: 'Artigianato', cats: ['Artigianato'] },
  { key: 'alimentare', label: 'Alimentare', cats: ['Alimentare'] },
  { key: 'gratis', label: 'Gratis', free: true },
]

// Esplora: one page that answers "where do I go, and when?". Typing in the search
// field swaps the page for the search results; clearing it brings the page back.
export default function Explore(p) {
  const { query, onQuery, loading, error, onRetry } = p
  return (
    <div className="explore">
      <div className="band band-awning">
        <div className="band-top">
          <span className="wordmark">Fuori</span>
          <span className="eyebrow">Mercatini d'Italia</span>
        </div>
        <SearchField value={query} onChange={onQuery} />
      </div>
      {query.trim() ? <SearchResults {...p} /> : (
        <>
          <ContextBar barRef={p.barRef} whereLabel={p.whereLabel} whenLabel={p.whenLabel} onWhere={p.onOpenWhere} onWhen={p.onOpenWhen} />
          {p.showPrompt && (
            <div className="prompt" role="region" aria-label="Dove vuoi andare">
              <strong>Dove vuoi andare?</strong>
              <p>Ti mostriamo i mercatini entro 50 km, divisi per giorno.</p>
              <div className="prompt-actions">
                <button type="button" className="btn-primary" onClick={p.onPromptNearby}><Icon name="navigation" size={16} strokeWidth={2} />Mercati vicino a me</button>
                <button type="button" className="btn-secondary" onClick={p.onOpenWhere}>Scegli una città</button>
              </div>
              <button type="button" className="link" onClick={p.onPromptDismiss}>Non ora, guardo tutta Italia</button>
            </div>
          )}
          <div className="cat-chips" aria-label="Che cosa cerchi">
            {CATEGORY_FILTERS.map(f => (
              <button key={f.key} type="button" aria-pressed={p.category === f.key}
                className={'cat-chip' + (p.category === f.key ? ' on' : '')}
                style={{ '--c': f.free ? 'var(--olive)' : f.cats ? categoryColor(f.cats[0]) : 'var(--ink)' }}
                onClick={() => p.onCategory(f.key)}>
                {f.cats && <CategoryIcon category={f.cats[0]} size={16} strokeWidth={2} />}
                {f.free && <Icon name="ticket" size={16} strokeWidth={2} />}
                <span>{f.label}</span>
                {!loading && <span className="n">{(p.categoryCounts[f.key] || 0).toLocaleString('it-IT')}</span>}
              </button>
            ))}
          </div>
          <p className="results-count">{loading ? 'Caricamento del catalogo…' : p.resultsLine}</p>
          {p.gps && (
            <div role="note" className="list-note">
              {p.includeEstimated ? 'Vicino a me · 50 km, anche posizioni indicative' : 'Vicino a me · 50 km, posizioni precise'}
              {' '}<button type="button" className="link" onClick={p.onToggleEstimated}>
                {p.includeEstimated ? 'Solo posizioni precise' : 'Mostra anche posizioni indicative'}
              </button>
            </div>
          )}
          {loading ? <div className="section"><Skeleton /></div> : error ? (
            <div className="empty">Catalogo non raggiungibile.<br /><button type="button" className="btn-secondary" onClick={onRetry}>Riprova</button></div>
          ) : (
            <>
              <Events {...p} />
              <WeeklySection {...p} />
              {p.regions.length > 0 && (
                <Section title="Per regione">
                  <div className="region-grid">
                    {p.regions.map(([name, n]) => (
                      <button key={name} type="button" className="region-link" onClick={() => p.onRegion(name)}>
                        <span>{name}</span><span className="region-n">{n}</span>
                      </button>
                    ))}
                  </div>
                </Section>
              )}
            </>
          )}
        </>
      )}
    </div>
  )
}

function Events({ items, featured, visibleCount, onMore, onOpen, favorites, onToggleFav, emptyActions, whenKind, listStyle, today }) {
  if (!items.length) {
    return (
      <div className="empty">
        Nessun mercatino in questo periodo e in questa zona.
        <div className="empty-actions">{emptyActions.map(a => <button key={a.label} type="button" className="btn-secondary" onClick={a.onClick}>{a.label}</button>)}</div>
      </div>
    )
  }
  const tomorrow = localISO(new Date(new Date(today + 'T12:00:00').getTime() + 86400000))
  const perDay = new Map()
  for (const it of items) perDay.set(it.day, (perDay.get(it.day) || 0) + 1)
  const days = []
  for (const it of items.slice(0, visibleCount)) {
    if (!days.length || days[days.length - 1].day !== it.day) days.push({ day: it.day, items: [] })
    days[days.length - 1].items.push(it)
  }
  const Card = { biglietti: TicketCard, locandine: PosterCard, griglia: GridTile }[listStyle]
  const card = it => Card
    ? <Card key={it.market.id} market={it.market} date={it.day} km={it.km} onOpen={onOpen} onToggleFav={onToggleFav} isFav={favorites.has(it.market.id)} />
    : <EventRow key={it.market.id} market={it.market} date={it.day} twoDays={whenKind === 'weekend' && it.twoDays} showDate={!it.day}
        hot={false} km={it.km} onOpen={onOpen} onToggleFav={onToggleFav} isFav={favorites.has(it.market.id)} />
  return (
    <div className="section">
      {featured.length > 0 && (
        <div className="feat-row" aria-label="In evidenza">
          {featured.map(it => <FeaturedTile key={it.market.id} market={it.market} date={it.day} onOpen={onOpen} />)}
        </div>
      )}
      <div className={Card ? 'list-area list-' + listStyle : 'markets-list rivista'}>
        {days.map(group => (
          <Fragment key={group.day || 'nd'}>
            {Card ? <DayDivider day={group.day} count={perDay.get(group.day)} today={today} tomorrow={tomorrow} />
              : <h2 className="day-header">{dayHeaderLabel(group.day)}</h2>}
            {Card ? <div className={listStyle === 'griglia' ? 'markets-grid' : 'cards-col'}>{group.items.map(card)}</div> : group.items.map(card)}
          </Fragment>
        ))}
      </div>
      {visibleCount < items.length && (
        <button type="button" className="btn-secondary more-btn" onClick={onMore}>
          Mostra altri ({items.length - visibleCount})
        </button>
      )}
    </div>
  )
}

function WeeklySection({ weekly, onOpen, favorites, onToggleFav, getMarketDetails, onOpenWhere, onWeeklyAll, weekdaySelected }) {
  return (
    <Section title="Mercati settimanali" aside={weekly.city && <span className="eyebrow">{weekly.city}</span>}>
      {!weekly.city ? (
        <div className="empty">
          I mercati comunali di ogni settimana si vedono città per città.<br />
          <button type="button" className="btn-secondary" onClick={onOpenWhere}>Scegli una città</button>
        </div>
      ) : weekly.entries.length === 0 ? (
        <div className="empty">Nessun mercato settimanale a {weekly.city} nei giorni scelti.</div>
      ) : (
        <div className="markets-list rivista">
          {weekly.entries.map(entry => entry.kind === 'group'
            ? <WeeklyCityGroup key={entry.key} group={entry} loadMarket={getMarketDetails} onOpenMarket={onOpen}
                selectedWeekday={weekdaySelected} autoExpand={shouldAutoExpandWeeklyGroup(entry, weekdaySelected, weekly.city, '')} />
            : <EventRow key={entry.key} market={entry.market} date={entry.day} hot={false}
                onOpen={onOpen} onToggleFav={onToggleFav} isFav={favorites.has(entry.market.id)} />)}
        </div>
      )}
      {weekly.city && <button type="button" className="box-link" onClick={() => onWeeklyAll(weekly.city)}>Tutti i mercati settimanali di {weekly.city}, giorno per giorno ›</button>}
    </Section>
  )
}

function SearchResults({ query, results, cityMatches, onPickCity, visibleCount, onMore, onOpen, favorites, onToggleFav, today }) {
  const shown = results.slice(0, visibleCount)
  return (
    <div className="search-results">
      {cityMatches.length > 0 && (
        <div className="city-matches">
          {cityMatches.map(city => (
            <button key={city} type="button" className="city-match" onClick={() => onPickCity(city)}>
              <span className="opt-ico"><Icon name="mapPin" size={18} strokeWidth={2} /></span>
              <span><strong>Mercatini a {city} e dintorni</strong><span className="opt-sub">Scegli {city} come zona</span></span>
              <Icon name="chevronRight" size={18} />
            </button>
          ))}
        </div>
      )}
      <p className="results-count">{results.length === 1 ? '1 mercato' : results.length.toLocaleString('it-IT') + ' mercati'} per «{query.trim()}»</p>
      {results.length === 0 ? (
        <div className="empty">Nessun mercato con queste parole. Prova con il nome della città o del mercatino.</div>
      ) : (
        <div className="section">
          <div className="markets-list rivista">
            {shown.map(m => {
              const day = [...m.dates].sort().find(d => d >= today) || null
              return <EventRow key={m.id} market={m} date={day} onOpen={onOpen} onToggleFav={onToggleFav} isFav={favorites.has(m.id)} />
            })}
          </div>
          {visibleCount < results.length && (
            <button type="button" className="btn-secondary more-btn" onClick={onMore}>Mostra altri ({results.length - visibleCount})</button>
          )}
        </div>
      )}
    </div>
  )
}
