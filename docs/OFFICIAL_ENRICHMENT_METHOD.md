# Official-source evidence enrichment: manual proof → script → daily DEV

## Why enrichment exists

The first Lombardia official import added 1,127 fresh source identities but kept
233 duplicate-like venue/day records in quarantine. Until this change, the
official hours of those 233 could not improve the already-published legacy
cards without adding duplicate markets.

Manual observation: 12 October 2026. Reading original official MERCap
dataset rows directly, alongside existing regional DEV catalog records.

Evidence:
- https://www.dati.lombardia.it/d/68zx-njaw
- Official market ID 100001, Albizzate, Piazzale Sefro, Tuesday 08:00–13:00.
- Official market ID 100004, Arsago Seprio, Via Monici, Wednesday 08:00–13:00.
- Official market ID 100551, Pogliano Milanese, Via Europa, Friday 08:00–12:00.
- Original third-party cards had the SAME city/address/weekday but NO hours.
- The original publisher dataset updated 6 October 2026, **not** an individual
  market confirmation. Different point coordinates had differences under
  600 metres in manually observed cases; do not claim a precise entrance.

## Deterministic safe-transfer policy

Reusable module: \`backend/official_enrichment.py\`, function
\`enrich(base, held_official, source_id, today)\`.

Strict rules:
1. Source prefix, region and official URL must be on a reviewed allowlist.
2. Municipality, street text and ONE explicit weekday must match exactly after
   safe punctuation/case normalization. Never join merely by city name.
3. Both available points must be no more than 600m apart. Invalid coordinates
   cannot be treated as precise.
4. Exactly one official source row per venue/day. Multiple source identities
   at the same venue/day are left for human review.
5. Only unfilled \`orario_testo\` is enriched, with a mandatory
   \`(fonte comunale, da verificare)\` warning.
6. Attach source evidence to \`fonti\` without replacing \`fonte\` or
   \`url_fonte\`. The browser displays it on market details; the compressed
   nationwide index remains unchanged.
7. Never change \`slug\`, confirmed dates, \`verificato_il\`, event status,
   source refresh dates, coordinate values or source primary attribution.
8. Refuse source observations outside the 540-day permitted age and
   stop if more than 500 previously published market cards would be changed.

## Verified real full-market rehearsal

Isolated GitHub Actions:
https://github.com/tommyv-spec/mercati-italia/actions/runs/38189953775

- Original catalog: **13,779** identities.
- Post-enrichment candidate: **13,779** identities (no duplicates).
- Official overlap records evaluated: **233**.
- Exact match: **132** legacy market cards.
- Missing hours filled: **129**.
- New official attribution links: **132**.
- Previously missing hours: **10,969** → **10,840**.
- Confirmed dates invented: **0**.
- Verification claims invented: **0**.
- Primary sources replaced: **0**.
- Coordinate overwrites: **0**.
- National gzip index increased by only 289 bytes
  (404,096 → 404,385), because full source evidence is lazy-loaded.
- Full security, JS unit tests and mobile browser smoke passed.

The first import is controlled with \`backend/autopilot_policy.json\`:

~~~json
"enrichment": {"enabled": true, "source": "lombardia-mercap"}
~~~

Main job \`.github/workflows/market-autopilot.yml\` performs source collection,
exact matching, QA gates, browser check, DEV publication, trend history and
notifications. The SHA of the source and checks are versioned; failed runs
retain only checkpoint artifacts (which expire after 30 days).

## Replay & future source adapters

~~~bash
python -m unittest discover -s backend/tests -v
python backend/autopilot.py --offline --output autopilot-output
~~~

For a full real-source dry-run before adding a new trusted publisher,
copy the isolated workflow design from
\`.github/workflows/official-enrichment-audit.yml\` (review the source allowlist,
license, row identity and specific negative fixtures first).

At each scheduled run the previous enriched records are inputs; second and
subsequent runs **must produce zero new additions** unless fresh and genuinely
new evidence exists. Logs report \`existing_market_hours_added\` and
\`official_source_attributions_added\` separately from the number of records.
An unchanged source must not create duplicate links.

Important: this is **data completeness**, NOT human verification of openings.
Old market claims can still be wrong, so the app must display caveats.
