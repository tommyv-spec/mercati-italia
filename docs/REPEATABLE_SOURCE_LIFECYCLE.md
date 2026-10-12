# Mercati d'Italia — sistema ripetibile di qualità e copertura delle fonti

Aggiornato: 13 ottobre 2026. **L'unità di lavoro quotidiano è il DATASET, non il singolo mercato.**

## Perché cambiare

Il catalogo DEV ha 13.784 ID. Esistono già uno scout nazionale, un inventario di 43 fonti, campioni degli schemi, adattatori approvati, forecast, test mobile, workflow quotidiano e output statici. Ma aggiungere un nuovo Comune è ancora troppo simile a scrivere eccezioni per decine di mercati. La metodologia sottostante va resa indipendente dai nomi dei mercati.

## Come funziona

    SCOPERTA (dati.gov.it, CKAN, portali enti)
             ↓
    Registro versionato di fonti e licenze dichiarate
             ↓
    Controllo leggero dello schema (max 3 × 64 KiB/ciclo)
             ↓
    Un CONTRATTO JSON per editore/dataset
    Schema, significato della riga, ID, giorni, timestamp,
    URL approvato, limite bytes, licenza, policy
             ↓
    Scaricamento bounded (solo endpoint HTTPS in allowlist)
             ↓
    Parser condiviso CSV/JSON → osservazioni immutabili
             ↓
    Fingerprint per identità + fingerprint per attributi
             ↓
    DIFF: identità nuova/variata/non più vista
             ↓
    Confronto con catalogo (ID esatto, sede, Comune, giorno)
             ↓
    ┌────────────────────────┬─────────────────────────────┐
    │ Fonte e identità sicure│ Conflitto/schema cambiato   │
    │ → candidato in staging │ → quarantena e revisione    │
    └────────────────────────┴─────────────────────────────┘
             ↓
    Release DEV solo dopo controlli di diritti, ID, date,
    GPS, conservazione fonti, output JSON, UI mobile e costo
             ↓
    Trend giornaliero, checkpoint e rollback, mai riscrittura
    automatica della produzione

## Differenze fondamentali

| Concetto | Interpretazione consentita | Interpretazione vietata |
|---|---|---|
| Riga di un mercato | Identità di una sede | Una nuova apertura confermata |
| Riga con giorno | Programma previsto, se fonte abbastanza recente | Mercato distinto ogni settimana |
| Concessione per posteggio | Dato amministrativo | Nuovo mercato per ogni commerciante |
| Archivio di posti/anno | Statistica | Elenco di mercati visitabili |
| Metadata aggiornati oggi | Timestamp catalogo | Verifica singolo mercato oggi |
| Riga sparita | Cambiamento o assenza della fonte | Mercato chiuso o record cancellabile |
| Coordinate senza CRS/controllo | Prova da esaminare | Nuova navigazione affidabile |
| Due mercati omonimi | Possibile conflitto di identità | Fusione automatica non reversibile |
| Fonte irraggiungibile | Errore fonte; checkpoint precedente mantenuto | Zero mercati disponibili |

## Nuovo codice condiviso

**Contratti:** backend/data/market-source-contracts.json. Dichiarano fonte, URL, formato, colonne, ID, Comune, giorni, soglie, età dei dati, granularità della riga e permessi. Una nuova fonte strutturata richiede la revisione di UN profilo, non la codifica di un mercato per volta.

**Motore:** backend/source_lifecycle.py. Un parser CSV/JSON generico, hashing stabili, diff tra scansioni, validazione di righe, sicurezza URL, intestazioni, giorni/orari, distinzione concessioni e mercati. In parallelo controlla i record dei cinque adattatori già approvati senza scaricarli di nuovo.

**Pilota:** Comune di Corciano, scaricando il suo CSV da un URL esatto autorizzato. Le colonne long/lat sono invertite nella sorgente: il parser generico le ignora del tutto, non le esporta come GPS. I 4 record del file non diventano automaticamente 4 nuove schede. Le due schede non presenti con ID uguale al catalogo sono candidate alla riconciliazione, non nuovi mercati approvati.

**Test:** backend/tests/test_source_lifecycle.py. Le prove includono fonte non raggiungibile, schema variato, duplicati, dati amministrativi, giorno 'Nessun giorno', fonte vecchia, metadata non probatori e URL malevoli.

La modalità attuale di ogni nuovo profilo è shadow_only, senza importazioni, aggiornamenti, coordinate, date confermate o scrittura in Cloudflare. Si mantiene l'adapter specializzato finché un confronto ombra dimostra che quello generico produce fatti equivalenti.

## Onboarding di una fonte: cinque attività, non 500 mercati

1. Trovare la distribuzione ufficiale e i permessi di riuso effettivi, non soltanto la scritta 'open data' nel catalogo.
2. Indicare per tutto il dataset se ogni riga è sede, sede-giorno, posteggio, concessione o statistica; scegliere un ID fonte immutabile. Senza ID affidabile, le varianti rimangono in review.
3. Configurare una sola volta il contratto JSON: colonne consentite, policy di data, sede, evento, schema atteso e limiti di download.
4. Eseguire in shadow un ciclo completo e verificare classificazioni, collisioni, cambi, date, diritti, soglie e punti GPS. Il test non deve amplificare il numero dei mercati.
5. Abilitare successivamente il publisher nel flusso DEV, con budget per nuovi ID e blocco automatico sulle anomalie. La produzione richiede una promozione distinta.

## Manutenzione giornaliera senza mouse

- GitHub Actions esegue il pull bounded delle fonti autorizzate; i visitatori leggono JSON statici, non interrogano Cloudflare Functions per cercare mercati.
- Confronta la firma degli ID e degli attributi del dataset con il precedente run. I nomi e gli indirizzi grezzi non vengono duplicati nello storico dell'audit; le anomalie sono aggregate e ricostruibili per hash.
- **Prova puntuale del filtro sovrapposizioni:** i 233 ID Lombardia e i 2 ID Corciano esclusi dal feed non sono automaticamente "235 nuovi mercati". Lo stesso run confronta, *solo in RAM*, tutti gli ID della fonte con gli ID esatti restituiti dagli screen di sovrapposizione. Pubblica soltanto conteggi e hash del set degli esclusi. Coincidenze numeriche non bastano: se manca il set reale, i record sono classificati "senza esito", non "già verificati". Un risultato da controllare non conferma un'apertura.
- Se i record scompaiono, salva una coda di eccezioni senza rimuovere i vecchi dati. Il primo run non considera come 'nuove aperture' tutte le identità incontrate.
- I controlli distinguono età del dataset, età del singolo record, data dello scraper e data di verifica effettiva. Nessuna IA trasforma un titolo o una data metadata in apertura verificata.
- La policy permette al massimo i campioni approvati. Errore fonte, schema o rete = diagnosi/hold, non perdita di mercati.
- Report e checkpoint restano nel branch DEV. Lo scheduler non accede al mouse o alla sessione browser dell'utente.

## Comandi da repository

Test di regressione:

    python -m unittest discover -s backend/tests -v

Ciclo senza rete su file normalizzati già acquisiti:

    python backend/source_lifecycle.py --manifest public/data/v1/manifest.json \
      --source-dir autopilot-output/sources \
      --previous reports/automation/source-lifecycle.json \
      --out /tmp/source-lifecycle.json --report /tmp/SOURCE_LIFECYCLE.md

Verifica limitata del CSV ufficiale Corciano (una sola richiesta, solo lettura):

    python backend/source_lifecycle.py --manifest public/data/v1/manifest.json \
      --probe-raw --previous reports/automation/raw-source-lifecycle.json \
      --out /tmp/raw-source-lifecycle.json \
      --report /tmp/RAW_SOURCE_LIFECYCLE.md

## Confini tra già disponibile e lavori futuri

**Già implementato:** discovery, registry, campionamento, vari adapters, forecast, DEV statico, conservazione fonti, protezioni geografiche, test browser, contratti condivisi e diff sorgenti read-only.

**NON ancora generalizzato:** ammissione automatica a DEV da qualunque nuovo schema. Per attivarla servono approvazione dei diritti a livello di dataset, una policy firmata, confronto forte di identità ed eventuale promozione di un adapter in shadow alla modalità di import. Un parser che legge 10.000 concessioni non è autorizzato a creare 10.000 mercati.

La prossima ottimizzazione di scala è migrarne uno alla volta **come fonte intera**, mantenendo comparazioni automatizzate su tutte le sue righe, non progettare a mano ogni nuovo mercato.
