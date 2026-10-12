import test from 'node:test'
import assert from 'node:assert/strict'
import { auditDisplayRows, markdown } from '../scripts/reversible-duplicate-audit.mjs'

const data = (slug, overrides={}) => ({
  slug, nome:'Mercato settimanale di Albizzate',
  citta:'Albizzate', regione:'Lombardia', provincia:'VA',
  indirizzo:'Piazzale Sefro', categoria:'misto',
  orario_testo:'08:00–13:00 (fonte comunale, da verificare)',
  ricorrenza_testo:'settimanale - martedì',
  date:['2026-10-13','2026-10-20','2026-10-27'],
  date_quality:'prevista', status:'non_confermato', verificato_il:'',
  lat:45.724163,lng:8.797983,
  url_fonte:'https://www.happings.com/it/mercato-settimanale-a-albizzate.html',
  ...overrides,
})

test('national auditor reuses production grouping but retains every source ID', () => {
  const rows=[
    data('mercato-settimanale-di-albizzate-albizzate'),
    data('mercato-settimanale-di-albizzate-albizzate-martedi'),
    data('distinct-friday',{ricorrenza_testo:'settimanale - venerdì',date:['2026-10-16','2026-10-23']}),
    data('old-city',{citta:'Arsago Seprio',indirizzo:'Via Monici'}),
  ]
  const report=auditDisplayRows(rows)
  assert.equal(report.metrics.original_records,4)
  assert.equal(report.metrics.ids_retained,4)
  assert.equal(report.metrics.highly_supported_same_source_visit_groups,1)
  assert.equal(report.metrics.suppressed_repeat_buttons_only,1)
  assert.equal(report.metrics.original_records_in_reversible_groups,2)
  assert.equal(report.metrics.market_identities_deleted,0)
  assert.equal(report.metrics.event_confirmations_created,0)
  assert.equal(rows.length,4)
  assert.match(markdown(report),/visualizzazione reversibile/)
})

test('auditor never claims a same-date distinct publisher venue as a duplicate', () => {
  const rows=[data('a'),data('b',{url_fonte:'https://example.org/other'})]
  assert.equal(auditDisplayRows(rows).metrics.suppressed_repeat_buttons_only,0)
})

test('auditor rejects missing source IDs without mutating originals', () => {
  assert.throws(()=>auditDisplayRows([data('a'),data('a')]),/Duplicate/)
  assert.throws(()=>auditDisplayRows([data('a'),{...data('b'),slug:''}]),/missing/)
  assert.throws(()=>auditDisplayRows([]),/invalid/)
})
