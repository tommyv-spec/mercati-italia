# Vintagery snapshot — how to refresh (about once a month)

Vintagery (vintagery.it) is the owner's own market directory. Its site answers scripts
with a Vercel Security Checkpoint (HTTP 429), so the nightly runner cannot read it and
must never try to get past that. This is the ONE step of the pipeline that needs a browser:
the owner's Chrome, driven by Claude in Chrome on the owner's PC.

1. Open https://vintagery.it/ in Chrome. Clear the old progress first if this is a new
   monthly read: `localStorage.removeItem('vg_cards_v1')` in that tab.
2. Run `ops/vintagery/collect.js` in that tab (Claude in Chrome `javascript_tool`, or paste
   it in the DevTools console). It reads one page every 3.5 s (about 50 minutes for ~840
   cards), keeps its progress in the tab, and stops by itself after three blocked replies.
   Running it again resumes. Progress: `window.__vgState`.
3. When it finishes, Chrome downloads `vintagery_cards.json`.
4. From the repo root: `python backend/vintagery_source.py <path>/vintagery_cards.json`
   writes `backend/data/vintagery-snapshot.json` (structured fields, no HTML). Commit it.

The nightly then uses the snapshot by itself:
- new markets enter through editorial discovery (at most 32 a night, same rules as the
  other editorial publishers);
- Vintagery's own cards are re-read from the newer snapshot;
- markets other sources already have get empty street/hours filled and a matching rule
  restated, each with a receipt naming the Vintagery page (`vintagery_source.fill`).

Each card counts as read on the day the browser read it. After 45 days without a new
snapshot, cards stop being applied and their dates age out under the normal rules.
