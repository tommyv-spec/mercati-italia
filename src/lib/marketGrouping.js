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

export function shouldAutoExpandWeeklyGroup(group, weekdayFilter, cityFilter = '', searchQuery = '') {
  if (weekdayFilter === null) return false
  const city = italianKey(group.city)
  return (Boolean(cityFilter) && city === italianKey(cityFilter)) ||
    (Boolean(searchQuery.trim()) && city === italianKey(searchQuery.trim()))
}


/**
 * Group only highly corroborated duplicate *display entries* at a venue.
 * All source record identities remain accessible and unchanged.
 *
 * Manually observed: Albizzate / Piazzale Sefro / Tuesday, two Happings
 * source records with identical future weeks; Breganze Wednesday in
 * EventieSagre. Different venue, day, publisher, hours or category must
 * never be collapsed based on a fuzzy title alone.
 */
export function sameWeeklyVisitEvidence(a, b) {
  if (!a || !b || a.id === b.id) return false
  if (![a, b].every(isGenericCityWeeklyMarket)) return false
  if ([a, b].some(m => /^(lo-mercap-|bo-open-|pg-corciano-)/.test(m.id || ''))) return false
  if (italianKey(a.region) !== italianKey(b.region) ||
      italianKey(a.city) !== italianKey(b.city) ||
      italianKey(a.category) !== italianKey(b.category)) return false
  const addrA = reliableVenueAddress(a.address)
  const addrB = reliableVenueAddress(b.address)
  if (!addrA || addrA !== addrB) return false
  if (!a.sourceUrl || a.sourceUrl !== b.sourceUrl ||
      !/^https:\/\//i.test(a.sourceUrl)) return false
  if (a.dateQuality !== 'prevista' || b.dateQuality !== 'prevista' ||
      a.lastVerified || b.lastVerified ||
      (a.status || 'non_confermato') !== (b.status || 'non_confermato')) return false
  const hoursA = italianKey(a.hours)
  const hoursB = italianKey(b.hours)
  if (hoursA && hoursB && hoursA !== hoursB) return false

  const datesA = [...new Set(a.dates || [])].sort()
  const datesB = [...new Set(b.dates || [])].sort()
  // Two identical successive weeks, not an isolated one-off or monthly
  // series with a coincidentally shared weekday.
  if (datesA.length < 2 || datesB.length < 2 ||
      datesA[0] !== datesB[0] || datesA[1] !== datesB[1]) return false
  const day = weekdayFromISO(datesA[0])
  if (day === null || day !== weekdayFromISO(datesA[1])) return false
  const [year1, month1, day1] = datesA[0].split('-').map(Number)
  const [year2, month2, day2] = datesA[1].split('-').map(Number)
  if (Date.UTC(year2, month2 - 1, day2) - Date.UTC(year1, month1 - 1, day1) !== 604800000) return false
  if (![a, b].every(m => {
    const rule = italianKey(m.recurrence)
    return rule.includes('settimanale') && !/mensil|quindicinal|alternat/.test(rule)
  })) return false

  const bothHaveCoordinates = [a.lat, a.lng, b.lat, b.lng].every(Number.isFinite)
  if (bothHaveCoordinates) {
    const latScale = 111.2
    const lonScale = 111.2 * Math.cos((a.lat + b.lat) / 2 * Math.PI / 180)
    if (Math.hypot((a.lat - b.lat) * latScale, (a.lng - b.lng) * lonScale) > 0.25) return false
  }
  return true
}

function bestVisitRecord(records) {
  return [...records].sort((a, b) => {
    const score = m => Number(Boolean(m.hours)) * 8 +
      Number(Boolean(m.description)) * 3 +
      Number(Boolean(m.sourceEvidence?.length)) * 2 +
      (Number(m.dataCompleteness) || 0) / 100
    return score(b) - score(a) ||
      String(b.sourceUpdated || '').localeCompare(String(a.sourceUpdated || '')) ||
      String(a.id).localeCompare(String(b.id))
  })[0]
}

/** One visible appointment and expandable records; no input is mutated. */
export function groupVenueAppointments(markets = []) {
  const groups = []
  for (const market of markets) {
    const group = groups.find(g => g.records.every(other => sameWeeklyVisitEvidence(other, market)))
    if (group) group.records.push(market)
    else groups.push({ records: [market] })
  }
  return groups.map(g => {
    const representative = bestVisitRecord(g.records)
    return {
      key: representative.id,
      market: representative,
      records: [...g.records].sort((a, b) => String(a.id).localeCompare(String(b.id))),
    }
  })
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
