import { useEffect, useState } from 'react'
import Icon from './Icon.jsx'

// "Dove" and "Quando", always in view: one tap opens the sheet to change each. Once the page
// scrolls the bar drops its two small labels, so the stuck band leaves more room to the list.
export default function ContextBar({ whereLabel, whenLabel, onWhere, onWhen, barRef }) {
  const [stuck, setStuck] = useState(false)
  useEffect(() => {
    const onScroll = () => setStuck(window.scrollY > 160)
    onScroll()
    window.addEventListener('scroll', onScroll, { passive: true })
    return () => window.removeEventListener('scroll', onScroll)
  }, [])
  return (
    <div className={'context-bar' + (stuck ? ' stuck' : '')} ref={barRef}>
      <button type="button" className="ctx" onClick={onWhere}>
        <Icon name="mapPin" size={17} strokeWidth={2} />
        <span className="ctx-text"><span className="ctx-k">Dove</span><span className="ctx-v">{whereLabel}</span></span>
        <Icon name="chevronDown" size={16} strokeWidth={2.2} />
      </button>
      <button type="button" className="ctx" onClick={onWhen}>
        <Icon name="calendar" size={17} strokeWidth={2} />
        <span className="ctx-text"><span className="ctx-k">Quando</span><span className="ctx-v">{whenLabel}</span></span>
        <Icon name="chevronDown" size={16} strokeWidth={2.2} />
      </button>
    </div>
  )
}
