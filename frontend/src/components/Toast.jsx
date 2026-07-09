import { useEffect } from 'react'

export default function Toast({ toasts, setToasts }) {
  useEffect(() => {
    if (!toasts.length) return
    const t = setTimeout(() => setToasts(prev => prev.slice(1)), 3500)
    return () => clearTimeout(t)
  }, [toasts])

  return (
    <>
      {toasts.map((t, i) => (
        <div key={i} className={`toast ${t.type}`}>{t.msg}</div>
      ))}
    </>
  )
}
