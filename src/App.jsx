import { useState, useCallback, useMemo, useEffect, useRef, lazy, Suspense, Fragment } from "react";
import { useMarkets } from "./hooks/useMarkets";
import { displayEntries, weekdayFromISO, WEEKDAY_LABELS, shouldAutoExpandWeeklyGroup, italianKey } from './lib/marketGrouping';
import WeeklyCityGroup from './components/WeeklyCityGroup.jsx';
import { UNKNOWN_CITY_HELP, VENUE_UNCONFIRMED_HELP } from './lib/locationQuality';
import { marketDateDisclosure } from './lib/dateDisclosure.js';
import { mergeContacts, sourceCalendarView, sourceContacts, sourceHoursForDate } from './lib/sourceCalendar.js';
import { editorialContacts, editorialSummaryView } from './lib/editorialEvidence.js';
import { addressConflictView } from './lib/sourceFieldConflicts.js';
import { destinationForMarket } from './lib/marketDirections.js';
import { effectiveDateFilter } from './lib/searchDateFilter.js';
import Home from './screens/Home.jsx';
import List from './screens/List.jsx';
import Weekly from './screens/Weekly.jsx';
import FilterSheet from './ui/FilterSheet.jsx';
import EventRow from './ui/EventRow.jsx';
import Detail from './screens/Detail.jsx';
import { weekendOf, inWeekend } from './lib/weekend.js';
import Icon from './ui/Icon.jsx';
import { CATEGORY_COLORS, localISO, TODAY, todayStr, formatDateIT, getDateBadge, dateQualityLabel, dateLeaf, dayHeaderLabel, getNextDate, uniqueByName } from './lib/display.js';
import { downloadCalendarEvent } from './lib/calendarFile.js';
import { reportUrl } from './lib/report.js';
import { haversine } from './services/staticMarkets.js';

// ─── Sample Data (kept as fallback, but primary source is useMarkets hook) ──
// Market records come from the versioned static catalog, not bundled fixtures.
const CATEGORIES = ["Alimentare", "Antiquariato", "Vintage e abbigliamento", "Usato", "Artigianato", "Misto"];
const REGIONS = [];
const CITIES = [];

const CATEGORY_ICONS = {
  "Alimentare": "🍅", "Antiquariato": "🏺", "Vintage e abbigliamento": "👗",
  "Usato": "📦", "Artigianato": "🎨", "Misto": "🎪"
};


// User position (Firenze as default)
const USER_LAT = 43.7696;
const USER_LNG = 11.2558;


// ─── Main App ───────────────────────────────────────────────
export default function App() {
  // Data from Firebase (auto-seeds on first load)
  const {
    markets: allMarkets,
    loading: marketsLoading,
    error: marketsError,
    seedStatus,
    favorites,
    toggleFav: hookToggleFav,
    getMarketDetails,
    categories: hookCategories,
    regions: hookRegions,
    cities: hookCities,
    categoryIcons: hookCatIcons,
    categoryColors: hookCatColors,
    dataMode,
    userLat, userLng, positionStatus, positionError,
    requestPosition, clearPosition, canonicalId,
  } = useMarkets();

  const [tab, setTab] = useState("esplora");
  const [view, setView] = useState("home");        // esplora: home | list | weekly
  const [weekendOffset, setWeekendOffset] = useState(0);
  const [weeklyCity, setWeeklyCity] = useState("");
  const [eventsOnly, setEventsOnly] = useState(false);   // list opened from the home events
  const [viewMode, setViewMode] = useState("lista");
  const [searchQuery, setSearchQuery] = useState("");
  // Prioritize visits people can actually plan; deselect to browse undated markets.
  const [dateFilter, setDateFilter] = useState('7giorni');
  const [dateFilterExplicit, setDateFilterExplicit] = useState(false);
  // Search should discover every market, including ones without a future
  // date; manually selected calendar chips always remain authoritative.
  const activeDateFilter = effectiveDateFilter(dateFilter, searchQuery, dateFilterExplicit);
  const [weekdayFilter, setWeekdayFilter] = useState(null);
  const [visibleCount, setVisibleCount] = useState(60);
  const [showFilters, setShowFilters] = useState(false);
  const [showSort, setShowSort] = useState(false);
  const [sortBy, setSortBy] = useState("data");
  const [selectedMarket, setSelectedMarket] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');

  const [toast, setToast] = useState(null);

  // Filter states
  const [filterCategories, setFilterCategories] = useState([]);
  const [filterRegion, setFilterRegion] = useState("");
  const [filterCity, setFilterCity] = useState("");
  const [filterDistance, setFilterDistance] = useState(100);
  const [includeEstimatedNearby, setIncludeEstimatedNearby] = useState(false);
  const [activeFilterCount, setActiveFilterCount] = useState(0);

  // Pending filter states (applied on "Applica")
  const [pendingCats, setPendingCats] = useState([]);
  const [pendingRegion, setPendingRegion] = useState("");
  const [pendingCity, setPendingCity] = useState("");
  const [pendingDist, setPendingDist] = useState(100);

  // Settings
  const [locationMode, setLocationMode] = useState("none");
  const [manualCity, setManualCity] = useState("");

  // Map state
  const [hoveredPin, setHoveredPin] = useState(null);
  const mapRef = useRef(null);

  // Day headers stick right under the search bar, whatever its rendered height.
  const headerRef = useRef(null);
  useEffect(() => {
    const el = headerRef.current;
    if (!el || typeof ResizeObserver === 'undefined') return undefined;
    const observer = new ResizeObserver(() =>
      document.documentElement.style.setProperty('--header-h', el.offsetHeight + 'px'));
    observer.observe(el);
    return () => observer.disconnect();
  }, [tab, view]);

  // Bridge: use hook's categories/colors/icons, falling back to local constants
  const CATS = hookCategories.length > 0 ? hookCategories : CATEGORIES;
  const CAT_ICONS = Object.keys(hookCatIcons).length > 0 ? hookCatIcons : CATEGORY_ICONS;
  const CAT_COLORS = Object.keys(hookCatColors).length > 0 ? hookCatColors : CATEGORY_COLORS;
  const REGS = hookRegions.length > 0 ? hookRegions : REGIONS;
  const CTS = hookCities.length > 0 ? hookCities : CITIES;
  const canUseDistance = Number.isFinite(userLat) && Number.isFinite(userLng);

  const toggleFav = useCallback((id, e) => {
    if (e) e.stopPropagation();
    hookToggleFav(id);
  }, [hookToggleFav]);

  const openMarket = useCallback(async (market) => {
    setSelectedMarket(market);
    setDetailError('');
    setDetailLoading(true);
    try {
      const detailed = await getMarketDetails(market.id);
      setSelectedMarket(current => current?.id === market.id ? (detailed || market) : current);
    } catch (error) {
      setDetailError(error.message || 'Impossibile caricare i dettagli');
    } finally {
      setDetailLoading(false);
    }
  }, [getMarketDetails]);

  const showToast = useCallback((msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2000);
  }, []);

  // Details are shareable by URL hash: no server-side route required.
  useEffect(() => {
    const openHash = async () => {
      const hash = window.location.hash.replace(/^#/, '');
      const requested = new URLSearchParams(hash).get('mercato');
      // A link shared for a soft-merged copy opens its kept record.
      const id = requested && await canonicalId(requested);
      // A concluded market is not in the lists but its link still opens it.
      const item = id && (allMarkets.find(market => market.id === id)
        || await getMarketDetails(id).catch(() => null));
      if (item) openMarket(item);
    };
    openHash();
    window.addEventListener('hashchange', openHash);
    return () => window.removeEventListener('hashchange', openHash);
  }, [allMarkets, openMarket, canonicalId, getMarketDetails]);

  const closeMarket = () => {
    setSelectedMarket(null);
    if (window.location.hash.startsWith('#mercato=')) {
      window.history.replaceState(null, '', window.location.pathname + window.location.search);
    }
  };

  const shareMarket = async (market) => {
    const url = new URL(window.location.href);
    url.hash = 'mercato=' + encodeURIComponent(market.id);
    const payload = { title: market.name, text: market.city, url: url.toString() };
    try {
      if (navigator.share) {
        await navigator.share(payload);
      } else if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(payload.url);
        showToast('Link del mercato copiato.');
      } else {
        window.prompt('Copia questo link per condividerlo:', payload.url);
      }
    } catch (error) {
      if (error?.name !== 'AbortError') showToast('Condivisione non riuscita.');
    }
  };

  const openDirections = (market) => {
    // The search-index preview does not contain municipality source holds.
    // Directions must never be possible before full regional details arrive.
    if (detailLoading || detailError) {
      showToast('Indicazioni non disponibili finché i dettagli non sono verificati.');
      return;
    }
    const destination = destinationForMarket(market);
    if (!destination) {
      showToast('Indirizzo non abbastanza preciso per navigare.');
      return;
    }
    const url = 'https://www.google.com/maps/dir/?api=1&destination=' + encodeURIComponent(destination);
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const copyMarketAddress = async (market) => {
    if (!market.address?.trim()) {
      showToast('Indirizzo non disponibile.');
      return;
    }
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard not supported');
      await navigator.clipboard.writeText(market.address);
      showToast('Indirizzo copiato.');
    } catch {
      showToast('Seleziona il testo dell’indirizzo per copiarlo.');
    }
  };

  const activateNearby = () => {
    // Asking permission must not erase the visitor's current city/filter.
    // Activate nearby only AFTER the browser provides coordinates.
    setLocationMode('auto');
    if (!canUseDistance) requestPosition();
  };

  useEffect(() => {
    if (positionStatus === 'ready' && canUseDistance && locationMode === 'auto') {
      setFilterCity('');
      setFilterRegion('');
      setIncludeEstimatedNearby(false);
      setFilterDistance(50);
      setActiveFilterCount(1 + Number(filterCategories.length > 0));
      setSortBy('distanza');
    } else if (['denied', 'error', 'unavailable'].includes(positionStatus) && locationMode === 'auto') {
      // GPS denial is not an empty city search: keep all existing filters.
      setLocationMode('none');
    }
  }, [positionStatus, canUseDistance, locationMode]);

  const confirmManualCity = () => {
    const name = manualCity.trim().toLocaleLowerCase('it');
    const match = CTS.find(city => city.toLocaleLowerCase('it') === name);
    if (!match) {
      showToast('Scegli una città presente nel catalogo.');
      return;
    }
    clearPosition();
    setLocationMode('manual');
    setFilterCity(match);
    setFilterRegion('');
    setFilterDistance(100);
    setSortBy('data');
    setActiveFilterCount(1);
    setTab('esplora');
    setView('list');
    showToast('Filtra per città: ' + match);
  };

  const disableLocation = () => {
    clearPosition();
    setLocationMode('none');
    setFilterCity('');
    setFilterDistance(100);
    setActiveFilterCount(Number(filterCategories.length > 0) + Number(Boolean(filterRegion)));
    setSortBy('data');
  };

  // One tap on a category chip filters by that category alone; a second tap clears it.
  const setCategoryQuick = (cat) => {
    const next = filterCategories.length === 1 && filterCategories[0] === cat ? [] : [cat];
    setFilterCategories(next);
    setActiveFilterCount(Number(next.length > 0) + Number(Boolean(filterRegion)) +
      Number(Boolean(filterCity)) + Number(canUseDistance && filterDistance < 100));
  };

  // "Vedi tutti i mercati a <città>" from a card: every card of that town, any date.
  const showCity = (city) => {
    setFilterRegion('');
    setFilterCity(city);
    setSearchQuery('');
    setDateFilter(null);
    setDateFilterExplicit(true);
    setActiveFilterCount(1 + Number(filterCategories.length > 0));
    setTab('esplora');
    setViewMode('lista');
    setView('list');
    closeMarket();
    window.scrollTo(0, 0);
  };

  // Home -> list hand-offs (the list keeps today's filter engine).
  const cityForToday = useMemo(() => {
    if (filterCity) return filterCity;
    if (!canUseDistance) return '';
    const nearest = allMarkets
      .filter(m => Number.isFinite(m.distance) && m.distance <= 15 && m.positionQuality === 'precisa')
      .sort((a, b) => a.distance - b.distance)[0];
    return nearest ? nearest.city : '';
  }, [filterCity, canUseDistance, allMarkets]);
  const countFilters = (cats, region, city) => Number(cats.length > 0) + Number(Boolean(region)) +
    Number(Boolean(city)) + Number(canUseDistance && filterDistance < 100);
  const goHome = () => { setView('home'); window.scrollTo(0, 0); };
  const goList = () => { setView('list'); setViewMode('lista'); window.scrollTo(0, 0); };
  const homeQuery = (q) => { setSearchQuery(q); if (q.trim()) goList(); };
  const homeCategory = (cats) => {
    setEventsOnly(false);
    setFilterCategories(cats);
    setActiveFilterCount(countFilters(cats, filterRegion, filterCity));
    setDateFilter(cats.includes('Misto') ? '7giorni' : 'weekend');
    setDateFilterExplicit(true);
    goList();
  };
  const homeRegion = (name) => {
    setEventsOnly(true);
    setFilterRegion(name);
    setFilterCity('');
    setActiveFilterCount(countFilters(filterCategories, name, ''));
    setDateFilter('weekend');
    setDateFilterExplicit(true);
    goList();
  };
  const homeSeeAll = () => { setEventsOnly(true); setDateFilter('weekend'); setDateFilterExplicit(true); goList(); };
  // Where the home looks from: the visitor (GPS) or the chosen city (centre of its precise points).
  const homeCenter = useMemo(() => {
    if (canUseDistance) return { lat: userLat, lng: userLng, label: 'vicino a te' };
    if (!filterCity) return null;
    const points = allMarkets.filter(m => m.city === filterCity && Number.isFinite(m.lat) && Number.isFinite(m.lng));
    if (!points.length) return null;
    return { lat: points.reduce((sum, m) => sum + m.lat, 0) / points.length,
      lng: points.reduce((sum, m) => sum + m.lng, 0) / points.length, label: 'vicino a ' + filterCity };
  }, [canUseDistance, userLat, userLng, filterCity, allMarkets]);
  const openWeekly = (city) => { setWeeklyCity(city); setView('weekly'); window.scrollTo(0, 0); };
  const renderHome = () => (
    <Home markets={allMarkets} loading={marketsLoading} error={marketsError} onRetry={() => window.location.reload()}
      query={searchQuery} onQuery={homeQuery} weekendOffset={weekendOffset} onWeekend={setWeekendOffset}
      onSeeAll={homeSeeAll} onCategory={homeCategory} onRegion={homeRegion}
      onNearby={activateNearby} onAllItaly={disableLocation} positionStatus={positionStatus} canUseDistance={canUseDistance} center={homeCenter}
      cityForToday={cityForToday} onWeeklyCity={openWeekly} onChooseCity={() => setTab('impostazioni')}
      onOpen={openMarket} favorites={favorites} onToggleFav={toggleFav} />
  );

  // Use hook's markets (already have distances computed)
  const marketsWithDistance = allMarkets;

  // Render at most 60 cards initially on slow mobile browsers.
  useEffect(() => setVisibleCount(60), [searchQuery, activeDateFilter, weekdayFilter, filterCategories, filterRegion, filterCity, filterDistance, sortBy, canUseDistance, includeEstimatedNearby, weekdayFilter]);

  // Apply filters
  const filteredMarkets = useMemo(() => {
    let result = [...marketsWithDistance];

    // Search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(m =>
        m.name.toLowerCase().includes(q) ||
        m.city.toLowerCase().includes(q) ||
        m.category.toLowerCase().includes(q) ||
        m.tags.some(t => t.toLowerCase().includes(q))
      );
    }

    if (eventsOnly) result = result.filter(m => m.isEvent);

    // Date filter
    if (activeDateFilter === "oggi") {
      result = result.filter(m => m.dates.includes(todayStr));
    } else if (activeDateFilter === "weekend") {
      const weekend = weekendOf(TODAY, weekendOffset);
      result = result.filter(m => inWeekend(m.dates, weekend));
    } else if (activeDateFilter === "7giorni") {
      const end = new Date(TODAY); end.setDate(end.getDate() + 7);
      const endStr = localISO(end);
      result = result.filter(m => m.dates.some(d => d >= todayStr && d <= endStr));
    }

    // A day-of-week filter is applied to individual source appointments BEFORE
    // aggregating their city/venue display. It never alters the stored records.
    if (weekdayFilter !== null) {
      result = result.filter(m => (m.dates || []).some(
        d => d >= todayStr && weekdayFromISO(d) === weekdayFilter
      ));
    }

    // Category filter
    if (filterCategories.length > 0) {
      result = result.filter(m => filterCategories.includes(m.category));
    }

    // Region
    if (filterRegion) {
      result = result.filter(m => m.region === filterRegion);
    }

    // City
    if (filterCity) {
      result = result.filter(m => m.city === filterCity);
    }

    // Distance
    if (canUseDistance && filterDistance < 100) {
      result = result.filter(m =>
        Number.isFinite(m.distance) &&
        m.distance <= filterDistance &&
        (includeEstimatedNearby || m.positionQuality === 'precisa')
      );
    }

    // Sort
    if (sortBy === "distanza" && canUseDistance) {
      const priority = (market) => market.positionQuality === 'precisa'
        ? 0 : market.positionQuality === 'approssimata' ? 1 : 2;
      result.sort((a, b) => priority(a) - priority(b) ||
        (a.distance ?? Infinity) - (b.distance ?? Infinity));
    } else {
      // Same-day markets should not default to an accidental alphabetical
      // order by region (Abruzzo -> Veneto). Prefer more useful records.
      const rank = market =>
        (market.dateQuality === 'confermata' ? 50 : 0) +
        (market.positionQuality === 'precisa' ? 9 : 0) +
        (market.hours ? 5 : 0) +
        (market.category !== 'Misto' ? 3 : 0);
      result.sort((a, b) => {
        const aDate = getNextDate(a.dates);
        const bDate = getNextDate(b.dates);
        return (aDate || '9999').localeCompare(bDate || '9999') ||
          rank(b) - rank(a) ||
          a.name.localeCompare(b.name, 'it');
      });
    }

    return result;
  }, [marketsWithDistance, searchQuery, activeDateFilter, weekdayFilter, filterCategories, filterRegion, filterCity, filterDistance, sortBy, canUseDistance, includeEstimatedNearby, weekendOffset, eventsOnly]);

  // Group generic city-wide weekly listings only for presentation. The
  // map and the underlying dataset retain every individually sourced record.
  const groupedList = useMemo(() => displayEntries(filteredMarkets, {
    keepSingleWeeklyGroups: weekdayFilter !== null,
  }), [filteredMarkets, weekdayFilter]);

  const openFilters = () => {
    setPendingCats([...filterCategories]);
    setPendingRegion(filterRegion);
    setPendingCity(filterCity);
    setPendingDist(filterDistance);
    setShowFilters(true);
  };

  const applyFilters = () => {
    setFilterCategories(pendingCats);
    setFilterRegion(pendingRegion);
    setFilterCity(pendingCity);
    setFilterDistance(canUseDistance ? pendingDist : 100);
    let count = 0;
    if (pendingCats.length > 0) count++;
    if (pendingRegion) count++;
    if (pendingCity) count++;
    if (canUseDistance && pendingDist < 100) count++;
    setActiveFilterCount(count);
    setShowFilters(false);
  };

  const resetFilters = () => {
    setPendingCats([]);
    setPendingRegion("");
    setPendingCity("");
    setPendingDist(100);
    setFilterCategories([]);
    setFilterRegion("");
    setFilterCity("");
    setFilterDistance(100);
    setActiveFilterCount(0);
    setIncludeEstimatedNearby(false);
    setShowFilters(false);
  };

  const resetAllFilters = () => {
    setEventsOnly(false);
    setFilterCategories([]);
    setFilterRegion("");
    setFilterCity("");
    setFilterDistance(100);
    setIncludeEstimatedNearby(false);
    setActiveFilterCount(0);
    setDateFilter(null);
    setDateFilterExplicit(false);
    setWeekdayFilter(null);
    setSearchQuery("");
  };

  // ─── Map projection (Italy bounds) ────────────
  const mapProject = useCallback((lat, lng, w, h) => {
    const minLat = 36.5, maxLat = 47.5, minLng = 6.5, maxLng = 19.5;
    const x = ((lng - minLng) / (maxLng - minLng)) * w;
    const y = ((maxLat - lat) / (maxLat - minLat)) * h;
    return { x, y };
  }, []);

  // ─── Render Functions ─────────────────────────

  const renderList = () => (
    <List
      headerRef={headerRef} query={searchQuery} onQuery={setSearchQuery} onHome={goHome}
      loading={marketsLoading} error={marketsError}
      filteredMarkets={filteredMarkets} groupedList={groupedList} visibleCount={visibleCount}
      onMore={() => setVisibleCount(n => n + 60)}
      activeDateFilter={activeDateFilter}
      onDateFilter={key => { setDateFilter(activeDateFilter === key ? null : key); setDateFilterExplicit(true); }}
      weekdayFilter={weekdayFilter}
      onWeekday={i => { setWeekdayFilter(v => v === i ? null : i); if (weekdayFilter !== i) setDateFilter('7giorni'); }}
      onClearWeekday={() => setWeekdayFilter(null)}
      filterCity={filterCity} filterRegion={filterRegion} filterCategories={filterCategories}
      onRemoveCity={() => { setFilterCity(''); setActiveFilterCount(Math.max(0, activeFilterCount - 1)); }}
      onRemoveRegion={() => { setFilterRegion(''); setActiveFilterCount(Math.max(0, activeFilterCount - 1)); }}
      onRemoveCategories={() => { setFilterCategories([]); setActiveFilterCount(Math.max(0, activeFilterCount - 1)); }}
      onResetAll={resetAllFilters} activeFilterCount={activeFilterCount} onOpenFilters={openFilters}
      canUseDistance={canUseDistance} filterDistance={filterDistance} includeEstimatedNearby={includeEstimatedNearby}
      onToggleEstimated={() => setIncludeEstimatedNearby(prev => !prev)}
      positionStatus={positionStatus} positionError={positionError} onNearby={activateNearby}
      sortBy={sortBy} onSort={setSortBy} showSort={showSort} setShowSort={setShowSort}
      viewMode={viewMode} setViewMode={setViewMode}
      userLat={userLat} userLng={userLng}
      favorites={favorites} onToggleFav={toggleFav} onOpen={openMarket}
      getMarketDetails={getMarketDetails} dataMode={dataMode}
      eventsOnly={eventsOnly} onToggleEventsOnly={() => setEventsOnly(v => !v)}
    />
  );

  const renderWeekly = () => (
    <Weekly city={weeklyCity} markets={allMarkets} onOpen={openMarket} onBack={goHome} />
  );

  const renderFilterSheet = () => (
    <FilterSheet onClose={() => setShowFilters(false)} cats={CATS} catColors={CAT_COLORS}
      pendingCats={pendingCats} setPendingCats={setPendingCats}
      regions={REGS} pendingRegion={pendingRegion} setPendingRegion={setPendingRegion}
      cities={CTS.filter(c => !pendingRegion || allMarkets.find(m => m.city === c)?.region === pendingRegion)}
      pendingCity={pendingCity} setPendingCity={setPendingCity}
      pendingDist={pendingDist} setPendingDist={setPendingDist} canUseDistance={canUseDistance}
      onReset={resetFilters} onApply={applyFilters} />
  );

  const renderFavorites = () => {
    const favMarkets = marketsWithDistance.filter(m => favorites.has(m.id));
    return (
      <>
        <div className="header">
          <div className="header-title">Preferiti</div>
        </div>
        <div className="page-content">
          {favMarkets.length > 0 ? (
            <div className="markets-list" style={{ padding: 0 }}>
              {favMarkets.map(m => <EventRow key={m.id} market={m} when="" onOpen={openMarket} onToggleFav={toggleFav} isFav={favorites.has(m.id)} />)}
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">❤️</div>
              <div className="empty-title">Nessun preferito</div>
              <div className="empty-text">Salva i mercati che ti interessano per ritrovarli qui.</div>
            </div>
          )}
        </div>
      </>
    );
  };

  const renderNotifications = () => {
    const savedMarkets = marketsWithDistance.filter(market => favorites.has(market.id));
    const scheduled = savedMarkets
      .map(market => ({ market, next: getNextDate(market.dates) }))
      .filter(item => item.next)
      .sort((left, right) => left.next.localeCompare(right.next))
      .slice(0, 30);
    const missingDates = savedMarkets.filter(market => !getNextDate(market.dates));

    return (
      <>
        <div className="header">
          <div className="header-title">Agenda preferiti</div>
        </div>
        <div className="page-content">
          <div className="setting-card">
            <div className="setting-label">I prossimi mercati che hai salvato</div>
            <div className="setting-sublabel">
              Qui trovi le date disponibili. Le notifiche push automatiche non sono ancora attive.
              Controlla sempre se la data è confermata prima di partire.
            </div>
          </div>
          {savedMarkets.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">♡</div>
              <div className="empty-title">Nessun mercato salvato</div>
              <div className="empty-text">Salva un mercato dalla ricerca per vederlo qui.</div>
              <button className="btn-primary" style={{ padding: '10px 20px', marginTop: 12 }}
                onClick={() => setTab('esplora')}>Cerca mercati</button>
            </div>
          ) : (
            <>
              {scheduled.length > 0 ? (
                <div className="markets-list" style={{ padding: 0 }}>
                  {scheduled.map(({ market, next }, index) => (
                    <button key={market.id} className="setting-card" style={{
                      display: 'flex', width: '100%', textAlign: 'left', gap: 12,
                      alignItems: 'center', cursor: 'pointer', border: 'none',
                    }} onClick={() => openMarket(market)}>
                      <span style={{ minWidth: 85, fontWeight: 700 }}>{formatDateIT(next)}</span>
                      <span style={{ flex: 1 }}>
                        <strong>{market.name}</strong>
                        <span style={{ display: 'block', fontSize: 12, opacity: 0.75 }}>
                          {market.city} · {market.dateQuality === 'confermata' ? 'Confermata'
                            : market.dateQuality === 'riportata' ? 'Riportata dalla fonte' : 'Prevista, da verificare'}
                        </span>
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="setting-card">Nessuna data futura disponibile per i tuoi preferiti.</div>
              )}
              {missingDates.length > 0 && (
                <div className="setting-card" style={{ marginTop: 12 }}>
                  <div className="setting-label">{missingDates.length} preferiti senza prossima data</div>
                  <div className="setting-sublabel">Li trovi nella sezione Preferiti. Verifica la fonte ufficiale.</div>
                </div>
              )}
            </>
          )}
        </div>
      </>
    );
  };

  const renderSettings = () => (
    <>
      <div className="header">
        <div className="header-title">Impostazioni</div>
      </div>
      <div className="page-content">
        <div className="setting-card">
          <div className="setting-label" style={{ marginBottom: 4 }}>Posizione</div>
          <div className="setting-sublabel">Scegli come trovare i mercati vicino a te</div>
          <div className="location-options">
            <button
              className={`location-option ${locationMode === 'auto' ? 'active' : ''}`}
              onClick={activateNearby}
            >
              <div className="icon-circle"><Icon name="compass" size={18} /></div>
              <div>
                <div style={{ fontWeight: 600 }}>Usa la mia posizione</div>
                <div style={{ fontSize: 12, color: '#6C6255', marginTop: 1 }}>
                  {positionStatus === 'ready' ? 'Posizione attiva' :
                   positionStatus === 'requesting' ? 'Richiesta in corso…' : 'Richiede il tuo consenso'}
                </div>
              </div>
            </button>
            <button
              className={`location-option ${locationMode === 'manual' ? 'active' : ''}`}
              onClick={() => setLocationMode('manual')}
            >
              <div className="icon-circle"><Icon name="mapPin" size={18} /></div>
              <div>
                <div style={{ fontWeight: 600 }}>Scegli una città</div>
                <div style={{ fontSize: 12, color: '#6C6255', marginTop: 1 }}>Inserisci manualmente</div>
              </div>
            </button>
            <button
              className={`location-option ${locationMode === 'none' ? 'active' : ''}`}
              onClick={disableLocation}
            >
              <div className="icon-circle"><Icon name="x" size={18} /></div>
              <div>
                <div style={{ fontWeight: 600 }}>Non ora</div>
                <div style={{ fontSize: 12, color: '#6C6255', marginTop: 1 }}>Naviga senza posizione</div>
              </div>
            </button>
          </div>

          {positionError && <div role="alert" className="setting-sublabel" style={{ marginTop: 12 }}>{positionError}</div>}
          {canUseDistance && (
            <div className="setting-sublabel" style={{ marginTop: 10 }}>
              Distanze calcolate rispetto alla tua posizione. Alcuni mercati hanno solo coordinate indicative.
            </div>
          )}
          {locationMode === 'manual' && (
            <>
              <div className="manual-city-input">
                <input list="available-market-cities" placeholder="Es. Firenze" value={manualCity}
                  onChange={e => setManualCity(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') confirmManualCity(); }} />
                <datalist id="available-market-cities">
                  {CTS.map(city => <option key={city} value={city} />)}
                </datalist>
                <button onClick={confirmManualCity}>Filtra città</button>
              </div>
              <div className="setting-sublabel">
                La città selezionata filtra i risultati. Non equivale alla posizione GPS.
              </div>
            </>
          )}
        </div>

        <div className="app-version">
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 16, marginBottom: 4 }}>
            <span style={{ color: 'var(--terracotta)' }}>Fuori</span> · Mercatini d'Italia
          </div>
          Versione 1.2 · Catalogo statico (lettura gratuita)
        </div>
      </div>
    </>
  );

  return (
    <>
      <div className="app-container" onClick={() => showSort && setShowSort(false)}>
        {tab === "esplora" && (view === "home" ? renderHome() : view === "weekly" ? renderWeekly() : renderList())}
        {tab === "mappa" && renderList()}
        {tab === "preferiti" && renderFavorites()}
        {tab === "notifiche" && renderNotifications()}
        {tab === "impostazioni" && renderSettings()}

        {showFilters && renderFilterSheet()}
        {selectedMarket && (
          <Detail market={selectedMarket} loading={detailLoading} error={detailError} allMarkets={allMarkets}
            favorites={favorites} onToggleFav={toggleFav} onBack={closeMarket} onShare={shareMarket}
            onDirections={openDirections} onCopyAddress={copyMarketAddress} onOpen={openMarket}
            onShowCity={showCity} onShowRegion={region => { closeMarket(); homeRegion(region); }} />
        )}
        {toast && <div className="toast">{toast}</div>}

        <nav className="bottom-tabs">
          {[
            { id: "esplora", label: "Esplora", icon: "compass" },
            { id: "preferiti", label: "Preferiti", icon: "heart" },
            { id: "notifiche", label: "Agenda", icon: "calendar" },
            { id: "impostazioni", label: "Impostazioni", icon: "settings" },
          ].map(t => (
            <button key={t.id} className={`tab-btn ${tab === t.id ? 'active' : ''}`}
              onClick={() => { setTab(t.id); if (t.id === 'esplora') { setViewMode('lista'); setView('home'); } }}>
              <Icon name={t.icon} size={22} strokeWidth={tab === t.id ? 2 : 1.6} />
              {t.label}
            </button>
          ))}
        </nav>
      </div>
    </>
  );
}
