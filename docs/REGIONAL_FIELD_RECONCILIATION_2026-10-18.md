# Ricostruzione dei campi dai publisher — Lombardia + Veneto

Aggiornato il **18 ottobre 2026**. Questo è il PASSO DI MISURA e rimane
**solo lettura**. La modifica alle singole schede avviene unicamente dopo
un controllo indipendente dei campi e dei permessi.

## Lombardia MERCap — migliorare le schede esistenti

L'adapter ufficiale `backend/source_lombardia.py` scarica già il dataset
MERCap a pagine con controllo del conteggio, degli ID e della data
effettiva del publisher. Il dataset è descritto su
https://www.dati.lombardia.it/d/68zx-njaw ed è dichiarato settimanale.

L'importatore esistente `backend/official_enrichment.py` può
aggiungere orari a vecchie schede se Comune, **indirizzo e giorno**
coincidono; preserva URL originale, date, ID e coordinate. Non copia
gli orari quando l'indirizzo manca. Il nuovo
`backend/source_reconciliation_audit.py` misura
**tutte** le righe ufficiali contro tutte le schede legacy e distingue:
- source-ID già presente con campi diversi o vuoti;
- vecchia scheda con stesso Comune + provincia + via + giorno, fonte univoca;
- scheda con indirizzo mancante, **solo indizio** dalla stessa città,
  stesso giorno e breve distanza, non sufficiente a modificare la scheda;
- conflitti con più mercati alla stessa sede, giorni contraddittori,
  dati stantii o punti discordanti.

Un problema reale trovato nei test: a volte lo **slug contiene un
giorno diverso dalla ricorrenza**. Non usare lo slug come prova se
una regola esplicita lo contraddice: bloccare il match.
La vicinanza alla coordinata non convalida automaticamente la sede,
perché molte posizioni legacy sono centroidi comunali.

Output `reports/automation/lombardia-field-audit.json` e
`LOMBARDIA_FIELD_AUDIT.md`: contatori, piccoli esempi di slug
e impronta del feed, MAI l'intero dataset copiato.

## Veneto sagre e fiere — formato XLSX ufficiale

Publisher:
https://elezioni2020.regione.veneto.it/web/attivita-produttive/somministrazione-alimenti-e-bevande-nelle-sagre-e-nelle-fiere

Il 18 ottobre la pagina ufficiale indica
**Calendario cronologico sagre e fiere 2026** in formato XLSX,
**aggiornato all'8 ottobre 2026**.

La fonte è particolarmente utile per **eventi temporanei**,
non per i mercati settimanali. Per questo la nuova sonda
`backend/veneto_event_workbook_probe.py` non importa nessuna riga:
legge il file da URL esatto, verifica un limite massimo di
byte e decompressione, individua i fogli e osserva **soltanto
nomi delle colonne, tipi di dati e conteggi strutturali**.
Non conserva email, nomi di organizzatori o testi di manifestazioni.

Prima di creare un adapter che estragga eventi veri servono:
- identificativi stabili o hash attendibili delle sedi/eventi;
- schema completo di Comune, titolo, luogo, inizio/fine, eccezioni;
- **licenza di riuso della distribuzione** e attribuzione;
- test sui cambi d'anno, cancellazioni e dati ripetuti;
- un confronto con eventi già nel catalogo (senza inventare
  mercati ricorrenti da sagre una tantum).

I report dello schema sono
`reports/automation/veneto-event-schema.json` e
`VENETO_EVENT_SCHEMA.md`. Non sono un calendario
da mostrare ai visitatori.

## Verifiche

```bash
python -m unittest discover -s backend/tests -v

python backend/source_reconciliation_audit.py \
  --out /tmp/lo.json --report /tmp/LOMBARDIA.md

python backend/veneto_event_workbook_probe.py \
  --out /tmp/ve.json --report /tmp/VENETO.md
```

Solo GitHub Actions ha il permesso di salvare report nel
branch DEV. Nessun automatismo di questa pipeline modifica
`public/data/v1`, `main`, le regole Firebase o Cloudflare.
