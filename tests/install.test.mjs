import test from 'node:test'
import assert from 'node:assert/strict'
import { installPlatform, shouldOffer, startVisit, EMPTY_INSTALL_STATE } from '../src/lib/install.js'

const IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Mobile/15E148 Safari/604.1'
const IPAD_AS_MAC = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.0 Safari/605.1.15'
const ANDROID_CHROME = 'Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Mobile Safari/537.36'
const ANDROID_FIREFOX = 'Mozilla/5.0 (Android 14; Mobile; rv:143.0) Gecko/143.0 Firefox/143.0'
const INSTAGRAM = 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 Instagram 400.0.0.0'
const DESKTOP = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/141.0.0.0 Safari/537.36'

test('the platform decides how Fuori can be installed', () => {
  assert.equal(installPlatform({ userAgent: ANDROID_CHROME, standalone: true, hasPrompt: true }), 'installed')
  assert.equal(installPlatform({ userAgent: ANDROID_CHROME, hasPrompt: true }), 'native')
  assert.equal(installPlatform({ userAgent: ANDROID_FIREFOX, hasPrompt: false }), 'android-manual')
  assert.equal(installPlatform({ userAgent: IPHONE }), 'ios')
  assert.equal(installPlatform({ userAgent: IPAD_AS_MAC, maxTouchPoints: 5 }), 'ios')
  assert.equal(installPlatform({ userAgent: IPAD_AS_MAC, maxTouchPoints: 0 }), 'desktop')
  assert.equal(installPlatform({ userAgent: INSTAGRAM, hasPrompt: false }), 'inapp')
  assert.equal(installPlatform({ userAgent: DESKTOP, hasPrompt: true }), 'native')
  assert.equal(installPlatform({ userAgent: DESKTOP }), 'desktop')
})

const DAY = 86400000
const NOW = Date.UTC(2026, 10, 2, 10)

test('never on the first screen; a save is the moment; a second visit with two markets opened too', () => {
  const fresh = startVisit(EMPTY_INSTALL_STATE, NOW)
  assert.equal(shouldOffer(fresh, { trigger: 'open', platform: 'native', now: NOW }), false)
  assert.equal(shouldOffer(fresh, { trigger: 'save', platform: 'native', now: NOW }), true)
  assert.equal(shouldOffer(fresh, { trigger: 'save', platform: 'ios', now: NOW }), true)
  const second = startVisit({ ...fresh, opened: 2 }, NOW + DAY)
  assert.equal(second.visits, 2)
  assert.equal(shouldOffer({ ...second, opened: 1 }, { trigger: 'open', platform: 'native', now: NOW + DAY }), false)
  assert.equal(shouldOffer(second, { trigger: 'open', platform: 'native', now: NOW + DAY }), true)
})

test('a visit is counted once per six hours', () => {
  const a = startVisit(EMPTY_INSTALL_STATE, NOW)
  assert.equal(startVisit(a, NOW + 3600000).visits, 1)
  assert.equal(startVisit(a, NOW + 7 * 3600000).visits, 2)
})

test('installed, desktop, in-app browsers and no-prompt Chrome never get the automatic banner', () => {
  const s = startVisit(EMPTY_INSTALL_STATE, NOW)
  for (const platform of ['installed', 'desktop', 'inapp']) assert.equal(shouldOffer(s, { trigger: 'save', platform, now: NOW }), false, platform)
  assert.equal(shouldOffer({ ...s, installed: true }, { trigger: 'save', platform: 'native', now: NOW }), false)
})

test('after "Non ora": only a new save brings it back, after 14 days; two refusals end it', () => {
  const once = { ...startVisit(EMPTY_INSTALL_STATE, NOW), visits: 3, opened: 5, dismissals: 1, lastShownAt: NOW }
  assert.equal(shouldOffer(once, { trigger: 'open', platform: 'native', now: NOW + 30 * DAY }), false)
  assert.equal(shouldOffer(once, { trigger: 'save', platform: 'native', now: NOW + 13 * DAY }), false)
  assert.equal(shouldOffer(once, { trigger: 'save', platform: 'native', now: NOW + 15 * DAY }), true)
  assert.equal(shouldOffer({ ...once, dismissals: 2 }, { trigger: 'save', platform: 'native', now: NOW + 60 * DAY }), false)
  assert.equal(shouldOffer({ ...once, dismissals: 0, shownThisVisit: true }, { trigger: 'save', platform: 'native', now: NOW + 60 * DAY }), false)
})
