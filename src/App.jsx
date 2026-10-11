import { useState, useCallback, useMemo, useEffect, useRef, lazy, Suspense } from "react";
import { useMarkets } from "./hooks/useMarkets";
const MarketsMap = lazy(() => import('./components/MarketsMap.jsx'));

// ─── Sample Data (kept as fallback, but primary source is useMarkets hook) ──
// Market records come from the versioned static catalog, not bundled fixtures.
const CATEGORIES = ["Alimentare", "Antiquariato", "Vintage e abbigliamento", "Usato", "Artigianato", "Misto"];
const REGIONS = [];
const CITIES = [];

const CATEGORY_ICONS = {
  "Alimentare": "🍅", "Antiquariato": "🏺", "Vintage e abbigliamento": "👗",
  "Usato": "📦", "Artigianato": "🎨", "Misto": "🎪"
};

const CATEGORY_COLORS = {
  "Alimentare": "#5B7A5E", "Antiquariato": "#C75146", "Vintage e abbigliamento": "#8B6F8E",
  "Usato": "#B8860B", "Artigianato": "#2E86AB", "Misto": "#E07A5F"
};

// ─── Utility Functions ──────────────────────────────────────
function localISO(d = new Date()) {
  return [d.getFullYear(), String(d.getMonth() + 1).padStart(2, '0'), String(d.getDate()).padStart(2, '0')].join('-');
}
const TODAY = new Date();
const todayStr = localISO(TODAY);

function formatDateIT(dateStr) {
  if (!dateStr) return 'Data da verificare';
  const d = new Date(dateStr + 'T00:00:00');
  return Number.isNaN(d.getTime())
    ? 'Data da verificare'
    : d.toLocaleDateString('it-IT', { weekday: 'short', day: 'numeric', month: 'short' });
}

function getDateBadge(dates = [], quality = 'prevista') {
  const confirmed = quality === 'confermata';
  const suffix = confirmed ? '' : ' · da verificare';
  const now = new Date();
  const today = localISO(now);
  const tomorrow = new Date(now); tomorrow.setDate(tomorrow.getDate() + 1);
  const satDate = new Date(now); satDate.setDate(satDate.getDate() + ((6 - now.getDay() + 7) % 7));
  const sunDate = new Date(satDate); sunDate.setDate(sunDate.getDate() + 1);
  if (dates.includes(today)) return { label: 'Oggi' + suffix, color: confirmed ? '#C75146' : '#81796D' };
  if (dates.includes(localISO(tomorrow))) return { label: 'Domani' + suffix, color: confirmed ? '#C75146' : '#81796D' };
  if (dates.includes(localISO(satDate)) || dates.includes(localISO(sunDate))) {
    return { label: 'Weekend' + suffix, color: confirmed ? '#5B7A5E' : '#81796D' };
  }
  return null;
}

function getNextDate(dates = []) {
  return dates.filter(d => d >= localISO()).sort()[0] || null;
}

function haversine(lat1, lng1, lat2, lng2) {
  const R = 6371;
  const dLat = (lat2 - lat1) * Math.PI / 180;
  const dLng = (lng2 - lng1) * Math.PI / 180;
  const a = Math.sin(dLat / 2) ** 2 + Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) * Math.sin(dLng / 2) ** 2;
  return R * 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
}

// User position (Firenze as default)
const USER_LAT = 43.7696;
const USER_LNG = 11.2558;

// ─── Icons (SVG) ────────────────────────────────────────────
const Icon = ({ name, size = 20, color = "currentColor", strokeWidth = 1.8 }) => {
  const icons = {
    search: <><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></>,
    filter: <><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></>,
    heart: <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"/>,
    heartFilled: <path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z" fill="currentColor"/>,
    mapPin: <><path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/><circle cx="12" cy="10" r="3"/></>,
    clock: <><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></>,
    compass: <><circle cx="12" cy="12" r="10"/><polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/></>,
    bell: <><path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/><path d="M13.73 21a2 2 0 0 1-3.46 0"/></>,
    settings: <><circle cx="12" cy="12" r="3"/><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06A1.65 1.65 0 0 0 4.68 15a1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06A1.65 1.65 0 0 0 9 4.68a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06A1.65 1.65 0 0 0 19.4 9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/></>,
    chevronLeft: <polyline points="15 18 9 12 15 6"/>,
    chevronRight: <polyline points="9 18 15 12 9 6"/>,
    x: <><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></>,
    copy: <><rect x="9" y="9" width="13" height="13" rx="2" ry="2"/><path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/></>,
    navigation: <polygon points="3 11 22 2 13 21 11 13 3 11"/>,
    share: <><circle cx="18" cy="5" r="3"/><circle cx="6" cy="12" r="3"/><circle cx="18" cy="19" r="3"/><line x1="8.59" y1="13.51" x2="15.42" y2="17.49"/><line x1="15.41" y1="6.51" x2="8.59" y2="10.49"/></>,
    calendar: <><rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></>,
    list: <><line x1="8" y1="6" x2="21" y2="6"/><line x1="8" y1="12" x2="21" y2="12"/><line x1="8" y1="18" x2="21" y2="18"/><line x1="3" y1="6" x2="3.01" y2="6"/><line x1="3" y1="12" x2="3.01" y2="12"/><line x1="3" y1="18" x2="3.01" y2="18"/></>,
    map: <><polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/><line x1="8" y1="2" x2="8" y2="18"/><line x1="16" y1="6" x2="16" y2="22"/></>,
    check: <polyline points="20 6 9 17 4 12"/>,
    minus: <line x1="5" y1="12" x2="19" y2="12"/>,
    plus: <><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></>,
    externalLink: <><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/><polyline points="15 3 21 3 21 9"/><line x1="10" y1="14" x2="21" y2="3"/></>,
    info: <><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></>,
    sort: <><line x1="12" y1="5" x2="12" y2="19"/><polyline points="19 12 12 19 5 12"/></>,
    bookmark: <path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"/>,
  };
  return (
    <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color}
      strokeWidth={strokeWidth} strokeLinecap="round" strokeLinejoin="round" style={{ flexShrink: 0 }}>
      {icons[name]}
    </svg>
  );
};

// ─── Styles ─────────────────────────────────────────────────
const styles = `
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Source+Sans+3:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&display=swap');

:root {
  --terracotta: #C75146;
  --terracotta-light: #E8857D;
  --olive: #5B7A5E;
  --olive-light: #7FA882;
  --olive-pale: #E8F0E9;
  --beige: #F5F0E8;
  --beige-dark: #E8E0D4;
  --sand: #D4C5A9;
  --ink: #2C2416;
  --ink-light: #5C513F;
  --ink-lighter: #8C8272;
  --cream: #FDFBF7;
  --white: #FFFFFF;
  --shadow-sm: 0 1px 3px rgba(44,36,22,0.06);
  --shadow-md: 0 4px 12px rgba(44,36,22,0.08);
  --shadow-lg: 0 8px 30px rgba(44,36,22,0.12);
  --radius-sm: 8px;
  --radius-md: 12px;
  --radius-lg: 16px;
  --radius-xl: 20px;
  --font-display: 'DM Serif Display', Georgia, serif;
  --font-body: 'Source Sans 3', -apple-system, sans-serif;
}

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: var(--font-body);
  background: var(--beige);
  color: var(--ink);
  -webkit-font-smoothing: antialiased;
}

/* Animations */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(16px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}
@keyframes slideUp {
  from { transform: translateY(100%); }
  to { transform: translateY(0); }
}
@keyframes slideInRight {
  from { opacity: 0; transform: translateX(20px); }
  to { opacity: 1; transform: translateX(0); }
}
@keyframes scaleIn {
  from { opacity: 0; transform: scale(0.95); }
  to { opacity: 1; transform: scale(1); }
}
@keyframes heartPop {
  0% { transform: scale(1); }
  50% { transform: scale(1.3); }
  100% { transform: scale(1); }
}
@keyframes shimmer {
  0% { background-position: -200% 0; }
  100% { background-position: 200% 0; }
}
@keyframes pulseGlow {
  0%, 100% { box-shadow: 0 0 0 0 rgba(199,81,70,0.3); }
  50% { box-shadow: 0 0 0 8px rgba(199,81,70,0); }
}

.app-container {
  max-width: 480px;
  margin: 0 auto;
  min-height: 100vh;
  background: var(--cream);
  position: relative;
  overflow: hidden;
}

/* ─── Header ─── */
.header {
  background: linear-gradient(180deg, var(--cream) 0%, var(--cream) 90%, transparent 100%);
  padding: 16px 20px 8px;
  position: sticky;
  top: 0;
  z-index: 50;
  backdrop-filter: blur(12px);
}

.header-title {
  font-family: var(--font-display);
  font-size: 28px;
  color: var(--ink);
  letter-spacing: -0.3px;
  margin-bottom: 12px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.header-title .accent {
  color: var(--terracotta);
}

/* ─── Search ─── */
.search-container {
  position: relative;
  margin-bottom: 12px;
}

.search-input {
  width: 100%;
  padding: 12px 16px 12px 44px;
  border: 2px solid var(--beige-dark);
  border-radius: var(--radius-lg);
  font-family: var(--font-body);
  font-size: 15px;
  color: var(--ink);
  background: var(--white);
  transition: all 0.25s ease;
  outline: none;
}

.search-input:focus {
  border-color: var(--olive);
  box-shadow: 0 0 0 3px var(--olive-pale);
}

.search-input::placeholder {
  color: var(--ink-lighter);
}

.search-icon {
  position: absolute;
  left: 14px;
  top: 50%;
  transform: translateY(-50%);
  color: var(--ink-lighter);
}

/* ─── Quick Chips ─── */
.chips-row {
  display: flex;
  gap: 8px;
  overflow-x: auto;
  scrollbar-width: none;
  padding: 4px 0 8px;
  -webkit-overflow-scrolling: touch;
}

.chips-row::-webkit-scrollbar { display: none; }

.chip {
  white-space: nowrap;
  padding: 8px 16px;
  border-radius: 100px;
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 500;
  border: 1.5px solid var(--beige-dark);
  background: var(--white);
  color: var(--ink-light);
  cursor: pointer;
  transition: all 0.2s ease;
  user-select: none;
}

.chip:hover {
  border-color: var(--sand);
  background: var(--beige);
}

.chip.active {
  background: var(--ink);
  color: var(--cream);
  border-color: var(--ink);
}

/* ─── Controls Row ─── */
.controls-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 0 0 12px;
}

.view-toggle {
  display: flex;
  background: var(--beige);
  border-radius: var(--radius-sm);
  padding: 3px;
  gap: 2px;
}

.view-toggle button {
  padding: 7px 14px;
  border: none;
  border-radius: 6px;
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-lighter);
  background: transparent;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 5px;
  transition: all 0.2s ease;
}

.view-toggle button.active {
  background: var(--white);
  color: var(--ink);
  box-shadow: var(--shadow-sm);
}

.filter-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  border: 1.5px solid var(--beige-dark);
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-light);
  background: var(--white);
  cursor: pointer;
  transition: all 0.2s ease;
  margin-left: auto;
}

.filter-btn:hover { border-color: var(--sand); }

.filter-btn.has-filters {
  background: var(--ink);
  color: var(--cream);
  border-color: var(--ink);
}

.filter-count {
  background: var(--terracotta);
  color: white;
  font-size: 11px;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
}

.sort-btn {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 8px 12px;
  border: 1.5px solid var(--beige-dark);
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 13px;
  font-weight: 500;
  color: var(--ink-light);
  background: var(--white);
  cursor: pointer;
  transition: all 0.2s;
}

/* ─── Market Cards ─── */
.markets-list {
  padding: 0 20px 100px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.market-card {
  background: var(--white);
  border-radius: var(--radius-lg);
  padding: 16px;
  box-shadow: var(--shadow-sm);
  cursor: pointer;
  transition: all 0.25s ease;
  animation: fadeInUp 0.4s ease both;
  border: 1px solid rgba(44,36,22,0.04);
  position: relative;
  overflow: hidden;
}

.market-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-1px);
}

.market-card::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  border-radius: 4px 0 0 4px;
}

.card-top {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 8px;
}

.card-badges {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  align-items: center;
}

.category-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  border-radius: 100px;
  font-size: 12px;
  font-weight: 600;
  letter-spacing: 0.02em;
}

.date-badge {
  display: inline-flex;
  align-items: center;
  padding: 3px 10px;
  border-radius: 100px;
  font-size: 11px;
  font-weight: 600;
  color: white;
  letter-spacing: 0.02em;
}

.fav-btn {
  background: none;
  border: none;
  cursor: pointer;
  padding: 4px;
  transition: all 0.2s;
  color: var(--ink-lighter);
  flex-shrink: 0;
}

.fav-btn:hover { color: var(--terracotta); }
.fav-btn.active { color: var(--terracotta); animation: heartPop 0.35s ease; }

.card-name {
  font-family: var(--font-display);
  font-size: 18px;
  color: var(--ink);
  margin-bottom: 6px;
  line-height: 1.25;
}

.card-info {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 14px;
  font-size: 13px;
  color: var(--ink-light);
}

.card-info-item {
  display: flex;
  align-items: center;
  gap: 5px;
}

.card-distance {
  color: var(--olive);
  font-weight: 600;
}

/* ─── Map View ─── */
.map-container {
  position: relative;
  height: calc(100vh - 260px);
  background: var(--beige);
  margin: 0 20px;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

.map-svg {
  width: 100%;
  height: 100%;
}

.map-pin {
  cursor: pointer;
  transition: all 0.2s ease;
}

.map-pin:hover {
  transform: scale(1.15);
}

.map-tooltip {
  position: absolute;
  background: var(--white);
  border-radius: var(--radius-md);
  padding: 14px 16px;
  box-shadow: var(--shadow-lg);
  z-index: 20;
  min-width: 220px;
  max-width: 280px;
  animation: scaleIn 0.2s ease;
  border: 1px solid rgba(44,36,22,0.06);
}

.tooltip-name {
  font-family: var(--font-display);
  font-size: 16px;
  margin-bottom: 6px;
}

.tooltip-meta {
  font-size: 13px;
  color: var(--ink-light);
  margin-bottom: 10px;
  display: flex;
  flex-direction: column;
  gap: 3px;
}

.tooltip-actions {
  display: flex;
  gap: 8px;
}

.tooltip-actions button {
  flex: 1;
  padding: 8px;
  border: 1.5px solid var(--beige-dark);
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 12px;
  font-weight: 600;
  background: var(--white);
  color: var(--ink);
  cursor: pointer;
  transition: all 0.15s;
}

.tooltip-actions button:hover {
  background: var(--beige);
}

.tooltip-actions button.primary {
  background: var(--terracotta);
  color: white;
  border-color: var(--terracotta);
}

/* ─── Detail Page ─── */
.detail-page {
  position: fixed;
  inset: 0;
  z-index: 100;
  background: var(--cream);
  overflow-y: auto;
  animation: slideUp 0.35s cubic-bezier(0.16, 1, 0.3, 1);
}

.detail-hero {
  position: relative;
  padding: 60px 24px 32px;
  background: linear-gradient(135deg, var(--beige) 0%, var(--beige-dark) 100%);
  overflow: hidden;
}

.detail-hero::before {
  content: '';
  position: absolute;
  top: -50px;
  right: -50px;
  width: 200px;
  height: 200px;
  border-radius: 50%;
  opacity: 0.06;
}

.detail-back {
  position: absolute;
  top: 16px;
  left: 16px;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--white);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-sm);
  color: var(--ink);
  transition: all 0.2s;
  z-index: 5;
}

.detail-back:hover { box-shadow: var(--shadow-md); }

.detail-actions-top {
  position: absolute;
  top: 16px;
  right: 16px;
  display: flex;
  gap: 8px;
  z-index: 5;
}

.detail-icon-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: var(--white);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: var(--shadow-sm);
  transition: all 0.2s;
  color: var(--ink-light);
}

.detail-icon-btn:hover { box-shadow: var(--shadow-md); }
.detail-icon-btn.fav-active { color: var(--terracotta); }

.detail-category-tag {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 14px;
  border-radius: 100px;
  font-size: 13px;
  font-weight: 600;
  margin-bottom: 12px;
}

.detail-name {
  font-family: var(--font-display);
  font-size: 30px;
  line-height: 1.15;
  color: var(--ink);
  margin-bottom: 8px;
}

.detail-city {
  font-size: 15px;
  color: var(--ink-light);
  font-weight: 500;
}

.detail-body {
  padding: 24px;
}

.detail-section {
  margin-bottom: 24px;
  animation: fadeInUp 0.4s ease both;
}

.detail-section-title {
  font-family: var(--font-display);
  font-size: 17px;
  color: var(--ink);
  margin-bottom: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.detail-dates-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.date-chip {
  padding: 6px 14px;
  border-radius: 100px;
  font-size: 13px;
  font-weight: 500;
  background: var(--beige);
  color: var(--ink-light);
  border: 1px solid var(--beige-dark);
}

.date-chip.today {
  background: var(--terracotta);
  color: white;
  border-color: var(--terracotta);
}

.date-chip.weekend {
  background: var(--olive);
  color: white;
  border-color: var(--olive);
}

.detail-hours {
  font-size: 22px;
  font-weight: 600;
  color: var(--ink);
  letter-spacing: -0.02em;
}

.detail-recurrence {
  font-size: 14px;
  color: var(--ink-lighter);
  margin-top: 4px;
}

.detail-address {
  font-size: 15px;
  color: var(--ink-light);
  line-height: 1.5;
  margin-bottom: 12px;
}

.detail-address-actions {
  display: flex;
  gap: 8px;
}

.detail-address-actions button {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 11px 16px;
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.detail-address-actions button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  background: var(--beige);
  color: var(--ink-lighter);
  border: 1px solid var(--beige-dark);
}


.btn-primary {
  background: var(--terracotta);
  color: white;
  border: none;
}
.btn-primary:hover { background: #b5443a; }

.btn-secondary {
  background: var(--white);
  color: var(--ink);
  border: 1.5px solid var(--beige-dark);
}
.btn-secondary:hover { background: var(--beige); }

.detail-description {
  font-size: 15px;
  line-height: 1.7;
  color: var(--ink-light);
}

.detail-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.detail-tag {
  padding: 5px 12px;
  border-radius: 100px;
  font-size: 12px;
  font-weight: 500;
  background: var(--beige);
  color: var(--ink-light);
  border: 1px solid var(--beige-dark);
}

.detail-provenance {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  background: var(--beige);
  border-radius: var(--radius-md);
  font-size: 13px;
  color: var(--ink-lighter);
}

.confidence-bar {
  height: 4px;
  background: var(--beige-dark);
  border-radius: 2px;
  width: 60px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 0.5s ease;
}

/* ─── Mini Map in Detail ─── */
.detail-minimap {
  width: 100%;
  height: 140px;
  border-radius: var(--radius-md);
  overflow: hidden;
  background: var(--beige);
  margin-bottom: 12px;
  position: relative;
}

/* ─── Filter Panel ─── */
.filter-overlay {
  position: fixed;
  inset: 0;
  background: rgba(44,36,22,0.4);
  backdrop-filter: blur(4px);
  z-index: 80;
  animation: fadeIn 0.2s ease;
}

.filter-panel {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 480px;
  max-height: 85vh;
  background: var(--cream);
  border-radius: var(--radius-xl) var(--radius-xl) 0 0;
  z-index: 85;
  overflow-y: auto;
  animation: slideUp 0.35s cubic-bezier(0.16, 1, 0.3, 1);
  box-shadow: 0 -4px 30px rgba(44,36,22,0.15);
}

.filter-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 24px 12px;
  position: sticky;
  top: 0;
  background: var(--cream);
  z-index: 5;
  border-bottom: 1px solid var(--beige-dark);
}

.filter-title {
  font-family: var(--font-display);
  font-size: 22px;
}

.filter-close {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--beige);
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-light);
  transition: all 0.2s;
}

.filter-body {
  padding: 20px 24px;
}

.filter-section {
  margin-bottom: 24px;
}

.filter-section-label {
  font-size: 13px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: var(--ink-lighter);
  margin-bottom: 10px;
}

.filter-categories {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.filter-cat-chip {
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 8px 14px;
  border-radius: 100px;
  font-size: 13px;
  font-weight: 500;
  border: 1.5px solid var(--beige-dark);
  background: var(--white);
  color: var(--ink-light);
  cursor: pointer;
  transition: all 0.2s;
}

.filter-cat-chip.active {
  border-color: currentColor;
  font-weight: 600;
}

.filter-select {
  width: 100%;
  padding: 10px 14px;
  border: 1.5px solid var(--beige-dark);
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 14px;
  color: var(--ink);
  background: var(--white);
  appearance: none;
  cursor: pointer;
  outline: none;
  transition: border-color 0.2s;
}

.filter-select:focus { border-color: var(--olive); }

.range-container {
  padding: 8px 0;
}

.range-label {
  display: flex;
  justify-content: space-between;
  font-size: 14px;
  color: var(--ink-light);
  margin-bottom: 8px;
}

.range-value {
  font-weight: 700;
  color: var(--ink);
}

.range-input {
  width: 100%;
  -webkit-appearance: none;
  height: 6px;
  border-radius: 3px;
  background: var(--beige-dark);
  outline: none;
}

.range-input::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--terracotta);
  cursor: pointer;
  box-shadow: 0 2px 6px rgba(199,81,70,0.3);
  transition: transform 0.15s;
}

.range-input::-webkit-slider-thumb:hover {
  transform: scale(1.15);
}

.filter-footer {
  display: flex;
  gap: 10px;
  padding: 16px 24px 28px;
  border-top: 1px solid var(--beige-dark);
  position: sticky;
  bottom: 0;
  background: var(--cream);
}

.filter-footer button {
  flex: 1;
  padding: 13px;
  border-radius: var(--radius-md);
  font-family: var(--font-body);
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-reset {
  background: var(--beige);
  color: var(--ink-light);
  border: 1.5px solid var(--beige-dark);
}

.filter-apply {
  background: var(--terracotta);
  color: white;
  border: none;
}

.filter-apply:hover { background: #b5443a; }

/* ─── Sorting Dropdown ─── */
.sort-dropdown {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: var(--white);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-lg);
  z-index: 60;
  overflow: hidden;
  min-width: 180px;
  animation: scaleIn 0.15s ease;
  border: 1px solid rgba(44,36,22,0.06);
}

.sort-option {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 12px 16px;
  font-size: 14px;
  color: var(--ink-light);
  cursor: pointer;
  border: none;
  background: none;
  width: 100%;
  text-align: left;
  font-family: var(--font-body);
  transition: background 0.15s;
}

.sort-option:hover { background: var(--beige); }
.sort-option.active { color: var(--terracotta); font-weight: 600; }

/* ─── Bottom Tabs ─── */
.bottom-tabs {
  position: fixed;
  bottom: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 100%;
  max-width: 480px;
  background: var(--white);
  border-top: 1px solid var(--beige-dark);
  display: flex;
  padding: 6px 8px 22px;
  z-index: 70;
  backdrop-filter: blur(12px);
}

.tab-btn {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 8px 4px;
  border: none;
  background: none;
  cursor: pointer;
  color: var(--ink-lighter);
  font-family: var(--font-body);
  font-size: 11px;
  font-weight: 500;
  transition: color 0.2s;
  position: relative;
}

.tab-btn.active {
  color: var(--terracotta);
}

.tab-btn.active::before {
  content: '';
  position: absolute;
  top: 0;
  left: 50%;
  transform: translateX(-50%);
  width: 24px;
  height: 3px;
  border-radius: 0 0 3px 3px;
  background: var(--terracotta);
}

/* ─── Favorites Page ─── */
.page-content {
  padding: 0 20px 100px;
}

.empty-state {
  text-align: center;
  padding: 60px 20px;
  animation: fadeIn 0.4s ease;
}

.empty-icon {
  font-size: 48px;
  margin-bottom: 16px;
  opacity: 0.4;
}

.empty-title {
  font-family: var(--font-display);
  font-size: 20px;
  color: var(--ink);
  margin-bottom: 8px;
}

.empty-text {
  font-size: 14px;
  color: var(--ink-lighter);
  line-height: 1.5;
}

/* ─── Notifications / Settings ─── */
.setting-card {
  background: var(--white);
  border-radius: var(--radius-lg);
  padding: 18px 20px;
  margin-bottom: 12px;
  box-shadow: var(--shadow-sm);
  border: 1px solid rgba(44,36,22,0.04);
}

.setting-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.setting-label {
  font-size: 15px;
  font-weight: 500;
  color: var(--ink);
}

.setting-sublabel {
  font-size: 13px;
  color: var(--ink-lighter);
  margin-top: 2px;
}

/* Toggle Switch */
.toggle {
  position: relative;
  width: 48px;
  height: 28px;
  flex-shrink: 0;
}

.toggle input {
  opacity: 0;
  width: 0;
  height: 0;
}

.toggle-track {
  position: absolute;
  inset: 0;
  background: var(--beige-dark);
  border-radius: 14px;
  cursor: pointer;
  transition: background 0.25s;
}

.toggle input:checked + .toggle-track {
  background: var(--olive);
}

.toggle-track::after {
  content: '';
  position: absolute;
  left: 3px;
  top: 3px;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--white);
  box-shadow: 0 1px 4px rgba(0,0,0,0.15);
  transition: transform 0.25s cubic-bezier(0.16, 1, 0.3, 1);
}

.toggle input:checked + .toggle-track::after {
  transform: translateX(20px);
}

/* ─── Location Selection ─── */
.location-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 16px;
}

.location-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1.5px solid var(--beige-dark);
  border-radius: var(--radius-md);
  background: var(--white);
  cursor: pointer;
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 500;
  color: var(--ink);
  transition: all 0.2s;
}

.location-option:hover { border-color: var(--sand); }
.location-option.active {
  border-color: var(--olive);
  background: var(--olive-pale);
}

.location-option .icon-circle {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  background: var(--beige);
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--ink-light);
}

.manual-city-input {
  display: flex;
  gap: 8px;
  margin-top: 10px;
  animation: fadeIn 0.2s ease;
}

.manual-city-input input {
  flex: 1;
  padding: 10px 14px;
  border: 1.5px solid var(--beige-dark);
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 14px;
  outline: none;
  transition: border-color 0.2s;
}

.manual-city-input input:focus { border-color: var(--olive); }

.manual-city-input button {
  padding: 10px 20px;
  background: var(--olive);
  color: white;
  border: none;
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
}

/* ─── Settings time pickers ─── */
.time-row {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-top: 10px;
}

.time-row label {
  font-size: 13px;
  color: var(--ink-lighter);
  min-width: 30px;
}

.time-row input[type="time"] {
  padding: 8px 10px;
  border: 1.5px solid var(--beige-dark);
  border-radius: var(--radius-sm);
  font-family: var(--font-body);
  font-size: 14px;
  outline: none;
  color: var(--ink);
}

/* ─── Scrollbar ─── */
.detail-page::-webkit-scrollbar,
.filter-panel::-webkit-scrollbar { width: 0; }

/* ─── Results count ─── */
.results-count {
  padding: 0 20px 8px;
  font-size: 13px;
  color: var(--ink-lighter);
  font-weight: 500;
}

/* ─── Copied toast ─── */
.toast {
  position: fixed;
  bottom: 90px;
  left: 50%;
  transform: translateX(-50%);
  background: var(--ink);
  color: var(--cream);
  padding: 10px 20px;
  border-radius: 100px;
  font-size: 14px;
  font-weight: 500;
  z-index: 200;
  animation: fadeInUp 0.3s ease;
  box-shadow: var(--shadow-lg);
}

/* ─── App version ─── */
.app-version {
  text-align: center;
  font-size: 12px;
  color: var(--ink-lighter);
  padding: 20px;
  opacity: 0.6;
}
`;

// ─── Main App ───────────────────────────────────────────────
export default function App() {
  // Data from Firebase (auto-seeds on first load)
  const {
    markets: allMarkets,
    loading: marketsLoading,
    error: marketsError,
    seedStatus,
    favorites,
    toggleFav: hookToggleFav,
    getMarketDetails,
    categories: hookCategories,
    regions: hookRegions,
    cities: hookCities,
    categoryIcons: hookCatIcons,
    categoryColors: hookCatColors,
    dataMode,
    userLat, userLng, positionStatus, positionError,
    requestPosition, clearPosition,
  } = useMarkets();

  const [tab, setTab] = useState("esplora");
  const [viewMode, setViewMode] = useState("lista");
  const [searchQuery, setSearchQuery] = useState("");
  // Prioritize visits people can actually plan; deselect to browse undated markets.
  const [dateFilter, setDateFilter] = useState('7giorni');
  const [visibleCount, setVisibleCount] = useState(60);
  const [showFilters, setShowFilters] = useState(false);
  const [showSort, setShowSort] = useState(false);
  const [sortBy, setSortBy] = useState("data");
  const [selectedMarket, setSelectedMarket] = useState(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState('');

  const [toast, setToast] = useState(null);

  // Filter states
  const [filterCategories, setFilterCategories] = useState([]);
  const [filterRegion, setFilterRegion] = useState("");
  const [filterCity, setFilterCity] = useState("");
  const [filterDistance, setFilterDistance] = useState(100);
  const [includeEstimatedNearby, setIncludeEstimatedNearby] = useState(false);
  const [activeFilterCount, setActiveFilterCount] = useState(0);

  // Pending filter states (applied on "Applica")
  const [pendingCats, setPendingCats] = useState([]);
  const [pendingRegion, setPendingRegion] = useState("");
  const [pendingCity, setPendingCity] = useState("");
  const [pendingDist, setPendingDist] = useState(100);

  // Settings
  const [locationMode, setLocationMode] = useState("none");
  const [manualCity, setManualCity] = useState("");

  // Map state
  const [hoveredPin, setHoveredPin] = useState(null);
  const mapRef = useRef(null);

  // Bridge: use hook's categories/colors/icons, falling back to local constants
  const CATS = hookCategories.length > 0 ? hookCategories : CATEGORIES;
  const CAT_ICONS = Object.keys(hookCatIcons).length > 0 ? hookCatIcons : CATEGORY_ICONS;
  const CAT_COLORS = Object.keys(hookCatColors).length > 0 ? hookCatColors : CATEGORY_COLORS;
  const REGS = hookRegions.length > 0 ? hookRegions : REGIONS;
  const CTS = hookCities.length > 0 ? hookCities : CITIES;
  const canUseDistance = Number.isFinite(userLat) && Number.isFinite(userLng);

  const toggleFav = useCallback((id, e) => {
    if (e) e.stopPropagation();
    hookToggleFav(id);
  }, [hookToggleFav]);

  const openMarket = useCallback(async (market) => {
    setSelectedMarket(market);
    setDetailError('');
    setDetailLoading(true);
    try {
      const detailed = await getMarketDetails(market.id);
      setSelectedMarket(current => current?.id === market.id ? (detailed || market) : current);
    } catch (error) {
      setDetailError(error.message || 'Impossibile caricare i dettagli');
    } finally {
      setDetailLoading(false);
    }
  }, [getMarketDetails]);

  const showToast = useCallback((msg) => {
    setToast(msg);
    setTimeout(() => setToast(null), 2000);
  }, []);

  // Details are shareable by URL hash: no server-side route required.
  useEffect(() => {
    const openHash = () => {
      const hash = window.location.hash.replace(/^#/, '');
      const id = new URLSearchParams(hash).get('mercato');
      const item = id && allMarkets.find(market => market.id === id);
      if (item) openMarket(item);
    };
    openHash();
    window.addEventListener('hashchange', openHash);
    return () => window.removeEventListener('hashchange', openHash);
  }, [allMarkets, openMarket]);

  const closeMarket = () => {
    setSelectedMarket(null);
    if (window.location.hash.startsWith('#mercato=')) {
      window.history.replaceState(null, '', window.location.pathname + window.location.search);
    }
  };

  const shareMarket = async (market) => {
    const url = new URL(window.location.href);
    url.hash = 'mercato=' + encodeURIComponent(market.id);
    const payload = { title: market.name, text: market.city, url: url.toString() };
    try {
      if (navigator.share) {
        await navigator.share(payload);
      } else if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(payload.url);
        showToast('Link del mercato copiato.');
      } else {
        window.prompt('Copia questo link per condividerlo:', payload.url);
      }
    } catch (error) {
      if (error?.name !== 'AbortError') showToast('Condivisione non riuscita.');
    }
  };

  const destinationForMarket = (market) => {
    // Use exact official coordinates first. Guessed city-centre coordinates
    // and vague strings such as "centro" are NOT navigable market addresses.
    if (market.positionQuality === 'precisa' &&
        Number.isFinite(market.lat) && Number.isFinite(market.lng)) {
      return market.lat + ',' + market.lng;
    }
    const address = market.address?.trim() || '';
    const specificStreet = /\b(via|viale|piazza|piazzale|piazzetta|corso|largo|vicolo|strada|contrada|lungomare|località|localita|borgo|parco)\b/i;
    if (address.length >= 9 && specificStreet.test(address)) {
      return [market.name, address, market.city, 'Italia'].filter(Boolean).join(', ');
    }
    return null;
  };

  const openDirections = (market) => {
    const destination = destinationForMarket(market);
    if (!destination) {
      showToast('Indirizzo non abbastanza preciso per navigare.');
      return;
    }
    const url = 'https://www.google.com/maps/dir/?api=1&destination=' + encodeURIComponent(destination);
    window.open(url, '_blank', 'noopener,noreferrer');
  };

  const copyMarketAddress = async (market) => {
    if (!market.address?.trim()) {
      showToast('Indirizzo non disponibile.');
      return;
    }
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard not supported');
      await navigator.clipboard.writeText(market.address);
      showToast('Indirizzo copiato.');
    } catch {
      showToast('Seleziona il testo dell’indirizzo per copiarlo.');
    }
  };

  const activateNearby = () => {
    setLocationMode('auto');
    setFilterCity('');
    setIncludeEstimatedNearby(false);
    setFilterDistance(50);
    setActiveFilterCount(1 + Number(filterCategories.length > 0) + Number(Boolean(filterRegion)));
    setSortBy('distanza');
    requestPosition();
  };

  const confirmManualCity = () => {
    const name = manualCity.trim().toLocaleLowerCase('it');
    const match = CTS.find(city => city.toLocaleLowerCase('it') === name);
    if (!match) {
      showToast('Scegli una città presente nel catalogo.');
      return;
    }
    clearPosition();
    setLocationMode('manual');
    setFilterCity(match);
    setFilterRegion('');
    setFilterDistance(100);
    setSortBy('data');
    setActiveFilterCount(1);
    setTab('esplora');
    showToast('Filtra per città: ' + match);
  };

  const disableLocation = () => {
    clearPosition();
    setLocationMode('none');
    setFilterCity('');
    setFilterDistance(100);
    setActiveFilterCount(Number(filterCategories.length > 0) + Number(Boolean(filterRegion)));
    setSortBy('data');
  };

  // Use hook's markets (already have distances computed)
  const marketsWithDistance = allMarkets;

  // Render at most 60 cards initially on slow mobile browsers.
  useEffect(() => setVisibleCount(60), [searchQuery, dateFilter, filterCategories, filterRegion, filterCity, filterDistance, sortBy, canUseDistance, includeEstimatedNearby]);

  // Apply filters
  const filteredMarkets = useMemo(() => {
    let result = [...marketsWithDistance];

    // Search
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase();
      result = result.filter(m =>
        m.name.toLowerCase().includes(q) ||
        m.city.toLowerCase().includes(q) ||
        m.category.toLowerCase().includes(q) ||
        m.tags.some(t => t.toLowerCase().includes(q))
      );
    }

    // Date filter
    if (dateFilter === "oggi") {
      result = result.filter(m => m.dates.includes(todayStr));
    } else if (dateFilter === "weekend") {
      const dayOfWeek = TODAY.getDay();
      const satOffset = dayOfWeek === 0 ? -1 : 6 - dayOfWeek;
      const sat = new Date(TODAY); sat.setDate(sat.getDate() + satOffset);
      const sun = new Date(sat); sun.setDate(sun.getDate() + 1);
      const satStr = localISO(sat);
      const sunStr = localISO(sun);
      result = result.filter(m => m.dates.includes(satStr) || m.dates.includes(sunStr));
    } else if (dateFilter === "7giorni") {
      const end = new Date(TODAY); end.setDate(end.getDate() + 7);
      const endStr = localISO(end);
      result = result.filter(m => m.dates.some(d => d >= todayStr && d <= endStr));
    }

    // Category filter
    if (filterCategories.length > 0) {
      result = result.filter(m => filterCategories.includes(m.category));
    }

    // Region
    if (filterRegion) {
      result = result.filter(m => m.region === filterRegion);
    }

    // City
    if (filterCity) {
      result = result.filter(m => m.city === filterCity);
    }

    // Distance
    if (canUseDistance && filterDistance < 100) {
      result = result.filter(m =>
        Number.isFinite(m.distance) &&
        m.distance <= filterDistance &&
        (includeEstimatedNearby || m.positionQuality === 'precisa')
      );
    }

    // Sort
    if (sortBy === "distanza" && canUseDistance) {
      const priority = (market) => market.positionQuality === 'precisa'
        ? 0 : market.positionQuality === 'approssimata' ? 1 : 2;
      result.sort((a, b) => priority(a) - priority(b) ||
        (a.distance ?? Infinity) - (b.distance ?? Infinity));
    } else {
      // Same-day markets should not default to an accidental alphabetical
      // order by region (Abruzzo -> Veneto). Prefer more useful records.
      const rank = market =>
        (market.dateQuality === 'confermata' ? 50 : 0) +
        (market.positionQuality === 'precisa' ? 9 : 0) +
        (market.hours ? 5 : 0) +
        (market.category !== 'Misto' ? 3 : 0);
      result.sort((a, b) => {
        const aDate = getNextDate(a.dates);
        const bDate = getNextDate(b.dates);
        return (aDate || '9999').localeCompare(bDate || '9999') ||
          rank(b) - rank(a) ||
          a.name.localeCompare(b.name, 'it');
      });
    }

    return result;
  }, [marketsWithDistance, searchQuery, dateFilter, filterCategories, filterRegion, filterCity, filterDistance, sortBy, canUseDistance, includeEstimatedNearby]);

  const openFilters = () => {
    setPendingCats([...filterCategories]);
    setPendingRegion(filterRegion);
    setPendingCity(filterCity);
    setPendingDist(filterDistance);
    setShowFilters(true);
  };

  const applyFilters = () => {
    setFilterCategories(pendingCats);
    setFilterRegion(pendingRegion);
    setFilterCity(pendingCity);
    setFilterDistance(canUseDistance ? pendingDist : 100);
    let count = 0;
    if (pendingCats.length > 0) count++;
    if (pendingRegion) count++;
    if (pendingCity) count++;
    if (canUseDistance && pendingDist < 100) count++;
    setActiveFilterCount(count);
    setShowFilters(false);
  };

  const resetFilters = () => {
    setPendingCats([]);
    setPendingRegion("");
    setPendingCity("");
    setPendingDist(100);
    setFilterCategories([]);
    setFilterRegion("");
    setFilterCity("");
    setFilterDistance(100);
    setActiveFilterCount(0);
    setIncludeEstimatedNearby(false);
    setShowFilters(false);
  };

  const resetAllFilters = () => {
    setFilterCategories([]);
    setFilterRegion("");
    setFilterCity("");
    setFilterDistance(100);
    setIncludeEstimatedNearby(false);
    setActiveFilterCount(0);
    setDateFilter(null);
    setSearchQuery("");
  };

  // ─── Map projection (Italy bounds) ────────────
  const mapProject = useCallback((lat, lng, w, h) => {
    const minLat = 36.5, maxLat = 47.5, minLng = 6.5, maxLng = 19.5;
    const x = ((lng - minLng) / (maxLng - minLng)) * w;
    const y = ((maxLat - lat) / (maxLat - minLat)) * h;
    return { x, y };
  }, []);

  // ─── Render Functions ─────────────────────────

  const renderMarketCard = (market, index) => {
    const badge = getDateBadge(market.dates, market.dateQuality);
    const nextDate = getNextDate(market.dates);
    const catColor = CAT_COLORS[market.category] || "#888";
    const isFav = favorites.has(market.id);

    return (
      <div
        key={market.id}
        className="market-card"
        style={{ animationDelay: `${Math.min(index, 12) * 50}ms`, '--cat-color': catColor }}
        onClick={() => openMarket(market)}
        tabIndex={0}
        role="button"
        aria-label={'Apri i dettagli di ' + market.name}
        onKeyDown={(e) => {
          if (e.target === e.currentTarget && (e.key === 'Enter' || e.key === ' ')) {
            e.preventDefault();
            openMarket(market);
          }
        }}
      >
        <div style={{ position: 'absolute', left: 0, top: 0, bottom: 0, width: 4, background: catColor, borderRadius: '4px 0 0 4px' }} />
        <div className="card-top">
          <div className="card-badges">
            <span className="category-badge" style={{ background: catColor + '14', color: catColor }}>
              {CAT_ICONS[market.category]} {market.category}
            </span>
            {badge && (
              <span className="date-badge" style={{ background: badge.color }}>
                {badge.label}
              </span>
            )}
          </div>
          <button
            className={`fav-btn ${isFav ? 'active' : ''}`}
            onClick={(e) => toggleFav(market.id, e)}
            aria-label={isFav ? "Rimuovi dai preferiti" : "Aggiungi ai preferiti"}
          >
            <Icon name={isFav ? "heartFilled" : "heart"} size={20} />
          </button>
        </div>

        <div className="card-name">{market.name}</div>

        <div className="card-info">
          <span className="card-info-item">
            <Icon name="calendar" size={14} color="#8C8272" />
            {formatDateIT(nextDate)}
          </span>
          <span className="card-info-item">
            <Icon name="clock" size={14} color="#8C8272" />
            {market.hours || 'Orari da verificare'}
          </span>
          <span className="card-info-item">
            <Icon name="mapPin" size={14} color="#8C8272" />
            {market.city}
          </span>
          {canUseDistance && (
            <span className="card-info-item card-distance">
              {market.positionQuality === 'precisa' && Number.isFinite(market.distance)
                ? 'a ' + Math.round(market.distance) + ' km'
                : market.positionQuality === 'approssimata' && Number.isFinite(market.distance)
                  ? 'circa ' + Math.round(market.distance) + ' km (stimati)'
                  : 'Posizione da verificare'}
            </span>
          )}
        </div>
      </div>
    );
  };

  const renderMapView = () => (
    <Suspense fallback={<div role="status" style={{
      margin: '22px 18px 110px', padding: 22, background: 'var(--white)',
      borderRadius: 12, color: 'var(--ink-lighter)' }}>Caricamento mappa interattiva…</div>}>
      <MarketsMap markets={filteredMarkets} userLat={userLat} userLng={userLng}
        onSelect={openMarket} />
    </Suspense>
  );

  const renderDetail = () => {
    if (!selectedMarket) return null;
    const m = selectedMarket;
    const catColor = CAT_COLORS[m.category] || "#888";
    const isFav = favorites.has(m.id);
    const futureDates = m.dates.filter(d => d >= todayStr).sort();

    return (
      <div className="detail-page">
        <div className="detail-hero" style={{ background: `linear-gradient(135deg, ${catColor}08 0%, ${catColor}14 100%)` }}>
          <div style={{ position: 'absolute', top: -40, right: -40, width: 180, height: 180, borderRadius: '50%', background: catColor, opacity: 0.04 }} />
          <button className="detail-back" onClick={closeMarket}>
            <Icon name="chevronLeft" size={20} />
          </button>
          <div className="detail-actions-top">
            <button className="detail-icon-btn" onClick={() => shareMarket(m)} aria-label="Condividi questo mercato">
              <Icon name="share" size={18} />
            </button>
            <button
              className={`detail-icon-btn ${isFav ? 'fav-active' : ''}`}
              onClick={() => toggleFav(m.id)}
            >
              <Icon name={isFav ? "heartFilled" : "heart"} size={18} />
            </button>
          </div>

          <span className="detail-category-tag" style={{ background: catColor + '18', color: catColor }}>
            {CAT_ICONS[m.category]} {m.category}
          </span>
          <div className="detail-name">{m.name}</div>
          {detailLoading && <div style={{ fontSize: 12, marginTop: 8 }}>Caricamento dettagli completi…</div>}
          {detailError && <div role="alert" style={{ fontSize: 12, marginTop: 8 }}>
            {detailError}. Sono visibili i dati sintetici.
          </div>}

          <div className="detail-city">
            <Icon name="mapPin" size={14} color={catColor} strokeWidth={2} /> {m.city}, {m.region}
          </div>
        </div>

        <div className="detail-body">
          {/* Dates */}
          <div className="detail-section" style={{ animationDelay: '0.05s' }}>
            <div className="detail-section-title">
              <Icon name="calendar" size={18} color={catColor} /> Prossime date
            </div>
            <div className="detail-dates-chips">
              {futureDates.length === 0 && <span className="date-chip">Date da verificare</span>}
              {futureDates.map(d => {
                const isToday = d === todayStr;
                const dayOfWeek = new Date(d + "T00:00:00").getDay();
                const isWeekend = dayOfWeek === 0 || dayOfWeek === 6;
                return (
                  <span key={d} className={`date-chip ${isToday ? 'today' : isWeekend ? 'weekend' : ''}`}>
                    {formatDateIT(d)}
                  </span>
                );
              })}
            </div>
            {m.recurrence && (
              <div className="detail-recurrence">{m.recurrence}</div>
            )}
            {m.dateQuality !== 'confermata' && (
              <div style={{ fontSize: 12, color: '#8C8272', marginTop: 8 }}>
                Date previste, non confermate per ogni singola edizione. Controlla la fonte prima di partire.
              </div>
            )}
          </div>

          {/* Hours */}
          <div className="detail-section" style={{ animationDelay: '0.1s' }}>
            <div className="detail-section-title">
              <Icon name="clock" size={18} color={catColor} /> Orari
            </div>
            <div className="detail-hours">{m.hours || "Orari non disponibili"}</div>
          </div>

          {/* Address */}
          <div className="detail-section" style={{ animationDelay: '0.15s' }}>
            <div className="detail-section-title">
              <Icon name="mapPin" size={18} color={catColor} /> Indirizzo
            </div>
            <div className="detail-address">{m.address || 'Indirizzo non verificato'}</div>
            {m.positionQuality !== 'precisa' && (
              <div style={{ fontSize: 12, color: '#8C8272', marginTop: 6 }}>Posizione indicativa o da verificare</div>
            )}
            {!destinationForMarket(m) && (
              <div role="note" style={{ fontSize: 12, color: '#8C8272', margin: '10px 0' }}>
                Indicazioni non disponibili: manca un indirizzo sufficientemente preciso.
              </div>
            )}
            <div className="detail-address-actions">
              <button className="btn-primary" onClick={() => openDirections(m)}
                disabled={!destinationForMarket(m)}
                title={!destinationForMarket(m) ? 'Indirizzo non sufficiente per navigare' : 'Apri indicazioni stradali'}>
                <Icon name="navigation" size={16} color="white" /> Indicazioni
              </button>
              <button className="btn-secondary" onClick={() => copyMarketAddress(m)}
                disabled={!m.address?.trim()}>
                <Icon name="copy" size={16} /> Copia
              </button>
            </div>
          </div>

          {/* Description */}
          {m.description && (
            <div className="detail-section" style={{ animationDelay: '0.2s' }}>
              <div className="detail-section-title">
                <Icon name="info" size={18} color={catColor} /> Descrizione
              </div>
              <div className="detail-description">{m.description}</div>
            </div>
          )}

          {/* Tags */}
          {m.tags && m.tags.length > 0 && (
            <div className="detail-section" style={{ animationDelay: '0.25s' }}>
              <div className="detail-section-title">Tag</div>
              <div className="detail-tags">
                {m.tags.map(t => (
                  <span key={t} className="detail-tag">{t}</span>
                ))}
              </div>
            </div>
          )}

          {/* Provenance */}
          <div className="detail-section" style={{ animationDelay: '0.3s' }}>
            <div className="detail-provenance">
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 13, marginBottom: 2 }}>
                  {m.lastVerified ? 'Verificato il ' + m.lastVerified : 'Non verificato di recente'}
                </div>
                <div style={{ fontSize: 12, opacity: 0.7 }}>
                  Fonte: {m.source || 'non disponibile'}
                  {m.sourceUpdated ? ' · dati del ' + m.sourceUpdated : ''}
                </div>
                {m.sourceUrl && (
                  <a href={m.sourceUrl} target="_blank" rel="noopener noreferrer"
                     style={{ display: 'inline-block', fontSize: 12, marginTop: 5 }}>
                    Controlla la fonte originale
                  </a>
                )}
              </div>
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: 11, marginBottom: 4 }}>Completezza dati</div>
                <div className="confidence-bar">
                  <div className="confidence-fill" style={{
                    width: `${m.dataCompleteness}%`,
                    background: m.dataCompleteness > 80 ? '#5B7A5E' : m.dataCompleteness > 55 ? '#B8860B' : '#C75146'
                  }} />
                </div>
                <div style={{ fontSize: 10, maxWidth: 135, marginTop: 5 }}>
                  Campi compilati, non verifica delle informazioni
                </div>
              </div>
            </div>
          </div>

          <div style={{ height: 40 }} />
        </div>
      </div>
    );
  };

  const renderFilterPanel = () => (
    <>
      <div className="filter-overlay" onClick={() => setShowFilters(false)} />
      <div className="filter-panel">
        <div className="filter-header">
          <span className="filter-title">Filtri</span>
          <button className="filter-close" onClick={() => setShowFilters(false)}>
            <Icon name="x" size={18} />
          </button>
        </div>
        <div className="filter-body">
          {/* Categories */}
          <div className="filter-section">
            <div className="filter-section-label">Categoria</div>
            <div className="filter-categories">
              {CATS.map(cat => {
                const active = pendingCats.includes(cat);
                const color = CAT_COLORS[cat];
                return (
                  <button key={cat}
                    className={`filter-cat-chip ${active ? 'active' : ''}`}
                    style={active ? { borderColor: color, color, background: color + '10' } : {}}
                    onClick={() => {
                      setPendingCats(prev =>
                        prev.includes(cat) ? prev.filter(c => c !== cat) : [...prev, cat]
                      );
                    }}
                  >
                    {CAT_ICONS[cat]} {cat}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Region */}
          <div className="filter-section">
            <div className="filter-section-label">Regione</div>
            <select className="filter-select" value={pendingRegion}
              onChange={e => { setPendingRegion(e.target.value); setPendingCity(""); }}>
              <option value="">Tutte le regioni</option>
              {REGS.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>

          {/* City */}
          <div className="filter-section">
            <div className="filter-section-label">Città</div>
            <select className="filter-select" value={pendingCity}
              onChange={e => setPendingCity(e.target.value)}>
              <option value="">Tutte le città</option>
              {CTS.filter(c => !pendingRegion || allMarkets.find(m => m.city === c)?.region === pendingRegion)
                .map(c => <option key={c} value={c}>{c}</option>)}
            </select>
          </div>

          {/* Distance */}
          <div className="filter-section">
            <div className="filter-section-label">Distanza massima</div>
            <div className="range-container">
              <div className="range-label">
                <span>0 km</span>
                <span className="range-value">{pendingDist} km</span>
              </div>
              <input type="range" className="range-input"
                min={5} max={100} step={5} value={pendingDist}
                disabled={!canUseDistance}
                onChange={e => setPendingDist(Number(e.target.value))} />
              {!canUseDistance && (
                <div className="setting-sublabel">
                  Per usare il raggio, attiva la posizione in Impostazioni.
                </div>
              )}
            </div>
          </div>
        </div>
        <div className="filter-footer">
          <button className="filter-reset" onClick={resetFilters}>Reimposta filtri</button>
          <button className="filter-apply" onClick={applyFilters}>Applica filtri</button>
        </div>
      </div>
    </>
  );

  const renderExplore = () => (
    <>
      <div className="header">
        <div className="header-title">
          <span className="accent">Mercati</span> d'Italia
        </div>

        <div className="search-container">
          <span className="search-icon"><Icon name="search" size={18} /></span>
          <input
            className="search-input"
            placeholder="Cerca città, mercato o parola chiave"
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>

        <div className="chips-row">
          {[
            { key: "oggi", label: "Oggi" },
            { key: "weekend", label: "Questo weekend" },
            { key: "7giorni", label: "Prossimi 7 giorni" },
          ].map(({ key, label }) => (
            <button key={key}
              className={`chip ${dateFilter === key ? 'active' : ''}`}
              onClick={() => setDateFilter(dateFilter === key ? null : key)}
            >{label}</button>
          ))}
        </div>

        {viewMode === 'lista' && !canUseDistance && !filterCity && !filterRegion && !searchQuery.trim() && (
          <div role="note" style={{
            background: '#F0EEE8', borderRadius: 12, padding: '12px 14px',
            margin: '6px 0 12px', fontSize: 12, lineHeight: 1.5,
            color: 'var(--ink-light)',
          }}>
            <strong style={{ display: 'block', marginBottom: 3, fontSize: 13, color: 'var(--ink)' }}>
              Stai esplorando tutta Italia
            </strong>
            Cerca la tua città nella barra sopra, oppure usa la posizione per trovare
            mercati nella tua zona. Le date automatiche non sono conferme degli organizzatori.
            <div style={{ display: 'flex', gap: 6, marginTop: 9, flexWrap: 'wrap' }}>
              {['Firenze', 'Roma', 'Milano'].map(city => (
                <button key={city} type="button" className="chip"
                  onClick={() => {
                    setFilterRegion('');
                    setFilterCity(city);
                    setActiveFilterCount(1);
                    setViewMode('lista');
                  }}>{city}</button>
              ))}
            </div>
          </div>
        )}
        {(filterCity || filterRegion || filterCategories.length > 0) && (
          <div className="chips-row" style={{ gap: 8, alignItems: 'center', margin: '2px 0 8px' }}>
            {filterCity && (
              <button className="chip active" onClick={() => {
                setFilterCity('');
                setActiveFilterCount(Math.max(0, activeFilterCount - 1));
              }} aria-label={'Rimuovi filtro città ' + filterCity}>Città: {filterCity} ×</button>
            )}
            {filterRegion && (
              <button className="chip active" onClick={() => {
                setFilterRegion('');
                setActiveFilterCount(Math.max(0, activeFilterCount - 1));
              }} aria-label={'Rimuovi filtro regione ' + filterRegion}>Regione: {filterRegion} ×</button>
            )}
            {filterCategories.length > 0 && (
              <button className="chip active" onClick={() => {
                setFilterCategories([]);
                setActiveFilterCount(Math.max(0, activeFilterCount - 1));
              }}>Categorie ×</button>
            )}
            <button className="chip" onClick={resetAllFilters}>Azzera filtri</button>
          </div>
        )}
        <div className="chips-row" style={{ marginTop: 8, alignItems: 'center' }}>
          <button className={`chip ${canUseDistance ? 'active' : ''}`} onClick={activateNearby}
            disabled={positionStatus === 'requesting'}>
            <Icon name="mapPin" size={13} />
            {positionStatus === 'ready' ? (includeEstimatedNearby ? 'Vicino a me · posizioni indicative' : 'Vicino a me · 50 km, posizioni precise') :
             positionStatus === 'requesting' ? 'Cerco la posizione…' : 'Mercati vicino a me'}
          </button>
          {positionError && <span role="alert" style={{ fontSize: 12, color: '#A5443D' }}>{positionError}</span>}
        </div>

        {canUseDistance && filterDistance < 100 && (
          <div role="note" style={{ fontSize: 12, lineHeight: 1.5, color: '#7D7267', margin: '4px 20px 10px' }}>
            {includeEstimatedNearby
              ? 'Mostriamo anche mercati con coordinate non verificate. Alcuni possono non essere davvero vicini.'
              : 'Nel raggio mostriamo solo mercati con posizione precisa. Altri mercati possono mancare.'}
            <button className="chip" style={{ display: 'block', marginTop: 8 }}
              onClick={() => setIncludeEstimatedNearby(prev => !prev)}>
              {includeEstimatedNearby ? 'Escludi posizioni indicative' : 'Mostra anche posizioni indicative'}
            </button>
          </div>
        )}
        <div className="controls-row">
          <div className="view-toggle">
            <button className={viewMode === "lista" ? "active" : ""} onClick={() => setViewMode("lista")}>
              <Icon name="list" size={14} /> Lista
            </button>
            <button className={viewMode === "mappa" ? "active" : ""} onClick={() => setViewMode("mappa")}>
              <Icon name="map" size={14} /> Mappa
            </button>
          </div>

          <div style={{ position: 'relative' }}>
            <button className="sort-btn" onClick={() => setShowSort(!showSort)}>
              <Icon name="sort" size={14} /> Ordina
            </button>
            {showSort && (
              <div className="sort-dropdown">
                {[
                  { key: "data", label: "Data", icon: "calendar" },
                  { key: "distanza", label: "Distanza", icon: "mapPin" },
                ].map(({ key, label, icon }) => (
                  <button key={key}
                    className={`sort-option ${sortBy === key ? 'active' : ''}`}
                    disabled={key === 'distanza' && !canUseDistance}
                    title={key === 'distanza' && !canUseDistance ? 'Attiva la posizione per ordinare per distanza' : ''}
                    onClick={() => { setSortBy(key); setShowSort(false); }}
                  >
                    <Icon name={icon} size={16} /> {label}
                    {sortBy === key && <Icon name="check" size={16} color="#C75146" />}
                  </button>
                ))}
              </div>
            )}
          </div>

          <button className={`filter-btn ${activeFilterCount > 0 ? 'has-filters' : ''}`}
            onClick={openFilters}>
            <Icon name="filter" size={14} /> Filtri
            {activeFilterCount > 0 && <span className="filter-count">{activeFilterCount}</span>}
          </button>
        </div>
      </div>

      <div className="results-count" style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <span>
          {marketsLoading
            ? 'Caricamento mercati statici...'
            : `${filteredMarkets.length.toLocaleString('it-IT')} mercat${filteredMarkets.length === 1 ? 'o' : 'i'} ${dateFilter === 'oggi' ? 'previsti oggi' : dateFilter === 'weekend' ? 'previsti nel weekend' : dateFilter === '7giorni' ? 'previsti nei prossimi 7 giorni' : 'nel catalogo'}${filterCity ? ' · ' + filterCity : filterRegion ? ' · ' + filterRegion : !canUseDistance ? ' · Italia' : ''}`
          }
        </span>
        {dataMode === 'demo' && (
          <span style={{
            fontSize: 10, fontWeight: 700, letterSpacing: '0.05em',
            padding: '2px 8px', borderRadius: 100, 
            background: 'var(--sand)', color: 'var(--ink-lighter)',
          }}>DEMO</span>
        )}
      </div>

      {marketsError && !marketsLoading && (
        <div role="alert" className="empty-state">
          <div className="empty-title">Catalogo temporaneamente non disponibile</div>
          <div className="empty-text">{marketsError}</div>
        </div>
      )}

      {marketsLoading ? (
        <div className="markets-list">
          {[1, 2, 3].map(i => (
            <div key={i} className="market-card" style={{
              height: 120, animation: 'none',
              background: 'linear-gradient(90deg, var(--white) 25%, var(--beige) 50%, var(--white) 75%)',
              backgroundSize: '200% 100%',
              animationName: 'shimmer', animationDuration: '1.5s',
              animationIterationCount: 'infinite', animationTimingFunction: 'linear',
            }} />
          ))}
        </div>
      ) : viewMode === "lista" ? (
        <div className="markets-list">
          {filteredMarkets.length > 0 ? (
            <>
              {filteredMarkets.slice(0, visibleCount).map((m, i) => renderMarketCard(m, i))}
              {visibleCount < filteredMarkets.length && (
                <button className="btn-secondary" onClick={() => setVisibleCount(n => n + 60)}
                  style={{ margin: '18px auto 30px', padding: '12px 24px', display: 'block' }}>
                  Mostra altri mercati ({Math.min(visibleCount, filteredMarkets.length)} di {filteredMarkets.length})
                </button>
              )}
            </>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">🔍</div>
              <div className="empty-title">Nessun mercato trovato</div>
              <div className="empty-text">
                {canUseDistance && filterDistance < 100 && !includeEstimatedNearby
                  ? 'Nessun mercato con posizione precisa in questo raggio e periodo. Puoi includere quelli con posizione indicativa.'
                  : 'Prova a cambiare data, distanza, città o categoria.'}
              </div>
              {canUseDistance && filterDistance < 100 && !includeEstimatedNearby && (
                <button className="btn-secondary" style={{ padding: '10px 18px', marginTop: 12 }}
                  onClick={() => setIncludeEstimatedNearby(true)}>Mostra posizioni indicative</button>
              )}
              <button style={{
                marginTop: 16, padding: '10px 24px', background: 'var(--terracotta)',
                color: 'white', border: 'none', borderRadius: 100, fontFamily: 'var(--font-body)',
                fontSize: 14, fontWeight: 600, cursor: 'pointer'
              }} onClick={resetAllFilters}>
                Reimposta
              </button>
            </div>
          )}
        </div>
      ) : (
        renderMapView()
      )}
    </>
  );

  const renderFavorites = () => {
    const favMarkets = marketsWithDistance.filter(m => favorites.has(m.id));
    return (
      <>
        <div className="header">
          <div className="header-title">Preferiti</div>
        </div>
        <div className="page-content">
          {favMarkets.length > 0 ? (
            <div className="markets-list" style={{ padding: 0 }}>
              {favMarkets.map((m, i) => renderMarketCard(m, i))}
            </div>
          ) : (
            <div className="empty-state">
              <div className="empty-icon">❤️</div>
              <div className="empty-title">Nessun preferito</div>
              <div className="empty-text">Salva i mercati che ti interessano per ritrovarli qui.</div>
            </div>
          )}
        </div>
      </>
    );
  };

  const renderNotifications = () => {
    const savedMarkets = marketsWithDistance.filter(market => favorites.has(market.id));
    const scheduled = savedMarkets
      .map(market => ({ market, next: getNextDate(market.dates) }))
      .filter(item => item.next)
      .sort((left, right) => left.next.localeCompare(right.next))
      .slice(0, 30);
    const missingDates = savedMarkets.filter(market => !getNextDate(market.dates));

    return (
      <>
        <div className="header">
          <div className="header-title">Agenda preferiti</div>
        </div>
        <div className="page-content">
          <div className="setting-card">
            <div className="setting-label">I prossimi mercati che hai salvato</div>
            <div className="setting-sublabel">
              Qui trovi le date disponibili. Le notifiche push automatiche non sono ancora attive.
              Controlla sempre se la data è confermata prima di partire.
            </div>
          </div>
          {savedMarkets.length === 0 ? (
            <div className="empty-state">
              <div className="empty-icon">♡</div>
              <div className="empty-title">Nessun mercato salvato</div>
              <div className="empty-text">Salva un mercato dalla ricerca per vederlo qui.</div>
              <button className="btn-primary" style={{ padding: '10px 20px', marginTop: 12 }}
                onClick={() => setTab('esplora')}>Cerca mercati</button>
            </div>
          ) : (
            <>
              {scheduled.length > 0 ? (
                <div className="markets-list" style={{ padding: 0 }}>
                  {scheduled.map(({ market, next }, index) => (
                    <button key={market.id} className="setting-card" style={{
                      display: 'flex', width: '100%', textAlign: 'left', gap: 12,
                      alignItems: 'center', cursor: 'pointer', border: 'none',
                    }} onClick={() => openMarket(market)}>
                      <span style={{ minWidth: 85, fontWeight: 700 }}>{formatDateIT(next)}</span>
                      <span style={{ flex: 1 }}>
                        <strong>{market.name}</strong>
                        <span style={{ display: 'block', fontSize: 12, opacity: 0.75 }}>
                          {market.city} · {market.dateQuality === 'confermata' ? 'Confermata' : 'Prevista, da verificare'}
                        </span>
                      </span>
                    </button>
                  ))}
                </div>
              ) : (
                <div className="setting-card">Nessuna data futura disponibile per i tuoi preferiti.</div>
              )}
              {missingDates.length > 0 && (
                <div className="setting-card" style={{ marginTop: 12 }}>
                  <div className="setting-label">{missingDates.length} preferiti senza prossima data</div>
                  <div className="setting-sublabel">Li trovi nella sezione Preferiti. Verifica la fonte ufficiale.</div>
                </div>
              )}
            </>
          )}
        </div>
      </>
    );
  };

  const renderSettings = () => (
    <>
      <div className="header">
        <div className="header-title">Impostazioni</div>
      </div>
      <div className="page-content">
        <div className="setting-card">
          <div className="setting-label" style={{ marginBottom: 4 }}>Posizione</div>
          <div className="setting-sublabel">Scegli come trovare i mercati vicino a te</div>
          <div className="location-options">
            <button
              className={`location-option ${locationMode === 'auto' ? 'active' : ''}`}
              onClick={activateNearby}
            >
              <div className="icon-circle"><Icon name="compass" size={18} /></div>
              <div>
                <div style={{ fontWeight: 600 }}>Usa la mia posizione</div>
                <div style={{ fontSize: 12, color: '#8C8272', marginTop: 1 }}>
                  {positionStatus === 'ready' ? 'Posizione attiva' :
                   positionStatus === 'requesting' ? 'Richiesta in corso…' : 'Richiede il tuo consenso'}
                </div>
              </div>
            </button>
            <button
              className={`location-option ${locationMode === 'manual' ? 'active' : ''}`}
              onClick={() => setLocationMode('manual')}
            >
              <div className="icon-circle"><Icon name="mapPin" size={18} /></div>
              <div>
                <div style={{ fontWeight: 600 }}>Scegli una città</div>
                <div style={{ fontSize: 12, color: '#8C8272', marginTop: 1 }}>Inserisci manualmente</div>
              </div>
            </button>
            <button
              className={`location-option ${locationMode === 'none' ? 'active' : ''}`}
              onClick={disableLocation}
            >
              <div className="icon-circle"><Icon name="x" size={18} /></div>
              <div>
                <div style={{ fontWeight: 600 }}>Non ora</div>
                <div style={{ fontSize: 12, color: '#8C8272', marginTop: 1 }}>Naviga senza posizione</div>
              </div>
            </button>
          </div>

          {positionError && <div role="alert" className="setting-sublabel" style={{ marginTop: 12 }}>{positionError}</div>}
          {canUseDistance && (
            <div className="setting-sublabel" style={{ marginTop: 10 }}>
              Distanze calcolate rispetto alla tua posizione. Alcuni mercati hanno solo coordinate indicative.
            </div>
          )}
          {locationMode === 'manual' && (
            <>
              <div className="manual-city-input">
                <input list="available-market-cities" placeholder="Es. Firenze" value={manualCity}
                  onChange={e => setManualCity(e.target.value)}
                  onKeyDown={e => { if (e.key === 'Enter') confirmManualCity(); }} />
                <datalist id="available-market-cities">
                  {CTS.map(city => <option key={city} value={city} />)}
                </datalist>
                <button onClick={confirmManualCity}>Filtra città</button>
              </div>
              <div className="setting-sublabel">
                La città selezionata filtra i risultati. Non equivale alla posizione GPS.
              </div>
            </>
          )}
        </div>

        <div className="app-version">
          <div style={{ fontFamily: 'var(--font-display)', fontSize: 16, marginBottom: 4 }}>
            <span style={{ color: 'var(--terracotta)' }}>Mercati</span> d'Italia
          </div>
          Versione 1.1 · Catalogo statico (lettura gratuita)
        </div>
      </div>
    </>
  );

  return (
    <>
      <style>{styles}</style>
      <div className="app-container" onClick={() => showSort && setShowSort(false)}>
        {tab === "esplora" && renderExplore()}
        {tab === "mappa" && renderExplore()}
        {tab === "preferiti" && renderFavorites()}
        {tab === "notifiche" && renderNotifications()}
        {tab === "impostazioni" && renderSettings()}

        {showFilters && renderFilterPanel()}
        {selectedMarket && renderDetail()}
        {toast && <div className="toast">{toast}</div>}

        <nav className="bottom-tabs">
          {[
            { id: "esplora", label: "Esplora", icon: "compass" },
            { id: "preferiti", label: "Preferiti", icon: "heart" },
            { id: "notifiche", label: "Agenda", icon: "calendar" },
            { id: "impostazioni", label: "Impostazioni", icon: "settings" },
          ].map(t => (
            <button key={t.id} className={`tab-btn ${tab === t.id ? 'active' : ''}`}
              onClick={() => { setTab(t.id); if (t.id === 'esplora') setViewMode('lista'); }}>
              <Icon name={t.icon} size={22} strokeWidth={tab === t.id ? 2 : 1.6} />
              {t.label}
            </button>
          ))}
        </nav>
      </div>
    </>
  );
}
