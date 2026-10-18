# Audit da zero delle sorgenti: campi effettivamente disponibili e perdite

Data di analisi: **18 ottobre 2026**. Baseline DEV: **13.824 schede**,
87 etichette di origine. Questo documento distingue la presenza nella
pagina originale dal campo effettivamente conservato nel catalogo.

## Risultato: buona parte delle lacune nasce PRIMA del catalogo statico

Nel repository il flusso `backend/source_firestore_public.py` è una
**migrazione una tantum da Firestore**; lo script storico
`backend/pipeline.py` richiama solo `scrape_eventiesagre()` e
ha il connettore Cose di Casa commentato. Non esiste al momento un
connettore giornaliero completo per Happings o Cose di Casa.
L'Autopilot odierno aggiorna i dataset **ufficiali approvati**
e conserva le vecchie schede editoriali. L'esportatore statico
può conservare `orario_testo`, `indirizzo`, `date`,
`ricorrenza_testo` e `descrizione` quando li riceve, ma
non può ripristinare informazioni mai arrivate allo snapshot.

Non possiamo dimostrare se OGNI campo mancante sia stato perso
nella primissima estrazione o in Firestore senza conservare
il payload originale: per questo il nuovo audit parla di
**differenze fonte vs catalogo**, non attribuisce cause inventate.

## 1. Happings — 9.647 schede, 9.483 orari mancanti

Esempio originale:
https://www.happings.com/it/mercati-settimanali-a-venezia-e-provincia/

HTML esaminato:
- contenitore `div.happings-seo-content`;
- `h3`: gruppi **per giorno** (es. "Mercati del mercoledì");
- `ul > li`: *Comune* + *via/piazza/frazione* + fascia ("la mattina");
- metadati WordPress `article:published_time` e
  `article:modified_time`; sono metadati dell'articolo,
  NON conferme di apertura di ciascun mercato.

Dati **presenti**: località, giorno, molte sedi stradali/frazioni
e fascia generica. Dati **non dimostrati** dall'indice:
orario preciso HH:MM per singola sede, conferma di una
edizione nel 2026, eccezioni festive e GPS d'ingresso.
La versione attuale fa redirect dalle vecchie URL
`...mercati-settimanali-a-venezia.html` al nuovo
`...mercati-settimanali-a-venezia-e-provincia/`.

Confronto concreto **Spinea**: mercoledì la pagina
indica *Villaggio dei Fiori*. Abbiamo tre schede già salvate
con stessa origine, città e giorno:
due con `indirizzo=""` e una con
`indirizzo="Villaggio dei Fiori"`. Sono informazioni
**già interne al nostro catalogo**: possono generare una
proposta con i due ID ma non confermare automaticamente
che non esista un'altra sede omonima.

ATTENZIONE: https://www.happings.com/it/termini-e-condizioni/
paragrafo 3, punto 10, vieta l'uso di robot/scraper
per raccogliere contenuti senza **consenso scritto**.
Pertanto **NON attiviamo crawling massivo né riuso
automatico del contenuto**. Il layout viene studiato
con campioni di ricerca; per miglioramenti in massa
servono permesso del publisher o fonti ufficiali autonome.

## 2. Cose di Casa — 432 schede, 431 orari mancanti

Esempio originale:
https://www.cosedicasa.com/mercatini/venezia-campo-san-maurizio

HTML reale esaminato:
- `meta[property="article:modified_time"]` per aggiornamento editoriale;
- `div.mercatini-mostre-date-big time` per intervalli
  con giorni espliciti dell'anno (NON tutte date ricorrenti);
- `div.mercatini-mostre-row.mercatini-mostre-address` per sede;
- classi `-suspension`, `-contacts`, `-phone`,
  `-website`, `-performer` per eccezioni,
  contatti, siti e organizzatore;
- gli **orari** sono spesso nel corpo redazionale,
  ad esempio "dalle ore 9 alle 19", e non in una
  colonna CSS chiamata `orario`;
- numeri di espositori, categorie, fotografie e
  avvisi di possibile annullamento sono ulteriori informazioni.

Confronto Campo San Maurizio: il sito pubblica l'orario
9–19, un elenco di edizioni del 2026, indirizzo,
organizzatore e avvertenze; nel nostro record
l'indirizzo e l'organizzatore sono presenti, ma
`orario_testo=""` e `date=[]`.
Lo snapshot ha `ricorrenza_testo="mensile"`,
non sufficiente per ricostruire le cinque edizioni.

**Incoerenza originale da non propagare ciecamente:**
il campo "Sospensioni" riporta mesi non compatibili
con almeno alcune date annuali pubblicate.
Il parser dovrà sempre preferire *edizioni esplicite*
e segnalare collisioni con sospensioni.

Le pagine hanno copyright e disclaimer contro
la riproduzione dei contenuti. La lettura di
pochi esempi non concede diritti di riuso automatico
delle 432 schede. Il punto di miglioramento concreto
è ricostruire un **adapter di campo** e chiedere
autorizzazione per uso ricorrente, oppure ricontrollare
sedi, calendari e orari presso gli organizzatori
indicati nelle schede.

## 3. EventiESagre — 2.197 schede

Esempio reale:
https://www.eventiesagre.it/Mercatini_Filiera+Corta/21185843_Mercato+Settimanale+Di+Alba+Adriatica.html

HTML esaminato:
- numero ID evento stabile, titolo e tipologia;
- intestazioni `Dal:` e `Al:` dell'edizione;
- indicatore esplicito **"Evento Passato!"**;
- sede e Comune, giorno/ricorrenza nel testo,
  orario, prodotti e note;
- un timbro "Data ultimo aggiornamento pagina",
  non sostituibile con la data in cui il nostro
  importer ha creato la scheda.

Confronto Alba Adriatica: evento originario
**2 gennaio 2023**, etichettato passato, e pagina
riportante aggiornamento 2021. La nostra scheda
conserva sede e orario e genera date previste
del 2026 per la regola "ogni lunedì".
Non sono false date confermate, ma è sbagliato
considerare un annuncio del 2023 prova sufficiente
che il mercato svolga ogni lunedì nel 2026.

Il vecchio `backend/scraper_eventiesagre.py`
usa contenitori HTML generici, prende solo i primi
paragrafi di fallback e produce campi senza
marcare in modo affidabile *archiviato vs corrente*.
Il vecchio `backend/cleaner.py` proietta date
da una ricorrenza senza distinguere l'età della
**fonte originaria** dalla data di import.
Lo scraper legacy NON va riattivato a tappeto:
il sito vieta la riproduzione dei contenuti.
Usiamo i link esistenti come piste verso la
fonte Comune/organizzatore.

## 4. Fonti ufficiali: tipo di dato e limiti

**Regione Lombardia MERCap**
https://www.dati.lombardia.it/d/68zx-njaw

L'adapter `backend/source_lombardia.py` legge API,
metadata e controllo di licenza. Campi:
`codice_id`, `istat`, `despro`, `descom`,
`indirizzi`/`ubicazione`, `giorno`,
`periodicita_tipo`, `mesi_svolgimento`,
orari stagionali e coordinate WGS84 quando
presenti. Granularità **sede+giorno**.
Nel campione live precedente 1.360 righe,
1.359 indirizzi e 889 orari; non tutte le righe
includono orari originari, quindi quel vuoto
non è automaticamente un bug del parser.

**Comune di Milano DS291**: 85 righe, orari
e coordinate ma non vie nel JSON.
Il PDF comunale 1 ottobre 2026 contiene le
sedi; abbiamo già ricongiunto 75 indirizzi
con ID GIS e documenti ufficiali. Gli altri
non sono un bug di colonna inventabile.

**Bologna, Firenze, Corciano**: adapter
ufficiali normalizzati, verificati per ID,
regione, schema, anno e campo; protezione
contro dati vecchi e riempimenti non provati.

**Veneto**: calendario mercati PDF e sagre/fiere
XLSX sono fonti distinte. Posteggi individuali
NON equivalgono a nuovi mercati e le sagre
NON sono mercati settimanali; verificare
licenza del singolo dataset prima di riuso
automatico.

## Cosa è stato realizzato in questa revisione

- `backend/source_layout_forensics.py`: parser
  **offline** a contratto per tre layout reali,
  registra solo presenza di campi, intervalli,
  flag storico e assenze nel nostro mercato.
  Non salva testo editoriale, telefono o email
  e non si collega in rete.
- `backend/stored_market_sibling_proposals.py`:
  cerca sedi **già contenute nelle nostre schede**
  quando copie dello stesso publisher con URL,
  Comune, provincia e giorno le hanno perse.
  Registra ID donatore e ricevente per
  ulteriori verifiche; zero merge automatici.
- Test di fatto su Spinea, archivio EventiESagre,
  calendario Cose di Casa, collisioni fra sedi,
  duplicati e permessi di fonte.
- Gli incompleti rimangono nel sito. La review
  non attribuisce alcuna verifica di apertura,
  un indirizzo preciso o un nuovo diritto di
  raccolta automatizzata.

## Metrica corretta

**Tasso di conservazione dei campi disponibili
dalla singola sorgente**, misurato su campioni
per versione di layout e controllato end-to-end:

    fonte originale → parser → normalizzazione
        → snapshot → export → sito

Ogni perdita deve avere una ragione verificabile
(età, licenza, campo realmente assente, collisione,
bug del parser, valore rifiutato da QA).
Un numero totale più alto di schede da solo non
rappresenta un aumento di qualità.
