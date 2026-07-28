import { useState, useEffect, useMemo } from 'react'
import { api } from '../api.js'
import { fmtDate, isExpiring, statusBadgeClass, riskBadgeClass } from '../helpers.js'
import CreateVendorModal from './modals/CreateVendorModal.jsx'

const EMPTY_FILTERS = {
  category: '', business_unit: '', region: '', insurance_provider: '',
  document_type: '', assigned_analyst_id: '', vendor_type: '',
}

export default function Vendors({ navigate, toast, user }) {
  // Feature 7 (RBAC): Auditor is read-only everywhere; the backend already
  // rejects these calls with 403, this just avoids showing a button that
  // would fail.
  const canEdit = user?.role !== 'AUDITOR'
  const [vendors, setVendors] = useState([])
  const [total, setTotal] = useState(0)
  const [search, setSearch] = useState('')
  const [filters, setFilters] = useState(EMPTY_FILTERS)
  const [showFilters, setShowFilters] = useState(false)
  const [options, setOptions] = useState({
    category: [], vendor_type: [], document_type: [],
    business_unit: [], region: [], insurance_provider: [], assigned_analyst: [],
  })
  const [showCreate, setShowCreate] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    api('GET', '/vendors/filters/options').then(o => o && setOptions(o)).catch(() => {})
  }, [])

  // Build the query string from the active advanced filters (server-side).
  // Free-text search stays a client-side filter over the loaded page, same
  // as before, so it narrows instantly without a round trip.
  function buildQuery() {
    const params = new URLSearchParams({ page: '1', page_size: '100' })
    Object.entries(filters).forEach(([k, v]) => { if (v) params.set(k, v) })
    return params.toString()
  }

  function loadVendors() {
    setLoading(true)
    api('GET', `/vendors?${buildQuery()}`)
      .then(res => { setVendors(res?.data || []); setTotal(res?.total ?? (res?.data || []).length) })
      .catch(() => { setVendors([]); setTotal(0) })
      .finally(() => setLoading(false))
  }

  // Re-fetch whenever an advanced filter changes.
  useEffect(() => { loadVendors() }, [filters])

  const activeFilterCount = Object.values(filters).filter(Boolean).length

  const filtered = search
    ? vendors.filter(v => v.name?.toLowerCase().includes(search.toLowerCase()) ||
        v.email?.toLowerCase().includes(search.toLowerCase()) ||
        v.city?.toLowerCase().includes(search.toLowerCase()))
    : vendors

  function setFilter(k, v) { setFilters(f => ({ ...f, [k]: v })) }
  function clearFilters() { setFilters(EMPTY_FILTERS) }

  const analystNameById = useMemo(() => {
    const m = {}
    ;(options.assigned_analyst || []).forEach(a => { m[a.id] = a.name })
    return m
  }, [options.assigned_analyst])

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Vendors</div>
          <div className="page-sub">{total} total vendor{total !== 1 ? 's' : ''}{activeFilterCount ? ` · ${activeFilterCount} filter${activeFilterCount!==1?'s':''} active` : ''}{search ? ` · ${filtered.length} match${filtered.length!==1?'es':''}` : ''}</div>
        </div>
        <div className="flex gap-2">
          <input className="form-input" style={{ width:220, padding:'7px 12px' }} placeholder="Search vendors…"
            value={search} onChange={e => setSearch(e.target.value)} />
          <button className={`btn btn-sm ${activeFilterCount ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setShowFilters(s => !s)}>
            <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"/></svg>
            Filters{activeFilterCount ? ` (${activeFilterCount})` : ''}
          </button>
          {canEdit && (
            <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
              Add Vendor
            </button>
          )}
        </div>
      </div>

      {showFilters && (
        <div className="card" style={{ marginBottom:16, padding:16 }}>
          <div style={{ display:'grid', gridTemplateColumns:'repeat(auto-fill, minmax(180px, 1fr))', gap:12 }}>
            <div className="form-group">
              <label className="form-label">Category</label>
              <select className="form-input" value={filters.category} onChange={e=>setFilter('category', e.target.value)}>
                <option value="">All categories</option>
                {(options.category||[]).map(c => <option key={c} value={c}>{c.charAt(0)+c.slice(1).toLowerCase()}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Business Unit</label>
              <select className="form-input" value={filters.business_unit} onChange={e=>setFilter('business_unit', e.target.value)}>
                <option value="">All business units</option>
                {(options.business_unit||[]).map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Region</label>
              <select className="form-input" value={filters.region} onChange={e=>setFilter('region', e.target.value)}>
                <option value="">All regions</option>
                {(options.region||[]).map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Insurance Provider</label>
              <select className="form-input" value={filters.insurance_provider} onChange={e=>setFilter('insurance_provider', e.target.value)}>
                <option value="">All providers</option>
                {(options.insurance_provider||[]).map(v => <option key={v} value={v}>{v}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Document Type</label>
              <select className="form-input" value={filters.document_type} onChange={e=>setFilter('document_type', e.target.value)}>
                <option value="">Any</option>
                {(options.document_type||[]).map(v => <option key={v} value={v}>{v.replace('_',' ')}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Assigned Analyst</label>
              <select className="form-input" value={filters.assigned_analyst_id} onChange={e=>setFilter('assigned_analyst_id', e.target.value)}>
                <option value="">Anyone</option>
                {(options.assigned_analyst||[]).map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
              </select>
            </div>
            <div className="form-group">
              <label className="form-label">Vendor Type</label>
              <select className="form-input" value={filters.vendor_type} onChange={e=>setFilter('vendor_type', e.target.value)}>
                <option value="">All types</option>
                {(options.vendor_type||[]).map(v => <option key={v} value={v}>{v.replace('_',' ')}</option>)}
              </select>
            </div>
          </div>
          {activeFilterCount > 0 && (
            <div style={{ marginTop:12, textAlign:'right' }}>
              <button className="btn btn-ghost btn-sm" onClick={clearFilters}>Clear all filters</button>
            </div>
          )}
        </div>
      )}

      <div className="card" style={{ padding:0, overflow:'hidden' }}>
        {loading ? (
          <div className="empty-state"><div className="spinner" style={{ width:24, height:24, borderWidth:3, margin:'24px auto' }} /></div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <div className="icon">🏢</div>
            <p style={{ color:'#555' }}>{search || activeFilterCount ? 'No vendors match your search/filters.' : 'No vendors yet.'}</p>
            {!search && !activeFilterCount && canEdit && <button className="btn btn-ghost btn-sm mt-4" onClick={() => setShowCreate(true)}>Add your first vendor</button>}
          </div>
        ) : (
          <table className="tbl">
            <thead><tr>
              <th>Vendor Name</th><th>Category</th><th>Business Unit / Region</th>
              <th>Risk Tier</th><th>Status</th><th>Analyst</th><th>GL Expiry</th><th></th>
            </tr></thead>
            <tbody>
              {filtered.map(v => (
                <tr key={v.id} onClick={() => navigate('vendor-detail', v.id)}>
                  <td>
                    <div style={{ fontWeight:600, color:'#e0e0e0' }}>{v.name}</div>
                    <div style={{ fontSize:11, color:'#444', marginTop:2 }}>{v.email || ''}</div>
                  </td>
                  <td style={{ color:'#666', fontSize:12 }}>{v.category ? (v.category.charAt(0)+v.category.slice(1).toLowerCase()) : '—'}</td>
                  <td style={{ color:'#666', fontSize:12 }}>{[v.business_unit, v.region].filter(Boolean).join(' · ') || '—'}</td>
                  <td><span className={`badge ${riskBadgeClass(v.risk_tier)}`}>{v.risk_tier || '—'}</span></td>
                  <td><span className={`badge ${statusBadgeClass(v.status)}`}>{v.status || '—'}</span></td>
                  <td style={{ color:'#666', fontSize:12 }}>{analystNameById[v.assigned_analyst_id] || '—'}</td>
                  <td style={{ fontSize:12, color: isExpiring(v.gl_expiry)?'#f87171':'#555' }}>{fmtDate(v.gl_expiry)}</td>
                  <td style={{ textAlign:'right' }}><span style={{ color:'#333', fontSize:18, padding:'0 8px' }}>›</span></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showCreate && (
        <CreateVendorModal
          onClose={() => setShowCreate(false)}
          onCreated={() => {
            setShowCreate(false)
            toast('Vendor created successfully!', 'success')
            loadVendors()
          }}
        />
      )}
    </div>
  )
}
