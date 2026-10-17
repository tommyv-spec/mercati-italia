# Source lifecycle — manutenzione automatica di dataset, non mercati uno per uno

Le fonti hanno un contratto per schema, identità, formato, granularità, data e diritti.
Nessuna riga di venditore, concessione o testo grezzo viene persistita qui.
La data di lettura non prova che un mercato abbia aperto oggi.

- Schede nazionali confrontate: **13,805**
- Fonti controllate: **4**
- Record di mercato importati da questo audit: **0**
- Aperture individuali verificate: **0**

| Fonte | Stato | ID fonte fuori catalogo (non nuovi mercati) | Già trattenuti dal controllo sovrapposizioni | Residui senza esito del filtro | Proposte in staging | Collisioni da valutare | Fatti cambiati | ID non più visti (non chiusi) |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| corciano | sola verifica, non apertura confermata | 2 | 2 | 0 | 0 | 0 | 0 | 0 |
| firenze | sola verifica, non apertura confermata | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| lombardia | sola verifica, non apertura confermata | 233 | 233 | 0 | 0 | 0 | 0 | 0 |
| milano | sola verifica, non apertura confermata | 0 | 0 | 0 | 0 | 0 | 0 | 0 |

## Aggiunta di nuove fonti (senza nuovi script per Comune)

1. Scoprire il dataset nella coda automatica e verificare a livello di **fonte** editore, diritti, struttura, data e contenuto.
2. Registrarne il contratto JSON: colonne, identità stabile, una riga=sede/giorno/posteggio, schema atteso, budget dimensione e data effettiva.
3. Gli stessi parser e controlli confrontano in automatico tutti i record ad ogni aggiornamento.
4. Fonti nuove/modificate, identità collidenti, sedi dubbie o dati storici sono trattenuti in revisione: nessun market/evento inventato.
5. Gli adapter esistenti continuano a gestire gli import già revisionati. La promozione di altri contratti richiede qualità/licenza/gate DEV separati.

Le proposte in staging non sono mercati nuovi o aperti: richiedono diritti, identità e QA. Le collisioni segnalano possibili doppioni e sedi non distinguibili.
Questo report non elimina mercati scomparsi da una sorgente e non assegna nuova navigazione GPS.
