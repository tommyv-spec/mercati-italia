"""Offline source-format rechecks; output stays under /tmp, never source reads."""
from collections import Counter
from copy import deepcopy
from datetime import date
import base64
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from types import ModuleType

ARGS = argparse.ArgumentParser(description=__doc__)
ARGS.add_argument('stage', nargs='?', choices=['all', 'shared', 'raw', 'prior'], default='all')
ARGS.add_argument('--repo', type=Path, default=Path('/workspace/scratch/81e91a77b820/mercati-format-rechecks-final'))
ARGS.add_argument('--manifest', type=Path)
ARGS.add_argument('--output', type=Path, default=Path('/tmp/source-format-final-rechecks-20261020'))
OPTIONS = ARGS.parse_args()
ROOT = OPTIONS.repo
OUT = OPTIONS.output
OUT.mkdir(parents=True, exist_ok=True)
MANIFEST = OPTIONS.manifest or ROOT / 'public/data/v1/manifest.json'
DAY = date(2026, 10, 20)
sys.path.insert(0, str(ROOT / 'backend'))
from merge_catalog import load_existing
from source_format_audit import classify_url, digest, storage_snapshot
from export_static import normalize, export
from field_evidence import clean_receipts, valid_receipt
from province_reconciliation import KEY as PROVINCE_KEY, valid_proof
import publisher_refresh


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write(name, value):
    (OUT / name).write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n')


def old_module(name, ref='3a4d5c7'):
    path = ROOT / 'backend' / (name + '.py')
    module = ModuleType('audit_previous_' + name)
    module.__file__ = str(path)
    sys.modules[module.__name__] = module
    blob = subprocess.check_output(['git', '-C', str(ROOT), 'show', ref + ':backend/' + name + '.py'])
    exec(compile(blob, str(path), 'exec'), module.__dict__)
    return module


def candidate(rows, label):
    path = OUT / label / 'public/data/v1'
    exported = export(rows, path, today=DAY, min_count=len(BASE), preserve_ids=IDS)
    result = load_existing(path / 'manifest.json')
    assert {r['slug'] for r in result} == IDS and len(result) == len(BASE)
    return result, {'manifest': str(path / 'manifest.json'), 'manifest_sha256': sha(path / 'manifest.json'),
                    'records': len(result), 'all_ids_preserved': True, 'stats': exported['stats']}


BASE = load_existing(MANIFEST)
IDS = {r['slug'] for r in BASE}
assert len(IDS) == len(BASE) and BASE
LEDGER = json.loads((ROOT / 'backend/data/source-format-review-ledger.json').read_text())


def shared():
    old_export = old_module('export_static')
    old_fields = old_module('field_evidence')
    old_publisher = old_module('publisher_refresh')
    changed = Counter()
    receipt_total = 0
    for row in BASE:
        before, old_reason = old_export.normalize(row, DAY)
        after, reason = normalize(row, DAY)
        assert reason == old_reason and before is not None and after is not None
        keys = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
        assert keys <= {PROVINCE_KEY}
        if keys:
            assert valid_proof(after[PROVINCE_KEY], after)
            changed.update(keys)
        assert old_fields.clean_receipts(row.get('riscontri_campi'), row, today=DAY) == clean_receipts(
            row.get('riscontri_campi'), row, today=DAY)
        receipt_total += len(clean_receipts(row.get('riscontri_campi'), row, today=DAY))
    config = json.loads((ROOT / 'backend/data/publisher-refresh-contracts.json').read_text())
    relevant = {e['format_id'] for e in LEDGER['formats'] if set(e.get('code_sha256', {})) <= {
        'backend/source_firestore_public.py', 'backend/publisher_page_parser.py', 'backend/publisher_refresh.py'}}
    coverage = []
    for path in [None, Path('/tmp/vintagery-live-39487468359')]:
        rows = BASE if path is None else load_existing(path / 'candidate/public/data/v1/manifest.json')
        existing = None if path is None else json.loads((path / 'existing-source-refresh.json').read_text())
        previous = old_publisher.catalog_resources(rows, config, today=DAY, existing_source_report=existing)
        current = publisher_refresh.catalog_resources(rows, config, today=DAY, existing_source_report=existing)
        a = {r['url']: r for r in previous['resources']}
        b = {r['url']: r for r in current['resources']}
        assert set(a) == set(b)
        restricted = [url for url in a if classify_url(url)['format_id'] in relevant]
        changed_restricted = [url for url in restricted if a[url] != b[url]]
        assert {classify_url(url)['format_id'] for url in changed_restricted} <= {'padovatoday.it--a15e8e68ca15'}
        changed_urls = [url for url in a if a[url] != b[url]]
        coverage.append({'context': 'no_run_report' if path is None else 'actual_live7_report',
                         'catalog_records': len(rows), 'compared_format_ids': sorted(relevant),
                         'compared_resource_urls': len(restricted),
                         'identical_resource_count': len(restricted) - len(changed_restricted),
                         'changed_restricted_resources': [{'url': url, 'old': a[url], 'new': b[url]}
                                                          for url in changed_restricted],
                         'all_resource_differences': changed_urls,
                         'report_path': str(path / 'existing-source-refresh.json') if path else None})
    exported, export_report = candidate(BASE, 'shared-export')
    assert {r['slug']: r for r in exported} == {r['slug']: r for r in BASE}
    input_manifest = json.loads(MANIFEST.read_text())
    output_manifest = json.loads(Path(export_report['manifest']).read_text())
    assert output_manifest['index_schema'] == 6
    assert output_manifest['index_as_of'] == DAY.isoformat()
    export_report['index_schema'] = output_manifest['index_schema']
    export_report['index_as_of'] = output_manifest['index_as_of']
    # All region filenames are content hashes; exact files must also match.
    assert input_manifest['regions'] == output_manifest['regions']
    region_files = [MANIFEST.parent / Path(value['path']).relative_to('data/v1')
                    for value in input_manifest['regions']]
    matched = []
    for original in region_files:
        counterpart = Path(export_report['manifest']).parent / original.relative_to(MANIFEST.parent)
        assert counterpart.is_file() and counterpart.read_bytes() == original.read_bytes()
        matched.append({'path': str(original.relative_to(MANIFEST.parent)), 'sha256': sha(original)})
    export_report['regional_files_byte_identical'] = matched
    report = {'schema': 1, 'date': DAY.isoformat(), 'network_requests': 0,
              'comparison': 'Previous changed modules at 3a4d5c7 against final 37f1078, current dependencies held constant; LIVE7 catalog and index schema6.',
              'catalog_records': len(BASE), 'manifest_path': str(MANIFEST), 'manifest_sha256': sha(MANIFEST),
              'normalization_differences': dict(changed), 'all_other_normalized_fields_identical': True,
              'old_and_new_receipts_identical': receipt_total, 'publisher_coverage': coverage,
              'static_roundtrip': export_report, 'static_all_rows_byte_equivalent': True}
    write('shared-replay.json', report)
    print(json.dumps({'shared': 'passed', 'records': len(BASE), 'receipt_count': receipt_total,
                      'normalization_differences': dict(changed)}), flush=True)


def capture_record(page, family, **extra):
    raw = page.get('html', page.get('body'))
    return {'family': family, 'requested_url': page['requested_url'], 'final_url': page['final_url'],
            'requested_format_id': classify_url(page['requested_url'])['format_id'],
            'final_format_id': classify_url(page['final_url'])['format_id'],
            'sha256': hashlib.sha256(raw).hexdigest(), 'bytes': len(raw), **extra}


def raw_replays():
    import eventiesagre_detail_refresh as editorial
    import citynews_detail_enrichment as citynews
    import happings_autopilot as happings
    import happings_source_enrichment as weekly
    import happings_detail_enrichment as details
    from happings_legacy_resources import prove_resource
    from happings_weekly_layout import fold
    captures, results = [], {}
    for publisher, file_prefix in [('eventiesagre.it', 'eventiesagre'), ('cosedicasa.com', 'cosedicasa')]:
        path = Path('/tmp/vintagery-live-39487468359/sources') / (file_prefix + '-detail-pages.json')
        checkpoint = json.loads(path.read_text())
        docs = []
        for packed in checkpoint['pages']:
            page = editorial._unpack(packed, today=DAY)
            document = editorial.parse_document(page['body'], requested_url=page['requested_url'],
                                               final_url=page['final_url'], today=DAY)
            docs.append({'read_on': page['read_on'], 'parsed': document})
            captures.append(capture_record(page, publisher, read_on=page['read_on'],
                                            transport_metadata={k: v for k, v in page.items() if k != 'body'},
                                            parser_status=document['status'], raw_container=str(path)))
        revised, report = editorial.preview(BASE, docs, today=DAY, publisher=publisher)
        proof = editorial.verify_changes(BASE, revised, report, today=DAY)
        final, exported = candidate(revised, file_prefix + '-export')
        guard = editorial.verify_exported(final, report, today=DAY)
        write(file_prefix + '-proof.json', report)
        results[publisher] = {'captured_pages': len(docs), 'capture_sha256': sha(path), 'source_file': str(path),
                              'outcomes': dict(Counter(e['status'] for e in report['outcomes'])),
                              'source_guard': proof, 'export_guard': guard, 'export': exported}
        print(json.dumps({publisher: results[publisher]['outcomes'], 'pages': len(docs)}), flush=True)
    path = Path('/tmp/citynews-captures-20261020/manifest.json')
    manifest = json.loads(path.read_text())
    docs, pages = [], []
    for item in manifest['results']:
        if item['status'] != 'retrieved':
            continue
        raw = Path(item['html_file']).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == item['sha256'] and len(raw) == item['bytes']
        page = {'requested_url': item['requested_url'], 'final_url': item['final_url'],
                'read_on': item['fetched_at'][:10], 'html': raw}
        pages.append(page)
        parsed = citynews.parse_document(raw, requested_url=page['requested_url'], final_url=page['final_url'], today=DAY)
        docs.append({'read_on': page['read_on'], 'parsed': parsed})
        captures.append(capture_record(page, 'citynews', read_on=page['read_on'], fetched_at=item['fetched_at'],
                                        parser_status=parsed['status'], raw_container=str(path)))
    import citynews_detail_refresh as citynews_controller
    live_citynews = Path('/tmp/vintagery-live-39487468359/sources/citynews-detail-pages.json')
    for item in json.loads(live_citynews.read_text())['pages']:
        raw = citynews_controller._unpack(item, today=DAY, kind='detail')
        page = {'requested_url': item['url'], 'final_url': item['url'], 'read_on': item['read_on'], 'html': raw}
        pages.append(page)
        parsed = citynews.parse_document(raw, requested_url=item['url'], final_url=item['url'], today=DAY)
        docs.append({'read_on': item['read_on'], 'parsed': parsed})
        captures.append(capture_record(page, 'citynews', read_on=item['read_on'],
                                        parser_status=parsed['status'], raw_container=str(live_citynews)))
    # Preserve each acquired page above, use one latest observation per exact URL in matching.
    by_url = {p['requested_url']: (p, d) for p, d in zip(pages, docs)}
    pages, docs = map(list, zip(*by_url.values()))
    revised, report = citynews.preview(BASE, docs, today=DAY)
    raw_guard = citynews.verify_source_pages(pages, docs, today=DAY)
    final, exported = candidate(revised, 'citynews-export')
    write('citynews-proof.json', report)
    results['citynews'] = {'captured_pages': len(docs), 'capture_sha256': sha(path), 'source_file': str(path),
                          'outcomes': dict(Counter(e['status'] for e in report['outcomes'])), 'raw_guard': raw_guard,
                          'export_guard': citynews.verify_exported(final, report, today=DAY), 'export': exported}
    print(json.dumps({'citynews': results['citynews']['outcomes'], 'pages': len(docs)}), flush=True)
    path = Path('/tmp/vintagery-live-39487468359/sources/happings-pages.json')
    checkpoint = json.loads(path.read_text())
    pages = happings._unpack_pages(checkpoint, checkpoint['context'])
    for page in pages:
        captures.append(capture_record(page, 'happings_weekly', read_on=checkpoint['context']['today'],
                                        raw_container=str(path), time_precision='day_only_from_original_checkpoint'))
    revised, report = weekly.preview(BASE, pages, today=DAY, apply=True, rights_verified=True)
    weekly.safe_report(report, BASE, source_pages=pages)
    final, exported = candidate(revised, 'happings-weekly-export')
    for row in final:
        assert all(valid_receipt(r, row, today=DAY) for r in row.get('riscontri_campi', []))
    write('happings-weekly-proof.json', report)
    results['happings_weekly'] = {'captured_pages': len(pages), 'capture_sha256': sha(path), 'source_file': str(path),
                                 'field_changes': report['field_changes'], 'record_changes': report['record_changes'],
                                 'safe_report_reconstruction': True, 'export': exported,
                                 'failed_original_requests_excluded': checkpoint['failures']}
    print(json.dumps({'happings_weekly': 'passed', 'pages': len(pages)}), flush=True)
    folder = Path('/tmp/happings-legacy-captures-20261020')
    first = json.loads((folder / 'captures.json').read_text())
    second = json.loads((folder / 'captures-next.json').read_text())
    last = json.loads((folder / 'captures-final.json').read_text())
    legacy, resource_proofs = [], []
    for a, b, c, name in zip(first, second, last, ['trieste', 'bolzano']):
        assert a['status'] == b['status'] == 301 and c['status'] == 200
        assert a['location'] == b['requested_url'] and b['location'] == c['requested_url']
        raw = (folder / (name + '.html')).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == c['sha256'] and len(raw) == c['bytes']
        page = {'requested_url': a['requested_url'], 'final_url': c['final_url'], 'html': raw}
        bound_rows = [row for row in BASE if row.get('url_fonte') == a['requested_url']]
        assert bound_rows and len({(row['regione'], row['provincia']) for row in bound_rows}) == 1
        item = {'region': fold(bound_rows[0]['regione']), 'province': bound_rows[0]['provincia']}
        resource_proof, disposition = prove_resource(item, c['requested_url'], raw, bound_rows, today=DAY)
        assert disposition == 'resolved' and resource_proof is not None
        resource_proofs.append({'origin_url': a['requested_url'], 'proof': resource_proof})
        # This is the separately recorded real 200 final request. The legacy
        # origin and both observed 301s remain in the distinct provenance above.
        legacy.append({'requested_url': c['requested_url'], 'final_url': c['final_url'], 'html': raw})
        captures.append(capture_record(page, 'happings_legacy_town', fetched_at=c['fetched_at'],
                                        read_on=c['fetched_at'][:10], raw_container=str(folder / (name + '.html')),
                                        observed_redirects=[a, b], final_capture=c))
    revised, report = weekly.preview(BASE, legacy, today=DAY, apply=True, rights_verified=True)
    weekly.safe_report(report, BASE, source_pages=legacy)
    final, exported = candidate(revised, 'happings-town-export')
    write('happings-town-proof.json', report)
    results['happings_legacy_town'] = {'captured_pages': len(legacy), 'field_changes': report['field_changes'],
                                     'record_changes': report['record_changes'], 'safe_report_reconstruction': True,
                                     'export': exported, 'actual_redirect_hops': 4,
                                     'independent_resource_proofs': resource_proofs}
    pages = []
    folder = Path('/tmp/happings-detail-20261020')
    for name in ['pisa', 'lana', 'pescia', 'lucca_antiquario', 'piemontese', 'castelrotto', 'natale_parcines',
                 'natale_concerto', 'notizia_fumetti']:
        meta = json.loads((folder / (name + '.json')).read_text())
        raw = (folder / (name + '.html')).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == meta['sha256'] and len(raw) == meta['bytes']
        page = {'requested_url': meta['requested_url'], 'final_url': meta['final_url'], 'html': raw,
                'fetched_at': meta['captured_at']}
        pages.append(page)
        captures.append(capture_record(page, 'happings_detail', fetched_at=meta['captured_at'],
                                        read_on=meta['captured_at'][:10], raw_container=str(folder / (name + '.html'))))
    import happings_detail_autopilot as detail_controller
    path = Path('/tmp/vintagery-live-39487468359/sources/happings-detail-pages.json')
    saved = json.loads(path.read_text())
    state, live_pages, acquisition = detail_controller._unpack(saved, saved['context'], today=DAY,
                                                              max_requests=saved['context']['details_policy']['max_requests'])
    for page in live_pages:
        captures.append(capture_record(page, 'happings_detail', fetched_at=page['fetched_at'],
                                        read_on=page['fetched_at'][:10], raw_container=str(path)))
    pages = list({p['requested_url']: p for p in pages + live_pages}.values())
    revised, report = details.preview(BASE, pages, today=DAY, apply=True, admit_new=False)
    guard = details.verify_changes(BASE, revised, report, today=DAY)
    final, exported = candidate(revised, 'happings-detail-export')
    write('happings-detail-proof.json', report)
    results['happings_detail'] = {'captured_pages': len(pages), 'source_guard': guard, 'export': exported,
                                 'outcomes': dict(Counter(e['status'] for e in report['outcomes']))}
    write('capture-replays.json', {'schema': 1, 'date': DAY.isoformat(), 'network_requests': 0,
                                 'product_catalog_modified': False, 'raw_captures': captures, 'results': results,
                                 'notes': ['Independent replay candidates under /tmp, not a merged or published catalog.',
                                           'No capture timestamp or hash has been substituted for an older audit sample.']})
    print(json.dumps({'raw_replays': 'passed', 'pages': len(captures),
                      'requested_formats': dict(Counter(c['requested_format_id'] for c in captures))}), flush=True)



def prior_replays():
    import eventiesagre_detail_refresh as editorial
    import happings_autopilot as happings
    import happings_source_enrichment as weekly
    captures, results = [], {}
    source = Path('/tmp/vintagery-live-39471001816/sources')
    path = source / 'eventiesagre-detail-pages.json'
    checkpoint = json.loads(path.read_text())
    docs = []
    for packed in checkpoint['pages']:
        page = editorial._unpack(packed, today=DAY)
        parsed = editorial.parse_document(page['body'], requested_url=page['requested_url'],
                                          final_url=page['final_url'], today=DAY)
        docs.append({'read_on': page['read_on'], 'parsed': parsed})
        captures.append(capture_record(page, 'eventiesagre.it', read_on=page['read_on'],
                                        parser_status=parsed['status'], raw_container=str(path)))
    revised, report = editorial.preview(BASE, docs, today=DAY, publisher='eventiesagre.it')
    proof = editorial.verify_changes(BASE, revised, report, today=DAY)
    final, exported = candidate(revised, 'eventiesagre-prior-export')
    guard = editorial.verify_exported(final, report, today=DAY)
    write('eventiesagre-prior-proof.json', report)
    results['eventiesagre_prior'] = {'captured_pages': len(docs), 'capture_sha256': sha(path),
        'outcomes': dict(Counter(e['status'] for e in report['outcomes'])),
        'source_guard': proof, 'export_guard': guard, 'export': exported}
    path = source / 'happings-pages.json'
    checkpoint = json.loads(path.read_text())
    pages = happings._unpack_pages(checkpoint, checkpoint['context'])
    for page in pages:
        captures.append(capture_record(page, 'happings_weekly_prior', read_on=checkpoint['context']['today'],
                                        raw_container=str(path), time_precision='day_only_from_original_checkpoint'))
    revised, report = weekly.preview(BASE, pages, today=DAY, apply=True, rights_verified=True)
    weekly.safe_report(report, BASE, source_pages=pages)
    final, exported = candidate(revised, 'happings-weekly-prior-export')
    write('happings-weekly-prior-proof.json', report)
    results['happings_weekly_prior'] = {'captured_pages': len(pages), 'capture_sha256': sha(path),
        'field_changes': report['field_changes'], 'record_changes': report['record_changes'],
        'safe_report_reconstruction': True, 'export': exported}
    write('prior-capture-replays.json', {'schema': 1, 'date': DAY.isoformat(), 'network_requests': 0,
        'raw_captures': captures, 'results': results, 'notes': ['Earlier actual captures, not new HTTP reads.']})
    print(json.dumps({'prior_replays': 'passed', 'pages': len(captures)}), flush=True)

if __name__ == '__main__':
    stage = OPTIONS.stage
    if stage in {'shared', 'all'}:
        shared()
    if stage in {'raw', 'all'}:
        raw_replays()

    if stage in {'prior', 'all'}:
        prior_replays()
