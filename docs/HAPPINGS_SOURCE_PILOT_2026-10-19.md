# Happings — confronto sorgente reale vs catalogo (19 ottobre 2026)

## Test controllato, non una campagna di scraping

L'operatore è indicato da
[termini Happings](https://www.happings.com/it/termini-e-condizioni/)
come **Girolamo srls**. I tre PDF trasmessi dall'utente contengono
testi che concedono raccolta automatica; **non mostrano firme
autografe né una firma digitale PDF verificabile**. Uno attribuisce
la titolarità ad Happings S.r.l., diversamente dai termini ufficiali.
Perciò il flag di autorizzazione resta **disabilitato** fino alla
verifica dell'autenticità della concessione del titolare.

La prima verifica è stata una **sola lettura controllata**:
1. richiesta a `robots.txt` con lo user-agent del progetto;
2. consentito dalla policy robots per l'URL;
3. pausa di 3 secondi e una richiesta HTML;
4. nessuna conservazione di contenuti HTML nel repository;
5. confronto in RAM con il catalogo originale;
6. nessuna modifica di orari, indirizzi, date, GPS o status.

**Pagina:** https://www.happings.com/it/mercati-settimanali-a-venezia-e-provincia/

## Risultati misurati

| Metrica | Risultato |
|---|---:|
| Schede catalogo controllate | 13.824 |
| Mercati indicati nella pagina provinciale | 110 |
| Sezioni per giorno | 7 |
| Schede archiviate riferite alla stessa pagina | 57 |
| Vecchie schede mancanti della sede visibile nel loro Comune/giorno | 28 |
| Nuove proposte di indirizzo senza conflitti (match rigoroso) | **11** |
| Gruppi della fonte con più sedi lo stesso giorno | da revisionare |
| Campi effettivamente modificati | **0** |
| Verifiche individuali create | **0** |

I valori **28** e **11** non sono due gruppi da sommare:
11 è un sottoinsieme ammissibile alla fase di *proposta*, non una
prova di apertura. Le altre schede sono escluse per origine
non univoca, via già archiviata incompatibile o sede vaga.

## Nuovo bug di riconciliazione trovato

Le vecchie URL Happings finiscono spesso con
`...mercati-settimanali-a-{provincia}.html`, mentre
quelle nuove usano
`...mercati-settimanali-a-{provincia}-e-provincia/`.
Il comparatore `backend/happings_weekly_layout.py`
**riconosceva soltanto Venezia** per questo redirect:
altre province risultavano senza match, anche se la pagina
veniva letta correttamente. Ora controlla il nome di
provincia in tutte le URL dei listati, con HTTPS, host
e categoria esatti. Blocca altre province, pagine singole
ed endpoint arbitrari.

La lettura di due ulteriori URL storiche,
`mercato-settimanale-a-pianiga.html` e
`mercato-settimanale-a-spinea.html`, ha mostrato che
oggi reindirizzano entrambe **all'indice provinciale
di Venezia**. Questo è un **segnale di struttura cambiata**:
un parser dedicato ai vecchi dettagli troverebbe
un documento completamente diverso da quello atteso.
Queste URL non vengono equiparate in modo
automatico alla pagina provinciale senza una verifica
esplicita del redirect.

## Riprova in un audit riproducibile

Usando un campione HTML già raccolto con titolo
e provenienza controllati:

```bash
python backend/happings_source_enrichment.py \
  --manifest public/data/v1/manifest.json \
  --input-html /tmp/happings-venezia.html \
  --source-url https://www.happings.com/it/mercati-settimanali-a-venezia.html \
  --source-final-url https://www.happings.com/it/mercati-settimanali-a-venezia-e-provincia/ \
  --out /tmp/happings-proposals.json \
  --summary /tmp/happings-summary.json
```

Il comando è **offline e read-only** (non richiede permesso
di riuso automatico e non scrive schede); i risultati
restano un report di controllo. I file di prova
non vanno committati su GitHub. Una futura
concessione verificabile del titolare potrà
consentire la fase di aggiornamento, sempre con
limiti, controlli di qualità e permessi separati.

## Obiettivo successivo

Solo dopo aver verificato il consenso:
- massimo **2 pagine / esecuzione**, con verifica robots,
  pausa di almeno 3 secondi e timeout;
- estrazione degli indirizzi unici nella struttura
  `div.happings-seo-content > h3 > ul > li`;
- match univoco per Comune, provincia, giorno e
  provenienza; zero fusioni di ID;
- solo campo `indirizzo` vuoto, mai sovrascrittura,
  mai orari stimati o coordinate nuove;
- confronto indipendente degli esatti campi
  permessi prima della pubblicazione DEV.

Per recuperare effettivamente la **qualità di tutte le
schede** servono ancora gli altri formati di sorgente
e i riscontri da Comuni/organizzatori per casi ambigui.
