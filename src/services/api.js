/**
 * Mercati d'Italia — API Service Layer (Firebase/Firestore)
 *
 * Always connects to Firestore (credentials hardcoded).
 * Falls back to seed data in-memory if Firestore queries fail.
 */
import { db, auth, isFirebaseConfigured } from '../lib/firebase'
import {
  collection, doc, query, where, orderBy, limit,
  getDocs, getDoc, setDoc, deleteDoc, Timestamp, startAfter,
} from 'firebase/firestore'
import { SEED_MARKETS } from '../data/sampleMarkets'

// ─── Haversine distance ─────────────────────────────────────

export function haversine(lat1, lng1, lat2, lng2) {
  const R = 6371
  const dLat = (lat2 - lat1) * Math.PI / 180
  const dLng = (lng2 - lng1) * Math.PI / 180
  const a = Math.sin(dLat / 2) ** 2 +
    Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
    Math.sin(dLng / 2) ** 2
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

// ─── Date helpers ───────────────────────────────────────────

// Local calendar dates: UTC timestamps can be a day off in Italy.
export function todayISO(now = new Date()) {
  const year = now.getFullYear()
  const month = String(now.getMonth() + 1).padStart(2, '0')
  const day = String(now.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}
const allowDemoFallback = import.meta.env.DEV && import.meta.env.VITE_DEMO_MODE === 'true'

function getWeekendDates() {
  const now = new Date()
  const day = now.getDay()
  const satOffset = 6 - day
  const sat = new Date(now); sat.setDate(sat.getDate() + satOffset)
  const sun = new Date(sat); sun.setDate(sun.getDate() + 1)
  return [todayISO(sat), todayISO(sun)]
}

function getNext7DaysEnd() {
  const end = new Date(); end.setDate(end.getDate() + 7)
  return todayISO(end)
}

export function getDateBadge(dates) {
  const tomorrow = new Date(); tomorrow.setDate(tomorrow.getDate() + 1)
  const tomorrowStr = todayISO(tomorrow)
  const [sat, sun] = getWeekendDates()
  if (dates?.includes(todayISO())) return { label: 'Oggi', color: '#C75146' }
  if (dates?.includes(tomorrowStr)) return { label: 'Domani', color: '#E07A5F' }
  if (dates?.includes(sat) || dates?.includes(sun)) return { label: 'Questo weekend', color: '#5B7A5E' }
  return null
}

export function getNextDate(dates) {
  if (!dates?.length) return null
  return dates.filter(d => d >= todayISO()).sort()[0] || null
}

export function formatDateIT(dateStr) {
  const d = new Date(dateStr + 'T00:00:00')
  return d.toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' })
}

// ─── Data source mode ───────────────────────────────────────

export function getDataMode() {
  return 'firebase'
}

// ═══════════════════════════════════════════════════════════════
// MARKET QUERIES
// ═══════════════════════════════════════════════════════════════

export async function fetchMarkets({
  userLat = null, userLng = null,
  categoria = null, regione = null, citta = null,
  maxDistanceKm = null, dateFilter = null,
  searchQuery = '', sortBy = 'data',
} = {}) {
  let markets

  try {
    markets = await _fetchFromFirestore({ categoria, regione })
  } catch (e) {
    if (!allowDemoFallback) throw e
    console.warn('Firestore query failed. Explicit development demo fallback enabled:', e)
    markets = _seedAsFallback()
  }

  // Compute distances
  if (Number.isFinite(userLat) && Number.isFinite(userLng)) {
    markets = markets.map(m => ({
      ...m,
      distance: haversine(userLat, userLng, m.lat, m.lng)
    }))
  }

  // Client-side filters
  markets = _applyFilters(markets, { categoria, regione, citta, maxDistanceKm, dateFilter, searchQuery })

  // Sort
  if (sortBy === 'distanza' && userLat) {
    markets.sort((a, b) => (a.distance || 999) - (b.distance || 999))
  } else {
    markets.sort((a, b) => {
      const aDate = getNextDate(a.date) || '9999'
      const bDate = getNextDate(b.date) || '9999'
      return aDate.localeCompare(bDate)
    })
  }

  return markets
}

export async function fetchMarketById(id) {
  try {
    const snap = await getDoc(doc(db, 'mercati', id))
    if (!snap.exists()) return null
    return _normalizeDoc(snap)
  } catch (e) {
    if (!allowDemoFallback) throw e
    console.warn('Firestore fetch failed. Explicit development demo fallback enabled:', e)
    return _seedAsFallback().find(m => m.id === id) || null
  }
}

export async function fetchFilterOptions() {
  try {
    const snap = await getDocs(collection(db, 'mercati'))
    const regioni = new Set(), citta = new Set()
    snap.forEach(d => {
      const data = d.data()
      if (data.regione) regioni.add(data.regione)
      if (data.citta) citta.add(data.citta)
    })
    return { regioni: [...regioni].sort(), citta: [...citta].sort() }
  } catch (e) {
    if (!allowDemoFallback) throw e
    const fallback = _seedAsFallback()
    return {
      regioni: [...new Set(fallback.map(m => m.regione))].sort(),
      citta: [...new Set(fallback.map(m => m.citta))].sort(),
    }
  }
}

// ═══════════════════════════════════════════════════════════════
// FAVORITES (localStorage — no auth required)
// ═══════════════════════════════════════════════════════════════

const LOCAL_FAVS_KEY = 'mercati_preferiti'

export async function getFavorites() {
  // If user is authenticated, use Firestore
  if (auth?.currentUser) {
    try {
      const uid = auth.currentUser.uid
      const snap = await getDocs(collection(db, 'utenti', uid, 'preferiti'))
      return new Set(snap.docs.map(d => d.id))
    } catch { /* fall through to local */ }
  }
  return _getLocalFavorites()
}

export async function toggleFavorite(marketId) {
  if (auth?.currentUser) {
    try {
      const uid = auth.currentUser.uid
      const ref = doc(db, 'utenti', uid, 'preferiti', marketId)
      const snap = await getDoc(ref)
      if (snap.exists()) await deleteDoc(ref)
      else await setDoc(ref, { creato_il: Timestamp.now() })
      return getFavorites()
    } catch { /* fall through */ }
  }
  return _toggleLocalFavorite(marketId)
}

function _getLocalFavorites() {
  try {
    const stored = localStorage.getItem(LOCAL_FAVS_KEY)
    return new Set(stored ? JSON.parse(stored) : [])
  } catch { return new Set() }
}

function _toggleLocalFavorite(marketId) {
  const favs = _getLocalFavorites()
  if (favs.has(marketId)) favs.delete(marketId)
  else favs.add(marketId)
  try { localStorage.setItem(LOCAL_FAVS_KEY, JSON.stringify([...favs])) } catch {}
  return favs
}

// ═══════════════════════════════════════════════════════════════
// INTERNAL: Firestore
// ═══════════════════════════════════════════════════════════════

async function _fetchFromFirestore({ categoria, regione }) {
  const ref = collection(db, 'mercati')
  const constraints = []
  // Indexed single-field filtering; any additional filters run client-side.
  if (regione) constraints.push(where('regione', '==', regione))
  else if (typeof categoria === 'string') constraints.push(where('categoria', '==', categoria))

  const PAGE_SIZE = 250
  const MAX_RECORDS = 10000
  const markets = []
  let cursor = null
  do {
    const pageQuery = query(ref, ...constraints, limit(PAGE_SIZE), ...(cursor ? [startAfter(cursor)] : []))
    const page = await getDocs(pageQuery)
    markets.push(...page.docs.map(_normalizeDoc))
    if (page.empty || page.size < PAGE_SIZE) break
    cursor = page.docs[page.docs.length - 1]
  } while (markets.length < MAX_RECORDS)

  if (markets.length >= MAX_RECORDS) {
    throw new Error('Troppi mercati per la ricerca client: usa filtri o una ricerca server-side.')
  }
  return markets
}

function _normalizeDoc(snap) {
  const d = snap.data()
  return {
    id: snap.id,
    nome: d.nome || '',
    citta: d.citta || '',
    provincia: d.provincia || '',
    regione: d.regione || '',
    indirizzo: d.indirizzo || '',
    lat: d.lat || 0, lng: d.lng || 0,
    categoria: d.categoria || 'misto',
    tags: d.tags || [],
    orario_testo: d.orario_testo || '',
    ricorrenza_testo: d.ricorrenza_testo || '',
    descrizione: d.descrizione || '',
    confidence: d.confidence || 50,
    aggiornato_il: d.aggiornato_il || '',
    verificato_il: d.verificato_il || '',
    date: d.date || [],
    prossima_data: getNextDate(d.date || []),
    fonte: d.fonte || '',
  }
}

// ═══════════════════════════════════════════════════════════════
// INTERNAL: Seed fallback (resolve date getters)
// ═══════════════════════════════════════════════════════════════

function _seedAsFallback() {
  return SEED_MARKETS.map(m => ({
    id: m.slug,
    nome: m.nome,
    citta: m.citta,
    provincia: m.provincia,
    regione: m.regione,
    indirizzo: m.indirizzo,
    lat: m.lat, lng: m.lng,
    categoria: m.categoria,
    tags: m.tags,
    orario_testo: m.orario_testo,
    ricorrenza_testo: m.ricorrenza_testo,
    descrizione: m.descrizione,
    confidence: m.confidence,
    aggiornato_il: todayISO(),
    date: m.date, // triggers the getter
    prossima_data: m.date[0] || null,
    fonte: m.fonte,
  }))
}

// ═══════════════════════════════════════════════════════════════
// INTERNAL: Client-side filtering
// ═══════════════════════════════════════════════════════════════

function _applyFilters(markets, { categoria, regione, citta, maxDistanceKm, dateFilter, searchQuery }) {
  let result = markets

  if (searchQuery?.trim()) {
    const q = searchQuery.toLowerCase()
    result = result.filter(m =>
      m.nome?.toLowerCase().includes(q) ||
      m.citta?.toLowerCase().includes(q) ||
      m.categoria?.toLowerCase().includes(q) ||
      m.tags?.some(t => t.toLowerCase().includes(q))
    )
  }

  if (dateFilter === 'oggi') {
    result = result.filter(m => m.date?.includes(todayISO()))
  } else if (dateFilter === 'weekend') {
    const [sat, sun] = getWeekendDates()
    result = result.filter(m => m.date?.includes(sat) || m.date?.includes(sun))
  } else if (dateFilter === '7giorni') {
    const endStr = getNext7DaysEnd()
    result = result.filter(m => m.date?.some(d => d >= todayISO() && d <= endStr))
  }

  if (categoria && typeof categoria === 'object' && categoria.length > 0) {
    result = result.filter(m => categoria.includes(m.categoria))
  }
  if (regione) result = result.filter(m => m.regione === regione)
  if (citta) result = result.filter(m => m.citta === citta)
  if (maxDistanceKm != null) {
    result = result.filter(m => Number.isFinite(m.distance) && m.distance <= maxDistanceKm)
  }

  return result
}
