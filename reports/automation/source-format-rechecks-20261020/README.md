# Riconfronto offline del registro dei formati

Questa è una **proposta condizionata**, non una modifica del registro operativo. La base di codice è `1f0c624cbb5c96019458d119abc9f30b47663014`; il catalogo è quello pubblicato prima di LIVE7, con 13.856 schede e manifest SHA-256 `13382293ef0b1f7c2d741f96395e1a5642b5b28a892c21ee3b401be6832dd625`. Il catalogo, il ledger operativo e i rami remoti non sono stati modificati. Non è stata fatta alcuna richiesta HTTP.

Il nuovo indice schema 6 e il successivo candidato LIVE7 richiedono un ultimo confronto prima dell'eventuale applicazione. **Una nuova impronta del codice o del catalogo non costituisce da sola una prova per aggiornare il ledger.**

## Risultato dimostrato

Le 83 riaperture primarie non significano che siano scomparse le letture precedenti. Il controllo confronta l'impronta di interi moduli condivisi e l'impronta dell'intera scheda campione; anche una nuova prova amministrativa o la rimozione di una data passata cambia quest'ultima.

| Gruppo | Prova eseguita | Limite della proposta |
| --- | --- | --- |
| 53 formati con solo `publisher_refresh.py` cambiato | Confronto differenziale contro il modulo registrato: 77 risorse pertinenti restano identiche anche con un report operativo dei nuovi lettori | È compatibilità di instradamento. Sei formati hanno ancora la fonte o la mappatura incompleta: i loro hash di confronto parser restano invariati |
| 8 formati ufficiali primari e 25 ausiliari | Parser sorgente registrati identici; confronto di normalizzazione, ricevute ed export sull'intero catalogo | Un formato ausiliario senza campione valido resta aperto; nessuna nuova lettura delle fonti ufficiali |
| 4 formati Happings primari e 1 ausiliario | 13 pagine provinciali, 9 dettagli e 2 destinazioni di vecchi URL, con originali e metadati conservati | I reindirizzamenti effettivi restano distinti dal canonical; le prove riguardano i campioni |
| 2 formati EES | 10 HTML `Eventi_Enogastronomici` e 1 `Eventi_Feste`, parser, raccordo alle identità ed export | Gli altri 14 formati EES non hanno un corpo pertinente in questo corpus e restano aperti |
| 1 formato Cose di Casa | 16 HTML originali, verificatore delle modifiche ed export | La lettura di una pagina storica non la rende attuale |
| 27 formati Citynews già riconfrontati | Nuovo replay di controllo dei 27 originali; gli hash del reader erano già allineati | Nessuna riconferma di PadovaToday, il cui dettaglio non è stato acquisito con successo |

L'eccezione nel primo gruppo è stata individuata confrontando realmente gli output: PadovaToday passa da `source_layout_needed` a lettore configurato con stato `not_selected`. Il catalogo non contiene una nuova prova di lettura. Il tentativo del 19 ottobre aveva restituito HTTP 503; quello del 20 ottobre era terminato durante l'acquisizione di robots. Non si deduce nulla sui campi della pagina da questi fallimenti.

## Confronto del codice condiviso

Il file `shared-replay.json` registra:

- 13.856 record confrontati tra il vecchio e il nuovo normalizzatore;
- unica differenza: conservazione di 220 prove `riconciliazione_provincia`, tutte validate contro il riferimento ISTAT fissato;
- tutti gli altri campi normalizzati identici;
- 2.264 ricevute con risultato identico nel validatore precedente e in quello attuale;
- esportazione e rilettura con tutte le righe esattamente uguali alla base;
- confronto del report di copertura sia senza un report di acquisizione sia con il report operativo del replay dei checkpoint v2.

Questo confronto tiene ferme le dipendenze correnti e sostituisce solamente i moduli condivisi cambiati con la versione il cui hash è registrato. Non è presentato come riesecuzione integrale di un vecchio checkout.

Sono passati 54 test mirati di audit, copertura e ricevute:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend:backend/tests python -m unittest test_source_format_audit test_existing_source_refresh_coverage test_field_evidence -q
```

## Replay dei byte originali

`capture-replays.json` contiene 78 corpi HTTP con URL richiesto, destinazione, hash, dimensione e data originale, non nuovi timestamp di acquisizione. I sei candidati di prova sono stati scritti soltanto in `/tmp`, ciascuno con tutti i 13.856 ID conservati.

| Famiglia | Corpi | Esito del raccordo |
| --- | ---: | --- |
| EES | 11 | 2 evidenze editoriali migliorate, 8 già osservate, 2 esiti trattenuti; 10 identità con prova controllata all'export |
| Cose di Casa | 16 | 14 esiti osservati, 3 trattenuti; nessuna nuova modifica |
| Citynews | 27 | 11 aggiunte di evidenza storica, 19 esiti trattenuti |
| Happings provinciale | 13 | Nessun nuovo indirizzo; 581 modifiche alle schede, comprensive di metadati nelle prove ricostruite |
| Happings vecchio URL comunale | 2 | 4 redirect HTTP documentati; provincia, intestazione e Comune/giorno provati indipendentemente; 3 cambi di campo nel confronto delle due pagine provinciali finali |
| Happings dettaglio | 9 | 1 corrispondenza, 7 casi trattenuti e 1 candidatura non ammessa; nessun ID nuovo |

Gli esiti possono essere più dei corpi perché una pagina può essere confrontata con più schede. Le modifiche dei candidati di prova non sono pubblicazioni. Il replay dei vecchi URL conserva il percorso `.html → / → pagina provinciale`: la risposta HTTP 200 finale viene fornita al lettore provinciale soltanto dopo il controllo di appartenenza della pagina; il requested URL originario non viene riscritto nella prova della catena.

## I 15 snapshot di catalogo cambiati

Sono state ritrovate **tutte e 15 le fotografie precedenti con impronta identica** a quella registrata. `storage-comparison.json` riporta manifest precedente, vecchia e nuova impronta del campione, ID cambiati, conteggi dei campi e motivo della decisione. Il dettaglio completo delle impronte prima/dopo per campo è conservato in `/tmp/source-format-rechecks-20261020/storage-comparison.json`, con hash riportato nel documento compatto.

Nove confronti hanno una prova circoscritta sufficiente:

- **Milanopocket e Sagreumbre:** solo provincia e prova amministrativa, con validazione indipendente sul riferimento ISTAT già fissato;
- **vecchio Happings `ad-...`, EES Filiera Corta e indice RiminiToday:** esclusivamente rimozione di date ormai passate, senza aggiunte;
- **vecchi URL comunali Happings e due formati Roma XIII:** tutte le schede campione sono ricostruite esattamente da dati precedenti, regole di ricorrenza e normalizzazione attuali;
- **EES Enogastronomici / November Porc:** sola evidenza editoriale, verificata contro il corpo originale salvato e contro il verificatore finale, mantenendo l'edizione storica.

Sei snapshot **non sono proposti per la riconferma**, pur avendo una differenza completa e misurata:

| Formato campione | Differenze da raccordare specificamente |
| --- | --- |
| Lombardia, `/d/68zx-njaw` | Identità sorgente, ricevute, date di dataset, ricorrenze e limiti di calendario |
| Milano, dataset mercati settimanali | Ricevute, metadati delle fonti e proiezioni |
| Bologna, dataset mercati e fiere | 9 orari e ricevute dei campi |
| Firenze, pagine FeelFlorence | Testo completo di un orario con chiusure, più ricevute e date sorgente |
| Corciano, pagina documento | Ricevute, metadati sorgente e proiezioni |
| Happings, vecchio indice Milano | Nuovi campi/riscontri da fonti sovrapposte, oltre alle province corrette |

Le prove e i dati di quei passaggi possono già essere conservati negli artefatti live; questa revisione non sostituisce il loro raccordo specifico con una semplice uguaglianza di ID o con la validità sintattica delle ricevute.

## Proposta di ledger e controllo successivo

`ledger-proposal.json` contiene aggiornamenti mirati con impronta dell'entry precedente, impronta del ledger e del manifest attesi. Conserva integralmente ogni campione, ogni data/hash di lettura e tutti gli stati dei TODO. Aggiunge una storia del confronto precedente prima di proporre nuovi hash. Il ledger operativo non è stato toccato.

Sono proposti nuovi hash per **62 confronti parser primari e 25 ausiliari**, più i 9 snapshot dimostrati. La simulazione sulla sola base `1f0c624` lascia **27 formati primari da riconfrontare**: 14 categorie EES, PadovaToday, 6 formati con lettura/mappatura ancora incompleta e i 6 snapshot con fatti/ricevute cambiati. Le letture primarie documentate restano **104**, i formati non esaminati restano **5**, i TODO restano **36 aperti e 23 completati**. Nessuna percentuale di completezza dei mercati viene dedotta da questi numeri.

Per il successivo codice e catalogo, rieseguire il confronto condiviso in una cartella di uscita nuova:

```sh
PYTHONDONTWRITEBYTECODE=1 python reports/automation/source-format-rechecks-20261020/replay.py shared --repo /percorso/del/codice/schema6 --manifest /percorso/LIVE7/candidate/public/data/v1/manifest.json --output /tmp/source-format-rechecks-schema6-live7
```

Lo stesso script accetta `raw` per ripetere il corpus di 78 originali. I nuovi campioni contenuti nell'artefatto LIVE7 dovranno essere aggiunti al confronto con le proprie prove di trasporto: non sono implicitamente coperti dal corpus precedente. Gli script `storage_check.py` e `package_report.py` documentano la costruzione di questa proposta, con percorsi e baseline espliciti; non sono un applicatore automatico del ledger.

**Prima di applicare qualsiasi aggiornamento:** verificare che il nuovo indice schema 6 cambi soltanto le colonne intenzionali, che i regionali mantengano i campi e le prove, e che nessun nuovo hash di storage venga promosso senza spiegare le differenze rispetto alla fotografia già confrontata.
