/**
 * Mercati d'Italia — static, CDN-friendly read-only catalog.
 *
 * Public visitors never touch Firestore, Workers, KV or D1.
 * The update job creates a manifest and content-hashed JSON assets at build time.
 * Browser Cache-Control handles subsequent visits and refreshes.
 */
const BASE_URL = import.meta.env.BASE_URL || '/'
const FAVORITES_KEY = 'mercati_preferiti'
let catalogPromise
const regionPromises = new Map()

function staticURL(path) {
  if (typeof path !== 'string' || !/^data\/v1\/[a-zA-Z0-9._/-]+\.json$/.test(path) || path.includes('..')) {
    throw new Error('Percorso catalogo non valido')
  }
  return BASE_URL.replace(/\/$/, '/') + path
}

async function loadJSON(path, immutable = false) {
  const response = await fetch(staticURL(path), { cache: immutable ? 'force-cache' : 'default' })
  if (!response.ok) throw new Error('Catalogo non disponibile: ' + path + ' (' + response.status + ')')
  return response.json()
}

async function mapLimited(items, concurrency, mapper) {
  let next = 0
  const output = new Array(items.length)
  await Promise.all(Array.from({ length: Math.min(items.length, concurrency) }, async () => {
    while (next < items.length) {
      const index = next++
      output[index] = await mapper(items[index], index)
    }
  }))
  return output
}

async function loadCatalog() {
  const manifest = await loadJSON('data/v1/manifest.json')
  if (manifest.schema !== 1 || !Number.isInteger(manifest.total) || manifest.total < 0) {
    throw new Error('Manifest del catalogo non valido')
  }

  if (manifest.index) {
    const index = await loadJSON(manifest.index, true)
    if (index.schema !== 1 || !Array.isArray(index.markets) || index.markets.length !== manifest.total) {
      throw new Error('Indice mercati incompleto')
    }
    const ids = new Set()
    for (const record of index.markets) {
      if (!record.slug || ids.has(record.slug)) throw new Error('Indice duplicato o non valido')
      ids.add(record.slug)
    }
    return { manifest, markets: index.markets }
  }

  let parts
  if (manifest.layout === 'single') {
    parts = [{ path: manifest.catalog }]
  } else if (manifest.layout === 'regional' && Array.isArray(manifest.regions)) {
    parts = manifest.regions
  } else {
    throw new Error('Formato catalogo non supportato')
  }

  const chunks = await mapLimited(parts, 4, async (part) => {
    const data = await loadJSON(part.path, true)
    if (data.schema !== 1 || !Array.isArray(data.markets)) {
      throw new Error('File mercati non valido: ' + part.path)
    }
    if (part.count !== undefined && data.markets.length !== part.count) {
      throw new Error('Conteggio non valido: ' + part.path)
    }
    return data.markets
  })

  const markets = chunks.flat()
  if (markets.length !== manifest.total) throw new Error('Catalogo incompleto')
  const ids = new Set()
  for (const market of markets) {
    if (!market.slug || ids.has(market.slug)) throw new Error('ID mercato duplicato o assente')
    ids.add(market.slug)
  }
  return { manifest, markets }
}

export async function fetchCatalog() {
  if (!catalogPromise) {
    catalogPromise = loadCatalog().catch(error => {
      catalogPromise = null
      throw error
    })
  }
  return catalogPromise
}

export function todayISO(now = new Date()) {
  return [now.getFullYear(), String(now.getMonth() + 1).padStart(2, '0'), String(now.getDate()).padStart(2, '0')].join('-')
}

export function getNextDate(dates = []) {
  const today = todayISO()
  return (dates || []).filter(d => typeof d === 'string' && d >= today).sort()[0] || null
}

export function haversine(lat1, lng1, lat2, lng2) {
  if (![lat1, lng1, lat2, lng2].every(Number.isFinite)) return Infinity
  const rad = Math.PI / 180
  const deltaLat = (lat2 - lat1) * rad
  const deltaLng = (lng2 - lng1) * rad
  const a = Math.sin(deltaLat / 2) ** 2 +
    Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(deltaLng / 2) ** 2
  return 6371 * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a))
}

function normalize(m, userLat, userLng) {
  const lat = typeof m.lat === 'number' && Number.isFinite(m.lat) ? m.lat : null
  const lng = typeof m.lng === 'number' && Number.isFinite(m.lng) ? m.lng : null
  return {
    id: m.slug,
    nome: m.nome || '',
    citta: m.citta || '',
    provincia: m.provincia || '',
    regione: m.regione || '',
    indirizzo: m.indirizzo || '',
    lat, lng,
    categoria: m.categoria || 'misto',
    tags: m.tags || [],
    orario_testo: m.orario_testo || '',
    ricorrenza_testo: m.ricorrenza_testo || '',
    descrizione: m.descrizione || '',
    date: m.date || [],
    prossima_data: getNextDate(m.date),
    confidence: m.confidence ?? 0,
    completezza: m.completezza ?? 0,
    verificato_il: m.verificato_il || '',
    aggiornato_il: m.aggiornato_il || '',
    date_quality: m.date_quality || 'prevista',
    position_quality: m.position_quality || 'sconosciuta',
    status: m.status || 'non_confermato',
    fonte: m.fonte || '',
    url_fonte: m.url_fonte || '',
    distance: Number.isFinite(userLat) && Number.isFinite(userLng)
      && Number.isFinite(lat) && Number.isFinite(lng)
      ? haversine(userLat, userLng, lat, lng) : null,
  }
}

export async function fetchMarkets({ userLat = null, userLng = null } = {}) {
  const { markets } = await fetchCatalog()
  return markets.map(m => normalize(m, userLat, userLng))
}

export async function fetchMarketById(id) {
  const { manifest, markets } = await fetchCatalog()
  const summary = markets.find(m => m.slug === id)
  if (!summary) return null

  // Before the index migration, the entire catalog was already loaded.
  if (!manifest.index) return normalize(summary, null, null)

  const entry = manifest.layout === 'single'
    ? { path: manifest.catalog }
    : manifest.regions.find(part => part.name === summary.regione)
  if (!entry) throw new Error('Dettagli non disponibili per la regione')

  if (!regionPromises.has(entry.path)) {
    const request = loadJSON(entry.path, true).then(payload => {
      if (payload.schema !== 1 || !Array.isArray(payload.markets)) {
        throw new Error('Dati regionali non validi')
      }
      if (entry.count !== undefined && payload.markets.length !== entry.count) {
        throw new Error('Catalogo regionale incompleto')
      }
      return payload.markets
    }).catch(error => {
      regionPromises.delete(entry.path)
      throw error
    })
    regionPromises.set(entry.path, request)
  }
  const records = await regionPromises.get(entry.path)
  const detail = records.find(m => m.slug === id)
  if (!detail) throw new Error('Mercato non trovato nel file regionale')
  return normalize(detail, null, null)
}

export async function fetchFilterOptions() {
  const { markets } = await fetchCatalog()
  return {
    regioni: [...new Set(markets.map(m => m.regione).filter(Boolean))].sort(),
    citta: [...new Set(markets.map(m => m.citta).filter(Boolean))].sort(),
  }
}

export function getDataMode() { return 'static' }

function localFavorites() {
  try {
    return new Set(JSON.parse(localStorage.getItem(FAVORITES_KEY) || '[]'))
  } catch {
    return new Set()
  }
}

export async function getFavorites() {
  return localFavorites()
}

export async function toggleFavorite(marketId) {
  const favorites = localFavorites()
  if (favorites.has(marketId)) favorites.delete(marketId)
  else favorites.add(marketId)
  try { localStorage.setItem(FAVORITES_KEY, JSON.stringify([...favorites])) } catch { /* no storage */ }
  return favorites
}
