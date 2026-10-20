# Lettura sistematica dei dettagli Happings

## Cosa cambia

Le pagine `/it/happing/{slug}/` contengono dati che il lettore degli elenchi provinciali non importava. Il nuovo percorso legge il dettaglio dell’evento, trova altre pagine nelle sitemap pubblicate dal sito, confronta l’identità con tutto il catalogo e conserva le informazioni fino alla scheda mostrata all’utente.

Il lavoro nasce dal [mercato coperto Campagna Amica di Pisa](https://www.happings.com/it/happing/mercato-coperto-campagna-amica-di-pisa/). Il codice non contiene indirizzi, orari o calendari assegnati a mano a quel mercato. L’URL indicato dall’utente è un punto di partenza osservato; le altre risorse vengono dai collegamenti e dalle sitemap effettivamente acquisite.

## Prova su dati reali

Il [rapporto di validazione](../reports/automation/happings-detail-validation-2026-10-20.json) conserva URL, timestamp, hash dei byte HTTP, campi letti, conflitti, esito del confronto e nuove schede ottenute nel replay. Il riferimento è il catalogo DEV di 13.824 schede nel commit `e2ee92aded38ccb505528dd74cd6be8a98886999`.

| Campione reale | Informazioni conservate o problema rilevato | Esito sul catalogo completo |
| --- | --- | --- |
| Campagna Amica Pisa | Via del Chiassatello 64/65; 07:30–12:30; dieci date pubblicate fra 24 ottobre e 26 dicembre 2026 | Nuova identità distinta, con prova della fonte |
| Campagna Amica Pescia | Indirizzo, orario e nove appuntamenti espliciti | Nuova identità distinta, con prova della fonte |
| Mercato del venerdì a Lana | Dieci date; l’edizione del 24 dicembre termina alle 13:00 | Possibile identità esistente con sede discordante: confronto sospeso |
| Antiquariato Lucca | Fine settimana espliciti, con ore di inizio e termine del periodo | Possibile identità già presente con indirizzo composto: confronto sospeso |
| Mercato settimanale Castelrotto | Quattro appuntamenti e condizione relativa al maltempo | Possibile identità esistente: confronto sospeso |
| Mercatino regionale piemontese | Periodo che attraversa due mesi e orari qualificati | Possibile identità esistente a Monza: confronto sospeso |
| Natale Parcines | Orari discordanti fra riquadro e testo/dati strutturati; attività accessorie distinte | Conflitto della fonte registrato |
| “Jingle Bells Rock” nel mercatino di Natale | Concerto accessorio e sedi discordanti nella pagina | Non viene importato come un nuovo mercato |
| “Il mercato dei fumetti nel 2026” | Incontro culturale sul settore economico del fumetto | Escluso dalla categoria mercato |

Nel replay dei nove originali sono ottenute **due nuove identità**, con **zero modifiche alle 13.824 righe preesistenti**. L’export contiene 13.826 schede e conserva esattamente il risultato normalizzato. La pubblicazione effettiva del ciclo quotidiano è distinta da questa prova: i file del catalogo pubblico non vengono riscritti dal replay.

Le nove fixture contengono i sottoalberi fattuali necessari ai test. Il relativo [manifest](../backend/tests/fixtures/happings_detail/manifest.json) distingue l’hash della risposta completa da quello della fixture ridotta. Evento, conflitti, avvisi e attribuzione dei campi devono essere uguali nei due replay.

Il replay dell’intero Autopilot con queste nove risposte salvate supera tutti i **17 controlli di pubblicazione**, comprese le verifiche indipendenti delle ammissioni e dell’indice statico. Non effettua nuove richieste HTTP. Il normale aggiornamento delle previsioni del resto del catalogo resta distinto dalle modifiche della fase Happings.

## Meccanismo automatico

### Reperimento delle pagine

Il crawler parte dalle sitemap dichiarate in `robots.txt`, dalle risorse già salvate nel catalogo e dagli URL già osservati. L’inventario iniziale comprende **2.196 URL italiani di dettaglio** e **14 risorse sitemap**: indice e tredici sitemap degli eventi. I 315 URL con parole tipiche di mercati ricevono priorità di lettura, senza essere considerati mercati già verificati.

Il rapporto conserva inoltre dodici URL osservati fuori dalla route supportata: la pagina indice e undici slug con caratteri o codifiche differenti. Non sono conteggiati come dettagli letti o coperti dal parser corrente.

La coda persistente `public/data/v1/happings-discovery.json` registra scoperta, ultimo tentativo, ultima lettura riuscita, impronta dei byte, errore e prossima lettura. Non basta scaricare una pagina per dichiarare corretto il mercato. Il bootstrap conserva gli orari reali delle acquisizioni e lascia i dettagli ancora da leggere.

Il ciclo esistente ha un massimo di **128 richieste per la fase dettagli**, comprese le sitemap, oltre alla lettura di `robots.txt`. Un limite di **420 secondi** impedisce di avviare ulteriori richieste quando il tempo disponibile termina; le risorse rimanenti conservano il proprio stato per il ciclo successivo. La risposta eventualmente già in corso mantiene il suo timeout. Restano tutte le pause richieste dal sito, con almeno tre secondi fra richieste.

Le riletture dovute delle pagine già collegate al catalogo e degli URL con termini tipici di mercato hanno priorità. Quote riservate mantengono la scoperta di pagine nuove e la rilettura degli altri dettagli, evitando che una classe occupi tutta la coda. **Quando le pagine mai lette superano quelle già lette e dovute, la priorità passa alla prima scansione**: sei slot su nove servono URL nuovi (due in ordine di anzianità), due rileggono pagine pertinenti e uno gli altri dettagli. Quando la prima scansione recupera terreno, torna la priorità alle riletture (sei slot pertinenti, due nuovi, uno di altri dettagli). La quota è una regola di selezione, non una nuova richiesta o una dichiarazione di completezza.

Le letture riuscite diventano nuovamente dovute dopo sette giorni: questa è la data di eleggibilità, non una promessa di freschezza settimanale indipendente da errori e capacità. Gli errori hanno un’attesa crescente fino a sette giorni. I report conservano durata effettiva e motivo di arresto del lotto.

Nel controllo del 20 ottobre 2026 la coda DEV pubblicata aveva **2.196 dettagli**, di cui **216 già letti** e **1.980 mai letti**, oltre a 14 sitemap lette. Un test di sola selezione sulla coda congelata, per il 28 ottobre e senza simulare letture intermedie, passa da 28 a 84 primi dettagli su 128 richieste massime, mantenendo 42 riletture e due sitemap. Non è un'acquisizione reale né una previsione del numero di mercati ricavabili. Vedi [il rapporto di schedulazione](../reports/automation/happings-catchup-scheduling-2026-10-20.json).

La fase provinciale già esistente mantiene il suo limite di sedici pagine e il proprio controllo robots. Non vengono aggiunti servizi, dipendenze, workflow o nuove programmazioni. Il job Autopilot quotidiano esistente usa la configurazione DEV.

### Lettura e attribuzione

Il lettore confronta il contenuto visibile dell’evento con l’oggetto strutturato `Event` che corrisponde alla pagina. Conserva nome, Comune, provincia/regione riconciliate con ISTAT, sede, orari, date esplicite, organizzatore, contatti, condizioni e note pertinenti. I dati strutturati non prevalgono automaticamente sul testo quando i due discordano.

Footer dell’editore, eventi correlati, concerti e attività accessorie non possono fornire l’indirizzo o gli orari del mercato principale. Un errore di layout o un contenuto non rappresentabile produce un esito per quella pagina; gli altri dettagli del lotto possono essere elaborati.

La data di pubblicazione della pagina, la sua eventuale modifica e la lettura del crawler rimangono campi distinti. Nessuna di queste date diventa una conferma personale dell’apertura. Le coordinate pubblicate dalla fonte vengono conservate come informazione della fonte, senza creare automaticamente una posizione precisa per la navigazione.

### Identità e aggiornamento

Il sistema confronta ogni dettaglio con l’intero catalogo. Un URL canonico esatto o una combinazione non ambigua di nome, Comune, sede e giorno possono identificare una scheda. Somiglianze più deboli, come una strada compresa in un indirizzo con più sedi, servono a sospendere un possibile duplicato; non autorizzano un’unione.

Una nuova scheda richiede un mercato riconoscibile, geografia esatta, sede specifica, date future effettivamente pubblicate e assenza di una possibile identità già presente. Gli identificativi sono stabili rispetto all’URL canonico. I valori preesistenti non vuoti sono protetti; un successivo aggiornamento di un campo gestito dal nuovo lettore deve mantenere la prova della fonte e rispettare la precedenza temporale.

Ogni assegnazione viene ricostruita dai fatti estratti durante i controlli. Modificare una ricevuta o ricalcolare l’hash del risultato non basta a rendere ammissibile un valore diverso. I controlli del catalogo mantengono separata l’ammissione Happings dalla verifica storica delle identità delle altre fonti.

### Calendario e visualizzazione

`calendario_fonte` conserva gli appuntamenti, gli orari della singola data, gli eventuali annullamenti e i limiti dei periodi. `dettaglio_fonte` conserva gli altri fatti con la stessa provenienza e identità. Entrambi attraversano normalizzazione, export, caricamento dei dettagli e interfaccia.

La scheda mostra **“Date riportate dalla fonte”**. A Lana, il 24 dicembre mantiene la chiusura diversa. Un intervallo dal sabato alla domenica non diventa un’apertura continuativa notturna e non autorizza ad assegnare lo stesso orario a ogni giorno. Condizioni meteo e altre eccezioni restano visibili. Gli annullamenti già documentati nel catalogo prevalgono sulle normali indicazioni della pagina.

Quando finiscono le date pubblicate, il motore non estende quel calendario al mese o all’anno successivo. Occorre una nuova lettura con nuove date esplicite. Una pagina non disponibile non rinnova la data della prova e non cancella un mercato dal catalogo.

### Ripresa e pubblicazione

Il checkpoint temporaneo contiene HTML compresso, provenienza e avanzamento. Le pagine riuscite devono corrispondere esattamente agli esiti della coda per URL, ordine, dimensione, hash e timestamp. Riprendere una lavorazione usa la data originale della lettura e non effettua richieste nascoste.

Anche una lavorazione che scopre soltanto nuovi URL deve conservare la coda nel candidato DEV. Il test completo verifica questo caso: il contenuto del catalogo resta identico, ma l’avanzamento non viene perso fra due esecuzioni.

Il controllo nazionale continua a contare tutte le possibili sovrapposizioni. Distingue ora quelle rese visibili dal recupero documentato di indirizzi da una crescita non spiegata dei possibili duplicati. Sono necessarie le stesse identità preesistenti, i valori originali e le prove della fonte; nuove schede o variazioni non sostenute da prove restano soggette alla soglia precedente. Il replay dell’esecuzione quotidiana `39400676914` conserva le 859 sovrapposizioni grezze, attribuisce alle prove i 94 casi emersi dopo l’arricchimento e rileva crescita non spiegata pari a zero.

## Check-in e attività residue

- [x] Lettore del dettaglio e isolamento dei campi del singolo evento.
- [x] Discovery dalle sitemap reali, coda persistente e ripresa verificabile.
- [x] Confronto con tutte le identità esistenti e ammissione di sedi distinte.
- [x] Calendari, eccezioni e intervalli conservati fino all’interfaccia.
- [x] Replay dei nove originali e confronto con le fixture.
- [x] `HAPP-FORMAT-01` e `HAPP-FORMAT-02` chiusi con prove nel registro.
- [ ] Risolvere con ulteriori prove le identità ambigue; il testo di una sede non autorizza da solo una correzione.
- [ ] Completare i TODO provinciali, le vecchie route, la stagionalità e i metadati degli altri formati Happings.
- [ ] Proseguire la rilettura delle altre famiglie di fonti secondo la checklist generale.

La [checklist dei formati](../reports/automation/SOURCE_FORMAT_CHECKLIST.md) e il [registro dei check-in](../backend/data/source-format-review-ledger.json) conservano l’avanzamento. Gli avvisi di ricontrollo causati dai cambiamenti ai raccordi condivisi restano visibili: il nuovo lettore Happings non certifica automaticamente tutte le altre fonti.
