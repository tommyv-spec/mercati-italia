# Fonte nuova: dal controllo reale all'adapter riutilizzabile

## Risultato osservato prima dell'automazione (12 ottobre 2026)

Il sistema consultava sempre gli stessi tre dataset dalla prima pagina del catalogo nazionale, anche se molti avevano già un importer. Delle 42 fonti candidate, le altre rimanevano fuori dai controlli di schema.

Una nuova ricerca con due parole chiave aggiuntive ha trovato una **43ª fonte**, l'Anagrafica mercati della Regione Piemonte. Il documento nazionale riferisce però un ultimo aggiornamento dei dati nel **2019**. Non sono calendari 2026 confermati.

Il primo nuovo ciclo completo è stato approvato:
https://github.com/tommyv-spec/mercati-italia/actions/runs/38190747046

- 43 fonti catalogate (in precedenza 42)
- 26 potenzialmente esplorabili entro la allowlist per URL e formato
- 3 nuove ispezioni di soli schemi completate
- 22 fonti esplorabili ancora mai ispezionate dopo il ciclo
- zero mercati inventati, zero importazioni, zero appuntamenti confermati dal solo probing

## Fonti realmente esaminate prima di scrivere gli script

**Regione Veneto, Comune di Soave**:
https://dati.veneto.it/SpodCkanApi/api/2/rest/dataset/4afb27b6-e3a4-4f25-9dae-5c1fa925e4d9.csv

Nel CSV le colonne principali sono NOME, FIERA/MERCATO, ATTIVITA',
DATA VALIDITA CONCESSIONE e DATA SCADENZA CONCESSIONE. Sono concessioni
amministrative (esempi 2015–2030 e 2031–2039), non un elenco affidabile di
giorni di apertura e indirizzi visitabili. Categoria di schema:
concession_registry_without_visit_schedule. Casalserugo e Fontaniva
sono stati ispezionati separatamente: non applicare mai una categoria a
un altro Comune senza leggerne il file.

**Regione Lazio, censimento mercati mensili**:
https://dati.lazio.it/dataset/74600cc1-0adb-4ae3-8255-30556e03e932/resource/2d48b4df-5df7-48c5-81d8-a8f8758d7756/download/oscomercatimensili.csv

Il file contiene Comune, Provincia, Anno (ad esempio 2007), numero mercati,
posteggi, attivazioni, cessazioni e settori. Non offre sede e calendario
del singolo mercato. Categoria di schema: historical_aggregate_not_venues.
Non gonfiare l'app con una riga per ogni Comune/anno.

**Regione Piemonte, Anagrafica mercati**:
https://www.dati.gov.it/node/view-dataset/dataset?id=26c619d9-ecf8-4882-910e-925a4fb459ec

Il catalogo descrive dati su tipologie, posteggi isolati, luoghi e ricorrenze,
ma l'ultimo aggiornamento del dataset è maggio 2019. La modifica del catalogo
2026 non dimostra freschezza delle singole righe. Usare solo come lead da
controllare, non generare automaticamente date nel 2026.

## Scansione riutilizzabile, incrementale e a costo delimitato

Gli script sono:

- backend/source_scout.py — fino a sei query nazionali mirate, metadata-only
- backend/source_probe.py — fino a tre campioni di schema per ciclo, ciascuno
  limitato a 64 KiB e ai soli host e percorsi ufficiali in allowlist
- backend/source_intake.py — coda di priorità da metadati diretti publisher
  e categorie di schema realmente osservate (mai permesso di import automatico)
- backend/tests/test_source_probe.py e test_source_intake.py — suite
  riproducibile per richieste bounded, rotazione, classi e sicurezza
- main/.github/workflows/market-autopilot.yml — singolo job giornaliero DEV,
  checkpoint ad ogni fase e gate prima della pubblicazione

Le fonti già dotate di adattatori sono escluse dal campionamento ridondante.
Si privilegiano le fonti mai lette, poi quelle viste da più tempo.
All'interno della stessa priorità, i controlli coprono editori/host differenti
prima di scegliere una seconda fonte dallo stesso dominio.

La prova nel file reports/automation/source-probes.json salva ID, data del
controllo, stato, classificazione e SHA-256 dell'intestazione; NON righe o
nomi personali. Lo storico cresce in modo limitato (massimo 400 elementi).

Le classi ammesse sono: market_venue_schedule_candidate,
venue_inventory_missing_visit_days,
historical_aggregate_not_venues,
concession_registry_without_visit_schedule e manual_schema_review_required.

La coda ordinata in reports/automation/SOURCE_QUEUE.md declassa dati storici
o concessioni. Una fonte declassata può scomparire dalle prime 20 posizioni,
ma resta conservata nell'inventario. Non è un errore o cancellazione.

## Comandi per replicare i controlli

Per test offline dalla root GitHub del progetto:

    python -m unittest discover -s backend/tests -v
    python backend/source_probe.py --offline \
      --registry reports/automation/source-registry.json \
      --previous reports/automation/source-probes.json \
      --out /tmp/probes.json --report /tmp/probes.md

Per una nuova lettura di schema limitata (fino a tre richieste pubbliche):

    python backend/source_probe.py \
      --registry reports/automation/source-registry.json \
      --previous reports/automation/source-probes.json \
      --out /tmp/probes.json --report /tmp/probes.md

La coda che combina dati nazionali e verifica della fonte specifica si
rigenera nel job (da file esistenti dello stesso run) così:

    python backend/source_intake.py \
      --scout autopilot-output/official-candidates.json \
      --previous reports/automation/source-registry.json \
      --publisher-evidence autopilot-output/source-evidence.json \
      --schema-evidence autopilot-output/source-probes.json \
      --out autopilot-output/source-registry.json \
      --report autopilot-output/SOURCE_QUEUE.md

## Gate per ogni adapter futuro

1. Leggere personalmente la fonte originale (un caso normale e uno problematico).
2. Stabilire licenza dichiarata, ultima elaborazione dei DATI, schema, ID e
   coordinate; non fidarsi di date del catalogo aggregato.
3. Classificare righe, differenziando interi mercati, posteggi, concessioni,
   anni statistici, feste e calendario con eccezioni.
4. Creare adapter specifico con download limitato, checksum, test golden,
   test negativi e confronti con le schede esistenti.
5. Riprodurre un intero ciclo DEV in sola lettura con mobile Playwright,
   mantenendo versioni precedenti e checklist di anomalie.
6. Consentire la pubblicazione soltanto con tutti i gate approvati;
   la lettura di schema NON concede permesso di importare o verificare eventi.

Obiettivo: qualità e copertura del mercato reale, non record aggiunti senza prove.
Le chiamate di ricerca avvengono nei job GitHub e non nelle visite agli asset
statici, evitando richieste di Cloudflare Worker/KV/D1 o Firebase runtime.
