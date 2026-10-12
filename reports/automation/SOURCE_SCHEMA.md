# Campioni limitati — proposte di schema

Solo lettura da una lista chiusa di domini ufficiali. Nessun record pubblicato.
Campi rilevati e corrispondenze sono suggerimenti, non dati verificati.
Fonti strutturate ammesse per probing: **26**; mai osservate: **19**.
Ogni run controlla fino a tre fonti in rotazione, mantenendo uno storico bounded dei soli schemi.

## Fiere e mercati - Comune di Badia Polesine
- Esito: schema_preview_only
- Formato: CSV
- Campi: NOME, FIERA/MERCATO, ATTIVITA', DATA VALIDITA CONCESSIONE, DATA SCADENZA CONCESSIONE
- Possibili mappature: {"name": ["NOME"], "market_type": ["FIERA/MERCATO"], "concession_period": ["DATA VALIDITA CONCESSIONE", "DATA SCADENZA CONCESSIONE"]}
- Valore dello schema per futuri importatori: concession_registry_without_visit_schedule
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

## Fiere e mercati - Comune di Lazise
- Esito: schema_preview_only
- Formato: CSV
- Campi: NOME, FIERA/MERCATO, ATTIVITA', DATA VALIDITA CONCESSIONE, DATA SCADENZA CONCESSIONE
- Possibili mappature: {"name": ["NOME"], "market_type": ["FIERA/MERCATO"], "concession_period": ["DATA VALIDITA CONCESSIONE", "DATA SCADENZA CONCESSIONE"]}
- Valore dello schema per futuri importatori: concession_registry_without_visit_schedule
- Punti da risolvere: municipality_must_be_validated_from_publisher_context
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.
