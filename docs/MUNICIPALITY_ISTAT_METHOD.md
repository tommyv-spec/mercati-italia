# ISTAT 2026 — riconciliazione Comuni, calendario e provenienza

Data fonte: 21 febbraio 2026. Fonte originale:
https://www.istat.it/storage/codici-unita-amministrative/Elenco-comuni-italiani.xlsx

SHA-256 dell'XLSX letto direttamente:
83842076860450f7e482daecea6b7a769f5f93d0bf5b0d48802b44896d7a26d5

Fonte informativa: https://www.istat.it/classificazione/codici-dei-comuni-delle-province-e-delle-regioni/
Licenza dichiarata: CC BY 4.0 (attribuzione a ISTAT).

## Prova manuale eseguita prima degli script

- 7.894 Comuni ISTAT e 13.779 schede originali DEV.
- 52 città anomale identificate da controllo reale.
- Il nome Castiglione Messer Marino era stato contaminato da testo su Celenza sul Trigno: non è valido dedurre automaticamente il giorno da un blocco che parla di due mercati.
- NA era stato usato come città per Somma Vesuviana: NA è la Provincia, verificata con ISTAT e titolo.
- Piazza Brembana e Piazza al Serchio sono Comuni veri, non nomi di indirizzo.
- Castegnero Nanto è incluso nella versione 2026; non usare elenchi storici non versionati.

Il riferimento canonico con soli Comuni, Province e Regioni si trova nel file
backend/data/istat-comuni-2026.json. Non serve scaricare l'XLSX a ogni
run: una revisione futura richiederà prova originale, nuovo hash, test e policy.

## Regole conservative

- Il Comune suggerito deve corrispondere a ISTAT nella Regione e Provincia della scheda.
- La ricostruzione deve essere supportata anche dal titolo e dallo slug originale; nessuna correzione fuzzy a prescindere dalla fonte.
- Conservare la città, il titolo e la ricorrenza precedenti nei campi di provenienza.
- Se il testo sorgente contiene mercati/località concatenate, cancellare soltanto le previsioni non provate: non inventare una ricorrenza.
- Non cambiare ID, coordinate, indirizzi, stato, fonti o verifiche documentate.
- Non correggere automaticamente mercati già verificati da esseri umani oppure esplicitamente confermati.
- Massimo 60 città e 80 calendari da sistemare per run; un'anomalia superiore blocca tutto.
- I 20 casi residui rimangono in revisione, non vanno eliminati o trattati come città attendibili.

## Numeri del primo audit integrale

Verifica GitHub Actions:
https://github.com/tommyv-spec/mercati-italia/actions/runs/38257567252

- 32 località supportate da Comune/Provincia ISTAT e titolo originale.
- 18 titoli contaminati migliorati per leggibilità.
- 19 schede con calendario contaminato messe in quarantena.
- 331 date future previste non supportate sospese.
- Località sospette scese da 52 a 20.
- Tutte le 13.779 schede e gli ID mantenuti.
- Zero falsi appuntamenti confermati, zero verifiche umane inventate.
- Controlli di release, sicurezza, JavaScript e browser Playwright mobile superati.

## Script, QA e automazione futura

- backend/municipality_reconciliation.py — pura trasformazione opzionale.
- backend/municipality_release_guard.py — confronto field-by-field di
  tutti gli ID originali e verifica di ogni modifica consentita.
- backend/tests/test_municipality_reconciliation.py e
  backend/tests/test_municipality_release_guard.py — casi reali e negativi.
- .github/workflows/municipality-reconciliation-audit.yml — prova integrale
  su GitHub Actions in ambiente isolato, senza pubblicare.
- .github/workflows/market-autopilot.yml — unico flusso giornaliero DEV.
- backend/autopilot_history.py — conserva metriche aggregate per 400 run.

Re-esecuzione offline:
    python -m unittest discover -s backend/tests -q
    python backend/autopilot.py --offline --output audit-offline

Il primo run abilitato in DEV deve ridurre le 52 località anomale a 20.
I run seguenti devono essere idempotenti: zero nuove correzioni quando il
catalogo rimane invariato; nessuna data sospesa deve riapparire in automatico.
Tutte le previsioni residue sono appuntamenti previsti, non conferme reali.

## Provincia amministrativa da Comune e regione esatti

Il ramo `province_reconciliation.py` riusa lo stesso riferimento ISTAT già
versionato. Confronta il Comune già salvato con l'unico Comune corrispondente
nella regione già salvata; non ricostruisce nomi, quartieri o ex Comuni e non
usa coordinate, indirizzi, vicinanza o inferenze da una pagina editoriale.
La corrispondenza ammette soltanto la normalizzazione tipografica già usata
nel catalogo (maiuscole, accenti, spazi e punteggiatura).

Il controllo fissa sia l'hash XLSX originale sia l'hash canonico dell'intero
JSON estratto (`6e94770332bd5d979dabfb8f9f3cefd714712912cc5543f94a5688fbdd772a14`).
Una modifica alla tabella con metadati e hash XLSX copiati non supera il gate.
La verifica HTTP del 20 ottobre 2026 ha letto nuovamente il file ufficiale:
risposta 200, 1.229.843 byte e SHA-256 identico al pin. La data di lettura
rimane distinta dalla revisione ISTAT del 21 febbraio 2026. La prova e i
risultati dei replay sono in
`reports/automation/source-format-audit-2026-10-20/istat-province-replay.json`.

La sola sigla non vuota e discordante può cambiare. Il record conserva una
`riconciliazione_provincia` amministrativa con ID, Comune e regione invariati,
sigla precedente, sigla ISTAT, Comune canonico, fonte, data del riferimento
e i due hash. Non si aggiunge una data di lettura recente, una verifica umana
o una conferma del mercato. Nessun indirizzo, orario, calendario, nome o GPS
viene modificato da questa operazione.

Le schede con ricevute di campo, calendari o evidenze editoriali, eccezioni,
identità ufficiali, prove di ricostruzione geografica o verifiche umane
preesistenti restano in revisione: le prove legate alla vecchia provincia
non vengono cancellate, ricopiate o rifirmate.

Le correzioni città/calendario esistenti consumano per prime il budget
complessivo, che rimane **80 record per esecuzione**. Gli eventuali slot
residui sono assegnati alle province ordinate per ID stabile. Le correzioni
pubblicate escono dall'insieme pendente; il ciclo successivo prosegue dal
catalogo pubblicato, senza whitelist di mercati o nuova coda. `province_fixed`,
`province_pending` e `province_protected` sono registrati nel report e nello
storico dell'automazione.

Il gate intermedio ricalcola dalla tabella pinned sia tutti i valori sia la
selezione entro budget. L'export conserva soltanto prove amministrative valide
per l'esatta identità esportata. `municipality-static-guard.json` verifica sul
catalogo finale che le province non siano state cambiate da una fase successiva
e che ogni prova amministrativa sia rimasta integra. I gate MAIN esistenti
continuano a importare il checker da DEV; non sono modificati.

Questa correzione non autorizza l'uso di una pagina Happings di un'altra
provincia. Il router conserva tutti i controlli su URL, Comune, giorno e sede.
Il controllo read-only del candidato 39465324614 (13.856 schede) ha trovato
220 province discordanti senza prove preesistenti: 216 Happings, 3 Milanopocket,
1 Sagreumbre. Il sottoinsieme Happings con nome/giorno già ammessi è di 215;
solo 44 diventano instradabili dal router invariato. Gli altri 171 richiedono
ancora una risorsa fonte o una prova di affiliazione adeguata. Instradabilità
non significa che siano stati recuperati nuovi indirizzi o orari.
