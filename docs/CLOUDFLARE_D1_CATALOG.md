# Cloudflare D1 — Mercati Italia

Database separato: `mercati-italia-catalog` (D1, giurisdizione UE). Questo archivio **non** è il database Loris e non cambia automaticamente il sito pubblico.

## Contratto

- `catalog_datasets` contiene versioni immutabili e la firma dell'export statico.
- `catalog_markets` conserva tutte le schede per versione, con slug e SHA-256.
- `catalog_channels` tiene solo due puntatori: `dev` e `prod`. Sono indipendenti.
- `happings_source_facts` conserva tutti i dati estratti dalla fonte, compressi, con URL e impronte originali.
- `catalog_import_chunks` e `source_import_chunks` rendono l'import ripetibile. I lotti già verificati non vengono rieseguiti.
- `release_audit` registra ogni cambio del puntatore visibile a un canale.

Il puntatore `prod` parte da NULL. Nessuna operazione di import o di verifica può aggiornarlo. Un futuro comando di promozione deve usare un'approvazione esplicita e verificare che la versione esista e sia completa. Il sito attuale serve ancora file statici Cloudflare Pages; **creare D1 non significa cambiare la produzione**.

## Costi e limiti

Cloudflare Workers Free: 5 milioni di righe lette/giorno, 100.000 scritte/giorno, 5 GB complessivi e massimo 500 MB per singolo database. Non creare servizi a pagamento, non usare runner GitHub a pagamento. Prima di importare un lotto verificare la dimensione e il budget di scritture.

## Ripetibilità

Il catalogo resta versionato in D1 senza trasferire decine di MB attraverso ChatGPT/GitHub ad ogni correzione. Prima si importa la fotografia DEV, poi si verifica il numero di ID, la firma, i campi e i lotti. Solo dopo viene aggiornato il puntatore DEV. Le future correzioni Happings devono leggere il fingerprint della fonte, non inventare orari e non sovrascrivere campi già confermati.

Percorso migrazione: `backend/d1_catalog.py` e `db/cloudflare/0001_catalog.sql`.

### Stato integrazione sito

L'anteprima frontend usa ancora `public/data/v1/*.json`. La parte D1 è un archivio remoto gestito e la base del successivo flusso di pubblicazione; il sito non legge ancora direttamente i suoi canali. Non attivare il frontend D1 senza test end-to-end, autorizzazione e una verifica delle quote Cloudflare.

## Incremental D1 (migrazione 0002, 23 ottobre 2026)

`db/cloudflare/0002_incremental.sql` aggiunge tre tabelle; le sette originali restano inalterate. Il dataset DEV esistente rimane una base immutabile in `catalog_markets`. Ogni versione successiva salva in `catalog_market_changes` solo gli ID nuovi o i record con JSON diverso. Il puntatore padre consente di ricostruire ogni versione usando l'ultima modifica di ogni ID.

Comandi nello stesso ambiente autenticato Cloudflare, usando `backend/d1_incremental.py`:

```text
python backend/d1_incremental.py migrate
python backend/d1_incremental.py status
python backend/d1_incremental.py verify --manifest public/data/v1/manifest.json --source-git-sha <SHA_DELLA_VERSIONE_ATTIVA>
python backend/d1_incremental.py plan --manifest <CANDIDATO>/public/data/v1/manifest.json --source-git-sha <SHA_CANDIDATO> --proof <CANDIDATO>/happings-field-release-report.json
python backend/d1_incremental.py import --manifest <CANDIDATO>/public/data/v1/manifest.json --source-git-sha <SHA_CANDIDATO> --proof <CANDIDATO>/happings-field-release-report.json
```

- `migrate` è ripetibile, crea solo tabelle/indici. `status`, `verify` e `plan` non scrivono sul database.
- `plan` e `import` richiedono validazione completa di indice, asset regionali e firma globale, più una prova QA per l'identica firma e con gli ID originali preservati.
- Ogni lotto salva un'impronta SHA-256 su D1. I lotti già verificati sono saltati al riavvio; contenuti differenti con lo stesso ID o una ricevuta incoerente causano un blocco.
- Il confronto verifica gli hash di **tutti** gli ID, non soltanto il totale. Un ID rimosso, un errore nel riferimento padre, un import incompleto o una versione che cambia mentre si prepara il rilascio bloccano l'attivazione.
- Il puntatore DEV viene aggiornato solo se il padre è ancora quello iniziale. PROD non viene aggiornato dallo script.
- Il limite prudenziale rifiuta un import quando le scritture D1 nelle ultime 24 ore più le modifiche proposte e il margine supererebbero **85.000 righe**. Resta il limite locale di 450 MB di database. In mancanza di informazioni sul consumo, lo script rifiuta di scrivere.
- D1 non viene interrogato dai visitatori: il sito usa ancora asset statici su Cloudflare Pages. Non si attivano abbonamenti, runner GitHub a pagamento o altri servizi.

**Correzione collaterale del controllo qualità:** sei falsi rifiuti sul DEV di ottobre derivavano dalla lettura implicita di `istat-comuni-2026.json` col codec predefinito Windows. Il riferimento ISTAT era corretto. La lettura è ora esplicitamente UTF-8 in `backend/editorial_calendar_scope.py`, senza modificare il dataset ISTAT o le schede.

La sincronizzazione incrementale periodica non è ancora agganciata all'Autopilot: finché non lo sarà, `import` si esegue esplicitamente dopo una prova QA completata. Nessuno di questi passaggi abilita PROD o cambia il sito.
