# Verifica dei formati delle fonti esistenti

## Obiettivo e risultato del confronto

L’audit del 20 ottobre 2026 verifica se le fonti già associate al catalogo pubblicano informazioni che i lettori precedenti non estraggono, attribuiscono al mercato sbagliato oppure perdono prima dell’esportazione. Il confronto conferma tutti e tre i problemi. Le attività riguardano i lettori e i raccordi riutilizzabili; questo audit non modifica manualmente le singole schede.

Il riferimento è il catalogo di **13.824 schede, 5.752 URL primari e 87 etichette di fonte** presente nel commit DEV `bd9889fb49c0b0a6bfa5f948cdd6c99659150661`. Gli URL contengono 72 hostname distinti, 71 unificando il prefisso `www`. Le letture originali sono datate 19 ottobre UTC, già 20 ottobre in Italia; ogni campione conserva il proprio timestamp.

Sono state inventariate **109 unità di formato URL**, tutte presenti nel registro con un controllo o un esito esplicito di indisponibilità. Una forma di URL è l’unità di lavoro iniziale: non dimostra che tutte le pagine abbiano lo stesso DOM. I layout realmente osservati, comprese le varianti all’interno dello stesso formato, sono descritti nelle prove.

| Famiglia | Formati URL primari | Schede del catalogo | Prove del confronto |
| --- | ---: | ---: | --- |
| Happings | 3 | 9.647 | [Happings](../reports/automation/source-format-audit-2026-10-20/happings.json) |
| Eventi e Sagre | 16 | 2.197 | [Calendari editoriali](../reports/automation/source-format-audit-2026-10-20/editorial.json) |
| Fonti ufficiali | 8 | 1.333 | [Fonti ufficiali](../reports/automation/source-format-audit-2026-10-20/official.json) |
| Cose di Casa | 1 | 432 | [Calendari editoriali](../reports/automation/source-format-audit-2026-10-20/editorial.json) |
| Citynews | 48 | 92 | [Citynews](../reports/automation/source-format-audit-2026-10-20/citynews.json) |
| Altri editori | 33 | 123 | [Altri editori](../reports/automation/source-format-audit-2026-10-20/other.json) |
| **Totale** | **109** | **13.824** | [Inventario e stato](../reports/automation/source-format-audit.json) |

Le risorse ausiliarie, come CSV, GeoJSON, metadati, PDF allegati e nuovi formati raggiunti dai vecchi URL, sono registrate separatamente. Non aumentano il numero delle schede conteggiate.

Nel registro del primo confronto **102 formati avevano tutti e quattro i confronti del campione completati e sette restavano parziali**. Erano tracciate anche 27 unità ausiliarie, con quattro dei 55 TODO implementati. Il successivo check-in sui dettagli Happings chiude `HAPP-FORMAT-01` e `HAPP-FORMAT-02`; la checklist generata riporta lo stato corrente, compresi i ricontrolli richiesti dai cambiamenti al codice condiviso. Il completamento del confronto non viene confuso con la risoluzione di tutte le perdite.

## Dove seguire check-in e TODO

La [checklist leggibile](../reports/automation/SOURCE_FORMAT_CHECKLIST.md) contiene la tabella di tutti i formati, le prove per ciascun campione, i check-in e i TODO con criterio di chiusura. Il [registro JSON](../backend/data/source-format-review-ledger.json) è la fonte dello stato di avanzamento. Il [report JSON generato](../reports/automation/source-format-audit.json) confronta quel registro con il catalogo e il codice effettivamente presenti.

Per ogni formato sono distinti quattro controlli:

1. **Fonte letta:** contenuto acquisito e analizzato, con URL richiesto, destinazione HTTP osservata se disponibile, eventuale canonical HTML, timestamp, dimensione e SHA-256. Un HTTP 200 privo di analisi del contenuto non chiude il controllo.
2. **Campi letti:** individuazione dei campi del mercato nel loro contesto, comprese assenze, edizioni, stagionalità, più sedi e contraddizioni. Footer, altri eventi e date editoriali restano separati.
3. **Parser confrontato:** confronto con la versione del codice identificata dalle impronte dei file pertinenti. Se manca il produttore storico, il registro dichiara l’assenza: non attribuisce al codice attuale un’importazione passata non riproducibile.
4. **Catalogo confrontato:** confronto delle schede che usano gli URL campione. L’impronta comprende l’intera riga esportata, inclusi Comune, provenienza e stato dei campi.

Una spunta chiude il **controllo del campione**. La correzione individuata ha un TODO separato, che resta aperto fino al superamento del proprio criterio di accettazione. Nessuna spunta certifica da sola tutte le schede di una fonte, la validità di un appuntamento futuro o l’attuale apertura di un mercato.

Il report segnala un nuovo controllo quando compaiono formati o URL nuovi, cambiano i file del parser o i dati delle schede campione, oppure trascorrono 30 giorni dal check-in. Conserva i timestamp originali: rigenerare il report non equivale a rileggere la fonte. Le simulazioni con una data precedente al check-in non possono usare quelle prove come già disponibili.

## Informazioni presenti ma perse dal sistema

### Eventi e Sagre

Il confronto usa 17 HTML salvati, rappresentativi dei 16 prefissi URL presenti nel catalogo. Il lettore precedente cercava anche fuori dal riquadro dell’evento: nel replay attribuiva in nove casi l’indirizzo del footer, `Via Magenta 8`, e non ricavava correttamente il Comune e la provincia del riquadro in nessuno dei 17 campioni.

Il nuovo lettore delimita `schedaEvento` e il relativo contenuto. Sugli stessi HTML ricava correttamente Comune e provincia in 17 casi, elimina le nove contaminazioni del footer e passa da un testo di orario a 13, di cui nove intervalli completi e quattro sole aperture. Il precedente orario isolato riguardava un’attività accessoria. Apertura senza chiusura e intervallo completo conservano precisioni diverse.

Il parser distingue 17 intervalli di edizione dalle date editoriali, riconosce 16 indicazioni di archivio e segnala 12 documenti JSON-LD non validi. Nell’esempio con più mercati a Pescara mantiene quattro combinazioni distinte di sede, giorno e orario. I conflitti visibili restano espliciti. Il replay del vecchio calendario Argenta avrebbe generato sei date future da un’edizione del 2025; il raccordo corretto ne genera zero.

**Il ponte dei nuovi metadati rimane un TODO:** `RawMarket` e `CleanMarket` non conservano ancora integralmente archivio, intervallo, conflitti e data editoriale. Il lettore puro conserva queste prove; il raccordo legacy evita di consegnare al vecchio cleaner una ricorrenza che perderebbe i limiti dell’edizione. Non è stata eseguita un’importazione editoriale completa con rete e geocodifica. La correzione dello scraper non attiva un nuovo importatore nel job quotidiano.

### Firenze e Bologna

Il problema è anche nel salvataggio. Il testo ufficiale Firenze contiene clausole e chiusure oltre i precedenti limiti di 180 caratteri nel lettore e 160 nell’export; un ulteriore controllo del feed imponeva 250 caratteri. Il percorso Bologna attivo usa il contratto generico e scartava gli orari stagionali che non corrispondevano a un singolo intervallo numerico.

Il raccordo degli orari deve mantenere lo stesso testo e la relativa prova dal lettore fino a ricevute, merge ed export. Il limite condiviso è 2.000 caratteri: un testo più lungo provoca un esito esplicito, senza salvare un prefisso che potrebbe escludere le chiusure. Le ore composte mantengono le condizioni pubblicate, senza scegliere arbitrariamente una stagione.

Il replay dopo la correzione recupera **nove orari Bologna prima vuoti**, sulle 39 identità esatte del contratto attivo, e conserva integralmente i quattro testi Firenze. Il testo Firenze precedentemente troncato mantiene tutti i 1.885 caratteri e le 17 date esplicite, comprese le 15 perse nel vecchio export. Gli anni pubblicati restano invariati. Questi risultati provengono dai replay degli originali, senza modifiche manuali alle schede pubblicate.

Le prove dopo la correzione, con le impronte definitive del codice, sono separate dalle misure del vecchio percorso nel [report ufficiale](../reports/automation/source-format-audit-2026-10-20/official.json). Gli aggiornamenti degli orari richiedono corrispondenza esatta con l’identità e la sede già associate alla fonte, conservazione della ricevuta e rispetto delle prove più recenti. Non aggiornano artificialmente l’età della fonte: i problemi dei timestamp Firenze e degli altri metadati restano attività distinte.

### Happings

Le pagine provinciali e i dettagli evento contengono informazioni diverse. Il dettaglio attuale osservato per Lana pubblica indirizzo, orario, dieci date esplicite e un’eccezione per il 24 dicembre. Il nuovo [percorso sistematico dei dettagli](HAPPINGS_DETAIL_EXTRACTION.md) importa questo formato nel ciclo DEV, con discovery dalle sitemap, confronto delle identità e calendario conservato fino all’interfaccia. Il replay di nove pagine reali sul catalogo completo produce due nuove identità distinte e mantiene quattro possibili duplicati in verifica, due conflitti della fonte e un incontro estraneo alla categoria mercato. Tutte le righe preesistenti restano integre. Il vecchio URL comunale può ancora restituire l’elenco provinciale, senza dimostrare da solo il collegamento con il dettaglio giusto.

Per Trieste è emerso un limite nel reperimento della risorsa: esistono righe leggibili sul vecchio URL comunale ma manca una risorsa provinciale già collegata dal percorso corrente. In altri elenchi, come i campioni Avellino e Bari, le sedi precise non sono pubblicate. La correzione deve quindi distinguere informazioni presenti ma non lette, risorse non raggiunte e informazioni assenti nella fonte. I TODO `HAPP-FORMAT-*` mantengono separati dettagli, calendari, collegamenti, sedi, URL e stagionalità.

### Altre fonti già associate

| Famiglia | Riscontro verificato sul campione | Lavoro da completare nel meccanismo |
| --- | --- | --- |
| Cose di Casa | Cinque varianti semantiche; quattro orari precisi presenti ma vuoti nelle schede confrontate. Calendari visibili e JSON-LD possono discordare. | Lettore dedicato, esclusioni estive, sabato che precede la seconda domenica, conflitti e conservazione dell’edizione. |
| Citynews | Su 48 formati, 47 contenuti acquisiti e un errore HTTP. Nelle schede con gli URL campione risultano 11 indirizzi e 14 testi numerici di orario presenti nella pagina ma vuoti nel catalogo. | Separare scheda evento, articolo e indice; leggere campi nel contesto; conservare intervalli ed eccezioni senza riportare edizioni passate nel futuro. |
| Lombardia | Campi `dal/al` in 171 righe; periodi non annuali o ambigui in 14. Per tre identità esatte, il confronto individua 38 previsioni oltre i limiti univoci della fonte. | Trasferire i limiti al motore delle previsioni; conservare denominazione originale e qualificatori. |
| Milano | La tabella PDF completa contiene 93 combinazioni mercato/giorno, contro 87 della vecchia estrazione. | Copertura delle righe, distinzione vendita/sgombero, orario stagionale, note di spostamento e precisione delle geometrie. |
| Roma | Il dataset contiene orari per giorno e date di aggiornamento delle righe; è presente una distribuzione più recente di quella usata. | Selezione della distribuzione, adapter mantenuto, data con ambito corretto e raccordo documenti/sedi. |
| Altri editori | Elenchi dinamici, più mercati nello stesso articolo, vecchie edizioni, dati strutturati in conflitto con il testo e sedi già salvate discordanti. | I TODO `NC-*` definiscono lettura, discovery, precisione temporale, identità, conflitti, geografia e copertura operativa. |

Gli orari numerici non sono tutti intervalli completi: espressioni come “dalle 8 al tramonto” conservano un limite non numerico. Le date di una vecchia edizione restano dati storici; la loro assenza nel calendario futuro non costituisce automaticamente una perdita da correggere.

## Esiti parziali da mantenere visibili

I campioni Assosagre, PadovaToday e i due formati Trentino hanno restituito rispettivamente HTTP 429, 503, 503 e 503. Un URL Emilia-Romagna contiene un hostname ottenuto concatenando un collegamento relativo: il tentativo non viene trasformato in una richiesta verso un indirizzo inventato. Questi cinque formati conservano i controlli della fonte e dei campi aperti.

Ferrarainfo ha restituito HTML, ma il contenuto dinamico completo degli eventi non è ancora risolto. SagreFVG ha una destinazione HTTP `/sagre/` e un canonical HTML `/sagris/`: il registro conserva entrambi e non tratta la transizione come dimostrata. Questi due controlli restano parziali. Anche gli allegati ausiliari indisponibili e il nuovo formato provinciale Happings osservato solo indirettamente restano distinti dalle letture dirette.

## Aggiornamento nel sistema esistente

`publisher_quality_matrix.py` genera il rapporto usando catalogo e registro locali. Il job `publisher-quality-daily.yml` già presente su `main` richiama quel comando sul ramo DEV. Il riepilogo contiene lo stato di ciascun formato, i controlli pendenti, le ragioni di ricontrollo e gli ID dei TODO: la coppia JSON/Markdown già pubblicata dal job conserva così l’avanzamento. Il report completo e la checklist generata entrano anche nell’artifact di output esistente. Il workflow e la sua programmazione non vengono modificati.

Anche Autopilot produce il report dei formati sul candidato e ne include il riepilogo nella valutazione. Questo passaggio è locale: **non aggiunge letture di rete, dipendenze, job o servizi a pagamento**. Segnalare un formato da ricontrollare non significa aver già implementato la sua rilettura automatica. I lettori e i raccordi ancora mancanti rimangono nei TODO.

Per rigenerare inventario e checklist:

```bash
python backend/source_format_audit.py \
  --manifest public/data/v1/manifest.json \
  --ledger backend/data/source-format-review-ledger.json \
  --today 2026-10-20 \
  --output reports/automation/source-format-audit.json \
  --markdown reports/automation/SOURCE_FORMAT_CHECKLIST.md
```

Per aggiornare un controllo, aggiungere il check-in reale, le prove del nuovo campione, l’ambito del layout e le impronte del codice eseguito. Aggiornare la fotografia delle schede solo dopo il nuovo confronto. Un TODO passa a `done` soltanto con una risoluzione documentata e la prova del criterio di accettazione. Non cambiare soltanto timestamp o hash per eliminare un avviso.

I replay successivi usano catture salvate e conservano URL, hash e date delle letture originali. La validazione sul catalogo completo e i test delle correzioni sono documentati nel [rapporto di validazione](../reports/automation/source-format-audit-2026-10-20/validation.json). Le prove di un singolo lettore, l’esito del replay completo e l’avvenuta pubblicazione su DEV sono risultati distinti.
