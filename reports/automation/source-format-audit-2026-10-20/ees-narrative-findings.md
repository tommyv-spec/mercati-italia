# Eventi e Sagre: sezioni narrative delimitate

Verifica del 20 ottobre 2026 sui **11 HTML originali** acquisiti dal workflow
`39471001816`. È un replay locale dei byte HTTP già acquisiti: nessuna nuova
richiesta di rete, nessuna scrittura nel catalogo pubblicato. URL, dimensioni,
SHA256 e selettori di ciascuna pagina sono in `ees-narrative-replay.json`.

## Meccanismo corretto

- [x] Leggere le sezioni principali `INFORMAZIONI UTILI`, `DOVE` e `ORARI`,
  conservando i confini dei paragrafi e delle liste del DOM.
- [x] Conservare gli orari insieme alle singole date osservate. Una lista di
  orari datati non diventa un orario giornaliero permanente.
- [x] Usare l'anno della sola edizione esplicita e coerente. La data di lettura
  e la data di modifica della pagina non forniscono mai l'anno dell'evento.
- [x] Registrare i conflitti tra intestazione e testo, incluse date fuori
  dall'edizione, orari differenti e continuazioni sovrapposte senza data.
- [x] Escludere footer, contatti, concerti, laboratori, sedi accessorie e
  continuazioni prive di una data attribuibile. Un secondo titolo di servizio
  dentro una sezione accessoria non riapre il contesto principale.
- [x] Trattenere un `DOVE` con località aggiuntiva discordante o irrisolta.
  `Via Roma` e `Via Milano` restano nomi di strade, senza interpretarne il nome
  come un cambiamento di Comune.
- [x] Non assegnare un calendario generale alle diverse sedi di una pagina
  con più blocchi di mercato; restano necessari i confronti di sede e giorno.

La modifica riguarda il formato del lettore, senza tabelle di correzione per
singoli ID. Il bridge utilizza i campi già previsti `occurrences`,
`hours_qualifications` e `field_evidence`. I conflitti e le informazioni storiche
attraversano la normalizzazione e l'esportazione senza diventare conferme attuali.

## Risultato dimostrato sui byte reali

| Fonte osservata | Informazione precedentemente persa | Risultato del replay |
| --- | --- | --- |
| Borgo diVino, Celle Ligure | Paragrafo DOVE con Via S. Boagno; lista ORARI con tre date e orari 18–24 | Estrazione corretta. Il raccordo al catalogo resta trattenuto perché l'indirizzo già salvato è una ripetizione del titolo dell'evento, non vuoto. Nessuna sovrascrittura. |
| Fiera del Vino, Polpenazze | Orari per giorno, pausa per riallestimento, ingresso e una data oltre il termine della scheda | Fatti storici conservati; conflitto di edizione e di orari segnalato. Le righe sovrapposte senza data non sono attribuite a un giorno come aperture. |
| Le Vie del Gusto e dell'Artigianato, San Piero Patti | Due sequenze di giorno e orario unite nel medesimo paragrafo | Due orari storici conservati; differenza rispetto all'intestazione segnalata. Nessun calendario applicato dal testo in conflitto. |
| Altre otto pagine | Informazioni già lette o contenuti accessori/non sufficientemente delimitati | Documento estratto invariato. |

Dieci pagine descrivono edizioni già passate. L'unica futura nel campione,
Fasulin a Pizzighettone, non espone una sede precisa o orari nel contenuto
acquisito e contiene una sequenza di date ambigua. Il replay non la espande in
aperture quotidiane.

Sul catalogo reale di **13.856 identità**, il raccordo e l'export modificano
soltanto **due oggetti di evidenza editoriale storica**, quelli di Polpenazze e
San Piero Patti. Tutti gli altri valori dei record rimangono identici, comprese
le **2.264 ricevute**. Le evidenze editoriali restano 25. I controlli semantici,
il controllo dell'export e la validazione statica passano; il secondo replay è
idempotente. Nessun indirizzo/orario attuale e nessuna data futura vengono
aggiunti da questi undici documenti.

## Formati ancora aperti, distinti da questo fix

- [ ] Nomi di sedi senza una strada, come Malga Millegrobbe: richiedono una
  rappresentazione di sede nominata, senza trasformarli in un indirizzo preciso.
- [ ] Elenchi di date in prosa senza una sezione orari delimitata, come le due
  giornate della Ciaspomagna: non equivalgono a ogni giorno dell'intervallo.
- [ ] Più strade nell'intestazione di una manifestazione: vanno conservate come
  area articolata, senza scegliere arbitrariamente una singola sede.
- [ ] Deduplicazione semantica delle ricorrenze storiche ripetute di Courmayeur;
  gli orari degli incontri con gli chef restano attività accessorie.
- [ ] Espressioni ambigue di date, come la sequenza di novembre a Pizzighettone,
  e indirizzi preesistenti che ripetono il titolo: restano trattenuti con motivo.

## Verifica

`python -m unittest discover -s backend/tests -p 'test_eventiesagre*.py' -q`

La suite comprende **100 test** del parser e del bridge, inclusi 22 nuovi test
semantici con strutture sintetiche. Queste fixture non sono presentate come
catture originali. Il replay dei documenti originali è provato separatamente
dagli hash, dai selettori e dai risultati dei controlli nell'audit JSON.
