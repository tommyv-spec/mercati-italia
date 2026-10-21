# Happings: ciclo automatico e ripetibile di acquisizione, verifica, ammissione DEV

Le operazioni sono gestite per **fonti e formati**, non mediante correzioni
manuali a singoli mercati. Le identità e gli indirizzi sono vincolati alle
prove del publisher; senza prove, nessun dato nuovo viene pubblicato.

## Acquisizione locale quotidiana

Il task Windows già installato `MercatiItalia-HappingsDaily` parte alle
09:30 ora italiana quando l'utente è connesso e il computer è disponibile.
L'unico entrypoint è:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "$env:LOCALAPPDATA\mercati-italia\scraper-code\scripts\happings-daily-windows.ps1"
```

Lo scheduler usa il clone dedicato del DEV, aggiorna il codice senza
sovrascrivere altri progetti, esegue **Python in UTF-8** (indispensabile
per i nomi ISTAT con accenti), lancia i test Happings e poi:

1. Ricontrolla `robots.txt`, sitemap e gli URL già scoperti; rispetta
   i limiti per il publisher e usa checkpoint atomici e un lock per
   impedire crawler concorrenti sulla stessa directory.
2. Rilegge incrementalmente soltanto pagine nuove/scadute;
   non cancella una lettura valida se una richiesta fallisce.
3. Riconcilia le 106 province lette, le schede evento, indirizzi, orari
   pubblicati, candidati nuovi, collisioni, luoghi ISTAT e calendari.
4. Riesegue la **preview** dei mercati settimanali usando HTML live e
   riscontri crittografici, applica tutti i controlli del catalogo
   in un'area temporanea e produce un report locale.
5. Conserva l'HTML usato per le ammissioni in file `gzip` con
   nome legato all'hash del contenuto e URL, **solo sul computer**.

La parte locale è volutamente **read-only verso GitHub**: sul computer,
il token attualmente collegato può leggere questo repository ma non può
effettuare push. La procedura non tenta più un push che fallirebbe.

## Pubblicazione automatica soltanto su DEV

L'**Autopilot GitHub già esistente** è programmato una volta al giorno
nella workflow `.github/workflows/market-autopilot.yml` sul branch `main`,
alle 04:17 UTC. Non sono stati creati nuovi job o runner a pagamento.

Il job esistente `publish_dev` (permesso `contents:write`) continua
a eseguire la propria acquisizione, export e QA complessiva. Nella sua
**stessa esecuzione** il modulo `happings_weekly_dev_admission.py`
può rigiocare soltanto le pagine HTML provinciali già osservate da
`happings_autopilot.py`, verificate sul checkpoint e sul contesto
immutabile `autopilot-output/sources/happings-pages.json`. Il
publisher non viene nuovamente contattato per questo passaggio.

La nuova ammissione:
- è limitata a **32 nuovi mercati per ciclo**, con ulteriori casi
  elaborati nei giorni successivi quando riappaiono nelle fonti;
- richiede Comune ISTAT univoco, una sola sede specifica nella pagina,
  giorno settimanale esplicito, nessun mercato esistente compatibile e
  un riscontro sui campi con URL/HTML SHA/date e identità;
- esegue prima replay del parser, poi normalizzazione, prova esatta
  degli ID, `validate_static` e i gate nazionali
  `autopilot.compare_candidates`;
- non modifica né elimina **alcuna scheda esistente**;
- produce nuove schede `non_confermato`, senza coordinate, orari
  numerici o date future inventate;
- salva soltanto i contenuti statici `public/data/v1` e li spinge
  su DEV con un push **non forzato**. Un aggiornamento concorrente
  blocca la pubblicazione.

La preview statica isolata viene aggiornata solo dopo un export valido,
con indici e manifest coerenti. Nessun codice o catalogo di produzione
è modificato.

I dettagli Happings (date e intervalli orari) rimangono nel precedente
sistema DEV `happings_detail_autopilot.py` con verifica indipendente
e provenienza individuale. Non trasformare etichette qualitative come
«la mattina» in orari di apertura esatti.

## Controlli, dati e tracciabilità

Rapporti locali in `%LOCALAPPDATA%\mercati-italia\happings-reconciliation`:
`happings-local-run.json`, `happings-source-reconciliation.json`,
`happings-source-worklist.json`, `happings-detail-match-report.json`,
`happings-weekly-admission.json` e archivio HTML
`happings-source-html/`.

I rapporti di GH Actions restano negli artefatti dell'Autopilot e nel
riepilogo del run. Il job si ferma ai primi errori; nessuna quantità
di URL equivale da sola a una conferma che un mercato operi oggi.

### Verifica indipendente dopo ogni commit DEV

`backend/happings_postrelease_audit.py` è eseguito dallo **stesso**
job GitHub esistente, solo quando l'ammissione ha pubblicato nuovi ID.
Rilegge **i record realmente salvati** da `git show HEAD^:` e
`git show HEAD:`, verifica gli hash degli asset e ricostruisce le
ammissioni dalla cattura HTML originale già contenuta nel checkpoint
dell'Autopilot. La release passa soltanto se:
- tutti i record preesistenti sono identici byte-per-campo;
- non è sparito nessun ID e i nuovi ID coincidono esattamente con il report;
- i nuovi record equivalgono ai dati normalizzati dal parser HTML originale;
- nessun orario numerico, data futura, coordinate o apertura verificata
  è stata inventata dalla nuova ammissione;
- il manifest pubblicato coincide con quello verificato nel batch.

La prima prova reale sul commit `54afb270` ha confermato **13.981
record invariati, 18 aggiunti, zero eliminati**, rigiocando le 10
pagine Happings utilizzate dal job. Una discrepanza fa fallire il
job e impedisce la successiva pubblicazione della preview isolata.
Il report viene registrato nel riepilogo e nel checkpoint temporaneo
dell'esecuzione, senza nuovi runner.

Da un clone Git completo con un archivio del checkpoint già disponibile:

```bash
python backend/happings_postrelease_audit.py \
  --before HEAD^ --after HEAD --repo . \
  --source-dir autopilot-output \
  --admission autopilot-output/happings-weekly-admission.json \
  --out autopilot-output/happings-postrelease-proof.json
```


I dati non presenti nel publisher devono essere cercati in altre fonti
indipendenti. La procedura non inventa orari, coordinate o conferme.

### Riprodurre una simulazione senza pubblicazione

```powershell
python -X utf8 -m unittest discover -s backend/tests -p "test_happings_*.py"
python -X utf8 backend/happings_daily_local.py
python -X utf8 backend/happings_weekly_dev_admission.py
```

Nella workflow GH, la modalità ammissione usa invece:
`--from-autopilot-output autopilot-output --publish-dev`,
con permessi limitati a quel job e con tutta la QA già approvata.
