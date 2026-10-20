# Qualità dei dati DEV: verifica della pubblicazione

## Stato misurato prima della nuova esecuzione

Il catalogo DEV al commit `05dce2dd00a2192b37da076042090383eef37c65` contiene
ancora la fotografia generata il 19 ottobre 2026 alle 09:56 UTC. Le correzioni
dei lettori sono presenti nel codice, ma la nuova acquisizione non è ancora
stata promossa. I risultati dei test del codice e dei replay non dimostrano
che il catalogo pubblicato sia stato aggiornato.

La [baseline completa per fonte](../reports/automation/dev-data-quality-baseline-2026-10-20.json)
conserva manifest, impronta, definizioni delle misure e limiti del confronto.

| Misura sul catalogo pubblicato | Schede |
| --- | ---: |
| Totale | 13.824 |
| Indirizzo vuoto | 3.429 |
| Indirizzo vuoto o vago secondo `audit_dataset` | 5.889 |
| Orario vuoto | 10.853 |
| Nessuna data futura | 1.918 |
| Date future classificate `prevista` | 11.906 |
| Date future classificate `riportata` o `confermata` | 0 |
| Data del contenuto sorgente non dimostrata nel catalogo | 12.574 |
| Almeno una ricevuta di campo valida esportata | 0 |
| Lettore configurato per il formato primario | 9.451 |
| Formato primario senza lettore configurato | 4.373 |

Un dato presente può comunque essere vecchio o sbagliato. Una ricevuta di
estrazione dimostra ciò che la fonte pubblicava al momento della lettura,
senza trasformarlo in una conferma indipendente dell'apertura del mercato.
I lettori devono conservare questa distinzione anche nell'export e nell'interfaccia.

## Blocchi finali riprodotti e correzione del meccanismo

Il candidato completo ottenuto dal replay delle catture originali contiene
13.826 schede: tutte le 13.824 identità precedenti e due ammissioni Happings
ricostruibili dalle pagine osservate. Passa i controlli interni dell'Autopilot,
ma due ulteriori consumatori della procedura MAIN confrontavano i conteggi
prima e dopo le ammissioni come se riguardassero lo stesso insieme:

- `reviewed_city_static_guard.py`, nella verifica QA degli asset finali;
- `autopilot_history.py`, prima del commit di pubblicazione DEV.

La correzione ricostruisce le aggiunte dal certificato sorgente e le confronta
con le righe effettive e con l'indice del catalogo finale. Soltanto le identità
provate entrano nell'equazione dei conteggi. I totali delle fasi precedenti
rimangono storici: non vengono riscritti per farli coincidere con il risultato.
Un numero dichiarato, un ID aggiuntivo senza prova o una sede modificata non
autorizzano la pubblicazione.

## Acquisizione reale del 20 ottobre, ore 16:50–17:02 UTC

L'[esecuzione 39460884416](https://github.com/tommyv-spec/mercati-italia/actions/runs/39460884416)
ha acquisito fonti HTTP e prodotto un candidato di 13.853 schede con tutte
le 13.824 identità precedenti. Il commit DEV usato è
`7b9388d532b4da1fc0ef14b5a64211420b306a76`. Il
[confronto completo per fonte e formato](../reports/automation/dev-live-candidate-39460884416-quality.json)
è legato all'impronta dell'artefatto originale e ai due manifest validati.

**Questo candidato non è stato pubblicato.** I controlli sui dati, sulle prove
sorgenti, sull'indice e sulla build sono passati. Il test mobile si è fermato
perché un indirizzo appena recuperato porta un'altra scheda nella stessa sede:
il controllo contava tutte le visite della sede invece di verificare il gruppo
dei due duplicati originali. La correzione verifica quel gruppo e l'accesso
a entrambi gli originali, conservando distinte le altre identità.

| Misura con definizione invariata | DEV prima | Candidato HTTP |
| --- | ---: | ---: |
| Schede | 13.824 | 13.853 |
| Indirizzi vuoti | 3.429 | 3.214 |
| Indirizzi vuoti o vaghi, `audit_dataset` | 5.889 | 5.655 |
| Orari vuoti | 10.853 | 10.593 |
| Schede con ricevute di campo valide | 0 | 1.671 |
| Schede con calendario esplicito della fonte valido | 0 | 29 |

Sulle identità già presenti: 215 indirizzi vuoti recuperati, 26 sedi generiche
precisate, 260 orari vuoti recuperati e un testo orario aggiornato. Nessun
indirizzo o orario preesistente è stato svuotato; nessun nome, Comune o punto
geografico è stato cambiato da questo aggiornamento. Le 29 nuove schede Happings
hanno 152 date future esplicitamente pubblicate, classificate `riportata`.
Il normale scorrimento delle previsioni e la rimozione delle date passate sono
misurati separatamente e non sono conteggiati come nuove informazioni sorgenti.

La lettura dei dettagli Happings ha completato 61 pagine entro il limite di
420 secondi. Le 16 pagine provinciali selezionate hanno invece incontrato un
redirect intermedio non riconosciuto. La catena realmente osservata è ora
documentata nei test del trasporto; non viene resa più permissiva l'identità
della pagina finale. La frontiera dei vecchi URL conserva il punto raggiunto
e consuma al massimo due richieste del budget provinciale esistente.

## Calendari con limiti dichiarati dalla fonte

Il lettore MERCap conserva ora i campi originali `dal`, `al`, mesi, Comune,
provincia e identità della sede. Le previsioni rispettano gli intervalli
giorno/mese anche dopo merge, export e riapertura del catalogo senza rete.
Valori composti o incompleti restano documentati e sospendono la previsione;
non ricevono un anno o un'interpretazione inventati. Il replay completo conserva
13.824 identità e rimuove 38 previsioni sicuramente fuori intervallo. Queste
regole sono verificate anche dai controlli finali del percorso di pubblicazione.

## Seconda acquisizione reale: liste provinciali recuperate

L’esecuzione [39465324614](https://github.com/tommyv-spec/mercati-italia/actions/runs/39465324614)
usa DEV `60c9c7c`. Legge correttamente 13 elenchi provinciali Happings su 14
selezionati; Enna risponde 404 e non produce aggiornamenti. Legge inoltre 82
pagine di dettaglio. Il candidato contiene 13.856 schede, tutte le identità
precedenti e 32 nuove identità provate, con 158 date future esplicite.

Sulle schede precedenti recupera 363 indirizzi vuoti e precisa 26 sedi generiche;
recupera 254 orari vuoti e aggiorna un testo orario già presente. Restano 3.066
indirizzi vuoti e 10.599 orari vuoti. Sono esportate ricevute valide per 2.235
schede. Il [confronto completo](../reports/automation/dev-live-candidate-39465324614-quality.json)
conserva le definizioni originali e l’impronta dell’artefatto.

**Anche questo candidato è ancora in attesa di pubblicazione.** I controlli
sorgenti, dei dati e della build passano; l’allarme sulla crescita dei gruppi
reversibili confronta 588 pulsanti ripetuti con il vecchio riferimento di 382.
La [verifica completa](../reports/automation/display-group-growth-review-39465324614.json)
ricostruisce tutte le 258 nuove coppie: ognuna dipende esclusivamente da campi
recuperati con ricevute sorgenti valide. Nessun cambiamento di identità, fonte
primaria, Comune, coordinate o conferma umana; nessuna nuova coppia inspiegata.
Il riferimento statistico è aggiornato ai valori effettivamente esaminati,
marcandolo esplicitamente come candidato non pubblicato. Le soglie e i controlli
MAIN restano identici; le schede originali rimangono tutte apribili.

## Lettori ricorrenti delle fonti già presenti

Il nuovo raccordo legge le URL primarie già associate alle schede Eventi e
Sagre e Cose di Casa. Conserva una coda pubblicabile con esiti, tentativi,
letture effettive e pagine ancora da leggere; un errore non vale come lettura
riuscita. Il limite è 64 dettagli/210 secondi per Eventi e Sagre e 16 dettagli/
90 secondi per Cose di Casa, con richieste distanziate e budget separati.
I due domini vengono letti contemporaneamente; il normale Autopilot giornaliero
rimane il solo percorso di pubblicazione.

Il raccordo conserva indirizzi, orari, condizioni e limiti delle edizioni,
separando la data effettiva della fonte dalla data in cui viene letta. Gli
intervalli di una manifestazione non diventano aperture quotidiane. Le edizioni
storiche restano consultabili e possono sospendere previsioni non sostenute,
senza cancellare il mercato o dichiararlo definitivamente chiuso. I dettagli
nell’interfaccia mostrano anche limiti, orari storici e contraddizioni.

Il [rapporto dei lettori editoriali](../reports/automation/editorial-reader-validation-20261020.json)
distingue cinque acquisizioni HTTP complete Cose di Casa dai 17 snapshot di
fatti Eventi e Sagre salvati nell’audit precedente, che non conservavano il
trasporto HTTP originale. I replay Cose di Casa conservano tutte le 13.824 e
13.856 identità attraverso export, ricaricamento e giorno offline successivo;
recuperano due orari correnti, conservano due orari storici nelle sole prove
e ritirano quattro previsioni non sostenute dalla relativa edizione.

Il lettore mantenuto Roma d881 seleziona il CSV più recente dai metadati
realmente ricevuti. Le 70 righe originali producono 68 raccordi univoci e due
sospensioni per identità danneggiate. Gli orari espongono le date 2021/2023 del
CSV: non sono conferme attuali e non aggiornano la freschezza del calendario.
Le prove dei campi vengono ricostruite dal contenuto originale prima e dopo
l’export. Nessuna modifica a indirizzi, coordinate o identità da questo lettore.

Sono chiusi nove ulteriori TODO di meccanismo, con prove specifiche, nel registro
delle fonti. Restano separati i TODO narrativi, discovery e conflitti non
risolti. La prima acquisizione reale dei nuovi lettori nel candidato, il ciclo
completo di tutte le URL e la pubblicazione effettiva richiedono ancora i loro
risultati osservati; non sono dedotti dal passaggio dei test.

## Check-in e criterio di completamento

- [x] Misurare il catalogo realmente pubblicato, su tutte le fonti.
- [x] Riprodurre i blocchi dei controlli finali sul candidato completo.
- [x] Correggere i consumatori mantenendo la verifica semantica delle fonti.
- [x] Completare una nuova acquisizione HTTP nel normale Autopilot (`39460884416`).
- [ ] Superare QA e pubblicazione con lo stesso commit DEV e gli stessi asset.
- [ ] Confrontare il manifest pubblicato e la preview con il candidato verificato.
- [ ] Misurare i recuperi effettivi e le lacune rimaste, con le stesse definizioni.

Le ultime attività si chiudono con l'ID della nuova esecuzione e gli asset
effettivamente pubblicati. Non si chiudono con un semplice merge del codice.
Il workflow MAIN esistente rimane il solo percorso di pubblicazione e conserva
la sua programmazione. Le attività sui formati e i raccordi ancora mancanti
restano nella [checklist delle fonti](../reports/automation/SOURCE_FORMAT_CHECKLIST.md).
