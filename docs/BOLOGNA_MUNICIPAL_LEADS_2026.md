# Bologna 2026 — quattro nuove piste da fonte comunale

**Stato: verifica in sola lettura. Nessuna pubblicazione di nuovi mercati.**

## Prove originali

- [Comune di Bologna, 15 giugno 2026 — due nuovi mercati sperimentali](https://www.comune.bologna.it/novita/comunicati-stampa/due-nuovi-mercati-sperimentali-navile-e-borgo-panigale-reno)
- [Delibera PG 478716/2026 del 9 giugno 2026](https://atti9.comune.bologna.it/atti/wpub_delibere.nsf/$$OpenDominoDocument.xsp?action=openDocument&documentId=994D1751792FC53EC1258E130079A296)
- Dati sorgente strutturati: `backend/data/bologna-municipal-leads-2026.json`

Il comunicato distingue **due mercati annunciati** dai **due già esistenti alla data dell'annuncio**. Non dimostra che una specifica edizione del 2026 sia stata aperta.

| Sede | Cosa dice la fonte | Stato |
|---|---|---|
| Via della Cà Bianca (Navile) | Mercato sperimentale alimentare previsto da settembre, fascia 15–19, giorno non indicato | Avvio e giorno da verificare |
| Via Lorenzetti (Borgo Panigale-Reno) | Mercato sperimentale alimentare previsto da settembre, fascia 15–19, giorno non indicato | Avvio e giorno da verificare |
| Piazza Puntoni | Mercato della carta il mercoledì 9–18, marzo–giugno e settembre–dicembre | La fonte lo descrive come già attivo a giugno; nessuna edizione futura confermata |
| Piazzetta di via Vetulonia | Mercato ortofrutticolo lunedì e venerdì 7–14 | La fonte lo descrive come già attivo a giugno; nessuna edizione futura confermata |

### Confronto col catalogo esistente

Il catalogo DEV fotografato al commit `2ca995d5176de64e0c5b9139224096588c851f34` conserva 13.779 schede, di cui **13** nel Comune di Bologna. Nessuna delle quattro sedi appare nello stesso indirizzo delle 13 schede bolognesi.

**Non basta per provare che siano quattro mercati unici**: confrontare anche il dataset strutturato di Bologna, le altre sedi con toponimi varianti e la tipologia. Piazza Puntoni, ad esempio, può ospitare mercati diversi in giorni diversi (carta mercoledì, vintage martedì).

### Condizioni per aggiungere una scheda

1. Verificare l'effettivo avvio e il giorno preciso dei due mercati sperimentali. Mai indovinare il giorno dalla fascia 15–19.
2. Confermare che i due mercati descritti come già attivi il 15 giugno siano tuttora programmati, senza chiamare le date «confermate» in assenza di prove individuali.
3. Controllare **licenza e diritti di riutilizzo** della pagina municipale. La licenza del dataset open-data Bologna non si trasferisce automaticamente ai comunicati stampa. Evitare la copia dei testi protetti; conservare URL e fatti documentati soltanto per audit.
4. Verificare overlap con identità e giorni, non solo via o piazza. Nessun import se stesso mercato già presente.
5. Non assegnare coordinate stimate. Fino a verifica, niente indicazioni stradali verso un centro cittadino.
6. Solo dopo revisione, costruire adapter con ID stabili, fonte, test negativi e rilascio **solo DEV**.

La fonte è un punto di ricerca aggiornato al giugno 2026, non una conferma di funzionamento a ottobre. Nessun dato è stato modificato nella normale app.
