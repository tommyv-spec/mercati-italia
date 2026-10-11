# Mercati d'Italia — verifica esperienza utente (2026-10-11)

## Verdetto
NON ancora pronto per il rilascio pubblico come guida attendibile. Il catalogo statico contiene molte schede candidate, ma non tutte hanno date, luoghi e orari controllati. Nessuna verifica umana è presente nel dataset esportato. Questo documento descrive i problemi rilevati dal codice; non sostituisce un test reale su Android/iOS/browser.

## Percorso utente atteso
1. Apro l'app: ricerca, filtri per data e categoria, indicazione chiara che i dati possono essere da verificare.
2. Premo «Mercati vicino a me»: richiesta esplicita del permesso GPS. Senza permesso non appare una distanza inventata; posso filtrare per città.
3. Filtri «Oggi», «Questo weekend», «Prossimi 7 giorni»: distinguere edizioni confermate da previsioni calcolate; mai presentare una ricorrenza come conferma ufficiale.
4. Elenco: nome, città, categoria, prossima data o «Data da verificare», orari o «Orari da verificare», distanza SOLO se autorizzata.
5. Apro la scheda: descrizione quando disponibile, giorni/date, orari, indirizzo, livello di precisione, fonte, data della fonte e ultima verifica.
6. Toccco «Indicazioni»: si apre un servizio esterno con indirizzo reale o punto preciso, altrimenti comando disabilitato.
7. Toccco «Condividi»: link funzionante alla scheda (via hash, senza route server), o copia link.
8. Salvo nei Preferiti: persistenza locale. Agenda mostra i preferiti con date prossime; nessuna promessa di push che non esiste.

## Interventi implementati sul branch di review
- [x] Vietate distanze da Firenze di default. Posizione solo con consenso esplicito.
- [x] Filtro città manuale esegue una vera ricerca per città.
- [x] Filtro/ranking distanza disabilitato senza geolocalizzazione.
- [x] Eliminati finti controlli di notifiche: «Agenda» reale dei preferiti, con nota che push non è disponibile.
- [x] Condivisione con deep link alla scheda; copia link come alternativa.
- [x] «Indicazioni» apre Google Maps solo se destinazione disponibile; «Copia» non dichiara successo falso.
- [x] Schede con orario mancante mostrano testo chiaro.
- [x] Rimossa finta minimappa dai dettagli.
- [x] Vista Italia indicata come SCHEMA e non come mappa stradale.
- [x] Lista a pagine per non renderizzare migliaia di schede contemporaneamente.
- [x] Data prevista/confemata e completezza dati distinte dalla verifica umana.
- [x] Dataset servito come file statici; preferiti locali (Cloudflare: nessun Worker/D1 richiesto durante la lettura).
- [x] Caricamento leggero per indice con dettagli lazy per singola regione (verificare le prestazioni su dispositivi reali).

## Problemi ancora aperti — non nasconderli
- [ ] Mappa stradale reale, pan/zoom, marker clustering e navigazione: attualmente solo vista geografica schematica. Scegliere provider/hosting coerente con costi nulli lato Cloudflare Worker. Non fare uso massivo non autorizzato di tile pubbliche OSM.
- [ ] Controlli end-to-end su Android/iPhone (GPS consentito/rifiutato, schede senza data, deep link, navigazione esterna, browser e offline).
- [ ] Verifica sul sito pubblico e sul dashboard Cloudflare: codice GitHub non prova il deploy né gli addebiti.
- [ ] Affidabilità delle fonti, orari, date precise e distinzione mercato/fiera/sagra a livello di catalogo; il 100% di completezza non è garantito.
- [ ] Controlli periodici di reali cancellazioni, trasferimenti e chiusure; una «data prevista» non basta.
- [ ] Test accessibilità con lettore di schermo, contrasto, mappa e tastiera.
- [ ] PWA/offline completo e notifiche push se in futuro richieste. Per ora Agenda non invia alcun push.
- [ ] Filtro «solo date confermate» quando disporremo di date effettivamente verificate.
- [ ] Test quantitativi reali: tempo prima lista utilizzabile, trasferimento dati, frame rate su telefoni economici, errori per connessioni mobili lente.

## Criteri di rilascio
Non dichiarare l'app «completa e verificata» finché:
- le funzionalità visibili hanno effetto reale oppure sono chiaramente etichettate come non disponibili;
- dati non verificati/non presenti sono mostrati come tali;
- la nuova release passa test automatici ed end-to-end su dispositivi;
- Cloudflare serve le richieste di catalogo come file statici (Network browser + dashboard);
- i campi più importanti delle schede scelte per il test (date, luogo e orario) sono confrontati con fonti primarie recenti.

## Checkpoint UX browser mobile — 11 ottobre 2026
- Browser Chromium mobile emulato (390x844); test visita schermata principale, scheda, ricerca città, autorizzazione GPS e Agenda.
- Run iniziale: https://github.com/tommyv-spec/mercati-italia/actions/runs/38166839296 — PASS. 60 card renderizzate (paginazione), nessun errore JS, zero richieste a Firestore/Workers nella visita simulata. Artefatto con screenshot nella pagina Actions.
- La schermata reale ha mostrato difetti che il build statico NON poteva trovare: risultati non pertinenti, doppioni e titoli riferiti al 2023, distanze «circa 0 km» ricavate da coordinate non verificate, elenco iniziale di oltre 13.000 candidati.
- Correzioni dopo la review visiva: predefinito filtro «prossimi 7 giorni» (deselezionabile), pulsante vicino a me con raggio indicativo di 50 km, nessun numero di chilometri per coordinate non verificate, ordinamento che privilegia posizioni precise, avvisi visibili su approssimazioni. Aggiunti filtri a monte per edizioni storiche senza date future e città senza lettere.
- Serve rieseguire export statico con i nuovi filtri prima della produzione. Non eliminare definitivamente i record sorgente; tenere traccia degli esclusi e analizzare i falsi positivi.
- Test mobile ripetuto anche sulle nuove etichette vicino a me; richiedere screenshot più recente prima di chiudere il checkpoint.
- Test automatico mobile non equivale a user testing: devono ancora essere verificati manualmente i flussi su Android e iPhone fisici e con accessibilità attivata.
