# Happings: sistema completo di scansione, qualità dati e DEV

Verifica reale del 21 ottobre 2026. Riferimento: snapshot locale, hash dei
fatti salvati, catalogo DEV `cca613aebe218b9f39df2b298f6a8d25df9b07f8`.
Una scansione degli URL non dimostra la completezza di tutti i campi.

## Copertura della fonte realmente misurata

| Unità | Esito |
| --- | ---: |
| URL scoperti da home, sitemap e archivio Mercati | 2.313 |
| Pagine interpretate nella prima scansione | 2.313 |
| Elenchi settimanali provinciali | 106 |
| Righe fisiche negli elenchi | 8.053 |
| Schede evento interpretate | 2.207 |
| Schede evento classificate come mercato | 281 |
| Mercati con intervalli orari nel dettaglio | 273 |
| Mercati con appuntamenti espliciti nel dettaglio | 272 |
| Dettagli con conflitti fra valori pubblicati | 59 |
| Schede di dettaglio riconciliate a un solo mercato esistente | 128 |
| Dettagli che potrebbero rappresentare un mercato nuovo | 86 |
| Di questi, con i dati minimi di ammissione nel lettore | 55 |
| Dettagli senza Comune/provincia riconciliabile univocamente | 49 |

### Copertura reale del catalogo DEV

Nella fotografia analizzata: 9.775 schede con Happings come fonte primaria;
2.329 senza indirizzo; 556 con un testo orario; 9.334 con date previste;
128 con date riportate da fonte. Nei listati settimanali 7.984 delle 8.053
righe specificano soltanto la mattina. Questi valori sono qualitativi,
non orari numerici. La fonte non prova l'effettiva apertura del mercato.

Nella riconciliazione geografica abbiamo osservato città in province
sbagliate: la pagina di Alessandria include molti Comuni di Biella.
La provincia del titolo non può essere usata per correggere ISTAT.
Sono stati rilevati anche elenchi con più sedi differenti per lo stesso
Comune e giorno, sedi vaghe e identità già presenti con nomi discordanti.
Ogni gruppo è classificato e documentato nel worklist locale, non viene
trasformato arbitrariamente in una nuova scheda.

## Architettura del crawler

1. **Discovery**: `/it/`, `robots.txt`, sitemap index, sitemap articolo,
   13 sitemap evento, 26 pagine dell'archivio Mercati e link effettivamente
   pubblicati. Il prefisso `/it/` non prova che un luogo sia in Italia;
   la geografia è verificata con il riferimento ISTAT.
2. **Frontier + fetch**: coda univoca, HTTPS/dominio esatto, URL e MIME
   controllati, rate limit di almeno tre secondi sul dominio,
   timeout, download sequenziali, checkpoint atomici e lock per impedire
   crawler concorrenti sulla stessa directory.
3. **Extract**: due parser separati (`happings_weekly_layout.py` e
   `happings_detail_layout.py`); fatti strutturati per pagina,
   URL originale, timestamp di lettura, impronta SHA-256 dei byte HTML
   e hash del file JSON compresso. Layout non riconosciuti = sospesi.
4. **Retry / refresh**: `happings_retry_failures.py` tenta di recuperare
   solo i fallimenti della prima passata.
   `happings_bulk_refresh.py` scopre periodicamente nuove pagine e
   rilegge le fonti quando diventano dovute; non cancella le ultime
   informazioni buone per un errore temporaneo. Il primo refresh del
   21 ottobre ha richiesto **zero download** delle pagine già aggiornate.
5. **Reconcile**: `happings_full_reconciliation.py` controlla TUTTE
   le righe contro gli ID DEV, Comune ISTAT, giorno, sede e conflitti.
   `happings_detail_matching_report.py` verifica separatamente le
   schede con ore/date e la loro identità. La fase non modifica il catalogo.
6. **Admission / export**: gli aggiornamenti di campo già esistenti
   passano soltanto nei validatori dell'Autopilot DEV. Per i mercati
   settimanali nuovi `happings_weekly_admission.py` è ancora
   **review-only**, poiché manca la sua ammissione indipendente nella
   catena dei gate nazionali. Le nuove schede da evento sono inseribili
   solo attraverso il certificato di ammissione per il dettaglio già
   esistente. Non si deve aggirare questo passaggio.

## Operazione locale autonoma, senza costo GitHub

Dopo la prima scansione, sul computer dell'utente:

```powershell
python backend/happings_daily_local.py --snapshot "$env:LOCALAPPDATA\mercati-italia\happings-full-crawl" --out "$env:LOCALAPPDATA\mercati-italia\happings-reconciliation" --repo .
```

Il comando richiama il refresh bounded (70 pagine max nella sessione),
la riconciliazione sull'ultimo DEV pubblico via `git fetch`, il controllo
dei dettagli e il report finale, mantenendo tutti i dati privati fuori da
GitHub. `happings-local-run.json` registra successo o errore in modo
leggibile da programmi. Pubblicazione produzione sempre disabilitata.

Per la scansione iniziale completa o un suo resume:

```powershell
python backend/happings_bulk_snapshot.py
```

Per rileggerne gli esiti senza rete Happings:

```powershell
python backend/happings_bulk_finisher.py
```

### Qualità e test

```powershell
python -m unittest discover -s backend/tests -p "test_happings_*.py"
```

Il controllo indipendente verifica hash, identità e ripetibilità.
I file gzip vengono decompressi con dimensione massima, così snapshot
malformati non consumano memoria senza limiti. Gli errori non vengono
contati come pagine correttamente lette. Nessun nuovo servizio a
pagamento o runner GitHub è necessario.

## Limiti veri e prossime migliorie verificabili

- **Non esiste un orario esatto dove il publisher indica solo «la mattina».**
  Questo dato richiede un'altra fonte attendibile.
- Alcune pagine provinciali non corrispondono alla geografia delle righe;
  gli indici stranieri o storici richiedono revisione distinta.
- I 53 gruppi settimanali apparentemente nuovi e le 55 schede evento
  con dati minimi non sono automaticamente 108 mercati reali distinti.
  Vanno passati nella deduplicazione e negli stessi gate di ammissione.
- Lo snapshot conserva **i fatti strutturati**, non una copia del DOM HTML.
  Un cambio del parser può quindi richiedere una nuova lettura della
  pagina: è un miglioramento futuro, non una capacità già implementata.
- Ogni nuovo formato va aggiunto al registry dei parser e misurato con
  fixture e prova fonte→campo→catalogo, non corretto un mercato alla volta.

Riferimenti: [Scrapy JOBDIR](https://docs.scrapy.org/en/latest/topics/jobs.html),
[Scrapy AutoThrottle](https://docs.scrapy.org/en/master/topics/autothrottle.html),
[Scrapy Optimization](https://docs.scrapy.org/en/master/topics/optimize.html),
[RFC 9309](https://www.rfc-editor.org/rfc/rfc9309.html) e
[Google Sitemaps](https://developers.google.com/search/docs/crawling-indexing/sitemaps/overview).
