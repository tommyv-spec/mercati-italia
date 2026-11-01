# Fuori · UX "Dove e Quando" — design

Data: 2026-11-01 · Stato: approvato dal proprietario ("Ristrutturazione completa") · Ramo: DEV

## Il problema (prova da telefono, 1 nov)

- Il tasto Indietro del telefono esce dall'app da lista e scheda (un solo elemento nella cronologia).
- Scegliere la città: 5 tocchi passando da "Altro"; poi la lista mostra "prossimi 7 giorni" e la home
  "questo weekend" per la stessa città.
- Due sistemi di tempo (frecce weekend in home; Oggi/Weekend/7 giorni + Lun–Dom nella lista).
- "Vedi tutti" apre la lista con filtri non scelti ("Solo mercatini ed eventi ×"); la mappa eredita in
  silenzio i filtri della lista.
- Ricerca per sottostringa: "Arezzo" trova "Sarezzo"; la Fiera Antiquaria non è tra i primi cinque.
- "Ricordamelo" salva soltanto: nessun avviso esiste.
- Parole tecniche: "schede", "appuntamenti", "sede riconciliata".

## La regola

L'app risponde a una domanda: **dove vado e quando?** Dove e Quando si scelgono una volta, restano
visibili e valgono per Esplora e Mappa.

## Struttura

Tab: **Esplora · Mappa · Salvati · Altro**.

Esplora, dall'alto:
1. Fascia: Fuori + campo di ricerca (`.search-input`, unico).
2. Barra contesto (fissa in alto allo scorrimento): `📍 <Dove> ▾` e `📅 <Quando> ▾`, ognuno apre un foglio.
3. Alla prima visita, se Dove è "Tutta Italia": riquadro "Dove vuoi andare?" con *Mercati vicino a me*,
   *Scegli una città*, *Non ora*.
4. Categorie come filtri con conteggio: Tutti · Antiquariato · Vintage e usato · Artigianato · Alimentare · Gratis.
5. Riga risultati (`.results-count`): "N mercatini ed eventi · <dove> · <quando>". Con GPS: "Vicino a me ·
   50 km, posizioni precise" e il pulsante per includere le posizioni indicative.
6. In evidenza (4 locandine) solo con più di 8 eventi e categoria "Tutti".
7. Eventi raggruppati per giorno (righe con disegno di categoria), "Mostra altri".
8. Mercati settimanali della città scelta (o della più vicina col GPS) nei giorni scelti, con il gruppo per
   città esistente; link alla pagina "giorno per giorno". Senza città: invito a sceglierla.
9. Solo con "Tutta Italia": Per regione con conteggi.

Scrivendo nella ricerca, sotto la fascia compaiono i risultati al posto di 2–9: prima le città
("Mercatini a Arezzo e dintorni"), poi i mercati. Ogni parola cercata deve essere l'inizio di una parola del
nome, della città, della regione, della categoria o dei tag (niente "Sarezzo"). Accenti ignorati. La ricerca
non filtra per data e mostra "Data da verificare" dove manca.

**Dove**: Tutta Italia · Vicino a me (GPS, 50 km, posizioni precise salvo scelta) · Città (eventi entro 50 km
dal centro della città, settimanali della città) · Regione. La città scelta resta al prossimo avvio.

**Quando**: Oggi · Domani · Questo weekend (giorni passati esclusi) · Prossimo weekend · Prossimi 7 giorni ·
un giorno della settimana (il prossimo entro 7 giorni) · Tutte le date (anche senza data).

**Scheda**: "Salva" (non "Ricordamelo") e "Aggiungi al calendario" come vero promemoria; parole semplici.

**Indietro**: ogni apertura (scheda, ricerca, foglio, tab, pagina settimanali) aggiunge un passo alla
cronologia; Indietro chiude il passo in cima e non esce mai dall'app. Un link `#mercato=` aperto da fuori
torna alla home.

## Invariati

Dati, regole di onestà (date confermate/previste, posizioni indicative, indicazioni bloccate), link
condivisi e `/evento/<id>`, preferiti nel telefono, nessuna chiamata a database a pagamento.

## Test notturni

Stesse protezioni, percorsi nuovi: mercato concluso fuori dalla ricerca ma apribile dal link; "Prossimi 7
giorni" esclude i mercati senza data; Firenze: un gruppo con 4 sedi, il sabato solo Piazza I Maggio;
Albizzate una sola scheda; GPS con distanze vere e mai "circa 0 km"; mappa vera; Salvati senza promesse di
notifiche; nessun errore, nessuna chiamata a pagamento. In più: Indietro non esce dall'app.
