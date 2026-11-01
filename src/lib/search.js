// Search by the start of words: "arezzo" finds "Fiera Antiquaria di Arezzo", never "Sarezzo".
// Accents and apostrophes are ignored ("nardo" finds Nardò, "usato" finds dell'usato).
const fold = text => String(text || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')

export function queryWords(text) {
  return fold(text).split(/[^a-z0-9]+/).filter(Boolean)
}

const cache = new WeakMap()
function wordsOf(market) {
  let entry = cache.get(market)
  if (!entry) {
    const name = queryWords(market.name)
    entry = { name, nameText: name.join(' '),
      all: [...name, ...queryWords(market.city), ...queryWords(market.region), ...queryWords(market.category),
        ...(market.tags || []).flatMap(queryWords)] }
    cache.set(market, entry)
  }
  return entry
}

const everyWordStarts = (wanted, words) => wanted.every(w => words.some(word => word.startsWith(w)))

// 3 = the name starts with what was typed, 2 = every word is in the name, 1 = found via town, region, tags.
function score(market, wanted, typed) {
  const words = wordsOf(market)
  if (!everyWordStarts(wanted, words.all)) return 0
  if (words.nameText.startsWith(typed)) return 3
  return everyWordStarts(wanted, words.name) ? 2 : 1
}

export function searchMarkets(markets, query, today) {
  const wanted = queryWords(query)
  if (!wanted.length) return []
  const typed = wanted.join(' ')
  const next = market => [...(market.dates || [])].sort().find(day => day >= today) || '9999'
  return markets
    .map(market => ({ market, s: score(market, wanted, typed) }))
    .filter(item => item.s > 0)
    // Equal match: an event (a fair, a monthly market) before a town's weekly market, then the next date.
    .sort((a, b) => b.s - a.s || Number(Boolean(b.market.isEvent)) - Number(Boolean(a.market.isEvent)) ||
      next(a.market).localeCompare(next(b.market)) || a.market.name.localeCompare(b.market.name, 'it'))
    .map(item => item.market)
}

export function matchCities(cities, query, limit = 3) {
  const wanted = queryWords(query)
  if (!wanted.length) return []
  const typed = wanted.join(' ')
  return cities
    .filter(city => everyWordStarts(wanted, queryWords(city)))
    .sort((a, b) => Number(queryWords(b).join(' ') === typed) - Number(queryWords(a).join(' ') === typed) || a.localeCompare(b, 'it'))
    .slice(0, limit)
}
