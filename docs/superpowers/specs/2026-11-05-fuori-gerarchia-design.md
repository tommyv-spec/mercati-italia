# Fuori · gerarchia visiva, secondo giro — design

Data: 2026-11-05 · Stato: scelto da Claude ("Rifinire i biglietti") dopo che il proprietario non era
sicuro tra le tre strade; da rivedere sull'app DEV · Ramo: DEV

## Il problema (schermate da telefono, 390 px, 5 nov)

- Esplora, primo schermo: nessun mercato intero visibile; intestazione, Dove/Quando, invito "vicino a me",
  categorie e "In evidenza" occupano tutto.
- Il talloncino colorato del biglietto è la cosa più forte della scheda, più del nome; 115 dei 138 mercati
  del weekend sono di antiquariato, quindi la lista è un muro rosso. Il talloncino a volte dice l'ora, a
  volte solo "Antico".
- Nomi tagliati a metà ("Mercatino dell'Antiquariato di Com…") mentre la città è scritta sotto.
- Scheda: "Orario per questa data non indicato" in grande e subito sotto "09:00–19:00"; tre righe di avviso
  sulla data; "Indicazioni" sparisce scorrendo; la parte sulle fonti mescola "2026-10-28" e "28 ott 2026".
- Mappa: quattro righe di testo prima della mappa, crediti ripetuti due volte.

## Cosa cambia (look dei biglietti scelto il 1° nov: invariato)

- **Biglietto**: talloncino in tinta chiara del colore della categoria, disegno colorato, ora in inchiostro;
  senza ora resta solo il disegno. Il nome non ripete la città scritta sotto ("… di Como" → riga "Como"),
  tranne quando la città fa parte del nome ("… Città di Pistoia") o resterebbe una parola sola
  (`cardName` in `src/lib/display.js`, test in `tests/display-name.test.mjs`). "Gratis" resta (39 schede su
  134) ma in grigio: il giallo di "Data prevista" è l'unico avviso colorato.
- **Esplora**: intestazione e "In evidenza" più bassi, il primo mercato entra nel primo schermo; giorno su
  una riga; scorrendo, Dove/Quando perdono le due etichette (restano per i lettori di schermo);
  categorie a zero grigie e non toccabili.
- **Quando**: ogni scelta dice i suoi giorni (Oggi, Domani, Prossimi 7 giorni compresi).
- **Scheda**: una sola riga sulla certezza della data (l'avviso quando c'è, altrimenti l'etichetta); se la
  data non ha orari propri si mostra l'orario abituale detto come tale; Salva e Indicazioni in una barra
  sempre in fondo allo schermo (il segnalibro in alto è tolto: era doppio); "Tutte le date previste" come
  link con freccia; ordine: il mercato, etichette, consiglio, contatti, vicini, altri in città, poi un solo
  riquadro "Fonti e verifiche" con le date in un formato.
- **Mappa**: una riga sopra ("8 mercati", Lista; precise/indicative col pulsante), mappa più alta,
  crediti chiusi dietro (i) e scritti una volta sotto.

## Invariati

Dati, regole di onestà (date previste/confermate, orari solo della data o detti abituali, indicazioni
bloccate), testi controllati dai test notturni, link condivisi, nessuna chiamata a database a pagamento.
Il sito pubblico resta sull'app del tag `release-2026-11-03` finché il proprietario non rilascia.

## Prove

`node --test tests/*.test.mjs` (120 ok); `ui-smoke`, `reviewed-city-ui`, `roma-xiii-geo-hold-ui`,
`roma-xiii-2026-venues-ui`, `install-ui` PASS sul build locale. Non fatto: impaginazione da computer
(lista e mappa affiancate), da valutare dopo.
