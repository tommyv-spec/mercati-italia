import test from 'node:test'
import assert from 'node:assert/strict'
import { fetchMarkets, fetchMarketById } from '../src/services/staticMarkets.js'

const cityId='cernobbio-mercatino-delle-curiosita-mercatino-delle-curiosita'
const hold='indirizzo_e_punto_sorgente_non_riconciliati'
const source='https://www.cosedicasa.com/mercatini/cernobbio-mercatino-delle-curiosita'

test('municipality navigation hold and publisher links survive regional lazy-load', async () => {
  const previous=globalThis.fetch
  const urls=[]
  const summary=[cityId, 'Mercatino delle Curiosità', 'Cernobbio',
    'Lombardia','misto',[],null,null,'sconosciuta','',
    'sconosciuta',[]]
  const detail={
    slug:cityId,nome:'Mercatino delle Curiosità',citta:'Cernobbio',
    regione:'Lombardia',indirizzo:'Via Roma 15',lat:null,lng:null,
    position_quality:'sconosciuta',
    navigazione_sospesa_motivo:hold,
    coordinate_sospese_motivo:'coordinate_sorgente_incompatibili_con_localita_documentata',
    fonti:[{nome:'Fonte comunale',url:source}],
    date_quality:'sconosciuta',date:[],
    fonte:'Editore originale',url_fonte:source,
  }
  globalThis.fetch=async (url)=>{
    const s=String(url)
    urls.push(s)
    if(s.endsWith('/manifest.json')) return {ok:true,json:async()=>({
      schema:1,layout:'regional',total:1,regions:[{
        name:'Lombardia',count:1,path:'data/v1/regions/lombardia-proof.json',
      }],
      index:'data/v1/index-proof.json',
    })}
    if(s.endsWith('/index-proof.json')) return {ok:true,json:async()=>({
      schema:1,markets:[summary],
    })}
    if(s.endsWith('/lombardia-proof.json')) return {ok:true,json:async()=>({
      schema:1,markets:[detail],
    })}
    throw new Error('Unapproved source request: '+s)
  }
  try{
    const list=await fetchMarkets()
    assert.equal(list.length,1)
    assert.equal(list[0].id,cityId)
    assert.equal(list[0].navigazione_sospesa_motivo,'',
      'Search index is intentionally compact; cannot be trusted for navigation')
    const reviewed=await fetchMarketById(cityId)
    assert.equal(reviewed.navigazione_sospesa_motivo,hold,
      'Source-bound navigation hold must reach React detail adapter')
    assert.equal(reviewed.coordinate_sospese_motivo,
      'coordinate_sorgente_incompatibili_con_localita_documentata')
    assert.equal(reviewed.lat,null)
    assert.deepEqual(reviewed.fonti,[{nome:'Fonte comunale',url:source}])
    assert.equal(urls.filter(url=>url.endsWith('/lombardia-proof.json')).length,1)
    assert.equal(urls.length,3,'No dynamic Firestore/Worker calls to read regional details')
  } finally{
    globalThis.fetch=previous
  }
})
