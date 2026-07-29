import { useState, useEffect } from 'react'
import { api } from '../../api.js'

// NOTE on fixes made here:
// - Was called with `id` + `onSaved` props from VendorDetail but destructured
//   {vendor, onClose, onUpdated} — `vendor` was always undefined, so
//   `vendor.name` crashed the moment this modal opened. Caller now passes
//   the actual vendor object (see VendorDetail.jsx).
// - Used HTTP PUT, but the backend route is a PATCH (`@router.patch`) —
//   a PUT request would 405. Switched to PATCH via api.js.
// - Status/Risk Tier dropdowns offered values ("active"/"low"/"critical"...)
//   that don't match the backend's actual enums (VendorStatus:
//   COMPLIANT/NEEDS_REVIEW/NON_COMPLIANT, RiskTier: LOW/MEDIUM/HIGH) —
//   sending them would fail 422 validation. Fixed to the real enum values.
// - Industry/Website inputs collected data with no backing schema field
//   (VendorUpdate has no industry/website column) — always silently
//   discarded. Removed and replaced with City/State/Zip, which the schema
//   actually supports and VendorDetail already displays.
export default function EditVendorModal({ vendor, onClose, onUpdated }) {
  const [form, setForm] = useState({
    name: vendor?.name || '',
    contact_name: vendor?.contact_name || '',
    email: vendor?.email || '',
    phone: vendor?.phone || '',
    address: vendor?.address || '',
    city: vendor?.city || '',
    state: vendor?.state || '',
    zip_code: vendor?.zip_code || '',
    status: vendor?.status || 'NEEDS_REVIEW',
    category: vendor?.category || 'OTHER',
    vendor_type: vendor?.vendor_type || '',
    business_unit: vendor?.business_unit || '',
    region: vendor?.region || '',
    insurance_provider: vendor?.insurance_provider || '',
    assigned_analyst_id: vendor?.assigned_analyst_id || '',
    gl_expiry: vendor?.gl_expiry || '',
    wc_expiry: vendor?.wc_expiry || '',
    notes: vendor?.notes || '',
  })
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')
  const [options, setOptions] = useState({ category: [], vendor_type: [], assigned_analyst: [] })

  useEffect(() => {
    api('GET', '/vendors/filters/options').then(o => o && setOptions(o)).catch(() => {})
  }, [])

  function set(k, v) { setForm(f => ({ ...f, [k]: v })) }

  async function submit(e) {
    e.preventDefault()
    if (!form.name.trim()) { setErr('Vendor name is required'); return }
    setLoading(true); setErr('')
    try {
      const payload = { ...form }
      if (!payload.gl_expiry) delete payload.gl_expiry
      if (!payload.wc_expiry) delete payload.wc_expiry
      Object.keys(payload).forEach(k => { if (payload[k] === '') delete payload[k] })
      const updated = await api('PATCH', `/vendors/${vendor.id}`, payload)
      onUpdated(updated)
    } catch (ex) {
      setErr(ex?.data?.error || (ex?.data?.details && ex.data.details[0]?.message) || 'Failed to update vendor')
    } finally {
      setLoading(false)
    }
  }

  if (!vendor) return null

  return (
    <div className="modal-overlay" onClick={e => e.target===e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <div className="modal-title">Edit Vendor</div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={submit}>
          <div className="modal-body">
            {err && <div className="alert alert-error" style={{ marginBottom:16 }}>{err}</div>}
            <div className="form-grid">
              <div className="form-group" style={{ gridColumn:'1/-1' }}>
                <label className="form-label">Company Name *</label>
                <input className="form-input" value={form.name} onChange={e=>set('name',e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Contact Name</label>
                <input className="form-input" value={form.contact_name} onChange={e=>set('contact_name',e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Email</label>
                <input className="form-input" type="email" value={form.email} onChange={e=>set('email',e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Phone</label>
                <input className="form-input" value={form.phone} onChange={e=>set('phone',e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Status</label>
                <select className="form-input" value={form.status} onChange={e=>set('status',e.target.value)}>
                  <option value="COMPLIANT">Compliant</option>
                  <option value="NEEDS_REVIEW">Needs Review</option>
                  <option value="NON_COMPLIANT">Non-Compliant</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Category</label>
                <select className="form-input" value={form.category} onChange={e=>set('category',e.target.value)}>
                  {(options.category.length?options.category:['CONSTRUCTION','SOFTWARE','ELECTRICAL','TRANSPORTATION','CIVIL','OTHER']).map(c => <option key={c} value={c}>{c.charAt(0)+c.slice(1).toLowerCase()}</option>)}
                </select>
                <div style={{ fontSize:11, color:'#555', marginTop:4 }}>Risk tier is now calculated automatically from the score — no manual override.</div>
              </div>
              <div className="form-group">
                <label className="form-label">Vendor Type</label>
                <select className="form-input" value={form.vendor_type} onChange={e=>set('vendor_type',e.target.value)}>
                  <option value="">Unset</option>
                  {(options.vendor_type.length?options.vendor_type:['SUBCONTRACTOR','SUPPLIER','CONSULTANT','SERVICE_PROVIDER','OTHER']).map(t => <option key={t} value={t}>{t.replace('_',' ')}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Business Unit</label>
                <input className="form-input" value={form.business_unit} onChange={e=>set('business_unit',e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Region</label>
                <input className="form-input" value={form.region} onChange={e=>set('region',e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Insurance Provider</label>
                <input className="form-input" value={form.insurance_provider} onChange={e=>set('insurance_provider',e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Assigned Analyst</label>
                <select className="form-input" value={form.assigned_analyst_id} onChange={e=>set('assigned_analyst_id',e.target.value)}>
                  <option value="">Unassigned</option>
                  {options.assigned_analyst.map(a => <option key={a.id} value={a.id}>{a.name}</option>)}
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">City</label>
                <input className="form-input" value={form.city} onChange={e=>set('city',e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">State</label>
                <input className="form-input" value={form.state} onChange={e=>set('state',e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">GL Expiry (YYYY-MM-DD)</label>
                <input className="form-input" placeholder="2026-12-31" value={form.gl_expiry} onChange={e=>set('gl_expiry',e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">WC Expiry (YYYY-MM-DD)</label>
                <input className="form-input" placeholder="2026-12-31" value={form.wc_expiry} onChange={e=>set('wc_expiry',e.target.value)} />
              </div>
              <div className="form-group" style={{ gridColumn:'1/-1' }}>
                <label className="form-label">Address</label>
                <input className="form-input" value={form.address} onChange={e=>set('address',e.target.value)} />
              </div>
              <div className="form-group" style={{ gridColumn:'1/-1' }}>
                <label className="form-label">Notes</label>
                <textarea className="form-input" rows={3} value={form.notes} onChange={e=>set('notes',e.target.value)} />
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? 'Saving…' : 'Save Changes'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}
