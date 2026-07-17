import { useState, useEffect } from 'react'
import { api } from '../api.js'
import { fmtDate, isExpiring, statusBadgeClass, riskBadgeClass } from '../helpers.js'
import CreateVendorModal from './modals/CreateVendorModal.jsx'

export default function Vendors({ navigate, toast }) {
  const [vendors, setVendors] = useState([])
  const [filter, setFilter] = useState('')
  const [showCreate, setShowCreate] = useState(false)
  const [loading, setLoading] = useState(true)

  // NOTE: previously this used ?skip=0&limit=200 (not a param the backend
  // recognizes — it uses page/page_size) and did setVendors(d || []) where
  // `d` was the *entire* paginated envelope { success, data, total, page,
  // page_size, total_pages }, not a bare array. Calling .filter()/.map() on
  // that object crashed this page every single time it was opened.
  function loadVendors() {
    setLoading(true)
    api('GET', '/vendors?page=1&page_size=100')
      .then(res => setVendors(res?.data || []))
      .catch(() => setVendors([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { loadVendors() }, [])

  const filtered = filter
    ? vendors.filter(v => v.name?.toLowerCase().includes(filter.toLowerCase()) ||
        v.email?.toLowerCase().includes(filter.toLowerCase()) ||
        v.city?.toLowerCase().includes(filter.toLowerCase()))
    : vendors

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Vendors</div>
          <div className="page-sub">{vendors.length} total vendor{vendors.length !== 1 ? 's' : ''}</div>
        </div>
        <div className="flex gap-2">
          <input className="form-input" style={{ width:220, padding:'7px 12px' }} placeholder="Search vendors…"
            value={filter} onChange={e => setFilter(e.target.value)} />
          <button className="btn btn-primary" onClick={() => setShowCreate(true)}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/></svg>
            Add Vendor
          </button>
        </div>
      </div>

      <div className="card" style={{ padding:0, overflow:'hidden' }}>
        {loading ? (
          <div className="empty-state"><div className="spinner" style={{ width:24, height:24, borderWidth:3, margin:'24px auto' }} /></div>
        ) : filtered.length === 0 ? (
          <div className="empty-state">
            <div className="icon">🏢</div>
            <p style={{ color:'#555' }}>{filter ? 'No vendors match your search.' : 'No vendors yet.'}</p>
            {!filter && <button className="btn btn-ghost btn-sm mt-4" onClick={() => setShowCreate(true)}>Add your first vendor</button>}
          </div>
        ) : (
          <table className="tbl">
            <thead><tr>
              <th>Vendor Name</th><th>Contact</th><th>Location</th>
              <th>Risk Tier</th><th>Status</th><th>GL Expiry</th><th></th>
            </tr></thead>
            <tbody>
              {filtered.map(v => (
                <tr key={v.id} onClick={() => navigate('vendor-detail', v.id)}>
                  <td>
                    <div style={{ fontWeight:600, color:'#e0e0e0' }}>{v.name}</div>
                    <div style={{ fontSize:11, color:'#444', marginTop:2 }}>{v.email || ''}</div>
                  </td>
                  <td style={{ color:'#666' }}>{v.contact_name || '—'}</td>
                  <td style={{ color:'#666' }}>{[v.city,v.state].filter(Boolean).join(', ') || '—'}</td>
                  <td><span className={`badge ${riskBadgeClass(v.risk_tier)}`}>{v.risk_tier || '—'}</span></td>
                  <td><span className={`badge ${statusBadgeClass(v.status)}`}>{v.status || '—'}</span></td>
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
