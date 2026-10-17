# Scoperta autonoma dei mercatini e altri eventi (solo DEV)

Inizio: 18 ottobre 2026. Il sistema trova nuove segnalazioni, ma **non**
importa né conferma eventi da solo. I dati del catalogo di produzione
rimangono invariati.

## Cosa abbiamo scoperto nel codice precedente

backend/scraper_eventiesagre.py conosce già regioni, sezioni e URL
delle schede, ma NON è eseguito dall'Autopilot. Può seguire redirect
e fare scraping di testo da pagine cambiate o vecchie. L'indice
EventiESagre Toscana/Antiquariato contiene ancora eventi del 2022-2023
accanto agli annunci 2026: non possiamo usare una frase come
"ogni domenica" per dichiarare aperto oggi il mercato.

## Fonti studiate con dati reali

**Firenze FeelFlorence (fonte ufficiale)**

- Dataset: https://www.dati.toscana.it/dataset/eventi-a-firenze
- GeoJSON: https://datigis.comune.fi.it/resources/open-data/eventi-a-firenze/feelflorence_eventi.geojson
- Licenza dichiarata CC BY 4.0. La pagina dichiara aggiornamento quotidiano.
- Struttura vista il 17/10: FeatureCollection, totalFeatures, features
  con id e properties: titolo, comuni, data_inizio, data_fine,
  feelflorence_link, appuntamenti.
- Nella risposta live: 115 eventi, 1 titolo chiaramente riferito a
  un mercato (Mercato di Natale in Piazza Santa Croce).
- Le informazioni personali, le descrizioni e i geopoint non vengono
  salvati da questo connettore. Nessuna data viene confermata.

**Bologna Agenda Cultura (fonte ufficiale)**

- Dataset: https://opendata.comune.bologna.it/explore/dataset/eventi-bologna-agenda-cultura/
- Endpoint: https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/eventi-bologna-agenda-cultura/records?limit=3
- Struttura: total_count e results; ogni riga ha id, title, start,
  end, address, url e categorie. Il dataset intero comprende molti
  anni di archivio, anche eventi passati.
- Il job chiede solo candidati attuali/futuri con titoli a tema
  mercato, fiera, antiquariato e sagra. Massimo 150 righe e tre pagine.
- Un primo filtro online ha restituito la Fiera delle Idee (non un
  mercato, da escludere). Evitare falsi positivi come Mercato Sonato.
- Per il riuso delle singole righe oltre agli indizi di ricerca,
  riconfermare i termini di licenza specifici del dataset.

**EventiESagre.it (solo link di ricerca)**

- Indice: https://www.eventiesagre.it/cerca/Mercatini/Antiquariato/mesi/Toscana/prov/cit/rilib
- Robots: https://www.eventiesagre.it/robots.txt
- Termini: https://www.eventiesagre.it/CONDIZIONI_GENERALI_SERVIZIO.pdf
- Non abbiamo il permesso di ripubblicarne testi e descrizioni.
- Il nuovo parser legge unicamente link e ID numerici all'interno
  della sezione principale Elenco Eventi, scartando gli annunci
  in evidenza e senza seguire i link alle schede.
- Massimo due pagine di indici ogni giorno; sezioni e regioni
  ruotano. Prima di accedere viene interrogato robots.txt.
- In report compare solo l'URL: nessun nome evento, orario, luogo,
  descrizione, foto, contatto, promessa di apertura o fatto dedotto.

## Come diventa automatico

1. Una fonte viene prima classificata e collegata a un contratto
   per l'intero sito/dataset, mai per il singolo evento.
2. La pipeline legge l'endpoint consentito, limita byte e richieste,
   controlla DNS/HTTPS e rifiuta i redirect.
3. Un parser per tipo di fonte estrae solo i campi esplicitamente
   consentiti. Le date, le identità e la struttura vengono validate.
4. Il sistema cerca soltanto indizi di corrispondenza con il catalogo.
   Un nome simile nella stessa città non produce fusioni o modifiche.
5. Un report sul branch DEV mostra segnali, cambiamenti e blocchi.
   Scomparse ed errori di rete NON vengono presentati come chiusure.
6. La pianificazione GitHub Actions esegue il processo senza il PC.
   Se in futuro una nuova fonte supera revisione diritti e QA, si
   potrà usare un flusso distinto per aggiornare campi affidabili.

## File

- backend/event_lead_discovery.py — downloader e parser generici
  per GeoJSON, Opendatasoft e HTML links-only; matching solo review.
- backend/data/event-lead-source-contracts.json — approvazione
  limitata alla ricerca delle tre strutture e politica dei permessi.
- backend/tests/test_event_lead_discovery.py — casi reali in fixture,
  data source drift, URL malevoli, robots denied, dedup e false dates.
- reports/automation/event-leads.json e EVENT_LEADS.md — report
  prodotti nel ciclo schedulato, mai contenuto grezzo.

Per eseguire manualmente dalla root DEV:

    python -m unittest discover -s backend/tests -v

    python backend/event_lead_discovery.py --offline \
      --out /tmp/leads.json --report /tmp/EVENT_LEADS.md

    python backend/event_lead_discovery.py \
      --out /tmp/leads.json --report /tmp/EVENT_LEADS.md

## Crescita futura delle fonti

Per ogni nuovo sito verificare: titolarità, diritti, robots,
struttura dei listati, API/RSS/JSON-LD, identificatore stabile,
significato dei campi, calendario storico contro date correnti.
Creare un contratto a livello di publisher e un test con esempi.
Solo dopo si abilita il ciclo limitato della fonte. I diritti
di riuso e le prove sulle date continuano a essere necessari
prima di aggiornare qualsiasi mercato nel catalogo.
