export default function Pill({ active = false, onClick, children }) {
  return (
    <button type="button" className={'pill' + (active ? ' active' : '')} onClick={onClick}>{children}</button>
  )
}
