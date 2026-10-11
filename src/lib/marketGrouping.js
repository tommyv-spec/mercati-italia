/** Pure grouping rules: display aggregation NEVER rewrites source market IDs. */

export const WEEKDAY_LABELS = ['Lun', 'Mar', 'Mer', 'Gio', 'Ven', 'Sab', 'Dom']

export function italianKey(value) {
  return String(value || '')
    .normalize('NFD').replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('it')
    .replace(/[’']/g, ' ')
    .replace(/[^a-z0-9]+/g, ' ')
    .trim().replace(/\s+/g, ' ')
}

export function isGenericCityWeeklyMarket(market) {
  const name = italianKey(market?.name)
  const city = italianKey(market?.city)
  if (!name || !city || !market?.region) return false
  // Do not collapse named neighborhood, artisan or antique markets.
  // Only a title literally equivalent to "Mercato settimanale di/a [city]".
  const match = name.match(/^mercat(?:o|ino) settimanale (?:di|a|ad|del|della|dei|in|nel|nella) (.+)$/)
  return Boolean(match && match[1] === city)
}

export function weeklyGroupKey(market) {
  return `weekly:${italianKey(market.region)}:${italianKey(market.city)}`
}

export function weekdayFromISO(value) {
  if (typeof value !== 'string' || !/^\d{4}-\d\d-\d\d$/.test(value)) return null
  const parsed = new Date(value + 'T12:00:00')
  if (Number.isNaN(parsed.getTime()) || parsed.getFullYear() !== Number(value.slice(0, 4)) ||
      parsed.getMonth() + 1 !== Number(value.slice(5, 7)) ||
      parsed.getDate() !== Number(value.slice(8))) return null
  return (parsed.getDay() + 6) % 7 // Monday = 0
}

export function nextMatchingDate(dates = [], selectedWeekday = null, now = new Date()) {
  const today = [now.getFullYear(),
    String(now.getMonth() + 1).padStart(2, '0'),
    String(now.getDate()).padStart(2, '0')].join('-')
  return dates.filter(d => d >= today &&
    (selectedWeekday === null || weekdayFromISO(d) === selectedWeekday)).sort()[0] || null
}

export function displayEntries(markets, { keepSingleWeeklyGroups = false } = {}) {
  const entries = []
  const weekly = new Map()
  for (const market of markets) {
    if (!isGenericCityWeeklyMarket(market)) {
      entries.push({ kind: 'market', key: market.id, market })
      continue
    }
    const key = weeklyGroupKey(market)
    let slot = weekly.get(key)
    if (!slot) {
      slot = { kind: 'group', key, city: market.city, region: market.region, markets: [] }
      weekly.set(key, slot)
      entries.push(slot)
    }
    slot.markets.push(market)
  }
  return entries.flatMap(entry => entry.kind === 'group' &&
    entry.markets.length === 1 && !keepSingleWeeklyGroups
    ? [{ kind: 'market', key: entry.markets[0].id, market: entry.markets[0] }]
    : [entry])
}

export function distinctWeekdays(markets) {
  const days = new Set()
  for (const market of markets) {
    for (const date of market.dates || []) {
      const weekday = weekdayFromISO(date)
      if (weekday !== null) days.add(weekday)
    }
  }
  return [...days].sort((a, b) => a - b)
}

export function reliableVenueAddress(value) {
  const original = String(value || '').trim()
  const simplified = italianKey(original)
  if (!simplified || simplified.length < 7 ||
      ['centro', 'centro storico', 'da definire', 'non disponibile', 'sconosciuto',
        'non verificato', 'sede da verificare', 'citta', 'varie sedi'].includes(simplified)) return ''
  return simplified
}

function distinctPreciseLocation(a, b) {
  if (a.positionQuality !== 'precisa' || b.positionQuality !== 'precisa') return false
  if (![a.lat, a.lng, b.lat, b.lng].every(Number.isFinite)) return false
  return Math.abs(a.lat - b.lat) > 0.0025 || Math.abs(a.lng - b.lng) > 0.0025
}

export function groupVenues(markets) {
  const venues = []
  const byAddress = new Map()
  for (const market of markets) {
    const addressKey = reliableVenueAddress(market.address)
    let venue = null
    if (addressKey) {
      for (const candidate of byAddress.get(addressKey) || []) {
        if (!distinctPreciseLocation(candidate.markets[0], market)) {
          venue = candidate
          break
        }
      }
    }
    if (!venue) {
      venue = {
        key: addressKey ? `venue:${addressKey}:${market.id}` : `unknown:${market.id}`,
        address: addressKey ? market.address.trim() : '',
        verifiedAddress: Boolean(addressKey),
        markets: [],
      }
      venues.push(venue)
      if (addressKey) {
        if (!byAddress.has(addressKey)) byAddress.set(addressKey, [])
        byAddress.get(addressKey).push(venue)
      }
    }
    venue.markets.push(market)
  }
  // Sedes with dates soonest first, then consistent address order.
  return venues.sort((a, b) => {
    const nextA = a.markets.map(m => nextMatchingDate(m.dates)).filter(Boolean).sort()[0] || '9999'
    const nextB = b.markets.map(m => nextMatchingDate(m.dates)).filter(Boolean).sort()[0] || '9999'
    return nextA.localeCompare(nextB) || a.address.localeCompare(b.address, 'it')
  })
}
