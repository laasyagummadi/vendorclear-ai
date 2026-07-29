import { useState, useEffect } from 'react'
import { api } from '../api.js'

// ─────────────────────────────────────────────────────────────
//  components/Policies.jsx  —  Admin compliance policy editor
//  (Feature 6 / Nirupama Module 2: "Configurable Compliance
//  Policies" — admins can tune per-category scoring weights,
//  finding penalties, required document types, and risk
//  thresholds instead of everything being hardcoded.)
//
//  The backend CRUD (GET/POST/PATCH/DELETE /api/v1/policies) has
//  existed since Phase 2 kicked off, but no screen in the Admin
//  Portal ever called it — admins had no way to actually edit a
//  policy short of hitting the API directly. This page is that
//  screen.
// ─────────────────────────────────────────────────────────────

const CATEGORY_LABELS = {
  CONSTRUCTION: 'Construction',
  SOFTWARE: 'Software',
  ELECTRICAL: 'Electrical',
  TRANSPORTATION: 'Transportation',
  CIVIL: 'Civil',
  OTHER: 'Other',
}

const DOC_TYPE_OPTIONS = ['COI', 'DIVERSITY_CERT']

const EMPTY_FORM = {
  name: '', description: '',
  weight_status: 0.40, weight_documents: 0.30, weight_expiry: 0.20, weight_diversity: 0.10,
  finding_penalty_critical: 10, finding_penalty_high: 5, finding_penalty_medium: 2,
  required_document_types: [], risk_low_min_score: 75, risk_medium_min_score: 50,
  is_active: true,
}

function toForm(policy) {
  return {
    name: policy.name || '',
    description: policy.description || '',
    weight_status: policy.weight_status,
    weight_documents: policy.weight_documents,
    weight_expiry: policy.weight_expiry,
    weight_diversity: policy.weight_diversity,
    finding_penalty_critical: policy.finding_penalty_critical,
    finding_penalty_high: policy.finding_penalty_high,
    finding_penalty_medium: policy.finding_penalty_medium,
    required_document_types: policy.required_document_types || [],
    risk_low_min_score: policy.risk_low_min_score,
    risk_medium_min_score: policy.risk_medium_min_score,
    is_active: policy.is_active,
  }
}

export default function Policies({ toast, user }) {
  const [policies, setPolicies] = useState([])
  const [loading, setLoading] = useState(true)
  const [selectedId, setSelectedId] = useState(null)
  const [form, setForm] = useState(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  const isAdmin = user?.role === 'ADMIN'

  function load() {
    setLoading(true)
    api('GET', '/policies')
      .then(res => {
        const list = Array.isArray(res) ? res : []
        setPolicies(list)
        if (list.length && !selectedId) selectPolicy(list[0])
      })
      .catch(() => setPolicies([]))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  function selectPolicy(p) {
    setSelectedId(p.id)
    setForm(toForm(p))
    setError('')
  }

  function set(field, value) {
    setForm(f => ({ ...f, [field]: value }))
  }

  function setNum(field, value) {
    set(field, value === '' ? '' : Number(value))
  }

  function toggleDocType(type) {
    setForm(f => {
      const has = f.required_document_types.includes(type)
      return {
        ...f,
        required_document_types: has
          ? f.required_document_types.filter(t => t !== type)
          : [...f.required_document_types, type],
      }
    })
  }

  const weightSum = ['weight_status', 'weight_documents', 'weight_expiry', 'weight_diversity']
    .reduce((sum, k) => sum + (Number(form[k]) || 0), 0)

  async function save() {
    if (!selectedId) return
    setError('')
    if (Number(form.risk_medium_min_score) > Number(form.risk_low_min_score)) {
      setError('The "Medium risk" threshold cannot be higher than the "Low risk" threshold.')
      return
    }
    setSaving(true)
    try {
      const updated = await api('PATCH', `/policies/${selectedId}`, form)
      toast?.('Policy saved — new scores will use these weights going forward.', 'success')
      setPolicies(list => list.map(p => (p.id === selectedId ? updated : p)))
    } catch (e) {
      setError(e?.data?.detail || 'Failed to save policy.')
    } finally {
      setSaving(false)
    }
  }

  if (!isAdmin) {
    return (
      <div>
        <div className="page-header">
          <div>
            <div className="page-title">Compliance Policies</div>
            <div className="page-sub">Admin access required</div>
          </div>
        </div>
        <div className="card">
          <div className="empty-state">
            <div className="icon">🔒</div>
            <p>Only Admins can view or edit compliance policies. Ask an Admin to make changes here.</p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <div className="page-header">
        <div>
          <div className="page-title">Compliance Policies</div>
          <div className="page-sub">
            {policies.length} categor{policies.length !== 1 ? 'ies' : 'y'} configured — each vendor is scored using the policy that matches its category.
          </div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load}>↺ Refresh</button>
      </div>

      {loading ? (
        <div className="empty-state"><div className="spinner" style={{ margin: '0 auto' }} /></div>
      ) : policies.length === 0 ? (
        <div className="card"><div className="empty-state"><p>No policies found.</p></div></div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '260px 1fr', gap: 20 }}>
          {/* ── Category list ───────────────────────────── */}
          <div className="card" style={{ padding: 8 }}>
            {policies.map(p => (
              <div
                key={p.id}
                onClick={() => selectPolicy(p)}
                style={{
                  padding: '12px 14px', borderRadius: 8, cursor: 'pointer', marginBottom: 4,
                  background: p.id === selectedId ? '#111' : 'transparent',
                  border: p.id === selectedId ? '1px solid #333' : '1px solid transparent',
                }}
              >
                <div style={{ fontWeight: 600, fontSize: 13 }}>
                  {CATEGORY_LABELS[p.category] || p.category}
                </div>
                <div style={{ fontSize: 11, color: '#666', marginTop: 2 }}>
                  {p.is_active ? 'Active' : 'Inactive'} · Low risk ≥ {p.risk_low_min_score}
                </div>
              </div>
            ))}
          </div>

          {/* ── Editor ──────────────────────────────────── */}
          <div className="card">
            {error && (
              <div style={{ background: '#1c0a0a', border: '1px solid #f87171', color: '#f87171', borderRadius: 8, padding: '10px 14px', marginBottom: 16, fontSize: 13 }}>
                {error}
              </div>
            )}

            <div className="form-group">
              <label className="form-label">Policy name</label>
              <input className="form-input" value={form.name} onChange={e => set('name', e.target.value)} />
            </div>
            <div className="form-group">
              <label className="form-label">Description</label>
              <input className="form-input" value={form.description || ''} onChange={e => set('description', e.target.value)} />
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 16 }}>
              <input type="checkbox" checked={!!form.is_active} onChange={e => set('is_active', e.target.checked)} id="policy-active" />
              <label htmlFor="policy-active" style={{ fontSize: 13, color: '#ccc' }}>Policy is active</label>
            </div>

            <div style={{ fontSize: 12, fontWeight: 600, color: '#777', textTransform: 'uppercase', letterSpacing: '.06em', margin: '20px 0 10px' }}>
              Scoring weights {weightSum.toFixed(2) !== '1.00' && (
                <span style={{ color: '#fbbf24', fontWeight: 400, textTransform: 'none', letterSpacing: 'normal' }}>
                  &nbsp;(sum: {weightSum.toFixed(2)} — normalized automatically, doesn't need to be exactly 1.0)
                </span>
              )}
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label className="form-label">Status</label>
                <input type="number" step="0.05" min="0" max="1" className="form-input" value={form.weight_status} onChange={e => setNum('weight_status', e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Documents</label>
                <input type="number" step="0.05" min="0" max="1" className="form-input" value={form.weight_documents} onChange={e => setNum('weight_documents', e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Expiry</label>
                <input type="number" step="0.05" min="0" max="1" className="form-input" value={form.weight_expiry} onChange={e => setNum('weight_expiry', e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Diversity</label>
                <input type="number" step="0.05" min="0" max="1" className="form-input" value={form.weight_diversity} onChange={e => setNum('weight_diversity', e.target.value)} />
              </div>
            </div>

            <div style={{ fontSize: 12, fontWeight: 600, color: '#777', textTransform: 'uppercase', letterSpacing: '.06em', margin: '20px 0 10px' }}>
              Finding penalties (points deducted per finding)
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label className="form-label">Critical</label>
                <input type="number" step="1" min="0" className="form-input" value={form.finding_penalty_critical} onChange={e => setNum('finding_penalty_critical', e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">High</label>
                <input type="number" step="1" min="0" className="form-input" value={form.finding_penalty_high} onChange={e => setNum('finding_penalty_high', e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Medium</label>
                <input type="number" step="1" min="0" className="form-input" value={form.finding_penalty_medium} onChange={e => setNum('finding_penalty_medium', e.target.value)} />
              </div>
            </div>

            <div style={{ fontSize: 12, fontWeight: 600, color: '#777', textTransform: 'uppercase', letterSpacing: '.06em', margin: '20px 0 10px' }}>
              Risk tier thresholds (score ≥ threshold → tier)
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
              <div className="form-group">
                <label className="form-label">Low risk minimum score</label>
                <input type="number" step="1" min="0" max="100" className="form-input" value={form.risk_low_min_score} onChange={e => setNum('risk_low_min_score', e.target.value)} />
              </div>
              <div className="form-group">
                <label className="form-label">Medium risk minimum score</label>
                <input type="number" step="1" min="0" max="100" className="form-input" value={form.risk_medium_min_score} onChange={e => setNum('risk_medium_min_score', e.target.value)} />
              </div>
            </div>
            <div style={{ fontSize: 11, color: '#555', marginTop: -4, marginBottom: 16 }}>
              Anything scoring below the Medium threshold is High risk.
            </div>

            <div style={{ fontSize: 12, fontWeight: 600, color: '#777', textTransform: 'uppercase', letterSpacing: '.06em', margin: '20px 0 10px' }}>
              Required document types
            </div>
            <div style={{ display: 'flex', gap: 16, marginBottom: 20 }}>
              {DOC_TYPE_OPTIONS.map(type => (
                <label key={type} style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 13, color: '#ccc', cursor: 'pointer' }}>
                  <input type="checkbox" checked={form.required_document_types.includes(type)} onChange={() => toggleDocType(type)} />
                  {type === 'COI' ? 'Certificate of Insurance' : 'Diversity Certificate'}
                </label>
              ))}
            </div>

            <button className="btn btn-primary" onClick={save} disabled={saving}>
              {saving ? 'Saving…' : 'Save Policy'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
