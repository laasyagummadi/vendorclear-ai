import { useState, useEffect } from 'react'
import { api } from '../api.js'

// Module 7 — Audit Trail viewer, with Module 8 version-history drill-down.
// Visible to ADMIN and AUDITOR (backend enforces AUDIT_VIEW).
export default function AuditLog({ toast }) {
  const [logs, setLogs] = useState([])
  const [total, setTotal] = useState(0)
  const [entityType, setEntityType] = useState('')
  const [action, setAction] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [expanded, setExpanded] = useState(null)
  const [history, setHistory] = useState(null)

  function load() {
    setLoading(true)
    const q = new URLSearchParams()
    if (entityType) q.set('entity_type', entityType)
    if (action) q.set('action', action)
    q.set('limit', '100')
    api('GET', `/audit/logs?${q}`)
      .then(r => { setLogs(r.logs || []); setTotal(r.total || 0); setError('') })
      .catch(e => setError(e?.data?.detail || 'Audit access requires admin or auditor role.'))
      .finally(() => setLoading(false))
  }
  useEffect(load, [entityType, action])

  async function loadHistory(log) {
    if (!log.entity_id) return
    try {
      const h = await api('GET', `/audit/history/${log.entity_type}/${log.entity_id}`)
      setHistory(h)
    } catch { setHistory(null) }
  }

  const actionClass = a => ({
    CREATE: 'badge-green', UPDATE: 'badge-blue', DELETE: 'badge-red',
    LOGIN: 'badge-gray', APPROVE: 'badge-green', REJECT: 'badge-red',
    CONFIG_CHANGE: 'badge-yellow', UPLOAD: 'badge-blue',
  }[a] || 'badge-gray')

  if (loading) return <div className="empty-state"><p>Loading audit trail…</p></div>
  if (error) return (
    <div>
      <div className="page-header"><div><div className="page-title">Audit Trail</div></div></div>
      <div className="card"><div className="empty-state"><p>{error}</p></div></div>
    </div>
  )

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Audit Trail</div>
          <div className="page-sub">{total} recorded action(s) · who changed what, and when</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 14, flexWrap: 'wrap' }}>
        <select className="form-input" style={{ width: 190 }} value={entityType}
                onChange={e => setEntityType(e.target.value)}>
          <option value="">All entity types</option>
          <option value="vendor">Vendor</option>
          <option value="version_config">Configuration</option>
          <option value="policy_submission">Submission</option>
          <option value="user">User</option>
        </select>
        <select className="form-input" style={{ width: 190 }} value={action}
                onChange={e => setAction(e.target.value)}>
          <option value="">All actions</option>
          {['CREATE','UPDATE','DELETE','LOGIN','APPROVE','REJECT','CONFIG_CHANGE'].map(a =>
            <option key={a} value={a}>{a}</option>)}
        </select>
        <button className="btn btn-ghost btn-sm" onClick={load}>Refresh</button>
      </div>

      {logs.length === 0
        ? <div className="card"><div className="empty-state"><p>No audit entries match.</p></div></div>
        : <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
            <table className="tbl">
              <thead><tr><th>When</th><th>Action</th><th>Entity</th><th>Who</th><th>Summary</th></tr></thead>
              <tbody>
                {logs.map(l => (
                  <>
                    <tr key={l.id} onClick={() => {
                          const next = expanded === l.id ? null : l.id
                          setExpanded(next); setHistory(null)
                          if (next) loadHistory(l)
                        }}>
                      <td style={{ fontSize: 12, whiteSpace: 'nowrap' }}>
                        {(l.timestamp || '').replace('T', ' ').slice(0, 19)}
                      </td>
                      <td><span className={`badge ${actionClass(l.action)}`}>{l.action}</span></td>
                      <td style={{ fontSize: 12 }}>
                        <div style={{ fontWeight: 600 }}>{l.entity_name || l.entity_type}</div>
                        <div style={{ color: '#605e5c' }}>{l.entity_type}</div>
                      </td>
                      <td style={{ fontSize: 12 }}>
                        {l.actor_email || '—'}
                        {l.actor_role && <div style={{ color: '#605e5c' }}>{l.actor_role}</div>}
                      </td>
                      <td style={{ fontSize: 12 }}>{l.summary || '—'}</td>
                    </tr>
                    {expanded === l.id && (
                      <tr key={l.id + '-d'}>
                        <td colSpan={5} style={{ background: '#faf9f8' }}>
                          <div style={{ padding: '6px 0 12px' }}>
                            {l.changes && Object.keys(l.changes).length > 0 && (
                              <>
                                <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 6 }}>What changed</div>
                                <table style={{ fontSize: 12, marginBottom: 12 }}>
                                  <tbody>
                                    {Object.entries(l.changes).map(([k, v]) => (
                                      <tr key={k}>
                                        <td style={{ padding: '2px 14px 2px 0', fontWeight: 600 }}>{k.replace(/_/g, ' ')}</td>
                                        <td style={{ padding: '2px 8px', color: '#a4262c' }}>{String(v.from)}</td>
                                        <td style={{ padding: '2px 8px' }}>→</td>
                                        <td style={{ padding: '2px 8px', color: '#107c10', fontWeight: 600 }}>{String(v.to)}</td>
                                      </tr>
                                    ))}
                                  </tbody>
                                </table>
                              </>
                            )}
                            {history?.versions?.length > 0 && (
                              <>
                                <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 6 }}>
                                  Version history ({history.versions.length})
                                </div>
                                {history.versions.slice(0, 6).map(v => (
                                  <div key={v.version} style={{ fontSize: 12, marginBottom: 3 }}>
                                    <span className="badge badge-gray">v{v.version}</span>{' '}
                                    <span style={{ color: '#605e5c' }}>{(v.date || '').replace('T',' ').slice(0,19)}</span>{' · '}
                                    <span>{v.uploader || 'system'}</span>
                                    {v.note && <span style={{ color: '#605e5c' }}> · {v.note}</span>}
                                  </div>
                                ))}
                              </>
                            )}
                            {!l.changes && !history?.versions?.length && (
                              <div style={{ fontSize: 12, color: '#605e5c' }}>No field-level detail recorded for this action.</div>
                            )}
                          </div>
                        </td>
                      </tr>
                    )}
                  </>
                ))}
              </tbody>
            </table>
          </div>
      }
    </div>
  )
}
