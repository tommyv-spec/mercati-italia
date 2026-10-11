# Mercati d'Italia — metodo ripetibile per dati aggiornati

## Regola di lavoro

Non correggere manualmente i singoli mercati per risolvere problemi ricorrenti. Modificare lo script che genera i dati, aggiungere un test del difetto, rieseguire la pipeline e confrontare i risultati con il checkpoint precedente.

Un run riuscito non conferma che gli orari, i mercati o i giorni siano aggiornati. La fonte deve essere verificabile. Le ricorrenze calcolate restano **previste**, non confermate.

## Unico workflow automatico

GitHub Actions: [Mercati Autopilot](https://github.com/tommyv-spec/mercati-italia/actions/workflows/market-autopilot.yml), ogni giorno alle 04:17 UTC e avvio manuale con **Run workflow**.

- Branch con codice e catalogo: improve/data-quality-security-performance-2026-10-11
- Anteprima approvata: dev-static-preview
- Main: soltanto scheduler approvato, nessun catalogo DEV in produzione
- I vecchi publisher automatici sono disattivati per evitare scritture concorrenti
- Cloudflare serve JSON e asset statici; i visitatori non chiamano Firestore, Worker, KV o D1 per leggere i mercati
- Una scheda dell'app rimasta aperta controlla il manifest statico ogni 30 minuti mentre è visibile

GitHub può ritardare uno scheduler. La frequenza giornaliera è un controllo regolare, non una garanzia di conferme in tempo reale.

## Script e checkpoint

| Fase | Script | Responsabilità |
|---|---|---|
| Catalogo | backend/autopilot.py | baseline, source, merge, forecast, export, quality; firma e decisione |
| Scouting | backend/source_scout.py | metadati pubblici, senza import |
| Registro | backend/source_intake.py | fonti nuove, cambiate, storicizzate |
| Schema | backend/source_probe.py | massimo 3 piccoli campioni allowlist, nessun record persistito |
| Diritti | backend/source_evidence.py | licenze dichiarate e data publisher da fonti ufficiali |
| Revisioni | backend/source_change_detector.py | confronto con ultimo report, senza inventare modifiche ai mercati |
| Freschezza | backend/freshness_monitor.py | età reale delle fonti, previsioni e verifiche documentate |
| Avvisi | backend/freshness_alert.py | singola issue GitHub per debito informativo |
| Storico | backend/autopilot_history.py | metriche e checkpoint dopo QA completa |

Gli output vivono in autopilot-output durante il job. Gli artefatti GitHub Actions conservano checkpoint e candidato. Solo dopo test completi sono salvati in reports/automation e, se il contenuto cambia, nei file statici DEV.

## Comandi riproducibili senza rete

Da root del repository:

~~~bash
python -m unittest discover -s backend/tests -v
python backend/autopilot.py --offline --output autopilot-output
python backend/source_scout.py --offline --out autopilot-output/official-candidates.json
python backend/source_intake.py --scout autopilot-output/official-candidates.json --previous reports/automation/source-registry.json --out autopilot-output/source-registry.json --report autopilot-output/SOURCE_QUEUE.md
python backend/source_probe.py --offline --registry autopilot-output/source-registry.json --out autopilot-output/source-probes.json --report autopilot-output/SOURCE_SCHEMA.md
python backend/source_evidence.py --offline --registry autopilot-output/source-registry.json --out autopilot-output/source-evidence.json --report autopilot-output/SOURCE_EVIDENCE.md
python backend/source_change_detector.py --current autopilot-output/source-evidence.json --previous reports/automation/source-evidence.json --out autopilot-output/source-changes.json --report autopilot-output/SOURCE_CHANGES.md
python backend/freshness_monitor.py --manifest autopilot-output/candidate/public/data/v1/manifest.json --publisher-evidence autopilot-output/source-evidence.json --out autopilot-output/freshness.json --report autopilot-output/FRESHNESS.md
python backend/freshness_alert.py --freshness autopilot-output/freshness.json --source-changes autopilot-output/source-changes.json --out autopilot-output/freshness-alert.json
npm ci --no-audit --no-fund
node --test tests/*.test.mjs
npm run build -- --base=./
~~~

Per aggiornare con fonti vere usare **Run workflow** del job GitHub, opzione offline=false. La pipeline chiama gli stessi script e testa anche i percorsi mobile prima di pubblicare DEV.

## Recuperare da un errore

- Leggere il job fallito, il report della policy e i checkpoint del relativo artifact.
- Se si tratta di un errore ricorrente, creare un test che riproduca il caso, quindi correggere lo script.
- Non riusare un checkpoint con firma catalogo, policy o data diversi. Il comando --resume del catalogo rifiuta queste combinazioni.
- Un candidato respinto non può essere copiato nei dati DEV. Il push concorrente è rifiutato senza forzare o ribasare codice non testato.
- La preview è scritta solo dall'Autopilot dopo le verifiche; gli asset delle precedenti versioni rimangono recuperabili.

## Invarianti

1. Ultimo run e data della fonte non sono la stessa cosa. Anche una fonte appena aggiornata non verifica automaticamente ogni appuntamento.
2. Non inventare verificato_il, date confermate, licenze, sedi, giorni o coordinate.
3. Righe con giorni diversi nello stesso dataset possono essere mercati distinti: non unirle per nome/città senza prove.
4. Non interpretare geo_x/geo_y come coordinate WGS84 senza prova. Quartiere e nome mercato sono campi diversi.
5. Le previsioni basate su fonti oltre 540 giorni vanno fatte scadere, conservando identità e provenienza dei mercati.
6. Non abilitare un nuovo importer da soli metadati. Prima occorrono schema controllato, licenza verificata, ID stabili, test e dedup prudente.
7. Non alterare Firebase/Cloudflare live o main come effetto collaterale di un aggiornamento DEV.
8. Misurare variazioni reali e mantenere separati problemi di qualità informativa e problemi tecnici.

## Dove controllare

- [Ultime metriche](../reports/automation/LATEST.md)
- [Freschezza dei dati](../reports/automation/FRESHNESS.md)
- [Licenze e aggiornamenti publisher](../reports/automation/SOURCE_EVIDENCE.md)
- [Confronto revisioni publisher](../reports/automation/SOURCE_CHANGES.md)
- [Coda per nuove fonti](../reports/automation/SOURCE_QUEUE.md)
- [Issue persistente sui dati](https://github.com/tommyv-spec/mercati-italia/issues/2)

**Obiettivo permanente: aggiornare i dati quando cambiano le prove, non aggiornare solo il numero della data.**
