# Importazione riutilizzabile: una sola approvazione per ogni fonte

Aggiornato il 13 ottobre 2026. **Lo standard è il dataset, non la singola scheda.**

## Stato verificabile

Il sistema generico esiste già nel branch DEV. Il registro backend/data/approved-source-admissions.json è volutamente vuoto: per ora **zero nuovi publisher autorizzati e zero aperture individuali confermate**.

## Pipeline

    Scoperta ufficiale di un dataset (ente e licenza)
                |
          Contratto JSON della fonte
     schema, ID, data dati, giorno, orari, tipo riga
                |
    Download limitato HTTPS, niente redirect né browser utente
                |
    Parser condiviso CSV o JSON + fingerprint per identità
                |
    Staging: nuova sede / identità esistente / collisione
                |
    Solo se un certificato della FONTE è stato approvato
                |
     Candidate DEV con limite al numero di nuove schede
                |
    Confronti pre/post export + indice, ricorrenze previste
      GPS ignoto, navigazione sospesa, provenance originale
                |
     Gate QA, sicurezza browser, release SOLO DEV

## Componenti e compiti

- backend/data/market-source-contracts.json: contratto per intero dataset. Una volta definito, l'aggiunta di un nuovo mercato non richiede nuovo codice.
- backend/source_lifecycle.py: analisi versionata di nuovi ID, scomparsi, cambi di schema, anagrafiche e staging. Riutilizza gli stessi byte scaricati.
- backend/source_contract_ingest.py: generazione uniforme delle schede candidate da CSV/JSON, senza duplicati. Una fonte non approvata non può diventare pubblica.
- backend/source_contract_parity.py: confronto con il precedente importer sullo STESSO CSV. Il pilot Corciano ha riprodotto tutti e quattro gli ID, indirizzi, giorni e orari in un test indipendente.
- backend/data/approved-source-admissions.json: autorizzazione a livello di fonte. È vuoto finché diritti, identità e schema non sono stati esaminati.
- backend/source_contract_activation.py: ammette in DEV tutti i record non ambigui di una fonte autorizzata, rispetta il limite per fonte e isola sorgenti non disponibili.
- backend/autopilot.py: orchestrazione, previsione, export statico, controlli, assenza di chiamate a consumo per visita.
- backend/reviewed_city_static_guard.py e backend/autopilot_history.py: proteggono i vecchi dati e rendicontano separatamente le nuove schede di fonti approvate.

## Approvazione UNA TANTUM del nuovo publisher

1. Verificare personalmente, sulla pagina dell'editore originale, licenza della distribuzione, data effettiva e identità delle sedi. Metadati aggregati o concessioni per posteggio non sono mercati con aperture confermate.
2. Aggiungere un contratto alla sezione raw_profiles di backend/data/market-source-contracts.json con resource_url, schema_columns, identity_fields, municipality, region, province, weekday_field, street_fields, formato, limite di righe e dimensione.
3. Definire correttamente row_kind: market_venue o market_venue_day. Una riga di tipo concession, stall o aggregate NON deve essere convertita in nuovo mercato.
4. Provare in shadow la fonte completa: identità e orari rispetto al vecchio importer (se esiste), collisioni sede/giorno, fonte vecchia, ID rinominati, riuso e indirizzi. Il sistema non dovrebbe richiedere 100 verifiche individuali.
5. Se le prove di fonte e diritti sono positive, passare il profilo ad approved_dev_only, contrassegnare legal_reuse_reviewed come true e stabilire max_new_ids_per_run basso.
6. Registrare UNA voce in approved-source-admissions.json. Il certificato vincola source_id, SHA-256 del profilo, data di revisione, URL ufficiale della licenza, tipo di identità e limite delle nuove schede. Aggiornare i fingerprint Git pin della policy sotto revisione.
7. Il job schedulato applica sempre lo stesso parser e le stesse regole a tutti i record successivi. Se una riga è ambigua, l'ID viene trattenuto. Se la fonte non risponde, restano i dati precedenti. Non vengono creati eventi verificati.

## Regole di sicurezza non negoziabili

- Nessun timestamp della pagina o del download può certificare l'apertura di un mercato.
- Se la fonte non è raggiungibile o cambia struttura, lo stato resta da riconciliare, non chiuso.
- Identità senza indirizzo/giorno certo e possibili doppioni restano in staging.
- Nessun GPS da colonne senza controllo CRS; nuove indicazioni stradali disabilitate.
- Nessun titolare di concessione, contatto o dato personale entra nei rapporti.
- Solo il branch DEV può ricevere candidate approvate. Mai pubblicare in produzione da questo job.
- Il report finale controlla ID originali, source URLs, giorni previsti, stati di conferma, ricerca mobile e costo statico.

## Verifica riproducibile

    python -m unittest discover -s backend/tests -v

    python backend/autopilot.py --offline --today 2026-10-13 \
      --output /tmp/source-generic-test

Workflow read-only originale e parity:
.github/workflows/source-contracts-full-audit.yml

## Limiti ancora presenti

Il convertitore generico attuale copre file CSV/JSON piccoli e URL che superano i controlli HTTPS/host già ammessi. Per provider di dimensione maggiore, API paginata, geodati complessi, PDF non strutturati o un nuovo dominio ufficiale, bisogna estendere la gestione di quel TIPO DI SORGENTE, non scrivere eccezioni per ogni mercato. Non affermare che tutte le 43 fonti candidate siano già importabili.

Il file delle fonti approvate è vuoto; anche dopo test verdi la presenza di un'opzione tecnica di import NON costituisce da sola approvazione della licenza.
