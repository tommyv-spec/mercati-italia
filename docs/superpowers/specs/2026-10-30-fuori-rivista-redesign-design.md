# Fuori · redesign "Rivista" — design

Data: 2026-10-30 · Stato: approvato dal proprietario (direzione A, "Rivista") · Ramo: DEV

## 1. Perché

L'app mostra 9.127 mercati vivi come card tutte uguali. 7.300 sono mercati comunali settimanali
(categoria `misto`), utili per "dov'è il mercato oggi" ma noiosi da sfogliare; circa 1.800 sono
mercatini ed eventi (antiquariato, vintage, usato, artigianato, feste alimentari, mensili), che sono
quelli che la gente sfoglia per piacere. Finché i due gruppi condividono la stessa card nello stesso
elenco, la home resta monotona. La home attuale mostra inoltre cinque righe di comandi prima del
primo contenuto, usa il terracotta ovunque e non mostra indirizzo, cadenza, descrizione o ingresso,
che il catalogo ha (file regionali: indirizzo 96 %, cadenza 96 %, descrizione 65 %).

Riferimento: la struttura di vintagery.it (sezioni per weekend con conteggio, card con contenuto,
scheda ordinata cosa/quando → prossima apertura → fatti → testo → vicino → fonte).

## 2. Obiettivi e non obiettivi

Obiettivi
- Home da rivista: "Questo weekend" con frecce, eventi con contenuto vero, settimanali raggruppati
  per città in un blocco a parte, "Per regione".
- Scheda nell'ordine di Vintagery.
- Un solo sistema visivo (sezione 6), senza card con ombra, bordi colorati o emoji.
- App.jsx spezzato in schermate e componenti; stili in CSS.
- Tutto su DEV, verificato con build + test + anteprima Firebase (canale `dev`). Mai PROD.

Non obiettivi (dopo, se mai)
- Pagine statiche per mercato e immagini di condivisione (OG).
- Notifiche push.
- Correzioni ai dati (es. doppione Fiera Antiquaria di Arezzo da due fonti).
- Cambiare i servizi dati, le librerie `src/lib/*` o lo schema dell'indice nazionale.

## 3. Schermate

Tab in basso: **Esplora · Mappa · Agenda · Altro**. "Preferiti" e "Agenda" si fondono in Agenda.

### 3.1 Esplora (home)
1. Fascia inchiostro: wordmark "Fuori" + "Mercatini d'Italia"; campo ricerca; stepper weekend
   (‹ Questo weekend ›, sotto "sabato 31 ottobre · domenica 1 novembre"); riga "N mercatini ed
   eventi in Italia · Vicino a me".
2. Riga categorie (pillole): Antiquariato · Vintage e usato · Artigianato · Alimentare · Settimanali.
3. Sezione "Questo weekend" (o "Prossimo weekend" dopo le frecce): le prime 8 righe evento,
   poi "Vedi tutti i N ›" → Lista.
4. Sezione "Il mercato oggi · <giorno> · <città>": fino a 3 settimanali aperti oggi nella città
   scelta/rilevata, poi "Tutti i N mercati di oggi a <città> ›" → Settimanali. Senza posizione né
   città: il blocco invita a scegliere la città (link a Altro › Posizione).
5. Sezione "Per regione": griglia 2 colonne con le 10 regioni con più eventi, "Tutte le 20 regioni ›".
Con posizione nota (GPS o città manuale): la sezione 3 diventa "Questo weekend vicino a te" (≤ 50 km,
ordinata per distanza, con km) e la 4 usa la città della posizione.

### 3.2 Lista
Si apre da "Vedi tutti", dalla ricerca, da una categoria, da una regione. Mantiene il motore di
oggi (ricerca, filtri categoria/regione/città/giorno/distanza, ordine) con una veste nuova:
ricerca in alto, intestazioni per giorno sticky, righe evento, un solo bottone "Filtri" che apre un
foglio con tutti i filtri, chip attivi rimovibili sotto la ricerca, `.results-count` come oggi.
Il filtro "Settimanali" mostra i settimanali raggruppati per città (componente `WeeklyCityGroup`
già esistente, rivestito).

### 3.3 Settimanali di una città
Titolo "Mercati settimanali a <città>", righe raggruppate per giorno della settimana (Oggi in cima),
una riga per mercato: nome, quartiere/indirizzo se noto, orario. Tocco → Scheda.

### 3.4 Scheda mercato
Ordine: barra (indietro, condividi, salva) → occhiello "categoria · cadenza" → nome → città ·
regione · indirizzo breve → pannello "Prossima apertura" (data grande, seconda data se weekend,
orario, riga qualità data: "confermata dalla fonte, letta il …" / "prevista dalla cadenza" /
"da verificare"; bottoni Ricordamelo (= salva in Agenda) e Indicazioni; link "Calendario" = .ics) →
fatti (Orario, Ingresso, Dove, Organizza/Posteggi quando noti) → "Tutte le date previste (N)"
ripiegato → "Il mercato" (descrizione, "Leggi tutto") → "Consiglio pratico" (se `consigli`) →
"Questo weekend, qui vicino" (≤ 4, ≤ 30 km, dedupe per nome, km) → tag → riga fonte ("Scheda
verificata il …", fonti, "Segnala un errore" = mailto esistente, "Altri mercatini in <regione> ›").
Le note di sicurezza di oggi (posizione indicativa, navigazione sospesa, conflitti campi, evidenza
editoriale) restano, nello stesso tono quieto, sotto i fatti.

### 3.5 Mappa
Parte centrata sulla posizione o sulla città scelta (zoom città); senza nessuna delle due, sull'Italia
ma con i soli eventi del weekend. Puntini colorati per categoria, settimanali grigio chiaro,
"Mostra solo posizioni precise" resta come interruttore nel foglio Filtri. Tocco → card compatta
in basso → Scheda.

### 3.6 Agenda
Mercati salvati ordinati per prossima data, raggruppati Oggi / Questo weekend / Prossimi / Senza data;
ogni riga con "Calendario"; stato vuoto: "Nessun mercato salvato" + 3 eventi del weekend suggeriti.
Nota notifiche push come oggi.

### 3.7 Altro
Posizione (GPS / città manuale / nessuna, come oggi), "Informazioni" (cos'è Fuori, fonti, catalogo
statico), "Segnala un errore" (mailto), versione.

## 4. Dati

### 4.1 Regola settimanale / evento (`src/lib/cadence.js`, e Python nell'esportatore)
Un mercato è **settimanale** se `proiezione_regola.kind == "weekly"` oppure un tag tra
`settimanale`, `mercato settimanale`, `mercato comunale`, `MERCAP`. Altrimenti è **evento**.
Lato app, l'indice nazionale non porta `proiezione_regola`: un mercato è evento se e solo se compare
nel file eventi (4.2). Ripiego senza file eventi: `categoria !== 'misto'` e nessun tag settimanale.

### 4.2 File eventi (nuovo, esportatore `backend/export_static.py`)
`data/v1/eventi-{hash}.json` = `{"schema": 1, "eventi": [[slug, indirizzo, ricorrenza_testo,
descrizione_breve, ingresso, consigli, organizzatore], …]}` per i soli eventi (4.1) vivi
(non `concluso`, non `duplicato_di`). `descrizione_breve` = descrizione tagliata a 240 caratteri
sull'ultimo confine di frase o parola, "…" in coda se tagliata. Stima: ~1.800 righe, ~0,5 MB.
Manifest: `"events": "<path>"`, `"events_schema": 1`. Il cortocircuito "unchanged" dell'export
richiede anche che il file eventi esista. Scritto con `_write_asset` (immutabile, hash nel nome).
Test Python/JS: una riga per campo, taglio della descrizione, settimanale escluso, manifest.

### 4.3 Caricamento (`src/services/staticMarkets.js`)
`fetchCatalog` carica indice e file eventi in parallelo; `normalize` fonde i campi eventi nel record
(`indirizzo`, `ricorrenza_testo`, `descrizione`, `ingresso`, `consigli`, `organizzatore`,
`isEvent: true`). File eventi assente o non valido → ripiego 4.1, mai errore bloccante.
Il dettaglio regionale resta come oggi (`fetchMarketById`).

### 4.4 Weekend (`src/lib/weekend.js`)
`weekendOf(date, offset=0)` → `{sat, sun, label, sub}`; "questo weekend" = il sabato+domenica che
contiene oggi se oggi è sabato o domenica, altrimenti il prossimo. Le frecce spostano di ±1 weekend
(massimo +8, i dati proiettati arrivano a ~120 giorni). "Oggi" e "Domani" restano come filtri rapidi
nella Lista.

## 5. Codice

```
src/
  App.jsx            guscio: tab, mercato aperto, posizione, preferiti, hash #mercato=, toast
  styles.css         token + componenti (sostituisce la stringa `styles` in App.jsx)
  screens/Home.jsx  List.jsx  Weekly.jsx  Detail.jsx  MapScreen.jsx  Agenda.jsx  More.jsx
  ui/                Icon.jsx  EventRow.jsx  WeeklyRow.jsx  Section.jsx  Pill.jsx  Button.jsx
                     TabBar.jsx  SearchField.jsx  WeekendStepper.jsx  FilterSheet.jsx  Skeleton.jsx
  lib/cadence.js  lib/weekend.js   (nuovi; il resto di lib/ invariato)
  services/staticMarkets.js         (solo 4.3)
  components/MarketsMap.jsx  WeeklyCityGroup.jsx   (rivestiti, logica invariata)
```
Lo stato condiviso passa per props da App; niente store nuovi. Le funzioni di utilità oggi in App.jsx
(getDateBadge, dateLeaf, dayHeaderLabel, uniqueByName, downloadCalendarEvent, reportUrl, haversine)
vanno in `src/lib/display.js` e `src/lib/calendarFile.js`.

Contratto DOM mantenuto per i test notturni: `.results-count`, `.market-card`, `.market-card-open`,
`.card-name`, `.card-city` (testo = città esatta), `.card-distance` (solo con posizione, mai
"circa 0 km"), "Mercati vicino a me", `.search-input`, `.detail-page`, `.detail-back`,
`.detail-address`, bottone "Condividi questo mercato", `.bottom-tabs` con Esplora/Mappa/Agenda/Altro,
`.manual-city-input input`, "Filtra città", `.toast`, "Azzera filtri", "Mostra mercati del sabato",
"Togli filtro giorno", `[data-testid="weekly-city-group"]`, testo notifiche in Agenda.
I test `tests/ui-smoke.mjs`, `reviewed-city-ui.mjs`, `roma-xiii-*.mjs` si aggiornano dove il
percorso cambia (es. tab "Preferiti" → "Agenda"), mantenendo ogni controllo di comportamento.

## 6. Sistema visivo

Token: carta `#FDFBF7`, beige `#F5F0E8`, riga `#E8E0D4`, sabbia `#D4C5A9`, inchiostro `#2C2416`,
testo secondario `#5C513F`, testo attenuato `#6C6255`, terracotta `#B94439` (link, tab attiva,
occhielli "Oggi"), oliva `#446E47` (ingresso gratuito, confermato), colori categoria esistenti per
i puntini mappa. Font: DM Serif Display (titoli), Source Sans 3 (testo). Scala: 11 occhiello
maiuscolo spaziato / 13 nota / 14 testo riga / 15 testo / 20–22 titolo riga e sezione / 26–32 titoli
grandi. Raggio 12–16 px solo su campo ricerca, pannelli e bottoni. Tocchi ≥ 44 px. Contrasto ≥ 4.5:1.
Niente ombre, bordi colorati, emoji; icone a tratto (Icon esistente, ampliato).

Stati: caricamento = 4 righe segnaposto; vuoto = frase + azione (prossimo weekend / togli filtri /
scegli città); errore = "Catalogo non raggiungibile" + Riprova; offline = banner sottile.

## 7. Comportamenti invariati

Link `#mercato=<id>`; preferiti in localStorage; posizione GPS / città manuale; motore di ricerca e
filtri; file calendario; mailto "Segnala un errore"; service worker e catalogo statico; revalidazione
catalogo ogni 30 minuti.

## 8. Passi di consegna (ognuno: build, `node --test tests/*.test.mjs`, test UI Playwright,
redeploy canale `dev`, commit su DEV quando il lock del runner è assente)

1. `styles.css` + guscio App + TabBar + Icon + lib display/calendarFile (app identica, solo spostata).
2. Home + weekend.js + cadence.js + EventRow + Section + Pill + WeekendStepper + stati.
3. Lista + FilterSheet + Settimanali + test UI aggiornati.
4. Scheda.
5. Mappa, Agenda, Altro.
6. Esportatore: file eventi + manifest + test; `staticMarkets` legge il file; ripiego verificato.

## 9. Rischi

- Il file eventi arriva su DEV solo dopo un export notturno: finché manca, il ripiego per categoria
  mette tra gli eventi i mercati alimentari settimanali (Campagna Amica). Accettato, temporaneo.
- Laptop da 16 GB: build e test uno alla volta, mai due server di anteprima.
- Il runner notturno esegue i test UI: ogni passo lascia i test verdi prima del push.
