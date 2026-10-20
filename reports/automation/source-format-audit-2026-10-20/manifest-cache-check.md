# Manifest cache visibility

The public stable preview returned the 18:16 catalog at 19:31 UTC on
2026-10-20, including when requested with no-cache. The exact published
commit and the stable URL with `?refresh=995847` returned the 19:27 catalog.
The recorded response hashes and metadata are in `manifest-cache-recheck.json`.
No additional HTTP request was made while implementing this fix.

Only `data/v1/manifest.json` now receives a deterministic cache key:
`floor(current UTC epoch milliseconds / 1800000)`. Initial loads and later
checks use the same rule. The validated local path is constructed before
adding the numeric parameter. Content-hashed indexes, region files and other
assets retain their original immutable URLs.

- [x] Regression models an old stable CDN response despite no-cache and a
  fresh response at the shared bucket URL.
- [x] Revalidation remains limited to one attempt per 30 minutes; concurrent
  focus/visibility checks share a pending promise.
- [x] An unchanged manifest avoids downloading the index or regions again.
- [x] A failed index read preserves the working catalog and its regional
  detail cache. Repeated focus events do not retry before the next interval.
- [x] A backward clock adjustment cannot request an earlier bucket or roll
  the active catalog back. Checks resume when the prior interval is reached.
- [x] An external index URL in a manifest is rejected before any request.
- [x] All 11 Node test files and the production Vite build pass.

The change does not alter cache headers, schedules, market records or backend
services. It does not promise immediate visibility within an already cached
30-minute bucket; the next permitted check advances to a later bucket.
