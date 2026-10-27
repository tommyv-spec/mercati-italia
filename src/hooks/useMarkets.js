/**
 * useMarkets — read-only static market catalog hook.
 * No Firebase or Cloudflare runtime invocation on visits.
 */
import { useState, useEffect, useCallback, useMemo } from 'react'
import { isSuspiciousCityName, safeCityLabel } from '../lib/locationQuality.js'
import { fieldEvidenceSummary } from '../lib/fieldEvidence.js'
import { addressConflictView, cleanAddressConflicts } from '../lib/sourceFieldConflicts.js'
import {
  fetchMarkets, fetchMarketById, getFavorites, revalidateCatalogIfStale,
  toggleFavorite as apiToggleFavorite, getDataMode, canonicalMarketId,
} from '../services/staticMarkets.js'

const CATEGORY_LABELS = {
  alimentare: 'Alimentare',
  antiquariato: 'Antiquariato',
  vintage_abbigliamento: 'Vintage e abbigliamento',
  usato: 'Usato',
  artigianato: 'Artigianato',
  misto: 'Misto',
}

const CATEGORY_ICONS = {
  Alimentare: '🍅', Antiquariato: '🏺', 'Vintage e abbigliamento': '👗',
  Usato: '📦', Artigianato: '🎨', Misto: '🎪',
}

const CATEGORY_COLORS = {
  Alimentare: '#446E47', Antiquariato: '#B94439', 'Vintage e abbigliamento': '#705073',
  Usato: '#805B08', Artigianato: '#216886', Misto: '#9C4B36',
}

export function adaptMarket(m, userLat, userLng) {
  const categoryLabel = CATEGORY_LABELS[m.categoria] || m.categoria || 'Misto'
  const locationReviewRequired = isSuspiciousCityName(m.citta) ||
    m.navigazione_sospesa_motivo === 'indirizzo_e_punto_sorgente_non_riconciliati'
  // Only picks the warning text: a repaired town (citta_originale) also started as a
  // place no Comune matched; otherwise the Comune is known and the venue isn't confirmed.
  const cityUncertain = isSuspiciousCityName(m.citta) || Boolean(m.citta_originale)
  const market = {
    id: m.id,
    name: m.nome,
    city: safeCityLabel(m.citta),
    originalCity: m.citta,
    province: m.provincia || '',
    locationReviewRequired,
    cityUncertain,
    region: m.regione,
    address: m.indirizzo || '',
    lat: m.lat, lng: m.lng,
    category: categoryLabel,
    tags: m.tags || [],
    dates: m.date || [],
    hours: m.orario_testo || '',
    indexHoursScope: m.ambito_orari || '',
    recurrence: m.ricorrenza_testo || '',
    description: m.descrizione || '',
    source: m.fonte || '',
    confidence: m.confidence ?? 0,
    dataCompleteness: m.completezza ?? 0,
    sourceUpdated: m.fonte_aggiornata_il ? m.fonte_aggiornata_il.slice(0, 10) : '',
    sourceUpdateScope: m.aggiornamento_ambito || '',
    // Last scrape is not a human confirmation.
    lastVerified: m.verificato_il ? m.verificato_il.slice(0, 10) : '',
    dateQuality: m.date_quality || 'prevista',
    positionQuality: m.position_quality || 'sconosciuta',
    // Street-level point looked up on OpenStreetMap (ODbL): needs its attribution.
    positionFromOsm: m.posizione_fonte?.fonte === 'openstreetmap',
    status: m.status || 'non_confermato',
    // Hidden from lists; still opens from an old link or favourite.
    concluded: m.concluso || '',
    sourceUrl: m.url_fonte || '',
    // Full source list arrives only with lazy-loaded regional detail JSON.
    // The nationwide compact index remains unchanged and cheap to fetch.
    sourceEvidence: Array.isArray(m.fonti) ? m.fonti.filter(s => s && s.url && s.nome) : [],
    fieldEvidence: fieldEvidenceSummary(m),
    fieldConflicts: cleanAddressConflicts(m.conflitti_campi, m),
    calendarExceptions: Array.isArray(m.eccezioni_calendario) ? m.eccezioni_calendario : [],
    sourceCalendar: m.calendario_fonte || null,
    sourceDetail: m.dettaglio_fonte || null,
    editorialEvidence: m.evidenza_editoriale || null,
    distance: Number.isFinite(m.distance) ? m.distance : null,
  }
  return {...market, addressReviewRequired: addressConflictView(market).length > 0}
}

export function useMarkets() {
  const [markets, setMarkets] = useState([])
  const [loading, setLoading] = useState(true)
  const [catalogRevision, setCatalogRevision] = useState(0)
  const seedStatus = null // Retained for compatibility; no browser-side seed
  const [error, setError] = useState(null)
  const [favorites, setFavorites] = useState(new Set())
  const [filterOptions, setFilterOptions] = useState({ regioni: [], citta: [] })
  // Explicit opt-in only. Never pretend the visitor is located in Florence.
  const [userPosition, setUserPosition] = useState(null)
  const [positionStatus, setPositionStatus] = useState('idle')
  const [positionError, setPositionError] = useState('')
  const userLat = userPosition?.lat ?? null
  const userLng = userPosition?.lng ?? null
  const dataMode = getDataMode()

  const requestPosition = useCallback(() => {
    if (typeof navigator === 'undefined' || !navigator.geolocation) {
      setPositionStatus('unavailable')
      setPositionError('La posizione non è disponibile su questo dispositivo.')
      return
    }
    setPositionStatus('requesting')
    setPositionError('')
    navigator.geolocation.getCurrentPosition(
      (position) => {
        const lat = position?.coords?.latitude
        const lng = position?.coords?.longitude
        if (!Number.isFinite(lat) || !Number.isFinite(lng)) {
          setPositionStatus('error')
          setPositionError('Non sono riuscito a leggere la posizione.')
          return
        }
        setUserPosition({ lat, lng })
        setPositionStatus('ready')
        setPositionError('')
      },
      (error) => {
        setPositionStatus(error?.code === 1 ? 'denied' : 'error')
        setPositionError(error?.code === 1
          ? 'Accesso alla posizione negato. Puoi cercare per città.'
          : 'Posizione non disponibile. Puoi cercare per città.')
      },
      { enableHighAccuracy: false, timeout: 12000, maximumAge: 300000 }
    )
  }, [])

  const clearPosition = useCallback(() => {
    setUserPosition(null)
    setPositionStatus('idle')
    setPositionError('')
  }, [])

  // Keep long-open tabs current without polling while hidden or invoking
  // Firestore, Workers, Functions or other dynamic backends.
  useEffect(() => {
    let mounted = true
    const check = () => {
      if (document.visibilityState === 'hidden') return
      revalidateCatalogIfStale().then(changed => {
        if (mounted && changed) setCatalogRevision(value => value + 1)
      }).catch(() => {
        // Preserve the last tested working catalog; retry at the next check.
      })
    }
    document.addEventListener('visibilitychange', check)
    window.addEventListener('focus', check)
    const interval = window.setInterval(check, 30 * 60 * 1000)
    return () => {
      mounted = false
      document.removeEventListener('visibilitychange', check)
      window.removeEventListener('focus', check)
      window.clearInterval(interval)
    }
  }, [])

  // Load the static catalog; recalculate distances after opt-in positioning.
  useEffect(() => {
    let cancelled = false

    async function init() {
      try {
        setLoading(true)

        // Load published static records. Never write data on behalf of a visitor.
        const [rawMarkets, favs] = await Promise.all([
          fetchMarkets({ userLat, userLng }),
          getFavorites(),
        ])
        // Quarantine corrupt municipality labels in the UI only; original
        // source rows, title search and all source IDs remain untouched.
        const adapted = rawMarkets.map(m => adaptMarket(m, userLat, userLng))
        const filters = {
          regioni: [...new Set(adapted.map(m => m.region).filter(Boolean))].sort(),
          citta: [...new Set(adapted.filter(m => !m.locationReviewRequired)
            .map(m => m.city).filter(Boolean))].sort(),
        }
        if (cancelled) return

        setMarkets(adapted)
        setFavorites(favs)
        setFilterOptions(filters)
        setError(null)
      } catch (e) {
        if (!cancelled) setError(e.message)
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    init()
    return () => { cancelled = true }
  }, [userLat, userLng, catalogRevision])

  const toggleFav = useCallback(async (marketId) => {
    setFavorites(prev => {
      const next = new Set(prev)
      if (next.has(marketId)) next.delete(marketId)
      else next.add(marketId)
      return next
    })
    try {
      const updated = await apiToggleFavorite(marketId)
      setFavorites(updated)
    } catch {}
  }, [])

  const getMarketDetails = useCallback(async marketId => {
    const raw = await fetchMarketById(marketId)
    return raw ? adaptMarket(raw, userLat, userLng) : null
  }, [userLat, userLng])

  const categories = useMemo(() =>
    ['Alimentare', 'Antiquariato', 'Vintage e abbigliamento', 'Usato', 'Artigianato', 'Misto'], [])

  const regions = useMemo(() =>
    filterOptions.regioni.length > 0
      ? filterOptions.regioni
      : [...new Set(markets.map(m => m.region))].sort(),
    [filterOptions.regioni, markets])

  const cities = useMemo(() =>
    filterOptions.citta.length > 0
      ? filterOptions.citta
      : [...new Set(markets.map(m => m.city))].sort(),
    [filterOptions.citta, markets])

  return {
    markets, loading, error, seedStatus,
    favorites, toggleFav, getMarketDetails, canonicalId: canonicalMarketId,
    categories, regions, cities,
    categoryIcons: CATEGORY_ICONS,
    categoryColors: CATEGORY_COLORS,
    dataMode, userLat, userLng, positionStatus, positionError,
    requestPosition, clearPosition,
  }
}
