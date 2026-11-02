/**
 * The list cards show a date's hours only when the market page shows the same exact
 * hours for that date. Checked on the real catalog in public/data/v1 (every nightly
 * export runs this before publishing): the events file's "orari_date" against the
 * full regional record read by the market page.
 */
import test from 'node:test'
import assert from 'node:assert/strict'
import fs from 'node:fs'
import { decodeIndexRecords, decodeEventRows, mergeEventFields, normalize } from '../src/services/staticMarkets.js'
import { adaptMarket } from '../src/hooks/useMarkets.js'
import { sourceHoursForDate } from '../src/lib/sourceCalendar.js'

const PUBLIC = new URL('../public/', import.meta.url)
const read = path => JSON.parse(fs.readFileSync(new URL(path, PUBLIC)))
const EXACT = /^\d{2}:\d{2}–\d{2}:\d{2}$/
const manifest = fs.existsSync(new URL('data/v1/manifest.json', PUBLIC)) ? read('data/v1/manifest.json') : null

test('list hours equal the market page, date by date, on the real catalog', { skip: manifest?.events_schema !== 2 && 'catalog without per-date hours' }, () => {
  const events = decodeEventRows(read(manifest.events))
  const index = decodeIndexRecords(read(manifest.index).markets, manifest)
  const full = new Map()
  for (const region of manifest.regions || []) for (const record of read(region.path).markets) full.set(record.slug, record)
  let exported = 0, exact = 0
  const wrong = [], missing = []
  for (const row of index) {
    if (!events.has(row.slug) || row.concluso || row.duplicato_di) continue
    // The same steps as the app: list = index row + events file; page = regional record.
    const list = adaptMarket(normalize(mergeEventFields(row, events)))
    const page = adaptMarket(normalize(full.get(row.slug)))
    for (const day of row.date || []) {
      const shown = sourceHoursForDate(list, day), truth = sourceHoursForDate(page, day)
      if (list.dateHours?.[day]) exported++
      if (EXACT.test(truth)) exact++
      if (EXACT.test(shown) && shown !== truth) wrong.push(`${row.slug} ${day}: lista ${shown}, scheda ${truth}`)
      if (EXACT.test(truth) && shown !== truth) missing.push(`${row.slug} ${day}: scheda ${truth}, lista ${shown}`)
    }
  }
  assert.deepEqual(wrong.slice(0, 10), [], 'A card would show hours the market page does not')
  assert.deepEqual(missing.slice(0, 10), [], 'The page knows exact hours the card does not show')
  assert.ok(exported > 0 && exact > 0)
})
