import { useState, useEffect, useRef } from 'react'
import { api } from '../api.js'
import Chart from 'chart.js/auto'
import { severityBadgeClass } from '../helpers.js'

const MONTH_OPTIONS = [3, 6, 12]

export default function Analytics({ navigate, toast }) {
  const [data, setData] = useState(null)
  const [months, setMonths] = useState(6)
  const [loading, setLoading] = useState(true)

  const trendRef = useRef(null)
  const regionRef = useRef(null)
  const riskRef = useRef(null)
  const charts = useRef({})

  function load() {
    setLoading(true)
    api('GET', `/dashboard/analytics?months=${months}`)
      .then(setData).catch(() => setData(null)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [months])

  useEffect(() => {
    if (!data) return
    Object.values(charts.current).forEach(c => { try { c.destroy() } catch (e) {} })
    charts.current = {}

    const trend = data.monthly_compliance_trend || []
    if (trendRef.current && trend.length) {
      charts.current.trend = new Chart(trendRef.current, {
        type: 'line',
        data: {
          labels: trend.map(t => t.month),
          datasets: [{
            label: 'Compliance Rate %',
            data: trend.map(t => t.compliance_rate_pct),
            borderColor: '#4ade80',
            backgroundColor: 'rgba(74,222,128,0.12)',
            tension: 0.3,
            fill: true,
            pointBackgroundColor: '#4ade80',
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { color: '#111' }, ticks: { color: '#555', font: { size: 11 } } },
            y: { grid: { color: '#111' }, ticks: { color: '#555', font: { size: 11 } }, beginAtZero: true, max: 100 },
          },
        },
      })
    }

    const regions = data.regional_analysis || []
    if (regionRef.current && regions.length) {
      charts.current.region = new Chart(regionRef.current, {
        type: 'bar',
        data: {
          labels: regions.map(r => r.region),
          datasets: [{
            label: 'Compliance Rate %',
            data: regions.map(r => r.compliance_rate_pct),
            backgroundColor: '#052e16',
            borderColor: '#4ade80',
            borderWidth: 1.5,
            borderRadius: 6,
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { display: false } },
          scales: {
            x: { grid: { color: '#111' }, ticks: { color: '#555', font: { size: 11 } } },
            y: { grid: { color: '#111' }, ticks: { color: '#555', font: { size: 11 } }, beginAtZero: true, max: 100 },
          },
        },
      })
    }

    const rf = data.risk_distribution?.fleet_wide || {}
    if (riskRef.current) {
      charts.current.risk = new Chart(riskRef.current, {
        type: 'doughnut',
        data: {
          labels: ['Low', 'Medium', 'High'],
          datasets: [{
            data: [rf.LOW || 0, rf.MEDIUM || 0, rf.HIGH || 0],
            backgroundColor: ['#052e16', '#1c1003', '#1c0a0a'],
            borderColor: ['#4ade80', '#fbbf24', '#f87171'], borderWidth: 2,
          }],
        },
        options: {
          responsive: true, maintainAspectRatio: false, cutout: '65%',
          plugins: { legend: { position: 'bottom', labels: { color: '#555', font: { size: 11 }, boxWidth: 10, padding: 12 } } },
        },
      })
    }

    return () => { Object.values(charts.current).forEach(c => { try { c.destroy() } catch (e) {} }) }
  }, [data])

  const violations = data?.most_common_violations || []
  const byCategory = data?.risk_distribution?.by_category || {}

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Analytics</div>
          <div className="page-sub">Trends, regional breakdowns, and common compliance violations</div>
        </div>
        <div className="flex gap-2">
          <select className="form-input" style={{ padding: '7px 10px' }} value={months} onChange={e => setMonths(Number(e.target.value))}>
            {MONTH_OPTIONS.map(m => <option key={m} value={m}>Last {m} months</option>)}
          </select>
          <button className="btn btn-ghost btn-sm" onClick={load}>↺ Refresh</button>
        </div>
      </div>

      {loading ? (
        <div className="card" style={{ padding: 0 }}><div className="empty-state"><div className="spinner" style={{ width: 24, height: 24, borderWidth: 3, margin: '24px auto' }} /></div></div>
      ) : !data ? (
        <div className="card" style={{ padding: 0 }}><div className="empty-state"><p>Analytics data unavailable.</p></div></div>
      ) : (
        <>
          <div className="charts-row">
            <div className="card">
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Monthly Compliance Trend</div>
              <div style={{ fontSize: 11, color: '#555', marginBottom: 8 }}>Compliance rate among vendors onboarded each month</div>
              <div style={{ position: 'relative', height: 200 }}><canvas ref={trendRef} /></div>
            </div>
            <div className="card">
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Regional Analysis</div>
              <div style={{ fontSize: 11, color: '#555', marginBottom: 8 }}>Compliance rate by region</div>
              <div style={{ position: 'relative', height: 200 }}><canvas ref={regionRef} /></div>
            </div>
            <div className="card">
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Risk Distribution</div>
              <div style={{ fontSize: 11, color: '#555', marginBottom: 8 }}>Fleet-wide risk tier breakdown</div>
              <div style={{ position: 'relative', height: 200 }}><canvas ref={riskRef} /></div>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
            <div className="card">
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Most Common Violations</div>
              {violations.length === 0 ? (
                <div className="empty-state" style={{ padding: 16 }}><p>No findings recorded.</p></div>
              ) : (
                <table className="tbl">
                  <thead><tr><th>Rule</th><th>Severity</th><th>Occurrences</th><th>Vendors</th></tr></thead>
                  <tbody>
                    {violations.map(v => (
                      <tr key={v.rule_code}>
                        <td>
                          <div style={{ fontWeight: 600 }}>{v.rule_code}</div>
                          <div style={{ fontSize: 11, color: '#555' }}>{v.message}</div>
                        </td>
                        <td><span className={`badge ${severityBadgeClass(v.severity)}`}>{v.severity}</span></td>
                        <td>{v.occurrences}</td>
                        <td>{v.vendors_affected}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>

            <div className="card">
              <div style={{ fontSize: 14, fontWeight: 600, marginBottom: 16 }}>Risk by Category</div>
              {Object.keys(byCategory).length === 0 ? (
                <div className="empty-state" style={{ padding: 16 }}><p>No vendor categories yet.</p></div>
              ) : (
                <table className="tbl">
                  <thead><tr><th>Category</th><th>Low</th><th>Medium</th><th>High</th></tr></thead>
                  <tbody>
                    {Object.entries(byCategory).map(([cat, counts]) => (
                      <tr key={cat}>
                        <td style={{ fontWeight: 600 }}>{cat}</td>
                        <td style={{ color: '#4ade80' }}>{counts.LOW || 0}</td>
                        <td style={{ color: '#fbbf24' }}>{counts.MEDIUM || 0}</td>
                        <td style={{ color: '#f87171' }}>{counts.HIGH || 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
