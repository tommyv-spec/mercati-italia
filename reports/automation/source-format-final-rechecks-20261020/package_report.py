"""Apply only demonstrated LIVE7 comparisons; original observations remain intact."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
ROOT = Path(__file__).resolve().parents[3]
OUT = Path('/tmp/source-format-final-rechecks-20261020')
DEST = Path(__file__).resolve().parent
MANIFEST = Path('/tmp/vintagery-live-39487468359/candidate/public/data/v1/manifest.json')
CODE = '37f1078c0fdef79a70e20e9ce2e3876b38742f94'
sys.path.insert(0, str(ROOT / 'backend'))
from merge_catalog import load_existing
from source_format_audit import build_report, code_fingerprints, digest, render_checklist

def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):
    return json.loads(Path(path).read_text())
def write(path, value):
    Path(path).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')

ledger_path = ROOT / 'backend/data/source-format-review-ledger.json'
# Reproducible against the unchanged ledger at the fixed reviewed code commit.
ledger = json.loads(subprocess.check_output(['git','-C',str(ROOT),'show',CODE + ':backend/data/source-format-review-ledger.json']))
rows = load_existing(MANIFEST)
baseline = build_report(rows, ledger, today='2026-10-20', repo_root=ROOT)
raw = read(OUT / 'capture-replays.json')
prior_raw = read(OUT / 'prior-capture-replays.json')
raw['raw_captures'].extend(prior_raw['raw_captures'])
raw['results'].update(prior_raw['results'])
raw['capture_counts_by_family'] = dict(Counter(c['family'] for c in raw['raw_captures']))
raw['distinct_response_sha256'] = len({c['sha256'] for c in raw['raw_captures']})
storage = read(OUT / 'storage-comparison.json')
shared = read(OUT / 'shared-replay.json')
assert shared['catalog_records'] == 13888 and shared['static_all_rows_byte_equivalent']
assert len(shared['static_roundtrip']['regional_files_byte_identical']) == 20
assert shared['static_roundtrip']['index_schema'] == 6
# The only changed admission contract function adapts the final index comparison.
contract = 'backend/source_contract_activation.py'
previous_contract = subprocess.check_output(['git','-C',str(ROOT),'show','3a4d5c7:' + contract])
current_contract = (ROOT / contract).read_bytes()
def tree_functions(blob):
    tree = ast.parse(blob)
    return {getattr(node, 'name', '<statement>') + ':' + str(i): ast.dump(node, include_attributes=False)
            for i,node in enumerate(tree.body)}
a, b = tree_functions(previous_contract), tree_functions(current_contract)
changed_functions = sorted(k for k in a.keys() | b.keys() if a.get(k) != b.get(k))
assert len(changed_functions) == 1 and changed_functions[0].startswith('verify_static:')
old_manifest = read(MANIFEST)
new_manifest_path = Path(shared['static_roundtrip']['manifest'])
new_manifest = read(new_manifest_path)
old_index = read(MANIFEST.parent / Path(old_manifest['index']).relative_to('data/v1'))
new_index = read(new_manifest_path.parent / Path(new_manifest['index']).relative_to('data/v1'))
old_values = {r[0]: r for r in old_index['markets']}
new_values = {r[0]: r for r in new_index['markets']}
assert set(old_values) == set(new_values)
assert all(new_values[k][:12] == old_values[k] for k in old_values)
shared['generic_admission_contract_recomparison'] = {
    'path': contract, 'previous_sha256': hashlib.sha256(previous_contract).hexdigest(),
    'current_sha256': sha(ROOT / contract), 'changed_functions': ['verify_static'],
    'source_acquisition_parsing_identity_and_admission_functions_ast_identical': True,
    'difference': 'Final compact-index validation now uses the declared schema and reference day and checks all supported identities.',
    'all_original_index_fields_equal': len(old_values), 'new_index_schema': 6,
    'index_hours_scopes': dict(Counter(r[12] or 'ordinary' for r in new_values.values())),
    'full_pipeline_reference': 'reports/automation/source-quality-offline-integration-20261020.json',
    'full_pipeline_report_commit': 'f29d1a1', 'full_pipeline_gates_passed': 17}
at = datetime.now(timezone.utc).isoformat()
before_by = {e['format_id']: e for e in ledger['formats']}
baseline_by = {e['format_id']: e for e in baseline['formats'] + baseline['auxiliary_formats']}
changed = {}
for e in ledger['formats']:
    now = code_fingerprints(e.get('code_sha256', {}), ROOT)
    changed[e['format_id']] = {p: {'before': e.get('code_sha256', {}).get(p), 'after': h}
                              for p,h in now.items() if h != e.get('code_sha256', {}).get(p)}
shared_paths = {'backend/export_static.py','backend/field_evidence.py','backend/compact_index.py',
                'backend/field_conflicts.py','backend/source_contract_activation.py'}
shared_only = {ident for ident, paths in changed.items() if paths and (
               set(paths) == {'backend/publisher_refresh.py'} or set(paths) <= shared_paths)}
shared_only.discard('padovatoday.it--a15e8e68ca15')
raw_formats = {c['requested_format_id'] for c in raw['raw_captures']}
raw_formats |= {c['final_format_id'] for c in raw['raw_captures'] if c['family'].startswith('happings')}
source_replayed = {ident for ident in raw_formats if changed.get(ident)}
incomplete_shared = {ident for ident in shared_only if any(
    baseline_by[ident]['checks'][name]['state'] != 'done' for name in ('source_sample','field_mapping'))}
parser_ok = (shared_only - incomplete_shared) | source_replayed
storage_ok = {e['format_id']: e for e in storage['formats'] if e['proposed_storage_reconfirmation']}
assert len(raw['raw_captures']) == 221
assert len(storage_ok) == 16 and storage['kept_pending'] == 7
assert len(shared_only) == 86
updated_ledger = deepcopy(ledger)
updates = []
for entry in updated_ledger['formats']:
    ident = entry['format_id']
    if ident not in parser_ok and ident not in storage_ok:
        continue
    old = deepcopy(entry)
    event = {'at': at, 'kind': 'offline_final_code_and_live7_storage_recomparison',
             'previous_reviewed_at': old.get('reviewed_at'),
             'previous_code_sha256': old.get('code_sha256'),
             'previous_storage_snapshot': old.get('storage_snapshot'),
             'source_reads_relabelled': 0, 'original_source_samples_modified': False,
             'code_commit': CODE, 'catalog_manifest_sha256': sha(MANIFEST),
             'report': 'reports/automation/source-format-final-rechecks-20261020/review.json'}
    if ident in parser_ok:
        basis = ('unchanged_source_parser_and_differential_shared_export_index6_coverage' if ident in shared_only
                 else 'exact_retained_http_format_replay_and_full_live7_catalog_export_index6')
        entry['code_sha256'] = code_fingerprints(entry['code_sha256'], ROOT)
        entry['parser_comparison_basis'] = basis
        entry['checks']['parser_comparison'] = {'state': 'done', 'note': (
            'Compatibilità riconfrontata sul codice finale 37f1078: parser sorgente registrato immutato, '
            'raccordi condivisi e indice schema6 verificati su 13.888 schede. Il solo routing non prova '
            'completezza o attualità dei contenuti. Nessuna nuova lettura. Prova: '
            'source-format-final-rechecks-20261020/shared-replay.json.' if ident in shared_only else
            'Parser rieseguito sui byte HTTP originali conservati di questo formato e sui passaggi osservati, '
            'con associazione al catalogo LIVE7 di 13.888 schede ed export separato schema6. '
            'Acquisizioni originali invariate; ambiti storici e conflitti restano qualificati. Prova: '
            'source-format-final-rechecks-20261020/capture-replays.json.')}
        event['changed_code_paths'] = changed[ident]
        event['parser_basis'] = basis
        entry['last_code_recomparison'] = deepcopy(event)
    if ident in storage_ok:
        item = storage_ok[ident]
        entry['storage_snapshot'] = item['current_snapshot']
        entry['checks']['storage_comparison'] = {'state': 'done', 'note':
            'Fotografia precedente ritrovata con SHA-256 identico; tutte le differenze effettive ricostruite '
            'con la prova ' + item['proof']['kind'] + '. Nessuna nuova acquisizione o conferma di apertura. '
            'Prova: source-format-final-rechecks-20261020/storage-comparison.json.'}
        event['storage_proof'] = item['proof']
        entry['last_storage_recomparison'] = {'at': at, 'previous_snapshot': item['old_snapshot'],
                                            'current_snapshot': item['current_snapshot'], 'proof': item['proof']}
    entry.setdefault('comparison_history', []).append(event)
    entry['reviewed_at'] = at
    assert entry['samples'] == old['samples']
    updates.append(ident)

# A new observed DOM variant is documented explicitly inside its existing URL family.
lucca = read(ROOT / 'reports/automation/happings-lucca-layout-validation-20261020/summary.json')
observed = next(p for p in lucca['source_pages'] if p.get('current_status') == 'parsed_editorial_scopes')
variant = {'variant_id': 'hpe-editorial-local-guide-with-explicit-section-scopes',
    'status': 'sample_replayed_with_qualified_holds',
    'source_hash': observed['sha256'], 'read_on': observed['read_on'], 'read_time_precision': 'day',
    'content_selector': 'main#main article.hpe-editorial--local-guide .hpe-editorial-grid > .hpe-editorial-body',
    'sections': observed['editorial_sections'],
    'acceptance_criteria': [
        'Use only the main editorial body; sidebar, navigation and footer remain excluded.',
        'An explicitly current section may propose ordinary evidence only after existing identity/geography/day guards.',
        'Keep all 53 historical rows as qualified facts; do not promote them into current fields or calendar.',
        'Unknown current market statements, including ul/ol lists, invalidate uniqueness for that section.',
        'Attribute an address conflict only with explicit previous-to-current replacement and a unique whole-catalog identity.',
        'Bind the final conflict guard to the original bounded response bytes and hash, not a self-declared parsed report.',
        'Keep all existing IDs, addresses, coordinates, dates and opening-verification flags unchanged.'],
    'proved_results': {'compared_catalog_rows': 13888, 'linked_catalog_rows_compared': 60,
                      'current_day_locality_units': 3, 'historical_units_held': 53,
                      'explicit_address_conflicts': 2, 'other_catalog_fields_changed': 0,
                      'all_other_weekly_captures_unchanged': 13},
    'remaining_limits': ['Only this observed DOM variant and its explicit section statements were replayed.',
                         'HAPP-FORMAT-04, HAPP-FORMAT-06 and NC-05 retain their broader unfinished requirements.',
                         'The two warning envelopes require the next real DEV run; this check-in is offline.'],
    'evidence': ['reports/automation/happings-lucca-layout-validation-20261020/summary.json',
                 'reports/automation/address-conflict-ui-validation-20261020.json',
                 'reports/automation/source-format-final-rechecks-20261020/capture-replays.json']}
entry = next(e for e in updated_ledger['formats'] if e['format_id'] == 'happings.com--04b85587f84c')
sample = {'id': 'province-editorial-lucca-live-39487468359', 'requested_url': observed['requested_url'],
          'observed_final_url': observed['final_url'], 'acquired_at': observed['read_on'],
          'time_basis': 'day_only_from_original_live_checkpoint', 'state': 'read', 'http_status': None,
          'sha256': observed['sha256'], 'bytes': observed['bytes'], 'hash_basis': 'http_response_bytes',
          'content_reviewed': True, 'layout': {'variant': variant['variant_id'], 'content': variant['content_selector'],
                                              'source_rows': 56, 'section_scopes': {'current': 3, 'historical_unverified': 53}},
          'field_map': {'address': 'Three current locality/day assertions; 53 historical entries cannot enrich current fields.',
                        'hours': '08:00–13:00 explicitly in three current facts; parsed as source facts, not assigned blindly.',
                        'calendar': 'Weekdays are recurrence facts, not explicit opening dates; no dates generated.',
                        'conflicts': 'Explicit old-to-current venue replacement; exactly two uniquely bound warnings.',
                        'page_metadata': 'Editorial publication/modification dates remain distinct from reading and market confirmation.'},
          'transport_limit': 'Actual requested/final response URLs saved; intermediate redirect status codes were not retained.',
          'layout_transition': {'observed_format_id': 'happings.com--311686cb6f8d',
                                'basis': 'observed_http_redirect',
                                'note': 'Final HTTP response URL is recorded separately from the requested legacy URL; no intermediate status is inferred.'}}
entry['samples'].append(sample)
entry.setdefault('layout_variants', []).append(variant)
entry.setdefault('findings', []).append('LIVE7: nuova variante DOM hpe-editorial/local-guide. Tre unità giorno/località attuali e 53 storiche separate; solo due conflitti di sede dimostrati, senza sovrascrivere dati o generare aperture. La rilettura non rende attuale una sezione storica.')
updated_ledger['checkins'].append({'id': 'source-format-final-live7-recheck-20261020', 'at': at,
    'summary': 'Riconfronto offline sul codice finale 37f1078 e sul catalogo LIVE7 di 13.888 schede: 53 compatibilità di routing distinte da letture di contenuto; 221 risposte HTTP già conservate rigiocate, indice6 con 20 regionali identici, 16 snapshot ricostruiti e 7 lasciati aperti. Nuova variante DOM provinciale Lucca documentata: 3 unità attuali/53 storiche e 2 conflitti univoci. Nessuna nuova rete, nessun mercato verificato per il solo replay, nessun TODO precedente chiuso.'})
assert updated_ledger['tasks'] == ledger['tasks']
assert all(e['samples'][:len(before_by[e['format_id']]['samples'])] == before_by[e['format_id']]['samples']
           for e in updated_ledger['formats'])
after = build_report(rows, updated_ledger, today='2026-10-20', repo_root=ROOT)
write(ledger_path, updated_ledger)
write(DEST / 'shared-replay.json', shared)
write(DEST / 'capture-replays.json', raw)
compact_storage = deepcopy(storage)
for entry in compact_storage['formats']:
    details = entry.pop('change_digests', [])
    entry['changed_record_digests_sha256'] = digest(details)
    entry['changed_ids'] = [e['slug'] for e in details]
compact_storage['full_proof_sha256'] = sha(OUT / 'storage-comparison.json')
write(DEST / 'storage-comparison.json', compact_storage)
write(DEST / 'lucca-dom-variant.json', variant)
write(DEST / 'audit.json', after)
(DEST / 'CHECKLIST.md').write_text(render_checklist(after))
matrix = []
for item in baseline['formats'] + baseline['auxiliary_formats']:
    ident = item['format_id']
    disposition = ('shared_compatibility_only_prior_source_or_mapping_incomplete' if ident in incomplete_shared else
                   'shared_compatibility_reconfirmed' if ident in shared_only else
                   'original_http_format_replayed' if ident in source_replayed else
                   'no_successful_original_body' if ident == 'padovatoday.it--a15e8e68ca15' else
                   'changed_parser_specific_format_not_replayed' if changed.get(ident) else 'code_unchanged')
    evidence = [c for c in raw['raw_captures'] if ident in {c['requested_format_id'], c['final_format_id']}]
    matrix.append({'format_id': ident, 'scope': item['scope'], 'url_pattern': item.get('url_pattern'),
                   'catalog_records': item['catalog_records'], 'parser_disposition': disposition,
                   'parser_hash_updated': ident in parser_ok, 'storage_hash_updated': ident in storage_ok,
                   'changed_code_paths': changed.get(ident, {}), 'raw_response_count': len(evidence),
                   'original_response_hashes': sorted({c['sha256'] for c in evidence}),
                   'remaining_recheck_reasons': next(e['recheck_reasons'] for e in after['formats'] + after['auxiliary_formats'] if e['format_id'] == ident)})
review = {'schema': 1, 'checked_at': at, 'mode': 'OFFLINE_FINAL_CODE_AND_LIVE7_RECHECK',
          'code_commit': CODE, 'catalog_artifact_run': '39487468359', 'catalog_records': len(rows),
          'catalog_manifest_sha256': sha(MANIFEST), 'network_requests': 0, 'catalog_files_modified': 0,
          'new_source_acquisitions_claimed': 0, 'original_source_samples_preserved_exactly': True,
          'newly_documented_retained_source_samples': [sample['id']], 'existing_todo_statuses_unchanged': True,
          'before': baseline['summary'], 'after': after['summary'],
          'counts': {'updated_entries': len(updates), 'parser_hash_updates': len(parser_ok),
                     'source_format_replays': len(source_replayed), 'shared_compatible_formats': len(shared_only),
                     'routing_compatibility_only_formats': 53, 'shared_with_original_evidence_incomplete': len(incomplete_shared),
                     'http_response_captures_replayed': len(raw['raw_captures']),
                     'separate_source_candidate_exports': len(raw['results']),
                     'storage_reconfirmed': len(storage_ok), 'storage_still_pending': storage['kept_pending']},
          'scope_limits': ['Replayed URL formats do not prove that every page sharing the URL shape uses the same DOM.',
                           'Routing-only compatibility never counts as a fresh content read or currentness proof.',
                           'No source timestamp was moved to this review time.',
                           'Retained source facts can be historical, held or contradictory; replay does not certify opening.',
                           'The next live publication may legitimately invalidate sample storage hashes again.'],
          'integration_reference': {'report': 'reports/automation/source-quality-offline-integration-20261020.json',
                                    'report_commit': 'f29d1a1', 'gates_passed': 17},
          'formats': matrix}
write(DEST / 'review.json', review)
print(json.dumps({'before': baseline['summary'], 'after': after['summary'], 'counts': review['counts']}, ensure_ascii=False))
