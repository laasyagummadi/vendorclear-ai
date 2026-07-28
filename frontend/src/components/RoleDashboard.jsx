import { useState, useEffect } from 'react'
import { api } from '../api.js'
import { fmtDate, statusBadgeClass, riskBadgeClass } from '../helpers.js'
import Dashboard from './Dashboard.jsx'

// Module 5 — Role Based Dashboards.
// Fetches /dashboard/me, which returns a payload shaped for the caller's role,
// and renders the matching homepage.
export default function RoleDashboard({ navigate, toast, user }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api('GET', '/dashboard/me')
      .then(setData)
      .catch(() => setData(null))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="empty-state"><p>Loading your dashboard…</p></div>
  if (!data) return <Dashboard navigate={navigate} toast={toast} />

  const roleLabel = {
    ADMIN: 'Administrator', ANALYST: 'Compliance Analyst',
    VENDOR: 'Vendor Portal', AUDITOR: 'Auditor (read-only)',
  }[data.role] || data.role

  // ── VENDOR: only their own record ───────────────────────────
  if (data.view === 'vendor') {
    const v = data.vendor
    const cfg = data.my_settings || {}
    const score = data.my_score || {}
    if (!v) return (
      <div>
        <div className="page-header"><div><div className="page-title">Vendor Portal</div></div></div>
        <div className="card"><div className="empty-state"><p>{data.message || 'No vendor record linked.'}</p></div></div>
      </div>
    )
    return (
      <div>
        <div className="page-header">
          <div>
            <div className="page-title">{v.name}</div>
            <div className="page-sub">{roleLabel} · Version {v.assigned_version}</div>
          </div>
        </div>

        <div className="stat-grid" style={{ marginBottom: 20 }}>
          <div className="stat-box">
            <div className="stat-label">Compliance Status</div>
            <div className="stat-val"><span className={`badge ${statusBadgeClass(v.status)}`}>{v.status || '—'}</span></div>
          </div>
          <div className="stat-box">
            <div className="stat-label">Risk Tier</div>
            <div className="stat-val"><span className={`badge ${riskBadgeClass(v.risk_tier)}`}>{v.risk_tier || '—'}</span></div>
          </div>
          <div className="stat-box">
            <div className="stat-label">Compliance Score</div>
            <div className="stat-val">{score.total_score != null ? `${score.total_score}/100` : '—'}</div>
          </div>
          <div className="stat-box">
            <div className="stat-label">GL Expiry</div>
            <div className="stat-val" style={{ fontSize: 18 }}>{fmtDate(v.gl_expiry) || '—'}</div>
          </div>
        </div>

        <div className="card">
          <div style={{ fontWeight: 700, marginBottom: 4 }}>My Compliance Requirements</div>
          <div style={{ fontSize: 12, color: '#605e5c', marginBottom: 14 }}>
            These are the settings that apply to your account (Version {v.assigned_version}). Read-only.
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <Row label="Compliance Compensation" value={cfg.compliance_compensation_inr != null ? '₹' + Number(cfg.compliance_compensation_inr).toLocaleString('en-IN') : '—'} />
            <Row label="Required GL Limit" value={cfg.required_gl_limit_usd != null ? '$' + Number(cfg.required_gl_limit_usd).toLocaleString() : '—'} />
            <Row label="Required Workers Comp" value={cfg.required_wc_limit_usd != null ? '$' + Number(cfg.required_wc_limit_usd).toLocaleString() : '—'} />
            <Row label="Min Diversity Ownership" value={cfg.min_ownership_percent != null ? cfg.min_ownership_percent + '%' : '—'} />
          </div>
        </div>

        <div style={{ marginTop: 16 }}>
          <button className="btn btn-primary btn-sm" onClick={() => navigate('upload')}>Upload a Document</button>
        </div>
      </div>
    )
  }

  // ── AUDITOR: read-only banner + org overview ────────────────
  // ── ANALYST / ADMIN: operational overview ───────────────────
  const s = data.summary || {}
  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Dashboard</div>
          <div className="page-sub">{roleLabel}</div>
        </div>
      </div>

      {data.read_only && (
        <div className="card" style={{ marginBottom: 16, borderLeft: '3px solid #fbbf24' }}>
          <div style={{ fontSize: 13 }}>
            <strong>Read-only access.</strong> You can review all compliance data but cannot make changes.
          </div>
        </div>
      )}

      {data.view === 'admin' && data.config && (
        <div className="card" style={{ marginBottom: 16 }}>
          <div style={{ fontWeight: 700, marginBottom: 8 }}>Version Configuration</div>
          <div style={{ display: 'flex', gap: 24, fontSize: 13 }}>
            <div>
              <span style={{ color: '#605e5c' }}>Version 1 compensation: </span>
              <strong>₹{Number(data.config.version_1?.compliance_compensation_inr || 0).toLocaleString('en-IN')}</strong>
            </div>
            <div>
              <span style={{ color: '#605e5c' }}>Version 2 compensation: </span>
              <strong>₹{Number(data.config.version_2?.compliance_compensation_inr || 0).toLocaleString('en-IN')}</strong>
            </div>
          </div>
          <button className="btn btn-ghost btn-sm" style={{ marginTop: 12 }} onClick={() => navigate('admin-settings')}>
            Manage Settings
          </button>
        </div>
      )}

      <div className="stat-grid" style={{ marginBottom: 20 }}>
        <div className="stat-box">
          <div className="stat-label">Total Vendors</div>
          <div className="stat-val">{s.vendors?.total ?? '—'}</div>
          <div className="stat-sub">{s.vendors?.active ?? 0} active</div>
        </div>
        <div className="stat-box">
          <div className="stat-label">Compliance Rate</div>
          <div className="stat-val">{s.vendors?.compliance_rate_pct != null ? `${Math.round(s.vendors.compliance_rate_pct)}%` : '—'}</div>
          <div className="stat-sub">{s.vendors?.compliant ?? 0} compliant</div>
        </div>
        <div className="stat-box">
          <div className="stat-label">Documents</div>
          <div className="stat-val">{s.documents?.total ?? '—'}</div>
          <div className="stat-sub">{s.documents?.processed ?? 0} processed</div>
        </div>
        <div className="stat-box">
          <div className="stat-label">Open Alerts</div>
          <div className="stat-val">{s.alerts?.total ?? '—'}</div>
          <div className="stat-sub">{s.alerts?.expiry ?? 0} expiry · {s.alerts?.compliance ?? 0} compliance</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('vendors')}>View Vendors</button>
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('report')}>Compliance Report</button>
        <button className="btn btn-ghost btn-sm" onClick={() => navigate('alerts')}>Alerts ({s.alerts?.total ?? 0})</button>
      </div>
    </div>
  )
}

function Row({ label, value }) {
  return (
    <div>
      <div style={{ fontSize: 11, color: '#605e5c', textTransform: 'uppercase', letterSpacing: 0.4 }}>{label}</div>
      <div style={{ fontSize: 15, fontWeight: 600, marginTop: 2 }}>{value}</div>
    </div>
  )
}
