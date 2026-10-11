// Run against the built, purely static Vite preview. Report measurements;
// do not confuse an audit run with a passing production launch certification.
import { chromium } from 'playwright'
import AxeBuilder from '@axe-core/playwright'
import fs from 'node:fs/promises'

const BASE = process.env.AUDIT_BASE || 'http://127.0.0.1:4173/'
const OUT = 'reports/audit/browser.json'
const report = {
  audited_url: BASE,
  measured_at: new Date().toISOString(),
  browser: 'Playwright Chromium mobile emulation',
  network_profile: 'cold 1.6 Mbps downstream, 150ms artificial latency, CPU throttle 4x',
  stages: [],
  response_errors: [],
  request_errors: [],
  page_errors: [],
  console_errors: [],
  active_backend_requests: [],
  wcag: [],
}
const timer = () => performance.now()
const stage = async (name, task) => {
  const t = timer()
  try {
    const detail = await task()
    report.stages.push({ name, success: true, duration_ms: Math.round(timer()-t), detail })
    console.log('AUDIT OK',name,JSON.stringify(detail).slice(0,650))
  } catch (error) {
    report.stages.push({ name, success: false, duration_ms: Math.round(timer()-t), error: String(error).slice(0,900) })
    console.log('AUDIT FAIL',name,String(error).slice(0,400))
  }
}
const browser = await chromium.launch({ headless: true })
const context = await browser.newContext({
  viewport: { width: 390, height: 844 },
  isMobile: true, hasTouch: true, deviceScaleFactor: 1,
  locale: 'it-IT', timezoneId: 'Europe/Rome',
})
const page = await context.newPage()
const requests = []
page.on('pageerror', error => report.page_errors.push(String(error).slice(0,700)))
page.on('console', msg => { if (msg.type()==='error') report.console_errors.push(msg.text().slice(0,600)) })
page.on('request', request => {
  requests.push(request)
  if (/firestore\.googleapis\.com|firebaseio\.com|workers\.dev|\/api\//i.test(request.url())) {
    report.active_backend_requests.push(request.url())
  }
})
page.on('requestfailed', r => report.request_errors.push({ url:r.url().slice(0,200), failure:r.failure() }))
page.on('response', r => { if (r.status()>=400) report.response_errors.push({ url:r.url().slice(0,200), status:r.status() }) })

await stage('cold mobile load with throttling',async () => {
  const client = await context.newCDPSession(page)
  await client.send('Network.enable')
  await client.send('Network.emulateNetworkConditions', {
    offline:false, latency:150, downloadThroughput:200000, uploadThroughput:60000
  })
  await client.send('Emulation.setCPUThrottlingRate', {rate:4})
  const started = timer()
  const response = await page.goto(BASE,{waitUntil:'domcontentloaded',timeout:45000})
  const domMs = Math.round(timer()-started)
  await page.locator('.market-card .card-name').first().waitFor({timeout:90000})
  const readyMs = Math.round(timer()-started)
  await page.waitForTimeout(500)
  const browserStats=await page.evaluate(() => ({
    viewport_width: window.innerWidth,
    document_scroll_width: document.documentElement.scrollWidth,
    painted: performance.getEntriesByType('paint').map(v=>({name:v.name,ms:Math.round(v.startTime)})),
    resources: performance.getEntriesByType('resource').length,
    first_card_text:document.querySelector('.market-card .card-name')?.textContent,
    hero_count:document.querySelector('.results-count')?.textContent,
    heap_bytes:performance.memory?.usedJSHeapSize ?? null,
    dom_nodes:document.querySelectorAll('*').length,
  }))
  await page.screenshot({path:'reports/audit/home-mobile.png',animations:'disabled'})
  await client.send('Emulation.setCPUThrottlingRate',{rate:1})
  await client.send('Network.emulateNetworkConditions',{
    offline:false,latency:0,downloadThroughput:-1,uploadThroughput:-1
  })
  await client.detach()
  return { http_status:response.status(), DOM_ready_ms:domMs, first_market_card_ms:readyMs,...browserStats }
})

await stage('mobile accessibility axe wcag2/2.1 AA', async () => {
  const result=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze()
  const violations=result.violations.map(v=>({
    rule:v.id, impact:v.impact, description:v.help, nodes:v.nodes.length,
    target_example:v.nodes[0]?.target?.slice(0,3)
  }))
  report.wcag.push({stage:'home',violations})
  return {violations:violations.length,top:violations.slice(0,12)}
})

await stage('city grouped markets and 7 source IDs',async () => {
  // Clicking suggested Firenze is equivalent to the manual city filter.
  await page.getByRole('button',{name:'Firenze',exact:true}).first().click()
  const group=page.getByTestId('weekly-city-group').filter({hasText:'Mercati settimanali a Firenze'}).first()
  await group.waitFor({timeout:20000})
  const before=await group.locator('.weekly-city-counter').innerText()
  await group.getByRole('button',{name:'Visualizza sedi e giornate'}).click()
  await group.getByText('Largo Monzani',{exact:true}).waitFor({timeout:20000})
  await group.getByText('Caricamento sedi…').waitFor({state:'hidden',timeout:20000})
  const city = {
    count: before,
    known_venues: await group.locator('.weekly-venue[data-known="true"]').count(),
    unknown_venues_visible: await group.locator('.weekly-venue[data-known="false"]').count(),
    visible_streets:await group.locator('.weekly-venue-title').allTextContents(),
    missing_address_button:await group.getByRole('button',{name:/appuntamento senza sede identificata/}).count(),
  }
  await page.screenshot({path:'reports/audit/firenze-venues.png',animations:'disabled'})
  if(city.known_venues!==4)throw new Error('Expected 4 city venues, got '+city.known_venues)
  return city
})

await stage('Saturday filter + source preservation',async()=>{
  await page.getByRole('button',{name:'Mostra mercati del sabato'}).click()
  const group=page.getByTestId('weekly-city-group').filter({hasText:'Mercati settimanali a Firenze'}).first()
  await group.getByText('Piazza i maggio',{exact:true}).waitFor({timeout:25000})
  await group.getByText('Largo Monzani',{exact:true}).waitFor({state:'hidden',timeout:25000})
  const known=await group.locator('.weekly-venue[data-known="true"]').count()
  const entries=await group.locator('.weekly-appointment').count()
  await page.screenshot({path:'reports/audit/firenze-saturday.png',animations:'disabled'})
  if(known!==1)throw new Error('Saturday should show one identified venue, got '+known)
  await page.getByRole('button',{name:'Togli filtro giorno'}).click()
  return {known_venues:known,source_appointments:entries}
})

await stage('source details and recency labels',async()=>{
  const first=page.locator('.market-card .card-name').first()
  await page.locator('.market-card-open').first().click()
  await page.locator('.detail-page').waitFor({timeout:20000})
  await page.getByText('Caricamento dettagli completi…').waitFor({state:'hidden',timeout:20000})
  const d = {
    title:await page.locator('.detail-name').innerText(),
    source_links:await page.locator('.detail-page a[href^="http"]').count(),
    date_quality_note:await page.getByText(/Date previste, non confermate/i).count(),
    share_button:await page.getByRole('button',{name:'Condividi questo mercato'}).count()
  }
  await page.locator('.detail-back').click()
  return d
})

await stage('filters and favorites across navigation',async()=>{
  await page.locator('.bottom-tabs').getByRole('button',{name:'Impostazioni'}).click()
  await page.getByRole('button',{name:/Scegli una città/}).click()
  await page.locator('.manual-city-input input').fill('Milano')
  await page.getByRole('button',{name:'Filtra città'}).click()
  const before=await page.locator('.results-count').innerText()
  await page.locator('.bottom-tabs').getByRole('button',{name:'Preferiti'}).click()
  const favs=await page.getByText('Nessun preferito').count()
  await page.locator('.bottom-tabs').getByRole('button',{name:'Esplora'}).click()
  const after=await page.locator('.results-count').innerText()
  return {before,after,favorites_empty:favs===1,city_filter_persisted:before===after}
})

await stage('map lazy load and navigation',async()=>{
  await page.getByRole('button',{name:'Mappa',exact:true}).first().click()
  await page.locator('.maplibregl-map').waitFor({timeout:20000})
  const data={
    webgl_canvas:await page.locator('.maplibregl-canvas').count(),
    first_load_message:await page.getByText('Caricamento mappa…').count(),
    source_label:await page.getByText(/posizioni indicative/i).count()
  }
  await page.screenshot({path:'reports/audit/map-mobile.png',animations:'disabled'})
  await page.getByRole('button',{name:'Lista',exact:true}).first().click()
  return data
})

await stage('accessibility grouped venue state',async()=>{
  // Return to city filter, then open a group.
  await page.locator('.bottom-tabs').getByRole('button',{name:'Impostazioni'}).click()
  await page.getByRole('button',{name:/Scegli una città/}).click()
  await page.locator('.manual-city-input input').fill('Firenze')
  await page.getByRole('button',{name:'Filtra città'}).click()
  const group=page.getByTestId('weekly-city-group').filter({hasText:'Mercati settimanali a Firenze'}).first()
  await group.waitFor({timeout:20000})
  await group.getByRole('button',{name:'Visualizza sedi e giornate'}).click()
  await group.getByText('Largo Monzani',{exact:true}).waitFor({timeout:15000})
  const a=await new AxeBuilder({page}).withTags(['wcag2a','wcag2aa','wcag21a','wcag21aa']).analyze()
  const violations=a.violations.map(v=>({
    rule:v.id,impact:v.impact,nodes:v.nodes.length,target_example:v.nodes[0]?.target?.slice(0,3)
  }))
  report.wcag.push({stage:'expanded-firenze',violations})
  return {violations:violations.length,top:violations.slice(0,12)}
})

await stage('HTTP and asset cost summary',async()=>{
  let transfer=0
  const assets={}
  for(const req of requests) {
    if(!req.url().startsWith(new URL(BASE).origin))continue
    try {
      const stats=await req.sizes()
      const path = new URL(req.url()).pathname
      transfer+=stats.responseBodySize
      assets[path]=(assets[path]||0)+stats.responseBodySize
    }catch{}
  }
  const entries=Object.entries(assets).sort((a,b)=>b[1]-a[1])
  return {requests:requests.length,first_party_bytes:transfer,largest:entries.slice(0,15)}
})

await fs.mkdir('reports/audit',{recursive:true})
report.failed_stages=report.stages.filter(s=>!s.success).length
report.completed_stages=report.stages.length
await fs.writeFile(OUT,JSON.stringify(report,null,2)+'\n')
console.log('AUDIT_SUMMARY',JSON.stringify({
  failed_stages:report.failed_stages,stages:report.completed_stages,
  first_card_ms:report.stages[0]?.detail?.first_market_card_ms,
  page_errors:report.page_errors.length,
  http_errors:report.response_errors.length,
  failed_requests:report.request_errors.length,
  axe_violations:report.wcag.map(x=>({stage:x.stage,violations:x.violations.length})),
},null,2))
await context.close()
await browser.close()
