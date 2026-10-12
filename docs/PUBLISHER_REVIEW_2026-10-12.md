# Revisione fonti 12 ottobre 2026 — stagionalità e sicurezza geografica

Questa revisione corregge **solo cinque ID già presenti**. Non conferma alcuna
apertura, non sposta punti sulla mappa, non sostituisce la fonte principale e
non elimina alcuna scheda. Tutti i cambiamenti sono eseguiti ogni giorno
dall'Autopilot **dopo** il normale calcolo delle date e **prima** dell'export
statico, così una data sospesa non può riapparire il giorno seguente.

## Prove documentate

- **Todi, "CreativaMente" —** Cose di Casa, pagina aggiornata 20/08/2026,
  https://www.cosedicasa.com/mercatini/todi-giardini-oberdan:
  terza domenica, soltanto marzo–ottobre, sospensione novembre–febbraio,
  ore 9 fino al tramonto. Il Comune cita edizioni a luglio e agosto 2026
  (https://comune.todi.pg.it/it/news/2017921;
  https://www.comune.todi.pg.it/it/news/118527/eventi-nel-mese-di-agosto-2026-a-todi).
  Le date del 15/11/2026, 20/12/2026 e 17/01/2027 **non sono
  più proiettate**. L'eventuale 11 novembre straordinario non viene
  inserito automaticamente, perché non è una conferma dell'edizione 2026.
  Il punto ereditato (43.11, 12.39) è distante dalla città identificata
  (GeoNames Todi 42.77881, 12.41202) e rimane conservato solo per audit.
- **Centro storico di Collalto / Cessalto —** Happings
  https://www.happings.com/it/mercati-settimanali-a-treviso-e-provincia/
  li elenca distintamente: Collalto mercoledì e Cessalto venerdì.
  Collalto è una frazione del Comune di Susegana: documento urbanistico
  del Comune https://gestioneterritorio.comune.susegana.tv.it/wp-content/uploads/2021/05/PI_Var4_elab_1b.pdf.
  Due ID di Collalto sono riconciliati con Susegana, senza unirli
  e senza riattivare il calendario misto di venerdì.
  Gli indirizzi e i punti GPS ereditati non diventano indirizzi confermati.
- **Due schede da elenco TrevisoToday —** etichette città "NA",
  coordinate (44.405991, 8.946072) e (40.794443, 14.463539).
  Entrambe sono fuori dall'estensione ufficiale del Veneto, anche con
  una tolleranza ampia:
  https://www.dati.gov.it/node/view-dataset/dataset?id=6408768c-62ff-43b7-99c3-cc3f362cf5a1.
  Non si attribuisce un Comune dal nome dell'evento o da coordinate
  incompatibili; le schede rimangono consultabili con la fonte originaria,
  senza pin e senza navigazione.

## Contratto del codice

- Evidenza e campi originali, con tutti e cinque gli ID:
  `backend/data/publisher-review-2026-10-12.json`.
- Applicazione conservativa, con identificazione ISTAT e
  confronto preciso con source URL + vecchio nome, Comune e coordinate:
  `backend/publisher_exception_review.py`.
- Fingerprint delle prove e attivazione vincolante:
  `backend/autopilot_policy.json`.
- Uscite della pipeline:
  `publisher-exception-review.json`, `publisher-exception-diff-guard.json`,
  `publisher-exception-static-safety.json`,
  `intermediate/reviewed-publishers.json` e checkpoint `reviewed_publishers`.
- Copia originale delle coordinate in `coordinate_originali`; i
  campi `lat` e `lng` non vengono sostituiti con un centro città.
- Calcolo stagionale ripetuto **dopo ogni nuova proiezione**; date
  sempre `prevista`, mai `confermata`. Se la finestra futura
  non contiene edizioni in stagione, la scheda resta senza date previste.
- Blocco per qualunque ID mancante, fonte originale cambiata,
  sorgente precedente non verificata, coordinate inattese, ISTAT differente,
  maggiore conferma, falsa riattivazione stagionale o scarto
  tra indice compatto mobile e dettagli regionali.

## Verifica

```sh
python -m unittest discover -s backend/tests -q
python backend/autopilot.py --offline --output /tmp/publisher-dev-audit --today 2026-10-12
node --test tests/*.test.mjs
```

Rieseguire l'Autopilot usando il manifest candidato come `--manifest`;
`has_changes` deve risultare `false`. In GitHub CI la build frontend,
la prova mobile e la firma del dataset precedono **qualsiasi** rilascio DEV.
La produzione non viene aggiornata. Non forzare un rilascio se un guard
fallisce.

Nota: l'ID, il nome, l'eventuale sede e il calendario sono fatti distinti.
Una località risolta non significa che ogni singolo appuntamento si svolgerà.
