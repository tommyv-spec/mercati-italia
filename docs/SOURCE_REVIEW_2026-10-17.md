# Review fonti esterne — 17 ottobre 2026

**Ambito:** valutazione di qualità delle sorgenti, solo DEV. Nessuna nuova
scheda, calendario, geocodifica, licenza o verifica del singolo mercato viene
approvata da questa revisione. Il numero di righe di un registro posteggi
NON equivale al numero di mercati.

## Evidenza e decisioni

| Fonte e pagina primaria | Fatto osservabile al 17/10/2026 | Decisione dati |
|---|---|---|
| Regione Piemonte, [Anagrafica mercati](https://www.dati.gov.it/node/view-dataset/dataset?id=26c619d9-ecf8-4882-910e-925a4fb459ec) | Dichiarati località, tipo mercato/posteggio, giorni, cadenza e stagionalità; il **dataset** dichiara ultima modifica **2019-05-10**. Il catalogo dati.gov.it risulta aggiornato nel 2026, ma ciò NON aggiorna il dataset. Distribuzione dichiarata CC BY 4.0. | Buon schema potenziale per coprire il Piemonte, ma **solo archivio storico** finché non si trova un aggiornamento dell'editore. Non importare date od orari 2026, non considerare il catalogo aggiornato un controllo degli eventi. Endpoint SmartDataNet da riprovare in verifica bounded; se non raggiungibile mantenere stato unavailable. |
| Regione Lazio, [Censimento dei mercati giornalieri](https://dati.lazio.it/it/dataset/censimento-dei-mercati-giornalieri) | Risorsa CSV esplicitamente **Dati 2007-2013**; metadati modificati **2020-10-08**; pagina non mostra una licenza. Dati statistici su struttura/settore. | **Non idonea all'inserimento di mercati visitabili attuali.** Classificarla come fonte statistica storica, senza permessi di riuso automatico. Verificare eventuale nuova versione presso Regione/Comuni prima di riaprire l'ipotesi. |
| Comune di Pianiga, [Posteggi mercati e fiere](https://dati.veneto.it/opendata/5150_posteggi_mercati?metadati=showall) | Aggiornamento dichiarato **2026-09-07** e CC BY 4.0. Metadati riportano **133 righe**, ma **solo quattro denominazioni distinte** (tre mercati settimanali e una sagra). Campi GIORNO, INIZIO/FINE PERIODO, TIPO POSTEGGIO, TOTALE POSTEGGI; manca l'indirizzo. | **133 righe non sono 133 mercati.** Usare questo schema solo per ricercare il programma di massimo tre sedi distinte, filtrando sagre e periodi scaduti. Per pubblicare: recuperare prima indirizzi, identità stabili, calendario attuale e prove dalla pagina comunale; non moltiplicare le sedi per anno/posteggio. |
| Comune di Firenze, [Mercati Storici](https://www.dati.gov.it/node/view-dataset/dataset?id=46b622a3-6653-42c1-8ee2-c8e1181969a9) | Distribuzione georeferenziata da FeelFlorence, CC BY 4.0, data di **ultima modifica dataset catalogata 2026-09-01**; il connettore esistente mantiene precedenti dati sorgente 2023. | **Possibile aggiornamento da confrontare, non nuova verifica automatica.** Rileggere esattamente le risorse CSV/GeoJSON primarie, calcolare hash, confrontare ID e coordinate; aggiornare la data del dataset solo dopo prova sui contenuti, mai dal solo metadato/catalogo. |

## Priorità operativa

1. **Recuperare report freschi dal workflow growth-audit.** Il job del 17/10 ha letto correttamente entrambi i contratti approvati, ma il vecchio gate su `main` elencava soltanto Corciano e ha bloccato la scrittura dei report. Il nuovo validatore pin/contratti è già su DEV (PR #21); la sola correzione del workflow è in PR #22, separata dalla produzione. Non usare report risalenti al 13/10 per stimare il catalogo del 17/10.
2. **Verificare contenuto Firenze 2026.** Confrontare gli stessi file pubblicati nell'ente (date, dimensioni, ID, coordinate, diritti). Se non raggiungibili o invariati, mantenere la data sorgente precedente, senza certificare eventi.
3. **Ricerca sedi e orari originali dove mancano.** Iniziare da fonti ufficiali con orari/indirizzo e identity key chiara; classificarle per dataset, non per migliaia di singoli posteggi.
4. **Archivio Piemonte / Lazio: distinguere storico da aggiornato.** Non inferire mercati del 2026 da dataset 2019 o 2007-2013. Riusare solo per confronto o come traccia di ricerca.
5. **Check di efficacia:** variazione in schede con orari/indirizzi supportati da URL originali, meno collisioni, meno fonti scadute e nessun incremento di eventi falsamente confermati. Il totale di schede non è un indicatore sufficiente.

### Barriere di importazione

- Le pagine nazionali riportano spesso date di raccolta/metadati più recenti della distribuzione. Non usarle come date del singolo mercato.
- Nuove fonti: prima prova effettiva di licenza sul publisher e schema completo, poi contratto fonte, snapshot bounded, confronto identità, quarantena dei conflitti e passaggi QA DEV.
- Le concessioni, i posteggi, le sagre e i record per anno **non** sono mercati addizionali.
- Il riuso di dataset con licenza dichiarata va documentato nell'attribuzione. Nessun aggiornamento automatico di coordinate se non verificato, nessun forecast di aperture su fonti troppo vecchie.
- Non pubblicare modifiche su `main` o su Cloudflare produzione in base a questa nota.
