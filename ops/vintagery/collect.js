// Vintagery collector: run INSIDE a vintagery.it tab of the owner's Chrome (Claude in Chrome
// javascript_tool, or the DevTools console). Scripts outside a browser get Vercel's Security
// Checkpoint (HTTP 429); this never tries to get past it, it reads pages as the browser does.
//
// Two modes:
// - full (default): every card listed in /sitemap/mercatini-*.xml.
// - daily: when window.__vgPlan = {day, known: [8-char id prefixes], fetch: [prefixes]} is
//   set first (`python backend/vintagery_source.py --plan plan.js`): the sitemap listing,
//   then only the cards we don't hold yet and the ones the plan asks to re-read.
//   The sitemap's <lastmod> is when the sitemap was built, not when a card changed, so
//   it is never used to skip a card.
//
// Each page embeds its card record in the Next.js payload (self.__next_f.push); the record
// plus tags, "Scheda verificata il" and "Data da confermare" are kept. A page without a record
// (undated cards) keeps its visible text (4,000 characters) for the importer's page reader.
// Pages are read one at a time, 3.5 s apart; progress stays in localStorage, so running the
// file again resumes. Three blocked replies in a row (429 / checkpoint page) stop it.
// At the end Chrome downloads vintagery_cards[_<day>].json. Progress: window.__vgState.
// Then: python backend/vintagery_source.py <Downloads>/vintagery_cards*.json
window.__vgCollect = async () => {
  const plan = window.__vgPlan && typeof window.__vgPlan === 'object' ? window.__vgPlan : null
  const KEY = plan ? 'vg_daily_' + plan.day : 'vg_cards_v1'
  const PAUSE_MS = 3500
  const load = () => { try { return JSON.parse(localStorage.getItem(KEY) || '{}') } catch { return {} } }
  const save = cards => localStorage.setItem(KEY, JSON.stringify(cards))
  const wait = ms => new Promise(resolve => setTimeout(resolve, ms))
  const state = window.__vgState = { mode: plan ? 'daily' : 'full', total: 0, done: 0, blocked: 0, errors: 0, running: true, last: '' }

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
  const listed = []
  for (const path of maps) {
    const body = await (await fetch(path)).text()
    listed.push(...(body.match(/https:\/\/vintagery\.it\/mercatini\/[0-9a-f-]{36}/g) || []))
    await wait(1500)
  }
  const unique = [...new Set(listed)]
  if (!unique.length) { state.running = false; state.last = 'stopped: empty sitemap (blocked?)'; return }
  const known = new Set(plan ? plan.known : [])
  const asked = new Set(plan ? plan.fetch : [])
  const todo = plan ? unique.filter(url => !known.has(url.slice(-36, -28)) || asked.has(url.slice(-36, -28))) : unique
  state.total = todo.length
  state.done = Object.keys(load()).length
  let strikes = 0
  for (const url of todo) {
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
      } else {
        card.parse_error = true
        card.page_text = page.body.textContent.slice(0, 4000)
      }
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
  const payload = plan
    ? JSON.stringify({ schema: 2, mode: 'daily', listing_day: plan.day, listing: unique.map(url => url.slice(-36)), cards: load() })
    : localStorage.getItem(KEY)
  const link = document.createElement('a')
  link.href = URL.createObjectURL(new Blob([payload], { type: 'application/json' }))
  link.download = plan ? 'vintagery_cards_' + plan.day + '.json' : 'vintagery_cards.json'
  document.body.appendChild(link); link.click(); link.remove()
}
window.__vgCollect(); 'collector started'
