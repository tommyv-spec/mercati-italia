import Icon from './Icon.jsx'

// A sheet that slides up from the bottom; the backdrop and the cross close it.
export default function Sheet({ title, onClose, children }) {
  return (
    <>
      <div className="sheet-backdrop" onClick={onClose} />
      <div className="sheet" role="dialog" aria-label={title}>
        <div className="sheet-head">
          <h2>{title}</h2>
          <button type="button" className="ico-btn" aria-label="Chiudi" onClick={onClose}><Icon name="x" size={18} /></button>
        </div>
        {children}
      </div>
    </>
  )
}
