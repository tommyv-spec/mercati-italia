import { useMemo } from 'react'
import SearchField from '../ui/SearchField.jsx'
import Pill from '../ui/Pill.jsx'
import Section from '../ui/Section.jsx'
import EventRow from '../ui/EventRow.jsx'
import FeaturedTile from '../ui/FeaturedTile.jsx'
import WeeklyRow from '../ui/WeeklyRow.jsx'
import WeekendStepper from '../ui/WeekendStepper.jsx'
import Skeleton from '../ui/Skeleton.jsx'
import { weekendOf, inWeekend } from '../lib/weekend.js'
import { TODAY, todayStr } from '../lib/display.js'
import { italianKey } from '../lib/marketGrouping.js'
import { haversine } from '../services/staticMarkets.js'

const CATEGORY_PILLS = [
  ['Antiquariato', ['Antiquariato']],
  ['Vintage e usato', ['Vintage e abbigliamento', 'Usato']],
  ['Artigianato', ['Artigianato']],
  ['Alimentare', ['Alimentare']],
  ['Settimanali', ['Misto']],
]
const NEARBY_KM = 50
const HOME_EVENTS = 10
const HOME_FEATURED = 4
const HOME_WEEKLY = 3
const HOME_REGIONS = 10

const longDay = iso => {
  const s = new Date(iso + 'T12:00:00').toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' })
  return s.charAt(0).toUpperCase() + s.slice(1)
}
const rank = m => (m.dateQuality === 'riportata' || m.dateQuality === 'confermata' ? 10 : 0) + (m.description ? 3 : 0) +
  (/gratuit|libero/i.test(m.entry || '') ? 2 : 0) + (m.address ? 1 : 0)

export default function Home({
  markets, loading, error, onRetry, query, onQuery, weekendOffset, onWeekend, onSeeAll, onCategory, onRegion,
  onNearby, onAllItaly, positionStatus, canUseDistance, center, cityForToday, onWeeklyCity, onChooseCity,
  onOpen, favorites, onToggleFav,
}) {
  const weekend = useMemo(() => weekendOf(TODAY, weekendOffset), [weekendOffset])
  const live = useMemo(() => markets.filter(m => !m.concluded), [markets])

  const events = useMemo(() => {
    let list = live.filter(m => m.isEvent && inWeekend(m.dates, weekend))
    if (center) {
      // Around the visitor (GPS) or around the chosen city: nearest first, 50 km.
      list = list.map(m => ({ m, d: Number.isFinite(m.lat) && Number.isFinite(m.lng) ? haversine(center.lat, center.lng, m.lat, m.lng) : Infinity }))
        .filter(x => x.d <= NEARBY_KM).sort((a, b) => a.d - b.d).map(x => x.m)
    } else {
      list.sort((a, b) => rank(b) - rank(a) || a.name.localeCompare(b.name, 'it'))
    }
    return list
  }, [live, weekend, center])

  const todayWeekly = useMemo(() => {
    if (!cityForToday) return []
    const key = italianKey(cityForToday)
    return live.filter(m => !m.isEvent && m.dates.includes(todayStr) && italianKey(m.city) === key)
      .sort((a, b) => a.name.localeCompare(b.name, 'it'))
  }, [live, cityForToday])

  const regions = useMemo(() => {
    const counts = new Map()
    for (const m of live) if (m.isEvent && m.region) counts.set(m.region, (counts.get(m.region) || 0) + 1)
    return [...counts.entries()].sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'it')).slice(0, HOME_REGIONS)
  }, [live])

  // Four poster tiles for the richest events, then everyone else by day.
  const featured = useMemo(() => {
    const sorted = [...events].filter(m => m.description).sort((a, b) => rank(b) - rank(a) || a.name.localeCompare(b.name, 'it'))
    // Mix the colours: at most two tiles per category, then fill up.
    const perCat = new Map(); const picked = []
    for (const m of sorted) {
      if ((perCat.get(m.category) || 0) >= 2) continue
      perCat.set(m.category, (perCat.get(m.category) || 0) + 1); picked.push(m)
      if (picked.length === HOME_FEATURED) break
    }
    for (const m of sorted) { if (picked.length >= HOME_FEATURED) break; if (!picked.includes(m)) picked.push(m) }
    return picked
  }, [events])
  const byDay = useMemo(() => {
    const picked = new Set(featured.map(m => m.id))
    const rest = events.filter(m => !picked.has(m.id)).slice(0, HOME_EVENTS)
    return [
      [weekend.sat, rest.filter(m => m.dates.includes(weekend.sat))],
      [weekend.sun, rest.filter(m => !m.dates.includes(weekend.sat))],
    ].filter(([, list]) => list.length > 0)
  }, [events, featured, weekend])
  const firstDay = m => m.dates.includes(weekend.sat) ? weekend.sat : weekend.sun
  const bothDays = m => m.dates.includes(weekend.sat) && m.dates.includes(weekend.sun)
  const todayLabel = TODAY.toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' })
  const scope = center ? center.label : 'in Italia'

  return (
    <div className="home">
      <div className="band">
        <div className="band-top">
          <span className="wordmark">Fuori</span>
          <span className="eyebrow">Mercatini d'Italia</span>
        </div>
        <SearchField value={query} onChange={onQuery} />
        <WeekendStepper weekend={weekend} offset={weekendOffset} onChange={onWeekend} />
        <div className="stat">
          <span className="results-count">
            {loading ? 'Caricamento del catalogo…' : <><strong>{events.length.toLocaleString('it-IT')}</strong> mercatini ed eventi {scope}</>}
          </span>
          <span aria-hidden="true">·</span>
          {canUseDistance
            ? <button type="button" onClick={onAllItaly}>Tutta Italia</button>
            : <button type="button" onClick={onNearby} disabled={positionStatus === 'requesting'}>
                {positionStatus === 'requesting' ? 'Cerco la posizione…' : 'Mercati vicino a me'}
              </button>}
        </div>
      </div>

      <div className="pill-row">
        {CATEGORY_PILLS.map(([label, cats]) => (
          <Pill key={label} onClick={() => onCategory(cats)}>{label}</Pill>
        ))}
      </div>

      <Section title="Mercatini ed eventi"
        aside={events.length > 0 && <button type="button" onClick={onSeeAll}>Vedi tutti i {events.length.toLocaleString('it-IT')} ›</button>}>
        {loading ? <Skeleton /> : error ? (
          <div className="empty">Catalogo non raggiungibile.<br /><button type="button" className="btn-secondary" onClick={onRetry}>Riprova</button></div>
        ) : events.length === 0 ? (
          <div className="empty">
            Nessun evento in programma {weekend.label === 'Questo weekend' ? 'questo weekend' : 'in quel weekend'} {scope}.
            {weekendOffset < 8 && <><br /><button type="button" className="btn-secondary" onClick={() => onWeekend(weekendOffset + 1)}>Prova il weekend dopo</button></>}
          </div>
        ) : (
          <>
            {featured.length > 0 && (
              <div className="feat-row" aria-label="In evidenza">
                {featured.map(m => <FeaturedTile key={m.id} market={m} date={firstDay(m)} onOpen={onOpen} />)}
              </div>
            )}
            {byDay.map(([day, list]) => (
              <div key={day}>
                <h3 className="day-sub">{longDay(day)}<span className="day-sub-n">{list.length}</span></h3>
                {list.map(m => (
                  <EventRow key={m.id} market={m} date={firstDay(m)} twoDays={bothDays(m)} hot={false}
                    onOpen={onOpen} onToggleFav={onToggleFav} isFav={favorites.has(m.id)} />
                ))}
              </div>
            ))}
          </>
        )}
      </Section>

      <Section title="Il mercato oggi" aside={<span className="eyebrow">{todayLabel}{cityForToday ? ' · ' + cityForToday : ''}</span>}>
        {!cityForToday ? (
          <div className="empty">
            Scegli la tua città per vedere i mercati settimanali aperti oggi.<br />
            <button type="button" className="btn-secondary" onClick={onChooseCity}>Scegli una città</button>
          </div>
        ) : loading ? <Skeleton rows={2} /> : todayWeekly.length === 0 ? (
          <div className="empty">Nessun mercato settimanale in programma oggi a {cityForToday}.</div>
        ) : (
          <div className="weekly-box">
            {todayWeekly.slice(0, HOME_WEEKLY).map(m => <WeeklyRow key={m.id} market={m} onOpen={onOpen} />)}
            <button type="button" className="box-link" onClick={() => onWeeklyCity(cityForToday)}>
              Tutti i {todayWeekly.length} mercati di oggi a {cityForToday} ›
            </button>
          </div>
        )}
        <p className="note">Mercati comunali settimanali, raggruppati per città. <button type="button" className="link" onClick={onChooseCity}>Cambia città</button></p>
      </Section>

      <Section title="Per regione">
        <div className="region-grid">
          {regions.map(([name]) => <button key={name} type="button" className="region-link" onClick={() => onRegion(name)}>{name}</button>)}
        </div>
        <button type="button" className="box-link" onClick={() => onRegion('')}>Tutte le regioni ›</button>
      </Section>
    </div>
  )
}
