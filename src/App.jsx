import { useState, useCallback, useMemo, useEffect, useRef } from "react";
import { useMarkets } from "./hooks/useMarkets";
import { displayEntries } from './lib/marketGrouping';
import { destinationForMarket } from './lib/marketDirections.js';
import Explore, { CATEGORY_FILTERS } from './screens/Explore.jsx';
import Weekly from './screens/Weekly.jsx';
import Detail from './screens/Detail.jsx';
import MapScreen from './screens/MapScreen.jsx';
import Agenda from './screens/Agenda.jsx';
import More from './screens/More.jsx';
import TabBar from './ui/TabBar.jsx';
import WhereSheet from './ui/WhereSheet.jsx';
import WhenSheet from './ui/WhenSheet.jsx';
import { todayStr, isFreeEntry } from './lib/display.js';
import { DEFAULT_WHEN, whenDays, firstDayIn, whenLabel } from './lib/when.js';
import { searchMarkets, matchCities } from './lib/search.js';
import { haversine } from './services/staticMarkets.js';

const NEAR_KM = 50;
const PAGE = 30;
// One history entry per opened layer, so the phone's Back closes the top layer and never leaves the app.
const ROOT = { fuori: 1, tab: 'esplora', view: 'main', sheet: null, search: false, market: null };
const WHERE_KEY = 'fuori.where';
const PROMPT_KEY = 'fuori.where.prompt';
const readStore = (key, fallback) => { try { const v = localStorage.getItem(key); return v ? JSON.parse(v) : fallback; } catch { return fallback; } };
const writeStore = (key, value) => { try { localStorage.setItem(key, JSON.stringify(value)); } catch { /* private mode: nothing to keep */ } };
const hashMarket = () => new URLSearchParams(window.location.hash.replace(/^#/, '')).get('mercato');
const urlFor = id => window.location.pathname + window.location.search + (id ? '#mercato=' + encodeURIComponent(id) : '');
const rank = m => (m.dateQuality === 'riportata' || m.dateQuality === 'confermata' ? 10 : 0) + (m.description ? 3 : 0) +
  (isFreeEntry(m.entry) ? 2 : 0) + (m.address ? 1 : 0);
const matchCategory = (key, market) => {
  const filter = CATEGORY_FILTERS.find(f => f.key === key);
  if (!filter || key === 'tutti') return true;
  return filter.free ? isFreeEntry(market.entry) : filter.cats.includes(market.category);
};

export default function App() {
  const {
    markets: allMarkets, loading, error, favorites, toggleFav: hookToggleFav, getMarketDetails, cities,
    userLat, userLng, positionStatus, positionError, requestPosition, clearPosition, canonicalId,
  } = useMarkets();

  const [tab, setTab] = useState('esplora');
  const [view, setView] = useState('main');          // esplora: main | weekly
  const [sheet, setSheet] = useState(null);           // where | when
  const [query, setQuery] = useState('');
  const [where, setWhereState] = useState(() => {
    const stored = readStore(WHERE_KEY, null);
    return stored && ['city', 'region', 'italia'].includes(stored.mode) ? stored : { mode: 'italia' };
  });
  const [when, setWhen] = useState(DEFAULT_WHEN);
  const [category, setCategory] = useState('tutti');
  const [includeEstimated, setIncludeEstimated] = useState(false);
  const [visibleCount, setVisibleCount] = useState(PAGE);
  const [promptDismissed, setPromptDismissed] = useState(() => readStore(PROMPT_KEY, false));
  const [wantGps, setWantGps] = useState(false);
  const [manualCity, setManualCity] = useState('');
  const [weeklyCity, setWeeklyCity] = useState('');
  const [selectedMarket, setSelectedMarket] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');
  const [toast, setToast] = useState(null);
  // ponytail: list style picked from the address (?lista=) while the owner compares; one style stays after.
  const [listStyle] = useState(() => { const v = new URLSearchParams(window.location.search).get('lista'); return ['righe', 'biglietti', 'locandine', 'griglia'].includes(v) ? v : 'biglietti'; });
  const selectedRef = useRef(null);
  const marketsRef = useRef(allMarkets);
  marketsRef.current = allMarkets;
  const barRef = useRef(null);
  const canUseDistance = Number.isFinite(userLat) && Number.isFinite(userLng);

  // Day headers stick right under the Dove/Quando bar, whatever its height.
  useEffect(() => {
    const el = barRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver(() => document.documentElement.style.setProperty('--header-h', el.offsetHeight + 'px'));
    observer.observe(el);
    return () => observer.disconnect();
  }, [tab, view, query]);

  const showToast = useCallback(msg => { setToast(msg); setTimeout(() => setToast(null), 2200); }, []);
  const toggleFav = useCallback(id => {
    showToast(favorites.has(id) ? 'Tolto dai salvati.' : 'Salvato: lo trovi in «Salvati».');
    hookToggleFav(id);
  }, [favorites, hookToggleFav, showToast]);

  const setWhere = useCallback(next => {
    setWhereState(next);
    setIncludeEstimated(false);
    if (next.mode !== 'gps') writeStore(WHERE_KEY, next);
    window.scrollTo(0, 0);
  }, []);

  // ─── Market page loading ─────────────────────────────────
  const loadMarket = useCallback(async market => {
    selectedRef.current = market;
    setSelectedMarket(market);
    setDetailError('');
    setDetailLoading(true);
    try {
      const detailed = await getMarketDetails(market.id);
      if (detailed && selectedRef.current?.id === market.id) { selectedRef.current = detailed; setSelectedMarket(detailed); }
    } catch (err) {
      setDetailError(err.message || 'Impossibile caricare i dettagli');
    } finally {
      setDetailLoading(false);
    }
  }, [getMarketDetails]);

  const openById = useCallback(async requested => {
    // A link shared for a soft-merged copy opens its kept record; a concluded market still opens.
    const id = await canonicalId(requested).catch(() => requested);
    const item = marketsRef.current.find(m => m.id === id) || await getMarketDetails(id).catch(() => null);
    if (item) loadMarket(item);
  }, [canonicalId, getMarketDetails, loadMarket]);

  // ─── History: every layer is one step back ───────────────
  const snapRef = useRef(ROOT);
  const applySnap = useCallback(s => {
    snapRef.current = s;
    setTab(s.tab);
    setView(s.view);
    setSheet(s.sheet);
    if (!s.search) setQuery('');
    if (!s.market) { selectedRef.current = null; setSelectedMarket(null); }
    else if (selectedRef.current?.id !== s.market) openById(s.market);
  }, [openById]);
  const applyRef = useRef(applySnap);
  applyRef.current = applySnap;
  const go = useCallback(change => {
    const next = { ...snapRef.current, ...change };
    window.history.pushState(next, '', urlFor(next.market));
    applyRef.current(next);
  }, []);
  const replace = useCallback(change => {
    const next = { ...snapRef.current, ...change };
    window.history.replaceState(next, '', urlFor(next.market));
    applyRef.current(next);
  }, []);
  const back = useCallback(() => window.history.back(), []);

  useEffect(() => {
    if (window.history.state?.fuori) applyRef.current(window.history.state);
    else {
      const id = hashMarket();
      window.history.replaceState(ROOT, '', urlFor(null));
      if (id) {
        // A shared link: the market page sits on top of Esplora, so Back stays in the app.
        const next = { ...ROOT, market: id };
        window.history.pushState(next, '', urlFor(id));
        applyRef.current(next);
      }
    }
    const onPop = e => {
      if (e.state?.fuori) applyRef.current(e.state);
      else if (!hashMarket()) applyRef.current(ROOT);
    };
    const onHash = () => {
      const id = hashMarket();
      if (!id || id === snapRef.current.market) return;
      const next = { ...snapRef.current, market: id };
      window.history.replaceState(next, '', window.location.href);
      applyRef.current(next);
    };
    window.addEventListener('popstate', onPop);
    window.addEventListener('hashchange', onHash);
    return () => { window.removeEventListener('popstate', onPop); window.removeEventListener('hashchange', onHash); };
  }, []);

  const openMarket = useCallback(market => { loadMarket(market); go({ market: market.id }); }, [loadMarket, go]);

  const onQuery = q => {
    setQuery(q);
    setVisibleCount(PAGE);
    if (q.trim() && !snapRef.current.search) go({ search: true });
    else if (!q.trim() && snapRef.current.search) { snapRef.current = { ...snapRef.current, search: false }; back(); }
  };
  const onTab = id => {
    if (id === snapRef.current.tab) {
      if (id === 'esplora' && snapRef.current.view !== 'main') go({ view: 'main' });
      window.scrollTo(0, 0);
      return;
    }
    go({ tab: id, view: 'main', sheet: null, search: false });
    window.scrollTo(0, 0);
  };

  // ─── Dove ────────────────────────────────────────────────
  const askGps = () => {
    if (canUseDistance) { setWhere({ mode: 'gps' }); if (snapRef.current.sheet) back(); return; }
    setWantGps(true);
    requestPosition();
  };
  useEffect(() => {
    if (!wantGps) return;
    if (positionStatus === 'ready' && canUseDistance) {
      setWantGps(false);
      setWhere({ mode: 'gps' });
      if (snapRef.current.sheet) back();
    } else if (['denied', 'error', 'unavailable'].includes(positionStatus)) setWantGps(false);
  }, [wantGps, positionStatus, canUseDistance, setWhere, back]);
  const confirmCity = () => {
    const name = manualCity.trim().toLocaleLowerCase('it');
    const match = cities.find(city => city.toLocaleLowerCase('it') === name);
    if (!match) { showToast('Scegli una città presente nel catalogo.'); return; }
    clearPosition();
    setWhere({ mode: 'city', city: match });
    setManualCity('');
    back();
  };
  const chooseItaly = () => {
    clearPosition();
    setWhere({ mode: 'italia' });
    setPromptDismissed(true);
    writeStore(PROMPT_KEY, true);
    if (snapRef.current.sheet) back();
  };
  const pickCity = city => { clearPosition(); setWhere({ mode: 'city', city }); back(); };

  // ─── What Esplora shows ──────────────────────────────────
  const days = useMemo(() => whenDays(when, todayStr), [when]);
  const live = useMemo(() => allMarkets.filter(m => !m.concluded), [allMarkets]);
  const center = useMemo(() => {
    if (where.mode === 'gps' && canUseDistance) return { lat: userLat, lng: userLng };
    if (where.mode !== 'city') return null;
    const points = live.filter(m => m.city === where.city && Number.isFinite(m.lat) && Number.isFinite(m.lng));
    if (!points.length) return null;
    return { lat: points.reduce((s, m) => s + m.lat, 0) / points.length, lng: points.reduce((s, m) => s + m.lng, 0) / points.length };
  }, [where, canUseDistance, userLat, userLng, live]);
  const kmFrom = useCallback(m => (center && Number.isFinite(m.lat) && Number.isFinite(m.lng) ? haversine(center.lat, center.lng, m.lat, m.lng) : null), [center]);
  const inWhere = useCallback(m => {
    if (where.mode === 'gps') return Number.isFinite(m.distance) && m.distance <= NEAR_KM && (includeEstimated || m.positionQuality === 'precisa');
    if (where.mode === 'city') { const km = kmFrom(m); return m.city === where.city || (km !== null && km <= NEAR_KM); }
    if (where.mode === 'region') return m.region === where.region;
    return true;
  }, [where, includeEstimated, kmFrom]);
  const whereShort = where.mode === 'gps' ? 'Vicino a me' : where.mode === 'city' ? where.city : where.mode === 'region' ? where.region : 'Tutta Italia';
  const whereLabel = where.mode === 'city' ? where.city + ' e dintorni' : whereShort;

  const baseEvents = useMemo(() => live
    .filter(m => m.isEvent && inWhere(m))
    .map(m => ({
      market: m,
      day: firstDayIn(m.dates, days, todayStr),
      km: where.mode === 'city' ? kmFrom(m) : null,
      twoDays: Boolean(days && days.length === 2 && days.every(d => m.dates.includes(d))),
    }))
    .filter(item => !days || item.day), [live, inWhere, days, where, kmFrom]);
  const categoryCounts = useMemo(() => Object.fromEntries(CATEGORY_FILTERS.map(f =>
    [f.key, baseEvents.filter(item => matchCategory(f.key, item.market)).length])), [baseEvents]);
  const nearFirst = where.mode === 'gps' || where.mode === 'city';
  const eventItems = useMemo(() => baseEvents
    .filter(item => matchCategory(category, item.market))
    .sort((a, b) => (a.day || '9999').localeCompare(b.day || '9999') ||
      (nearFirst ? ((where.mode === 'gps' ? a.market.distance : a.km) ?? 999) - ((where.mode === 'gps' ? b.market.distance : b.km) ?? 999)
        : rank(b.market) - rank(a.market)) ||
      a.market.name.localeCompare(b.market.name, 'it')), [baseEvents, category, nearFirst, where]);
  // Four posters for the richest events across Italy (colours dealt so neighbours differ).
  const featured = useMemo(() => {
    if (category !== 'tutti' || nearFirst || eventItems.length <= 8) return [];
    const sorted = eventItems.filter(item => item.market.description).sort((a, b) => rank(b.market) - rank(a.market));
    const perCat = new Map(); const picked = [];
    for (const item of sorted) {
      const c = item.market.category;
      if ((perCat.get(c) || 0) >= 2) continue;
      perCat.set(c, (perCat.get(c) || 0) + 1); picked.push(item);
      if (picked.length === 4) break;
    }
    const groups = [...new Set(picked.map(i => i.market.category))].map(c => picked.filter(i => i.market.category === c));
    const dealt = [];
    while (dealt.length < picked.length) for (const g of groups) if (g.length) dealt.push(g.shift());
    return dealt;
  }, [eventItems, category, nearFirst]);
  const listItems = useMemo(() => {
    const shown = new Set(featured.map(i => i.market.id));
    return eventItems.filter(i => !shown.has(i.market.id));
  }, [eventItems, featured]);
  useEffect(() => setVisibleCount(PAGE), [where, when, category]);

  const nearestCity = useMemo(() => {
    if (where.mode !== 'gps') return '';
    const nearest = live.filter(m => Number.isFinite(m.distance) && m.distance <= 15 && m.positionQuality === 'precisa')
      .sort((a, b) => a.distance - b.distance)[0];
    return nearest ? nearest.city : '';
  }, [where, live]);
  const weeklyCityName = where.mode === 'city' ? where.city : nearestCity;
  const weeklyMarkets = useMemo(() => !weeklyCityName ? [] : live
    .filter(m => !m.isEvent && m.city === weeklyCityName && (!days || m.dates.some(d => days.includes(d))))
    .sort((a, b) => (firstDayIn(a.dates, days, todayStr) || '9999').localeCompare(firstDayIn(b.dates, days, todayStr) || '9999') ||
      a.name.localeCompare(b.name, 'it')), [live, weeklyCityName, days]);
  const weeklyEntries = useMemo(() => displayEntries(weeklyMarkets, { keepSingleWeeklyGroups: when.kind === 'weekday' })
    .map(entry => entry.kind === 'group' ? entry : { ...entry, day: firstDayIn(entry.market.dates, days, todayStr) }),
  [weeklyMarkets, when, days]);
  const regions = useMemo(() => {
    if (where.mode !== 'italia') return [];
    const counts = new Map();
    for (const item of baseEvents) counts.set(item.market.region, (counts.get(item.market.region) || 0) + 1);
    return [...counts.entries()].filter(([name]) => name).sort((a, b) => b[1] - a[1] || a[0].localeCompare(b[0], 'it'));
  }, [where, baseEvents]);

  const n = eventItems.length;
  const resultsLine = `${n === 1 ? '1 mercatino o evento' : n.toLocaleString('it-IT') + ' mercatini ed eventi'} · ${whereLabel} · ${whenLabel(when).toLowerCase()}`;
  const emptyActions = [
    ...(when.kind !== 'weekend' || (when.offset || 0) === 0 ? [{ label: 'Prova il prossimo weekend', onClick: () => setWhen({ kind: 'weekend', offset: 1 }) }] : []),
    ...(where.mode !== 'italia' ? [{ label: 'Allarga a tutta Italia', onClick: chooseItaly }] : []),
    ...(when.kind !== 'tutte' ? [{ label: 'Tutte le date', onClick: () => setWhen({ kind: 'tutte' }) }] : []),
  ];
  const searchResults = useMemo(() => (query.trim() ? searchMarkets(live, query, todayStr) : []), [live, query]);
  const cityMatches = useMemo(() => (query.trim() ? matchCities(cities, query) : []), [cities, query]);
  const mapMarkets = useMemo(() => [...eventItems.map(i => i.market), ...weeklyMarkets], [eventItems, weeklyMarkets]);

  // ─── Market page actions ─────────────────────────────────
  const shareMarket = async market => {
    const url = new URL(window.location.href);
    url.hash = 'mercato=' + encodeURIComponent(market.id);
    const payload = { title: market.name, text: market.city, url: url.toString() };
    try {
      if (navigator.share) await navigator.share(payload);
      else if (navigator.clipboard?.writeText) { await navigator.clipboard.writeText(payload.url); showToast('Link del mercato copiato.'); }
      else window.prompt('Copia questo link per condividerlo:', payload.url);
    } catch (err) {
      if (err?.name !== 'AbortError') showToast('Condivisione non riuscita.');
    }
  };
  const openDirections = market => {
    // Directions only after the full regional details (with the source holds) have arrived.
    if (detailLoading || detailError) { showToast('Indicazioni non disponibili finché i dettagli non sono verificati.'); return; }
    const destination = destinationForMarket(market);
    if (!destination) { showToast('Indirizzo non abbastanza preciso per navigare.'); return; }
    window.open('https://www.google.com/maps/dir/?api=1&destination=' + encodeURIComponent(destination), '_blank', 'noopener,noreferrer');
  };
  const copyMarketAddress = async market => {
    if (!market.address?.trim()) { showToast('Indirizzo non disponibile.'); return; }
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard not supported');
      await navigator.clipboard.writeText(market.address);
      showToast('Indirizzo copiato.');
    } catch {
      showToast('Seleziona il testo dell’indirizzo per copiarlo.');
    }
  };
  const leaveMarketFor = change => replace({ market: null, tab: 'esplora', view: 'main', search: false, sheet: null, ...change });

  const context = { whereLabel: whereShort, whenLabel: whenLabel(when), onOpenWhere: () => go({ sheet: 'where' }), onOpenWhen: () => go({ sheet: 'when' }) };

  return (
    <div className="app-container">
      {tab === 'esplora' && (view === 'weekly'
        ? <Weekly city={weeklyCity} markets={live} onOpen={openMarket} onBack={back} />
        : <Explore {...context} barRef={barRef} query={query} onQuery={onQuery} loading={loading} error={error}
            onRetry={() => window.location.reload()}
            showPrompt={where.mode === 'italia' && !promptDismissed} onPromptNearby={askGps} onPromptDismiss={chooseItaly}
            category={category} onCategory={setCategory} categoryCounts={categoryCounts}
            resultsLine={resultsLine} gps={where.mode === 'gps'} includeEstimated={includeEstimated}
            onToggleEstimated={() => setIncludeEstimated(v => !v)}
            items={listItems} featured={featured} visibleCount={visibleCount} onMore={() => setVisibleCount(c => c + PAGE)}
            whenKind={when.kind} emptyActions={emptyActions} listStyle={listStyle}
            weekly={{ city: weeklyCityName, entries: weeklyEntries }} weekdaySelected={when.kind === 'weekday' ? when.weekday : null}
            onWeeklyAll={city => { setWeeklyCity(city); go({ view: 'weekly' }); }}
            regions={regions} onRegion={region => setWhere({ mode: 'region', region })}
            results={searchResults} cityMatches={cityMatches} onPickCity={pickCity} today={todayStr}
            onOpen={openMarket} favorites={favorites} onToggleFav={toggleFav} getMarketDetails={getMarketDetails} />)}
      {tab === 'mappa' && (
        <MapScreen {...context} markets={mapMarkets} userLat={userLat} userLng={userLng} onSelect={openMarket}
          label={`${mapMarkets.length.toLocaleString('it-IT')} mercati sulla mappa`}
          onList={() => go({ tab: 'esplora', view: 'main' })} />
      )}
      {tab === 'salvati' && (
        <Agenda markets={allMarkets} favorites={favorites} onOpen={openMarket} onToggleFav={toggleFav}
          onExplore={() => go({ tab: 'esplora', view: 'main' })} />
      )}
      {tab === 'altro' && <More />}

      {sheet === 'where' && (
        <WhereSheet where={where} cities={cities} manualCity={manualCity} setManualCity={setManualCity}
          onGps={askGps} onCity={confirmCity} onItaly={chooseItaly} onClose={back}
          positionStatus={positionStatus} positionError={positionError} />
      )}
      {sheet === 'when' && <WhenSheet when={when} onPick={w => { setWhen(w); back(); }} onClose={back} />}
      {selectedMarket && (
        <Detail market={selectedMarket} loading={detailLoading} error={detailError} allMarkets={allMarkets}
          favorites={favorites} onToggleFav={toggleFav} onBack={back} onShare={shareMarket}
          onDirections={openDirections} onCopyAddress={copyMarketAddress} onOpen={openMarket}
          onShowCity={city => { clearPosition(); setWhere({ mode: 'city', city }); setWhen({ kind: 'tutte' }); leaveMarketFor({}); }}
          onShowRegion={region => { setWhere({ mode: 'region', region }); leaveMarketFor({}); }} />
      )}
      {toast && <div className="toast" role="status">{toast}</div>}
      <TabBar tab={tab} onTab={onTab} />
    </div>
  );
}
