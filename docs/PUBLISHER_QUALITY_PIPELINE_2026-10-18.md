# Fonte per fonte: qualità, resa e aggiornamento automatico

Prima versione: **18 ottobre 2026** — solo DEV.

## Perché cambia il metodo

I 49 record del registro dati.gov.it NON sono le 49 fonti usate dal sito.
Abbiamo 13.810 schede e quattro fonti dominanti: Happings 9.647,
EventiESagre 2.197, Lombardia MERCap 1.128 e Cose di Casa 432.

Il nuovo codice \`backend/publisher_quality_matrix.py\` attraversa TUTTE
le schede salvate, ne identifica il \`fonte\`/URL, e calcola un profilo
separato per **ogni etichetta sorgente**, senza scegliere un campione
casuale. Ordina i lavori per record effettivi e, all'interno, misura
orari, indirizzi, coordinate, date, sorgente, età indicata del dato
e contraddizioni fra giorno dello slug, ricorrenza e date previste.

ATTENZIONE: un campo vuoto nel nostro catalogo non dimostra che la
fonte originale sia errata; e \`aggiornato_il\` può riferirsi alla nostra
importazione o a un dataset, NON a una conferma della singola apertura.

In parallelo il report prende **tutti i dataset ufficiali censiti**
dal registro di discovery (oggi 49) e rende esplicito se la fonte è:
\`metadata_candidate_only\`, \`schema_sampled_review_only\`,
\`already_integrated_adapter\`, \`statistics_not_event_venues\`,
\`concession_registry_not_market_venues\`. Una concessione non è un
mercato, un anno statistico non è una data di svolgimento.

## Formati studiati davvero

### 1. Happings — 9.647 schede

- [Indice settimanale Milano](https://www.happings.com/it/mercati-settimanali-a-milano-e-provincia/)
  raggruppa **una provincia per giorno della settimana**; righe
  Comune, sede, descrizione «la mattina». Una riga di elenco non fornisce
  automaticamente orari HH:MM, data della verifica o singolo evento.
- [Dettaglio Lana](https://www.happings.com/it/happing/mercato-del-venerdi-mattina-a-lana/)
  è un **altro layout**: titolo, sede, fascia 07:30–12:30, elenco date,
  variazione per 24 dicembre, organizzatore Comune. Una ricorrenza
  regolare non può sovrascrivere una eccezione della giornata speciale.
- Prima di costruire un importatore Happings servono diritti di riuso
  su scala nazionale e una revisione indipendente dell'attualità
  di sede/giorno, per esempio da Comuni e Regioni.
- Il nostro report **non effettua scraping massivo** e non dichiara
  «confermato» solo perché Happings fornisce un dato preciso.

### 2. EventiESagre — 2.197 schede

- L'indice contiene anche annunci 2022–2023 accanto a eventi nuovi.
- Esiste uno script storico con selettori HTML generici, ma
  il nuovo sistema **non** lo importa direttamente.
- Il collector quotidiano già attivo registra soltanto URL e ID,
  non testi protetti da diritti, con robots.txt e pagine limitate.
- L'aggiornamento finale richiede una nuova fonte ufficiale Comune
  o organizzatore per data, luogo, eccezioni e licenza.

### 3. Regione Lombardia MERCap — 1.128 schede

- Dataset autorizzato dell'ente, adapter stabile
  \`backend/source_lombardia.py\`.
- Fonte con granularità **mercato-giorno** e orari distinti
  per inverno/estate, non 1 riga = 1 mercato fisico.
- Il controllo precedente: 1.360 righe fonte, 129 abbinamenti sede/giorno
  con schede legacy già provviste di orari; 61 schede con indirizzo
  mancante ma vicinanza **non sufficiente** a correggerlo automaticamente.
- Il nuovo audit riporta con sicurezza solo i problemi nei dati nostri
  e usa l'adapter ufficiale per verifiche indipendenti prima di scrivere.

### 4. Cose di Casa — 432 schede

- [Mercatino Bologna](https://www.cosedicasa.com/mercatini/bologna-piazza-s-stefano)
  indica \`secondi sabato e domenica del mese\`, esclude luglio e agosto,
  ha eccezioni, luogo e organizzatore.
- Il sito stesso avverte che date e orari sono indicativi e che
  il visitatore deve verificarli presso l'organizzatore.
- Non ripubblicare contenuti protetti da licenza; controllare
  eventuali riscontri ufficiali per ciascuna sede.
- Ricorrenze «prima domenica», «secondi sabato e domenica» richiedono
  parser diversi dai mercati settimanali; il catalogo non deve
  inventare date precise o estendere 2025 automaticamente al 2026.

## Pipeline autonoma attuale e nuovo gate

1. **Raccolta dei publisher e prove:** \`reports/automation/source-registry.json\`
   e \`source-probes.json\` rotano le nuove fonti; gli adapter
   Lombardia, Milano, Firenze, Bologna, Corciano hanno ciascuno un
   contratto. Solo i file approvati sono importabili su DEV.
2. **Misura completa:** \`publisher_quality_matrix.py\` monitora
   ogni campo di ogni scheda con conteggi e piccoli ID di esempio.
3. **Dati contraddittori:** il giorno dello slug non può vincere
   su un «ogni martedì» esplicito, né possiamo proiettare date
   incompatibili con il giorno.
4. **Report di regressione:** confronta i conteggi per fonte fra
   scansioni senza interpretare la scomparsa di un ID come
   conferma della chiusura. Una nuova riga non è prova di un mercato nuovo.
5. **Aggiornamenti autorizzati:** riuso degli adapter ufficiali
   con ID stabili, validazioni di schema e licenze. Dati incerti
   restano in revisione con URL originale; niente conferme o coordinate
   inventate.
6. **Verifiche:** tutti i test + gate QA; il workflow deve
   generare un report DEV anche quando i siti terzi non rispondono,
   senza modificare file di catalogo o production.

## Esecuzione

Dalla root del repository:

\`\`\`bash
python -m unittest discover -s backend/tests -v

python backend/publisher_quality_matrix.py \\
  --manifest public/data/v1/manifest.json \\
  --registry reports/automation/source-registry.json \\
  --probes reports/automation/source-probes.json \\
  --out /tmp/publishers.json --report /tmp/PUBLISHERS.md
\`\`\`

Gli output da collegare all'audit giornaliero sono:
\`reports/automation/publisher-quality-matrix.json\` e
\`reports/automation/PUBLISHER_QUALITY_MATRIX.md\`.

**Politica:** zero import, zero conferme, zero sovrascritture
di \`public/data/v1\` da questo audit. Tutte le fonti vengono analizzate,
ma solamente le fonti con diritti e schema già approvati possono
alimentare un flusso distinto di arricchimento dati.
