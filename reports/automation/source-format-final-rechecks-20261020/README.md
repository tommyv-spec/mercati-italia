# Riconfronto finale dei formati sulle prove LIVE7

Questo pacchetto applica soltanto confronti dimostrati al registro dei formati. Il codice esaminato è `37f1078c0fdef79a70e20e9ce2e3876b38742f94`; il catalogo è l’artefatto realmente pubblicato dal run `39487468359`, con 13.888 schede e manifest SHA-256 `f70dddd6664ba5dc020c2f83c465382a748231175abd2d350d660b8571dae816`. Tutto il lavoro di questo pacchetto è offline: nessuna richiesta HTTP e nessun file di catalogo prodotto modificato.

## Che cosa è stato ricontrollato

| Prova | Risultato e limite |
| --- | --- |
| Codice condiviso ed export | Confronto differenziale con i moduli precedentemente registrati a `3a4d5c7`; tutte le 13.888 schede, i 20 asset regionali e i 2.819 riscontri restano identici. Le 220 prove amministrative ISTAT sono mantenute dal nuovo normalizzatore. |
| Indice schema6 | I primi 12 campi delle 13.888 righe sono identici. La nuova colonna distingue 64 schede storiche, 93 con orari legati alle date e 13.731 ordinarie. Non modifica i fatti regionali. |
| Compatibilità di routing | 53 formati hanno il parser sorgente registrato immutato e il solo raccordo condiviso riconfrontato. Questo non equivale a una nuova lettura del contenuto. Sei di questi mantengono incompleta la precedente prova di fonte/mappatura, quindi i loro hash non sono avanzati. |
| Compatibilità dei lettori ufficiali | 33 unità, incluse quelle ausiliarie, hanno i parser sorgente invariati. Export e riscontri sono riconfrontati; per sei unità il solo `verify_static` del contratto di ammissione cambia per leggere l’indice versionato. Le funzioni di acquisizione, parsing, identità e ammissione sono AST-identiche. Un’unità ausiliaria senza prova originaria completa resta aperta. |
| Byte originali conservati | 221 risposte: 27 provinciali Happings (14 LIVE7 e 13 precedenti), 2 risposte finali comunali con 4 passaggi 301 distintamente documentati, 73 dettagli Happings (64 LIVE7 e 9 precedenti), 71 EES (60 LIVE7 e 11 precedenti), 16 CDC e 32 Citynews. Esistono più acquisizioni di alcuni URL; il report distingue tutti gli hash e usa una sola osservazione per URL nel singolo replay di associazione. |
| Associazione e salvataggio | Otto candidati di replay separati, ciascuno con tutti i 13.888 ID conservati, export schema6 e guardie applicabili. Non sono un catalogo unificato o pubblicato. I dettagli Happings vengono confrontati con `admit_new=False` contro il catalogo già pubblicato. |
| Snapshot del registro | Ritrovate le righe precedenti con hash esattamente uguale per tutti i 23 campioni cambiati. Sedici vengono ricostruiti integralmente; sette restano aperti perché le sole prove disponibili non ricostruiscono tutti i fatti e riscontri cambiati. |

L’integrazione offline completa dello stesso codice, con 17/17 controlli passati e tutte le cinque code conservate, è documentata separatamente in `reports/automation/source-quality-offline-integration-20261020.json` (commit del solo rapporto `f29d1a1`). La proposta precedente sotto `source-format-rechecks-20261020` resta conservata come passaggio condizionale, senza essere confusa con questo riconfronto definitivo.

## Nuova variante provinciale Happings

La pagina di Lucca ricevuta nel LIVE7 usa il contenitore `hpe-editorial/local-guide`. È una nuova variante DOM del formato provinciale già registrato. Il suo corpo principale separa tre unità esplicitamente attuali per località/giorno e 53 righe dichiarate storiche o da verificare.

Il parser mantiene separati gli ambiti. Solo un’affermazione di sostituzione esplicita della vecchia sede, associabile a un’unica identità sull’intero catalogo, consente un avviso di conflitto. Sui byte conservati risultano due avvisi e nessuna modifica di indirizzi, coordinate, date o verifiche. Le altre 13 pagine provinciali LIVE7 mantengono righe e metadati identici al parser precedente. Le condizioni di accettazione e i limiti sono in `lucca-dom-variant.json`; il confronto delle 60 schede associate e la prova contro alterazioni sono in `happings-lucca-layout-validation-20261020`.

Il registro aggiunge un solo campione reale già acquisito: hash, URL richiesto e finale restano quelli del checkpoint. La precisione del momento di lettura è soltanto il giorno, come nel checkpoint originale. Non sono inventati un’ora di lettura o i codici dei passaggi intermedi. La data editoriale della pagina non diventa una verifica dei mercati. I due avvisi devono ancora passare attraverso il successivo run reale DEV.

## Esito della checklist

| Contatore | Prima | Dopo |
| --- | ---: | ---: |
| Formati primari inventariati | 110 | 110 |
| Formati con lettura documentata | 104 | 104 |
| Formati con confronto del campione completo rispetto al codice e allo storage registrati | 20 | 82 |
| Formati primari da riconfrontare | 85 | 22 |
| Formati con correzioni ancora aperte | 105 | 105 |
| TODO aperti | 36 | 36 |
| TODO completati | 23 | 23 |

Il significato di “campione confrontato” resta limitato al campione e al confronto dichiarato. Non certifica tutte le pagine, tutti i campi, l’apertura o l’attualità di tutti i mercati. Nessuno dei TODO preesistenti cambia stato.

Restano non riconfermati gli otto formati EES senza byte specifici in questo corpus, Padova senza HTML riuscito, le sei prove originarie di fonte/mappatura incomplete e i sette snapshot non interamente ricostruiti. I sette storage sono Corciano, Milano, Roma d881, Lombardia, Firenze, Bologna e il campione provinciale Happings di Milano. Non si sostituisce il loro vecchio hash con quello nuovo per il solo fatto che il catalogo è stato esportato. `HAPP-FORMAT-04`, `HAPP-FORMAT-06` e `NC-05` rimangono aperti.

## File e riproduzione

- `review.json`: disposizione per ogni formato, hash di codice modificati, prove e limiti.
- `shared-replay.json`: compatibilità, indice6 e confronto effettivo dei regionali.
- `capture-replays.json`: richieste, URL finali, hash, byte, date originali e risultati degli otto replay.
- `storage-comparison.json`: vecchi snapshot esatti, differenze per campo, ricostruzioni e blocchi residui.
- `audit.json` e `CHECKLIST.md`: inventario derivato dal ledger aggiornato sul LIVE7.
- `replay.py`, `storage_check.py`, `package_report.py`: procedure offline con i percorsi degli artefatti indicati; richiedono che i checkpoint e gli snapshot citati siano disponibili.

```sh
PYTHONDONTWRITEBYTECODE=1 python reports/automation/source-format-final-rechecks-20261020/replay.py all \
  --repo /workspace/scratch/81e91a77b820/mercati-format-rechecks-final \
  --manifest /tmp/vintagery-live-39487468359/candidate/public/data/v1/manifest.json \
  --output /tmp/source-format-final-rechecks-20261020
PYTHONDONTWRITEBYTECODE=1 python reports/automation/source-format-final-rechecks-20261020/storage_check.py
PYTHONDONTWRITEBYTECODE=1 python reports/automation/source-format-final-rechecks-20261020/package_report.py
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend:backend/tests python -m unittest test_source_format_audit -q
```

Un successivo run può introdurre fatti nuovi e rendere nuovamente necessario il confronto di uno snapshot. Questo comportamento è intenzionale: un hash cambiato non costituisce da solo una prova di qualità.
