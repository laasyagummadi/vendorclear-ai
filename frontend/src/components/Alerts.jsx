import { useState, useEffect } from 'react'
import { api } from '../api.js'
import { fmtDate, statusBadgeClass } from '../helpers.js'

export default function Alerts({ navigate, toast, user }) {
  const [alerts, setAlerts] = useState(null)
  const [notifying, setNotifying] = useState(false)
  const [history, setHistory] = useState([])
  const [historyLoading, setHistoryLoading] = useState(true)

  function load() {
    api('GET', '/alerts?expiry_days=30').then(setAlerts).catch(() => setAlerts({ expiry_alerts:[], compliance_alerts:[], total:0 }))
  }

  function loadHistory() {
    setHistoryLoading(true)
    api('GET', '/alerts/notifications?limit=20')
      .then(res => setHistory(Array.isArray(res) ? res : []))
      .catch(() => setHistory([]))
      .finally(() => setHistoryLoading(false))
  }

  useEffect(() => { load(); loadHistory() }, [])

  const exp = alerts?.expiry_alerts || []
  const comp = alerts?.compliance_alerts || []
  const escalated = [...exp, ...comp].filter(a => a.escalated)
  const escalatedCount = alerts?.escalated_count ?? escalated.length
  const canNotify = user?.role === 'ADMIN' || user?.role === 'ANALYST'

  async function notifyVendors() {
    setNotifying(true)
    try {
      const res = await api('POST', '/alerts/notify?expiry_days=30', null, false, false, 20000)
      if (res?.disabled_reason) {
        toast?.(res.disabled_reason, 'error')
      } else {
        const parts = []
        if (res?.sent) parts.push(`${res.sent} vendor${res.sent !== 1 ? 's' : ''} emailed`)
        if (res?.skipped_no_email) parts.push(`${res.skipped_no_email} skipped (no email on file)`)
        if (res?.failed) parts.push(`${res.failed} failed`)
        toast?.(parts.length ? parts.join(' · ') : 'No new alerts to notify vendors about', res?.failed ? 'error' : 'success')
      }
    } catch (e) {
      toast?.(e?.data?.error || e?.data?.detail || 'Failed to send vendor notifications', 'error')
    } finally {
      setNotifying(false)
      loadHistory()
    }
  }

  function PriorityBadge({ a }) {
    if (!a.priority) return null
    const color = a.priority === 'CRITICAL' ? '#f87171' : a.priority === 'HIGH' ? '#fbbf24' : '#4ade80'
    return (
      <span style={{ fontSize:10, fontWeight:700, letterSpacing:'.04em', textTransform:'uppercase', color, border:`1px solid ${color}`, borderRadius:20, padding:'1px 7px', marginLeft:8 }}>
        {a.escalated ? '⚠ Escalated' : a.priority}
      </span>
    )
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Alerts</div>
          <div className="page-sub">{(alerts?.total||0)} open alert{(alerts?.total||0)!==1?'s':''}{escalatedCount ? ` · ${escalatedCount} escalated` : ''}</div>
        </div>
        <div style={{ display:'flex', gap:8 }}>
          {canNotify && (
            <button className="btn btn-sm" onClick={notifyVendors} disabled={notifying}>
              {notifying ? 'Sending…' : '✉ Notify Vendors'}
            </button>
          )}
          <button className="btn btn-ghost btn-sm" onClick={load}>↺ Refresh</button>
        </div>
      </div>

      {escalated.length > 0 && (
        <div className="card" style={{ marginBottom:20, borderColor:'#f87171' }}>
          <div style={{ fontSize:13, fontWeight:700, color:'#f87171', textTransform:'uppercase', letterSpacing:'.06em', marginBottom:10 }}>
            ⚠ Escalated — needs immediate attention ({escalated.length})
          </div>
          <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
            {escalated.map((a, i) => (
              <div key={i} className="alert-item" style={{ borderLeft:'3px solid #f87171' }}>
                <div className="alert-item-title">{a.vendor_name}<PriorityBadge a={a} /></div>
                <div className="alert-item-sub">
                  {a.alert_type === 'COMPLIANCE_ISSUE'
                    ? <span className={`badge ${statusBadgeClass(a.status)}`}>{a.status}</span>
                    : <>{a.coverage_type}{a.days_overdue > 0 ? ` — overdue by ${a.days_overdue} days` : ` — expires in ${a.days_until_expiry} days`}</>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:20 }}>
        <div>
          <div style={{ fontSize:13, fontWeight:600, color:'#777', textTransform:'uppercase', letterSpacing:'.06em', marginBottom:12 }}>
            Expiry Alerts ({exp.length})
          </div>
          {exp.length === 0
            ? <div className="card"><div className="empty-state" style={{ padding:24 }}><div className="icon" style={{ fontSize:24 }}>✓</div><p>No expiry alerts</p></div></div>
            : exp.map((a, i) => (
              <div key={i} className="alert-item" style={{ borderLeft:`3px solid ${a.days_until_expiry<=7?'#f87171':'#fbbf24'}` }}>
                <div className="alert-item-title">{a.vendor_name}<PriorityBadge a={a} /></div>
                <div className="alert-item-sub">
                  {a.coverage_type || ''}{' '}
                  {a.days_overdue > 0
                    ? <strong style={{ color:'#f87171' }}>overdue by {a.days_overdue} days</strong>
                    : <>expires in <strong style={{ color:a.days_until_expiry<=7?'#f87171':'#fbbf24' }}>{a.days_until_expiry} days</strong></>}
                </div>
                <div className="alert-item-sub mt-1">Expires: {fmtDate(a.expiry_date)}</div>
              </div>
            ))
          }
        </div>
        <div>
          <div style={{ fontSize:13, fontWeight:600, color:'#777', textTransform:'uppercase', letterSpacing:'.06em', marginBottom:12 }}>
            Compliance Alerts ({comp.length})
          </div>
          {comp.length === 0
            ? <div className="card"><div className="empty-state" style={{ padding:24 }}><div className="icon" style={{ fontSize:24 }}>✓</div><p>No compliance alerts</p></div></div>
            : comp.map((a, i) => (
              <div key={i} className="alert-item" style={{ borderLeft:'3px solid #f87171' }}>
                <div className="alert-item-title">{a.vendor_name}<PriorityBadge a={a} /></div>
                <div className="alert-item-sub"><span className={`badge ${statusBadgeClass(a.status)}`}>{a.status||'—'}</span></div>
                {a.message && <div className="alert-item-sub mt-1">{a.message}</div>}
              </div>
            ))
          }
        </div>
      </div>

      <div className="card" style={{ marginTop:20 }}>
        <div style={{ display:'flex', alignItems:'center', justifyContent:'space-between', marginBottom:12 }}>
          <div style={{ fontSize:13, fontWeight:600, color:'#777', textTransform:'uppercase', letterSpacing:'.06em' }}>
            Recent Notifications ({history.length})
          </div>
          <button className="btn btn-ghost btn-sm" onClick={loadHistory}>↺ Refresh</button>
        </div>
        <div style={{ fontSize:11, color:'#555', marginBottom:12 }}>
          Emails are sent through the SMTP server configured in the backend .env (currently a Mailtrap
          sandbox inbox in this environment, not vendors' real inboxes). Every send attempt — success
          or failure — is logged below, whether triggered by "Notify Vendors" or the daily scheduled job.
        </div>
        {historyLoading ? (
          <div className="empty-state" style={{ padding:16 }}><div className="spinner" style={{ width:18, height:18, borderWidth:2, margin:'0 auto' }} /></div>
        ) : history.length === 0 ? (
          <div className="empty-state" style={{ padding:16 }}><p>No notification emails sent yet. Click "Notify Vendors" above to send the first batch.</p></div>
        ) : (
          <table className="tbl">
            <thead><tr><th>Vendor</th><th>Recipient</th><th>Type</th><th>Urgency</th><th>Sent</th><th>Result</th></tr></thead>
            <tbody>
              {history.map(h => (
                <tr key={h.id}>
                  <td>{h.vendor_name || '—'}</td>
                  <td style={{ fontSize:12, color:'#888' }}>{h.recipient_email}</td>
                  <td style={{ fontSize:12 }}>{h.coverage_type || h.alert_type}</td>
                  <td style={{ fontSize:12 }}>{h.urgency_bucket}</td>
                  <td style={{ fontSize:12, color:'#888' }}>{fmtDate(h.sent_at)}</td>
                  <td>
                    {h.success
                      ? <span style={{ fontSize:11, fontWeight:700, color:'#4ade80' }}>✓ Sent</span>
                      : (
                        <div>
                          <span style={{ fontSize:11, fontWeight:700, color:'#f87171' }}>✕ Failed</span>
                          {h.error_message && (
                            <div style={{ fontSize:11, color:'#f87171', opacity:0.8, marginTop:2, maxWidth:280 }}>
                              {h.error_message}
                            </div>
                          )}
                        </div>
                      )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  )
}
