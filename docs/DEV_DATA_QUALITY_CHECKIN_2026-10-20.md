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
| Date future classificate `segnalata` o `confermata` | 0 |
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

## Check-in e criterio di completamento

- [x] Misurare il catalogo realmente pubblicato, su tutte le fonti.
- [x] Riprodurre i blocchi dei controlli finali sul candidato completo.
- [x] Correggere i consumatori mantenendo la verifica semantica delle fonti.
- [ ] Completare una nuova acquisizione HTTP nel normale Autopilot.
- [ ] Superare QA e pubblicazione con lo stesso commit DEV e gli stessi asset.
- [ ] Confrontare il manifest pubblicato e la preview con il candidato verificato.
- [ ] Misurare i recuperi effettivi e le lacune rimaste, con le stesse definizioni.

Le ultime attività si chiudono con l'ID della nuova esecuzione e gli asset
effettivamente pubblicati. Non si chiudono con un semplice merge del codice.
Il workflow MAIN esistente rimane il solo percorso di pubblicazione e conserva
la sua programmazione. Le attività sui formati e i raccordi ancora mancanti
restano nella [checklist delle fonti](../reports/automation/SOURCE_FORMAT_CHECKLIST.md).
