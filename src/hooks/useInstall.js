import { useCallback, useEffect, useState } from 'react'
import { EMPTY_INSTALL_STATE, installPlatform, startVisit } from '../lib/install.js'
import { track } from '../lib/installEvents.js'

const KEY = 'fuori.install'
const read = () => { try { return { ...EMPTY_INSTALL_STATE, ...JSON.parse(localStorage.getItem(KEY) || '{}') } } catch { return { ...EMPTY_INSTALL_STATE } } }
const write = state => { try { localStorage.setItem(KEY, JSON.stringify(state)) } catch { /* private mode: nothing kept */ } }
const standaloneNow = () => window.matchMedia?.('(display-mode: standalone)').matches || window.navigator.standalone === true

// What the device can do (platform), what the visitor has done (state), and the native prompt.
export function useInstall() {
  const [prompt, setPrompt] = useState(() => window.__fuoriInstallPrompt || null)
  const [standalone, setStandalone] = useState(standaloneNow)
  const [state, setState] = useState(() => {
    const next = startVisit(read(), Date.now())
    write(next)
    return next
  })
  const update = useCallback(change => setState(prev => {
    const next = { ...prev, ...(typeof change === 'function' ? change(prev) : change) }
    write(next)
    return next
  }), [])

  useEffect(() => {
    const onInstallable = () => setPrompt(window.__fuoriInstallPrompt || null)
    const onInstalled = () => {
      window.__fuoriInstallPrompt = null
      setPrompt(null)
      update({ installed: true })
      track('app_installed')
    }
    const media = window.matchMedia?.('(display-mode: standalone)')
    const onMode = () => setStandalone(standaloneNow())
    window.addEventListener('fuori-installable', onInstallable)
    window.addEventListener('appinstalled', onInstalled)
    media?.addEventListener?.('change', onMode)
    if (standaloneNow()) track('open_installed_app')
    return () => {
      window.removeEventListener('fuori-installable', onInstallable)
      window.removeEventListener('appinstalled', onInstalled)
      media?.removeEventListener?.('change', onMode)
    }
  }, [update])

  const platform = installPlatform({
    userAgent: navigator.userAgent, standalone: standalone || state.installed,
    hasPrompt: Boolean(prompt), maxTouchPoints: navigator.maxTouchPoints || 0,
  })

  // The browser's own dialog; resolves to 'accepted', 'dismissed' or 'unavailable'.
  const promptNative = useCallback(async () => {
    const event = prompt || window.__fuoriInstallPrompt
    if (!event) return 'unavailable'
    event.prompt()
    const choice = await event.userChoice.catch(() => ({ outcome: 'dismissed' }))
    window.__fuoriInstallPrompt = null
    setPrompt(null)
    return choice.outcome
  }, [prompt])

  return { platform, state, update, promptNative }
}
