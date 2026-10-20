# Copertura dei campi Happings

La copertura distingue ciò che è scritto nella pagina acquisita, ciò che il
parser conserva e ciò che il motore può collegare o applicare al catalogo. Non
attesta l'apertura di un mercato e non modifica dati, identità o autorizzazioni.

## Dove compare

Il report `field_coverage` viene prodotto automaticamente dai due motori
`happings_source_enrichment.preview` e `happings_detail_enrichment.preview`.
Rimane quindi dentro i rispettivi rapporti di prova salvati in
`happings-enrichment.json` dal ciclo esistente. Compare anche nel confronto
offline `happings_weekly_layout.compare_saved_markets` e nella sintesi del
motore provinciale. Non aggiunge richieste HTTP, code o fasi di pipeline.

L'inventario `source_format_audit` conserva i precedenti conteggi
`empty_fields`, ma li qualifica esplicitamente con
`empty_fields_basis = catalog_storage_only_not_source_absence`. Un campo vuoto
nel catalogo non dimostra che manchi nella fonte.

## Denominatori

| Contatore | Unità |
| --- | --- |
| `pages_supplied` | Pagine già acquisite e consegnate al lettore nel ciclo |
| `pages_unassessed` | Pagine per cui il blocco previsto non è riconoscibile; non sono prove di assenza |
| `source_units` | Righe fisiche del listato provinciale oppure singoli eventi di dettaglio |
| `catalog_page_pairs_considered` | Coppie pagina/scheda effettivamente presenti nel catalogo valutato |
| `catalog_page_pairs_linked` | Coppie con collegamento prodotto dal motore esistente |
| `new_venue_candidates_not_catalog_records` | Candidati di dettaglio non inseriti; esclusi dal denominatore delle schede |
| `catalog_values_applied` | Valori effettivamente cambiati e sostenuti dalla relativa ricevuta |
| `catalog_values_supported` | Valori già uguali, nuovamente riscontrati dalla fonte |

Ogni campo — `indirizzo`, `orario_testo`, `ricorrenza_testo`, `date` — ha tre
partizioni che sommano separatamente a `source_units`: `source_presence`,
`reader`, `disposition`. I conteggi di applicazione al catalogo rimangono
distinti. Una riga fonte collegata a tre schede duplicate vale una riga fonte
e può sostenere tre valori del catalogo.

## Significato degli esiti

| Esito | Significato |
| --- | --- |
| `source_absent` | Il campo non compare nei blocchi riconosciuti esaminati |
| `source_qualitative` | La fonte fornisce un'indicazione vaga o qualitativa: per esempio `centro` oppure `la mattina` |
| `source_unclassified` | Il testo relativo al campo esiste, ma il controllo non può affermarne la precisione |
| `source_unassessed` | Il contenuto non ha una struttura riconoscibile per quel controllo |
| `source_present_parser_missing` | Il probe trova un valore preciso nel blocco fonte, ma il parser non lo conserva |
| `source_present_parser_partial` | Il parser conserva soltanto parte dei fatti espliciti individuati |
| `source_present_parser_held_conflict` | Il parser ha sospeso una rappresentazione completa per un conflitto dichiarato |
| `source_present_parsed_identity_unresolved` | Il valore è letto, ma manca un collegamento utilizzabile a una scheda |
| `source_present_parsed_held` | Il valore è letto ma un conflitto, un limite o un criterio di ammissione ne sospende l'uso |
| `source_present_parsed_available` | Il motore ha prodotto una proposta non applicata |
| `source_present_parsed_retained_as_detail` | Il fatto fonte è conservato nel dettaglio, senza sovrascrivere il campo principale |
| `source_present_parsed_supported` | Il campo già salvato è riscontrato dalla stessa prova |
| `source_present_parsed_applied` | Almeno un valore collegato è stato effettivamente cambiato |

Le ragioni specifiche rimangono negli esiti e nei contatori del motore; i campioni
limitati del nuovo report riportano anche `hold_reasons`. La diagnosi non viene
usata per autorizzare un cambiamento o superare una guardia.

## Fonte e parser vengono confrontati separatamente

Il probe legge l'HTML già acquisito, senza ricavare la presenza fonte dal valore
nel catalogo o dalla presenza di un valore nel risultato del parser. Nei listati
esamina le righe di `.happings-seo-content`; nei dettagli esamina i blocchi
dell'evento, il riquadro informativo e gli Event JSON-LD legati a URL osservato e
titolo. Esclude footer, navigazione, schede correlate e contatti del sito.

`centro` produce zero sedi precise recuperabili. `La mattina` rimane un'indicazione
qualitativa. Gli orari precisi scritti in un listato ma non estratti dal lettore
provinciale risultano una lacuna del lettore. La pagina reale di Pisa, oggi
supportata dal lettore dei dettagli, risulta invece letta e applicabile alla
corretta identità; una regressione che perde i suoi orari viene rilevata.

Gli orari di una singola data e i confini temporali di un'edizione rimangono
distinti dagli orari generali. `parsed_hours_scope` e `parsed_calendar_scope`
preservano questa distinzione nel report: per Lucca gli orari sono
`interval_boundaries`. Il conflitto reale sugli orari di Parcines resta un
conflitto, non un dato applicato né una falsa assenza fonte.

## Prova riproducibile e limiti

Eseguire dalla radice del repository:

```bash
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend:backend/tests python -m unittest test_happings_field_coverage
```

I test includono i frammenti reali già registrati di Pisa, Lucca, Parcines e le
52 righe di Trieste, oltre ai casi sintetici avversi. I manifest delle fixture
distinguono l'hash del documento HTTP completo da quello del frammento di test.

Il report `reports/automation/happings-field-coverage-validation-20261020.json`
documenta inoltre il replay delle 13 pagine provinciali e dei nove dettagli HTTP
già acquisiti, contro il catalogo pubblicato di 13.856 schede. Confronta il
risultato con il commit precedente alla diagnostica e registra l'uguaglianza
esatta degli output dei due motori. Non è una nuova acquisizione né una nuova
pubblicazione del catalogo.

L'assenza riguarda i blocchi esaminati, non ogni pagina del sito. Pagine non lette,
errori HTTP e strutture non riconosciute non possono diventare prove di campo
assente. La precisione di un dato pubblicato e la sua corretta estrazione non
dimostrano, da sole, l'effettivo svolgimento di un'edizione futura.
