# Vintagery — reading it every day

Vintagery (vintagery.it) is the owner's own market directory. Its site answers scripts with
a Vercel Security Checkpoint (HTTP 429), so the nightly runner cannot read it and must never
try to get past that. Vintagery is read in the owner's Chrome, through Claude in Chrome.

## Daily, unattended (once installed)

Windows task `MercatiItalia-Vintagery`, every day at 03:30 (before the 04:30 nightly), only
while the owner is logged in. It runs `refresh-daily.ps1`:

1. resets its own DEV checkout (`%LOCALAPPDATA%\mercati-italia\vintagery\repo`);
2. writes today's plan, 120 cards: those the previous day's sitemap listing named that we
   don't hold yet, then passed next dates, then the oldest reads, so every card is re-read
   about weekly (the sitemap itself is read every day, for new and removed cards);
3. `claude -p --chrome` (prompt on stdin, the plan + `collect.js` inside it) opens
   vintagery.it in a new tab, runs the script, waits;
4. the downloaded `vintagery_cards_<day>.json` is merged into
   `backend/data/vintagery-snapshot.json` and moved to `...\vintagery\archive\`;
5. if the snapshot changed: waits for the nightly runner to be idle, commits only the
   snapshot to DEV and pushes via SSH.

Chrome or the extension not connected, Vercel blocking, no download: the log
(`%LOCALAPPDATA%\mercati-italia\vintagery\logs\<day>.log`) says why and the task exits 1. The
nightly keeps using the older snapshot; a card stops counting 45 days after its last read.

Install (the owner, once, from any up-to-date checkout of DEV):

    powershell -NoProfile -ExecutionPolicy Bypass -File ops\vintagery\install-task.ps1

A test run that reads and merges a few cards but commits nothing:

    powershell -NoProfile -ExecutionPolicy Bypass -File ops\vintagery\refresh-daily.ps1 -PerDay 3 -DryRun

Why not the sitemap's `<lastmod>`: it is the time the sitemap was built (the same value for
all 840 cards, checked 27 Oct 2026), so it cannot tell which card changed. A card is renewed
only by reading it again.

## By hand (a full read)

1. Open https://vintagery.it/ in Chrome; clear old progress: `localStorage.removeItem('vg_cards_v1')`.
2. Run `ops/vintagery/collect.js` in that tab (no `window.__vgPlan` = full read, ~50 minutes).
3. `python backend/vintagery_source.py <Downloads>\vintagery_cards.json` rebuilds the snapshot.

## What the nightly does with the snapshot

- new markets enter through editorial discovery: every current card is checked each night,
  at most 32 are added (same rules as the other editorial publishers). A card with no date
  enters when its page shows its own status ("Torna a luglio", "Date annunciate di volta in
  volta"); no date is ever invented;
- Vintagery's own cards are re-read from the newer snapshot;
- markets other sources already have get empty street/hours filled, a matching rule restated
  (each with a receipt), and Vintagery's entry price, tips and tags (`vintagery_source.apply`).
