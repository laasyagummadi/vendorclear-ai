import { useState, useEffect } from 'react'
import { api } from '../api.js'
import { fmtDate, isExpiring, statusBadgeClass, riskBadgeClass } from '../helpers.js'

export default function Report({ navigate }) {
  const [report, setReport] = useState(null)

  function load() {
    api('GET', '/dashboard/compliance-report').then(setReport).catch(() => setReport(null))
  }

  useEffect(() => { load() }, [])

  const vendors = report?.vendors || []
  const sum = report?.summary || {}

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Compliance Report</div>
          <div className="page-sub">Generated {fmtDate(report?.report_date) || 'now'} · {vendors.length} vendors</div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load}>↺ Refresh</button>
      </div>

      <div className="stat-grid" style={{ marginBottom:20 }}>
        <div className="stat-box"><div className="stat-label">Total Vendors</div><div className="stat-val">{sum.total_vendors??'—'}</div></div>
        <div className="stat-box"><div className="stat-label">Avg Score</div><div className="stat-val">{sum.avg_score!=null?sum.avg_score.toFixed(0):'—'}</div></div>
        <div className="stat-box"><div className="stat-label">Compliant</div><div className="stat-val" style={{ color:'#4ade80' }}>{sum.compliant??'—'}</div></div>
        <div className="stat-box"><div className="stat-label">Non-Compliant</div><div className="stat-val" style={{ color:'#f87171' }}>{sum.non_compliant??'—'}</div></div>
      </div>

      <div className="card" style={{ padding:0, overflow:'hidden' }}>
        {vendors.length === 0
          ? <div className="empty-state"><p>No vendor data available.</p></div>
          : <table className="tbl">
              <thead><tr>
                <th>#</th><th>Vendor</th><th>Status</th><th>Risk</th>
                <th>Score</th><th>Grade</th><th>Documents</th><th>GL Expiry</th>
              </tr></thead>
              <tbody>
                {vendors.map((v, i) => {
                  const gc = v.grade==='A'?'#4ade80':v.grade==='B'?'#86efac':v.grade==='C'?'#fbbf24':v.grade==='D'?'#fb923c':'#f87171'
                  return (
                    <tr key={v.id} onClick={() => navigate('vendor-detail', v.id)}>
                      <td style={{ color:'#333' }}>{i+1}</td>
                      <td>
                        <div style={{ fontWeight:600 }}>{v.name}</div>
                        <div style={{ fontSize:11, color:'#444' }}>{v.email||''}</div>
                      </td>
                      <td><span className={`badge ${statusBadgeClass(v.status)}`}>{v.status||'—'}</span></td>
                      <td><span className={`badge ${riskBadgeClass(v.risk_tier)}`}>{v.risk_tier||'—'}</span></td>
                      <td>
                        <div style={{ display:'flex', alignItems:'center', gap:8 }}>
                          <div style={{ width:60, height:4, background:'#111', borderRadius:4 }}>
                            <div style={{ height:4, background:gc, borderRadius:4, width:`${v.total_score||0}%` }} />
                          </div>
                          <span style={{ fontSize:12, color:'#777' }}>{v.total_score??'—'}</span>
                        </div>
                      </td>
                      <td><span style={{ fontSize:18, fontWeight:700, color:gc }}>{v.grade||'?'}</span></td>
                      <td style={{ color:'#555', fontSize:12 }}>{v.document_count??0} doc{(v.document_count||0)!==1?'s':''}</td>
                      <td style={{ fontSize:12, color:isExpiring(v.gl_expiry)?'#f87171':'#555' }}>{fmtDate(v.gl_expiry)||'—'}</td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
        }
      </div>
    </div>
  )
}
