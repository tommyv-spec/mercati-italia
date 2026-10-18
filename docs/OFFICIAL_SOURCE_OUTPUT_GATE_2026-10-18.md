# Validazione automatica delle 5 sorgenti ufficiali — 18 ottobre 2026

## Problema riscontrato

Il catalogo DEV ha **13.810 schede**. Il nuovo audit per editore
(prodotto giornalmente) distingue **87 sorgenti effettive** dal registro
di **49 dataset candidati**. I principali sono Happings (9.647),
EventiESagre (2.197), Regione Lombardia MERCap (1.128) e
Cose di Casa (432): la loro data di importazione non conferma
una singola visita o l'apertura di un mercato.

Una verifica live del dataset
[Milano DS291](https://dati.comune.milano.it/dataset/ds291-economia-mercati-settimanali-scoperti)
ha trovato 85 righe e queste colonne:
ID, MERCATO, sette giorni della settimana, orari,
CAP, MUNICIPIO, NIL, LONG_X_4326, LAT_Y_4326, Location.

**Non compare** un campo con via/indirizzo. Questo spiega tutte le
85 schede Milano senza indirizzo. Il feed include coordinate,
ma non una sede stradale verificata.
Non costruire un indirizzo da MERCATO, NIL o reverse geocoding
automatico. Cercare una fonte comunale di sede **per ID**, non
confondere il mercato "Papiniano" con una via d'accesso certa.

## Nuovo controllo DOPO il parser

Una HTTP 200, una API con total_count e un CSV valido non
dimostrano che il **parser abbia letto la colonna corretta**.
Il file backend/official_source_output_gate.py è un gate comune:

- Milano, Firenze, Lombardia MERCap, Bologna e Corciano:
  profilo, ID, regione, provincia, qualità coordinate e
  link di attribuzione sono controllati per **ogni riga**.
- La data del dataset non rinnova alcuna verifica umana.
  Ogni data prevista deve essere futura, ISO e coerente
  col giorno dichiarato.
- Le informazioni mancanti restano mancanti, mai inventate.
- Le righe MERCap rappresentano mercato + giorno della settimana:
  non collassare due giornate nella stessa identità fisica.
- Cambi di schema, URL esterni, date impossibili, coordinate
  invalide, variazioni ID senza nuova data publisher,
  forte perdita di completezza o perdita massiva di record
  bloccano **l'intero batch della fonte**.
- autopilot.source_feed() usa il gate dopo il parser.
  autopilot.retrieve_sources() lo applica al batch o al
  checkpoint di ripresa, prima del merge.
- Se un batch è bloccato, conserva la versione esistente
  senza dichiarare chiusure o aperture verificate.
- Stato e report contengono contatori/digest degli ID,
  non copie delle righe in un nuovo report.

## Audit indipendente giornaliero

backend/official_source_output_audit.py controlla in sola lettura
i cinque adapter (compreso Bologna, non ancora abilitato nella
policy generale) e può confrontare la lettura con l'ultima
impronta valida. I report distinguono dati aggiornati oggi da
**ultima prova storica**. Non modificano il catalogo.

Comandi dalla root:

```bash
python -m unittest discover -s backend/tests -v
python backend/official_source_output_audit.py --offline \
  --out /tmp/official-qa.json \
  --report /tmp/OFFICIAL_SOURCE_OUTPUT_QA.md
```

La pianificazione GitHub dedicata deve aggiornare soltanto
reports/automation/official-source-output-qa.json e
OFFICIAL_SOURCE_OUTPUT_QA.md su DEV dopo regressioni, mai
public/data/v1 o l'app di produzione.

Questo controllo NON concede nuove licenze, non autorizza
copie di contenuti commerciali né verifica i singoli mercati.
