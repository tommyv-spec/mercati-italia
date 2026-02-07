/**
 * useMarkets — Data hook with auto-seed.
 *
 * On first load:
 *   1. Check if Firestore has data
 *   2. If empty → seed 30 markets from SEED_MARKETS
 *   3. Fetch markets from Firestore
 *   4. Adapt field names for the UI
 */
import { useState, useEffect, useCallback, useMemo } from 'react'
import {
  fetchMarkets, fetchFilterOptions, getFavorites,
  toggleFavorite as apiToggleFavorite, getDataMode, haversine,
} from '../services/api'
import { autoSeed } from '../services/seed'

const DEFAULT_LAT = 43.7696
const DEFAULT_LNG = 11.2558

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
  Alimentare: '#5B7A5E', Antiquariato: '#C75146', 'Vintage e abbigliamento': '#8B6F8E',
  Usato: '#B8860B', Artigianato: '#2E86AB', Misto: '#E07A5F',
}

function adaptMarket(m, userLat, userLng) {
  const categoryLabel = CATEGORY_LABELS[m.categoria] || m.categoria || 'Misto'
  return {
    id: m.id,
    name: m.nome,
    city: m.citta,
    region: m.regione,
    address: m.indirizzo || '',
    lat: m.lat, lng: m.lng,
    category: categoryLabel,
    tags: m.tags || [],
    dates: m.date || [],
    hours: m.orario_testo || '',
    recurrence: m.ricorrenza_testo || '',
    description: m.descrizione || '',
    source: m.fonte || '',
    confidence: m.confidence || 50,
    lastVerified: m.aggiornato_il ? m.aggiornato_il.slice(0, 10) : '',
    distance: m.distance != null
      ? m.distance
      : (userLat && m.lat ? haversine(userLat, userLng, m.lat, m.lng) : 999),
  }
}

export function useMarkets() {
  const [markets, setMarkets] = useState([])
  const [loading, setLoading] = useState(true)
  const [seedStatus, setSeedStatus] = useState(null) // null | 'seeding' | 'done'
  const [error, setError] = useState(null)
  const [favorites, setFavorites] = useState(new Set())
  const [filterOptions, setFilterOptions] = useState({ regioni: [], citta: [] })
  const [userLat] = useState(DEFAULT_LAT)
  const [userLng] = useState(DEFAULT_LNG)
  const dataMode = getDataMode()

  // Load: auto-seed then fetch
  useEffect(() => {
    let cancelled = false

    async function init() {
      try {
        setLoading(true)

        // Step 1: Auto-seed if Firestore is empty
        setSeedStatus('seeding')
        const seedResult = await autoSeed()
        if (cancelled) return
        setSeedStatus('done')

        if (seedResult.seeded) {
          console.log(`[useMarkets] Seeded ${seedResult.count} markets`)
        }

        // Step 2: Fetch markets + favorites + filter options
        const [rawMarkets, favs, filters] = await Promise.all([
          fetchMarkets({ userLat, userLng }),
          getFavorites(),
          fetchFilterOptions(),
        ])
        if (cancelled) return

        setMarkets(rawMarkets.map(m => adaptMarket(m, userLat, userLng)))
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
  }, [userLat, userLng])

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
    favorites, toggleFav,
    categories, regions, cities,
    categoryIcons: CATEGORY_ICONS,
    categoryColors: CATEGORY_COLORS,
    dataMode, userLat, userLng,
  }
}
