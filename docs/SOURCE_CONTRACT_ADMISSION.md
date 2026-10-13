# Importazione riutilizzabile: una sola approvazione per ogni fonte

Aggiornato il 13 ottobre 2026. **Lo standard è il dataset, non la singola scheda.**

## Stato verificabile

Il branch DEV ha due contratti generici autorizzati: Corciano (quattro righe, due ID già pubblicati, due sovrapposizioni in quarantena) e Bologna (dataset comunale filtrato, 48 righe di mercato e 39 sedi attualmente ammissibili). Nella prima simulazione del ciclo Bologna sono state aggiunte **5 schede candidate**, con **34 rinviate a cicli successivi**. Ogni fonte ha un certificato e fingerprint Git. Sono schede DEV `non_confermato`, non nuove aperture verificate. Nessuna modifica automatica alla produzione.

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
- backend/data/approved-source-admissions.json: autorizzazioni firmate per fonte; al momento sono due e valgono solo su DEV.
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
7. Il job schedulato applica sempre lo stesso parser e le stesse regole a tutti i record successivi. Se una riga è ambigua, l'ID viene trattenuto. Se la fonte non risponde, restano i dati precedenti. Non vengono creati eventi verificati. Se una fonte approvata contiene più candidati non ambigui del limite giornaliero, il parser seleziona un lotto ordinato per ID stabile. Gli altri restano in attesa, con solo conteggio e hash; il ciclo successivo riprende gli ID non ancora pubblicati. Non sono richieste approvazioni per singolo mercato.

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

Corciano e Bologna sono fonti CC BY 4.0 con attribuzione. La licenza NON prova aperture, orari 2026 o localizzazioni precise. Ogni fonte nuova richiede review di editore, licenza, identità e schema; i singoli mercati non richiedono nuova approvazione. Una fonte può produrre zero record aggiuntivi se sono tutti già presenti o ambigui.

Per l'API Opendatasoft v1 di Bologna il parser condiviso:
- proietta soltanto colonne dichiarate, verifica `datasetid`, `recordid` esadecimale SHA-1 da 40 caratteri e `nhits==len(records)` (niente pagine incomplete);
- filtra per tipi di mercato esplicitamente autorizzati, escludendo 31 altre righe della query corrente;
- trattiene sede ripetuta su più giorni, stesso nome/luogo su categorie diverse, traslochi temporanei e collisioni tra fonti;
- permette di superare la scheda testuale generica di una città senza indirizzo, **solo quando** il dataset contiene almeno dieci indirizzi fisici distinti e il vecchio calendario non è identificabile;
- separa il limite di ammissione di un'inventario comunale storico (fino a 730 giorni) dal limite per previsioni di apertura (365 giorni). Bologna è del 2 aprile 2025: niente appuntamenti futuri inferiti.

Restano necessari controlli per API paginate, conflitti trasversali e dati multi-giorno; non affermare che tutte le fonti candidate siano già importabili.


## Fonti ufficiali non raggiungibili: conservazione controllata

Un errore di rete non dimostra che un mercato sia chiuso. Il controllo Autopilot può conservare i dati di una fonte temporaneamente irraggiungibile senza bloccare le nuove sedi approvate da altri editori, **soltanto se**:

- l'importer appartiene alla lista ufficiale, lo stato è `unavailable` e contiene zero righe nuove;
- tutti i precedenti ID ufficiali della fonte rimangono nel catalogo; nessun ID dello stesso prefisso viene creato;
- nome, città, provincia, indirizzo, GPS, fonte, stato e verifica delle sue schede restano identici;
- restano validi gli altri controlli su date, conferme, prova dell'origine, indice statico e autorizzazione DEV.

Lo stato della fonte resta visibile come `unavailable` nel report, non come fonte verificata nel giorno corrente. Un ID scomparso o un campo fondamentale cambiato blocca il rilascio. Le previsioni generate da regole storiche già approvate sono consentite solo se marcate come previste, mai confermate.

Test reale (13 ottobre 2026): Milano e Lombardia non raggiungibili dal PC Windows; tutti gli **85 + 1.127 ID ufficiali** sono stati preservati. Il lotto Bologna di **5 schede non confermate** supera il confronto indipendente sulla candidatura da **13.789 schede**, senza deletions o GPS inventato. La pubblicazione effettiva nel sito DEV rimane soggetta ai job GitHub e ai relativi test del browser.
