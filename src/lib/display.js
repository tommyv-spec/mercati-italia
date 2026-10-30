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
