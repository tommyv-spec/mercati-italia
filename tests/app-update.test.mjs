import test from 'node:test'
import assert from 'node:assert/strict'
import { entryScript } from '../src/lib/appUpdate.js'

test('the published version is the hashed entry script, not analytics or the dev server entry', () => {
  const built = `<head><script>if (location.hostname) {}</script>
    <script async src="https://www.googletagmanager.com/gtag/js?id=G-QXT33JZQZ1"></script>
    <script type="module" crossorigin src="/assets/index-B7xQ2kLm.js"></script>
    <link rel="stylesheet" crossorigin href="/assets/index-C1d2e3f4.css"></head>`
  assert.equal(entryScript(built), '/assets/index-B7xQ2kLm.js')
  assert.equal(entryScript('<script type="module" src="/src/main.jsx"></script>'), null)
  assert.equal(entryScript('<!doctype html><title>Errore</title>'), null)
})
