# Recupero e aggiornamento automatico delle fonti

## Obiettivo e criterio di riuscita

La qualità va migliorata nel meccanismo che legge e aggiorna il catalogo. Un
elenco di correzioni per singolo mercato non soddisfa questo obiettivo.

La prova richiesta è un ciclo completo: prima lettura della fonte, estrazione
dei suoi mercati, collegamento delle identità, acquisizione dei campi mancanti,
seconda lettura con contenuto modificato, aggiornamento dei valori gestiti,
esportazione con prove ancora valide. Un problema in una fonte deve lasciare
visibili il suo stato e i mercati esistenti, senza trasformare l'esecuzione
riuscita in una dichiarazione di correttezza dell'intero catalogo.

## Meccanismi disponibili

| Percorso | Unità di lavoro | Aggiornamento successivo |
|---|---|---|
| Adapter ufficiali esistenti | Dataset completo e ID del publisher | Confronto dei record della stessa fonte; controlli indipendenti su tutti i campi normalizzati |
| Arricchimento MERCap | Dataset regionale completo; sede/giorno oppure Comune/provincia/giorno univoci | Recupera sedi mancanti e orari, poi aggiorna i campi assegnati dal motore alla stessa identità fonte |
| Contratti CSV e JSON approvati | Risorsa e schema dichiarati nel contratto | Nuovi inserimenti e aggiornamenti dei tre campi gestiti dello stesso record fonte |
| Pagine comunali con blocchi Quando/Dove/Orari | Pagina intera, con limiti di struttura e cardinalità | Aggiorna i campi assegnati dal lettore quando cambia la stessa riga fonte |

`publisher_page_parser.py` è un parser puro, senza rete o scritture. Il
contratto descrive struttura della pagina, territorio, tipo di mercato e
limiti attesi. Non contiene ID di schede del catalogo, indirizzi, orari o
valori da applicare. Le prime due pagine configurate sono gli elenchi dei
mercati settimanali e dei mercati contadini della Bassa Romagna:

- https://www.bassaromagnamia.it/poitofintrests/mercati-settimanali-6/
- https://www.bassaromagnamia.it/poitofintrests/mercati-del-contadino/

Le fixture HTML conservano i fatti necessari a provare l'intero formato,
inclusi frazioni, sedi alternative, orari stagionali e cadenze quindicinali.
La loro provenienza distingue l'impronta della fixture dall'impronta della
pagina originale. Le date di contenuto osservate sono rispettivamente
23 marzo 2026 e 27 gennaio 2026: una lettura il 19 ottobre non le rende
contenuti aggiornati in ottobre.

## Identità e prove dei campi

Un riscontro lega un valore preciso a identità del mercato, editore, URL,
riga fonte, data di lettura, data dichiarata del contenuto e impronta.
`impronta_tipo` distingue i byte HTML dal JSON normalizzato del publisher.
Il frontend mostra quali campi hanno quel riscontro e le due date separate.
Questo non conferma un'apertura futura e non certifica un punto sulla mappa.

`campi_gestiti` e `gestore_campi` indicano soltanto valori realmente assegnati
dal motore. Trovare nella fonte un valore già presente aggiunge una prova,
ma non permette di prendere il controllo di una modifica preesistente.

La sostituzione di un campo gestito richiede tutte queste condizioni:

1. Identità fonte e mercato ancora compatibili, senza ambiguità di sede,
   Comune, provincia, giorno o tipo di mercato.
2. Valore corrente identico al valore precedentemente assegnato.
3. Nuova lettura successiva, impronta diversa e data del publisher non regredita.
4. Nessuna prova concorrente di altra fonte e nessuna verifica individuale
   che l'aggiornamento renderebbe obsoleta.
5. Per le sedi, nessun punto preciso relativo alla precedente ubicazione
   lasciato utilizzabile come se rappresentasse quella nuova.

Il cambio conserva una cronologia limitata delle prove precedenti. Se una
nuova versione contraddice un valore che non può essere sostituito, il valore
rimane e il report registra il conflitto; viene ritirata solo la precedente
prova contraddetta della stessa fonte. Le prove di altre fonti restano.

Lo schema attuale registra la lettura per giorno: due contenuti diversi letti
lo stesso giorno non stabiliscono un ordine verificabile per un aggiornamento
gestito. Il caso rimane in revisione. La rilettura identica conserva la
proprietà del campo, e non può abbassare la data del contenuto già documentata.

Il confronto fra ID diversi non usa soltanto nome e via. Richiede anche
provincia, categoria, stessa fonte e ricorrenza settimanale completa.
Schede con prove o cancellazioni valide restano separate nella deduplicazione.
L'esportazione ricontrolla che ogni prova appartenga ancora all'identità e ai
valori della scheda finale.

### Sedi mancanti dal dataset completo MERCap

Il percorso aggiuntivo `comune_provincia_giorno_univoco` riguarda mercati
ordinari misti con ricorrenza annuale settimanale esplicita. Richiede una sola
riga compatibile per Comune, provincia e giorno nell'intera fonte. I campi raw
devono provare la cadenza, i dodici mesi di attività e la presenza di entrambi
i settori merceologici. Il solo nome generico della scheda non è sufficiente.

Il controllo include anche le righe escluse dall'importazione: una sede
stagionale, un'identità incompleta o un giorno sconosciuto possono rendere
ambiguo il collegamento. Il raw viene riconvertito e confrontato con tutti i
campi del checkpoint normalizzato usati nella decisione. Nella lettura reale
del 19 ottobre questo significa 1.453 righe controllate, comprese 93 non
importate dal normalizzatore, e 1.360 identità fonte normalizzate.

Il motore sostituisce soltanto indirizzi assenti o segnaposto enumerati come
“centro storico”. Indirizzi brevi ma reali, valori umani, sedi discordanti e
coordinate precise sono protetti. Le coordinate possono escludere un
collegamento; non provano da sole l'identità e non vengono riscritte.

Una ricorrenza già presente può ricevere una prova senza cambiare il testo
soltanto se coincide con una delle due rappresentazioni deterministiche del
giorno dichiarato dalla fonte. Non acquisisce per questo la proprietà del
campo e non diventa una conferma di apertura.

`autopilot.py` conserva `sources/lombardia-raw.json` dalla stessa chiamata che
produce le osservazioni. Il checkpoint lega impronta del JSON del publisher
e impronta del feed normalizzato. Il riavvio conserva la data originale e
non effettua una seconda lettura. Un vecchio checkpoint senza raw mantiene
compatibile il precedente percorso sede/giorno, ma non abilita il nuovo
collegamento per unicità. Un checkpoint presente ma incoerente blocca il ciclo.

Il controllo delle contraddizioni segue il codice ufficiale anche quando la
nuova versione non soddisfa più il vecchio collegamento. Cambio esplicito di
giorno, stagione, tipo o sede può ritirare i riscontri precedenti. Se una sede
nuova è trattenuta per conflitto geografico, la prova della sede vecchia non
continua a risultare attuale. Il ritiro richiede una lettura completa successiva,
un'impronta diversa e una data contenuto non regredita. Conserva i campi e le
prove indipendenti non contraddetti. Assenza del codice e indisponibilità della
fonte non dichiarano la chiusura del mercato.

## Date, aggiornamento e calendario

- `importato_il`: quando il nostro processo ha importato il record.
- `fonte_letta_il`: quando è stata effettivamente letta la fonte.
- `fonte_aggiornata_il`: data del contenuto dichiarata dalla fonte, quando
  attribuibile; non viene ricavata da un'importazione recente.
- `verificato_il`: verifica individuale già documentata; i lettori non la inventano.

`source_freshness.py` ammette un ripiego sui vecchi timestamp soltanto per
adapter di dataset già revisionati, con URL e identità riconosciuti. Non
attribuisce questa semantica ai timestamp legacy generici.

Il rinnovo delle previsioni richiede una ricorrenza esplicita e un'età fonte
documentata. Con età ignota non estende le vecchie previsioni. Un riscontro
recente ed esatto del campo ricorrenza può sostenere il rinnovo, senza
attribuire la data della fonte secondaria a quella primaria. Per questo
ripiego sono richiesti lettura entro 45 giorni e contenuto entro 180 giorni.
Le nuove date restano etichettate come previste.

Se una previsione era stata generata esplicitamente da `riscontri_campi` e
quella ricorrenza perde ogni prova utilizzabile, il motore ritira anche tali
previsioni, quando manca una fonte primaria attuale. Rimuove i metadati della
proiezione e conserva la scheda. Questo copre anche una fonte primaria con età
ignota: non può mantenere in vita una previsione derivata da una prova ora
contraddetta. Calendari legacy con altra provenienza e date riportate o
confermate conservano i loro percorsi esistenti.

Il lettore non trasforma “la mattina” in un intervallo numerico. Mantiene i
periodi degli orari stagionali. Cadenze quindicinali, alternative di sede,
marchi non identificati dalla pagina e ambiguità territoriali impediscono
un collegamento settimanale automatico. Una fonte che omette una scheda non
prova che il mercato abbia chiuso.

## Esecuzione ricorrente e monitoraggio

La fase è integrata in `backend/autopilot.py`, prima del rinnovo delle
previsioni, dell'esportazione e dei controlli finali. L'ordine rimane:
arricchimento della base, merge dei feed, contratti approvati, pagine fonte,
previsioni, esportazione e verifiche. Il risultato già arricchito è la base
del merge: reinserire la vecchia base sopra di esso non è un'operazione equivalente.

Il workflow esistente `market-autopilot.yml` su `main` seleziona il commit
esatto di DEV e chiama questo codice. Ha già un cron quotidiano alle 04:17
UTC; GitHub può avviarlo più tardi. L'esecuzione schedulata del 19 ottobre è
riuscita: https://github.com/tommyv-spec/mercati-italia/actions/runs/39233735947.
Questa modifica non aggiunge workflow, scheduler, servizi o dipendenze.
La pubblicazione del catalogo e dell'anteprima resta nel suo percorso di QA.

Le pagine sono selezionate con rotazione deterministica: massimo 12 per
ciclo, massimo 4 sullo stesso host. La rotazione non può lasciare una pagina
permanentemente esclusa dal limite per host. Ogni pagina viene letta una volta
per tutte le schede candidate; il lettore rispetta robots.txt, ritmo di
richiesta, limite di byte, HTTPS, destinazioni pubbliche e integrità della
risposta. Risposte troncate o struttura cambiata tengono quella fonte in revisione.

I checkpoint dei nuovi lettori conservano byte, impronta e data originale
della lettura, legati a catalogo, contratti, policy e giorno di riferimento.
`--resume` non recupera da rete uno snapshot mancante. La cache dei contratti
generici evita richieste ripetute fra profili della stessa risorsa; il vecchio
adapter specializzato Corciano mantiene un recupero separato.

L'artefatto già esistente comprende:

- `publisher-refresh.json` e guardia finale: cambi, prove, conflitti ed esiti
  delle pagine lette;
- `source-refresh-coverage.json`: tutti gli URL primari del catalogo con
  un esito esplicito di copertura;
- `market-field-quality.json`: valutazione dei tre campi su tutte le schede;
- report dei contratti generici con aggiornamenti e ritiri di prove.

Il riepilogo delle pagine confluisce in `freshness.json` e `FRESHNESS.md`,
già pubblicati dal workflow. La firma del catalogo e il giorno devono
corrispondere. I lettori fermi e i conflitti entrano nell'avviso di qualità
esistente; l'approvazione tecnica del candidato non diventa un certificato
di verità per tutti i dati.

## Prima integrazione del 19 ottobre 2026

Il report aggregato è in
`reports/automation/automatic-source-refresh-validation-2026-10-19.json`.
Il replay delle letture reali salvate ha attraversato tutta Autopilot e le
guardie successive su 13.824 schede: 22 orari e 12 sedi cambiati dal codice,
nessun ID eliminato, nessuna apertura confermata. Non è un elenco di patch
manuali. Il candidato resta separato dal catalogo pubblicato: viene pubblicato
solo dal percorso ricorrente dopo la sua QA.

Una seconda versione **sintetica** del dataset MERCap ha provato il rinnovo:
22 campi gestiti aggiornati, 121 valori preesistenti conservati e le rispettive
121 prove superate ritirate; tutte le prove rimaste valide dopo l'esportazione.
I test HTML verificano lo stesso passaggio con cambio di sede e orario. I
test CSV/JSON includono anche cambio della ricorrenza e passaggio nelle
guardie di pubblicazione e storico.

Sono stati eseguiti 739 test Python, 8 file di test Node, build Vite e controllo
del worker MapLibre. Il browser locale non è stato installabile: il download
ha restituito un archivio incompleto. Dopo il merge della PR #59 in DEV,
il test mobile GitHub è passato insieme a Quality, build di anteprima e
controllo delle città revisionate. Il report aggregato conserva i link alle
esecuzioni sul commit `807c539832d057048a67e3d56694e26302e6fca0`.

Il vecchio `official-enrichment-audit.yml` è un audit precedente
all'attivazione: rifiuta per progetto una policy con arricchimento già
abilitato, condizione presente anche prima della PR #59. Il suo avvio su
push ha quindi prodotto un fallimento non applicabile alla fase attuale.
Il workflow viene mantenuto solo manuale con tutte le sue guardie; Quality
e il percorso ricorrente Autopilot continuano a eseguire i controlli correnti.
Il fallimento storico resta tale e non viene contato come test superato.

## Estensione validata sul dataset completo il 19 ottobre 2026

Il successivo intervento amplia il meccanismo MERCap alle sedi mancanti e
corregge il ritiro delle prove nei cicli successivi. Il report completo è
[`source-family-refresh-validation-2026-10-19.json`](../reports/automation/source-family-refresh-validation-2026-10-19.json).
La verifica finale usa le letture reali già salvate il 19 ottobre e conserva
le loro date originali; il dataset Lombardia dichiara contenuto del 13 ottobre.
Non è una nuova lettura della rete e il candidato non è stato pubblicato.

| Risultato del ciclo completo | Quantità |
|---|---:|
| Schede iniziali e finali, con gli stessi ID | 13.824 |
| Sedi recuperate tramite il dataset completo MERCap | 229 |
| Di cui indirizzi vuoti / segnaposto vaghi | 211 / 18 |
| Righe ufficiali distinte dietro le 229 sedi | 164 |
| Altre sedi recuperate dai due elenchi HTML già integrati | 12 |
| Totale valori di indirizzo cambiati nel candidato | 241 |
| Orari aggiunti da MERCap | 251 |
| Ricorrenze esistenti corredate di un riscontro MERCap | 229 |
| Coordinate, array di date o verifiche individuali modificati | 0 |

I 251 orari comprendono i 22 già recuperabili dal percorso sede/giorno e
229 dal nuovo collegamento univoco. I 372 record legacy toccati dal passaggio
MERCap comprendono anche 121 orari preesistenti soltanto riscontrati, senza
acquisirne la gestione. I conteggi riguardano schede: più schede legacy possono
riferirsi alla stessa riga ufficiale e non vengono fuse da questa modifica.

Sull'intero candidato gli indirizzi vuoti passano da 3.429 a 3.214, le sedi
vaghe enumerate da 2.495 a 2.469 e gli orari assenti da 10.853 a 10.602.
Le due pagine HTML mantengono quattro conflitti di orario in revisione.

La prova indipendente della **lettura successiva sintetica**, eseguita su una
copia dell'intero candidato con date di test del 20 ottobre, ha due casi:

- Cambiano solo gli orari nella fonte: 251 valori gestiti aggiornati, 121
  valori preesistenti conservati e le loro prove contraddette ritirate.
- Cambiano sede e orari: 229 sedi e 229 orari gestiti aggiornati. Vengono
  inoltre ritirati 31 vecchi riscontri sede/giorno legati alle righe ufficiali
  spostate, mantenendo i valori che il motore non può sostituire.

In entrambi i casi rimangono tutti gli ID, le prove di altre fonti e lo storico
delle modifiche autorizzate. Nessun riscontro invalido sopravvive all'export;
ripetere lo stesso ciclo lascia il risultato identico. Le 1.502 potature di
date trascorse nell'export al 20 ottobre coincidono con un controllo che cambia
soltanto il giorno di riferimento: non sono cambiamenti introdotti dalla fonte.
I valori sintetici non sono dati reali e non sono stati pubblicati.

La suite finale comprende **784 test Python**, **8 file di test Node**, build
Vite e controllo del worker MapLibre. Il replay dell'intera Autopilot supera
**tutte le 17 guardie di rilascio**, con indice compresso di 406.328 byte e
firma `f7573e34bcc87d7a0fe7448853909e062db6e60d0959ea3d29af759a17652bd4`.
I test includono anche cambi di giorno e stagione, perdita delle prove,
previsioni da ritirare, coordinate precise protette, checkpoint incoerenti,
contratti disabilitati senza letture e tabelle HTML non supportate.

La misura della qualità rimane distinta dall'esito dei test: **1.512 schede**
hanno almeno un riscontro recente e **1.015** lo hanno per tutti e tre i campi
sede, orario e ricorrenza. Le soglie sono lettura entro 45 giorni, contenuto
entro 365 giorni per la sede e 180 per orario e ricorrenza. Questi riscontri
non verificano individualmente le aperture future. L'integrazione del codice
su DEV permette al workflow quotidiano esistente di applicare il meccanismo
alle proprie letture dopo la QA; non modifica da sola il catalogo pubblicato.

## Copertura da completare per famiglie di fonti

Nel catalogo di partenza ci sono 5.752 URL primari, 72 domini e 87 etichette
di fonte. Il report corretto classifica 1.219 schede per gli adapter ufficiali
configurati, 39 per il contratto generico Bologna, 9.647 schede Happings con
arricchimento disabilitato dal proprio gate e 2.919 con formato primario ancora
da integrare. La prima versione contava solo gli URL restituiti dagli adapter
nel ciclo e ometteva i contratti generici. La copertura ora rimane riconosciuta
anche quando la lettura della fonte non riesce; disponibilità, disabilitazione
e formato mancante hanno esiti distinti. Dettagli e limiti dei timestamp dei
contratti sono in `docs/SOURCE_READER_COVERAGE.md`. Sono stati aggiunti inoltre
i due elenchi primari supplementari descritti sopra. I conteggi di copertura
degli URL non sono conteggi di mercati individualmente verificati, né includono
tutti i riscontri ottenuti da fonti secondarie indipendenti.

Per ampliare la copertura si aggiunge o corregge un contratto per la fonte o
per il formato, con una pagina/dataset completo e test delle sue variazioni.
Non si aggiunge una voce di correzione per ogni mercato. Un formato non
supportato deve rimanere visibile nella coda; non va dichiarato aggiornato.
Il blocco Happings già presente resta nel suo percorso dedicato e non può
essere aggirato da un contratto del nuovo lettore.

Questa è una base operativa verificata per l'aggiornamento automatico. La
copertura di tutte le fonti e la correttezza attuale di ogni singola apertura
non sono ancora dimostrate.
