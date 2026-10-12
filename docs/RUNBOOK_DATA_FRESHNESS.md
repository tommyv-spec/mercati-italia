# Mercati d'Italia — metodo ripetibile per dati aggiornati

## Regola di lavoro

Non correggere manualmente i singoli mercati per risolvere problemi ricorrenti. Modificare lo script che genera i dati, aggiungere un test del difetto, rieseguire la pipeline e confrontare i risultati con il checkpoint precedente.

Un run riuscito non conferma che gli orari, i mercati o i giorni siano aggiornati. La fonte deve essere verificabile. Le ricorrenze calcolate restano **previste**, non confermate.

## Regola obbligatoria: prima lo faccio una volta, poi lo automatizzo

**Manuale una volta → osservazione → script → test → automazione.**
Questa è la modalità di lavoro predefinita per qualunque nuova fonte, correzione sistematica o funzione del progetto.

1. **Esecuzione reale personalmente controllata.** Leggere la fonte originale, eseguire un esempio completo in modalità sola lettura o in un ambiente isolato, vedere input, passaggi, risposta reale ed effetti. Non basarsi soltanto sulla documentazione o sui metadati.
2. **Capire davvero il procedimento.** Rilevare struttura dei dati, licenza e attribuzione, identificativi, cambiamenti nel tempo, casi mancanti, duplicati, limiti di download e situazioni ambigue. Verificare almeno un caso normale e un caso che deve essere rifiutato.
3. **Salvare la prova ripetibile.** Registrare nel repository, senza segreti o dati personali, le osservazioni utili, un campione minimo consentito, schema e provenienza, un esempio di input/output e i criteri di correttezza. Se non è consentito conservare il campione, salvare soltanto test sintetici e fingerprint.
4. **Solo dopo scrivere lo script.** Trasformare *esattamente* i passaggi verificati in codice deterministico, con parametri espliciti, limiti di rete/costo, logging, gestione errori, checkpoint, idempotenza e modalità offline/dry-run quando appropriata. Non automatizzare ipotesi non verificate.
5. **Confrontare con il lavoro fatto personalmente.** Eseguire lo script sul caso reale verificato e su fixture di regressione; controllare che produca lo stesso risultato, riconosca errori e non introduca effetti indesiderati.
6. **Provare il ciclo completo in DEV.** Misurare qualità, completezza, perdita di ID, duplicati, date, sicurezza, prestazioni e UI mobile. Bloccare la pubblicazione se fallisce uno dei controlli. Salvare report e checkpoint.
7. **Infine pianificare e sorvegliare.** Attivare GitHub Actions soltanto dopo l'esito positivo della simulazione completa. Confrontare ogni nuovo risultato con l'ultimo buono; creare una segnalazione su regressioni o fonti non aggiornate. Evitare un secondo scheduler concorrente.

**Criterio di completamento:** non dichiarare “automatizzato” un flusso finché non esistono (a) esecuzione reale osservata, (b) script nel repository, (c) test di replay e regressione passati, (d) almeno un run DEV completo verificato, (e) un sistema di controllo dei run successivi. Se una parte è mancante, riportarla esplicitamente.

**Esempio già applicato:** per Lombardia MERCap abbiamo prima letto righe e metadati reali, scoperto i record multipli per giorno e una nota storica sulla sede; poi creato adapter, golden test e controllo doppioni; infine fatto un audit completo senza pubblicazione prima di abilitare il refresh giornaliero. Non invertire quest'ordine nelle fonti successive.

## Unico workflow automatico

GitHub Actions: [Mercati Autopilot](https://github.com/tommyv-spec/mercati-italia/actions/workflows/market-autopilot.yml), ogni giorno alle 04:17 UTC e avvio manuale con **Run workflow**.

- Branch con codice e catalogo: improve/data-quality-security-performance-2026-10-11
- Anteprima approvata: dev-static-preview
- Main: soltanto scheduler approvato, nessun catalogo DEV in produzione
- I vecchi publisher automatici sono disattivati per evitare scritture concorrenti
- Cloudflare serve JSON e asset statici; i visitatori non chiamano Firestore, Worker, KV o D1 per leggere i mercati
- Una scheda dell'app rimasta aperta controlla il manifest statico ogni 30 minuti mentre è visibile

GitHub può ritardare uno scheduler. La frequenza giornaliera è un controllo regolare, non una garanzia di conferme in tempo reale.

## Script e checkpoint

| Fase | Script | Responsabilità |
|---|---|---|
| Catalogo | backend/autopilot.py | baseline, source, merge, forecast, export, quality; firma e decisione |
| Scouting | backend/source_scout.py | metadati pubblici, senza import |
| Registro | backend/source_intake.py | fonti nuove, cambiate, storicizzate |
| Schema | backend/source_probe.py | massimo 3 piccoli campioni allowlist, nessun record persistito |
| Diritti | backend/source_evidence.py | licenze dichiarate e data publisher da fonti ufficiali |
| Revisioni | backend/source_change_detector.py | confronto con ultimo report, senza inventare modifiche ai mercati |
| Freschezza | backend/freshness_monitor.py | età reale delle fonti, previsioni e verifiche documentate |
| Avvisi | backend/freshness_alert.py | singola issue GitHub per debito informativo |
| Storico | backend/autopilot_history.py | metriche e checkpoint dopo QA completa |

Gli output vivono in autopilot-output durante il job. Gli artefatti GitHub Actions conservano checkpoint e candidato. Solo dopo test completi sono salvati in reports/automation e, se il contenuto cambia, nei file statici DEV.

## Comandi riproducibili senza rete

Da root del repository:

~~~bash
python -m unittest discover -s backend/tests -v
python backend/autopilot.py --offline --output autopilot-output
python backend/source_scout.py --offline --out autopilot-output/official-candidates.json
python backend/source_intake.py --scout autopilot-output/official-candidates.json --previous reports/automation/source-registry.json --out autopilot-output/source-registry.json --report autopilot-output/SOURCE_QUEUE.md
python backend/source_probe.py --offline --registry autopilot-output/source-registry.json --out autopilot-output/source-probes.json --report autopilot-output/SOURCE_SCHEMA.md
python backend/source_evidence.py --offline --registry autopilot-output/source-registry.json --out autopilot-output/source-evidence.json --report autopilot-output/SOURCE_EVIDENCE.md
python backend/source_change_detector.py --current autopilot-output/source-evidence.json --previous reports/automation/source-evidence.json --out autopilot-output/source-changes.json --report autopilot-output/SOURCE_CHANGES.md
python backend/freshness_monitor.py --manifest autopilot-output/candidate/public/data/v1/manifest.json --publisher-evidence autopilot-output/source-evidence.json --out autopilot-output/freshness.json --report autopilot-output/FRESHNESS.md
python backend/freshness_alert.py --freshness autopilot-output/freshness.json --source-changes autopilot-output/source-changes.json --out autopilot-output/freshness-alert.json
npm ci --no-audit --no-fund
node --test tests/*.test.mjs
npm run build -- --base=./
~~~

Per aggiornare con fonti vere usare **Run workflow** del job GitHub, opzione offline=false. La pipeline chiama gli stessi script e testa anche i percorsi mobile prima di pubblicare DEV.

## Recuperare da un errore

- Leggere il job fallito, il report della policy e i checkpoint del relativo artifact.
- Se si tratta di un errore ricorrente, creare un test che riproduca il caso, quindi correggere lo script.
- Non riusare un checkpoint con firma catalogo, policy o data diversi. Il comando --resume del catalogo rifiuta queste combinazioni.
- Un candidato respinto non può essere copiato nei dati DEV. Il push concorrente è rifiutato senza forzare o ribasare codice non testato.
- La preview è scritta solo dall'Autopilot dopo le verifiche; gli asset delle precedenti versioni rimangono recuperabili.

## Invarianti

1. Ultimo run e data della fonte non sono la stessa cosa. Anche una fonte appena aggiornata non verifica automaticamente ogni appuntamento.
2. Non inventare verificato_il, date confermate, licenze, sedi, giorni o coordinate.
3. Righe con giorni diversi nello stesso dataset possono essere mercati distinti: non unirle per nome/città senza prove.
4. Non interpretare geo_x/geo_y come coordinate WGS84 senza prova. Quartiere e nome mercato sono campi diversi.
5. Le previsioni basate su fonti oltre 540 giorni vanno fatte scadere, conservando identità e provenienza dei mercati.
6. Non abilitare un nuovo importer da soli metadati. Prima occorrono schema controllato, licenza verificata, ID stabili, test e dedup prudente.
7. Non alterare Firebase/Cloudflare live o main come effetto collaterale di un aggiornamento DEV.
8. Misurare variazioni reali e mantenere separati problemi di qualità informativa e problemi tecnici.

## Dove controllare

- [Ultime metriche](../reports/automation/LATEST.md)
- [Freschezza dei dati](../reports/automation/FRESHNESS.md)
- [Licenze e aggiornamenti publisher](../reports/automation/SOURCE_EVIDENCE.md)
- [Confronto revisioni publisher](../reports/automation/SOURCE_CHANGES.md)
- [Coda per nuove fonti](../reports/automation/SOURCE_QUEUE.md)
- [Issue persistente sui dati](https://github.com/tommyv-spec/mercati-italia/issues/2)

**Obiettivo permanente: aggiornare i dati quando cambiano le prove, non aggiornare solo il numero della data.**


## Lombardia MERCap — adapter giornaliero e controllo sovrapposizioni

- Fonte ufficiale: https://www.dati.lombardia.it/d/68zx-njaw
- Adapter: `backend/source_lombardia.py`, con paginazione stabile per `:id`, controllo del conteggio e verifica che `rowsUpdatedAt` non cambi durante il download.
- Le identità usano `lo-mercap-{codice_id}-{giorno}`. Giorni diversi non sono duplicati. Milano città usa ancora il connettore specifico, evitando import doppio.
- Solo periodi settimanali/giornalieri con giorno e mesi dichiarati generano `date_quality=prevista`. Date quindicinali o mensili senza settimana precisa restano sconosciute. Un orario `00:00-00:00` non è considerato apertura valida.
- `aggiornamento_ambito=dataset` separa l'ultima revisione dell'intero dataset dalla verifica del singolo mercato. Il frontend spiega questa differenza.
- `backend/lombardia_overlap.py` fa una seconda verifica su Comune/indirizzo/giorno; casi di stessa sede senza prova sufficiente vengono esclusi dalla nuova importazione e segnalati, senza cancellare le vecchie schede. Risultati ricorrenti: `reports/automation/lombardia-overlaps.json` e `LOMBARDIA_OVERLAPS.md`.
- `backend/autopilot.py` può mettere in quarantena date non più supportate quando un'identità MERCap sparisce dall'ultimo feed valido; cali anomali di righe bloccano il rilascio.
- La prova completa, solo di lettura e senza pubblicazione, si riesegue da GitHub Actions → `Lombardia MERCap full integration audit (no publish)`. Prima dell'attivazione giornaliera si eseguono gli stessi controlli, senza eccezioni manuali.

## Applicazione verificata: Comune di Bologna

Le osservazioni originali del publisher, i conteggi, gli ID e i test si trovano nel [caso manuale Bologna](BOLOGNA_SOURCE_METHOD.md). È vietato abilitare i dati senza il ciclo completo di QA previsto.

## Corciano — primo CSV letto manualmente, testato e ora in DEV

- [Prove manuali e comportamento documentato](CORCIANO_SOURCE_METHOD.md) – quattro mercati, orari, licenza comunale e coordinate con intestazioni invertite.
- Importer riutilizzabile: `backend/source_corciano.py`; checksum SHA-256 originale conservato nei checkpoint e nella scheda di qualità.
- Revisione collisioni: `backend/corciano_overlap.py`; due mercati nuovi (Mantignana e San Mariano), due in quarantena (Corciano mercoledì ed Ellera venerdì) per conflitti nell'archivio precedente.
- Regressione: `backend/tests/test_source_corciano.py` e `test_corciano_overlap.py`.
- Prima simulazione reale completa approvata: [GitHub Actions 38188219950](https://github.com/tommyv-spec/mercati-italia/actions/runs/38188219950), nessuna pubblicazione in quel test.
- Policy giornaliera: dopo la simulazione è abilitata solo per DEV, passando per gli stessi checkpoint, QA, browser mobile e controlli di sovrapposizione.
- Per un CSV successivamente modificato, `backend/source_change_detector.py` confronta l'impronta del file precedente e `backend/freshness_alert.py` segnala una revisione da controllare, senza dichiarare confermati i mercati.
- Gli appuntamenti sono previsioni derivate dalla periodicità dichiarata: gli aggiornamenti della pagina web non sono prova di nuove edizioni.

## Conservazione storica

Le esecuzioni avvengono ogni giorno, quindi `backend/autopilot_history.py` conserva le ultime **400 scorecard versionate** nel repository (oltre un anno). Gli artefatti GitHub Actions, inclusi i file candidati e gli screenshot, scadono secondo il retention del workflow (tipicamente 7–30 giorni); i metodi, i test golden, gli esiti essenziali e gli SHA-256 sono invece salvati in Git.

## Migliorare le schede già presenti prima di importare duplicati

[Metodo riutilizzabile, casi osservati e prova end-to-end](OFFICIAL_ENRICHMENT_METHOD.md): dati Regione Lombardia, confronto Comune/indirizzo/giorno con geolocalizzazione compatibile, orari incompleti recuperati senza verifiche inventate. Prima della pubblicazione DEV il workflow esegue confronto delle identità, audit, test mobile e checkpoint.
