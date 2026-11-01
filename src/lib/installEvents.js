// Imported first in main.jsx: Chrome may say "installable" before React has mounted.
// We keep the event and suppress the browser's own mini-banner, so Fuori offers
// installation at a moment that makes sense (see lib/install.js).
export function captureInstallPrompt() {
  window.addEventListener('beforeinstallprompt', event => {
    event.preventDefault()
    window.__fuoriInstallPrompt = event
    window.dispatchEvent(new Event('fuori-installable'))
  })
}

// Google Analytics event when the live site loads it (index.html); a no-op on previews.
export function track(name, params = {}) {
  if (typeof window.gtag === 'function') window.gtag('event', name, params)
}
