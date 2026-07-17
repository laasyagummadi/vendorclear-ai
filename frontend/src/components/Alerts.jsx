import { useState, useEffect } from 'react'
import { api } from '../api.js'
import { fmtDate, statusBadgeClass } from '../helpers.js'

export default function Alerts({ navigate }) {
  const [alerts, setAlerts] = useState(null)

  function load() {
    api('GET', '/alerts?expiry_days=30').then(setAlerts).catch(() => setAlerts({ expiry_alerts:[], compliance_alerts:[], total:0 }))
  }

  useEffect(() => { load() }, [])

  const exp = alerts?.expiry_alerts || []
  const comp = alerts?.compliance_alerts || []

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Alerts</div>
          <div className="page-sub">{(alerts?.total||0)} open alert{(alerts?.total||0)!==1?'s':''}</div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load}>↺ Refresh</button>
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:20 }}>
        <div>
          <div style={{ fontSize:13, fontWeight:600, color:'#777', textTransform:'uppercase', letterSpacing:'.06em', marginBottom:12 }}>
            Expiry Alerts ({exp.length})
          </div>
          {exp.length === 0
            ? <div className="card"><div className="empty-state" style={{ padding:24 }}><div className="icon" style={{ fontSize:24 }}>✓</div><p>No expiry alerts</p></div></div>
            : exp.map((a, i) => (
              <div key={i} className="alert-item" style={{ borderLeft:`3px solid ${a.days_until_expiry<=7?'#f87171':'#fbbf24'}` }}>
                <div className="alert-item-title">{a.vendor_name}</div>
                <div className="alert-item-sub">
                  {a.coverage_type || ''} expires in <strong style={{ color:a.days_until_expiry<=7?'#f87171':'#fbbf24' }}>{a.days_until_expiry} days</strong>
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
                <div className="alert-item-title">{a.vendor_name}</div>
                <div className="alert-item-sub"><span className={`badge ${statusBadgeClass(a.status)}`}>{a.status||'—'}</span></div>
                {a.message && <div className="alert-item-sub mt-1">{a.message}</div>}
              </div>
            ))
          }
        </div>
      </div>
    </div>
  )
}
