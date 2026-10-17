# Campioni limitati — proposte di schema

Solo lettura da una lista chiusa di domini ufficiali. Nessun record pubblicato.
Campi rilevati e corrispondenze sono suggerimenti, non dati verificati.
Fonti strutturate ammesse per probing: **32**; mai osservate: **3**.
Ogni run controlla fino a tre fonti in rotazione, mantenendo uno storico bounded dei soli schemi.

## Fiere e mercati - Comune di Noventa Padovana
- Esito: schema_preview_only
- Formato: CSV
- Campi: NOME, FIERA/MERCATO, ATTIVITA', DATA VALIDITA CONCESSIONE, DATA SCADENZA CONCESSIONE
- Possibili mappature: {"name": ["NOME"], "market_type": ["FIERA/MERCATO"], "concession_period": ["DATA VALIDITA CONCESSIONE", "DATA SCADENZA CONCESSIONE"]}
- Valore dello schema per futuri importatori: concession_registry_without_visit_schedule
- Punti da risolvere: municipality_must_be_validated_from_publisher_context
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.

## Fiere e mercati - Comune di Rovere Veronese
- Esito: schema_preview_only
- Formato: CSV
- Campi: NOME, FIERA/MERCATO, ATTIVITA', DATA VALIDITA CONCESSIONE, DATA SCADENZA CONCESSIONE
- Possibili mappature: {"name": ["NOME"], "market_type": ["FIERA/MERCATO"], "concession_period": ["DATA VALIDITA CONCESSIONE", "DATA SCADENZA CONCESSIONE"]}
- Valore dello schema per futuri importatori: concession_registry_without_visit_schedule
- Punti da risolvere: municipality_must_be_validated_from_publisher_context
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.

## Fiere e mercati - Comune di Nogarole Rocca
- Esito: schema_preview_only
- Formato: CSV
- Campi: NOME, FIERA/MERCATO, ATTIVITA', DATA VALIDITA CONCESSIONE, DATA SCADENZA CONCESSIONE
- Possibili mappature: {"name": ["NOME"], "market_type": ["FIERA/MERCATO"], "concession_period": ["DATA VALIDITA CONCESSIONE", "DATA SCADENZA CONCESSIONE"]}
- Valore dello schema per futuri importatori: concession_registry_without_visit_schedule
- Punti da risolvere: municipality_must_be_validated_from_publisher_context
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.
