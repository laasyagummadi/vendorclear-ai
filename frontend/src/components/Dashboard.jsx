import { useState, useEffect, useRef } from 'react'
import { api } from '../api.js'
import Chart from 'chart.js/auto'

export default function Dashboard({ navigate, toast }) {
  const [summary, setSummary] = useState(null)
  const riskRef = useRef(null)
  const statusRef = useRef(null)
  const charts = useRef({})

  useEffect(() => {
    api('GET', '/dashboard/summary').then(setSummary).catch(() => setSummary(null))
  }, [])

  useEffect(() => {
    if (!summary) return
    const rt = summary?.risk_tiers || {}
    const v = summary?.vendors || {}
    Object.values(charts.current).forEach(c => { try { c.destroy() } catch(e){} })
    charts.current = {}
    if (riskRef.current) {
      charts.current.risk = new Chart(riskRef.current, {
        type: 'doughnut',
        data: { labels: ['Low','Medium','High','Critical'],
          datasets: [{ data: [rt.low||0,rt.medium||0,rt.high||0,rt.critical||0],
            backgroundColor:['#052e16','#1c1003','#1c0a0a','#2a0a0a'],
            borderColor:['#4ade80','#fbbf24','#f87171','#f43f5e'], borderWidth:2 }]
        },
        options: { responsive:true, maintainAspectRatio:false, cutout:'65%',
          plugins:{ legend:{ position:'bottom', labels:{ color:'#555', font:{size:11}, boxWidth:10, padding:12 } } }
        }
      })
    }
    if (statusRef.current) {
      charts.current.status = new Chart(statusRef.current, {
        type: 'bar',
        data: { labels:['Compliant','Needs Review','Non-Compliant','Pending'],
          datasets: [{ data:[v.compliant||0,v.needs_review||0,v.non_compliant||0,v.pending||0],
            backgroundColor:['#052e16','#1c1003','#1c0a0a','#111'],
            borderColor:['#4ade80','#fbbf24','#f87171','#333'], borderWidth:1.5, borderRadius:6 }]
        },
        options: { responsive:true, maintainAspectRatio:false,
          plugins:{legend:{display:false}},
          scales:{ x:{grid:{color:'#111'},ticks:{color:'#555',font:{size:11}}},
                   y:{grid:{color:'#111'},ticks:{color:'#555',font:{size:11}},beginAtZero:true} }
        }
      })
    }
    return () => { Object.values(charts.current).forEach(c => { try { c.destroy() } catch(e){} }) }
  }, [summary])

  const v = summary?.vendors || {}
  const d = summary?.documents || {}
  const al = summary?.alerts || {}

  function ProgressBar({ label, val, total, color }) {
    const pct = total > 0 ? Math.round((val/total)*100) : 0
    return (
      <div>
        <div style={{ display:'flex', justifyContent:'space-between', marginBottom:4 }}>
          <span style={{ fontSize:12, color:'#555' }}>{label}</span>
          <span style={{ fontSize:12, color:'#777' }}>{val} <span style={{ color:'#333' }}>({pct}%)</span></span>
        </div>
        <div style={{ height:4, background:'#111', borderRadius:4 }}>
          <div style={{ height:4, background:color, borderRadius:4, width:`${pct}%`, transition:'width .4s' }} />
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Dashboard</div>
          <div className="page-sub">VendorClear AI — {new Date().toLocaleDateString('en-US',{weekday:'long',year:'numeric',month:'long',day:'numeric'})}</div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={() => window.location.reload()}>↺ Refresh</button>
      </div>

      <div className="stat-grid">
        <div className="stat-box">
          <div className="stat-label">Total Vendors</div>
          <div className="stat-val">{v.total ?? '—'}</div>
          <div className="stat-sub">{v.active ?? 0} active</div>
        </div>
        <div className="stat-box">
          <div className="stat-label">Compliance Rate</div>
          <div className="stat-val" style={{ color: (v.compliance_rate_pct||0)>=80?'#4ade80':(v.compliance_rate_pct||0)>=50?'#fbbf24':'#f87171' }}>
            {(v.compliance_rate_pct??0).toFixed(0)}%
          </div>
          <div className="stat-sub">{v.compliant ?? 0} compliant vendors</div>
        </div>
        <div className="stat-box">
          <div className="stat-label">Documents</div>
          <div className="stat-val">{d.total ?? '—'}</div>
          <div className="stat-sub">{d.processed ?? 0} processed</div>
        </div>
        <div className="stat-box">
          <div className="stat-label">Open Alerts</div>
          <div className="stat-val" style={{ color: (al.total||0)>0?'#fbbf24':'#4ade80' }}>{al.total ?? 0}</div>
          <div className="stat-sub">{al.expiry ?? 0} expiry · {al.compliance ?? 0} compliance</div>
        </div>
      </div>

      <div className="charts-row">
        <div className="card">
          <div style={{ fontSize:14, fontWeight:600, marginBottom:16 }}>Risk Tier Distribution</div>
          <div style={{ position:'relative', height:200 }}><canvas ref={riskRef} /></div>
        </div>
        <div className="card">
          <div style={{ fontSize:14, fontWeight:600, marginBottom:16 }}>Vendor Status Overview</div>
          <div style={{ position:'relative', height:200 }}><canvas ref={statusRef} /></div>
        </div>
      </div>

      <div style={{ display:'grid', gridTemplateColumns:'1fr 1fr', gap:16 }}>
        <div className="card">
          <div style={{ fontSize:14, fontWeight:600, marginBottom:16 }}>Document Processing</div>
          <div style={{ display:'flex', flexDirection:'column', gap:10 }}>
            <ProgressBar label="Processed" val={d.processed||0} total={d.total||1} color="#4ade80" />
            <ProgressBar label="Pending" val={d.pending||0} total={d.total||1} color="#fbbf24" />
            <ProgressBar label="Failed" val={d.failed||0} total={d.total||1} color="#f87171" />
          </div>
        </div>
        <div className="card">
          <div style={{ fontSize:14, fontWeight:600, marginBottom:16 }}>Quick Actions</div>
          <div style={{ display:'flex', flexDirection:'column', gap:8 }}>
            <button className="btn btn-ghost" style={{ justifyContent:'flex-start' }}
              onClick={() => { navigate('vendors') }}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Add New Vendor
            </button>
            <button className="btn btn-ghost" style={{ justifyContent:'flex-start' }} onClick={() => navigate('alerts')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M18 8A6 6 0 006 8c0 7-3 9-3 9h18s-3-2-3-9"/></svg>
              View Alerts ({al.total||0})
            </button>
            <button className="btn btn-ghost" style={{ justifyContent:'flex-start' }} onClick={() => navigate('report')}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M14 2H6a2 2 0 00-2 2v16"/><polyline points="14 2 14 8 20 8"/></svg>
              Compliance Report
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
