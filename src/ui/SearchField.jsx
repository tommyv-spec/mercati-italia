import Icon from './Icon.jsx'

export default function SearchField({ value, onChange, onSubmit, autoFocus = false }) {
  return (
    <label className="search-field">
      <Icon name="search" size={18} />
      <span className="sr-only">Cerca</span>
      <input className="search-input" type="search" value={value} autoFocus={autoFocus}
        placeholder="Cerca città, mercatino o regione"
        onChange={e => onChange(e.target.value)}
        onKeyDown={e => { if (e.key === 'Enter' && onSubmit) onSubmit() }} />
    </label>
  )
}
