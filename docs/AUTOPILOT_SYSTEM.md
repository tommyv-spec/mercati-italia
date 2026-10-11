# Mercati Autopilot — metodologia e sistema automatico

Aggiornato: 11 ottobre 2026. Il sistema esegue il lavoro ripetitivo su GitHub Actions, **non** in ChatGPT, nel browser dell'utente o sul PC privato.

## Obiettivo

Migliorare progressivamente **qualità, copertura, sicurezza, costi e prestazioni** senza inventare date o aprire rischi di pubblicazione. Le metriche e le decisioni di rilascio devono essere riproducibili e misurabili.

## Architettura

```text
Scheduler GitHub Actions su main (martedì/venerdì alle 04:17 UTC)
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

## Le sei fasi e i relativi checkpoint

| Fase | Script | Risultato e condizioni |
|---|---|---|
| 00 baseline | `backend/autopilot.py` | Verifica firma, numero mercati, asset hash, fotografia delle metriche. |
| 01 sources | `backend/source_milano.py`, `source_firenze.py` | Acquisizione **limitata** da fonti autorizzate; ogni fallimento viene registrato. Nessuno scraping massivo. |
| 02 merge | `backend/merge_catalog.py` | Conserva slug, fonti, record distinti per sede; non ripristina date vecchie che la nuova fonte ha esplicitamente azzerato. |
| 03 forecast | `backend/recurrence_refresh.py` | Rinnova soltanto regole settimanali/mensili esplicite da fonti datate e attribuibili; salva la provenienza. Stima ≠ conferma. |
| 04 export | `backend/export_static.py` | Scrive asset JSON con hash in una **cartella temporanea**, mantenendo quelli dell'ultima generazione per compatibilità cache. |
| 05 quality | `backend/validate_static.py`, `audit_dataset.py` | Confronta numeri, firme, 60 giorni di copertura, budget rete e identità; rifiuta la nuova versione se peggiora oltre soglia. |

Ogni checkpoint è salvato in `autopilot-output/checkpoints/*.json` e allegato per 30 giorni alle esecuzioni GitHub Actions. `--resume` può ricaricare i risultati già acquisiti solo se policy e catalogo iniziale hanno ancora la stessa firma. Un candidato respinto **non** altera la cartella `public/data/v1` in DEV.

## Miglioramento continuo basato sui dati

- `backend/autopilot_feedback.py` ordina le priorità in base a frequenza del problema, severità, affidabilità e costo di implementazione. Genera `roadmap.json` + `roadmap.md` con criteri di accettazione. Non crea false verifiche.
- `backend/source_scout.py` cerca **solo metadati** di fonti comunali strutturate nel catalogo nazionale [dati.gov.it](https://www.dati.gov.it/). Esclude mercati finanziari/immobiliari, fonti non strutturate e URL HTTP; ordina i candidati per utilità, formato, ente, licenza dichiarata e aggiornamento.
- **Nuove fonti scoperte = proposta, non import automatico.** Prima di aggiungere un adapter, verificare licenza, condizioni, schema, stabilità dell'identificatore e test. Questo evita di gonfiare il catalogo con dati non riutilizzabili o inventati.

Si tratta di un sistema di **feedback con policy**, non di un'IA che riscrive autonomamente e senza approvazione gli script di produzione.

## Soglie attuali (modificabili in una sola policy)

`backend/autopilot_policy.json`:
- Almeno **12.000** record, perdita massima **2%**, conservazione almeno **99%** degli ID preesistenti.
- Previsioni esplicite su **120 giorni**, fonti non oltre **540 giorni** dall'ultimo aggiornamento dichiarato.
- Almeno **8.000** mercati con date previste ancora disponibili a **+60 giorni**.
- Indice gzip massimo **512 KiB**, crescita massima **40%** rispetto all'indice precedente.
- Divieto automatico di passare da `prevista` a `confermata` e divieto di inventare `verificato_il`.
- Se una fonte storica o nuova prova a cambiare/privare un record della sua fonte originale, la pubblicazione viene respinta finché non si conserva evidenza.

## Costi e sicurezza

- **Visita utente:** HTML, CSS, JS, cataloghi e indice statici; zero Firestore/Worker/D1/KV per la semplice lettura.
- **Lavori periodici:** eseguiti da GitHub Actions, circa due volte a settimana; il consumo riguarda quote/minuti/artifact GitHub, **non** richieste dinamiche Cloudflare.
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
- Test: `backend/tests/test_autopilot.py`, `test_autopilot_feedback.py`, `test_recurrence_refresh.py`
- Controllo mobile: `tests/ui-smoke.mjs`
- Anteprima: https://raw.githack.com/tommyv-spec/mercati-italia/dev-static-preview/index.html
- Prima esecuzione riuscita: https://github.com/tommyv-spec/mercati-italia/actions/runs/38179027185
