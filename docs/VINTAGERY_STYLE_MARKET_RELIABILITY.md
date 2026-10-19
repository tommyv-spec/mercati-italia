# Mercati Italia: qualità dei dati stile Vintagery, senza eliminare schede

Revisione **19 ottobre 2026**. Pipeline DEV e aggiornamento dei meccanismi di fonte.

## Obiettivo operativo

Per ciascun mercato esistente separiamo:

- **Identità e luogo:** ID originale, Comune, provincia, indirizzo, coordinate; i
  centroidi e le posizioni indicative NON diventano ingressi navigabili.
- **Orari:** possono essere pubblicati da un dataset aggiornato, senza con
  questo confermare che la singola edizione si svolga oggi.
- **Calendario:** ricorrenza dichiarata, date previste calcolate,
  edizioni dichiarate/confermate e sospensioni restano concetti differenti.
- **Evidenza di ogni campo:** fonte primaria, ID del record pubblico,
  data effettiva del dataset, metodo di abbinamento e grado di certezza.
- **Stato di controllo:** un record incompleto o smentito rimane
  raggiungibile, con avvertenza e lavoro da approfondire; nessuna
  eliminazione o ricostruzione automatica dell'identità.

Questo replica i principi utili osservati su Vintagery (ricorrenze,
date da confermare, segnalazioni esaminate, precedenza alle fonti
pubbliche), **non importa contenuti Vintagery**. Non adottiamo la sua
directory come un feed liberamente riutilizzabile.

## Non interpretare "verificato" in modo scorretto

**Un feed consultato oggi NON verifica automaticamente l'apertura
di un mercato oggi.**

Lo stesso vale per una data prevista da una regola "ogni domenica".
La presenza di un orario o di una strada certa NON certifica la
prossima edizione. Il controllo della scheda richiede una prova
ufficiale esplicita, possibilmente aggiornata dal Comune o dall'organizzatore.

## Contratti una volta sola per fonte

`backend/data/market-evidence-source-families.json` descrive il
layout di cinque famiglie osservate: Happings (indice provincia/giorno
e pagine evento), EventiESagre (link e anni differenti), Cose di Casa
(mensili, pause ed eccezioni), Lombardia MERCap (ID sede+giorno,
CSV/JSON ufficiale), Milano (GIS+PDF comunale per ID).

Non concede alcun permesso nuovo di scraping, importazione o
attribuzione di "verificato". Le 87 etichette di fonte nel catalogo
vengono comunque scansionate e segnalate, anche se il relativo
parser non è ancora approvato.

Per Happings, il report legge lo stesso registro di autorizzazione usato dal
motore e ne conserva riferimento, impronta e data di controllo. L'istruzione
esplicita del titolare del progetto autorizza l'adattatore degli elenchi
settimanali nell'ambito DEV; non viene presentata come autenticazione dei
documenti del publisher. Il report non abilita crawler e non richiede un
nuovo consenso a ogni esecuzione. Un registro mancante, revocato o incoerente
produce lo stesso esito non autorizzato del motore. Eventi e Sagre e Cose di
Casa conservano il percorso senza raccolta massiva.

Una fonte che non rientra nelle cinque famiglie della worklist ha stato
`not_resolved_by_this_worklist`: il report indica di consultare anzitutto i
registri operativi esistenti per il passo successivo. L'assenza da questa descrizione
limitata non viene presentata come mancanza di autorizzazione; un lettore già
approvato, come quello generico di Bologna, mantiene il proprio stato nel
report di copertura delle fonti.

Per aggiungere una fonte:

1. campione originale e diritti d'uso verificati;
2. studio dei campi e della **granularità** (sede, giorno,
   posteggio, concessione o evento una tantum);
3. contratto editore, identificativo fonte, timestamp, URL
   e max richieste/dimensioni;
4. parser condiviso per il **tipo** di struttura (non uno scraper
   nuovo per ogni singolo mercato);
5. test su fonte reale, duplicati, dati anacronistici, cambi
   schema, errati match e blocco dei record parziali;
6. solo dopo, esecuzione ricorrente senza nuovo lavoro manuale.

## Algoritmo implementato

`backend/market_evidence_worklist.py`:

- apre le **13.824 schede** conservate nel manifest corrente;
- rileva per **ognuna** indirizzo mancante/vago, orario assente,
  mancanza ricorrenza, date future assenti, coordinate indicative
  e mancanza di conferma individuale;
- usa SOLO il feed normalizzato Lombardia **già letto**
  dall'importatore approvato per trovare riscontri con
  Comune+provincia+via+giorno (o stesso ID ufficiale);
- se manca la via ma il Comune ha un unico mercato quel giorno,
  crea una **pista da verificare**, non un indirizzo automatico:
  il record Happings potrebbe riferirsi a un luogo differente;
- ogni eventuale proposta memorizza campo, valore, ID e data
  dataset ufficiali, match, applicabilità e
  `opening_verified=false`;
- segnala conflitti fra Comuni, giorni, punti incompatibili
  o più sedi. I campi esistenti non vengono sovrascritti;
- divide la worklist in **31 sottoinsiemi stabili per ID**.
  In qualunque giorno controlla tutte le schede e prepara
  il sottoinsieme da approfondire. Una rotazione di 31
  giorni include ogni scheda incompleta senza richieste
  di rete per singolo mercato.

### Report Git e risorse

La lista dettagliata rotante è prova QA transitoria nel file
`autopilot-output/market-evidence-worklist.json` dell'Autopilot.
Lo storico Git conserva solo il riassunto e la matrice
fonte/carenze, evitando file enormi riscritti ogni giorno:
`reports/automation/market-evidence-summary.json` e
`reports/automation/MARKET_EVIDENCE_WORKLIST.md`.

La worklist rimane una ricerca di evidenze e non modifica i dati.
L'arricchimento è eseguito dai lettori descritti in
[Recupero e aggiornamento automatico delle fonti](AUTOMATIC_SOURCE_REFRESH.md),
con prove per campo e controlli indipendenti fino all'export. Le pagine
Happings già nella rotazione possono anche riscontrare sedi esistenti di
schede provenienti da altre origini, richiedendo identità e sede coincidenti
senza aumentare le richieste. Il report distingue la capacità di confronto
dal riscontro effettivamente ottenuto.

## Riproduzione senza costi per singola ricerca

Da root DEV:

```bash
python -m unittest discover -s backend/tests -v
python backend/market_evidence_worklist.py \
  --manifest public/data/v1/manifest.json \
  --contracts backend/data/market-evidence-source-families.json \
  --out /tmp/worklist.json --summary /tmp/summary.json \
  --report /tmp/MARKET_EVIDENCE_WORKLIST.md
```

La versione schedulata riceve anche
`--official-lombardia autopilot-output/sources/lombardia.json`
**solo se la fonte completa ha già passato il suo QA.**
Nessuna API a pagamento, nuove GitHub Actions o copie
massive dei testi editoriali.

## Misure per valutare i prossimi miglioramenti

- schede analizzate e **tutte le identità originali conservate**;
- numero di fonti con un parser approvato contro fonti ancora
  da studiare (e prove di licenza);
- proposte **forti** per campo e **piste deboli** distinte;
- campi realmente riempiti da prove ufficiali, senza
  contare date stimate come verificate;
- errori per schema cambiato, fonte non disponibile,
  duplicati e posizioni non precise, senza nasconderli.

### Percorsi attivi e lacune da misurare

1. **Happings (9.647 schede):** leggere gli elenchi provinciali attraverso
   l'adattatore autorizzato e confrontarli con tutte le identità compatibili.
   Continuare la ricerca di prove comunali e regionali per campi mancanti,
   conflitti o date di contenuto ignote.
2. **EventiESagre (2.197):** link-only come piste,
   verifica della singola edizione su Comune/organizzatore.
3. **Cose di Casa (432):** calendari mensili con pause,
   fonte primaria prima di confermare date.
4. **Dataset approvati:** automatizzare il completamento
   per campo con un contratto condiviso e un report di
   provenienza verificabile. Conservare sempre il record
   incompleto se una fonte viene a mancare.
