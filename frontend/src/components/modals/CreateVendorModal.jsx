import { useState } from 'react'
import { api } from '../../api.js'

// NOTE on fixes made here:
// - POSTed to '/vendors/' (trailing slash) while the route is registered as
//   '' under the /vendors prefix — FastAPI 307-redirects that, an extra
//   cross-origin round trip that's fragile with credentials/CORS. Fixed to
//   the exact registered path.
// - risk_tier/industry/website fields were collected but don't exist on the
//   VendorCreate schema at all, so they were silently discarded on every
//   submit (risk tier is actually assigned automatically once a document is
//   analyzed). Replaced with city/state/zip_code, which the schema and the
//   rest of the UI (VendorDetail) actually use.
// - Error handling read `ex.message`, but api.js throws a plain
//   {status, data} object (not an Error), so `.message` was always
//   undefined and every failure showed the same generic text. Now reads the
//   real backend error/validation message.
export default function CreateVendorModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    name: '', contact_name: '', email: '', phone: '',
    address: '', city: '', state: '', zip_code: '', notes: ''
  })
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  function set(k, v) { setForm(f => ({ ...f, [k]: v })) }

  async function submit(e) {
    e.preventDefault()
    if (!form.name.trim()) { setErr('Vendor name is required'); return }
    setLoading(true); setErr('')
    try {
      const vendor = await api('POST', '/vendors', form)
      onCreated(vendor)
    } catch (ex) {
      setErr(ex?.data?.error || (ex?.data?.details && ex.data.details[0]?.message) || 'Failed to create vendor')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={e => e.target===e.currentTarget && onClose()}>
      <div className="modal">
        <div className="modal-header">
          <div className="modal-title">Add New Vendor</div>
          <button className="modal-close" onClick={onClose}>✕</button>
        </div>
        <form onSubmit={submit}>
          <div className="modal-body">
            {err && <div className="alert alert-error" style={{ marginBottom:16 }}>{err}</div>}
            <div className="form-grid">
              <div className="form-group" style={{ gridColumn:'1/-1' }}>
                <label className="form-label">Company Name *</label>
                <input className="form-input" value={form.name} onChange={e=>set('name',e.target.value)} placeholder="Acme Corp" />
              </div>
              <div className="form-group">
                <label className="form-label">Contact Name</label>
                <input className="form-input" value={form.contact_name} onChange={e=>set('contact_name',e.target.value)} placeholder="John Smith" />
              </div>
              <div className="form-group">
                <label className="form-label">Email</label>
                <input className="form-input" type="email" value={form.email} onChange={e=>set('email',e.target.value)} placeholder="contact@acme.com" />
              </div>
              <div className="form-group">
                <label className="form-label">Phone</label>
                <input className="form-input" value={form.phone} onChange={e=>set('phone',e.target.value)} placeholder="+1 555 000 0000" />
              </div>
              <div className="form-group">
                <label className="form-label">City</label>
                <input className="form-input" value={form.city} onChange={e=>set('city',e.target.value)} placeholder="Austin" />
              </div>
              <div className="form-group">
                <label className="form-label">State</label>
                <input className="form-input" value={form.state} onChange={e=>set('state',e.target.value)} placeholder="TX" />
              </div>
              <div className="form-group" style={{ gridColumn:'1/-1' }}>
                <label className="form-label">Address</label>
                <input className="form-input" value={form.address} onChange={e=>set('address',e.target.value)} placeholder="123 Main St" />
              </div>
              <div className="form-group" style={{ gridColumn:'1/-1' }}>
                <label className="form-label">Notes</label>
                <textarea className="form-input" rows={3} value={form.notes} onChange={e=>set('notes',e.target.value)} placeholder="Any additional notes..." />
              </div>
            </div>
          </div>
          <div className="modal-footer">
            <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
            <button type="submit" className="btn btn-primary" disabled={loading}>{loading ? 'Creating…' : 'Create Vendor'}</button>
          </div>
        </form>
      </div>
    </div>
  )
}
