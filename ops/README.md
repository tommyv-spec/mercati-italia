# Automazione senza GitHub Actions

Dal 25 ottobre 2026 i lavori automatici del progetto **non usano GitHub Actions**. Li esegue
`ops/runner.py` su un computer (oggi il PC del progetto, domani eventualmente un server gratuito).

## Cosa gira e quando

Ogni giorno alle 04:30 (ora del PC) l'attività di Windows **MercatiItalia-Automazione** esegue
`runner.py daily`, che lancia in ordine i lavori in scadenza descritti in `ops/workflows/`:

| Lavoro | Frequenza | Cosa fa |
|---|---|---|
| `happings-weekly-fields` | lunedì | rilegge le 107 pagine settimanali Happings e completa i campi |
| `market-autopilot` | ogni giorno | scarica le fonti, aggiorna il catalogo (salvato nel ramo DEV) |
| `data-expansion-audit`, `event-leads-daily`, `regional-field-reconciliation`, `publisher-quality-daily`, `official-source-output-qa` | ogni giorno | report di controllo nel ramo DEV |

Poi pubblica `reports/QUALITA.md`, la pagina unica sulla qualità dei dati, mette il catalogo della
notte sul **sito pubblico** (sezione sotto) e infine aggiorna il **link di anteprima**
(https://market-ef407--dev-n0hayy7b.web.app, canale Firebase `dev`): serve solo a guardare le
modifiche all'app non ancora rilasciate, e il sito pubblico non dipende da lui. Se non si aggiorna
si apre l'issue «[Automazione locale] app-dev — verifica richiesta». A mano:
`python ops/runner.py devapp` (`--force` per ricostruirlo comunque). La configurazione hosting sta in
`ops/devapp-hosting.json` (vale anche per il sito pubblico, con un altro nome apposta).

## Il sito pubblico (fuori-mercatini.com)

**Il catalogo va sul sito da solo** (proprietario, 4 novembre 2026: il sito aggiornato è la
conseguenza di un'automazione che funziona). Dopo una notte riuscita (nessun lavoro fallito,
`QUALITA.md` senza segnali rossi) `runner.py daily` mette sul sito il catalogo della notte, dentro
l'app dell'ultimo rilascio (il tag `release-*` più recente):

1. costruisce quel tag con la cartella `public/data` salvata stanotte nel ramo DEV e lo pubblica sul
   canale di anteprima `release`;
2. lo apre in un browser da telefono (`ops/live-smoke.mjs`): l'elenco deve mostrare mercati e
   aprire una scheda, senza errori;
3. copia quella stessa versione sul sito (`hosting:clone market-ef407:release market-ef407:live`) e
   controlla che il sito serva il nuovo catalogo.

Se qualcosa non va il sito tiene il catalogo di prima e si apre l'issue
«[Automazione locale] app-live — verifica richiesta». L'ultima pubblicazione è in
`%LOCALAPPDATA%\mercati-italia\runner\live.json` (versione e versione precedente); il log
`logs\live-<data>.log` riporta il comando per tornare indietro. A mano: `python ops/runner.py live`.

**L'app (aspetto, funzioni) va sul sito solo con il via del proprietario**, e ogni rilascio prende un
tag `release-<data>`: è il tag che dice alle notti quale app usare. Il sito riceve **esattamente** la
versione già provata sull'app DEV, senza ricostruirla:

```bash
python ops/runner.py devapp      # l'app DEV serve il catalogo DEV di oggi
npx firebase hosting:channel:list --project market-ef407 --json   # annotare la versione di "live"
npx firebase hosting:clone market-ef407:dev market-ef407:live
git tag -a release-<data> -m "..." <commit dell'app DEV> && git push origin release-<data>
```

Per tornare indietro: `npx firebase hosting:clone market-ef407@<versione annotata> market-ef407:live`.
Un rilascio (o un ritorno indietro) fatto a mano senza un tag nuovo ferma le notti: vedono che il
sito non è più la versione messa da loro e aspettano il tag invece di rimettere l'app di prima.
Il primo rilascio di questa app è del 1° novembre 2026; prima c'era la vecchia app Leaflet
(versione `5e49e9ef9a5dfb91`). `public/sw.js` esiste solo per togliere dai telefoni il service
worker della vecchia app e ricaricare le pagine ancora aperte su di essa; i vecchi link
`/evento/<id>` aprono la stessa scheda.

Se DEV contiene lavori non ancora pronti: ramo `release/<data>` dall'ultimo tag `release-*` più le
sole modifiche volute, `npx firebase hosting:channel:deploy swtest`, prove sul canale `swtest`, poi
`npx firebase hosting:clone market-ef407:swtest market-ef407:live` e il tag `release-<data>`.

Chi ha già l'app non deve fare nulla: la pagina è servita `no-cache`, e quando si torna su un'app
rimasta aperta `src/lib/appUpdate.js` (al massimo ogni 5 minuti) confronta la pagina pubblicata e
ricarica da sola sulla nuova versione, senza chiedere. Il catalogo si aggiorna già da sé
(`src/hooks/useMarkets.js`).

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
python ops/runner.py live                 # il catalogo della notte sul sito, nell'app dell'ultimo tag release-*
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

Ogni lettore lega la lettura salvata alle schede esatte che riceve. Se la modifica cambia le
schede prima o dentro un lettore (città, province, date delle pagine), la prova con le letture
salvate si ferma con «Cannot resume …». In quel caso: `rehearse --live --code <cartella>` rilegge
davvero le fonti (stessi limiti e pause della notte, partendo dallo stato di quella notte),
sempre senza pubblicare. Le differenze includono allora anche ciò che le fonti hanno cambiato.

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
