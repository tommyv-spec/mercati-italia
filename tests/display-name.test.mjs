import test from 'node:test'
import assert from 'node:assert/strict'
import { displayName, displayAddress, isFreeEntry } from '../src/lib/display.js'

const m = (name, address = '') => ({ name, address })

test('a quoted name inside a long source title becomes the title', () => {
  assert.equal(displayName(m('Mercatino antiquariato e usato di Monfalcone, "Mercatino della Rocca", centro storico, piazza della Repubblica')), 'Mercatino della Rocca')
  assert.equal(displayName(m('Mercatino antiquariato e usato di Predosa, “Il Mercatino del Lido di Predosa”, lungo il fiume Orba')), 'Il Mercatino del Lido di Predosa')
  assert.equal(displayName(m('Mercatino antiquariato e usato di Nardò, "di tutto un po\'", via XX Settembre')), 'Mercatino di tutto un po\'')
  assert.equal(displayName(m('Mercatino antiquariato e usato di Torino, "Dell\'Usato e delle Cose Antiche", via Don Grioli')), 'Mercatino dell\'Usato e delle Cose Antiche')
  const vergato = m('Mercatino antiquariato e usato di Vergato, "Mercatino delle Cose Antiche, del Modernariato e del Riuso", centro storico, via Don Giorgio Pederzini',
    '"Mercatino delle Cose Antiche, del Modernariato e del Riuso", centro storico, via Don Giorgio Pederzini')
  assert.equal(displayName(vergato), 'Mercatino delle Cose Antiche, del Modernariato e del Riuso')
  assert.equal(displayAddress(vergato), 'centro storico, via Don Giorgio Pederzini')
})

test('a quoted name that is only a category word falls back to kind + town', () => {
  assert.equal(displayName(m('Mercatino antiquariato e usato di Bogliasco, "Artigianato", piazza XXVI Aprile', 'piazza XXVI Aprile')), 'Mercatino antiquariato e usato di Bogliasco')
  assert.equal(displayName(m('Mercatino antiquariato e usato di Ceglie Messapica, "Il Mercatino", piazza Sant\'Antonio')), 'Mercatino antiquariato e usato di Ceglie Messapica')
  assert.equal(displayAddress(m('Mercatino antiquariato e usato di Bogliasco, "Artigianato", piazza XXVI Aprile', '"Artigianato", piazza XXVI Aprile')), 'piazza XXVI Aprile')
})

test('an unquoted name is kept, a bare street falls back to kind + town', () => {
  assert.equal(displayName(m('Mercatino antiquariato e usato di Genova, Genovantiquaria, piazza Giacomo Matteotti')), 'Genovantiquaria')
  assert.equal(displayName(m('Mercatino antiquariato e usato di Magenta, Mercatino estivo serale, piazza Liberazione')), 'Mercatino estivo serale')
  assert.equal(displayName(m('Mercatino antiquariato e usato di Cerignola, piazza Libertà')), 'Mercatino antiquariato e usato di Cerignola')
  assert.equal(displayName(m('Mercatino antiquariato e usato di Sotto il Monte Giovanni XXIII, centro storico, piazza Caduti')), 'Mercatino antiquariato e usato di Sotto il Monte Giovanni XXIII')
})

test('other names are left alone, Title Case is softened', () => {
  assert.equal(displayName(m('Fiera Antiquaria di Arezzo')), 'Fiera Antiquaria di Arezzo')
  assert.equal(displayName(m('Svuota-Cantine Domenicale — Stadio della Vittoria, Bari')), 'Svuota-Cantine Domenicale — Stadio della Vittoria, Bari')
  assert.equal(displayName(m('Mercatino Dell’antiquariato A Piazzola Sul Brenta')), 'Mercatino dell’antiquariato a Piazzola sul Brenta')
  assert.equal(displayName(m('Il Mercatino Dell\'usato A Collegno')), 'Il Mercatino dell\'usato a Collegno')
  assert.equal(displayName(m('')), '')
})

test('the address drops a leading name the title already shows', () => {
  assert.equal(displayAddress(m('Mercatino antiquariato e usato di Venaria Reale, "Belle Epoque", viale Buridani', '"Belle Epoque", viale Buridani')), 'viale Buridani')
  assert.equal(displayAddress(m('Mercatino antiquariato e usato di Genova, Genovantiquaria, piazza Giacomo Matteotti', 'Genovantiquaria, piazza Giacomo Matteotti')), 'piazza Giacomo Matteotti')
  assert.equal(displayAddress(m('Fiera Antiquaria di Arezzo', 'Piazza Grande')), 'Piazza Grande')
  assert.equal(displayAddress(m('x', '')), '')
})

test('free entry is recognised in the wording sources use', () => {
  assert.equal(isFreeEntry('Ingresso gratuito'), true)
  assert.equal(isFreeEntry('Ingresso libero e gratuito per i visitatori'), true)
  assert.equal(isFreeEntry('Ingresso 5 €'), false)
  assert.equal(isFreeEntry(''), false)
})
