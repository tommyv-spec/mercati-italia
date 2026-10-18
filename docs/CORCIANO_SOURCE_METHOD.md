# Corciano — fonte comunale osservata prima dell'automazione

Data osservazione: 12 ottobre 2026. Fonte originale letta in sola modalità pubblica (CSV integrale, 4 righe), senza modificare il sito.

- CSV originale: https://comune.corciano.pg.it/download/oggetto_documenti/372/1O__Oelenco-mercati-settinamanali-comune-corciano.csv
- Scheda dell'ente: https://comune.corciano.pg.it/area_letturaDocumento/29645/pagsistema.html
- Candidatura nel catalogo nazionale: dati.gov.it / ID \`62be39fe-adbe-464a-84b1-85bc060b75d2\`.
- Licenza indicata sul sito del Comune: CC BY 4.0. Conservare l'attribuzione e il collegamento.
- Data dichiarata del dataset nel registro nazionale: \`07-01-2026\` (7 gennaio 2026); il sito riporta **aggiornamento pagina** 27 luglio 2026. Il cambio della pagina *non conferma* un cambio dei quattro mercati.
- Il testo descrittivo della pagina parla erroneamente di *protocolli* invece che di mercati: NON usarlo per inferire contenuto, stato o orari.
- La sorgente non presenta un ID mercato univoco: i nostri ID derivati dal nome ufficiale vanno conservati stabilmente, e un cambiamento nel nome richiede revisione deduplicazione.

## Quattro casi verificati nel file reale

| Denominazione ufficiale | Giorno scritto | Via/piazza | Orario dichiarato | Valore colonna long | Valore colonna lat |
|---|---|---|---|---|---|
| MERCATO DI MANTIGNANA | LUNEDI | PIAZZA GIOVANNI ERCOLANI | 07:30–14:00 | 43.16083199538295 | 12.285842603579857 |
| MERCATO DI SAN MARIANO | MARTEDI | VIA ALDO MORO | 07:30–14:00 | 43.089055028914366 | 12.309725879769752 |
| MERCATO DI CORCIANO | MERCOLEDI | PIAZZA CADUTI | 07:30–14:00 | 43.12865722653829 | 12.28622486563546 |
| MERCATO DI ELLERA | VENERDI | PIAZZA DELLA CROCE ROSSA | 07:30–14:00 | 43.10389696931246 | 12.317285858345878 |

**Attenzione schema:** nel CSV le colonne \`long\` e \`lat\` sono INVERTITE rispetto ai loro nomi: \`long\` contiene latitudine ~43 e \`lat\` contiene longitudine ~12. Il campo \`geopoint\` conferma la coppia \`(43.x,12.x)\`. Non scegliere automaticamente la prima colonna per longitudine. Validare entrambi i numeri e il geopoint; in caso di schema cambiato, non pubblicare coordinate non verificate.

## Contratto per script riutilizzabili

1. Fare un solo download bounded (max 16 KiB), HTTPS esatto, senza redirect.
2. Fare il parse con \`csv.DictReader\` delimitatore punto e virgola e verificare l'intestazione completa.
3. Identificare i singoli mercati mediante denominazione ufficiale; trattare le località Mantignana, San Mariano ed Ellera come frazioni del Comune di Corciano: \`citta=Corciano\` e nome/località nella scheda.
4. Generare solo **date previste** dalla parola esatta del giorno, e solo finché la data ufficiale del dataset non supera la soglia di qualità. Non inventare conferme, eccezioni festive o verifiche umane.
5. Coordinate non verificate sul posto -> \`position_quality=non_verificata\`, mai \`precisa\`; per mismatch numerico lasciare coordinate sconosciute e aprire verifica.
6. Test gold sul CSV reale (fixture sintetica derivata dai quattro valori) e test negativi per schema mutato, duplicati, \`lat\`/\`long\` in posizione diversa, redirect, giornate mancanti e conteggio inatteso.
7. Fare dry-run completo in CI prima di inserire \`corciano\` nella allowlist giornaliera. Salvare report sorgente, collisioni, qualità della build e prova browser negli artefatti; solo allora abilitare su DEV.

Nota di corretta attribuzione: \`aggiornato_il\` deve significare la data del dataset dichiarata nel catalogo nazionale, non la data odierna del controllo né l'aggiornamento della pagina web.

## Primo contratto generico approvato — 13 ottobre 2026 (solo DEV)

- Licenza confermata anche da dati.gov.it: https://www.dati.gov.it/node/view-dataset/dataset?id=62be39fe-adbe-464a-84b1-85bc060b75d2 (CC BY 4.0). URL di attribuzione: pagina Comune sopra.
- CSV integrale verificato via HTTPS: 737 byte, SHA-256 `1c42627045f28ab7d0bd187493339f27b3e2c7afcfd5155bf7f739cf49a83121`. Quattro sedi, header immutato, parità esatta con adapter storico.
- Baseline DEV: 13.784 ID; 2 ID del CSV già in catalogo, altri 2 trattenuti per sovrapposizione con vecchie schede. **Nessuna nuova scheda ammissibile oggi.**
- Certificato a livello di fonte, budget di 2 nuove sedi per ciclo, nessun evento verificato o geocodifica; gli aggiornamenti futuri passano solo da parser comune e controlli automatici.
- Non usare il timestamp pagina del 27 luglio come data di verifica delle quattro sedi: resta la data dataset del 7 gennaio 2026.
- Il vecchio nome tecnico del contratto (`corciano-generic-shadow`) resta stabile per non invalidare checkpoint e audit; il campo `publication_mode` governa l'effettiva autorizzazione.
