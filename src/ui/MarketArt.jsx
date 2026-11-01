import { artFor } from '../lib/art.js'

// Line drawings on a 24px grid, one stroke weight, chosen per market by lib/art.js.
const ART = {
  vase: <><path d="M9 3h6" /><path d="M10 3v2.5C10 7 6.5 8.5 6.5 13a5.5 5.5 0 0 0 11 0c0-4.5-3.5-6-3.5-7.5V3" /><path d="M8.5 21h7" /><path d="M12 18.5V21" /></>,
  clock: <><path d="M7 21V8a5 5 0 0 1 10 0v13z" /><circle cx="12" cy="9" r="3" /><path d="M12 7.6V9l.9.9" /><path d="M12 13.5v3.5" /><circle cx="12" cy="18" r="1" /><path d="M5.5 21h13" /></>,
  lamp: <><path d="M8 3h8l3 7H5z" /><path d="M12 10v8" /><path d="M8 21h8" /><path d="M10 18h4" /></>,
  record: <><circle cx="12" cy="12" r="8.5" /><circle cx="12" cy="12" r="2.5" /><path d="M12 5.5a6.5 6.5 0 0 1 6.5 6.5" /><path d="M12 7.8a4.2 4.2 0 0 1 4.2 4.2" /></>,
  books: <><rect x="4" y="4" width="4" height="16" rx="1" /><rect x="9" y="6.5" width="4" height="13.5" rx="1" /><path d="m14.6 7.2 3.4-.9 3.1 13.1-3.4.9z" /><path d="M4 8h4M9 10h4" /></>,
  stamp: <><rect x="5" y="4" width="14" height="16" rx="1" strokeDasharray="2 1.7" /><rect x="8" y="7" width="8" height="7" rx="1" /><path d="M8.5 17h7" /></>,
  hanger: <><path d="M10 6.5a2 2 0 1 1 2 2v1.5" /><path d="M12 10 3.6 15.6a1.3 1.3 0 0 0 .7 2.4h15.4a1.3 1.3 0 0 0 .7-2.4z" /></>,
  dress: <><path d="M9.5 3h5l-.8 4 4.3 13H6l4.3-13z" /><path d="M10.3 7h3.4" /><path d="M8.2 14h7.6" /></>,
  glasses: <><circle cx="7" cy="14" r="3.3" /><circle cx="17" cy="14" r="3.3" /><path d="M10.3 13.6c1.1-.8 2.3-.8 3.4 0" /><path d="M3.8 13 2.7 8.5M20.2 13l1.1-4.5" /></>,
  box: <><path d="M3.5 8.5 12 4.5l8.5 4v8L12 20.5l-8.5-4z" /><path d="M3.5 8.5 12 12.5l8.5-4" /><path d="M12 12.5v8" /></>,
  teapot: <><path d="M6 10.5h11V15a5 5 0 0 1-5 5h-1a5 5 0 0 1-5-5z" /><path d="M17 12h1.4a2 2 0 0 1 0 4H16.6" /><path d="M6 12.5 3.3 9.8" /><path d="M9 10.5V9a2.5 2.5 0 0 1 5 0v1.5" /></>,
  palette: <><path d="M12 3.5a8.5 8.5 0 1 0 0 17c1.1 0 1.7-.9 1.3-1.8-.5-1.2.3-2.4 1.6-2.4h1.6a4 4 0 0 0 4-4c0-4.9-3.8-8.8-8.5-8.8z" /><circle cx="7.6" cy="11.5" r="1.1" /><circle cx="10" cy="7.6" r="1.1" /><circle cx="14.7" cy="7.8" r="1.1" /></>,
  scissors: <><circle cx="6.5" cy="17.5" r="2.5" /><circle cx="17.5" cy="17.5" r="2.5" /><path d="M8.3 15.7 18 4" /><path d="M15.7 15.7 6 4" /></>,
  basket: <><path d="M3 10.5h18l-1.7 7.7a2 2 0 0 1-2 1.6H6.7a2 2 0 0 1-2-1.6z" /><path d="m7.5 10.5 3-6" /><path d="m16.5 10.5-3-6" /><path d="M9 13.8v3M12 13.8v3M15 13.8v3" /></>,
  wheat: <><path d="M12 21V7.5" /><path d="M12 11.5c-2.4 0-3.8-1.4-3.8-3.8 2.4 0 3.8 1.4 3.8 3.8zM12 11.5c2.4 0 3.8-1.4 3.8-3.8-2.4 0-3.8 1.4-3.8 3.8z" /><path d="M12 16c-2.4 0-3.8-1.4-3.8-3.8 2.4 0 3.8 1.4 3.8 3.8zM12 16c2.4 0 3.8-1.4 3.8-3.8-2.4 0-3.8 1.4-3.8 3.8z" /><path d="M12 7.5c-1.4-1.1-1.4-2.9 0-4.4 1.4 1.5 1.4 3.3 0 4.4z" /></>,
  glass: <><path d="M8 3h8l-.4 5.2a3.6 3.6 0 0 1-7.2 0z" /><path d="M12 11.8V20" /><path d="M8.5 20.5h7" /><path d="M8.3 6.5h7.4" /></>,
  stall: <><path d="m3.5 9 1.8-5h13.4l1.8 5" /><path d="M3.5 9a2.8 2.8 0 0 0 5.67 0 2.8 2.8 0 0 0 5.66 0 2.8 2.8 0 0 0 5.67 0" /><path d="M5 12v8h14v-8" /><path d="M10 20v-4.5h4V20" /></>,
  bunting: <><path d="M3 5.5c6 3.2 12 3.2 18 0" /><path d="m5.8 6.9 1.4 5.3 2-4.6" /><path d="m11 8.1 1 5.4 2-5.3" /><path d="m16.4 7.6.4 5.3 2.3-4.9" /><path d="M3 5.5V21M21 5.5V21" /></>,
  tree: <><path d="M12 3 7.5 9.5h2.8L6 15.5h12l-4.3-6h2.8z" /><path d="M12 15.5V20" /><path d="M9.5 20.5h5" /></>,
}

export default function MarketArt({ market, size = 28, strokeWidth = 1.6, color = 'currentColor' }) {
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={strokeWidth}
      strokeLinecap="round" strokeLinejoin="round" aria-hidden="true" style={{ flexShrink: 0 }}>
      {ART[artFor(market)] || ART.stall}
    </svg>
  )
}
