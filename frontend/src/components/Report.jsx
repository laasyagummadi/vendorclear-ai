import { useState, useEffect, useMemo } from 'react'
import { api, apiDownload } from '../api.js'
import { fmtDate, isExpiring, statusBadgeClass, riskBadgeClass } from '../helpers.js'

const EMPTY_FILTERS = {
  status: '', risk_tier: '', category: '', vendor_type: '', business_unit: '', region: '',
  insurance_provider: '', assigned_analyst: '', document_type: '', expiry_before: '', search: '',
}
const GROUP_OPTIONS = [
  { value: '', label: 'No grouping' },
  { value: 'category', label: 'Category' },
  { value: 'status', label: 'Status' },
  { value: 'risk_tier', label: 'Risk Tier' },
]
const SORT_COLUMNS = {
  name: v => v.name?.toLowerCase() || '',
  status: v => v.status || '',
  risk_tier: v => ({ HIGH: 3, MEDIUM: 2, LOW: 1 }[v.risk_tier] || 0),
  total_score: v => v.total_score ?? -1,
  document_count: v => v.document_count ?? 0,
  gl_expiry: v => v.gl_expiry || '',
}

export default function Report({ navigate, toast }) {
  const [report, setReport] = useState(null)
  const [loading, setLoading] = useState(true)
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [showFilters, setShowFilters] = useState(false)
  const [groupBy, setGroupBy] = useState('')
  const [sortCol, setSortCol] = useState(null)
  const [sortDir, setSortDir] = useState('desc')
  const [exporting, setExporting] = useState(false)
  const [exportError, setExportError] = useState('')

  function buildQuery() {
    const params = new URLSearchParams()
    Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v) })
    return params.toString()
  }

  function load() {
    setLoading(true)
    const qs = buildQuery()
    api('GET', `/dashboard/compliance-report${qs ? `?${qs}` : ''}`)
      .then(setReport).catch(() => setReport(null)).finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [filters])

  const activeFilterCount = Object.values(filters).filter(Boolean).length
  function setFilter(k, v) { setFilters(f => ({ ...f, [k]: v })) }
  function clearFilters() { setFilters(EMPTY_FILTERS) }

  function toggleSort(col) {
    if (sortCol === col) setSortDir(d => d === 'desc' ? 'asc' : 'desc')
    else { setSortCol(col); setSortDir('desc') }
  }

  const vendors = report?.vendors || []
  const sum = report?.summary || {}

  const sorted = useMemo(() => {
    if (!sortCol) return vendors
    const key = SORT_COLUMNS[sortCol]
    const copy = [...vendors].sort((a, b) => {
      const av = key(a), bv = key(b)
      if (av < bv) return -1
      if (av > bv) return 1
      return 0
    })
    if (sortDir === 'desc') copy.reverse()
    return copy
  }, [vendors, sortCol, sortDir])

  const grouped = useMemo(() => {
    if (!groupBy) return [{ key: null, rows: sorted }]
    const groups = new Map()
    for (const v of sorted) {
      const key = v[groupBy] || 'Unassigned'
      if (!groups.has(key)) groups.set(key, [])
      groups.get(key).push(v)
    }
    return [...groups.entries()].map(([key, rows]) => ({ key, rows }))
  }, [sorted, groupBy])

  async function exportCSV() {
    setExporting(true)
    setExportError('')
    try {
      const qs = buildQuery()
      const blob = await apiDownload(`/dashboard/compliance-report/export${qs ? `?${qs}` : ''}`)
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `compliance-report-${report?.report_date || 'export'}.csv`
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)
      const count = vendors.length
      if (toast) toast(`Exported ${count} vendor${count !== 1 ? 's' : ''} to CSV — check your Downloads folder.`, 'success')
    } catch (e) {
      const msg = e?.message || 'Export failed — please try again.'
      setExportError(msg)
      if (toast) toast(msg, 'error')
    } finally {
      setExporting(false)
    }
  }

  function sortArrow(col) {
    if (sortCol !== col) return ''
    return sortDir === 'desc' ? ' ↓' : ' ↑'
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Compliance Report</div>
          <div className="page-sub">Generated {fmtDate(report?.report_date) || 'now'} · {vendors.length} vendors{activeFilterCount ? ` · ${activeFilterCount} filter${activeFilterCount!==1?'s':''} active` : ''}</div>
        </div>
        <div className="flex gap-2">
          <select className="form-input" style={{ padding:'7px 10px' }} value={groupBy} onChange={e => setGroupBy(e.target.value)}>
            {GROUP_OPTIONS.map(g => <option key={g.value} value={g.value}>{g.value ? `Group by ${g.label}` : g.label}</option>)}
          </select>
          <button className={`btn btn-sm ${activeFilterCount ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setShowFilters(s => !s)}>Filters{activeFilterCount ? ` (${activeFilterCount})` : ''}</button>
          <button className="btn btn-ghost btn-sm" onClick={exportCSV} disabled={exporting || vendors.length === 0}>{exporting ? 'Exporting…' : '⭳ Export CSV'}</button>
          <button className="btn btn-ghost btn-sm" onClick={load}>↺ Refresh</button>
        </div>
      </div>

      {showFilters && (
        <div className="card" style={{ marginBottom:20, padding:16 }}>
          <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(180px, 1fr))', gap:12 }}>
            <div className="form-group">
              <label className="form-label">Search</label>
              <input className="form-input" placeholder="Vendor name…" value={filters.search} onChange={e=>setFilter('search', e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Status</label>
              <select className="form-input" value={filters.status} onChange={e=>setFilter('status', e.target.value)}>
                <option value="">All statuses</option>
                <option value="COMPLIANT">Compliant</option>
                <option value="NEEDS_REVIEW">Needs Review</option>
                <option value="NON_COMPLIANT">Non-Compliant</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Risk Tier</label>
              <select className="form-input" value={filters.risk_tier} onChange={e=>setFilter('risk_tier', e.target.value)}>
                <option value="">All risk tiers</option>
                <option value="LOW">Low</option>
                <option value="MEDIUM">Medium</option>
                <option value="HIGH">High</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Category</label>
              <select className="form-input" value={filters.category} onChange={e=>setFilter('category', e.target.value)}>
                <option value="">All categories</option>
                <option value="CONSTRUCTION">Construction</option>
                <option value="SOFTWARE">Software</option>
                <option value="ELECTRICAL">Electrical</option>
                <option value="OTHER">Other</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Vendor Type</label>
              <select className="form-input" value={filters.vendor_type} onChange={e=>setFilter('vendor_type', e.target.value)}>
                <option value="">All vendor types</option>
                <option value="SUBCONTRACTOR">Subcontractor</option>
                <option value="SUPPLIER">Supplier</option>
                <option value="CONSULTANT">Consultant</option>
                <option value="SERVICE_PROVIDER">Service Provider</option>
                <option value="OTHER">Other</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Business Unit</label>
              <input className="form-input" placeholder="Contains…" value={filters.business_unit} onChange={e=>setFilter('business_unit', e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Region</label>
              <input className="form-input" placeholder="Contains…" value={filters.region} onChange={e=>setFilter('region', e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Insurance Provider</label>
              <input className="form-input" placeholder="Contains…" value={filters.insurance_provider} onChange={e=>setFilter('insurance_provider', e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Assigned Analyst</label>
              <input className="form-input" placeholder="Analyst name…" value={filters.assigned_analyst} onChange={e=>setFilter('assigned_analyst', e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Document Type</label>
              <select className="form-input" value={filters.document_type} onChange={e=>setFilter('document_type', e.target.value)}>
                <option value="">All document types</option>
                <option value="COI">Certificate of Insurance</option>
                <option value="DIVERSITY_CERT">Diversity Certificate</option>
                <option value="UNKNOWN">Unknown</option>
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Expiry On/Before</label>
              <input type="date" className="form-input" value={filters.expiry_before} onChange={e=>setFilter('expiry_before', e.target.value)} />
            </div>
          </div>
          {activeFilterCount > 0 && (
            <div style={{ marginTop:12, textAlign:'right' }}>
              <button className="btn btn-ghost btn-sm" onClick={clearFilters}>Clear all filters</button>
            </div>
          )}
        </div>
      )}

      {exportError && (
        <div data-testid="export-error" className="card" style={{ marginBottom:16, padding:'10px 14px', borderColor:'#f87171', color:'#f87171', fontSize:13 }}>
          ⚠ {exportError}
        </div>
      )}

      <div className="stat-grid" style={{ marginBottom:20 }}>
        <div className="stat-box"><div className="stat-label">Total Vendors</div><div className="stat-val">{sum.total_vendors??'—'}</div></div>
        <div className="stat-box"><div className="stat-label">Avg Score</div><div className="stat-val">{sum.avg_score!=null?sum.avg_score.toFixed(0):'—'}</div></div>
        <div className="stat-box"><div className="stat-label">Compliant</div><div className="stat-val" style={{ color:'#4ade80' }}>{sum.compliant??'—'}</div></div>
        <div className="stat-box"><div className="stat-label">Non-Compliant</div><div className="stat-val" style={{ color:'#f87171' }}>{sum.non_compliant??'—'}</div></div>
      </div>

      {loading ? (
        <div className="card" style={{ padding:0 }}><div className="empty-state"><div className="spinner" style={{ width:24, height:24, borderWidth:3, margin:'24px auto' }} /></div></div>
      ) : vendors.length === 0 ? (
        <div className="card" style={{ padding:0 }}><div className="empty-state"><p>No vendor data available.</p></div></div>
      ) : (
        grouped.map(group => (
          <div key={group.key ?? 'all'} style={{ marginBottom: groupBy ? 16 : 0 }}>
            {group.key !== null && (
              <div style={{ fontSize:12, fontWeight:600, color:'#888', textTransform:'uppercase', letterSpacing:'.06em', margin:'0 0 8px 4px' }}>
                {group.key} <span style={{ color:'#444', fontWeight:400 }}>({group.rows.length})</span>
              </div>
            )}
            <div className="card" style={{ padding:0, overflow:'hidden' }}>
              <table className="tbl">
                <thead><tr>
                  <th>#</th>
                  <th style={{ cursor:'pointer' }} onClick={() => toggleSort('name')}>Vendor{sortArrow('name')}</th>
                  <th style={{ cursor:'pointer' }} onClick={() => toggleSort('status')}>Status{sortArrow('status')}</th>
                  <th style={{ cursor:'pointer' }} onClick={() => toggleSort('risk_tier')}>Risk{sortArrow('risk_tier')}</th>
                  <th style={{ cursor:'pointer' }} onClick={() => toggleSort('total_score')}>Score{sortArrow('total_score')}</th>
                  <th>Grade</th>
                  <th>Analyst</th>
                  <th style={{ cursor:'pointer' }} onClick={() => toggleSort('document_count')}>Documents{sortArrow('document_count')}</th>
                  <th style={{ cursor:'pointer' }} onClick={() => toggleSort('gl_expiry')}>GL Expiry{sortArrow('gl_expiry')}</th>
                </tr></thead>
                <tbody>
                  {group.rows.map((v, i) => {
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
                        <td style={{ color:'#555', fontSize:12 }}>{v.assigned_analyst || '—'}</td>
                        <td style={{ color:'#555', fontSize:12 }}>{v.document_count??0} doc{(v.document_count||0)!==1?'s':''}</td>
                        <td style={{ fontSize:12, color:isExpiring(v.gl_expiry)?'#f87171':'#555' }}>{fmtDate(v.gl_expiry)||'—'}</td>
                      </tr>
                    )
                  })}
                </tbody>
              </table>
            </div>
          </div>
        ))
      )}
    </div>
  )
}
