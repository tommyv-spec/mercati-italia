# Roma Capitale d881: original public captures

These files are unchanged public HTTP responses captured on 20 October 2026.
They are fixtures for the dataset reader, not a current market calendar.
The CSV is stored in a lossless gzip archive to preserve its original
CP1252 encoding and CRLF line endings across checkouts. Its hash below
refers to the decompressed original HTTP bytes.

- Metadata: `https://dati.comune.roma.it/catalog/api/3/action/package_show?id=e2e30174-ba7f-4319-bf4a-c13f80278c0c`
- Selected CSV: `https://dati.comune.roma.it/catalog/it/dataset/e2e30174-ba7f-4319-bf4a-c13f80278c0c/resource/cd515283-3079-42fe-a066-ced11b9a8387/download/mercati_rionali_agosto_2023.csv`
- Dataset attribution: Roma Capitale, dataset **Mercati Rionali**, d881.
- CSV SHA256: `71b479a7067cfb66249de0d132b311eb7484daec06a462f513da910efb0bf204`.
- Metadata SHA256: `2ab85403fe3fcbbc4faa1ad7e0e695d363946beaf0f04e9435e23d71a76e79de`.
- Exact HTTP read times, MIME types and byte counts are retained in `captures-2026-10-20.json`.

The original metadata declares dataset licence `cc-by-sa` and distribution
licence `https://w3id.org/italia/controlled-vocabulary/licences/A21_CCBY40`.
Both claims are retained separately without replacing one with the other.

The CP1252, semicolon-delimited file contains 1,003 physical data rows:
932 blank rows, 70 market rows, and one municipality-only note. The 70
market rows have `AGGIORNATO` dates in 2021 or 2023. Six weekday clock
pairs, source notes, and row dates must survive parsing. There is no
Sunday field or geolocation in this source. Test mutations of these
fixtures are synthetic and never count as additional live observations.
