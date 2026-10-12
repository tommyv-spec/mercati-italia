# Campioni limitati — proposte di schema

Solo lettura da una lista chiusa di domini ufficiali. Nessun record pubblicato.
Campi rilevati e corrispondenze sono suggerimenti, non dati verificati.
Fonti strutturate ammesse per probing: **26**; mai osservate: **13**.
Ogni run controlla fino a tre fonti in rotazione, mantenendo uno storico bounded dei soli schemi.

## Fiere e mercati - Comune di Marcon
- Esito: schema_preview_only
- Formato: CSV
- Campi: NOME, FIERA/MERCATO, ATTIVITA', DATA VALIDITA CONCESSIONE, DATA SCADENZA CONCESSIONE
- Possibili mappature: {"name": ["NOME"], "market_type": ["FIERA/MERCATO"], "concession_period": ["DATA VALIDITA CONCESSIONE", "DATA SCADENZA CONCESSIONE"]}
- Valore dello schema per futuri importatori: concession_registry_without_visit_schedule
- Punti da risolvere: municipality_must_be_validated_from_publisher_context
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.

## Censimento dei mercati quindicinali
- Esito: schema_preview_only
- Formato: CSV
- Campi: comune, provincia, anno, mercati, totale, attivazioni, cessazioni, posteggi, alimentare_totale, alimentare_attivazioni, alimentare_cessazioni, nonalimentare_totale, nonalimentare_attivazioni, nonalimentare_cessazioni, produttori_totale, produttori_attivazioni, produttori_cessazioni
- Possibili mappature: {"municipality": ["comune"], "statistics_year": ["anno"], "statistics_count": ["mercati", "attivazioni", "cessazioni"]}
- Valore dello schema per futuri importatori: historical_aggregate_not_venues
- Punti da risolvere: explicit_market_name_missing
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.

## Fiere e mercati - Comune di Povegliano Veronese
- Esito: schema_preview_only
- Formato: CSV
- Campi: NOME, FIERA/MERCATO, ATTIVITA', DATA VALIDITA CONCESSIONE, DATA SCADENZA CONCESSIONE
- Possibili mappature: {"name": ["NOME"], "market_type": ["FIERA/MERCATO"], "concession_period": ["DATA VALIDITA CONCESSIONE", "DATA SCADENZA CONCESSIONE"]}
- Valore dello schema per futuri importatori: concession_registry_without_visit_schedule
- Punti da risolvere: municipality_must_be_validated_from_publisher_context
- Verifiche obbligatorie: licenza, schema completo, ID stabili, date attuali, dedup.
