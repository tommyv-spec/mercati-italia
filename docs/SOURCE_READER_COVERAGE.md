# Copertura dei lettori e disponibilità delle fonti

Verifica locale del 19 ottobre 2026, base DEV `0c76a08`.

## Correzioni del meccanismo

Il report `source-refresh-coverage.json` distingueva i formati supportati usando
soltanto gli URL restituiti dagli adapter nel ciclo corrente. Questo lasciava
fuori Bologna, che viene elaborata dal contratto generico, e faceva sembrare
prive di lettore le fonti temporaneamente irraggiungibili.

La copertura ora deriva anche dai contratti normalizzati, dalla policy dei
singoli adapter e dai contratti CSV/JSON con il loro registro di ammissione.
Gli URL che identificano solo un host richiedono anche il prefisso dell'identità
fonte; una qualsiasi pagina sullo stesso dominio non diventa supportata.

Ogni risorsa mantiene separati:

- `mode`: percorso previsto, contratto disabilitato, approvazione assente/non
  valida oppure formato ancora da integrare;
- `source_layout_status`: supporto del formato, disabilitazione, necessità di
  approvazione o assenza di supporto;
- `source_read_status`: esito osservato nel ciclo, per esempio `unavailable`,
  `resumed_checkpoint` o `not_observed`;
- `readers`: tutti i percorsi configurati quando più lettori coprono lo stesso URL.

Un formato supportato non significa che la lettura sia riuscita o che i campi
di tutti i suoi mercati siano stati verificati. L'esito di un contratto generico
si collega al report solo quando coincidono contratto, registro e giorno.
I riepiloghi restano nello stesso artefatto e nel report quotidiano esistente.

Il dispatcher generico ora rispetta anche `raw_profiles[].enabled`: un profilo
disabilitato non legge la fonte né il suo checkpoint e non modifica il catalogo.
Il suo esito è `source_contract_disabled`. Il numero `source_contracts_active`
conta solo i profili realmente abilitati; `source_contracts_approved` conserva
il totale dei certificati presenti. Le guardie di rilascio, export e città
controllano questa distinzione. Disabilitare un profilo non permette di ignorare
un registro mancante o un fingerprint di approvazione incoerente.

## Misura sull'intero catalogo locale

La firma del catalogo esaminato è
`4de17fb44655745c6a941f591c44c9ff682bff511181c4c21ab232934536fd6f`.
La prova ha simulato l'indisponibilità degli adapter per verificare che il
formato resti riconosciuto. Non ha eseguito richieste alle fonti.

| Disposizione | Schede |
|---|---:|
| Adapter ufficiale configurato | 1.219 |
| Contratto generico attivo Bologna | 39 |
| Happings con arricchimento disabilitato | 9.647 |
| Formato primario ancora da integrare | 2.919 |
| Totale | 13.824 |

Le 1.219 schede degli adapter sono 1.128 Lombardia, 85 Milano, 4 Firenze e
2 Corciano. Il contratto generico Corciano copre anch'esso quelle due schede:
non sono contate due volte. Le risorse primarie sono sempre 5.752 su 72 domini.
Nessun campo o ID del catalogo è stato modificato da questa misura.

## Contratti già approvati e limiti delle date

I due contratti generici sono già attivi; non esistono altri contratti CSV/JSON
approvati nel registro da accendere senza una nuova revisione della fonte.

| Contratto | Risorsa completa già osservata | Copertura e limite |
|---|---|---|
| `corciano-generic-shadow` | CSV comunale di 4 righe | 2 ID presenti; 2 sovrapposizioni trattenute. Data dichiarata 7 gennaio 2026. |
| `bologna-generic-venues` | Query Opendatasoft v1 di 79 righe: 48 mercati e 31 righe escluse | 39 ID presenti; 9 righe trattenute per identità/sedi ambigue. Data contenuto 2 aprile 2025. |

Le misure delle righe provengono dai report già salvati
`reports/automation/raw-source-lifecycle.json` e dalle revisioni documentate
in `docs/SOURCE_CONTRACT_ADMISSION.md`; non sono letture eseguite da questa verifica.

- Corciano CSV: https://comune.corciano.pg.it/download/oggetto_documenti/372/1O__Oelenco-mercati-settinamanali-comune-corciano.csv
- Bologna dataset: https://opendata.comune.bologna.it/explore/dataset/mercati-e-fiere/

Entrambi i profili hanno `source_dataset_date` fisso. Il parser e i riscontri
usano quella data, anche in una successiva lettura. Per Bologna i metadati già
salvati in `source-evidence.json` continuano a riportare `data_processed`
del 2 aprile 2025: non emerge da queste prove un aggiornamento del contenuto
più recente rimasto nascosto. La modifica dei metadati del 30 settembre 2026
non sostituisce la data dei dati. Per Corciano non è disponibile in questi
report una nuova data del contenuto comprovata.

Collegare metadati dinamici del publisher ai futuri riscontri richiede un
confronto coerente con lo snapshot del dataset e un controllo delle variazioni
della fonte. Questa patch non modifica le date né i certificati. Anche il
registro di scoperta e il report storico di resa rimangono separati dal
registro di ammissione: i loro flag di revisione non sono lo stato del lettore.

## Verifica mirata

Sono passati 112 test relativi a copertura, attivazione generica, guardie delle
città, lettore delle pagine, Autopilot e storico. I nuovi casi comprendono
registro assente/non valido, disabilitazione individuale e globale, checkpoint
di una fonte disabilitata, approvazione incoerente, indisponibilità di un
adapter e conservazione delle altre fonti attive. Le prove con cambi della
policy o dei certificati usano esclusivamente fixture dei test.

Nessuna modifica a registry, policy, workflow, servizi o catalogo pubblicato.
