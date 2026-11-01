// Which drawing a market gets: first what its name and tags say it is about,
// then its category; a stable pick from the id spreads the drawings of one category.
const fold = text => String(text || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')

const CLUES = [
  [/natal|presepe|avvent/, 'tree'],
  [/\bdisc|vinil|record|giradisch/, 'record'],
  [/\blibr|\bcarta\b|stamp[ae]|fumett|editor/, 'books'],
  [/collezion|numismat|filatel|monet|francobol|militaria/, 'stamp'],
  [/campagna amica|agricol|contadin|km ?0|produttor|biologic|coltivat/, 'wheat'],
  [/\bvin[oi]\b|enogastr|sagra|degustaz|birr/, 'glass'],
  [/svuota|sbaracc|baratto|riuso|\bpulci\b|rigatt/, 'box'],
  [/hobbist|creativ|ingegno|handmade|fatto a mano|uncinett|maglia/, 'scissors'],
]
const BY_CATEGORY = {
  Antiquariato: ['vase', 'clock', 'lamp'],
  'Vintage e abbigliamento': ['hanger', 'dress', 'glasses'],
  Usato: ['box', 'teapot'],
  Artigianato: ['palette', 'scissors'],
  Alimentare: ['basket', 'wheat'],
  Misto: ['stall', 'bunting'],
}

function stableIndex(text, size) {
  let h = 0
  for (const ch of String(text)) h = (h * 31 + ch.charCodeAt(0)) >>> 0
  return h % size
}

export function artFor(market) {
  const text = fold([market.name, ...(market.tags || [])].join(' '))
  for (const [pattern, art] of CLUES) if (pattern.test(text)) return art
  const options = BY_CATEGORY[market.category] || BY_CATEGORY.Misto
  return options[stableIndex(market.id || market.name, options.length)]
}
