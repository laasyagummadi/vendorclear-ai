import { useState } from 'react'
import { api } from '../../api.js'

export default function CreateVendorModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    name: '', contact_name: '', email: '', phone: '',
    address: '', risk_tier: 'medium', industry: '', website: '',
    notes: ''
  })
  const [loading, setLoading] = useState(false)
  const [err, setErr] = useState('')

  function set(k, v) { setForm(f => ({ ...f, [k]: v })) }

  async function submit(e) {
    e.preventDefault()
    if (!form.name.trim()) { setErr('Vendor name is required'); return }
    setLoading(true); setErr('')
    try {
      const vendor = await api('POST', '/vendors/', form)
      onCreated(vendor)
    } catch (ex) {
      setErr(ex.message || 'Failed to create vendor')
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
                <label className="form-label">Risk Tier</label>
                <select className="form-input" value={form.risk_tier} onChange={e=>set('risk_tier',e.target.value)}>
                  <option value="low">Low</option>
                  <option value="medium">Medium</option>
                  <option value="high">High</option>
                  <option value="critical">Critical</option>
                </select>
              </div>
              <div className="form-group">
                <label className="form-label">Industry</label>
                <input className="form-input" value={form.industry} onChange={e=>set('industry',e.target.value)} placeholder="Technology" />
              </div>
              <div className="form-group">
                <label className="form-label">Website</label>
                <input className="form-input" value={form.website} onChange={e=>set('website',e.target.value)} placeholder="https://acme.com" />
              </div>
              <div className="form-group" style={{ gridColumn:'1/-1' }}>
                <label className="form-label">Address</label>
                <input className="form-input" value={form.address} onChange={e=>set('address',e.target.value)} placeholder="123 Main St, City, State" />
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
