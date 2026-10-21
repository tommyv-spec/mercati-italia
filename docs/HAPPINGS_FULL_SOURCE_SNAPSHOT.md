# Scansione completa Happings senza interventi per singolo mercato

Il job DEV giornaliero continua a riempire il catalogo con fonti convalidabili
e checkpoint. Per accelerare il primo inventario nazionale è disponibile
anche una **scansione una tantum completa, riprendibile**:

```bash
python backend/happings_bulk_snapshot.py
```

L'estrazione legge, in modo sequenziale:

1. `https://www.happings.com/it/` e la policy `robots.txt`;
2. l'indice Yoast e tutte le sitemap articoli rilevanti;
3. gli elenchi dei mercati settimanali delle province italiane riconosciute;
4. le 13 sitemap eventi e le pagine dell'archivio Mercati;
5. ogni singola pagina evento osservata e tutti i suoi campi.

L'inventario effettivo rilevato il 21 ottobre 2026 è di 106 URL provinciali,
2.208 URL evento e 26 pagine dell'archivio categoria Mercati. Questi non
sono 2.208 mercati: contengono anche altri eventi. Il lettore usa un
classificatore conservativo e preserva i fatti della fonte separati
dalle aperture confermate.

## Controlli e salvataggio

- Sono consentiti solo HTTPS, `www.happings.com`, `robots.txt` e gli
  URL scoperti direttamente nel sito. Le pagine non vengono inventate
  partendo dai nomi dei mercati.
- Pausa minima di 3 secondi tra richieste, timeout e dimensione HTML limitati,
  un'unica richiesta alla volta, nessun browser, Docker o servizio a pagamento.
- Il checkpoint JSON contiene coda, pagina letta, risultato ed errore.
  Ogni risposta convertita in dati strutturati va in
  `pages/<sha256-url>.json.gz`. Il file viene sostituito atomicamente.
- I file **non** sono pubblicati automaticamente: prima devono essere
  riconciliati con gli ID e le fonti del catalogo, con il medesimo
  controllo anti-duplicati già richiesto dal DEV Autopilot.
- Una pagina indisponibile, incompleta o incompatibile non causa una
  nuova apertura inventata: lo stato rimane `unavailable` o
  `unassessed`.
- La scansione può essere interrotta e ripresa eseguendo lo stesso comando,
  che salta i file già acquisiti.

Su Windows, la cartella persistente predefinita è:

```text
%LOCALAPPDATA%\mercati-italia\happings-full-crawl
```

Per eseguire un lotto controllato:

```bash
python backend/happings_bulk_snapshot.py --max-pages 16
```

Per indicare una directory diversa:

```bash
python backend/happings_bulk_snapshot.py --out PATH
```

Questa scansione misura **le informazioni realmente estratte**.
Non sostituisce il lavoro di collegamento alle schede storiche Happings.
Se la fonte pubblica soltanto `la mattina`, l'orario esatto resta
sconosciuto, non `08:00–13:00`. Le date future non diventano conferme
di apertura. 
