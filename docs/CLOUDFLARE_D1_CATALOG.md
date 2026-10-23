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
