# Località e doppioni: verifica manuale → logica di visualizzazione → audit giornaliero

## Problemi reali verificati prima di scrivere gli script

Il 12 ottobre 2026 si è confrontato direttamente il catalogo DEV nazionale con
le pagine di origine (solo lettura), mantenendo i record originali.

1. **Albizzate (VA), Piazzale Sefro, martedì**:
   https://www.happings.com/it/mercato-settimanale-a-albizzate.html

   Sul sito sorgente è riportato un mercato in questa sede e giorno;
   il catalogo nazionale ha due schede con stessa URL Happings,
   stesso Comune, sede, giorno settimanale e settimane previste.
   Il codice sorgente ufficiale MERCap 100001 ne documenta sede,
   martedì e fascia oraria 08:00–13:00 (non è verifica di apertura
   del mercato in una data specifica).
   https://www.dati.lombardia.it/d/68zx-njaw

2. **Breganze (VI), Piazza Mazzini, mercoledì**:
   https://www.happings.com/it/mercato-settimanale-a-breganze.html

   La fonte riporta il mercato in piazza il mercoledì; due schede
   precedenti derivano anche da una stessa pagina EventieSagre,
   con identiche settimane previste. Se un'altra fonte o il giorno
   è discordante, NON trattarla come lo stesso appuntamento.

3. **Firenze**: sei schede di mercati settimanali e una settima
   sede generica (indirizzo mancante) non devono fondersi fra loro;
   ogni giorno e sede rimane identificato. Per i dettagli, l'UI
   usa il file regionale lazy-load, non richieste cloud a pagamento.

4. **Località corrotte dal parser**:
   - Cernobbio, "Mercatino delle Curiosità": il nome dell'evento
     era nel campo Comune al posto della località;
   - "Fiera del Disco" come città per una scheda a Fiumicino;
   - codici Provincia NA, BO, RM nel campo Comune;
   - testo concatenato ad altri mercati come
     "in provincia di... Mercato settimanale a..."
   - Nomi veri "Piazza Brembana" e "Piazza al Serchio"
     **non sono errori** solo perché contengono "Piazza".

## Script e metodi che abbiamo riprodotto

- \`src/lib/marketGrouping.js\`:
  \`sameWeeklyVisitEvidence\` e \`groupVenueAppointments\`.
  Un appuntamento può essere raggruppato **solo** quando coincidono
  esattamente Regione, Comune, indirizzo specifico, categoria,
  URL sorgente, due settimane consecutive e ricorrenza settimanale,
  senza differenze nei due orari quando entrambi sono presenti.
  Coordinate discordanti oltre 250 metri bloccano il raggruppamento.
  Identità ufficiali MERCap/Bologna/Corciano, singole date, mensili,
  giorni diversi, città o fonti differenti restano separati.
  Le schede originali sono apribili in "Mostra originali".
- \`src/lib/locationQuality.js\`:
  classificazione conservativa di città palesemente malformate.
  L'app presenta "Località da verificare", conserva ricerca per titolo,
  esclude questi testi dalla scelta dei Comuni e disabilita
  indicazioni stradali per schede con Comune dubbio. **Non cambia**
  dati pubblicati, coordinate, fonti, slug o verifiche.
- \`tests/marketGrouping.test.mjs\`, \`tests/location-quality.test.mjs\`,
  \`tests/reversible-duplicate-audit.test.mjs\`: fixture reali e
  controesempi che devono rimanere separati.
- \`tests/ui-smoke.mjs\`: test mobile end-to-end (Albizzate = uno
  appuntamento + due schede originali; Firenze non regressa;
  Cernobbio resta ricercabile e navigazione bloccata).
- \`scripts/reversible-duplicate-audit.mjs\`: legge i venti shard
  regionali originali, richiama la **medesima funzione della UI**,
  confronta tutti gli ID col manifest e produce JSON/Markdown
  senza scrivere le schede.
- \`backend/autopilot_history.py\`: integra metriche nel diario
  delle esecuzioni DEV (fino a 400 report giornalieri).
- \`.github/workflows/reversible-duplicate-audit.yml\`:
  dry-run separato per misurare risultati prima dell'attivazione.

## Prova completa nazionale e test di ripetibilità

Isolato, nessuna pubblicazione:
https://github.com/tommyv-spec/mercati-italia/actions/runs/38242606879

Successivo test con entrambe le protezioni e mobile:
https://github.com/tommyv-spec/mercati-italia/actions/runs/38243216144

Esecuzione quotidiana con tutti i gate e pubblicazione DEV:
https://github.com/tommyv-spec/mercati-italia/actions/runs/38243731464

Risultato dopo controllo di tutte le 20 regioni:

| Metrica | Osservazione |
|---|---:|
| Record originali | 13.779 |
| Record originali conservati | 13.779 |
| Gruppi stessa fonte e visita compatibile | 382 |
| Pulsanti ripetuti non più mostrati in vista sedi | 382 |
| Record dietro gruppi, accessibili | 764 |
| Località palesemente malformate schermate | 52 |
| ID eliminati | 0 |
| Nuovi eventi dichiarati confermati | 0 |
| Verifiche individuali inventate | 0 |

Distribuzione del gruppo conservativo: Lombardia 375; Piemonte 2;
Toscana 3; Veneto 2. **Non** sono 382 mercati chiusi o cancellati:
si tratta solo di pulsanti di visita mostrati una volta invece che
due nella vista delle sedi.

Il vecchio audit più largo aveva 755 gruppi potenzialmente sovrapposti:
la differenza è intenzionale. Solo i 382 con prove rigorose sono
compressi dalla UI; gli altri restano distinti.

## Metodo per il prossimo passo: Comune validato con fonte ISTAT

L'etichetta prudente è una protezione, non la soluzione definitiva.
Per ricostruire il Comune di quelle 52 schede:

1. Consultare la classificazione ufficiale ISTAT e registrare data,
   licenza, codici dei Comuni e Regione.
   https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/
2. Leggere a mano almeno due esempi originali malformati e uno
   "Piazza Brembana" valido per calibrare i falsi positivi.
3. Preparare un **report di ipotesi**, non una modifica automatica:
   solo confronto esatto del Comune / Regione, più fonte originaria,
   indicando quando il titolo contiene più località o toponimi.
4. I record ambigui rimangono in quarantena. Nessuna cittadinanza
   inventata da titoli, URL o coordinate stimate.
5. Solo i casi verificati con fonte originale potranno avanzare
   a un nuovo adapter con test, dry-run e gate mobile.

## Esecuzione ripetibile

~~~bash
node --test tests/marketGrouping.test.mjs \
  tests/location-quality.test.mjs \
  tests/reversible-duplicate-audit.test.mjs

node scripts/reversible-duplicate-audit.mjs \
  --manifest public/data/v1/manifest.json \
  --out /tmp/reversible-display-duplicates.json \
  --report /tmp/REVERSIBLE_DISPLAY_DUPLICATES.md
~~~

La stessa lettura si esegue prima di ogni rilascio DEV nel job
\`market-autopilot.yml\`, confrontando il numero totale degli ID,
la lista dei Comuni sospetti con \`backend/catalog_quality_report.py\`,
e l'ultima versione approvata. Incrementi anomali bloccano il rilascio.
Gli snapshot permanenti sono
\`reports/automation/reversible-display-duplicates.json\`,
\`REVERSIBLE_DISPLAY_DUPLICATES.md\` e \`latest.json\`.

Il sistema non genera richieste Firebase/Cloudflare durante la lettura:
i dati delle sedi sono file JSON statici CDN, caricati su richiesta.
