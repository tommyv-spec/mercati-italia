import { CATEGORY_COLORS } from '../lib/display.js'

// One line drawing per category, same 24px grid and stroke as Icon.jsx.
const PATHS = {
  // a vase with a narrow neck
  Antiquariato: <><path d="M9 3h6" /><path d="M10 3v2.5C10 7 6.5 8.5 6.5 13a5.5 5.5 0 0 0 11 0c0-4.5-3.5-6-3.5-7.5V3" /><path d="M8.5 21h7" /><path d="M12 18.5V21" /></>,
  // a coat hanger
  'Vintage e abbigliamento': <><path d="M10 6.5a2 2 0 1 1 2 2v1.5" /><path d="M12 10 3.6 15.6a1.3 1.3 0 0 0 .7 2.4h15.4a1.3 1.3 0 0 0 .7-2.4z" /></>,
  // an open box
  Usato: <><path d="M3.5 8.5 12 4.5l8.5 4v8L12 20.5l-8.5-4z" /><path d="M3.5 8.5 12 12.5l8.5-4" /><path d="M12 12.5v8" /></>,
  // a painter's palette
  Artigianato: <><path d="M12 3.5a8.5 8.5 0 1 0 0 17c1.1 0 1.7-.9 1.3-1.8-.5-1.2.3-2.4 1.6-2.4h1.6a4 4 0 0 0 4-4c0-4.9-3.8-8.8-8.5-8.8z" /><circle cx="7.6" cy="11.5" r="1.1" /><circle cx="10" cy="7.6" r="1.1" /><circle cx="14.7" cy="7.8" r="1.1" /></>,
  // a basket
  Alimentare: <><path d="M3 10.5h18l-1.7 7.7a2 2 0 0 1-2 1.6H6.7a2 2 0 0 1-2-1.6z" /><path d="m7.5 10.5 3-6" /><path d="m16.5 10.5-3-6" /><path d="M9 13.8v3M12 13.8v3M15 13.8v3" /></>,
  // a market stall with an awning
  Misto: <><path d="m3.5 9 1.8-5h13.4l1.8 5" /><path d="M3.5 9a2.8 2.8 0 0 0 5.67 0 2.8 2.8 0 0 0 5.66 0 2.8 2.8 0 0 0 5.67 0" /><path d="M5 12v8h14v-8" /><path d="M10 20v-4.5h4V20" /></>,
}

export function categoryColor(category) {
  return CATEGORY_COLORS[category] || CATEGORY_COLORS.Misto
}

export default function CategoryIcon({ category, size = 24, color = 'currentColor', strokeWidth = 1.7 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flexShrink: 0 }}>
      {PATHS[category] || PATHS.Misto}
    </svg>
  )
}

// The square tile a row leads with: the category's tint and its drawing.
export function CategoryTile({ category, size = 56 }) {
  return (
    <span className="cat-tile" style={{ '--c': categoryColor(category), width: size, height: size }}>
      <CategoryIcon category={category} size={Math.round(size * 0.46)} />
      <span className="sr-only">{category}</span>
    </span>
  )
}
