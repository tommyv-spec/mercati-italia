"""Package an explicitly conditional ledger proposal, never edit the live ledger."""
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path('/workspace/scratch/81e91a77b820/mercati-format-rechecks')
OUT = Path('/tmp/source-format-rechecks-20261020')
DEST = ROOT / 'reports/automation/source-format-rechecks-20261020'
DEST.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(ROOT / 'backend'))
from merge_catalog import load_existing
from source_format_audit import build_report, code_fingerprints, digest, render_checklist


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


ledger_path = ROOT / 'backend/data/source-format-review-ledger.json'
manifest = ROOT / 'public/data/v1/manifest.json'
ledger = json.loads(ledger_path.read_text())
rows = load_existing(manifest)
baseline = build_report(rows, ledger, today='2026-10-20', repo_root=ROOT)
raw = json.loads((OUT / 'capture-replays.json').read_text())
storage = json.loads((OUT / 'storage-comparison.json').read_text())
shared = json.loads((OUT / 'shared-replay.json').read_text())
at = datetime.now(timezone.utc).isoformat()
before_by = {e['format_id']: e for e in ledger['formats']}
baseline_by = {e['format_id']: e for e in baseline['formats'] + baseline['auxiliary_formats']}
changed = {}
for e in ledger['formats']:
    now = code_fingerprints(e.get('code_sha256', {}), ROOT)
    changed[e['format_id']] = {p: {'before': h, 'after': now[p]}
                                for p, h in e.get('code_sha256', {}).items() if h != now[p]}
shared_only = {ident for ident, paths in changed.items() if paths and (
    set(paths) == {'backend/publisher_refresh.py'} or
    set(paths) == {'backend/export_static.py', 'backend/field_evidence.py'})}
shared_only.remove('padovatoday.it--a15e8e68ca15')
raw_formats = {c['requested_format_id'] for c in raw['raw_captures']}
raw_formats |= {c['final_format_id'] for c in raw['raw_captures'] if c['family'].startswith('happings')}
source_replayed = {ident for ident in raw_formats if changed.get(ident)}
incomplete_shared = {ident for ident in shared_only if any(
    baseline_by[ident]['checks'][name]['state'] != 'done' for name in ('source_sample', 'field_mapping'))}
parser_ok = (shared_only - incomplete_shared) | source_replayed
storage_ok = {x['format_id']: x for x in storage['formats'] if x['proposed_storage_reconfirmation']}
assert len(parser_ok) == 87 and len(shared_only) == 86 and len(source_replayed) == 8 and len(incomplete_shared) == 7
assert len(storage_ok) == 9

proposal_ledger = deepcopy(ledger)
updates = []
for entry in proposal_ledger['formats']:
    ident = entry['format_id']
    if ident not in parser_ok and ident not in storage_ok:
        continue
    old = deepcopy(entry)
    event = {'at': at, 'kind': 'offline_code_and_storage_recomparison',
             'previous_reviewed_at': old.get('reviewed_at'),
             'previous_code_sha256': old.get('code_sha256'),
             'previous_storage_snapshot': old.get('storage_snapshot'),
             'source_reads_relabelled': 0, 'source_samples_modified': False,
             'baseline_code': '1f0c624cbb5c96019458d119abc9f30b47663014',
             'report': 'reports/automation/source-format-rechecks-20261020/review.json'}
    if ident in parser_ok:
        basis = 'unchanged_source_parser_and_differential_shared_code_export_coverage' if ident in shared_only else \
                'real_retained_http_sample_replay_on_exact_url_format_and_full_catalog_export'
        entry['code_sha256'] = code_fingerprints(entry['code_sha256'], ROOT)
        entry['parser_comparison_basis'] = basis
        entry['checks']['parser_comparison'] = {'state': 'done', 'note': (
            'Compatibilità riconfrontata: parser sorgente registrato immutato; confronto differenziale del codice '
            'condiviso e roundtrip completo di 13.856 schede. Non è una nuova lettura né una verifica di completezza '
            'dei contenuti. Prova: source-format-rechecks-20261020/shared-replay.json.'
            if ident in shared_only else
            'Rieseguito il parser sui byte HTTP originali conservati per questo formato e sulle relative '
            'transizioni osservate, con confronto contro 13.856 schede ed export separato in /tmp. '
            'Date e hash delle acquisizioni originali invariati. Prova: source-format-rechecks-20261020/capture-replays.json.')}
        event['changed_code_paths'] = changed[ident]
        event['parser_basis'] = basis
        entry['last_code_recomparison'] = deepcopy(event)
    if ident in storage_ok:
        item = storage_ok[ident]
        entry['storage_snapshot'] = item['current_snapshot']
        entry['checks']['storage_comparison'] = {'state': 'done', 'note':
            'Ritrovata la fotografia precedente con SHA-256 identico e confrontate tutte le differenze effettive. '
            'Riconferma limitata alla prova ' + item['proof']['kind'] + '. Nessuna nuova lettura o verifica '
            'di apertura dichiarata. Prova: source-format-rechecks-20261020/storage-comparison.json.'}
        event['storage_proof'] = item['proof']
        entry['last_storage_recomparison'] = {'at': at, 'previous_snapshot': item['old_snapshot'],
                                            'current_snapshot': item['current_snapshot'], 'proof': item['proof']}
    entry.setdefault('comparison_history', []).append(event)
    entry['reviewed_at'] = at
    assert entry['samples'] == old['samples']
    updates.append({'format_id': ident, 'entry_before_sha256': digest(old),
                    'set': {k: v for k, v in entry.items() if old.get(k) != v}})

checkin = {'id': 'source-format-offline-recheck-20261020', 'at': at,
           'summary': 'Proposta offline su baseline 1f0c624: 53 compatibilità di routing, 33 confronti ufficiali '
           '(8 primari/25 ausiliari) con parser sorgente immutato, 8 formati con replay reale. '
           'Le 7 verifiche condivise senza mappatura/fonte completa restano aperte; 9 snapshot '
           'ricostruiti, 6 storage e 21 parser primari lasciati da riconfrontare. Nessuna lettura nuova. '
           'Applicazione sospesa: richiede nuovo confronto sul candidato LIVE7 e indice schema6.'}
proposal_ledger['checkins'].append(checkin)
after = build_report(rows, proposal_ledger, today='2026-10-20', repo_root=ROOT)
write(OUT / 'ledger.proposed.json', proposal_ledger)
write(OUT / 'audit.proposed.json', after)
(OUT / 'checklist.proposed.md').write_text(render_checklist(after))

compact_storage = deepcopy(storage)
for entry in compact_storage['formats']:
    changes = entry.pop('change_digests')
    entry['changed_record_digests_sha256'] = digest(changes)
    entry['changed_ids'] = [e['slug'] for e in changes]
    entry['exact_change_details_local'] = str(OUT / 'storage-comparison.json')
compact_storage['full_local_proof_sha256'] = sha(OUT / 'storage-comparison.json')
write(DEST / 'storage-comparison.json', compact_storage)
for name in ['shared-replay.json', 'capture-replays.json']:
    shutil.copyfile(OUT / name, DEST / name)

matrix = []
for item in baseline['formats'] + baseline['auxiliary_formats']:
    ident = item['format_id']
    reason = 'not_changed_or_not_reviewed'
    if ident in incomplete_shared:
        reason = 'shared_compatibility_proved_but_prior_source_or_field_comparison_incomplete'
    elif ident in shared_only:
        reason = 'shared_compatibility_reconfirmed'
    elif ident in source_replayed:
        reason = 'captured_format_replayed'
    elif ident == 'padovatoday.it--a15e8e68ca15':
        reason = 'reader_newly_routed_but_no_successful_body_capture'
    elif ident.startswith('eventiesagre.it--') and changed.get(ident):
        reason = 'changed_source_parser_no_retained_body_for_this_format'
    raw_evidence = [c for c in raw['raw_captures'] if ident in {c['requested_format_id'], c['final_format_id']}]
    matrix.append({'format_id': ident, 'scope': item['scope'], 'catalog_records': item['catalog_records'],
                   'url_pattern': item.get('url_pattern'), 'original_recheck_reasons': item['recheck_reasons'],
                   'changed_code_paths': changed.get(ident, {}), 'parser_disposition': reason,
                   'parser_hash_update_proposed': ident in parser_ok,
                   'storage_hash_update_proposed': ident in storage_ok,
                   'capture_count': len(raw_evidence),
                   'original_capture_hashes': sorted({c['sha256'] for c in raw_evidence}),
                   'storage_comparison': next(({'changed_records': e['changed_records'],
                       'changed_fields': e['changed_fields'], 'reconfirmable': e['proposed_storage_reconfirmation'],
                       'proof_kind': (e['proof'] or {}).get('kind')}
                       for e in storage['formats'] if e['format_id'] == ident), None)})

review = {'schema': 1, 'checked_at': at, 'mode': 'OFFLINE_CONDITIONAL_RECHECK_PROPOSAL',
          'code_commit': subprocess.check_output(['git', '-C', str(ROOT), 'rev-parse', 'HEAD'], text=True).strip(),
          'catalog_manifest': str(manifest.relative_to(ROOT)), 'catalog_manifest_sha256': sha(manifest),
          'ledger_before_sha256': sha(ledger_path), 'network_requests': 0, 'catalog_product_files_modified': 0,
          'baseline_summary': baseline['summary'], 'hypothetical_proposal_summary': after['summary'],
          'not_approved_for_next_release': True,
          'next_release_requirements': ['Re-run the shared export/reload comparison on final index schema6 code.',
               'Compare the newly published LIVE7 catalog to these exact storage snapshots; a new hash alone is not evidence.',
               'Any changed source facts not covered by retained captures remain pending.',
               'Never relabel original source acquisition timestamps or turn compatibility into currentness.'],
          'counts': {'shared_compatibility_primary_formats': 61, 'shared_compatibility_auxiliary_formats': 25,
                     'routing_compatibility_only_formats': 53, 'source_parser_replayed_primary_formats': 7,
                     'source_parser_replayed_auxiliary_formats': 1, 'unchanged_citynews_formats_replayed': 27,
                     'raw_http_bodies': len(raw['raw_captures']), 'storage_reconfirmations': 9,
                     'storage_pending': 6, 'parser_pending_no_specific_raw': 15,
                     'shared_compatible_but_source_comparison_incomplete_primary': 6,
                     'shared_compatible_but_source_comparison_incomplete_auxiliary': 1,
                     'parser_hash_updates_proposed_primary': 62,
                     'parser_hash_updates_proposed_auxiliary': 25},
          'validation': {'shared_catalog_roundtrip_rows': 13856, 'existing_receipts_preserved': 2264,
                         'administrative_proofs_retained': 220, 'targeted_tests': 54, 'test_failures': 0,
                         'test_command': 'PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=backend:backend/tests python -m unittest test_source_format_audit test_existing_source_refresh_coverage test_field_evidence -q',
                         'separate_capture_replay_exports': 6},
          'storage_limit': 'Six actual sample fact/provenance changes are documented but their hashes stay old until a dedicated saved-source reconciliation is proved.',
          'all_original_samples_preserved_exactly': all(a['samples'] == b['samples'] for a, b in zip(ledger['formats'], proposal_ledger['formats'])),
          'task_statuses_unchanged': proposal_ledger['tasks'] == ledger['tasks'],
          'formats': matrix}
write(DEST / 'review.json', review)
proposal = {'schema': 1, 'status': 'conditional_do_not_apply_before_final_schema6_and_live7_recheck',
            'requires_exact_code_commit': review['code_commit'], 'requires_ledger_sha256': sha(ledger_path),
            'requires_catalog_manifest_sha256': sha(manifest), 'new_source_reads_claimed': 0,
            'source_samples_must_remain_equal': True, 'task_status_changes': [],
            'entry_updates': updates, 'checkin_to_append_after_revalidation': checkin}
write(DEST / 'ledger-proposal.json', proposal)
print(json.dumps({'report': str(DEST), 'proposal_entry_updates': len(updates),
                  'before': baseline['summary'], 'hypothetical_after': after['summary'],
                  'parser_uncovered': [m['format_id'] for m in matrix if m['parser_disposition'] in {
                      'reader_newly_routed_but_no_successful_body_capture', 'changed_source_parser_no_retained_body_for_this_format'}]}, ensure_ascii=False))
