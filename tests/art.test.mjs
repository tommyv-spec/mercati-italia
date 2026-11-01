import test from 'node:test'
import assert from 'node:assert/strict'
import { artFor } from '../src/lib/art.js'

const m = (name, category, tags = [], id = name) => ({ id, name, category, tags })

test('what the market is about picks the drawing', () => {
  assert.equal(artFor(m('Mercatino di Natale in piazza', 'Misto')), 'tree')
  assert.equal(artFor(m('Fiera del disco e del vinile', 'Usato')), 'record')
  assert.equal(artFor(m('Carta e stampe antiche', 'Antiquariato')), 'books')
  assert.equal(artFor(m('Mercato', 'Antiquariato', ['collezionismo'])), 'stamp')
  assert.equal(artFor(m('Mercato di Campagna Amica di Pavia', 'Alimentare')), 'wheat')
  assert.equal(artFor(m('Sagra del vino', 'Alimentare')), 'glass')
  assert.equal(artFor(m('Svuota cantine', 'Usato')), 'box')
})

test('without a clue the category decides, and the same market always gets the same drawing', () => {
  const a = artFor(m('Mercatino del Passato', 'Antiquariato', [], 'pavullo-1'))
  assert.ok(['vase', 'clock', 'lamp'].includes(a))
  assert.equal(artFor(m('Mercatino del Passato', 'Antiquariato', [], 'pavullo-1')), a)
  assert.ok(['hanger', 'dress', 'glasses'].includes(artFor(m('Piazza', 'Vintage e abbigliamento'))))
  assert.ok(['palette', 'scissors'].includes(artFor(m('Mostra', 'Artigianato'))))
  assert.ok(['stall', 'bunting'].includes(artFor(m('Mercato', 'Misto'))))
})

test('neighbouring antiques markets do not all get the same drawing', () => {
  const names = ['Collezionando', 'Mercantico', 'Il Mercatino del Passato', 'Antico Baule', 'Soffitte in piazza', 'Belle Epoque', 'Novantico', 'Genovantiquaria']
  const drawings = new Set(names.map(name => artFor(m(name, 'Antiquariato', [], name.toLowerCase()))))
  assert.ok(drawings.size >= 2, 'at least two different drawings among eight antiques markets')
})
