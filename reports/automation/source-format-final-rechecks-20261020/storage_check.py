"""Reconstruct changed reviewed samples from exact prior snapshots and retained captures.

No network; unreconstructed differences keep the old ledger storage hash.
"""
from collections import Counter
from copy import deepcopy
from datetime import date
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[3]
OUT = Path('/tmp/source-format-final-rechecks-20261020')
MANIFEST = Path('/tmp/vintagery-live-39487468359/candidate/public/data/v1/manifest.json')
sys.path.insert(0, str(ROOT / 'backend'))
from merge_catalog import load_existing
from source_format_audit import digest, storage_snapshot, build_report
from province_reconciliation import KEY, valid_proof
from recurrence_refresh import refresh_records
from export_static import normalize
import eventiesagre_detail_refresh as editorial
import citynews_detail_enrichment as citynews
DAY = date(2026, 10, 20)
def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def write(name, data):
    (OUT / name).write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')
rows = load_existing(MANIFEST)
byid = {row['slug']: row for row in rows}
ledger = json.loads((ROOT / 'backend/data/source-format-review-ledger.json').read_text())
entries = {e['format_id']: e for e in ledger['formats']}
audit = build_report(rows, ledger, today=DAY, repo_root=ROOT)
changed_ids = {e['format_id'] for e in audit['formats'] + audit['auxiliary_formats']
               if 'sample_catalog_fields_changed' in e['recheck_reasons']}
previous = json.loads(Path('/tmp/source-format-rechecks-20261020/storage-baseline-search.json').read_text())
found = {k: v for k, v in previous['found'].items() if k in changed_ids}
probes = []
for prior in [ROOT / 'public/data/v1/manifest.json',
              Path('/workspace/scratch/81e91a77b820/mercati-lombardia-scope/public/data/v1/manifest.json'),
              Path('/tmp/vintagery-live-39460884416/candidate/public/data/v1/manifest.json'),
              Path('/tmp/vintagery-live-39465324614/candidate/public/data/v1/manifest.json'),
              Path('/tmp/vintagery-live-39471001816/candidate/public/data/v1/manifest.json')]:
    prior_rows = load_existing(prior)
    matched = []
    for ident in sorted(changed_ids - set(found)):
        entry = entries[ident]
        snapshot = storage_snapshot(prior_rows, entry['sample_catalog_urls'])
        if snapshot != entry['storage_snapshot']:
            continue
        old_rows = [r for r in prior_rows if r.get('url_fonte') in entry['sample_catalog_urls']]
        found[ident] = {'manifest': str(prior), 'manifest_sha256': sha(prior),
                        'snapshot': snapshot, 'old_rows': old_rows}
        matched.append(ident)
    probes.append({'manifest': str(prior), 'matched': matched})
write('storage-baseline-search.json', {'found': found, 'unresolved': sorted(changed_ids - set(found)), 'probes': probes})
results = []
for ident in sorted(changed_ids):
    entry = entries[ident]
    prior = found.get(ident)
    if not prior:
        results.append({'format_id': ident, 'proposed_storage_reconfirmation': False,
                        'remaining_work': 'Exact prior sample rows unavailable; prior hash retained.'})
        continue
    old = prior['old_rows']
    old_by = {r['slug']: r for r in old}
    assert storage_snapshot(old, entry['sample_catalog_urls']) == entry['storage_snapshot']
    now = [r for r in rows if r.get('url_fonte') in entry['sample_catalog_urls']]
    same_ids = {r['slug'] for r in now} == set(old_by)
    changes = []
    for before in old:
        after = byid.get(before['slug'])
        if after is None:
            continue
        fields = sorted(k for k in set(before) | set(after) if before.get(k) != after.get(k))
        if fields:
            changes.append({'slug': before['slug'], 'fields': fields,
                            'before_sha256': digest(before), 'after_sha256': digest(after),
                            'field_digests': {k: {'before': digest(before.get(k)), 'after': digest(after.get(k))}
                                             for k in fields}})
    keys = {k for change in changes for k in change['fields']}
    proof = None
    tried = []
    if same_ids and keys <= {'date'} and all(byid[r['slug']]['date'] == [d for d in r['date'] if d >= DAY.isoformat()] for r in old):
        proof = {'kind': 'past_dates_pruned_only', 'new_dates_added': 0,
                 'source_field_values_and_provenance_unchanged': True}
    elif same_ids and keys <= {'provincia', KEY} and all(
            valid_proof(byid[c['slug']][KEY], byid[c['slug']])
            and byid[c['slug']][KEY]['provincia_originale'] == old_by[c['slug']]['provincia'] for c in changes):
        proof = {'kind': 'independent_pinned_istat_province_only', 'administrative_changes': len(changes),
                 'market_fields_and_source_provenance_unchanged': True}
    if same_ids and proof is None:
        refreshed, _ = refresh_records(old, DAY)
        reproduced = {r['slug']: normalize(r, DAY)[0] for r in refreshed}
        if reproduced == {r['slug']: r for r in now}:
            proof = {'kind': 'existing_recurrence_scope_and_normalization_exact_reconstruction',
                     'all_current_sample_fields_reconstructed': True,
                     'new_source_read_or_market_confirmation_claimed': False}
        tried.append('existing_recurrence_scope_and_normalization')
    if same_ids and proof is None and (ident.startswith('eventiesagre.it--') or entry['url_kind'] == 'citynews_event_detail'):
        filenames = ['eventiesagre-proof.json', 'eventiesagre-prior-proof.json'] if ident.startswith('eventiesagre.it--') else ['citynews-proof.json']
        reader = editorial if ident.startswith('eventiesagre.it--') else citynews
        for filename in filenames:
            raw_report = json.loads((OUT / filename).read_text())
            urls = set(entry['sample_catalog_urls'])
            docs = [v for v in raw_report['documents'] if v['parsed']['source']['requested_url'] in urls]
            if not docs:
                continue
            test_base = [deepcopy(old_by.get(r['slug'], r)) for r in rows]
            kwargs = {'today': DAY}
            if reader is editorial:
                kwargs['publisher'] = 'eventiesagre.it'
            reconstructed, report = reader.preview(test_base, docs, **kwargs)
            reproduced = {r['slug']: normalize(r, DAY)[0] for r in reconstructed if r['slug'] in old_by}
            tried.append(filename)
            if reproduced != {r['slug']: r for r in now}:
                continue
            guard = reader.verify_exported(rows, report, today=DAY)
            proof = {'kind': 'complete_sample_reconstructed_from_exact_prior_rows_and_original_http_documents',
                     'all_current_sample_fields_reconstructed': True, 'source_proof': filename,
                     'source_documents': [{'requested_url': v['parsed']['source']['requested_url'],
                                           'sha256': v['parsed']['source']['html_sha256'],
                                           'read_on': v['read_on']} for v in docs],
                     'guard': guard, 'new_source_read_claimed': False}
            break
    results.append({'format_id': ident, 'old_manifest': prior['manifest'],
                    'old_manifest_sha256': prior['manifest_sha256'], 'old_snapshot': prior['snapshot'],
                    'current_snapshot': storage_snapshot(rows, entry['sample_catalog_urls']),
                    'sample_ids_preserved': same_ids, 'sample_records': len(old), 'changed_records': len(changes),
                    'changed_fields': dict(Counter(k for c in changes for k in c['fields'])),
                    'change_digests': changes, 'reconstructions_attempted': tried,
                    'proposed_storage_reconfirmation': proof is not None, 'proof': proof,
                    'remaining_work': None if proof else 'Exact differences documented; not all changed facts/receipts reconstructed from their original source. Prior hash retained.'})
report = {'schema': 1, 'date': DAY.isoformat(), 'network_requests': 0,
          'catalog_manifest': str(MANIFEST), 'catalog_manifest_sha256': sha(MANIFEST),
          'old_snapshot_exact_matches': len(found), 'changed_sample_formats': len(changed_ids),
          'reconfirmable': sum(x['proposed_storage_reconfirmation'] for x in results),
          'kept_pending': sum(not x['proposed_storage_reconfirmation'] for x in results), 'formats': results}
write('storage-comparison.json', report)
print(json.dumps({k: v for k, v in report.items() if k != 'formats'}), flush=True)
