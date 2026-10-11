# Mercati d'Italia — stato e checkpoint verificabili

**Data:** 11 ottobre 2026 · **Branch:** `improve/data-quality-security-performance-2026-10-11` · **PR in bozza:** https://github.com/tommyv-spec/mercati-italia/pull/1

## Obiettivo

Più mercati italiani, dati affidabili, ricerca veloce su telefono, nessun costo Cloudflare **per le normali letture del catalogo**. Le visite leggono file statici su Pages. Nessuna visita invoca Firebase, Pages Functions, KV o D1. Il costo reale dell'account Cloudflare e le sue eventuali altre Workers route **non sono ancora stati verificati**.

## Checkpoint completati

- [x] **CP0 — Audit iniziale.** Firestore pubblico scrivibile, auto-seed dal browser, date hardcoded febbraio 2026, dati demo duplicati, frontend limitato a 300 risultati, classificazione/dedup/geocoding fragili.
- [x] **CP1 — Hardening del codice.** `firestore.rules` impedisce scritture pubbliche. Rimossi Firebase SDK, vecchio browser auto-seed, codice demo e Firestore query dal frontend. **Attenzione: le regole non sono state ancora applicate all'istanza Firebase live.**
- [x] **CP2 — Catalogo nazionale statico.** Import read-only dell'istanza Firestore esistente a pagine con aggregazione preventiva; 13.501 documenti nelle categorie interrogate, aggiunti 85 record di Milano, poi normalizzati/esclusi i non idonei. Manifest, file regionali versionati con hash e validator. Fonte storica Firestore conservata, nessuna scrittura.
- [x] **CP3 — Quantità e sorgenti ufficiali.** Importatore Milano DS291 (85 mercati con coordinate 4326, date ricorrenti previste, fonte maggio 2024); Firenze FeelFlorence (4 mercati con coordinate ufficiali, fonte marzo 2023). Connettori eseguibili periodicamente, attribuzione presente, senza fingere verifica attuale.
- [x] **CP4 — Integrità, sicurezza, qualità.** VentI regioni canoniche, record fuori Italia esclusi; blocco categorie esterne (sagra/carnevale) e titoli generici ambigui; dedup/merge conservativo che preserva fonti e non elimina assenti; coordinate indicative distinte dalle precise; qualità date (confermata, prevista, sconosciuta); punteggio `completezza` separato da verifiche umane. Esportazioni vuote e cali anomali bloccati.
- [x] **CP5 — Prestazioni/CDN.** Un solo indice statico nazionale per lista/ricerca/filtri/mappa, descrizioni e schede complete lette *solo alla selezione* dalla regione immutabile. Render iniziale massimo 60 carte, poi Mostra altri. Firebase rimossa anche dalle dipendenze NPM. `public/_routes.json` evita l'invocazione Pages Functions sui file pubblici; `public/_headers` abilita cache lunga sugli asset hash e refresh del manifest.
- [x] **CP6 — CI e rollback.** GitHub Actions testa Python, firma e integrità completa dello snapshot, build Vite, routing Cloudflare. Snapshot precedenti preservati durante gli aggiornamenti. Workflow one-off eseguiti e rimossi; `.github/workflows/refresh-data.yml` e `.github/workflows/quality.yml` sono quelli permanenti. PR lasciata *draft* finché non viene provato il deploy.

## Snapshot attuale — ultimo export sul branch

- **13.099 record candidati** con categorie incluse e 20 regioni italiane.
- **8.202** con almeno una data futura registrata/proiettata. Date automaticamente ricorrenti = *previste*, non edizioni confermate.
- **13.099** con coordinate, ma molte coordinate dal vecchio archivio indicano solo centri comunali o posizioni non verificate. Non equivalgono a ingressi precisi.
- **0** con una verifica umana documentata; UI lo segnala correttamente.
- Indice globale: **4.369.258 byte** prima della compressione HTTP, contro 7.312.633 della prima versione.
- Catalogo: `public/data/v1/manifest.json`; `index_schema=2`; 20 shard regionali.
- La vecchia collezione conteneva moltissimi eventi generici; il numero di record **non** misura la qualità e può contenere ancora duplicati/eventi da rivedere.

**Import riuscito:** GitHub Actions run `38165365302` (prima migrazione completa), run `38165680504` (20 regioni), run `38166243508` (coordinate Milano + fonte Firenze), run `38166397677` (indice compatto); test CI e build verificati nei workflow `quality.yml`.

## Cosa manca prima di mettere online

- [ ] **R1 — Sicurezza effettiva:** deploy delle `firestore.rules` sul vero progetto Firebase con credenziali amministrative e test negativo di scrittura anonima. Le regole nel repository, da sole, **non proteggono il DB di produzione**.
- [ ] **R2 — Costi effettivi:** audit Cloudflare dashboard (Pages/Workers/Functions, route del dominio, analytics/usage/billing) e conferma che le richieste sul dominio reale non invocano Workers. Cloudflare documenta static asset requests gratuite e illimitate; non garantisce costo zero di altri servizi.
- [ ] **R3 — Test browser reale:** verifica sito mobile, schede lazy, ricerche, mappa e URL delle fonti con Network tab su preview Pages. Nessun URL di deploy Cloudflare è disponibile in questa sessione.
- [ ] **R4 — Qualità editoriale:** analisi a campione delle categorie `misto`, conflitti tra fonti, date/festivi, coordinate comunali stimate, possibili mercati distinti con nomi simili; ampliare fonti comunali ufficiali dove possibile.
- [ ] **R5 — Pubblicazione:** dopo le verifiche precedenti, approvare e unire PR. Configurare su Cloudflare Pages Vite `npm run build`, output `dist`, e verificare il dominio effettivo.
- [ ] **R6 — Monitoraggio:** misurare dimensione compressa/tempo avvio su mobile; osservare crescita dell'indice e aggiornamenti falliti; aggiungere più regioni da open data aggiornati.

## Comandi riproducibili e link

```bash
python -m unittest discover -s backend/tests -v
python backend/validate_static.py --manifest public/data/v1/manifest.json
npm ci
npm run build
```

- README aggiornato: `README.md`.
- PR: https://github.com/tommyv-spec/mercati-italia/pull/1
- Tariffe ufficiali: https://developers.cloudflare.com/pages/functions/pricing/
- Routing statico: https://developers.cloudflare.com/pages/functions/routing/
- Non usare il geocoder pubblico Nominatim per elaborazioni geografiche massive. Non spacciare dati previsti o fonte del 2023/2024 come verificati nel 2026.

**Principio di sicurezza:** nessuna migrazione operativa o sostituzione pubblica deve distruggere l'archivio precedente. L'importazione Firestore già eseguita è stata di sola lettura; la nuova pubblicazione è separata.
