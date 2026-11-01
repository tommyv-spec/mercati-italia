/**
 * Mobile browser smoke test for real visitor actions.
 * Run with: npm install --no-save playwright@1.55.0 && node tests/ui-smoke.mjs
 * Assumes Vite app is running at http://127.0.0.1:5173/.
 */
import { chromium } from 'playwright'
import assert from 'node:assert/strict'
import fs from 'node:fs/promises'

const BASE = process.env.UI_BASE || 'http://127.0.0.1:5173'
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({
  viewport: { width: 390, height: 844 },
  deviceScaleFactor: 1,
  isMobile: true,
  hasTouch: true,
  locale: 'it-IT',
})
// rawgit.hack shows a safety interstitial to new browser visitors.
 // CI opts into this exact public repository by setting the documented
 // prefixed cookie; real visitors see and approve the warning themselves.
if (new URL(BASE).hostname === 'raw.githack.com') {
  await context.addCookies([{
    name: '__Http-phish', value: '1', url: 'https://raw.githack.com/',
    secure: true, httpOnly: true, sameSite: 'Lax',
  }])
}
const page = await context.newPage()
const remoteDataRequests = []
const pageErrors = []
const brokenMapAssets = []
page.on('pageerror', error => pageErrors.push(error.message))
page.on('response', response => {
  if (/maplibre-gl-worker|maplibre-gl-shared/i.test(response.url()) && response.status() >= 400) {
    brokenMapAssets.push({ status: response.status(), url: response.url() })
  }
})
page.on('requestfailed', request => {
  if (/maplibre-gl-worker|maplibre-gl-shared/i.test(request.url())) {
    brokenMapAssets.push({ failed: true, url: request.url() })
  }
})
page.on('request', request => {
  const url = request.url()
  if (/firestore\.googleapis\.com|firebaseio\.com|workers\.dev/i.test(url)) {
    remoteDataRequests.push(url)
  }
})

async function assertCards({ allowGroupedVenue = false } = {}) {
  try {
    await page.waitForFunction((acceptGroups) => {
      const count = document.querySelector('.results-count')?.textContent || ''
      const card = document.querySelector('.market-card .card-name')
      const group = document.querySelector('[data-testid="weekly-city-group"]')
      return !!(card || (acceptGroups && group)) &&
        count.length > 0 && !count.includes('Caricamento')
    }, allowGroupedVenue, { timeout: 45000 })
    await page.locator(allowGroupedVenue
      ? '.market-card, [data-testid="weekly-city-group"]' : '.market-card').first()
      .waitFor({ timeout: 45000 })
  } catch (error) {
    const diagnosis = await page.evaluate(() => ({
      url: window.location.href,
      resultsCount: document.querySelector('.results-count')?.textContent || '',
      marketCards: document.querySelectorAll('.market-card').length,
      weeklyGroups: document.querySelectorAll('[data-testid="weekly-city-group"]').length,
      bodyText: document.body?.innerText?.slice(0, 2800) || '',
    }))
    console.error('MOBILE_RESULTS_DIAGNOSTIC', JSON.stringify({
      diagnosis, pageErrors, remoteDataRequests,
    }))
    await page.screenshot({ path: 'ux-smoke-failed-results.png', animations: 'disabled' })
    throw error
  }
}

// Dove and Quando are chosen in sheets opened from the bar at the top of Esplora.
async function chooseWhen(name) {
  await page.getByRole('button', { name: /^Quando/ }).first().click()
  await page.locator('.sheet').waitFor()
  await page.locator('.sheet').getByRole('button', { name }).first().click()
  await page.locator('.sheet').waitFor({ state: 'hidden', timeout: 10000 })
}
async function chooseCity(city) {
  await page.getByRole('button', { name: /^Dove/ }).first().click()
  await page.locator('.sheet').waitFor()
  await page.locator('.manual-city-input input').fill(city)
  await page.getByRole('button', { name: 'Mostra', exact: true }).click()
  await page.locator('.sheet').waitFor({ state: 'hidden', timeout: 10000 })
  await page.getByText(city + ' e dintorni', { exact: false }).first().waitFor({ timeout: 20000 })
}
async function chooseItaly() {
  await page.getByRole('button', { name: /^Dove/ }).first().click()
  await page.locator('.sheet').waitFor()
  await page.locator('.sheet').getByRole('button', { name: /Tutta Italia/ }).click()
  await page.locator('.sheet').waitFor({ state: 'hidden', timeout: 10000 })
}

try {
  const response = await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 45000 })
  assert.equal(response?.status(), 200)
  await assertCards()
  await page.screenshot({ path: 'ux-home.png', animations: 'disabled' })
  assert.equal(await page.getByText('Mercati vicino a me', { exact: false }).count() > 0, true)
  assert.equal(await page.locator('.market-card .card-distance').count(), 0,
    'Without permission, app must not show fabricated distances')

  // Real navigation: Esplora → market page → back, with the phone's Back button too.
  await page.locator('.market-card-open').first().click()
  await page.locator('.detail-page').waitFor()
  await page.getByText('Caricamento dettagli completi…').waitFor({ state: 'hidden', timeout: 20000 })
  await page.screenshot({ path: 'ux-detail.png', animations: 'disabled' })
  assert.equal(await page.getByRole('button', { name: 'Condividi questo mercato' }).count(), 1)
  const displayedAddress = (await page.locator('.detail-address').innerText()).trim().toLowerCase()
  if (['centro', 'centro storico', 'zona centro'].includes(displayedAddress)) {
    const directions = page.getByRole('button', { name: /Indicazioni/ })
    assert.equal(await directions.isDisabled(), true,
      'Vague city-centre text must not create a fake navigation destination')
    const opacity = await directions.evaluate(el => Number(getComputedStyle(el).opacity))
    assert.ok(opacity < 0.7, 'Disabled directions must look disabled to a visitor')
  }
  await page.goBack()
  await page.locator('.detail-page').waitFor({ state: 'hidden', timeout: 10000 })
  assert.equal(new URL(page.url()).origin, new URL(BASE).origin, 'The phone Back button must not leave the app')
  await assertCards()

  // Lifecycle rule: Cernobbio's Mercatino delle Curiosità has no upcoming date and its
  // source shows the edition is over, so it is "concluso": gone from search and lists,
  // never advertised as planned, but a shared link still opens it.
  await page.locator('.search-input').fill('Mercatino delle Curiosità')
  await page.locator('.results-count').waitFor({ timeout: 20000 })
  await page.waitForTimeout(1500)
  assert.equal(await page.locator('.market-card').filter({ hasText: 'Cernobbio' }).count(), 0,
    'A concluded market must leave search results')
  // Search never hides a market for lacking a date, and never invents one:
  // Lombardy's registered sites ("sede da verificare") state no weekday or date.
  await page.locator('.search-input').fill('sede da verificare')
  await page.locator('.market-card-open').first().waitFor({ timeout: 20000 })
  const undatedWhen = await page.locator('.market-card .when').allInnerTexts()
  assert.ok(undatedWhen.length > 0 && undatedWhen.every(text => text.includes('Data da verificare')),
    'Undated markets stay findable and say their date is unknown')
  await page.evaluate(() => {
    window.location.hash = 'mercato=cernobbio-mercatino-delle-curiosita-mercatino-delle-curiosita'
  })
  await page.locator('.detail-page').waitFor({ timeout: 20000 })
  await page.getByText('Caricamento dettagli completi…').waitFor({ state: 'hidden', timeout: 20000 })
  await page.getByText('Non più in programma', { exact: false }).waitFor({ timeout: 20000 })
  await page.getByText('Nessuna data futura disponibile.', { exact: false }).waitFor({ timeout: 20000 })
  // Navigation MUST stay disabled until the venue address is reconciled.
  await page.getByText('La località riportata dalla fonte non identifica con sicurezza un Comune.',
    { exact: false }).waitFor()
  assert.equal(await page.getByRole('button', { name: /Indicazioni/ }).isDisabled(), true,
    'Unreconciled market addresses must never produce navigation directions, even after ISTAT city repair')
  assert.equal(await page.getByText('Date previste, non confermate per ogni singola edizione.',
    { exact: false }).count(), 0,
    'An unscheduled market must never have a misleading future-date notice')
  await page.locator('.detail-back').click()
  await page.locator('.detail-page').waitFor({ state: 'hidden', timeout: 10000 })
  await page.locator('.search-input').fill('')
  await assertCards()

  // An explicit "Prossimi 7 giorni" never shows a market without a known date.
  await chooseWhen('Prossimi 7 giorni')
  await assertCards()
  assert.equal(await page.locator('.market-card .when').filter({ hasText: 'Data da verificare' }).count(), 0,
    'Explicit seven-day choice must exclude markets with unknown dates')

  // The map must be a real interactive map, not the old decorative SVG.
  await page.locator('.bottom-tabs').getByRole('button', { name: 'Mappa', exact: true }).click()
  await page.locator('.maplibregl-map').waitFor({ timeout: 20000 })
  assert.equal(await page.locator('.maplibregl-canvas').count(), 1)
  // A canvas alone is NOT a functioning map: MapLibre v6 previously
  // requested an absent worker (.mjs 404), leaving load() frozen forever.
  await page.locator('[data-map-ready="true"]').waitFor({ timeout: 30000 })
  const mapPoints = await page.locator('[data-map-ready="true"]').getAttribute('data-visible-points')
  assert.ok(Number(mapPoints) > 0, 'MapLibre did not receive market points')
  assert.deepEqual(brokenMapAssets, [], 'MapLibre worker or shared module failed to load')
  assert.equal(await page.getByText('Schema indicativo dell’Italia', { exact: false }).count(), 0)
  await page.getByText('Mostra solo posizioni precise', { exact: false }).first().click()
  await page.getByText('Includi posizioni indicative', { exact: false }).first().waitFor()
  await page.getByText('Includi posizioni indicative', { exact: false }).first().click()
  await page.screenshot({ path: 'ux-map.png', animations: 'disabled' })
  await page.getByRole('button', { name: 'Lista', exact: true }).first().click()
  await assertCards()

  // Choosing a town filters real results, not a cosmetic toast.
  await chooseCity('Firenze')
  await assertCards({ allowGroupedVenue: true })
  assert.match(await page.locator('.results-count').innerText(), /Firenze/, 'The town choice did not reach the results')

  // Firenze's six generic weekday records must appear as one city group,
  // with four physical venue labels after lazy-loading regional details.
  const cityGroup = page.getByTestId('weekly-city-group').filter({
    hasText: 'Mercati settimanali a Firenze',
  }).first()
  await cityGroup.waitFor({ timeout: 20000 })
  assert.equal(await cityGroup.getByText('7 schede').count(), 1)
  await cityGroup.getByRole('button', { name: 'Visualizza sedi e giornate' }).click()
  await cityGroup.getByText('Caricamento sedi…').waitFor({ state: 'hidden', timeout: 25000 })
  await cityGroup.getByText('Largo Monzani', { exact: true }).waitFor()
  assert.equal(await cityGroup.locator('.weekly-venue[data-known="true"]').count(), 4,
    'Firenze weekly listings must be four venues, not six duplicate cards')
  assert.equal(await cityGroup.getByText('Piazza i maggio', { exact: true }).count(), 1)
  assert.equal(await cityGroup.getByRole('button', { name: /1 appuntamento senza sede identificata/ }).count(), 1)
  assert.equal(await cityGroup.locator('.weekly-venue[data-known="false"]').count(), 0)
  await cityGroup.getByRole('button', { name: /1 appuntamento senza sede identificata/ }).click()
  assert.equal(await cityGroup.locator('.weekly-venue[data-known="false"]').count(), 1)
  await cityGroup.getByRole('button', { name: /1 appuntamento senza sede identificata/ }).click()
  await page.screenshot({ path: 'ux-weekly-city.png', animations: 'disabled' })

  // Saturday must reveal only the specific Piazza I maggio schedule.
  await page.getByRole('button', { name: /^Quando/ }).first().click()
  await page.locator('.sheet').waitFor()
  await page.getByRole('button', { name: 'Mostra mercati del sabato' }).click()
  await page.locator('.sheet').waitFor({ state: 'hidden', timeout: 10000 })
  const saturdayGroup = page.getByTestId('weekly-city-group').filter({
    hasText: 'Mercati settimanali a Firenze',
  }).first()
  await saturdayGroup.waitFor()
  await saturdayGroup.getByText('Piazza i maggio', { exact: true }).waitFor({ timeout: 25000 })
  // The city group keeps a stable React key across weekday changes.
  // Wait until the previous weekday venues have actually been removed.
  await saturdayGroup.getByText('Largo Monzani', { exact: true })
    .waitFor({ state: 'hidden', timeout: 25000 })
  assert.equal(await saturdayGroup.locator('.weekly-venue[data-known="true"]').count(), 1)
  await page.screenshot({ path: 'ux-weekly-saturday.png', animations: 'disabled' })
  await chooseWhen('Prossimi 7 giorni')

  // Albizzate: Happings lists ONE Tuesday market (Piazzale Sefro); the three
  // imported copies are soft-merged in the data ("duplicato_di"). The visitor
  // sees one market, and a link shared for a merged copy opens the kept one.
  await chooseCity('Albizzate')
  await assertCards()
  assert.equal(await page.locator('.market-card').filter({ hasText: 'Mercato settimanale' }).count(), 1,
    'Soft-merged copies of one listed market must show as one card')
  assert.equal(await page.getByTestId('weekly-city-group').count(), 0)
  await page.evaluate(() => {
    window.location.hash = 'mercato=mercato-settimanale-di-albizzate-albizzate-martedi'
  })
  await page.locator('.detail-page').filter({ hasText: /Piazzale Sefro/i }).waitFor({ timeout: 20000 })
  await page.screenshot({ path: 'ux-weekly-duplicate-detail.png', animations: 'disabled' })
  await page.locator('.detail-back').click()
  await page.locator('.detail-page').waitFor({ state: 'hidden', timeout: 10000 })
  await chooseItaly()
  await assertCards()

  // Location opt-in: only now is browser GPS permission used.
  await context.grantPermissions(['geolocation'], { origin: new URL(BASE).origin })
  await context.setGeolocation({ latitude: 43.77, longitude: 11.25 })
  await page.getByRole('button', { name: /^Dove/ }).first().click()
  await page.locator('.sheet').waitFor()
  await page.getByRole('button', { name: /Usa la mia posizione/ }).click()
  await page.getByText('Vicino a me · 50 km, posizioni precise', { exact: false }).waitFor({ timeout: 20000 })
  // By default, do not show approximate locations as truly nearby.
  await page.getByRole('button', { name: 'Mostra anche posizioni indicative' }).first().click()
  await assertCards()
  assert.equal(await page.locator('.market-card .card-distance').count() > 0, true,
    'No location status after GPS permission')
  assert.equal(await page.locator('.market-card .card-distance').filter({ hasText: 'circa 0 km' }).count(), 0,
    'Unverified coordinates must not be presented as zero kilometers')
  await page.locator('.toast').waitFor({ state: 'hidden', timeout: 10000 })
  await page.screenshot({ path: 'ux-nearby.png', animations: 'disabled' })

  // Saved markets are local-only; the page never promises background push.
  await page.locator('.bottom-tabs').getByRole('button', { name: 'Salvati' }).click()
  await page.getByText('Le notifiche push automatiche non sono ancora attive.', { exact: false }).waitFor()
  await page.goBack()
  await page.locator('.explore').waitFor({ timeout: 10000 })
  assert.equal(new URL(page.url()).origin, new URL(BASE).origin, 'Back from a tab returns to Esplora')

  await page.screenshot({ path: 'ux-phone.png', fullPage: true, animations: 'disabled' })
  await fs.writeFile('ux-smoke-result.json', JSON.stringify({
    marketCardsFound: await page.locator('.market-card').count(),
    staticOnly: remoteDataRequests.length === 0,
    pageErrors,
    remoteDataRequests,
    viewport: { width: 390, height: 844 },
  }, null, 2))
  assert.deepEqual(remoteDataRequests, [], 'Public visitor must not query a paid database')
  assert.deepEqual(pageErrors, [], 'Browser runtime exceptions')
  console.log('PASS: mobile visitor experience smoke test')
} finally {
  await browser.close()
}
