# Mercati Autopilot — metodologia e sistema automatico

Aggiornato: 12 ottobre 2026. Il sistema esegue il lavoro ripetitivo su GitHub Actions, **non** in ChatGPT, nel browser dell'utente o sul PC privato.

## Obiettivo

Migliorare progressivamente **qualità, copertura, sicurezza, costi e prestazioni** senza inventare date o aprire rischi di pubblicazione. Le metriche e le decisioni di rilascio devono essere riproducibili e misurabili.

## Architettura

```text
Scheduler GitHub Actions su main (ogni giorno alle 04:17 UTC)
    │
    ▼
Check-out di codice DEV (job senza permesso di scrittura)
    │
    ▼
Autopilot deterministico: backup → fonti ufficiali → merge prudente
    │
    ▼
Ricorrenze esplicite previste, MAI confermate artificialmente
    │
    ▼
Nuovo catalogo immutabile + indice compatto
    │
    ▼
Quality gates: record, identità, licenze/evidenze, date, budget KB
    │
    ├── FAIL → non pubblica, salva artefatto, apre/aggiorna issue
    │
    └── PASS → QA separata (audit npm, build Vite, Playwright mobile)
                    │
                    ├── FAIL → non pubblica, issue + screenshot/log
                    │
                    └── PASS → job con permesso di scrittura limitato
                                     │
                                     ▼
                              aggiorna SOLO dati DEV
                                     │
                                     ▼
                              static site DEV indipendente dal PC
                                     │
                                     ▼
                         risultato e checkpoint nel log GitHub
```

**Solo lo scheduler** `.github/workflows/market-autopilot.yml` è su `main`. Legge e prova il branch `improve/data-quality-security-performance-2026-10-11`. Non modifica `main`, i dati Firestore né l'app in produzione Cloudflare. Il token con scrittura è confinato al job di promozione del catalogo DEV, che gira solo dopo QA positiva.

**Revisione bloccata per esecuzione:** il primo job salva l'SHA esatto di DEV e i job successivi verificano di usare lo stesso codice. Se DEV cambia, la pubblicazione si ferma. È vietato fare rebase di un catalogo già testato su codice nuovo e non verificato. Il push standard rifiuta modifiche concorrenti.

## Le sei fasi e i relativi checkpoint

| Fase | Script | Risultato e condizioni |
|---|---|---|
| 00 baseline | `backend/autopilot.py` | Verifica firma, numero mercati, asset hash, fotografia delle metriche. |
| 01 sources | `backend/source_milano.py`, `source_firenze.py` | Acquisizione **limitata** da fonti autorizzate; ogni fallimento viene registrato. Nessuno scraping massivo. |
| 02 merge | `backend/merge_catalog.py` | Conserva slug, fonti, record distinti per sede; non ripristina date vecchie che la nuova fonte ha esplicitamente azzerato. |
| 03 forecast | `backend/recurrence_refresh.py` | Rinnova soltanto regole settimanali/mensili esplicite da fonti datate e attribuibili; salva la provenienza. Stima ≠ conferma. |
| 04 export | `backend/export_static.py` | Scrive asset JSON con hash in una **cartella temporanea**, mantenendo quelli dell'ultima generazione per compatibilità cache. |
| 05 quality | `backend/validate_static.py`, `audit_dataset.py` | Confronta numeri, firme, 60 giorni di copertura, budget rete e identità; rifiuta la nuova versione se peggiora oltre soglia. |

Ogni checkpoint è salvato in `autopilot-output/checkpoints/*.json` e allegato per 30 giorni alle esecuzioni GitHub Actions. `--resume` può ricaricare i risultati già acquisiti solo se policy, catalogo iniziale **e data di riferimento** coincidono. Un candidato respinto **non** altera la cartella `public/data/v1` in DEV.

## Miglioramento continuo basato sui dati

- `backend/autopilot_feedback.py` ordina le priorità in base a frequenza del problema, severità, affidabilità e costo di implementazione. Genera `roadmap.json` + `roadmap.md` con criteri di accettazione. Non crea false verifiche.
- `backend/source_scout.py` cerca **solo metadati** di fonti comunali strutturate nel catalogo nazionale [dati.gov.it](https://www.dati.gov.it/). Esclude mercati finanziari/immobiliari, fonti non strutturate e URL HTTP; ordina i candidati per utilità, formato, ente, licenza dichiarata e aggiornamento.
- `backend/source_intake.py` conserva in `reports/automation/source-registry.json` le fonti nuove e cambiate, con impronta verificabile dei campi importanti. I metadati aggiornati dal catalogo non sono scambiati per dati sui mercati aggiornati. Ricerche offline o parziali non cancellano fonti conosciute. La coda `reports/automation/SOURCE_QUEUE.md` espone punteggi di **priorità della verifica**, non affidabilità: vecchie tabelle statistiche sono declassate, fonti con potenziali sedi/calendari sono favorite. I primi dataset includono Bologna, Lombardia, Lazio, Roma, Veneto e Corciano; licenze e dati effettivi restano da verificare.
- **Nuove fonti scoperte = proposta, non import automatico.** Prima di aggiungere un adapter, verificare licenza, condizioni, schema, stabilità dell'identificatore e test. Questo evita di gonfiare il catalogo con dati non riutilizzabili o inventati.

### Campionamento sicuro delle nuove fonti

- `backend/source_probe.py` può leggere fino a **3 campioni**, massimo **64 KiB** ciascuno, solo da `opendata.comune.bologna.it`, `www.dati.lombardia.it` e `dati.comune.roma.it`. Gli URL non autorizzati e i redirect vengono rifiutati.
- Lo script cerca colonne come nome, indirizzo, comune, giorno e orari, ma conserva **solo i nomi delle colonne**, mai i record originali. Se una risposta è troppo grande o non leggibile, segnala una verifica da fare.
- Produce `reports/automation/source-probes.json` e `reports/automation/SOURCE_SCHEMA.md`, con traccia del risultato e suggerimenti di mapping. Né la licenza né gli orari né le date diventano automaticamente confermati.
- Gli adapter vengono aggiunti all'import ufficiale soltanto dopo verifica dei diritti di riuso, della struttura, della stabilità dell'ID e dei test. La nuova procedura usa il tempo di GitHub Actions; non invoca Cloudflare per le visite degli utenti.

Si tratta di un sistema di **feedback con policy**, non di un'IA che riscrive autonomamente e senza approvazione gli script di produzione.

## Dati aggiornati e ripetibilità

- **Ogni giorno alle 04:17 UTC**: l'orchestratore su GitHub Actions legge le fonti autorizzate, ricostruisce un catalogo candidato, lo confronta con il precedente, esegue CI e test browser mobile, poi pubblica solo su DEV. GitHub può ritardare le esecuzioni pianificate; non è un servizio real-time.
- **Sempre rieseguibile**: usare Actions → Mercati Autopilot → Run workflow. Lo script centrale è `python backend/autopilot.py --output autopilot-output`; `--offline` verifica il catalogo senza rete e `--resume` riutilizza solo checkpoint con firma, policy e data identici. Le fasi di monitoraggio sono script separati.
- **Metadati non equivalgono a dati correnti**: `backend/source_evidence.py` verifica solo fonti ufficiali con endpoint fissi (Bologna, Lombardia, Roma). Registra data dichiarata dei dati, data dei metadati, licenza dichiarata e hash di risposta, senza trasformarli in permessi di importazione.
- **Freshness indipendente**: `backend/freshness_monitor.py` rilegge lo snapshot e conta fonti recenti, vecchie, sconosciute e previsioni senza evidenza aggiornata. Salva `FRESHNESS.md` e `freshness.json`. La data del run NON sostituisce `aggiornato_il` di una fonte.
- **Avvisi GitHub automatici**: anomalie bloccanti aprono l'issue Autopilot. Un'issue distinta tiene traccia del debito di aggiornamento (assenza di verifiche documentate, fonti obsolete o metadati publisher non disponibili); non va scambiata con un errore del codice.
- **Nessuna promessa di dati in tempo reale**: ogni fonte può aggiornare a frequenza propria. Un calendario futuro dedotto da una regola settimanale è una previsione, non una conferma.

## Soglie attuali (modificabili in una sola policy)

`backend/autopilot_policy.json`:
- Almeno **12.000** record, perdita massima **2%**, conservazione almeno **99%** degli ID preesistenti.
- Previsioni esplicite su **120 giorni**, fonti non oltre **540 giorni** dall'ultimo aggiornamento dichiarato.
- Almeno **8.000** mercati con date previste ancora disponibili a **+60 giorni**.
- Indice gzip massimo **512 KiB**, crescita massima **40%** rispetto all'indice precedente.
- Divieto automatico di passare da `prevista` a `confermata` e divieto di inventare `verificato_il`.
- Se una fonte storica o nuova prova a cambiare/privare un record della sua fonte originale, la pubblicazione viene respinta finché non si conserva evidenza.
- Un feed ufficiale non raggiungibile o troppo piccolo viene quarantinato. Milano deve restituire almeno **60** schede (85 nell'ultima esecuzione); Firenze almeno **3** (4 nell'ultima esecuzione).
- Una nuova scheda non può essere marcata `confermata` o `verificato_il` da questa automazione; i cambi di città/regione di un ID esistente sono bloccati.
- La quota di schede prive di URL fonte può aumentare al massimo di **1 punto percentuale** in un ciclo. La policy non può autorizzare verifiche umane automatiche.
- Una pubblicazione nuova è consentita solo dopo controlli di routing Cloudflare statico, dipendenze, Python, build e browser mobile.

## Costi e sicurezza

- **Visita utente:** HTML, CSS, JS, cataloghi e indice statici; zero Firestore/Worker/D1/KV per la semplice lettura.
- **Lavori periodici:** eseguiti giornalmente su GitHub Actions; il consumo riguarda quote/minuti/artifact GitHub, **non** richieste dinamiche Cloudflare. Controllare le quote Actions del repository.
- **Mappa:** OpenFreeMap rimane servizio terzo con proprie condizioni e disponibilità.
- **Sicurezza:** `npm audit --omit=dev --audit-level=high` e test Python/Node/mobile bloccano DEV su errore. Non è un pentest.
- **Fatture Cloudflare:** la sicurezza di costo dell'architettura non implica che l'account non abbia altri servizi fatturabili attivi; serve controllare route e billing reali.
- **Firebase:** lo scheduler non distribuisce regole Firebase. Le regole DEV vanno distribuite separatamente dopo verifica del progetto corretto.

## Modalità di avvio e recupero

Il workflow schedulato su `main` si trova su:
https://github.com/tommyv-spec/mercati-italia/actions/workflows/market-autopilot.yml

GitHub → Actions → **Mercati Autopilot — scheduled DEV improvements**:
- **Run workflow** avvia immediatamente una sessione completa.
- Opzione `offline` prova tutte le fasi usando solo i record già registrati, senza nuove interrogazioni a portali ufficiali.
- I file `mercati-checkpoints-<run-id>` contengono checkpoint e report.
- `mercati-qa-build-<run-id>` contiene il sito compilato dopo i test.
- Se un job fallisce, viene aperta/aggiornata un'unica issue **[Mercati autopilot] Verifica richiesta**; viene chiusa quando un ciclo completo successivo riesce.
- Per riprendere manualmente da un artifact già scaricato, usare `python backend/autopilot.py --resume --output autopilot-output`. Non forzare un catalogo con firma diversa.

## Comandi locali opzionali

```bash
python -m unittest discover -s backend/tests -v
python backend/autopilot.py --offline --output autopilot-output
python backend/autopilot_feedback.py --manifest public/data/v1/manifest.json --out reports/automation/roadmap.json
python backend/source_scout.py --offline --out reports/automation/open-data-candidates.json
python backend/validate_static.py --manifest public/data/v1/manifest.json
npm ci && npm audit --omit=dev --audit-level=high && npm run build
```

## Cosa resta volutamente sotto controllo

1. **Fonti illegittime o senza licenza**, cancellazioni e verifiche umane: nessuno script deve inventare autorizzazioni o presenze.
2. **Nuovi adapter e cambi di metodologia**: script di scouting propongono, test e review autorizzano.
3. **Pubblicazione in produzione**: non automatizzata finché regole Firebase, licenze e affidabilità dei mercati non sono certificate.
4. **Nuove spese**: niente acquisto di piani Cloudflare o servizi esterni in automatico.

## Tracciabilità

- Codice DEV e policy: `backend/autopilot.py`, `backend/autopilot_policy.json`
- Fonti candidate persistenti: `backend/source_intake.py`, `reports/automation/source-registry.json`, `reports/automation/SOURCE_QUEUE.md`
- Riscontro ufficiale: `backend/source_evidence.py`, `reports/automation/SOURCE_EVIDENCE.md`
- Attualità: `backend/freshness_monitor.py`, `reports/automation/FRESHNESS.md`, `reports/automation/freshness.json`
- Test: `backend/tests/test_autopilot.py`, `test_autopilot_feedback.py`, `test_recurrence_refresh.py`
- Controllo mobile: `tests/ui-smoke.mjs`
- Anteprima: https://raw.githack.com/tommyv-spec/mercati-italia/dev-static-preview/index.html
- Prima esecuzione riuscita: https://github.com/tommyv-spec/mercati-italia/actions/runs/38179027185
