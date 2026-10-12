#!/usr/bin/env node
/**
 * Deterministic, read-only quality audit of same-source weekly display repeats.
 *
 * Uses EXACTLY the same function as mobile rendering, to prevent QA drift.
 * Archives every source ID: the report measures fewer visible appointment
 * buttons, not deleted database rows or newly verified event occurrences.
 */
import fs from 'node:fs/promises'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import {
  groupVenueAppointments, isGenericCityWeeklyMarket,
  italianKey, reliableVenueAddress,
} from '../src/lib/marketGrouping.js'

const MAX_MARKETS = 100000
const MAX_SHARDS = 30
const MAX_EXAMPLES = 40

function asDisplay(m) {
  return {
    id: m.slug, name: m.nome, city: m.citta, region: m.regione,
    address: m.indirizzo || '', category: m.categoria || 'misto',
    dates: Array.isArray(m.date) ? m.date : [],
    dateQuality: m.date_quality, recurrence: m.ricorrenza_testo,
    sourceUrl: m.url_fonte || '', hours: m.orario_testo || '',
    status: m.status || 'non_confermato',
    lastVerified: m.verificato_il || '',
    lat: m.lat, lng: m.lng,
    sourceUpdated: m.aggiornato_il || '',
    sourceEvidence: Array.isArray(m.fonti) ? m.fonti : [],
    dataCompleteness: m.completezza || 0,
  }
}

export function auditDisplayRows(raw) {
  if (!Array.isArray(raw) || !raw.length || raw.length > MAX_MARKETS) {
    throw new Error('Display quality input is invalid or unbounded')
  }
  const stableIds = new Set()
  const grouped = new Map()
  let eligible = 0
  for (const row of raw) {
    const m = asDisplay(row)
    if (!m.id || stableIds.has(m.id)) throw new Error('Duplicate/missing original ID')
    stableIds.add(m.id)
    const address = reliableVenueAddress(m.address)
    if (!isGenericCityWeeklyMarket(m) || !address) continue
    eligible++
    const key = [italianKey(m.region), italianKey(m.city), address].join('|')
    if (!grouped.has(key)) grouped.set(key, [])
    grouped.get(key).push(m)
  }
  const examples = []
  const perRegion = new Map()
  let exactGroups = 0, duplicateDisplayExtras = 0, sourceRecords = 0
  for (const group of grouped.values()) {
    const originalIds = new Set(group.map(x => x.id))
    const visits = groupVenueAppointments(group)
    const seen = new Set(visits.flatMap(x => x.records.map(m => m.id)))
    if (seen.size !== group.length || seen.size !== originalIds.size) {
      throw new Error('UI grouping omitted or duplicated an original market ID')
    }
    for (const visit of visits) {
      if (visit.records.length < 2) continue
      exactGroups++
      const extra = visit.records.length - 1
      duplicateDisplayExtras += extra
      sourceRecords += visit.records.length
      const region = visit.market.region
      const prev = perRegion.get(region) || {region, groups:0, extra_display_entries:0}
      prev.groups += 1
      prev.extra_display_entries += extra
      perRegion.set(region,prev)
      if (examples.length < MAX_EXAMPLES) examples.push({
        region, city:visit.market.city, address:visit.market.address,
        source_url:visit.market.sourceUrl,
        visible_id:visit.market.id,
        original_ids:visit.records.map(r => r.id),
        date:visit.market.dates[0] || null,
      })
    }
  }
  const metrics = {
    original_records: raw.length,
    ids_retained: stableIds.size,
    generic_weekly_with_specific_venue: eligible,
    venue_groups_examined: grouped.size,
    highly_supported_same_source_visit_groups: exactGroups,
    suppressed_repeat_buttons_only: duplicateDisplayExtras,
    original_records_in_reversible_groups: sourceRecords,
    market_identities_deleted: 0,
    event_confirmations_created: 0,
    verification_claims_created: 0,
  }
  return {
    schema:1, review_only:true,
    display_grouping_only:true,
    criteria:'exact municipality, region, street, category, source URL, weekly dates, mutually compatible hours and coordinates',
    metrics, per_region:[...perRegion.values()].sort((a,b)=>a.region.localeCompare(b.region,'it')),
    examples, market_data_modified:false,
  }
}

export async function auditFromManifest(manifestFile) {
  const manifestPath=path.resolve(manifestFile)
  const manifest=JSON.parse(await fs.readFile(manifestPath,'utf8'))
  if (!Array.isArray(manifest.regions) || manifest.regions.length > MAX_SHARDS ||
      !Number.isInteger(manifest.total) || manifest.total > MAX_MARKETS) {
    throw new Error('Untrusted or unbounded static manifest')
  }
  const root = path.resolve(path.dirname(manifestPath),'../..')
  const all = []
  for (const part of manifest.regions) {
    const loc = String(part.path || '')
    if (!/^data\/v1\/regions\/[a-z0-9-]+\.json$/.test(loc)) {
      throw new Error('Region path is not an immutable static catalog asset')
    }
    const fullPath=path.resolve(root,loc)
    if (!fullPath.startsWith(root+path.sep)) throw new Error('Invalid region path')
    const shard=JSON.parse(await fs.readFile(fullPath,'utf8'))
    if (!Array.isArray(shard.markets) || shard.markets.length !== part.count) {
      throw new Error('Region shard count differs from manifest')
    }
    all.push(...shard.markets)
  }
  if (all.length !== manifest.total) throw new Error('National catalog row count differs from manifest')
  return auditDisplayRows(all)
}

export function markdown(report) {
  const m=report.metrics
  const lines=[
    '# Ripetizioni settimanali — visualizzazione reversibile',
    '',
    '**Audit della vista soltanto. Nessuna scheda cancellata o fusa nel database.**',
    'Confronta soltanto sede e giorno identici con la stessa URL di fonte',
    'e orari, coordinate, categoria e ricorrenze compatibili.',
    '',
    '- Schede originali: **'+m.original_records.toLocaleString('it-IT')+'**.',
    '- ID originali preservati: **'+m.ids_retained.toLocaleString('it-IT')+'**.',
    '- Gruppi supportati da prove forti: **'+m.highly_supported_same_source_visit_groups+'**.',
    '- Pulsanti ripetuti evitati nella vista delle sedi: **'+m.suppressed_repeat_buttons_only+'**.',
    '- Schede originali ancora apribili dietro tali gruppi: **'+m.original_records_in_reversible_groups+'**.',
    '- Eventi o verifiche dichiarati confermati: **0**.',
    '',
    '## Distribuzione',
    '',
    '| Regione | Gruppi supportati | Pulsanti ripetuti evitati |',
    '|---|---:|---:|',
  ]
  for (const r of report.per_region) lines.push('| '+r.region+' | '+r.groups+' | '+r.extra_display_entries+' |')
  lines.push('','## Esempi reali', '')
  for (const e of report.examples.slice(0,25)) {
    lines.push('- '+e.region+' · '+e.city+' · '+e.address+
      ' · '+e.original_ids.length+' schede originali · '+e.source_url)
  }
  lines.push('','Le date restano previste, non confermate. Gruppi diversi o',
    'incerti restano separati. Per aprire tutte le schede originali',
    'toccare “Mostra originali” nella vista delle sedi.', '')
  return lines.join('\n')
}

async function main() {
  const args=process.argv.slice(2)
  function option(key) {
    const ix=args.indexOf(key)
    if (ix < 0 || ix === args.length-1) throw new Error('Missing '+key)
    return args[ix+1]
  }
  const manifest=option('--manifest')
  const out=option('--out')
  const md=option('--report')
  const report=await auditFromManifest(manifest)
  for (const name of [out,md]) await fs.mkdir(path.dirname(path.resolve(name)),{recursive:true})
  await fs.writeFile(out,JSON.stringify(report,null,2)+'\n','utf8')
  await fs.writeFile(md,markdown(report),'utf8')
  console.log('REVERSIBLE_DISPLAY_DUPLICATE_AUDIT',JSON.stringify(report.metrics))
}

if (process.argv[1] && path.resolve(process.argv[1])===fileURLToPath(import.meta.url)) {
  main().catch(error => { console.error('DISPLAY_GROUP_AUDIT_BLOCKED',error); process.exitCode=2 })
}
