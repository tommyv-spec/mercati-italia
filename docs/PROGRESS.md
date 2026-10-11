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
- [ ] CP1 — Hardening regole Firestore e disabilitazione demo/seed in produzione.
- [ ] CP2 — Query frontend più corrette e paginazione; protezioni per coordinate e date.
- [ ] CP3 — Ingestione fonte ufficiale Milano e metadata di precisione/provenienza.
- [ ] CP4 — Dedup, ricorrenze e geocodifica; quality gate prima del DB.
- [ ] CP5 — Test, workflow CI, istruzioni di rilascio e audit finale.

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
