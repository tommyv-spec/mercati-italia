/**
 * Install flow at phone width: no invitation on arrival; after a save the invitation
 * appears above the tabs; "Non ora" is remembered; Android gets one tap, iPhone the
 * three-step guide; "Altro" always offers it. The browser's install event is simulated.
 * Run: UI_BASE=http://127.0.0.1:4173/ node tests/install-ui.mjs
 */
import { chromium } from 'playwright'
import assert from 'node:assert/strict'

const BASE = process.env.UI_BASE || 'http://127.0.0.1:4173/'
const ANDROID = 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36'
const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1'
const browser = await chromium.launch({ headless: true })
const errors = []

async function open(userAgent) {
  const context = await browser.newContext({ viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, locale: 'it-IT', userAgent })
  const page = await context.newPage()
  page.on('pageerror', e => errors.push(e.message))
  await page.goto(BASE, { waitUntil: 'domcontentloaded', timeout: 45000 })
  await page.locator('.market-card .card-name').first().waitFor({ timeout: 45000 })
  return { context, page }
}
// What Chrome does once the app is installable; prompt() records the call.
const fireInstallable = page => page.evaluate(() => {
  const event = new Event('beforeinstallprompt', { cancelable: true })
  event.prompt = () => { window.__prompted = (window.__prompted || 0) + 1 }
  event.userChoice = Promise.resolve({ outcome: 'accepted', platform: 'web' })
  window.dispatchEvent(event)
  return event.defaultPrevented
})

try {
  // Android Chrome
  {
    const { context, page } = await open(ANDROID)
    assert.equal(await fireInstallable(page), true, 'The browser mini-banner is held back for a better moment')
    await page.waitForTimeout(500)
    assert.equal(await page.locator('.install-banner').count(), 0, 'No invitation on arrival')
    await page.locator('.market-card .row-fav').first().click()
    await page.locator('.install-banner').waitFor({ timeout: 5000 })
    assert.match(await page.locator('.install-banner').innerText(), /Salvato\. Vuoi Fuori sul telefono\?/)
    await page.locator('.install-banner').getByRole('button', { name: 'Non ora' }).click()
    await page.locator('.install-banner').waitFor({ state: 'hidden' })
    await page.locator('.market-card .row-fav').nth(1).click()
    await page.waitForTimeout(500)
    assert.equal(await page.locator('.install-banner').count(), 0, '"Non ora" is respected')
    const stored = await page.evaluate(() => JSON.parse(localStorage.getItem('fuori.install')))
    assert.equal(stored.dismissals, 1)
    // Altro always offers it, one tap.
    await page.locator('.bottom-tabs').getByRole('button', { name: 'Altro' }).click()
    await page.getByRole('button', { name: 'Installa Fuori' }).click()
    await page.waitForFunction(() => window.__prompted === 1)
    await context.close()
  }
  // iPhone Safari: no install event; the invitation leads to the three-step guide.
  {
    const { context, page } = await open(IPHONE)
    assert.equal(await page.locator('.install-banner').count(), 0, 'No invitation on arrival')
    await page.locator('.market-card .row-fav').first().click()
    await page.locator('.install-banner').waitFor({ timeout: 5000 })
    await page.locator('.install-banner').getByRole('button', { name: 'Installa' }).click()
    await page.locator('.sheet').getByText('Aggiungi alla schermata Home').waitFor()
    assert.equal(await page.locator('.sheet .install-steps li').count(), 3)
    await page.goBack()
    await page.locator('.sheet').waitFor({ state: 'hidden' })
    await page.locator('.bottom-tabs').getByRole('button', { name: 'Altro' }).click()
    await page.locator('.install-panel').getByText('Apri come web app').waitFor()
    await context.close()
  }
  assert.deepEqual(errors, [], 'No runtime errors')
  console.log('PASS: install is offered after a save, respects "Non ora", one tap on Android, three steps on iPhone')
} finally {
  await browser.close()
}
