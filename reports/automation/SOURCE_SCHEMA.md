# Campioni limitati — proposte di schema

Solo lettura da una lista chiusa di domini ufficiali. Nessun record pubblicato.
Campi rilevati e corrispondenze sono suggerimenti, non dati verificati.

## Mercati su aree pubbliche
- Esito: schema_preview_only
- Formato: JSON
- Campi: codice_id, istat_provincia, despro, istat, descom, ubicazione, indirizzi, periodicita_tipo, giorno, mesi_svolgimento, dalle_ore_invernale, alle_ore_invernale, dalle_ore_estivo, alle_ore_estivo, anno_istituzione_mercato, n_post_alim, n_post_non_alim, n_post_tot, sup_post_non_alim, sup_post_alim, sup_post_tot, postdestprodtiplomb, postdestprodagric, postdestbattitori
- Possibili mappature: {"address": ["ubicazione", "indirizzi"], "municipality": ["descom"], "weekday": ["periodicita_tipo", "giorno"], "hours": ["dalle_ore_invernale", "alle_ore_invernale", "dalle_ore_estivo", "alle_ore_estivo"], "geometry_requires_crs_review": ["geo_x", "geo_y", "location"], "stable_id_candidate": ["codice_id"]}
- Punti da risolvere: explicit_market_name_missing, geometry_crs_and_coordinate_units_unknown
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.

## Mercati e fiere
- Esito: schema_preview_only
- Formato: JSON
- Campi: denominazione, tipologia, tipologia_mercato, ubicazione, specializzazione, numero_posteggi, numero_chioschi_alimentari, numero_chioschi_non_alimentari, numero_chioschi_misti, numero_chioschi_prodotti_agricoli, giorni_svolgimento, orario_svolgimento, nome_quartiere, nome_zona, area_statistica, codice_area_statistica, codice_quartiere, codice_zona, long, lat, geopoint, zona_pross
- Possibili mappature: {"name": ["denominazione"], "address": ["ubicazione"], "district": ["nome_quartiere", "nome_zona"], "weekday": ["giorni_svolgimento"], "hours": ["orario_svolgimento"], "latitude": ["lat"], "longitude": ["long"], "geometry_requires_crs_review": ["geopoint"], "market_type": ["tipologia", "tipologia_mercato"]}
- Punti da risolvere: municipality_must_be_validated_from_publisher_context
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.

## Dati sui Mercati Rionali
- Esito: needs_review
- Formato: CSV
- Campi: 
- Possibili mappature: {}
- Punti da risolvere: 
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.
