// Weekly municipal market vs event. The exporter decides with the projection rule;
// the app only has to trust the events file. Without it, tags and category decide.
export const WEEKLY_TAGS = new Set(['settimanale', 'mercato settimanale', 'mercato comunale', 'MERCAP'])

export function fallbackIsEvent(record) {
  if ((record.tags || []).some(tag => WEEKLY_TAGS.has(tag))) return false
  return (record.categoria || 'misto') !== 'misto'
}
