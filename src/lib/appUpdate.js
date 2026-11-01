// A release ships a new hashed entry script in index.html. When someone comes back to an app
// left open, compare it with the published page and reload onto the new version without asking.
// The catalog has its own refresh (useMarkets); this covers the app code.
export const APP_CHECK_INTERVAL_MS = 5 * 60 * 1000
const RELOADED_FOR = 'fuori-app-reloaded-for'

export function entryScript(html) {
  return html.match(/<script[^>]*\ssrc="([^"]*\/assets\/[^"]+\.js)"/)?.[1] || null
}

export function keepAppCurrent() {
  const running = document.querySelector('script[src*="/assets/"]')?.getAttribute('src')
  if (!running) return // dev server: no hashed build to compare
  let lastCheck = Date.now()
  const check = async () => {
    if (document.visibilityState !== 'visible' || Date.now() - lastCheck < APP_CHECK_INTERVAL_MS) return
    lastCheck = Date.now()
    try {
      const response = await fetch(import.meta.env.BASE_URL, { cache: 'no-store' })
      const published = response.ok && entryScript(await response.text())
      // One reload per release, so a stale edge cache can never cause a reload loop.
      if (!published || published === running || sessionStorage.getItem(RELOADED_FOR) === published) return
      sessionStorage.setItem(RELOADED_FOR, published)
      window.location.reload()
    } catch {
      // Offline or storage blocked: keep the running version and try at the next return.
    }
  }
  document.addEventListener('visibilitychange', check)
  window.addEventListener('focus', check)
}
