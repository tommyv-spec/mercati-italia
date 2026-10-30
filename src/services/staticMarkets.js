/**
 * Mercati d'Italia — static, CDN-friendly read-only catalog.
 *
 * Public visitors never touch Firestore, Workers, KV or D1.
 * The update job creates a manifest and content-hashed JSON assets at build time.
 * Browser Cache-Control handles subsequent visits and refreshes.
 */
import { cleanAddressConflicts } from '../lib/sourceFieldConflicts.js'
import { fallbackIsEvent } from '../lib/cadence.js'

const BASE_URL = import.meta.env?.BASE_URL || '/'
export const CATALOG_CHECK_INTERVAL_MS = 30 * 60 * 1000
let lastCatalogCheckAt = 0
let catalogRecheckPromise = null
const FAVORITES_KEY = 'mercati_preferiti'
let catalogPromise
const regionPromises = new Map()
const INDEX_FIELDS = ['slug', 'nome', 'citta', 'regione', 'categoria', 'tags',
  'lat', 'lng', 'position_quality', 'orario_testo', 'date_quality', 'date']
const HOURS_SCOPES = new Set(['', 'per_data', 'storico'])

export function decodeIndexRecords(records, manifest) {
  const schema = manifest.index_schema
  const compact = [4, 5, 6, 7, 8].includes(schema)
  const legacy = schema === undefined || [1, 2, 3].includes(schema)
  if (!compact && !legacy) throw new Error('Versione indice non supportata')
  if (schema >= 6) {
    const day = manifest.index_as_of
    const parsed = typeof day === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(day)
      ? new Date(day + 'T12:00:00Z') : null
    if (!parsed || !Number.isFinite(parsed.getTime()) || parsed.toISOString().slice(0, 10) !== day) {
      throw new Error('Data di riferimento indice non valida')
    }
  }
  const columns = schema === 8 ? [...INDEX_FIELDS, 'ambito_orari', 'duplicato_di', 'concluso']
    : schema === 7 ? [...INDEX_FIELDS, 'ambito_orari', 'duplicato_di']
    : schema === 6 ? [...INDEX_FIELDS, 'ambito_orari'] : INDEX_FIELDS
  return records.map(record => {
    if (!Array.isArray(record)) {
      if (!legacy || !record || typeof record !== 'object') throw new Error('Formato indice errato')
      // Legacy object previews never establish the new source-bound flag.
      return {...record, ambito_orari: ''}
    }
    if ((schema !== undefined && !compact) || record.length !== columns.length ||
        schema >= 6 && !HOURS_SCOPES.has(record[INDEX_FIELDS.length]) ||
        schema >= 7 && typeof record[INDEX_FIELDS.length + 1] !== 'string' ||
        schema === 8 && typeof record[columns.length - 1] !== 'string') {
      throw new Error('Formato indice errato')
    }
    return Object.fromEntries(columns.map((key, i) => [key, record[i]]))
  })
}

const EVENT_FIELDS = ['indirizzo', 'ricorrenza_testo', 'descrizione', 'ingresso', 'consigli']

// data/v1/eventi-{hash}.json -> Map(slug -> rich fields). null when the file is unusable.
export function decodeEventRows(data) {
  if (!data || data.schema !== 1 || !Array.isArray(data.markets)) return null
  const map = new Map()
  for (const row of data.markets) {
    if (!Array.isArray(row) || row.length !== EVENT_FIELDS.length + 1 || typeof row[0] !== 'string') return null
    map.set(row[0], Object.fromEntries(EVENT_FIELDS.map((key, i) => [key, typeof row[i + 1] === 'string' ? row[i + 1] : ''])))
  }
  return map
}

export function mergeEventFields(record, events) {
  if (!events) return { ...record, isEvent: fallbackIsEvent(record) }
  const rich = events.get(record.slug)
  if (!rich) return { ...record, isEvent: false }
  const merged = { ...record, isEvent: true }
  for (const key of EVENT_FIELDS) if (!merged[key]) merged[key] = rich[key]
  return merged
}

function staticURL(path) {
  if (typeof path !== 'string' || !/^data\/v1\/[a-zA-Z0-9._/-]+\.json$/.test(path) || path.includes('..')) {
    throw new Error('Percorso catalogo non valido')
  }
  return BASE_URL.replace(/\/$/, '/') + path
}

async function loadJSON(path, immutable = false, revalidate = false, now = Date.now()) {
  let url = staticURL(path)
  if (path === 'data/v1/manifest.json') {
    if (!Number.isFinite(now) || now < 0) throw new Error('Data controllo catalogo non valida')
    // The stable preview CDN can retain an old manifest even with no-cache.
    // Share one deterministic cache entry per half hour; hashed assets keep
    // their immutable URL. Add this key only after validating the local path.
    url += '?refresh=' + Math.floor(now / CATALOG_CHECK_INTERVAL_MS)
  }
  const response = await fetch(url, {
    cache: immutable ? 'force-cache' : revalidate ? 'no-cache' : 'default',
  })
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

/**
 * A soft-merged copy ("duplicato_di") keeps its ID only so old favourites and
 * links resolve to the kept record; list, map and counters never show it.
 */
export function splitDuplicates(markets) {
  const ids = new Set(markets.map(m => m.slug))
  const aliases = new Map()
  const concluded = new Map()
  const visible = []
  for (const market of markets) {
    if (market.duplicato_di && ids.has(market.duplicato_di)) aliases.set(market.slug, market.duplicato_di)
    else if (market.concluso) concluded.set(market.slug, market)
    else visible.push(market)
  }
  return { markets: visible, aliases, concluded }
}

async function loadCatalogFromManifest(manifest) {
  if (manifest.schema !== 1 || !Number.isInteger(manifest.total) || manifest.total < 0) {
    throw new Error('Manifest del catalogo non valido')
  }

  if (manifest.index) {
    const index = await loadJSON(manifest.index, true)
    if (index.schema !== 1 || !Array.isArray(index.markets) || index.markets.length !== manifest.total) {
      throw new Error('Indice mercati incompleto')
    }
    const markets = decodeIndexRecords(index.markets, manifest)
    const ids = new Set()
    for (const record of markets) {
      if (!record.slug || ids.has(record.slug)) throw new Error('Indice duplicato o non valido')
      ids.add(record.slug)
    }
    let events = null
    if (typeof manifest.events === 'string' && manifest.events_schema === 1) {
      events = decodeEventRows(await loadJSON(manifest.events, true).catch(() => null))
    }
    return { manifest, events, ...splitDuplicates(markets) }
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
  return { manifest, ...splitDuplicates(markets) }
}

async function loadCatalog() {
  const checkedAt = Date.now()
  const result = await loadCatalogFromManifest(await loadJSON('data/v1/manifest.json', false, false, checkedAt))
  lastCatalogCheckAt = checkedAt
  return result
}

// A browser tab can remain open after the daily deployment. Only the small
// static manifest is revalidated, at most once per 30 minutes while visible.
// Unchanged manifests avoid downloading a new index or regional data.
export function shouldRevalidateCatalog(lastCheck, now = Date.now()) {
  return Number.isFinite(now) && (!lastCheck || (now >= lastCheck
    && now - lastCheck >= CATALOG_CHECK_INTERVAL_MS))
}

export async function revalidateCatalogIfStale(now = Date.now()) {
  const current = await fetchCatalog()
  if (catalogRecheckPromise) return catalogRecheckPromise
  if (!shouldRevalidateCatalog(lastCatalogCheckAt, now)) return false
  // A failed check keeps the working catalog and also observes the rate
  // limit. Focus/visibility events must not repeatedly hit a failing CDN.
  lastCatalogCheckAt = now
  catalogRecheckPromise = (async () => {
    const manifest = await loadJSON('data/v1/manifest.json', false, true, now)
    if (manifest.content_signature && current.manifest.content_signature
        && manifest.content_signature === current.manifest.content_signature
        && manifest.index === current.manifest.index) {
      lastCatalogCheckAt = now
      return false
    }
    // Prepare all data before switching. A missing shard/index must never
    // replace the last working catalog in the active browser session.
    const next = await loadCatalogFromManifest(manifest)
    catalogPromise = Promise.resolve(next)
    regionPromises.clear()
    lastCatalogCheckAt = now
    return true
  })()
  try {
    return await catalogRecheckPromise
  } finally {
    catalogRecheckPromise = null
  }
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
    citta_originale: m.citta_originale || '',
    provincia: m.provincia || '',
    regione: m.regione || '',
    indirizzo: m.indirizzo || '',
    lat, lng,
    categoria: m.categoria || 'misto',
    tags: m.tags || [],
    orario_testo: m.orario_testo || '',
    ambito_orari: HOURS_SCOPES.has(m.ambito_orari) ? m.ambito_orari : '',
    ricorrenza_testo: m.ricorrenza_testo || '',
    descrizione: m.descrizione || '',
    posteggi: Number.isInteger(m.posteggi) && m.posteggi > 0 ? m.posteggi : null,
    ingresso: typeof m.ingresso === 'string' ? m.ingresso : '',
    consigli: typeof m.consigli === 'string' ? m.consigli : '',
    date: m.date || [],
    prossima_data: getNextDate(m.date),
    confidence: m.confidence ?? 0,
    completezza: m.completezza ?? 0,
    verificato_il: m.verificato_il || '',
    aggiornato_il: m.aggiornato_il || '',
    aggiornamento_ambito: m.aggiornamento_ambito || '',
    importato_il: m.importato_il || '',
    fonte_letta_il: m.fonte_letta_il || '',
    fonte_aggiornata_il: m.fonte_aggiornata_il || '',
    riscontri_campi: Array.isArray(m.riscontri_campi) ? m.riscontri_campi : [],
    conflitti_campi: cleanAddressConflicts(m.conflitti_campi, m),
    eccezioni_calendario: Array.isArray(m.eccezioni_calendario) ? m.eccezioni_calendario : [],
    calendario_fonte: m.calendario_fonte && typeof m.calendario_fonte === 'object'
      && !Array.isArray(m.calendario_fonte) ? m.calendario_fonte : null,
    dettaglio_fonte: m.dettaglio_fonte && typeof m.dettaglio_fonte === 'object'
      && !Array.isArray(m.dettaglio_fonte) ? m.dettaglio_fonte : null,
    evidenza_editoriale: m.evidenza_editoriale && typeof m.evidenza_editoriale === 'object'
      && !Array.isArray(m.evidenza_editoriale) ? m.evidenza_editoriale : null,
    date_quality: m.date_quality || 'prevista',
    position_quality: m.position_quality || 'sconosciuta',
    status: m.status || 'non_confermato',
    concluso: m.concluso || '',
    isEvent: m.isEvent === true,
    fonte: m.fonte || '',
    url_fonte: m.url_fonte || '',
    // Full regional details carry publisher-side safety holds and source
    // evidence. The compact national index intentionally omits them.
    navigazione_sospesa_motivo: m.navigazione_sospesa_motivo || '',
    coordinate_sospese_motivo: m.coordinate_sospese_motivo || '',
    posizione_fonte: m.posizione_fonte && typeof m.posizione_fonte === 'object' ? m.posizione_fonte : null,
    fonti: Array.isArray(m.fonti)
      ? m.fonti.filter(s => s && typeof s.nome === 'string' && typeof s.url === 'string')
      : [],
    distance: Number.isFinite(userLat) && Number.isFinite(userLng)
      && Number.isFinite(lat) && Number.isFinite(lng)
      ? haversine(userLat, userLng, lat, lng) : null,
  }
}

export async function fetchMarkets({ userLat = null, userLng = null } = {}) {
  const { markets, events = null } = await fetchCatalog()
  return markets.map(m => normalize(mergeEventFields(m, events), userLat, userLng))
}

/** Shared links and favourites may name a soft-merged copy: use its kept record. */
export async function canonicalMarketId(id) {
  const { aliases } = await fetchCatalog()
  return aliases.get(id) || id
}

export async function fetchMarketById(requestedId) {
  const { manifest, markets, aliases, concluded } = await fetchCatalog()
  const id = aliases.get(requestedId) || requestedId
  // A concluded market is hidden from lists but still opens from links.
  const summary = markets.find(m => m.slug === id) || concluded?.get(id)
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

// Favourites saved on a soft-merged copy follow it to the kept record.
async function resolvedFavorites() {
  const { aliases } = await fetchCatalog()
  return new Set([...localFavorites()].map(id => aliases.get(id) || id))
}

export async function getFavorites() {
  try {
    return await resolvedFavorites()
  } catch {
    return localFavorites()
  }
}

export async function toggleFavorite(marketId) {
  const favorites = await getFavorites()
  if (favorites.has(marketId)) favorites.delete(marketId)
  else favorites.add(marketId)
  try { localStorage.setItem(FAVORITES_KEY, JSON.stringify([...favorites])) } catch { /* no storage */ }
  return favorites
}
