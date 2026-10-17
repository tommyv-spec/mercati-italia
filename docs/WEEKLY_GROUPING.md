# Mercati settimanali — raggruppamento città → sedi → giorni

Aggiornato 11 ottobre 2026; branch `improve/data-quality-security-performance-2026-10-11`.
Nessuna mutazione o dedup del dataset Firestore: la trasformazione è **solo UI**.

## Regola

- Mostrare una sola card per città/regione SOLO per titoli generici riconoscibili esattamente come `Mercato settimanale di/a [città]`.
- Non raggruppare gli altri mercati con nome proprio, quartiere o tipologia specifica (San Lorenzo, antiquariato, ecc.).
- Applicare PRIMA i filtri città, regione, categoria, data, giorno della settimana e posizione; aggregare DOPO i record risultanti.
- La città non è una sede: caricare gli indirizzi dalla shard regionale **solo quando si espande** il gruppo. Non aggiungere indirizzi all'indice nazionale compatto.
- Una sede si identifica tramite indirizzo riportato sufficientemente specifico; stesso indirizzo e coordinate ufficiali non incompatibili → stessa sede con giornate distinte. Indirizzi distinti → sedi distinte.
- Se manca un indirizzo affidabile (`centro`, vuoto, `ce...`), il record non viene assorbito da alcuna sede nota. Compare soltanto nella sezione secondaria «appuntamenti senza sede identificata».
- I record non verificati restano «previsti», non «confermati». Gli originali con i singoli slug e URL delle fonti sono sempre raggiungibili.
- Filtro `Sab`: visualizza l'occorrenza successiva del sabato e, se è stata selezionata una città, apre automaticamente il gruppo relativo. In una ricerca nazionale non si espandono gruppi in massa, per risparmiare banda.

## Caso Firenze (snapshot 2026-10-11)

Fonte principale `happings.com`: 7 record generici, 6 giornate distinte. Quattro sedi riportate:
- Largo Monzani — lunedì, mercoledì, giovedì.
- Cascina Rossa (piante e fiori) — martedì.
- Cintola — venerdì.
- Piazza I Maggio — sabato.

Settimo record: `Mercato settimanale a Firenze`, lunedì **senza indirizzo**; nel gruppo accessibile separatamente, non automaticamente unito a Largo Monzani.

Le sedi e le date sono soltanto informazioni **riportate dalle fonti originali**, non confermate dall'amministrazione nel 2026.

## Codice

- `src/lib/marketGrouping.js`: `isGenericCityWeeklyMarket`, `displayEntries`, `groupVenues`, `shouldAutoExpandWeeklyGroup`, parsing weekday, indirizzi vaghi.
- `src/components/WeeklyCityGroup.jsx` / `.css`: card inclusiva di aria-expanded, sedi e date, eventuale gruppo incerto, fetch lazy.
- `src/App.jsx`: filtro Lun–Dom, aggregazione solo lista, rendering, paginazione, keep raw map records.
- `tests/marketGrouping.test.mjs`: test della logica senza dipendenze.
- `tests/ui-smoke.mjs`: test Playwright del flusso Firenze e filtro Sabato, più la navigazione normale.

## Distribuzione test

- Branch sorgente: https://github.com/tommyv-spec/mercati-italia/tree/improve/data-quality-security-performance-2026-10-11
- PR di review: https://github.com/tommyv-spec/mercati-italia/pull/1
- Anteprima statica separata: https://raw.githack.com/tommyv-spec/mercati-italia/dev-static-preview/index.html
- Il provider rawgit.hack mostra un avviso di sicurezza una sola volta al primo accesso (non inserire password/dati personali nella preview) e ha limiti per traffico elevato. Non è hosting di produzione; il tunnel DEV precedente non è stato sovrascritto.
- Build/publish automated: `.github/workflows/publish-dev-static.yml` e verifica browser `.github/workflows/check-public-preview.yml`.

## QA residuo

- Le fonti ufficiali devono essere verificate sulle sedi/ore: qui stiamo evitando duplicazioni UI, non confermando informazioni commerciali.
- Evitare che filtrare per un giorno a livello nazionale provochi chiamate per tutti i dettagli regionali: auto-espansione solo con città esplicita.
- Controllare UI su Android/iOS fisici, contrasto e screen readers.
