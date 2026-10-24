# Happings — struttura del sito, regole di comportamento e metodo ripetibile

Aggiornato 24 ottobre 2026, branch DEV `improve/data-quality-security-performance-2026-10-11`.
Questo documento sostituisce la lettura dei dieci `HAPPINGS_*.md` precedenti per capire **dove stanno
i dati, come leggerli e cosa fa il programma ogni settimana**. I documenti precedenti restano lo storico.

## In breve

- Su Happings i mercati stanno in **due soli posti**: le **107 pagine settimanali provinciali** e le
  **pagine evento** della categoria Mercati (≈300). Tutto il resto (blog, sagre, concerti) non serve.
- Una pagina settimanale dà per ogni mercato **solo quattro fatti**: comune, giorno, luogo, mattina/pomeriggio.
  **Mai orari esatti.** Per circa metà dei mercati il luogo è soltanto «in centro».
- Le pagine evento hanno dati ricchi (orario esatto, via, coordinate, tutte le date) in un blocco
  schema.org `Event`.
- Il programma settimanale rilegge le 107 pagine, completa i campi mancanti con prova della fonte,
  ripara i giorni troncati e unisce (senza cancellare) le schede doppie. Pubblica solo in DEV.

## 1. Struttura del sito

### Inventario (sitemap del 24/10/2026)

| Tipo di pagina | Indirizzo | Quante | Utile? |
|---|---|---|---|
| Elenco settimanale provinciale | `/it/mercati-settimanali-a-<provincia>-e-provincia/` | 157 (107 italiane, 50 spagnole) | **Sì, fonte principale** |
| Stesso elenco in DE/EN | `/de/wochenm-c3-a4rkte-…`, `/en/weekly-markets-…` | 251 | No (copie tradotte) |
| Dipartimenti francesi | `/it/mercati-settimanali-nel-dipartimento-di-…/` | 95 | No |
| Vecchia pagina per comune | `/it/mercato-settimanale-a-<comune>.html` | – | Solo come link: **reindirizza** alla pagina provinciale |
| Vecchia pagina provinciale | `/it/mercati-settimanali-a-<provincia>.html` | – | Reindirizza alla pagina `-e-provincia/` |
| Evento | `/it/happing/<nome>/` (+ 5 lingue, + `/all/happing/`) | 2.252 italiani | Sì, solo categoria Mercati |
| Categorie evento | `/it/categoria-evento/<categoria>/` | 19 italiane | Indice: `mercati`, `mercatini-natale`, `mercatini-antiquariato` |
| Luoghi, organizzatori, post | `/it/category/…`, `/it/organizer/…` | ≈6.800 | No |

Le sitemap `post-sitemap.xml` (≈1 MB) sono **molto lente** e vanno spesso in timeout: per questo la lista
delle 107 pagine italiane osservate è salvata in `backend/data/happings-weekly-pages.json` e la scoperta
via sitemap serve solo ad aggiungere pagine nuove.

### Pagina settimanale provinciale (layout standard, 106 pagine su 107)

Dentro `<div class="happings-seo-content">` si ripete questo schema:

```html
<h3>Mercati del mercoledì nei comuni di Pistoia</h3>
<ul>
  <li>a Agliana, in Piazza Don Ceccarelli (la mattina)</li>
  ...
</ul>
```

Riga = `a <comune>, in <luogo> (<la mattina|il pomeriggio>)`. Il lettore è
`backend/happings_weekly_layout.py`: se anche una sola riga non segue lo schema, **rifiuta l'intera pagina**
(meglio nessun dato che un giorno sbagliato). La breadcrumb in alto
(`EVENTI NEL MONDO | ITALIA | <provincia>`) distingue le pagine italiane da quelle spagnole.

**Lucca** usa un layout editoriale nuovo (`hpe-editorial--local-guide`) con frasi tipo «si svolge in … il
martedì, dalle 8 alle 13»: è letto da `happings_editorial_weekly_layout.py`. Se Happings estende questo
layout ad altre province, comparirà come `layout_changed` nei report.

### Particolarità dei dati settimanali (tutte gestite dal codice)

| Cosa scrive Happings | Esempio | Come lo trattiamo |
|---|---|---|
| Solo «in centro» | `a Cingoli, in centro` | Salvato come `centro`; l'app lo mostra come sede generica, mai unito ad altre sedi |
| Confini pre-2009 | Comuni di Monza-Brianza nella pagina Milano, BAT in Bari/Foggia | `PAGE_EXTRA_PROVINCES` in `happings_source_enrichment.py` |
| Quartieri di Roma | `a CASILINO, in VIA DEL PIGNETO` | Accettati se il record è della stessa provincia della pagina |
| Bancarelle numerate, comuni rinominati o fusi, refusi | `Ancona 1`, `Popoli` (ora Popoli Terme), `Trivero`, `Alessandriaa` | Come sopra: nome non ISTAT → vale la provincia della pagina |
| Province sarde storiche | Carbonia-Iglesias, Medio Campidano, Ogliastra | Alias ISTAT CI / VS / OG |
| Due pagine per una provincia | Olbia e Sassari (SS) | Entrambe lette, una URL per pagina |
| Nomi di province spagnole uguali a comuni italiani | Burgos (SS), Lugo (RA) | Escluse dalla lista: breadcrumb `spagna` |
| Data di modifica della pagina | `dateModified 2025-10-24` | Registrata; vedi limite sulle date previste (§6) |

### Pagina evento (`/it/happing/<nome>/`)

Il blocco `<script type="application/ld+json">` con `@type: Event` contiene `name`, `startDate`/`endDate`
(prossima data con orario), `eventStatus`, `location.address` (via, comune, regione) e `location.geo`
(coordinate). La pagina visibile ripete i dati e aggiunge «Tutte le date» (elenco completo) e
«Informazioni utili» (periodo, orario, indirizzo). Il lettore è `happings_detail_layout.py`; l'autopilota
giornaliero legge fino a 128 pagine evento per giro.

Attenzione: la sitemap contiene anche eventi **rimossi**. Esempio:
`/all/happing/mercatino-delle-pulci-a-lana/` risponde con «Questo Happing sembra essere scomparso» (404).
Un URL in sitemap non prova che l'evento esista.

## 2. Come comportarsi con Happings

Le regole sono nel registro `backend/data/happings-rights-review.json` e il codice le verifica a ogni giro:

- **Autorizzazione:** estrazione, elaborazione e ripubblicazione autorizzate per istruzione esplicita del
  titolare del progetto (19/10/2026). Le lettere di licenza fornite non sono autenticate: il registro lo dice.
- **Canale:** solo **DEV**. PROD richiede una nuova decisione esplicita.
- **Rete:** leggere `robots.txt` a ogni giro; almeno **3 secondi** tra due pagine; user agent
  `MercatiItaliaMarketFields/1.0`; niente browser, Docker o servizi a pagamento.
- **Dati:** non salvare l'HTML delle pagine in Git (solo impronte SHA-256 e fatti estratti); non cancellare
  mai un ID di mercato; non dichiarare mai un mercato «confermato»; non inventare orari esatti.
- `robots.txt` di Happings blocca solo i crawler di addestramento IA (GPTBot, Google-Extended,
  Applebot-Extended); l'accesso generale è permesso.

## 3. Il metodo ripetibile

### Ogni lunedì alle 03:05 UTC (`.github/workflows/happings-weekly-fields.yml`, su `main`)

1. `happings_bulk_snapshot.py --weekly-only` legge le pagine della lista salvata più quelle trovate in
   sitemap, con le regole del §2, e ritenta una volta le pagine fallite.
2. `happings_bulk_catalog_publish.py --install` esegue `enrich()` di `happings_bulk_catalog_enrichment.py`:
   - **orario qualitativo**: «La mattina» / «Il pomeriggio» se tutte le righe del comune in quel giorno
     dicono lo stesso;
   - **via**: solo se la pagina elenca un solo mercato per comune e giorno e non c'è una via diversa salvata;
   - **«centro»**: se è tutto ciò che la pagina dice, per l'unico mercato elencato e mai accanto a una via esatta;
   - **giorno troncato** (`settimanale - me`, oppure solo `settimanale`): riparato solo se la pagina lascia
     **un solo** giorno compatibile con le lettere rimaste;
   - **schede doppie**: se la pagina elenca **un** mercato per comune e giorno, tutti i record Happings che
     la citano per quel comune e giorno sono quel mercato. Si tiene il più completo (preferendo quello con la
     via elencata, poi quello già tenuto prima) e gli altri ricevono `duplicato_di`. Con più mercati
     elencati si uniscono solo i record con la **stessa via elencata**.
   - Ogni valore scritto porta una ricevuta (`riscontri_campi`) con URL e impronta della pagina.
   - I marcatori `duplicato_di` sono ricalcolati solo per i record valutati in quel giro; un marcatore che
     punta a un record sparito o a sua volta doppio viene tolto.
3. Lo stesso script riesegue export, `validate_static.py`, audit e i cancelli della policy autopilota;
   se qualcosa non passa, non installa nulla. Se non c'è niente da cambiare termina con `no_changes`.
4. Tutta la suite `backend/tests` deve passare sul catalogo aggiornato; poi commit su DEV.
5. L'autopilota giornaliero (04:17 UTC) ricostruisce l'anteprima DEV: le modifiche appaiono lì.

### Schede doppie nell'app (soft merge)

Il record doppio **resta** nei file (ID, preferiti e ricevute non si perdono). L'indice compatto ha una
colonna in più (`index_schema` 7: `duplicato_di`). `splitDuplicates()` in `src/services/staticMarkets.js`
nasconde le copie da elenco, mappa e contatori; i preferiti e i link vecchi aprono il record tenuto.

### Eseguire a mano: prima un pilota, poi tutto il sito

Ogni modifica al metodo si prova **prima su poche pagine**, si controlla ogni cambiamento contro il testo
della pagina, e solo dopo si esegue su tutte le 107 pagine.

```bash
# 1. Pilota: poche province scelte per coprire i casi particolari (nessuna installazione)
python backend/happings_bulk_snapshot.py --weekly-only --provinces pistoia,pescara,milano,roma,modena,ogliastra --out /tmp/pilot
python backend/happings_bulk_catalog_publish.py --repo . --snapshot /tmp/pilot --out /tmp/pilot-release
#    → leggere /tmp/pilot-release/happings-field-changes.json e confrontare ogni modifica con la pagina

# 2. Tutto il sito, solo se il pilota è corretto
python backend/happings_bulk_snapshot.py --weekly-only --out /tmp/happings-weekly
python backend/happings_bulk_catalog_publish.py --repo . --snapshot /tmp/happings-weekly --out /tmp/release --install
python -m unittest discover -s backend/tests
```

Il 24/10/2026 il pilota sulle 6 province sopra ha prodotto 451 modifiche (70 luoghi, 20 fasce orarie,
20 giorni riparati, 341 copie unite), tutte confermate una per una sul testo delle pagine con un lettore
indipendente.

Su Windows: clonare con `git -c core.autocrlf=false clone …` (altrimenti 3 test di impronta falliscono)
e impostare `PYTHONUTF8=1`. Il comando è idempotente: rieseguito sullo stesso catalogo dà `no_changes`.

## 4. Le altre fonti del progetto (contesto)

| Fonte | Tipo | Record principali | Cosa dà | Stato |
|---|---|---|---|---|
| Happings | sito, autorizzazione progetto | 9.831 | comune, giorno, luogo, mattina/pomeriggio | attiva (questo metodo + autopilota) |
| eventiesagre.it | sito | 2.197 | indirizzo, orari, date di edizione | rilettura pagine esistenti |
| Regione Lombardia MERCap | open data CC0 | 1.128 | indirizzo, giorno, **orari esatti**, coordinate | attiva, completa anche 387 record Happings |
| cosedicasa.com | sito | 432 | indirizzo, orari | rilettura pagine esistenti |
| Comune di Milano | open data CC BY 4.0 + PDF 2026 | 85 | orari, giorno, coordinate | attiva |
| Roma Capitale d881 | open data | 70 | indirizzo, orari | attiva (solo orari) |
| Bologna, Firenze, Corciano | open data CC BY 4.0 | 39 / 4 / 2 | via, orari | attive |
| Citynews (28 siti) | siti | ≈94 | indirizzo, orari, date | rilettura limitata |
| Veneto XLSX 2026 | open data | 0 | sagre e fiere, non mercati | solo audit |

Elenco completo dei metodi per fonte in `docs/OFFICIAL_ENRICHMENT_METHOD.md`,
`docs/REGIONAL_FIELD_RECONCILIATION_2026-10-18.md` e `docs/HIGH_YIELD_MARKET_SOURCES_2026-10-17.md`.

## 5. Risultato del 24 ottobre 2026

| Record Happings (9.831) | prima | dopo |
|---|---|---|
| con mattina/pomeriggio | 8.040 | 9.066 |
| con luogo (via o «centro») | 7.866 | 9.206 |
| giorno troncato riparato | – | 210 |
| copie unite (`duplicato_di`) | – | 2.830 |
| voci doppie visibili nelle card città | 1.457 | 47 |

Tutti i 14.008 ID conservati; cancelli di rilascio `all_policies_pass`; nessun orario inventato.

## 6. Limiti noti e prossimi passi

- **Orari esatti in Lombardia — risolto il 25/10/2026.** Regola di precedenza in
  `official_enrichment.py`: l'orario esatto MERCap sostituisce «La mattina»/«Il pomeriggio» solo se
  (1) MERCap ha un solo mercato in quel comune e giorno, (2) l'orario inizia nella stessa fascia e
  (3) la via salvata è vaga oppure condivide almeno una parola distintiva con quella ufficiale.
  Altrimenti il record non viene toccato. Pilota CO/BG/VA: 85 orari; tutta la Lombardia: 273, tutti
  verificati sulle righe grezze MERCap. Lo applica l'autopilota giornaliero.
- **Date previste per i 210 giorni riparati.** Il generatore di date accetta una ricorrenza solo se la
  fonte è aggiornata da ≤180 giorni; le pagine Happings risultano modificate il 24/10/2025. Le date
  arriveranno quando Happings aggiornerà le pagine, oppure con una decisione esplicita sulla policy.
- **47 doppioni visibili** restano tra fonti diverse (es. Happings + eventiesagre): serve un
  confronto tra fonti, non coperto da questo metodo.
- **563 combinazioni comune/giorno** in cui Happings elenca più mercati di quelli presenti nell'app:
  candidati per l'ammissione di nuovi mercati (`happings_weekly_dev_admission.py`).
