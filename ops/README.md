# Automazione senza GitHub Actions

Dal 25 ottobre 2026 i lavori automatici del progetto **non usano GitHub Actions**. Li esegue
`ops/runner.py` su un computer (oggi il PC del progetto, domani eventualmente un server gratuito).

## Cosa gira e quando

Ogni giorno alle 04:30 (ora del PC) l'attività di Windows **MercatiItalia-Automazione** esegue
`runner.py daily`, che lancia in ordine i lavori in scadenza descritti in `ops/workflows/`:

| Lavoro | Frequenza | Cosa fa |
|---|---|---|
| `happings-weekly-fields` | lunedì | rilegge le 107 pagine settimanali Happings e completa i campi |
| `market-autopilot` | ogni giorno | scarica le fonti ufficiali, aggiorna il catalogo DEV, ricostruisce l'app DEV |
| `data-expansion-audit`, `event-leads-daily`, `regional-field-reconciliation`, `publisher-quality-daily`, `official-source-output-qa` | ogni giorno | report di controllo nel ramo DEV |

Poi pubblica `reports/QUALITA.md`, la pagina unica sulla qualità dei dati.

- Se il PC era spento, l'attività parte appena si riaccende; un lavoro settimanale saltato viene
  recuperato il giorno dopo.
- Se un lavoro fallisce: **nessun dato parziale viene pubblicato** e si apre un'issue su GitHub
  «[Automazione locale] … — verifica richiesta», che si chiude da sola quando torna a funzionare.

## Dove guardare

- Log: `%LOCALAPPDATA%\mercati-italia\runner\logs\`
- Stato dell'ultimo giro di ogni lavoro: `%LOCALAPPDATA%\mercati-italia\runner\state.json`
- Qualità dei dati: `reports/QUALITA.md` nel ramo DEV

## Comandi

```bash
python ops/runner.py plan                 # cosa verrebbe eseguito oggi e perché
python ops/runner.py run market-autopilot # un lavoro subito
python ops/runner.py daily                # tutto ciò che è in scadenza
python ops/runner.py rehearse --code <cartella>   # prova generale di una modifica, senza pubblicare
powershell -ExecutionPolicy Bypass -File ops/install-windows.ps1   # (re)installa l'attività
```

## Prova generale prima di pubblicare una modifica

`rehearse` rigioca l'ultimo giro di `market-autopilot` di oggi (giorno UTC) con le modifiche da
provare: il codice e il catalogo di quella notte, più i commit della cartella `--code` che DEV non
ha ancora. Le fonti non vengono rilette: si riusano le letture salvate quella notte
(`--offline --resume`). Girano tutti i controlli dei job che leggono soltanto, poi l'ammissione
Happings del job di pubblicazione **senza** pubblicare. Ogni job clona una copia usa-e-getta del
repository e può spingere solo lì; `state.json` e gli allarmi non vengono toccati.

Il risultato è nel log (`…-market-autopilot-rehearsal.log`): `rehearsal PASSED` o `FAILED`, e
`catalog-diff.json` nella cartella del giro, con ogni scheda che cambia rispetto a quella notte.
Senza `--code` è un collaudo della prova stessa: deve passare con zero differenze.

Requisiti sul computer: Python 3.13 con PyYAML, Node 22, Git (con Git Bash su Windows), una chiave
SSH con permesso di scrittura sul repository e il comando `gh` collegato a un account GitHub
(serve solo per le issue di allarme).

## Spostarlo su un server Linux

Clonare il ramo DEV in `~/mercati-italia/runner/code` e aggiungere a `crontab -e`:

```
30 4 * * * cd ~/mercati-italia/runner/code && git fetch -q && git reset -q --hard origin/improve/data-quality-security-performance-2026-10-11 && PYTHONUTF8=1 python3 ops/runner.py daily >> ~/mercati-italia/runner/logs/daily.log 2>&1
```

## Come funziona `runner.py`

Legge gli stessi file YAML che usava GitHub Actions e li esegue sul computer: ogni job in un clone
pulito del repository, i passaggi `run` con Bash, gli artefatti passati da un job all'altro, le
condizioni `if`. I push usano la chiave SSH del computer. Le parti solo-GitHub (`github-script`)
sono sostituite dal runner stesso (allarmi). Per modificare un lavoro si modifica il suo YAML in
`ops/workflows/`.
