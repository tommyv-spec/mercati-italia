// Vintagery collector: run INSIDE a vintagery.it tab of the owner's Chrome (Claude in Chrome
// javascript_tool, or the DevTools console). Scripts outside a browser get Vercel's Security
// Checkpoint (HTTP 429); this never tries to get past it, it reads pages as the browser does.
//
// What it does: sitemap index /sitemap.xml -> /sitemap/mercatini-*.xml -> every
// /mercatini/<uuid> page, one at a time, >= 3.5 s apart. Each page embeds its card record in
// the Next.js payload (self.__next_f.push); the record plus tags, "Scheda verificata il" and
// "Data da confermare" are kept in localStorage (key vg_cards_v1), so a reload or a stop
// resumes where it was. Three blocked replies in a row (429 / checkpoint page) stop it.
// When every card is read it downloads vintagery_cards.json (one file, about 1 MB).
//
// Progress: window.__vgState. Start again later: just run this file again.
// Then: python backend/vintagery_source.py <Downloads>/vintagery_cards.json
(async () => {
  const KEY = 'vg_cards_v1'
  const PAUSE_MS = 3500
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY) || '{}') } catch { return {} } }
  const save = cards => localStorage.setItem(KEY, JSON.stringify(cards))
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms))

  function record(text) {
    // The card record is the JSON object around "schedule_notes" in the joined payload.
    const at = text.indexOf('"schedule_notes"')
    if (at < 0) return null
    let depth = 0, start = at
    for (; start >= 0; start--) {
      if (text[start] === '}') depth++
      else if (text[start] === '{') { if (depth === 0) break; depth-- }
    }
    let end = start
    for (depth = 0; end < text.length; end++) {
      if (text[end] === '{') depth++
      else if (text[end] === '}' && --depth === 0) break
    }
    try { return JSON.parse(text.slice(start, end + 1)) } catch { return null }
  }

  const index = await (await fetch('/sitemap.xml')).text()
  const maps = [...index.matchAll(/<loc>([^<]+)<\/loc>/g)].map(m => new URL(m[1]).pathname)
    .filter(path => /^\/sitemap\/mercatini-\d+\.xml$/.test(path))
  const urls = []
  for (const path of maps) {
    const body = await (await fetch(path)).text()
    urls.push(...(body.match(/https:\/\/vintagery\.it\/mercatini\/[0-9a-f-]{36}/g) || []))
    await wait(1500)
  }
  const unique = [...new Set(urls)]
  const state = window.__vgState = { total: unique.length, done: Object.keys(load()).length, blocked: 0, errors: 0, running: true, last: '' }
  let strikes = 0
  for (const url of unique) {
    const id = url.slice(-36)
    if (load()[id]) continue
    try {
      const response = await fetch(url)
      const html = await response.text()
      if (response.status !== 200 || /Security Checkpoint/.test(html) || !html.includes('__next_f')) {
        state.blocked++; state.last = 'blocked ' + response.status
        if (++strikes >= 3) { state.running = false; state.last = 'stopped: blocked 3 times, run again later'; return }
        await wait(60000)
        continue
      }
      strikes = 0
      const parts = []
      for (const m of html.matchAll(/self\.__next_f\.push\(\[1,"((?:[^"\\]|\\.)*)"\]\)/g)) {
        try { parts.push(JSON.parse('"' + m[1] + '"')) } catch { /* not a string chunk */ }
      }
      const text = parts.join('')
      const found = record(text)
      const tagAt = text.indexOf('lucide lucide-tag')
      const tags = [...new Set([...(tagAt >= 0 ? text.slice(tagAt, tagAt + 4000) : '')
        .matchAll(/\["\$","span","([^"]{2,40})",\{"className":"text-\[11px\] font-semibold px-3 py-1 rounded-full border"/g)]
        .map(m => m[1]))]
      const page = new DOMParser().parseFromString(html, 'text/html')
      const title = page.title
      page.querySelectorAll('script,style,svg').forEach(node => node.remove())
      const visible = page.body.textContent.replace(/\s+/g, ' ')
      const card = {}
      if (found && typeof found === 'object') {
        for (const [key, value] of Object.entries(found)) if (value !== '$undefined' && key !== 'icsTable') card[key] = value
      } else card.parse_error = true
      Object.assign(card, {
        url, title, tags,
        verified: (visible.match(/Scheda verificata il ([0-9]{1,2} [a-z]+(?: [0-9]{4})?)/) || [])[1] || '',
        unconfirmed: /Data da confermare/.test(visible.slice(0, visible.indexOf('Prossima apertura') + 50)),
        not_verified: /Scheda non (ancora )?verificata/i.test(visible),
        read_at: new Date().toISOString(),
      })
      const cards = load(); cards[id] = card; save(cards)
      state.done = Object.keys(cards).length; state.last = id
    } catch (error) { state.errors++; state.last = 'error ' + String(error).slice(0, 80) }
    await wait(PAUSE_MS)
  }
  state.running = false; state.last = 'finished'
  const link = document.createElement('a')
  link.href = URL.createObjectURL(new Blob([localStorage.getItem(KEY)], { type: 'application/json' }))
  link.download = 'vintagery_cards.json'
  document.body.appendChild(link); link.click(); link.remove()
})()
