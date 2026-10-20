# Happings: risoluzione dei collegamenti comunali storici

Verifica del 20 ottobre 2026. Il cambiamento riguarda il meccanismo di acquisizione;
non contiene correzioni manuali di mercati o nuove identità.

## Problema e copertura

La ricomputazione sul catalogo di 13.824 schede trova 57 schede Happings con
Comune/provincia ISTAT coerenti e ricorrenza settimanale semplice che non entrano
nella rotazione: 15 senza alcuna risorsa provinciale nota (GO 5, TS 8, OT 2) e
42 il cui vecchio slug non prova esattamente il Comune. Sono 43 URL distinti,
letti dal catalogo esistente. Nessun URL viene costruito dal nome del mercato.

- [x] Censire tutti i 43 URL nel medesimo stato persistente.
- [x] Dare precedenza ai gruppi geografici senza risorsa nota.
- [x] Riconoscere i due redirect osservati: `town.html` → stesso `town/` → elenco provinciale.
- [x] Conservare ogni hop e continuare dal target osservato nel ciclo successivo.
- [x] Richiedere intestazione provinciale esplicita, geografia coerente e presenza del Comune/giorno nel contenuto letto.
- [x] Evitare altre letture dei vecchi URL dello stesso gruppo dopo averne provato una risorsa.
- [x] Rendere espliciti indisponibilità, layout inatteso, scope discordante e identità non provata.
- [x] Conservare la coda attraverso il publisher DEV esistente anche quando cambia soltanto lo stato.
- [ ] Eseguire il primo ciclo operativo con il nuovo risolutore dopo la normale revisione e pubblicazione del codice.
- [ ] Riesaminare le 42 identità ambigue solo quando una fonte fornisce prove sufficienti; una pagina provinciale generica non le corregge automaticamente.

## Limiti e controlli

`happings_enrichment.legacy_resolution` usa al massimo 2 slot del budget
settimanale già esistente di 16. Restano quindi 14–16 pagine provinciali nel
medesimo ciclo. Gli hop HTTP del risolutore sono manuali e consumano ciascuno
uno slot; non ci sono redirect automatici nascosti. La scadenza di avvio delle
richieste è 45 secondi, con timeout di trasporto al massimo 18 secondi.
Il ritardo minimo resta 3 secondi e rispetta eventuali limiti robots più lenti.
La stessa policy robots è riutilizzata dalla fase provinciale; resta attivo il
controllo DNS pubblico. Non è stata aggiunta un'altra fase da sette minuti,
un'altra pianificazione o un servizio esterno.

`happings-legacy-resources.json` conserva origine, prossimo URL osservato,
catena HTTP, esito, ultimo tentativo e ultima risoluzione riuscita. Un errore
non produce una data di successo o una nuova attestazione del mercato.
I canonical HTML restano distinti dagli URL finali HTTP. Il checkpoint grezzo
temporaneo permette di ripetere la prova senza nuove richieste e rifiuta
successi privi del relativo HTML e hash. La coda viene mantenuta dal prune
degli asset e può produrre un aggiornamento DEV anche a catalogo immutato.

Le risorse osservate alimentano il router esistente. Lo slug comunale esatto,
il Comune/provincia, il giorno, l'unicità della sede e i conflitti con gli
indirizzi salvati continuano a essere verificati dal lettore settimanale.
Non si riscrive `url_fonte`, non si rimappa OT verso un'altra provincia e non
si inventano orari, date, coordinate o verifiche umane.

## Prova su acquisizioni reali, ripetuta senza rete

Il report [happings-legacy-resolution.json](happings-legacy-resolution.json)
conserva URL, orari UTC, codici HTTP e hash della catena acquisita il 20 ottobre:
il vecchio URL di Trieste risponde 301 verso la variante con slash; questa
risponde 301 verso il provinciale, che risponde 200. Il corpo di 139.963 byte
ha SHA-256 `5452a6fbd04d0fdcca6a3cdcc61dc303126edf67e6aff95da77e2576aa686c8a`.
Il replay usa tutti i 13.824 record per i controlli e non effettua HTTP.

Due richieste nel primo lotto e una nel secondo risolvono la risorsa. Il parser
legge 52 righe e rende instradabili 8 schede della provincia di Trieste:
sette di Trieste e una di Muggia. **Non cambia alcun dato di mercato**: sei
schede hanno più sedi possibili, due confliggono con l'indirizzo già salvato.
Questi esiti restano casi da risolvere con prove, non diventano aggiornamenti
automatici. La preparazione della frontiera completa richiede 2,83 secondi
nella prova locale; l'intero replay, compresi confronto e guardia finale,
richiede 12,52 secondi. Sono misure locali senza rete, non una garanzia sui
tempi del sito.

I test automatici usano HTML sintetico esplicitamente etichettato e verificano
anche i redirect osservati, il limite condiviso, la ripresa interrotta, la
geografia errata, i 404, il divieto robots e la pubblicazione della sola coda.
I corpi HTML reali restano nei checkpoint temporanei, non nel repository.
