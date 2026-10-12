# Qualità dei mercati: verifica manuale → script → gate automatici

**Conoscenza verificata il 12 ottobre 2026.**

Questo documento registra un audit reale del catalogo prima della correzione e
descrive la strategia conservativa applicata negli script. Non trasforma
fonti di terze parti in prove di apertura dei singoli mercati.

## Osservazioni fatte sui record pubblicati

- Lombardia: due schede «Mercato settimanale di Albizzate» con lo stesso
  Piazzale Sefro e il martedì; il database ufficiale MERCap 100001 riporta
  piazzale, martedì e orario 08:00–13:00.
- Lombardia: `citta=\"Mercatino delle Curiosità\"` per una scheda che
  titola «Cernobbio, Mercatino delle Curiosità». È un nome evento, non Comune.
- Lazio: una scheda ha `citta=\"Fiera del Disco\"`, un'altra contiene
  frammenti concatenati come «... in provincia... Mercato settimanale a ...».
- Toscana: alcuni `citta` contengono frammenti di pagine testuali su fiere
  invece di una località.
- «Piazza Brembana» e «Piazza al Serchio» sono località italiane: non
  contrassegnarle erroneamente soltanto perché iniziano con «Piazza».
- Diverse schede con `date=[]` continuavano a riportare
  `date_quality=prevista`: il visitatore non ha una data futura da consultare.

## Primo ciclo completo di correzione, senza pubblicazione

[Audit GitHub Actions 38235823171](https://github.com/tommyv-spec/mercati-italia/actions/runs/38235823171)

- Schede originali: **13.779**.
- Etichette previste/confermate senza date future prima della correzione: **1.455**.
- Etichette senza date future dopo la correzione: **0**.
- Comuni/località sospetti identificati nel nuovo audit: **52**.
- Gruppi settimanali potenzialmente ripetuti (Comune + indirizzo + giorno): **755**.
- ID eliminati: **0**. Indirizzi, coordinate, fonti, città e date di
  verifica preesistenti alterati: **0**.
- Test Python, sicurezza Node e browser mobile: **tutti superati**.

Le 755 corrispondenze **NON equivalgono a 755 duplicati accertati**:
mercati diversi possono svolgersi nella stessa piazza nello stesso giorno.
Le 52 località sono candidati a revisione, non località automaticamente cambiate.

## Script ripetibili

- `backend/export_static.py`: demuove `date_quality` a `sconosciuta`
  quando non esiste nessuna `date` futura. Non altera le verifiche storiche
  documentate, né inventa edizioni.
- `backend/catalog_quality_report.py`: audit del catalogo reale:
  orari, indirizzi, coordinate, date, fonti, località anomale, possibili
  sovrapposizioni settimanali; nessuna cancellazione o scrittura su mercati.
- `backend/tests/test_catalog_quality_report.py` e
  `backend/tests/test_static_pipeline.py`: test su casi osservati
  e regressioni, comprese località italiane che sembrano indirizzi.
- `.github/workflows/catalog-integrity-audit.yml`: dry-run completo
  offline e mobile. Conserva i report solo come artefatti a scadenza.
- `.github/workflows/market-autopilot.yml`: esegue lo stesso audit ad
  ogni ciclo giornaliero, prima di pubblicare DEV; conserva JSON e report
  versionati in `reports/automation`.

### Riproduzione manuale

Da root del repository:

```bash
python -m unittest discover -s backend/tests -v
python backend/catalog_quality_report.py \
  --manifest public/data/v1/manifest.json \
  --previous reports/automation/catalog-quality.json \
  --out /tmp/catalog-quality.json --report /tmp/CATALOG_QUALITY.md
```

I report contengono soltanto conteggi e campioni limitati di ID pubblici.
Non scaricano interi siti né chiamano Cloudflare Worker/KV/D1 per le
consultazioni. Le aree da verificare restano segnalate finché non si
trova una prova ufficiale e una strategia esplicita di deduplicazione.

## Regole di rilascio e metodi futuri

1. Bloccare qualsiasi scheda con `date_quality=prevista` o
   `confermata` se `date=[]`.
2. Se aumentano improvvisamente le località evidentemente malformate o
   le sovrapposizioni settimanali, fermare il rilascio DEV e controllare
   la fonte che le ha introdotte.
3. Per le 52 località dubbie, ottenere un elenco aggiornato dei Comuni
   ISTAT (fonte istituzionale 2026), confrontare il nome e la Regione
   con i valori sorgente e creare un dry-run di riconciliazione.
   Non sostituire automaticamente `citta` con una parte del titolo.
4. Per i possibili doppioni, partire dagli ID della fonte e
   dalle date/orari effettivi, confrontare luogo e giorno, mantenere
   la provenance di ogni scheda e preferire raggruppamenti UI reversibili
   piuttosto che cancellazioni del catalogo.
5. Non promuovere una correzione non ancora testata su un caso reale.

Fonte sulla classificazione aggiornata dei Comuni:
https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/

Un dataset rifatto ogni giorno **non** significa 13.779 mercati verificati
ogni giorno: il monitoraggio rileva la qualità dei dati, non garantisce
l'apertura del mercato senza una prova dell'organizzatore.
