# Bologna: dalla verifica manuale all'automazione

## Prove osservate prima della scrittura dell'importatore

Fonte pubblica: https://opendata.comune.bologna.it/explore/dataset/mercati-e-fiere/

Data della ricognizione: 12 ottobre 2026. Consultazioni in sola lettura.

API usate per la verifica:
- Metadati: https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/mercati-e-fiere
- Record con identità originale: https://opendata.comune.bologna.it/api/records/1.0/search/?dataset=mercati-e-fiere&rows=2
- Raggruppamento di tutti i tipi: https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/mercati-e-fiere/records?select=tipologia%2Ctipologia_mercato%2Ccount%28%2A%29%20as%20n&group_by=tipologia%2Ctipologia_mercato&limit=100

| Categoria ufficiale | Righe osservate | Prima decisione |
|---|---:|---|
| Mercato, periodico | 19 | Sede di mercato |
| Mercato, rionale | 9 | Sede di mercato |
| Mercato produttori agricoli | 20 | Sede di mercato |
| Fiera, periodico | 31 | Esclusa da questo importatore |
| Mercato, a turno giornaliero | 59 | Posteggio, non mercato intero |
| Mercato, giornaliero periferico | 4 | Posteggio, non mercato intero |
| Mercato, mercato diffuso A | 27 | Posteggio, non mercato intero |
| Mercato, mercato diffuso B | 43 | Posteggio, non mercato intero |
| Mercato, stagionale | 37 | Richiede separata valutazione |

Totale 249: 48 mercati pertinenti e 201 righe di altra natura.

Casi letti nell'API reale: La Piazzola appare sia venerdì sia sabato, senza essere una replica errata; Via Sigonio ha una settimana di attività, ma il programma non è verificato per ogni edizione; la Fiera di San Luca segue un calendario mobile e non va trasformata in mercato settimanale. Il Mercato Antiquario e il mercato Vintage hanno eccezioni mensili e stagionali: nessuna data inventata.

L'API v1 restituisce recordid ufficiale di 40 caratteri esadecimali. L'API v2.1 di ricerca non lo include. I record sono identificati tramite recordid, non con hash inventati dei nomi.

## Età effettiva dei dati: NON confondere i metadati

- Ultima elaborazione dati: 2 aprile 2025.
- Campo di modifica dichiarato: 31 dicembre 2025.
- Ultima elaborazione metadati: 30 settembre 2026.
- Flag del publisher: modified_updates_on_data_change=false.
- Licenza dichiarata: CC BY 4.0, con attribuzione.

Al 12 ottobre 2026, l'ultima elaborazione dei dati ha oltre 540 giorni. Nessun nuovo appuntamento del 2026 viene automaticamente confermato o previsto dal solo dataset.

## Script ripetibili e verifiche

- backend/source_bologna.py: download limitato a endpoint ufficiali, controlli di ID, cardinalità e metadati prima/dopo.
- backend/tests/test_source_bologna.py: test golden con 249 righe e 48 mercati, due giorni distinti di La Piazzola, calendari complessi esclusi, fonte parziale, licenza cambiata, coordinate incongruenti.
- backend/lombardia_overlap.py: riusa la stessa logica conservativa Comune/indirizzo/giorno anche per Emilia-Romagna, senza cancellare schede esistenti.
- backend/autopilot.py: fonte registrata dietro abilitazione esplicita, genera bologna-overlaps.json e BOLOGNA_OVERLAPS.md.
- .github/workflows/bologna-integration-audit.yml: usa il feed reale, produce il candidato DEV in una cartella effimera, esegue regressioni, QA di origine/ID e browser mobile. Non pubblica dati.
- backend/source_evidence.py e backend/source_change_detector.py: distinguono correzioni della metodologia dalle vere revisioni dell'ente.

Per ripetere la validazione della logica: python -m unittest discover -s backend/tests -v

Per ripetere la prova di rete autorizzata e completa: https://github.com/tommyv-spec/mercati-italia/actions/workflows/bologna-integration-audit.yml

Criterio di attivazione automatica: feed reale riuscito, identità preservate, doppioni in quarantena, nessuna data futura non provata, attribuzione visibile e test mobile riuscito. Dati vecchi restano etichettati come tali; la produzione non viene toccata.

## Secondo contratto generico DEV — verifica del 13 ottobre 2026

- Licenza confermata sul portale del Comune e nel catalogo nazionale dati.gov.it: CC BY 4.0 con attribuzione.
- API v1 usa il suo ID stabile `recordid` (40 hex, identità `bo-open-...`), compatibile con l'importatore storico. Controllo sui dati veri: **48/48 ID identici**.
- Ricerca ufficiale selettiva, richiesta limitata e senza redirect; snapshot 31.925 byte, SHA-256 `603b6ee6febc5646e28806be59cbd1f025018e918adbccf6927fce453f85ecfa`.
- Il risultato comprende 79 righe. 48 sono un mercato rionale, periodico o dei produttori agricoli; 31 sono scartate perché non appartengono alle categorie ammesse. Le 48 righe non corrispondono necessariamente a 48 sedi uniche.
- Controllo completo su 13.784 schede: **39 candidate** con identità distinta, indirizzo e confronto per fonte; **9 righe trattenute** per quattro record a sede/giovedì-venerdì ripetuta, due con stesso nome/luogo ma natura diversa, un trasferimento temporaneo, due possibili sovrapposizioni del catalogo.
- Primo lotto: 5 schede DEV, 34 in coda con hash degli ID residui. Prova di più cicli: 5,5,5,5,5,5,5,4 e 0; nessun ID perso, duplicato o verificato automaticamente.
- Non sovrascrivere `source_dataset_date=2025-04-02` con `metadata_processed=2026-09-30`. Le nuove schede non hanno date confermate, date previste o GPS derivato dall'API. Gli orari 2025, se semplici, restano sempre indicati come da verificare.
- I vecchi record restano intatti. La sorgente già disponibile tramite `backend/source_bologna.py` è tenuta come comparatore indipendente; non attivare anche il vecchio importatore nello stesso ciclo, per evitare doppio inserimento.
- La generalizzazione è per il **formato Opendatasoft v1**, non uno script per mercato o singolo Comune. Il filtro di tipo e la regola sulle schede cittadine generiche sono dichiarati nel contratto e soggetti a checksum.
- `main`, produzione, Cloudflare Worker, KV/D1 e conferme individuali non sono coinvolti.
