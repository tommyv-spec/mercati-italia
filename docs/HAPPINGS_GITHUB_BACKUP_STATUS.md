# Happings — GitHub source backup verificato

## Backup pubblicato: 21 ottobre 2026

Il ramo pubblico [happings-backup-2026-10-21](https://github.com/tommyv-spec/mercati-italia/tree/happings-backup-2026-10-21/source-archives/happings/2026-10-21)
contiene un backup leggibile in **88 file JSON** più README:

- **2.313 pagine Happings** complete di fatti strutturati, URL, data di acquisizione
  e SHA-256 dell'HTML originario;
- **10 rapporti** di qualità, riconciliazione, potenziali duplicati e verifica
  dell'ammissione DEV di 18 mercati settimanali;
- manifest con hash SHA-256, dimensioni e numero di record per ogni blocco.

Prima della pubblicazione, tutti gli **88 Git blob** sono stati confrontati
con gli hash delle copie locali: **zero differenze**. Il branch GitHub è stato
riaperto e verificato: **89 file presenti su 89 attesi**, compreso il README.

Il backup conserva integralmente i **dati estratti**, non il markup HTML originale
o i byte gzip storici. Un ripristino rigenera gzip e relative impronte;
gli hash della pagina HTML di origine restano quelli osservati.

## Ripristino e verifica ripetibili

Lo script `backend/happings_github_readable_backup.py` sul ramo DEV crea,
verifica e ripristina i fatti Happings. Per ripartire da GitHub, scaricare
il ramo del backup, poi dal repository DEV:

```powershell
python -X utf8 backend/happings_github_readable_backup.py --out PATH_ARCHIVIO
python -X utf8 backend/happings_github_readable_backup.py --out PATH_ARCHIVIO --restore-to DIRECTORY_VUOTA
```

Il restore rifiuta directory non vuote, ricostruisce
`happings-full-crawl/checkpoint.json`, tutti i `pages/*.json.gz` e i
rapporti; verifica l'hash di ciascun blocco prima della scrittura e i file
ricostruiti prima del successo.

**Prova reale effettuata:** 2.313 pagine sorgente e 10 rapporti sono stati
ripristinati in una directory temporanea, tutte le 2.313 schede hanno
superato la verifica locale. I byte gzip risultanti non sono dichiarati
uguali a quelli del primo download.

## Uso quotidiano e nessun costo GitHub

Il catalogo DEV, il codice del crawler e le pubblicazioni periodiche
continuano sul ramo `improve/data-quality-security-performance-2026-10-11`
e sull'Autopilot GitHub già esistente, senza nuova infrastruttura.
Il task Windows locale `MercatiItalia-HappingsDaily` usa ancora
il piccolo checkpoint attivo per fare aggiornamenti incrementali.
Non cancellare quel checkpoint mentre il task è attivo.

**Questo archivio è una fotografia del 21 ottobre:** eventuali fonti lette
successivamente dal PC non sono automaticamente incluse nel backup.
La procedura di esportazione è ripetibile; la sincronizzazione automatica
di nuovi backup su GitHub richiede ancora un meccanismo che disponga di
permessi di scrittura (il token GitHub attualmente collegato al PC non li ha
sul repository `tommyv-spec`).

Niente Git LFS, GitHub Actions/runner aggiuntivi, piani storage a pagamento,
dati utente, token o cartelle personali nella pubblicazione. Nessun merge
in produzione; le prove sorgente non equivalgono a verifica dell'apertura
effettiva di un mercato.
