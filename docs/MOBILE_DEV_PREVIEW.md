# DEV mobile preview — 2026-10-11

## Preview attiva (temporanea)

URL: https://share-thats-battery-fax.trycloudflare.com/

È un **Cloudflare Quick Tunnel**, non un progetto Pages persistente. L'indirizzo è pubblico per chiunque abbia il link, cambia al riavvio del tunnel e smette di rispondere quando il PC o il processo si arresta. Cloudflare offre i Quick Tunnel senza account e senza costi per test di sviluppo. Non esistono modifiche alla produzione. Riferimento ufficiale: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/

## Provenienza della build

- Branch: `improve/data-quality-security-performance-2026-10-11`
- Commit della build: `034711a33bb2100b3dde455305250562c1e87a90`
- GitHub Actions build: https://github.com/tommyv-spec/mercati-italia/actions/runs/38169192475
- Artefatto: `mercati-mobile-dev-site`; prodotto da `.github/workflows/dev-mobile-build.yml`.
- Snapshot statico: 12.650 mercati candidati, 20 regioni; nessuna promessa che siano tutti verificati.

## Hosting di test isolato

Macchina autorizzata: BOOK-V1KQL7L6GB.

- Cartella: `C:\Users\tomma\Documents\MercatiItalia-Dev\`
- Sito compilato: `site\`, servito con Python `http.server` solo su `127.0.0.1:4173`
- Tunnel esterno: `cloudflared.exe tunnel --url http://127.0.0.1:4173`
- Logs: `http-err.log`, `http-out.log`, `tunnel-err.log`, `tunnel-out.log`
- `cloudflared.exe`: release ufficiale Windows 2026.10.0 firmata `Cloudflare, Inc.` (Authenticode Status: Valid).
- Il tunnel espone solo il web server di file statici, non file privati del computer.

## Verifiche effettuate

- HTTP origin locale: 200.
- URL pubblico HTTPS: 200.
- Pagina statica pubblica e `/data/v1/manifest.json` scaricabili da una sessione esterna.
- Rendering Chrome headless su URL pubblico: 60 card mercato, nessun messaggio di caricamento bloccato, nessun errore di catalogo.
- CI della stessa linea di codice: Python tests, Vite build e QA mobile Chromium precedentemente superati.
- Il sito usa solo JSON statici per la normale visita, non Cloudflare Workers/Pages Functions né Firestore.

## Limiti

Questo è un ambiente DEV da provare sul telefono, non hosting production o URL stabile. Il laptop deve restare acceso e online. Una verifica su iPhone/Android fisici e dei dati locali rimane da completare; la revisione UX e del contenuto è ancora nella PR bozza.

## Aggiornamento: correzioni DEV e controllo pubblico (11 ottobre 2026, sessione QA)

- URL stabile finché resta attivo lo stesso processo del Quick Tunnel: **https://share-thats-battery-fax.trycloudflare.com/**
- Frontend **aggiornato** (solo DEV) da build GitHub Actions **38171786850**; commit sorgente **f6f934a39fb4b36a8d16a3de898fed38de36b620**; non è stato unito su main e la produzione non è stata modificata.
- Nuova cartella servita sul PC: `site-v2/`; servizio statico Python `dev_server.py` PID **16608** su localhost:4173, Cloudflare tunnel PID **17432** invariato. Vecchia cartella `site/` conservata come rollback; `site-ready/` build intermedia funzionante.
- Correzioni principali: errore React bloccante `useRef`, fonte dati schema v4, sostituzione SVG con MapLibre e clustering, caricamento lazy mappa, font OpenFreeMap Noto Sans per evitare glyph 404, reset città/regione, GPS negato non cancella i filtri, date previste etichettate, introduzione ricerca contestuale per città.
- Browser Chrome con emulazione iPhone13/timezone Europe/Rome, contro URL **pubblico**: **11 test di percorso PASS, 0 errori runtime JS, 0 errori console, 0 risposte HTTP fallite e 0 richieste di rete fallite**; rete esterna HTTP200, GZIP attivo sull'indice, cache per file immutabili. Primo caricamento nel test ~4,33 secondi; da rete mobile reale può variare.
- Solo anteprima gratuita e temporanea; dev server non è un Cloudflare Pages deployment persistente. Mantieni PC acceso e online. Se pagina ancora vecchia, ricarica o apri in una finestra privata, dato che il browser può aver memorizzato asset statici.
- Limiti aperti: numerosi record **previsti, non confermati**; geocoordinate indicative (circa 89 precise sul totale), orari/sedi spesso incompleti; alcune città duplicate per maiuscole/minuscole o provincia erroneamente inserita. Il catalogo **non** è certificato.
