import test from 'node:test'
import assert from 'node:assert/strict'
import { fieldEvidenceSummary } from '../src/lib/fieldEvidence.js'

const today = '2026-10-19'
function market() {
  const identity = { slug: 'market-a', citta: 'Milano', provincia: 'MI', regione: 'Lombardia' }
  return {
    ...identity, indirizzo: 'Piazza A', orario_testo: '08:00–13:00',
    riscontri_campi: [{
      schema: 1, mercato: { ...identity },
      valori: { indirizzo: 'Piazza A', orario_testo: '08:00–13:00' },
      url: 'https://example.org/market-a', fonte: 'Comune',
      letto_il: today, fonte_aggiornata_il: '2024-05-27',
    }],
  }
}

test('shows the old content date independently of today’s read', () => {
  const [evidence] = fieldEvidenceSummary(market(), today)
  assert.equal(evidence.sourceDate, '2024-05-27')
  assert.equal(evidence.readOn, today)
  assert.equal(evidence.fields, 'Sede, Orari')
  assert.equal('verified' in evidence, false)
})

test('a changed address cannot retain address evidence; unchanged hours can', () => {
  const changed = market()
  changed.indirizzo = 'Piazza B'
  assert.equal(fieldEvidenceSummary(changed, today)[0].fields, 'Orari')
})

test('evidence cannot move to a different municipality or market identity', () => {
  for (const field of ['slug', 'citta', 'provincia', 'regione']) {
    const changed = market()
    changed[field] = 'another'
    assert.deepEqual(fieldEvidenceSummary(changed, today), [])
  }
})

test('unknown content date stays unknown after reading and importing', () => {
  const changed = market()
  changed.aggiornato_il = today
  changed.importato_il = today
  changed.riscontri_campi[0].fonte_aggiornata_il = ''
  assert.equal(fieldEvidenceSummary(changed, today)[0].sourceDate, '')
})

test('invalid and future evidence dates are not shown', () => {
  for (const [field, value] of [
    ['letto_il', '2026-10-20'], ['letto_il', '2026-02-30'],
    ['fonte_aggiornata_il', '2026-10-20'], ['fonte_aggiornata_il', '2026-02-30'],
  ]) {
    const changed = market()
    changed.riscontri_campi[0][field] = value
    assert.deepEqual(fieldEvidenceSummary(changed, today), [])
  }
})

test('unsafe source URLs cannot become evidence links', () => {
  for (const url of ['javascript:alert(1)', 'https://user:password@example.org/']) {
    const changed = market()
    changed.riscontri_campi[0].url = url
    assert.deepEqual(fieldEvidenceSummary(changed, today), [])
  }
})
