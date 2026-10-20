# Revisione delle code automatiche — 20 ottobre 2026

## Ambito e prove

Analisi locale del codice a partire da `140119f` e dello stato pubblicato in
`/tmp/vintagery-dev-39483325379/public/data/v1/manifest.json` (13.856 schede).
Le integrazioni Citynews successive sono gestite dal ramo di integrazione del
parent; il controller e il trasporto erano già disponibili per questa review.
Nessuna nuova richiesta HTTP. Inventario dettagliato iniziale in
`/tmp/vintagery-source-rotation-inventory-20261020.json`; replay del difetto
precedente in `/tmp/editorial-retry-baseline-repro-20261020.json`.

Il workflow MAIN salvato in `/tmp/happings-main-autopilot.yml` è giornaliero
alle 04:17 UTC. Esegue il codice DEV fissato al commit selezionato e conserva
il limite di 20 minuti. Le code pubbliche avanzano solo quando il candidato
supera le guardie e viene pubblicato; un candidato scartato non costituisce
un avanzamento della coda pubblicata. Il resume rilegge prove già acquisite,
non significa una nuova lettura della fonte.

## Meccanismi e tempi effettivamente dimostrabili

| Gruppo | Inventario / limite | Rotazione e ritenti | Limite della prova |
| --- | --- | --- | --- |
| Happings, listati provinciali | 95 risorse collegate a 8.217 schede primarie; massimo16 pagine, ridotto dalle richieste del resolver legacy | Selezione deterministica per data anche quando i campi sono già pieni; con inventario fisso e16 slot servono6 batch, con14 slot7 batch | È copertura delle pagine selezionate, non prova che ogni riga si associ a un'identità né garanzia di lettura riuscita. I fallimenti non hanno una coda persistente propria: ritornano con la rotazione. |
| Happings, URL legacy | 43 origini persistenti nel campione;2 richieste/hop e45 secondi per ciclo | Prima i Comuni senza provincia provata; poi catene osservate e tentativi più vecchi. Errori7 giorni; layout/identità irrisolti30 giorni; redirect osservati riprendono dal passo successivo | Due richieste non equivalgono a due pagine finali. Il resolver prova il trasporto e la risorsa provinciale, non riscrive da solo i dati dei mercati. |
| Happings, dettagli | 2.196 URL di dettaglio e14 sitemap; massimo128 risorse,420 secondi, oltre al controllo robots | Rotazione persistente9 slot con quote per schede catalogate, possibili mercati e pagine mai lette; successi nuovamente eleggibili dopo7 giorni; errori1/2/4/7 giorni | I7 giorni sono eleggibilità, non un periodo garantito: persino con il tetto teorico occorrono almeno18 batch per2.196 URL. Al snapshot90 dettagli erano letti e2.106 no; i14 altri elementi letti sono sitemap. Il trasporto preesistente ha timeout per richiesta, non interruzione assoluta dell'intero DNS/body. |
| Eventi e Sagre | 2.197 schede,1.853 URL primari;64 dettagli,210 secondi | Prima della correzione19 tentati,11 letti,8 errori; i fallimenti aspettavano il completamento dell'intera prima scansione. La correzione introduce ritenti persistenti1/2/4/7 giorni e quota1/4 quando ci sono anche pagine nuove |29 batch è solo il limite inferiore a64 pagine sempre riuscite; il primo ciclo reale si è fermato a19 tentativi in211,21 secondi. Il nuovo limite temporale interrompe il worker, senza aumentare budget o frequenza. |
| Cose di Casa |432 schede,425 URL;16 dettagli,90 secondi |16 letti e409 ancora non letti; stessa correzione del controller EES. Opera in parallelo su un altro host con coda e checkpoint separati |27 batch è il minimo teorico. Le fonti con edizioni archiviate o date discordanti mantengono queste qualifiche; leggere oggi non rende attuale un'edizione vecchia. |
| Roma d881 |70 schede, un dataset completo | Se esistono identità d881, ogni ciclo legge metadati e distribuzione CSV; fallimento conserva i dati ed è ritentato nel ciclo successivo | Nessuna generazione di nuove date o nuovi ID. Data `AGGIORNATO` della riga separata dai metadati del dataset e dall'ora di lettura. Trasporto non convertito dal presente intervento. |
| Citynews |62 schede con57 URL ammessi,28 host;8 HTTP totali compresi robots,60 secondi | Coda persistente, robots e pacing per host; trasporto interruptible già rivisto. Richieste non iniziate non completano URL; checkpoint inflight verificati | I fallimenti terminali attuali attendono il giro della coorte, senza backoff1/2/4/7 dedicato.8 HTTP non equivalgono a8 dettagli: ogni nuovo host consuma un robots. Nessun periodo esatto sostenibile deducibile dal solo tetto. |
| Feed strutturati abilitati | Lombardia, Milano, Firenze, Corciano, più contratti registrati | Ogni feed abilitato è acquisito a ogni ciclo; retry limitato, mantenimento del catalogo precedente se la fonte manca | Disponibilità dell'endpoint e validità delle identità restano controllate. Un download riuscito non riscrive la data editoriale del dataset. |
| Pagine comunali contrattualizzate | Due pagine Bassa Romagna attive nel registro | Batch bilanciati per host, tetti globali/per-host; con l'inventario attuale entrambe sono eleggibili ogni giorno | Le altre pagine comunali e tutti gli altri formati web non diventano supportati per somiglianza del dominio. |

I gruppi non sono sommabili come schede distinte: alcuni sono risorse, alcuni
URL e altri righe catalogo. Le pagine Happings provinciale non coprono
automaticamente tutte le9.679 schede aventi Happings come fonte primaria.
Formati non riconosciuti, ricorrenze incomplete, geografie in conflitto e
associazioni ambigue restano nei report e nelle TODO specifiche.

## Difetto riprodotto e correzione delimitata

Nel run39471001816 tutti gli8 errori EES registrati erano effettivi tentativi
di rete con `error_type=URLError`. Il report non memorizzava `reason`, errno o
stato HTTP: non è possibile attribuirli onestamente a DNS, TLS, timeout o
blocco del sito. Robots e11 pagine dello stesso host erano stati letti.

La coda precedente escludeva quegli8 URL il giorno successivo mentre lasciava
1.834 pagine mai tentate. Il nuovo selettore li rende eleggibili il21ottobre,
con alternanza persistente3 tentativi ordinari /1 retry. Su64 slot seleziona
gli8 errori e56 URL ordinari; sui primi19 slot5 errori e14 ordinari. Sono
simulazioni di selezione sulla vera coda, non nuovi esiti di lettura.

Il secondo difetto riprodotto completava un URL quando il tempo scadeva
durante l'attesa prima dell'HTTP: nel caso dimostrato era stato letto soltanto
robots, ma lo stato dichiarava il dettaglio `unavailable` e il ciclo completo.
Ora nessun tentativo viene contato prima della partenza effettiva; l'eventuale
scrittura checkpoint che esaurisce il tempo viene annullata. Una richiesta
iniziata e poi interrotta resta `inflight`, incompleta, eleggibile dal giorno
successivo. La prova dei singoli hop impedisce di trasformarla in un errore
terminale o di inventare un redirect.

Il nuovo worker EES/CDC racchiude DNS, TLS e lettura body nel tempo restante.
Timeout e interruzioni terminano e raccolgono il processo; l'interruzione
originale è rilanciata. Host, identità numerica EES e catene CDC restano
vincolati agli URL primari ammessi. Non aggiunge dipendenze, host, nuovi ID,
budget o chiamate di rete a questo replay.

## Persistenza e osservabilità

I nomi pubblici restano `eventiesagre-detail-state.json` e
`cosedicasa-detail-state.json`. `validate_state` accetta lo stato storico v1 e
produce v2 con `failure_count`, `next_retry_on`, `last_error_code`; conserva
date di lettura, hash, numero tentativi e data del contenuto. Il vecchio
`URLError` non genera una diagnosi nuova né uno streak supposto. Il checkpoint
runtime passa a v2 con l'elenco dei singoli HTTP; non si reinterpreta un
checkpoint v1 privo di tale prova. I report pubblici restano schema1.

Il report espone `retry_pending`, `retry_due`, la sequenza1/2/4/7 e la quota.
Il limite45 giorni è un allarme di ritardo, non una promessa di freschezza.
I ricevuti `read_on`, `published_at`, `modified_at`, le edizioni e la verifica
umana continuano a essere dati separati. Nessuna lettura aggiorna da sola il
timestamp dei fatti o conferma un'apertura.

## Limiti residui da tenere visibili

- L'obiettivo «tutte le fonti» non è una proprietà dimostrata da queste code:
  l'inventario completo contiene ancora altri formati e fonti non instradati.
- La pubblicazione giornaliera può fallire per guardie successive o tempo
  totale; in tal caso il ciclo pubblico non avanza. Nessuna guardia è stata
  abbassata da questa correzione.
- Happings provinciali e Citynews non hanno lo stesso backoff dedicato del
  nuovo controller EES/CDC; sono comportamenti residui documentati, non
  modifiche incluse in questo intervento.
- Il tetto per URL, i diversi robots e i tempi reali fanno variare la durata
  di un giro. Non esiste una base per dichiarare «tutto aggiornato» o una
  garanzia settimanale.

File centrali del codice consultati: `backend/eventiesagre_detail_refresh.py`,
`editorial_transport.py`, `existing_source_refresh.py`, `autopilot.py`,
`happings_source_enrichment.py`, `happings_detail_discovery.py`,
`happings_legacy_resources.py`, `citynews_detail_refresh.py`,
`source_roma_d881.py`, `publisher_refresh.py`, `source_freshness.py`.
