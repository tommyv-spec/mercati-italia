# 🏪 Mercati d'Italia

Scopri i mercati rionali, dell'antiquariato, vintage e artigianali in tutta Italia.

![React](https://img.shields.io/badge/React-18-blue) ![Vite](https://img.shields.io/badge/Vite-6-purple) ![License](https://img.shields.io/badge/license-MIT-green)

## ✨ Funzionalità

- **Esplora** — cerca mercati per nome, città o parola chiave
- **Filtri** — categoria, regione, città, distanza massima
- **Mappa** — visualizzazione interattiva con pin colorati per categoria
- **Preferiti** — salva i mercati che ti interessano
- **Notifiche** — promemoria per i preferiti e avvisi per mercati vicini
- **Dettaglio mercato** — date, orari, indirizzo con navigazione, descrizione, tag e affidabilità della fonte

## 🚀 Avvio rapido

```bash
# Clona il repository
git clone https://github.com/YOUR_USERNAME/mercati-italia.git
cd mercati-italia

# Installa le dipendenze
npm install

# Avvia il server di sviluppo (modalità demo con dati di esempio)
npm run dev
```

Apri [http://localhost:5173](http://localhost:5173) nel browser.

### Collegare Firebase (dati reali)

1. Crea un progetto su [console.firebase.google.com](https://console.firebase.google.com)
2. Attiva Firestore Database (modalità produzione)
3. Aggiungi una Web App → copia la configurazione
4. Scarica la service account key per il backend
5. Popola il database:
   ```bash
   cd backend
   pip install -r requirements.txt
   # Metti serviceAccountKey.json nella cartella backend/
   python pipeline.py --db --regioni Toscana Lazio Emilia-Romagna
   ```
6. Copia `.env.example` → `.env` e inserisci i valori Firebase:
   ```
   VITE_FIREBASE_API_KEY=AIzaSy...
   VITE_FIREBASE_AUTH_DOMAIN=your-project.firebaseapp.com
   VITE_FIREBASE_PROJECT_ID=your-project
   VITE_FIREBASE_STORAGE_BUCKET=your-project.firebasestorage.app
   VITE_FIREBASE_MESSAGING_SENDER_ID=123456789
   VITE_FIREBASE_APP_ID=1:123456789:web:abcdef
   ```
7. Riavvia `npm run dev` — l'app si connette automaticamente

Senza `.env`, l'app funziona in modalità demo con 12 mercati di esempio.

### Testare su mobile (stessa rete Wi-Fi)

```bash
npm run dev
# Vite mostrerà un URL tipo: http://192.168.x.x:5173
# Aprilo dal browser del telefono
```

## 📦 Build e deploy

```bash
# Build di produzione
npm run build

# Anteprima locale della build
npm run preview
```

### Deploy su Vercel (consigliato)

1. Pusha il repo su GitHub
2. Vai su [vercel.com](https://vercel.com) e importa il repository
3. Vercel rileva Vite automaticamente — clicca **Deploy**
4. Ricevi un URL pubblico da condividere

### Deploy su Netlify

1. Pusha il repo su GitHub
2. Vai su [netlify.com](https://netlify.com) → **Add new site** → **Import from Git**
3. Build command: `npm run build` — Publish directory: `dist`
4. Clicca **Deploy**

## 🗂 Struttura del progetto

```
mercati-italia/
├── index.html              # Entry point HTML
├── package.json
├── vite.config.js
├── .env.example            # Template configurazione Firebase
├── firestore.rules         # Regole sicurezza Firestore
├── firestore.indexes.json  # Indici compositi Firestore
├── src/
│   ├── main.jsx            # Bootstrap React
│   ├── App.jsx             # Componente principale (tutte le schermate)
│   ├── lib/
│   │   └── firebase.js     # Client Firebase
│   ├── services/
│   │   └── api.js          # Layer API (Firestore + fallback demo)
│   ├── hooks/
│   │   └── useMarkets.js   # Hook dati mercati
│   └── data/
│       └── sampleMarkets.js # Dati demo (12 mercati)
└── backend/
    ├── schema.sql           # Schema logico di riferimento
    ├── config.py            # Configurazione e tipi
    ├── cleaner.py           # Pipeline pulizia e normalizzazione
    ├── scraper_eventiesagre.py # Scraper eventiesagre.it
    ├── pipeline.py          # Orchestratore scrape → clean → Firestore
    ├── requirements.txt     # Dipendenze Python
    └── .env.example         # Template credenziali backend
```

## 🛣 Roadmap MVP

- [x] Navigazione a tab (Esplora, Preferiti, Notifiche, Impostazioni)
- [x] Ricerca e filtri avanzati
- [x] Vista lista e mappa
- [x] Dettaglio mercato con date, orari, indirizzo
- [x] Preferiti con persistenza locale
- [x] Impostazioni posizione
- [ ] Backend API con dati reali
- [ ] Geolocalizzazione reale
- [ ] Notifiche push
- [ ] Scraper per aggregare dati da fonti multiple
- [ ] Dashboard admin

## 📄 Licenza

MIT
