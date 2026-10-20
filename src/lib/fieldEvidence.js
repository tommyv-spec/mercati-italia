// Field evidence is narrower than confirmation of a market opening.
import { CITYNEWS_HOSTS, citynewsSourceIdentity } from './citynewsIdentity.js'

const fields = { indirizzo: 'Sede', orario_testo: 'Orari', ricorrenza_testo: 'Giorni' }
const validDay = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) &&
  Number.isFinite(Date.parse(`${value}T00:00:00Z`)) &&
  new Date(`${value}T00:00:00Z`).toISOString().slice(0, 10) === value

export function fieldEvidenceSummary(market, today = new Date().toISOString().slice(0, 10)) {
  if (!Array.isArray(market.riscontri_campi)) return []
  const expected = {
    slug: market.slug || market.id,
    citta: market.citta || '', provincia: market.provincia || '', regione: market.regione || '',
  }
  return market.riscontri_campi.slice(0, 6).flatMap(receipt => {
    if (!receipt || receipt.schema !== 1 || !receipt.mercato || !receipt.valori ||
        Object.entries(expected).some(([key, value]) => receipt.mercato[key] !== value) ||
        !validDay(receipt.letto_il) || receipt.letto_il > today ||
        (receipt.fonte_aggiornata_il && (!validDay(receipt.fonte_aggiornata_il) ||
          receipt.fonte_aggiornata_il > receipt.letto_il))) return []
    let source
    try { source = new URL(receipt.url) } catch { return [] }
    if (source.protocol !== 'https:' || source.username || source.password) return []
    const citynews = citynewsSourceIdentity(receipt.url)
    if (citynews || CITYNEWS_HOSTS.has(receipt.fonte) || receipt.gestore_campi === 'citynews_detail' ||
        String(receipt.fonte_id || '').startsWith('citynews-')) {
      if (!citynews || receipt.url !== market.url_fonte || receipt.fonte !== citynews[0] ||
          receipt.fonte_id !== citynews[1] || receipt.riga_fonte !== citynews[1] + ':event-card' ||
          receipt.metodo !== 'pagina_primaria_revisionata' || receipt.ambito !== 'pagina' ||
          receipt.impronta_tipo !== 'html_bytes' || !/^[a-f0-9]{64}$/.test(receipt.sha256 || '') ||
          receipt.fonte_aggiornata_il) return []
    }
    const covered = Object.keys(fields).filter(field =>
      typeof receipt.valori[field] === 'string' && receipt.valori[field] &&
      receipt.valori[field] === market[field])
    if (!covered.length) return []
    return [{
      fields: covered.map(field => fields[field]).join(', '),
      readOn: receipt.letto_il,
      sourceDate: receipt.fonte_aggiornata_il || '',
      sourceName: String(receipt.fonte || 'Fonte'), sourceUrl: source.href,
    }]
  })
}
