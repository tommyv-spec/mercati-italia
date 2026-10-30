export default function Skeleton({ rows = 4 }) {
  return (
    <div aria-hidden="true">
      {Array.from({ length: rows }, (_, i) => <div key={i} className="skeleton-row" />)}
    </div>
  )
}
