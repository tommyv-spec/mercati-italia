# Verifica dei formati delle fonti

Generato per il 2026-10-20.

Catalogo: **13,824 schede**, **5,752 URL primari**, **72 hostname** (71 dopo l’unificazione di `www`).

**109 unità di formato URL**: 19 con confronto del campione completato, 85 parziali, 5 da verificare. Le 27 unità ausiliarie non aumentano il numero delle schede.

Le spunte indicano una verifica eseguita sul campione. Non attestano che tutte le schede siano corrette, aggiornate o complete. I TODO indicano separatamente le correzioni e i raccordi ancora da realizzare. Il report quotidiano legge il catalogo e questo registro senza effettuare nuove richieste alle fonti.

## Check-in

- **2026-10-19T22:47:28.515202+00:00 — HAPPINGS-FORMATS-20261020**: Tre formati primari e due formati attuali osservati; sette HTML completi e un 404. Registrati gap del dettaglio, route provinciali mancanti e qualificatori temporali.
- **2026-10-19T22:55:49.608199+00:00 — OFFICIAL-FORMATS-20261020**: Otto formati primari ufficiali esaminati, 36 risposte complete su 37 risorse. Distinte le perdite in lettura, normalizzazione, export e i dati storici già nella fonte.
- **2026-10-19T23:09:26.342049+00:00 — OTHER-FORMATS-20261020**: 33 unità di altri editori: 29 HTML esaminati, tre errori HTTP e un URL malformato. Ferrara resta parziale per contenuto dinamico e SagreFVG per transizione HTTP/canonical irrisolta; distinti indici, dettagli, edizioni passate e identità discordanti.
- **2026-10-19T23:27:40.941196+00:00 — OFFICIAL-HOURS-FIX-20261020**: Conservazione degli orari Firenze/Bologna verificata fino all’export; due TODO chiusi, tredici ufficiali ancora aperti. Rinnovate le impronte degli otto formati e dei raccordi condivisi sulla base delle prove finali, senza nuove letture o ri-datazioni delle fonti.
- **2026-10-19T23:28:56.354672+00:00 — EDITORIAL-FORMATS-20261020**: Esaminati 16 prefissi Eventi e Sagre e cinque varianti di calendario Cose di Casa. Replay di 17 pagine prima/dopo la correzione; ponte dei nuovi metadati ancora aperto.
- **2026-10-19T23:28:56.354672+00:00 — CITYNEWS-FORMATS-20261020**: 48 unità di formato, 47 contenuti letti e un errore 503. Distinti dettagli, variante redazionale, articoli e indici; 11 indirizzi e 14 testi di orario presenti in fonte ma vuoti nelle schede campione.
- **2026-10-19T23:31:01.565477+00:00 — SOURCE-FORMATS-VALIDATION-20261020**: 995 test Python, 8 file di test Node, build e worker verificati; replay offline del catalogo con 17 gate superati e 13.824 identità conservate. Revisione indipendente conclusa; checklist integrata nel report quotidiano esistente, con 102 confronti completi, sette parziali e 51 TODO aperti.
- **2026-10-20T16:09:24.295488+00:00 — HAPPINGS-DETAIL-MECHANISM-20261020**: Nuovo lettore dettagli, discovery dalle sitemap con stato persistente, calendari espliciti e visualizzazione. Nove pagine reali confrontate con 13.824 schede; due nuove identità nel replay, nessuna scheda esistente alterata. HAPP-FORMAT-01 e 02 chiusi con prove; gli altri problemi delle fonti restano tracciati.

## Checklist dei formati primari

Legenda: ✓ completato sul campione; ◐ parziale; ○ da verificare.

| Formato / fonte | Schede | Fonte | Campi | Parser | Catalogo | TODO aperti |
| --- | ---: | :---: | :---: | :---: | :---: | --- |
| `happings.com` · `/it/{scheda-comunale}.html` | 4746 | ✓ | ✓ | ✓ | ✓ | HAPP-FORMAT-03, HAPP-FORMAT-04, HAPP-FORMAT-05, HAPP-FORMAT-06 |
| `happings.com` · `/it/mercati-settimanali-a-{provincia}.html` | 4487 | ✓ | ✓ | ✓ | ✓ | HAPP-FORMAT-07 |
| `eventiesagre.it` · `/Mercatini_Filiera+Corta/{id}_{slug}.html` | 1150 | ✓ | ✓ | ✓ | ✓ | EES-METADATA-ROUNDTRIP, EES-MULTI-LOCATION-BRIDGE, EES-NARRATIVE-FIELD-GAPS, EES-URL-DISCOVERY-INVENTORY, EDITORIAL-FIELD-RETENTION-GATE |
| `dati.lombardia.it` · `/d/68zx-njaw` | 1128 | ✓ | ✓ | ○ | ✓ | OFF-LO-01, OFF-LO-02 |
| `cosedicasa.com` · `/mercatini/{slug}` | 432 | ✓ | ✓ | ○ | ✓ | CDC-STRUCTURED-ADAPTER, CDC-CALENDAR-SEMANTICS, CDC-SOURCE-INTERNAL-CONFLICTS, CDC-HOURS-CONTEXT, CDC-PROVENANCE-URLS, EDITORIAL-FIELD-RETENTION-GATE |
| `happings.com` · `/it/mercati-settimanali-ad-{provincia}.html` | 414 | ✓ | ✓ | ✓ | ✓ | HAPP-FORMAT-07 |
| `eventiesagre.it` · `/Mercatini_Vari/{id}_{slug}.html` | 267 | ✓ | ✓ | ✓ | ✓ | EES-METADATA-ROUNDTRIP, EES-MULTI-LOCATION-BRIDGE, EES-NARRATIVE-FIELD-GAPS, EES-URL-DISCOVERY-INVENTORY, EDITORIAL-FIELD-RETENTION-GATE |
| `eventiesagre.it` · `/Mercatini_Antiquariato/{id}_{slug}.html` | 205 | ✓ | ✓ | ✓ | ✓ | EES-METADATA-ROUNDTRIP, EES-MULTI-LOCATION-BRIDGE, EES-NARRATIVE-FIELD-GAPS, EES-URL-DISCOVERY-INVENTORY, EDITORIAL-FIELD-RETENTION-GATE |
| `eventiesagre.it` · `/Mercatini_Artigianato/{id}_{slug}.html` | 173 | ✓ | ✓ | ✓ | ✓ | EES-METADATA-ROUNDTRIP, EES-MULTI-LOCATION-BRIDGE, EES-NARRATIVE-FIELD-GAPS, EES-URL-DISCOVERY-INVENTORY, EDITORIAL-FIELD-RETENTION-GATE |
| `eventiesagre.it` · `/Mercatini_Usato/{id}_{slug}.html` | 151 | ✓ | ✓ | ✓ | ✓ | EES-METADATA-ROUNDTRIP, EES-MULTI-LOCATION-BRIDGE, EES-NARRATIVE-FIELD-GAPS, EES-URL-DISCOVERY-INVENTORY, EDITORIAL-FIELD-RETENTION-GATE |
| `eventiesagre.it` · `/Mercatini_Enogastronomici/{id}_{slug}.html` | 142 | ✓ | ✓ | ✓ | ✓ | EES-METADATA-ROUNDTRIP, EES-MULTI-LOCATION-BRIDGE, EES-NARRATIVE-FIELD-GAPS, EES-URL-DISCOVERY-INVENTORY, EDITORIAL-FIELD-RETENTION-GATE |
| `dati.comune.milano.it` · `/dataset/ds291-economia-mercati-settimanali-scoperti` | 85 | ✓ | ✓ | ○ | ✓ | OFF-MI-01, OFF-MI-02, OFF-MI-03 |
| `dati.comune.roma.it` · `/catalog/dataset/d881` | 70 | ✓ | ✓ | ○ | ✓ | OFF-RO-01, OFF-RO-02 |
| `opendata.comune.bologna.it` · `/explore/dataset/mercati-e-fiere/` | 39 | ✓ | ✓ | ○ | ✓ | OFF-BO-02, OFF-BO-03 |
| `eventiesagre.it` · `/Mercatini_hobbisti+creativi/{id}_{slug}.html` | 32 | ✓ | ✓ | ✓ | ✓ | EES-METADATA-ROUNDTRIP, EES-MULTI-LOCATION-BRIDGE, EES-NARRATIVE-FIELD-GAPS, EES-URL-DISCOVERY-INVENTORY, EDITORIAL-FIELD-RETENTION-GATE |
| `cosafareafirenze.it` · `/mercati-firenze/` | 22 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-05, NC-06, NC-09, NC-15, NC-14 |
| `eventiesagre.it` · `/Eventi_Enogastronomici/{id}_{slug}.html` | 17 | ✓ | ✓ | ✓ | ✓ | EES-METADATA-ROUNDTRIP, EES-MULTI-LOCATION-BRIDGE, EES-NARRATIVE-FIELD-GAPS, EES-URL-DISCOVERY-INVENTORY, EDITORIAL-FIELD-RETENTION-GATE |
| `eventiesagre.it` · `/Mercatini_Collezionismo/{id}_{slug}.html` | 16 | ✓ | ✓ | ✓ | ✓ | EES-METADATA-ROUNDTRIP, EES-MULTI-LOCATION-BRIDGE, EES-NARRATIVE-FIELD-GAPS, EES-URL-DISCOVERY-INVENTORY, EDITORIAL-FIELD-RETENTION-GATE |
| `eventiesagre.it` · `/Mercatini_Natale/{id}_{slug}.html` | 13 | ✓ | ✓ | ✓ | ✓ | EES-METADATA-ROUNDTRIP, EES-MULTI-LOCATION-BRIDGE, EES-NARRATIVE-FIELD-GAPS, EES-URL-DISCOVERY-INVENTORY, EDITORIAL-FIELD-RETENTION-GATE |
| `eventiesagre.it` · `/Eventi_Feste/{id}_{slug}.html` | 13 | ✓ | ✓ | ✓ | ✓ | EES-METADATA-ROUNDTRIP, EES-MULTI-LOCATION-BRIDGE, EES-NARRATIVE-FIELD-GAPS, EES-URL-DISCOVERY-INVENTORY, EDITORIAL-FIELD-RETENTION-GATE |
| `romatoday.it` · `/eventi/{percorso-evento}.html` | 10 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `eventiesagre.it` · `/Eventi_Mostra+Mercato/{id}_{slug}.html` | 9 | ✓ | ✓ | ✓ | ✓ | EES-METADATA-ROUNDTRIP, EES-MULTI-LOCATION-BRIDGE, EES-NARRATIVE-FIELD-GAPS, EES-URL-DISCOVERY-INVENTORY, EDITORIAL-FIELD-RETENTION-GATE |
| `emiliaromagnaturismo.it` · `/it/eventi/{slug}` | 8 | ✓ | ✓ | ○ | ✓ | NC-01, NC-03, NC-04, NC-06, NC-07, NC-15, NC-14 |
| `trentino.com` · `/it/calendario/` | 8 | ○ | ○ | ○ | ○ | NC-08, NC-11, NC-14 |
| `algherohospitality.it` · `/mercati-rionali-di-alghero/` | 7 | ✓ | ✓ | ○ | ✓ | NC-01, NC-05, NC-06, NC-10, NC-14 |
| `eventi.bergamo.it` · `/evento/{slug}/` | 7 | ✓ | ✓ | ○ | ✓ | NC-01, NC-03, NC-04, NC-05, NC-07, NC-15, NC-14 |
| `genovatoday.it` · `/eventi/{percorso-evento}.html` | 7 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `solosagre.it` · `/mostre-e-mercatini/{regione}/{provincia}/{comune}/{slug}.html` | 7 | ✓ | ✓ | ○ | ✓ | NC-01, NC-03, NC-06, NC-07, NC-09, NC-15, NC-14 |
| `eventiesagre.it` · `/Eventi_Festival/{id}_{slug}.html` | 6 | ✓ | ✓ | ✓ | ✓ | EES-METADATA-ROUNDTRIP, EES-MULTI-LOCATION-BRIDGE, EES-NARRATIVE-FIELD-GAPS, EES-URL-DISCOVERY-INVENTORY, EDITORIAL-FIELD-RETENTION-GATE |
| `sagretorino.it` · `/` | 6 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-06, NC-07, NC-13, NC-14 |
| `firenzetoday.it` · `/eventi/{percorso-evento}.html` | 5 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `milanopocket.it` · `/sagre-lombardia/` | 5 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-08, NC-14 |
| `sagreumbre.it` · `/fiere-mercati/` | 5 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-04, NC-08, NC-14 |
| `comune.roma.it` · `/web-resources/cms/documents/MunXIII_DD647_2026_Graduatorie_mercati.pdf` | 4 | ✓ | ✓ | ○ | ✓ | OFF-RO-03 |
| `feelflorence.it` · `/it/punti-di-interesse/{slug}` | 4 | ✓ | ✓ | ○ | ✓ | OFF-FI-02, OFF-FI-03 |
| `modenatoday.it` · `/eventi/{percorso-evento}.html` | 4 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `umbriaeventi.com` · `/{slug}-{id}.htm` | 4 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-04, NC-05, NC-06, NC-07, NC-08, NC-09, NC-10, NC-11, NC-14 |
| `umbriaeventi.com` · `/` | 4 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-06, NC-07, NC-08, NC-15, NC-14 |
| `enjoysicilia.it` · `/it/events/` | 3 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-14 |
| `riminitoday.it` · `/eventi/{percorso-evento}.html` | 3 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `romatoday.it` · `/eventi/tipo/{filtri}/` | 3 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `sagrefvg.it` · `/` | 3 | ◐ | ◐ | ○ | ✓ | NC-01, NC-02, NC-03, NC-04, NC-06, NC-07, NC-10, NC-15, NC-14 |
| `sagretoscane.com` · `/fiere-mercati/si/` | 3 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-05, NC-08, NC-14 |
| `suedtirol.info` · `/it/esperienze/eventi` | 3 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-04, NC-08, NC-11, NC-12, NC-14 |
| `veneziatoday.it` · `/eventi/{percorso-evento}.html` | 3 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `vicenzatoday.it` · `/eventi/tipo/{filtri}/` | 3 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `assosagre.it` · `/calendario_sagre.php?id_provincia={value}&id_sagra={value}` | 2 | ○ | ○ | ○ | ○ | NC-08, NC-11, NC-14 |
| `baritoday.it` · `/eventi/{percorso-evento}.html` | 2 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `bolognatoday.it` · `/eventi/{percorso-evento}.html` | 2 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `bresciatoday.it` · `/eventi/{percorso-evento}.html` | 2 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `brindisireport.it` · `/tag/{tag}/` | 2 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `cittadellaspezia.com` · `/tag/sagre/` | 2 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-14 |
| `comune.corciano.pg.it` · `/area_letturaDocumento/29645/pagsistema.html` | 2 | ✓ | ✓ | ○ | ✓ | OFF-CO-01 |
| `eventiintoscana.it` · `/` | 2 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-07, NC-14 |
| `ferrarainfo.com` · `/it/eventi/eventi` | 2 | ✓ | ◐ | ○ | ◐ | NC-02, NC-03, NC-11, NC-12, NC-14 |
| `forlitoday.it` · `/eventi/{percorso-evento}.html` | 2 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `frosinonetoday.it` · `/eventi/{percorso-evento}.html` | 2 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `genovatoday.it` · `/eventi/tipo/{filtri}/` | 2 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `lazioinfesta.com` · `/` | 2 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-07, NC-14 |
| `monzatoday.it` · `/eventi/{percorso-evento}.html` | 2 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `novaratoday.it` · `/eventi/tipo/{filtri}/` | 2 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `palermotoday.it` · `/eventi/{percorso-evento}.html` | 2 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `paradisola.it` · `/eventi-sardegna` | 2 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-07, NC-14 |
| `pugliainfesta.it` · `/evento/{id}/{slug}.html` | 2 | ✓ | ✓ | ○ | ✓ | NC-01, NC-03, NC-05, NC-06, NC-07, NC-08, NC-13, NC-14 |
| `ravennatoday.it` · `/eventi/tipo/{filtri}/` | 2 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `sagreinromagna.it` · `/sagre_per_provincia/1/ravenna` | 2 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-06, NC-07, NC-08, NC-14 |
| `terredipisa.it` · `/events/categories/sagra-fiere-mercati/` | 2 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-06, NC-07, NC-14 |
| `torinotoday.it` · `/eventi/{percorso-evento}.html` | 2 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `trevisotoday.it` · `/eventi/tipo/{filtri}/` | 2 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `varesenews.it` · `/category-evento/eventi-sagre-feste/` | 2 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-04, NC-05, NC-07, NC-13, NC-14 |
| `veneziatoday.it` · `/eventi/tipo/{filtri}/` | 2 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `arezzonotizie.it` · `/eventi/{percorso-evento}.html` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `bolognatoday.it` · `/eventi/tipo/{filtri}/` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `bresciatoday.it` · `/eventi/tipo/{filtri}/` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `cagliaritoday.it` · `/eventi/{percorso-evento}.html` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `casertanews.it` · `/eventi/{percorso-evento}.html` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `cataniatoday.it` · `/eventi/{percorso-evento}.html` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `cesenatoday.it` · `/eventi/{percorso-evento}.html` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `chietitoday.it` · `/attualita/{articolo}.html` | 1 | ✓ | ✓ | ○ | ✓ | CNY-EDITORIAL, CNY-ROUNDTRIP |
| `comune.roma.it` · `/web/it/bando-concorso.page?contentId={value}` | 1 | ✓ | ✓ | ○ | ✓ | OFF-RO-03 |
| `eventi.bergamo.it` · `/` | 1 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-04, NC-07, NC-14 |
| `eventiesagre.it` · `/Eventi_Sagre/{id}_{slug}.html` | 1 | ✓ | ✓ | ✓ | ✓ | EES-METADATA-ROUNDTRIP, EES-MULTI-LOCATION-BRIDGE, EES-NARRATIVE-FIELD-GAPS, EES-URL-DISCOVERY-INVENTORY, EDITORIAL-FIELD-RETENTION-GATE |
| `eventiesagre.it` · `/Eventi_Folklore/{id}_{slug}.html` | 1 | ✓ | ✓ | ✓ | ✓ | EES-METADATA-ROUNDTRIP, EES-MULTI-LOCATION-BRIDGE, EES-NARRATIVE-FIELD-GAPS, EES-URL-DISCOVERY-INVENTORY, EDITORIAL-FIELD-RETENTION-GATE |
| `eventiesagre.it` · `/Eventi_Fiere/{id}_{slug}.html` | 1 | ✓ | ✓ | ✓ | ✓ | EES-METADATA-ROUNDTRIP, EES-MULTI-LOCATION-BRIDGE, EES-NARRATIVE-FIELD-GAPS, EES-URL-DISCOVERY-INVENTORY, EDITORIAL-FIELD-RETENTION-GATE |
| `eventiinsardegna.it` · `/` | 1 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-04, NC-09, NC-14 |
| `ferraratoday.it` · `/eventi/tipo/{filtri}/` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `ferraratoday.it` · `/eventi/{percorso-evento}.html` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `firenzetoday.it` · `/eventi/tipo/{filtri}/` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `frosinonetoday.it` · `/eventi/tipo/{filtri}/` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `leccotoday.it` · `/eventi/{percorso-evento}.html` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `lombardiainfesta.it` · `/` | 1 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-07, NC-14 |
| `milanotoday.it` · `/eventi/tipo/{filtri}/` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `modenatoday.it` · `/eventi/tipo/{filtri}/` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `napolidavivere.it` · `/category/eventi/sagre-e-feste/` | 1 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-07, NC-08, NC-14 |
| `novaratoday.it` · `/eventi/{percorso-evento}.html` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `padovatoday.it` · `/eventi/{percorso-evento}.html` | 1 | ○ | ○ | ○ | ○ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP, RETRY-CITYNEWS-PADOVA |
| `palermotoday.it` · `/eventi/tipo/{filtri}/` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `parmatoday.it` · `/eventi/{percorso-evento}.html` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `ravennatoday.it` · `/eventi/{percorso-evento}.html` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `riminitoday.it` · `/eventi/tipo/{filtri}/` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `romapop.it` · `/eventi/roma/sagre-fiere-mercatini/` | 1 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-07, NC-11, NC-14 |
| `sagrefvg.it` · `/sagris/` | 1 | ✓ | ✓ | ○ | ✓ | NC-01, NC-02, NC-03, NC-04, NC-06, NC-07, NC-10, NC-15, NC-14 |
| `salernotoday.it` · `/eventi/tipo/{filtri}/` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `trentino.com` · `/it/calendario/dettagli/{slug}/#{edizione}` | 1 | ○ | ○ | ○ | ○ | NC-08, NC-11, NC-14 |
| `trevisotoday.it` · `/eventi/{percorso-evento}.html` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `vicenzatoday.it` · `/eventi/{percorso-evento}.html` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `viterbotoday.it` · `/eventi/{percorso-evento}.html` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DETAIL, CNY-EDITORIAL, CNY-ROUNDTRIP |
| `viterbotoday.it` · `/eventi/tipo/{filtri}/` | 1 | ✓ | ✓ | ○ | ✓ | CNY-DISCOVERY, CNY-ROUNDTRIP |
| `wwwservizi.regione.emilia-romagna.itnote.asp` · `/?anno={value}&cod_co={value}&dt_dataa={value}&dt_datada={value}&progr_fiera={value}&r1={value}&r2={value}&strr_provincia={value}&strr_sede={value}&strs_keywords={value}` | 1 | ○ | ○ | ○ | ○ | NC-08, NC-11, NC-14 |

## Evidenze e prossime azioni per formato

### happings.com--7b87b2b2b5db

`/it/{scheda-comunale}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T22:47:28.515202+00:00.
- [x] Fonte letta: Letti e analizzati 4 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Replay del lettore provinciale sul contenuto restituito e confronto con il monitor del dettaglio; il monitor riconosce il template ma non importa i campi del dettaglio.
- [x] Catalogo confrontato: Confrontate 14 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.happings.com/it/mercato-settimanale-a-citt---sant-angelo.html — http_error, lettura 2026-10-19T22:39:48.012688+00:00; SHA-256 `9026b64d6aa06cb533291ec1991e64cd7bd5a1e12ceeeaf17c1cb57e30bbd059`.
- Campione: https://www.happings.com/it/mercato-settimanale-a-poggiorsini--ogni-15gg-.html — read, lettura 2026-10-19T22:37:23.63424+00:00; SHA-256 `94fb7ce8a36011999e2111b8bed935b2d57485523255e3dd59ed28603aed050c`.
- Campione: https://www.happings.com/it/mercato-settimanale-a-lana.html — read, lettura 2026-10-19T22:30:14.309439+00:00; SHA-256 `5cf7bd9871a61fd76a1f00210459997d3777d73d897e9e70a34bdeb114bf8012`.
- Campione: https://www.happings.com/it/mercato-settimanale-a-riolo-terme--estivo-.html — read, lettura 2026-10-19T22:36:38.906006+00:00; SHA-256 `3eb4fe0fb501c86ff5d01c1a085809b7d07c6f1d4c2ceccd5741e8bb2686ada1`.
- Campione: https://www.happings.com/it/mercato-settimanale-a-trieste.html — read, lettura 2026-10-19T22:35:58.712386+00:00; SHA-256 `8504f0ff37d0e38d6944fdb121aa1972d7dd08aa65458b5dd7fa6d1253d08f85`.
- Riscontro: Error: Failed to fetch URL: HTTP error! Status: 404
- Riscontro: existing_index_reader_with_source_and_routing_limits
- Riscontro: existing_index_reader_with_source_and_routing_limits
- Riscontro: existing_index_reader_with_source_and_routing_limits
- Riscontro: existing_index_reader_with_source_and_routing_limits
- Dettagli: `reports/automation/source-format-audit-2026-10-20/happings.json`.

### happings.com--04b85587f84c

`/it/mercati-settimanali-a-{provincia}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T22:47:28.515202+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Replay del lettore provinciale sul contenuto restituito e confronto con il monitor del dettaglio; il monitor riconosce il template ma non importa i campi del dettaglio.
- [x] Catalogo confrontato: Confrontate 246 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.happings.com/it/mercati-settimanali-a-milano.html — read, lettura 2026-10-19T22:34:55.035315+00:00; SHA-256 `6705b3eaed3523c3f1aaffac4ef30ff630f794743861ccaff7c6fa10bd1b80aa`.
- Riscontro: existing_index_reader_with_source_and_routing_limits
- Dettagli: `reports/automation/source-format-audit-2026-10-20/happings.json`.

### eventiesagre.it--c25111abbd5a

`/Mercatini_Filiera+Corta/{id}_{slug}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Confronto prima/dopo sui medesimi HTML; i nuovi campi non supportati da RawMarket/CleanMarket restano una perdita di salvataggio aperta.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventiesagre.it/Mercatini_Filiera+Corta/21185843_Mercato+Settimanale+Di+Alba+Adriatica.html — read, lettura 2026-10-19T22:29:31Z; SHA-256 `2accd13038bd19542ae5d548c9f04d4ac46a6f233096402b2bb044652228695b`.
- Riscontro: Il replay nuovo preserva il riquadro dell’evento. Metadati di edizione/archivio e casi con più sedi richiedono ancora il ponte di salvataggio.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/editorial.json`.

### dati.lombardia.it--eb61afdd496f

`/d/68zx-njaw` — primary_catalog.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1128 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.dati.lombardia.it/d/68zx-njaw — read, lettura 2026-10-19T22:36:54.514177+00:00; SHA-256 `798c27ee841f81d71f15024f83634aba4f938da0e36847e045cabae598992e65`.
- Riscontro: 171 source rows contain dal/al; 14 are non-full-year or ambiguous boundaries. Three exact catalog records contain 38 forecasts outside the explicit single source boundary; one further record has an ambiguous combined al value and 17 forecasts.
- Riscontro: The source dictionary labels ubicazione as market denomination. Its value is absent from displayed adapter fields for 700 rows with separate indirizzi; this includes seasonal qualifications. This is a preservation count, not 700 confirmed identity errors.
- Riscontro: identita_fonte is present in all 1360 normalized source rows but omitted from every export_static.normalize output; dal/al are absent even before export.
- Riscontro: I difetti misurati nel primo audit conservano il loro ambito storico; il report separato dopo il fix documenta soltanto le correzioni orari Firenze/Bologna e le verifiche di compatibilità. Gli altri TODO restano aperti.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### cosedicasa.com--e4978a2ff443

`/mercatini/{slug}` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 5 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 5 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.cosedicasa.com/mercatini/bologna-piazza-s-stefano — read, lettura 2026-10-19T22:32:24.298861+00:00; SHA-256 `f74caed341212287b133ce954ec22b1ec50089722f2296c527be6c58afb88ae2`.
- Campione: https://www.cosedicasa.com/mercatini/venezia-campo-san-maurizio — read, lettura 2026-10-19T22:32:24.489Z; SHA-256 `21ff8d2a726098d6d832c86b52525f44721b8c9938a0f2eead8bb9c1df81879f`.
- Campione: https://www.cosedicasa.com/mercatini/todi-giardini-oberdan — read, lettura 2026-10-19T22:32:28.466Z; SHA-256 `463830f33001548da2b85d87921e87ae72ff2be0decfaabdba6871626f73010a`.
- Campione: https://www.cosedicasa.com/mercatini/cernobbio-mercatino-estivo — read, lettura 2026-10-19T22:32:32.364Z; SHA-256 `b673d0194ab787f55d333695f2243fb5d20f5c6df7fd022f9bbfb8e67cece5e8`.
- Campione: https://www.cosedicasa.com/mercatini/fiumicino-parco-da-vinci-3 — read, lettura 2026-10-19T22:32:37.059Z; SHA-256 `6db5f5bbe136aac21c23260236f5be7f1a94e5e4aad495024a9a9c7b12b4bed1`.
- Riscontro: precise_hours
- Riscontro: saturday_before_second_sunday
- Riscontro: july_august_suspension
- Riscontro: next_explicit_weekend
- Riscontro: editorial_modification_date
- Riscontro: JSON-LD dates are 2026-10-19; visible rule is second Sunday with previous Saturday, and next weekend is 2026-11-07/08.
- Riscontro: Second Saturday is not always the Saturday before the second Sunday.
- Riscontro: five_edition_intervals
- Riscontro: suspension_conflict
- Riscontro: The suspension row includes July–December while the edition list explicitly includes September, October and December.
- Riscontro: year_for_november_11_extra_edition
- Riscontro: JSON-LD dates are 2026-10-19, a Monday; visible rule is third Sunday and next date is 2027-03-21.
- Riscontro: 14_explicit_summer_dates
- Riscontro: season_and_missing_fridays
- Riscontro: canonical_source_url_change
- Riscontro: seasonal_daily_cadence
- Riscontro: inconsistent_date_bounds
- Riscontro: weather_cancellation_condition
- Riscontro: Header and JSON-LD show 2026-06-02 through 2026-08-10; the main text says 10 June through 2 August.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/editorial.json`.

### happings.com--3d81fd9e0a91

`/it/mercati-settimanali-ad-{provincia}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T22:47:28.515202+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Replay del lettore provinciale sul contenuto restituito e confronto con il monitor del dettaglio; il monitor riconosce il template ma non importa i campi del dettaglio.
- [x] Catalogo confrontato: Confrontate 77 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.happings.com/it/mercati-settimanali-ad-avellino.html — read, lettura 2026-10-19T22:32:52.622758+00:00; SHA-256 `52113c376b20c8ff0450c98a0f870331eba8087372114bbe5d140e8ad4e324e5`.
- Riscontro: existing_index_reader_with_source_and_routing_limits
- Dettagli: `reports/automation/source-format-audit-2026-10-20/happings.json`.

### eventiesagre.it--5130dde4763c

`/Mercatini_Vari/{id}_{slug}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 2 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Confronto prima/dopo sui medesimi HTML; i nuovi campi non supportati da RawMarket/CleanMarket restano una perdita di salvataggio aperta.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventiesagre.it/Mercatini_Vari/21054160_Antico+Mercatino+Di+San+Pancrazio+a+Campli.html — read, lettura 2026-10-19T22:30:11.995Z; SHA-256 `28dd0eaa0183e35bf897764591c7ae66267c04d0c8b6bad20a0b97b05c8d8b07`.
- Campione: https://www.eventiesagre.it/Mercatini_Vari/21182790_Mercati+Settimanali+A+Pescara.html — read, lettura 2026-10-19T22:32:03.377Z; SHA-256 `47232a4a4cf3bdd25b74069ad237103560f6c85a4e1ac9067917efcdfb690c9e`.
- Riscontro: Il replay nuovo preserva il riquadro dell’evento. Metadati di edizione/archivio e casi con più sedi richiedono ancora il ponte di salvataggio.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/editorial.json`.

### eventiesagre.it--86b2ab982276

`/Mercatini_Antiquariato/{id}_{slug}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Confronto prima/dopo sui medesimi HTML; i nuovi campi non supportati da RawMarket/CleanMarket restano una perdita di salvataggio aperta.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventiesagre.it/Mercatini_Antiquariato/21036009_Antiquariato+a+Bologna.html — read, lettura 2026-10-19T22:30:11.996Z; SHA-256 `9d9f57d8455e24c002e97a8085f696af0c4ee7a6989915a551ad73e72265baf2`.
- Riscontro: Il replay nuovo preserva il riquadro dell’evento. Metadati di edizione/archivio e casi con più sedi richiedono ancora il ponte di salvataggio.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/editorial.json`.

### eventiesagre.it--7b2012e05e04

`/Mercatini_Artigianato/{id}_{slug}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Confronto prima/dopo sui medesimi HTML; i nuovi campi non supportati da RawMarket/CleanMarket restano una perdita di salvataggio aperta.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventiesagre.it/Mercatini_Artigianato/21177701_Castrocaro+Sotto+Le+Stelle+Il+Mercatino+Hand+Made+A+Castrocaro+Terme.html — read, lettura 2026-10-19T22:30:11.996Z; SHA-256 `a55d2d5cf557b9ec761009abcb275b65db4b43e6a65fc0db53c6b3fd99e17959`.
- Riscontro: Il replay nuovo preserva il riquadro dell’evento. Metadati di edizione/archivio e casi con più sedi richiedono ancora il ponte di salvataggio.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/editorial.json`.

### eventiesagre.it--85894968edb7

`/Mercatini_Usato/{id}_{slug}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Confronto prima/dopo sui medesimi HTML; i nuovi campi non supportati da RawMarket/CleanMarket restano una perdita di salvataggio aperta.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventiesagre.it/Mercatini_Usato/21163185_Il+Mercatino+a+Argenta.html — read, lettura 2026-10-19T22:30:33.914Z; SHA-256 `1a1b9060153367c58e5ec4e73206ce9ce58bc82a04ed90dc75f46fcd0c7edcc3`.
- Riscontro: Il replay nuovo preserva il riquadro dell’evento. Metadati di edizione/archivio e casi con più sedi richiedono ancora il ponte di salvataggio.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/editorial.json`.

### eventiesagre.it--f3b997a2f09a

`/Mercatini_Enogastronomici/{id}_{slug}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Confronto prima/dopo sui medesimi HTML; i nuovi campi non supportati da RawMarket/CleanMarket restano una perdita di salvataggio aperta.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventiesagre.it/Mercatini_Enogastronomici/21032063_Mercato+della+Terra.html — read, lettura 2026-10-19T22:30:33.914Z; SHA-256 `ccb12553c0e89ec087d82dc17ae83edfb42621208fd65230045deac41cc42059`.
- Riscontro: Il replay nuovo preserva il riquadro dell’evento. Metadati di edizione/archivio e casi con più sedi richiedono ancora il ponte di salvataggio.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/editorial.json`.

### dati.comune.milano.it--de1e536ced97

`/dataset/ds291-economia-mercati-settimanali-scoperti` — primary_catalog.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 85 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://dati.comune.milano.it/dataset/ds291-economia-mercati-settimanali-scoperti — read, lettura 2026-10-19T22:36:52.908225+00:00; SHA-256 `805841631aaec790c82f306cd6d95d7118acb7872d18633f922c8235f5323851`.
- Riscontro: Six PDF rows absent from prior partial extraction: De Predis Monday, Trechi Monday, Mompiani Tuesday, Segneri Thursday, Delle Betulle (Olmi) Saturday, Osoppo Saturday. Five match existing name/ID mappings; Olmi needs an explicit alias review. Complete venue/day reconciliation is still required; no direct catalog edits follow from this report.
- Riscontro: Seasonal, per-street hours and street stretch columns are not consumed by the operational overlays; they only reuse reviewed names/days and a 75-entry street manifest.
- Riscontro: The JSON and CSV differ in one MERCATO label (ID39: Fauch / Fauchè); stable ID and the other name field are retained. GeoJSON provides additional polygon geometry, not new street text.
- Riscontro: I difetti misurati nel primo audit conservano il loro ambito storico; il report separato dopo il fix documenta soltanto le correzioni orari Firenze/Bologna e le verifiche di compatibilità. Gli altri TODO restano aperti.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### dati.comune.roma.it--eae32c9ad822

`/catalog/dataset/d881` — primary_catalog.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 70 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://dati.comune.roma.it/catalog/dataset/d881 — read, lettura 2026-10-19T22:36:59.547377+00:00; SHA-256 `7607023529fb6fe37e27b1bd8fdb07e8d2a1571691dba2e744cb831d32465a53`.
- Riscontro: Source hours absent from at least 68 rigorously name-and-address matched current records; these are historical data and cannot be promoted to fresh 2026 confirmed opening times.
- Riscontro: Two catalog records have replacement-character damage, while source decoding as cp1252 recovers Cinecittà and Unità.
- Riscontro: Current repository contains metadata/probe readers and curated XIII overlays but no maintained d881 row adapter; old import cause cannot be attributed to code not present.
- Riscontro: I difetti misurati nel primo audit conservano il loro ambito storico; il report separato dopo il fix documenta soltanto le correzioni orari Firenze/Bologna e le verifiche di compatibilità. Gli altri TODO restano aperti.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### opendata.comune.bologna.it--72028fdb86a6

`/explore/dataset/mercati-e-fiere/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 39 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://opendata.comune.bologna.it/explore/dataset/mercati-e-fiere/ — read, lettura 2026-10-19T22:36:56.675954+00:00; SHA-256 `d1d0757432029e6254c94a4e6bf9c3a76d53bb33c2b1ee5723abe6b912841c23`.
- Riscontro: Nine source-present/catalog-missing hours proven by recordid and reproduced with current generic candidate; all nine strings have separate seasonal hours.
- Riscontro: The generic path does not preserve original days text on the 39 matching records, though it conservatively creates no forecasts from this aged source.
- Riscontro: Twelve matching catalog records have category misto although full source specialization permits a more specific reviewed category; includes one vintage and two antiquarian examples.
- Riscontro: I difetti misurati nel primo audit conservano il loro ambito storico; il report separato dopo il fix documenta soltanto le correzioni orari Firenze/Bologna e le verifiche di compatibilità. Gli altri TODO restano aperti.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### eventiesagre.it--2e3d99867afe

`/Mercatini_hobbisti+creativi/{id}_{slug}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Confronto prima/dopo sui medesimi HTML; i nuovi campi non supportati da RawMarket/CleanMarket restano una perdita di salvataggio aperta.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventiesagre.it/Mercatini_hobbisti+creativi/21194719_Il+Mercatino+Creativo+Handmade+A+Ferrara.html — read, lettura 2026-10-19T22:30:33.914Z; SHA-256 `dba3df4b834c00914b3f51d617a79cdbb4d71c64c30925d7a97c632e9598c463`.
- Riscontro: Il replay nuovo preserva il riquadro dell’evento. Metadati di edizione/archivio e casi con più sedi richiedono ancora il ponte di salvataggio.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/editorial.json`.

### cosafareafirenze.it--4aba31ad6df6

`/mercati-firenze/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 22 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.cosafareafirenze.it/mercati-firenze/ — read, lettura 2026-10-19T22:38:39.609482+00:00; SHA-256 `6429b67c954387706f0cde9fd2b5686408a75e106653a5c33897abb64c5b064e`.
- Riscontro: Gap dimostrato di ricorrenza per Indipendenza Antiquaria e conflitto di orari per Mercato Vintage Piazza Ciompi.
- Riscontro: Il confronto corrente non prova che il vecchio scraper vedesse lo stesso contenuto: il listato mensile viene aggiornato.
- Riscontro: Non sostituire una sede salvata con quella di un’altra edizione dello stesso marchio.
- Riscontro: Valori salvati molto corti come indirizzo G o ore 11/15 richiedono controllo di completezza; gli eventi corrispondenti non sono nel campione attuale, quindi nessun recupero per contiguità.
- Riscontro: Ventidue schede condividono il campione. Stessi nomi ricorrono in sedi e date diverse: Only Usato compare in più luoghi; Fiera dell’Oltrarno e Santo Spirito in Fiera sono eventi distinti.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### eventiesagre.it--eb4c1e3b925a

`/Eventi_Enogastronomici/{id}_{slug}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Confronto prima/dopo sui medesimi HTML; i nuovi campi non supportati da RawMarket/CleanMarket restano una perdita di salvataggio aperta.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventiesagre.it/Eventi_Enogastronomici/3043_November+Porc.html — read, lettura 2026-10-19T22:30:56.161Z; SHA-256 `f30e5e35f862dcbb672e5525d6fdd6aa5c21ee339393a87a434e7f8c1f187d5e`.
- Riscontro: Il replay nuovo preserva il riquadro dell’evento. Metadati di edizione/archivio e casi con più sedi richiedono ancora il ponte di salvataggio.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/editorial.json`.

### eventiesagre.it--91f1a4b8c538

`/Mercatini_Collezionismo/{id}_{slug}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Confronto prima/dopo sui medesimi HTML; i nuovi campi non supportati da RawMarket/CleanMarket restano una perdita di salvataggio aperta.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventiesagre.it/Mercatini_Collezionismo/6248_La+Domenica+Del+Collezionista.html — read, lettura 2026-10-19T22:30:56.161Z; SHA-256 `7415137902b97052d68c8df65af98b8fc5ebdb67966fbf49344a69b70e4f4d46`.
- Riscontro: Il replay nuovo preserva il riquadro dell’evento. Metadati di edizione/archivio e casi con più sedi richiedono ancora il ponte di salvataggio.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/editorial.json`.

### eventiesagre.it--1e35acf83ff0

`/Mercatini_Natale/{id}_{slug}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Confronto prima/dopo sui medesimi HTML; i nuovi campi non supportati da RawMarket/CleanMarket restano una perdita di salvataggio aperta.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventiesagre.it/Mercatini_Natale/21193810_Mercatino+Di+Natale+A+Massa+D+albe.html — read, lettura 2026-10-19T22:30:56.161Z; SHA-256 `8229fbcfba6a6274eb54b0439f81ba38102d827f927066b2449b9ac3b7ced366`.
- Riscontro: Il replay nuovo preserva il riquadro dell’evento. Metadati di edizione/archivio e casi con più sedi richiedono ancora il ponte di salvataggio.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/editorial.json`.

### eventiesagre.it--895ca733a723

`/Eventi_Feste/{id}_{slug}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Confronto prima/dopo sui medesimi HTML; i nuovi campi non supportati da RawMarket/CleanMarket restano una perdita di salvataggio aperta.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventiesagre.it/Eventi_Feste/17309_Festa+nel+Borgo+a+Cassinetta+di+Lugagnano.html — read, lettura 2026-10-19T22:31:34.736Z; SHA-256 `6b178d547da37b30a6477561e5a7dd2c1e35fd9be76d1a8d71ef387a2c0be785`.
- Riscontro: Il replay nuovo preserva il riquadro dell’evento. Metadati di edizione/archivio e casi con più sedi richiedono ancora il ponte di salvataggio.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/editorial.json`.

### romatoday.it--d53004dedb50

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.romatoday.it/eventi/hippie-market-14-15-febbraio-2026.html — read, lettura 2026-10-19T22:38:39.025982+00:00; SHA-256 `9ac2b98dd7ce020ee82fe6b7fb22da4a7d9d38439879078b54ec212cd1ae552c`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Riscontro: JSON-LD privo di endDate mentre il riquadro Quando pubblica l’intervallo completo.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### eventiesagre.it--fe59c2391d07

`/Eventi_Mostra+Mercato/{id}_{slug}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Confronto prima/dopo sui medesimi HTML; i nuovi campi non supportati da RawMarket/CleanMarket restano una perdita di salvataggio aperta.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventiesagre.it/Eventi_Mostra+Mercato/21159660_CCR2+MOSTRA+SCAMBIO+RIUSO.html — read, lettura 2026-10-19T22:31:38.080Z; SHA-256 `b5f2c7da5677d88e2780f74998bef1f81217d1d45de100e9c50a102bc9f25335`.
- Riscontro: Il replay nuovo preserva il riquadro dell’evento. Metadati di edizione/archivio e casi con più sedi richiedono ancora il ponte di salvataggio.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/editorial.json`.

### emiliaromagnaturismo.it--058519c55f08

`/it/eventi/{slug}` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://emiliaromagnaturismo.it/it/eventi/sagra-uva-lambrusco-grasparossa-di-castelvetro-di-modena — read, lettura 2026-10-19T22:38:38.919366+00:00; SHA-256 `66ca55acd751e85a707f1a72fd6a7f5af1894c7a8c41096002552717e483be61`.
- Riscontro: Catalogo senza sede descrittiva, ricorrenza e date; il campione offre informazioni storiche e una regola annuale limitata, non una nuova agenda futura.
- Riscontro: Un parser deve preservare i weekend disgiunti e la precisione del luogo, senza inventare orario giornaliero o indirizzo.
- Riscontro: Otto URL nel formato; il campione coincide con la Sagra Uva/Lambrusco di Castelvetro del catalogo. Gli altri sette dettagli non sono stati acquisiti in questa revisione.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### trentino.com--2b837e50ce8e

`/it/calendario/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [ ] Fonte letta: Acquisizione non riuscita o formato osservato solo indirettamente; non conteggiato come lettura verificata.
- [ ] Campi letti: Il contenuto non è disponibile per un confronto attendibile dei campi.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [ ] Catalogo confrontato: Confrontate 8 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.trentino.com/it/calendario/ — http_error_or_external_redirect, lettura 2026-10-19T22:38:38.827658+00:00; SHA-256 `—`.
- Riscontro: Non classificare un errore HTTP come fonte controllata o vuota; nessun nuovo timestamp di prova dei mercati.
- Riscontro: Conservare distinzione tra URL pagina e identificatore di edizione/fragment, senza assumere calendario attuale.
- Riscontro: Otto schede settimanali hanno ore e date previste ma indirizzo vuoto; risposta 503 non le riconferma.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### algherohospitality.it--e297ca84a4bf

`/mercati-rionali-di-alghero/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 7 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.algherohospitality.it/mercati-rionali-di-alghero/ — read, lettura 2026-10-19T22:38:42.279885+00:00; SHA-256 `fc061ddaaeb24666c341cad7879cc685f2ac1b50b2236bfea19b40e96499e08d`.
- Riscontro: Gran parte di sedi, orari e ricorrenze dei sette mercati risulta già salvata; i vuoti del mercato artigianale non sono un gap dimostrato della fonte.
- Riscontro: La sede di Fertilia non è aggiornabile prendendo il primo indirizzo trovato: il sito pubblica due sedi discordanti.
- Riscontro: Un estrattore di mappe deve conservare ambito e precisione, senza promuovere il centro viewport a posizione del mercato.
- Riscontro: Sette schede del catalogo condividono il campione; corrispondenza dei nomi e sedi da mantenere per sezione. Un ottavo blocco del sito non dimostra automaticamente un nuovo mercato assente da tutto il catalogo.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### eventi.bergamo.it--86372603eab0

`/evento/{slug}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventi.bergamo.it/evento/%f0%9f%9b%8d%ef%b8%8f-mercatino-agricolo-km-0-piazza-pontida-bergamo-citta-5/ — read, lettura 2026-10-19T22:38:42.124188+00:00; SHA-256 `4538cfce9aef56e512b9c789b593f5b650b0bc56b825c706eded95158a166c9c`.
- Riscontro: Ricorrenza presente in fonte e assente nella scheda: gap dimostrato.
- Riscontro: L’edizione passata e le date discordanti impediscono di trattare la lettura come prova fresca di una cadenza futura illimitata.
- Riscontro: Il contenuto turistico Bergamo Città sotto l’evento non deve fornire sede/orari del mercato.
- Riscontro: Sette URL nel formato; il campione corrisponde al mercato agricolo Piazza Pontida. Stessa identità, ma due date diverse all’interno della fonte.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### genovatoday.it--bd4d23568a60

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.genovatoday.it/eventi/artegenova-mostra-mercato-arte-moderna-contemporanea-2026.html — read, lettura 2026-10-19T22:38:43.164033+00:00; SHA-256 `ef5bceee5165bbece5e6fcbddaf8a73583295107914ce61040de5fe8e44056f5`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Riscontro: JSON-LD privo di endDate mentre il riquadro Quando pubblica l’intervallo completo.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### solosagre.it--ceaedca6c042

`/mostre-e-mercatini/{regione}/{provincia}/{comune}/{slug}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.solosagre.it/mostre-e-mercatini/emilia-romagna/ra/cervia/a-spass-per-zirvia-cervia.html — read, lettura 2026-10-19T22:38:44.680075+00:00; SHA-256 `7a83d05762a08d96945f6a8465ad7d0756cde8c368991a6f2709d74e3c04d21c`.
- Riscontro: Contaminazione dimostrata dell’indirizzo da navigazione; serve controllo generico su confini DOM e plausibilità della sede.
- Riscontro: Il sito offre un luogo descrittivo, non una strada precisa: non sostituire la contaminazione con un indirizzo inventato.
- Riscontro: Le proiezioni salvate non sono date fonte; eccezioni e stato scaduto richiedono prova ulteriore per aggiornamento.
- Riscontro: Sette URL nel formato; il campione corrisponde ad A Spass per Zirvia a Cervia, edizione 22 febbraio 2026 marcata conclusa.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### eventiesagre.it--23337f2e261f

`/Eventi_Festival/{id}_{slug}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Confronto prima/dopo sui medesimi HTML; i nuovi campi non supportati da RawMarket/CleanMarket restano una perdita di salvataggio aperta.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventiesagre.it/Eventi_Festival/21194258_Green+Market+Festival+18+19+Maggio.html — read, lettura 2026-10-19T22:31:40.269Z; SHA-256 `33e8636b716bf215a4c385148fac2774b5aeb303185dc75bbd1edccc898e5b19`.
- Riscontro: Il replay nuovo preserva il riquadro dell’evento. Metadati di edizione/archivio e casi con più sedi richiedono ancora il ponte di salvataggio.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/editorial.json`.

### sagretorino.it--3ad295df7ef3

`/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 6 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.sagretorino.it/ — read, lettura 2026-10-19T22:38:45.972288+00:00; SHA-256 `00458f660ccc1ace94853a9d1713069c9d8095796b50246ecd9476cf1070c4a0`.
- Riscontro: Il sistema deve leggere il programma collegato e una data con anno prima di generare edizioni.
- Riscontro: Contenuto su passeggiate/biciclettate richiede verifica della tipologia mercato, senza cancellare ID storici.
- Riscontro: Non unire la ricomparsa di un paese al vecchio evento dello stesso paese.
- Riscontro: Nessuno dei sei specifici eventi del catalogo è riconfermato: alcuni Comuni ricompaiono per eventi diversi.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### firenzetoday.it--3aaf8d291320

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.firenzetoday.it/eventi/emporium-piazza-savonarola-firenze-24-gennaio-2026.html — read, lettura 2026-10-19T22:38:46.875217+00:00; SHA-256 `e93a25ebe6705dd7baf0690a143211371ee6e0f3c3af5dda666296caefcbd5c4`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### milanopocket.it--549124b1743e

`/sagre-lombardia/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 5 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.milanopocket.it/sagre-lombardia/ — read, lettura 2026-10-19T22:38:48.193709+00:00; SHA-256 `ee8f5093a1f5a8711fd30fdc6138c5f6122cf2e52adfa7a066ce2c24e1990b94`.
- Riscontro: Tutte le cinque schede hanno provincia MI, anche città denominate Varese/Padenghe/Solbiate: anomalia geografica da validare con repertorio di Comuni, non col dominio del sito.
- Riscontro: Stesso marchio in città diversa è prova del rischio di join solo per titolo, non autorizza un aggiornamento degli eventi salvati.
- Riscontro: Le date multiple del listato richiedono parser di insiemi, non min/max.
- Riscontro: I cinque eventi del catalogo non sono individuati nella pagina corrente. Il marchio Mercatino da Forte dei Marmi compare a Crema, diverso da Padenghe/Rozzano salvati.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### sagreumbre.it--f52d57ff5da2

`/fiere-mercati/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 5 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.sagreumbre.it/fiere-mercati/ — read, lettura 2026-10-19T22:38:48.253717+00:00; SHA-256 `a6857870a3bbf9836a015f9bbeb47c9e44aa61e105120fe344103518803268cf`.
- Riscontro: Indirizzi e orari presenti in altre card non possono riempire i cinque eventi che condividevano il vecchio URL di indice.
- Riscontro: Microdata e DOM offrono discovery, ma nessun Event JSON-LD è presente.
- Riscontro: Cinque target salvati non individuati nelle tre card correnti; il listato attuale riguarda Alviano, Valtopina e Terni.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### comune.roma.it--d39d0b6041d2

`/web-resources/cms/documents/MunXIII_DD647_2026_Graduatorie_mercati.pdf` — primary_catalog.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 4 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.comune.roma.it/web-resources/cms/documents/MunXIII_DD647_2026_Graduatorie_mercati.pdf — read, lettura 2026-10-19T22:36:59.804441+00:00; SHA-256 `8d81efa0270003107f96e1daf261e9d6342c54d2f3c7187165668a4197f56a79`.
- Riscontro: Operational source is a fixed reviewed manifest, not a general recurring reader for new versions of the PDF/KML. Row descriptions/stall counts and hours in KML are richer than the curated identity subset but need chronology and site reconciliation.
- Riscontro: I difetti misurati nel primo audit conservano il loro ambito storico; il report separato dopo il fix documenta soltanto le correzioni orari Firenze/Bologna e le verifiche di compatibilità. Gli altri TODO restano aperti.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### feelflorence.it--01efd5fd9033

`/it/punti-di-interesse/{slug}` — primary_catalog.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 4 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 4 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.feelflorence.it/it/punti-di-interesse/mercato-di-san-lorenzo-o-mercato-centrale — read, lettura 2026-10-19T22:36:56.306730+00:00; SHA-256 `fe828ba55b6be915e910786f332b3fc77c6f6597c4b5981f3d83ec51dfe528be`.
- Campione: https://www.feelflorence.it/it/punti-di-interesse/mercato-delle-pulci — read, lettura 2026-10-19T22:36:57.856917+00:00; SHA-256 `bd4c0199b7028c51969df9e22f22e74ef71a758b3a1fcb4e26a25fd19f7a03da`.
- Campione: https://www.feelflorence.it/it/punti-di-interesse/mercato-del-porcellino — read, lettura 2026-10-19T22:36:58.337813+00:00; SHA-256 `7e2001db586a6c3add35ba9798af799df66ad6efba61c4f1a2b69c875a9d049d`.
- Campione: https://www.feelflorence.it/it/punti-di-interesse/mercatino-di-san-lorenzo — read, lettura 2026-10-19T22:36:58.552362+00:00; SHA-256 `197929eb275331105b3b48fc832c253aaf8b1197200070646af5b12d4a912630`.
- Riscontro: Mercatino di San Lorenzo source hours are 1885 characters after strip; adapter keeps 180, current catalog 160 after final strip. Fifteen of the seventeen explicit date tokens disappear. This is one record with lost constraints, not fifteen missing confirmed 2026 events.
- Riscontro: Shapefile DBF truncates three descriptions and one hours field to fixed widths, changes field names to descrizion/feelfloren, and contains character substitutions. GeoJSON/CSV carry the fuller data.
- Riscontro: Three source operator links are absent from mapped/public source-link fields.
- Riscontro: I difetti misurati nel primo audit conservano il loro ambito storico; il report separato dopo il fix documenta soltanto le correzioni orari Firenze/Bologna e le verifiche di compatibilità. Gli altri TODO restano aperti.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### modenatoday.it--d4f51ae43a3f

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.modenatoday.it/eventi/Mercato-invernale-parco-novi-sad-Modena-15-febbraio-3026.html — read, lettura 2026-10-19T22:38:49.212072+00:00; SHA-256 `e70ce1773890d9fec540c8aba66302b235761257ae94008a4000918b6860cfa2`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### umbriaeventi.com--a21a189c200c

`/{slug}-{id}.htm` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.umbriaeventi.com/anticamente-orvieto-mostra-mercato-collezionismo-antiquariato-15811.htm — read, lettura 2026-10-19T22:38:50.817216+00:00; SHA-256 `18ffb174195cfaf7b9248074a27b4789a0d848baa162602b24fc1d41dabc142d`.
- Riscontro: Gap dimostrati di sede, orario parziale e prossime edizioni; titolo contaminato da concatenazione di altri blocchi.
- Riscontro: Estrarre solo JSON-LD perderebbe le prossime due date. Unire calendario, h1 e blocco descrittivo dello stesso evento con provenienza per campo.
- Riscontro: I link di eventi gemelli Foligno/Todi/Perugia non sono sedi alternative di Orvieto.
- Riscontro: Quattro URL nel formato; il campione corrisponde all’Anticamente di Orvieto. Le altre città citate come eventi gemelli non appartengono alla stessa sede.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### umbriaeventi.com--f193ae86be90

`/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 4 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.umbriaeventi.com/ — read, lettura 2026-10-19T22:38:53.322438+00:00; SHA-256 `8dd8225b6efd1794c6aa865b60f367d1ff6ed8c6ff8d9735c05439943ee92e9c`.
- Riscontro: Gap dimostrato di discovery/date per i due Anticamente del catalogo, con collegamento dettagliato disponibile.
- Riscontro: Stessa marca e date diverse richiedono join composto; la geografia nel catalogo è inclusa nel campo citta come testo (PG), provincia separata vuota.
- Riscontro: La lettura di un estratto tagliato non deve produrre ricorrenze parziali.
- Riscontro: Anticamente Foligno e Ponte Rio fra i quattro target sono presenti, con date proprie. Mercato delle Gaite e Calzolarissimo non individuati nel campione.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### enjoysicilia.it--c47fcfe933c0

`/it/events/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 3 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.enjoysicilia.it/it/events/ — read, lettura 2026-10-19T22:38:51.029232+00:00; SHA-256 `1c43edfbadfcd67ed84ff0c641e4ef1b775e64e23b8369038c5472006476b621`.
- Riscontro: Fonte adatta a scoprire dettagli e conservare precisione delle date; mancanza dalla vista corrente non indica chiusura del mercato.
- Riscontro: Nessun Event JSON-LD osservato nel campione: non basta affidarsi allo schema strutturato.
- Riscontro: Tre eventi del catalogo (Little Sicily, Catarratto, Aspettando EnoEtna) non individuati nelle card del campione corrente.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### riminitoday.it--3fcce20b0a85

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.riminitoday.it/eventi/piazzetta-delle-idee-chi-cerca-trova-artigianato-creativita-tesori-riccione-paese.html — read, lettura 2026-10-19T22:38:51.124835+00:00; SHA-256 `8cdd913874f41dbc7f9f48958b54326384be8615e11eb659a2180bc7417dbcdb`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Riscontro: JSON-LD privo di endDate mentre il riquadro Quando pubblica l’intervallo completo.
- Riscontro: La pagina contiene due mercati diversi: venerdì mattina e seconda domenica (esclusi luglio/agosto), sedi parzialmente sovrapposte; l’intervallo generale non indica aperture quotidiane.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### romatoday.it--773e7b132541

`/eventi/tipo/{filtri}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 3 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.romatoday.it/eventi/tipo/fiere~mercatini~sagre/ — read, lettura 2026-10-19T22:38:41.219322+00:00; SHA-256 `e6704200a7d0df15185714c6b323fecf55855896cfb9905e615c41ac98c32b8c`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### sagrefvg.it--bb0f79aae507

`/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [ ] Fonte letta: HTML acquisito e contenuto esaminato, ma destinazione HTTP /sagre/ e canonical HTML /sagris/ individuano due formati diversi. La transizione e la copertura del formato originale restano da risolvere.
- [ ] Campi letti: HTML acquisito e contenuto esaminato, ma destinazione HTTP /sagre/ e canonical HTML /sagris/ individuano due formati diversi. La transizione e la copertura del formato originale restano da risolvere.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 3 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://sagrefvg.it/ — read, lettura 2026-10-19T22:38:53.462727+00:00; SHA-256 `029fc02aa621028403faeae85c52e1d90c2fd57ea9583db3b9bc88d60f14a351`.
- Riscontro: Campi ricchi esistono ma appartengono ad altre schede. Occorre join per URL/Comune/luogo e controllo programma/schema.
- Riscontro: Rimuovere indiscriminatamente gli header distruggerebbe titolo, periodo e sede delle card: servono confini semantici del template.
- Riscontro: Borgo Pinzano, Magnalonga Savorgnano e I Cjarsons Sutrio non individuati fra gli otto eventi correnti; la homepage ha redirect HTTP 301 a /sagre/.
- Riscontro: HTML acquisito e contenuto esaminato, ma destinazione HTTP /sagre/ e canonical HTML /sagris/ individuano due formati diversi. La transizione e la copertura del formato originale restano da risolvere.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### sagretoscane.com--7e915f1a79a5

`/fiere-mercati/si/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 3 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.sagretoscane.com/fiere-mercati/si/ — read, lettura 2026-10-19T22:38:54.322708+00:00; SHA-256 `1447eb9ef4457606d003511ab0ffb9a8021b8e169b518be868ef98fec6552fb9`.
- Riscontro: Il campione dimostra un rischio concreto di falso join per nome: 51 date previste delle tre schede non possono ricevere prova dal mercato di Buonconvento.
- Riscontro: I campi ricchi della card di Chiusi non vanno ereditati dalla card vicina.
- Riscontro: Il nome Angolo del Collezionista compare a Buonconvento l’8 dicembre 2026, mentre le tre schede salvate sono di Gaiole, San Gimignano e Siena, tutte con cadenza domenicale.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### suedtirol.info--826da4efb87f

`/it/esperienze/eventi` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 3 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.suedtirol.info/it/esperienze/eventi — read, lettura 2026-10-19T22:38:54.557674+00:00; SHA-256 `518f16ceae6b514e2e7872c0df7f3e883507be57e8e7f25889bd8cf6692f02ef`.
- Riscontro: Un reader solo JSON-LD vedrebbe ItemList vuoto malgrado trenta card nel DOM: gap concreto di copertura del formato.
- Riscontro: Campione utile per discovery con link dettaglio; non è prova di completezza di tutta la base dati dinamica.
- Riscontro: La normalizzazione geografica deve tenere separati Comune, area turistica e ripetizioni di UI.
- Riscontro: Nessuno dei tre target Merano via Galilei/Naturno/Terlano individuato nelle card o nelle relative stringhe del campione.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### veneziatoday.it--98a866420834

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.veneziatoday.it/eventi/mercatino-mirano-15-febbraio-2026.html — read, lettura 2026-10-19T22:38:55.547254+00:00; SHA-256 `2ac1965b2aa7a5ff80ca5538b3af2ee649e34cc53f840dafb4112074fcd21ddb`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### vicenzatoday.it--7f29dd72d035

`/eventi/tipo/{filtri}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 3 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.vicenzatoday.it/eventi/tipo/fiere~sagre~mercatini/ — read, lettura 2026-10-19T22:38:56.822924+00:00; SHA-256 `ffc2fb44784662d24ea75c25d04440b166869e4798e20470a8387648fd675d55`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### assosagre.it--4377f96ccd50

`/calendario_sagre.php?id_provincia={value}&id_sagra={value}` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [ ] Fonte letta: Acquisizione non riuscita o formato osservato solo indirettamente; non conteggiato come lettura verificata.
- [ ] Campi letti: Il contenuto non è disponibile per un confronto attendibile dei campi.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [ ] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.assosagre.it/calendario_sagre.php?id_sagra=74&id_provincia=105 — http_error_or_external_redirect, lettura 2026-10-19T22:38:58.171119+00:00; SHA-256 `—`.
- Riscontro: Nessuna conclusione sulla presenza di campi nella pagina. Via Mameli e apertura 19:00 già salvate non vengono riconfermate da un errore HTTP.
- Riscontro: Due URL/schede nel formato; campione non letto. La città PD nella scheda è un dato del catalogo, non un valore confermato dalla fonte.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### baritoday.it--0c17b5073dc8

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.baritoday.it/eventi/fiera-fischietto-rutigliano-24-25-gennaio-2026.html — read, lettura 2026-10-19T22:38:59.507084+00:00; SHA-256 `64cf384b662d8c6d4c06b728890bd7ed030107f19055fc5ed13eb2fcc98c57bf`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Riscontro: JSON-LD privo di endDate mentre il riquadro Quando pubblica l’intervallo completo.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### bolognatoday.it--98c9652acb3c

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.bolognatoday.it/eventi/da-berlino-a-bologna-the-vinyl-market-berlin-arriva-a-eufonica-lucretio-e-idriss-d-13675563.html — read, lettura 2026-10-19T22:39:00.355936+00:00; SHA-256 `0e828b281b3d6dd5623564d2a8ce90ccaebb391bbe57b0a0d1d772578a5bf59f`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Riscontro: JSON-LD privo di endDate mentre il riquadro Quando pubblica l’intervallo completo.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### bresciatoday.it--323a7ea664ee

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.bresciatoday.it/eventi/sagre/chiari-mercatini-san-faustino-2026.html — read, lettura 2026-10-19T22:39:00.489278+00:00; SHA-256 `a94b3ad723f21bb5008e3a87572438fced509adf91744f807a19ef69fd91b2fe`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### brindisireport.it--5b0c85ac1d51

`/tag/{tag}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.brindisireport.it/tag/sagre/ — read, lettura 2026-10-19T22:39:00.883203+00:00; SHA-256 `927fbf84a6a561ae82eda20e58d311c574315672c000e3d9e1b04ef1cb6693a4`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### cittadellaspezia.com--daef88baba75

`/tag/sagre/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.cittadellaspezia.com/tag/sagre/ — read, lettura 2026-10-19T22:39:02.617261+00:00; SHA-256 `e450daf46205004384be4309d5cafe842ccceb81ae9a883e267d6c1593536eeb`.
- Riscontro: Il listato può scoprire URL dettagliati; il solo URL di tag non è prova aggiornata per tutte le schede importate in passato.
- Riscontro: L’assenza dalla prima pagina non dimostra cessazione o annullamento.
- Riscontro: I due eventi salvati per questo URL (Cantamaggio e Madonna dell’Olmo) non sono stati individuati nelle schede del campione corrente.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### comune.corciano.pg.it--1d7a32ba013d

`/area_letturaDocumento/29645/pagsistema.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://comune.corciano.pg.it/area_letturaDocumento/29645/pagsistema.html — read, lettura 2026-10-19T22:36:58.104066+00:00; SHA-256 `218495ec0bcd73c1a3a5d199a65945a4abbd8b8532c4379158f93557b751e925`.
- Riscontro: I difetti misurati nel primo audit conservano il loro ambito storico; il report separato dopo il fix documenta soltanto le correzioni orari Firenze/Bologna e le verifiche di compatibilità. Gli altri TODO restano aperti.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### eventiintoscana.it--641b8123d9f9

`/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventiintoscana.it — read, lettura 2026-10-19T22:39:04.175631+00:00; SHA-256 `82a1b7486601597e050fb365a5b54dccc32e1fcfbc7c56ba43282a178079144c`.
- Riscontro: Serve discovery di URL evento e scoping; indirizzi e parole di frequenza nel contatto editoriale sono falsi candidati.
- Riscontro: Non considerare l’assenza dei target dalla homepage prova di cessazione.
- Riscontro: Fiera Antiquaria Arezzo e Mercatini San Quirico non individuati nei contenuti del campione corrente.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### ferrarainfo.com--1dfcae70a0aa

`/it/eventi/eventi` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [ ] Campi letti: HTML e stato serializzato letti, ma il contenuto dinamico dei risultati evento resta irrisolto.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [ ] Catalogo confrontato: Scheda catalogo esaminata; il confronto dei campi evento richiede il contenuto dinamico non ancora letto.
- Campione: https://www.ferrarainfo.com/it/eventi/eventi — read, lettura 2026-10-19T22:39:05.314682+00:00; SHA-256 `63862bbfec16bc07dda302ca4d1d7a14818c9f5a3ed57fa9c1cd31b03b8e00cc`.
- Riscontro: Il HTML di circa 690 kB contiene soprattutto stato applicativo e traduzioni, mentre il corpo dice Nessun risultato.
- Riscontro: La lettura della pagina è riuscita, ma la raccolta degli eventi dinamici non è risolta: non segnare il calendario verificato né cancellare schede.
- Riscontro: Le proiezioni già salvate per i due mercati non ricevono nuova prova da una pagina senza risultati.
- Riscontro: Agrimercato Grisù e mercato contadino del venerdì non compaiono come testo nel HTML o nello stato serializzato del campione.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### forlitoday.it--ebf7741cbe52

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.forlitoday.it/eventi/mercato-di-campagna-amica-coldiretti-programma-iniziative-febbraio-2026.html — read, lettura 2026-10-19T22:39:05.322310+00:00; SHA-256 `962516396015a8f7cf9728b2721958b692f7765a861df15ebe8ed9858fee02fa`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Riscontro: JSON-LD privo di endDate mentre il riquadro Quando pubblica l’intervallo completo.
- Riscontro: Riquadro fino al 27/02/2026 e testo con appuntamento sabato 28: incongruenza interna da conservare; venerdì/sabato e programma non equivalgono a tutte le date del periodo.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### frosinonetoday.it--719a6eee7966

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.frosinonetoday.it/eventi/ceccano-mercatino-degli-artigiani-del-borgo-odv.html — read, lettura 2026-10-19T22:39:06.155416+00:00; SHA-256 `b79f02c872b20620cbad8352a02253f8a479bac196da6b50ed82981a4022e875`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### genovatoday.it--023670032cbe

`/eventi/tipo/{filtri}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.genovatoday.it/eventi/tipo/fiere~manifestazioni~mercatini~sagre/ — read, lettura 2026-10-19T22:38:45.773840+00:00; SHA-256 `a25f30089010590a1605e4b51ac5d14c0c4dd364b338ddc5b5e7d0876d6974fb`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### lazioinfesta.com--9432160459d4

`/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.lazioinfesta.com/ — read, lettura 2026-10-19T22:39:07.808020+00:00; SHA-256 `232a033665a64319dd121f7dd1873a9a6eaf065ff93bd12da71ecc6ba1fbe8b6`.
- Riscontro: Card utili alla discovery di schede; non trasformare un intervallo lungo in presenza quotidiana o data corrente del target.
- Riscontro: Nessuna riconferma possibile per i due eventi assenti dalla vista.
- Riscontro: Bonfire Market Roma e I Sapori del Parco Sabaudia non individuati nelle card correnti.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### monzatoday.it--a48c40adcb3f

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.monzatoday.it/eventi/monza-mercatino-francese_febbraio-2026.html — read, lettura 2026-10-19T22:39:07.891197+00:00; SHA-256 `fd2ee640f40769453ffa5778cf1c9f41a0355420e676cf20215454e14ea90691`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Riscontro: JSON-LD privo di endDate mentre il riquadro Quando pubblica l’intervallo completo.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### novaratoday.it--fd80b2faea81

`/eventi/tipo/{filtri}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.novaratoday.it/eventi/tipo/fiere~sagre~mercatini/ — read, lettura 2026-10-19T22:39:08.173303+00:00; SHA-256 `6e704990e12fa870a29c9ecd6ba6826f2bf453555fad74769186d5641355e610`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### palermotoday.it--5b9cabc75906

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.palermotoday.it/eventi/artgarden-14-15-febbraio-2026-vivai-gitto.html — read, lettura 2026-10-19T22:39:10.006870+00:00; SHA-256 `6124fdfa05fdf721ae81a1e6dda59a1e5bea2e9fc1477ffbed695d47dfd5af43`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Riscontro: JSON-LD privo di endDate mentre il riquadro Quando pubblica l’intervallo completo.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### paradisola.it--b32e4258186f

`/eventi-sardegna` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.paradisola.it/eventi-sardegna — read, lettura 2026-10-19T22:39:10.462598+00:00; SHA-256 `cc2b047bb0f7614511e4b63ff481e29bf30d8a75a339915c7c21edf68058890b`.
- Riscontro: Necessaria discovery verso programmi e dettagli, mantenendo precisione dell’anno e identità.
- Riscontro: Nessun Event JSON-LD osservato nel campione.
- Riscontro: Sulcis Iglesiente Espone Carbonia e festival birra Serramanna non individuati nel listato corrente.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### pugliainfesta.it--8852e0d42557

`/evento/{id}/{slug}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.pugliainfesta.it/evento/18483/la-tua-pausa-gourmet-nella-citt-bianca.html — read, lettura 2026-10-19T22:39:10.493110+00:00; SHA-256 `29afa5575adc60a2938465e16bd14599a49eda15699c4a36ce8bb928689e15ab`.
- Riscontro: Fonte offre un indirizzo che il catalogo non salva, ma prima servono controllo di identità geografica ed eleggibilità come mercato.
- Riscontro: Lettori di pagine evento non devono importare automaticamente ristorazione permanente come mercato, né trasformare gli estremi della promozione in orari.
- Riscontro: Due URL nel formato; il campione è una promozione pranzo/cena di ristorante. Intestazione Brindisi, descrizione Ostuni (BR): conflitto di Comune.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### ravennatoday.it--b46159a30433

`/eventi/tipo/{filtri}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.ravennatoday.it/eventi/tipo/fiere~sagre~mercatini/ — read, lettura 2026-10-19T22:39:12.886691+00:00; SHA-256 `5061504a127ab7fbd30d65b953db061a134f2e621eded434426a807aebe46489`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### sagreinromagna.it--073cd6052d05

`/sagre_per_provincia/1/ravenna` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.sagreinromagna.it/sagre_per_provincia/1/ravenna — read, lettura 2026-10-19T22:39:13.778762+00:00; SHA-256 `f9c0b4bfd977b44e34e31933d976faef5c9fb4ec10b4fb075e4cff5d713bf516`.
- Riscontro: Date storiche presenti e campo date vuoto: gap di conservazione dell’edizione, non prova di nuove date future.
- Riscontro: Le card e la tabella duplicano gli stessi eventi e vanno deduplicate per identità/edizione.
- Riscontro: L’indirizzo mancante non può diventare una via inventata a partire dal solo Comune/frazione.
- Riscontro: Entrambi i target del catalogo sono nel listato: Mercatini di primavera e Portobello Beach, a Marina di Ravenna. Solo edizioni passate osservate per loro.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### terredipisa.it--6b239e3c095e

`/events/categories/sagra-fiere-mercati/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.terredipisa.it/events/categories/sagra-fiere-mercati/ — read, lettura 2026-10-19T22:39:13.886516+00:00; SHA-256 `7ef68a51a286cadd0da2146207b7ea251b6c5112802901e8ed372bc95c607b03`.
- Riscontro: Link dettagliato disponibile per il mercato di San Miniato, mentre il catalogo conserva il solo indice.
- Riscontro: Il catalogo salva solo 6 dicembre prevista; non è corretto aggiungere ogni data del range senza leggere il programma dettagliato.
- Riscontro: Il target San Miniato è presente. Il target Vicopisano non è nella prima pagina; non se ne deduce cessazione.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### torinotoday.it--9d13c4c3e50b

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.torinotoday.it/eventi/salone-libro-usato-nichelino-14-22-febbraio.html — read, lettura 2026-10-19T22:39:14.178792+00:00; SHA-256 `dfe4a66fca40b587b6e9323e3529a8833102c9321a356b35b566bcc6a84f3fa1`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Riscontro: JSON-LD privo di endDate mentre il riquadro Quando pubblica l’intervallo completo.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### trevisotoday.it--f2521f69a8c7

`/eventi/tipo/{filtri}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.trevisotoday.it/eventi/tipo/fiere~sagre~mercatini/ — read, lettura 2026-10-19T22:39:16.946924+00:00; SHA-256 `8974fe111a87d3dc254eb31792ac85065d7822fadd975f8b720628d738a36c7b`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### varesenews.it--888bef8902d4

`/category-evento/eventi-sagre-feste/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.varesenews.it/category-evento/eventi-sagre-feste/ — read, lettura 2026-10-19T22:39:17.086801+00:00; SHA-256 `13a5cae821eb636d1a92aebedfd83d406be24b037858cdd5756821e0c2f7b45a`.
- Riscontro: Il lettore deve conservare gli header locali delle card: una pulizia globale degli header cancella tutti i campi utili.
- Riscontro: La pagina contiene date e luoghi ma non dei due target; richiede discovery e controlli di plausibilità del periodo.
- Riscontro: Non correggere da soli l’anno discordante della manifestazione sportiva né importarvi un mercato.
- Riscontro: Fashion Day Lavena Ponte Tresa e Calici Sapori Motori Venegono non individuati nelle card correnti.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### veneziatoday.it--81e9b7eb8036

`/eventi/tipo/{filtri}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 2 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.veneziatoday.it/eventi/tipo/fiere~sagre~mercatini/ — read, lettura 2026-10-19T22:38:57.828911+00:00; SHA-256 `561c0c8736a0d63a5d36b92a45bcaa7aa8f122f0fdf0da43c6bc1f1174a1357e`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### arezzonotizie.it--9521d1fd66d9

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.arezzonotizie.it/eventi/mercato-pulci-2026.html — read, lettura 2026-10-19T22:39:17.384232+00:00; SHA-256 `3a9ccb5cd82d5f69a710eff0484970f3e6e91b32383bda2111962f43c49e2a3e`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Riscontro: JSON-LD privo di endDate mentre il riquadro Quando pubblica l’intervallo completo.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### bolognatoday.it--e0f6de959b8b

`/eventi/tipo/{filtri}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.bolognatoday.it/eventi/tipo/fiere~sagre~mercatini/ — read, lettura 2026-10-19T22:39:02.684050+00:00; SHA-256 `6454422185ef2bddcc7adb5cb741b71741e8f6d27865213e457643978d2c2f8f`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### bresciatoday.it--6206d2d85129

`/eventi/tipo/{filtri}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.bresciatoday.it/eventi/tipo/fiere~sagre~mercatini/ — read, lettura 2026-10-19T22:39:02.492326+00:00; SHA-256 `73fe1f03e9d96e9dfbc40505a34e103c9e2f0a5ba248163b796f284a3584b2ae`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### cagliaritoday.it--e1ef02204e41

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.cagliaritoday.it/eventi/Hermaearket-pirri-marzo-handmade-artigianato.html — read, lettura 2026-10-19T22:39:17.624767+00:00; SHA-256 `136396e3ec25a7838d716ca5fa0e7e84ccc0fec1b01219915904124d955bce8d`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Riscontro: JSON-LD privo di endDate mentre il riquadro Quando pubblica l’intervallo completo.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### casertanews.it--2214b2178409

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.casertanews.it/eventi/fiera-vintage-polo-a1-expo-14-15-febbraio.html — read, lettura 2026-10-19T22:39:19.112893+00:00; SHA-256 `df41fdd3ee1f5d428c86cbd5821bf435e93516040007f3907399d163de468055`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Riscontro: JSON-LD privo di endDate mentre il riquadro Quando pubblica l’intervallo completo.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### cataniatoday.it--31ed67739fab

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.cataniatoday.it/eventi/mercatino-fera-bio-catania-febbraio-2026.html — read, lettura 2026-10-19T22:39:20.031232+00:00; SHA-256 `2051b920cbdf36dd1f86cae04b88ee43d0c985d8e30fac35eaa23850dbcfff39`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### cesenatoday.it--c9fd22db3421

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.cesenatoday.it/eventi/festa-del-maiale-quando-montiano-25-gennaio-2026.html — read, lettura 2026-10-19T22:39:20.651994+00:00; SHA-256 `15bc6ff87cd61e6e148c184c6cdc3a6694c8505159ed62eaeb6bfa8b4b4866d1`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### chietitoday.it--2f12ec6202a9

`/attualita/{articolo}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.chietitoday.it/attualita/mercatino-curiosita-centro-chieti-aniac.html — read, lettura 2026-10-19T22:39:21.501434+00:00; SHA-256 `b575bd0e77f5eb9ff4d87239f292f04e3f58031118c83c57f8dd486138eda8d2`.
- Riscontro: Articolo redazionale o elenco di luoghi: la data di pubblicazione non è una data di mercato. Servono blocchi distinti per le sedi.
- Riscontro: Il corpo contiene un elenco esplicito delle edizioni 2026 e sospensioni estive/dicembre; l’indicazione generica terzo/quarto weekend non è una ricorrenza uniforme.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### comune.roma.it--b6b446c7c7b8

`/web/it/bando-concorso.page?contentId={value}` — primary_catalog.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.comune.roma.it/web/it/bando-concorso.page?contentId=BEC1533869 — read, lettura 2026-10-19T22:37:01.765844+00:00; SHA-256 `84364f4ba29e36f5fe65e3952760e183b5005319621bfb268b746a5646ab8636`.
- Campione: https://www.comune.roma.it/web/it/bando-concorso.page?contentId=BEC1343579 — read, lettura 2026-10-19T22:37:00.919757+00:00; SHA-256 `0a1dd174a2f5648c2c1582bf76764e6c8faa20c4b05a29a486c93618287eea35`.
- Riscontro: Risorsa HTML collegata alla fonte comune.roma.it; non aumenta le schede conteggiate.
- Riscontro: No maintained extraction path for future notice revisions. Site plan and underlying notice attachments remain a specific follow-up before deriving an entrance or opening schedule.
- Riscontro: I difetti misurati nel primo audit conservano il loro ambito storico; il report separato dopo il fix documenta soltanto le correzioni orari Firenze/Bologna e le verifiche di compatibilità. Gli altri TODO restano aperti.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### eventi.bergamo.it--849986cf0982

`/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventi.bergamo.it — read, lettura 2026-10-19T22:38:45.040188+00:00; SHA-256 `5c2f12f994539c233abb71574750de967c40583f98e7c3ee15ad07274ca67c03`.
- Riscontro: Estrarre il primo JSON-LD Event della homepage e attribuirlo al target sarebbe un falso collegamento.
- Riscontro: I titoli/orari dentro header locali delle card sono contenuto evento e vanno conservati, separando l’header globale.
- Riscontro: Wine Form Mais a Casnigo, unica scheda catalogo per questo URL, non individuata fra gli eventi del campione.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### eventiesagre.it--3c3a269d898e

`/Eventi_Sagre/{id}_{slug}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Confronto prima/dopo sui medesimi HTML; i nuovi campi non supportati da RawMarket/CleanMarket restano una perdita di salvataggio aperta.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventiesagre.it/Eventi_Sagre/21195398_Ferrara+Food+Festival.html — read, lettura 2026-10-19T22:31:54.326Z; SHA-256 `b458ec6a318b0047c2ac86b4128c2c38f73c70d49f2f53cb03345be296a02688`.
- Riscontro: Il replay nuovo preserva il riquadro dell’evento. Metadati di edizione/archivio e casi con più sedi richiedono ancora il ponte di salvataggio.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/editorial.json`.

### eventiesagre.it--c49b67f8f8bc

`/Eventi_Folklore/{id}_{slug}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Confronto prima/dopo sui medesimi HTML; i nuovi campi non supportati da RawMarket/CleanMarket restano una perdita di salvataggio aperta.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventiesagre.it/Eventi_Folklore/21072795_Profumi+Di+Primavera+a+Collevecchio.html — read, lettura 2026-10-19T22:31:57.906Z; SHA-256 `16f37b8c3c1c23e9c7fb04ed7718f7ed1b968fdab3849ebb23a8e22460ea77b7`.
- Riscontro: Il replay nuovo preserva il riquadro dell’evento. Metadati di edizione/archivio e casi con più sedi richiedono ancora il ponte di salvataggio.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/editorial.json`.

### eventiesagre.it--e5298c4f16d6

`/Eventi_Fiere/{id}_{slug}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [x] Parser confrontato: Confronto prima/dopo sui medesimi HTML; i nuovi campi non supportati da RawMarket/CleanMarket restano una perdita di salvataggio aperta.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventiesagre.it/Eventi_Fiere/21087135_Artigianando.html — read, lettura 2026-10-19T22:32:00.549Z; SHA-256 `5c9158466e70b82b58735a3928a17612a7f9e5333952bc763c913088857c2f0d`.
- Riscontro: Il replay nuovo preserva il riquadro dell’evento. Metadati di edizione/archivio e casi con più sedi richiedono ancora il ponte di salvataggio.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/editorial.json`.

### eventiinsardegna.it--4f6de7c3abb7

`/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.eventiinsardegna.it/ — read, lettura 2026-10-19T22:39:22.403259+00:00; SHA-256 `8a02719d1006cd933a29f17e54818b3b764f8d1df598125ce59dc0311fb53cf1`.
- Riscontro: I placeholder NA non devono contare come completezza dei dati.
- Riscontro: L’Event graph della homepage descrive altre manifestazioni, non prova nuove date del mercato salvato.
- Riscontro: Primavera nel Cuore a Baunei non individuata nel campione corrente.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### ferraratoday.it--096c9d2b9991

`/eventi/tipo/{filtri}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.ferraratoday.it/eventi/tipo/fiere~sagre~mercatini/ — read, lettura 2026-10-19T22:39:22.870183+00:00; SHA-256 `2f1853bfe800dc28a18b5d94415aea749a37e7ffbc96cbe42e02df2d1ea1c89f`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### ferraratoday.it--2f49a574f3cd

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.ferraratoday.it/eventi/markettino-prima-edizione-del-mercato-contemporaneo-atigianato-indipendente-8-febbraio.html — read, lettura 2026-10-19T22:39:25.187354+00:00; SHA-256 `7c4aae15444b323f82aaf74608751fb32538fa8f38c30f4753264cf681e72773`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### firenzetoday.it--4c68a0e41483

`/eventi/tipo/{filtri}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.firenzetoday.it/eventi/tipo/fiere~mercatini~mostre~sagre/ — read, lettura 2026-10-19T22:38:48.669744+00:00; SHA-256 `20ff2a6f0341b9e071990768f5f472138ab7afc8474ddc7210beef4951520a59`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### frosinonetoday.it--13df3249e7e8

`/eventi/tipo/{filtri}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.frosinonetoday.it/eventi/tipo/fiere~sagre~mercatini/ — read, lettura 2026-10-19T22:39:08.366432+00:00; SHA-256 `f6fee7dedf90b9fd0cad861a6f2dd0bbae4e7b489fabea4a78687143bd0b6a3b`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### leccotoday.it--a1f15b11015f

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.leccotoday.it/eventi/mandello-mercatino-2000-libri-fuoriclasse-.html — read, lettura 2026-10-19T22:39:23.450226+00:00; SHA-256 `fdda26a123cb27129d8bb03690f1e0be2561a52c10c3266cbee8d4f550e9d6c5`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### lombardiainfesta.it--aac72178e0f0

`/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.lombardiainfesta.it/ — read, lettura 2026-10-19T22:39:24.266731+00:00; SHA-256 `1c07b35a03ff985b002f2143a41b6df5735967e2e2dc8ce4e8c2aaa7af02ce28`.
- Riscontro: Il formato è una sorgente di link, non una scheda stabile di Crema Wine Festival.
- Riscontro: Nessun Event JSON-LD osservato; richiede contratto DOM e dettaglio.
- Riscontro: Crema Wine Festival non individuato nelle card del campione.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### milanotoday.it--800bdea3a7e9

`/eventi/tipo/{filtri}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.milanotoday.it/eventi/tipo/fiere~sagre~mercatini/ — read, lettura 2026-10-19T22:39:24.740426+00:00; SHA-256 `3a7619c5a42797175c71298f7a8b2b802dc68c833421542d996e54bc96d45822`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### modenatoday.it--6d93abfa3a9b

`/eventi/tipo/{filtri}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.modenatoday.it/eventi/tipo/fiere~sagre~mercatini/ — read, lettura 2026-10-19T22:38:51.348652+00:00; SHA-256 `270f6bcd6ab3aedaf885e2452e850c2035b152bbca53697a134e58d112ea1f9f`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### napolidavivere.it--679a0a2b46d4

`/category/eventi/sagre-e-feste/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.napolidavivere.it/category/eventi/sagre-e-feste/ — read, lettura 2026-10-19T22:39:26.215739+00:00; SHA-256 `1aa6574990417885f00b4b03a7729de2bc941491accc38d5d5182acd2546ca73`.
- Riscontro: Serve lettore di archivio più URL dettaglio, con ruoli separati per publication time/event time.
- Riscontro: Provincia NA salvata per Santa Maria di Castellabate richiede controllo geografico indipendente; il nome del portale non è una provincia di default.
- Riscontro: Pescato di Paranza a Santa Maria di Castellabate non individuato nel campione corrente.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### novaratoday.it--12e887ae9cfd

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.novaratoday.it/eventi/sagra-primavera-cameri-2026.html — read, lettura 2026-10-19T22:39:10.810720+00:00; SHA-256 `cdd056d78e6f78df8f4a9b22e23eae1cc5c69b7a0df4bc404de5c2d0ff73cddc`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Riscontro: JSON-LD privo di endDate mentre il riquadro Quando pubblica l’intervallo completo.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### padovatoday.it--a15e8e68ca15

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [ ] Fonte letta: Acquisizione non riuscita o formato osservato solo indirettamente; non conteggiato come lettura verificata.
- [ ] Campi letti: Il contenuto non è disponibile per un confronto attendibile dei campi.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [ ] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.padovatoday.it/eventi/festa-baccala-pesce-taggi-sopra-30-gennaio-1-febbraio-2026.html — http_error_or_external_redirect, lettura 2026-10-19T22:39:26.398913+00:00; SHA-256 `—`.
- Riscontro: Lettura non riuscita: HTTP 503. I campi della fonte non sono stati verificati.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### palermotoday.it--7be3a486df34

`/eventi/tipo/{filtri}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.palermotoday.it/eventi/tipo/fiere~sagre~mercatini/ — read, lettura 2026-10-19T22:39:12.372126+00:00; SHA-256 `529abd7f59faad0bc82a7d21111558c77e44c65bdd63d302dec0700b34655123`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### parmatoday.it--4d0ed834ab18

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.parmatoday.it/eventi/librokilo-parma-1-febbraio.html — read, lettura 2026-10-19T22:39:27.878884+00:00; SHA-256 `1aa91a788bf9a3f5f57de02291d1a249df912875ba85389286e95ef4d9deab81`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### ravennatoday.it--d19463631447

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.ravennatoday.it/eventi/festa-della-patrona-sant-agata-sul-santerno-iniziative-2026.html — read, lettura 2026-10-19T22:39:15.386341+00:00; SHA-256 `73a6de7a9e7cbadf621e313e2806b6249226ec2e7221ba1098ac65d283ee2ab8`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Riscontro: JSON-LD privo di endDate mentre il riquadro Quando pubblica l’intervallo completo.
- Riscontro: Programma di festa: il mercatino è domenica 1 febbraio, con recupero condizionato al maltempo il 7; altri orari/date sono spettacoli, messe o pranzi.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### riminitoday.it--8bfbd004bf42

`/eventi/tipo/{filtri}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.riminitoday.it/eventi/tipo/fiere~sagre~mercatini/ — read, lettura 2026-10-19T22:38:53.326469+00:00; SHA-256 `55cc590d60866c70609fbfed90ccca8c72608a55637652597e8745796def1d40`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### romapop.it--55f380b91494

`/eventi/roma/sagre-fiere-mercatini/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.romapop.it/eventi/roma/sagre-fiere-mercatini/ — read, lettura 2026-10-19T22:39:27.916797+00:00; SHA-256 `c0e3ce1cb1c5c47784e20da2718aad908679e87e09f96ac6ec6c71c071fdaad8`.
- Riscontro: Il redirect effettivamente osservato cambia tipo semantico da presunto percorso evento a articolo di raccolta.
- Riscontro: Il contenuto può offrire nuova discovery/corroborazione per altri eventi, solo con identità e data proprie; non va riversato nel target assente.
- Riscontro: Fuori Mercato Roma non individuato nel campione. Bonfire Market compare in un’altra voce, ma è diverso dal target di questo URL.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### sagrefvg.it--6113121f4eaf

`/sagris/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://sagrefvg.it/sagris/ — read, lettura 2026-10-19T22:38:56.675781+00:00; SHA-256 `f151040b91dbc5de50ce37203b0c3cb184b0542ccd5814c52c22ed78d2f83d75`.
- Riscontro: Campi ricchi esistono ma appartengono ad altre schede. Occorre join per URL/Comune/luogo e controllo programma/schema.
- Riscontro: Rimuovere indiscriminatamente gli header distruggerebbe titolo, periodo e sede delle card: servono confini semantici del template.
- Riscontro: Festa dello Sport a Treppo Grande non individuata fra gli otto eventi correnti.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### salernotoday.it--6f80ccd14ebc

`/eventi/tipo/{filtri}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.salernotoday.it/eventi/tipo/fiere~sagre~mercatini/ — read, lettura 2026-10-19T22:39:28.067125+00:00; SHA-256 `4d3c29ec0dbb71ce02d3d25178ef9cddebb44f14f3ae7fb8ef6a533d14c6687b`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### trentino.com--f4ac442f344e

`/it/calendario/dettagli/{slug}/#{edizione}` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [ ] Fonte letta: Acquisizione non riuscita o formato osservato solo indirettamente; non conteggiato come lettura verificata.
- [ ] Campi letti: Il contenuto non è disponibile per un confronto attendibile dei campi.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [ ] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://trentino.com/it/calendario/dettagli/mercato-contadino-trento---pdante/#2026-02-14 — http_error_or_external_redirect, lettura 2026-10-19T22:38:39.729834+00:00; SHA-256 `—`.
- Riscontro: Non classificare un errore HTTP come fonte controllata o vuota; nessun nuovo timestamp di prova dei mercati.
- Riscontro: Conservare distinzione tra URL pagina e identificatore di edizione/fragment, senza assumere calendario attuale.
- Riscontro: Una scheda Trento ha Comune TN, dati mancanti e frammento URL con vecchia edizione 2026-02-14; risposta 503 non dimostra il contenuto della pagina.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### trevisotoday.it--d14b81554c11

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.trevisotoday.it/eventi/mostra-mercato-disco-silea-2026.html — read, lettura 2026-10-19T22:39:19.365615+00:00; SHA-256 `22f4b40bfffb9337c33492e5bcf23c211ca06c23a9b1ac7e4c6b4437f0ebb5bb`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Riscontro: JSON-LD privo di endDate mentre il riquadro Quando pubblica l’intervallo completo.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### vicenzatoday.it--711d824754df

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.vicenzatoday.it/eventi/art-ciocc-il-tour-dei-cioccolatieri-ad-asiago.html — read, lettura 2026-10-19T22:38:59.220376+00:00; SHA-256 `cce9d36cabd96af3007bd487edd169e20b94fcb98e8b3b0b0a0dd5e11b5883d5`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Riscontro: JSON-LD privo di endDate mentre il riquadro Quando pubblica l’intervallo completo.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### viterbotoday.it--51968ac255a6

`/eventi/{percorso-evento}.html` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.viterbotoday.it/eventi/fiere/mercatino-dell-antico-viterbo-15-febbraio-2026.html — read, lettura 2026-10-19T22:39:28.136976+00:00; SHA-256 `b2d06e47d3f02ad8cb6395a1ed85fd6d1ad239cfbac4087103659781b93558cb`.
- Riscontro: Date dell’edizione e data editoriale restano distinte; le edizioni passate non provano appuntamenti futuri.
- Riscontro: Gli orari del programma nel corpo possono riguardare concerti o attività: non attribuirli automaticamente all’intero mercato.
- Riscontro: Confronto per URL primario: prima di scrivere servono identità della scheda, Comune e sede compatibili; nessun dato modificato.
- Riscontro: Il telefono Organization nel JSON-LD è del giornale; Event.url può essere il sito dell’organizzatore.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### viterbotoday.it--c0d9902be5e7

`/eventi/tipo/{filtri}/` — primary_catalog.

Ultimo check-in: 2026-10-19T23:28:56.354672+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://www.viterbotoday.it/eventi/tipo/fiere~sagre~mercatini/ — read, lettura 2026-10-19T22:39:30.878313+00:00; SHA-256 `cd129009fb5649e866e14daeeef597bfdd05aa7ab58d3e36b6e8b8a6bb5bd9a1`.
- Riscontro: Il contenuto attuale di un elenco cambia: la lettura dell’indice non verifica la singola vecchia scheda salvata.
- Riscontro: Date, luoghi e orari devono essere collegati all’URL del singolo evento; header, sidebar e altri eventi non sono prove.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/citynews.json`.

### wwwservizi.regione.emilia-romagna.itnote.asp--08f6dd05bcee

`/?anno={value}&cod_co={value}&dt_dataa={value}&dt_datada={value}&progr_fiera={value}&r1={value}&r2={value}&strr_provincia={value}&strr_sede={value}&strs_keywords={value}` — primary_catalog.

Ultimo check-in: 2026-10-19T23:09:26.342049+00:00.
- [ ] Fonte letta: Acquisizione non riuscita o formato osservato solo indirettamente; non conteggiato come lettura verificata.
- [ ] Campi letti: Il contenuto non è disponibile per un confronto attendibile dei campi.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [ ] Catalogo confrontato: Confrontate 1 schede con gli URL campione; vuoti e incongruenze non sono stati corretti automaticamente.
- Campione: https://wwwservizi.regione.emilia-romagna.itnote.asp?anno=2026&cod_co=037009&progr_fiera=1&dt_datada=&dt_dataa=&r1=&strr_sede=&strr_provincia=&r2=&strs_keywords= — malformed_source_url_needs_repair, lettura —; SHA-256 `—`.
- Riscontro: Nessuna presenza/assenza di campi fonte è verificata.
- Riscontro: Serve risolvere link relativi con urljoin contro la pagina di provenienza, validare hostname e conservare URL originale. Non indovinare la destinazione della vecchia scheda.
- Riscontro: Una scheda ha titolo SETTIMANA CALDERARESE - MERCATO DEI CENTO e campo citta MERCATO DEI CENTO: il nome non è una geografia confermata.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/other.json`.

### comune.corciano.pg.it--742b4c3b5941

`/download/oggetto_documenti/372/1O__Oelenco-mercati-settinamanali-comune-corciano.csv` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://comune.corciano.pg.it/download/oggetto_documenti/372/1O__Oelenco-mercati-settinamanali-comune-corciano.csv — read, lettura 2026-10-19T22:36:58.738511+00:00; SHA-256 `1c42627045f28ab7d0bd187493339f27b3e2c7afcfd5155bf7f739cf49a83121`.
- Riscontro: Risorsa CSV collegata alla fonte comune.corciano.pg.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### comune.roma.it--198edc4b9b92

`/web/it/informazione-di-servizio.page?contentId={value}` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://www.comune.roma.it/web/it/informazione-di-servizio.page?contentId=IDS1305104 — read, lettura 2026-10-19T22:37:04.771274+00:00; SHA-256 `3ca7e768307040f0f970ce60c29d5990f1ed132b74f8012ea9c7740c73294ccb`.
- Riscontro: Risorsa HTML collegata alla fonte comune.roma.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### comune.roma.it--289437d31bd8

`/web-resources/cms/documents/Determina_17723_24_02_2025_venerd_firm.pdf` — additional_attribution.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://www.comune.roma.it/web-resources/cms/documents/Determina_17723_24_02_2025_venerd_firm.pdf — read, lettura 2026-10-19T22:37:01.247267+00:00; SHA-256 `6d0ce65fb052b30d141f5a80fb33e35eaaca95e01caf4f512bdecefebb159203`.
- Riscontro: Risorsa PDF collegata alla fonte comune.roma.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### comune.roma.it--62c2acfb1eb4

`/web-resources/cms/documents/Contratto_AMA_2024__2025_Allegato_7_Carta_Municipale_Municipio_13.pdf` — additional_attribution.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://www.comune.roma.it/web-resources/cms/documents/Contratto_AMA_2024__2025_Allegato_7_Carta_Municipale_Municipio_13.pdf — read, lettura 2026-10-19T22:37:03.805302+00:00; SHA-256 `c7c428362059a8795a838d33b26b5ad428b8a3b4b6e86c36f704246753cc2c1f`.
- Riscontro: Risorsa PDF collegata alla fonte comune.roma.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### data.comune.fi.it--aebe3c51a74f

`/datastore/download.php?format={value}&id={value}&type={value}` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://data.comune.fi.it/datastore/download.php?id=7501&type=1&format=metadata — read, lettura 2026-10-19T22:41:29.044578+00:00; SHA-256 `606cdb1499c978a3fa25a146a54cc4927e05c0b4297d2e01e34365cc29a247ad`.
- Riscontro: Risorsa XML metadata collegata alla fonte feelflorence.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### dati.comune.milano.it--811e995cd76b

`/dataset/f758d24c-8805-40b0-9a72-a8aac06d1e98/resource/b07ed03a-d198-4a16-9eb5-744cb406f3eb/download/mss-mag24_final.json` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://dati.comune.milano.it/dataset/f758d24c-8805-40b0-9a72-a8aac06d1e98/resource/b07ed03a-d198-4a16-9eb5-744cb406f3eb/download/mss-mag24_final.json — read, lettura 2026-10-19T22:38:50.775827+00:00; SHA-256 `800e354085cdc3ac85ae5f2b785f1fe3407f5e0a3de605adc22656dc397b1336`.
- Riscontro: Risorsa JSON collegata alla fonte dati.comune.milano.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### dati.comune.milano.it--e93fe70b0688

`/dataset/f758d24c-8805-40b0-9a72-a8aac06d1e98/resource/b6c162cb-6e26-4e1c-bba0-3f1f595a19dc/download/mss-mag24.geojson` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://dati.comune.milano.it/dataset/f758d24c-8805-40b0-9a72-a8aac06d1e98/resource/b6c162cb-6e26-4e1c-bba0-3f1f595a19dc/download/mss-mag24.geojson — read, lettura 2026-10-19T22:41:28.961118+00:00; SHA-256 `e91a78745efd0a090dccff6117f127469276bc2970bca919b51e8b8a5d8af2f2`.
- Riscontro: Risorsa GeoJSON collegata alla fonte dati.comune.milano.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### dati.comune.milano.it--fa20a25c15b9

`/dataset/f758d24c-8805-40b0-9a72-a8aac06d1e98/resource/5d4a83c3-6ac5-4430-b5a9-d669a933b036/download/mss-mag24_final.csv` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://dati.comune.milano.it/dataset/f758d24c-8805-40b0-9a72-a8aac06d1e98/resource/5d4a83c3-6ac5-4430-b5a9-d669a933b036/download/mss-mag24_final.csv — read, lettura 2026-10-19T22:41:28.568105+00:00; SHA-256 `944d041207856e13fab53b5e322f67334588f8207df185e2579819bb00d7be20`.
- Riscontro: Risorsa CSV collegata alla fonte dati.comune.milano.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### dati.comune.roma.it--698a81c590c6

`/catalog/it/dataset/e2e30174-ba7f-4319-bf4a-c13f80278c0c/resource/61ae5f8b-8ac5-44c0-ad82-6d342d0c45d6/download/mercati_rionali_giugno_2022.csv` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://dati.comune.roma.it/catalog/it/dataset/e2e30174-ba7f-4319-bf4a-c13f80278c0c/resource/61ae5f8b-8ac5-44c0-ad82-6d342d0c45d6/download/mercati_rionali_giugno_2022.csv — read, lettura 2026-10-19T22:37:00.973213+00:00; SHA-256 `0802f34534867411134c5e92e25f8d0e89fc1ceae0b81a67b8ef4ad5ad1c40af`.
- Riscontro: Risorsa CSV collegata alla fonte dati.comune.roma.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### dati.comune.roma.it--e20fd21ce1be

`/catalog/it/dataset/e2e30174-ba7f-4319-bf4a-c13f80278c0c/resource/cd515283-3079-42fe-a066-ced11b9a8387/download/mercati_rionali_agosto_2023.csv` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://dati.comune.roma.it/catalog/it/dataset/e2e30174-ba7f-4319-bf4a-c13f80278c0c/resource/cd515283-3079-42fe-a066-ced11b9a8387/download/mercati_rionali_agosto_2023.csv — read, lettura 2026-10-19T22:38:52.378579+00:00; SHA-256 `71b479a7067cfb66249de0d132b311eb7484daec06a462f513da910efb0bf204`.
- Riscontro: Risorsa CSV collegata alla fonte dati.comune.roma.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### dati.comune.roma.it--e33b298b8b6e

`/catalog/api/3/action/package_show?id={value}` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://dati.comune.roma.it/catalog/api/3/action/package_show?id=e2e30174-ba7f-4319-bf4a-c13f80278c0c — read, lettura 2026-10-19T22:37:00.411955+00:00; SHA-256 `2ab85403fe3fcbbc4faa1ad7e0e695d363946beaf0f04e9435e23d71a76e79de`.
- Riscontro: Risorsa CKAN JSON metadata collegata alla fonte dati.comune.roma.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### dati.lombardia.it--432287cb35fe

`/resource/68zx-njaw.json?$limit={value}&$order={value}` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://www.dati.lombardia.it/resource/68zx-njaw.json?$limit=2000&$order=%3Aid — read, lettura 2026-10-19T22:38:52.338719+00:00; SHA-256 `30aa877027b9538f11396d9c1ba0a0ced2482c74a6b46d1c2f372a7cbdb17e46`.
- Riscontro: Risorsa Socrata JSON collegata alla fonte dati.lombardia.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### dati.lombardia.it--94017c4ffe4c

`/api/views/68zx-njaw.json` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://www.dati.lombardia.it/api/views/68zx-njaw.json — read, lettura 2026-10-19T22:36:54.778927+00:00; SHA-256 `1cf3eb672c3e36777c4d361c6fe378c25d92c8d1c064cb8441b0b52d6d9629f0`.
- Riscontro: Risorsa JSON metadata collegata alla fonte dati.lombardia.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### datigis.comune.fi.it--13155d9f084d

`/resources/open-data/mercati/feelflorence_mercati.zip` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://datigis.comune.fi.it/resources/open-data/mercati/feelflorence_mercati.zip — read, lettura 2026-10-19T22:41:29.899755+00:00; SHA-256 `3d91d1e030db2f7f27d20f92b8f2ba2d8f02dad02f9b37a700ea72442b8e01e5`.
- Riscontro: Risorsa ZIP shapefile collegata alla fonte feelflorence.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### datigis.comune.fi.it--3dffd7636e05

`/resources/open-data/mercati/feelflorence_mercati.geojson` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://datigis.comune.fi.it/resources/open-data/mercati/feelflorence_mercati.geojson — read, lettura 2026-10-19T22:38:51.356991+00:00; SHA-256 `a37afe2e8bbb6ad43ec30d9b02cb5132c852b25f8a828a207bb1be52d625c257`.
- Riscontro: Risorsa GeoJSON collegata alla fonte feelflorence.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### datigis.comune.fi.it--d75dc7aad7be

`/resources/open-data/mercati/feelflorence_mercati.csv` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://datigis.comune.fi.it/resources/open-data/mercati/feelflorence_mercati.csv — read, lettura 2026-10-19T22:41:28.842772+00:00; SHA-256 `416cd8d295f6d6724ce3bbd39e819a4433d0f19e00e2a815d964b989c5322e1d`.
- Riscontro: Risorsa CSV collegata alla fonte feelflorence.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### gisportal.comune.milano.it--435c4683d9f2

`/server/rest/services/D_SUAP_Specialistica_autorizzazioni_concessioni/MSS_Mercati_Settimanali_Scoperti/MapServer/0/query?f={value}&outFields={value}&outSR={value}&resultRecordCount={value}&returnGeometry={value}&where={value}` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://gisportal.comune.milano.it/server/rest/services/D_SUAP_Specialistica_autorizzazioni_concessioni/MSS_Mercati_Settimanali_Scoperti/MapServer/0/query?where=1%3D1&outFields=*&returnGeometry=true&outSR=4326&f=json&resultRecordCount=200 — read, lettura 2026-10-19T22:36:55.472502+00:00; SHA-256 `12982ae068b7e1d513c012126c2bc2555ac36fe542cce61d2c91a744d1997029`.
- Riscontro: Risorsa ArcGIS JSON collegata alla fonte dati.comune.milano.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### gisportal.comune.milano.it--b80d45a7e660

`/server/rest/services/D_SUAP_Specialistica_autorizzazioni_concessioni/MSS_Mercati_Settimanali_Scoperti/MapServer/0?f={value}` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://gisportal.comune.milano.it/server/rest/services/D_SUAP_Specialistica_autorizzazioni_concessioni/MSS_Mercati_Settimanali_Scoperti/MapServer/0?f=json — read, lettura 2026-10-19T22:36:53.672038+00:00; SHA-256 `dd88a9dc783baac7d1e028bd323f4bc81ce3825448890a3fa8335aff5c778d08`.
- Riscontro: Risorsa ArcGIS metadata collegata alla fonte dati.comune.milano.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### google.com--d20b509e76f3

`/maps/d/kml?forcekml={value}&mid={value}` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://www.google.com/maps/d/kml?mid=1qazVyQE42cRyzP-gMSxjZz8wX8iowbQ&forcekml=1 — read, lettura 2026-10-19T22:36:59.011868+00:00; SHA-256 `20fe71c60aebe37af1ffca96a8a9663a68fd7198e3f022ffb89c87ef1175f67c`.
- Riscontro: Risorsa KML collegata alla fonte comune.roma.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### happings.com--311686cb6f8d

`/it/mercati-settimanali-{a\|ad}-{provincia}-e-provincia/` — current_observed_layout.

Ultimo check-in: 2026-10-19T22:47:28.515202+00:00.
- [ ] Fonte letta: Acquisizione non riuscita o formato osservato solo indirettamente; non conteggiato come lettura verificata.
- [ ] Campi letti: Il contenuto non è disponibile per un confronto attendibile dei campi.
- [x] Parser confrontato: Replay del lettore provinciale sul contenuto restituito e confronto con il monitor del dettaglio; il monitor riconosce il template ma non importa i campi del dettaglio.
- [ ] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Riscontro: Layout provinciale attuale osservato nei corpi restituiti da vecchi URL e nei canonical; nessuna richiesta diretta di questo formato registrata in questo check-in.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/happings.json`.

### happings.com--795abb069b70

`/it/happing/{slug}/` — current_observed_layout.

Ultimo check-in: 2026-10-20T16:09:24.295488+00:00.
- [x] Fonte letta: Nove nuove risposte HTTP complete analizzate, con URL finale, SHA e timestamp originali.
- [x] Campi letti: Testo, self Event, elenco date, intervalli, condizioni e sottoeventi confrontati; conflitti mantenuti.
- [x] Parser confrontato: Nove replay dei byte originali uguali alle fixture nei fatti e conflitti; estrazione, discovery, raccordi ed interfaccia identificati dagli hash.
- [x] Catalogo confrontato: Confronto con tutte le 13.824 schede; 13.826 schede nel candidato esportato, due nuove identità e nessuna riga precedente alterata dal dettaglio. Pubblicazione distinta dal replay.
- Campione: https://www.happings.com/it/happing/mercato-del-venerdi-mattina-a-lana/ — read, lettura 2026-10-19T22:34:48+00:00; SHA-256 `5ba96a9364c3db4e29fea0f4f4603011205df3e658716f79bc8a9746ed9f3e0b`.
- Campione: https://www.happings.com/it/happing/mercato-coperto-campagna-amica-di-pisa/ — read, lettura 2026-10-20T15:32:41.308593+00:00; SHA-256 `d07bc45c56cde4ee939aab5bb927496d1e18f0f17aa4cab01fe587cac2faafa0`.
- Campione: https://www.happings.com/it/happing/mercato-del-venerdi-mattina-a-lana/ — read, lettura 2026-10-20T15:34:40.551888+00:00; SHA-256 `8c998dc38dd2732bc5e1ddd2ae7604475a617ad82b3655584ba2bb7464e55e58`.
- Campione: https://www.happings.com/it/happing/mercato-di-campagna-amica-di-pescia/ — read, lettura 2026-10-20T15:36:14.380071+00:00; SHA-256 `913814e5bde8a34ae4b72ce900042e0437e3c67a40e25576cce3e60bf4cc2045`.
- Campione: https://www.happings.com/it/happing/mercato-antiquario-lucca-autunno-inverno-2026/ — read, lettura 2026-10-20T15:41:40.544547+00:00; SHA-256 `f3cbddbae2ef0a4c2d4f100110646c661efe7525c5d3c67acc1b1d797b6e7d81`.
- Campione: https://www.happings.com/it/happing/mercato-settimanale-a-castelrotto/ — read, lettura 2026-10-20T15:41:46.295803+00:00; SHA-256 `e5ff56d561d4df2a7e495c71b69d23fe22a2f5729b0ecd0f8ef3d2eed2814fbc`.
- Campione: https://www.happings.com/it/happing/mercatino-regionale-piemontese/ — read, lettura 2026-10-20T15:42:08.444838+00:00; SHA-256 `fa5aa012531ec6b5be3428d955deb5a6a4ade16a84cbbe4a1a22ef9aebf874e2`.
- Campione: https://www.happings.com/it/happing/mercatino-di-natale-di-parcines/ — read, lettura 2026-10-20T15:41:52.486746+00:00; SHA-256 `0ea38afb17251db506fe98ff4c7c12d277bdc96faa0a631ec22c6b58af0724e9`.
- Campione: https://www.happings.com/it/happing/mercatino-di-natale-polvere-di-stelle-jingle-bells-rock/ — read, lettura 2026-10-20T15:42:01.871964+00:00; SHA-256 `76ce1928a92446d2d7f3dc0c1674268b9976de7d0da529e0f454637e058a5ba5`.
- Campione: https://www.happings.com/it/happing/il-mercato-dei-fumetti-nel-2026-tra-assestamento-e-crescita/ — read, lettura 2026-10-20T15:41:56.136859+00:00; SHA-256 `9055fe122811577a60cddee2286fd2cd5baa2742ea60ef951e1dbb5f5565c429`.
- Riscontro: Lettore operativo del dettaglio e discovery persistente collegati ad Autopilot DEV.
- Riscontro: Due nuove identità nel replay; quattro confronti ambigui conservati senza fusione.
- Riscontro: Due conflitti della fonte e un incontro non commerciale esclusi dall’importazione.
- Riscontro: Date riportate dalla fonte, orari per data, intervalli e condizioni conservati fino all’interfaccia.
- Riscontro: Data editoriale e lettura della fonte non costituiscono conferma dell’apertura.
- Dettagli: `reports/automation/happings-detail-validation-2026-10-20.json`.

### opendata.comune.bologna.it--1cd38e42835b

`/api/records/1.0/search/?dataset={value}&rows={value}` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://opendata.comune.bologna.it/api/records/1.0/search/?dataset=mercati-e-fiere&rows=350 — read, lettura 2026-10-19T22:36:57.945929+00:00; SHA-256 `ba71aebc426844618607e70feaab12907029e3fffb9e0300cdd4f727492426cc`.
- Riscontro: Risorsa Opendatasoft JSON collegata alla fonte opendata.comune.bologna.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### opendata.comune.bologna.it--7645d392be0d

`/api/records/1.0/search/?dataset={value}&fields={value}&q={value}&rows={value}` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://opendata.comune.bologna.it/api/records/1.0/search/?dataset=mercati-e-fiere&rows=100&q=tipologia_mercato%3Arionale+OR+tipologia_mercato%3Aperiodico+OR+tipologia%3A%22mercato+produttori+agricoli%22&fields=denominazione%2Cubicazione%2Ctipologia%2Ctipologia_mercato%2Cgiorni_svolgimento%2Corario_svolgimento — read, lettura 2026-10-19T22:38:51.721355+00:00; SHA-256 `21a95c15245929cc3586cce24d47b2864451d60730f952200b4750837294b73a`.
- Riscontro: Risorsa Opendatasoft JSON configured subset collegata alla fonte opendata.comune.bologna.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### opendata.comune.bologna.it--97ad8bc609d7

`/api/explore/v2.1/catalog/datasets/mercati-e-fiere` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://opendata.comune.bologna.it/api/explore/v2.1/catalog/datasets/mercati-e-fiere — read, lettura 2026-10-19T22:36:56.877571+00:00; SHA-256 `46298b228c3d5d39c8925bc104b81e331e7fde1962c4f4193ff16f2ee7138e68`.
- Riscontro: Risorsa JSON metadata collegata alla fonte opendata.comune.bologna.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### opendata.comune.fi.it--87db03cd3378

`/page_dataset_show?id={value}` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://opendata.comune.fi.it/page_dataset_show?id=mercati — read, lettura 2026-10-19T22:36:56.545780+00:00; SHA-256 `968540a56509bf750d734afeae6b1d02c73f2238243708da59af0305decbae62`.
- Riscontro: Risorsa HTML collegata alla fonte feelflorence.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### www2.comune.milano.it--040bb7e6ca15

`/web/fare-impresa/mercati-settimanali-scoperti` — attached_resource.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [ ] Fonte letta: Acquisizione non riuscita o formato osservato solo indirettamente; non conteggiato come lettura verificata.
- [ ] Campi letti: Il contenuto non è disponibile per un confronto attendibile dei campi.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [ ] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://www2.comune.milano.it/web/fare-impresa/mercati-settimanali-scoperti — http_error, lettura 2026-10-19T22:36:51.727767+00:00; SHA-256 `—`.
- Riscontro: Risorsa HTML collegata alla fonte dati.comune.milano.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

### www2.comune.milano.it--5fe8b3668208

`/documents/87339536/190972166/MSS+-+ubicazioni%2Corari%2Corganici+1+Ottobre+2026.pdf/d5b13a87-b9de-7c48-5674-65c4151565c3?t={value}` — additional_attribution.

Ultimo check-in: 2026-10-19T23:27:40.941196+00:00.
- [x] Fonte letta: Letti e analizzati 1 campioni del formato; acquisizioni, hash e transizioni registrati.
- [x] Campi letti: Campi, assenze e limiti di attribuzione annotati nel campione; dati dell’evento distinti da footer, altri eventi e date editoriali.
- [ ] Parser confrontato: Il codice confrontato è cambiato: ripetere il confronto.
- [x] Catalogo confrontato: Risorsa ausiliaria: nessuna scheda conteggiata di nuovo; il raccordo alle identità esistenti resta separato dalla lettura.
- Campione: https://www2.comune.milano.it/documents/87339536/190972166/MSS+-+ubicazioni%2Corari%2Corganici+1+Ottobre+2026.pdf/d5b13a87-b9de-7c48-5674-65c4151565c3?t=1790841765683 — read, lettura 2026-10-19T22:36:52.416512+00:00; SHA-256 `7feaa1429e221cec8d2b8bb962ed747f5100e890321d391e3f85e7f161cb6c6c`.
- Riscontro: Risorsa PDF collegata alla fonte dati.comune.milano.it; non aumenta le schede conteggiate.
- Da riconfrontare: parser_code_changed.
- Dettagli: `reports/automation/source-format-audit-2026-10-20/official.json`.

## TODO del meccanismo

- [x] **HAPP-FORMAT-01 — Leggere i dettagli evento e dimostrare il raccordo con il mercato** (P0; done). Criterio di chiusura: Fixture returns address, ordinary hours, explicit dates, organizer profile and source GPS for the self Event URL. Related-event cards, footer/publisher Organization and a second market in the same town cannot contribute fields. Ambiguous venue/name matches produce review evidence without overwriting an existing address or claiming precise GPS. Esito: Lettore self Event, confronto identità/Comune/indirizzo, discovery dalle sitemap e arricchimento automatico DEV implementati. Replay di nove dettagli su 13.824 schede, due nuove identità distinte, quattro possibili duplicati sospesi. Footer, schede correlate, concerti e articoli non forniscono dati di mercato. Prove: reports/automation/happings-detail-validation-2026-10-20.json.
- [x] **HAPP-FORMAT-02 — Conservare calendari espliciti ed eccezioni della singola edizione** (P0; done). Criterio di chiusura: Nine ordinary Friday entries plus the listed Thursday exception remain ten dates, without fabricating 25 December or January dates. The extraordinary 24 December closing time remains 13:00; do not copy the next-date 12:30 end time to it. A missing next edition, changed boundary or conflicting text/JSON-LD prevents renewal until the scope is resolved. Esito: Calendario della fonte conservato fino a export e interfaccia. Lana mantiene dieci date e la chiusura alle 13 del 24 dicembre; nessuna proiezione oltre il calendario pubblicato. Intervalli di più giorni conservano i limiti senza inventare aperture quotidiane. Conflitti, annullamenti ed eccezioni vengono mantenuti; regressioni backend/frontend e replay reali documentati.
- [ ] **HAPP-FORMAT-03 — Trovare le risorse provinciali attuali anche quando manca l’URL nel catalogo** (P1; open). Criterio di chiusura: The Trieste-shaped fixture becomes a source resource candidate while all 8 old TS market IDs remain intact. A canonical link or redirect to a different/unproved province fails closed; no inferred HTTP redirect metadata. Source-location ambiguity is still held after routing succeeds.
- [ ] **HAPP-FORMAT-04 — Mantenere distinte le righe con sedi e giorni diversi** (P1; open). Criterio di chiusura: The 52-row Trieste-shaped source fixture retains all 52 row identities; a seven-weekday map cannot collapse them to 7. Multiple venues on the same weekday never yield an arbitrary address overwrite. Cross-source duplicate review occurs before declaring a new market; source rows are not counted as newly verified markets.
- [ ] **HAPP-FORMAT-05 — Risolvere con prove i vecchi URL alterati** (P1; open). Criterio di chiusura: A 404 sample contributes no field-presence claims or freshness receipt. A guessed town slug is never recorded as an observed canonical or redirect. Repeated-hyphen, suffix-number and qualifier variants remain distinct until a source/identity match is proven.
- [ ] **HAPP-FORMAT-06 — Conservare stagionalità e frequenze separate dal Comune** (P1; open). Criterio di chiusura: Estivo does not create a year-round weekly forecast or get swallowed into a geographical match. Ogni 15gg without an anchor cannot turn into a weekly or an invented fortnightly calendar. Known place names such as Inverno e Monteleone or Passeggiata d’Inverno remain protected from false seasonal matches.
- [ ] **HAPP-FORMAT-07 — Misurare i campi mancanti in base a ciò che il formato pubblica** (P2; open). Criterio di chiusura: A source giving only centro contributes zero recoverable precise addresses. La mattina remains a daypart and never becomes fabricated opening/closing hours. An event-detail page with real hours is counted as an unsupported field-reader gap rather than source-hours absent.
- [ ] **HAPP-FORMAT-08 — Separare la data della pagina dalla verifica del mercato** (P2; in_progress). Criterio di chiusura: JSON-LD WebPage.datePublished is discoverable even when article meta tags are absent. A page publication date cannot manufacture event confirmation or override a contradicted edition list. Unknown row freshness remains distinguishable from a known page publication date. Esito: Dettagli evento: WebPage.datePublished/dateModified estratti separatamente da calendario, lettura e conferma, con test. Resta da estendere il confronto dei metadati al formato provinciale compreso in questo TODO; non chiuso globalmente.
- [x] **EES-SCOPED-DETAIL — Leggere il riquadro e il testo dell’evento senza contaminazioni** (P1; done). Criterio di chiusura: 31 stdlib tests pass; replay 17/17 same documents, no footer address and no related-event municipality; card-only legacy page remains readable. Network and activation policy unchanged. Esito: Implementato e provato su 17 HTML con 31 regressioni stdlib; il ponte dei metadati ha un TODO separato.
- [ ] **EES-METADATA-ROUNDTRIP — Conservare metadati e limiti dalla fonte fino all’export** (P1; open). Criterio di chiusura: Round-trip an archived weekly announcement without generating future openings; retain all original calendar bounds and source hashes/read dates; a past edition never deletes the market or claims permanent closure.
- [ ] **EES-MULTI-LOCATION-BRIDGE — Raccordare separatamente le righe con più sedi** (P1; open). Criterio di chiusura: Four distinct rows survive, a duplicate source block does not create a fifth market, and a header address or day cannot be propagated to another venue.
- [ ] **EES-NARRATIVE-FIELD-GAPS — Leggere sedi e calendari nel testo narrativo delimitato** (P1; open). Criterio di chiusura: The additional grammar recovers the intended main-market field without importing a concert/workshop location, related-event date or publisher footer address.
- [ ] **EES-URL-DISCOVERY-INVENTORY — Verificare discovery e filtri delle categorie Eventi e Sagre** (P1; open). Criterio di chiusura: All 16 present path prefixes are classified; Eventi/Sagre/Festival pages cannot silently become ordinary weekly markets.
- [x] **EES-JSONLD-CONFLICTS — Rilevare JSON-LD invalidi o discordanti senza inventare campi** (P1; done). Criterio di chiusura: Invalid JSON-LD does not break a valid visible card; another event's JSON-LD does not contribute fields; date endpoints never become market hours. Esito: Implementato e provato su 17 HTML con 31 regressioni stdlib; il ponte dei metadati ha un TODO separato.
- [ ] **CDC-STRUCTURED-ADAPTER — Realizzare il lettore dei campi strutturati Cose di Casa** (P1; open). Criterio di chiusura: Fixtures cover all five observed semantic variants, contain no raw publisher HTML, and distinguish field extraction from source reading and verification.
- [ ] **CDC-CALENDAR-SEMANTICS — Rappresentare edizioni, ricorrenze e sospensioni Cose di Casa** (P1; open). Criterio di chiusura: Bologna includes the preceding Saturday, Cernobbio retains only listed Fridays, Venice retains five separate ranges, and unspecified extra-edition years remain unknown.
- [ ] **CDC-SOURCE-INTERNAL-CONFLICTS — Gestire conflitti tra calendario visibile e JSON-LD** (P1; open). Criterio di chiusura: No 19 October opening is inferred for a Sunday market; no disputed summer span is expanded; suspension rows labelled Prossime date are not interpreted as closures.
- [ ] **CDC-HOURS-CONTEXT — Leggere gli orari del mercato dal relativo blocco** (P1; open). Criterio di chiusura: Bologna 08:30–18:00, Venice 09:00–19:00, Cernobbio 08:00–19:00 and Fiumicino 18:00–24:00 are detected; Cernobbio's 10–18 activity is not substituted, and Todi's sunset is not converted into an invented clock time.
- [ ] **CDC-PROVENANCE-URLS — Conservare provenienza, canonical e date della fonte** (P1; open). Criterio di chiusura: No redirect is claimed from a canonical tag; no editorial modification timestamp is stored as a market occurrence or personal verification date.
- [ ] **EDITORIAL-FIELD-RETENTION-GATE — Controllare le perdite tra parser, normalizzazione ed export** (P1; open). Criterio di chiusura: Report supported source formats, observed field presence, parser retention and verified data as separate measures. Completion of a parser task never marks the storage bridge or all source records as verified.
- [x] **OFF-FI-01 — Conservare integralmente orari e chiusure Firenze fino all’export** (P1; done). Criterio di chiusura: Replay the complete four-row original: all 17 date tokens remain attributable in San Lorenzo; source age, IDs, forecast dates and confirmation status unchanged. A long compound hours rule survives adapter and export. Esito: Correzione provata sul codice finale con 11 nuove regressioni e 137 test mirati. Quattro orari Firenze conservati integralmente attraverso gate, ricevute, merge, dettaglio e indice; una troncatura preesistente corretta nel replay, chiusure del 2025 restano del 2025. Prove separate dopo il fix in reports/automation/source-format-audit-2026-10-20/official.json; nessuna modifica manuale al catalogo.
- [x] **OFF-BO-01 — Conservare orari stagionali e composti Bologna nella catena attiva** (P1; done). Criterio di chiusura: All nine recordid-matched seasonal strings survive candidate + export; numeric forecasts are not added; source remains 2025-04-02; simple ranges still work. Esito: Correzione provata sul codice finale con 11 nuove regressioni e 137 test mirati. Nove orari Bologna prima vuoti recuperati attraverso il contratto generico attivo, con identità/sede esatte e ricevuta completa. Fonte regressiva o lettura coeva sospendono l’aggiornamento; punteggiatura delle chiusure e data fonte 2025 conservate. Prove separate dopo il fix in reports/automation/source-format-audit-2026-10-20/official.json; nessuna modifica manuale al catalogo.
- [ ] **OFF-LO-01 — Rispettare dal/al, mesi e frequenze Lombardia prima di proiettare date** (P1; open). Criterio di chiusura: Real 3-record/38-date conflict set is recognized; full-year ranges remain unchanged; Idro combined al is reported as ambiguous. No manual ID exceptions.
- [ ] **OFF-LO-02 — Conservare denominazione originale e qualificatori del mercato Lombardia** (P2; open). Criterio di chiusura: Roundtrip meaningful source values through a bounded evidence representation; do not substitute tender dates for market dates or tender links for organizers.
- [ ] **OFF-MI-01 — Leggere tutte le righe delle tabelle PDF Milano** (P1; open). Criterio di chiusura: Current original yields 93 market/day pairs and 84 labels; six omissions explained; site/day aliases reviewed without collapsing distinct market days/venues.
- [ ] **OFF-MI-02 — Separare orari di vendita, sgombero e variazioni stagionali Milano** (P1; open). Criterio di chiusura: Ciccotti/Fauchè/Garigliano/Tabacchi seasonal columns and Papiniano split subareas survive; no single time is guessed or blindly copied over a conflicting stored value.
- [ ] **OFF-MI-03 — Conservare geometrie e note di spostamento Milano come prove di fonte** (P2; open). Criterio di chiusura: Do not convert polygons or old center points into verified entrances; JSON/CSV label variation does not produce new identity.
- [ ] **OFF-FI-02 — Leggere la data Firenze dai metadati validati, con il giusto ambito** (P2; open). Criterio di chiusura: Dataset page data-modified 2026-09-01 is distinguished from per-market verification and from explicit 2025 closures.
- [ ] **OFF-FI-03 — Conservare link e contatti distinti dall’attribuzione Firenze** (P2; open). Criterio di chiusura: Four records remain four; DBF truncation does not overwrite fuller evidence; three source links remain attributable without inferring organizer authority.
- [ ] **OFF-BO-02 — Conservare giorni, mesi ed esclusioni completi Bologna** (P2; open). Criterio di chiusura: Split months and July/August exclusions remain visible evidence; aged dataset never creates fresh events.
- [ ] **OFF-BO-03 — Leggere la specializzazione prima della classificazione Bologna** (P2; open). Criterio di chiusura: Twelve category differences reviewed, including vintage and antiquarian examples; postal/locality metadata and office contact are not mistaken for organizer fields.
- [ ] **OFF-CO-01 — Mantenere parità delle colonne e controllo degli assi Corciano** (P3; open). Criterio di chiusura: All eleven original columns remain consumed; no duplicate market created from the two quarantined source IDs; no row freshness manufactured from page timestamp.
- [ ] **OFF-RO-01 — Leggere l’ultima distribuzione d881 Roma con orari per giorno e note** (P1; open). Criterio di chiusura: 70 named rows, 933 empty rows ignored; damaged UTF-8 replacement values are never emitted; historical row age remains explicit and unknown freshness does not become 2026 confirmation.
- [ ] **OFF-RO-02 — Raccordare date AGGIORNATO e distinguere coordinate generiche Roma** (P2; open). Criterio di chiusura: Do not state CSV supplied GPS; preserve source-backed full addresses while withholding unsupported navigation precision.
- [ ] **OFF-RO-03 — Raccordare revisioni, atti e planimetrie Roma senza inventare ingressi/orari** (P2; open). Criterio di chiusura: Market vs stall vs map marker remains distinct; 2024/2025 map facts cannot overwrite newer 2026 source; no new calendar dates from administrative deadlines.
- [ ] **CNY-DETAIL — Leggere il riquadro dell’evento Citynews nel suo ambito** (P2; open). Criterio di chiusura: Indirizzo, orario e intervallo visibile restano legati a titolo, Comune e URL della singola edizione; footer e programma accessorio esclusi.
- [ ] **CNY-DISCOVERY — Separare elenchi Citynews e schede evento** (P2; open). Criterio di chiusura: Una pagina indice/tag produce URL di dettagli, non attributi globali da applicare alle vecchie schede; nessun evento indicato non equivale a chiusura del mercato.
- [ ] **CNY-EDITORIAL — Leggere le varianti redazionali Citynews** (P2; open). Criterio di chiusura: Articoli con più mercati, calendari espliciti o giorni di recupero restano separati per identità, sede e condizione; data redazionale non diventa data del mercato.
- [ ] **CNY-ROUNDTRIP — Conservare provenienza ed edizione lungo il raccordo Citynews** (P2; open). Criterio di chiusura: Campi letti, conflitti, data editoriale, URL osservato e limiti di edizione arrivano all’evidenza; edizioni passate non generano appuntamenti futuri.
- [ ] **RETRY-CITYNEWS-PADOVA — Riprovare il campione Padova dopo errore temporaneo** (P2; open). Criterio di chiusura: Ottenere e analizzare il documento pubblico completo, senza aggirare limiti o blocchi.
- [ ] **NC-01 — Contratti DOM per confini di evento e campi** (P1; open). Criterio di chiusura: VareseNews/SagreFVG: mantenere date e sede in header della card, scartare header globale. SoloSagre: luogo centro storico, mai menu Sagre Lombardia. UmbriaEventi: titolo dal solo h1, mai data+città+descrizione concatenati. Firenze: riga orari prima del titolo resta unita al relativo blocco.
- [ ] **NC-02 — Discovery dall’indice al dettaglio con identità composta** (P2; open). Criterio di chiusura: Angolo del Collezionista Buonconvento non si collega a Gaiole/Siena/San Gimignano. Anticamente Foligno/Ponte Rio/Orvieto/Perugia restano distinti. Only Usato in sedi diverse non sovrascrive una sede tramite nome. Homepage Eventi Bergamo: primo Event JSON-LD non viene attribuito a Wine Form Mais.
- [ ] **NC-03 — Precisione e provenienza dei calendari** (P1; open). Criterio di chiusura: SagreTorino: nessuna data numerica nuova quando manca anno o estremo. SagreInRomagna: marzo/maggio si salvano come storia finita, non prossime edizioni. Terre di Pisa: range 1 novembre–6 dicembre non diventa 36 giorni di mercato. EmiliaRomagnaTurismo: terzo/quarto weekend restano quattro giornate limitate all’edizione.
- [ ] **NC-04 — Confronto DOM, microdata e JSON-LD** (P2; open). Criterio di chiusura: Orvieto: otto Event storici non nascondono due date future nell’header. Suedtirol: ItemList vuoto e trenta card DOM produce discovery con copertura dichiarata, non zero eventi. Bergamo: date 20 febbraio e 23 gennaio discordanti generano conflitto tracciato.
- [ ] **NC-05 — Conflitti sorgente e valori salvati senza sovrascritture** (P1; open). Criterio di chiusura: Alghero Fertilia: Via Fiume/Via Zara produce conflitto. PugliainFesta: Brindisi/Ostuni non produce overwrite. Firenze: 9–19 nuovo contro 9–20 salvato ha provenance e conflitto. VareseNews: descrizione due giorni/range un anno è incoerente, non autocorrezione dell’anno.
- [ ] **NC-06 — Orari completi, parziali e limiti di validità** (P1; open). Criterio di chiusura: Orvieto: 9:00–tramonto conserva tramonto. PugliainFesta: estremi 2025 ore12 / 2026 ore22 non diventano 12–22 tutti i giorni. JSON-LD 00:00/23:59 non crea ore operative. Numero di telefono con 19.30–21.30 non diventa orario mercato.
- [ ] **NC-07 — Ruoli corretti per organizzatore e contatti** (P2; open). Criterio di chiusura: UmbriaEventi: Associazione InDivenire nel testo non è rimpiazzata dall’editore in schema. SoloSagre: Consorzio Cervia Centro dal blocco Informazioni, mai contatto recruiting. Footer editoriale o performer Organization non produce un organizzatore mercato.
- [ ] **NC-08 — Geografia strutturata e validata senza default dal sito** (P2; open). Criterio di chiusura: Naturno Naturno/Terlano Terlano e città con (PG) non restano geografie duplicate. Provincia MI non viene assegnata automaticamente a ogni voce del portale lombardo. PD/TN come unico campo città e MERCATO DEI CENTO vengono segnalati come geografia non risolta. Ravenna–Marina di Ravenna conserva la frazione.
- [ ] **NC-09 — Qualità dei valori prima della completezza** (P2; open). Criterio di chiusura: NA in orario/indirizzo non conta come dato completo. via Sagre Lombardia Sagre Lazio non passa plausibilità indirizzo. Nome concatenato data/luogo/descrizione non sostituisce un h1 pulito. Indirizzo G e ora 11 privi di contesto non diventano validi solo perché non vuoti.
- [ ] **NC-10 — Coordinate con ambito e precisione dimostrati** (P2; open). Criterio di chiusura: Link Maps con viewport e destinazione usa coordinate del luogo solo se coerenti. Orvieto Place generico non garantisce posizione della piazza. Coordinate di altra card non vengono assegnate al target assente.
- [ ] **NC-11 — Esiti HTTP e migrazioni URL verificabili** (P2; open). Criterio di chiusura: 429/503 mantengono stato non verificato, nessun source_checked_at mercato. Redirect osservato conserva URL originario e finale con hash del contenuto. note.asp concatenato a hostname viene segnalato, non richiesto o riparato per congettura.
- [ ] **NC-12 — Indice dinamico con copertura misurabile** (P2; open). Criterio di chiusura: Ferrara: Nessun risultato/stato non popolato è coverage unresolved. Suedtirol: trenta card campionate non diventano dichiarazione di intero catalogo verificato. Nessun latitude/longitude di dizionario traduzioni produce coordinate.
- [ ] **NC-13 — Eleggibilità di manifestazione come mercato** (P2; open). Criterio di chiusura: Promozione ristorante Hostaria non viene importata come mercato solo dal template evento. Passeggiata/biciclettata priva di vendita/espositori non viene ammessa come mercato dal titolo generico. Manifestazione sportiva nel listato sagre non diventa mercato.
- [ ] **NC-14 — Copertura operativa per formato e prove riproducibili** (P2; open). Criterio di chiusura: Ogni formato ha fixture, hash, data originale e stato review; HTTP falliti restano aperti. Report separa record del formato, record dello stesso URL campione e mercati effettivamente identificati. Replay dei futuri reader conserva ID/storia/dati umani e non rinnova prove assenti.
- [ ] **NC-15 — Qualificatori temporali completi prima delle proiezioni** (P2; open). Criterio di chiusura: Scheggino da marzo a… nell’estratto impedisce proiezione finché dettaglio completo non è disponibile. SoloSagre appuntamenti speciali non vengono cancellati dalla sola ultima domenica. Rinvio meteo Q5 e weekend di SagreFVG non si perdono trasformando il programma in cadenza generica.
