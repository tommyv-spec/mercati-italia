# Fonti ad alto rendimento per migliorare il catalogo già esistente

Ricerca: **17 ottobre 2026**. Ambito: `DEV` e **sola riconciliazione**.
Il catalogo ha **13.810 schede** nell'ultimo manifest del 17/10. Il
report di copertura salvato (`reports/automation/data-coverage.json`) conta
ancora **13.784 schede**: il workflow di audit si è fermato per il vecchio
filtro fisso su Corciano. NON usare i numeri di copertura come misure della
versione odierna e NON chiamarli matching con nuove fonti.

## I dataset con il maggiore potenziale pratico

### 1. Calendario ufficiale dei mercati del Veneto 2026

- Ente: **Regione Veneto**, [pagina sorgente](https://www.regione.veneto.it/web/attivita-produttive/dalla-a-alla-z-dettaglio?articleId=109333),
  [PDF originale 2026, 16 pagine](https://www.regione.veneto.it/documents/10713/12114597/Calendario%2Bregionale%2Bmarcati%2B2026.pdf/be79e5c1-ceae-4e76-8207-3b49630ae080).
- Contenuto ispezionato: Provincia, Comune, luogo, denominazione,
  stagionalità, periodicità, giorno, orario, quantità di posteggi previsti
  e assegnati. **Contiene anche posteggi isolati**: non sono nuovi mercati.
- Esempi che provano la granularità dei dati: Belluno elenca sedi distinte
  `Piazza Piloni` e `Piazza dei Martiri/Castello`, entrambe di sabato,
  più sedi minori, ciascuna con un proprio indirizzo e orario. Alleghe e
  Falcade riportano anche finestre stagionali.
- Nel nostro catalogo **1.203 schede Veneto**. Nell'ultimo audit
  ancora **947 senza orari** e **275 senza indirizzo**. Questo NON implica
  che 947/275 saranno correggibili: serve confrontare le righe.
- **Stato licenza:** la pagina ufficiale consultata non riporta in modo
  esplicito una licenza di riuso di questa specifica tabella PDF.
  È consentita la ricerca/valutazione, NON è approvata la copia
  automatica dei dati nel nostro catalogo.
- **Primo pilot consigliato:** parsare SOLO in memoria un PDF ufficiale
  fingerprintato, dividere per provincia/Comune/luogo/giorno, escludere
  `posteggio isolato`, `posteggi isolati`, casi senza luogo o giorni
  discordanti. Confrontare le 1.203 schede esistenti, senza scriverle.
  Restituire soltanto conteggi di `exact_match`, `ambiguous`,
  `missing_hours_proposals`, `missing_address_proposals`,
  `day_conflicts`, `existing_not_in_publisher_calendar`,
  `source_venue_not_in_catalog`. Non chiamare questi ultimi
  nuovi mercati finché non si esclude il doppione.
- La dicitura **2026** si riferisce al calendario programmato,
  non certifica che ogni mercato sia aperto oggi.

### 2. Regione Lombardia MERCap — consolidare prima di importare

- [Fonte ufficiale](https://www.dati.lombardia.it/d/68zx-njaw),
  [metadati nazionali](https://www.dati.gov.it/node/view-dataset/dataset?id=2e41941b-80fb-4ded-8330-427383f725f8).
  Dati comunali, indicati come aggiornati **settimanalmente**.
- Già collegato in `backend/source_lombardia.py`; il codice interroga
  metadati, snapshot integrale con paginazione, ID `codice_id`,
  Comune/provincia, orari invernali/estivi e validazioni coordinate.
  Un mercato ripetuto in più giorni genera più righe `mercato-giorno`.
  Il Comune di Milano è trattato da un'altra fonte e non va duplicato.
- Nel nostro catalogo **3.948 schede Lombardia**. Ultimo audit salvato:
  **2.766 orari mancanti** e **754 indirizzi mancanti** su 3.947
  schede di allora. Non è detto che le righe MERCap coincidano con
  tutte le schede storiche.
- **Azione:** usare la fonte **già approvata** per un audit di
  corrispondenze con le schede legacy. Mai fondere sedi distinte solo
  perché nome e Comune coincidono. Conservare ID e provenienza
  originari. Dove orari o vie si contraddicono, aprire quarantena.
- Licenza **CC0** verificata dai metadati nell'adapter esistente;
  la data di aggiornamento del dataset non è verifica del singolo mercato.

### 3. Campagna Amica: grande rete nazionale, permessi da verificare

- [Directory ufficiale della rete](https://www.campagnamica.it/la-nostra-rete/mercati-a-km-0/).
  [Coldiretti ha dichiarato circa 1.200 mercati contadini](https://www.coldiretti.it/economia/campagna-amica-inaugurato-il-mercato-contadino-a-torino)
  nel novembre 2025. Non abbiamo misurato 1.200 schede estraibili dal sito.
- Un esempio concreto:
  [Coldiretti Milano/Lodi/Monza, 24 marzo 2026](https://milano.coldiretti.it/news/vendita-diretta/ecco-tutti-i-nostri-mercati-agricoli-sul-territorio/)
  pubblica elenco territoriale, vie e orari. Include più sedi nella stessa
  città (es. Milano) e periodicità mensili. Queste informazioni potrebbero
  completare schede di mercati contadini del catalogo.
- La directory non è un dataset open data con licenza di esportazione
  verificata. **Non eseguire bulk scraping o riversamento** senza
  consenso o condizioni di riuso chiare. Richiedere un CSV/API autorizzato
  o una collaborazione per aggiornamenti.
- Il mercato dei produttori e il mercato comunale della stessa piazza
  possono essere lo stesso evento o iniziative distinte: trattare come
  conflitto finché non si chiarisce.

### 4. Mercatini dell'antiquariato Veneto 2026

- [PDF originale Regione Veneto, 3 pagine](https://www.regione.veneto.it/documents/10713/12114597/Calendario%2Bmercatini%2Busato%2B2026.pdf/7ca1a502-6de9-4e5e-a247-4ec2f3e6cf3d).
  Offre luogo, cadenza mensile/stagionale, giorni, orari e posteggi.
- Può migliorare un sottoinsieme di mercati **antiquariato/collezionismo**,
  spesso con regole come `terza domenica del mese, eccetto agosto`.
  Non ridurre le eccezioni ad una generica ripetizione ogni domenica.
- Licenza di riuso specifica del PDF non ancora accertata. Nessuna
  aggiunta automatica di date o eventi.

### 5. OpenStreetMap: geografia su tutta Italia, non agenda ufficiale

- [Geofabrik Italia](https://download.geofabrik.de/europe/italy.html),
  [amenity=marketplace](https://wiki.openstreetmap.org/wiki/Tag:amenity%3Dmarketplace),
  [licenza](https://www.openstreetmap.org/copyright).
- Può servire per **trovare coordinate sospette** nel nostro catalogo,
  distinguere centro Comune / area mercato e confrontare nomi e strade.
  `opening_hours=*` può esistere ma non certifica l'attività nel 2026.
- **ODbL**: richiede attribuzione e ha obblighi share-alike sulle banche
  dati derivate. Verificare compatibilità con la nostra distribuzione
  prima di mescolare/redistribuire campi o coordinate. Una semplice
  corrispondenza OSM non conferisce permesso di modificare il pin.
- Per ricerca massiva usare estratti regionali e lavoro offline,
  non migliaia di query all'API pubblica Overpass.

### 6. Veneto: molte risorse CSV comunali raccolte nello stesso portale

- [dati.gov.it: fiere e mercati Veneto](https://www.dati.gov.it/node/192?tags=fiere).
  Esistono molti file strutturati 2026 per Comuni diversi.
- Attenzione: dataset `Posteggi mercati e fiere` o `Fiere e mercati`
  possono contenere **una riga per posteggio, concessione o anno**,
  non una riga per mercato. Non interpretare il totale righe come
  nuove sedi e non generalizzare una licenza per tutti i dataset.
- Buona opportunità per un `template CSV` condiviso, previa approvazione
  separata dell'editore/dataset e verifica del significato dei campi.

### 7. Slow Food Mercati della Terra — verifica mirata

- [Directory Italia](https://www.fondazioneslowfood.com/it/nazioni-mercati/italia-it/).
  [Notizie di settembre 2026](https://www.slowfood.it/la-prima-slow-week-di-settembre-rianima-gli-animi-e-gli-eventi/)
  con diversi luoghi, calendari e orari.
- Buon controllo per mercati di produttori locali.
  Elenchi tematici, contenuti dei singoli organizzatori e date talvolta
  diverse fra pagine: non è un censimento completo.
- Permessi di riuso massivo non stabiliti: solo ricerca/revisione
  finché non viene accordata licenza/partnership.

### 8. Piemonte — anagrafica regionale **storica**

- [Scheda dati.gov.it Regione Piemonte](https://www.dati.gov.it/node/view-dataset/dataset?id=26c619d9-ecf8-4882-910e-925a4fb459ec).
  Copertura potenzialmente ampia: sedi, giorni, periodicità, posteggi.
  **Dati aggiornati al 2019**, non al 2026.
- Riutilizzare come pista per anomalie strutturali o trovare pubblicazioni
  comunali sostitutive; **non** correggere con essa gli orari correnti o
  creare appuntamenti futuri.

## Metodo di riconciliazione prima della pubblicazione

1. Conservare il manifest attuale, l'ID e tutti i campi della scheda
   originale. Scaricare la fonte SOLO con URL e dimensioni consentiti,
   salvarne SHA-256, data vera e licenza.
2. Distinguere rigorosamente `venue`, `venue_day`, `stall`,
   `concession`, `historical`, `one-off event`. Non creare una
   nuova scheda quando cambia soltanto il giorno o l'operatore.
3. Per il matching usare **Comune ISTAT + provincia + sede fisica +
   giorno**. Nome e coordinate da soli non bastano; se Comune o via
   sono assenti, la riga finisce in revisione.
4. Proporre prima il completamento di campi vuoti:
   `orario_testo`, `indirizzo`, `ricorrenza`, stagionalità.
   Le differenze sui campi non vuoti vanno confrontate senza overwrite.
5. Mai impostare `confermata`, `verificato_il`, coordinate precise
   o navigazione attiva in base a cataloghi o a PDF calendariali.
   Una previsione rimane `prevista` con anno e fonte.
6. Prima e dopo: confrontare tutti gli ID, collisioni, date, fonte
   originale, conteggi per Comune, record in quarantena e fruizione
   mobile. Rilascio **DEV only**, poi revisione separata per produzione.

## Priorità: correggere prima i record esistenti

- **Primo:** Veneto 2026, perché la fonte è ufficiale, ricca di
  orari/sedi, e il nostro catalogo ha molti vuoti. Prima solo
  reconciliazione e verifica diritti PDF.
- **Secondo:** Lombardia MERCap, perché l'importer è già pronto;
  massimizzare i recuperi sicuri e individuare collisioni legacy.
- **Terzo:** Campagna Amica, fonte organizzatore con ampia rete;
  cercare licenza o esportazione autorizzata prima dell'automazione.
- **Quarto:** OSM per individuare errori geografici su scala nazionale
  con appropriata revisione ODbL.

## Strumenti aggiunti al repository

`backend/data/high-yield-source-leads-2026-10-17.json` contiene
otto schede di *ricerca* (non contratti di import). `backend/high_yield_source_audit.py`
calcola i margini regionali leggendo **soltanto** il report di
copertura locale. Nessuna rete e nessuna scrittura sulle schede.

Esecuzione da root:

```bash
python backend/high_yield_source_audit.py \
  --registry backend/data/high-yield-source-leads-2026-10-17.json \
  --coverage reports/automation/data-coverage.json \
  --out /tmp/high-yield.json \
  --report /tmp/HIGH_YIELD_SOURCES.md

python -m unittest discover -s backend/tests -v
```

**Importante:** i numeri dei campi mancanti sono *limiti di opportunità*
per regione, non corrispondenze provate con un nuovo dataset.
Prima di promettere una quantità di schede corrette, bisogna produrre
un report di confronto reale sulla stessa versione del catalogo.
