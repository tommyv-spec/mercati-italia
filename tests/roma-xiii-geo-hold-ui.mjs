/** Fail closed if source-conflicted Rome coordinates become navigable on mobile. */
import assert from 'node:assert/strict'
import { chromium } from 'playwright'

const browser = await chromium.launch({ headless: true })
const base = process.env.UI_BASE || 'http://127.0.0.1:4173/'
const errors = [], dynamic = []
const context = await browser.newContext({
  viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true,
  locale: 'it-IT',
})
const page = await context.newPage()
page.on('pageerror', error => errors.push(error.message))
page.on('request', request => {
  if (/firestore\.googleapis\.com|firebaseio\.com|workers\.dev/i.test(request.url()))
    dynamic.push(request.url())
})
try {
  const opened = await page.goto(base, {waitUntil:'domcontentloaded',timeout:45000})
  assert.equal(opened?.status(),200)
  await page.locator('.market-card-open').first().waitFor({timeout:30000})
  for (const item of [
    {search:'Irnerio',city:'Roma',file:'ux-roma-irnerio-held.png'},
    {search:'Casalotti',city:'Roma',file:'ux-roma-casalotti-held.png'},
  ]) {
    await page.locator('.search-input').fill(item.search)
    const candidate = page.locator('.market-card').filter({hasText:item.city}).first()
    await candidate.waitFor({timeout:30000})
    await candidate.locator('.market-card-open').click()
    await page.locator('.detail-page').waitFor({timeout:15000})
    await page.getByText('Caricamento dettagli completi…').waitFor({
      state:'hidden',timeout:20000,
    })
    const button=page.getByRole('button',{name:/Indicazioni/}).first()
    assert.equal(await button.isDisabled(),true,
      'Source-conflicted Rome marker must never enable directions: '+item.search)
    await page.getByText(
      'Le indicazioni stradali per questa scheda sono disabilitate.',{exact:false}
    ).waitFor({timeout:15000})
    await page.screenshot({path:item.file,animations:'disabled'})
    await page.locator('.detail-back').click()
    await page.locator('.search-input').fill('')
    await page.locator('.market-card-open').first().waitFor()
  }
  assert.deepEqual(errors,[])
  assert.deepEqual(dynamic,[])
  console.log('PASS: Rome municipal source-conflicted points remain non-navigable on mobile')
} finally {
  await browser.close()
}
