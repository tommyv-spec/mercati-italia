import { addressConflictView } from './sourceFieldConflicts.js'

/** Conflicting source evidence blocks both coordinates and address fallback. */
export function destinationForMarket(market, today) {
  // Do not trust an omitted/false presentation flag to clear a valid conflict.
  if (!market || market.locationReviewRequired || addressConflictView(market, today).length) return null
  if (market.positionQuality === 'precisa' &&
      Number.isFinite(market.lat) && Number.isFinite(market.lng)) {
    return market.lat + ',' + market.lng
  }
  const address = market.address?.trim() || ''
  const specificStreet = /\b(via|viale|piazza|piazzale|piazzetta|corso|largo|vicolo|strada|contrada|lungomare|località|localita|borgo|parco)\b/i
  if (address.length >= 9 && specificStreet.test(address)) {
    return [market.name, address, market.city, 'Italia'].filter(Boolean).join(', ')
  }
  return null
}
