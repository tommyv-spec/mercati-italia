/** UI must retain city label AND block wrong directions after manual review. */
import { chromium } from 'playwright'
import assert from 'node:assert/strict'

const base = process.env.UI_BASE || 'http://127.0.0.1:4173/'
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({
  viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true,
  locale: 'it-IT',
})
const page = await context.newPage()
const errors = []
const billed = []
page.on('pageerror', err => errors.push(err.message))
page.on('request', request => {
  if (/firestore\.googleapis\.com|firebaseio\.com|workers\.dev/i.test(request.url()))
    billed.push(request.url())
})

try {
  const response = await page.goto(base, { waitUntil: 'domcontentloaded', timeout: 45000 })
  assert.equal(response?.status(), 200)
  await page.locator('.market-card-open').first().waitFor({ timeout: 30000 })

  for (const item of [
    { search: 'Mercatino delle Curiosità', city: 'Cernobbio', image: 'ux-reviewed-city-cernobbio.png',
      id: 'cernobbio-mercatino-delle-curiosita-mercatino-delle-curiosita' },
    { search: 'Valeggio Contemporanea', city: 'Valeggio sul Mincio', image: 'ux-reviewed-city-valeggio.png',
      id: 'valeggio-sul-mincio-valeggio-contemporanea-valeggio-contemporanea' },
    { search: 'CreativaMente', city: 'Todi', image: 'ux-reviewed-city-todi.png',
      id: 'todi-artigianando-mostra-mercato-della-creativita-giardini-oberdan-artigianando' },
    { search: 'Centro storico di Collalto', city: 'Susegana', image: 'ux-reviewed-city-collalto.png',
      id: 'mercato-settimanale-di-centro-storico-di-collalto-in-provincia-mercato-settimana' },
    { search: 'Stoffaday', city: 'Località da verificare', image: 'ux-reviewed-city-stoffaday.png',
      id: 'mercatini-stoffaday-na' },
  ]) {
    await page.locator('.search-input').fill(item.search)
    const candidate = page.locator('.market-card').filter({ hasText: item.city }).first()
    // A reviewed market that is no longer scheduled ("concluso") leaves search but still
    // opens from its link; the same safety checks apply either way.
    const listed = await candidate.waitFor({ timeout: 8000 }).then(() => true, () => false)
    if (listed) {
      await candidate.getByText(item.city, { exact: true }).waitFor({ timeout: 30000 })
      await candidate.locator('.market-card-open').click()
    } else {
      await page.evaluate(id => { window.location.hash = 'mercato=' + id }, item.id)
    }
    await page.locator('.detail-page').waitFor({ timeout: 15000 })
    if (!listed) {
      await page.getByText('Non più in programma', { exact: false }).waitFor({ timeout: 15000 })
    }
    await page.getByText('Caricamento dettagli completi…').waitFor({
      state: 'hidden', timeout: 20000,
    })
    const actions = page.getByRole('button', { name: /Indicazioni/ }).first()
    assert.equal(await actions.isDisabled(), true,
      'A corrected municipality is not proof of navigable address: ' + item.city)
    await page.getByText(
      'Le indicazioni stradali per questa scheda sono disabilitate.', { exact: false }
    ).waitFor({ timeout: 15000 })
    await page.screenshot({ path: item.image, animations: 'disabled' })
    await page.locator('.detail-back').click()
    await page.locator('.search-input').fill('')
    await page.locator('.market-card-open').first().waitFor()
  }
  assert.deepEqual(errors, [], 'No new runtime errors from source-bound city overlays')
  assert.deepEqual(billed, [], 'No paid dynamic data calls allowed during public browsing')
  console.log('PASS: manually reviewed cities remain readable with directions safely disabled')
} finally {
  await browser.close()
}
