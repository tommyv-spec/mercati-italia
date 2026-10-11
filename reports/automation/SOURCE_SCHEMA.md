# Campioni limitati — proposte di schema

Solo lettura da una lista chiusa di domini ufficiali. Nessun record pubblicato.
Campi rilevati e corrispondenze sono suggerimenti, non dati verificati.

## Mercati e fiere
- Esito: schema_preview_only
- Formato: JSON
- Campi: denominazione, tipologia, tipologia_mercato, ubicazione, specializzazione, numero_posteggi, numero_chioschi_alimentari, numero_chioschi_non_alimentari, numero_chioschi_misti, numero_chioschi_prodotti_agricoli, giorni_svolgimento, orario_svolgimento, nome_quartiere, nome_zona, area_statistica, codice_area_statistica, codice_quartiere, codice_zona, long, lat, geopoint, zona_pross
- Possibili mappature: {"name": ["denominazione", "tipologia_mercato", "nome_quartiere", "nome_zona"], "address": ["ubicazione"], "weekday": ["giorni_svolgimento"], "hours": ["orario_svolgimento"], "latitude": ["lat"]}
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.

## Mercati su aree pubbliche
- Esito: schema_preview_only
- Formato: JSON
- Campi: codice_id, istat_provincia, despro, istat, descom, ubicazione, indirizzi, periodicita_tipo, giorno, mesi_svolgimento, dalle_ore_invernale, alle_ore_invernale, dalle_ore_estivo, alle_ore_estivo, anno_istituzione_mercato, n_post_alim, n_post_non_alim, n_post_tot, sup_post_non_alim, sup_post_alim, sup_post_tot, postdestprodtiplomb, postdestprodagric, postdestbattitori
- Possibili mappature: {"name": ["anno_istituzione_mercato"], "address": ["ubicazione"], "municipality": ["descom"], "weekday": ["periodicita_tipo", "giorno"]}
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.

## Dati sui Mercati Rionali
- Esito: schema_preview_only
- Formato: CSV
- Campi: Municipio, Nome_Mercato, INDIRIZZO, Civico, Esp_Civico, Altre_indicazioni, CAP, TIPOLOGIA, Note_mercato, POSTEGGI_TOTALI, POSTEGGI_OCCUPATI, NUMERO_OPERATORI, POSTEGGI_ALIMENTARI, POSTEGGI_NON_ALIMENTARI, Apertura_Lunedi, Chiusura_Lunedi, Apertura_Martedi, Chiusura_Martedi, Apertura_Mercoledi, Chiusura_Mercoledi, Apertura_Giovedi, Chiusura_Giovedi, Apertura_Venedi, Chiusura_Venedi
- Possibili mappature: {"name": ["Nome_Mercato", "Note_mercato"], "address": ["INDIRIZZO"], "municipality": ["Municipio"], "hours": ["Apertura_Lunedi", "Chiusura_Lunedi", "Apertura_Martedi", "Chiusura_Martedi", "Apertura_Mercoledi", "Chiusura_Mercoledi"]}
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.
