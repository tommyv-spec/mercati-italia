# Happings nel ciclo DEV

Il recupero dei campi ora è una fase di `backend/autopilot.py`, immediatamente
prima dell'export. Usa il parser e il motore già presenti. Non crea workflow,
scheduler, servizi o job GitHub aggiuntivi.

## Stato attuale

La fase è **disabilitata per default**. `backend/autopilot_policy.json` non
abilita `happings_enrichment` e il registro diritti esistente non è stato
modificato. Nessuna richiesta Happings viene eseguita in questo stato.

L'attivazione tecnica richiede entrambe le condizioni già previste:

- `happings_enrichment: {"enabled": true}` nella policy;
- registro corrente con `republication_rights_authenticated: true`.

La sola impostazione della policy non supera il gate del registro.

## Comportamento della fase

`backend/happings_autopilot.py` conserva gli ID Happings già presenti anche
quando il recupero è spento. Se attivo, seleziona al massimo due URL dal
catalogo, usando la rotazione del motore esistente. Richiede le pagine con i
controlli di dominio, robots, redirect, dimensione e attesa già implementati.
Scrive soltanto gli indirizzi vuoti provati dal parser, insieme alla fonte.

Il report espone uno stato preciso:

| Stato | Significato |
| --- | --- |
| `disabled` | Policy disabilitata: nessuna rete e nessun campo modificato. |
| `blocked_rights` | Policy attiva, gate del registro non superato. Nessuna rete o modifica. |
| `offline_skipped` | Prova offline senza riuso esplicito delle risposte. |
| `no_eligible_pages` | Nessun URL del formato ammesso con campi recuperabili. |
| `retrieved` | Acquisizione limitata completata; si applicano solo le proposte ammesse. |
| `resumed_checkpoint` | Risposte precedenti rilette e validate, senza richieste. |
| `resume_missing_evidence` | Ripresa senza prove salvate: nessuna nuova richiesta. |
| `unavailable` | Richiesta fallita o batch incompleto. Il catalogo viene conservato. |
| `layout_changed` | Tutte le pagine hanno un formato non più ammesso. Nessuna modifica. |
| `partial_layout_changed` | Le pagine di formato diverso sono isolate; le altre restano valutabili. |

`--resume` richiede lo stesso catalogo di partenza, input della fase, policy,
registro diritti e giorno di riferimento. Verifica hash, URL e contenuto HTML.
Non effettua nuove richieste, neppure se manca un checkpoint. Si può combinare
con `--offline`. Se una seconda richiesta fallisce, conserva comunque l'HTML
della prima nei checkpoint; il batch incompleto non applica indirizzi.
Un registro che non supera più il gate impedisce anche il riuso delle prove.

## Conservazione delle schede e controllo finale

L'export riceve `preserve_ids` con tutti gli ID Happings esistenti. Due schede
che acquisiscono lo stesso indirizzo restano quindi due schede. Non vengono
fuse dal deduplicatore, né scartate dalla normalizzazione.

La verifica successiva all'export controlla l'insieme esatto degli ID Happings e ogni
campo dei loro JSON finali. Le altre fonti conservano i controlli e le regole di
deduplicazione già previsti. Gli unici cambiamenti della fase consentiti sono
`indirizzo` prima vuoto e aggiunta della fonte in `fonti`. La normalizzazione
ricalcola `completezza` e l'ordine delle fonti. Non sono permessi cambiamenti
a date, orari, coordinate, città, stato o verifica di apertura.

La fase continua a dipendere dai normali gate dell'Autopilot: integrità dei
dati, controlli delle fonti, build, sicurezza, test browser e confronto dello
SHA prima di promuovere il candidato DEV. Non pubblica direttamente.

## Prove e report

Nel percorso temporaneo `--output` sono prodotti:

- `sources/happings-pages.json`: HTML limitato, hash, URL richiesto/finale e contesto della ripresa;
- `happings-enrichment.json`: stato e prove per campo;
- `HAPPINGS_ENRICHMENT.md`: riepilogo leggibile;
- `checkpoints/happings_enrichment.json`: contatori della fase;
- `happings-enrichment-static-guard.json`: prova dell'export finale.

Sono inclusi nel percorso di checkpoint già raccolto dal workflow esistente.
Le pagine HTML e le prove complete non vanno aggiunte al repository. Nessuna
configurazione di conservazione artifact o cache GitHub è stata aumentata.

I test in `backend/tests/test_happings_autopilot.py` usano esclusivamente
fixture locali, incluse quelle con un registro simulato abilitato.

## Verifica del 19 ottobre 2026

Base del lavoro: DEV `0aa02086a59489c194bd4b3ab7746f5921b7f9a4`.
Il catalogo letto contiene **13.824 schede**, di cui **9.647 Happings**.
La famiglia di URL provinciali `ad-...` comprende **414 schede**, **236** con
indirizzo vuoto. Dopo i nuovi controlli su URL, Comune, provincia, regione e
giorno, **179** risultano eleggibili per una futura valutazione della fonte.
Eleggibile non significa indirizzo trovato o applicabile senza altre prove.

La prova completa dell'Autopilot sul catalogo reale è stata eseguita con
`--offline --today 2026-10-19`. È terminata con:

- 13.824 schede prima e dopo, nessun ID aggiunto o eliminato;
- 9.647 ID Happings protetti anche con la fase disabilitata;
- stato `disabled`, gate del registro `blocked_rights`;
- zero pagine Happings richieste e zero indirizzi modificati;
- prova finale `release_safe: true` e decisione `approved: true`;
- `has_changes: false`, firma del catalogo invariata:
  `4de17fb44655745c6a941f591c44c9ff682bff511181c4c21ab232934536fd6f`.

In questo intervento non sono state fatte richieste di rete a Happings e non
è stato cambiato alcun indirizzo reale. I test del percorso attivo usano
HTML e registri simulati; non attestano un permesso reale. La policy e il
registro effettivi restano disabilitati per il recupero ricorrente.
