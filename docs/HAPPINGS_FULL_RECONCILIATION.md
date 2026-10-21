# Happings: riconciliazione nazionale automatica, fonte → scheda DEV

Non basta trovare gli URL: serve dimostrare campo per campo se il publisher
contiene l'informazione, se è stata letta, se identifica una scheda già
pubblicata e se possiamo salvarla senza attribuirla al mercato sbagliato.

## Copertura osservata il 21 ottobre 2026 (prima scansione non ancora conclusa)

- 2.313 pagine nella coda: 106 indici settimanali italiani e 2.207 dettagli
  evento con URL valido. La home, gli archivi e le sitemap sono già stati
  controllati separatamente.
- 106 pagine provinciali interpretate: 8.053 righe fisiche della fonte.
- 6.663 gruppi di fonte distinti per provincia, Comune, giorno.
- La prima riconciliazione ha trovato **1.054 gruppi Comune/giorno la cui
  geografia ISTAT non concorda con quella della pagina Happings**.
- 2.805 gruppi hanno una località troppo vaga per diventare indirizzo.
- 490 gruppi hanno più sedi differenti nella fonte per lo stesso Comune e
  giorno: non possono ricevere un'assegnazione automatica di un indirizzo
  unico senza un'identità aggiuntiva.
- Sono emersi 53 candidati di mercato settimanale assenti dal catalogo,
  con sede specifica e Comune riconciliabile, non ancora ammessi.
- Tra gli eventi di dettaglio letti, 281 erano classificati come mercati;
  273 riportavano intervalli orari, 272 appuntamenti e 59 conflitti fra
  valori della pagina. Il numero cambierà al completamento della coda.

Questi numeri sono misure provvisorie della scansione, **non conteggi di
mercati aperti o verificati**.

### Problema generale osservato nella fonte

L'indice Happings intitolato «mercati settimanali a Alessandria e provincia»
include decine di Comuni della provincia di Biella. Un'applicazione per
provincia senza confronto ISTAT inventerebbe geografie sbagliate.
`happings_full_reconciliation.py` registra per ciascuna riga l'ambito
dell'indice, il Comune, la provincia ISTAT effettiva e una ragione di
accettazione/sospensione. Mai fidarsi della sola intestazione della pagina.

## Software già nel ciclo quotidiano DEV

- `happings_province_directory.py`: risale dalla home all'indice di
  sitemap degli articoli, individua gli elenchi provinciali italiani e
  rifiuta l'importazione da ambiti geografici non univoci.
- `happings_source_enrichment.py`: legge il listato settimanale, confronta
  i mercati già noti e applica solo gli indirizzi con ricevute valide.
- `happings_detail_discovery.py`: percorre home, archivio Mercati,
  paginazioni e sitemap; salva una frontiera riprendibile.
- `happings_detail_enrichment.py`: confronta schede evento e contenuto
  strutturato per date, orari e indirizzi dei mercati effettivi.
- `happings_weekly_admission.py`: propone automaticamente l'inserimento di
  mercati nuovi con Comune, giorno e sede unici. **La fase DEV per ora
  è review-only**: non inserisce nuovi ID finché non supera anche il
  controllo indipendente delle ammissioni. La lista è disponibile nel
  rapporto `weekly_unmatched_review`.

La sorgente con `orario = la mattina` non fornisce un orario numerico.
Il sistema conserva l'informazione qualitativa nella diagnostica, ma non
crea arbitrariamente «08:00–13:00». Le date previste e le aperture
individualmente confermate rimangono due cose distinte.

## Analisi completa riprendibile sul computer

La scansione usa, per ciascun URL:
- checkpoint atomico `checkpoint.json`;
- fonte, digest e dati estratti in `pages/<sha256(url)>.json.gz`;
- cause esplicite di fallimento o layout non valutabile.

I dati rimangono fuori dal catalogo di produzione.
L'analisi indipendente controlla che ogni file corrisponda al proprio URL
e alla propria impronta nel checkpoint prima di ricostruire gli abbinamenti.

Da root del repository:

```bash
python backend/happings_full_reconciliation.py \
  --manifest public/data/v1/manifest.json \
  --snapshot PATH_AL_CRAWL \
  --out PATH_AI_REPORT
```

Produce:

- `happings-source-worklist.json`: ogni gruppo geografico/giorno, indirizzo,
  eventuali schede esistenti e motivo di uso/sospensione;
- `happings-source-reconciliation.json`: numeri per campo, fonte, esito,
  provincia incoerente, conflitto e candidati di nuovi mercati.

Per eseguire in autonomia l'analisi **solo dopo la fine del crawl**, e
compararla al DEV più recente, esiste `happings_bulk_finisher.py`.
Controlla il checkpoint senza effettuare richieste Happings, attende il
completamento, scarica con `git fetch` i soli file statici dell'ultimo
DEV e costruisce il report. Non pubblica un market ID privo del relativo
controllo indipendente.

```bash
python backend/happings_bulk_finisher.py \
  --snapshot PATH_AL_CRAWL \
  --repo PATH_AL_REPOSITORY \
  --out PATH_AI_REPORT
```

### Regressioni

```bash
python -m unittest discover -s backend/tests -p 'test_happings_*.py'
```

Il processo esistente gestisce l'aggiornamento giornaliero del catalogo e
i gate di rilascio. La scansione completa e il finisher sono strumenti locali
senza nuovi runner, abbonamenti, servizi Cloudflare o Docker.

**Rimanente:** integrare anche i nuovi mercati settimanali con un certificato
di ammissione indipendente, riconciliare gli ambiti sbagliati e recuperare
orari esatti da altre fonti quando Happings pubblica solo una fascia
qualitativa. Non abbassare i criteri di ammissione per far salire la
percentuale apparente di completezza.
