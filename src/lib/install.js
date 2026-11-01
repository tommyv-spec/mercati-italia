// When and how to offer "install Fuori". Follows web.dev "Patterns for promoting PWA
// installation": never on arrival; offer after a conversion (saving a market) or on a
// repeat visit with real use; keep a permanent entry in the menu; respect "Non ora".

export const EMPTY_INSTALL_STATE = {
  visits: 0, lastVisitAt: 0, opened: 0, saves: 0,
  shown: 0, lastShownAt: 0, dismissals: 0, installed: false, shownThisVisit: false,
}
const VISIT_GAP = 6 * 3600 * 1000
const COOLDOWN = 14 * 86400 * 1000
const MAX_DISMISSALS = 2
// In-app browsers (Instagram, Facebook, TikTok, the Google app…) cannot install a web app.
const IN_APP = /FBAN|FBAV|FB_IAB|Instagram|Line\/|TikTok|musical_ly|BytedanceWebview|Twitter|LinkedInApp|Snapchat|Pinterest|GSA\//

export function installPlatform({ userAgent = '', standalone = false, hasPrompt = false, maxTouchPoints = 0 }) {
  if (standalone) return 'installed'
  if (IN_APP.test(userAgent)) return 'inapp'
  if (hasPrompt) return 'native'
  if (/iPhone|iPad|iPod/.test(userAgent) || (/Macintosh/.test(userAgent) && maxTouchPoints > 1)) return 'ios'
  if (/Android/.test(userAgent)) return 'android-manual'
  return 'desktop'
}

// A new visit after six quiet hours; the "already shown this visit" flag resets with it.
export function startVisit(state, now) {
  const s = { ...EMPTY_INSTALL_STATE, ...state }
  if (now - s.lastVisitAt < VISIT_GAP) return { ...s, lastVisitAt: now }
  return { ...s, visits: s.visits + 1, lastVisitAt: now, shownThisVisit: false }
}

// trigger: 'save' (a market was just saved) or 'open' (a market page was opened).
export function shouldOffer(state, { trigger, platform, now }) {
  if (!['native', 'ios', 'android-manual'].includes(platform)) return false
  if (state.installed || state.shownThisVisit || state.dismissals >= MAX_DISMISSALS) return false
  if (state.lastShownAt && now - state.lastShownAt < COOLDOWN) return false
  if (trigger === 'save') return true
  // A repeat visit with real use, and only if the visitor never said "Non ora".
  return trigger === 'open' && state.dismissals === 0 && state.visits >= 2 && state.opened >= 2
}
