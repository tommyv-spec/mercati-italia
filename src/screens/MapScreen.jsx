import { Suspense, lazy } from 'react'
import Icon from '../ui/Icon.jsx'
import ContextBar from '../ui/ContextBar.jsx'

const MarketsMap = lazy(() => import('../components/MarketsMap.jsx'))

// The map follows the same Dove and Quando as Esplora, shown at the top.
export default function MapScreen({ markets, userLat, userLng, label, onSelect, onList, whereLabel, whenLabel, onOpenWhere, onOpenWhen }) {
  return (
    <div className="map-screen">
      <ContextBar whereLabel={whereLabel} whenLabel={whenLabel} onWhere={onOpenWhere} onWhen={onOpenWhen} />
      <div className="map-bar">
        <span className="map-label">{label}</span>
        <button type="button" className="pill" onClick={onList}><Icon name="list" size={13} />{' '}Lista</button>
      </div>
      <Suspense fallback={<div role="status" className="list-note" style={{ padding: 22 }}>Caricamento mappa interattiva…</div>}>
        <MarketsMap markets={markets} userLat={userLat} userLng={userLng} onSelect={onSelect} />
      </Suspense>
    </div>
  )
}
