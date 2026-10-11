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

- **12.650 record candidati** con categorie incluse e 20 regioni italiane.
- **7.763** con almeno una data futura registrata/proiettata. Date automaticamente ricorrenti = *previste*, non edizioni confermate.
- **12.650** con coordinate, ma molte coordinate dal vecchio archivio indicano solo centri comunali o posizioni non verificate. Non equivalgono a ingressi precisi.
- **0** con una verifica umana documentata; UI lo segnala correttamente.
- Indice globale: **4.369.258 byte** prima della compressione HTTP, contro 7.312.633 della prima versione.
- Catalogo: `public/data/v1/manifest.json`; `index_schema=3`; 20 shard regionali.
- La vecchia collezione conteneva moltissimi eventi generici; il numero di record **non** misura la qualità e può contenere ancora duplicati/eventi da rivedere.

**Import riuscito:** GitHub Actions run `38165365302` (prima migrazione completa), run `38165680504` (20 regioni), run `38166243508` (coordinate Milano + fonte Firenze), run `38166397677` (indice compatto); test CI e build verificati nei workflow `quality.yml`.

## CP7 — Audit reale UX e deduplicazione sicura

- [x] Browser mobile Chromium 390×844: ricerca, scheda, filtro città, GPS con consenso, Agenda e controllo di **zero chiamate Firestore/Workers** nel flusso testato. Screenshot e report in artefatti GitHub Actions; un primo test ha superato tutte le verifiche.
- [x] Ripuliti controlli che simulavano funzioni inesistenti: notifiche sostituite da Agenda, indicazioni e condivisione realmente collegate, nessuna posizione fittizia Firenze.
- [x] Distanze calcolate solo con GPS autorizzato; raggio vicino a me limitato ai punti precisi, con scelta esplicita per vedere anche posizioni indicative. Dati incerti spiegati nella scheda.
- [x] Audit doppioni: prima proposta di 3.903 fusioni **bloccata** perché includeva mercati in vie/giorni diversi. Dopo controllo: **446 unioni sicure**, da 13.096 a 12.650; snapshot rigenerato con `index_schema=3` e tutte le 20 regioni.
- [x] Test Python e build/validazione snapshot superati nel workflow `quality.yml` run `38168363210`.
- [x] Retest automatico Chromium mobile dopo snapshot 12.650 e UX fixes: run `38168580936` PASS, 60 card, zero JavaScript page errors, zero richieste Firebase/Workers nel percorso simulato. Screenshot casa, scheda e GPS nell'artefatto `mercati-ux-mobile`.
- [ ] Review su telefoni fisici Android/iOS, contrasto/accessibilità e UX con utenti reali; il test emulato non basta.
- [ ] Mappa stradale reale, verifiche umane delle date/sedi/orari, e controllo Cloudflare/Firebase dal dashboard restano aperti.

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

## CP8 — Fix della preview DEV segnalata dall'utente (11 ottobre 2026)

- [x] Audit browser iPhone13 (Playwright su Chrome reale): inizialmente la preview caricava oltre 7.500 risultati stimati senza spiegare la zona; la vecchia mappa era solo SVG, alcuni pin occlusi dal menu; richiesta GPS negata cancellava il filtro città; un refactoring aveva causato un errore fatale `useRef is not defined`.
- [x] Corretti il crash `useRef`, i filtri città e reset, GPS con consenso e fallback senza perdita di filtri, indicazione visibile che le date previste non sono confermate, banner «tutta Italia», classifica dei risultati, weekend di domenica.
- [x] Sostituita mappa SVG con MapLibre GL JS lazy, clustering, popup, navigazione, posizione precisa vs indicativa, zoom automatico sui mercati filtrati; font cluster Noto Sans supportato da OpenFreeMap (correzione 404 glyph).
- [x] Migliorato indice nazionale con `index_schema=4`: array compatti, 12.650 record preservati, dettagli regionali caricati solo quando si apre una scheda. I JSON rimangono file statici, senza Firebase/Workers durante le visite.
- [x] Build di staging GitHub Actions run `38171786850`, commit `f6f934a39fb4b36a8d16a3de898fed38de36b620`; esito SUCCESS. Prima dell'update, test di 11 flussi su `site-ready` (port4176) fallimenti 0, errori JavaScript 0. Preview nuova `site-v2` (port4177) verificata: mappa caricata, zero HTTP 404 font, nessun page error.
- [x] DEV temporaneo aggiornato su `https://share-thats-battery-fax.trycloudflare.com/` senza cambiare URL del Quick Tunnel. Tunnel cloudflared PID17432 invariato, ora servizio statico Python con gzip/ETag e cache sul port4173 (PID16608), verificato HTTP200 dall'esterno; server vecchio e i suoi file rimangono disponibili per rollback.
- [x] Verifica browser iPhone13 emulato direttamente sul **link pubblico HTTPS** terminata: **11/11 scenari PASS; 0 page errors, 0 console errors, 0 risposte HTTP 4xx/5xx, 0 request failed**. Primo caricamento test esterno circa 4,33 s; 60 schede reali visibili; ricerca, filtri, date, dettaglio lazy, preferiti, Agenda, mappa, geolocalizzazione negata/accettata, opzione posizioni indicative e condivisione esercitati.
- [ ] Resta la verifica pratica su iPhone/Android fisici; il test Playwright emulato non prova tutti i browser o GPS reali.
- [ ] Non equiparare la funzionalità software a date e indirizzi verificati: 0 verifiche umane documentate, posizioni indicative e data quality rimangono criticità per il rilascio pubblico.

