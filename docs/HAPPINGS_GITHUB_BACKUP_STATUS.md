# Happings: dati, backup e spazio locale

**Stato al 21 ottobre 2026.**

Il repository pubblico `tommyv-spec/mercati-italia` contiene già il
sistema ripetibile di discovery, parsing, riconciliazione ISTAT, aggiornamento
del catalogo, controlli pre- e post-pubblicazione e scheduler DEV. Il flusso
GitHub Actions già esistente usa runner pubblici gratuiti, senza Git LFS,
storage acquistato o nuove infrastrutture.

## Verificato su GitHub

- DEV: `improve/data-quality-security-performance-2026-10-11`.
- Esecuzione Autopilot: `39652026641`, tutti e quattro i job riusciti.
- Nuove schede settimanali ammesse da Happings: **18**.
- Confronto dei cataloghi: **13.981 prima, 13.999 dopo, zero record preesistenti
  modificati, zero ID cancellati**.
- Verifica indipendente effettuata rigiocando le stesse dieci pagine HTML:
  **18 ID ricostruiti**, senza attribuire orari, coordinate o aperture certe.
- Il codice e le prove essenziali di fonte sono conservati in DEV; gli
  artefatti completi del run GitHub Actions hanno una retention limitata.

## Inventario della scansione completa locale

Sulla macchina `BOOK-V1KQL7L6GB` lo snapshot Happings ha
**2.313 documenti** processati: 106 pagine di mercati settimanali,
2.207 dettagli evento, 8.053 righe negli indici, 281 dettagli classificati
come mercati. La scansione locale ha archiviato per ogni URL i fatti estratti,
lo SHA-256 della pagina HTML di origine e la data della lettura.

È stato generato un backup ZIP deterministico e verificato:
**2.333 oggetti sorgente/report in 3.537.916 byte compressi**, ripartito in
18 blocchi, con manifest SHA-256 per blocco e per file. Il digest del
checkpoint d'origine è
`9f367aca9f6a35d6eb94d423f0e1a1673b621b20f1651d7210697d819267774f`.

**Attenzione:** il trasferimento del backup binario compresso a GitHub è
stato bloccato dai controlli della connessione nel tentativo del
21 ottobre. Non indicare il backup come già disponibile su GitHub, né
cancellare lo snapshot locale sulla base di questo inventario.
La scansione locale pesa meno di 3 MB; gran parte dello spazio occupato
proviene dai cloni temporanei usati nell'analisi, non dai dati Happings.

## Politica permanente

- Niente Git LFS, Storage/Actions a pagamento, acquisto di capacità
  o pubblicazione sulla produzione.
- Usare il repository DEV e la pipeline già autorizzata per codice e
  catalogo. Conservare i risultati storici senza far crescere Git
  indefinitamente con snapshot completi identici ogni giorno.
- Prima di cancellare un archivio, verificare da GitHub una copia
  ricostruibile e confrontare dimensione, SHA-256 globale, SHA-256 di
  ciascun elemento e numero di pagine.
- Non pubblicare percorsi di Windows, account personali, log, token o
  altri metadati del dispositivo.
- Il catalogo DEV e il backup delle pagine d'origine sono due oggetti
  differenti: i 13.999 record su GitHub non costituiscono di per sé
  il backup integrale dei 2.313 file della scansione originale.
