# Happings — discovery completa dal sito (DEV)

## Fonte e metodo

La raccolta comincia dal sito pubblico `https://www.happings.com/it/`, non
da nomi inventati o da un elenco fisso di mercati. Dal menu, dagli archivi,
dalla sitemap in `robots.txt` e dai collegamenti osservati ricostruisce le
famiglie editoriali pubblicate. Il sito usa WordPress, Yoast e una
tassonomia eventi con archivio `/it/categoria-evento/mercati/`.

La documentazione di WordPress spiega come rilevare i tipi e le tassonomie
REST e come scorrere pagine di risultati (`per_page`, `page`,
`X-WP-TotalPages`). La documentazione Yoast spiega che le sitemap sono
divise per tipo, possono essere paginate e comprendono URL canonici, ma
non necessariamente contenuti `noindex`.

Fonti tecniche:
- https://developer.wordpress.org/rest-api/using-the-rest-api/discovery/
- https://developer.wordpress.org/rest-api/using-the-rest-api/pagination/
- https://developer.wordpress.org/rest-api/extending-the-rest-api/adding-rest-api-support-for-custom-content-types/
- https://developer.yoast.com/features/xml-sitemaps/functional-specification/

Happings espone `wp-json/wp/v2/posts` e tassonomie evento ma non la
collezione pubblica `wp/v2/happings_event` (HTTP 404 il 21 ottobre 2026).
Quindi la REST API **non** sostituisce l'inventario dei dettagli `/it/happing/`.

## Inventario live verificato il 21 ottobre 2026

Il replay HTTPS legge direttamente la home, `robots.txt`, l'indice sitemap,
le 13 sitemap degli eventi, le due sitemap degli articoli, tutte le 26 pagine
dell'archivio Mercati seguendo i link `next` effettivamente osservati.
Pausa di almeno tre secondi fra richieste; nessuna nuova scheda creata
durante questo audit.

| Unità | URL / risultato |
| --- | ---: |
| Sitemap elencate nell'indice | 22 |
| Sitemap eventi lette | 13 |
| URL italiani `/it/happing/` elencati dalle sitemap | 2.208 |
| Sitemap articoli lette | 2 |
| URL post / guide nelle sitemap articoli | 1.706 |
| URL contenenti `mercati-settimanali-` | 253 |
| URL di pagine provinciali riconosciute con ISTAT | 106 |
| Pagine di archivio Mercati percorse | 26 |
| URL di scheda nel solo archivio Mercati | 260 |
| URL archivio Mercati assenti dalle sitemap eventi | 0 |

I 2.208 URL sono di *tutti i tipi di evento*, non sono 2.208 mercati.
Una pagina provinciale rappresenta molti mercati distinti. Un URL trovato
non prova né che un evento si svolga davvero né che sia completo.

Il rapporto osservato è
`reports/automation/happings-home-map-audit-2026-10-21.json`.
Contiene URL e SHA-256 delle risposte HTTP, conteggi per pagina e riscontri
tra indici. Non contiene HTML copiato né conferme individuali di aperture.

## Come funziona l'autopilota

### Ramo A — elenchi settimanali

`backend/happings_province_directory.py`:

1. Scarica la **home** reale usando solo HTTPS, host esatto, robots,
   MIME e URL non rediretto. Rileva i link effettivi a Mercati, città e Italia.
2. Segue la sitemap dichiarata nel `robots.txt`, non un elenco statico
   di province. Dall'indice rileva ogni `post-sitemap*.xml`.
3. Identifica gli elenchi settimanali nella famiglia di URL pubblicata.
   Ammette **solo** pagine la cui provincia coincide con un unico ambito
   ISTAT italiano nel riferimento versionato. Esclude siti esteri anche
   quando la pagina è sotto `/it/`.
4. Gestisce anche gli slug WordPress esadecimali realmente osservati
   (L'Aquila, Forlì-Cesena) e gli alias editoriali verificabili
   (Ascoli, Pesaro-Urbino, Caltanissetta).
5. Passa alla rotazione provinciale **anche** le pagine non ancora collegate
   a vecchie schede. Il parser già esistente confronta tutte le righe, sede,
   Comune, giorno, ambiti di calendario e conflitti. Non inventa ore.
6. La prima lettura e i retry usano i gate già presenti. Il report
   `happings-enrichment.json` separa richieste directory, legacy e liste.

La scoperta usa fino a 4 richieste e 60 secondi **dal medesimo budget
provinciale esistente di 16 pagine per ciclo**. Nessun servizio o job
aggiuntivo è introdotto. Se vengono aggiunte altre sitemap degli articoli,
il crawler le ruota senza saltare le restrizioni del publisher.

### Ramo B — eventi e mercatini a data specifica

`backend/happings_detail_discovery.py`:

1. Registra la home come **prima pagina di navigazione** quando la policy
   DEV attiva `home_navigation`.
2. Trova gli archivi Mercati attraverso i link HTML osservati e segue
   pagine `/page/N/` soltanto quando sono collegate dall'archivio.
3. Confronta la frontiera dell'archivio con i dettagli trovati nelle
   tredici sitemap evento. La frontiera persistente tiene tentativi,
   timestamp, hash dei byte e URL di origine.
4. Le pagine evento lette vengono filtrate dal classificatore esistente
   per evitare concerti dentro mercatini e altri falsi mercati. Le date
   esatte e gli orari sono conservati solo se presenti sul dettaglio.
5. Matching forte con i mercati già salvati; possibili duplicati, conflitti
   e dati non supportati restano sospesi anziché produrre nuovi ID a caso.

Il budget resta quello esistente: fino a 128 richieste/420 secondi per ciclo,
con massimo tre richieste di navigazione (home e archivi) e due sitemap
in quel budget. La coda delle schede dettagliate continua ogni giorno
fino alla prima copertura; poi riparte dalle pagine dovute.

### Completezza: cosa significa davvero

I contatori devono distinguere **URL noti**, **pagine lette con successo**,
**righe mercato estratte**, **righe con identità ricondotta al catalogo**,
**campi salvati con ricevuta**, **orari precisi** e **freschezza del contenuto**.
Avere tutte le sitemap non prova di aver estratto tutti i dati.

Un dettaglio assente dalle sitemap può essere scoperto dall'archivio.
Una riga provinciale `la mattina` non diventa `08:00–13:00`.
Una provincia priva di vecchie schede va comunque letta e analizzata:
la sua eventuale ammissione nel catalogo richiede ulteriori regole di
identità e collisione. L'obiettivo è una raccolta ripetibile, senza
intervento manuale per ogni singolo mercato.

## Test

```bash
PYTHONPATH=backend python -m unittest discover -s backend/tests -p 'test_happings_*.py'
```

Includono sitemap multiple, archivi paginati, link homepage, alias ISTAT,
filtri geografici, limiti, redirect, parser, checkpoint, riavvio e integrazione
con la pubblicazione. Il test di codice **non** certifica da solo il
completamento del backfill in DEV. Le pubblicazioni DEV mantengono i gate.
