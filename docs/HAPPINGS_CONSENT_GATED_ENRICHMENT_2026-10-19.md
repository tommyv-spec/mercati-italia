# Happings: recupero automatico delle informazioni (19 ottobre 2026)

> **Nota storica — stato operativo superato il 19 ottobre 2026.**
> Questo documento conserva il test e le decisioni precedenti all'istruzione
> esplicita dell'utente di attivare il recupero Happings. La procedura corrente
> è descritta in [Happings nel ciclo DEV](HAPPINGS_AUTOPILOT_PHASE.md):
> autorizzazione operativa del progetto, 16 pagine per ciclo, rotazione
> permanente, riscontri dei campi e aggiornamento delle sole sedi gestite
> dal motore. I conteggi del test qui sotto restano storici. Le osservazioni
> sull'autenticazione dei documenti restano separate dall'attivazione del
> recupero e non costituiscono una nuova richiesta di conferma all'utente.

## Autorizzazioni ricevute e autenticità

Le condizioni pubbliche di Happings, versione del 5 ottobre 2026,
identificano **Girolamo srls** come operatore. L'ultimo PDF caricato
dal beneficiario, HAP-LIC-2026-01, dichiara una licenza per scraping,
elaborazione e ripubblicazione dal 19 ottobre 2026, con limite di
frequenza ragionevole e revoca con preavviso scritto di 30 giorni.

Gli altri due PDF includono AUT-SCRAP-2026 e HAP-AUT-2026-091.
Nessuno dei tre contiene una firma digitale rilevabile con pdfsig;
sull'ultimo documento sono vuoti gli spazi per le firme. Inoltre il
documento HAP-AUT-2026-091 indica un concedente «Happings S.r.l.»,
mentre la società indicata nelle condizioni ufficiali è Girolamo srls.

I documenti **non sono caricati nel repository**. Abbiamo registrato
soltanto le impronte SHA256 e lo stato, nel file
backend/data/happings-rights-review.json. Per abilitare il crawling
ricorrente e il riuso automatico dei campi serve una conferma
autenticabile rilasciata da Girolamo srls o documento firmato.

## Struttura studiata una volta per editore

Le pagine provinciali Happings contengono:
- div.happings-seo-content;
- h3 dedicati ai giorni della settimana;
- ul/li con Comune, indirizzo o piazza, parte della giornata;
- possibili vecchie URL .html che reindirizzano alla pagina
  canonica -e-provincia/.

La dicitura «la mattina» NON diventa un orario numerico.
Il timestamp di aggiornamento della pagina NON significa
che un mercato sia stato individualmente verificato aperto.

## Connettore implementato

Il modulo backend/happings_source_enrichment.py riusa
happings_weekly_layout.py e garantisce:

1. dominio HTTPS e provincia esatti, senza redirect arbitrari;
2. robots.txt letto prima delle richieste;
3. massimo due pagine per esecuzione, 2,6 MB ciascuna, timeout
   18 secondi e pausa minima di tre secondi;
4. confronto su URL originale, Comune, provincia, giorno e tipologia
   di mercato settimanale; una sola sede ammessa per Comune/giorno;
5. rifiuto delle sedi ambigue, delle informazioni vaghe e delle
   vie che confliggono con le vecchie schede;
6. quando autorizzato, aggiunta SOLTANTO degli indirizzi prima
   vuoti, con fonte editoriale attribuita; nessuna modifica a
   date, verifiche, GPS, identità o fonte principale;
7. controllo dei diff campo-per-campo e identità mantenute.

Il download automatico (--live) e l'applicazione (--apply) rimangono
disabilitati dal registro diritti finché manca conferma autentica
del consenso. Il parser offline, le prove QA e i test funzionano.

## Esperimento su due pagine reali

19 ottobre 2026: Venezia e Modena lette una volta, consultando
prima robots.txt che permetteva le richieste.

- 179 righe elencate dalle due pagine;
- 15 candidati indirizzo, su schede già conservate;
- 8 conflitti con vie registrate in precedenza;
- 22 schede per cui mancava una riga unica città/giorno;
- ZERO schede modificate.

Esempi dei campi recuperabili dalla fonte corrente:
Spinea → Villaggio dei Fiori;
Marcon → Via della cultura / P.tta del Donatore;
Fanano → Piazza Rinaldi; Modena → Parco Novi Sad.

Sono informazioni puntuali tratte dall'elenco, ma NON prove
che l'edizione odierna si svolga sicuramente.

## Esempio d'uso senza richieste remote

    python backend/happings_source_enrichment.py \
      --manifest public/data/v1/manifest.json \
      --input-html /tmp/venezia-autorizzata.html \
      --source-url https://www.happings.com/it/mercati-settimanali-a-venezia.html \
      --out /tmp/happings-audit.json \
      --summary /tmp/happings-summary.json

## Prossime strutture

Happings pubblica anche pagine di dettaglio con date e orari
numerici, che necessitano di un parser differente e verifiche
di aggiornamento, stagionalità e ricorrenza. Le informazioni
provenienti da terzi non devono diventare automaticamente
«apertura confermata», soprattutto in presenza di anni storici.

La stessa tecnica di studio del formato (una volta) + controlli
giornalieri per tutte le schede vale per le altre fonti solo
quando i rispettivi diritti e campi siano verificati.
