import test from 'node:test'
import assert from 'node:assert/strict'
import { isSuspiciousCityName, safeCityLabel, UNKNOWN_CITY_HELP } from '../src/lib/locationQuality.js'

test('actual national catalog corrupt scraped city labels are not exposed as municipalities', () => {
  const malformed = [
    '"Mercatino delle Curiosità"',
    '“La Soffitta in Piazza e l’Angolo del Libro Usato”',
    '"Fiera del Disco"',
    'NA','BO','AL','RM',
    'Castiglione Messer Marino, in provincia di... Mercato settimanale a Celenza Sul Trigno',
    'Cervia ( ra ) Fiere, Mostre e Mercati Antiquariato Gastronomia Vintage',
    'Via Tiburtina - FROSINONE',
  ]
  for (const label of malformed) {
    assert.equal(isSuspiciousCityName(label),true,label)
    assert.equal(safeCityLabel(label),'Località da verificare')
  }
  assert.match(UNKNOWN_CITY_HELP,/Comune/)
})

test('valid Italian municipalities are not confused with generic street words', () => {
  const legitimate=[
    'Piazza Brembana','Piazza al Serchio','Piazzatorre',
    'Cernobbio','Albizzate','San Pellegrino Terme','Gallarate',
    'San Marcello Piteglio','Castiglione Messer Marino',
    'Castellammare di Stabia','Trinità d’Agultu e Vignola',
  ]
  for (const city of legitimate) {
    assert.equal(isSuspiciousCityName(city),false,city)
    assert.equal(safeCityLabel(city),city)
  }
})

test('no city rewrite is performed: source labels remain valid search text', () => {
  const original='"Mercatino delle Curiosità"'
  assert.equal(safeCityLabel(original),'Località da verificare')
  assert.equal(original,'"Mercatino delle Curiosità"')
  assert.equal(safeCityLabel(''),'')
})
