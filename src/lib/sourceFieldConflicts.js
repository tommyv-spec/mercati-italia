// A publisher contradiction is a reason to review a saved field, never a
// replacement value or a confirmation of the market's current opening.
const conflictKeys = ['schema', 'gestore', 'campo', 'mercato', 'valore_catalogo',
  'valore_fonte', 'giorno_settimana', 'url_richiesto', 'url_finale', 'letto_il',
  'sha256', 'bytes', 'prova']
const identityKeys = ['slug', 'nome', 'citta', 'provincia', 'regione', 'fonte', 'url_fonte']
const identityLimits = {slug: 130, nome: 160, citta: 120, provincia: 2,
  regione: 80, fonte: 100, url_fonte: 650}
const proofKeys = ['tipo', 'selettore', 'frammento', 'sede_precedente', 'sede_attuale']
const replacement = 'queste indicazioni sostituiscono i vecchi riferimenti'
const selector = /^main#main article\.hpe-editorial--local-guide \.hpe-editorial-grid > \.hpe-editorial-body > p:nth-child\(([1-9]\d{0,2})\)$/
const vagueAddresses = new Set(['centro', 'centro storico', 'sede da verificare',
  'da verificare', 'piazza', 'via', 'viale', 'citta', 'zona centro',
  'non disponibile', 'sconosciuto', 'varie sedi'])
const badPhrases = ['mercati in ', 'mercati settimanali', 'sagra', 'fiera',
  'su richiesta', 'consultare', 'da definire', 'presso gli stand']
const addressPrefix = /^(?:via|viale|vicolo|vico|corso|piazza|piazzale|piazzetta|largo|lungomare|strada|villaggio|campo|parco|borgo|frazione|contrada|passeggiata(?=\s+(?:d|di|del|della|dell|dei|delle|degli)(?:\s+|['’])\p{L}))(?![\p{L}\p{N}_])/iu

const object = value => value !== null && typeof value === 'object' && !Array.isArray(value)
const exactKeys = (value, keys) => object(value) && Object.keys(value).length === keys.length &&
  keys.every(key => Object.hasOwn(value, key))
const boundedText = (value, max) => typeof value === 'string' && value.length > 0 &&
  [...value].length <= max && value === value.split(/[\s\u0085]+/u).filter(Boolean).join(' ') &&
  !/[\u0000-\u001f\u007f]/.test(value)
const norm = value => value.normalize('NFKD').replace(/\p{Mark}/gu, '').toLowerCase()
  .replace(/ß/g, 'ss').replace(/\s+/g, ' ').trim()
// happings_weekly_layout.fold uses lower(), while the stored-street safety
// classifier uses casefold(). Keep the two normalizations distinct.
const fold = value => (value.normalize('NFKD').replace(/\p{Mark}/gu, '').toLowerCase()
  .match(/[a-z0-9]+/g) || []).join(' ')
const validDay = value => typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) &&
  Number.isFinite(Date.parse(value + 'T00:00:00Z')) &&
  new Date(value + 'T00:00:00Z').toISOString().slice(0, 10) === value
const todayISO = () => new Date().toISOString().slice(0, 10)

function safeURL(value) {
  if (typeof value !== 'string' || !/^https:\/\/[^/]/i.test(value) ||
      value.includes('\\') || value !== value.trim()) return null
  try {
    const url = new URL(value)
    return url.protocol === 'https:' && url.hostname && !url.username && !url.password &&
      !url.port && !url.hash ? url : null
  } catch { return null }
}

function provincePageKey(value) {
  const url = safeURL(value)
  if (!url || url.hostname !== 'www.happings.com' || url.port || url.search) return null
  const raw = value.match(/^https:\/\/([^/?#]+)(\/[^?#]*)/i)
  if (!raw || !/^www\.happings\.com(?::443)?$/i.test(raw[1])) return null
  return raw[2].match(/^\/it\/mercati-settimanali-(?:a|ad)-([a-z0-9]+(?:-[a-z0-9]+)*?)(?:\.html|-e-provincia\/)$/)?.[1] || null
}

function specificAddress(value) {
  if (typeof value !== 'string' || [...value].length < 7 || [...value].length > 190) return false
  const normalized = norm(value)
  return addressPrefix.test(normalized) && !vagueAddresses.has(fold(value)) &&
    !badPhrases.some(part => normalized.includes(part))
}

/** Mirrors the persisted address-conflict contract, using the full record. */
export function validAddressConflict(conflict, record, today = todayISO()) {
  if (!object(record) || !exactKeys(conflict, conflictKeys) ||
      conflict.schema !== 1 || conflict.gestore !== 'happings-weekly' ||
      conflict.campo !== 'indirizzo' || !exactKeys(conflict.mercato, identityKeys) ||
      identityKeys.some(key => !boundedText(conflict.mercato[key], identityLimits[key]) ||
        conflict.mercato[key] !== (key === 'slug' ? record.slug || record.id : record[key])) ||
      !/^[A-Z]{2}$/.test(conflict.mercato.provincia) ||
      !safeURL(conflict.mercato.url_fonte) ||
      conflict.valore_catalogo !== record.indirizzo ||
      !boundedText(conflict.valore_catalogo, 190) || !boundedText(conflict.valore_fonte, 190) ||
      !specificAddress(conflict.valore_catalogo) || !specificAddress(conflict.valore_fonte) ||
      fold(conflict.valore_catalogo) === fold(conflict.valore_fonte) ||
      !Number.isInteger(conflict.giorno_settimana) || conflict.giorno_settimana < 0 ||
      conflict.giorno_settimana > 6 || !validDay(today) || !validDay(conflict.letto_il) ||
      conflict.letto_il > today || typeof conflict.sha256 !== 'string' || !/^[a-f0-9]{64}$/.test(conflict.sha256) ||
      !Number.isInteger(conflict.bytes) || conflict.bytes < 1 || conflict.bytes > 2600000) return false
  if (!boundedText(conflict.url_richiesto, 650) || !boundedText(conflict.url_finale, 650)) return false
  const requested = provincePageKey(conflict.url_richiesto)
  if (!requested || requested !== provincePageKey(conflict.url_finale)) return false
  const proof = conflict.prova
  if (!exactKeys(proof, proofKeys) || proof.tipo !== 'sostituzione_sede_esplicita' ||
      !boundedText(proof.selettore, 200) ||
      !selector.test(proof.selettore) || Number(proof.selettore.match(selector)[1]) > 200 ||
      !boundedText(proof.frammento, 1200) ||
      proof.sede_precedente !== conflict.valore_catalogo || proof.sede_attuale !== conflict.valore_fonte) return false
  const fragment = fold(proof.frammento)
  const parts = fragment.split(replacement)
  return parts.length === 2 && (' ' + parts[0] + ' ').includes(' ' + fold(proof.sede_attuale) + ' ') &&
    (' ' + parts[1] + ' ').includes(' ' + fold(proof.sede_precedente) + ' ')
}

export function cleanAddressConflicts(value, record, today = todayISO()) {
  if (!Array.isArray(value) || value.length > 3) return []
  const canonical = value => Array.isArray(value) ? value.map(canonical) : object(value)
    ? Object.fromEntries(Object.keys(value).sort().map(key => [key, canonical(value[key])])) : value
  const distinct = new Map(value.filter(conflict => validAddressConflict(conflict, record, today))
    .map(conflict => { const item = canonical(conflict); return [JSON.stringify(item), item] }))
  return [...distinct.values()].sort((a, b) => {
    const left = [a.letto_il, a.url_finale, a.sha256, a.valore_fonte, a.prova.selettore, a.prova.frammento]
    const right = [b.letto_il, b.url_finale, b.sha256, b.valore_fonte, b.prova.selettore, b.prova.frammento]
    for (let i = 0; i < left.length; i++) {
      if (left[i] !== right[i]) return left[i] > right[i] ? -1 : 1
    }
    return 0
  })
}

/** React's adapted market retains the same original identity and source. */
export function addressConflictView(market, today = todayISO()) {
  if (!object(market)) return []
  const record = {slug: market.id, nome: market.name, citta: market.originalCity,
    provincia: market.province, regione: market.region, fonte: market.source,
    url_fonte: market.sourceUrl, indirizzo: market.address}
  return cleanAddressConflicts(market.fieldConflicts, record, today).map(conflict => ({
    key: [conflict.sha256, conflict.valore_fonte, conflict.giorno_settimana].join('/'),
    savedAddress: conflict.valore_catalogo, sourceAddress: conflict.valore_fonte,
    sourceUrl: conflict.url_finale, readOn: conflict.letto_il,
    readOnLabel: new Date(conflict.letto_il + 'T12:00:00Z').toLocaleDateString('it-IT', {
      day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC',
    }),
  }))
}
