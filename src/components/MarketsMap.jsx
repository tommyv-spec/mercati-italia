import { useEffect, useMemo, useRef, useState } from 'react'
import * as maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'

// Public, keyless vector basemap; no Cloudflare Worker/D1/KV calls.
// https://openfreemap.org/quick_start/

const MAP_STYLE = 'https://tiles.openfreemap.org/styles/positron'
const COLORS = {
  'Alimentare': '#5B7A5E',
  'Antiquariato': '#C75146',
  'Vintage e abbigliamento': '#8B6F8E',
  'Usato': '#B8860B',
  'Artigianato': '#2E86AB',
  'Misto': '#7E796E',
}

function validPoint(market) {
  return Number.isFinite(market.lat) && Number.isFinite(market.lng) &&
    market.lat >= 35 && market.lat <= 48 && market.lng >= 6 && market.lng <= 20
}

export default function MarketsMap({ markets, userLat, userLng, onSelect }) {
  const containerRef = useRef(null)
  const mapRef = useRef(null)
  const onSelectRef = useRef(onSelect)
  const marketsRef = useRef(new Map())
  const popupRef = useRef(null)
  // At national scale, hiding all indicative positions leaves one
  // cluster near Milan and makes the map appear empty. Show these by
  // default with visible warnings and allow a precise-only toggle.
  const [showEstimated, setShowEstimated] = useState(true)
  const [ready, setReady] = useState(false)
  const [error, setError] = useState('')
  const hasUserPosition = Number.isFinite(userLat) && Number.isFinite(userLng)

  onSelectRef.current = onSelect
  marketsRef.current = new Map(markets.map(m => [m.id, m]))

  const pointMarkets = useMemo(
    () => markets.filter(validPoint), [markets]
  )
  const preciseCount = pointMarkets.filter(m => m.positionQuality === 'precisa').length
  const estimatedCount = pointMarkets.length - preciseCount
  const shown = useMemo(
    () => showEstimated ? pointMarkets : pointMarkets.filter(m => m.positionQuality === 'precisa'),
    [pointMarkets, showEstimated]
  )
  const geojson = useMemo(() => ({
    type: 'FeatureCollection',
    features: shown.map(m => ({
      type: 'Feature',
      geometry: { type: 'Point', coordinates: [m.lng, m.lat] },
      properties: {
        id: m.id,
        category: m.category,
        quality: m.positionQuality === 'precisa' ? 'precisa' : 'indicativa',
      },
    })),
  }), [shown])

  useEffect(() => {
    if (!containerRef.current) return undefined
    const center = hasUserPosition ? [userLng, userLat] : [12.5, 42.3]
    const map = new maplibregl.Map({
      container: containerRef.current,
      style: MAP_STYLE,
      center,
      zoom: hasUserPosition ? 9 : 4.75,
      minZoom: 4,
      maxZoom: 18,
      maxBounds: [[5.4, 35], [20.4, 48.6]],
      attributionControl: true,
      cooperativeGestures: false,
    })
    mapRef.current = map
    map.addControl(new maplibregl.NavigationControl({ visualizePitch: false }), 'top-right')

    const selectMarket = (feature, point) => {
      const market = marketsRef.current.get(feature.properties?.id)
      if (!market) return
      popupRef.current?.remove()
      const body = document.createElement('div')
      body.style.cssText = 'font:14px/1.4 system-ui;min-width:190px;max-width:260px'
      const title = document.createElement('strong')
      title.textContent = market.name
      body.append(title)
      const info = document.createElement('p')
      info.textContent = [market.city, market.category,
        market.positionQuality === 'precisa' ? 'Posizione precisa' : 'Posizione indicativa'
      ].filter(Boolean).join(' · ')
      info.style.cssText = 'margin:5px 0 12px;color:#61594e;font-size:12px'
      body.append(info)
      const open = document.createElement('button')
      open.textContent = 'Apri scheda'
      open.style.cssText = 'background:#C75146;color:#fff;border:0;border-radius:7px;padding:8px 13px;cursor:pointer'
      open.addEventListener('click', () => {
        popupRef.current?.remove()
        onSelectRef.current?.(market)
      })
      body.append(open)
      popupRef.current = new maplibregl.Popup({ offset: 14, closeOnClick: true })
        .setLngLat(point)
        .setDOMContent(body)
        .addTo(map)
    }

    map.on('load', () => {
      if (!mapRef.current) return
      map.addSource('markets', {
        type: 'geojson', data: { type: 'FeatureCollection', features: [] },
        cluster: true, clusterRadius: 46, clusterMaxZoom: 13,
      })
      map.addLayer({
        id: 'market-clusters', type: 'circle', source: 'markets',
        filter: ['has', 'point_count'],
        paint: {
          'circle-color': '#446F59',
          'circle-radius': ['step', ['get', 'point_count'], 18, 25, 24, 100, 31],
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 2,
        },
      })
      map.addLayer({
        id: 'cluster-counts', type: 'symbol', source: 'markets',
        filter: ['has', 'point_count'],
        layout: { 'text-field': ['get', 'point_count_abbreviated'], 'text-size': 12, 'text-font': ['Noto Sans Regular'] },
        paint: { 'text-color': '#ffffff' },
      })
      map.addLayer({
        id: 'market-markers', type: 'circle', source: 'markets',
        filter: ['!', ['has', 'point_count']],
        paint: {
          'circle-radius': ['interpolate', ['linear'], ['zoom'], 4, 5, 12, 9],
          'circle-color': ['match', ['get', 'category'],
            ...Object.entries(COLORS).flat(), '#646e65'],
          'circle-opacity': ['case', ['==', ['get', 'quality'], 'precisa'], 0.95, 0.58],
          'circle-stroke-color': '#ffffff',
          'circle-stroke-width': 2,
        },
      })
      map.on('click', 'market-clusters', async e => {
        const features = map.queryRenderedFeatures(e.point, { layers: ['market-clusters'] })
        const feature = features[0]
        if (!feature) return
        try {
          const zoom = await map.getSource('markets').getClusterExpansionZoom(feature.properties.cluster_id)
          map.easeTo({ center: feature.geometry.coordinates, zoom })
        } catch { /* map is still usable */ }
      })
      map.on('click', 'market-markers', e => {
        const f = e.features?.[0]
        if (f) selectMarket(f, f.geometry.coordinates)
      })
      for (const layer of ['market-clusters', 'market-markers']) {
        map.on('mouseenter', layer, () => { map.getCanvas().style.cursor = 'pointer' })
        map.on('mouseleave', layer, () => { map.getCanvas().style.cursor = '' })
      }
      setReady(true)
      setError('')
    })
    map.on('error', e => {
      if (!map.isStyleLoaded()) {
        setError('Impossibile caricare la mappa in questo momento. La ricerca in elenco funziona comunque.')
      }
    })
    return () => {
      popupRef.current?.remove()
      popupRef.current = null
      mapRef.current = null
      map.remove()
    }
    // Map initialized once per mount. Data and user location update below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    const map = mapRef.current
    if (!ready || !map?.getSource('markets')) return
    map.getSource('markets').setData(geojson)
  }, [geojson, ready])

  useEffect(() => {
    const map = mapRef.current
    if (ready && hasUserPosition && map) {
      map.easeTo({ center: [userLng, userLat], zoom: Math.max(map.getZoom(), 8.5), duration: 450 })
    }
  }, [ready, hasUserPosition, userLat, userLng])

  // When a city/region filter is applied, zoom to that place rather
  // than leaving the map centered on the whole country.
  useEffect(() => {
    const map = mapRef.current
    if (!ready || !map || hasUserPosition || shown.length === 0 || shown.length > 1200) return
    const bounds = new maplibregl.LngLatBounds()
    shown.forEach(m => bounds.extend([m.lng, m.lat]))
    map.fitBounds(bounds, { padding: 46, maxZoom: 12, duration: 400 })
  }, [shown, ready, hasUserPosition])

  return (
    <section aria-label="Mappa interattiva dei mercati" style={{ margin: '0 16px 110px' }}>
      <div style={{ background: 'var(--white)', borderRadius: 12, padding: '12px 14px', marginBottom: 10, fontSize: 13 }}>
        <strong>Mappa dei mercati</strong>
        <span style={{ display: 'block', color: 'var(--ink-lighter)', marginTop: 4 }}>
          {preciseCount} posizioni precise
          {estimatedCount ? ` · ${estimatedCount} posizioni indicative` : ''}
        </span>
        {estimatedCount > 0 && (
          <button type="button" onClick={() => setShowEstimated(v => !v)}
            style={{ border: '1px solid var(--beige-dark)', borderRadius: 20, padding: '8px 12px', marginTop: 8,
              background: showEstimated ? 'var(--ink)' : 'var(--white)',
              color: showEstimated ? '#fff' : 'var(--ink)', cursor: 'pointer', fontSize: 12 }}>
            {showEstimated ? 'Mostra solo posizioni precise' : 'Includi posizioni indicative'}
          </button>
        )}
        {shown.length === 0 && (
          <div style={{ marginTop: 8, color: 'var(--ink-lighter)', fontSize: 12 }}>
            Nessun mercato con posizione precisa per questi filtri. Puoi includere quelli indicativi.
          </div>
        )}
        {showEstimated && (
          <p style={{ fontSize: 12, color: '#886d42', margin: '8px 0 0' }}>
            Le posizioni indicative possono essere al centro del comune, non nella sede del mercato.
          </p>
        )}
      </div>
      <div ref={containerRef} role="application" aria-label="Mappa: trascina per spostarti, usa + e − per ingrandire"
        style={{ height: 'min(60vh, 600px)', minHeight: 340, width: '100%',
          borderRadius: 14, overflow: 'hidden', position: 'relative', background: '#e9eeea' }} />
      {error && <p role="alert" style={{ fontSize: 12, marginTop: 9, color: '#AB453B' }}>{error}</p>}
      {!ready && !error && <p style={{ fontSize: 12, marginTop: 9, color: 'var(--ink-lighter)' }}>Caricamento mappa…</p>}
      <p style={{ fontSize: 11, color: 'var(--ink-lighter)', marginTop: 10 }}>
        Mappa © OpenFreeMap e OpenStreetMap. Tocca un punto o un gruppo per esplorare.
        Le date dei mercati possono non essere confermate.
      </p>
    </section>
  )
}
