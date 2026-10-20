import test from 'node:test'
import assert from 'node:assert/strict'
import { CATALOG_CHECK_INTERVAL_MS, shouldRevalidateCatalog } from '../src/services/staticMarkets.js'

const PERIOD = CATALOG_CHECK_INTERVAL_MS
const START = Date.UTC(2026, 9, 20, 19, 32)

test('static catalog revalidation checks at most every thirty minutes and ignores a clock rollback', () => {
  assert.equal(shouldRevalidateCatalog(START, START + 60_000), false)
  assert.equal(shouldRevalidateCatalog(START, START + PERIOD), true)
  assert.equal(shouldRevalidateCatalog(START, START - PERIOD), false)
  assert.equal(shouldRevalidateCatalog(START, NaN), false)
  assert.equal(shouldRevalidateCatalog(START, Infinity), false)
})

test('a shared manifest bucket defeats a stale CDN while hashed assets and the working catalog stay coherent', async () => {
  const originalFetch = globalThis.fetch
  const originalNow = Date.now
  Date.now = () => START
  const requests = []
  let revision = 1, failIndex = false, unsafeIndex = false
  let pauseManifest = null, onManifest = null
  const row = value => ['market-id', 'Mercato versione ' + value, 'Firenze', 'Toscana', 'misto', [],
    43.77, 11.25, 'precisa', '', 'prevista', ['2026-10-25']]
  const manifest = value => ({schema: 1, layout: 'regional', total: 1,
    content_signature: 'sig-' + value,
    index: unsafeIndex ? 'https://untrusted.example/index.json' : `data/v1/index-v${value}.json`,
    regions: [{name: 'Toscana', count: 1, path: `data/v1/regions/toscana-v${value}.json`}],
  })
  const json = payload => ({ok: true, status: 200, json: async () => payload})
  globalThis.fetch = async (value, options = {}) => {
    const url = new URL(value, 'https://catalog.example')
    requests.push({url: String(value), path: url.pathname, search: url.search, cache: options.cache})
    if (url.pathname.endsWith('/manifest.json')) {
      // This models the observed preview: even no-cache at the stable URL
      // gives the old release. Only the shared bucket gets the recent one.
      const result = manifest(url.search ? revision : 0)
      if (onManifest) onManifest()
      if (pauseManifest) await pauseManifest
      return json(result)
    }
    const index = url.pathname.match(/\/index-v(\d+)\.json$/)
    if (index) return failIndex ? {ok: false, status: 503} : json({schema: 1, markets: [row(index[1])]})
    const region = url.pathname.match(/\/toscana-v(\d+)\.json$/)
    if (region) return json({schema: 1, markets: [{slug: 'market-id', nome: row(region[1])[1],
      citta: 'Firenze', regione: 'Toscana', indirizzo: 'Sede versione ' + region[1]}]})
    throw Error('Unexpected static URL: ' + value)
  }
  try {
    const {fetchMarkets, fetchMarketById, revalidateCatalogIfStale} =
      await import('../src/services/staticMarkets.js?cache-bucket-regression')
    assert.equal((await fetchMarkets())[0].nome, 'Mercato versione 1', 'The stable CDN URL would return version 0')
    assert.equal((await fetchMarketById('market-id')).indirizzo, 'Sede versione 1')
    assert.equal(await revalidateCatalogIfStale(START + PERIOD - 1), false)
    assert.equal(requests.filter(item => item.path.endsWith('/manifest.json')).length, 1)

    let releaseManifest
    pauseManifest = new Promise(resolve => { releaseManifest = resolve })
    const manifestStarted = new Promise(resolve => { onManifest = resolve })
    revision = 2
    const first = revalidateCatalogIfStale(START + PERIOD)
    const simultaneous = revalidateCatalogIfStale(START + PERIOD)
    await manifestStarted
    assert.equal(requests.filter(item => item.path.endsWith('/manifest.json')).length, 2,
      'Simultaneous visibility/focus checks share one request')
    assert.equal((await fetchMarkets())[0].nome, 'Mercato versione 1', 'Keep the coherent old catalog until the new index is ready')
    releaseManifest()
    assert.deepEqual(await Promise.all([first, simultaneous]), [true, true])
    pauseManifest = null; onManifest = null
    assert.equal((await fetchMarkets())[0].nome, 'Mercato versione 2')
    assert.equal((await fetchMarketById('market-id')).indirizzo, 'Sede versione 2', 'A new catalog invalidates the regional detail cache')

    const assetCount = requests.filter(item => !item.path.endsWith('/manifest.json')).length
    assert.equal(await revalidateCatalogIfStale(START + 2 * PERIOD), false)
    assert.equal(requests.filter(item => !item.path.endsWith('/manifest.json')).length, assetCount,
      'An unchanged manifest downloads no index or region again')

    revision = 3; failIndex = true
    await assert.rejects(revalidateCatalogIfStale(START + 3 * PERIOD), /503/)
    assert.equal((await fetchMarkets())[0].nome, 'Mercato versione 2')
    assert.equal((await fetchMarketById('market-id')).indirizzo, 'Sede versione 2')
    const afterFailure = requests.length
    assert.equal(await revalidateCatalogIfStale(START + 3 * PERIOD + 1), false)
    assert.equal(await revalidateCatalogIfStale(START + PERIOD), false,
      'A clock rollback must not request an older CDN bucket')
    assert.equal(requests.length, afterFailure, 'Failures and clock rollback do not cause repeated requests')
    failIndex = false
    assert.equal(await revalidateCatalogIfStale(START + 4 * PERIOD), true)
    assert.equal((await fetchMarkets())[0].nome, 'Mercato versione 3')

    revision = 4; unsafeIndex = true
    await assert.rejects(revalidateCatalogIfStale(START + 5 * PERIOD), /Percorso catalogo non valido/)
    assert.equal((await fetchMarkets())[0].nome, 'Mercato versione 3')
    assert.ok(requests.every(item => item.url.startsWith('/data/v1/')), 'Manifest values cannot trigger external requests')
    const manifests = requests.filter(item => item.path.endsWith('/manifest.json'))
    assert.deepEqual(manifests.map(item => item.search), Array.from({length: 6}, (_, index) =>
      '?refresh=' + Math.floor((START + index * PERIOD) / PERIOD)))
    assert.equal(manifests[0].cache, 'default')
    assert.ok(manifests.slice(1).every(item => item.cache === 'no-cache'))
    assert.ok(requests.filter(item => !item.path.endsWith('/manifest.json'))
      .every(item => !item.search && item.cache === 'force-cache'), 'Hashed assets remain immutable and have no query')
  } finally {
    Date.now = originalNow
    globalThis.fetch = originalFetch
  }
})
