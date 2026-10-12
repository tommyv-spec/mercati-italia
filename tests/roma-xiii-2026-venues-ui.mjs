import assert from 'node:assert/strict'
import { chromium } from 'playwright'

const browser=await chromium.launch({headless:true})
const context=await browser.newContext({
 viewport:{width:390,height:844},isMobile:true,hasTouch:true,locale:'it-IT',
})
const page=await context.newPage()
const errors=[],backend=[]
page.on('pageerror',e=>errors.push(e.message))
page.on('request',r=>{
 if(/firestore\.googleapis\.com|firebaseio\.com|workers\.dev/i.test(r.url())) backend.push(r.url())
})
try{
 const response=await page.goto(process.env.UI_BASE||'http://127.0.0.1:4173/',{
   waitUntil:'domcontentloaded',timeout:45000,
 })
 assert.equal(response.status(),200)
 await page.locator('.market-card-open').first().waitFor({timeout:30000})
 for(const item of [
  {term:'Piazza Ormea',title:'Casalotti',file:'ux-rm13-ormea-2026.png'},
  {term:'Fogaccia',title:'Fogaccia',file:'ux-rm13-fogaccia-2026.png'},
  {term:'Torrevecchia',title:'Torrevecchia',file:'ux-rm13-torrevecchia-2026.png'},
  {term:'Valle Aurelia',title:'Valle Aurelia',file:'ux-rm13-valle-aurelia-2026.png'},
  {term:'San Silverio',title:'San Silverio',file:'ux-rm13-san-silverio-2026.png'},
 ]){
   await page.locator('.search-input').fill(item.term)
   const card=page.locator('.market-card').filter({hasText:item.title}).first()
   await card.waitFor({timeout:20000})
   await card.locator('.market-card-open').click()
   await page.locator('.detail-page').waitFor({timeout:15000})
   await page.getByText('Caricamento dettagli completi…').waitFor({
       state:'hidden',timeout:20000
   })
   const btn=page.getByRole('button',{name:/Indicazioni/}).first()
   assert.equal(await btn.isDisabled(),true,
      'Unverified municipal venue must not enable navigation: '+item.term)
   await page.screenshot({path:item.file,animations:'disabled'})
   await page.locator('.detail-back').click()
   await page.locator('.search-input').fill('')
   await page.locator('.market-card-open').first().waitFor({timeout:15000})
 }
 assert.deepEqual(errors,[])
 assert.deepEqual(backend,[])
 console.log('PASS: five source-reviewed Roma venues found on mobile, no unsafe directions or dynamic paid calls')
}finally{await browser.close()}
