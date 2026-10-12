/**
 * Quick "next 7 days" is selected by default to favor actionable markets.
 * An explicit text search is broader: include unscheduled markets unless the
 * visitor personally activated a time chip. Never secretly undo their chip.
 */
export function effectiveDateFilter(dateFilter, searchQuery = '', userSelected = false) {
  if (typeof searchQuery === 'string' && searchQuery.trim() && !userSelected) return null
  return dateFilter || null
}
