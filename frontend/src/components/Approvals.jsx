import { useState, useEffect } from 'react'
import { api } from '../api.js'

// Module 9 — Approval Workflow UI.
// Admin creates a policy (e.g. Construction: $5M GL + Workers Comp + Umbrella),
// vendors/analysts submit against it, admin approves or rejects.
export default function Approvals({ toast, user }) {
  const [tab, setTab] = useState('submissions')
  const [policies, setPolicies] = useState([])
  const [submissions, setSubmissions] = useState([])
  const [vendors, setVendors] = useState([])
  const [loading, setLoading] = useState(true)
  const [showNew, setShowNew] = useState(false)
  const [expanded, setExpanded] = useState(null)
  const [notes, setNotes] = useState({})

  const isAdmin = user?.role === 'ADMIN' || user?.is_admin
  const canSubmit = isAdmin || user?.role === 'ANALYST' || user?.role === 'VENDOR'

  function load() {
    setLoading(true)
    Promise.all([
      api('GET', '/policies').catch(() => []),
      api('GET', '/policies/submissions').catch(() => []),
      api('GET', '/vendors?page=1&page_size=100').catch(() => ({ data: [] })),
    ]).then(([p, s, v]) => {
      setPolicies(Array.isArray(p) ? p : [])
      setSubmissions(Array.isArray(s) ? s : [])
      setVendors(v?.data || [])
    }).finally(() => setLoading(false))
  }
  useEffect(load, [])

  async function decide(id, action) {
    try {
      await api('POST', `/policies/submissions/${id}/${action}`, { notes: notes[id] || '' })
      toast?.(`Submission ${action === 'approve' ? 'approved and activated' : 'rejected'}.`, 'success')
      load()
    } catch (e) {
      toast?.(e?.data?.detail || `Could not ${action}`, 'error')
    }
  }

  const statusClass = s => ({
    PENDING: 'badge-yellow', ACTIVE: 'badge-green', APPROVED: 'badge-green',
    REJECTED: 'badge-red', EXPIRED: 'badge-gray', DRAFT: 'badge-gray',
  }[s] || 'badge-gray')

  const vendorName = id => vendors.find(v => v.id === id)?.name || id?.slice(0, 8)
  const policyName = id => policies.find(p => p.id === id)?.name || '—'

  if (loading) return <div className="empty-state"><p>Loading approvals…</p></div>

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Approvals</div>
          <div className="page-sub">Compliance policies and vendor submissions</div>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          {canSubmit && <button className="btn btn-ghost btn-sm" onClick={() => setTab('submit')}>New Submission</button>}
          {isAdmin && <button className="btn btn-primary btn-sm" onClick={() => setShowNew(true)}>+ New Policy</button>}
        </div>
      </div>

      <div style={{ display: 'flex', gap: 8, marginBottom: 16 }}>
        {['submissions', 'policies'].map(t => (
          <button key={t} className={`btn btn-sm ${tab === t ? 'btn-primary' : 'btn-ghost'}`}
                  onClick={() => setTab(t)}>
            {t === 'submissions' ? `Submissions (${submissions.length})` : `Policies (${policies.length})`}
          </button>
        ))}
      </div>

      {tab === 'submit' && <SubmitForm policies={policies} vendors={vendors} user={user}
                                       toast={toast} onDone={() => { setTab('submissions'); load() }} />}

      {tab === 'submissions' && (
        submissions.length === 0
          ? <div className="card"><div className="empty-state"><p>No submissions yet.</p></div></div>
          : <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
              <table className="tbl">
                <thead><tr><th>Vendor</th><th>Policy</th><th>Status</th><th>Meets Requirements</th><th>Submitted</th><th></th></tr></thead>
                <tbody>
                  {submissions.map(s => (
                    <>
                      <tr key={s.id} onClick={() => setExpanded(expanded === s.id ? null : s.id)}>
                        <td style={{ fontWeight: 600 }}>{vendorName(s.vendor_id)}</td>
                        <td>{policyName(s.policy_id)}</td>
                        <td><span className={`badge ${statusClass(s.status)}`}>{s.status}</span></td>
                        <td>{s.meets_requirements
                              ? <span className="badge badge-green">All met</span>
                              : <span className="badge badge-red">Gaps found</span>}</td>
                        <td style={{ fontSize: 12 }}>{(s.submitted_at || '').slice(0, 10) || '—'}</td>
                        <td style={{ textAlign: 'right', fontSize: 11 }}>{expanded === s.id ? '▲' : '▼'}</td>
                      </tr>
                      {expanded === s.id && (
                        <tr key={s.id + '-x'}>
                          <td colSpan={6} style={{ background: '#faf9f8' }}>
                            <div style={{ padding: '4px 0 10px' }}>
                              <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 8 }}>Requirement check</div>
                              {Object.entries(s.requirement_results || {}).map(([k, r]) => (
                                <div key={k} style={{ display: 'flex', gap: 10, alignItems: 'center', marginBottom: 4, fontSize: 12 }}>
                                  <span className={`badge ${r.passed ? 'badge-green' : 'badge-red'}`}>
                                    {r.passed ? 'PASS' : 'FAIL'}
                                  </span>
                                  <span style={{ fontWeight: 600, minWidth: 150 }}>{k.replace(/_/g, ' ')}</span>
                                  <span style={{ color: '#605e5c' }}>
                                    required: {String(r.required)} · found: {String(r.found)}
                                  </span>
                                </div>
                              ))}
                              {s.review_notes && (
                                <div style={{ marginTop: 10, fontSize: 12 }}>
                                  <strong>Review notes:</strong> {s.review_notes}
                                </div>
                              )}
                              {isAdmin && s.status === 'PENDING' && (
                                <div style={{ marginTop: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
                                  <input className="form-input" style={{ maxWidth: 320 }}
                                         placeholder="Decision notes (optional)"
                                         value={notes[s.id] || ''}
                                         onClick={e => e.stopPropagation()}
                                         onChange={e => setNotes(n => ({ ...n, [s.id]: e.target.value }))} />
                                  <button className="btn btn-primary btn-sm"
                                          onClick={e => { e.stopPropagation(); decide(s.id, 'approve') }}>Approve</button>
                                  <button className="btn btn-danger btn-sm"
                                          onClick={e => { e.stopPropagation(); decide(s.id, 'reject') }}>Reject</button>
                                </div>
                              )}
                            </div>
                          </td>
                        </tr>
                      )}
                    </>
                  ))}
                </tbody>
              </table>
            </div>
      )}

      {tab === 'policies' && (
        policies.length === 0
          ? <div className="card"><div className="empty-state"><p>No policies defined yet.</p></div></div>
          : <div className="card" style={{ padding: 0, overflow: 'hidden' }}>
              <table className="tbl">
                <thead><tr><th>Policy</th><th>Category</th><th>Version</th><th>Requirements</th></tr></thead>
                <tbody>
                  {policies.map(p => (
                    <tr key={p.id}>
                      <td style={{ fontWeight: 600 }}>{p.name}
                        {p.description && <div style={{ fontSize: 11, color: '#605e5c' }}>{p.description}</div>}
                      </td>
                      <td>{p.category || '—'}</td>
                      <td>Version {p.version}</td>
                      <td style={{ fontSize: 12 }}>
                        {Object.entries(p.requirements || {}).map(([k, v]) => (
                          <div key={k}>{k.replace(/_/g, ' ')}: <strong>{String(v)}</strong></div>
                        ))}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
      )}

      {showNew && <NewPolicyModal onClose={() => setShowNew(false)}
                                  onCreated={() => { setShowNew(false); load() }} toast={toast} />}
    </div>
  )
}

function SubmitForm({ policies, vendors, user, toast, onDone }) {
  const [policyId, setPolicyId] = useState('')
  const [vendorId, setVendorId] = useState(user?.vendor_id || '')
  const [busy, setBusy] = useState(false)

  async function submit() {
    if (!policyId || !vendorId) return toast?.('Pick a policy and a vendor.', 'error')
    setBusy(true)
    try {
      await api('POST', '/policies/submissions', { policy_id: policyId, vendor_id: vendorId })
      toast?.('Submitted for approval.', 'success')
      onDone()
    } catch (e) {
      toast?.(e?.data?.detail || 'Submission failed', 'error')
    } finally { setBusy(false) }
  }

  return (
    <div className="card" style={{ marginBottom: 16 }}>
      <div style={{ fontWeight: 700, marginBottom: 12 }}>New Submission</div>
      <div className="form-row">
        <div className="form-group">
          <label className="form-label">Policy</label>
          <select className="form-input" value={policyId} onChange={e => setPolicyId(e.target.value)}>
            <option value="">-- choose policy --</option>
            {policies.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
        </div>
        <div className="form-group">
          <label className="form-label">Vendor</label>
          <select className="form-input" value={vendorId} onChange={e => setVendorId(e.target.value)}
                  disabled={user?.role === 'VENDOR'}>
            <option value="">-- choose vendor --</option>
            {vendors.map(v => <option key={v.id} value={v.id}>{v.name}</option>)}
          </select>
        </div>
      </div>
      <button className="btn btn-primary btn-sm" onClick={submit} disabled={busy}>
        {busy ? 'Submitting…' : 'Submit for Approval'}
      </button>
    </div>
  )
}

function NewPolicyModal({ onClose, onCreated, toast }) {
  const [f, setF] = useState({
    name: '', category: '', description: '', version: 1,
    gl: 5000000, wc: true, umbrella: true, notExpired: true,
  })
  const [busy, setBusy] = useState(false)

  async function create() {
    if (!f.name.trim()) return toast?.('Policy name is required.', 'error')
    setBusy(true)
    try {
      await api('POST', '/policies', {
        name: f.name, category: f.category || null, description: f.description || null,
        version: Number(f.version),
        requirements: {
          required_gl_limit_usd: Number(f.gl),
          workers_comp_required: f.wc,
          umbrella_required: f.umbrella,
          must_not_be_expired: f.notExpired,
        },
      })
      toast?.('Policy created.', 'success')
      onCreated()
    } catch (e) {
      toast?.(e?.data?.detail || 'Could not create policy', 'error')
    } finally { setBusy(false) }
  }

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal" onClick={e => e.stopPropagation()}>
        <div className="modal-title">New Compliance Policy</div>
        <div className="modal-sub">e.g. Construction Policy — $5M GL, Workers Comp, Umbrella</div>
        <div className="form-group">
          <label className="form-label">Policy name</label>
          <input className="form-input" value={f.name} placeholder="Construction Policy"
                 onChange={e => setF({ ...f, name: e.target.value })} />
        </div>
        <div className="form-row">
          <div className="form-group">
            <label className="form-label">Category</label>
            <input className="form-input" value={f.category} placeholder="Construction"
                   onChange={e => setF({ ...f, category: e.target.value })} />
          </div>
          <div className="form-group">
            <label className="form-label">Applies to version</label>
            <select className="form-input" value={f.version} onChange={e => setF({ ...f, version: e.target.value })}>
              <option value={1}>Version 1</option><option value={2}>Version 2</option>
            </select>
          </div>
        </div>
        <div className="form-group">
          <label className="form-label">Required General Liability ($)</label>
          <input className="form-input" type="number" value={f.gl}
                 onChange={e => setF({ ...f, gl: e.target.value })} />
        </div>
        <div className="form-group">
          <label className="form-label">Additional requirements</label>
          {[['wc', 'Workers Compensation required'], ['umbrella', 'Umbrella / excess liability required'],
            ['notExpired', 'Certificates must not be expired']].map(([k, lbl]) => (
            <label key={k} style={{ display: 'flex', gap: 8, alignItems: 'center', fontWeight: 400, marginBottom: 4 }}>
              <input type="checkbox" checked={f[k]} onChange={e => setF({ ...f, [k]: e.target.checked })} />
              {lbl}
            </label>
          ))}
        </div>
        <div className="modal-footer" style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: 16 }}>
          <button className="btn btn-ghost btn-sm" onClick={onClose}>Cancel</button>
          <button className="btn btn-primary btn-sm" onClick={create} disabled={busy}>
            {busy ? 'Creating…' : 'Create Policy'}
          </button>
        </div>
      </div>
    </div>
  )
}
