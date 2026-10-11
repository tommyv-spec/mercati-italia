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
