# Mercati d'Italia — checkpoint e piano operativo
Aggiornato: 2026-10-11. Branch: `improve/data-quality-security-performance-2026-10-11`.
Nessuna modifica di questo branch deve essere considerata deployata finché non viene verificata su Firebase e sul sito pubblico.

## Obiettivi
1. Sicurezza: bloccare modifiche pubbliche ai mercati; togliere l'inserimento di demo nel browser; separare demo/produzione.
2. Prestazioni: rimuovere limite invisibile di 300 record, introdurre fetch paginato, evitare date scadute e fallback silenziosi.
3. Qualità: provenienza per campo, geocodifica prudente, ricorrenze affidabili, non perdere dati verificati nella fusione.
4. Quantità: connettore funzionante per una fonte ufficiale strutturata; framework per altre fonti con import ripetibili.
5. Test: controlli di normalizzazione, deduplicazione, fonti e sicurezza; CI GitHub.
6. Operatività: controlli di copertura/affidabilità e report dry-run prima di scrivere in Firestore.

## Checkpoint
- [x] CP0 — Audit repo: pipeline monofonte, geocodifica che ripiega sul centro città, merge con perdita fonti, ricorrenze fragili, read max 300, Firestore aperto.
- [x] CP1 — Regole Firestore sicure versionate + auto-seed browser disabilitato (**da distribuire manualmente su Firebase**).
- [x] CP2 — Frontend passato a lettura statica + preferiti locali, 0 query DB per vista; eliminato limite 300, date hardcoded e mock dal bundle (**catalogo iniziale non ancora esportato**).
- [x] CP3 — Importatore Comune di Milano DS291 (fonte 2024: date previste, NON confermate); esportatore statico con chunk adattivi, cache immutabile e manifest.
- [ ] CP4 — Merge conservativo + provenance e quality gate implementati; restano da migliorare dedup cross-source e parser delle ricorrenze originali.
- [ ] CP5 — Test Python e build Vite configurati in GitHub Actions; PR #1 aperta in bozza. Verifica in corso e istruzioni di rilascio da completare.

## Note
- La configurazione Firebase nel frontend è pubblica per progetto: il vero controllo di accesso sono le regole Firestore.
- Le regole versionate NON cambiano la produzione senza un deploy esplicito.
- Import da ArcGIS: layer `MSS_Mercati_Settimanali_Scoperti` del Comune di Milano, licenza CC BY 4.0; separare la data della fonte dall'ultima scansione.
- OSM/Nominatim pubblico: niente scraping sistematico/bulk geocoding, rispettare limiti, usare coordinate da fonti ufficiali quando presenti.
- Bloccare nelle viste “confermato oggi” per sole date generate: le occorrenze stimate restano etichettate.
- Non sostituire o cancellare i documenti Firestore esistenti durante le importazioni senza snapshot e riconciliazione.

## Verifiche finali previste
- [ ] Esecuzione test Python e JavaScript
- [ ] Build Vite (se l'ambiente consente installazione dipendenze)
- [ ] PR review e differenze controllate
- [ ] Pubblicazione regole con credenziali del progetto (se autorizzata e tecnicamente possibile)
- [ ] Dry-run sorgenti reali con conteggi; solo dopo, import in DB

## Cloudflare, costi e release (2026-10-11)
- Design selezionato: Vite SPA statica su Cloudflare Pages, nessuna funzione eseguita su `/`, `/assets/*` o `/data/*`; pubblico legge manifest + file immutabili; preferiti localStorage.
- Pagina tariffe ufficiale: https://developers.cloudflare.com/pages/functions/pricing/ (richieste asset statici gratis e illimitate, le Functions/Workers sono soggette a fatturazione/quote).
- Configurazione nel repo: `public/_routes.json` riserva alle Functions solo `/api/*` e `public/_headers` imposta cache; una route esterna definita nel dashboard potrebbe comunque invocare un Worker.
- Il consumo Cloudflare reale NON è ancora stato ispezionato. Né Firebase rules né Cloudflare Pages sono stati deployati.
- `backend/export_static.py`: input JSON dalla pipeline o `--firestore` con Firebase Admin SDK; no richieste ai DB durante le visite. Rifiuta dataset vuoti e forti cali; manifest pubblicato per ultimo.
- `backend/merge_catalog.py`: unisce feed nuovi al catalogo già validato senza cancellare assenti; gestisce collisioni senza fondere arbitrariamente mercati distinti.
- `backend/source_milano.py`: primo connettore; la base è 2024 e richiede riconferma prima di dichiarare date reali.
- `.github/workflows/refresh-data.yml`: update settimanale, ma si FERMA se manca il catalogo baseline; questo evita di rimpiazzare il catalogo nazionale con la sola Milano.
- `.github/workflows/quality.yml`: test e controllo build su ogni PR e branch improve.
- Branch: https://github.com/tommyv-spec/mercati-italia/tree/improve/data-quality-security-performance-2026-10-11
- PR in bozza: https://github.com/tommyv-spec/mercati-italia/pull/1

## Prima di fare merge o attivare il nuovo sito
1. Backup del Firestore esistente e primo export in `public/data/v1/manifest.json` usando `backend/export_static.py --firestore` (servono credenziali Firebase Admin, non disponibili nella sessione GitHub).
2. Validazione `python backend/validate_static.py --manifest public/data/v1/manifest.json` e confronto visuale di mercati, filtri e date.
3. Esecuzione e superamento di tutti i test, verifica richieste Network browser: solo HTML/JS/CSS/JSON statici.
4. Deployment separato delle regole Firestore (procedura Firebase Console o CLI).
5. Controllo Cloudflare billing/Workers routes reali nel dashboard. Non promettere spesa zero per altri servizi attivi (dominio, piano, ecc.).
