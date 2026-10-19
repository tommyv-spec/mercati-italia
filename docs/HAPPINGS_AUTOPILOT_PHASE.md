# Happings nel ciclo DEV

Il recupero Happings è una fase di `backend/autopilot.py`, prima dell'export.
Legge una pagina provinciale per tutte le schede compatibili e conserva le
prove dei campi osservati. Usa il ciclo quotidiano e i controlli di rilascio
già presenti.

## Stato operativo dal 19 ottobre 2026

La policy versionata contiene:

```json
"happings_enrichment": {"enabled": true, "max_pages": 16}
```

`backend/data/happings-rights-review.json` registra l'istruzione esplicita
del titolare del progetto per raccolta, elaborazione e ripubblicazione in
DEV. Il report distingue i due fatti:

- `fetch_authorized: true`, con base `explicit_project_owner_instruction`;
- `rights_authenticated: false`, perché l'autenticazione dei documenti del
  concedente resta un'informazione separata.

La fase può operare con l'istruzione registrata. Il codice non richiede una
nuova conferma del medesimo consenso a ogni ciclo. Il registro conserva le
osservazioni precedenti sui documenti senza attribuire loro firme verificate.

`authorization_status()` controlla data, ambito, canale DEV e assenza di
revoca dell'istruzione. Una policy spenta o un registro non valido bloccano
anche la ripresa di prove salvate. Il fallback del modulo, in assenza di una
policy, rimane disabilitato.

## Una rotazione per le fonti

`catalog_page_routes()` collega ogni scheda ammessa a un URL provinciale
**già presente nel catalogo**. `select_pages()` ordina questo insieme stabile
e seleziona fino a 16 pagine per esecuzione. La selezione continua anche
quando gli indirizzi sono stati riempiti. Non dipende più dal numero di
campi vuoti.

Sul catalogo alla base DEV `fd000371c77822fd70dc3faadf369e85389ba8ae`, la
misura del 19 ottobre 2026 è:

| Famiglia di URL salvata | Schede Happings | Schede instradabili | Indirizzi vuoti nelle schede instradabili |
| --- | ---: | ---: | ---: |
| Elenco provinciale `mercati-settimanali-a-…html` | 4.487 | 3.883 | 2.152 |
| Elenco provinciale `mercati-settimanali-ad-…html` | 414 | 332 | 179 |
| Vecchio dettaglio `mercato-settimanale-a-…html` | 4.746 | 3.978 | 2 |
| **Totale** | **9.647** | **8.193** | **2.333** |

Le 8.193 schede fanno capo a **95 pagine provinciali**. Con l'insieme
invariato e 16 pagine per ciclo, sei esecuzioni quotidiane selezionano tutte
le pagine. Questo misura la copertura della rotazione: una pagina non
disponibile può fallire e viene segnalata come tale.

Le **1.454 schede** senza un collegamento provato restano nel catalogo e nel
report di copertura. Gli indirizzi vuoti instradabili sono candidati al
confronto: il numero non afferma che la fonte contenga una sede unica e
recuperabile per ciascuno.

## Collegamento dei vecchi dettagli comunali

Le vecchie pagine comunali vengono collegate al listato della propria
provincia senza scaricarle una per una. Il confronto richiede insieme:

1. URL HTTPS della famiglia comunale già osservata, senza query o host diversi;
2. Comune dell'URL uguale al Comune salvato, dopo la sola normalizzazione di
   maiuscole, accenti e punteggiatura; lettere mancanti, frazioni e suffissi
   numerici non vengono ricostruiti;
3. Comune, provincia e regione coerenti con il riferimento ISTAT locale;
4. nome generico di mercato settimanale e un solo giorno espresso da una
   formula settimanale completa, senza qualifiche di stagione, orario o stato;
5. una sola riga compatibile nella pagina e assenza di sedi salvate in conflitto.

Le schede con qualifiche di stagione, orario o stato restano segnali di
possibile conflitto di sede quando Comune e giorno settimanale coincidono.
La loro esclusione dalle nuove assegnazioni non le nasconde al confronto.
Anche una riga della fonte marcata dal parser come sede non utilizzabile,
per esempio con sospensione, stagione o orario non strutturato, resta nel
conteggio delle possibili sedi. Il motore rispetta questo esito del parser
sia per assegnare un indirizzo sia per registrare un riscontro.

Il report indica `province_index_join` come percorso del dettaglio comunale.
La fonte primaria della scheda resta il vecchio URL. La pagina provinciale è
registrata come fonte del nuovo riscontro. Questa relazione non dichiara che
sia stato osservato un redirect del vecchio dettaglio.

## Riscontro di schede provenienti da altre fonti

`secondary_catalog_page_routes()` descrive quali schede di altra origine
possono essere confrontate con le stesse pagine provinciali già nella
rotazione. Non aggiunge URL o richieste. Richiede identità generica di un
mercato ordinario, geografia ISTAT esatta, un solo giorno settimanale completo
e un indirizzo esistente specifico. I limiti temporali dell'identità originale
restano rilevanti anche quando il nome visualizzato è stato normalizzato.

Per registrare un riscontro, la sede già salvata deve coincidere con la sola
riga compatibile del publisher; il controllo delle sedi concorrenti comprende
tutte le origini. Una scheda di altra origine con indirizzo vuoto o vago non
ottiene un'assegnazione tramite questo percorso.

Vengono aggiunti soltanto `fonti` e `riscontri_campi`. Fonte primaria, URL,
indirizzo, ricorrenza, orari, date, coordinate e ID restano gli stessi.
L'osservazione di un valore preesistente non gli attribuisce `campi_gestiti`,
nemmeno dopo più cicli concordanti. La data del contenuto Happings resta
sconosciuta e il riscontro non conferma un'apertura futura.

## Campi osservati e aggiornamenti successivi

La fase può riempire una sede vuota con un indirizzo specifico proveniente
dalla riga unica. Aggiunge un riscontro in `riscontri_campi`, con identità del
mercato, URL, Comune e giorno della riga, hash dell'HTML e data di lettura.
Il limite è 2.000 assegnazioni di indirizzo per esecuzione.

I valori assegnati dal motore hanno il gestore `happings-weekly-index`.
Un successivo cambio di sede viene applicato solo con la stessa identità di
fonte, una lettura successiva, contenuto cambiato e assenza di prove
concorrenti. Una rilettura con valore uguale conserva la gestione precedente.
Una sede già presente e soltanto osservata dalla fonte non acquisisce questa
gestione. Gli interventi umani e le posizioni precise restano protetti.

Se una lettura successiva, con corpo diverso, mostra una sede specifica
discordante per la stessa riga fonte univoca, il motore ritira il precedente
riscontro contraddetto anche quando l'indirizzo non può essere aggiornato.
Conserva l'indirizzo e le prove delle altre fonti. Il report espone il ritiro
e la prova che lo giustifica. Indisponibilità, righe mancanti, più sedi,
contenuti vaghi o struttura cambiata non autorizzano questo ritiro.

La ricorrenza viene riscontrata soltanto quando la formula settimanale è
integralmente sostenuta dal giorno della riga. Un giorno diverso o una
qualifica non attestata non viene trasformato in un nuovo calendario.
Le diciture «la mattina» e «il pomeriggio» restano parti della giornata;
non forniscono ore numeriche.

La fonte non offre una data di aggiornamento del singolo contenuto che il
lettore possa attestare. I riscontri hanno quindi `fonte_aggiornata_il: ""`.
Una lettura recente rimane classificata come **riscontro con data della
fonte sconosciuta**. Non rinnova le date globali della scheda e non crea una
verifica di apertura o nuove date previste. Restano invariati anche orari,
coordinate, identità, Comune e fonte primaria.

## Richieste, errori e ripresa

Il lettore usa HTTPS, dominio esatto, `robots.txt`, pausa minima di tre
secondi, timeout di 18 secondi e massimo 2,6 MB per pagina. I redirect
ammessi restano nella stessa provincia e rispettano a loro volta robots e
limiti di richiesta.

| Stato | Significato |
| --- | --- |
| `disabled` | Policy disabilitata. |
| `blocked_rights` | Istruzione assente, revocata o registro non valido. |
| `offline_skipped` | Prova offline senza ripresa di risposte già salvate. |
| `no_eligible_pages` | Nessuna pagina instradabile dal catalogo corrente. |
| `retrieved` | Acquisizione limitata completata; il parser valuta i campi. |
| `resumed_checkpoint` | Risposte salvate validate e riusate senza richieste. |
| `resume_missing_evidence` | Ripresa priva di checkpoint, senza nuovi download. |
| `unavailable` | Nessuna pagina richiesta utilizzabile. |
| `partial_unavailable` | Alcune pagine non sono disponibili; le altre vengono valutate. |
| `layout_changed` | Tutte le pagine lette hanno una struttura non ammessa. |
| `partial_layout_changed` | Alcune pagine hanno una struttura diversa; le altre vengono valutate. |

`page_failures` conserva l'esito di ogni URL non disponibile. Un errore su
una pagina non elimina le risposte valide delle altre. La ripresa di un batch
interrotto conserva le pagine già ottenute e segnala gli URL senza esito.

`--resume` richiede lo stesso giorno, catalogo di partenza, input della fase,
policy e registro. Controlla ordine delle pagine, URL richiesto e finale,
hash e contenuto. Non rietichetta un vecchio download con la data di oggi e
non scarica pagine mancanti.

Il report `source-refresh-coverage.json` separa la capacità del lettore
(`happings_province_index`) dall'esito della lettura. Un URL dello stesso
dominio privo di un percorso valido resta `happings_source_scope_unproven`.
Le pagine non selezionate nel ciclo hanno uno stato distinto da quelle lette,
in errore o con struttura cambiata. Se un URL contiene schede instradabili e
altre ambigue, i due gruppi hanno conteggi separati.

`secondary_corroboration` espone separatamente il numero di schede di altre
origini ammesse al confronto di una sede esistente, gli URL secondari e i
loro esiti di lettura. Ogni risorsa primaria mantiene la propria copertura:
una scheda Eventi e Sagre confrontabile con Happings non viene conteggiata
come se disponessimo di un lettore Eventi e Sagre. Un confronto possibile o
una pagina scaricata non costituiscono una ricevuta di riscontro del campo.

## Identità e controllo dell'export

L'export conserva tutti gli ID del catalogo, compresi quelli incompleti o non
instradabili. Due schede che acquisiscono o riscontrano la stessa sede
conservano i loro ID. Il controllo finale confronta tutte le schede
normalizzate con i soli campi e riscontri autorizzati dalla fase. Il report
mantiene il conteggio storico `protected_existing_market_ids` per Happings e
aggiunge `protected_catalog_market_ids` e relativa impronta per il catalogo
completo, così anche le prove secondarie appartengono all'esatto insieme
conservato.

La promozione del candidato DEV continua a dipendere dai controlli ordinari
dell'Autopilot, inclusi integrità del catalogo, prove delle fonti, build e
navigazione. La fase non pubblica direttamente e non introduce workflow,
scheduler, servizi, dipendenze o impostazioni di conservazione aggiuntivi.

## Prove e report

Nel percorso temporaneo `--output` sono prodotti:

- `sources/happings-pages.json`: HTML, hash, URL, esiti e contesto della ripresa;
- `happings-enrichment.json`: stato, proposte e riscontri per campo;
- `HAPPINGS_ENRICHMENT.md`: riepilogo leggibile;
- `checkpoints/happings_enrichment.json`: contatori della fase;
- `happings-enrichment-static-guard.json`: esito del controllo dell'export;
- `source-refresh-coverage.json`: copertura effettiva e stato delle letture.

I checkpoint usano il percorso già previsto dal workflow. HTML e prove
complete rimangono temporanei; il repository conserva codice, regole e
rapporti sintetici. I test con fixture sintetiche verificano il comportamento
del motore. I campioni reali, le date delle loro letture e gli errori di rete
sono rendicontati separatamente e non si deducono dall'esito dei test.

### Verifica dei riscontri fra origini e dei calendari

La revisione successiva supera **927 test Python**, gli **otto file di test
Node**, la build e il controllo del worker della mappa. La prova completa
dell'Autopilot riusa gli snapshot salvati, conserva tutte le **13.824 schede**
e supera i **17 controlli di rilascio**.

Sui due HTML reali già disponibili, Venezia e Modena, restano **15 proposte
di indirizzo** per le schede Happings. Il confronto produce in memoria
riscontri per **62 schede primarie e sei di altre origini**; due precedenti
abbinamenti primari sono esclusi dal controllo delle sedi concorrenti. I
valori delle sei schede secondarie rimangono intatti. Questa prova non è
una nuova lettura di rete né l'esecuzione della rotazione programmata.

Sul catalogo completo il motore ammette al confronto secondario **563
schede** attraverso **81 pagine già comprese nella rotazione primaria**.
Sono conteggi di capacità, non di fatti verificati. La copertura primaria
rimane di **9.451 schede con lettore e 4.373 senza lettore compatibile**.

Il controllo temporale comune a tutte le origini rileva **104 schede** con
limiti di calendario non rappresentati e, nella prova, ritira **215 date
calcolate da 15 schede**. Gli intervalli di mesi integralmente espressi
nella ricorrenza vengono invece rispettati. Questi risultati riguardano il
candidato di validazione; il catalogo pubblico segue il ciclo di rilascio
ordinario.

Conteggi, impronte, regressioni e limiti sono nel
[report dei riscontri e dei calendari](../reports/automation/source-corroboration-and-calendar-scope-validation-2026-10-19.json).

### Verifica dell'attivazione precedente, PR #63

La suite completa della modifica supera **877 test Python**, oltre agli
otto file di test Node, alla build e al controllo del worker della mappa.
Sono verificati anche i cicli successivi, la protezione degli interventi
umani, le date sconosciute della fonte e gli errori isolati per pagina.

Due HTML reali richiesti direttamente agli URL canonici di Venezia e Modena
sono stati confrontati con tutte le **13.824 schede**. Il parser legge
rispettivamente 110 e 69 righe. La preview individua **15 assegnazioni di
indirizzo ammissibili** (11 e 4) e 64 possibili riscontri di sede e ricorrenza.
La preview non modifica il catalogo. Gli HTML sono snapshot UTF-8 del testo
completo restituito dal connettore; quest'ultimo non espone gli header né
l'URL finale del trasporto. L'identità canonica richiesta e dichiarata
nell'HTML non viene presentata come prova di un redirect osservato.

La prova completa dell'Autopilot riusa separatamente gli snapshot ufficiali
già salvati e supera tutti i **17 controlli di rilascio**, conservando tutti
gli ID. Non contiene i due campioni Happings nel checkpoint della rotazione
odierna: nessuna esecuzione live dell'intero batch di 16 pagine è attestata.
L'attivazione della policy entra nel prossimo ciclo quotidiano esistente.

Conteggi, impronte, provenienza e limiti della verifica sono nel
[report di attivazione](../reports/automation/happings-authorized-refresh-validation-2026-10-19.json).

## Verifica storica precedente all'attivazione

La sezione seguente conserva i risultati della versione iniziale del 19
ottobre 2026, quando la fase era ancora disabilitata. Non descrive lo stato
operativo corrente.


Base del lavoro: DEV `0aa02086a59489c194bd4b3ab7746f5921b7f9a4`.
Il catalogo letto contiene **13.824 schede**, di cui **9.647 Happings**.
La famiglia di URL provinciali `ad-...` comprende **414 schede**, **236** con
indirizzo vuoto. Dopo i nuovi controlli su URL, Comune, provincia, regione e
giorno, **179** risultano eleggibili per una futura valutazione della fonte.
Eleggibile non significa indirizzo trovato o applicabile senza altre prove.

La prova completa dell'Autopilot sul catalogo reale è stata eseguita con
`--offline --today 2026-10-19`. È terminata con:

- 13.824 schede prima e dopo, nessun ID aggiunto o eliminato;
- 9.647 ID Happings protetti anche con la fase disabilitata;
- stato `disabled`, gate del registro `blocked_rights`;
- zero pagine Happings richieste e zero indirizzi modificati;
- prova finale `release_safe: true` e decisione `approved: true`;
- `has_changes: false`, firma del catalogo invariata:
  `4de17fb44655745c6a941f591c44c9ff682bff511181c4c21ab232934536fd6f`.

Questa verifica precedente non ha fatto richieste di rete a Happings e non
ha cambiato indirizzi reali. Il percorso attivo era provato con HTML e
registri simulati. In quella versione policy e registro erano ancora
disabilitati per il recupero ricorrente; lo stato operativo corrente è
descritto sopra.
