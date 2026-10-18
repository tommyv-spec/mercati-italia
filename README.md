# Mercati d'Italia

## Procedura dati aggiornati

[Metodo ripetibile, automatismi giornalieri, verifiche e checkpoint](docs/RUNBOOK_DATA_FRESHNESS.md).
Gli aggiornamenti automatici sono in DEV e non equivalgono a eventi confermati.


React 18 + Vite 6 — catalogo nazionale di mercati rionali, antiquariato, vintage, usato e artigianato.

## Architettura e costi Cloudflare

**Il sito pubblico è statico.** Non deve eseguire Cloudflare Workers/Pages Functions, KV, D1 o chiamate Firestore per mostrare i mercati. Cloudflare Pages serve i normali asset statici senza addebiti per richiesta secondo la documentazione attuale (questo non annulla eventuali costi del piano, del dominio o di altri Workers configurati nel dashboard).

- `public/data/v1/manifest.json`: indice delle versioni, contatori e qualità del dataset.
- `public/data/v1/index-<hash>.json`: riepilogo leggero dei mercati, per ricerca/filtri/mappa. Una sola lettura all'avvio.
- `public/data/v1/regions/*.json`: schede complete, scaricate *solo quando si apre una scheda*, con cache lunga e hash immutabile.
- `public/_routes.json`: le route di pagina, asset e dati statici non invocano Pages Functions.
- `public/_headers`: manifest aggiornabile, shard immutabili, alcune intestazioni di sicurezza.
- Preferiti: `localStorage` sul dispositivo. Non c'è nessun login necessario per la consultazione.

Documentazione ufficiale Cloudflare:
- https://developers.cloudflare.com/pages/functions/pricing/
- https://developers.cloudflare.com/pages/functions/routing/

**Nota importante:** il repository non mostra le impostazioni e le fatture dell'account Cloudflare. Controllare eventuali vecchie route Worker, impostazioni `run_worker_first`, Pages Functions e altri progetti dalla dashboard.

## Situazione del catalogo (snapshot del branch di revisione — 11 ottobre 2026)

Il primo export contiene **13.099 record candidati**, distribuiti su **20 regioni italiane**. Non significa che tutti siano mercati verificati. **8.202** hanno almeno una prossima data nei dati ricevuti o previsti; **nessun record possiede ancora una verifica umana documentata**. Le coordinate possono essere approssimative: non trattarle come ingressi precisi finché non confermate.

Le fonti esistenti provengono dal vecchio Firestore. Si aggiungono importazioni comunali ufficiali, attualmente:
- **Milano:** 85 mercati settimanali, coordinate WGS84, dataset maggio 2024, licenza CC BY 4.0. Date ricorrenti *previste*, da riconfermare.
- **Firenze:** 4 mercati da FeelFlorence, coordinate comunali, dati modificati a marzo 2023, licenza CC BY 4.0. Nessuna data futura inventata.

L'importazione esclude automaticamente categorie estranee come sagre e carnevali. I mercati generici senza evidenze chiare sono scartati dal catalogo pubblico. Resta necessaria un'ulteriore verifica degli eventi esistenti, degli orari e delle sovrapposizioni.

## Avvio e test

```bash
npm ci
npm run dev
# Apri http://localhost:5173
```

La cartella `public/data/v1` è la copia statica di sviluppo (non occorre Firebase). Per la build:

```bash
python -m unittest discover -s backend/tests -v
python backend/validate_static.py --manifest public/data/v1/manifest.json
npm run build
npm run preview
```

### Aggiornare i dati

Il workflow `.github/workflows/refresh-data.yml` raccoglie le fonti comunali **una volta alla settimana**, unisce al catalogo precedente, verifica gli invarianti e committa solo le differenze. Ogni push a `main` può poi produrre una nuova build statica di Pages. Nessuna visita di utenti invoca gli scraper.

Per aggiornare a mano:

```bash
python backend/source_milano.py --output /tmp/mercati_milano.json
python backend/source_firenze.py --output /tmp/mercati_firenze.json
python backend/merge_catalog.py \
  --new /tmp/mercati_milano.json \
  --new /tmp/mercati_firenze.json \
  --out /tmp/mercati_uniti.json
python backend/export_static.py --input /tmp/mercati_uniti.json \
  --min-count 12000 --max-drop-ratio 0.05
python backend/validate_static.py --manifest public/data/v1/manifest.json
```

La firma dei contenuti e il controllo della riduzione impediscono l'export accidentalmente incompleto. **Non sostituire** il catalogo corrente con i pochi mercati di un solo Comune.

## Firestore esistente e sicurezza

Il frontend non importa più Firebase e non scrive automaticamente record demo nel database. La vecchia istanza Firestore può essere mantenuta come storico per la pipeline amministrativa, ma non è necessaria alla lettura pubblica.

`firestore.rules` nel repository contiene regole più sicure che impediscono le scritture pubbliche. **Il solo commit NON aggiorna le regole attive in Firebase:** vanno pubblicate separatamente da chi ha le credenziali del progetto.

## Rilascio

1. Attendere il verde di `.github/workflows/quality.yml` su questo branch/PR.
2. Verificare navigazione, filtri, mappe e schede su mobile e il dataset con il validatore.
3. Controllare le regole attive su Firebase e applicare le regole versionate.
4. Controllare su Cloudflare che il dominio non instradi le visite a Workers/Functions (il repository non può confermare la configurazione dell'account).
5. Solo allora approvare e unire la pull request; collegare il progetto a Cloudflare Pages come Vite, build `npm run build`, directory `dist`.

Vedi `docs/PROGRESS.md` per checkpoint verificabili, rischi e passaggi ancora aperti.

Licenza codice: MIT. Le fonti e i dati di terzi mantengono le rispettive condizioni di licenza e attribuzione.
