"""Explain exact existing storage hash changes without relabelling a source read."""
from collections import Counter
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path('/workspace/scratch/81e91a77b820/mercati-format-rechecks')
OUT = Path('/tmp/source-format-rechecks-20261020')
sys.path.insert(0, str(ROOT / 'backend'))
from merge_catalog import load_existing
from source_format_audit import digest, storage_snapshot
from province_reconciliation import KEY, valid_proof
from recurrence_refresh import refresh_records
from export_static import normalize
from eventiesagre_detail_refresh import verify_exported

DAY = date(2026, 10, 20)
rows = load_existing(ROOT / 'public/data/v1/manifest.json')
byid = {row['slug']: row for row in rows}
found = json.loads((OUT / 'storage-baseline-search.json').read_text())['found']
ledger = json.loads((ROOT / 'backend/data/source-format-review-ledger.json').read_text())
entries = {e['format_id']: e for e in ledger['formats']}
results = []
for ident, prior in found.items():
    old = prior['old_rows']
    old_by = {r['slug']: r for r in old}
    entry = entries[ident]
    assert storage_snapshot(old, entry['sample_catalog_urls']) == entry['storage_snapshot']
    now = [r for r in rows if r.get('url_fonte') in entry['sample_catalog_urls']]
    assert {r['slug'] for r in now} == set(old_by)
    changes = []
    for before in old:
        after = byid[before['slug']]
        fields = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        if fields:
            changes.append({'slug': before['slug'], 'fields': fields,
                            'before_sha256': digest(before), 'after_sha256': digest(after),
                            'field_digests': {k: {'before': digest(before.get(k)), 'after': digest(after.get(k))}
                                             for k in fields}})
    keys = {k for change in changes for k in change['fields']}
    proof = None
    if keys <= {'date'}:
        assert all(byid[r['slug']]['date'] == [day for day in r['date'] if day >= DAY.isoformat()]
                   for r in old)
        proof = {'kind': 'past_dates_pruned_only', 'new_dates_added': 0,
                 'source_field_values_and_provenance_unchanged': True}
    elif keys <= {'provincia', KEY}:
        assert all(valid_proof(byid[c['slug']][KEY], byid[c['slug']]) for c in changes)
        assert all(byid[c['slug']][KEY]['provincia_originale'] == old_by[c['slug']]['provincia'] for c in changes)
        proof = {'kind': 'independent_pinned_istat_province_only', 'administrative_changes': len(changes),
                 'market_fields_and_source_provenance_unchanged': True}
    elif ident in {'happings.com--7b87b2b2b5db', 'comune.roma.it--b6b446c7c7b8', 'comune.roma.it--d39d0b6041d2'}:
        refreshed, _ = refresh_records(old, DAY)
        reproduced = {r['slug']: normalize(r, DAY)[0] for r in refreshed}
        assert reproduced == {r['slug']: r for r in now}
        proof = {'kind': 'existing_recurrence_scope_and_normalization_exact_reconstruction',
                 'all_current_sample_fields_reconstructed': True,
                 'new_source_read_or_market_confirmation_claimed': False}
    elif ident == 'eventiesagre.it--eb4c1e3b925a':
        assert keys == {'evidenza_editoriale'}
        observed = json.loads((OUT / 'eventiesagre-proof.json').read_text())
        observed['outcomes'] = [v for v in observed['outcomes'] if v['slug'] in old_by]
        assert len(observed['outcomes']) == 1 and observed['outcomes'][0]['status'] == 'observed'
        proof = {'kind': 'exact_original_http_replay_of_current_historical_evidence',
                 'result': verify_exported(rows, observed, today=DAY),
                 'source_document_sha256': byid[old[0]['slug']]['evidenza_editoriale']['source_sha256'],
                 'read_on': byid[old[0]['slug']]['evidenza_editoriale']['read_on'],
                 'source_proof': 'eventiesagre-proof.json'}
    results.append({'format_id': ident, 'old_manifest': prior['manifest'],
                    'old_manifest_sha256': prior['manifest_sha256'], 'old_snapshot': prior['snapshot'],
                    'current_snapshot': storage_snapshot(rows, entry['sample_catalog_urls']),
                    'sample_ids_preserved': len(old), 'changed_records': len(changes),
                    'changed_fields': dict(Counter(k for c in changes for k in c['fields'])),
                    'change_digests': changes,
                    'proposed_storage_reconfirmation': proof is not None, 'proof': proof,
                    'remaining_work': None if proof else
                    'The exact old and new values are documented, but changed source facts/receipts need a dedicated saved-source reconciliation; shared export identity alone is insufficient.'})
report = {'schema': 1, 'date': DAY.isoformat(), 'network_requests': 0,
          'old_snapshot_exact_matches': len(results),
          'reconfirmable': sum(x['proposed_storage_reconfirmation'] for x in results),
          'kept_pending': sum(not x['proposed_storage_reconfirmation'] for x in results),
          'formats': results}
(OUT / 'storage-comparison.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'formats'}))
