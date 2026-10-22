# Happings — source backup GitHub verificato

**Aggiornamento: 22 ottobre 2026 — backup pubblicato e ripristinato.**

## Backup pubblico indipendente dal catalogo DEV

- Repository: `tommyv-spec/mercati-italia`
- Branch archivio: `happings-source-archive-2026-10-21`
- Commit pubblicato: `8d6e0fa54f4c992e66b352002f7f64739960d3f5`
- Cartella: `source-archives/happings/2026-10-21/`
- Manifest SHA-256: `90d23f8c835420c7b2eca01bfc35f8fc3124069603d74e3df7a86db9ca8292e4`
- **88 file JSON con SHA-256 corrispondenti**, 49 dei quali con fatti di fonte;
  **2.313 pagine Happings elaborate + 10 report**.

La verifica indipendente ha scaricato **i soli file del branch GitHub**
senza leggere lo snapshot originale del PC e li ha ripristinati in una
cartella vuota: **2.313 file pagina `*.json.gz` e 10 rapporti**.
La cartella contiene `github-restore-proof.json` con il risultato di
questa prova, insieme al `README.md` per il recupero su una nuova macchina.

## Ripristino

```bash
git clone --depth 1 --single-branch \
  --branch happings-source-archive-2026-10-21 \
  https://github.com/tommyv-spec/mercati-italia.git mercati-archive
cd mercati-archive
python backend/happings_github_readable_backup.py \
  --out source-archives/happings/2026-10-21 \
  --restore-to /percorso/vuoto/mercati-happings
```

**Limite esatto:** il crawl nazionale memorizzava fatti strutturati
e hash dell'HTML originale, non l'intero DOM HTML di ogni pagina.
Il backup GitHub conserva questi fatti e hash, ma non pretende di
ricostruire byte per byte l'HTML mai salvato. Il gzip riprodotto
può avere SHA diverso perché ricostruito dal JSON equivalente.

## Spazio locale e automazione

Dopo il ripristino verificato sono state eliminate **soltanto** le
due copie di prova e di trasferimento (`github-readable-backup-resume-20261022`
e `archive-github-smoke-20261022`), per circa 29,7 MB complessivi.
Rimane la piccola cache operativa del crawler in
`%LOCALAPPDATA%/mercati-italia/happings-full-crawl`: è richiesta per
l'aggiornamento incrementale con checkpoint e può essere ricostruita
dal backup nel caso di guasto.

Lo scraper giornaliero Windows rimane distinto dal job DEV GitHub:
il backup del **21 ottobre è verificato**, ma non bisogna considerare
automatica la pubblicazione delle successive versioni dell'archivio
finché non esiste un canale di scrittura autorizzato. L'account GitHub
del PC ha soltanto permessi di lettura su questo repository; il job
`publish_dev` usa i permessi già autorizzati.

La regressione dei test Happings del 22 ottobre derivava dalla data
storica `2026-10-21` letta con l'orologio reale; il test usa ora
un orologio UTC fittizio coerente con la prova, senza indebolire la
validazione di produzione.

**Nessun servizio GitHub a pagamento, Git LFS o nuovo runner.**
Nessuna modifica effettuata alla produzione o ai fatti già verificati.
