/**
 * Fail the deploy if Vite forgets MapLibre v6's separate ESM worker.
 * A map canvas can exist while all vector-market pins remain frozen:
 * the old bundle requested an absent /assets/maplibre-gl-worker.mjs (404).
 */
import fs from 'node:fs'
import path from 'node:path'
import assert from 'node:assert/strict'

const dir = 'dist/assets'
const files = fs.readdirSync(dir)
const workers = files.filter(name => /^maplibre-gl-worker-[\w-]+\.(?:js|mjs)$/.test(name))
assert.equal(workers.length, 1, 'Vite must emit exactly one content-hashed MapLibre worker asset')
const worker = workers[0]
assert.ok(fs.statSync(path.join(dir,worker)).size > 40_000, 'Emitted MapLibre worker is unexpectedly tiny')
const chunks = files.filter(name => /^MarketsMap-[\w-]+\.js$/.test(name))
assert.equal(chunks.length, 1, 'Lazy map JavaScript chunk missing')
const mapChunk = fs.readFileSync(path.join(dir,chunks[0]), 'utf8')
assert.ok(mapChunk.includes(worker), 'MapLibre chunk does not reference emitted Vite worker URL')
assert.ok(!mapChunk.includes('maplibre-gl-worker.mjs?v='),
  'MapLibre still tries to load the unbundled, missing default worker')
const workerContents = fs.readFileSync(path.join(dir, worker), 'utf8')
assert.ok(!/from\s*["']\.\/maplibre-gl-shared\.mjs["']/.test(workerContents),
  'MapLibre worker is not self-contained: sibling shared module missing')
console.log('MAPLIBRE_BUNDLED_WORKER_OK',JSON.stringify({
  filename: worker,
  bytes: fs.statSync(path.join(dir,worker)).size,
  mapChunk: chunks[0]
}))
