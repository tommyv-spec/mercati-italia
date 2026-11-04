// The runner's check before a catalog goes live (ops/runner.py smoke): the built app, opened
// in a phone-sized browser, must list markets and open one, with no runtime error.
// Generic on purpose: it must hold for any night's data, unlike tests/ui-smoke.mjs.
// Usage: node live-smoke.mjs <url>
import { chromium } from 'playwright'

const url = process.argv[2]
const browser = await chromium.launch({ headless: true })
const page = await browser.newPage({
  viewport: { width: 390, height: 844 }, isMobile: true, hasTouch: true, locale: 'it-IT',
})
const errors = []
page.on('pageerror', error => errors.push(error.message))
try {
  const reply = await page.goto(url, { waitUntil: 'domcontentloaded', timeout: 60000 })
  if (reply?.status() !== 200) throw new Error(`HTTP ${reply?.status()}`)
  await page.waitForFunction(() => {
    const count = document.querySelector('.results-count')?.textContent || ''
    return document.querySelectorAll('.market-card').length > 0 && count && !count.includes('Caricamento')
  }, null, { timeout: 60000 })
  const count = await page.locator('.results-count').innerText()
  await page.locator('.market-card-open').first().click()
  await page.locator('.detail-page').waitFor({ timeout: 30000 })
  await page.getByText('Caricamento dettagli completi…').waitFor({ state: 'hidden', timeout: 30000 })
  if (errors.length) throw new Error('page errors: ' + errors.join(' | '))
  console.log(`live-smoke ok: ${count.trim()} | detail opened`)
} finally {
  await browser.close()
}
