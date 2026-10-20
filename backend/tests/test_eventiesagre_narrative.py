"""Minimal synthetic structures matching the independently captured EES DOM.

These are parser fixtures, not original publisher HTML or proof of a live read.
The captured-byte replay and its hashes are recorded separately in the audit.
"""
from copy import deepcopy
from datetime import date
from pathlib import Path
import sys
import unittest

BACKEND = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(BACKEND), str(Path(__file__).resolve().parent)]
from test_eventiesagre_source_layout import html as source_html, URL
from test_eventiesagre_detail_refresh import row
from eventiesagre_source_layout import parse_eventiesagre_html
from eventiesagre_detail_refresh import parse_document, preview, verify_exported
from editorial_calendar_scope import KEY, clean_editorial_evidence, valid_editorial_reported_dates
from export_static import normalize

TODAY = date(2026, 10, 20)


def html(body, **changes):
    defaults = {"body": body, "hours": "", "address": "", "start": "19/06/2026",
                "end": "21/06/2026", "archived": True}
    defaults.update(changes)
    return source_html(**defaults)


def parse(body, **changes):
    return parse_eventiesagre_html(html(body, **changes), URL, today=TODAY)


def listing(*rows):
    return '<p><strong>ORARI</strong></p><ul>' + ''.join('<li>' + v + '</li>' for v in rows) + '</ul>'


class NarrativeLayoutTests(unittest.TestCase):
    def test_utility_heading_where_prose_and_list_preserve_the_date_clock_binding(self):
        result = parse('<p><strong>INFORMAZIONI UTILI</strong></p>'
            '<p><strong>DOVE SI TIENE L’EVENTO</strong> – Mercato Di Esempio sarà ospitato '
            'nel centro di Esempio, in Via S. Boagno.</p>' + listing(
                'Venerdì 19 giugno dalle 18.00 alle 24.00',
                'Sabato 20 giugno dalle 18.00 alle 24.00',
                'Domenica 21 giugno dalle 18.00 alle 24.00'))
        self.assertEqual(result['legacy_fields']['indirizzo'], 'Via S. Boagno')
        self.assertEqual(result['legacy_fields']['orario_raw'], '')
        self.assertEqual([(v['date'], v['start_time'], v['end_time']) for v in result['explicit_occurrences']],
            [('2026-06-19', '18:00', '24:00'), ('2026-06-20', '18:00', '24:00'), ('2026-06-21', '18:00', '24:00')])
        self.assertEqual(result['issues'], [])
        self.assertIn('li:nth-of-type(2)', result['explicit_occurrences'][1]['evidence'][0])
        self.assertTrue(result['edition_is_past'])

    def test_standalone_label_accepts_colon_and_explicit_year(self):
        result = parse('<h4>Orari:</h4><p>Venerdì 19 giugno 2026 dalle 18 alle 24</p>')
        self.assertEqual(result['explicit_occurrences'][0]['date'], '2026-06-19')

    def test_split_day_header_and_opening_closed_intervals_are_not_flattened(self):
        result = parse('<p>Sabato 20 e domenica 21 giugno:<br>'
            '10:00 - 15:00 ingresso libero<br>15.00 - 16.00: chiusura fiera per riallestimento<br>'
            '16.00 - 24.00: ingresso a pagamento</p>')
        self.assertEqual(len(result['explicit_occurrences']), 4)
        self.assertNotIn('narrative_calendar_incomplete', result['issues'])
        self.assertTrue(any('chiusura' in v for v in result['hours_qualifications']))
        self.assertFalse(any(v['start_time'] == '15:00' for v in result['explicit_occurrences']))

    def test_adjacent_inline_weekday_after_midnight_preserves_two_rows(self):
        result = parse('<p>SABATO 30 SETTEMBRE DALLE ORE 18:00 ALLE ORE 00:00'
            'DOMENICA 1 OTTOBRE DALLE ORE 10:00 ALLE ORE 23:30</p>',
            start='30/09/2017', end='01/10/2017', hours='dalle ore 10:00 alle ore 23:55')
        self.assertEqual([(v['date'], v['end_time']) for v in result['explicit_occurrences']],
            [('2017-09-30', '00:00'), ('2017-10-01', '23:30')])
        self.assertIn('visible_hours_conflict', result['issues'])
        self.assertEqual(result['legacy_fields']['orario_raw'], '')

    def test_named_edition_lead_outside_the_card_is_a_conflict_not_a_new_date(self):
        blob = html('<p>FIERA DEL VINO DI ESEMPIO 29/30/31 MAGGIO 1/2 GIUGNO 2026</p>'
            '<p>Venerdì 29 maggio: 18:00 - 24:00 ingresso a pagamento</p>',
            start='29/05/2026', end='01/06/2026', hours='dalle ore 10:00')
        blob = blob.replace(b'Mercato Di Esempio', b'Fiera Del Vino A Esempio')
        result = parse_eventiesagre_html(blob, URL, today=TODAY)
        self.assertIn('visible_edition_conflict', result['issues'])
        self.assertIn('visible_hours_conflict', result['issues'])
        self.assertFalse(any(v['date'] == '2026-06-02' for v in result['explicit_occurrences']))

    def test_overlapping_unlabelled_continuation_is_held_for_that_day(self):
        result = parse('<p>Venerdì 19 giugno: 18:00 - 24:00 ingresso a pagamento<br>'
                       '10:00 - 15:00 ingresso libero<br>16:00 - 24:00 ingresso a pagamento</p>')
        self.assertEqual(result['explicit_occurrences'], [])
        self.assertIn('visible_hours_conflict', result['issues'])
        self.assertIn('narrative_calendar_incomplete', result['issues'])

    def test_footer_related_and_nested_footer_never_supply_narrative_fields(self):
        body = '<footer><p>Dove: Via Falsa, 9</p>' + listing('Venerdì 19 giugno dalle 8 alle 13') + '</footer>'
        result = parse(body)
        self.assertEqual(result['legacy_fields']['indirizzo'], '')
        self.assertEqual(result['explicit_occurrences'], [])

    def test_contacts_programme_and_concert_heading_stop_scope(self):
        for heading in ('Contatti', 'Concerti', 'Laboratori', 'Programma e menù:', 'Dove dormire'):
            with self.subTest(heading=heading):
                result = parse('<h4>' + heading + '</h4><p>Dove: Via Accessoria, 9</p>' +
                    listing('Venerdì 19 giugno dalle 8 alle 13'))
                self.assertEqual(result['legacy_fields']['indirizzo'], '')
                self.assertEqual(result['explicit_occurrences'], [])
                old_labels = parse('<h4>' + heading + '</h4><p>Indirizzo: Via Accessoria, 9</p>'
                                   '<p>Orario: dalle 8 alle 13</p>')
                self.assertEqual(old_labels['legacy_fields']['indirizzo'], '')
                self.assertEqual(old_labels['legacy_fields']['orario_raw'], '')

    def test_activity_sentence_cannot_override_the_market_clock_or_venue(self):
        for text in ('Venerdì 19 giugno dalle 18 alle 20 concerto',
                     'Venerdì 19 giugno dalle 18 alle 20 laboratorio bambini',
                     'Venerdì 19 giugno dalle 18 alle 20 degustazione guidata'):
            result = parse('<p>' + text + '</p><p>DOVE SI TIENE L’EVENTO – '
                           'Il laboratorio si tiene a Esempio, in Via Accessoria, 9.</p>',
                           hours='dalle 8 alle 13')
            self.assertEqual(result['legacy_fields']['indirizzo'], '')
            self.assertEqual(result['legacy_fields']['orario_raw'], '08:00–13:00')
            self.assertEqual(result['explicit_occurrences'], [])

    def test_prose_location_requires_the_observed_city_and_a_primary_event(self):
        for prose in ('Il mercato si tiene ad Altrove, in Via Accessoria, 9.',
                      'Il ristorante a Esempio si trova in Via Accessoria, 9.'):
            result = parse('<p>DOVE SI TIENE L’EVENTO – ' + prose + '</p>')
            self.assertEqual(result['legacy_fields']['indirizzo'], '')

    def test_direct_where_with_foreign_or_unresolved_locality_is_held(self):
        for address in ('Via Roma, Altrove', 'Via Roma a Altrove', 'Via Roma, 99999 Altrove',
                        'Via Roma - Altrove', 'Via Roma (Altrove)'):
            with self.subTest(address=address):
                result = parse('<p>Dove: ' + address + '</p>')
                self.assertEqual(result['legacy_fields']['indirizzo'], '')
                self.assertIn('visible_address_conflict', result['issues'])
                self.assertEqual(parse('<p>Dove: ' + address + '</p>', address='Via Fonte, 1')
                    ['legacy_fields']['indirizzo'], '')
        for address, expected in (('Via Roma', 'Via Roma'), ('Via Milano', 'Via Milano'),
                                  ('Via Roma, 4/c', 'Via Roma, 4/c'),
                                  ('Via Roma a Esempio', 'Via Roma'), ('Via Roma, Esempio', 'Via Roma')):
            with self.subTest(address=address):
                self.assertEqual(parse('<p>Dove: ' + address + '</p>')['legacy_fields']['indirizzo'], expected)

    def test_secondary_utility_heading_does_not_reopen_primary_scope(self):
        result = parse(listing('Venerdì 19 giugno dalle 18 alle 24') + '<h4>Concerti</h4>'
            '<p>INFORMAZIONI UTILI</p><p>Dove: Via Accessoria, 9</p>' +
            listing('Sabato 20 giugno dalle 21 alle 24'))
        self.assertEqual(result['legacy_fields']['indirizzo'], '')
        self.assertEqual([v['date'] for v in result['explicit_occurrences']], ['2026-06-19'])

    def test_conflicting_or_multiple_labelled_streets_are_not_selected(self):
        result = parse('<p>Dove: Via Nuova, 9</p>', address='Via Esistente, 1')
        self.assertEqual(result['legacy_fields']['indirizzo'], '')
        self.assertIn('visible_address_conflict', result['issues'])
        result = parse('<p>Dove: Via Nuova e Piazza Altra</p>')
        self.assertEqual(result['legacy_fields']['indirizzo'], '')
        self.assertIn('visible_address_conflict', result['issues'])

    def test_missing_day_month_or_edition_year_never_uses_read_year(self):
        for text, changes in (
            ('dalle 18 alle 24', {}), ('Venerdì dalle 18 alle 24', {}),
            ('Venerdì 19 dalle 18 alle 24', {}),
            ('Venerdì 19 giugno dalle 18 alle 24', {'start': '', 'end': ''}),
            ('Venerdì 19 giugno dalle 18 alle 24', {'start': '01/12/2025', 'end': '30/06/2026'}),
        ):
            with self.subTest(text=text, changes=changes):
                result = parse(listing(text), **changes)
                self.assertEqual(result['explicit_occurrences'], [])

    def test_wrong_weekday_invalid_day_range_and_out_of_edition_date_are_held(self):
        for text in ('Venerdì 20 giugno dalle 18 alle 24',
                     'Venerdì 31 giugno dalle 18 alle 24',
                     'Venerdì 19-21 giugno dalle 18 alle 24',
                     'Lunedì 22 giugno dalle 18 alle 24'):
            with self.subTest(text=text):
                result = parse(listing(text))
                self.assertEqual(result['explicit_occurrences'], [])
                self.assertTrue({'visible_edition_conflict', 'narrative_calendar_incomplete'} & set(result['issues']))

    def test_partial_list_is_not_complete_and_duplicates_do_not_multiply_days(self):
        result = parse(listing('Venerdì 19 giugno dalle 18 alle 24',
            'Venerdì 19 giugno dalle 18 alle 24', 'Sabato 20 giugno dalle 18'))
        self.assertEqual(len(result['explicit_occurrences']), 1)
        self.assertIn('narrative_calendar_incomplete', result['issues'])

    def test_next_list_item_without_a_date_cannot_inherit_the_previous_day(self):
        for tail in ('Sabato dalle 18 alle 24', 'dalle 10 alle 15', 'Orario da definire',
                     'Sabato 20 giugno dalle 18 alle 20 concerto'):
            with self.subTest(tail=tail):
                result = parse(listing('Venerdì 19 giugno dalle 18 alle 24', tail))
                self.assertEqual(len(result['explicit_occurrences']), 1)
                self.assertIn('narrative_calendar_incomplete', result['issues'])

    def test_page_wide_dated_schedule_is_not_assigned_to_multiple_market_venues(self):
        result = parse('<p>Luogo: Via Prima</p><p>Giorni di svolgimento: Venerdì</p>'
            '<p>Orario: dalle 8 alle 13</p><p>Luogo: Via Seconda</p>'
            '<p>Giorni di svolgimento: Sabato</p><p>Orario: dalle 9 alle 14</p>' +
            listing('Venerdì 19 giugno dalle 8 alle 13', 'Sabato 20 giugno dalle 9 alle 14'))
        self.assertEqual(len(result['source_rows']), 2)
        self.assertEqual(result['explicit_occurrences'], [])
        self.assertIn('narrative_calendar_incomplete', result['issues'])


class NarrativeBridgeTests(unittest.TestCase):
    def document(self, body, **changes):
        blob = html(body, **changes).replace(b'Esempio', b'Bologna')
        return {'read_on': TODAY.isoformat(), 'parsed': parse_document(blob, requested_url=URL, today=TODAY)}

    def test_historical_source_keeps_precise_facts_without_refreshing_current_fields(self):
        observed = self.document('<p>Dove: Via Fonte, 9</p>' + listing(
            'Venerdì 19 giugno dalle 18 alle 24', 'Sabato 20 giugno dalle 18 alle 24'))
        original = row()
        actual, report = preview([original], [observed], today=TODAY)
        self.assertEqual(actual[0]['indirizzo'], '')
        self.assertEqual(actual[0]['orario_testo'], '')
        self.assertEqual(actual[0][KEY]['facts']['location']['address'], 'Via Fonte, 9')
        self.assertEqual(len(actual[0][KEY]['facts']['occurrences']), 2)
        self.assertEqual(actual[0]['date'], [])
        self.assertEqual(actual[0][KEY]['calendar_mode'], 'limit_forecasts')
        self.assertEqual(actual[0]['fonte_aggiornata_il'], original['fonte_aggiornata_il'])
        self.assertNotIn('riscontri_campi', actual[0])
        normalized, _ = normalize(actual[0], today=TODAY)
        self.assertEqual(normalized[KEY], actual[0][KEY])
        self.assertTrue(verify_exported([normalized], report, today=TODAY)['release_safe'])

    def test_current_explicit_days_roundtrip_with_per_day_hours_and_no_global_hours(self):
        observed = self.document(listing('Venerdì 23 ottobre dalle 18 alle 24',
            'Sabato 24 ottobre dalle 10 alle 15'), start='23/10/2026', end='24/10/2026', archived=False)
        actual, report = preview([row()], [observed], today=TODAY)
        self.assertEqual(actual[0]['date'], ['2026-10-23', '2026-10-24'])
        self.assertEqual(actual[0]['date_quality'], 'riportata')
        self.assertEqual(actual[0]['orario_testo'], '')
        self.assertTrue(valid_editorial_reported_dates(actual[0], today=TODAY))
        self.assertTrue(clean_editorial_evidence(actual[0][KEY], actual[0], today=TODAY))
        normalized, _ = normalize(actual[0], today=TODAY)
        self.assertTrue(verify_exported([normalized], report, today=TODAY)['release_safe'])
        forged = deepcopy(actual[0])
        forged['date'].append('2026-10-25')
        self.assertFalse(valid_editorial_reported_dates(forged, today=TODAY))

    def test_incomplete_and_conflicting_narrative_lists_cannot_apply_dates(self):
        for body, hours in (
            (listing('Venerdì 23 ottobre dalle 18 alle 24', 'Sabato 24 ottobre dalle 18'), ''),
            (listing('Venerdì 23 ottobre dalle 18 alle 24'), 'dalle 10 alle 23'),
            (listing('Domenica 25 ottobre dalle 18 alle 24'), ''),
        ):
            with self.subTest(body=body, hours=hours):
                observed = self.document(body, start='23/10/2026', end='24/10/2026',
                                         archived=False, hours=hours)
                self.assertFalse(observed['parsed']['event']['calendar_complete'])
                actual, report = preview([row()], [observed], today=TODAY)
                self.assertNotEqual(actual[0].get('date_quality'), 'riportata')
                self.assertEqual(actual[0]['date'], [])
                self.assertEqual(actual[0]['orario_testo'], '')
                self.assertTrue(verify_exported(actual, report, today=TODAY)['release_safe'])

    def test_existing_unowned_address_and_identity_guards_are_unchanged(self):
        observed = self.document('<p>Dove: Via Nuova, 9</p>' + listing(
            'Venerdì 23 ottobre dalle 18 alle 24'), start='23/10/2026', end='24/10/2026', archived=False)
        for original in (row(indirizzo='Via Esistente, 4'), row(provincia='MI'), row(citta='Altrove')):
            actual, _ = preview([original], [observed], today=TODAY)
            self.assertEqual(actual, [original])


if __name__ == '__main__':
    unittest.main()
