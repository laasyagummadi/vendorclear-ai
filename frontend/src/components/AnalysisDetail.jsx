import { useState, useEffect } from 'react'
import { api } from '../api.js'
import { fmtDate, fmtMoney, analysisBadgeClass, severityBadgeClass } from '../helpers.js'

// ── Per-field confidence badge (Module 8) ───────────────────
function ConfidenceBadge({ score }) {
  if (score == null) return null
  const pct = Math.round(score * 100)
  const color = pct >= 85 ? '#107c10' : pct >= 60 ? '#97600a' : '#a4262c'
  const bg = pct >= 85 ? '#dff6dd' : pct >= 60 ? '#fff4ce' : '#fde7e9'
  return (
    <span style={{
      display: 'inline-flex', alignItems: 'center', padding: '1px 7px',
      borderRadius: 20, fontSize: 10, fontWeight: 700, letterSpacing: '.04em',
      background: bg, color, marginLeft: 6
    }}>
      {pct}%
    </span>
  )
}

// ── Overall confidence ring (Module 8) ─────────────────────
function ConfidenceRing({ score }) {
  const pct = Math.round((score || 0) * 100)
  const color = pct >= 85 ? '#107c10' : pct >= 60 ? '#97600a' : '#a4262c'
  const r = 24, circ = 2 * Math.PI * r
  const dash = (pct / 100) * circ
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
      <svg width={60} height={60} viewBox="0 0 60 60">
        <circle cx={30} cy={30} r={r} fill="none" stroke="#e1dfdd" strokeWidth={5} />
        <circle
          cx={30} cy={30} r={r} fill="none" stroke={color} strokeWidth={5}
          strokeDasharray={`${dash} ${circ - dash}`}
          strokeLinecap="round"
          transform="rotate(-90 30 30)"
          style={{ transition: 'stroke-dasharray .4s ease' }}
        />
        <text x={30} y={35} textAnchor="middle" fontSize={14} fontWeight={700} fill={color}>
          {pct}%
        </text>
      </svg>
      <div>
        <div style={{ fontSize: 12, fontWeight: 700, color }}>
          {pct >= 85 ? 'High Confidence' : pct >= 60 ? 'Medium Confidence' : 'Low Confidence'}
        </div>
        <div style={{ fontSize: 11, color: '#605e5c' }}>AI Extraction</div>
      </div>
    </div>
  )
}

// ── Editable field row (Module 3) ──────────────────────────
function EditableField({ label, fieldKey, value, type = 'text', fieldConf, onChange }) {
  return (
    <div style={{ marginBottom: 10 }}>
      <div style={{ display: 'flex', alignItems: 'center', marginBottom: 3 }}>
        <span style={{ fontSize: 10, color: '#a19f9d', textTransform: 'uppercase', letterSpacing: '.06em', fontWeight: 600 }}>
          {label}
        </span>
        <ConfidenceBadge score={fieldConf} />
      </div>
      <input
        type={type}
        className="form-input"
        style={{ padding: '7px 10px', fontSize: 13 }}
        value={value ?? ''}
        onChange={e => onChange(fieldKey, e.target.value)}
      />
    </div>
  )
}

export default function AnalysisDetail({ id, navigate, toast }) {
  const [analysis, setAnalysis] = useState(null)
  const [editing, setEditing] = useState(false)
  const [editData, setEditData] = useState({})
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api('GET', `/analyses/${id}`).then(a => {
      setAnalysis(a)
      setEditData(extractEditable(a))
    }).catch(() => setAnalysis(null))
  }, [id])

  function extractEditable(a) {
    return {
      insured_name: a.insured_name ?? '',
      insurer_name: a.insurer_name ?? '',
      policy_number: a.policy_number ?? '',
      coverage_type: a.coverage_type ?? '',
      general_liability_limit_usd: a.general_liability_limit_usd ?? '',
      workers_comp_limit_usd: a.workers_comp_limit_usd ?? '',
      auto_liability_limit_usd: a.auto_liability_limit_usd ?? '',
      effective_date: a.effective_date ?? '',
      expiry_date: a.expiry_date ?? '',
      additional_insured: a.additional_insured ?? false,
      certificate_holder: a.certificate_holder ?? '',
      cert_body: a.cert_body ?? '',
      cert_type: a.cert_type ?? '',
      cert_number: a.cert_number ?? '',
      ownership_pct: a.ownership_pct ?? '',
    }
  }

  function handleChange(key, value) {
    setEditData(d => ({ ...d, [key]: value }))
  }

  async function saveEdits() {
    setSaving(true)
    try {
      // Convert numeric fields from string
      const payload = { ...editData }
      for (const numKey of ['general_liability_limit_usd', 'workers_comp_limit_usd', 'auto_liability_limit_usd', 'ownership_pct']) {
        if (payload[numKey] !== '' && payload[numKey] != null) {
          payload[numKey] = parseFloat(payload[numKey]) || null
        } else {
          payload[numKey] = null
        }
      }
      // Remove empty strings → null
      for (const k of Object.keys(payload)) {
        if (payload[k] === '') payload[k] = null
      }

      const updated = await api('PUT', `/analyses/${id}`, payload)
      if (updated) {
        setAnalysis(updated)
        setEditData(extractEditable(updated))
        toast?.('Analysis saved and compliance re-evaluated!', 'success')
        setEditing(false)
      }
    } catch (e) {
      toast?.(e?.data?.detail || 'Failed to save changes', 'error')
    } finally {
      setSaving(false)
    }
  }

  if (!analysis) return (
    <div className="empty-state">
      <div className="spinner" style={{ width: 24, height: 24, borderWidth: 3, margin: '48px auto' }} />
    </div>
  )

  const findings = analysis.findings || []
  const fc = analysis.field_confidences || {}

  return (
    <div>
      {/* Breadcrumb */}
      <div className="breadcrumb">
        <a onClick={() => navigate('vendors')}>Vendors</a>
        <span className="breadcrumb-sep">›</span>
        <a onClick={() => navigate('vendor-detail', analysis.vendor_id || '')}>Vendor</a>
        <span className="breadcrumb-sep">›</span>
        <span style={{ color: '#605e5c' }}>Analysis</span>
      </div>

      {/* Header */}
      <div className="page-header">
        <div>
          <div className="page-title">Document Analysis Review</div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginTop: 4 }}>
            <span className={`badge ${analysisBadgeClass(analysis.status)}`}>{analysis.status || '—'}</span>
            <span style={{ fontSize: 11, color: '#605e5c' }}>
              Analyzed {new Date(analysis.created_at).toLocaleDateString()}
            </span>
          </div>
        </div>
        <div style={{ display: 'flex', gap: 8, alignItems: 'center' }}>
          {editing ? (
            <>
              <button className="btn btn-ghost btn-sm" onClick={() => { setEditing(false); setEditData(extractEditable(analysis)) }}>
                Cancel
              </button>
              <button className="btn btn-primary btn-sm" onClick={saveEdits} disabled={saving}>
                {saving ? <><span className="spinner" style={{ width: 12, height: 12, borderWidth: 2, marginRight: 6 }} />Saving...</> : '✓ Save & Re-evaluate'}
              </button>
            </>
          ) : (
            <button className="btn btn-ghost btn-sm" onClick={() => setEditing(true)}>
              ✎ Edit Fields
            </button>
          )}
        </div>
      </div>

      {/* Split-screen layout (Module 4) */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16, marginBottom: 20 }}>

        {/* LEFT — OCR Text / Document info */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Confidence ring (Module 8) */}
          <div className="card" style={{ padding: '16px 20px' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 12 }}>
              <div style={{ fontSize: 12, fontWeight: 600, color: '#605e5c', textTransform: 'uppercase', letterSpacing: '.06em' }}>
                AI Confidence
              </div>
              {analysis.confidence_score === 0.65 && (
                <span className="badge badge-warning" title="Gemini API failed or was rate-limited. Results generated using fallback mock logic.">
                  ⚠ Fallback Mode
                </span>
              )}
            </div>
            <ConfidenceRing score={analysis.confidence_score} />
          </div>

          {/* OCR text */}
          {analysis.raw_text && (
            <div className="card">
              <div style={{ fontSize: 12, fontWeight: 600, color: '#605e5c', marginBottom: 10, textTransform: 'uppercase', letterSpacing: '.06em' }}>
                Extracted Document Text (OCR)
              </div>
              <pre style={{
                fontSize: 11, color: '#1b1a19', whiteSpace: 'pre-wrap', wordBreak: 'break-word',
                maxHeight: 340, overflowY: 'auto', lineHeight: 1.6,
                background: '#f3f2f1', borderRadius: 6, padding: 12, margin: 0
              }}>
                {analysis.raw_text.substring(0, 2500)}
                {analysis.raw_text.length > 2500 ? '\n…' : ''}
              </pre>
            </div>
          )}

          {/* Compliance Findings */}
          <div className="card">
            <div style={{ fontSize: 12, fontWeight: 600, color: '#605e5c', marginBottom: 12, textTransform: 'uppercase', letterSpacing: '.06em' }}>
              Compliance Findings ({findings.length})
            </div>
            {findings.length === 0
              ? <div style={{ color: '#107c10', fontSize: 13, textAlign: 'center', padding: '16px 0' }}>✓ No compliance issues found</div>
              : findings.map((f, i) => (
                <div key={i} className="finding-item">
                  <div className="finding-sev"><span className={`badge ${severityBadgeClass(f.severity)}`}>{f.severity || '—'}</span></div>
                  <div>
                    <div style={{ fontSize: 12, fontWeight: 600, color: '#1b1a19' }}>{f.rule_code || ''}</div>
                    <div style={{ fontSize: 12, color: '#605e5c', marginTop: 2 }}>{f.message || ''}</div>
                  </div>
                </div>
              ))
            }
          </div>
        </div>

        {/* RIGHT — Editable extracted fields (Module 3) */}
        <div className="card">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
            <div style={{ fontSize: 12, fontWeight: 600, color: '#605e5c', textTransform: 'uppercase', letterSpacing: '.06em' }}>
              Extracted Fields
            </div>
            {editing && (
              <span style={{ fontSize: 11, color: '#0078d4', fontWeight: 600 }}>
                ● Editing — all changes trigger compliance re-evaluation
              </span>
            )}
          </div>

          {editing ? (
            /* Editable mode */
            <div>
              <EditableField label="Insured Name" fieldKey="insured_name" value={editData.insured_name} fieldConf={fc.insured_name} onChange={handleChange} />
              <EditableField label="Insurer Name" fieldKey="insurer_name" value={editData.insurer_name} onChange={handleChange} />
              <EditableField label="Policy Number" fieldKey="policy_number" value={editData.policy_number} fieldConf={fc.policy_number} onChange={handleChange} />
              <EditableField label="Coverage Type" fieldKey="coverage_type" value={editData.coverage_type} onChange={handleChange} />
              <EditableField label="GL Limit (USD)" fieldKey="general_liability_limit_usd" value={editData.general_liability_limit_usd} type="number" fieldConf={fc.general_liability_limit_usd} onChange={handleChange} />
              <EditableField label="Workers Comp Limit (USD)" fieldKey="workers_comp_limit_usd" value={editData.workers_comp_limit_usd} type="number" fieldConf={fc.workers_comp_limit_usd} onChange={handleChange} />
              <EditableField label="Auto Liability Limit (USD)" fieldKey="auto_liability_limit_usd" value={editData.auto_liability_limit_usd} type="number" fieldConf={fc.auto_liability_limit_usd} onChange={handleChange} />
              <EditableField label="Effective Date (YYYY-MM-DD)" fieldKey="effective_date" value={editData.effective_date} type="date" fieldConf={fc.effective_date} onChange={handleChange} />
              <EditableField label="Expiry Date (YYYY-MM-DD)" fieldKey="expiry_date" value={editData.expiry_date} type="date" fieldConf={fc.expiry_date} onChange={handleChange} />
              <EditableField label="Certificate Holder" fieldKey="certificate_holder" value={editData.certificate_holder} onChange={handleChange} />
              <div style={{ marginBottom: 10 }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: 8, cursor: 'pointer' }}>
                  <input type="checkbox" checked={!!editData.additional_insured} onChange={e => handleChange('additional_insured', e.target.checked)} />
                  <span style={{ fontSize: 13 }}>Additional Insured</span>
                  <ConfidenceBadge score={fc.additional_insured} />
                </label>
              </div>
              {/* Diversity cert fields */}
              {(analysis.cert_type || editData.cert_type) && (
                <>
                  <div style={{ height: 1, background: '#e1dfdd', margin: '10px 0' }} />
                  <div style={{ fontSize: 11, fontWeight: 600, color: '#a19f9d', marginBottom: 8 }}>DIVERSITY CERT FIELDS</div>
                  <EditableField label="Cert Body" fieldKey="cert_body" value={editData.cert_body} fieldConf={fc.cert_body} onChange={handleChange} />
                  <EditableField label="Cert Type (MBE/WBE/DBE...)" fieldKey="cert_type" value={editData.cert_type} fieldConf={fc.cert_type} onChange={handleChange} />
                  <EditableField label="Cert Number" fieldKey="cert_number" value={editData.cert_number} fieldConf={fc.cert_number} onChange={handleChange} />
                  <EditableField label="Ownership %" fieldKey="ownership_pct" value={editData.ownership_pct} type="number" fieldConf={fc.ownership_pct} onChange={handleChange} />
                </>
              )}
            </div>
          ) : (
            /* Read-only mode — show values with confidence badges */
            <div>
              {[
                ['Insured Name', analysis.insured_name, 'insured_name'],
                ['Insurer Name', analysis.insurer_name, null],
                ['Policy Number', analysis.policy_number, 'policy_number'],
                ['Coverage Type', analysis.coverage_type, null],
                ['GL Limit', fmtMoney(analysis.general_liability_limit_usd), 'general_liability_limit_usd'],
                ['Workers Comp', fmtMoney(analysis.workers_comp_limit_usd), 'workers_comp_limit_usd'],
                ['Auto Liability', fmtMoney(analysis.auto_liability_limit_usd), 'auto_liability_limit_usd'],
                ['Effective Date', fmtDate(analysis.effective_date), 'effective_date'],
                ['Expiry Date', fmtDate(analysis.expiry_date), 'expiry_date'],
                ['Certificate Holder', analysis.certificate_holder, null],
                ['Additional Insured', analysis.additional_insured != null ? (analysis.additional_insured ? 'Yes' : 'No') : null, 'additional_insured'],
                ['Cert Body', analysis.cert_body, 'cert_body'],
                ['Cert Type', analysis.cert_type, 'cert_type'],
                ['Cert Number', analysis.cert_number, 'cert_number'],
                ['Ownership %', analysis.ownership_pct != null ? analysis.ownership_pct + '%' : null, 'ownership_pct'],
              ].filter(([, v]) => v && v !== '—' && v !== null).map(([label, value, confKey]) => (
                <div key={label} className="detail-item" style={{ marginBottom: 8 }}>
                  <div style={{ display: 'flex', alignItems: 'center' }}>
                    <span className="detail-item-label">{label}</span>
                    {confKey && <ConfidenceBadge score={fc[confKey]} />}
                  </div>
                  <div className="detail-item-val">{String(value)}</div>
                </div>
              ))}
              {Object.keys(fc).length === 0 && (
                <div style={{ fontSize: 11, color: '#a19f9d', marginTop: 8 }}>
                  Confidence scores not available for this analysis
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
