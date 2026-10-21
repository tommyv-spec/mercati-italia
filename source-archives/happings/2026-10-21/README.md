# Happings — backup dati sorgente del 21 ottobre 2026

Backup **leggibile e verificabile** del progetto Mercati Italia. Questo branch
non viene pubblicato sul sito in produzione o nella preview DEV.

La cartella `source-archives/happings/2026-10-21/` contiene **88 file JSON**:
`manifest.json`, 49 blocchi di fatti estratti da **2.313 pagine Happings**
e 38 blocchi di report (10 rapporti distinti, incluso l'audit dei 18 mercati
pubblicati su DEV). Il backup contiene tutti i campi strutturati estratti
da Happings, gli URL, le date di lettura e le impronte SHA-256 della fonte.

## Integrità

Ogni blocco è indicato nel `manifest.json`, con il relativo
`sha256`, il numero di record e la dimensione. I **88 blob Git**
sono stati confrontati uno a uno con le 88 copie locali prima del commit,
senza differenze. Il generatore locale ha verificato anche la presenza
di tutte le 2.313 pagine. La firma del checkpoint originario è
`9f367aca9f6a35d6eb94d423f0e1a1673b621b20f1651d7210697d819267774f`.

I file `source-facts-NNN.json` contengono `pages`, con `ordinal`,
`url`, `checkpoint_entry` e `fact`. I file
`report-*.json` contengono `items`; l'ordine e la
ricomposizione di ogni rapporto sono nel manifest.

## Ambito e limiti

Questo è un backup **semantico dei dati strutturati**, non l'HTML originale:
le pagine HTML sono rappresentate dai dati estratti e dall'hash
originale. I file `.json.gz` del primo crawl non sono stati caricati
byte per byte: riproducendo i file gzip con una diversa compressione
cambierà il loro hash binario, pur mantenendo gli stessi campi e
gli stessi hash HTML originali. Un ripristino deve rigenerare le
impronte del nuovo gzip nel checkpoint, mai simulare l'hash binario
originale. Il contenuto dei report viene preservato, tranne
informazioni sul percorso locale del computer.

Nessun account personale, token, servizio GitHub a pagamento,
Git LFS, Docker o nuovo runner è incluso o necessario.
La lettura originale di ogni fonte non prova che il mercato
sia aperto o che eventuali date previste siano confermate.

Le modifiche al codice e al catalogo continuano sul branch
`improve/data-quality-security-performance-2026-10-11`;
questo branch è dedicato ai backup e non influisce sulla produzione.
