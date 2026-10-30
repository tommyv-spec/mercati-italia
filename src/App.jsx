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
import { weekendOf, inWeekend } from './lib/weekend.js';
import Icon from './ui/Icon.jsx';
import { CATEGORY_COLORS, localISO, TODAY, todayStr, formatDateIT, getDateBadge, dateQualityLabel, dateLeaf, dayHeaderLabel, getNextDate, uniqueByName } from './lib/display.js';
import { downloadCalendarEvent } from './lib/calendarFile.js';
import { reportUrl } from './lib/report.js';
import { haversine } from './services/staticMarkets.js';
const MarketsMap = lazy(() => import('./components/MarketsMap.jsx'));

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
  }, [tab]);

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
    setFilterCategories(cats);
    setActiveFilterCount(countFilters(cats, filterRegion, filterCity));
    setDateFilter(cats.includes('Misto') ? '7giorni' : 'weekend');
    setDateFilterExplicit(true);
    goList();
  };
  const homeRegion = (name) => {
    setFilterRegion(name);
    setFilterCity('');
    setActiveFilterCount(countFilters(filterCategories, name, ''));
    setDateFilter('weekend');
    setDateFilterExplicit(true);
    goList();
  };
  const homeSeeAll = () => { setDateFilter('weekend'); setDateFilterExplicit(true); goList(); };
  const renderHome = () => (
    <Home markets={allMarkets} loading={marketsLoading} error={marketsError} onRetry={() => window.location.reload()}
      query={searchQuery} onQuery={homeQuery} weekendOffset={weekendOffset} onWeekend={setWeekendOffset}
      onSeeAll={homeSeeAll} onCategory={homeCategory} onRegion={homeRegion}
      onNearby={activateNearby} onAllItaly={disableLocation} positionStatus={positionStatus} canUseDistance={canUseDistance}
      cityForToday={cityForToday} onWeeklyCity={showCity} onChooseCity={() => setTab('impostazioni')}
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
  }, [marketsWithDistance, searchQuery, activeDateFilter, weekdayFilter, filterCategories, filterRegion, filterCity, filterDistance, sortBy, canUseDistance, includeEstimatedNearby, weekendOffset]);

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

  const renderMarketCard = (market, index) => {
    const badge = getDateBadge(market.dates);
    const nextDate = getNextDate(market.dates);
    const leaf = dateLeaf(nextDate);
    const catColor = CAT_COLORS[market.category] || "#888";
    const isFav = favorites.has(market.id);

    return (
      <div
        key={market.id}
        className="market-card"
        style={{ animationDelay: `${Math.min(index, 12) * 50}ms`, '--cat-color': catColor }}
      >
        <button type="button" className="market-card-open"
          aria-label={'Apri i dettagli di ' + market.name + ', ' + market.city}
          onClick={() => openMarket(market)} />
        <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 4, background: catColor, borderRadius: '4px 0 0 4px' }} />
        <div className="card-row">
          <div className={`card-date ${badge ? badge.tone : ''}`}>
            <span className="card-date-day">{leaf.day}</span>
            <span className="card-date-month">{leaf.month}</span>
          </div>
          <div className="card-main">
            <div className="card-eyebrow">
              <span className="card-city">{market.city}</span>
              {market.region && <span> · {market.region}</span>}
            </div>
            <div className="card-name">{market.name}</div>
            <div className="card-info">
              <span className="card-info-item card-hours">
                <Icon name="clock" size={14} color="#6C6255" />
                {sourceHoursForDate(market, nextDate)}
              </span>
              <span className="card-info-item" style={{ color: catColor, fontWeight: 600 }}>
                <span aria-hidden="true">{CAT_ICONS[market.category]}</span> {market.category}
              </span>
              {canUseDistance && (
                <span className="card-info-item card-distance">
                  {market.positionQuality === 'precisa' && Number.isFinite(market.distance)
                    ? (market.distance < 1 ? 'a meno di 1 km' : 'a ' + Math.round(market.distance) + ' km')
                    : market.positionQuality === 'approssimata' && Number.isFinite(market.distance)
                      ? (market.distance < 1 ? 'meno di 1 km (stimati)'
                        : 'circa ' + Math.round(market.distance) + ' km (stimati)')
                      : 'Posizione da verificare'}
                </span>
              )}
            </div>
            <div className="card-status">
              {badge && <span className={badge.tone}>{badge.label} · </span>}
              <span className={market.dateQuality === 'confermata' ? 'confirmed' : ''}>
                {nextDate ? dateQualityLabel(market.dateQuality) : 'Data da verificare'}
              </span>
            </div>
          </div>
          <button
            className={`fav-btn ${isFav ? 'active' : ''}`}
            onClick={(e) => toggleFav(market.id, e)}
            aria-label={isFav ? "Rimuovi dai preferiti" : "Aggiungi ai preferiti"}
          >
            <Icon name={isFav ? "heartFilled" : "heart"} size={20} />
          </button>
        </div>
      </div>
    );
  };

  const renderMapView = () => (
    <Suspense fallback={<div role="status" style={{
      margin: '22px 18px 110px', padding: 22, background: 'var(--white)',
      borderRadius: 12, color: 'var(--ink-lighter)' }}>Caricamento mappa interattiva…</div>}>
      <MarketsMap markets={filteredMarkets} userLat={userLat} userLng={userLng}
        onSelect={openMarket} />
    </Suspense>
  );

  const renderDetail = () => {
    if (!selectedMarket) return null;
    const m = selectedMarket;
    const catColor = CAT_COLORS[m.category] || "#888";
    const isFav = favorites.has(m.id);
    const futureDates = m.dates.filter(d => d >= todayStr).sort();
    const nextDate = futureDates[0] || null;
    const nextBadge = getDateBadge(m.dates);
    // Other cards within 30 km with a date in the next seven days, nearest first.
    const weekAhead = (() => { const d = new Date(TODAY); d.setDate(d.getDate() + 7); return localISO(d); })();
    const nearby = Number.isFinite(m.lat) && Number.isFinite(m.lng) ? uniqueByName(allMarkets
      .filter(x => x.id !== m.id && Number.isFinite(x.lat) && Number.isFinite(x.lng) &&
        x.dates.some(d => d >= todayStr && d <= weekAhead))
      .map(x => ({ market: x, km: haversine(m.lat, m.lng, x.lat, x.lng) }))
      .filter(x => x.km <= 30).sort((a, b) => a.km - b.km), item => item.market).slice(0, 4) : [];
    const sameCity = m.locationReviewRequired ? [] : uniqueByName(allMarkets
      .filter(x => x.id !== m.id && x.city === m.city && !x.locationReviewRequired &&
        italianKey(x.name) !== italianKey(m.name))
      .sort((a, b) => (getNextDate(a.dates) || '9999').localeCompare(getNextDate(b.dates) || '9999')));
    const canNavigate = !detailLoading && !detailError && Boolean(destinationForMarket(m));
    const sourceSchedule = sourceCalendarView(m);
    const summary = editorialSummaryView(m);
    const editorial = summary.evidence;
    const contacts = mergeContacts(sourceContacts(m.sourceDetail), editorialContacts(m));
    const addressConflicts = addressConflictView(m);

    return (
      <div className="detail-page">
        <div className="detail-hero" style={{ background: `linear-gradient(135deg, ${catColor}08 0%, ${catColor}14 100%)` }}>
          <div style={{ position: 'absolute', top: -40, right: -40, width: 180, height: 180, borderRadius: '50%', background: catColor, opacity: 0.04 }} />
          <button className="detail-back" onClick={closeMarket}>
            <Icon name="chevronLeft" size={20} />
          </button>
          <div className="detail-actions-top">
            <button className="detail-icon-btn" onClick={() => shareMarket(m)} aria-label="Condividi questo mercato">
              <Icon name="share" size={18} />
            </button>
            <button
              className={`detail-icon-btn ${isFav ? 'fav-active' : ''}`}
              onClick={() => toggleFav(m.id)}
            >
              <Icon name={isFav ? "heartFilled" : "heart"} size={18} />
            </button>
          </div>

          <span className="detail-category-tag" style={{ background: catColor + '18', color: catColor }}>
            {CAT_ICONS[m.category]} {m.category}
          </span>
          <div className="detail-name">{m.name}</div>
          {detailLoading && <div style={{ fontSize: 12, marginTop: 8 }}>Caricamento dettagli completi…</div>}
          {detailError && <div role="alert" style={{ fontSize: 12, marginTop: 8 }}>
            {detailError}. Sono visibili i dati sintetici.
          </div>}

          <div className="detail-city">
            <Icon name="mapPin" size={14} color={catColor} strokeWidth={2} /> {m.city}, {m.region}
          </div>
          {(summary.recurrence || summary.hours) && (
            <div className="detail-lead">
              {[summary.recurrence, summary.hours].filter(Boolean).join(' · ')}
            </div>
          )}
        </div>

        <div className="detail-body">
          {/* Next date first; the full list of predicted dates is folded away */}
          <div className="detail-section" style={{ animationDelay: '0.05s' }}>
            <div className="detail-section-title">
              <Icon name="calendar" size={18} color={catColor} /> Prossima apertura
            </div>
            {nextDate ? (
              <div className="detail-next">
                <div className={`card-date ${nextBadge ? nextBadge.tone : ''}`}>
                  <span className="card-date-day">{dateLeaf(nextDate).day}</span>
                  <span className="card-date-month">{dateLeaf(nextDate).month}</span>
                </div>
                <div>
                  <div className="detail-next-label">{dayHeaderLabel(nextDate)}</div>
                  <div className="detail-next-sub">
                    {sourceHoursForDate(m, nextDate)} · {dateQualityLabel(m.dateQuality)}
                  </div>
                </div>
              </div>
            ) : <span className="date-chip">Date da verificare</span>}
            {futureDates.length > 1 && (
              <details className="source-calendar">
                <summary>Tutte le date previste ({futureDates.length})</summary>
                <div className="detail-dates-chips">
                  {futureDates.map(d => {
                    const isToday = d === todayStr;
                    const dayOfWeek = new Date(d + "T00:00:00").getDay();
                    const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
                    return (
                      <span key={d} className={`date-chip ${isToday ? 'today' : isWeekend ? 'weekend' : ''}`}
                        title={sourceHoursForDate(m, d)}>
                        {formatDateIT(d)}
                      </span>
                    );
                  })}
                </div>
              </details>
            )}
            {marketDateDisclosure(m.dates, m.dateQuality) && (
              <div style={{ fontSize: 12, color: '#6C6255', marginTop: 8 }}>
                {marketDateDisclosure(m.dates, m.dateQuality)}
              </div>
            )}
            <div className="detail-address-actions" style={{ marginTop: 14 }}>
              <button className={isFav ? 'btn-primary' : 'btn-secondary'} onClick={() => toggleFav(m.id)}>
                <Icon name={isFav ? 'heartFilled' : 'heart'} size={16} color={isFav ? 'white' : 'currentColor'} />
                {isFav ? 'In Agenda' : 'Salva in Agenda'}
              </button>
              {nextDate && (
                <button className="btn-secondary"
                  onClick={() => downloadCalendarEvent(m, nextDate, sourceHoursForDate(m, nextDate))}>
                  <Icon name="calendar" size={16} /> Aggiungi al calendario
                </button>
              )}
            </div>
          </div>

          {/* Hours */}
          <div className="detail-section" style={{ animationDelay: '0.1s' }}>
            <div className="detail-section-title">
              <Icon name="clock" size={18} color={catColor} /> Orari
            </div>
            <div className="detail-hours" style={summary.hours.length > 100 ? { fontSize: 15 } : undefined}>
              {summary.hours || (sourceSchedule.rows.length ? 'Vedi gli orari delle singole date' : 'Orari non disponibili')}
            </div>
            {sourceSchedule.notes.map((note, i) => (
              <p key={note + i} className="source-calendar-note">{note}</p>
            ))}
            {m.stalls && <p className="source-calendar-note" data-stalls>Circa {m.stalls} banchi secondo la fonte.</p>}
            {m.entry && <p className="source-calendar-note" data-entry>Ingresso: {m.entry}</p>}
            {m.tips && <p className="source-calendar-note" data-tips>Consiglio: {m.tips}</p>}
            {sourceSchedule.rows.length > 0 && (
              <details className="source-calendar" key={m.id}
                open={sourceSchedule.hasVariations || sourceSchedule.rows.length <= 3}>
                <summary>Date e orari riportati dalla fonte ({sourceSchedule.rows.length})</summary>
                <dl>
                  {sourceSchedule.rows.map(row => (
                    <div key={row.key} className="source-calendar-row" data-period={row.kind === 'interval'}>
                      <dt>{row.label}</dt>
                      <dd>
                        {row.status && <strong>{row.status}{row.hours ? ' · ' : ''}</strong>}
                        {row.hours}
                        {row.note && <p className="source-calendar-note">{row.note}</p>}
                      </dd>
                    </div>
                  ))}
                </dl>
              </details>
            )}
          </div>

          {editorial && (
            <div className="detail-section">
              <div className="detail-section-title">
                <Icon name="info" size={18} color={catColor} /> {editorial.title}
              </div>
              {editorial.notes.map((note, i) => (
                <p key={note + i} className="source-calendar-note">{note}</p>
              ))}
              {editorial.hours && <p className="detail-description">
                <strong>{editorial.hoursLabel}:</strong> {editorial.hours}
              </p>}
              {editorial.recurrence && <p className="source-calendar-note">
                Cadenza descritta nella pagina: {editorial.recurrence}
              </p>}
              {editorial.rows.length > 0 && (
                <details className="source-calendar" key={m.id + '/editorial'} open={editorial.rows.length <= 3}>
                  <summary>Date e periodi descritti nella pagina ({editorial.rows.length})</summary>
                  <dl>
                    {editorial.rows.map(row => (
                      <div key={row.key} className="source-calendar-row" data-period={row.kind === 'interval'}>
                        <dt>{row.label}</dt>
                        <dd>
                          <strong>{row.status}{row.hours ? ' · ' : ''}</strong>{row.hours}
                          {row.note && <p className="source-calendar-note">{row.note}</p>}
                        </dd>
                      </div>
                    ))}
                  </dl>
                </details>
              )}
              <p className="source-calendar-note">
                <a href={editorial.sourceUrl} target="_blank" rel="noopener noreferrer">{editorial.sourceName}</a>
                {' · pagina letta il ' + editorial.readOn}<br />
                {editorial.editorialDate}
              </p>
            </div>
          )}

          {/* Address */}
          <div className="detail-section" style={{ animationDelay: '0.15s' }}>
            <div className="detail-section-title">
              <Icon name="mapPin" size={18} color={catColor} /> Indirizzo
            </div>
            {addressConflicts.length > 0 && <p className="source-calendar-note">
              Indirizzo salvato, discordante con la fonte
            </p>}
            <div className="detail-address">{m.address || 'Indirizzo non verificato'}</div>
            {addressConflicts.map(conflict => (
              <div className="detail-address-conflict" role="note" key={conflict.key}>
                <p className="detail-description">
                  La fonte indica invece: <strong>{conflict.sourceAddress}</strong>.
                </p>
                <p className="source-calendar-note">
                  <a href={conflict.sourceUrl} target="_blank" rel="noopener noreferrer">Happings</a>
                  {' · pagina letta il ' + conflict.readOnLabel}
                </p>
              </div>
            ))}
            {m.locationReviewRequired && (
              <p role="note" style={{ color: '#857660', fontSize: 12, lineHeight: 1.5, margin: '9px 0' }}>
                {m.cityUncertain ? UNKNOWN_CITY_HELP : VENUE_UNCONFIRMED_HELP} Le indicazioni stradali per questa scheda sono disabilitate.
              </p>
            )}
            {m.concluded && (
              <p role="note" style={{ color: '#857660', fontSize: 12, lineHeight: 1.5, margin: '9px 0' }}>
                Non più in programma: la fonte non indica nuove date.
              </p>
            )}
            {m.positionQuality !== 'precisa' && (
              <div style={{ fontSize: 12, color: '#6C6255', marginTop: 6 }}>
                {m.positionFromOsm ? <>
                  Posizione indicativa: la via, non il punto esatto del mercato ·{' '}
                  <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noopener noreferrer">© OpenStreetMap contributors</a>
                </> : 'Posizione indicativa o da verificare'}
              </div>
            )}
            {!canNavigate && !detailLoading && (
              <div role="note" style={{ fontSize: 12, color: '#6C6255', margin: '10px 0' }}>
                {addressConflicts.length > 0
                  ? 'Indicazioni sospese: l’indirizzo salvato è discordante con la fonte.'
                  : 'Indicazioni non disponibili: manca una sede riconciliata e verificabile.'}
              </div>
            )}
            <div className="detail-address-actions">
              <button className="btn-primary" onClick={() => openDirections(m)}
                disabled={!canNavigate}
                title={!canNavigate ? 'Dettagli o sede non sufficienti per navigare' : 'Apri indicazioni stradali'}>
                <Icon name="navigation" size={16} color="white" /> Indicazioni
              </button>
              <button className="btn-secondary" onClick={() => copyMarketAddress(m)}
                disabled={!m.address?.trim()}
                title={addressConflicts.length > 0 ? 'Copia l’indirizzo salvato, segnalato come discordante' : 'Copia indirizzo'}>
                <Icon name="copy" size={16} /> Copia
              </button>
            </div>
          </div>

          {nearby.length > 0 && (
            <div className="detail-section" style={{ animationDelay: '0.18s' }}>
              <div className="detail-section-title">
                <Icon name="compass" size={18} color={catColor} /> Nei prossimi 7 giorni, qui vicino
              </div>
              {nearby.map(({ market, km }) => (
                <button type="button" className="link-row" key={market.id} onClick={() => openMarket(market)}>
                  <span className="link-row-date">{formatDateIT(getNextDate(market.dates))}</span>
                  <span className="link-row-main">
                    {market.name}
                    <small>{market.city} · circa {Math.max(1, Math.round(km))} km</small>
                  </span>
                  <span className="link-row-arrow" aria-hidden="true">›</span>
                </button>
              ))}
              <p className="source-calendar-note">
                Distanze indicative tra i punti sulla mappa, non tra gli ingressi dei mercati.
              </p>
            </div>
          )}

          {/* Description */}
          {m.description && (
            <div className="detail-section" style={{ animationDelay: '0.2s' }}>
              <div className="detail-section-title">
                <Icon name="info" size={18} color={catColor} /> Descrizione
              </div>
              <div className="detail-description">{m.description}</div>
            </div>
          )}

          {/* Tags */}
          {(contacts.organizer || contacts.links.length > 0) && (
            <div className="detail-section">
              <div className="detail-section-title">
                <Icon name="info" size={18} color={catColor} /> Contatti riportati dalla fonte
              </div>
              {contacts.organizer && <p className="detail-description">
                Organizzatore:{' '}
                {contacts.organizer.href
                  ? <a href={contacts.organizer.href} target="_blank" rel="noopener noreferrer">{contacts.organizer.label}</a>
                  : contacts.organizer.label}
              </p>}
              {contacts.links.map((contact, i) => (
                <p key={contact.href + i} className="detail-description" style={{ marginTop: 6, overflowWrap: 'anywhere' }}>
                  <a href={contact.href} target="_blank" rel="noopener noreferrer">{contact.label}</a>
                </p>
              ))}
            </div>
          )}

          {m.tags && m.tags.length > 0 && (
            <div className="detail-section" style={{ animationDelay: '0.25s' }}>
              <div className="detail-section-title">Tag</div>
              <div className="detail-tags">
                {m.tags.map(t => (
                  <span key={t} className="detail-tag">{t}</span>
                ))}
              </div>
            </div>
          )}

          {/* Provenance */}
          <div className="detail-section" style={{ animationDelay: '0.3s' }}>
            <div className="detail-provenance">
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, marginBottom: 2 }}>
                  {m.lastVerified ? 'Verificato il ' + m.lastVerified : 'Verifica individuale non documentata'}
                </div>
                <div style={{ fontSize: 12, opacity: 0.7 }}>
                  Fonte: {m.source || 'non disponibile'}
                  {m.sourceUpdated ? (m.sourceUpdateScope === 'dataset'
                    ? ' · dataset aggiornato il ' + m.sourceUpdated + ' (non verifica del singolo mercato)'
                    : ' · data dichiarata dalla fonte: ' + m.sourceUpdated) : ''}
                </div>
                {m.sourceUrl && (
                  <a href={m.sourceUrl} target="_blank" rel="noopener noreferrer"
                     style={{ display: 'inline-block', fontSize: 12, marginTop: 5 }}>
                    Controlla la fonte originale
                  </a>
                )}
                {(m.sourceEvidence || []).filter(s => s.url !== m.sourceUrl).slice(0, 3).map((s, i) => (
                  <div key={s.url + i} style={{ fontSize: 12, marginTop: 5, lineHeight: 1.4 }}>
                    Fonte aggiuntiva:{' '}
                    <a href={s.url} target="_blank" rel="noopener noreferrer">{s.nome}</a>
                  </div>
                ))}
                {(m.fieldEvidence || []).map((evidence, i) => (
                  <div key={evidence.sourceUrl + evidence.readOn + i}
                       style={{ fontSize: 12, marginTop: 10, lineHeight: 1.5 }}>
                    <strong>{evidence.fields}: riscontro nella fonte</strong><br />
                    <a href={evidence.sourceUrl} target="_blank" rel="noopener noreferrer">
                      {evidence.sourceName}
                    </a>
                    {' · letta il ' + evidence.readOn}<br />
                    {evidence.sourceDate ? 'Data dei contenuti: ' + evidence.sourceDate
                      : 'Data dei contenuti non dichiarata'}
                  </div>
                ))}
                {(m.calendarExceptions || []).filter(e => e.data >= new Date().toISOString().slice(0, 10)).map((exception, i) => (
                  <div key={exception.data + i} style={{ fontSize: 12, marginTop: 10, lineHeight: 1.5 }}>
                    <strong>{exception.data}: edizione annullata</strong><br />
                    {exception.motivo}{' '}
                    <a href={exception.url} target="_blank" rel="noopener noreferrer">Fonte</a>
                  </div>
                ))}
              </div>
              <div style={{ marginTop: 10 }}>
                Informazioni non corrette?{' '}
                <a href={reportUrl(m)}>Segnala un errore</a>
              </div>
            </div>
          </div>

          {sameCity.length > 0 && (
            <div className="detail-section" style={{ animationDelay: '0.35s' }}>
              <div className="detail-section-title">
                <Icon name="mapPin" size={18} color={catColor} /> Altri mercati a {m.city}
              </div>
              {sameCity.slice(0, 5).map(market => (
                <button type="button" className="link-row" key={market.id} onClick={() => openMarket(market)}>
                  <span className="link-row-date">{formatDateIT(getNextDate(market.dates))}</span>
                  <span className="link-row-main">
                    {market.name}
                    <small>{market.category}{market.hours ? ' · ' + market.hours : ''}</small>
                  </span>
                  <span className="link-row-arrow" aria-hidden="true">›</span>
                </button>
              ))}
              {sameCity.length > 5 && (
                <div className="detail-address-actions" style={{ marginTop: 10 }}>
                  <button className="btn-secondary" onClick={() => showCity(m.city)}>
                    Vedi tutti i {sameCity.length + 1} mercati a {m.city}
                  </button>
                </div>
              )}
            </div>
          )}

          <div style={{ height: 40 }} />
        </div>
      </div>
    );
  };

  const renderFilterPanel = () => (
    <>
      <div className="filter-overlay" onClick={() => setShowFilters(false)} />
      <div className="filter-panel">
        <div className="filter-header">
          <span className="filter-title">Filtri</span>
          <button className="filter-close" onClick={() => setShowFilters(false)}>
            <Icon name="x" size={18} />
          </button>
        </div>
        <div className="filter-body">
          {/* Categories */}
          <div className="filter-section">
            <div className="filter-section-label">Categoria</div>
            <div className="filter-categories">
              {CATS.map(cat => {
                const active = pendingCats.includes(cat);
                const color = CAT_COLORS[cat];
                return (
                  <button key={cat}
                    className={`filter-cat-chip ${active ? 'active' : ''}`}
                    style={active ? { borderColor: color, color, background: color + '10' } : {}}
                    onClick={() => {
                      setPendingCats(prev =>
                        prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]
                      );
                    }}
                  >
                    {CAT_ICONS[cat]} {cat}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Region */}
          <div className="filter-section">
            <div className="filter-section-label">Regione</div>
            <select className="filter-select" value={pendingRegion}
              onChange={e => { setPendingRegion(e.target.value); setPendingCity(""); }}>
              <option value="">Tutte le regioni</option>
              {REGS.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>

          {/* City */}
          <div className="filter-section">
            <div className="filter-section-label">Città</div>
            <select className="filter-select" value={pendingCity}
              onChange={e => setPendingCity(e.target.value)}>
              <option value="">Tutte le città</option>
              {CTS.filter(c => !pendingRegion || allMarkets.find(m => m.city === c)?.region === pendingRegion)
                .map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          {/* Distance */}
          <div className="filter-section">
            <div className="filter-section-label">Distanza massima</div>
            <div className="range-container">
              <div className="range-label">
                <span>0 km</span>
                <span className="range-value">{pendingDist} km</span>
              </div>
              <input type="range" className="range-input"
                min={5} max={100} step={5} value={pendingDist}
                disabled={!canUseDistance}
                onChange={e => setPendingDist(Number(e.target.value))} />
              {!canUseDistance && (
                <div className="setting-sublabel">
                  Per usare il raggio, attiva la posizione in Impostazioni.
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="filter-footer">
          <button className="filter-reset" onClick={resetFilters}>Reimposta filtri</button>
          <button className="filter-apply" onClick={applyFilters}>Applica filtri</button>
        </div>
      </div>
    </>
  );

  const renderExplore = () => (
    <>
      <div className="header" ref={headerRef}>
        <div className="header-title">
          <span className="accent">Fuori</span> <span className="header-sub">Mercatini d'Italia</span>
        </div>

        <div className="search-container">
          <span className="search-icon"><Icon name="search" size={18} /></span>
          <input
            className="search-input"
            placeholder="Cerca città, mercato o parola chiave"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      <div className="toolbar">
        <button type="button" className="back-home" onClick={goHome}><Icon name="chevronLeft" size={16} strokeWidth={2.2} /> Home</button>
        <div className="chips-row" style={{ paddingTop: 0 }}>
          <button className={`chip ${canUseDistance ? 'active' : ''}`} onClick={activateNearby}
            disabled={positionStatus === 'requesting'}>
            <Icon name="mapPin" size={13} />
            {positionStatus === 'ready' ? (includeEstimatedNearby ? 'Vicino a me · posizioni indicative' : 'Vicino a me · 50 km, posizioni precise') :
             positionStatus === 'requesting' ? 'Cerco la posizione…' : 'Mercati vicino a me'}
          </button>
          {[
            { key: "oggi", label: "Oggi" },
            { key: "weekend", label: "Questo weekend" },
            { key: "7giorni", label: "Prossimi 7 giorni" },
          ].map(({ key, label }) => (
            <button key={key}
              className={`chip ${activeDateFilter === key ? 'active' : ''}`}
              onClick={() => {
                setDateFilter(activeDateFilter === key ? null : key);
                setDateFilterExplicit(true);
              }}
            >{label}</button>
          ))}
        </div>
        {positionError && <div role="alert" style={{ fontSize: 12, color: '#A5443D', margin: '0 0 8px' }}>{positionError}</div>}

        <div className="chips-row" aria-label="Filtra per categoria" style={{ paddingTop: 0 }}>
          {CATS.map(cat => {
            const active = filterCategories.length === 1 && filterCategories[0] === cat;
            const color = CAT_COLORS[cat];
            return (
              <button key={cat} type="button" aria-pressed={active}
                className={`chip chip-cat ${active ? 'active' : ''}`}
                style={active ? { background: color, borderColor: color, color: 'white' } : undefined}
                onClick={() => setCategoryQuick(cat)}>
                <span aria-hidden="true">{CAT_ICONS[cat]}</span>{cat}
              </button>
            );
          })}
        </div>

        {viewMode === 'lista' && (
          <div className="chips-row" aria-label="Filtra per giorno della settimana"
            style={{ gap: 5, marginTop: 3, paddingBottom: 5, flexWrap: 'nowrap',
              overflowX: 'auto', scrollbarWidth: 'thin' }}>
            {WEEKDAY_LABELS.map((day, i) => (
              <button key={day} type="button" aria-pressed={weekdayFilter === i}
                aria-label={'Mostra mercati del ' + ['lunedì', 'martedì', 'mercoledì', 'giovedì', 'venerdì', 'sabato', 'domenica'][i]}
                className={`chip ${weekdayFilter === i ? 'active' : ''}`}
                style={{ flexShrink: 0, minWidth: 39, padding: '7px 10px', fontSize: 12 }}
                onClick={() => {
                  setWeekdayFilter(v => v === i ? null : i);
                  // Clicking a weekday asks for the next occurrence, not only today's.
                  if (weekdayFilter !== i) setDateFilter('7giorni');
                }}>
                {day}
              </button>
            ))}
            {weekdayFilter !== null && (
              <button type="button" className="chip" style={{ flexShrink: 0, padding: '7px 9px' }}
                onClick={() => setWeekdayFilter(null)} aria-label="Togli filtro giorno">×</button>
            )}
          </div>
        )}

        {(filterCity || filterRegion || filterCategories.length > 0) && (
          <div className="chips-row" style={{ gap: 8, alignItems: 'center', margin: '2px 0 8px' }}>
            {filterCity && (
              <button className="chip active" onClick={() => {
                setFilterCity('');
                setActiveFilterCount(Math.max(0, activeFilterCount - 1));
              }} aria-label={'Rimuovi filtro città ' + filterCity}>Città: {filterCity} ×</button>
            )}
            {filterRegion && (
              <button className="chip active" onClick={() => {
                setFilterRegion('');
                setActiveFilterCount(Math.max(0, activeFilterCount - 1));
              }} aria-label={'Rimuovi filtro regione ' + filterRegion}>Regione: {filterRegion} ×</button>
            )}
            {filterCategories.length > 0 && (
              <button className="chip active" onClick={() => {
                setFilterCategories([]);
                setActiveFilterCount(Math.max(0, activeFilterCount - 1));
              }}>Categorie ×</button>
            )}
            <button className="chip" onClick={resetAllFilters}>Azzera filtri</button>
          </div>
        )}
        {canUseDistance && filterDistance < 100 && (
          <div role="note" style={{ fontSize: 12, lineHeight: 1.5, color: '#7D7267', margin: '4px 20px 10px' }}>
            {includeEstimatedNearby
              ? 'Mostriamo anche mercati con coordinate non verificate. Alcuni possono non essere davvero vicini.'
              : 'Nel raggio mostriamo solo mercati con posizione precisa. Altri mercati possono mancare.'}
            <button className="chip" style={{ display: 'block', marginTop: 8 }}
              onClick={() => setIncludeEstimatedNearby(prev => !prev)}>
              {includeEstimatedNearby ? 'Escludi posizioni indicative' : 'Mostra anche posizioni indicative'}
            </button>
          </div>
        )}
        <div className="controls-row">
          <div className="view-toggle">
            <button className={viewMode === "lista" ? "active" : ""} onClick={() => setViewMode("lista")}>
              <Icon name="list" size={14} /> Lista
            </button>
            <button className={viewMode === "mappa" ? "active" : ""} onClick={() => setViewMode("mappa")}>
              <Icon name="map" size={14} /> Mappa
            </button>
          </div>

          <div style={{ position: 'relative' }}>
            <button className="sort-btn" onClick={() => setShowSort(!showSort)}>
              <Icon name="sort" size={14} /> Ordina
            </button>
            {showSort && (
              <div className="sort-dropdown">
                {[
                  { key: "data", label: "Data", icon: "calendar" },
                  { key: "distanza", label: "Distanza", icon: "mapPin" },
                ].map(({ key, label, icon }) => (
                  <button key={key}
                    className={`sort-option ${sortBy === key ? 'active' : ''}`}
                    disabled={key === 'distanza' && !canUseDistance}
                    title={key === 'distanza' && !canUseDistance ? 'Attiva la posizione per ordinare per distanza' : ''}
                    onClick={() => { setSortBy(key); setShowSort(false); }}
                  >
                    <Icon name={icon} size={16} /> {label}
                    {sortBy === key && <Icon name="check" size={16} color="#B94439" />}
                  </button>
                ))}
              </div>
            )}
          </div>

          <button className={`filter-btn ${activeFilterCount > 0 ? 'has-filters' : ''}`}
            onClick={openFilters}>
            <Icon name="filter" size={14} /> Filtri
            {activeFilterCount > 0 && <span className="filter-count">{activeFilterCount}</span>}
          </button>
        </div>
      </div>

      <div className="results-count" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span>
          {marketsLoading
            ? 'Caricamento mercati statici...'
            : `${filteredMarkets.length.toLocaleString('it-IT')} ${activeDateFilter ? 'appuntament' + (filteredMarkets.length === 1 ? 'o' : 'i') + ' ' + (activeDateFilter === 'oggi' ? 'previsti oggi' : activeDateFilter === 'weekend' ? 'previsti nel weekend' : 'previsti nei prossimi 7 giorni') : 'sched' + (filteredMarkets.length === 1 ? 'a' : 'e') + ' nel catalogo'}${filterCity ? ' · ' + filterCity : filterRegion ? ' · ' + filterRegion : !canUseDistance ? ' · Italia' : ''}`
          }
          {viewMode === 'lista' && groupedList.length < filteredMarkets.length && !marketsLoading &&
            ` · ${groupedList.length.toLocaleString('it-IT')} schede`}
        </span>
        {dataMode === 'demo' && (
          <span style={{
            fontSize: 10, fontWeight: 700, letterSpacing: '0.05em',
            padding: '2px 8px', borderRadius: 100, 
            background: 'var(--sand)', color: 'var(--ink-lighter)',
          }}>DEMO</span>
        )}
      </div>

      {marketsError && !marketsLoading && (
        <div role="alert" className="empty-state">
          <div className="empty-title">Catalogo temporaneamente non disponibile</div>
          <div className="empty-text">{marketsError}</div>
        </div>
      )}

      {marketsLoading ? (
        <div className="markets-list">
          {[1, 2, 3].map(i => (
            <div key={i} className="market-card" style={{
              height: 120, animation: 'none',
              background: 'linear-gradient(90deg, var(--white) 25%, var(--beige) 50%, var(--white) 75%)',
              backgroundSize: '200% 100%',
              animationName: 'shimmer', animationDuration: '1.5s',
              animationIterationCount: 'infinite', animationTimingFunction: 'linear',
            }} />
          ))}
        </div>
      ) : viewMode === "lista" ? (
        <div className="markets-list">
          {groupedList.length > 0 ? (
            <>
              {groupedList.slice(0, visibleCount).map((entry, i, shown) => {
                // A day header opens each new date; the list is already sorted by next date.
                const dayOf = e => e.kind === 'group'
                  ? e.markets.map(x => getNextDate(x.dates)).filter(Boolean).sort()[0] || null
                  : getNextDate(e.market.dates);
                const showDay = sortBy !== 'distanza' && (i === 0 || dayOf(entry) !== dayOf(shown[i - 1]));
                return (
                  <Fragment key={entry.key}>
                    {showDay && <h2 className="day-header">{dayHeaderLabel(dayOf(entry))}</h2>}
                    {entry.kind === 'group'
                      ? <WeeklyCityGroup group={entry}
                          loadMarket={getMarketDetails} onOpenMarket={openMarket}
                          selectedWeekday={weekdayFilter}
                          autoExpand={shouldAutoExpandWeeklyGroup(entry, weekdayFilter, filterCity, searchQuery)} />
                      : renderMarketCard(entry.market, i)}
                  </Fragment>
                );
              })}
              {visibleCount < groupedList.length && (
                <button className="btn-secondary" onClick={() => setVisibleCount(n => n + 60)}
                  style={{ margin: '18px auto 30px', padding: '12px 24px', display: 'block' }}>
                  Mostra altre schede ({Math.min(visibleCount, groupedList.length)} di {groupedList.length})
                </button>
              )}
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">🔍</div>
              <div className="empty-title">Nessun mercato trovato</div>
              <div className="empty-text">
                {canUseDistance && filterDistance < 100 && !includeEstimatedNearby
                  ? 'Nessun mercato con posizione precisa in questo raggio e periodo. Puoi includere quelli con posizione indicativa.'
                  : 'Prova a cambiare data, distanza, città o categoria.'}
              </div>
              {canUseDistance && filterDistance < 100 && !includeEstimatedNearby && (
                <button className="btn-secondary" style={{ padding: '10px 18px', marginTop: 12 }}
                  onClick={() => setIncludeEstimatedNearby(true)}>Mostra posizioni indicative</button>
              )}
              <button style={{
                marginTop: 16, padding: '10px 24px', background: 'var(--terracotta)',
                color: 'white', border: 'none', borderRadius: 100, fontFamily: 'var(--font-body)',
                fontSize: 14, fontWeight: 600, cursor: 'pointer'
              }} onClick={resetAllFilters}>
                Reimposta
              </button>
            </div>
          )}
        </div>
      ) : (
        renderMapView()
      )}
    </>
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
              {favMarkets.map((m, i) => renderMarketCard(m, i))}
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
        {tab === "esplora" && (view === "home" ? renderHome() : renderExplore())}
        {tab === "mappa" && renderExplore()}
        {tab === "preferiti" && renderFavorites()}
        {tab === "notifiche" && renderNotifications()}
        {tab === "impostazioni" && renderSettings()}

        {showFilters && renderFilterPanel()}
        {selectedMarket && renderDetail()}
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
