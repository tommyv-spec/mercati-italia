# Lettore mantenuto Roma d881

## Risultato osservato

Le risposte HTTP pubbliche originali del Comune, lette il 20 ottobre 2026,
contengono 70 mercati. Il CSV CP1252 ha sei coppie di orari distinte per
giorno, note sugli orari, note sul mercato, civici e indicazioni aggiuntive.
Le date `AGGIORNATO` sono 31 dicembre 2021 per 8 righe e 30 aprile 2023
per 62. La lettura del 2026 non rende attuali queste informazioni.

Il replay dei byte originali sull'intero catalogo di 13.824 schede collega
68 schede con nome e strada univoci. Le due identità contenenti caratteri
corrotti rimangono sospese. Tutte le 70 schede esistenti rimangono presenti;
nessun ID, indirizzo, punto geografico, ricorrenza o data viene creato o
corretto dal lettore. I 68 riscontri degli orari sono classificati
`riscontro_da_aggiornare` dal modello di evidenza esistente.

Questo è un replay con acquisizioni reali già salvate, non l'esecuzione
live del nuovo lettore. Il riepilogo riproducibile è in `roma-d881-replay.json`.
Le risposte originali, gli SHA256, le date di lettura e l'attribuzione a
Roma Capitale sono nelle fixture `backend/tests/fixtures/roma-d881/`.

## Meccanismo

1. Legge l'endpoint CKAN `package_show` del dataset pubblico d881.
2. Sceglie l'unica distribuzione CSV attiva con data dichiarata più recente
   fra `created` e `last_modified`; l'ordine della lista non conta.
3. Scarica soltanto l'URL realmente osservato nei metadati, dentro lo
   stesso dataset e dominio. Non ricostruisce il nome del file dal titolo.
4. Esclude le righe vuote e conserva separatamente la nota del Municipio 6,
   che non è una scheda mercato né una cancellazione attuale.
5. Abbina solo schede già attribuite all'URL esatto del dataset, a Roma/RM/Lazio,
   con nome e strada normalizzati ma univoci. Il Municipio, quando presente,
   deve concordare. Nessun completamento approssimativo di testo danneggiato.
6. Assegna il testo completo dei sei giorni, le condizioni della stessa riga
   e la sua data effettiva. La domenica rimane non dichiarata.
7. Conserva i byte originali nello snapshot: il verificatore finale ricostruisce
   il parser, il confronto e ogni campo modificato, oltre a controllare gli hash.

Una distribuzione successiva viene scoperta dalla stessa lettura dei metadati.
Una riga nuova non crea un mercato: rimane fra i record sorgente non abbinati.
Solo gli orari assegnati da questo gestore possono seguire una versione
successiva della medesima chiave nome+sede+Municipio. Occorrono una lettura
successiva, contenuto diverso, data di riga non regressiva e assenza di prove
concorrenti o modifiche manuali. Un valore preesistente coincidente riceve
evidenza senza acquisire automaticamente la proprietà del gestore.

## Limiti e integrazione

| Controllo | Limite |
| --- | --- |
| Richieste per acquisizione | 2, senza retry o redirect |
| Timeout per richiesta | 20 secondi |
| Metadati | 300.000 byte, massimo 256 risorse |
| CSV | 512.000 byte |
| Righe lette | massimo 5.000 |
| Righe mercato | massimo 300 |
| Età massima della lettura riutilizzata | 45 giorni |
| Modifiche catalogo | `orario_testo`, `riscontri_campi` |

Le destinazioni DNS devono essere pubbliche. URL, status, MIME e dimensione
vengono verificati; il MIME osservato `text/x-comma-separated-values` è
accettato. I metadati e il CSV devono appartenere alla stessa acquisizione.
Errori, distribuzioni ambigue, layout nuovi e identità in conflitto restano
espliciti e non aggiornano prove di lettura di una scheda.

Le date della fonte primaria del catalogo rimangono identiche. L'età degli
orari è nella ricevuta di campo e nel testo datato: non deve autorizzare
ricorrenze che questo lettore non ha verificato. Il frontend esistente
mostra separatamente data dei contenuti e data di lettura.

API:

```python
snapshot = source_roma_d881.acquire(today=today)
rows, report = roma_d881_enrichment.preview(base, snapshot, today=today, apply=True)
roma_d881_enrichment.verify_changes(base, rows, report, today=today)
roma_d881_enrichment.verify_exported(base, normalized_rows, report, today=today)
```

Per un replay si usa `make_snapshot` con i due corpi originali e i rispettivi
timestamp effettivi. `acquire` accetta `fetch(url) -> bytes` e `clock()` per
prove controllate. `load_policy()` valida il contratto separato
`backend/data/roma-d881-policy.json`.

Nella pipeline la fase Roma segue forecast, eccezioni e correzioni geografiche,
ed è verificata prima della fase Happings. La successiva verifica Happings
deve conservare e controllare tutte le modifiche ulteriori fino all'export.

## Verifica

- 33 test semantici Roma superati, inclusi acquisizione limitata, scelta di
  nuove distribuzioni, CP1252, righe ambigue, assenza di calendari inventati,
  versione successiva degli orari, corruzione delle prove e verifica export.
- 14 test del modello condiviso `field_evidence` superati.
- Una regressione chiama il motore reale `recurrence_refresh`: una nuova
  prova di soli orari del 2026 non rinnova una vecchia ricorrenza.
- Replay completo: 13.824 schede conservate, 70 schede Roma verificate in
  export, 68 testi completi storici, 2 identità sospese, zero nuove date.
