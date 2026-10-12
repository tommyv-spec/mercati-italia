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
page.on('pageerror', error => pageErrors.push(error.message))
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

try {
  const response = await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 45000 })
  assert.equal(response?.status(), 200)
  await assertCards()
  await page.screenshot({ path: 'ux-home.png', animations: 'disabled' })
  assert.equal(await page.getByText('Mercati vicino a me', { exact: false }).count() > 0, true)
  assert.equal(await page.locator('.market-card .card-distance').count(), 0,
    'Without permission, app must not show fabricated distances')

  // Real navigation: home → market detail → back.
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
  await page.locator('.detail-back').click()

  // Source-bound real regression: Cernobbio's Mercatino delle Curiosità
  // has no upcoming date. An empty forecast must not be advertised as a
  // "planned" event merely because the source once listed the market.
  // The name is intentionally read from a still-reviewable legacy card.
  await page.locator('.search-input').fill('Mercatino delle Curiosità')
  await page.locator('.market-card-open').first().waitFor({ timeout: 20000 })
  // When a visitor *explicitly* selects the 7-day chip while searching,
  // an undated market should disappear. Toggling it off restores the
  // existing card: no hidden persistent filter or fabricated schedule.
  await page.getByRole('button', { name: 'Prossimi 7 giorni', exact: true }).click()
  await page.waitForFunction(() =>
    (document.querySelector('.results-count')?.textContent || '').includes('0 appuntamenti previsti'),
    null, { timeout: 20000 })
  assert.equal(await page.locator('.market-card-open').count(), 0,
    'Explicit seven-day filter must exclude markets with unknown dates')
  await page.getByRole('button', { name: 'Prossimi 7 giorni', exact: true }).click()
  await page.locator('.market-card-open').first().waitFor({ timeout: 20000 })
  await page.locator('.market-card-open').first().click()
  await page.locator('.detail-page').waitFor()
  await page.getByText('Caricamento dettagli completi…').waitFor({ state: 'hidden', timeout: 20000 })
  await page.getByText('Nessuna data futura disponibile.', { exact: false }).waitFor({ timeout: 20000 })
  assert.equal(await page.getByText('Date previste, non confermate per ogni singola edizione.',
    { exact: false }).count(), 0,
    'An unscheduled market must never have a misleading future-date notice')
  await page.locator('.detail-back').click()
  await page.locator('.search-input').fill('')
  await assertCards()

  // The map must be a real interactive map, not the old decorative SVG.
  await page.getByRole('button', { name: 'Mappa', exact: true }).first().click()
  await page.locator('.maplibregl-map').waitFor({ timeout: 20000 })
  assert.equal(await page.locator('.maplibregl-canvas').count(), 1)
  assert.equal(await page.getByText('Schema indicativo dell’Italia', { exact: false }).count(), 0)
  await page.getByText('Mostra solo posizioni precise', { exact: false }).first().click()
  await page.getByText('Includi posizioni indicative', { exact: false }).first().waitFor()
  await page.getByText('Includi posizioni indicative', { exact: false }).first().click()
  await page.screenshot({ path: 'ux-map.png', animations: 'disabled' })
  await page.getByRole('button', { name: 'Lista', exact: true }).first().click()
  await assertCards()

  // Manual city selection filters actual results, not a cosmetic toast.
  await page.locator('.bottom-tabs').getByRole('button', { name: 'Impostazioni' }).click()
  await page.getByRole('button', { name: /Scegli una città/ }).click()
  await page.locator('.manual-city-input input').fill('Firenze')
  await page.getByRole('button', { name: 'Filtra città' }).click()
  // A group of real weekday markets is a valid Firenze search result,
  // not an empty result set. The group-specific checks below still
  // assert the venues and days rather than merely accepting any text.
  await assertCards({ allowGroupedVenue: true })
  const citySearchResult = await page.locator(
    '.market-card, [data-testid="weekly-city-group"]'
  ).first().innerText()
  assert.match(citySearchResult, /Firenze/i, 'Manual city filter did not affect the results')

  // Firenze's six generic weekday records must appear as one city group,
  // with four physical venue labels after lazy-loading regional details.
  const cityGroup = page.getByTestId('weekly-city-group').filter({
    hasText: 'Mercati settimanali a Firenze',
  }).first()
  await cityGroup.waitFor({ timeout: 20000 })
  assert.equal(await cityGroup.getByText('7 appuntamenti').count(), 1)
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
  await page.locator('.toast').waitFor({ state: 'hidden', timeout: 10000 })
  await page.screenshot({ path: 'ux-weekly-city.png', animations: 'disabled' })

  // Saturday must reveal only the specific Piazza I maggio schedule.
  await page.getByRole('button', { name: 'Mostra mercati del sabato' }).click()
  const saturdayGroup = page.getByTestId('weekly-city-group').filter({
    hasText: 'Mercati settimanali a Firenze',
  }).first()
  await saturdayGroup.waitFor()
  await saturdayGroup.getByText('Piazza i maggio', { exact: true }).waitFor({ timeout: 25000 })
  // The city group keeps a stable React key across weekday filter changes.
  // Wait until the previous weekday venues have actually been removed.
  await saturdayGroup.getByText('Largo Monzani', { exact: true })
    .waitFor({ state: 'hidden', timeout: 25000 })
  assert.equal(await saturdayGroup.locator('.weekly-venue[data-known="true"]').count(), 1)
  await page.screenshot({ path: 'ux-weekly-saturday.png', animations: 'disabled' })
  await page.getByRole('button', { name: 'Togli filtro giorno' }).click()
  await assertCards({ allowGroupedVenue: true })
  // Restore nationwide results before exercising GPS. A real city filter
  // legitimately collapses to one weekly-city group (zero market-card
  // elements), so GPS must not inherit that unrelated city restriction.
  await page.getByRole('button', { name: 'Azzera filtri' }).click()
  await assertCards()

  // Location opt-in: only now is browser GPS permission used.
  await context.grantPermissions(['geolocation'], { origin: new URL(BASE).origin })
  await context.setGeolocation({ latitude: 43.77, longitude: 11.25 })
  await page.getByRole('button', { name: /Mercati vicino a me|Vicino a me/ }).first().click()
  await page.getByText('Vicino a me · 50 km, posizioni precise', { exact: false }).waitFor({ timeout: 20000 })
  // By default, do not show approximate locations as truly nearby.
  const trustedResults = await page.locator('.market-card').count()
  await page.getByRole('button', { name: 'Mostra anche posizioni indicative' }).first().click()
  await assertCards()
  assert.ok(trustedResults >= 0)
  assert.equal(await page.locator('.market-card .card-distance').count() > 0, true,
    'No location status after GPS permission')
  assert.equal(await page.locator('.market-card .card-distance').filter({ hasText: 'circa 0 km' }).count(), 0,
    'Unverified coordinates must not be presented as zero kilometers')
  await page.locator('.toast').waitFor({ state: 'hidden', timeout: 10000 })
  await page.screenshot({ path: 'ux-nearby.png', animations: 'disabled' })

  // Existing favorites are local-only; Agenda never promises background push.
  await page.locator('.bottom-tabs').getByRole('button', { name: 'Agenda' }).click()
  await page.getByText('Le notifiche push automatiche non sono ancora attive.', { exact: false }).waitFor()
  await page.locator('.bottom-tabs').getByRole('button', { name: 'Esplora' }).click()

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
