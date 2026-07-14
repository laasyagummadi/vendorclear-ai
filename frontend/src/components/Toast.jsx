import { useEffect } from 'react'

export default function Toast({ id, msg, type, onRemove }) {
  useEffect(() => {
    const t = setTimeout(() => onRemove(id), 3500)
    return () => clearTimeout(t)
  }, [id, onRemove])

  return (
    <div className={`toast ${type}`}>{msg}</div>
  )
}
