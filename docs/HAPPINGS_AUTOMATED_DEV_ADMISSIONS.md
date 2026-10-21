# Happings → DEV: acquisizione e pubblicazione ripetibili

L'operazione non è un intervento su tre mercati. La procedura giornaliera
opera sul catalogo nazionale usando le stesse regole per tutte le fonti Happings.
Nessuna pubblicazione su produzione e nessun runner/servizio GitHub a pagamento.

## Unico punto d'ingresso sul PC collegato

Il task Windows `MercatiItalia-HappingsDaily` è attivo alle 09:30 ora
locale (solo quando la sessione Windows dell'utente è disponibile):

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\mercati-italia\scraper-code\scripts\happings-daily-windows.ps1"
```

Il programma esegue automaticamente, in ordine:

1. `git fetch` del DEV, senza usare `main`, e controllo di checkout
   dedicato. Aggiornamento atomico del codice locale.
2. Avvio Python con **`-X utf8`**, obbligatorio su Windows: il decoder
   CP1252 deformava l'ISTAT e i nomi come Forlì/Mondovì. Il sistema rifiuta
   esecuzioni non UTF-8, anziché perdere silenziosamente prove.
3. I test di regressione di Happings. Se falliscono, non scarica nulla.
4. `happings_bulk_refresh.py`: legge robots.txt e controlla sitemap/home,
   aggiorna le pagine solo quando scadono. Rispetta i ritardi del publisher,
   scrive checkpoint atomici e usa lock esclusivo contro doppio crawler.
5. `happings_bulk_finisher.py`: recupera fallimenti, acquisisce la versione
   precisa del catalogo DEV, riconcilia **tutti** gli elenchi provinciali e
   tutte le schede di dettaglio. Salva le ragioni di quarantena.
6. `happings_weekly_dev_admission.py`: usa **solo** le pagine indicate dal
   report come candidati nuovi senza collisioni, rilegge l'HTML live per
   provare il dato attuale, ricostruisce Comune, sede e giorno con ISTAT,
   valida due volte identità/provenienza e tenta fino a 32 nuove schede.
7. Esporta in un'area temporanea, applica i gate nazionali Autopilot,
   controlla la firma del manifest, indici, hash e ID. Nessuna scheda
   preesistente può cambiare in questa fase.
8. Se e solo se tutti i controlli passano, committa i soli file
   `public/data/v1` e spinge in **DEV** con `git push` fast-forward,
   mai `--force`. Se DEV è cambiato, blocca il push e riprova durante
   l'esecuzione successiva. Le verifiche CI preesistenti devono passare
   prima di promuovere manualmente qualsiasi risultato in produzione.

## Provenienza e qualità

Le pagine HTML esatte usate come prova vengono conservate **solo in locale**
in `%LOCALAPPDATA%\mercati-italia\happings-reconciliation\happings-source-html`,
con nome basato su SHA-256 URL/HTML e archivio gzip bounded. I riscontri
delle schede DEV legano campo, URL, SHA-256, data di lettura e identità.
L'HTML non viene caricato sul sito, su GitHub o su altri servizi.

Rimangono bloccati: città/ province non riconciliate con ISTAT; più sedi
nello stesso Comune/giorno; identità già esistenti con calendario ignoto;
indirizzi vaghi; pagine con layout incompleto; eventuali duplicati;
mancanza di riscontri; modifiche a qualsiasi mercato esistente;
nuove date, verifiche, coordinate o orari che la fonte non prova.

Una fonte che scrive «la mattina» **non prova un orario esatto**. Le nuove
schede sono pubblicate con `non_confermato`, `date_quality=sconosciuta`,
senza date future inventate e senza coordinate.

## Rapporti verificabili

In `%LOCALAPPDATA%\mercati-italia\happings-reconciliation`:

- `happings-local-run.json`: ultima scansione/QA, errori/last success
- `happings-source-reconciliation.json`: copertura nazionale su commit DEV
- `happings-source-worklist.json`: identità e ragione per ogni riga
- `happings-detail-match-report.json`: comparazione delle schede dettagli
- `happings-weekly-admission.json`: candidati, prove, ammissioni, QA e
  commit DEV pubblicato o fallimento.
- `happings-source-html-index.json`: prove HTML preservate in locale

Il task Windows `MercatiItalia-HappingsDaily` scrive anche log in
`%LOCALAPPDATA%\mercati-italia\logs`. Con computer spento o utente
non collegato la sessione programmata non parte; `StartWhenAvailable`
la recupera quando Windows lo permette.

## Esecuzione QA senza pubblicare

Dalla directory del checkout dedicato:

```powershell
python -X utf8 -m unittest discover -s backend/tests -p "test_happings_*.py"
python -X utf8 backend/happings_daily_local.py
python -X utf8 backend/happings_weekly_dev_admission.py
```

La pubblicazione è attivata **solo** dal parametro `--publish-dev`.

**Limite dell'attuale automazione:** ciò che Happings non fornisce (ad
esempio orari numerici, coordinate, conferma che un mercato operi oggi)
richiede un'altra fonte attendibile. Non può essere simulato dalla pipeline.
