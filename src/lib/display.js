import { italianKey } from './marketGrouping.js';

export const CATEGORY_COLORS = {
  "Alimentare": "#446E47", "Antiquariato": "#B94439", "Vintage e abbigliamento": "#705073",
  "Usato": "#805B08", "Artigianato": "#216886", "Misto": "#9C4B36"
};

// ─── Utility Functions ──────────────────────────────────────
export function localISO(d = new Date()) {
  return [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-');
}
export const TODAY = new Date();
export const todayStr = localISO(TODAY);

export function formatDateIT(dateStr) {
  if (!dateStr) return 'Data da verificare';
  const d = new Date(dateStr + 'T00:00:00');
  return Number.isNaN(d.getTime())
    ? 'Data da verificare'
    : d.toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' });
}

// "Oggi", "Domani" or "Weekend" for the next date; the date quality is shown
// separately as quiet text, never as a loud "da verificare" pill on every card.
export function getDateBadge(dates = []) {
  const now = new Date();
  const today = localISO(now);
  const tomorrow = new Date(now); tomorrow.setDate(tomorrow.getDate() + 1);
  const satDate = new Date(now); satDate.setDate(satDate.getDate() + ((6 - now.getDay() + 7) % 7));
  const sunDate = new Date(satDate); sunDate.setDate(sunDate.getDate() + 1);
  if (dates.includes(today)) return { label: 'Oggi', tone: 'today' };
  if (dates.includes(localISO(tomorrow))) return { label: 'Domani', tone: 'today' };
  if (dates.includes(localISO(satDate)) || dates.includes(localISO(sunDate))) {
    return { label: 'Questo weekend', tone: 'weekend' };
  }
  return null;
}

export function dateQualityLabel(quality) {
  return quality === 'confermata' ? 'Data confermata'
    : quality === 'riportata' ? 'Riportata dalla fonte' : 'Data prevista, da verificare';
}

// Calendar-leaf pieces for a card: day number plus "dom nov".
export function dateLeaf(dateStr) {
  const d = dateStr ? new Date(dateStr + 'T12:00:00') : null;
  if (!d || Number.isNaN(d.getTime())) return { day: '–', month: 'n.d.' };
  return {
    day: String(d.getDate()),
    month: d.toLocaleDateString('it-IT', { weekday: 'short' }) + ' ' + d.toLocaleDateString('it-IT', { month: 'short' }),
  };
}

export function dayHeaderLabel(dateStr) {
  if (!dateStr) return 'Senza una data prossima';
  const tomorrow = new Date(TODAY); tomorrow.setDate(tomorrow.getDate() + 1);
  const long = new Date(dateStr + 'T12:00:00').toLocaleDateString('it-IT', { weekday: 'long', day: 'numeric', month: 'long' });
  const label = long.charAt(0).toUpperCase() + long.slice(1);
  return dateStr === todayStr ? 'Oggi · ' + label : dateStr === localISO(tomorrow) ? 'Domani · ' + label : label;
}

export function getNextDate(dates = []) {
  return dates.filter(d => d >= localISO()).sort()[0] || null;
}

// Generic weekly records of one town repeat the same name per weekday: show the first (earliest) only.
export function uniqueByName(items, pick = item => item) {
  const seen = new Set();
  return items.filter(item => {
    const key = italianKey(pick(item).city) + '|' + italianKey(pick(item).name);
    return seen.has(key) ? false : seen.add(key);
  });
}

// ─── Display-only names ────────────────────────────────────────────────────
// Some sources write "Mercatino antiquariato e usato di <Town>, "<Name>", <street…>":
// the real name is inside, the rest repeats the town and the address. The card
// shows the name; search and the market page keep the full source title.
const SOURCE_TITLE = /^(Mercatino [^,]*?) di ([^,]+), (.+)$/
const QUOTED = /^["“«]([^"”»]{2,})["”»]$/
const PLACE_WORD = /^(via|viale|vicolo|piazza|piazzale|piazzetta|corso|largo|lungo|lungomare|lungolago|lungofiume|centro|parco|area|zona|località|loc\.|borgo|strada|contrada|passeggiata|portici|chiostro|giardini|giardino|parcheggio|campo|riva|banchina|presso|nel|nella|nei|in|sotto|ex|foro|rione|quartiere|frazione|fraz\.|stazione|porto|molo|spiazzo|sagrato|cortile|palazzo|villa|castello|polo|ippodromo|stadio)\b/i
const GENERIC_NAMES = new Set(['antiquariato', 'artigianato', 'usato', 'vintage', 'collezionismo', 'modernariato', 'hobbisti', 'mercatino', 'il mercatino', 'mercato', 'il mercato', "mercatino dell'usato", "mercatino dell'antiquariato", 'antiquariato e usato', 'pulci'])
const SMALL_WORDS = new Set(['di', 'del', 'della', 'dello', 'dei', 'degli', 'delle', 'a', 'al', 'alla', 'allo', 'ai', 'agli', 'alle', 'in', 'nel', 'nella', 'nello', 'nei', 'negli', 'nelle', 'su', 'sul', 'sulla', 'sullo', 'sui', 'sugli', 'sulle', 'da', 'dal', 'dalla', 'dai', 'e', 'ed', 'con', 'per', 'tra', 'fra', 'dell', 'nell', 'sull', 'dall', 'all', 'coll'])

function sourceTitleParts(name) {
  const match = SOURCE_TITLE.exec(name || '')
  if (!match) return null
  const rest = match[3].trim()
  // A quoted name may hold commas of its own: read up to the closing quote.
  const close = /^["“«]/.test(rest) ? rest.slice(1).search(/["”»]/) : -1
  const first = close >= 0 ? rest.slice(0, close + 2) : rest.split(',')[0].trim()
  const quoted = QUOTED.exec(first)
  if (quoted) {
    const inner = quoted[1].trim()
    // "Artigianato", "Il Mercatino": a category word, not a name.
    if (GENERIC_NAMES.has(inner.toLowerCase())) return { title: match[1] + ' di ' + match[2].trim(), lead: first }
    const head = inner.split(/[\s'’]/)[0].toLowerCase()
    // "Dell'Usato e delle Cose Antiche", "di tutto un po'": a name that starts with a preposition.
    const title = SMALL_WORDS.has(head) ? 'Mercatino ' + inner.charAt(0).toLowerCase() + inner.slice(1)
      : inner.charAt(0).toUpperCase() + inner.slice(1)
    return { title, lead: first }
  }
  if (!PLACE_WORD.test(first)) return { title: first, lead: first }
  return { title: match[1] + ' di ' + match[2].trim(), lead: '' }
}

// "Mercatino Dell’antiquariato A Piazzola Sul Brenta" → small words lower case.
function softenTitleCase(name) {
  const words = name.split(' ')
  const capital = words.filter(w => /^[A-ZÀ-Ý]/.test(w)).length
  if (words.length < 3 || capital / words.length < 0.75) return name
  return words.map((word, i) => {
    if (i === 0) return word
    const [head, ...rest] = word.split(/(?<=['’])/)
    if (SMALL_WORDS.has(head.replace(/['’]$/, '').toLowerCase())) return head.toLowerCase() + rest.join('')
    return word
  }).join(' ')
}

export function displayName(market) {
  const name = (market?.name || '').trim()
  const parts = sourceTitleParts(name)
  return parts ? parts.title : softenTitleCase(name)
}

export function displayAddress(market) {
  let address = (market?.address || '').trim()
  const parts = sourceTitleParts(market?.name)
  if (parts?.lead && address.startsWith(parts.lead)) address = address.slice(parts.lead.length).replace(/^[\s,]+/, '')
  return address
}

export function isFreeEntry(text) {
  return /gratuit|libero/i.test(text || '')
}
