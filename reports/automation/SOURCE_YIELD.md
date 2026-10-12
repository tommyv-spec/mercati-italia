# Fonti ufficiali — resa osservata e prossime verifiche

**Audit in sola lettura. Nessun ID, mercato o calendario modificato.**

- Fonti catalogate: **43**
- Schede conservate: **13779**
- Fonti con righe ricontrollate ora: **1**
- Bologna: **48** schede ufficiali osservate.
- Nuovi ID Bologna (non mercati certificati nuovi): **48**.
- Possibili sedi distinte, ancora da verificare: **47**.
- Possibili sovrapposizioni tra fonti: **1**.
- Source data Bologna: **2025-04-02**; non e' una conferma di apertura.

## Priorita basate sulla resa, non sul punteggio dei metadati

| Priorita | Fonte | Stato | Righe viste | Candidati distinti | Azione |
|---:|---|---|---:|---:|---|
| 1 | Mercati e fiere | observed_candidate_venues | 48 | 47 | Check 2026 municipality schedule and exact venue identities before allowing import. |
| 2 | Dati sui Mercati Rionali | historical_hours_lead | n.d. | n.d. | Find a current Roma municipal record to corroborate 2022 addresses and opening hours. |
| 3 | Anagrafica mercati | unreachable_candidate_source | n.d. | n.d. | Restore official dataset endpoint or find replacement, then inspect actual municipality rows. |
| 4 | Censimento dei mercati giornalieri | schema_and_rights_review | n.d. | n.d. | Check live row schema, source date, attribution and calendar before integration. |
| 5 | Censimento dei mercati itineranti | schema_and_rights_review | n.d. | n.d. | Check live row schema, source date, attribution and calendar before integration. |
| 6 | Posteggi mercati e fiere - Comune di Brendola | events_and_stalls_mixed | n.d. | n.d. | Separate periodic markets from fairs and vendors; do not auto-import. |
| 7 | Posteggi mercati e fiere - Comune di Fontaniva | events_and_stalls_mixed | n.d. | n.d. | Separate periodic markets from fairs and vendors; do not auto-import. |
| 8 | Posteggi mercati e fiere - Comune di Lazise | events_and_stalls_mixed | n.d. | n.d. | Separate periodic markets from fairs and vendors; do not auto-import. |
| 9 | Posteggi mercati e fiere - Comune di Meolo | events_and_stalls_mixed | n.d. | n.d. | Separate periodic markets from fairs and vendors; do not auto-import. |
| 10 | Posteggi mercati e fiere - Comune di Pianiga | events_and_stalls_mixed | n.d. | n.d. | Separate periodic markets from fairs and vendors; do not auto-import. |
| 11 | Posteggi mercati e fiere - Comune di Sandrigo | events_and_stalls_mixed | n.d. | n.d. | Separate periodic markets from fairs and vendors; do not auto-import. |
| 12 | Posteggi mercati e fiere - Comune di Soave | events_and_stalls_mixed | n.d. | n.d. | Separate periodic markets from fairs and vendors; do not auto-import. |

Fonti gia integrate, concessioni e statistiche non contano come nuovi mercati.
Le fonti con righe non accessibili restano non misurate, non diventano zero.
