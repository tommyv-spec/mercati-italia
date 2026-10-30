# Fuori "Rivista" Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Fuori app's screens on the approved "Rivista" design (spec: `docs/superpowers/specs/2026-10-30-fuori-rivista-redesign-design.md`, markup reference: `docs/superpowers/specs/mockup-rivista/Main.dc.html` and `A-Scheda.dc.html`), separating weekly municipal markets from events, without changing the data services or the national index schema.

**Architecture:** `App.jsx` becomes a thin shell (tab, view, open market, filters, position, favourites, hash link) that renders one screen component per tab from `src/screens/`; shared pieces live in `src/ui/`; all CSS moves to `src/styles.css`. A new immutable `data/v1/eventi-{hash}.json` written by `backend/export_static.py` carries the rich fields for non-weekly markets; `staticMarkets.js` merges it into the normalised record and sets `isEvent`.

**Tech Stack:** React 18 + Vite 6 (no router, no state library), maplibre-gl 6.14, node:test unit tests (`node --test tests/*.test.mjs`), Playwright 1.55 UI tests at 390×844 (`tests/ui-smoke.mjs` and three `*-ui.mjs`), Python 3.13 `unittest` for the exporter (`python -m unittest discover -s backend/tests -v`).

**Working rules for every task**
- Work in the clone `C:\Users\tomma\AppData\Local\mercati-italia\ui-upgrade` on branch `improve/data-quality-security-performance-2026-10-11`. Never touch `~/mercati-italia` (PROD).
- Verify = `npx vite build` → `npm run preview -- --host 127.0.0.1 --port 4173 --strictPort` (one server at a time, kill it after) → `UI_BASE=http://127.0.0.1:4173/ node tests/ui-smoke.mjs` plus `node --test tests/*.test.mjs`. Delete the `ux-*.png` / `ux-smoke-result.json` files the smoke test leaves (`git clean -fq -- 'ux-*'`).
- Commit after each task with the trailer `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`. Push only when `%LOCALAPPDATA%\mercati-italia\runner\runner.lock` is absent, after `git fetch` + rebase.
- After each task that changes what the visitor sees: `firebase hosting:channel:deploy dev --project market-ef407 --expires 30d` from the clone (firebase.json is already there, untracked) so the owner can look at https://market-ef407--dev-n0hayy7b.web.app.
- Design rules that must survive every task: no box-shadow cards, no coloured left borders, no emoji in the UI (category icons become stroke SVG or plain text), touch targets ≥ 44 px, terracotta only on links/active tab/"Oggi" eyebrows, olive for "Ingresso gratuito" and "confermato".

---

## File structure

| Path | Responsibility |
|---|---|
| `src/styles.css` (new) | `@import` fonts, `:root` tokens, base, every component class. Replaces the `styles` template string. |
| `src/main.jsx` | adds `import './styles.css'` |
| `src/App.jsx` | shell only: state, data hook, handlers, hash link, toast, tab switch. Target ≤ 700 lines after Task 6. |
| `src/ui/Icon.jsx` (new) | the `Icon` component moved from App.jsx + new icons |
| `src/ui/TabBar.jsx` (new) | bottom tabs |
| `src/ui/SearchField.jsx`, `Pill.jsx`, `Section.jsx`, `EventRow.jsx`, `WeeklyRow.jsx`, `WeekendStepper.jsx`, `Skeleton.jsx`, `FilterSheet.jsx` (new) | shared presentational pieces |
| `src/screens/Home.jsx`, `List.jsx`, `Weekly.jsx`, `Detail.jsx`, `MapScreen.jsx`, `Agenda.jsx`, `More.jsx` (new) | one per screen |
| `src/lib/display.js` (new) | date/label helpers moved from App.jsx (`localISO`, `formatDateIT`, `getDateBadge`, `dateQualityLabel`, `dateLeaf`, `dayHeaderLabel`, `uniqueByName`, `CATEGORY_COLORS`) |
| `src/lib/calendarFile.js` (new) | `downloadCalendarEvent` moved from App.jsx |
| `src/lib/report.js` (new) | `reportUrl` moved from App.jsx |
| `src/lib/cadence.js` (new) | `WEEKLY_TAGS`, `fallbackIsEvent` |
| `src/lib/weekend.js` (new) | `weekendOf`, `inWeekend`, `weekendLabel` |
| `src/services/staticMarkets.js` | loads `manifest.events`, merges rich fields, sets `isEvent` |
| `src/hooks/useMarkets.js` | `adaptMarket` exposes `isEvent` |
| `backend/export_static.py` | events asset + manifest keys |
| `backend/tests/test_export_events.py` (new) | exporter tests |
| `tests/cadence.test.mjs`, `tests/weekend.test.mjs`, `tests/catalog-events.test.mjs` (new) | unit tests |
| `tests/ui-smoke.mjs` | tab names updated in Task 6 |

---

### Task 1: Move styles, icons and helpers out of App.jsx (no visible change)

**Files:**
- Create: `src/styles.css`, `src/ui/Icon.jsx`, `src/lib/display.js`, `src/lib/calendarFile.js`, `src/lib/report.js`
- Modify: `src/App.jsx` (lines 25–135 helpers, 139–175 `Icon`, 176–1572 `styles`, 2962 `<style>{styles}</style>`), `src/main.jsx`

- [ ] **Step 1: Create `src/styles.css`** with the exact content of the template string in `src/App.jsx` lines 177–1571 (everything between the backticks, starting with the `@import url('https://fonts.googleapis.com/css2?...')` line). Do not change a rule yet.

- [ ] **Step 2: Add the import to `src/main.jsx`**

```jsx
import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles.css'
```

- [ ] **Step 3: Create `src/ui/Icon.jsx`** = the `Icon` component from `src/App.jsx` lines 139–175, unchanged, ending with `export default Icon`. Keep every existing icon name. Add these names (24×24 viewBox, stroke paths, same style as the existing ones):

```jsx
search: <><circle cx="11" cy="11" r="7" /><path d="m20 20-3.5-3.5" /></>,
chevronLeft: <path d="m15 6-6 6 6 6" />,
chevronRight: <path d="m9 6 6 6-6 6" />,
bell: <path d="M6 9a6 6 0 0 1 12 0v5l2 3H4l2-3zM10 20a2 2 0 0 0 4 0" />,
bookmark: <path d="M6 3h12a1 1 0 0 1 1 1v17l-7-4-7 4V4a1 1 0 0 1 1-1z" />,
upload: <path d="M12 15V4M7 9l5-5 5 5M5 14v5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-5" />,
pin: <><path d="M12 21s7-6.5 7-12a7 7 0 1 0-14 0c0 5.5 7 12 7 12z" /><circle cx="12" cy="9" r="2.5" /></>,
check: <path d="m5 12 5 5 9-10" />,
mapOutline: <><path d="M3 6l6-2 6 2 6-2v14l-6 2-6-2-6 2z" /><path d="M9 4v14M15 6v14" /></>,
dots: <><circle cx="5" cy="12" r="1.5" /><circle cx="12" cy="12" r="1.5" /><circle cx="19" cy="12" r="1.5" /></>,
```

- [ ] **Step 4: Create `src/lib/display.js`** by moving, verbatim, from `src/App.jsx`: `CATEGORY_COLORS` (line 25), `localISO`, `TODAY`, `todayStr`, `formatDateIT`, `getDateBadge`, `dateQualityLabel`, `dateLeaf`, `dayHeaderLabel`, `getNextDate`, `uniqueByName`. Export each with `export`. `italianKey` is imported from `./marketGrouping.js`.

- [ ] **Step 5: Create `src/lib/calendarFile.js`** = `downloadCalendarEvent` from App.jsx (line 98), `export`ed. Create `src/lib/report.js` = `reportUrl` (line 120), `export`ed.

- [ ] **Step 6: Edit `src/App.jsx`**: delete the moved code and the `haversine` copy (line 126; import `haversine` from `./services/staticMarkets.js`, which already exports it); delete the `styles` string and the `<style>{styles}</style>` line; add

```jsx
import Icon from './ui/Icon.jsx';
import { CATEGORY_COLORS, localISO, TODAY, todayStr, formatDateIT, getDateBadge, dateQualityLabel, dateLeaf, dayHeaderLabel, getNextDate, uniqueByName } from './lib/display.js';
import { downloadCalendarEvent } from './lib/calendarFile.js';
import { reportUrl } from './lib/report.js';
import { haversine } from './services/staticMarkets.js';
```

- [ ] **Step 7: Verify nothing changed**

Run: `npx vite build` → Expected: `✓ built`. Run: `node --test tests/*.test.mjs` → Expected: all pass (89 today). Run the preview + `UI_BASE=http://127.0.0.1:4173/ node tests/ui-smoke.mjs` → Expected: `PASS: mobile visitor experience smoke test`.

- [ ] **Step 8: Commit**

```bash
git add src/styles.css src/main.jsx src/ui/Icon.jsx src/lib/display.js src/lib/calendarFile.js src/lib/report.js src/App.jsx
git commit -m "app: move styles, icon and helpers out of App.jsx (no visible change)"
```

---

### Task 2: Events file (exporter), cadence rule, loader merge

**Files:**
- Modify: `backend/export_static.py` (after `small_index`, and inside `export()`)
- Create: `backend/tests/test_export_events.py`, `src/lib/cadence.js`, `tests/cadence.test.mjs`, `tests/catalog-events.test.mjs`
- Modify: `src/services/staticMarkets.js` (`loadCatalogFromManifest`, `normalize`, `fetchMarkets`), `src/hooks/useMarkets.js` (`adaptMarket`)

- [ ] **Step 1: Write the failing exporter test** `backend/tests/test_export_events.py`

```python
import unittest
from export_static import is_weekly_market, short_description, events_rows, EVENTS_FIELDS


class EventsFileTests(unittest.TestCase):
    def test_weekly_by_rule_or_tag(self):
        self.assertTrue(is_weekly_market({"proiezione_regola": {"kind": "weekly", "weekdays": [2]}}))
        self.assertTrue(is_weekly_market({"tags": ["mercato comunale"]}))
        self.assertTrue(is_weekly_market({"tags": ["MERCAP"]}))
        self.assertFalse(is_weekly_market({"proiezione_regola": {"kind": "monthly_nth_weekday"}, "tags": ["antiquariato"]}))
        self.assertFalse(is_weekly_market({"categoria": "misto"}))

    def test_short_description_cuts_on_sentence_then_word(self):
        self.assertEqual(short_description("Breve."), "Breve.")
        long_text = "Prima frase lunga. " * 10 + "Seconda frase che non entra."
        cut = short_description(long_text, limit=60)
        self.assertTrue(cut.endswith("…"))
        self.assertLessEqual(len(cut), 61)
        self.assertEqual(short_description("a" * 300, limit=240), "a" * 240 + "…")
        self.assertEqual(short_description(None), "")

    def test_events_rows_skip_weekly_concluded_and_merged(self):
        markets = [
            {"slug": "fiera", "indirizzo": "Piazza Grande", "ricorrenza_testo": "primo weekend",
             "descrizione": "Testo.", "ingresso": "Ingresso gratuito", "consigli": "Arriva presto",
             "tags": ["antiquariato"], "proiezione_regola": None},
            {"slug": "weekly", "tags": ["settimanale"]},
            {"slug": "gone", "concluso": "fonte_non_riletta"},
            {"slug": "copy", "duplicato_di": "fiera"},
        ]
        rows = events_rows(markets)
        self.assertEqual(rows, [["fiera", "Piazza Grande", "primo weekend", "Testo.", "Ingresso gratuito", "Arriva presto"]])
        self.assertEqual(EVENTS_FIELDS, ("slug", "indirizzo", "ricorrenza_testo", "descrizione", "ingresso", "consigli"))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run it to see it fail**

Run (from the clone): `python -m unittest backend.tests.test_export_events -v` (if `backend` is not importable that way, run `cd backend && python -m unittest tests.test_export_events -v`; match how the other `backend/tests/test_*.py` import `export_static`). Expected: `ImportError: cannot import name 'is_weekly_market'`.

- [ ] **Step 3: Implement in `backend/export_static.py`** right after `small_index`:

```python
# Rich fields for the non-weekly markets only ("eventi"): the national index stays
# small; the home shows address, cadence, a short description, entry and tips
# without downloading a 10 MB regional file.
EVENTS_SCHEMA = 1
EVENTS_FIELDS = ("slug", "indirizzo", "ricorrenza_testo", "descrizione", "ingresso", "consigli")
WEEKLY_TAGS = {"settimanale", "mercato settimanale", "mercato comunale", "MERCAP"}


def is_weekly_market(market: dict) -> bool:
    rule = market.get("proiezione_regola")
    if isinstance(rule, dict) and rule.get("kind") == "weekly":
        return True
    return bool(WEEKLY_TAGS & set(market.get("tags") or []))


def short_description(text, limit: int = 240) -> str:
    text = " ".join(str(text or "").split())
    if len(text) <= limit:
        return text
    cut = text[:limit]
    sentence = max(cut.rfind(". "), cut.rfind("! "), cut.rfind("? "))
    if sentence >= limit // 2:
        return cut[:sentence + 1] + "…"
    word = cut.rfind(" ")
    if word >= limit // 2:
        return cut[:word] + "…"
    return cut + "…"


def events_rows(markets: list[dict]) -> list[list]:
    rows = []
    for market in markets:
        if market.get("concluso") or market.get("duplicato_di") or is_weekly_market(market):
            continue
        rows.append([
            market.get("slug") or "",
            str(market.get("indirizzo") or ""),
            str(market.get("ricorrenza_testo") or ""),
            short_description(market.get("descrizione")),
            str(market.get("ingresso") or ""),
            str(market.get("consigli") or ""),
        ])
    return rows
```

In `export()`:
1. In the "unchanged" condition add `and previous.get("events") and (out.parent.parent / previous["events"]).is_file()` before the final `):`.
2. After `index_path = _write_asset(...)` add `events_path = _write_asset(out, "eventi-{hash}.json", events_rows(markets))`.
3. In `manifest` add `"events": events_path, "events_schema": EVENTS_SCHEMA,` after `"index_schema": INDEX_SCHEMA,`.

- [ ] **Step 4: Run the exporter tests** → Expected: 3 tests OK. Run the whole backend suite `python -m unittest discover -s backend/tests -v` → Expected: everything that passed before still passes.

- [ ] **Step 5: Write the failing JS tests**

`tests/cadence.test.mjs`:
```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { fallbackIsEvent, WEEKLY_TAGS } from '../src/lib/cadence.js'

test('fallback: weekly tags and misto are weekly, the rest are events', () => {
  assert.equal(fallbackIsEvent({ categoria: 'antiquariato', tags: [] }), true)
  assert.equal(fallbackIsEvent({ categoria: 'misto', tags: [] }), false)
  assert.equal(fallbackIsEvent({ categoria: 'alimentare', tags: ['mercato comunale'] }), false)
  assert.equal(fallbackIsEvent({ categoria: 'alimentare', tags: ['MERCAP'] }), false)
  assert.equal(fallbackIsEvent({ categoria: 'usato', tags: ['vintage'] }), true)
  assert.ok(WEEKLY_TAGS.has('settimanale'))
})
```

`tests/catalog-events.test.mjs`:
```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { decodeEventRows, mergeEventFields } from '../src/services/staticMarkets.js'

const rows = [['fiera', 'Piazza Grande', 'primo weekend del mese', 'Testo breve.', 'Ingresso gratuito', 'Arriva presto']]

test('decodeEventRows builds a slug map and rejects bad rows', () => {
  const map = decodeEventRows({ schema: 1, markets: rows })
  assert.equal(map.get('fiera').indirizzo, 'Piazza Grande')
  assert.equal(map.get('fiera').consigli, 'Arriva presto')
  assert.equal(decodeEventRows({ schema: 2, markets: rows }), null)
  assert.equal(decodeEventRows({ schema: 1, markets: [['x', 'only-two']] }), null)
})

test('mergeEventFields fills missing fields and flags events; fallback without a map', () => {
  const events = decodeEventRows({ schema: 1, markets: rows })
  const merged = mergeEventFields({ slug: 'fiera', categoria: 'antiquariato', tags: [], indirizzo: '' }, events)
  assert.equal(merged.isEvent, true)
  assert.equal(merged.indirizzo, 'Piazza Grande')
  assert.equal(merged.descrizione, 'Testo breve.')
  const weekly = mergeEventFields({ slug: 'w', categoria: 'misto', tags: ['settimanale'] }, events)
  assert.equal(weekly.isEvent, false)
  assert.equal(mergeEventFields({ slug: 'fiera', categoria: 'antiquariato', tags: [] }, null).isEvent, true)
  assert.equal(mergeEventFields({ slug: 'w', categoria: 'misto', tags: [] }, null).isEvent, false)
})
```

Run: `node --test tests/cadence.test.mjs tests/catalog-events.test.mjs` → Expected: FAIL (module/export missing).

- [ ] **Step 6: Create `src/lib/cadence.js`**

```js
// Weekly municipal market vs event. The exporter decides with the projection rule;
// the app only has to trust the events file. Without it, tags and category decide.
export const WEEKLY_TAGS = new Set(['settimanale', 'mercato settimanale', 'mercato comunale', 'MERCAP'])

export function fallbackIsEvent(record) {
  if ((record.tags || []).some(tag => WEEKLY_TAGS.has(tag))) return false
  return (record.categoria || 'misto') !== 'misto'
}
```

- [ ] **Step 7: Edit `src/services/staticMarkets.js`**

Add after `decodeIndexRecords`:
```js
const EVENT_FIELDS = ['indirizzo', 'ricorrenza_testo', 'descrizione', 'ingresso', 'consigli']

// data/v1/eventi-{hash}.json → Map(slug → rich fields). null when the file is unusable.
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
```
with `import { fallbackIsEvent } from '../lib/cadence.js'` at the top.

In `loadCatalogFromManifest`, in the `if (manifest.index)` branch, after `const markets = decodeIndexRecords(index.markets, manifest)`:
```js
    let events = null
    if (typeof manifest.events === 'string' && manifest.events_schema === 1) {
      events = decodeEventRows(await loadJSON(manifest.events, true).catch(() => null))
    }
```
and return `{ manifest, events, ...splitDuplicates(markets) }`. In `fetchMarkets`:
```js
export async function fetchMarkets({ userLat = null, userLng = null } = {}) {
  const { markets, events = null } = await fetchCatalog()
  return markets.map(m => normalize(mergeEventFields(m, events), userLat, userLng))
}
```
In `normalize` add `isEvent: m.isEvent === true,` next to `concluso`.

In `src/hooks/useMarkets.js` `adaptMarket` add `isEvent: m.isEvent === true,` after `tags`.

- [ ] **Step 8: Run all unit tests** `node --test tests/*.test.mjs` → Expected: all pass, including the two new files.

- [ ] **Step 9: Local events file for the preview (not committed).** The nightly export will write `public/data/v1/eventi-*.json` on DEV. Until then, after every `npx vite build`, generate it into `dist/` from the regional files with this scratch script saved OUTSIDE the repo (scratchpad `make_events_local.py`):

```python
import glob, hashlib, json, sys
sys.path.insert(0, 'backend')
from export_static import events_rows, compact_json, EVENTS_SCHEMA
root = 'dist/data/v1'
markets = [m for f in glob.glob(root + '/regions/*.json') for m in json.load(open(f, encoding='utf-8'))['markets']]
manifest = json.load(open(root + '/manifest.json', encoding='utf-8'))
listed = {r['path'] for r in manifest.get('regions', [])}
markets = [m for f in glob.glob(root + '/regions/*.json') if ('data/v1/' + f.replace('\\', '/').split('data/v1/')[1]) in listed
           for m in json.load(open(f, encoding='utf-8'))['markets']]
body = compact_json({'schema': 1, 'markets': events_rows(markets)})
digest = hashlib.sha256(body).hexdigest()[:14]
open(f'{root}/eventi-{digest}.json', 'wb').write(body)
manifest['events'] = f'data/v1/eventi-{digest}.json'; manifest['events_schema'] = EVENTS_SCHEMA
open(root + '/manifest.json', 'wb').write(compact_json(manifest))
print('events rows', len(events_rows(markets)), 'bytes', len(body))
```
Run: `python -I -X utf8 <scratchpad>/make_events_local.py` from the clone. Expected: about 1,800 rows, under 800 KB. Serve `dist/` and check in the browser console that `fetchMarkets` records have `isEvent`.

- [ ] **Step 10: Verify + commit**

Build, unit tests, smoke test (unchanged UI, must still pass). Commit:
```bash
git add backend/export_static.py backend/tests/test_export_events.py src/lib/cadence.js src/services/staticMarkets.js src/hooks/useMarkets.js tests/cadence.test.mjs tests/catalog-events.test.mjs
git commit -m "catalog: events file with address, cadence, description, entry and tips for non-weekly markets"
```

---

### Task 3: Home screen

**Files:**
- Create: `src/lib/weekend.js`, `tests/weekend.test.mjs`, `src/ui/SearchField.jsx`, `src/ui/Pill.jsx`, `src/ui/Section.jsx`, `src/ui/EventRow.jsx`, `src/ui/WeeklyRow.jsx`, `src/ui/WeekendStepper.jsx`, `src/ui/Skeleton.jsx`, `src/screens/Home.jsx`
- Modify: `src/styles.css` (tokens + new classes), `src/App.jsx` (view state, handlers, render)

- [ ] **Step 1: Failing test `tests/weekend.test.mjs`**

```js
import test from 'node:test'
import assert from 'node:assert/strict'
import { weekendOf, inWeekend } from '../src/lib/weekend.js'

const d = s => new Date(s + 'T12:00:00')

test('this weekend is the coming Saturday+Sunday, or the current one on Sat/Sun', () => {
  assert.deepEqual([weekendOf(d('2026-10-30')).sat, weekendOf(d('2026-10-30')).sun], ['2026-10-31', '2026-11-01'])
  assert.equal(weekendOf(d('2026-10-31')).sat, '2026-10-31')
  assert.equal(weekendOf(d('2026-11-01')).sat, '2026-10-31')
  assert.equal(weekendOf(d('2026-11-02')).sat, '2026-11-07')
})

test('offset moves whole weekends and labels them', () => {
  const next = weekendOf(d('2026-10-30'), 1)
  assert.deepEqual([next.sat, next.sun], ['2026-11-07', '2026-11-08'])
  assert.equal(weekendOf(d('2026-10-30')).label, 'Questo weekend')
  assert.equal(next.label, 'Prossimo weekend')
  assert.equal(weekendOf(d('2026-10-30'), 2).label, 'Weekend del 14 novembre')
  assert.equal(weekendOf(d('2026-10-30')).sub, 'sabato 31 ottobre · domenica 1 novembre')
})

test('inWeekend checks either day', () => {
  const w = weekendOf(d('2026-10-30'))
  assert.equal(inWeekend(['2026-11-01'], w), true)
  assert.equal(inWeekend(['2026-11-03'], w), false)
})
```

- [ ] **Step 2: Create `src/lib/weekend.js`**

```js
import { localISO } from './display.js'

const longDay = date => date.toLocaleDateString('it-IT', { weekday: 'long' })
const dayMonth = date => date.getDate() + ' ' + date.toLocaleDateString('it-IT', { month: 'long' })

// Saturday+Sunday that contains `now` when it is Sat/Sun, else the coming one; `offset` weekends later.
export function weekendOf(now = new Date(), offset = 0) {
  const base = new Date(now); base.setHours(12, 0, 0, 0)
  const day = base.getDay()
  const sat = new Date(base)
  sat.setDate(base.getDate() + (day === 0 ? -1 : 6 - day) + offset * 7)
  const sun = new Date(sat); sun.setDate(sat.getDate() + 1)
  const label = offset === 0 ? 'Questo weekend' : offset === 1 ? 'Prossimo weekend' : 'Weekend del ' + dayMonth(sat)
  return { sat: localISO(sat), sun: localISO(sun), label, sub: longDay(sat) + ' ' + dayMonth(sat) + ' · ' + longDay(sun) + ' ' + dayMonth(sun) }
}

export function inWeekend(dates = [], weekend) {
  return dates.includes(weekend.sat) || dates.includes(weekend.sun)
}
```
Run `node --test tests/weekend.test.mjs` → Expected: 3 pass.

- [ ] **Step 3: Tokens and component CSS in `src/styles.css`.** Replace the `:root` block values with the spec tokens and append the classes used by the new components (the exact pixel values are in `docs/superpowers/specs/mockup-rivista/Main.dc.html`; copy them, converting inline styles to these classes):

```css
:root {
  --cream: #FDFBF7; --beige: #F5F0E8; --beige-dark: #E8E0D4; --sand: #D4C5A9;
  --ink: #2C2416; --ink-light: #5C513F; --ink-lighter: #6C6255;
  --terracotta: #B94439; --terracotta-dark: #8F342C; --olive: #446E47; --olive-pale: #E8F0E9;
  --white: #FFFFFF; --radius-md: 12px; --radius-lg: 16px;
  --font-display: 'DM Serif Display', Georgia, serif; --font-body: 'Source Sans 3', -apple-system, sans-serif;
  --tab-h: 64px;
}
.band { background: var(--ink); color: var(--cream); padding: 18px 20px 22px; display: flex; flex-direction: column; gap: 16px; }
.band .wordmark { font-family: var(--font-display); font-size: 30px; line-height: 1; }
.eyebrow { font-size: 11px; font-weight: 600; letter-spacing: .08em; text-transform: uppercase; color: var(--ink-lighter); }
.band .eyebrow { color: var(--sand); }
.search-field { display: flex; align-items: center; gap: 10px; background: var(--cream); border-radius: var(--radius-md); height: 46px; padding: 0 14px; color: var(--ink-lighter); }
.search-field input { flex: 1; border: 0; background: transparent; font: inherit; font-size: 15px; color: var(--ink); outline: none; min-width: 0; }
.stepper { display: flex; align-items: center; justify-content: space-between; gap: 8px; }
.stepper button { width: 44px; height: 44px; border: 1px solid var(--ink-light); border-radius: 999px; background: transparent; color: var(--cream); display: inline-flex; align-items: center; justify-content: center; }
.stepper button:disabled { opacity: .35; }
.stepper .label { font-family: var(--font-display); font-size: 26px; line-height: 1.1; text-align: center; }
.stepper .sub { font-size: 13px; color: var(--sand); text-align: center; display: block; }
.band .stat { display: flex; justify-content: center; gap: 6px; font-size: 13px; color: var(--sand); flex-wrap: wrap; }
.band .stat a, .band .stat button { color: var(--cream); font-weight: 600; background: none; border: 0; font: inherit; font-size: 13px; padding: 0; min-height: 24px; }
.pill-row { display: flex; gap: 8px; padding: 16px 20px 6px; overflow-x: auto; scrollbar-width: none; }
.pill { display: inline-flex; align-items: center; height: 36px; padding: 0 14px; border: 1px solid var(--sand); border-radius: 999px; font-size: 14px; font-weight: 500; color: var(--ink); background: var(--white); white-space: nowrap; }
.pill.active { background: var(--ink); color: var(--cream); border-color: var(--ink); }
.section { padding: 10px 20px 0; }
.section-head { display: flex; align-items: baseline; justify-content: space-between; padding: 8px 0 10px; }
.section-head h2 { font-family: var(--font-display); font-weight: 400; font-size: 22px; margin: 0; }
.section-head a, .section-head button { font-size: 13px; font-weight: 600; color: var(--terracotta); background: none; border: 0; font: inherit; padding: 0; min-height: 24px; }
.market-card.event-row { display: flex; flex-direction: column; gap: 6px; padding: 16px 0; border-top: 1px solid var(--beige-dark); background: none; box-shadow: none; border-radius: 0; margin: 0; }
.event-row .card-name { font-family: var(--font-display); font-size: 21px; line-height: 1.2; color: var(--ink); margin: 0; font-weight: 400; }
.event-row .meta { font-size: 14px; line-height: 1.4; color: var(--ink); margin: 0; }
.event-row .desc { font-size: 14px; line-height: 1.45; color: var(--ink-light); margin: 0; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }
.event-row .foot { display: flex; align-items: center; gap: 8px; font-size: 12px; color: var(--ink-lighter); flex-wrap: wrap; }
.tag { padding: 2px 8px; border: 1px solid var(--beige-dark); border-radius: 999px; }
.ok { display: inline-flex; align-items: center; gap: 4px; color: var(--olive); font-weight: 600; }
.free { color: var(--olive); font-weight: 600; }
.weekly-box { background: var(--beige); border-radius: 14px; padding: 6px 16px; }
.weekly-row { display: flex; justify-content: space-between; align-items: center; min-height: 44px; padding: 8px 0; border-bottom: 1px solid var(--beige-dark); color: var(--ink); font-size: 15px; background: none; border-left: 0; border-right: 0; border-top: 0; width: 100%; font-family: inherit; text-align: left; }
.weekly-row:last-of-type { border-bottom: 0; }
.weekly-row .name { font-weight: 600; } .weekly-row .hours { color: var(--ink-lighter); }
.region-grid { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); column-gap: 24px; }
.region-link { display: block; padding: 11px 0; border-bottom: 1px solid var(--beige-dark); font-size: 15px; color: var(--ink); background: none; border-left: 0; border-right: 0; border-top: 0; text-align: left; width: 100%; font-family: inherit; }
.skeleton-row { height: 96px; margin: 12px 0; border-radius: 8px; background: linear-gradient(90deg, var(--beige) 25%, var(--beige-dark) 50%, var(--beige) 75%); background-size: 200% 100%; animation: shimmer 1.2s infinite; }
@keyframes shimmer { to { background-position: -200% 0; } }
.empty { padding: 28px 0; text-align: center; color: var(--ink-light); font-size: 15px; }
```
Delete the old `.card-row`, `.card-date*`, `.card-eyebrow`, `.card-status*`, `.card-hours`, `.market-card` box/shadow/left-border rules and `.header`, `.toolbar`, `.chip*` rules that the new components no longer use (grep each class in `src/` before deleting; keep any still used by `List` until Task 4 replaces them).

- [ ] **Step 4: Create the UI pieces** (all plain function components, props only):

`src/ui/SearchField.jsx`:
```jsx
import Icon from './Icon.jsx'
export default function SearchField({ value, onChange, onSubmit, autoFocus = false }) {
  return (
    <label className="search-field">
      <Icon name="search" size={18} />
      <span className="sr-only">Cerca</span>
      <input className="search-input" type="search" value={value} autoFocus={autoFocus}
        placeholder="Cerca città, mercatino o regione"
        onChange={e => onChange(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter' && onSubmit) onSubmit() }} />
    </label>
  )
}
```
(add `.sr-only { position:absolute; width:1px; height:1px; overflow:hidden; clip:rect(0 0 0 0); }` to styles.css.)

`src/ui/Pill.jsx`: `<button type="button" className={'pill' + (active ? ' active' : '')} onClick={onClick}>{children}</button>`.

`src/ui/Section.jsx`: `({ title, aside, children, id })` → `<section className="section" id={id}><div className="section-head"><h2>{title}</h2>{aside}</div>{children}</section>`.

`src/ui/WeekendStepper.jsx`: `({ weekend, offset, onChange })` → `.stepper` with two 44 px buttons (`aria-label="Weekend precedente"`, disabled when `offset === 0`; `aria-label="Weekend successivo"`, disabled when `offset >= 8`), centre `.label` = `weekend.label`, `.sub` = `weekend.sub`.

`src/ui/Skeleton.jsx`: `({ rows = 4 })` → `rows` × `<div className="skeleton-row" aria-hidden="true" />`.

`src/ui/EventRow.jsx` (Home and List share it; keeps the test contract `.market-card`, `.card-name`, `.card-city`, `.card-distance`, `.market-card-open`):
```jsx
import Icon from './Icon.jsx'
import { getDateBadge, dateQualityLabel } from '../lib/display.js'

const DAY = s => { const d = new Date(s + 'T00:00:00'); return d.toLocaleDateString('it-IT', { weekday: 'short' }) + ' ' + d.getDate() + ' ' + d.toLocaleDateString('it-IT', { month: 'short' }) }

export default function EventRow({ market, nextDate, onOpen, onToggleFav, isFav }) {
  const badge = getDateBadge(market.dates)
  const when = nextDate ? DAY(nextDate) : 'Data da verificare'
  const confirmed = market.dateQuality === 'confermata' || market.dateQuality === 'riportata'
  return (
    <article className="market-card event-row">
      <span className="eyebrow">
        {badge && <span style={{ color: 'var(--terracotta)' }}>{badge.label} · </span>}
        {when} · <span className="card-city">{market.city}</span>{market.region ? ' · ' + market.region : ''}
      </span>
      <button type="button" className="market-card-open" onClick={() => onOpen(market)}>
        <h3 className="card-name">{market.name}</h3>
      </button>
      <p className="meta">
        {[market.address, market.hours].filter(Boolean).join(' · ')}
        {market.entry && <> · <span className="free">{market.entry}</span></>}
        {Number.isFinite(market.distance) && market.distance >= 0.5 && <span className="card-distance"> · circa {Math.round(market.distance)} km</span>}
      </p>
      {market.description && <p className="desc">{market.description}</p>}
      <div className="foot">
        {confirmed ? <span className="ok"><Icon name="check" size={14} strokeWidth={2.5} />Data confermata dalla fonte</span>
                   : <span>{dateQualityLabel(market.dateQuality)}</span>}
        {market.tags.slice(0, 2).map(t => <span key={t} className="tag">{t}</span>)}
        <button type="button" className="fav-btn" aria-label={isFav ? 'Togli dall\u2019agenda' : 'Salva in agenda'} onClick={() => onToggleFav(market.id)}><Icon name="bookmark" size={18} /></button>
      </div>
    </article>
  )
}
```
Keep the existing `.card-distance` rule: it is rendered only when `distance` is a finite number (no position → no element) and never for < 0.5 km, which preserves the "never 'circa 0 km'" assertion. Reuse the existing `market-card-open` styling reset (a `button` with no border/background, text left).

`src/ui/WeeklyRow.jsx`: `({ market, onOpen })` → `<button type="button" className="weekly-row market-card-open" onClick={() => onOpen(market)}><span className="name">{market.name}</span><span className="hours">{market.hours}</span></button>`.

- [ ] **Step 5: Create `src/screens/Home.jsx`**

Props: `{ markets, loading, error, onRetry, query, onQuery, onSearchSubmit, weekendOffset, onWeekend, onSeeAll, onCategory, onRegion, onNearby, positionLabel, cityForToday, onWeeklyCity, onOpen, favorites, onToggleFav, userLat, userLng }`.
Content, top to bottom (markup from `Main.dc.html`):
1. `<div className="band">`: wordmark row (`Fuori` + eyebrow `Mercatini d'Italia`), `<SearchField>`, `<WeekendStepper>`, `.stat` line: `<span className="results-count"><strong>{events.length}</strong> mercatini ed eventi in Italia</span>` and `<button onClick={onNearby}>Mercati vicino a me</button>` (that visible text is pinned by the smoke test). When `userLat` is set, the stat reads `… vicino a te` and the button reads `Tutta Italia`.
2. `.pill-row` with `Antiquariato`, `Vintage e usato`, `Artigianato`, `Alimentare` → `onCategory(label)`; `Settimanali` → `onCategory('Misto')`.
3. `<Section title={weekend.label} aside={<button onClick={onSeeAll}>Vedi tutti i {events.length} ›</button>}>`: `loading` → `<Skeleton />`; `error` → `.empty` with text `Catalogo non raggiungibile.` and a `Riprova` button; no events → `.empty` `Nessun evento in programma questo weekend. Prova il prossimo.`; else first 8 `events` as `<EventRow>` (`nextDate` = the weekend day the market has: `market.dates.includes(w.sat) ? w.sat : w.sun`). `events` = `markets.filter(m => m.isEvent && !m.concluded && inWeekend(m.dates, weekend))`, sorted by distance when `userLat` is set (≤ 50 km only), else by `dateQuality` (`riportata`/`confermata` first) then name.
4. `<Section title="Il mercato oggi" aside={<span className="eyebrow">{todayLabel} · {cityForToday || 'scegli una città'}</span>}>`: `today = markets.filter(m => !m.isEvent && !m.concluded && m.dates.includes(todayStr) && (cityForToday ? italianKey(m.city) === italianKey(cityForToday) : false))`; with a city: `.weekly-box` with up to 3 `<WeeklyRow>` and `<button className="section-head-link" onClick={() => onWeeklyCity(cityForToday)}>Tutti i {today.length} mercati di oggi a {cityForToday} ›</button>`; without a city: `.empty` text `Scegli la tua città per vedere i mercati settimanali aperti oggi.` + button `Scegli una città` → `onNearby`.
5. `<Section title="Per regione">`: `.region-grid` of the 10 regions with most events (count events per `m.region`), each `<button className="region-link" onClick={() => onRegion(name)}>{name}</button>`, then `Tutte le 20 regioni ›` → `onRegion('')` + `onSeeAll()`.
Add `padding-bottom: calc(var(--tab-h) + 24px)` on the Home root.

- [ ] **Step 6: Wire `src/App.jsx`**

Add state `const [view, setView] = useState('home')` (`'home' | 'list' | 'weekly'`), `const [weekendOffset, setWeekendOffset] = useState(0)`, `const [weeklyCity, setWeeklyCity] = useState('')`. `cityForToday` = `manualCity || (positionCity from the nearest market when userLat is set) || ''` (reuse what the current nearby/city code already derives; if nothing exists, nearest market's `city` among `positionQuality === 'precisa'` within 15 km).
Handlers:
- `onQuery(q)`: `setSearchQuery(q); if (q) setView('list')`.
- `onCategory(label)`: `setCategoryQuick(label)` (existing) + `setView('list')`.
- `onRegion(name)`: `setFilterRegion(name)`, recompute `activeFilterCount`, `setView('list')`.
- `onSeeAll()`: `setDateFilter('weekend'); setDateFilterExplicit(true); setView('list')`. Make the existing `'weekend'` date filter use `weekendOf(TODAY, weekendOffset)` instead of the fixed coming weekend (find where `dateFilter === 'weekend'` is evaluated; replace the sat/sun computation with `inWeekend(market.dates, weekendOf(TODAY, weekendOffset))`).
- `onWeeklyCity(city)`: `setWeeklyCity(city); setView('weekly')` (the Weekly screen arrives in Task 4; until then route to `showCity(city)` + `setView('list')`).
- `onNearby`: the existing nearby chip handler.
Render: `tab === 'esplora' && view === 'home' ? <Home …/> : tab === 'esplora' && renderExplore()`. `renderExplore` keeps a `← Home` text button at the top of its toolbar that sets `view = 'home'` and clears `searchQuery` when it is the only active filter. Bottom tab `Esplora` click: `setView('home')`.
Hash links (`#mercato=`) keep opening the detail from any view.

- [ ] **Step 7: Verify**

Build; preview; run `make_events_local.py` (Task 2 step 9) so the home has `isEvent`; open http://127.0.0.1:4173/ at 390 px and check: band, 8 event rows with address/description, weekly box, regions. `node --test tests/*.test.mjs` → all pass. `UI_BASE=http://127.0.0.1:4173/ node tests/ui-smoke.mjs` → PASS (on load: `.results-count` text without "Caricamento", `.market-card .card-name`, "Mercati vicino a me", no `.card-distance`; typing in `.search-input` switches to the list). Take `shot-home.png` with Playwright at 390×844 for the owner.

- [ ] **Step 8: Deploy preview + commit**

```bash
firebase hosting:channel:deploy dev --project market-ef407 --expires 30d
git add src/lib/weekend.js tests/weekend.test.mjs src/ui/*.jsx src/screens/Home.jsx src/styles.css src/App.jsx
git commit -m "app: magazine home with weekend events, today's weekly markets by city, regions"
```

---

### Task 4: List screen, filter sheet, weekly-city screen

**Files:**
- Create: `src/screens/List.jsx`, `src/ui/FilterSheet.jsx`, `src/screens/Weekly.jsx`
- Modify: `src/App.jsx` (move `renderExplore`, `renderMarketCard`, the filter panel and sort menu), `src/styles.css`, `src/components/WeeklyCityGroup.css` (tokens only)

- [ ] **Step 1: Create `src/screens/List.jsx`** by moving the JSX of `renderExplore` (the list branch, the toolbar, the active-filter chips, the position note, the controls row, the day headers, the `groupedList` map, the "load more" button) and `renderMarketCard`. Props: every state value and setter it reads (`markets`, `groupedList`, `visibleCount`, `setVisibleCount`, `sortBy`, `setSortBy`, `dateFilter`, `setDateFilter`, `setDateFilterExplicit`, `weekdayFilter`, `setWeekdayFilter`, `filterCategories`, `filterRegion`, `filterCity`, `filterDistance`, `includeEstimatedNearby`, `setIncludeEstimatedNearby`, `activeFilterCount`, `clearFilters`, `query`, `onQuery`, `viewMode`, `setViewMode`, `onOpen`, `favorites`, `onToggleFav`, `userLat`, `userLng`, `positionError`, `positionNote`, `onNearby`, `onHome`, `onOpenFilters`, `resultsLabel`). Replace `renderMarketCard` with `<EventRow>` for `market.isEvent` and `<WeeklyRow>` for the rest (the weekly rows inside the list are grouped under their day header like today).
Top of the screen: the same `.band` as Home but compact (wordmark row + `<SearchField>` only) followed by a `.list-tools` row: `← Home` button (`onHome`), `Oggi`, `Questo weekend`, `Prossimi 7 giorni` pills (exact names kept: the smoke test clicks `Prossimi 7 giorni`), `Filtri (N)` button (`onOpenFilters`), `Ordina` menu as today, and the `Lista` / `Mappa` toggle buttons (exact names kept until Task 6).
Keep: `.results-count`, `Azzera filtri`, `Mostra mercati del sabato` / `Togli filtro giorno`, `Mostra anche posizioni indicative`, the `Vicino a me · 50 km, posizioni precise` note, `[data-testid="weekly-city-group"]` via the unchanged `WeeklyCityGroup`.

- [ ] **Step 2: Create `src/ui/FilterSheet.jsx`** = the current filter panel markup (categories, region select, city input with `Filtra città`, distance slider, `Mostra anche posizioni indicative`, `Azzera filtri`, `Applica`) as a bottom sheet: `.sheet-backdrop` (fixed, rgba(44,36,22,.4)) + `.sheet` (fixed bottom, cream, radius 16px 16px 0 0, max-height 85vh, overflow auto, padding 20px, bottom padding `calc(var(--tab-h) + 20px)`). Weekday chips (`Lun…Dom`, with the pinned `Mostra mercati del sabato` / `Togli filtro giorno` labels) move into the sheet too.

- [ ] **Step 3: Create `src/screens/Weekly.jsx`**: props `{ city, markets, onOpen, onBack }`. Title `Mercati settimanali a {city}`; `rows = markets.filter(m => !m.isEvent && !m.concluded && italianKey(m.city) === italianKey(city))`; group by weekday using `weekdayFromISO(nextDate)` from `marketGrouping.js` (markets with no date go under `Giorno da verificare`), today's group first with the eyebrow `Oggi`; each row `<WeeklyRow>` plus the address under the name when `market.address` is set. Back button `← Home` → `onBack`.

- [ ] **Step 4: Wire `App.jsx`**: `view === 'list'` → `<List …/>`, `view === 'weekly'` → `<Weekly city={weeklyCity} …/>`; `showFilters` → `<FilterSheet …/>`. Delete the moved JSX from `App.jsx`.

- [ ] **Step 5: Styles**: `.list-tools` (flex, gap 8px, padding 12px 20px, overflow-x auto), `.day-header` stays sticky under the compact band (`top: var(--header-h)` measured by the existing `ResizeObserver`), `.sheet*` rules. Replace the hard-coded colours in `src/components/WeeklyCityGroup.css` with the tokens (`var(--beige)`, `var(--beige-dark)`, `var(--ink)`, `var(--terracotta)`), remove its box-shadow if any.

- [ ] **Step 6: Verify** build + unit tests + `ui-smoke.mjs` + `reviewed-city-ui.mjs` + `roma-xiii-2026-venues-ui.mjs` + `roma-xiii-geo-hold-ui.mjs` (all four open the app, search in `.search-input`, click `.market-card-open`, read `.detail-page`, click `.detail-back`). Expected: all PASS. If `ui-smoke.mjs` fails on `Scegli una città` → that flow lives in Impostazioni until Task 6, unchanged.

- [ ] **Step 7: Deploy preview + commit**

```bash
firebase hosting:channel:deploy dev --project market-ef407 --expires 30d
git add src/screens/List.jsx src/screens/Weekly.jsx src/ui/FilterSheet.jsx src/App.jsx src/styles.css src/components/WeeklyCityGroup.css
git commit -m "app: list with sticky day headers and a filter sheet; weekly markets by city"
```

---

### Task 5: Detail screen

**Files:**
- Create: `src/screens/Detail.jsx`
- Modify: `src/App.jsx` (move `renderDetail`, lines ~2058–2650), `src/styles.css`

- [ ] **Step 1: Create `src/screens/Detail.jsx`** by moving `renderDetail` into a component with props `{ market, loading, error, allMarkets, favorites, onToggleFav, onBack, onShare, onOpen, onShowCity, onShowRegion, userLat, userLng }`. Keep every existing computation (summary, futureDates, nearby, sameCity, safety notes, directions disabled rule with its reduced opacity, `Caricamento dettagli completi…`, `Non più in programma`, `Nessuna data futura disponibile.`, `La località riportata dalla fonte non identifica con sicurezza un Comune.`, the `Date previste, non confermate per ogni singola edizione.` note only when dates exist). Re-order the markup to the spec §3.4 using `A-Scheda.dc.html`:
1. `.detail-bar`: `.detail-back` button (`aria-label="Indietro"`, 44 px circle), right: `Condividi questo mercato` (keep this accessible name on the share button: `aria-label="Condividi questo mercato"`) and the bookmark/save button.
2. `.eyebrow`: `{market.category} · {market.recurrence || dateQualityLabel(...)}`.
3. `<h1 className="detail-title">`; `.detail-place`: `<strong>{city}</strong> · {region} · <span className="detail-address">{address}</span>` (the test reads `.detail-address` innerText; keep it the address only).
4. `.next-panel` (beige): eyebrow `Prossima apertura`, `.next-day` (serif 28) = `dayHeaderLabel(nextDate)` without the "Oggi ·" prefix, second line = second weekend day if any + `sourceHoursForDate`, `.ok` line = quality label + `letta il {lastVerified}` when known, buttons: primary `Ricordamelo`/`In agenda` (ink) and secondary `Indicazioni` (the existing disabled logic + `opacity: .5` when disabled), text link `Aggiungi al calendario` → `downloadCalendarEvent`.
5. `.facts` grid 2×2: `Orario`, `Ingresso` (`.free` when it contains "gratuit" or "libero"), `Dove`, and `Posteggi` or `Cadenza` when known.
6. `<details className="source-calendar">` `Tutte le date previste (N)` (existing).
7. Safety notes block (existing texts), then `Il mercato` (description, `Leggi tutto` toggling the 2-line clamp), `Consiglio pratico` card when `market.tips`, `Questo weekend, qui vicino` (existing nearby block renamed; rows `.near` with date leaf + name + sub line + km), tags, provenance line (`Scheda verificata il …`, sources, `Segnala un errore` mailto, `Altri mercatini in {region} ›` → `onShowRegion(region)` and `Vedi tutti i N mercati a {city}` → `onShowCity(city)`).

- [ ] **Step 2: Styles**: `.detail-bar`, `.detail-title` (serif 32/1.1), `.detail-place`, `.next-panel`, `.next-day`, `.btn-primary` (ink bg, cream text, 48 px, radius 12), `.btn-secondary` (white, 1px sand border), `.facts` (grid, `.fact` with eyebrow + 15 px value, hairline top), `.tip` (white, 1px hairline, radius 14), `.near` rows. Remove `.detail-next*`, `.link-row*`, `.detail-lead` rules no longer used.

- [ ] **Step 3: Wire `App.jsx`**: `selectedMarket && <Detail …/>` replaces `renderDetail()`.

- [ ] **Step 4: Verify** build + unit tests + the four UI tests → PASS (they check `.detail-page`, `.detail-back`, `.detail-address`, the share button name, the disabled directions rule, the lifecycle texts). Screenshot the detail at 390 px.

- [ ] **Step 5: Deploy preview + commit**

```bash
firebase hosting:channel:deploy dev --project market-ef407 --expires 30d
git add src/screens/Detail.jsx src/App.jsx src/styles.css
git commit -m "app: market page in magazine order with next opening, facts, tips and nearby"
```

---

### Task 6: Map tab, Agenda, Altro, tab bar

**Files:**
- Create: `src/screens/MapScreen.jsx`, `src/screens/Agenda.jsx`, `src/screens/More.jsx`, `src/ui/TabBar.jsx`
- Modify: `src/App.jsx` (tabs, `renderFavorites`, `renderAgenda`, `renderSettings`, map branch), `src/styles.css`, `tests/ui-smoke.mjs` (lines 163, 221, 256–258)

- [ ] **Step 1: `src/ui/TabBar.jsx`**: `({ tab, onTab })` → `<nav className="bottom-tabs">` with four `<button>`s: `Esplora` (icon compass), `Mappa` (mapOutline), `Agenda` (calendar), `Altro` (dots); active = `.on` (terracotta). Keep the class `bottom-tabs` and the button names (`getByRole('button', { name })`).

- [ ] **Step 2: `src/screens/MapScreen.jsx`**: props `{ markets, userLat, userLng, cityCenter, onlyPrecise, setOnlyPrecise, onSelect, onList }`. Renders the existing `<MarketsMap markets=… userLat userLng onSelect>` (unchanged component; `data-map-ready`/`data-visible-points` stay) with a top bar: `Lista` button (`onList` → tab esplora, view list; keeps the smoke test's `Lista` click) and the toggle button whose label alternates `Mostra solo posizioni precise` / `Includi posizioni indicative` (texts pinned). `markets` passed = events of the selected weekend + weekly markets of today, weekly ones with `muted: true` so `MarketsMap` can draw them grey (add that one optional field to the point builder in `MarketsMap.jsx`; default colour unchanged). Initial centre: `userLat/userLng` → zoom 11; else `cityCenter` (centroid of `cityForToday` markets) → zoom 11; else Italy as today.

- [ ] **Step 3: `src/screens/Agenda.jsx`**: merge `renderFavorites` + `renderAgenda`: title `Agenda`, the note `Le notifiche push automatiche non sono ancora attive.` kept verbatim, groups `Oggi` / `Questo weekend` / `Prossimi` / `Senza data` of saved markets (`favorites` ids → markets, sorted by `nextDate`), each as `<EventRow>` (events) or `<WeeklyRow>` (weekly) plus a `Calendario` text button → `downloadCalendarEvent`. Empty state: `Nessun mercato salvato` + up to 3 `<EventRow>` of this weekend's events under the eyebrow `Da salvare questo weekend`.

- [ ] **Step 4: `src/screens/More.jsx`**: title `Altro`; the position card from `renderSettings` unchanged (`Usa la mia posizione`, `Scegli una città` with `.manual-city-input input` and `Filtra città`, `Non ora`); an `Informazioni` card (three sentences: what Fuori is, data from public sources, static catalogue read for free); a `Segnala un errore` link (`mailto:fuori.mercatini.sagre@gmail.com?subject=Segnalazione%20Fuori%20Mercatini`); footer `Fuori · Mercatini d'Italia · Versione 2.0`.

- [ ] **Step 5: Wire `App.jsx`**: tabs `esplora | mappa | agenda | altro`; remove `preferiti` and `impostazioni` (map `tab === 'impostazioni'` callers to `'altro'`, `'preferiti'` to `'agenda'`); remove the `Lista`/`Mappa` toggle from `List.jsx` (`viewMode` state can go); `<TabBar>` replaces the inline nav. Bottom padding of every screen = `calc(var(--tab-h) + 24px)`.

- [ ] **Step 6: Update `tests/ui-smoke.mjs`**: line 163 and 221 `name: 'Impostazioni'` → `name: 'Altro'`; the map section (lines 145–160) is unchanged in wording (`Mappa` tab button, `.maplibregl-map`, toggle texts, `Lista` button). Agenda assertions (256–258) unchanged.

- [ ] **Step 7: Verify** build, unit tests, all four UI tests → PASS. Screenshots of map, agenda, altro at 390 px.

- [ ] **Step 8: Deploy preview + commit + push**

```bash
firebase hosting:channel:deploy dev --project market-ef407 --expires 30d
git add src/ui/TabBar.jsx src/screens/MapScreen.jsx src/screens/Agenda.jsx src/screens/More.jsx src/components/MarketsMap.jsx src/App.jsx src/styles.css tests/ui-smoke.mjs
git commit -m "app: map tab centred on you, agenda with saved markets, altro with position and info"
# only when %LOCALAPPDATA%\mercati-italia\runner\runner.lock is absent:
git fetch origin improve/data-quality-security-performance-2026-10-11 && git rebase origin/improve/data-quality-security-performance-2026-10-11 && git push origin improve/data-quality-security-performance-2026-10-11
```

---

## Self-review notes

- Spec coverage: §3.1 Task 3, §3.2–3.3 Task 4, §3.4 Task 5, §3.5–3.7 Task 6, §4 Task 2 (+ weekend.js in Task 3), §5 Tasks 1–6, §6 Task 3 tokens + each task's styles, §7 preserved by keeping handlers and texts, §8 is the task order, §9 risk 1 handled by the fallback in Task 2 and the local generation script.
- Names used across tasks: `isEvent` (Task 2 → 3, 4, 6), `EventRow`/`WeeklyRow` (Task 3 → 4, 6), `weekendOf`/`inWeekend` (Task 3 → 3, 6), `view` state values `'home' | 'list' | 'weekly'` (Task 3 → 4), `onWeeklyCity` (Task 3 → 4), `onList` (Task 6).
