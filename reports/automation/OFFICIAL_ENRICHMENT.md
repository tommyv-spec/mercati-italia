# Official source enrichment — legacy cards

Existing venues can receive published hours through exact street/day joins.
Missing venues additionally require a unique municipality/province/weekday
identity across the complete raw dataset, including nonimported competitors.
Coordinates can veto a join; they never establish market identity.
No forecast, human verification, original source, or identity changed.

- Held official rows screened: **1360**
- Existing market cards with added information: **366**
- Missing hours supplied from official regional source: **245**
- Missing/vague venues supplied from the complete source: **223**
- Managed venues updated from the same source ID: **0**
- Official source attributions attached: **245**
- addresses_added: 223
- exact_matches: 143
- existing_hours_preserved: 121
- field_observation_records_updated: 366
- held_unique_town_coordinates_conflict: 62
- held_unique_town_multiple_eligible_sources: 10
- held_unique_town_no_eligible_source: 410
- held_unique_town_raw_same_city_day_competitor: 4
- held_unique_town_raw_unknown_weekday_competitor: 11
- held_unique_town_target_identity_incomplete: 60
- hours_added: 245
- municipality_day_unique_matches: 223
- observed_spelling_matches: 22
- official_source_attributions_added: 245
- recurrence_observations_added: 223
- skipped_coordinates_conflict: 18
- skipped_legacy_without_explicit_annual_weekday: 253
- skipped_market_type_unproved_or_conflicting: 2
- skipped_multiple_official_markets_same_venue_day: 1
- skipped_no_exact_legacy_market: 638
- skipped_no_exact_location_or_day: 548
- skipped_official_raw_identity_unproved_or_conflicting: 56
- skipped_official_without_explicit_annual_weekday: 523
- skipped_province_conflict: 5
- unique_town_targets_screened: 780
- vague_addresses_replaced: 18

## Example exact matches

- mercato-settimanale-di-calusco-d-adda-calusco-d-adda ← 101240 (hours added: False, venue distance: 0.04 km)
- mercato-settimanale-di-calusco-d-adda-calusco-d-adda-sabato ← 101240 (hours added: False, venue distance: 0.04 km)
- mercato-settimanale-di-castel-d-ario-castel-d-ario ← 100641 (hours added: False, venue distance: 0.209 km)
- mercato-settimanale-di-castel-d-ario-castel-d-ario-domenica ← 100641 (hours added: False, venue distance: 0.209 km)
- mercato-settimanale-di-castiglione-d-adda-castiglione-d-adda ← 100755 (hours added: False, venue distance: 0.05 km)
- mercato-settimanale-di-castiglione-d-adda-castiglione-d-adda-giovedi ← 100755 (hours added: False, venue distance: 0.05 km)
- mercato-settimanale-di-paderno-d-adda-paderno-d-adda ← 100843 (hours added: False, venue distance: 0.176 km)
- mercato-settimanale-di-paderno-d-adda-paderno-d-adda-giovedi ← 100843 (hours added: False, venue distance: 0.176 km)
- mercato-settimanale-di-vezza-d-oglio-vezza-d-oglio ← 101187 (hours added: False, venue distance: 0.022 km)
- mercato-settimanale-di-vezza-d-oglio-vezza-d-oglio-giovedi ← 101187 (hours added: False, venue distance: 0.022 km)
- mercato-settimanale-di-abbiategrasso-abbiategrasso-sabato ← 100331 (hours added: False, venue distance: 0.392 km)
- mercato-settimanale-di-albavilla-albavilla-martedi ← 530068 (hours added: True, venue distance: 0.203 km)
- mercato-settimanale-di-albizzate-albizzate ← 100001 (hours added: False, venue distance: 0.077 km)
- mercato-settimanale-di-albizzate-albizzate-martedi ← 100001 (hours added: False, venue distance: 0.077 km)
- mercato-settimanale-di-almenno-san-salvatore-almenno-san-salvatore ← 101200 (hours added: False, venue distance: 0.107 km)
- mercato-settimanale-di-almenno-san-salvatore-almenno-san-salvatore-sabato ← 101200 (hours added: False, venue distance: 0.107 km)
- mercato-settimanale-di-angolo-terme-angolo-terme ← 101002 (hours added: False, venue distance: 0.035 km)
- mercato-settimanale-di-angolo-terme-angolo-terme-martedi ← 101002 (hours added: False, venue distance: 0.035 km)
- mercato-settimanale-di-arsago-seprio-arsago-seprio ← 100004 (hours added: False, venue distance: 0.097 km)
- mercato-settimanale-di-arsago-seprio-arsago-seprio-mercoledi ← 100004 (hours added: False, venue distance: 0.097 km)
- mercato-settimanale-di-artogne-artogne-venerdi ← 101003 (hours added: False, venue distance: 0.061 km)
- mercato-settimanale-di-azzano-mella-azzano-mella ← 530031 (hours added: False, venue distance: 0.339 km)
- mercato-settimanale-di-azzano-mella-azzano-mella-venerdi ← 530031 (hours added: False, venue distance: 0.339 km)
- mercato-settimanale-di-bagnolo-mella-bagnolo-mella ← 101005 (hours added: False, venue distance: None km)
- mercato-settimanale-di-bagnolo-mella-bagnolo-mella-sabato ← 101005 (hours added: False, venue distance: None km)
- mercato-settimanale-di-barbariga-barbariga ← 101008 (hours added: False, venue distance: 0.022 km)
- mercato-settimanale-di-barbariga-barbariga-martedi ← 101008 (hours added: False, venue distance: 0.022 km)
- mercato-settimanale-di-bareggio-bareggio-giovedi ← 100337 (hours added: False, venue distance: 0.139 km)
- mercato-settimanale-di-berbenno-di-valtellina-berbenno-di-valtellina ← 100111 (hours added: False, venue distance: 0.184 km)
- mercato-settimanale-di-berbenno-di-valtellina-berbenno-di-valtellina-lunedi ← 100111 (hours added: False, venue distance: 0.184 km)
