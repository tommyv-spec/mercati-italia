import test from 'node:test'
import assert from 'node:assert/strict'
import {
  CATALOG_CHECK_INTERVAL_MS, shouldRevalidateCatalog,
  fetchMarkets, revalidateCatalogIfStale,
} from '../src/services/staticMarkets.js'

test('static catalog revalidation checks at most every thirty minutes', () => {
  assert.equal(shouldRevalidateCatalog(1000, 1000 + 60_000), false)
  assert.equal(shouldRevalidateCatalog(1000, 1000 + CATALOG_CHECK_INTERVAL_MS), true)
  assert.equal(shouldRevalidateCatalog(1000, 999), false)
})

test('a long-open tab fetches a changed manifest and retains data when unchanged', async () => {
  const original = globalThis.fetch
  const requests = []
  let revision = 0
  const marketRow = (name) => [
    'market-id', name, 'Firenze', 'Toscana', 'misto', [],
    43.77, 11.25, 'precisa', '', 'prevista', ['2026-10-17'],
  ]
  const manifest = () => ({
    schema: 1, layout: 'single', total: 1,
    content_signature: revision ? 'sig-new' : 'sig-old',
    index: revision ? 'data/v1/index-new.json' : 'data/v1/index-old.json',
  })
  globalThis.fetch = async (url, options = {}) => {
    requests.push({ url, cache: options.cache })
    if (url.endsWith('manifest.json')) {
      return { ok: true, status: 200, json: async () => manifest() }
    }
    if (url.endsWith('index-old.json')) {
      return { ok: true, status: 200, json: async () => ({
        schema: 1, markets: [marketRow('Mercato originale')],
      }) }
    }
    if (url.endsWith('index-new.json')) {
      return { ok: true, status: 200, json: async () => ({
        schema: 1, markets: [marketRow('Mercato aggiornato')],
      }) }
    }
    throw Error('Unexpected static URL: ' + url)
  }
  try {
    assert.equal((await fetchMarkets())[0].nome, 'Mercato originale')
    const future = Date.now() + CATALOG_CHECK_INTERVAL_MS + 60_000
    assert.equal(await revalidateCatalogIfStale(future), false)
    assert.equal(requests.filter(x => x.url.endsWith('manifest.json')).length, 2)
    revision = 1
    assert.equal(await revalidateCatalogIfStale(future + CATALOG_CHECK_INTERVAL_MS + 1), true)
    assert.equal((await fetchMarkets())[0].nome, 'Mercato aggiornato')
    assert.equal(requests.filter(x => x.url.endsWith('index-new.json')).length, 1)
    assert.equal(requests.filter(x => x.url.endsWith('index-old.json')).length, 1)
    assert.equal(requests.filter(x => x.cache === 'no-cache').length, 2)
  } finally {
    globalThis.fetch = original
  }
})
