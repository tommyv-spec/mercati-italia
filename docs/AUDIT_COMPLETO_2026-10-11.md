# AUDIT COMPLETO — Mercati d'Italia
**Data:** 11 ottobre 2026 · **Ambiente:** branch `improve/data-quality-security-performance-2026-10-11` · **PR:** [#1](https://github.com/tommyv-spec/mercati-italia/pull/1)

**Verdetto: NO-GO per la produzione.** Il codice DEV è funzionante in un percorso di test, ma la maggior parte dei mercati è priva di dati verificati, la rigenerazione delle date non è assicurata e la sicurezza delle regole Firebase distribuite non è stata verificata.

Questo report separa rigorosamente **fatti misurati**, **rischi inferiti dal codice** e **verifiche ancora impossibili senza accesso agli account**. Non è un pentest indipendente, una verifica legale delle licenze o uno studio su iPhone/Android fisici.

## 1. Scorecard

| Area | Stato | Motivazione |
|---|---|---|
| Architettura costi per visita | **Promettente, non certificata** | Catalogo JSON statico con indice compatto e shard regionali; nessun DB/Worker usato nel flusso testato. Cloudflare Pages static asset non fattura le richieste; account/route Cloudflare reale non esaminato. |
| Prestazioni mobile | **Migliorabile** | Prima card in 5,58 secondi a 1,6 Mbps, RTT artificiale 150ms e CPU 4× rallentata. First Contentful Paint 0,88s. Test sintetico, non misura utenti reali. |
| Qualità e copertura dei dati | **Bloccante** | 0 verifiche documentate, 84% senza orari, 47,1% indirizzo assente/vago, 99,3% punti non dichiarati precisi. |
| Date e operatività | **Bloccante** | Entro 60 giorni rimangono solo 13 record con date future. Workflow schedulato presente soltanto nel branch non predefinito; mancano refresh per la gran parte delle fonti. |
| Sicurezza | **Richiede rilascio separato e verifica** | Versione MapLibre precedentemente vulnerabile a CVE-2026-85061; aggiornata sul branch a 6.14.0 con audit npm a 0 advisories. Regole Firestore in `main` ancora con `allow write: if true`; regole effettivamente deployate sconosciute. |
| Accessibilità | **In correzione / da validare** | Prima scansione Axe WCAG: zoom disattivato, contrasto basso e controlli annidati. Sono state applicate correzioni sul branch; non dichiararle chiuse finché la scansione post-fix non è conclusa. |
| Esperienza utente | **Parziale** | Ricerca, mappa, filtro, preferiti e card raggruppate funzionano nei test, ma frequenti dati mancanti e luoghi stimati rendono debole la fiducia. |
| SEO/discovery | **Da progettare** | SPA con title e meta description generici; schede in hash URL, senza pagine pubbliche per mercato e markup schema.org. |
| Licenze/provenienza | **Da verificare** | 93,6% del catalogo proviene da due siti non ufficiali; licenze e diritti di riuso vanno documentati. |

## 2. Audit dati: tutti i 12.650 record (non campione)

**Fonte riproducibile:** `python backend/audit_dataset.py`, artefatto `market-audit-dataset` del workflow [38175662762](https://github.com/tommyv-spec/mercati-italia/actions/runs/38175662762).

| Metrica | Risultato |
|---|---:|
| Record | **12.650** |
| Regioni | 20 |
| Record con una futura data disponibile | **7.763 (61,4%)** |
| Nessuna futura data | **4.887 (38,6%)** |
| Nessun orario | **10.627 (84,0%)** |
| Nessun indirizzo (vuoto) | **3.503 (27,7%)** |
| Indirizzo assente o vago (es. «centro») | **5.963 (47,1%)** |
| Nessuna descrizione | **6.744 (53,3%)** |
| Coordinate etichettate «precise» nel dataset | **89 (0,7%)** |
| Coordinate non verificate | **12.561 (99,3%)** |
| Con verifica umana documentata | **0** |
| Categoria generica «misto» | **9.884 (78,1%)** |
| Fonte Happings | **9.647 (76,3%)** |
| Fonte Eventi e Sagre | **2.197 (17,4%)** |
| Città con più grafie maiuscole/minuscole | **200** |

**Concentrazione:** Happings + Eventi e Sagre rappresentano 11.844/12.650 (93,6%) delle schede. Una fonte presente non è una prova che l'edizione sia aggiornata o confermata.

**Precisione geografica:** Roma ha 110 record con la medesima coordinata arrotondata `(41.90, 12.50)`; Firenze 44 record su `(43.77, 11.25)`; Milano 35 su `(45.46, 9.19)`. Molte mappe indicano quindi il centro città, non la sede del mercato. Anche le 89 coordinate definite «precise» non implicano una verifica recente della sede.

**Pulizia:** città come `Bagno a Ripoli`/`Bagno A Ripoli` producono doppioni nei filtri; sigle come `AR`, `IM`, `NA` compaiono nel campo città. La corrispondenza esatta usata da alcuni filtri UI amplifica il problema.

### La criticità temporale

| Orizzonte, da 11/10/2026 | Record con almeno una data futura nel catalogo salvato |
|---|---:|
| Oggi | 7.763 |
| +7 giorni | 7.761 |
| +30 giorni | 7.553 |
| **+60 giorni** | **13** |
| +90 giorni | 1 |
| +180 giorni | 1 |
| +240 giorni | 0 |

La lista nazionale quasi scomparirebbe dai filtri temporali dopo due mesi **anche se i mercati continuassero realmente a svolgersi**. È il problema P0 più urgente del prodotto.

Il catalogo mantiene date pre-generate, ma il processo schedulato non rigenera una ricorrenza per ogni fonte: `backend/source_milano.py` rigenera solo Milano, `backend/source_firenze.py` importa quattro sedi storiche senza date; il merge mantiene i precedenti record quasi invariati. Il `small_index()` contiene solo le prime otto date. Il workflow `refresh-data.yml` è presente nel branch DEV ma non in `main`, dove GitHub esegue gli eventi `schedule`.

## 3. Prestazioni, trasporto e hosting

**Benchmark**: Playwright Chromium mobile 390×844, 1,6 Mbps downstream, 150ms di latenza artificiale, CPU ×4; ambiente Vite statico, non reale rete italiana. [Workflow](https://github.com/tommyv-spec/mercati-italia/actions/runs/38175662762).

| Voce | Baseline misurata |
|---|---:|
| Prima card visibile | **5,578 ms** |
| First Contentful Paint | 880 ms |
| Indice nazionale non compresso | 3.163.378 byte |
| Indice nazionale gzip | **340.949 byte (~333 KiB)** |
| 20 shard regionali (totale non compresso) | 11.183.804 byte |
| 20 shard regionali (gzip sommato) | ~1.014.000 byte |
| Bundle mappa caricato su richiesta, trasferimento misurato | ~288.000 byte |
| JS heap nel punto misurato | ~12,7 MB (dato Chrome, non memoria totale processo) |

Punti a favore: niente Worker/DB in visita, contenuti immutabili con hash, paginazione visuale, dettagli di una singola regione caricati su richiesta, mappa lazy e cluster.

Punti da migliorare: non caricare/normalizzare ~12.650 record come prerequisito per le prime card; valutare ricerca per area con indice ridotto e cache, Web Vitals sul dispositivo reale, test 3G/4G e bundle budgets CI. Evitare di conteggiare come gratis un'eventuale Cloudflare Function invocata da route/dashboard esterne.

**Cloudflare:** la documentazione ufficiale (settembre 2026) dichiara illimitate e gratuite le richieste ai file statici di Pages su Free e Paid; le Pages Functions e i Workers sono invece soggetti a quote/fatturazione. Limiti Free Pages: 20.000 file/deploy, 25 MiB per asset, 500 build mensili. Il sito attuale non ha ancora un audit dell'account Cloudflare reale. Costi di altre risorse, dominio, piani o route non vengono eliminati semplicemente con JSON statici.

**Mappa:** OpenFreeMap dichiara pubblicamente gratuiti i tile senza limiti/chiavi, ma il suo servizio è offerto «as-is» e non equivale a una garanzia contrattuale. La visualizzazione di punti indicativi non deve suggerire un ingresso preciso.

**Preview:** `raw.githack.com` è un proxy terzo DEV con schermata di conferma e senza SLA di uptime; non va venduto come ambiente production. La versione finale è da distribuire su Pages con preview autentica e verifica del `Network` tab.

Fonti: https://developers.cloudflare.com/pages/functions/pricing/ ; https://developers.cloudflare.com/pages/platform/limits/ ; https://developers.cloudflare.com/pages/functions/routing/ ; https://openfreemap.org/tos/ ; https://raw.githack.com/

## 4. Sicurezza e supply chain

- **MapLibre:** audit npm iniziale: una vulnerabilità *critical* `GHSA-jrc7-96c5-q579 / CVE-2026-85061`, versioni `<=6.4.0`, rischio XSS attraverso stringhe di attribuzione HTML non fidate. Il branch è stato aggiornato a `maplibre-gl 6.14.0`, il run di aggiornamento ha verificato `npm audit --omit=dev` con **0 advisories note** e build riuscita. Aggiunto blocco in `quality.yml` per future dipendenze high/critical. Non equivale ad assenza assoluta di vulnerabilità.
- **Firebase Main:** `firestore.rules` nel branch predefinito concede `allow write: if true` a mercati, fonti, preferiti e segnalazioni. Il branch di review ha regole più sicure ma **non risultano deployate**. Non è stato fatto alcun tentativo anonimo di modifica dell'istanza live. **Verificare e applicare le regole realmente attive prima di rilasciare.**
- **Contenuti utente:** i link fonte vengono limitati a URL HTTP(S) dall'export; popup mappa crea testo usando `textContent`, evitando inserimento diretto di HTML non fidato. Sono punti positivi, non un audit XSS esaustivo.
- **Hardening:** servono verifica CSP compatibile con mappa/font, dipendenze OSS/ToS e gestione incidenti; `X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options` sono previsti in `public/_headers`, ma non abbiamo verificato la loro effettiva applicazione su Cloudflare Pages.

Advisory: https://github.com/advisories/GHSA-jrc7-96c5-q579

## 5. Accessibilità e user journey

Test end-to-end precedenti hanno validato il raggruppamento «Firenze → 4 sedi riportate + 1 record senza sede → giorno Sabato» e la navigazione di base, senza riscrivere i dati originali.

**Prima scansione automatica WCAG 2.0/2.1 AA**:
- `meta-viewport` (critical): pinch-zoom disabilitato da `maximum-scale=1,user-scalable=no`.
- `nested-interactive` (serious): 58 card avevano il bottone Preferiti dentro una card con `role=button`.
- `color-contrast` (serious): 128 nodi sotto i rapporti WCAG richiesti nella schermata iniziale.

**Correzioni sul branch di review:** rimozione dei limiti allo zoom mobile, pulsante semantico separato dal cuore preferiti, palette testuale più scura e leggibile. Non segnare definitivamente *accessibilità OK* senza la verifica Axe dopo le correzioni e test con VoiceOver/TalkBack su device reali.

Ulteriori rischi UX:
- Un record `prevista` non va presentato come apertura confermata.
- Schede con orari e indirizzi assenti devono mostrare il motivo, la fonte e una CTA che non prometta navigazione per un punto impreciso.
- Favoriti in `localStorage`: non passano fra browser/dispositivi, possono scomparire se si cancellano i dati; comunicarlo.
- Città omonime e nomi non canonici: città e regioni devono essere disambiguate e normalizzate.
- Verificare la navigazione da tastiera anche sulla mappa, i focus trap dei pannelli e i contrasti sul dispositivo reale.

## 6. SEO, privacy, legalità delle fonti

- **SEO:** HTML base rende un'unica SPA, lo stesso `<title>` e `description` per tutti; i deep link usano fragment/hash. Manca un URL indicizzabile e metadati strutturati per ciascun mercato. Da valutare pagine prerender statiche selettive solo per schede realmente verificate.
- **Privacy:** i preferiti sono locali, il GPS si chiede esplicitamente, ma i tile della mappa vengono richiesti a OpenFreeMap e i font a Google Fonts. Valutare informativa/terze parti e possibilità di ospitare i font staticamente, nel rispetto delle rispettive licenze.
- **Diritti sui dati:** la prevalenza di Happings/Eventi e Sagre richiede una verifica puntuale di licenze, termini d'uso e diritti su descrizioni. Non dichiarare permesso il riuso commerciale solo perché un contenuto è raggiungibile online.

## 7. Piano correttivo con criteri di accettazione

| Priorità | Intervento | Test per considerarlo chiuso |
|---|---|---|
| **P0** | Sicurezza Firebase live e backup | Scritture anonime a mercati e fonti effettivamente negate dalle regole deployate; nessun danno agli import Admin SDK. |
| **P0** | Rigenerare ricorrenze a ogni refresh + gestione eccezioni, festività e data quality | A +60 giorni copertura dei mercati periodici verificabilmente coerente; non «13 record». Previsti chiaramente distinti da confermati. |
| **P0** | Workflow refresh realmente attivo sul branch di pubblicazione | GitHub Actions pianificato, ultimo run riuscito, report e alert su fallimento. Nessuna pubblicazione di snapshot vuoti. |
| **P0** | Licenze e dati ufficiali prioritari | Prove di autorizzazione/compatibilità licenze, URL per fonte e data reale di ultima verifica per record. |
| **P0** | MapLibre upgrade e dependency gate | `npm audit --omit=dev --audit-level=high` PASS; build e UI smoke PASS prima di qualsiasi rilascio. |
| **P1** | Geocodifica e sedi | Niente centri città spacciati per mercati; quantità di coordinate precise verificata fonte-per-fonte; CTA navigazione coerente. |
| **P1** | Orari e categorie | Aumento misurato della copertura, niente conversioni di sagre in «Misto» senza prova. |
| **P1** | WCAG / device QA | Axe senza critical/serious, pinch zoom vero su Safari/Chrome, navigazione card e preferiti via tastiera e screen reader. |
| **P1** | Performance + hosted Pages preview | LCP/INP/CLS e tempo prima card su 4G/device medio, CDN file statici, nessun Worker/DB in Network, controllo fatture Cloudflare. |
| **P2** | Filtri omonimi/normalizzazione e UX | Elenco città canoniche con provincia, gruppi per sede/giorno, preferiti con limiti dichiarati. |
| **P2** | SEO/analytics/privacy | URL market univoci per schede verificate, JSON-LD accurato, log errori rispettosi della privacy. |

### Release gate finale

Non definire «corretto e ottimizzato» finché **tutti i P0** non sono chiusi e verificati sul dominio/servizi reali. Un test GitHub Actions PASS prova solamente il flusso specificamente coperto dal test; non dimostra l'affidabilità delle 12.650 schede, la sicurezza Firebase deployata o le fatture Cloudflare effettive.

### Riferimenti e riproducibilità

- Codice review: https://github.com/tommyv-spec/mercati-italia/tree/improve/data-quality-security-performance-2026-10-11
- PR: https://github.com/tommyv-spec/mercati-italia/pull/1
- Dataset numerico: https://github.com/tommyv-spec/mercati-italia/actions/runs/38175662762
- Test: `python backend/audit_dataset.py`, `npm run build`, `node --test tests/marketGrouping.test.mjs`, `node tests/audit_browser.mjs`.
- CI post-fix: `.github/workflows/quality.yml`, `.github/workflows/audit-review.yml`.
