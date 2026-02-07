# 🔧 Mercati d'Italia — Backend & Data Pipeline

## Architettura

```
┌─────────────────┐     ┌──────────────┐     ┌─────────────┐     ┌────────────┐
│  Fonti Web      │     │  Scraper     │     │  Cleaner    │     │  Firestore │
│                 │────▶│              │────▶│             │────▶│            │
│ eventiesagre.it │     │ HTML → Raw   │     │ Raw → Clean │     │  Firebase  │
│ ilturista.info  │     │ Market data  │     │ + Geocode   │     │  Admin SDK │
│ cosedicasa.com  │     │              │     │ + Dedup     │     │            │
│ siti comunali   │     └──────────────┘     └─────────────┘     └────────────┘
└─────────────────┘                                                     │
                                                                        ▼
                                                                 ┌────────────┐
                                                                 │  Frontend  │
                                                                 │  Firebase  │
                                                                 │  JS SDK    │
                                                                 └────────────┘
```

## Struttura file

```
backend/
├── config.py                # Configurazione, tipi, costanti
├── cleaner.py               # Pipeline di pulizia e normalizzazione
├── scraper_eventiesagre.py  # Scraper per eventiesagre.it
├── pipeline.py              # Orchestratore principale
├── schema.sql               # Schema SQL di riferimento (struttura logica)
├── requirements.txt         # Dipendenze Python
├── .env.example             # Template variabili d'ambiente
└── README.md                # Questo file
```

## Setup

```bash
cd backend

# Crea ambiente virtuale
python -m venv .venv
source .venv/bin/activate   # su Windows: .venv\Scripts\activate

# Installa dipendenze
pip install -r requirements.txt

# Configura Firebase Admin SDK
# 1. Vai su Firebase Console → Project Settings → Service Accounts
# 2. Clicca "Generate New Private Key"
# 3. Salva il file come serviceAccountKey.json nella cartella backend/
cp .env.example .env
```

## Utilizzo

### Scraping + export JSON (senza database)

```bash
# Scrape 3 regioni MVP → mercati_clean.json
python pipeline.py

# Scrape regioni specifiche
python pipeline.py --regioni Toscana Lombardia Sicilia

# Dry run (solo scrape e pulizia, nessun salvataggio)
python pipeline.py --dry-run --regioni Toscana

# Output file personalizzato
python pipeline.py --output dati_mercati.json
```

### Scraping + salvataggio su Firestore

```bash
python pipeline.py --db --regioni Toscana Lazio Emilia-Romagna
```

### Solo lo scraper (senza pulizia)

```bash
python scraper_eventiesagre.py Toscana Lazio
```

## Struttura Firestore

```
mercati/                          # Collezione principale
├── {slug}/                       # Documento mercato (ID = slug)
│   ├── nome: string
│   ├── slug: string
│   ├── citta: string
│   ├── provincia: string
│   ├── regione: string
│   ├── indirizzo: string
│   ├── lat: number
│   ├── lng: number
│   ├── categoria: string        # alimentare|antiquariato|vintage_abbigliamento|usato|artigianato|misto
│   ├── tags: array<string>
│   ├── status: string           # attivo|non_confermato|annullato|archiviato
│   ├── ricorrenza: string
│   ├── ricorrenza_testo: string
│   ├── orario_testo: string
│   ├── descrizione: string
│   ├── confidence: number       # 0–100
│   ├── date: array<string>      # ISO dates ["2026-02-07", ...]
│   ├── prossima_data: string    # primo elemento di date
│   ├── fonte: string
│   ├── url_fonte: string
│   ├── creato_il: string
│   ├── aggiornato_il: string
│   └── fonti/                   # Sottocollezione: provenance
│       └── {fonte_nome}/
│           ├── url_originale: string
│           ├── dati_grezzi: map
│           ├── hash_contenuto: string
│           └── ultimo_visto: string
│
utenti/                           # Dati per-utente
├── {uid}/
│   └── preferiti/               # Sottocollezione: mercati preferiti
│       └── {mercato_slug}/
│           └── creato_il: timestamp
│
fonti/                            # Registro fonti (opzionale)
├── {nome}/
│   ├── url_base: string
│   ├── tipo: string
│   └── affidabilita: number
│
segnalazioni/                     # Report della community
├── {auto-id}/
│   ├── user_id: string
│   ├── mercato_id: string
│   ├── tipo: string
│   ├── messaggio: string
│   └── creato_il: timestamp
```

## Indici Firestore

Gli indici compositi necessari sono definiti in `../firestore.indexes.json`.
Deploy con:

```bash
firebase deploy --only firestore:indexes
```

## Pipeline di pulizia (cleaner.py)

Il modulo `cleaner.py` gestisce 7 fasi:

1. **Classificazione categoria** — keyword scoring da testo italiano
2. **Parsing ricorrenza** — "ogni prima domenica del mese" → date concrete ISO
3. **Normalizzazione orari** — "dalle 9 alle 19" → "9:00–19:00"
4. **Geocoding** — Nominatim (OpenStreetMap) con fallback a livello di città
5. **Estrazione tag** — keyword matching per al chiuso/all'aperto/serale/ecc.
6. **Deduplicazione** — fuzzy name matching + prossimità geografica
7. **Hashing contenuto** — rileva cambiamenti tra scrape successivi

## Aggiungere nuove fonti

1. Crea `scraper_nomesite.py` con un generatore che yielda `RawMarket`
2. Importa e invoca il nuovo scraper in `pipeline.py` → `step_scrape()`

## Roadmap

- [x] Scraper eventiesagre.it
- [x] Pipeline Firebase/Firestore
- [ ] Scraper ilturista.info
- [ ] Scraper cosedicasa.com/mercatini
- [ ] Scraper siti comunali
- [ ] Scheduling (Cloud Functions / Cloud Scheduler)
- [ ] Sistema di verifica community
