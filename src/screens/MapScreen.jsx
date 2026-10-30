import { Suspense, lazy } from 'react'
import Icon from '../ui/Icon.jsx'

const MarketsMap = lazy(() => import('../components/MarketsMap.jsx'))

// The map tab: the same markets the list shows, around the visitor or the chosen city when known.
export default function MapScreen({ markets, userLat, userLng, label, onSelect, onList }) {
  return (
    <div className="map-screen">
      <div className="map-bar">
        <button type="button" className="pill" onClick={onList}><Icon name="list" size={13} />{' '}Lista</button>
        <span className="note">{label}</span>
      </div>
      <Suspense fallback={<div role="status" className="list-note" style={{ padding: 22 }}>Caricamento mappa interattiva…</div>}>
        <MarketsMap markets={markets} userLat={userLat} userLng={userLng} onSelect={onSelect} />
      </Suspense>
    </div>
  )
}
