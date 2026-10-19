# Campioni limitati — proposte di schema

Solo lettura da una lista chiusa di domini ufficiali. Nessun record pubblicato.
Campi rilevati e corrispondenze sono suggerimenti, non dati verificati.
Fonti strutturate ammesse per probing: **32**; mai osservate: **0**.
Ogni run controlla fino a tre fonti in rotazione, mantenendo uno storico bounded dei soli schemi.

## Fiere e mercati - Comune di Brendola
- Esito: schema_preview_only
- Formato: CSV
- Campi: NOME, FIERA/MERCATO, ATTIVITA', DATA VALIDITA CONCESSIONE, DATA SCADENZA CONCESSIONE
- Possibili mappature: {"name": ["NOME"], "market_type": ["FIERA/MERCATO"], "concession_period": ["DATA VALIDITA CONCESSIONE", "DATA SCADENZA CONCESSIONE"]}
- Valore dello schema per futuri importatori: concession_registry_without_visit_schedule
- Punti da risolvere: municipality_must_be_validated_from_publisher_context
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.

## Dati sui Mercati Rionali
- Esito: schema_preview_only
- Formato: CSV
- Campi: Municipio, Nome_Mercato, INDIRIZZO, Civico, Esp_Civico, Altre_indicazioni, CAP, TIPOLOGIA, Note_mercato, POSTEGGI_TOTALI, POSTEGGI_OCCUPATI, NUMERO_OPERATORI, POSTEGGI_ALIMENTARI, POSTEGGI_NON_ALIMENTARI, Apertura_Lunedi, Chiusura_Lunedi, Apertura_Martedi, Chiusura_Martedi, Apertura_Mercoledi, Chiusura_Mercoledi, Apertura_Giovedi, Chiusura_Giovedi, Apertura_Venedi, Chiusura_Venedi
- Possibili mappature: {"name": ["Nome_Mercato"], "address": ["INDIRIZZO"], "district": ["Municipio"], "hours": ["Apertura_Lunedi", "Chiusura_Lunedi", "Apertura_Martedi", "Chiusura_Martedi", "Apertura_Mercoledi", "Chiusura_Mercoledi"], "market_type": ["TIPOLOGIA"], "notes": ["Altre_indicazioni", "Note_mercato"]}
- Valore dello schema per futuri importatori: venue_inventory_missing_visit_days
- Punti da risolvere: municipality_must_be_validated_from_publisher_context
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.

## Censimento dei mercati giornalieri
- Esito: needs_review
- Formato: CSV
- Campi: 
- Possibili mappature: {}
- Valore dello schema per futuri importatori: da controllare
- Punti da risolvere: 
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.
