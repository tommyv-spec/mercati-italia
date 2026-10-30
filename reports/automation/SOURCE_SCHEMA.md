# Campioni limitati — proposte di schema

Solo lettura da una lista chiusa di domini ufficiali. Nessun record pubblicato.
Campi rilevati e corrispondenze sono suggerimenti, non dati verificati.
Fonti strutturate ammesse per probing: **33**; mai osservate: **0**.
Ogni run controlla fino a tre fonti in rotazione, mantenendo uno storico bounded dei soli schemi.

## Posteggi mercati e fiere - Comune di Sarego
- Esito: schema_preview_only
- Formato: CSV
- Campi: NOME, FIERA/MERCATO, GIORNO, INIZIO PERIODO, FINE PERIODO, TIPO POSTEGGIO, TOTALE POSTEGGI
- Possibili mappature: {"name": ["NOME"], "weekday": ["GIORNO"], "market_type": ["FIERA/MERCATO"]}
- Valore dello schema per futuri importatori: manual_schema_review_required
- Punti da risolvere: municipality_must_be_validated_from_publisher_context
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.

## Censimento dei mercati itineranti
- Esito: schema_preview_only
- Formato: CSV
- Campi: comune, provincia, anno, totale, attivazioni, cessazioni, alimentare_totale, alimentare_attivazioni, alimentare_cessazioni, nonalimentare_totale, nonalimentare_attivazioni, nonalimentare_cessazioni, produttori_totale, produttori_attivazioni, produttori_cessazioni
- Possibili mappature: {"municipality": ["comune"], "statistics_year": ["anno"], "statistics_count": ["attivazioni", "cessazioni"]}
- Valore dello schema per futuri importatori: manual_schema_review_required
- Punti da risolvere: explicit_market_name_missing
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.

## Dati sui Mercati Rionali
- Esito: schema_preview_only
- Formato: CSV
- Campi: Municipio, Nome_Mercato, INDIRIZZO, Civico, Esp_Civico, Altre_indicazioni, CAP, TIPOLOGIA, Note_mercato, POSTEGGI_TOTALI, POSTEGGI_OCCUPATI, NUMERO_OPERATORI, POSTEGGI_ALIMENTARI, POSTEGGI_NON_ALIMENTARI, Apertura_Lunedi, Chiusura_Lunedi, Apertura_Martedi, Chiusura_Martedi, Apertura_Mercoledi, Chiusura_Mercoledi, Apertura_Giovedi, Chiusura_Giovedi, Apertura_Venedi, Chiusura_Venedi
- Possibili mappature: {"name": ["Nome_Mercato"], "address": ["INDIRIZZO"], "district": ["Municipio"], "hours": ["Apertura_Lunedi", "Chiusura_Lunedi", "Apertura_Martedi", "Chiusura_Martedi", "Apertura_Mercoledi", "Chiusura_Mercoledi"], "market_type": ["TIPOLOGIA"], "notes": ["Altre_indicazioni", "Note_mercato"]}
- Valore dello schema per futuri importatori: venue_inventory_missing_visit_days
- Punti da risolvere: municipality_must_be_validated_from_publisher_context
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.
